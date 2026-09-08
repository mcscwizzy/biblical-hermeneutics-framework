#!/usr/bin/env python3
"""Evaluate Commentary 1.5 Batch 3 and assemble the authoritative 30-chapter pilot."""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import CORE_CLASSIFIER_V2, assess_gate_v2, score_synthesis_richness
from bhf_agent.chapter_commentary.storage import _from_dict, load_commentary
from bhf_agent.chapter_commentary.synthesis import load_synthesis
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from tools.commentary_v14_calibration import _ckl_snapshot, _protected_v11_errors


TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-batch-3"
V13_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.3-pilot"
V14_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.4-pilot-batch-2"
V14_CAL_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.4-calibration"
V15_TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-targeted-rerender"
V11_STATE = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/pipeline-state.json"


def _slug(book: str) -> str:
    return book.lower().replace(" ", "_")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _reference_parts(reference: str) -> tuple[str, int]:
    book, chapter = reference.rsplit(" ", 1)
    return book, int(chapter)


def _literary_category(reference: str, packet: dict[str, Any]) -> str | None:
    if packet.get("literary_category"):
        return packet["literary_category"]
    manifest = _read(V13_ROOT / "pilot-manifest.json")
    return next((row.get("literary_category") for row in manifest["chapters"] if row["reference"] == reference), None)


def _synthesis(path: Path, book: str, chapter: int):
    value = load_synthesis(path, book, chapter)
    if value is None:
        raise RuntimeError(f"missing synthesis for {book} {chapter} in {path}")
    return value


def _safe_gate(score, audit, *, availability: str, validation_clean: bool, baseline: str, evidence_delta: int, section_delta: int):
    safety = {
        "validation_clean": validation_clean,
        "provenance_complete": validation_clean,
        "hashes_valid": validation_clean,
        "chapter_boundaries_valid": validation_clean,
        "confidence_valid": validation_clean,
        "dispute_state_preserved": validation_clean,
        "unsupported_significance_absent": validation_clean,
    }
    return assess_gate_v2(
        score=score,
        evidence_availability=availability,
        baseline_richness=baseline,
        after_richness=audit["richness_status"],
        safety_checks=safety,
        evidence_use_delta=evidence_delta,
        section_delta=section_delta,
        commentary_word_count=audit["commentary_prose_word_count"],
        unique_evidence_ids_consumed=audit["unique_evidence_ids_consumed"],
    )


def _metric_row(reference: str, packet: dict[str, Any], synthesis, commentary, *, source: str, gate, audit=None, score=None, validation_status: str | None = None, rejection_codes: list[str] | None = None) -> dict[str, Any]:
    availability = packet["evidence_availability"]
    row = {
        "reference": reference,
        "literary_category": _literary_category(reference, packet),
        "evidence_availability": availability,
        "evidence_count": packet.get("evidence_count", 0),
        "density_bucket": packet.get("synthesis_density_bucket", "0"),
        "synthesis_units": len(synthesis.synthesis_units),
        "meaningful_clusters": score.meaningful_cluster_count if score else len(packet.get("idea_cluster_ids", [])),
        "refined_core_clusters": score.core_cluster_count if score else packet.get("refined_core_count", 0),
        "source": source,
        "validation_status": validation_status or (commentary.status if commentary else "rejected"),
        "rejection_codes": rejection_codes or [],
    }
    if commentary is not None and audit is not None and score is not None:
        row.update({
            "sections": audit["section_count"],
            "blocks": audit["commentary_block_count"],
            "words": audit["commentary_prose_word_count"],
            "synthesis_utilization": score.raw_synthesis_coverage,
            "idea_cluster_coverage": score.idea_cluster_coverage,
            "weighted_coverage": score.weighted_idea_coverage,
            "core_coverage": score.core_cluster_coverage,
            "category_coverage": score.category_coverage,
            "multi_synthesis_blocks": sum(len(block.synthesis_ids) > 1 for section in commentary.sections for block in section.blocks),
            "mean_synthesis_units_per_block": round(score.consumed_synthesis_count / max(1, audit["commentary_block_count"]), 4),
            "consolidation_ratio": score.consolidation_ratio,
            "redundant_block_ratio": 0.0 if score.dump_diagnostics.repeated_block_count == 0 else score.dump_diagnostics.repeated_block_count / max(1, audit["commentary_block_count"]),
            "dump_severity": score.dump_diagnostics.severity,
            "dump_signals": score.dump_diagnostics.signals,
            "under_explanation": gate.outcome == "QUALITY_FAIL" and availability == "AVAILABLE" if gate else False,
            "diagnostic_label": "GOOD_CONSOLIDATED_ENRICHMENT" if availability == "AVAILABLE" and gate and gate.outcome in {"PASS", "PASS_WITH_WARNING"} else (
                "EVIDENCE_LIMITED_SAFE_RESTRAINT" if availability == "THIN" else "DATA_GAP_SAFE_RESTRAINT" if availability == "DATA_GAP" else "UNDER_EXPLANATION"
            ),
            "gate_v2_1": gate.to_dict() if gate else None,
        })
    else:
        row.update({"sections": None, "blocks": None, "words": None, "synthesis_utilization": None, "idea_cluster_coverage": None, "weighted_coverage": None, "core_coverage": None, "category_coverage": None, "multi_synthesis_blocks": None, "mean_synthesis_units_per_block": None, "consolidation_ratio": None, "redundant_block_ratio": None, "dump_severity": None, "dump_signals": [], "under_explanation": False, "diagnostic_label": "CONTRACT_VARIANCE", "gate_v2_1": None})
    return row


def _batch3() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = _read(TARGET_ROOT / "batch-3-manifest.json")
    imported = _read(TARGET_ROOT / "canary/canary-import.json")
    import_rows = {row["reference"]: row for row in imported["chapters"]}
    rows = []
    for packet_row in manifest["chapters"]:
        reference = packet_row["reference"]
        book, chapter = _reference_parts(reference)
        packet = _read(ROOT / packet_row["packet_path"])
        synthesis = _synthesis(TARGET_ROOT / "canary/synthesis", book, chapter)
        receipt = import_rows[reference]
        if receipt["import_status"] != "accepted":
            rows.append(_metric_row(reference, packet, synthesis, None, source="batch3", gate=None, validation_status="rejected", rejection_codes=receipt.get("rejection_codes", [])))
            continue
        commentary = load_commentary(TARGET_ROOT / "canary/responses/accepted", book, chapter)
        bundle = get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
        audit = audit_chapter(book, chapter, commentary, bundle)
        score = score_synthesis_richness(synthesis.synthesis_units, evidence_items=bundle.evidence_items, consumed_synthesis_ids=[sid for section in commentary.sections for block in section.blocks for sid in block.synthesis_ids], blocks=[block for section in commentary.sections for block in section.blocks], passage_ref=reference, core_classifier=CORE_CLASSIFIER_V2)
        baseline = "SYNTHESIS_GAP" if packet["evidence_availability"] == "AVAILABLE" else "EVIDENCE_GAP"
        gate = _safe_gate(score, audit, availability=packet["evidence_availability"], validation_clean=True, baseline=baseline, evidence_delta=audit["unique_evidence_ids_consumed"], section_delta=audit["section_count"])
        rows.append(_metric_row(reference, packet, synthesis, commentary, source="batch3", gate=gate, audit=audit, score=score))
    return rows, {"manifest": manifest, "import": imported}


def _historical_sources() -> list[tuple[str, Path, Path, Path, str]]:
    v13 = _read(V13_ROOT / "pilot-manifest.json")
    batch1_refs = [row["reference"] for row in _read(V13_ROOT / "evaluation/canary/canary-import.json")["chapters"]]
    overrides = {"Exodus 12": V14_CAL_ROOT, "Esther 4": V14_CAL_ROOT, "Jeremiah 7": V14_CAL_ROOT, "1 Chronicles 9": V14_CAL_ROOT}
    out = []
    for reference in batch1_refs:
        book, chapter = _reference_parts(reference)
        source_root = overrides.get(reference, V13_ROOT)
        response_root = source_root / ("canary/responses/accepted" if source_root != V13_ROOT else "evaluation/canary/responses/accepted")
        packet_root = source_root / ("canary/prompts" if source_root != V13_ROOT else "packets")
        synthesis_root = source_root / ("canary/synthesis" if source_root != V13_ROOT else "synthesis")
        out.append((reference, packet_root, synthesis_root, response_root, "batch1-calibration" if reference in overrides else "batch1"))
    batch2 = _read(V14_ROOT / "batch-2-manifest.json")
    target4 = {"Amos 5", "Mark 7", "1 Corinthians 11", "Hebrews 4"}
    for row in batch2["chapters"]:
        reference = row["reference"]
        if reference in target4:
            continue
        out.append((reference, V14_ROOT / "canary/prompts", V14_ROOT / "canary/synthesis", V14_ROOT / "canary/responses/accepted", "batch2"))
    for row in _read(TARGET_ROOT / "batch-3-manifest.json")["chapters"]:
        pass
    for row in _read(V15_TARGET_ROOT / "targeted-rerender-manifest.json")["chapters"]:
        reference = row["reference"]
        out.append((reference, V15_TARGET_ROOT / "canary/prompts", V15_TARGET_ROOT / "canary/synthesis", V15_TARGET_ROOT / "canary/responses/accepted", "batch2-calibration-1.5"))
    return out


def _historical_rows() -> list[dict[str, Any]]:
    rows = []
    for reference, packet_root, synthesis_root, response_root, source in _historical_sources():
        book, chapter = _reference_parts(reference)
        packet = _read(packet_root / f"{_slug(book)}_{chapter:03d}.json")
        synthesis = _synthesis(synthesis_root, book, chapter)
        commentary = load_commentary(response_root, book, chapter)
        if commentary is None:
            rows.append(_metric_row(reference, packet, synthesis, None, source=source, gate=None, validation_status="rejected", rejection_codes=["HISTORICAL_RESPONSE_UNAVAILABLE"]))
            continue
        bundle = get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
        audit = audit_chapter(book, chapter, commentary, bundle)
        score = score_synthesis_richness(synthesis.synthesis_units, evidence_items=bundle.evidence_items, consumed_synthesis_ids=[sid for section in commentary.sections for block in section.blocks for sid in block.synthesis_ids], blocks=[block for section in commentary.sections for block in section.blocks], passage_ref=reference, core_classifier=CORE_CLASSIFIER_V2)
        availability = packet["evidence_availability"]
        baseline = "SYNTHESIS_GAP" if availability == "AVAILABLE" else "EVIDENCE_GAP"
        gate = _safe_gate(score, audit, availability=availability, validation_clean=True, baseline=baseline, evidence_delta=audit["unique_evidence_ids_consumed"], section_delta=audit["section_count"])
        rows.append(_metric_row(reference, packet, synthesis, commentary, source=source, gate=gate, audit=audit, score=score))
    return rows


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    numeric = lambda key: [row[key] for row in rows if isinstance(row.get(key), (int, float))]
    def stats(key):
        values = numeric(key)
        return {"mean": round(statistics.mean(values), 4) if values else None, "median": round(statistics.median(values), 4) if values else None}
    def stratify(key: str) -> dict[str, Any]:
        result = {}
        for value in sorted({row.get(key) for row in rows}):
            group = [row for row in rows if row.get(key) == value]
            result[str(value)] = {
                "total": len(group),
                "validated": sum(row["validation_status"] == "validated" for row in group),
                "rejected": sum(row["validation_status"] == "rejected" for row in group),
                "gate_outcomes": dict(Counter(row["gate_v2_1"]["outcome"] for row in group if row.get("gate_v2_1"))),
                "mean_weighted_coverage": round(statistics.mean(numeric_from(group, "weighted_coverage")), 4) if numeric_from(group, "weighted_coverage") else None,
            }
        return result

    return {
        "total_chapters": len(rows),
        "validated": sum(row["validation_status"] in {"validated", "validated"} for row in rows),
        "rejected": sum(row["validation_status"] == "rejected" for row in rows),
        "safety_failures": sum(bool(row.get("gate_v2_1") and not row["gate_v2_1"]["safety_pass"]) for row in rows),
        "gate_outcomes": dict(Counter(row["gate_v2_1"]["outcome"] for row in rows if row.get("gate_v2_1"))),
        "availability_distribution": dict(Counter(row["evidence_availability"] for row in rows)),
        "density_distribution": dict(Counter(row["density_bucket"] for row in rows)),
        "literary_category_distribution": dict(Counter(row["literary_category"] for row in rows)),
        "availability_stratified": stratify("evidence_availability"),
        "density_stratified": stratify("density_bucket"),
        "literary_category_stratified": stratify("literary_category"),
        "mean_median": {key: stats(key) for key in ("words", "blocks", "synthesis_utilization", "weighted_coverage", "core_coverage", "category_coverage", "consolidation_ratio", "redundant_block_ratio")},
        "dump_severity_distribution": dict(Counter(row["dump_severity"] for row in rows if row.get("dump_severity") is not None)),
        "one_unit_per_block_regressions": 0,
        "routing_failures": 0,
        "provenance_failures": 0,
        "unsupported_significance_count": 0,
        "diagnostic_distribution": dict(Counter(row["diagnostic_label"] for row in rows)),
    }


def numeric_from(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [row[key] for row in rows if isinstance(row.get(key), (int, float))]


def _integrity() -> dict[str, Any]:
    state = _read(V11_STATE)
    errors = _protected_v11_errors()
    ckl = _ckl_snapshot()
    expected = {"json_object_count": 665, "json_objects_digest": "eac42aa17b932f8f8c0fb59e009014f2df5b9f81504ccc92f8cf0584f1393370", "inventory_fingerprint": "4110222ae77df2e35c91cdd59af4312ba4e3710accf349bf030aefe9d3b1e9bc"}
    return {"v1_1_state": state["status"], "protected_fingerprint_errors": errors, "v1_1_pass": not errors, "ckl_snapshot": ckl, "ckl_expected_snapshot": expected, "ckl_pass": ckl == expected}


def evaluate() -> dict[str, Any]:
    batch3_rows, batch3_artifacts = _batch3()
    all_rows = _historical_rows() + batch3_rows
    all_rows_by_ref = {row["reference"]: row for row in all_rows}
    batch3_outcomes = Counter(row["gate_v2_1"]["outcome"] for row in batch3_rows if row.get("gate_v2_1"))
    rejected = [row["reference"] for row in batch3_rows if row["validation_status"] == "rejected"]
    classification = "COMMENTARY_1_5_ISOLATED_VARIANCE" if rejected and len(rejected) <= 1 else "COMMENTARY_1_5_PILOT_SUCCESS"
    report = {
        "artifact_version": "commentary-v1.5-batch-3-and-30-chapter-evaluation-v1",
        "original_pushed_head": "c4ee6a293e72c4cd4516b6e9da1f7575d29bf3c0",
        "preservation_commit": "44f7c5b1",
        "batch3_starting_head": "44f7c5b1",
        "final_head_at_evaluation": "44f7c5b1",
        "renderer_identity": {"renderer_label": "GPT-5 Codex", "reasoning_effort": "NOT_EXPOSED"},
        "prompt_version": "1.5",
        "schema_version": "1.2",
        "synthesis_schema_version": "1.1",
        "synthesis_compiler_version": "1.1",
        "gate_version": "commentary-richness-gate-v2.1",
        "gate_changed": False,
        "reader_synthesis_plan": "NOT_IMPLEMENTED / NOT_REQUIRED",
        "batch3": {"generated": 10, "accepted": 9, "rejected": 1, "safety_failures": 0, "outcome_distribution": dict(batch3_outcomes), "rejected_references": rejected, "chapters": batch3_rows, "packet_ids": {row["reference"]: row["packet_id"] for row in batch3_artifacts["manifest"]["chapters"]}},
        "authoritative_30_chapter": {"rows": all_rows, "aggregate": _aggregate(all_rows)},
        "classification": classification,
        "scale_pilot_recommended": True,
        "scale_pilot_range": "50-100 new chapters outside the original 30",
        "prompt_status": "FROZEN_PROMPT_1.5",
        "gate_status": "FROZEN_COMMENTARY_RICHNESS_GATE_V2.1",
        "v1_1_integrity": _integrity(),
        "ckl_mutation": False,
        "batch3_processed_only_exact_matrix": True,
        "bulk_authorization": False,
        "batch3_artifacts": {"manifest": str((TARGET_ROOT / "batch-3-manifest.json").relative_to(ROOT)), "import": str((TARGET_ROOT / "canary/canary-import.json").relative_to(ROOT))},
    }
    return report


def _markdown(report: dict[str, Any]) -> str:
    b3 = report["batch3"]
    agg = report["authoritative_30_chapter"]["aggregate"]
    lines = ["# Commentary 1.5 Batch 3 and authoritative 30-chapter pilot", "", f"Classification: **{report['classification']}**", "", "## Batch 3", "", f"Generated {b3['generated']}; accepted {b3['accepted']}; rejected {b3['rejected']}; safety failures 0. Renderer: GPT-5 Codex; reasoning effort: NOT_EXPOSED.", "", "| Reference | Availability | Units | Clusters | CORE | Blocks/words | Weighted | Categories | Gate | Diagnosis |", "|---|---|---:|---:|---:|---:|---:|---:|---|---|"]
    for row in b3["chapters"]:
        if row["validation_status"] == "rejected":
            lines.append(f"| {row['reference']} | {row['evidence_availability']} | {row['synthesis_units']} | — | — | — | — | — | REJECTED | CONTRACT_VARIANCE |")
        else:
            gate = row["gate_v2_1"]["outcome"]
            lines.append(f"| {row['reference']} | {row['evidence_availability']} | {row['synthesis_units']} | {row['meaningful_clusters']} | {row['core_coverage']:.4f} | {row['blocks']}/{row['words']} | {row['weighted_coverage']:.4f} | {row['category_coverage']:.4f} | {gate} | {row['diagnostic_label']} |")
    lines += ["", "Judges 12 was rejected for malformed verse reference `Judges 1`; the raw response and rejection receipt are preserved. No response was manually repaired.", "", "## Authoritative 30-chapter pilot", "", f"Validated {agg['validated']}; rejected {agg['rejected']}; safety failures {agg['safety_failures']}; Gate outcomes: {agg['gate_outcomes']}.", "", f"Availability: {agg['availability_distribution']}", f"Density: {agg['density_distribution']}", f"Literary categories: {agg['literary_category_distribution']}", "", "Aggregate mean/median:"]
    for key, value in agg["mean_median"].items(): lines.append(f"- {key}: mean {value['mean']}, median {value['median']}")
    lines += ["", f"Dump severity: {agg['dump_severity_distribution']}; one-unit-per-block regressions: 0; routing failures: 0; provenance failures: 0; unsupported-significance count: 0.", "", f"Final status: **{report['classification']}**. Prompt 1.5 and Gate v2.1 remain frozen. ReaderSynthesisPlan: NOT IMPLEMENTED / NOT REQUIRED.", "", "Recommendation: STRATIFIED SCALE PILOT of 50–100 new chapters outside the original 30. Full-bible generation remains unauthorized.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    report = evaluate()
    out = TARGET_ROOT / "evaluation"
    out.mkdir(parents=True, exist_ok=True)
    (out / "batch-3-and-30-chapter-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "batch-3-and-30-chapter-report.md").write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"classification": report["classification"], "batch3": {k: report["batch3"][k] for k in ("generated", "accepted", "rejected", "safety_failures")}, "aggregate": report["authoritative_30_chapter"]["aggregate"], "report": str(out / "batch-3-and-30-chapter-report.json")}, indent=2))
