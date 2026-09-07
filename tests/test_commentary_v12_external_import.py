"""External renderer round-trip tests for the bounded Commentary v1.2 canary."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.chapter_commentary.synthesis import load_synthesis
from tools.commentary_canary_import import import_responses
from tools.commentary_v12_canary import (
    CANARY_ROOT,
    ROOT,
    _read_json,
    compare,
    evaluate_gate,
    prepare,
)


FIXED_TIME = "2026-09-07T12:00:00+00:00"


def _workspace(tmp_path: Path):
    prepare()
    candidate = tmp_path / "candidate"
    canary = candidate / "canary"
    canary.mkdir(parents=True)
    for name in ("canary-preflight.json", "canary-generation-manifest.json"):
        shutil.copy2(CANARY_ROOT / name, canary / name)
    raw = canary / "responses/raw"
    raw.mkdir(parents=True)
    return candidate, raw


def _response(reference: str) -> dict:
    manifest = _read_json(CANARY_ROOT / "canary-generation-manifest.json")
    preflight = _read_json(CANARY_ROOT / "canary-preflight.json")
    packet = next(row for row in manifest["chapters"] if row["reference"] == reference)
    locked = next(row for row in preflight["chapters"] if row["reference"] == reference)
    synthesis = load_synthesis(CANARY_ROOT / "synthesis", locked["book"], locked["chapter"])
    assert synthesis is not None
    unit = next(value for value in synthesis.synthesis_units if value.evidence_ids)
    verse_refs = list(unit.verse_refs)
    if not verse_refs:
        verse_refs = [f"{locked['book']} {locked['chapter']}:1"]
    return {
        "reference": reference,
        "packet_id": packet["packet_id"],
        "prompt_version": packet["commentary_prompt_version"],
        "evidence_hash": packet["evidence_hash"],
        "synthesis_hash": packet["synthesis_hash"],
        "renderer_label": "Luna Medium",
        "response_payload": {
            "reference": reference,
            "book": locked["book"],
            "chapter": locked["chapter"],
            "status": "pending",
            "sections": [{
                "kind": unit.kind,
                "title": "Context",
                "blocks": [{
                    "id": "block_1",
                    "text": "A concise explanation grounded in the available chapter context.",
                    "verse_refs": verse_refs,
                    "evidence_ids": list(unit.evidence_ids),
                    "synthesis_ids": [unit.id],
                    "confidence": unit.confidence,
                    "interpretation_level": unit.interpretation_level,
                }],
            }],
            "generated_metadata": None,
        },
    }


def _write(path: Path, value) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_valid_external_response_import_stamps_metadata_and_preserves_raw(tmp_path):
    candidate, raw = _workspace(tmp_path)
    source = raw / "genesis_001.json"
    value = _response("Genesis 1")
    value["response_payload"]["status"] = "validated"
    value["response_payload"]["generated_metadata"] = {"evidence_hash": "renderer-owned"}
    original = json.dumps(value)
    source.write_text(original, encoding="utf-8")

    result = import_responses(raw, candidate_root=candidate, imported_at=FIXED_TIME)

    assert result["status"] == "PARTIAL_RESPONSES"
    assert result["accepted_count"] == 1
    assert source.read_text(encoding="utf-8") == original
    accepted = load_commentary(candidate / "canary/responses/accepted", "Genesis", 1)
    assert accepted is not None and accepted.status == "validated"
    metadata = accepted.generated_metadata
    assert metadata is not None
    assert metadata.evidence_hash == value["evidence_hash"]
    assert metadata.synthesis_hash == value["synthesis_hash"]
    assert metadata.renderer_label == "Luna Medium"
    assert metadata.imported_timestamp == FIXED_TIME
    assert metadata.generated_timestamp == FIXED_TIME
    assert metadata.candidate_id.startswith("commentary-v1.2-candidate:")
    assert metadata.model == "external-renderer"
    assert not list((candidate / "canary/responses/rejected").glob("*.json"))


def test_data_gap_empty_renderer_gets_application_owned_fallback(tmp_path):
    candidate, raw = _workspace(tmp_path)
    manifest = _read_json(CANARY_ROOT / "canary-generation-manifest.json")
    packet = next(row for row in manifest["chapters"] if row["reference"] == "Numbers 3")
    response = {
        "reference": "Numbers 3",
        "packet_id": packet["packet_id"],
        "prompt_version": packet["commentary_prompt_version"],
        "evidence_hash": packet["evidence_hash"],
        "synthesis_hash": packet["synthesis_hash"],
        "renderer_label": "Luna Medium",
        "response_payload": {
            "reference": "Numbers 3",
            "book": "Numbers",
            "chapter": 3,
            "status": "pending",
            "sections": [],
            "generated_metadata": None,
        },
    }
    _write(raw / "numbers_003.json", response)
    result = import_responses(raw, candidate_root=candidate, imported_at=FIXED_TIME)
    assert result["accepted_count"] == 1
    accepted = load_commentary(candidate / "canary/responses/accepted", "Numbers", 3)
    assert accepted is not None
    assert accepted.data_gap_fallback is True
    assert accepted.sections[0].blocks[0].evidence_ids == []


def test_data_gap_renderer_prose_is_rejected(tmp_path):
    candidate, raw = _workspace(tmp_path)
    manifest = _read_json(CANARY_ROOT / "canary-generation-manifest.json")
    packet = next(row for row in manifest["chapters"] if row["reference"] == "Numbers 3")
    response = {
        "reference": "Numbers 3",
        "packet_id": packet["packet_id"],
        "prompt_version": packet["commentary_prompt_version"],
        "evidence_hash": packet["evidence_hash"],
        "synthesis_hash": packet["synthesis_hash"],
        "renderer_label": "Luna Medium",
        "response_payload": {
            "reference": "Numbers 3", "book": "Numbers", "chapter": 3,
            "status": "pending",
            "sections": [{"kind": "chapter_overview", "title": "No context", "blocks": []}],
            "generated_metadata": None,
        },
    }
    _write(raw / "numbers_003.json", response)
    result = import_responses(raw, candidate_root=candidate, imported_at=FIXED_TIME)
    assert result["rejected_count"] == 1
    assert "DATA_GAP_RENDERER_PROSE" in result["chapters"][0]["rejection_codes"]


def test_malformed_response_is_rejected_and_raw_is_preserved(tmp_path):
    candidate, raw = _workspace(tmp_path)
    source = raw / "broken.json"
    source.write_text("{not json", encoding="utf-8")
    result = import_responses(raw, candidate_root=candidate, imported_at=FIXED_TIME)
    assert result["rejected_count"] == 1
    assert "MALFORMED_RESPONSE_JSON" in result["chapters"][0]["rejection_codes"]
    assert source.read_text(encoding="utf-8") == "{not json"
    assert (candidate / "canary/responses/rejected/broken.json").is_file()


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("packet_id", "commentary-v1.2-packet:" + "0" * 64, "UNKNOWN_PACKET"),
        ("reference", "Genesis 2", "NON_CANARY_RESPONSE"),
        ("evidence_hash", "0" * 64, "EVIDENCE_HASH_MISMATCH"),
        ("synthesis_hash", "0" * 64, "SYNTHESIS_HASH_MISMATCH"),
        ("prompt_version", "1.1", "PROMPT_VERSION_MISMATCH"),
    ],
)
def test_envelope_identity_mismatches_are_rejected(tmp_path, field, value, code):
    candidate, raw = _workspace(tmp_path)
    response = _response("Genesis 1")
    response[field] = value
    _write(raw / "response.json", response)
    result = import_responses(raw, candidate_root=candidate, imported_at=FIXED_TIME)
    assert code in result["chapters"][0]["rejection_codes"]
    assert not list((candidate / "canary/responses/accepted").glob("*.json"))


def test_missing_field_and_non_object_payload_are_rejected(tmp_path):
    candidate, raw = _workspace(tmp_path)
    response = _response("Genesis 1")
    response.pop("renderer_label")
    response["response_payload"] = "not commentary JSON"
    _write(raw / "response.json", response)
    result = import_responses(raw, candidate_root=candidate, imported_at=FIXED_TIME)
    codes = result["chapters"][0]["rejection_codes"]
    assert "MISSING_REQUIRED_FIELD" in codes
    assert "MALFORMED_COMMENTARY_JSON" in codes


def test_duplicate_responses_are_both_rejected(tmp_path):
    candidate, raw = _workspace(tmp_path)
    response = _response("Genesis 1")
    _write(raw / "one.json", response)
    _write(raw / "two.json", response)
    result = import_responses(raw, candidate_root=candidate, imported_at=FIXED_TIME)
    assert result["rejected_count"] == 2
    assert all("DUPLICATE_RESPONSE" in row["rejection_codes"] for row in result["chapters"])


def test_unsupported_synthesis_id_is_rejected(tmp_path):
    candidate, raw = _workspace(tmp_path)
    response = _response("Genesis 1")
    response["response_payload"]["sections"][0]["blocks"][0]["synthesis_ids"] = ["missing"]
    _write(raw / "response.json", response)
    result = import_responses(raw, candidate_root=candidate, imported_at=FIXED_TIME)
    assert "UNKNOWN_SYNTHESIS_ID" in result["chapters"][0]["rejection_codes"]


def test_evidence_outside_synthesis_ancestry_is_rejected(tmp_path):
    candidate, raw = _workspace(tmp_path)
    response = _response("Genesis 1")
    preflight = _read_json(CANARY_ROOT / "canary-preflight.json")
    locked = next(row for row in preflight["chapters"] if row["reference"] == "Genesis 1")
    cited = set(response["response_payload"]["sections"][0]["blocks"][0]["evidence_ids"])
    outside = next(evidence_id for evidence_id in locked["evidence_ids"] if evidence_id not in cited)
    response["response_payload"]["sections"][0]["blocks"][0]["evidence_ids"] = [outside]
    _write(raw / "response.json", response)
    result = import_responses(raw, candidate_root=candidate, imported_at=FIXED_TIME)
    assert "SYNTHESIS_ANCESTRY_MISMATCH" in result["chapters"][0]["rejection_codes"]


def test_accepted_and_rejected_outputs_remain_separate(tmp_path):
    candidate, raw = _workspace(tmp_path)
    _write(raw / "genesis.json", _response("Genesis 1"))
    invalid = _response("Leviticus 16")
    invalid["response_payload"]["sections"][0]["blocks"][0]["synthesis_ids"] = ["missing"]
    _write(raw / "leviticus.json", invalid)
    result = import_responses(raw, candidate_root=candidate, imported_at=FIXED_TIME)
    assert result["accepted_count"] == 1 and result["rejected_count"] == 1
    assert (candidate / "canary/responses/accepted/genesis_001.json").is_file()
    assert not (candidate / "canary/responses/accepted/leviticus_016.json").exists()
    assert (candidate / "canary/responses/rejected/leviticus.json").is_file()


def _gate_row(reference="Genesis 1", before_status="SYNTHESIS_GAP"):
    before = {
        "evidence_availability": "AVAILABLE",
        "richness_status": before_status,
        "section_count": 1,
        "commentary_prose_word_count": 60,
        "unique_evidence_ids_consumed": 1,
        "boilerplate_detected": True,
    }
    after = {
        "richness_status": "RICH_ENOUGH",
        "section_count": 2,
        "commentary_prose_word_count": 100,
        "unique_evidence_ids_consumed": 2,
        "boilerplate_detected": False,
    }
    return {
        "reference": reference,
        "before": before,
        "after": after,
        "deltas": {"evidence_use_delta": 1, "synthesis_use_percentage": 100.0},
        "import_status": "accepted",
        "response_structurally_parsed": True,
        "validation_status": "validated",
        "provenance_complete": True,
        "evidence_and_synthesis_locks_match": True,
        "rejection_codes": [],
        "validation_errors": [],
        "synthesis_validation_errors": [],
    }


def test_partial_response_gate():
    rows = [_gate_row(), {**_gate_row("Leviticus 16"), "import_status": "missing", "validation_status": "not_run", "after": None}]
    status, _ = evaluate_gate(rows, {"raw_response_count": 1, "missing_references": ["Leviticus 16"]})
    assert status == "PARTIAL_RESPONSES"


def test_complete_successful_canary_gate_is_review_only():
    rows = [_gate_row()]
    status, checks = evaluate_gate(rows, {"raw_response_count": 1, "missing_references": []})
    assert status == "CANARY_PASS"
    assert all(checks.values())


def test_comparison_output_is_deterministic_without_responses():
    prepare()
    first = compare()
    first_bytes = (CANARY_ROOT / "canary-comparison.json").read_bytes()
    second = compare()
    assert first == second
    assert first_bytes == (CANARY_ROOT / "canary-comparison.json").read_bytes()
