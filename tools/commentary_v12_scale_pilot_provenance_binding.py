#!/usr/bin/env python3
"""Run the frozen 75-chapter v1.2 pilot with deterministic provenance binding.

The source pilot is read-only.  This harness reuses its exact corpus, batches,
prompt-1.7 inputs, reader projections, ancestry envelopes, packet identities,
and scoring contract, then appends reader-provenance-binding-v1.  Raw renderer
responses are captured once and normalized deterministically before validation.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    audit_ancestry_envelope,
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
from framework.commentary.production.inputs import prepare_chapter
from framework.commentary.production.models import (
    ArtifactCollisionError,
    canonical_json,
    sha256_bytes,
    sha256_json,
    write_immutable,
)
from tools import commentary_renderer_selection_breadth_diagnostic as validator
from tools import commentary_v12_scale_pilot as source_pilot


SOURCE_NAMESPACE = (
    ".bhf-data/bhf-commentary-candidates/"
    "commentary-v1.2-scale-pilot-922472547555015a3ced"
)
SOURCE_ROOT = ROOT / SOURCE_NAMESPACE
ARTIFACT_VERSION = "commentary-v1.2-scale-pilot-provenance-binding-v1"
STARTING_SHA = "6955ac414cea9a50062d2ec9e39741460a97bc31"
PROMPT_VERSION = "1.7"
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
TARGET_COUNT = 75
BATCH_SIZES = (13, 13, 13, 12, 12, 12)
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
FAILURE_CLASSES = frozenset(
    {
        "RICHNESS_SHORTFALL",
        "CORE_OMISSION",
        "CATEGORY_SHORTFALL",
        "STRUCTURAL_FAILURE",
        "PROVENANCE_FAILURE",
        "DUMP_FAILURE",
        "READABILITY_REGRESSION",
    }
)


class PilotError(RuntimeError):
    """A frozen identity, generation receipt, or pilot invariant disagrees."""


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PilotError(f"invalid JSON artifact {path}: {exc}") from exc


def _write_json(path: Path, value: Any) -> str:
    return write_immutable(path, (canonical_json(value) + "\n").encode("utf-8"))


def _write_text(path: Path, value: str) -> str:
    return write_immutable(path, value.encode("utf-8"))


def _verify_identity(value: dict[str, Any], key: str, label: str) -> None:
    if value.get(key) != sha256_json({k: v for k, v in value.items() if k != key}):
        raise PilotError(f"{label} identity mismatch")


def _source_paths(row: dict[str, Any]) -> dict[str, Path]:
    stem = f"{row['ordinal']:03d}_{row['slug']}"
    batch_root = SOURCE_ROOT / f"batch-{int(row['batch']):03d}"
    return {
        "projection": SOURCE_ROOT / "projections" / f"{row['slug']}.json",
        "envelope": SOURCE_ROOT / "ancestry-envelopes" / f"{row['slug']}.json",
        "envelope_audit": SOURCE_ROOT / "ancestry-envelope-audits" / f"{row['slug']}.json",
        "system_prompt": batch_root / "renderer-input" / stem / "system_prompt.txt",
        "user_prompt": batch_root / "renderer-input" / stem / "user_prompt.txt",
    }


def _record(row: dict[str, Any]) -> dict[str, Any]:
    paths = _source_paths(row)
    projection = _read(paths["projection"])
    envelope = _read(paths["envelope"])
    envelope_audit = _read(paths["envelope_audit"])
    if projection.get("projection_hash") != row["projection_hash"]:
        raise PilotError(f"source projection identity changed for {row['reference']}")
    if envelope.get("envelope_hash") != row["ancestry_envelope_hash"]:
        raise PilotError(f"source ancestry envelope changed for {row['reference']}")
    if envelope_audit.get("valid") is not True:
        raise PilotError(f"source ancestry envelope is invalid for {row['reference']}")
    prepared = prepare_chapter(row["book"], int(row["chapter"]))
    if prepared.bundle.evidence_hash != row["evidence_hash"]:
        raise PilotError(f"source evidence identity changed for {row['reference']}")
    if prepared.synthesis.synthesis_hash != row["synthesis_hash"]:
        raise PilotError(f"source synthesis identity changed for {row['reference']}")
    identity = prepared.row["input_identity"]
    if identity["packet_id"] != row["source_packet_id"] or identity["packet_hash"] != row["source_packet_hash"]:
        raise PilotError(f"source packet identity changed for {row['reference']}")
    if not audit_ancestry_envelope(envelope, projection, prepared.synthesis)["valid"]:
        raise PilotError(f"source ancestry envelope no longer rebuilds for {row['reference']}")
    system_prompt = paths["system_prompt"].read_text(encoding="utf-8")
    source_user_prompt = paths["user_prompt"].read_text(encoding="utf-8")
    if sha256_bytes(system_prompt.encode()) != row["system_prompt_sha256"]:
        raise PilotError(f"source system prompt changed for {row['reference']}")
    if sha256_bytes(source_user_prompt.encode()) != row["candidate_input_sha256"]:
        raise PilotError(f"source candidate prompt changed for {row['reference']}")
    binding = build_provenance_binding(envelope)
    binding_audit = audit_provenance_binding(binding, envelope)
    if not binding_audit["valid"]:
        raise PilotError(f"provenance binding invalid for {row['reference']}")
    candidate_prompt = add_provenance_binding_to_prompt(source_user_prompt, envelope, binding)
    if "1.8" in candidate_prompt or "1.8" in system_prompt:
        raise PilotError("prompt 1.8 content entered the pilot")
    return {
        "row": row,
        "prepared": prepared,
        "projection": projection,
        "envelope": envelope,
        "envelope_audit": envelope_audit,
        "binding": binding,
        "binding_audit": binding_audit,
        "system_prompt": system_prompt,
        "source_user_prompt": source_user_prompt,
        "candidate_prompt": candidate_prompt,
    }


def build_context(repo_root: Path = ROOT) -> dict[str, Any]:
    source_root = repo_root / SOURCE_NAMESPACE
    source_manifest = _read(source_root / "manifest.json")
    _verify_identity(source_manifest, "manifest_identity", "source pilot manifest")
    rows = source_manifest.get("chapters", [])
    if len(rows) != TARGET_COUNT or len({row["reference"] for row in rows}) != TARGET_COUNT:
        raise PilotError("source pilot is not the exact unique 75-chapter population")
    if [sum(int(row["batch"]) == batch for row in rows) for batch in range(1, 7)] != list(BATCH_SIZES):
        raise PilotError("source pilot batch membership changed")
    records = [_record(dict(row)) for row in rows]
    source_corpus_bytes = (source_root / "frozen-corpus.json").read_bytes()
    source_references_hash = sha256_bytes("\n".join(row["reference"] for row in rows).encode())
    contract_hashes = {
        "prompt_source_sha256": source_manifest["contract_hashes"]["prompt_source_sha256"],
        "projection_source_sha256": source_manifest["contract_hashes"]["projection_source_sha256"],
        "ancestry_envelope_source_sha256": source_manifest["contract_hashes"]["ancestry_envelope_source_sha256"],
        "provenance_binding_source_sha256": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/reader_provenance_binding.py").read_bytes()),
        "validator_source_sha256": source_manifest["contract_hashes"]["validator_source_sha256"],
        "scorer_source_sha256": source_manifest["contract_hashes"]["scorer_source_sha256"],
    }
    public = []
    for record in records:
        row = record["row"]
        public.append(
            {
                **row,
                "source_candidate_input_sha256": row["candidate_input_sha256"],
                "candidate_input_sha256": sha256_bytes(record["candidate_prompt"].encode()),
                "provenance_binding_version": READER_PROVENANCE_BINDING_VERSION,
                "provenance_binding_hash": record["binding"]["binding_hash"],
                "provenance_path_count": len(record["binding"]["paths"]),
            }
        )
    base = {
        "artifact_version": f"{ARTIFACT_VERSION}-manifest",
        "starting_sha": STARTING_SHA,
        "source_pilot": {
            "namespace": SOURCE_NAMESPACE,
            "manifest_identity": source_manifest["manifest_identity"],
            "frozen_corpus_sha256": sha256_bytes(source_corpus_bytes),
            "ordered_references_sha256": source_references_hash,
            "result": "SCALE_PILOT_NOT_READY",
        },
        "exact_source_corpus_reused": True,
        "chapter_count": TARGET_COUNT,
        "batch_sizes": list(BATCH_SIZES),
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "runtime_self_attestation": False,
        "one_generation_per_chapter": True,
        "retries": 0,
        "prompt_version": PROMPT_VERSION,
        "projection_version": source_manifest["projection_version"],
        "projection_implementation_identity": source_manifest["projection_implementation_identity"],
        "ancestry_envelope_version": source_manifest["ancestry_envelope_version"],
        "ancestry_envelope_implementation_identity": source_manifest["ancestry_envelope_implementation_identity"],
        "provenance_binding_version": READER_PROVENANCE_BINDING_VERSION,
        "provenance_binding_implementation_identity": READER_PROVENANCE_BINDING_IMPLEMENTATION,
        "frozen_scoring_contracts": source_manifest["frozen_scoring_contracts"],
        "contract_hashes": contract_hashes,
        "seen_definition": source_manifest["seen_definition"],
        "seen_count": source_manifest["seen_count"],
        "unseen_count": source_manifest["unseen_count"],
        "unseen_percentage": source_manifest["unseen_percentage"],
        "chapters": public,
    }
    seed = sha256_json(base)
    namespace = (
        ".bhf-data/bhf-commentary-candidates/"
        f"commentary-v1.2-scale-pilot-provenance-binding-v1-{seed[:20]}"
    )
    manifest = {**base, "namespace": namespace, "immutable_id": seed[:20]}
    manifest["manifest_identity"] = sha256_json(manifest)
    return {
        "source_manifest": source_manifest,
        "manifest": manifest,
        "records": records,
        "root": repo_root / namespace,
    }


def prepare(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    _write_json(root / "manifest.json", manifest)
    _write_json(
        root / "frozen-corpus.json",
        {
            "artifact_version": f"{ARTIFACT_VERSION}-corpus",
            "source_pilot": manifest["source_pilot"],
            "order_frozen": True,
            "chapters": [
                {key: row[key] for key in ("ordinal", "reference", "batch", "seen_status", "literary_stratum", "density_bucket", "density_class", "content_shape")}
                for row in manifest["chapters"]
            ],
        },
    )
    _write_json(
        root / "contract-identities.json",
        {
            "artifact_version": f"{ARTIFACT_VERSION}-contracts",
            "prompt": PROMPT_VERSION,
            "projection": manifest["projection_version"],
            "ancestry_envelope": manifest["ancestry_envelope_version"],
            "provenance_binding": READER_PROVENANCE_BINDING_VERSION,
            "scoring": manifest["frozen_scoring_contracts"],
            "source_hashes": manifest["contract_hashes"],
            "validator_behavior": "existing-validator-unchanged",
            "scorer_behavior": "existing-scorer-unchanged",
        },
    )
    for record, public in zip(context["records"], manifest["chapters"], strict=True):
        batch_root = root / f"batch-{public['batch']:03d}"
        stem = f"{public['ordinal']:03d}_{public['slug']}"
        _write_json(root / "projections" / f"{public['slug']}.json", record["projection"])
        _write_json(root / "ancestry-envelopes" / f"{public['slug']}.json", record["envelope"])
        _write_json(root / "ancestry-envelope-audits" / f"{public['slug']}.json", record["envelope_audit"])
        _write_json(root / "provenance-bindings" / f"{public['slug']}.json", record["binding"])
        _write_json(root / "provenance-binding-audits" / f"{public['slug']}.json", record["binding_audit"])
        _write_text(batch_root / "renderer-input" / stem / "system_prompt.txt", record["system_prompt"])
        _write_text(batch_root / "renderer-input" / stem / "user_prompt.txt", record["candidate_prompt"])
        _write_json(batch_root / "renderer-input" / stem / "metadata.json", {"artifact_version": f"{ARTIFACT_VERSION}-renderer-input", **public, "generation_count": 0})
    for batch in range(1, 7):
        rows = [row for row in manifest["chapters"] if row["batch"] == batch]
        _write_json(root / f"batch-{batch:03d}" / "batch-manifest.json", {"artifact_version": f"{ARTIFACT_VERSION}-batch-manifest", "batch": batch, "status": "READY_FOR_ONE_GENERATION_EACH", "contract_manifest_identity": manifest["manifest_identity"], "chapters": rows})
    return {"status": "PREPARED", "namespace": manifest["namespace"], "chapter_count": TARGET_COUNT, "batch_count": 6, "seen_count": manifest["seen_count"], "unseen_percentage": manifest["unseen_percentage"]}


def _valid_json(raw: bytes) -> bool:
    try:
        return isinstance(json.loads(raw.decode("utf-8")), dict)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False


def render_batch(batch: int, *, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    stored = _read(root / "manifest.json")
    _verify_identity(stored, "manifest_identity", "pilot manifest")
    if stored != manifest:
        raise PilotError("frozen pilot inputs changed")
    generated = []
    for index, row in enumerate((r for r in manifest["chapters"] if r["batch"] == batch), 1):
        response_path = root / f"batch-{batch:03d}" / "responses/raw" / row["response_filename"]
        if response_path.exists():
            raw = response_path.read_bytes()
            disposition = "PRESERVED_EXISTING_FIRST_RESPONSE"
            exit_code = 0
        else:
            input_root = root / f"batch-{batch:03d}" / "renderer-input" / f"{row['ordinal']:03d}_{row['slug']}"
            exchange = (
                "Render the requested commentary using only the exact generation contract below. "
                "Do not call tools, inspect files, browse, or add explanation. Return the requested "
                "raw JSON object only, with no Markdown fence or preamble.\n\nSYSTEM PROMPT\n"
                + (input_root / "system_prompt.txt").read_text(encoding="utf-8")
                + "\n\nUSER PROMPT\n"
                + (input_root / "user_prompt.txt").read_text(encoding="utf-8")
            )
            with tempfile.TemporaryDirectory(prefix="bhf-v12-binding-scale-") as temp_dir:
                output = Path(temp_dir) / "response.txt"
                completed = subprocess.run(
                    [str(CODEX), "exec", "--ephemeral", "--ignore-user-config", "-m", RENDERER, "-c", 'model_reasoning_effort="medium"', "-s", "read-only", "-C", temp_dir, "--skip-git-repo-check", "--output-last-message", str(output), "-"],
                    input=exchange,
                    text=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                if not output.is_file():
                    raise PilotError(f"renderer produced no bytes for {row['reference']} (exit {completed.returncode}): {completed.stderr[-1000:]}")
                raw = output.read_bytes()
                exit_code = completed.returncode
            try:
                write_immutable(response_path, raw)
                disposition = "GENERATED_BY_ISOLATED_EXCHANGE"
            except ArtifactCollisionError:
                raw = response_path.read_bytes()
                disposition = "PRESERVED_CONCURRENT_FIRST_RESPONSE"
        generated.append({"reference": row["reference"], "response_path": str(response_path.relative_to(repo_root)), "response_sha256": sha256_bytes(raw), "generation_count": 1, "retry_count": 0, "renderer_exit_code": exit_code, "syntactically_valid_json": _valid_json(raw), "resume_disposition": disposition})
        print(f"batch {batch}: {index}/{BATCH_SIZES[batch - 1]} {row['reference']} {disposition}", flush=True)
    result = {"artifact_version": f"{ARTIFACT_VERSION}-batch-generation", "batch": batch, "renderer": RENDERER, "renderer_effort": RENDERER_EFFORT, "runtime_self_attestation": False, "one_generation_per_chapter": True, "retries": 0, "generated_count": len(generated), "chapters": generated}
    _write_json(root / f"batch-{batch:03d}" / "batch-generation.json", result)
    return result


def _evaluate_one(record: dict[str, Any], public: dict[str, Any], raw: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ProvenanceBindingError("MALFORMED_PROVENANCE_REFERENCE", "renderer response is not an object")
        normalized, binding_metadata = normalize_renderer_payload(payload, record["binding"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        payload, normalized = {}, None
        binding_metadata = {"artifact_version": READER_PROVENANCE_BINDING_VERSION, "blocks": []}
        binding_error = ProvenanceBindingError("MALFORMED_PROVENANCE_REFERENCE", str(exc))
    except ProvenanceBindingError as exc:
        normalized = None
        binding_metadata = {"artifact_version": READER_PROVENANCE_BINDING_VERSION, "blocks": []}
        binding_error = exc
    else:
        binding_error = None
    if binding_error:
        result = {"structural_result": "REJECTED", "rejection_codes": [binding_error.code], "weighted_coverage": None, "core_coverage": None, "eligible_idea_utilization": None, "category_coverage": None, "dump_severity": None, "quality_gate_outcome": None, "validation_errors": [str(binding_error)]}
        ancestry = {"valid": False, "ancestry_mismatch_count": 0, "block_count": 0, "blocks": []}
        parsed = {"artifact_version": f"{ARTIFACT_VERSION}-parsed", "parse_status": "PROVENANCE_BINDING_REJECTED", "raw_renderer_payload": payload, "normalized_renderer_payload": {}, "provenance_binding": binding_metadata, "provenance_binding_error": str(binding_error)}
        normalized = {}
    else:
        normalized_bytes = (canonical_json(normalized) + "\n").encode()
        result, parsed = validator._evaluate_one({"reference": public["reference"], "book": public["book"], "chapter": public["chapter"], "packet_id": public["source_packet_id"], "packet_hash": public["source_packet_hash"]}, normalized_bytes, record["prepared"])
        ancestry = response_ancestry_audit(normalized, record["envelope"])
        parsed.update({"raw_renderer_payload": payload, "normalized_renderer_payload": normalized, "provenance_binding": binding_metadata, "normalized_response_sha256": sha256_bytes(normalized_bytes)})
    hard = sorted(set(result.get("rejection_codes", [])) & (set(source_pilot.HARD_PROVENANCE_CODES) | set(NEW_HARD_PROVENANCE_CODES)))
    represented = source_pilot._representation(record["envelope"], normalized)
    qualitative = source_pilot._qualitative(normalized, result)
    row = {
        **{key: public[key] for key in ("reference", "seen_status", "literary_stratum", "density_bucket", "density_class", "content_shape", "synthesis_unit_count", "eligible_cluster_count", "projected_idea_count", "provenance_path_count")},
        "structural_validity": result.get("structural_result") == "ACCEPTED",
        "structural_status": result.get("structural_result"),
        "provenance_path_validity": binding_error is None,
        "hard_provenance_errors": hard,
        "ancestry_mismatch_count": ancestry["ancestry_mismatch_count"],
        "weighted_coverage": result.get("weighted_coverage"),
        "core_coverage": result.get("core_coverage"),
        "eligible_idea_utilization": result.get("eligible_idea_utilization"),
        "category_coverage": result.get("category_coverage"),
        "dump_severity": result.get("dump_severity"),
        "gate_result": result.get("quality_gate_outcome"),
        "prose_word_count": len(source_pilot._prose(normalized).split()),
        "projected_concepts_represented": represented["represented_count"],
        "projected_concept_representation": represented,
        "readability_result": qualitative["readability"],
        "checklist_behavior": qualitative["checklist_behavior"],
        "qualitative_review": qualitative,
        "response_sha256": sha256_bytes(raw),
        "rejection_codes": result.get("rejection_codes", []),
        "ancestry_validation": ancestry,
        "binding_metadata": binding_metadata,
    }
    row["final_chapter_classification"] = _classification(row)
    parsed.update({"reference": public["reference"], "raw_response_sha256": sha256_bytes(raw), "ancestry_validation": ancestry})
    return row, parsed


def _classification(row: dict[str, Any]) -> str:
    if not row["structural_validity"]:
        return "STRUCTURAL_FAILURE"
    if not row["provenance_path_validity"] or row["hard_provenance_errors"] or row["ancestry_mismatch_count"]:
        return "PROVENANCE_FAILURE"
    if row["dump_severity"] == "HIGH":
        return "DUMP_FAILURE"
    if row["readability_result"] != "PASS" or row["checklist_behavior"] != "PASS":
        return "READABILITY_REGRESSION"
    if (row["core_coverage"] or 0) < 1.0:
        return "CORE_OMISSION"
    if (row["category_coverage"] or 0) < 1.0:
        return "CATEGORY_SHORTFALL"
    shortfall = row["gate_result"] != "PASS" or (row["weighted_coverage"] or 0) < 0.75 or (row["eligible_idea_utilization"] or 0) < 0.70
    substantial_projection = row["projected_concepts_represented"] == row["projected_idea_count"]
    if shortfall and row["gate_result"] == "PASS" and substantial_projection:
        return "SCORER_RENDERER_EDGE_CASE"
    return "RICHNESS_SHORTFALL" if shortfall else "CLEAN_PASS"


def validate_batch(batch: int, *, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    if _read(root / "manifest.json") != manifest:
        raise PilotError("frozen manifest changed before validation")
    generation = _read(root / f"batch-{batch:03d}" / "batch-generation.json")
    expected = [row for row in manifest["chapters"] if row["batch"] == batch]
    if generation.get("generated_count") != len(expected) or generation.get("retries") != 0:
        raise PilotError(f"batch {batch} generation receipt is incomplete")
    by_ref = {record["row"]["reference"]: record for record in context["records"]}
    receipt = {row["reference"]: row for row in generation["chapters"]}
    rows = []
    for public in expected:
        raw_path = root / f"batch-{batch:03d}" / "responses/raw" / public["response_filename"]
        if not raw_path.is_file():
            raise PilotError(f"response missing for {public['reference']}")
        raw = raw_path.read_bytes()
        if receipt[public["reference"]]["response_sha256"] != sha256_bytes(raw):
            raise PilotError(f"response receipt mismatch for {public['reference']}")
        row, parsed = _evaluate_one(by_ref[public["reference"]], public, raw)
        out = root / f"batch-{batch:03d}"
        _write_json(out / "parsed" / public["response_filename"], parsed)
        _write_json(out / "normalized" / public["response_filename"], parsed.get("normalized_renderer_payload", {}))
        _write_json(out / "validation" / public["response_filename"], row)
        rows.append(row)
    threshold = math.ceil(len(rows) / 3)
    catastrophic = sum(not row["structural_validity"] for row in rows) >= threshold or sum(not row["provenance_path_validity"] or bool(row["hard_provenance_errors"]) or row["ancestry_mismatch_count"] > 0 for row in rows) >= threshold
    report = {"artifact_version": f"{ARTIFACT_VERSION}-batch-validation", "batch": batch, "chapter_count": len(rows), "catastrophic_threshold": threshold, "catastrophic_stop": catastrophic, "classification_distribution": dict(sorted(Counter(row["final_chapter_classification"] for row in rows).items())), "chapters": rows}
    _write_json(root / f"batch-{batch:03d}" / "batch-validation.json", report)
    return report


def _percentile(values: Iterable[float], percentile: int) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * percentile / 100
    lower, upper = math.floor(position), math.ceil(position)
    value = ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
    return round(value, 4)


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    weighted = [row["weighted_coverage"] or 0.0 for row in rows]
    eligible = [row["eligible_idea_utilization"] or 0.0 for row in rows]
    rate = lambda predicate: round(100 * sum(predicate(row) for row in rows) / total, 2) if total else 0.0
    return {
        "chapter_count": total,
        "structurally_valid_percentage": rate(lambda r: r["structural_validity"]),
        "provenance_path_valid_percentage": rate(lambda r: r["provenance_path_validity"]),
        "hard_provenance_safe_percentage": rate(lambda r: not r["hard_provenance_errors"]),
        "ancestry_safe_percentage": rate(lambda r: r["ancestry_mismatch_count"] == 0),
        "gate_pass_percentage": rate(lambda r: r["gate_result"] == "PASS"),
        "weighted_coverage_mean": round(statistics.mean(weighted), 4),
        "weighted_coverage_median": round(statistics.median(weighted), 4),
        "weighted_coverage_percentiles": {f"P{p}": _percentile(weighted, p) for p in (10, 25, 50, 75, 90)},
        "eligible_utilization_mean": round(statistics.mean(eligible), 4),
        "eligible_utilization_median": round(statistics.median(eligible), 4),
        "core_coverage_rate": rate(lambda r: r["core_coverage"] == 1.0),
        "category_coverage_rate": rate(lambda r: r["category_coverage"] == 1.0),
        "high_dump_rate": rate(lambda r: r["dump_severity"] == "HIGH"),
        "clean_pass_rate": rate(lambda r: r["final_chapter_classification"] == "CLEAN_PASS"),
        "edge_case_rate": rate(lambda r: r["final_chapter_classification"] == "SCORER_RENDERER_EDGE_CASE"),
        "genuine_renderer_failure_rate": rate(lambda r: r["final_chapter_classification"] in FAILURE_CLASSES),
        "failure_rate": rate(lambda r: r["final_chapter_classification"] in FAILURE_CLASSES),
        "average_prose_word_count": round(statistics.mean(row["prose_word_count"] for row in rows), 1) if rows else 0.0,
        "classification_distribution": dict(sorted(Counter(row["final_chapter_classification"] for row in rows).items())),
    }


def _failure_clusters(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        cls = row["final_chapter_classification"]
        if cls == "PROVENANCE_FAILURE":
            group = "provenance/path binding"
        elif cls == "CORE_OMISSION":
            group = "core omission"
        elif cls == "READABILITY_REGRESSION":
            group = "readability"
        elif cls == "SCORER_RENDERER_EDGE_CASE":
            group = "scorer/prose semantic mismatch"
        elif cls in {"RICHNESS_SHORTFALL", "CATEGORY_SHORTFALL"}:
            group = "contextual breadth"
        elif cls == "DUMP_FAILURE":
            group = "dense chapter" if row["density_class"] == "dense" else "other"
        elif cls == "STRUCTURAL_FAILURE":
            group = "other"
        else:
            continue
        groups[group].append(row["reference"])
        if cls in FAILURE_CLASSES and row["density_class"] in {"sparse", "dense"}:
            groups[f"{row['density_class']} chapter"].append(row["reference"])
    return {key: {"count": len(set(refs)), "references": sorted(set(refs))} for key, refs in sorted(groups.items())}


def _qualitative_sample(rows: list[dict[str, Any]]) -> list[str]:
    chosen: list[str] = []
    pools = [
        sorted(rows, key=lambda r: ((r["weighted_coverage"] or 0), r["reference"]))[:4],
        sorted(rows, key=lambda r: (-(r["weighted_coverage"] or 0), r["reference"]))[:3],
        [r for r in rows if r["final_chapter_classification"] in FAILURE_CLASSES],
        [r for r in rows if r["density_class"] == "sparse" and r["seen_status"] == "unseen"],
        [r for r in rows if r["density_class"] == "medium" and r["seen_status"] == "unseen"],
        [r for r in rows if r["density_class"] == "dense" and r["seen_status"] == "unseen"],
        [r for r in rows if r["seen_status"] == "unseen"],
    ]
    for pool in pools:
        for row in pool:
            if row["reference"] not in chosen:
                chosen.append(row["reference"])
            if len(chosen) == 13:
                return chosen
    return chosen


def finalize(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    if _read(root / "manifest.json") != manifest:
        raise PilotError("frozen manifest changed before finalization")
    rows, batch_reports = [], []
    for batch in range(1, 7):
        report = _read(root / f"batch-{batch:03d}" / "batch-validation.json")
        rows.extend(report["chapters"])
        batch_reports.append({"batch": batch, "catastrophic_stop": report["catastrophic_stop"], "classification_distribution": report["classification_distribution"]})
    if len(rows) != TARGET_COUNT or len({row["reference"] for row in rows}) != TARGET_COUNT:
        raise PilotError("validated population is incomplete or duplicated")
    aggregate = _summary(rows)
    stratified = {field: {value: _summary([row for row in rows if row[field] == value]) for value in sorted({row[field] for row in rows})} for field in ("seen_status", "density_class", "literary_stratum")}
    seen, unseen = stratified["seen_status"].get("seen", {}), stratified["seen_status"].get("unseen", {})
    unseen_comparable = abs(seen.get("weighted_coverage_mean", 0) - unseen.get("weighted_coverage_mean", 0)) <= 0.10 and abs(seen.get("gate_pass_percentage", 0) - unseen.get("gate_pass_percentage", 0)) <= 5.0
    criteria = {
        "structural_at_least_98": aggregate["structurally_valid_percentage"] >= 98,
        "provenance_path_at_least_98": aggregate["provenance_path_valid_percentage"] >= 98,
        "hard_provenance_at_least_98": aggregate["hard_provenance_safe_percentage"] >= 98,
        "ancestry_at_least_98": aggregate["ancestry_safe_percentage"] >= 98,
        "core_at_least_98": aggregate["core_coverage_rate"] >= 98,
        "gate_at_least_95": aggregate["gate_pass_percentage"] >= 95,
        "high_dump_near_zero": aggregate["high_dump_rate"] <= 1.5,
        "unseen_broadly_comparable": unseen_comparable,
        "no_widespread_readability_regression": sum(row["final_chapter_classification"] == "READABILITY_REGRESSION" for row in rows) <= 2,
        "no_catastrophic_batch": not any(report["catastrophic_stop"] for report in batch_reports),
    }
    exceptions = [row for row in rows if row["final_chapter_classification"] != "CLEAN_PASS"]
    if all(criteria.values()):
        decision = "SCALE_PILOT_PASS_WITH_EDGE_CASE_MONITORING" if exceptions else "SCALE_PILOT_PASS_BULK_GENERATION_READY"
    else:
        decision = "SCALE_PILOT_NOT_READY"
    sample = _qualitative_sample(rows)
    qualitative = {"artifact_version": f"{ARTIFACT_VERSION}-qualitative-review", "selection_method": "deterministic low/high scorers, genuine failures, then unseen sparse/medium/dense representatives", "references": sample, "review_scope": ["natural English", "coherence", "usefulness", "evidence-dump feel", "checklist feel", "awkward provenance-driven wording", "excessive verbosity", "insufficient explanation"], "chapters": {row["reference"]: row["qualitative_review"] for row in rows if row["reference"] in sample}}
    low_weighted = sorted(rows, key=lambda r: ((r["weighted_coverage"] or 0), r["reference"]))[:10]
    low_eligible = sorted(rows, key=lambda r: ((r["eligible_idea_utilization"] or 0), r["reference"]))[:10]
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-final-report",
        "namespace": manifest["namespace"],
        "starting_sha": STARTING_SHA,
        "source_pilot": manifest["source_pilot"],
        "contract": {"prompt": PROMPT_VERSION, "projection": manifest["projection_version"], "ancestry_envelope": manifest["ancestry_envelope_version"], "provenance_binding": READER_PROVENANCE_BINDING_VERSION, "renderer": RENDERER, "effort": RENDERER_EFFORT, "scoring": manifest["frozen_scoring_contracts"]},
        "aggregate": aggregate,
        "stratified": stratified,
        "batch_reports": batch_reports,
        "lowest_10_weighted": [{"reference": r["reference"], "weighted_coverage": r["weighted_coverage"], "classification": r["final_chapter_classification"]} for r in low_weighted],
        "lowest_10_eligible": [{"reference": r["reference"], "eligible_idea_utilization": r["eligible_idea_utilization"], "classification": r["final_chapter_classification"]} for r in low_eligible],
        "exceptions": [{"reference": r["reference"], "classification": r["final_chapter_classification"], "weighted_coverage": r["weighted_coverage"], "eligible_idea_utilization": r["eligible_idea_utilization"], "gate_result": r["gate_result"]} for r in exceptions],
        "failure_clusters": _failure_clusters(rows),
        "qualitative_sample": sample,
        "success_criteria": criteria,
        "galatians_3": next(row for row in rows if row["reference"] == "Galatians 3"),
        "revelation_20": next(row for row in rows if row["reference"] == "Revelation 20"),
        "final_readiness_decision": decision,
        "bulk_generation_answer": decision != "SCALE_PILOT_NOT_READY",
        "full_corpus_generation_started": False,
        "next_strategy": "Use controlled 25-50 chapter batches; validate each batch; automatically accept clean passes; quarantine exceptions without score-driven regeneration; review failure clusters periodically; increase batch size only after several healthy batches." if decision != "SCALE_PILOT_NOT_READY" else "Identify one bounded remediation from the dominant population-level failure cluster; do not create prompt 1.8 or tune an isolated chapter.",
        "chapters": rows,
    }
    _write_json(root / "aggregate-metrics.json", aggregate)
    _write_json(root / "stratified-analysis.json", stratified)
    _write_json(root / "failure-clusters.json", report["failure_clusters"])
    _write_json(root / "qualitative-review.json", qualitative)
    _write_json(root / "exception-queue.json", {"artifact_version": f"{ARTIFACT_VERSION}-exceptions", "count": len(exceptions), "exceptions": report["exceptions"]})
    _write_json(root / "final-report.json", report)
    return report


def checksums(*, repo_root: Path = ROOT) -> dict[str, Any]:
    root = build_context(repo_root)["root"]
    target = root / "checksums.json"
    files = sorted(path for path in root.rglob("*") if path.is_file() and path != target)
    value = {"artifact_version": f"{ARTIFACT_VERSION}-checksums", "files": {str(path.relative_to(root)): sha256_bytes(path.read_bytes()) for path in files}}
    _write_json(target, value)
    return {"status": "CHECKSUMMED", "file_count": len(files), "path": str(target.relative_to(repo_root))}


def status(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root = context["root"]
    batches = []
    for batch in range(1, 7):
        expected = [row for row in context["manifest"]["chapters"] if row["batch"] == batch]
        present = sum((root / f"batch-{batch:03d}" / "responses/raw" / row["response_filename"]).is_file() for row in expected)
        batches.append({"batch": batch, "responses_present": present, "responses_required": len(expected), "validated": (root / f"batch-{batch:03d}" / "batch-validation.json").is_file()})
    return {"status": "FINALIZED" if (root / "final-report.json").is_file() else "PREPARED" if (root / "manifest.json").is_file() else "NOT_PREPARED", "namespace": context["manifest"]["namespace"], "batches": batches}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "render-batch", "validate-batch", "finalize", "checksums", "status"))
    parser.add_argument("--batch", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command in {"render-batch", "validate-batch"} and args.batch not in range(1, 7):
            raise PilotError("--batch must be 1-6")
        result = prepare() if args.command == "prepare" else render_batch(args.batch) if args.command == "render-batch" else validate_batch(args.batch) if args.command == "validate-batch" else finalize() if args.command == "finalize" else checksums() if args.command == "checksums" else status()
    except (PilotError, ProvenanceBindingError, ArtifactCollisionError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
