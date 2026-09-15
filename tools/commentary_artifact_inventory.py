#!/usr/bin/env python3
"""Write a deterministic inventory of commentary artifact roots and references."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/commentary-artifact-inventory.json"
COMMENTARY_ROOTS = [
    ROOT / ".bhf-data/bhf-commentary",
    ROOT / ".bhf-data/bhf-commentary-v1.1",
    ROOT / ".bhf-data/bhf-commentary-v1.2",
    ROOT / ".bhf-data/bhf-commentary-production",
    ROOT / ".bhf-data/bhf-commentary-production/v1",
    ROOT / ".bhf-data/bhf-commentary-candidates",
]

CLASSIFICATIONS = {
    ".bhf-data/bhf-commentary": "ACTIVE_RUNTIME_RELEASE",
    ".bhf-data/bhf-commentary-v1.1": "ACTIVE_RUNTIME_RELEASE",
    ".bhf-data/bhf-commentary-v1.2": "ACTIVE_RUNTIME_RELEASE",
    ".bhf-data/bhf-commentary-production": "HISTORICAL_AUDIT_ONLY",
    ".bhf-data/bhf-commentary-production/v1": "ABANDONED_RUNTIME_LAYOUT",
    ".bhf-data/bhf-commentary-candidates": "ACTIVE_VALIDATION_ARTIFACT",
}

KNOWN_CANDIDATE_CLASSES = {
    "commentary-renderer-transport-diagnostic-v1": (
        "TEMPORARY_DIAGNOSTIC", "REMOVE_FROM_HEAD",
        "Transport diagnosis is resolved; the immutable audit report remains in docs and Git history preserves raw evidence.",
    ),
    "commentary-output-conformance-v1-d278cba2d2151d1b4242": (
        "ACTIVE_VALIDATION_ARTIFACT", "KEEP",
        "Current conformance regression coverage still reads this frozen artifact.",
    ),
    "commentary-v1.2-terra-75-scale-validation-v1-e8af58131e066def98a2": (
        "ACTIVE_RELEASE_AUDIT", "KEEP",
        "The v1.2 promotion tool consumes this immutable validation source.",
    ),
    "commentary-v1.2-scale-pilot-provenance-binding-v1-f139d722270544978d04": (
        "ACTIVE_VALIDATION_ARTIFACT", "KEEP",
        "The frozen v1.2 validation chain retains its source identity and audit bindings.",
    ),
}

REMOVED_RECORDS = [
    {
        "path": ".bhf-data/bhf-commentary-candidates/commentary-renderer-transport-diagnostic-v1",
        "type": "directory",
        "present": False,
        "file_count": 17,
        "directory_count": 1,
        "bytes": 74715,
        "first_identifiable_version": "v1",
        "current_consumer_or_reference": {
            "docs": ["docs/commentary-v1.2-renderer-transport-diagnostic-v1.md"],
            "git_source_commit": "5a3cb3329a3671f81db187f85478b770f068f233",
        },
        "required_for_v1_1": False,
        "required_for_v1_2": False,
        "required_for_current_release_promotion": False,
        "required_for_reproducibility": False,
        "classification": "TEMPORARY_DIAGNOSTIC",
        "proposed_action": "REMOVED_FROM_HEAD",
        "reason": "Transport diagnosis is resolved; the immutable audit report remains in docs and Git history preserves raw evidence.",
        "worktree_modified": False,
    },
]


def _root_record(path: Path) -> dict[str, object]:
    relative = path.relative_to(ROOT).as_posix()
    files = sorted(item for item in path.rglob("*") if item.is_file()) if path.exists() else []
    directories = sorted(item for item in path.rglob("*") if item.is_dir()) if path.exists() else []
    refs: dict[str, list[str]] = {}
    needle = path.name
    for scope, locations in {
        "python": ["bhf_agent", "bhf_web", "framework", "tools"],
        "tests": ["tests"],
        "docs": ["docs"],
        "runtime_configuration": [".github", "Dockerfile", "vercel.json", ".vercelignore"],
    }.items():
        command = [
            "rg", "-l", "-F", "--hidden", "--glob", "!.git/**", "--glob", "!.bhf-data/**",
            needle, *locations,
        ]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        values = sorted(line for line in result.stdout.splitlines() if line)
        if values:
            refs[scope] = values
    status = subprocess.run(
        ["git", "status", "--short", "--", relative],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    classification, proposed_action, reason = KNOWN_CANDIDATE_CLASSES.get(
        path.name,
        ("UNKNOWN_REQUIRES_REVIEW", "REVIEW_ONLY", "Locally present artifact requires explicit review before removal."),
    )
    if relative in CLASSIFICATIONS:
        classification = CLASSIFICATIONS[relative]
        proposed_action = "KEEP" if relative != ".bhf-data/bhf-commentary-production/v1" else "REVIEW_ONLY"
        reason = "Aggregate directory inventory; individual release payloads are verified by their manifests/checksum indexes."
    return {
        "path": relative,
        "type": "directory",
        "file_count": len(files),
        "directory_count": len(directories) + 1,
        "bytes": sum(item.stat().st_size for item in files),
        "first_identifiable_version": (re.search(r"v\d+(?:\.\d+)*", path.name) or ["legacy"])[0],
        "current_consumer_or_reference": refs,
        "required_for_v1_1": path.name in {"bhf-commentary", "bhf-commentary-v1.1", "bhf-commentary-production", "v1", "commentary-v1.1-scale", "commentary-v1.1-terra"},
        "required_for_v1_2": path.name in {"bhf-commentary-v1.2", "commentary-v1.2-terra-75-scale-validation-v1-e8af58131e066def98a2", "commentary-v1.2-scale-pilot-provenance-binding-v1-f139d722270544978d04"},
        "required_for_current_release_promotion": path.name in {"bhf-commentary-v1.2", "commentary-v1.2-terra-75-scale-validation-v1-e8af58131e066def98a2", "commentary-v1.2-scale-pilot-provenance-binding-v1-f139d722270544978d04"},
        "required_for_reproducibility": path.name in {"bhf-commentary-v1.1", "bhf-commentary-v1.2", "commentary-v1.1-scale", "commentary-v1.1-terra", "commentary-v1.2-terra-75-scale-validation-v1-e8af58131e066def98a2", "commentary-v1.2-scale-pilot-provenance-binding-v1-f139d722270544978d04"},
        "classification": classification,
        "proposed_action": proposed_action,
        "reason": reason,
        "worktree_modified": bool(status),
    }


def main() -> None:
    records = [_root_record(path) for path in COMMENTARY_ROOTS if path.exists()]
    candidates = ROOT / ".bhf-data/bhf-commentary-candidates"
    if candidates.exists():
        records.extend(_root_record(path) for path in sorted(candidates.iterdir()) if path.is_dir())
    records.extend(REMOVED_RECORDS)
    payload = {
        "inventory_version": "commentary-artifact-inventory-v1",
        "generated_from": "working-tree",
        "granularity": "directory aggregates plus repository references; release manifests enumerate payload files",
        "records": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
