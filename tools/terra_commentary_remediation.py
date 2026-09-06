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


def regenerate(batch_root: Path, references: list[str], *, attempt: int = 1) -> dict[str, Any]:
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
    targets = sorted(set(references))
    if not targets or len(targets) > 3:
        raise RuntimeError("remediation target must contain one to three chapters")
    if any(reference not in entries or reference not in bundles or reference not in paths for reference in targets):
        raise RuntimeError("remediation target is not a complete locked Terra output")

    attempt_root = batch_root / "terra" / "remediation-attempts" / f"attempt-{attempt:03d}"
    archive_root = attempt_root / "original"
    staging_root = batch_root / f".remediation-attempt-{attempt:03d}.finalizing"
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)
    chapter_rows: list[dict[str, Any]] = []
    model_id = _model_id(str(manifest["batch_id"]))
    for ordinal, reference in enumerate(targets):
        source = paths[reference]
        original = json.loads(source.read_text(encoding="utf-8"))
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
        archive = archive_root / source.name
        if not archive.exists():
            archive.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, archive)
        chapter_rows.append({
            "reference": reference,
            "initial_disposition": "QUARANTINE",
            "initial_reasons": ["READER_UNFRIENDLY"],
            "final_disposition": "PENDING_RECERTIFICATION",
            "regeneration_attempts": attempt,
            "original_path": str(archive.relative_to(ROOT)),
            "replacement_path": str(source.relative_to(ROOT)),
            "original_sha256": _sha256(source),
            "staged_sha256": _sha256(destination),
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
    shutil.rmtree(staging_root)
    report = {
        "report_version": "commentary-v1.1-bounded-remediation-v1",
        "generated_at": _now(),
        "batch_id": manifest["batch_id"],
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
    _write_json(batch_root / "remediation-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--reference", action="append", required=True)
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    try:
        report = regenerate(args.batch_root, args.reference, attempt=args.attempt)
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}))
        return 1
    print(json.dumps({"status": report["status"], "targets": [row["reference"] for row in report["targets"]]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
