"""Study, notes, and highlights route registration for the FastAPI app."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from bhf_agent.study_actions import StudyActionRouter, compact_fact_packet
from bhf_agent.study_db import StudyDataError

from ..services.companion_context import CompanionContextService
from ..services.web_helpers import (
    record_action,
    request_payload,
)


def register_study_routes(
    app: FastAPI,
    *,
    study_db_path: str,
    templates: Any,
    job_store: Any,
    study_action_router: StudyActionRouter | None = None,
    context_presenter: Callable[[Mapping[str, Any]], dict[str, Any]] | None = None,
    commentary_db_path: str | Path = ".bhf/commentary.sqlite",
    companion_context_service: CompanionContextService | None = None,
) -> None:
    router = study_action_router or StudyActionRouter()
    companion_context = companion_context_service or CompanionContextService(
        study_db_path=study_db_path,
        commentary_db_path=commentary_db_path,
    )
    app.state.companion_context_service = companion_context

    def device_only_response(label: str) -> JSONResponse:
        return JSONResponse(
            {
                "error": f"{label} are stored only on this device.",
                "device_only": True,
            },
            status_code=410,
        )

    @app.get("/api/study/companion-context", response_class=JSONResponse)
    async def get_companion_context(
        book: str,
        chapter: int,
        verse_start: int | None = None,
        verse_end: int | None = None,
        translation: str | None = None,
    ) -> JSONResponse:
        """Return compact resource availability without loading resource bodies."""

        try:
            return JSONResponse(
                companion_context.build(
                    book=book,
                    chapter=chapter,
                    verse_start=verse_start,
                    verse_end=verse_end,
                    translation=translation,
                )
            )
        except (ValueError, StudyDataError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        except Exception as exc:  # noqa: BLE001 - invalid books surface as a compact client error
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.post("/api/study/actions", response_class=JSONResponse)
    async def post_study_action(request: Request) -> JSONResponse:
        try:
            payload = await request_payload(request)
            action = payload.get("action") or payload.get("study_action")
            passage = {
                "book": payload.get("book") or payload.get("reader_book"),
                "chapter": payload.get("chapter") or payload.get("reader_chapter"),
                "start_verse": payload.get("start_verse") or payload.get("verse_start") or payload.get("reader_start_verse"),
                "end_verse": payload.get("end_verse") or payload.get("verse_end") or payload.get("reader_end_verse"),
                "selected_verses": payload.get("selected_verses") or payload.get("reader_selected_verses"),
                "selected_text": payload.get("selected_text") or payload.get("reader_selected_text"),
                "translation": payload.get("translation") or payload.get("reader_translation") or payload.get("source_translation"),
                "word_position": payload.get("word_position") or payload.get("position") or payload.get("token_position"),
                "strongs_number": payload.get("strongs_number") or payload.get("strongs") or payload.get("selected_strongs"),
                "lemma": payload.get("lemma") or payload.get("selected_lemma"),
                "language": payload.get("language") or payload.get("source_language"),
                "surface_form": payload.get("surface_form") or payload.get("selected_surface_form"),
            }
            result = router.execute(
                str(action or ""),
                passage=passage,
                query=str(payload.get("query") or payload.get("question") or ""),
            )
            if (
                context_presenter is not None
                and payload.get("presentation") == "ai"
                and result.evidence_packet
                and result.action != "archaeology"
            ):
                result.presentation = context_presenter(result.evidence_packet)
            data = result.to_dict()
            data["fact_packet"] = compact_fact_packet(result)
            record_action(result.action, result.metadata, path=study_db_path)
            return JSONResponse(data)
        except (StudyDataError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        except Exception as exc:  # noqa: BLE001 - API failures must remain JSON
            return JSONResponse(
                {"error": "Could not load the study action.", "detail": str(exc)},
                status_code=500,
            )

    # Personal reader records intentionally have no server persistence or API
    # representation. The browser intercepts these paths and uses IndexedDB.
    @app.get("/api/saved-studies", response_class=JSONResponse)
    async def saved_studies() -> JSONResponse:
        return device_only_response("Saved studies")

    @app.get("/api/saved-studies/{study_id}", response_class=JSONResponse)
    async def saved_study(study_id: str) -> JSONResponse:
        return device_only_response("Saved studies")

    @app.post("/api/saved-studies", response_class=JSONResponse)
    async def post_saved_study() -> JSONResponse:
        return device_only_response("Saved studies")

    @app.delete("/api/saved-studies/{study_id}", response_class=JSONResponse)
    async def remove_saved_study(study_id: str) -> JSONResponse:
        return device_only_response("Saved studies")

    @app.get("/api/notes", response_class=JSONResponse)
    async def get_all_notes() -> JSONResponse:
        return device_only_response("Notes")

    @app.get("/api/notes/{book}/{chapter}", response_class=JSONResponse)
    async def get_notes(book: str, chapter: int) -> JSONResponse:
        return device_only_response("Notes")

    @app.post("/api/notes", response_class=JSONResponse)
    async def post_note() -> JSONResponse:
        return device_only_response("Notes")

    @app.put("/api/notes/{note_id}", response_class=JSONResponse)
    async def put_note(note_id: str) -> JSONResponse:
        return device_only_response("Notes")

    @app.delete("/api/notes/{note_id}", response_class=JSONResponse)
    async def remove_note(note_id: str) -> JSONResponse:
        return device_only_response("Notes")

    @app.get("/api/highlights/{book}/{chapter}", response_class=JSONResponse)
    async def get_highlights(book: str, chapter: int) -> JSONResponse:
        return device_only_response("Highlights")

    @app.post("/api/highlights", response_class=JSONResponse)
    async def post_highlight() -> JSONResponse:
        return device_only_response("Highlights")

    @app.delete("/api/highlights/{highlight_id}", response_class=JSONResponse)
    async def remove_highlight(highlight_id: str) -> JSONResponse:
        return device_only_response("Highlights")
