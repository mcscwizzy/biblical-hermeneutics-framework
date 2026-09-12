import json
import hashlib
from pathlib import Path

import pytest

from framework.commentary.v12_corpus import (
    V12AuthorizationError,
    V12CorpusRunner,
    V12IntegrityError,
)
from framework.commentary.v12_config import (
    DEFAULT_V12_PROSE_MODEL,
    V12ProseConfigurationError,
    ensure_v12_prose_renderer_available,
    load_v12_prose_configuration,
)
from bhf_agent.chapter_commentary.models import CommentaryGenerationResult


def _canonical():
    return [
        {"reference": "Genesis 1", "book": "Genesis", "chapter": 1, "canonical_ordinal": 1},
        {"reference": "Genesis 2", "book": "Genesis", "chapter": 2, "canonical_ordinal": 2},
        {"reference": "Genesis 3", "book": "Genesis", "chapter": 3, "canonical_ordinal": 3},
        {"reference": "Exodus 1", "book": "Exodus", "chapter": 1, "canonical_ordinal": 4},
    ]


class FakePipeline:
    def __init__(self, statuses=None):
        self.calls = []
        self.statuses = statuses or {}

    def generate(self, book, chapter):
        self.calls.append(f"{book} {chapter}")
        reference = f"{book} {chapter}"
        return CommentaryGenerationResult(reference=reference, status=self.statuses.get(reference, "validated"))


def _runner(tmp_path, *, authorized=True, pipeline=None):
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "candidate-state.json").write_text(json.dumps({
        "pipeline_version": "commentary-v1.2-enrichment",
        "full_bible_generation_authorized": authorized,
    }))
    return V12CorpusRunner(
        tmp_path,
        candidate_root=candidate,
        release_root=tmp_path / "release",
        canonical_loader=_canonical,
        pipeline=pipeline,
    )


def _write_v12_config(tmp_path, *, model=DEFAULT_V12_PROSE_MODEL, effort="high"):
    path = tmp_path / "config" / "commentary-v1.2-prose.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "config_version": 1,
        "adapter": "openai_compatible",
        "base_url": "https://api.openai.com/v1",
        "model": model,
        "reasoning_effort": effort,
        "profile": "commentary-v1.2-test",
    }))
    return path


def test_default_v12_prose_configuration_resolves_terra_high_and_ignores_codex_runtime(tmp_path, monkeypatch):
    _write_v12_config(tmp_path)
    monkeypatch.setenv("CODEX_MODEL", "gpt-5.6-luna")
    configuration = load_v12_prose_configuration(tmp_path)
    assert configuration.is_default
    assert configuration.config.model == "gpt-5.6-terra"
    assert configuration.config.reasoning_effort == "high"
    assert configuration.metadata()["pipeline"] == "commentary-v1.2-enrichment"


def test_explicit_v12_config_overrides_persisted_default(tmp_path):
    _write_v12_config(tmp_path)
    explicit = tmp_path / "explicit.json"
    explicit.write_text(json.dumps({
        "config_version": 1,
        "adapter": "ollama",
        "base_url": "http://localhost:11434",
        "model": "deliberate-local-model",
        "profile": "explicit-test",
    }))
    configuration = load_v12_prose_configuration(tmp_path, explicit)
    assert not configuration.is_default
    assert configuration.config.model == "deliberate-local-model"


def test_terra_renderer_unavailability_fails_closed(tmp_path):
    _write_v12_config(tmp_path)
    configuration = load_v12_prose_configuration(tmp_path)
    with pytest.raises(V12ProseConfigurationError, match="TERRA_HIGH_PROSE_RENDERER_UNAVAILABLE"):
        ensure_v12_prose_renderer_available(
            configuration,
            build_adapter=lambda config: object(),
            credential_present=lambda config: False,
        )


def test_canonical_traversal_and_batch_limit(tmp_path):
    runner = _runner(tmp_path)
    discovery = runner.discover(2)
    assert discovery.next_chapters == ("Genesis 1", "Genesis 2")
    assert discovery.chapters_remaining == 4


def test_terminal_runner_results_are_skipped_and_resume_selects_next(tmp_path):
    pipeline = FakePipeline()
    runner = _runner(tmp_path, pipeline=pipeline)
    first = runner.run(2)
    assert pipeline.calls == ["Genesis 1", "Genesis 2"]
    assert len(first["chapters"]) == 2
    second = runner.run(2)
    assert pipeline.calls == ["Genesis 1", "Genesis 2", "Genesis 3", "Exodus 1"]
    assert second["discovery"]["chapters_remaining"] == 0


def test_existing_terminal_release_state_is_skipped(tmp_path):
    runner = _runner(tmp_path)
    release = tmp_path / "release"
    release.mkdir()
    manifest = release / ".bhf-commentary-release.json"
    manifest.write_text(json.dumps({
        "release": "commentary-v1.2",
        "chapter_publication_index": [{
            "book": "Genesis", "chapter": 1, "release_state": "PUBLISHED", "validated": True,
        }],
    }))
    (release / ".bhf-commentary-release-checksums.json").write_text(json.dumps({
        "files": {manifest.name: hashlib.sha256(manifest.read_bytes()).hexdigest()},
    }))
    discovery = runner.discover(3)
    assert not discovery.conflicts
    assert discovery.terminal_v1_2_chapters == 1
    assert discovery.next_chapters == ("Genesis 2", "Genesis 3", "Exodus 1")


def test_dry_run_does_not_call_pipeline_or_write_runs(tmp_path):
    pipeline = FakePipeline()
    runner = _runner(tmp_path, pipeline=pipeline)
    result = runner.dry_run(3)
    assert result["status"] == "DRY_RUN"
    assert pipeline.calls == []
    assert not (tmp_path / "candidate" / "corpus-runner").exists()


def test_authorization_guard_blocks_generation(tmp_path):
    pipeline = FakePipeline()
    runner = _runner(tmp_path, authorized=False, pipeline=pipeline)
    with pytest.raises(V12AuthorizationError):
        runner.run(1)
    assert pipeline.calls == []


def test_result_classification_passes_through_unchanged(tmp_path):
    pipeline = FakePipeline({"Genesis 1": "needs_review"})
    runner = _runner(tmp_path, pipeline=pipeline)
    result = runner.run(1)
    assert result["chapters"][0]["status"] == "needs_review"
    receipt = next((tmp_path / "candidate" / "corpus-runner").rglob("result.json"))
    assert json.loads(receipt.read_text())["status"] == "needs_review"


def test_duplicate_canonical_identity_fails_closed(tmp_path):
    runner = _runner(tmp_path)
    runner.canonical_loader = lambda: _canonical() + [_canonical()[0]]
    with pytest.raises(V12IntegrityError):
        runner.run(1)


def test_awaiting_render_state_is_nonterminal_but_not_corrupt(tmp_path):
    runner = _runner(tmp_path)
    runs = tmp_path / "candidate" / "corpus-runner" / "runs" / "prepared"
    runs.mkdir(parents=True)
    (runs / "manifest.json").write_text(json.dumps({
        "workflow": "prepare -> codex_session_render -> finalize",
        "chapters": [{"reference": "Genesis 1", "book": "Genesis", "chapter": 1}],
    }))
    (runs / "state.json").write_text(json.dumps({
        "artifact_version": "commentary-v1.2-corpus-session-state-v1",
        "chapters": {"Genesis 1": {"status": "awaiting_render", "attempt": 0}},
    }))
    discovery = runner.discover(2)
    assert not discovery.conflicts
    assert discovery.next_chapters == ("Genesis 1", "Genesis 2")


def test_prepare_is_session_only_and_resumable_without_pipeline(tmp_path, monkeypatch):
    runner = _runner(tmp_path)
    writes = []

    def freeze(run_root, entry, *, run_id):
        writes.append(entry["reference"])
        return {"renderer_input_sha256": "frozen"}

    monkeypatch.setattr(runner, "_write_renderer_input", freeze)
    first = runner.prepare(2)
    second = runner.prepare(2)
    assert first["status"] == "PREPARED"
    assert second["run_id"] == first["run_id"]
    assert writes == ["Genesis 1", "Genesis 2", "Genesis 1", "Genesis 2"]
    state = json.loads((tmp_path / "candidate" / "corpus-runner" / "runs" / first["run_id"] / "state.json").read_text())
    assert all(row["status"] == "awaiting_render" for row in state["chapters"].values())


def test_finalize_refuses_missing_raw_responses_before_validation(tmp_path, monkeypatch):
    runner = _runner(tmp_path)
    monkeypatch.setattr(runner, "_write_renderer_input", lambda *args, **kwargs: {"renderer_input_sha256": "frozen"})
    prepared = runner.prepare(1)
    with pytest.raises(Exception, match="missing raw responses"):
        runner.finalize()
    assert not (tmp_path / "candidate" / "corpus-runner" / "runs" / prepared["run_id"] / "chapters" / "genesis_001" / "result.json").exists()


def test_finalize_rejects_duplicate_response_artifacts(tmp_path, monkeypatch):
    runner = _runner(tmp_path)
    monkeypatch.setattr(runner, "_write_renderer_input", lambda *args, **kwargs: {"renderer_input_sha256": "frozen"})
    prepared = runner.prepare(1)
    chapter = tmp_path / "candidate" / "corpus-runner" / "runs" / prepared["run_id"] / "chapters" / "genesis_001"
    chapter.mkdir(parents=True)
    (chapter / "raw-response.bin").write_bytes(b"{}")
    (chapter / "raw-response-second.bin").write_bytes(b"{}")
    with pytest.raises(V12IntegrityError, match="duplicate/conflicting responses"):
        runner.finalize()
