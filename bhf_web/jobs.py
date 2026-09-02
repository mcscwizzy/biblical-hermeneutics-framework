"""Job state and worker helpers for the FastAPI app."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping

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
    ask_agent,
    record_action,
    is_transient_translation_lookup,
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
    error_category: str | None = None
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
    created_at: str = field(default_factory=lambda: timestamp())
    stage_started_at: str = field(default_factory=lambda: timestamp())
    deadline_at: str | None = None
    _persist: Callable[["AskJob"], None] | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def emit(self, event: dict[str, Any]) -> None:
        if self.done:
            return
        if self.is_expired():
            self.expire()
            return
        entry = StatusEntry.from_event(event)
        if self.stage != entry.stage:
            self.stage_started_at = entry.timestamp
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
        self._save()

    def fail(
        self,
        error: str,
        status_code: int = 400,
        failed_stage: str | None = None,
        error_category: str | None = None,
    ) -> None:
        if self.done:
            return
        self.failed_stage = failed_stage or self.stage
        self.error = error
        self.error_category = error_category
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
                details={
                    "failed_stage": self.failed_stage,
                    "error_category": self.error_category,
                },
            )
        )
        self._save()

    def complete(self, result: Any) -> None:
        if self.done:
            return
        if self.is_expired():
            self.expire()
            return
        self.result = result
        self.done = True
        self.status = "complete"
        self._save()

    def to_dict(self) -> dict[str, Any]:
        elapsed_total = self.elapsed_total_seconds
        elapsed_stage = self.elapsed_current_stage_seconds
        if not self.done:
            now = datetime.now(timezone.utc)
            elapsed_total = max(elapsed_total, _elapsed_since(self.created_at, now))
            elapsed_stage = max(elapsed_stage, _elapsed_since(self.stage_started_at, now))
        payload = {
            "job_id": self.job_id,
            "stage": self.stage,
            "message": self.message,
            "history": [entry.to_dict() for entry in self.history],
            "done": self.done,
            "error": self.error,
            "error_category": self.error_category,
            "status_code": self.status_code,
            "failed_stage": self.failed_stage,
            "percent_complete": self.percent_complete,
            "elapsed_total_seconds": round(elapsed_total, 1),
            "elapsed_current_stage_seconds": round(elapsed_stage, 1),
            "status": self.status,
            "reader_reference": self.reader_reference,
            "study_type": self.study_type,
        }
        provider_diagnostics = _result_provider_diagnostics(self.result)
        if provider_diagnostics:
            payload["provider_diagnostics"] = provider_diagnostics
        return payload

    def _save(self) -> None:
        if self._persist is not None:
            self._persist(self)

    def is_expired(self) -> bool:
        if not self.deadline_at:
            return False
        return _elapsed_since(self.deadline_at, datetime.now(timezone.utc)) > 0

    def expire(self) -> None:
        """Finish an over-deadline job with the model-timeout contract."""

        self.fail(
            "Model call exceeded its configured deadline (overall)",
            status_code=504,
            failed_stage="waiting_for_model_response",
            error_category="provider_timeout",
        )


PRESENTATION_ERROR_MESSAGES = {
    "provider_unavailable": "AI presentation provider is unavailable.",
    "provider_timeout": "AI presentation generation timed out.",
    "provider_failure": "AI presentation generation failed.",
    "validation_rejected": "AI presentation output was rejected.",
    "capacity_unavailable": "AI presentation capacity is unavailable.",
    "stale_evidence": "Passage evidence changed before presentation generation.",
    "presentation_unavailable": "AI presentation enhancement is unavailable.",
}


@dataclass
class PresentationJob:
    """Small public lifecycle record for optional presentation enhancement."""

    job_id: str
    reference: str
    evidence_hash: str
    status: str = "queued"
    done: bool = False
    result: dict[str, Any] | None = None
    error_category: str | None = None
    created_at: str = field(default_factory=lambda: timestamp())
    updated_at: str = field(default_factory=lambda: timestamp())
    deadline_at: str | None = None
    _persist: Callable[["PresentationJob"], None] | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def start(self) -> None:
        if self.done:
            return
        if self.is_expired():
            self.expire()
            return
        self.status = "running"
        self.updated_at = timestamp()
        self._save()

    def succeed(self, result: Mapping[str, Any]) -> None:
        if self.done:
            return
        if self.is_expired():
            self.expire()
            return
        self.result = _sanitized_presentation_result(result)
        self.status = "succeeded"
        self.done = True
        self.updated_at = timestamp()
        self._save()

    def fail(
        self,
        error_category: str,
        *,
        result: Mapping[str, Any] | None = None,
    ) -> None:
        if self.done:
            return
        category = (
            error_category
            if error_category in PRESENTATION_ERROR_MESSAGES
            else "presentation_unavailable"
        )
        self.error_category = category
        self.result = _sanitized_presentation_result(result) if result is not None else None
        self.status = "failed"
        self.done = True
        self.updated_at = timestamp()
        self._save()

    def expire(self) -> None:
        if self.done:
            return
        self.error_category = "provider_timeout"
        self.status = "expired"
        self.done = True
        self.updated_at = timestamp()
        self._save()

    def is_expired(self) -> bool:
        if not self.deadline_at:
            return False
        return _elapsed_since(self.deadline_at, datetime.now(timezone.utc)) > 0

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "job_id": self.job_id,
            "status": self.status,
            "done": self.done,
            "reference": self.reference,
            "evidence_hash": self.evidence_hash,
        }
        if self.error_category:
            payload["error_category"] = self.error_category
            payload["message"] = PRESENTATION_ERROR_MESSAGES[self.error_category]
        if self.result is not None:
            payload["result"] = self.result
        return payload

    def _save(self) -> None:
        if self._persist is not None:
            self._persist(self)


@dataclass
class StoredResult:
    """JSON-safe result facade used when a job is loaded in another process."""

    answer_text: str = ""
    reference_context: Any = None
    genre_context: Any = None
    question_context: Any = None
    profile_used: str = ""
    validation_result: Any = None
    model_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    fatal_errors: list[str] = field(default_factory=list)
    error_category: str | None = None
    failed_stage: str | None = None
    repair_applied: bool = False
    repair_attempted: bool = False
    repair_reason: str | None = None
    original_validation_result: Any = None
    repaired_validation_result: Any = None

    def public_response(self) -> dict[str, str]:
        return {"answer": self.answer_text}


class AskJobStore:
    """Process-safe SQLite store for Ask and presentation job polling.

    SQLite is suitable for the public beta's single Railway instance. A
    multi-replica deployment will require an external shared job store.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else settings.JOB_DB_PATH
        self._lock = threading.Lock()
        self._initialize()

    def create(self, *, deadline_seconds: float | None = None) -> AskJob:
        now = datetime.now(timezone.utc)
        deadline_at = None
        if deadline_seconds is not None:
            deadline_at = (
                now + timedelta(seconds=max(1.0, deadline_seconds))
            ).isoformat().replace("+00:00", "Z")
        job = AskJob(
            job_id=uuid.uuid4().hex,
            created_at=now.isoformat().replace("+00:00", "Z"),
            stage_started_at=now.isoformat().replace("+00:00", "Z"),
            deadline_at=deadline_at,
        )
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
        job._persist = self._save
        self._prune()
        self._save(job)
        return job

    def create_presentation(
        self,
        *,
        reference: str,
        evidence_hash: str,
        deadline_seconds: float,
    ) -> PresentationJob:
        """Create presentation state without serializing execution inputs."""

        now = datetime.now(timezone.utc)
        deadline_at = (
            now + timedelta(seconds=max(1.0, deadline_seconds))
        ).isoformat().replace("+00:00", "Z")
        job = PresentationJob(
            job_id=uuid.uuid4().hex,
            reference=reference,
            evidence_hash=evidence_hash,
            created_at=now.isoformat().replace("+00:00", "Z"),
            updated_at=now.isoformat().replace("+00:00", "Z"),
            deadline_at=deadline_at,
        )
        job._persist = self._save_presentation
        self._prune()
        self._save_presentation(job)
        return job

    def get(self, job_id: str) -> AskJob | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT payload FROM ask_jobs WHERE job_id = ?",
                    (job_id,),
                ).fetchone()
        if row is None:
            return None
        job = _job_from_payload(json.loads(str(row[0])))
        job._persist = self._save
        if job.is_expired() and not job.done:
            job.expire()
        return job

    def get_presentation(self, job_id: str) -> PresentationJob | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT payload FROM presentation_jobs WHERE job_id = ?",
                    (job_id,),
                ).fetchone()
        if row is None:
            return None
        job = _presentation_job_from_payload(json.loads(str(row[0])))
        job._persist = self._save_presentation
        if job.is_expired() and not job.done:
            job.expire()
        return job

    def _initialize(self) -> None:
        directory = self.path.parent
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RuntimeError(
                f"BHF job database directory could not be created: {directory}"
            ) from exc
        if not directory.is_dir() or not os.access(directory, os.W_OK):
            raise RuntimeError(
                f"BHF job database directory is not writable: {directory}"
            )

        try:
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ask_jobs (
                        job_id TEXT PRIMARY KEY,
                        payload TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS presentation_jobs (
                        job_id TEXT PRIMARY KEY,
                        payload TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                ask_schema = connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' AND name = 'ask_jobs'"
                ).fetchone()
                presentation_schema = connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' AND name = 'presentation_jobs'"
                ).fetchone()
                if ask_schema is None or presentation_schema is None:
                    raise RuntimeError("expected job schemas were not initialized")
        except (OSError, sqlite3.Error, RuntimeError) as exc:
            raise RuntimeError(
                f"BHF job database could not be opened or initialized: {self.path}"
            ) from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _save(self, job: AskJob) -> None:
        payload = json.dumps(_job_payload(job), ensure_ascii=False, default=str)
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO ask_jobs (job_id, payload, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(job_id) DO UPDATE SET
                        payload = excluded.payload,
                        updated_at = excluded.updated_at
                    """,
                    (job.job_id, payload, timestamp()),
                )

    def _save_presentation(self, job: PresentationJob) -> None:
        payload = json.dumps(
            _presentation_job_payload(job),
            ensure_ascii=False,
            default=str,
        )
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO presentation_jobs (job_id, payload, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(job_id) DO UPDATE SET
                        payload = excluded.payload,
                        updated_at = excluded.updated_at
                    """,
                    (job.job_id, payload, timestamp()),
                )

    def _prune(self) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace(
            "+00:00", "Z"
        )
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    "DELETE FROM ask_jobs WHERE updated_at < ?",
                    (cutoff,),
                )
                connection.execute(
                    "DELETE FROM presentation_jobs WHERE updated_at < ?",
                    (cutoff,),
                )


job_store = AskJobStore()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _elapsed_since(value: str, now: datetime) -> float:
    try:
        started = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, (now - started).total_seconds())


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _json_safe(value.to_dict())
    if hasattr(value, "__dict__"):
        return {
            str(key): _json_safe(item)
            for key, item in vars(value).items()
            if not str(key).startswith("_")
        }
    return str(value)


_RESULT_FIELDS = tuple(StoredResult.__dataclass_fields__)


def _result_payload(result: Any) -> dict[str, Any] | None:
    if result is None:
        return None
    if isinstance(result, Mapping):
        return {"kind": "mapping", "value": _json_safe(result)}
    return {
        "kind": "result",
        "value": {
            name: _json_safe(
                getattr(result, name, StoredResult.__dataclass_fields__[name].default)
            )
            for name in _RESULT_FIELDS
            if hasattr(result, name)
        },
    }


def _namespace(value: Any) -> Any:
    if isinstance(value, Mapping):
        return SimpleNamespace(**{str(key): _namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_namespace(item) for item in value]
    return value


def _stored_result(payload: Mapping[str, Any] | None) -> Any:
    if payload is None:
        return None
    if payload.get("kind") == "mapping":
        value = payload.get("value")
        return dict(value) if isinstance(value, Mapping) else {}
    raw_values = payload.get("value") if payload.get("kind") == "result" else payload
    values = dict(raw_values) if isinstance(raw_values, Mapping) else {}
    for name in (
        "reference_context",
        "genre_context",
        "question_context",
        "validation_result",
        "original_validation_result",
        "repaired_validation_result",
    ):
        values[name] = _namespace(values.get(name))
    values["model_metadata"] = dict(values.get("model_metadata") or {})
    return StoredResult(
        **{name: values[name] for name in _RESULT_FIELDS if name in values}
    )


def _job_payload(job: AskJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "stage": job.stage,
        "message": job.message,
        "history": [entry.to_dict() for entry in job.history],
        "done": job.done,
        "error": job.error,
        "error_category": job.error_category,
        "failed_stage": job.failed_stage,
        "result": _result_payload(job.result),
        "reader_reference": job.reader_reference,
        "study_type": job.study_type,
        "question": job.question,
        "study_context": _json_safe(job.study_context),
        "status_code": job.status_code,
        "percent_complete": job.percent_complete,
        "elapsed_total_seconds": job.elapsed_total_seconds,
        "elapsed_current_stage_seconds": job.elapsed_current_stage_seconds,
        "status": job.status,
        "created_at": job.created_at,
        "stage_started_at": job.stage_started_at,
        "deadline_at": job.deadline_at,
    }


def _job_from_payload(payload: Mapping[str, Any]) -> AskJob:
    history = [
        StatusEntry(
            stage=str(entry.get("stage") or "unknown"),
            message=str(entry.get("message") or "Working"),
            timestamp=str(entry.get("timestamp") or timestamp()),
            step_index=_int_value(entry.get("step_index"), 1),
            total_steps=_int_value(entry.get("total_steps"), 1),
            percent_complete=_float_value(entry.get("percent_complete"), 0.0),
            elapsed_total_seconds=_float_value(entry.get("elapsed_total_seconds"), 0.0),
            elapsed_current_stage_seconds=_float_value(entry.get("elapsed_current_stage_seconds"), 0.0),
            status=str(entry.get("status") or "running"),
            details=dict(entry.get("details")) if isinstance(entry.get("details"), Mapping) else None,
        )
        for entry in payload.get("history", [])
        if isinstance(entry, Mapping)
    ]
    return AskJob(
        job_id=str(payload.get("job_id") or ""),
        stage=str(payload.get("stage") or "queued"),
        message=str(payload.get("message") or "Queued"),
        history=history,
        done=bool(payload.get("done")),
        error=str(payload["error"]) if payload.get("error") is not None else None,
        error_category=(
            str(payload["error_category"])
            if payload.get("error_category") is not None
            else None
        ),
        failed_stage=(
            str(payload["failed_stage"])
            if payload.get("failed_stage") is not None
            else None
        ),
        result=_stored_result(payload.get("result")),
        reader_reference=(
            str(payload["reader_reference"])
            if payload.get("reader_reference") is not None
            else None
        ),
        study_type=str(payload["study_type"]) if payload.get("study_type") is not None else None,
        question=str(payload["question"]) if payload.get("question") is not None else None,
        study_context=(
            dict(payload.get("study_context"))
            if isinstance(payload.get("study_context"), Mapping)
            else None
        ),
        status_code=_int_value(payload.get("status_code"), 200),
        percent_complete=_float_value(payload.get("percent_complete"), 0.0),
        elapsed_total_seconds=_float_value(payload.get("elapsed_total_seconds"), 0.0),
        elapsed_current_stage_seconds=_float_value(payload.get("elapsed_current_stage_seconds"), 0.0),
        status=str(payload.get("status") or "running"),
        created_at=str(payload.get("created_at") or timestamp()),
        stage_started_at=str(payload.get("stage_started_at") or timestamp()),
        deadline_at=(
            str(payload["deadline_at"])
            if payload.get("deadline_at") is not None
            else None
        ),
    )


def _presentation_job_payload(job: PresentationJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "reference": job.reference,
        "evidence_hash": job.evidence_hash,
        "status": job.status,
        "done": job.done,
        "result": _sanitized_presentation_result(job.result),
        "error_category": job.error_category,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "deadline_at": job.deadline_at,
    }


def _presentation_job_from_payload(payload: Mapping[str, Any]) -> PresentationJob:
    result = payload.get("result")
    return PresentationJob(
        job_id=str(payload.get("job_id") or ""),
        reference=str(payload.get("reference") or ""),
        evidence_hash=str(payload.get("evidence_hash") or ""),
        status=str(payload.get("status") or "queued"),
        done=bool(payload.get("done")),
        result=(
            _sanitized_presentation_result(result)
            if isinstance(result, Mapping)
            else None
        ),
        error_category=(
            str(payload["error_category"])
            if payload.get("error_category") in PRESENTATION_ERROR_MESSAGES
            else None
        ),
        created_at=str(payload.get("created_at") or timestamp()),
        updated_at=str(payload.get("updated_at") or timestamp()),
        deadline_at=(
            str(payload["deadline_at"])
            if payload.get("deadline_at") is not None
            else None
        ),
    )


def _sanitized_presentation_result(
    result: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Keep only the already-public Companion presentation response fields."""

    if result is None:
        return None
    allowed = (
        "reference",
        "evidence_bundle",
        "presentation_packet",
        "presentation_evidence",
    )
    return {
        key: _json_safe(result[key])
        for key in allowed
        if key in result
    }


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


def _result_provider_diagnostics(result: Any) -> dict[str, Any]:
    metadata = getattr(result, "model_metadata", None)
    if not isinstance(metadata, Mapping):
        return {}
    diagnostics = metadata.get("provider_diagnostics")
    return dict(diagnostics) if isinstance(diagnostics, Mapping) else {}


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
        result = ask_agent(
            agent_class(config),
            question,
            status_callback=job.emit,
            canonical_fact_packet=fact_packet,
            transient_translation_lookup=is_transient_translation_lookup(form),
        )
    except (ConfigError, ProfileError, ValueError) as exc:
        job.fail(str(exc), status_code=400)
        return
    except Exception as exc:
        job.fail(f"Unexpected agent error: {exc}", status_code=500)
        return

    if result_has_fatal_error(result):
        fatal_errors = getattr(result, "fatal_errors", None)
        errors = fatal_errors or getattr(result, "errors", [])
        metadata = getattr(result, "model_metadata", {}) or {}
        pipeline = metadata.get("pipeline") if isinstance(metadata.get("pipeline"), dict) else {}
        error_category = (
            getattr(result, "error_category", None)
            or metadata.get("error_category")
            or pipeline.get("error_category")
        )
        job.result = result
        job.fail(
            "; ".join(str(error) for error in errors),
            status_code=agent_error_status_code(result),
            error_category=str(error_category) if error_category else None,
            failed_stage=(
                getattr(result, "failed_stage", None)
                or metadata.get("failed_stage")
                or pipeline.get("failed_stage")
                or job.failed_stage
                or "building_final_answer"
            ),
        )
        return

    job.complete(result)


def run_presentation_job(
    job: PresentationJob,
    companion_context_service: Any,
    request_values: Mapping[str, Any],
    provider: Any,
    generation_profile: str | None,
) -> None:
    """Run existing presentation generation with memory-only provider state."""

    from .services.companion_context import StalePresentationEvidenceError

    job.start()
    if job.done:
        return
    try:
        result = companion_context_service.enhance_presentation(
            **dict(request_values),
            provider=provider,
            generation_profile=generation_profile,
        )
    except StalePresentationEvidenceError:
        job.fail("stale_evidence")
        return
    except TimeoutError:
        job.fail("provider_timeout")
        return
    except Exception:  # noqa: BLE001 - provider internals are deliberately not retained
        job.fail("provider_failure")
        return

    packet = result.get("presentation_packet") if isinstance(result, Mapping) else None
    mode = str(packet.get("presentation_mode") or "") if isinstance(packet, Mapping) else ""
    if mode in {"generated", "cached", "bundled"}:
        job.succeed(result)
        return
    job.fail("presentation_unavailable", result=result)


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
