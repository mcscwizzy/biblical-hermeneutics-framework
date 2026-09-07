"""Build and adjudicate the Commentary v1.1 quarantine recovery inventory.

This tool never edits CKL data or historical quarantine reports.  It creates a
canonical, append-only recovery inventory and applies the current preflight
result to that inventory.  Recovery is an explicit allowlist consumed by the
evidence preflight; it is not a blanket exemption from prior-batch rules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from framework.commentary.recovery import build_recovery_ledger


REASON_TAXONOMY = {
    "CROSS_BOOK_PARENT_REUSE": "CROSS_BOOK_PARENT_REUSE",
    "WORD_STUDY_BROAD_PARENT_ANCHOR": "WORD_STUDY_OVERREACH",
    "EVIDENCE_HASH_DISAGREEMENT": "BACKEND_HASH_DISAGREEMENT",
    "PRESENTATION_ROLE_AUDIT_FAILURE": "PRESENTATION_ROLE",
    "PRESENTATION_ROLE_MISMATCH": "PRESENTATION_ROLE",
    "TEXTUAL_ROUTING_AUDIT_FAILURE": "ROUTING_CLASSIFICATION",
    "TERRA_SUPPRESSION_REQUIRED": "OTHER",
}
CKL_REMEDIATION_REASONS = {
    "CROSS_BOOK_PARENT_REUSE",
    "WORD_STUDY_BROAD_PARENT_ANCHOR",
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _taxonomy(reason: str) -> str:
    return REASON_TAXONOMY.get(reason, "OTHER")


def _historical_rows(scale_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(scale_root.glob("batch-*/quarantine-report.json")):
        batch = path.parent.name
        data = _read(path)
        for row in data.get("chapters", []):
            item = dict(row)
            item["source_batch"] = batch
            rows.append(item)
    return rows


def _final_references(scale_root: Path) -> set[str]:
    references: set[str] = set()
    for path in sorted(scale_root.glob("batch-*/batch-manifest.json")):
        references.update(str(value) for value in (_read(path).get("final_references") or []))
    return references


def build_inventory(scale_root: Path, output: Path) -> dict[str, Any]:
    rows = _historical_rows(scale_root)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["reference"])].append(row)
    finalized = _final_references(scale_root)
    chapters = []
    for reference in sorted(grouped):
        history = grouped[reference]
        reasons = sorted({str(code) for row in history for code in row.get("reason_codes", [])})
        taxonomy = sorted({_taxonomy(reason) for reason in reasons}) or ["OTHER"]
        chapters.append({
            "reference": reference,
            "first_quarantine_batch": min(row["source_batch"] for row in history),
            "most_recent_quarantine_batch": max(row["source_batch"] for row in history),
            "source_quarantine_batches": sorted({row["source_batch"] for row in history}),
            "historical_reason_codes": reasons,
            "historical_reason_taxonomy": taxonomy,
            "evidence_ids": sorted({str(value) for row in history for value in row.get("evidence_ids", [])}),
            "ckl_parent_records": sorted({str(value) for row in history for value in row.get("ckl_parent_records", [])}),
            "historical_records": history,
            "later_successfully_generated": reference in finalized,
            "adjudication": "ALREADY_RESOLVED" if reference in finalized else "PENDING_CURRENT_PREFLIGHT",
            "current_preflight": None,
        })
    reason_raw = Counter(str(code) for row in rows for code in row.get("reason_codes", []))
    reason_unique = Counter(
        code for chapter in chapters for code in chapter["historical_reason_codes"]
    )
    taxonomy_raw = Counter(_taxonomy(str(code)) for row in rows for code in row.get("reason_codes", []))
    taxonomy_unique = Counter(category for chapter in chapters for category in chapter["historical_reason_taxonomy"])
    payload = {
        "manifest_version": "commentary-v1.1-quarantine-recovery-v1",
        "generated_at": _now(),
        "source": "commentary-v1.1-scale/batch-*/quarantine-report.json",
        "ckl_mutated": False,
        "raw_quarantine_records": len(rows),
        "unique_quarantined_chapters": len(chapters),
        "already_resolved_count": sum(chapter["adjudication"] == "ALREADY_RESOLVED" for chapter in chapters),
        "unresolved_unique_count": sum(chapter["adjudication"] != "ALREADY_RESOLVED" for chapter in chapters),
        "reason_distribution": {
            "raw_reason_codes": dict(sorted(reason_raw.items())),
            "unique_reason_codes": dict(sorted(reason_unique.items())),
            "raw_taxonomy": dict(sorted(taxonomy_raw.items())),
            "unique_taxonomy": dict(sorted(taxonomy_unique.items())),
        },
        "chapters": chapters,
        "future_ckl_remediation_queue": [],
        "adjudication_status": "PENDING_CURRENT_PREFLIGHT",
    }
    _write_json(output, payload)
    return payload


def _preflight_report(
    scale_root: Path,
    batch_id: str,
    preflight_report: Path | None = None,
) -> tuple[dict[str, Any], Path]:
    if preflight_report is not None:
        return _read(preflight_report), preflight_report
    batch = scale_root / batch_id
    final = batch / "preflight-report.json"
    if final.exists():
        return _read(final), final
    blocked = scale_root / f".{batch_id}.work" / "blocked-report.json"
    if blocked.exists():
        report = _read(blocked)
        return report.get("preflight", report), blocked
    raise FileNotFoundError(f"no preflight report found for {batch_id}")


def adjudicate(
    scale_root: Path,
    manifest_path: Path,
    batch_id: str,
    output: Path,
    queue_output: Path | None = None,
    preflight_report: Path | None = None,
) -> dict[str, Any]:
    manifest = _read(manifest_path)
    preflight, source_path = _preflight_report(scale_root, batch_id, preflight_report)
    evaluated = {str(row["reference"]): row for row in preflight.get("evaluated", [])}
    chapters = []
    future_queue = []
    for chapter in manifest.get("chapters", []):
        item = dict(chapter)
        reference = str(item["reference"])
        record = evaluated.get(reference)
        if item.get("adjudication") == "ALREADY_RESOLVED":
            item["current_preflight"] = {"status": "ALREADY_RESOLVED"}
            chapters.append(item)
            continue
        if record is None:
            item["adjudication"] = "STILL_QUARANTINED"
            item["current_preflight"] = {"status": "NOT_EVALUATED", "reason": "not present in current preflight"}
            chapters.append(item)
            continue
        reasons = sorted({str(value) for value in record.get("quarantine_reason_codes", [])})
        integrity = record.get("json_sqlite_agreement", {})
        current = {
            "status": record.get("status"),
            "availability": record.get("availability"),
            "evidence_ids": record.get("evidence_ids", []),
            "evidence_hash": record.get("evidence_hash"),
            "reason_codes": reasons,
            "json_sqlite_agreement": integrity,
            "anomaly_scan": record.get("anomaly_scan", {}),
            "semantic_audit": record.get("semantic_audit", {}),
            "presentation_role_audit": record.get("presentation_role_audit", {}),
            "textual_routing_audit": record.get("textual_routing_audit", {}),
        }
        item["current_preflight"] = current
        if record.get("status") == "PASS" and record.get("availability") in {"AVAILABLE", "THIN"}:
            item["adjudication"] = "RECOVERABLE"
        elif record.get("status") == "DATA_GAP":
            item["adjudication"] = "DATA_GAP"
        elif set(reasons) & CKL_REMEDIATION_REASONS:
            item["adjudication"] = "REQUIRES_CKL_REMEDIATION"
            future_queue.append({
                "reference": reference,
                "current_blocker": reasons,
                "affected_evidence": item.get("evidence_ids", []),
                "required_ckl_change_type": "parent anchor scope or routing metadata review",
                "archaeology_expansion_helpful": False,
                "language_expansion_helpful": "WORD_STUDY_BROAD_PARENT_ANCHOR" in reasons,
                "cultural_historical_expansion_helpful": "CROSS_BOOK_PARENT_REUSE" in reasons,
                "routing_metadata_correction_helpful": False,
                "simple_evidence_enrichment_helpful": False,
            })
        else:
            item["adjudication"] = "STILL_QUARANTINED"
        chapters.append(item)
    counts = Counter(str(chapter["adjudication"]) for chapter in chapters)
    result = dict(manifest)
    result["generated_at"] = _now()
    result["adjudication_status"] = "COMPLETE"
    result["preflight_source"] = str(source_path)
    result["current_preflight_batch"] = batch_id
    result["adjudication_counts"] = dict(sorted(counts.items()))
    result["chapters"] = chapters
    result["future_ckl_remediation_queue"] = future_queue
    result["recoverable_references"] = sorted(
        chapter["reference"] for chapter in chapters if chapter["adjudication"] == "RECOVERABLE"
    )
    result["recovery_manifest_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    _write_json(output, result)
    if queue_output is not None:
        _write_json(queue_output, {
            "queue_version": "commentary-v1.1-future-ckl-remediation-v1",
            "generated_at": result["generated_at"],
            "source_recovery_manifest": str(output),
            "ckl_mutated": False,
            "chapters": future_queue,
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "adjudicate", "ledger"))
    parser.add_argument("--scale-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--base-adjudication", type=Path)
    parser.add_argument("--final-four-adjudication", type=Path)
    parser.add_argument("--batch-id", default="batch-007")
    parser.add_argument("--queue-output", type=Path)
    parser.add_argument("--preflight-report", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        result = build_inventory(args.scale_root.resolve(), args.output.resolve())
    elif args.command == "adjudicate":
        if args.manifest is None:
            parser.error("--manifest is required for adjudicate")
        result = adjudicate(
            args.scale_root.resolve(),
            args.manifest.resolve(),
            args.batch_id,
            args.output.resolve(),
            args.queue_output.resolve() if args.queue_output else None,
            args.preflight_report.resolve() if args.preflight_report else None,
        )
    else:
        result = build_recovery_ledger(
            args.scale_root.resolve(),
            args.output.resolve(),
            base_adjudication=args.base_adjudication.resolve() if args.base_adjudication else None,
            final_four_adjudication=args.final_four_adjudication.resolve() if args.final_four_adjudication else None,
        )
    print(json.dumps({
        "status": result.get("adjudication_status") or result.get("schema_version"),
        "raw_quarantine_records": result.get("raw_quarantine_records"),
        "unique_quarantined_chapters": result.get("unique_quarantined_chapters") or result.get("historical_quarantine_count"),
        "adjudication_counts": result.get("adjudication_counts") or result.get("counts"),
        "recoverable_count": len(result.get("recoverable_references", [])) or (result.get("counts") or {}).get("prior_quarantine_recoverable"),
        "output": str(args.output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
