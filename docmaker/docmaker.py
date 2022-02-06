import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterable
from functools import wraps

import frontmatter
import pypandoc
from docxcompose.composer import Composer
from docx import Document
from toposort import toposort_flatten

from .context import Context
from .features import FeatureNotFound, load_feature
from .hacks import load_hacks
from .hooks import Hook, StopProcessing


class Docmaker:
    def __init__(self, features=None, options=None):
        self.features = list(map(load_feature, features or []))
        self.options = options or {}  # Options()

    def get_context(self, srcfile, output_file=None, **kwargs):
        return Context(self, srcfile, output_file, **kwargs)

    def __call__(self, srcfile, output_file=None):
        with self.get_context(srcfile, output_file) as ctx:
            try:
                self.initialize(ctx)

                self.setup_tmpdir(ctx)
                self.collect_metadata(ctx)

                if ctx.output_format != "md":
                    self.convert_to_docx(ctx)
                    self.save_docx(ctx)
                    self.finalize_docx(ctx)

                    if ctx.output_format != "docx":
                        self.convert_to_pdf(ctx)
                        self.finalize_pdf(ctx)

                self.finalize(ctx)
            except StopProcessing as e:
                pass
            self.cleanup_tmpdir(ctx)
            return ctx.output_file

    @Hook()
    def initialize(self, ctx):
        pass

    @Hook()
    def setup_tmpdir(self, ctx):
        ctx.setup_tmpdir()

    @Hook(metadata=lambda _: dict())
    def collect_metadata(self, ctx):
        if "metadata" in ctx:
            ctx.metadata.update(ctx["metadata"])

    @Hook(docxfile=lambda ctx: ctx.get_temp_file(suffix=".docx"))
    def convert_to_docx(self, ctx):
        if ctx.srcfile is None:
            raise ValueError("No sourcefile provided")

        self.get_pypandoc_kwargs(ctx)

        pypandoc.convert_file(
            ctx.srcfile,
            outputfile=ctx.docxfile,
            **ctx.pypandoc_kwargs
        )

        self.get_src_document(ctx)
        self.get_composer(ctx)

    @Hook(pypandoc_kwargs=lambda _: dict())
    def get_pypandoc_kwargs(self, ctx):
        self.get_pandoc_extra_args(ctx)

        if ctx.get("pandoc_format"):
            ctx.pypandoc_kwargs["format"] = ctx["pandoc_format"]
        elif ctx.srcfile_format:
            ctx.pypandoc_kwargs["format"] = ctx.srcfile_format

        ctx.pypandoc_kwargs.update({
            "to": "docx",
            "sandbox": False,
            "extra_args": ctx.pandoc_extra_args
        })

    @Hook(pandoc_extra_args=lambda _: list())
    def get_pandoc_extra_args(self, ctx):
        if ctx.reference_doc:
            ctx.pandoc_extra_args.append(f"--reference-doc={ctx.reference_doc}")

        if "pandoc.extra_args" in ctx:
            ctx.pandoc_extra_args.extend(ctx["pandoc.extra_args"])

    @Hook()
    def get_src_document(self, ctx):
        ctx.src_doc = Document(ctx.docxfile)

    @Hook()
    def get_composer(self, ctx):
        ctx.composer = Composer(ctx.src_doc)
        ctx.src_section = ctx.composer.doc.sections[0]

    @Hook(docxfile=lambda ctx: ctx.get_temp_file(suffix=".docx"))
    def save_docx(self, ctx):
        ctx.composer.save(ctx.docxfile)

    @Hook(finalized_docx=lambda ctx: ctx.get_temp_file(suffix=".docx"))
    def finalize_docx(self, ctx):
        shutil.copyfile(ctx.docxfile, ctx.finalized_docx)

    @Hook(pdffile=lambda ctx: ctx.get_temp_file(suffix=".pdf"))
    def convert_to_pdf(self, ctx):
        unoconv_args = []
        unoconv_kwargs = {}

        verbose = int(ctx.get("unoconv.verbosity") or 0)
        retries = int(ctx.get("unoconv.retries") or 3)

        if verbose > 0:
            verbose = "v" * min(verbose, 3)
            unoconv_args.append(f"-{verbose}")
            unoconv_kwargs.update({
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
            })
        else:
            unoconv_kwargs.update({
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            })

        tries = 0
        while tries < retries:
            cpe = None
            try:
                subprocess.run(
                    [
                        shutil.which("unoconv"),
                        "-f", ctx.output_format,
                        "-o", ctx.pdffile,
                        *unoconv_args,
                        ctx.finalized_docx
                    ],
                    check=True,
                    **unoconv_kwargs
                )
            except subprocess.CalledProcessError as cpe:
                tries += 1
            else:
                break

        if cpe is not None:
            raise cpe

    @Hook(finalized_pdf=lambda ctx: ctx.get_temp_file(suffix=".pdf"))
    def finalize_pdf(self, ctx):
        shutil.copyfile(ctx.pdffile, ctx.finalized_pdf)

    @Hook()
    def cleanup_tmpdir(self, ctx):
        ctx.cleanup_tmpdir()

    @Hook()
    def finalize(self, ctx):
        shutil.copyfile(ctx.finalized, ctx.output_file)

        try:
            print(json.dumps(ctx.timing), file=sys.stderr)
        except BrokenPipeError:
            pass
