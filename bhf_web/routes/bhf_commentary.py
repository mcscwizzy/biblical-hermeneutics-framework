"""API for BHF-generated chapter commentary."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_web.services.bhf_commentary import (
    COMMENTARY_RELEASE,
    load_commentary_projection,
    project_commentary_evidence,
    search_commentary,
)


def register_bhf_commentary_routes(
    app: FastAPI,
    *,
    storage_dir: str | Path,
    companion_context_service=None,
) -> None:
    """Register routes for BHF-generated commentary."""

    storage_path = Path(storage_dir)

    @app.get("/api/bhf-commentary/diagnostics", response_class=JSONResponse)
    async def bhf_commentary_diagnostics() -> JSONResponse:
        """Return diagnostic info about BHF commentary availability."""
        from bhf_agent.chapter_commentary.storage import list_commentaries

        commentaries = list_commentaries(storage_path)
        return JSONResponse(
            {
                "available": len(commentaries) > 0,
                "total_files": len(commentaries),
                "status": "ok" if len(commentaries) > 0 else "no_commentaries",
            }
        )

    @app.get("/api/bhf-commentary/search", response_class=JSONResponse)
    async def bhf_commentary_search(
        q: str = "",
        availability: str | None = None,
        book: str | None = None,
        chapter: int | None = None,
        verse: str | None = None,
        category: str | None = None,
        entity: str | None = None,
        period: str | None = None,
        limit: int = 25,
    ) -> JSONResponse:
        """Search immutable commentary projections using existing reader data."""
        try:
            return JSONResponse(
                search_commentary(
                    storage_path,
                    query=q,
                    availability=availability,
                    book=book,
                    chapter=chapter,
                    verse=verse,
                    category=category,
                    entity=entity,
                    period=period,
                    limit=limit,
                )
            )
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.get("/api/bhf-commentary/{book}/{chapter}", response_class=JSONResponse)
    async def bhf_commentary_chapter(
        book: str,
        chapter: int,
    ) -> JSONResponse:
        """Get BHF commentary for a chapter."""
        try:
            commentary = load_commentary_projection(storage_path, book, chapter)

            if commentary is None:
                return JSONResponse(
                    {
                        "available": False,
                        "reason": "bhf_commentary_not_available",
                        "release": COMMENTARY_RELEASE,
                        "book": book,
                        "chapter": chapter,
                    }
                )

            return JSONResponse(
                {
                    "available": True,
                    **commentary,
                }
            )
        except Exception:
            return JSONResponse(
                {
                    "available": False,
                    "reason": "bhf_commentary_error",
                    "release": COMMENTARY_RELEASE,
                    "book": book,
                    "chapter": chapter,
                }
            )

    @app.get("/api/bhf-commentary/{book}/{chapter}/evidence", response_class=JSONResponse)
    async def bhf_commentary_evidence(book: str, chapter: int) -> JSONResponse:
        """Return only evidence explicitly cited by the stored commentary."""
        try:
            commentary = load_commentary(storage_path, book, chapter)
            if commentary is None:
                return JSONResponse(
                    {
                        "available": False,
                        "reason": "bhf_commentary_not_available",
                        "release": COMMENTARY_RELEASE,
                        "book": book,
                        "chapter": chapter,
                        "evidence_items": [],
                        "unavailable_ids": [],
                        "evidence_count": 0,
                    }
                )
            if companion_context_service is None:
                return JSONResponse(
                    {"available": False, "reason": "commentary_evidence_unavailable"},
                    status_code=503,
                )
            bundle = await run_in_threadpool(
                companion_context_service.build_evidence_bundle_for_passage,
                book=book,
                chapter=chapter,
            )
            return JSONResponse(
                {"available": True, **project_commentary_evidence(commentary, bundle)}
            )
        except Exception:
            return JSONResponse(
                {
                    "available": False,
                    "reason": "commentary_evidence_error",
                    "release": COMMENTARY_RELEASE,
                    "book": book,
                    "chapter": chapter,
                },
                status_code=503,
            )
