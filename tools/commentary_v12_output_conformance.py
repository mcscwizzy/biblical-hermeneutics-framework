#!/usr/bin/env python3
"""Run the bounded five-failure Commentary v1.2 output-conformance diagnostic.

The frozen provenance-binding scale pilot is read-only.  This diagnostic
reuses its five structural-failure packets, captures fresh renderer attempts
under the exact same contract, applies only deterministic output conformance,
then delegates canonical validation, provenance binding, ancestry auditing,
scoring, and Gate v2.1 to the existing implementations.
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

from bhf_agent.chapter_commentary.output_conformance import (
    COMMENTARY_OUTPUT_CONFORMANCE_IMPLEMENTATION,
    COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
    MAX_STRUCTURAL_ATTEMPTS,
    ConformanceResult,
    conform_renderer_output,
    parse_renderer_json,
    structural_retry_allowed,
)
from framework.commentary.production.models import (
    ArtifactCollisionError,
    canonical_json,
    sha256_bytes,
    sha256_json,
    slug,
    write_immutable,
)
from tools import commentary_v12_scale_pilot_provenance_binding as binding_pilot
from tools import commentary_v12_scale_pilot as original_pilot


ARTIFACT_VERSION = "commentary-output-conformance-v1-diagnostic"
SOURCE_NAMESPACE = (
    ".bhf-data/bhf-commentary-candidates/"
    "commentary-v1.2-scale-pilot-provenance-binding-v1-f139d722270544978d04"
)
SOURCE_RESULT = "SCALE_PILOT_NOT_READY"
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
PROMPT_VERSION = "1.7"
PROJECTION_VERSION = "reader-level-idea-projection-v1"
ANCESTRY_VERSION = "reader-level-idea-ancestry-envelope-v1"
PROVENANCE_BINDING_VERSION = "reader-provenance-binding-v1"
CODEX = Path("/home/johnwalker/.local/bin/codex")
EXPECTED_FAILURES = frozenset(
    {"Numbers 2", "2 Kings 4", "Psalms 103", "Numbers 1", "Psalms 19"}
)


class DiagnosticError(RuntimeError):
    """The frozen source or bounded diagnostic is incomplete or changed."""


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
    expected = sha256_json({k: v for k, v in value.items() if k != key})
    if value.get(key) != expected:
        raise DiagnosticError(f"{label} identity mismatch")


def _source_context(repo_root: Path = ROOT) -> dict[str, Any]:
    context = binding_pilot.build_context(repo_root)
    root = repo_root / SOURCE_NAMESPACE
    stored = _read(root / "manifest.json")
    _verify_identity(stored, "manifest_identity", "source provenance-binding manifest")
    if stored != context["manifest"]:
        raise DiagnosticError("frozen provenance-binding source manifest changed")
    failures = {
        row["reference"]
        for row in _read(root / "final-report.json")["chapters"]
        if row.get("final_chapter_classification") == "STRUCTURAL_FAILURE"
    }
    if failures != EXPECTED_FAILURES:
        raise DiagnosticError(f"unexpected source structural failures: {sorted(failures)}")
    return context


def _source_failure_identity(
    repo_root: Path, source_root: Path, public: dict[str, Any]
) -> dict[str, Any]:
    batch_root = source_root / f"batch-{int(public['batch']):03d}"
    stem = f"{public['ordinal']:03d}_{public['slug']}"
    raw_path = batch_root / "responses/raw" / public["response_filename"]
    parsed = _read(batch_root / "parsed" / public["response_filename"])
    validation = _read(batch_root / "validation" / public["response_filename"])
    raw = _read(raw_path)
    sections = raw.get("sections")
    empty_sections = sections == []
    malformed_fields: list[dict[str, Any]] = []
    for section_index, section in enumerate(sections if isinstance(sections, list) else []):
        if not isinstance(section, dict):
            continue
        for block_index, block in enumerate(section.get("blocks", [])):
            if not isinstance(block, dict):
                continue
            for ref_index, ref in enumerate(block.get("verse_refs", [])):
                if ref == public["reference"]:
                    malformed_fields.append(
                        {
                            "path": f"sections[{section_index}].blocks[{block_index}].verse_refs[{ref_index}]",
                            "raw_value": ref,
                            "expected_canonical_shape": f"{public['reference']}:<verse-or-range>",
                            "chapter_only": True,
                        }
                    )
    prose_elsewhere = any(
        isinstance(value, str) and len(value.split()) >= 8
        for key, value in raw.items()
        if key != "sections"
    )
    return {
        "reference": public["reference"],
        "source_batch": public["batch"],
        "source_response_path": str(raw_path.relative_to(repo_root)),
        "source_parsed_path": str((batch_root / "parsed" / public["response_filename"]).relative_to(repo_root)),
        "source_validation_path": str((batch_root / "validation" / public["response_filename"]).relative_to(repo_root)),
        "raw_response_sha256": validation.get("response_sha256") or sha256_bytes(raw_path.read_bytes()),
        "exact_structural_rejection_codes": validation.get("rejection_codes", []),
        "json_parsing_succeeded": parsed.get("parse_status") == "JSON_OBJECT",
        "schema_parsing_succeeded": isinstance(parsed.get("renderer_payload"), dict),
        "exact_malformed_or_empty_field": (
            {"path": "sections", "raw_value": [], "representation": "literal empty JSON array"}
            if empty_sections
            else malformed_fields
        ),
        "prose_existed_elsewhere_in_response": prose_elsewhere,
        "provenance_references_otherwise_valid": (
            validation.get("provenance_path_validity") is True
            and validation.get("ancestry_validation", {}).get("valid") is True
            and not validation.get("hard_provenance_errors")
        ),
        "generation_or_normalization_diagnosis": (
            "generation-side missing required content"
            if empty_sections
            else "generation-side chapter-only reference; normalization cannot infer a verse"
        ),
        "sections_literal_empty_array": empty_sections,
        "raw_payload": raw,
        "parsed_validation_errors": parsed.get("validation_errors", []),
        "validation_summary": {
            "structural_status": validation.get("structural_status"),
            "structural_validity": validation.get("structural_validity"),
            "provenance_path_validity": validation.get("provenance_path_validity"),
            "ancestry_safe": validation.get("ancestry_validation", {}).get("valid"),
            "hard_provenance_errors": validation.get("hard_provenance_errors", []),
        },
    }


def build_manifest(repo_root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    context = _source_context(repo_root)
    source_manifest = context["manifest"]
    source_root = repo_root / SOURCE_NAMESPACE
    source_by_reference = {
        public["reference"]: (record, public)
        for record, public in zip(context["records"], source_manifest["chapters"], strict=True)
        if public["reference"] in EXPECTED_FAILURES
    }
    if set(source_by_reference) != EXPECTED_FAILURES:
        raise DiagnosticError("source failure set is not exactly five chapters")
    rows: list[dict[str, Any]] = []
    records: dict[str, Any] = {}
    failures: list[dict[str, Any]] = []
    for ordinal, (reference, pair) in enumerate(
        sorted(source_by_reference.items(), key=lambda item: item[1][1]["ordinal"]), 1
    ):
        record, public = pair
        source_failure = _source_failure_identity(repo_root, source_root, public)
        if public["reference"] != reference:
            raise DiagnosticError("source reference identity mismatch")
        stem = f"{ordinal:03d}_{slug(public['book'], int(public['chapter']))}"
        row = {
            "ordinal": ordinal,
            "source_ordinal": public["ordinal"],
            "reference": reference,
            "book": public["book"],
            "chapter": public["chapter"],
            "slug": slug(public["book"], int(public["chapter"])),
            "response_filename": f"{stem}.json",
            "source_response_filename": public["response_filename"],
            "source_batch": public["batch"],
            "source_packet_id": public["source_packet_id"],
            "source_packet_hash": public["source_packet_hash"],
            "evidence_hash": public["evidence_hash"],
            "synthesis_hash": public["synthesis_hash"],
            "projection_hash": public["projection_hash"],
            "ancestry_envelope_hash": public["ancestry_envelope_hash"],
            "provenance_binding_hash": public["provenance_binding_hash"],
            "source_candidate_input_sha256": public["source_candidate_input_sha256"],
            "candidate_input_sha256": public["candidate_input_sha256"],
            "system_prompt_sha256": public["system_prompt_sha256"],
            "source_failure_raw_response_sha256": source_failure["raw_response_sha256"],
        }
        rows.append(row)
        records[reference] = record
        failures.append({k: v for k, v in source_failure.items() if k != "raw_payload"})
    conformance_hash = sha256_bytes(
        (repo_root / "bhf_agent/chapter_commentary/output_conformance.py").read_bytes()
    )
    diagnostic_hash = sha256_bytes(
        (repo_root / "tools/commentary_v12_output_conformance.py").read_bytes()
    )
    base = {
        "artifact_version": ARTIFACT_VERSION,
        "source_scale_pilot": {
            "namespace": SOURCE_NAMESPACE,
            "manifest_identity": source_manifest["manifest_identity"],
            "result": SOURCE_RESULT,
            "exact_source_corpus_reused": True,
        },
        "source_failure_references": [row["reference"] for row in rows],
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "runtime_self_attestation": False,
        "prompt_version": PROMPT_VERSION,
        "projection_version": PROJECTION_VERSION,
        "ancestry_envelope_version": ANCESTRY_VERSION,
        "provenance_binding_version": PROVENANCE_BINDING_VERSION,
        "output_conformance_version": COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
        "output_conformance_implementation": COMMENTARY_OUTPUT_CONFORMANCE_IMPLEMENTATION,
        "output_conformance_source_sha256": conformance_hash,
        "diagnostic_implementation_source_sha256": diagnostic_hash,
        "max_structural_attempts": MAX_STRUCTURAL_ATTEMPTS,
        "one_fresh_attempt_one_per_chapter": True,
        "scoring_unchanged": True,
        "validator_unchanged": True,
        "synthesis_unchanged": True,
        "evidence_routing_unchanged": True,
        "chapters": rows,
    }
    seed = sha256_json(base)
    manifest = {**base, "immutable_id": seed[:20]}
    manifest["namespace"] = (
        ".bhf-data/bhf-commentary-candidates/"
        f"commentary-output-conformance-v1-{seed[:20]}"
    )
    manifest["manifest_identity"] = sha256_json(manifest)
    return manifest, {"context": context, "records": records, "failures": failures}


def _verify_manifest(manifest: dict[str, Any]) -> None:
    _verify_identity(manifest, "manifest_identity", "output-conformance manifest")
    if manifest.get("artifact_version") != ARTIFACT_VERSION:
        raise DiagnosticError("unsupported output-conformance artifact version")
    if manifest.get("renderer") != RENDERER or manifest.get("renderer_effort") != RENDERER_EFFORT:
        raise DiagnosticError("renderer identity or effort mismatch")
    if manifest.get("prompt_version") != PROMPT_VERSION:
        raise DiagnosticError("prompt contract changed")
    if manifest.get("output_conformance_version") != COMMENTARY_OUTPUT_CONFORMANCE_VERSION:
        raise DiagnosticError("conformance version changed")
    if manifest.get("max_structural_attempts") != MAX_STRUCTURAL_ATTEMPTS:
        raise DiagnosticError("retry maximum changed")
    if len(manifest.get("chapters", [])) != 5:
        raise DiagnosticError("diagnostic must contain exactly five chapters")


def prepare(*, repo_root: Path = ROOT) -> dict[str, Any]:
    manifest, material = build_manifest(repo_root)
    _verify_manifest(manifest)
    root = repo_root / manifest["namespace"]
    _write_json(root / "manifest.json", manifest)
    _write_json(root / "contract-identities.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-contracts",
        "prompt": PROMPT_VERSION,
        "projection": PROJECTION_VERSION,
        "ancestry_envelope": ANCESTRY_VERSION,
        "provenance_binding": PROVENANCE_BINDING_VERSION,
        "output_conformance": COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
        "output_conformance_source_sha256": manifest["output_conformance_source_sha256"],
        "validator_behavior": "existing-validator-unchanged",
        "scorer_behavior": "existing-scorer-unchanged",
        "synthesis_behavior": "existing-synthesis-unchanged",
    })
    _write_json(root / "deterministic-normalization-rules.json", {
        "artifact_version": f"{COMMENTARY_OUTPUT_CONFORMANCE_VERSION}-rules",
        "rules": [
            "A single non-empty verse_refs string may become a one-item array.",
            "A parseable reference may be serialized with the canonical CKL book/chapter/verse form.",
            "Chapter-only references in ordinary sections are ambiguous and are rejected; no verse is inferred.",
            "Empty sections and empty blocks are rejected; no prose or evidence is fabricated.",
            "Provenance refs are resolved only by reader-provenance-binding-v1 after conformance.",
        ],
    })
    _write_json(root / "source-failure-identities.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-source-failures",
        "source_namespace": SOURCE_NAMESPACE,
        "failures": material["failures"],
    })
    context = material["context"]
    source_manifest = context["manifest"]
    for row in manifest["chapters"]:
        record = material["records"][row["reference"]]
        source_public = next(item for item in source_manifest["chapters"] if item["reference"] == row["reference"])
        source_root = repo_root / SOURCE_NAMESPACE
        source_batch = source_root / f"batch-{int(source_public['batch']):03d}" / "renderer-input" / f"{source_public['ordinal']:03d}_{source_public['slug']}"
        handoff = root / "renderer-input" / f"{row['ordinal']:03d}_{row['slug']}"
        _write_text(handoff / "system_prompt.txt", (source_batch / "system_prompt.txt").read_text(encoding="utf-8"))
        _write_text(handoff / "user_prompt.txt", (source_batch / "user_prompt.txt").read_text(encoding="utf-8"))
        _write_json(handoff / "metadata.json", {
            "artifact_version": f"{ARTIFACT_VERSION}-renderer-input",
            **row,
            "source_manifest_identity": source_manifest["manifest_identity"],
            "generation_count": 0,
            "fresh_generation": True,
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
            "source_candidate_input_sha256": row["source_candidate_input_sha256"],
            "candidate_input_sha256": row["candidate_input_sha256"],
            "source_renderer_input_reused": True,
            "source_record_rebuilt": record["row"]["reference"],
        })
    return {
        "status": "PREPARED",
        "namespace": manifest["namespace"],
        "immutable_id": manifest["immutable_id"],
        "chapter_count": 5,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "output_conformance_version": COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
    }


def _root(repo_root: Path, manifest: dict[str, Any]) -> Path:
    return repo_root / manifest["namespace"]


def _exchange(handoff: Path) -> str:
    return (
        "You are the selected GPT-5.6 Sol prose renderer at medium effort. "
        "Do not call tools, inspect files, browse, or add explanation. Treat the exact "
        "SYSTEM PROMPT and USER PROMPT below as the complete generation contract. "
        "Return the requested raw JSON object only, with no Markdown fence or preamble.\n\n"
        "SYSTEM PROMPT\n" + (handoff / "system_prompt.txt").read_text(encoding="utf-8")
        + "\n\nUSER PROMPT\n" + (handoff / "user_prompt.txt").read_text(encoding="utf-8")
    )


def _render_one(root: Path, row: dict[str, Any], attempt: int) -> tuple[bytes, int]:
    handoff = root / "renderer-input" / f"{row['ordinal']:03d}_{row['slug']}"
    with tempfile.TemporaryDirectory(prefix="bhf-output-conformance-") as temp_dir:
        output = Path(temp_dir) / "response.txt"
        completed = subprocess.run(
            [
                str(CODEX), "exec", "--ephemeral", "--ignore-user-config",
                "-m", RENDERER, "-c", 'model_reasoning_effort="medium"',
                "-s", "read-only", "-C", temp_dir, "--skip-git-repo-check",
                "--output-last-message", str(output), "-",
            ],
            input=_exchange(handoff),
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        if not output.is_file():
            raise DiagnosticError(
                f"renderer produced no bytes for {row['reference']} attempt {attempt} "
                f"(exit {completed.returncode}): {completed.stderr[-1000:]}"
            )
        return output.read_bytes(), completed.returncode


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (canonical_json(payload) + "\n").encode("utf-8")


def _structurally_accepted(result: dict[str, Any]) -> bool:
    return result.get("structural_result", result.get("structural_status")) == "ACCEPTED"


def _evaluate_existing(
    record: dict[str, Any], public: dict[str, Any], conformed: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    canonical_bytes = _canonical_bytes(conformed)
    result, parsed = binding_pilot._evaluate_one(record, public, canonical_bytes)
    return result, parsed, canonical_bytes


def _attempt_assessment(
    record: dict[str, Any], public: dict[str, Any], raw: bytes
) -> dict[str, Any]:
    payload, parse_status, parse_errors = parse_renderer_json(raw)
    conformance = conform_renderer_output(
        payload,
        expected_reference=public["reference"],
        expected_book=public["book"],
        expected_chapter=int(public["chapter"]),
        parse_status=parse_status,
        parse_errors=parse_errors,
    )
    result: dict[str, Any] | None = None
    parsed: dict[str, Any] | None = None
    canonical_payload: dict[str, Any] | None = None
    canonical_bytes: bytes | None = None
    if conformance.valid and conformance.payload is not None:
        result, parsed, canonical_bytes = _evaluate_existing(record, public, conformance.payload)
        canonical_payload = conformance.payload
        codes = result.get("rejection_codes", [])
        retry_eligible = not _structurally_accepted(result) and structural_retry_allowed(
            attempt_ordinal=1, codes=codes
        )
    else:
        codes = list(conformance.codes)
        result = {
            "reference": public["reference"],
            "structural_result": "REJECTED",
            "rejection_codes": codes or ["VALIDATION_FAILED"],
            "weighted_coverage": None,
            "core_coverage": None,
            "eligible_idea_utilization": None,
            "category_coverage": None,
            "dump_severity": None,
            "quality_gate_outcome": None,
            "readability_result": None,
            "word_count": None,
            "provenance_path_validity": None,
            "hard_provenance_errors": [],
            "ancestry_mismatch_count": None,
        }
        parsed = {
            "artifact_version": f"{ARTIFACT_VERSION}-parsed",
            "reference": public["reference"],
            "parse_status": conformance.parse_status,
            "validation_errors": list(conformance.errors),
            "raw_renderer_payload": payload,
            "normalized_renderer_payload": None,
        }
        retry_eligible = structural_retry_allowed(
            attempt_ordinal=1, codes=result["rejection_codes"]
        )
    return {
        "raw_response_sha256": sha256_bytes(raw),
        "parse_status": conformance.parse_status,
        "json_parsing_succeeded": payload is not None,
        "schema_parsing_succeeded": payload is not None and isinstance(payload, dict),
        "conformance_valid": conformance.valid,
        "conformance_errors": list(conformance.errors),
        "conformance_codes": list(conformance.codes),
        "normalization_events": list(conformance.events),
        "canonical_payload": canonical_payload,
        "canonical_response_sha256": sha256_bytes(canonical_bytes) if canonical_bytes else None,
        "validation_result": result,
        "parsed_result": parsed,
        "retry_eligible": retry_eligible,
    }


def _write_attempt_artifacts(
    root: Path, row: dict[str, Any], attempt: int, raw: bytes, assessment: dict[str, Any]
) -> None:
    attempt_root = root / "attempts" / f"{row['ordinal']:03d}_{row['slug']}" / f"attempt-{attempt:03d}"
    write_immutable(attempt_root / "raw-response.json", raw)
    _write_json(attempt_root / "conformance.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-conformance-result",
        "reference": row["reference"],
        "attempt_ordinal": attempt,
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
    if assessment["canonical_payload"] is not None:
        _write_json(attempt_root / "canonical-payload.json", assessment["canonical_payload"])
    _write_json(attempt_root / "parsed.json", assessment["parsed_result"])
    _write_json(attempt_root / "validation.json", assessment["validation_result"])


def _final_row(row: dict[str, Any], attempt: int, assessment: dict[str, Any]) -> dict[str, Any]:
    result = dict(assessment["validation_result"])
    result.update(
        {
            "reference": row["reference"],
            "attempt_ordinal": attempt,
            "raw_response_sha256": assessment["raw_response_sha256"],
            "canonical_response_sha256": assessment["canonical_response_sha256"],
            "conformance_valid": assessment["conformance_valid"],
            "normalization_events": assessment["normalization_events"],
            "final_structural_validity": _structurally_accepted(result),
            "provenance_path_validity": result.get("provenance_path_validity"),
            "ancestry_safe": (
                result.get("ancestry_mismatch_count") == 0
                if result.get("ancestry_mismatch_count") is not None
                else None
            ),
            "hard_provenance_errors": result.get("hard_provenance_errors", []),
            "weighted_coverage": result.get("weighted_coverage"),
            "core_coverage": result.get("core_coverage"),
            "eligible_utilization": result.get("eligible_idea_utilization"),
            "category_coverage": result.get("category_coverage"),
            "gate_result": result.get("gate_result"),
            "readability": result.get("readability_result"),
            "word_count": result.get("prose_word_count", result.get("word_count")),
        }
    )
    return result


def run(*, repo_root: Path = ROOT) -> dict[str, Any]:
    manifest, material = build_manifest(repo_root)
    _verify_manifest(manifest)
    root = _root(repo_root, manifest)
    stored = _read(root / "manifest.json")
    if stored != manifest:
        raise DiagnosticError("prepared output-conformance manifest changed")
    records = material["records"]
    source_public_rows = {
        source_row["reference"]: source_row
        for source_row in material["context"]["manifest"]["chapters"]
    }
    attempt_history: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    first_success = 0
    normalization_count = 0
    retry_count = 0
    retry_success_count = 0
    for row in manifest["chapters"]:
        record = records[row["reference"]]
        source_public = source_public_rows[row["reference"]]
        attempt_assessments: list[dict[str, Any]] = []
        for attempt in range(1, MAX_STRUCTURAL_ATTEMPTS + 1):
            attempt_root = root / "attempts" / f"{row['ordinal']:03d}_{row['slug']}" / f"attempt-{attempt:03d}"
            raw_path = attempt_root / "raw-response.json"
            if raw_path.exists():
                raw = raw_path.read_bytes()
                assessment = _attempt_assessment(record, source_public, raw)
                _write_attempt_artifacts(root, row, attempt, raw, assessment)
            else:
                raw, exit_code = _render_one(root, row, attempt)
                write_immutable(raw_path, raw)
                assessment = _attempt_assessment(record, source_public, raw)
                assessment["renderer_exit_code"] = exit_code
                _write_attempt_artifacts(root, row, attempt, raw, assessment)
            attempt_assessments.append(assessment)
            normalization_count += len(assessment["normalization_events"])
            if attempt == 1 and _structurally_accepted(assessment["validation_result"]):
                first_success += 1
                break
            if attempt == 1 and not assessment["retry_eligible"]:
                break
            if attempt == MAX_STRUCTURAL_ATTEMPTS:
                break
            retry_count += 1
        final_attempt = len(attempt_assessments)
        final_assessment = attempt_assessments[-1]
        if final_attempt == 2 and _structurally_accepted(final_assessment["validation_result"]):
            retry_success_count += 1
        final = _final_row(row, final_attempt, final_assessment)
        final_rows.append(final)
        history = {
            "artifact_version": f"{ARTIFACT_VERSION}-attempt-history",
            "reference": row["reference"],
            "attempts": [
                {
                    "attempt_ordinal": index,
                    "raw_response_sha256": assessment["raw_response_sha256"],
                    "first_attempt_rejection_reason": (
                        attempt_assessments[0]["conformance_errors"]
                        or attempt_assessments[0]["validation_result"].get("rejection_codes", [])
                    ) if index == 2 else None,
                    "deterministic_normalization_attempted": bool(assessment["normalization_events"]),
                    "retry_trigger": (
                        attempt_assessments[0]["conformance_codes"]
                        or attempt_assessments[0]["validation_result"].get("rejection_codes", [])
                    ) if index == 2 else None,
                    "final_accepted": _structurally_accepted(assessment["validation_result"]),
                }
                for index, assessment in enumerate(attempt_assessments, 1)
            ],
            "final_attempt_ordinal": final_attempt,
            "final_accepted": final["final_structural_validity"],
        }
        _write_json(root / "attempt-history" / f"{row['ordinal']:03d}_{row['slug']}.json", history)
        _write_json(root / "final" / "validation" / f"{row['ordinal']:03d}_{row['slug']}.json", final)
        if final_assessment["canonical_payload"] is not None:
            _write_json(root / "final" / "canonical" / f"{row['ordinal']:03d}_{row['slug']}.json", final_assessment["canonical_payload"])
        attempt_history.append(history)
        print(f"{row['reference']}: attempts={final_attempt} structural={final['final_structural_validity']}", flush=True)
    report = _build_report(manifest, final_rows, attempt_history, first_success, normalization_count, retry_count, retry_success_count)
    _write_json(root / "replication-report.json", report)
    _write_json(root / "comparison-report.json", _comparison_report(repo_root, manifest, final_rows))
    return report


def _build_report(
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    history: list[dict[str, Any]],
    first_success: int,
    normalization_count: int,
    retry_count: int,
    retry_success_count: int,
) -> dict[str, Any]:
    total = len(rows)
    return {
        "artifact_version": f"{ARTIFACT_VERSION}-replication",
        "namespace": manifest["namespace"],
        "source_scale_pilot": manifest["source_scale_pilot"],
        "contract": {
            "prompt": PROMPT_VERSION,
            "projection": PROJECTION_VERSION,
            "ancestry_envelope": ANCESTRY_VERSION,
            "provenance_binding": PROVENANCE_BINDING_VERSION,
            "output_conformance": COMMENTARY_OUTPUT_CONFORMANCE_VERSION,
            "renderer": RENDERER,
            "effort": RENDERER_EFFORT,
        },
        "replication_rule": "one attempt 1, then at most one exact-contract structural retry",
        "counts": {
            "chapters": total,
            "first_attempt_structural_success": first_success,
            "first_attempt_structural_success_rate": round(first_success / total, 4) if total else 0,
            "deterministic_normalization_recovery_count": sum(
                bool(row.get("normalization_events")) and row.get("attempt_ordinal") == 1 and row.get("final_structural_validity")
                for row in rows
            ),
            "normalization_event_count": normalization_count,
            "structural_retry_count": retry_count,
            "retry_success_count": retry_success_count,
            "final_structural_success": sum(row["final_structural_validity"] for row in rows),
            "final_structural_success_rate": round(sum(row["final_structural_validity"] for row in rows) / total, 4) if total else 0,
        },
        "success_criteria": {
            "final_structural_validity_5_of_5": sum(row["final_structural_validity"] for row in rows) == 5,
            "provenance_path_validity_5_of_5": all(row.get("provenance_path_validity") is True for row in rows),
            "ancestry_safe_5_of_5": all(row.get("ancestry_safe") is True for row in rows),
            "hard_provenance_errors_zero": sum(bool(row.get("hard_provenance_errors")) for row in rows) == 0,
            "high_dumps_zero": sum(row.get("dump_severity") == "HIGH" for row in rows) == 0,
            "validator_weakening": False,
            "invented_prose_during_normalization": False,
            "manual_response_editing": False,
        },
        "quality_metrics": [
            {
                "reference": row["reference"],
                "weighted_coverage": row.get("weighted_coverage"),
                "core_coverage": row.get("core_coverage"),
                "eligible_utilization": row.get("eligible_utilization"),
                "category_coverage": row.get("category_coverage"),
                "gate_result": row.get("gate_result"),
                "readability": row.get("readability"),
                "word_count": row.get("word_count"),
            }
            for row in rows
        ],
        "attempt_history": history,
        "chapters": rows,
        "final_status": "PROMISING" if all(
            row["final_structural_validity"]
            and row.get("provenance_path_validity") is True
            and row.get("ancestry_safe") is True
            and not row.get("hard_provenance_errors")
            and row.get("dump_severity") != "HIGH"
            for row in rows
        ) else "FAILED",
    }


def _comparison_report(repo_root: Path, manifest: dict[str, Any], final_rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_root = repo_root / SOURCE_NAMESPACE
    historical = _read(source_root / "final-report.json")
    affected = set(manifest["source_failure_references"])
    unchanged = [row for row in historical["chapters"] if row["reference"] not in affected]
    combined = unchanged + final_rows
    structural = sum(bool(row.get("structural_validity", row.get("final_structural_validity"))) for row in combined)
    provenance = sum(bool(row.get("provenance_path_validity")) for row in combined)
    ancestry = sum(
        row.get("ancestry_mismatch_count", 1) == 0 if "ancestry_mismatch_count" in row else bool(row.get("ancestry_safe"))
        for row in combined
    )
    hard_safe = sum(not row.get("hard_provenance_errors") for row in combined)
    high_dumps = sum(row.get("dump_severity") == "HIGH" for row in combined)
    return {
        "artifact_version": f"{ARTIFACT_VERSION}-counterfactual",
        "historical_namespace_unchanged": SOURCE_NAMESPACE,
        "historical_70_structurally_usable_responses_kept_unchanged": len(unchanged) == 70,
        "historical_immutable_responses_rewritten": False,
        "five_failure_recoverability_basis": "fresh exact-contract replication final artifacts; historical bytes are not replaced",
        "modeled_population": 75,
        "modeled_metrics": {
            "structural_validity_count": structural,
            "structural_validity_rate": round(structural / 75, 4),
            "provenance_path_validity_count": provenance,
            "ancestry_safe_count": ancestry,
            "hard_provenance_safe_count": hard_safe,
            "high_dump_count": high_dumps,
        },
        "unchanged_scale_thresholds": {
            "structural_at_least_98": structural / 75 * 100 >= 98,
            "provenance_path_at_least_98": provenance / 75 * 100 >= 98,
            "ancestry_at_least_98": ancestry / 75 * 100 >= 98,
            "hard_provenance_at_least_98": hard_safe / 75 * 100 >= 98,
            "high_dump_near_zero": high_dumps / 75 * 100 <= 1.5,
            "quality_thresholds_not_tuned": True,
        },
        "recommendation": (
            "If the five-chapter replication is PROMISING, run this bounded counterfactual review before any new full pilot; "
            "do not rewrite the historical namespace. Structural remediation alone does not imply overall scale readiness "
            "because the frozen quality/gate thresholds remain unchanged."
        ),
    }


def checksums(*, repo_root: Path = ROOT) -> dict[str, Any]:
    manifest, _ = build_manifest(repo_root)
    root = _root(repo_root, manifest)
    target = root / "checksums.json"
    files = sorted(path for path in root.rglob("*") if path.is_file() and path != target)
    value = {
        "artifact_version": f"{ARTIFACT_VERSION}-checksums",
        "files": {str(path.relative_to(root)): sha256_bytes(path.read_bytes()) for path in files},
    }
    _write_json(target, value)
    return {"status": "CHECKSUMMED", "namespace": manifest["namespace"], "file_count": len(files)}


def status(*, repo_root: Path = ROOT) -> dict[str, Any]:
    manifest, _ = build_manifest(repo_root)
    root = _root(repo_root, manifest)
    return {
        "namespace": manifest["namespace"],
        "prepared": (root / "manifest.json").is_file(),
        "replicated": (root / "replication-report.json").is_file(),
        "checksummed": (root / "checksums.json").is_file(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "checksums", "status"))
    args = parser.parse_args(argv)
    try:
        result = (
            prepare()
            if args.command == "prepare"
            else run()
            if args.command == "run"
            else checksums()
            if args.command == "checksums"
            else status()
        )
    except (DiagnosticError, ArtifactCollisionError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
