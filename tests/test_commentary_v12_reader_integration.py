import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi import FastAPI


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / ".bhf-data/bhf-commentary-v1.2"


class _CompanionContext:
    def __init__(self, evidence_ids=None):
        self.evidence_ids = set(evidence_ids or ())

    def build_evidence_bundle_for_passage(self, *, book, chapter):
        return SimpleNamespace(
            provenance={"sources": []},
            entities_by_id={},
            evidence_by_id={
                evidence_id: SimpleNamespace(
                    id=evidence_id,
                    claim=f"Stored claim for {evidence_id}",
                    category="history",
                    confidence="medium",
                    passage_anchors=[f"{book} {chapter}:1"],
                    relevance_metadata={},
                    source_ids=[],
                    related_entity_ids=[],
                )
                for evidence_id in self.evidence_ids
            },
        )


def _client(monkeypatch, evidence_ids=None):
    import bhf_web.routes.bhf_commentary as route_module
    import bhf_web.services.bhf_commentary as service_module

    monkeypatch.setattr(route_module, "COMMENTARY_RELEASE", "commentary-v1.2")
    monkeypatch.setattr(service_module, "COMMENTARY_RELEASE", "commentary-v1.2")
    app = FastAPI()
    route_module.register_bhf_commentary_routes(
        app,
        storage_dir=RELEASE_ROOT,
        companion_context_service=_CompanionContext(evidence_ids),
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def test_v12_reader_exposes_published_and_typed_unavailable_states_without_fallback(monkeypatch):
    async def request():
        async with _client(monkeypatch) as client:
            return {
                reference: await client.get(f"/api/bhf-commentary/{book}/{chapter}")
                for reference, book, chapter in (
                    ("published", "John", 5),
                    ("source_limited", "Isaiah", 3),
                    ("rejected", "Romans", 3),
                    ("review", "Galatians", 3),
                    ("outside", "Genesis", 1),
                )
            }

    responses = asyncio.run(request())
    assert responses["published"].status_code == 200
    assert responses["published"].json()["available"] is True
    for key, expected in {
        "source_limited": "NOT_RENDERABLE_SOURCE_LIMITED",
        "rejected": "MODEL_OUTPUT_REJECTED",
        "review": "QUALITY_REVIEW_REQUIRED",
        "outside": "OUTSIDE_VALIDATED_V1_2_POPULATION",
    }.items():
        payload = responses[key].json()
        assert responses[key].status_code == 200
        assert payload["available"] is False
        assert payload["release"] == "commentary-v1.2"
        assert payload["release_state"] == expected
        assert "commentary-v1.1" not in str(payload)


def test_v12_evidence_route_returns_only_stored_citations(monkeypatch):
    from bhf_agent.chapter_commentary.storage import load_commentary

    commentary = load_commentary(RELEASE_ROOT, "John", 5)
    assert commentary is not None
    cited_ids = {
        evidence_id
        for section in commentary.sections
        for block in section.blocks
        for evidence_id in block.evidence_ids
    }

    async def request():
        async with _client(monkeypatch, cited_ids) as client:
            return await client.get("/api/bhf-commentary/John/5/evidence")

    async def direct_threadpool(func, **kwargs):
        return func(**kwargs)

    with patch("bhf_web.routes.bhf_commentary.run_in_threadpool", direct_threadpool):
        response = asyncio.run(request())
    payload = response.json()
    assert response.status_code == 200
    assert payload["available"] is True
    returned_ids = {item["id"] for item in payload["evidence_items"]}
    assert returned_ids <= cited_ids
    assert set(payload["unavailable_ids"]) <= cited_ids
