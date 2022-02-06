import inspect
import time
from collections.abc import Iterable
from functools import partial, wraps

from toposort import toposort_flatten

from .features import FeatureNotFound, load_feature
from .hacks import load_hacks


class StopProcessing(Exception): pass


def run_hooks(ctx, hook_name):
    methods = {}
    plugins = {}

    for feature in ctx.features:
        for (_, _method) in inspect.getmembers(feature, inspect.ismethod):
            if not callable(_method):
                continue
            if getattr(_method, "hook", None) != hook_name:
                continue

            qualname = _method.__qualname__
            methods[qualname] = _method

            if qualname not in plugins:
                plugins[qualname] = list()

            for depend in getattr(_method, "after", []):
                if "." not in depend:
                    try:
                        _feature = load_feature(depend)
                    except FeatureNotFound:
                        # Assume it's a hack, and no action is required
                        depends = [depend]
                    else:
                        depends = []
                        for (_, feature_method) in inspect.getmembers(_feature, inspect.isfunction):
                            depends.append(feature_method.__qualname__)
                else:
                    depends = [depend]

                for _depend in depends:
                    plugins[qualname].append(_depend)

            for reverse_depend in getattr(_method, "before", []):
                if "." not in reverse_depend:
                    try:
                        _feature = load_feature(reverse_depend)
                    except FeatureNotFound:
                        # Assume it's a hack, and no action is required
                        reverse_depends = [reverse_depend]
                    else:
                        reverse_depends = []
                        for (_, feature_method) in inspect.getmembers(_feature, inspect.isfunction):
                            reverse_depends.append(feature_method.__qualname__)

                else:
                    reverse_depends = [reverse_depend]

                for _reverse_depend in reverse_depends:
                    if _reverse_depend not in plugins:
                        plugins[_reverse_depend] = list()
                    plugins[_reverse_depend].append(qualname)

    for _method in load_hacks(hook_name):
        if ctx.get_as_boolean(f"hacks.disable_{_method.__name__}", False):
            continue
        if not callable(_method):
            continue

        qualname = _method.__qualname__
        methods[qualname] = _method

        if qualname not in plugins:
            plugins[qualname] = list()

        for depend in getattr(_method, "after", []):
            if "." not in depend:
                try:
                    feature = load_feature(depend)
                except FeatureNotFound:
                    # Assume it's a hack, and no action is required
                    depends = [depend]
                else:
                    depends = []
                    for (_, feature_method) in inspect.getmembers(feature, inspect.isfunction):
                        depends.append(feature_method.__qualname__)
            else:
                depends = [depend]

            for _depend in depends:
                plugins[qualname].append(_depend)

        for reverse_depend in getattr(_method, "before", []):
            if "." not in reverse_depend:
                try:
                    feature = load_feature(reverse_depend)
                except FeatureNotFound:
                    # Assume it's a hack, and no action is required
                    reverse_depends = [reverse_depend]
                else:
                    reverse_depends = []
                    for (_, feature_method) in inspect.getmembers(feature, inspect.isfunction):
                        reverse_depends.append(feature_method.__qualname__)

            else:
                reverse_depends = [reverse_depend]

            for _reverse_depend in reverse_depends:
                if _reverse_depend not in plugins:
                    plugins[_reverse_depend] = list()
                plugins[_reverse_depend].append(qualname)

    plugins = toposort_flatten({k: set(v) for (k, v) in plugins.items()})
    plugins = filter(lambda m: m in methods, plugins)
    plugins = map(methods.get, plugins)
    plugins = list(plugins)

    if not plugins:
        return

    for _method in plugins:
        _method(ctx)

"""
@Hook
def foo(self, ctx):

@Hook(bizz=lambda ctx: buzz)
def foo(self, ctx):

@Hook("pre_foo")
def bar(self, ctx):
"""
def Hook(hook_name=None, /, before=None, after=None, predicate=None, ctx=None, **kwargs):
    def wrapper(f):
        _predicate = predicate or (lambda _: True)

        if not isinstance(_predicate, Iterable):
            f.predicate = [_predicate]
        else:
            f.predicate = _predicate

        @wraps(f)
        def call_with_hooks(*args):
            if ctx:
                _ctx = ctx(args)
            else:
                _ctx = args[-1]

            for attr, value in kwargs.items():
                if callable(value):
                    value = value(_ctx)
                setattr(_ctx, attr, value)

            run_hooks(_ctx, f"pre_{f.__name__}")

            if f.predicate:
                for p in f.predicate:
                    if not p(_ctx):
                        return

            start = time.time()
            f(*args)
            _ctx.timing[f.__name__] = round(time.time() - start, 4)

            run_hooks(_ctx, f"post_{f.__name__}")

        call_with_hooks.hook = hook_name
        call_with_hooks.before = before or []
        call_with_hooks.after = after or []

        return call_with_hooks

    return wrapper
