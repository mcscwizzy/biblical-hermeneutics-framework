"""Integrity checks for the Genesis Commentary D2 candidate transaction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D1 = ROOT / ".bhf-data/bhf-commentary-candidates/genesis-commentary-refresh-d1"
D2 = ROOT / ".bhf-data/bhf-commentary-candidates/genesis-commentary-refresh-d2"
RELEASE = ROOT / ".bhf-data/bhf-commentary-v1.2"
REFERENCES = [f"Genesis {chapter}" for chapter in range(2, 51)]


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_candidate_manifest_is_exactly_genesis_2_through_50():
    manifest = _json(D2 / "candidate-manifest.json")
    assert manifest["expected_candidate_count"] == 49
    assert manifest["expected_references"] == REFERENCES
    assert set(manifest["candidates"]) == set(REFERENCES)
    assert sorted(path.name for path in (D2 / "candidates").glob("*.json")) == [
        f"genesis_{chapter:03d}.json" for chapter in range(2, 51)
    ]
    assert not (D2 / "approval-manifest.json").exists()


def test_each_ready_candidate_matches_its_locked_d1_lineage_and_validation():
    candidate_manifest = _json(D2 / "candidate-manifest.json")["candidates"]
    d1_manifest = _json(D1 / "renderer-input-manifest.json")
    d1_packets = {row["reference"]: row for row in d1_manifest["packets"]}

    for chapter, reference in enumerate(REFERENCES, start=2):
        record = candidate_manifest[reference]
        candidate_path = D2 / "candidates" / f"genesis_{chapter:03d}.json"
        validation_path = D2 / "validation" / f"genesis_{chapter:03d}.json"
        candidate = _json(candidate_path)
        validation = _json(validation_path)
        packet = d1_packets[reference]

        assert record["technical_review_state"] == "READY_FOR_HUMAN_REVIEW"
        assert record["d3_eligibility"] is True
        assert record["candidate_artifact_sha256"] == _sha(candidate_path)
        assert record["d1_renderer_packet_sha256"] == packet["renderer_packet_sha256"]
        assert record["evidence_hash"] == packet["evidence_hash"]
        assert record["synthesis_hash"] == packet["synthesis_hash"]
        assert candidate["reference"] == reference
        assert candidate["book"] == "Genesis"
        assert candidate["chapter"] == chapter
        assert candidate["generated_metadata"]["model"] == "gpt-5.6-terra"
        assert candidate["generated_metadata"]["commentary_prompt_version"] == "1.8"
        assert candidate["generated_metadata"]["commentary_schema_version"] == "1.2"
        assert candidate["generated_metadata"]["evidence_hash"] == packet["evidence_hash"]
        assert candidate["generated_metadata"]["synthesis_hash"] == packet["synthesis_hash"]
        assert validation["candidate_status"] == "READY_FOR_HUMAN_REVIEW"
        assert validation["validation_errors"] == []
        assert validation["audits"]["ancestry"]["valid"] is True
        assert validation["audits"]["provenance_binding"]["valid"] is True
        assert validation["audits"]["envelope"]["valid"] is True
        assert validation["audits"]["gate"]["outcome"] in {"PASS", "PASS_WITH_WARNING"}


def test_published_v12_tree_and_d1_root_remain_unchanged():
    before = _json(D1 / "published-release-tree-before.json")
    after = _json(D2 / "published-release-tree-after-render.json")
    actual = {
        path.relative_to(RELEASE).as_posix(): _sha(path)
        for path in sorted(RELEASE.rglob("*"))
        if path.is_file()
    }
    assert after["byte_identical_to_d1_snapshot"] is True
    assert after["release_tree_files_sha256"] == before["release_tree_files_sha256"]
    assert actual == before["release_tree_files_sha256"]
    assert _json(D2 / "d1-immutability-verification.json")["byte_identical_to_d1_master_state"] is True


def test_genesis1_and_non_genesis_controls_are_excluded_from_candidates():
    genesis1 = _json(D2 / "genesis-1-control.json")
    non_genesis = _json(D2 / "non-genesis-controls.json")
    assert genesis1["published_artifact_unchanged"] is True
    assert genesis1["source_lineage_unchanged"] is True
    assert genesis1["no_genesis_1_candidate"] is True
    assert non_genesis["no_non_genesis_candidates"] is True
    assert set(non_genesis["controls"]) == {
        "Exodus 14",
        "Psalms 76",
        "Isaiah 36",
        "Acts 16",
        "Revelation 18",
    }
    assert all(row["index_identity_matches"] for row in non_genesis["controls"].values())
