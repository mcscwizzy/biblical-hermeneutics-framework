#!/usr/bin/env python3
"""Simulate the scoring-only Commentary Richness Gate v2.1.

This tool reads the locked v1.2 canary and the existing v1.1 runtime corpus.
It never regenerates prose, changes CKL/evidence, invokes a model, or updates
the active canary gate.  Its output is a versioned candidate-policy report.
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

from bhf_agent import bible
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V1,
    CORE_CLASSIFIER_V2,
    GateOutcome,
    GateV2Thresholds,
    RICHNESS_GATE_V2_VERSION,
    assess_gate_v2,
    classify_gate_class,
    proposed_gate_passes,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis
from bhf_agent.chapter_commentary.synthesis.models import SynthesisUnit
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION


CANDIDATE_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment"
CANARY_ROOT = CANDIDATE_ROOT / "canary"
BASELINE_AUDIT = CANDIDATE_ROOT / "audit/commentary-richness-audit.json"
RUNTIME_V11 = ROOT / ".bhf-data/bhf-commentary-v1.1"
DEFAULT_OUTPUT = CANDIDATE_ROOT / "audit/commentary-richness-gate-v2.1.json"
CANARY_REFERENCES = (
    ("Genesis", 1), ("Leviticus", 16), ("Ruth", 3), ("Psalms", 1),
    ("1 Samuel", 21), ("1 Samuel", 28), ("2 Samuel", 6), ("2 Samuel", 24),
    ("1 Chronicles", 8), ("John", 1), ("Isaiah", 6), ("Revelation", 12),
    ("Numbers", 3),
)

_UNSAFE_CODES = {
    "CHAPTER_IDENTITY_MISMATCH", "OUT_OF_CHAPTER_VERSE_REFERENCE",
    "UNKNOWN_EVIDENCE_ID", "UNKNOWN_SYNTHESIS_ID", "SYNTHESIS_ANCESTRY_MISMATCH",
    "CONFIDENCE_EXCEEDS_EVIDENCE", "DISPUTED_AS_FACT", "INVALID_CONFIDENCE",
    "INVALID_INTERPRETATION_LEVEL", "INVENTED_SIGNIFICANCE", "UNSUPPORTED_ENTITY",
    "UNSUPPORTED_DATE", "UNSUPPORTED_SECTION_KIND", "UNSUPPORTED_SYNTHESIS",
}


def canary_report() -> dict[str, Any]:
    comparison = _read_json(CANARY_ROOT / "canary-comparison.json")
    by_reference = {row["reference"]: row for row in comparison["chapters"]}
    rows = []
    for book, chapter in CANARY_REFERENCES:
        reference = f"{book} {chapter}"
        row = by_reference[reference]
        bundle = get_chapter_evidence_bundle(
            book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
        )
        synthesis_data = _read_json(
            CANARY_ROOT / "synthesis" / f"{_slug(book)}_{chapter:03d}.json"
        )
        units = [SynthesisUnit(**value) for value in synthesis_data["synthesis_units"]]
        commentary = load_commentary(CANARY_ROOT / "responses/accepted", book, chapter)
        blocks = [
            block
            for section in commentary.sections
            for block in section.blocks
        ] if commentary else []
        consumed = [synthesis_id for block in blocks for synthesis_id in block.synthesis_ids]
        score_v1 = score_synthesis_richness(
            units,
            evidence_items=bundle.evidence_items if bundle else [],
            consumed_synthesis_ids=consumed,
            blocks=blocks,
            passage_ref=reference,
            core_classifier=CORE_CLASSIFIER_V1,
        )
        score_v2 = score_synthesis_richness(
            units,
            evidence_items=bundle.evidence_items if bundle else [],
            consumed_synthesis_ids=consumed,
            blocks=blocks,
            passage_ref=reference,
            core_classifier=CORE_CLASSIFIER_V2,
        )
        after = row.get("after") or {}
        before = row["before"]
        safety = _canary_safety(row)
        v1_pass, v1_checks = proposed_gate_passes(
            score=score_v1,
            evidence_availability=before["evidence_availability"],
            validation_clean=safety["validation_clean"],
            boilerplate_detected=bool(after.get("boilerplate_detected")),
            evidence_use_delta=int((row.get("deltas") or {}).get("evidence_use_delta") or 0),
            boundary_repetition_ratio=float(after.get("opening_closing_lexical_overlap") or 0),
        )
        v2 = assess_gate_v2(
            score=score_v2,
            evidence_availability=before["evidence_availability"],
            baseline_richness=before["richness_status"],
            after_richness=after.get("richness_status"),
            safety_checks=safety,
            boilerplate_detected=bool(after.get("boilerplate_detected")),
            evidence_use_delta=int((row.get("deltas") or {}).get("evidence_use_delta") or 0),
            section_delta=int((row.get("deltas") or {}).get("section_delta") or 0),
            boilerplate_removed=bool((row.get("deltas") or {}).get("boilerplate_removed")),
            boundary_repetition_ratio=float(after.get("opening_closing_lexical_overlap") or 0),
            commentary_word_count=after.get("commentary_prose_word_count"),
            unique_evidence_ids_consumed=after.get("unique_evidence_ids_consumed"),
        )
        rows.append({
            "reference": reference,
            "gate_class": v2.gate_class,
            "safety_pass": v2.safety_pass,
            "safety_checks": v2.safety_checks,
            "baseline_richness": before["richness_status"],
            "evidence_availability": before["evidence_availability"],
            "raw_units": score_v2.synthesis_unit_count,
            "idea_clusters": len(score_v2.clusters),
            "meaningful_clusters": score_v2.meaningful_cluster_count,
            "core_clusters_v1": score_v1.core_cluster_count,
            "core_covered_v1": score_v1.consumed_core_cluster_count,
            "core_clusters_v2": score_v2.core_cluster_count,
            "core_covered_v2": score_v2.consumed_core_cluster_count,
            "weighted_coverage": score_v2.weighted_idea_coverage,
            "category_coverage": score_v2.category_coverage,
            "blocks": len(blocks),
            "words": after.get("commentary_prose_word_count"),
            "dump": score_v2.dump_diagnostics.to_dict(),
            "gate_v1": {"outcome": "PASS" if v1_pass else "FAIL", "checks": v1_checks},
            "gate_v2": v2.to_dict(),
        })
    return {
        "artifact_version": "commentary-v1.2-richness-gate-v2.1-canary-v1",
        "gate_version": RICHNESS_GATE_V2_VERSION,
        "core_classifier_v1": CORE_CLASSIFIER_V1,
        "core_classifier_v2": CORE_CLASSIFIER_V2,
        "chapters": rows,
        "outcome_distribution": dict(Counter(row["gate_v2"]["outcome"] for row in rows)),
    }


def leviticus_core_audit() -> list[dict[str, Any]]:
    book, chapter = "Leviticus", 16
    synthesis = _read_json(CANARY_ROOT / "synthesis/leviticus_016.json")
    units = [SynthesisUnit(**value) for value in synthesis["synthesis_units"]]
    bundle = get_chapter_evidence_bundle(
        book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    commentary = load_commentary(CANARY_ROOT / "responses/accepted", book, chapter)
    consumed = {
        synthesis_id
        for section in commentary.sections
        for block in section.blocks
        for synthesis_id in block.synthesis_ids
    }
    old = score_synthesis_richness(
        units, evidence_items=bundle.evidence_items, core_classifier=CORE_CLASSIFIER_V1
    )
    refined = score_synthesis_richness(
        units, evidence_items=bundle.evidence_items, core_classifier=CORE_CLASSIFIER_V2
    )
    refined_by_ids = {tuple(cluster.synthesis_ids): cluster for cluster in refined.clusters}
    units_by_id = {unit.id: unit for unit in units}
    result = []
    for cluster in old.clusters:
        if cluster.quality_class != "CORE":
            continue
        new = refined_by_ids.get(tuple(cluster.synthesis_ids))
        if new is None:
            new = next(
                candidate
                for candidate in refined.clusters
                if set(candidate.synthesis_ids) == set(cluster.synthesis_ids)
            )
        facts = [
            fact
            for synthesis_id in cluster.synthesis_ids
            for fact in units_by_id[synthesis_id].facts
        ]
        result.append({
            "cluster_id": cluster.id,
            "kind": cluster.kind,
            "facts": facts,
            "evidence_ancestry": cluster.evidence_ids,
            "passage_scope": cluster.passage_scope,
            "importance_basis": cluster.importance_basis,
            "covered": bool(set(cluster.synthesis_ids).intersection(consumed)),
            "legacy_classifier_label": "CORE",
            "refined_classifier_label": new.quality_class,
            "refined_importance_basis": new.importance_basis,
            "classification_review": _leviticus_review(cluster, new),
        })
    return result


def corpus_simulation() -> dict[str, Any]:
    """Run a metrics-only simulation over all chapters.

    Enrichment targets are intentionally NOT_EVALUATED because the corpus has
    no v2 candidate prose. Existing v1.1 prose is evaluated only as the
    non-regression/ restraint control for the other classes.
    """

    baseline = {
        row["reference"]: row for row in _read_json(BASELINE_AUDIT)["chapters"]
    }
    dimensions: dict[str, Counter[str]] = defaultdict(Counter)
    density_dimensions: dict[str, Counter[str]] = defaultdict(Counter)
    safety_count = Counter()
    dump_count = Counter()
    for book_row in bible.list_books():
        book = str(book_row["name"])
        for chapter in range(1, int(book_row["chapters"]) + 1):
            reference = f"{book} {chapter}"
            base = baseline[reference]
            bundle = get_chapter_evidence_bundle(
                book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
            )
            synthesis = compile_chapter_synthesis(bundle, book=book, chapter=chapter)
            commentary = load_commentary(RUNTIME_V11, book, chapter)
            blocks = [
                block for section in (commentary.sections if commentary else [])
                for block in section.blocks
            ]
            consumed = [synthesis_id for block in blocks for synthesis_id in block.synthesis_ids]
            score = score_synthesis_richness(
                synthesis.synthesis_units,
                evidence_items=bundle.evidence_items,
                consumed_synthesis_ids=consumed,
                blocks=blocks,
                passage_ref=reference,
                core_classifier=CORE_CLASSIFIER_V2,
            )
            gate_class = classify_gate_class(
                synthesis.evidence_availability, base["richness_status"]
            )
            density = _bucket(score.synthesis_unit_count)
            if gate_class == "ENRICHMENT_TARGET":
                outcome = "NOT_EVALUATED_BASELINE_ONLY"
            else:
                outcome = _control_simulation_outcome(
                    gate_class, base, score, commentary, blocks
                )
            dimensions[synthesis.evidence_availability][outcome] += 1
            dimensions[base["richness_status"]][outcome] += 1
            dimensions[gate_class][outcome] += 1
            density_dimensions[density][outcome] += 1
            dump_count[score.dump_diagnostics.severity] += 1
            safety_count["validated"] += int(bool(commentary and commentary.status == "validated"))

    return {
        "scope": "1189 canonical chapters; v1.1 prose as control input",
        "evaluation_limit": "ENRICHMENT_TARGET is not quality-evaluated without v2 candidate prose",
        "outcomes_by_availability": _counter_dict(dimensions, ("AVAILABLE", "THIN", "DATA_GAP")),
        "outcomes_by_baseline": _counter_dict(dimensions, ("RICH_ENOUGH", "SYNTHESIS_GAP", "EVIDENCE_GAP")),
        "outcomes_by_gate_class": _counter_dict(dimensions, (
            "ENRICHMENT_TARGET", "RICH_CONTROL", "EVIDENCE_LIMITED_CONTROL", "DATA_GAP_CONTROL"
        )),
        "outcomes_by_density": _counter_dict(density_dimensions, ("0", "1-5", "6-10", "11-20", "21-40", "41+")),
        "dump_severity_distribution": dict(sorted(dump_count.items())),
        "validated_control_inputs": safety_count["validated"],
    }


def build_report() -> dict[str, Any]:
    canaries = canary_report()
    return {
        "artifact_version": "commentary-v1.2-richness-gate-v2.1-report-v1",
        "gate_version": RICHNESS_GATE_V2_VERSION,
        "scoring_only": True,
        "authoritative": False,
        "bulk_generation_authorized": False,
        "thresholds": GateV2Thresholds().__dict__,
        "canary": canaries,
        "leviticus_16_provisional_core_audit": leviticus_core_audit(),
        "full_corpus_simulation": corpus_simulation(),
        "v1_reference": "commentary-richness-policy-v2-proposed (retained for comparison)",
    }


def _canary_safety(row: dict[str, Any]) -> dict[str, bool]:
    rejection_codes = set(row.get("rejection_codes") or [])
    return {
        "validation_clean": row.get("validation_status") == "validated"
        and not row.get("validation_errors")
        and not row.get("synthesis_validation_errors"),
        "provenance_complete": bool(row.get("provenance_complete")),
        "evidence_ancestry_valid": not rejection_codes.intersection(
            {"UNKNOWN_EVIDENCE_ID", "SYNTHESIS_ANCESTRY_MISMATCH"}
        ),
        "synthesis_ancestry_valid": not rejection_codes.intersection(
            {"UNKNOWN_SYNTHESIS_ID", "SYNTHESIS_ANCESTRY_MISMATCH"}
        ),
        "hashes_valid": bool(row.get("evidence_and_synthesis_locks_match")),
        "chapter_boundaries_valid": not rejection_codes.intersection(
            {"CHAPTER_IDENTITY_MISMATCH", "OUT_OF_CHAPTER_VERSE_REFERENCE"}
        ),
        "confidence_valid": not rejection_codes.intersection(
            {"CONFIDENCE_EXCEEDS_EVIDENCE", "INVALID_CONFIDENCE", "INVALID_INTERPRETATION_LEVEL"}
        ),
        "dispute_state_preserved": "DISPUTED_AS_FACT" not in rejection_codes,
        "unsupported_significance_absent": "INVENTED_SIGNIFICANCE" not in rejection_codes,
    }


def _leviticus_review(old, new) -> str:
    if new.quality_class == "CORE":
        return "retained as essential passage-understanding context"
    if "chronology" in new.categories or old.kind == "chronology":
        return "supporting chronology or reconstruction, not necessary to follow the rite"
    if new.quality_class == "DISPUTED":
        return "contested or interpretive context; preserve as qualified support rather than CORE"
    return "generic/entity-linked supporting context; useful but not necessary for passage understanding"


def _control_simulation_outcome(gate_class, base, score, commentary, blocks) -> str:
    if not commentary or commentary.status != "validated":
        return GateOutcome.SAFETY_FAIL.value
    if gate_class == "RICH_CONTROL":
        return GateOutcome.PASS_WITH_WARNING.value if score.dump_diagnostics.severity != "NONE" else GateOutcome.PASS.value
    if gate_class == "DATA_GAP_CONTROL":
        return GateOutcome.PASS.value
    return GateOutcome.PASS.value if not base.get("boilerplate_detected") else GateOutcome.PASS_WITH_WARNING.value


def _counter_dict(values: dict[str, Counter[str]], order: tuple[str, ...]) -> dict[str, dict[str, int]]:
    return {
        key: dict(sorted(values.get(key, Counter()).items()))
        for key in order
    }


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


def _slug(book: str) -> str:
    return book.lower().replace(" ", "_")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = build_report()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "artifact": str(args.json_out),
        "canaries": len(report["canary"]["chapters"]),
        "corpus": report["full_corpus_simulation"]["scope"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
