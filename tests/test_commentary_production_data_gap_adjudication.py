"""Regression coverage for application-owned production DATA_GAP handling."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from framework.commentary.production.handoff import HandoffRunner
from framework.commentary.production.ledger import rebuild_ledger
from framework.commentary.production.normalization import normalize_data_gap_fallback
from framework.commentary.production.runner import _parse_response
from framework.commentary.production.inputs import prepare_chapter
from bhf_agent.chapter_commentary.models import GeneratedMetadata
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "run-04109d5ff664ed80"


def test_true_data_gap_empty_sections_receive_only_application_fallback():
    raw = {"reference": "Numbers 3", "sections": [], "data_gap_fallback": None}
    normalized, audit = normalize_data_gap_fallback(
        raw,
        expected_evidence_availability="DATA_GAP",
        evidence_item_count=0,
        synthesis_unit_count=0,
    )
    assert raw == {"reference": "Numbers 3", "sections": [], "data_gap_fallback": None}
    assert audit["applied"] is True
    assert normalized["data_gap_fallback"] is True
    assert normalized["sections"][0]["blocks"][0]["id"] == "data_gap_notice"


def test_data_gap_renderer_prose_and_nonempty_authorities_cannot_be_normalized():
    prose, prose_audit = normalize_data_gap_fallback(
        {"sections": [{"kind": "chapter_overview"}]},
        expected_evidence_availability="DATA_GAP",
        evidence_item_count=0,
        synthesis_unit_count=0,
    )
    evidence, evidence_audit = normalize_data_gap_fallback(
        {"sections": []},
        expected_evidence_availability="DATA_GAP",
        evidence_item_count=1,
        synthesis_unit_count=0,
    )
    synthesis, synthesis_audit = normalize_data_gap_fallback(
        {"sections": []},
        expected_evidence_availability="DATA_GAP",
        evidence_item_count=0,
        synthesis_unit_count=1,
    )
    assert prose == {"sections": [{"kind": "chapter_overview"}]}
    assert evidence == {"sections": []}
    assert synthesis == {"sections": []}
    assert not prose_audit["applied"]
    assert not evidence_audit["applied"]
    assert not synthesis_audit["applied"]


def _copied_run(tmp_path: Path) -> Path:
    source = REPO_ROOT / ".bhf-data/bhf-commentary-production/v1/runs" / RUN_ID
    target = tmp_path / ".bhf-data/bhf-commentary-production/v1/runs" / RUN_ID
    shutil.copytree(source, target)
    return target


def test_reprocess_existing_raw_preserves_raw_and_original_quarantine_history(tmp_path):
    run_root = _copied_run(tmp_path)
    # The repository fixture is post-adjudication; restore just this copied
    # derived state to the original receipt-backed condition.
    state_path = run_root / "batches/batch-001/state.json"
    copied_state = json.loads(state_path.read_text())
    copied_record = copied_state["chapters"]["2 Kings 11"]
    copied_record["state"] = "QUARANTINED"
    for key in ("accepted_path", "gate_path", "gate_status", "reader_activation", "reader_path", "reader_status", "adjudication_receipt_path", "application_normalization", "derived_validation_path", "historical_quarantine_path", "historical_quarantines"):
        copied_record.pop(key, None)
    state_path.write_text(json.dumps(copied_state), encoding="utf-8")
    raw_path = run_root / "batches/batch-001/raw/attempt-001/2_kings_011.json"
    before = raw_path.read_bytes()
    before_sha = hashlib.sha256(before).hexdigest()

    runner = HandoffRunner(tmp_path, renderer_identity="codex-gpt-5")
    result = runner.reprocess_derived(RUN_ID, ["2 Kings 11"])

    row = result["chapters"][0]
    assert row["status"] == "READJUDICATED"
    assert raw_path.read_bytes() == before
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == before_sha
    state = json.loads((run_root / "batches/batch-001/state.json").read_text())
    record = state["chapters"]["2 Kings 11"]
    assert record["attempt"] == 1
    assert record["state"] == "COMPLETE"
    assert record["historical_quarantines"][0]["rejection_codes"] == ["DATA_GAP_FALLBACK_REQUIRED"]
    assert (tmp_path / record["adjudication_receipt_path"]).is_file()
    assert (tmp_path / record["derived_validation_path"]).is_file()
    repeat = runner.reprocess_derived(RUN_ID, ["2 Kings 11"])
    assert repeat["chapters"][0]["status"] == "SKIPPED_ALREADY_ADJUDICATED"
    assert json.loads(state_path.read_text())["chapters"]["2 Kings 11"]["attempt"] == 1


def test_ledger_separates_quality_quarantine_from_content_quarantine(tmp_path):
    run_root = _copied_run(tmp_path)
    # Reconciliation derives the intended state from the accepted artifact and
    # its Gate receipt while retaining the immutable quality-quarantine record.
    ledger = rebuild_ledger(tmp_path)
    assert ledger["current"]["Exodus 14"]["state"] == "GATE_QUALITY_FAIL"
    assert ledger["dispositions"]["production_quarantined_quality"] == 7
    assert ledger["dispositions"]["production_quarantined_content"] == 2
    assert (run_root / "batches/batch-001/quarantine/attempt-001/exodus_014.json").is_file()


def _canary_validation_codes(book: str, chapter: int) -> set[str]:
    name = f"{book.lower().replace(' ', '_')}_{chapter:03d}"
    raw = REPO_ROOT / ".bhf-data/bhf-commentary-production/v1/runs" / RUN_ID / "batches/batch-001/raw/attempt-001" / f"{name}.json"
    prepared = prepare_chapter(book, chapter)
    payload = dict(_parse_response(raw.read_text()) or {})
    payload["generated_metadata"] = GeneratedMetadata(
        evidence_hash=prepared.bundle.evidence_hash,
        evidence_bundle_version=prepared.bundle.version,
        commentary_schema_version="1.2",
        commentary_prompt_version="1.5",
        model="external_handoff",
        generated_timestamp=None,
        synthesis_hash=prepared.synthesis.synthesis_hash,
        synthesis_schema_version=prepared.synthesis.synthesis_schema_version,
        synthesis_compiler_version=prepared.synthesis.synthesis_compiler_version,
        renderer_label="codex-gpt-5",
    ).to_dict()
    payload["evidence_availability"] = prepared.synthesis.evidence_availability
    payload["status"] = "pending"
    result = validate_chapter_commentary(
        payload, prepared.bundle, expected_evidence_hash=prepared.bundle.evidence_hash,
        expected_prompt_version="1.5", expected_reference=f"{book} {chapter}",
        expected_book=book, expected_chapter=chapter, synthesis=prepared.synthesis,
        expected_synthesis_hash=prepared.synthesis.synthesis_hash,
    )
    return {message.split(":", 1)[0] for message in result.errors}


def test_ruth_confidence_and_hebrews_ancestry_rejections_remain_content_rejections():
    assert "CONFIDENCE_EXCEEDS_EVIDENCE" in _canary_validation_codes("Ruth", 2)
    hebrews = _canary_validation_codes("Hebrews", 8)
    assert {"SYNTHESIS_ANCESTRY_MISMATCH", "UNKNOWN_EVIDENCE_ID"}.issubset(hebrews)
