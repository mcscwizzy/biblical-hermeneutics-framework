"""Host-local Codex transport contracts; every subprocess is mocked."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from framework.commentary.production.models import sha256_bytes
from framework.commentary.v12_corpus import (
    CODEX_TERRA_EFFORT,
    CODEX_TERRA_MODEL,
    V12CorpusError,
    V12CorpusRunner,
    V12IntegrityError,
)


def _runner(tmp_path: Path) -> V12CorpusRunner:
    candidate = tmp_path / "candidate"
    candidate.mkdir(exist_ok=True)
    (candidate / "candidate-state.json").write_text(json.dumps({
        "pipeline_version": "commentary-v1.2-enrichment",
        "full_bible_generation_authorized": True,
    }))
    return V12CorpusRunner(
        tmp_path, candidate_root=candidate, release_root=tmp_path / "release",
        canonical_loader=lambda: [],
    )


def _codex(tmp_path: Path) -> Path:
    executable = tmp_path / "codex"
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    return executable


def _prepared_run(tmp_path: Path, *, references=("Genesis 1", "Genesis 2"), source_limited=()) -> tuple[V12CorpusRunner, str, Path]:
    runner = _runner(tmp_path)
    run_id = "session-batch-test"
    root = tmp_path / "candidate" / "corpus-runner" / "runs" / run_id
    chapters = []
    state_chapters = {}
    for ordinal, reference in enumerate(references, 1):
        book, chapter = reference.rsplit(" ", 1)
        chapter = int(chapter)
        chapters.append({"reference": reference, "book": book, "chapter": chapter, "canonical_ordinal": ordinal})
        if reference in source_limited:
            state_chapters[reference] = {"status": "validated", "classification": "source-limited"}
            continue
        state_chapters[reference] = {"status": "awaiting_render", "attempt": 0}
        input_root = root / "chapters" / f"{book.lower()}_{chapter:03d}" / "renderer-input"
        system, user = f"system {reference}", f"user {reference}"
        input_root.mkdir(parents=True)
        (input_root / "system_prompt.txt").write_text(system)
        (input_root / "user_prompt.txt").write_text(user)
        (input_root / "metadata.json").write_text(json.dumps({
            "run_id": run_id, "reference": reference, "book": book, "chapter": chapter,
            "requested_model": CODEX_TERRA_MODEL, "requested_effort": CODEX_TERRA_EFFORT,
            "renderer_input_sha256": sha256_bytes((system + "\n\nUSER PROMPT\n" + user).encode()),
        }))
    manifest = {
        "workflow": "prepare -> codex_session_render -> finalize",
        "run_id": run_id, "batch_number": 6, "chapters": chapters,
    }
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    (root / "state.json").write_text(json.dumps({
        "run_id": run_id, "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "chapters": state_chapters,
    }))
    return runner, run_id, root


def _success(calls: list[list[str]]):
    def invoke(command, **kwargs):
        calls.append(command)
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_bytes(b'{"reference":"test"}')
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
    return invoke


def test_render_local_uses_only_existing_prepared_run_and_frozen_terra_contract(tmp_path):
    runner, run_id, root = _prepared_run(tmp_path, source_limited=("Genesis 2",))
    calls: list[list[str]] = []

    result = runner.render_local(run_id, codex_path=_codex(tmp_path), runner=_success(calls))

    assert result["rendered"] == ["Genesis 1"]
    assert result["source_limited"] == ["Genesis 2"]
    assert len(calls) == 1
    assert calls[0][calls[0].index("-m") + 1] == "gpt-5.6-terra"
    assert calls[0][calls[0].index("-c") + 1] == 'model_reasoning_effort="high"'
    assert "--ephemeral" in calls[0] and "--ignore-user-config" in calls[0]
    assert not (root / "chapters" / "genesis_002" / "raw-response.bin").exists()
    assert (root / "chapters" / "genesis_001" / "raw-response.bin").read_bytes() == b'{"reference":"test"}'
    assert json.loads((root / "chapters" / "genesis_001" / "renderer-receipt.json").read_text())["transport"] == "local_codex_cli"


def test_render_local_resume_skips_completed_immutable_response(tmp_path):
    runner, run_id, _ = _prepared_run(tmp_path, references=("Genesis 1",))
    calls: list[list[str]] = []
    runner.render_local(run_id, codex_path=_codex(tmp_path), runner=_success(calls))
    resumed = runner.render_local(run_id, codex_path=_codex(tmp_path), runner=_success(calls))

    assert len(calls) == 1
    assert resumed["rendered"] == []
    assert resumed["skipped"] == ["Genesis 1"]


def test_render_local_rejects_unknown_or_tampered_prepared_identity(tmp_path):
    runner = _runner(tmp_path)
    with pytest.raises(V12CorpusError, match="unknown prepared session run"):
        runner.render_local("session-missing", codex_path=_codex(tmp_path), runner=_success([]))

    runner, run_id, root = _prepared_run(tmp_path)
    metadata = root / "chapters" / "genesis_001" / "renderer-input" / "metadata.json"
    value = json.loads(metadata.read_text())
    value["renderer_input_sha256"] = "tampered"
    metadata.write_text(json.dumps(value))
    with pytest.raises(V12IntegrityError, match="renderer-input identity changed"):
        runner.render_local(run_id, codex_path=_codex(tmp_path), runner=_success([]))


def test_subprocess_failure_checkpoints_earlier_response_without_fake_raw(tmp_path):
    runner, run_id, root = _prepared_run(tmp_path)
    calls = 0

    def invoke(command, **kwargs):
        nonlocal calls
        calls += 1
        output = Path(command[command.index("--output-last-message") + 1])
        if calls == 1:
            output.write_bytes(b"{}")
            return subprocess.CompletedProcess(command, 0, stdout="first", stderr="")
        return subprocess.CompletedProcess(command, 9, stdout="", stderr="transport failed")

    with pytest.raises(V12CorpusError, match="Genesis 2"):
        runner.render_local(run_id, codex_path=_codex(tmp_path), runner=invoke)
    assert (root / "chapters" / "genesis_001" / "raw-response.bin").is_file()
    assert not (root / "chapters" / "genesis_002" / "raw-response.bin").exists()
    assert json.loads(next((root / "chapters" / "genesis_002" / "transport-failures").glob("*.json")).read_text())["stderr"] == "transport failed"


def test_finalize_is_called_only_after_all_local_responses_exist(tmp_path, monkeypatch):
    runner, run_id, _ = _prepared_run(tmp_path, references=("Genesis 1",))
    finalized = []
    monkeypatch.setattr(runner, "finalize", lambda *, run_id: finalized.append(run_id) or {"status": "FINALIZED"})
    result = runner.render_local(run_id, codex_path=_codex(tmp_path), runner=_success([]), finalize=True)

    assert finalized == [run_id]
    assert result["finalize"]["status"] == "FINALIZED"
