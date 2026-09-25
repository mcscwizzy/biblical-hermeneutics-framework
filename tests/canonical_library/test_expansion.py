from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from framework.canonical_library import CanonicalLibrary
from framework.canonical_library.expansion import (
    apply_candidate_queue,
    changed_chapter_references,
    changed_references,
    selective_recompile,
    validate_candidate,
)
from framework.canonical_library.semantic_deduplication import semantic_claim_fingerprint
from framework.canonical_library import semantic_deduplication

from .helpers import make_object, write_library


def _source(source_id: str = "gazetteer") -> dict[str, object]:
    return {
        "id": source_id,
        "title": "Approved geography gazetteer",
        "author": "",
        "publisher": "Fixture source",
        "year": None,
        "locator": "Bethlehem record",
        "url": "https://example.test/gazetteer",
        "source_type": "reference-work",
        "supports": [],
        "notes": "Source provenance fixture.",
    }


def _claim(claim_id: str = "existing") -> dict[str, object]:
    return {
        "id": claim_id,
        "claim": "Bethlehem is a named settlement in Ruth's passage.",
        "claim_type": "historical_cultural",
        "certainty": "probable",
        "dispute_status": "not_disputed",
        "scripture_references": ["Ruth 1:1-2"],
        "source_ids": ["gazetteer"],
        "traditions": [],
        "rationale": "The claim is limited to the source record and passage anchor.",
        "notes": "",
    }


def _library(tmp_path: Path) -> CanonicalLibrary:
    root = tmp_path / "ckl"
    write_library(
        root,
        [
            make_object(
                "bethlehem",
                "place",
                "Bethlehem",
                ["Bethlehem Ephrathah"],
                scripture_references=[
                    {"reference": "Ruth 1:1-2", "relationship": "primary", "notes": "named place"}
                ],
                sources=[_source()],
                claims=[_claim()],
            )
        ],
    )
    return CanonicalLibrary(root=root).load()


def _candidate(**overrides: object) -> dict[str, object]:
    candidate = {
        "dimension": "geography",
        "target_object_id": "bethlehem",
        "passage_reference": "Ruth 1:1-2",
        "claim": {
            **_claim("new-location"),
            "claim": "Bethlehem has a source-backed location record for Ruth 1.",
        },
    }
    candidate.update(overrides)
    return candidate


def _typed_evidence(
    evidence_id: str, source_id: str, *, description: str = "Bethlehem is near Sychar in this fixture.",
    target_id: str = "sychar", temporal_period: str = "Ruth narrative setting",
) -> dict[str, object]:
    return {
        "id": evidence_id, "title": "Bethlehem and Sychar proximity",
        "evidence_type": "geography-environment", "description": description,
        "assertion_type": "primary-evidence", "confidence": "high",
        "confidence_rationale": "The source names the places.",
        "passage_relevance": "The named setting is relevant to Ruth 1.",
        "certainty": "textually_explicit", "dispute_status": "not_disputed",
        "primary_observation": "Ruth 1 names Bethlehem.", "scholarly_interpretation": "",
        "temporal_scope": {"periods": [temporal_period]},
        "geography_ids": [], "related_objects": [], "related_evidence": [],
        "evidence_targets": [{"kind": "entity", "relationship": "near", "entity_id": target_id}],
        "scripture_references": [{
            "reference": "Ruth 1:1-2", "relationship": "direct",
            "temporal_relation": "contemporary", "relevance_rationale": "The passage names Bethlehem.",
            "weight": 9,
        }],
        "source_ids": [source_id], "claim_ids": [], "external_references": [],
        "metadata": {}, "notes": "",
    }


def _typed_source(source_id: str, locator: str) -> dict[str, object]:
    return {**_source(source_id), "locator": locator}


def _typed_library(tmp_path: Path, loaded: list[dict[str, object]]) -> CanonicalLibrary:
    root = tmp_path / "typed-ckl"
    sources = [_typed_source(source_id, f"Ruth 1:{index + 1}")
               for index, source_id in enumerate(dict.fromkeys(
                   source_id for evidence in loaded for source_id in evidence["source_ids"]
               ))]
    write_library(root, [
        make_object(
            "bethlehem", "place", "Bethlehem", ["Bethlehem Ephrathah"],
            scripture_references=[{"reference": "Ruth 1:1-2", "relationship": "primary", "notes": "named place"}],
            sources=sources, evidence_items=loaded,
        ),
        make_object("sychar", "place", "Sychar", ["Village of Sychar"]),
        make_object("judah-territory", "place", "Judah territory", ["Territory of Judah"]),
    ])
    return CanonicalLibrary(root=root).load()


def _typed_candidate(evidence_id: str, source_id: str, locator: str, *,
                     description: str = "Independent source describes the same proximity.",
                     target_id: str = "sychar") -> dict[str, object]:
    return {
        "source_lock_id": f"lock-{evidence_id}", "dimension": "geography",
        "target_object_id": "bethlehem", "passage_reference": "Ruth 1:1-2",
        "relationship": "near", "source_records": [_typed_source(source_id, locator)],
        "evidence_item": _typed_evidence(evidence_id, source_id, description=description, target_id=target_id),
    }


def test_structural_fingerprint_ignores_prose_but_keeps_relationship_and_time() -> None:
    first = _typed_evidence("first", "source-a")
    same = _typed_evidence("second", "source-b", description="Different wording.")
    different_target = _typed_evidence("third", "source-c", target_id="judah-territory")
    different_time = _typed_evidence("fourth", "source-d", temporal_period="Different period")
    fingerprint = semantic_deduplication.evidence_structural_fingerprint
    assert fingerprint("bethlehem", first) == fingerprint("bethlehem", same)
    assert fingerprint("bethlehem", first) != fingerprint("bethlehem", different_target)
    assert fingerprint("bethlehem", first) != fingerprint("bethlehem", different_time)


def test_staged_duplicate_preserves_loaded_canonical_id_and_merges_provenance(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [_typed_evidence("z-canonical", "existing")])
    result = apply_candidate_queue(library.root, [
        _typed_candidate("a-staged", "new", "Ruth 1:2"),
    ], write=False)
    merged = result.simulated_objects["bethlehem"]["evidence_items"]
    assert [item["id"] for item in merged] == ["z-canonical"]
    assert merged[0]["source_ids"] == ["existing", "new"]
    assert {source["id"]: source["locator"] for source in result.simulated_objects["bethlehem"]["sources"]} == {
        "existing": "Ruth 1:1", "new": "Ruth 1:2",
    }
    assert result.decisions[0].classification == "duplicate-existing-provenance-merged"
    assert result.decisions[0].survivor_evidence_id == "z-canonical"


def test_multiple_loaded_structural_matches_fail_closed(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [
        _typed_evidence("first", "existing"), _typed_evidence("second", "second-source"),
    ])
    with pytest.raises(ValueError, match="canonical-structural-duplicate-conflict"):
        apply_candidate_queue(library.root, [], write=False)


def test_staged_structural_duplicate_chooses_lowest_id_regardless_of_queue_order(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [])
    candidates = [
        _typed_candidate("z-staged", "source-z", "Ruth 1:2"),
        _typed_candidate("a-staged", "source-a", "Ruth 1:1"),
    ]
    first = apply_candidate_queue(library.root, candidates, write=False)
    reverse = apply_candidate_queue(library.root, list(reversed(candidates)), write=False)
    assert first.simulated_objects == reverse.simulated_objects
    merged = first.simulated_objects["bethlehem"]["evidence_items"]
    assert [item["id"] for item in merged] == ["a-staged"]
    assert merged[0]["source_ids"] == ["source-a", "source-z"]
    assert {decision.classification for decision in first.decisions} == {
        "new", "duplicate-pilot-provenance-merged",
    }
    assert all(decision.contributing_source_ids == ["source-a", "source-z"] for decision in first.decisions)


def test_structurally_distinct_typed_evidence_remains_complementary(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [])
    result = apply_candidate_queue(library.root, [
        _typed_candidate("sychar-near", "source-a", "Ruth 1:1"),
        _typed_candidate("judah-near", "source-b", "Ruth 1:2", target_id="judah-territory"),
    ], write=False)
    assert len(result.simulated_objects["bethlehem"]["evidence_items"]) == 2


def test_matching_source_id_with_different_locator_is_provenance_conflict(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [_typed_evidence("z-canonical", "existing")])
    result = apply_candidate_queue(library.root, [
        _typed_candidate("a-staged", "existing", "Different locator"),
    ], write=False)
    assert result.decisions[0].accepted is False
    assert result.decisions[0].classification == "provenance-conflict"
    assert result.decisions[0].provenance_conflicts == [{
        "source_id": "existing",
        "existing": _typed_source("existing", "Ruth 1:1"),
        "candidate": _typed_source("existing", "Different locator"),
    }]


def test_identical_source_duplicate_keeps_one_canonical_record(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [_typed_evidence("z-canonical", "existing")])
    result = apply_candidate_queue(library.root, [
        _typed_candidate("a-staged", "existing", "Ruth 1:1"),
    ], write=False)
    assert [item["id"] for item in result.simulated_objects["bethlehem"]["evidence_items"]] == ["z-canonical"]
    assert result.decisions[0].classification == "duplicate-existing"
    assert result.changed_object_ids == []
    assert result.changed_references == []


def test_compatible_equal_id_merges_passage_and_external_provenance(tmp_path: Path) -> None:
    loaded = _typed_evidence("same-id", "existing")
    library = _typed_library(tmp_path, [loaded])
    candidate = _typed_candidate("same-id", "new", "Ruth 1:2", description=str(loaded["description"]))
    candidate["evidence_item"]["scripture_references"].append({
        "reference": "Ruth 1:19-22", "relationship": "direct", "temporal_relation": "contemporary",
        "relevance_rationale": "Ruth returns to Bethlehem.", "weight": 8,
    })
    candidate["evidence_item"]["external_references"] = [{
        "domain": "map-place", "id": "external-sychar", "relationship": "same-evidence", "notes": "",
    }]
    result = apply_candidate_queue(library.root, [candidate], write=False)
    evidence = result.simulated_objects["bethlehem"]["evidence_items"][0]
    assert evidence["id"] == "same-id"
    assert evidence["source_ids"] == ["existing", "new"]
    assert {item["reference"] for item in evidence["scripture_references"]} == {"Ruth 1:1-2", "Ruth 1:19-22"}
    assert [item["id"] for item in evidence["external_references"]] == ["external-sychar"]


def test_equal_id_with_different_nonprovenance_fields_is_identity_conflict(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [_typed_evidence("same-id", "existing")])
    result = apply_candidate_queue(library.root, [
        _typed_candidate("same-id", "new", "Ruth 1:2", description="Changed assertion wording."),
    ], write=False)
    assert result.decisions[0].accepted is False
    assert result.decisions[0].classification == "identity-conflict"


def test_staged_duplicate_with_reused_source_id_and_changed_locator_is_rejected(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [])
    result = apply_candidate_queue(library.root, [
        _typed_candidate("a-staged", "shared-source", "Ruth 1:1"),
        _typed_candidate("z-staged", "shared-source", "Ruth 1:2"),
    ], write=False)
    assert [item["id"] for item in result.simulated_objects["bethlehem"]["evidence_items"]] == ["a-staged"]
    assert result.decisions[1].accepted is False
    assert result.decisions[1].classification == "provenance-conflict"


def _bootstrap_candidate(entity_id: str = "new-place") -> dict[str, object]:
    scripture_source = {**_typed_source("scripture-source", "Ruth 1:1"), "source_type": "scripture"}
    identity_source = _typed_source("openbible-source", f"records openbible-a123; https://www.openbible.info/geo/atlas/{entity_id}")
    identity = _typed_evidence(f"{entity_id}-identity", "scripture-source")
    identity.update(
        title=f"{entity_id} identity", description=f"{entity_id} is named in Ruth 1:1.",
        evidence_targets=[], source_ids=["scripture-source", "openbible-source"],
        external_references=[{
            "domain": "map-place", "id": "openbible-a123",
            "relationship": "same-evidence", "notes": "",
        }],
    )
    identity.pop("evidence_targets")
    bootstrap = make_object(
        entity_id, "place", entity_id.replace("-", " ").title(), [f"alias for {entity_id}"],
        content_status="draft", review_status="unreviewed", human_review_required=True,
        scripture_references=[{"reference": "Ruth 1:1-2", "relationship": "primary", "notes": "named place"}],
        sources=[scripture_source, identity_source], evidence_items=[identity],
    )
    candidate = _typed_candidate(
        f"{entity_id}-near", "scripture-source", "Ruth 1:1", target_id=entity_id,
    )
    candidate["source_records"] = [scripture_source]
    candidate["entity_bootstraps"] = [bootstrap]
    candidate["source_locks"] = [
        {"source_id": "scripture-source", "locator": "Ruth 1:1", "support_type": "direct-textual"},
        {"source_id": "openbible-source", "locator": identity_source["locator"], "support_type": "entity-identification-and-occurrence"},
    ]
    return candidate


def test_dry_run_stages_bootstrap_before_target_resolution_without_writing(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [])
    before = {path: path.read_bytes() for path in library.root.rglob("*.json")}
    result = apply_candidate_queue(library.root, [_bootstrap_candidate()], write=False)
    assert result.wrote is False
    assert "new-place" in result.simulated_objects
    assert result.changed_object_ids == ["bethlehem", "new-place"]
    assert result.decisions[0].accepted is True
    assert {path: path.read_bytes() for path in library.root.rglob("*.json")} == before


def test_identical_bootstrap_requests_coalesce(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [])
    first = _bootstrap_candidate()
    second = _bootstrap_candidate()
    second["evidence_item"] = _typed_evidence(
        "another-near", "scripture-source", target_id="new-place",
        description="Another source locates the place near Bethlehem.",
    )
    result = apply_candidate_queue(library.root, [first, second], write=False)
    assert list(result.simulated_objects).count("new-place") == 1
    assert result.simulated_objects["new-place"]["id"] == "new-place"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda bootstrap: bootstrap.update(title="Bethlehem"), "bootstrap.*title.*collision"),
        (lambda bootstrap: bootstrap.update(aliases=["Bethlehem Ephrathah"]), "bootstrap.*alias.*collision"),
        (lambda bootstrap: bootstrap.update(type="person"), "bootstrap.*type|bootstrap.*id.*conflict"),
        (lambda bootstrap: bootstrap.update(scripture_references=[]), "bootstrap.*anchor"),
        (lambda bootstrap: bootstrap.update(evidence_items=[]), "bootstrap.*identity evidence"),
    ],
)
def test_bootstrap_collision_and_identity_gates_fail_closed(tmp_path: Path, mutation, message: str) -> None:
    library = _typed_library(tmp_path, [])
    candidate = _bootstrap_candidate()
    mutation(candidate["entity_bootstraps"][0])
    with pytest.raises(ValueError, match=message):
        apply_candidate_queue(library.root, [candidate], write=False)


def test_bootstrap_same_id_with_different_mapping_conflicts(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [])
    first = _bootstrap_candidate()
    second = _bootstrap_candidate()
    second["entity_bootstraps"][0]["summary"] = "A different identity assertion."
    with pytest.raises(ValueError, match="bootstrap.*id.*conflict"):
        apply_candidate_queue(library.root, [first, second], write=False)


def test_bootstrap_write_mode_rejects_before_any_writer_runs(tmp_path: Path, monkeypatch) -> None:
    library = _typed_library(tmp_path, [])
    def forbidden_writer(*args, **kwargs):
        raise AssertionError("writer reached")
    monkeypatch.setattr("framework.canonical_library.expansion._write_json_atomically", forbidden_writer)
    with pytest.raises(ValueError, match="write=True.*bootstrap"):
        apply_candidate_queue(library.root, [_bootstrap_candidate()], write=True)


def test_bootstrap_rejects_unattached_openbible_identity_source(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [])
    candidate = _bootstrap_candidate()
    bootstrap = candidate["entity_bootstraps"][0]
    bootstrap["sources"] = [source for source in bootstrap["sources"] if source["id"] != "openbible-source"]
    bootstrap["evidence_items"][0]["source_ids"] = ["scripture-source"]
    with pytest.raises(ValueError, match="bootstrap.*OpenBible source"):
        apply_candidate_queue(library.root, [candidate], write=False)


def test_bootstrap_direct_source_record_must_overlap_lock_anchor(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [])
    candidate = _bootstrap_candidate()
    bootstrap = candidate["entity_bootstraps"][0]
    bootstrap["sources"][0]["locator"] = "Ruth 2:1"
    with pytest.raises(ValueError, match="bootstrap.*direct Scripture source"):
        apply_candidate_queue(library.root, [candidate], write=False)


def test_bootstrap_source_identity_collision_fails_closed(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [])
    first = _bootstrap_candidate("new-place")
    second = _bootstrap_candidate("another-place")
    with pytest.raises(ValueError, match="bootstrap source-identity collision"):
        apply_candidate_queue(library.root, [first, second], write=False)


def test_unbootstrapped_entity_target_stays_rejected(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [])
    candidate = _typed_candidate("missing-near", "source-a", "Ruth 1:1", target_id="new-place")
    result = apply_candidate_queue(library.root, [candidate], write=False)
    assert result.decisions[0].accepted is False
    assert "new-place" not in result.simulated_objects


def test_bootstrap_full_library_validation_rejects_missing_entity_reference(tmp_path: Path) -> None:
    library = _typed_library(tmp_path, [])
    candidate = _bootstrap_candidate()
    identity = candidate["entity_bootstraps"][0]["evidence_items"][0]
    identity["evidence_targets"] = [{
        "kind": "entity", "relationship": "near", "entity_id": "never-bootstrapped",
    }]
    with pytest.raises(ValueError, match="candidate queue fails final CKL validation.*never-bootstrapped"):
        apply_candidate_queue(library.root, [candidate], write=False)


def test_expansion_adapter_accepts_anchored_source_backed_geography_claim(tmp_path: Path) -> None:
    decision = validate_candidate(_candidate(), library=_library(tmp_path))

    assert decision.accepted is True
    assert decision.reasons == []


def test_expansion_adapter_rejects_cross_book_entity_leakage(tmp_path: Path) -> None:
    decision = validate_candidate(
        _candidate(
            passage_reference="Ruth 1:1-2",
            claim={**_claim("leak"), "scripture_references": ["1 Samuel 16:1-4"]},
        ),
        library=_library(tmp_path),
    )

    assert decision.accepted is False
    assert "scripture-anchor-not-eligible" in decision.reasons


def test_expansion_adapter_rejects_interpretive_or_duplicate_claims(tmp_path: Path) -> None:
    duplicate = validate_candidate(
        _candidate(
            claim={**_claim("duplicate"), "claim": "Bethlehem is a named settlement in Ruth's passage."}
        ),
        library=_library(tmp_path),
    )
    interpretive = validate_candidate(
        _candidate(
            claim={
                **_claim("interpretive"),
                "claim": "Bethlehem symbolizes spiritual struggle.",
                "claim_type": "biblical_theology",
            }
        ),
        library=_library(tmp_path),
    )

    assert duplicate.accepted is False
    assert "semantic-duplicate" in duplicate.reasons
    assert interpretive.accepted is False
    assert "interpretive-claim" in interpretive.reasons


@pytest.mark.parametrize("relationship", ["territory-of", "located-in", "ruled-by"])
def test_historical_geography_relationship_requires_temporal_scope(
    tmp_path: Path, relationship: str
) -> None:
    missing = validate_candidate(
        _candidate(relationship=relationship),
        library=_library(tmp_path),
    )
    qualified = validate_candidate(
        _candidate(
            relationship=relationship,
            temporal_scope={
                "start_year": -1000,
                "end_year": -900,
                "approximate": True,
                "periods": ["Iron Age"],
                "narrative_setting": "Ruth narrative setting",
            },
        ),
        library=_library(tmp_path),
    )

    assert missing.accepted is False
    assert "historical-relationship-requires-temporal-scope" in missing.reasons
    assert qualified.accepted is False
    assert "historical-relationship-requires-temporal-evidence-item" in qualified.reasons


def test_expansion_adapter_accepts_time_qualified_typed_geography_evidence_item(
    tmp_path: Path,
) -> None:
    """A production geography relation must retain its temporal qualifier."""

    root = tmp_path / "evidence-ckl"
    write_library(
        root,
        [
            make_object(
                "bethlehem",
                "place",
                "Bethlehem",
                ["Bethlehem Ephrathah"],
                scripture_references=[
                    {"reference": "Ruth 1:1-2", "relationship": "primary", "notes": "named place"}
                ],
                sources=[_source()],
            ),
            make_object(
                "judah-territory",
                "place",
                "Judah territory",
                ["territory of Judah"],
                sources=[_source()],
            ),
        ],
    )
    library = CanonicalLibrary(root=root).load()
    decision = validate_candidate(
        {
            "dimension": "geography",
            "target_object_id": "bethlehem",
            "passage_reference": "Ruth 1:1-2",
            "evidence_item": {
                "id": "bethlehem-judah-ruth-1",
                "title": "Bethlehem in Judah in Ruth 1",
                "evidence_type": "geography-environment",
                "description": "Ruth names Bethlehem as Bethlehem-judah while locating the family's movement between it and Moab.",
                "assertion_type": "primary-evidence",
                "confidence": "high",
                "confidence_rationale": "The relationship is explicitly named in the passage.",
                "passage_relevance": "The territorial label identifies the migration's Judean endpoint.",
                "certainty": "textually_explicit",
                "dispute_status": "not_disputed",
                "primary_observation": "Ruth 1:1-2 calls the origin Bethlehem-judah.",
                "scholarly_interpretation": "",
                "temporal_scope": {
                    "periods": ["Judges-period narrative setting"],
                    "narrative_setting": "The narrated setting of Ruth 1.",
                    "notes": "The relationship is qualified to the passage setting."
                },
                "geography_ids": ["bethlehem", "judah-territory"],
                "related_objects": [
                    {
                        "id": "judah-territory",
                        "relationship": "territory-of",
                        "weight": 9,
                        "notes": "Bethlehem-judah is the territorial label used in Ruth 1."
                    }
                ],
                "related_evidence": [],
                "scripture_references": [
                    {
                        "reference": "Ruth 1:1-2",
                        "relationship": "direct",
                        "temporal_relation": "contemporary",
                        "relevance_rationale": "The verses explicitly name Bethlehem-judah and the move to Moab.",
                        "weight": 9
                    }
                ],
                "source_ids": ["gazetteer"],
                "claim_ids": [],
                "external_references": [],
                "metadata": {},
                "notes": "No exact ancient route is asserted."
            },
        },
        library=library,
    )

    assert decision.accepted is True
    assert decision.reasons == []
    assert decision.normalized_evidence_item is not None


def test_candidate_queue_dry_run_does_not_write_and_explicit_apply_writes_only_target(
    tmp_path: Path,
) -> None:
    """The production queue must be a fail-closed dry run until explicitly applied."""

    library = _library(tmp_path)
    target_path = library.source_path_for("bethlehem")
    assert target_path is not None
    before = target_path.read_bytes()
    candidate = {
        "dimension": "geography",
        "target_object_id": "bethlehem",
        "passage_reference": "Ruth 1:1-2",
        "evidence_item": {
            "id": "bethlehem-ruth-travel-context",
            "title": "Bethlehem and Moab movement in Ruth 1",
            "evidence_type": "geography-environment",
            "description": "Ruth narrates movement from Bethlehem to Moab and a return from Moab to Bethlehem.",
            "assertion_type": "primary-evidence",
            "confidence": "high",
            "confidence_rationale": "The movement is explicit in Ruth 1.",
            "passage_relevance": "The movement frames Naomi and Ruth's return.",
            "certainty": "textually_explicit",
            "dispute_status": "not_disputed",
            "primary_observation": "Ruth 1:1-2 and 1:19-22 name the departure and return endpoints.",
            "scholarly_interpretation": "",
            "temporal_scope": {},
            "geography_ids": [],
            "related_objects": [],
            "related_evidence": [],
            "scripture_references": [
                {
                    "reference": "Ruth 1:1-2; Ruth 1:19-22",
                    "relationship": "direct",
                    "temporal_relation": "contemporary",
                    "relevance_rationale": "The narrative itself supplies the two endpoints and return.",
                    "weight": 9,
                }
            ],
            "source_ids": ["gazetteer"],
            "claim_ids": [],
            "external_references": [],
            "metadata": {},
            "notes": "No exact route or distance is asserted.",
        },
    }

    dry_run = apply_candidate_queue(library.root, [candidate], write=False)

    assert dry_run.wrote is False
    assert dry_run.changed_object_ids == ["bethlehem"]
    assert dry_run.changed_references == ["Ruth 1:1-2", "Ruth 1:19-22"]
    assert target_path.read_bytes() == before

    applied = apply_candidate_queue(library.root, [candidate], write=True)

    assert applied.wrote is True
    assert target_path.read_bytes() != before
    written = CanonicalLibrary(root=library.root).load().objects_by_id.get("bethlehem")
    assert written is not None
    assert [item.id for item in written.evidence_items] == ["bethlehem-ruth-travel-context"]


def test_geography_evidence_item_allows_an_institutional_territory_subject(
    tmp_path: Path,
) -> None:
    """Numbers 18 cannot be represented if geography is restricted to places."""

    root = tmp_path / "levites-ckl"
    write_library(
        root,
        [
            make_object("levites", "institution", "Levites", ["tribe of Levi"], sources=[_source()]),
            make_object("elders", "institution", "Elders", ["village elders"], sources=[_source()]),
            make_object("israel", "place", "Israel", ["land of Israel"], sources=[_source()]),
        ],
    )
    decision = validate_candidate(
        {
            "dimension": "geography",
            "target_object_id": "levites",
            "passage_reference": "Numbers 18:20-24",
            "evidence_item": {
                "id": "levites-no-territorial-inheritance",
                "title": "Levitical territorial inheritance in Numbers 18",
                "evidence_type": "geography-environment",
                "description": "Numbers states that the Levites have no territorial inheritance among Israel and receive tithe for their service.",
                "assertion_type": "primary-evidence",
                "confidence": "high",
                "confidence_rationale": "The allocation and its stated substitute are explicit in the passage.",
                "passage_relevance": "The territorial distinction explains the chapter's tithe provision.",
                "certainty": "textually_explicit",
                "dispute_status": "not_disputed",
                "primary_observation": "Numbers 18:20-24 denies the Levites an inheritance among Israel while assigning tithe.",
                "scholarly_interpretation": "",
                "temporal_scope": {
                    "narrative_setting": "The wilderness-period legal setting represented by Numbers 18.",
                    "notes": "This is not a timeless political-control claim."
                },
                "geography_ids": ["israel"],
                "related_objects": [
                    {
                        "id": "israel",
                        "relationship": "territory-of",
                        "weight": 9,
                        "notes": "The relationship is explicitly negative: no territorial inheritance among Israel."
                    }
                ],
                "related_evidence": [],
                "scripture_references": [
                    {
                        "reference": "Numbers 18:20-24",
                        "relationship": "direct",
                        "temporal_relation": "contemporary",
                        "relevance_rationale": "The verses set land inheritance and tithe side by side.",
                        "weight": 9
                    }
                ],
                "source_ids": ["gazetteer"],
                "claim_ids": [],
                "external_references": [],
                "metadata": {},
                "notes": "The record preserves the exclusion rather than assigning an invented territory."
            }
        },
        library=CanonicalLibrary(root=root).load(),
    )

    assert decision.accepted is True
    assert "geography-target-not-relevant" not in decision.reasons

    unrelated = validate_candidate(
        {**decision.candidate, "passage_reference": "Ruth 1:1-2"},
        library=CanonicalLibrary(root=root).load(),
    )
    assert unrelated.accepted is False
    assert "geography-target-not-relevant" in unrelated.reasons

    other_institution = validate_candidate(
        {**decision.candidate, "target_object_id": "elders"},
        library=CanonicalLibrary(root=root).load(),
    )
    assert other_institution.accepted is False
    assert "geography-target-not-relevant" in other_institution.reasons

    unrelated_levite_fact = validate_candidate(
        {
            **decision.candidate,
            "evidence_item": {
                **decision.candidate["evidence_item"],
                "id": "levites-service-only",
                "description": "The Levites serve at the tabernacle.",
                "primary_observation": "Numbers 18 names Levite service.",
                "related_objects": [],
            },
        },
        library=CanonicalLibrary(root=root).load(),
    )
    assert unrelated_levite_fact.accepted is False
    assert "geography-target-not-relevant" in unrelated_levite_fact.reasons

    positive_territory_edge = validate_candidate(
        {
            **decision.candidate,
            "evidence_item": {
                **decision.candidate["evidence_item"],
                "id": "levites-positive-territory",
                "related_objects": [
                    {"id": "israel", "relationship": "territory-of", "weight": 9, "notes": "Levites possess Israel's territory."}
                ],
            },
        },
        library=CanonicalLibrary(root=root).load(),
    )
    assert positive_territory_edge.accepted is False
    assert "geography-target-not-relevant" in positive_territory_edge.reasons


def test_temporal_geography_claim_cannot_bypass_scope_gate_by_omitting_relationship(tmp_path: Path) -> None:
    missing = validate_candidate(
        _candidate(
            claim={
                **_claim("roman-control"),
                "claim": "Bethlehem was controlled by the Roman Empire.",
            }
        ),
        library=_library(tmp_path),
    )
    discarded = validate_candidate(
        _candidate(
            temporal_scope={"periods": ["Roman period"]},
        ),
        library=_library(tmp_path),
    )

    assert missing.accepted is False
    assert "historical-relationship-requires-temporal-scope" in missing.reasons
    assert discarded.accepted is False
    assert "historical-relationship-requires-temporal-evidence-item" in discarded.reasons


def test_changed_reference_tracking_uses_changed_child_anchors(tmp_path: Path) -> None:
    library = _library(tmp_path)
    before = list(library.objects_by_id.values())
    changed = {
        **before[0].to_dict(),
        "claims": [
            {
                **_claim(),
                "claim": "Bethlehem's passage-specific location record was refined.",
                "scripture_references": ["Ruth 1:1-2"],
            }
        ],
    }
    after = [changed]

    assert changed_references(before, after) == ["Ruth 1:1-2"]
    assert changed_chapter_references(before, after) == ["Ruth 1"]


def test_parent_change_propagates_only_its_anchored_child_chapters(tmp_path: Path) -> None:
    library = _library(tmp_path)
    before = list(library.objects_by_id.values())
    changed = {
        **before[0].to_dict(),
        "summary": "A revised source-backed geographic summary.",
        "claims": [
            {
                **_claim(),
                "scripture_references": ["Ruth 1:1-2", "Ruth 2:1-3"],
            }
        ],
    }

    assert changed_chapter_references(before, [changed]) == ["Ruth 1", "Ruth 2"]


def test_selective_recompile_rejects_legacy_unvalidated_compiler_hooks():
    with pytest.raises(ValueError, match="cannot certify Commentary v1.2"):
        selective_recompile(
            ["Ruth 1"],
            bundle_builder=lambda reference: {"passage_ref": reference},
            synthesis_compiler=lambda bundle: {"reference": bundle["passage_ref"]},
        )


def _territory_library(tmp_path: Path) -> CanonicalLibrary:
    root = tmp_path / "territory-ckl"
    write_library(
        root,
        [
            make_object(
                "bethlehem",
                "place",
                "Bethlehem",
                ["Bethlehem Ephrathah"],
                scripture_references=[
                    {"reference": "Ruth 1:1-2", "relationship": "primary", "notes": "named place"}
                ],
                sources=[_source()],
                claims=[
                    {
                        **_claim("bethlehem-judah"),
                        "claim": "Bethlehem was located in Judah.",
                    }
                ],
            )
        ],
    )
    return CanonicalLibrary(root=root).load()


def test_semantic_duplicate_collapses_safe_territory_paraphrases(tmp_path: Path) -> None:
    library = _territory_library(tmp_path)
    belonged = validate_candidate(
        _candidate(
            claim={
                **_claim("bethlehem-belonged"),
                "claim": "Bethlehem belonged to Judah.",
            }
        ),
        library=library,
    )
    judean = validate_candidate(
        _candidate(
            claim={
                **_claim("bethlehem-judean"),
                "claim": "Bethlehem was a Judean town.",
            }
        ),
        library=library,
    )

    assert belonged.accepted is False
    assert judean.accepted is False
    assert "semantic-duplicate" in belonged.reasons
    assert "semantic-duplicate" in judean.reasons


def test_semantic_duplicate_preserves_complementary_physical_geography(tmp_path: Path) -> None:
    decision = validate_candidate(
        _candidate(
            claim={
                **_claim("bethlehem-hill-country"),
                "claim": "Bethlehem stood in the hill country.",
            }
        ),
        library=_territory_library(tmp_path),
    )

    assert decision.accepted is True
    assert "semantic-duplicate" not in decision.reasons


def test_semantic_territory_fingerprint_preserves_subject_and_negation() -> None:
    bethlehem = semantic_claim_fingerprint(
        "Bethlehem was located in Judah.",
        "historical_cultural",
    )
    hebron = semantic_claim_fingerprint(
        "Hebron was located in Judah.",
        "historical_cultural",
    )
    negated = semantic_claim_fingerprint(
        "Bethlehem was not located in Judah.",
        "historical_cultural",
    )

    assert bethlehem != hebron
    assert bethlehem != negated


def test_changed_child_anchor_invalidates_old_and_new_chapters(tmp_path: Path) -> None:
    library = _library(tmp_path)
    before = list(library.objects_by_id.values())
    after = [
        {
            **before[0].to_dict(),
            "claims": [
                {
                    **_claim(),
                    "scripture_references": ["Ruth 2:1-3"],
                }
            ],
        }
    ]

    assert changed_references(before, after) == ["Ruth 1:1-2", "Ruth 2:1-3"]
    assert changed_chapter_references(before, after) == ["Ruth 1", "Ruth 2"]


def test_unanchored_structured_parent_summary_does_not_fan_out_to_children() -> None:
    before = [
        {
            "id": "regional-parent",
            "type": "place",
            "title": "Regional parent",
            "summary": "Old summary",
            "sources": [_source()],
            "claims": [_claim()],
            "evidence_items": [],
            "scripture_references": [],
        }
    ]
    after = [{**before[0], "summary": "New summary"}]

    assert changed_references(before, after) == []


def test_anchored_entity_summary_change_propagates_its_parent_anchor() -> None:
    before = [
        {
            "id": "bethlehem",
            "type": "place",
            "title": "Bethlehem",
            "summary": "Old summary",
            "sources": [_source()],
            "claims": [_claim()],
            "evidence_items": [],
            "scripture_references": [
                {"reference": "Ruth 1:1-2", "relationship": "primary"}
            ],
        }
    ]
    after = [{**before[0], "summary": "New summary"}]

    assert changed_references(before, after) == ["Ruth 1:1-2"]


def test_source_change_propagates_only_children_that_use_that_source() -> None:
    source_a = _source("source-a")
    source_b = _source("source-b")
    claim_a = {**_claim("claim-a"), "source_ids": ["source-a"]}
    claim_b = {
        **_claim("claim-b"),
        "scripture_references": ["Ruth 2:1-3"],
        "source_ids": ["source-b"],
    }
    before = [
        {
            "id": "bethlehem",
            "type": "place",
            "title": "Bethlehem",
            "sources": [source_a, source_b],
            "claims": [claim_a, claim_b],
            "evidence_items": [],
            "scripture_references": [],
        }
    ]
    after = [
        {
            **before[0],
            "sources": [
                {**source_a, "locator": "Revised Bethlehem record"},
                source_b,
            ],
        }
    ]

    assert changed_references(before, after) == ["Ruth 1:1-2"]


def test_source_change_propagates_to_v12_child_with_parent_source_fallback() -> None:
    source = _source("source-a")
    child = {**_claim("inherited-source-child"), "source_ids": []}
    before = [
        {
            "id": "bethlehem",
            "type": "place",
            "title": "Bethlehem",
            "sources": [source],
            "claims": [child],
            "evidence_items": [],
            "scripture_references": [],
        }
    ]
    after = [{**before[0], "sources": [{**source, "locator": "Revised record"}]}]

    assert changed_references(before, after) == ["Ruth 1:1-2"]


def test_added_parent_source_does_not_fan_out_to_unrelated_fallback_children() -> None:
    source = _source("source-a")
    added = _source("source-b")
    child = {**_claim("inherited-source-child"), "source_ids": []}
    before = [
        {
            "id": "bethlehem",
            "type": "place",
            "title": "Bethlehem",
            "sources": [source],
            "claims": [child],
            "evidence_items": [],
            "scripture_references": [],
        }
    ]
    after = [{**before[0], "sources": [source, added]}]

    assert changed_references(before, after) == []


def test_added_parent_source_does_not_change_unrelated_parent_anchor() -> None:
    source = _source("source-a")
    added = _source("source-b")
    before = [
        {
            "id": "bethlehem",
            "type": "place",
            "title": "Bethlehem",
            "sources": [source],
            "claims": [],
            "evidence_items": [],
            "scripture_references": [
                {"reference": "Ruth 1:1-2", "relationship": "primary"}
            ],
        }
    ]
    after = [{**before[0], "sources": [source, added]}]

    assert changed_references(before, after) == []


def test_later_comparative_change_still_invalidates_v12_bundle_hash() -> None:
    evidence = {
        "id": "later-comparison",
        "evidence_type": "geography-environment",
        "description": "A later comparison mentions Bethlehem.",
        "source_ids": ["gazetteer"],
        "scripture_references": [
            {
                "reference": "Ruth 1:1-2",
                "relationship": "supporting",
                "temporal_relation": "later-comparative",
            }
        ],
    }
    before = [
        {
            "id": "bethlehem",
            "type": "place",
            "title": "Bethlehem",
            "sources": [_source()],
            "claims": [],
            "evidence_items": [evidence],
            "scripture_references": [],
        }
    ]
    after = [{**before[0], "evidence_items": [{**evidence, "description": "Revised."}]}]

    assert changed_references(before, after) == ["Ruth 1:1-2"]


def test_interpretive_note_change_invalidates_its_v12_bundle_chapters() -> None:
    note = {
        "note": "Old interpretation.",
        "sources": ["gazetteer"],
        "scripture_references": ["Ruth 1:1-2"],
    }
    before = [
        {
            "id": "ruth",
            "type": "book",
            "title": "Ruth",
            "sources": [_source()],
            "claims": [],
            "evidence_items": [],
            "interpretive_notes": [note],
            "scripture_references": [],
        }
    ]
    after = [{**before[0], "interpretive_notes": [{**note, "note": "Revised interpretation."}]}]

    assert changed_references(before, after) == ["Ruth 1:1-2"]


def test_selective_recompile_uses_current_v12_evidence_and_synthesis_contract() -> None:
    from bhf_agent.chapter_commentary.synthesis import (
        SYNTHESIS_COMPILER_VERSION,
        SYNTHESIS_SCHEMA_VERSION,
    )
    from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION

    first = selective_recompile(["Genesis 1"])
    second = selective_recompile(["Genesis 1"])

    assert first == second
    assert len(first) == 1
    row = first[0]
    assert row["reference"] == "Genesis 1"
    assert row["pipeline"] == "commentary-v1.2-enrichment"
    assert row["operation"] == "evidence-synthesis-only"
    assert row["evidence_bundle_version"] == EVIDENCE_BUNDLE_CANDIDATE_VERSION
    assert row["synthesis_schema_version"] == SYNTHESIS_SCHEMA_VERSION
    assert row["synthesis_compiler_version"] == SYNTHESIS_COMPILER_VERSION
    assert row["evidence_hash"]
    assert row["synthesis_hash"]
    assert "sections" not in row
    assert "commentary" not in row


def test_selective_recompile_revalidates_prepared_v12_synthesis() -> None:
    from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
    from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis
    from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION

    bundle = get_chapter_evidence_bundle(
        "Genesis",
        1,
        evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
    )
    assert bundle is not None
    synthesis = compile_chapter_synthesis(bundle, book="Genesis", chapter=1)
    invalid = replace(synthesis, synthesis_hash="0" * 64)

    with pytest.raises(ValueError, match="synthesis validation failed"):
        selective_recompile(
            ["Genesis 1"],
            chapter_preparer=lambda _book, _chapter: SimpleNamespace(
                bundle=bundle,
                synthesis=invalid,
            ),
        )


def test_selective_recompile_rejects_prepared_identity_from_another_chapter() -> None:
    from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
    from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis
    from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION

    bundle = get_chapter_evidence_bundle(
        "Genesis",
        1,
        evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
    )
    assert bundle is not None
    synthesis = compile_chapter_synthesis(bundle, book="Genesis", chapter=1)

    with pytest.raises(ValueError, match="bundle identity mismatch"):
        selective_recompile(
            ["Ruth 1"],
            chapter_preparer=lambda _book, _chapter: SimpleNamespace(
                bundle=bundle,
                synthesis=synthesis,
            ),
        )


def test_selective_recompile_rejects_deprecated_bundle_version() -> None:
    from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
    from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis
    from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION

    current = get_chapter_evidence_bundle(
        "Genesis",
        1,
        evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
    )
    assert current is not None
    synthesis = compile_chapter_synthesis(current, book="Genesis", chapter=1)

    with pytest.raises(ValueError, match="current v1.2 evidence bundle required"):
        selective_recompile(
            ["Genesis 1"],
            chapter_preparer=lambda _book, _chapter: SimpleNamespace(
                bundle=replace(current, version="1.0"),
                synthesis=synthesis,
            ),
        )


def test_selective_recompile_does_not_create_missing_study_database(tmp_path: Path) -> None:
    from bhf_agent.db.common import StudyDataError

    missing = tmp_path / "missing-study.sqlite"

    with pytest.raises(StudyDataError, match="current study database required for read-only access"):
        selective_recompile(["Genesis 1"], study_db_path=missing)

    assert not missing.exists()


def test_selective_recompile_normalizes_and_deduplicates_chapter_references() -> None:
    calls: list[tuple[str, int]] = []

    def prepare(book: str, chapter: int):
        calls.append((book, chapter))
        return None

    with pytest.raises(ValueError, match="prepared chapter is required"):
        selective_recompile(
            ["Ruth 1:1-22", "Ruth 1"],
            chapter_preparer=prepare,
        )
    assert calls == [("Ruth", 1)]


@pytest.mark.parametrize("reference", ["Ruth", "Ruth 1-2", "not a reference"])
def test_selective_recompile_rejects_non_chapter_identity(reference: str) -> None:
    with pytest.raises(ValueError, match="single canonical chapter"):
        selective_recompile([reference], chapter_preparer=lambda *_: None)


def test_recompile_cli_has_no_artifact_output_option() -> None:
    from framework.canonical_library.__main__ import build_parser

    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "recompile-chapters",
                "--references",
                "changed.json",
                "--output",
                "production.json",
            ]
        )
