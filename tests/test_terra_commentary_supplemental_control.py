from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.terra_commentary_supplemental_control import (
    EXPECTED_IDS,
    REFERENCE,
    TERRA_ROOT,
    run,
)


def _fingerprint_primary() -> str:
    digest = hashlib.sha256()
    for path in sorted((TERRA_ROOT / "chapters").glob("*.json")):
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_supplemental_samuel_control_is_locked_validated_and_does_not_touch_primary(tmp_path):
    before = _fingerprint_primary()
    source_review = TERRA_ROOT / "terra-canary-review.json"
    source_report = Path("docs/commentary-v1.1-terra-canary-report.md")
    review = tmp_path / "review.json"
    report = tmp_path / "report.md"
    review.write_bytes(source_review.read_bytes())
    report.write_bytes(source_report.read_bytes())

    result = run(tmp_path / "candidate", tmp_path / "certification.json", review, report)

    assert _fingerprint_primary() == before
    assert result["primary_chapters_unchanged"] is True
    certification = json.loads((tmp_path / "certification.json").read_text())
    assert certification["status"] == "LOCKED"
    assert certification["availability"] == "THIN"
    assert certification["evidence_bundle_version"] == "1.1"
    assert certification["evidence_hash_version"] == "2"
    assert certification["evidence_ids"] == EXPECTED_IDS
    assert certification["json_sqlite_agreement"]["result_ids_agree"] is True
    assert certification["json_sqlite_agreement"]["bundle_hash_agree"] is True
    assert result["validation"] == {"reference": REFERENCE, "valid": True, "errors": []}
    assert result["supplemental"]["flags"] == []
    assert result["supplemental"]["apparition_uncertainty"]["preserved"] is True
    candidate = json.loads((tmp_path / "candidate" / "chapters" / "1_samuel_028.json").read_text())
    assert candidate["evidence_availability"] == "THIN"
    assert [section["kind"] for section in candidate["sections"]] == ["chapter_overview", "interpretive_questions"]
    assert candidate["sections"][1]["blocks"][0]["interpretation_level"] == "disputed"
    updated = json.loads(review.read_text())
    assert updated["primary_canary"]["chapters_reviewed"] == 25
    assert updated["supplemental_integrity_controls"]["validated"] == 1
    assert updated["total_prose_artifacts_reviewed"] == 26
