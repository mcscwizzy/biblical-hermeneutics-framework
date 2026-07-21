"""FastAPI app for the local BHF Agent web UI."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bhf_agent.bible import (
    BibleError,
    list_books,
    list_translation_books,
    save_imported_xml_translation,
    search_bible_text,
    resolve_translation_chapter,
)
from bhf_agent.translation_catalog import (
    catalog_by_id,
    import_translation,
    translation_selector_sections,
)
from bhf_agent.translation_installer import (
    TranslationInstallError,
    download_translation,
    get_translation_installation,
    list_installed_translations,
    remove_translation,
)
from bhf_agent.translation_settings import (
    get_default_reader_translation,
    save_reader_settings,
    set_default_reader_translation,
)
from bhf_agent.runner import BHFAgent
from bhf_agent.study_db import (
    StudyDataError,
    get_source,
    list_sources,
)

from .forms import (
    ADAPTERS,
    ANSWER_MODES,
    RUNTIME_PROFILE_MODES,
    form_values_from_config,
    load_web_defaults,
)
from . import settings
from .routes.ask import register_ask_routes
from .routes.canonical import register_canonical_routes
from .routes.canonical import register_canonical_editor_routes
from .routes.curation import register_curation_routes
from .routes.debug import register_debug_routes
from .routes.maps import register_map_routes
from .routes.study import register_study_routes
from .jobs import (
    AskJob,
    job_store,
    run_ask_job as _run_ask_job,
    run_search_fallback_job as _run_search_fallback_job,
)
from .runtime import load_runtime_config
from .services.web_helpers import available_profiles as _available_profiles


PACKAGE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
STUDY_DB_PATH = settings.STUDY_DB_PATH


def create_app() -> FastAPI:
    runtime_config = load_runtime_config()
    web_app = FastAPI(title="BHF Bible Reader")
    web_app.mount(
        "/static",
        StaticFiles(directory=str(PACKAGE_DIR / "static")),
        name="static",
    )
    frontend_dir = PACKAGE_DIR.parent / "frontend"
    if frontend_dir.exists():
        web_app.mount(
            "/frontend",
            StaticFiles(directory=str(frontend_dir)),
            name="frontend",
        )

    def shared_context(extra: dict[str, object] | None = None) -> dict[str, object]:
        context: dict[str, object] = {
            "runtime_config": runtime_config,
        }
        if extra:
            context.update(extra)
        return context

    @web_app.get("/manifest.webmanifest", include_in_schema=False)
    async def manifest() -> Response:
        manifest_data = {
            "name": runtime_config["appName"],
            "short_name": runtime_config["shortName"],
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": runtime_config["backgroundColor"],
            "theme_color": runtime_config["themeColor"],
            "icons": [
                {
                    "src": "/static/icons/icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                },
                {
                    "src": "/static/icons/maskable.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable any",
                },
            ],
        }
        return Response(
            content=json.dumps(manifest_data, separators=(",", ":")),
            media_type="application/manifest+json",
        )

    @web_app.get("/sw.js", include_in_schema=False)
    async def service_worker() -> Response:
        return Response(
            content=(PACKAGE_DIR / "static" / "sw.js").read_text(encoding="utf-8"),
            media_type="application/javascript",
        )

    @web_app.get("/api/health", response_class=JSONResponse)
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "bhf-web"}

    @web_app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(content=b"", media_type="image/x-icon")

    @web_app.get("/offline", response_class=HTMLResponse)
    async def offline(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "offline.html",
            shared_context(),
        )

    @web_app.get("/api/llm/health", response_class=JSONResponse)
    async def llm_health() -> JSONResponse:
        loaded = load_web_defaults()
        try:
            agent = BHFAgent(loaded.config)
            report = agent.adapter.health_check(loaded.config.model)
        except Exception as exc:  # pragma: no cover - defensive route
            return JSONResponse(
                {
                    "ok": False,
                    "provider": loaded.config.adapter,
                    "model": loaded.config.model,
                    "base_url": loaded.config.base_url,
                    "error": str(exc),
                },
                status_code=503,
            )
        status_code = 200 if report.get("ok") else 503
        return JSONResponse(report, status_code=status_code)

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
            shared_context(
                {
                    "form": form_values_from_config(loaded.config),
                    "adapters": ADAPTERS,
                    "profiles": _available_profiles(loaded.config.profile),
                    "runtime_profile_modes": RUNTIME_PROFILE_MODES,
                    "answer_modes": ANSWER_MODES,
                    "config_warning": loaded.warning,
                    "cesium_ion_token": os.environ.get("BHF_CESIUM_ION_TOKEN", "").strip(),
                    "books": list_books(),
                    "default_translation": get_default_reader_translation(),
                    "test_mode": settings.TEST_MODE,
                }
            ),
        )

    @web_app.get("/api/bible/books", response_class=JSONResponse)
    async def bible_books(translation: str | None = None) -> JSONResponse:
        try:
            return JSONResponse({"books": list_translation_books(translation or get_default_reader_translation())})
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    def _installed_translation_ids() -> list[str]:
        return [
            str(entry.get("translation_id") or "").lower()
            for entry in list_installed_translations()
            if bool(entry.get("installed"))
        ]

    def _translation_state_payload() -> dict[str, object]:
        installed_ids = _installed_translation_ids()
        default_translation = get_default_reader_translation()
        sections = translation_selector_sections(
            installed_translation_ids=installed_ids,
            default_translation_id=default_translation,
        )
        translations: list[dict[str, object]] = []
        for entry in sections["catalog"]:
            installed = entry["id"] in installed_ids
            translations.append(
                {
                    "id": entry["id"],
                    "name": entry["name"],
                    "abbreviation": entry["abbreviation"],
                    "language": entry["language"],
                    "language_code": entry["language_code"],
                    "bundled": bool(entry.get("bundled", False)),
                    "install_mode": entry.get("install_mode"),
                    "license_status": entry.get("license_status"),
                    "source": entry.get("source"),
                    "validation": entry.get("validation"),
                    "installed": installed,
                    "can_select": installed,
                    "can_download": bool(entry.get("install_mode") == "direct_download" and not installed),
                    "can_remove": bool(installed and not entry.get("bundled", False)),
                    "can_set_default": installed,
                    "status_label": (
                        "Built in"
                        if entry["id"] == "asv"
                        else "Installed locally"
                        if installed
                        else entry.get("status_label")
                        if entry.get("status_label")
                        else "Download from GitHub"
                        if entry.get("install_mode") == "direct_download"
                        else "License required"
                    ),
                    "third_party": bool(entry.get("third_party", False)),
                    "third_party_notice": entry.get("third_party_notice") or "",
                }
            )
        return {
            "translations": translations,
            "default_translation": default_translation,
            "catalog": sections["catalog"],
            "sections": sections["sections"],
        }

    @web_app.get("/api/translations", response_class=JSONResponse)
    async def translations_index() -> JSONResponse:
        return JSONResponse(_translation_state_payload())

    @web_app.get("/api/translations/catalog", response_class=JSONResponse)
    async def translations_catalog() -> JSONResponse:
        return JSONResponse(_translation_state_payload())

    @web_app.get("/api/translations/{translation_id}", response_class=JSONResponse)
    async def translation_detail(translation_id: str) -> JSONResponse:
        entry = catalog_by_id().get(translation_id.lower())
        if not entry:
            return JSONResponse({"error": "unknown translation"}, status_code=404)
        return JSONResponse(
            {
                "translation": entry,
                "installation": get_translation_installation(translation_id),
            }
        )

    @web_app.post("/api/translations/{translation_id}/download", response_class=JSONResponse)
    async def translation_download(translation_id: str) -> JSONResponse:
        try:
            payload = dict(download_translation(translation_id))
            payload.setdefault("download_enabled", True)
            return JSONResponse(payload)
        except TranslationInstallError as exc:
            entry = catalog_by_id().get(translation_id.lower())
            status_code = 403 if entry and entry.get("install_mode") == "licensed_provider" else 400
            payload = {"error": str(exc), "translation_id": translation_id.lower(), "download_enabled": False}
            if status_code == 403:
                payload.update(
                    {
                        "license_explanation": "This translation is copyrighted and is not currently available for direct download through BHF.",
                        "actions": ["Learn more", "Import legally obtained XML", "Configure licensed provider"],
                    }
                )
            return JSONResponse(payload, status_code=status_code)

    @web_app.post("/api/translations/{translation_id}/install", response_class=JSONResponse)
    async def translation_install(translation_id: str) -> JSONResponse:
        try:
            payload = dict(download_translation(translation_id))
            payload.setdefault("download_enabled", True)
            return JSONResponse(payload)
        except TranslationInstallError as exc:
            entry = catalog_by_id().get(translation_id.lower())
            status_code = 403 if entry and entry.get("install_mode") == "licensed_provider" else 400
            payload = {"error": str(exc), "translation_id": translation_id.lower(), "download_enabled": False}
            if status_code == 403:
                payload.update(
                    {
                        "license_explanation": "This translation is copyrighted and is not currently available for direct download through BHF.",
                        "actions": ["Learn more", "Import legally obtained XML", "Configure licensed provider"],
                    }
                )
            return JSONResponse(payload, status_code=status_code)

    @web_app.post("/api/translations/import/notice", response_class=JSONResponse)
    async def translation_import_notice(request: Request) -> JSONResponse:
        payload = await request.json()
        try:
            return JSONResponse(
                import_translation(
                    str(payload.get("translation_id") or ""),
                    confirmed=bool(payload.get("confirmed", False)),
                    source_filename=str(payload.get("source_filename") or ""),
                )
            )
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.post("/api/translations/{translation_id}/import", response_class=JSONResponse)
    async def translation_import_upload(
        translation_id: str,
        confirmed: bool = Form(False),
        file: UploadFile = File(...),
    ) -> JSONResponse:
        source_filename = file.filename or f"{translation_id}.xml"
        try:
            notice = import_translation(
                translation_id,
                confirmed=confirmed,
                source_filename=source_filename,
            )
            content = await file.read()
            installed = save_imported_xml_translation(
                translation_id,
                content,
                source_filename=source_filename,
                translation_name=catalog_by_id().get(translation_id.lower(), {}).get("name"),
            )
            return JSONResponse(
                {
                    **notice,
                    **installed,
                    "upload_to_bhf": False,
                    "redistribute_to_users": False,
                    "add_to_shared_catalog": False,
                }
            )
        except (BibleError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @web_app.get("/api/settings/reader", response_class=JSONResponse)
    async def reader_settings() -> JSONResponse:
        return JSONResponse({"default_translation": get_default_reader_translation()})

    @web_app.put("/api/settings/reader", response_class=JSONResponse)
    async def update_reader_settings(request: Request) -> JSONResponse:
        payload = await request.json()
        try:
            normalized = set_default_reader_translation(str(payload.get("default_translation") or ""))
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse({"default_translation": normalized})

    @web_app.delete("/api/translations/{translation_id}", response_class=JSONResponse)
    async def translation_delete(translation_id: str) -> JSONResponse:
        current_default = get_default_reader_translation()
        try:
            removed = remove_translation(translation_id)
        except TranslationInstallError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        if removed and current_default == translation_id.lower():
            save_reader_settings({"default_translation": "asv"})
        return JSONResponse({"translation_id": translation_id.lower(), "removed": removed})

    @web_app.get("/api/bible/{book}/{chapter}", response_class=JSONResponse)
    async def bible_chapter(book: str, chapter: int, translation: str | None = None) -> JSONResponse:
        try:
            return JSONResponse(resolve_translation_chapter(translation or get_default_reader_translation(), book, chapter))
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @web_app.get("/api/bible/search", response_class=JSONResponse)
    async def bible_search(q: str, limit: int = 25, translation: str | None = None) -> JSONResponse:
        try:
            return JSONResponse(search_bible_text(q, limit=limit, translation=translation or get_default_reader_translation()))
        except (BibleError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    register_curation_routes(web_app, study_db_path=str(STUDY_DB_PATH), templates=templates)
    register_canonical_routes(web_app)
    register_canonical_editor_routes(web_app, templates=templates)
    register_map_routes(web_app, study_db_path=str(STUDY_DB_PATH))
    register_study_routes(
        web_app,
        study_db_path=str(STUDY_DB_PATH),
        templates=templates,
        job_store=job_store,
    )
    register_debug_routes(web_app)
    register_ask_routes(
        web_app,
        templates=templates,
        job_store=job_store,
        agent_factory=lambda: BHFAgent,
        ask_job_runner=_run_ask_job,
        search_fallback_job_runner=_run_search_fallback_job,
        test_mode=settings.TEST_MODE,
    )

    return web_app


app = create_app()
