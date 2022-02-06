import os

import bugsnag
import falcon
import requests

import docmaker
from docmaker.api import error_handler
from docmaker.hooks import Hook


def bugsnag_error_handler(e, req, resp, params):
    # pylint: disable=unused-argument

    meta_data = {}
    if isinstance(e, requests.exceptions.HTTPError):
        if hasattr(e, "response"):
            meta_data["response"] = {
                "text": e.response.text,
                "headers": dict(e.response.headers),
                "status_code": e.response.status_code,
            }
        if hasattr(e, "request"):
            meta_data["request"] = {
                "url": e.request.url,
                "method": e.request.method,
                "headers": dict(e.request.headers),
            }

    if hasattr(req.context, "_post_body"):
        meta_data["postData"] = req.context._post_body

    if hasattr(req.context, "timing"):
        meta_data["requestTiming"] = req.context.timing

    meta_data["requestHeaders"] = req.headers
    meta_data["wsgiEnv"] = req.env

    if getattr(e, "status", None) != falcon.HTTP_NOT_FOUND:
        bugsnag.notify(
            e,
            context=req.uri,
            meta_data=meta_data,
            severity="error"
        )

    # Allow the default error handler to still run
    error_handler(e, req, resp, params)


class Bugsnag:
    @Hook("post_api__initialize", predicate=(
        lambda ctx: "bugsnag.api_key" in ctx,
        lambda ctx: hasattr(ctx, "_app"),
    ))
    def add_bugsnag_error_handler(self, ctx):
        bugsnag.configure(
            api_key=ctx["bugsnag.api_key"],
            project_root=ctx.get("bugsnag.project_root") or os.path.dirname(docmaker.__file__),
            release_stage=ctx.get("bugsnag.release_stage" or "production"),
            auto_notify=False,
            asynchronous=False,
            app_version=ctx.get("bugsnag.app_version" or docmaker.__version__),
        )

        ctx._app.add_error_handler(Exception, bugsnag_error_handler)
