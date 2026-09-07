from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from bhf_agent import bible
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.genre import CANONICAL_BOOK_GENRE_BUCKETS, classify_genre
from bhf_agent.models import ReferenceContext
from bhf_agent.presentation.evidence import build_evidence_bundle
from bhf_agent.presentation.evidence_hash import calculate_evidence_hash
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION, EvidenceItem
from bhf_agent.presentation.relevance import (
    DIRECT_CONTEXT,
    LATER_RECEPTION,
    is_semantically_relevant,
)
from tools.commentary_v11_canary import (
    _block_for_item,
    _interpretation_level,
    eligible_for_section,
    select_overview_item,
)


def _item(
    item_id: str,
    *,
    claim: str = "Claim",
    category: str = "history",
    anchors: list[str] | None = None,
    relationship: str = DIRECT_CONTEXT,
    assertion_type: str = "",
    dispute_status: str = "not_disputed",
    confidence: str = "high",
) -> EvidenceItem:
    return EvidenceItem(
        id=item_id,
        claim=claim,
        category=category,
        source_ids=[f"source:{item_id}"],
        related_entity_ids=[],
        passage_anchors=anchors or ["Genesis 1:3"],
        confidence=confidence,
        relevance_metadata={
            "semantic_relationship": relationship,
            "assertion_type": assertion_type,
            "dispute_status": dispute_status,
            "anchor_specificity": "verse",
        },
    )


def test_genesis_1_excludes_confirmed_archaeology_misanchors():
    bundle = get_chapter_evidence_bundle(
        "Genesis", 1, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    ids = {item.id for item in bundle.evidence_items}
    assert not any(item.startswith("arad-ostraca:") for item in ids)
    assert not any(item.startswith("caesarea-maritima-excavations:") for item in ids)


def test_later_pauline_reuse_is_retained_but_not_overview_context():
    bundle = get_chapter_evidence_bundle(
        "Genesis", 1, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    item = bundle.evidence_by_id["2-corinthians:interpretive_note:21"]
    assert item.relevance_metadata["semantic_relationship"] == LATER_RECEPTION
    assert not eligible_for_section(item, "chapter_overview")
    assert eligible_for_section(item, "dig_deeper")
    assert select_overview_item(bundle).id != item.id


def test_overview_selection_is_not_array_order_dependent():
    direct = _item("direct", claim="Direct chapter context")
    later = _item("later", relationship=LATER_RECEPTION, claim="Later reuse")
    bundle = SimpleNamespace(evidence_items=[later, direct])
    assert select_overview_item(bundle).id == "direct"
    bundle = SimpleNamespace(evidence_items=[direct, later])
    assert select_overview_item(bundle).id == "direct"


def test_precise_evidence_anchor_is_preserved_in_compiler_block():
    item = _item("precise", anchors=["Genesis 1:26-27"])
    block = _block_for_item(item, 0)
    assert block.verse_refs == ["Genesis 1:26-27"]


def test_interpretation_mapping_preserves_fact_inference_and_disputed():
    assert _interpretation_level(_item("fact", assertion_type="textual-observation")) == "fact"
    assert _interpretation_level(_item("inference", assertion_type="inference")) == "inference"
    assert _interpretation_level(_item("disputed", assertion_type="fact", dispute_status="major_scholarly_disagreement")) == "disputed"


def test_all_canonical_books_resolve_to_expected_genre_bucket():
    books = [book["name"] for book in bible.list_books()]
    assert set(books) == set(CANONICAL_BOOK_GENRE_BUCKETS)
    for book in books:
        result = classify_genre(ReferenceContext(book=book))
        assert result.primary_genre == CANONICAL_BOOK_GENRE_BUCKETS[book], book


def test_song_of_songs_is_poetry():
    assert classify_genre(ReferenceContext(book="Song of Songs")).primary_genre == "poetry"


def test_semantic_relevance_controls_regeneration_eligibility():
    good = _item("good")
    bad = _item("bad", relationship="SEMANTICALLY_MISANCHORED")
    assert is_semantically_relevant(good)
    assert not is_semantically_relevant(bad)


def test_evidence_hash_ignores_retrieval_score_but_includes_semantic_role():
    item = _item("hash", assertion_type="inference")
    bundle = build_evidence_bundle(
        "Genesis 1",
        canonical_results=[],
        bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
    )
    changed_score = replace(item, relevance_metadata={**item.relevance_metadata, "retrieval_score": 0.1})
    changed_score_bundle = replace(bundle, evidence_items=[changed_score])
    baseline_bundle = replace(bundle, evidence_items=[item])
    assert calculate_evidence_hash(baseline_bundle) == calculate_evidence_hash(changed_score_bundle)
    changed_role = replace(
        item,
        relevance_metadata={**item.relevance_metadata, "semantic_relationship": LATER_RECEPTION},
    )
    assert calculate_evidence_hash(baseline_bundle) != calculate_evidence_hash(
        replace(bundle, evidence_items=[changed_role])
    )


def test_zephaniah_1_and_1_samuel_28_controls_remain_semantically_bounded():
    zephaniah = get_chapter_evidence_bundle(
        "Zephaniah", 1, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    samuel = get_chapter_evidence_bundle(
        "1 Samuel", 28, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    assert len(zephaniah.evidence_items) > 0
    assert len(samuel.evidence_items) == 2
    apparition = samuel.evidence_by_id["1-samuel:interpretive_note:3"]
    assert apparition.relevance_metadata["dispute_status"] == "denominational_disagreement"
    assert _interpretation_level(apparition) == "disputed"


def test_numbers_3_remains_data_gap():
    bundle = get_chapter_evidence_bundle(
        "Numbers", 3, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    assert bundle.evidence_items == []


def test_candidate_bundle_version_is_explicitly_v11():
    bundle = get_chapter_evidence_bundle(
        "Genesis", 1, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    assert bundle.version == "1.1"
    assert bundle.evidence_hash_version == "2"
