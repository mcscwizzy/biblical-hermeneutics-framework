from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from tools.validate_ne9c_current_compatibility import (
    validate_current_compatibility,
)
from scripts.ne9c_bulk_curation import validate_inventory


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _copy_protected_inputs(root: Path) -> None:
    relative_files = (
        "docs/narrative-explorer/ne9c-bulk-curation/checkpoint.json",
        "docs/narrative-explorer/ne9c-bulk-curation/decisions.jsonl",
        "framework/canonical_library/curations/narrative-explorer/ne10/passage-bridges.json",
        "framework/canonical_library/curations/narrative-explorer/ne10/research-candidates-held.json",
    )
    for relative in relative_files:
        source = REPOSITORY_ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    source_tree = (
        REPOSITORY_ROOT
        / "framework/canonical_library/curations/narrative-explorer/ne9c"
    )
    shutil.copytree(source_tree, root / source_tree.relative_to(REPOSITORY_ROOT))


def test_current_compatibility_passes_after_ckl_evidence_updates_without_refreshing_history():
    protected_checkpoint = (
        REPOSITORY_ROOT
        / "docs/narrative-explorer/ne9c-bulk-curation/checkpoint.json"
    )
    checkpoint_before = hashlib.sha256(protected_checkpoint.read_bytes()).hexdigest()

    report = validate_current_compatibility(REPOSITORY_ROOT)

    assert report["validation_status"] == "passed"
    assert report["historical_ckl_fingerprint_matches"] is False
    assert report["authored_relationship_count"] == 4061
    assert report["reviewed_relationship_count"] == 3925
    assert report["disposition_counts"] == {
        "curated": 408,
        "excluded": 1622,
        "held": 1895,
    }
    assert report["verified_bridge_count"] == 44
    assert report["held_candidate_count"] == 7
    assert hashlib.sha256(protected_checkpoint.read_bytes()).hexdigest() == checkpoint_before


def test_current_compatibility_rejects_a_changed_decision_ledger(tmp_path: Path):
    _copy_protected_inputs(tmp_path)
    target = tmp_path / "docs/narrative-explorer/ne9c-bulk-curation/decisions.jsonl"
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="protected artifact hash changed: decisions.jsonl"):
        validate_current_compatibility(tmp_path)


def test_current_compatibility_rejects_a_changed_held_candidate_registry(tmp_path: Path):
    _copy_protected_inputs(tmp_path)
    source = REPOSITORY_ROOT / "framework/canonical_library/curations/narrative-explorer/ne10"
    target = tmp_path / "framework/canonical_library/curations/narrative-explorer/ne10"
    target.mkdir(parents=True, exist_ok=True)
    held = json.loads((source / "research-candidates-held.json").read_text(encoding="utf-8"))
    held["candidates"].pop()
    (target / "research-candidates-held.json").write_text(
        json.dumps(held), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="protected artifact hash changed: research-candidates-held.json"):
        validate_current_compatibility(tmp_path)


def test_historical_validator_still_rejects_the_modern_ckl_without_refreshing_checkpoint(tmp_path: Path):
    source_state = REPOSITORY_ROOT / "docs/narrative-explorer/ne9c-bulk-curation"
    state_copy = tmp_path / "ne9c-bulk-curation"
    shutil.copytree(source_state, state_copy)
    checkpoint = source_state / "checkpoint.json"
    before = hashlib.sha256(checkpoint.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="protected CKL source fingerprint changed"):
        validate_inventory(REPOSITORY_ROOT, state_copy)

    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == before
