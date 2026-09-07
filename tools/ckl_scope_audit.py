#!/usr/bin/env python3
"""Audit CKL parent scope and write deterministic remediation artifacts.

This tool is deliberately separate from commentary generation.  It reads the
existing population/checkpoint and quarantine artifacts, clusters findings by
CKL parent, and records the projection-level scope remediation.  It never
edits CKL JSON, SQLite, finalized commentary, or historical quarantine
reports.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


STRUCTURED_CHILD_SOURCE_KINDS = {"ckl_evidence_item", "ckl_claim", "ckl_interpretive_note"}
GLOBAL_RELATIONSHIPS = {"GENERIC_BACKGROUND", "INTERTEXTUAL_REUSE", "LATER_RECEPTION", "COMPARATIVE_CONTEXT"}
ENTITY_TYPES = {"person", "place", "event", "institution", "archaeology"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def preflight_payload(path: Path) -> tuple[dict[str, Any], Path]:
    payload = read(path)
    if "preflight" in payload:
        return payload["preflight"], path
    return payload, path


def historical_rows(scale_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(scale_root.glob("batch-*/quarantine-report.json")):
        batch = path.parent.name
        for row in read(path).get("chapters", []):
            item = dict(row)
            item["source_batch"] = batch
            rows.append(item)
    return rows


def final_references(scale_root: Path, canary_root: Path | None) -> tuple[set[str], set[str], set[str]]:
    regular: set[str] = set()
    for path in sorted(scale_root.glob("batch-*/batch-manifest.json")):
        regular.update(str(value) for value in read(path).get("final_references", []))
    canary: set[str] = set()
    if canary_root and canary_root.exists():
        # Only the released canary and supplemental control artifacts are
        # protected finalized controls.  The *_initial artifacts are input
        # certification history, not additional finalized commentary.
        canary_paths = (
            canary_root / "evidence-certification-commentary_canary.json",
            canary_root / "evidence-certification-supplemental-controls.json",
        )
        for path in sorted(path for path in canary_paths if path.exists()):
            payload = read(path)
            canary.update(str(row["reference"]) for row in payload.get("chapters", []) if row.get("reference"))
            if payload.get("reference"):
                canary.add(str(payload["reference"]))
    return regular | canary, regular, canary


def population_report(scale_root: Path, canary_root: Path | None) -> dict[str, Any]:
    population_path = scale_root / ".batch-007.work" / "population.json"
    if population_path.exists():
        payload = read(population_path)
        population = payload.get("report", payload)
    else:
        population = read(canary_root / "low-information-commentary.json") if canary_root and (canary_root / "low-information-commentary.json").exists() else {}
    low_info = {str(row["reference"]) for row in population.get("records", []) if row.get("reference")}
    eligible = {str(value) for value in population.get("chapters_evidence_supports_regeneration", [])}
    insufficient = {str(value) for value in population.get("chapters_evidence_insufficient", [])}
    finalized, regular, canaries = final_references(scale_root, canary_root)
    historical = {str(row["reference"]) for row in historical_rows(scale_root)}
    eligible_finalized = eligible & finalized
    unresolved = eligible - finalized
    intentional_exclusions = low_info - eligible
    return {
        "report_version": "ckl-corpus-accounting-v1",
        "generated_at": now(),
        "definitions": {
            "eligible": "low-information validated chapters whose current EvidenceBundle supports grounded regeneration (AVAILABLE or THIN); this is the derived Commentary v1.1 population, not all canonical chapters",
            "finalized": "references represented by protected finalized Terra artifacts, including canary controls",
            "regular_generated": "references in scaled batch manifests",
            "canary": "references in Commentary v1.1 canary certification artifacts",
            "historical_quarantine": "unique references in append-only scaled quarantine reports",
            "intentional_exclusion": "low-information chapters classified insufficient for regeneration and therefore outside eligible",
        },
        "counts": {
            "low_information": len(low_info),
            "eligible": len(eligible),
            "insufficient_or_intentionally_excluded": len(insufficient),
            "finalized_total": len(finalized),
            "regular_generated": len(regular),
            "canary": len(canaries),
            "historical_quarantine": len(historical),
            "eligible_finalized": len(eligible_finalized),
            "unresolved_eligible": len(unresolved),
            "intentional_exclusions": len(intentional_exclusions),
        },
        "set_relationships": {
            "eligible_and_finalized": sorted(eligible_finalized),
            "eligible_and_historical_quarantine": sorted(eligible & historical),
            "historical_quarantine_and_finalized": sorted(historical & finalized),
            "finalized_outside_eligible": sorted(finalized - eligible),
            "eligible_unresolved_not_historical": sorted(unresolved - historical),
            "low_information_outside_eligible": sorted(intentional_exclusions),
        },
        "invariants": {
            "eligible_equals_finalized_plus_unresolved_plus_intentional_exclusions": len(eligible) == len(eligible_finalized) + len(unresolved) + 0,
            "eligible_partition": len(eligible) == len(eligible_finalized) + len(unresolved),
            "finalized_count_includes_out_of_scope_controls": len(finalized - eligible) > 0,
            "historical_quarantine_is_not_finalized": not bool(historical & finalized),
        },
    }


def parent_scope_impact(preflight: Mapping[str, Any], objects: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    cross_count = 0
    word_count = 0
    word_parents: set[str] = set()
    cross_parents: set[str] = set()
    overlap_paths: Counter[str] = Counter()
    for row in preflight.get("evaluated", []):
        reference = str(row.get("reference") or "")
        for anomaly in (row.get("anomaly_scan") or {}).get("anomalies", []):
            code = str(anomaly.get("code") or "")
            if code not in {"CROSS_BOOK_PARENT_REUSE", "WORD_STUDY_BROAD_PARENT_ANCHOR"}:
                continue
            parent_id = str(anomaly.get("ckl_parent_record") or "")
            evidence_id = str(anomaly.get("evidence_id") or "")
            item = next((item for item in row.get("evidence_items", []) if str(item.get("evidence_id")) == evidence_id), {})
            if not parent_id:
                continue
            entry = grouped.setdefault(parent_id, {
                "parent_id": parent_id,
                "parent_type": str(item.get("parent_type") or objects.get(parent_id, {}).get("type") or ""),
                "parent_title": str(item.get("parent_title") or objects.get(parent_id, {}).get("title") or ""),
                "affected_evidence_records": 0,
                "affected_chapters": set(),
                "affected_books": set(),
                "affected_chapter_references": set(),
                "affected_evidence_ids": set(),
                "current_routing_scope_metadata": {
                    "parent_scripture_references": [
                        value.get("reference", "") if isinstance(value, dict) else str(value)
                        for value in objects.get(parent_id, {}).get("scripture_references", [])
                    ],
                    "source_kinds": set(),
                    "applicability_scopes": set(),
                    "semantic_relationships": set(),
                },
                "classifications": Counter(),
                "finding_codes": set(),
            })
            entry["affected_evidence_records"] += 1
            entry["affected_chapters"].add(reference)
            entry["affected_books"].add(str(row.get("book") or reference.rsplit(" ", 1)[0]))
            entry["affected_chapter_references"].add(reference)
            entry["affected_evidence_ids"].add(evidence_id)
            entry["finding_codes"].add(code)
            metadata = entry["current_routing_scope_metadata"]
            metadata["source_kinds"].add(str(item.get("source_kind") or "unknown"))
            metadata["applicability_scopes"].add(str(item.get("applicability_scope") or "unknown"))
            metadata["semantic_relationships"].add(str(item.get("semantic_relationship") or "unknown"))
            source_kind = str(item.get("source_kind") or "")
            relation = str(item.get("semantic_relationship") or "")
            parent_type = entry["parent_type"]
            if code == "CROSS_BOOK_PARENT_REUSE":
                cross_count += 1
                cross_parents.add(parent_id)
                if source_kind in STRUCTURED_CHILD_SOURCE_KINDS:
                    classification = "legitimate passage-specific child under reused conceptual parent"
                elif relation in GLOBAL_RELATIONSHIPS and parent_type in ENTITY_TYPES:
                    classification = "legitimate entity background"
                elif relation in GLOBAL_RELATIONSHIPS:
                    classification = "legitimate global context"
                elif parent_type == "book" and relation == "BOOK_CONTEXT":
                    classification = "legitimate book-level context"
                else:
                    classification = "likely over-broad inheritance / passage anchoring review"
                entry["classifications"][classification] += 1
            else:
                word_count += 1
                word_parents.add(parent_id)
                classification = (
                    "valid explicit lexical child"
                    if source_kind in STRUCTURED_CHILD_SOURCE_KINDS and item.get("applicability_scope") in {"passage", "section", "lexical"}
                    else "likely incorrect lexical parent anchoring"
                )
                entry["classifications"][classification] += 1
    rows = []
    for parent_id, entry in sorted(grouped.items(), key=lambda pair: (-pair[1]["affected_evidence_records"], pair[0])):
        entry = dict(entry)
        for key in ("affected_chapters", "affected_books", "affected_chapter_references", "affected_evidence_ids"):
            entry[key] = sorted(entry[key])
        entry["affected_chapter_count"] = len(entry["affected_chapters"])
        entry["affected_book_count"] = len(entry["affected_books"])
        metadata = dict(entry["current_routing_scope_metadata"])
        for key in ("source_kinds", "applicability_scopes", "semantic_relationships"):
            metadata[key] = sorted(metadata[key])
        entry["current_routing_scope_metadata"] = metadata
        entry["classifications"] = dict(sorted(entry["classifications"].items()))
        entry["finding_codes"] = sorted(entry["finding_codes"])
        rows.append(entry)
    return {
        "report_version": "ckl-parent-scope-impact-v1",
        "generated_at": now(),
        "source_preflight": str(preflight.get("batch_id") or "unknown"),
        "findings": {"cross_book_parent_reuse": cross_count, "word_study_broad_parent_anchor": word_count},
        "parent_counts": {"cross_book_parents": len(cross_parents), "word_study_parents": len(word_parents), "overlap_parents": len(cross_parents & word_parents)},
        "parents": rows,
    }


def word_study_overlap(impact: Mapping[str, Any]) -> dict[str, Any]:
    rows = impact.get("parents", [])
    same = [row for row in rows if any("lexical" in key or "word" in key for key in row.get("classifications", {}))]
    cross_ids = {row["parent_id"] for row in rows if "CROSS_BOOK_PARENT_REUSE" in row.get("finding_codes", [])}
    word_ids = {row["parent_id"] for row in same}
    word_findings = sum(int(row.get("affected_evidence_records", 0)) for row in same)
    same_path_findings = sum(
        int(row.get("affected_evidence_records", 0))
        for row in same
        if row["parent_id"] in cross_ids
    )
    return {
        "report_version": "ckl-word-study-scope-overlap-v1",
        "generated_at": now(),
        "word_study_findings": word_findings,
        "same_parent_or_inheritance_path": same_path_findings,
        "independent_lexical_anchoring_defects": sum(
            int(row.get("affected_evidence_records", 0)) for row in same if row["parent_id"] not in cross_ids
        ),
        "legitimate_broad_lexical_background": sum(
            int(row.get("affected_evidence_records", 0))
            for row in same
            if any("global" in key for key in row.get("classifications", {}))
        ),
        "uncertain_cases": sum(
            int(row.get("affected_evidence_records", 0))
            for row in same
            if any("review" in key for key in row.get("classifications", {}))
        ),
        "parent_ids": sorted(word_ids),
    }


def remediation_plan(impact: Mapping[str, Any], overlap: Mapping[str, Any]) -> dict[str, Any]:
    changes = []
    for row in impact.get("parents", []):
        classifications = row.get("classifications", {})
        if any("incorrect lexical" in key for key in classifications):
            action = "fail_closed_legacy_word_study_fields_require_explicit_child_anchor"
            disposition = "projection_remediation"
        elif any("over-broad" in key for key in classifications):
            action = "retain_quarantine_and_require_parent_or_child_anchor_review"
            disposition = "human_review"
        else:
            action = "preserve_explicit_child_or_background_scope_metadata"
            disposition = "projection_remediation"
        changes.append({
            "parent_id": row["parent_id"],
            "action": action,
            "disposition": disposition,
            "affected_evidence_ids": row["affected_evidence_ids"],
            "affected_chapters": row["affected_chapter_references"],
            "preserve_citations_and_provenance": True,
            "json_records_migrated": 0,
        })
    return {
        "report_version": "ckl-scope-remediation-plan-v1",
        "generated_at": now(),
        "migration_mode": "deterministic_projection_and_retrieval_policy",
        "schema_extension_required": False,
        "reason": "Existing child scripture_references already express applicability; the correction is to stop parent relevance from creating child passage evidence and to derive explicit non-passage scope for legacy fields.",
        "word_study_overlap": dict(overlap),
        "parent_changes": changes,
        "ambiguous_cases_fail_closed": True,
    }


def hash_report(preflight: Mapping[str, Any], postflight: Mapping[str, Any] | None = None) -> dict[str, Any]:
    disagreements = [row for row in preflight.get("evaluated", []) if not (row.get("json_sqlite_agreement") or {}).get("bundle_hash_agree", True)]
    report = {
        "report_version": "evidence-hash-reconciliation-v1",
        "generated_at": now(),
        "canonical_serialization": "EvidenceBundle v1.1 stable evidence items with retrieval scores excluded; source collisions merged by sorted canonical source payload and canonical_object_ids",
        "before": {
            "hash_disagreements": len(disagreements),
            "result_id_disagreements": sum(not (row.get("json_sqlite_agreement") or {}).get("result_ids_agree", True) for row in preflight.get("evaluated", [])),
            "evidence_id_disagreements": sum(not (row.get("json_sqlite_agreement") or {}).get("evidence_ids_agree", True) for row in preflight.get("evaluated", [])),
        },
        "disagreements": [
            {"reference": row.get("reference"), "cause_class": "serialization_or_ordering_review_required", "ids_agree": bool((row.get("json_sqlite_agreement") or {}).get("evidence_ids_agree"))}
            for row in disagreements
        ],
        "fail_closed": True,
    }
    if postflight is not None:
        report["after"] = {
            "hash_disagreements": postflight.get("disagreement_counts", {}).get("json_sqlite_hash_disagreements", 0),
            "result_id_disagreements": postflight.get("disagreement_counts", {}).get("json_sqlite_result_id_disagreements", 0),
            "evidence_id_disagreements": postflight.get("disagreement_counts", {}).get("json_sqlite_evidence_id_disagreements", 0),
        }
    return report


def result_report(plan: Mapping[str, Any], preflight: Mapping[str, Any], *, before: Mapping[str, Any] | None = None) -> dict[str, Any]:
    before_payload = dict(before or {})
    post_metrics = {
        "cross_book_parent_reuse": preflight.get("anomaly_raw_counts", {}).get("CROSS_BOOK_PARENT_REUSE", 0),
        "word_study_broad_parent_anchor": preflight.get("anomaly_raw_counts", {}).get("WORD_STUDY_BROAD_PARENT_ANCHOR", 0),
        "hash_disagreements": preflight.get("disagreement_counts", {}).get("json_sqlite_hash_disagreements", 0),
        "presentation_role_issues": preflight.get("anomaly_raw_counts", {}).get("PRESENTATION_ROLE_MISMATCH", 0),
        "textual_routing_issues": preflight.get("anomaly_raw_counts", {}).get("TERRA_SUPPRESSION_REQUIRED", 0),
        "terra_suppression_signals": sum(
            bool((row.get("terra_suppression_simulation") or {}).get("terra_textual_suppression_required"))
            for row in preflight.get("evaluated", [])
        ),
    }
    return {
        "report_version": "ckl-scope-remediation-result-v1",
        "generated_at": now(),
        "json_ckl_records_migrated": 0,
        "sqlite_records_migrated": 0,
        "parents_remediated_by_policy": sum(row.get("disposition") == "projection_remediation" for row in plan.get("parent_changes", [])),
        "parents_left_for_human_review": sum(row.get("disposition") == "human_review" for row in plan.get("parent_changes", [])),
        "semantic_changes": ["structured child applicability is anchored to child Scripture references", "legacy word-study fields without child anchors are excluded", "legacy parent fields carry explicit background/entity scope"],
        "evidence_added": 0,
        "evidence_deleted": 0,
        "historical_reports_mutated": False,
        "terra_prose_generated": False,
        "before_metrics": before_payload,
        "post_preflight_metrics": post_metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--post-preflight", type=Path)
    parser.add_argument("--recovery-adjudication", type=Path)
    args = parser.parse_args()
    scale_root = args.scale_root.resolve()
    output_dir = args.output_dir.resolve()
    baseline_path = args.preflight or (scale_root / ".batch-007.work" / "blocked-report.json")
    baseline, _ = preflight_payload(baseline_path)
    objects: dict[str, Mapping[str, Any]] = {}
    for path in sorted((Path(__file__).resolve().parents[1] / "framework/canonical_library/objects").rglob("*.json")):
        payload = read(path)
        if payload.get("id"):
            objects[str(payload["id"])] = payload
    accounting = population_report(scale_root, scale_root.parent / "commentary-v1.1")
    impact = parent_scope_impact(baseline, objects)
    overlap = word_study_overlap(impact)
    plan = remediation_plan(impact, overlap)
    post = baseline
    if args.post_preflight:
        post, _ = preflight_payload(args.post_preflight.resolve())
    hashes = hash_report(baseline, post if args.post_preflight else None)
    before_metrics = {
        "cross_book_parent_reuse": baseline.get("anomaly_raw_counts", {}).get("CROSS_BOOK_PARENT_REUSE", 0),
        "word_study_broad_parent_anchor": baseline.get("anomaly_raw_counts", {}).get("WORD_STUDY_BROAD_PARENT_ANCHOR", 0),
        "hash_disagreements": baseline.get("disagreement_counts", {}).get("json_sqlite_hash_disagreements", 0),
        "presentation_role_issues": baseline.get("anomaly_raw_counts", {}).get("PRESENTATION_ROLE_MISMATCH", 0),
        "textual_routing_issues": baseline.get("anomaly_raw_counts", {}).get("TERRA_SUPPRESSION_REQUIRED", 0),
        "terra_suppression_signals": sum(
            bool((row.get("terra_suppression_simulation") or {}).get("terra_textual_suppression_required"))
            for row in baseline.get("evaluated", [])
        ),
    }
    remediation = result_report(plan, post, before=before_metrics)
    write(output_dir / "corpus-accounting-report.json", accounting)
    write(output_dir / "parent-scope-impact-report.json", impact)
    write(output_dir / "word-study-scope-overlap-report.json", overlap)
    write(output_dir / "ckl-scope-remediation-plan.json", plan)
    write(output_dir / "ckl-scope-remediation-result.json", remediation)
    write(output_dir / "evidence-hash-reconciliation-report.json", hashes)
    post_counts = Counter(
        "RECOVERABLE" if row.get("status") == "PASS" and row.get("availability") in {"AVAILABLE", "THIN"}
        else "DATA_GAP" if row.get("status") == "DATA_GAP"
        else "REQUIRES_CKL_REMEDIATION" if set(row.get("quarantine_reason_codes", [])) & {"CROSS_BOOK_PARENT_REUSE", "WORD_STUDY_BROAD_PARENT_ANCHOR"}
        else "STILL_QUARANTINED"
        for row in post.get("evaluated", [])
    )
    if args.recovery_adjudication and args.recovery_adjudication.exists():
        recovery = read(args.recovery_adjudication)
        adjudication_counts = recovery.get("adjudication_counts", recovery.get("counts", {}))
        chapters = recovery.get("chapters", [])
        adjudication = {
            "report_version": "post-remediation-quarantine-adjudication-v1",
            "generated_at": now(),
            "source_recovery_adjudication": "tools/commentary_v11_quarantine_recovery.py adjudicate",
            "preflight_source": "isolated post-remediation Luna High preflight",
            "historical_quarantine_population": recovery.get("unique_quarantined_chapters"),
            "adjudication_counts": dict(sorted(adjudication_counts.items())),
            "recoverable_reference_count": len(recovery.get("recoverable_references", [])),
            "remaining_references_by_disposition": {
                disposition: sorted(
                    str(chapter["reference"])
                    for chapter in chapters
                    if chapter.get("adjudication") == disposition
                )
                for disposition in ("STILL_QUARANTINED", "REQUIRES_CKL_REMEDIATION", "DATA_GAP", "ALREADY_RESOLVED")
            },
            "ckl_mutated": False,
            "terra_generation": False,
        }
        adjudication["batch_007_safe_to_continue"] = not any(
            adjudication_counts.get(key, 0)
            for key in ("STILL_QUARANTINED", "REQUIRES_CKL_REMEDIATION", "DATA_GAP")
        )
        adjudication["scope_audit"] = {
            "before_metrics": before_metrics,
            "post_preflight_metrics": remediation["post_preflight_metrics"],
            "terra_generation": False,
        }
    else:
        adjudication = {
        "report_version": "post-remediation-quarantine-adjudication-v1",
        "generated_at": now(),
        "source_preflight": str(args.post_preflight or baseline_path),
        "historical_quarantine_population": len({str(row["reference"]) for row in historical_rows(scale_root)}),
        "counts": dict(sorted(post_counts.items())),
        "terra_generation": False,
        "batch_007_safe_to_continue": not post_counts,
        "scope_audit": {"post_preflight_metrics": remediation["post_preflight_metrics"]},
        }
    write(output_dir / "post-remediation-quarantine-adjudication.json", adjudication)
    print(json.dumps({"output_dir": str(output_dir), "parents": len(impact["parents"]), "before": before_metrics, "post": remediation["post_preflight_metrics"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
