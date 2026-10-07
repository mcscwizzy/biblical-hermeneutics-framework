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
    assert all(row["review_state"] == "READY_FOR_HUMAN_REVIEW" for row in rows)

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
    ruth = next(row for row in rows if row["reference"] == "Ruth 1")
    assert ruth["review_state"] == "READY_FOR_HUMAN_REVIEW"
    superseded = ruth["superseded_attempts"]
    assert len(superseded) == 2
    prior = next(row for row in superseded if row["review_state"] == "INVALID_ARTIFACT")
    archived = ROOT / prior["archived_candidate_artifact_path"]
    assert archived.is_file() and _sha256(archived) == prior["candidate_artifact_sha256"]
    assert prior["review_state"] == "INVALID_ARTIFACT"
    assert prior["candidate_artifact_sha256"] == "0529d5ddf77b5cfa5fbe1afa2513785cb1e02062384eb00af39c90bf2fae6e76"
    assert not (ROOT / prior["original_candidate_artifact_path"]).exists()
    raw_path = ROOT / prior["raw_response_path"]
    raw = json.loads(raw_path.read_bytes())
    assert all(
        "confidence" not in block and "interpretation_level" not in block
        for section in raw["sections"] for block in section["blocks"]
    )
    assert "Superseded invalid attempt" in (ROOT / ruth["review_document_path"]).read_text(encoding="utf-8")

    index = (C2_ROOT / "review-package/index.md").read_text(encoding="utf-8")
    assert "{len(manifest_rows)}" not in index
    assert "{counts.get(" not in index
    assert "**Candidates:** 12 exact C1 chapters" in index
    assert "**Validated for human review:** 12" in index
    assert "**Invalid artifacts:** 0" in index


def test_c2_published_v12_release_tree_matches_pre_render_snapshot():
    snapshot = _json(C2_ROOT / "published-tree-before.json")
    current = {
        path.relative_to(RELEASE_ROOT).as_posix(): _sha256(path)
        for path in sorted(RELEASE_ROOT.rglob("*"))
        if path.is_file()
    }

    assert current == snapshot["files"]
    assert len(current) == snapshot["file_count"]

    repair_snapshot = _json(C2_ROOT / "ruth-repair-001/pre-repair-state.json")["published_release_tree"]
    assert current == repair_snapshot["files"]
    assert len(current) == repair_snapshot["file_count"]


def test_c2s_stabilization_preserves_c1_inputs_and_eight_untouched_candidate_artifacts():
    impact = _json(IMPACT_PATH)
    c1 = {row["reference"]: row for row in impact["chapters"]}
    manifest = _json(C2_ROOT / "candidate-manifest.json")
    ruth = next(row for row in manifest["candidates"] if row["reference"] == "Ruth 1")
    before = _json(C2_ROOT / "ruth-repair-001/pre-repair-state.json")
    ruth_input = before["ruth_input"]

    assert ruth_input["checks"] and all(ruth_input["checks"].values())
    assert ruth_input["evidence_hash"] == c1["Ruth 1"]["new_identity"]["evidence_hash"]
    assert ruth_input["synthesis_hash"] == c1["Ruth 1"]["new_identity"]["synthesis_hash"]
    assert ruth_input["evidence_ids"] == sorted(c1["Ruth 1"]["new_identity"]["evidence_ids"])
    assert ruth_input["synthesis_unit_count"] == c1["Ruth 1"]["new_identity"]["synthesis_unit_count"]
    assert ruth["new_evidence_hash"] == c1["Ruth 1"]["new_identity"]["evidence_hash"]
    assert ruth["new_synthesis_hash"] == c1["Ruth 1"]["new_identity"]["synthesis_hash"]
    assert ruth["renderer_input_evidence_hash"] == ruth_input["evidence_hash"]
    assert ruth["renderer_input_synthesis_hash"] == ruth_input["synthesis_hash"]

    stabilized = {"1 Samuel 17", "Joshua 6", "Numbers 18", "Ruth 1"}
    rows_before = {
        row["reference"]: row["sha256"]
        for row in before["untouched_candidate_artifacts"]
        if row["reference"] not in stabilized
    }
    rows_after = {
        row["reference"]: row["candidate_artifact_sha256"]
        for row in manifest["candidates"]
        if row["reference"] not in stabilized
    }
    assert rows_before == rows_after

    for reference in stabilized:
        row = next(row for row in manifest["candidates"] if row["reference"] == reference)
        assert row["review_state"] == "READY_FOR_HUMAN_REVIEW"
        assert row["stabilization"]["stage"] == "C2S"
        assert row["stabilization"]["evidence_hash"] == c1[reference]["new_identity"]["evidence_hash"]
        assert row["stabilization"]["synthesis_hash"] == c1[reference]["new_identity"]["synthesis_hash"]
        history = next(
            attempt for attempt in row["superseded_attempts"]
            if attempt["attempt"] == "C2S semantic stabilization"
        )
        archived = ROOT / history["archived_candidate_artifact_path"]
        assert archived.is_file() and _sha256(archived) == history["candidate_artifact_sha256"]
    assert _json(C2_ROOT / "ruth-repair-001/render-result.json")["status"] == "validated"
    confidence_audit = _json(C2_ROOT / "ruth-repair-001/confidence-validation.json")
    assert confidence_audit["status"] == "PASS"
    assert confidence_audit["evidence_hash"] == ruth_input["evidence_hash"]
    assert confidence_audit["synthesis_hash"] == ruth_input["synthesis_hash"]
    assert confidence_audit["block_count"] == 5
    assert all(block["passed"] for block in confidence_audit["blocks"])


def test_c2_controls_remain_unchanged_and_have_no_candidate_artifacts():
    impact = _json(IMPACT_PATH)
    manifest = _json(C2_ROOT / "candidate-manifest.json")
    controls = {row["reference"]: row["new_identity"] for row in impact["chapters"] if row["role"] == "control"}
    verified = _json(C2_ROOT / "ruth-repair-001/control-verification.json")
    assert verified["identities"] == controls
    assert not (set(controls) & {row["reference"] for row in manifest["candidates"]})


def test_production_reader_resolves_published_v12_when_v12_is_selected():
    resolved = default_commentary_storage_path({"BHF_COMMENTARY_RELEASE": "commentary-v1.2"})

    assert resolved == Path(".bhf-data/bhf-commentary-v1.2")
    assert "commentary-candidates" not in resolved.parts
