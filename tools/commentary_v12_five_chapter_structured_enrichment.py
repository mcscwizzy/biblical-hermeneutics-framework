#!/usr/bin/env python3
"""Build the bounded v1.2 five-chapter structured-enrichment artifact.

This tool is intentionally deterministic.  It overlays only the five edited
CKL book objects over the read-only runtime CKL, rebuilds the frozen evidence
and renderability path, and writes an immutable artifact.  It does not call a
model and it never edits the CKL or canonical Bible data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
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
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
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
    add_provenance_binding_to_prompt_v2,
    audit_provenance_binding_v2,
    build_provenance_binding_v2,
)
from bhf_agent.chapter_commentary.renderer_reference_presentation_v1 import (
    add_presentation_to_prompt,
    audit_active_paths,
    present_binding,
)
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    RICHNESS_POLICY_VERSION_V3,
    cluster_synthesis_units,
)
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis, validate_synthesis
from bhf_agent.ckl import load_canonical_library
from bhf_agent.presentation.models import EvidenceBundle
from bhf_agent.presentation.references import _BOOK_ALIASES
from framework.canonical_library import CKLRepositoryConfig
from framework.canonical_library.scripture import parse_scripture_references
from framework.commentary.production.models import canonical_json
from tools.commentary_v12_post_applicability_coverage_census import (
    contract_snapshot,
)


ARTIFACT_VERSION = "commentary-v1.2-five-chapter-structured-enrichment-v1"
STARTING_SHA = "22e32598c08f8a788f2bc31749eabd33abaf9b67"
EXPECTED_BRANCH = "feat/commentary-v1.2-enrichment"
ARTIFACT_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates" / f"{ARTIFACT_VERSION}-{STARTING_SHA[:8]}"
BASELINE_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-post-applicability-coverage-census-v1-5cd6a3e32d5b4dcb03e5ecf0"
EDITORIAL_PROPOSAL = ROOT / ".bhf-data/bhf-commentary-candidates" / f"{ARTIFACT_VERSION}-{STARTING_SHA[:8]}" / "editorial-proposal/proposal.json"
TARGETS = (
    ("Psalms", 19),
    ("Psalms", 103),
    ("2 Kings", 4),
    ("Psalms", 2),
    ("Genesis", 5),
)
TARGET_PATHS = {
    "Psalms": ROOT / "framework/canonical_library/objects/books/psalms.json",
    "2 Kings": ROOT / "framework/canonical_library/objects/books/2-kings.json",
    "Genesis": ROOT / "framework/canonical_library/objects/books/genesis.json",
}
PSALM_2_HEADING = " Psalm 3 A Psalm of David, when he fled from Absalom his son."


class EnrichmentError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_immutable(path: Path, value: Any) -> None:
    payload = (canonical_json(value) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise EnrichmentError(f"immutable artifact collision: {path}")
        return
    path.write_bytes(payload)


def write_text_immutable(path: Path, value: str) -> None:
    payload = value.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise EnrichmentError(f"immutable artifact collision: {path}")
        return
    path.write_bytes(payload)


def slug(book: str, chapter: int) -> str:
    return f"{book.lower().replace(' ', '_')}_{chapter:03d}"


def reference(book: str, chapter: int) -> str:
    return bible.verse_range_reference(book, chapter)


def serialize(value: Any) -> Any:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return value.value
    return value


class OverlayLibrary:
    """Use stale SQLite for the population and replace only edited parents."""

    def __init__(self, base: Any, targets: Mapping[str, Mapping[str, Any]]):
        self.base = base
        self.targets = dict(targets)

    def retrieve_by_scripture_reference(self, passage_ref: str, **kwargs: Any) -> list[Any]:
        limit = int(kwargs.get("limit", 100))
        rows = list(self.base.retrieve_by_scripture_reference(passage_ref, limit=limit, include_placeholders=False))
        seen: set[str] = set()
        result: list[Any] = []
        for row in rows:
            object_id = str(getattr(getattr(row, "object", None), "id", ""))
            if object_id in self.targets:
                result.append(SimpleNamespace(object=self.targets[object_id], score=getattr(row, "score", 0.99)))
                seen.add(object_id)
            else:
                result.append(row)
        for object_id, target in sorted(self.targets.items()):
            if object_id not in seen and _target_overlaps(target, passage_ref):
                result.append(SimpleNamespace(object=target, score=0.99))
        return result[:limit]


def _target_overlaps(target: Mapping[str, Any], passage_ref: str) -> bool:
    from bhf_agent.presentation.references import references_overlap

    refs = [
        value.get("reference") if isinstance(value, Mapping) else value
        for value in (target.get("scripture_references") or [])
    ]
    return any(references_overlap(passage_ref, str(value)) for value in refs if value)


def load_targets() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(set(TARGET_PATHS.values())):
        data = read_json(path)
        result[str(data["id"])] = data
    return result


def safe_canonical_text(book: str, chapter: int) -> tuple[str, dict[str, Any]]:
    chapter_data = bible.resolve_chapter(book, chapter)
    original = bible.passage_text(chapter_data["verses"])
    rows = [dict(row) for row in chapter_data["verses"]]
    removed = False
    if book == "Psalms" and chapter == 2:
        for row in rows:
            if PSALM_2_HEADING in str(row.get("text", "")):
                row["text"] = str(row["text"]).replace(PSALM_2_HEADING, "")
                removed = True
        if not removed:
            raise EnrichmentError("Psalm 2 safe path expected the known Psalm 3 heading contamination")
    safe = bible.passage_text(rows)
    return safe, {
        "contamination_removed": removed,
        "original_text_sha256": sha256_bytes(original.encode("utf-8")),
        "safe_text_sha256": sha256_bytes(safe.encode("utf-8")),
        "source": "bounded_task_local_canonical_text_projection",
        "dataset_mutated": False,
    }


def max_verse(book: str, chapter: int) -> int:
    return max(int(row["verse"]) for row in bible.resolve_chapter(book, chapter)["verses"])


def verse_set(ref: str, book: str, chapter: int) -> set[int]:
    covered: set[int] = set()
    for span in parse_scripture_references(ref, book_alias_lookup=_BOOK_ALIASES):
        if span.book != bible.normalize_book_name(book):
            continue
        if span.start_chapter != chapter or (span.end_chapter or span.start_chapter) != chapter:
            continue
        first = span.start_verse or 1
        last = span.end_verse or max_verse(book, chapter)
        covered.update(range(first, min(last, max_verse(book, chapter)) + 1))
    return covered


def applicability(bundle: EvidenceBundle) -> dict[str, Any]:
    decisions = [evaluate_evidence_applicability(item, bundle.passage_ref) for item in bundle.evidence_items]
    rows = [decision.to_dict() for decision in decisions]
    legal = [item for item, decision in zip(bundle.evidence_items, decisions, strict=True) if decision.current_chapter_eligible]
    source_kinds = {}
    for item in bundle.evidence_items:
        kind = str((item.relevance_metadata or {}).get("source_kind") or "unknown")
        source_kinds[kind] = source_kinds.get(kind, 0) + 1
    return {
        "decisions": rows,
        "raw_evidence_count": len(bundle.evidence_items),
        "commentary_eligible_evidence_count": len(legal),
        "commentary_ineligible_evidence_count": len(bundle.evidence_items) - len(legal),
        "structured_child_evidence_count": sum((item.relevance_metadata or {}).get("source_kind") == "ckl_claim" for item in bundle.evidence_items),
        "inherited_legacy_evidence_count": sum(
            (item.relevance_metadata or {}).get("source_kind") == "ckl_legacy_field"
            and (item.relevance_metadata or {}).get("inherited_from_parent") is True
            for item in bundle.evidence_items
        ),
        "source_kind_counts": dict(sorted(source_kinds.items())),
        "exclusion_reason_counts": dict(sorted(
            {reason: sum(row["reason"] == reason for row in rows if not row["current_chapter_eligible"]) for reason in {row["reason"] for row in rows if not row["current_chapter_eligible"]}}.items()
        )),
        "legal_evidence_ids": sorted(item.id for item in legal),
    }


def normalize_claim(claim: str) -> str:
    return re.sub(r"\s+", " ", claim.casefold()).strip()


def historical_baseline(book: str, chapter: int) -> dict[str, Any]:
    path = next(BASELINE_ROOT.joinpath("chapters").glob(f"*_{slug(book, chapter)}.json"))
    row = read_json(path)
    return {
        "artifact": str(path.relative_to(ROOT)),
        "reference": row.get("reference"),
        "raw_evidence_bundle_evidence_count": row.get("raw_evidence_bundle_evidence_count"),
        "commentary_eligible_evidence_count": row.get("commentary_eligible_evidence_count"),
        "inherited_legacy_evidence_count": row.get("inherited_legacy_evidence_count"),
        "evidence_availability": row.get("evidence_availability"),
        "synthesis_unit_count": row.get("synthesis_unit_count"),
        "current_chapter_synthesis_count": row.get("current_chapter_synthesis_count"),
        "surrounding_passage_synthesis_count": row.get("surrounding_passage_synthesis_count"),
        "projected_idea_count": row.get("projected_idea_count"),
        "priority_provenance_path_count": row.get("priority_provenance_path_count"),
        "fallback_provenance_path_count": row.get("fallback_provenance_path_count"),
        "renderer_legal_path_count": row.get("renderer_legal_path_count"),
        "renderer_ambiguous_path_count": row.get("renderer_ambiguous_path_count"),
        "renderer_invalid_path_count": row.get("renderer_invalid_path_count"),
        "legal_commentary_verse_coverage": row.get("legal_commentary_verse_coverage", []),
        "evidence_hash": row.get("evidence_hash"),
        "synthesis_hash": row.get("synthesis_hash"),
    }


def build_chapter(book: str, chapter: int, library: Any) -> dict[str, Any]:
    ref = reference(book, chapter)
    bundle = get_chapter_evidence_bundle(book, chapter, canonical_library=library)
    if bundle is None:
        raise EnrichmentError(f"no evidence bundle for {ref}")
    synthesis = compile_chapter_synthesis(bundle, book=book, chapter=chapter)
    errors = validate_synthesis(synthesis, bundle)
    if errors:
        raise EnrichmentError(f"synthesis validation failed for {ref}: {errors}")
    safe_text, text_audit = safe_canonical_text(book, chapter)
    clusters = cluster_synthesis_units(
        synthesis.synthesis_units,
        bundle.evidence_items,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=safe_text,
    )
    projection = project_reader_level_ideas(synthesis, clusters, bundle.evidence_items)
    if not synthesis.synthesis_units:
        raise EnrichmentError(f"no synthesis units for {ref}; fail closed")
    envelope = build_ancestry_envelope(projection, synthesis, bundle.evidence_items)
    ancestry_audit = audit_ancestry_envelope(envelope, projection, synthesis)
    binding = build_provenance_binding_v2(envelope, synthesis, bundle.evidence_items)
    binding_audit = audit_provenance_binding_v2(binding, envelope, synthesis, bundle.evidence_items)
    presentation = present_binding(binding, synthesis, bundle.evidence_items)
    presentation_audit = audit_active_paths(binding, synthesis, bundle.evidence_items)
    if not ancestry_audit.get("valid") or not binding_audit.get("valid"):
        raise EnrichmentError(f"ancestry/provenance audit failed for {ref}")
    user_prompt = build_user_prompt(
        ref, book, chapter, safe_text, synthesis, bundle, prompt_version="1.8"
    )
    user_prompt = add_projection_to_prompt(user_prompt, projection)
    user_prompt = add_ancestry_envelope_to_prompt(user_prompt, envelope)
    user_prompt = add_provenance_binding_to_prompt_v2(user_prompt, envelope, binding)
    user_prompt, _ = add_presentation_to_prompt(
        user_prompt, envelope, binding, synthesis, bundle.evidence_items
    )
    app = applicability(bundle)
    legal = [item for item in bundle.evidence_items if item.id in set(app["legal_evidence_ids"])]
    source_map = {str(row.get("id")): row for row in bundle.provenance.get("sources", [])}
    source_resolution = {
        item.id: {
            "source_ids": list(item.source_ids),
            "resolved": all(source_id in source_map and source_map[source_id].get("source_type") != "unresolved-source-reference" for source_id in item.source_ids),
        }
        for item in legal
    }
    duplicate_groups: dict[str, list[str]] = {}
    for item in legal:
        duplicate_groups.setdefault(normalize_claim(item.claim), []).append(item.id)
    duplicate_groups = {key: sorted(value) for key, value in duplicate_groups.items() if len(value) > 1}
    raw_verses = set().union(*(verse_set(anchor, book, chapter) for item in bundle.evidence_items for anchor in item.passage_anchors)) if bundle.evidence_items else set()
    legal_verses = set().union(*(verse_set(anchor, book, chapter) for item in legal for anchor in item.passage_anchors)) if legal else set()
    path_counts = dict(presentation_audit.get("counts", {}))
    current_path_hard_errors = [
        path for path in presentation_audit.get("paths", [])
        if path.get("passage_scope") == "CURRENT_CHAPTER"
        and path.get("canonicalization", {}).get("classification") in {"AMBIGUOUS", "INVALID_SOURCE_REFERENCE"}
    ]
    audit = {
        "raw_evidence_count": len(bundle.evidence_items),
        "commentary_eligible_evidence_count": len(legal),
        "inherited_legacy_evidence_count": app["inherited_legacy_evidence_count"],
        "evidence_availability": synthesis.evidence_availability,
        "synthesis_unit_count": len(synthesis.synthesis_units),
        "current_chapter_synthesis_count": sum(unit.passage_scope == "CURRENT_CHAPTER" for unit in synthesis.synthesis_units),
        "surrounding_passage_synthesis_count": sum(unit.passage_scope == "SURROUNDING_PASSAGE" for unit in synthesis.synthesis_units),
        "projected_core_idea_count": sum(idea.importance == "CORE" for idea in projection.ideas),
        "projected_relevant_idea_count": sum(idea.importance == "RELEVANT" for idea in projection.ideas),
        "projected_idea_count": len(projection.ideas),
        "priority_provenance_path_count": int(binding.get("binding_audit", {}).get("priority_path_count", 0)),
        "fallback_provenance_path_count": int(binding.get("binding_audit", {}).get("fallback_renderable_path_count", 0)),
        "renderer_legal_path_count": int(path_counts.get("VALID_ALREADY", 0)) + int(path_counts.get("SAFE_FULL_CHAPTER_SCOPE", 0)),
        "renderer_ambiguous_path_count": int(path_counts.get("AMBIGUOUS", 0)),
        "renderer_invalid_path_count": int(path_counts.get("INVALID_SOURCE_REFERENCE", 0)),
        "renderer_current_chapter_hard_error_count": len(current_path_hard_errors),
        "raw_verse_coverage": sorted(raw_verses),
        "legal_commentary_verse_coverage": sorted(legal_verses),
        "legal_commentary_verse_coverage_percentage": round(100 * len(legal_verses) / max_verse(book, chapter), 2),
        "distinct_claim_family_count": len({item.category for item in legal}),
        "distinct_claim_families": sorted({item.category for item in legal}),
        "duplicate_legal_claim_groups": duplicate_groups,
        "duplicate_inflation_count": sum(len(ids) - 1 for ids in duplicate_groups.values()),
        "high_legacy_leak_count": sum((item.relevance_metadata or {}).get("source_kind") == "ckl_legacy_field" for item in legal),
        "all_legal_source_ids_resolve": all(value["resolved"] for value in source_resolution.values()),
        "ancestry_valid": bool(ancestry_audit.get("valid")),
        "provenance_binding_valid": bool(binding_audit.get("valid")),
        "renderer_preflight_no_hard_errors": not current_path_hard_errors,
        "evidence_hash": bundle.evidence_hash,
        "synthesis_hash": synthesis.synthesis_hash,
        "projection_hash": projection.projection_hash,
        "ancestry_envelope_hash": envelope.get("envelope_hash"),
        "provenance_binding_hash": binding.get("binding_hash"),
        "renderer_presentation_hash": presentation.get("presentation_hash"),
    }
    audit["deterministic_pass"] = all((
        audit["renderer_legal_path_count"] >= 1,
        audit["ancestry_valid"],
        audit["provenance_binding_valid"],
        audit["renderer_preflight_no_hard_errors"],
        audit["high_legacy_leak_count"] == 0,
        audit["all_legal_source_ids_resolve"],
        audit["duplicate_inflation_count"] == 0,
        audit["high_legacy_leak_count"] == 0,
    ))
    return {
        "reference": ref,
        "book": book,
        "chapter": chapter,
        "slug": slug(book, chapter),
        "before": historical_baseline(book, chapter),
        "after": audit,
        "text_audit": text_audit,
        "applicability": app,
        "bundle": serialize(bundle),
        "synthesis": serialize(synthesis),
        "clusters": serialize(clusters),
        "projection": serialize(projection),
        "ancestry": envelope,
        "ancestry_audit": ancestry_audit,
        "provenance": binding,
        "provenance_audit": binding_audit,
        "renderer_presentation": presentation,
        "renderer_preflight": presentation_audit,
        "system_prompt": system_prompt_for_version("1.8"),
        "user_prompt": user_prompt,
        "source_resolution": source_resolution,
    }


def write_artifact(rows: list[dict[str, Any]], targets: Mapping[str, Mapping[str, Any]], contracts: Mapping[str, Any]) -> dict[str, Any]:
    manifest = {
        "artifact_version": ARTIFACT_VERSION,
        "artifact_identity": sha256_json({"version": ARTIFACT_VERSION, "starting_sha": STARTING_SHA, "references": [row["reference"] for row in rows]}),
        "starting_commit": STARTING_SHA,
        "expected_branch": EXPECTED_BRANCH,
        "model": {"provider": "openai", "model": "gpt-5.6-sol", "effort": "medium", "fresh_generation_per_passing_chapter": True},
        "prompt_version": "1.8",
        "model_calls_made": 0,
        "ckl_mutation": "authored child claims were applied before this deterministic rebuild; this tool performs no CKL mutation",
        "chapters": [{"reference": row["reference"], "slug": row["slug"], "deterministic_pass": row["after"]["deterministic_pass"]} for row in rows],
    }
    write_immutable(ARTIFACT_ROOT / "manifest.json", manifest)
    write_immutable(ARTIFACT_ROOT / "contract-identities.json", contracts)
    if EDITORIAL_PROPOSAL.exists() and EDITORIAL_PROPOSAL != ARTIFACT_ROOT / "editorial-proposal/proposal.json":
        write_immutable(ARTIFACT_ROOT / "editorial-proposal/proposal.json", read_json(EDITORIAL_PROPOSAL))
    for object_id, target in sorted(targets.items()):
        if object_id in {"psalms", "2-kings", "genesis"}:
            write_immutable(ARTIFACT_ROOT / "source-identities" / f"{object_id}.json", {
                "object_id": object_id,
                "path": str(TARGET_PATHS["Psalms" if object_id == "psalms" else "2 Kings" if object_id == "2-kings" else "Genesis"].relative_to(ROOT)),
                "object_sha256": sha256_json(target),
                "source_ids": sorted(str(source.get("id")) for source in target.get("sources", []) if source.get("id")),
                "accepted_claim_ids": sorted(
                    str(claim.get("id"))
                    for claim in target.get("claims", [])
                    if str(claim.get("id", "")).startswith(
                        ("psalm-19", "psalm-103", "psalm-2", "second-kings-4", "genesis-5")
                    )
                ),
            })
    for row in rows:
        key = row["slug"]
        base = ARTIFACT_ROOT
        write_immutable(base / "before/metrics" / f"{key}.json", row["before"])
        write_immutable(base / "after/evidence-bundles" / f"{key}.json", row["bundle"])
        write_immutable(base / "after/synthesis" / f"{key}.json", row["synthesis"])
        write_immutable(base / "after/applicability" / f"{key}.json", row["applicability"])
        write_immutable(base / "after/projection" / f"{key}.json", row["projection"])
        write_immutable(base / "after/ancestry" / f"{key}.json", {"envelope": row["ancestry"], "audit": row["ancestry_audit"]})
        write_immutable(base / "after/provenance" / f"{key}.json", {"binding": row["provenance"], "audit": row["provenance_audit"]})
        write_immutable(base / "after/renderer-preflight" / f"{key}.json", row["renderer_preflight"])
        write_immutable(base / "after/renderer-input" / f"{key}/metadata.json", {"reference": row["reference"], "text_audit": row["text_audit"], "after": row["after"], "source_resolution": row["source_resolution"]})
        write_text_immutable(base / "after/renderer-input" / f"{key}/system_prompt.txt", row["system_prompt"])
        write_text_immutable(base / "after/renderer-input" / f"{key}/user_prompt.txt", row["user_prompt"])
        write_immutable(base / "after/metrics" / f"{key}.json", row["after"])
    comparison = {row["reference"]: {"before": row["before"], "after": row["after"]} for row in rows}
    write_immutable(ARTIFACT_ROOT / "deterministic-report.json", {
        "artifact_version": ARTIFACT_VERSION,
        "criteria": {
            "minimum_passing_chapters_for_model": 4,
            "required_renderer_legal_path_count": 1,
            "required_no_legacy_promotion": True,
            "required_no_duplicate_inflation": True,
            "required_no_high_confidence_legacy_leak": True,
        },
        "chapters": comparison,
        "passing_chapter_count": sum(row["after"]["deterministic_pass"] for row in rows),
        "recommendation": "READY_FOR_BROADER_PILOT" if sum(row["after"]["deterministic_pass"] for row in rows) >= 4 else "MORE_TARGETED_ENRICHMENT_REQUIRED",
        "model_calls_permitted": sum(row["after"]["deterministic_pass"] for row in rows) >= 4,
    })
    checksums = {}
    for path in sorted(ARTIFACT_ROOT.rglob("*")):
        if path.is_file() and path.name != "checksums.json":
            checksums[str(path.relative_to(ARTIFACT_ROOT))] = sha256_file(path)
    write_immutable(ARTIFACT_ROOT / "checksums.json", checksums)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.dry_run == args.write:
        parser.error("choose exactly one of --dry-run or --write")
    contracts = contract_snapshot()
    if not contracts.get("all_protected_contracts_unchanged"):
        raise EnrichmentError("protected contract fingerprint changed")
    targets = load_targets()
    base = load_canonical_library(config=CKLRepositoryConfig(
        backend="sqlite",
        database_path=str(ROOT / ".bhf/ckl.sqlite"),
        json_root=str(ROOT / "framework/canonical_library"),
        stale_database_policy="ignore",
        read_only=True,
    ))
    target_parents = {object_id: target for object_id, target in targets.items() if object_id in {"psalms", "2-kings", "genesis"}}
    rows = [build_chapter(book, chapter, OverlayLibrary(base, target_parents)) for book, chapter in TARGETS]
    print(json.dumps({"chapters": [{"reference": row["reference"], "after": row["after"]} for row in rows], "passing_chapter_count": sum(row["after"]["deterministic_pass"] for row in rows)}, indent=2, sort_keys=True))
    if args.write:
        write_artifact(rows, target_parents, contracts)
        print(f"wrote {ARTIFACT_ROOT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
