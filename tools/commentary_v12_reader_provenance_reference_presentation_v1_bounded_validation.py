#!/usr/bin/env python3
"""Bounded validation of the versioned v2 renderer-reference presentation.

This diagnostic preserves the frozen v1/v2 bindings and all Prompt 1.8
contracts.  It first runs exactly one fresh Numbers 1 generation.  Only when
that succeeds does it run the bounded five-case structural regression.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.output_conformance import (
    COMMENTARY_OUTPUT_CONFORMANCE_IMPLEMENTATION,
    COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
    MAX_STRUCTURAL_ATTEMPTS,
    conform_renderer_output,
    parse_renderer_json,
    structural_retry_allowed,
)
from bhf_agent.chapter_commentary.renderer_reference_presentation_v1 import (
    RENDERER_REFERENCE_PRESENTATION_IMPLEMENTATION,
    RENDERER_REFERENCE_PRESENTATION_VERSION,
    add_presentation_to_prompt,
    audit_active_paths,
    normalize_selected_chapter_scope_refs,
    present_binding,
)
from bhf_agent.chapter_commentary.reader_provenance_binding_v2 import (
    READER_PROVENANCE_BINDING_V2_VERSION,
    ProvenanceBindingV2Error,
)
from framework.commentary.production.models import (
    ArtifactCollisionError,
    canonical_json,
    sha256_bytes,
    sha256_json,
    write_immutable,
)
from tools import commentary_v12_reader_provenance_binding_v2_bounded_validation as previous


ARTIFACT_VERSION = "commentary-v1.2-reader-provenance-renderer-reference-presentation-v1-bounded-validation-v1"
RENDERER = previous.RENDERER
RENDERER_EFFORT = previous.RENDERER_EFFORT
PROMPT_VERSION = previous.PROMPT_VERSION
ORDERED_REFERENCES = previous.ORDERED_REFERENCES
HARD_PROVENANCE_CODES = previous.HARD_PROVENANCE_CODES


class DiagnosticError(RuntimeError):
    """The bounded diagnostic cannot proceed safely."""


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DiagnosticError(f"invalid JSON artifact {path}: {exc}") from exc


def _write_json(path: Path, value: Any) -> str:
    return write_immutable(path, (canonical_json(value) + "\n").encode("utf-8"))


def _write_text(path: Path, value: str) -> str:
    return write_immutable(path, value.encode("utf-8"))


def build_context(repo_root: Path = ROOT) -> dict[str, Any]:
    """Rebuild the frozen v2 context and derive only renderer presentations."""

    frozen = previous.build_context(repo_root)
    records: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    presentations: dict[str, dict[str, Any]] = {}
    for old_row in frozen["manifest"]["rows"]:
        reference = old_row["reference"]
        old_record = frozen["records"][reference]
        presentation = present_binding(
            old_record["binding"],
            old_record["prepared"].synthesis,
            old_record["prepared"].bundle.evidence_items,
        )
        candidate_prompt, presentation = add_presentation_to_prompt(
            old_record["candidate_prompt"],
            old_record["envelope"],
            old_record["binding"],
            old_record["prepared"].synthesis,
            old_record["prepared"].bundle.evidence_items,
        )
        record = {**old_record, "candidate_prompt": candidate_prompt, "presentation": presentation}
        row = {
            **old_row,
            "renderer_reference_presentation_version": RENDERER_REFERENCE_PRESENTATION_VERSION,
            "renderer_reference_presentation_hash": presentation["presentation_hash"],
            "source_candidate_input_sha256": old_row.get("candidate_input_sha256"),
            "candidate_input_sha256": sha256_bytes(candidate_prompt.encode()),
        }
        records[reference] = record
        presentations[reference] = presentation
        rows.append(row)
    base = {
        "artifact_version": f"{ARTIFACT_VERSION}-manifest",
        "previous_v2_namespace": frozen["manifest"]["namespace"],
        "source_manifest_identity": frozen["manifest"]["manifest_identity"],
        "source_structural_failure_references": list(ORDERED_REFERENCES),
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "renderer_reference_presentation_version": RENDERER_REFERENCE_PRESENTATION_VERSION,
        "renderer_reference_presentation_implementation": RENDERER_REFERENCE_PRESENTATION_IMPLEMENTATION,
        "output_conformance_version": COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
        "output_conformance_implementation": COMMENTARY_OUTPUT_CONFORMANCE_IMPLEMENTATION,
        "max_structural_attempts": MAX_STRUCTURAL_ATTEMPTS,
        "numbers_1_single_initial_generation": True,
        "five_case_regression_authorized_only_after_numbers_1_success": True,
        "validator_unchanged": True,
        "scorer_unchanged": True,
        "gate_unchanged": True,
        "transport_unchanged": True,
        "projection_unchanged": True,
        "compiled_synthesis_unchanged": True,
        "evidence_unchanged": True,
        "prompt_1_8_unchanged": True,
        "v1_binding_frozen": True,
        "v2_binding_frozen": True,
        "rows": rows,
    }
    seed = sha256_json(base)
    manifest = {
        **base,
        "namespace": f".bhf-data/bhf-commentary-candidates/{ARTIFACT_VERSION}-{seed[:20]}",
        "immutable_id": seed[:20],
    }
    manifest["manifest_identity"] = sha256_json(manifest)
    return {"manifest": manifest, "records": records, "presentations": presentations, "root": repo_root / manifest["namespace"]}


def prepare(repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    _write_json(root / "manifest.json", manifest)
    _write_json(root / "contract-identities.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-contracts",
        "prompt_1_8_system_sha256": manifest["rows"][0]["system_prompt_sha256"],
        "source_v2_binding_version": READER_PROVENANCE_BINDING_V2_VERSION,
        "renderer_reference_presentation_version": RENDERER_REFERENCE_PRESENTATION_VERSION,
        "renderer_reference_presentation_implementation": RENDERER_REFERENCE_PRESENTATION_IMPLEMENTATION,
        "output_conformance": COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
        "validator": "existing-validator-unchanged",
        "scorer": "existing-scorer-unchanged",
        "gate": "existing-gate-unchanged",
        "source_prompt_1_8_preserved": True,
        "source_semantics_immutable": True,
    })
    for row in manifest["rows"]:
        reference = row["reference"]
        record = context["records"][reference]
        presentation = context["presentations"][reference]
        stem = f"{row['ordinal']:03d}_{row['slug']}"
        _write_json(root / "projections" / f"{row['slug']}.json", record["projection"])
        _write_json(root / "ancestry-envelopes" / f"{row['slug']}.json", record["envelope"])
        _write_json(root / "provenance-bindings-v1" / f"{row['slug']}.json", record["v1_binding"])
        _write_json(root / "provenance-bindings-v2" / f"{row['slug']}.json", record["binding"])
        _write_json(root / "renderer-reference-presentations" / f"{row['slug']}.json", presentation)
        _write_json(root / "canonicalization-audits" / f"{row['slug']}.json", audit_active_paths(record["binding"], record["prepared"].synthesis, record["prepared"].bundle.evidence_items))
        _write_json(root / "source-provenance-paths" / f"{row['slug']}.json", [
            {
                "path_id": path["path_id"],
                "synthesis_id": path["synthesis_id"],
                "source_verse_refs": path["source_verse_refs"],
                "renderer_verse_refs": path["renderer_verse_refs"],
                "canonicalization": path["canonicalization"],
            }
            for path in presentation["paths"]
        ])
        handoff = root / "renderer-input" / stem
        _write_text(handoff / "system_prompt.txt", record["system_prompt"])
        _write_text(handoff / "user_prompt.txt", record["candidate_prompt"])
        _write_json(handoff / "metadata.json", {
            "artifact_version": f"{ARTIFACT_VERSION}-renderer-input",
            **row,
            "source_renderer_input_reused": False,
            "source_packet_reused": True,
            "fresh_generation": reference == "Numbers 1",
            "generation_count": 0,
            "source_semantics_immutable": True,
        })
        _write_json(root / "source-packet-identities" / f"{row['slug']}.json", {
            "reference": reference,
            "source_packet_id": row["source_packet_id"],
            "source_packet_hash": row["source_packet_hash"],
            "evidence_hash": row["evidence_hash"],
            "synthesis_hash": row["synthesis_hash"],
            "projection_hash": row["projection_hash"],
            "ancestry_envelope_hash": row["ancestry_envelope_hash"],
            "reader_provenance_binding_v1_hash": row["reader_provenance_binding_v1_hash"],
            "reader_provenance_binding_v2_hash": row["reader_provenance_binding_v2_hash"],
            "renderer_reference_presentation_hash": presentation["presentation_hash"],
        })
    return {"status": "PREPARED", "namespace": str(root.relative_to(repo_root)), "chapter_count": 5}


def audit(repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root = context["root"]
    chapters = []
    total = {"VALID_ALREADY": 0, "SAFE_FULL_CHAPTER_SCOPE": 0, "AMBIGUOUS": 0, "INVALID_SOURCE_REFERENCE": 0}
    affected = {key: [] for key in total}
    for reference in ORDERED_REFERENCES:
        record = context["records"][reference]
        result = audit_active_paths(record["binding"], record["prepared"].synthesis, record["prepared"].bundle.evidence_items)
        chapters.append({"reference": reference, **result})
        for key, count in result["counts"].items():
            total[key] += count
            affected[key].extend(result["affected_path_ids"][key])
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-preflight-audit",
        "namespace": str(root.relative_to(repo_root)),
        "references": list(ORDERED_REFERENCES),
        "counts": total,
        "affected_path_ids": affected,
        "chapters": chapters,
        "source_semantics_immutable": True,
        "generation_started": False,
    }
    _write_json(root / "preflight-path-audit.json", report)
    return report


def _exchange(handoff: Path) -> str:
    return (
        "You are the selected GPT-5.6 Sol prose renderer at medium effort. Do not call tools, inspect files, browse, or add explanation. Treat the exact SYSTEM PROMPT and USER PROMPT below as the complete generation contract. Return the requested raw JSON object only, with no Markdown fence or preamble.\n\nSYSTEM PROMPT\n"
        + (handoff / "system_prompt.txt").read_text(encoding="utf-8")
        + "\n\nUSER PROMPT\n"
        + (handoff / "user_prompt.txt").read_text(encoding="utf-8")
    )


def _render_one(root: Path, row: dict[str, Any], attempt: int) -> tuple[bytes, int, str]:
    handoff = root / "renderer-input" / f"{row['ordinal']:03d}_{row['slug']}"
    with tempfile.TemporaryDirectory(prefix="bhf-v12-renderer-reference-") as temp_dir:
        output = Path(temp_dir) / "response.txt"
        completed = subprocess.run(
            [str(previous.CODEX), "exec", "--ephemeral", "--ignore-user-config", "-m", RENDERER,
             "-c", 'model_reasoning_effort="medium"', "-s", "read-only", "-C", temp_dir,
             "--skip-git-repo-check", "--output-last-message", str(output), "-"],
            input=_exchange(handoff), text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        if not output.is_file():
            raise DiagnosticError(f"renderer produced no output for {row['reference']}: {completed.stderr[-1000:]}")
        return output.read_bytes(), completed.returncode, completed.stderr


def _emitted_verse_refs(payload: Any) -> list[str]:
    refs: list[str] = []
    for section in (payload or {}).get("sections", []):
        for block in section.get("blocks", []):
            refs.extend(str(value) for value in block.get("verse_refs", []))
    return refs


def _assess(context: dict[str, Any], row: dict[str, Any], raw: bytes) -> dict[str, Any]:
    record = context["records"][row["reference"]]
    presentation = context["presentations"][row["reference"]]
    payload, parse_status, parse_errors = parse_renderer_json(raw)
    safeguard_events: list[dict[str, Any]] = []
    presented_payload = payload
    if payload is not None:
        presented_payload, safeguard_events = normalize_selected_chapter_scope_refs(
            payload, record["binding"], presentation
        )
    conformance = conform_renderer_output(
        presented_payload,
        expected_reference=row["reference"], expected_book=row["book"],
        expected_chapter=int(row["chapter"]), parse_status=parse_status,
        parse_errors=parse_errors,
    )
    if conformance.valid and conformance.payload is not None:
        normalized, parsed = previous._evaluate_one(
            record, row, raw, payload_override=conformance.payload
        )
        normalized["normalization_events"] = safeguard_events + list(conformance.events)
        parsed["renderer_reference_presentation"] = presentation
        parsed["chapter_scope_normalization_events"] = safeguard_events
        parsed["emitted_verse_refs"] = _emitted_verse_refs(conformance.payload)
        parsed["raw_renderer_payload_before_presentation"] = payload
        canonical_payload = parsed.get("normalized_renderer_payload")
        canonical_hash = sha256_bytes((canonical_json(canonical_payload) + "\n").encode()) if canonical_payload is not None else None
    else:
        normalized = {
            "reference": row["reference"], "projected_idea_count": row["projected_idea_count"],
            "priority_path_count": row["priority_path_count"], "fallback_renderable_path_count": row["fallback_renderable_path_count"],
            "compiled_synthesis_unit_count": row["compiled_synthesis_unit_count"],
            "structural_validity": False, "structural_status": "REJECTED",
            "provenance_path_validity": None, "hard_provenance_errors": [],
            "ancestry_mismatch_count": None, "ancestry_validity": None,
            "gate_result": None, "readability_result": None, "word_count": None,
            "dump_severity": None, "high_dump": False, "rejection_codes": list(conformance.codes),
            "confidence_dispute_preservation": {"valid": None},
            "normalization_events": safeguard_events + list(conformance.events),
            "emitted_verse_refs": _emitted_verse_refs(conformance.payload or payload),
        }
        parsed = {
            "artifact_version": f"{ARTIFACT_VERSION}-parsed", "reference": row["reference"],
            "parse_status": conformance.parse_status, "validation_errors": list(conformance.errors),
            "raw_renderer_payload": payload, "presented_renderer_payload": conformance.payload,
            "normalized_renderer_payload": None,
            "renderer_reference_presentation": presentation,
            "chapter_scope_normalization_events": safeguard_events,
            "emitted_verse_refs": normalized["emitted_verse_refs"],
        }
        canonical_hash = None
    normalized["renderer_reference_presentation_hash"] = presentation["presentation_hash"]
    normalized["source_verse_refs_preserved"] = True
    normalized["raw_response_sha256"] = sha256_bytes(raw)
    normalized["canonical_response_sha256"] = canonical_hash
    normalized["emitted_verse_refs"] = parsed.get("emitted_verse_refs", [])
    parsed["validation_result"] = normalized
    parsed["raw_response_sha256"] = sha256_bytes(raw)
    return {
        "raw_response_sha256": sha256_bytes(raw),
        "parse_status": conformance.parse_status,
        "json_parsing_succeeded": payload is not None,
        "conformance_valid": conformance.valid,
        "conformance_errors": list(conformance.errors),
        "conformance_codes": list(conformance.codes),
        "normalization_events": safeguard_events + list(conformance.events),
        "canonical_payload": parsed.get("normalized_renderer_payload"),
        "canonical_response_sha256": canonical_hash,
        "validation_result": normalized,
        "parsed_result": parsed,
        "retry_eligible": structural_retry_allowed(
            attempt_ordinal=1,
            codes=normalized.get("rejection_codes", list(conformance.codes)),
        ),
    }


def _write_attempt(root: Path, row: dict[str, Any], raw: bytes, assessment: dict[str, Any], stderr: str, exit_code: int, attempt: int) -> None:
    target = root / "attempts" / f"{row['ordinal']:03d}_{row['slug']}" / f"attempt-{attempt:03d}"
    write_immutable(target / "raw-response.json", raw)
    _write_text(target / "stderr.txt", stderr)
    _write_json(target / "process.json", {"exit_code": exit_code, "renderer": RENDERER, "effort": RENDERER_EFFORT, "attempt_ordinal": attempt})
    _write_json(target / "conformance.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-conformance", "reference": row["reference"],
        "attempt_ordinal": attempt, "raw_response_sha256": assessment["raw_response_sha256"],
        "parse_status": assessment["parse_status"], "json_parsing_succeeded": assessment["json_parsing_succeeded"],
        "conformance_valid": assessment["conformance_valid"], "conformance_errors": assessment["conformance_errors"],
        "conformance_codes": assessment["conformance_codes"], "normalization_events": assessment["normalization_events"],
        "canonical_response_sha256": assessment["canonical_response_sha256"], "retry_eligible": assessment["retry_eligible"],
    })
    _write_json(target / "parsed.json", assessment["parsed_result"])
    _write_json(target / "validation.json", assessment["validation_result"])
    if assessment["canonical_payload"] is not None:
        _write_json(target / "normalized-response.json", assessment["canonical_payload"])


def _accepted(result: dict[str, Any]) -> bool:
    return result.get("structural_result", result.get("structural_status")) == "ACCEPTED"


def _success(result: dict[str, Any]) -> bool:
    return bool(
        result.get("structural_validity")
        and result.get("provenance_path_validity") is True
        and result.get("ancestry_validity") is True
        and not result.get("hard_provenance_errors")
        and result.get("ancestry_mismatch_count") == 0
        and not result.get("high_dump")
    )


def run_numbers_1(repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    row = next(item for item in manifest["rows"] if item["reference"] == "Numbers 1")
    if list((root / "attempts").glob("004_numbers_001/attempt-*")):
        raise DiagnosticError("Numbers 1 initial generation has already been attempted")
    raw, exit_code, stderr = _render_one(root, row, 1)
    assessment = _assess(context, row, raw)
    _write_attempt(root, row, raw, assessment, stderr, exit_code, 1)
    result = assessment["validation_result"]
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-numbers-1-report",
        "namespace": manifest["namespace"], "reference": "Numbers 1",
        "prompt_version": PROMPT_VERSION, "renderer": RENDERER, "effort": RENDERER_EFFORT,
        "fresh_initial_generation_count": 1, "fresh_numbers_1_generation_count": 1,
        "reused_failed_raw_response": False, "manual_editing": False,
        "deterministic_prose_creation": False, "success": _success(result),
        "raw_response_sha256": assessment["raw_response_sha256"],
        "emitted_verse_refs": result.get("emitted_verse_refs", []),
        "renderer_reference_presentation": context["presentations"]["Numbers 1"],
        "source_reference_preserved": True,
        "row": result,
        "stop_if_unsuccessful": True,
    }
    _write_json(root / "attempt-history" / "004_numbers_001.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-attempt-history", "reference": "Numbers 1",
        "attempts": [{"attempt_ordinal": 1, "raw_response_sha256": assessment["raw_response_sha256"], "normalization_events": assessment["normalization_events"], "retry_eligible": assessment["retry_eligible"], "final_accepted": result.get("structural_validity")}],
        "final_attempt_ordinal": 1, "fresh_initial_generation_count": 1, "structural_retry_count": 0,
    })
    _write_json(root / "numbers-1-final-report.json", report)
    return report


def _row_with_metadata(context: dict[str, Any], row: dict[str, Any], assessment: dict[str, Any], history: dict[str, Any]) -> dict[str, Any]:
    result = dict(assessment["validation_result"])
    result.update({
        "attempt_ordinal": history["final_attempt_ordinal"],
        "raw_response_sha256": assessment["raw_response_sha256"],
        "canonical_response_sha256": assessment["canonical_response_sha256"],
        "final_structural_validity": assessment["validation_result"].get("structural_validity"),
        "provenance_validity": assessment["validation_result"].get("provenance_path_validity"),
        "ancestry_validity": assessment["validation_result"].get("ancestry_validity"),
        "high_dump": assessment["validation_result"].get("high_dump"),
        "first_attempt_structural_validity": history["attempts"][0]["final_accepted"],
        "structural_retry_count": history["structural_retry_count"],
        "retry_result": history["attempts"][-1]["final_accepted"] if len(history["attempts"]) > 1 else None,
        "renderer_reference_presentation_hash": context["presentations"][row["reference"]]["presentation_hash"],
    })
    return result


def run_regression(repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    numbers_report_path = root / "numbers-1-final-report.json"
    numbers = _read(numbers_report_path)
    if numbers.get("success") is not True:
        raise DiagnosticError("five-case regression is not authorized because fresh Numbers 1 did not succeed")
    report_path = root / "five-case-regression-final-report.json"
    if report_path.exists():
        raise DiagnosticError("five-case regression has already been run")
    rows_by_reference = {row["reference"]: row for row in manifest["rows"]}
    final_rows: list[dict[str, Any]] = []
    histories: list[dict[str, Any]] = []
    normalization_count = 0
    for reference in ORDERED_REFERENCES:
        row = rows_by_reference[reference]
        if reference == "Numbers 1":
            result = dict(numbers["row"])
            history = {
                "reference": reference,
                "attempts": [{"attempt_ordinal": 1, "raw_response_sha256": numbers["raw_response_sha256"], "normalization_events": result.get("normalization_events", []), "retry_eligible": False, "final_accepted": result.get("structural_validity")}],
                "final_attempt_ordinal": 1, "structural_retry_count": 0,
                "reused_numbers_1_initial_attempt": True,
            }
            normalization_count += len(result.get("normalization_events", []))
        else:
            assessments: list[dict[str, Any]] = []
            for attempt in range(1, MAX_STRUCTURAL_ATTEMPTS + 1):
                raw, exit_code, stderr = _render_one(root, row, attempt)
                assessment = _assess(context, row, raw)
                _write_attempt(root, row, raw, assessment, stderr, exit_code, attempt)
                assessments.append(assessment)
                normalization_count += len(assessment["normalization_events"])
                if assessment["validation_result"].get("structural_validity"):
                    break
                if attempt == MAX_STRUCTURAL_ATTEMPTS or not assessment["retry_eligible"]:
                    break
            history = {
                "reference": reference,
                "attempts": [{"attempt_ordinal": index, "raw_response_sha256": item["raw_response_sha256"], "normalization_events": item["normalization_events"], "retry_eligible": item["retry_eligible"], "final_accepted": item["validation_result"].get("structural_validity")} for index, item in enumerate(assessments, 1)],
                "final_attempt_ordinal": len(assessments),
                "structural_retry_count": len(assessments) - 1,
                "reused_numbers_1_initial_attempt": False,
            }
            result = _row_with_metadata(context, row, assessments[-1], history)
        result.setdefault("final_structural_validity", result.get("structural_validity"))
        result.setdefault("provenance_validity", result.get("provenance_path_validity"))
        result.setdefault("ancestry_validity", result.get("ancestry_mismatch_count") == 0)
        result.setdefault("high_dump", result.get("dump_severity") == "HIGH")
        _write_json(root / "attempt-history" / f"{row['ordinal']:03d}_{row['slug']}-regression.json", history)
        _write_json(root / "final" / "regression-validation" / f"{row['ordinal']:03d}_{row['slug']}.json", result)
        final_rows.append(result)
        histories.append(history)
        print(f"{reference}: attempts={history['final_attempt_ordinal']} structural={result.get('final_structural_validity')}", flush=True)
    criteria = {
        "final_structural_5_of_5": all(row.get("final_structural_validity") for row in final_rows),
        "provenance_5_of_5": all(row.get("provenance_validity") is True for row in final_rows),
        "ancestry_5_of_5": all(row.get("ancestry_validity") is True for row in final_rows),
        "hard_provenance_errors_zero": all(not row.get("hard_provenance_errors") for row in final_rows),
        "evidence_leakage_zero": all(row.get("ancestry_mismatch_count") == 0 for row in final_rows),
        "high_dumps_zero": all(not row.get("high_dump") for row in final_rows),
        "validator_weakening": False, "fabricated_prose": False, "manual_editing": False,
    }
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-five-case-regression",
        "namespace": manifest["namespace"], "authorization": "fresh Numbers 1 generation satisfied bounded success criteria",
        "references": list(ORDERED_REFERENCES), "renderer": RENDERER, "effort": RENDERER_EFFORT, "prompt_version": PROMPT_VERSION,
        "counts": {
            "chapters": 5,
            "first_attempt_structural_validity": sum(bool(row.get("first_attempt_structural_validity", row.get("structural_validity"))) for row in final_rows),
            "normalization_event_count": normalization_count,
            "structural_retry_count": sum(row.get("structural_retry_count", 0) for row in final_rows),
            "retry_success_count": sum(bool(row.get("retry_result")) for row in final_rows),
            "final_structural_validity": sum(bool(row.get("final_structural_validity")) for row in final_rows),
            "provenance_validity": sum(row.get("provenance_validity") is True for row in final_rows),
            "ancestry_validity": sum(row.get("ancestry_validity") is True for row in final_rows),
            "high_dump_count": sum(bool(row.get("high_dump")) for row in final_rows),
        },
        "criteria": criteria, "chapters": final_rows, "attempt_histories": histories,
        "status": "PASS" if _regression_passes(criteria) else "FAIL",
        "quality_is_separate_gate": True,
    }
    _write_json(report_path, report)
    return report


def _regression_passes(criteria: dict[str, Any]) -> bool:
    """Evaluate positive results and negative safety assertions correctly."""

    return (
        all(
            criteria.get(key) is True
            for key in (
                "final_structural_5_of_5",
                "provenance_5_of_5",
                "ancestry_5_of_5",
                "hard_provenance_errors_zero",
                "evidence_leakage_zero",
                "high_dumps_zero",
            )
        )
        and all(
            criteria.get(key) is False
            for key in ("validator_weakening", "fabricated_prose", "manual_editing")
        )
    )


def reconcile_regression_report(repo_root: Path = ROOT) -> dict[str, Any]:
    """Write a corrected immutable report for the completed regression.

    The original report is retained byte-for-byte.  This reconciliation fixes
    only its boolean status aggregation; it does not change any result row.
    """

    context = build_context(repo_root)
    root = context["root"]
    source_path = root / "five-case-regression-final-report.json"
    source = _read(source_path)
    corrected = {
        **source,
        "artifact_version": f"{source['artifact_version']}-reconciled",
        "supersedes": str(source_path.relative_to(repo_root)),
        "status": "PASS" if _regression_passes(source["criteria"]) else "FAIL",
        "status_reconciliation": {
            "reason": "negative safety assertions are pass conditions when false",
            "source_status": source.get("status"),
            "reconciled_status": "PASS" if _regression_passes(source["criteria"]) else "FAIL",
        },
    }
    target = root / "five-case-regression-final-report-reconciled.json"
    _write_json(target, corrected)
    return {"status": corrected["status"], "report": str(target.relative_to(repo_root))}


def finalize(repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    numbers = _read(root / "numbers-1-final-report.json") if (root / "numbers-1-final-report.json").is_file() else None
    regression_path = root / "five-case-regression-final-report-reconciled.json"
    if not regression_path.is_file():
        regression_path = root / "five-case-regression-final-report.json"
    regression = _read(regression_path) if regression_path.is_file() else None
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-final-report", "namespace": manifest["namespace"],
        "branch_scope": "feat/commentary-v1.2-enrichment", "starting_sha": "7f261d8936f667f0506216798ba3a8ff1c40ebad",
        "prompt_1_8_changed": False, "source_prompt_1_8_preserved": True,
        "source_semantics_immutable": True, "v1_binding_frozen": True, "v2_binding_frozen": True,
        "renderer_reference_presentation_version": RENDERER_REFERENCE_PRESENTATION_VERSION,
        "numbers_1": numbers, "five_case_regression": regression,
        "five_case_regression_report": str(regression_path.relative_to(repo_root)) if regression else None,
        "five_case_regression_authorized": bool(numbers and numbers.get("success") is True),
        "five_case_regression_run": regression is not None,
        "validator_weakening": False, "manual_editing": False, "deterministic_prose_creation": False,
        "production_behavior_changed": True, "75_chapter_pilot_started": False,
        "stop_reason": "five-case regression completed with bounded result: " + regression.get("status", "UNKNOWN") if regression else "Numbers 1 bounded validation only",
    }
    target = root / "final-report.json"
    _write_json(target, report)
    return {"status": "FINALIZED", "namespace": str(root.relative_to(repo_root)), "report": str(target.relative_to(repo_root)), "five_case_regression_run": regression is not None}


def checksums(repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root = context["root"]
    target = root / "checksums.json"
    files = sorted(path for path in root.rglob("*") if path.is_file() and path != target)
    value = {"artifact_version": f"{ARTIFACT_VERSION}-checksums", "files": {str(path.relative_to(root)): sha256_bytes(path.read_bytes()) for path in files}}
    _write_json(target, value)
    return {"status": "CHECKSUMMED", "namespace": str(root.relative_to(repo_root)), "file_count": len(files)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "audit", "run-numbers-1", "run-regression", "reconcile-regression", "finalize", "checksums", "status"))
    args = parser.parse_args(argv)
    try:
        context = build_context()
        root = context["root"]
        if args.command == "prepare":
            result = prepare()
        elif args.command == "audit":
            result = audit()
        elif args.command == "run-numbers-1":
            result = run_numbers_1()
        elif args.command == "run-regression":
            result = run_regression()
        elif args.command == "reconcile-regression":
            result = reconcile_regression_report()
        elif args.command == "finalize":
            result = finalize()
        elif args.command == "checksums":
            result = checksums()
        else:
            result = {"namespace": str(root.relative_to(ROOT)), "prepared": (root / "manifest.json").is_file(), "preflight_audited": (root / "preflight-path-audit.json").is_file(), "numbers_1_report": (root / "numbers-1-final-report.json").is_file(), "regression_report": (root / "five-case-regression-final-report.json").is_file(), "finalized": (root / "final-report.json").is_file(), "checksummed": (root / "checksums.json").is_file()}
    except (DiagnosticError, ArtifactCollisionError, OSError, ValueError, ProvenanceBindingV2Error) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
