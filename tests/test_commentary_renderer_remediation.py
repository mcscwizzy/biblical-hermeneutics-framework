"""Focused tests for the isolated Commentary prompt 1.6 remediation."""

from pathlib import Path

import pytest

from bhf_agent.chapter_commentary.models import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
)
from bhf_agent.chapter_commentary.prompts import (
    CHAPTER_COMMENTARY_SYSTEM_PROMPT,
    CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16,
    build_user_prompt,
    system_prompt_for_version,
)
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis
from bhf_agent.presentation.models import EvidenceBundle, EvidenceItem
from tools import commentary_renderer_remediation as remediation


REPO_ROOT = Path(__file__).resolve().parents[1]


def _synthesis():
    bundle = EvidenceBundle(
        passage_ref="Job 1",
        entities={"people": [], "places": [], "groups": [], "events": [], "artifacts": []},
        evidence_items=[
            EvidenceItem(
                id="e1",
                claim="The supplied claim is direct chapter context.",
                category="history",
                source_ids=["source"],
                related_entity_ids=[],
                passage_anchors=["Job 1:1"],
                confidence="high",
                relevance_metadata={},
            )
        ],
        geography={},
        provenance={},
        version="1.1",
        evidence_hash="e" * 64,
    )
    return bundle, compile_chapter_synthesis(bundle, book="Job", chapter=1)


def test_candidate_contract_bumps_prompt_only_and_keeps_v15_default():
    bundle, synthesis = _synthesis()
    default_prompt = build_user_prompt("Job 1", "Job", 1, "canonical", synthesis, bundle, "AVAILABLE")
    candidate_prompt = build_user_prompt(
        "Job 1",
        "Job",
        1,
        "canonical",
        synthesis,
        bundle,
        "AVAILABLE",
        prompt_version=COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
    )
    assert COMMENTARY_PROMPT_VERSION == "1.5"
    assert COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION == "1.6"
    assert COMMENTARY_SCHEMA_VERSION == "1.2"
    assert "Commentary v1.5" in default_prompt
    assert "representative-breadth check" not in default_prompt
    assert system_prompt_for_version("1.5") == CHAPTER_COMMENTARY_SYSTEM_PROMPT
    assert "Commentary v1.6" in candidate_prompt
    assert "representative-breadth check" in candidate_prompt
    assert "union of the evidence ancestry" in candidate_prompt
    assert "Never mention a claim or attach an ID merely" in candidate_prompt
    assert system_prompt_for_version("1.6") == CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16
    assert CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16.startswith(
        "You write BHF reader commentary for an intelligent reader"
    )
    assert "Do not attempt to mention every available synthesis unit." in CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16


def test_unknown_prompt_contract_is_rejected():
    with pytest.raises(ValueError, match="unsupported commentary prompt version"):
        system_prompt_for_version("9.9")


def test_remediation_manifest_freezes_exact_five_sol_medium_packets():
    manifest, material = remediation.build_manifest(REPO_ROOT)
    assert manifest["previous_qualification_id"] == remediation.PREVIOUS_QUALIFICATION_ID
    assert manifest["renderer"] == "gpt-5.6-sol"
    assert manifest["renderer_effort"] == "medium"
    assert manifest["chapter_count"] == 5
    assert [row["reference"] for row in manifest["chapters"]] == list(remediation.EXPECTED_REFERENCES)
    assert len(material) == 5
    assert manifest["generation_authorized"] is False
    assert manifest["bulk_generation_authorized"] is False
    assert manifest["contract_versions"] == {
        "old_commentary_prompt_version": "1.5",
        "candidate_commentary_prompt_version": "1.6",
        "commentary_schema_version": "1.2",
        "synthesis_schema_version": "1.1",
        "synthesis_compiler_version": "1.1",
        "gate_version": "commentary-richness-gate-v2.1",
    }
    for row, (packet, prepared) in zip(manifest["chapters"], material, strict=True):
        assert row["source_packet_id"] == prepared.row["input_identity"]["packet_id"]
        assert row["source_packet_hash"] == prepared.row["input_identity"]["packet_hash"]
        assert row["evidence_hash"] == prepared.bundle.evidence_hash
        assert row["synthesis_hash"] == prepared.synthesis.synthesis_hash
        assert packet["commentary_prompt_version"] == "1.6"
        assert packet["commentary_schema_version"] == "1.2"
        assert packet["renderer"] == "gpt-5.6-sol"
        assert packet["renderer_effort"] == "medium"
