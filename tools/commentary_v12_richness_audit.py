#!/usr/bin/env python3
"""Audit dense synthesis denominators and proposed v2 richness metrics.

The command is read-only with respect to CKL, v1.1, synthesis, and commentary
inputs.  It writes only the requested diagnostic report artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.richness_clusters import (
    ProposedGateThresholds,
    proposed_gate_passes,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION


CANDIDATE_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment"
CANARY_ROOT = CANDIDATE_ROOT / "canary"
CANARY_REFERENCES = (
    ("Genesis", 1), ("Leviticus", 16), ("Ruth", 3), ("Psalms", 1),
    ("1 Samuel", 21), ("1 Samuel", 28), ("2 Samuel", 6), ("2 Samuel", 24),
    ("1 Chronicles", 8), ("John", 1), ("Isaiah", 6), ("Revelation", 12),
    ("Numbers", 3),
)


def inventory() -> list[dict[str, Any]]:
    rows = []
    for book_row in bible.list_books():
        book = str(book_row["name"])
        for chapter in range(1, int(book_row["chapters"]) + 1):
            bundle = get_chapter_evidence_bundle(
                book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
            )
            if bundle is None:
                raise RuntimeError(f"unable to build EvidenceBundle for {book} {chapter}")
            synthesis = compile_chapter_synthesis(bundle, book=book, chapter=chapter)
            score = score_synthesis_richness(
                synthesis.synthesis_units,
                evidence_items=bundle.evidence_items,
            )
            kinds = Counter(unit.kind for unit in synthesis.synthesis_units)
            scopes = Counter(unit.passage_scope for unit in synthesis.synthesis_units)
            rows.append(
                {
                    "reference": f"{book} {chapter}",
                    "book": book,
                    "chapter": chapter,
                    "synthesis_unit_count": len(synthesis.synthesis_units),
                    "evidence_item_count": len(bundle.evidence_items),
                    "unique_evidence_ids": len({item.id for item in bundle.evidence_items}),
                    "units_per_evidence_item": round(
                        len(synthesis.synthesis_units) / len(bundle.evidence_items), 4
                    ) if bundle.evidence_items else None,
                    "unit_kind_counts": dict(sorted(kinds.items())),
                    "current_chapter_unit_count": scopes.get("CURRENT_CHAPTER", 0),
                    "surrounding_passage_unit_count": scopes.get("SURROUNDING_PASSAGE", 0),
                    "availability": synthesis.evidence_availability,
                    "distinct_idea_cluster_count": len(score.clusters),
                    "meaningful_idea_cluster_count": score.meaningful_cluster_count,
                    "duplicate_reason_counts": dict(
                        Counter(cluster.duplicate_reason for cluster in score.clusters)
                    ),
                }
            )
    return rows


def canary_report() -> list[dict[str, Any]]:
    comparison = json.loads((CANARY_ROOT / "canary-comparison.json").read_text(encoding="utf-8"))
    by_reference = {row["reference"]: row for row in comparison["chapters"]}
    result = []
    for book, chapter in CANARY_REFERENCES:
        reference = f"{book} {chapter}"
        locked = by_reference[reference]
        synthesis = json.loads(
            (CANARY_ROOT / "synthesis" / f"{book.lower().replace(' ', '_')}_{chapter:03d}.json").read_text(
                encoding="utf-8"
            )
        )
        accepted_path = CANARY_ROOT / "responses/accepted" / f"{book.lower().replace(' ', '_')}_{chapter:03d}.json"
        commentary = load_commentary(CANARY_ROOT / "responses/accepted", book, chapter) if accepted_path.is_file() else None
        bundle = get_chapter_evidence_bundle(
            book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
        )
        if bundle is None:
            raise RuntimeError(f"unable to rebuild {reference}")
        units = [
            _unit_from_dict(value) for value in synthesis.get("synthesis_units", [])
        ]
        consumed_ids = [
            synthesis_id
            for section in (commentary.sections if commentary else [])
            for block in section.blocks
            for synthesis_id in block.synthesis_ids
        ]
        blocks = [
            block
            for section in (commentary.sections if commentary else [])
            for block in section.blocks
        ]
        score = score_synthesis_richness(
            units,
            evidence_items=bundle.evidence_items,
            consumed_synthesis_ids=consumed_ids,
            blocks=blocks,
            passage_ref=reference,
        )
        after = locked.get("after") or {}
        clean = (
            locked.get("validation_status") == "validated"
            and not locked.get("validation_errors")
            and not locked.get("synthesis_validation_errors")
            and not locked.get("rejection_codes")
            and locked.get("evidence_and_synthesis_locks_match")
        )
        proposed_pass, proposed_checks = proposed_gate_passes(
            score=score,
            evidence_availability=locked["before"]["evidence_availability"],
            validation_clean=clean,
            boilerplate_detected=bool(after.get("boilerplate_detected")),
            evidence_use_delta=int(locked["deltas"].get("evidence_use_delta") or 0),
            boundary_repetition_ratio=float(after.get("opening_closing_lexical_overlap") or 0),
        )
        result.append(
            {
                "reference": reference,
                "current_gate_status": comparison["status"],
                "current_richness": after.get("richness_status"),
                "raw_synthesis_count": score.synthesis_unit_count,
                "distinct_idea_cluster_count": len(score.clusters),
                "meaningful_idea_cluster_count": score.meaningful_cluster_count,
                "core_cluster_count": score.core_cluster_count,
                "consumed_synthesis_count": score.consumed_synthesis_count,
                "consumed_idea_cluster_count": score.consumed_cluster_count,
                "consumed_core_cluster_count": score.consumed_core_cluster_count,
                "raw_synthesis_coverage": score.raw_synthesis_coverage,
                "idea_cluster_coverage": score.idea_cluster_coverage,
                "weighted_idea_coverage": score.weighted_idea_coverage,
                "core_cluster_coverage": score.core_cluster_coverage,
                "category_coverage": score.category_coverage,
                "blocks": after.get("commentary_block_count"),
                "words": after.get("commentary_prose_word_count"),
                "evidence_ids": after.get("unique_evidence_ids_consumed"),
                "consolidation_ratio": score.consolidation_ratio,
                "evidence_dump": score.dump_diagnostics.to_dict(),
                "proposed_gate_pass": proposed_pass,
                "proposed_gate_checks": proposed_checks,
            }
        )
    return result


def build_report() -> dict[str, Any]:
    rows = inventory()
    bucket_order = ("0", "1-5", "6-10", "11-20", "21-40", "41+")
    buckets = Counter(_bucket(row["synthesis_unit_count"]) for row in rows)
    unit_kind_totals = Counter(
        kind
        for row in rows
        for kind, count in row["unit_kind_counts"].items()
        for _ in range(count)
    )
    top = sorted(rows, key=lambda row: (-row["synthesis_unit_count"], row["reference"]))[:50]
    top_by_density = sorted(
        [row for row in rows if row["units_per_evidence_item"] is not None],
        key=lambda row: (-row["units_per_evidence_item"], -row["synthesis_unit_count"], row["reference"]),
    )[:50]
    dense = [row for row in rows if row["synthesis_unit_count"] >= 41]
    sample_refs = {
        "high_density": [row["reference"] for row in dense[:5]],
        "medium_density": [row["reference"] for row in rows if 11 <= row["synthesis_unit_count"] <= 20][:5],
        "low_density": [row["reference"] for row in rows if 1 <= row["synthesis_unit_count"] <= 5][:5],
        "thin": [row["reference"] for row in rows if row["availability"] == "THIN"][:5],
        "data_gap": [row["reference"] for row in rows if row["availability"] == "DATA_GAP"][:5],
        "genealogy_or_list": ["1 Chronicles 8", "Numbers 3"],
    }
    return {
        "artifact_version": "commentary-v1.2-dense-richness-audit-v1",
        "cluster_audit_version": "commentary-richness-clusters-v1",
        "proposed_policy_version": "commentary-richness-policy-v2-proposed",
        "chapter_count": len(rows),
        "synthesis_unit_total": sum(row["synthesis_unit_count"] for row in rows),
        "evidence_item_total": sum(row["evidence_item_count"] for row in rows),
        "density_distribution": {bucket: buckets.get(bucket, 0) for bucket in bucket_order},
        "availability_distribution": dict(Counter(row["availability"] for row in rows)),
        "unit_kind_totals": dict(sorted(unit_kind_totals.items())),
        "current_chapter_unit_total": sum(row["current_chapter_unit_count"] for row in rows),
        "surrounding_passage_unit_total": sum(row["surrounding_passage_unit_count"] for row in rows),
        "distinct_idea_cluster_total": sum(row["distinct_idea_cluster_count"] for row in rows),
        "raw_units_beyond_distinct_clusters_total": sum(
            row["synthesis_unit_count"] - row["distinct_idea_cluster_count"] for row in rows
        ),
        "duplicate_reason_cluster_totals": dict(
            Counter(
                reason
                for row in rows
                for reason, count in row["duplicate_reason_counts"].items()
                for _ in range(count)
            )
        ),
        "densest_chapters": top,
        "densest_chapters_by_units_per_evidence": top_by_density,
        "samples": sample_refs,
        "canaries": canary_report(),
        "proposed_thresholds": asdict(ProposedGateThresholds()),
    }


def _unit_from_dict(value: dict[str, Any]) -> Any:
    from bhf_agent.chapter_commentary.synthesis.models import SynthesisUnit

    return SynthesisUnit(**value)


def _bucket(value: int) -> str:
    if value == 0:
        return "0"
    if value <= 5:
        return "1-5"
    if value <= 10:
        return "6-10"
    if value <= 20:
        return "11-20"
    if value <= 40:
        return "21-40"
    return "41+"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=CANDIDATE_ROOT / "audit/dense-synthesis-richness-audit.json",
    )
    args = parser.parse_args(argv)
    report = build_report()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(args.json_out), "chapters": report["chapter_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
