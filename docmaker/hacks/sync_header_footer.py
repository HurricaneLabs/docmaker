from docx import Document

from docmaker.hooks import Hook


@Hook("pre_save_docx")
def sync_header_footer(ctx):
    # get the header reference from the last section
    header = ctx.composer.doc.sections[-1].header
    headerReference = header._sectPr.get_headerReference(header._hdrftr_index)

    # get the footer reference from the last section
    footer = ctx.composer.doc.sections[-1].footer
    footerReference = footer._sectPr.get_footerReference(footer._hdrftr_index)

    # add the references to the other sections
    for section in ctx.composer.doc.sections[:-1]:
        if headerReference is not None:
            section.header._sectPr.add_headerReference(
                header._hdrftr_index,
                headerReference.rId
            )
        section.header_distance = ctx.composer.doc.sections[-1].header_distance
        if footerReference is not None:
            section.footer._sectPr.add_footerReference(
                footer._hdrftr_index,
                footerReference.rId
            )
        section.footer_distance = ctx.composer.doc.sections[-1].footer_distance
