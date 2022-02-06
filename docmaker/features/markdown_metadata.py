import frontmatter

from docmaker.hooks import Hook


class MarkdownMetadata:
    @Hook("pre_collect_metadata", predicate=lambda ctx: ctx.srcfile_format == "md")
    def parse_frontmatter(self, ctx):
        with open(ctx.srcfile, "rb") as f:
            src = f.read().decode("utf-8")

        try:
            markdown_metadata, _ = frontmatter.parse(src)
        except:
            return
        else:
            ctx.metadata.update(markdown_metadata)
