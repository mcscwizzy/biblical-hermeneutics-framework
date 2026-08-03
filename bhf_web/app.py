"""FastAPI app for the local BHF Agent web UI."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bhf_agent.bible import (
    BibleError,
    list_books,
    list_translation_books,
    load_translation_bible,
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
from bhf_agent.lexicon import WordStudyService
from bhf_agent.study_db import (
    StudyDataError,
    get_source,
    list_sources,
)

from .forms import (
    ADAPTERS,
    ADAPTER_LABELS,
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
from .offline import build_offline_manifest, build_offline_pack
from .runtime import load_runtime_config


PACKAGE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
STUDY_DB_PATH = settings.STUDY_DB_PATH


def static_asset(path: str) -> str:
    """Return same-origin static asset paths that are safe behind HTTPS proxies."""
    return f"/static/{path.lstrip('/')}"


templates.env.globals["static_asset"] = static_asset


class ForwardedProtoMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            forwarded_proto = _first_forwarded_header_value(
                scope.get("headers", []),
                b"x-forwarded-proto",
            )
            if forwarded_proto in {"http", "https"}:
                scope = dict(scope)
                scope["scheme"] = forwarded_proto
        await self.app(scope, receive, send)


def _first_forwarded_header_value(headers, name: bytes) -> str:
    for header_name, header_value in headers:
        if header_name.lower() == name:
            return (
                header_value.decode("latin-1")
                .split(",", 1)[0]
                .strip()
                .lower()
            )
    return ""


def create_app() -> FastAPI:
    runtime_config = load_runtime_config()
    web_app = FastAPI(title="BHF Bible Reader")
    web_app.add_middleware(ForwardedProtoMiddleware)
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

    @web_app.get("/api/offline/manifest", response_class=JSONResponse)
    async def offline_manifest() -> JSONResponse:
        return JSONResponse(build_offline_manifest())

    @web_app.get("/api/offline/packs/{pack_id}", response_class=JSONResponse)
    async def offline_pack(pack_id: str) -> JSONResponse:
        try:
            return JSONResponse(build_offline_pack(pack_id, study_db_path=STUDY_DB_PATH))
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @web_app.get("/api/lexicon/diagnostics", response_class=JSONResponse)
    async def lexicon_diagnostics() -> dict[str, object]:
        return WordStudyService().diagnostics()

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
        response = templates.TemplateResponse(
            request,
            "index.html",
            shared_context(
                {
                    "form": form_values_from_config(loaded.config),
                    "adapters": ADAPTERS,
                    "adapter_labels": ADAPTER_LABELS,
                    "config_warning": loaded.warning,
                    "books": list_books(),
                    "default_translation": get_default_reader_translation(),
                    "test_mode": settings.TEST_MODE,
                }
            ),
        )
        if any(request.query_params.get(name) for name in ("code", "state", "error", "error_description")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

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
        default_translation = get_default_reader_translation()
        translations: list[dict[str, object]] = []
        for installation in list_installed_translations():
            if not installation.get("installed"):
                continue
            translation_id = str(installation.get("translation_id") or "").lower()
            if not translation_id:
                continue
            registry = installation.get("registry") or {}
            translation = dict(installation.get("translation") or {})
            name = str(registry.get("name") or translation.get("name") or translation_id.upper())
            abbreviation = str(translation.get("id") or translation_id.upper()).upper()
            bundled = bool(installation.get("bundled", False))
            translations.append(
                {
                    "id": translation_id,
                    "name": name,
                    "abbreviation": abbreviation,
                    "language": translation.get("language") or "en",
                    "language_code": translation.get("language") or "en",
                    "bundled": bundled,
                    "install_mode": "bundled" if bundled else "installed",
                    "license_status": (installation.get("metadata") or {}).get("license_status"),
                    "source": registry.get("source") or translation.get("source") or "",
                    "installed": True,
                    "default": translation_id == default_translation,
                    "can_select": True,
                    "can_download": False,
                    "can_remove": not bundled,
                    "can_set_default": True,
                    "status_label": "Built in" if bundled else "Installed locally",
                    "third_party": bool(installation.get("third_party", False)),
                    "third_party_notice": "",
                    "created_date": registry.get("created_date"),
                }
            )
        return {
            "translations": translations,
            "default_translation": default_translation,
            "catalog": translations,
            "sections": {
                "installed": translations,
            },
        }

    @web_app.get("/api/translations", response_class=JSONResponse)
    async def translations_index() -> JSONResponse:
        return JSONResponse(_translation_state_payload())

    @web_app.get("/api/translations/installed", response_class=JSONResponse)
    async def translations_installed() -> JSONResponse:
        return JSONResponse(_translation_state_payload())

    @web_app.get("/api/translations/catalog", response_class=JSONResponse)
    async def translations_catalog() -> JSONResponse:
        default_translation = get_default_reader_translation()
        payload = translation_selector_sections(
            installed_translation_ids=_installed_translation_ids(),
            default_translation_id=default_translation,
        )
        payload["translations"] = payload["sections"]["installed"]
        payload["default_translation"] = default_translation
        return JSONResponse(payload)

    @web_app.get("/api/translations/{translation_id}", response_class=JSONResponse)
    async def translation_detail(translation_id: str) -> JSONResponse:
        installation = get_translation_installation(translation_id)
        if not installation.get("installed") or not installation.get("bundled"):
            return JSONResponse({"error": "translation is not installed"}, status_code=404)
        return JSONResponse({"translation": installation.get("translation"), "installation": installation})

    @web_app.get("/api/translations/{translation_id}/offline-data", response_class=JSONResponse)
    async def translation_offline_data(translation_id: str) -> JSONResponse:
        installation = get_translation_installation(translation_id)
        if (
            not installation.get("installed")
            or not installation.get("bundled")
            or not installation.get("offline_supported")
        ):
            return JSONResponse({"error": "translation is not installed for offline use"}, status_code=404)
        try:
            return JSONResponse(
                {
                    "translation_id": translation_id.lower(),
                    "dataset": load_translation_bible(translation_id),
                    "installation": installation,
                }
            )
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

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
        if translation_id.lower() not in {"asv", "kjv"}:
            return JSONResponse(
                {"error": "Imported translations are stored on the device and cannot be removed from the server."},
                status_code=400,
            )
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
