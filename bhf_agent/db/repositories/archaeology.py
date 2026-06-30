"""Repositories for archaeology site, item, and scripture-link reads."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..common import DEFAULT_DB_PATH, StudyDataError
from ..connection import connect


EnsureSchema = Callable[[Any], None]
AttachSource = Callable[[dict[str, Any], str | Path], dict[str, Any]]
PeriodFilter = Callable[[list[str], str | None], bool]
PeriodsFromValue = Callable[[Any, Any], list[str]]
ItemLoader = Callable[[str | None, str | None, str | Path], list[dict[str, Any]]]
LinkLoader = Callable[[str | None, str | Path], list[dict[str, Any]]]


def list_archaeology_sites(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    list_archaeology_items: ItemLoader,
    period_filter_matches: PeriodFilter,
    periods_from_value: PeriodsFromValue,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM archaeology_sites
            ORDER BY confidence_rank DESC, name
            """
        ).fetchall()
    sites = [
        attach_source(
            archaeology_site_from_row(row, periods_from_value=periods_from_value),
            path,
        )
        for row in rows
    ]
    for site in sites:
        site["archaeology_items"] = list_archaeology_items(site["id"], period, path)
        site["scripture_links"] = [
            link
            for item in site["archaeology_items"]
            for link in item.get("scripture_links", [])
        ]
        site["reference_count"] = len(site["scripture_links"])
    return [site for site in sites if period_filter_matches(site["periods"], period)]


def get_archaeology_site(
    site_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    list_archaeology_items: ItemLoader,
    periods_from_value: PeriodsFromValue,
) -> dict[str, Any]:
    with connect(path) as connection:
        ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM archaeology_sites WHERE id = ?",
            (site_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("archaeology site not found")
    site = attach_source(
        archaeology_site_from_row(row, periods_from_value=periods_from_value),
        path,
    )
    site["archaeology_items"] = list_archaeology_items(site_id, None, path)
    site["scripture_links"] = [
        link
        for item in site["archaeology_items"]
        for link in item.get("scripture_links", [])
    ]
    site["reference_count"] = len(site["scripture_links"])
    return site


def list_archaeology_items(
    site_id: str | None = None,
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    list_archaeology_scripture_links: LinkLoader,
    period_filter_matches: PeriodFilter,
    periods_from_value: PeriodsFromValue,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        if site_id is None:
            rows = connection.execute(
                "SELECT * FROM archaeology_items ORDER BY confidence_rank DESC, period, name"
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM archaeology_items
                WHERE site_id = ?
                ORDER BY confidence_rank DESC, period, name
                """,
                (site_id,),
            ).fetchall()
    items = [
        attach_source(
            archaeology_item_from_row(row, periods_from_value=periods_from_value),
            path,
        )
        for row in rows
    ]
    for item in items:
        item["scripture_links"] = list_archaeology_scripture_links(item["id"], path)
        item["reference_count"] = len(item["scripture_links"])
    return [item for item in items if period_filter_matches(item["periods"], period)]


def get_archaeology_item(
    item_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    list_archaeology_scripture_links: LinkLoader,
    periods_from_value: PeriodsFromValue,
) -> dict[str, Any]:
    with connect(path) as connection:
        ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM archaeology_items WHERE id = ?",
            (item_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("archaeology item not found")
    item = attach_source(
        archaeology_item_from_row(row, periods_from_value=periods_from_value),
        path,
    )
    item["scripture_links"] = list_archaeology_scripture_links(item_id, path)
    item["reference_count"] = len(item["scripture_links"])
    return item


def list_archaeology_scripture_links(
    item_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        if item_id is None:
            rows = connection.execute(
                "SELECT * FROM archaeology_scripture_links ORDER BY book, chapter, verse_start, verse_end"
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM archaeology_scripture_links
                WHERE item_id = ?
                ORDER BY book, chapter, verse_start, verse_end
                """,
                (item_id,),
            ).fetchall()
    return [archaeology_scripture_link_from_row(row) for row in rows]


def archaeology_site_from_row(
    row: Any,
    *,
    periods_from_value: PeriodsFromValue,
) -> dict[str, Any]:
    periods = periods_from_value(row["periods"], fallback=row["period"])
    return {
        "id": row["id"],
        "name": row["name"],
        "site_type": row["site_type"],
        "period": row["period"],
        "periods": periods,
        "latitude": float(row["latitude"]) if row["latitude"] is not None else None,
        "longitude": float(row["longitude"]) if row["longitude"] is not None else None,
        "modern_location": row["modern_location"],
        "ancient_region": row["ancient_region"],
        "description": row["description"],
        "confidence": row["confidence"],
        "confidence_rank": int(row["confidence_rank"]),
        "source_id": row["source_id"] if "source_id" in row.keys() else "",
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "license": row["license"],
        "notes": row["notes"],
    }


def archaeology_item_from_row(
    row: Any,
    *,
    periods_from_value: PeriodsFromValue,
) -> dict[str, Any]:
    periods = periods_from_value(row["periods"], fallback=row["period"])
    return {
        "id": row["id"],
        "site_id": row["site_id"],
        "name": row["name"],
        "item_type": row["item_type"],
        "period": row["period"],
        "periods": periods,
        "relationship": row["relationship"],
        "why_it_matters": row["why_it_matters"],
        "bhf_caution": row["bhf_caution"],
        "confidence": row["confidence"],
        "confidence_rank": int(row["confidence_rank"]),
        "source_id": row["source_id"] if "source_id" in row.keys() else "",
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "license": row["license"],
        "notes": row["notes"],
    }


def archaeology_scripture_link_from_row(row: Any) -> dict[str, Any]:
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
