import os
import shutil

from docx import Document
from docx.enum.style import WD_STYLE_TYPE

from docmaker.hooks import Hook


class ExtendedStyles:
    @Hook("post_initialize", predicate=(
        lambda ctx: "extended_styles.file" in ctx,
        lambda ctx: os.path.exists(ctx["extended_styles.file"])
    ))
    def merge_extended_styles(self, ctx):
        if not ctx.reference_doc:
            ctx.reference_doc = ctx.get_temp_file(suffix=".docx")
            shutil.copyfile(ctx["extended_styles.file"], ctx.reference_doc)

            return

        d1 = Document(ctx.reference_doc)
        d2 = Document(ctx["extended_styles.file"])

        for style in d2.styles:
            if style.type != WD_STYLE_TYPE.PARAGRAPH or style.builtin:
                continue

            new_style = d1.styles.add_style(style.name, style.type)
            new_style.element._element = style.element
            new_style.base_style = style.base_style

            for tab_stop in style.paragraph_format.tab_stops:
                new_style.paragraph_format.tab_stops.add_tab_stop(
                    tab_stop.position,
                    tab_stop.alignment,
                    tab_stop.leader
                )

        ctx.reference_doc = ctx.get_temp_file(suffix=".docx")
        d1.save(ctx.reference_doc)
