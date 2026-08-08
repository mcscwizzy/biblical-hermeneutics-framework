"""Deterministic commentary lookup service independent of the AI agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bhf_agent.bible import BibleError, normalize_book_name

from .database_schema import DEFAULT_COMMENTARY_DATABASE_PATH
from .models import CommentaryEntry, CommentarySource
from .repository import CommentaryRepository


class CommentaryService:
    def __init__(self, database_path: str | Path = DEFAULT_COMMENTARY_DATABASE_PATH, repository: CommentaryRepository | None = None):
        self.repository = repository or CommentaryRepository(database_path)

    def lookup_chapter(self, book: str, chapter: int) -> list[CommentaryEntry]:
        canonical_book, chapter_number = _reference(book, chapter)
        return self.repository.lookup_chapter(canonical_book, chapter_number)

    def lookup_passage(self, book: str, chapter: int, start_verse: int, end_verse: int | None = None) -> list[CommentaryEntry]:
        canonical_book, chapter_number = _reference(book, chapter)
        start = _positive_int(start_verse, "start_verse")
        end = _positive_int(end_verse or start, "end_verse")
        if end < start:
            raise ValueError("end_verse must be greater than or equal to start_verse")
        return self.repository.lookup_passage(canonical_book, chapter_number, start, end)

    def source(self) -> CommentarySource | None:
        return self.repository.get_source()

    def diagnostics(self) -> dict[str, Any]:
        if not self.repository.available:
            return {"available": False, "reason": "commentary_not_installed"}
        try:
            sources = self.repository.list_sources()
            raw_import_diagnostics = self.repository.get_metadata("import_diagnostics")
        except Exception as exc:  # noqa: BLE001 - diagnostics must remain safe
            return {"available": False, "reason": "commentary_database_error", "detail": str(exc)}
        diagnostics: dict[str, Any] = {
            "available": True,
            "sources": [source.to_dict() for source in sources],
        }
        if raw_import_diagnostics:
            try:
                diagnostics["import"] = json.loads(raw_import_diagnostics)
            except json.JSONDecodeError:
                diagnostics["import"] = {"warning": "invalid_import_diagnostics"}
        return diagnostics


def _reference(book: str, chapter: int | str) -> tuple[str, int]:
    try:
        canonical = normalize_book_name(str(book))
    except BibleError as exc:
        raise ValueError(str(exc)) from exc
    return canonical, _positive_int(chapter, "chapter")


def _positive_int(value: Any, label: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return result
