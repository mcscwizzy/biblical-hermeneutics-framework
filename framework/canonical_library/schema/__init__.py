"""Canonical Knowledge Library schema API."""

from __future__ import annotations

from . import legacy as _legacy
from .validator import BASE_SCHEMA_PATH, load_base_schema, validate_base_object


def __getattr__(name: str) -> object:
    return getattr(_legacy, name)


def __dir__() -> list[str]:
    names = set(globals()) | set(dir(_legacy))
    return sorted(names)


__all__ = sorted(
    {
        *(
            name
            for name in dir(_legacy)
            if not name.startswith("_")
        ),
        "BASE_SCHEMA_PATH",
        "load_base_schema",
        "validate_base_object",
    }
)
