import argparse
import base64
import gzip
import io
import json
import os
import re
import socket
import tempfile
import time
import traceback
from typing import MutableMapping

import falcon
import multipart
import werkzeug.http
from ruamel.yaml import YAML
from werkzeug.serving import run_simple

from .context import Context
from .docmaker import Docmaker
from .features import load_all_features, load_feature
from .features.remote_files import RemoteFiles
from .hooks import Hook
from .options import flatten, get_features_options_from_environ


class DocmakerApi:
    @Hook("pre_initialize")
    def initialize_api(self, ctx):
        (ctx.__req, ctx.__resp) = ctx.srcfile
        ctx.srcfile = None
        ctx.__req.context = ctx

    @Hook("post_setup_tmpdir")
    def parse_post_body(self, ctx):
        start = time.time()
        form = ctx.__req.stream.read(ctx.__req.content_length or 0)
        ctx.timing["parse_post_body.read_from_stream"] = round(time.time() - start, 4)

        if ctx.__req.get_header("content-encoding") == "gzip":
            start = time.time()
            form = gzip.decompress(form)
            ctx.timing["parse_post_body.decompress"] = round(time.time() - start, 4)

        content_type, content_type_options = werkzeug.http.parse_options_header(ctx.__req.content_type)

        if content_type == "application/json":
            start = time.time()
            form = json.loads(form)
            ctx.timing["parse_post_body.json_loads"] = round(time.time() - start, 4)
            ctx._post_body = form

            for key in form:
                start = time.time()

                if key == "options":
                    ctx.options.update(flatten(form[key]))
                else:
                    if not isinstance(form[key], MutableMapping):
                        form[key] = {
                            "filename": key,
                            "contents": form[key]
                        }

                    tmpfile = os.path.join(ctx.tmpdir, form[key]["filename"])

                    contents = form[key]["contents"]

                    if not isinstance(contents, (bytes, str)):
                        contents = json.dumps(contents)

                        if "format" not in form[key]:
                            form[key]["format"] = "json"
                    elif form[key].get("base64encoded", False):
                        contents = base64.b64decode(contents)

                    if not isinstance(contents, bytes):
                        contents = contents.encode()

                    with open(tmpfile, "wb") as f:
                        f.write(contents)

                    if key == "srcfile":
                        ctx.srcfile = form[key]["filename"]

                        if "format" in form[key]:
                            ctx.srcfile_format = form[key]["format"]
                    elif key == "template":
                        ctx.options["jinja_template.template_file"] = form[key]["filename"]
                ctx.timing[f"parse_post_body.{key}"] = round(time.time() - start, 4)
        elif content_type == "multipart/form-data":
            mpparser = multipart.MultipartParser(
                io.BytesIO(form),
                content_type_options["boundary"]
            )

            for part in mpparser:
                start = time.time()
                if part.name == "options":
                    opts = YAML().load(part.file)
                    ctx.options.update(flatten(opts))
                else:
                    if part.filename and not ctx.file_exists_in_temp_dir(part.filename):
                        tmpfile = os.path.join(ctx.tmpdir, part.filename)
                    else:
                        tmpfile = ctx.get_temp_file(suffix=part.filename or None)

                    with open(tmpfile, "wb") as f:
                        f.write(part.raw)

                    if part.name == "srcfile":
                        ctx.srcfile = tmpfile
                ctx.timing[f"parse_post_body.{part.name}"] = round(time.time() - start, 4)

        if "features" in ctx.options:
            for feature in ctx.options["features"]:
                feature = load_feature(feature)
                if feature not in ctx._features:
                    ctx.add_feature(feature)

            del ctx.options["features"]

        if not (ctx.srcfile and ctx.file_exists_in_temp_dir(ctx.srcfile)):
            raise ValueError(ctx.srcfile)

        ctx.srcfile = os.path.join(ctx.tmpdir, ctx.srcfile)
        ctx.output_file = ctx.get_temp_file(suffix=f".{ctx.output_format}")

    @Hook("post_get_pypandoc_kwargs")
    def set_pypandoc_cworkdir(self, ctx):
        ctx.pypandoc_kwargs["cworkdir"] = ctx.tmpdir

    @Hook("pre_cleanup_tmpdir")
    def stream_response(self, ctx):
        ctx.__resp.stream = open(ctx.output_file, "rb")
        size = os.stat(ctx.output_file).st_size

        srcfile = os.path.basename(ctx.srcfile)
        srcfile = srcfile.rsplit(".", 1)[0]

        ctx.__resp.status = falcon.HTTP_OK
        ctx.__resp.set_header("content-length", size)
        ctx.__resp.set_header("content-disposition",
                              f"attachment; filename={srcfile}.{ctx.output_format}")

        if ctx.__req.get_param_as_bool("timing", default=False):
            ctx.__resp.set_header("x-timing", json.dumps(ctx.timing))


class DocmakerResource(Docmaker):
    def __init__(self, features=None, options=None):
        super().__init__(features, options)
        if DocmakerApi not in self.features:
            self.features.append(DocmakerApi)

    def get_context(self, srcfile, output_file=None):
        req, _ = srcfile

        features = []
        if req.has_param("feature"):
            for feature in req.get_param_as_list("feature"):
                if feature not in features:
                    features.append(feature)

        ctx = super().get_context(srcfile, output_file, features=features)
        return ctx

    def on_post(self, req, resp):
        self((req, resp))


class FeatureListResource:
    def on_get(self, req, resp):
        # pylint: disable=unused-argument
        features = load_all_features()

        resp.status = falcon.HTTP_OK
        resp.text = json.dumps(list(features.keys()))


class HealthCheckResource:
    def on_get(self, req, resp):
        response = {}

        if req.get_param_as_bool("uno", default=False):
            try:
                s = socket.create_connection(("127.0.0.1", 2002))
            except ConnectionRefusedError:
                response["error"] = "uno: connection refused"
            else:
                s.close()

        if "error" in response:
            response["status"] = "err"
            resp.status = falcon.HTTP_INTERNAL_SERVER_ERROR
        else:
            response["status"] = "ok"
            resp.status = falcon.HTTP_OK

        resp.text = json.dumps(response)


def error_handler(e, req, resp, params):
    # pylint: disable=unused-argument
    resp.status = falcon.HTTP_INTERNAL_SERVER_ERROR
    resp.text = json.dumps({
        "err": str(e),
        "traceback": traceback.format_exc()
    })


class DocmakerApp(falcon.App):
    def __init__(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        super().__init__(*args, **kwargs)

        features, options = get_features_options_from_environ()

        ctx = Context(
            docmaker=None,
            srcfile=None,
            output_file=None,
            features=list(map(load_feature, features)),
            options=options
        )

        ctx._app = self

        self.api__initialize(ctx)
        self.api__setup_feature_list_resource(ctx)
        self.api__setup_health_check_resource(ctx)
        self.api__setup_default_route(ctx)
        self.api__setup_routes_from_environment(ctx)

    @property
    def default_route(self):
        return os.environ.get("DOCMAKER_DEFAULT_ROUTE", "/render")

    @Hook(ctx=lambda args: args[1])
    def add_route(self, ctx, uri_template, resource, **kwargs):
        super().add_route(uri_template, resource, **kwargs)

    @Hook()
    def api__initialize(self, ctx):
        self.add_error_handler(Exception, error_handler)

    @Hook()
    def api__setup_feature_list_resource(self, ctx):
        self.add_route(ctx, "/features", FeatureListResource())

    @Hook()
    def api__setup_health_check_resource(self, ctx):
        self.add_route(ctx, "/health", HealthCheckResource())

    @Hook(default_route=lambda _: os.environ.get("DOCMAKER_DEFAULT_ROUTE", "/render"))
    def api__setup_default_route(self, ctx):
        self.__default_resource = DocmakerResource(ctx._features, ctx.options)
        self.add_route(ctx, ctx.default_route, self.__default_resource)

    @Hook()
    def api__setup_routes_from_environment(self, ctx):
        # Dynamically configure additional routes from environment
        for envvar in os.environ:
            m = re.match(r"^DOCMAKER_ROUTE_(\d+)_PATH$", envvar)
            if m:
                route_id = m.groups()[0]
                features, options = get_features_options_from_environ(
                    f"DOCMAKER_ROUTE_{route_id}",
                    ctx._features,
                    ctx.options,
                )

                resource = DocmakerResource(features, options)
                self.add_route(ctx, os.environ[envvar], resource)


app = DocmakerApp()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind-addr", default="0.0.0.0")
    ap.add_argument("--bind-port", type=int, default=8080)
    args = ap.parse_args()

    run_simple(args.bind_addr, args.bind_port, app, use_debugger=True)
