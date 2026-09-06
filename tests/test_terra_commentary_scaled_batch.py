from __future__ import annotations

import json
import shutil
from pathlib import Path

from tools.terra_commentary_scaled_batch import ROOT, prose_audit, run


BATCH_003_ROOT = ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-scale" / "batch-003"


def test_scaled_terra_batch_revalidates_and_generates_only_locked_members(tmp_path):
    result = run(BATCH_003_ROOT, tmp_path / "terra", tmp_path / "report.md")

    assert result["status"] == "READY_FOR_BATCH_004"
    assert result["lock_revalidation"]["locks_revalidated"] == 150
    assert result["lock_revalidation"]["stale_locks"] == []
    assert result["validation"]["valid"] == 150
    assert result["validation"]["invalid"] == 0
    assert result["quarantined_chapters_not_generated"] is True
    assert len(list((tmp_path / "terra" / "chapters").glob("*.json"))) == 150
    acts = json.loads((tmp_path / "terra" / "chapters" / "john_005.json").read_text())
    cited_ids = {
        evidence_id
        for section in acts["sections"]
        for block in section["blocks"]
        for evidence_id in block["evidence_ids"]
    }
    assert "john-5-variant" in cited_ids
    assert result["quality"]["possible_evidence_review"] == []


def test_scaled_terra_batch_stale_lock_stops_before_chapter_generation(tmp_path):
    batch_root = tmp_path / "batch-003"
    shutil.copytree(BATCH_003_ROOT, batch_root)
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


def test_textual_dispute_status_alone_is_not_textual_witness_material():
    from tools.terra_commentary_scaled_batch import _is_textual_witness_material

    class Item:
        claim = "A historical model remains disputed."
        relevance_metadata = {"dispute_status": "textual_variant"}

    assert _is_textual_witness_material(Item()) is False


def test_prose_audit_allows_ordinary_historical_use_of_model():
    class Item:
        id = "item"
        relevance_metadata = {"dispute_status": "not_disputed"}

    class Bundle:
        evidence_by_id = {"item": Item()}

    candidate = {
        "evidence_availability": "THIN",
        "sections": [{
            "kind": "chapter_overview",
            "blocks": [{
                "text": "One historical model remains disputed.",
                "evidence_ids": ["item"],
                "verse_refs": ["Luke 1:1"],
                "interpretation_level": "fact",
            }],
        }],
    }

    assert "READER_UNFRIENDLY" not in prose_audit(candidate, Bundle())
