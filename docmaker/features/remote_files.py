import os
import re
import sys
from collections import MutableMapping
from urllib.parse import parse_qs, urlparse

import boto3
import boto3.session
import requests

from docmaker.hooks import Hook


class RemoteFiles:
    ACCEPT_HEADER = ", ".join([
        "application/octet-stream",
        "application/*",
        "image/*",
        "text/*",
        "*/*;q=0.8"
    ])

    @staticmethod
    def expand_environment_variables(url):
        return url.format(**os.environ)

    def _get_remote_file_http(self, ctx, src):
        r = requests.get(
            src,
            headers={
                "accept": self.ACCEPT_HEADER
            }
        )
        if r.status_code != 200:
            return None, None

        m = re.search(r"filename=(.+)", r.headers.get("content-disposition", ""))
        if m:
            filename = m.groups()[0]
        else:
            filename = urlparse(src).path.rsplit("/", 1)[1]

        return r.content, filename

    _get_remote_file_https = _get_remote_file_http

    def _get_remote_file_s3(self, ctx, src):
        remote_url = urlparse(src)

        params = {k: v[0] for (k, v) in parse_qs(remote_url.query).items()}

        if remote_url.username:
            params["aws_access_key_id"] = remote_url.username
        if remote_url.password:
            params["aws_secret_access_key"] = remote_url.password

        session = boto3.session.Session(**params)

        s3 = session.client(
            "s3",
            **params
        )

        resp = s3.get_object(
            Bucket=remote_url.hostname,
            Key=remote_url.path[1:],
        )

        return resp["Body"].read(), os.path.basename(remote_url.path)

    def get_remote_file(self, ctx, src, filename=None, ext=None, dest=None):
        src = self.expand_environment_variables(src)
        remote_url = urlparse(src)

        getter = getattr(self, f"_get_remote_file_{remote_url.scheme}", None)
        if not callable(getter):
            return None

        contents, remote_filename = getter(ctx, src)

        if contents is None:
            return None

        if not filename:
            filename = remote_filename

        if ext:
            filename = f"{filename}.{ext}"

        if dest is None:
            dest = ctx.get_temp_file(suffix=filename)

        with open(dest, "wb") as f:
            f.write(contents)

        return dest

    @Hook("post_setup_tmpdir", predicate=lambda ctx: ctx.get_options("remote_files.files"))
    def download_remote_files_to_tmpdir(self, ctx):
        for opt_name, remote_file in ctx.get_options("remote_files.files"):
            ctx[opt_name] = self.get_remote_file(
                ctx,
                remote_file
            )

    @Hook("post_setup_tmpdir", predicate=(
        lambda ctx: ctx.get("reference"),
        lambda ctx: "://" in ctx["reference"]
    ))
    def download_remote_reference(self, ctx):
        ctx.reference_doc = self.get_remote_file(
            ctx,
            ctx["reference"],
            ext="docx"
        )

    @Hook("pre_generate_coverpage", predicate=(
        lambda ctx: ctx.get("coverpage.template"),
        lambda ctx: "://" in ctx["coverpage.template"]
    ))
    def download_remote_coverpage_template(self, ctx):
        ctx.coverpage_template = self.get_remote_file(
            ctx,
            ctx["coverpage.template"],
            ext=".docx"
        )

    @Hook("post_setup_tmpdir", predicate=(
        lambda ctx: "://" in ctx.srcfile,
    ))
    def download_remote_srcfile(self, ctx):
        ctx.srcfile = self.get_remote_file(
            ctx,
            ctx.srcfile,
            ext=ctx.get("srcfile_format")
        )
