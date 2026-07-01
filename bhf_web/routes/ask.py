"""Ask and search-fallback route registration for the FastAPI app."""

from __future__ import annotations

import threading
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bhf_agent.config import ConfigError
from bhf_agent.profiles import ProfileError

from ..forms import config_from_form, load_web_defaults
from ..services.web_helpers import (
    build_ask_question as _question_from_form,
    job_error_message as _job_error_message,
    render_safe_markdown,
    result_metadata,
)


def register_ask_routes(
    app: FastAPI,
    *,
    templates: Any,
    job_store: Any,
    agent_factory: Callable[[], Any],
    ask_job_runner: Callable[[Any, dict[str, Any], Any], None],
    search_fallback_job_runner: Callable[[Any, dict[str, Any], Any], None],
) -> None:
    @app.post("/ask", response_class=HTMLResponse)
    async def ask(request: Request) -> HTMLResponse:
        form = await request.form()
        loaded = load_web_defaults()
        try:
            question, reader_reference = _question_from_form(form)
            config = config_from_form(form, loaded.config)
            result = agent_factory()(config).ask(question)
        except (ConfigError, ProfileError, ValueError) as exc:
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                {
                    "error": str(exc),
                    "result": None,
                    "answer_html": "",
                    "metadata": {},
                    "reader_reference": None,
                },
                status_code=400,
            )

        return templates.TemplateResponse(
            request,
            "partials/answer.html",
            {
                "error": None,
                "result": result,
                "answer_html": render_safe_markdown(result.answer_text),
                "metadata": result_metadata(result),
                "reader_reference": reader_reference,
            },
        )

    @app.post("/ask/jobs", response_class=JSONResponse)
    async def create_ask_job(request: Request) -> JSONResponse:
        form = await request.form()
        job = job_store.create()
        form_values = dict(form)
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
        job = job_store.get(job_id)
        if job is None:
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                {
                    "error": "job not found",
                    "result": None,
                    "answer_html": "",
                    "metadata": {},
                    "reader_reference": None,
                },
                status_code=404,
            )
        if not job.done:
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                {
                    "error": "answer is still running",
                    "result": None,
                    "answer_html": "",
                    "metadata": {},
                    "reader_reference": None,
                },
                status_code=202,
            )
        if job.error:
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                {
                    "error": _job_error_message(job),
                    "result": None,
                    "answer_html": "",
                    "metadata": {},
                    "reader_reference": job.reader_reference,
                },
                status_code=job.status_code,
            )

        result = job.result
        return templates.TemplateResponse(
            request,
            "partials/answer.html",
            {
                "error": None,
                "result": result,
                "answer_html": render_safe_markdown(result.answer_text),
                "metadata": result_metadata(result),
                "reader_reference": job.reader_reference,
            },
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
