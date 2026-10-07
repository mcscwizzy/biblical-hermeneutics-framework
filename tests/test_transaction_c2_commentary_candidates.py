"""C2 candidate identity, review-scope, and release-isolation checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bhf_agent.runtime_paths import default_commentary_storage_path


ROOT = Path(__file__).resolve().parents[1]
C2_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2"
IMPACT_PATH = ROOT / ".bhf-data/bhf-commentary-candidates/transaction-c-commentary-impact/impact-manifest.json"
RELEASE_ROOT = ROOT / ".bhf-data/bhf-commentary-v1.2"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_c2_candidate_artifacts_are_one_to_one_with_c1_and_match_locked_inputs():
    impact = _json(IMPACT_PATH)
    manifest = _json(C2_ROOT / "candidate-manifest.json")
    expected = set(impact["candidate_chapter_set"])
    rows = manifest["candidates"]

    assert manifest["candidate_chapter_count"] == 12
    assert len(rows) == 12
    assert {row["reference"] for row in rows} == expected
    assert len({row["candidate_artifact_path"] for row in rows}) == 12
    commentary_files = {
        path.relative_to(ROOT).as_posix()
        for path in C2_ROOT.rglob("commentary.json")
    }
    assert commentary_files == {row["candidate_artifact_path"] for row in rows}
    assert not (set(impact["control_chapter_set"]) & {row["reference"] for row in rows})
    assert manifest["approval_state"] == "NONE_APPROVED"
    assert all(row["approval_state"] == "NOT_APPROVED" for row in rows)

    c1 = {row["reference"]: row for row in impact["chapters"]}
    for row in rows:
        artifact = ROOT / row["candidate_artifact_path"]
        review = ROOT / row["review_document_path"]
        commentary = _json(artifact)
        metadata = commentary["generated_metadata"]
        expected_identity = c1[row["reference"]]["new_identity"]

        assert artifact.is_relative_to(C2_ROOT)
        assert artifact.is_file() and _sha256(artifact) == row["candidate_artifact_sha256"]
        assert review.is_file()
        review_text = review.read_text(encoding="utf-8")
        assert row["renderer_input_evidence_hash"] == expected_identity["evidence_hash"]
        assert row["renderer_input_synthesis_hash"] == expected_identity["synthesis_hash"]
        assert metadata["evidence_hash"] == expected_identity["evidence_hash"]
        assert metadata["synthesis_hash"] == expected_identity["synthesis_hash"]
        assert row["review_state"] in {
            "READY_FOR_HUMAN_REVIEW", "GENERATION_FAILED", "INPUT_IDENTITY_MISMATCH",
            "INVALID_ARTIFACT", "BLOCKED",
        }
        if row["review_state"] == "INVALID_ARTIFACT":
            assert "Raw candidate Commentary (unvalidated)" in review_text
            assert "No accepted commentary sections" in review_text

    index = (C2_ROOT / "review-package/index.md").read_text(encoding="utf-8")
    assert "{len(manifest_rows)}" not in index
    assert "{counts.get(" not in index
    assert "**Candidates:** 12 exact C1 chapters" in index
    assert "**Validated for human review:** 11" in index
    assert "**Invalid artifacts:** 1" in index


def test_c2_published_v12_release_tree_matches_pre_render_snapshot():
    snapshot = _json(C2_ROOT / "published-tree-before.json")
    current = {
        path.relative_to(RELEASE_ROOT).as_posix(): _sha256(path)
        for path in sorted(RELEASE_ROOT.rglob("*"))
        if path.is_file()
    }

    assert current == snapshot["files"]
    assert len(current) == snapshot["file_count"]


def test_production_reader_resolves_published_v12_when_v12_is_selected():
    resolved = default_commentary_storage_path({"BHF_COMMENTARY_RELEASE": "commentary-v1.2"})

    assert resolved == Path(".bhf-data/bhf-commentary-v1.2")
    assert "commentary-candidates" not in resolved.parts
