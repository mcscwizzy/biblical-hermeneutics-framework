"""Tests for deterministic NE-9C relationship inventory and review state."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.ne9c_bulk_curation import (
    build_authored_object_relationships,
    initialize_inventory,
    partition_relationship_waves,
    record_decisions,
    validate_disposition_decision,
)


def test_inventory_counts_authored_object_edges_once_and_keeps_exact_direction_metadata():
    objects = [
        {
            "id": "source-event",
            "type": "event",
            "title": "Source event",
            "related_objects": [{
                "id": "target-theme",
                "relationship": "thematic-link",
                "notes": "An authored note.",
                "weight": 7,
            }],
            "evidence_items": [{"related_evidence": [{"id": "ignored", "relationship": "evidence-link"}]}],
        },
        {
            "id": "target-theme",
            "type": "theme",
            "title": "Target theme",
            "related_objects": [{
                "id": "source-event",
                "relationship": "thematic-link",
                "notes": "Reverse authored separately.",
                "weight": 6,
            }],
        },
    ]

    relationships = build_authored_object_relationships(objects)

    assert len(relationships) == 2
    forward = next(item for item in relationships if item["source_id"] == "ckl:source-event")
    assert forward["target_id"] == "ckl:target-theme"
    assert forward["original_relationship_type"] == "thematic-link"
    assert forward["original_notes"] == "An authored note."
    assert forward["original_weight"] == 7
    assert forward["authored_direction"] == "reciprocal"
    assert forward["relationship_kind"] == "object"


def test_wave_partition_is_deterministic_and_uses_exactly_500_unique_edges():
    relationships = [
        {"edge_id": f"edge-{index:04d}", "priority_score": index % 4, "topic_cluster": "creation"}
        for index in range(1001)
    ]

    first = partition_relationship_waves(relationships)
    second = partition_relationship_waves(list(reversed(relationships)))

    assert [len(wave) for wave in first] == [500, 500, 1]
    assert first == second
    assert len({edge["edge_id"] for wave in first for edge in wave}) == 1001


def test_disposition_validation_requires_reasons_and_identity_matched_curation():
    edge = {
        "edge_id": "edge-a",
        "relationship_kind": "object",
        "source_id": "ckl:source",
        "target_id": "ckl:target",
        "original_relationship_type": "label",
        "original_notes": "note",
        "original_weight": 5,
        "authored_direction": "one_way",
    }

    with pytest.raises(ValueError, match="reason"):
        validate_disposition_decision(edge, {"disposition": "held", "reason": ""})
    with pytest.raises(ValueError, match="exact authored identity"):
        validate_disposition_decision(edge, {
            "disposition": "curated",
            "reason": "Passage and CKL sources substantiate the route.",
            "research_notes": "Reviewed the passage and source basis.",
            "curation": {"relationship_kind": "object"},
        })


def test_cli_inventory_can_import_repository_packages_when_run_by_script_path(tmp_path):
    repository = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable, "scripts/ne9c_bulk_curation.py",
            "--source-root", str(repository), "--state-dir", str(tmp_path / "state"), "inventory",
        ],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    inventory = json.loads(result.stdout)
    assert inventory["inventory_relationship_count"] == 4061
    assert inventory["wave_size"] == 500
    assert inventory["backlog_relationship_count"] == sum(
        manifest["relationship_count"] for manifest in inventory["waves"]
    )


def test_batch_decisions_are_idempotent_and_reject_conflicts_without_partial_writes(tmp_path):
    repository = Path(__file__).resolve().parents[1]
    state_dir = tmp_path / "state"
    initialize_inventory(repository, state_dir)
    first_wave = state_dir / "waves/wave-0001.jsonl"
    edges = [json.loads(line) for line in first_wave.read_text(encoding="utf-8").splitlines()[:2]]
    submissions = [
        {
            "edge_id": edge["edge_id"],
            "decision": {
                "disposition": "held",
                "reason": f"Passage-level basis remains unresolved for {edge['source_id']}.",
                "research_notes": "Reviewed owner records and checked for edge-specific passage support.",
            },
        }
        for edge in edges
    ]

    first = record_decisions(repository, state_dir, submissions)
    recorded_bytes = (state_dir / "decisions.jsonl").read_bytes()
    replay = record_decisions(repository, state_dir, submissions)
    assert first["reviewed_relationship_count"] == replay["reviewed_relationship_count"] == 2
    assert (state_dir / "decisions.jsonl").read_bytes() == recorded_bytes

    conflicting = [dict(submissions[0]), submissions[1]]
    conflicting[0] = {
        **submissions[0],
        "decision": {
            **submissions[0]["decision"],
            "reason": "A conflicting disposition must not overwrite the recorded review.",
        },
    }
    with pytest.raises(ValueError, match="conflicting disposition"):
        record_decisions(repository, state_dir, conflicting)
    assert (state_dir / "decisions.jsonl").read_bytes() == recorded_bytes
