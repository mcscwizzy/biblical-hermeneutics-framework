#!/usr/bin/env python3
"""Freeze, import, and evaluate the five-case Sol renderer remediation.

This is an isolated candidate-contract harness.  It does not mutate the active
production prompt, the prior 21-chapter qualification, or production outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.models import (
    COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    GeneratedMetadata,
)
from bhf_agent.chapter_commentary.prompts import build_user_prompt, system_prompt_for_version
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    assess_gate_v2,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from framework.commentary.production.inputs import prepare_chapter
from framework.commentary.production.models import (
    ArtifactCollisionError,
    sha256_bytes,
    sha256_json,
    slug,
    write_immutable,
)
from tools import commentary_renderer_qualification as qualification


ARTIFACT_VERSION = "commentary-renderer-remediation-v1"
IMPORT_VERSION = "commentary-renderer-remediation-import-v1"
EVALUATION_VERSION = "commentary-renderer-remediation-evaluation-v1"
PREVIOUS_QUALIFICATION_ID = "renderer-qualification-v1-gpt-5.6-sol-a0f4063638cf9730958a"
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
EXPECTED_REFERENCES = (
    "Exodus 14",
    "Deuteronomy 10",
    "Job 1",
    "1 Corinthians 14",
    "Revelation 21",
)
DEFAULT_ROOT = (
    ROOT
    / ".bhf-data/bhf-commentary-candidates/renderer-contract-remediation-v1"
    / RENDERER
    / f"prompt-{COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION}"
)
HARD_PROVENANCE_CODES = frozenset(
    {
        "UNKNOWN_EVIDENCE_ID",
        "UNKNOWN_SYNTHESIS_ID",
        "SYNTHESIS_ANCESTRY_MISMATCH",
        "SYNTHESIS_HASH_MISMATCH",
        "CONFIDENCE_EXCEEDS_EVIDENCE",
        "DISPUTED_AS_FACT",
        "INVENTED_SIGNIFICANCE",
        "UNSUPPORTED_DATE",
        "UNSUPPORTED_ENTITY",
        "UNANCHORED_CLAIM",
        "OUT_OF_CHAPTER_SYNTHESIS_REFERENCE",
    }
)


class RemediationError(RuntimeError):
    """The bounded remediation input or output is incomplete or changed."""


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RemediationError(f"invalid JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RemediationError(f"JSON artifact must be an object: {path}")
    return value


def _write_json_immutable(path: Path, value: Any) -> str:
    return write_immutable(path, _json_bytes(value))


def _old_context(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    old_root = qualification._root(repo_root)
    old_manifest = _read(old_root / "qualification-manifest.json")
    qualification._verify_qualification_manifest(old_manifest)
    if old_manifest.get("qualification_id") != PREVIOUS_QUALIFICATION_ID:
        raise RemediationError("previous qualification ID mismatch")
    current = qualification.build_qualification_manifest(repo_root)
    if current != old_manifest:
        raise RemediationError("previous frozen qualification inputs changed")
    old_evaluation = _read(old_root / "evaluation/evaluation.json")
    if old_evaluation.get("qualification_id") != PREVIOUS_QUALIFICATION_ID:
        raise RemediationError("previous evaluation qualification ID mismatch")
    return old_manifest, old_evaluation


def _candidate_packet(repo_root: Path, old_row: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    prepared = prepare_chapter(old_row["book"], int(old_row["chapter"]))
    old_identity = prepared.row["input_identity"]
    if old_identity.get("packet_id") != old_row.get("packet_id"):
        raise RemediationError(f"source packet ID mismatch for {old_row['reference']}")
    if old_identity.get("packet_hash") != old_row.get("packet_hash"):
        raise RemediationError(f"source packet hash mismatch for {old_row['reference']}")
    chapter_data = bible.resolve_chapter(old_row["book"], int(old_row["chapter"]))
    canonical_text = bible.passage_text(chapter_data.get("verses", []))
    system_prompt = system_prompt_for_version(COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION)
    user_prompt = build_user_prompt(
        old_row["reference"],
        old_row["book"],
        int(old_row["chapter"]),
        canonical_text,
        prepared.synthesis,
        prepared.bundle,
        prepared.synthesis.evidence_availability,
        prompt_version=COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
    )
    packet_base = {
        "artifact_version": "commentary-renderer-remediation-packet-v1",
        "previous_qualification_id": PREVIOUS_QUALIFICATION_ID,
        "reference": old_row["reference"],
        "book": old_row["book"],
        "chapter": int(old_row["chapter"]),
        "candidate_only": True,
        "generation_authorized": False,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "commentary_prompt_version": COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "evidence_bundle_version": prepared.bundle.version,
        "evidence_availability": prepared.synthesis.evidence_availability,
        "evidence_count": len(prepared.bundle.evidence_items),
        "evidence_hash": prepared.bundle.evidence_hash,
        "synthesis_hash": prepared.synthesis.synthesis_hash,
        "synthesis_schema_version": prepared.synthesis.synthesis_schema_version,
        "synthesis_compiler_version": prepared.synthesis.synthesis_compiler_version,
        "gate_version": old_identity["gate_version"],
        "validator_identity": old_identity["validator_identity"],
        "synthesis_unit_count": len(prepared.synthesis.synthesis_units),
        "source_packet_id": old_row["packet_id"],
        "source_packet_hash": old_row["packet_hash"],
    }
    packet_hash = sha256_json(packet_base)
    packet = {
        **packet_base,
        "packet_id": f"commentary-renderer-remediation-v1-packet:{packet_hash}",
        "packet_hash": packet_hash,
    }
    return packet, prepared


def build_manifest(repo_root: Path = ROOT) -> tuple[dict[str, Any], list[tuple[dict[str, Any], Any]]]:
    """Reconstruct the five candidate packets and their complete identity."""

    old_manifest, _ = _old_context(repo_root)
    old_by_reference = {row["reference"]: row for row in old_manifest["chapters"]}
    material: list[tuple[dict[str, Any], Any]] = []
    rows: list[dict[str, Any]] = []
    for ordinal, reference in enumerate(EXPECTED_REFERENCES, 1):
        old_row = old_by_reference.get(reference)
        if old_row is None:
            raise RemediationError(f"previous qualification lacks {reference}")
        packet, prepared = _candidate_packet(repo_root, old_row)
        filename = f"{ordinal:03d}_{slug(packet['book'], packet['chapter'])}.json"
        packet_bytes = _json_bytes(packet)
        row = {
            "ordinal": ordinal,
            "source_qualification_ordinal": old_row["ordinal"],
            "reference": reference,
            "book": packet["book"],
            "chapter": packet["chapter"],
            "packet_filename": filename,
            "response_filename": filename,
            "packet_id": packet["packet_id"],
            "packet_hash": packet["packet_hash"],
            "packet_file_sha256": sha256_bytes(packet_bytes),
            "source_packet_id": packet["source_packet_id"],
            "source_packet_hash": packet["source_packet_hash"],
            "evidence_hash": packet["evidence_hash"],
            "synthesis_hash": packet["synthesis_hash"],
        }
        rows.append(row)
        material.append((packet, prepared))
    system_hash = sha256_bytes(
        system_prompt_for_version(COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION).encode("utf-8")
    )
    remediation_seed = sha256_json(
        {
            "artifact_version": ARTIFACT_VERSION,
            "previous_qualification_id": PREVIOUS_QUALIFICATION_ID,
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
            "prompt_version": COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
            "system_prompt_sha256": system_hash,
            "packet_hashes": [row["packet_hash"] for row in rows],
        }
    )
    manifest = {
        "artifact_version": ARTIFACT_VERSION,
        "remediation_id": f"renderer-remediation-v1-{RENDERER}-{remediation_seed[:20]}",
        "previous_qualification_id": PREVIOUS_QUALIFICATION_ID,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "generation_authorized": False,
        "bulk_generation_authorized": False,
        "contract_versions": {
            "old_commentary_prompt_version": "1.5",
            "candidate_commentary_prompt_version": COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "synthesis_schema_version": "1.1",
            "synthesis_compiler_version": "1.1",
            "gate_version": "commentary-richness-gate-v2.1",
        },
        "system_prompt_sha256": system_hash,
        "chapter_count": len(rows),
        "chapters": rows,
    }
    manifest["manifest_identity"] = sha256_json(manifest)
    return manifest, material


def _verify_manifest(manifest: dict[str, Any]) -> None:
    identity = manifest.get("manifest_identity")
    expected = sha256_json({key: value for key, value in manifest.items() if key != "manifest_identity"})
    if identity != expected:
        raise RemediationError("remediation manifest identity mismatch")
    if manifest.get("artifact_version") != ARTIFACT_VERSION:
        raise RemediationError("unsupported remediation artifact version")
    if manifest.get("previous_qualification_id") != PREVIOUS_QUALIFICATION_ID:
        raise RemediationError("previous qualification identity mismatch")
    if manifest.get("renderer") != RENDERER or manifest.get("renderer_effort") != RENDERER_EFFORT:
        raise RemediationError("renderer identity or effort mismatch")
    rows = manifest.get("chapters")
    if not isinstance(rows, list) or len(rows) != 5:
        raise RemediationError("remediation must contain exactly five chapters")
    if [row.get("reference") for row in rows] != list(EXPECTED_REFERENCES):
        raise RemediationError("remediation chapter order or membership mismatch")


def prepare(*, repo_root: Path = ROOT, remediation_root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    """Freeze five candidate packets and exact text handoffs immutably."""

    manifest, material = build_manifest(repo_root)
    _verify_manifest(manifest)
    _write_json_immutable(remediation_root / "manifest.json", manifest)
    handoff_items: list[dict[str, Any]] = []
    for row, (packet, _) in zip(manifest["chapters"], material, strict=True):
        packet_bytes = _json_bytes(packet)
        if sha256_bytes(packet_bytes) != row["packet_file_sha256"]:
            raise RemediationError(f"candidate packet serialization drift for {row['reference']}")
        _write_json_immutable(remediation_root / "packets" / row["packet_filename"], packet)
        stem = Path(row["packet_filename"]).stem
        handoff = remediation_root / "handoff" / stem
        system_bytes = packet["system_prompt"].encode("utf-8")
        user_bytes = packet["user_prompt"].encode("utf-8")
        write_immutable(handoff / "system_prompt.txt", system_bytes)
        write_immutable(handoff / "user_prompt.txt", user_bytes)
        metadata = {
            **row,
            "remediation_id": manifest["remediation_id"],
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
            "commentary_prompt_version": COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "system_prompt_sha256": sha256_bytes(system_bytes),
            "user_prompt_sha256": sha256_bytes(user_bytes),
        }
        _write_json_immutable(handoff / "metadata.json", metadata)
        handoff_items.append(
            {
                "ordinal": row["ordinal"],
                "reference": row["reference"],
                "directory": f"handoff/{stem}",
                "response_filename": row["response_filename"],
                "packet_id": row["packet_id"],
                "packet_hash": row["packet_hash"],
                "system_prompt_sha256": metadata["system_prompt_sha256"],
                "user_prompt_sha256": metadata["user_prompt_sha256"],
            }
        )
    handoff_manifest = {
        "artifact_version": "commentary-renderer-remediation-handoff-v1",
        "remediation_id": manifest["remediation_id"],
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "items": handoff_items,
    }
    handoff_manifest["handoff_identity"] = sha256_json(handoff_manifest)
    _write_json_immutable(remediation_root / "handoff/manifest.json", handoff_manifest)
    return {
        "status": "PREPARED",
        "remediation_id": manifest["remediation_id"],
        "chapter_count": 5,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "root": str(remediation_root),
    }


def import_responses(
    source_dir: Path,
    *,
    repo_root: Path = ROOT,
    remediation_root: Path = DEFAULT_ROOT,
) -> dict[str, Any]:
    """Immutably import exactly five unmodified renderer response files."""

    manifest = _read(remediation_root / "manifest.json")
    _verify_manifest(manifest)
    current, _ = build_manifest(repo_root)
    if current != manifest:
        raise RemediationError("frozen remediation inputs changed before response import")
    expected = {row["response_filename"] for row in manifest["chapters"]}
    actual = {path.name for path in source_dir.glob("*.json") if path.is_file()}
    if actual != expected:
        raise RemediationError(
            f"response filenames mismatch; missing={sorted(expected - actual)}; extra={sorted(actual - expected)}"
        )
    rows = []
    for row in manifest["chapters"]:
        raw = (source_dir / row["response_filename"]).read_bytes()
        destination = remediation_root / "responses/raw" / row["response_filename"]
        digest = write_immutable(destination, raw)
        rows.append(
            {
                "ordinal": row["ordinal"],
                "reference": row["reference"],
                "packet_id": row["packet_id"],
                "packet_hash": row["packet_hash"],
                "response_filename": row["response_filename"],
                "raw_sha256": digest,
            }
        )
    receipt = {
        "artifact_version": IMPORT_VERSION,
        "remediation_id": manifest["remediation_id"],
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "response_count": len(rows),
        "raw_responses_immutable": True,
        "responses": rows,
    }
    _write_json_immutable(remediation_root / "responses/import-receipt.json", receipt)
    return {
        "status": "IMPORTED",
        "remediation_id": manifest["remediation_id"],
        "response_count": len(rows),
        "raw_responses_immutable": True,
    }


def _codes(errors: Iterable[str]) -> list[str]:
    values = []
    for error in errors:
        code = str(error).split(":", 1)[0].strip()
        if code.isupper() and " " not in code:
            values.append(code)
    return sorted(set(values))


def _empty_metrics(row: dict[str, Any], codes: list[str]) -> dict[str, Any]:
    return {
        "reference": row["reference"],
        "structural_result": "REJECTED",
        "rejection_codes": codes,
        "weighted_coverage": None,
        "core_coverage": None,
        "synthesis_utilization": None,
        "category_coverage": None,
        "dump_severity": None,
        "word_count": None,
        "block_count": None,
        "quality_gate_outcome": None,
        "gate_v2_1": None,
    }


def _evaluate_one(row: dict[str, Any], raw: bytes, prepared: Any) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _empty_metrics(row, ["MALFORMED_RESPONSE_JSON"])
    if not isinstance(payload, dict):
        return _empty_metrics(row, ["MALFORMED_RESPONSE_JSON"])
    payload = dict(payload)
    payload["generated_metadata"] = GeneratedMetadata(
        evidence_hash=prepared.bundle.evidence_hash,
        evidence_bundle_version=prepared.bundle.version,
        commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
        commentary_prompt_version=COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
        model="external_handoff",
        generated_timestamp=None,
        synthesis_hash=prepared.synthesis.synthesis_hash,
        synthesis_schema_version=prepared.synthesis.synthesis_schema_version,
        synthesis_compiler_version=prepared.synthesis.synthesis_compiler_version,
        renderer_label=RENDERER,
    ).to_dict()
    payload["evidence_availability"] = prepared.synthesis.evidence_availability
    payload["status"] = "pending"
    validation = validate_chapter_commentary(
        payload,
        prepared.bundle,
        expected_evidence_hash=prepared.bundle.evidence_hash,
        expected_prompt_version=COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
        expected_reference=row["reference"],
        expected_book=row["book"],
        expected_chapter=int(row["chapter"]),
        synthesis=prepared.synthesis,
        expected_synthesis_hash=prepared.synthesis.synthesis_hash,
    )
    if not validation.valid or validation.commentary is None:
        return _empty_metrics(row, _codes(validation.errors) or ["VALIDATION_FAILED"])
    blocks = [block for section in validation.commentary.sections for block in section.blocks]
    audit = audit_chapter(row["book"], int(row["chapter"]), validation.commentary, prepared.bundle)
    score = score_synthesis_richness(
        prepared.synthesis.synthesis_units,
        evidence_items=prepared.bundle.evidence_items,
        consumed_synthesis_ids=[sid for block in blocks for sid in block.synthesis_ids],
        blocks=blocks,
        passage_ref=row["reference"],
        core_classifier=CORE_CLASSIFIER_V2,
    )
    safety = {
        name: True
        for name in (
            "validation_clean",
            "provenance_complete",
            "hashes_valid",
            "chapter_boundaries_valid",
            "confidence_valid",
            "dispute_state_preserved",
            "unsupported_significance_absent",
        )
    }
    gate = assess_gate_v2(
        score=score,
        evidence_availability=prepared.synthesis.evidence_availability,
        baseline_richness="SYNTHESIS_GAP",
        after_richness=audit["richness_status"],
        safety_checks=safety,
        evidence_use_delta=audit["unique_evidence_ids_consumed"],
        section_delta=audit["section_count"],
        commentary_word_count=audit["commentary_prose_word_count"],
        unique_evidence_ids_consumed=audit["unique_evidence_ids_consumed"],
    )
    return {
        "reference": row["reference"],
        "structural_result": "ACCEPTED",
        "rejection_codes": [],
        "weighted_coverage": score.weighted_idea_coverage,
        "core_coverage": score.core_cluster_coverage,
        "synthesis_utilization": score.raw_synthesis_coverage,
        "category_coverage": score.category_coverage,
        "dump_severity": score.dump_diagnostics.severity,
        "word_count": audit["commentary_prose_word_count"],
        "block_count": audit["commentary_block_count"],
        "quality_gate_outcome": gate.outcome,
        "gate_v2_1": gate.to_dict(),
        "score": score.to_dict(),
        "audit": audit,
    }


def evaluate(*, repo_root: Path = ROOT, remediation_root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    """Run unchanged validation, scoring, and Gate v2.1 over imported bytes."""

    manifest = _read(remediation_root / "manifest.json")
    _verify_manifest(manifest)
    current, material = build_manifest(repo_root)
    if current != manifest:
        raise RemediationError("frozen remediation inputs changed before evaluation")
    receipt = _read(remediation_root / "responses/import-receipt.json")
    if receipt.get("remediation_id") != manifest["remediation_id"] or receipt.get("response_count") != 5:
        raise RemediationError("five-response immutable import is absent or mismatched")
    old_manifest, old_evaluation = _old_context(repo_root)
    old_rows = {row["reference"]: row for row in old_evaluation["chapters"]}
    old_manifest_rows = {row["reference"]: row for row in old_manifest["chapters"]}
    results = []
    comparisons = []
    for row, (_, prepared) in zip(manifest["chapters"], material, strict=True):
        if row["source_packet_id"] != old_manifest_rows[row["reference"]]["packet_id"]:
            raise RemediationError(f"old/new source identity mismatch for {row['reference']}")
        raw_path = remediation_root / "responses/raw" / row["response_filename"]
        if not raw_path.is_file():
            raise RemediationError(f"missing immutable response for {row['reference']}")
        raw = raw_path.read_bytes()
        receipt_row = next(item for item in receipt["responses"] if item["reference"] == row["reference"])
        if sha256_bytes(raw) != receipt_row["raw_sha256"]:
            raise RemediationError(f"raw response changed after import for {row['reference']}")
        new = _evaluate_one(row, raw, prepared)
        new["raw_sha256"] = sha256_bytes(raw)
        new["packet_id"] = row["packet_id"]
        new["packet_hash"] = row["packet_hash"]
        old = old_rows[row["reference"]]
        comparisons.append(
            {
                "reference": row["reference"],
                "old_prompt_1_5": {
                    key: old.get(key)
                    for key in (
                        "structural_result",
                        "rejection_codes",
                        "weighted_coverage",
                        "core_coverage",
                        "synthesis_utilization",
                        "category_coverage",
                        "dump_severity",
                        "word_count",
                        "block_count",
                    )
                }
                | {"quality_gate_outcome": (old.get("gate_v2_1") or {}).get("outcome")},
                "new_prompt_1_6": {
                    key: new.get(key)
                    for key in (
                        "structural_result",
                        "rejection_codes",
                        "weighted_coverage",
                        "core_coverage",
                        "synthesis_utilization",
                        "category_coverage",
                        "dump_severity",
                        "word_count",
                        "block_count",
                        "quality_gate_outcome",
                    )
                },
            }
        )
        results.append(new)
    rejection_counts = Counter(code for row in results for code in row["rejection_codes"])
    quality_targets = [row for row in results if row["reference"] != "1 Corinthians 14"]
    old_quality = {row["reference"]: old_rows[row["reference"]] for row in quality_targets}
    materially_improved = all(
        isinstance(row.get("weighted_coverage"), (int, float))
        and row["weighted_coverage"] > old_quality[row["reference"]]["weighted_coverage"]
        and row.get("quality_gate_outcome") != "QUALITY_FAIL"
        for row in quality_targets
    )
    structurally_valid = sum(row["structural_result"] == "ACCEPTED" for row in results)
    high_dump_count = sum(row.get("dump_severity") == "HIGH" for row in results)
    quality_fail_count = sum(row.get("quality_gate_outcome") == "QUALITY_FAIL" for row in results)
    hard_codes = sorted(code for code in rejection_counts if code in HARD_PROVENANCE_CODES)
    one_corinthians = next(row for row in results if row["reference"] == "1 Corinthians 14")
    core_ok = all(
        isinstance(row.get("core_coverage"), (int, float)) and row["core_coverage"] >= 0.98
        for row in results
    )
    bounded_pass = (
        structurally_valid == 5
        and "SYNTHESIS_ANCESTRY_MISMATCH" not in one_corinthians["rejection_codes"]
        and not hard_codes
        and high_dump_count == 0
        and core_ok
        and materially_improved
        and quality_fail_count == 0
    )
    report = {
        "artifact_version": EVALUATION_VERSION,
        "remediation_id": manifest["remediation_id"],
        "previous_qualification_id": PREVIOUS_QUALIFICATION_ID,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "contracts": manifest["contract_versions"],
        "chapters": results,
        "before_after": comparisons,
        "summary": {
            "chapter_count": 5,
            "structurally_valid": structurally_valid,
            "structural_failures": 5 - structurally_valid,
            "rejection_codes": dict(rejection_counts),
            "hard_provenance_codes": hard_codes,
            "quality_failures": quality_fail_count,
            "high_dump_count": high_dump_count,
            "core_coverage_minimum_met": core_ok,
            "four_quality_cases_materially_improved": materially_improved,
            "four_quality_cases_at_or_above_0_75": sum(
                isinstance(row.get("weighted_coverage"), (int, float))
                and row["weighted_coverage"] >= 0.75
                for row in quality_targets
            ),
            "one_corinthians_14_ancestry_result": (
                "PASS"
                if "SYNTHESIS_ANCESTRY_MISMATCH" not in one_corinthians["rejection_codes"]
                and one_corinthians["structural_result"] == "ACCEPTED"
                else "FAIL"
            ),
        },
        "bounded_result": (
            "FIVE_CHAPTER_REMEDIATION_PASS"
            if bounded_pass
            else "FIVE_CHAPTER_REMEDIATION_FAILED"
        ),
    }
    _write_json_immutable(remediation_root / "evaluation/evaluation.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remediation-root", type=Path, default=DEFAULT_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare", help="freeze the exact five candidate prompt packets")
    importer = subparsers.add_parser("import", help="immutably import five raw Sol responses")
    importer.add_argument("--source-dir", type=Path, required=True)
    subparsers.add_parser("evaluate", help="run unchanged validation, scoring, and Gate v2.1")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(remediation_root=args.remediation_root)
        elif args.command == "import":
            result = import_responses(args.source_dir, remediation_root=args.remediation_root)
        else:
            result = evaluate(remediation_root=args.remediation_root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (RemediationError, qualification.QualificationError, ArtifactCollisionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
