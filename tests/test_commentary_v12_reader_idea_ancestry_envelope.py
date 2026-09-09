"""Focused tests for the relational reader-idea ancestry presentation."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    AncestryEnvelopeError,
    READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
    add_ancestry_envelope_to_prompt,
    build_ancestry_envelope,
)
from tools import commentary_v12_reader_idea_ancestry_envelope as diagnostic


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / diagnostic.SOURCE_NAMESPACE
TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/reader-idea-ancestry-envelope-v1-b970c53e1dc561f23530"


def _fixture() -> tuple[dict, dict]:
    synthesis = {
        "synthesis_units": [
            {
                "id": "syn_a",
                "kind": "interpretive_questions",
                "evidence_ids": ["ev_1", "ev_2"],
                "confidence": "medium",
                "interpretation_level": "disputed",
                "passage_scope": "CURRENT_CHAPTER",
                "verse_refs": ["1 Corinthians 14:1"],
                "source_anchors": ["1 Corinthians 14:1"],
            },
            {
                "id": "syn_b",
                "kind": "interpretive_questions",
                "evidence_ids": ["ev_3"],
                "confidence": "high",
                "interpretation_level": "fact",
                "passage_scope": "CURRENT_CHAPTER",
                "verse_refs": ["1 Corinthians 14:2"],
                "source_anchors": ["1 Corinthians 14:2"],
            },
        ]
    }
    projection = {
        "reference": "1 Corinthians 14",
        "book": "1 Corinthians",
        "chapter": 14,
        "projection_version": "reader-level-idea-projection-v1",
        "projection_hash": "projection-hash",
        "evidence_hash": "evidence-hash",
        "synthesis_hash": "synthesis-hash",
        "ideas": [
            {
                "idea_id": "idea_1",
                "label": "A grouped idea",
                "importance": "RELEVANT",
                "categories": ["culture"],
                "cluster_ids": ["cluster_1"],
                "synthesis_unit_ids": ["syn_a", "syn_b"],
                "evidence_ids": ["ev_1", "ev_2", "ev_3"],
                "disputed": True,
                "status": "DISPUTED",
                "confidence": "medium",
            }
        ],
    }
    evidence = {
        evidence_id: {"id": evidence_id}
        for evidence_id in ("ev_1", "ev_2", "ev_3")
    }
    return projection, synthesis | {"_evidence": evidence}


def test_ancestry_paths_are_deterministic_and_explicit():
    projection, synthesis_with_evidence = _fixture()
    synthesis = {"synthesis_units": synthesis_with_evidence["synthesis_units"]}
    first = build_ancestry_envelope(projection, synthesis, synthesis_with_evidence["_evidence"])
    second = build_ancestry_envelope(projection, synthesis, synthesis_with_evidence["_evidence"])

    assert first == second
    assert first["artifact_version"] == READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION
    assert [
        (path["synthesis_id"], path["evidence_ids"])
        for path in first["ideas"][0]["ancestry_paths"]
    ] == [("syn_a", ["ev_1", "ev_2"]), ("syn_b", ["ev_3"])]
    assert "synthesis_unit_ids" not in first["ideas"][0]
    assert "evidence_ids" not in first["ideas"][0]


def test_no_cross_synthesis_evidence_leakage_is_possible_in_a_path():
    projection, synthesis_with_evidence = _fixture()
    envelope = build_ancestry_envelope(
        projection,
        {"synthesis_units": synthesis_with_evidence["synthesis_units"]},
        synthesis_with_evidence["_evidence"],
    )
    paths = envelope["ideas"][0]["ancestry_paths"]
    assert set(paths[0]["evidence_ids"]) == {"ev_1", "ev_2"}
    assert set(paths[1]["evidence_ids"]) == {"ev_3"}
    assert envelope["ancestry_audit"]["cross_synthesis_evidence_leakage"] == []

    invalid = copy.deepcopy(projection)
    invalid["ideas"][0]["evidence_ids"] = ["ev_1", "ev_2", "ev_3", "ev_4"]
    with pytest.raises(AncestryEnvelopeError, match="flat ancestry disagrees"):
        build_ancestry_envelope(
            invalid,
            {"synthesis_units": synthesis_with_evidence["synthesis_units"]},
            synthesis_with_evidence["_evidence"],
        )


def test_full_frozen_projection_ancestry_is_preserved():
    projection = json.loads((SOURCE_ROOT / "projections/1_corinthians_014.json").read_text())
    context = diagnostic._source_context(ROOT)
    envelope = context["envelope"]

    assert envelope["projection_hash"] == projection["projection_hash"]
    assert envelope["ancestry_audit"]["idea_ids_preserved"] is True
    assert envelope["ancestry_audit"]["synthesis_unit_ids_preserved"] is True
    assert envelope["ancestry_audit"]["evidence_ids_preserved"] is True
    assert envelope["ancestry_audit"]["paths_have_exact_unit_ancestry"] is True
    assert envelope["ancestry_audit"]["synthetic_parentage_created"] is False
    assert len(envelope["ideas"]) == 7
    assert sum(len(idea["ancestry_paths"]) for idea in envelope["ideas"]) == 33


def test_projection_v1_input_is_not_mutated():
    projection = json.loads((SOURCE_ROOT / "projections/1_corinthians_014.json").read_text())
    before = copy.deepcopy(projection)
    context = diagnostic._source_context(ROOT)
    build_ancestry_envelope(projection, context["prepared"].synthesis, context["prepared"].bundle.evidence_items)

    assert projection == before
    assert projection["projection_version"] == "reader-level-idea-projection-v1"
    assert all("ancestry_paths" not in idea for idea in projection["ideas"])


def test_prompt_17_is_unchanged_and_envelope_is_additive():
    context = diagnostic._source_context(ROOT)
    source_prompt = context["source_user_prompt"]
    candidate_prompt = context["candidate_user_prompt"]

    assert source_prompt == (SOURCE_ROOT / "renderer-input/003_1_corinthians_014/user_prompt.txt").read_text()
    assert "READER-LEVEL IDEA ANCESTRY ENVELOPE" not in source_prompt
    assert "READER-LEVEL IDEA ANCESTRY ENVELOPE" in candidate_prompt
    compact_prompt = " ".join(candidate_prompt.split())
    assert "only pair evidence IDs with synthesis IDs from the same" in compact_prompt
    assert "Do not treat IDs from the same reader-level idea as interchangeable." in compact_prompt
    assert "1.8" not in candidate_prompt
    assert add_ancestry_envelope_to_prompt(source_prompt, context["envelope"]) == candidate_prompt


def test_validator_behavior_unchanged_and_still_rejects_original_pair():
    context = diagnostic._source_context(ROOT)
    raw = (SOURCE_ROOT / "responses/raw/003_1_corinthians_014.json").read_bytes()
    result, parsed = diagnostic.renderer_validation._evaluate_one(
        {"reference": diagnostic.REFERENCE, "book": diagnostic.BOOK, "chapter": diagnostic.CHAPTER},
        raw,
        context["prepared"],
    )

    assert result["structural_result"] == "REJECTED"
    assert "SYNTHESIS_ANCESTRY_MISMATCH" in result["rejection_codes"]
    assert parsed["validation_errors"] == [
        "SYNTHESIS_ANCESTRY_MISMATCH: section[0].block[2] cites evidence outside its synthesis ancestry"
    ]


def test_candidate_artifact_reproducibility():
    context = diagnostic._source_context(ROOT)
    manifest = json.loads((TARGET_ROOT / "manifest.json").read_text())
    envelope = json.loads((TARGET_ROOT / "envelope/ancestry-envelope.json").read_text())

    assert manifest == context["manifest"]
    assert envelope == context["envelope"]
    assert (TARGET_ROOT / "renderer-input/user_prompt.txt").read_text() == context["candidate_user_prompt"]
    assert manifest["ancestry_envelope"]["hash"] == envelope["envelope_hash"]
