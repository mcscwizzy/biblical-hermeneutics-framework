"""Tests for deterministic reader-level synthesis richness diagnostics."""

from types import SimpleNamespace

from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.richness_clusters import (
    DuplicateReason,
    QualityClass,
    cluster_synthesis_units,
    proposed_gate_passes,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.synthesis.storage import load_synthesis
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


def _evidence(ident, *, parent="parent", category="history", entity_ids=(), disputed="", role=None):
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
        _evidence("e1", parent="core", category="geography", entity_ids=("place",)),
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
    evidence = [_evidence(f"e{i}") for i in range(20)]
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
