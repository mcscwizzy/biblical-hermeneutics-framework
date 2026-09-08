"""Deterministic audit selection for later human or AI review."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any, Iterable


def _rank(seed: str, reference: str) -> str:
    return hashlib.sha256(f"{seed}:{reference}".encode("utf-8")).hexdigest()


def sample_audit_records(records: Iterable[dict[str, Any]], *, count: int = 25, seed: str = "20260908") -> dict[str, Any]:
    if count <= 0:
        raise ValueError("audit sample count must be positive")
    rows = sorted((dict(row) for row in records), key=lambda row: str(row.get("reference", "")))
    mandatory: list[dict[str, Any]] = []
    optional: list[dict[str, Any]] = []
    for row in rows:
        state = str(row.get("state", ""))
        gate = str(row.get("gate_status", row.get("gate_outcome", "")))
        availability = str(row.get("evidence_availability", ""))
        if state in {"QUARANTINED", "GATE_QUALITY_FAIL"} or gate in {"PASS_WITH_WARNING", "QUALITY_FAIL", "SAFETY_FAIL"} or availability in {"THIN", "DATA_GAP"} or row.get("reader_status") in {"ELIGIBLE", "FAILED"}:
            mandatory.append(row)
        else:
            optional.append(row)
    mandatory = sorted(mandatory, key=lambda row: _rank(seed, str(row.get("reference", ""))))
    optional = sorted(optional, key=lambda row: _rank(seed, str(row.get("reference", ""))))
    selected = mandatory + optional
    if len(selected) > count:
        selected = selected[:count] if len(mandatory) <= count else mandatory
    return {
        "artifact_version": "commentary-production-audit-sample-v1",
        "seed": seed,
        "requested_count": count,
        "actual_count": len(selected),
        "mandatory_overflow": len(mandatory) > count,
        "selection_policy": "include rejects, quality failures, warnings, thin/data-gap, and reader failures/eligibility; fill by SHA-256 seed rank",
        "chapters": selected,
    }
