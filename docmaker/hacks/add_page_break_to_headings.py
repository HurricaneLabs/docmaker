import re

from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.shared import qn
# from docx.oxml.text.parfmt import CT_PPr
# from docx.oxml.xmlchemy import ZeroOrOne

from docmaker.hooks import Hook
from docmaker.oxml import OxmlElement


# CT_PPr.outlineLvl = ZeroOrOne("w:outlineLvl")


@Hook("pre_save_docx")
def add_page_break_to_headings(ctx):
    heading_levels_with_break = ctx.get("hacks.page_break_before_headings") or [1]

    for heading_style in ctx.composer.doc.styles:
        if not heading_style.type == WD_STYLE_TYPE.PARAGRAPH:
            continue

        m = re.match(r"^Heading (\d+)$", heading_style.name)
        if not m:
            continue

        heading_level = int(m.groups()[0])

        if heading_level in heading_levels_with_break:
            heading_style.paragraph_format.page_break_before = True

            new_style_name = f"{heading_style.name} - No Break"
            if new_style_name in ctx.composer.doc.styles:
                ctx.composer.doc.styles[new_style_name].delete()

            new_style = ctx.composer.doc.styles.add_style(
                new_style_name,
                WD_STYLE_TYPE.PARAGRAPH
            )

            new_style.base_style = heading_style
            new_style.paragraph_format.page_break_before = False
        else:
            heading_style.paragraph_format.page_break_before = False

            new_style_name = f"{heading_style.name} - With Break"
            if new_style_name in ctx.composer.doc.styles:
                ctx.composer.doc.styles[new_style_name].delete()

            new_style = ctx.composer.doc.styles.add_style(
                new_style_name,
                WD_STYLE_TYPE.PARAGRAPH
            )

            new_style.base_style = heading_style
            new_style.paragraph_format.page_break_before = True

        pPr = new_style._element.get_or_add_pPr()

        with OxmlElement("w:outlineLvl", append_to=pPr) as outlineLvl:
            outlineLvl.set(qn("w:val"), str(heading_level - 1))
