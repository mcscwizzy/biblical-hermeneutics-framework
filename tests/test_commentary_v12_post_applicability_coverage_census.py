"""Focused deterministic tests for the post-applicability coverage census."""

import hashlib
from pathlib import Path

from tools import commentary_v12_post_applicability_coverage_census as census


def _record(
    reference="Genesis 1",
    *,
    raw=10,
    inherited=8,
    legal=2,
    current=2,
    coverage=50.0,
    projected=1,
    old_current=6,
):
    return {
        "reference": reference,
        "book": reference.rsplit(" ", 1)[0],
        "chapter": int(reference.rsplit(" ", 1)[1]),
        "raw_evidence_bundle_evidence_count": raw,
        "inherited_legacy_evidence_count": inherited,
        "commentary_eligible_evidence_count": legal,
        "synthesis_unit_count": current,
        "current_chapter_synthesis_count": current,
        "projected_idea_count": projected,
        "legal_commentary_verse_coverage_percentage": coverage,
        "before": {
            "current_chapter_synthesis_count": old_current,
            "legal_verse_coverage_percentage": 100.0,
        },
    }


def test_frozen_population_identity_is_reproducible():
    population = census.load_population()
    assert population["chapter_count"] == 75
    assert population["manifest_identity"] == "eb282a2a684e13499f56894c0f9da9c38b71c08dd5c2cf58b0a072b64b487394"
    assert population["ordered_references_sha256"] == "876d0fbca0c3986a0c40c9e87b1028b826d2d510dd74c8c2875462482f4538ea"
    assert population["batch_sizes"] == [13, 13, 13, 12, 12, 12]


def test_coverage_calculation_counts_only_overlapping_current_chapter_verses():
    assert census.coverage_for_anchors(["Genesis 1:1-2", "Exodus 1:1"], "Genesis", 1) == {1, 2}


def test_state_classification_exposes_legacy_dependency_and_gap_flags():
    state = census.classify_state(_record(raw=18, inherited=18, legal=0, current=0, coverage=0.0, old_current=18))
    assert state["state"] == "MIXED"
    assert state["legacy_proportion"] == 1.0
    assert state["lost_current_chapter_synthesis_count"] == 18
    assert state["legal_coverage_loss_percentage_points"] == 100.0
    assert {"COMMENTARY_DATA_GAP", "LEGACY_INFLATED"}.issubset(state["diagnostic_flags"])


def test_state_classification_keeps_focused_positive_control_focused():
    record = _record(raw=2, inherited=0, legal=2, current=2, coverage=100.0, projected=0, old_current=2)
    state = census.classify_state(record)
    assert state["state"] == "EVIDENCE_FOCUSED"


def test_family_aggregation_reports_loss_and_queue_membership():
    record = _record(raw=1, inherited=1, legal=0, current=0, coverage=0.0, old_current=1)
    record.update(
        {
            "_legacy_evidence_ids": ["parent:historical_context:0"],
            "_bundle_records": [
                {
                    "id": "parent:historical_context:0",
                    "relevance_metadata": {
                        "parent_type": "person",
                        "field": "historical_context",
                    },
                }
            ],
            "_old_unit_records": [
                {"id": "old", "evidence_ids": ["parent:historical_context:0"], "verse_refs": ["Genesis 1:1-2"]}
            ],
            "_current_unit_records": [],
        }
    )
    queues = {
        "migration_candidates": [],
        "background_only_candidates": [
            {"book": "Genesis", "parent_object_type": "person", "legacy_field": "historical_context"}
        ],
        "editorial_review_queue": [],
    }
    rows = census.family_report([record], queues)
    assert rows == [
        {
            "family": "Genesis:person:historical_context",
            "book": "Genesis",
            "object_type": "person",
            "field": "historical_context",
            "affected_chapters": ["Genesis 1"],
            "affected_chapter_count": 1,
            "inherited_instances": 1,
            "former_synthesis_units": 1,
            "current_legal_synthesis_units": 0,
            "legal_verse_coverage_lost_count": 2,
            "migration_candidate_count": 0,
            "background_only_candidate_count": 1,
            "editorial_review_count": 0,
        }
    ]


def test_queue_ordering_is_reproducible_and_does_not_invent_anchors():
    def legacy(reference, ident):
        record = _record(reference, raw=1, inherited=1, legal=0, current=0, coverage=0.0, old_current=1)
        record.update(
            {
                "_legacy_evidence_ids": [f"{ident}:historical_context:0"],
                "_bundle_records": [
                    {
                        "id": f"{ident}:historical_context:0",
                        "relevance_metadata": {
                            "parent_object_id": ident,
                            "parent_type": "person",
                            "field": "historical_context",
                            "parent_title": ident.title(),
                            "source_kind": "ckl_legacy_field",
                            "inherited_from_parent": True,
                        },
                    }
                ],
                "_old_unit_records": [],
                "_current_unit_records": [],
            }
        )
        return record

    records = [legacy("Genesis 1", "person-a"), legacy("Genesis 2", "person-a")]
    objects = {"person-a": {"id": "person-a", "title": "Person A", "historical_context": "General biography."}}
    first = census.build_queues(records, objects)
    second = census.build_queues(list(reversed(records)), objects)
    assert first == second
    assert first["migration_candidates"] == []
    assert len(first["background_only_candidates"]) == 1
    assert first["background_only_candidates"][0]["reason"].startswith("legacy parent inheritance")


def test_contract_snapshot_keeps_protected_contracts_and_records_asv_repair():
    snapshot = census.contract_snapshot()
    assert snapshot["all_protected_contracts_unchanged"] is True
    assert all(
        row["unchanged_from_freeze"] is True
        for name, row in snapshot["contracts"].items()
        if name != "asv_bible"
    )
    assert snapshot["contracts"]["asv_bible"]["authorized_asv_repair_difference"] is True


def test_ckl_and_asv_are_not_mutated_by_read_only_inputs():
    paths = [census.CKL_PATH, census.ASV_PATH]
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    census.load_object_index()
    census.current_ckl()
    after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    assert after == before


def test_zero_model_and_renderer_invocation_surface():
    source = Path(census.__file__).read_text(encoding="utf-8").casefold()
    for forbidden in ("build_chat_adapter", "openrouter", "claude", "ollama", "gpt-5.6 sol"):
        assert forbidden not in source
    assert census.build_identity(
        {"manifest_identity": "population", "ordered_references_sha256": "references"},
        {"contracts": {"contract": {"sha256": "contract"}}},
    )[1]["model_calls"] == 0
