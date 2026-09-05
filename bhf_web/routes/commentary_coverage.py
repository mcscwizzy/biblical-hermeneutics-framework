"""Internal, read-only BHF Commentary coverage dashboard routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bhf_web.services.commentary_coverage import build_commentary_coverage_snapshot


def register_commentary_coverage_routes(
    app: FastAPI,
    *,
    storage_dir: str | Path,
    templates,
) -> None:
    """Register local-admin coverage views without any write endpoints."""

    @app.get("/internal/commentary-coverage", response_class=HTMLResponse)
    async def commentary_coverage_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "commentary_coverage.html",
            {"release": "commentary-v1.0"},
        )

    @app.get("/api/internal/bhf-commentary/coverage", response_class=JSONResponse)
    async def commentary_coverage_api(scope: str | None = None) -> JSONResponse:
        try:
            return JSONResponse(build_commentary_coverage_snapshot(storage_dir, scope=scope))
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        except Exception:
            return JSONResponse(
                {"error": "Commentary coverage is temporarily unavailable."},
                status_code=503,
            )
