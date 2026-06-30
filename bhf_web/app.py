"""FastAPI app for the local BHF Agent web UI."""

from __future__ import annotations

import json
import html
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bhf_agent.bible import (
    BibleError,
    compare_translation_passages,
    build_selected_passage_context,
    geography_for_book,
    list_books,
    search_bible_text,
    resolve_chapter,
    timeline_for_book,
    testament_for_book,
    verse_range_reference,
)
from bhf_agent.config import ConfigError
from bhf_agent.profiles import ProfileError, ProfileLoader
from bhf_agent.runner import BHFAgent
from bhf_agent.study_db import (
    DEFAULT_DB_PATH,
    StudyDataError,
    create_highlight,
    create_note,
    create_map_note,
    create_saved_map_study,
    create_saved_study,
    delete_highlight,
    delete_note,
    delete_saved_map_study,
    delete_saved_study,
    get_saved_study,
    get_saved_map_study,
    get_source,
    list_highlights,
    list_notes,
    list_saved_map_studies,
    list_saved_studies,
    list_sources,
    record_study_action,
    update_note,
)
from bhf_agent.curation import (
    CURATION_COLLECTIONS,
    delete_curation_record,
    export_curation_bundle,
    get_curation_record,
    import_curation_bundle,
    list_curation_collections,
    list_curation_records,
    save_curation_record,
)

from .map_service import (
    get_archaeology_markers,
    get_biblical_place_markers,
    get_historical_layers,
    get_map_routes_for_passage,
    get_manuscript_markers,
    get_political_context_layers,
    get_related_passages_for_place,
    resolve_political_context_for_passage,
    resolve_archaeology_for_passage,
    resolve_manuscripts_for_passage,
    resolve_places_for_passage,
)
from .forms import (
    ANSWER_MODES,
    config_from_form,
    form_values_from_config,
    load_web_defaults,
    validate_question,
)
from .services.web_helpers import (
    available_profiles as _available_profiles,
    build_ask_question as _question_from_form,
    curation_blank_record as _curation_blank_record,
    curation_record_summary as _curation_record_summary,
    curation_template_sections as _curation_template_sections,
    float_value as _float_value,
    format_question_type as _format_question_type,
    format_reference as _format_reference,
    failed_stage as _failed_stage,
    int_value as _int_value,
    join_or_none as _join_or_none,
    job_error_message as _job_error_message,
    map_note_payload_from_request as _map_note_payload_from_request,
    map_study_payload_from_request as _map_study_payload_from_request,
    optional_form_value as _optional_form_value,
    optional_map_context as _optional_map_context,
    record_action as _record_action,
    reader_context_from_form as _reader_context_from_form,
    render_safe_markdown as render_safe_markdown,
    request_payload as _request_payload,
    result_metadata as result_metadata,
    saved_study_payload_from_request as _saved_study_payload_from_request,
    study_type_from_form as _study_type_from_form,
    timestamp as _timestamp,
)


PACKAGE_DIR = Path(__file__).resolve().parent
STUDY_DB_PATH = DEFAULT_DB_PATH
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


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
            timestamp=str(event.get("timestamp") or _timestamp()),
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
                timestamp=_timestamp(),
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
                "timestamp": _timestamp(),
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


def _timestamp() -> str:
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


def _failed_stage(entry: StatusEntry) -> str | None:
    if not isinstance(entry.details, dict):
        return None
    value = entry.details.get("failed_stage")
    return str(value) if value else None


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

    @web_app.get("/sources", response_class=HTMLResponse)
    async def sources_index(request: Request) -> HTMLResponse:
        sources = list_sources(path=STUDY_DB_PATH)
        return templates.TemplateResponse(
            request,
            "sources.html",
            {
                "sources": sources,
            },
        )

    @web_app.get("/sources/{source_id}", response_class=HTMLResponse)
    async def source_detail(request: Request, source_id: str) -> HTMLResponse:
        try:
            source = get_source(source_id, path=STUDY_DB_PATH)
        except StudyDataError as exc:
            return templates.TemplateResponse(
                request,
                "sources.html",
                {
                    "sources": list_sources(path=STUDY_DB_PATH),
                    "error": str(exc),
                },
                status_code=404,
            )
        return templates.TemplateResponse(
            request,
            "source.html",
            {
                "source": source,
            },
        )

    @web_app.get("/api/sources", response_class=JSONResponse)
    async def api_sources() -> JSONResponse:
        return JSONResponse({"sources": list_sources(path=STUDY_DB_PATH)})

    @web_app.get("/api/sources/{source_id}", response_class=JSONResponse)
    async def api_source(source_id: str) -> JSONResponse:
        try:
            return JSONResponse(get_source(source_id, path=STUDY_DB_PATH))
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @web_app.get("/curation", response_class=HTMLResponse)
    async def curation(request: Request, collection: str | None = None) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "curation.html",
            {
                "collections": _curation_template_sections(STUDY_DB_PATH),
                "collection": collection or "",
                "export_json": json.dumps(
                    export_curation_bundle(path=STUDY_DB_PATH),
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                ),
            },
        )

    @web_app.get("/api/curation/export", response_class=JSONResponse)
    async def curation_export() -> JSONResponse:
        return JSONResponse(export_curation_bundle(path=STUDY_DB_PATH))

    @web_app.post("/api/curation/import", response_class=JSONResponse)
    async def curation_import(request: Request) -> JSONResponse:
        try:
            payload = await _request_payload(request)
            if "record_json" in payload:
                raw = str(payload["record_json"])
                payload = json.loads(raw)
            result = import_curation_bundle(payload, path=STUDY_DB_PATH)
            return JSONResponse(result)
        except (json.JSONDecodeError, StudyDataError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.get("/api/curation/{collection}", response_class=JSONResponse)
    async def curation_collection(collection: str) -> JSONResponse:
        try:
            return JSONResponse({"records": list_curation_records(collection, path=STUDY_DB_PATH)})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @web_app.get("/api/curation/{collection}/{record_id}", response_class=JSONResponse)
    async def curation_record(collection: str, record_id: str) -> JSONResponse:
        try:
            return JSONResponse(get_curation_record(collection, record_id, path=STUDY_DB_PATH))
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @web_app.post("/api/curation/{collection}", response_class=JSONResponse)
    async def curation_save(collection: str, request: Request) -> JSONResponse:
        try:
            payload = await _request_payload(request)
            if "record_json" in payload:
                payload = json.loads(str(payload["record_json"]))
            saved = save_curation_record(collection, payload, path=STUDY_DB_PATH)
            return JSONResponse(saved, status_code=201)
        except (json.JSONDecodeError, StudyDataError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.put("/api/curation/{collection}/{record_id}", response_class=JSONResponse)
    async def curation_update(collection: str, record_id: str, request: Request) -> JSONResponse:
        try:
            payload = await _request_payload(request)
            if "record_json" in payload:
                payload = json.loads(str(payload["record_json"]))
            payload["id"] = record_id
            saved = save_curation_record(collection, payload, path=STUDY_DB_PATH)
            return JSONResponse(saved)
        except (json.JSONDecodeError, StudyDataError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.delete("/api/curation/{collection}/{record_id}", response_class=JSONResponse)
    async def curation_delete(collection: str, record_id: str) -> JSONResponse:
        try:
            delete_curation_record(collection, record_id, path=STUDY_DB_PATH)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @web_app.post("/api/curation/{collection}/{record_id}/delete", response_class=JSONResponse)
    async def curation_delete_post(collection: str, record_id: str) -> JSONResponse:
        try:
            delete_curation_record(collection, record_id, path=STUDY_DB_PATH)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

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
                "books": list_books(),
            },
        )

    @web_app.get("/api/bible/books", response_class=JSONResponse)
    async def bible_books() -> JSONResponse:
        return JSONResponse({"books": list_books()})

    @web_app.get("/api/bible/{book}/{chapter}", response_class=JSONResponse)
    async def bible_chapter(book: str, chapter: int) -> JSONResponse:
        try:
            return JSONResponse(resolve_chapter(book, chapter))
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @web_app.get("/api/bible/search", response_class=JSONResponse)
    async def bible_search(q: str, limit: int = 25) -> JSONResponse:
        try:
            return JSONResponse(search_bible_text(q, limit=limit))
        except (BibleError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.post("/api/bible/search/fallback/jobs", response_class=JSONResponse)
    async def create_bible_search_fallback_job(request: Request) -> JSONResponse:
        form = await request.form()
        job = job_store.create()
        form_values = dict(form)
        thread = threading.Thread(
            target=_run_search_fallback_job,
            args=(job, form_values, BHFAgent),
            daemon=True,
        )
        thread.start()
        return JSONResponse(job.to_dict(), status_code=202)

    @web_app.get("/api/bible/search/fallback/status/{job_id}", response_class=JSONResponse)
    async def bible_search_fallback_status(job_id: str) -> JSONResponse:
        job = job_store.get(job_id)
        if job is None:
            return JSONResponse({"error": "job not found"}, status_code=404)
        return JSONResponse(job.to_dict())

    @web_app.get("/api/bible/search/fallback/result/{job_id}", response_class=JSONResponse)
    async def bible_search_fallback_result(job_id: str) -> JSONResponse:
        job = job_store.get(job_id)
        if job is None:
            return JSONResponse({"error": "job not found"}, status_code=404)
        if not job.done:
            return JSONResponse({"error": "search fallback is still running"}, status_code=202)
        if job.error:
            return JSONResponse({"error": _job_error_message(job)}, status_code=job.status_code)
        return JSONResponse(job.result)

    @web_app.get("/api/maps/biblical-places", response_class=JSONResponse)
    async def maps_biblical_places(period: str | None = None) -> JSONResponse:
        return JSONResponse({"markers": get_biblical_place_markers(period=period, path=STUDY_DB_PATH)})

    @web_app.get("/api/maps/archaeology", response_class=JSONResponse)
    async def maps_archaeology(period: str | None = None) -> JSONResponse:
        return JSONResponse({"markers": get_archaeology_markers(period=period, path=STUDY_DB_PATH)})

    @web_app.get("/api/maps/manuscripts", response_class=JSONResponse)
    async def maps_manuscripts(period: str | None = None) -> JSONResponse:
        return JSONResponse({"markers": get_manuscript_markers(period=period, path=STUDY_DB_PATH)})

    @web_app.get("/api/maps/routes", response_class=JSONResponse)
    async def maps_routes(period: str | None = None) -> JSONResponse:
        return JSONResponse({"routes": get_map_routes_for_passage(period=period, path=STUDY_DB_PATH)["routes"]})

    @web_app.get("/api/maps/historical-layers", response_class=JSONResponse)
    async def maps_historical_layers(period: str | None = None) -> JSONResponse:
        return JSONResponse({"layers": get_historical_layers(period=period, path=STUDY_DB_PATH)})

    @web_app.get("/api/maps/political-context", response_class=JSONResponse)
    async def maps_political_context(period: str | None = None) -> JSONResponse:
        return JSONResponse({"layers": get_political_context_layers(period=period, path=STUDY_DB_PATH)})

    @web_app.get("/api/maps/routes-for-passage", response_class=JSONResponse)
    async def maps_routes_for_passage(
        book: str | None = None,
        chapter: int | None = None,
        verse_start: int | None = None,
        verse_end: int | None = None,
        passage_text: str | None = None,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = get_map_routes_for_passage(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                passage_text=passage_text,
                period=period,
                path=STUDY_DB_PATH,
            )
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @web_app.get("/api/maps/places-for-passage", response_class=JSONResponse)
    async def maps_places_for_passage(
        book: str | None = None,
        chapter: int | None = None,
        verse_start: int | None = None,
        verse_end: int | None = None,
        passage_text: str | None = None,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = resolve_places_for_passage(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                passage_text=passage_text,
                period=period,
                path=STUDY_DB_PATH,
            )
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @web_app.get("/api/maps/related-passages-for-place", response_class=JSONResponse)
    async def maps_related_passages_for_place(
        place_id: str,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = get_related_passages_for_place(
                place_id=place_id,
                period=period,
                path=STUDY_DB_PATH,
            )
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @web_app.get("/api/maps/archaeology-for-passage", response_class=JSONResponse)
    async def maps_archaeology_for_passage(
        book: str | None = None,
        chapter: int | None = None,
        verse_start: int | None = None,
        verse_end: int | None = None,
        passage_text: str | None = None,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = resolve_archaeology_for_passage(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                passage_text=passage_text,
                period=period,
                path=STUDY_DB_PATH,
            )
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @web_app.get("/api/maps/manuscripts-for-passage", response_class=JSONResponse)
    async def maps_manuscripts_for_passage(
        book: str | None = None,
        chapter: int | None = None,
        verse_start: int | None = None,
        verse_end: int | None = None,
        passage_text: str | None = None,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = resolve_manuscripts_for_passage(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                passage_text=passage_text,
                period=period,
                path=STUDY_DB_PATH,
            )
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @web_app.get("/api/maps/political-context-for-passage", response_class=JSONResponse)
    async def maps_political_context_for_passage(
        book: str | None = None,
        chapter: int | None = None,
        verse_start: int | None = None,
        verse_end: int | None = None,
        passage_text: str | None = None,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = resolve_political_context_for_passage(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                passage_text=passage_text,
                period=period,
                path=STUDY_DB_PATH,
            )
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @web_app.get("/api/maps/sample-markers", response_class=JSONResponse)
    async def maps_sample_markers() -> JSONResponse:
        return JSONResponse({"markers": get_biblical_place_markers(path=STUDY_DB_PATH)})

    @web_app.get("/api/saved-studies", response_class=JSONResponse)
    async def saved_studies(book: str | None = None, chapter: int | None = None) -> JSONResponse:
        try:
            return JSONResponse(
                {"saved_studies": list_saved_studies(book, chapter, path=STUDY_DB_PATH)}
            )
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.get("/api/map-studies", response_class=JSONResponse)
    async def map_studies(book: str | None = None, chapter: int | None = None) -> JSONResponse:
        try:
            return JSONResponse(
                {"saved_map_studies": list_saved_map_studies(book, chapter, path=STUDY_DB_PATH)}
            )
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.get("/api/map-studies/{study_id}", response_class=JSONResponse)
    async def map_study(study_id: str) -> JSONResponse:
        try:
            return JSONResponse(get_saved_map_study(study_id, path=STUDY_DB_PATH))
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @web_app.post("/api/map-studies", response_class=JSONResponse)
    async def post_map_study(request: Request) -> JSONResponse:
        try:
            payload = await _request_payload(request)
            study = _map_study_payload_from_request(payload)
            saved = create_saved_map_study(study, path=STUDY_DB_PATH)
            _record_action("map_study_saved", saved)
            return JSONResponse(saved, status_code=201)
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.delete("/api/map-studies/{study_id}", response_class=JSONResponse)
    async def remove_map_study(study_id: str) -> JSONResponse:
        try:
            delete_saved_map_study(study_id, path=STUDY_DB_PATH)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @web_app.post("/api/map-notes", response_class=JSONResponse)
    async def post_map_note(request: Request) -> JSONResponse:
        try:
            payload = await _request_payload(request)
            note = _map_note_payload_from_request(payload)
            saved = create_map_note(note, path=STUDY_DB_PATH)
            _record_action("map_note_added", saved)
            return JSONResponse(saved, status_code=201)
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.get("/api/saved-studies/{study_id}", response_class=HTMLResponse)
    async def saved_study(request: Request, study_id: str) -> HTMLResponse:
        try:
            study = get_saved_study(study_id, path=STUDY_DB_PATH)
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

    @web_app.post("/api/saved-studies", response_class=JSONResponse)
    async def post_saved_study(request: Request) -> JSONResponse:
        try:
            payload = await _request_payload(request)
            study = _saved_study_payload_from_request(payload)
            saved = create_saved_study(study, path=STUDY_DB_PATH)
            _record_action("study_saved", saved)
            return JSONResponse(saved, status_code=201)
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.delete("/api/saved-studies/{study_id}", response_class=JSONResponse)
    async def remove_saved_study(study_id: str) -> JSONResponse:
        try:
            delete_saved_study(study_id, path=STUDY_DB_PATH)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @web_app.post("/ask", response_class=HTMLResponse)
    async def ask(request: Request) -> HTMLResponse:
        form = await request.form()
        loaded = load_web_defaults()
        try:
            question, reader_reference = _question_from_form(form)
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

    @web_app.post("/ask/jobs", response_class=JSONResponse)
    async def create_ask_job(request: Request) -> JSONResponse:
        form = await request.form()
        job = job_store.create()
        form_values = dict(form)
        agent_class = BHFAgent
        thread = threading.Thread(
            target=_run_ask_job,
            args=(job, form_values, agent_class),
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

    @web_app.get("/api/notes/{book}/{chapter}", response_class=JSONResponse)
    async def get_notes(book: str, chapter: int) -> JSONResponse:
        try:
            return JSONResponse({"notes": list_notes(book, chapter, path=STUDY_DB_PATH)})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.post("/api/notes", response_class=JSONResponse)
    async def post_note(request: Request) -> JSONResponse:
        try:
            payload = await _request_payload(request)
            note = create_note(payload, path=STUDY_DB_PATH)
            _record_action("note_created", note)
            return JSONResponse(note, status_code=201)
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.put("/api/notes/{note_id}", response_class=JSONResponse)
    async def put_note(request: Request, note_id: str) -> JSONResponse:
        try:
            payload = await _request_payload(request)
            return JSONResponse(update_note(note_id, payload, path=STUDY_DB_PATH))
        except StudyDataError as exc:
            status = 404 if "not found" in str(exc) else 400
            return JSONResponse({"error": str(exc)}, status_code=status)

    @web_app.delete("/api/notes/{note_id}", response_class=JSONResponse)
    async def remove_note(note_id: str) -> JSONResponse:
        try:
            delete_note(note_id, path=STUDY_DB_PATH)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @web_app.get("/api/highlights/{book}/{chapter}", response_class=JSONResponse)
    async def get_highlights(book: str, chapter: int) -> JSONResponse:
        try:
            return JSONResponse(
                {"highlights": list_highlights(book, chapter, path=STUDY_DB_PATH)}
            )
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.post("/api/highlights", response_class=JSONResponse)
    async def post_highlight(request: Request) -> JSONResponse:
        try:
            payload = await _request_payload(request)
            highlight = create_highlight(payload, path=STUDY_DB_PATH)
            _record_action("highlight_created", highlight)
            return JSONResponse(highlight, status_code=201)
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.delete("/api/highlights/{highlight_id}", response_class=JSONResponse)
    async def remove_highlight(highlight_id: str) -> JSONResponse:
        try:
            delete_highlight(highlight_id, path=STUDY_DB_PATH)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    return web_app


def _run_ask_job(job: AskJob, form: dict[str, Any], agent_class: Any = BHFAgent) -> None:
    try:
        loaded = load_web_defaults()
        job.study_type = _study_type_from_form(form)
        job.study_context = _reader_context_from_form(form)
        question, reader_reference = _question_from_form(form, path=STUDY_DB_PATH)
        job.question = question
        job.reader_reference = reader_reference
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


def _run_search_fallback_job(
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
        prompt = _bible_search_fallback_prompt(query)
        result = agent_class(config).ask(prompt, status_callback=job.emit)
        if getattr(result, "errors", None):
            job.fail(
                "; ".join(str(error) for error in result.errors),
                status_code=502,
                failed_stage=job.failed_stage or "waiting_for_model_response",
            )
            job.result = result
            return
        payload = _parse_search_fallback_payload(result.answer_text, query)
    except (ConfigError, ProfileError, ValueError, json.JSONDecodeError) as exc:
        job.fail(str(exc), status_code=400)
        return
    except Exception as exc:
        job.fail(f"Unexpected agent error: {exc}", status_code=500)
        return

    job.complete(payload)


app = create_app()
