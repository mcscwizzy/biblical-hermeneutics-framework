from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from framework.commentary.orchestrator import (
    CORPUS_COMPLETE,
    STAGES,
    _transition,
    accept_handoff,
    advance_batch,
    initialize,
    load_state,
    run_stage,
    resume,
    save_state,
    state_path,
    status,
    validate_state,
    _terra_command,
    _preflight_outputs_already_complete,
)


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _locked_batch(repo: Path, *, chapter_status: str = "PASS") -> Path:
    batch = repo / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-004"
    reference = "Genesis 1"
    _write(batch / "batch-manifest.json", {
        "batch_id": "batch-004", "status": "LOCKED", "current_population": {"eligible": 5},
        "candidate_pool": [{"reference": reference}], "final_chapters": [{"reference": reference, "book": "Genesis", "genre": "law", "availability": "AVAILABLE", "evidence_count": 1}],
    })
    _write(batch / "preflight-report.json", {"batch_id": "batch-004", "status": "PASS"})
    _write(batch / "evidence-certification.json", {
        "batch_id": "batch-004", "status": "LOCKED", "chapters": [{"reference": reference, "status": chapter_status, "evidence_ids": ["e-1"]}],
    })
    _write(batch / "terra-input-manifest.json", {
        "batch_id": "batch-004", "status": "READY_FOR_TERRA", "prose_included": False,
        "chapters": [{"reference": reference}],
    })
    return batch


def test_initial_state_is_derived_and_state_hash_is_valid(tmp_path):
    state = initialize(tmp_path)
    assert state["current_batch"] == 1
    assert state["current_stage"] == "CANDIDATE_SELECTION"
    assert state["required_model"] == "luna"
    assert state["required_effort"] == "high"
    assert load_state(state_path(tmp_path))["state_hash"] == state["state_hash"]


def test_locked_batch_bootstraps_to_generation_handoff(tmp_path):
    _locked_batch(tmp_path)
    state = initialize(tmp_path)
    assert state["current_batch"] == 4
    assert state["current_stage"] == "READY_FOR_GENERATION"
    assert state["required_model"] == "terra"
    assert state["required_effort"] == "medium"
    assert state["remaining_chapters"] == 5


def test_corrupt_state_is_rejected(tmp_path):
    initialize(tmp_path)
    path = state_path(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["current_batch"] = 99
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Exception, match="hash mismatch"):
        load_state(path)


def test_atomic_save_recalculates_state_hash(tmp_path):
    state = initialize(tmp_path)
    state["history"].append({"event": "TEST"})
    saved = save_state(state_path(tmp_path), state)
    assert load_state(state_path(tmp_path))["state_hash"] == saved["state_hash"]
    assert not list(state_path(tmp_path).parent.glob(".pipeline-state.json.tmp.*"))


def test_illegal_stage_transition_is_rejected(tmp_path):
    state = initialize(tmp_path)
    with pytest.raises(Exception, match="illegal transition"):
        _transition(state, next_stage="EVIDENCE_LOCKED", event="bad")


def test_stage_metadata_contains_model_and_gate_policy():
    assert STAGES["EVIDENCE_PREFLIGHT"].required_model == "luna"
    assert STAGES["EVIDENCE_PREFLIGHT"].required_effort == "high"
    assert STAGES["PROSE_GENERATION"].required_model == "terra"
    assert STAGES["PROSE_GENERATION"].required_effort == "medium"
    assert STAGES["EVIDENCE_PREFLIGHT"].resumable is True
    assert STAGES["PROSE_GENERATION"].mutates_prose is True
    assert STAGES["PROSE_GENERATION"].resumable is False


def test_terra_generation_uses_the_repository_runner(tmp_path):
    state = initialize(tmp_path)
    state["current_batch"] = 4
    command = _terra_command(tmp_path, state, tmp_path / "staging", tmp_path / "report.md")
    assert command[1].endswith("tools/terra_commentary_scaled_batch.py")
    assert "--output" in command and "--report" in command


def test_protected_fingerprint_change_is_a_validation_error(tmp_path):
    prose = tmp_path / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-terra/chapters/genesis_001.json"
    _write(prose, {"reference": "Genesis 1", "text": "protected"})
    state = initialize(tmp_path)
    prose.write_text('{"reference":"Genesis 1","text":"changed"}\n', encoding="utf-8")
    errors = validate_state(tmp_path, state)
    assert any("protected fingerprint changed" in error for error in errors)


def test_integrity_failure_becomes_a_first_class_blocker(tmp_path):
    prose = tmp_path / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-terra/chapters/genesis_001.json"
    _write(prose, {"reference": "Genesis 1", "text": "protected"})
    initialize(tmp_path)
    prose.write_text('{"reference":"Genesis 1","text":"changed"}\n', encoding="utf-8")
    result = run_stage(tmp_path)
    assert result["action"] == "BLOCKED"
    blocked = load_state(state_path(tmp_path))
    assert blocked["status"] == "BLOCKED"
    assert blocked["blocked_reason"]["error_class"] == "NON_RETRYABLE"


def test_validate_reports_blocked_state_as_blocked(tmp_path):
    state = initialize(tmp_path)
    state["status"] = "BLOCKED"
    state["blocked_reason"] = {"reason": "review required"}
    save_state(state_path(tmp_path), state)
    from framework.commentary.orchestrator import main
    assert main(["--repo-root", str(tmp_path), "validate"]) == 12


def test_quarantine_cannot_enter_generation_gate(tmp_path):
    _locked_batch(tmp_path, chapter_status="QUARANTINE")
    state = initialize(tmp_path)
    errors = validate_state(tmp_path, state)
    assert any("non-PASS" in error for error in errors)


def test_model_handoff_rejects_wrong_model_and_accepts_terra(tmp_path):
    _locked_batch(tmp_path)
    initialize(tmp_path)
    wrong = accept_handoff(tmp_path, model="luna", effort="high")
    assert wrong["action"] == "MODEL_HANDOFF_REQUIRED"
    accepted = accept_handoff(tmp_path, model="terra", effort="medium")
    assert accepted["action"] == "ADVANCED"
    assert load_state(state_path(tmp_path))["current_stage"] == "PROSE_GENERATION"


def test_wrong_model_cannot_advance_a_luna_stage(tmp_path):
    initialize(tmp_path)
    before = load_state(state_path(tmp_path))
    result = run_stage(tmp_path, model="terra", effort="medium")
    assert result["action"] == "MODEL_HANDOFF_REQUIRED"
    assert load_state(state_path(tmp_path))["current_stage"] == before["current_stage"]


def test_interrupted_stage_remains_resumable_and_is_not_pass(tmp_path):
    state = initialize(tmp_path)
    state["stage_status"] = "RUNNING"
    state["resume_token"] = {"chunk": "chunk-001", "complete": False}
    save_state(state_path(tmp_path), state)
    result = resume(tmp_path)
    assert result["action"] == "RESUME_REQUIRED"
    assert load_state(state_path(tmp_path))["stage_status"] == "RUNNING"


def test_empty_preflight_pool_becomes_human_review_blocker(tmp_path, monkeypatch):
    initialize(tmp_path)
    work_root = tmp_path / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/.batch-001.work"
    _write(work_root / "blocked-report.json", {
        "manifest": {
            "candidate_pool_size": 0,
            "chapters_evaluated": 0,
            "current_population": {"eligible": 935, "insufficient": 153},
            "skipped_verdicts": [
                {"reference": "1 Corinthians 1", "status": "SKIP_PRIOR_QUARANTINE"},
                {"reference": "Genesis 1", "status": "SKIP_ALREADY_GENERATED"},
            ],
        },
    })
    monkeypatch.setattr(
        "framework.commentary.orchestrator.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1),
    )
    result = run_stage(tmp_path, model="luna", effort="high")
    assert result["action"] == "BLOCKED"
    blocked = load_state(state_path(tmp_path))
    assert blocked["status"] == "BLOCKED"
    assert blocked["blocked_reason"]["error_class"] == "HUMAN_REVIEW_REQUIRED"
    assert "no eligible candidate chapters" in blocked["blocked_reason"]["reason"]
    assert blocked["blocked_reason"]["affected_chapters"] == ["1 Corinthians 1"]


def test_promoted_preflight_outputs_are_reconciled_without_child_rerun(tmp_path):
    _locked_batch(tmp_path)
    initialize(tmp_path)
    assert _preflight_outputs_already_complete(tmp_path, 4) is True
    state = load_state(state_path(tmp_path))
    state["current_stage"] = "EVIDENCE_PREFLIGHT"
    state["stage_status"] = "RUNNING"
    save_state(state_path(tmp_path), state)
    result = run_stage(tmp_path, model="luna", effort="high")
    assert result["action"] == "STAGE_COMPLETE"
    assert load_state(state_path(tmp_path))["current_stage"] == "EVIDENCE_CERTIFICATION"


def test_pending_stage_validates_inputs_without_demanding_its_output(tmp_path):
    batch = _locked_batch(tmp_path)
    state = initialize(tmp_path)
    state["current_stage"] = "EVIDENCE_CERTIFICATION"
    state["stage_status"] = "PENDING"
    save_state(state_path(tmp_path), state)
    (batch / "evidence-certification.json").unlink()
    assert validate_state(tmp_path, load_state(state_path(tmp_path))) == []


def test_batch_advancement_initializes_next_batch_without_running_it(tmp_path):
    _locked_batch(tmp_path)
    state = initialize(tmp_path)
    state["current_stage"] = "BATCH_COMPLETE"
    state["stage_status"] = "PENDING"
    save_state(state_path(tmp_path), state)
    result = advance_batch(tmp_path)
    assert result["action"] == "ADVANCED"
    next_state = load_state(state_path(tmp_path))
    assert next_state["current_batch"] == 5
    assert next_state["current_stage"] == "CANDIDATE_SELECTION"
    assert (tmp_path / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/.batch-005.work").is_dir()


def test_corpus_completion_is_explicit(tmp_path):
    _locked_batch(tmp_path)
    state = initialize(tmp_path)
    state["current_stage"] = "BATCH_COMPLETE"
    state["stage_status"] = "PENDING"
    state["eligible_corpus_total"] = 0
    state["finalized_chapters"] = 0
    state["remaining_chapters"] = 0
    save_state(state_path(tmp_path), state)
    result = advance_batch(tmp_path)
    assert result["action"] == CORPUS_COMPLETE
    final_state = load_state(state_path(tmp_path))
    assert final_state["status"] == CORPUS_COMPLETE
    assert (tmp_path / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/final-corpus-certification.json").exists()
