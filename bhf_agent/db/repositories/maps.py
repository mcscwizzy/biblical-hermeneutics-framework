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
