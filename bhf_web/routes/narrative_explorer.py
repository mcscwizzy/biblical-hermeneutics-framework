"""Versioned, read-only Narrative Explorer passage route."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from ..cold_start_diagnostics import diagnostic_stage
from ..services.narrative_explorer import (
    CanonicalLookupUnavailable,
    InvalidNarrativePassage,
    NarrativeExplorerService,
)


LOGGER = logging.getLogger(__name__)


def register_narrative_explorer_routes(
    app: FastAPI,
    *,
    study_db_path: str | Path | None = None,
    service: NarrativeExplorerService | None = None,
) -> None:
    explorer_service = service or NarrativeExplorerService(
        study_db_path=study_db_path or ".bhf-data/study.sqlite"
    )

    @app.get(
        "/api/narrative-explorer/v1/passages/{book}/{chapter}",
        response_class=JSONResponse,
    )
    async def narrative_explorer_passage(
        book: str,
        chapter: int,
        verse_start: int | None = Query(default=None),
        verse_end: int | None = Query(default=None),
    ) -> JSONResponse:
        try:
            projection: dict[str, Any] = explorer_service.build(
                book,
                chapter,
                verse_start=verse_start,
                verse_end=verse_end,
            )
        except InvalidNarrativePassage as exc:
            return JSONResponse(
                {"error": "invalid_passage"},
                status_code=exc.status_code,
            )
        except CanonicalLookupUnavailable:
            return JSONResponse(
                {"error": "canonical_lookup_unavailable"},
                status_code=503,
            )
        except Exception as exc:  # noqa: BLE001 - never return implementation details
            LOGGER.error("Narrative Explorer projection failed (%s)", type(exc).__name__)
            return JSONResponse(
                {"error": "narrative_explorer_unavailable"},
                status_code=500,
            )
        with diagnostic_stage("response_construction"):
            return JSONResponse(projection)
