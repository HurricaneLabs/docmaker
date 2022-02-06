import os
import sys
import tempfile
import uuid
import zipfile
from collections import Iterable

import requests
from defusedxml.lxml import fromstring
from lxml import etree

from docmaker.hooks import Hook


def obfuscateTtf(fontstream, guid):
    outstream = bytearray(fontstream)
    _guid = uuid.UUID(guid)

    for idx, gbyte in enumerate(reversed(_guid.bytes * 2)):
        outstream[idx] ^= gbyte

    return bytes(outstream)


class EmbedFonts:
    @Hook("post_finalize_docx", predicate=(
        lambda ctx: ctx.output_format == "docx",
        lambda ctx: ctx.get_options("embed_fonts.fonts"),
    ))
    def embed_fonts(self, ctx):
        font_dirs = ctx.get("embed_fonts.font_dir")

        if font_dirs and not isinstance(font_dirs, Iterable):
            font_dirs = [font_dirs]

        if not font_dirs:
            font_dirs = []

            if sys.platform in ("linux", "cygwin"):
                font_dirs.extend([
                    "/usr/share/fonts/truetype",
                    "/usr/local/share/fonts/"
                ])
            elif sys.platform == "darwin":
                font_dirs.extend([
                    "/System/Library/Fonts",
                    "/Library/Fonts",
                    os.path.expanduser("~/Library/Fonts")
                ])

        font_dirs = filter(os.path.exists, font_dirs)

        with tempfile.TemporaryDirectory(dir=ctx.tmpdir) as tmpdir:
            with zipfile.ZipFile(ctx.finalized_docx) as zf:
                zf.extractall(tmpdir)

            try:
                os.makedirs(os.path.join(tmpdir, "word", "fonts"))
            except:
                pass

            # Helpers for XML prefixes
            r = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
            w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

            # Update word/fontTable.xml and word/_rels/fontTable.xml.rels
            with open(os.path.join(tmpdir, "word", "fontTable.xml"), "rb") as f:
                fontTable = fromstring(f.read())

            fontTableRels = etree.Element("Relationships", xmlns="http://schemas.openxmlformats.org/package/2006/relationships")

            rId = 1
            for font_name, font_file in ctx.get_options("embed_fonts.fonts"):
                font_name, font_style = font_name.split(".", 1)
                if "://" in font_file:
                    font_url, font_file = font_file, ctx.get_temp_file(suffix=".ttf")

                    r = requests.get(font_url)
                    r.raise_for_status()

                    with open(font_file, "wb") as f:
                        f.write(r.content)

                font_path = None
                if os.path.exists(font_file):
                    font_path = font_file
                else:
                    for font_dir in font_dirs:
                        fp = os.path.join(font_dir, font_file)
                        if os.path.exists(fp):
                            font_path = fp
                            break

                if font_path is None:
                    continue

                elem = fontTable.find(f"w:font[@w:name='{font_name}']", namespaces=fontTable.nsmap)
                guid = str(uuid.uuid4()).upper()

                # Add it to fontTable.xml.rels
                rel = etree.SubElement(fontTableRels, "Relationship")
                rel.attrib["Id"] = f"rId{rId}"
                rel.attrib["Type"] = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
                rel.attrib["Target"] = f"fonts/font{rId}.odttf"

                # Update fontTable.xml
                embed = etree.SubElement(elem, f"{w}embed{font_style}", nsmap=fontTable.nsmap)
                embed.attrib[f"{r}id"] = f"rId{rId}"
                embed.attrib[f"{w}fontKey"] = "{%s}" % guid

                # Copy the font to word/fonts
                outpath = os.path.join(tmpdir, "word", "fonts", f"font{rId}.odttf")
                with open(font_path, "rb") as f:
                    ttf = f.read()
                with open(outpath, "wb") as f:
                    f.write(obfuscateTtf(ttf, guid))

                # Increment rId
                rId += 1

            with open(os.path.join(tmpdir, "word", "fontTable.xml"), "wb") as f:
                f.write(etree.tostring(fontTable, encoding="utf-8", standalone="yes"))
            with open(os.path.join(tmpdir, "word", "_rels", "fontTable.xml.rels"), "wb") as f:
                f.write(etree.tostring(fontTableRels, encoding="utf-8", standalone="yes"))

            # Update [Content_Types].xml
            with open(os.path.join(tmpdir, "[Content_Types].xml"), "rb") as f:
                ContentTypes = fromstring(f.read())

            ttf = etree.SubElement(ContentTypes, "Default")
            ttf.attrib["Extension"] = "odttf"
            ttf.attrib["ContentType"] = "application/vnd.openxmlformats-officedocument.obfuscatedFont"

            with open(os.path.join(tmpdir, "[Content_Types].xml"), "wb") as f:
                f.write(etree.tostring(ContentTypes, encoding="utf-8", standalone="yes"))

            # Update word/settings.xml
            with open(os.path.join(tmpdir, "word/settings.xml"), "rb") as f:
                Settings = fromstring(f.read())

            etree.SubElement(Settings, f"{w}embedTrueTypeFonts")

            with open(os.path.join(tmpdir, "word/settings.xml"), "wb") as f:
                f.write(etree.tostring(Settings, encoding="utf-8", standalone="yes"))

            ctx.finalized_docx = ctx.get_temp_file(suffix=".docx")

            with zipfile.ZipFile(ctx.finalized_docx, "w") as zf:
                def addToZip(path, zippath):
                    if os.path.isfile(path):
                        zf.write(path, zippath, zipfile.ZIP_DEFLATED)
                    elif os.path.isdir(path):
                        if zippath:
                            zf.write(path, zippath)
                        for nm in sorted(os.listdir(path)):
                            addToZip(os.path.join(path, nm), os.path.join(zippath, nm))
                addToZip(tmpdir, "")
