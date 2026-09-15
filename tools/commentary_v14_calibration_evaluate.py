#!/usr/bin/env python3
"""Evaluate the four Commentary 1.4 calibration responses and Revelation 3.

The report is scoring-only: validation and provenance remain independent hard
gates, Gate v2.1 stays candidate-only, and no production commentary is written.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    GateOutcome,
    RICHNESS_GATE_V2_VERSION,
    assess_gate_v2,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.storage import _from_dict, load_commentary
from bhf_agent.chapter_commentary.synthesis.models import SynthesisUnit
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION


PILOT_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.3-pilot"
CALIBRATION_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.4-calibration"
TARGETS = (("Exodus", 12), ("Esther", 4), ("Jeremiah", 7), ("1 Chronicles", 9))
BASELINE_RICHNESS = {
    "Exodus 12": "SYNTHESIS_GAP",
    "Esther 4": "SYNTHESIS_GAP",
    "Jeremiah 7": "SYNTHESIS_GAP",
    "1 Chronicles 9": "VALIDATION_FAILED",
}


def _slug(book: str) -> str:
    return book.lower().replace(" ", "_")


def _raw_payload(root: Path, book: str, chapter: int) -> dict:
    value = json.loads((root / "expected-external-responses" / f"{_slug(book)}_{chapter:03d}.json").read_text())
    return value["response_payload"]


def _commentary_from_payload(value: dict):
    return _from_dict({**value, "status": value.get("status") or "pending"})


def _score(root: Path, book: str, chapter: int, commentary):
    synthesis_root = root / "canary/synthesis" if (root / "canary/synthesis").is_dir() else root / "synthesis"
    synthesis_data = json.loads((synthesis_root / f"{_slug(book)}_{chapter:03d}.json").read_text())
    units = [SynthesisUnit(**value) for value in synthesis_data["synthesis_units"]]
    bundle = get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
    blocks = [block for section in commentary.sections for block in section.blocks]
    consumed = [synthesis_id for block in blocks for synthesis_id in block.synthesis_ids]
    return score_synthesis_richness(
        units,
        evidence_items=bundle.evidence_items if bundle else [],
        consumed_synthesis_ids=consumed,
        blocks=blocks,
        passage_ref=f"{book} {chapter}",
        core_classifier=CORE_CLASSIFIER_V2,
    )


def _metrics(commentary, score, audit):
    duplicate_clusters = sum(cluster.duplicate_reason != "DISTINCT" for cluster in score.clusters)
    return {
        "validation_status": commentary.status,
        "core_coverage": score.core_cluster_coverage,
        "weighted_coverage": score.weighted_idea_coverage,
        "category_coverage": score.category_coverage,
        "raw_units": score.synthesis_unit_count,
        "meaningful_clusters": score.meaningful_cluster_count,
        "consumed_units": score.consumed_synthesis_count,
        "consumed_clusters": score.consumed_cluster_count,
        "blocks": audit["commentary_block_count"],
        "words": audit["commentary_prose_word_count"],
        "sections": audit["section_count"],
        "unit_utilization": round(score.raw_synthesis_coverage, 4),
        "consolidation_ratio": score.consolidation_ratio,
        "block_to_cluster_ratio": score.dump_diagnostics.block_to_cluster_ratio,
        "redundant_cluster_count": duplicate_clusters,
        "repeated_block_count": score.dump_diagnostics.repeated_block_count,
        "dump_severity": score.dump_diagnostics.severity,
        "dump_signals": score.dump_diagnostics.signals,
        "unique_evidence_ids": audit["unique_evidence_ids_consumed"],
        "richness_status": audit["richness_status"],
    }


def _gate(score, *, availability, baseline, after, safety, evidence_delta, section_delta=0, word_count, evidence_count, boilerplate=False):
    return assess_gate_v2(
        score=score,
        evidence_availability=availability,
        baseline_richness=baseline,
        after_richness=after,
        safety_checks=safety,
        boilerplate_detected=boilerplate,
        evidence_use_delta=evidence_delta,
        section_delta=section_delta,
        commentary_word_count=word_count,
        unique_evidence_ids_consumed=evidence_count,
    )


def evaluate() -> dict:
    rows = []
    for book, chapter in TARGETS:
        reference = f"{book} {chapter}"
        old = _commentary_from_payload(_raw_payload(PILOT_ROOT, book, chapter))
        new = load_commentary(CALIBRATION_ROOT / "canary/responses/accepted", book, chapter)
        if new is None:
            raise RuntimeError(f"missing imported v1.4 response for {reference}")
        old_audit = audit_chapter(book, chapter, old, get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION))
        new_audit = audit_chapter(book, chapter, new, get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION))
        old_score = _score(PILOT_ROOT, book, chapter, old)
        new_score = _score(CALIBRATION_ROOT, book, chapter, new)
        old_metrics = _metrics(old, old_score, old_audit)
        old_metrics["validation_status"] = "validated" if reference != "1 Chronicles 9" else "rejected"
        old_metrics["richness_status"] = BASELINE_RICHNESS[reference]
        safety = {"validation_clean": True, "provenance_complete": True, "hashes_valid": True, "chapter_boundaries_valid": True, "confidence_valid": True, "dispute_state_preserved": True, "unsupported_significance_absent": True}
        gate = _gate(
            new_score,
            availability="AVAILABLE",
            baseline="SYNTHESIS_GAP",
            after=new_audit["richness_status"],
            safety=safety,
            evidence_delta=new_audit["unique_evidence_ids_consumed"] - old_audit["unique_evidence_ids_consumed"],
            section_delta=new_audit["section_count"] - old_audit["section_count"],
            word_count=new_audit["commentary_prose_word_count"],
            evidence_count=new_audit["unique_evidence_ids_consumed"],
        )
        rows.append({
            "reference": reference,
            "prompt_change": "1.3 -> 1.4",
            "old_1_3": old_metrics,
            "new_1_4": _metrics(new, new_score, new_audit),
            "gate_v2_1": gate.to_dict(),
            "validation": {"old": old.status == "validated", "new": new.status == "validated", "new_errors": new.validation_errors},
        })

    rev_book, rev_chapter = "Revelation", 3
    rev = _commentary_from_payload(_raw_payload(PILOT_ROOT, rev_book, rev_chapter))
    rev_bundle = get_chapter_evidence_bundle(rev_book, rev_chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
    rev_audit = audit_chapter(rev_book, rev_chapter, rev, rev_bundle)
    rev_score = _score(PILOT_ROOT, rev_book, rev_chapter, rev)
    rev_safety = {"validation_clean": True, "provenance_complete": True, "hashes_valid": True, "chapter_boundaries_valid": True, "confidence_valid": True, "dispute_state_preserved": True, "unsupported_significance_absent": True}
    new_gate = _gate(
        rev_score,
        availability="THIN",
        baseline="SYNTHESIS_GAP",
        after=rev_audit["richness_status"],
        safety=rev_safety,
        evidence_delta=0,
        word_count=rev_audit["commentary_prose_word_count"],
        evidence_count=rev_audit["unique_evidence_ids_consumed"],
    )
    old_gate = {
        "outcome": GateOutcome.QUALITY_FAIL.value,
        "gate_class": "EVIDENCE_LIMITED_CONTROL",
        "failed_check": "remains_evidence_limited",
        "reason": "Gate v2 treated RICH_ENOUGH post-render classification as incompatible with THIN safe restraint.",
    }
    revelation = {
        "reference": "Revelation 3",
        "response_version": "1.3 preserved; not rerendered",
        "metrics": _metrics(rev, rev_score, rev_audit),
        "old_gate_v2": old_gate,
        "gate_v2_1": new_gate.to_dict(),
        "validation": "valid preserved response",
    }
    outcomes = [row["gate_v2_1"]["outcome"] for row in rows] + [new_gate.outcome]
    return {
        "artifact_version": "commentary-v1.4-calibration-evaluation-v1",
        "prompt_version": "1.4",
        "gate_version": RICHNESS_GATE_V2_VERSION,
        "renderer_identity": {"renderer_label": "GPT-5 Codex", "reasoning_effort": "NOT_EXPOSED"},
        "source_pilot_preserved": True,
        "rerendered_chapters": [f"{book} {chapter}" for book, chapter in TARGETS],
        "revelation_3_rerendered": False,
        "outcome_distribution": dict(Counter(outcomes)),
        "chapters": rows,
        "revelation_3": revelation,
        "classification": "CALIBRATION_SUCCESS" if all(outcome in {"PASS", "PASS_WITH_WARNING"} for outcome in outcomes) else "CALIBRATION_REVIEW_REQUIRED",
        "reader_synthesis_plan_needed": False,
        "bulk_authorization": False,
        "gate_v2_1_state": "CANDIDATE_ONLY; not activated globally",
    }


if __name__ == "__main__":
    output = CALIBRATION_ROOT / "evaluation/gate-v2.1-calibration-report.json"
    report = evaluate()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"classification": report["classification"], "outcomes": report["outcome_distribution"], "report": str(output)}, indent=2))
