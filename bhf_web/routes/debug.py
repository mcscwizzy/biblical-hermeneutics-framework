"""Developer-only debug routes for CKL retrieval inspection."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .. import settings
from ..forms import load_web_defaults
from ..services.ckl_inspector import build_search_inspector_payload
from ..services.web_helpers import request_payload


def register_debug_routes(app: FastAPI) -> None:
    @app.get(
        "/api/debug/runtime-storage",
        response_class=JSONResponse,
        include_in_schema=False,
    )
    async def debug_runtime_storage() -> JSONResponse:
        loaded = load_web_defaults()
        if not bool(getattr(loaded.config, "debug", False)):
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(
            {
                "data_directory": str(settings.DATA_DIR),
                "job_database_path": str(settings.JOB_DB_PATH),
                "job_store": "sqlite",
                "deployment_mode": "single_instance",
            }
        )

    @app.post("/api/debug/ckl-search", response_class=JSONResponse, include_in_schema=False)
    async def debug_ckl_search(request: Request) -> JSONResponse:
        loaded = load_web_defaults()
        if not bool(getattr(loaded.config, "debug", False)):
            return JSONResponse({"error": "not found"}, status_code=404)

        try:
            payload = await request_payload(request)
        except Exception as exc:  # noqa: BLE001 - developer route should fail cleanly
            return JSONResponse({"error": str(exc)}, status_code=400)

        query = str(payload.get("query") or payload.get("question") or "").strip()
        if not query:
            return JSONResponse({"error": "query is required"}, status_code=400)

        limit = _int_value(payload.get("limit"), default=8)
        answer_mode = str(payload.get("answer_mode") or loaded.config.answer_mode or "study").strip() or "study"
        max_context_tokens = _int_value(
            payload.get("max_context_tokens"),
            default=int(
                getattr(
                    getattr(loaded.config, "canonical_library", None),
                    "max_context_tokens",
                    3000,
                )
                or 3000
            ),
        )

        inspector = build_search_inspector_payload(
            query,
            limit=limit,
            answer_mode=answer_mode,
            max_context_tokens=max_context_tokens,
            debug=True,
        )
        return JSONResponse(inspector)


def _int_value(value: object, default: int) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default
