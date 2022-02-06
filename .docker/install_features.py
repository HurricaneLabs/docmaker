#!/usr/bin/env python3

import os
import re
import subprocess
import tempfile
from urllib.parse import urlparse, urlunparse

import requests
from docmaker.features.remote_files import RemoteFiles


env_config = []

for envvar in os.environ:
    m = re.match(r"^DOCMAKER_INSTALL_(FEATURE|PIP|WHEEL)(\d+)$", envvar)
    if not m:
        continue

    install_type, idx = m.groups()

    install_type = {
        "PIP": 0,
    }.get(install_type, 50)

    env_config.append((idx, install_type, os.environ[envvar]))


env_config.sort(key=lambda config: (config[1], config[0]))

with tempfile.TemporaryDirectory() as tmpdir:
    rf = RemoteFiles()

    for _, install_type, requirement in env_config:
        pip_req = requirement

        if "://" in requirement:
            parsed = urlparse(requirement)

            if parsed.password:
                auth, netloc = parsed.netloc.rsplit("@", 1)
                username, password = auth.split(":", 1)
                netloc = f"{username}:****@{netloc}"
            else:
                netloc = parsed.netloc

            requirement = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))

        if install_type == "WHEEL":
            content, filename = rf._get_remote_file_http(ctx=None, src=pip_req)

            if content is None:
                print(f"Failed to download {requirement}")

            pip_req = os.path.join(tmpdir, filename)

            with open(pip_req, "wb") as f:
                f.write(content)

        result = subprocess.run(
            f"pip install {pip_req}",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
        )

        if result.returncode != 0:
            print(f"Failed to install {requirement}")
            print("-" * 80)
            print(result.stdout.decode())
            print("-" * 80)
        else:
            print(f"Successfully installed {requirement}")
