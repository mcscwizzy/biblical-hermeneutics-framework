from __future__ import annotations

import json
from pathlib import Path

import pytest

from framework.commentary.remediation import (
    MAX_AUTOMATIC_REGENERATION_ATTEMPTS,
    regeneration_eligibility,
)


def test_reader_unfriendly_with_clean_integrity_allows_one_retry():
    eligible, diagnostics = regeneration_eligibility(
        ["READER_UNFRIENDLY"], integrity_clean=True, evidence_lock_valid=True, attempts=0
    )
    assert eligible is True
    assert diagnostics == []


@pytest.mark.parametrize("finding", [
    "provenance failure",
    "hash disagreement",
    "unsupported claim",
    "semantic leakage",
])
def test_reader_unfriendly_plus_integrity_finding_is_not_retryable(finding: str):
    eligible, diagnostics = regeneration_eligibility(
        ["READER_UNFRIENDLY", finding], integrity_clean=False, evidence_lock_valid=False, attempts=0
    )
    assert eligible is False
    assert diagnostics


def test_reader_unfriendly_retry_limit_is_strict_and_cannot_reset():
    eligible, diagnostics = regeneration_eligibility(
        ["READER_UNFRIENDLY"], integrity_clean=True, evidence_lock_valid=True,
        attempts=MAX_AUTOMATIC_REGENERATION_ATTEMPTS,
    )
    assert eligible is False
    assert any("limit" in value for value in diagnostics)
    eligible, diagnostics = regeneration_eligibility(
        ["READER_UNFRIENDLY"], integrity_clean=True, evidence_lock_valid=True, attempts=-1
    )
    assert eligible is False
    assert any("negative" in value for value in diagnostics)


def test_non_allowlisted_quality_finding_is_not_retryable():
    eligible, diagnostics = regeneration_eligibility(
        ["READER_UNFRIENDLY", "EVIDENCE_DUMP"], integrity_clean=True, evidence_lock_valid=True, attempts=0
    )
    assert eligible is False
    assert any("non-allowlisted" in value for value in diagnostics)


def test_live_batch_records_bounded_retry_and_successful_recertification():
    # This is intentionally a repository-state regression: it ensures the
    # production audit retains the original failure instead of flattening it.
    root = Path(__file__).resolve().parents[1]
    batch = root / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-004"
    initial_path = batch / "post-generation-initial-report.json"
    final_path = batch / "prose-certification.json"
    remediation_path = batch / "remediation-report.json"
    if not initial_path.exists() or not final_path.exists() or not remediation_path.exists():
        pytest.skip("Batch 004 remediation artifacts are not present in this checkout")
    initial = json.loads(initial_path.read_text(encoding="utf-8"))
    final = json.loads(final_path.read_text(encoding="utf-8"))
    remediation = json.loads(remediation_path.read_text(encoding="utf-8"))
    assert initial["status"] == "NO_GO"
    assert initial["disposition_counts"] == {"PASS": 147, "QUARANTINE": 3}
    assert final["status"] == "GO"
    assert final["disposition_counts"] == {"PASS": 150}
    assert final["regeneration_attempts"] == 3
    assert remediation["status"] == "CERTIFIED"
    assert all(row["regeneration_attempts"] == 1 for row in remediation["targets"])
    assert all(row["final_disposition"] == "PASS" for row in remediation["targets"])
    assert all(row["evidence_hash_before"] == row["evidence_hash_after"] == row["evidence_hash_locked"] for row in remediation["targets"])
    assert all(row["evidence_ids_before"] == row["evidence_ids_after"] for row in remediation["targets"])
    assert all(Path(root / row["original_path"]).exists() for row in remediation["targets"])
