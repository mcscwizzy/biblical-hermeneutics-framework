"""Job state and worker helpers for the FastAPI app."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from bhf_agent.config import ConfigError
from bhf_agent.profiles import ProfileError
from bhf_agent.runner import BHFAgent
from bhf_agent.study_db import DEFAULT_DB_PATH

from .forms import config_from_form, load_web_defaults
from .services.web_helpers import (
    build_ask_question as _question_from_form,
    failed_stage as _failed_stage,
    record_action,
    reader_context_from_form as _reader_context_from_form,
    study_type_from_form as _study_type_from_form,
)


@dataclass
class StatusEntry:
    stage: str
    message: str
    timestamp: str
    step_index: int = 1
    total_steps: int = 1
    percent_complete: float = 0.0
    elapsed_total_seconds: float = 0.0
    elapsed_current_stage_seconds: float = 0.0
    status: str = "running"
    details: dict[str, Any] | None = None

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> "StatusEntry":
        total_steps = _int_value(event.get("total_steps"), 1)
        step_index = _int_value(event.get("step_index"), 1)
        return cls(
            stage=str(event.get("stage") or "unknown"),
            message=str(event.get("message") or "Working"),
            timestamp=str(event.get("timestamp") or timestamp()),
            step_index=step_index,
            total_steps=total_steps,
            percent_complete=_float_value(
                event.get("percent_complete"),
                (step_index / max(total_steps, 1)) * 100,
            ),
            elapsed_total_seconds=_float_value(
                event.get("elapsed_total_seconds"),
                0.0,
            ),
            elapsed_current_stage_seconds=_float_value(
                event.get("elapsed_current_stage_seconds"),
                0.0,
            ),
            status=str(event.get("status") or "running"),
            details=event.get("details") if isinstance(event.get("details"), dict) else None,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "stage": self.stage,
            "message": self.message,
            "timestamp": self.timestamp,
            "step_index": self.step_index,
            "total_steps": self.total_steps,
            "percent_complete": self.percent_complete,
            "elapsed_total_seconds": self.elapsed_total_seconds,
            "elapsed_current_stage_seconds": self.elapsed_current_stage_seconds,
            "status": self.status,
        }
        if self.details:
            data["details"] = self.details
        return data


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
    reader_reference: str | None = None
    study_type: str | None = None
    question: str | None = None
    study_context: dict[str, Any] | None = None
    status_code: int = 200
    percent_complete: float = 0.0
    elapsed_total_seconds: float = 0.0
    elapsed_current_stage_seconds: float = 0.0
    status: str = "running"

    def emit(self, event: dict[str, Any]) -> None:
        entry = StatusEntry.from_event(event)
        if self.history and self.history[-1].stage == entry.stage:
            self.message = entry.message
            self.history[-1] = entry
        else:
            if self.history and self.history[-1].status == "running":
                self.history[-1].status = "complete"
            self.history.append(entry)
        self.stage = entry.stage
        self.message = entry.message
        self.percent_complete = entry.percent_complete
        self.elapsed_total_seconds = entry.elapsed_total_seconds
        self.elapsed_current_stage_seconds = entry.elapsed_current_stage_seconds
        self.status = entry.status
        if entry.status == "error":
            self.failed_stage = _failed_stage(entry) or self.stage

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
        self.status = "error"
        self.history.append(
            StatusEntry(
                stage="error",
                message=f"Failed: {error}",
                timestamp=timestamp(),
                step_index=self.history[-1].step_index if self.history else 1,
                total_steps=self.history[-1].total_steps if self.history else 1,
                percent_complete=self.percent_complete,
                elapsed_total_seconds=self.elapsed_total_seconds,
                elapsed_current_stage_seconds=self.elapsed_current_stage_seconds,
                status="error",
                details={"failed_stage": self.failed_stage},
            )
        )

    def complete(self, result: Any) -> None:
        self.result = result
        self.done = True
        self.status = "complete"

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "stage": self.stage,
            "message": self.message,
            "history": [entry.to_dict() for entry in self.history],
            "done": self.done,
            "error": self.error,
            "failed_stage": self.failed_stage,
            "percent_complete": self.percent_complete,
            "elapsed_total_seconds": self.elapsed_total_seconds,
            "elapsed_current_stage_seconds": self.elapsed_current_stage_seconds,
            "status": self.status,
            "reader_reference": self.reader_reference,
            "study_type": self.study_type,
        }


class AskJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, AskJob] = {}
        self._lock = threading.Lock()

    def create(self) -> AskJob:
        job = AskJob(job_id=uuid.uuid4().hex)
        job.emit(
            {
                "stage": "queued",
                "message": "Queued",
                "timestamp": timestamp(),
                "step_index": 1,
                "total_steps": 16,
                "percent_complete": 0,
                "elapsed_total_seconds": 0,
                "elapsed_current_stage_seconds": 0,
                "status": "running",
            }
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> AskJob | None:
        with self._lock:
            return self._jobs.get(job_id)


job_store = AskJobStore()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def run_ask_job(job: AskJob, form: dict[str, Any], agent_class: Any = BHFAgent) -> None:
    try:
        loaded = load_web_defaults()
        job.study_type = _study_type_from_form(form)
        job.study_context = _reader_context_from_form(form)
        question, reader_reference = _question_from_form(form, path=DEFAULT_DB_PATH)
        job.question = question
        job.reader_reference = reader_reference
        if job.study_context and str(form.get("study_action") or "").strip():
            record_action(str(form.get("study_action") or "").strip(), job.study_context, path=DEFAULT_DB_PATH)
        config = config_from_form(form, loaded.config)
        result = agent_class(config).ask(question, status_callback=job.emit)
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
            failed_stage=job.failed_stage or "waiting_for_model_response",
        )
        job.result = result
        return

    job.complete(result)


def run_search_fallback_job(
    job: AskJob,
    form: dict[str, Any],
    agent_class: Any = BHFAgent,
) -> None:
    try:
        query = str(form.get("query") or "").strip()
        if not query:
            raise ConfigError("search query is required")
        job.study_type = "search_fallback"
        job.question = query
        loaded = load_web_defaults()
        config = config_from_form(form, loaded.config)
        prompt = bible_search_fallback_prompt(query)
        result = agent_class(config).ask(prompt, status_callback=job.emit)
        if getattr(result, "errors", None):
            job.fail(
                "; ".join(str(error) for error in result.errors),
                status_code=502,
                failed_stage=job.failed_stage or "waiting_for_model_response",
            )
            job.result = result
            return
        payload = parse_search_fallback_payload(result.answer_text, query)
    except (ConfigError, ProfileError, ValueError, json.JSONDecodeError) as exc:
        job.fail(str(exc), status_code=400)
        return
    except Exception as exc:
        job.fail(f"Unexpected agent error: {exc}", status_code=500)
        return

    job.complete(payload)


def bible_search_fallback_prompt(query: str) -> str:
    return "\n".join(
        [
            "Using BHF, identify likely Bible passages for the following search query.",
            f"Query: {query}",
            "",
            "Return a JSON object with a results array.",
            "Each result should include book, chapter, optional verse_start, optional verse_end, reason, and confidence.",
            "Use only likely passages and keep the response concise.",
            "Do not include markdown fences or extra commentary.",
        ]
    )


def parse_search_fallback_payload(answer_text: str, query: str) -> dict[str, Any]:
    def _format_reference(item: dict[str, Any]) -> str:
        reference = f"{item['book']} {item['chapter']}"
        verse_start = item.get("verse_start")
        verse_end = item.get("verse_end")
        if verse_start not in (None, ""):
            suffix = str(verse_start)
            if verse_end not in (None, "") and str(verse_end) != str(verse_start):
                suffix = f"{suffix}-{verse_end}"
            reference = f"{reference}:{suffix}"
        return reference

    raw = answer_text.strip()
    if not raw:
        return {
            "source": "ai_fallback",
            "query": query,
            "results": [],
            "message": "BHF could not identify likely passage candidates.",
        }
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "source": "ai_fallback",
            "query": query,
            "results": [],
            "message": "BHF returned an unreadable fallback response.",
        }

    results: list[dict[str, Any]] = []
    if isinstance(parsed, dict):
        candidate_results = parsed.get("results")
        if isinstance(candidate_results, list):
            for item in candidate_results:
                if not isinstance(item, dict):
                    continue
                book = str(item.get("book") or "").strip()
                chapter_value = item.get("chapter")
                if not book or chapter_value in (None, ""):
                    continue
                try:
                    chapter = int(chapter_value)
                except (TypeError, ValueError):
                    continue
                normalized = {
                    "book": book,
                    "chapter": chapter,
                    "reference": _format_reference({"book": book, "chapter": chapter, **item}),
                    "reason": str(item.get("reason") or "Likely topical connection."),
                    "confidence": str(item.get("confidence") or ""),
                }
                verse_start = item.get("verse_start")
                verse_end = item.get("verse_end")
                if verse_start not in (None, ""):
                    try:
                        normalized["verse_start"] = int(verse_start)
                    except (TypeError, ValueError):
                        pass
                if verse_end not in (None, ""):
                    try:
                        normalized["verse_end"] = int(verse_end)
                    except (TypeError, ValueError):
                        pass
                results.append(normalized)

    return {
        "source": "ai_fallback",
        "query": query,
        "results": results,
        "message": str(parsed.get("message") or "BHF identified likely passage candidates.") if isinstance(parsed, dict) else "BHF identified likely passage candidates.",
    }
