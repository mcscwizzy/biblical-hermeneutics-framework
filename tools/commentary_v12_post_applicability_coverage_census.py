#!/usr/bin/env python3
"""Deterministic post-applicability commentary evidence coverage census.

This is a read-only census of the frozen v1.2 75-chapter population.  It
rebuilds the local deterministic path through evidence, applicability,
synthesis, reader projection, ancestry, provenance binding v2, and renderer
reference presentation preflight.  It intentionally has no model or prose
generation path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.availability import classify_evidence_availability
from bhf_agent.chapter_commentary.evidence_applicability import (
    COMMENTARY_EVIDENCE_APPLICABILITY_VERSION,
    evaluate_evidence_applicability,
)
from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_IMPLEMENTATION,
    READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
    audit_ancestry_envelope,
    build_ancestry_envelope,
)
from bhf_agent.chapter_commentary.reader_level_projection import (
    READER_LEVEL_IDEA_PROJECTION_IMPLEMENTATION,
    READER_LEVEL_IDEA_PROJECTION_VERSION,
    project_reader_level_ideas,
)
from bhf_agent.chapter_commentary.reader_provenance_binding_v2 import (
    READER_PROVENANCE_BINDING_V2_IMPLEMENTATION,
    READER_PROVENANCE_BINDING_V2_VERSION,
    audit_provenance_binding_v2,
    build_provenance_binding_v2,
)
from bhf_agent.chapter_commentary.renderer_reference_presentation_v1 import (
    RENDERER_REFERENCE_PRESENTATION_IMPLEMENTATION,
    RENDERER_REFERENCE_PRESENTATION_VERSION,
    audit_active_paths,
    present_binding,
)
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
    RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    RICHNESS_GATE_V2_VERSION,
    RICHNESS_POLICY_VERSION_V3,
    cluster_synthesis_units,
)
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis, validate_synthesis
from bhf_agent.chapter_commentary.validation import __file__ as structural_validator_file
from bhf_agent.chapter_commentary.output_conformance import __file__ as output_conformance_file
from bhf_agent.presentation.evidence import build_evidence_bundle
from bhf_agent.presentation.models import EntityRef, EvidenceBundle, EvidenceItem
from bhf_agent.presentation.references import _BOOK_ALIASES, references_overlap
from bhf_agent.ckl import load_canonical_library
from framework.canonical_library.repository import CKLRepositoryConfig
from framework.canonical_library.scripture import parse_scripture_references
from framework.commentary.production.inputs import (
    literary_category,
    prepare_chapter,
)
from framework.commentary.production.models import canonical_json
from tools import commentary_v12_evidence_applicability_enforcement as applicability_tool


ARTIFACT_VERSION = "commentary-v1.2-post-applicability-coverage-census-v1"
SOURCE_NAMESPACE = (
    ".bhf-data/bhf-commentary-candidates/"
    "commentary-v1.2-scale-pilot-922472547555015a3ced"
)
SOURCE_ROOT = ROOT / SOURCE_NAMESPACE
SOURCE_MANIFEST = SOURCE_ROOT / "manifest.json"
CONTRACT_FREEZE = ROOT / "docs/commentary-v1.2-evidence-applicability-contract-freeze-v1.json"
APPLICABILITY_ENFORCEMENT_ARTIFACT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-applicability-enforcement-v1-96f7b9c60c4768cc564ef819/manifest.json"
ASV_PATH = ROOT / "bhf_agent/data/asv_bible.json"
CKL_PATH = ROOT / ".bhf/ckl.sqlite"
EXPECTED_BRANCH = "feat/commentary-v1.2-enrichment"
EXPECTED_STARTING_SHA = "3522c0dbf748e2edca2f2ce68d52dcf3ea584833"
TARGET_COUNT = 75
BATCH_SIZES = (13, 13, 13, 12, 12, 12)
STRUCTURED_CHILD_KINDS = frozenset({"ckl_evidence_item", "ckl_claim", "ckl_interpretive_note"})
RESOLVER_KINDS = frozenset({"archaeology_resolver", "passage_map_place", "passage_map_route"})
# The applicability enforcement artifact predates the broader contract-freeze
# manifest and did not record this source-file digest.  This is the verified
# post-enforcement digest at the expected starting HEAD; retaining it here
# makes a later implementation edit fail closed during the census.
EXPECTED_APPLICABILITY_SHA256 = "46355b6b5803a96b4f8f541fb46696530eba7d4a7cc488e659cfcb178b618129"


class CensusError(RuntimeError):
    """A frozen input or protected contract cannot be verified."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CensusError(f"invalid JSON artifact {path}: {exc}") from exc


def write_immutable(path: Path, value: Any) -> None:
    payload = (canonical_json(value) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise CensusError(f"immutable artifact collision: {path}")
        return
    temporary = path.with_name(f".{path.name}.tmp.{__import__('os').getpid()}")
    temporary.write_bytes(payload)
    temporary.replace(path)


def slug(book: str, chapter: int) -> str:
    return f"{book.lower().replace(' ', '_')}_{int(chapter):03d}"


def max_verse(book: str, chapter: int) -> int:
    return max(int(row["verse"]) for row in bible.resolve_chapter(book, chapter)["verses"])


def verse_set(reference: str, *, book: str, chapter: int) -> set[int]:
    result: set[int] = set()
    for span in parse_scripture_references(reference, book_alias_lookup=_BOOK_ALIASES):
        if span.book != bible.normalize_book_name(book):
            continue
        if span.start_chapter != chapter or (span.end_chapter or span.start_chapter) != chapter:
            continue
        first = span.start_verse or 1
        last = span.end_verse or max_verse(book, chapter)
        result.update(range(first, min(last, max_verse(book, chapter)) + 1))
    return result


def bundle_from_dict(data: Mapping[str, Any]) -> EvidenceBundle:
    return EvidenceBundle(
        passage_ref=str(data["passage_ref"]),
        entities={
            bucket: [EntityRef(**value) for value in data.get("entities", {}).get(bucket, [])]
            for bucket in ("people", "places", "groups", "events", "artifacts")
        },
        evidence_items=[EvidenceItem(**value) for value in data.get("evidence_items", [])],
        geography=dict(data.get("geography", {})),
        provenance=dict(data.get("provenance", {})),
        version=str(data.get("version", "1.0")),
        evidence_hash=str(data.get("evidence_hash", "")),
    )


def load_population() -> dict[str, Any]:
    manifest = read_json(SOURCE_MANIFEST)
    if manifest.get("manifest_identity") != sha256_json({k: v for k, v in manifest.items() if k != "manifest_identity"}):
        raise CensusError("frozen population manifest identity mismatch")
    rows = list(manifest.get("chapters", []))
    if len(rows) != TARGET_COUNT or len({row.get("reference") for row in rows}) != TARGET_COUNT:
        raise CensusError("frozen population is not exactly 75 unique chapters")
    if [sum(int(row.get("batch", 0)) == n for row in rows) for n in range(1, 7)] != list(BATCH_SIZES):
        raise CensusError("frozen population batch shape changed")
    corpus = read_json(SOURCE_ROOT / "frozen-corpus.json")
    corpus_refs = [row.get("reference") for row in corpus.get("chapters", [])]
    refs = [row.get("reference") for row in rows]
    if corpus.get("order_frozen") is not True or corpus_refs != refs:
        raise CensusError("frozen corpus order or membership disagrees with manifest")
    ordered_hash = sha256_bytes("\n".join(refs).encode("utf-8"))
    return {
        "source_artifact": str(SOURCE_MANIFEST.relative_to(ROOT)),
        "source_namespace": SOURCE_NAMESPACE,
        "manifest_identity": manifest["manifest_identity"],
        "immutable_id": manifest["immutable_id"],
        "ordered_references_sha256": ordered_hash,
        "frozen_corpus_sha256": sha256_file(SOURCE_ROOT / "frozen-corpus.json"),
        "chapter_count": len(rows),
        "batch_sizes": list(BATCH_SIZES),
        "selection_seed": corpus.get("selection_seed"),
        "selection_method": manifest.get("selection_method"),
        "literary_category_distribution": dict(sorted(Counter(row["literary_stratum"] for row in rows).items())),
        "previous_packet_id_count": sum(bool(row.get("source_packet_id")) for row in rows),
        "previous_packet_id_sha256": sha256_json([
            {"reference": row["reference"], "packet_id": row.get("source_packet_id"), "packet_hash": row.get("source_packet_hash")}
            for row in rows
        ]),
        "chapters": rows,
    }


def contract_snapshot() -> dict[str, Any]:
    frozen = read_json(CONTRACT_FREEZE)
    contracts = {
        "commentary_evidence_applicability_v1": {
            "path": "bhf_agent/chapter_commentary/evidence_applicability.py",
            "version": COMMENTARY_EVIDENCE_APPLICABILITY_VERSION,
        },
        "prompt_1_8": {"path": frozen["contracts"]["prompt_1_8_system"]["path"], "version": "1.8"},
        "reader_level_projection": {"path": "bhf_agent/chapter_commentary/reader_level_projection.py", "version": READER_LEVEL_IDEA_PROJECTION_VERSION},
        "reader_ancestry_envelope": {"path": "bhf_agent/chapter_commentary/reader_idea_ancestry_envelope.py", "version": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION},
        "reader_provenance_binding_v2": {"path": "bhf_agent/chapter_commentary/reader_provenance_binding_v2.py", "version": READER_PROVENANCE_BINDING_V2_VERSION},
        "renderer_reference_presentation_v1": {"path": "bhf_agent/chapter_commentary/renderer_reference_presentation_v1.py", "version": RENDERER_REFERENCE_PRESENTATION_VERSION},
        "output_conformance_v1": {"path": "bhf_agent/chapter_commentary/output_conformance.py", "version": "commentary-output-conformance-v1"},
        "structural_validator": {"path": "bhf_agent/chapter_commentary/validation.py", "version": "structural_validator"},
        "ckl_database": {"path": ".bhf/ckl.sqlite", "version": "canonical-ckl"},
        "asv_bible": {"path": "bhf_agent/data/asv_bible.json", "version": "ASV"},
    }
    expected_by_path = {value["path"]: value["sha256"] for value in frozen["contracts"].values()}
    current: dict[str, Any] = {}
    for name, value in contracts.items():
        path = ROOT / value["path"]
        actual = sha256_file(path)
        expected = EXPECTED_APPLICABILITY_SHA256 if name == "commentary_evidence_applicability_v1" else expected_by_path.get(value["path"])
        protected = name != "asv_bible"
        if protected and expected and expected != actual:
            raise CensusError(f"protected contract fingerprint changed: {name}")
        current[name] = {
            **value,
            "sha256": actual,
            "frozen_sha256": expected,
            "unchanged_from_freeze": expected == actual if expected else None,
            "authorized_asv_repair_difference": name == "asv_bible" and expected != actual,
        }
    return {
        "artifact_version": f"{ARTIFACT_VERSION}-contract-freeze",
        "frozen_contract_artifact": str(CONTRACT_FREEZE.relative_to(ROOT)),
        "applicability_enforcement_artifact": str(APPLICABILITY_ENFORCEMENT_ARTIFACT.relative_to(ROOT)),
        "contracts": current,
        "all_protected_contracts_unchanged": all(
            row["unchanged_from_freeze"] is True for name, row in current.items() if name != "asv_bible" and row["frozen_sha256"]
        ),
        "asv_note": "Psalm 19:14 contamination was repaired; 115 systematic heading-boundary patterns remain deferred pending a Psalms superscription representation policy.",
    }


def canonical_text(book: str, chapter: int) -> str:
    return bible.passage_text(bible.resolve_chapter(book, chapter)["verses"])


def current_ckl() -> Any:
    return load_canonical_library(config=CKLRepositoryConfig(
        backend="sqlite", database_path=str(CKL_PATH),
        json_root=str(ROOT / "framework/canonical_library"),
        stale_database_policy="ignore", read_only=True,
    ))


def retrieved_objects(lib: Any, reference: str) -> list[Any]:
    return list(lib.retrieve_by_scripture_reference(reference, limit=100, include_placeholders=False))


def _legacy_key(item: Any) -> tuple[str, str, str, str]:
    metadata = dict(item.relevance_metadata or {})
    return (
        str(metadata.get("parent_object_id") or ""),
        str(metadata.get("parent_type") or metadata.get("parent_object_type") or ""),
        str(metadata.get("field") or metadata.get("legacy_field") or ""),
        str(metadata.get("parent_title") or ""),
    )


def applicability_counts(bundle: EvidenceBundle) -> dict[str, Any]:
    decisions = [evaluate_evidence_applicability(item, bundle.passage_ref) for item in bundle.evidence_items]
    rows = [decision.to_dict() for decision in decisions]
    current = [item for item, decision in zip(bundle.evidence_items, decisions, strict=True) if decision.current_chapter_eligible]
    ineligible = [item for item, decision in zip(bundle.evidence_items, decisions, strict=True) if not decision.current_chapter_eligible]
    source_kinds = Counter(str((item.relevance_metadata or {}).get("source_kind") or "unknown") for item in bundle.evidence_items)
    inherited = [item for item, decision in zip(bundle.evidence_items, decisions, strict=True) if decision.inherited_from_parent is True and (item.relevance_metadata or {}).get("source_kind") == "ckl_legacy_field"]
    return {
        "decisions": rows,
        "eligible_items": current,
        "ineligible_items": ineligible,
        "raw_evidence_count": len(bundle.evidence_items),
        "structured_child_evidence_count": sum((item.relevance_metadata or {}).get("source_kind") in STRUCTURED_CHILD_KINDS for item in bundle.evidence_items),
        "resolver_owned_evidence_count": sum((item.relevance_metadata or {}).get("source_kind") in RESOLVER_KINDS for item in bundle.evidence_items),
        "inherited_legacy_evidence_count": len(inherited),
        "commentary_eligible_evidence_count": len(current),
        "commentary_ineligible_evidence_count": len(ineligible),
        "exclusion_reason_counts": dict(sorted(Counter(decision.reason for decision in decisions if not decision.current_chapter_eligible).items())),
        "source_kind_counts": dict(sorted(source_kinds.items())),
        "legacy_evidence_ids": sorted(item.id for item in inherited),
        "legacy_keys": sorted({_legacy_key(item) for item in inherited}),
    }


def coverage_for_anchors(anchors: Iterable[str], book: str, chapter: int) -> set[int]:
    covered: set[int] = set()
    for anchor in anchors:
        covered.update(verse_set(anchor, book=book, chapter=chapter))
    return covered


def historical_synthesis(row: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    path = SOURCE_ROOT / f"batch-{int(row['batch']):03d}" / "renderer-input" / f"{int(row['ordinal']):03d}_{row['slug']}" / "user_prompt.txt"
    if not path.exists():
        raise CensusError(f"historical source packet prompt missing: {path}")
    text = path.read_text(encoding="utf-8")
    marker = "COMPILED CHAPTER SYNTHESIS:"
    index = text.find(marker)
    if index < 0:
        raise CensusError(f"historical compiled synthesis marker missing: {path}")
    try:
        value = json.JSONDecoder().raw_decode(text[index + len(marker):].lstrip())[0]
    except json.JSONDecodeError as exc:
        raise CensusError(f"historical compiled synthesis is not parseable: {path}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("units"), list):
        raise CensusError(f"historical compiled synthesis has no units: {path}")
    return value, str(path.relative_to(ROOT))


def _current_clusters(prepared: Any) -> list[Any]:
    return cluster_synthesis_units(
        prepared.synthesis.synthesis_units,
        prepared.bundle.evidence_items,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=canonical_text(prepared.synthesis.book, prepared.synthesis.chapter),
    )


def _path_counts(binding: Mapping[str, Any], presentation_audit: Mapping[str, Any]) -> dict[str, int]:
    audit = dict(binding.get("binding_audit", {}))
    counts = dict(presentation_audit.get("counts", {}))
    return {
        "priority_provenance_path_count": int(audit.get("priority_path_count", 0)),
        "fallback_provenance_path_count": int(audit.get("fallback_renderable_path_count", 0)),
        "renderer_legal_path_count": int(counts.get("VALID_ALREADY", 0)) + int(counts.get("SAFE_FULL_CHAPTER_SCOPE", 0)),
        "renderer_ambiguous_path_count": int(counts.get("AMBIGUOUS", 0)),
        "renderer_invalid_path_count": int(counts.get("INVALID_SOURCE_REFERENCE", 0)),
    }


def chapter_census(row: Mapping[str, Any], lib: Any) -> dict[str, Any]:
    book, chapter, reference = str(row["book"]), int(row["chapter"]), str(row["reference"])
    prepared = prepare_chapter(book, chapter)
    bundle, synthesis = prepared.bundle, prepared.synthesis
    if bundle is None or synthesis is None:
        raise CensusError(f"deterministic preparation returned no objects for {reference}")
    if synthesis.reference != reference:
        raise CensusError(f"canonical reference disagreement for {reference}")
    validation_errors = validate_synthesis(synthesis, bundle)
    if validation_errors:
        raise CensusError(f"synthesis validation failed for {reference}: {validation_errors}")
    objects = retrieved_objects(lib, reference)
    applicability = applicability_counts(bundle)
    clusters = _current_clusters(prepared)
    projection = project_reader_level_ideas(synthesis, clusters, bundle.evidence_items)
    if synthesis.synthesis_units:
        envelope = build_ancestry_envelope(projection, synthesis, bundle.evidence_items)
        envelope_audit = audit_ancestry_envelope(envelope, projection, synthesis)
        binding = build_provenance_binding_v2(envelope, synthesis, bundle.evidence_items)
        binding_audit = audit_provenance_binding_v2(binding, envelope, synthesis, bundle.evidence_items)
        presentation = present_binding(binding, synthesis, bundle.evidence_items)
        presentation_audit = audit_active_paths(binding, synthesis, bundle.evidence_items)
        if not envelope_audit.get("valid") or not binding_audit.get("valid"):
            raise CensusError(f"deterministic downstream contract audit failed for {reference}")
    else:
        # The frozen envelope contract requires at least one synthesis unit.
        # A zero-unit chapter is recorded as a fail-closed data-gap boundary;
        # no synthetic empty envelope or renderer presentation is created.
        envelope = {"artifact_version": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION, "reference": reference, "ideas": [], "paths": []}
        envelope_audit = {"valid": False, "status": "NOT_APPLICABLE_NO_SYNTHESIS_UNITS"}
        binding = {"artifact_version": READER_PROVENANCE_BINDING_V2_VERSION, "reference": reference, "paths": [], "binding_audit": {"priority_path_count": 0, "fallback_renderable_path_count": 0}}
        binding_audit = {"valid": False, "status": "NOT_APPLICABLE_NO_SYNTHESIS_UNITS"}
        presentation = {"artifact_version": RENDERER_REFERENCE_PRESENTATION_VERSION, "reference": reference, "paths": []}
        presentation_audit = {"status": "NOT_APPLICABLE_NO_SYNTHESIS_UNITS", "counts": {"VALID_ALREADY": 0, "SAFE_FULL_CHAPTER_SCOPE": 0, "AMBIGUOUS": 0, "INVALID_SOURCE_REFERENCE": 0}}
    decisions = applicability["decisions"]
    eligible = applicability["eligible_items"]
    raw_anchors = [anchor for item in bundle.evidence_items for anchor in item.passage_anchors]
    legal_anchors = [anchor for item in eligible for anchor in item.passage_anchors]
    raw_verses = coverage_for_anchors(raw_anchors, book, chapter)
    legal_verses = coverage_for_anchors(legal_anchors, book, chapter)
    current_units = [unit for unit in synthesis.synthesis_units if unit.passage_scope == "CURRENT_CHAPTER"]
    surrounding_units = [unit for unit in synthesis.synthesis_units if unit.passage_scope == "SURROUNDING_PASSAGE"]
    historical, historical_path = historical_synthesis(row)
    old_units = list(historical["units"])
    old_current_units = [unit for unit in old_units if unit.get("passage_scope") == "CURRENT_CHAPTER"]
    old_all_verses = coverage_for_anchors(
        [ref for unit in old_units for ref in unit.get("verse_refs", [])], book, chapter
    )
    old_legal_verses = coverage_for_anchors(
        [ref for unit in old_current_units for ref in unit.get("verse_refs", [])], book, chapter
    )
    before = {
        "source_packet_prompt": historical_path,
        "evidence_count": int(historical.get("coverage", {}).get("evidence_item_count", len(historical.get("coverage", {}).get("used_evidence_ids", [])))),
        "evidence_hash": str(row.get("evidence_hash", "")),
        "availability": str(row.get("evidence_availability", "UNKNOWN")),
        "synthesis_hash": str(historical.get("synthesis_hash", row.get("synthesis_hash", ""))),
        "synthesis_unit_count": len(old_units),
        "current_chapter_synthesis_count": len(old_current_units),
        "surrounding_passage_count": sum(unit.get("passage_scope") == "SURROUNDING_PASSAGE" for unit in old_units),
        "projected_idea_count": int(row.get("projected_idea_count", 0)),
        "provenance_path_count": int(row.get("ancestry_path_count", 0)),
        "priority_provenance_path_count": int(row.get("ancestry_path_count", 0)),
        "fallback_provenance_path_count": 0,
        "renderer_legal_path_count": int(row.get("ancestry_path_count", 0)),
        "raw_verse_coverage": sorted(old_all_verses),
        "legal_verse_coverage": sorted(old_legal_verses),
        "legal_verse_coverage_percentage": round(100 * len(old_legal_verses) / max_verse(book, chapter), 2),
        "historical_metric_basis": "frozen pre-applicability compiled synthesis and packet manifest; source prompts are immutable historical packet evidence",
    }
    current_paths = _path_counts(binding, presentation_audit)
    record = {
        "reference": reference,
        "book": book,
        "chapter": chapter,
        "literary_stratum": row["literary_stratum"],
        "literary_category": literary_category(book, chapter),
        "seen_status": row.get("seen_status"),
        "batch": row.get("batch"),
        "ordinal": row.get("ordinal"),
        "chapter_verse_count": max_verse(book, chapter),
        "retrieved_ckl_object_count": len(objects),
        "raw_evidence_bundle_evidence_count": len(bundle.evidence_items),
        "structured_child_evidence_count": applicability["structured_child_evidence_count"],
        "resolver_owned_evidence_count": applicability["resolver_owned_evidence_count"],
        "inherited_legacy_evidence_count": applicability["inherited_legacy_evidence_count"],
        "commentary_eligible_evidence_count": applicability["commentary_eligible_evidence_count"],
        "commentary_ineligible_evidence_count": applicability["commentary_ineligible_evidence_count"],
        "exclusion_reason_counts": applicability["exclusion_reason_counts"],
        "source_kind_counts": applicability["source_kind_counts"],
        "evidence_availability": synthesis.evidence_availability,
        "synthesis_unit_count": len(synthesis.synthesis_units),
        "current_chapter_synthesis_count": len(current_units),
        "surrounding_passage_synthesis_count": len(surrounding_units),
        "projected_core_idea_count": sum(idea.importance == "CORE" for idea in projection.ideas),
        "projected_relevant_idea_count": sum(idea.importance == "RELEVANT" for idea in projection.ideas),
        "projected_idea_count": len(projection.ideas),
        **current_paths,
        "distinct_passage_scopes": sorted(set(raw_anchors)),
        "distinct_legal_passage_scopes": sorted(set(legal_anchors)),
        "raw_verse_coverage": sorted(raw_verses),
        "raw_verse_coverage_count": len(raw_verses),
        "raw_verse_coverage_percentage": round(100 * len(raw_verses) / max_verse(book, chapter), 2),
        "legal_commentary_verse_coverage": sorted(legal_verses),
        "legal_commentary_verse_coverage_count": len(legal_verses),
        "legal_commentary_verse_coverage_percentage": round(100 * len(legal_verses) / max_verse(book, chapter), 2),
        "coverage_difference_percentage_points": round(100 * (len(raw_verses) - len(legal_verses)) / max_verse(book, chapter), 2),
        "evidence_hash": bundle.evidence_hash,
        "synthesis_hash": synthesis.synthesis_hash,
        "projection_hash": projection.projection_hash,
        "ancestry_envelope_hash": envelope.get("envelope_hash"),
        "provenance_binding_hash": binding.get("binding_hash"),
        "renderer_presentation_hash": presentation.get("presentation_hash"),
        "ancestry_audit": envelope_audit,
        "provenance_binding_audit": binding_audit,
        "renderer_presentation_audit": presentation_audit,
        "applicability": {key: value for key, value in applicability.items() if key not in {"eligible_items", "ineligible_items"}},
        "before": before,
        "_legacy_evidence_ids": applicability["legacy_evidence_ids"],
        "_current_unit_records": [unit.to_dict() for unit in synthesis.synthesis_units],
        "_old_unit_records": old_units,
        "_bundle_records": [item.to_dict() for item in bundle.evidence_items],
    }
    return record


def _candidate_text(raw: Mapping[str, Any], field: str) -> str:
    value = raw.get(field)
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True) if value else ""


def _target_reference_mentions(text: str, reference: str, book: str, chapter: int) -> list[str]:
    mentions: list[str] = []
    # This only detects authored text containing the exact target book/chapter
    # and does not convert the mention into an anchor.
    pattern = re.compile(rf"\b{re.escape(book)}\s+{chapter}(?::\d+(?:-\d+)?)?\b", re.IGNORECASE)
    for match in pattern.finditer(text):
        value = " ".join(match.group(0).split())
        if value.casefold() not in {reference.casefold()}:
            mentions.append(value)
    return sorted(set(mentions))


def load_object_index() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "framework/canonical_library/objects").rglob("*.json")):
        value = read_json(path)
        if isinstance(value, dict) and value.get("id"):
            result[str(value["id"])] = {**value, "_path": str(path.relative_to(ROOT))}
    return result


def build_queues(records: list[dict[str, Any]], objects: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for record in records:
        for item in record["_bundle_records"]:
            meta = item.get("relevance_metadata", {}) or {}
            if meta.get("source_kind") != "ckl_legacy_field" or meta.get("inherited_from_parent") is not True:
                continue
            key = (record["book"], str(meta.get("parent_object_id") or ""), str(meta.get("field") or ""), str(meta.get("parent_type") or ""))
            group = grouped.setdefault(key, {
                "book": record["book"], "chapter": record["chapter"], "references": set(),
                "parent_object_id": key[1], "parent_object_type": key[3],
                "parent_title": str(meta.get("parent_title") or ""), "legacy_field": key[2],
                "evidence_ids": set(), "former_synthesis_units": set(), "former_verse_coverage": set(),
                "review_status": None, "source_status": None, "source_types": set(),
            })
            group["references"].add(record["reference"])
            group["evidence_ids"].add(item["id"])
            parent = objects.get(key[1], {})
            group["review_status"] = parent.get("review_status")
            group["source_status"] = parent.get("source_status")
            for source in parent.get("sources", []) or []:
                if isinstance(source, dict) and source.get("source_type"):
                    group["source_types"].add(str(source["source_type"]))
            for unit in record["_old_unit_records"]:
                if item["id"] in (unit.get("evidence_ids") or []):
                    group["former_synthesis_units"].add(unit.get("id"))
                    for ref in unit.get("verse_refs", []):
                        group["former_verse_coverage"].update(verse_set(ref, book=record["book"], chapter=record["chapter"]))
    migration: list[dict[str, Any]] = []
    background: list[dict[str, Any]] = []
    editorial: list[dict[str, Any]] = []
    for key, group in sorted(grouped.items()):
        parent = objects.get(group["parent_object_id"], {})
        field = group["legacy_field"]
        text = _candidate_text(parent, field)
        mentions = sorted({mention for ref in group["references"] for row in records if row["reference"] == ref for mention in _target_reference_mentions(text, ref, row["book"], row["chapter"])})
        exact_claim_signal = bool(mentions) and bool(parent.get("sources") or parent.get("source_ids"))
        source_quality = sorted(group["source_types"])
        item = {
            "family_key": {"book": key[0], "parent_object_type": key[3], "legacy_field": key[2]},
            "book": group["book"], "affected_chapters": sorted(group["references"]),
            "parent_object_id": group["parent_object_id"], "parent_object_type": group["parent_object_type"],
            "parent_title": group["parent_title"], "legacy_field": field,
            "evidence_ids": sorted(group["evidence_ids"]),
            "former_synthesis_units": len(group["former_synthesis_units"]),
            "former_verse_coverage_count": len(group["former_verse_coverage"]),
            "review_status": group["review_status"], "source_status": group["source_status"], "source_types": source_quality,
            "claim_level_signal": mentions,
            "classification": None,
            "reason": None,
        }
        if exact_claim_signal:
            item["classification"] = "MIGRATION_CANDIDATE"
            item["reason"] = "legacy field text contains an explicit population chapter reference and source provenance; authored child anchoring is still required"
            item["editorial_status"] = "REQUIRES_EDITORIAL_REVIEW"
            migration.append(item)
            editorial.append({**item, "classification": "REQUIRES_EDITORIAL_REVIEW", "reason": "deterministic signal is insufficient to invent a child anchor; editor must author and verify verse scope"})
        else:
            item["classification"] = "BACKGROUND_ONLY"
            item["reason"] = "legacy parent inheritance has no deterministic claim-level target anchor; parent title, Bible words, retrieval frequency, and inherited anchor are insufficient"
            item["editorial_status"] = "NOT_RECOMMENDED_FOR_MIGRATION"
            background.append(item)
    return {
        "policy": {
            "migration": "Only explicit target-reference text plus source provenance creates a migration candidate; no anchor is invented and every candidate requires editorial review.",
            "background_only": "Generic legacy parent fields with no claim-level target-reference signal remain background-only.",
            "ordering": "descending affected chapter count, legal verse coverage represented by former units, former synthesis units, source quality, then stable family key; ties are lexical",
        },
        "migration_candidates": sorted(migration, key=lambda x: (-len(x["affected_chapters"]), -x["former_verse_coverage_count"], -x["former_synthesis_units"], x["parent_object_id"], x["legacy_field"])),
        "background_only_candidates": sorted(background, key=lambda x: (-len(x["affected_chapters"]), -x["former_verse_coverage_count"], -x["former_synthesis_units"], x["parent_object_id"], x["legacy_field"])),
        "editorial_review_queue": sorted(editorial, key=lambda x: (-len(x["affected_chapters"]), -x["former_verse_coverage_count"], x["parent_object_id"], x["legacy_field"])),
    }


def family_report(records: list[dict[str, Any]], queues: Mapping[str, Any]) -> list[dict[str, Any]]:
    families: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(lambda: {
        "affected_chapters": set(), "inherited_instances": 0, "former_units": set(), "current_legal_units": set(), "lost_verses": set(),
    })
    for record in records:
        legacy_ids = set(record["_legacy_evidence_ids"])
        old_units = record["_old_unit_records"]
        current_units = record["_current_unit_records"]
        item_by_id = {item["id"]: item for item in record["_bundle_records"]}
        for evidence_id in legacy_ids:
            item = item_by_id[evidence_id]; meta = item.get("relevance_metadata", {}) or {}
            key = (record["book"], str(meta.get("parent_type") or ""), str(meta.get("field") or ""))
            family = families[key]; family["affected_chapters"].add(record["reference"]); family["inherited_instances"] += 1
            for unit in old_units:
                if evidence_id in (unit.get("evidence_ids") or []):
                    family["former_units"].add((record["reference"], unit.get("id")))
                    for ref in unit.get("verse_refs", []):
                        family["lost_verses"].update(verse_set(ref, book=record["book"], chapter=record["chapter"]))
            for unit in current_units:
                if evidence_id in (unit.get("evidence_ids") or []) and unit.get("passage_scope") == "CURRENT_CHAPTER":
                    family["current_legal_units"].add((record["reference"], unit.get("id")))
    migration_keys = {(x["book"], x["parent_object_type"], x["legacy_field"]) for x in queues["migration_candidates"]}
    background_keys = {(x["book"], x["parent_object_type"], x["legacy_field"]) for x in queues["background_only_candidates"]}
    editorial_keys = {(x["book"], x["parent_object_type"], x["legacy_field"]) for x in queues["editorial_review_queue"]}
    rows = []
    for (book, object_type, field), value in families.items():
        key = (book, object_type, field)
        rows.append({
            "family": f"{book}:{object_type}:{field}", "book": book, "object_type": object_type, "field": field,
            "affected_chapters": sorted(value["affected_chapters"]), "affected_chapter_count": len(value["affected_chapters"]),
            "inherited_instances": value["inherited_instances"], "former_synthesis_units": len(value["former_units"]),
            "current_legal_synthesis_units": len(value["current_legal_units"]),
            "legal_verse_coverage_lost_count": len(value["lost_verses"]),
            "migration_candidate_count": int(key in migration_keys), "background_only_candidate_count": int(key in background_keys),
            "editorial_review_count": int(key in editorial_keys),
        })
    return sorted(rows, key=lambda x: (-x["affected_chapter_count"], -x["legal_verse_coverage_lost_count"], -x["former_synthesis_units"], x["family"]))


def classify_state(record: Mapping[str, Any]) -> dict[str, Any]:
    raw = int(record["raw_evidence_bundle_evidence_count"]); inherited = int(record["inherited_legacy_evidence_count"]); legal = int(record["commentary_eligible_evidence_count"])
    synth = int(record["synthesis_unit_count"]); current = int(record["current_chapter_synthesis_count"]); coverage = float(record["legal_commentary_verse_coverage_percentage"])
    proportion = inherited / raw if raw else 0.0
    flags: list[str] = []
    if current == 0:
        flags.append("COMMENTARY_DATA_GAP")
    if raw >= 5 and proportion >= 0.75:
        flags.append("LEGACY_INFLATED")
    if raw >= 6 and synth >= 6 and legal <= 1:
        flags.append("REDUNDANCY_INFLATED")
    if 0 < coverage < 100:
        flags.append("EVIDENCE_PARTIAL")
    if coverage >= 75 and 1 <= current <= 5 and legal > 0:
        flags.append("EVIDENCE_FOCUSED")
    if coverage >= 75 and current >= 6 and int(record["projected_idea_count"]) >= 3:
        flags.append("EVIDENCE_RICH")
    if len(flags) > 1:
        state = "MIXED"
    elif flags:
        state = flags[0]
    else:
        state = "EVIDENCE_PARTIAL" if coverage > 0 else "COMMENTARY_DATA_GAP"
    return {
        "reference": record["reference"], "state": state, "diagnostic_flags": flags,
        "criteria": {
            "legacy_inflated": "raw evidence >= 5 and inherited proportion >= 0.75",
            "redundancy_inflated": "raw evidence >= 6, synthesis units >= 6, legal evidence <= 1",
            "partial": "legal verse coverage strictly between 0% and 100%",
            "focused": "legal coverage >= 75%, 1-5 current-chapter units, and legal evidence exists",
            "rich": "legal coverage >= 75%, >=6 current-chapter units, and >=3 projected ideas",
            "data_gap": "zero CURRENT_CHAPTER synthesis units",
        },
        "legacy_proportion": round(proportion, 4), "raw_evidence_count": raw, "inherited_legacy_count": inherited,
        "legal_evidence_count": legal, "lost_current_chapter_synthesis_count": max(0, int(record["before"]["current_chapter_synthesis_count"]) - current),
        "legal_coverage_loss_percentage_points": round(max(0.0, float(record["before"]["legal_verse_coverage_percentage"]) - coverage), 2),
    }


def aggregate_stats(records: list[dict[str, Any]], states: list[dict[str, Any]]) -> dict[str, Any]:
    def stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
        raw = [int(x["raw_evidence_bundle_evidence_count"]) for x in rows]; legal = [int(x["commentary_eligible_evidence_count"]) for x in rows]
        raw_cov = [float(x["raw_verse_coverage_percentage"]) for x in rows]; legal_cov = [float(x["legal_commentary_verse_coverage_percentage"]) for x in rows]
        unit_counts = Counter("0" if x["current_chapter_synthesis_count"] == 0 else "1" if x["current_chapter_synthesis_count"] == 1 else "2-5" if x["current_chapter_synthesis_count"] <= 5 else "6-10" if x["current_chapter_synthesis_count"] <= 10 else ">10" for x in rows)
        return {
            "chapter_count": len(rows), "availability": dict(sorted(Counter(x["evidence_availability"] for x in rows).items())),
            "zero_legal_synthesis_count": sum(x["current_chapter_synthesis_count"] == 0 for x in rows), "synthesis_unit_buckets": dict(sorted(unit_counts.items())),
            "raw_evidence_average": round(statistics.mean(raw), 2) if raw else 0, "raw_evidence_median": statistics.median(raw) if raw else 0,
            "legal_evidence_average": round(statistics.mean(legal), 2) if legal else 0, "legal_evidence_median": statistics.median(legal) if legal else 0,
            "raw_verse_coverage_average": round(statistics.mean(raw_cov), 2) if raw_cov else 0, "legal_verse_coverage_average": round(statistics.mean(legal_cov), 2) if legal_cov else 0,
            "legal_verse_coverage_median": statistics.median(legal_cov) if legal_cov else 0,
            "legacy_inflated_count": sum("LEGACY_INFLATED" in s["diagnostic_flags"] for s in states if s["reference"] in {x["reference"] for x in rows}),
            "partial_evidence_count": sum("EVIDENCE_PARTIAL" in s["diagnostic_flags"] for s in states if s["reference"] in {x["reference"] for x in rows}),
            "focused_count": sum("EVIDENCE_FOCUSED" in s["diagnostic_flags"] for s in states if s["reference"] in {x["reference"] for x in rows}),
            "rich_count": sum("EVIDENCE_RICH" in s["diagnostic_flags"] for s in states if s["reference"] in {x["reference"] for x in rows}),
        }
    by_category = {}
    for category in sorted({x["literary_stratum"] for x in records}):
        selected = [x for x in records if x["literary_stratum"] == category]
        by_category[category] = stats(selected)
    overall = stats(records)
    return {"overall": overall, "by_literary_category": by_category}


def asv_exposure(population: Mapping[str, Any]) -> dict[str, Any]:
    scan = applicability_tool.asv_contamination_scan()
    refs = {(row["book"], int(row["chapter"])) for row in population["chapters"]}
    intersecting = [row for row in scan["other_psalms_boundary_matches"] if (row.get("book"), int(row.get("chapter", 0))) in refs]
    return {
        "current_asv_sha256": sha256_file(ASV_PATH),
        "scan_total_matches": scan["total_matches"], "remaining_systematic_heading_boundary_patterns": len(scan["other_psalms_boundary_matches"]),
        "population_intersections": intersecting,
        "psalm_19_14_repaired": True,
        "repair_action": "not modified during census",
        "deferred_policy": "Psalms superscription representation policy",
    }


def public_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if not key.startswith("_")}


def build_identity(population: Mapping[str, Any], contracts: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    payload = {
        "artifact_version": ARTIFACT_VERSION, "population_manifest_identity": population["manifest_identity"],
        "ordered_references_sha256": population["ordered_references_sha256"],
        "contract_sha256": {key: value["sha256"] for key, value in contracts["contracts"].items()},
        "model_calls": 0, "commentary_generated": False, "renderer_invocations": 0,
    }
    return sha256_json(payload)[:24], payload


def run(output_dir: Path | None = None) -> Path:
    population = load_population()
    contracts = contract_snapshot()
    identity, identity_payload = build_identity(population, contracts)
    namespace = f".bhf-data/bhf-commentary-candidates/{ARTIFACT_VERSION}-{identity}"
    target = output_dir or ROOT / namespace
    target.mkdir(parents=True, exist_ok=True)
    manifest_base = {
        "artifact_version": ARTIFACT_VERSION,
        "artifact_namespace": namespace,
        "identity": identity,
        "identity_payload": identity_payload,
        "population_manifest_identity": population["manifest_identity"],
        "ordered_references_sha256": population["ordered_references_sha256"],
        "chapter_count": len(population["chapters"]),
        "batch_sizes": population["batch_sizes"],
        "model_calls": 0,
        "commentary_generated": False,
        "renderer_invocations": 0,
        "production_behavior_changed": False,
        "immutable": True,
    }
    manifest = {**manifest_base, "manifest_sha256": sha256_json(manifest_base)}
    write_immutable(target / "manifest.json", manifest)
    write_immutable(target / "frozen-population-identity.json", population)
    write_immutable(target / "chapter-list.json", {"references": [row["reference"] for row in population["chapters"]], "identity": population["ordered_references_sha256"]})
    write_immutable(target / "contract-hashes.json", contracts)
    lib = current_ckl()
    records: list[dict[str, Any]] = []
    for row in population["chapters"]:
        path = target / "chapters" / f"{int(row['ordinal']):03d}_{row['slug']}.json"
        if path.exists():
            record = read_json(path)
            if "_bundle_records" not in record:
                # Older interrupted checkpoints contain the public record
                # only. Rebuild that chapter in memory so downstream family
                # analysis remains complete without rewriting immutable data.
                record = chapter_census(row, lib)
        else:
            record = chapter_census(row, lib)
            write_immutable(path, public_record(record))
        records.append(record)
    records.sort(key=lambda x: int(x["ordinal"]))
    states = [classify_state(record) for record in records]
    queues = build_queues(records, load_object_index())
    families = family_report(records, queues)
    stats = aggregate_stats(records, states)
    coverage = {record["reference"]: {key: record[key] for key in ("chapter_verse_count", "raw_verse_coverage", "raw_verse_coverage_count", "raw_verse_coverage_percentage", "legal_commentary_verse_coverage", "legal_commentary_verse_coverage_count", "legal_commentary_verse_coverage_percentage", "coverage_difference_percentage_points")} for record in records}
    before_after: dict[str, Any] = {}
    for record in records:
        before = record["before"]
        after_keys = (
            "raw_evidence_bundle_evidence_count", "evidence_availability",
            "synthesis_unit_count", "current_chapter_synthesis_count",
            "surrounding_passage_synthesis_count", "projected_idea_count",
            "priority_provenance_path_count", "fallback_provenance_path_count",
            "renderer_legal_path_count", "legal_commentary_verse_coverage_percentage",
        )
        transitions = (
            ("AVAILABLE_TO_THIN", before["availability"] == "AVAILABLE" and record["evidence_availability"] == "THIN"),
            ("AVAILABLE_TO_DATA_GAP", before["availability"] == "AVAILABLE" and record["evidence_availability"] == "DATA_GAP"),
            ("THIN_TO_DATA_GAP", before["availability"] == "THIN" and record["evidence_availability"] == "DATA_GAP"),
            ("NONZERO_TO_ZERO_SYNTHESIS", before["synthesis_unit_count"] > 0 and record["synthesis_unit_count"] == 0),
            ("PRIORITY_TO_NONE", before["priority_provenance_path_count"] > 0 and record["priority_provenance_path_count"] == 0),
            ("FALLBACK_TO_ZERO", before["fallback_provenance_path_count"] > 0 and record["fallback_provenance_path_count"] == 0),
        )
        before_after[record["reference"]] = {
            "before": before,
            "after": {key: record[key] for key in after_keys},
            "changes": {
                "evidence_count": record["raw_evidence_bundle_evidence_count"] - before["evidence_count"],
                "synthesis_count": record["synthesis_unit_count"] - before["synthesis_unit_count"],
                "current_chapter_synthesis_count": record["current_chapter_synthesis_count"] - before["current_chapter_synthesis_count"],
                "projected_idea_count": record["projected_idea_count"] - before["projected_idea_count"],
                "provenance_path_count": record["priority_provenance_path_count"] + record["fallback_provenance_path_count"] - before["provenance_path_count"],
                "legal_coverage_percentage_points": round(record["legal_commentary_verse_coverage_percentage"] - before["legal_verse_coverage_percentage"], 2),
            },
            "change_flags": [flag for flag, condition in transitions if condition],
        }
    write_immutable(target / "coverage-records.json", coverage)
    write_immutable(target / "before-after-comparison.json", before_after)
    write_immutable(target / "evidence-state-classification.json", {"criteria": states[0]["criteria"] if states else {}, "chapters": states})
    write_immutable(target / "legacy-dependency-metrics.json", {"chapters": [{"reference": state["reference"], **{key: state[key] for key in ("legacy_proportion", "raw_evidence_count", "inherited_legacy_count", "legal_evidence_count", "lost_current_chapter_synthesis_count", "legal_coverage_loss_percentage_points")}} for state in states]})
    write_immutable(target / "ckl-family-impact-report.json", {"families": families, "top_10_commentary_impact": families[:10], "population_inherited_instance_count": sum(x["inherited_legacy_evidence_count"] for x in records)})
    write_immutable(target / "migration-candidate-queue.json", {"queue_name": "MIGRATION_CANDIDATES", "candidates": queues["migration_candidates"], "count": len(queues["migration_candidates"])})
    write_immutable(target / "background-only-queue.json", {"queue_name": "BACKGROUND_ONLY_CANDIDATES", "candidates": queues["background_only_candidates"], "count": len(queues["background_only_candidates"])})
    write_immutable(target / "editorial-review-queue.json", {"queue_name": "REQUIRES_EDITORIAL_REVIEW", "candidates": queues["editorial_review_queue"], "count": len(queues["editorial_review_queue"])})
    write_immutable(target / "psalm-superscription-exposure.json", asv_exposure(population))
    write_immutable(target / "summary-statistics.json", stats)
    chapter_public = [public_record(record) for record in records]
    final = {
        "artifact_version": ARTIFACT_VERSION, "identity": identity, "identity_payload": identity_payload,
        "namespace": namespace, "branch": EXPECTED_BRANCH, "starting_sha": EXPECTED_STARTING_SHA,
        "ending_sha_at_census": __import__('subprocess').check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "population_identity": population["manifest_identity"], "chapters_analyzed": len(records),
        "model_calls": 0, "commentary_generated": False, "renderer_invocations": 0, "production_behavior_changed": False,
        "summary": stats, "states": {key: sum(state["state"] == key for state in states) for key in sorted({state["state"] for state in states})},
        "zero_legal_synthesis_count": sum(record["current_chapter_synthesis_count"] == 0 for record in records),
        "migration_candidate_count": len(queues["migration_candidates"]), "background_only_candidate_count": len(queues["background_only_candidates"]), "editorial_review_count": len(queues["editorial_review_queue"]),
        "top_10_ckl_pollution_families": families[:10],
        "top_20_chapter_enrichment_priorities": sorted(({
            "reference": record["reference"], "literary_category": record["literary_stratum"], "legal_coverage_loss_percentage_points": next(state["legal_coverage_loss_percentage_points"] for state in states if state["reference"] == record["reference"]), "legal_coverage_percentage": record["legal_commentary_verse_coverage_percentage"], "inherited_legacy_count": record["inherited_legacy_evidence_count"], "current_legal_synthesis_count": record["current_chapter_synthesis_count"], "raw_evidence_count": record["raw_evidence_bundle_evidence_count"], "priority_reason": "enrich chapters with greatest legal coverage loss, then zero/low legal synthesis, then inherited dependency; descriptive queue only"
        } for record in records), key=lambda x: (-x["legal_coverage_loss_percentage_points"], x["legal_coverage_percentage"], -x["inherited_legacy_count"], x["reference"]))[:20],
        "controls": {ref: next(public_record(record) for record in records if record["reference"] == ref) for ref in ("2 Kings 4", "Psalms 103", "Psalms 19", "Numbers 2", "Numbers 1")},
        "psalm_superscription_exposure": asv_exposure(population),
        "test_contract": {"zero_model_invocation_expected": True, "no_renderer_invocation_expected": True},
    }
    write_immutable(target / "final-report.json", final)
    files: dict[str, str] = {}
    for path in sorted(target.rglob("*")):
        if path.is_file() and path.name != "checksums.json":
            files[str(path.relative_to(target))] = sha256_file(path)
    write_immutable(target / "checksums.json", {"artifact_version": f"{ARTIFACT_VERSION}-checksums", "files": files})
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        target = run(args.output_dir)
    except CensusError as exc:
        print(f"CENSUS_STOPPED: {exc}", file=sys.stderr)
        return 2
    print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
