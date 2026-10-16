"""FastAPI integration contract for Narrative Explorer NE-3."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import FastAPI
import httpx
import pytest

from bhf_agent.presentation.narrative_explorer import DomainLookup, validate_projection
from bhf_web.routes.narrative_explorer import register_narrative_explorer_routes
from bhf_web.services.narrative_explorer import NarrativeExplorerService


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CKL_ROOT = PROJECT_ROOT / "framework" / "canonical_library"
PILOTS = (
    ("Genesis", 1),
    ("Genesis", 2),
    ("Genesis", 3),
    ("Genesis", 6),
    ("Deuteronomy", 32),
    ("Psalm", 82),
    ("Exodus", 3),
)


@pytest.fixture(scope="module")
def ckl_library():
    from framework.canonical_library.loader import CanonicalLibrary

    return CanonicalLibrary(root=CKL_ROOT).load()


class _CanonicalLibrary:
    def __init__(self, objects: list[dict[str, Any]] | None = None) -> None:
        self.objects_by_id = {str(item["id"]): item for item in objects or []}
        self.calls: list[tuple[str, int, dict[str, Any]]] = []

    def retrieve_by_scripture_reference(self, reference: str, *, limit: int, **filters: Any):
        self.calls.append((reference, limit, filters))
        return list(self.objects_by_id.values())[:limit]


def _map_record(
    item_id: str,
    name: str,
    reference: str,
    *,
    identification_status: str | None = None,
    identification_confidence: str | None = None,
) -> dict[str, Any]:
    book, scope = reference.split(" ", 1)
    chapter_text, verse_text = scope.split(":", 1)
    start_text, _, end_text = verse_text.partition("-")
    record: dict[str, Any] = {
        "id": item_id,
        "name": name,
        "marker_kind": "place",
        "description": f"Stored map record for {name}.",
        "latitude": 31.0,
        "longitude": 35.0,
        "confidence": "high",
        "source_id": f"map-source-{item_id}",
        "source_name": "BHF map catalog fixture",
        "source_url": "https://example.test/map-source",
        "periods": ["Broad / uncertain period"],
        "related_references": [
            {
                "book": book,
                "chapter": int(chapter_text),
                "verse_start": int(start_text),
                "verse_end": int(end_text or start_text),
                "relationship_type": "contextual",
                "notes": "Stored passage anchor.",
            }
        ],
    }
    if identification_status is not None:
        record["physical_identification_status"] = identification_status
    if identification_confidence is not None:
        record["place_identification_confidence"] = identification_confidence
    return record


def _map_provider(**request: Any) -> DomainLookup:
    book = request["book"]
    chapter = request["chapter"]
    records = []
    if book == "Genesis" and chapter in {2, 3}:
        reference = "Genesis 2:8-14" if chapter == 2 else "Genesis 3:8-24"
        records.append(_map_record("eden", "Garden of Eden", reference))
    if book == "Exodus" and chapter == 3:
        records.extend(
            [
                _map_record(
                    "midian",
                    "Midian",
                    "Exodus 3:1-2",
                    identification_status="established",
                    identification_confidence="high",
                ),
                {
                    **_map_record(
                        "horeb-sinai",
                        "Horeb / Sinai",
                        "Exodus 3:1-6",
                        identification_status="disputed",
                        identification_confidence="disputed",
                    ),
                    "dispute_status": "identification_uncertainty",
                },
            ]
        )
    return DomainLookup(domain="maps", records=records, query_status="complete")


def _empty_archaeology_provider(**_request: Any) -> DomainLookup:
    return DomainLookup(domain="archaeology", records=(), query_status="complete")


class _ASGIClient:
    def __init__(self, app: FastAPI) -> None:
        self.app = app

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        async def request() -> httpx.Response:
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                return await client.get(path, params=params)

        return asyncio.run(request())


def _client(service: NarrativeExplorerService) -> _ASGIClient:
    app = FastAPI()
    register_narrative_explorer_routes(app, service=service)
    return _ASGIClient(app)


def _service(
    library: Any,
    *,
    map_provider=_map_provider,
    archaeology_provider=_empty_archaeology_provider,
) -> NarrativeExplorerService:
    return NarrativeExplorerService(
        study_db_path=PROJECT_ROOT / ".bhf-data" / "study.sqlite",
        canonical_library_provider=lambda: library,
        maps_lookup_provider=map_provider,
        archaeology_lookup_provider=archaeology_provider,
    )


def _coverage(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["domain"]: entry for entry in payload["coverage"]}


def _item(payload: dict[str, Any], item_id: str) -> dict[str, Any]:
    return next(item for item in payload["items"] if item["id"] == item_id)


def test_versioned_route_returns_valid_deterministic_chapter_and_range_projections(ckl_library):
    client = _client(_service(ckl_library))

    for book, chapter in PILOTS:
        chapter_response = client.get(f"/api/narrative-explorer/v1/passages/{book}/{chapter}")
        assert chapter_response.status_code == 200
        chapter_payload = chapter_response.json()
        validate_projection(chapter_payload)
        assert chapter_payload["schema_version"] == "1.0"
        assert chapter_payload["passage"]["scope"] == "chapter"
        assert client.get(f"/api/narrative-explorer/v1/passages/{book}/{chapter}").json() == chapter_payload

        range_response = client.get(
            f"/api/narrative-explorer/v1/passages/{book}/{chapter}",
            params={"verse_start": 1, "verse_end": 2},
        )
        assert range_response.status_code == 200
        range_payload = range_response.json()
        validate_projection(range_payload)
        assert range_payload["passage"]["scope"] == "verse_range"
        assert range_payload["passage"]["verse_start"] == 1
        assert range_payload["passage"]["verse_end"] == 2


def test_genesis_6_exposes_scoped_cultural_evidence_without_book_level_cross_references(ckl_library):
    payload = _client(_service(ckl_library)).get(
        "/api/narrative-explorer/v1/passages/Genesis/6"
    ).json()
    validate_projection(payload)

    sons = _item(
        payload,
        "ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions",
    )
    assert sons["object_type"] == "cultural_background"
    assert sons["certainty"] == "disputed"
    assert sons["dispute_status"] == "major_scholarly_disagreement"
    assert all(
        "Exodus 1" not in str(edge) and "Psalm 105" not in str(edge) and "Matthew 1" not in str(edge)
        for edge in payload["connections"]
    )
    assert not any(
        phrase in str(item.get("claim_text") or "").casefold()
        for item in payload["items"]
        for phrase in ("therefore the divine council interpretation is certain", "proves the sons of god are")
    )

    narrow = _client(_service(ckl_library)).get(
        "/api/narrative-explorer/v1/passages/Genesis/6",
        params={"verse_start": 1, "verse_end": 2},
    ).json()
    evidence_ids = {item["evidence_id"] for item in narrow["items"] if item.get("evidence_id")}
    assert "g6-sons-of-god-interpretive-positions" in evidence_ids
    assert "g6-nephilim-and-mighty-men" not in evidence_ids
    assert "g6-evil-intention-and-violence" not in evidence_ids


def test_psalm_82_discloses_council_context_and_keeps_explicit_text_distinct_from_dispute(ckl_library):
    payload = _client(_service(ckl_library)).get(
        "/api/narrative-explorer/v1/passages/Psalm/82"
    ).json()
    validate_projection(payload)

    claim = _item(payload, "ckl:ancient-divine-assembly-imagery#claim:psalm-82-assembly-text")
    assert claim["certainty"] == "textually_explicit"
    assert claim["dispute_status"] == "major_scholarly_disagreement"
    assert claim["interpretation_state"] == "disputed"
    assert not any(item["object_type"] == "theme" for item in payload["items"])


def test_deuteronomy_32_ckl_manuscript_witness_survives_empty_archaeology_lookup(ckl_library):
    payload = _client(_service(ckl_library)).get(
        "/api/narrative-explorer/v1/passages/Deuteronomy/32"
    ).json()
    validate_projection(payload)

    witness = _item(
        payload,
        "ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant",
    )
    assert witness["evidence_category"] == "manuscript"
    assert witness["certainty"] == "disputed"
    assert _coverage(payload)["archaeology"]["state"] == "not_represented"
    assert "ulrich-biblical-qumran-scrolls-2010" in witness["source_ids"]
    assert all(edge["connection_type"] != "direct_quotation" for edge in payload["connections"])


def test_acts7_nile_anchor_is_present_without_displayable_coordinates(ckl_library):
    nile_lookup = DomainLookup(
        domain="maps",
        query_status="complete",
        records=[{
            "id": "openbible-a012705",
            "name": "Nile",
            "marker_kind": "place",
            "description": "Existing Nile passage association.",
            "confidence": "unknown",
            "source_id": "openbible-info-bible-geocoding-data",
            "source_name": "OpenBible.info Bible Geocoding Data",
            "source_url": "https://www.openbible.info/geo/",
            "periods": [],
            "related_references": [{
                "id": "openbible-ref-openbible-a012705-45",
                "book": "Acts",
                "chapter": 7,
                "verse_start": 19,
                "verse_end": 19,
                "relationship_type": "directly_named",
                "notes": "Imported from OpenBible.info Bible Geocoding Data.",
            }],
        }],
    )
    payload = _client(_service(ckl_library, map_provider=lambda **_request: nile_lookup)).get(
        "/api/narrative-explorer/v1/passages/Acts/7"
    ).json()
    validate_projection(payload)

    nile = _item(payload, "maps:openbible-a012705")
    assert nile["title"] == "Nile"
    assert any(
        anchor["reference"] == "Acts 7:19" and anchor["relationship"] == "directly_named"
        for anchor in nile["passage_anchors"]
    )
    assert nile.get("coordinates_displayable") is not True
    assert nile.get("stored_coordinates") is None
    assert nile["navigation"]["target_id"] == "openbible-a012705"


def test_genesis_2_and_3_keep_eden_coordinates_unidentified_and_require_client_selection(ckl_library):
    client = _client(_service(ckl_library))
    for chapter in (2, 3):
        payload = client.get(f"/api/narrative-explorer/v1/passages/Genesis/{chapter}").json()
        eden = _item(payload, "maps:eden")
        assert eden["stored_coordinates"] == {"latitude": 31.0, "longitude": 35.0}
        assert eden["coordinates_displayable"] is False
        assert eden["place_identification_confidence"] == "unknown"
        navigation = next(item for item in payload["navigation"] if item["target_id"] == "eden")
        assert navigation["href"] == "/api/maps/biblical-places"
        assert navigation["selection_required"] is True
        assert "sacred_space" not in eden["geography_kind"]


def test_exodus_3_keeps_physical_places_uncertainty_and_conceptual_language_separate(ckl_library):
    payload = _client(_service(ckl_library)).get(
        "/api/narrative-explorer/v1/passages/Exodus/3"
    ).json()

    midian = _item(payload, "maps:midian")
    horeb = _item(payload, "maps:horeb-sinai")
    assert midian["geography_kind"] == "physical_place"
    assert midian["coordinates_displayable"] is True
    assert horeb["dispute_status"] == "identification_uncertainty"
    assert horeb["coordinates_displayable"] is False
    assert any(item["object_type"] == "theology" and item["geography_kind"] != "physical_place" for item in payload["items"])
    presence_theme = _item(payload, "ckl:presence-theme")
    divine_presence = _item(payload, "ckl:divine-presence")
    cosmic = next(
        section
        for section in payload["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    assert presence_theme["id"] not in cosmic["item_ids"]
    assert divine_presence["id"] not in cosmic["item_ids"]
    assert cosmic["item_ids"] == []
    assert cosmic["state"] == "unknown"
    assert "Passage-specific availability could not be established" in cosmic["description"]
    for navigation in payload["navigation"]:
        if navigation["kind"] in {"map_place", "map_route"}:
            assert navigation["selection_required"] is True


def test_invalid_passages_return_safe_errors_and_ckl_failure_is_unavailable():
    empty_library = _CanonicalLibrary()
    client = _client(_service(empty_library))

    assert client.get("/api/narrative-explorer/v1/passages/NotABook/1").status_code == 404
    assert client.get("/api/narrative-explorer/v1/passages/Genesis/999").status_code == 404
    assert client.get(
        "/api/narrative-explorer/v1/passages/Genesis/1",
        params={"verse_start": 3, "verse_end": 2},
    ).status_code == 422
    assert client.get(
        "/api/narrative-explorer/v1/passages/Genesis/1",
        params={"verse_end": 3},
    ).status_code == 422

    empty = client.get("/api/narrative-explorer/v1/passages/Genesis/1")
    assert empty.status_code == 200
    assert _coverage(empty.json())["ckl"]["state"] == "not_represented"

    unavailable_service = NarrativeExplorerService(
        study_db_path=PROJECT_ROOT / ".bhf-data" / "study.sqlite",
        canonical_library_provider=None,
        maps_lookup_provider=_map_provider,
        archaeology_lookup_provider=_empty_archaeology_provider,
    )
    unavailable = _client(unavailable_service).get("/api/narrative-explorer/v1/passages/Genesis/1")
    assert unavailable.status_code == 503
    assert unavailable.json() == {"error": "canonical_lookup_unavailable"}


def test_independent_domain_failures_and_partial_results_keep_accurate_coverage(ckl_library):
    library = ckl_library

    def failed_maps(**_request: Any) -> DomainLookup:
        raise OSError("do not disclose paths or configuration")

    payload = _client(
        _service(library, map_provider=failed_maps, archaeology_provider=lambda **_: (_ for _ in ()).throw(RuntimeError("private")))
    ).get("/api/narrative-explorer/v1/passages/Genesis/1").json()
    validate_projection(payload)
    coverage = _coverage(payload)
    assert coverage["ckl"]["query_status"] == "complete"
    assert coverage["maps"]["query_status"] == "failed"
    assert coverage["maps"]["state"] == "unknown"
    assert coverage["archaeology"]["query_status"] == "failed"
    assert coverage["archaeology"]["state"] == "unknown"
    assert coverage["ckl"]["state"] == "available"
    assert _item(payload, "ckl:genesis")
    cosmic = next(
        section
        for section in payload["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    ancient_cosmology_id = (
        "ckl:mesopotamian-creation-and-flood-comparisons"
        "#evidence:enuma-elish-cosmic-ordering-comparison"
    )
    assert ancient_cosmology_id in cosmic["item_ids"]
    assert cosmic["state"] == "partial"
    assert "private" not in str(payload)
    assert "/home/" not in str(payload)

    partial = _client(
        _service(
            library,
            map_provider=lambda **_: DomainLookup(
                domain="maps",
                records=[_map_record("midian", "Midian", "Exodus 3:1-2")],
                query_status="partial",
                reason_code="map_result_limit_reached",
                missing_subdomains=["routes"],
            ),
        )
    ).get("/api/narrative-explorer/v1/passages/Exodus/3").json()
    assert _coverage(partial)["maps"]["state"] == "partial"
    assert _coverage(partial)["maps"]["reason_code"] == "map_result_limit_reached"


def test_narrative_map_lookup_adds_explicit_links_alongside_text_matches(monkeypatch):
    import bhf_web.services.narrative_explorer as service_module

    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(service_module, "require_current_study_database", lambda _path: None)

    def places(**arguments: Any) -> dict[str, Any]:
        calls.append(("places", arguments.get("include_reference_matches", False)))
        return {"markers": [{"id": "text-jericho"}, {"id": "anchor-nile"}], "matched_terms": {"text-jericho": ["Jericho"]}}

    def routes(**arguments: Any) -> dict[str, Any]:
        calls.append(("routes", arguments.get("include_reference_matches", False)))
        return {"routes": [], "matched_terms": {}}

    monkeypatch.setattr(service_module, "resolve_places_for_passage", places)
    monkeypatch.setattr(service_module, "get_map_routes_for_passage", routes)
    lookup = NarrativeExplorerService(
        study_db_path=PROJECT_ROOT / ".bhf-data" / "study.sqlite",
    )._lookup_maps(
        book="Acts",
        chapter=7,
        verse_start=None,
        verse_end=None,
        passage_text="They came to Jericho.",
    )

    assert calls == [("places", True), ("routes", True)]
    assert lookup.query_status == "complete"
    assert [record["id"] for record in lookup.records] == ["text-jericho", "anchor-nile"]


def test_archaeology_resolver_limit_is_reported_as_partial(monkeypatch):
    import bhf_web.services.narrative_explorer as service_module

    records = [{"id": f"archaeology-{index}"} for index in range(25)]

    class _Archaeology:
        def for_passage(self, **arguments):
            assert arguments["limit"] == 25
            return {"archaeological_items": records}

    monkeypatch.setattr(service_module, "require_current_study_database", lambda _path: None)
    monkeypatch.setattr(service_module, "ArchaeologyService", lambda _path: _Archaeology())
    lookup = NarrativeExplorerService(
        study_db_path=PROJECT_ROOT / ".bhf-data" / "study.sqlite",
    )._lookup_archaeology(
        book="Genesis",
        chapter=1,
        verse_start=None,
        verse_end=None,
        passage_text="",
    )

    assert lookup.query_status == "partial"
    assert lookup.reason_code == "archaeology_result_limit_reached"
    assert lookup.missing_subdomains == ("remaining_archaeology_items",)
    assert len(lookup.records) == 25


def test_default_ckl_provider_never_builds_an_index_for_a_read_request(monkeypatch, tmp_path):
    import bhf_web.services.narrative_explorer as service_module
    from framework.canonical_library import CKLRepositoryConfig

    database_path = tmp_path / "missing-ckl.sqlite"
    expected_library = object()
    config = CKLRepositoryConfig(
        backend="sqlite",
        database_path=str(database_path),
        stale_database_policy="rebuild",
        read_only=False,
    )

    class _JsonRepository:
        def __init__(self, *, root):
            self.library = expected_library

    monkeypatch.setattr(service_module, "repository_config_from_env", lambda _base: config)
    monkeypatch.setattr(service_module, "JsonCanonicalRepository", _JsonRepository)

    assert service_module.NarrativeExplorerService._default_canonical_library() is expected_library
    assert not database_path.exists()


def test_ckl_lookup_uses_inventory_bound_not_a_small_fixed_cap_and_keeps_parent_ids_unique():
    objects = []
    for index in range(125):
        objects.append(
            {
                "id": f"large-fixture-{index:03d}",
                "type": "cultural_background",
                "title": f"Fixture {index}",
                "scripture_references": [],
                "sources": [],
                "claims": [],
                "evidence_items": [
                    {
                        "id": "shared-local-evidence",
                        "title": f"Witness {index}",
                        "description": "Recorded evidence " + ("x" * 1300),
                        "evidence_type": "manuscript",
                        "assertion_type": "primary-evidence",
                        "scripture_references": ["Genesis 1:1-2"],
                        "source_ids": ["missing-source"],
                    }
                ],
            }
        )
    library = _CanonicalLibrary(objects)
    response = _client(_service(library)).get("/api/narrative-explorer/v1/passages/Genesis/1")
    assert response.status_code == 200
    payload = response.json()
    validate_projection(payload)
    assert library.calls == [("Genesis 1", 125, {"include_placeholders": True})]
    evidence_items = [item for item in payload["items"] if item["record_kind"] == "evidence"]
    assert len(evidence_items) == 125
    assert _item(payload, "ckl:large-fixture-124#evidence:shared-local-evidence")
    unresolved = evidence_items[0]["sources"][0]
    assert unresolved["id"] == "missing-source"
    assert unresolved["details_available"] is False
    assert len(response.content) > 100_000


def test_projection_does_not_expose_personal_study_data_or_mutate_injected_records():
    record = {
        "id": "privacy-fixture",
        "type": "cultural_background",
        "title": "Public context",
        "scripture_references": [],
        "private_notes": ["private value"],
        "user_study_history": ["private passage"],
        "evidence_items": [
            {
                "id": "evidence",
                "title": "Public evidence",
                "description": "Authored public evidence.",
                "scripture_references": ["Genesis 1:1-2"],
                "personal_note": "private value",
            }
        ],
    }
    before = deepcopy(record)
    payload = _client(_service(_CanonicalLibrary([record]))).get(
        "/api/narrative-explorer/v1/passages/Genesis/1"
    ).json()

    assert "private value" not in str(payload)
    assert "private_notes" not in str(payload)
    assert "user_study_history" not in str(payload)
    assert record == before


def test_app_registers_only_the_versioned_route_and_preserves_existing_api_routes():
    from bhf_web.app import create_app

    paths = {getattr(route, "path", "") for route in create_app().routes}
    assert "/api/narrative-explorer/v1/passages/{book}/{chapter}" in paths
    assert "/api/narrative-explorer/passages/{book}/{chapter}" not in paths
    assert "/api/study/companion-context" in paths
    assert "/api/canonical/entities-for-passage" in paths
    assert "/api/maps/places-for-passage" in paths
    assert "/api/archaeology/for-passage" in paths
    assert "/api/commentary/{book}/{chapter}" in paths
