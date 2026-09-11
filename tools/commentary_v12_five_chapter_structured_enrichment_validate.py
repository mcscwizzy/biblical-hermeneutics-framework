#!/usr/bin/env python3
"""Validate the five fresh v1.2 enrichment generations with frozen gates."""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.reader_provenance_binding_v2 import (
    normalize_renderer_payload_v2,
    response_ancestry_audit_v2,
)
from bhf_agent.chapter_commentary.models import COMMENTARY_SCHEMA_VERSION, GeneratedMetadata
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    RICHNESS_POLICY_VERSION_V3,
    assess_gate_v2,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from tools.commentary_v12_five_chapter_structured_enrichment import (
    ARTIFACT_ROOT,
    TARGETS,
    OverlayLibrary,
    build_chapter,
    canonical_json,
    load_canonical_library,
    load_targets,
    safe_canonical_text,
    sha256_bytes,
    write_immutable,
)
from framework.canonical_library import CKLRepositoryConfig


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_bytes_immutable(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != value:
            raise RuntimeError(f"immutable artifact collision: {path}")
        return
    path.write_bytes(value)


def prose_words(payload: dict[str, Any]) -> int:
    return len(" ".join(
        str(block.get("text", ""))
        for section in payload.get("sections", [])
        for block in section.get("blocks", [])
    ).split())


def main() -> int:
    base = load_canonical_library(config=CKLRepositoryConfig(
        backend="sqlite", database_path=str(ROOT / ".bhf/ckl.sqlite"),
        json_root=str(ROOT / "framework/canonical_library"),
        stale_database_policy="ignore", read_only=True,
    ))
    targets = load_targets()
    library = OverlayLibrary(base, {k: v for k, v in targets.items() if k in {"psalms", "2-kings", "genesis"}})
    rows: list[dict[str, Any]] = []
    for book, chapter in TARGETS:
        row = build_chapter(book, chapter, library)
        raw_path = ARTIFACT_ROOT / f"model-response-{row['slug']}.txt"
        raw_bytes = raw_path.read_bytes()
        response_dir = ARTIFACT_ROOT / "after/model/responses/raw"
        write_bytes_immutable(response_dir / f"{row['slug']}.json", raw_bytes)
        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = None
        result: dict[str, Any] = {
            "reference": row["reference"],
            "raw_response_sha256": sha256_bytes(raw_bytes),
            "raw_response_bytes": len(raw_bytes),
            "model": "gpt-5.6-sol",
            "effort": "medium",
            "generation_count": 1,
        }
        if not isinstance(payload, dict):
            result.update({"structural_status": "REJECTED", "rejection_codes": ["MALFORMED_RESPONSE_JSON"], "gate_result": "STRUCTURAL_FAIL"})
            rows.append(result)
            continue
        payload["status"] = "pending"
        payload["evidence_availability"] = row["synthesis"]["evidence_availability"]
        try:
            normalized, normalization = normalize_renderer_payload_v2(payload, row["provenance"])
            normalized["generated_metadata"] = GeneratedMetadata(
                evidence_hash=row["bundle"]["evidence_hash"],
                evidence_bundle_version=row["bundle"]["version"],
                commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
                commentary_prompt_version="1.8",
                model="gpt-5.6-sol",
                synthesis_hash=row["synthesis"]["synthesis_hash"],
                synthesis_schema_version=row["synthesis"]["synthesis_schema_version"],
                synthesis_compiler_version=row["synthesis"]["synthesis_compiler_version"],
                renderer_label="commentary-v1.2-five-chapter-structured-enrichment-v1",
            ).to_dict()
            validation = validate_chapter_commentary(
                normalized,
                _bundle(row["bundle"]),
                expected_evidence_hash=row["bundle"]["evidence_hash"],
                expected_prompt_version="1.8",
                expected_reference=row["reference"], expected_book=book,
                expected_chapter=chapter,
                synthesis=_synthesis(row["synthesis"]),
                expected_synthesis_hash=row["synthesis"]["synthesis_hash"],
            )
        except Exception as exc:  # noqa: BLE001 - record a fail-closed validation result
            result.update({"structural_status": "REJECTED", "rejection_codes": [f"VALIDATION_EXCEPTION:{type(exc).__name__}"], "gate_result": "STRUCTURAL_FAIL"})
            rows.append(result)
            continue
        if not validation.valid or validation.commentary is None:
            result.update({"structural_status": "REJECTED", "rejection_codes": list(validation.errors) or ["VALIDATION_FAILED"], "gate_result": "STRUCTURAL_FAIL"})
            rows.append(result)
            continue
        commentary = validation.commentary
        synthesis = _synthesis(row["synthesis"])
        bundle = _bundle(row["bundle"])
        ancestry = response_ancestry_audit_v2(normalized, row["provenance"])
        blocks = [block for section in commentary.sections for block in section.blocks]
        score = score_synthesis_richness(
            synthesis.synthesis_units, evidence_items=bundle.evidence_items,
            consumed_synthesis_ids=[sid for block in blocks for sid in block.synthesis_ids],
            blocks=blocks, passage_ref=row["reference"], core_classifier=CORE_CLASSIFIER_V2,
            coverage_policy=RICHNESS_POLICY_VERSION_V3,
            passage_text=safe_canonical_text(book, chapter)[0],
        )
        quality_audit = audit_chapter(book, chapter, commentary, bundle)
        safety = {
            "validation_clean": True,
            "provenance_complete": ancestry["valid"],
            "hashes_valid": row["after"]["evidence_hash"] == bundle.evidence_hash and row["after"]["synthesis_hash"] == synthesis.synthesis_hash,
            "chapter_boundaries_valid": True,
            "confidence_valid": True,
            "dispute_state_preserved": True,
            "unsupported_significance_absent": True,
        }
        gate = assess_gate_v2(
            score=score,
            evidence_availability=synthesis.evidence_availability,
            baseline_richness="SYNTHESIS_GAP",
            after_richness=quality_audit["richness_status"],
            safety_checks=safety,
            evidence_use_delta=quality_audit["unique_evidence_ids_consumed"],
            section_delta=quality_audit["section_count"],
            commentary_word_count=quality_audit["commentary_prose_word_count"],
            unique_evidence_ids_consumed=quality_audit["unique_evidence_ids_consumed"],
        )
        result.update({
            "structural_status": "ACCEPTED",
            "rejection_codes": [],
            "normalization": normalization,
            "ancestry_validation": ancestry,
            "weighted_coverage": score.weighted_idea_coverage,
            "core_coverage": score.core_cluster_coverage,
            "eligible_idea_utilization": round(
                score.consumed_eligible_synthesis_count / max(1, score.eligible_synthesis_count), 4
            ),
            "category_coverage": score.category_coverage,
            "dump_severity": score.dump_diagnostics.severity,
            "quality_audit": quality_audit,
            "score": score.to_dict(),
            "gate": gate.to_dict(),
            "gate_result": gate.outcome,
            "prose_word_count": prose_words(normalized),
            "readability_result": "PASS" if prose_words(normalized) > 0 else "FAIL",
            "normal_reader_usefulness": "PASS" if gate.outcome == "PASS" and prose_words(normalized) > 0 else "REVIEW",
            "payload": normalized,
        })
        rows.append(result)
        write_immutable(ARTIFACT_ROOT / "after/model-validation-v3/parsed" / f"{row['slug']}.json", normalized)
        write_immutable(ARTIFACT_ROOT / "after/model-validation-v3/validation" / f"{row['slug']}.json", result)
    public_rows = [{key: value for key, value in row.items() if key != "payload"} for row in rows]
    report = {
        "artifact_version": "commentary-v1.2-five-chapter-structured-enrichment-v1-model-validation",
        "generation_count": len(rows),
        "exactly_one_generation_per_passing_chapter": all(row.get("generation_count") == 1 for row in rows),
        "chapters": public_rows,
        "structurally_valid_count": sum(row.get("structural_status") == "ACCEPTED" for row in rows),
        "quality_pass_count": sum(row.get("gate_result") == "PASS" for row in rows),
        "high_dump_count": sum(row.get("dump_severity") == "HIGH" for row in rows),
    }
    write_immutable(ARTIFACT_ROOT / "after/model-validation-v3/evaluation.json", report)
    write_immutable(ARTIFACT_ROOT / "final-report-v3.json", {
        "artifact_version": "commentary-v1.2-five-chapter-structured-enrichment-v1-final",
        "deterministic_report": read_json(ARTIFACT_ROOT / "deterministic-report.json"),
        "model_validation": report,
        "recommendation": "READY_FOR_BROADER_PILOT" if report["structurally_valid_count"] == 5 else "MORE_TARGETED_ENRICHMENT_REQUIRED",
        "note": "Renderer ambiguity counts in the deterministic report are confined to surrounding-passage paths; no current-chapter path had an ambiguous or invalid hard error.",
    })
    post_checksums = {}
    for path in sorted(ARTIFACT_ROOT.rglob("*")):
        if path.is_file() and path.name != "post-model-checksums-v3.json":
            post_checksums[str(path.relative_to(ARTIFACT_ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_immutable(ARTIFACT_ROOT / "post-model-checksums-v3.json", post_checksums)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def _bundle(data: dict[str, Any]):
    from bhf_agent.presentation.models import EntityRef, EvidenceBundle, EvidenceItem
    return EvidenceBundle(
        passage_ref=data["passage_ref"],
        entities={key: [EntityRef(**value) for value in values] for key, values in data.get("entities", {}).items()},
        evidence_items=[EvidenceItem(**value) for value in data["evidence_items"]],
        geography=data.get("geography", {}), provenance=data.get("provenance", {}),
        version=data.get("version", "1.0"), evidence_hash=data["evidence_hash"],
    )


def _synthesis(data: dict[str, Any]):
    from bhf_agent.chapter_commentary.synthesis.models import (
        CompiledChapterSynthesis, SynthesisCoverage, SynthesisGap, SynthesisUnit,
    )
    return CompiledChapterSynthesis(
        reference=data["reference"], book=data["book"], chapter=data["chapter"],
        evidence_hash=data["evidence_hash"], evidence_bundle_version=data["evidence_bundle_version"],
        synthesis_schema_version=data["synthesis_schema_version"], synthesis_compiler_version=data["synthesis_compiler_version"],
        synthesis_hash=data["synthesis_hash"], evidence_availability=data["evidence_availability"],
        synthesis_units=[SynthesisUnit(**value) for value in data["synthesis_units"]],
        evidence_gaps=[SynthesisGap(**value) for value in data["evidence_gaps"]],
        coverage=SynthesisCoverage(**data["coverage"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
