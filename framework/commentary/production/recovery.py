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
    sha256_json,
    sha256_bytes,
    slug,
    transition,
    write_json,
)
from bhf_agent.chapter_commentary.selection_sufficiency import (
    RENDERER_SELECTION_COLLAPSE,
    SELECTION_SUFFICIENCY_VERSION,
    validate_selection_assessment,
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
    selection_relative = expected.get("selection_assessment") or (
        f"runs/{chapter.get('run_id', record.get('run_id'))}/"
        f"batches/{chapter.get('batch_id', record.get('batch_id'))}/"
        "selection-assessments/attempt-001/"
        f"{slug(chapter['book'], int(chapter['chapter']))}.json"
    )
    selection_path = _path(repo_root, selection_relative)
    if raw.is_file():
        digest = sha256_bytes(raw.read_bytes())
        recorded = record.get("raw_sha256")
        if recorded and recorded != digest:
            record["state"] = BLOCKED
            record["recovery_error"] = "raw artifact hash disagrees with state"
            return record
        record["raw_sha256"] = digest
        record["raw_path"] = expected["raw"]
        if not int(record.get("attempt", 0)):
            # The expected raw directory is attempt-001 in production v1.
            # Recovering a written artifact must not create a new attempt.
            record["attempt"] = 1
        if state in {PENDING, "READY", GENERATING}:
            state = RAW_CAPTURED
    if selection_path is not None and selection_path.is_file() and not accepted.is_file():
        selection_value = read_json(selection_path)
        selection_assessment = selection_value.get("selection_sufficiency", {})
        input_identity = chapter.get("input_identity", {})
        valid_assessment = validate_selection_assessment(
            selection_assessment,
            {
                "reference": chapter.get("reference"),
                "evidence_hash": input_identity.get("evidence_hash"),
                "synthesis_hash": input_identity.get("synthesis_hash"),
                "prompt_version": input_identity.get("prompt_version"),
                "commentary_schema_version": input_identity.get("commentary_schema_version"),
                "raw_response_sha256": record.get("raw_sha256"),
            },
        )
        if (
            selection_value.get("artifact_version")
            != f"{SELECTION_SUFFICIENCY_VERSION}-receipt-v1"
            or selection_value.get("reference") != chapter.get("reference")
            or selection_value.get("input_identity") != input_identity
            or not valid_assessment["valid"]
        ):
            record["state"] = QUARANTINED
            record["selection_sufficiency_status"] = "ASSESSMENT_UNAVAILABLE"
            record["recovery_error"] = (
                "RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE: selection receipt identity "
                "or assessment hash is invalid"
            )
            record["production_disposition"] = "PRODUCTION_QUARANTINED_SELECTION"
            return record
        record["selection_assessment_path"] = selection_relative
        record["selection_sufficiency_status"] = valid_assessment["status"]
        if valid_assessment["status"] != "PASS":
            if (
                valid_assessment["status"] == "FAIL"
                and selection_assessment.get("diagnostic_code") == RENDERER_SELECTION_COLLAPSE
            ):
                record["state"] = GATE_QUALITY_FAIL
            else:
                record["state"] = QUARANTINED
            record["production_disposition"] = "PRODUCTION_QUARANTINED_SELECTION"
            record["recovery_error"] = (
                selection_assessment.get("diagnostic_code")
                or "RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE"
            )
            return record
    if accepted.is_file() and gate.is_file():
        gate_value = read_json(gate)
        if not selection_path.is_file():
            record["state"] = QUARANTINED
            record["selection_sufficiency_status"] = "ASSESSMENT_UNAVAILABLE"
            record["recovery_error"] = (
                "RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE: accepted output has no "
                "selection assessment receipt"
            )
            record["production_disposition"] = "PRODUCTION_QUARANTINED_SELECTION"
            return record
        selection_value = read_json(selection_path)
        selection_assessment = selection_value.get("selection_sufficiency", {})
        selection_status = selection_assessment.get("status")
        input_identity = chapter.get("input_identity", {})
        accepted_payload = read_json(accepted)
        valid_assessment = validate_selection_assessment(
            selection_assessment,
            {
                "reference": chapter.get("reference"),
                "evidence_hash": input_identity.get("evidence_hash"),
                "synthesis_hash": input_identity.get("synthesis_hash"),
                "prompt_version": input_identity.get("prompt_version"),
                "commentary_schema_version": input_identity.get("commentary_schema_version"),
                "commentary_sha256": sha256_json(accepted_payload),
                "raw_response_sha256": record.get("raw_sha256"),
            },
        )
        if (
            selection_value.get("artifact_version")
            != f"{SELECTION_SUFFICIENCY_VERSION}-receipt-v1"
            or selection_value.get("reference") != chapter.get("reference")
            or selection_value.get("input_identity") != input_identity
            or not valid_assessment["valid"]
        ):
            selection_status = "ASSESSMENT_UNAVAILABLE"
            record["recovery_error"] = (
                "RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE: selection receipt identity "
                "does not match the locked production input"
            )
        record["selection_assessment_path"] = selection_relative
        record["selection_sufficiency_status"] = valid_assessment["status"] if selection_status != "ASSESSMENT_UNAVAILABLE" else selection_status
        if selection_status != "PASS":
            if selection_status == "FAIL" and selection_assessment.get("diagnostic_code") == RENDERER_SELECTION_COLLAPSE:
                record["state"] = GATE_QUALITY_FAIL
                record["production_disposition"] = "PRODUCTION_QUARANTINED_SELECTION"
            else:
                record["state"] = QUARANTINED
                record["production_disposition"] = "PRODUCTION_QUARANTINED_SELECTION"
            record.setdefault(
                "recovery_error",
                "RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE: selection gate did not pass",
            )
            return record
        outcome = str(gate_value.get("assessment", {}).get("outcome", ""))
        state = {"PASS": GATE_PASS, "PASS_WITH_WARNING": GATE_WARNING, "QUALITY_FAIL": GATE_QUALITY_FAIL}.get(outcome, state)
        # QUALITY_FAIL is intentionally both structurally accepted and
        # production-quarantined.  Its quarantine receipt must not erase the
        # richer state during crash recovery or ledger reconstruction.
        if state == GATE_QUALITY_FAIL:
            record["state"] = state
            record["production_disposition"] = "PRODUCTION_QUARANTINED_QUALITY"
            return record
        if state in {GATE_PASS, GATE_WARNING}:
            state = COMPLETE
    if quarantine.is_file():
        record["state"] = QUARANTINED
        record["production_disposition"] = "PRODUCTION_QUARANTINED_CONTENT"
        return record
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
