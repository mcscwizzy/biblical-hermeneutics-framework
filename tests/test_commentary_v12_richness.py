"""Tests for deterministic evidence-gap versus synthesis-gap reporting."""

from types import SimpleNamespace

from bhf_agent.chapter_commentary.models import ChapterCommentary, CommentaryBlock, CommentarySection
from bhf_agent.chapter_commentary.richness import (
    RichnessStatus,
    audit_chapter,
    classify_richness,
)
from bhf_agent.presentation.models import EvidenceBundle, EvidenceItem


def _bundle(count=2):
    items = [
        EvidenceItem(
            id=f"evidence-{index}",
            claim=f"Supported contextual fact {index}.",
            category="history" if index == 0 else "culture",
            source_ids=["source"],
            related_entity_ids=[],
            passage_anchors=[f"Genesis 1:{index + 1}"],
            confidence="high",
            relevance_metadata={},
        )
        for index in range(count)
    ]
    return EvidenceBundle(
        passage_ref="Genesis 1",
        entities={"people": [], "places": [], "groups": [], "events": [], "artifacts": []},
        evidence_items=items,
        geography={},
        provenance={},
        evidence_hash="a" * 64,
    )


def _commentary(text, evidence_ids, *, sections=1):
    section_values = []
    for index in range(sections):
        section_values.append(
            CommentarySection(
                kind="historical_context",
                title="Context",
                blocks=[
                    CommentaryBlock(
                        id=f"block-{index}",
                        text=text,
                        verse_refs=["Genesis 1:1-2"],
                        evidence_ids=evidence_ids,
                        confidence="high",
                        interpretation_level="fact",
                    )
                ],
            )
        )
    return ChapterCommentary("Genesis 1", "Genesis", 1, "validated", sections=section_values)


def test_data_gap_is_an_evidence_gap():
    result, _ = classify_richness(
        evidence_availability="DATA_GAP",
        evidence_count=0,
        evidence_score=0,
        specific_evidence_count=0,
        category_diversity=0,
        contextually_thin=False,
    )
    assert result is RichnessStatus.EVIDENCE_GAP


def test_available_minimal_commentary_is_a_synthesis_gap():
    row = audit_chapter("Genesis", 1, _commentary("Supported.", ["evidence-0"]), _bundle())
    assert row["evidence_availability"] == "AVAILABLE"
    assert row["richness_status"] == "SYNTHESIS_GAP"
    assert row["validated_but_contextually_thin"] is True


def test_fallback_boilerplate_is_detected_deterministically():
    text = (
        "Read the chapter with this setting in view. "
        "It gives a starting point for following the chapter's own movement."
    )
    first = audit_chapter("Genesis", 1, _commentary(text, ["evidence-0", "evidence-1"]), _bundle())
    second = audit_chapter("Genesis", 1, _commentary(text, ["evidence-0", "evidence-1"]), _bundle())
    assert first == second
    assert first["boilerplate_detected"] is True
    assert first["richness_status"] == "SYNTHESIS_GAP"


def test_genuinely_explanatory_supported_commentary_is_rich_enough():
    text = " ".join(
        [
            "The two supplied contextual facts illuminate different parts of the chapter and their relationship.",
            "The historical setting identifies the circumstances assumed by the passage, while the cultural detail",
            "explains a practice that an ordinary modern reader may not recognize. Reading them together clarifies",
            "why the sequence is intelligible without adding a motive, date, or theological conclusion not supplied",
            "by the evidence. The explanation remains bounded by the cited facts and by the chapter's own wording.",
        ]
    )
    row = audit_chapter(
        "Genesis", 1, _commentary(text, ["evidence-0", "evidence-1"], sections=2), _bundle()
    )
    assert row["richness_status"] == "RICH_ENOUGH"
    assert row["unique_evidence_ids_consumed"] == 2


def test_meaningful_thin_evidence_can_be_a_synthesis_gap_not_evidence_gap():
    result, _ = classify_richness(
        evidence_availability="THIN",
        evidence_count=1,
        evidence_score=1.0,
        specific_evidence_count=1,
        category_diversity=1,
        contextually_thin=True,
    )
    assert result is RichnessStatus.SYNTHESIS_GAP
