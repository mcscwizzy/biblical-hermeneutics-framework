"""Study, notes, and highlights route registration for the FastAPI app."""

from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any, Callable, Mapping

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from bhf_agent.bible import normalize_book_name
from bhf_agent.study_actions import StudyActionRouter, compact_fact_packet
from bhf_agent.study_db import StudyDataError

from ..jobs import run_presentation_job
from ..services.companion_context import (
    CompanionContextService,
)
from ..services.web_helpers import (
    record_action,
    request_payload,
)


_EVIDENCE_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def _validated_presentation_request(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    """Validate cheap ownership fields before a job becomes visible."""

    try:
        book = normalize_book_name(str(payload.get("book") or ""))
    except Exception as exc:
        raise ValueError(str(exc)) from exc
    chapter = _positive_request_int(payload.get("chapter"), "chapter")
    verse_start = _optional_request_int(payload.get("verse_start"), "verse_start")
    verse_end = _optional_request_int(payload.get("verse_end"), "verse_end") or verse_start
    if verse_start is not None and verse_end is not None and verse_end < verse_start:
        raise ValueError("verse_end must be greater than or equal to verse_start")
    evidence_hash = str(payload.get("evidence_hash") or "").strip().lower()
    if not _EVIDENCE_HASH_PATTERN.fullmatch(evidence_hash):
        raise ValueError("evidence_hash must be a SHA-256 fingerprint")
    reference = f"{book} {chapter}"
    if verse_start is not None:
        verse_label = (
            str(verse_start)
            if verse_end in (None, verse_start)
            else f"{verse_start}-{verse_end}"
        )
        reference = f"{reference}:{verse_label}"
    return (
        {
            "book": book,
            "chapter": chapter,
            "verse_start": verse_start,
            "verse_end": verse_end,
            "evidence_hash": evidence_hash,
        },
        reference,
    )


def _positive_request_int(value: Any, label: str) -> int:
    number = _optional_request_int(value, label)
    if number is None:
        raise ValueError(f"{label} must be a positive integer")
    return number


def _optional_request_int(value: Any, label: str) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive integer") from exc
    if number <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return number


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
    presentation_job_runner: Callable[..., None] = run_presentation_job,
    presentation_jobs_enabled: bool = True,
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
            context = await run_in_threadpool(
                companion_context.build,
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                translation=translation,
            )
            return JSONResponse(context)
        except (ValueError, StudyDataError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        except Exception as exc:  # noqa: BLE001 - invalid books surface as a compact client error
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.post("/api/study/presentation", response_class=JSONResponse)
    async def post_study_presentation(request: Request) -> JSONResponse:
        """Validate and queue optional enhancement without waiting for its model."""

        try:
            payload = await request_payload(request)
            if not presentation_jobs_enabled:
                return JSONResponse(
                    {
                        "error": "Presentation jobs require a durable BHF backend.",
                        "error_category": "presentation_unavailable",
                    },
                    status_code=503,
                )
            request_values, reference = _validated_presentation_request(payload)
            transient_api_key = request.headers.get("X-BHF-OpenRouter-Key") or None
            profile = payload.get("ai_profile")
            if profile is not None and not isinstance(profile, Mapping):
                raise ValueError("ai_profile must be an object")
            if isinstance(profile, Mapping):
                requested_adapter = str(profile.get("adapter") or "openrouter").strip()
                if requested_adapter != "openrouter":
                    raise ValueError(
                        "Request-scoped presentation supports OpenRouter browser credentials only."
                    )
                if not transient_api_key:
                    raise ValueError(
                        "An OpenRouter browser credential is required for the submitted AI profile."
                    )
            runtime = getattr(request.app.state, "presentation_runtime", None)
            if runtime is None:
                raise ValueError("Presentation provider runtime is unavailable.")
            provider, generation_profile = runtime.provider_for_request(
                profile,
                transient_api_key,
            )
            if provider is None:
                return JSONResponse(
                    {
                        "error": "Connect an AI provider to add AI passage summaries.",
                        "error_category": "provider_unavailable",
                    },
                    status_code=400,
                )
            deadline_seconds = min(30.0, float(runtime.settings.timeout_seconds)) + 5.0
            job = job_store.create_presentation(
                reference=reference,
                evidence_hash=request_values["evidence_hash"],
                deadline_seconds=deadline_seconds,
            )
            # The request-scoped provider may contain a browser credential. It
            # exists only in this execution closure and is never job metadata.
            thread = threading.Thread(
                target=presentation_job_runner,
                args=(
                    job,
                    companion_context,
                    request_values,
                    provider,
                    generation_profile,
                ),
                daemon=True,
            )
            thread.start()
            response = job.to_dict()
            response["poll_url"] = f"/api/study/presentation/jobs/{job.job_id}"
            return JSONResponse(response, status_code=202)
        except (ValueError, StudyDataError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        except Exception:  # noqa: BLE001 - optional generation fails independently
            return JSONResponse(
                {
                    "error": "Presentation enhancement is unavailable.",
                    "error_category": "presentation_unavailable",
                },
                status_code=503,
            )

    @app.get(
        "/api/study/presentation/jobs/{job_id}",
        response_class=JSONResponse,
    )
    async def get_study_presentation_job(job_id: str) -> JSONResponse:
        job = job_store.get_presentation(job_id)
        if job is None:
            return JSONResponse(
                {
                    "error": "Presentation job was not found.",
                    "error_category": "presentation_unavailable",
                },
                status_code=404,
            )
        return JSONResponse(job.to_dict())

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
                result.presentation = await run_in_threadpool(
                    context_presenter,
                    result.evidence_packet,
                )
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
