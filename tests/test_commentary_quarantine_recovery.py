from __future__ import annotations

import json
from pathlib import Path

import pytest

from framework.commentary.recovery import (
    RecoveryLedgerError,
    build_recovery_ledger,
    load_recovery_ledger,
    recoverable_unconsumed_references,
    recovery_accounting,
)
from tools.commentary_v11_quarantine_recovery import adjudicate, build_inventory


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _quarantine(reference: str, reason: str, batch: str) -> dict[str, object]:
    return {
        "reference": reference,
        "reason_codes": [reason],
        "evidence_ids": [f"{reference}:evidence"],
        "ckl_parent_records": [f"{reference}:parent"],
        "source_batch": batch,
    }


def test_inventory_collapses_duplicate_quarantine_identity_and_preserves_history(tmp_path):
    scale = tmp_path / "scale"
    _write(scale / "batch-001/quarantine-report.json", {"chapters": [_quarantine("Genesis 1", "CROSS_BOOK_PARENT_REUSE", "batch-001")]})
    _write(scale / "batch-002/quarantine-report.json", {"chapters": [_quarantine("Genesis 1", "EVIDENCE_HASH_DISAGREEMENT", "batch-002")]})
    output = tmp_path / "inventory.json"
    result = build_inventory(scale, output)
    assert result["raw_quarantine_records"] == 2
    assert result["unique_quarantined_chapters"] == 1
    chapter = result["chapters"][0]
    assert chapter["source_quarantine_batches"] == ["batch-001", "batch-002"]
    assert chapter["historical_reason_codes"] == ["CROSS_BOOK_PARENT_REUSE", "EVIDENCE_HASH_DISAGREEMENT"]
    assert chapter["adjudication"] == "PENDING_CURRENT_PREFLIGHT"


def test_adjudication_requires_current_pass_and_keeps_ckl_queue(tmp_path):
    scale = tmp_path / "scale"
    rows = [
        _quarantine("Genesis 1", "CROSS_BOOK_PARENT_REUSE", "batch-001"),
        _quarantine("Genesis 2", "EVIDENCE_HASH_DISAGREEMENT", "batch-001"),
        _quarantine("Genesis 3", "WORD_STUDY_BROAD_PARENT_ANCHOR", "batch-001"),
        _quarantine("Genesis 4", "PRESENTATION_ROLE_MISMATCH", "batch-001"),
        _quarantine("Genesis 5", "CROSS_BOOK_PARENT_REUSE", "batch-001"),
    ]
    _write(scale / "batch-001/quarantine-report.json", {"chapters": rows})
    _write(scale / "batch-002/batch-manifest.json", {"final_references": ["Genesis 5"]})
    inventory = tmp_path / "inventory.json"
    build_inventory(scale, inventory)
    blocked = scale / ".batch-007.work/blocked-report.json"
    _write(blocked, {
        "preflight": {
            "evaluated": [
                {"reference": "Genesis 1", "status": "PASS", "availability": "AVAILABLE", "evidence_ids": ["e1"], "evidence_hash": "h1", "quarantine_reason_codes": [], "json_sqlite_agreement": {"result_ids_agree": True, "evidence_ids_agree": True, "bundle_hash_agree": True}},
                {"reference": "Genesis 2", "status": "QUARANTINE", "availability": "THIN", "evidence_ids": ["e2"], "evidence_hash": "h2", "quarantine_reason_codes": ["EVIDENCE_HASH_DISAGREEMENT"], "json_sqlite_agreement": {"result_ids_agree": False}},
                {"reference": "Genesis 3", "status": "QUARANTINE", "availability": "THIN", "evidence_ids": ["e3"], "evidence_hash": "h3", "quarantine_reason_codes": ["WORD_STUDY_BROAD_PARENT_ANCHOR"], "json_sqlite_agreement": {"result_ids_agree": True}},
                {"reference": "Genesis 4", "status": "DATA_GAP", "availability": "DATA_GAP", "evidence_ids": [], "evidence_hash": None, "quarantine_reason_codes": ["DATA_GAP"], "json_sqlite_agreement": {}},
            ],
        },
    })
    output = tmp_path / "adjudicated.json"
    queue = tmp_path / "queue.json"
    result = adjudicate(scale, inventory, "batch-007", output, queue)
    assert result["adjudication_counts"] == {
        "ALREADY_RESOLVED": 1,
        "DATA_GAP": 1,
        "RECOVERABLE": 1,
        "REQUIRES_CKL_REMEDIATION": 1,
        "STILL_QUARANTINED": 1,
    }
    assert result["recoverable_references"] == ["Genesis 1"]
    assert json.loads(queue.read_text(encoding="utf-8"))["chapters"][0]["reference"] == "Genesis 3"
    assert result["ckl_mutated"] is False


def test_adjudication_can_use_isolated_current_preflight(tmp_path):
    scale = tmp_path / "scale"
    _write(scale / "batch-001/quarantine-report.json", {"chapters": [_quarantine("Genesis 1", "CROSS_BOOK_PARENT_REUSE", "batch-001")]})
    inventory = tmp_path / "inventory.json"
    build_inventory(scale, inventory)
    isolated = tmp_path / "isolated-preflight.json"
    _write(isolated, {"evaluated": [{"reference": "Genesis 1", "status": "PASS", "availability": "AVAILABLE", "quarantine_reason_codes": []}]})
    result = adjudicate(
        scale,
        inventory,
        "batch-007",
        tmp_path / "result.json",
        preflight_report=isolated,
    )
    assert result["adjudication_counts"] == {"RECOVERABLE": 1}
    assert result["preflight_source"] == str(isolated)


def test_corpus_ledger_reconciles_authoritative_257_population_and_consumption():
    root = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale")
    ledger = root / "quarantine-recovery-ledger.json"
    payload = load_recovery_ledger(ledger, scale_root=root)
    assert payload["historical_quarantine_count"] == 257
    assert payload["counts"] == {
        "historical_quarantine": 257,
        "prior_quarantine_recoverable": 257,
        "prior_quarantine_recovered_already_generated": 150,
        "prior_quarantine_recovered_consumed_locked": 107,
        "prior_quarantine_recovered_unconsumed": 0,
        "prior_quarantine_unadjudicated": 0,
        "prior_quarantine_still_blocked": 0,
        "unresolved_quarantine": 0,
    }
    assert len(recoverable_unconsumed_references(payload)) == 0


def test_corpus_ledger_rebuild_is_deterministic(tmp_path):
    scale = tmp_path / "scale"
    _write(scale / "batch-001/quarantine-report.json", {"chapters": [_quarantine("Genesis 1", "CROSS_BOOK_PARENT_REUSE", "batch-001")]})
    _write(scale / "batch-001/batch-manifest.json", {"status": "LOCKED", "created_at": "2026-01-01T00:00:00Z", "final_references": ["Genesis 1"]})
    base = tmp_path / "base.json"
    final_four = tmp_path / "final-four.json"
    _write(base, {"manifest_version": "base-v1", "generated_at": "2026-01-02T00:00:00Z", "chapters": [{**_quarantine("Genesis 1", "CROSS_BOOK_PARENT_REUSE", "batch-001"), "adjudication": "RECOVERABLE", "current_preflight": {"evidence_ids": ["e1"], "evidence_hash": "h1", "json_sqlite_agreement": {}}}]})
    _write(final_four, {"historical_quarantine_population": 1, "recoverable": 1, "still_quarantined": 0, "chapters": []})
    first = build_recovery_ledger(scale, tmp_path / "one.json", repo_root=tmp_path, base_adjudication=base, final_four_adjudication=final_four)
    second = build_recovery_ledger(scale, tmp_path / "two.json", repo_root=tmp_path, base_adjudication=base, final_four_adjudication=final_four)
    assert first == second
    assert first["counts"]["prior_quarantine_recovered_already_generated"] == 0
    assert first["counts"]["prior_quarantine_recovered_consumed_locked"] == 1


def test_recovery_accounting_preserves_150_consumed_107_pending_transition():
    chapters = [
        {"reference": f"Genesis {number}", "adjudication": "RECOVERABLE", "consumption_status": "CONSUMED_GENERATED"}
        for number in range(1, 151)
    ] + [
        {"reference": f"Exodus {number}", "adjudication": "RECOVERABLE", "consumption_status": "PENDING_CONSUMPTION"}
        for number in range(1, 108)
    ]
    counts = recovery_accounting({"chapters": chapters})
    assert counts["historical_quarantine"] == 257
    assert counts["prior_quarantine_recovered_already_generated"] == 150
    assert counts["prior_quarantine_recovered_unconsumed"] == 107


def test_corrupt_ledger_source_hash_fails_closed(tmp_path):
    root = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale")
    payload = json.loads((root / "quarantine-recovery-ledger.json").read_text(encoding="utf-8"))
    payload["source_artifacts"][0]["sha256"] = "0" * 64
    path = tmp_path / "ledger.json"
    _write(path, payload)
    with pytest.raises(RecoveryLedgerError, match="source hash mismatch"):
        load_recovery_ledger(path, repo_root=Path("."), scale_root=root)


def test_missing_ledger_source_artifact_fails_closed(tmp_path):
    root = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale")
    payload = json.loads((root / "quarantine-recovery-ledger.json").read_text(encoding="utf-8"))
    payload["source_artifacts"][0]["path"] = "missing-adjudication.json"
    path = tmp_path / "ledger.json"
    _write(path, payload)
    with pytest.raises(RecoveryLedgerError, match="missing"):
        load_recovery_ledger(path, repo_root=Path("."), scale_root=root)
