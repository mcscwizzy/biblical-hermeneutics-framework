"""Integrity and boundary checks for the Genesis Commentary D3A audit."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D1 = ROOT / ".bhf-data/bhf-commentary-candidates/genesis-commentary-refresh-d1"
D2 = ROOT / ".bhf-data/bhf-commentary-candidates/genesis-commentary-refresh-d2"
D3 = ROOT / ".bhf-data/bhf-commentary-candidates/genesis-commentary-refresh-d3a"
RELEASE = ROOT / ".bhf-data/bhf-commentary-v1.2"
REFERENCES = [f"Genesis {chapter}" for chapter in range(2, 51)]
RISK_REFERENCES = [
    f"Genesis {chapter}"
    for chapter in [3, 6, 9, 11, 18, 19, 22, 28, 32, 34, 37, 38, 41, 45, 46, 49, 50]
]
RECOMMENDATIONS = {
    "RECOMMEND_APPROVE",
    "RECOMMEND_REJECT",
    "NEEDS_REVISION",
    "HUMAN_DECISION_REQUIRED",
}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def test_d3a_reviews_exactly_the_49_immutable_d2_candidates():
    d2_manifest_path = D2 / "candidate-manifest.json"
    d2_manifest = _json(d2_manifest_path)
    integrity = _json(D3 / "candidate-integrity-verification.json")
    recommendation_manifest = _json(D3 / "approval-recommendation-manifest.json")
    digest = hashlib.sha256(d2_manifest_path.read_bytes()).hexdigest()

    assert digest == integrity["d2_candidate_manifest_sha256"]
    assert digest == recommendation_manifest["candidate_manifest_sha256"]
    assert d2_manifest["expected_references"] == REFERENCES
    assert set(d2_manifest["candidates"]) == set(REFERENCES)
    assert integrity["candidate_count"] == 49
    assert integrity["exact_candidate_set"] is True
    assert integrity["all_candidate_hashes_match"] is True
    assert integrity["all_d1_packet_identities_match"] is True
    assert integrity["all_evidence_synthesis_lineages_match"] is True
    assert integrity["all_technical_validations_pass"] is True

    candidate_files = sorted(path.name for path in (D2 / "candidates").glob("*.json"))
    assert candidate_files == [f"genesis_{chapter:03}.json" for chapter in range(2, 51)]
    assert not (D2 / "candidates/genesis_001.json").exists()
    assert not [path for path in (D2 / "candidates").glob("*.json") if not path.name.startswith("genesis_")]

    for reference in REFERENCES:
        record = d2_manifest["candidates"][reference]
        candidate_path = D2 / record["canonical_candidate_path"]
        assert _sha(candidate_path) == record["candidate_artifact_sha256"]


def test_every_candidate_has_one_recommendation_and_all_risk_chapters_are_reviewed():
    manifest = _json(D3 / "approval-recommendation-manifest.json")
    review = _json(D3 / "substantive-review.json")
    risk = _json(D3 / "risk-chapter-review.json")
    ordinary = _json(D3 / "ordinary-chapter-review.json")

    assert [row["reference"] for row in manifest["recommendations"]] == REFERENCES
    assert [row["reference"] for row in review["recommendations"]] == REFERENCES
    assert len(manifest["recommendations"]) == len(review["recommendations"]) == 49
    for row in manifest["recommendations"]:
        assert row["substantive_recommendation"] in RECOMMENDATIONS
        assert row["substantive_recommendation"] == "RECOMMEND_APPROVE"
        assert row["human_approval_state"] == "NOT_YET_PROVIDED"
        assert "APPROVED" != row["substantive_recommendation"]
        assert "EXPLICIT_HUMAN_APPROVAL" != row["substantive_recommendation"]

    assert risk["risk_chapter_count"] == 17
    assert [row["reference"] for row in risk["reviews"]] == RISK_REFERENCES
    assert all(row["relevant_candidate_language"] for row in risk["reviews"])
    assert all(row["recommendation"] == "RECOMMEND_APPROVE" for row in risk["reviews"])
    assert ordinary["ordinary_chapter_count"] == 32
    assert len(ordinary["reviews"]) == 32
    assert not set(row["reference"] for row in ordinary["reviews"]) & set(RISK_REFERENCES)


def test_proposed_set_is_exact_and_still_awaits_explicit_human_approval():
    proposed = _json(D3 / "proposed-approval-set.json")
    d2_manifest = _json(D2 / "candidate-manifest.json")
    expected = [
        {
            "reference": reference,
            "candidate_sha256": d2_manifest["candidates"][reference]["candidate_artifact_sha256"],
        }
        for reference in REFERENCES
    ]
    assert proposed["state"] == "AWAITING_EXPLICIT_HUMAN_APPROVAL"
    assert proposed["approval_obtained"] is False
    assert proposed["human_approval_state"] == "NOT_YET_PROVIDED"
    assert proposed["candidate_manifest_sha256"] == _sha(D2 / "candidate-manifest.json")
    assert proposed["candidate_count"] == 49
    assert proposed["candidate_set_complete"] is True
    assert proposed["candidates"] == expected
    assert proposed["references"] == REFERENCES
    assert "APPROVED" not in proposed["state"]
    assert proposed["state"] != "EXPLICIT_HUMAN_APPROVAL"
    assert proposed.get("status") != "EXPLICIT_HUMAN_APPROVAL"


def test_production_controls_release_and_reader_remain_unchanged():
    genesis1 = _json(D3 / "genesis-1-control.json")
    non_genesis = _json(D3 / "non-genesis-controls.json")
    freeze = _json(D3 / "published-release-tree-verification.json")
    immutability = _json(D3 / "d1-d2-immutability-verification.json")
    d1_snapshot = _json(D1 / "published-release-tree-before.json")
    actual_release = {
        path.relative_to(RELEASE).as_posix(): _sha(path)
        for path in sorted(RELEASE.rglob("*"))
        if path.is_file()
    }

    assert genesis1["candidate_excluded"] is True
    assert genesis1["published_artifact_unchanged"] is True
    assert genesis1["source_lineage_unchanged"] is True
    assert non_genesis["no_non_genesis_candidate"] is True
    assert set(non_genesis["controls"]) == {
        "Exodus 14",
        "Psalms 76",
        "Isaiah 36",
        "Acts 16",
        "Revelation 18",
    }
    assert all(
        row.get("artifact_sha256_matches", row.get("release_artifact_absent")) is True
        for row in non_genesis["controls"].values()
    )
    assert freeze["complete_release_tree_equality"] is True
    assert freeze["expected_file_count"] == freeze["actual_file_count"] == 974
    assert freeze["release_tree_files_sha256"] == d1_snapshot["release_tree_files_sha256"]
    assert actual_release == d1_snapshot["release_tree_files_sha256"]
    assert freeze["manifest_sha256_expected"] == freeze["manifest_sha256_actual"]
    assert freeze["checksum_index_sha256_expected"] == freeze["checksum_index_sha256_actual"]

    assert _git("rev-parse", "HEAD:.bhf-data/bhf-commentary-candidates/genesis-commentary-refresh-d1") == immutability[
        "d1_tree_oid_at_base"
    ]
    assert _git("rev-parse", "HEAD:.bhf-data/bhf-commentary-candidates/genesis-commentary-refresh-d2") == immutability[
        "d2_tree_oid_at_base"
    ]
    assert _git("rev-parse", "HEAD:framework") == immutability["production_reader_code_unchanged_baseline_tree_oid"]
    assert _git("rev-parse", "HEAD:.bhf-data/bhf-commentary-v1.2") == immutability[
        "published_release_root_tree_oid_at_base"
    ]
    assert _git("status", "--porcelain", "--", str(D1.relative_to(ROOT)), str(D2.relative_to(ROOT)), str(RELEASE.relative_to(ROOT)), "framework") == ""
    assert not subprocess.run(
        ["git", "diff", "--quiet", "origin/master", "--", str(D1.relative_to(ROOT)), str(D2.relative_to(ROOT)), str(RELEASE.relative_to(ROOT)), "framework"],
        cwd=ROOT,
        check=False,
    ).returncode


def test_d3a_did_not_promote_or_change_candidate_prose():
    report = _json(D3 / "validation-report.json")
    d2_manifest = _json(D2 / "candidate-manifest.json")
    assert report["promotion_occurred"] is False
    assert report["deployment_occurred"] is False
    assert report["merge_occurred"] is False
    assert not (D2 / "approval-manifest.json").exists()
    for reference in REFERENCES:
        row = d2_manifest["candidates"][reference]
        assert _sha(D2 / row["canonical_candidate_path"]) == row["candidate_artifact_sha256"]


def test_d3a_diff_check_is_clean():
    for command in (["git", "diff", "--check"], ["git", "diff", "--cached", "--check"]):
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
