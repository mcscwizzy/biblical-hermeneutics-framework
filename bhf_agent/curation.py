"""Local curation helpers for editable study data."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .bible import BibleError, normalize_book_name
from .study_db import (
    DEFAULT_DB_PATH,
    StudyDataError,
    _connect,
    _ensure_schema,
    get_archaeology_item,
    get_archaeology_site,
    get_biblical_place,
    list_archaeology_items,
    list_archaeology_scripture_links,
    list_archaeology_sites,
    list_biblical_places,
    list_historical_layers,
    list_map_routes,
    list_place_references,
    list_route_references,
)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_default(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)


def _parse_json_field(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    text = str(value).strip()
    if not text:
        return default
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StudyDataError("record_json must contain valid JSON") from exc
    return parsed


def _positive_int(value: Any, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise StudyDataError(f"{label} must be a positive integer") from exc
    if number <= 0:
        raise StudyDataError(f"{label} must be a positive integer")
    return number


def _float_or_none(value: Any, label: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise StudyDataError(f"{label} must be a number") from exc


@dataclass(frozen=True)
class FieldSpec:
    name: str
    kind: str = "text"
    required: bool = False
    normalize_book: bool = False


@dataclass(frozen=True)
class CollectionSpec:
    key: str
    title: str
    table: str
    order_by: str
    fields: tuple[FieldSpec, ...]
    summary_fields: tuple[str, ...]
    list_fn: Callable[[str | None, str | None, str | None], list[dict[str, Any]]] | None = None
    get_fn: Callable[[str, str | None], dict[str, Any]] | None = None


def _core_list(kind: str) -> Callable[[str | None, str | None, str | None], list[dict[str, Any]]]:
    def _list(period: str | None = None, _unused: str | None = None, path: str | None = None) -> list[dict[str, Any]]:
        resolved = path or DEFAULT_DB_PATH
        if kind == "places":
            return list_biblical_places(period=period, path=resolved)
        if kind == "place_references":
            return list_place_references(path=resolved)
        if kind == "routes":
            return list_map_routes(period=period, path=resolved)
        if kind == "route_references":
            return list_route_references(path=resolved)
        if kind == "historical_layers":
            return list_historical_layers(period=period, path=resolved)
        if kind == "archaeology_sites":
            return list_archaeology_sites(period=period, path=resolved)
        if kind == "archaeology_items":
            return list_archaeology_items(path=resolved)
        if kind == "archaeology_scripture_links":
            return list_archaeology_scripture_links(path=resolved)
        raise StudyDataError(f"unsupported collection: {kind}")

    return _list


def _core_get(kind: str) -> Callable[[str, str | None], dict[str, Any]]:
    def _get(item_id: str, path: str | None = None) -> dict[str, Any]:
        resolved = path or DEFAULT_DB_PATH
        if kind == "places":
            return get_biblical_place(item_id, path=resolved)
        if kind == "archaeology_sites":
            return get_archaeology_site(item_id, path=resolved)
        if kind == "archaeology_items":
            return get_archaeology_item(item_id, path=resolved)
        if kind == "routes":
            with _connect(resolved) as connection:
                _ensure_schema(connection)
                row = connection.execute("SELECT * FROM map_routes WHERE id = ?", (item_id,)).fetchone()
            if row is None:
                raise StudyDataError("map route not found")
            from .study_db import _map_route_from_row

            route = _map_route_from_row(row)
            route["scripture_links"] = list_route_references(route["id"], path=resolved)
            route["reference_count"] = len(route["scripture_links"])
            return route
        if kind == "historical_layers":
            with _connect(resolved) as connection:
                _ensure_schema(connection)
                row = connection.execute(
                    "SELECT * FROM historical_layers WHERE id = ?",
                    (item_id,),
                ).fetchone()
            if row is None:
                raise StudyDataError("historical layer not found")
            from .study_db import _historical_layer_from_row

            return _historical_layer_from_row(row)
        raise StudyDataError(f"unsupported collection: {kind}")

    return _get


CURATION_COLLECTIONS: dict[str, CollectionSpec] = {
    "places": CollectionSpec(
        key="places",
        title="Places",
        table="biblical_places",
        order_by="confidence_rank DESC, name",
        fields=(
            FieldSpec("id", required=False),
            FieldSpec("name", required=True),
            FieldSpec("aliases", kind="json_list"),
            FieldSpec("periods", kind="json_list"),
            FieldSpec("latitude", kind="float"),
            FieldSpec("longitude", kind="float"),
            FieldSpec("modern_location"),
            FieldSpec("ancient_region"),
            FieldSpec("description"),
            FieldSpec("confidence"),
            FieldSpec("confidence_rank", kind="int"),
            FieldSpec("source_name"),
            FieldSpec("source_url"),
            FieldSpec("license"),
            FieldSpec("notes"),
        ),
        summary_fields=("name", "confidence", "confidence_rank"),
        list_fn=_core_list("places"),
        get_fn=_core_get("places"),
    ),
    "place_references": CollectionSpec(
        key="place_references",
        title="Place Aliases and Links",
        table="place_references",
        order_by="place_id, book, chapter, verse_start, verse_end",
        fields=(
            FieldSpec("id", required=False),
            FieldSpec("place_id", required=True),
            FieldSpec("book", required=True, normalize_book=True),
            FieldSpec("chapter", kind="int", required=True),
            FieldSpec("verse_start", kind="int", required=True),
            FieldSpec("verse_end", kind="int", required=True),
            FieldSpec("relationship_type", required=True),
            FieldSpec("notes"),
        ),
        summary_fields=("place_id", "book", "chapter"),
        list_fn=_core_list("place_references"),
    ),
    "routes": CollectionSpec(
        key="routes",
        title="Routes",
        table="map_routes",
        order_by="confidence_rank DESC, name",
        fields=(
            FieldSpec("id", required=False),
            FieldSpec("name", required=True),
            FieldSpec("description"),
            FieldSpec("period"),
            FieldSpec("periods", kind="json_list"),
            FieldSpec("route_type"),
            FieldSpec("geojson", kind="json_object", required=True),
            FieldSpec("confidence"),
            FieldSpec("confidence_rank", kind="int"),
            FieldSpec("source_name"),
            FieldSpec("source_url"),
            FieldSpec("notes"),
        ),
        summary_fields=("name", "route_type", "confidence"),
        list_fn=_core_list("routes"),
        get_fn=_core_get("routes"),
    ),
    "route_references": CollectionSpec(
        key="route_references",
        title="Route Scripture Links",
        table="route_references",
        order_by="route_id, book, chapter, verse_start, verse_end",
        fields=(
            FieldSpec("id", required=False),
            FieldSpec("route_id", required=True),
            FieldSpec("book", required=True, normalize_book=True),
            FieldSpec("chapter", kind="int", required=True),
            FieldSpec("verse_start", kind="int", required=True),
            FieldSpec("verse_end", kind="int", required=True),
            FieldSpec("relationship_type", required=True),
            FieldSpec("notes"),
        ),
        summary_fields=("route_id", "book", "chapter"),
        list_fn=_core_list("route_references"),
    ),
    "historical_layers": CollectionSpec(
        key="historical_layers",
        title="Historical Layers",
        table="historical_layers",
        order_by="confidence_rank DESC, period, name",
        fields=(
            FieldSpec("id", required=False),
            FieldSpec("name", required=True),
            FieldSpec("period"),
            FieldSpec("periods", kind="json_list"),
            FieldSpec("description"),
            FieldSpec("layer_type"),
            FieldSpec("geojson", kind="json_object", required=True),
            FieldSpec("confidence"),
            FieldSpec("confidence_rank", kind="int"),
            FieldSpec("source_name"),
            FieldSpec("source_url"),
            FieldSpec("notes"),
        ),
        summary_fields=("name", "layer_type", "confidence"),
        list_fn=_core_list("historical_layers"),
        get_fn=_core_get("historical_layers"),
    ),
    "archaeology_sites": CollectionSpec(
        key="archaeology_sites",
        title="Archaeology Sites",
        table="archaeology_sites",
        order_by="confidence_rank DESC, name",
        fields=(
            FieldSpec("id", required=False),
            FieldSpec("name", required=True),
            FieldSpec("site_type"),
            FieldSpec("period"),
            FieldSpec("periods", kind="json_list"),
            FieldSpec("latitude", kind="float"),
            FieldSpec("longitude", kind="float"),
            FieldSpec("modern_location"),
            FieldSpec("ancient_region"),
            FieldSpec("description"),
            FieldSpec("confidence"),
            FieldSpec("confidence_rank", kind="int"),
            FieldSpec("source_name"),
            FieldSpec("source_url"),
            FieldSpec("license"),
            FieldSpec("notes"),
        ),
        summary_fields=("name", "site_type", "confidence"),
        list_fn=_core_list("archaeology_sites"),
        get_fn=_core_get("archaeology_sites"),
    ),
    "archaeology_items": CollectionSpec(
        key="archaeology_items",
        title="Archaeology Items",
        table="archaeology_items",
        order_by="confidence_rank DESC, period, name",
        fields=(
            FieldSpec("id", required=False),
            FieldSpec("site_id", required=True),
            FieldSpec("name", required=True),
            FieldSpec("item_type"),
            FieldSpec("period"),
            FieldSpec("periods", kind="json_list"),
            FieldSpec("relationship"),
            FieldSpec("why_it_matters"),
            FieldSpec("bhf_caution"),
            FieldSpec("confidence"),
            FieldSpec("confidence_rank", kind="int"),
            FieldSpec("source_name"),
            FieldSpec("source_url"),
            FieldSpec("license"),
            FieldSpec("notes"),
        ),
        summary_fields=("name", "item_type", "confidence"),
        list_fn=_core_list("archaeology_items"),
        get_fn=_core_get("archaeology_items"),
    ),
    "archaeology_scripture_links": CollectionSpec(
        key="archaeology_scripture_links",
        title="Archaeology Scripture Links",
        table="archaeology_scripture_links",
        order_by="book, chapter, verse_start, verse_end",
        fields=(
            FieldSpec("id", required=False),
            FieldSpec("item_id", required=True),
            FieldSpec("book", required=True, normalize_book=True),
            FieldSpec("chapter", kind="int", required=True),
            FieldSpec("verse_start", kind="int", required=True),
            FieldSpec("verse_end", kind="int", required=True),
            FieldSpec("relationship_type", required=True),
            FieldSpec("notes"),
        ),
        summary_fields=("item_id", "book", "chapter"),
        list_fn=_core_list("archaeology_scripture_links"),
    ),
    "sources": CollectionSpec(
        key="sources",
        title="Sources",
        table="sources",
        order_by="label",
        fields=(
            FieldSpec("id", required=False),
            FieldSpec("label", required=True),
            FieldSpec("url"),
            FieldSpec("license"),
            FieldSpec("notes"),
        ),
        summary_fields=("label", "url"),
    ),
    "confidence_labels": CollectionSpec(
        key="confidence_labels",
        title="Confidence Labels",
        table="confidence_labels",
        order_by="rank DESC, label",
        fields=(
            FieldSpec("id", required=False),
            FieldSpec("label", required=True),
            FieldSpec("rank", kind="int", required=True),
            FieldSpec("description"),
            FieldSpec("notes"),
        ),
        summary_fields=("label", "rank"),
    ),
}


def list_curation_collections(path: str | None = None) -> list[dict[str, Any]]:
    resolved = path or DEFAULT_DB_PATH
    collections: list[dict[str, Any]] = []
    for spec in CURATION_COLLECTIONS.values():
        collections.append(
            {
                "key": spec.key,
                "title": spec.title,
                "count": len(list_curation_records(spec.key, path=resolved)),
            }
        )
    return collections


def list_curation_records(collection: str, path: str | None = None) -> list[dict[str, Any]]:
    spec = _spec_for(collection)
    if spec.list_fn is not None:
        return spec.list_fn(None, None, path or DEFAULT_DB_PATH)
    with _connect(path or DEFAULT_DB_PATH) as connection:
        _ensure_schema(connection)
        rows = connection.execute(f"SELECT * FROM {spec.table} ORDER BY {spec.order_by}").fetchall()
    return [_row_to_record(spec, row) for row in rows]


def get_curation_record(collection: str, record_id: str, path: str | None = None) -> dict[str, Any]:
    spec = _spec_for(collection)
    if spec.get_fn is not None:
        return spec.get_fn(record_id, path or DEFAULT_DB_PATH)
    with _connect(path or DEFAULT_DB_PATH) as connection:
        _ensure_schema(connection)
        row = connection.execute(f"SELECT * FROM {spec.table} WHERE id = ?", (record_id,)).fetchone()
    if row is None:
        raise StudyDataError(f"{spec.title[:-1].lower()} not found")
    return _row_to_record(spec, row)


def save_curation_record(
    collection: str,
    payload: dict[str, Any],
    path: str | None = None,
) -> dict[str, Any]:
    spec = _spec_for(collection)
    record = _normalized_record(spec, payload)
    resolved = path or DEFAULT_DB_PATH
    now = _timestamp()
    columns = [field.name for field in spec.fields]
    values = [_value_for_db(record.get(field.name), field) for field in spec.fields]
    with _connect(resolved) as connection:
        _ensure_schema(connection)
        existing = connection.execute(
            f"SELECT id FROM {spec.table} WHERE id = ?",
            (record["id"],),
        ).fetchone()
        if existing is None:
            placeholders = ", ".join(["?"] * len(columns))
            connection.execute(
                f"INSERT INTO {spec.table} ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
        else:
            assignments = ", ".join(f"{column} = ?" for column in columns if column != "id")
            update_values = [values[index] for index, field in enumerate(spec.fields) if field.name != "id"]
            update_values.append(record["id"])
            connection.execute(
                f"UPDATE {spec.table} SET {assignments} WHERE id = ?",
                update_values,
            )
    saved = get_curation_record(collection, record["id"], path=resolved)
    saved.setdefault("created_at", now)
    saved.setdefault("updated_at", now)
    return saved


def delete_curation_record(collection: str, record_id: str, path: str | None = None) -> bool:
    spec = _spec_for(collection)
    resolved = path or DEFAULT_DB_PATH
    with _connect(resolved) as connection:
        _ensure_schema(connection)
        cursor = connection.execute(f"DELETE FROM {spec.table} WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            raise StudyDataError(f"{spec.title[:-1].lower()} not found")
    return True


def export_curation_bundle(path: str | None = None) -> dict[str, Any]:
    resolved = path or DEFAULT_DB_PATH
    return {
        "generated_at": _timestamp(),
        "collections": {
            key: list_curation_records(key, path=resolved) for key in CURATION_COLLECTIONS
        },
    }


def import_curation_bundle(payload: dict[str, Any], path: str | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise StudyDataError("import payload must be a JSON object")
    collections = payload.get("collections")
    if not isinstance(collections, dict):
        raise StudyDataError("import payload must include a collections object")
    resolved = path or DEFAULT_DB_PATH
    imported: dict[str, int] = {}
    with _connect(resolved) as connection:
        _ensure_schema(connection)
        for collection, records in collections.items():
            spec = _spec_for(collection)
            if not isinstance(records, list):
                raise StudyDataError(f"{collection} must be a JSON array")
            connection.execute(f"DELETE FROM {spec.table}")
            imported[collection] = 0
            for record in records:
                if not isinstance(record, dict):
                    raise StudyDataError(f"{collection} records must be JSON objects")
                normalized = _normalized_record(spec, record)
                columns = [field.name for field in spec.fields]
                values = [_value_for_db(normalized.get(field.name), field) for field in spec.fields]
                placeholders = ", ".join(["?"] * len(columns))
                connection.execute(
                    f"INSERT INTO {spec.table} ({', '.join(columns)}) VALUES ({placeholders})",
                    values,
                )
                imported[collection] += 1
    return {"imported": imported}


def _spec_for(collection: str) -> CollectionSpec:
    try:
        return CURATION_COLLECTIONS[collection]
    except KeyError as exc:
        raise StudyDataError(f"unknown curation collection: {collection}") from exc


def _row_to_record(spec: CollectionSpec, row: sqlite3.Row) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for field in spec.fields:
        record[field.name] = _value_from_db(row[field.name], field)
    return record


def _normalized_record(spec: CollectionSpec, payload: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for field in spec.fields:
        value = payload.get(field.name)
        if field.name == "id" and not value:
            value = uuid.uuid4().hex
        if field.required and (value is None or value == ""):
            raise StudyDataError(f"{field.name.replace('_', ' ')} is required")
        record[field.name] = _normalize_value(value, field)
    return record


def _normalize_value(value: Any, field: FieldSpec) -> Any:
    if field.kind == "int":
        if value in (None, ""):
            return 0
        return _positive_int(value, field.name)
    if field.kind == "float":
        return _float_or_none(value, field.name)
    if field.kind == "json_list":
        parsed = _parse_json_field(value, [])
        if not isinstance(parsed, list):
            raise StudyDataError(f"{field.name} must be a JSON array")
        return [str(item) for item in parsed if str(item).strip()]
    if field.kind == "json_object":
        parsed = _parse_json_field(value, {})
        if not isinstance(parsed, dict):
            raise StudyDataError(f"{field.name} must be a JSON object")
        return parsed
    text = "" if value is None else str(value).strip()
    if field.normalize_book and text:
        try:
            text = normalize_book_name(text)
        except BibleError as exc:
            raise StudyDataError(str(exc)) from exc
    return text


def _value_for_db(value: Any, field: FieldSpec) -> Any:
    if field.kind in {"json_list", "json_object"}:
        return json.dumps(value, sort_keys=True)
    if field.kind == "float":
        return value
    if field.kind == "int":
        return int(value or 0)
    return value if value is not None else ""


def _value_from_db(value: Any, field: FieldSpec) -> Any:
    if field.kind == "json_list":
        if value in (None, ""):
            return []
        try:
            parsed = json.loads(str(value))
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    if field.kind == "json_object":
        if value in (None, ""):
            return {}
        try:
            parsed = json.loads(str(value))
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    if field.kind == "float":
        return float(value) if value is not None else None
    if field.kind == "int":
        return int(value or 0)
    return "" if value is None else value
