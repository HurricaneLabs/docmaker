from contextlib import contextmanager

from docx.oxml.shared import OxmlElement as _OxmlElement


@contextmanager
def OxmlElement(nsptag_str, attrs=None, nsdecls=None, append_to=None, next_to=None):
    _element = _OxmlElement(nsptag_str, attrs, nsdecls)

    yield _element

    if append_to is not None:
        append_to.append(_element)
    if next_to is not None:
        next_to.addnext(_element)
