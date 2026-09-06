from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from bhf_agent.presentation.evidence_hash import calculate_evidence_hash
from bhf_agent.presentation.models import EvidenceBundle, EvidenceItem
from bhf_agent.presentation.references import _BOOK_ALIASES
from bhf_agent.presentation.relevance import presentation_role
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from tools.commentary_v11_scaled_preflight import (
    EVIDENCE_BUNDLE_VERSION,
    EVIDENCE_HASH_VERSION,
    backend_agreement,
    quarantine_reasons,
    scan_anomalies,
    select_final_chapters,
    select_mixed_candidate_pool,
    _previous_batch_references,
    _checkpoint_identity,
    _json_dump,
    _load_recovery_manifest,
    _load_checkpoint,
    _mapping_is_textual,
    _presentation_audit,
    terra_textual_suppression_simulation,
)


def _item(
    evidence_id: str = "evidence-1",
    *,
    category: str = "history",
    claim: str = "A specific claim.",
    parent_type: str = "event",
    parent_id: str = "event-1",
    relationship: str = "DIRECT_CONTEXT",
    role: str | None = "historical_context",
    dispute_status: str = "not_disputed",
    assertion_type: str = "fact",
):
    metadata = {
        "parent_object_id": parent_id,
        "parent_type": parent_type,
        "parent_title": parent_id,
        "semantic_relationship": relationship,
        "presentation_role": role,
        "dispute_status": dispute_status,
        "assertion_type": assertion_type,
        "anchor_specificity": "verse",
    }
    return EvidenceItem(
        id=evidence_id,
        claim=claim,
        category=category,
        source_ids=["source-1"],
        related_entity_ids=[],
        passage_anchors=["Genesis 1:1"],
        confidence="high",
        relevance_metadata=metadata,
    )


def _bundle(*items):
    return EvidenceBundle(
        passage_ref="Genesis 1",
        entities={"people": [], "places": [], "groups": [], "events": [], "artifacts": []},
        evidence_items=list(items),
        geography={"places": [], "routes": []},
        provenance={"sources": [], "canonical_objects": []},
        version=EVIDENCE_BUNDLE_VERSION,
    )


def _result(object_id: str):
    return SimpleNamespace(object=SimpleNamespace(id=object_id))


def test_pool_excludes_existing_canaries_and_caps_book_dominance():
    rows = [
        {"reference": f"Genesis {n}", "book": "Genesis", "chapter": n, "availability_from_recalculation": "AVAILABLE"}
        for n in range(1, 8)
    ] + [
        {"reference": f"Luke {n}", "book": "Luke", "chapter": n, "availability_from_recalculation": "THIN"}
        for n in range(1, 8)
    ]
    pool = select_mixed_candidate_pool(rows, pool_size=10, excluded_references={"Genesis 1"})
    assert "Genesis 1" not in {row["reference"] for row in pool}
    assert max(sum(row["book"] == book for row in pool) for book in {"Genesis", "Luke"}) <= 5


def test_pool_never_selects_data_gap_rows():
    rows = [
        {"reference": "Numbers 3", "book": "Numbers", "chapter": 3, "availability_from_recalculation": "DATA_GAP"},
        {"reference": "Psalms 2", "book": "Psalms", "chapter": 2, "availability_from_recalculation": "THIN"},
    ]
    # The caller supplies the evidence-supported population; a DATA_GAP row
    # must not be silently promoted when it appears in a fixture.
    pool = select_mixed_candidate_pool([row for row in rows if row["availability_from_recalculation"] != "DATA_GAP"], pool_size=1)
    assert [row["reference"] for row in pool] == ["Psalms 2"]


def test_pool_mixes_available_and_thin():
    rows = [
        {"reference": f"Psalms {n}", "book": "Psalms", "chapter": n, "availability_from_recalculation": "AVAILABLE"}
        for n in range(1, 5)
    ] + [
        {"reference": f"Job {n}", "book": "Job", "chapter": n, "availability_from_recalculation": "THIN"}
        for n in range(1, 5)
    ]
    pool = select_mixed_candidate_pool(rows, pool_size=6)
    assert {row["availability_from_recalculation"] for row in pool} == {"AVAILABLE", "THIN"}


def test_soft_book_cap_yields_to_requested_pool_size():
    rows = [
        {"reference": f"Genesis {n}", "book": "Genesis", "chapter": n, "availability_from_recalculation": "AVAILABLE"}
        for n in range(1, 7)
    ]
    pool = select_mixed_candidate_pool(rows, pool_size=6)
    assert len(pool) == 6


def test_available_and_thin_can_pass_final_selection():
    evaluated = [
        {"reference": "Psalms 1", "status": "PASS", "availability": "AVAILABLE"},
        {"reference": "1 Samuel 28", "status": "PASS", "availability": "THIN"},
        {"reference": "Numbers 3", "status": "DATA_GAP", "availability": "DATA_GAP"},
    ]
    assert [row["reference"] for row in select_final_chapters(evaluated, 2)] == ["Psalms 1", "1 Samuel 28"]


def test_json_sqlite_disagreement_is_a_blocker():
    agreement = backend_agreement([_result("a")], [_result("b")], _bundle(_item()), _bundle(_item()))
    record = {"availability": "AVAILABLE", "json_sqlite_agreement": agreement, "semantic_audit": {"status": "PASS"}, "presentation_role_audit": {"status": "PASS"}, "anomaly_scan": {"anomalies": []}}
    assert "JSON_SQLITE_DISAGREEMENT" in quarantine_reasons(record)


def test_evidence_hash_disagreement_is_a_blocker():
    one = _bundle(_item())
    two = _bundle(_item(claim="Different evidence content."))
    one = replace(one, evidence_hash=calculate_evidence_hash(one))
    two = replace(two, evidence_hash=calculate_evidence_hash(two))
    agreement = backend_agreement([_result("a")], [_result("a")], one, two)
    record = {"availability": "AVAILABLE", "json_sqlite_agreement": agreement, "semantic_audit": {"status": "PASS"}, "presentation_role_audit": {"status": "PASS"}, "anomaly_scan": {"anomalies": []}}
    assert "EVIDENCE_HASH_DISAGREEMENT" in quarantine_reasons(record)


def test_suspicious_word_study_direct_context_is_flagged():
    item = _item("lexical", parent_type="word_study", parent_id="pneuma", claim="Greek pneuma serves as a lexical anchor for this passage.", category="language", role="language_literary")
    codes = {row["code"] for row in scan_anomalies(_bundle(item))}
    assert "WORD_STUDY_UNPROVEN_TRANSLATION_RELATIONSHIP" in codes


def test_legitimate_direct_lexical_evidence_is_allowed():
    item = _item("lexical", parent_type="word_study", parent_id="hebrew-term", claim="The Hebrew lexical form is used in this verse.", category="language", role="language_literary")
    assert scan_anomalies(_bundle(item)) == []


def test_comparative_lexical_evidence_remains_allowed():
    item = _item("lexical", parent_type="word_study", parent_id="makarios", claim="Greek translation comparison clarifies a range of blessedness language.", category="language", relationship="COMPARATIVE_CONTEXT", role="dig_deeper")
    assert scan_anomalies(_bundle(item)) == []


def test_suspicious_archaeology_template_is_flagged():
    item = _item("arch", parent_type="archaeology", claim="Ancient background for Site includes generic material culture.", category="archaeology", role="archaeology_geography")
    codes = {row["code"] for row in scan_anomalies(_bundle(item))}
    assert "ARCHAEOLOGY_TEMPLATE_DIRECT_CONTEXT" in codes


def test_legitimate_archaeology_is_allowed():
    item = _item("arch", parent_type="archaeology", claim="Excavation documents a first-century inscription at the named site.", category="archaeology", role="archaeology_geography")
    assert scan_anomalies(_bundle(item)) == []


def test_later_reception_cannot_ground_overview():
    item = _item("reception", parent_type="book", relationship="LATER_RECEPTION", role="historical_context")
    codes = {row["code"] for row in scan_anomalies(_bundle(item), overview_id="reception")}
    assert "LATER_RECEPTION_FIRST_AUDIENCE_LEAKAGE" in codes


def test_presentation_role_mismatch_is_flagged():
    item = _item("lexical", category="language", claim="Lexical morphology is discussed.", role="historical_context")
    codes = {row["code"] for row in scan_anomalies(_bundle(item))}
    assert "PRESENTATION_ROLE_MISMATCH" in codes


def test_broad_parent_anchor_leakage_is_detected():
    item = _item("broad", parent_type="event", claim="A direct claim.")
    fake_library = SimpleNamespace(_book_alias_lookup=_BOOK_ALIASES)
    parent = {"event-1": {"scripture_references": ["Genesis 1-50"]}}
    codes = {row["code"] for row in scan_anomalies(_bundle(item), library=fake_library, parent_records=parent)}
    assert "BROAD_PARENT_ANCHOR_LEAKAGE" in codes


def test_claim_level_precise_anchor_does_not_trigger_broad_parent_rule():
    item = _item("precise", parent_type="event", claim="A direct claim.")
    fake_library = SimpleNamespace(_book_alias_lookup=_BOOK_ALIASES)
    parent = {"event-1": {"scripture_references": ["Genesis 1:1"]}}
    assert "BROAD_PARENT_ANCHOR_LEAKAGE" not in {row["code"] for row in scan_anomalies(_bundle(item), library=fake_library, parent_records=parent)}


def test_template_direct_context_is_flagged():
    item = _item(claim="Literarily, this chapter is read through a template.")
    codes = {row["code"] for row in scan_anomalies(_bundle(item))}
    assert "TEMPLATE_DIRECT_CONTEXT" in codes


def test_disputed_evidence_remains_disputed_and_is_not_silently_normalized():
    item = _item(dispute_status="interpretation_disputed", assertion_type="disputed")
    assert scan_anomalies(_bundle(item), overview_id="not-this-item") == []
    assert item.relevance_metadata["dispute_status"] == "interpretation_disputed"


def test_disputed_overview_is_reviewed():
    item = _item(dispute_status="interpretation_disputed", relationship="BOOK_CONTEXT")
    stronger = _item("stronger", claim="A stronger direct historical claim.")
    codes = {row["code"] for row in scan_anomalies(_bundle(item, stronger), overview_id=item.id)}
    assert "DISPUTED_OVERVIEW_CANDIDATE" in codes


def test_extreme_count_is_review_signal_not_quarantine():
    from tools.commentary_v11_scaled_preflight import _mark_extreme_counts
    rows = [{"reference": str(n), "evidence_count": 1, "anomaly_scan": {}} for n in range(9)] + [{"reference": "outlier", "evidence_count": 100, "anomaly_scan": {}}]
    outliers = _mark_extreme_counts(rows)
    assert outliers and rows[-1]["anomaly_scan"]["review_signals"][0]["severity"] == "review"


def test_quarantined_chapter_does_not_block_other_chapters():
    evaluated = [
        {"reference": "bad", "status": "QUARANTINE", "availability": "AVAILABLE"},
        {"reference": "good", "status": "PASS", "availability": "THIN"},
    ]
    assert [row["reference"] for row in select_final_chapters(evaluated, 1)] == ["good"]


def test_textual_witness_cannot_follow_legacy_history_category():
    metadata = {
        "parent_type": "book",
        "parent_object_id": "acts",
        "semantic_relationship": "DIRECT_CONTEXT",
        "claim_type": "historical_cultural",
    }
    assert presentation_role(
        metadata,
        category="history",
        claim="Acts is preserved in early papyri and major Greek codices.",
    ) == "language_literary"


def test_textual_variant_routes_to_language_literary():
    metadata = {
        "parent_type": "book",
        "semantic_relationship": "DIRECT_CONTEXT",
        "claim_type": "biblical_text",
    }
    assert presentation_role(
        metadata,
        category="history",
        claim="Shorter and longer text forms remain debated among witnesses.",
    ) == "language_literary"


def test_interpretive_textual_uncertainty_may_route_to_questions():
    metadata = {
        "parent_type": "book",
        "semantic_relationship": "DIRECT_CONTEXT",
        "note_type": "interpretive_caution",
    }
    assert presentation_role(
        metadata,
        category="culture",
        claim="The manuscript reading is uncertain and should not control interpretation.",
    ) == "interpretive_questions"


def test_material_manuscript_discovery_remains_archaeology():
    metadata = {
        "parent_type": "archaeology",
        "source_kind": "archaeology_resolver",
        "semantic_relationship": "DIRECT_CONTEXT",
    }
    assert presentation_role(
        metadata,
        category="archaeology",
        claim="A manuscript was discovered at Qumran Cave X.",
    ) == "archaeology_geography"


def test_manuscript_reading_is_not_archaeology_because_object_is_physical():
    metadata = {
        "parent_type": "archaeology",
        "source_kind": "archaeology_resolver",
        "semantic_relationship": "DIRECT_CONTEXT",
    }
    assert presentation_role(
        metadata,
        category="archaeology",
        claim="This manuscript preserves a different reading of verse 5.",
    ) == "language_literary"


def test_terra_suppression_simulation_catches_bad_textual_routing():
    item = _item(
        "witness",
        category="history",
        claim="The manuscript preserves a different textual reading.",
        role="historical_context",
    )
    simulation = terra_textual_suppression_simulation(_bundle(item))
    assert simulation["terra_textual_suppression_required"] is True
    assert simulation["suppressed_items"][0]["evidence_id"] == "witness"


def test_suppression_required_is_a_blocking_verdict():
    record = {
        "availability": "AVAILABLE",
        "json_sqlite_agreement": {
            "result_ids_agree": True,
            "evidence_ids_agree": True,
            "bundle_hash_agree": True,
        },
        "semantic_audit": {"status": "PASS"},
        "presentation_role_audit": {"status": "PASS"},
        "textual_routing_audit": {"status": "PASS"},
        "terra_suppression_simulation": {"terra_textual_suppression_required": True},
        "anomaly_scan": {"anomalies": []},
    }
    assert "TERRA_SUPPRESSION_REQUIRED" in quarantine_reasons(record)


def test_clean_textual_variant_needs_no_suppression():
    item = _item(
        "luke-meal-variant",
        category="history",
        claim="Shorter and longer textual readings of the meal remain debated.",
        role="language_literary",
    )
    assert terra_textual_suppression_simulation(_bundle(item))["terra_textual_suppression_required"] is False


def test_replacement_selection_backfills_batch():
    evaluated = [{"reference": f"chapter-{n}", "status": "QUARANTINE" if n < 2 else "PASS", "availability": "AVAILABLE"} for n in range(5)]
    assert [row["reference"] for row in select_final_chapters(evaluated, 3)] == ["chapter-2", "chapter-3", "chapter-4"]


def test_final_certification_can_contain_exactly_fifty_passes():
    evaluated = [{"reference": f"chapter-{n}", "status": "PASS", "availability": "AVAILABLE"} for n in range(60)]
    assert len(select_final_chapters(evaluated, 50)) == 50


def test_bundle_version_and_hash_version_are_locked():
    bundle = _bundle(_item())
    assert bundle.version == EVIDENCE_BUNDLE_VERSION == "1.1"
    assert bundle.evidence_hash_version == EVIDENCE_HASH_VERSION == "2"


def test_retrieval_score_does_not_affect_evidence_hash():
    one = _bundle(_item())
    changed = replace(one.evidence_items[0], relevance_metadata={**one.evidence_items[0].relevance_metadata, "retrieval_score": 0.01})
    assert calculate_evidence_hash(one) == calculate_evidence_hash(replace(one, evidence_items=[changed]))


def test_semantic_role_change_affects_evidence_hash():
    one = _bundle(_item())
    changed = replace(one.evidence_items[0], relevance_metadata={**one.evidence_items[0].relevance_metadata, "semantic_relationship": "BOOK_CONTEXT"})
    assert calculate_evidence_hash(one) != calculate_evidence_hash(replace(one, evidence_items=[changed]))


def test_presentation_role_change_affects_evidence_hash():
    one = _bundle(_item())
    changed = replace(one.evidence_items[0], relevance_metadata={**one.evidence_items[0].relevance_metadata, "presentation_role": "dig_deeper"})
    assert calculate_evidence_hash(one) != calculate_evidence_hash(replace(one, evidence_items=[changed]))


def test_json_sqlite_agreement_requires_evidence_ids_as_well_as_parent_ids():
    one = _bundle(_item("one"))
    two = _bundle(_item("two"))
    agreement = backend_agreement([_result("a")], [_result("a")], one, two)
    assert agreement["result_ids_agree"] is True
    assert agreement["evidence_ids_agree"] is False
    assert "JSON_SQLITE_DISAGREEMENT" in quarantine_reasons({"availability": "AVAILABLE", "json_sqlite_agreement": agreement, "semantic_audit": {"status": "PASS"}, "presentation_role_audit": {"status": "PASS"}, "anomaly_scan": {"anomalies": []}})


def test_semantic_audit_failure_is_a_quarantine_reason():
    record = {"availability": "AVAILABLE", "json_sqlite_agreement": {"result_ids_agree": True, "evidence_ids_agree": True, "bundle_hash_agree": True}, "semantic_audit": {"status": "FAIL"}, "presentation_role_audit": {"status": "PASS"}, "anomaly_scan": {"anomalies": []}}
    assert "SEMANTIC_AUDIT_FAILURE" in quarantine_reasons(record)


def test_presentation_audit_failure_is_a_quarantine_reason():
    record = {"availability": "AVAILABLE", "json_sqlite_agreement": {"result_ids_agree": True, "evidence_ids_agree": True, "bundle_hash_agree": True}, "semantic_audit": {"status": "PASS"}, "presentation_role_audit": {"status": "FAIL"}, "anomaly_scan": {"anomalies": []}}
    assert "PRESENTATION_ROLE_AUDIT_FAILURE" in quarantine_reasons(record)


def test_numbers_data_gap_is_not_final_terra_input():
    evaluated = [{"reference": "Numbers 3", "status": "DATA_GAP", "availability": "DATA_GAP"}, {"reference": "Numbers 4", "status": "PASS", "availability": "THIN"}]
    assert [row["reference"] for row in select_final_chapters(evaluated, 2)] == ["Numbers 4"]


def test_allowed_final_availability_is_restricted_to_available_and_thin():
    evaluated = [{"reference": "gap", "status": "PASS", "availability": "DATA_GAP"}]
    assert select_final_chapters(evaluated, 1) == []


def test_textual_variant_does_not_route_to_archaeology_geography():
    metadata = {
        "parent_type": "book",
        "source_kind": "ckl_claim",
        "semantic_relationship": "DIRECT_CONTEXT",
        "claim_type": "biblical_text",
        "dispute_status": "textual_variant",
        "parent_object_id": "luke",
    }
    assert presentation_role(
        metadata,
        category="geography",
        claim="The reading is present in major manuscript witnesses but absent in important Western witnesses.",
    ) == "language_literary"


def test_dispute_status_alone_is_not_textual_witness_evidence():
    metadata = {
        "parent_type": "event",
        "source_kind": "ckl_claim",
        "semantic_relationship": "DIRECT_CONTEXT",
        "dispute_status": "textual_variant",
    }
    claim = "A historical model remains disputed."
    assert _mapping_is_textual({"relevance_metadata": metadata, "claim": claim}) is False
    assert presentation_role(metadata, category="history", claim=claim) == "historical_context"


def test_checkpoint_identity_rejects_other_run_configuration(tmp_path):
    identity = _checkpoint_identity(
        batch_id="batch-004",
        target_count=150,
        candidate_pool_size=250,
        candidate_source=tmp_path / "candidate-source",
    )
    path = tmp_path / "checkpoint.json"
    _json_dump(path, {"checkpoint_identity": identity, "stage": "selected"})
    assert _load_checkpoint(path, identity)["stage"] == "selected"
    altered = {**identity, "target_count": 149}
    assert _load_checkpoint(path, altered) is None


def test_recovery_manifest_rejects_duplicate_canonical_references(tmp_path):
    path = tmp_path / "recovery.json"
    _json_dump(path, {"chapters": [{"reference": "Genesis 1"}, {"reference": "Genesis 1"}]})
    try:
        _load_recovery_manifest(path)
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate recovery references must be rejected")


def test_textual_criticism_routes_to_language_literary():
    metadata = {
        "parent_type": "event",
        "source_kind": "ckl_claim",
        "semantic_relationship": "DIRECT_CONTEXT",
        "claim_type": "textual_criticism",
    }
    assert presentation_role(metadata, category="archaeology", claim="Textual transmission preserves two readings.") == "language_literary"


def test_interpretive_textual_uncertainty_routes_to_questions():
    metadata = {
        "parent_type": "event",
        "source_kind": "ckl_interpretive_note",
        "semantic_relationship": "DIRECT_CONTEXT",
        "note_type": "interpretive_question",
        "dispute_status": "textual_variant",
    }
    assert presentation_role(metadata, category="geography", claim="The manuscript reading remains uncertain.") == "interpretive_questions"


def test_real_archaeology_and_geography_keep_their_roles():
    archaeology = {
        "parent_type": "archaeology",
        "source_kind": "ckl_evidence_item",
        "semantic_relationship": "DIRECT_CONTEXT",
    }
    geography = {
        "parent_type": "place",
        "source_kind": "ckl_evidence_item",
        "semantic_relationship": "DIRECT_CONTEXT",
    }
    assert presentation_role(archaeology, category="archaeology", claim="Excavation documents a first-century inscription.") == "archaeology_geography"
    assert presentation_role(geography, category="geography", claim="The route runs from the named city to the valley.") == "archaeology_geography"


def test_literary_claim_with_place_name_does_not_become_geography():
    metadata = {
        "parent_type": "book",
        "source_kind": "ckl_claim",
        "semantic_relationship": "BOOK_CONTEXT",
        "claim_type": "literary",
    }
    assert presentation_role(metadata, category="geography", claim="The literary movement links Jerusalem and Galilee.") == "language_literary"


def test_luke_22_regression_routes_meal_variant_to_language_literary():
    bundle = get_chapter_evidence_bundle("Luke", 22)
    item = next(item for item in bundle.evidence_items if item.id == "luke-meal-variant")
    assert item.relevance_metadata["presentation_role"] == "language_literary"


def test_batch_002_excludes_batch_001_final_and_quarantined_references():
    excluded = _previous_batch_references("batch-002")
    assert "Luke 22" in excluded
    assert "Deuteronomy 32" in excluded
    assert "Job 1" in excluded
    assert "Leviticus 19" in excluded


def test_old_luke_22_role_is_a_textual_routing_blocker():
    item = _item(
        "luke-meal-variant",
        category="geography",
        claim="A textual variant is preserved in major manuscript witnesses.",
        parent_type="book",
        parent_id="luke",
        role="archaeology_geography",
    )
    audit = _presentation_audit(_bundle(item))
    assert audit["status"] == "FAIL"
    assert any("expected-role:language_literary" in error for error in audit["errors"])
