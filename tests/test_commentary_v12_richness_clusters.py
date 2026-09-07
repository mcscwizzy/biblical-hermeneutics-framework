"""Tests for deterministic reader-level synthesis richness diagnostics."""

import json
from pathlib import Path
from types import SimpleNamespace

from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V1,
    CORE_CLASSIFIER_V2,
    DuplicateReason,
    DumpSeverity,
    GateClass,
    GateOutcome,
    QualityClass,
    assess_gate_v2,
    cluster_synthesis_units,
    classify_gate_class,
    proposed_gate_passes,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.chapter_commentary.synthesis.storage import load_synthesis
from bhf_agent.chapter_commentary.synthesis.models import SynthesisUnit
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION, EvidenceItem


def _unit(
    ident,
    *,
    kind="historical_context",
    facts=("A distinct supported fact.",),
    evidence_ids=(),
    entity_ids=(),
    related_unit_ids=(),
    passage_scope="CURRENT_CHAPTER",
    interpretation_level="fact",
    explicit_significance=False,
):
    return SimpleNamespace(
        id=ident,
        kind=kind,
        facts=list(facts),
        evidence_ids=list(evidence_ids),
        entity_ids=list(entity_ids),
        related_unit_ids=list(related_unit_ids),
        passage_scope=passage_scope,
        interpretation_level=interpretation_level,
        metadata={"explicit_significance": explicit_significance},
    )


def _evidence(
    ident,
    *,
    parent="parent",
    category="history",
    entity_ids=(),
    disputed="",
    role=None,
    passage_relationship="",
):
    return EvidenceItem(
        id=ident,
        claim="Supported claim.",
        category=category,
        source_ids=["source"],
        related_entity_ids=list(entity_ids),
        passage_anchors=["Genesis 1:1"],
        confidence="high",
        relevance_metadata={
            "parent_object_id": parent,
            "dispute_status": disputed,
            "presentation_role": role,
            "passage_relationship": passage_relationship,
        },
    )


def test_exact_duplicate_clustering_is_deterministic():
    units = [
        _unit("source", facts=("The same fact.",), evidence_ids=("e1",)),
        _unit(
            "derived",
            facts=("The same fact.",),
            evidence_ids=("e1",),
            related_unit_ids=("source",),
        ),
    ]
    first = cluster_synthesis_units(units, [_evidence("e1")])
    second = cluster_synthesis_units(reversed(units), [_evidence("e1")])
    assert first == second
    assert len(first) == 1
    assert first[0].duplicate_reason == DuplicateReason.EXACT_DUPLICATE.value
    assert first[0].synthesis_ids == ["derived", "source"]


def test_ancestry_duplicate_does_not_require_identical_fact_text():
    units = [
        _unit("one", facts=("First wording.",), evidence_ids=("e1",)),
        _unit("two", facts=("Second wording.",), evidence_ids=("e1",)),
    ]
    clusters = cluster_synthesis_units(units, [_evidence("e1")])
    assert len(clusters) == 1
    assert clusters[0].duplicate_reason == DuplicateReason.ANCESTRY_DUPLICATE.value


def test_parent_parallel_strips_what_is_the_prefix():
    units = [
        _unit("tabernacle", facts=("A mobile sanctuary stood in the wilderness.",), evidence_ids=("e1",)),
        _unit("what-is", facts=("The wilderness tent served as a mobile sanctuary.",), evidence_ids=("e2",)),
    ]
    evidence = [
        _evidence("e1", parent="tabernacle"),
        _evidence("e2", parent="what-is-the-tabernacle"),
    ]
    clusters = cluster_synthesis_units(units, evidence)
    assert len(clusters) == 1
    assert clusters[0].duplicate_reason == DuplicateReason.PARENT_PARALLEL.value


def test_distinct_facts_remain_distinct():
    units = [
        _unit("one", facts=("A priest guarded the sanctuary.",), evidence_ids=("e1",)),
        _unit("two", facts=("A festival marked the harvest.",), evidence_ids=("e2",)),
    ]
    evidence = [_evidence("e1", parent="priesthood"), _evidence("e2", parent="festival")]
    clusters = cluster_synthesis_units(units, evidence)
    assert len(clusters) == 2
    assert all(cluster.duplicate_reason == DuplicateReason.DISTINCT.value for cluster in clusters)


def test_quality_classes_and_weighted_category_coverage():
    units = [
        _unit("core", facts=("Core fact.",), evidence_ids=("e1",), entity_ids=("place",)),
        _unit("support", facts=("Supporting fact.",), evidence_ids=("e2",)),
        _unit("optional", facts=("Optional comparison.",), evidence_ids=("e3",)),
        _unit("surrounding", facts=("A surrounding passage.",), evidence_ids=("e4",), passage_scope="SURROUNDING_PASSAGE"),
        _unit("disputed", facts=("A disputed reading.",), evidence_ids=("e5",), interpretation_level="disputed"),
    ]
    evidence = [
        _evidence(
            "e1",
            parent="core",
            category="geography",
            entity_ids=("place",),
            passage_relationship="direct",
        ),
        _evidence("e2", parent="support", category="history"),
        _evidence("e3", parent="optional", category="culture", role="dig_deeper"),
        _evidence("e4", parent="surrounding", category="history"),
        _evidence("e5", parent="disputed", category="language", disputed="major_scholarly_disagreement"),
    ]
    score = score_synthesis_richness(
        units,
        evidence_items=evidence,
        consumed_synthesis_ids=("core", "support", "surrounding", "disputed"),
        blocks=[],
        passage_ref="Genesis 1",
    )
    classes = {cluster.synthesis_ids[0]: cluster.quality_class for cluster in score.clusters}
    assert classes["core"] == QualityClass.CORE.value
    assert classes["support"] == QualityClass.SUPPORTING.value
    assert classes["optional"] == QualityClass.OPTIONAL.value
    assert classes["surrounding"] == QualityClass.SURROUNDING.value
    assert classes["disputed"] == QualityClass.DISPUTED.value
    assert score.consumed_cluster_count == 4
    assert score.category_coverage > 0.7
    assert score.weighted_idea_coverage > 0.7


def test_evidence_dump_detection_flags_one_record_per_block():
    units = [_unit(f"u{i}", facts=(f"Fact {i}.",), evidence_ids=(f"e{i}",)) for i in range(20)]
    evidence = [_evidence(f"e{i}", parent=f"parent-{i}") for i in range(20)]
    blocks = [SimpleNamespace(text=f"Block {i}.", evidence_ids=[f"e{i}"], synthesis_ids=[f"u{i}"]) for i in range(20)]
    score = score_synthesis_richness(
        units,
        evidence_items=evidence,
        consumed_synthesis_ids=[f"u{i}" for i in range(20)],
        blocks=blocks,
    )
    assert "ONE_BLOCK_PER_SYNTHESIS_UNIT" in score.dump_diagnostics.signals
    assert "LOW_EVIDENCE_PER_BLOCK_CONSOLIDATION" in score.dump_diagnostics.signals
    assert score.dump_diagnostics.consolidation_ratio == 0.0


def test_data_gap_has_no_quality_pass_path():
    score = score_synthesis_richness([], evidence_items=[], consumed_synthesis_ids=[])
    passed, checks = proposed_gate_passes(
        score=score,
        evidence_availability="DATA_GAP",
        validation_clean=True,
        boilerplate_detected=False,
        evidence_use_delta=1,
    )
    assert passed is False
    assert checks["evidence_available"] is False


def test_concise_genealogy_is_not_dumped_or_length_penalized():
    unit = _unit(
        "genealogy",
        kind="surrounding_passages",
        facts=("Genealogies are selective literary maps.",),
        evidence_ids=("e1",),
        passage_scope="SURROUNDING_PASSAGE",
    )
    score = score_synthesis_richness(
        [unit],
        evidence_items=[_evidence("e1", category="culture")],
        consumed_synthesis_ids=["genealogy"],
        blocks=[SimpleNamespace(text="A concise note.", evidence_ids=["e1"], synthesis_ids=["genealogy"])],
    )
    assert score.dump_diagnostics.signals == []
    assert score.consumed_cluster_count == 1


def test_leviticus_16_denominator_case_is_reduced_without_regenerating():
    root = ".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/canary"
    synthesis = load_synthesis(f"{root}/synthesis", "Leviticus", 16)
    bundle = get_chapter_evidence_bundle(
        "Leviticus", 16, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    assert synthesis is not None and bundle is not None
    score = score_synthesis_richness(
        synthesis.synthesis_units,
        evidence_items=bundle.evidence_items,
        consumed_synthesis_ids=[],
    )
    assert score.synthesis_unit_count == 41
    assert score.meaningful_cluster_count == 20
    assert score.synthesis_unit_count > score.meaningful_cluster_count


def test_genesis_1_full_raw_consumption_still_exposes_dumping():
    units = [_unit(f"u{i}", facts=(f"Fact {i}.",), evidence_ids=(f"e{i}",)) for i in range(20)]
    evidence = [_evidence(f"e{i}") for i in range(20)]
    blocks = [SimpleNamespace(text=f"Block {i}.", evidence_ids=[f"e{i}"], synthesis_ids=[f"u{i}"]) for i in range(20)]
    score = score_synthesis_richness(units, evidence_items=evidence, consumed_synthesis_ids=[u.id for u in units], blocks=blocks)
    assert score.raw_synthesis_coverage == 1.0
    assert score.dump_diagnostics.signal_count >= 2


def test_proposed_gate_requires_clean_safety_and_material_evidence_use():
    unit = _unit("u", facts=("Core fact.",), evidence_ids=("e",), entity_ids=("entity",))
    score = score_synthesis_richness([unit], evidence_items=[_evidence("e", entity_ids=("entity",))], consumed_synthesis_ids=["u"])
    passed, checks = proposed_gate_passes(
        score=score,
        evidence_availability="AVAILABLE",
        validation_clean=False,
        boilerplate_detected=False,
        evidence_use_delta=1,
    )
    assert passed is False
    assert checks["validation_clean"] is False


def test_gate_classification_uses_evidence_and_baseline_state():
    assert classify_gate_class("AVAILABLE", "SYNTHESIS_GAP") == GateClass.ENRICHMENT_TARGET.value
    assert classify_gate_class("THIN", "RICH_ENOUGH") == GateClass.RICH_CONTROL.value
    assert classify_gate_class("THIN", "EVIDENCE_GAP") == GateClass.EVIDENCE_LIMITED_CONTROL.value
    assert classify_gate_class("DATA_GAP", "EVIDENCE_GAP") == GateClass.DATA_GAP_CONTROL.value


def test_v2_core_classifier_requires_direct_passage_context():
    unit = _unit("entity-only", evidence_ids=("e",), entity_ids=("artifact",))
    evidence = [_evidence("e", entity_ids=("artifact",))]
    assert cluster_synthesis_units([unit], evidence, core_classifier=CORE_CLASSIFIER_V1)[0].quality_class == QualityClass.CORE.value
    refined = cluster_synthesis_units([unit], evidence, core_classifier=CORE_CLASSIFIER_V2)[0]
    assert refined.quality_class == QualityClass.SUPPORTING.value
    assert refined.importance_basis == ["entity_background_not_direct_passage_context"]


def test_small_cluster_comprehensive_coverage_is_not_dumping():
    units = [_unit(f"u{i}", facts=(f"Distinct fact {i}.",), evidence_ids=(f"e{i}",)) for i in range(5)]
    evidence = [_evidence(f"e{i}") for i in range(5)]
    blocks = [SimpleNamespace(text=f"Note {i}.", evidence_ids=[f"e{i}"], synthesis_ids=[f"u{i}"]) for i in range(5)]
    score = score_synthesis_richness(units, evidence_items=evidence, consumed_synthesis_ids=[u.id for u in units], blocks=blocks)
    assert score.idea_cluster_coverage == 1.0
    assert score.dump_diagnostics.severity == DumpSeverity.NONE.value


def test_dense_one_block_per_unit_with_low_consolidation_is_high():
    words = "amber cedar dune ember fjord grove harbor island jade kiln lagoon meadow north olive prairie quartz ridge summit thicket umber".split()
    units = [_unit(f"u{i}", facts=(f"{words[i]} {words[(i + 7) % 20]} {words[(i + 13) % 20]}",), evidence_ids=(f"e{i}",)) for i in range(20)]
    evidence = [_evidence(f"e{i}", parent=f"parent-{i}") for i in range(20)]
    blocks = [SimpleNamespace(text=f"A separate explanatory block with enough words {i}.", evidence_ids=[f"e{i}"], synthesis_ids=[f"u{i}"]) for i in range(20)]
    score = score_synthesis_richness(units, evidence_items=evidence, consumed_synthesis_ids=[u.id for u in units], blocks=blocks)
    # The fixture deliberately has one cluster per fact, unlike the duplicate
    # fixture used by the legacy signal tests.
    assert score.meaningful_cluster_count == 20
    assert score.dump_diagnostics.severity in {DumpSeverity.MODERATE.value, DumpSeverity.HIGH.value}
    assert score.dump_diagnostics.block_to_cluster_ratio == 1.0


def _actual_canary(book, chapter, *, core_classifier=CORE_CLASSIFIER_V2):
    root = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/canary")
    slug = book.lower().replace(" ", "_")
    synthesis = json.loads((root / "synthesis" / f"{slug}_{chapter:03d}.json").read_text())
    units = [SynthesisUnit(**value) for value in synthesis["synthesis_units"]]
    bundle = get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
    commentary = load_commentary(root / "responses/accepted", book, chapter)
    blocks = [block for section in commentary.sections for block in section.blocks]
    consumed = [sid for block in blocks for sid in block.synthesis_ids]
    score = score_synthesis_richness(units, evidence_items=bundle.evidence_items, consumed_synthesis_ids=consumed, blocks=blocks, passage_ref=f"{book} {chapter}", core_classifier=core_classifier)
    return score


def _safe_v2(score, availability, baseline, after, **kwargs):
    validation_clean = kwargs.pop("validation_clean", None)
    return assess_gate_v2(
        score=score,
        evidence_availability=availability,
        baseline_richness=baseline,
        after_richness=after,
        safety_checks={"validation_clean": True, "provenance_complete": True, "hashes_valid": True},
        validation_clean=validation_clean,
        **kwargs,
    )


def test_genesis_1_is_the_over_generation_negative_control():
    score = _actual_canary("Genesis", 1)
    result = _safe_v2(score, "AVAILABLE", "SYNTHESIS_GAP", "RICH_ENOUGH", evidence_use_delta=56, section_delta=3)
    assert score.dump_diagnostics.severity == DumpSeverity.HIGH.value
    assert result.outcome == GateOutcome.QUALITY_FAIL.value


def test_leviticus_16_uses_refined_core_and_passes_on_essential_coverage():
    score_v1 = _actual_canary("Leviticus", 16)
    root = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/canary")
    synthesis = json.loads((root / "synthesis/leviticus_016.json").read_text())
    units = [SynthesisUnit(**value) for value in synthesis["synthesis_units"]]
    bundle = get_chapter_evidence_bundle("Leviticus", 16, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
    old = score_synthesis_richness(units, evidence_items=bundle.evidence_items, core_classifier=CORE_CLASSIFIER_V1)
    assert old.core_cluster_count == 10
    assert old.consumed_core_cluster_count == 0
    assert score_v1.core_cluster_count == 2
    result = _safe_v2(score_v1, "AVAILABLE", "SYNTHESIS_GAP", "SYNTHESIS_GAP", evidence_use_delta=11, section_delta=3, boilerplate_removed=True)
    assert score_v1.core_cluster_coverage == 1.0
    assert result.outcome == GateOutcome.PASS_WITH_WARNING.value


def test_good_dense_and_control_canaries_are_not_false_quality_failures():
    two_samuel = _safe_v2(_actual_canary("2 Samuel", 6), "AVAILABLE", "SYNTHESIS_GAP", "RICH_ENOUGH", evidence_use_delta=7)
    john = _safe_v2(_actual_canary("John", 1), "AVAILABLE", "SYNTHESIS_GAP", "RICH_ENOUGH", evidence_use_delta=55, section_delta=2)
    assert two_samuel.outcome == GateOutcome.PASS_WITH_WARNING.value
    assert john.outcome == GateOutcome.PASS_WITH_WARNING.value
    assert john.dump_severity == DumpSeverity.MODERATE.value


def test_limited_and_data_gap_controls_pass_without_forced_richness():
    chronicles = _safe_v2(_actual_canary("1 Chronicles", 8), "THIN", "SYNTHESIS_GAP", "SYNTHESIS_GAP")
    numbers = _safe_v2(_actual_canary("Numbers", 3), "DATA_GAP", "EVIDENCE_GAP", "EVIDENCE_GAP", commentary_word_count=11, unique_evidence_ids_consumed=0)
    assert chronicles.gate_class == GateClass.EVIDENCE_LIMITED_CONTROL.value
    assert chronicles.outcome == GateOutcome.PASS.value
    assert numbers.gate_class == GateClass.DATA_GAP_CONTROL.value
    assert numbers.outcome == GateOutcome.PASS.value


def test_gate_v2_keeps_safety_as_a_hard_blocker():
    score = _actual_canary("Ruth", 3)
    result = _safe_v2(score, "AVAILABLE", "SYNTHESIS_GAP", "RICH_ENOUGH", validation_clean=False)
    assert result.outcome == GateOutcome.SAFETY_FAIL.value
    assert result.quality_checks


def test_gate_v1_and_v2_comparison_is_deterministic_for_leviticus():
    score = _actual_canary("Leviticus", 16)
    legacy_score = _actual_canary("Leviticus", 16, core_classifier=CORE_CLASSIFIER_V1)
    v1_pass, _ = proposed_gate_passes(score=legacy_score, evidence_availability="AVAILABLE", validation_clean=True, boilerplate_detected=False, evidence_use_delta=11)
    v2 = _safe_v2(score, "AVAILABLE", "SYNTHESIS_GAP", "SYNTHESIS_GAP", evidence_use_delta=11, section_delta=3, boilerplate_removed=True)
    assert v1_pass is False
    assert v2.outcome == GateOutcome.PASS_WITH_WARNING.value
