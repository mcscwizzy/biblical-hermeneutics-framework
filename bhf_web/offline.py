"""Offline pack manifest helpers for the BHF web PWA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bhf_agent.bible import DATA_PATH as ASV_DATA_PATH
from bhf_agent.bible import KJV_DATA_PATH
from bhf_agent.ckl import load_canonical_library
from framework.canonical_library import load_framework_version_fingerprint

from .map_service import (
    get_archaeology_markers,
    get_biblical_place_markers,
    get_historical_layers,
    get_map_catalog,
    get_map_routes,
    get_manuscript_markers,
    get_political_context_layers,
)
from .routes.canonical import _serialize_object_detail
from bhf_agent.study_db import get_source, list_sources


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent


def build_offline_manifest() -> dict[str, Any]:
    """Describe cacheable app data and offline boundaries for the browser."""

    static_root = PACKAGE_DIR / "static"
    ckl_root = REPO_ROOT / "framework" / "canonical_library"
    sources_root = REPO_ROOT / "sources"

    return {
        "schema_version": 1,
        "app": "bhf-bible-reader",
        "version_fingerprint": load_framework_version_fingerprint(),
        "offline_boundary": {
            "available": [
                "app_shell",
                "installed_translations",
                "local_bible_search",
                "canonical_library",
                "maps",
                "notes",
                "highlights",
                "saved_studies",
                "commentary",
            ],
            "device_only": [
                "notes",
                "highlights",
                "saved_studies",
                "imported_translations",
            ],
            "requires_online_or_local_runtime": [
                "ai_ask",
                "llm_health",
                "ai_search_fallback",
                "translation_downloads",
                "licensed_provider_content",
            ],
        },
        "packs": [
            {
                "id": "core",
                "label": "Reader core",
                "required": True,
                "strategy": "precache",
                "size_bytes": _safe_size(static_root) + _safe_file_size(ASV_DATA_PATH) + _safe_file_size(KJV_DATA_PATH),
                "routes": [
                    "/",
                    "/offline",
                    "/manifest.webmanifest",
                    "/api/offline/manifest",
                    "/api/offline/packs/{pack_id}",
                    "/api/translations",
                    "/api/translations/installed",
                    "/api/translations/{translation_id}/offline-data",
                    "/api/bible/books",
                    "/api/commentary/",
                ],
                "assets": [
                    "/static/style.css",
                    "/static/api/http.js",
                    "/static/offline/db.js",
                    "/static/htmx-lite.js",
                    "/static/htmx-study-panels.js",
                    "/static/htmx-search.js",
                    "/static/pwa.js",
                    "/static/icons/icon-192.png",
                    "/static/icons/icon-512.png",
                    "/static/icons/maskable.png",
                    "/static/icons/apple-touch-icon.png",
                    "/static/vendor/leaflet/leaflet.css",
                    "/static/vendor/leaflet/leaflet.js",
                    "/static/vendor/leaflet/leaflet.js.map",
                    "/static/vendor/leaflet/images/layers-2x.png",
                    "/static/vendor/leaflet/images/layers.png",
                    "/static/vendor/leaflet/images/marker-icon-2x.png",
                    "/static/vendor/leaflet/images/marker-icon.png",
                    "/static/vendor/leaflet/images/marker-shadow.png",
                ],
            },
            {
                "id": "study",
                "label": "Canonical study library",
                "required": False,
                "strategy": "on_demand",
                "size_bytes": _safe_size(ckl_root / "objects"),
                "routes": [
                    "/api/canonical/search",
                    "/api/canonical/objects/",
                    "/api/study/actions",
                ],
            },
            {
                "id": "maps",
                "label": "Maps and journeys",
                "required": False,
                "strategy": "on_demand",
                "size_bytes": _safe_size(static_root / "data") + _safe_size(static_root / "maps"),
                "routes": [
                    "/api/maps/catalog",
                    "/api/maps/biblical-places",
                    "/api/maps/archaeology",
                    "/api/maps/manuscripts",
                    "/api/maps/routes",
                    "/api/maps/historical-layers",
                    "/api/maps/political-context",
                    "/api/maps/search",
                    "/api/maps/places-for-passage",
                    "/api/maps/routes-for-passage",
                    "/api/maps/related-passages-for-place",
                    "/api/maps/archaeology-for-passage",
                    "/api/maps/manuscripts-for-passage",
                    "/api/maps/political-context-for-passage",
                ],
            },
            {
                "id": "sources",
                "label": "Source library",
                "required": False,
                "strategy": "installable_pack",
                "size_bytes": _safe_size(sources_root),
                "routes": [
                    "/sources",
                    "/sources/",
                    "/api/sources",
                    "/api/sources/",
                ],
            },
        ],
        "client_stores": [
            "apiResponses",
            "translations",
            "chapters",
            "searches",
            "notes",
            "highlights",
            "savedStudies",
            "mutationQueue",
            "metadata",
            "commentary",
        ],
        "offline_mutations": [
            "POST /api/map-notes",
            "PUT /api/settings/reader",
        ],
    }


def build_offline_pack(pack_id: str, *, study_db_path: str | Path) -> dict[str, Any]:
    """Return installable offline pack data for a known pack id."""

    normalized = str(pack_id or "").strip().lower()
    manifest = build_offline_manifest()
    pack_entry = next((pack for pack in manifest["packs"] if pack["id"] == normalized), None)
    if pack_entry is None:
        raise ValueError(f"unknown offline pack: {pack_id}")

    if normalized == "study":
        return _build_study_pack(pack_entry)
    if normalized == "maps":
        return _build_maps_pack(pack_entry, study_db_path=study_db_path)
    if normalized == "core":
        return {
            "schema_version": 1,
            "pack_id": "core",
            "label": pack_entry["label"],
            "strategy": pack_entry["strategy"],
            "routes": [],
            "assets": pack_entry.get("assets", []),
            "responses": [],
        }
    if normalized == "sources":
        return _build_sources_pack(pack_entry, study_db_path=study_db_path)
    raise ValueError(f"unknown offline pack: {pack_id}")


def _build_study_pack(pack_entry: dict[str, Any]) -> dict[str, Any]:
    library = load_canonical_library()
    objects = [
        _serialize_object_detail(obj, library, browse=True)
        for obj in sorted(
            library.objects_by_id.values(),
            key=lambda item: (-int(item.importance), item.type, item.title, item.id),
        )
    ]
    browse_results = objects[:25]
    return {
        "schema_version": 1,
        "pack_id": "study",
        "label": pack_entry["label"],
        "strategy": pack_entry["strategy"],
        "version_fingerprint": load_framework_version_fingerprint(),
        "objects": objects,
        "responses": [
            {
                "url": "/api/canonical/search?",
                "payload": {
                    "query": "",
                    "limit": 12,
                    "filters": {
                        "type": "all",
                        "review_status": "all",
                        "content_status": "all",
                        "include_placeholders": True,
                    },
                    "metadata": {
                        "retrieval_method": "offline_pack",
                        "topic_count": len(browse_results),
                        "query": "",
                        "max_results": 12,
                    },
                    "results": browse_results[:12],
                },
            }
        ],
    }


def _build_maps_pack(pack_entry: dict[str, Any], *, study_db_path: str | Path) -> dict[str, Any]:
    path = str(study_db_path)
    responses = [
        {"url": "/api/maps/catalog", "payload": get_map_catalog(path=path)},
        {"url": "/api/maps/biblical-places", "payload": {"markers": get_biblical_place_markers(path=path)}},
        {"url": "/api/maps/archaeology", "payload": {"markers": get_archaeology_markers(path=path)}},
        {"url": "/api/maps/manuscripts", "payload": {"markers": get_manuscript_markers(path=path)}},
        {"url": "/api/maps/routes", "payload": {"routes": get_map_routes(path=path)}},
        {"url": "/api/maps/historical-layers", "payload": {"layers": get_historical_layers(path=path)}},
        {"url": "/api/maps/political-context", "payload": {"layers": get_political_context_layers(path=path)}},
    ]
    return {
        "schema_version": 1,
        "pack_id": "maps",
        "label": pack_entry["label"],
        "strategy": pack_entry["strategy"],
        "version_fingerprint": load_framework_version_fingerprint(),
        "responses": responses,
    }


def _build_sources_pack(pack_entry: dict[str, Any], *, study_db_path: str | Path) -> dict[str, Any]:
    path = str(study_db_path)
    sources = list_sources(path=path)
    details = []
    responses = [{"url": "/api/sources", "payload": {"sources": sources}}]
    for source in sources:
        source_id = str(source.get("id") or "").strip()
        if not source_id:
            continue
        detail = get_source(source_id, path=path)
        details.append(detail)
        responses.append({"url": f"/api/sources/{source_id}", "payload": detail})
    return {
        "schema_version": 1,
        "pack_id": "sources",
        "label": pack_entry["label"],
        "strategy": pack_entry["strategy"],
        "version_fingerprint": load_framework_version_fingerprint(),
        "sources": sources,
        "details": details,
        "responses": responses,
        "deferred": True,
    }


def _safe_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return _safe_file_size(path)
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += _safe_file_size(item)
    return total


def _safe_file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0
