"""Validation for stable Archaeology ↔ CKL identifiers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from .study_db import list_archaeology_ckl_links, list_archaeology_items

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_cross_domain_archaeology_relationships(
    ckl_objects: Iterable[Any],
    *,
    path: str | Path,
) -> None:
    """Raise ``ValueError`` for dangling or malformed cross-domain links.

    Existing CKL ``archaeology`` fields contain legacy descriptive context and
    are not used as identifiers. Stable links are stored in the archaeology
    domain's relationship table, so CKL keeps no archaeology media or prose.
    """

    records = list(ckl_objects)
    ckl_ids = {str(getattr(obj, "id", "") or (obj.get("id") if isinstance(obj, dict) else "")) for obj in records}
    archaeology_ids = {item["id"] for item in list_archaeology_items(path=path)}
    errors: list[str] = []
    for link in list_archaeology_ckl_links(path=path):
        if link["archaeology_item_id"] not in archaeology_ids:
            errors.append(f"archaeology relationship references missing item '{link['archaeology_item_id']}'")
        if link["ckl_object_id"] not in ckl_ids:
            errors.append(f"archaeology relationship references missing CKL object '{link['ckl_object_id']}'")
        if not _ID.fullmatch(link["relationship"]):
            errors.append(f"archaeology relationship has invalid type '{link['relationship']}'")
    if errors:
        raise ValueError("; ".join(errors))
