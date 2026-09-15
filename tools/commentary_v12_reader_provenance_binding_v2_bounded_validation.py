#!/usr/bin/env python3
"""Bounded validation of reader-provenance-binding-v2.

The diagnostic reuses the frozen five-case Prompt 1.8 source packet and
changes only the provenance binding plus its path-only renderer adapter.  It
must run Numbers 2 exactly once before the historical five-case regression is
authorized.  No source artifact or raw response from the failed Prompt 1.8
run is reused as a generated response.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.output_conformance import (
    COMMENTARY_OUTPUT_CONFORMANCE_IMPLEMENTATION,
    COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
    MAX_STRUCTURAL_ATTEMPTS,
    conform_renderer_output,
    parse_renderer_json,
    structural_retry_allowed,
)
from bhf_agent.chapter_commentary.prompts import build_user_prompt, system_prompt_for_version
from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    add_ancestry_envelope_to_prompt,
)
from bhf_agent.chapter_commentary.reader_level_projection import (
    add_projection_to_prompt,
    project_reader_level_ideas,
)
from bhf_agent.chapter_commentary.reader_provenance_binding import (
    READER_PROVENANCE_BINDING_VERSION,
    audit_provenance_binding,
    build_provenance_binding,
)
from bhf_agent.chapter_commentary.reader_provenance_binding_v2 import (
    READER_PROVENANCE_BINDING_V2_IMPLEMENTATION,
    READER_PROVENANCE_BINDING_V2_VERSION,
    ProvenanceBindingV2Error,
    add_provenance_binding_to_prompt_v2,
    audit_provenance_binding_v2,
    build_provenance_binding_v2,
    normalize_renderer_payload_v2,
    response_ancestry_audit_v2,
)
from framework.commentary.production.models import (
    ArtifactCollisionError,
    canonical_json,
    sha256_bytes,
    sha256_json,
    write_immutable,
)
from tools import commentary_v12_output_conformance as historical
from tools import commentary_v12_scale_pilot as source_pilot
from tools import commentary_v12_scale_pilot_provenance_binding as binding_pilot


ARTIFACT_VERSION = "commentary-v1.2-reader-provenance-binding-v2-bounded-validation-v1"
PROMPT_VERSION = "1.8"
SOURCE_PROMPT_VERSION = "1.7"
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
PROJECTION_VERSION = "reader-level-idea-projection-v1"
ANCESTRY_VERSION = "reader-level-idea-ancestry-envelope-v1"
CODEX = Path("/home/johnwalker/.local/bin/codex")
ORDERED_REFERENCES = ("Numbers 2", "2 Kings 4", "Psalms 103", "Numbers 1", "Psalms 19")
EXPECTED_NUMBERS_2_PACKET = "commentary-production-v1-packet:ce6d8a6bea996b1ed4da3670da4b6d823ff25856f3f173d5d30cb85cdb307fd7"
HARD_PROVENANCE_CODES = frozenset(source_pilot.HARD_PROVENANCE_CODES) | frozenset(
    {
        "MALFORMED_PROVENANCE_REFERENCE",
        "MISSING_PROVENANCE_REFERENCES",
        "DUPLICATE_PROVENANCE_REFERENCE",
        "UNKNOWN_PROVENANCE_PATH",
        "OUT_OF_CHAPTER_PROVENANCE_PATH",
        "PROVENANCE_PATH_IDENTITY_MISMATCH",
    }
)


class DiagnosticError(RuntimeError):
    """The bounded v2 diagnostic cannot proceed safely."""


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DiagnosticError(f"invalid JSON artifact {path}: {exc}") from exc


def _write_json(path: Path, value: Any) -> str:
    return write_immutable(path, (canonical_json(value) + "\n").encode("utf-8"))


def _write_text(path: Path, value: str) -> str:
    return write_immutable(path, value.encode("utf-8"))


def _verify_identity(value: dict[str, Any], key: str, label: str) -> None:
    if value.get(key) != sha256_json({k: v for k, v in value.items() if k != key}):
        raise DiagnosticError(f"{label} identity mismatch")


def _record(source_record: dict[str, Any], source_public: dict[str, Any]) -> dict[str, Any]:
    prepared = source_record["prepared"]
    projection = project_reader_level_ideas(
        prepared.synthesis,
        source_pilot._clusters(prepared),
        prepared.bundle.evidence_items,
    )
    if projection.to_dict() != source_record["projection"]:
        raise DiagnosticError(f"projection changed for {source_public['reference']}")
    envelope = source_record["envelope"]
    v1 = build_provenance_binding(envelope)
    v1_audit = audit_provenance_binding(v1, envelope)
    if not v1_audit["valid"] or v1["binding_hash"] != source_record["binding"]["binding_hash"]:
        raise DiagnosticError(f"frozen v1 binding changed for {source_public['reference']}")
    v1_hash = v1["binding_hash"]
    v2 = build_provenance_binding_v2(
        envelope, prepared.synthesis, prepared.bundle.evidence_items
    )
    v2_audit = audit_provenance_binding_v2(
        v2, envelope, prepared.synthesis, prepared.bundle.evidence_items
    )
    if not v2_audit["valid"]:
        raise DiagnosticError(f"v2 binding failed deterministic audit for {source_public['reference']}")
    chapter = bible.resolve_chapter(source_public["book"], int(source_public["chapter"]))
    original = build_user_prompt(
        source_public["reference"],
        source_public["book"],
        int(source_public["chapter"]),
        bible.passage_text(chapter["verses"]),
        prepared.synthesis,
        prepared.bundle,
        prepared.synthesis.evidence_availability,
        prompt_version=PROMPT_VERSION,
    )
    candidate = add_provenance_binding_to_prompt_v2(
        add_ancestry_envelope_to_prompt(
            add_projection_to_prompt(original, projection), envelope
        ),
        envelope,
        v2,
    )
    return {
        "row": source_public,
        "prepared": prepared,
        "projection": projection.to_dict(),
        "envelope": envelope,
        "v1_binding": v1,
        "v1_binding_audit": v1_audit,
        "binding": v2,
        "binding_audit": v2_audit,
        "source_system_prompt_sha256": source_public["system_prompt_sha256"],
        "source_candidate_input_sha256": source_public.get("candidate_input_sha256"),
        "system_prompt": system_prompt_for_version(PROMPT_VERSION),
        "candidate_prompt": candidate,
        "v1_binding_hash": v1_hash,
    }


def build_context(repo_root: Path = ROOT) -> dict[str, Any]:
    source = historical._source_context(repo_root)
    source_manifest = source["manifest"]
    source_records = {record["row"]["reference"]: record for record in source["records"]}
    rows_by_reference = {
        row["reference"]: row
        for row in source_manifest["chapters"]
        if row["reference"] in ORDERED_REFERENCES
    }
    if set(rows_by_reference) != set(ORDERED_REFERENCES):
        raise DiagnosticError("source structural-failure set is not exactly five chapters")
    records: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for ordinal, reference in enumerate(ORDERED_REFERENCES, 1):
        public = rows_by_reference[reference]
        record = _record(source_records[reference], public)
        row = {
            "ordinal": ordinal,
            "reference": reference,
            "book": public["book"],
            "chapter": public["chapter"],
            "slug": public["slug"],
            "source_batch": public["batch"],
            "source_ordinal": public["ordinal"],
            "source_packet_id": public["source_packet_id"],
            "source_packet_hash": public["source_packet_hash"],
            "evidence_hash": public["evidence_hash"],
            "synthesis_hash": public["synthesis_hash"],
            "projection_hash": public["projection_hash"],
            "ancestry_envelope_hash": public["ancestry_envelope_hash"],
            "reader_provenance_binding_v1_hash": record["v1_binding_hash"],
            "reader_provenance_binding_v2_hash": record["binding"]["binding_hash"],
            "projected_idea_count": len(record["projection"]["ideas"]),
            "priority_path_count": len(record["binding"]["priority_paths"]),
            "fallback_renderable_path_count": len(record["binding"]["fallback_renderable_paths"]),
            "compiled_synthesis_unit_count": len(record["prepared"].synthesis.synthesis_units),
            "source_system_prompt_sha256": record["source_system_prompt_sha256"],
            "source_candidate_input_sha256": record["source_candidate_input_sha256"],
            "system_prompt_sha256": sha256_bytes(record["system_prompt"].encode()),
            "candidate_input_sha256": sha256_bytes(record["candidate_prompt"].encode()),
            "response_filename": f"{ordinal:03d}_{public['slug']}.json",
        }
        rows.append(row)
        records[reference] = record
    numbers = records["Numbers 2"]
    if rows[0]["source_packet_id"] != EXPECTED_NUMBERS_2_PACKET:
        raise DiagnosticError("Numbers 2 source packet identity is not the requested packet")
    base = {
        "artifact_version": f"{ARTIFACT_VERSION}-manifest",
        "source_namespace": historical.SOURCE_NAMESPACE,
        "source_manifest_identity": source_manifest["manifest_identity"],
        "source_structural_failure_references": list(ORDERED_REFERENCES),
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "source_prompt_version": SOURCE_PROMPT_VERSION,
        "projection_version": PROJECTION_VERSION,
        "ancestry_envelope_version": ANCESTRY_VERSION,
        "provenance_binding_v1_version": READER_PROVENANCE_BINDING_VERSION,
        "provenance_binding_v2_version": READER_PROVENANCE_BINDING_V2_VERSION,
        "provenance_binding_v2_implementation": READER_PROVENANCE_BINDING_V2_IMPLEMENTATION,
        "output_conformance_version": COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
        "output_conformance_implementation": COMMENTARY_OUTPUT_CONFORMANCE_IMPLEMENTATION,
        "max_structural_attempts": MAX_STRUCTURAL_ATTEMPTS,
        "numbers_2_single_initial_generation": True,
        "five_case_regression_authorized_only_after_numbers_2_success": True,
        "validator_unchanged": True,
        "scorer_unchanged": True,
        "gate_unchanged": True,
        "transport_unchanged": True,
        "projection_unchanged": True,
        "compiled_synthesis_unchanged": True,
        "evidence_unchanged": True,
        "prompt_1_8_unchanged": True,
        "v1_binding_frozen": True,
        "rows": rows,
        "numbers_2_architecture": {
            "projected_idea_count": len(numbers["projection"]["ideas"]),
            "priority_path_count": len(numbers["binding"]["priority_paths"]),
            "compiled_synthesis_unit_count": len(numbers["prepared"].synthesis.synthesis_units),
            "fallback_renderable_path_count": len(numbers["binding"]["fallback_renderable_paths"]),
            "fallback_path_mapping": [
                {
                    "path_id": path["path_id"],
                    "synthesis_id": path["synthesis_id"],
                    "evidence_ids": path["evidence_ids"],
                    "confidence": path["path"]["synthesis_confidence"],
                    "interpretation_level": path["path"]["interpretation_level"],
                    "disputed": path["path"]["disputed"],
                }
                for path in numbers["binding"]["fallback_renderable_paths"]
            ],
        },
    }
    seed = sha256_json(base)
    manifest = {
        **base,
        "namespace": f".bhf-data/bhf-commentary-candidates/{ARTIFACT_VERSION}-{seed[:20]}",
        "immutable_id": seed[:20],
    }
    manifest["manifest_identity"] = sha256_json(manifest)
    return {"manifest": manifest, "records": records, "root": repo_root / manifest["namespace"]}


def prepare(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    _write_json(root / "manifest.json", manifest)
    _write_json(root / "contract-identities.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-contracts",
        "prompt_1_8_system_sha256": manifest["rows"][0]["system_prompt_sha256"],
        "prompt_1_8_user_input_sha256": manifest["rows"][0]["candidate_input_sha256"],
        "prompt_1_8_unchanged": True,
        "projection": PROJECTION_VERSION,
        "ancestry_envelope": ANCESTRY_VERSION,
        "provenance_binding_v1": READER_PROVENANCE_BINDING_VERSION,
        "provenance_binding_v2": READER_PROVENANCE_BINDING_V2_VERSION,
        "output_conformance": COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
        "validator": "existing-validator-unchanged",
        "scorer": "existing-scorer-unchanged",
        "gate": "existing-gate-unchanged",
    })
    for row in manifest["rows"]:
        record = context["records"][row["reference"]]
        stem = f"{row['ordinal']:03d}_{row['slug']}"
        _write_json(root / "projections" / f"{row['slug']}.json", record["projection"])
        _write_json(root / "ancestry-envelopes" / f"{row['slug']}.json", record["envelope"])
        _write_json(root / "provenance-bindings-v1" / f"{row['slug']}.json", record["v1_binding"])
        _write_json(root / "provenance-bindings-v2" / f"{row['slug']}.json", record["binding"])
        _write_json(root / "provenance-binding-audits-v1" / f"{row['slug']}.json", record["v1_binding_audit"])
        _write_json(root / "provenance-binding-audits-v2" / f"{row['slug']}.json", record["binding_audit"])
        _write_json(root / "priority-paths" / f"{row['slug']}.json", record["binding"]["priority_paths"])
        _write_json(root / "fallback-renderable-paths" / f"{row['slug']}.json", record["binding"]["fallback_renderable_paths"])
        handoff = root / "renderer-input" / stem
        _write_text(handoff / "system_prompt.txt", record["system_prompt"])
        _write_text(handoff / "user_prompt.txt", record["candidate_prompt"])
        _write_json(handoff / "metadata.json", {
            "artifact_version": f"{ARTIFACT_VERSION}-renderer-input",
            **row,
            "source_renderer_input_reused": False,
            "source_packet_reused": True,
            "fresh_generation": row["reference"] == "Numbers 2",
            "generation_count": 0,
        })
        _write_json(root / "source-packet-identities" / f"{row['slug']}.json", {
            "reference": row["reference"],
            "source_packet_id": row["source_packet_id"],
            "source_packet_hash": row["source_packet_hash"],
            "evidence_hash": row["evidence_hash"],
            "synthesis_hash": row["synthesis_hash"],
            "projection_hash": row["projection_hash"],
            "ancestry_envelope_hash": row["ancestry_envelope_hash"],
            "reader_provenance_binding_v1_hash": row["reader_provenance_binding_v1_hash"],
            "reader_provenance_binding_v2_hash": row["reader_provenance_binding_v2_hash"],
        })
    return {"status": "PREPARED", "namespace": str(root.relative_to(repo_root)), "chapter_count": 5}


def _exchange(handoff: Path) -> str:
    return (
        "You are the selected GPT-5.6 Sol prose renderer at medium effort. Do not call tools, inspect files, browse, or add explanation. Treat the exact SYSTEM PROMPT and USER PROMPT below as the complete generation contract. Return the requested raw JSON object only, with no Markdown fence or preamble.\n\nSYSTEM PROMPT\n"
        + (handoff / "system_prompt.txt").read_text(encoding="utf-8")
        + "\n\nUSER PROMPT\n"
        + (handoff / "user_prompt.txt").read_text(encoding="utf-8")
    )


def _render_one(root: Path, row: dict[str, Any], attempt: int) -> tuple[bytes, int, str]:
    handoff = root / "renderer-input" / f"{row['ordinal']:03d}_{row['slug']}"
    with tempfile.TemporaryDirectory(prefix="bhf-v12-binding-v2-") as temp_dir:
        output = Path(temp_dir) / "response.txt"
        completed = subprocess.run(
            [str(CODEX), "exec", "--ephemeral", "--ignore-user-config", "-m", RENDERER,
             "-c", 'model_reasoning_effort="medium"', "-s", "read-only", "-C", temp_dir,
             "--skip-git-repo-check", "--output-last-message", str(output), "-"],
            input=_exchange(handoff), text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        if not output.is_file():
            raise DiagnosticError(f"renderer produced no output for {row['reference']}: {completed.stderr[-1000:]}")
        return output.read_bytes(), completed.returncode, completed.stderr


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (canonical_json(payload) + "\n").encode("utf-8")


def _structurally_accepted(result: dict[str, Any]) -> bool:
    return result.get("structural_result", result.get("structural_status")) == "ACCEPTED"


def _evaluate_one(
    record: dict[str, Any],
    public: dict[str, Any],
    raw: bytes,
    *,
    payload_override: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed_raw, parse_status, parse_errors = parse_renderer_json(raw)
    payload = payload_override if payload_override is not None else parsed_raw
    binding_error: ProvenanceBindingV2Error | None = None
    normalized: dict[str, Any] | None = None
    binding_metadata: dict[str, Any] = {"artifact_version": READER_PROVENANCE_BINDING_V2_VERSION, "blocks": []}
    if payload is not None:
        try:
            normalized, binding_metadata = normalize_renderer_payload_v2(payload, record["binding"])
        except ProvenanceBindingV2Error as exc:
            binding_error = exc
    if binding_error or normalized is None:
        error = binding_error or ProvenanceBindingV2Error("MALFORMED_PROVENANCE_REFERENCE", "; ".join(parse_errors))
        result: dict[str, Any] = {
            "reference": public["reference"], "structural_result": "REJECTED",
            "rejection_codes": [error.code], "weighted_coverage": None,
            "core_coverage": None, "eligible_idea_utilization": None,
            "category_coverage": None, "dump_severity": None,
            "quality_gate_outcome": None, "readability_result": None,
            "provenance_path_validity": False, "hard_provenance_errors": [error.code],
            "ancestry_mismatch_count": None,
            "validation_errors": [str(error)],
        }
        parsed = {
            "artifact_version": f"{ARTIFACT_VERSION}-parsed",
            "reference": public["reference"], "parse_status": parse_status,
            "validation_errors": list(parse_errors) + [str(error)],
            "raw_renderer_payload": parsed_raw, "normalized_renderer_payload": None,
            "provenance_binding": binding_metadata,
        }
    else:
        normalized_bytes = _canonical_bytes(normalized)
        result, validator_parsed = binding_pilot.validator._evaluate_one(
            {"reference": public["reference"], "book": public["book"], "chapter": public["chapter"], "packet_id": public["source_packet_id"], "packet_hash": public["source_packet_hash"]},
            normalized_bytes,
            record["prepared"],
        )
        ancestry = response_ancestry_audit_v2(normalized, record["binding"])
        parsed = {
            "artifact_version": f"{ARTIFACT_VERSION}-parsed",
            "reference": public["reference"], "parse_status": parse_status,
            "raw_renderer_payload": parsed_raw,
            "normalized_renderer_payload": normalized,
            "normalized_response_sha256": sha256_bytes(normalized_bytes),
            "provenance_binding": binding_metadata,
            "path_resolution": binding_metadata,
            "ancestry_validation": ancestry,
        }
        parsed["validator_result"] = validator_parsed
        result["provenance_path_validity"] = True
        result["ancestry_mismatch_count"] = ancestry["ancestry_mismatch_count"]
        result["ancestry_validation"] = ancestry
    hard = sorted(set(result.get("rejection_codes", [])) & HARD_PROVENANCE_CODES)
    represented = source_pilot._representation(record["envelope"], normalized)
    qualitative = source_pilot._qualitative(normalized, result)
    row = {
        "reference": public["reference"],
        "projected_idea_count": public["projected_idea_count"],
        "priority_path_count": public["priority_path_count"],
        "fallback_renderable_path_count": public["fallback_renderable_path_count"],
        "compiled_synthesis_unit_count": public["compiled_synthesis_unit_count"],
        "structural_validity": _structurally_accepted(result),
        "structural_status": result.get("structural_result"),
        "provenance_path_validity": result.get("provenance_path_validity"),
        "hard_provenance_errors": hard,
        "ancestry_mismatch_count": result.get("ancestry_mismatch_count"),
        "ancestry_validity": result.get("ancestry_mismatch_count") == 0,
        "weighted_coverage": result.get("weighted_coverage"),
        "core_coverage": result.get("core_coverage"),
        "eligible_idea_utilization": result.get("eligible_idea_utilization"),
        "category_coverage": result.get("category_coverage"),
        "dump_severity": result.get("dump_severity"),
        "gate_result": result.get("quality_gate_outcome"),
        "readability_result": qualitative["readability"],
        "word_count": len(source_pilot._prose(normalized).split()),
        "confidence_dispute_preservation": _preservation(record, normalized),
        "normalization_events": [],
        "rejection_codes": result.get("rejection_codes", []),
        "ancestry_validation": result.get("ancestry_validation", {}),
        "binding_metadata": binding_metadata,
        "response_sha256": sha256_bytes(raw),
    }
    row["high_dump"] = row["dump_severity"] == "HIGH"
    row["qualitative_review"] = qualitative
    row["final_chapter_classification"] = (
        "STRUCTURAL_FAILURE" if not row["structural_validity"] else
        "PROVENANCE_FAILURE" if hard or not row["ancestry_validity"] else
        "DUMP_FAILURE" if row["high_dump"] else "CLEAN_PASS"
    )
    parsed.update({"validation_result": result, "raw_response_sha256": sha256_bytes(raw)})
    return row, parsed


def _preservation(record: dict[str, Any], normalized: dict[str, Any] | None) -> dict[str, Any]:
    expected = {
        unit.id: {"confidence": unit.confidence, "interpretation_level": unit.interpretation_level}
        for unit in record["prepared"].synthesis.synthesis_units
    }
    observed = {}
    block_checks = []
    for section in (normalized or {}).get("sections", []):
        for block in section.get("blocks", []):
            cited = [expected[unit_id] for unit_id in block.get("synthesis_ids", []) if unit_id in expected]
            expected_confidence = min(
                (value["confidence"] for value in cited),
                key=lambda value: {"low": 0, "medium": 1, "high": 2}[value],
                default=None,
            )
            expected_interpretation = "disputed" if any(
                value["interpretation_level"] == "disputed" for value in cited
            ) else block.get("interpretation_level")
            block_checks.append({
                "block_id": block.get("id"),
                "expected_confidence": expected_confidence,
                "actual_confidence": block.get("confidence"),
                "expected_interpretation_level": expected_interpretation,
                "actual_interpretation_level": block.get("interpretation_level"),
            })
            for unit_id in block.get("synthesis_ids", []):
                unit = expected.get(unit_id)
                if unit:
                    observed[unit_id] = unit
    return {
        "valid": all(value == expected.get(key) for key, value in observed.items())
        and all(
            check["actual_confidence"] == check["expected_confidence"]
            and check["actual_interpretation_level"] == check["expected_interpretation_level"]
            for check in block_checks
        ),
        "observed": observed,
        "blocks": block_checks,
        "disputed_units_remain_disputed": all(
            value["interpretation_level"] == "disputed"
            for key, value in observed.items()
            if expected[key]["interpretation_level"] == "disputed"
        ),
    }


def _assessment(record: dict[str, Any], public: dict[str, Any], raw: bytes) -> dict[str, Any]:
    payload, parse_status, parse_errors = parse_renderer_json(raw)
    conformance = conform_renderer_output(
        payload, expected_reference=public["reference"], expected_book=public["book"],
        expected_chapter=int(public["chapter"]), parse_status=parse_status,
        parse_errors=parse_errors,
    )
    if conformance.valid and conformance.payload is not None:
        row, parsed = _evaluate_one(record, public, raw, payload_override=conformance.payload)
        row["normalization_events"] = list(conformance.events)
        canonical_payload = record["binding"] and parsed.get("normalized_renderer_payload")
        canonical_hash = sha256_bytes(_canonical_bytes(canonical_payload)) if canonical_payload is not None else None
    else:
        row = {
            "reference": public["reference"], "projected_idea_count": public["projected_idea_count"],
            "priority_path_count": public["priority_path_count"], "fallback_renderable_path_count": public["fallback_renderable_path_count"],
            "compiled_synthesis_unit_count": public["compiled_synthesis_unit_count"],
            "structural_validity": False, "structural_status": "REJECTED",
            "provenance_path_validity": None, "hard_provenance_errors": [],
            "ancestry_mismatch_count": None, "ancestry_validity": None,
            "gate_result": None, "readability_result": None, "word_count": None,
            "dump_severity": None, "high_dump": False, "rejection_codes": list(conformance.codes),
            "confidence_dispute_preservation": {"valid": None}, "normalization_events": list(conformance.events),
        }
        parsed = {
            "artifact_version": f"{ARTIFACT_VERSION}-parsed", "reference": public["reference"],
            "parse_status": conformance.parse_status, "validation_errors": list(conformance.errors),
            "raw_renderer_payload": payload, "normalized_renderer_payload": None,
        }
        canonical_payload, canonical_hash = None, None
    return {
        "raw_response_sha256": sha256_bytes(raw), "parse_status": conformance.parse_status,
        "json_parsing_succeeded": payload is not None, "conformance_valid": conformance.valid,
        "conformance_errors": list(conformance.errors), "conformance_codes": list(conformance.codes),
        "normalization_events": list(conformance.events), "canonical_payload": canonical_payload,
        "canonical_response_sha256": canonical_hash, "validation_result": row,
        "parsed_result": parsed,
        "retry_eligible": structural_retry_allowed(attempt_ordinal=1, codes=row.get("rejection_codes", list(conformance.codes))),
    }


def _write_attempt(
    root: Path,
    row: dict[str, Any],
    raw: bytes,
    assessment: dict[str, Any],
    stderr: str,
    exit_code: int,
    attempt: int = 1,
) -> None:
    target = root / "attempts" / f"{row['ordinal']:03d}_{row['slug']}" / f"attempt-{attempt:03d}"
    write_immutable(target / "raw-response.json", raw)
    _write_text(target / "stderr.txt", stderr)
    _write_json(target / "process.json", {"exit_code": exit_code, "renderer": RENDERER, "effort": RENDERER_EFFORT})
    _write_json(target / "conformance.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-conformance", "reference": row["reference"],
        "attempt_ordinal": 1, "raw_response_sha256": assessment["raw_response_sha256"],
        "parse_status": assessment["parse_status"], "json_parsing_succeeded": assessment["json_parsing_succeeded"],
        "conformance_valid": assessment["conformance_valid"], "conformance_errors": assessment["conformance_errors"],
        "conformance_codes": assessment["conformance_codes"], "normalization_events": assessment["normalization_events"],
        "canonical_response_sha256": assessment["canonical_response_sha256"], "retry_eligible": assessment["retry_eligible"],
    })
    _write_json(target / "parsed.json", assessment["parsed_result"])
    _write_json(target / "validation.json", assessment["validation_result"])
    if assessment["canonical_payload"] is not None:
        _write_json(target / "normalized-response.json", assessment["canonical_payload"])


def run_numbers_2(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest, record = context["root"], context["manifest"], context["records"]["Numbers 2"]
    if (root / "numbers-2-final-report.json").exists() or list((root / "attempts").glob("001_numbers_002/attempt-*")):
        raise DiagnosticError("Numbers 2 initial generation has already been attempted")
    row = next(item for item in manifest["rows"] if item["reference"] == "Numbers 2")
    raw, exit_code, stderr = _render_one(root, row, 1)
    assessment = _assessment(record, row, raw)
    _write_attempt(root, row, raw, assessment, stderr, exit_code)
    result = assessment["validation_result"]
    success = bool(
        result.get("structural_validity")
        and result.get("provenance_path_validity") is True
        and result.get("ancestry_validity") is True
        and not result.get("hard_provenance_errors")
        and not result.get("high_dump")
        and result.get("readability_result") == "PASS"
    )
    history = {
        "artifact_version": f"{ARTIFACT_VERSION}-attempt-history", "reference": "Numbers 2",
        "attempts": [{"attempt_ordinal": 1, "raw_response_sha256": assessment["raw_response_sha256"], "normalization_events": assessment["normalization_events"], "retry_eligible": assessment["retry_eligible"], "final_accepted": result.get("structural_validity")}],
        "final_attempt_ordinal": 1, "fresh_initial_generation_count": 1, "structural_retry_count": 0,
    }
    _write_json(root / "attempt-history" / "001_numbers_002.json", history)
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-numbers-2-report", "namespace": manifest["namespace"],
        "prompt_version": PROMPT_VERSION, "renderer": RENDERER, "effort": RENDERER_EFFORT,
        "source_packet_id": row["source_packet_id"], "source_packet_hash": row["source_packet_hash"],
        "fresh_generation_count": 1, "reused_failed_raw_response": False, "manual_editing": False,
        "deterministic_prose_creation": False, "success": success, "row": result,
        "stop_if_unsuccessful": True,
    }
    _write_json(root / "numbers-2-final-report.json", report)
    return report


def run_regression(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    numbers = _read(root / "numbers-2-final-report.json")
    if numbers.get("success") is not True:
        raise DiagnosticError("five-case regression is not authorized because Numbers 2 did not succeed")
    report_path = root / "five-case-regression-final-report.json"
    if report_path.exists():
        raise DiagnosticError("five-case regression has already been run")
    rows_by_reference = {row["reference"]: row for row in manifest["rows"]}
    final_rows: list[dict[str, Any]] = []
    histories: list[dict[str, Any]] = []
    retry_count = 0
    normalization_count = 0
    for reference in ORDERED_REFERENCES:
        row = rows_by_reference[reference]
        if reference == "Numbers 2":
            final = dict(numbers["row"])
            history = {
                "reference": reference,
                "attempts": [{
                    "attempt_ordinal": 1,
                    "raw_response_sha256": final["response_sha256"],
                    "normalization_events": final.get("normalization_events", []),
                    "retry_eligible": False,
                    "final_accepted": final["final_structural_validity"] if "final_structural_validity" in final else final["structural_validity"],
                }],
                "final_attempt_ordinal": 1,
                "structural_retry_count": 0,
                "reused_numbers_2_initial_attempt": True,
            }
        else:
            record = context["records"][reference]
            assessments: list[dict[str, Any]] = []
            for attempt in range(1, MAX_STRUCTURAL_ATTEMPTS + 1):
                raw, exit_code, stderr = _render_one(root, row, attempt)
                assessment = _assessment(record, row, raw)
                _write_attempt(root, row, raw, assessment, stderr, exit_code, attempt)
                assessments.append(assessment)
                normalization_count += len(assessment["normalization_events"])
                if assessment["validation_result"].get("structural_validity"):
                    break
                if attempt == MAX_STRUCTURAL_ATTEMPTS or not assessment["retry_eligible"]:
                    break
                retry_count += 1
            final = dict(assessments[-1]["validation_result"])
            final.update({
                "attempt_ordinal": len(assessments),
                "raw_response_sha256": assessments[-1]["raw_response_sha256"],
                "canonical_response_sha256": assessments[-1]["canonical_response_sha256"],
                "normalization_events": assessments[-1]["normalization_events"],
                "final_structural_validity": assessments[-1]["validation_result"].get("structural_validity"),
                "provenance_validity": assessments[-1]["validation_result"].get("provenance_path_validity"),
                "ancestry_validity": assessments[-1]["validation_result"].get("ancestry_validity"),
                "high_dump": assessments[-1]["validation_result"].get("high_dump"),
            })
            history = {
                "reference": reference,
                "attempts": [{
                    "attempt_ordinal": index,
                    "raw_response_sha256": item["raw_response_sha256"],
                    "normalization_events": item["normalization_events"],
                    "retry_eligible": item["retry_eligible"],
                    "final_accepted": item["validation_result"].get("structural_validity"),
                } for index, item in enumerate(assessments, 1)],
                "final_attempt_ordinal": len(assessments),
                "structural_retry_count": len(assessments) - 1,
                "reused_numbers_2_initial_attempt": False,
            }
        final.setdefault("final_structural_validity", final.get("structural_validity"))
        final.setdefault("provenance_validity", final.get("provenance_path_validity"))
        final.setdefault("ancestry_validity", final.get("ancestry_mismatch_count") == 0)
        final.setdefault("high_dump", final.get("dump_severity") == "HIGH")
        final["first_attempt_structural_validity"] = history["attempts"][0]["final_accepted"]
        final["structural_retry_count"] = history["structural_retry_count"]
        final["retry_result"] = (
            history["attempts"][-1]["final_accepted"] if len(history["attempts"]) > 1 else None
        )
        _write_json(root / "attempt-history" / f"{row['ordinal']:03d}_{row['slug']}-regression.json", history)
        _write_json(root / "final" / "regression-validation" / f"{row['ordinal']:03d}_{row['slug']}.json", final)
        final_rows.append(final)
        histories.append(history)
        print(f"{reference}: attempts={history['final_attempt_ordinal']} structural={final['final_structural_validity']}", flush=True)
    criteria = {
        "final_structural_5_of_5": all(row["final_structural_validity"] for row in final_rows),
        "provenance_5_of_5": all(row.get("provenance_validity") is True for row in final_rows),
        "ancestry_5_of_5": all(row.get("ancestry_validity") is True for row in final_rows),
        "hard_provenance_errors_zero": all(not row.get("hard_provenance_errors") for row in final_rows),
        "evidence_leakage_zero": all(row.get("ancestry_mismatch_count") == 0 for row in final_rows),
        "high_dumps_zero": all(not row.get("high_dump") for row in final_rows),
        "validator_weakening": False,
        "fabricated_prose": False,
        "manual_editing": False,
    }
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-five-case-regression",
        "namespace": manifest["namespace"],
        "authorization": "Numbers 2 fresh generation satisfied bounded success criteria",
        "references": list(ORDERED_REFERENCES),
        "renderer": RENDERER,
        "effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "counts": {
            "chapters": 5,
            "first_attempt_structural_validity": sum(bool(row["first_attempt_structural_validity"]) for row in final_rows),
            "normalization_event_count": normalization_count + sum(len(row.get("normalization_events", [])) for row in final_rows if row["reference"] == "Numbers 2"),
            "structural_retry_count": sum(row["structural_retry_count"] for row in final_rows),
            "retry_success_count": sum(bool(row["retry_result"]) for row in final_rows),
            "final_structural_validity": sum(bool(row["final_structural_validity"]) for row in final_rows),
            "provenance_validity": sum(row.get("provenance_validity") is True for row in final_rows),
            "ancestry_validity": sum(row.get("ancestry_validity") is True for row in final_rows),
            "high_dump_count": sum(bool(row.get("high_dump")) for row in final_rows),
        },
        "criteria": criteria,
        "chapters": final_rows,
        "attempt_histories": histories,
        "status": "PASS" if all(criteria.values()) else "FAIL",
    }
    _write_json(report_path, report)
    return report


def checksums(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root = context["root"]
    target = root / ("checksums-post-regression.json" if (root / "checksums.json").exists() else "checksums.json")
    files = sorted(path for path in root.rglob("*") if path.is_file() and path != target)
    value = {"artifact_version": f"{ARTIFACT_VERSION}-checksums", "files": {str(path.relative_to(root)): sha256_bytes(path.read_bytes()) for path in files}}
    _write_json(target, value)
    return {"status": "CHECKSUMMED", "namespace": str(root.relative_to(repo_root)), "file_count": len(files)}


def finalize(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    numbers_path = root / "numbers-2-final-report.json"
    numbers = _read(numbers_path) if numbers_path.is_file() else None
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-final-report", "namespace": manifest["namespace"],
        "prompt_1_8_changed": False, "source_prompt_1_7_preserved": True,
        "source_contracts": {
            "renderer": RENDERER, "effort": RENDERER_EFFORT, "prompt": PROMPT_VERSION,
            "projection": PROJECTION_VERSION, "ancestry_envelope": ANCESTRY_VERSION,
            "provenance_binding_v1": READER_PROVENANCE_BINDING_VERSION,
            "provenance_binding_v2": READER_PROVENANCE_BINDING_V2_VERSION,
            "output_conformance": COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
            "source_packet_id": EXPECTED_NUMBERS_2_PACKET,
        },
        "numbers_2": numbers,
        "five_case_regression": None,
        "five_case_regression_authorized": bool(numbers and numbers.get("success") is True),
        "five_case_regression_run": False,
        "production_behavior_changes": True,
        "validator_weakening": False, "manual_editing": False,
        "deterministic_prose_creation": False, "75_chapter_pilot_started": False,
        "stop_reason": "Numbers 2 failed" if not numbers or numbers.get("success") is not True else "regression not run in this turn",
    }
    target = root / ("final-report-post-regression.json" if (root / "final-report.json").exists() else "final-report.json")
    if (root / "five-case-regression-final-report.json").is_file():
        regression = _read(root / "five-case-regression-final-report.json")
        report["five_case_regression"] = regression
        report["five_case_regression_run"] = True
        report["stop_reason"] = "five-case regression completed with bounded result: " + regression.get("status", "UNKNOWN")
    report["authoritative_report"] = str(target.relative_to(repo_root))
    _write_json(target, report)
    return {"status": "FINALIZED", "namespace": str(root.relative_to(repo_root)), "report": str(target.relative_to(repo_root)), "numbers_2_success": bool(numbers and numbers.get("success") is True)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run-numbers-2", "run-regression", "checksums", "finalize", "status"))
    args = parser.parse_args(argv)
    try:
        context = build_context()
        root = context["root"]
        if args.command == "prepare":
            result = prepare()
        elif args.command == "run-numbers-2":
            result = run_numbers_2()
        elif args.command == "run-regression":
            result = run_regression()
        elif args.command == "checksums":
            result = checksums()
        elif args.command == "finalize":
            result = finalize()
        else:
            result = {"namespace": str(root.relative_to(ROOT)), "prepared": (root / "manifest.json").is_file(), "numbers_2_report": (root / "numbers-2-final-report.json").is_file(), "checksummed": (root / "checksums.json").is_file()}
    except (DiagnosticError, ArtifactCollisionError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
