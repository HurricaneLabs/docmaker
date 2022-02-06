from docx import Document

from docmaker.hooks import Hook


@Hook("pre_save_docx")
def sync_margins(ctx):
    for section in ctx.composer.doc.sections[:-1]:
        section.top_margin = ctx.composer.doc.sections[-1].top_margin
        section.bottom_margin = ctx.composer.doc.sections[-1].bottom_margin
        section.left_margin = ctx.composer.doc.sections[-1].left_margin
        section.right_margin = ctx.composer.doc.sections[-1].right_margin
