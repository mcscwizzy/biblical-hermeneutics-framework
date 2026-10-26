"""Repositories for map catalog and political-context reads."""

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
ReferenceLoader = Callable[[str | None, str | Path], list[dict[str, Any]]]


def list_biblical_places(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    period_filter_matches: PeriodFilter,
    periods_from_value: PeriodsFromValue,
    biblical_place_periods: dict[str, list[str]],
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM biblical_places
            ORDER BY confidence_rank DESC, name
            """
        ).fetchall()
    places = [
        biblical_place_from_row(
            row,
            periods_from_value=periods_from_value,
            biblical_place_periods=biblical_place_periods,
        )
        for row in rows
    ]
    return [place for place in places if period_filter_matches(place["periods"], period)]


def get_biblical_place(
    place_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    periods_from_value: PeriodsFromValue,
    biblical_place_periods: dict[str, list[str]],
) -> dict[str, Any]:
    with connect(path) as connection:
        ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM biblical_places WHERE id = ?",
            (place_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("biblical place not found")
    return attach_source(
        biblical_place_from_row(
            row,
            periods_from_value=periods_from_value,
            biblical_place_periods=biblical_place_periods,
        ),
        path,
    )


def list_place_references(
    place_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        if place_id is None:
            rows = connection.execute(
                "SELECT * FROM place_references ORDER BY book, chapter, verse_start, verse_end"
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM place_references
                WHERE place_id = ?
                ORDER BY book, chapter, verse_start, verse_end
                """,
                (place_id,),
            ).fetchall()
    return [place_reference_from_row(row) for row in rows]


def list_map_routes(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    list_route_references: ReferenceLoader,
    period_filter_matches: PeriodFilter,
    periods_from_value: PeriodsFromValue,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM map_routes
            ORDER BY confidence_rank DESC, name
            """
        ).fetchall()
    routes = [
        attach_source(
            map_route_from_row(row, periods_from_value=periods_from_value),
            path,
        )
        for row in rows
    ]
    for route in routes:
        route["scripture_links"] = list_route_references(route["id"], path)
        route["reference_count"] = len(route["scripture_links"])
    return [route for route in routes if period_filter_matches(route["periods"], period)]


def list_route_references(
    route_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        if route_id is None:
            rows = connection.execute(
                "SELECT * FROM route_references ORDER BY book, chapter, verse_start, verse_end"
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM route_references
                WHERE route_id = ?
                ORDER BY book, chapter, verse_start, verse_end
                """,
                (route_id,),
            ).fetchall()
    return [route_reference_from_row(row) for row in rows]


def list_passage_map_summaries(
    book: str,
    chapter: int,
    verse_start: int,
    verse_end: int,
    *,
    path: str | Path = DEFAULT_DB_PATH,
    ensure_schema: EnsureSchema,
    limit: int = 12,
    prepare_schema: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    """Return linked place and route summaries without geometry or child reads."""

    bounded_limit = max(1, min(int(limit), 25))
    parameters = (
        str(book).strip(),
        int(chapter),
        int(verse_end),
        int(verse_start),
        bounded_limit,
    )
    with connect(path) as connection:
        if prepare_schema:
            ensure_schema(connection)
        place_rows = connection.execute(
            """
            SELECT p.id, p.name AS title, p.description,
                   p.modern_location, p.ancient_region, p.confidence,
                   p.source_name, p.source_url,
                   MIN(r.relationship_type) AS relationship
            FROM place_references AS r
            JOIN biblical_places AS p ON p.id = r.place_id
            WHERE lower(r.book) = lower(?)
              AND r.chapter = ?
              AND r.verse_start <= ?
              AND r.verse_end >= ?
            GROUP BY p.id, p.name, p.description, p.modern_location,
                     p.ancient_region, p.confidence, p.source_name, p.source_url
            ORDER BY p.confidence_rank DESC, p.name
            LIMIT ?
            """,
            parameters,
        ).fetchall()
        route_rows = connection.execute(
            """
            SELECT m.id, m.name AS title, m.description, m.confidence,
                   m.route_type, m.source_name, m.source_url,
                   MIN(r.relationship_type) AS relationship
            FROM route_references AS r
            JOIN map_routes AS m ON m.id = r.route_id
            WHERE lower(r.book) = lower(?)
              AND r.chapter = ?
              AND r.verse_start <= ?
              AND r.verse_end >= ?
            GROUP BY m.id, m.name, m.description, m.confidence,
                     m.route_type, m.source_name, m.source_url
            ORDER BY m.confidence_rank DESC, m.name
            LIMIT ?
            """,
            parameters,
        ).fetchall()
    return {
        "places": [
            {
                "id": str(row["id"]),
                "title": str(row["title"]),
                "type": "place",
                "summary": str(row["description"] or row["modern_location"] or ""),
                "modern_location": str(row["modern_location"] or ""),
                "ancient_region": str(row["ancient_region"] or ""),
                "confidence": str(row["confidence"] or "unknown"),
                "relationship": str(row["relationship"] or "map Scripture link"),
                "source_name": str(row["source_name"] or ""),
                "source_url": str(row["source_url"] or ""),
            }
            for row in place_rows
        ],
        "routes": [
            {
                "id": str(row["id"]),
                "title": str(row["title"]),
                "summary": str(row["description"] or ""),
                "route_type": str(row["route_type"] or ""),
                "confidence": str(row["confidence"] or "unknown"),
                "relationship": str(row["relationship"] or "map Scripture link"),
                "source_name": str(row["source_name"] or ""),
                "source_url": str(row["source_url"] or ""),
            }
            for row in route_rows
        ],
    }


def list_passage_location_summaries(
    book: str,
    chapter: int,
    verse_start: int,
    verse_end: int,
    *,
    path: str | Path = DEFAULT_DB_PATH,
    ensure_schema: EnsureSchema,
    limit: int = 5,
    offset: int = 0,
    prepare_schema: bool = True,
) -> dict[str, Any]:
    """Return one bounded, deterministically ordered page of directly named places.

    This reader is independent of the compact map summaries used for resource
    availability and PresentationPacket construction. Map references are
    source records in their own right, so the returned verse labels retain the
    catalog's exact verse bounds.
    """

    bounded_limit = max(1, min(int(limit), 25))
    bounded_offset = max(0, int(offset))
    reference_parameters = (
        str(book).strip(),
        int(chapter),
        int(verse_end),
        int(verse_start),
    )
    relation_filter = "r.relationship_type = 'directly_named'"
    source_filter = (
        "trim(coalesce(p.name, '')) <> '' AND "
        "(trim(coalesce(p.source_name, '')) <> '' OR trim(coalesce(p.source_url, '')) <> '')"
    )

    with connect(path) as connection:
        if prepare_schema:
            ensure_schema(connection)
        total = int(connection.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT p.id
                FROM place_references AS r
                JOIN biblical_places AS p ON p.id = r.place_id
                WHERE lower(r.book) = lower(?)
                  AND r.chapter = ?
                  AND r.verse_start <= ?
                  AND r.verse_end >= ?
                  AND {relation_filter}
                  AND {source_filter}
                GROUP BY p.id
            )
            """,
            reference_parameters,
        ).fetchone()[0])
        page_offset = min(bounded_offset, total)
        place_rows = connection.execute(
            f"""
            SELECT p.id, p.name, p.description, p.modern_location,
                   p.ancient_region, p.confidence, p.confidence_rank,
                   p.source_name, p.source_url, p.license,
                   MIN(r.verse_end - r.verse_start) AS anchor_span
            FROM place_references AS r
            JOIN biblical_places AS p ON p.id = r.place_id
            WHERE lower(r.book) = lower(?)
              AND r.chapter = ?
              AND r.verse_start <= ?
              AND r.verse_end >= ?
              AND {relation_filter}
              AND {source_filter}
            GROUP BY p.id, p.name, p.description, p.modern_location,
                     p.ancient_region, p.confidence, p.confidence_rank,
                     p.source_name, p.source_url, p.license
            ORDER BY anchor_span ASC, p.confidence_rank DESC,
                     lower(p.name) ASC, p.id ASC
            LIMIT ? OFFSET ?
            """,
            (*reference_parameters, bounded_limit, page_offset),
        ).fetchall()

        references_by_place: dict[str, list[dict[str, Any]]] = {}
        if place_rows:
            place_ids = [str(row["id"]) for row in place_rows]
            placeholders = ",".join("?" for _ in place_ids)
            ref_rows = connection.execute(
                f"""
                SELECT place_id, book, chapter, verse_start, verse_end,
                       relationship_type, notes
                FROM place_references
                WHERE place_id IN ({placeholders})
                  AND lower(book) = lower(?)
                  AND chapter = ?
                  AND verse_start <= ?
                  AND verse_end >= ?
                  AND relationship_type = 'directly_named'
                ORDER BY place_id, verse_start, verse_end, relationship_type, id
                """,
                (*place_ids, *reference_parameters),
            ).fetchall()
            for row in ref_rows:
                references_by_place.setdefault(str(row["place_id"]), []).append({
                    "book": str(row["book"]),
                    "chapter": int(row["chapter"]),
                    "verse_start": int(row["verse_start"]),
                    "verse_end": int(row["verse_end"]),
                    "relationship": str(row["relationship_type"]),
                    "notes": str(row["notes"] or ""),
                })

    items = []
    for row in place_rows:
        place_id = str(row["id"])
        references = references_by_place.get(place_id, [])
        labels = sorted({
            _location_reference_label(reference)
            for reference in references
        }, key=_reference_sort_key)
        confidence = str(row["confidence"] or "unknown").strip().casefold() or "unknown"
        item = {
            "id": place_id,
            "origin": "maps",
            "title": str(row["name"] or "").strip(),
            "references": labels,
            "relationship": "directly_named",
            "region": str(row["ancient_region"] or "").strip(),
            "modern_location": str(row["modern_location"] or "").strip(),
            "description": str(row["description"] or "").strip(),
            "map_confidence": confidence,
            "provenance": {
                "name": str(row["source_name"] or "").strip(),
                "url": str(row["source_url"] or "").strip(),
                "license": str(row["license"] or "").strip(),
            },
            # The map resource id comes from the exact joined catalog row.
            "map_focus_id": place_id,
        }
        if confidence in {"possible", "uncertain", "unknown"}:
            item["identification_uncertainty"] = (
                f"The map catalog rates this identification as {confidence}; "
                "that rating does not establish historical or archaeological certainty."
            )
        specific_notes = [
            reference["notes"]
            for reference in references
            if reference["notes"]
            and not reference["notes"].startswith("Imported from OpenBible.info")
        ]
        if specific_notes:
            item["passage_role"] = specific_notes[0]
        items.append(item)

    return {"items": items, "total": total, "offset": page_offset, "limit": bounded_limit}


def _location_reference_label(reference: dict[str, Any]) -> str:
    label = f"{reference['book']} {reference['chapter']}"
    start = int(reference["verse_start"])
    end = int(reference["verse_end"])
    if start == end:
        return f"{label}:{start}"
    return f"{label}:{start}-{end}"


def _reference_sort_key(reference: str) -> tuple[str, int, int]:
    prefix, _, verse = reference.partition(":")
    start, separator, end = verse.partition("-")
    try:
        return prefix.casefold(), int(start), int(end if separator else start)
    except ValueError:
        return reference.casefold(), 0, 0


def list_historical_layers(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    period_filter_matches: PeriodFilter,
    periods_from_value: PeriodsFromValue,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM historical_layers
            ORDER BY confidence_rank DESC, period, name
            """
        ).fetchall()
    layers = [
        attach_source(
            historical_layer_from_row(row, periods_from_value=periods_from_value),
            path,
        )
        for row in rows
    ]
    return [layer for layer in layers if period_filter_matches(layer["periods"], period)]


def list_political_context_layers(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    list_political_context_references: ReferenceLoader,
    period_filter_matches: PeriodFilter,
    periods_from_value: PeriodsFromValue,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM political_context_layers
            ORDER BY confidence_rank DESC, sort_order, name
            """
        ).fetchall()
    layers = [
        attach_source(
            political_context_layer_from_row(row, periods_from_value=periods_from_value),
            path,
        )
        for row in rows
    ]
    for layer in layers:
        layer["scripture_links"] = list_political_context_references(layer["id"], path)
        layer["reference_count"] = len(layer["scripture_links"])
    return [layer for layer in layers if period_filter_matches(layer["periods"], period)]


def get_political_context_layer(
    layer_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    attach_source: AttachSource,
    list_political_context_references: ReferenceLoader,
    periods_from_value: PeriodsFromValue,
) -> dict[str, Any]:
    with connect(path) as connection:
        ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM political_context_layers WHERE id = ?",
            (layer_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("political context layer not found")
    layer = political_context_layer_from_row(row, periods_from_value=periods_from_value)
    layer["scripture_links"] = list_political_context_references(layer["id"], path)
    layer["reference_count"] = len(layer["scripture_links"])
    return attach_source(layer, path)


def list_political_context_references(
    layer_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        if layer_id is None:
            rows = connection.execute(
                "SELECT * FROM political_context_references ORDER BY book, chapter, verse_start, verse_end"
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM political_context_references
                WHERE context_id = ?
                ORDER BY book, chapter, verse_start, verse_end
                """,
                (layer_id,),
            ).fetchall()
    return [political_context_reference_from_row(row) for row in rows]


def biblical_place_from_row(
    row: Any,
    *,
    periods_from_value: PeriodsFromValue,
    biblical_place_periods: dict[str, list[str]],
) -> dict[str, Any]:
    aliases = _json_list(row["aliases"])
    periods = periods_from_value(row["periods"], fallback=biblical_place_periods.get(row["id"], []))
    return {
        "id": row["id"],
        "name": row["name"],
        "aliases": [str(alias) for alias in aliases if str(alias).strip()],
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


def place_reference_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "place_id": row["place_id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "verse_start": int(row["verse_start"]),
        "verse_end": int(row["verse_end"]),
        "relationship_type": row["relationship_type"],
        "notes": row["notes"],
    }


def map_route_from_row(
    row: Any,
    *,
    periods_from_value: PeriodsFromValue,
) -> dict[str, Any]:
    geojson = _json_dict(row["geojson"])
    periods = periods_from_value(row["periods"], fallback=row["period"])
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "period": row["period"],
        "periods": periods,
        "route_type": row["route_type"],
        "geojson": geojson,
        "confidence": row["confidence"],
        "confidence_rank": int(row["confidence_rank"]),
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "source_id": row["source_id"] if "source_id" in row.keys() else "",
        "notes": row["notes"],
    }


def route_reference_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "route_id": row["route_id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "verse_start": int(row["verse_start"]),
        "verse_end": int(row["verse_end"]),
        "relationship_type": row["relationship_type"],
        "notes": row["notes"],
    }


def historical_layer_from_row(
    row: Any,
    *,
    periods_from_value: PeriodsFromValue,
) -> dict[str, Any]:
    geojson = _json_dict(row["geojson"])
    periods = periods_from_value(row["periods"], fallback=row["period"])
    return {
        "id": row["id"],
        "name": row["name"],
        "period": row["period"],
        "periods": periods,
        "description": row["description"],
        "layer_type": row["layer_type"],
        "geojson": geojson,
        "confidence": row["confidence"],
        "confidence_rank": int(row["confidence_rank"]),
        "source_id": row["source_id"] if "source_id" in row.keys() else "",
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "notes": row["notes"],
    }


def political_context_layer_from_row(
    row: Any,
    *,
    periods_from_value: PeriodsFromValue,
) -> dict[str, Any]:
    geojson = _json_dict(row["geojson"])
    periods = periods_from_value(row["periods"], fallback=row["period"])
    return {
        "id": row["id"],
        "name": row["name"],
        "entity_type": row["entity_type"],
        "period": row["period"],
        "periods": periods,
        "summary": row["summary"],
        "description": row["description"],
        "layer_type": row["layer_type"],
        "sort_order": int(row["sort_order"]),
        "geojson": geojson,
        "confidence": row["confidence"],
        "confidence_rank": int(row["confidence_rank"]),
        "source_id": row["source_id"] if "source_id" in row.keys() else "",
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "notes": row["notes"],
    }


def political_context_reference_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "context_id": row["context_id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "verse_start": int(row["verse_start"]),
        "verse_end": int(row["verse_end"]),
        "relationship_type": row["relationship_type"],
        "notes": row["notes"],
    }


def _json_dict(value: Any) -> dict[str, Any]:
    try:
        decoded = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _json_list(value: Any) -> list[Any]:
    try:
        decoded = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []
