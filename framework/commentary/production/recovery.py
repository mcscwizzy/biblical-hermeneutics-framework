"""Crash reconciliation for production batch state and immutable artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    BLOCKED,
    COMPLETE,
    GATE_PASS,
    GATE_QUALITY_FAIL,
    GATE_WARNING,
    GENERATING,
    PENDING,
    QUARANTINED,
    RAW_CAPTURED,
    STALE_INPUT,
    VALIDATING,
    read_json,
    sha256_bytes,
    transition,
    write_json,
)


def _path(repo_root: Path, relative: str) -> Path:
    return repo_root / ".bhf-data" / "bhf-commentary-production" / "v1" / relative


def reconcile_chapter(repo_root: Path, chapter: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """Prefer evidence of a written artifact over an interrupted duplicate status."""

    state = str(record.get("state", PENDING))
    expected = chapter.get("expected_artifacts", {})
    raw = _path(repo_root, expected["raw"])
    accepted = _path(repo_root, expected["accepted"])
    gate = _path(repo_root, expected["gate"])
    quarantine = _path(repo_root, expected["quarantine"])
    if raw.is_file():
        digest = sha256_bytes(raw.read_bytes())
        recorded = record.get("raw_sha256")
        if recorded and recorded != digest:
            record["state"] = BLOCKED
            record["recovery_error"] = "raw artifact hash disagrees with state"
            return record
        record["raw_sha256"] = digest
        if state in {PENDING, "READY", GENERATING}:
            state = RAW_CAPTURED
    if quarantine.is_file():
        record["state"] = QUARANTINED
        return record
    if accepted.is_file() and gate.is_file():
        gate_value = read_json(gate)
        outcome = str(gate_value.get("assessment", {}).get("outcome", ""))
        state = {"PASS": GATE_PASS, "PASS_WITH_WARNING": GATE_WARNING, "QUALITY_FAIL": GATE_QUALITY_FAIL}.get(outcome, state)
        if state in {GATE_PASS, GATE_WARNING}:
            state = COMPLETE
    elif accepted.is_file() and state not in {COMPLETE, GATE_QUALITY_FAIL}:
        # An accepted artifact without its Gate receipt is recoverable only
        # through the still-required raw/import path.  If raw disappeared,
        # leave the chapter blocked rather than trusting a partial duplicate.
        state = RAW_CAPTURED if raw.is_file() else BLOCKED
    elif state == GENERATING and not raw.is_file():
        state = PENDING
        record["recovered_from_interrupted_generation"] = True
    record["state"] = state
    return record


def reconcile_batch(repo_root: Path, manifest: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    for chapter in manifest.get("chapters", []):
        reference = chapter["reference"]
        state.setdefault("chapters", {}).setdefault(reference, {"state": PENDING, "attempt": 0})
        state["chapters"][reference] = reconcile_chapter(repo_root, chapter, state["chapters"][reference])
    write_json(Path(state["state_path"]), state)
    return state
