"""Repositories for archaeology site, item, and scripture-link reads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from ..common import DEFAULT_DB_PATH, StudyDataError
from ..connection import connect
from ...archaeology import validate_media_record


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
    include_details: bool = True,
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
    if include_details:
        for site in sites:
            site["archaeology_items"] = list_archaeology_items(site["id"], period, path)
            site["media"] = list_archaeology_media(site_id=site["id"], path=path, ensure_schema=ensure_schema)
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
    site["media"] = list_archaeology_media(site_id=site_id, path=path, ensure_schema=ensure_schema)
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
    include_media: bool = True,
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
        if include_media:
            item["media"] = list_archaeology_media(item_id=item["id"], path=path, ensure_schema=ensure_schema)
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
    include_media: bool = True,
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
    if include_media:
        item["media"] = list_archaeology_media(item_id=item_id, path=path, ensure_schema=ensure_schema)
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


def list_archaeology_passage_summaries(
    book: str,
    chapter: int,
    verse_start: int,
    verse_end: int,
    *,
    path: str | Path = DEFAULT_DB_PATH,
    ensure_schema: EnsureSchema,
    limit: int = 8,
    prepare_schema: bool = True,
) -> list[dict[str, Any]]:
    """Return compact passage matches without reading archaeology media."""

    bounded_limit = max(1, min(int(limit), 25))
    with connect(path) as connection:
        if prepare_schema:
            ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT i.id, i.name AS title, i.item_type, i.period,
                   i.why_it_matters AS summary, i.bhf_caution AS caution,
                   i.confidence, i.site_id, s.name AS site_name,
                   l.relationship_type, l.verse_start, l.verse_end
            FROM archaeology_scripture_links AS l
            JOIN archaeology_items AS i ON i.id = l.item_id
            LEFT JOIN archaeology_sites AS s ON s.id = i.site_id
            WHERE lower(l.book) = lower(?)
              AND l.chapter = ?
              AND l.verse_start <= ?
              AND l.verse_end >= ?
            ORDER BY i.confidence_rank DESC, i.name, i.id
            LIMIT ?
            """,
            (str(book).strip(), int(chapter), int(verse_end), int(verse_start), bounded_limit),
        ).fetchall()
    return [
        {
            "id": str(row["id"]),
            "title": str(row["title"]),
            "item_type": str(row["item_type"]),
            "period": str(row["period"]),
            "summary": str(row["summary"]),
            "caution": str(row["caution"]),
            "confidence": str(row["confidence"]),
            "site_id": str(row["site_id"]),
            "site_name": str(row["site_name"] or ""),
            "relationship": str(row["relationship_type"]),
            "verse_start": int(row["verse_start"]),
            "verse_end": int(row["verse_end"]),
        }
        for row in rows
    ]


def list_archaeology_ckl_links(
    item_id: str | None = None,
    *,
    ckl_object_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    ensure_schema: EnsureSchema,
) -> list[dict[str, str]]:
    """Return stable archaeology-to-CKL links without coupling either schema."""

    with connect(path) as connection:
        ensure_schema(connection)
        if item_id:
            rows = connection.execute(
                """SELECT archaeology_item_id, ckl_object_id, relationship, notes
                   FROM archaeology_ckl_links WHERE archaeology_item_id = ?
                   ORDER BY ckl_object_id, relationship""",
                (item_id,),
            ).fetchall()
        elif ckl_object_id:
            rows = connection.execute(
                """SELECT archaeology_item_id, ckl_object_id, relationship, notes
                   FROM archaeology_ckl_links WHERE ckl_object_id = ?
                   ORDER BY archaeology_item_id, relationship""",
                (ckl_object_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                """SELECT archaeology_item_id, ckl_object_id, relationship, notes
                   FROM archaeology_ckl_links ORDER BY archaeology_item_id, ckl_object_id, relationship"""
            ).fetchall()
    return [
        {
            "archaeology_item_id": str(row["archaeology_item_id"]),
            "ckl_object_id": str(row["ckl_object_id"]),
            "relationship": str(row["relationship"]),
            "notes": str(row["notes"]),
        }
        for row in rows
    ]


def list_archaeology_media(
    *,
    item_id: str | None = None,
    site_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    ensure_schema: EnsureSchema,
) -> list[dict[str, Any]]:
    if bool(item_id) == bool(site_id):
        raise StudyDataError("provide exactly one archaeology item or site id")
    column = "archaeology_item_id" if item_id else "archaeology_site_id"
    value = item_id or site_id
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            f"SELECT * FROM archaeology_media WHERE {column} = ? ORDER BY title, id",
            (value,),
        ).fetchall()
    return [archaeology_media_from_row(row) for row in rows]


def create_archaeology_media(
    record: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> dict[str, Any]:
    """Insert one validated media record for an explicit import workflow."""

    with connect(path) as connection:
        ensure_schema(connection)
        item_ids = {
            row["id"] for row in connection.execute("SELECT id FROM archaeology_items")
        }
        site_ids = {
            row["id"] for row in connection.execute("SELECT id FROM archaeology_sites")
        }
        normalized = validate_media_record(
            record,
            archaeology_item_ids=item_ids,
            archaeology_site_ids=site_ids,
        )
        if connection.execute(
            "SELECT 1 FROM archaeology_media WHERE id = ?", (normalized["id"],)
        ).fetchone():
            raise StudyDataError("archaeology media already exists")
        columns = (
            "id", "archaeology_item_id", "archaeology_site_id", "media_type", "title",
            "caption", "source_url", "image_url", "thumbnail_url", "local_asset_path",
            "creator", "institution", "license_id", "license_url", "attribution_text",
            "rights_status", "can_redistribute", "can_cache", "can_modify",
            "source_record_id", "checksum", "width", "height",
        )
        connection.execute(
            f"INSERT INTO archaeology_media ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            tuple(
                None
                if column in {"archaeology_item_id", "archaeology_site_id"}
                and not normalized.get(column)
                else normalized.get(column, "")
                for column in columns
            ),
        )
        row = connection.execute(
            "SELECT * FROM archaeology_media WHERE id = ?", (normalized["id"],)
        ).fetchone()
    return archaeology_media_from_row(row)


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
    details_raw = row["evidence_details"] if "evidence_details" in row.keys() else "{}"
    try:
        evidence_details = json.loads(details_raw or "{}")
    except (TypeError, json.JSONDecodeError):
        evidence_details = {}
    if not isinstance(evidence_details, dict):
        evidence_details = {}
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
        "evidence_details": evidence_details,
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


def archaeology_media_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "archaeology_item_id": row["archaeology_item_id"],
        "archaeology_site_id": row["archaeology_site_id"],
        "media_type": row["media_type"],
        "title": row["title"],
        "caption": row["caption"],
        "source_url": row["source_url"],
        "image_url": row["image_url"],
        "thumbnail_url": row["thumbnail_url"],
        "local_asset_path": row["local_asset_path"],
        "creator": row["creator"],
        "institution": row["institution"],
        "license_id": row["license_id"],
        "license_url": row["license_url"],
        "attribution_text": row["attribution_text"],
        "rights_status": row["rights_status"],
        "can_redistribute": bool(row["can_redistribute"]),
        "can_cache": bool(row["can_cache"]),
        "can_modify": bool(row["can_modify"]),
        "source_record_id": row["source_record_id"],
        "checksum": row["checksum"],
        "width": row["width"],
        "height": row["height"],
    }
