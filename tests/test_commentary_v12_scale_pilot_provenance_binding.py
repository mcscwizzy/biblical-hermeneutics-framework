"""Focused contracts for the provenance-bound 75-chapter v1.2 scale pilot."""

import copy

import pytest

from bhf_agent.chapter_commentary.reader_provenance_binding import (
    ProvenanceBindingError,
    normalize_renderer_payload,
)
from tools import commentary_v12_scale_pilot_provenance_binding as pilot


def test_source_corpus_and_batches_are_reused_exactly():
    context = pilot.build_context()
    manifest = context["manifest"]
    source = context["source_manifest"]

    assert manifest["source_pilot"]["manifest_identity"] == source["manifest_identity"]
    assert manifest["exact_source_corpus_reused"] is True
    assert [row["reference"] for row in manifest["chapters"]] == [
        row["reference"] for row in source["chapters"]
    ]
    assert [row["batch"] for row in manifest["chapters"]] == [
        row["batch"] for row in source["chapters"]
    ]
    assert manifest["chapter_count"] == 75
    assert manifest["unseen_percentage"] == 93.33


def test_unified_contract_versions_are_frozen():
    manifest = pilot.build_context()["manifest"]

    assert manifest["prompt_version"] == "1.7"
    assert manifest["projection_version"] == "reader-level-idea-projection-v1"
    assert manifest["ancestry_envelope_version"] == "reader-level-idea-ancestry-envelope-v1"
    assert manifest["provenance_binding_version"] == "reader-provenance-binding-v1"
    assert manifest["renderer"] == "gpt-5.6-sol"
    assert manifest["renderer_effort"] == "medium"
    assert manifest["frozen_scoring_contracts"] == {
        "essential_passage_context": "essential-passage-context-v2",
        "reader_relevance_eligibility": "reader-relevance-eligibility-v1",
        "richness_clusters": "commentary-richness-clusters-v2",
        "richness_policy": "commentary-richness-policy-v3-reader-relevance",
        "gate": "commentary-richness-gate-v2.1",
    }


def test_manifest_and_all_path_bindings_are_deterministic():
    first = pilot.build_context()
    second = pilot.build_context()

    assert first["manifest"] == second["manifest"]
    assert [record["binding"] for record in first["records"]] == [
        record["binding"] for record in second["records"]
    ]
    assert all(record["binding_audit"]["valid"] for record in first["records"])


def test_unknown_paths_are_rejected_and_manual_ids_cannot_leak():
    record = pilot.build_context()["records"][0]
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
    context = pilot.build_context()
    stored = pilot._read(context["root"] / "manifest.json")
    assert stored == context["manifest"]
    pilot._verify_identity(stored, "manifest_identity", "test manifest")
    for batch, size in enumerate(pilot.BATCH_SIZES, 1):
        batch_manifest = pilot._read(
            context["root"] / f"batch-{batch:03d}" / "batch-manifest.json"
        )
        assert len(batch_manifest["chapters"]) == size
        assert batch_manifest["contract_manifest_identity"] == stored["manifest_identity"]
