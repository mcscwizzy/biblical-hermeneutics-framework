from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bhf_agent.chapter_commentary.reader_provenance_binding import (
    build_provenance_binding,
)
from bhf_agent.chapter_commentary.reader_provenance_binding_v2 import (
    build_provenance_binding_v2,
)
from bhf_agent.chapter_commentary.renderer_reference_presentation_v1 import (
    AMBIGUOUS,
    INVALID_SOURCE_REFERENCE,
    SAFE_FULL_CHAPTER_SCOPE,
    VALID_ALREADY,
    RendererReferencePresentationError,
    audit_active_paths,
    canonical_chapter_boundary,
    normalize_selected_chapter_scope_refs,
    present_binding,
)
from tools import commentary_v12_reader_provenance_binding_v2_bounded_validation as v2_diagnostic


ROOT = Path(__file__).resolve().parents[1]
V2_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-reader-provenance-binding-v2-bounded-validation-v1-023f67f998ec3f853936"


def _envelope(book: str = "Numbers", chapter: int = 1, *, path_refs: list[str] | None = None, scope: str = "CURRENT_CHAPTER") -> dict:
    refs = path_refs or ["Numbers 1"]
    return {
        "artifact_version": "reader-level-idea-ancestry-envelope-v1",
        "reference": f"{book} {chapter}",
        "book": book,
        "chapter": chapter,
        "envelope_hash": "envelope-hash",
        "ideas": [{
            "idea_id": "reader_idea_a",
            "label": "Numbers",
            "ancestry_paths": [{
                "synthesis_id": "syn_a",
                "evidence_ids": ["ev_a"],
                "synthesis_confidence": "low",
                "interpretation_level": "disputed",
                "disputed": True,
                "passage_scope": scope,
                "kind": "interpretive_questions",
                "verse_refs": refs,
                "source_anchors": refs,
                "ancestry_hashes": {"evidence_hash": "evidence-hash", "synthesis_hash": "synthesis-hash"},
            }],
        }],
    }


def _synthesis(*, refs: list[str] | None = None, scope: str = "CURRENT_CHAPTER", anchors: list[str] | None = None) -> dict:
    refs = refs or ["Numbers 1"]
    return {
        "book": "Numbers",
        "chapter": 1,
        "evidence_hash": "evidence-hash",
        "synthesis_hash": "synthesis-hash",
        "synthesis_units": [{
            "id": "syn_a",
            "kind": "interpretive_questions",
            "confidence": "low",
            "interpretation_level": "disputed",
            "passage_scope": scope,
            "verse_refs": refs,
            "source_anchors": anchors if anchors is not None else refs,
            "evidence_ids": ["ev_a"],
        }],
    }


def _evidence(*, anchors: list[str] | None = None) -> list[dict]:
    return [{"id": "ev_a", "passage_anchors": anchors or ["Numbers 1"], "confidence": "low"}]


def _binding(*, path_refs: list[str] | None = None, scope: str = "CURRENT_CHAPTER") -> tuple[dict, dict, list[dict]]:
    envelope = _envelope(path_refs=path_refs, scope=scope)
    synthesis = _synthesis(refs=path_refs, scope=scope)
    evidence = _evidence()
    binding = build_provenance_binding_v2(envelope, synthesis, evidence)
    return binding, synthesis, evidence


def test_chapter_only_current_chapter_path_expands_from_authoritative_data() -> None:
    binding, synthesis, evidence = _binding()
    presentation = present_binding(binding, synthesis, evidence)
    path = presentation["paths"][0]
    assert path["canonicalization"]["classification"] == SAFE_FULL_CHAPTER_SCOPE
    assert path["source_verse_refs"] == ["Numbers 1"]
    assert path["renderer_verse_refs"] == ["Numbers 1:1-54"]
    assert presentation["canonical_boundary"]["final_verse"] == 54
    assert presentation["canonical_boundary"]["source"]["path"] == "bhf_agent/data/asv_bible.json"


def test_canonical_final_verse_comes_from_supplied_authoritative_data() -> None:
    data = {
        "translation": {"id": "fixture"},
        "books": [{"name": "Numbers", "chapters": [{"chapter": 1, "verses": [{"verse": 1}, {"verse": 2}, {"verse": 3}]}]}],
    }
    boundary = canonical_chapter_boundary("Numbers", 1, data=data)
    assert boundary["renderer_reference"] == "Numbers 1:1-3"
    assert boundary["final_verse"] == 3


def test_existing_valid_verse_and_range_are_unchanged() -> None:
    for refs in (["Numbers 1:1"], ["Numbers 1:1-54"]):
        binding, synthesis, evidence = _binding(path_refs=list(refs))
        path = present_binding(binding, synthesis, evidence)["paths"][0]
        assert path["canonicalization"]["classification"] == VALID_ALREADY
        assert path["source_verse_refs"] == list(refs)
        assert path["renderer_verse_refs"] == list(refs)


@pytest.mark.parametrize(
    ("path_refs", "scope", "synthesis_scope", "anchors", "classification"),
    [
        (["Leviticus 1"], "SURROUNDING_PASSAGE", "SURROUNDING_PASSAGE", ["Leviticus 1"], AMBIGUOUS),
        (["Numbers 2"], "CURRENT_CHAPTER", "CURRENT_CHAPTER", ["Numbers 2"], AMBIGUOUS),
        (["Numbers 1:bad"], "CURRENT_CHAPTER", "CURRENT_CHAPTER", ["Numbers 1:bad"], INVALID_SOURCE_REFERENCE),
        (["Numbers 1", "Numbers 1:1"], "CURRENT_CHAPTER", "CURRENT_CHAPTER", ["Numbers 1", "Numbers 1:1"], AMBIGUOUS),
        (["Numbers 1"], "CURRENT_CHAPTER", "SURROUNDING_PASSAGE", ["Numbers 1"], AMBIGUOUS),
        (["Numbers 1"], "CURRENT_CHAPTER", "CURRENT_CHAPTER", ["Numbers 1:1"], AMBIGUOUS),
    ],
)
def test_unsafe_references_are_not_normalized(
    path_refs: list[str],
    scope: str,
    synthesis_scope: str,
    anchors: list[str],
    classification: str,
) -> None:
    envelope = _envelope(path_refs=path_refs, scope=scope)
    synthesis = _synthesis(refs=path_refs, scope=synthesis_scope, anchors=anchors)
    evidence = _evidence(anchors=anchors)
    binding = build_provenance_binding_v2(envelope, synthesis, evidence)
    path = present_binding(binding, synthesis, evidence)["paths"][0]
    assert path["canonicalization"]["classification"] == classification
    assert path["renderer_verse_refs"] == path_refs


def test_path_constrained_safeguard_preserves_source_and_dispute() -> None:
    binding, synthesis, evidence = _binding()
    presentation = present_binding(binding, synthesis, evidence)
    path_id = binding["paths"][0]["path_id"]
    payload = {
        "sections": [{"blocks": [{
            "provenance_refs": [path_id],
            "verse_refs": ["Numbers 1"],
            "confidence": "low",
            "interpretation_level": "disputed",
        }]}],
    }
    normalized, events = normalize_selected_chapter_scope_refs(payload, binding, presentation)
    assert normalized["sections"][0]["blocks"][0]["verse_refs"] == ["Numbers 1:1-54"]
    assert events[0]["code"] == "CHAPTER_SCOPE_REFERENCE_EXPANDED"
    assert events[0]["source_provenance_path_id"] == path_id
    assert events[0]["source_reference"] == "Numbers 1"
    assert events[0]["renderer_reference"] == "Numbers 1:1-54"
    assert normalized["sections"][0]["blocks"][0]["confidence"] == "low"
    assert normalized["sections"][0]["blocks"][0]["interpretation_level"] == "disputed"


def test_safeguard_does_not_expand_unselected_or_mixed_paths() -> None:
    binding, synthesis, evidence = _binding(path_refs=["Numbers 1:1"])
    safe_binding, safe_synthesis, safe_evidence = _binding()
    # The binding has only an already-valid path, so chapter-only output has no
    # mechanically proven selected whole-chapter owner.
    presentation = present_binding(binding, synthesis, evidence)
    payload = {"sections": [{"blocks": [{"provenance_refs": [binding["paths"][0]["path_id"]], "verse_refs": ["Numbers 1"]}]}]}
    normalized, events = normalize_selected_chapter_scope_refs(payload, binding, presentation)
    assert normalized == payload
    assert events == []
    assert safe_binding["paths"][0]["path_id"] != binding["paths"][0]["path_id"]


def test_active_path_audit_reports_counts_and_ids() -> None:
    binding, synthesis, evidence = _binding()
    audit = audit_active_paths(binding, synthesis, evidence)
    assert audit["counts"] == {
        VALID_ALREADY: 0,
        SAFE_FULL_CHAPTER_SCOPE: 1,
        AMBIGUOUS: 0,
        INVALID_SOURCE_REFERENCE: 0,
    }
    assert audit["affected_path_ids"][SAFE_FULL_CHAPTER_SCOPE] == [binding["paths"][0]["path_id"]]


def test_binding_identity_is_unchanged_by_derived_presentation() -> None:
    binding, synthesis, evidence = _binding()
    original = copy.deepcopy(binding)
    presentation = present_binding(binding, synthesis, evidence)
    assert binding == original
    assert presentation["binding_hash"] == binding["binding_hash"]
    assert presentation["paths"][0]["path_id"] == binding["paths"][0]["path_id"]


def test_frozen_v1_and_committed_v2_identities_remain_reproducible() -> None:
    context = v2_diagnostic.build_context(ROOT)
    record = context["records"]["Numbers 1"]
    stored_v1 = json.loads((V2_ROOT / "provenance-bindings-v1/numbers_001.json").read_text())
    stored_v2 = json.loads((V2_ROOT / "provenance-bindings-v2/numbers_001.json").read_text())
    assert stored_v1 == record["v1_binding"]
    assert stored_v2 == record["binding"]
    assert stored_v1["binding_hash"] == record["v1_binding"]["binding_hash"]
    assert stored_v2["binding_hash"] == record["binding"]["binding_hash"]
