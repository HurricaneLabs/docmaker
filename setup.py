import os
from setuptools import find_packages, setup

import versioneer


readMeFile = os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.md")

if os.path.exists(readMeFile):
    with open(readMeFile, encoding="utf-8") as readMeFile:
        long_description = readMeFile.read()
else:
    long_description = ""

setup(
    name="docmaker",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="Steve McMaster",
    author_email="mcmaster@hurricanelabs.com",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    url="https://github.com/HurricaneLabs/docmaker",
    description="A PDF generator",
    long_description=long_description,
    install_requires=[
        "boto3",
        "defusedxml",
        "docx-mailmerge",
        "docxcompose",
        "falcon",
        "jinja2",
        "multipart",
        "python-dateutil",
        "python-frontmatter",
        # "pypandoc",
        "pypandoc @ git+https://github.com/mcm/pypandoc#egg=pypandoc",
        "requests",
        "ruamel.yaml",
        "toposort",
        "werkzeug"
    ],
    entry_points={
        "console_scripts": [
            "docmaker = docmaker:main",
        ]
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Development Status :: 5 - Production/Stable",
    ],
    bugtrack_url="https://github.com/HurricaneLabs/docmaker/issues",
)
