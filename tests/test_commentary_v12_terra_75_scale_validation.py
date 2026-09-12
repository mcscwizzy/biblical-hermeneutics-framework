"""Deterministic checks for the frozen Terra 75-chapter validation artifact."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-terra-75-scale-validation-v1-e8af58131e066def98a2"
FROZEN_IDENTITY = "eb282a2a684e13499f56894c0f9da9c38b71c08dd5c2cf58b0a072b64b487394"


def load(name: str) -> dict:
    return json.loads((NAMESPACE / name).read_text())


def test_frozen_population_and_remaining_calculation_are_exact():
    manifest = load("manifest.json")
    frozen = load("frozen-population.json")
    remaining = load("remaining-50-selection.json")
    prior = set(load("prior-25-output-index.json")["references"])
    assert manifest["frozen_population_identity"] == FROZEN_IDENTITY
    assert frozen["identity"] == FROZEN_IDENTITY
    assert len(frozen["references"]) == 75
    assert len(set(frozen["references"])) == 75
    assert len(remaining["references"]) == 50
    remaining_refs = {row["reference"] for row in remaining["references"]}
    assert remaining_refs == set(frozen["references"]) - prior
    assert len(prior) == 25


def test_protected_contracts_and_source_files_are_unchanged():
    start = load("starting-state.json")
    freeze = load("contract-freeze.json")
    assert start["frozen_population_identity"] == FROZEN_IDENTITY
    assert start["protected_contract_hashes"] == freeze["protected_contract_hashes"]
    assert load("final-report-v2.json")["protected_contracts_unchanged"] is True
    assert load("final-report-v2.json")["ckl_unchanged"] is True
    assert load("final-report-v2.json")["asv_unchanged"] is True


def test_psalm_safe_text_and_sol_missing_control_are_preserved():
    safe = load("safe-psalm-text/records.json")
    assert sorted(r["reference"] for r in safe["records"]) == ["Psalms 122", "Psalms 137", "Psalms 2", "Psalms 22", "Psalms 8"]
    assert safe["dataset_mutated"] is False
    sol = load("sol-comparison-status.json")
    assert sol["status"] == "4_OF_5_COMPLETE_COMPARISON_PENDING"
    assert sol["missing_control"] == "Psalms 2"
    assert sol["no_retry"] is True
    assert sol["no_substitution"] is True


def test_aggregate_and_failure_classification_are_bounded():
    report = load("final-report-v2.json")
    assert report["population_size"] == 75
    assert report["prior_terra_generations_reused"] == 25
    assert report["new_terra_generations_attempted"] == 42
    assert report["new_terra_generations_completed"] == 42
    assert report["terra_completed"] == 67
    assert report["not_renderable_count"] == 8
    assert report["validation"]["retry_count"] == 0
    assert report["validation"]["high_dumps"] == 0
    assert set(report["failure_classification_totals"]) <= {"PASS", "SOURCE_LIMITED", "NOT_RENDERABLE_SOURCE_LIMITED", "STRUCTURAL_MODEL_FAILURE", "PROVENANCE_FAILURE", "ANCESTRY_FAILURE", "REFERENCE_FAILURE", "UNDER_EXPLANATION", "READABILITY_FAILURE", "EVIDENCE_SELECTION_FAILURE", "UNSUPPORTED_CLAIM", "CANONICAL_TEXT_ISSUE", "MODEL_PROVIDER_FAILURE", "OTHER"}


def test_human_sample_and_backlog_are_reproducible_and_complete():
    sample = load("human-review-sample-final.json")
    assert sample["sample_size"] == 10
    assert len({row["report_category"] for row in sample["chapters"]}) >= 5
    enriched = {"Genesis 5", "Psalms 2", "Psalms 19", "Psalms 103", "2 Kings 4"}
    assert len(enriched & {row["reference"] for row in sample["chapters"]}) >= 2
    backlog = load("content-enrichment-backlog.json")["chapters"]
    assert [row["priority"] for row in backlog] == sorted(row["priority"] for row in backlog)
    assert all(row["failure_classification"] != "PASS" for row in backlog)


def test_final_artifact_checksums_match():
    payload = load("checksums-v2.json")
    for relative, expected in payload["files"].items():
        assert hashlib.sha256((NAMESPACE / relative).read_bytes()).hexdigest() == expected
