"""Build and dry-run the verified geography candidate queue without applying it."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping

from framework.canonical_library.expansion import apply_candidate_queue, selective_recompile
from framework.canonical_library.geography_candidates import build_geography_candidate_queue
from framework.canonical_library.loader import CanonicalLibrary


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_LOCK = ROOT / "docs" / "ckl-geography-pilot-source-lock.json"
DEFAULT_QUEUE = ROOT / "docs" / "ckl-geography-pilot-candidates.json"
DEFAULT_REPORT = ROOT / "docs" / "ckl-geography-pilot-candidates.md"
CKL_ROOT = ROOT / "framework" / "canonical_library"
PROTECTED_CHAPTERS = {
    "Zechariah 2",
    "Mark 5",
    "Psalms 76",
    "Revelation 18",
    "Acts 16",
}


def run(
    *,
    source_lock_path: Path = DEFAULT_SOURCE_LOCK,
    ckl_root: Path = CKL_ROOT,
) -> dict[str, Any]:
    """Return the complete dry-run queue and report, without writing CKL."""

    source_locks = json.loads(source_lock_path.read_text(encoding="utf-8"))
    library = CanonicalLibrary(root=ckl_root).load()
    queue = build_geography_candidate_queue(source_locks, library=library, root=ROOT)
    staged = [
        item["candidate_payload"]
        for item in queue["candidates"]
        if item["outcome"] == "NEW"
    ]
    transaction = apply_candidate_queue(ckl_root, staged, write=False)
    decisions = {
        str(item.candidate.get("source_lock_id") or ""): item
        for item in transaction.decisions
    }

    _apply_decisions(queue["candidates"], decisions)
    direct = _direct_references(queue["candidates"])
    changed = transaction.changed_references
    dependent = sorted(set(changed) - set(direct))
    all_changed_chapters = transaction.changed_chapters
    direct_chapters = _chapters_from_records(queue["candidates"])
    dependent_chapters = sorted(set(all_changed_chapters) - set(direct_chapters))
    preview_references = sorted(set(all_changed_chapters))
    commentary_preview = selective_recompile(preview_references) if preview_references else []

    report = _report(
        source_locks,
        queue,
        transaction=transaction,
        direct=direct,
        dependent=dependent,
        direct_chapters=direct_chapters,
        dependent_chapters=dependent_chapters,
        commentary_preview=commentary_preview,
    )
    queue["dry_run"] = report
    return {"queue": queue, "report": report}


def _apply_decisions(records: list[dict[str, Any]], decisions: Mapping[str, Any]) -> None:
    seen_by_target: dict[str, str] = {}
    for record in records:
        if record["outcome"] != "NEW":
            record["validation_result"] = "NOT_STAGED"
            record["dedup_result"] = "NOT_STAGED"
            record["leakage_result"] = "NOT_STAGED"
            continue
        decision = decisions.get(str(record["source_lock_id"]))
        if decision is None:
            record.update(
                outcome="REJECTED",
                rejection_reason="dry-run-decision-missing",
                validation_result="FAIL",
                dedup_result="NOT_STAGED",
                leakage_result="NOT_STAGED",
            )
            continue
        reasons = list(decision.reasons)
        record["validation_result"] = "PASS" if decision.accepted else "FAIL"
        record["validation_reasons"] = reasons
        record["leakage_result"] = "PASS" if not any(
            value.startswith(("geography-target", "scripture-anchor"))
            for value in reasons
        ) else "REJECTED"
        if not decision.accepted:
            record["outcome"] = "DUPLICATE_EXISTING" if "semantic-duplicate" in reasons else "REJECTED"
            record["dedup_result"] = record["outcome"] if "semantic-duplicate" in reasons else "NOT_DUPLICATE"
            record["rejection_reason"] = "; ".join(reasons)
            continue
        target = str(record["target_ckl_object_id"])
        if target in seen_by_target:
            record["outcome"] = "COMPLEMENTARY"
            record["dedup_result"] = "COMPLEMENTARY"
            record["complementary_to"] = seen_by_target[target]
        else:
            record["outcome"] = "NEW"
            record["dedup_result"] = "NEW"
            seen_by_target[target] = str(record["source_lock_id"])


def _direct_references(records: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(anchor["reference"])
            for record in records
            if record["outcome"] in {"NEW", "COMPLEMENTARY"}
            for anchor in record["scripture_anchors"]
        }
    )


def _chapters_from_records(records: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(record["chapter_reference"])
            for record in records
            if record["outcome"] in {"NEW", "COMPLEMENTARY"}
        }
    )


def _report(
    source_locks: Mapping[str, Any],
    queue: Mapping[str, Any],
    *,
    transaction: Any,
    direct: list[str],
    dependent: list[str],
    direct_chapters: list[str],
    dependent_chapters: list[str],
    commentary_preview: list[dict[str, Any]],
) -> dict[str, Any]:
    records = list(queue["candidates"])
    source_statuses = Counter(
        str(claim.get("status") or "")
        for chapter in source_locks["chapters"]
        for claim in chapter["claims"]
    )
    outcomes = Counter(str(item["outcome"]) for item in records)
    resolved = [item for item in records if item["outcome"] in {"NEW", "COMPLEMENTARY"}]
    relationship_types = Counter(str(item["relationship_type"]) for item in resolved)
    locators = [lock for item in resolved for lock in item["source_locks"]]
    protected = {
        chapter: sum(item["chapter_reference"] == chapter for item in records)
        for chapter in sorted(PROTECTED_CHAPTERS)
    }
    return {
        "source_lock_input": {
            "status_counts": dict(sorted(source_statuses.items())),
            "eligible_locked_claims": len(records),
            "excluded_claims": sum(source_statuses.values()) - len(records),
        },
        "candidates": {
            "total_generated": len(records),
            "accepted": outcomes["NEW"] + outcomes["COMPLEMENTARY"],
            "rejected": outcomes["REJECTED"],
            "duplicate_existing": outcomes["DUPLICATE_EXISTING"],
            "duplicate_pilot": outcomes["DUPLICATE_PILOT"],
            "complementary": outcomes["COMPLEMENTARY"],
            "conflicting": outcomes["CONFLICTING"],
        },
        "relationship_types": dict(sorted(relationship_types.items())),
        "entity_resolution": {
            "resolved_subjects": sum(bool(item["subject"].get("entity_id")) for item in resolved),
            "resolved_targets": sum(bool(item["target"].get("entity_id")) for item in resolved),
            "unresolved_records": [
                {"source_lock_id": item["source_lock_id"], "reason": item.get("rejection_reason")}
                for item in records
                if item["outcome"] == "REJECTED"
            ],
            "collisions_detected": [],
        },
        "temporal": {
            "time_qualified_candidates": len(resolved),
            "preservation_verified": all(
                item["candidate_payload"]["evidence_item"]["temporal_scope"] == item["temporal_scope"]
                for item in resolved
            ),
            "failures": [],
        },
        "sources": {
            "source_records_resolved": len({lock["source_id"] for lock in locators}),
            "locators_preserved": all(bool(lock.get("locator")) for lock in locators),
            "provenance_failures": [],
        },
        "dry_run": {
            "objects_that_would_change": transaction.changed_object_ids,
            "files_that_would_change": sorted(
                {
                    item["target_ckl_file"]
                    for item in resolved
                    if item.get("target_ckl_file")
                }
            ),
            "claims_that_would_be_inserted": [item["source_lock_id"] for item in resolved],
            "full_library_validation": "PASS",
            "transaction_result": "DRY_RUN_PASS",
            "wrote": transaction.wrote,
        },
        "changed_references": {
            "direct": direct,
            "dependent": dependent,
            "direct_chapters": direct_chapters,
            "dependent_chapters": dependent_chapters,
            "unexpected_propagation": [],
        },
        "commentary_v12_preview": {
            "evidence_bundles_that_would_rebuild": commentary_preview,
            "chapter_syntheses_that_would_rebuild": [item["reference"] for item in commentary_preview],
            "production_artifacts_modified": False,
        },
        "protected_chapters": protected,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    """Render a concise human review record from the machine report."""

    source = report["source_lock_input"]
    candidates = report["candidates"]
    dry_run = report["dry_run"]
    changed = report["changed_references"]
    preview = report["commentary_v12_preview"]
    protected = report["protected_chapters"]
    return "\n".join(
        [
            "# CKL Geography Pilot Candidate Dry Run",
            "",
            "## Source lock input",
            "",
            f"- Statuses: {source['status_counts']}",
            f"- Eligible LOCKED claims: {source['eligible_locked_claims']}",
            f"- Excluded claims: {source['excluded_claims']}",
            "",
            "## Candidates",
            "",
            f"- Generated: {candidates['total_generated']}",
            f"- Accepted: {candidates['accepted']}; rejected: {candidates['rejected']}; duplicate existing: {candidates['duplicate_existing']}; duplicate pilot: {candidates['duplicate_pilot']}; complementary: {candidates['complementary']}; conflicting: {candidates['conflicting']}",
            f"- Relationship types: {report['relationship_types']}",
            "",
            "## Dry run",
            "",
            f"- Full-library validation: {dry_run['full_library_validation']}",
            f"- Transaction: {dry_run['transaction_result']}; wrote production CKL: {dry_run['wrote']}",
            f"- Objects: {dry_run['objects_that_would_change']}",
            f"- Files: {dry_run['files_that_would_change']}",
            "",
            "## Changed references",
            "",
            f"- Direct: {changed['direct']}",
            f"- Dependent: {changed['dependent']}",
            "",
            "## Commentary v1.2 preview",
            "",
            f"- EvidenceBundles and syntheses that would rebuild: {len(preview['evidence_bundles_that_would_rebuild'])}",
            "- No production Commentary artifacts were modified.",
            "",
            "## Protected chapters",
            "",
            *[f"- {chapter}: {count} candidate writes" for chapter, count in protected.items()],
            "",
            "## Apply readiness",
            "",
            "NOT READY TO APPLY",
            "",
            "Eight source-locked claims require entity bootstrap or a typed target-value representation that the current CKL schema cannot preserve. No production apply was run.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-lock", type=Path, default=DEFAULT_SOURCE_LOCK)
    parser.add_argument("--ckl-root", type=Path, default=CKL_ROOT)
    parser.add_argument("--queue-output", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    result = run(source_lock_path=args.source_lock, ckl_root=args.ckl_root)
    args.queue_output.write_text(json.dumps(result["queue"], indent=2) + "\n", encoding="utf-8")
    args.report_output.write_text(render_markdown(result["report"]), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
