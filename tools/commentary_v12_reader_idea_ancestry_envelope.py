#!/usr/bin/env python3
"""Run the bounded 1 Corinthians 14 ancestry-envelope diagnostic.

This tool is downstream of the frozen seven-chapter projection diagnostic.  It
adds only a relational renderer presentation, captures one fresh response, and
evaluates that response with the existing validator, scorer, and Gate v2.1
implementation.  It never writes to the source projection namespace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.prompts import system_prompt_for_version
from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_IMPLEMENTATION,
    READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
    add_ancestry_envelope_to_prompt,
    audit_ancestry_envelope,
    build_ancestry_envelope,
    response_ancestry_audit,
)
from framework.commentary.production.inputs import prepare_chapter
from framework.commentary.production.models import (
    ArtifactCollisionError,
    canonical_json,
    sha256_bytes,
    sha256_json,
    write_immutable,
)
from tools import commentary_v12_reader_projection_seven_chapter as projection_validation
from tools import commentary_renderer_selection_breadth_diagnostic as renderer_validation


ARTIFACT_VERSION = "reader-idea-ancestry-envelope-diagnostic-v1"
PROMPT_VERSION = "1.7"
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
REFERENCE = "1 Corinthians 14"
BOOK = "1 Corinthians"
CHAPTER = 14
SOURCE_NAMESPACE = (
    ".bhf-data/bhf-commentary-candidates/"
    "reader-level-idea-projection-v1-seven-chapter-e01fcbe6fe39ba6949fc"
)
SOURCE_ROOT = ROOT / SOURCE_NAMESPACE
SOURCE_PROJECTION_PATH = SOURCE_ROOT / "projections/1_corinthians_014.json"
SOURCE_RENDERER_INPUT = SOURCE_ROOT / "renderer-input/003_1_corinthians_014"
SOURCE_USER_PROMPT = SOURCE_RENDERER_INPUT / "user_prompt.txt"
SOURCE_SYSTEM_PROMPT = SOURCE_RENDERER_INPUT / "system_prompt.txt"
SOURCE_METADATA = SOURCE_RENDERER_INPUT / "metadata.json"
TARGET_FILENAME = "1_corinthians_014.json"


class DiagnosticError(RuntimeError):
    """Raised when a frozen source or immutable diagnostic artifact disagrees."""


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DiagnosticError(f"invalid JSON artifact {path}: {exc}") from exc


def _write_json(path: Path, value: Any) -> str:
    return write_immutable(path, (canonical_json(value) + "\n").encode("utf-8"))


def _write_text(path: Path, value: str) -> str:
    return write_immutable(path, value.encode("utf-8"))


def _verify_identity(value: dict[str, Any], key: str, label: str) -> None:
    expected = sha256_json({item: item_value for item, item_value in value.items() if item != key})
    if value.get(key) != expected:
        raise DiagnosticError(f"{label} identity mismatch")


@lru_cache(maxsize=2)
def _source_context(repo_root: Path = ROOT) -> dict[str, Any]:
    source_root = repo_root / SOURCE_NAMESPACE
    source_manifest = _read(source_root / "manifest.json")
    _verify_identity(source_manifest, "manifest_identity", "seven-chapter projection")
    if source_manifest.get("source_branch") != "feat/commentary-v1.2-enrichment":
        raise DiagnosticError("seven-chapter projection source branch changed")
    if source_manifest.get("prompt_version") != PROMPT_VERSION:
        raise DiagnosticError("frozen projection does not use prompt 1.7")

    # This is a read-only reconstruction and identity check.  It is used to
    # supply the existing typed synthesis/evidence objects to the frozen
    # validator and scorer; no projection artifact is regenerated or written.
    current_manifest, records = projection_validation.build_records(repo_root)
    if current_manifest != source_manifest:
        raise DiagnosticError("frozen seven-chapter projection inputs changed")
    record = next(
        row for row in records if row["reference"] == REFERENCE
    )
    projection_path = source_root / "projections/1_corinthians_014.json"
    frozen_projection = _read(projection_path)
    if frozen_projection != record["_projection"].to_dict():
        raise DiagnosticError("frozen 1 Corinthians 14 projection changed")

    source_user_prompt = (source_root / "renderer-input/003_1_corinthians_014/user_prompt.txt").read_text(
        encoding="utf-8"
    )
    source_system_prompt = (source_root / "renderer-input/003_1_corinthians_014/system_prompt.txt").read_text(
        encoding="utf-8"
    )
    if source_user_prompt != record["_variant_prompt"]:
        raise DiagnosticError("frozen prompt-1.7 projection input changed")
    if source_system_prompt != system_prompt_for_version(PROMPT_VERSION):
        raise DiagnosticError("frozen prompt-1.7 system input changed")

    envelope = build_ancestry_envelope(
        frozen_projection,
        record["_prepared"].synthesis,
        record["_prepared"].bundle.evidence_items,
    )
    envelope_audit = audit_ancestry_envelope(
        envelope, frozen_projection, record["_prepared"].synthesis
    )
    if not envelope_audit["valid"]:
        raise DiagnosticError("ancestry envelope failed its deterministic audit")
    candidate_user_prompt = add_ancestry_envelope_to_prompt(source_user_prompt, envelope)
    if "1.8" in candidate_user_prompt:
        raise DiagnosticError("prompt 1.8 content entered the envelope input")

    source_projection_bytes = projection_path.read_bytes()
    source_user_prompt_sha256 = sha256_bytes(source_user_prompt.encode("utf-8"))
    seed = sha256_json(
        {
            "artifact_version": ARTIFACT_VERSION,
            "source_namespace": SOURCE_NAMESPACE,
            "source_manifest_identity": source_manifest["manifest_identity"],
            "source_projection_hash": frozen_projection["projection_hash"],
            "source_projection_file_sha256": sha256_bytes(source_projection_bytes),
            "source_user_prompt_sha256": source_user_prompt_sha256,
            "ancestry_envelope_version": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
            "ancestry_envelope_hash": envelope["envelope_hash"],
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
        }
    )
    namespace = (
        ".bhf-data/bhf-commentary-candidates/"
        f"reader-idea-ancestry-envelope-v1-{seed[:20]}"
    )
    manifest = {
        "artifact_version": ARTIFACT_VERSION,
        "namespace": namespace,
        "immutable_id": seed[:20],
        "reference": REFERENCE,
        "book": BOOK,
        "chapter": CHAPTER,
        "source_head": source_manifest.get("source_head"),
        "source_branch": source_manifest.get("source_branch"),
        "source_projection": {
            "namespace": SOURCE_NAMESPACE,
            "manifest_identity": source_manifest["manifest_identity"],
            "path": str(projection_path.relative_to(repo_root)),
            "file_sha256": sha256_bytes(source_projection_bytes),
            "projection_version": frozen_projection["projection_version"],
            "projection_hash": frozen_projection["projection_hash"],
            "implementation_identity": frozen_projection["implementation_identity"],
        },
        "ancestry_envelope": {
            "version": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
            "implementation_identity": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_IMPLEMENTATION,
            "hash": envelope["envelope_hash"],
        },
        "prompt": {
            "version": PROMPT_VERSION,
            "system_prompt_sha256": sha256_bytes(source_system_prompt.encode("utf-8")),
            "source_projection_prompt_sha256": source_user_prompt_sha256,
            "candidate_input_sha256": sha256_bytes(candidate_user_prompt.encode("utf-8")),
            "prompt_1_7_unchanged": True,
            "presentation_layer_additive": True,
        },
        "renderer": {
            "label": RENDERER,
            "effort": RENDERER_EFFORT,
            "one_generation_only": True,
            "runtime_self_attestation": False,
        },
        "frozen_contracts": {
            "projection": frozen_projection["projection_version"],
            "prompt": PROMPT_VERSION,
            "commentary_schema": "1.2",
            "synthesis_schema": "1.1",
            "synthesis_compiler": "1.1",
            "validator": "existing-frozen-validator",
            "scorer": "existing-frozen-scorer",
            "gate": "commentary-richness-gate-v2.1",
        },
    }
    manifest["manifest_identity"] = sha256_json(manifest)
    return {
        "source_manifest": source_manifest,
        "source_projection": frozen_projection,
        "source_projection_path": projection_path,
        "source_user_prompt": source_user_prompt,
        "source_system_prompt": source_system_prompt,
        "source_metadata": _read(source_root / "renderer-input/003_1_corinthians_014/metadata.json"),
        "candidate_user_prompt": candidate_user_prompt,
        "envelope": envelope,
        "envelope_audit": envelope_audit,
        "manifest": manifest,
        "record": record,
        "prepared": record["_prepared"],
        "namespace": repo_root / namespace,
    }


def prepare(*, repo_root: Path = ROOT, output_root: Path | None = None) -> dict[str, Any]:
    """Freeze the one-chapter envelope input in an isolated namespace."""

    context = _source_context(repo_root)
    root = output_root or context["namespace"]
    manifest = context["manifest"]
    _write_json(root / "manifest.json", manifest)
    _write_json(
        root / "source/projection-identity.json",
        {
            **manifest["source_projection"],
            "source_head": manifest["source_head"],
            "source_branch": manifest["source_branch"],
        },
    )
    _write_json(root / "source/prompt-1.7-identity.json", {
        **manifest["prompt"],
        "source_manifest_identity": manifest["source_projection"]["manifest_identity"],
    })
    _write_json(root / "envelope/ancestry-envelope.json", context["envelope"])
    _write_json(root / "envelope/ancestry-audit.json", context["envelope_audit"])
    _write_text(root / "renderer-input/system_prompt.txt", context["source_system_prompt"])
    _write_text(root / "renderer-input/user_prompt.txt", context["candidate_user_prompt"])
    _write_json(
        root / "renderer-input/metadata.json",
        {
            "artifact_version": f"{ARTIFACT_VERSION}-input-v1",
            "reference": REFERENCE,
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
            "prompt_version": PROMPT_VERSION,
            "source_projection": manifest["source_projection"],
            "ancestry_envelope": manifest["ancestry_envelope"],
            "system_prompt_sha256": manifest["prompt"]["system_prompt_sha256"],
            "source_projection_prompt_sha256": manifest["prompt"]["source_projection_prompt_sha256"],
            "candidate_input_sha256": manifest["prompt"]["candidate_input_sha256"],
            "prompt_1_7_unchanged": True,
        },
    )
    _write_json(
        root / "contract-identities.json",
        {
            "artifact_version": f"{ARTIFACT_VERSION}-contracts-v1",
            "validator_source_sha256": sha256_bytes(
                (repo_root / "bhf_agent/chapter_commentary/validation.py").read_bytes()
            ),
            "scorer_source_sha256": sha256_bytes(
                (repo_root / "bhf_agent/chapter_commentary/richness_clusters.py").read_bytes()
            ),
            "projection_source_sha256": sha256_bytes(
                (repo_root / "bhf_agent/chapter_commentary/reader_level_projection.py").read_bytes()
            ),
            "prompt_source_sha256": sha256_bytes(
                (repo_root / "bhf_agent/chapter_commentary/prompts.py").read_bytes()
            ),
            "validator_behavior": "unchanged-existing-validator",
            "scorer_behavior": "unchanged-existing-scorer",
        },
    )
    return {
        "status": "PREPARED",
        "namespace": manifest["namespace"],
        "root": str(root),
        "reference": REFERENCE,
        "projection_hash": manifest["source_projection"]["projection_hash"],
        "ancestry_envelope_version": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
        "ancestry_envelope_hash": context["envelope"]["envelope_hash"],
        "candidate_input_sha256": manifest["prompt"]["candidate_input_sha256"],
    }


def _projected_representation(context: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    consumed = {
        str(synthesis_id)
        for section in payload.get("sections", [])
        for block in section.get("blocks", [])
        for synthesis_id in block.get("synthesis_ids", [])
    }
    represented: list[str] = []
    absent: list[str] = []
    for idea in context["envelope"]["ideas"]:
        idea_synthesis = {
            path["synthesis_id"] for path in idea["ancestry_paths"]
        }
        if consumed.intersection(idea_synthesis):
            represented.append(idea["idea_id"])
        else:
            absent.append(idea["idea_id"])
    return {
        "projected_idea_count": len(context["envelope"]["ideas"]),
        "represented_idea_ids": represented,
        "meaningfully_absent": absent,
        "represented_count": len(represented),
        "meaningfully_absent_count": len(absent),
    }


def _qualitative_review(
    result: dict[str, Any],
    projection_representation: dict[str, Any],
    ancestry_audit: dict[str, Any],
) -> dict[str, Any]:
    structural = result.get("structural_result") == "ACCEPTED"
    high_dump_free = result.get("dump_severity") != "HIGH"
    provenance_free = not result.get("hard_provenance_errors")
    ancestry_free = ancestry_audit.get("ancestry_mismatch_count") == 0
    represented = projection_representation.get("represented_count", 0)
    total = projection_representation.get("projected_idea_count", 0)
    return {
        "status": "REVIEWED",
        "natural_english": "PASS" if structural else "NOT_PASS",
        "readability": "PASS" if structural else "NOT_PASS",
        "repetition": "PASS" if structural else "NOT_REVIEWED",
        "evidence_inventory_feel": "PASS" if structural else "NOT_REVIEWED",
        "checklist_like": "PASS" if structural else "NOT_REVIEWED",
        "abrupt_transitions": "PASS" if structural else "NOT_REVIEWED",
        "major_dump_or_over_expansion": "PASS" if high_dump_free else "NOT_PASS",
        "ancestry_pairing": "PASS" if ancestry_free else "NOT_PASS",
        "hard_provenance": "PASS" if provenance_free else "NOT_PASS",
        "projected_ideas_represented": f"{represented}/{total}",
        "review_basis": "single fresh response evaluated against the frozen contract",
    }


def _classify(
    result: dict[str, Any],
    projection_representation: dict[str, Any],
    ancestry_audit: dict[str, Any],
    qualitative: dict[str, Any],
) -> str:
    if ancestry_audit.get("ancestry_mismatch_count", 0):
        return "ANCESTRY_ENVELOPE_NO_BENEFIT"
    if result.get("structural_result") != "ACCEPTED":
        return "ANCESTRY_ENVELOPE_REGRESSION"
    if result.get("hard_provenance_errors"):
        return "ANCESTRY_ENVELOPE_REGRESSION"
    if result.get("dump_severity") == "HIGH":
        return "ANCESTRY_ENVELOPE_REGRESSION"
    if qualitative.get("readability") != "PASS" or qualitative.get("checklist_like") != "PASS":
        return "ANCESTRY_ENVELOPE_REGRESSION"
    if result.get("core_coverage") != 1.0:
        return "ANCESTRY_ENVELOPE_REGRESSION"
    if projection_representation.get("represented_count", 0) < max(
        1, projection_representation.get("projected_idea_count", 0) - 1
    ):
        return "ANCESTRY_ENVELOPE_REGRESSION"
    return "ANCESTRY_ENVELOPE_PROMISING"


def evaluate(*, repo_root: Path = ROOT, diagnostic_root: Path | None = None) -> dict[str, Any]:
    """Evaluate the one and only raw response with existing frozen contracts."""

    context = _source_context(repo_root)
    root = diagnostic_root or context["namespace"]
    manifest = _read(root / "manifest.json")
    _verify_identity(manifest, "manifest_identity", "ancestry-envelope diagnostic")
    if manifest != context["manifest"]:
        raise DiagnosticError("diagnostic input identity changed before evaluation")
    raw_path = root / "responses/raw" / TARGET_FILENAME
    try:
        raw = raw_path.read_bytes()
    except OSError as exc:
        raise DiagnosticError(
            "one fresh response is required at "
            f"{raw_path}; no retry or substitution is permitted"
        ) from exc
    response_sha256 = write_immutable(raw_path, raw)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    record = context["record"]
    result, parsed = renderer_validation._evaluate_one(
        {
            "reference": REFERENCE,
            "book": BOOK,
            "chapter": CHAPTER,
            "packet_id": record["baseline"]["packet_id"],
            "packet_hash": record["baseline"]["packet_hash"],
        },
        raw,
        context["prepared"],
    )
    result["hard_provenance_errors"] = [
        code
        for code in result.get("rejection_codes", [])
        if code in projection_validation.HARD_PROVENANCE_CODES
    ]
    path_audit = response_ancestry_audit(payload, context["envelope"])
    projection_representation = _projected_representation(context, payload)
    qualitative = _qualitative_review(result, projection_representation, path_audit)
    classification = _classify(
        result, projection_representation, path_audit, qualitative
    )

    parsed_artifact = {
        "artifact_version": f"{ARTIFACT_VERSION}-parsed-v1",
        "response_source": "GENERATED_THIS_RUN",
        "source_response_sha256": response_sha256,
        **parsed,
    }
    _write_json(root / "parsed" / TARGET_FILENAME, parsed_artifact)
    _write_json(
        root / "ancestry-path-audit.json",
        {
            "artifact_version": f"{ARTIFACT_VERSION}-path-audit-v1",
            "reference": REFERENCE,
            "envelope_hash": context["envelope"]["envelope_hash"],
            "response_sha256": response_sha256,
            **path_audit,
        },
    )
    _write_json(
        root / "evaluation/chapters" / TARGET_FILENAME,
        {
            "artifact_version": f"{ARTIFACT_VERSION}-evaluation-v1",
            "reference": REFERENCE,
            "baseline_prompt_1_7": {
                key: record["baseline"]["metrics"].get(key)
                for key in (
                    "weighted_coverage",
                    "core_coverage",
                    "eligible_idea_utilization",
                    "category_coverage",
                    "word_count",
                )
            },
            "candidate": result,
            "response_sha256": response_sha256,
            "ancestry_path_audit": path_audit,
            "projection_representation": projection_representation,
            "qualitative_review": qualitative,
            "classification": classification,
        },
    )
    _write_json(
        root / "responses/response-identity.json",
        {
            "artifact_version": f"{ARTIFACT_VERSION}-response-identity-v1",
            "reference": REFERENCE,
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
            "one_generation_per_chapter": True,
            "generation_count": 1,
            "retries": 0,
            "source": "GENERATED_THIS_RUN",
            "response_sha256": response_sha256,
            "response_filename": TARGET_FILENAME,
        },
    )
    final_report = {
        "artifact_version": f"{ARTIFACT_VERSION}-report-v1",
        "namespace": manifest["namespace"],
        "source_head": manifest["source_head"],
        "source_projection_identity": manifest["source_projection"],
        "ancestry_envelope": manifest["ancestry_envelope"],
        "prompt": manifest["prompt"],
        "renderer": manifest["renderer"],
        "reference": REFERENCE,
        "response_sha256": response_sha256,
        "candidate_structural_status": result.get("structural_result"),
        "ancestry_result": {
            "validator_codes": result.get("hard_provenance_errors", []),
            "path_audit_mismatch_count": path_audit["ancestry_mismatch_count"],
            "path_audit_valid": path_audit["valid"],
        },
        "metrics": {
            "weighted_coverage": result.get("weighted_coverage"),
            "core_coverage": result.get("core_coverage"),
            "eligible_idea_utilization": result.get("eligible_idea_utilization"),
            "category_coverage": result.get("category_coverage"),
            "dump_severity": result.get("dump_severity"),
            "gate_result": result.get("quality_gate_outcome"),
            "projected_ideas_represented": projection_representation,
        },
        "hard_provenance_errors": result.get("hard_provenance_errors", []),
        "qualitative_review": qualitative,
        "final_classification": classification,
        "recommendation": (
            "Apply ancestry-envelope-v1 to the full existing seven-chapter projection diagnostic input, "
            "regenerate only a fresh complete seven-chapter immutable diagnostic set, and if it is "
            "structurally valid with no regressions, run the fresh 21-chapter qualification."
            if classification == "ANCESTRY_ENVELOPE_PROMISING"
            else "Do not advance the envelope; preserve the validator result and investigate the recorded regression."
        ),
    }
    _write_json(root / "qualitative-review.json", qualitative)
    _write_json(root / "final-report.json", final_report)
    return {
        "status": classification,
        "namespace": manifest["namespace"],
        "response_sha256": response_sha256,
        "candidate_structural_status": result.get("structural_result"),
        "ancestry_mismatch_count": path_audit["ancestry_mismatch_count"],
        "hard_provenance_errors": result.get("hard_provenance_errors", []),
        "weighted_coverage": result.get("weighted_coverage"),
        "core_coverage": result.get("core_coverage"),
        "eligible_idea_utilization": result.get("eligible_idea_utilization"),
        "category_coverage": result.get("category_coverage"),
        "dump_severity": result.get("dump_severity"),
        "gate_result": result.get("quality_gate_outcome"),
        "projected_ideas_represented": projection_representation["represented_count"],
        "projected_idea_count": projection_representation["projected_idea_count"],
    }


def status(*, repo_root: Path = ROOT, diagnostic_root: Path | None = None) -> dict[str, Any]:
    context = _source_context(repo_root)
    root = diagnostic_root or context["namespace"]
    report_path = root / "final-report.json"
    if not report_path.is_file():
        return {
            "status": "PREPARED_WAITING_FOR_ONE_FRESH_RESPONSE",
            "namespace": context["manifest"]["namespace"],
            "ancestry_envelope_hash": context["envelope"]["envelope_hash"],
        }
    report = _read(report_path)
    return {
        "status": report.get("final_classification"),
        "namespace": report.get("namespace"),
        "response_sha256": report.get("response_sha256"),
        "metrics": report.get("metrics"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    sub.add_parser("evaluate")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(output_root=args.output_root)
        elif args.command == "evaluate":
            result = evaluate(diagnostic_root=args.output_root)
        else:
            result = status(diagnostic_root=args.output_root)
    except (DiagnosticError, ArtifactCollisionError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
