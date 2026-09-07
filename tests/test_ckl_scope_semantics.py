from __future__ import annotations

from types import SimpleNamespace

from bhf_agent.presentation.evidence import build_evidence_bundle
from bhf_agent.presentation.models import EvidenceBundle, EvidenceItem
from bhf_agent.presentation.relevance import applicability_scope
from framework.canonical_library.evidence import rank_claims


def _source(source_id: str, *, locator: str = "") -> dict[str, object]:
    return {"id": source_id, "title": source_id, "source_type": "reference-work", "locator": locator}


def _parent(
    object_id: str,
    object_type: str,
    references: list[str],
    *,
    sources: list[dict[str, object]] | None = None,
    historical_context: list[str] | None = None,
    evidence_items: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": object_id,
        "type": object_type,
        "title": object_id,
        "scripture_references": [{"reference": value, "relationship": "primary", "notes": "authored"} for value in references],
        "sources": sources or [_source(f"source-{object_id}")],
        "historical_context": historical_context or [],
        "evidence_items": evidence_items or [],
        "claims": [],
        "interpretive_notes": [],
    }


def _child(item_id: str, reference: str) -> dict[str, object]:
    return {
        "id": item_id,
        "title": item_id,
        "evidence_type": "historical-event",
        "description": "A passage-specific authored child.",
        "assertion_type": "secondary-evidence",
        "confidence": "high",
        "confidence_rationale": "fixture",
        "passage_relevance": "The child is linked to the requested passage.",
        "scripture_references": [{
            "reference": reference,
            "relationship": "direct",
            "temporal_relation": "contemporary",
            "relevance_rationale": "fixture",
        }],
        "source_ids": ["source-child"],
    }


def test_legacy_word_study_parent_does_not_become_passage_evidence():
    parent = _parent(
        "mishpat",
        "word_study",
        ["Deuteronomy 32:3-4", "Romans 2:1-11"],
        historical_context=["A broad lexical explanation."],
    )
    bundle = build_evidence_bundle("Romans 2", canonical_results=[SimpleNamespace(object=parent, score=1.0)])
    assert bundle.evidence_items == []


def test_structured_child_keeps_its_explicit_passage_scope_under_reused_parent():
    parent = _parent(
        "justice-theme",
        "theme",
        ["Deuteronomy 32:3-4", "Romans 2:1-11", "Revelation 19:1-2"],
        evidence_items=[_child("romans-justice", "Romans 2:1-11")],
    )
    bundle = build_evidence_bundle("Romans 2", canonical_results=[SimpleNamespace(object=parent, score=1.0)])
    item = next(item for item in bundle.evidence_items if item.id == "romans-justice")
    assert item.passage_anchors == ["Romans 2:1-11"]
    assert item.relevance_metadata["applicability_scope"] == "passage"
    assert item.relevance_metadata["anchor_source"] == "child"


def test_global_legacy_background_is_explicitly_non_passage_scope():
    parent = _parent(
        "resurrection-doctrine",
        "theology",
        ["Daniel 12:1-3", "Romans 6:1-11", "Revelation 21:1-5"],
        historical_context=["A broad canonical background note."],
    )
    bundle = build_evidence_bundle("Romans 6", canonical_results=[SimpleNamespace(object=parent, score=1.0)])
    item = next(item for item in bundle.evidence_items if item.id == "resurrection-doctrine:historical_context:0")
    assert item.relevance_metadata["applicability_scope"] == "global"
    assert item.relevance_metadata["inherited_from_parent"] is True


def test_rank_claims_rejects_parent_related_claim_without_passage_anchor():
    parent = {
        "id": "theme",
        "title": "Theme",
        "type": "theme",
        "claims": [{
            "id": "broad-claim",
            "claim": "A concept related to resurrection.",
            "claim_type": "theological",
            "certainty": "probable",
            "dispute_status": "not_disputed",
            "source_ids": ["source"],
        }],
        "sources": [{"id": "source", "title": "Source"}],
    }
    assert rank_claims("What is Romans 6 about?", parent, scripture_references=["Romans 6"]) == []


def test_source_collisions_have_order_independent_bundle_hash():
    first_child = _child("a-child", "Genesis 1:1")
    first_child["source_ids"] = ["shared"]
    second_child = _child("b-child", "Genesis 1:1")
    second_child["source_ids"] = ["shared"]
    first = _parent(
        "a",
        "theme",
        ["Genesis 1:1"],
        sources=[_source("shared", locator="A")],
        evidence_items=[first_child],
    )
    second = _parent(
        "b",
        "theme",
        ["Genesis 1:1"],
        sources=[_source("shared", locator="B")],
        evidence_items=[second_child],
    )
    one = build_evidence_bundle("Genesis 1", canonical_results=[SimpleNamespace(object=first, score=1.0), SimpleNamespace(object=second, score=0.5)])
    two = build_evidence_bundle("Genesis 1", canonical_results=[SimpleNamespace(object=second, score=0.5), SimpleNamespace(object=first, score=1.0)])
    assert one.evidence_hash == two.evidence_hash
    shared = next(source for source in one.provenance["sources"] if source["id"] == "shared")
    assert shared["canonical_object_ids"] == ["a", "b"]
    assert len(shared["canonical_source_variants"]) == 2


def test_applicability_scope_fails_closed_for_unknown_inheritance():
    assert applicability_scope(
        "Genesis 1",
        anchors=["Genesis 1:1"],
        metadata={"source_kind": "ckl_legacy_field", "parent_type": "unknown"},
        inherited=True,
    ) == "global"
