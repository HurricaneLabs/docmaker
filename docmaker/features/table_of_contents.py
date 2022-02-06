from contextlib import contextmanager
from multiprocessing import context

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.shared import qn

from docmaker.hooks import Hook
from docmaker.options import option_is_false
from docmaker.oxml import OxmlElement


class TableOfContents:
    @Hook("post_collect_metadata", predicate=(
        lambda ctx: ctx.get_as_boolean("toc.settings_in_metadata", True),
    ))
    def read_toc_settings_from_metadata(self, ctx):
        if "toc" in ctx.metadata and option_is_false(ctx.metadata["toc"]):
            ctx["toc.disabled_by_metadata"] = True
            return
        ctx["toc.disabled_by_metadata"] = False

        for key in ("title_text", "title_style", "depth"):
            if f"toc_{key}" not in ctx.metadata:
                continue
            ctx[f"toc.{key}"] = ctx.metadata[f"toc_{key}"]

    @Hook("post_convert_to_docx", before=["Coverpage"], predicate=(
        lambda ctx: not ctx.get_as_boolean("toc.disabled_by_metadata"),
    ))
    def insert_table_of_contents(self, ctx):
        toc_title_text = ctx.get("toc.title_text") or "Table of Contents"
        toc_title_style = ctx.get("toc.title_style") or "TOC Heading"
        toc_depth = int(ctx.get("toc.depth") or 3)

        # ---

        ctx.toc_doc = Document()

        if toc_title_style not in ctx.toc_doc.styles:
            ctx.toc_doc.styles.add_style(toc_title_style, WD_STYLE_TYPE.PARAGRAPH)

        pPr = ctx.toc_doc.styles[toc_title_style]._element.get_or_add_pPr()

        with OxmlElement("w:outlineLvl", append_to=pPr) as outlineLvl:
            outlineLvl.set(qn("w:val"), "9")

        toc_p = ctx.toc_doc.add_paragraph(text=toc_title_text, style=toc_title_style)

        with OxmlElement("w:sdt", next_to=toc_p._element) as w_sdt:
            with OxmlElement("w:sdtPr", append_to=w_sdt) as w_sdtPr:
                with OxmlElement("w:docPartObj", append_to=w_sdtPr) as w_docPartObj:
                    with OxmlElement("w:docPartGallery", append_to=w_docPartObj) as w_docPartGallery:
                        w_docPartGallery.set(qn("w:val"), "Table of Contents")
                    with OxmlElement("w:docPartUnique", append_to=w_docPartObj) as w_docPartUnique:
                        w_docPartUnique.set(qn("w:val"), "true")
            with OxmlElement("w:sdtContent", append_to=w_sdt) as w_sdtContent:
                with OxmlElement("w:p", append_to=w_sdtContent) as w_p:
                    with OxmlElement("w:r", append_to=w_p) as w_r:
                        with OxmlElement("w:fldChar", append_to=w_r) as w_fldChar_begin:
                            w_fldChar_begin.set(qn("w:fldCharType"), "begin")
                            w_fldChar_begin.set(qn("w:dirty"), "true")
                    with OxmlElement("w:r", append_to=w_p) as w_r:
                        with OxmlElement("w:instrText", append_to=w_r) as w_instrText:
                            w_instrText.set(qn("xml:space"), "preserve")
                            w_instrText.text = r' TOC \z \o "1-%s" \u \h ' % toc_depth
                    with OxmlElement("w:r", append_to=w_p) as w_r:
                        with OxmlElement("w:fldChar", append_to=w_r) as w_fldChar_separate:
                            w_fldChar_separate.set(qn("w:fldCharType"), "separate")
                with OxmlElement("w:p", append_to=w_sdtContent) as w_p:
                    with OxmlElement("w:r", append_to=w_p) as w_r:
                        with OxmlElement("w:fldChar", append_to=w_r) as w_fldChar_end:
                            w_fldChar_end.set(qn("w:fldCharType"), "end")

        # ---

        ctx.toc_doc.add_section(WD_SECTION.NEW_PAGE)
        ctx.composer.insert(0, ctx.toc_doc)
        ctx.toc_section = ctx.composer.doc.sections[0]

    @Hook("pre_save_docx")
    def fix_toc_heading_outline_level(self, ctx):
        toc_title_style = ctx.get("toc.title_style") or "TOC Heading"

        pPr = ctx.composer.doc.styles[toc_title_style]._element.get_or_add_pPr()

        with OxmlElement("w:outlineLvl", append_to=pPr) as outlineLvl:
            outlineLvl.set(qn("w:val"), "9")
