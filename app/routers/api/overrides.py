import sys


def runtime_override(name: str, default):
    runtime_module = sys.modules.get("app.main")
    if runtime_module is None:
        return default
    return getattr(runtime_module, name, default)
