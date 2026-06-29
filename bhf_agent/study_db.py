"""SQLite-backed local study data."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bible import BibleError, normalize_book_name


DEFAULT_DB_PATH = Path(".bhf") / "study.sqlite"
HIGHLIGHT_COLORS = {"yellow", "green", "blue", "pink"}
DEFAULT_HIGHLIGHT_COLOR = "yellow"
SCHEMA_VERSION = 7


class StudyDataError(ValueError):
    """Raised when study data input or storage cannot be resolved."""


def initialize_database(path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(path) as connection:
        _ensure_schema(connection)


def list_notes(
    book: str | None = None,
    chapter: int | str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        if book is None and chapter is None:
            rows = connection.execute(
                "SELECT * FROM notes ORDER BY book, chapter, verse_start, created_at"
            ).fetchall()
        else:
            canonical, chapter_number = _reference_filter(book, chapter)
            rows = connection.execute(
                """
                SELECT * FROM notes
                WHERE book = ? AND chapter = ?
                ORDER BY verse_start, verse_end, created_at
                """,
                (canonical, chapter_number),
            ).fetchall()
    return [_note_from_row(row) for row in rows]


def create_note(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    note = _validated_note(data)
    now = _timestamp()
    note_id = uuid.uuid4().hex
    with _connect(path) as connection:
        _ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO notes (
                id, book, chapter, verse_start, verse_end, selected_text,
                note_body, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_id,
                note["book"],
                note["chapter"],
                note["start_verse"],
                note["end_verse"],
                note["selected_text"],
                note["body"],
                now,
                now,
            ),
        )
    return {
        **note,
        "id": note_id,
        "created_at": now,
        "updated_at": now,
    }


def update_note(
    note_id: str,
    updates: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        current_row = connection.execute(
            "SELECT * FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()
        if current_row is None:
            raise StudyDataError("note not found")

        current = _note_from_row(current_row)
        merged = {**current, **updates}
        if "note_body" in updates and "body" not in updates:
            merged["body"] = updates["note_body"]
        if "verse_start" in updates and "start_verse" not in updates:
            merged["start_verse"] = updates["verse_start"]
        if "verse_end" in updates and "end_verse" not in updates:
            merged["end_verse"] = updates["verse_end"]
        note = _validated_note(merged)
        updated_at = _timestamp()
        connection.execute(
            """
            UPDATE notes
            SET book = ?, chapter = ?, verse_start = ?, verse_end = ?,
                selected_text = ?, note_body = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                note["book"],
                note["chapter"],
                note["start_verse"],
                note["end_verse"],
                note["selected_text"],
                note["body"],
                updated_at,
                note_id,
            ),
        )
        row = connection.execute(
            "SELECT * FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()
    return _note_from_row(row)


def delete_note(note_id: str, path: str | Path = DEFAULT_DB_PATH) -> bool:
    with _connect(path) as connection:
        _ensure_schema(connection)
        cursor = connection.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        if cursor.rowcount == 0:
            raise StudyDataError("note not found")
    return True


def list_highlights(
    book: str | None = None,
    chapter: int | str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        if book is None and chapter is None:
            rows = connection.execute(
                "SELECT * FROM highlights ORDER BY book, chapter, verse_start, created_at"
            ).fetchall()
        else:
            canonical, chapter_number = _reference_filter(book, chapter)
            rows = connection.execute(
                """
                SELECT * FROM highlights
                WHERE book = ? AND chapter = ?
                ORDER BY verse_start, verse_end, created_at
                """,
                (canonical, chapter_number),
            ).fetchall()
    return [_highlight_from_row(row) for row in rows]


def create_highlight(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    highlight = _validated_highlight(data)
    now = _timestamp()
    highlight_id = uuid.uuid4().hex
    with _connect(path) as connection:
        _ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO highlights (
                id, book, chapter, verse_start, verse_end, selected_text,
                color, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                highlight_id,
                highlight["book"],
                highlight["chapter"],
                highlight["start_verse"],
                highlight["end_verse"],
                highlight["selected_text"],
                highlight["color"],
                now,
                now,
            ),
        )
    return {
        **highlight,
        "id": highlight_id,
        "created_at": now,
        "updated_at": now,
    }


def delete_highlight(highlight_id: str, path: str | Path = DEFAULT_DB_PATH) -> bool:
    with _connect(path) as connection:
        _ensure_schema(connection)
        cursor = connection.execute(
            "DELETE FROM highlights WHERE id = ?",
            (highlight_id,),
        )
        if cursor.rowcount == 0:
            raise StudyDataError("highlight not found")
    return True


def list_saved_studies(
    book: str | None = None,
    chapter: int | str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        if book is None and chapter is None:
            rows = connection.execute(
                "SELECT * FROM saved_studies ORDER BY created_at DESC"
            ).fetchall()
        else:
            canonical, chapter_number = _reference_filter(book, chapter)
            rows = connection.execute(
                """
                SELECT * FROM saved_studies
                WHERE book = ? AND chapter = ?
                ORDER BY created_at DESC
                """,
                (canonical, chapter_number),
            ).fetchall()
    return [_saved_study_from_row(row) for row in rows]


def get_saved_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM saved_studies WHERE id = ?",
            (study_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("saved study not found")
    return _saved_study_from_row(row)


def create_saved_study(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    study = _validated_saved_study(data)
    now = _timestamp()
    study_id = uuid.uuid4().hex
    with _connect(path) as connection:
        _ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO saved_studies (
                id, title, book, chapter, verse_start, verse_end, selected_text,
                study_type, question, answer, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                study_id,
                study["title"],
                study["book"],
                study["chapter"],
                study["start_verse"],
                study["end_verse"],
                study["selected_text"],
                study["study_type"],
                study["question"],
                study["answer"],
                now,
                now,
            ),
        )
    return {
        **study,
        "id": study_id,
        "created_at": now,
        "updated_at": now,
    }


def delete_saved_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
) -> bool:
    with _connect(path) as connection:
        _ensure_schema(connection)
        cursor = connection.execute(
            "DELETE FROM saved_studies WHERE id = ?",
            (study_id,),
        )
        if cursor.rowcount == 0:
            raise StudyDataError("saved study not found")
    return True


def record_study_action(
    action_type: str,
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    reference = _validated_reference(data)
    now = _timestamp()
    action_id = uuid.uuid4().hex
    action = {
        "id": action_id,
        "action_type": str(action_type).strip(),
        **reference,
        "created_at": now,
    }
    if not action["action_type"]:
        raise StudyDataError("action_type is required")
    with _connect(path) as connection:
        _ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO study_actions (
                id, action_type, book, chapter, verse_start, verse_end,
                selected_text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action["id"],
                action["action_type"],
                action["book"],
                action["chapter"],
                action["start_verse"],
                action["end_verse"],
                action["selected_text"],
                action["created_at"],
            ),
        )
    return action


def list_biblical_places(path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM biblical_places
            ORDER BY confidence_rank DESC, name
            """
        ).fetchall()
    return [_biblical_place_from_row(row) for row in rows]


def get_biblical_place(place_id: str, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM biblical_places WHERE id = ?",
            (place_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("biblical place not found")
    return _biblical_place_from_row(row)


def list_place_references(
    place_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
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
    return [_place_reference_from_row(row) for row in rows]


def list_map_routes(path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM map_routes
            ORDER BY confidence_rank DESC, name
            """
        ).fetchall()
    routes = [_map_route_from_row(row) for row in rows]
    for route in routes:
        route["scripture_links"] = list_route_references(route["id"], path=path)
        route["reference_count"] = len(route["scripture_links"])
    return routes


def list_route_references(
    route_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
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
    return [_route_reference_from_row(row) for row in rows]


def list_historical_layers(
    period: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        if period is None or not str(period).strip() or str(period).strip().lower() == "all":
            rows = connection.execute(
                """
                SELECT *
                FROM historical_layers
                ORDER BY confidence_rank DESC, period, name
                """
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM historical_layers
                WHERE lower(period) = lower(?)
                ORDER BY confidence_rank DESC, period, name
                """,
                (period,),
            ).fetchall()
    return [_historical_layer_from_row(row) for row in rows]


def list_archaeology_sites(path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM archaeology_sites
            ORDER BY confidence_rank DESC, name
            """
        ).fetchall()
    sites = [_archaeology_site_from_row(row) for row in rows]
    for site in sites:
        site["archaeology_items"] = list_archaeology_items(site["id"], path=path)
        site["scripture_links"] = [
            link
            for item in site["archaeology_items"]
            for link in item.get("scripture_links", [])
        ]
        site["reference_count"] = len(site["scripture_links"])
    return sites


def get_archaeology_site(site_id: str, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM archaeology_sites WHERE id = ?",
            (site_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("archaeology site not found")
    site = _archaeology_site_from_row(row)
    site["archaeology_items"] = list_archaeology_items(site_id, path=path)
    site["scripture_links"] = [
        link
        for item in site["archaeology_items"]
        for link in item.get("scripture_links", [])
    ]
    site["reference_count"] = len(site["scripture_links"])
    return site


def list_archaeology_items(
    site_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
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
    items = [_archaeology_item_from_row(row) for row in rows]
    for item in items:
        item["scripture_links"] = list_archaeology_scripture_links(item["id"], path=path)
        item["reference_count"] = len(item["scripture_links"])
    return items


def get_archaeology_item(item_id: str, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM archaeology_items WHERE id = ?",
            (item_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("archaeology item not found")
    item = _archaeology_item_from_row(row)
    item["scripture_links"] = list_archaeology_scripture_links(item_id, path=path)
    item["reference_count"] = len(item["scripture_links"])
    return item


def list_archaeology_scripture_links(
    item_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
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
    return [_archaeology_scripture_link_from_row(row) for row in rows]


def list_saved_map_studies(
    book: str | None = None,
    chapter: int | str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        if book is None and chapter is None:
            rows = connection.execute(
                "SELECT * FROM saved_map_studies ORDER BY created_at DESC"
            ).fetchall()
        else:
            canonical, chapter_number = _reference_filter(book, chapter)
            rows = connection.execute(
                """
                SELECT * FROM saved_map_studies
                WHERE book = ? AND chapter = ?
                ORDER BY created_at DESC
                """,
                (canonical, chapter_number),
            ).fetchall()
    studies = [_saved_map_study_from_row(row) for row in rows]
    for study in studies:
        study["map_notes"] = _map_notes_for_ids(
            place_id=study["selected_place_id"],
            route_id=study["selected_route_id"],
            layer_id=study["selected_layer_id"],
            archaeology_id=study["selected_archaeology_id"],
            path=path,
        )
    return studies


def get_saved_map_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM saved_map_studies WHERE id = ?",
            (study_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("saved map study not found")
    study = _saved_map_study_from_row(row)
    study["map_notes"] = _map_notes_for_ids(
        place_id=study["selected_place_id"],
        route_id=study["selected_route_id"],
        layer_id=study["selected_layer_id"],
        archaeology_id=study["selected_archaeology_id"],
        path=path,
    )
    return study


def create_saved_map_study(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    study = _validated_saved_map_study(data)
    now = _timestamp()
    study_id = uuid.uuid4().hex
    with _connect(path) as connection:
        _ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO saved_map_studies (
                id, book, chapter, verse_start, verse_end, passage_reference,
                selected_place_id, selected_route_id, selected_layer_id,
                archaeology_id,
                selected_layers, map_view_state, generated_summary, user_notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                study_id,
                study["book"],
                study["chapter"],
                study["start_verse"],
                study["end_verse"],
                study["passage_reference"],
                study["selected_place_id"],
                study["selected_route_id"],
                study["selected_layer_id"],
                study["selected_archaeology_id"],
                json.dumps(study["selected_layers"]),
                json.dumps(study["map_view_state"]),
                study["generated_summary"],
                study["user_notes"],
                now,
                now,
            ),
        )
    return {
        **study,
        "id": study_id,
        "created_at": now,
        "updated_at": now,
    }


def delete_saved_map_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
) -> bool:
    with _connect(path) as connection:
        _ensure_schema(connection)
        cursor = connection.execute(
            "DELETE FROM saved_map_studies WHERE id = ?",
            (study_id,),
        )
        if cursor.rowcount == 0:
            raise StudyDataError("saved map study not found")
    return True


def create_map_note(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    note = _validated_map_note(data)
    now = _timestamp()
    note_id = uuid.uuid4().hex
    with _connect(path) as connection:
        _ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO map_notes (
                id, book, chapter, verse_start, verse_end, passage_reference,
                place_id, route_id, layer_id, archaeology_id, note_body, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_id,
                note["book"],
                note["chapter"],
                note["start_verse"],
                note["end_verse"],
                note["passage_reference"],
                note["place_id"],
                note["route_id"],
                note["layer_id"],
                note["archaeology_id"],
                note["note_body"],
                now,
                now,
            ),
        )
    return {
        **note,
        "id": note_id,
        "created_at": now,
        "updated_at": now,
    }


def list_map_notes(
    place_id: str | None = None,
    route_id: str | None = None,
    layer_id: str | None = None,
    archaeology_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    with _connect(path) as connection:
        _ensure_schema(connection)
        clauses: list[str] = []
        params: list[Any] = []
        if place_id is not None:
            clauses.append("place_id = ?")
            params.append(place_id)
        if route_id is not None:
            clauses.append("route_id = ?")
            params.append(route_id)
        if layer_id is not None:
            clauses.append("layer_id = ?")
            params.append(layer_id)
        if archaeology_id is not None:
            clauses.append("archaeology_id = ?")
            params.append(archaeology_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = connection.execute(
            f"SELECT * FROM map_notes {where} ORDER BY created_at DESC",
            params,
        ).fetchall()
    return [_map_note_from_row(row) for row in rows]


def _connect(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _add_column_if_missing(connection: sqlite3.Connection, table: str, column_sql: str) -> None:
    column_name = column_sql.split()[0]
    columns = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column_name not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")


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


def _validated_note(data: dict[str, Any]) -> dict[str, Any]:
    reference = _validated_reference(data)
    body = str(data.get("body") or data.get("note_body") or "").strip()
    if not body:
        raise StudyDataError("note body is required")
    return {
        **reference,
        "body": body,
    }


def _validated_highlight(data: dict[str, Any]) -> dict[str, Any]:
    reference = _validated_reference(data)
    color = str(data.get("color") or DEFAULT_HIGHLIGHT_COLOR).strip().lower()
    if color not in HIGHLIGHT_COLORS:
        raise StudyDataError(
            "highlight color must be one of: " + ", ".join(sorted(HIGHLIGHT_COLORS))
        )
    return {
        **reference,
        "color": color,
    }


def _validated_saved_study(data: dict[str, Any]) -> dict[str, Any]:
    reference = _validated_reference(data)
    study_type = str(
        data.get("study_type") or data.get("ask_mode") or data.get("type") or ""
    ).strip()
    if not study_type:
        raise StudyDataError("study_type is required")
    question = str(data.get("question") or "").strip()
    if not question:
        raise StudyDataError("question is required")
    answer = str(data.get("answer") or data.get("answer_html") or "").strip()
    if not answer:
        raise StudyDataError("answer is required")
    title = str(data.get("title") or "").strip()
    if not title:
        title = _default_saved_study_title(
            reference["book"],
            reference["chapter"],
            reference["start_verse"],
            reference["end_verse"],
            study_type,
        )
    return {
        **reference,
        "study_type": study_type,
        "question": question,
        "answer": answer,
        "title": title,
    }


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
    if not place_id and not route_id and not layer_id and not archaeology_id:
        raise StudyDataError("select a place, route, historical layer, or archaeology item for the note")
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
        "note_body": note_body,
    }


def _validated_reference(data: dict[str, Any]) -> dict[str, Any]:
    try:
        book = normalize_book_name(str(data.get("book", "")))
    except BibleError as exc:
        raise StudyDataError(str(exc)) from exc
    chapter = _positive_int(data.get("chapter"), "chapter")
    start_verse = _positive_int(
        data.get("start_verse") or data.get("verse_start"),
        "start_verse",
    )
    end_verse = _positive_int(
        data.get("end_verse") or data.get("verse_end") or start_verse,
        "end_verse",
    )
    if end_verse < start_verse:
        raise StudyDataError("end_verse must be greater than or equal to start_verse")
    return {
        "book": book,
        "chapter": chapter,
        "start_verse": start_verse,
        "end_verse": end_verse,
        "selected_text": str(data.get("selected_text") or "").strip(),
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


def _reference_filter(
    book: str | None,
    chapter: int | str | None,
) -> tuple[str, int]:
    if book is None or chapter is None:
        raise StudyDataError("book and chapter are both required when filtering study data")
    try:
        canonical = normalize_book_name(str(book))
    except BibleError as exc:
        raise StudyDataError(str(exc)) from exc
    return canonical, _positive_int(chapter, "chapter")


def _note_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "start_verse": int(row["verse_start"]),
        "end_verse": int(row["verse_end"]),
        "selected_text": row["selected_text"],
        "body": row["note_body"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _highlight_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "start_verse": int(row["verse_start"]),
        "end_verse": int(row["verse_end"]),
        "selected_text": row["selected_text"],
        "color": row["color"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _saved_study_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "start_verse": int(row["verse_start"]),
        "end_verse": int(row["verse_end"]),
        "selected_text": row["selected_text"],
        "study_type": row["study_type"],
        "question": row["question"],
        "answer": row["answer"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _biblical_place_from_row(row: sqlite3.Row) -> dict[str, Any]:
    aliases_raw = row["aliases"] or "[]"
    try:
        aliases = json.loads(aliases_raw)
    except json.JSONDecodeError:
        aliases = []
    if not isinstance(aliases, list):
        aliases = []
    return {
        "id": row["id"],
        "name": row["name"],
        "aliases": [str(alias) for alias in aliases if str(alias).strip()],
        "latitude": float(row["latitude"]) if row["latitude"] is not None else None,
        "longitude": float(row["longitude"]) if row["longitude"] is not None else None,
        "modern_location": row["modern_location"],
        "ancient_region": row["ancient_region"],
        "description": row["description"],
        "confidence": row["confidence"],
        "confidence_rank": int(row["confidence_rank"]),
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "license": row["license"],
        "notes": row["notes"],
    }


def _place_reference_from_row(row: sqlite3.Row) -> dict[str, Any]:
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


def _map_route_from_row(row: sqlite3.Row) -> dict[str, Any]:
    geojson_raw = row["geojson"] or "{}"
    try:
        geojson = json.loads(geojson_raw)
    except json.JSONDecodeError:
        geojson = {}
    if not isinstance(geojson, dict):
        geojson = {}
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "period": row["period"],
        "route_type": row["route_type"],
        "geojson": geojson,
        "confidence": row["confidence"],
        "confidence_rank": int(row["confidence_rank"]),
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "notes": row["notes"],
    }


def _route_reference_from_row(row: sqlite3.Row) -> dict[str, Any]:
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


def _historical_layer_from_row(row: sqlite3.Row) -> dict[str, Any]:
    geojson_raw = row["geojson"] or "{}"
    try:
        geojson = json.loads(geojson_raw)
    except json.JSONDecodeError:
        geojson = {}
    if not isinstance(geojson, dict):
        geojson = {}
    return {
        "id": row["id"],
        "name": row["name"],
        "period": row["period"],
        "description": row["description"],
        "layer_type": row["layer_type"],
        "geojson": geojson,
        "confidence": row["confidence"],
        "confidence_rank": int(row["confidence_rank"]),
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "notes": row["notes"],
    }


def _archaeology_site_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "site_type": row["site_type"],
        "period": row["period"],
        "latitude": float(row["latitude"]) if row["latitude"] is not None else None,
        "longitude": float(row["longitude"]) if row["longitude"] is not None else None,
        "modern_location": row["modern_location"],
        "ancient_region": row["ancient_region"],
        "description": row["description"],
        "confidence": row["confidence"],
        "confidence_rank": int(row["confidence_rank"]),
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "license": row["license"],
        "notes": row["notes"],
    }


def _archaeology_item_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "site_id": row["site_id"],
        "name": row["name"],
        "item_type": row["item_type"],
        "period": row["period"],
        "relationship": row["relationship"],
        "why_it_matters": row["why_it_matters"],
        "bhf_caution": row["bhf_caution"],
        "confidence": row["confidence"],
        "confidence_rank": int(row["confidence_rank"]),
        "source_name": row["source_name"],
        "source_url": row["source_url"],
        "license": row["license"],
        "notes": row["notes"],
    }


def _archaeology_scripture_link_from_row(row: sqlite3.Row) -> dict[str, Any]:
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


def _saved_map_study_from_row(row: sqlite3.Row) -> dict[str, Any]:
    selected_layers_raw = row["selected_layers"] or "[]"
    map_view_state_raw = row["map_view_state"] or "{}"
    try:
        selected_layers = json.loads(selected_layers_raw)
    except json.JSONDecodeError:
        selected_layers = []
    if not isinstance(selected_layers, list):
        selected_layers = []
    try:
        map_view_state = json.loads(map_view_state_raw)
    except json.JSONDecodeError:
        map_view_state = {}
    if not isinstance(map_view_state, dict):
        map_view_state = {}
    return {
        "id": row["id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "start_verse": int(row["verse_start"]),
        "end_verse": int(row["verse_end"]),
        "passage_reference": row["passage_reference"],
        "selected_place_id": row["selected_place_id"],
        "selected_route_id": row["selected_route_id"],
        "selected_layer_id": row["selected_layer_id"],
        "selected_archaeology_id": row["archaeology_id"],
        "selected_layers": [str(value) for value in selected_layers if str(value).strip()],
        "map_view_state": map_view_state,
        "generated_summary": row["generated_summary"],
        "user_notes": row["user_notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _map_note_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "start_verse": int(row["verse_start"]),
        "end_verse": int(row["verse_end"]),
        "passage_reference": row["passage_reference"],
        "place_id": row["place_id"],
        "route_id": row["route_id"],
        "layer_id": row["layer_id"],
        "archaeology_id": row["archaeology_id"],
        "note_body": row["note_body"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _map_notes_for_ids(
    *,
    place_id: str = "",
    route_id: str = "",
    layer_id: str = "",
    archaeology_id: str = "",
    path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    if place_id:
        notes.extend(list_map_notes(place_id=place_id, path=path))
    if route_id:
        notes.extend(list_map_notes(route_id=route_id, path=path))
    if layer_id:
        notes.extend(list_map_notes(layer_id=layer_id, path=path))
    if archaeology_id:
        notes.extend(list_map_notes(archaeology_id=archaeology_id, path=path))
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for note in notes:
        note_id = note["id"]
        if note_id in seen:
            continue
        seen.add(note_id)
        unique.append(note)
    return unique


def _positive_int(value: Any, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise StudyDataError(f"{label} must be a positive integer") from exc
    if number <= 0:
        raise StudyDataError(f"{label} must be a positive integer")
    return number


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_saved_study_title(
    book: str,
    chapter: int,
    start_verse: int,
    end_verse: int,
    study_type: str,
) -> str:
    reference = f"{book} {chapter}"
    if start_verse:
        suffix = str(start_verse) if start_verse == end_verse else f"{start_verse}-{end_verse}"
        reference = f"{reference}:{suffix}"
    label = study_type.replace("_", " ").strip().title()
    return f"{reference} - {label}"


def _seed_biblical_places(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM biblical_places").fetchone()[0]
    if existing:
        return

    for place in _BIBLICAL_PLACES_SEED:
        connection.execute(
            """
            INSERT INTO biblical_places (
                id, name, aliases, latitude, longitude, modern_location,
                ancient_region, description, confidence, confidence_rank,
                source_name, source_url, license, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                place["id"],
                place["name"],
                json.dumps(place["aliases"]),
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


def _seed_map_routes(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM map_routes").fetchone()[0]
    if existing:
        return

    for route in _MAP_ROUTES_SEED:
        connection.execute(
            """
            INSERT INTO map_routes (
                id, name, description, period, route_type, geojson,
                confidence, confidence_rank, source_name, source_url, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                route["id"],
                route["name"],
                route["description"],
                route["period"],
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
                id, name, period, description, layer_type, geojson,
                confidence, confidence_rank, source_name, source_url, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                layer["id"],
                layer["name"],
                layer["period"],
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


def _seed_archaeology(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM archaeology_sites").fetchone()[0]
    if existing:
        return

    for site in _ARCHAEOLOGY_SITES_SEED:
        connection.execute(
            """
            INSERT INTO archaeology_sites (
                id, name, site_type, period, latitude, longitude,
                modern_location, ancient_region, description, confidence,
                confidence_rank, source_name, source_url, license, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                site["id"],
                site["name"],
                site["site_type"],
                site["period"],
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
                id, site_id, name, item_type, period, relationship,
                why_it_matters, bhf_caution, confidence, confidence_rank,
                source_name, source_url, license, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["site_id"],
                item["name"],
                item["item_type"],
                item["period"],
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
