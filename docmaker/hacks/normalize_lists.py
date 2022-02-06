from docx import Document

from docmaker.hooks import Hook


@Hook("pre_finalize_docx")
def normalize_lists(ctx):
    d = Document(ctx.docxfile)

    for p in d.paragraphs:
        if p._p.find("./{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr/{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr") is None:
            continue
        pPr = p._p.get_or_add_pPr()
        numPr = pPr.get_or_add_numPr()
        ilvl = numPr.get_or_add_ilvl().val

        if ilvl == 0:
            style_name = "List Bullet"
        elif ilvl < 4:
            style_name = "List Bullet %s" % (ilvl + 1)
        else:
            style_name = "List Bullet 5"

        if style_name not in d.styles:
            continue

        # numId = numPr.get_or_add_numId()
        # numPr.remove(numId)
        pPr.remove(numPr)
        p.style = d.styles[style_name]

    d.save(ctx.docxfile)
