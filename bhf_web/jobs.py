"""Job state and worker helpers for the FastAPI app."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from bhf_agent.config import ConfigError
from bhf_agent.profiles import ProfileError
from bhf_agent.runner import BHFAgent

from . import settings
from .forms import config_from_form, load_web_defaults
from .services.bible_search_fallback import build_bible_search_fallback_payload
from .services.web_helpers import (
    build_ask_question as _question_from_form,
    agent_error_status_code,
    result_has_fatal_error,
    deterministic_fact_packet_from_form,
    failed_stage as _failed_stage,
    record_action,
    normalize_study_action,
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


def run_ask_job(
    job: AskJob,
    form: dict[str, Any],
    agent_class: Any = BHFAgent,
    transient_api_key: str | None = None,
) -> None:
    try:
        loaded = load_web_defaults()
        job.study_type = _study_type_from_form(form)
        job.study_context = _reader_context_from_form(form)
        question, reader_reference = _question_from_form(form, path=settings.STUDY_DB_PATH)
        fact_packet = deterministic_fact_packet_from_form(form)
        job.question = question
        job.reader_reference = reader_reference
        if job.study_context and normalize_study_action(form.get("study_action")):
            record_action(normalize_study_action(form.get("study_action")), job.study_context, path=settings.STUDY_DB_PATH)
        if settings.TEST_MODE:
            job.emit(
                {
                    "stage": "test_mode",
                    "message": "Deterministic test answer ready",
                    "timestamp": timestamp(),
                    "step_index": 16,
                    "total_steps": 16,
                    "percent_complete": 100,
                    "elapsed_total_seconds": 0.1,
                    "elapsed_current_stage_seconds": 0.1,
                    "status": "running",
                }
            )
            job.complete(_fake_result(job.question, job.reader_reference))
            return
        config = config_from_form(
            form,
            loaded.config,
            transient_api_key=transient_api_key,
        )
        result = agent_class(config).ask(
            question,
            status_callback=job.emit,
            canonical_fact_packet=fact_packet,
        )
    except (ConfigError, ProfileError, ValueError) as exc:
        job.fail(str(exc), status_code=400)
        return
    except Exception as exc:
        job.fail(f"Unexpected agent error: {exc}", status_code=500)
        return

    if result_has_fatal_error(result):
        fatal_errors = getattr(result, "fatal_errors", None)
        errors = fatal_errors if fatal_errors is not None else getattr(result, "errors", [])
        metadata = getattr(result, "model_metadata", {}) or {}
        pipeline = metadata.get("pipeline") if isinstance(metadata.get("pipeline"), dict) else {}
        job.fail(
            "; ".join(str(error) for error in errors),
            status_code=agent_error_status_code(result),
            failed_stage=(
                getattr(result, "failed_stage", None)
                or metadata.get("failed_stage")
                or pipeline.get("failed_stage")
                or job.failed_stage
                or "building_final_answer"
            ),
        )
        job.result = result
        return

    job.complete(result)


def _fake_result(question: str | None, reader_reference: str | None) -> Any:
    reference = reader_reference or "the requested question"
    answer_text = "\n".join(
        [
            "# Test answer",
            f"Question: {question or 'not provided'}",
            f"Reference: {reference}",
            "",
            "This is a deterministic GUI test response.",
        ]
    )
    reference_context = SimpleNamespace(
        is_reference_based=bool(reader_reference),
        book=None,
        chapter=None,
        verse=None,
        testament=None,
        topic=None,
    )
    if reader_reference:
        parts = str(reader_reference).split()
        if len(parts) >= 2:
            reference_context.book = parts[0]
            chapter_part = parts[1].split(":", 1)[0]
            try:
                reference_context.chapter = int(chapter_part)
            except ValueError:
                reference_context.chapter = None
    return SimpleNamespace(
        answer_text=answer_text,
        profile_used="gui-test-mode",
        model_metadata={"answer_mode": "gui-test-mode", "local_knowledge_keys": ["test-mode"]},
        validation_result=SimpleNamespace(warnings=[]),
        reference_context=reference_context,
        genre_context=SimpleNamespace(primary_genre="test"),
        question_context=SimpleNamespace(question_type="test"),
        errors=[],
    )


def run_search_fallback_job(
    job: AskJob,
    form: dict[str, Any],
    agent_class: Any = BHFAgent,
    transient_api_key: str | None = None,
) -> None:
    try:
        query = str(form.get("query") or "").strip()
        if not query:
            raise ConfigError("search query is required")
        job.study_type = "search_fallback"
        job.question = query
        loaded = load_web_defaults()
        config = config_from_form(
            form,
            loaded.config,
            transient_api_key=transient_api_key,
        )
        del agent_class
        job.emit(
            {
                "stage": "searching_canonical_library",
                "message": "Searching the Canonical Knowledge Library for likely passages",
                "timestamp": timestamp(),
                "step_index": 11,
                "total_steps": 16,
                "percent_complete": 75,
                "elapsed_total_seconds": 0.0,
                "elapsed_current_stage_seconds": 0.0,
                "status": "running",
            }
        )
        payload = build_bible_search_fallback_payload(
            query,
            canonical_library=config.canonical_library,
            limit=config.canonical_library.max_results,
        )
        job.emit(
            {
                "stage": "complete",
                "message": "Complete",
                "timestamp": timestamp(),
                "step_index": 16,
                "total_steps": 16,
                "percent_complete": 100,
                "elapsed_total_seconds": 0.0,
                "elapsed_current_stage_seconds": 0.0,
                "status": "complete",
            }
        )
    except (ConfigError, ProfileError, ValueError) as exc:
        job.fail(str(exc), status_code=400)
        return
    except Exception as exc:
        job.fail(f"Unexpected agent error: {exc}", status_code=500)
        return

    job.complete(payload)
