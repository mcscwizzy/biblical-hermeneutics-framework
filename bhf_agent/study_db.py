"""SQLite-backed local study data."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bible import BibleError, normalize_book_name


DEFAULT_DB_PATH = Path(".bhf") / "study.sqlite"
HIGHLIGHT_COLORS = {"yellow", "green", "blue", "pink"}
DEFAULT_HIGHLIGHT_COLOR = "yellow"
SCHEMA_VERSION = 2


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


def _connect(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


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
