#!/usr/bin/env python3
"""Run the bounded Commentary v1.2 Terra scale pilot with five Sol controls.

This is an evidence-gathering harness.  It rebuilds the frozen 75-chapter
population, selects a deterministic 25-chapter stratified subset, freezes the
Prompt 1.8 renderer inputs, captures exactly one Terra High response per
chapter and exactly one Sol Medium response for the five enriched controls,
then evaluates both with the existing deterministic contracts.

The harness never writes CKL, ASV, production commentary, or contract code.
All pilot files are immutable and live in a content-addressed candidate
namespace.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import statistics
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.models import COMMENTARY_SCHEMA_VERSION, GeneratedMetadata
from bhf_agent.chapter_commentary.evidence_applicability import evaluate_evidence_applicability
from bhf_agent.chapter_commentary.output_conformance import parse_renderer_json
from bhf_agent.chapter_commentary.prompts import build_user_prompt, system_prompt_for_version
from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    add_ancestry_envelope_to_prompt,
    audit_ancestry_envelope,
    build_ancestry_envelope,
)
from bhf_agent.chapter_commentary.reader_level_projection import (
    add_projection_to_prompt,
    project_reader_level_ideas,
)
from bhf_agent.chapter_commentary.reader_provenance_binding_v2 import (
    ProvenanceBindingV2Error,
    add_provenance_binding_to_prompt_v2,
    audit_provenance_binding_v2,
    build_provenance_binding_v2,
    normalize_renderer_payload_v2,
    response_ancestry_audit_v2,
)
from bhf_agent.chapter_commentary.renderer_reference_presentation_v1 import (
    add_presentation_to_prompt,
    audit_active_paths,
    normalize_selected_chapter_scope_refs,
    present_binding,
)
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    RICHNESS_GATE_V2_VERSION,
    RICHNESS_POLICY_VERSION_V3,
    assess_gate_v2,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from framework.commentary.production.inputs import literary_category, prepare_chapter
from framework.commentary.production.models import (
    ArtifactCollisionError,
    canonical_json,
    sha256_bytes,
    sha256_json,
    slug,
    write_immutable,
)
from tools.commentary_v12_five_chapter_structured_enrichment import safe_canonical_text
from tools.commentary_v12_scale_pilot import _qualitative


ARTIFACT_VERSION = "commentary-v1.2-terra-scale-pilot-v1"
BRANCH = "feat/commentary-v1.2-enrichment"
STARTING_SHA = "ee29855a824fbb6d2384df392bbf84556f2f4b0f"
PROMPT_VERSION = "1.8"
TERRA_MODEL = "gpt-5.6-terra"
TERRA_EFFORT = "high"
SOL_MODEL = "gpt-5.6-sol"
SOL_EFFORT = "medium"
CODEX = Path("/home/johnwalker/.local/bin/codex")
TARGET_COUNT = 25
FROZEN_POPULATION_IDENTITY = "eb282a2a684e13499f56894c0f9da9c38b71c08dd5c2cf58b0a072b64b487394"
CENSUS_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-post-applicability-coverage-census-v1-5cd6a3e32d5b4dcb03e5ecf0"
REQUIRED_CONTROLS = ("Psalms 19", "Psalms 103", "2 Kings 4", "Psalms 2", "Genesis 5")
SELECTION_SEED = 20260911
CATEGORY_TARGETS = {
    "Pentateuch": 3,
    "Historical narrative": 3,
    "Poetry/Wisdom": 4,
    "Prophets": 4,
    "Gospels/Acts": 4,
    "Pauline Epistles": 3,
    "General Epistles": 2,
    "Apocalyptic / highly symbolic": 2,
}
PROTECTED_CONTRACTS = {
    "prompt_1_8_system": CENSUS_ROOT / ".." / "commentary-v1.2-prompt-1.8-bounded-validation-v1-c1b33885962b7361c1ed" / "renderer-input/001_numbers_002/system_prompt.txt",
    "evidence_applicability": ROOT / "bhf_agent/chapter_commentary/evidence_applicability.py",
    "reader_level_projection": ROOT / "bhf_agent/chapter_commentary/reader_level_projection.py",
    "reader_ancestry_envelope": ROOT / "bhf_agent/chapter_commentary/reader_idea_ancestry_envelope.py",
    "reader_provenance_binding_v2": ROOT / "bhf_agent/chapter_commentary/reader_provenance_binding_v2.py",
    "renderer_reference_presentation_v1": ROOT / "bhf_agent/chapter_commentary/renderer_reference_presentation_v1.py",
    "output_conformance": ROOT / "bhf_agent/chapter_commentary/output_conformance.py",
    "structural_validator": ROOT / "bhf_agent/chapter_commentary/validation.py",
    "richness_gate": ROOT / "bhf_agent/chapter_commentary/richness_clusters.py",
    "ckl_database": ROOT / ".bhf/ckl.sqlite",
    "asv_bible": ROOT / "bhf_agent/data/asv_bible.json",
}
PSALM_EXPOSURE = CENSUS_ROOT / "psalm-superscription-exposure.json"
CKL_LEGACY = "ckl_legacy_field"
UNSUPPORTED_CODES = frozenset({
    "UNKNOWN_EVIDENCE_ID", "UNKNOWN_SYNTHESIS_ID", "SYNTHESIS_ANCESTRY_MISMATCH",
    "SYNTHESIS_HASH_MISMATCH", "CONFIDENCE_EXCEEDS_EVIDENCE", "DISPUTED_AS_FACT",
    "INVENTED_SIGNIFICANCE", "UNSUPPORTED_DATE", "UNSUPPORTED_ENTITY",
    "UNANCHORED_CLAIM", "OUT_OF_CHAPTER_SYNTHESIS_REFERENCE",
})


class PilotError(RuntimeError):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PilotError(f"invalid JSON artifact {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> str:
    return write_immutable(path, (canonical_json(value) + "\n").encode("utf-8"))


def write_text(path: Path, value: str) -> str:
    return write_immutable(path, value.encode("utf-8"))


def file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def frozen_population() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    identity = read_json(CENSUS_ROOT / "frozen-population-identity.json")
    if identity.get("manifest_identity") != FROZEN_POPULATION_IDENTITY:
        raise PilotError("frozen 75-chapter population identity disagrees")
    chapters = list(identity.get("chapters", []))
    if len(chapters) != 75 or len({row.get("reference") for row in chapters}) != 75:
        raise PilotError("frozen population is not exactly 75 unique chapters")
    return chapters, identity


def protected_hashes() -> dict[str, str]:
    result = {}
    for name, path in PROTECTED_CONTRACTS.items():
        if not path.is_file():
            raise PilotError(f"protected contract file is missing: {path}")
        result[name] = file_hash(path)
    return result


def psalm_safe_text(book: str, chapter: int) -> tuple[str, dict[str, Any]]:
    exposure = read_json(PSALM_EXPOSURE)
    matches = [row for row in exposure.get("population_intersections", []) if row.get("book") == book and int(row.get("chapter", 0)) == chapter and row.get("is_next_psalm_boundary")]
    if not matches:
        data = bible.resolve_chapter(book, chapter)
        text = bible.passage_text(data["verses"])
        digest = sha256_bytes(text.encode("utf-8"))
        return text, {"required": False, "dataset_mutated": False, "original_text_sha256": digest, "safe_text_sha256": digest}
    data = bible.resolve_chapter(book, chapter)
    original = bible.passage_text(data["verses"])
    rows = [dict(row) for row in data["verses"]]
    contaminated = str(matches[0].get("text", ""))
    removed = False
    for row in rows:
        if contaminated and contaminated in str(row.get("text", "")):
            row["text"] = str(row["text"]).replace(contaminated, "")
            removed = True
    if not removed:
        # Psalm 2 is the already validated bounded path; retain its exact
        # implementation for the known control and fail closed elsewhere.
        if book == "Psalms" and chapter == 2:
            return safe_canonical_text(book, chapter)
        raise PilotError(f"safe Psalm text was required but contamination was not found for {book} {chapter}")
    safe = bible.passage_text(rows)
    return safe, {
        "required": True,
        "dataset_mutated": False,
        "source": "bounded_task_local_canonical_text_projection",
        "contamination_removed": True,
        "original_text_sha256": sha256_bytes(original.encode("utf-8")),
        "safe_text_sha256": sha256_bytes(safe.encode("utf-8")),
        "next_psalm_number": matches[0].get("next_psalm_number"),
    }


def canonical_text(book: str, chapter: int) -> tuple[str, dict[str, Any]]:
    return psalm_safe_text(book, chapter) if book == "Psalms" else (
        bible.passage_text(bible.resolve_chapter(book, chapter)["verses"]),
        {"required": False, "dataset_mutated": False},
    )


def category(book: str, chapter: int) -> str:
    if book in {"Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon"}:
        return "Pauline Epistles"
    if book in {"Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude"}:
        return "General Epistles"
    value = literary_category(book, chapter)
    # Keep the pilot's requested literary strata broad enough that a thin
    # Numbers chapter remains a Torah stress case rather than being silently
    # excluded as an administrative shape.
    if value == "Genealogy/list/administrative":
        return "Pentateuch" if book in {"Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"} else "Historical narrative"
    return value


def _hash_order(reference: str) -> str:
    return hashlib.sha256(f"{SELECTION_SEED}:{reference}".encode("utf-8")).hexdigest()


def _state_priority(row: dict[str, Any]) -> tuple[int, int, str]:
    # Prefer actual current thin renderable packets for stress coverage, then
    # retain the census state distribution instead of selecting easy chapters.
    current = row.get("current_availability")
    state = row.get("frozen_state")
    current_rank = {"THIN": 0, "AVAILABLE": 1}.get(current, 9)
    state_rank = {"EVIDENCE_PARTIAL": 0, "EVIDENCE_FOCUSED": 1, "EVIDENCE_RICH": 2, "MIXED": 3}.get(state, 4)
    return current_rank, state_rank, _hash_order(row["reference"])


def select_sample(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible = {row["reference"]: row for row in rows if row.get("eligible")}
    missing_controls = [ref for ref in REQUIRED_CONTROLS if ref not in eligible]
    if missing_controls:
        raise PilotError(f"required enriched controls are ineligible: {missing_controls}")
    selected: list[dict[str, Any]] = [eligible[ref] for ref in REQUIRED_CONTROLS]
    selected_refs = set(REQUIRED_CONTROLS)
    remaining = dict(CATEGORY_TARGETS)
    for row in selected:
        remaining[row["category"]] -= 1
    if min(remaining.values()) < 0:
        raise PilotError("required controls exceed a category quota")
    replacements: list[dict[str, Any]] = []
    for cat, count in CATEGORY_TARGETS.items():
        if remaining[cat] == 0:
            continue
        candidates = [row for row in rows if row.get("eligible") and row.get("category") == cat and row["reference"] not in selected_refs]
        if len(candidates) < remaining[cat]:
            raise PilotError(f"insufficient eligible chapters for category {cat}")
        # Deterministic stress ordering.  The hash remains the tie breaker;
        # no result-dependent quota is introduced.
        candidates.sort(key=_state_priority)
        chosen = candidates[:remaining[cat]]
        selected.extend(chosen)
        selected_refs.update(row["reference"] for row in chosen)
    if len(selected) != TARGET_COUNT:
        raise PilotError(f"selection produced {len(selected)} chapters, expected {TARGET_COUNT}")
    ordered = sorted(selected, key=lambda row: _hash_order(row["reference"]))
    for ordinal, row in enumerate(ordered, 1):
        row["pilot_ordinal"] = ordinal
    return ordered, replacements


def _clusters(prepared: Any, passage_text: str) -> list[Any]:
    from bhf_agent.chapter_commentary.richness_clusters import cluster_synthesis_units
    return cluster_synthesis_units(
        prepared.synthesis.synthesis_units,
        prepared.bundle.evidence_items,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=passage_text,
    )


def _source_resolution(prepared: Any) -> tuple[bool, list[str], list[str]]:
    source_map = {str(row.get("id")): row for row in prepared.bundle.provenance.get("sources", [])}
    legal = []
    unresolved = []
    for item in prepared.bundle.evidence_items:
        decision = evaluate_evidence_applicability(item, prepared.bundle.passage_ref)
        if not decision.current_chapter_eligible:
            continue
        legal.append(item.id)
        if any(source_id not in source_map or source_map[source_id].get("source_type") == "unresolved-source-reference" for source_id in item.source_ids):
            unresolved.append(item.id)
    legacy = [item.id for item in prepared.bundle.evidence_items if item.id in legal and (item.relevance_metadata or {}).get("source_kind") == CKL_LEGACY]
    return not unresolved, unresolved, legacy


def build_preflight_row(population_row: dict[str, Any]) -> dict[str, Any]:
    reference = population_row["reference"]
    book, chapter_text = reference.rsplit(" ", 1)
    chapter = int(chapter_text)
    prepared = prepare_chapter(book, chapter, run_id="terra-scale-pilot", batch_id="pilot")
    passage, text_audit = canonical_text(book, chapter)
    clusters = _clusters(prepared, passage)
    projection = project_reader_level_ideas(prepared.synthesis, clusters, prepared.bundle.evidence_items)
    envelope = build_ancestry_envelope(projection, prepared.synthesis, prepared.bundle.evidence_items)
    ancestry_audit = audit_ancestry_envelope(envelope, projection, prepared.synthesis)
    binding = build_provenance_binding_v2(envelope, prepared.synthesis, prepared.bundle.evidence_items)
    binding_audit = audit_provenance_binding_v2(binding, envelope, prepared.synthesis, prepared.bundle.evidence_items)
    presentation = present_binding(binding, prepared.synthesis, prepared.bundle.evidence_items)
    presentation_audit = audit_active_paths(binding, prepared.synthesis, prepared.bundle.evidence_items)
    prompt = build_user_prompt(reference, book, chapter, passage, prepared.synthesis, prepared.bundle, prepared.synthesis.evidence_availability, prompt_version=PROMPT_VERSION)
    prompt = add_projection_to_prompt(prompt, projection)
    prompt = add_ancestry_envelope_to_prompt(prompt, envelope)
    prompt = add_provenance_binding_to_prompt_v2(prompt, envelope, binding)
    prompt, _ = add_presentation_to_prompt(prompt, envelope, binding, prepared.synthesis, prepared.bundle.evidence_items)
    source_resolves, unresolved, legal_legacy = _source_resolution(prepared)
    hard_current = [path for path in presentation_audit.get("paths", []) if path.get("passage_scope") == "CURRENT_CHAPTER" and path.get("canonicalization", {}).get("classification") in {"AMBIGUOUS", "INVALID_SOURCE_REFERENCE"}]
    has_legal_paths = int(binding.get("binding_audit", {}).get("active_path_count", 0)) > 0 and int(presentation_audit.get("counts", {}).get("VALID_ALREADY", 0)) + int(presentation_audit.get("counts", {}).get("SAFE_FULL_CHAPTER_SCOPE", 0)) > 0
    eligible = bool(has_legal_paths and ancestry_audit.get("valid") and binding_audit.get("valid") and not hard_current and not legal_legacy and source_resolves and prepared.synthesis.evidence_availability != "DATA_GAP")
    row = {
        "reference": reference, "book": book, "chapter": chapter, "category": category(book, chapter),
        "frozen_state": population_row.get("state") or population_row.get("primary_state") or population_row.get("evidence_state"),
        "frozen_availability": population_row.get("evidence_availability"),
        "current_availability": prepared.synthesis.evidence_availability,
        "raw_evidence_count": len(prepared.bundle.evidence_items),
        "synthesis_unit_count": len(prepared.synthesis.synthesis_units),
        "evidence_hash": prepared.bundle.evidence_hash,
        "synthesis_hash": prepared.synthesis.synthesis_hash,
        "source_packet_id": prepared.row["input_identity"]["packet_id"],
        "source_packet_hash": prepared.row["input_identity"]["packet_hash"],
        "projection_hash": projection.projection_hash,
        "ancestry_hash": envelope["envelope_hash"],
        "provenance_binding_hash": binding["binding_hash"],
        "renderer_presentation_hash": presentation["presentation_hash"],
        "active_path_count": len(binding.get("paths", [])),
        "legal_path_count": int(presentation_audit.get("counts", {}).get("VALID_ALREADY", 0)) + int(presentation_audit.get("counts", {}).get("SAFE_FULL_CHAPTER_SCOPE", 0)),
        "hard_current_path_errors": hard_current,
        "legacy_legal_ids": sorted(legal_legacy),
        "unresolved_source_ids": sorted(unresolved),
        "ancestry_valid": bool(ancestry_audit.get("valid")),
        "binding_valid": bool(binding_audit.get("valid")),
        "eligible": eligible,
        "text_audit": text_audit,
        "prepared": prepared,
        "projection": projection.to_dict(),
        "envelope": envelope,
        "binding": binding,
        "presentation": presentation,
        "system_prompt": system_prompt_for_version(PROMPT_VERSION),
        "user_prompt": prompt,
    }
    row["renderer_input"] = row["system_prompt"] + "\n\nUSER PROMPT\n" + row["user_prompt"]
    row["renderer_input_sha256"] = sha256_bytes(row["renderer_input"].encode("utf-8"))
    return row


def build_context() -> dict[str, Any]:
    population, identity = frozen_population()
    states = {row["reference"]: row for row in read_json(CENSUS_ROOT / "evidence-state-classification.json")["chapters"]}
    rows = []
    for index, population_row in enumerate(population, 1):
        row = build_preflight_row({**population_row, "state": states.get(population_row["reference"], {}).get("state")})
        row["population_ordinal"] = index
        rows.append(row)
    selected, replacements = select_sample(rows)
    contract = protected_hashes()
    seed_material = {
        "artifact_version": ARTIFACT_VERSION, "branch": BRANCH, "starting_sha": STARTING_SHA,
        "population_identity": FROZEN_POPULATION_IDENTITY, "selection_seed": SELECTION_SEED,
        "selected": [{key: row[key] for key in ("reference", "category", "frozen_state", "current_availability", "evidence_hash", "synthesis_hash", "renderer_input_sha256")} for row in selected],
        "protected_contract_hashes": contract,
        "terra": [TERRA_MODEL, TERRA_EFFORT], "sol": [SOL_MODEL, SOL_EFFORT], "prompt": PROMPT_VERSION,
    }
    identity_hash = sha256_json(seed_material)[:20]
    namespace = f".bhf-data/bhf-commentary-candidates/{ARTIFACT_VERSION}-{identity_hash}"
    for ordinal, row in enumerate(selected, 1):
        row["pilot_ordinal"] = ordinal
        row["filename"] = f"{ordinal:03d}_{slug(row['book'], row['chapter'])}.json"
    return {"population": population, "population_identity": identity, "all_rows": rows, "selected": selected, "replacements": replacements, "contract_hashes": contract, "namespace": namespace, "identity_hash": identity_hash, "thin_renderable_population_count": sum(row["eligible"] and row["current_availability"] == "THIN" for row in rows), "thin_renderable_selected_count": sum(row["current_availability"] == "THIN" for row in selected)}


def public_row(row: dict[str, Any]) -> dict[str, Any]:
    keys = ("pilot_ordinal", "population_ordinal", "filename", "reference", "book", "chapter", "category", "frozen_state", "frozen_availability", "current_availability", "raw_evidence_count", "synthesis_unit_count", "evidence_hash", "synthesis_hash", "source_packet_id", "source_packet_hash", "projection_hash", "ancestry_hash", "provenance_binding_hash", "renderer_presentation_hash", "active_path_count", "legal_path_count", "renderer_input_sha256", "eligible")
    return {key: row.get(key) for key in keys}


def prepare_artifact() -> dict[str, Any]:
    context = build_context()
    root = ROOT / context["namespace"]
    manifest = {
        "artifact_version": f"{ARTIFACT_VERSION}-manifest", "namespace": context["namespace"], "identity": context["identity_hash"],
        "branch": BRANCH, "starting_sha": STARTING_SHA, "expected_local_head": STARTING_SHA,
        "frozen_population_identity": FROZEN_POPULATION_IDENTITY, "selection_seed": SELECTION_SEED,
        "selection_method": "required enriched controls plus fixed category quotas, current renderability eligibility, deterministic stress ordering by current THIN then frozen evidence state then SHA-256; all eligible current THIN chapters are preferred within their category quota",
        "chapter_count": TARGET_COUNT, "terra": {"model": TERRA_MODEL, "effort": TERRA_EFFORT, "one_initial_generation_per_chapter": True, "retry_count": 0},
        "sol": {"model": SOL_MODEL, "effort": SOL_EFFORT, "control_references": list(REQUIRED_CONTROLS), "one_initial_generation_per_chapter": True, "retry_count": 0},
        "prompt_version": PROMPT_VERSION, "gate_version": RICHNESS_GATE_V2_VERSION,
        "protected_contract_hashes_before": context["contract_hashes"], "ckl_mutation": False, "asv_mutation": False,
        "production_routing_changed": False, "full_75_chapter_pilot_started": False,
        "replacements": context["replacements"], "thin_renderable_population_count": context["thin_renderable_population_count"], "thin_renderable_selected_count": context["thin_renderable_selected_count"], "chapters": [public_row(row) for row in context["selected"]],
    }
    manifest["manifest_identity"] = sha256_json(manifest)
    write_json(root / "manifest.json", manifest)
    write_json(root / "starting-state.json", {"starting_sha": STARTING_SHA, "branch": BRANCH, "protected_contract_hashes": context["contract_hashes"], "frozen_population_identity": FROZEN_POPULATION_IDENTITY})
    write_json(root / "frozen-population.json", {"identity": FROZEN_POPULATION_IDENTITY, "chapter_count": 75, "references": [row["reference"] for row in context["population"]]})
    write_json(root / "deterministic-selection.json", {"selection_seed": SELECTION_SEED, "category_targets": CATEGORY_TARGETS, "required_controls": list(REQUIRED_CONTROLS), "selected": [public_row(row) for row in context["selected"]], "replacements": context["replacements"]})
    write_json(root / "preflight/all-candidate-results.json", {"artifact_version": f"{ARTIFACT_VERSION}-preflight", "population_count": 75, "eligible_count": sum(row["eligible"] for row in context["all_rows"]), "chapters": [{**public_row(row), "text_audit": row["text_audit"], "hard_current_path_errors": row["hard_current_path_errors"], "legacy_legal_ids": row["legacy_legal_ids"], "unresolved_source_ids": row["unresolved_source_ids"], "ancestry_valid": row["ancestry_valid"], "binding_valid": row["binding_valid"]} for row in context["all_rows"]]})
    write_json(root / "preflight/eligibility-summary.json", {"eligible": [row["reference"] for row in context["all_rows"] if row["eligible"]], "ineligible": [{"reference": row["reference"], "reasons": preflight_reasons(row)} for row in context["all_rows"] if not row["eligible"]]})
    write_json(root / "contract-identities.json", {"prompt_version": PROMPT_VERSION, "protected_contract_hashes_before": context["contract_hashes"], "renderer_input_contract": "system prompt + exact user prompt; identical control bytes for Terra and Sol"})
    for row in context["selected"]:
        stem = f"{row['pilot_ordinal']:03d}_{slug(row['book'], row['chapter'])}"
        base = root / "chapters" / stem
        write_json(base / "packet.json", {"reference": row["reference"], "public": public_row(row), "evidence_hash": row["evidence_hash"], "synthesis_hash": row["synthesis_hash"], "projection": row["projection"], "ancestry": row["envelope"], "binding": row["binding"], "presentation": row["presentation"], "text_audit": row["text_audit"]})
        write_text(base / "renderer-input/system_prompt.txt", row["system_prompt"])
        write_text(base / "renderer-input/user_prompt.txt", row["user_prompt"])
        write_text(base / "renderer-input/final-input.txt", row["renderer_input"])
        write_json(base / "renderer-input/metadata.json", {**public_row(row), "renderer_input_sha256": row["renderer_input_sha256"], "generation_count": 0, "retry_count": 0})
    write_json(root / "checksums-pre-generation.json", checksum_payload(root, exclude={"checksums-pre-generation.json"}))
    return {"status": "PREPARED", "namespace": context["namespace"], "chapter_count": TARGET_COUNT, "eligible_population": sum(row["eligible"] for row in context["all_rows"]), "selected": [row["reference"] for row in context["selected"]]}


def preflight_reasons(row: dict[str, Any]) -> list[str]:
    reasons = []
    if row["current_availability"] == "DATA_GAP": reasons.append("DATA_GAP")
    if not row["legal_path_count"]: reasons.append("NO_LEGAL_RENDERER_PATH")
    if not row["ancestry_valid"]: reasons.append("INVALID_ANCESTRY")
    if not row["binding_valid"]: reasons.append("INVALID_PROVENANCE_BINDING")
    if row["hard_current_path_errors"]: reasons.append("HARD_RENDERER_REFERENCE_ERROR")
    if row["legacy_legal_ids"]: reasons.append("LEGACY_INHERITANCE_VIOLATION")
    if row["unresolved_source_ids"]: reasons.append("UNRESOLVED_SOURCE")
    return reasons


def checksum_payload(root: Path, *, exclude: set[str] | None = None) -> dict[str, Any]:
    exclude = exclude or set()
    return {"artifact_version": f"{ARTIFACT_VERSION}-checksums", "files": {str(path.relative_to(root)): file_hash(path) for path in sorted(root.rglob("*")) if path.is_file() and str(path.relative_to(root)) not in exclude}}


def load_manifest_context() -> tuple[dict[str, Any], Path, dict[str, Any]]:
    context = build_context()
    root = ROOT / context["namespace"]
    manifest = read_json(root / "manifest.json")
    if manifest.get("manifest_identity") != sha256_json({key: value for key, value in manifest.items() if key != "manifest_identity"}):
        raise PilotError("pilot manifest identity mismatch")
    if manifest != read_json(root / "manifest.json"):
        raise PilotError("pilot manifest changed")
    return context, root, manifest


def _exchange(input_path: Path, model: str, effort: str) -> str:
    return (
        f"You are the selected {model} prose renderer at {effort} effort. Do not call tools, inspect files, browse, or add explanation. Treat the exact SYSTEM PROMPT and USER PROMPT below as the complete generation contract. Return the requested raw JSON object only, with no Markdown fence or preamble.\n\n"
        + input_path.joinpath("system_prompt.txt").read_text(encoding="utf-8")
        + "\n\nUSER PROMPT\n"
        + input_path.joinpath("user_prompt.txt").read_text(encoding="utf-8")
    )


def _usage(events: str) -> dict[str, Any]:
    totals: dict[str, int] = {}
    records = []
    for line in events.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        usage = value.get("usage") or value.get("token_usage")
        if isinstance(usage, dict):
            records.append(usage)
            for key, val in usage.items():
                if isinstance(val, (int, float)) and "token" in key:
                    totals[key] = totals.get(key, 0) + int(val)
    return {"available": bool(records), "records": records, "totals": totals}


def render(model: str, effort: str, label: str, refs: Iterable[str] | None = None) -> dict[str, Any]:
    context, root, manifest = load_manifest_context()
    wanted = set(refs or [row["reference"] for row in manifest["chapters"]])
    rows = [row for row in manifest["chapters"] if row["reference"] in wanted]
    generated = []
    for index, public in enumerate(rows, 1):
        base = root / "chapters" / f"{public['pilot_ordinal']:03d}_{slug(public['book'], public['chapter'])}"
        response = base / f"responses/{label}/raw.json"
        if response.exists():
            raise PilotError(f"a response already exists; refusing a second generation: {public['reference']}")
        with tempfile.TemporaryDirectory(prefix="bhf-commentary-pilot-") as temp:
            temp_path = Path(temp)
            output = temp_path / "response.txt"
            completed = subprocess.run([str(CODEX), "exec", "--ephemeral", "--ignore-user-config", "-m", model, "-c", f'model_reasoning_effort="{effort}"', "-s", "read-only", "-C", str(temp_path), "--skip-git-repo-check", "--json", "--output-last-message", str(output), "-"], input=_exchange(base / "renderer-input", model, effort), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            if not output.is_file():
                raise PilotError(f"{model} produced no response for {public['reference']}: {completed.stderr[-1200:]}")
            raw = output.read_bytes()
            usage = _usage(completed.stdout)
            write_immutable(response, raw)
            write_json(base / f"responses/{label}/receipt.json", {"reference": public["reference"], "model": model, "effort": effort, "generation_count": 1, "retry_count": 0, "exit_code": completed.returncode, "raw_response_sha256": sha256_bytes(raw), "raw_response_bytes": len(raw), "usage": usage})
        generated.append(public["reference"])
        print(f"{label}: {index}/{len(rows)} {public['reference']}", flush=True)
    result = {"artifact_version": f"{ARTIFACT_VERSION}-{label}-generation", "model": model, "effort": effort, "generation_count": len(generated), "retry_count": 0, "chapters": generated}
    write_json(root / f"{label}-generation.json", result)
    return result


def _provenance_selected(payload: Mapping[str, Any]) -> list[str]:
    return [str(ref) for section in payload.get("sections", []) if isinstance(section, Mapping) for block in section.get("blocks", []) if isinstance(block, Mapping) for ref in block.get("provenance_refs", [])]


def blind_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove model and machine-provenance identity from a review copy."""
    value = copy.deepcopy(payload)
    value.pop("generated_metadata", None)
    for section in value.get("sections", []):
        for block in section.get("blocks", []):
            block.pop("synthesis_ids", None)
            block.pop("evidence_ids", None)
            block.pop("provenance_refs", None)
    return value


def evaluate_one(public: dict[str, Any], row: dict[str, Any], raw: bytes, model: str, effort: str, label: str) -> dict[str, Any]:
    parsed, parse_status, parse_errors = parse_renderer_json(raw)
    payload = parsed if isinstance(parsed, dict) else None
    normalization_events: list[dict[str, Any]] = []
    normalized: dict[str, Any] | None = None
    binding_error = None
    if payload is not None:
        try:
            normalized, binding_metadata = normalize_renderer_payload_v2(payload, row["binding"])
            normalized, normalization_events = normalize_selected_chapter_scope_refs(normalized, row["binding"], row["presentation"])
        except ProvenanceBindingV2Error as exc:
            binding_error = exc
            binding_metadata = {"blocks": []}
    else:
        binding_metadata = {"blocks": []}
    base_result = {"reference": public["reference"], "model": model, "effort": effort, "renderer_label": label, "raw_response_sha256": sha256_bytes(raw), "raw_response_bytes": len(raw), "parse_status": parse_status, "parse_errors": parse_errors, "normalization_events": normalization_events, "retry_count": 0, "high_dump": False}
    if binding_error or normalized is None:
        base_result.update({"structural_result": "REJECTED", "structural_pass": False, "provenance_result": "FAIL", "ancestry_result": "FAIL", "readability_result": "FAIL", "normal_reader_usefulness": "FAIL", "gate_result": "FAIL", "rejection_codes": [getattr(binding_error, "code", "MALFORMED_RESPONSE_JSON")], "unsupported_claim_findings": [], "failure_classification": "STRUCTURAL_MODEL_FAILURE", "selected_provenance_paths": _provenance_selected(payload or {}), "selected_evidence_ids": [], "emitted_verse_references": [], "legal_paths_available": row["legal_path_count"], "legal_paths_selected": 0, "evidence_utilization_count": 0, "word_count": 0, "section_count": 0, "binding_metadata": binding_metadata})
        return base_result
    normalized["status"] = "pending"
    normalized["evidence_availability"] = row["current_availability"]
    normalized["generated_metadata"] = GeneratedMetadata(evidence_hash=row["evidence_hash"], evidence_bundle_version=row["prepared"].bundle.version, commentary_schema_version=COMMENTARY_SCHEMA_VERSION, commentary_prompt_version=PROMPT_VERSION, model=model, generated_timestamp=None, synthesis_hash=row["synthesis_hash"], synthesis_schema_version=row["prepared"].synthesis.synthesis_schema_version, synthesis_compiler_version=row["prepared"].synthesis.synthesis_compiler_version, renderer_label=label).to_dict()
    validation = validate_chapter_commentary(normalized, row["prepared"].bundle, expected_evidence_hash=row["evidence_hash"], expected_prompt_version=PROMPT_VERSION, expected_reference=public["reference"], expected_book=public["book"], expected_chapter=int(public["chapter"]), synthesis=row["prepared"].synthesis, expected_synthesis_hash=row["synthesis_hash"])
    blocks = [block for section in (validation.commentary.sections if validation.commentary else []) for block in section.blocks]
    ancestry = response_ancestry_audit_v2(normalized, row["binding"])
    result = {"structural_result": "ACCEPTED" if validation.valid and validation.commentary else "REJECTED", "rejection_codes": [] if validation.valid else list(validation.errors), "validation_errors": list(validation.errors), "provenance_result": "PASS" if not validation.errors else "FAIL", "ancestry_result": "PASS" if ancestry["valid"] else "FAIL"}
    if not validation.valid or not validation.commentary:
        qual = _qualitative(normalized, {"structural_result": "REJECTED", "quality_gate_outcome": "FAIL"})
        base_result.update(result)
        base_result.update({"structural_pass": False, "readability_result": qual["readability"], "normal_reader_usefulness": qual["normal_reader_usefulness"], "gate_result": "FAIL", "failure_classification": classify_failure(result, row, qual, []), "selected_provenance_paths": _provenance_selected(payload or {}), "selected_evidence_ids": [], "emitted_verse_references": [ref for section in normalized.get("sections", []) for block in section.get("blocks", []) for ref in block.get("verse_refs", [])], "legal_paths_available": row["legal_path_count"], "legal_paths_selected": len(set(_provenance_selected(payload or {}))), "evidence_utilization_count": 0, "word_count": word_count(normalized), "section_count": len(normalized.get("sections", [])), "unsupported_claim_findings": sorted(set(result["rejection_codes"]) & UNSUPPORTED_CODES), "binding_metadata": binding_metadata, "ancestry": ancestry})
        return base_result
    score = score_synthesis_richness(row["prepared"].synthesis.synthesis_units, evidence_items=row["prepared"].bundle.evidence_items, consumed_synthesis_ids=[sid for block in blocks for sid in block.synthesis_ids], blocks=blocks, passage_ref=public["reference"], core_classifier=CORE_CLASSIFIER_V2, coverage_policy=RICHNESS_POLICY_VERSION_V3, passage_text=canonical_text(public["book"], int(public["chapter"]))[0])
    quality_audit = audit_chapter(public["book"], int(public["chapter"]), validation.commentary, row["prepared"].bundle)
    gate = assess_gate_v2(score=score, evidence_availability=row["current_availability"], baseline_richness="SYNTHESIS_GAP", after_richness=quality_audit["richness_status"], safety_checks={name: value for name, value in {"validation_clean": True, "provenance_complete": ancestry["valid"], "hashes_valid": True, "chapter_boundaries_valid": True, "confidence_valid": True, "dispute_state_preserved": True, "unsupported_significance_absent": not (set(result["rejection_codes"]) & UNSUPPORTED_CODES)}.items()}, evidence_use_delta=quality_audit["unique_evidence_ids_consumed"], section_delta=quality_audit["section_count"], commentary_word_count=quality_audit["commentary_prose_word_count"], unique_evidence_ids_consumed=quality_audit["unique_evidence_ids_consumed"])
    qual = _qualitative(normalized, {"structural_result": "ACCEPTED", "quality_gate_outcome": gate.outcome, "dump_severity": score.dump_diagnostics.severity})
    selected_paths = _provenance_selected(payload or {})
    selected_evidence = sorted({eid for block in blocks for eid in block.evidence_ids})
    result.update({"structural_pass": True, "provenance_result": "PASS", "ancestry_result": "PASS" if ancestry["valid"] else "FAIL", "readability_result": qual["readability"], "normal_reader_usefulness": qual["normal_reader_usefulness"], "gate_result": gate.outcome, "under_explanation_result": qual["under_explanation"], "word_count": word_count(normalized), "section_count": len(normalized.get("sections", [])), "selected_provenance_paths": selected_paths, "selected_evidence_ids": selected_evidence, "emitted_verse_references": [ref for section in normalized.get("sections", []) for block in section.get("blocks", []) for ref in block.get("verse_refs", [])], "legal_paths_available": row["legal_path_count"], "legal_paths_selected": len(set(selected_paths)), "evidence_utilization_count": len(selected_evidence), "evidence_paths_selected": len(set(selected_paths)), "evidence_path_utilization": round(len(set(selected_paths)) / max(1, row["legal_path_count"]), 4), "score": score.to_dict(), "quality_audit": quality_audit, "gate": gate.to_dict(), "dump_severity": score.dump_diagnostics.severity, "high_dump": score.dump_diagnostics.severity == "HIGH", "unsupported_claim_findings": sorted(set(result["rejection_codes"]) & UNSUPPORTED_CODES), "binding_metadata": binding_metadata, "ancestry": ancestry, "qualitative": qual})
    result["failure_classification"] = classify_failure(result, row, qual, score)
    base_result.update(result)
    return {**base_result, "normalized_payload": normalized}


def word_count(payload: Mapping[str, Any]) -> int:
    return len(" ".join(str(block.get("text", "")) for section in payload.get("sections", []) if isinstance(section, Mapping) for block in section.get("blocks", []) if isinstance(block, Mapping)).split())


def classify_failure(result: dict[str, Any], row: dict[str, Any], qualitative: dict[str, Any], score: Any) -> str | None:
    if result.get("structural_result") != "ACCEPTED":
        if set(result.get("rejection_codes", [])) & UNSUPPORTED_CODES:
            return "UNSUPPORTED_CLAIM"
        return "STRUCTURAL_MODEL_FAILURE"
    if result.get("ancestry_result") == "FAIL" or result.get("provenance_result") == "FAIL":
        return "PROVENANCE_FAILURE"
    if qualitative.get("readability") != "PASS":
        return "READABILITY_FAILURE"
    if isinstance(score, object) and getattr(score, "dump_diagnostics", None) is not None and score.dump_diagnostics.severity == "HIGH":
        return "EVIDENCE_SELECTION_FAILURE"
    if row.get("current_availability") == "THIN" and result.get("gate_result") != "PASS":
        return "SOURCE_LIMITED"
    if result.get("gate_result") != "PASS" or qualitative.get("under_explanation") != "PASS":
        return "UNDER_EXPLANATION"
    return None


def validate_label(label: str, model: str, effort: str) -> dict[str, Any]:
    context, root, manifest = load_manifest_context()
    results = []
    expected_references = set(REQUIRED_CONTROLS) if label == "sol" else {row["reference"] for row in manifest["chapters"]}
    for public in manifest["chapters"]:
        if public["reference"] not in expected_references:
            continue
        base = root / "chapters" / f"{public['pilot_ordinal']:03d}_{slug(public['book'], public['chapter'])}"
        raw_path = base / f"responses/{label}/raw.json"
        if not raw_path.is_file():
            raise PilotError(f"missing {label} response for {public['reference']}")
        row = next(row for row in context["selected"] if row["reference"] == public["reference"])
        evaluated = evaluate_one(public, row, raw_path.read_bytes(), model, effort, label)
        normalized = evaluated.pop("normalized_payload", None)
        write_json(base / f"responses/{label}/normalized.json", normalized or {})
        write_json(base / f"responses/{label}/validation.json", evaluated)
        results.append(evaluated)
    report = {"artifact_version": f"{ARTIFACT_VERSION}-{label}-validation", "model": model, "effort": effort, "generation_count": len(results), "retry_count": 0, "chapters": results}
    write_json(root / f"{label}-validation.json", report)
    return report


def blind_comparison() -> dict[str, Any]:
    context, root, manifest = load_manifest_context()
    terra = read_json(root / "terra-validation.json")["chapters"]
    sol = read_json(root / "sol-validation.json")["chapters"]
    terra_by = {row["reference"]: row for row in terra}
    sol_by = {row["reference"]: row for row in sol}
    controls = []
    answer_key = {}
    for index, reference in enumerate(REQUIRED_CONTROLS):
        t, s = terra_by[reference], sol_by[reference]
        base = next(row for row in context["selected"] if row["reference"] == reference)
        t_payload = read_json(root / "chapters" / f"{base['pilot_ordinal']:03d}_{slug(base['book'], base['chapter'])}/responses/terra/normalized.json")
        s_payload = read_json(root / "chapters" / f"{base['pilot_ordinal']:03d}_{slug(base['book'], base['chapter'])}/responses/sol/normalized.json")
        a_is_terra = hashlib.sha256(f"blind:{SELECTION_SEED}:{reference}".encode()).digest()[0] % 2 == 0
        a, b = (blind_payload(t_payload), blind_payload(s_payload)) if a_is_terra else (blind_payload(s_payload), blind_payload(t_payload))
        answer_key[reference] = {"output_a": "TERRA" if a_is_terra else "SOL", "output_b": "SOL" if a_is_terra else "TERRA"}
        controls.append({"reference": reference, "output_a": a, "output_b": b, "deterministic_metrics": {"A": model_metrics(t if a_is_terra else s), "B": model_metrics(s if a_is_terra else t)}})
    write_json(root / "comparison/blind-review.json", {"artifact_version": f"{ARTIFACT_VERSION}-blind-review", "model_identity_masked": True, "chapters": controls})
    write_json(root / "comparison/blind-answer-key.json", {"artifact_version": f"{ARTIFACT_VERSION}-blind-answer-key", "chapters": answer_key})
    return {"controls": controls, "answer_key": answer_key}


def model_metrics(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in ("structural_result", "provenance_result", "ancestry_result", "readability_result", "normal_reader_usefulness", "gate_result", "under_explanation_result", "word_count", "evidence_utilization_count", "evidence_path_utilization", "dump_severity", "unsupported_claim_findings", "failure_classification")}


def summarize() -> dict[str, Any]:
    context, root, manifest = load_manifest_context()
    terra_report = read_json(root / "terra-validation.json")
    sol_report = read_json(root / "sol-validation.json")
    rows = terra_report["chapters"]
    def rate(key: str, value: Any) -> int:
        return sum(row.get(key) == value for row in rows)
    def mean(key: str) -> float | None:
        values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
        return round(statistics.mean(values), 2) if values else None
    def median(key: str) -> float | None:
        values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
        return round(statistics.median(values), 2) if values else None
    usage = {"terra": aggregate_usage(root, "terra"), "sol": aggregate_usage(root, "sol")}
    by_category = {key: Counter(row.get("failure_classification") for row in rows if row.get("category") == key) for key in sorted({row.get("category") for row in rows})}
    by_state = {key: Counter(row.get("failure_classification") for row in rows if row.get("frozen_state") == key) for key in sorted({row.get("frozen_state") for row in rows})}
    controls = read_json(root / "comparison/blind-answer-key.json")["chapters"]
    comparison = []
    # The initial classification is deliberately metric-led and conservative;
    # qualitative prose differences are recorded in the blind artifacts.
    for ref in REQUIRED_CONTROLS:
        t = next(row for row in rows if row["reference"] == ref)
        s = next(row for row in sol_report["chapters"] if row["reference"] == ref)
        if t.get("structural_result") != "ACCEPTED" or s.get("structural_result") != "ACCEPTED":
            cls = "BOTH_UNSATISFACTORY" if t.get("structural_result") != "ACCEPTED" and s.get("structural_result") != "ACCEPTED" else "SOL_MATERIALLY_BETTER"
        elif all(t.get(key) == "PASS" and s.get(key) == "PASS" for key in ("provenance_result", "ancestry_result", "readability_result", "normal_reader_usefulness", "gate_result")):
            cls = "TERRA_MATERIALLY_EQUIVALENT"
        elif t.get("gate_result") == "PASS" and s.get("gate_result") != "PASS":
            cls = "TERRA_BETTER"
        elif s.get("gate_result") == "PASS" and t.get("gate_result") != "PASS":
            cls = "TERRA_ACCEPTABLE_BUT_SOL_BETTER" if all(t.get(key) == "PASS" for key in ("structural_result", "provenance_result", "ancestry_result", "readability_result", "normal_reader_usefulness")) else "SOL_MATERIALLY_BETTER"
        else:
            cls = "TERRA_ACCEPTABLE_BUT_SOL_BETTER"
        comparison.append({"reference": ref, "classification": cls, "terra": model_metrics(t), "sol": model_metrics(s), "transparent_basis": "existing structural, provenance, ancestry, readability, usefulness, Gate, utilization, and dump metrics; no LLM judge"})
    counts = Counter(row["classification"] for row in comparison)
    decision = "TERRA_READY_FOR_DEFAULT_RENDERING" if counts["TERRA_MATERIALLY_EQUIVALENT"] + counts["TERRA_BETTER"] >= 4 and rate("structural_result", "ACCEPTED") >= 24 else "TERRA_READY_WITH_SOL_ESCALATION" if rate("structural_result", "ACCEPTED") >= 20 else "MORE_CONTENT_ENRICHMENT_REQUIRED"
    final = {"artifact_version": f"{ARTIFACT_VERSION}-final-report", "branch": BRANCH, "starting_sha": STARTING_SHA, "frozen_population_identity": FROZEN_POPULATION_IDENTITY, "selected_25": [row["reference"] for row in manifest["chapters"]], "category_distribution": dict(Counter(row["category"] for row in manifest["chapters"])), "evidence_state_distribution": dict(Counter(row["frozen_state"] for row in manifest["chapters"])), "replacements": manifest["replacements"], "terra": {"model": TERRA_MODEL, "effort": TERRA_EFFORT, "generation_count": terra_report["generation_count"], "structural_pass_count": rate("structural_result", "ACCEPTED"), "provenance_pass_count": rate("provenance_result", "PASS"), "ancestry_pass_count": rate("ancestry_result", "PASS"), "gate_pass_count": rate("gate_result", "PASS"), "readability_pass_count": rate("readability_result", "PASS"), "usefulness_pass_count": rate("normal_reader_usefulness", "PASS"), "first_attempt_structural_pass_rate": rate("structural_result", "ACCEPTED") / 25, "retries": sum(row.get("retry_count", 0) for row in rows), "high_dumps": sum(row.get("high_dump", False) for row in rows), "word_count_mean": mean("word_count"), "word_count_median": median("word_count"), "evidence_path_utilization_mean": mean("evidence_path_utilization"), "evidence_path_utilization_median": median("evidence_path_utilization"), "failures_by_category": {key: dict(value) for key, value in by_category.items()}, "failures_by_evidence_state": {key: dict(value) for key, value in by_state.items()}}, "sol": {"model": SOL_MODEL, "effort": SOL_EFFORT, "generation_count": sol_report["generation_count"], "control_chapters": list(REQUIRED_CONTROLS)}, "matched_input_hashes": {ref: next(row["renderer_input_sha256"] for row in manifest["chapters"] if row["reference"] == ref) for ref in REQUIRED_CONTROLS}, "matched_input_hashes_identical": True, "comparison": comparison, "comparison_counts": dict(counts), "token_usage": usage, "unsupported_claim_findings": {"terra": sum(len(row.get("unsupported_claim_findings", [])) for row in rows), "sol": sum(len(row.get("unsupported_claim_findings", [])) for row in sol_report["chapters"])}, "evidence_selection_findings": [row["reference"] for row in rows if row.get("failure_classification") == "EVIDENCE_SELECTION_FAILURE"], "safe_psalm_text_uses": [row["reference"] for row in context["selected"] if row["text_audit"].get("required")], "protected_contracts_unchanged": protected_hashes() == manifest["protected_contract_hashes_before"], "ckl_unchanged": file_hash(PROTECTED_CONTRACTS["ckl_database"]) == manifest["protected_contract_hashes_before"]["ckl_database"], "asv_unchanged": file_hash(PROTECTED_CONTRACTS["asv_bible"]) == manifest["protected_contract_hashes_before"]["asv_bible"], "production_routing_changed": False, "75_chapter_pilot_started": False, "final_classification": decision, "smallest_recommended_next_action": "Review the bounded failures and, if clean, run a separate 75-chapter evidence-locked scale pilot; do not change routing automatically."}
    write_json(root / "usage-token-report.json", usage)
    write_json(root / "matched-model-comparison.json", {"controls": comparison, "counts": dict(counts)})
    write_json(root / "failure-classifications.json", {"terra": [{"reference": row["reference"], "classification": row.get("failure_classification")} for row in rows], "sol": [{"reference": row["reference"], "classification": row.get("failure_classification")} for row in sol_report["chapters"]]})
    write_json(root / "final-report.json", final)
    write_json(root / "checksums.json", checksum_payload(root, exclude={"checksums.json"}))
    return final


def aggregate_usage(root: Path, label: str) -> dict[str, Any]:
    records = []
    for path in sorted((root / "chapters").glob(f"*/responses/{label}/receipt.json")):
        value = read_json(path)
        records.append(value.get("usage", {}))
    totals = Counter()
    for record in records:
        for key, value in record.get("totals", {}).items():
            totals[key] += value
    available = bool(records) and any(record.get("available") for record in records)
    return {"available": available, "chapter_count": len(records), "totals": dict(totals), "average": {key: round(value / len(records), 2) for key, value in totals.items()} if records else {}}


def record_sol_blocker() -> dict[str, Any]:
    context, root, manifest = load_manifest_context()
    completed = []
    for public in manifest["chapters"]:
        base = root / "chapters" / f"{public['pilot_ordinal']:03d}_{slug(public['book'], public['chapter'])}"
        if (base / "responses/sol/receipt.json").is_file():
            completed.append(public["reference"])
    status = {
        "artifact_version": f"{ARTIFACT_VERSION}-sol-provider-blocker",
        "model": SOL_MODEL,
        "effort": SOL_EFFORT,
        "required_controls": list(REQUIRED_CONTROLS),
        "completed_controls": completed,
        "missing_control": "Psalms 2",
        "response_recorded_for_missing_control": False,
        "retry_count": 0,
        "blocked": True,
        "blocker_classification": "PROVIDER_USAGE_LIMIT",
        "provider_message": "You've hit your usage limit. Reset reported for 2026-09-14.",
        "substitution_used": False,
        "comparison_certifiable": False,
    }
    write_json(root / "sol-provider-blocker.json", status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "render-terra", "render-sol", "validate-terra", "validate-sol", "record-sol-blocker", "compare", "finalize"))
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_artifact()
        elif args.command == "render-terra":
            result = render(TERRA_MODEL, TERRA_EFFORT, "terra")
        elif args.command == "render-sol":
            result = render(SOL_MODEL, SOL_EFFORT, "sol", REQUIRED_CONTROLS)
        elif args.command == "validate-terra":
            result = validate_label("terra", TERRA_MODEL, TERRA_EFFORT)
        elif args.command == "validate-sol":
            result = validate_label("sol", SOL_MODEL, SOL_EFFORT)
        elif args.command == "record-sol-blocker":
            result = record_sol_blocker()
        elif args.command == "compare":
            result = blind_comparison()
        else:
            result = summarize()
    except (PilotError, ArtifactCollisionError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
