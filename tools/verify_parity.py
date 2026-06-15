import json
import importlib
from pathlib import Path


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_converter_parity(original_module: str, wrapper_module: str, func_name: str = "convert") -> bool:
    orig = importlib.import_module(f"originals.{original_module}")
    wrap = importlib.import_module(f"convert.{wrapper_module}")

    orig_func = getattr(orig, func_name, None)
    wrap_func = getattr(wrap, func_name, None)
    if orig_func is None or wrap_func is None:
        raise ValueError("Both modules must expose a 'convert' function")

    # Use sample input from repo
    sample_path = Path("abstraction2.json")
    if not sample_path.exists():
        raise FileNotFoundError("abstraction2.json sample not found in repository root")

    spec = load_json(sample_path)

    orig_out = orig_func(spec, destination_file=None)
    wrap_out = wrap_func(spec, destination_file=None)

    # Direct JSON comparison
    return json.dumps(orig_out, sort_keys=True) == json.dumps(wrap_out, sort_keys=True)


if __name__ == "__main__":
    ok = verify_converter_parity("convert_2to3", "step_2to3", "convert_2to3")
    print("Parity test for 2->3:", ok)
