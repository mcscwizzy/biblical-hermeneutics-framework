"""SQLite-backed local study data."""

from __future__ import annotations

import json
import sqlite3
import re
import uuid
from pathlib import Path
from typing import Any

from .db.common import (
    DEFAULT_DB_PATH,
    StudyDataError,
    timestamp as _timestamp,
    validated_reference as _validated_reference,
)
from .db.repositories import archaeology as _archaeology_repo
from .db.repositories import map_notes as _map_notes_repo
from .db.repositories import maps as _maps_repo
from .db.repositories import manuscripts as _manuscripts_repo
from .db.repositories import reader_state as _reader_state_repo
from .db.repositories import sources as _sources_repo

SCHEMA_VERSION = 13
OPENBIBLE_PLACES_PATH = Path(__file__).resolve().parent / "data" / "openbible_places.json"
BROAD_PERIOD_LABEL = "Broad / uncertain period"
CANONICAL_PERIOD_LABELS = (
    BROAD_PERIOD_LABEL,
    "Divided Kingdom",
    "Assyrian period",
    "Babylonian period",
    "Persian period",
    "Hellenistic period",
    "NT / Roman period",
)

_PERIOD_NORMALIZATION_MAP = {
    "new testament / roman period": "NT / Roman period",
    "new testament / roman": "NT / Roman period",
    "roman period": "NT / Roman period",
    "nt / roman": "NT / Roman period",
    "broad / uncertain": BROAD_PERIOD_LABEL,
    "broad / uncertain period": BROAD_PERIOD_LABEL,
    "uncertain / broad period": BROAD_PERIOD_LABEL,
    "uncertain": BROAD_PERIOD_LABEL,
    "broad": BROAD_PERIOD_LABEL,
}

_LEGACY_PERIOD_BUCKETS = {
    "iron age ii": ["Divided Kingdom", "Assyrian period"],
    "late iron age": ["Assyrian period", "Babylonian period"],
    "9th century bc": ["Divided Kingdom", "Assyrian period"],
    "late 8th century bc": ["Assyrian period"],
    "late 7th century bc": ["Babylonian period"],
    "6th century bc": ["Babylonian period", "Persian period"],
    "neo-assyrian period": ["Assyrian period"],
    "neo-babylonian / persian period": ["Babylonian period", "Persian period"],
    "herodian / roman period": ["NT / Roman period"],
    "second temple period": ["Hellenistic period", "NT / Roman period"],
    "second temple / roman period": ["NT / Roman period"],
    "2nd century bc to 1st century ad": ["Hellenistic period", "NT / Roman period"],
    "1st century ad": ["NT / Roman period"],
    "new testament / roman period": ["NT / Roman period"],
    "divided kingdom": ["Divided Kingdom"],
    "assyrian period": ["Assyrian period"],
    "babylonian period": ["Babylonian period"],
    "persian period": ["Persian period"],
    "hellenistic period": ["Hellenistic period"],
}

_BIBLICAL_PLACE_PERIODS = {
    "jerusalem": ["Divided Kingdom", "Assyrian period", "Babylonian period", "Persian period", "NT / Roman period"],
    "bethlehem": ["Divided Kingdom", "Assyrian period", "Babylonian period", "Persian period", "NT / Roman period"],
    "capernaum": ["NT / Roman period"],
    "caesarea-maritima": ["NT / Roman period"],
    "babylon": ["Babylonian period", "Persian period"],
}

_POLITICAL_CONTEXT_PERIODS = {
    "egypt": ["Broad / uncertain period", "Divided Kingdom", "Assyrian period", "Babylonian period", "Persian period", "Hellenistic period", "NT / Roman period"],
    "canaanite-city-states": ["Broad / uncertain period", "Divided Kingdom"],
    "philistia": ["Divided Kingdom", "Assyrian period"],
    "israel": ["Divided Kingdom", "Assyrian period"],
    "judah": ["Divided Kingdom", "Assyrian period", "Babylonian period", "Persian period"],
    "aram-damascus": ["Divided Kingdom", "Assyrian period"],
    "assyria": ["Assyrian period"],
    "babylon": ["Babylonian period"],
    "persia": ["Persian period"],
    "greece": ["Hellenistic period"],
    "rome": ["NT / Roman period"],
}

_MANUSCRIPT_PERIODS = {
    "dead-sea-scrolls": ["Hellenistic period", "NT / Roman period"],
    "nash-papyrus": ["Hellenistic period"],
    "codex-sinaiticus": ["NT / Roman period"],
    "codex-vaticanus": ["NT / Roman period"],
    "aleppo-codex": ["NT / Roman period"],
    "chester-beatty-papyri": ["NT / Roman period"],
}

def initialize_database(path: str | Path = DEFAULT_DB_PATH) -> None:
    _reader_state_repo.initialize_database(path=path, ensure_schema=_ensure_schema)


def list_notes(
    book: str | None = None,
    chapter: int | str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _reader_state_repo.list_notes(
        book=book,
        chapter=chapter,
        path=path,
        ensure_schema=_ensure_schema,
    )


def create_note(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    return _reader_state_repo.create_note(
        data,
        path=path,
        ensure_schema=_ensure_schema,
    )


def update_note(
    note_id: str,
    updates: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    return _reader_state_repo.update_note(
        note_id,
        updates,
        path=path,
        ensure_schema=_ensure_schema,
    )


def delete_note(note_id: str, path: str | Path = DEFAULT_DB_PATH) -> bool:
    return _reader_state_repo.delete_note(
        note_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def list_highlights(
    book: str | None = None,
    chapter: int | str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _reader_state_repo.list_highlights(
        book=book,
        chapter=chapter,
        path=path,
        ensure_schema=_ensure_schema,
    )


def create_highlight(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    return _reader_state_repo.create_highlight(
        data,
        path=path,
        ensure_schema=_ensure_schema,
    )


def delete_highlight(highlight_id: str, path: str | Path = DEFAULT_DB_PATH) -> bool:
    return _reader_state_repo.delete_highlight(
        highlight_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def list_saved_studies(
    book: str | None = None,
    chapter: int | str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _reader_state_repo.list_saved_studies(
        book=book,
        chapter=chapter,
        path=path,
        ensure_schema=_ensure_schema,
    )


def get_saved_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    return _reader_state_repo.get_saved_study(
        study_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def create_saved_study(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    return _reader_state_repo.create_saved_study(
        data,
        path=path,
        ensure_schema=_ensure_schema,
    )


def delete_saved_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
) -> bool:
    return _reader_state_repo.delete_saved_study(
        study_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def record_study_action(
    action_type: str,
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    return _reader_state_repo.record_study_action(
        action_type,
        data,
        path=path,
        ensure_schema=_ensure_schema,
    )


def list_biblical_places(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _maps_repo.list_biblical_places(
        period=period,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        period_filter_matches=_period_filter_matches,
        periods_from_value=_periods_from_value,
        biblical_place_periods=_BIBLICAL_PLACE_PERIODS,
    )


def get_biblical_place(place_id: str, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    return _maps_repo.get_biblical_place(
        place_id,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        periods_from_value=_periods_from_value,
        biblical_place_periods=_BIBLICAL_PLACE_PERIODS,
    )


def list_place_references(
    place_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _maps_repo.list_place_references(
        place_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def list_map_routes(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _maps_repo.list_map_routes(
        period=period,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        list_route_references=lambda route_id, db_path: list_route_references(route_id, path=db_path),
        period_filter_matches=_period_filter_matches,
        periods_from_value=_periods_from_value,
    )


def list_route_references(
    route_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _maps_repo.list_route_references(
        route_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def list_historical_layers(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _maps_repo.list_historical_layers(
        period=period,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        period_filter_matches=_period_filter_matches,
        periods_from_value=_periods_from_value,
    )


def list_political_context_layers(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _maps_repo.list_political_context_layers(
        period=period,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        list_political_context_references=lambda layer_id, db_path: list_political_context_references(
            layer_id, path=db_path
        ),
        period_filter_matches=_period_filter_matches,
        periods_from_value=_periods_from_value,
    )


def get_political_context_layer(
    layer_id: str,
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    return _maps_repo.get_political_context_layer(
        layer_id,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        list_political_context_references=lambda current_layer_id, db_path: list_political_context_references(
            current_layer_id, path=db_path
        ),
        periods_from_value=_periods_from_value,
    )


def list_political_context_references(
    layer_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _maps_repo.list_political_context_references(
        layer_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def list_manuscript_items(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _manuscripts_repo.list_manuscript_items(
        period=period,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        list_manuscript_scripture_links=lambda item_id, db_path: list_manuscript_scripture_links(
            item_id, path=db_path
        ),
        period_filter_matches=_period_filter_matches,
        periods_from_value=_periods_from_value,
    )


def get_manuscript_item(
    item_id: str,
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    return _manuscripts_repo.get_manuscript_item(
        item_id,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        list_manuscript_scripture_links=lambda current_item_id, db_path: list_manuscript_scripture_links(
            current_item_id, path=db_path
        ),
        periods_from_value=_periods_from_value,
    )


def list_manuscript_scripture_links(
    item_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _manuscripts_repo.list_manuscript_scripture_links(
        item_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def list_archaeology_sites(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _archaeology_repo.list_archaeology_sites(
        period=period,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        list_archaeology_items=lambda site_id, current_period, db_path: list_archaeology_items(
            site_id, period=current_period, path=db_path
        ),
        period_filter_matches=_period_filter_matches,
        periods_from_value=_periods_from_value,
    )


def get_archaeology_site(site_id: str, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    return _archaeology_repo.get_archaeology_site(
        site_id,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        list_archaeology_items=lambda current_site_id, current_period, db_path: list_archaeology_items(
            current_site_id, period=current_period, path=db_path
        ),
        periods_from_value=_periods_from_value,
    )


def list_archaeology_items(
    site_id: str | None = None,
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _archaeology_repo.list_archaeology_items(
        site_id,
        period,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        list_archaeology_scripture_links=lambda item_id, db_path: list_archaeology_scripture_links(
            item_id, path=db_path
        ),
        period_filter_matches=_period_filter_matches,
        periods_from_value=_periods_from_value,
    )


def get_archaeology_item(item_id: str, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    return _archaeology_repo.get_archaeology_item(
        item_id,
        path=path,
        ensure_schema=_ensure_schema,
        attach_source=_attach_source,
        list_archaeology_scripture_links=lambda current_item_id, db_path: list_archaeology_scripture_links(
            current_item_id, path=db_path
        ),
        periods_from_value=_periods_from_value,
    )


def list_archaeology_scripture_links(
    item_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _archaeology_repo.list_archaeology_scripture_links(
        item_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def list_sources(path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    return _sources_repo.list_sources(
        path=path,
        ensure_schema=_ensure_schema,
    )


def get_source(source_id: str, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    return _sources_repo.get_source(
        source_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def list_saved_map_studies(
    book: str | None = None,
    chapter: int | str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _map_notes_repo.list_saved_map_studies(
        book=book,
        chapter=chapter,
        path=path,
        ensure_schema=_ensure_schema,
    )


def get_saved_map_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    return _map_notes_repo.get_saved_map_study(
        study_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def create_saved_map_study(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    return _map_notes_repo.create_saved_map_study(
        data,
        path=path,
        ensure_schema=_ensure_schema,
        validate_saved_map_study=_validated_saved_map_study,
    )


def delete_saved_map_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
) -> bool:
    return _map_notes_repo.delete_saved_map_study(
        study_id,
        path=path,
        ensure_schema=_ensure_schema,
    )


def create_map_note(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    return _map_notes_repo.create_map_note(
        data,
        path=path,
        ensure_schema=_ensure_schema,
        validate_map_note=_validated_map_note,
    )


def list_map_notes(
    place_id: str | None = None,
    route_id: str | None = None,
    layer_id: str | None = None,
    archaeology_id: str | None = None,
    manuscript_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    return _map_notes_repo.list_map_notes(
        place_id=place_id,
        route_id=route_id,
        layer_id=layer_id,
        archaeology_id=archaeology_id,
        manuscript_id=manuscript_id,
        path=path,
        ensure_schema=_ensure_schema,
    )
def _add_column_if_missing(connection: sqlite3.Connection, table: str, column_sql: str) -> None:
    column_name = column_sql.split()[0]
    columns = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column_name not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")


def _normalized_period_label(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return ""
    return _PERIOD_NORMALIZATION_MAP.get(cleaned.lower(), cleaned)


def _periods_from_value(value: Any, fallback: Any = None) -> list[str]:
    raw_values: list[Any]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raw_values = []
        else:
            try:
                decoded = json.loads(stripped)
            except json.JSONDecodeError:
                raw_values = [stripped]
            else:
                raw_values = decoded if isinstance(decoded, list) else [decoded]
    elif isinstance(value, list):
        raw_values = value
    elif value is None:
        raw_values = []
    else:
        raw_values = [value]

    periods = [_normalized_period_label(str(item)) for item in raw_values if str(item).strip()]
    periods = [period for period in periods if period in CANONICAL_PERIOD_LABELS]
    if not periods and fallback:
        if isinstance(fallback, list):
            periods = _periods_from_value(fallback)
        else:
            normalized_fallback = _normalized_period_label(fallback)
            if normalized_fallback in CANONICAL_PERIOD_LABELS:
                periods = [normalized_fallback]
            else:
                periods = _legacy_period_buckets(fallback)
    if not periods:
        periods = [BROAD_PERIOD_LABEL]
    return _unique_preserve_order(periods)


def _legacy_period_buckets(period: str | None) -> list[str]:
    normalized = str(period or "").strip().lower()
    if not normalized:
        return [BROAD_PERIOD_LABEL]
    return _unique_preserve_order(
        [label for label in _LEGACY_PERIOD_BUCKETS.get(normalized, [BROAD_PERIOD_LABEL]) if label in CANONICAL_PERIOD_LABELS]
    )


def _period_filter_matches(periods: list[str], period: str | None) -> bool:
    normalized = normalize_period_filter(period)
    if normalized is None:
        return True
    if normalized == BROAD_PERIOD_LABEL:
        return BROAD_PERIOD_LABEL in periods
    if BROAD_PERIOD_LABEL in periods:
        return True
    return normalized in periods


def normalize_period_filter(period: str | None) -> str | None:
    normalized = _normalized_period_label(period or "")
    if not normalized or normalized.lower() == "all":
        return None
    if normalized not in CANONICAL_PERIOD_LABELS:
        return BROAD_PERIOD_LABEL
    return normalized


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied = {
        int(row["version"])
        for row in connection.execute("SELECT version FROM schema_migrations")
    }
    if 1 not in applied:
        _apply_v1_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (1, _timestamp()),
        )
    if 2 not in applied:
        _apply_v2_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (2, _timestamp()),
        )
    if 3 not in applied:
        _apply_v3_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (3, _timestamp()),
        )
    if 4 not in applied:
        _apply_v4_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (4, _timestamp()),
        )
    if 5 not in applied:
        _apply_v5_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (5, _timestamp()),
        )
    if 6 not in applied:
        _apply_v6_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (6, _timestamp()),
        )
    if 7 not in applied:
        _apply_v7_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (7, _timestamp()),
        )
    if 8 not in applied:
        _apply_v8_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (8, _timestamp()),
        )
    if 9 not in applied:
        _apply_v9_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (9, _timestamp()),
        )
    if 10 not in applied:
        _apply_v10_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (10, _timestamp()),
        )
    if 11 not in applied:
        _apply_v11_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (11, _timestamp()),
        )
    if 12 not in applied:
        _apply_v12_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (12, _timestamp()),
        )
    if 13 not in applied:
        _apply_v13_schema(connection)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (13, _timestamp()),
        )


def _apply_v1_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER NOT NULL,
            selected_text TEXT NOT NULL DEFAULT '',
            note_body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_notes_reference
            ON notes(book, chapter);

        CREATE TABLE IF NOT EXISTS highlights (
            id TEXT PRIMARY KEY,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER NOT NULL,
            selected_text TEXT NOT NULL DEFAULT '',
            color TEXT NOT NULL DEFAULT 'yellow',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_highlights_reference
            ON highlights(book, chapter);

        CREATE TABLE IF NOT EXISTS study_actions (
            id TEXT PRIMARY KEY,
            action_type TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER NOT NULL,
            selected_text TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_study_actions_reference
            ON study_actions(book, chapter);
        """
    )


def _apply_v2_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS saved_studies (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER NOT NULL,
            selected_text TEXT NOT NULL DEFAULT '',
            study_type TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_saved_studies_reference
            ON saved_studies(book, chapter);
        """
    )


def _apply_v3_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS biblical_places (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            aliases TEXT NOT NULL DEFAULT '[]',
            periods TEXT NOT NULL DEFAULT '[]',
            latitude REAL,
            longitude REAL,
            modern_location TEXT NOT NULL DEFAULT '',
            ancient_region TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT 'unknown',
            confidence_rank INTEGER NOT NULL DEFAULT 0,
            source_name TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            license TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_biblical_places_name
            ON biblical_places(name);

        CREATE INDEX IF NOT EXISTS idx_biblical_places_confidence
            ON biblical_places(confidence_rank);

        CREATE TABLE IF NOT EXISTS place_references (
            id TEXT PRIMARY KEY,
            place_id TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(place_id) REFERENCES biblical_places(id)
        );

        CREATE INDEX IF NOT EXISTS idx_place_references_place
            ON place_references(place_id);

        CREATE INDEX IF NOT EXISTS idx_place_references_reference
            ON place_references(book, chapter, verse_start, verse_end);
        """
    )
    _seed_biblical_places(connection)


def _apply_v4_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS map_routes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            period TEXT NOT NULL DEFAULT '',
            periods TEXT NOT NULL DEFAULT '[]',
            route_type TEXT NOT NULL DEFAULT '',
            geojson TEXT NOT NULL,
            confidence TEXT NOT NULL DEFAULT 'unknown',
            confidence_rank INTEGER NOT NULL DEFAULT 0,
            source_name TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_map_routes_confidence
            ON map_routes(confidence_rank);

        CREATE TABLE IF NOT EXISTS route_references (
            id TEXT PRIMARY KEY,
            route_id TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(route_id) REFERENCES map_routes(id)
        );

        CREATE INDEX IF NOT EXISTS idx_route_references_route
            ON route_references(route_id);

        CREATE INDEX IF NOT EXISTS idx_route_references_reference
            ON route_references(book, chapter, verse_start, verse_end);
        """
    )
    _seed_map_routes(connection)


def _apply_v5_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS historical_layers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            period TEXT NOT NULL DEFAULT '',
            periods TEXT NOT NULL DEFAULT '[]',
            description TEXT NOT NULL DEFAULT '',
            layer_type TEXT NOT NULL DEFAULT '',
            geojson TEXT NOT NULL,
            confidence TEXT NOT NULL DEFAULT 'unknown',
            confidence_rank INTEGER NOT NULL DEFAULT 0,
            source_name TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_historical_layers_period
            ON historical_layers(period);

        CREATE INDEX IF NOT EXISTS idx_historical_layers_confidence
            ON historical_layers(confidence_rank);
        """
    )
    _seed_historical_layers(connection)


def _apply_v6_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS saved_map_studies (
            id TEXT PRIMARY KEY,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER NOT NULL,
            passage_reference TEXT NOT NULL DEFAULT '',
            selected_place_id TEXT NOT NULL DEFAULT '',
            selected_route_id TEXT NOT NULL DEFAULT '',
            selected_layer_id TEXT NOT NULL DEFAULT '',
            selected_layers TEXT NOT NULL DEFAULT '[]',
            map_view_state TEXT NOT NULL DEFAULT '{}',
            generated_summary TEXT NOT NULL DEFAULT '',
            user_notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_saved_map_studies_reference
            ON saved_map_studies(book, chapter);

        CREATE TABLE IF NOT EXISTS map_notes (
            id TEXT PRIMARY KEY,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER NOT NULL,
            passage_reference TEXT NOT NULL DEFAULT '',
            place_id TEXT NOT NULL DEFAULT '',
            route_id TEXT NOT NULL DEFAULT '',
            layer_id TEXT NOT NULL DEFAULT '',
            note_body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_map_notes_place
            ON map_notes(place_id);

        CREATE INDEX IF NOT EXISTS idx_map_notes_route
            ON map_notes(route_id);

        CREATE INDEX IF NOT EXISTS idx_map_notes_layer
            ON map_notes(layer_id);
        """
    )


def _apply_v7_schema(connection: sqlite3.Connection) -> None:
    _add_column_if_missing(
        connection,
        "saved_map_studies",
        "archaeology_id TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        connection,
        "map_notes",
        "archaeology_id TEXT NOT NULL DEFAULT ''",
    )
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS archaeology_sites (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            site_type TEXT NOT NULL DEFAULT '',
            period TEXT NOT NULL DEFAULT '',
            periods TEXT NOT NULL DEFAULT '[]',
            latitude REAL,
            longitude REAL,
            modern_location TEXT NOT NULL DEFAULT '',
            ancient_region TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT 'unknown',
            confidence_rank INTEGER NOT NULL DEFAULT 0,
            source_name TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            license TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_archaeology_sites_confidence
            ON archaeology_sites(confidence_rank);

        CREATE INDEX IF NOT EXISTS idx_archaeology_sites_period
            ON archaeology_sites(period);

        CREATE TABLE IF NOT EXISTS archaeology_items (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            item_type TEXT NOT NULL DEFAULT '',
            period TEXT NOT NULL DEFAULT '',
            periods TEXT NOT NULL DEFAULT '[]',
            relationship TEXT NOT NULL DEFAULT '',
            why_it_matters TEXT NOT NULL DEFAULT '',
            bhf_caution TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT 'unknown',
            confidence_rank INTEGER NOT NULL DEFAULT 0,
            source_name TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            license TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(site_id) REFERENCES archaeology_sites(id)
        );

        CREATE INDEX IF NOT EXISTS idx_archaeology_items_site
            ON archaeology_items(site_id);

        CREATE INDEX IF NOT EXISTS idx_archaeology_items_confidence
            ON archaeology_items(confidence_rank);

        CREATE TABLE IF NOT EXISTS archaeology_scripture_links (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(item_id) REFERENCES archaeology_items(id)
        );

        CREATE INDEX IF NOT EXISTS idx_archaeology_scripture_links_item
            ON archaeology_scripture_links(item_id);

        CREATE INDEX IF NOT EXISTS idx_archaeology_scripture_links_reference
            ON archaeology_scripture_links(book, chapter, verse_start, verse_end);
        """
    )
    _seed_archaeology(connection)


def _apply_v8_schema(connection: sqlite3.Connection) -> None:
    _add_column_if_missing(
        connection,
        "biblical_places",
        "periods TEXT NOT NULL DEFAULT '[]'",
    )
    _add_column_if_missing(
        connection,
        "map_routes",
        "periods TEXT NOT NULL DEFAULT '[]'",
    )
    _add_column_if_missing(
        connection,
        "historical_layers",
        "periods TEXT NOT NULL DEFAULT '[]'",
    )
    _add_column_if_missing(
        connection,
        "archaeology_sites",
        "periods TEXT NOT NULL DEFAULT '[]'",
    )
    _add_column_if_missing(
        connection,
        "archaeology_items",
        "periods TEXT NOT NULL DEFAULT '[]'",
    )
    _backfill_period_columns(connection)


def _apply_v9_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS political_context_layers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            entity_type TEXT NOT NULL DEFAULT '',
            period TEXT NOT NULL DEFAULT '',
            periods TEXT NOT NULL DEFAULT '[]',
            summary TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            layer_type TEXT NOT NULL DEFAULT 'political_context',
            sort_order INTEGER NOT NULL DEFAULT 0,
            geojson TEXT NOT NULL,
            confidence TEXT NOT NULL DEFAULT 'unknown',
            confidence_rank INTEGER NOT NULL DEFAULT 0,
            source_name TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_political_context_layers_period
            ON political_context_layers(period);

        CREATE INDEX IF NOT EXISTS idx_political_context_layers_confidence
            ON political_context_layers(confidence_rank);

        CREATE TABLE IF NOT EXISTS political_context_references (
            id TEXT PRIMARY KEY,
            context_id TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(context_id) REFERENCES political_context_layers(id)
        );

        CREATE INDEX IF NOT EXISTS idx_political_context_references_context
            ON political_context_references(context_id);

        CREATE INDEX IF NOT EXISTS idx_political_context_references_reference
            ON political_context_references(book, chapter, verse_start, verse_end);
        """
    )
    _seed_political_context(connection)


def _apply_v10_schema(connection: sqlite3.Connection) -> None:
    _add_column_if_missing(
        connection,
        "saved_map_studies",
        "manuscript_id TEXT NOT NULL DEFAULT ''",
    )
    _add_column_if_missing(
        connection,
        "map_notes",
        "manuscript_id TEXT NOT NULL DEFAULT ''",
    )
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS manuscript_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            manuscript_type TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT '',
            date TEXT NOT NULL DEFAULT '',
            material TEXT NOT NULL DEFAULT '',
            discovery_location TEXT NOT NULL DEFAULT '',
            current_location TEXT NOT NULL DEFAULT '',
            latitude REAL,
            longitude REAL,
            related_books TEXT NOT NULL DEFAULT '[]',
            period TEXT NOT NULL DEFAULT '',
            periods TEXT NOT NULL DEFAULT '[]',
            significance TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT 'unknown',
            confidence_rank INTEGER NOT NULL DEFAULT 0,
            source_name TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            license TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            bhf_caution TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_manuscript_items_confidence
            ON manuscript_items(confidence_rank);

        CREATE INDEX IF NOT EXISTS idx_manuscript_items_period
            ON manuscript_items(period);

        CREATE TABLE IF NOT EXISTS manuscript_scripture_links (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(item_id) REFERENCES manuscript_items(id)
        );

        CREATE INDEX IF NOT EXISTS idx_manuscript_scripture_links_item
            ON manuscript_scripture_links(item_id);

        CREATE INDEX IF NOT EXISTS idx_manuscript_scripture_links_reference
            ON manuscript_scripture_links(book, chapter, verse_start, verse_end);
        """
    )
    _seed_manuscripts(connection)


def _apply_v11_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            url TEXT NOT NULL DEFAULT '',
            license TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_sources_label
            ON sources(label);

        CREATE TABLE IF NOT EXISTS confidence_labels (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            rank INTEGER NOT NULL DEFAULT 0,
            description TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_confidence_labels_rank
            ON confidence_labels(rank);
        """
    )
    _seed_confidence_labels(connection)


def _apply_v12_schema(connection: sqlite3.Connection) -> None:
    for table in (
        "biblical_places",
        "map_routes",
        "historical_layers",
        "political_context_layers",
        "archaeology_sites",
        "archaeology_items",
        "manuscript_items",
    ):
        _add_column_if_missing(connection, table, "source_id TEXT NOT NULL DEFAULT ''")
    _backfill_source_registry(connection)


def _apply_v13_schema(connection: sqlite3.Connection) -> None:
    _seed_openbible_places(connection)


def _backfill_source_registry(connection: sqlite3.Connection) -> None:
    source_columns = {
        "biblical_places": ("source_name", "source_url", "license"),
        "map_routes": ("source_name", "source_url", None),
        "historical_layers": ("source_name", "source_url", None),
        "political_context_layers": ("source_name", "source_url", None),
        "archaeology_sites": ("source_name", "source_url", "license"),
        "archaeology_items": ("source_name", "source_url", "license"),
        "manuscript_items": ("source_name", "source_url", "license"),
    }
    for table, fields in source_columns.items():
        rows = connection.execute(f"SELECT id, source_id, {', '.join(column for column in fields if column)} FROM {table}").fetchall()
        for row in rows:
            source_name = str(row["source_name"] or "").strip()
            source_url = str(row["source_url"] or "").strip()
            license = str(row["license"] or "").strip() if "license" in fields else ""
            source_id = _register_source(connection, source_name, source_url, license)
            if source_id:
                connection.execute(
                    f"UPDATE {table} SET source_id = ? WHERE id = ?",
                    (source_id, row["id"]),
                )
    _seed_sources_from_existing_records(connection)


def _seed_sources_from_existing_records(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT DISTINCT source_name, source_url, license
        FROM (
            SELECT source_name, source_url, license FROM biblical_places
            UNION ALL SELECT source_name, source_url, '' FROM map_routes
            UNION ALL SELECT source_name, source_url, '' FROM historical_layers
            UNION ALL SELECT source_name, source_url, '' FROM political_context_layers
            UNION ALL SELECT source_name, source_url, license FROM archaeology_sites
            UNION ALL SELECT source_name, source_url, license FROM archaeology_items
            UNION ALL SELECT source_name, source_url, license FROM manuscript_items
        )
        WHERE trim(COALESCE(source_name, '')) != '' OR trim(COALESCE(source_url, '')) != '' OR trim(COALESCE(license, '')) != ''
        ORDER BY source_name, source_url, license
        """
    ).fetchall()
    for row in rows:
        _register_source(
            connection,
            str(row["source_name"] or "").strip(),
            str(row["source_url"] or "").strip(),
            str(row["license"] or "").strip(),
        )


def _source_identifier(source_name: str, source_url: str, license: str) -> str:
    normalized = "|".join(
        part.strip().lower()
        for part in (source_name, source_url, license)
        if part and str(part).strip()
    )
    if not normalized:
        return ""
    safe = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return safe[:80] or uuid.uuid4().hex


def _register_source(
    connection: sqlite3.Connection,
    source_name: str,
    source_url: str,
    license: str,
    notes: str = "",
) -> str:
    source_name = source_name.strip()
    source_url = source_url.strip()
    license = license.strip()
    notes = notes.strip()
    source_id = _source_identifier(source_name, source_url, license)
    if not source_id:
        return ""
    label = source_name or source_url or license or source_id
    connection.execute(
        """
        INSERT OR IGNORE INTO sources (id, label, url, license, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (source_id, label, source_url, license, notes),
    )
    if notes:
        connection.execute(
            "UPDATE sources SET notes = CASE WHEN notes = '' THEN ? ELSE notes END WHERE id = ?",
            (notes, source_id),
        )
    return source_id


def _seed_confidence_labels(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM confidence_labels").fetchone()[0]
    if existing:
        return
    for label in (
        {
            "id": "unknown",
            "label": "unknown",
            "rank": 0,
            "description": "Not enough information to evaluate confidence.",
            "notes": "Default fallback label.",
        },
        {
            "id": "possible",
            "label": "possible",
            "rank": 2,
            "description": "A plausible identification or relationship.",
            "notes": "",
        },
        {
            "id": "likely",
            "label": "likely",
            "rank": 4,
            "description": "Supported by strong local evidence, though not certain.",
            "notes": "",
        },
        {
            "id": "strong",
            "label": "strong",
            "rank": 5,
            "description": "Well-supported and broadly accepted in the local dataset.",
            "notes": "",
        },
    ):
        connection.execute(
            """
            INSERT INTO confidence_labels (
                id, label, rank, description, notes
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                label["id"],
                label["label"],
                label["rank"],
                label["description"],
                label["notes"],
            ),
        )
def _validated_saved_map_study(data: dict[str, Any]) -> dict[str, Any]:
    reference = _validated_reference(data)
    passage_reference = str(
        data.get("passage_reference")
        or _default_map_passage_reference(
            reference["book"],
            reference["chapter"],
            reference["start_verse"],
            reference["end_verse"],
        )
    ).strip()
    selected_place_id = str(data.get("selected_place_id") or "").strip()
    selected_route_id = str(data.get("selected_route_id") or "").strip()
    selected_layer_id = str(data.get("selected_layer_id") or "").strip()
    selected_archaeology_id = str(data.get("selected_archaeology_id") or "").strip()
    selected_manuscript_id = str(data.get("selected_manuscript_id") or "").strip()
    selected_layers = data.get("selected_layers") or []
    if isinstance(selected_layers, str):
        try:
            selected_layers = json.loads(selected_layers)
        except json.JSONDecodeError:
            selected_layers = [selected_layers]
    if not isinstance(selected_layers, list):
        selected_layers = []
    selected_layers = [str(value).strip() for value in selected_layers if str(value).strip()]
    if (
        not selected_place_id
        and not selected_route_id
        and not selected_layer_id
        and not selected_archaeology_id
        and not selected_manuscript_id
        and not selected_layers
    ):
        raise StudyDataError("select a place, route, historical layer, or archaeology item before saving a map study")
    map_view_state = data.get("map_view_state") or {}
    if isinstance(map_view_state, str):
        try:
            map_view_state = json.loads(map_view_state)
        except json.JSONDecodeError:
            map_view_state = {}
    if not isinstance(map_view_state, dict):
        map_view_state = {}
    generated_summary = str(data.get("generated_summary") or "").strip()
    user_notes = str(data.get("user_notes") or "").strip()
    return {
        **reference,
        "passage_reference": passage_reference,
        "selected_place_id": selected_place_id,
        "selected_route_id": selected_route_id,
        "selected_layer_id": selected_layer_id,
        "selected_archaeology_id": selected_archaeology_id,
        "selected_manuscript_id": selected_manuscript_id,
        "selected_layers": selected_layers,
        "map_view_state": map_view_state,
        "generated_summary": generated_summary,
        "user_notes": user_notes,
    }


def _validated_map_note(data: dict[str, Any]) -> dict[str, Any]:
    reference = _validated_reference(data)
    note_body = str(data.get("note_body") or data.get("body") or "").strip()
    if not note_body:
        raise StudyDataError("map note body is required")
    place_id = str(data.get("place_id") or "").strip()
    route_id = str(data.get("route_id") or "").strip()
    layer_id = str(data.get("layer_id") or "").strip()
    archaeology_id = str(data.get("archaeology_id") or "").strip()
    manuscript_id = str(data.get("manuscript_id") or "").strip()
    if not place_id and not route_id and not layer_id and not archaeology_id and not manuscript_id:
        raise StudyDataError("select a place, route, historical layer, archaeology item, or manuscript for the note")
    passage_reference = str(
        data.get("passage_reference")
        or _default_map_passage_reference(
            reference["book"],
            reference["chapter"],
            reference["start_verse"],
            reference["end_verse"],
        )
    ).strip()
    return {
        **reference,
        "passage_reference": passage_reference,
        "place_id": place_id,
        "route_id": route_id,
        "layer_id": layer_id,
        "archaeology_id": archaeology_id,
        "manuscript_id": manuscript_id,
        "note_body": note_body,
    }
def _default_map_passage_reference(
    book: str,
    chapter: int,
    start_verse: int,
    end_verse: int,
) -> str:
    reference = f"{book} {chapter}"
    suffix = str(start_verse) if start_verse == end_verse else f"{start_verse}-{end_verse}"
    return f"{reference}:{suffix}"
def _attach_source(record: dict[str, Any], path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    source_id = str(record.get("source_id") or "").strip()
    source = None
    if source_id:
        try:
            source = get_source(source_id, path=path)
        except StudyDataError:
            source = None
    if source is None:
        fallback_id = _source_identifier(
            str(record.get("source_name") or "").strip(),
            str(record.get("source_url") or "").strip(),
            str(record.get("license") or "").strip(),
        )
        if fallback_id and fallback_id != source_id:
            try:
                source = get_source(fallback_id, path=path)
                source_id = fallback_id
            except StudyDataError:
                source = None
    record["source_id"] = source_id
    record["source"] = source
    record["source_summary"] = _source_summary_text(record, source)
    return record


def _source_summary_text(record: dict[str, Any], source: dict[str, Any] | None) -> str:
    if source:
        parts = [str(source.get("label") or "").strip()]
        if source.get("license"):
            parts.append(f"License: {source['license']}")
        if source.get("url"):
            parts.append(str(source["url"]))
        return " · ".join(part for part in parts if part)
    parts = [
        str(record.get("source_name") or "").strip(),
        str(record.get("source_url") or "").strip(),
        str(record.get("license") or "").strip(),
    ]
    return " · ".join(part for part in parts if part) or "Missing source metadata"
def _seed_biblical_places(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM biblical_places").fetchone()[0]
    if existing:
        return

    for place in _BIBLICAL_PLACES_SEED:
        connection.execute(
            """
            INSERT INTO biblical_places (
                id, name, aliases, periods, latitude, longitude, modern_location,
                ancient_region, description, confidence, confidence_rank,
                source_name, source_url, license, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                place["id"],
                place["name"],
                json.dumps(place["aliases"]),
                json.dumps(_BIBLICAL_PLACE_PERIODS.get(place["id"], [BROAD_PERIOD_LABEL])),
                place["latitude"],
                place["longitude"],
                place["modern_location"],
                place["ancient_region"],
                place["description"],
                place["confidence"],
                place["confidence_rank"],
                place["source_name"],
                place["source_url"],
                place["license"],
                place["notes"],
            ),
        )

    for reference in _PLACE_REFERENCES_SEED:
        connection.execute(
            """
            INSERT INTO place_references (
                id, place_id, book, chapter, verse_start, verse_end,
                relationship_type, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reference["id"],
                reference["place_id"],
                reference["book"],
                reference["chapter"],
                reference["verse_start"],
                reference["verse_end"],
                reference["relationship_type"],
                reference["notes"],
            ),
        )


def _load_openbible_places(path: Path = OPENBIBLE_PLACES_PATH) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _seed_openbible_places(connection: sqlite3.Connection) -> None:
    imported_places = _load_openbible_places()
    if not imported_places:
        return

    existing_local_names = {
        _normalize_seed_name(place["name"])
        for place in _BIBLICAL_PLACES_SEED
    }
    source_id = _register_source(
        connection,
        "OpenBible.info Bible Geocoding Data",
        "https://github.com/openbibleinfo/Bible-Geocoding-Data",
        "CC-BY-4.0",
        "Imported compact point dataset for biblical place lookup and map pinning.",
    )

    place_rows = []
    reference_rows = []
    for place in imported_places:
        if _normalize_seed_name(str(place.get("name") or "")) in existing_local_names:
            continue
        place_rows.append(
            (
                place["id"],
                place["name"],
                json.dumps(place.get("aliases", [])),
                json.dumps([BROAD_PERIOD_LABEL]),
                place["latitude"],
                place["longitude"],
                place.get("modern_location", ""),
                place.get("ancient_region", ""),
                place.get("description", ""),
                place.get("confidence", "unknown"),
                int(place.get("confidence_rank") or 0),
                place.get("source_name", "OpenBible.info Bible Geocoding Data"),
                place.get("source_url", "https://github.com/openbibleinfo/Bible-Geocoding-Data"),
                place.get("license", "CC-BY-4.0"),
                place.get("notes", ""),
                source_id,
            )
        )
        for index, reference in enumerate(place.get("references", []), start=1):
            reference_rows.append(
                (
                    f"openbible-ref-{place['id']}-{index}",
                    place["id"],
                    reference["book"],
                    int(reference["chapter"]),
                    int(reference["verse_start"]),
                    int(reference.get("verse_end") or reference["verse_start"]),
                    "directly_named",
                    "Imported from OpenBible.info Bible Geocoding Data.",
                )
            )
    connection.executemany(
        """
        INSERT OR IGNORE INTO biblical_places (
            id, name, aliases, periods, latitude, longitude, modern_location,
            ancient_region, description, confidence, confidence_rank,
            source_name, source_url, license, notes, source_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        place_rows,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO place_references (
            id, place_id, book, chapter, verse_start, verse_end,
            relationship_type, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        reference_rows,
    )


def _normalize_seed_name(value: str) -> str:
    normalized = value.lower().replace("'", "")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _seed_map_routes(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM map_routes").fetchone()[0]
    if existing:
        return

    for route in _MAP_ROUTES_SEED:
        connection.execute(
            """
            INSERT INTO map_routes (
                id, name, description, period, periods, route_type, geojson,
                confidence, confidence_rank, source_name, source_url, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                route["id"],
                route["name"],
                route["description"],
                route["period"],
                json.dumps(_periods_from_value(route.get("periods"), fallback=route["period"])),
                route["route_type"],
                json.dumps(route["geojson"]),
                route["confidence"],
                route["confidence_rank"],
                route["source_name"],
                route["source_url"],
                route["notes"],
            ),
        )

    for reference in _ROUTE_REFERENCES_SEED:
        connection.execute(
            """
            INSERT INTO route_references (
                id, route_id, book, chapter, verse_start, verse_end,
                relationship_type, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reference["id"],
                reference["route_id"],
                reference["book"],
                reference["chapter"],
                reference["verse_start"],
                reference["verse_end"],
                reference["relationship_type"],
                reference["notes"],
            ),
        )


def _seed_historical_layers(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM historical_layers").fetchone()[0]
    if existing:
        return

    for layer in _HISTORICAL_LAYERS_SEED:
        connection.execute(
            """
            INSERT INTO historical_layers (
                id, name, period, periods, description, layer_type, geojson,
                confidence, confidence_rank, source_name, source_url, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                layer["id"],
                layer["name"],
                layer["period"],
                json.dumps(_periods_from_value(layer.get("periods"), fallback=layer["period"])),
                layer["description"],
                layer["layer_type"],
                json.dumps(layer["geojson"]),
                layer["confidence"],
                layer["confidence_rank"],
                layer["source_name"],
                layer["source_url"],
                layer["notes"],
            ),
        )


def _seed_political_context(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM political_context_layers").fetchone()[0]
    if existing:
        return

    for layer in _POLITICAL_CONTEXT_LAYERS_SEED:
        connection.execute(
            """
            INSERT INTO political_context_layers (
                id, name, entity_type, period, periods, summary, description,
                layer_type, sort_order, geojson, confidence, confidence_rank,
                source_name, source_url, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                layer["id"],
                layer["name"],
                layer["entity_type"],
                layer["period"],
                json.dumps(_periods_from_value(layer.get("periods"), fallback=layer["period"])),
                layer["summary"],
                layer["description"],
                layer["layer_type"],
                layer["sort_order"],
                json.dumps(layer["geojson"]),
                layer["confidence"],
                layer["confidence_rank"],
                layer["source_name"],
                layer["source_url"],
                layer["notes"],
            ),
        )

    for reference in _POLITICAL_CONTEXT_REFERENCES_SEED:
        connection.execute(
            """
            INSERT INTO political_context_references (
                id, context_id, book, chapter, verse_start, verse_end,
                relationship_type, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reference["id"],
                reference["context_id"],
                reference["book"],
                reference["chapter"],
                reference["verse_start"],
                reference["verse_end"],
                reference["relationship_type"],
                reference["notes"],
            ),
        )


def _seed_manuscripts(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM manuscript_items").fetchone()[0]
    if existing:
        return

    for item in _MANUSCRIPT_ITEMS_SEED:
        connection.execute(
            """
            INSERT INTO manuscript_items (
                id, name, manuscript_type, language, date, material,
                discovery_location, current_location, latitude, longitude,
                related_books, period, periods, significance, confidence,
                confidence_rank, source_name, source_url, license, notes,
                bhf_caution
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["name"],
                item["manuscript_type"],
                item["language"],
                item["date"],
                item["material"],
                item["discovery_location"],
                item["current_location"],
                item["latitude"],
                item["longitude"],
                json.dumps(item["related_books"]),
                item["period"],
                json.dumps(_periods_from_value(item.get("periods"), fallback=item["period"])),
                item["significance"],
                item["confidence"],
                item["confidence_rank"],
                item["source_name"],
                item["source_url"],
                item["license"],
                item["notes"],
                item["bhf_caution"],
            ),
        )

    for link in _MANUSCRIPT_SCRIPTURE_LINKS_SEED:
        connection.execute(
            """
            INSERT INTO manuscript_scripture_links (
                id, item_id, book, chapter, verse_start, verse_end,
                relationship_type, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                link["id"],
                link["item_id"],
                link["book"],
                link["chapter"],
                link["verse_start"],
                link["verse_end"],
                link["relationship_type"],
                link["notes"],
            ),
        )


def _seed_archaeology(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM archaeology_sites").fetchone()[0]
    if existing:
        return

    for site in _ARCHAEOLOGY_SITES_SEED:
        connection.execute(
            """
            INSERT INTO archaeology_sites (
                id, name, site_type, period, periods, latitude, longitude,
                modern_location, ancient_region, description, confidence,
                confidence_rank, source_name, source_url, license, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                site["id"],
                site["name"],
                site["site_type"],
                site["period"],
                json.dumps(_periods_from_value(site.get("periods"), fallback=site["period"])),
                site["latitude"],
                site["longitude"],
                site["modern_location"],
                site["ancient_region"],
                site["description"],
                site["confidence"],
                site["confidence_rank"],
                site["source_name"],
                site["source_url"],
                site["license"],
                site["notes"],
            ),
        )

    for item in _ARCHAEOLOGY_ITEMS_SEED:
        connection.execute(
            """
            INSERT INTO archaeology_items (
                id, site_id, name, item_type, period, periods, relationship,
                why_it_matters, bhf_caution, confidence, confidence_rank,
                source_name, source_url, license, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["site_id"],
                item["name"],
                item["item_type"],
                item["period"],
                json.dumps(_periods_from_value(item.get("periods"), fallback=item["period"])),
                item["relationship"],
                item["why_it_matters"],
                item["bhf_caution"],
                item["confidence"],
                item["confidence_rank"],
                item["source_name"],
                item["source_url"],
                item["license"],
                item["notes"],
            ),
        )

    for link in _ARCHAEOLOGY_SCRIPTURE_LINKS_SEED:
        connection.execute(
            """
            INSERT INTO archaeology_scripture_links (
                id, item_id, book, chapter, verse_start, verse_end,
                relationship_type, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                link["id"],
                link["item_id"],
                link["book"],
                link["chapter"],
                link["verse_start"],
                link["verse_end"],
                link["relationship_type"],
                link["notes"],
            ),
        )


def _backfill_period_columns(connection: sqlite3.Connection) -> None:
    for place_id, periods in _BIBLICAL_PLACE_PERIODS.items():
        connection.execute(
            "UPDATE biblical_places SET periods = ? WHERE id = ? AND (periods IS NULL OR periods = '' OR periods = '[]')",
            (json.dumps(periods), place_id),
        )

    for table in ("map_routes", "historical_layers", "archaeology_sites", "archaeology_items"):
        rows = connection.execute(f"SELECT id, period, periods FROM {table}").fetchall()
        for row in rows:
            normalized_periods = _periods_from_value(row["periods"], fallback=row["period"])
            connection.execute(
                f"UPDATE {table} SET periods = ? WHERE id = ?",
                (json.dumps(normalized_periods), row["id"]),
            )


_BIBLICAL_PLACES_SEED: list[dict[str, Any]] = [
    {
        "id": "jerusalem",
        "name": "Jerusalem",
        "aliases": ["City of David", "Zion", "Yerushalayim"],
        "latitude": 31.778,
        "longitude": 35.235,
        "modern_location": "Jerusalem, Israel/Palestine",
        "ancient_region": "Judea",
        "description": "Center of temple worship, royal administration, and major biblical narrative scenes.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Coordinates are approximate city-center coordinates for map display.",
    },
    {
        "id": "bethlehem",
        "name": "Bethlehem",
        "aliases": ["Beth-lehem", "House of Bread"],
        "latitude": 31.705,
        "longitude": 35.200,
        "modern_location": "Bethlehem, West Bank",
        "ancient_region": "Judah",
        "description": "Associated with David, Ruth, and the infancy narratives of Matthew and Luke.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Approximate location for local study and map browsing.",
    },
    {
        "id": "capernaum",
        "name": "Capernaum",
        "aliases": ["Kefar Nahum"],
        "latitude": 32.880,
        "longitude": 35.574,
        "modern_location": "Near the northwest shore of the Sea of Galilee",
        "ancient_region": "Galilee",
        "description": "A key setting in Jesus' Galilean ministry and several healing narratives.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Approximate site coordinates.",
    },
    {
        "id": "caesarea-maritima",
        "name": "Caesarea Maritima",
        "aliases": ["Caesarea", "Caesarea by the Sea"],
        "latitude": 32.500,
        "longitude": 34.888,
        "modern_location": "Caesarea, Israel",
        "ancient_region": "Coastal plain",
        "description": "Roman coastal administrative center appearing prominently in Acts.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Coordinates approximate archaeological area.",
    },
    {
        "id": "babylon",
        "name": "Babylon",
        "aliases": ["Babel"],
        "latitude": 32.536,
        "longitude": 44.420,
        "modern_location": "Near Hillah, Iraq",
        "ancient_region": "Babylonia",
        "description": "Major imperial center and exile setting in the Old Testament and later symbolic imagery.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Approximate historical location for map display.",
    },
]


_PLACE_REFERENCES_SEED: list[dict[str, Any]] = [
    {
        "id": "pr-jerusalem-2sam5",
        "place_id": "jerusalem",
        "book": "2 Samuel",
        "chapter": 5,
        "verse_start": 6,
        "verse_end": 12,
        "relationship_type": "directly_named",
        "notes": "David's capture of Jerusalem and establishment of rule.",
    },
    {
        "id": "pr-jerusalem-luke2",
        "place_id": "jerusalem",
        "book": "Luke",
        "chapter": 2,
        "verse_start": 22,
        "verse_end": 38,
        "relationship_type": "directly_named",
        "notes": "Presentation narrative and temple setting.",
    },
    {
        "id": "pr-bethlehem-ruth4",
        "place_id": "bethlehem",
        "book": "Ruth",
        "chapter": 4,
        "verse_start": 11,
        "verse_end": 22,
        "relationship_type": "directly_named",
        "notes": "Bethlehem as the family setting in Ruth's closing genealogy.",
    },
    {
        "id": "pr-bethlehem-matt2",
        "place_id": "bethlehem",
        "book": "Matthew",
        "chapter": 2,
        "verse_start": 1,
        "verse_end": 16,
        "relationship_type": "directly_named",
        "notes": "The birthplace setting in Matthew's infancy narrative.",
    },
    {
        "id": "pr-capernaum-matt4",
        "place_id": "capernaum",
        "book": "Matthew",
        "chapter": 4,
        "verse_start": 12,
        "verse_end": 17,
        "relationship_type": "directly_named",
        "notes": "Jesus begins ministry in Capernaum.",
    },
    {
        "id": "pr-caesarea-acts10",
        "place_id": "caesarea-maritima",
        "book": "Acts",
        "chapter": 10,
        "verse_start": 1,
        "verse_end": 48,
        "relationship_type": "directly_named",
        "notes": "Cornelius narrative is centered in Caesarea.",
    },
    {
        "id": "pr-babylon-dan1",
        "place_id": "babylon",
        "book": "Daniel",
        "chapter": 1,
        "verse_start": 1,
        "verse_end": 21,
        "relationship_type": "directly_named",
        "notes": "Daniel's exile setting in Babylon.",
    },
]


_MAP_ROUTES_SEED: list[dict[str, Any]] = [
    {
        "id": "pauls-first-missionary-journey",
        "name": "Paul's First Missionary Journey",
        "description": "A curated approximation of Paul's first journey from Antioch through Cyprus and into the Galatian region.",
        "period": "New Testament / Roman period",
        "route_type": "missionary_journey",
        "geojson": {
            "type": "Feature",
            "properties": {
                "name": "Paul's First Missionary Journey",
                "confidence": "likely",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [36.206, 36.159],
                    [33.367, 35.126],
                    [34.927, 31.245],
                    [33.886, 31.528],
                    [31.938, 34.772],
                    [31.780, 35.233],
                ],
            },
        },
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "notes": "Approximate route; the exact path between travel points is debated and simplified for study use.",
    },
]


_HISTORICAL_LAYERS_SEED: list[dict[str, Any]] = [
    {
        "id": "divided-kingdom-israel",
        "name": "Northern Kingdom of Israel",
        "period": "Divided Kingdom",
        "description": "Approximate overlay for the northern kingdom during the divided monarchy. The boundaries are schematic and should be read as a study guide, not an exact border map.",
        "layer_type": "kingdom",
        "geojson": {
            "type": "Feature",
            "properties": {
                "title": "Northern Kingdom of Israel",
                "confidence": "possible",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [34.05, 33.75],
                        [34.05, 31.6],
                        [35.95, 31.6],
                        [35.95, 33.75],
                        [34.05, 33.75],
                    ]
                ],
            },
        },
        "confidence": "possible",
        "confidence_rank": 2,
        "source_name": "BHF curated local seed; schematic historical overlay",
        "source_url": "",
        "notes": "Approximate study overlay for the northern kingdom; schematic border detail is intentionally conservative.",
    },
    {
        "id": "divided-kingdom-judah",
        "name": "Southern Kingdom of Judah",
        "period": "Divided Kingdom",
        "description": "Approximate overlay for Judah during the divided monarchy. The map is intentionally broad and should not be treated as an exact political boundary.",
        "layer_type": "kingdom",
        "geojson": {
            "type": "Feature",
            "properties": {
                "title": "Southern Kingdom of Judah",
                "confidence": "possible",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [34.55, 32.7],
                        [34.55, 30.85],
                        [35.9, 30.85],
                        [35.9, 32.7],
                        [34.55, 32.7],
                    ]
                ],
            },
        },
        "confidence": "possible",
        "confidence_rank": 2,
        "source_name": "BHF curated local seed; schematic historical overlay",
        "source_url": "",
        "notes": "Approximate study overlay for Judah; real borders changed over time.",
    },
    {
        "id": "assyrian-empire",
        "name": "Assyrian Empire",
        "period": "Assyrian period",
        "description": "Broad imperial overlay showing the Assyrian imperial sphere relevant to the northern kingdom and the prophetic books. The extent is schematic.",
        "layer_type": "empire",
        "geojson": {
            "type": "Feature",
            "properties": {
                "title": "Assyrian Empire",
                "confidence": "likely",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [35.0, 38.5],
                        [35.0, 28.5],
                        [48.5, 28.5],
                        [48.5, 38.5],
                        [35.0, 38.5],
                    ]
                ],
            },
        },
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed; schematic imperial extent",
        "source_url": "",
        "notes": "The empire's exact borders shifted by reign and decade; this is a broad visual context layer only.",
    },
    {
        "id": "roman-judea-galilee",
        "name": "Roman Judea and Galilee",
        "period": "NT / Roman period",
        "description": "Broad provincial overlay for Roman-era Judea and Galilee used to situate Gospel and early church passages. It is intentionally approximate.",
        "layer_type": "province",
        "geojson": {
            "type": "Feature",
            "properties": {
                "title": "Roman Judea and Galilee",
                "confidence": "likely",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [33.35, 33.65],
                        [33.35, 30.15],
                        [36.55, 30.15],
                        [36.55, 33.65],
                        [33.35, 33.65],
                    ]
                ],
            },
        },
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed; schematic provincial overlay",
        "source_url": "",
        "notes": "This is a broad Roman-period background layer, not a claim about exact administrative borders at a single date.",
    },
]


_POLITICAL_CONTEXT_LAYERS_SEED: list[dict[str, Any]] = [
    {
        "id": "egypt",
        "name": "Egypt",
        "entity_type": "kingdom / empire",
        "period": "Broad / uncertain period",
        "periods": _POLITICAL_CONTEXT_PERIODS["egypt"],
        "summary": "Egypt repeatedly appears as a place of refuge, oppression, diplomacy, and symbolic memory.",
        "description": "A broad political background layer for the Nile kingdom and later imperial Egypt. The footprint is schematic and intentionally coarse.",
        "layer_type": "political_context",
        "sort_order": 10,
        "geojson": {
            "type": "Feature",
            "properties": {"title": "Egypt", "confidence": "possible"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[24.0, 31.5], [24.0, 21.0], [36.5, 21.0], [36.5, 31.5], [24.0, 31.5]]],
            },
        },
        "confidence": "possible",
        "confidence_rank": 2,
        "source_name": "BHF curated local seed; schematic political context",
        "source_url": "",
        "notes": "Use as a broad setting cue, not as a precise boundary reconstruction.",
    },
    {
        "id": "canaanite-city-states",
        "name": "Canaanite City-States",
        "entity_type": "city-state network",
        "period": "Broad / uncertain period",
        "periods": _POLITICAL_CONTEXT_PERIODS["canaanite-city-states"],
        "summary": "Late Bronze and early Iron Age Canaan featured overlapping city-state control rather than one clean border map.",
        "description": "A schematic pre-monarchic political backdrop for Joshua and Judges. This is intentionally broad because the evidence is fragmentary and shifting.",
        "layer_type": "political_context",
        "sort_order": 20,
        "geojson": {
            "type": "Feature",
            "properties": {"title": "Canaanite city-states", "confidence": "possible"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[34.0, 34.8], [34.0, 30.5], [36.2, 30.5], [36.2, 34.8], [34.0, 34.8]]],
            },
        },
        "confidence": "possible",
        "confidence_rank": 2,
        "source_name": "BHF curated local seed; schematic political context",
        "source_url": "",
        "notes": "A broad teaching layer for the overlapping local powers of the land.",
    },
    {
        "id": "philistia",
        "name": "Philistia",
        "entity_type": "regional polity",
        "period": "Divided Kingdom",
        "periods": _POLITICAL_CONTEXT_PERIODS["philistia"],
        "summary": "Philistia forms the western coastal political backdrop for many stories in Samuel and Kings.",
        "description": "A cautious regional overlay for the Philistine coastal plain. It is useful for narrative geography, not for exact border claims.",
        "layer_type": "political_context",
        "sort_order": 30,
        "geojson": {
            "type": "Feature",
            "properties": {"title": "Philistia", "confidence": "likely"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[34.1, 32.1], [34.1, 31.0], [35.2, 31.0], [35.2, 32.1], [34.1, 32.1]]],
            },
        },
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed; schematic political context",
        "source_url": "",
        "notes": "The coastal plain shifted over time; the layer is deliberately broad.",
    },
    {
        "id": "israel",
        "name": "Israel",
        "entity_type": "kingdom",
        "period": "Divided Kingdom",
        "periods": _POLITICAL_CONTEXT_PERIODS["israel"],
        "summary": "The northern kingdom provides the historical frame for many prophetic and royal narratives.",
        "description": "A schematic northern kingdom layer that highlights the broad historical setting of Israel after the division of the monarchy.",
        "layer_type": "political_context",
        "sort_order": 40,
        "geojson": {
            "type": "Feature",
            "properties": {"title": "Israel", "confidence": "possible"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[34.05, 33.8], [34.05, 31.6], [35.95, 31.6], [35.95, 33.8], [34.05, 33.8]]],
            },
        },
        "confidence": "possible",
        "confidence_rank": 3,
        "source_name": "BHF curated local seed; schematic political context",
        "source_url": "",
        "notes": "The borders are schematic and should not be treated as exact administrative lines.",
    },
    {
        "id": "judah",
        "name": "Judah",
        "entity_type": "kingdom",
        "period": "Divided Kingdom",
        "periods": _POLITICAL_CONTEXT_PERIODS["judah"],
        "summary": "Judah is the southern monarchy and the setting for much of the late monarchic and exilic material.",
        "description": "A cautious Judah overlay for late monarchic, exile, and return-period study. The shape is intentionally broad.",
        "layer_type": "political_context",
        "sort_order": 50,
        "geojson": {
            "type": "Feature",
            "properties": {"title": "Judah", "confidence": "possible"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[34.55, 32.8], [34.55, 30.8], [35.9, 30.8], [35.9, 32.8], [34.55, 32.8]]],
            },
        },
        "confidence": "possible",
        "confidence_rank": 3,
        "source_name": "BHF curated local seed; schematic political context",
        "source_url": "",
        "notes": "Real borders changed over time, so the overlay stays intentionally approximate.",
    },
    {
        "id": "aram-damascus",
        "name": "Aram-Damascus",
        "entity_type": "regional kingdom",
        "period": "Assyrian period",
        "periods": _POLITICAL_CONTEXT_PERIODS["aram-damascus"],
        "summary": "Aram-Damascus is a key northern neighbor in the prophetic and monarchic narratives.",
        "description": "A schematic overlay for the Aramean political sphere around Damascus. It is useful for conflict context and diplomatic framing.",
        "layer_type": "political_context",
        "sort_order": 60,
        "geojson": {
            "type": "Feature",
            "properties": {"title": "Aram-Damascus", "confidence": "possible"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[35.4, 37.2], [35.4, 32.0], [40.0, 32.0], [40.0, 37.2], [35.4, 37.2]]],
            },
        },
        "confidence": "possible",
        "confidence_rank": 3,
        "source_name": "BHF curated local seed; schematic political context",
        "source_url": "",
        "notes": "Use as a regional cue for Assyrian-era conflicts and alliances.",
    },
    {
        "id": "assyria",
        "name": "Assyria",
        "entity_type": "empire",
        "period": "Assyrian period",
        "periods": _POLITICAL_CONTEXT_PERIODS["assyria"],
        "summary": "Assyria is the dominant imperial background for the fall of the northern kingdom and the Assyrian crisis.",
        "description": "A broad imperial overlay for the Neo-Assyrian sphere. It is schematic and intentionally oversized for study orientation.",
        "layer_type": "political_context",
        "sort_order": 70,
        "geojson": {
            "type": "Feature",
            "properties": {"title": "Assyria", "confidence": "likely"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[35.0, 38.5], [35.0, 28.5], [48.5, 28.5], [48.5, 38.5], [35.0, 38.5]]],
            },
        },
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed; schematic political context",
        "source_url": "",
        "notes": "The imperial extent changed by reign and decade; this is a broad study layer only.",
    },
    {
        "id": "babylon",
        "name": "Babylon",
        "entity_type": "empire",
        "period": "Babylonian period",
        "periods": _POLITICAL_CONTEXT_PERIODS["babylon"],
        "summary": "Babylon frames exile, imperial displacement, and return-from-exile narratives.",
        "description": "A broad imperial overlay for the Neo-Babylonian sphere. It is intended to anchor exilic study passages without overstating precision.",
        "layer_type": "political_context",
        "sort_order": 80,
        "geojson": {
            "type": "Feature",
            "properties": {"title": "Babylon", "confidence": "likely"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[42.5, 36.0], [42.5, 29.0], [49.5, 29.0], [49.5, 36.0], [42.5, 36.0]]],
            },
        },
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed; schematic political context",
        "source_url": "",
        "notes": "A broad frame for exilic material; do not read it as a precise border reconstruction.",
    },
    {
        "id": "persia",
        "name": "Persia",
        "entity_type": "empire",
        "period": "Persian period",
        "periods": _POLITICAL_CONTEXT_PERIODS["persia"],
        "summary": "Persia is the imperial context for return, rebuilding, and post-exilic administration.",
        "description": "A broad imperial overlay for the Persian period. The layer is schematic and intended only for historical orientation.",
        "layer_type": "political_context",
        "sort_order": 90,
        "geojson": {
            "type": "Feature",
            "properties": {"title": "Persia", "confidence": "possible"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[44.0, 40.0], [44.0, 24.0], [63.0, 24.0], [63.0, 40.0], [44.0, 40.0]]],
            },
        },
        "confidence": "possible",
        "confidence_rank": 3,
        "source_name": "BHF curated local seed; schematic political context",
        "source_url": "",
        "notes": "The Persian imperial span is intentionally broad and simplified.",
    },
    {
        "id": "greece",
        "name": "Greece",
        "entity_type": "empire / cultural sphere",
        "period": "Hellenistic period",
        "periods": _POLITICAL_CONTEXT_PERIODS["greece"],
        "summary": "Greece marks the Hellenistic world that reshaped the eastern Mediterranean after Alexander.",
        "description": "A broad Hellenistic political-cultural overlay for study of the intertestamental world and related texts.",
        "layer_type": "political_context",
        "sort_order": 100,
        "geojson": {
            "type": "Feature",
            "properties": {"title": "Greece", "confidence": "possible"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[20.0, 42.0], [20.0, 30.0], [42.0, 30.0], [42.0, 42.0], [20.0, 42.0]]],
            },
        },
        "confidence": "possible",
        "confidence_rank": 2,
        "source_name": "BHF curated local seed; schematic political context",
        "source_url": "",
        "notes": "A broad Hellenistic frame rather than a claim about precise control lines.",
    },
    {
        "id": "rome",
        "name": "Rome",
        "entity_type": "empire",
        "period": "NT / Roman period",
        "periods": _POLITICAL_CONTEXT_PERIODS["rome"],
        "summary": "Rome is the imperial context for the Gospels and Acts.",
        "description": "A broad Roman imperial overlay for New Testament study. It keeps the map context careful and schematic.",
        "layer_type": "political_context",
        "sort_order": 110,
        "geojson": {
            "type": "Feature",
            "properties": {"title": "Rome", "confidence": "likely"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[10.0, 45.0], [10.0, 30.0], [45.0, 30.0], [45.0, 45.0], [10.0, 45.0]]],
            },
        },
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed; schematic political context",
        "source_url": "",
        "notes": "A broad imperial frame for the New Testament rather than a reconstruction of province-by-province borders.",
    },
]


_POLITICAL_CONTEXT_REFERENCES_SEED: list[dict[str, Any]] = [
    {
        "id": "pcr-egypt-1",
        "context_id": "egypt",
        "book": "Exodus",
        "chapter": 1,
        "verse_start": 8,
        "verse_end": 14,
        "relationship_type": "historical_context",
        "notes": "Background of oppression and state power in Egypt.",
    },
    {
        "id": "pcr-egypt-2",
        "context_id": "egypt",
        "book": "Matthew",
        "chapter": 2,
        "verse_start": 13,
        "verse_end": 15,
        "relationship_type": "historical_context",
        "notes": "Egypt as a refuge setting in the infancy narrative.",
    },
    {
        "id": "pcr-canaan-1",
        "context_id": "canaanite-city-states",
        "book": "Joshua",
        "chapter": 11,
        "verse_start": 1,
        "verse_end": 23,
        "relationship_type": "historical_context",
        "notes": "Shows the network of local powers in the land before monarchy.",
    },
    {
        "id": "pcr-philistia-1",
        "context_id": "philistia",
        "book": "1 Samuel",
        "chapter": 4,
        "verse_start": 1,
        "verse_end": 22,
        "relationship_type": "historical_context",
        "notes": "Philistine pressure and conflict with Israel.",
    },
    {
        "id": "pcr-israel-1",
        "context_id": "israel",
        "book": "1 Kings",
        "chapter": 12,
        "verse_start": 16,
        "verse_end": 33,
        "relationship_type": "historical_context",
        "notes": "The northern kingdom emerges after the division of the monarchy.",
    },
    {
        "id": "pcr-judah-1",
        "context_id": "judah",
        "book": "2 Kings",
        "chapter": 18,
        "verse_start": 13,
        "verse_end": 37,
        "relationship_type": "historical_context",
        "notes": "Judah under Assyrian pressure in the late monarchic period.",
    },
    {
        "id": "pcr-aram-1",
        "context_id": "aram-damascus",
        "book": "2 Kings",
        "chapter": 8,
        "verse_start": 7,
        "verse_end": 15,
        "relationship_type": "historical_context",
        "notes": "Aram-Damascus in the wider monarchic conflict world.",
    },
    {
        "id": "pcr-assyria-1",
        "context_id": "assyria",
        "book": "Isaiah",
        "chapter": 36,
        "verse_start": 1,
        "verse_end": 22,
        "relationship_type": "historical_context",
        "notes": "Assyrian invasion and diplomatic pressure.",
    },
    {
        "id": "pcr-babylon-1",
        "context_id": "babylon",
        "book": "2 Kings",
        "chapter": 24,
        "verse_start": 10,
        "verse_end": 17,
        "relationship_type": "historical_context",
        "notes": "Beginning of the exile setting.",
    },
    {
        "id": "pcr-persia-1",
        "context_id": "persia",
        "book": "Ezra",
        "chapter": 1,
        "verse_start": 1,
        "verse_end": 4,
        "relationship_type": "historical_context",
        "notes": "Persian policy frame for return and rebuilding.",
    },
    {
        "id": "pcr-greece-1",
        "context_id": "greece",
        "book": "Daniel",
        "chapter": 8,
        "verse_start": 20,
        "verse_end": 22,
        "relationship_type": "historical_context",
        "notes": "Hellenistic imperial background in apocalyptic imagery.",
    },
    {
        "id": "pcr-rome-1",
        "context_id": "rome",
        "book": "Luke",
        "chapter": 2,
        "verse_start": 1,
        "verse_end": 7,
        "relationship_type": "historical_context",
        "notes": "Roman administrative setting for the infancy narrative.",
    },
    {
        "id": "pcr-rome-2",
        "context_id": "rome",
        "book": "John",
        "chapter": 19,
        "verse_start": 1,
        "verse_end": 16,
        "relationship_type": "historical_context",
        "notes": "Roman provincial power in the passion narrative.",
    },
]


_MANUSCRIPT_ITEMS_SEED: list[dict[str, Any]] = [
    {
        "id": "dead-sea-scrolls",
        "name": "Dead Sea Scrolls",
        "manuscript_type": "manuscript corpus",
        "language": "Hebrew / Aramaic / Greek",
        "date": "3rd century BC to 1st century AD",
        "material": "parchment, papyrus, and leather",
        "discovery_location": "Qumran caves, Dead Sea region",
        "current_location": "Multiple repositories, including the Israel Museum and other institutions",
        "latitude": 31.745,
        "longitude": 35.459,
        "related_books": ["Isaiah", "Psalms", "Deuteronomy", "Daniel"],
        "period": "Second Temple period",
        "periods": _MANUSCRIPT_PERIODS["dead-sea-scrolls"],
        "significance": "A major textual witness to Jewish scripture and Second Temple scribal practice.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The corpus is diverse; no single scroll should be treated as representative of the whole collection.",
        "bhf_caution": "Use the corpus as textual evidence, not as a shortcut to uniformity or certainty on every reading.",
    },
    {
        "id": "nash-papyrus",
        "name": "Nash Papyrus",
        "manuscript_type": "papyrus fragment",
        "language": "Hebrew",
        "date": "2nd century BC to 1st century BC",
        "material": "papyrus",
        "discovery_location": "Egypt, exact provenance uncertain",
        "current_location": "Cambridge University Library",
        "latitude": 30.044,
        "longitude": 31.236,
        "related_books": ["Exodus", "Deuteronomy"],
        "period": "Hellenistic period",
        "periods": _MANUSCRIPT_PERIODS["nash-papyrus"],
        "significance": "An early Hebrew witness to the Decalogue and the Shema tradition.",
        "confidence": "possible",
        "confidence_rank": 3,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The manuscript's discovery history is less secure than some other witnesses, so the map keeps its placement cautious.",
        "bhf_caution": "Treat the location as a study approximation and avoid overclaiming provenance precision.",
    },
    {
        "id": "codex-sinaiticus",
        "name": "Codex Sinaiticus",
        "manuscript_type": "codex",
        "language": "Greek",
        "date": "4th century AD",
        "material": "parchment",
        "discovery_location": "St Catherine's Monastery, Sinai",
        "current_location": "Split between the British Library, Leipzig University Library, St Catherine's Monastery, and the National Library of Russia",
        "latitude": 28.558,
        "longitude": 33.976,
        "related_books": ["Genesis", "Psalms", "Matthew", "John", "Romans", "Hebrews", "Revelation"],
        "period": "NT / Roman period",
        "periods": _MANUSCRIPT_PERIODS["codex-sinaiticus"],
        "significance": "A major early continuous-text witness to the Christian scriptures.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The codex is now divided among repositories, so the map uses its discovery location for orientation.",
        "bhf_caution": "The codex is important evidence, but it does not by itself settle every textual question.",
    },
    {
        "id": "codex-vaticanus",
        "name": "Codex Vaticanus",
        "manuscript_type": "codex",
        "language": "Greek",
        "date": "4th century AD",
        "material": "parchment",
        "discovery_location": "Unknown / not securely recorded",
        "current_location": "Vatican Library",
        "latitude": 41.903,
        "longitude": 12.454,
        "related_books": ["Genesis", "Psalms", "Isaiah", "Matthew", "John", "Romans"],
        "period": "NT / Roman period",
        "periods": _MANUSCRIPT_PERIODS["codex-vaticanus"],
        "significance": "One of the most important early biblical codices.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The discovery history is unclear, so the marker uses the current repository for map orientation.",
        "bhf_caution": "A major witness does not mean a complete answer; keep it as evidence within the wider textual tradition.",
    },
    {
        "id": "aleppo-codex",
        "name": "Aleppo Codex",
        "manuscript_type": "codex",
        "language": "Hebrew",
        "date": "10th century AD",
        "material": "parchment",
        "discovery_location": "Aleppo, Syria",
        "current_location": "Israel Museum, Jerusalem",
        "latitude": 36.202,
        "longitude": 37.134,
        "related_books": ["Deuteronomy", "Psalms", "Isaiah", "Malachi"],
        "period": "NT / Roman period",
        "periods": _MANUSCRIPT_PERIODS["aleppo-codex"],
        "significance": "A landmark Masoretic manuscript for the Hebrew Bible textual tradition.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The map uses the historical discovery context; the manuscript is now held in Jerusalem.",
        "bhf_caution": "A later medieval manuscript can still be an important witness without being the earliest possible reading.",
    },
    {
        "id": "chester-beatty-papyri",
        "name": "Chester Beatty Papyri",
        "manuscript_type": "papyrus codices",
        "language": "Greek",
        "date": "2nd to 4th century AD",
        "material": "papyrus",
        "discovery_location": "Egypt, likely the Fayum region",
        "current_location": "Various repositories",
        "latitude": 29.31,
        "longitude": 30.84,
        "related_books": ["Genesis", "Psalms", "Isaiah", "Matthew", "Mark", "John", "Acts", "Pauline Epistles"],
        "period": "NT / Roman period",
        "periods": _MANUSCRIPT_PERIODS["chester-beatty-papyri"],
        "significance": "An important early papyrus group for Old and New Testament textual study.",
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The collection is multiple codices rather than a single unified manuscript.",
        "bhf_caution": "Use the collection as witness data, not as a blanket rule for every book or reading.",
    },
]


_MANUSCRIPT_SCRIPTURE_LINKS_SEED: list[dict[str, Any]] = [
    {
        "id": "msl-dss-isaiah",
        "item_id": "dead-sea-scrolls",
        "book": "Isaiah",
        "chapter": 40,
        "verse_start": 1,
        "verse_end": 11,
        "relationship_type": "textual_witness",
        "notes": "Representative prophetic text among the scroll corpus.",
    },
    {
        "id": "msl-dss-deut",
        "item_id": "dead-sea-scrolls",
        "book": "Deuteronomy",
        "chapter": 6,
        "verse_start": 4,
        "verse_end": 9,
        "relationship_type": "textual_witness",
        "notes": "Representative Torah text among the scroll corpus.",
    },
    {
        "id": "msl-nash-exodus",
        "item_id": "nash-papyrus",
        "book": "Exodus",
        "chapter": 20,
        "verse_start": 1,
        "verse_end": 17,
        "relationship_type": "textual_witness",
        "notes": "The Decalogue tradition is part of the papyrus's textual significance.",
    },
    {
        "id": "msl-sinaiticus-matthew",
        "item_id": "codex-sinaiticus",
        "book": "Matthew",
        "chapter": 1,
        "verse_start": 1,
        "verse_end": 25,
        "relationship_type": "textual_witness",
        "notes": "Representative Gospel text from the codex.",
    },
    {
        "id": "msl-sinaiticus-john",
        "item_id": "codex-sinaiticus",
        "book": "John",
        "chapter": 1,
        "verse_start": 1,
        "verse_end": 18,
        "relationship_type": "textual_witness",
        "notes": "Representative Johannine text from the codex.",
    },
    {
        "id": "msl-vaticanus-psalms",
        "item_id": "codex-vaticanus",
        "book": "Psalms",
        "chapter": 23,
        "verse_start": 1,
        "verse_end": 6,
        "relationship_type": "textual_witness",
        "notes": "Representative Old Testament witness from the codex.",
    },
    {
        "id": "msl-vaticanus-romans",
        "item_id": "codex-vaticanus",
        "book": "Romans",
        "chapter": 8,
        "verse_start": 1,
        "verse_end": 39,
        "relationship_type": "textual_witness",
        "notes": "Representative Pauline witness from the codex.",
    },
    {
        "id": "msl-aleppo-isaiah",
        "item_id": "aleppo-codex",
        "book": "Isaiah",
        "chapter": 53,
        "verse_start": 1,
        "verse_end": 12,
        "relationship_type": "textual_witness",
        "notes": "Representative prophetic witness from the Aleppo Codex.",
    },
    {
        "id": "msl-aleppo-psalms",
        "item_id": "aleppo-codex",
        "book": "Psalms",
        "chapter": 119,
        "verse_start": 1,
        "verse_end": 176,
        "relationship_type": "textual_witness",
        "notes": "Representative Psalms witness from the Aleppo Codex.",
    },
    {
        "id": "msl-chester-beatty-gospels",
        "item_id": "chester-beatty-papyri",
        "book": "Mark",
        "chapter": 1,
        "verse_start": 1,
        "verse_end": 20,
        "relationship_type": "textual_witness",
        "notes": "Representative Gospel text for the papyrus collection.",
    },
    {
        "id": "msl-chester-beatty-acts",
        "item_id": "chester-beatty-papyri",
        "book": "Acts",
        "chapter": 1,
        "verse_start": 1,
        "verse_end": 26,
        "relationship_type": "textual_witness",
        "notes": "Representative Acts text for the papyrus collection.",
    },
]


_ARCHAEOLOGY_SITES_SEED: list[dict[str, Any]] = [
    {
        "id": "tel-dan",
        "name": "Tel Dan",
        "site_type": "archaeological site",
        "period": "Iron Age II",
        "latitude": 33.246,
        "longitude": 35.651,
        "modern_location": "Northern Galilee, Israel",
        "ancient_region": "Upper Galilee / northern Israel",
        "description": "A tel associated with the northern kingdom period and the findspot for the Tel Dan Stele.",
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Coordinates are approximate site-center coordinates for study mapping.",
    },
    {
        "id": "dhiban",
        "name": "Dhiban (Dibon)",
        "site_type": "archaeological site",
        "period": "Iron Age II",
        "latitude": 31.497,
        "longitude": 35.757,
        "modern_location": "Dhiban, Jordan",
        "ancient_region": "Moab",
        "description": "Modern Dhiban is commonly associated with biblical Dibon and the discovery context for the Mesha Stele.",
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Identification and exact ancient topography remain approximate.",
    },
    {
        "id": "hezekiahs-tunnel",
        "name": "Hezekiah's Tunnel",
        "site_type": "waterworks",
        "period": "Iron Age II",
        "latitude": 31.777,
        "longitude": 35.236,
        "modern_location": "Jerusalem",
        "ancient_region": "Judea",
        "description": "A tunnel in Jerusalem associated with the late monarchic water system and the Siloam inscription.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Useful for study orientation, but the tunnel itself should not be treated as a proof-text.",
    },
    {
        "id": "lachish",
        "name": "Lachish",
        "site_type": "archaeological site",
        "period": "Late Iron Age",
        "latitude": 31.560,
        "longitude": 34.830,
        "modern_location": "Tel Lachish, Israel",
        "ancient_region": "Judah",
        "description": "A major Judahite city whose destruction levels and letters illuminate the Assyrian crisis period.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The site is well known archaeologically, but individual interpretive links should stay cautious.",
    },
    {
        "id": "qumran",
        "name": "Qumran",
        "site_type": "settlement / cave complex",
        "period": "Second Temple period",
        "latitude": 31.745,
        "longitude": 35.459,
        "modern_location": "Northwest Dead Sea region",
        "ancient_region": "Judean wilderness",
        "description": "A study site for the Dead Sea Scrolls and their desert discovery context.",
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The scroll corpus is wider than a single cave or single settlement phase.",
    },
    {
        "id": "babylon",
        "name": "Babylon",
        "site_type": "archaeological site",
        "period": "Neo-Babylonian / Persian period",
        "latitude": 32.536,
        "longitude": 44.420,
        "modern_location": "Hillah, Iraq",
        "ancient_region": "Babylonia",
        "description": "The broader Babylonian archaeological setting relevant to the Cyrus Cylinder and exilic literature.",
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Coordinates mark the broader Babylon area rather than one object findspot.",
    },
    {
        "id": "nimrud",
        "name": "Nimrud",
        "site_type": "archaeological site",
        "period": "Neo-Assyrian period",
        "latitude": 36.100,
        "longitude": 43.320,
        "modern_location": "Near Mosul, Iraq",
        "ancient_region": "Assyria",
        "description": "Assyrian royal site associated with the Black Obelisk of Shalmaneser III.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The obelisk is a royal artifact; the site marker gives the historical location context.",
    },
    {
        "id": "caesarea-maritima",
        "name": "Caesarea Maritima",
        "site_type": "archaeological site",
        "period": "Herodian / Roman period",
        "latitude": 32.500,
        "longitude": 34.888,
        "modern_location": "Mediterranean coast of Israel",
        "ancient_region": "Coastal Judea",
        "description": "A Roman-era port city associated with the Pilate Stone and NT administrative setting.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The site is secure; exact contextual interpretations should still be read carefully.",
    },
    {
        "id": "bethesda-pool",
        "name": "Pool of Bethesda",
        "site_type": "pool complex",
        "period": "Second Temple / Roman period",
        "latitude": 31.783,
        "longitude": 35.233,
        "modern_location": "Jerusalem",
        "ancient_region": "Jerusalem",
        "description": "A pool complex in Jerusalem associated with John 5.",
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Multiple archaeological phases have been proposed; the map stays at a cautious study level.",
    },
    {
        "id": "siloam-pool",
        "name": "Pool of Siloam",
        "site_type": "pool complex",
        "period": "Second Temple / Roman period",
        "latitude": 31.774,
        "longitude": 35.235,
        "modern_location": "Jerusalem",
        "ancient_region": "Jerusalem",
        "description": "A pool complex associated with John 9 and the Jerusalem water system.",
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "A broad site label is preferable to over-specific boundary claims.",
    },
]


_ARCHAEOLOGY_ITEMS_SEED: list[dict[str, Any]] = [
    {
        "id": "tel-dan-stele",
        "site_id": "tel-dan",
        "name": "Tel Dan Stele",
        "item_type": "inscribed basalt stele",
        "period": "9th century BC",
        "relationship": "extra-biblical inscription from the northern kingdom period",
        "why_it_matters": "It is a major extra-biblical witness to Iron Age Israel's political world and the debated 'House of David' phrase.",
        "bhf_caution": "The inscription is important historical evidence, but it does not settle every question about the biblical narratives it is often linked with.",
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Use as a cautious historical witness, not as a shortcut to a full reconstruction.",
    },
    {
        "id": "mesha-stele",
        "site_id": "dhiban",
        "name": "Mesha Stele",
        "item_type": "basalt victory stele",
        "period": "9th century BC",
        "relationship": "extra-biblical inscription from Moab",
        "why_it_matters": "It provides a Moabite perspective on the same broad Iron Age conflict world that appears in 2 Kings.",
        "bhf_caution": "The inscription is a royal victory text and should be read with the usual genre caution.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The inscription is often used for historical context, not for direct exegetical claims.",
    },
    {
        "id": "siloam-inscription",
        "site_id": "hezekiahs-tunnel",
        "name": "Siloam Inscription",
        "item_type": "royal water inscription",
        "period": "late 8th century BC",
        "relationship": "inscription associated with Jerusalem water works",
        "why_it_matters": "It helps contextualize Jerusalem's water system in the late monarchic period and pairs naturally with Hezekiah's tunnel.",
        "bhf_caution": "The inscription supports the water-system context, but the Bible text remains the primary interpretive anchor.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Often discussed alongside 2 Kings 20:20 and 2 Chronicles 32:30.",
    },
    {
        "id": "hezekiahs-tunnel-item",
        "site_id": "hezekiahs-tunnel",
        "name": "Hezekiah's Tunnel",
        "item_type": "water tunnel",
        "period": "late 8th century BC",
        "relationship": "Jerusalem water infrastructure",
        "why_it_matters": "It illustrates the engineering backdrop behind Jerusalem's defenses and water supply during Assyrian pressure.",
        "bhf_caution": "The tunnel is a real ancient feature, but the map should not overstate what any one passage proves about its exact use.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "This item is useful for study context and for comparing the text with the site layout.",
    },
    {
        "id": "lachish-letters",
        "site_id": "lachish",
        "name": "Lachish Letters",
        "item_type": "ostraca / correspondence",
        "period": "late 7th century BC",
        "relationship": "administrative correspondence from Judah's collapse period",
        "why_it_matters": "They provide a close-up glimpse of Judah's military and administrative stress during the Babylonian crisis.",
        "bhf_caution": "These letters are valuable background, but they remain a small and fragmented witness to a broader event.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Helpful for historically careful reading of the late monarchic context.",
    },
    {
        "id": "dead-sea-scrolls",
        "site_id": "qumran",
        "name": "Dead Sea Scrolls",
        "item_type": "manuscript corpus",
        "period": "2nd century BC to 1st century AD",
        "relationship": "textual witness from the Second Temple period",
        "why_it_matters": "They preserve a major collection of Jewish texts from the period between the Old and New Testaments.",
        "bhf_caution": "The corpus is diverse and should not be collapsed into a single viewpoint or single date.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The scrolls are a textual witness; not every scroll needs a passage link.",
    },
    {
        "id": "cyrus-cylinder",
        "site_id": "babylon",
        "name": "Cyrus Cylinder",
        "item_type": "cuneiform royal inscription",
        "period": "6th century BC",
        "relationship": "imperial decree context for the Persian period",
        "why_it_matters": "It is frequently used to frame the Persian-period background of return-from-exile discussions.",
        "bhf_caution": "Use it as a broad historical comparison, not as a one-to-one commentary on a biblical decree text.",
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The cylinder is often discussed in relation to Persian policy and return narratives.",
    },
    {
        "id": "black-obelisk",
        "site_id": "nimrud",
        "name": "Black Obelisk of Shalmaneser III",
        "item_type": "royal monument",
        "period": "9th century BC",
        "relationship": "Assyrian royal propaganda artifact",
        "why_it_matters": "It provides an Assyrian visual and textual context for the power dynamics of the northern kingdom era.",
        "bhf_caution": "Royal monuments are inherently selective sources and must be handled as such.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "Frequently compared with the world of 2 Kings, but not a direct proof of any one verse.",
    },
    {
        "id": "pilate-stone",
        "site_id": "caesarea-maritima",
        "name": "Pilate Stone",
        "item_type": "dedication inscription",
        "period": "1st century AD",
        "relationship": "Roman governor inscription from Judea",
        "why_it_matters": "It confirms Pilate's historical presence in the Roman provincial setting of the Gospels.",
        "bhf_caution": "The inscription confirms a person and office, not the full narrative details of the passion accounts.",
        "confidence": "strong",
        "confidence_rank": 5,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "A secure historical witness for the Roman setting of the New Testament.",
    },
    {
        "id": "pool-of-bethesda",
        "site_id": "bethesda-pool",
        "name": "Pool of Bethesda",
        "item_type": "pool complex",
        "period": "Second Temple / Roman period",
        "relationship": "archaeological context for John's healing narrative",
        "why_it_matters": "It helps situate John 5 within Jerusalem's built environment and water features.",
        "bhf_caution": "The location tradition is useful but should not be treated as a simplistic confirmation of every reconstruction.",
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "The site label should remain broad enough to reflect interpretive caution.",
    },
    {
        "id": "pool-of-siloam",
        "site_id": "siloam-pool",
        "name": "Pool of Siloam",
        "item_type": "pool complex",
        "period": "Second Temple / Roman period",
        "relationship": "archaeological context for John's healing narrative",
        "why_it_matters": "It gives concrete urban context for John 9 and Jerusalem's water infrastructure.",
        "bhf_caution": "The pool is a helpful historical anchor, but the map should still distinguish evidence from interpretation.",
        "confidence": "likely",
        "confidence_rank": 4,
        "source_name": "BHF curated local seed",
        "source_url": "",
        "license": "Local curated data",
        "notes": "A conservative site marker is preferable to a precise claim about every sub-phase.",
    },
]


_ARCHAEOLOGY_SCRIPTURE_LINKS_SEED: list[dict[str, Any]] = [
    {
        "id": "asl-tel-dan-1",
        "item_id": "tel-dan-stele",
        "book": "2 Kings",
        "chapter": 8,
        "verse_start": 28,
        "verse_end": 29,
        "relationship_type": "historical_context",
        "notes": "Helps frame the Aramean conflict world associated with the inscription.",
    },
    {
        "id": "asl-mesha-1",
        "item_id": "mesha-stele",
        "book": "2 Kings",
        "chapter": 3,
        "verse_start": 4,
        "verse_end": 27,
        "relationship_type": "historical_context",
        "notes": "Biblical background for the Moabite conflict world reflected in the stele.",
    },
    {
        "id": "asl-siloam-1",
        "item_id": "siloam-inscription",
        "book": "2 Kings",
        "chapter": 20,
        "verse_start": 20,
        "verse_end": 20,
        "relationship_type": "direct_context",
        "notes": "Pairs naturally with the tunnel and water-system setting.",
    },
    {
        "id": "asl-siloam-2",
        "item_id": "siloam-inscription",
        "book": "2 Chronicles",
        "chapter": 32,
        "verse_start": 30,
        "verse_end": 30,
        "relationship_type": "direct_context",
        "notes": "Historic waterworks context in Judah.",
    },
    {
        "id": "asl-tunnel-1",
        "item_id": "hezekiahs-tunnel-item",
        "book": "2 Kings",
        "chapter": 20,
        "verse_start": 20,
        "verse_end": 20,
        "relationship_type": "direct_context",
        "notes": "The tunnel provides the archaeological setting for the verse.",
    },
    {
        "id": "asl-tunnel-2",
        "item_id": "hezekiahs-tunnel-item",
        "book": "2 Chronicles",
        "chapter": 32,
        "verse_start": 30,
        "verse_end": 30,
        "relationship_type": "direct_context",
        "notes": "Water engineering in Hezekiah's reign.",
    },
    {
        "id": "asl-tunnel-3",
        "item_id": "hezekiahs-tunnel-item",
        "book": "Isaiah",
        "chapter": 22,
        "verse_start": 11,
        "verse_end": 11,
        "relationship_type": "historical_setting",
        "notes": "Background context for Jerusalem's water system.",
    },
    {
        "id": "asl-lachish-1",
        "item_id": "lachish-letters",
        "book": "2 Kings",
        "chapter": 18,
        "verse_start": 13,
        "verse_end": 37,
        "relationship_type": "historical_context",
        "notes": "Frames the Assyrian siege context for Judah.",
    },
    {
        "id": "asl-lachish-2",
        "item_id": "lachish-letters",
        "book": "Jeremiah",
        "chapter": 34,
        "verse_start": 7,
        "verse_end": 7,
        "relationship_type": "historical_context",
        "notes": "Later Judahite crisis context.",
    },
    {
        "id": "asl-cyrus-1",
        "item_id": "cyrus-cylinder",
        "book": "Ezra",
        "chapter": 1,
        "verse_start": 1,
        "verse_end": 4,
        "relationship_type": "historical_context",
        "notes": "Persian-period return setting.",
    },
    {
        "id": "asl-cyrus-2",
        "item_id": "cyrus-cylinder",
        "book": "2 Chronicles",
        "chapter": 36,
        "verse_start": 22,
        "verse_end": 23,
        "relationship_type": "historical_context",
        "notes": "Return-from-exile context in the Chronicler's ending.",
    },
    {
        "id": "asl-black-obelisk-1",
        "item_id": "black-obelisk",
        "book": "2 Kings",
        "chapter": 9,
        "verse_start": 14,
        "verse_end": 15,
        "relationship_type": "historical_context",
        "notes": "Assyrian royal context for Jehu-era reading.",
    },
    {
        "id": "asl-black-obelisk-2",
        "item_id": "black-obelisk",
        "book": "2 Kings",
        "chapter": 10,
        "verse_start": 32,
        "verse_end": 33,
        "relationship_type": "historical_context",
        "notes": "Broad political setting for Assyrian pressure on Israel.",
    },
    {
        "id": "asl-pilate-1",
        "item_id": "pilate-stone",
        "book": "Matthew",
        "chapter": 27,
        "verse_start": 2,
        "verse_end": 2,
        "relationship_type": "historical_context",
        "notes": "Roman governor setting for the passion narrative.",
    },
    {
        "id": "asl-pilate-2",
        "item_id": "pilate-stone",
        "book": "John",
        "chapter": 19,
        "verse_start": 1,
        "verse_end": 16,
        "relationship_type": "historical_context",
        "notes": "Pilate's role in the Gospel trial setting.",
    },
    {
        "id": "asl-bethesda-1",
        "item_id": "pool-of-bethesda",
        "book": "John",
        "chapter": 5,
        "verse_start": 2,
        "verse_end": 9,
        "relationship_type": "direct_context",
        "notes": "The pool appears directly in the passage.",
    },
    {
        "id": "asl-siloam-pool-1",
        "item_id": "pool-of-siloam",
        "book": "John",
        "chapter": 9,
        "verse_start": 7,
        "verse_end": 11,
        "relationship_type": "direct_context",
        "notes": "The pool appears directly in the passage.",
    },
]


_ROUTE_REFERENCES_SEED: list[dict[str, Any]] = [
    {
        "id": "rr-acts13-journey",
        "route_id": "pauls-first-missionary-journey",
        "book": "Acts",
        "chapter": 13,
        "verse_start": 1,
        "verse_end": 52,
        "relationship_type": "directly_mentions",
        "notes": "Antioch sends Paul and Barnabas out in the opening of the journey.",
    },
    {
        "id": "rr-acts14-journey",
        "route_id": "pauls-first-missionary-journey",
        "book": "Acts",
        "chapter": 14,
        "verse_start": 1,
        "verse_end": 28,
        "relationship_type": "directly_mentions",
        "notes": "Continuation of the journey through the Galatian cities.",
    },
]
