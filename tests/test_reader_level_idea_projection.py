"""Focused contract tests for reader-level idea projection v1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import pytest

from framework.commentary.production.inputs import prepare_chapter
from bhf_agent import bible
from bhf_agent.chapter_commentary.prompts import build_user_prompt, system_prompt_for_version
from bhf_agent.chapter_commentary.reader_level_projection import (
    ProjectionError,
    add_projection_to_prompt,
    project_reader_level_ideas,
)
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    RICHNESS_GATE_V2_VERSION,
    RICHNESS_POLICY_VERSION_V3,
    SynthesisIdeaCluster,
    cluster_synthesis_units,
)
from bhf_agent.chapter_commentary.synthesis.models import (
    CompiledChapterSynthesis,
    SynthesisCoverage,
    SynthesisUnit,
)
from bhf_agent.presentation.models import EvidenceItem


ROOT = Path(__file__).resolve().parents[1]
PROMPT_17_ROOT = (
    ROOT
    / ".bhf-data/bhf-commentary-candidates/renderer-remediation-prompt-1.7-selection-breadth-7e1f844705a27ef5d2a1"
)


@lru_cache(maxsize=None)
def _prepared(book: str, chapter: int):
    return prepare_chapter(book, chapter)


def _projection(book: str, chapter: int):
    prepared = _prepared(book, chapter)
    chapter_text = bible.passage_text(
        bible.resolve_chapter(book, chapter)["verses"]
    )
    clusters = cluster_synthesis_units(
        prepared.synthesis.synthesis_units,
        prepared.bundle.evidence_items,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=chapter_text,
    )
    return prepared, clusters, project_reader_level_ideas(
        prepared.synthesis, clusters, prepared.bundle.evidence_items
    )


def test_projection_identity_is_deterministic():
    first = _projection("Revelation", 21)[2]
    second = _projection("Revelation", 21)[2]
    assert first.to_dict() == second.to_dict()
    assert first.projection_hash == second.projection_hash


def test_grouping_is_stable_when_cluster_input_order_changes():
    prepared, clusters, first = _projection("Revelation", 21)
    reversed_projection = project_reader_level_ideas(
        prepared.synthesis,
        list(reversed(clusters)),
        list(reversed(prepared.bundle.evidence_items)),
    )
    assert first.to_dict() == reversed_projection.to_dict()


def test_revelation_21_dense_projection_compresses_without_forcing_count():
    _, _, projection = _projection("Revelation", 21)
    assert projection.source_synthesis_unit_count == 119
    assert projection.eligible_cluster_count == 16
    assert len(projection.ideas) == 8
    assert sum(idea.importance == "CORE" for idea in projection.ideas) == 0
    assert sum(idea.importance == "RELEVANT" for idea in projection.ideas) == 8
    assert sum(audit.decision == "GROUP" for audit in projection.pair_audit) == 23


def test_revelation_20_control_projection_is_smaller_and_ancestry_complete():
    _, _, projection = _projection("Revelation", 20)
    assert projection.source_synthesis_unit_count == 21
    assert projection.eligible_cluster_count == 6
    assert len(projection.ideas) == 4
    assert projection.ancestry_audit["eligible_cluster_ids_preserved"] is True
    assert projection.ancestry_audit["synthesis_unit_ids_preserved"] is True
    assert projection.ancestry_audit["evidence_ids_preserved"] is True


def test_sparse_exodus_control_does_not_inflate():
    _, _, projection = _projection("Exodus", 14)
    assert projection.source_synthesis_unit_count == 34
    assert projection.eligible_cluster_count == 2
    assert len(projection.ideas) == 2
    assert sum(idea.importance == "CORE" for idea in projection.ideas) == 1
    assert sum(idea.importance == "RELEVANT" for idea in projection.ideas) == 1
    assert not any(audit.decision == "GROUP" for audit in projection.pair_audit)


def test_all_eligible_ancestry_and_evidence_are_preserved():
    _, _, projection = _projection("Revelation", 21)
    assert projection.ancestry_audit == {
        **projection.ancestry_audit,
        "eligible_cluster_ids_preserved": True,
        "synthesis_unit_ids_preserved": True,
        "evidence_ids_preserved": True,
        "invented_synthesis_ids": [],
        "invented_evidence_ids": [],
    }


def test_core_importance_is_promoted_only_from_existing_required_core_cluster():
    _, _, projection = _projection("Exodus", 14)
    core = [idea for idea in projection.ideas if idea.importance == "CORE"]
    assert len(core) == 1
    assert core[0].cluster_ids == ["idea_cluster_304529f2e7f4"]


def test_ambiguous_fact_overlap_remains_separate():
    synthesis = _synthetic_synthesis(
        SynthesisUnit(
            id="syn_culture",
            kind="cultural_context",
            facts=["The temple has a court for worship and sacrifice."],
            verse_refs=["Test 1:1"],
            evidence_ids=["e_culture"],
            entity_ids=[],
        ),
        SynthesisUnit(
            id="syn_history",
            kind="historical_context",
            facts=["The temple has a court for worship and sacrifice."],
            verse_refs=["Test 1:1"],
            evidence_ids=["e_history"],
            entity_ids=[],
        ),
    )
    clusters = [
        _cluster("cluster_culture", "syn_culture", "e_culture", "culture"),
        _cluster("cluster_history", "syn_history", "e_history", "history"),
    ]
    projection = project_reader_level_ideas(
        synthesis,
        clusters,
        [
            _evidence("e_culture", "culture"),
            _evidence("e_history", "history"),
        ],
    )
    assert len(projection.ideas) == 2
    assert projection.pair_audit[0].decision == "KEEP_SEPARATE_AMBIGUOUS"
    assert len(projection.ambiguous_cluster_ids) == 2


def test_scope_boundary_prevents_current_and_surrounding_merge():
    synthesis = _synthetic_synthesis(
        replace(
            _unit("syn_current", "e_current", "Current temple presence."),
            passage_scope="CURRENT_CHAPTER",
        ),
        replace(
            _unit("syn_surrounding", "e_surrounding", "Current temple presence."),
            passage_scope="SURROUNDING_PASSAGE",
        ),
    )
    clusters = [
        _cluster("cluster_current", "syn_current", "e_current", "culture"),
        _cluster("cluster_surrounding", "syn_surrounding", "e_surrounding", "culture", scope="SURROUNDING_PASSAGE"),
    ]
    evidence = [
        _evidence("e_current", "culture", parent="temple"),
        _evidence("e_surrounding", "culture", parent="temple"),
    ]
    projection = project_reader_level_ideas(synthesis, clusters, evidence)
    assert len(projection.ideas) == 2
    assert projection.pair_audit[0].reason == "SCOPE_BOUNDARY"


def test_unknown_synthesis_id_is_rejected():
    synthesis = _synthetic_synthesis(_unit("syn_known", "e1", "Known."))
    cluster = _cluster("cluster", "syn_missing", "e1", "culture")
    with pytest.raises(ProjectionError, match="unknown synthesis IDs"):
        project_reader_level_ideas(synthesis, [cluster], [_evidence("e1", "culture")])


def test_evidence_outside_synthesis_ancestry_is_rejected():
    synthesis = _synthetic_synthesis(_unit("syn_known", "e1", "Known."))
    cluster = _cluster("cluster", "syn_known", "invented", "culture")
    with pytest.raises(ProjectionError, match="outside unit ancestry"):
        project_reader_level_ideas(synthesis, [cluster], [_evidence("e1", "culture")])


def test_projection_prompt_view_retains_full_synthesis_and_is_variant_only():
    prepared, _, projection = _projection("Revelation", 21)
    chapter = bible.resolve_chapter("Revelation", 21)
    canonical_text = bible.passage_text(chapter["verses"])
    original = build_user_prompt(
        "Revelation 21",
        "Revelation",
        21,
        canonical_text,
        prepared.synthesis,
        prepared.bundle,
        prepared.synthesis.evidence_availability,
        prompt_version="1.7",
    )
    variant = add_projection_to_prompt(original, projection)
    assert "DISTINCT READER-LEVEL IDEAS" not in original
    assert "DISTINCT READER-LEVEL IDEAS" in variant
    assert "COMPILED CHAPTER SYNTHESIS:" in variant
    assert prepared.synthesis.synthesis_hash in variant
    assert variant != original


def test_prompt_1_7_frozen_packet_is_unchanged():
    prepared = _prepared("Revelation", 21)
    chapter = bible.resolve_chapter("Revelation", 21)
    canonical_text = bible.passage_text(chapter["verses"])
    prompt = build_user_prompt(
        "Revelation 21",
        "Revelation",
        21,
        canonical_text,
        prepared.synthesis,
        prepared.bundle,
        prepared.synthesis.evidence_availability,
        prompt_version="1.7",
    )
    packet = json.loads(
        (PROMPT_17_ROOT / "packets/005_revelation_021.json").read_text()
    )
    assert hashlib.sha256(prompt.encode()).hexdigest() == packet["user_prompt_sha256"]
    assert hashlib.sha256(system_prompt_for_version("1.7").encode()).hexdigest() == packet["system_prompt_sha256"]


def test_scoring_contract_constants_remain_frozen():
    assert RICHNESS_CLUSTER_AUDIT_VERSION_V2 == "commentary-richness-clusters-v2"
    assert RICHNESS_POLICY_VERSION_V3 == "commentary-richness-policy-v3-reader-relevance"
    assert RICHNESS_GATE_V2_VERSION == "commentary-richness-gate-v2.1"


def _unit(unit_id: str, evidence_id: str, fact: str) -> SynthesisUnit:
    return SynthesisUnit(
        id=unit_id,
        kind="cultural_context",
        facts=[fact],
        verse_refs=["Test 1:1"],
        evidence_ids=[evidence_id],
        entity_ids=[],
    )


def _evidence(evidence_id: str, category: str, *, parent: str | None = None) -> EvidenceItem:
    return EvidenceItem(
        id=evidence_id,
        claim="A supplied fact.",
        category=category,
        source_ids=["source"],
        related_entity_ids=[],
        passage_anchors=["Test 1:1"],
        confidence="high",
        relevance_metadata={"parent_object_id": parent} if parent else {},
    )


def _cluster(
    cluster_id: str,
    synthesis_id: str,
    evidence_id: str,
    category: str,
    *,
    scope: str = "CURRENT_CHAPTER",
) -> SynthesisIdeaCluster:
    return SynthesisIdeaCluster(
        id=cluster_id,
        kind="cultural_context",
        synthesis_ids=[synthesis_id],
        evidence_ids=[evidence_id],
        passage_scope=scope,
        concept_signature="",
        importance_weight=0.7,
        duplicate_reason="DISTINCT",
        confidence="high",
        quality_class="SUPPORTING",
        unit_kinds=["cultural_context"],
        categories=[category],
        importance_basis=[],
        dispute_present=False,
        coverage_eligibility="RELEVANT",
        coverage_eligibility_basis=[],
    )


def _synthetic_synthesis(*units: SynthesisUnit) -> CompiledChapterSynthesis:
    return CompiledChapterSynthesis(
        reference="Test 1",
        book="Test",
        chapter=1,
        evidence_hash="evidence-hash",
        evidence_bundle_version="1.1",
        synthesis_schema_version="1.1",
        synthesis_compiler_version="1.1",
        synthesis_hash="synthesis-hash",
        evidence_availability="AVAILABLE",
        synthesis_units=list(units),
        evidence_gaps=[],
        coverage=SynthesisCoverage(
            evidence_item_count=len(units),
            used_evidence_ids=[unit.evidence_ids[0] for unit in units],
            unused_evidence_ids=[],
            evidence_categories={},
            category_diversity=0,
            specific_evidence_count=0,
            entity_counts={},
            unit_kind_counts={},
            relationship_unit_count=0,
        ),
    )
