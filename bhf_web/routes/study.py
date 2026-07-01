"""Study, notes, and highlights route registration for the FastAPI app."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bhf_agent.study_db import (
    StudyDataError,
    create_highlight,
    create_note,
    create_saved_study,
    delete_highlight,
    delete_note,
    delete_saved_study,
    get_saved_study,
    list_highlights,
    list_notes,
    list_saved_studies,
    update_note,
)

from ..services.web_helpers import (
    record_action,
    request_payload,
    render_safe_markdown,
    saved_study_payload_from_request,
)


def register_study_routes(
    app: FastAPI,
    *,
    study_db_path: str,
    templates: Any,
    job_store: Any,
) -> None:
    @app.get("/api/saved-studies", response_class=JSONResponse)
    async def saved_studies(book: str | None = None, chapter: int | None = None) -> JSONResponse:
        try:
            return JSONResponse({"saved_studies": list_saved_studies(book, chapter, path=study_db_path)})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.get("/api/saved-studies/{study_id}", response_class=HTMLResponse)
    async def saved_study(request: Request, study_id: str) -> HTMLResponse:
        try:
            study = get_saved_study(study_id, path=study_db_path)
        except StudyDataError as exc:
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                {
                    "error": str(exc),
                    "result": None,
                    "saved_study": None,
                    "answer_html": "",
                    "metadata": {},
                    "reader_reference": None,
                },
                status_code=404,
            )

        reference = f"{study['book']} {study['chapter']}"
        if study["start_verse"]:
            suffix = (
                str(study["start_verse"])
                if study["start_verse"] == study["end_verse"]
                else f"{study['start_verse']}-{study['end_verse']}"
            )
            reference = f"{reference}:{suffix}"

        return templates.TemplateResponse(
            request,
            "partials/answer.html",
            {
                "error": None,
                "result": None,
                "saved_study": study,
                "answer_html": render_safe_markdown(study["answer"]),
                "metadata": {
                    "Title": study["title"],
                    "Study type": study["study_type"],
                    "Created": study["created_at"],
                    "Updated": study["updated_at"],
                },
                "reader_reference": reference,
            },
        )

    @app.post("/api/saved-studies", response_class=JSONResponse)
    async def post_saved_study(request: Request) -> JSONResponse:
        try:
            payload = await request_payload(request)
            study = saved_study_payload_from_request(payload, job_store=job_store)
            saved = create_saved_study(study, path=study_db_path)
            record_action("study_saved", saved, path=study_db_path)
            return JSONResponse(saved, status_code=201)
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.delete("/api/saved-studies/{study_id}", response_class=JSONResponse)
    async def remove_saved_study(study_id: str) -> JSONResponse:
        try:
            delete_saved_study(study_id, path=study_db_path)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @app.get("/api/notes/{book}/{chapter}", response_class=JSONResponse)
    async def get_notes(book: str, chapter: int) -> JSONResponse:
        try:
            return JSONResponse({"notes": list_notes(book, chapter, path=study_db_path)})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.post("/api/notes", response_class=JSONResponse)
    async def post_note(request: Request) -> JSONResponse:
        try:
            payload = await request_payload(request)
            note = create_note(payload, path=study_db_path)
            record_action("note_created", note, path=study_db_path)
            return JSONResponse(note, status_code=201)
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.put("/api/notes/{note_id}", response_class=JSONResponse)
    async def put_note(request: Request, note_id: str) -> JSONResponse:
        try:
            payload = await request_payload(request)
            return JSONResponse(update_note(note_id, payload, path=study_db_path))
        except StudyDataError as exc:
            status = 404 if "not found" in str(exc) else 400
            return JSONResponse({"error": str(exc)}, status_code=status)

    @app.delete("/api/notes/{note_id}", response_class=JSONResponse)
    async def remove_note(note_id: str) -> JSONResponse:
        try:
            delete_note(note_id, path=study_db_path)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @app.get("/api/highlights/{book}/{chapter}", response_class=JSONResponse)
    async def get_highlights(book: str, chapter: int) -> JSONResponse:
        try:
            return JSONResponse({"highlights": list_highlights(book, chapter, path=study_db_path)})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.post("/api/highlights", response_class=JSONResponse)
    async def post_highlight(request: Request) -> JSONResponse:
        try:
            payload = await request_payload(request)
            highlight = create_highlight(payload, path=study_db_path)
            record_action("highlight_created", highlight, path=study_db_path)
            return JSONResponse(highlight, status_code=201)
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.delete("/api/highlights/{highlight_id}", response_class=JSONResponse)
    async def remove_highlight(highlight_id: str) -> JSONResponse:
        try:
            delete_highlight(highlight_id, path=study_db_path)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
