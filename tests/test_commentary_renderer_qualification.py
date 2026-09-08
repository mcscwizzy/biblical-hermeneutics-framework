"""Focused contract tests for the isolated GPT-5.6 Sol exchange."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from tools import commentary_renderer_qualification as qualification


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / ".bhf-data/bhf-commentary-production/v1/runs/run-04109d5ff664ed80"


def _exported(tmp_path: Path) -> Path:
    root = tmp_path / "qualification"
    result = qualification.export_bundle(repo_root=REPO_ROOT, qualification_root=root)
    assert result["packet_count"] == 21
    return root


def _response_zip(root: Path, destination: Path, *, raw: bytes = b"{}", mutate=None, extra: bool = False, duplicate: bool = False) -> Path:
    manifest = qualification.response_manifest_template(qualification_root=root)
    if mutate:
        mutate(manifest)
    with zipfile.ZipFile(destination, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for row in manifest["responses"]:
            archive.writestr(f"responses/{row['response_filename']}", raw)
        if extra:
            archive.writestr("responses/022_unknown.json", raw)
        if duplicate:
            archive.writestr(f"responses/{manifest['responses'][0]['response_filename']}", raw)
    return destination


def _source_fingerprint() -> dict[str, str]:
    files = [SOURCE / "manifest.json", SOURCE / "handoff/manifest.json"]
    files.extend(sorted((SOURCE / "batches/batch-001/packets").glob("*.json")))
    files.append(REPO_ROOT / ".bhf-data/bhf-commentary-production/v1/ledger.json")
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def test_export_is_exact_21_packet_set_excludes_data_gap_and_leaks_no_baseline(tmp_path):
    root = _exported(tmp_path)
    manifest = json.loads((root / "qualification-manifest.json").read_text())
    assert [row["reference"] for row in manifest["chapters"]] == list(qualification.EXPECTED_REFERENCES)
    assert set(qualification.EXCLUDED_DATA_GAP_REFERENCES).isdisjoint(
        row["reference"] for row in manifest["chapters"]
    )
    with zipfile.ZipFile(root / "renderer-qualification-gpt-5.6-sol-input.zip") as archive:
        assert archive.namelist() == [
            "manifest.json", "GENERATION_INSTRUCTIONS.txt",
            *[f"packets/{row['packet_filename']}" for row in manifest["chapters"]],
        ]
        portable_manifest = json.loads(archive.read("manifest.json"))
        assert "codex-gpt-5" not in json.dumps(portable_manifest)
        assert "QUALITY_FAIL" not in json.dumps(portable_manifest)
        assert "baseline" not in json.dumps(portable_manifest).lower()


def test_export_preserves_every_original_packet_byte_and_sha256(tmp_path):
    root = _exported(tmp_path)
    manifest = json.loads((root / "qualification-manifest.json").read_text())
    with zipfile.ZipFile(root / "renderer-qualification-gpt-5.6-sol-input.zip") as archive:
        for row in manifest["chapters"]:
            original = (REPO_ROOT / row["source_packet_path"]).read_bytes()
            exported = archive.read(f"packets/{row['packet_filename']}")
            assert exported == original
            assert hashlib.sha256(exported).hexdigest() == row["packet_file_sha256"]


def test_response_manifest_identity_missing_extra_packet_mismatch_and_duplicate_are_rejected(tmp_path):
    root = _exported(tmp_path)
    valid = _response_zip(root, tmp_path / "valid.zip")
    missing = tmp_path / "missing.zip"
    with zipfile.ZipFile(valid) as source, zipfile.ZipFile(missing, "w") as target:
        for name in source.namelist()[:-1]:
            target.writestr(name, source.read(name))
    with pytest.raises(qualification.QualificationError, match="filenames mismatch"):
        qualification.import_bundle(missing, qualification_root=root)
    with pytest.raises(qualification.QualificationError, match="filenames mismatch"):
        qualification.import_bundle(_response_zip(root, tmp_path / "extra.zip", extra=True), qualification_root=root)
    with pytest.raises(qualification.QualificationError, match="packet identity mismatch"):
        qualification.import_bundle(
            _response_zip(root, tmp_path / "mismatch.zip", mutate=lambda manifest: manifest["responses"][0].__setitem__("packet_hash", "wrong")),
            qualification_root=root,
        )
    with pytest.raises(qualification.QualificationError, match="duplicate ZIP members"):
        qualification.import_bundle(_response_zip(root, tmp_path / "duplicate.zip", duplicate=True), qualification_root=root)


def test_imported_raw_is_immutable_and_evaluation_uses_isolated_frozen_path(tmp_path):
    root = _exported(tmp_path)
    qualification.import_bundle(_response_zip(root, tmp_path / "first.zip", raw=b"{}"), qualification_root=root)
    raw = root / "responses/raw/001_exodus_014.json"
    before = raw.read_bytes()
    with pytest.raises(qualification.ArtifactCollisionError, match="immutable artifact collision"):
        qualification.import_bundle(_response_zip(root, tmp_path / "second.zip", raw=b'{"changed":true}'), qualification_root=root)
    assert raw.read_bytes() == before
    report = qualification.evaluate(qualification_root=root)
    assert report["dense_reader_applied"] is False
    assert report["frozen_contracts"]["gate_version"] == "commentary-richness-gate-v2.1"
    assert len(report["chapters"]) == 21
    assert len(report["chapter_comparison"]) == 21
    assert all(row["structural_result"] == "REJECTED" for row in report["chapters"])


def test_export_import_and_evaluation_leave_production_ledger_and_canary_artifacts_untouched(tmp_path):
    before = _source_fingerprint()
    root = _exported(tmp_path)
    manifest = json.loads((root / "qualification-manifest.json").read_text())
    response = tmp_path / "production-raw-fixture.zip"
    template = qualification.response_manifest_template(qualification_root=root)
    with zipfile.ZipFile(response, "w") as archive:
        archive.writestr("manifest.json", json.dumps(template))
        for row in manifest["chapters"]:
            source = SOURCE / "batches/batch-001/raw/attempt-001" / f"{qualification.slug(row['book'], row['chapter'])}.json"
            archive.writestr(f"responses/{row['response_filename']}", source.read_bytes())
    qualification.import_bundle(response, qualification_root=root)
    qualification.evaluate(qualification_root=root)
    assert _source_fingerprint() == before
