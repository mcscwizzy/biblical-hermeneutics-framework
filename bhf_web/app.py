"""FastAPI app for the local BHF Agent web UI."""

from __future__ import annotations

import html
import re
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bhf_agent.config import ConfigError
from bhf_agent.profiles import ProfileError, ProfileLoader
from bhf_agent.runner import BHFAgent

from .forms import (
    ANSWER_MODES,
    config_from_form,
    form_values_from_config,
    load_web_defaults,
    validate_question,
)


PACKAGE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


@dataclass
class StatusEntry:
    stage: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"stage": self.stage, "message": self.message}


@dataclass
class AskJob:
    job_id: str
    stage: str = "queued"
    message: str = "Queued"
    history: list[StatusEntry] = field(default_factory=list)
    done: bool = False
    error: str | None = None
    failed_stage: str | None = None
    result: Any = None
    status_code: int = 200

    def emit(self, stage: str, message: str) -> None:
        if self.history and self.history[-1].stage == stage:
            self.message = message
            return
        self.stage = stage
        self.message = message
        self.history.append(StatusEntry(stage=stage, message=message))

    def fail(
        self,
        error: str,
        status_code: int = 400,
        failed_stage: str | None = None,
    ) -> None:
        self.failed_stage = failed_stage or self.stage
        self.error = error
        self.status_code = status_code
        self.stage = "failed"
        self.message = f"Failed: {error}"
        self.done = True
        self.history.append(StatusEntry(stage="failed", message=f"Failed: {error}"))

    def complete(self, result: Any) -> None:
        self.result = result
        self.done = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "stage": self.stage,
            "message": self.message,
            "history": [entry.to_dict() for entry in self.history],
            "done": self.done,
            "error": self.error,
            "failed_stage": self.failed_stage,
        }


class AskJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, AskJob] = {}
        self._lock = threading.Lock()

    def create(self) -> AskJob:
        job = AskJob(job_id=uuid.uuid4().hex)
        job.emit("preparing_request", "Preparing request")
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> AskJob | None:
        with self._lock:
            return self._jobs.get(job_id)


job_store = AskJobStore()


def create_app() -> FastAPI:
    web_app = FastAPI(title="BHF Agent Local UI")
    web_app.mount(
        "/static",
        StaticFiles(directory=str(PACKAGE_DIR / "static")),
        name="static",
    )

    @web_app.get("/api/health", response_class=JSONResponse)
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "bhf-web"}

    @web_app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        loaded = load_web_defaults()
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "form": form_values_from_config(loaded.config),
                "profiles": _available_profiles(loaded.config.profile),
                "answer_modes": ANSWER_MODES,
                "config_warning": loaded.warning,
            },
        )

    @web_app.post("/ask", response_class=HTMLResponse)
    async def ask(request: Request) -> HTMLResponse:
        form = await request.form()
        loaded = load_web_defaults()
        try:
            question = validate_question(form)
            config = config_from_form(form, loaded.config)
            result = BHFAgent(config).ask(question)
        except (ConfigError, ProfileError, ValueError) as exc:
            return templates.TemplateResponse(
                request,
                "partials/answer.html",
                {
                    "error": str(exc),
                    "result": None,
                    "answer_html": "",
                    "metadata": {},
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
            },
        )

    @web_app.post("/ask/jobs", response_class=JSONResponse)
    async def create_ask_job(request: Request) -> JSONResponse:
        form = await request.form()
        job = job_store.create()
        form_values = dict(form)
        thread = threading.Thread(
            target=_run_ask_job,
            args=(job, form_values),
            daemon=True,
        )
        thread.start()
        return JSONResponse(job.to_dict(), status_code=202)

    @web_app.get("/ask/status/{job_id}", response_class=JSONResponse)
    async def ask_status(job_id: str) -> JSONResponse:
        job = job_store.get(job_id)
        if job is None:
            return JSONResponse({"error": "job not found"}, status_code=404)
        return JSONResponse(job.to_dict())

    @web_app.get("/ask/result/{job_id}", response_class=HTMLResponse)
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
            },
        )

    return web_app


def _run_ask_job(job: AskJob, form: dict[str, Any]) -> None:
    try:
        loaded = load_web_defaults()
        question = validate_question(form)
        config = config_from_form(form, loaded.config)
        result = BHFAgent(config, progress_callback=job.emit).ask(question)
    except (ConfigError, ProfileError, ValueError) as exc:
        job.fail(str(exc), status_code=400)
        return
    except Exception as exc:
        job.fail(f"Unexpected agent error: {exc}", status_code=500)
        return

    if getattr(result, "errors", None):
        job.fail(
            "; ".join(str(error) for error in result.errors),
            status_code=502,
            failed_stage="waiting_for_model",
        )
        job.result = result
        return

    job.complete(result)


def _job_error_message(job: AskJob) -> str:
    if job.failed_stage:
        return f"{job.error} (failed during {job.failed_stage.replace('_', ' ')})"
    return job.error or "Request failed."


def result_metadata(result: Any) -> dict[str, Any]:
    metadata = getattr(result, "model_metadata", {}) or {}
    validation = getattr(result, "validation_result", None)
    reference = getattr(result, "reference_context", None)
    genre = getattr(result, "genre_context", None)
    question = getattr(result, "question_context", None)

    return {
        "Profile used": getattr(result, "profile_used", "not available"),
        "Answer mode": metadata.get("answer_mode") or "not available",
        "Detected reference": _format_reference(reference),
        "Detected genre": getattr(genre, "primary_genre", None) or "not detected",
        "Question type": _format_question_type(question),
        "Local knowledge used": _join_or_none(
            metadata.get("local_knowledge_keys") or []
        ),
        "Validation warnings": _join_or_none(getattr(validation, "warnings", [])),
        "Adapter errors": _join_or_none(getattr(result, "errors", [])),
    }


def render_safe_markdown(text: str) -> str:
    """Render a small safe subset of Markdown without accepting raw HTML."""

    if not text.strip():
        return "<p><em>No answer returned.</em></p>"

    blocks: list[str] = []
    list_items: list[str] = []

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>" + "".join(list_items) + "</ul>")
            list_items.clear()

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_list()
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet:
            list_items.append(f"<li>{_inline_markdown(bullet.group(1))}</li>")
            continue

        flush_list()
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            blocks.append(
                f"<h{level}>{_inline_markdown(heading.group(2))}</h{level}>"
            )
        else:
            blocks.append(f"<p>{_inline_markdown(stripped)}</p>")

    flush_list()
    return "\n".join(blocks)


def _inline_markdown(text: str) -> str:
    escaped = html.escape(text, quote=True)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def _available_profiles(selected: str) -> list[str]:
    profiles = ProfileLoader().available_profiles()
    if selected and selected not in profiles:
        profiles.append(selected)
    return sorted(profiles)


def _format_reference(reference: Any) -> str:
    if reference is None:
        return "not detected"
    if not getattr(reference, "is_reference_based", False):
        return f"topic-only ({getattr(reference, 'topic', None) or 'not detected'})"
    location = getattr(reference, "book", None) or "unknown"
    chapter = getattr(reference, "chapter", None)
    verse = getattr(reference, "verse", None)
    testament = getattr(reference, "testament", None)
    if chapter is not None:
        location += f" {chapter}"
    if verse is not None:
        location += f":{verse}"
    if testament:
        location += f" [{testament}]"
    return location


def _format_question_type(question: Any) -> str:
    if question is None:
        return "not detected"
    value = getattr(question, "question_type", None) or "not detected"
    language = getattr(question, "target_language", None)
    if language:
        value += f" [{language}]"
    return value


def _join_or_none(values: list[str]) -> str:
    return ", ".join(str(value) for value in values if value) or "none"


app = create_app()
