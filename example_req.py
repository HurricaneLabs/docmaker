import argparse
import gzip
import json
import logging
import os
import time
from http.client import HTTPConnection

import requests

ap = argparse.ArgumentParser()
ap.add_argument("-C", "--compress", action="store_true", default=False)
ap.add_argument("-F", "--feature", dest="features", action="append")
ap.add_argument("-k", "--insecure", action="store_true", default=False)
ap.add_argument("-m", "--metadata", dest="metadata", action="append")
ap.add_argument("-o", "--option", dest="options", action="append")
ap.add_argument("-O", "--output-format")
ap.add_argument("-t", "--template")
ap.add_argument("-U", "--url", default="https://127.0.0.1:8443/render")
ap.add_argument("--file", action="append")
ap.add_argument("srcfile")
ap.add_argument("outfile", nargs="?")
args = ap.parse_args()

postData = {}

with open(args.srcfile, "r") as f:
    postData["srcfile"] = {
        "filename": os.path.basename(args.srcfile),
        "contents": f.read()
    }

if args.file:
    for file in args.file:
        filename = os.path.basename(file)
        with open(file, "r") as f:
            postData[filename] = {
                "filename": filename,
                "contents": f.read()
            }

if args.template:
    with open(args.template, "r") as f:
        postData["template"] = {
            "filename": os.path.basename(args.template),
            "contents": f.read()
        }

postData["options"] = {}

if not args.options:
    args.options = []

if os.path.exists(".docmaker.json"):
    args.options.append("@.docmaker.json")

for opt in args.options:
    if opt[0] == "@":
        with open(opt[1:], "r") as f:
            postData["options"].update(json.load(f))
        continue

    if "=" in opt:
        opt, value = opt.split("=", 1)

        if value in ("yes", "true", "on"):
            value = True
        elif value in ("no", "false", "off"):
            value = False
    else:
        value = True

    if opt in postData["options"]:
        if not isinstance(postData["options"][opt], list):
            postData["options"][opt] = [postData["options"][opt]]
        postData["options"][opt].append(value)
    else:
        postData["options"][opt] = value

if "features" in postData["options"]:
    args.features = args.features or []
    args.features.extend(postData["options"].pop("features"))

metadata = {}

if args.metadata:
    for md in args.metadata:
        if md[0] == "@":
            with open(md[1:], "r") as f:
                metadata.update(json.load(f))
            continue

        md, value = md.split("=", 1)
        metadata[md] = value

if "metadata" in postData["options"]:
    raise KeyError("Don't specify metadata in options, use -m/--metadata")

if metadata:
    postData["options"]["metadata"] = metadata

if "output" not in postData["options"]:
    if args.output_format:
        postData["options"]["output"] = args.output_format
    elif args.outfile:
        postData["options"]["output"] = args.outfile.split(".")[-1]
    else:
        postData["options"]["output"] = "pdf"

if args.outfile is None:
    args.outfile =  "%s.%s" % (args.srcfile.rsplit(".", 1)[0], postData["options"]["output"])

headers = {
    "content-type": "application/json"
}
payload = json.dumps(postData).encode("utf-8")

if args.compress:
    start = time.time()
    headers["content-encoding"] = "gzip"
    payload = gzip.compress(payload, compresslevel=5)
    took = round(time.time() - start, 4)
    print(f"Compress took {took} seconds")

print(f"Payload is {len(payload)} bytes")

start = time.time()
r = requests.post(
    args.url,
    params={"feature": args.features},
    data=payload,
    headers=headers,
    verify=not args.insecure
)
took = round(time.time() - start, 4)
print(f"Request took {took} seconds")

if "x-timing" in r.headers:
    timing = json.loads(r.headers["x-timing"])
    for (k, v) in timing.items():
        print(f"    {k}: {v} seconds")

if r.status_code != 200:
    print(r.text)
else:
    print("saving to %s" % args.outfile)

    with open(args.outfile, "wb") as f:
        for chunk in r.iter_content(4096):
            f.write(chunk)
