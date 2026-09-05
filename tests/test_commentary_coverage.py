import asyncio

import pytest

from bhf_web.services.commentary_coverage import build_commentary_coverage_snapshot


def test_coverage_snapshot_is_read_only_and_preserves_report_sections():
    health = {
        "corpus_counts": {"generated": 2, "total_chapters": 1189, "validated": 2},
        "evidence_availability_distribution": {"AVAILABLE": 1, "DATA_GAP": 1},
        "structure": {"sections": {"average": 1.0}},
        "content_size": {"average": 100},
        "citation_statistics": {"valid_percentage": 100},
    }
    coverage = {
        "scope": "Leviticus 1-5",
        "coverage_totals": {"chapters_analyzed": 5, "data_gaps": 3},
        "book_summaries": {"Leviticus": {"chapters": 5}},
        "chapter_results": [{"book": "Leviticus", "chapter": 2, "status": "DATA_GAP"}],
        "evidence_density": {"average": 0.4},
        "category_distribution": {"religion": 2},
        "expansion_candidates": [{"reference": "Leviticus 2"}],
    }
    result = build_commentary_coverage_snapshot(
        "/tmp/unused-commentary-path",
        scope="Leviticus 1-5",
        health_report=lambda _path: health,
        ckl_report=lambda _scope: coverage,
    )

    assert result["release"] == "commentary-v1.0"
    assert result["scope"] == "Leviticus 1-5"
    assert result["commentary"]["corpus_counts"]["generated"] == 2
    assert result["ckl"]["coverage_totals"]["data_gaps"] == 3
    assert result["ckl"]["expansion_candidates"] == [{"reference": "Leviticus 2"}]


def test_coverage_page_and_api_are_read_only(tmp_path):
    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")
    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates
    from unittest.mock import patch

    from bhf_web.routes.commentary_coverage import register_commentary_coverage_routes

    app = FastAPI()
    templates = Jinja2Templates(directory="bhf_web/templates")
    templates.env.globals["static_asset"] = lambda path: f"/static/{path.lstrip('/')}"
    register_commentary_coverage_routes(app, storage_dir=tmp_path, templates=templates)
    snapshot = {"release": "commentary-v1.0", "scope": "Genesis", "commentary": {}, "ckl": {}}

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            page = await client.get("/internal/commentary-coverage")
            api = await client.get("/api/internal/bhf-commentary/coverage?scope=Genesis")
            return page, api

    with patch("bhf_web.routes.commentary_coverage.build_commentary_coverage_snapshot", return_value=snapshot):
        page, api = asyncio.run(request())

    assert page.status_code == 200
    assert "BHF Commentary Coverage" in page.text
    assert api.status_code == 200
    assert api.json() == snapshot
