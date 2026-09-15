#!/usr/bin/env python3
"""Prepare, render once, and evaluate the v1.2 provenance-binding replication.

This diagnostic uses exactly the four chapters that failed the frozen v1.2
scale pilot.  It reads the pilot inputs without mutating that namespace,
appends a path-only provenance adapter to the frozen prompt-1.7 input, captures
one renderer response per chapter, resolves path IDs deterministically, and
then invokes the existing validator, scorer, and Gate v2.1.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_IMPLEMENTATION,
    READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
    response_ancestry_audit,
)
from bhf_agent.chapter_commentary.reader_provenance_binding import (
    READER_PROVENANCE_BINDING_IMPLEMENTATION,
    READER_PROVENANCE_BINDING_VERSION,
    ProvenanceBindingError,
    add_provenance_binding_to_prompt,
    audit_provenance_binding,
    build_provenance_binding,
    normalize_renderer_payload,
)
from framework.commentary.production.models import (
    ArtifactCollisionError,
    canonical_json,
    sha256_bytes,
    sha256_json,
    slug,
    write_immutable,
)
from framework.commentary.production.inputs import prepare_chapter
from tools import commentary_renderer_selection_breadth_diagnostic as validator
from tools import commentary_v12_scale_pilot as scale_pilot


ARTIFACT_VERSION = "commentary-v1.2-reader-provenance-binding-v1"
PACKET_VERSION = f"{ARTIFACT_VERSION}-packet-v1"
SOURCE_NAMESPACE = (
    ".bhf-data/bhf-commentary-candidates/"
    "commentary-v1.2-scale-pilot-922472547555015a3ced"
)
SOURCE_ROOT = ROOT / SOURCE_NAMESPACE
REFERENCES = ("Romans 3", "Joshua 10", "Leviticus 1", "Genesis 5")
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
PROMPT_VERSION = "1.7"
CODEX = Path("/home/johnwalker/.local/bin/codex")
NEW_HARD_PROVENANCE_CODES = frozenset(
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
    """The frozen source or four-case replication is incomplete or inconsistent."""


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


def _source_row(reference: str) -> dict[str, Any]:
    manifest = _read(SOURCE_ROOT / "manifest.json")
    _verify_identity(manifest, "manifest_identity", "source scale-pilot manifest")
    rows = {row["reference"]: row for row in manifest.get("chapters", [])}
    try:
        return rows[reference]
    except KeyError as exc:
        raise DiagnosticError(f"source scale pilot does not contain {reference}") from exc


def _source_paths(row: dict[str, Any]) -> dict[str, Path]:
    stem = f"{row['ordinal']:03d}_{row['slug']}"
    batch_root = SOURCE_ROOT / f"batch-{int(row['batch']):03d}"
    return {
        "envelope": SOURCE_ROOT / "ancestry-envelopes" / f"{row['slug']}.json",
        "envelope_audit": SOURCE_ROOT / "ancestry-envelope-audits" / f"{row['slug']}.json",
        "system_prompt": batch_root / "renderer-input" / stem / "system_prompt.txt",
        "user_prompt": batch_root / "renderer-input" / stem / "user_prompt.txt",
        "raw_response": batch_root / "responses/raw" / row["response_filename"],
        "validation": batch_root / "validation" / row["response_filename"],
    }


def _record(reference: str) -> dict[str, Any]:
    row = _source_row(reference)
    paths = _source_paths(row)
    envelope = _read(paths["envelope"])
    envelope_audit = _read(paths["envelope_audit"])
    if envelope_audit.get("valid") is not True:
        raise DiagnosticError(f"source ancestry envelope is not valid for {reference}")
    if envelope.get("envelope_hash") != row.get("ancestry_envelope_hash"):
        raise DiagnosticError(f"source ancestry envelope hash changed for {reference}")
    source_user_prompt = paths["user_prompt"].read_text(encoding="utf-8")
    source_system_prompt = paths["system_prompt"].read_text(encoding="utf-8")
    if sha256_bytes(source_user_prompt.encode("utf-8")) != row["candidate_input_sha256"]:
        raise DiagnosticError(f"source prompt identity changed for {reference}")
    if sha256_bytes(source_system_prompt.encode("utf-8")) != row["system_prompt_sha256"]:
        raise DiagnosticError(f"source system prompt identity changed for {reference}")
    binding = build_provenance_binding(envelope)
    binding_audit = audit_provenance_binding(binding, envelope)
    if not binding_audit["valid"]:
        raise DiagnosticError(f"provenance binding failed its own audit for {reference}")
    candidate_prompt = add_provenance_binding_to_prompt(
        source_user_prompt, envelope, binding
    )
    if "1.8" in candidate_prompt or "1.8" in source_system_prompt:
        raise DiagnosticError("prompt 1.8 content entered the binding diagnostic")
    raw_response = paths["raw_response"].read_bytes()
    original_validation = _read(paths["validation"])
    prepared = prepare_chapter(row["book"], int(row["chapter"]))
    if prepared.bundle.evidence_hash != row["evidence_hash"]:
        raise DiagnosticError(f"source evidence identity changed for {reference}")
    if prepared.synthesis.synthesis_hash != row["synthesis_hash"]:
        raise DiagnosticError(f"source synthesis identity changed for {reference}")
    if prepared.row["input_identity"]["packet_id"] != row["source_packet_id"]:
        raise DiagnosticError(f"source packet identity changed for {reference}")
    if prepared.row["input_identity"]["packet_hash"] != row["source_packet_hash"]:
        raise DiagnosticError(f"source packet hash changed for {reference}")
    return {
        "reference": reference,
        "row": row,
        "paths": paths,
        "envelope": envelope,
        "envelope_audit": envelope_audit,
        "binding": binding,
        "binding_audit": binding_audit,
        "source_user_prompt": source_user_prompt,
        "source_system_prompt": source_system_prompt,
        "candidate_prompt": candidate_prompt,
        "source_failed_response_sha256": sha256_bytes(raw_response),
        "source_failed_validation": original_validation,
        "prepared": prepared,
    }


def _context(repo_root: Path = ROOT) -> dict[str, Any]:
    source_manifest = _read(repo_root / SOURCE_NAMESPACE / "manifest.json")
    _verify_identity(source_manifest, "manifest_identity", "source scale-pilot manifest")
    records = [_record(reference) for reference in REFERENCES]
    public_rows = []
    for ordinal, record in enumerate(records, 1):
        row = record["row"]
        public_rows.append(
            {
                "ordinal": ordinal,
                "reference": row["reference"],
                "book": row["book"],
                "chapter": row["chapter"],
                "slug": row["slug"],
                "source_batch": row["batch"],
                "renderer": RENDERER,
                "renderer_effort": RENDERER_EFFORT,
                "prompt_version": PROMPT_VERSION,
                "commentary_schema_version": "1.2",
                "projection_version": source_manifest["projection_version"],
                "projection_hash": row["projection_hash"],
                "ancestry_envelope_version": source_manifest["ancestry_envelope_version"],
                "ancestry_envelope_hash": row["ancestry_envelope_hash"],
                "provenance_binding_version": READER_PROVENANCE_BINDING_VERSION,
                "provenance_binding_hash": record["binding"]["binding_hash"],
                "provenance_path_count": len(record["binding"]["paths"]),
                "evidence_hash": row["evidence_hash"],
                "synthesis_hash": row["synthesis_hash"],
                "source_packet_id": row["source_packet_id"],
                "source_packet_hash": row["source_packet_hash"],
                "source_system_prompt_sha256": sha256_bytes(record["source_system_prompt"].encode("utf-8")),
                "source_user_prompt_sha256": sha256_bytes(record["source_user_prompt"].encode("utf-8")),
                "candidate_input_sha256": sha256_bytes(record["candidate_prompt"].encode("utf-8")),
                "source_failed_response_sha256": record["source_failed_response_sha256"],
                "response_filename": f"{ordinal:03d}_{slug(row['book'], row['chapter'])}.json",
            }
        )
    base = {
        "artifact_version": ARTIFACT_VERSION,
        "source_scale_pilot": {
            "namespace": SOURCE_NAMESPACE,
            "manifest_identity": source_manifest["manifest_identity"],
            "source_head": source_manifest["source_head"],
            "source_branch": source_manifest["source_branch"],
            "source_result": "SCALE_PILOT_NOT_READY",
        },
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "chapter_count": len(public_rows),
        "one_generation_per_chapter": True,
        "retries": 0,
        "fresh_no_retry_replication": True,
        "contracts": {
            "prompt": PROMPT_VERSION,
            "projection": source_manifest["projection_version"],
            "ancestry_envelope": source_manifest["ancestry_envelope_version"],
            "provenance_binding": READER_PROVENANCE_BINDING_VERSION,
            "scoring": source_manifest["frozen_scoring_contracts"],
            "validator_behavior": "existing-validator-unchanged",
            "scorer_behavior": "existing-scorer-unchanged",
        },
        "chapters": public_rows,
    }
    seed = sha256_json(base)
    manifest = {
        **base,
        "namespace": f".bhf-data/bhf-commentary-candidates/reader-provenance-binding-v1-{seed[:20]}",
        "immutable_id": seed[:20],
        "manifest_identity": sha256_json({**base, "namespace": f".bhf-data/bhf-commentary-candidates/reader-provenance-binding-v1-{seed[:20]}", "immutable_id": seed[:20]}),
    }
    return {
        "source_manifest": source_manifest,
        "manifest": manifest,
        "records": records,
        "root": repo_root / manifest["namespace"],
    }


def _verify_manifest(manifest: dict[str, Any]) -> None:
    _verify_identity(manifest, "manifest_identity", "binding diagnostic manifest")
    if manifest.get("artifact_version") != ARTIFACT_VERSION:
        raise DiagnosticError("unsupported provenance binding artifact version")
    if manifest.get("chapter_count") != 4:
        raise DiagnosticError("binding diagnostic must contain exactly four chapters")
    if [row.get("reference") for row in manifest.get("chapters", [])] != list(REFERENCES):
        raise DiagnosticError("binding diagnostic chapter order changed")
    if manifest.get("retries") != 0 or not manifest.get("one_generation_per_chapter"):
        raise DiagnosticError("binding diagnostic retry policy changed")


def prepare(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = _context(repo_root)
    root = context["root"]
    manifest = context["manifest"]
    _write_json(root / "manifest.json", manifest)
    _write_json(
        root / "source/scale-pilot-identity.json",
        {
            **manifest["source_scale_pilot"],
            "source_manifest_sha256": sha256_bytes(
                (repo_root / SOURCE_NAMESPACE / "manifest.json").read_bytes()
            ),
        },
    )
    _write_json(
        root / "source/failed-response-hashes.json",
        {
            "artifact_version": f"{ARTIFACT_VERSION}-source-failures",
            "chapters": {
                record["reference"]: {
                    "response_sha256": record["source_failed_response_sha256"],
                    "validation": record["source_failed_validation"],
                }
                for record in context["records"]
            },
        },
    )
    _write_json(
        root / "contract-identities.json",
        {
            "artifact_version": f"{ARTIFACT_VERSION}-contracts",
            "prompt_version": PROMPT_VERSION,
            "projection_version": manifest["contracts"]["projection"],
            "ancestry_envelope_version": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
            "provenance_binding_version": READER_PROVENANCE_BINDING_VERSION,
            "source_hashes": {
                "prompt": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/prompts.py").read_bytes()),
                "projection": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/reader_level_projection.py").read_bytes()),
                "ancestry_envelope": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/reader_idea_ancestry_envelope.py").read_bytes()),
                "provenance_binding": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/reader_provenance_binding.py").read_bytes()),
                "validator": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/validation.py").read_bytes()),
                "scorer": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/richness_clusters.py").read_bytes()),
            },
            "validator_behavior": "existing-validator-unchanged",
            "scorer_behavior": "existing-scorer-unchanged",
        },
    )
    for record, public in zip(context["records"], manifest["chapters"], strict=True):
        stem = Path(public["response_filename"]).stem
        _write_json(root / "binding" / f"{public['slug']}.json", record["binding"])
        _write_json(root / "binding-audits" / f"{public['slug']}.json", record["binding_audit"])
        _write_text(root / "renderer-input" / stem / "system_prompt.txt", record["source_system_prompt"])
        _write_text(root / "renderer-input" / stem / "user_prompt.txt", record["candidate_prompt"])
        _write_json(
            root / "renderer-input" / stem / "metadata.json",
            {
                "artifact_version": f"{ARTIFACT_VERSION}-renderer-input",
                **public,
                "binding_implementation": READER_PROVENANCE_BINDING_IMPLEMENTATION,
                "source_prompt_1_7_unchanged": True,
            },
        )
    return {
        "status": "PREPARED",
        "namespace": manifest["namespace"],
        "chapter_count": 4,
        "provenance_binding_version": READER_PROVENANCE_BINDING_VERSION,
        "provenance_binding_hashes": {
            row["reference"]: row["provenance_binding_hash"]
            for row in manifest["chapters"]
        },
    }


def render(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = _context(repo_root)
    root = context["root"]
    manifest = _read(root / "manifest.json")
    _verify_manifest(manifest)
    if manifest != context["manifest"]:
        raise DiagnosticError("frozen binding inputs changed before rendering")
    generated = []
    for public in manifest["chapters"]:
        response_path = root / "responses/raw" / public["response_filename"]
        if response_path.exists():
            raise DiagnosticError(
                f"a response already exists for {public['reference']}; no retry is permitted"
            )
        input_root = root / "renderer-input" / Path(public["response_filename"]).stem
        system_prompt = (input_root / "system_prompt.txt").read_text(encoding="utf-8")
        user_prompt = (input_root / "user_prompt.txt").read_text(encoding="utf-8")
        exchange = (
            "You are the selected GPT-5.6 Sol prose renderer at medium effort. "
            "Do not call tools, inspect files, browse, or add explanation. Treat the exact "
            "SYSTEM PROMPT and USER PROMPT below as the complete generation contract. "
            "Return the requested raw JSON object only, with no Markdown fence or preamble.\n\n"
            "SYSTEM PROMPT\n" + system_prompt + "\n\nUSER PROMPT\n" + user_prompt
        )
        with tempfile.TemporaryDirectory(prefix="bhf-v12-binding-render-") as temp_dir:
            output = Path(temp_dir) / "response.txt"
            completed = subprocess.run(
                [
                    str(CODEX),
                    "exec",
                    "--ephemeral",
                    "--ignore-user-config",
                    "-m",
                    RENDERER,
                    "-c",
                    'model_reasoning_effort="medium"',
                    "-s",
                    "read-only",
                    "-C",
                    temp_dir,
                    "--skip-git-repo-check",
                    "--output-last-message",
                    str(output),
                    "-",
                ],
                input=exchange,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=False,
            )
            if not output.is_file():
                raise DiagnosticError(
                    f"renderer produced no bytes for {public['reference']} (exit {completed.returncode}): "
                    f"{completed.stderr[-1000:]}"
                )
            raw = output.read_bytes()
        write_immutable(response_path, raw)
        generated.append(
            {
                "reference": public["reference"],
                "response_filename": public["response_filename"],
                "response_sha256": sha256_bytes(raw),
                "renderer_exit_code": completed.returncode,
                "generation_count": 1,
                "retry_count": 0,
                "syntactically_valid_json": _valid_json(raw),
            }
        )
        print(f"generated {public['reference']}", flush=True)
    result = {
        "artifact_version": f"{ARTIFACT_VERSION}-generation",
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "one_generation_per_chapter": True,
        "retries": 0,
        "generated_count": len(generated),
        "chapters": generated,
    }
    _write_json(root / "generation.json", result)
    return result


def _evaluate_one(record: dict[str, Any], public: dict[str, Any], raw: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    binding = record["binding"]
    envelope = record["envelope"]
    try:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ProvenanceBindingError("MALFORMED_PROVENANCE_REFERENCE", "renderer response is not an object")
        normalized, binding_metadata = normalize_renderer_payload(payload, binding)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        payload = {}
        normalized = None
        binding_metadata = {"artifact_version": READER_PROVENANCE_BINDING_VERSION, "blocks": []}
        binding_error = ProvenanceBindingError("MALFORMED_PROVENANCE_REFERENCE", str(exc))
    except ProvenanceBindingError as exc:
        normalized = None
        binding_metadata = {"artifact_version": READER_PROVENANCE_BINDING_VERSION, "blocks": []}
        binding_error = exc
    else:
        binding_error = None

    row_for_validator = {
        "reference": public["reference"],
        "book": public["book"],
        "chapter": public["chapter"],
        "packet_id": public["source_packet_id"],
        "packet_hash": public["source_packet_hash"],
    }
    if binding_error is not None:
        result = {
            "reference": public["reference"],
            "renderer_prompt_version": PROMPT_VERSION,
            "validation_status": "rejected",
            "structural_result": "REJECTED",
            "rejection_codes": [binding_error.code],
            "weighted_coverage": None,
            "core_coverage": None,
            "eligible_idea_utilization": None,
            "category_coverage": None,
            "dump_severity": None,
            "quality_gate_outcome": None,
            "gate_v2_1": None,
            "validation_errors": [str(binding_error)],
        }
        ancestry = {
            "valid": False,
            "ancestry_mismatch_count": 0,
            "block_count": 0,
            "blocks": [],
        }
        normalized = {}
        parsed = {
            "artifact_version": f"{ARTIFACT_VERSION}-parsed",
            "parse_status": "PROVENANCE_BINDING_REJECTED",
            "raw_renderer_payload": payload,
            "normalized_renderer_payload": normalized,
            "provenance_binding": binding_metadata,
            "provenance_binding_error": str(binding_error),
        }
    else:
        normalized_bytes = (canonical_json(normalized) + "\n").encode("utf-8")
        result, parsed = validator._evaluate_one(
            row_for_validator, normalized_bytes, record["prepared"]
        )
        ancestry = response_ancestry_audit(normalized, envelope)
        parsed["raw_renderer_payload"] = payload
        parsed["normalized_renderer_payload"] = normalized
        parsed["provenance_binding"] = binding_metadata
        parsed["raw_response_sha256"] = sha256_bytes(raw)
        parsed["normalized_response_sha256"] = sha256_bytes(normalized_bytes)

    hard_codes = sorted(
        set(result.get("rejection_codes", []))
        & (set(scale_pilot.HARD_PROVENANCE_CODES) | set(NEW_HARD_PROVENANCE_CODES))
    )
    if binding_error is not None:
        provenance_valid = False
    else:
        provenance_valid = True
    output_payload = normalized if isinstance(normalized, dict) else {}
    represented = scale_pilot._representation(envelope, output_payload)
    qualitative = scale_pilot._qualitative(output_payload, result)
    row = {
        "reference": public["reference"],
        "structural_validity": result.get("structural_result") == "ACCEPTED",
        "structural_status": result.get("structural_result"),
        "provenance_reference_validity": provenance_valid,
        "hard_provenance_errors": hard_codes,
        "ancestry_mismatch_count": ancestry["ancestry_mismatch_count"],
        "weighted_coverage": result.get("weighted_coverage"),
        "core_coverage": result.get("core_coverage"),
        "eligible_idea_utilization": result.get("eligible_idea_utilization"),
        "category_coverage": result.get("category_coverage"),
        "dump_severity": result.get("dump_severity"),
        "gate_result": result.get("quality_gate_outcome"),
        "prose_word_count": len(scale_pilot._prose(output_payload).split()),
        "projected_concepts_represented": represented["represented_count"],
        "projected_idea_count": represented["projected_idea_count"],
        "projected_concept_representation": represented,
        "readability_result": qualitative["readability"],
        "checklist_behavior": qualitative["checklist_behavior"],
        "qualitative_review": qualitative,
        "response_sha256": sha256_bytes(raw),
        "rejection_codes": result.get("rejection_codes", []),
        "ancestry_validation": ancestry,
        "binding_metadata": binding_metadata,
    }
    row["final_chapter_classification"] = scale_pilot._classification(row)
    parsed.update(
        {
            "reference": public["reference"],
            "raw_response_sha256": sha256_bytes(raw),
            "ancestry_validation": ancestry,
        }
    )
    return row, parsed


def evaluate(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = _context(repo_root)
    root = context["root"]
    manifest = _read(root / "manifest.json")
    _verify_manifest(manifest)
    if manifest != context["manifest"]:
        raise DiagnosticError("frozen binding inputs changed before evaluation")
    generation = _read(root / "generation.json")
    if generation.get("generated_count") != 4 or generation.get("retries") != 0:
        raise DiagnosticError("exactly four no-retry generations are required")
    results = []
    comparisons = []
    original_by_ref = {
        record["reference"]: record["source_failed_validation"]
        for record in context["records"]
    }
    for record, public in zip(context["records"], manifest["chapters"], strict=True):
        raw_path = root / "responses/raw" / public["response_filename"]
        if not raw_path.is_file():
            raise DiagnosticError(f"fresh response missing for {public['reference']}")
        raw = raw_path.read_bytes()
        generation_row = next(
            item for item in generation["chapters"] if item["reference"] == public["reference"]
        )
        if generation_row["response_sha256"] != sha256_bytes(raw) or generation_row["generation_count"] != 1:
            raise DiagnosticError(f"immutable generation receipt mismatch for {public['reference']}")
        result, parsed = _evaluate_one(record, public, raw)
        stem = Path(public["response_filename"]).stem
        _write_json(root / "parsed" / f"{stem}.json", parsed)
        _write_json(root / "normalized" / f"{stem}.json", parsed.get("normalized_renderer_payload", {}))
        _write_json(root / "validation" / f"{stem}.json", result)
        results.append(result)
        old = original_by_ref[public["reference"]]
        comparisons.append(
            {
                "reference": public["reference"],
                "source_scale_pilot": {
                    "response_sha256": record["source_failed_response_sha256"],
                    "structural_validity": old.get("structural_validity"),
                    "ancestry_mismatch_count": old.get("ancestry_mismatch_count"),
                    "hard_provenance_errors": old.get("hard_provenance_errors"),
                    "weighted_coverage": old.get("weighted_coverage"),
                    "core_coverage": old.get("core_coverage"),
                    "eligible_idea_utilization": old.get("eligible_idea_utilization"),
                    "category_coverage": old.get("category_coverage"),
                    "dump_severity": old.get("dump_severity"),
                    "gate_result": old.get("gate_result"),
                    "readability": old.get("readability_result"),
                },
                "fresh_binding_replication": {
                    "response_sha256": result["response_sha256"],
                    "structural_validity": result["structural_validity"],
                    "provenance_reference_validity": result["provenance_reference_validity"],
                    "ancestry_mismatch_count": result["ancestry_mismatch_count"],
                    "hard_provenance_errors": result["hard_provenance_errors"],
                    "weighted_coverage": result["weighted_coverage"],
                    "core_coverage": result["core_coverage"],
                    "eligible_idea_utilization": result["eligible_idea_utilization"],
                    "category_coverage": result["category_coverage"],
                    "dump_severity": result["dump_severity"],
                    "gate_result": result["gate_result"],
                    "readability": result["readability_result"],
                },
            }
        )

    def rate(key: str, expected: Any) -> float:
        return round(100 * sum(row.get(key) == expected for row in results) / len(results), 2)

    weighted = [row["weighted_coverage"] or 0.0 for row in results]
    eligible = [row["eligible_idea_utilization"] or 0.0 for row in results]
    aggregate = {
        "chapter_count": len(results),
        "structurally_valid": sum(row["structural_validity"] for row in results),
        "provenance_reference_valid": sum(row["provenance_reference_validity"] for row in results),
        "ancestry_safe": sum(row["ancestry_mismatch_count"] == 0 for row in results),
        "ancestry_safe_rate": rate("ancestry_mismatch_count", 0),
        "ancestry_mismatch_count": sum(row["ancestry_mismatch_count"] for row in results),
        "hard_provenance_error_count": sum(bool(row["hard_provenance_errors"]) for row in results),
        "hard_provenance_errors": sorted({code for row in results for code in row["hard_provenance_errors"]}),
        "weighted_coverage_mean": round(sum(weighted) / len(weighted), 4),
        "weighted_coverage_median": sorted(weighted)[len(weighted) // 2],
        "core_coverage_rate": rate("core_coverage", 1.0),
        "eligible_utilization_mean": round(sum(eligible) / len(eligible), 4),
        "category_coverage_rate": rate("category_coverage", 1.0),
        "high_dump_count": sum(row["dump_severity"] == "HIGH" for row in results),
        "gate_pass_rate": rate("gate_result", "PASS"),
        "readability_pass_rate": rate("readability_result", "PASS"),
        "classification_distribution": {
            key: sum(row["final_chapter_classification"] == key for row in results)
            for key in sorted({row["final_chapter_classification"] for row in results})
        },
    }
    replication_pass = (
        aggregate["structurally_valid"] == 4
        and aggregate["provenance_reference_valid"] == 4
        and aggregate["ancestry_mismatch_count"] == 0
        and aggregate["hard_provenance_error_count"] == 0
        and aggregate["high_dump_count"] == 0
        and aggregate["readability_pass_rate"] == 100.0
    )
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-evaluation",
        "namespace": manifest["namespace"],
        "source_scale_pilot": manifest["source_scale_pilot"],
        "binding_version": READER_PROVENANCE_BINDING_VERSION,
        "contracts": manifest["contracts"],
        "chapters": results,
        "aggregate": aggregate,
        "comparison_report": comparisons,
        "replication_result": "REPLICATION_PASS" if replication_pass else "REPLICATION_NOT_READY",
        "galatians_3": "UNRESOLVED_SECONDARY_CORE_OMISSION_NOT_ADDRESSED",
        "next_recommendation": (
            "Resume or cleanly restart the frozen 75-chapter scale pilot in a new immutable namespace under this binding contract; do not generate the remaining chapters in this diagnostic."
            if replication_pass
            else "Do not resume the scale pilot. Determine whether the remaining failure is path selection, presentation ambiguity, normalization, or another provenance boundary defect; do not weaken ancestry validation."
        ),
    }
    _write_json(root / "aggregate-metrics.json", aggregate)
    _write_json(root / "comparison-report.json", {"artifact_version": f"{ARTIFACT_VERSION}-comparison", "comparisons": comparisons})
    _write_json(root / "evaluation.json", report)
    return report


def checksums(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = _context(repo_root)
    root = context["root"]
    target = root / "checksums.json"
    files = sorted(path for path in root.rglob("*") if path.is_file() and path != target)
    value = {
        "artifact_version": f"{ARTIFACT_VERSION}-checksums",
        "files": {
            str(path.relative_to(root)): sha256_bytes(path.read_bytes()) for path in files
        },
    }
    _write_json(target, value)
    return {"status": "CHECKSUMMED", "file_count": len(files), "path": str(target)}


def status(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = _context(repo_root)
    root = context["root"]
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return {"status": "NOT_PREPARED", "namespace": str(root)}
    manifest = _read(manifest_path)
    _verify_manifest(manifest)
    generation_path = root / "generation.json"
    evaluation_path = root / "evaluation.json"
    return {
        "status": _read(evaluation_path).get("replication_result") if evaluation_path.is_file() else "GENERATED_AWAITING_EVALUATION" if generation_path.is_file() else "PREPARED",
        "namespace": manifest["namespace"],
        "chapter_count": 4,
        "binding_version": READER_PROVENANCE_BINDING_VERSION,
    }


def _valid_json(raw: bytes) -> bool:
    try:
        return isinstance(json.loads(raw.decode("utf-8")), dict)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    sub.add_parser("render")
    sub.add_parser("evaluate")
    sub.add_parser("checksums")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            value = prepare()
        elif args.command == "render":
            value = render()
        elif args.command == "evaluate":
            value = evaluate()
        elif args.command == "checksums":
            value = checksums()
        else:
            value = status()
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except (DiagnosticError, ArtifactCollisionError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
