import json
import hashlib
from pathlib import Path

import pytest

from framework.commentary.v12_corpus import (
    V12AuthorizationError,
    V12CorpusRunner,
    V12IntegrityError,
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
