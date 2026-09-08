"""Rebuildable production ledger; manifests and artifacts remain authoritative."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .census import canonical_chapters
from .models import PRODUCTION_VERSION, production_root, sha256_json, write_json


def rebuild_ledger(repo_root: Path, output: Path | None = None) -> dict[str, Any]:
    root = production_root(repo_root)
    occurrences: dict[str, list[dict[str, Any]]] = {}
    for state_path in sorted((root / "runs").glob("*/batches/*/state.json")):
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for reference, record in (state.get("chapters") or {}).items():
            occurrences.setdefault(reference, []).append({
                **record,
                "reference": reference,
                "run_id": state.get("run_id"),
                "batch_id": state.get("batch_id"),
                "state_path": str(state_path.relative_to(repo_root)),
            })
    current: dict[str, dict[str, Any]] = {}
    for reference, records in occurrences.items():
        current[reference] = sorted(records, key=lambda row: (str(row.get("run_id")), str(row.get("batch_id"))))[-1]
    counts = Counter(row.get("state", "PENDING") for row in current.values())
    all_chapters = canonical_chapters()
    known = {row["reference"] for row in all_chapters}
    counts["PENDING"] += len(known - set(current))
    terminal = {"COMPLETE", "GATE_QUALITY_FAIL", "QUARANTINED", "STALE_INPUT", "BLOCKED"}
    next_rows = [row for row in all_chapters if current.get(row["reference"], {}).get("state", "PENDING") not in terminal]
    used_batches = [str(row.get("batch_id", "")) for row in current.values()]
    batch_numbers = [int(value.split("-")[-1]) for value in used_batches if value.startswith("batch-") and value.split("-")[-1].isdigit()]
    ledger = {
        "artifact_version": "commentary-production-ledger-v1",
        "production_version": PRODUCTION_VERSION,
        "canonical_chapter_count": len(all_chapters),
        "counts": dict(sorted(counts.items())),
        "next_chapter": next_rows[0] if next_rows else None,
        "next_batch_id": f"batch-{(max(batch_numbers) + 1 if batch_numbers else 1):03d}",
        "current": {key: current[key] for key in sorted(current)},
        "history": {key: sorted(value, key=lambda row: (str(row.get("run_id")), str(row.get("batch_id")))) for key, value in sorted(occurrences.items())},
        "reconstructed_from": "batch state files; raw/accepted/gate/quarantine artifacts are reconciled by the runner",
    }
    ledger["ledger_identity"] = sha256_json(ledger)
    if output is None:
        output = root / "ledger.json"
    write_json(output, ledger)
    return ledger
