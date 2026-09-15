"""Safety and compatibility tests for the v2 renderability bridge."""

from __future__ import annotations

import copy

import pytest

from bhf_agent.chapter_commentary.reader_provenance_binding import (
    build_provenance_binding,
)
from bhf_agent.chapter_commentary.reader_provenance_binding_v2 import (
    ProvenanceBindingV2Error,
    build_provenance_binding_v2,
    normalize_renderer_payload_v2,
    resolve_provenance_refs_v2,
)


def _envelope(*, ideas: list[dict] | None = None) -> dict:
    return {
        "artifact_version": "reader-level-idea-ancestry-envelope-v1",
        "reference": "Numbers 2",
        "book": "Numbers",
        "chapter": 2,
        "envelope_hash": "frozen-envelope",
        "ideas": ideas or [],
    }


def _unit(
    unit_id: str = "syn_a",
    *,
    kind: str = "interpretive_questions",
    scope: str = "CURRENT_CHAPTER",
    confidence: str = "medium",
    interpretation: str = "disputed",
    evidence_ids: list[str] | None = None,
) -> dict:
    return {
        "id": unit_id,
        "kind": kind,
        "facts": ["A supplied fact."],
        "verse_refs": ["Numbers 2:1-34"] if scope == "CURRENT_CHAPTER" else [],
        "evidence_ids": evidence_ids or [f"ev_{unit_id}"],
        "entity_ids": [],
        "related_unit_ids": [],
        "confidence": confidence,
        "interpretation_level": interpretation,
        "passage_scope": scope,
        "source_anchors": ["Numbers 2:1-34"] if scope == "CURRENT_CHAPTER" else [],
        "metadata": {},
    }


def _synthesis(units: list[dict], availability: str = "AVAILABLE") -> dict:
    return {
        "book": "Numbers",
        "chapter": 2,
        "evidence_hash": "evidence-hash",
        "synthesis_hash": "synthesis-hash",
        "evidence_availability": availability,
        "synthesis_units": units,
    }


def _evidence(evidence_ids: list[str], *, disputed: bool = False) -> list[dict]:
    return [
        {
            "id": evidence_id,
            "confidence": "medium",
            "relevance_metadata": {"disputed": disputed},
        }
        for evidence_id in evidence_ids
    ]


def test_projected_chapter_keeps_v1_priority_paths_and_suppresses_fallbacks():
    unit = _unit("syn_a", kind="chapter_overview", interpretation="fact", evidence_ids=["ev_a"])
    idea = {
        "idea_id": "reader_idea_a",
        "label": "A",
        "ancestry_paths": [{
            "synthesis_id": "syn_a",
            "evidence_ids": ["ev_a"],
            "synthesis_confidence": "medium",
            "interpretation_level": "fact",
            "disputed": False,
            "passage_scope": "CURRENT_CHAPTER",
            "kind": "chapter_overview",
            "verse_refs": ["Numbers 2:1-34"],
            "source_anchors": ["Numbers 2:1-34"],
            "ancestry_hashes": {"evidence_hash": "evidence-hash", "synthesis_hash": "synthesis-hash"},
        }],
    }
    envelope = _envelope(ideas=[idea])
    v1 = build_provenance_binding(envelope)
    v2 = build_provenance_binding_v2(envelope, _synthesis([unit]), _evidence(["ev_a"]))
    assert v2["priority_paths"] == v1["paths"]
    assert v2["paths"] == v1["paths"]
    assert v2["fallback_renderable_paths"] == []
    assert "reader_idea_id" in v2["priority_paths"][0]


def test_zero_projection_creates_exact_fallback_without_reader_idea():
    unit = _unit(evidence_ids=["ev_a", "ev_b"])
    binding = build_provenance_binding_v2(
        _envelope(), _synthesis([unit]), _evidence(["ev_a", "ev_b"])
    )
    assert len(binding["fallback_renderable_paths"]) == 1
    path = binding["fallback_renderable_paths"][0]
    assert path["path_id"].startswith("render_path_numbers_002_")
    assert "reader_idea_id" not in path
    assert path["synthesis_id"] == "syn_a"
    assert path["evidence_ids"] == ["ev_a", "ev_b"]
    assert path["path"]["interpretation_level"] == "disputed"
    assert path["path"]["synthesis_confidence"] == "medium"
    assert binding["paths"] == binding["fallback_renderable_paths"]


def test_zero_projection_without_renderable_synthesis_keeps_empty_behavior():
    binding = build_provenance_binding_v2(_envelope(), _synthesis([], "DATA_GAP"), [])
    assert binding["fallback_renderable_paths"] == []
    assert binding["paths"] == []


def test_disputed_fallback_preserves_dispute_and_confidence():
    unit = _unit(interpretation="disputed", confidence="medium", evidence_ids=["ev_a"])
    path = build_provenance_binding_v2(
        _envelope(), _synthesis([unit]), _evidence(["ev_a"], disputed=True)
    )["paths"][0]
    assert path["path"]["disputed"] is True
    assert path["path"]["interpretation_level"] == "disputed"
    assert path["path"]["synthesis_confidence"] == "medium"


def test_cross_synthesis_evidence_leakage_is_rejected():
    units = [_unit("syn_a", evidence_ids=["ev_a"]), _unit("syn_b", evidence_ids=["ev_b"])]
    binding = build_provenance_binding_v2(_envelope(), _synthesis(units), _evidence(["ev_a", "ev_b"]))
    tampered = copy.deepcopy(binding)
    tampered["paths"][0]["evidence_ids"] = ["ev_b"]
    with pytest.raises(ProvenanceBindingV2Error, match="identity hash"):
        resolve_provenance_refs_v2([tampered["paths"][0]["path_id"]], tampered)


def test_unknown_fallback_path_is_rejected():
    binding = build_provenance_binding_v2(_envelope(), _synthesis([_unit()]), _evidence(["ev_syn_a"]))
    with pytest.raises(ProvenanceBindingV2Error) as error:
        resolve_provenance_refs_v2(["render_path_numbers_002_000000000000000000000000"], binding)
    assert error.value.code == "UNKNOWN_PROVENANCE_PATH"


def test_out_of_chapter_fallback_path_is_rejected():
    binding = build_provenance_binding_v2(_envelope(), _synthesis([_unit()]), _evidence(["ev_syn_a"]))
    with pytest.raises(ProvenanceBindingV2Error) as error:
        resolve_provenance_refs_v2(["render_path_leviticus_016_000000000000000000000000"], binding)
    assert error.value.code == "OUT_OF_CHAPTER_PROVENANCE_PATH"


def test_duplicate_path_is_rejected():
    binding = build_provenance_binding_v2(_envelope(), _synthesis([_unit()]), _evidence(["ev_syn_a"]))
    path_id = binding["paths"][0]["path_id"]
    with pytest.raises(ProvenanceBindingV2Error) as error:
        resolve_provenance_refs_v2([path_id, path_id], binding)
    assert error.value.code == "DUPLICATE_PROVENANCE_REFERENCE"


def test_v2_binding_hash_is_reproducible_and_normalizes_exact_ids():
    synthesis = _synthesis([_unit(evidence_ids=["ev_syn_a"])])
    evidence = _evidence(["ev_syn_a"])
    first = build_provenance_binding_v2(_envelope(), synthesis, evidence)
    second = build_provenance_binding_v2(_envelope(), synthesis, evidence)
    assert first == second
    path_id = first["paths"][0]["path_id"]
    payload = {
        "sections": [{"kind": "interpretive_questions", "blocks": [{"provenance_refs": [path_id]}]}]
    }
    normalized, metadata = normalize_renderer_payload_v2(payload, first)
    assert normalized["sections"][0]["blocks"][0]["synthesis_ids"] == ["syn_a"]
    assert normalized["sections"][0]["blocks"][0]["evidence_ids"] == ["ev_syn_a"]
    assert metadata["blocks"][0]["path_classes"] == ["fallback_renderable"]


def test_renderer_cannot_author_synthesis_or_evidence_pairings():
    binding = build_provenance_binding_v2(
        _envelope(), _synthesis([_unit()]), _evidence(["ev_syn_a"])
    )
    with pytest.raises(ProvenanceBindingV2Error, match="must not author canonical IDs"):
        normalize_renderer_payload_v2(
            {
                "sections": [{
                    "kind": "interpretive_questions",
                    "blocks": [{
                        "provenance_refs": [binding["paths"][0]["path_id"]],
                        "synthesis_ids": ["invented"],
                        "evidence_ids": ["invented"],
                    }],
                }]
            },
            binding,
        )
