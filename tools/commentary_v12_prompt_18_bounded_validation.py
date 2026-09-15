#!/usr/bin/env python3
"""Run the isolated Commentary v1.8 renderability validation.

The source five-case prompt-1.7 packets are read-only.  This diagnostic
rebuilds the same projection, ancestry envelope, provenance binding, source
packet, synthesis, and evidence identities with only the renderer contract
changed to prompt 1.8.  Numbers 2 is run once first; the five-case regression
is allowed only after that fresh result is fully valid.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
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
from bhf_agent.chapter_commentary.prompts import (
    CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V18,
    build_user_prompt,
    system_prompt_for_version,
)
from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    add_ancestry_envelope_to_prompt,
)
from bhf_agent.chapter_commentary.reader_level_projection import (
    add_projection_to_prompt,
    project_reader_level_ideas,
)
from bhf_agent.chapter_commentary.reader_provenance_binding import (
    add_provenance_binding_to_prompt,
    audit_provenance_binding,
    build_provenance_binding,
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


ARTIFACT_VERSION = "commentary-v1.2-prompt-1.8-bounded-validation-v1"
PROMPT_VERSION = "1.8"
SOURCE_PROMPT_VERSION = "1.7"
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
PROJECTION_VERSION = "reader-level-idea-projection-v1"
ANCESTRY_VERSION = "reader-level-idea-ancestry-envelope-v1"
PROVENANCE_BINDING_VERSION = "reader-provenance-binding-v1"
CODEX = Path("/home/johnwalker/.local/bin/codex")
EXPECTED_REFERENCES = historical.EXPECTED_FAILURES
ORDERED_REFERENCES = ("Numbers 2", "2 Kings 4", "Psalms 103", "Numbers 1", "Psalms 19")


class DiagnosticError(RuntimeError):
    """The bounded prompt-1.8 diagnostic cannot proceed safely."""


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


def _v18_record(record: dict[str, Any], source_public: dict[str, Any]) -> dict[str, Any]:
    prepared = record["prepared"]
    projection = project_reader_level_ideas(
        prepared.synthesis,
        source_pilot._clusters(prepared),
        prepared.bundle.evidence_items,
    )
    if projection.to_dict() != record["projection"]:
        raise DiagnosticError(f"projection identity changed for {source_public['reference']}")
    envelope = record["envelope"]
    binding = build_provenance_binding(envelope)
    binding_audit = audit_provenance_binding(binding, envelope)
    if not binding_audit["valid"] or binding["binding_hash"] != record["binding"]["binding_hash"]:
        raise DiagnosticError(f"provenance binding identity changed for {source_public['reference']}")
    chapter = bible.resolve_chapter(source_public["book"], int(source_public["chapter"]))
    canonical_text = bible.passage_text(chapter["verses"])
    original = build_user_prompt(
        source_public["reference"],
        source_public["book"],
        int(source_public["chapter"]),
        canonical_text,
        prepared.synthesis,
        prepared.bundle,
        prepared.synthesis.evidence_availability,
        prompt_version=PROMPT_VERSION,
    )
    candidate = add_provenance_binding_to_prompt(
        add_ancestry_envelope_to_prompt(
            add_projection_to_prompt(original, projection), envelope
        ),
        envelope,
        binding,
    )
    if "1.7" not in record["system_prompt"] and SOURCE_PROMPT_VERSION not in record["source_user_prompt"]:
        raise DiagnosticError("frozen prompt-1.7 source identity is missing")
    if "1.8" not in candidate or "1.7" in candidate.split("This contract is prompt", 1)[-1].split(".", 1)[0]:
        raise DiagnosticError(f"prompt 1.8 was not built for {source_public['reference']}")
    return {
        "row": source_public,
        "prepared": prepared,
        "projection": projection.to_dict(),
        "envelope": envelope,
        "binding": binding,
        "binding_audit": binding_audit,
        "source_system_prompt": record["system_prompt"],
        "source_user_prompt": record["candidate_prompt"],
        "system_prompt": system_prompt_for_version(PROMPT_VERSION),
        "candidate_prompt": candidate,
    }


def build_context(repo_root: Path = ROOT) -> dict[str, Any]:
    source = historical._source_context(repo_root)
    source_manifest = source["manifest"]
    source_records = {
        record["row"]["reference"]: record for record in source["records"]
    }
    source_rows = {
        row["reference"]: row
        for row in source_manifest["chapters"]
        if row["reference"] in EXPECTED_REFERENCES
    }
    if set(source_rows) != EXPECTED_REFERENCES:
        raise DiagnosticError("source structural-failure set is not exactly five chapters")
    records: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for ordinal, reference in enumerate(ORDERED_REFERENCES, 1):
        source_public = source_rows[reference]
        record = _v18_record(source_records[reference], source_public)
        row = {
            "ordinal": ordinal,
            "reference": reference,
            "book": source_public["book"],
            "chapter": source_public["chapter"],
            "slug": source_public["slug"],
            "source_batch": source_public["batch"],
            "source_ordinal": source_public["ordinal"],
            "source_packet_id": source_public["source_packet_id"],
            "source_packet_hash": source_public["source_packet_hash"],
            "evidence_hash": source_public["evidence_hash"],
            "synthesis_hash": source_public["synthesis_hash"],
            "projection_hash": source_public["projection_hash"],
            "ancestry_envelope_hash": source_public["ancestry_envelope_hash"],
            "provenance_binding_hash": source_public["provenance_binding_hash"],
            "source_system_prompt_sha256": source_public["system_prompt_sha256"],
            "source_candidate_input_sha256": source_public["candidate_input_sha256"],
            "system_prompt_sha256": sha256_bytes(record["system_prompt"].encode()),
            "candidate_input_sha256": sha256_bytes(record["candidate_prompt"].encode()),
            "response_filename": f"{ordinal:03d}_{source_public['slug']}.json",
        }
        rows.append(row)
        records[reference] = record
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
        "provenance_binding_version": PROVENANCE_BINDING_VERSION,
        "output_conformance_version": COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
        "output_conformance_implementation": COMMENTARY_OUTPUT_CONFORMANCE_IMPLEMENTATION,
        "max_structural_attempts": MAX_STRUCTURAL_ATTEMPTS,
        "numbers_2_single_initial_generation": True,
        "five_case_regression_authorized_only_after_numbers_2_success": True,
        "validator_unchanged": True,
        "synthesis_unchanged": True,
        "evidence_routing_unchanged": True,
        "projection_unchanged": True,
        "scoring_unchanged": True,
        "rows": rows,
    }
    seed = sha256_json(base)
    manifest = {
        **base,
        "namespace": f".bhf-data/bhf-commentary-candidates/{ARTIFACT_VERSION}-{seed[:20]}",
        "immutable_id": seed[:20],
    }
    manifest["manifest_identity"] = sha256_json(manifest)
    return {"manifest": manifest, "records": records, "source": source, "root": repo_root / manifest["namespace"]}


def prepare(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    manifest, root = context["manifest"], context["root"]
    _write_json(root / "manifest.json", manifest)
    _write_json(root / "contract-identities.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-contracts",
        "prompt_1_7_system_sha256": manifest["rows"][0]["source_system_prompt_sha256"],
        "prompt_1_8_system_sha256": manifest["rows"][0]["system_prompt_sha256"],
        "prompt_1_7_preserved": True,
        "prompt_1_8_only_contract_change": True,
        "projection": PROJECTION_VERSION,
        "ancestry_envelope": ANCESTRY_VERSION,
        "provenance_binding": PROVENANCE_BINDING_VERSION,
        "validator_behavior": "existing-validator-unchanged",
        "conformance_behavior": "existing-output-conformance-unchanged",
        "scoring_behavior": "existing-scorer-unchanged",
    })
    for row in manifest["rows"]:
        record = context["records"][row["reference"]]
        handoff = root / "renderer-input" / f"{row['ordinal']:03d}_{row['slug']}"
        _write_text(handoff / "system_prompt.txt", record["system_prompt"])
        _write_text(handoff / "user_prompt.txt", record["candidate_prompt"])
        _write_json(handoff / "metadata.json", {
            "artifact_version": f"{ARTIFACT_VERSION}-renderer-input",
            **row,
            "source_renderer_input_reused": True,
            "fresh_generation": True,
            "generation_count": 0,
        })
        _write_json(root / "source-identities" / f"{row['slug']}.json", {
            "reference": row["reference"],
            "source_packet_id": row["source_packet_id"],
            "source_packet_hash": row["source_packet_hash"],
            "evidence_hash": row["evidence_hash"],
            "synthesis_hash": row["synthesis_hash"],
            "projection_hash": row["projection_hash"],
            "ancestry_envelope_hash": row["ancestry_envelope_hash"],
            "provenance_binding_hash": row["provenance_binding_hash"],
            "source_system_prompt_sha256": row["source_system_prompt_sha256"],
            "source_candidate_input_sha256": row["source_candidate_input_sha256"],
            "system_prompt_sha256": row["system_prompt_sha256"],
            "candidate_input_sha256": row["candidate_input_sha256"],
            "only_prompt_contract_changed": True,
        })
    return {"status": "PREPARED", "namespace": manifest["namespace"], "chapter_count": 5}


def _exchange(handoff: Path) -> str:
    return (
        "You are the selected GPT-5.6 Sol prose renderer at medium effort. Do not call "
        "tools, inspect files, browse, or add explanation. Treat the exact SYSTEM PROMPT "
        "and USER PROMPT below as the complete generation contract. Return the requested "
        "raw JSON object only, with no Markdown fence or preamble.\n\nSYSTEM PROMPT\n"
        + (handoff / "system_prompt.txt").read_text(encoding="utf-8")
        + "\n\nUSER PROMPT\n"
        + (handoff / "user_prompt.txt").read_text(encoding="utf-8")
    )


def _render_one(root: Path, row: dict[str, Any], attempt: int) -> tuple[bytes, int, str]:
    handoff = root / "renderer-input" / f"{row['ordinal']:03d}_{row['slug']}"
    with tempfile.TemporaryDirectory(prefix="bhf-prompt-18-") as temp_dir:
        output = Path(temp_dir) / "response.txt"
        completed = subprocess.run(
            [str(CODEX), "exec", "--ephemeral", "--ignore-user-config", "-m", RENDERER,
             "-c", 'model_reasoning_effort="medium"', "-s", "read-only", "-C", temp_dir,
             "--skip-git-repo-check", "--output-last-message", str(output), "-"],
            input=_exchange(handoff), text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        if not output.is_file():
            raise DiagnosticError(
                f"renderer produced no output for {row['reference']} attempt {attempt}; "
                f"exit={completed.returncode} stderr={completed.stderr[-1000:]}"
            )
        return output.read_bytes(), completed.returncode, completed.stderr


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (canonical_json(payload) + "\n").encode("utf-8")


def _structurally_accepted(result: dict[str, Any]) -> bool:
    return result.get("structural_result", result.get("structural_status")) == "ACCEPTED"


def _evaluate_existing(record: dict[str, Any], public: dict[str, Any], conformed: dict[str, Any]):
    canonical_bytes = _canonical_bytes(conformed)
    result, parsed = binding_pilot._evaluate_one(record, public, canonical_bytes)
    return result, parsed, canonical_bytes


def _assessment(record: dict[str, Any], public: dict[str, Any], raw: bytes) -> dict[str, Any]:
    payload, parse_status, parse_errors = parse_renderer_json(raw)
    conformance = conform_renderer_output(
        payload, expected_reference=public["reference"], expected_book=public["book"],
        expected_chapter=int(public["chapter"]), parse_status=parse_status,
        parse_errors=parse_errors,
    )
    if conformance.valid and conformance.payload is not None:
        result, parsed, canonical_bytes = _evaluate_existing(record, public, conformance.payload)
        canonical_payload = conformance.payload
        retry_codes = result.get("rejection_codes", [])
    else:
        canonical_payload, canonical_bytes = None, None
        result = {
            "reference": public["reference"], "structural_result": "REJECTED",
            "rejection_codes": list(conformance.codes) or ["VALIDATION_FAILED"],
            "weighted_coverage": None, "core_coverage": None,
            "eligible_idea_utilization": None, "category_coverage": None,
            "dump_severity": None, "quality_gate_outcome": None,
            "readability_result": None, "word_count": None,
            "provenance_path_validity": None, "hard_provenance_errors": [],
            "ancestry_mismatch_count": None,
        }
        parsed = {
            "artifact_version": f"{ARTIFACT_VERSION}-parsed",
            "reference": public["reference"], "parse_status": conformance.parse_status,
            "validation_errors": list(conformance.errors), "raw_renderer_payload": payload,
            "normalized_renderer_payload": None,
        }
        retry_codes = result["rejection_codes"]
    return {
        "raw_response_sha256": sha256_bytes(raw),
        "parse_status": conformance.parse_status,
        "json_parsing_succeeded": payload is not None,
        "schema_parsing_succeeded": isinstance(payload, dict),
        "conformance_valid": conformance.valid,
        "conformance_errors": list(conformance.errors),
        "conformance_codes": list(conformance.codes),
        "normalization_events": list(conformance.events),
        "canonical_payload": canonical_payload,
        "canonical_response_sha256": sha256_bytes(canonical_bytes) if canonical_bytes else None,
        "validation_result": result,
        "parsed_result": parsed,
        "retry_eligible": structural_retry_allowed(attempt_ordinal=1, codes=retry_codes),
    }


def _write_attempt(root: Path, row: dict[str, Any], attempt: int, raw: bytes, assessment: dict[str, Any], stderr: str, exit_code: int) -> None:
    target = root / "attempts" / f"{row['ordinal']:03d}_{row['slug']}" / f"attempt-{attempt:03d}"
    write_immutable(target / "raw-response.json", raw)
    _write_text(target / "stderr.txt", stderr)
    _write_json(target / "process.json", {"exit_code": exit_code, "renderer": RENDERER, "effort": RENDERER_EFFORT})
    _write_json(target / "conformance.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-conformance",
        "reference": row["reference"], "attempt_ordinal": attempt,
        "raw_response_sha256": assessment["raw_response_sha256"],
        "parse_status": assessment["parse_status"],
        "json_parsing_succeeded": assessment["json_parsing_succeeded"],
        "schema_parsing_succeeded": assessment["schema_parsing_succeeded"],
        "conformance_valid": assessment["conformance_valid"],
        "conformance_errors": assessment["conformance_errors"],
        "conformance_codes": assessment["conformance_codes"],
        "normalization_events": assessment["normalization_events"],
        "canonical_response_sha256": assessment["canonical_response_sha256"],
        "retry_eligible": assessment["retry_eligible"],
    })
    _write_json(target / "parsed.json", assessment["parsed_result"])
    _write_json(target / "validation.json", assessment["validation_result"])
    if assessment["canonical_payload"] is not None:
        _write_json(target / "canonical-payload.json", assessment["canonical_payload"])


def _final_row(row: dict[str, Any], attempt: int, assessment: dict[str, Any]) -> dict[str, Any]:
    result = dict(assessment["validation_result"])
    result.update({
        "reference": row["reference"], "attempt_ordinal": attempt,
        "raw_response_sha256": assessment["raw_response_sha256"],
        "canonical_response_sha256": assessment["canonical_response_sha256"],
        "conformance_valid": assessment["conformance_valid"],
        "normalization_events": assessment["normalization_events"],
        "final_structural_validity": _structurally_accepted(result),
        "provenance_validity": result.get("provenance_path_validity"),
        "ancestry_validity": result.get("ancestry_mismatch_count") == 0 if result.get("ancestry_mismatch_count") is not None else None,
        "hard_provenance_errors": result.get("hard_provenance_errors", []),
        "gate_result": result.get("gate_result"),
        "readability": result.get("readability_result"),
        "word_count": result.get("prose_word_count", result.get("word_count")),
        "high_dump": result.get("dump_severity") == "HIGH",
    })
    return result


def _run_references(context: dict[str, Any], references: tuple[str, ...], *, allow_retry: bool) -> dict[str, Any]:
    root, manifest, records = context["root"], context["manifest"], context["records"]
    rows = {row["reference"]: row for row in manifest["rows"]}
    final_rows: list[dict[str, Any]] = []
    histories: list[dict[str, Any]] = []
    normalization_count = retry_count = retry_success_count = 0
    for reference in references:
        row, record = rows[reference], records[reference]
        assessments: list[dict[str, Any]] = []
        max_attempts = MAX_STRUCTURAL_ATTEMPTS if allow_retry else 1
        for attempt in range(1, max_attempts + 1):
            raw, exit_code, stderr = _render_one(root, row, attempt)
            assessment = _assessment(record, row, raw)
            _write_attempt(root, row, attempt, raw, assessment, stderr, exit_code)
            assessments.append(assessment)
            normalization_count += len(assessment["normalization_events"])
            if _structurally_accepted(assessment["validation_result"]):
                break
            if attempt == max_attempts or not assessment["retry_eligible"]:
                break
            retry_count += 1
        if len(assessments) == 2 and _structurally_accepted(assessments[-1]["validation_result"]):
            retry_success_count += 1
        final = _final_row(row, len(assessments), assessments[-1])
        final_rows.append(final)
        history = {
            "artifact_version": f"{ARTIFACT_VERSION}-attempt-history",
            "reference": reference,
            "attempts": [
                {
                    "attempt_ordinal": index,
                    "raw_response_sha256": item["raw_response_sha256"],
                    "normalization_events": item["normalization_events"],
                    "retry_eligible": item["retry_eligible"],
                    "final_accepted": _structurally_accepted(item["validation_result"]),
                }
                for index, item in enumerate(assessments, 1)
            ],
            "final_attempt_ordinal": len(assessments),
            "final_accepted": final["final_structural_validity"],
        }
        _write_json(root / "attempt-history" / f"{row['ordinal']:03d}_{row['slug']}.json", history)
        _write_json(root / "final" / "validation" / f"{row['ordinal']:03d}_{row['slug']}.json", final)
        if assessments[-1]["canonical_payload"] is not None:
            _write_json(root / "final" / "canonical" / f"{row['ordinal']:03d}_{row['slug']}.json", assessments[-1]["canonical_payload"])
        histories.append(history)
        print(f"{reference}: attempts={len(assessments)} structural={final['final_structural_validity']}", flush=True)
    return {
        "rows": final_rows,
        "histories": histories,
        "normalization_event_count": normalization_count,
        "structural_retry_count": retry_count,
        "retry_success_count": retry_success_count,
    }


def _numbers_2_success(row: dict[str, Any]) -> bool:
    return bool(
        row.get("final_structural_validity")
        and row.get("provenance_validity") is True
        and row.get("ancestry_validity") is True
        and not row.get("hard_provenance_errors")
        and row.get("high_dump") is False
    )


def run_numbers_2(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    manifest, root = context["manifest"], context["root"]
    if _read(root / "manifest.json") != manifest:
        raise DiagnosticError("prepared prompt-1.8 manifest changed")
    result = _run_references(context, ("Numbers 2",), allow_retry=False)
    row = result["rows"][0]
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-numbers-2-report",
        "namespace": manifest["namespace"], "prompt_version": PROMPT_VERSION,
        "source_packet_id": manifest["rows"][0]["source_packet_id"],
        "source_packet_hash": manifest["rows"][0]["source_packet_hash"],
        "fresh_generation_count": 1, "manual_editing": False,
        "success": _numbers_2_success(row), "row": row,
        "stop_if_unsuccessful": True,
    }
    _write_json(root / "numbers-2-final-report.json", report)
    return report


def run_regression(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    numbers_report = _read(root / "numbers-2-final-report.json")
    if numbers_report.get("success") is not True:
        raise DiagnosticError("five-case regression is not authorized because Numbers 2 did not succeed")
    result = _run_references(context, ORDERED_REFERENCES, allow_retry=True)
    rows = result["rows"]
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-five-case-regression",
        "namespace": manifest["namespace"], "prompt_version": PROMPT_VERSION,
        "references": list(ORDERED_REFERENCES),
        "authorization": "Numbers 2 fresh generation satisfied the bounded success criteria",
        "counts": {
            "chapters": len(rows),
            "first_attempt_structural_validity": sum(row["attempt_ordinal"] == 1 and row["final_structural_validity"] for row in rows),
            "normalization_event_count": result["normalization_event_count"],
            "structural_retry_count": result["structural_retry_count"],
            "retry_success_count": result["retry_success_count"],
            "final_structural_validity": sum(row["final_structural_validity"] for row in rows),
            "provenance_validity": sum(row.get("provenance_validity") is True for row in rows),
            "ancestry_validity": sum(row.get("ancestry_validity") is True for row in rows),
            "high_dump_count": sum(row.get("high_dump") is True for row in rows),
        },
        "criteria": {
            "final_structural_5_of_5": all(row["final_structural_validity"] for row in rows),
            "provenance_5_of_5": all(row.get("provenance_validity") is True for row in rows),
            "ancestry_5_of_5": all(row.get("ancestry_validity") is True for row in rows),
            "hard_provenance_errors_zero": all(not row.get("hard_provenance_errors") for row in rows),
            "high_dumps_zero": all(not row.get("high_dump") for row in rows),
            "validator_weakening": False, "fabricated_filler": False,
            "manual_editing": False,
        },
        "chapters": rows,
        "attempt_histories": result["histories"],
        "status": "PASS" if all(row["final_structural_validity"] and row.get("provenance_validity") is True and row.get("ancestry_validity") is True and not row.get("hard_provenance_errors") and not row.get("high_dump") for row in rows) else "FAIL",
    }
    _write_json(root / "five-case-regression-final-report.json", report)
    return report


def checksums(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root = context["root"]
    target = root / "checksums.json"
    files = sorted(path for path in root.rglob("*") if path.is_file() and path != target)
    value = {
        "artifact_version": f"{ARTIFACT_VERSION}-checksums",
        "files": {str(path.relative_to(root)): sha256_bytes(path.read_bytes()) for path in files},
    }
    _write_json(target, value)
    return {"status": "CHECKSUMMED", "namespace": str(root.relative_to(repo_root)), "file_count": len(files)}


def finalize(*, repo_root: Path = ROOT) -> dict[str, Any]:
    """Write the bounded final report without authorizing any further run."""

    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    numbers = _read(root / "numbers-2-final-report.json")
    regression_path = root / "five-case-regression-final-report.json"
    regression = _read(regression_path) if regression_path.is_file() else None
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-final-report",
        "namespace": manifest["namespace"],
        "prompt": {
            "version": PROMPT_VERSION,
            "source_prompt_version": SOURCE_PROMPT_VERSION,
            "prompt_1_7_system_sha256": manifest["rows"][0]["source_system_prompt_sha256"],
            "prompt_1_8_system_sha256": manifest["rows"][0]["system_prompt_sha256"],
            "prompt_1_8_user_template_sha256": sha256_bytes(
                CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V18.encode()
            ),
            "prompt_1_7_preserved": True,
        },
        "source_contracts": {
            "renderer": RENDERER,
            "effort": RENDERER_EFFORT,
            "projection": PROJECTION_VERSION,
            "ancestry_envelope": ANCESTRY_VERSION,
            "provenance_binding": PROVENANCE_BINDING_VERSION,
            "output_conformance": COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
            "source_packet_id": manifest["rows"][0]["source_packet_id"],
            "source_packet_hash": manifest["rows"][0]["source_packet_hash"],
            "evidence_hashes_unchanged": True,
            "synthesis_hashes_unchanged": True,
            "projection_hashes_unchanged": True,
            "ancestry_hashes_unchanged": True,
            "provenance_binding_hashes_unchanged": True,
        },
        "numbers_2": numbers,
        "five_case_regression": regression,
        "regression_authorized": numbers.get("success") is True,
        "regression_run": regression is not None,
        "stop_reason": (
            "Prompt 1.8 still produced sections: []; stop before regression and bulk generation."
            if numbers.get("success") is not True
            else "bounded regression completed"
        ),
        "production_behavior_changes": False,
        "validator_weakening": False,
        "manual_editing": False,
        "fabricated_prose": False,
        "bulk_generation_started": False,
    }
    _write_json(root / "final-report.json", report)
    return {"status": "FINALIZED", "namespace": manifest["namespace"], "success": numbers.get("success") is True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run-numbers-2", "run-regression", "finalize", "checksums", "status"))
    args = parser.parse_args(argv)
    try:
        context = build_context()
        if args.command == "prepare":
            result = prepare()
        elif args.command == "run-numbers-2":
            result = run_numbers_2()
        elif args.command == "run-regression":
            result = run_regression()
        elif args.command == "finalize":
            result = finalize()
        elif args.command == "checksums":
            result = checksums()
        else:
            root = context["root"]
            result = {"namespace": str(root.relative_to(ROOT)), "prepared": (root / "manifest.json").is_file(), "numbers_2_report": (root / "numbers-2-final-report.json").is_file(), "regression_report": (root / "five-case-regression-final-report.json").is_file(), "checksummed": (root / "checksums.json").is_file()}
    except (DiagnosticError, ArtifactCollisionError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
