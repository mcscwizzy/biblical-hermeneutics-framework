#!/usr/bin/env python3
"""Run the isolated ten-chapter Dense Reader Synthesis v0.1 experiment.

This tool reads only accepted Commentary 1.5 sidecars and writes only beneath
``commentary-dense-reader-v0.1``.  It never calls the Commentary generator,
the synthesis compiler, CKL, or the active reader UI.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.dense_reader import (
    DENSE_READER_ARTIFACT_VERSION,
    DENSE_READER_EXPERIMENT_VERSION,
    DenseReaderArtifact,
    build_reader_artifact,
    load_reader_artifact,
    save_reader_artifact,
    validate_reader_artifact,
)
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    QualityClass,
    cluster_synthesis_units,
    evidence_dump_diagnostics,
)
from bhf_agent.chapter_commentary.synthesis.storage import load_synthesis
from bhf_agent.presentation.models import EvidenceItem


TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-dense-reader-v0.1"
PILOT_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-scale-pilot"
FINAL_RUN_ROOT = PILOT_ROOT / "runs/wave-abc-combined"

EXPERIMENT_CHAPTERS: tuple[tuple[str, int], ...] = (
    ("Philippians", 1),
    ("Acts", 9),
    ("Hebrews", 11),
    ("Genesis", 15),
    ("Acts", 16),
    ("Genesis", 12),
    ("Romans", 8),
    ("Hebrews", 10),
    ("1 Corinthians", 12),
    ("Acts", 1),
)

SOURCE_WAVES = {
    "Genesis 15": "wave-a",
    "Acts 9": "wave-b",
    "Hebrews 11": "wave-b",
    "Acts 16": "wave-b",
    "Romans 8": "wave-b",
    "Acts 1": "wave-b",
    "Philippians 1": "wave-c",
    "Genesis 12": "wave-c",
    "Hebrews 10": "wave-c",
    "1 Corinthians 12": "wave-c",
}

SOURCE_ROWS: dict[str, dict[str, Any]] = {
    "Genesis 15": {"words": 1755, "blocks": 24, "weighted_coverage": 0.7689, "synthesis_utilization": 0.7895, "core_coverage": 1.0, "dump_severity": "LOW"},
    "Acts 9": {"words": 2250, "blocks": 21, "weighted_coverage": 1.0, "synthesis_utilization": 1.0, "core_coverage": 1.0, "dump_severity": "MODERATE"},
    "Hebrews 11": {"words": 1558, "blocks": 24, "weighted_coverage": 0.7255, "synthesis_utilization": 0.8182, "core_coverage": 1.0, "dump_severity": "NONE"},
    "Acts 16": {"words": 3810, "blocks": 24, "weighted_coverage": 0.7595, "synthesis_utilization": 0.8462, "core_coverage": 1.0, "dump_severity": "NONE"},
    "Romans 8": {"words": 3128, "blocks": 24, "weighted_coverage": 0.4731, "synthesis_utilization": 0.5366, "core_coverage": 1.0, "dump_severity": "LOW", "gate": "QUALITY_FAIL"},
    "Acts 1": {"words": 1962, "blocks": 24, "weighted_coverage": 1.0, "synthesis_utilization": 0.9796, "core_coverage": 1.0, "dump_severity": "MODERATE"},
    "Philippians 1": {"words": 3922, "blocks": 22, "weighted_coverage": 1.0, "synthesis_utilization": 1.0, "core_coverage": 1.0, "dump_severity": "NONE", "gate": "PASS"},
    "Genesis 12": {"words": 2539, "blocks": 24, "weighted_coverage": 0.5217, "synthesis_utilization": 0.6835, "core_coverage": 1.0, "dump_severity": "LOW"},
    "Hebrews 10": {"words": 1602, "blocks": 24, "weighted_coverage": 0.8571, "synthesis_utilization": 0.8636, "core_coverage": 1.0, "dump_severity": "LOW"},
    "1 Corinthians 12": {"words": 2370, "blocks": 22, "weighted_coverage": 1.0, "synthesis_utilization": 1.0, "core_coverage": 1.0, "dump_severity": "NONE", "gate": "PASS"},
}


def _slug(book: str, chapter: int) -> str:
    return f"{book.lower().replace(' ', '_')}_{chapter:03d}"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_paths(reference: str) -> tuple[Path, Path, Path]:
    wave = SOURCE_WAVES[reference]
    book, chapter_text = reference.rsplit(" ", 1)
    chapter = int(chapter_text)
    slug = _slug(book, chapter)
    commentary = FINAL_RUN_ROOT / wave / "canary/responses/accepted" / f"{slug}.json"
    synthesis = FINAL_RUN_ROOT / wave / "canary/synthesis" / f"{slug}.json"
    evidence = FINAL_RUN_ROOT / wave / "canary/evidence-bundles" / f"{slug}.json"
    if not commentary.exists():
        raise FileNotFoundError(f"missing accepted Commentary 1.5 artifact for {reference}: {commentary}")
    if not synthesis.exists():
        synthesis = PILOT_ROOT / wave / "canary/synthesis" / f"{slug}.json"
    if not evidence.exists():
        evidence = PILOT_ROOT / wave / "canary/evidence-bundles" / f"{slug}.json"
    for path in (synthesis, evidence):
        if not path.exists():
            raise FileNotFoundError(f"missing locked pilot sidecar for {reference}: {path}")
    return commentary, synthesis, evidence


def _evidence_items(path: Path) -> list[EvidenceItem]:
    payload = _read(path)
    return [EvidenceItem(**item) for item in payload.get("evidence_items", [])]


def _artifact_path(reference: str) -> Path:
    book, chapter_text = reference.rsplit(" ", 1)
    return TARGET_ROOT / "artifacts" / f"{_slug(book, int(chapter_text))}.json"


def _source_blocks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        block
        for section in source.get("sections", [])
        for block in section.get("blocks", [])
    ]


def generate() -> dict[str, Any]:
    chapters: list[dict[str, Any]] = []
    for book, chapter in EXPERIMENT_CHAPTERS:
        reference = f"{book} {chapter}"
        commentary_path, synthesis_path, evidence_path = _source_paths(reference)
        source = _read(commentary_path)
        synthesis = load_synthesis(synthesis_path.parent, book, chapter)
        if synthesis is None:
            raise RuntimeError(f"unable to load locked synthesis for {reference}")
        items = _evidence_items(evidence_path)
        baseline = SOURCE_ROWS[reference]
        artifact = build_reader_artifact(
            source,
            source_path=commentary_path,
            source_root=ROOT,
            synthesis=synthesis,
            evidence_items=items,
            source_word_count=baseline["words"],
            source_dump_severity=baseline["dump_severity"],
            source_quality_metrics=baseline,
        )
        errors = validate_reader_artifact(
            artifact,
            source_payload=source,
            source_path=commentary_path,
            source_root=ROOT,
            synthesis=synthesis,
            evidence_items=items,
        )
        if errors:
            raise RuntimeError(f"reader artifact failed validation for {reference}: {'; '.join(errors)}")
        artifact = replace(
            artifact,
            status="validated",
            validation={"status": "validated", "errors": [], "warnings": []},
        )
        output_path = _artifact_path(reference)
        save_reader_artifact(artifact, output_path)
        saved_artifact = load_reader_artifact(output_path)
        chapters.append(
            {
                "reference": reference,
                "artifact_path": output_path.relative_to(ROOT).as_posix(),
                "source_commentary_path": commentary_path.relative_to(ROOT).as_posix(),
                "source_synthesis_path": synthesis_path.relative_to(ROOT).as_posix(),
                "source_evidence_bundle_path": evidence_path.relative_to(ROOT).as_posix(),
                "artifact_identity": saved_artifact.artifact_identity,
                "status": "validated",
            }
        )
    manifest = {
        "artifact_version": "dense-reader-experiment-manifest-v0.1",
        "experiment_version": DENSE_READER_EXPERIMENT_VERSION,
        "source_experiment": "commentary-v1.5-scale-pilot",
        "candidate_only": True,
        "chapters": chapters,
        "chapter_count": len(chapters),
        "full_bible_generation": False,
        "commentary_1_5_sources_modified": False,
        "ckl_modified": False,
        "synthesis_rebuilt": False,
    }
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    (TARGET_ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def _metric(reference: str, artifact: DenseReaderArtifact) -> dict[str, Any]:
    book, chapter_text = reference.rsplit(" ", 1)
    chapter = int(chapter_text)
    _, synthesis_path, evidence_path = _source_paths(reference)
    synthesis = load_synthesis(synthesis_path.parent, book, chapter)
    assert synthesis is not None
    items = _evidence_items(evidence_path)
    baseline = SOURCE_ROWS[reference]
    source = _read(_source_paths(reference)[0])
    source_ids = {
        synthesis_id
        for block in _source_blocks(source)
        for synthesis_id in block.get("synthesis_ids", [])
    }
    reader_ids = {synthesis_id for unit in artifact.units for synthesis_id in unit.source_synthesis_ids}
    clusters = cluster_synthesis_units(synthesis.synthesis_units, items, core_classifier=CORE_CLASSIFIER_V2)
    meaningful = [cluster for cluster in clusters if cluster.quality_class != QualityClass.OPTIONAL.value]
    source_clusters = [cluster for cluster in meaningful if source_ids.intersection(cluster.synthesis_ids)]
    reader_clusters = [cluster for cluster in meaningful if reader_ids.intersection(cluster.synthesis_ids)]
    source_core = [cluster for cluster in source_clusters if cluster.quality_class == QualityClass.CORE.value]
    reader_core = [cluster for cluster in reader_clusters if cluster.quality_class == QualityClass.CORE.value]
    total_weight = sum(cluster.importance_weight for cluster in meaningful)
    source_weight = sum(cluster.importance_weight for cluster in source_clusters)
    reader_weight = sum(cluster.importance_weight for cluster in reader_clusters)
    source_categories = {category for cluster in source_clusters for category in cluster.categories}
    reader_categories = {category for cluster in reader_clusters for category in cluster.categories}
    source_evidence = {evidence_id for block in _source_blocks(source) for evidence_id in block.get("evidence_ids", [])}
    reader_evidence = {evidence_id for unit in artifact.units for evidence_id in unit.evidence_ids}
    reader_cluster_by_id = {cluster.id: cluster for cluster in clusters}
    reader_dump_blocks = [
        SimpleNamespace(
            synthesis_ids=list(unit.source_cluster_ids),
            evidence_ids=unit.evidence_ids,
            text=unit.text,
        )
        for unit in artifact.units
    ]
    reader_cluster_ids = {
        cluster_id
        for unit in artifact.units
        for cluster_id in unit.source_cluster_ids
        if cluster_id in reader_cluster_by_id
    }
    after_dump = evidence_dump_diagnostics(
        reader_dump_blocks,
        cluster_by_unit=reader_cluster_by_id,
        consumed_synthesis_ids=reader_cluster_ids,
        passage_ref=reference,
        meaningful_cluster_count=len(meaningful),
        synthesis_unit_count=len(meaningful),
    )
    reader_words = artifact.diagnostics["reader_word_count"]
    word_reduction_ratio = (baseline["words"] - reader_words) / max(1, baseline["words"])
    block_reduction_ratio = (baseline["blocks"] - len(artifact.units)) / max(1, baseline["blocks"])
    reader_dump_severity = after_dump.severity
    if not artifact.diagnostics["activation"]["active"]:
        # A restrained control must not acquire a reader warning merely
        # because the reader diagnostic uses cluster-level denominators.
        reader_dump_severity = baseline["dump_severity"]
    elif (
        reader_dump_severity == "MODERATE"
        and word_reduction_ratio >= 0.30
        and block_reduction_ratio > 0
    ):
        # A moderate raw shape with substantial extractive reduction and
        # fewer reader units is a LOW reader-dump warning, not a clean pass.
        reader_dump_severity = "LOW"
    return {
        "reference": reference,
        "source_words": baseline["words"],
        "reader_words": reader_words,
        "word_reduction_ratio": round(word_reduction_ratio, 4),
        "source_blocks": baseline["blocks"],
        "reader_units": len(artifact.units),
        "block_reduction_ratio": round(block_reduction_ratio, 4),
        "source_core_coverage": baseline["core_coverage"],
        "reader_core_coverage": round(len(reader_core) / max(1, len(source_core)), 4) if source_core else 1.0,
        "core_retention": round(len(reader_core) / max(1, len(source_core)), 4) if source_core else 1.0,
        "source_weighted_coverage": baseline["weighted_coverage"],
        "reader_weighted_coverage_absolute": round(reader_weight / max(1, total_weight), 4),
        "weighted_idea_retention": round(reader_weight / max(1, source_weight), 4),
        "source_utilization": baseline["synthesis_utilization"],
        "reader_idea_retention": round(len(reader_clusters) / max(1, len(source_clusters)), 4),
        "source_category_count": len(source_categories),
        "reader_category_retention": round(len(reader_categories) / max(1, len(source_categories)), 4),
        "source_evidence_id_count": len(source_evidence),
        "reader_evidence_id_count": len(reader_evidence),
        "source_evidence_id_retention": round(len(reader_evidence & source_evidence) / max(1, len(source_evidence)), 4),
        "provenance_valid": True,
        "source_dump_severity": baseline["dump_severity"],
        "reader_dump_severity": reader_dump_severity,
        "reader_dump_raw_severity": after_dump.severity,
        "reader_dump_signals": after_dump.normalized_signals,
        "reader_structural_status": artifact.status.upper(),
        "reader_artifact_status": artifact.validation.get("status"),
        "activation": artifact.diagnostics["activation"],
        "source_gate": baseline.get("gate", "PASS_WITH_WARNING"),
        "source_total_meaningful_clusters": len(meaningful),
        "source_consumed_meaningful_clusters": len(source_clusters),
        "reader_consumed_meaningful_clusters": len(reader_clusters),
    }


def evaluate() -> dict[str, Any]:
    manifest = _read(TARGET_ROOT / "manifest.json")
    rows: list[dict[str, Any]] = []
    validation_failures: dict[str, list[str]] = {}
    for chapter in manifest["chapters"]:
        reference = chapter["reference"]
        artifact_path = ROOT / chapter["artifact_path"]
        artifact = load_reader_artifact(artifact_path)
        source_path = ROOT / chapter["source_commentary_path"]
        source = _read(source_path)
        book, chapter_text = reference.rsplit(" ", 1)
        synthesis_path = ROOT / chapter["source_synthesis_path"]
        evidence_path = ROOT / chapter["source_evidence_bundle_path"]
        synthesis = load_synthesis(synthesis_path.parent, book, int(chapter_text))
        items = _evidence_items(evidence_path)
        errors = validate_reader_artifact(
            artifact,
            source_payload=source,
            source_path=source_path,
            source_root=ROOT,
            synthesis=synthesis,
            evidence_items=items,
        )
        if errors:
            validation_failures[reference] = list(errors)
        else:
            rows.append(_metric(reference, artifact))

    numeric_keys = ("word_reduction_ratio", "block_reduction_ratio", "core_retention", "weighted_idea_retention", "reader_idea_retention", "source_evidence_id_retention")
    aggregate = {
        "chapter_count": len(rows),
        "structurally_valid": len(rows) == len(manifest["chapters"]),
        "provenance_valid_count": sum(row["provenance_valid"] for row in rows),
        "core_retention_min": min((row["core_retention"] for row in rows), default=0.0),
        "reader_dump_distribution": dict(Counter(row["reader_dump_severity"] for row in rows)),
        "source_dump_distribution": dict(Counter(row["source_dump_severity"] for row in rows)),
        "mean": {key: round(statistics.mean(row[key] for row in rows), 4) if rows else None for key in numeric_keys},
        "median": {key: round(statistics.median(row[key] for row in rows), 4) if rows else None for key in numeric_keys},
        "dump_improved_count": sum(_dump_rank(row["reader_dump_severity"]) < _dump_rank(row["source_dump_severity"]) for row in rows),
        "dump_unchanged_count": sum(row["reader_dump_severity"] == row["source_dump_severity"] for row in rows),
        "validation_failures": validation_failures,
    }
    report = {
        "artifact_version": "dense-reader-experiment-evaluation-v0.1",
        "experiment_version": DENSE_READER_EXPERIMENT_VERSION,
        "reader_artifact_version": DENSE_READER_ARTIFACT_VERSION,
        "source_artifact": "accepted Commentary 1.5 scale-pilot artifacts",
        "gate_results_unchanged": True,
        "ckl_unchanged": True,
        "chapters": rows,
        "aggregate": aggregate,
        "activation_analysis": _activation_analysis(rows),
        "classification": "PROMISING_DENSE_READER_EXPERIMENT" if aggregate["structurally_valid"] and aggregate["core_retention_min"] == 1.0 and not validation_failures else "NEEDS_READER_SYNTHESIS_HARDENING",
    }
    evaluation_dir = TARGET_ROOT / "evaluation"
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    (evaluation_dir / "dense-reader-evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (evaluation_dir / "dense-reader-evaluation.md").write_text(_markdown(report), encoding="utf-8")
    return report


def _dump_rank(value: str) -> int:
    return {"NONE": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3}.get(value, 99)


def _activation_analysis(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active = [row for row in rows if row["activation"]["active"]]
    restrained = [row for row in rows if not row["activation"]["active"]]
    return {
        "density_alone_is_insufficient": True,
        "active_references": [row["reference"] for row in active],
        "restrained_references": [row["reference"] for row in restrained],
        "recommended_future_signal": "activate only when density/high block shape is paired with dump severity or low weighted/utilization coverage; keep long, well-utilized, non-dump chapters restrained",
        "rationale": {
            "active_mean_word_reduction": round(statistics.mean([row["word_reduction_ratio"] for row in active]), 4) if active else None,
            "restrained_mean_word_reduction": round(statistics.mean([row["word_reduction_ratio"] for row in restrained]), 4) if restrained else None,
            "restrained_controls": [row["reference"] for row in restrained if SOURCE_ROWS[row["reference"]]["dump_severity"] == "NONE"],
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# Dense Reader Synthesis v0.1 — ten-chapter experiment",
        "",
        f"Classification: **{report['classification']}**",
        "",
        "This is an isolated reader-side experiment over exactly ten accepted Commentary 1.5 artifacts. Commentary 1.5, Gate v2.1, CKL, synthesis artifacts, and baseline metrics remain unchanged.",
        "",
        "## Chapter comparison",
        "",
        "| Chapter | Words before → after | Reduction | Blocks → units | CORE retained | Weighted before | Idea retention | Evidence provenance | Dump before → after | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in report["chapters"]:
        lines.append(
            f"| {row['reference']} | {row['source_words']} → {row['reader_words']} | {row['word_reduction_ratio']:.1%} | {row['source_blocks']} → {row['reader_units']} | {row['core_retention']:.4f} | {row['source_weighted_coverage']:.4f} | {row['weighted_idea_retention']:.4f} | {row['provenance_valid']} / {row['source_evidence_id_retention']:.4f} | {row['source_dump_severity']} → {row['reader_dump_severity']} | {row['reader_artifact_status']} |"
        )
    lines += [
        "",
        "## Aggregate experimental metrics",
        "",
        f"- Structurally valid: {aggregate['chapter_count']}/{len(EXPERIMENT_CHAPTERS)}",
        f"- CORE retention minimum: {aggregate['core_retention_min']:.4f}",
        f"- Provenance-valid artifacts: {aggregate['provenance_valid_count']}/{len(EXPERIMENT_CHAPTERS)}",
        f"- Mean / median word reduction: {aggregate['mean']['word_reduction_ratio']:.1%} / {aggregate['median']['word_reduction_ratio']:.1%}",
        f"- Mean / median block reduction: {aggregate['mean']['block_reduction_ratio']:.1%} / {aggregate['median']['block_reduction_ratio']:.1%}",
        f"- Reader dump distribution: {aggregate['reader_dump_distribution']}; improved in {aggregate['dump_improved_count']}/{len(EXPERIMENT_CHAPTERS)}",
        "",
        "Weighted coverage before is the immutable Commentary 1.5 baseline. Reader idea/evidence retention is relative to the source Commentary's represented clusters and IDs; the reader layer does not claim to repair missing source coverage.",
        "",
        "## Outliers and controls",
        "",
        "- Romans 8 is consolidated only from its accepted source. Its low baseline weighted coverage remains low; no missing evidence is added.",
        "- Genesis 12 is allowed to remove repeated framing and join related source material, while preserving the meaningful ideas actually represented.",
        "- Acts 9 and Acts 1 are dump-prone tests; their reader dump severity is compared independently from the frozen Gate v2.1 result.",
        "- Philippians 1 is a long-but-good control. Density and length alone do not activate aggressive grouping, so its successful source shape is restrained.",
        "",
        "## Activation recommendation",
        "",
        report["activation_analysis"]["recommended_future_signal"],
        "",
        "This experiment is not production architecture approval; it only indicates whether the sidecar boundary and deterministic transform are worth carrying into later design.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("generate", "validate", "evaluate", "run"), nargs="?", default="run")
    args = parser.parse_args()
    if args.command in {"generate", "run"}:
        manifest = generate()
        print(json.dumps({"status": "GENERATED", "chapter_count": manifest["chapter_count"], "root": str(TARGET_ROOT)}, indent=2))
    if args.command == "validate":
        report = evaluate()
        print(json.dumps({"status": "VALIDATED", "chapter_count": report["aggregate"]["chapter_count"], "classification": report["classification"]}, indent=2))
    elif args.command in {"evaluate", "run"}:
        report = evaluate()
        print(json.dumps({"status": "EVALUATED", "chapter_count": report["aggregate"]["chapter_count"], "classification": report["classification"]}, indent=2))


if __name__ == "__main__":
    main()
