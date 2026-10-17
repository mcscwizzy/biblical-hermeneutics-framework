"""Compatibility responses for retired generated BHF Commentary routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse


router = APIRouter()


def _retired_response() -> JSONResponse:
    return JSONResponse(
        {
            "reason": "feature_retired",
            "message": "Generated BHF Commentary has been retired. Use Narrative Explorer when enabled.",
        },
        status_code=410,
    )


@router.get("/api/bhf-commentary")
@router.get("/api/bhf-commentary/{path:path}")
async def retired_bhf_commentary(path: str = "") -> JSONResponse:
    """Return 410 for legacy generated Commentary URLs without loading data."""
    return _retired_response()


@router.get("/internal/commentary-coverage")
@router.get("/api/internal/bhf-commentary/coverage")
async def retired_commentary_coverage() -> JSONResponse:
    """Return 410 for the retired generated Commentary coverage dashboard."""
    return _retired_response()
