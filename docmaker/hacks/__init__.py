"""Hacks are like features, but they're enabled by default"""

import importlib
import inspect
import pkgutil


__hacks = []


def load_hacks(hook_name=None):
    if not __hacks:
        # Crawl docmaker.hacks
        parent_module = importlib.import_module("docmaker.hacks")
        for _, module_name, _ in pkgutil.iter_modules(parent_module.__path__):
            module = importlib.import_module(f"docmaker.hacks.{module_name}")
            for (_, func) in inspect.getmembers(module, inspect.isfunction):
                if func.__module__ != f"docmaker.hacks.{module_name}":
                    continue
                __hacks.append(func)

        # Crawl hacks in external packages
        for _, module_name, _ in pkgutil.iter_modules():
            if not module_name.startswith("docmaker_hack"):
                continue

            module = importlib.import_module(module_name)
            for (_, func) in inspect.getmembers(module, inspect.isfunction):
                if func.__module__ != module_name:
                    continue
                __hacks.append(func)

    if hook_name:
        return [_method for _method in __hacks if getattr(_method, "hook", None) == hook_name]

    return __hacks
