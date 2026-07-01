"""Repositories for source registry reads and source-reference lookups."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..common import DEFAULT_DB_PATH, StudyDataError
from ..connection import connect


EnsureSchema = Callable[[Any], None]

_SOURCE_REFERENCE_TABLES = (
    ("biblical_places", "place"),
    ("map_routes", "route"),
    ("historical_layers", "historical_layer"),
    ("political_context_layers", "political_context_layer"),
    ("archaeology_sites", "archaeology_site"),
    ("archaeology_items", "archaeology_item"),
    ("manuscript_items", "manuscript_item"),
)


def list_sources(
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute("SELECT * FROM sources ORDER BY label").fetchall()
    return [source_from_row(row) for row in rows]


def get_source(
    source_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> dict[str, Any]:
    with connect(path) as connection:
        ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("source not found")
    source = source_from_row(row)
    source["reference_count"] = source_reference_count(
        source_id,
        path=path,
        ensure_schema=ensure_schema,
    )
    source["references"] = source_references(
        source_id,
        path=path,
        ensure_schema=ensure_schema,
    )
    return source


def source_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "label": row["label"],
        "url": row["url"],
        "license": row["license"],
        "notes": row["notes"],
    }


def source_reference_count(
    source_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> int:
    total = 0
    with connect(path) as connection:
        ensure_schema(connection)
        for table, _item_type in _SOURCE_REFERENCE_TABLES:
            row = connection.execute(
                f"SELECT COUNT(*) AS count FROM {table} WHERE source_id = ?",
                (source_id,),
            ).fetchone()
            total += int(row["count"]) if row else 0
    return total


def source_references(
    source_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    with connect(path) as connection:
        ensure_schema(connection)
        for table, item_type in _SOURCE_REFERENCE_TABLES:
            rows = connection.execute(
                f"SELECT id, name FROM {table} WHERE source_id = ? ORDER BY name",
                (source_id,),
            ).fetchall()
            for row in rows:
                references.append(
                    {
                        "item_type": item_type,
                        "id": row["id"],
                        "name": row["name"],
                    }
                )
    return references
