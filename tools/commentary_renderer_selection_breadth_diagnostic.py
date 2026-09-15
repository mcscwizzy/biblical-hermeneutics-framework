#!/usr/bin/env python3
"""Freeze, import, and evaluate the bounded prompt 1.7 renderer diagnostic.

The harness has no model client. It creates exactly seven immutable GPT-5.6
Sol request packets, accepts one raw response per packet, and evaluates those
bytes with the unchanged validator, reader-relevance scorer, and Gate v2.1.
It never mutates the prompt-1.6 qualification, CKL, evidence routing,
synthesis, scoring contracts, or production commentary.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.models import (
    COMMENTARY_RENDERER_SELECTION_BREADTH_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    GeneratedMetadata,
)
from bhf_agent.chapter_commentary.prompts import build_user_prompt, system_prompt_for_version
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
    RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    RICHNESS_GATE_V2_VERSION,
    RICHNESS_POLICY_VERSION_V3,
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


ARTIFACT_VERSION = "commentary-renderer-selection-breadth-diagnostic-v1"
PACKET_VERSION = f"{ARTIFACT_VERSION}-packet-v1"
HANDOFF_VERSION = f"{ARTIFACT_VERSION}-handoff-v1"
IMPORT_VERSION = f"{ARTIFACT_VERSION}-import-v1"
PARSED_VERSION = f"{ARTIFACT_VERSION}-parsed-output-v1"
EVALUATION_VERSION = f"{ARTIFACT_VERSION}-evaluation-v1"
PROMPT_VERSION = COMMENTARY_RENDERER_SELECTION_BREADTH_PROMPT_VERSION
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
PREVIOUS_QUALIFICATION_ID = (
    "renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-15f2be7cfcc60bb5ea31"
)
PREVIOUS_ROOT = (
    ROOT
    / ".bhf-data/bhf-commentary-candidates"
    / PREVIOUS_QUALIFICATION_ID
)
EXPECTED_REFERENCES = (
    "Isaiah 13",
    "Romans 3",
    "1 Corinthians 14",
    "Revelation 20",
    "Revelation 21",
    "Exodus 14",
    "Deuteronomy 10",
)
FAILURE_REFERENCES = EXPECTED_REFERENCES[:5]
CONTROL_REFERENCES = EXPECTED_REFERENCES[5:]
FROZEN_CONTRACTS = {
    "renderer_prompt_version": PROMPT_VERSION,
    "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
    "synthesis_schema_version": "1.1",
    "synthesis_compiler_version": "1.1",
    "core_classifier_version": CORE_CLASSIFIER_V2,
    "reader_relevance_eligibility_classifier_version": COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
    "richness_clustering_version": RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    "richness_policy_version": RICHNESS_POLICY_VERSION_V3,
    "gate_version": RICHNESS_GATE_V2_VERSION,
}
THRESHOLDS = {
    "weighted_coverage_min": 0.75,
    "eligible_idea_utilization_min": 0.70,
    "core_coverage_min": 1.0,
    "category_coverage_min": 1.0,
    "high_dump_max": 0,
}
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
GENERATION_INSTRUCTIONS = """Process exactly the seven packets in manifest order.
Use each packet's exact system_prompt and user_prompt without modification.
Renderer identity: gpt-5.6-sol.
Renderer effort: medium.
Renderer prompt contract: 1.7.
Return exactly one raw JSON chapter-commentary object per packet.
Do not use web or external sources. Do not add Markdown fences, envelopes,
commentary, or explanations around a response. Do not alter packet content or
synthesize evidence not present in the packet. Do not retry a packet.
"""


class DiagnosticError(RuntimeError):
    """The frozen seven-case exchange is incomplete or internally inconsistent."""


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DiagnosticError(f"invalid JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DiagnosticError(f"JSON artifact must be an object: {path}")
    return value


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write_json_immutable(path: Path, value: Any) -> str:
    return write_immutable(path, _json_bytes(value))


def _verify_identity(value: dict[str, Any], key: str, label: str) -> None:
    identity = value.get(key)
    expected = sha256_json({k: v for k, v in value.items() if k != key})
    if identity != expected:
        raise DiagnosticError(f"{label} identity mismatch")


def _previous_context(repo_root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    root = repo_root / PREVIOUS_ROOT.relative_to(ROOT)
    manifest = _read(root / "qualification-manifest.json")
    _verify_identity(manifest, "manifest_identity", "prompt-1.6 qualification manifest")
    if manifest.get("qualification_id") != PREVIOUS_QUALIFICATION_ID:
        raise DiagnosticError("prompt-1.6 qualification identity mismatch")
    if manifest.get("chapter_count") != 21:
        raise DiagnosticError("prompt-1.6 qualification is not the frozen 21-chapter corpus")
    if manifest.get("contract_versions", {}).get("renderer_prompt_version") != "1.6":
        raise DiagnosticError("prompt-1.6 qualification renderer identity changed")
    contracts = manifest.get("contract_versions", {})
    for key, expected in FROZEN_CONTRACTS.items():
        if key == "renderer_prompt_version":
            continue
        if contracts.get(key) != expected:
            raise DiagnosticError(f"frozen scoring contract changed: {key}")
    evaluation = _read(root / "evaluation/evaluation.json")
    if evaluation.get("qualification_id") != PREVIOUS_QUALIFICATION_ID:
        raise DiagnosticError("prompt-1.6 evaluation identity mismatch")
    if evaluation.get("qualification_result") != "RENDERER_QUALIFICATION_NOT_QUALIFIED":
        raise DiagnosticError("prompt-1.6 baseline result is not the recorded not-qualified result")
    if [row.get("reference") for row in manifest["chapters"]] != list(
        _previous_reference_order(manifest)
    ):
        raise DiagnosticError("prompt-1.6 qualification chapter order is invalid")
    return manifest, evaluation


def _previous_reference_order(manifest: dict[str, Any]) -> tuple[str, ...]:
    # The diagnostic only draws from these exact rows; the full qualification
    # order is otherwise intentionally not inferred from conversation history.
    available = {row.get("reference") for row in manifest.get("chapters", [])}
    expected = (
        "Exodus 14",
        "Leviticus 8",
        "Numbers 36",
        "Deuteronomy 10",
        "Ruth 2",
        "2 Samuel 15",
        "Ezra 8",
        "Nehemiah 7",
        "Job 1",
        "Isaiah 13",
        "Amos 2",
        "Matthew 4",
        "Matthew 19",
        "Matthew 20",
        "Romans 3",
        "1 Corinthians 14",
        "Hebrews 8",
        "Revelation 4",
        "Revelation 19",
        "Revelation 20",
        "Revelation 21",
    )
    if set(expected) != available:
        raise DiagnosticError("prompt-1.6 qualification membership changed")
    return expected


def _candidate_packet(
    old_row: dict[str, Any],
    prepared: Any,
    *,
    diagnostic_id: str,
) -> dict[str, Any]:
    source_identity = prepared.row["input_identity"]
    for key in ("packet_id", "packet_hash"):
        if source_identity.get(key) != old_row.get(f"source_{key}"):
            raise DiagnosticError(f"source packet {key} mismatch for {old_row['reference']}")
    chapter_data = bible.resolve_chapter(old_row["book"], int(old_row["chapter"]))
    canonical_text = bible.passage_text(chapter_data.get("verses", []))
    system_prompt = system_prompt_for_version(PROMPT_VERSION)
    user_prompt = build_user_prompt(
        old_row["reference"],
        old_row["book"],
        int(old_row["chapter"]),
        canonical_text,
        prepared.synthesis,
        prepared.bundle,
        prepared.synthesis.evidence_availability,
        prompt_version=PROMPT_VERSION,
    )
    packet_base = {
        "artifact_version": PACKET_VERSION,
        "diagnostic_id": diagnostic_id,
        "generation_authorized": False,
        "source_qualification_id": PREVIOUS_QUALIFICATION_ID,
        "source_qualification_ordinal": old_row["ordinal"],
        "reference": old_row["reference"],
        "book": old_row["book"],
        "chapter": int(old_row["chapter"]),
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "system_prompt_sha256": sha256_bytes(system_prompt.encode("utf-8")),
        "user_prompt_sha256": sha256_bytes(user_prompt.encode("utf-8")),
        "commentary_prompt_version": PROMPT_VERSION,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "evidence_availability": prepared.synthesis.evidence_availability,
        "evidence_count": len(prepared.bundle.evidence_items),
        "evidence_hash": prepared.bundle.evidence_hash,
        "synthesis_hash": prepared.synthesis.synthesis_hash,
        "synthesis_schema_version": prepared.synthesis.synthesis_schema_version,
        "synthesis_compiler_version": prepared.synthesis.synthesis_compiler_version,
        "gate_version": source_identity["gate_version"],
        "validator_identity": source_identity["validator_identity"],
        "synthesis_unit_count": len(prepared.synthesis.synthesis_units),
        "source_packet_id": old_row["source_packet_id"],
        "source_packet_hash": old_row["source_packet_hash"],
        "source_packet_file_sha256": old_row["source_packet_file_sha256"],
        "contract_versions": FROZEN_CONTRACTS,
    }
    packet_hash = sha256_json(packet_base)
    return {
        **packet_base,
        "packet_id": f"{ARTIFACT_VERSION}-packet:{packet_hash}",
        "packet_hash": packet_hash,
    }


def build_manifest(
    repo_root: Path = ROOT,
) -> tuple[dict[str, Any], list[tuple[dict[str, Any], Any]]]:
    old_manifest, old_evaluation = _previous_context(repo_root)
    old_by_reference = {row["reference"]: row for row in old_manifest["chapters"]}
    prepared_items: list[tuple[dict[str, Any], Any]] = []
    for reference in EXPECTED_REFERENCES:
        if reference not in old_by_reference:
            raise DiagnosticError(f"prompt-1.6 qualification lacks {reference}")
        old_row = old_by_reference[reference]
        prepared = prepare_chapter(old_row["book"], int(old_row["chapter"]))
        source_identity = prepared.row["input_identity"]
        if source_identity.get("packet_id") != old_row.get("source_packet_id"):
            raise DiagnosticError(f"source packet identity changed for {reference}")
        if source_identity.get("packet_hash") != old_row.get("source_packet_hash"):
            raise DiagnosticError(f"source packet hash changed for {reference}")
        prepared_items.append((old_row, prepared))

    system_hash = sha256_bytes(system_prompt_for_version(PROMPT_VERSION).encode("utf-8"))
    seed = sha256_json(
        {
            "artifact_version": ARTIFACT_VERSION,
            "previous_qualification_id": PREVIOUS_QUALIFICATION_ID,
            "previous_manifest_identity": old_manifest["manifest_identity"],
            "previous_scoring_baseline_sha256": old_manifest["source_scoring_baseline_sha256"],
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
            "contracts": FROZEN_CONTRACTS,
            "prompt_system_sha256": system_hash,
            "references": EXPECTED_REFERENCES,
        }
    )
    diagnostic_id = f"renderer-remediation-prompt-1.7-selection-breadth-{seed[:20]}"
    rows: list[dict[str, Any]] = []
    packets: list[tuple[dict[str, Any], Any]] = []
    for ordinal, (old_row, prepared) in enumerate(prepared_items, 1):
        packet = _candidate_packet(old_row, prepared, diagnostic_id=diagnostic_id)
        filename = f"{ordinal:03d}_{slug(packet['book'], packet['chapter'])}.json"
        packet_bytes = _json_bytes(packet)
        rows.append(
            {
                "ordinal": ordinal,
                "source_qualification_ordinal": old_row["ordinal"],
                "reference": packet["reference"],
                "book": packet["book"],
                "chapter": packet["chapter"],
                "packet_filename": filename,
                "response_filename": filename,
                "packet_id": packet["packet_id"],
                "packet_hash": packet["packet_hash"],
                "packet_file_sha256": sha256_bytes(packet_bytes),
                "source_packet_id": packet["source_packet_id"],
                "source_packet_hash": packet["source_packet_hash"],
                "source_packet_file_sha256": packet["source_packet_file_sha256"],
                "evidence_hash": packet["evidence_hash"],
                "synthesis_hash": packet["synthesis_hash"],
                "system_prompt_sha256": packet["system_prompt_sha256"],
                "user_prompt_sha256": packet["user_prompt_sha256"],
            }
        )
        packets.append((packet, prepared))
    manifest = {
        "artifact_version": ARTIFACT_VERSION,
        "diagnostic_id": diagnostic_id,
        "previous_qualification_id": PREVIOUS_QUALIFICATION_ID,
        "previous_qualification_manifest_identity": old_manifest["manifest_identity"],
        "previous_qualification_result": old_evaluation["qualification_result"],
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "generation_authorized": False,
        "external_response_required": True,
        "contract_versions": FROZEN_CONTRACTS,
        "source_scoring_baseline_sha256": old_manifest["source_scoring_baseline_sha256"],
        "renderer_prompt_source": {
            "module": "bhf_agent.chapter_commentary.prompts",
            "resolver": "system_prompt_for_version",
            "prompt_version": PROMPT_VERSION,
            "system_prompt_sha256": system_hash,
        },
        "chapter_count": len(rows),
        "chapters": rows,
    }
    manifest["manifest_identity"] = sha256_json(manifest)
    return manifest, packets


def _default_root(repo_root: Path = ROOT) -> Path:
    manifest, _ = build_manifest(repo_root)
    return repo_root / ".bhf-data/bhf-commentary-candidates" / manifest["diagnostic_id"]


def _root(repo_root: Path, diagnostic_root: Path | None) -> Path:
    return diagnostic_root or _default_root(repo_root)


def _verify_manifest(manifest: dict[str, Any]) -> None:
    _verify_identity(manifest, "manifest_identity", "prompt-1.7 diagnostic manifest")
    if manifest.get("artifact_version") != ARTIFACT_VERSION:
        raise DiagnosticError("unsupported prompt-1.7 diagnostic artifact version")
    if manifest.get("previous_qualification_id") != PREVIOUS_QUALIFICATION_ID:
        raise DiagnosticError("previous qualification identity mismatch")
    if manifest.get("renderer") != RENDERER or manifest.get("renderer_effort") != RENDERER_EFFORT:
        raise DiagnosticError("renderer identity or effort mismatch")
    if manifest.get("contract_versions") != FROZEN_CONTRACTS:
        raise DiagnosticError("prompt, scoring, or gate contract differs")
    if manifest.get("chapter_count") != 7:
        raise DiagnosticError("diagnostic must contain exactly seven chapters")
    rows = manifest.get("chapters")
    if not isinstance(rows, list) or [row.get("reference") for row in rows] != list(EXPECTED_REFERENCES):
        raise DiagnosticError("diagnostic chapter order or membership mismatch")
    prompt_source = manifest.get("renderer_prompt_source", {})
    if prompt_source.get("prompt_version") != PROMPT_VERSION:
        raise DiagnosticError("prompt 1.7 identity mismatch")
    if any(row.get("system_prompt_sha256") != prompt_source.get("system_prompt_sha256") for row in rows):
        raise DiagnosticError("prompt 1.7 system identity mismatch")


def _zip_write(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, content)


def prepare(*, repo_root: Path = ROOT, diagnostic_root: Path | None = None) -> dict[str, Any]:
    root = _root(repo_root, diagnostic_root)
    manifest, packets = build_manifest(repo_root)
    _verify_manifest(manifest)
    _write_json_immutable(root / "manifest.json", manifest)
    handoff_items = []
    archive_stream = BytesIO()
    with zipfile.ZipFile(archive_stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _zip_write(archive, "manifest.json", _json_bytes(manifest))
        _zip_write(archive, "GENERATION_INSTRUCTIONS.txt", GENERATION_INSTRUCTIONS.encode())
        for row, (packet, _) in zip(manifest["chapters"], packets, strict=True):
            packet_bytes = _json_bytes(packet)
            if sha256_bytes(packet_bytes) != row["packet_file_sha256"]:
                raise DiagnosticError(f"packet serialization drift for {row['reference']}")
            write_immutable(root / "packets" / row["packet_filename"], packet_bytes)
            _zip_write(archive, f"packets/{row['packet_filename']}", packet_bytes)
            stem = Path(row["packet_filename"]).stem
            handoff_dir = root / "handoff" / stem
            system_bytes = packet["system_prompt"].encode()
            user_bytes = packet["user_prompt"].encode()
            write_immutable(handoff_dir / "system_prompt.txt", system_bytes)
            write_immutable(handoff_dir / "user_prompt.txt", user_bytes)
            metadata = {
                **row,
                "diagnostic_id": manifest["diagnostic_id"],
                "renderer": RENDERER,
                "renderer_effort": RENDERER_EFFORT,
                "commentary_prompt_version": PROMPT_VERSION,
                "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            }
            _write_json_immutable(handoff_dir / "metadata.json", metadata)
            handoff_items.append(
                {
                    "ordinal": row["ordinal"],
                    "reference": row["reference"],
                    "directory": f"handoff/{stem}",
                    "response_filename": row["response_filename"],
                    "packet_id": row["packet_id"],
                    "packet_hash": row["packet_hash"],
                }
            )
    write_immutable(
        root / "renderer-remediation-prompt-1.7-selection-breadth-input.zip",
        archive_stream.getvalue(),
    )
    handoff = {
        "artifact_version": HANDOFF_VERSION,
        "diagnostic_id": manifest["diagnostic_id"],
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "items": handoff_items,
    }
    handoff["handoff_identity"] = sha256_json(handoff)
    _write_json_immutable(root / "handoff/manifest.json", handoff)
    return {
        "status": "PREPARED",
        "diagnostic_id": manifest["diagnostic_id"],
        "root": str(root),
        "chapter_count": 7,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "system_prompt_sha256": manifest["renderer_prompt_source"]["system_prompt_sha256"],
    }


def import_responses(
    source_dir: Path,
    *,
    repo_root: Path = ROOT,
    diagnostic_root: Path | None = None,
) -> dict[str, Any]:
    root = _root(repo_root, diagnostic_root)
    manifest = _read(root / "manifest.json")
    _verify_manifest(manifest)
    current, _ = build_manifest(repo_root)
    if current != manifest:
        raise DiagnosticError("frozen diagnostic inputs changed before response import")
    expected = {row["response_filename"] for row in manifest["chapters"]}
    actual = {path.name for path in source_dir.glob("*.json") if path.is_file()}
    if actual != expected:
        raise DiagnosticError(
            f"response filenames mismatch; missing={sorted(expected - actual)}; extra={sorted(actual - expected)}"
        )
    response_rows = []
    for row in manifest["chapters"]:
        raw = (source_dir / row["response_filename"]).read_bytes()
        digest = write_immutable(root / "responses/raw" / row["response_filename"], raw)
        response_rows.append(
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
        "diagnostic_id": manifest["diagnostic_id"],
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "response_count": 7,
        "raw_responses_immutable": True,
        "responses": response_rows,
    }
    _write_json_immutable(root / "responses/import-receipt.json", receipt)
    return {"status": "IMPORTED", "diagnostic_id": manifest["diagnostic_id"], "response_count": 7}


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
        "renderer_prompt_version": PROMPT_VERSION,
        "validation_status": "rejected",
        "structural_result": "REJECTED",
        "rejection_codes": codes,
        "weighted_coverage": None,
        "core_coverage": None,
        "eligible_idea_utilization": None,
        "eligible_unit_utilization": None,
        "raw_synthesis_utilization": None,
        "category_coverage": None,
        "dump_severity": None,
        "quality_gate_outcome": None,
        "gate_v2_1": None,
    }


def _evaluate_one(
    row: dict[str, Any], raw: bytes, prepared: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        result = _empty_metrics(row, ["MALFORMED_RESPONSE_JSON"])
        return result, {"artifact_version": PARSED_VERSION, "parse_status": "MALFORMED_JSON", "error": str(exc)}
    if not isinstance(payload, dict):
        result = _empty_metrics(row, ["MALFORMED_RESPONSE_JSON"])
        return result, {"artifact_version": PARSED_VERSION, "parse_status": "NON_OBJECT_JSON"}

    renderer_payload = dict(payload)
    renderer_payload["generated_metadata"] = GeneratedMetadata(
        evidence_hash=prepared.bundle.evidence_hash,
        evidence_bundle_version=prepared.bundle.version,
        commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
        commentary_prompt_version=PROMPT_VERSION,
        model=RENDERER,
        generated_timestamp=None,
        synthesis_hash=prepared.synthesis.synthesis_hash,
        synthesis_schema_version=prepared.synthesis.synthesis_schema_version,
        synthesis_compiler_version=prepared.synthesis.synthesis_compiler_version,
        renderer_label=RENDERER,
    ).to_dict()
    renderer_payload["evidence_availability"] = prepared.synthesis.evidence_availability
    renderer_payload["status"] = "pending"
    validation = validate_chapter_commentary(
        renderer_payload,
        prepared.bundle,
        expected_evidence_hash=prepared.bundle.evidence_hash,
        expected_prompt_version=PROMPT_VERSION,
        expected_reference=row["reference"],
        expected_book=row["book"],
        expected_chapter=int(row["chapter"]),
        synthesis=prepared.synthesis,
        expected_synthesis_hash=prepared.synthesis.synthesis_hash,
    )
    parsed = {
        "artifact_version": PARSED_VERSION,
        "reference": row["reference"],
        "raw_sha256": sha256_bytes(raw),
        "parse_status": "JSON_OBJECT",
        "renderer_payload": payload,
        "validated_commentary": None,
        "validation_errors": list(validation.errors),
    }
    if not validation.valid or validation.commentary is None:
        result = _empty_metrics(row, _codes(validation.errors) or ["VALIDATION_FAILED"])
        return result, parsed

    parsed["validated_commentary"] = validation.commentary.to_dict()
    blocks = [block for section in validation.commentary.sections for block in section.blocks]
    audit = audit_chapter(row["book"], int(row["chapter"]), validation.commentary, prepared.bundle)
    passage_text = bible.passage_text(
        bible.resolve_chapter(row["book"], int(row["chapter"])).get("verses", [])
    )
    score = score_synthesis_richness(
        prepared.synthesis.synthesis_units,
        evidence_items=prepared.bundle.evidence_items,
        consumed_synthesis_ids=[sid for block in blocks for sid in block.synthesis_ids],
        blocks=blocks,
        passage_ref=row["reference"],
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=passage_text,
    )
    gate = assess_gate_v2(
        score=score,
        evidence_availability=prepared.synthesis.evidence_availability,
        baseline_richness="SYNTHESIS_GAP",
        after_richness=audit["richness_status"],
        safety_checks={name: True for name in (
            "validation_clean", "provenance_complete", "hashes_valid",
            "chapter_boundaries_valid", "confidence_valid", "dispute_state_preserved",
            "unsupported_significance_absent",
        )},
        evidence_use_delta=audit["unique_evidence_ids_consumed"],
        section_delta=audit["section_count"],
        commentary_word_count=audit["commentary_prose_word_count"],
        unique_evidence_ids_consumed=audit["unique_evidence_ids_consumed"],
    )
    result = {
        "reference": row["reference"],
        "renderer_prompt_version": PROMPT_VERSION,
        "validation_status": "validated",
        "structural_result": "ACCEPTED",
        "rejection_codes": [],
        "weighted_coverage": score.weighted_idea_coverage,
        "core_coverage": score.core_cluster_coverage,
        "eligible_idea_utilization": score.idea_cluster_coverage,
        "eligible_unit_utilization": score.eligible_synthesis_coverage,
        "raw_synthesis_utilization": score.raw_synthesis_coverage,
        "category_coverage": score.category_coverage,
        "dump_severity": score.dump_diagnostics.severity,
        "word_count": audit["commentary_prose_word_count"],
        "block_count": audit["commentary_block_count"],
        "quality_gate_outcome": gate.outcome,
        "gate_v2_1": gate.to_dict(),
        "renderer_qualification_result": (
            "PASS" if score.weighted_idea_coverage >= THRESHOLDS["weighted_coverage_min"] else "BELOW_TARGET"
        ),
        "score": score.to_dict(),
        "audit": audit,
    }
    return result, parsed


def _delta(new: Any, old: Any) -> float | None:
    if isinstance(new, (int, float)) and isinstance(old, (int, float)):
        return round(new - old, 4)
    return None


def _classification(old: dict[str, Any], new: dict[str, Any], reference: str) -> str:
    if new.get("structural_result") != "ACCEPTED":
        return "STRUCTURAL_REGRESSION"
    if new.get("dump_severity") == "HIGH" and old.get("dump_severity") != "HIGH":
        return "REGRESSED"
    for key in ("core_coverage", "category_coverage"):
        if isinstance(old.get(key), (int, float)) and isinstance(new.get(key), (int, float)) and new[key] < old[key]:
            return "REGRESSED"
    if reference in CONTROL_REFERENCES:
        return "CONTROL_STABLE" if all(
            not (isinstance(old.get(key), (int, float)) and isinstance(new.get(key), (int, float)) and new[key] < old[key])
            for key in ("weighted_coverage", "eligible_idea_utilization", "category_coverage")
        ) else "REGRESSED"
    old_weighted = old.get("weighted_coverage")
    new_weighted = new.get("weighted_coverage")
    old_eligible = old.get("eligible_idea_utilization")
    new_eligible = new.get("eligible_idea_utilization")
    if (
        isinstance(new_weighted, (int, float))
        and new_weighted >= THRESHOLDS["weighted_coverage_min"]
        and isinstance(new_eligible, (int, float))
        and new_eligible >= THRESHOLDS["eligible_idea_utilization_min"]
    ):
        return "RESOLVED"
    if (
        isinstance(new_weighted, (int, float))
        and isinstance(old_weighted, (int, float))
        and new_weighted > old_weighted
    ) or (
        isinstance(new_eligible, (int, float))
        and isinstance(old_eligible, (int, float))
        and new_eligible > old_eligible
    ):
        return "IMPROVED_BUT_BELOW_TARGET"
    return "UNCHANGED"


def evaluate(*, repo_root: Path = ROOT, diagnostic_root: Path | None = None) -> dict[str, Any]:
    root = _root(repo_root, diagnostic_root)
    manifest = _read(root / "manifest.json")
    _verify_manifest(manifest)
    current, material = build_manifest(repo_root)
    if current != manifest:
        raise DiagnosticError("frozen diagnostic inputs changed before evaluation")
    receipt = _read(root / "responses/import-receipt.json")
    if receipt.get("diagnostic_id") != manifest["diagnostic_id"] or receipt.get("response_count") != 7:
        raise DiagnosticError("seven-response immutable import is absent or mismatched")
    _, old_evaluation = _previous_context(repo_root)
    old_rows = {row["reference"]: row for row in old_evaluation["chapters"]}
    results = []
    comparisons = []
    for row, (_, prepared) in zip(manifest["chapters"], material, strict=True):
        raw_path = root / "responses/raw" / row["response_filename"]
        raw = raw_path.read_bytes()
        receipt_row = next(item for item in receipt["responses"] if item["reference"] == row["reference"])
        if sha256_bytes(raw) != receipt_row["raw_sha256"]:
            raise DiagnosticError(f"raw response changed after import for {row['reference']}")
        result, parsed = _evaluate_one(row, raw, prepared)
        result.update({
            "evidence_availability": prepared.synthesis.evidence_availability,
            "packet_id": row["packet_id"],
            "packet_hash": row["packet_hash"],
            "raw_sha256": sha256_bytes(raw),
        })
        parsed.update({
            "diagnostic_id": manifest["diagnostic_id"],
            "packet_id": row["packet_id"],
            "packet_hash": row["packet_hash"],
        })
        stem = Path(row["response_filename"]).stem
        _write_json_immutable(root / "parsed" / f"{stem}.json", parsed)
        results.append(result)
        old = old_rows[row["reference"]]
        metric_keys = (
            "structural_result", "rejection_codes", "weighted_coverage", "core_coverage",
            "eligible_idea_utilization", "category_coverage", "dump_severity",
            "quality_gate_outcome",
        )
        comparison = {
            "reference": row["reference"],
            "old_prompt_1_6": {key: old.get(key) for key in metric_keys},
            "new_prompt_1_7": {key: result.get(key) for key in metric_keys},
            "delta": {
                key: _delta(result.get(key), old.get(key))
                for key in ("weighted_coverage", "core_coverage", "eligible_idea_utilization", "category_coverage")
            },
            "diagnostic_interpretation": _classification(old, result, row["reference"]),
            "gate_result": result.get("quality_gate_outcome"),
        }
        comparisons.append(comparison)
        _write_json_immutable(
            root / "evaluation/chapters" / f"{stem}.json",
            {"artifact_version": EVALUATION_VERSION, **comparison, "full_result": result},
        )

    failure_results = [row for row in results if row["reference"] in FAILURE_REFERENCES]
    control_results = [row for row in results if row["reference"] in CONTROL_REFERENCES]
    old_by_ref = old_rows
    structural_valid = sum(row["structural_result"] == "ACCEPTED" for row in results)
    high_dumps = sum(row.get("dump_severity") == "HIGH" for row in results)
    quality_failures = sum(row.get("quality_gate_outcome") == "QUALITY_FAIL" for row in results)
    core_ok = all(row.get("core_coverage") == THRESHOLDS["core_coverage_min"] for row in results)
    targets_met = all(
        isinstance(row.get("weighted_coverage"), (int, float))
        and row["weighted_coverage"] >= THRESHOLDS["weighted_coverage_min"]
        and isinstance(row.get("eligible_idea_utilization"), (int, float))
        and row["eligible_idea_utilization"] >= THRESHOLDS["eligible_idea_utilization_min"]
        for row in failure_results
    )
    material_improvement = all(
        isinstance(row.get("weighted_coverage"), (int, float))
        and isinstance(old_by_ref[row["reference"]].get("weighted_coverage"), (int, float))
        and row["weighted_coverage"] > old_by_ref[row["reference"]]["weighted_coverage"]
        for row in failure_results
    )
    controls_clean = all(
        row["structural_result"] == "ACCEPTED"
        and row.get("dump_severity") != "HIGH"
        and all(
            not (
                isinstance(row.get(key), (int, float))
                and isinstance(old_by_ref[row["reference"]].get(key), (int, float))
                and row[key] < old_by_ref[row["reference"]][key]
            )
            for key in ("weighted_coverage", "eligible_idea_utilization", "category_coverage")
        )
        for row in control_results
    )
    rejection_counts = Counter(code for row in results for code in row["rejection_codes"])
    hard_codes = sorted(code for code in rejection_counts if code in HARD_PROVENANCE_CODES)
    pass_result = (
        structural_valid == 7
        and core_ok
        and high_dumps == 0
        and not hard_codes
        and quality_failures == 0
        and material_improvement
        and targets_met
        and controls_clean
    )
    report = {
        "artifact_version": EVALUATION_VERSION,
        "diagnostic_id": manifest["diagnostic_id"],
        "previous_qualification_id": PREVIOUS_QUALIFICATION_ID,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "prompt_system_sha256": manifest["renderer_prompt_source"]["system_prompt_sha256"],
        "frozen_contracts": FROZEN_CONTRACTS,
        "chapters": results,
        "comparison_table": comparisons,
        "aggregate": {
            "chapter_count": 7,
            "structurally_valid": structural_valid,
            "structural_rejections": 7 - structural_valid,
            "rejection_codes": dict(rejection_counts),
            "hard_provenance_codes": hard_codes,
            "quality_failures": quality_failures,
            "high_dump_count": high_dumps,
            "core_coverage_all_required": core_ok,
            "failure_cases_materially_improved": material_improvement,
            "failure_cases_at_or_above_targets": targets_met,
            "controls_clean": controls_clean,
            "failure_case_results": {
                row["reference"]: _classification(
                    old_by_ref[row["reference"]], row, row["reference"]
                )
                for row in failure_results
            },
        },
        "thresholds": THRESHOLDS,
        "qualification_target_semantics": (
            "The unchanged v3 reader-relevance scorer and Gate v2.1 remain the measuring instrument; "
            "the seven-case result requires each prior failure to meet the stated breadth thresholds, "
            "with controls checked for regressions."
        ),
        "qualitative_review": {
            "status": "REQUIRED_AFTER_IMPORT",
            "scope": list(EXPECTED_REFERENCES),
            "dimensions": [
                "readability", "natural_english", "repetitive_evidence_phrasing",
                "encyclopedic_feel", "abrupt_transitions", "excessive_length",
                "missing_synthesis_connections", "evidence_dumping",
                "contextual_reader_value",
            ],
        },
        "diagnostic_result": (
            "PROMPT_1_7_SELECTION_BREADTH_PASS"
            if pass_result
            else "PROMPT_1_7_SELECTION_BREADTH_NOT_READY"
        ),
    }
    _write_json_immutable(root / "evaluation/evaluation.json", report)
    return report


def status(*, repo_root: Path = ROOT, diagnostic_root: Path | None = None) -> dict[str, Any]:
    root = _root(repo_root, diagnostic_root)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return {"status": "NOT_PREPARED", "diagnostic_root": str(root)}
    manifest = _read(manifest_path)
    _verify_manifest(manifest)
    receipt_path = root / "responses/import-receipt.json"
    evaluation_path = root / "evaluation/evaluation.json"
    return {
        "status": _read(evaluation_path).get("diagnostic_result") if evaluation_path.is_file()
        else "IMPORTED_AWAITING_EVALUATION" if receipt_path.is_file()
        else "AWAITING_EXTERNAL_RESPONSE_BUNDLE",
        "diagnostic_id": manifest["diagnostic_id"],
        "diagnostic_root": str(root),
        "chapter_count": 7,
        "response_count": _read(receipt_path).get("response_count") if receipt_path.is_file() else 0,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic-root", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare", help="freeze the seven prompt-1.7 packets")
    importer = sub.add_parser("import", help="immutably import seven raw renderer responses")
    importer.add_argument("--source-dir", type=Path, required=True)
    sub.add_parser("evaluate", help="run unchanged validation, scoring, and Gate v2.1")
    sub.add_parser("status", help="show diagnostic lifecycle status")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(diagnostic_root=args.diagnostic_root)
        elif args.command == "import":
            result = import_responses(args.source_dir, diagnostic_root=args.diagnostic_root)
        elif args.command == "evaluate":
            result = evaluate(diagnostic_root=args.diagnostic_root)
        else:
            result = status(diagnostic_root=args.diagnostic_root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (DiagnosticError, ArtifactCollisionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
