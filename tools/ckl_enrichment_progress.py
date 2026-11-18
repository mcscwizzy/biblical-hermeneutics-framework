#!/usr/bin/env python3
"""Sync and validate the CKL explanation-enrichment progress manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CKL_ROOT = REPO_ROOT / "framework" / "canonical_library"
MANIFEST_PATH = REPO_ROOT / "docs" / "evidence-depth" / "ckl-enrichment" / "progress.json"


def _protected_fingerprint(data: dict[str, Any]) -> str:
    claims = []
    for item in data.get("claims", []):
        claims.append({key: value for key, value in item.items() if key not in {"rationale", "notes"}})
    evidence = []
    for item in data.get("evidence_items", []):
        fields = (
            "id", "evidence_type", "assertion_type", "confidence", "certainty",
            "dispute_status", "scripture_references", "source_ids", "claim_ids",
            "related_objects", "related_evidence", "external_references", "geography_ids",
            "temporal_scope", "metadata", "notes",
        )
        evidence.append({key: item.get(key) for key in fields if key in item})
    protected = {
        key: data.get(key)
        for key in (
            "id", "type", "content_status", "review_status", "generated_by", "edited_by",
            "reviewed_by", "last_reviewed", "confidence", "human_review_required", "sources",
            "scripture_references", "cross_references", "related_objects", "related_entries",
            "claims", "evidence_items", "section_status", "knowledge_layers",
        )
        if key not in {"claims", "evidence_items"} and key in data
    }
    protected["claims"] = claims
    protected["evidence_items"] = evidence
    encoded = json.dumps(protected, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _inventory() -> dict[str, dict[str, Any]]:
    objects: dict[str, dict[str, Any]] = {}
    for path in sorted((CKL_ROOT / "objects").rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        object_id = str(data["id"])
        if object_id in objects:
            raise ValueError(f"duplicate CKL object id: {object_id}")
        objects[object_id] = {
            "id": object_id,
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "type": data.get("type", ""),
            "content_status": data.get("content_status", ""),
            "review_status": data.get("review_status", ""),
            "human_review_required": data.get("human_review_required", False),
            "protected_sha256": _protected_fingerprint(data),
        }
    return objects


def _new_entry(identity: dict[str, Any]) -> dict[str, Any]:
    return {
        **identity,
        "status": "pending_review",
        "fields_examined": [],
        "fields_changed": [],
        "outcome": "",
        "limitation": "",
        "validation": {"status": "not_run", "results": []},
    }


def sync(path: Path) -> dict[str, int]:
    inventory = _inventory()
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        prior = {item["id"]: item for item in manifest.get("objects", [])}
        stale = sorted(set(prior) - set(inventory))
        if stale:
            raise ValueError("manifest contains CKL objects no longer present: " + ", ".join(stale))
        rows = []
        for object_id, identity in inventory.items():
            existing = prior.get(object_id)
            if existing is None:
                rows.append(_new_entry(identity))
            else:
                # Refresh inventory metadata while preserving editorial progress.
                rows.append({
                    **_new_entry(identity),
                    **existing,
                    **{key: value for key, value in identity.items() if key != "protected_sha256"},
                    "protected_sha256": existing.get("protected_sha256", identity["protected_sha256"]),
                })
        manifest["objects"] = rows
        manifest["inventory_count"] = len(rows)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": "1.0",
            "mission": "Comprehensive CKL explanation enrichment",
            "branch": "feat/ckl-explanation-enrichment",
            "base_ref": "origin/master",
            "baseline": {
                "ckl_objects": len(inventory),
                "valid_objects": 687,
                "errors": 0,
                "warnings": 14,
                "warning_note": "14 warnings existed before enrichment; see initial audit output.",
            },
            "governance": {
                "protected": [
                    "object, claim, evidence, and source IDs",
                    "source identities, locks, attestations, and provenance",
                    "Scripture references and evidence relationships",
                    "confidence, certainty, dispute, and review statuses",
                    "NE-9C curations, NE-10 bridges and held candidates, and ED-7 classifications",
                ],
                "notes": "Do not expand an assertion beyond its recorded support. ED-7 withheld research remains withheld.",
            },
            "reader_compatibility": {
                "summary": "Serialized by the canonical object API and used in reader-facing object details.",
                "evidence_items": "Serialized in canonical object responses and indexed using title, description, observation, interpretation, passage relevance, and confidence rationale.",
                "claim_rationale": "Retained in structured CKL claim data; reader exposure varies by workflow.",
                "interpretive_notes": "Retained in canonical object detail; no blanket claim that every view renders them.",
            },
            "batches": [],
            "inventory_count": len(inventory),
            "objects": [_new_entry(value) for value in inventory.values()],
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summarize(manifest)


def summarize(manifest: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in manifest.get("objects", []):
        key = str(item.get("status", "missing_status"))
        counts[key] = counts.get(key, 0) + 1
    return counts


def check(path: Path) -> dict[str, int]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    inventory = _inventory()
    rows = manifest.get("objects", [])
    ids = [item.get("id") for item in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("manifest has duplicate object IDs")
    missing = sorted(set(inventory) - set(ids))
    stale = sorted(set(ids) - set(inventory))
    if missing or stale:
        raise ValueError(f"manifest inventory mismatch: missing={missing[:5]} stale={stale[:5]}")
    allowed_statuses = {"pending_review", "in_progress", "enriched", "unchanged_sufficient", "skipped_insufficient_support"}
    for item in rows:
        if item.get("status") not in allowed_statuses:
            raise ValueError(f"{item.get('id')}: invalid status {item.get('status')!r}")
        if item["status"] != "pending_review" and not item.get("fields_examined"):
            raise ValueError(f"{item['id']}: completed review is missing fields_examined")
        if item["status"] == "enriched" and not item.get("fields_changed"):
            raise ValueError(f"{item['id']}: enriched entry is missing fields_changed")
        if item["status"] == "skipped_insufficient_support" and not item.get("limitation"):
            raise ValueError(f"{item['id']}: skipped entry is missing its support limitation")
        if item.get("protected_sha256") != inventory[item["id"]]["protected_sha256"]:
            raise ValueError(f"{item['id']}: protected CKL fields changed")
    return summarize(manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sync", action="store_true", help="Add new inventory rows and preserve progress")
    mode.add_argument("--check", action="store_true", help="Check manifest coverage and completed-entry fields")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()
    try:
        counts = sync(args.manifest) if args.sync else check(args.manifest)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"CKL enrichment manifest error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"inventory_count": sum(counts.values()), "status_counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
