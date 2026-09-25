"""Build and dry-run the verified geography candidate queue without applying it."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.canonical_library.expansion import (
    CanonicalStructuralDuplicateConflict, apply_candidate_queue,
)
from framework.canonical_library.geography_candidates import build_geography_candidate_queue
from framework.canonical_library.loader import CanonicalLibrary
from framework.canonical_library.schema import CATEGORY_FOLDERS


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
    try:
        transaction = apply_candidate_queue(ckl_root, staged, write=False)
    except CanonicalStructuralDuplicateConflict as exc:
        return _structural_conflict_report(source_locks, queue, str(exc))
    except ValueError as exc:
        if not str(exc).startswith("bootstrap "):
            raise
        return _bootstrap_conflict_report(source_locks, queue, str(exc))
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
    commentary_preview = [
        {"reference": reference, "pipeline": "commentary-v1.2-enrichment", "operation": "would-rebuild"}
        for reference in preview_references
    ]

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


def _structural_conflict_report(
    source_locks: Mapping[str, Any], queue: dict[str, Any], message: str,
) -> dict[str, Any]:
    parts = message.split(":", 2)
    offending_parent = parts[1].strip() if len(parts) > 1 else ""
    for record in queue["candidates"]:
        if record["outcome"] != "NEW":
            record.update(validation_result="NOT_STAGED", dedup_result="NOT_STAGED", leakage_result="NOT_STAGED")
            continue
        if record.get("target_ckl_object_id") == offending_parent:
            record.update(
                outcome="CONFLICTING", validation_result="FAIL",
                dedup_result="canonical-structural-duplicate-conflict",
                transaction_classification="canonical-structural-duplicate-conflict",
                rejection_reason=message, leakage_result="NOT_STAGED",
            )
        else:
            record.update(
                outcome="REJECTED", validation_result="NOT_STAGED",
                dedup_result="NOT_STAGED", rejection_reason="transaction-blocked-by-canonical-structural-duplicate",
                leakage_result="NOT_STAGED",
            )
    report = _report(
        source_locks, queue,
        transaction=SimpleNamespace(changed_object_ids=[], simulated_objects={}, wrote=False),
        direct=[], dependent=[], direct_chapters=[], dependent_chapters=[], commentary_preview=[],
    )
    report["dry_run"].update(
        full_library_validation="FAIL", transaction_result="BLOCKED",
        transaction_blocker=message,
    )
    queue["dry_run"] = report
    return {"queue": queue, "report": report}


def _bootstrap_conflict_report(
    source_locks: Mapping[str, Any], queue: dict[str, Any], message: str,
) -> dict[str, Any]:
    def owns_collision(record: Mapping[str, Any]) -> bool:
        bootstraps = record.get("candidate_payload", {}).get("entity_bootstraps", [])
        for bootstrap in bootstraps:
            if message.startswith("bootstrap title collision: "):
                if str(bootstrap.get("title")) == message.removeprefix("bootstrap title collision: ").split(" with ", 1)[0]:
                    return True
            if message.startswith("bootstrap alias collision: "):
                if message.removeprefix("bootstrap alias collision: ").split(" with ", 1)[0] in bootstrap.get("aliases", []):
                    return True
            if message.startswith("bootstrap id conflict: "):
                if str(bootstrap.get("id")) == message.removeprefix("bootstrap id conflict: "):
                    return True
            if message.startswith("bootstrap source-identity collision: "):
                source_id = message.removeprefix("bootstrap source-identity collision: ")
                if any(source.get("id") == source_id for source in bootstrap.get("sources", [])):
                    return True
            if message.endswith(f": {bootstrap.get('id')}") or message.startswith(f"bootstrap validation failed for {bootstrap.get('id')}: "):
                return True
        return False
        return False

    for record in queue["candidates"]:
        if record["outcome"] == "NEW":
            if owns_collision(record):
                record.update(
                    outcome="CONFLICTING", validation_result="FAIL",
                    dedup_result="bootstrap-collision",
                    transaction_classification="bootstrap-collision",
                    rejection_reason=message, leakage_result="NOT_STAGED",
                )
            else:
                record.update(
                    outcome="REJECTED", validation_result="NOT_STAGED",
                    dedup_result="NOT_STAGED",
                    transaction_classification="transaction-blocked",
                    rejection_reason="transaction-blocked-by-bootstrap-collision",
                    leakage_result="NOT_STAGED",
                )
        else:
            record.update(validation_result="NOT_STAGED", dedup_result="NOT_STAGED", leakage_result="NOT_STAGED")
    report = _report(
        source_locks, queue,
        transaction=SimpleNamespace(changed_object_ids=[], simulated_objects={}, wrote=False),
        direct=[], dependent=[], direct_chapters=[], dependent_chapters=[], commentary_preview=[],
    )
    report["dry_run"].update(
        full_library_validation="FAIL", transaction_result="BLOCKED",
        transaction_blocker=message,
    )
    queue["dry_run"] = report
    return {"queue": queue, "report": report}


def _apply_decisions(records: list[dict[str, Any]], decisions: Mapping[str, Any]) -> None:
    seen_by_target: dict[str, str] = {}
    contributors: dict[tuple[str, str], list[str]] = {}
    for source_lock_id, decision in decisions.items():
        survivor = str(decision.survivor_evidence_id or "")
        if survivor:
            parent_id = str(decision.candidate.get("target_object_id") or "")
            contributors.setdefault((parent_id, survivor), []).append(str(source_lock_id))
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
        classification = str(decision.classification or "rejected")
        record["validation_result"] = "PASS" if decision.accepted else "FAIL"
        record["validation_reasons"] = reasons
        record["transaction_classification"] = classification
        if decision.survivor_evidence_id:
            record["survivor_evidence_id"] = decision.survivor_evidence_id
            record["contributing_source_lock_ids"] = sorted(contributors.get(
                (str(record["target_ckl_object_id"]), decision.survivor_evidence_id), [],
            ))
        if decision.contributing_source_ids:
            record["contributing_source_ids"] = list(decision.contributing_source_ids)
        if decision.provenance_conflicts:
            record["provenance_conflicts"] = list(decision.provenance_conflicts)
        record["leakage_result"] = "PASS" if not any(
            value.startswith(("geography-target", "scripture-anchor"))
            for value in reasons
        ) else "REJECTED"
        if not decision.accepted:
            if classification in {"identity-conflict", "provenance-conflict", "canonical-structural-duplicate-conflict"}:
                record["outcome"] = "CONFLICTING"
            elif classification == "duplicate-pilot":
                record["outcome"] = "DUPLICATE_PILOT"
            elif classification == "duplicate-existing" or "semantic-duplicate" in reasons:
                record["outcome"] = "DUPLICATE_EXISTING"
            else:
                record["outcome"] = "REJECTED"
            record["dedup_result"] = classification if record["outcome"] != "REJECTED" else "not-duplicate"
            record["rejection_reason"] = "; ".join(reasons)
            continue
        if classification.startswith("duplicate-existing"):
            record["outcome"] = "DUPLICATE_EXISTING"
            record["dedup_result"] = classification
            continue
        if classification.startswith("duplicate-pilot"):
            record["outcome"] = "DUPLICATE_PILOT"
            record["dedup_result"] = classification
            continue
        target = str(record["target_ckl_object_id"])
        if target in seen_by_target:
            record["outcome"] = "COMPLEMENTARY"
            record["dedup_result"] = "complementary"
            record["complementary_to"] = seen_by_target[target]
        else:
            record["outcome"] = "NEW"
            record["dedup_result"] = "new"
            seen_by_target[target] = str(record["source_lock_id"])


def _direct_references(records: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(anchor["reference"])
            for record in records
            if record["outcome"] in {"NEW", "COMPLEMENTARY"}
            or record.get("dedup_result") in {
                "duplicate-existing-provenance-merged", "duplicate-pilot-provenance-merged",
            }
            for anchor in record["scripture_anchors"]
        }
    )


def _chapters_from_records(records: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(record["chapter_reference"])
            for record in records
            if record["outcome"] in {"NEW", "COMPLEMENTARY"}
            or record.get("dedup_result") in {
                "duplicate-existing-provenance-merged", "duplicate-pilot-provenance-merged",
            }
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
    accepted_records = [item for item in records if item.get("validation_result") == "PASS"]
    merged = [item for item in records if item.get("dedup_result", "").endswith("provenance-merged")]
    staged_ids = {
        item["id"] for record in records for item in record.get("candidate_payload", {}).get("entity_bootstraps", [])
        if record.get("validation_result") == "PASS"
    }
    relationship_types = Counter(str(item["relationship_type"]) for item in accepted_records)
    locators = [lock for item in accepted_records for lock in item["source_locks"]]
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
            "accepted": len(accepted_records),
            "insertions": len(resolved),
            "rejected": outcomes["REJECTED"],
            "duplicate_existing": outcomes["DUPLICATE_EXISTING"],
            "duplicate_pilot": outcomes["DUPLICATE_PILOT"],
            "complementary": outcomes["COMPLEMENTARY"],
            "conflicting": outcomes["CONFLICTING"],
            "duplicate_existing_provenance_merged": sum(item["outcome"] == "DUPLICATE_EXISTING" for item in merged),
            "duplicate_pilot_provenance_merged": sum(item["outcome"] == "DUPLICATE_PILOT" for item in merged),
        },
        "relationship_types": dict(sorted(relationship_types.items())),
        "entity_resolution": {
            "resolved_subjects": sum(bool(item["subject"].get("entity_id")) for item in accepted_records),
            "resolved_targets": sum(bool(item["target"].get("entity_id")) for item in accepted_records),
            "unresolved_records": [
                {"source_lock_id": item["source_lock_id"], "reason": item.get("rejection_reason")}
                for item in records
                if item["outcome"] == "REJECTED"
            ],
            "collisions_detected": [
                {"source_lock_id": item["source_lock_id"], "classification": item.get("transaction_classification"),
                 "provenance_conflicts": item.get("provenance_conflicts", [])}
                for item in records if item["outcome"] == "CONFLICTING"
            ],
        },
        "temporal": {
            "time_qualified_candidates": len(accepted_records),
            "preservation_verified": all(
                item["candidate_payload"]["evidence_item"]["temporal_scope"] == item["temporal_scope"]
                for item in accepted_records
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
            "staged_bootstrap_count": len(staged_ids),
            "staged_manifest_object_count": len(transaction.simulated_objects),
            "files_that_would_change": sorted({
                path for object_id in transaction.changed_object_ids
                if (path := next((
                    record["target_ckl_file"] for record in records
                    if record.get("target_ckl_object_id") == object_id and record.get("target_ckl_file")
                ), "") or next((
                    f"framework/canonical_library/objects/{CATEGORY_FOLDERS[item['type']]}/{item['id']}.json"
                    for record in records
                    for item in record.get("candidate_payload", {}).get("entity_bootstraps", [])
                    if item["id"] == object_id
                ), ""))
            }),
            "claims_that_would_be_inserted": [item["source_lock_id"] for item in resolved],
            "provenance_merges": [
                {"source_lock_id": item["source_lock_id"],
                 "survivor_evidence_id": item.get("survivor_evidence_id"),
                 "contributing_source_ids": item.get("contributing_source_ids", []),
                 "contributing_source_lock_ids": item.get("contributing_source_lock_ids", [])}
                for item in merged
            ],
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
            "preview_mode": "reference-only",
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
            f"- New or complementary insertions: {candidates['insertions']}",
            f"- Provenance merges: existing {candidates['duplicate_existing_provenance_merged']}; pilot {candidates['duplicate_pilot_provenance_merged']}",
            f"- Relationship types: {report['relationship_types']}",
            "",
            "## Dry run",
            "",
            f"- Full-library validation: {dry_run['full_library_validation']}",
            f"- Transaction: {dry_run['transaction_result']}; wrote production CKL: {dry_run['wrote']}",
            f"- Objects: {dry_run['objects_that_would_change']}",
            f"- Staged bootstrap objects: {dry_run['staged_bootstrap_count']}; simulated manifest objects: {dry_run['staged_manifest_object_count']}",
            f"- Files: {dry_run['files_that_would_change']}",
            f"- Provenance merge details: {dry_run['provenance_merges']}",
            f"- Transaction blocker: {dry_run.get('transaction_blocker', 'none')}",
            "",
            "## Changed references",
            "",
            f"- Direct: {changed['direct']}",
            f"- Dependent: {changed['dependent']}",
            "",
            "## Commentary v1.2 preview",
            "",
            f"- Preview mode: {preview['preview_mode']}; synthesis was not recomputed.",
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
            f"{candidates['rejected']} source-locked claims remain rejected. No production apply was run; bootstrap-bearing transactions remain dry-run only.",
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
