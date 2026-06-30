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
        question, reader_reference = _question_from_form(form)
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


def _question_from_form(form: dict[str, Any] | Any) -> tuple[str, str | None]:
    if not _is_reader_submission(form):
        return validate_question(form), None

    ask_mode = str(form.get("ask_mode") or "").strip()
    context = _reader_context_from_form(form)
    if context is None:
        return validate_question(form), None
    study_action = str(form.get("study_action") or "").strip()
    if study_action:
        _record_action(study_action, context)
    if ask_mode == "ancient_context":
        return _ancient_context_question(form, context), str(context["reference"])
    if ask_mode == "literary_context":
        return _literary_context_question(form, context), str(context["reference"])
    if ask_mode == "cross_references":
        return _cross_references_question(form, context), str(context["reference"])
    if ask_mode == "related_ot_themes":
        return _related_ot_themes_question(form, context), str(context["reference"])
    if ask_mode == "fulfillment_nt":
        return _fulfillment_nt_question(form, context), str(context["reference"])
    if ask_mode == "compare_translations":
        return _compare_translations_question(form, context), str(context["reference"])
    if ask_mode == "timeline":
        return _timeline_question(form, context), str(context["reference"])
    if ask_mode == "maps":
        return _maps_question(form, context), str(context["reference"])
    if ask_mode == "word_study":
        return _word_study_question(form, context), str(context["reference"])

    user_question = str(form.get("question") or "").strip()
    if not user_question:
        user_question = f"Explain {context['reference']} using BHF."

    lines = [
        f"Using BHF, explain ASV {context['reference']}.",
        f"User question: {user_question}",
        "",
        f"Selected text (ASV {context['reference']}):",
        context["selected_text"],
    ]
    if context.get("chapter_context"):
        lines.extend(
            [
                "",
                f"Full chapter context (ASV {context['book']} {context['chapter']}):",
                str(context["chapter_context"]),
            ]
        )
    lines.extend(
        [
            "",
            "Method reminder: observe the text before interpreting it, and apply only after observation and interpretation.",
        ]
    )
    return "\n".join(lines), str(context["reference"])


def _bible_search_fallback_prompt(query: str) -> str:
    return "\n".join(
        [
            "Using BHF, suggest likely Bible passages for this topical Bible search.",
            f"Search query: {query}",
            "",
            "Return JSON only. Do not wrap it in markdown fences. Do not add commentary before or after the JSON.",
            'Use this schema: {"results":[{"book":"Romans","chapter":12,"verse_start":1,"verse_end":2,"reason":"...","confidence":"likely"}]}',
            "Rules:",
            "- Return 0 to 8 likely passage candidates.",
            "- Use canonical Protestant book names.",
            "- Include verse_start and verse_end when a verse-level match is likely; omit both when only a chapter-level candidate is appropriate.",
            "- confidence must be one of: strong, likely, possible.",
            "- Keep reason brief and cautious.",
            "- Do not claim exhaustive search coverage.",
        ]
    )


def _parse_search_fallback_payload(answer_text: str, query: str) -> dict[str, Any]:
    raw = _extract_json_block(answer_text)
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("search fallback did not return a JSON object")
    items = parsed.get("results")
    if not isinstance(items, list):
        raise ValueError("search fallback JSON must include a results list")
    results: list[dict[str, Any]] = []
    for item in items[:8]:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_search_fallback_candidate(item)
        if normalized:
            results.append(normalized)
    return {
        "query": query,
        "results": results,
        "message": "BHF suggested likely passages because the local ASV search found no direct matches." if results else "BHF could not identify confident passage candidates for this search.",
        "source": "ai_fallback",
    }


def _extract_json_block(answer_text: str) -> str:
    stripped = str(answer_text or "").strip()
    if stripped.startswith("```"):
        fenced = re.sub(r"^```(?:json)?\s*", "", stripped)
        fenced = re.sub(r"\s*```$", "", fenced)
        return fenced.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]
    return stripped


def _normalize_search_fallback_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
    try:
        book = str(item.get("book") or "").strip()
        chapter = int(item.get("chapter"))
    except (TypeError, ValueError):
        return None
    if not book or chapter <= 0:
        return None
    try:
        canonical_book = build_selected_passage_context(book, chapter)["book"]
    except BibleError:
        return None
    verse_start = item.get("verse_start")
    verse_end = item.get("verse_end")
    normalized_start: int | None = None
    normalized_end: int | None = None
    if verse_start not in (None, ""):
        try:
            normalized_start = int(verse_start)
            normalized_end = int(verse_end) if verse_end not in (None, "") else normalized_start
        except (TypeError, ValueError):
            return None
        if normalized_start <= 0 or normalized_end <= 0 or normalized_end < normalized_start:
            return None
    reference = (
        verse_range_reference(canonical_book, chapter, normalized_start, normalized_end)
        if normalized_start
        else f"{canonical_book} {chapter}"
    )
    confidence = str(item.get("confidence") or "possible").strip().lower()
    if confidence not in {"strong", "likely", "possible"}:
        confidence = "possible"
    return {
        "book": canonical_book,
        "chapter": chapter,
        "verse_start": normalized_start,
        "verse_end": normalized_end,
        "reference": reference,
        "reason": str(item.get("reason") or "").strip(),
        "confidence": confidence,
    }


def _reader_context_from_form(form: dict[str, Any] | Any) -> dict[str, Any] | None:
    if not _is_reader_submission(form):
        return None
    return build_selected_passage_context(
        str(form.get("reader_book") or ""),
        str(form.get("reader_chapter") or ""),
        _optional_form_value(form, "reader_start_verse"),
        _optional_form_value(form, "reader_end_verse"),
        _optional_form_value(form, "reader_selected_text"),
        include_chapter_context=True,
    )


def _study_type_from_form(form: dict[str, Any] | Any) -> str:
    ask_mode = str(form.get("ask_mode") or "").strip()
    if ask_mode:
        return ask_mode
    if _is_reader_submission(form):
        return "question"
    return "general_question"


def _ancient_context_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    testament = testament_for_book(str(context["book"]))
    background = (
        "Ancient Near Eastern context, covenant setting, and Israel's original audience concerns"
        if testament == "Old Testament"
        else "Second Temple Jewish and Greco-Roman context where relevant, including the original audience's concerns"
    )
    lines = [
        f"Using BHF, explain the ancient context of ASV {context['reference']}.",
        f"Testament context: {testament}. Use {background}.",
    ]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(
        [
            "",
            "Focus on the passage's ancient setting, original audience, cultural background, and covenant setting when relevant.",
            "Avoid modern assumptions and anachronistic readings.",
            "Clearly distinguish background that is certain from background that is probable or debated.",
            "",
            f"Selected text (ASV {context['reference']}):",
            context["selected_text"],
        ]
    )
    if context.get("chapter_context"):
        lines.extend(
            [
                "",
                f"Full chapter context (ASV {context['book']} {context['chapter']}):",
                str(context["chapter_context"]),
            ]
        )
    lines.extend(
        [
            "",
            "Use BHF method: observe first, interpret with genre and original audience in view, and reserve application until after interpretation.",
        ]
    )
    return "\n".join(lines)


def _literary_context_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    lines = [
        f"Using BHF, explain the literary context of ASV {context['reference']}.",
    ]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(
        [
            "",
            "Explain how the selected passage functions within the immediate paragraph, chapter, book, genre, and argument or narrative flow.",
            "Emphasize what comes before and after the selected passage.",
            "Avoid isolating the verse from the surrounding passage.",
            "Include genre awareness and explain how genre shapes interpretation.",
            "",
            f"Selected text (ASV {context['reference']}):",
            context["selected_text"],
        ]
    )
    if context.get("chapter_context"):
        lines.extend(
            [
                "",
                f"Full chapter context (ASV {context['book']} {context['chapter']}):",
                str(context["chapter_context"]),
            ]
        )
    lines.extend(
        [
            "",
            "Use BHF method: observe the literary flow before interpreting, and apply only after interpretation.",
        ]
    )
    return "\n".join(lines)


def _cross_references_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    testament = testament_for_book(str(context["book"]))
    lines = [
        f"Using BHF, give cross references for ASV {context['reference']}.",
        f"Testament context: {testament}. Prioritize direct quotations, clear allusions, repeated phrases, canonical themes, and OT/NT connections when relevant.",
    ]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(
        [
            "",
            "Separate strong references from possible references.",
            "Briefly explain why each reference matters.",
            "Do not dump a huge list.",
            "Avoid speculative links and label uncertainty clearly.",
            "",
            f"Selected text (ASV {context['reference']}):",
            context["selected_text"],
        ]
    )
    if context.get("chapter_context"):
        lines.extend(
            [
                "",
                f"Full chapter context (ASV {context['book']} {context['chapter']}):",
                str(context["chapter_context"]),
            ]
        )
    lines.extend(
        [
            "",
            "Use BHF method: observation first, then interpretation, then application only if useful.",
        ]
    )
    return "\n".join(lines)


def _related_ot_themes_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    testament = testament_for_book(str(context["book"]))
    lines = [
        f"Using BHF, identify related Old Testament themes for ASV {context['reference']}.",
        f"Testament context: {testament}. Especially important for New Testament passages, but still note canonical patterns carefully.",
    ]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(
        [
            "",
            "Include themes such as covenant, temple, exile/restoration, creation/new creation, wisdom, kingship, priesthood, sacrifice, Spirit, land, blessing/curse, and other earlier canonical patterns when they are genuinely relevant.",
            "Clearly mark strong versus possible thematic links.",
            "Avoid speculative connections.",
            "",
            f"Selected text (ASV {context['reference']}):",
            context["selected_text"],
        ]
    )
    if context.get("chapter_context"):
        lines.extend(
            [
                "",
                f"Full chapter context (ASV {context['book']} {context['chapter']}):",
                str(context["chapter_context"]),
            ]
        )
    lines.extend(
        [
            "",
            "Use BHF method: observe the text, interpret within genre and audience, and distinguish strong links from possible ones.",
        ]
    )
    return "\n".join(lines)


def _fulfillment_nt_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    testament = testament_for_book(str(context["book"]))
    lines = [
        f"Using BHF, evaluate fulfillment in the NT for ASV {context['reference']}.",
        f"Testament context: {testament}. Do not force a fulfillment reading where the text does not support it.",
    ]
    if user_question:
        lines.append(f"User question: {user_question}")
    if testament == "Old Testament":
        lines.extend(
            [
                "",
                "Assess whether the passage is quoted, echoed, developed, fulfilled, typologically reused, or thematically carried into the New Testament.",
                "Separate direct NT citation from strong allusion, typological pattern, thematic development, and speculative or weak connection.",
                "State clearly when the NT does not make or imply a connection.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "For a New Testament passage, explain how it may fulfill or develop earlier Old Testament themes instead of forcing a direct prophetic fulfillment.",
                "Separate direct OT citation from strong allusion, typological pattern, thematic development, and speculative or weak connection.",
                "State clearly when the passage is not directly tied to a specific Old Testament text.",
            ]
        )
    lines.extend(
        [
            "",
            "Avoid forcing Christological or prophetic readings where unsupported.",
            "Distinguish clear fulfillment from possible thematic resonance.",
            "Briefly explain why each link matters.",
            "",
            f"Selected text (ASV {context['reference']}):",
            context["selected_text"],
        ]
    )
    if context.get("chapter_context"):
        lines.extend(
            [
                "",
                f"Full chapter context (ASV {context['book']} {context['chapter']}):",
                str(context["chapter_context"]),
            ]
        )
    lines.extend(
        [
            "",
            "Use BHF method: observe the text first, interpret in literary and canonical context, and keep uncertainty explicit.",
        ]
    )
    return "\n".join(lines)


def _compare_translations_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    comparison = compare_translation_passages(
        str(context["book"]),
        int(context["chapter"]),
        context.get("start_verse"),
        context.get("end_verse"),
    )
    translation_names = ", ".join(
        f"{item['id']} ({item['name']})" for item in comparison["translations"]
    )
    lines = [
        f"Using BHF, compare the local public-domain translations for ASV {comparison['reference']}.",
        f"Available translations: {translation_names}. Use only the bundled local texts.",
        "Explain wording differences and how they may affect interpretation.",
        "Do not rely on copyrighted Bible APIs.",
        "Do not overstate the significance of minor wording differences.",
        "Separate clear interpretive differences from stylistic variation.",
    ]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(
        [
            "",
            "Comparison data by verse:",
        ]
    )
    for row in comparison["verse_rows"]:
        lines.append(f"Verse {row['verse']}:")
        for translation in comparison["translations"]:
            text = row["texts"].get(translation["id"], "")
            lines.append(f"- {translation['id']}: {text}")
        lines.append("")
    if context.get("chapter_context"):
        lines.extend(
            [
                f"Full chapter context (ASV {context['book']} {context['chapter']}):",
                str(context["chapter_context"]),
                "",
            ]
        )
    lines.extend(
        [
            f"Selected text (ASV {context['reference']}):",
            context["selected_text"],
            "",
            "Use BHF method: observe the wording first, interpret in literary and canonical context, and keep uncertainty explicit.",
        ]
    )
    return "\n".join(lines)


def _timeline_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    guide = timeline_for_book(str(context["book"]))
    testament = testament_for_book(str(context["book"]))
    lines = [
        f"Using BHF, place ASV {context['reference']} on the biblical timeline.",
        f"Testament context: {testament}. Broad period: {guide['period']}.",
    ]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(
        [
            "",
            "Show where the passage fits in biblical history, the major covenant period, and the relation to surrounding biblical events.",
            "Prefer broad historical placement over fake precision.",
            "If exact dating is uncertain, say so plainly.",
            guide["notes"],
            "",
            f"Selected text (ASV {context['reference']}):",
            context["selected_text"],
        ]
    )
    if context.get("chapter_context"):
        lines.extend(
            [
                "",
                f"Full chapter context (ASV {context['book']} {context['chapter']}):",
                str(context["chapter_context"]),
            ]
        )
    lines.extend(
        [
            "",
            "Use BHF method: observe first, interpret in literary and canonical context, and keep chronological claims broad and careful.",
        ]
    )
    return "\n".join(lines)


def _maps_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    user_question = str(form.get("question") or "").strip()
    guide = geography_for_book(str(context["book"]))
    testament = testament_for_book(str(context["book"]))
    map_context = _optional_map_context(form)
    lines = [
        f"Using BHF, give geography notes for ASV {context['reference']}.",
        f"Testament context: {testament}. Broad region: {guide['region']}.",
    ]
    if map_context:
        lines.extend(
            [
                "",
                "Structured map context retrieved from the local map layer:",
                map_context,
            ]
        )
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(
        [
            "",
            "Identify places named or implied in the passage and keep the result text-based for now.",
            "Mention when a place's exact location is debated.",
            "Do not invent locations if uncertain.",
            "Keep this as a geography helper until real map data is added.",
            guide["notes"],
            "",
            f"Selected text (ASV {context['reference']}):",
            context["selected_text"],
        ]
    )
    if context.get("chapter_context"):
        lines.extend(
            [
                "",
                f"Full chapter context (ASV {context['book']} {context['chapter']}):",
                str(context["chapter_context"]),
            ]
        )
    lines.extend(
        [
            "",
            "Use BHF method: observe the passage first, then note geography that is explicit, probable, or uncertain.",
        ]
    )
    return "\n".join(lines)


def _word_study_question(form: dict[str, Any] | Any, context: dict[str, Any]) -> str:
    selected_text = context["selected_text"]
    user_question = str(form.get("question") or "").strip()
    testament = testament_for_book(str(context["book"]))
    source_language = "Hebrew" if testament == "Old Testament" else "Greek"
    lines = [
        f"Using BHF, provide a cautious word study helper for ASV {context['reference']}.",
        f"The selected word or phrase is from the ASV English text: {selected_text}",
    ]
    if user_question:
        lines.append(f"User question: {user_question}")
    lines.extend(
        [
            "",
            f"Testament context: {testament}. Discuss possible {source_language} terms only as possibilities.",
            "The selected word is from the ASV English text.",
            "Do not claim exact Hebrew/Greek alignment unless the app has source-language data.",
            "Do not invent Strong's numbers.",
            "Offer likely Hebrew or Greek terms only as possibilities, with uncertainty.",
            "Recommend checking an actual lexicon/interlinear for confirmation.",
            "Explain semantic range, usage, and context cautiously.",
            "",
            f"Selected text (ASV {context['reference']}):",
            selected_text,
        ]
    )
    if context.get("chapter_context"):
        lines.extend(
            [
                "",
                f"Full chapter context (ASV {context['book']} {context['chapter']}):",
                str(context["chapter_context"]),
            ]
        )
    lines.extend(
        [
            "",
            "Use BHF method: original audience, literary context, genre awareness, intertextuality when relevant, theological caution, and application only after interpretation.",
        ]
    )
    return "\n".join(lines)


def _is_reader_submission(form: dict[str, Any] | Any) -> bool:
    return bool(str(form.get("reader_book") or "").strip()) and bool(
        str(form.get("reader_chapter") or "").strip()
    )


def _optional_form_value(form: dict[str, Any] | Any, name: str) -> str | None:
    value = str(form.get(name) or "").strip()
    return value or None


def _optional_map_context(form: dict[str, Any] | Any) -> str | None:
    value = str(form.get("map_context") or "").strip()
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    parts: list[str] = []
    for key in (
        "selected_place_name",
        "selected_route_name",
        "selected_layer_name",
        "passage_reference",
        "confidence",
        "modern_location",
        "ancient_region",
        "local_map_summary",
    ):
        item = parsed.get(key)
        if item:
            parts.append(f"{key.replace('_', ' ').title()}: {item}")
    if not parts:
        return None
    return "\n".join(f"- {part}" for part in parts)


def _curation_template_sections(path: str | Path) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for spec in CURATION_COLLECTIONS.values():
        records = list_curation_records(spec.key, path=path)
        sections.append(
            {
                "key": spec.key,
                "title": spec.title,
                "count": len(records),
                "summary_fields": spec.summary_fields,
                "records": [
                    {
                        "id": record.get("id", ""),
                        "summary": _curation_record_summary(record, spec.summary_fields),
                        "source_summary": record.get("source_summary", "Missing source metadata"),
                        "missing_source": "Missing source metadata" in str(record.get("source_summary", "")),
                        "json": json.dumps(
                            record,
                            indent=2,
                            sort_keys=True,
                            ensure_ascii=False,
                        ),
                    }
                    for record in records
                ],
                "new_record_json": json.dumps(
                    _curation_blank_record(spec),
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                ),
            }
        )
    return sections


def _curation_record_summary(record: dict[str, Any], fields: tuple[str, ...]) -> str:
    values = [str(record.get(field) or "").strip() for field in fields]
    values = [value for value in values if value]
    if values:
        return " · ".join(values)
    if record.get("id"):
        return str(record["id"])
    return "Record"


def _curation_blank_record(spec: Any) -> dict[str, Any]:
    blank: dict[str, Any] = {}
    for field in spec.fields:
        if field.name == "id":
            blank[field.name] = ""
        elif field.kind == "json_list":
            blank[field.name] = []
        elif field.kind == "json_object":
            blank[field.name] = {}
        elif field.kind == "int":
            blank[field.name] = 0
        elif field.kind == "float":
            blank[field.name] = None
        else:
            blank[field.name] = ""
    return blank


async def _request_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        if isinstance(payload, dict):
            return payload
        raise StudyDataError("JSON body must be an object")
    form = await request.form()
    return dict(form)


def _record_action(action_type: str, data: dict[str, Any]) -> None:
    try:
        record_study_action(action_type, data, path=STUDY_DB_PATH)
    except StudyDataError:
        return


def _saved_study_payload_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    job_id = str(payload.get("job_id") or "").strip()
    if job_id:
        job = job_store.get(job_id)
        if job is None:
            raise StudyDataError("job not found")
        if not job.done:
            raise StudyDataError("job is not complete")
        if job.error:
            raise StudyDataError("cannot save a failed study")
        if job.result is None:
            raise StudyDataError("job result is not available")
        if not job.study_context:
            raise StudyDataError("study context is not available")
        return {
            "title": payload.get("title"),
            "book": job.study_context["book"],
            "chapter": job.study_context["chapter"],
            "start_verse": job.study_context["start_verse"],
            "end_verse": job.study_context["end_verse"],
            "selected_text": job.study_context["selected_text"],
            "study_type": job.study_type or "question",
            "question": job.question or "",
            "answer": getattr(job.result, "answer_text", ""),
        }

    return {
        "title": payload.get("title"),
        "book": payload.get("book"),
        "chapter": payload.get("chapter"),
        "start_verse": payload.get("start_verse") or payload.get("verse_start"),
        "end_verse": payload.get("end_verse") or payload.get("verse_end"),
        "selected_text": payload.get("selected_text"),
        "study_type": payload.get("study_type") or payload.get("ask_mode"),
        "question": payload.get("question"),
        "answer": payload.get("answer") or payload.get("answer_html"),
    }


def _map_study_payload_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    view_state = payload.get("map_view_state") or {}
    selected_layers = payload.get("selected_layers") or []
    if isinstance(selected_layers, str):
        try:
            selected_layers = json.loads(selected_layers)
        except json.JSONDecodeError:
            selected_layers = [selected_layers]
    if isinstance(view_state, str):
        try:
            view_state = json.loads(view_state)
        except json.JSONDecodeError:
            view_state = {}
    return {
        "book": payload.get("book"),
        "chapter": payload.get("chapter"),
        "start_verse": payload.get("start_verse") or payload.get("verse_start"),
        "end_verse": payload.get("end_verse") or payload.get("verse_end"),
        "passage_reference": payload.get("passage_reference"),
        "selected_place_id": payload.get("selected_place_id"),
        "selected_route_id": payload.get("selected_route_id"),
        "selected_layer_id": payload.get("selected_layer_id"),
        "selected_archaeology_id": payload.get("selected_archaeology_id"),
        "selected_layers": selected_layers,
        "map_view_state": view_state,
        "generated_summary": payload.get("generated_summary"),
        "user_notes": payload.get("user_notes"),
    }


def _map_note_payload_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "book": payload.get("book"),
        "chapter": payload.get("chapter"),
        "start_verse": payload.get("start_verse") or payload.get("verse_start"),
        "end_verse": payload.get("end_verse") or payload.get("verse_end"),
        "passage_reference": payload.get("passage_reference"),
        "place_id": payload.get("place_id"),
        "route_id": payload.get("route_id"),
        "layer_id": payload.get("layer_id"),
        "archaeology_id": payload.get("archaeology_id"),
        "note_body": payload.get("note_body") or payload.get("body"),
    }


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
