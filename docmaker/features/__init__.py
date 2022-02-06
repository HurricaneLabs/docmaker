import importlib
import inspect
import pkgutil


class FeatureNotFound(ModuleNotFoundError):
    pass


__features = {}


def load_all_features():
    if not __features:
        # Crawl docmaker.features once
        parent_module = importlib.import_module("docmaker.features")
        for _, module_name, _ in pkgutil.iter_modules(parent_module.__path__):
            try:
                module = importlib.import_module(f"docmaker.features.{module_name}")
            except ModuleNotFoundError as mnfe:
                if mnfe.name.startswith("docmaker.name"):
                    raise mnfe
                continue
            for (_, obj) in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ != f"docmaker.features.{module_name}":
                    continue
                __features[obj.__name__] = obj

        # Crawl features in external packages
        # E.g. `docmaker_feature_fillable_forms.FillableForm`
        for _, module_name, _ in pkgutil.iter_modules():
            if not module_name.startswith("docmaker_feature"):
                continue

            module = importlib.import_module(module_name)

            if hasattr(module, "features"):
                # Module provides us a mapping of feature name to class
                for feature_name, obj in getattr(module, "features").items():
                    if feature_name not in __features:
                        __features[feature_name] = obj
                    else:
                        __features[f"{module_name}.{feature_name}"] = obj
            else:
                for (_, obj) in inspect.getmembers(module, inspect.isclass):
                    if obj.__module__ != module_name:
                        continue

                    if obj.__name__ not in __features:
                        __features[obj.__name__] = obj
                    else:
                        __features[f"{module_name}.{obj.__name__}"] = obj

    return __features


def load_feature(feature):
    if isinstance(feature, type):
        return feature

    if not __features:
        load_all_features()

    if feature not in __features:
        # Try to import it directly
        try:
            module = importlib.import_module(feature)
            for (_, obj) in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ != feature:
                    continue

                # Use the first class defined in the module
                __features[feature] = obj
                break
        except ModuleNotFoundError as exc:
            if not "." in feature:
                raise FeatureNotFound(feature) from exc

            (module_name, clsname) = feature.rsplit(".", 1)
            module = importlib.import_module(module_name)

            if not hasattr(module, clsname):
                raise FeatureNotFound(feature) from exc

            __features[feature] = getattr(module, clsname)

    if feature not in __features:
        # Still not found, throw an error
        raise FeatureNotFound(feature)

    return __features[feature]
