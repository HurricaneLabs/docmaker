import os

from docmaker.features.coverpage import Coverpage
from docmaker.hooks import Hook


class DraftMode:
    @Hook("post_initialize", predicate=lambda _: "DOCMAKER_DRAFT_MODE" in os.environ)
    def set_is_draft_mode_from_environ(self, ctx):
        ctx["draft_mode.is_draft"] = os.environ["DOCMAKER_DRAFT_MODE"]

    @Hook("pre_generate_coverpage", predicate=(
        lambda ctx: Coverpage in ctx._features,
        lambda ctx: ctx.get_as_boolean("draft_mode.is_draft", False)
    ))
    def add_draft_to_coverpage_title(self, ctx):
        draft_prefix = ctx.get("draft_mode.prefix") or "DRAFT"

        title_field = ctx.get("draft_mode.coverpage_title_field") or "title"
        if ctx.get(f"coverpage.{title_field}"):
            value = ctx[f"coverpage.{title_field}"]
            ctx[f"coverpage.{title_field}"] = f"{draft_prefix} {value}"

    @Hook("pre_finalize", predicate=(
        lambda ctx: ctx._output_file is None,
        lambda ctx: ctx.get_as_boolean("draft_mode.is_draft", False)
    ))
    def add_draft_to_output_filename(self, ctx):
        draft_prefix = ctx.get("draft_mode.prefix") or "DRAFT"

        path = os.path.dirname(ctx.output_file)
        filename = os.path.basename(ctx.output_file)
        filename = f"{draft_prefix}_{filename}"

        ctx.output_file = os.path.join(path, filename)
