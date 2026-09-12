"""Deterministic contracts for the bounded v1.2 Terra scale pilot."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from tools.commentary_v12_terra_scale_pilot import (
    CATEGORY_TARGETS,
    FROZEN_POPULATION_IDENTITY,
    REQUIRED_CONTROLS,
    blind_payload,
    classify_failure,
    protected_hashes,
    select_sample,
)


ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = next(
    path
    for path in sorted(ROOT.glob(".bhf-data/bhf-commentary-candidates/commentary-v1.2-terra-scale-pilot-v1-*"))
    if "thin_renderable_population_count" in json.loads((path / "manifest.json").read_text())
)


def _manifest() -> dict:
    return json.loads((NAMESPACE / "manifest.json").read_text())


def _preflight() -> dict:
    return json.loads((NAMESPACE / "preflight/all-candidate-results.json").read_text())


def test_sample_is_reproducible_and_drawn_only_from_frozen_population():
    manifest = _manifest()
    preflight = _preflight()
    selected, replacements = select_sample(preflight["chapters"])
    assert replacements == manifest["replacements"]
    assert [row["reference"] for row in selected] == [row["reference"] for row in manifest["chapters"]]
    frozen = set(json.loads((NAMESPACE / "frozen-population.json").read_text())["references"])
    assert set(row["reference"] for row in selected) <= frozen
    assert len(selected) == 25


def test_required_controls_and_category_stratification_are_frozen():
    manifest = _manifest()
    refs = {row["reference"] for row in manifest["chapters"]}
    assert set(REQUIRED_CONTROLS) <= refs
    assert Counter(row["category"] for row in manifest["chapters"]) == Counter(CATEGORY_TARGETS)
    assert manifest["thin_renderable_selected_count"] == manifest["thin_renderable_population_count"]


def test_renderer_eligibility_preflight_and_control_input_hashes():
    manifest = _manifest()
    assert all(row["eligible"] for row in manifest["chapters"])
    controls = [row for row in manifest["chapters"] if row["reference"] in REQUIRED_CONTROLS]
    assert len({row["renderer_input_sha256"] for row in controls}) == 5
    assert manifest["terra"]["model"] == "gpt-5.6-terra"
    assert manifest["terra"]["effort"] == "high"
    assert manifest["sol"]["model"] == "gpt-5.6-sol"
    assert manifest["sol"]["effort"] == "medium"


def test_population_identity_and_contracts_are_unchanged():
    manifest = _manifest()
    assert manifest["frozen_population_identity"] == FROZEN_POPULATION_IDENTITY
    starting = json.loads((NAMESPACE / "starting-state.json").read_text())
    assert protected_hashes() == starting["protected_contract_hashes"]
    assert starting["frozen_population_identity"] == FROZEN_POPULATION_IDENTITY
    assert manifest["ckl_mutation"] is False
    assert manifest["asv_mutation"] is False


def test_failure_classification_schema_is_bounded():
    assert classify_failure({"structural_result": "REJECTED", "rejection_codes": []}, {}, {}, []) == "STRUCTURAL_MODEL_FAILURE"
    assert classify_failure({"structural_result": "REJECTED", "rejection_codes": ["UNKNOWN_EVIDENCE_ID"]}, {}, {}, []) == "UNSUPPORTED_CLAIM"
    assert classify_failure({"structural_result": "ACCEPTED", "provenance_result": "FAIL", "ancestry_result": "PASS"}, {}, {}, []) == "PROVENANCE_FAILURE"
    assert classify_failure({"structural_result": "ACCEPTED", "provenance_result": "PASS", "ancestry_result": "PASS", "gate_result": "FAIL"}, {"current_availability": "THIN"}, {"readability": "PASS", "under_explanation": "FAIL"}, []) == "SOURCE_LIMITED"


def test_blind_comparison_masks_model_and_machine_identity():
    source = {"generated_metadata": {"model": "gpt-5.6-terra"}, "sections": [{"blocks": [{"synthesis_ids": ["syn"], "evidence_ids": ["ev"], "provenance_refs": ["path"], "text": "Reader-facing prose."}]}]}
    masked = blind_payload(source)
    assert "generated_metadata" not in masked
    assert masked["sections"][0]["blocks"][0] == {"text": "Reader-facing prose."}
    assert source["sections"][0]["blocks"][0]["synthesis_ids"] == ["syn"]


def test_pre_generation_checksum_integrity():
    payload = json.loads((NAMESPACE / "checksums-pre-generation.json").read_text())
    for relative, expected in payload["files"].items():
        assert hashlib.sha256((NAMESPACE / relative).read_bytes()).hexdigest() == expected
