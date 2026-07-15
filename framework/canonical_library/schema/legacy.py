"""Compatibility bridge for the legacy CKL schema module."""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


_LEGACY_MODULE_NAME = "framework.canonical_library._schema_legacy"
_LEGACY_PATH = Path(__file__).resolve().parents[1] / "schema.py"


def _load_legacy_module() -> ModuleType:
    module = sys.modules.get(_LEGACY_MODULE_NAME)
    if module is not None:
        return module

    spec = spec_from_file_location(_LEGACY_MODULE_NAME, _LEGACY_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load legacy CKL schema module at {_LEGACY_PATH}")
    module = module_from_spec(spec)
    sys.modules[_LEGACY_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


_LEGACY = _load_legacy_module()


def __getattr__(name: str) -> object:
    return getattr(_LEGACY, name)


def __dir__() -> list[str]:
    names = set(globals()) | set(dir(_LEGACY))
    return sorted(names)


__all__ = [
    name
    for name in dir(_LEGACY)
    if not name.startswith("_")
]
