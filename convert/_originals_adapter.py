"""Adapter that delegates to originals modules to ensure exact transformation parity.

If importing the originals fails due to modern Python syntax (e.g. PEP 604 `dict | str`),
this adapter will create a compatibility copy in `.compat_originals/` converting
`A | B` to `typing.Union[A, B]` and load that instead, leaving `originals/` intact.
"""

import importlib
import importlib.util
import sys
import re
from pathlib import Path
from importlib import import_module


def _transform_source_for_legacy_python(src: str) -> str:
    # Ensure typing is imported
    if "import typing" not in src:
        src = "import typing\n" + src

    # Replace simple binary | unions like 'dict | str' with typing.Union[dict, str]
    # This is a heuristic: only replace token|token patterns (identifiers, dotted names)
    pattern = re.compile(r"\b([A-Za-z_][A-Za-z0-9_\.<>]*)\b\s*\|\s*\b([A-Za-z_][A-Za-z0-9_\.<>]*)\b")

    def _repl(m):
        a = m.group(1)
        b = m.group(2)
        return f"typing.Union[{a}, {b}]"

    transformed = pattern.sub(_repl, src)
    return transformed


def _load_compat_module(orig_path: Path, module_name: str):
    repo_root = Path(__file__).resolve().parent.parent
    compat_dir = repo_root / ".compat_originals"
    compat_dir.mkdir(parents=True, exist_ok=True)

    with open(orig_path, "r", encoding="utf-8") as f:
        src = f.read()

    transformed = _transform_source_for_legacy_python(src)

    compat_file = compat_dir / (module_name + ".py")
    with open(compat_file, "w", encoding="utf-8") as f:
        f.write(transformed)

    # Load module from compat file under a unique name
    spec_name = f"compat_originals.{module_name}"
    if spec_name in sys.modules:
        return sys.modules[spec_name]

    spec = importlib.util.spec_from_file_location(spec_name, str(compat_file))
    mod = importlib.util.module_from_spec(spec)
    loader = spec.loader
    if loader is None:
        raise ImportError(f"Cannot load compatibility module for {module_name}")
    loader.exec_module(mod)
    sys.modules[spec_name] = mod
    return mod


def delegate(module_name: str, func_name: str = None):
    if func_name is None:
        func_name = module_name

    full_name = f"originals.{module_name}"
    try:
        module = import_module(full_name)
        return getattr(module, func_name)
    except Exception:
        # Attempt compatibility fallback by creating a transformed copy
        repo_root = Path(__file__).resolve().parent.parent
        orig_path = repo_root / "originals" / (module_name + ".py")
        if orig_path.exists():
            try:
                compat_mod = _load_compat_module(orig_path, module_name)
                return getattr(compat_mod, func_name)
            except Exception:
                # re-raise original import error if fallback fails
                raise
        # if originals file missing, re-raise
        raise
