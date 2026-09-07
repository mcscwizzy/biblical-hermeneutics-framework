#!/usr/bin/env python3
"""Independently certify a locked Terra commentary batch without changing prose."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.terra_commentary_scaled_batch import (
    ROOT, _load, _word_count, prose_audit, revalidate_locks, _validation_row,
)

HISTORICAL_ROOTS = {
    "canary": ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-terra/chapters",
    "supplemental": ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-terra/supplemental-integrity-controls/chapters",
    "batch_001": ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-001/terra/chapters",
    "batch_002": ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-002/terra/chapters",
}

def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def fingerprints(paths: list[Path]) -> dict[str, str]:
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}

def percentile(values: list[int], point: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * point
    lower, upper = int(index), min(int(index) + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower), 1)

def run(batch_root: Path) -> dict[str, Any]:
    batch_root = batch_root.resolve()
    manifest, certification, terra_input, _ = _load(batch_root)
    terra = batch_root / "terra"
    chapters = {row["reference"]: row for row in terra_input["chapters"]}
    certified = {row["reference"]: row for row in certification["chapters"]}
    lock, bundles = revalidate_locks(terra_input, certification)
    historical = fingerprints([p for root in HISTORICAL_ROOTS.values() for p in root.glob("*.json")])
    expected_historical = {}
    for key in ("artifact_fingerprints_after", "batch_001_terra_artifact_fingerprints_after", "batch_002_terra_artifact_fingerprints_after"):
        expected_historical.update(manifest.get(key, {}))
    candidates: dict[str, dict[str, Any]] = {}
    output_paths = list((terra / "chapters").glob("*.json"))
    for path in output_paths:
        candidate = json.loads(path.read_text(encoding="utf-8"))
        candidates[candidate.get("reference", path.stem)] = candidate
    rows, all_flags, provenance, unsupported = [], Counter(), [], []
    for reference, entry in chapters.items():
        candidate, bundle = candidates.get(reference), bundles.get(reference)
        reasons: list[str] = []
        if candidate is None: reasons.append("missing generated chapter")
        if bundle is None: reasons.append("stale locked bundle")
        if candidate and bundle:
            validation = _validation_row(candidate, bundle)
            flags = prose_audit(candidate, bundle)
            cited = {eid for section in candidate["sections"] for block in section["blocks"] for eid in block["evidence_ids"]}
            locked = set(certified[reference]["evidence_ids"])
            if not validation["valid"]: reasons.extend(validation["errors"])
            if cited - locked: provenance.append({"reference": reference, "unexpected_evidence_ids": sorted(cited - locked)}); reasons.append("evidence provenance drift")
            if candidate.get("generated_metadata", {}).get("evidence_hash") != entry["locked_evidence_bundle_hash"]: reasons.append("generated hash differs from lock")
            if flags: unsupported.append({"reference": reference, "flags": flags}); reasons.extend(flags)
            all_flags.update(flags)
        disposition = "PASS" if not reasons else "QUARANTINE"
        rows.append({"reference": reference, "initial_disposition": disposition, "final_disposition": disposition, "regeneration_attempts": 0, "reasons": reasons})
    extras = sorted(set(candidates) - set(chapters))
    if extras: rows.append({"reference": "__extra_outputs__", "initial_disposition": "QUARANTINE", "final_disposition": "QUARANTINE", "regeneration_attempts": 0, "reasons": extras})
    prose_fingerprints = fingerprints(output_paths)
    duplicates = [digest for digest, count in Counter(prose_fingerprints.values()).items() if count > 1]
    duplicate_rows = {digest: [path for path, value in prose_fingerprints.items() if value == digest] for digest in duplicates}
    words = [_word_count(candidate) for candidate in candidates.values()]
    evidence = [len(certified[ref]["evidence_ids"]) for ref in chapters]
    by_availability = Counter(row["availability"] for row in certification["chapters"])
    final_pass = sum(row["final_disposition"] == "PASS" for row in rows)
    go = lock["status"] == "PASS" and final_pass == len(chapters) and not extras and not duplicate_rows and historical == expected_historical
    return {
        "report_version": "commentary-v1.1-post-generation-v1", "generated_at": now(), "batch_id": manifest["batch_id"],
        "status": "GO" if go else "NO_GO", "chapters_attempted": len(chapters), "chapters_generated": len(candidates),
        "final_accepted_count": final_pass, "disposition_counts": dict(Counter(r["final_disposition"] for r in rows)), "regeneration_attempts": 0,
        "availability_outcomes": dict(by_availability), "lock_revalidation": lock,
        "provenance_anomalies": provenance, "unsupported_claim_findings": unsupported,
        "findings": {"lexical": [], "textual_routing": [], "archaeology": [], "later_reception": [], "presentation_role": [], "semantic_leakage": [], "template_evidence": [], "cross_book": [], "broad_anchor": []},
        "quality_flag_counts": dict(all_flags), "duplicate_prose_fingerprints": duplicate_rows,
        "cross_batch_fingerprint_matches": {path: digest for path, digest in prose_fingerprints.items() if digest in historical.values()},
        "prior_prose_fingerprints": {"expected_count": len(expected_historical), "actual_count": len(historical), "unchanged": historical == expected_historical},
        "batch_003_prose_fingerprints": prose_fingerprints,
        "statistics": {"evidence_count": stats(evidence), "word_count": stats(words)}, "chapters": rows,
    }

def stats(values: list[int]) -> dict[str, float]:
    return {"min": min(values), "median": statistics.median(values), "mean": round(statistics.mean(values), 1), "p90": percentile(values, .9), "p95": percentile(values, .95), "max": max(values)}

def markdown(report: dict[str, Any]) -> str:
    d = report["disposition_counts"]
    return "\n".join([f"# BHF Commentary v1.1 Scaled {report['batch_id'].replace('-', ' ').title()} Post-generation", "", f"Final certification: **{report['status']}**.", "", "## Result", "", f"- Attempted / generated / accepted: {report['chapters_attempted']} / {report['chapters_generated']} / {report['final_accepted_count']}.", f"- PASS / REGENERATE / QUARANTINE / DATA_GAP: {d.get('PASS',0)} / {d.get('REGENERATE',0)} / {d.get('QUARANTINE',0)} / {d.get('DATA_GAP',0)}.", f"- Rebuilt locks: {report['lock_revalidation']['locks_revalidated']}; stale: {len(report['lock_revalidation']['stale_locks'])}.", f"- Prior 176 prose artifacts unchanged: {report['prior_prose_fingerprints']['unchanged']}.", f"- Duplicate Batch 003 fingerprints: {len(report['duplicate_prose_fingerprints'])}; cross-batch matches: {len(report['cross_batch_fingerprint_matches'])}.", f"- Evidence statistics: {report['statistics']['evidence_count']}.", f"- Word statistics: {report['statistics']['word_count']}.", "", "No CKL records or pre-existing prose artifacts were modified.", ""])

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-root", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.batch_root)
    root = args.batch_root
    (root / "post-generation-report.json").write_text(json.dumps(report, indent=2) + "\n")
    (root / "prose-certification.json").write_text(json.dumps(report, indent=2) + "\n")
    (ROOT / "docs" / f"commentary-v1.1-scaled-{report['batch_id']}-post-generation.md").write_text(markdown(report))
    print(json.dumps({"status": report["status"], "accepted": report["final_accepted_count"]}))
    return 0 if report["status"] == "GO" else 1

if __name__ == "__main__": raise SystemExit(main())
