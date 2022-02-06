import os
import subprocess
import sys
import tempfile
import uuid
import zipfile
from collections import Iterable

import requests
from defusedxml.lxml import fromstring
from lxml import etree
from pypandoc import get_pandoc_path

from docmaker.hooks import Hook


THEME_COLORS = (
    "dk1",
    "lt1",
    "dk2",
    "lt2",
    "accent1",
    "accent2",
    "accent3",
    "accent4",
    "accent5",
    "accent6",
    "hlink",
    "folHlink",
)


class Theme:
    @Hook("pre_convert_to_docx", predicate=(
        lambda ctx: ctx.get_options("theme")
    ))
    def update_theme_xml(self, ctx):
        if ctx.reference_doc is None:
            ctx._reference_doc = ctx.get_temp_file(suffix=".docx")

            subprocess.run(
                [
                    get_pandoc_path(),
                    "-o", ctx.reference_doc,
                    "--print-default-data-file", "reference.docx"
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        with tempfile.TemporaryDirectory(dir=ctx.tmpdir) as tmpdir:
            with zipfile.ZipFile(ctx.reference_doc) as zf:
                zf.extractall(tmpdir)

            styles_xml_file = os.path.join(tmpdir, "word", "styles.xml")
            theme_xml_file = os.path.join(tmpdir, "word", "theme", "theme1.xml")

            if not os.path.exists(theme_xml_file):
                return

            with open(styles_xml_file, "rb") as f:
                styles_xml = fromstring(f.read())
            with open(theme_xml_file, "rb") as f:
                theme_xml = fromstring(f.read())

            clrScheme = theme_xml.find("a:themeElements/a:clrScheme", namespaces=theme_xml.nsmap)

            for color in THEME_COLORS:
                if f"theme.color_{color}" not in ctx:
                    continue

                colorValue = ctx[f"theme.color_{color}"]

                clr = clrScheme.find(f"a:{color}", namespaces=theme_xml.nsmap)

                if clr is None:
                    raise ValueError(f"{color} is invalid")

                if color in ("dk1", "lt1"):
                    clr = clr.find("a:sysClr", namespaces=theme_xml.nsmap)
                    attribute_name = "lastClr"
                else:
                    clr = clr.find("a:srgbClr", namespaces=theme_xml.nsmap)
                    attribute_name = "val"

                clr.attrib[attribute_name] = colorValue

                for style in styles_xml.findall("w:style", namespaces=styles_xml.nsmap):
                    clr = style.find("w:rPr/w:color", namespaces=styles_xml.nsmap)
                    if clr is None:
                        continue
                    if clr.get(etree.QName(styles_xml.nsmap["w"], "themeColor")) != color:
                        continue
                    clr.set(etree.QName(styles_xml.nsmap["w"], "val"), colorValue)

            fontScheme = theme_xml.find("a:themeElements/a:fontScheme", namespaces=theme_xml.nsmap)

            if "theme.major_font" in ctx:
                latinFont = fontScheme.find("a:majorFont/a:latin", namespaces=theme_xml.nsmap)
                latinFont.attrib["typeface"] = ctx["theme.major_font"]

            if "theme.minor_font" in ctx:
                latinFont = fontScheme.find("a:minorFont/a:latin", namespaces=theme_xml.nsmap)
                latinFont.attrib["typeface"] = ctx["theme.minor_font"]

            with open(styles_xml_file, "wb") as f:
                f.write(etree.tostring(styles_xml, encoding="utf-8", standalone="yes"))
            with open(theme_xml_file, "wb") as f:
                f.write(etree.tostring(theme_xml, encoding="utf-8", standalone="yes"))

            ctx._reference_doc = ctx.get_temp_file(suffix=".docx")

            with zipfile.ZipFile(ctx.reference_doc, "w") as zf:
                def addToZip(path, zippath):
                    if os.path.isfile(path):
                        zf.write(path, zippath, zipfile.ZIP_DEFLATED)
                    elif os.path.isdir(path):
                        if zippath:
                            zf.write(path, zippath)
                        for nm in sorted(os.listdir(path)):
                            addToZip(os.path.join(path, nm), os.path.join(zippath, nm))
                addToZip(tmpdir, "")
