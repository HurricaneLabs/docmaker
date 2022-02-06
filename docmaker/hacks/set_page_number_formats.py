import sys

from docx.oxml.shared import qn

from docmaker.hooks import Hook
from docmaker.oxml import OxmlElement


def set_page_number_format(section, pgNumStart=None, pgNumFmt=None):
    # delete any existing <w:pgNumType> tags
    for w_pgNumType in section._sectPr.xpath("./w:pgNumType"):
        section._sectPr.remove(w_pgNumType)

    if pgNumStart or pgNumFmt:
        with OxmlElement("w:pgNumType", append_to=section._sectPr) as pgNumType:
            if pgNumStart:
                pgNumType.set(qn("w:start"), str(pgNumStart))

            if pgNumFmt:
                pgNumType.set(qn("w:fmt"), pgNumFmt)


@Hook("pre_save_docx")
def set_page_number_formats(ctx):
    for section in ctx.composer.doc.sections[:-1]:
        set_page_number_format(
            section,
            pgNumFmt="lowerRoman"
        )

    if hasattr(ctx, "coverpage_section"):
        # Remove page number format for the coverpage section
        set_page_number_format(
            ctx.composer.doc.sections[1],
            pgNumStart=1,
            pgNumFmt="lowerRoman"
        )

    set_page_number_format(
        ctx.composer.doc.sections[-1],
        pgNumStart=1,
        pgNumFmt="decimal"
    )
