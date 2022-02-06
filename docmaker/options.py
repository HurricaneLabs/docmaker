import os
import re
import tempfile
from collections import MutableMapping

from ruamel.yaml import YAML

from docmaker.features.remote_files import RemoteFiles


def flatten(d, parent=None):
    if not isinstance(d, MutableMapping):
        return d

    d2 = {}
    for k in d:
        if parent:
            k2 = f"{parent}.{k}"
        else:
            k2 = k

        if isinstance(d[k], MutableMapping):
            d2.update(flatten(d[k], k2))
        else:
            d2[k2] = d[k]

    return d2


def option_is_true(value):
    return str(value).lower() in ("yes", "true", "on", "1")


def option_is_false(value):
    return str(value).lower() in ("no", "false", "off", "0")


def load_options_from_file(filename):
    if "://" in filename:
        rf = RemoteFiles()

        fd, dest = tempfile.mkstemp()
        os.close(fd)

        filename = rf.get_remote_file(
            src=filename,
            ctx=None,
            dest=dest
        )

    with open(filename, "r") as f:
        return load_options_from_stream(f)


def load_options_from_stream(stream):
    options = YAML().load(stream)
    options = flatten(options)

    features = options.pop("features", [])

    if "include" in options:
        for filename in options.pop("include"):
            opts, feats = load_options_from_file(filename)
            options.update(flatten(opts))
            features.extend(feats)

    features = list(set(features))

    return options, features


def get_features_options_from_environ(pattern=None, default_features=None, default_options=None):
    pattern = pattern or "DOCMAKER"

    env_config = []
    for envvar in os.environ:
        m = re.match(r"^%s_OPTIONS_FILE(\d+)$" % pattern, envvar)
        if not m:
            continue
        idx = int(m.groups()[0])

        filename = os.environ[envvar].format(**os.environ)

        options, features = load_options_from_file(filename)

        env_config.append((idx, features, options))

    features = []
    if default_features:
        features.extend(default_features)

    options = {}
    if default_options:
        options.update(default_options)

    for (_, c_features, c_options) in sorted(env_config, key=lambda config: config[0]):
        for c_feature in c_features:
            if c_feature[0] == "-" and c_feature[1:] in features:
                features.remove(c_feature[1:])
            elif c_feature not in features:
                features.append(c_feature)
        # features.extend(c_features)
        options.update(c_options)

    return features, options
