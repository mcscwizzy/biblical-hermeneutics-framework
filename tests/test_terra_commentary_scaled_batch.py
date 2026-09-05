from __future__ import annotations

import json
import shutil
from pathlib import Path

from tools.terra_commentary_scaled_batch import DEFAULT_BATCH_ROOT, prose_audit, run


def test_scaled_terra_batch_revalidates_and_generates_only_locked_members(tmp_path):
    result = run(output=tmp_path / "terra", report_destination=tmp_path / "report.md")

    assert result["status"] == "READY_FOR_BATCH_002"
    assert result["lock_revalidation"]["locks_revalidated"] == 50
    assert result["lock_revalidation"]["stale_locks"] == []
    assert result["validation"]["valid"] == 50
    assert result["validation"]["invalid"] == 0
    assert result["quarantined_chapters_not_generated"] is True
    assert len(list((tmp_path / "terra" / "chapters").glob("*.json"))) == 50


def test_scaled_terra_batch_stale_lock_stops_before_chapter_generation(tmp_path):
    batch_root = tmp_path / "batch-001"
    shutil.copytree(DEFAULT_BATCH_ROOT, batch_root)
    certification_path = batch_root / "evidence-certification.json"
    certification = json.loads(certification_path.read_text())
    certification["chapters"][0]["locked_evidence_hash"] = "stale-lock"
    certification_path.write_text(json.dumps(certification))

    result = run(batch_root, tmp_path / "terra", tmp_path / "report.md")

    assert result["status"] == "STALE_LOCK"
    assert len(result["lock_revalidation"]["stale_locks"]) == 1
    assert not (tmp_path / "terra" / "chapters").exists()


def test_scaled_terra_audit_rejects_internal_language_and_lost_dispute_semantics():
    class Item:
        id = "item"
        relevance_metadata = {"dispute_status": "disputed"}

    class Bundle:
        evidence_by_id = {"item": Item()}

    candidate = {
        "evidence_availability": "THIN",
        "sections": [{
            "kind": "chapter_overview",
            "blocks": [{
                "text": "This EvidenceBundle gives a final answer.",
                "evidence_ids": ["item"],
                "verse_refs": ["Luke 1:1"],
                "interpretation_level": "fact",
            }],
        }],
    }

    flags = prose_audit(candidate, Bundle())

    assert "READER_UNFRIENDLY" in flags
    assert "UNCERTAINTY_LOST" in flags
