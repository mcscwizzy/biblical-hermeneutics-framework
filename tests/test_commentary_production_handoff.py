from __future__ import annotations

import json
from pathlib import Path

import pytest

from framework.commentary.production.handoff import HandoffRunner
from framework.commentary.production.manifests import build_manifest, load_manifest, save_manifest
from framework.commentary.production.models import (
    COMPLETE,
    InputIdentity,
    ManifestError,
    PreparedChapter,
    RAW_CAPTURED,
    ArtifactCollisionError,
)
from framework.commentary.production.census import canonical_chapters
from framework.commentary.production.runtime import (
    EXTERNAL_HANDOFF_MODE,
    handoff_generation_receipt,
)


def _prepared(reference: str = "Genesis 1") -> PreparedChapter:
    book, chapter_text = reference.rsplit(" ", 1)
    chapter = int(chapter_text)
    identity = InputIdentity(
        "evidence", "synthesis", "1.5", "1.2", "1.1", "1.1",
        "commentary-richness-gate-v2.1", "validator", "packet-hash", "packet-id",
    )
    return PreparedChapter(
        row={
            "reference": reference,
            "book": book,
            "chapter": chapter,
            "canonical_ordinal": 1,
            "literary_category": "Pentateuch",
            "evidence_availability": "AVAILABLE",
            "evidence_count": 1,
            "synthesis_unit_count": 1,
            "density_bucket": "1-5",
            "input_identity": identity.to_dict(),
        },
        packet={
            "packet_id": "packet-id",
            "packet_hash": "packet-hash",
            "system_prompt": "frozen system prompt",
            "user_prompt": "frozen user prompt",
        },
    )


def _manifest(tmp_path: Path) -> Path:
    path = tmp_path / "planned.json"
    save_manifest(build_manifest([_prepared()], batch_size=1, run_id="run-handoff"), path)
    return path


class ImportHarness(HandoffRunner):
    def __init__(self, root: Path, *, terminal: bool = False):
        super().__init__(root, renderer_identity="terra-medium", input_loader=lambda book, chapter: _prepared())
        self.terminal = terminal

    def _import_and_evaluate(self, manifest, batch, chapter, prepared, record, state, enable_reader):
        if self.terminal:
            self._set_record(state, chapter["reference"], "VALIDATING")
            self._set_record(state, chapter["reference"], "ACCEPTED")
            self._set_record(state, chapter["reference"], "GATE_PASS")
            self._set_record(state, chapter["reference"], COMPLETE)
            self._save_state(state)
            return {"reference": chapter["reference"], "state": COMPLETE}
        return {"reference": chapter["reference"], "state": RAW_CAPTURED}


def _authorize(tmp_path: Path, *, terminal: bool = False) -> tuple[ImportHarness, str]:
    runner = ImportHarness(tmp_path, terminal=terminal)
    result = runner.prepare(_manifest(tmp_path), authorized_run=True)
    assert result["provider_calls"] == 0
    return runner, result["run_id"]


def test_handoff_requires_explicit_authorization(tmp_path):
    runner = ImportHarness(tmp_path)
    with pytest.raises(ManifestError, match="--authorized-run"):
        runner.prepare(_manifest(tmp_path), authorized_run=False)
    assert not (tmp_path / ".bhf-data/bhf-commentary-production/v1/runs/run-handoff/authorization.json").exists()


def test_handoff_prepare_exports_locked_packet_and_25_style_task_metadata(tmp_path):
    runner = ImportHarness(tmp_path)
    result = runner.prepare(_manifest(tmp_path), authorized_run=True)
    assert result["generation_mode"] == EXTERNAL_HANDOFF_MODE
    assert result["renderer_identity"] == "terra-medium"
    assert result["manifest_identity"] == json.loads((_manifest(tmp_path)).read_text())["manifest_identity"]
    assert result["task_count"] == 1
    task = result["tasks"][0]
    assert task["packet_id"] == "packet-id"
    assert task["packet_hash"] == "packet-hash"
    assert task["expected_raw_path"].endswith("raw/attempt-001/genesis_001.json")
    assert task["attempt"] == 1
    assert task["prompt_identity"]["prompt_version"] == "1.5"
    assert result["provider_calls"] == 0
    auth = json.loads((tmp_path / ".bhf-data/bhf-commentary-production/v1/runs/run-handoff/authorization.json").read_text())
    assert auth["generation_mode"] == EXTERNAL_HANDOFF_MODE
    assert "runtime_config_identity" not in auth


def test_exact_canary_fixture_handoff_dry_run_has_25_tasks_and_zero_provider_calls(tmp_path):
    manifest = load_manifest(Path(".bhf-data/bhf-commentary-production/v1/planned/canary-001-manifest.json"))
    by_key = {(row["book"], int(row["chapter"])): row for row in manifest["chapters"]}

    def fixture_loader(book, chapter):
        locked = by_key[(book, int(chapter))]
        identity = InputIdentity(**locked["input_identity"])
        return PreparedChapter(
            row={**locked, "input_identity": identity.to_dict()},
            packet={
                "packet_id": locked["packet_id"],
                "packet_hash": locked["packet_hash"],
                "system_prompt": "fixture system prompt",
                "user_prompt": "fixture user prompt",
            },
        )

    result = HandoffRunner(tmp_path, renderer_identity="terra-medium", input_loader=fixture_loader).prepare(
        Path(".bhf-data/bhf-commentary-production/v1/planned/canary-001-manifest.json"),
        authorized_run=True,
    )
    assert result["manifest_identity"] == "caaffaf7618e14246b3bfdcf9bb0674e54189b4ec30a604e608d0dc7c5334567"
    assert result["task_count"] == 25
    assert result["renderer_identity"] == "terra-medium"
    assert result["provider_calls"] == 0
    assert all(
        task["packet_id"]
        == by_key[(task["reference"].rsplit(" ", 1)[0], int(task["reference"].rsplit(" ", 1)[1]))]["packet_id"]
        for task in result["tasks"]
    )
    assert all(
        task["expected_raw_path"].startswith(
            "runs/run-04109d5ff664ed80/batches/"
        )
        and "/raw/attempt-001/" in task["expected_raw_path"]
        for task in result["tasks"]
    )
    assert not list((tmp_path / ".bhf-data/bhf-commentary-production/v1/runs/run-04109d5ff664ed80").glob("**/raw/**/*.json"))


def test_handoff_identity_is_deterministic_and_renderer_is_required():
    first = handoff_generation_receipt("terra-medium", reader_enabled=True)
    second = handoff_generation_receipt("terra-medium", reader_enabled=True)
    changed = handoff_generation_receipt("terra-high", reader_enabled=True)
    assert first["generation_identity"] == second["generation_identity"]
    assert first["generation_identity"] != changed["generation_identity"]
    with pytest.raises(Exception, match="EXTERNAL_RENDERER_IDENTITY_REQUIRED"):
        handoff_generation_receipt("", reader_enabled=False)


def test_handoff_import_is_immutable_and_duplicate_identical_import_is_idempotent(tmp_path):
    runner, run_id = _authorize(tmp_path)
    response = tmp_path / "response.json"
    response.write_text('{"reference":"Genesis 1","book":"Genesis","chapter":1}', encoding="utf-8")
    first = runner.import_response(run_id, "Genesis 1", response)
    second = runner.import_response(run_id, "Genesis 1", response)
    assert first["provider_calls"] == second["provider_calls"] == 0
    assert second["status"] == "IMPORTED"
    assert (tmp_path / ".bhf-data/bhf-commentary-production/v1/runs/run-handoff/batches/batch-001/raw/attempt-001/genesis_001.json").read_text() == response.read_text()


def test_handoff_conflicting_raw_bytes_are_rejected(tmp_path):
    runner, run_id = _authorize(tmp_path)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text("{\"different\":true}", encoding="utf-8")
    runner.import_response(run_id, "Genesis 1", first)
    with pytest.raises(ArtifactCollisionError, match="HANDOFF_RAW_COLLISION"):
        runner.import_response(run_id, "Genesis 1", second)


def test_malformed_handoff_response_is_quarantined_without_repair(tmp_path):
    runner = HandoffRunner(tmp_path, renderer_identity="terra-medium", input_loader=lambda book, chapter: _prepared())
    run_id = runner.prepare(_manifest(tmp_path), authorized_run=True)["run_id"]
    response = tmp_path / "malformed.json"
    response.write_text("[]", encoding="utf-8")
    result = runner.import_response(run_id, "Genesis 1", response)
    assert result["state"] == "QUARANTINED"
    quarantine = tmp_path / ".bhf-data/bhf-commentary-production/v1/runs/run-handoff/batches/batch-001/quarantine/attempt-001/genesis_001.json"
    assert quarantine.is_file()
    assert json.loads(quarantine.read_text())["rejection_codes"] == ["CONTENT_MALFORMED_JSON"]


def test_pending_handoff_is_reported_as_next_render_work(tmp_path):
    runner, run_id = _authorize(tmp_path)
    result = runner.next_work(run_id)
    assert result["status"] == "NEXT_HANDOFF_WORK"
    assert result["next"]["work"] == "RENDER_PACKET"
    assert result["next"]["attempt"] == 1


def test_more_than_50_handoff_chapters_requires_full_corpus_authorization(tmp_path):
    prepared = [_prepared(row["reference"]) for row in canonical_chapters()[:51]]
    path = tmp_path / "large-planned.json"
    save_manifest(build_manifest(prepared, batch_size=25), path)
    runner = HandoffRunner(tmp_path, renderer_identity="terra-medium", input_loader=lambda book, chapter: _prepared(f"{book} {chapter}"))
    with pytest.raises(ManifestError, match="full-corpus"):
        runner.prepare(path, authorized_run=True)


def test_completed_handoff_chapter_is_skipped_and_pending_is_next_work(tmp_path):
    runner, run_id = _authorize(tmp_path, terminal=True)
    response = tmp_path / "response.json"
    response.write_text("{}", encoding="utf-8")
    result = runner.import_response(run_id, "Genesis 1", response)
    assert result["status"] == "IMPORTED"
    assert runner.next_work(run_id)["status"] == "HANDOFF_COMPLETE"


def test_handoff_run_rejects_renderer_mismatch(tmp_path):
    runner, run_id = _authorize(tmp_path)
    with pytest.raises(Exception, match="RENDERER_IDENTITY_MISMATCH"):
        HandoffRunner(tmp_path, renderer_identity="terra-high", input_loader=lambda book, chapter: _prepared()).next_work(run_id)
