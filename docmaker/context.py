import os
import tempfile
from collections import OrderedDict

from .features import load_feature
from .options import flatten, option_is_false, option_is_true


class Context:
    _output_file = None
    _reference_doc = None
    _srcfile_format = None
    _tmpdir = None
    __tempfiles = None

    def __init__(self, docmaker, srcfile, output_file, features=None, options=None):
        self.timing = OrderedDict()

        self.docmaker = docmaker
        self.srcfile = srcfile

        self.features = []
        self._features = []
        self.options = {}

        if self.docmaker:
            self.add_features(self.docmaker.features)
            self.options.update(self.docmaker.options)

        if features:
            self.add_features(features)
        if options:
            self.options.update(options)

        # self.features = [feature() for feature in self._features]

        self._output_file = output_file

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cleanup_tmpdir()

    def add_feature(self, feature):
        if isinstance(feature, (bytes, str)):
            feature = load_feature(feature)

        self._features.append(feature)
        self.features.append(feature())

    def add_features(self, features):
        for feature in features:
            self.add_feature(feature)

    def file_exists_in_temp_dir(self, filename):
        if self._tmpdir is None:
            return False
        return os.path.exists(os.path.join(self.tmpdir, filename))

    def get_temp_file(self, *args, content=None, **kwargs):
        fd, tmpfile = tempfile.mkstemp(*args, dir=self.tmpdir, **kwargs)

        self.__tempfiles.append(fd)

        if content:
            with open(tmpfile, "wb") as f:
                if hasattr(content, "encode"):
                    content = content.encode()
                f.write(content)

        return tmpfile

    def setup_tmpdir(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.__tempfiles = []

    def cleanup_tmpdir(self):
        if self.__tempfiles:
            for fd in self.__tempfiles:
                os.close(fd)

            self.__tempfiles = []

        if self._tmpdir:
            self._tmpdir.cleanup()
            self._tmpdir = None

    def get_options(self, feature):
        # return [(k, v) for (k, v) in self.options.get(feature, {}).items()]
        opts = []
        for k in self.options:
            if k.startswith(f"{feature}."):
                key = k.replace(f"{feature}.", "")
                opts.append((key, self.options[k]))
        return opts

    def get(self, opt):
        try:
            return self[opt]
        except KeyError:
            return None

    def get_as_boolean(self, opt, default=None):
        value = self.get(opt)
        if value is None and default is not None:
            return default
        elif option_is_false(value):
            return False
        elif option_is_true(value):
            return True
        raise ValueError(f"{opt}: {value} is neither true nor false")

    def __getitem__(self, opt):
        return self.options[opt]

    def __setitem__(self, opt, value):
        self.options[opt] = flatten(value, parent=opt)

    def __contains__(self, other):
        try:
            self[other]
        except KeyError:
            return False
        else:
            return True

    @property
    def finalized(self):
        if self.output_format == "md":
            return self.srcfile
        elif self.output_format == "docx":
            return self.finalized_docx
        else:
            return self.finalized_pdf

    @property
    def output_file(self):
        if self._output_file:
            return self._output_file

        try:
            srcfilebase, _ = self.srcfile.rsplit(".", 1)
        except ValueError:
            srcfilebase = self.srcfile

        return os.path.basename(f"{srcfilebase}.{self.output_format}")

    @output_file.setter
    def output_file(self, value):
        self._output_file = value

    @property
    def output_format(self):
        return self.get("output") or "pdf"

    @property
    def reference_doc(self):
        if self._reference_doc:
            return self._reference_doc
        if "reference" not in self:
            return None

        reference = self.get("reference")

        if os.path.exists(reference):
            return reference
        elif self.file_exists_in_temp_dir(reference):
            return os.path.join(self.temp_dir, reference)
        else:
            return None

    @reference_doc.setter
    def reference_doc(self, value):
        self._reference_doc = value

    @property
    def srcfile_format(self):
        if self._srcfile_format:
            return self._srcfile_format
        elif "srcfile_format" in self:
            return self["srcfile_format"]
        elif "." in self.srcfile:
            return self.srcfile.rsplit(".", 1)[1]

        return "md"

    @srcfile_format.setter
    def srcfile_format(self, value):
        self._srcfile_format = value

    @property
    def tmpdir(self):
        return self._tmpdir.name if self._tmpdir else None
