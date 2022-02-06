import datetime
import os
from collections import MutableSequence
from string import Formatter

from docx import Document
from docx.enum.section import WD_SECTION
from mailmerge import MailMerge

from docmaker.hooks import Hook


class Coverpage:
    @Hook("pre_convert_to_docx",
          coverpage_template=lambda ctx: ctx.get("coverpage.template"),
          predicate=(
              lambda ctx: ctx.coverpage_template,
              lambda ctx: os.path.exists(ctx.coverpage_template)
          )
    )
    def generate_coverpage(self, ctx):
        ctx.coverpage_docxfile = ctx.get_temp_file()

        doc = MailMerge(ctx.coverpage_template)

        merge_fields = {}
        for field_name in doc.get_merge_fields():
            if f"coverpage.{field_name}" in ctx:
                value = ctx[f"coverpage.{field_name}"]

                if not isinstance(value, MutableSequence):
                    value = [value]
                formatter = Formatter()
                _value = []
                for potential_line in value:
                    include = True

                    for (_, md_field_name, _, _) in formatter.parse(potential_line):
                        if md_field_name is None:
                            continue
                        if md_field_name not in ctx.metadata:
                            include = False
                            break

                    if not include:
                        continue

                    _value.append(potential_line.format(**ctx.metadata))

                value = "\n".join(_value)

            elif field_name == "date" and "coverpage.date_format" in ctx:
                value = datetime.date.today().strftime(ctx["coverpage.date_format"])
            elif field_name in ctx.metadata:
                value = ctx.metadata[field_name]
            else:
                continue

            merge_fields[field_name] = value.replace("\\n", "\n")

        # Perform MailMerge
        doc.merge(**merge_fields)
        doc.write(ctx.coverpage_docxfile)

    @Hook("post_convert_to_docx", predicate=lambda ctx: hasattr(ctx, "coverpage_docxfile"))
    def insert_coverpage(self, ctx):
        ctx.coverpage_doc = Document(ctx.coverpage_docxfile)
        ctx.coverpage_doc.add_section(WD_SECTION.NEW_PAGE)
        ctx.composer.insert(0, ctx.coverpage_doc)
        ctx.coverpage_section = ctx.composer.doc.sections[0]

    @Hook("pre_finalize_docx", after=["sync_header_footer"],
          predicate=lambda ctx: hasattr(ctx, "coverpage_section"))
    def drop_header_footer_on_coverpage(self, ctx):
        # get the header reference from the last section
        header = ctx.coverpage_section.header
        headerReference = header._sectPr.get_headerReference(header._hdrftr_index)
        if headerReference is not None:
            header._drop_definition()

        # get the footer reference from the last section
        footer = ctx.composer.doc.sections[-1].footer
        footerReference = footer._sectPr.get_footerReference(footer._hdrftr_index)

        if footerReference is not None:
            footer._drop_definition()
