"""First-class archaeology exploration routes."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse


def register_archaeology_routes(app: FastAPI, *, templates: Any) -> None:
    @app.get("/archaeology", response_class=HTMLResponse)
    async def archaeology_explore(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "archaeology.html", {})

