#!/usr/bin/env python3

import io
import os
import re
import tempfile
import zipfile
from contextlib import contextmanager

import requests


@contextmanager
def zipopen(font_file):
    if "://" in font_file:
        r = requests.get(font_file.format(**os.environ))
        r.raise_for_status()
        fo = io.BytesIO(r.content)
    else:
        fo = open(font_file, "rb")

    with zipfile.ZipFile(fo, "r") as zf:
        yield zf

    fo.close()


env_config = []

if "DOCMAKER_INSTALL_FONT" in os.environ:
    env_config.append((-1, os.environ["DOCMAKER_INSTALL_FONT"]))

for envvar in os.environ:
    m = re.match(r"^DOCMAKER_INSTALL_FONT(\d+)$", envvar)
    if not m:
        continue
    env_config.append((m.groups()[0], os.environ[envvar]))

env_config.sort(key=lambda config: config[0])

for (_, font_file) in env_config:
    count = 0
    try:
        with zipopen(font_file) as zf:
            for zi in zf.infolist():
                if not zi.filename.lower().endswith(".ttf"):
                    continue
                filename = os.path.basename(zi.filename)

                with open(os.path.join("/usr/local/share/fonts", filename), "wb") as ff:
                    count += 1
                    ff.write(zf.read(zi))
    except:
        print(f"Failed to install fonts from {font_file}")
    else:
        print(f"Successfully installed {count} fonts from {font_file}")
