"""Corpus-level quarantine recovery state for Commentary v1.1.

Recovery authorization is durable corpus state.  This module derives one
ledger from the reviewed adjudication artifacts and the append-only scaled
quarantine reports, then validates that ledger before candidate selection can
consume it.  It never changes CKL or evidence content.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping


LEDGER_SCHEMA_VERSION = "commentary-v1.1-quarantine-recovery-ledger-v1"
RECOVERABLE = "RECOVERABLE"
KNOWN_ADJUDICATIONS = {
    RECOVERABLE,
    "UNADJUDICATED",
    "STILL_QUARANTINED",
    "DATA_GAP",
    "REQUIRES_CKL_REMEDIATION",
    "PERMANENTLY_EXCLUDED",
}

LEDGER_RELATIVE_PATH = Path(
    ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/quarantine-recovery-ledger.json"
)
BASE_ADJUDICATION_RELATIVE_PATH = Path(
    ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/ckl-scope-audit/post-remediation-recovery-adjudication.json"
)
FINAL_FOUR_ADJUDICATION_RELATIVE_PATH = Path(
    ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/ckl-scope-audit/post-final-four-quarantine-adjudication.json"
)


class RecoveryLedgerError(ValueError):
    """The recovery ledger or one of its authoritative sources is unsafe."""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RecoveryLedgerError(f"recovery source artifact is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryLedgerError(f"recovery source artifact cannot be read: {path}") from exc


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise RecoveryLedgerError(f"recovery source artifact cannot be hashed: {path}") from exc


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _resolve_source(path_value: str, repo_root: Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else repo_root / path


def _canonical_identity(reference: str) -> dict[str, Any]:
    try:
        book, chapter_text = reference.rsplit(" ", 1)
        chapter = int(chapter_text)
    except (ValueError, TypeError) as exc:
        raise RecoveryLedgerError(f"invalid canonical chapter reference: {reference!r}") from exc
    if not book.strip() or chapter < 1:
        raise RecoveryLedgerError(f"invalid canonical chapter reference: {reference!r}")
    return {"reference": reference, "book": book, "chapter": chapter}


def _historical_rows(scale_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(scale_root.glob("batch-*/quarantine-report.json")):
        data = _read_json(path)
        for row in data.get("chapters", []):
            if not row.get("reference"):
                continue
            item = dict(row)
            item["source_batch"] = path.parent.name
            rows.append(item)
    return rows


def _historical_by_reference(scale_root: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _historical_rows(scale_root):
        grouped[str(row["reference"])].append(row)
    return dict(grouped)


def _finalized_by_reference(scale_root: Path) -> dict[str, tuple[str, str | None, bool, bool]]:
    finalized: dict[str, tuple[str, str | None, bool, bool]] = {}
    for path in sorted(scale_root.glob("batch-*/batch-manifest.json")):
        data = _read_json(path)
        batch = path.parent.name
        created_at = data.get("created_at")
        locked = data.get("status") == "LOCKED"
        generated = any((path.parent / "terra" / "chapters").glob("*.json"))
        for value in data.get("final_references") or []:
            reference = str(value)
            finalized.setdefault(reference, (batch, created_at, locked, generated))
    return finalized


def _source_descriptor(path: Path, role: str, repo_root: Path) -> dict[str, Any]:
    return {
        "path": _repo_relative(path, repo_root),
        "sha256": _sha256(path),
        "role": role,
    }


def _ledger_hash_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "ledger_sha256"}


def _ledger_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(_ledger_hash_payload(payload)).encode("utf-8")).hexdigest()


def _source_evidence(chapter: Mapping[str, Any]) -> dict[str, Any]:
    current = chapter.get("current_preflight") or {}
    return {
        "evidence_ids": list(current.get("evidence_ids") or []),
        "evidence_hash": current.get("evidence_hash"),
        "json_sqlite_agreement": current.get("json_sqlite_agreement") or {},
    }


def build_recovery_ledger(
    scale_root: Path,
    output: Path,
    *,
    repo_root: Path | None = None,
    base_adjudication: Path | None = None,
    final_four_adjudication: Path | None = None,
) -> dict[str, Any]:
    """Build the durable ledger from the authoritative reviewed artifacts.

    The base adjudication contains the complete 257-reference inventory.  The
    final-four artifact is a later adjudication of exactly the four references
    that remained blocked in that base report; it is an explicit overlay, not
    an inferred allowlist.
    """

    scale_root = scale_root.resolve()
    repo_root = (repo_root or scale_root.parents[2]).resolve()
    base_path = (base_adjudication or (repo_root / BASE_ADJUDICATION_RELATIVE_PATH)).resolve()
    final_four_path = (final_four_adjudication or (repo_root / FINAL_FOUR_ADJUDICATION_RELATIVE_PATH)).resolve()
    historical = _historical_by_reference(scale_root)
    if not historical:
        raise RecoveryLedgerError("no historical quarantine reports were found")
    base = _read_json(base_path)
    final_four = _read_json(final_four_path)
    base_chapters = {str(row.get("reference")): row for row in base.get("chapters", []) if row.get("reference")}
    if len(base_chapters) != len(base.get("chapters", [])):
        raise RecoveryLedgerError("base recovery adjudication contains duplicate or missing identities")
    historical_refs = set(historical)
    if set(base_chapters) != historical_refs:
        missing = sorted(historical_refs - set(base_chapters))
        extra = sorted(set(base_chapters) - historical_refs)
        raise RecoveryLedgerError(f"base recovery adjudication identity mismatch: missing={missing}, extra={extra}")

    final_four_rows = {str(row.get("reference")): row for row in final_four.get("chapters", []) if row.get("reference")}
    if len(final_four_rows) != len(final_four.get("chapters", [])):
        raise RecoveryLedgerError("final-four adjudication contains duplicate or missing identities")
    base_still_quarantined = {
        reference for reference, row in base_chapters.items()
        if row.get("adjudication") != RECOVERABLE
    }
    final_four_refs = set(final_four_rows)
    if final_four_refs != base_still_quarantined:
        raise RecoveryLedgerError(
            "final-four adjudication does not exactly reconcile the base unresolved population"
        )
    if final_four.get("historical_quarantine_population") != len(historical_refs):
        raise RecoveryLedgerError("final-four historical population does not match quarantine reports")
    if final_four.get("recoverable") != len(historical_refs) or final_four.get("still_quarantined") != 0:
        raise RecoveryLedgerError("final-four artifact does not authorize the complete recovered population")
    if any((row.get("after_status") or row.get("after_audits", {}).get("after_status")) != "PASS" for row in final_four_rows.values()):
        raise RecoveryLedgerError("final-four artifact contains a chapter without a passing post-remediation audit")

    sources = [
        _source_descriptor(base_path, "complete_post_remediation_adjudication", repo_root),
        _source_descriptor(final_four_path, "final_four_overlay_adjudication", repo_root),
    ]
    finalized = _finalized_by_reference(scale_root)
    chapters: list[dict[str, Any]] = []
    for reference in sorted(historical_refs):
        base_row = dict(base_chapters[reference])
        history = historical[reference]
        adjudication = str(base_row.get("adjudication"))
        source_roles = [sources[0]["role"]]
        recovery_reason = "current hardened preflight adjudication passed"
        recovery_timestamp = base.get("generated_at")
        if reference in final_four_refs:
            adjudication = RECOVERABLE
            source_roles.append(sources[1]["role"])
            recovery_reason = "final-four routing remediation passed under unchanged hardened gates"
            recovery_timestamp = final_four.get("generated_at") or recovery_timestamp
        if adjudication == "PENDING_CURRENT_PREFLIGHT":
            adjudication = "UNADJUDICATED"
        if adjudication not in KNOWN_ADJUDICATIONS:
            raise RecoveryLedgerError(f"unknown adjudication for {reference}: {adjudication!r}")
        batch_info = finalized.get(reference)
        consumed = batch_info is not None
        chapters.append({
            "reference": reference,
            "canonical_identity": _canonical_identity(reference),
            "historical_quarantine": True,
            "historical_quarantine_batches": sorted({str(row["source_batch"]) for row in history}),
            "historical_reason_codes": sorted({str(code) for row in history for code in row.get("reason_codes", [])}),
            "historical_records": history,
            "adjudication": adjudication,
            "adjudication_version": base.get("manifest_version") or base.get("report_version") or "unknown",
            "adjudication_source_artifacts": source_roles,
            "adjudication_source_hashes": {
                source["role"]: source["sha256"] for source in sources if source["role"] in source_roles
            },
            "recovery_reason": recovery_reason if adjudication == RECOVERABLE else None,
            "recovery_timestamp": recovery_timestamp if adjudication == RECOVERABLE else None,
            "recovery_policy": "current hardened Luna evidence adjudication; no selection or evidence gate bypass",
            "adjudicated_evidence": _source_evidence(base_row),
            "consumption_status": (
                "CONSUMED_GENERATED" if consumed and batch_info[3]
                else "CONSUMED_LOCKED" if consumed
                else "PENDING_CONSUMPTION" if adjudication == RECOVERABLE
                else "NOT_CONSUMABLE"
            ),
            "consumed_by_batch": batch_info[0] if batch_info else None,
            "consumed_at": batch_info[1] if batch_info else None,
            "generated": bool(batch_info and batch_info[3]),
            "protected_finalized": bool(batch_info and batch_info[2] and batch_info[3]),
        })

    payload: dict[str, Any] = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "scope": "commentary-v1.1-scale",
        "historical_quarantine_count": len(historical_refs),
        "source_artifacts": sources,
        "policy": {
            "historical_quarantine_is_not_permanent_exclusion": True,
            "recoverable_reenters_candidate_selection": True,
            "recovery_does_not_bypass_current_preflight": True,
            "unresolved_dispositions_fail_closed": True,
        },
        "chapters": chapters,
    }
    payload["counts"] = recovery_accounting(payload)
    payload["ledger_sha256"] = _ledger_hash(payload)
    _write_json(output, payload)
    return payload


def validate_recovery_ledger(
    path: Path,
    *,
    repo_root: Path | None = None,
    scale_root: Path | None = None,
) -> dict[str, Any]:
    """Validate ledger structure, source hashes, identities, and invariants."""

    path = path.resolve()
    repo_root = (repo_root or path.parents[3]).resolve()
    payload = _read_json(path)
    if payload.get("schema_version") != LEDGER_SCHEMA_VERSION:
        raise RecoveryLedgerError("unsupported recovery ledger schema")
    sources = payload.get("source_artifacts")
    if not isinstance(sources, list) or not sources:
        raise RecoveryLedgerError("recovery ledger has no authoritative source artifacts")
    source_roles: set[str] = set()
    for source in sources:
        role = str(source.get("role") or "")
        if not role or role in source_roles:
            raise RecoveryLedgerError("recovery ledger has duplicate or missing source roles")
        source_roles.add(role)
        source_path = _resolve_source(str(source.get("path") or ""), repo_root)
        actual = _sha256(source_path)
        if actual != source.get("sha256"):
            raise RecoveryLedgerError(f"recovery source hash mismatch: {source_path}")
    chapters = payload.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise RecoveryLedgerError("recovery ledger has no chapter records")
    references = [str(row.get("reference") or "") for row in chapters]
    if any(not reference for reference in references) or len(references) != len(set(references)):
        raise RecoveryLedgerError("recovery ledger contains duplicate or missing canonical identities")
    if payload.get("historical_quarantine_count") != len(chapters):
        raise RecoveryLedgerError("recovery ledger historical count does not match chapter records")
    for row in chapters:
        reference = str(row["reference"])
        if row.get("historical_quarantine") is not True:
            raise RecoveryLedgerError(f"recovery ledger lost historical quarantine provenance for {reference}")
        identity = row.get("canonical_identity")
        if identity != _canonical_identity(reference):
            raise RecoveryLedgerError(f"recovery ledger canonical identity mismatch for {reference}")
        adjudication = row.get("adjudication")
        if adjudication not in KNOWN_ADJUDICATIONS:
            raise RecoveryLedgerError(f"unknown recovery adjudication for {reference}: {adjudication!r}")
        consumption = row.get("consumption_status")
        if adjudication == RECOVERABLE and consumption not in {"CONSUMED_LOCKED", "CONSUMED_GENERATED", "PENDING_CONSUMPTION"}:
            raise RecoveryLedgerError(f"invalid recoverable consumption state for {reference}")
        if adjudication != RECOVERABLE and consumption != "NOT_CONSUMABLE":
            raise RecoveryLedgerError(f"unresolved chapter is consumable for {reference}")
    expected_hash = _ledger_hash(payload)
    if payload.get("ledger_sha256") != expected_hash:
        raise RecoveryLedgerError("recovery ledger content hash mismatch")
    if scale_root is not None:
        historical = set(_historical_by_reference(scale_root.resolve()))
        if historical != set(references):
            raise RecoveryLedgerError("recovery ledger does not match current historical quarantine population")
    actual_counts = recovery_accounting(payload)
    if payload.get("counts") != actual_counts:
        raise RecoveryLedgerError("recovery ledger accounting does not match chapter states")
    return payload


def load_recovery_ledger(
    path: Path,
    *,
    repo_root: Path | None = None,
    scale_root: Path | None = None,
) -> dict[str, Any]:
    """Load the ledger only after all fail-closed validation succeeds."""

    return validate_recovery_ledger(path, repo_root=repo_root, scale_root=scale_root)


def recovery_accounting(payload: Mapping[str, Any]) -> dict[str, Any]:
    chapters = list(payload.get("chapters") or [])
    return {
        "historical_quarantine": len(chapters),
        "prior_quarantine_recoverable": sum(row.get("adjudication") == RECOVERABLE for row in chapters),
        "prior_quarantine_recovered_already_generated": sum(
            row.get("adjudication") == RECOVERABLE and row.get("consumption_status") == "CONSUMED_GENERATED"
            for row in chapters
        ),
        "prior_quarantine_recovered_consumed_locked": sum(
            row.get("adjudication") == RECOVERABLE and row.get("consumption_status") == "CONSUMED_LOCKED"
            for row in chapters
        ),
        "prior_quarantine_recovered_unconsumed": sum(
            row.get("adjudication") == RECOVERABLE and row.get("consumption_status") == "PENDING_CONSUMPTION"
            for row in chapters
        ),
        "prior_quarantine_unadjudicated": sum(
            row.get("adjudication") == "UNADJUDICATED" for row in chapters
        ),
        "prior_quarantine_still_blocked": sum(
            row.get("adjudication") in KNOWN_ADJUDICATIONS - {RECOVERABLE, "UNADJUDICATED"}
            for row in chapters
        ),
        "unresolved_quarantine": sum(row.get("adjudication") != RECOVERABLE for row in chapters),
    }


def recoverable_unconsumed_references(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(row["reference"])
        for row in payload.get("chapters", [])
        if row.get("adjudication") == RECOVERABLE
        and row.get("consumption_status") == "PENDING_CONSUMPTION"
    }


def recovery_record_map(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(row["reference"]): row for row in payload.get("chapters", [])}
