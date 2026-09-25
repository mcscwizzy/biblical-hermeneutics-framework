from __future__ import annotations

import json
from pathlib import Path

import pytest

from framework.canonical_library.geography_candidates import build_geography_candidate_queue
from framework.canonical_library.loader import CanonicalLibrary
from framework.canonical_library.expansion import apply_candidate_queue


ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "docs" / "ckl-geography-pilot-source-lock.json"


def _queue() -> dict[str, object]:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def library() -> CanonicalLibrary:
    return CanonicalLibrary().load()


@pytest.fixture(scope="module")
def result(library: CanonicalLibrary) -> dict[str, object]:
    return build_geography_candidate_queue(
        _queue(),
        library=library,
        root=ROOT,
    )


def test_builds_only_locked_candidates_for_eligible_chapters(result: dict[str, object]) -> None:
    records = result["candidates"]
    assert len(records) == 28
    assert {item["source_lock_status"] for item in records} == {"LOCKED"}
    assert {item["chapter_reference"] for item in records}.isdisjoint(
        {"Zechariah 2", "Mark 5", "Psalms 76", "Revelation 18", "Acts 16"}
    )
    assert {item["source_lock_id"] for item in records}.isdisjoint(
        {
            "genesis-34-shechem-person-place-conflation",
            "judges-20-bethel-campaign-movement",
            "acts-27-shipwreck-island-identification",
        }
    )


def test_preserves_locks_anchors_and_temporal_scope_in_accepted_candidate(result: dict[str, object]) -> None:
    candidate = next(
        item
        for item in result["candidates"]
        if item["source_lock_id"] == "matthew-2-bethlehem-judea-territory"
    )

    assert candidate["outcome"] == "NEW"
    assert candidate["source_locks"] == [
        {
            "source_id": "ckl-matthew-primary",
            "locator": "Matthew 2:1",
            "support_type": "direct-textual",
        },
        {
            "source_id": "openbible-geocoding-data",
            "locator": "records openbible-a112427 and openbible-a149f13; https://www.openbible.info/geo/atlas/bethlehem-1 and /judea-1",
            "support_type": "entity-identification-and-occurrence",
        },
    ]
    evidence = candidate["candidate_payload"]["evidence_item"]
    assert evidence["temporal_scope"] == candidate["temporal_scope"]
    assert evidence["scripture_references"] == [
        {
            "reference": "Matthew 2:1",
            "relationship": "direct",
            "temporal_relation": "unknown",
            "relevance_rationale": candidate["material_relevance"],
            "weight": 10,
        }
    ]
    assert evidence["related_objects"] == [
        {
            "id": "judea-1",
            "relationship": "located-in",
            "weight": 10,
            "notes": "ckl-matthew-primary @ Matthew 2:1 (direct-textual); openbible-geocoding-data @ records openbible-a112427 and openbible-a149f13; https://www.openbible.info/geo/atlas/bethlehem-1 and /judea-1 (entity-identification-and-occurrence)",
        }
    ]


def test_rejects_entity_bootstrap_and_untyped_entitlement_without_coercion(result: dict[str, object]) -> None:
    by_id = {item["source_lock_id"]: item for item in result["candidates"]}

    assert by_id["ruth-1-bethlehem-judah-territory"]["outcome"] == "REJECTED"
    assert by_id["ruth-1-bethlehem-judah-territory"]["rejection_reason"] == "entity-bootstrap-required"
    assert by_id["numbers-18-levites-no-territorial-inheritance"]["outcome"] == "REJECTED"
    assert by_id["numbers-18-levites-no-territorial-inheritance"]["rejection_reason"] == "schema-lacks-typed-target-value"


def test_dry_run_uses_candidate_sources_without_writing_production_ckl(
    result: dict[str, object],
) -> None:
    accepted = [
        item["candidate_payload"]
        for item in result["candidates"]
        if item["outcome"] == "NEW"
    ]
    before = {
        path.relative_to(ROOT).as_posix(): path.read_bytes()
        for path in (ROOT / "framework" / "canonical_library" / "objects").rglob("*.json")
    }

    transaction = apply_candidate_queue(
        ROOT / "framework" / "canonical_library",
        accepted,
        write=False,
    )

    assert transaction.wrote is False
    assert len(transaction.decisions) == 20
    assert all(decision.accepted for decision in transaction.decisions)
    after = {
        path.relative_to(ROOT).as_posix(): path.read_bytes()
        for path in (ROOT / "framework" / "canonical_library" / "objects").rglob("*.json")
    }
    assert after == before
