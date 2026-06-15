"""Adapter that delegates to originals modules to ensure exact transformation parity."""

from importlib import import_module


def delegate(module_name: str, func_name: str = None):
    if func_name is None:
        func_name = module_name

    module = import_module(f"originals.{module_name}")
    return getattr(module, func_name)
