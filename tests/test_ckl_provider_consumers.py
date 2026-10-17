"""Compatibility checks for CKL consumers using the app-scoped provider."""

from __future__ import annotations

import asyncio
import threading
from unittest.mock import patch

from fastapi import FastAPI
import httpx

from bhf_web.offline import build_offline_pack
from bhf_web.routes.canonical import register_canonical_routes


def test_study_pack_uses_the_injected_verified_library() -> None:
    library = object()
    provider_calls: list[object] = []

    def provider() -> object:
        provider_calls.append(library)
        return library

    def serialize(_entry, *, library):
        return {"library": library}

    with patch("bhf_web.offline._build_study_pack", side_effect=serialize):
        payload = build_offline_pack(
            "study",
            study_db_path="unused.sqlite",
            canonical_library_provider=provider,
        )

    assert payload == {"library": library}
    assert provider_calls == [library]


def test_canonical_read_route_uses_the_injected_provider() -> None:
    library = object()
    provider_threads: list[int] = []
    app = FastAPI()

    def provider() -> object:
        provider_threads.append(threading.get_ident())
        return library

    async def resolve_in_test(func):
        # The event-loop responsiveness contract is tested with a deterministic
        # blocking provider in test_narrative_explorer_api.py. Keep this test
        # focused on route/provider wiring; the local AnyIO + ASGI harness can
        # otherwise miss a wakeup for an immediately completing worker call.
        return func()

    register_canonical_routes(app, canonical_library_provider=provider)

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/canonical/entities-for-passage?book=Genesis&chapter=2")

    with (
        patch("bhf_web.routes.canonical._entities_for_passage", return_value=[]),
        patch("bhf_web.routes.canonical.run_in_threadpool", side_effect=resolve_in_test),
    ):
        response = asyncio.run(request())

    assert response.status_code == 200
    assert response.json()["reference"] == "Genesis 2"
    assert provider_threads == [threading.get_ident()]
