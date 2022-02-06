from docx import Document

from docmaker.hooks import Hook


@Hook("pre_finalize_docx")
def convert_single_row_tables(ctx):
    d = Document(ctx.docxfile)

    style_name = ctx.get("hacks.single_row_table_style") or "Normal Table"
    if style_name not in d.styles:
        return

    for table in d.tables:
        if len(table.rows) == 1:
            table.style = d.styles[style_name]

    d.save(ctx.docxfile)
