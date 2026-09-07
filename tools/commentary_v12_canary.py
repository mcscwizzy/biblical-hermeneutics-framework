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

from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.generator import CommentaryGenerator
from bhf_agent.chapter_commentary.models import CommentaryGenerationRequest
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.storage import load_commentary, save_commentary
from bhf_agent.chapter_commentary.synthesis import (
    compile_chapter_synthesis,
    save_synthesis,
    validate_synthesis,
)
from bhf_agent.config import AgentConfig
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from bhf_web.forms import load_web_defaults


CANDIDATE_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment"
AUDIT_PATH = CANDIDATE_ROOT / "audit/commentary-richness-audit.json"
CANARY_ROOT = CANDIDATE_ROOT / "canary"
SYNTHESIS_ROOT = CANARY_ROOT / "synthesis"
COMMENTARY_ROOT = CANARY_ROOT / "commentary"
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
                "status": "READY_FOR_TERRA",
            }
        )
    artifact = {
        "artifact_version": "commentary-v1.2-canary-preflight-v1",
        "status": "READY_FOR_TERRA",
        "model_requirement": {"owner": "terra", "effort": "medium"},
        "candidate_only": True,
        "v1_1_protected_fingerprints_verified": True,
        "evidence_locked": True,
        "synthesis_locked": True,
        "chapter_count": len(rows),
        "chapters": rows,
    }
    _write_json(CANARY_ROOT / "canary-preflight.json", artifact)
    _write_json(
        CANDIDATE_ROOT / "candidate-state.json",
        {
            "pipeline_version": "commentary-v1.2-enrichment",
            "current_stage": "CANARY_READY_FOR_TERRA",
            "required_model": "terra",
            "required_effort": "medium",
            "full_bible_generation_authorized": False,
            "v1_1_mutated": False,
            "ckl_mutated": False,
            "canary_chapter_count": len(rows),
        },
    )
    return artifact


def generate(reference: str | None = None) -> dict[str, Any]:
    """Generate only locked canaries, refusing non-Terra substitutions."""

    preflight = _read_json(CANARY_ROOT / "canary-preflight.json")
    if preflight.get("status") != "READY_FOR_TERRA":
        raise RuntimeError("run prepare and obtain READY_FOR_TERRA first")
    config = load_web_defaults().config
    try:
        _require_terra_medium(config)
    except RuntimeError as exc:
        blocker = {
            "artifact_version": "commentary-v1.2-canary-generation-v1",
            "status": "BLOCKED",
            "blocker": "REQUIRED_MODEL_UNAVAILABLE",
            "required_model": "terra",
            "required_effort": "medium",
            "configured_model": config.model,
            "reason": str(exc),
            "chapters": [],
        }
        _write_json(CANARY_ROOT / "canary-generation.json", blocker)
        _write_json(
            CANDIDATE_ROOT / "candidate-state.json",
            {
                "pipeline_version": "commentary-v1.2-enrichment",
                "current_stage": "CANARY_BLOCKED_MODEL",
                "required_model": "terra",
                "required_effort": "medium",
                "blocked_reason": "REQUIRED_MODEL_UNAVAILABLE",
                "configured_model": config.model,
                "full_bible_generation_authorized": False,
                "v1_1_mutated": False,
                "ckl_mutated": False,
                "canary_chapter_count": len(preflight["chapters"]),
            },
        )
        raise
    generator = CommentaryGenerator(config)
    rows = []
    selected = [row for row in preflight["chapters"] if reference in (None, row["reference"])]
    if reference and not selected:
        raise RuntimeError(f"reference is not in the canary matrix: {reference}")
    for row in selected:
        result = generator.generate(
            CommentaryGenerationRequest(
                book=row["book"],
                chapter=row["chapter"],
                reference=row["reference"],
                evidence_hash=row["evidence_hash"],
                synthesis_hash=row["synthesis_hash"],
            )
        )
        if result.commentary is not None:
            path = save_commentary(result.commentary, COMMENTARY_ROOT)
        else:
            path = None
        result_row = {
            "reference": row["reference"],
            "status": result.status,
            "error": result.error,
            "path": path.relative_to(ROOT).as_posix() if path else None,
        }
        rows.append(result_row)
        if result.status != "validated":
            break
    artifact = {
        "artifact_version": "commentary-v1.2-canary-generation-v1",
        "model": config.model,
        "model_owner": "terra",
        "effort": "medium",
        "requested_count": len(selected),
        "completed_count": len(rows),
        "status": "PASS" if len(rows) == len(selected) and all(row["status"] == "validated" for row in rows) else "STOPPED",
        "chapters": rows,
    }
    _write_json(CANARY_ROOT / "canary-generation.json", artifact)
    return artifact


def compare() -> dict[str, Any]:
    preflight = _read_json(CANARY_ROOT / "canary-preflight.json")
    rows = []
    for locked in preflight["chapters"]:
        book, chapter = locked["book"], locked["chapter"]
        commentary = load_commentary(COMMENTARY_ROOT, book, chapter)
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
        validation_errors = list(getattr(commentary, "validation_errors", []) or [])
        unsupported = sum(
            any(code in error for code in (
                "UNKNOWN_EVIDENCE_ID", "UNKNOWN_SYNTHESIS_ID", "SYNTHESIS_ANCESTRY_MISMATCH",
                "INVENTED_SIGNIFICANCE", "UNSUPPORTED_ENTITY", "UNSUPPORTED_DATE",
            ))
            for error in validation_errors
        )
        metadata = commentary.generated_metadata.to_dict() if commentary and commentary.generated_metadata else {}
        rows.append(
            {
                "reference": locked["reference"],
                "before": locked["before"],
                "after": _metrics(after) if after else None,
                "validation_outcome": commentary.status if commentary else "not_run",
                "evidence_and_synthesis_locks_match": identity_ok,
                "synthesis_validation_errors": synthesis_errors,
                "synthesis_hash": synthesis.synthesis_hash,
                "commentary_prompt_version": metadata.get("commentary_prompt_version"),
                "unsupported_claim_count": unsupported,
                "provenance_complete": all(metadata.get(field) for field in REQUIRED_PROVENANCE),
                "validation_errors": validation_errors,
            }
        )
    gate_checks = {
        "all_canaries_generated": all(row["after"] is not None for row in rows),
        "all_validated": all(row["validation_outcome"] == "validated" for row in rows),
        "no_unsupported_claim_regressions": all(
            row["after"] is not None and row["unsupported_claim_count"] == 0 for row in rows
        ),
        "no_provenance_regressions": all(
            row["after"] is not None and row["provenance_complete"] for row in rows
        ),
        "all_hash_locks_match": all(row["evidence_and_synthesis_locks_match"] for row in rows),
        "no_entity_or_chapter_leakage_regressions": all(
            row["after"] is not None
            and not row["synthesis_validation_errors"]
            and not any(
                code in error
                for error in row["validation_errors"]
                for code in ("UNSUPPORTED_ENTITY", "CHAPTER_IDENTITY_MISMATCH", "OUT_OF_CHAPTER_VERSE_REFERENCE")
            )
            for row in rows
        ),
        "available_chapters_materially_improve": _available_improved(rows),
        "data_gaps_remain_conservative": _data_gaps_conservative(rows),
        "genealogy_remains_concise": _genealogy_concise(rows),
    }
    artifact = {
        "artifact_version": "commentary-v1.2-canary-comparison-v1",
        "status": "PASS" if all(gate_checks.values()) else "BLOCKED",
        "scale_gate": False if not all(gate_checks.values()) else True,
        "gate_checks": gate_checks,
        "chapters": rows,
    }
    _write_json(CANARY_ROOT / "canary-comparison.json", artifact)
    _write_text(CANARY_ROOT / "canary-comparison.md", _render_comparison(artifact))
    return artifact


def _metrics(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        key: row[key]
        for key in (
            "evidence_availability", "section_count", "commentary_block_count",
            "commentary_prose_char_count", "commentary_prose_word_count",
            "unique_evidence_ids_consumed", "richness_status",
        )
    }


def _require_terra_medium(config: AgentConfig) -> None:
    owner = os.environ.get("BHF_COMMENTARY_MODEL_OWNER", "").casefold()
    effort = os.environ.get("BHF_COMMENTARY_MODEL_EFFORT", "").casefold()
    model = str(config.model or "").casefold()
    if owner != "terra" or effort != "medium" or "terra" not in model:
        raise RuntimeError(
            "Canary prose requires Terra Medium; refusing configured model substitution "
            f"(model={config.model!r}, owner={owner or 'unset'!r}, effort={effort or 'unset'!r})"
        )


def _protected_v11_errors() -> list[str]:
    state = _read_json(V11_STATE)
    errors = []
    for relative, expected in state.get("protected_fingerprints", {}).items():
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        if actual != expected:
            errors.append(relative)
    return errors


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
                row["after"]["commentary_prose_word_count"]
                >= round(row["before"]["commentary_prose_word_count"] * 1.1)
                and row["after"]["unique_evidence_ids_consumed"]
                > row["before"]["unique_evidence_ids_consumed"]
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
    row = next(value for value in rows if value["reference"] == "1 Chronicles 8")
    return bool(row["after"] and row["after"]["commentary_prose_word_count"] <= 250)


def _render_comparison(artifact: dict[str, Any]) -> str:
    lines = ["# Commentary v1.2 canary comparison", "", f"Status: **{artifact['status']}**", "", "| Reference | Before | After | Validation |", "|---|---:|---:|---|"]
    for row in artifact["chapters"]:
        before = row["before"]["richness_status"]
        after = row["after"]["richness_status"] if row["after"] else "not run"
        lines.append(f"| {row['reference']} | {before} | {after} | {row['validation_outcome']} |")
    lines.extend(["", "Scale generation remains disabled unless every machine-readable gate check passes.", ""])
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
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare()
        elif args.command == "generate":
            result = generate(args.reference)
        else:
            result = compare()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({key: result.get(key) for key in ("artifact_version", "status", "chapter_count", "scale_gate") if key in result}, indent=2))
    return 0 if result.get("status") not in {"BLOCKED", "STOPPED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
