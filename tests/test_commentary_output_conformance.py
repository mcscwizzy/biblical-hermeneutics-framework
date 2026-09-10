"""Focused tests for Commentary v1.2 renderer output conformance."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from bhf_agent.chapter_commentary.output_conformance import (
    COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
    MAX_STRUCTURAL_ATTEMPTS,
    conform_renderer_output,
    parse_renderer_json,
    structural_retry_allowed,
)
from bhf_agent.chapter_commentary.reader_provenance_binding import (
    build_provenance_binding,
    normalize_renderer_payload,
)
from framework.commentary.production.models import sha256_json


def _binding() -> dict:
    envelope = {
        "artifact_version": "reader-level-idea-ancestry-envelope-v1",
        "reference": "Romans 3",
        "book": "Romans",
        "chapter": 3,
        "envelope_hash": "frozen-envelope-hash",
        "ideas": [{
            "idea_id": "reader_idea_a",
            "label": "First idea",
            "ancestry_paths": [{
                "synthesis_id": "syn_a",
                "evidence_ids": ["ev_a"],
                "synthesis_confidence": "medium",
                "interpretation_level": "fact",
                "disputed": False,
                "passage_scope": "CURRENT_CHAPTER",
                "kind": "chapter_overview",
                "verse_refs": ["Romans 3:1"],
                "source_anchors": ["Romans 3:1"],
                "ancestry_hashes": {"evidence_hash": "ev-hash", "synthesis_hash": "syn-hash"},
            }],
        }],
    }
    return build_provenance_binding(envelope)


def _payload(binding: dict) -> dict:
    return {
        "reference": "Romans 3",
        "book": "Romans",
        "chapter": 3,
        "status": "pending",
        "sections": [{
            "kind": "chapter_overview",
            "title": "Overview",
            "blocks": [{
                "id": "block_1",
                "text": "A reader-facing explanation.",
                "verse_refs": ["Romans 3:1"],
                "provenance_refs": [binding["paths"][0]["path_id"]],
                "confidence": "medium",
                "interpretation_level": "fact",
            }],
        }],
        "generated_metadata": None,
    }


def test_empty_sections_are_explicitly_rejected_without_fabrication():
    payload = _payload(_binding())
    payload["sections"] = []
    result = conform_renderer_output(payload, expected_reference="Romans 3", expected_book="Romans", expected_chapter=3)
    assert not result.valid
    assert "EMPTY_REQUIRED_SECTIONS" in result.codes
    assert result.payload["sections"] == []


def test_missing_required_field_is_rejected():
    payload = _payload(_binding())
    del payload["sections"][0]["blocks"][0]["provenance_refs"]
    result = conform_renderer_output(payload)
    assert not result.valid
    assert "MALFORMED_REQUIRED_FIELD" in result.codes


def test_single_verse_reference_string_is_deterministically_wrapped():
    payload = _payload(_binding())
    payload["sections"][0]["blocks"][0]["verse_refs"] = "Romans 3:1"
    result = conform_renderer_output(payload)
    assert result.valid
    assert result.payload["sections"][0]["blocks"][0]["verse_refs"] == ["Romans 3:1"]
    assert result.events[0]["code"] == "VERSE_REFS_STRING_TO_ARRAY"


def test_reference_alias_and_spacing_are_canonically_serialized():
    payload = _payload(_binding())
    payload["sections"][0]["blocks"][0]["verse_refs"] = ["Rom 3 : 1"]
    result = conform_renderer_output(payload)
    assert result.valid
    assert result.payload["sections"][0]["blocks"][0]["verse_refs"] == ["Romans 3:1"]
    assert result.events[0]["code"] == "CANONICAL_VERSE_REFERENCE_SERIALIZATION"


def test_ambiguous_chapter_only_reference_is_rejected_without_guessing():
    payload = _payload(_binding())
    payload["sections"][0]["blocks"][0]["verse_refs"] = ["Romans 3"]
    result = conform_renderer_output(payload)
    assert not result.valid
    assert "AMBIGUOUS_VERSE_REFERENCE" in result.codes
    assert result.payload["sections"][0]["blocks"][0]["verse_refs"] == ["Romans 3"]


def test_valid_canonical_response_is_a_semantic_no_op():
    payload = _payload(_binding())
    original = copy.deepcopy(payload)
    result = conform_renderer_output(payload)
    assert result.valid
    assert result.payload == original
    assert result.events == ()


def test_conformance_output_remains_compatible_with_provenance_binding():
    binding = _binding()
    payload = _payload(binding)
    result = conform_renderer_output(payload)
    normalized, metadata = normalize_renderer_payload(result.payload, binding)
    assert normalized["sections"][0]["blocks"][0]["synthesis_ids"] == ["syn_a"]
    assert normalized["sections"][0]["blocks"][0]["evidence_ids"] == ["ev_a"]
    assert metadata["artifact_version"] == "reader-provenance-binding-v1"


def test_structural_retry_is_exactly_one_and_quality_failures_do_not_retry():
    assert COMMENTARY_OUTPUT_CONFORMANCE_VERSION == "commentary-output-conformance-v1"
    assert MAX_STRUCTURAL_ATTEMPTS == 2
    assert structural_retry_allowed(attempt_ordinal=1, codes=["EMPTY_REQUIRED_SECTIONS"])
    assert not structural_retry_allowed(attempt_ordinal=2, codes=["EMPTY_REQUIRED_SECTIONS"])
    assert not structural_retry_allowed(attempt_ordinal=1, codes=["QUALITY_FAIL"])
    assert not structural_retry_allowed(attempt_ordinal=1, codes=["RICHNESS_SHORTFALL"])


def test_strict_parser_preserves_json_failure_as_retryable_structure():
    payload, status, errors = parse_renderer_json(b"not json")
    assert payload is None
    assert status == "MALFORMED_JSON"
    assert errors[0].startswith("MALFORMED_RESPONSE_JSON:")
    result = conform_renderer_output(payload, parse_status=status, parse_errors=errors)
    assert not result.valid
    assert result.retry_eligible


def test_completed_diagnostic_artifact_is_checksum_reproducible():
    root = Path(__file__).resolve().parents[1] / ".bhf-data/bhf-commentary-candidates/commentary-output-conformance-v1-d278cba2d2151d1b4242"
    manifest = json.loads((root / "manifest.json").read_text())
    checksums = json.loads((root / "checksums.json").read_text())
    assert manifest["manifest_identity"] == sha256_json(
        {key: value for key, value in manifest.items() if key != "manifest_identity"}
    )
    assert len(manifest["chapters"]) == 5
    assert set(manifest["source_failure_references"]) == {
        "Numbers 2", "2 Kings 4", "Psalms 103", "Numbers 1", "Psalms 19"
    }
    for relative, expected in checksums["files"].items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
