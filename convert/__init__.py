import importlib

def get_converter(from_level: int, to_level: int):
    """
    Return a converter module for converting from `from_level` to `to_level`.
    The converter module must expose a function `convert(circuit_spec, destination_file=None, ecosystem=None, logger=None)`.
    """
    module_name = f"convert.step_{from_level}to{to_level}"
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        raise ImportError(f"Converter module {module_name} not found") from e
    if not hasattr(module, "convert"):
        raise ImportError(f"Module {module_name} has no 'convert' function")
    return module
