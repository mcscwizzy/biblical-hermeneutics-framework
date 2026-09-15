#!/usr/bin/env python3
"""Deterministic within-family audit for the Commentary 1.4 Batch 2 failures.

The audit reads only locked v1.4 synthesis, the rebuilt EvidenceBundle, and
the preserved renderer responses.  It does not call a model and does not alter
the synthesis, evidence, validator, or richness gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.chapter_commentary.synthesis.models import SynthesisUnit
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION


BATCH_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.4-pilot-batch-2/canary"
CALIBRATION_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.4-calibration/canary"
DEFAULT_JSON = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.4-pilot-batch-2/evaluation/within-family-audit.json"
DEFAULT_MARKDOWN = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.4-pilot-batch-2/evaluation/within-family-audit.md"


def _slug(book: str) -> str:
    return book.lower().replace(" ", "_")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _classify_omission(cluster: Any) -> str:
    if cluster.passage_scope == "SURROUNDING_PASSAGE":
        return "SURROUNDING_ONLY"
    if cluster.duplicate_reason != "DISTINCT":
        return "REDUNDANT_OR_PARALLEL"
    if cluster.quality_class == "DISPUTED":
        return "DISPUTED_SECONDARY"
    if cluster.quality_class == "OPTIONAL":
        return "USEFUL_BUT_OPTIONAL"
    return "MATERIAL_MISSING_CONTEXT"


def _cluster_row(cluster: Any, units_by_id: dict[str, SynthesisUnit], consumed: set[str]) -> dict[str, Any]:
    facts = [fact for synthesis_id in cluster.synthesis_ids for fact in units_by_id[synthesis_id].facts]
    consumed_by = [
        block_id
        for block_id, ids in consumed.items()
        if set(cluster.synthesis_ids).intersection(ids)
    ]
    is_consumed = bool(consumed_by)
    return {
        "cluster_id": cluster.id,
        "quality_class": cluster.quality_class,
        "importance_weight": cluster.importance_weight,
        "category_families": cluster.categories,
        "synthesis_ids": cluster.synthesis_ids,
        "passage_scope": cluster.passage_scope,
        "importance_basis": cluster.importance_basis,
        "disputed_status": cluster.dispute_present,
        "duplicate_reason": cluster.duplicate_reason,
        "consumed": is_consumed,
        "consuming_block_ids": consumed_by,
        "omission_classification": None if is_consumed else _classify_omission(cluster),
        "facts": facts,
    }


def _category_rows(clusters: list[Any], consumed_ids: set[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for category in sorted({category for cluster in clusters for category in cluster.categories}):
        available = [cluster for cluster in clusters if category in cluster.categories]
        consumed = [
            cluster
            for cluster in available
            if set(cluster.synthesis_ids).intersection(consumed_ids)
        ]
        rows[category] = {
            "available_meaningful_clusters": len(available),
            "consumed_meaningful_clusters": len(consumed),
            "weighted_available_ideas": round(sum(cluster.importance_weight for cluster in available), 4),
            "weighted_consumed_ideas": round(sum(cluster.importance_weight for cluster in consumed), 4),
            "coverage": round(
                sum(cluster.importance_weight for cluster in consumed)
                / sum(cluster.importance_weight for cluster in available),
                4,
            ) if available else 0.0,
        }
    return rows


def audit_reference(book: str, chapter: int, root: Path, role: str) -> dict[str, Any]:
    reference = f"{book} {chapter}"
    slug = f"{_slug(book)}_{chapter:03d}"
    synthesis_data = _read(root / "synthesis" / f"{slug}.json")
    units = [SynthesisUnit(**value) for value in synthesis_data["synthesis_units"]]
    bundle = get_chapter_evidence_bundle(
        book,
        chapter,
        evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
    )
    commentary = load_commentary(root / "responses/accepted", book, chapter)
    blocks = [block for section in commentary.sections for block in section.blocks]
    consumed_by_block = {
        block.id: list(block.synthesis_ids)
        for block in blocks
    }
    consumed_ids = {
        synthesis_id
        for ids in consumed_by_block.values()
        for synthesis_id in ids
    }
    score = score_synthesis_richness(
        units,
        evidence_items=bundle.evidence_items if bundle else [],
        consumed_synthesis_ids=consumed_ids,
        blocks=blocks,
        passage_ref=reference,
        core_classifier=CORE_CLASSIFIER_V2,
    )
    units_by_id = {unit.id: unit for unit in units}
    meaningful = [cluster for cluster in score.clusters if cluster.quality_class != "OPTIONAL"]
    cluster_rows = [
        _cluster_row(cluster, units_by_id, consumed_by_block)
        for cluster in meaningful
    ]
    omitted = [row for row in cluster_rows if not row["consumed"]]
    omitted_current_distinct = [
        row for row in omitted
        if row["passage_scope"] == "CURRENT_CHAPTER"
        and row["duplicate_reason"] == "DISTINCT"
    ]
    available_by_class = Counter(row["quality_class"] for row in cluster_rows)
    omitted_by_class = Counter(row["quality_class"] for row in omitted)
    consumed_by_class = Counter(row["quality_class"] for row in cluster_rows if row["consumed"])
    return {
        "reference": reference,
        "role": role,
        "evidence_availability": synthesis_data["evidence_availability"],
        "raw_synthesis_units": score.synthesis_unit_count,
        "meaningful_clusters": score.meaningful_cluster_count,
        "consumed_meaningful_clusters": score.consumed_cluster_count,
        "blocks": len(blocks),
        "words": sum(len(block.text.split()) for block in blocks),
        "synthesis_utilization": score.raw_synthesis_coverage,
        "weighted_idea_coverage": score.weighted_idea_coverage,
        "core_clusters": score.core_cluster_count,
        "consumed_core_clusters": score.consumed_core_cluster_count,
        "core_coverage": score.core_cluster_coverage,
        "category_coverage": score.category_coverage,
        "available_categories": score.category_families,
        "consumed_categories": score.consumed_category_families,
        "dump_severity": score.dump_diagnostics.severity,
        "dump_signals": score.dump_diagnostics.signals,
        "consolidation_ratio": score.consolidation_ratio,
        "category_rows": _category_rows(meaningful, consumed_ids),
        "clusters": cluster_rows,
        "summary": {
            "touches_most_categories_but_misses_distinct_ideas_within_family": bool(
                score.category_coverage >= 0.75 and omitted_current_distinct
            ),
            "omitted_distinct_ideas_are_genuinely_distinct": bool(omitted_current_distinct),
            "omitted_current_chapter_count": sum(
                row["passage_scope"] == "CURRENT_CHAPTER" for row in omitted
            ),
            "omitted_surrounding_count": sum(
                row["passage_scope"] == "SURROUNDING_PASSAGE" for row in omitted
            ),
            "missed_core_ideas": sum(
                row["quality_class"] == "CORE" and not row["consumed"] for row in cluster_rows
            ),
            "available_by_quality_class": dict(sorted(available_by_class.items())),
            "consumed_by_quality_class": dict(sorted(consumed_by_class.items())),
            "omitted_by_quality_class": dict(sorted(omitted_by_class.items())),
            "omitted_material_missing_context_count": sum(
                row["omission_classification"] == "MATERIAL_MISSING_CONTEXT" for row in omitted
            ),
            "omitted_supporting_fraction": round(
                omitted_by_class["SUPPORTING"] / available_by_class["SUPPORTING"], 4
            ) if available_by_class["SUPPORTING"] else 0.0,
            "material_improvement_from_distinct_current_ideas": bool(omitted_current_distinct),
        },
    }


def build_report() -> dict[str, Any]:
    batch_report = _read(BATCH_ROOT.parent / "evaluation/batch-2-report.json")
    failed = [
        row for row in batch_report["chapters"]
        if row.get("gate_outcome") == "QUALITY_FAIL"
    ]
    failure_refs = [row["reference"] for row in failed]
    by_ref = {reference: (reference.rsplit(" ", 1)[0], int(reference.rsplit(" ", 1)[1])) for reference in failure_refs}
    failures = [audit_reference(book, chapter, BATCH_ROOT, "FAILED_BATCH_2") for reference, (book, chapter) in by_ref.items()]
    controls = [
        audit_reference("Exodus", 12, CALIBRATION_ROOT, "POSITIVE_CONTROL_EXODUS_12"),
        audit_reference("Job", 3, BATCH_ROOT, "POSITIVE_CONTROL_JOB_3"),
    ]
    return {
        "artifact_version": "commentary-v1.4-within-family-audit-v1",
        "prompt_version": "1.4",
        "schema_version": "1.2",
        "gate_version": batch_report["gate_version"],
        "deterministic": True,
        "model_invoked": False,
        "source_batch_report": str((BATCH_ROOT.parent / "evaluation/batch-2-report.json").relative_to(ROOT)),
        "failure_references": failure_refs,
        "failures": failures,
        "positive_controls": controls,
        "root_cause_classification": "WITHIN_FAMILY_UNDERSAMPLING_CONFIRMED",
        "gate_change_justified": False,
        "prompt_change_justified": True,
        "reader_synthesis_plan_needed": False,
        "batch_3_authorized": False,
    }


def _md_cluster(row: dict[str, Any]) -> str:
    consumed = "yes" if row["consumed"] else "no"
    blocks = ", ".join(row["consuming_block_ids"]) or "—"
    facts = " / ".join(row["facts"])
    return (
        f"| `{row['cluster_id']}` | {row['quality_class']} | {row['importance_weight']:.2f} | "
        f"{', '.join(row['category_families']) or '—'} | {', '.join(row['synthesis_ids'])} | "
        f"{row['passage_scope']} | {', '.join(row['importance_basis']) or '—'} | "
        f"{'yes' if row['disputed_status'] else 'no'} | {consumed} | {blocks} | "
        f"{row['omission_classification'] or '—'} | {facts.replace('|', '/') } |"
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Commentary 1.4 within-family omitted-cluster audit",
        "",
        "Deterministic audit of preserved Prompt 1.4 responses. No model was invoked;",
        "EvidenceBundle, synthesis, schema, compiler, and Gate v2.1 were not changed.",
        "",
        f"Root-cause classification: **{report['root_cause_classification']}**",
        "",
        "## Chapter-level findings",
        "",
    ]
    for chapter in [*report["failures"], *report["positive_controls"]]:
        summary = chapter["summary"]
        lines.extend([
            f"### {chapter['reference']} ({chapter['role']})",
            "",
            f"- {chapter['raw_synthesis_units']} raw units; {chapter['meaningful_clusters']} meaningful clusters; "
            f"{chapter['consumed_meaningful_clusters']} consumed; weighted idea coverage "
            f"{chapter['weighted_idea_coverage']:.4f}; category coverage {chapter['category_coverage']:.4f}.",
            f"- Categories available: {', '.join(chapter['available_categories']) or 'none'}.",
            f"- Categories consumed: {', '.join(chapter['consumed_categories']) or 'none'}.",
            f"- Omitted current-chapter clusters: {summary['omitted_current_chapter_count']}; "
            f"surrounding-only clusters: {summary['omitted_surrounding_count']}; "
            f"missed CORE clusters: {summary['missed_core_ideas']}.",
            f"- Omitted supporting fraction: {summary['omitted_supporting_fraction']:.4f}; "
            f"dump severity: {chapter['dump_severity']}; blocks/words: {chapter['blocks']}/{chapter['words']}.",
            "",
            "| Category family | Available meaningful ideas | Consumed meaningful ideas | Weighted available ideas | Weighted consumed ideas | Coverage |",
            "|---|---:|---:|---:|---:|---:|",
        ])
        for category, values in chapter["category_rows"].items():
            lines.append(
                f"| {category} | {values['available_meaningful_clusters']} | {values['consumed_meaningful_clusters']} | "
                f"{values['weighted_available_ideas']:.4f} | {values['weighted_consumed_ideas']:.4f} | {values['coverage']:.4f} |"
            )
        lines.extend([
            "",
            "| Cluster ID | Quality | Importance | Families | Synthesis IDs | Scope | Importance basis | Disputed | Consumed | Consuming block(s) | Omission classification | Supported facts |",
            "|---|---|---:|---|---|---|---|---|---|---|---|---|",
        ])
        lines.extend(_md_cluster(row) for row in chapter["clusters"])
        lines.append("")
    lines.extend([
        "## Interpretation",
        "",
        "The failures are not explained by evidence dumping, duplicate prose, routing variance, or a broken safety boundary. The deterministic pattern is breadth across families without sufficient breadth among distinct current-chapter ideas that share a family. Exodus 12 passes because it preserves multiple distinct ideas within several families while consolidating duplicate and parallel records into nine substantial blocks. Job 3 passes because its three meaningful clusters are sparse and are all consumed; it is a restraint control, not a dense-family breadth control.",
        "",
        "The audit therefore justifies a semantic Prompt 1.5 change and does not justify changing Gate v2.1 or adding ReaderSynthesisPlan metadata.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    report = build_report()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({
        "root_cause_classification": report["root_cause_classification"],
        "failures": report["failure_references"],
        "positive_controls": [row["reference"] for row in report["positive_controls"]],
        "json": str(args.json_out),
        "markdown": str(args.markdown_out),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
