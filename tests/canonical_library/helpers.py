"""Shared fixtures for Canonical Knowledge Library tests."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from framework.canonical_library import CATEGORY_FOLDERS, CanonicalObject


MANIFEST_CATEGORY_KEYS = tuple(dict.fromkeys(CATEGORY_FOLDERS.values()))


def make_object(
    object_id: str,
    type_name: str,
    title: str,
    aliases: list[str],
    **overrides: Any,
) -> dict[str, Any]:
    obj = CanonicalObject(
        id=object_id,
        type=type_name,
        title=title,
        aliases=aliases,
        **overrides,
    )
    return obj.to_dict()


def write_library(
    root: Path,
    objects: Iterable[dict[str, Any]],
    *,
    path_overrides: dict[str, str] | None = None,
) -> dict[str, int]:
    root.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    for obj in objects:
        relative = None
        if path_overrides is not None:
            relative = path_overrides.get(obj["id"])
        if relative is None:
            relative = f"objects/{CATEGORY_FOLDERS[obj['type']]}/{obj['id']}.json"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(obj, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        counts[obj["type"]] += 1

    manifest = {
        "framework_version": "1.0",
        "schema_version": "1.0",
        "generated_at": None,
        "object_count": sum(counts.values()),
        "categories": {
            manifest_category: counts.get(category, 0)
            for category, manifest_category in CATEGORY_FOLDERS.items()
        },
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return dict(counts)
