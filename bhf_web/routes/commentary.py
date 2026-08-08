"""Direct reader API for locally installed published commentary."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from framework.commentary.service import CommentaryService


def register_commentary_routes(app: FastAPI, *, database_path: str | Path) -> None:
    service = CommentaryService(database_path=database_path)

    @app.get("/api/commentary/diagnostics", response_class=JSONResponse)
    async def commentary_diagnostics() -> JSONResponse:
        return JSONResponse(service.diagnostics())

    @app.get("/api/commentary/{book}/{chapter}", response_class=JSONResponse)
    async def commentary_chapter(
        book: str,
        chapter: int,
        start_verse: int | None = None,
        end_verse: int | None = None,
    ) -> JSONResponse:
        if not service.repository.available:
            return JSONResponse(
                {"available": False, "reason": "commentary_not_installed", "book": book, "chapter": chapter, "entries": []}
            )
        try:
            entries = (
                service.lookup_passage(book, chapter, start_verse, end_verse or start_verse)
                if start_verse is not None
                else service.lookup_chapter(book, chapter)
            )
            source = service.source()
            return JSONResponse(
                {
                    "available": True,
                    "book": entries[0].anchor.book if entries and entries[0].anchor else book,
                    "chapter": chapter,
                    "source": source.to_dict() if source else None,
                    "entries": [entry.to_dict() for entry in entries],
                }
            )
        except (ValueError, sqlite3.DatabaseError) as exc:
            return JSONResponse(
                {"available": False, "reason": "commentary_database_error", "detail": str(exc), "entries": []}
            )
