"""Focused regression coverage for the bounded v1.2 enrichment artifact."""

from __future__ import annotations

import json
from pathlib import Path

from tools.commentary_v12_five_chapter_structured_enrichment import (
    ARTIFACT_ROOT,
    safe_canonical_text,
)
from tools.commentary_v12_post_applicability_coverage_census import contract_snapshot


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_contracts_are_unchanged() -> None:
    snapshot = contract_snapshot()
    assert snapshot["all_protected_contracts_unchanged"] is True


def test_final_artifact_records_one_clean_generation_per_passing_chapter() -> None:
    report = json.loads((ARTIFACT_ROOT / "final-report-v3.json").read_text(encoding="utf-8"))
    validation = report["model_validation"]
    assert validation["generation_count"] == 5
    assert validation["structurally_valid_count"] == 5
    assert validation["quality_pass_count"] == 5
    assert validation["high_dump_count"] == 0
    assert all(row["generation_count"] == 1 for row in validation["chapters"])
    assert all(row["ancestry_validation"]["ancestry_mismatch_count"] == 0 for row in validation["chapters"])
    assert all(row["readability_result"] == "PASS" for row in validation["chapters"])
    assert all(row["normal_reader_usefulness"] == "PASS" for row in validation["chapters"])


def test_psalm_2_uses_bounded_safe_text_without_mutating_asv() -> None:
    safe_text, audit = safe_canonical_text("Psalms", 2)
    assert "Psalm 3 A Psalm of David" not in safe_text
    assert audit["contamination_removed"] is True
    assert audit["dataset_mutated"] is False
    raw = Path(ROOT / "bhf_agent/data/asv_bible.json").read_text(encoding="utf-8")
    assert "Psalm 3 A Psalm of David" in raw
