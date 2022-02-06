import argparse
import json
import os
from frontmatter import parse

import requests

from .docmaker import Docmaker
from .options import get_features_options_from_environ, load_options_from_file, option_is_false, \
                     option_is_true


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-F", "--feature", dest="features", action="append", default=[])
    ap.add_argument("-m", "--metadata", dest="metadata", action="append", default=[])
    ap.add_argument("-o", "--option", dest="options", action="append", default=[])
    ap.add_argument("-O", "--output-format")
    # ap.add_argument("-R", "--reference", default="reference.docx")
    ap.add_argument("-U", "--url")
    ap.add_argument("srcfile")
    ap.add_argument("outfile", nargs="?")
    args = ap.parse_args()

    features, options = get_features_options_from_environ()

    if args.features:
        features.extend([feature for feature in args.features if feature not in features])

    for dotfile in (".docmaker.json", ".docmaker.yaml"):
        if os.path.exists(dotfile):
            opts, feats = load_options_from_file(dotfile)
            options.update(opts)
            features.extend(feats)

    if args.options:
        for opt in args.options:
            if opt[0] == "@":
                opts, feats = load_options_from_file(opt[1:])
                options.update(opts)
                features.extend(feats)
                continue

            if "=" in opt:
                opt, value = opt.split("=", 1)

                if option_is_true(value):
                    value = True
                elif option_is_false(value):
                    value = False
            else:
                value = True

            options[opt] = value

    metadata = {}

    if args.metadata:
        for md in args.metadata:
            if md[0] == "@":
                with open(md[1:], "r") as f:
                    metadata.update(json.load(f))
                continue

            md, value = md.split("=", 1)
            metadata[md] = value

    if "metadata" in options:
        raise KeyError("Don't specify metadata in options, use -m/--metadata")
    options["metadata"] = metadata

    if "output" not in options:
        if args.output_format:
            options["output"] = args.output_format
        elif args.outfile:
            options["output"] = args.outfile.split(".")[-1]
        else:
            options["output"] = "pdf"
    # if args.reference and "reference" not in options:
    #     options["reference"] = args.reference

    features = list(set(features))

    if args.url:
        verify_ssl = options.pop("verify_ssl", "true")
        if option_is_false(verify_ssl):
            verify_ssl = False
        else:
            verify_ssl = True

        if args.outfile is None:
            args.outfile =  "%s.%s" % (args.srcfile.rsplit(".", 1)[0], options["output"])

        with open(args.srcfile, "r") as f:
            r = requests.post(
                args.url,
                params={"feature": features},
                headers={"user-agent": f"docmaker/{__version__}"},
                json={
                    "options": options,
                    "srcfile": {
                        "filename": os.path.basename(args.srcfile),
                        "contents": f.read()
                    }
                },
                verify=verify_ssl
            )

        if r.status_code != 200:
            print(r.text)
        else:
            with open(args.outfile, "wb") as f:
                for chunk in r.iter_content(4096):
                    f.write(chunk)
    else:
        dm = Docmaker(
            features=features,
            options=options
        )

        dm(args.srcfile, args.outfile)

from . import _version
__version__ = _version.get_versions()['version']
