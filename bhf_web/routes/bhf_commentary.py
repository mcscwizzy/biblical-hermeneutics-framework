"""API for BHF-generated chapter commentary."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from bhf_web.services.bhf_commentary import COMMENTARY_RELEASE, load_commentary_projection


def register_bhf_commentary_routes(app: FastAPI, *, storage_dir: str | Path) -> None:
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
