from dataclasses import replace
import json
from pathlib import Path

from bhf_agent.chapter_commentary.availability import (
    EvidenceAvailability,
    classify_evidence_availability,
    evidence_contribution,
)
from bhf_agent.chapter_commentary.evidence_applicability import (
    COMMENTARY_EVIDENCE_APPLICABILITY_VERSION,
    evaluate_evidence_applicability,
)
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis
from bhf_agent.presentation.evidence_hash import calculate_evidence_hash
from bhf_agent.presentation.models import EntityRef, EvidenceBundle, EvidenceItem


def _item(
    item_id: str,
    *,
    source_kind: str,
    scope: str,
    anchor_source: str,
    inherited=None,
    category: str = "history",
    anchor: str = "1 Samuel 21:10",
    dispute_status: str = "not_disputed",
) -> EvidenceItem:
    specificity = "verse" if ":" in anchor else "chapter"
    metadata = {
        "source_kind": source_kind,
        "applicability_scope": scope,
        "anchor_source": anchor_source,
        "anchor_specificity": specificity,
        "passage_relationship": "direct",
        "dispute_status": dispute_status,
    }
    if inherited is not None:
        metadata["inherited_from_parent"] = inherited
    return EvidenceItem(
        id=item_id,
        claim=f"Claim for {item_id}.",
        category=category,
        source_ids=["source"],
        related_entity_ids=[],
        passage_anchors=[anchor],
        confidence="low" if dispute_status == "disputed" else "high",
        relevance_metadata=metadata,
    )


def _bundle(*items: EvidenceItem, reference: str = "1 Samuel 21") -> EvidenceBundle:
    bundle = EvidenceBundle(
        passage_ref=reference,
        entities={
            "people": [],
            "places": [],
            "groups": [],
            "events": [],
            "artifacts": [],
        },
        evidence_items=list(items),
        geography={},
        provenance={},
        version="1.1",
    )
    return replace(bundle, evidence_hash=calculate_evidence_hash(bundle))


def test_legacy_person_parent_anchor_is_background_not_current_synthesis():
    item = _item(
        "person-legacy",
        source_kind="ckl_legacy_field",
        scope="entity",
        anchor_source="parent",
        inherited=True,
    )
    decision = evaluate_evidence_applicability(item, "1 Samuel 21")
    assert decision.policy_version == COMMENTARY_EVIDENCE_APPLICABILITY_VERSION
    assert decision.current_chapter_eligible is False
    assert decision.reason == "legacy_parent_inheritance_is_background_only"
    assert compile_chapter_synthesis(_bundle(item)).synthesis_units == []


def test_legacy_archaeology_parent_anchor_is_background_not_current_synthesis():
    item = _item(
        "archaeology-legacy",
        source_kind="ckl_legacy_field",
        scope="entity",
        anchor_source="parent",
        inherited=True,
        category="archaeology",
    )
    assert not compile_chapter_synthesis(_bundle(item)).synthesis_units


def test_legacy_theme_parent_anchor_is_background_not_current_synthesis():
    item = _item(
        "theme-legacy",
        source_kind="ckl_legacy_field",
        scope="global",
        anchor_source="parent",
        inherited=True,
    )
    assert not compile_chapter_synthesis(_bundle(item)).synthesis_units


def test_structured_child_verse_anchor_remains_current_chapter_eligible():
    item = _item(
        "child",
        source_kind="ckl_evidence_item",
        scope="passage",
        anchor_source="child",
    )
    decision = evaluate_evidence_applicability(item, "1 Samuel 21")
    assert decision.current_chapter_eligible is True
    assert evidence_contribution(item, "1 Samuel 21").specific is True
    assert len(compile_chapter_synthesis(_bundle(item)).synthesis_units) == 1


def test_structured_interpretive_note_with_authored_anchor_remains_eligible():
    item = _item(
        "note",
        source_kind="ckl_interpretive_note",
        scope="section",
        anchor_source="child",
        anchor="1 Samuel 21",
    )
    assert evaluate_evidence_applicability(item, "1 Samuel 21").current_chapter_eligible


def test_resolver_passage_record_remains_current_chapter_eligible():
    item = _item(
        "resolver",
        source_kind="archaeology_resolver",
        scope="passage",
        anchor_source="resolver",
        category="archaeology",
    )
    assert evaluate_evidence_applicability(item, "1 Samuel 21").current_chapter_eligible


def test_structured_disputed_evidence_preserves_dispute_and_confidence():
    item = _item(
        "disputed",
        source_kind="ckl_evidence_item",
        scope="passage",
        anchor_source="child",
        dispute_status="disputed",
    )
    unit = compile_chapter_synthesis(_bundle(item)).synthesis_units[0]
    assert unit.interpretation_level == "disputed"
    assert unit.confidence == "low"


def test_broad_book_context_is_not_promoted_to_verse_specific_availability():
    item = _item(
        "book-context",
        source_kind="ckl_claim",
        scope="book",
        anchor_source="child",
        anchor="1 Samuel 1-31",
    )
    decision = evaluate_evidence_applicability(item, "1 Samuel 21")
    contribution = evidence_contribution(item, "1 Samuel 21")
    assert decision.current_chapter_eligible is False
    assert contribution.specific is False
    assert contribution.specificity == "background:book"
    assert classify_evidence_availability(_bundle(item)) is EvidenceAvailability.THIN
    assert not compile_chapter_synthesis(_bundle(item)).synthesis_units


def test_missing_or_contradictory_applicability_fails_closed():
    missing = replace(_item("missing", source_kind="ckl_claim", scope="passage", anchor_source="child"), relevance_metadata={})
    contradictory = _item(
        "contradictory",
        source_kind="ckl_legacy_field",
        scope="passage",
        anchor_source="child",
        inherited=True,
    )
    assert evaluate_evidence_applicability(missing, "1 Samuel 21").reason == "missing_applicability_scope"
    assert evaluate_evidence_applicability(contradictory, "1 Samuel 21").current_chapter_eligible is False
    assert not compile_chapter_synthesis(_bundle(missing, contradictory)).synthesis_units


def test_numbers_controls_retain_authored_passage_paths():
    root = Path(__file__).resolve().parents[1]
    paths = {
        "Numbers 1": root / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-008/evidence-bundles/numbers_001.json",
        "Numbers 2": root / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-scale-pilot/wave-a/canary/evidence-bundles/numbers_002.json",
    }
    for reference, path in paths.items():
        raw = json.loads(path.read_text())
        bundle = EvidenceBundle(
            passage_ref=raw["passage_ref"],
            entities={bucket: [EntityRef(**value) for value in raw["entities"].get(bucket, [])] for bucket in ("people", "places", "groups", "events", "artifacts")},
            evidence_items=[EvidenceItem(**value) for value in raw["evidence_items"]],
            geography=raw.get("geography", {}),
            provenance=raw.get("provenance", {}),
            version=raw.get("version", "1.0"),
            evidence_hash=raw.get("evidence_hash", ""),
        )
        book, chapter = reference.rsplit(" ", 1)
        synthesis = compile_chapter_synthesis(bundle, book=book, chapter=int(chapter))
        assert len(synthesis.synthesis_units) > 0
        assert all(unit.passage_scope == "CURRENT_CHAPTER" for unit in synthesis.synthesis_units)
        assert all(evaluate_evidence_applicability(item, reference).current_chapter_eligible for item in bundle.evidence_items)
