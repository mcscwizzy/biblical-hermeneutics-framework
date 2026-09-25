from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from framework.canonical_library.geography_candidates import build_geography_candidate_queue, _typed_targets
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


def test_typed_families_cover_all_eight_locked_claims(result: dict[str, object]) -> None:
    by_id = {item["source_lock_id"]: item for item in result["candidates"]}
    typed = set(by_id) - set(json.loads((ROOT / "tests/fixtures/canonical_library/geography_original_20_payload_hashes.json").read_text()))
    assert len(typed) == 8
    assert {by_id[item]["outcome"] for item in typed} == {"NEW"}
    assert all(by_id[item]["candidate_payload"]["evidence_item"]["evidence_targets"] for item in typed)
    assert {item["id"] for record in typed for item in by_id[record]["candidate_payload"]["entity_bootstraps"]} == {
        "socoh-1", "azekah", "abana", "pharpar", "italy", "myra", "cyprus",
        "cnidus", "crete", "fair-havens", "lasea", "sychar", "archelaus", "judah-territory",
    }


def test_original_twenty_payload_hashes_are_unchanged(result: dict[str, object]) -> None:
    frozen = json.loads((ROOT / "tests/fixtures/canonical_library/geography_original_20_payload_hashes.json").read_text())
    actual = {}
    for record in result["candidates"]:
        if record["source_lock_id"] in frozen:
            payload = record["candidate_payload"]
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            actual[record["source_lock_id"]] = hashlib.sha256(canonical.encode()).hexdigest()
    assert actual == frozen


def test_sychar_requires_typed_field_target_and_bootstrap(result: dict[str, object]) -> None:
    record = next(item for item in result["candidates"] if item["source_lock_id"] == "john-4-sychar-well-near-jacob-field")
    assert record["outcome"] == "NEW"
    payload = record["candidate_payload"]
    assert {item["id"] for item in payload["entity_bootstraps"]} == {"sychar"}
    assert payload["evidence_item"]["evidence_targets"] == [{
        "kind": "value", "relationship": "near", "value_type": "geographic-feature",
        "normalized_value": "field", "display_value": "field Jacob gave to Joseph",
        "qualifiers": [
            {"kind": "attributed-giver", "entity_id": "jacob"},
            {"kind": "attributed-recipient", "entity_id": "joseph"},
        ],
    }]


@pytest.mark.parametrize(
    ("claim_id", "family", "mutate", "reason"),
    [
        ("acts-27-sidon-crete-maritime-itinerary", "maritime", lambda c: c["target"].update(label="Italy, Sidon, and Crete visited"), "malformed-maritime-sequence"),
        ("john-4-sychar-well-near-jacob-field", "field", lambda c: c["target"].update(label="Jacob's field somewhere"), "ambiguous-textual-field"),
        ("1samuel-17-socoh-azekah-encampment", "pair", lambda c: c["source_locks"][1].update(locator="record openbible-a39a6b9; https://www.openbible.info/geo/atlas/socoh-1 and /azekah"), "openbible-identity-unresolved"),
        ("matthew-2-archelaus-judea-administration", "person", lambda c: c["target"].update(label="an unnamed ruler"), "unregistered-person"),
    ],
)
def test_typed_grammar_rejects_unlocked_or_ambiguous_input(
    claim_id: str, family: str, mutate: object, reason: str,
) -> None:
    claim = deepcopy(next(
        claim for chapter in _queue()["chapters"] for claim in chapter["claims"]
        if claim["id"] == claim_id
    ))
    mutate(claim)
    with pytest.raises(ValueError, match=reason):
        _typed_targets(claim, family=family, library=None, root=ROOT)


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
    assert len(transaction.decisions) == 28
    assert all(decision.accepted for decision in transaction.decisions)
    after = {
        path.relative_to(ROOT).as_posix(): path.read_bytes()
        for path in (ROOT / "framework" / "canonical_library" / "objects").rglob("*.json")
    }
    assert after == before
