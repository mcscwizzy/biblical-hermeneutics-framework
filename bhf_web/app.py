"""FastAPI app for the local BHF Agent web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bhf_agent.bible import (
    BibleError,
    list_books,
    search_bible_text,
    resolve_chapter,
)
from bhf_agent.runner import BHFAgent
from bhf_agent.study_db import (
    DEFAULT_DB_PATH,
    StudyDataError,
    get_source,
    list_sources,
)

from .forms import (
    ANSWER_MODES,
    form_values_from_config,
    load_web_defaults,
)
from .routes.ask import register_ask_routes
from .routes.curation import register_curation_routes
from .routes.maps import register_map_routes
from .routes.study import register_study_routes
from .jobs import (
    job_store,
    run_ask_job as _run_ask_job,
    run_search_fallback_job as _run_search_fallback_job,
)
from .services.web_helpers import available_profiles as _available_profiles


PACKAGE_DIR = Path(__file__).resolve().parent
STUDY_DB_PATH = DEFAULT_DB_PATH
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


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

    register_curation_routes(web_app, study_db_path=str(STUDY_DB_PATH), templates=templates)
    register_map_routes(web_app, study_db_path=str(STUDY_DB_PATH))
    register_study_routes(
        web_app,
        study_db_path=str(STUDY_DB_PATH),
        templates=templates,
        job_store=job_store,
    )
    register_ask_routes(
        web_app,
        templates=templates,
        job_store=job_store,
        agent_factory=lambda: BHFAgent,
        ask_job_runner=_run_ask_job,
        search_fallback_job_runner=_run_search_fallback_job,
    )

    return web_app


app = create_app()
