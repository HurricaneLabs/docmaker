docmaker - A PDF generator
==========================

docmaker is a utility for converting text in a variety of formats into a PDF. It
utilizes other open-source tools under the hood, such as pandoc, LibreOffice,
and unoconv.

## Installation

docmaker can be installed using pip3:

    pip3 install docmaker

Or, if you're feeling adventurous, can be installed directly from github:

    pip3 install git+https://github.com/HurricaneLabs/docmaker.git

## Usage

### Common Terms

* **feature** - A docmaker **feature** contains one-or-more optional steps that
  will be executed during document conversion. **Features** are _disabled_ by
  default, and must be enabled to use them.
* **hack** - A docmaker **hack** also contains one-or-more optional steps that
  will be executed during document conversion. Unlike **features**, **hacks**
  are _enabled_ by default, and are generally used to perform "fixup" tasks that
  may be necessary due to oddities of document conversion. As an example,
  docmaker includes a **hack** that will ensure margin settings are copied from
  the reference document into any additional sections that are generated, such
  as a coverpage or a table of contents.
* **reference doc** - The **reference doc** is used by pandoc under the hood to
  apply styles to the generated document. More information can be found
  [here](https://pandoc.org/MANUAL.html#option--reference-doc).
* **metadata** - **Metadata** is available for use by **features** as they do
  their work. Metadata may include title, author, or date information about the
  document.
* **options** - **Options** control the behavior of **features** and **hacks**.
  See below for the **options** available for each bundled **feature** and
  **hack**.

### Command Line Usage

```
usage: docmaker [-h] [-F FEATURES] [-O OUTPUT_FORMAT] [-R REFERENCE] [-m METADATA] [-o OPTIONS] srcfile [outfile]

positional arguments:
  srcfile
  outfile

optional arguments:
  -h, --help            show this help message and exit
  -F FEATURES, --feature FEATURES
  -O OUTPUT_FORMAT, --output-format OUTPUT_FORMAT
  -R REFERENCE, --reference REFERENCE
  -m METADATA, --metadata METADATA
  -o OPTIONS, --option OPTIONS
```

`docmaker` can be run as a command-line tool for one-off document generation.
The `-o` option can be used to specify a json or yaml file containing options,
which is useful for specifying a set of common options to be used multiple times.
To do this, give the path to the json or yaml file, prefixed with `@`. If the
file is yaml, you must also specify that, as `@yaml:`.

### API Usage

TODO

### Docker Usage

There is an official docmaker docker image on hub.docker.com and on ghcr.io.
This docker image contains everything you need to run docmaker, either in a
one-off way or as an API.

To use the image for one-off conversions, you can run it like so:

    docker run --rm -v /path/on/host:/data -w /data hurricanelabs/docmaker docmaker ...

Which takes the same arguments as the CLI usage above. In addition to the
environment variables supported by the API, there are two special sets of
variables that can be used with the docker container:

* `DOCMAKER_INSTALL_FEATURE` - Using this variable (or numbered variables such
  as `DOCMAKER_INSTALL_FEATURE1`), you can install external features that you
  wish to make available. The value of these variables is passed to `pip` in
  the container.
* `DOCMAKER_INSTALL_WHEEL` - Using this variable (or numbered variables such
  as `DOCMAKER_INSTALL_WHEEL1`), you can install external features that you
  wish to make available. The value should be a path to a local or remote
  `.whl` file.
* `DOCMAKER_INSTALL_FONT` - Using this variable (or numbered variables such as
  `DOCMAKER_INSTALL_FONT1`), you can install additional fonts for use in your
  documents. The value of these variables should be either a local filesystem
  path, or a requests-compatible URL, that points to a zipfile containing one
  or more ttf files. These files can be in any nested structure. For example,
  `DOCMAKER_INSTALL_FONT=https://fonts.google.com/download?family=Roboto` will
  install the Roboto font family from Google fonts.

The API is available via HTTP on port 8080 and via HTTPS on port 8443. If you do
not provide a certificate and key in one of the following ways, a cert and key
will be generated the first time the container starts:

* You can mount a cert and key into the container at `/config/uwsgi.crt` and
  `/config/uwsgi.key` respectively. You must provide both, and they will be
  copied into place. They will be copied each time the container starts.
* You can mount a cert and key into the container at locations of your choosing
  and set the `DOCMAKER_SSL_CERT` and `DOCMAKER_SSL_KEY` environment variables
  to those locations, respectively.

## Core Features and Hacks

### Features

#### Coverpage

The **Coverpage** feature uses a docx file configured with mail merge fields in
order to generate a coverpage. These fields are user-defined, and may be pulled
either from the **options** or from the **metadata**. Options for his feature
are:

* `coverpage.template` - The docx file used as a template for creating the
  coverpage.
* `coverpage.FIELD` - Additional options may be specified (such as
  `coverpage.title`) that will be used in the mail merge operation.

#### DocumentHeader

The **DocumentHeader** feature is used to insert additional information at the
start of the content section of the generated document. This is useful for
inserting a standard disclaimer or heading in generated documents. The header
may optionally be a Jinja2 template, which will be generated using the document
**metadata**. Options for this feature are:

* `document_header.file` - A markdown file, or Jinja2 template for generating
  Markdown, that will be inserted before the content section.
* `document_header.jinja_template` - If specified, this will trigger Jinja2
  processing of the header file. The default is to treat the file as Markdown
  rather than a Jinja2 template.
* `document_header.separate_section` - If specified, this will cause a section
  and page break to be inserted between the document header and the content
  section. The default is to NOT include a section and page break.

#### EmbedFonts

The **EmbedFonts** feature is used when outputting a docx file to embed fonts
into the output document. This allows recipients to view the file with the
correct fonts, even if they do not have the fonts installed on their viewing
device. Options for this feature are:

* `embed_fonts.fonts` - A mapping of font name/style to file/url for each font
  that should be embedded into the document. For example,
  `embed_fonts.fonts.Roboto.Regular` could be set to `Roboto-Regular.ttf`,
  which would find the file `Roboto-Regular.ttf` in the font directory (see
  below). The file may be an absolute filesystem path, a filename to locate in
  the font directory, or a URL that points to a TTF file, which will be
  downloaded.
* `embed_fonts.font_dir` - One or more directories where embedded fonts may be
  found. If not specified, this defaults to the system font directories.

#### ExtendedStyles

The **ExtendedStyles** feature allows you to specify a docx file containing
additional styles, which will be merged into the reference doc prior to
document generation. This is useful if only a subset of documents require
certain styles to be defined. Options for this feature are:

* `extended_styles.file` - The docxfile containing additional styles, which will
  be merged into the reference doc.

#### JinjaTemplate

The **JinjaTemplate** feature allows you to use a Jinja2 template to convert a
JSON document into a Markdown file, which will be used as the source file for
document generation. Options for this feature are:

* `jinja_template.template_file` - A file containing a Jinja2 template, used to
  render JSON into Markdown.
* `jinja_template.output_file_extension` - For advanced cases, it may be
  desirable to have the Jinja template output another format (e.g.
  reStructuredText). In that case, this option may be specified to control the
  output filename.

#### MarkdownMetadata

The **MarkdownMetadata** feature allows metadata to be parsed from the source
document, assuming the source document is Markdown. This is useful to extract
fields such as title and author for use e.g. in generating a coverpage. This
feature has no configurable options.

#### RemoteFiles

The **RemoteFiles** feature allows files to be downloaded from a remote
location prior to document generation. This is especially useful when running
docmaker in a docker container, to avoid needing to mount the files into
the container's filesystem. This feature will detect when certain options are
URLs (specifically, `reference_doc`, `coverpage.template`, and the source file)
and will automatically download those as well. URLs downloaded by this feature
may contain environment variable names as Python string formatting placeholders
(e.g. `{DOCMAKER_CONFIG_HOST}`), which will be expanded before downloading.
Options for this feature are:

* `remote_files.files` - A mapping of option name to URL. Once downloaded, the
  specified option will be set to the path to the downloaded file. For example,
  `remote_files.files.jinja_template.file` can be set to a URL to load the
  Jinja2 template from a remote host.

#### TableOfContents

The **TableOfContents** feature handles creation of a separate table of contents
section of the document. This will be updated upon conversion to PDF so that
page numbers are accurate. Note that it will NOT be updated if a docx file is
output. Options for this feature are:

* `toc.title_text` - The title text for the table of contents section. If not
  specified, "Table of Contents" is used.
* `toc.title_style` - The style applied to the table of contents title. If not
  specified, "TOC Heading" is used.
* `toc.depth` - The maximum heading depth to be included in the table of
  contents. If not specified, the maximum depth is 3.

### Hacks

> To disable a hack, specify any value for the option `disable_HACK_NAME`, where
> `HACK_NAME` is the name you see below.

#### add_page_break_to_headings

This hack is responsible for adding page breaks before heading styles, and
generating styles with the opposite behavior. The default behavior adds a page
break before any text with the style `Heading 1`, creates a new style called
`Heading 1 - No Break`, and creates styles for each remaining heading style
called `Heading X - With Break`. Options for this hack are:

* `hacks.page_break_before_headings` - A list of heading levels (as integers)
  that should have page breaks added before them.

#### convert_single_row_tables

This hack finds all tables in the generated document with only one row and
removes the styling from them. This is useful if you use single row tables in
your document for layout purposes. Options for this hack are:

* `hacks.single_row_table_style` - Style name to be applied to single row
  tables. If not specified, `Normal Table` is used.

#### normalize_lists

This hack re-numbers the styles applied to lists to limit list styles to 1-5.

#### set_page_number_formats

This hack is responsible for setting page number formats on all sections of the
document. This will set the page number format for the content section to
`decimal` (e.g. "1", "2", "3", etc). All other sections will be set to
`lowerRoman` (e.g. "i", "ii", "iii", etc). If there is a coverpage, the page
number will be removed from that section, and numbering for the following
section will be reset.

#### sync_header_footer

This hack is responsible for copying any header and footer from the content
section to other sections, such as table of contents. This is necessary as the
table of contents section is not generated using the reference document.

#### sync_margins

This hack is responsible for copying margin settings from the content section to
other sections, such as table of contents. This is necessary as the table of
contents section is not generated using the reference document.

## Known Issues

- `unoconv` is deprecated, however its replacement `unoserver` does not yet
  handle updating indexes, which is necessary for Table of Contents support.

## Upcoming Features

- Developer documentation for the creation of docmaker hacks and features

## Version History

### Version x.x.x (2022-02-xx)

-   Initial release
