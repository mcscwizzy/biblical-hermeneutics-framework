"""Small helpers for retaining CKL provenance while presenting prose."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        if isinstance(result, Mapping):
            return dict(result)
    result: dict[str, Any] = {}
    for name in dir(value) if value is not None else ():
        if name.startswith("_"):
            continue
        try:
            candidate = getattr(value, name)
        except Exception:  # pragma: no cover - defensive for external adapters
            continue
        if callable(candidate):
            continue
        if isinstance(candidate, (str, int, float, bool, list, tuple, dict)) or candidate is None:
            result[name] = candidate
    return result


def strings(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        if isinstance(item, Mapping):
            item = item.get("reference") or item.get("id") or item.get("title") or ""
        text = str(item or "").strip()
        key = text.casefold()
        if text and key not in seen:
            result.append(text)
            seen.add(key)
    return result


def source_id_for(source: Any) -> str:
    data = as_mapping(source)
    return str(data.get("id") or data.get("source_id") or data.get("title") or "").strip()


def source_ids_for(value: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    values = value if isinstance(value, (list, tuple, set)) else [value]
    for item in values:
        source_id = source_id_for(item) if isinstance(item, Mapping) or hasattr(item, "to_dict") else str(item or "").strip()
        if source_id and source_id.casefold() not in seen:
            result.append(source_id)
            seen.add(source_id.casefold())
    return result


def merge_unique(first: Sequence[str], second: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in [*first, *second]:
        text = str(value or "").strip()
        key = text.casefold()
        if text and key not in seen:
            result.append(text)
            seen.add(key)
    return result
