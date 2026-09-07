"""Focused Commentary 1.3 consolidation-contract tests."""

from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION, COMMENTARY_SCHEMA_VERSION
from bhf_agent.chapter_commentary.prompts import CHAPTER_COMMENTARY_SYSTEM_PROMPT, build_user_prompt
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis
from bhf_agent.presentation.models import EvidenceBundle, EvidenceItem


def _synthesis():
    bundle = EvidenceBundle(
        passage_ref="1 Samuel 21",
        entities={"people": [], "places": [], "groups": [], "events": [], "artifacts": []},
        evidence_items=[
            EvidenceItem(
                id="e1", claim="Gath was a Philistine city.", category="geography",
                source_ids=["s"], related_entity_ids=[], passage_anchors=["1 Samuel 21:10"],
                confidence="high", relevance_metadata={},
            ),
            EvidenceItem(
                id="e2", claim="David fled to Gath.", category="history",
                source_ids=["s"], related_entity_ids=[], passage_anchors=["1 Samuel 21:10"],
                confidence="high", relevance_metadata={},
            ),
        ],
        geography={}, provenance={}, version="1.1", evidence_hash="e" * 64,
    )
    return bundle, compile_chapter_synthesis(bundle, book="1 Samuel", chapter=21)


def test_commentary_13_version_changes_without_schema_change():
    assert COMMENTARY_PROMPT_VERSION == "1.3"
    assert COMMENTARY_SCHEMA_VERSION == "1.2"


def test_commentary_13_explicitly_contracts_consolidation_and_selectivity():
    bundle, synthesis = _synthesis()
    prompt = build_user_prompt(
        "1 Samuel 21", "1 Samuel", 21, "canonical text", synthesis, bundle, "AVAILABLE"
    )
    contract = " ".join((CHAPTER_COMMENTARY_SYSTEM_PROMPT + "\n" + prompt).split())
    for phrase in (
        "combine multiple compatible synthesis units",
        "Cite every synthesis ID and evidence ID actually used",
        "Do not create one block for every synthesis unit",
        "The renderer need not consume all available synthesis units",
        "not a checklist",
        "Redundant, parallel, secondary, or unnecessary context may be omitted",
        "Combining units is consolidation, not relationship inference",
        "Do not repeat substantially the same explanation in multiple sections",
        "prioritize context that most directly helps the reader understand the chapter",
        "`why_it_matters` should add the supported significance",
    ):
        assert phrase in contract
    assert "Connect facts only where a synthesis unit has already grouped them" not in contract


def test_commentary_13_preserves_existing_safety_contracts():
    bundle, synthesis = _synthesis()
    prompt = build_user_prompt(
        "1 Samuel 21", "1 Samuel", 21, "canonical text", synthesis, bundle, "AVAILABLE"
    )
    assert "Never cross a chapter boundary" in prompt
    assert "Disputed synthesis cannot become `fact`." in prompt
    assert "Never expose implementation vocabulary in reader prose" in CHAPTER_COMMENTARY_SYSTEM_PROMPT
    gap_prompt = build_user_prompt(
        "Numbers 3", "Numbers", 3, "", synthesis, bundle, "DATA_GAP"
    )
    assert 'return "sections": []' in gap_prompt
