import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from framework.commentary.v12_corpus import (
    V12CorpusError,
    V12AuthorizationError,
    V12CorpusRunner,
    V12IntegrityError,
    assess_chapter_renderability,
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


def _runner(tmp_path, *, authorized=True, pipeline=None, canonical_loader=_canonical):
    candidate = tmp_path / "candidate"
    candidate.mkdir(parents=True)
    (candidate / "candidate-state.json").write_text(json.dumps({
        "pipeline_version": "commentary-v1.2-enrichment",
        "full_bible_generation_authorized": authorized,
    }))
    return V12CorpusRunner(
        tmp_path,
        candidate_root=candidate,
        release_root=tmp_path / "release",
        canonical_loader=canonical_loader,
        pipeline=pipeline,
    )


def _prepared(reference, *, availability="AVAILABLE", evidence_items=None, unit_count=1):
    items = list(evidence_items or [])
    units = [SimpleNamespace(id=f"unit-{index}") for index in range(unit_count)]
    book, chapter = reference.rsplit(" ", 1)
    return SimpleNamespace(
        bundle=SimpleNamespace(
            passage_ref=reference,
            evidence_items=items,
            evidence_hash=f"evidence-{reference}",
            version="1.1",
        ),
        synthesis=SimpleNamespace(
            reference=reference,
            evidence_availability=availability,
            synthesis_units=units,
            synthesis_hash=f"synthesis-{reference}",
        ),
        row={"input_identity": {
            "packet_id": f"packet-{reference}",
            "packet_hash": f"packet-hash-{reference}",
        }},
    )


def _ineligible_evidence(reference):
    from bhf_agent.presentation.models import EvidenceItem

    return EvidenceItem(
        id=f"evidence-{reference}", claim="background", category="history",
        source_ids=[], related_entity_ids=[], passage_anchors=[reference + ":1"],
        confidence="medium", relevance_metadata={"source_kind": "unknown"},
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


def test_renderability_classifies_true_data_gap_without_renderer_work():
    assessment = assess_chapter_renderability(
        _prepared("Numbers 3", availability="DATA_GAP", unit_count=0)
    )
    assert assessment.renderable is False
    assert assessment.evidence_item_count == 0
    assert "DATA_GAP" in assessment.reason


def test_renderability_classifies_empty_thin_synthesis_as_source_limited():
    prepared = _prepared(
        "Numbers 6", availability="THIN",
        evidence_items=[_ineligible_evidence("Numbers 6")], unit_count=0,
    )
    assessment = assess_chapter_renderability(prepared)
    assert assessment.renderable is False
    assert assessment.evidence_item_count == 1
    assert assessment.eligible_evidence_item_count == 0
    assert "applicability" in assessment.reason


def test_empty_synthesis_with_eligible_evidence_fails_as_compiler_regression():
    from bhf_agent.presentation.models import EvidenceItem

    prepared = _prepared(
        "Genesis 1", availability="AVAILABLE",
        evidence_items=[EvidenceItem(
            id="e1", claim="current", category="history", source_ids=[],
            related_entity_ids=[], passage_anchors=["Genesis 1:1"], confidence="high",
            relevance_metadata={"source_kind": "archaeology_resolver", "anchor_source": "resolver", "inherited_from_parent": False, "applicability_scope": "passage"},
        )], unit_count=0,
    )
    with pytest.raises(V12IntegrityError, match="synthesis compiler regression"):
        assess_chapter_renderability(prepared)


def test_normal_chapter_is_renderable_and_never_source_limited():
    assessment = assess_chapter_renderability(_prepared("Genesis 1", unit_count=1))
    assert assessment.renderable is True
    assert assessment.reason is None


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


def test_authorization_true_and_false_use_only_the_runner_candidate_root(tmp_path):
    true_runner = _runner(tmp_path / "true", authorized=True, pipeline=FakePipeline())
    false_runner = _runner(tmp_path / "false", authorized=False, pipeline=FakePipeline())
    assert true_runner.discover(1).full_bible_generation_authorized is True
    assert false_runner.discover(1).full_bible_generation_authorized is False
    assert json.loads((tmp_path / "true" / "candidate" / "candidate-state.json").read_text())["full_bible_generation_authorized"] is True
    assert json.loads((tmp_path / "false" / "candidate" / "candidate-state.json").read_text())["full_bible_generation_authorized"] is False


def test_source_limited_chapter_is_terminal_without_raw_and_skipped_by_discovery(tmp_path, monkeypatch):
    runner = _runner(tmp_path)
    prepared = _prepared("Genesis 1", availability="DATA_GAP", unit_count=0)
    monkeypatch.setattr(runner, "_prepared_for_session", lambda entry: (
        prepared, assess_chapter_renderability(prepared)
    ))
    prepared_result = runner.prepare(1)
    chapter_root = tmp_path / "candidate" / "corpus-runner" / "runs" / prepared_result["run_id"] / "chapters" / "genesis_001"
    receipt = json.loads((chapter_root / "result.json").read_text())
    assert receipt["release_state"] == "NOT_RENDERABLE_SOURCE_LIMITED"
    assert receipt["reason"] == "commentary_source_limited"
    assert not (chapter_root / "raw-response.bin").exists()
    assert runner.discover(1).next_chapters == ("Genesis 2",)
    finalized = runner.finalize()
    assert finalized["source_limited"] == 1


def test_source_limited_prepare_never_calls_ancestry_or_creates_renderer_input(tmp_path, monkeypatch):
    runner = _runner(tmp_path)
    prepared = _prepared("Genesis 1", availability="THIN", unit_count=0)
    calls = []
    monkeypatch.setattr(runner, "_prepared_for_session", lambda entry: (
        prepared, assess_chapter_renderability(prepared)
    ))
    monkeypatch.setattr(runner, "_write_renderer_input", lambda *args, **kwargs: calls.append(args) or {})
    monkeypatch.setattr("framework.commentary.v12_corpus.build_ancestry_envelope", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ancestry must not run")))
    result = runner.prepare(1)
    assert result["source_limited_count"] == 1
    assert calls == []
    assert not list((tmp_path / "candidate" / "corpus-runner").rglob("renderer-input"))


def test_mixed_fifty_chapter_prepare_terminalizes_only_source_limited_rows(tmp_path, monkeypatch):
    canonical = [
        {"reference": f"Genesis {index}", "book": "Genesis", "chapter": index, "canonical_ordinal": index}
        for index in range(1, 51)
    ]
    runner = _runner(tmp_path, canonical_loader=lambda: canonical)
    source_refs = {f"Genesis {index}" for index in range(1, 7)}

    def fake_prepared(entry):
        availability = "DATA_GAP" if entry["reference"] in source_refs else "AVAILABLE"
        item_count = 0 if entry["reference"] in source_refs else 0
        prepared = _prepared(entry["reference"], availability=availability, unit_count=0 if item_count == 0 and entry["reference"] in source_refs else 1)
        return prepared, assess_chapter_renderability(prepared)

    monkeypatch.setattr(runner, "_prepared_for_session", fake_prepared)
    monkeypatch.setattr(runner, "_write_renderer_input", lambda *args, **kwargs: {"renderer_input_sha256": "frozen"})
    result = runner.prepare(50)
    assert result["chapter_count"] == 50
    assert result["renderable_count"] == 44
    assert result["source_limited_count"] == 6
    assert runner.discover(50).terminal_v1_2_chapters == 6
    assert runner.discover(50).chapters_remaining == 44


def test_partial_prepare_reuses_matching_immutable_inputs_and_rejects_mismatch(tmp_path, monkeypatch):
    runner = _runner(tmp_path)
    prepared = _prepared("Genesis 1", unit_count=1)
    monkeypatch.setattr(runner, "_prepared_for_session", lambda entry: (
        prepared, assess_chapter_renderability(prepared)
    ))

    def freeze(run_root, entry, *, run_id, prepared):
        from framework.commentary.production.models import write_immutable, write_json
        input_root = run_root / "chapters" / "genesis_001" / "renderer-input"
        write_immutable(input_root / "system_prompt.txt", b"system")
        write_immutable(input_root / "user_prompt.txt", b"user")
        write_json(input_root / "metadata.json", {"renderer_input_sha256": "frozen"}, immutable=True)
        return {"renderer_input_sha256": "frozen"}

    monkeypatch.setattr(runner, "_write_renderer_input", freeze)
    first = runner.prepare(1)
    second = runner.prepare(1)
    assert second["run_id"] == first["run_id"]
    input_root = tmp_path / "candidate" / "corpus-runner" / "runs" / first["run_id"] / "chapters" / "genesis_001" / "renderer-input"
    (input_root / "user_prompt.txt").write_text("tampered")
    with pytest.raises(Exception, match="immutable artifact collision"):
        runner.prepare(1)


def test_prepare_resumes_incomplete_batch_before_selecting_after_source_limited_rows(tmp_path, monkeypatch):
    canonical = [
        {"reference": f"Genesis {index}", "book": "Genesis", "chapter": index, "canonical_ordinal": index}
        for index in range(1, 4)
    ]
    runner = _runner(tmp_path, canonical_loader=lambda: canonical)
    source = _prepared("Genesis 1", availability="DATA_GAP", unit_count=0)
    renderable = _prepared("Genesis 2", unit_count=1)
    renderable_three = _prepared("Genesis 3", unit_count=1)
    prepared_by_reference = {
        "Genesis 1": source,
        "Genesis 2": renderable,
        "Genesis 3": renderable_three,
    }
    monkeypatch.setattr(runner, "_prepared_for_session", lambda entry: (
        prepared_by_reference[entry["reference"]],
        assess_chapter_renderability(prepared_by_reference[entry["reference"]]),
    ))
    monkeypatch.setattr(runner, "_write_renderer_input", lambda *args, **kwargs: {"renderer_input_sha256": "frozen"})
    first = runner.prepare(3)
    second = runner.prepare(3)
    assert second["run_id"] == first["run_id"]
    assert second["chapter_count"] == 3
    assert second["source_limited_count"] == 1
    assert runner.discover(3).next_chapters == ("Genesis 2", "Genesis 3")


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

    def freeze(run_root, entry, *, run_id, prepared):
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
