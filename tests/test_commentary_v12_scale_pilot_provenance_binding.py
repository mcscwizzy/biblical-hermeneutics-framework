"""Focused contracts for the provenance-bound 75-chapter v1.2 scale pilot."""

import copy
import json
from pathlib import Path

import pytest

from bhf_agent.chapter_commentary.reader_provenance_binding import (
    ProvenanceBindingError,
    normalize_renderer_payload,
)
from tools import commentary_v12_scale_pilot_provenance_binding as pilot
from framework.commentary.v12_current_lineage import CURRENT_LINEAGE_REL, load_manifest, record_context


ROOT = Path(__file__).resolve().parents[1]
CURRENT_ROOT = ROOT / CURRENT_LINEAGE_REL
HISTORICAL_SCALE_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-scale-pilot-922472547555015a3ced"


def _current_context() -> tuple[dict, list[dict]]:
    manifest = load_manifest(ROOT)
    records = [record_context(ROOT, "scale_pilot", row["reference"])
               for row in manifest["scale_pilot"]["chapters"]]
    return manifest, records


def test_source_corpus_and_batches_are_reused_exactly():
    manifest, _ = _current_context()
    source = json.loads((HISTORICAL_SCALE_ROOT / "manifest.json").read_text())
    current = manifest["scale_pilot"]

    assert manifest["supersedes"]["scale_pilot_manifest_identity"] == source["manifest_identity"]
    assert [row["reference"] for row in current["chapters"]] == [
        row["reference"] for row in source["chapters"]
    ]
    assert [row["batch"] for row in current["chapters"]] == [
        row["batch"] for row in source["chapters"]
    ]
    assert current["chapter_count"] == 75
    assert source["unseen_percentage"] == 93.33


def test_unified_contract_versions_are_frozen():
    manifest = load_manifest(ROOT)["contracts"]

    assert manifest["prompt_version"] == "1.7"
    assert manifest["projection_version"] == "reader-level-idea-projection-v1"
    assert manifest["ancestry_envelope_version"] == "reader-level-idea-ancestry-envelope-v1"
    assert manifest["provenance_binding_version"] == "reader-provenance-binding-v1"
    assert manifest["frozen_scoring_contracts"] == {
        "essential_passage_context": "essential-passage-context-v2",
        "reader_relevance_eligibility": "reader-relevance-eligibility-v1",
        "richness_clusters": "commentary-richness-clusters-v2",
        "richness_policy": "commentary-richness-policy-v3-reader-relevance",
        "gate": "commentary-richness-gate-v2.1",
    }


def test_manifest_and_all_path_bindings_are_deterministic():
    first, first_records = _current_context()
    second, second_records = _current_context()

    assert first == second
    assert [record["binding"] for record in first_records] == [
        record["binding"] for record in second_records]
    assert all(record["binding_audit"]["valid"] for record in first_records)


def test_unknown_paths_are_rejected_and_manual_ids_cannot_leak():
    record = record_context(ROOT, "scale_pilot", "Romans 3")
    binding = record["binding"]
    path_id = binding["paths"][0]["path_id"]
    payload = {
        "reference": record["row"]["reference"],
        "book": record["row"]["book"],
        "chapter": record["row"]["chapter"],
        "status": "pending",
        "sections": [
            {
                "kind": "historical_context",
                "title": "Context",
                "blocks": [
                    {
                        "id": "block_1",
                        "text": "Supported prose.",
                        "provenance_refs": [path_id],
                        "synthesis_ids": ["invented"],
                        "evidence_ids": ["invented"],
                    }
                ],
            }
        ],
    }
    normalized, _ = normalize_renderer_payload(payload, binding)
    selected = binding["paths"][0]
    block = normalized["sections"][0]["blocks"][0]

    assert block["synthesis_ids"] == [selected["synthesis_id"]]
    assert block["evidence_ids"] == selected["evidence_ids"]
    bad = copy.deepcopy(payload)
    bad["sections"][0]["blocks"][0]["provenance_refs"] = [
        path_id[:-24] + "0" * 24
    ]
    with pytest.raises(ProvenanceBindingError, match="UNKNOWN_PROVENANCE_PATH"):
        normalize_renderer_payload(bad, binding)


def test_aggregate_and_quarantine_classification_are_deterministic():
    row = {
        "reference": "Example 1",
        "structural_validity": True,
        "provenance_path_validity": True,
        "hard_provenance_errors": [],
        "ancestry_mismatch_count": 0,
        "dump_severity": "NONE",
        "readability_result": "PASS",
        "checklist_behavior": "PASS",
        "core_coverage": 1.0,
        "category_coverage": 1.0,
        "gate_result": "FAIL",
        "weighted_coverage": 0.6,
        "eligible_idea_utilization": 0.5,
        "projected_concepts_represented": 0,
        "projected_idea_count": 1,
        "prose_word_count": 100,
    }
    assert pilot._classification(row) == "RICHNESS_SHORTFALL"
    row["final_chapter_classification"] = pilot._classification(row)
    summary = pilot._summary([row])
    assert summary["provenance_path_valid_percentage"] == 100.0
    assert summary["genuine_renderer_failure_rate"] == 100.0


def test_prepared_batch_manifests_and_checksums_reproduce():
    manifest, records = _current_context()
    rows = manifest["scale_pilot"]["chapters"]

    for batch, size in enumerate(pilot.BATCH_SIZES, 1):
        batch_rows = [row for row in rows if row["batch"] == batch]
        assert len(batch_rows) == size
        for record in (item for item in records if item["row"]["batch"] == batch):
            assert record["receipt"] == record["row"]
            assert record["root"].is_relative_to(CURRENT_ROOT)
