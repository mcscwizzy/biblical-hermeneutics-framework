"""Exact approval and selective-promotion invariants for Transaction C3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.runtime_paths import default_commentary_storage_path


ROOT = Path(__file__).resolve().parents[1]
C2_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2"
RELEASE_ROOT = ROOT / ".bhf-data/bhf-commentary-v1.2"
APPROVAL_PATH = C2_ROOT / "approval-manifest.json"
SNAPSHOT_PATH = C2_ROOT / "published-tree-c3-before.json"
APPROVED = {
    "1 Samuel 17": "50070415702264ae95cbfdbf1a334322bebadd6798f1c6ef1610e8c1e9bafa2d",
    "2 Kings 5": "480c7585e9836ded362662004d2818ed8f81f05affb5e9568d367a572b08c3c6",
    "Acts 27": "ac625b17687b3c0158f04a5d7678394f07b2c3877ee243b6f0342a0e043ef8d8",
    "Genesis 13": "c389b19f4781f3000242d437c61c0d36ffefc48c596e20f00f7935bafe97c8d4",
    "Genesis 34": "811c11c0421822df129b5c693d8c54047dc2a0c510b818eb3731c50385c760cd",
    "Isaiah 36": "c6b3461fea00d331c7f839ff8310f3081f18298341dad0762a4f9a04acfbfc41",
    "John 4": "bac11949ded437702a0e19933a2cb692718c03cadd16b61b68c5ca8581fbed10",
    "Joshua 6": "89ada8ecbf6b942405d93d55cd460653cb1934ea972fb91fd9d67d9bf779b41f",
    "Judges 20": "e10386a31b8fc9311fd992953f0958353ebee261530b97f960e7c32a00b31129",
    "Matthew 2": "a4f3f0f115de23a5f94ce99e91a91e7941ff7ffcef588f80c37120d19d745ebf",
    "Numbers 18": "502c079673d07725a126502a869ccdf28a8fefd054110f5495deb2e29753206a",
    "Ruth 1": "8e3ceec1c3095b48b33fbb27f4948bf569d8e3dfc788423941e7638474114b47",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_approval_manifest_binds_exact_active_candidate_identities():
    manifest = _json(C2_ROOT / "candidate-manifest.json")
    approval = _json(APPROVAL_PATH)
    active = {row["reference"]: row for row in manifest["candidates"]}

    assert approval["candidate_manifest_sha256"] == _sha256(C2_ROOT / "candidate-manifest.json")
    assert approval["approval_state"] == "EXPLICIT_HUMAN_APPROVAL"
    assert approval["approved_artifact_hashes"] == APPROVED
    assert len(approval["approvals"]) == 12
    assert {row["reference"] for row in approval["approvals"]} == set(APPROVED)
    for row in approval["approvals"]:
        candidate = active[row["reference"]]
        assert row["candidate_artifact_sha256"] == APPROVED[row["reference"]]
        assert row["candidate_artifact_sha256"] == candidate["candidate_artifact_sha256"]
        assert row["candidate_artifact_path"] == candidate["candidate_artifact_path"]
        assert row["evidence_hash"] == candidate["new_evidence_hash"]
        assert row["synthesis_hash"] == candidate["new_synthesis_hash"]
        assert row["validation_state"] == "validated"
        assert candidate["review_state"] == "READY_FOR_HUMAN_REVIEW"
        assert candidate["validation_errors"] == []
        assert _sha256(ROOT / row["candidate_artifact_path"]) == row["candidate_artifact_sha256"]
    c2s = {"1 Samuel 17", "Joshua 6", "Numbers 18", "Ruth 1"}
    for reference in c2s:
        candidate = active[reference]
        approval_row = next(row for row in approval["approvals"] if row["reference"] == reference)
        assert candidate["stabilization"]["stage"] == "C2S"
        assert approval_row["candidate_artifact_path"] == candidate["candidate_artifact_path"]
        assert approval_row["candidate_artifact_sha256"] == candidate["candidate_artifact_sha256"]
        assert all(
            attempt["candidate_artifact_sha256"] != approval_row["candidate_artifact_sha256"]
            for attempt in candidate.get("superseded_attempts", [])
        )


def test_release_delta_is_limited_to_approved_chapters_and_existing_indexes():
    before = _json(SNAPSHOT_PATH)
    current = _tree(RELEASE_ROOT)
    prior = before["files"]
    changed = {path for path in set(prior) | set(current) if prior.get(path) != current.get(path)}
    chapter_paths = {
        row["published_artifact_path"].removeprefix(".bhf-data/bhf-commentary-v1.2/")
        for row in _json(C2_ROOT / "candidate-manifest.json")["candidates"]
    }
    assert changed == chapter_paths | {
        ".bhf-commentary-release.json",
        ".bhf-commentary-release-checksums.json",
    }

    approval = _json(APPROVAL_PATH)
    rows = {row["reference"]: row for row in _json(RELEASE_ROOT / ".bhf-commentary-release.json")["chapter_publication_index"]}
    for item in approval["approvals"]:
        row = rows[item["reference"]]
        artifact = RELEASE_ROOT / row["filename"]
        assert _sha256(artifact) == item["candidate_artifact_sha256"]
        assert row["artifact_sha256"] == item["candidate_artifact_sha256"]
        assert row["source_lineage"] == {
            "evidence_hash": item["evidence_hash"],
            "synthesis_hash": item["synthesis_hash"],
        }


def test_controls_and_production_reader_remain_on_published_release():
    before = _json(SNAPSHOT_PATH)
    current = _tree(RELEASE_ROOT)
    current_index = {
        row["reference"]: row
        for row in _json(RELEASE_ROOT / ".bhf-commentary-release.json")["chapter_publication_index"]
    }
    for reference in ("Psalms 76", "Revelation 18", "Acts 16"):
        assert reference not in APPROVED
        old = before["chapter_identities"][reference]
        row = current_index[reference]
        assert row["source_lineage"] == old["source_lineage"]
        assert row.get("artifact_sha256") == old["artifact_sha256"]
        if old["filename"] is not None:
            assert current[old["filename"]] == before["files"][old["filename"]]

    storage = default_commentary_storage_path({"BHF_COMMENTARY_RELEASE": "commentary-v1.2"})
    assert storage == Path(".bhf-data/bhf-commentary-v1.2")
    assert "commentary-candidates" not in storage.parts
    for reference in APPROVED:
        book, chapter_text = reference.rsplit(" ", 1)
        assert load_commentary(storage, book, int(chapter_text)) is not None


def test_all_promoted_artifacts_pass_commentary_v12_validation_against_locked_inputs():
    from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
    from framework.commentary.production.inputs import prepare_chapter

    approval = _json(APPROVAL_PATH)
    for row in approval["approvals"]:
        artifact = RELEASE_ROOT / f"{row['book'].lower().replace(' ', '_')}_{row['chapter']:03d}.json"
        payload = _json(artifact)
        prepared = prepare_chapter(row["book"], row["chapter"])
        validation_payload = {
            key: value
            for key, value in payload.items()
            if key not in {"failure_reason", "validation_errors", "validation_warnings"}
        }
        result = validate_chapter_commentary(
            validation_payload,
            prepared.bundle,
            expected_evidence_hash=row["evidence_hash"],
            expected_prompt_version="1.8",
            expected_reference=row["reference"],
            expected_book=row["book"],
            expected_chapter=row["chapter"],
            synthesis=prepared.synthesis,
            expected_synthesis_hash=row["synthesis_hash"],
        )
        assert result.valid, (row["reference"], result.errors)
