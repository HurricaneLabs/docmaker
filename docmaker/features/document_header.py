import os

import pypandoc
from docx import Document
from docx.enum.section import WD_SECTION
from jinja2 import Environment

from docmaker.hooks import Hook


class DocumentHeader:
    @Hook("post_convert_to_docx", before=["Coverpage", "TableOfContents"], predicate=(
        lambda ctx: "document_header.file" in ctx,
        lambda ctx: os.path.exists(ctx["document_header.file"])
    ))
    def insert_document_header(self, ctx):
        with open(ctx["document_header.file"], "r") as f:
            ctx.document_header = f.read()

        if ctx.get_as_boolean("document_header.jinja_template", False):
            env = Environment(trim_blocks=True, lstrip_blocks=True)
            tpl = env.from_string(ctx.document_header)
            ctx.document_header = tpl.render(**ctx.metadata)

        ctx.document_header_srcfile = ctx.get_temp_file(suffix=".md")
        with open(ctx.document_header_srcfile, "w") as f:
            f.write(ctx.document_header)

        ctx.document_header_docxfile = ctx.get_temp_file(suffix=".docx")
        pypandoc.convert_file(
            ctx.document_header_srcfile,
            outputfile=ctx.document_header_docxfile,
            **ctx.pypandoc_kwargs
        )

        ctx.document_header_doc = Document(ctx.document_header_docxfile)

        if ctx.get_as_boolean("document_header.separate_section", False):
            ctx.document_header_doc.add_section(WD_SECTION.NEW_PAGE)

        ctx.composer.insert(0, ctx.document_header_doc)
