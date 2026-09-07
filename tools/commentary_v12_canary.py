#!/usr/bin/env python3
"""Prepare, generate, and compare the bounded Commentary v1.2 canary corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.chapter_commentary.synthesis import (
    compile_chapter_synthesis,
    save_synthesis,
    validate_synthesis,
)
from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION
from bhf_agent.chapter_commentary.prompts import CHAPTER_COMMENTARY_SYSTEM_PROMPT, build_user_prompt
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION


CANDIDATE_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment"
AUDIT_PATH = CANDIDATE_ROOT / "audit/commentary-richness-audit.json"
CANARY_ROOT = CANDIDATE_ROOT / "canary"
SYNTHESIS_ROOT = CANARY_ROOT / "synthesis"
COMMENTARY_ROOT = CANARY_ROOT / "commentary"
PROMPT_ROOT = CANARY_ROOT / "prompts"
RAW_RESPONSE_ROOT = CANARY_ROOT / "responses/raw"
ACCEPTED_RESPONSE_ROOT = CANARY_ROOT / "responses/accepted"
REJECTED_RESPONSE_ROOT = CANARY_ROOT / "responses/rejected"
RUNTIME_V11 = ROOT / ".bhf-data/bhf-commentary-v1.1"
V11_STATE = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/pipeline-state.json"
CANARY_REFERENCES = (
    ("Genesis", 1),
    ("Leviticus", 16),
    ("Ruth", 3),
    ("Psalms", 1),
    ("1 Samuel", 21),
    ("1 Samuel", 28),
    ("2 Samuel", 6),
    ("2 Samuel", 24),
    ("1 Chronicles", 8),
    ("John", 1),
    ("Isaiah", 6),
    ("Revelation", 12),
    # An additional observed DATA_GAP control; the required matrix alone does
    # not currently contain a chapter classified DATA_GAP by EvidenceBundle 1.1.
    ("Numbers", 3),
)
REQUIRED_PROVENANCE = (
    "evidence_hash",
    "evidence_bundle_version",
    "synthesis_hash",
    "synthesis_schema_version",
    "synthesis_compiler_version",
    "commentary_schema_version",
    "commentary_prompt_version",
    "model",
    "generated_timestamp",
    "renderer_label",
    "imported_timestamp",
    "candidate_id",
)


def prepare() -> dict[str, Any]:
    """Lock live evidence/synthesis identities and baseline audit rows."""

    baseline = _read_json(AUDIT_PATH)
    baseline_rows = {row["reference"]: row for row in baseline["chapters"]}
    fingerprint_errors = _protected_v11_errors()
    if fingerprint_errors:
        raise RuntimeError("protected Commentary v1.1 fingerprints changed")
    rows = []
    for book, chapter in CANARY_REFERENCES:
        reference = f"{book} {chapter}"
        bundle = get_chapter_evidence_bundle(
            book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
        )
        if bundle is None:
            raise RuntimeError(f"unable to build evidence for {reference}")
        synthesis = compile_chapter_synthesis(bundle, book=book, chapter=chapter)
        errors = validate_synthesis(synthesis, bundle)
        if errors:
            raise RuntimeError(f"invalid synthesis for {reference}: {errors}")
        path = save_synthesis(synthesis, SYNTHESIS_ROOT)
        before = baseline_rows.get(reference)
        if before is None:
            raise RuntimeError(f"baseline richness audit has no row for {reference}")
        rows.append(
            {
                "reference": reference,
                "book": book,
                "chapter": chapter,
                "evidence_hash": bundle.evidence_hash,
                "evidence_bundle_version": bundle.version,
                "evidence_availability": synthesis.evidence_availability,
                "evidence_ids": sorted(bundle.evidence_by_id),
                "synthesis_hash": synthesis.synthesis_hash,
                "synthesis_schema_version": synthesis.synthesis_schema_version,
                "synthesis_compiler_version": synthesis.synthesis_compiler_version,
                "synthesis_unit_count": len(synthesis.synthesis_units),
                "synthesis_path": path.relative_to(ROOT).as_posix(),
                "before": _metrics(before),
                **_prompt_packet_fields(reference, book, chapter, bundle, synthesis),
                "status": "READY_FOR_RENDERER",
            }
        )
    artifact = {
        "artifact_version": "commentary-v1.2-canary-preflight-v1",
        "status": "READY_FOR_RENDERER",
        "renderer_requirement": {
            "status": "APPROVED_RENDERER_REQUIRED",
            "execution_path": "external_or_conversational",
            "effort": "medium",
        },
        "renderer_is_repository_adapter": False,
        "candidate_only": True,
        "v1_1_protected_fingerprints_verified": True,
        "evidence_locked": True,
        "synthesis_locked": True,
        "chapter_count": len(rows),
        "chapters": rows,
    }
    _write_json(CANARY_ROOT / "canary-preflight.json", artifact)
    _write_json(
        CANARY_ROOT / "canary-generation-manifest.json",
        {
            "artifact_version": "commentary-v1.2-canary-generation-manifest-v1",
            "status": "READY_FOR_RENDERER",
            "renderer_requirement": artifact["renderer_requirement"],
            "renderer_is_repository_adapter": False,
            "candidate_only": True,
            "chapters": [
                {
                    "reference": row["reference"],
                    "packet_id": row["packet_id"],
                    "packet_path": row["prompt_path"],
                    "expected_response_path": row["expected_response_path"],
                    "accepted_candidate_path": row["accepted_candidate_path"],
                    "evidence_hash": row["evidence_hash"],
                    "synthesis_hash": row["synthesis_hash"],
                    "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
                }
                for row in rows
            ],
        },
    )
    _write_json(
        CANDIDATE_ROOT / "candidate-state.json",
        {
            "pipeline_version": "commentary-v1.2-enrichment",
            "current_stage": "CANARY_READY_FOR_RENDERER",
            "required_renderer": "approved_external_renderer",
            "required_effort": "medium",
            "full_bible_generation_authorized": False,
            "v1_1_mutated": False,
            "ckl_mutated": False,
            "canary_chapter_count": len(rows),
        },
    )
    return artifact


def generate(reference: str | None = None) -> dict[str, Any]:
    """Record the external-renderer boundary without invoking a repository adapter."""

    preflight = _read_json(CANARY_ROOT / "canary-preflight.json")
    if preflight.get("status") != "READY_FOR_RENDERER":
        raise RuntimeError("run prepare and obtain READY_FOR_RENDERER first")
    rows = []
    selected = [row for row in preflight["chapters"] if reference in (None, row["reference"])]
    if reference and not selected:
        raise RuntimeError(f"reference is not in the canary matrix: {reference}")
    for row in selected:
        rows.append({
            "reference": row["reference"],
            "packet_id": row["packet_id"],
            "status": "BLOCKED_BEFORE_PROSE",
            "blocker": "APPROVED_RENDERER_REQUIRED",
            "packet_path": row["prompt_path"],
            "expected_response_path": row["expected_response_path"],
            "accepted_candidate_path": row["accepted_candidate_path"],
        })
    artifact = {
        "artifact_version": "commentary-v1.2-canary-generation-v1",
        "status": "BLOCKED_BEFORE_PROSE",
        "blocker": "APPROVED_RENDERER_REQUIRED",
        "renderer_requirement": preflight["renderer_requirement"],
        "renderer_invoked": False,
        "fallback_provider_used": False,
        "requested_count": len(selected),
        "completed_count": 0,
        "chapters": rows,
    }
    _write_json(CANARY_ROOT / "canary-generation.json", artifact)
    _write_json(
        CANDIDATE_ROOT / "candidate-state.json",
        {
            "pipeline_version": "commentary-v1.2-enrichment",
            "current_stage": "CANARY_BLOCKED_BEFORE_PROSE",
            "required_renderer": "approved_external_renderer",
            "required_effort": "medium",
            "blocked_reason": "APPROVED_RENDERER_REQUIRED",
            "full_bible_generation_authorized": False,
            "v1_1_mutated": False,
            "ckl_mutated": False,
            "canary_chapter_count": len(preflight["chapters"]),
        },
    )
    return artifact


def compare() -> dict[str, Any]:
    """Write a deterministic v1.1/synthesis/v1.2 comparison for all canaries."""

    preflight = _read_json(CANARY_ROOT / "canary-preflight.json")
    import_path = CANARY_ROOT / "canary-import.json"
    import_artifact = _read_json(import_path) if import_path.is_file() else {
        "status": "BLOCKED_BEFORE_PROSE",
        "raw_response_count": len(list(RAW_RESPONSE_ROOT.glob("*.json"))),
        "missing_references": [row["reference"] for row in preflight["chapters"]],
        "chapters": [],
    }
    imported_by_reference = {
        row["reference"]: row
        for row in import_artifact.get("chapters", [])
        if row.get("reference")
    }
    rows = []
    for locked in preflight["chapters"]:
        book, chapter = locked["book"], locked["chapter"]
        import_row = imported_by_reference.get(locked["reference"], {})
        commentary = (
            load_commentary(ACCEPTED_RESPONSE_ROOT, book, chapter)
            if import_row.get("import_status") == "accepted"
            else None
        )
        bundle = get_chapter_evidence_bundle(
            book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
        )
        if bundle is None:
            raise RuntimeError(f"unable to rebuild {locked['reference']}")
        synthesis = compile_chapter_synthesis(bundle, book=book, chapter=chapter)
        synthesis_errors = list(validate_synthesis(synthesis, bundle))
        identity_ok = (
            bundle.evidence_hash == locked["evidence_hash"]
            and synthesis.synthesis_hash == locked["synthesis_hash"]
        )
        after = audit_chapter(book, chapter, commentary, bundle) if commentary else None
        validation_errors = list(import_row.get("validation_errors", []))
        rejection_codes = list(import_row.get("rejection_codes", []))
        metadata = commentary.generated_metadata.to_dict() if commentary and commentary.generated_metadata else {}
        before_metrics = locked["before"]
        after_metrics = _metrics(after) if after else None
        synthesis_ids = sorted({
            synthesis_id
            for section in (commentary.sections if commentary else [])
            for block in section.blocks
            for synthesis_id in block.synthesis_ids
        })
        if after_metrics is not None:
            after_metrics["synthesis_ids_consumed"] = synthesis_ids
            after_metrics["unique_synthesis_ids_consumed"] = len(synthesis_ids)
        deltas = _comparison_deltas(before_metrics, after_metrics, len(synthesis.synthesis_units))
        rows.append(
            {
                "reference": locked["reference"],
                "before": before_metrics,
                "synthesis": {
                    "synthesis_unit_count": len(synthesis.synthesis_units),
                    "evidence_ids_represented": sorted(synthesis.coverage.used_evidence_ids),
                    "categories_represented": sorted(synthesis.coverage.evidence_categories),
                    "synthesis_hash": synthesis.synthesis_hash,
                },
                "after": after_metrics,
                "deltas": deltas,
                "import_status": import_row.get("import_status", "missing"),
                "response_structurally_parsed": import_row.get("structurally_parsed", False),
                "validation_status": commentary.status if commentary else import_row.get("validation_status", "not_run"),
                "evidence_and_synthesis_locks_match": identity_ok,
                "synthesis_validation_errors": synthesis_errors,
                "commentary_prompt_version": metadata.get("commentary_prompt_version"),
                "provenance_complete": all(metadata.get(field) for field in REQUIRED_PROVENANCE),
                "rejection_codes": rejection_codes,
                "validation_errors": validation_errors,
                "likely_failure_layer": _failure_layer(
                    locked, synthesis, after_metrics, rejection_codes
                ),
            }
        )
    gate_state, gate_checks = evaluate_gate(rows, import_artifact, _protected_v11_errors())
    artifact = {
        "artifact_version": "commentary-v1.2-canary-comparison-v1",
        "status": gate_state,
        "gate_state": gate_state,
        "scale_gate_decision": "READY_FOR_HUMAN_REVIEW" if gate_state == "CANARY_PASS" else "NOT_READY",
        "bulk_generation_authorized": False,
        "gate_checks": gate_checks,
        "chapters": rows,
    }
    _write_json(CANARY_ROOT / "canary-comparison.json", artifact)
    _write_text(CANARY_ROOT / "canary-comparison.md", _render_comparison(artifact))
    return artifact


def gate() -> dict[str, Any]:
    """Evaluate and persist the canary scale gate without authorizing generation."""

    comparison = compare()
    artifact = {
        "artifact_version": "commentary-v1.2-canary-gate-v1",
        "status": comparison["gate_state"],
        "decision": comparison["scale_gate_decision"],
        "bulk_generation_authorized": False,
        "gate_checks": comparison["gate_checks"],
        "human_review_required": comparison["gate_state"] == "CANARY_PASS",
    }
    _write_json(CANARY_ROOT / "canary-gate.json", artifact)
    state = _read_json(CANDIDATE_ROOT / "candidate-state.json")
    state.update({
        "current_stage": f"CANARY_{artifact['status']}",
        "current_gate_state": artifact["status"],
        "full_bible_generation_authorized": False,
    })
    _write_json(CANDIDATE_ROOT / "candidate-state.json", state)
    return artifact


def export_manifest(output: Path | None = None) -> dict[str, Any]:
    """List one isolated packet and response target per canonical canary."""

    manifest = _read_json(CANARY_ROOT / "canary-generation-manifest.json")
    artifact = {
        "artifact_version": "commentary-v1.2-renderer-export-v1",
        "transaction_isolation": "one_chapter_per_response",
        "chapters": [
            {
                "packet_id": row["packet_id"],
                "reference": row["reference"],
                "prompt_file_path": row["packet_path"],
                "expected_response_file_path": row["expected_response_path"],
            }
            for row in manifest["chapters"]
        ],
    }
    if output is not None:
        _write_json(output, artifact)
    return artifact


def _metrics(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        key: row[key]
        for key in (
            "evidence_availability", "richness_status", "section_count",
            "commentary_block_count", "commentary_prose_char_count",
            "commentary_prose_word_count", "evidence_ids_referenced",
            "unique_evidence_ids_consumed", "boilerplate_detected",
            "boilerplate_phrases", "boilerplate_ratio",
        ) if key in row
    }


def _prompt_packet_fields(reference, book, chapter, bundle, synthesis) -> dict[str, str]:
    path = _write_prompt_packet(reference, book, chapter, bundle, synthesis)
    packet = _read_json(path)
    filename = f"{_slug(book)}_{chapter:03d}.json"
    return {
        "packet_id": packet["packet_id"],
        "prompt_path": path.relative_to(ROOT).as_posix(),
        "expected_response_path": (RAW_RESPONSE_ROOT / filename).relative_to(ROOT).as_posix(),
        "accepted_candidate_path": (ACCEPTED_RESPONSE_ROOT / filename).relative_to(ROOT).as_posix(),
    }


def _write_prompt_packet(reference, book, chapter, bundle, synthesis) -> Path:
    """Persist an exact application-built prompt without invoking a model."""

    try:
        chapter_data = bible.resolve_chapter(book, chapter)
        canonical_text = bible.passage_text(chapter_data.get("verses", []))
    except bible.BibleError as exc:
        raise RuntimeError(f"unable to load canonical text for {reference}: {exc}") from exc
    user_prompt = build_user_prompt(
        reference,
        book,
        chapter,
        canonical_text,
        synthesis,
        bundle,
        synthesis.evidence_availability,
    )
    path = PROMPT_ROOT / f"{_slug(book)}_{chapter:03d}.json"
    packet = {
        "artifact_version": "commentary-v1.2-generation-packet-v1",
        "reference": reference,
        "renderer_requirement": "APPROVED_RENDERER_REQUIRED",
        "execution_path": "external_or_conversational",
        "effort": "medium",
        "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
        "evidence_hash": bundle.evidence_hash,
        "synthesis_hash": synthesis.synthesis_hash,
        "system_prompt": CHAPTER_COMMENTARY_SYSTEM_PROMPT,
        "user_prompt": user_prompt,
    }
    packet["packet_id"] = calculate_packet_id(packet)
    _write_json(path, packet)
    return path


def calculate_packet_id(packet: dict[str, Any]) -> str:
    """Return the content identity of a generation packet, excluding its own ID."""

    identity_payload = {key: value for key, value in packet.items() if key != "packet_id"}
    encoded = json.dumps(
        identity_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"commentary-v1.2-packet:{hashlib.sha256(encoded).hexdigest()}"


def _slug(book: str) -> str:
    return book.lower().replace(" ", "_")


def _protected_v11_errors() -> list[str]:
    state = _read_json(V11_STATE)
    errors = []
    for relative, expected in state.get("protected_fingerprints", {}).items():
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        if actual != expected:
            errors.append(relative)
    return errors


def evaluate_gate(
    rows: list[dict[str, Any]],
    import_artifact: dict[str, Any],
    protected_errors: list[str] | None = None,
) -> tuple[str, dict[str, bool]]:
    """Return one stable gate state and its independently auditable checks."""

    protected_errors = protected_errors or []
    required_count = len(rows)
    raw_count = int(import_artifact.get("raw_response_count", 0))
    missing = list(import_artifact.get("missing_references", []))
    checks = {
        "all_required_renderer_responses_present": raw_count >= required_count and not missing,
        "all_required_responses_structurally_parse": all(
            row.get("response_structurally_parsed", row["import_status"] == "accepted")
            for row in rows
        ),
        "all_responses_validated": all(row["validation_status"] == "validated" for row in rows),
        "no_provenance_or_hash_mismatch": all(
            row["provenance_complete"] and row["evidence_and_synthesis_locks_match"]
            for row in rows
        ),
        "no_cross_chapter_or_unsupported_ancestry": all(
            not set(row["rejection_codes"]).intersection({
                "CHAPTER_IDENTITY_MISMATCH", "OUT_OF_CHAPTER_VERSE_REFERENCE",
                "UNKNOWN_EVIDENCE_ID", "UNKNOWN_SYNTHESIS_ID", "SYNTHESIS_ANCESTRY_MISMATCH",
            })
            for row in rows
        ),
        "no_confidence_or_dispute_regression": all(
            not set(row["rejection_codes"]).intersection({
                "CONFIDENCE_EXCEEDS_EVIDENCE", "DISPUTED_AS_FACT",
                "INVALID_CONFIDENCE", "INVALID_INTERPRETATION_LEVEL",
            })
            for row in rows
        ),
        "no_protected_artifact_changes": not protected_errors,
        "available_synthesis_gaps_meaningfully_enriched": _available_improved(rows),
        "data_gap_controls_conservative": _data_gaps_conservative(rows),
        "rich_enough_controls_not_regressed": _rich_controls_stable(rows),
        "genealogy_list_controls_concise": _genealogy_concise(rows),
        "boilerplate_materially_reduced": _boilerplate_reduced(rows),
        "no_validation_safety_regression": all(
            row["validation_status"] == "validated"
            and not row["validation_errors"]
            and not row["synthesis_validation_errors"]
            for row in rows
        ),
    }
    if raw_count == 0:
        return "BLOCKED_BEFORE_PROSE", checks
    if missing or raw_count < required_count:
        return "PARTIAL_RESPONSES", checks
    validation_keys = (
        "all_required_responses_structurally_parse", "all_responses_validated",
        "no_provenance_or_hash_mismatch", "no_cross_chapter_or_unsupported_ancestry",
        "no_confidence_or_dispute_regression", "no_protected_artifact_changes",
        "no_validation_safety_regression",
    )
    if not all(checks[key] for key in validation_keys):
        return "VALIDATION_FAILED", checks
    if not all(checks.values()):
        return "QUALITY_GATE_FAILED", checks
    return "CANARY_PASS", checks


def _comparison_deltas(before, after, synthesis_unit_count) -> dict[str, Any]:
    if after is None:
        return {
            "section_delta": None,
            "evidence_use_delta": None,
            "synthesis_use_percentage": None,
            "word_count_delta": None,
            "boilerplate_removed": None,
            "richness_classification_changed": None,
        }
    return {
        "section_delta": after["section_count"] - before["section_count"],
        "evidence_use_delta": after["unique_evidence_ids_consumed"] - before["unique_evidence_ids_consumed"],
        "synthesis_use_percentage": round(
            100 * after.get("unique_synthesis_ids_consumed", 0) / synthesis_unit_count, 2
        ) if synthesis_unit_count else 100.0,
        "word_count_delta": after["commentary_prose_word_count"] - before["commentary_prose_word_count"],
        "boilerplate_removed": bool(before.get("boilerplate_detected")) and not after.get("boilerplate_detected", False),
        "richness_classification_changed": before["richness_status"] != after["richness_status"],
    }


def _available_improved(rows: list[dict[str, Any]]) -> bool:
    available = [
        row for row in rows
        if row["before"]["evidence_availability"] == "AVAILABLE"
        and row["before"]["richness_status"] == "SYNTHESIS_GAP"
    ]
    return bool(available) and all(
        row["after"] is not None
        and (
            row["after"]["richness_status"] == "RICH_ENOUGH"
            or (
                row["deltas"]["evidence_use_delta"] > 0
                and row["deltas"]["synthesis_use_percentage"] >= 50
                and not row["after"].get("boilerplate_detected", False)
            )
        )
        for row in available
    )


def _data_gaps_conservative(rows: list[dict[str, Any]]) -> bool:
    gaps = [row for row in rows if row["before"]["evidence_availability"] == "DATA_GAP"]
    return all(
        row["after"] is not None
        and row["after"]["commentary_prose_word_count"] <= 180
        and row["after"]["unique_evidence_ids_consumed"] == 0
        for row in gaps
    )


def _genealogy_concise(rows: list[dict[str, Any]]) -> bool:
    controls = [row for row in rows if row["reference"] in {"1 Chronicles 8", "Numbers 3"}]
    return all(
        row["after"] is not None and row["after"]["commentary_prose_word_count"] <= 250
        for row in controls
    )


def _rich_controls_stable(rows: list[dict[str, Any]]) -> bool:
    controls = [row for row in rows if row["before"]["richness_status"] == "RICH_ENOUGH"]
    return all(
        row["after"] is not None
        and row["after"]["richness_status"] == "RICH_ENOUGH"
        and row["after"]["unique_evidence_ids_consumed"]
        >= max(0, row["before"]["unique_evidence_ids_consumed"] - 1)
        and not (row["after"].get("boilerplate_detected") and not row["before"].get("boilerplate_detected"))
        for row in controls
    )


def _boilerplate_reduced(rows: list[dict[str, Any]]) -> bool:
    if any(row["after"] is None for row in rows):
        return False
    before_count = sum(bool(row["before"].get("boilerplate_detected")) for row in rows)
    after_count = sum(bool(row["after"] and row["after"].get("boilerplate_detected")) for row in rows)
    return after_count == 0 if before_count == 0 else after_count < before_count


def _failure_layer(locked, synthesis, after, rejection_codes) -> str | None:
    infrastructure = {
        "PACKET_CONTENT_MISMATCH", "STALE_RESPONSE", "PROTECTED_ARTIFACT_CHANGED",
        "INFRASTRUCTURE_ERROR", "EVIDENCE_HASH_MISMATCH", "SYNTHESIS_HASH_MISMATCH",
        "PROMPT_VERSION_MISMATCH", "PACKET_ID_MISMATCH", "UNKNOWN_PACKET",
        "MALFORMED_RESPONSE_JSON", "MALFORMED_RESPONSE_ENVELOPE",
        "MISSING_REQUIRED_FIELD", "NON_CANARY_RESPONSE", "DUPLICATE_RESPONSE",
    }
    if set(rejection_codes).intersection(infrastructure):
        return "INFRASTRUCTURE_GAP"
    if after is None and not rejection_codes:
        return "INFRASTRUCTURE_GAP"
    if locked["evidence_availability"] == "DATA_GAP":
        return "EVIDENCE_GAP"
    evidence_count = len(locked.get("evidence_ids", []))
    represented = len(synthesis.coverage.used_evidence_ids)
    if not synthesis.synthesis_units or (evidence_count >= 3 and represented / evidence_count < 0.35):
        return "SYNTHESIS_COMPILER_GAP"
    if set(rejection_codes).intersection({"SYNTHESIS_ANCESTRY_MISMATCH"}):
        return "VALIDATION_CONTRACT_GAP"
    if rejection_codes or (after and after["richness_status"] != "RICH_ENOUGH"):
        return "RENDERER_PROMPT_GAP"
    return None


def _render_comparison(artifact: dict[str, Any]) -> str:
    lines = ["# Commentary v1.2 canary comparison", "", f"Status: **{artifact['status']}**", "", "| Reference | Before | After | Validation |", "|---|---:|---:|---|"]
    for row in artifact["chapters"]:
        before = row["before"]["richness_status"]
        after = row["after"]["richness_status"] if row["after"] else "not run"
        lines.append(f"| {row['reference']} | {before} | {after} | {row['validation_status']} |")
    lines.extend([
        "",
        "A CANARY_PASS means ready for human review; it does not authorize bulk generation.",
        "",
    ])
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    _write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare")
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--reference")
    subparsers.add_parser("compare")
    subparsers.add_parser("gate")
    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare()
        elif args.command == "generate":
            result = generate(args.reference)
        elif args.command == "compare":
            result = compare()
        elif args.command == "gate":
            result = gate()
        else:
            result = export_manifest(args.output)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.command == "export":
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({key: result.get(key) for key in ("artifact_version", "status", "chapter_count", "scale_gate") if key in result}, indent=2))
    return 0 if result.get("status") not in {"VALIDATION_FAILED", "QUALITY_GATE_FAILED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
