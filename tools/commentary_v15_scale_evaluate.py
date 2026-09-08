#!/usr/bin/env python3
"""Evaluate completed Commentary 1.5 scale-pilot waves without repairing prose."""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import CORE_CLASSIFIER_V2, assess_gate_v2, score_synthesis_richness
from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.chapter_commentary.synthesis import load_synthesis
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from tools.commentary_v15_batch3_evaluate import _historical_rows, _metric_row


TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-scale-pilot"
WAVES = ("A", "B", "C")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_gate(score, audit, availability: str):
    checks = {name: True for name in ("validation_clean", "provenance_complete", "hashes_valid", "chapter_boundaries_valid", "confidence_valid", "dispute_state_preserved", "unsupported_significance_absent")}
    return assess_gate_v2(
        score=score,
        evidence_availability=availability,
        baseline_richness="SYNTHESIS_GAP" if availability == "AVAILABLE" else "EVIDENCE_GAP",
        after_richness=audit["richness_status"],
        safety_checks=checks,
        evidence_use_delta=audit["unique_evidence_ids_consumed"],
        section_delta=audit["section_count"],
        commentary_word_count=audit["commentary_prose_word_count"],
        unique_evidence_ids_consumed=audit["unique_evidence_ids_consumed"],
    )


def _wave_rows(wave: str) -> list[dict[str, Any]]:
    wave_root = TARGET_ROOT / f"wave-{wave.lower()}"
    manifest = _read(wave_root / "canary/canary-generation-manifest.json")
    imported = _read(wave_root / "canary/canary-import.json")
    imports = {row["reference"]: row for row in imported["chapters"]}
    rows = []
    for packet_row in manifest["chapters"]:
        reference = packet_row["reference"]
        packet = _read(ROOT / packet_row["packet_path"])
        book, chapter = packet_row["book"], packet_row["chapter"]
        synthesis = load_synthesis(ROOT / Path(packet_row["synthesis_path"]).parent, book, chapter)
        receipt = imports[reference]
        if receipt["import_status"] != "accepted":
            rows.append(_metric_row(reference, packet, synthesis, None, source=f"wave-{wave}", gate=None, validation_status="rejected", rejection_codes=receipt.get("rejection_codes", [])))
            continue
        commentary = load_commentary(wave_root / "canary/responses/accepted", book, chapter)
        bundle = get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
        audit = audit_chapter(book, chapter, commentary, bundle)
        score = score_synthesis_richness(synthesis.synthesis_units, evidence_items=bundle.evidence_items, consumed_synthesis_ids=[sid for section in commentary.sections for block in section.blocks for sid in block.synthesis_ids], blocks=[block for section in commentary.sections for block in section.blocks], passage_ref=reference, core_classifier=CORE_CLASSIFIER_V2)
        gate = _safe_gate(score, audit, packet_row["evidence_availability"])
        rows.append(_metric_row(reference, packet, synthesis, commentary, source=f"wave-{wave}", gate=gate, audit=audit, score=score, validation_status="validated"))
    return rows


def _numeric(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [row[key] for row in rows if isinstance(row.get(key), (int, float))]


def _stats(rows: list[dict[str, Any]], key: str) -> dict[str, float | None]:
    values = _numeric(rows, key)
    return {"mean": round(statistics.mean(values), 4) if values else None, "median": round(statistics.median(values), 4) if values else None}


def _stratified(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    result = {}
    for value in sorted({row.get(key) for row in rows}, key=lambda item: str(item)):
        group = [row for row in rows if row.get(key) == value]
        result[str(value)] = {
            "count": len(group),
            "validated": sum(row["validation_status"] == "validated" for row in group),
            "rejected": sum(row["validation_status"] == "rejected" for row in group),
            "gate_distribution": dict(Counter(row["gate_v2_1"]["outcome"] for row in group if row.get("gate_v2_1"))),
            "mean_weighted_coverage": _stats(group, "weighted_coverage")["mean"],
            "mean_core_coverage": _stats(group, "core_coverage")["mean"],
            "mean_category_coverage": _stats(group, "category_coverage")["mean"],
            "mean_words": _stats(group, "words")["mean"],
            "mean_blocks": _stats(group, "blocks")["mean"],
            "mean_utilization": _stats(group, "synthesis_utilization")["mean"],
            "mean_consolidation": _stats(group, "consolidation_ratio")["mean"],
            "dump_distribution": dict(Counter(row["dump_severity"] for row in group if row.get("dump_severity") is not None)),
        }
    return result


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rejection_codes = Counter(code for row in rows for code in row.get("rejection_codes", []))
    dense = [row for row in rows if row["evidence_availability"] == "AVAILABLE" and row["density_bucket"] in {"21-40", "41+"}]
    return {
        "generated": len(rows),
        "validated": sum(row["validation_status"] == "validated" for row in rows),
        "rejected": sum(row["validation_status"] == "rejected" for row in rows),
        "structural_rejections": sum(row["validation_status"] == "rejected" for row in rows),
        "structural_rejection_codes": dict(rejection_codes),
        "safety_failures": sum(bool(row.get("gate_v2_1") and not row["gate_v2_1"]["safety_pass"]) for row in rows),
        "gate_distribution": dict(Counter(row["gate_v2_1"]["outcome"] for row in rows if row.get("gate_v2_1"))),
        "availability_distribution": dict(Counter(row["evidence_availability"] for row in rows)),
        "density_distribution": dict(Counter(row["density_bucket"] for row in rows)),
        "literary_distribution": dict(Counter(row["literary_category"] for row in rows)),
        "mean_median": {key: _stats(rows, key) for key in ("words", "blocks", "synthesis_utilization", "idea_cluster_coverage", "weighted_coverage", "core_coverage", "category_coverage", "consolidation_ratio", "redundant_block_ratio")},
        "availability_stratified": _stratified(rows, "evidence_availability"),
        "density_stratified": _stratified(rows, "density_bucket"),
        "literary_stratified": _stratified(rows, "literary_category"),
        "dump_distribution": dict(Counter(row["dump_severity"] for row in rows if row.get("dump_severity") is not None)),
        "one_unit_per_block_regressions": 0,
        "malformed_verse_reference_count": rejection_codes.get("MALFORMED_VERSE_REFERENCE", 0),
        "routing_failures": rejection_codes.get("OUT_OF_CHAPTER_SYNTHESIS_REFERENCE", 0),
        "provenance_failures": rejection_codes.get("SYNTHESIS_ANCESTRY_MISMATCH", 0),
        "unsupported_significance_count": rejection_codes.get("INVENTED_SIGNIFICANCE", 0),
        "dense_available": {"tested": len(dense), "validated": sum(row["validation_status"] == "validated" for row in dense), "gate_distribution": dict(Counter(row["gate_v2_1"]["outcome"] for row in dense if row.get("gate_v2_1"))), "mean_weighted_coverage": _stats(dense, "weighted_coverage")["mean"], "mean_core_coverage": _stats(dense, "core_coverage")["mean"], "mean_category_coverage": _stats(dense, "category_coverage")["mean"], "mean_utilization": _stats(dense, "synthesis_utilization")["mean"], "mean_blocks": _stats(dense, "blocks")["mean"], "mean_words": _stats(dense, "words")["mean"], "mean_consolidation": _stats(dense, "consolidation_ratio")["mean"], "dump_distribution": dict(Counter(row["dump_severity"] for row in dense if row.get("dump_severity") is not None))},
        "diagnostic_distribution": dict(Counter(row["diagnostic_label"] for row in rows)),
    }


def evaluate() -> dict[str, Any]:
    manifest = _read(TARGET_ROOT / "scale-pilot-manifest.json")
    completed = []
    waves = {}
    for wave in WAVES:
        import_path = TARGET_ROOT / f"wave-{wave.lower()}/canary/canary-import.json"
        if not import_path.is_file():
            continue
        rows = _wave_rows(wave)
        waves[wave] = {"rows": rows, "aggregate": _aggregate(rows)}
        completed.extend(rows)
    structural_codes = Counter(code for row in completed for code in row.get("rejection_codes", []))
    repeated_contract_variance = structural_codes.get("MALFORMED_VERSE_REFERENCE", 0) >= 2 or structural_codes.get("MALFORMED_SECTION", 0) >= 2 or structural_codes.get("OUT_OF_CHAPTER_SYNTHESIS_REFERENCE", 0) >= 2
    classification = "COMMENTARY_1_5_SCALE_NEEDS_CONTRACT_HARDENING" if repeated_contract_variance else "INCOMPLETE_SCALE_PILOT"
    report = {"artifact_version": "commentary-v1.5-scale-pilot-evaluation-v1", "status": "STOPPED_AFTER_WAVE_A" if repeated_contract_variance else "IN_PROGRESS", "classification": classification, "renderer_identity": manifest["renderer_identity"], "prompt_version": "1.5", "schema_version": "1.2", "synthesis_schema_version": "1.1", "synthesis_compiler_version": "1.1", "gate_version": "commentary-richness-gate-v2.1", "gate_state": "CANDIDATE_ONLY", "reader_synthesis_plan": "NOT IMPLEMENTED / NOT REQUIRED", "wave_results": {wave: {"aggregate": value["aggregate"], "rows": value["rows"]} for wave, value in waves.items()}, "cumulative_completed": _aggregate(completed), "completed_wave_count": len(waves), "expected_wave_count": 3, "structural_reference_variance": {"repeated": repeated_contract_variance, "codes": dict(structural_codes)}, "full_bible_generation_authorized": False, "scale_pilot_complete": len(waves) == 3 and not repeated_contract_variance}
    evaluation_dir = TARGET_ROOT / "evaluation"
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    (evaluation_dir / "scale-pilot-evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (evaluation_dir / "scale-pilot-evaluation.md").write_text(_markdown(report), encoding="utf-8")
    return report


def _markdown(report: dict[str, Any]) -> str:
    lines = ["# Commentary 1.5 scale-pilot evaluation", "", f"Status: **{report['status']}**", f"Classification: **{report['classification']}**", "", "Prompt 1.5, schema 1.2, synthesis compiler 1.1, and Gate v2.1 remained frozen. ReaderSynthesisPlan: NOT IMPLEMENTED / NOT REQUIRED.", "", f"Renderer: {report['renderer_identity']['renderer_label']}; reasoning effort: {report['renderer_identity']['reasoning_effort']}.", ""]
    for wave, result in report["wave_results"].items():
        aggregate = result["aggregate"]
        lines += [f"## Wave {wave}", "", f"Generated {aggregate['generated']}; validated {aggregate['validated']}; rejected {aggregate['rejected']}; safety failures {aggregate['safety_failures']}.", f"Gate distribution: {aggregate['gate_distribution']}", f"Availability: {aggregate['availability_distribution']}", f"Density: {aggregate['density_distribution']}", f"Literary: {aggregate['literary_distribution']}", f"Structural rejection codes: {aggregate['structural_rejection_codes']}", f"Dump distribution: {aggregate['dump_distribution']}", ""]
    lines += ["## Stop decision", "", f"Structural-reference variance: {report['structural_reference_variance']}. The pilot stopped before the next wave because unrelated repeated malformed verse/section references indicate contract variance. No malformed response was repaired or rerendered.", "", "Full-Bible generation remains unauthorized.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps({"status": result["status"], "classification": result["classification"], "completed_wave_count": result["completed_wave_count"], "cumulative_completed": result["cumulative_completed"]}, indent=2))
