"""Repositories for manuscript item and scripture-link reads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from ..common import DEFAULT_DB_PATH, StudyDataError
from ..connection import connect


EnsureSchema = Callable[[Any], None]
AttachSource = Callable[[dict[str, Any], str | Path], dict[str, Any]]
PeriodFilter = Callable[[list[str], str | None], bool]
PeriodsFromValue = Callable[[Any, Any], list[str]]
LinkLoader = Callable[[str | None, str | Path], list[dict[str, Any]]]


def list_manuscript_items(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    list_manuscript_scripture_links: LinkLoader,
    period_filter_matches: PeriodFilter,
    periods_from_value: PeriodsFromValue,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM manuscript_items
            ORDER BY confidence_rank DESC, name
            """
        ).fetchall()
    items = [
        attach_source(
            manuscript_item_from_row(row, periods_from_value=periods_from_value),
            path,
        )
        for row in rows
    ]
    for item in items:
        item["scripture_links"] = list_manuscript_scripture_links(item["id"], path)
        item["reference_count"] = len(item["scripture_links"])
    return [item for item in items if period_filter_matches(item["periods"], period)]


def get_manuscript_item(
    item_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    list_manuscript_scripture_links: LinkLoader,
    periods_from_value: PeriodsFromValue,
) -> dict[str, Any]:
    with connect(path) as connection:
        ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM manuscript_items WHERE id = ?",
            (item_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("manuscript item not found")
    item = attach_source(
        manuscript_item_from_row(row, periods_from_value=periods_from_value),
        path,
    )
    item["scripture_links"] = list_manuscript_scripture_links(item["id"], path)
    item["reference_count"] = len(item["scripture_links"])
    return item


def list_manuscript_scripture_links(
    item_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        if item_id is None:
            rows = connection.execute(
                "SELECT * FROM manuscript_scripture_links ORDER BY book, chapter, verse_start, verse_end"
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM manuscript_scripture_links
                WHERE item_id = ?
                ORDER BY book, chapter, verse_start, verse_end
                """,
                (item_id,),
            ).fetchall()
    return [manuscript_scripture_link_from_row(row) for row in rows]


def manuscript_item_from_row(
    row: Any,
    *,
    periods_from_value: PeriodsFromValue,
) -> dict[str, Any]:
    related_books = _json_list(row["related_books"])
    periods = periods_from_value(row["periods"], fallback=row["period"])
    return {
        "id": row["id"],
        "name": row["name"],
        "manuscript_type": row["manuscript_type"],
        "language": row["language"],
        "date": row["date"],
        "material": row["material"],
        "discovery_location": row["discovery_location"],
        "current_location": row["current_location"],
        "latitude": float(row["latitude"]) if row["latitude"] is not None else None,
        "longitude": float(row["longitude"]) if row["longitude"] is not None else None,
        "related_books": [str(book) for book in related_books if str(book).strip()],
        "period": row["period"],
        "periods": periods,
        "significance": row["significance"],
        "confidence": row["confidence"],
        "confidence_rank": int(row["confidence_rank"]),
        "source_id": row["source_id"] if "source_id" in row.keys() else "",
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "license": row["license"],
        "notes": row["notes"],
        "bhf_caution": row["bhf_caution"],
    }


def manuscript_scripture_link_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "item_id": row["item_id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "verse_start": int(row["verse_start"]),
        "verse_end": int(row["verse_end"]),
        "relationship_type": row["relationship_type"],
        "notes": row["notes"],
    }


def _json_list(value: Any) -> list[Any]:
    try:
        decoded = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []
