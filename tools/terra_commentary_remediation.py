#!/usr/bin/env python3
"""Regenerate only allowlisted reader-friendliness failures.

The runner revalidates the complete evidence lock, stages replacement prose,
and promotes only the explicitly named chapters after every replacement has
passed the same structural and quality checks.  It never selects evidence or
changes CKL data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.commentary.remediation import MAX_AUTOMATIC_REGENERATION_ATTEMPTS
from framework.commentary.remediation_groups import canonical_reference_sort_key
from tools.terra_commentary_scaled_batch import (
    _load,
    _model_id,
    _validation_row,
    payload_for,
    prose_audit,
    revalidate_locks,
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _semantic_sha256(path: Path) -> str:
    """Hash a chapter while ignoring the intentionally regenerated timestamp."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata = payload.get("generated_metadata")
    if isinstance(metadata, dict):
        metadata = dict(metadata)
        metadata.pop("generated_timestamp", None)
        payload["generated_metadata"] = metadata
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _chapter_paths(terra: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in sorted((terra / "chapters").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        reference = payload.get("reference")
        if reference:
            result[str(reference)] = path
    return result


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def regenerate(
    batch_root: Path,
    references: list[str],
    *,
    attempt: int = 1,
    group_id: str | None = None,
    group_root: Path | None = None,
    output_report: Path | None = None,
) -> dict[str, Any]:
    """Run one bounded, idempotently resumable remediation group.

    ``group_root`` and ``output_report`` isolate coordinated invocations from
    one another.  Omitting them preserves the original direct-runner layout
    for callers that intentionally run a single bounded group.
    """

    if attempt != 1 or attempt > MAX_AUTOMATIC_REGENERATION_ATTEMPTS:
        raise RuntimeError("automatic remediation permits exactly one attempt")
    batch_root = batch_root.resolve()
    manifest, certification, terra_input, _ = _load(batch_root)
    lock, bundles = revalidate_locks(terra_input, certification)
    if lock.get("status") != "PASS":
        raise RuntimeError("evidence lock revalidation failed; remediation refused")
    entries = {str(row["reference"]): row for row in terra_input["chapters"]}
    certified = {str(row["reference"]): row for row in certification["chapters"]}
    paths = _chapter_paths(batch_root / "terra")
    targets = sorted(set(references), key=canonical_reference_sort_key)
    if not targets or len(targets) > 3:
        raise RuntimeError("remediation target must contain one to three chapters")
    if any(reference not in entries or reference not in bundles or reference not in paths for reference in targets):
        raise RuntimeError("remediation target is not a complete locked Terra output")

    attempt_root = batch_root / "terra" / "remediation-attempts" / f"attempt-{attempt:03d}"
    if group_id and not group_root:
        group_root = attempt_root / group_id
    artifact_root = (group_root.resolve() if group_root else attempt_root.resolve())
    archive_root = artifact_root / "original"
    staging_root = artifact_root / ".staging"
    report_path = output_report.resolve() if output_report else batch_root / "remediation-report.json"
    if group_id and report_path.exists():
        try:
            existing_report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"existing remediation report is corrupt: {report_path}") from exc
        if (
            existing_report.get("status") == "READY_FOR_RECERTIFICATION"
            and existing_report.get("group_id") == group_id
            and sorted(existing_report.get("references", []), key=canonical_reference_sort_key) == targets
        ):
            return existing_report
    existing_rows = {}
    if report_path.exists():
        try:
            existing = json.loads(report_path.read_text(encoding="utf-8"))
            existing_rows = {row.get("reference"): row for row in existing.get("targets", [])}
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"existing remediation report is corrupt: {report_path}") from exc
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)
    chapter_rows: list[dict[str, Any]] = []
    model_id = _model_id(str(manifest["batch_id"]))
    for ordinal, reference in enumerate(targets):
        source = paths[reference]
        archive = archive_root / source.name
        if not archive.exists():
            archive.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, archive)
        prior_row = existing_rows.get(reference)
        if prior_row and prior_row.get("original_sha256") != _sha256(archive):
            raise RuntimeError(f"immutable original archive changed: {reference}")
        original = json.loads(archive.read_text(encoding="utf-8"))
        entry = entries[reference]
        bundle = bundles[reference]
        replacement = payload_for(entry, bundle, ordinal=ordinal, model_id=model_id, remediation=True)
        validation = _validation_row(replacement, bundle)
        flags = prose_audit(replacement, bundle)
        before_ids = sorted({eid for section in original["sections"] for block in section["blocks"] for eid in block["evidence_ids"]})
        after_ids = sorted({eid for section in replacement["sections"] for block in section["blocks"] for eid in block["evidence_ids"]})
        expected_ids = sorted(certified[reference]["evidence_ids"])
        if not validation["valid"] or flags or after_ids != before_ids or not set(after_ids).issubset(set(expected_ids)) or replacement["generated_metadata"].get("evidence_hash") != entry["locked_evidence_bundle_hash"]:
            raise RuntimeError(f"replacement validation failed for {reference}: {validation['errors'] or flags}")
        destination = staging_root / source.name
        _write_json(destination, replacement)
        current_sha = _sha256(source)
        original_sha = _sha256(archive)
        replacement_sha = _sha256(destination)
        current_semantic_sha = _semantic_sha256(source)
        original_semantic_sha = _semantic_sha256(archive)
        replacement_semantic_sha = _semantic_sha256(destination)
        if current_sha != original_sha and current_semantic_sha != replacement_semantic_sha:
            raise RuntimeError(f"existing remediation target is neither original nor staged replacement: {reference}")
        chapter_rows.append({
            "reference": reference,
            "initial_disposition": "QUARANTINE",
            "initial_reasons": ["READER_UNFRIENDLY"],
            "final_disposition": "PENDING_RECERTIFICATION",
            "regeneration_attempts": attempt,
            "original_path": _display_path(archive),
            "replacement_path": _display_path(source),
            "original_sha256": original_sha,
            "original_semantic_sha256": original_semantic_sha,
            "staged_sha256": replacement_sha,
            "replacement_semantic_sha256": replacement_semantic_sha,
            "locked_evidence_ids": expected_ids,
            "evidence_ids_before": before_ids,
            "evidence_ids_after": after_ids,
            "evidence_hash_before": original.get("generated_metadata", {}).get("evidence_hash"),
            "evidence_hash_after": replacement["generated_metadata"]["evidence_hash"],
            "evidence_hash_locked": entry["locked_evidence_bundle_hash"],
            "quality_flags_after": flags,
        })

    for row in chapter_rows:
        staged = staging_root / Path(row["replacement_path"]).name
        target = ROOT / row["replacement_path"]
        os.replace(staged, target)
        row["replacement_sha256"] = _sha256(target)
    if staging_root.exists():
        shutil.rmtree(staging_root)
    report = {
        "report_version": "commentary-v1.1-bounded-remediation-group-v1",
        "generated_at": _now(),
        "batch_id": manifest["batch_id"],
        "group_id": group_id,
        "group_status": "COMPLETE",
        "attempt": attempt,
        "references": targets,
        "artifact_root": _display_path(artifact_root),
        "policy": {
            "allowlisted_findings": ["READER_UNFRIENDLY"],
            "maximum_automatic_regeneration_attempts": MAX_AUTOMATIC_REGENERATION_ATTEMPTS,
            "model": "terra",
            "effort": "medium",
            "evidence_selection_changed": False,
        },
        "status": "READY_FOR_RECERTIFICATION",
        "targets": chapter_rows,
        "lock_revalidation": lock,
    }
    _write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--reference", action="append", required=True)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--group-id")
    parser.add_argument("--group-root", type=Path)
    parser.add_argument("--output-report", type=Path)
    args = parser.parse_args()
    try:
        report = regenerate(
            args.batch_root,
            args.reference,
            attempt=args.attempt,
            group_id=args.group_id,
            group_root=args.group_root,
            output_report=args.output_report,
        )
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}))
        return 1
    print(json.dumps({"status": report["status"], "targets": [row["reference"] for row in report["targets"]]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
