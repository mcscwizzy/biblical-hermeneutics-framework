"""Curation route registration for the FastAPI app."""

from __future__ import annotations

import json

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Any

from bhf_agent.curation import (
    delete_curation_record,
    export_curation_bundle,
    get_curation_record,
    import_curation_bundle,
    list_curation_records,
    save_curation_record,
)
from bhf_agent.study_db import StudyDataError

from ..services.web_helpers import curation_template_sections, request_payload


def register_curation_routes(app: FastAPI, *, study_db_path: str, templates: Any) -> None:
    @app.get("/curation", response_class=HTMLResponse)
    async def curation(request: Request, collection: str | None = None) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "curation.html",
            {
                "collections": curation_template_sections(study_db_path),
                "collection": collection or "",
                "export_json": json.dumps(
                    export_curation_bundle(path=study_db_path),
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                ),
            },
        )

    @app.get("/api/curation/export", response_class=JSONResponse)
    async def curation_export() -> JSONResponse:
        return JSONResponse(export_curation_bundle(path=study_db_path))

    @app.post("/api/curation/import", response_class=JSONResponse)
    async def curation_import(request: Request) -> JSONResponse:
        try:
            payload = await request_payload(request)
            if "record_json" in payload:
                raw = str(payload["record_json"])
                payload = json.loads(raw)
            result = import_curation_bundle(payload, path=study_db_path)
            return JSONResponse(result)
        except (json.JSONDecodeError, StudyDataError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.get("/api/curation/{collection}", response_class=JSONResponse)
    async def curation_collection(collection: str) -> JSONResponse:
        try:
            return JSONResponse({"records": list_curation_records(collection, path=study_db_path)})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @app.get("/api/curation/{collection}/{record_id}", response_class=JSONResponse)
    async def curation_record(collection: str, record_id: str) -> JSONResponse:
        try:
            return JSONResponse(get_curation_record(collection, record_id, path=study_db_path))
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @app.post("/api/curation/{collection}", response_class=JSONResponse)
    async def curation_save(collection: str, request: Request) -> JSONResponse:
        try:
            payload = await request_payload(request)
            if "record_json" in payload:
                payload = json.loads(str(payload["record_json"]))
            saved = save_curation_record(collection, payload, path=study_db_path)
            return JSONResponse(saved, status_code=201)
        except (json.JSONDecodeError, StudyDataError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.put("/api/curation/{collection}/{record_id}", response_class=JSONResponse)
    async def curation_update(collection: str, record_id: str, request: Request) -> JSONResponse:
        try:
            payload = await request_payload(request)
            if "record_json" in payload:
                payload = json.loads(str(payload["record_json"]))
            payload["id"] = record_id
            saved = save_curation_record(collection, payload, path=study_db_path)
            return JSONResponse(saved)
        except (json.JSONDecodeError, StudyDataError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.delete("/api/curation/{collection}/{record_id}", response_class=JSONResponse)
    async def curation_delete(collection: str, record_id: str) -> JSONResponse:
        try:
            delete_curation_record(collection, record_id, path=study_db_path)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @app.post("/api/curation/{collection}/{record_id}/delete", response_class=JSONResponse)
    async def curation_delete_post(collection: str, record_id: str) -> JSONResponse:
        try:
            delete_curation_record(collection, record_id, path=study_db_path)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
