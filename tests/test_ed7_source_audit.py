from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs/evidence-depth/ed7/source-verification-results.json"
INVENTORY_PATH = ROOT / "docs/evidence-depth/ed3/evidence-review-inventory.csv"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def test_ed7_audits_every_ed3_record_through_two_distinct_passes() -> None:
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    rows = _read_csv(INVENTORY_PATH)
    records = audit["records"]
    by_id = {record["stable_ckl_id"]: record for record in records}
    expected_ids = {
        f"ckl:{row['book_id']}#evidence:{row['evidence_id']}" for row in rows
    }

    assert len(rows) == 99
    assert len(records) == 99
    assert len(by_id) == 99
    assert set(by_id) == expected_ids
    assert audit["audit_method"]["independent_model_pass_used"] is False
    assert audit["audit_method"]["pass_a"]["name"] == "source_and_textual_verification"
    assert audit["audit_method"]["pass_b"]["name"] == "critical_challenge"

    for record in records:
        assert record["pass_a"]["outcome"] in {
            "supported_with_qualifications",
            "source_inaccessible_or_insufficiently_verified",
        }
        assert record["pass_a"]["materials_inspected"]
        assert record["pass_a"]["source_access_limit"]
        assert record["pass_b"]["challenge"]
        assert record["pass_b"]["unresolved_objections"]
        assert record["governance"]["human_review_required"] is True
        assert record["governance"]["review_status"] == "in_review"
        assert record["governance"]["content_status"] == "draft"
        assert record["governance"]["human_approval_recorded"] is False


def test_ed7_outcome_summary_keeps_unverified_and_historically_corrected_distinct() -> None:
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    summary = audit["summary"]["current_outcome_counts"]

    assert summary == {
        "source_checked_supported": 0,
        "supported_with_qualifications": 28,
        "correction_required": 0,
        "source_inaccessible_or_insufficiently_verified": 71,
        "unsupported_by_available_evidence": 0,
    }
    assert audit["summary"]["prior_ed3_corrections_already_applied"] == 1


def test_ed7_records_hash_and_inspects_each_existing_review_packet() -> None:
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

    for record in audit["records"]:
        packet = ROOT / record["packet"]["path"]
        packet_bytes = packet.read_bytes()
        assert re.fullmatch(r"[0-9a-f]{64}", record["packet"]["sha256"])
        assert hashlib.sha256(packet_bytes).hexdigest() == record["packet"]["sha256"]
        assert f"Human scholarly review: {record['evidence_id']}" in packet_bytes.decode("utf-8")
