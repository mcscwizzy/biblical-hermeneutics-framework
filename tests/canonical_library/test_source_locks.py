"""Regression coverage for the non-mutating geography source-lock queue."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from framework.canonical_library.source_locks import (
    SourceLockValidationError,
    validate_source_lock_queue_against_repository,
    validate_source_lock_queue,
)


ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "docs" / "ckl-geography-pilot-source-lock.json"


def _minimal_queue() -> dict:
    return {
        "schema_version": "1.0",
        "queue_id": "test-geography-source-lock",
        "approved_pilot_references": ["Ruth 1"],
        "sources": [
            {
                "id": "ruth-primary",
                "title": "Ruth 1-4",
                "source_type": "scripture",
                "registry_status": "existing-ckl-object-source",
                "locator": "Ruth 1:1-4:22",
                "provenance": {
                    "record_path": "framework/canonical_library/objects/books/ruth.json",
                    "record_object_id": "ruth",
                    "record_source_id": "ruth-1-4",
                },
            }
        ],
        "chapters": [
            {
                "reference": "Ruth 1",
                "candidate_generation": "eligible",
                "classification_before": "THIN",
                "geography_gap": "travel context",
                "claims": [
                    {
                        "id": "ruth-1-bethlehem-moab-itinerary",
                        "status": "LOCKED",
                        "subject": {
                            "label": "Ruth 1 family movement",
                            "entity_type": "passage-event",
                            "resolution": "embedded-passage-event",
                        },
                        "relationship_type": "route-between",
                        "target": {
                            "label": "Bethlehem and Moab",
                            "entity_type": "place-pair",
                            "resolution": "existing-ckl-entities",
                        },
                        "source_locks": [
                            {
                                "source_id": "ruth-primary",
                                "locator": "Ruth 1:1-2, 6, 19, 22",
                                "support_type": "direct-textual",
                            }
                        ],
                        "scripture_anchors": [
                            {"reference": "Ruth 1:1-2", "eligibility": "direct"},
                            {"reference": "Ruth 1:19-22", "eligibility": "direct"},
                        ],
                        "temporal_scope": {"narrative_setting": "The narrated days of the judges."},
                        "confidence": {"level": "high", "rationale": "The passage names the journey endpoints."},
                        "provenance": {"model_role": "normalization-only"},
                        "material_relevance": "It bounds the chapter's departure and return without inventing a route.",
                        "candidate_readiness": "ready-for-evidence-item",
                    }
                ],
            }
        ],
    }


def test_source_lock_queue_requires_a_locator_for_locked_claims() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["claims"][0]["source_locks"][0]["locator"] = ""

    with pytest.raises(SourceLockValidationError, match="locator"):
        validate_source_lock_queue(queue)


def test_source_lock_queue_requires_temporal_scope_for_territory_claims() -> None:
    queue = _minimal_queue()
    claim = queue["chapters"][0]["claims"][0]
    claim["relationship_type"] = "territory-of"
    claim["temporal_scope"] = {}

    with pytest.raises(SourceLockValidationError, match="temporal"):
        validate_source_lock_queue(queue)


def test_source_lock_queue_requires_chapter_eligible_scripture_anchors() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["claims"][0]["scripture_anchors"] = []

    with pytest.raises(SourceLockValidationError, match="Scripture anchor"):
        validate_source_lock_queue(queue)


def test_source_lock_queue_rejects_cross_chapter_anchor_leakage() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["claims"][0]["scripture_anchors"][0]["reference"] = "Ruth 2:1"

    with pytest.raises(SourceLockValidationError, match="chapter-ineligible"):
        validate_source_lock_queue(queue)


def test_source_lock_queue_requires_a_registered_source() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["claims"][0]["source_locks"][0]["source_id"] = "unknown-source"

    with pytest.raises(SourceLockValidationError, match="unknown source"):
        validate_source_lock_queue(queue)


def test_source_lock_queue_rejects_a_model_as_source() -> None:
    queue = _minimal_queue()
    queue["sources"][0]["provenance"]["source_origin"] = "model-generated fact"

    with pytest.raises(SourceLockValidationError, match="model as its source"):
        validate_source_lock_queue(queue)


def test_source_lock_queue_rejects_ambiguous_same_name_entities() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["claims"][0]["subject"]["resolution"] = "ambiguous-person-place"

    with pytest.raises(SourceLockValidationError, match="ambiguous"):
        validate_source_lock_queue(queue)


def test_source_lock_queue_rejects_semantic_duplicates() -> None:
    queue = _minimal_queue()
    duplicate = copy.deepcopy(queue["chapters"][0]["claims"][0])
    duplicate["id"] = "ruth-1-bethlehem-moab-itinerary-duplicate"
    queue["chapters"][0]["claims"].append(duplicate)

    with pytest.raises(SourceLockValidationError, match="duplicate"):
        validate_source_lock_queue(queue)


def test_checked_in_pilot_source_lock_queue_is_valid() -> None:
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))

    report = validate_source_lock_queue(queue)

    assert report.chapter_count == 17
    assert report.status_counts["LOCKED"] > 0
    assert report.status_counts["REJECTED"] >= 3


def test_checked_in_pilot_source_locks_resolve_to_local_source_records() -> None:
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))

    validate_source_lock_queue_against_repository(queue, root=ROOT)


def test_maritime_lock_names_exact_imported_occurrence_records() -> None:
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    claim = next(
        claim for chapter in queue["chapters"] for claim in chapter["claims"]
        if claim["id"] == "acts-27-sidon-crete-maritime-itinerary"
    )
    locator = next(
        lock["locator"] for lock in claim["source_locks"]
        if lock["source_id"] == "openbible-geocoding-data"
    )
    locked_ids = set(re.findall(r"openbible-[a-z0-9]+", locator))
    imported = json.loads((ROOT / "bhf_agent/data/openbible_places.json").read_text(encoding="utf-8"))
    records = [item for item in imported if item["id"] in locked_ids]
    assert len(locked_ids) == len(records) == 8
    assert {item["name"] for item in records} == {
        "Italy", "Sidon", "Myra", "Cyprus", "Cnidus", "Crete", "Fair Havens", "Lasea",
    }
    assert all(any(
        ref["book"] == "Acts" and ref["chapter"] == 27 and
        ref["verse_start"] <= 8 and ref["verse_end"] >= 1
        for ref in item["references"]
    ) for item in records)


def test_repository_source_crosscheck_rejects_a_missing_source_id() -> None:
    queue = _minimal_queue()
    queue["sources"][0]["provenance"]["record_source_id"] = "missing-ruth-source"

    with pytest.raises(SourceLockValidationError, match="not present"):
        validate_source_lock_queue_against_repository(queue, root=ROOT)


def test_locked_geography_cannot_use_openbible_identity_as_sole_support() -> None:
    queue = _minimal_queue()
    queue["sources"][0]["source_type"] = "external-dataset"
    queue["chapters"][0]["claims"][0]["source_locks"][0]["support_type"] = "entity-identification-only"

    with pytest.raises(SourceLockValidationError, match="substantive Scripture"):
        validate_source_lock_queue(queue)


def test_scripture_locator_must_be_specific_to_claim_chapter() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["claims"][0]["source_locks"][0]["locator"] = "Ruth 2:1"

    with pytest.raises(SourceLockValidationError, match="Scripture locator"):
        validate_source_lock_queue(queue)


def test_scripture_locator_must_overlap_its_claim_anchor() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["claims"][0]["source_locks"][0]["locator"] = "Ruth 1:10"

    with pytest.raises(SourceLockValidationError, match="anchor"):
        validate_source_lock_queue(queue)


def test_malformed_verse_anchor_does_not_qualify_claim() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["claims"][0]["scripture_anchors"][0]["reference"] = "Ruth 1:unknown"

    with pytest.raises(SourceLockValidationError, match="Scripture anchor"):
        validate_source_lock_queue(queue)


def test_openbible_occurrence_must_overlap_claim_anchor() -> None:
    queue = _minimal_queue()
    queue["sources"].append(
        {
            "id": "openbible-geocoding-data",
            "title": "OpenBible imported places",
            "source_type": "external-dataset",
            "registry_status": "existing-repository-dataset",
            "locator": "bhf_agent/data/openbible_places.json",
            "provenance": {"record_path": "bhf_agent/data/openbible_places.json"},
        }
    )
    queue["chapters"][0]["claims"][0]["source_locks"].append(
        {
            "source_id": "openbible-geocoding-data",
            "locator": "record openbible-a69c1d4",
            "support_type": "entity-identification-and-occurrence",
        }
    )

    with pytest.raises(SourceLockValidationError, match="no anchor occurrence"):
        validate_source_lock_queue_against_repository(queue, root=ROOT)


def test_no_write_control_cannot_become_locked() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["candidate_generation"] = "no-write"

    with pytest.raises(SourceLockValidationError, match="no-write"):
        validate_source_lock_queue(queue)


def test_no_write_control_cannot_be_marked_candidate_ready() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["candidate_generation"] = "no-write"
    claim = queue["chapters"][0]["claims"][0]
    claim["status"] = "REJECTED"
    claim["disposition_reason"] = "Control chapter."

    with pytest.raises(SourceLockValidationError, match="no-write"):
        validate_source_lock_queue(queue)


def test_chapter_requires_explicit_candidate_generation_disposition() -> None:
    queue = _minimal_queue()
    queue["chapters"][0].pop("candidate_generation")

    with pytest.raises(SourceLockValidationError, match="candidate_generation"):
        validate_source_lock_queue(queue)


def test_withheld_chapter_cannot_be_candidate_ready() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["candidate_generation"] = "withheld"

    with pytest.raises(SourceLockValidationError, match="withheld"):
        validate_source_lock_queue(queue)


def test_locked_claim_requires_evidence_specific_confidence_rationale() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["claims"][0]["confidence"].pop("rationale")

    with pytest.raises(SourceLockValidationError, match="confidence rationale"):
        validate_source_lock_queue(queue)


def test_eligible_chapter_needs_a_locked_minimum() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["claims"][0]["status"] = "UNRESOLVED"
    queue["chapters"][0]["claims"][0]["disposition_reason"] = "No sufficient source."

    with pytest.raises(SourceLockValidationError, match="locked minimum"):
        validate_source_lock_queue(queue)


@pytest.mark.parametrize("relationship", ["located-in", "ruled-by"])
def test_historical_relationships_require_temporal_scope(relationship: str) -> None:
    queue = _minimal_queue()
    claim = queue["chapters"][0]["claims"][0]
    claim["relationship_type"] = relationship
    claim["temporal_scope"] = {}

    with pytest.raises(SourceLockValidationError, match="temporal scope"):
        validate_source_lock_queue(queue)


def test_conflicted_claim_requires_distinct_source_backed_alternatives() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["candidate_generation"] = "withheld"
    claim = queue["chapters"][0]["claims"][0]
    claim["status"] = "CONFLICTED"
    claim["candidate_readiness"] = "requires-alternative-review"
    claim["source_locks"].append(dict(claim["source_locks"][0]))

    with pytest.raises(SourceLockValidationError, match="alternatives"):
        validate_source_lock_queue(queue)


def test_conflicted_claim_can_preserve_two_unresolved_identifications() -> None:
    queue = _minimal_queue()
    queue["chapters"][0]["candidate_generation"] = "withheld"
    claim = queue["chapters"][0]["claims"][0]
    claim["status"] = "CONFLICTED"
    claim["candidate_readiness"] = "requires-alternative-review"
    first = claim["source_locks"][0]
    second = {**first, "locator": "Ruth 1:19-22"}
    claim["source_locks"].append(second)
    claim["alternatives"] = [
        {
            "target": {"label": "site A", "entity_type": "place", "resolution": "proposed"},
            "source_locks": [first],
        },
        {
            "target": {"label": "site B", "entity_type": "place", "resolution": "proposed"},
            "source_locks": [second],
        },
    ]

    report = validate_source_lock_queue(queue)

    assert report.status_counts == {"CONFLICTED": 1}
