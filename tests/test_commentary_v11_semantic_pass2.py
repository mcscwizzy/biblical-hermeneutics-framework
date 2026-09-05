from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from tools.commentary_v11_canary import (
    _section_for_item,
    _select_section_kinds,
    select_overview_item,
)


def _bundle(book: str, chapter: int):
    return get_chapter_evidence_bundle(
        book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )


def test_genesis_word_studies_are_not_false_first_audience_language_context():
    bundle = _bundle("Genesis", 1)
    ids = {item.id for item in bundle.evidence_items}
    assert not any(item.startswith("parakletos:") for item in ids)
    assert not any(item.startswith("katabole:") for item in ids)
    assert not any(item.startswith("pneuma:") for item in ids)


def test_word_study_relationships_distinguish_direct_and_translation_comparison():
    bundle = _bundle("Psalms", 1)
    torah = bundle.evidence_by_id["torah:historical_context:0"]
    makarios = bundle.evidence_by_id["makarios:historical_context:0"]
    nomos = bundle.evidence_by_id["nomos:historical_context:0"]
    assert torah.relevance_metadata["semantic_relationship"] == "DIRECT_CONTEXT"
    assert torah.relevance_metadata["presentation_role"] == "language_literary"
    assert makarios.relevance_metadata["semantic_relationship"] == "COMPARATIVE_CONTEXT"
    assert nomos.relevance_metadata["semantic_relationship"] == "COMPARATIVE_CONTEXT"
    assert _section_for_item(makarios) == "dig_deeper"


def test_luke_acts_relation_is_not_archaeology():
    item = _bundle("Luke", 1).evidence_by_id["luke-acts-relation"]
    assert item.category == "geography"
    assert item.relevance_metadata["presentation_role"] == "language_literary"
    assert _section_for_item(item) == "language_literary"


def test_leviticus_sacrifice_background_is_historical_context():
    item = _bundle("Leviticus", 1).evidence_by_id[
        "what-is-sacrifice-in-the-bible:ancient_near_east_context:0"
    ]
    assert item.relevance_metadata["presentation_role"] == "historical_context"
    assert _section_for_item(item) == "historical_context"


def test_zephaniah_overview_prefers_chapter_context_over_textual_witnesses():
    bundle = _bundle("Zephaniah", 1)
    overview = select_overview_item(bundle)
    assert overview is not None
    assert overview.id != "zephaniah-textual-witnesses"
    assert overview.id in {"zephaniah-date", "zephaniah-superscription", "zephaniah-cult"}


def test_overview_meaningful_priority_precedes_evidence_id():
    weak_id = SimpleNamespace(
        id="z-weak",
        claim="Textual witnesses",
        category="history",
        confidence="high",
        passage_anchors=["Genesis 1:1"],
        relevance_metadata={
            "semantic_relationship": "DIRECT_CONTEXT",
            "presentation_role": "historical_context",
            "overview_priority": 40,
            "anchor_specificity": "verse",
        },
    )
    strong_id = SimpleNamespace(
        id="a-strong",
        claim="Josiah-era historical setting",
        category="history",
        confidence="high",
        passage_anchors=["Genesis 1:1"],
        relevance_metadata={
            "semantic_relationship": "DIRECT_CONTEXT",
            "presentation_role": "historical_context",
            "overview_priority": 90,
            "anchor_specificity": "verse",
        },
    )
    assert select_overview_item(SimpleNamespace(evidence_items=[weak_id, strong_id])).id == "a-strong"


def test_dig_deeper_reserves_a_slot_only_when_present():
    grouped = {kind: [object()] for kind in (
        "historical_context",
        "archaeology_geography",
        "language_literary",
        "chronology",
        "dig_deeper",
    )}
    selected = _select_section_kinds(grouped, 4)
    assert selected == ["historical_context", "archaeology_geography", "language_literary", "dig_deeper"]
    assert _select_section_kinds({"historical_context": [object()]}, 4) == ["historical_context"]


def test_presentation_role_changes_are_part_of_v11_grounding_identity():
    from dataclasses import replace
    from tests.test_commentary_v11_semantic import _item
    from bhf_agent.presentation.evidence_hash import calculate_evidence_hash
    from bhf_agent.presentation.models import EvidenceBundle

    item = _item("role", category="history")
    bundle = EvidenceBundle(
        passage_ref="Genesis 1",
        entities={},
        evidence_items=[item],
        geography={},
        provenance={},
        version="1.1",
    )
    changed = replace(
        item,
        relevance_metadata={
            **item.relevance_metadata,
            "presentation_role": "dig_deeper",
        },
    )
    assert calculate_evidence_hash(bundle) != calculate_evidence_hash(
        replace(bundle, evidence_items=[changed])
    )


def test_required_control_candidate_files_have_expected_states():
    root = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.1/chapters")
    genesis = json.loads((root / "genesis_001.json").read_text())
    luke = json.loads((root / "luke_001.json").read_text())
    leviticus = json.loads((root / "leviticus_001.json").read_text())
    zephaniah = json.loads((root / "zephaniah_001.json").read_text())
    numbers = json.loads((root / "numbers_003.json").read_text())
    assert genesis["evidence_availability"] == "AVAILABLE"
    assert luke["evidence_availability"] == "AVAILABLE"
    assert leviticus["evidence_availability"] == "AVAILABLE"
    assert zephaniah["evidence_availability"] == "AVAILABLE"
    assert numbers["evidence_availability"] == "DATA_GAP"
    assert all(
        "arad-ostraca" not in evidence_id and "caesarea-maritima" not in evidence_id
        for section in genesis["sections"]
        for block in section["blocks"]
        for evidence_id in block["evidence_ids"]
    )
    assert all(
        block["evidence_ids"] == []
        for section in numbers["sections"]
        for block in section["blocks"]
    )
