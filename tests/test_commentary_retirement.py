from __future__ import annotations

import asyncio
from importlib import import_module

from httpx import ASGITransport, AsyncClient

from bhf_web.app import create_app


def _optional_module(name: str):
    try:
        return import_module(name)
    except ModuleNotFoundError:
        return None


RETIRED_PATHS = (
    "/api/bhf-commentary/diagnostics",
    "/api/bhf-commentary/search?q=Abraham",
    "/api/bhf-commentary/Genesis/1",
    "/api/bhf-commentary/Genesis/1/evidence",
    "/api/internal/bhf-commentary/coverage?scope=Genesis",
    "/internal/commentary-coverage",
)


def test_retired_generated_commentary_and_coverage_paths_return_gone(monkeypatch):
    compiled_commentary_routes = _optional_module("bhf_web.routes.bhf_commentary")
    coverage_routes = _optional_module("bhf_web.routes.commentary_coverage")
    if compiled_commentary_routes is not None:
        monkeypatch.setattr(compiled_commentary_routes, "release_manifest_invalid", lambda *_args: False)
        monkeypatch.setattr(compiled_commentary_routes, "load_commentary", lambda *_args: None)
        monkeypatch.setattr(
            compiled_commentary_routes,
            "search_commentary",
            lambda *_args, **_kwargs: {"release": "commentary-v1.1", "count": 0, "results": []},
        )
    if coverage_routes is not None:
        monkeypatch.setattr(
            coverage_routes,
            "build_commentary_coverage_snapshot",
            lambda *_args, **_kwargs: {"release": "commentary-v1.1", "commentary": {}, "ckl": {}},
        )
    app = create_app()

    async def fetch_all():
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return [await client.get(path) for path in RETIRED_PATHS]

    responses = asyncio.run(fetch_all())

    for path, response in zip(RETIRED_PATHS, responses, strict=True):
        assert response.status_code == 410, path
        assert response.json()["reason"] == "feature_retired"
        assert "message" in response.json()
        assert "commentary" not in response.json()


def test_tyndale_commentary_api_remains_registered():
    app = create_app()

    paths = {route.path for route in app.routes}

    assert "/api/commentary/diagnostics" in paths
    assert "/api/commentary/{book}/{chapter}" in paths
