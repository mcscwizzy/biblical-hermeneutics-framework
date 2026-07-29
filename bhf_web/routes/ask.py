"""Ask and search-fallback route registration for the FastAPI app."""

from __future__ import annotations

import threading
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bhf_agent.config import ConfigError
from bhf_agent.profiles import ProfileError

from ..forms import config_from_form, form_values_for_ask_prompt, load_web_defaults
from ..jobs import _fake_result
from ..services.ckl_inspector import build_result_inspector_payload
from ..services.web_helpers import (
    build_ask_question as _question_from_form,
    agent_error_status_code,
    deterministic_fact_packet_from_form,
    job_error_message as _job_error_message,
    render_safe_markdown,
    result_metadata,
)


def _public_answer_text(result: Any) -> str:
    public_response = getattr(result, "public_response", None)
    if callable(public_response):
        payload = public_response()
        if isinstance(payload, dict):
            answer = payload.get("answer")
        else:
            answer = getattr(payload, "answer", None)
        if answer is not None:
            return str(answer)
    return str(getattr(result, "answer_text", "") or "")


def _result_error_message(result: Any) -> str:
    errors = getattr(result, "errors", None) or []
    if not errors:
        return "Request failed."
    return "; ".join(str(error) for error in errors)


def _device_study_payload(job: Any, result: Any) -> dict[str, Any] | None:
    context = getattr(job, "study_context", None) or {}
    if not context:
        return None
    metadata = getattr(result, "model_metadata", {}) or {}
    return {
        "title": getattr(job, "question", None) or "Saved study",
        "book": context.get("book"),
        "chapter": context.get("chapter"),
        "start_verse": context.get("start_verse"),
        "end_verse": context.get("end_verse"),
        "selected_text": context.get("selected_text") or "",
        "study_type": getattr(job, "study_type", None) or "question",
        "question": getattr(job, "question", None) or "",
        "answer": _public_answer_text(result),
        "canonical_object_ids": list(metadata.get("canonical_library_object_ids") or []),
    }


def _answer_template_context(
    *,
    error: str | None,
    answer_text: str = "",
    reader_reference: str | None = None,
    can_save_study: bool = False,
    saved_study: Any = None,
    debug_result: Any = None,
    show_debug: bool = False,
    inspector_question: str | None = None,
    inspector_max_context_tokens: int | None = None,
    device_study: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    canonical_context = None
    canonical_object_ids: list[str] = []
    developer_inspector = None
    if show_debug and debug_result is not None:
        metadata = result_metadata(debug_result)
        debug_metadata = getattr(debug_result, "model_metadata", {}) or {}
        if bool((debug_metadata.get("pipeline") or {}).get("ckl_context_injected")):
            canonical_context = debug_metadata.get("canonical_library_context")
            canonical_object_ids = list(debug_metadata.get("canonical_library_object_ids") or [])
        if inspector_question:
            developer_inspector = build_result_inspector_payload(
                inspector_question,
                debug_result,
                max_context_tokens=inspector_max_context_tokens or 3000,
                debug=True,
            )

    return {
        "error": error,
        "saved_study": saved_study,
        "answer_html": render_safe_markdown(answer_text),
        "metadata": metadata,
        "canonical_context": canonical_context,
        "canonical_object_ids": canonical_object_ids,
        "developer_inspector": developer_inspector,
        "reader_reference": reader_reference,
        "can_save_study": can_save_study,
        "device_study": device_study,
    }


def register_ask_routes(
    app: FastAPI,
    *,
    templates: Any,
    job_store: Any,
    agent_factory: Callable[[], Any],
    ask_job_runner: Callable[[Any, dict[str, Any], Any], None],
    search_fallback_job_runner: Callable[[Any, dict[str, Any], Any], None],
    test_mode: bool = False,
) -> None:
    @app.post("/ask", response_class=HTMLResponse)
    async def ask(request: Request) -> HTMLResponse:
        form = form_values_for_ask_prompt(await request.form())
        loaded = load_web_defaults()
        show_debug = bool(getattr(loaded.config, "debug", False))
        try:
            question, reader_reference = _question_from_form(form)
            fact_packet = deterministic_fact_packet_from_form(form)
            config = config_from_form(form, loaded.config)
            result = agent_factory()(config).ask(question, canonical_fact_packet=fact_packet)
        except (ConfigError, ProfileError, ValueError) as exc:
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                _answer_template_context(error=str(exc)),
                status_code=400,
            )

        if test_mode:
            result = _fake_result(question, reader_reference)
            answer_text = _public_answer_text(result)
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                _answer_template_context(
                    error=None,
                    answer_text=answer_text,
                    reader_reference=reader_reference,
                    can_save_study=bool(reader_reference),
                    debug_result=result if show_debug else None,
                    show_debug=show_debug,
                    inspector_question=question,
                    inspector_max_context_tokens=loaded.config.canonical_library.max_context_tokens,
                ),
            )

        answer_text = _public_answer_text(result)
        if getattr(result, "errors", None):
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                _answer_template_context(
                    error=_result_error_message(result),
                    reader_reference=reader_reference,
                    can_save_study=bool(reader_reference),
                    debug_result=result if show_debug else None,
                    show_debug=show_debug,
                    inspector_question=question,
                    inspector_max_context_tokens=loaded.config.canonical_library.max_context_tokens,
                ),
                status_code=agent_error_status_code(result),
            )
        return templates.TemplateResponse(
            request,
            "partials/answer.html",
            _answer_template_context(
                error=None,
                answer_text=answer_text,
                reader_reference=reader_reference,
                can_save_study=bool(reader_reference),
                debug_result=result if show_debug else None,
                show_debug=show_debug,
                inspector_question=question,
                inspector_max_context_tokens=loaded.config.canonical_library.max_context_tokens,
            ),
        )

    @app.post("/ask/jobs", response_class=JSONResponse)
    async def create_ask_job(request: Request) -> JSONResponse:
        form = await request.form()
        job = job_store.create()
        form_values = form_values_for_ask_prompt(form)
        agent_class = agent_factory()
        thread = threading.Thread(
            target=ask_job_runner,
            args=(job, form_values, agent_class),
            daemon=True,
        )
        thread.start()
        return JSONResponse(job.to_dict(), status_code=202)

    @app.get("/ask/status/{job_id}", response_class=JSONResponse)
    async def ask_status(job_id: str) -> JSONResponse:
        job = job_store.get(job_id)
        if job is None:
            return JSONResponse({"error": "job not found"}, status_code=404)
        return JSONResponse(job.to_dict())

    @app.get("/ask/result/{job_id}", response_class=HTMLResponse)
    async def ask_result(request: Request, job_id: str) -> HTMLResponse:
        loaded = load_web_defaults()
        show_debug = bool(getattr(loaded.config, "debug", False))
        job = job_store.get(job_id)
        if job is None:
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                _answer_template_context(error="job not found"),
                status_code=404,
            )
        if not job.done:
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                _answer_template_context(error="answer is still running"),
                status_code=202,
            )
        if job.error:
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                _answer_template_context(
                    error=_job_error_message(job),
                    reader_reference=job.reader_reference,
                ),
                status_code=job.status_code,
            )

        result = job.result
        answer_text = _public_answer_text(result)
        if getattr(result, "errors", None):
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                _answer_template_context(
                    error=_result_error_message(result),
                    reader_reference=job.reader_reference,
                    can_save_study=bool(job.reader_reference),
                    debug_result=result if show_debug else None,
                    show_debug=show_debug,
                    inspector_question=job.question,
                    inspector_max_context_tokens=loaded.config.canonical_library.max_context_tokens,
                    device_study=_device_study_payload(job, result),
                ),
                status_code=agent_error_status_code(result),
            )
        return templates.TemplateResponse(
            request,
            "partials/answer.html",
            _answer_template_context(
                error=None,
                answer_text=answer_text,
                reader_reference=job.reader_reference,
                can_save_study=bool(job.reader_reference),
                debug_result=result if show_debug else None,
                show_debug=show_debug,
                inspector_question=job.question,
                inspector_max_context_tokens=loaded.config.canonical_library.max_context_tokens,
                device_study=_device_study_payload(job, result),
            ),
        )

    @app.post("/api/bible/search/fallback/jobs", response_class=JSONResponse)
    async def create_bible_search_fallback_job(request: Request) -> JSONResponse:
        form = await request.form()
        job = job_store.create()
        form_values = dict(form)
        agent_class = agent_factory()
        thread = threading.Thread(
            target=search_fallback_job_runner,
            args=(job, form_values, agent_class),
            daemon=True,
        )
        thread.start()
        return JSONResponse(job.to_dict(), status_code=202)

    @app.get("/api/bible/search/fallback/status/{job_id}", response_class=JSONResponse)
    async def bible_search_fallback_status(job_id: str) -> JSONResponse:
        job = job_store.get(job_id)
        if job is None:
            return JSONResponse({"error": "job not found"}, status_code=404)
        return JSONResponse(job.to_dict())

    @app.get("/api/bible/search/fallback/result/{job_id}", response_class=JSONResponse)
    async def bible_search_fallback_result(job_id: str) -> JSONResponse:
        job = job_store.get(job_id)
        if job is None:
            return JSONResponse({"error": "job not found"}, status_code=404)
        if not job.done:
            return JSONResponse({"error": "search fallback is still running"}, status_code=202)
        if job.error:
            return JSONResponse({"error": _job_error_message(job)}, status_code=job.status_code)
        return JSONResponse(job.result)
