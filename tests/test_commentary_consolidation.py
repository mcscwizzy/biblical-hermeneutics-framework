"""Focused tests for deterministic reader-level consolidation diagnostics."""

from pathlib import Path
from types import SimpleNamespace

from bhf_agent.chapter_commentary.consolidation import (
    BlockConsolidationRecord,
    audit_prose_overlap,
    consolidation_metrics,
    map_commentary_blocks,
)
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.chapter_commentary.synthesis.models import SynthesisUnit
from bhf_agent.chapter_commentary.synthesis.storage import load_synthesis
from bhf_agent.chapter_commentary.richness_clusters import cluster_synthesis_units
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION, EvidenceItem


def _unit(ident, *, facts, evidence_ids):
    return SimpleNamespace(
        id=ident,
        kind="historical_context",
        facts=list(facts),
        evidence_ids=list(evidence_ids),
        entity_ids=[],
        related_unit_ids=[],
        passage_scope="CURRENT_CHAPTER",
        interpretation_level="fact",
        metadata={},
    )


def _evidence(ident, parent):
    return EvidenceItem(
        id=ident,
        claim="Supported claim.",
        category="history",
        source_ids=["source"],
        related_entity_ids=[],
        passage_anchors=["Genesis 1:1"],
        confidence="high",
        relevance_metadata={"parent_object_id": parent},
    )


def test_mapping_counts_units_and_evidence_and_clusters():
    units = [
        _unit("u1", facts=["A shared fact."], evidence_ids=["e1"]),
        _unit("u2", facts=["A shared fact."], evidence_ids=["e1"]),
        _unit("u3", facts=["A different fact."], evidence_ids=["e2", "e3"]),
    ]
    commentary = SimpleNamespace(
        sections=[
            SimpleNamespace(
                kind="historical_context",
                blocks=[
                    SimpleNamespace(
                        id="block_1",
                        text="Shared explanation.",
                        verse_refs=["Genesis 1:1"],
                        synthesis_ids=["u1", "u2"],
                        evidence_ids=["e1"],
                    ),
                    SimpleNamespace(
                        id="block_2",
                        text="Different explanation.",
                        verse_refs=["Genesis 1:2"],
                        synthesis_ids=["u3"],
                        evidence_ids=["e2", "e3"],
                    ),
                ],
            )
        ]
    )
    records, clusters = map_commentary_blocks(
        commentary, units, [_evidence("e1", "same"), _evidence("e2", "two"), _evidence("e3", "three")]
    )
    assert records[0].synthesis_unit_count == 2
    assert records[0].evidence_record_count == 1
    assert len(records[0].idea_cluster_ids) == 1
    assert records[1].evidence_record_count == 2
    metrics = consolidation_metrics(records, clusters)
    assert metrics["SYNTHESIS_UNITS_PER_BLOCK"] == 1.5
    assert metrics["IDEA_CLUSTERS_PER_BLOCK"] == 1.0


def test_prose_overlap_is_deterministic_and_classified_without_an_llm():
    blocks = [
        BlockConsolidationRecord("context", "a", [], [], [], 8, [], 0, 0, [], "Royal imagery extends dignity to all people."),
        BlockConsolidationRecord("context", "b", [], [], [], 8, [], 0, 0, [], "Royal imagery extends dignity to all people."),
        BlockConsolidationRecord("context", "c", [], [], [], 8, [], 0, 0, [], "A distinct note concerns harvest timing."),
    ]
    overlaps = audit_prose_overlap(blocks)
    assert overlaps[0].classification == "NEAR_DUPLICATE"
    assert overlaps[1].classification == "DISTINCT"
    assert overlaps == audit_prose_overlap(list(reversed(blocks)))


def _actual_canary(book, chapter):
    root = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/canary")
    synthesis = load_synthesis(root / "synthesis", book, chapter)
    commentary = load_commentary(root / "responses/accepted", book, chapter)
    bundle = get_chapter_evidence_bundle(
        book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    records, clusters = map_commentary_blocks(
        commentary, synthesis.synthesis_units, bundle.evidence_items
    )
    return consolidation_metrics(records, clusters, audit_prose_overlap(records))


def test_genesis_1_is_exhaustive_at_the_block_level():
    metrics = _actual_canary("Genesis", 1)
    assert metrics["consumed_synthesis_unit_count"] == 49
    assert metrics["consumed_idea_cluster_count"] == 25
    assert metrics["exactly_one_synthesis_unit_blocks"] == 49
    assert metrics["multi_synthesis_unit_blocks"] == 0
    assert metrics["SYNTHESIS_UNITS_PER_BLOCK"] == 1.0
    assert metrics["BLOCKS_PER_IDEA_CLUSTER"] == 1.96


def test_two_samuel_6_remains_a_small_natural_control():
    metrics = _actual_canary("2 Samuel", 6)
    assert metrics["block_count"] == 11
    assert metrics["word_count"] == 270
    assert metrics["consumed_synthesis_unit_count"] == 11
    assert metrics["consumed_idea_cluster_count"] == 6
    assert metrics["word_count"] < 300


def test_leviticus_16_exposes_real_multi_unit_consolidation():
    metrics = _actual_canary("Leviticus", 16)
    assert metrics["multi_synthesis_unit_blocks"] == 4
    assert metrics["SYNTHESIS_UNITS_PER_BLOCK"] > 1.0
    assert metrics["REDUNDANT_BLOCK_RATIO"] == 0.0


def test_small_revelation_control_does_not_trigger_density_by_size():
    metrics = _actual_canary("Revelation", 12)
    assert metrics["block_count"] == 5
    assert metrics["word_count"] == 124
    assert metrics["REDUNDANT_BLOCK_RATIO"] == 0.4
