"""Compatibility helpers for local study notes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .study_db import (
    DEFAULT_DB_PATH,
    StudyDataError,
    create_note,
    delete_note,
    list_notes,
    update_note,
)


DEFAULT_NOTES_PATH = DEFAULT_DB_PATH
NotesError = StudyDataError


def notes_db_path(path: str | Path | None = None) -> str | Path:
    return path or DEFAULT_DB_PATH


__all__ = [
    "DEFAULT_NOTES_PATH",
    "NotesError",
    "create_note",
    "delete_note",
    "list_notes",
    "notes_db_path",
    "update_note",
]
