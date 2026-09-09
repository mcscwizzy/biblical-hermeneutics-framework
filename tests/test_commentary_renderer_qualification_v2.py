"""Contract tests for the isolated prompt 1.6 renderer qualification."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from bhf_agent.chapter_commentary.prompts import system_prompt_for_version
from tools import commentary_renderer_qualification_v2 as qualification


REPO_ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_ROOT = (
    REPO_ROOT / ".bhf-data/bhf-commentary-candidates/renderer-qualification-v1/gpt-5.6-sol"
)


def _prepared(tmp_path: Path) -> Path:
    root = tmp_path / "qualification-v2"
    result = qualification.prepare(repo_root=REPO_ROOT, qualification_root=root)
    assert result["chapter_count"] == 21
    assert result["packet_count"] == 21
    return root


def _response_zip(
    root: Path,
    destination: Path,
    *,
    raw: bytes = b"{}",
    mutate=None,
) -> Path:
    manifest = qualification.response_manifest_template(
        repo_root=REPO_ROOT, qualification_root=root
    )
    if mutate:
        mutate(manifest)
    with zipfile.ZipFile(destination, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for row in manifest["responses"]:
            archive.writestr(f"responses/{row['response_filename']}", raw)
    return destination


def test_prepare_freezes_same_21_chapter_corpus_and_prompt_16_contract(tmp_path):
    root = _prepared(tmp_path)
    manifest = json.loads((root / "qualification-manifest.json").read_text())
    historical = json.loads((HISTORICAL_ROOT / "qualification-manifest.json").read_text())

    assert manifest["qualification_id"].startswith(
        "renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-"
    )
    assert manifest["renderer"] == "gpt-5.6-sol"
    assert manifest["renderer_effort"] == "medium"
    assert manifest["contract_versions"] == qualification.FROZEN_CONTRACTS
    assert [row["reference"] for row in manifest["chapters"]] == list(
        qualification.EXPECTED_REFERENCES
    )
    assert [row["reference"] for row in manifest["chapters"]] == [
        row["reference"] for row in historical["chapters"]
    ]
    assert all(
        candidate["source_packet_id"] == original["packet_id"]
        and candidate["source_packet_hash"] == original["packet_hash"]
        and candidate["source_packet_file_sha256"] == original["packet_file_sha256"]
        for candidate, original in zip(
            manifest["chapters"], historical["chapters"], strict=True
        )
    )

    for row in manifest["chapters"]:
        packet = json.loads((root / "packets" / row["packet_filename"]).read_text())
        assert packet["commentary_prompt_version"] == "1.6"
        assert packet["renderer"] == "gpt-5.6-sol"
        assert packet["renderer_effort"] == "medium"
        assert packet["packet_id"] == row["packet_id"]
        assert packet["packet_hash"] == row["packet_hash"]
        assert packet["system_prompt"] == system_prompt_for_version("1.6")
        assert packet["user_prompt"]

    exported = (root / "renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-input.zip")
    with zipfile.ZipFile(exported) as archive:
        assert archive.namelist() == [
            "manifest.json",
            "GENERATION_INSTRUCTIONS.txt",
            *[f"packets/{row['packet_filename']}" for row in manifest["chapters"]],
        ]
        portable = archive.read("manifest.json").decode("utf-8")
        assert "QUALITY_FAIL" not in portable
        assert "codex-gpt-5" not in portable
        assert "renderer_prompt_version\": \"1.6\"" in portable

    metadata = json.loads((root / "qualification-metadata.json").read_text())
    assert metadata["status"] == "AWAITING_EXTERNAL_RESPONSE_BUNDLE"
    assert (root / "checksums-prepared.json").is_file()


def test_response_import_requires_verified_sol_identity_and_is_immutable(tmp_path):
    root = _prepared(tmp_path)
    valid = _response_zip(root, tmp_path / "valid.zip")
    imported = qualification.import_bundle(valid, repo_root=REPO_ROOT, qualification_root=root)
    assert imported["response_count"] == 21
    assert imported["prompt_version"] == "1.6"

    changed = _response_zip(root, tmp_path / "changed.zip", raw=b'{"changed":true}')
    with pytest.raises(qualification.ArtifactCollisionError, match="immutable artifact collision"):
        qualification.import_bundle(
            changed, repo_root=REPO_ROOT, qualification_root=root
        )
    assert (root / "responses/raw/001_exodus_014.json").read_bytes() == b"{}"

    wrong_renderer = _prepared(tmp_path / "wrong-renderer")
    with pytest.raises(qualification.QualificationError, match="renderer mismatch"):
        qualification.import_bundle(
            _response_zip(
                wrong_renderer,
                tmp_path / "wrong-renderer.zip",
                mutate=lambda manifest: manifest.__setitem__("renderer", "claude"),
            ),
            repo_root=REPO_ROOT,
            qualification_root=wrong_renderer,
        )


def test_corrupt_response_stops_at_import_boundary(tmp_path):
    root = _prepared(tmp_path)
    with pytest.raises(qualification.QualificationError, match="corrupt JSON"):
        qualification.import_bundle(
            _response_zip(root, tmp_path / "corrupt.zip", raw=b"not-json"),
            repo_root=REPO_ROOT,
            qualification_root=root,
        )
    assert not (root / "responses/import-receipt.json").exists()


def test_evaluation_records_parsed_outputs_and_frozen_v3_metrics(tmp_path):
    root = _prepared(tmp_path)
    qualification.import_bundle(
        _response_zip(root, tmp_path / "empty-objects.zip"),
        repo_root=REPO_ROOT,
        qualification_root=root,
    )
    report = qualification.evaluate(repo_root=REPO_ROOT, qualification_root=root)

    assert report["qualification_result"] == "RENDERER_QUALIFICATION_NOT_QUALIFIED"
    assert report["renderer"] == "gpt-5.6-sol"
    assert report["renderer_effort"] == "medium"
    assert report["frozen_contracts"] == qualification.FROZEN_CONTRACTS
    assert len(report["chapters"]) == 21
    assert len(report["chapter_comparison"]) == 21
    assert all(row["structural_result"] == "REJECTED" for row in report["chapters"])
    manifest = json.loads((root / "qualification-manifest.json").read_text())
    expected_names = {Path(row["response_filename"]).name for row in manifest["chapters"]}
    assert {path.name for path in (root / "parsed").glob("*.json")} == expected_names
    assert {path.name for path in (root / "evaluation/chapters").glob("*.json")} == expected_names
    assert report["aggregate"]["structural_rejections"] == 21
    assert report["aggregate"]["high_dump"] == 0
    assert (root / "checksums-evaluation.json").is_file()
