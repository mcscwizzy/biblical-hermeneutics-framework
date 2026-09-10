"""Focused tests for deterministic renderer provenance binding."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bhf_agent.chapter_commentary.reader_provenance_binding import (
    READER_PROVENANCE_BINDING_VERSION,
    ProvenanceBindingError,
    audit_provenance_binding,
    build_provenance_binding,
    normalize_renderer_payload,
    resolve_provenance_refs,
)
from tools import commentary_v12_reader_provenance_binding as diagnostic


ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/reader-provenance-binding-v1-6bceab0758ee36f2c176"


def _path(synthesis_id: str, evidence_ids: list[str]) -> dict:
    return {
        "synthesis_id": synthesis_id,
        "evidence_ids": evidence_ids,
        "synthesis_confidence": "medium",
        "interpretation_level": "fact",
        "disputed": False,
        "passage_scope": "CURRENT_CHAPTER",
        "kind": "historical_context",
        "verse_refs": ["Romans 3:1"],
        "source_anchors": ["Romans 3:1"],
        "ancestry_hashes": {"evidence_hash": "ev-hash", "synthesis_hash": "syn-hash"},
    }


def _envelope(book: str = "Romans", chapter: int = 3) -> dict:
    return {
        "artifact_version": "reader-level-idea-ancestry-envelope-v1",
        "reference": f"{book} {chapter}",
        "book": book,
        "chapter": chapter,
        "envelope_hash": "frozen-envelope-hash",
        "ideas": [
            {
                "idea_id": "reader_idea_a",
                "label": "First idea",
                "ancestry_paths": [_path("syn_a", ["ev_a", "ev_b"])],
            },
            {
                "idea_id": "reader_idea_b",
                "label": "Second idea",
                "ancestry_paths": [_path("syn_b", ["ev_c"])],
            },
        ],
    }


def test_path_ids_and_ancestry_serialization_are_deterministic():
    first = build_provenance_binding(_envelope())
    second = build_provenance_binding(copy.deepcopy(_envelope()))

    assert first == second
    assert first["artifact_version"] == READER_PROVENANCE_BINDING_VERSION
    assert first["paths"][0]["path_id"].startswith("reader_path_romans_003_")
    assert first["paths"][0]["path"]["evidence_ids"] == ["ev_a", "ev_b"]
    assert audit_provenance_binding(first, _envelope())["valid"] is True


def test_path_id_is_chapter_scoped_and_cross_chapter_paths_are_rejected():
    romans = build_provenance_binding(_envelope("Romans", 3))
    joshua = build_provenance_binding(_envelope("Joshua", 10))
    foreign_path = joshua["paths"][0]["path_id"]

    with pytest.raises(ProvenanceBindingError, match="OUT_OF_CHAPTER_PROVENANCE_PATH"):
        resolve_provenance_refs([foreign_path], romans)


def test_unknown_malformed_and_duplicate_paths_are_rejected():
    binding = build_provenance_binding(_envelope())
    valid = binding["paths"][0]["path_id"]

    with pytest.raises(ProvenanceBindingError, match="UNKNOWN_PROVENANCE_PATH"):
        resolve_provenance_refs(["reader_path_romans_003_000000000000000000000000"], binding)
    with pytest.raises(ProvenanceBindingError, match="MALFORMED_PROVENANCE_REFERENCE"):
        resolve_provenance_refs(["not-a-path"], binding)
    with pytest.raises(ProvenanceBindingError, match="DUPLICATE_PROVENANCE_REFERENCE"):
        resolve_provenance_refs([valid, valid], binding)


def test_exact_resolution_unions_only_selected_path_ancestry():
    binding = build_provenance_binding(_envelope())
    first_id, second_id = [path["path_id"] for path in binding["paths"]]

    first = resolve_provenance_refs([first_id], binding)
    both = resolve_provenance_refs([first_id, second_id], binding)

    assert first["synthesis_ids"] == ["syn_a"]
    assert first["evidence_ids"] == ["ev_a", "ev_b"]
    assert both["synthesis_ids"] == ["syn_a", "syn_b"]
    assert both["evidence_ids"] == ["ev_a", "ev_b", "ev_c"]


def test_normalization_overwrites_manual_ids_and_cannot_leak_evidence():
    binding = build_provenance_binding(_envelope())
    first_id = binding["paths"][0]["path_id"]
    payload = {
        "reference": "Romans 3",
        "book": "Romans",
        "chapter": 3,
        "status": "pending",
        "sections": [
            {
                "kind": "historical_context",
                "title": "Context",
                "blocks": [
                    {
                        "id": "block_1",
                        "text": "Supported text",
                        "provenance_refs": [first_id],
                        "synthesis_ids": ["syn_b"],
                        "evidence_ids": ["ev_c"],
                    }
                ],
            }
        ],
    }

    normalized, metadata = normalize_renderer_payload(payload, binding)
    block = normalized["sections"][0]["blocks"][0]
    assert "provenance_refs" not in block
    assert block["synthesis_ids"] == ["syn_a"]
    assert block["evidence_ids"] == ["ev_a", "ev_b"]
    assert metadata["blocks"][0]["provenance_refs"] == [first_id]


def test_tampered_immutable_path_definition_is_rejected():
    binding = build_provenance_binding(_envelope())
    tampered = copy.deepcopy(binding)
    tampered["paths"][0]["evidence_ids"] = ["ev_c"]

    with pytest.raises(ProvenanceBindingError, match="PROVENANCE_PATH_IDENTITY_MISMATCH"):
        resolve_provenance_refs([binding["paths"][0]["path_id"]], tampered)


def test_frozen_four_chapter_artifact_is_reproducible_and_prompt_additive():
    context = diagnostic._context(ROOT)
    manifest = json.loads((TARGET_ROOT / "manifest.json").read_text())

    assert manifest == context["manifest"]
    assert manifest["contracts"]["prompt"] == "1.7"
    assert manifest["contracts"]["projection"] == "reader-level-idea-projection-v1"
    assert manifest["contracts"]["ancestry_envelope"] == "reader-level-idea-ancestry-envelope-v1"
    assert manifest["contracts"]["provenance_binding"] == READER_PROVENANCE_BINDING_VERSION
    for record, row in zip(context["records"], manifest["chapters"], strict=True):
        assert "READER PROVENANCE BINDING" not in record["source_user_prompt"]
        assert "READER PROVENANCE BINDING" in record["candidate_prompt"]
        assert "1.8" not in record["candidate_prompt"]
        assert row["source_user_prompt_sha256"] != row["candidate_input_sha256"]
        stored_binding = json.loads(
            (TARGET_ROOT / "binding" / f"{row['slug']}.json").read_text()
        )
        assert stored_binding == record["binding"]
        assert stored_binding["binding_hash"] == row["provenance_binding_hash"]


def test_existing_ancestry_validator_contract_is_recorded_unchanged():
    contracts = json.loads((TARGET_ROOT / "contract-identities.json").read_text())
    validator_path = ROOT / "bhf_agent/chapter_commentary/validation.py"
    import hashlib

    current_hash = hashlib.sha256(validator_path.read_bytes()).hexdigest()
    assert contracts["source_hashes"]["validator"] == current_hash
    assert contracts["validator_behavior"] == "existing-validator-unchanged"
    assert contracts["scorer_behavior"] == "existing-scorer-unchanged"
