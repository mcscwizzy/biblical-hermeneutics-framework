import asyncio
from dataclasses import replace

import pytest

from bhf_agent.chapter_commentary.models import (
    ChapterCommentary,
    CommentaryBlock,
    CommentarySection,
)
from bhf_web.services.bhf_commentary import load_commentary_projection, project_commentary


def commentary(*, availability="AVAILABLE"):
    return ChapterCommentary(
        reference="Genesis 13",
        book="Genesis",
        chapter=13,
        status="validated",
        evidence_availability=availability,
        sections=[
            CommentarySection(
                kind="chapter_overview",
                title="Overview",
                blocks=[
                    CommentaryBlock(
                        id="b1",
                        text="Abram and Lot separate.",
                        verse_refs=["Genesis 13:5-12"],
                        evidence_ids=["ckl-1", "ckl-2"],
                    ),
                    CommentaryBlock(
                        id="b2",
                        text="The land is described from the chapter's viewpoint.",
                        verse_refs=["Genesis 13:5-12", "Genesis 13:18"],
                        evidence_ids=["ckl-2"],
                    ),
                ],
            ),
        ],
    )


def test_projection_exposes_only_the_read_model_and_deduplicates_references():
    result = project_commentary(commentary())

    assert result == {
        "release": "commentary-v1.0",
        "book": "Genesis",
        "chapter": 13,
        "availability": "AVAILABLE",
        "commentary": "Abram and Lot separate.\n\nThe land is described from the chapter's viewpoint.",
        "verse_references": ["Genesis 13:5-12", "Genesis 13:18"],
        "evidence_count": 2,
    }
    assert "status" not in result
    assert "sections" not in result
    assert "generated_metadata" not in result


def test_projection_preserves_missing_legacy_availability():
    assert project_commentary(commentary(availability=None))["availability"] is None


def test_projection_preserves_thin_and_data_gap_availability():
    assert project_commentary(commentary(availability="THIN"))["availability"] == "THIN"
    assert project_commentary(commentary(availability="DATA_GAP"))["availability"] == "DATA_GAP"


def test_missing_artifact_returns_none(tmp_path):
    assert load_commentary_projection(tmp_path, "Genesis", 13) is None


def test_api_projection_returns_minimal_payload_when_fastapi_is_available(tmp_path):
    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")
    from fastapi import FastAPI

    from bhf_agent.chapter_commentary.storage import save_commentary
    from bhf_web.routes.bhf_commentary import register_bhf_commentary_routes

    save_commentary(commentary(), tmp_path)
    app = FastAPI()
    register_bhf_commentary_routes(app, storage_dir=tmp_path)

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/bhf-commentary/Genesis/13")

    response = asyncio.run(request())
    assert response.status_code == 200
    assert response.json() == {"available": True, **project_commentary(commentary())}

    save_commentary(replace(commentary(), evidence_availability=None), tmp_path)
    legacy_response = asyncio.run(request())
    assert legacy_response.json()["availability"] is None


def test_api_missing_artifact_is_a_normal_unavailable_response(tmp_path):
    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")
    from fastapi import FastAPI

    from bhf_web.routes.bhf_commentary import register_bhf_commentary_routes

    app = FastAPI()
    register_bhf_commentary_routes(app, storage_dir=tmp_path)

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/bhf-commentary/Leviticus/2")

    response = asyncio.run(request())
    assert response.json() == {
        "available": False,
        "reason": "bhf_commentary_not_available",
        "release": "commentary-v1.0",
        "book": "Leviticus",
        "chapter": 2,
    }
