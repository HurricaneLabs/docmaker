import json
import os
import time

import dateutil.parser
import jinja2

from docmaker.hooks import Hook


class Environment(jinja2.Environment):
    def add_filter(self, func, filter_name=None):
        if filter_name is None:
            filter_name = func.__name__
            if filter_name.startswith("jinja2_"):
                filter_name = filter_name[7:]
        if filter_name in self.filters:
            raise KeyError(filter_name)
        self.filters[filter_name] = func


class JinjaTemplate:
    __jinja_filters = {}

    @Hook("pre_generate_srcfile",
          jinja_context=lambda _: dict(),
          predicate=lambda ctx: "jinja_template.template_file" in ctx)
    def initialize_jinja_context(self, ctx):
        ctx.jinja_env = Environment(trim_blocks=True, lstrip_blocks=True)

        for filter in self.__jinja_filters:
            ctx.jinja_env.filters[filter] = self.__jinja_filters[filter]

        with open(ctx.srcfile, "r") as f:
            if ctx.srcfile_format == "json":
                ctx.jinja_context.update(json.load(f))
            else:
                ctx.jinja_context.update({"contents": f.read()})

        if os.path.exists(ctx["jinja_template.template_file"]):
            ctx.jinja_template_file = ctx["jinja_template.template_file"]
        elif ctx.file_exists_in_temp_dir(ctx["jinja_template.template_file"]):
            ctx.jinja_template_file = os.path.join(ctx.tmpdir, ctx["jinja_template.template_file"])
        else:
            ctx.jinja_template_file = None

    @Hook("pre_collect_metadata",
          before=["MarkdownMetadata"],
          predicate=lambda ctx: getattr(ctx, "jinja_template_file"))
    def generate_srcfile(self, ctx):
        with open(ctx.jinja_template_file, "r") as f:
            template = ctx.jinja_env.from_string(f.read())

        file_format = ctx.get("jinja_template.output_file_extension") or "md"

        ctx.srcfile = ctx.get_temp_file(suffix=f".{file_format}")

        with open(ctx.srcfile, "w") as f:
            f.write(template.render(**ctx.jinja_context))

    @classmethod
    def add_filter(cls, func, filter_name=None):
        if filter_name is None:
            filter_name = func.__name__
            if filter_name.startswith("jinja2_"):
                filter_name = filter_name[7:]
        if filter_name in cls.__jinja_filters:
            raise KeyError(filter_name)
        cls.__jinja_filters[filter_name] = func

    @classmethod
    def jinja_filter(cls, f):
        cls.add_filter(f)
        return f


@JinjaTemplate.jinja_filter
def jinja2_asciify(str):
    asciify_ok = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#' \
                 '$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    s2 = []
    for char in str:
        if char in asciify_ok:
            s2.append(char)
        else:
            s2.append(".")
    return "".join(s2)


@JinjaTemplate.jinja_filter
def jinja2_dictprint(d):
    return "\n".join(["%s: %s" % (k, v) for (k, v) in d.items()])


@JinjaTemplate.jinja_filter
def jinja2_formatdate(date, format):
    date = dateutil.parser.parse(date)
    native = date.replace(tzinfo=None)
    return native.strftime(format)


@JinjaTemplate.jinja_filter
def jinja2_hasattr(obj, attr):
    return hasattr(obj, attr)


@JinjaTemplate.jinja_filter
def jinja2_json(d):
    return json.dumps(d)


@JinjaTemplate.jinja_filter
def jinja2_pluralize(n, singular="", plural="s"):
    return singular if n == 1 else plural


@JinjaTemplate.jinja_filter
def jinja2_strftime(ts, fmt="%b %-d, %Y, %-I:%M %p"):
    return time.strftime(fmt, time.gmtime(ts))
