"""Focused tests for the guarded Commentary production machinery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from framework.commentary.production.census import build_census, canonical_chapters
from framework.commentary.production.ledger import rebuild_ledger
from framework.commentary.production.manifests import build_manifest, load_manifest, save_manifest
from framework.commentary.production.models import (
    COMPLETE,
    GENERATING,
    InputIdentity,
    ManifestError,
    PreparedChapter,
    ProductionError,
    QUARANTINED,
    STALE_INPUT,
    transition,
    write_json,
)
from framework.commentary.production.recovery import reconcile_batch
from framework.commentary.production.runner import ProviderFailure, ProductionRunner, RawResponse
from framework.commentary.production.sampling import sample_audit_records
from bhf_agent.chapter_commentary.dense_reader import _activation_decision


def _prepared(reference: str = "Genesis 1", ordinal: int = 1, *, identity: str = "e") -> PreparedChapter:
    book, chapter_text = reference.rsplit(" ", 1)
    chapter = int(chapter_text)
    input_identity = InputIdentity(identity, "s" + identity, "1.5", "1.2", "1.1", "1.1", "commentary-richness-gate-v2.1", "validator", "p" + identity, "packet:" + identity)
    row = {"reference": reference, "book": book, "chapter": chapter, "canonical_ordinal": ordinal, "literary_category": "Pentateuch", "evidence_availability": "AVAILABLE", "evidence_count": 1, "synthesis_unit_count": 1, "density_bucket": "1-5", "input_identity": input_identity.to_dict()}
    return PreparedChapter(row=row, packet={"packet_id": "packet:" + identity, "packet_hash": "p" + identity, "user_prompt": "fixture"})


def test_census_is_canonical_and_does_not_promote_historical_artifacts(tmp_path):
    census = build_census(Path("."))
    assert census["canonical_chapter_count"] == 1189
    assert census["production_complete_count"] == 0
    assert census["counts"] == {"PENDING": 1189}
    assert census["historical_counts"]["scale_pilot_only"] == 50
    assert census["historical_counts"]["experimental_only"] == 43


def test_manifest_batch_membership_and_identity_are_deterministic(tmp_path):
    first = build_manifest([_prepared("Genesis 1", 1), _prepared("Romans 8", 1000)], batch_size=1, run_id="run-test")
    second = build_manifest([_prepared("Romans 8", 1000), _prepared("Genesis 1", 1)], batch_size=1, run_id="run-test")
    assert first == second
    path = tmp_path / "manifest.json"
    save_manifest(first, path)
    assert load_manifest(path) == first
    changed = json.loads(path.read_text())
    changed["chapters"][0]["batch_id"] = "batch-999"
    path.write_text(json.dumps(changed))
    with pytest.raises(ManifestError):
        load_manifest(path)


def test_invalid_state_transition_fails_loudly():
    with pytest.raises(ProductionError):
        transition(GENERATING, COMPLETE)


def test_runner_resumes_without_regenerating_terminal_chapter(tmp_path):
    prepared = _prepared()
    manifest = build_manifest([prepared], batch_size=1, run_id="run-resume")
    manifest_path = tmp_path / "manifest.json"
    save_manifest(manifest, manifest_path)

    class Harness(ProductionRunner):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.calls = 0

        def _import_and_evaluate(self, manifest, batch, chapter, prepared, record, state, enable_reader):
            self._set_record(state, chapter["reference"], "VALIDATING")
            self._set_record(state, chapter["reference"], "ACCEPTED")
            self._set_record(state, chapter["reference"], "GATE_PASS")
            self._set_record(state, chapter["reference"], COMPLETE)
            self._save_state(state)
            return {"reference": chapter["reference"], "state": COMPLETE}

    class Renderer:
        def render(self, chapter, prepared):
            harness.calls += 1
            return RawResponse(text='{"fixture": true}')

    harness = Harness(tmp_path, renderer=None, input_loader=lambda book, chapter: prepared)
    harness.renderer = Renderer()
    first = harness.run_manifest(manifest_path, authorized_run=True)
    second = harness.run_manifest(manifest_path, authorized_run=True)
    assert first["batches"][0]["chapters"][0]["state"] == COMPLETE
    assert second["batches"][0]["chapters"][0]["skipped"] is True
    assert harness.calls == 1


def test_runner_requires_explicit_authorization(tmp_path):
    prepared = _prepared()
    manifest = build_manifest([prepared], batch_size=1, run_id="run-guard")
    path = tmp_path / "manifest.json"
    save_manifest(manifest, path)
    with pytest.raises(ManifestError, match="--authorized-run"):
        ProductionRunner(tmp_path, input_loader=lambda book, chapter: prepared).run_manifest(path)


def test_crash_reconciliation_promotes_written_raw_and_preserves_hash(tmp_path):
    prepared = _prepared()
    manifest = build_manifest([prepared], batch_size=1, run_id="run-crash")
    batch = manifest["batches"][0]
    from framework.commentary.production.manifests import batch_manifest
    batch_value = batch_manifest(manifest, batch["batch_id"])
    state_path = tmp_path / "state.json"
    state = {"state_path": str(state_path), "run_id": "run-crash", "batch_id": "batch-001", "manifest_identity": manifest["manifest_identity"], "chapters": {"Genesis 1": {"state": GENERATING, "attempt": 1}}}
    write_json(state_path, state)
    raw = tmp_path / ".bhf-data/bhf-commentary-production/v1/runs/run-crash/batches/batch-001/raw/attempt-001/genesis_001.json"
    write_json(raw, {"fixture": True})
    reconciled = reconcile_batch(tmp_path, batch_value, state)
    assert reconciled["chapters"]["Genesis 1"]["state"] == "RAW_CAPTURED"
    assert reconciled["chapters"]["Genesis 1"]["raw_sha256"]


def test_provider_failure_is_quarantined_and_separated(tmp_path):
    prepared = _prepared()
    manifest = build_manifest([prepared], batch_size=1, run_id="run-provider")
    manifest_path = tmp_path / "manifest.json"
    save_manifest(manifest, manifest_path)

    class Renderer:
        def render(self, chapter, prepared):
            raise ProviderFailure("timeout", "PROVIDER_TIMEOUT")

    runner = ProductionRunner(tmp_path, renderer=Renderer(), input_loader=lambda book, chapter: prepared)
    result = runner.run_manifest(manifest_path, authorized_run=True)
    assert result["batches"][0]["chapters"][0]["failure_kind"] == "PROVIDER_FAILURE"
    quarantine = tmp_path / ".bhf-data/bhf-commentary-production/v1/runs/run-provider/batches/batch-001/quarantine/attempt-001/genesis_001.json"
    receipt = json.loads(quarantine.read_text())
    assert receipt["generation_failure"] is True
    assert receipt["rejection_codes"] == ["PROVIDER_TIMEOUT"]


def test_input_drift_becomes_stale_instead_of_rerendering(tmp_path):
    locked = _prepared(identity="locked")
    current = _prepared(identity="current")
    manifest = build_manifest([locked], batch_size=1, run_id="run-drift")
    path = tmp_path / "manifest.json"
    save_manifest(manifest, path)
    runner = ProductionRunner(tmp_path, renderer=None, input_loader=lambda book, chapter: current)
    result = runner.run_manifest(path, authorized_run=True)
    assert result["batches"][0]["chapters"][0]["state"] == STALE_INPUT


def test_ledger_rebuild_is_deterministic_and_counts_pending(tmp_path):
    prepared = _prepared()
    manifest = build_manifest([prepared], batch_size=1, run_id="run-ledger")
    path = tmp_path / "manifest.json"
    save_manifest(manifest, path)

    class Harness(ProductionRunner):
        def _import_and_evaluate(self, manifest, batch, chapter, prepared, record, state, enable_reader):
            self._set_record(state, chapter["reference"], "VALIDATING")
            self._set_record(state, chapter["reference"], "ACCEPTED")
            self._set_record(state, chapter["reference"], "GATE_PASS")
            self._set_record(state, chapter["reference"], COMPLETE)
            self._save_state(state)
            return {"reference": chapter["reference"], "state": COMPLETE}

    class Renderer:
        def render(self, chapter, prepared):
            return RawResponse(text="{}")

    Harness(tmp_path, renderer=Renderer(), input_loader=lambda book, chapter: prepared).run_manifest(path, authorized_run=True)
    first = rebuild_ledger(tmp_path)
    second = rebuild_ledger(tmp_path)
    assert first == second
    assert first["counts"]["COMPLETE"] == 1
    assert first["counts"]["PENDING"] == 1188


def test_dense_reader_rule_preserves_philippians_restraint_and_selects_stress():
    restrained = _activation_decision(source_words=3922, source_block_count=22, source_dump_severity="NONE", source_quality_metrics={"weighted_coverage": 1.0, "synthesis_utilization": 1.0}, force_consolidation=False)
    stress = _activation_decision(source_words=2250, source_block_count=21, source_dump_severity="MODERATE", source_quality_metrics={"weighted_coverage": 1.0, "synthesis_utilization": 1.0}, force_consolidation=False)
    assert restrained["active"] is False
    assert stress["active"] is True


def test_audit_sampling_is_seed_deterministic_and_includes_failures():
    rows = [{"reference": "Genesis 1", "state": COMPLETE}, {"reference": "Numbers 33", "state": QUARANTINED}, {"reference": "Romans 8", "state": "GATE_QUALITY_FAIL"}]
    assert sample_audit_records(rows, count=2, seed="x") == sample_audit_records(rows, count=2, seed="x")
    result = sample_audit_records(rows, count=2, seed="x")
    assert {row["reference"] for row in result["chapters"]} == {"Numbers 33", "Romans 8"}
