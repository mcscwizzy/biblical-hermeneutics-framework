from __future__ import annotations

import json
from pathlib import Path

import pytest

from framework.commentary.remediation_groups import (
    MAX_REMEDIATION_GROUP_SIZE,
    build_remediation_groups,
    chunk_references,
)
from tools import terra_commentary_remediation as runner


TARGETS = [
    "Deuteronomy 32",
    "Psalms 119",
    "Daniel 10",
    "Isaiah 65",
    "Ezekiel 40",
    "2 Chronicles 32",
    "1 Samuel 4",
]


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, [1]), (2, [2]), (3, [3]), (4, [3, 1]), (7, [3, 3, 1]), (10, [3, 3, 3, 1])],
)
def test_remediation_chunk_sizes_are_bounded_and_deterministic(count: int, expected: list[int]):
    references = [f"Genesis {index}" for index in range(1, count + 1)]
    groups = chunk_references(reversed(references))
    assert [len(group) for group in groups] == expected
    assert all(len(group) <= MAX_REMEDIATION_GROUP_SIZE for group in groups)
    assert chunk_references(references) == groups


def test_remediation_chunking_uses_canonical_reference_order():
    references = ["Psalms 119", "1 Samuel 4", "Deuteronomy 32", "2 Chronicles 32"]
    assert chunk_references(references, maximum=2) == [
        ["Deuteronomy 32", "1 Samuel 4"],
        ["2 Chronicles 32", "Psalms 119"],
    ]


def test_group_plan_records_attempt_one_without_using_group_number_as_attempt():
    groups = build_remediation_groups(TARGETS)
    assert [group["group_id"] for group in groups] == ["group-001", "group-002", "group-003"]
    assert all(group["attempt"] == 1 for group in groups)
    assert all(len(group["references"]) <= 3 for group in groups)


def test_runner_rejects_more_than_three_direct_targets_without_mutation(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    batch = root / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-007"
    monkeypatch.setattr(
        runner,
        "revalidate_locks",
        lambda terra_input, certification: ({"status": "PASS", "stale_locks": []}, {}),
    )
    with pytest.raises(RuntimeError, match="one to three chapters"):
        runner.regenerate(batch, TARGETS[:4], attempt=1)


def test_runner_rejects_second_automatic_attempt_before_loading_artifacts():
    with pytest.raises(RuntimeError, match="exactly one attempt"):
        runner.regenerate(Path("/does/not/exist"), ["Genesis 1"], attempt=2)


def test_live_batch_has_three_complete_group_reports_and_one_attempt_per_chapter():
    root = Path(__file__).resolve().parents[1]
    batch = root / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-007"
    plan = json.loads((batch / "remediation-plan.json").read_text(encoding="utf-8"))
    assert [group["status"] for group in plan["groups"]] == ["COMPLETE"] * 3
    assert all(group["attempt"] == 1 for group in plan["groups"])
    assert plan["completed_groups"] == ["group-001", "group-002", "group-003"]

    report = json.loads((batch / "remediation-report.json").read_text(encoding="utf-8"))
    assert report["status"] == "CERTIFIED"
    assert report["policy"]["attempt_scope"] == "per_chapter"
    assert report["policy"]["maximum_chapters_per_runner_invocation"] == 3
    assert {row["reference"] for row in report["targets"]} == set(TARGETS)
    assert all(row["regeneration_attempts"] == 1 for row in report["targets"])
    assert all(row["evidence_ids_before"] == row["evidence_ids_after"] for row in report["targets"])
    assert all(
        row["evidence_hash_before"] == row["evidence_hash_after"] == row["evidence_hash_locked"]
        for row in report["targets"]
    )
    assert all(Path(root / row["original_path"]).exists() for row in report["targets"])
    assert all(Path(root / group["report_path"]).exists() for group in report["groups"])


def test_live_batch_recertification_is_full_batch_and_pass_chapters_are_not_targets():
    root = Path(__file__).resolve().parents[1]
    batch = root / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-007"
    report = json.loads((batch / "post-generation-report.json").read_text(encoding="utf-8"))
    assert report["status"] == "GO"
    assert report["disposition_counts"] == {"PASS": 150}
    assert report["final_accepted_count"] == 150
    remediation = json.loads((batch / "remediation-report.json").read_text(encoding="utf-8"))
    assert {row["reference"] for row in remediation["targets"]} == set(TARGETS)
    assert len(remediation["targets"]) == 7


def test_group_report_corruption_is_not_accepted():
    from framework.commentary.orchestrator import _validate_group_report

    group = {"group_id": "group-001", "references": ["Genesis 1"]}
    report = {
        "status": "READY_FOR_RECERTIFICATION",
        "group_id": "group-001",
        "references": ["Genesis 1"],
        "lock_revalidation": {"status": "PASS"},
        "targets": [{
            "reference": "Genesis 1",
            "regeneration_attempts": 1,
            "quality_flags_after": [],
            "evidence_ids_before": ["e-1"],
            "evidence_ids_after": ["e-2"],
            "evidence_hash_before": "h",
            "evidence_hash_after": "h",
            "evidence_hash_locked": "h",
        }],
    }
    with pytest.raises(Exception, match="evidence IDs"):
        _validate_group_report(report, group)
