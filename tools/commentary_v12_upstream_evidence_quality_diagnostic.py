"""Deterministic, read-only audit of the v1.2 commentary evidence path.

This module deliberately stops at diagnosis.  It reads immutable v1.2 inputs,
the current CKL in read-only mode, and canonical Bible data; it never writes
to those inputs and makes no model calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from bhf_agent import bible
from bhf_agent.ckl import load_canonical_library
from bhf_agent.chapter_commentary.synthesis.compiler import compile_chapter_synthesis
from bhf_agent.presentation.models import EntityRef, EvidenceBundle, EvidenceItem
from bhf_agent.presentation.references import _BOOK_ALIASES
from framework.canonical_library.repository import CKLRepositoryConfig
from framework.canonical_library.scripture import (
    parse_scripture_query,
    parse_scripture_references,
    scripture_reference_overlaps,
)


ROOT = Path(__file__).resolve().parents[1]
PRESENTATION_DIR = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-reader-provenance-renderer-reference-presentation-v1-bounded-validation-v1-ce695db52b3ad2d0e6f8"
CANONICAL_PATH = ROOT / "bhf_agent/data/asv_bible.json"
CASES = {
    "2_kings_004": {
        "book": "2 Kings", "chapter": 4, "reference": "2 Kings 4",
        "bundle": ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-007/evidence-bundles/2_kings_004.json",
        "people": {"elisha"},
        "spans": [(1, 7), (8, 17), (18, 37), (38, 41), (42, 44)],
    },
    "psalms_103": {
        "book": "Psalms", "chapter": 103, "reference": "Psalms 103",
        "bundle": ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-007/evidence-bundles/psalms_103.json",
        "spans": [(1, 5), (6, 7), (8, 13), (14, 18), (19, 22)],
    },
    "psalms_019": {
        "book": "Psalms", "chapter": 19, "reference": "Psalms 19",
        "bundle": ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-007/evidence-bundles/psalms_019.json",
        "archaeology": {
            "arad-ostraca", "caesarea-maritima-excavations", "ein-gedi-scroll",
            "herodium-excavations", "kurkh-monolith", "masada-excavations",
            "pool-of-bethesda-excavation", "samaria-ostraca", "samaria-palace",
            "shiloh-excavations",
        },
        "torah": {"what-does-torah-mean"},
        "spans": [(1, 6), (7, 11), (12, 14)],
    },
    "numbers_002": {
        "book": "Numbers", "chapter": 2, "reference": "Numbers 2",
        "bundle": ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-scale-pilot/wave-a/canary/evidence-bundles/numbers_002.json",
        "spans": [(1, 34)],
    },
    "numbers_001": {
        "book": "Numbers", "chapter": 1, "reference": "Numbers 1",
        "bundle": ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-008/evidence-bundles/numbers_001.json",
        "spans": [(1, 54)],
    },
}


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bundle_from_dict(data: dict[str, Any]) -> EvidenceBundle:
    entities = {
        bucket: [EntityRef(**entity) for entity in data.get("entities", {}).get(bucket, [])]
        for bucket in ("people", "places", "groups", "events", "artifacts")
    }
    return EvidenceBundle(
        passage_ref=data["passage_ref"],
        entities=entities,
        evidence_items=[EvidenceItem(**item) for item in data.get("evidence_items", [])],
        geography=data.get("geography", {}),
        provenance=data.get("provenance", {}),
        version=data.get("version", "1.0"),
        evidence_hash=data.get("evidence_hash", ""),
    )


def current_ckl() -> Any:
    return load_canonical_library(
        config=CKLRepositoryConfig(
            backend="sqlite",
            database_path=str(ROOT / ".bhf/ckl.sqlite"),
            json_root=str(ROOT / "framework/canonical_library"),
            stale_database_policy="ignore",
            read_only=True,
        )
    )


def query_span(reference: str) -> Any:
    return parse_scripture_query(reference, book_alias_lookup=_BOOK_ALIASES)


def verse_set(reference: str, *, book: str, chapter: int) -> set[int]:
    """Return only verses in the queried chapter covered by reference."""
    result: set[int] = set()
    query = query_span(reference)
    if query is None or query.book != bible.normalize_book_name(book):
        return result
    end_chapter = query.end_chapter or query.start_chapter
    if query.start_chapter != chapter or end_chapter != chapter:
        return result
    max_verse = max(int(v["verse"]) for v in bible.resolve_chapter(book, chapter)["verses"])
    first = query.start_verse or 1
    last = query.end_verse or max_verse
    return set(range(first, min(last, max_verse) + 1))


def refs_verses(refs: Iterable[str], *, book: str, chapter: int) -> set[int]:
    covered: set[int] = set()
    for ref in refs:
        covered.update(verse_set(str(ref), book=book, chapter=chapter))
    return covered


def object_dict(obj: Any) -> dict[str, Any]:
    value = obj.to_dict() if hasattr(obj, "to_dict") else obj
    return dict(value) if isinstance(value, dict) else {}


def stored_reference_records(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Capture raw stored reference records without normalizing or inferring."""
    records: list[dict[str, Any]] = []
    for value in raw.get("scripture_references", []) or []:
        records.append({"location": "object.scripture_references", "value": value})
    for field in ("evidence_items", "claims", "interpretive_notes"):
        values = raw.get(field, []) or []
        if isinstance(values, dict):
            values = list(values.values())
        for index, entry in enumerate(values):
            if not isinstance(entry, dict):
                continue
            refs = entry.get("scripture_references", entry.get("passage_anchors", [])) or []
            for value in refs:
                records.append({"location": f"{field}[{index}].scripture_references", "value": value})
    return records


def retrieval_trace(raw: dict[str, Any], *, query: str, result: Any, source_path: Path | None) -> dict[str, Any]:
    q = query_span(query)
    matches: list[dict[str, Any]] = []
    kinds: set[str] = set()
    for record in stored_reference_records(raw):
        value = record["value"]
        text = value.get("reference") if isinstance(value, dict) else str(value)
        spans = parse_scripture_references(str(text), book_alias_lookup=_BOOK_ALIASES)
        if q and any(scripture_reference_overlaps(q, span) for span in spans):
            matches.append(record)
            kinds.add(record["location"].split(".")[0])
    if not kinds:
        reason = "unavailable: no raw matching reference record was found"
    else:
        reason = "indexed scripture interval overlap in " + ", ".join(sorted(kinds))
    return {
        "ckl_object_id": raw.get("id"),
        "ckl_object_type": raw.get("type"),
        "ckl_title": raw.get("title"),
        "originating_ckl_path": str(source_path.relative_to(ROOT)) if source_path and source_path.exists() else "unavailable",
        "originating_ckl_file_sha256": sha256_file(source_path) if source_path and source_path.exists() else "unavailable",
        "raw_stored_scripture_references": raw.get("scripture_references", "unavailable"),
        "relationship_notes_attached_to_matching_references": [
            item for item in matches if isinstance(item.get("value"), dict)
        ],
        "retrieval_match_reason": reason,
        "retrieval_match_type": getattr(result, "match_type", "unavailable") if result is not None else "unavailable",
        "retrieval_match_locations": sorted(kinds) if kinds else ["unavailable"],
        "retrieval_score": result.score if result is not None else "unavailable",
        "retrieval_rank": "unavailable",
        "queried_chapter": query,
        "exact_matched_references": matches,
        "canonical_result_identity": {
            "object_id": raw.get("id"),
            "object_json_sha256": sha256_bytes(stable_json(raw).encode()),
        },
        "matched_fields": list(getattr(result, "matched_fields", []) or []) if result else ["unavailable"],
    }


def classify(case_key: str, item: dict[str, Any]) -> tuple[str, str]:
    meta = item.get("relevance_metadata", {})
    parent = meta.get("parent_object_id") or (item.get("related_entity_ids") or [None])[0]
    field = meta.get("field", "")
    if case_key == "2_kings_004":
        if parent == "elisha":
            return "GENERIC_CONTEXT", "Elisha is a chapter character, but the inherited legacy field is generic rather than episode-specific."
        return "CLEAR_FALSE_POSITIVE", "A non-character profile inherited the same parent anchor; its generic profile does not materially explain this chapter."
    if case_key == "psalms_019":
        if parent in CASES[case_key]["archaeology"]:
            return "CLEAR_FALSE_POSITIVE", "The archaeological object is not tied to Psalm 19 by a specific claim; its legacy field inherited the broad Psalm 19:1-6 anchor."
        if parent in CASES[case_key]["torah"]:
            return "DEFENSIBLE_CONTEXT", "The Torah entry makes a specific, passage-relevant comparison for Psalm 19:7-11."
        return "GENERIC_CONTEXT", "The thematic entry is related to law/word concepts but its legacy field remains generic and not materially passage-specific."
    if case_key == "psalms_103":
        return "GENERIC_CONTEXT", "The mercy/grace legacy field is a broad thematic statement; it does not add a distinct, passage-specific claim or chapter-span coverage."
    if case_key == "numbers_002":
        return "DEFENSIBLE_CONTEXT", "The disputed sanctuary comparison is a specific contextual claim for the chapter-wide camp arrangement."
    if case_key == "numbers_001":
        if field == "interpretive_notes":
            return "DEFENSIBLE_CONTEXT", "The note is an explicitly anchored interpretive or disputed question about Numbers 1."
        return "DIRECTLY_RELEVANT", "The structured claim is explicitly about Numbers 1's setting, literary movement, or census structure."
    return "UNKNOWN", "No deterministic case rule."


def normalize_claim(text: str, parent_title: str = "") -> str:
    value = text.casefold()
    if parent_title:
        value = value.replace(parent_title.casefold(), "<parent>")
    value = re.sub(r"[^a-z0-9<>]+", " ", value)
    return " ".join(value.split())


def duplicate_groups(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group exact/near duplicate claims deterministically.

    Exact groups use equal normalized text.  Near groups require the same
    category/field and token Jaccard >= .55 or SequenceMatcher >= .78.
    """
    rows = sorted(items, key=lambda x: x["evidence_item_id"])
    parent_titles = {r["evidence_item_id"]: str(r.get("ckl_title") or "") for r in rows}
    normalized = {r["evidence_item_id"]: normalize_claim(r.get("claim", ""), parent_titles[r["evidence_item_id"]]) for r in rows}
    groups: list[list[str]] = []
    for row in rows:
        eid = row["evidence_item_id"]
        target: list[str] | None = None
        for group in groups:
            candidate = next(x for x in group if x in normalized)
            a, b = set(normalized[eid].split()), set(normalized[candidate].split())
            jaccard = len(a & b) / len(a | b) if a | b else 1.0
            ratio = SequenceMatcher(None, normalized[eid], normalized[candidate]).ratio()
            same_shape = row.get("category") == next(x for x in rows if x["evidence_item_id"] == candidate).get("category") and row.get("field") == next(x for x in rows if x["evidence_item_id"] == candidate).get("field")
            if normalized[eid] == normalized[candidate] or (same_shape and (jaccard >= 0.55 or ratio >= 0.78)):
                target = group
                break
        if target is None:
            groups.append([eid])
        else:
            target.append(eid)
    return [
        {"group_id": f"duplicate_group_{index:03d}", "evidence_item_ids": sorted(group), "size": len(group)}
        for index, group in enumerate(groups, 1) if len(group) > 1
    ]


def selected_blocks(parsed: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    selected: dict[str, dict[str, Any]] = {}
    blocks: dict[str, dict[str, Any]] = {}
    payload = parsed.get("raw_renderer_payload", {})
    for section in payload.get("sections", []) or []:
        for block in section.get("blocks", []) or []:
            block_id = str(block.get("block_id") or block.get("id") or "")
            blocks[block_id] = {"section_kind": section.get("kind"), "section_title": section.get("title"), "final_block": block.get("text", block.get("body", ""))}
            for path_id in block.get("provenance_refs", []) or []:
                selected[path_id] = {"block_id": block_id, **blocks[block_id]}
    return selected, blocks


def path_records(binding: dict[str, Any]) -> list[dict[str, Any]]:
    return [*binding.get("fallback_renderable_paths", []), *binding.get("priority_paths", [])]


def production_input_path(slug: str) -> Path | None:
    candidates = sorted(PRESENTATION_DIR.glob(f"renderer-input/*_{slug}/user_prompt.txt"))
    return candidates[0] if candidates else None


def parsed_path(slug: str) -> Path:
    return next(PRESENTATION_DIR.glob(f"attempts/*_{slug}/attempt-001/parsed.json"))


def max_verse(book: str, chapter: int) -> int:
    return max(int(v["verse"]) for v in bible.resolve_chapter(book, chapter)["verses"])


def make_case_report(case_key: str, lib: Any) -> dict[str, Any]:
    spec = CASES[case_key]
    bundle_raw = read_json(spec["bundle"])
    bundle = bundle_from_dict(bundle_raw)
    synthesis = compile_chapter_synthesis(bundle, book=spec["book"], chapter=spec["chapter"])
    binding = read_json(PRESENTATION_DIR / f"provenance-bindings-v2/{case_key}.json")
    parsed = read_json(parsed_path(case_key))
    selected, _ = selected_blocks(parsed)
    path_by_eid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in path_records(binding):
        path = dict(record.get("path") or {})
        path["path_id"] = record.get("path_id")
        path["path_class"] = record.get("path_class", "unavailable")
        path["path_hash"] = record.get("path_hash", "unavailable")
        for eid in record.get("evidence_ids", []) or []:
            path_by_eid[eid].append(path)
    unit_by_eid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in synthesis.synthesis_units:
        for eid in unit.evidence_ids:
            unit_by_eid[eid].append(unit.to_dict())

    retrieval_results = lib.retrieve_by_scripture_reference(spec["reference"], limit=100, include_placeholders=False)
    retrieval_by_id = {r.object.id: r for r in retrieval_results}
    retrieval_audit: list[dict[str, Any]] = []
    object_raw_by_id: dict[str, dict[str, Any]] = {}
    for rank, result in enumerate(retrieval_results, 1):
        raw = object_dict(result.object)
        object_raw_by_id[result.object.id] = raw
        source_path = lib.source_path_for(result.object.id)
        audit = retrieval_trace(raw, query=f"{spec['book']} {spec['chapter']}:1-{max_verse(spec['book'], spec['chapter'])}", result=result, source_path=source_path)
        audit["retrieval_rank"] = rank
        audit["object_relevance_classification"] = "unavailable"
        audit["object_relevance_rationale"] = "unavailable"
        retrieval_audit.append(audit)

    evidence_trace: list[dict[str, Any]] = []
    for item in bundle.evidence_items:
        raw_meta = item.relevance_metadata or {}
        parent_id = raw_meta.get("parent_object_id") or (item.related_entity_ids[0] if item.related_entity_ids else None)
        raw_object = object_raw_by_id.get(parent_id, {})
        result = retrieval_by_id.get(parent_id)
        if result is None and parent_id:
            result = lib.retrieve_by_id(parent_id, include_placeholders=False)
            if result is not None:
                raw_object = object_dict(result.object)
        source_path = lib.source_path_for(parent_id) if parent_id else None
        classification, rationale = classify(case_key, item.to_dict())
        units = unit_by_eid.get(item.id, [])
        paths = path_by_eid.get(item.id, [])
        selected_paths = [p for p in paths if p.get("path_id") in selected]
        evidence_trace.append({
            "ckl_object_id": parent_id or "unavailable",
            "ckl_object_type": raw_object.get("type", "unavailable"),
            "ckl_title": raw_object.get("title", raw_meta.get("parent_title", "unavailable")),
            "originating_ckl_file_or_database_identity": {
                "path": str(source_path.relative_to(ROOT)) if source_path and source_path.exists() else "unavailable",
                "sha256": sha256_file(source_path) if source_path and source_path.exists() else "unavailable",
                "database": str(ROOT / ".bhf/ckl.sqlite") if result is not None else "unavailable",
            },
            "raw_stored_scripture_references": raw_object.get("scripture_references", "unavailable"),
            "relationship_notes_attached_to_scripture_reference": [
                record for record in stored_reference_records(raw_object)
                if isinstance(record.get("value"), dict)
                and record["value"].get("reference") in item.passage_anchors
            ],
            "retrieval_match_reason": "scripture interval overlap; evidence item was then produced from the matched parent object",
            "retrieval_match_type": "scripture",
            "retrieval_score_ranking": {"score": result.score if result else "unavailable", "rank": "unavailable"},
            "queried_chapter": spec["reference"],
            "exact_matched_reference": item.passage_anchors,
            "canonical_result_identity": {"object_id": parent_id or "unavailable", "object_json_sha256": sha256_bytes(stable_json(raw_object).encode()) if raw_object else "unavailable"},
            "evidence_item_id": item.id,
            "evidence_category": item.category,
            "evidence_confidence": item.confidence,
            "passage_anchors": item.passage_anchors,
            "source_ids": item.source_ids,
            "claim": item.claim,
            "synthesis_ids": [u["id"] for u in units],
            "synthesis_kind": [u["kind"] for u in units],
            "synthesis_confidence": [u["confidence"] for u in units],
            "interpretation_level": [u["interpretation_level"] for u in units],
            "passage_scope": [u["passage_scope"] for u in units],
            "source_anchors": [u["source_anchors"] for u in units],
            "verse_refs": [u["verse_refs"] for u in units],
            "explicit_significance": [u.get("metadata", {}).get("explicit_significance", "unavailable") for u in units],
            "support_count": [u.get("metadata", {}).get("support_count", "unavailable") for u in units],
            "resulting_provenance_path_ids": [p.get("path_id") for p in paths],
            "selected_by_renderer": bool(selected_paths),
            "selected_path_ids": [p.get("path_id") for p in selected_paths],
            "final_blocks": [selected[p.get("path_id")] for p in selected_paths],
            "relevance_classification": classification,
            "relevance_rationale": rationale,
            "relevance_metadata": raw_meta,
        })

    for audit in retrieval_audit:
        evidence_parents = {t["ckl_object_id"] for t in evidence_trace}
        oid = audit["ckl_object_id"]
        if case_key == "2_kings_004":
            audit["object_relevance_classification"] = "GENERIC_CONTEXT" if oid == "elisha" else "CLEAR_FALSE_POSITIVE"
            audit["object_relevance_rationale"] = "Actual chapter character but generic inherited fields." if oid == "elisha" else "Non-character profile entered through shared inherited 2 Kings 4:1-7 anchor."
        elif case_key == "psalms_019":
            audit["object_relevance_classification"] = "CLEAR_FALSE_POSITIVE" if oid in spec["archaeology"] else ("DEFENSIBLE_CONTEXT" if oid in spec["torah"] else "GENERIC_CONTEXT")
            audit["object_relevance_rationale"] = "See evidence-level classification; word-study object contributed no bundled evidence because legacy-only word studies fail closed."
        elif case_key == "psalms_103":
            audit["object_relevance_classification"] = "GENERIC_CONTEXT"
            audit["object_relevance_rationale"] = "Broad mercy/grace theme; three word-study objects are retrieval-only and contributed no evidence."
        else:
            audit["object_relevance_classification"] = "DEFENSIBLE_CONTEXT" if oid in evidence_parents else "GENERIC_CONTEXT"
            audit["object_relevance_rationale"] = "Classification is based on the exact immutable bundle evidence, not the explicit anchor alone."

    all_verses = set(range(1, max_verse(spec["book"], spec["chapter"]) + 1))
    any_covered = refs_verses([a for item in bundle.evidence_items for a in item.passage_anchors], book=spec["book"], chapter=spec["chapter"])
    useful_classes = {"DIRECTLY_RELEVANT", "DEFENSIBLE_CONTEXT"}
    useful_covered = refs_verses([a for item in evidence_trace if item["relevance_classification"] in useful_classes for a in item["passage_anchors"]], book=spec["book"], chapter=spec["chapter"])
    coverage = []
    for first, last in spec["spans"]:
        span = set(range(first, last + 1))
        any_span = sorted(span & any_covered)
        useful_span = sorted(span & useful_covered)
        coverage.append({
            "requested_interval": f"{spec['book']} {spec['chapter']}:{first}-{last}",
            "any_evidence_verses": any_span,
            "useful_evidence_verses": useful_span,
            "any_evidence": bool(any_span),
            "genuinely_useful_evidence": bool(useful_span),
            "only_generic_or_suspicious": bool(any_span) and not bool(useful_span),
            "selected_commentary_ancestry": bool(refs_verses([a for p in path_records(binding) if p.get("path_id") in selected for a in (p.get("path", {}).get("verse_refs", []) or [])], book=spec["book"], chapter=spec["chapter"]) & span),
        })

    duplicate_input = [{
        "evidence_item_id": row["evidence_item_id"], "claim": row["claim"],
        "category": row["evidence_category"], "field": row["relevance_metadata"].get("field", ""),
        "ckl_title": row["ckl_title"],
    } for row in evidence_trace]
    duplicates = duplicate_groups(duplicate_input)
    useful_ids = {row["evidence_item_id"] for row in evidence_trace if row["relevance_classification"] in useful_classes}
    selected_useful = {row["evidence_item_id"] for row in evidence_trace if row["relevance_classification"] in useful_classes and row["selected_by_renderer"]}
    selected_path_ids = sorted({p for row in evidence_trace for p in row["selected_path_ids"]})
    raw_paths = path_records(binding)
    useful_path_ids = sorted({p.get("path_id") for p in raw_paths if p.get("path_id") in {path_id for row in evidence_trace if row["evidence_item_id"] in useful_ids for path_id in row["resulting_provenance_path_ids"]}})
    selected_useful_path_ids = sorted(set(useful_path_ids) & set(selected_path_ids))
    useful_unselected_path_ids = sorted(set(useful_path_ids) - set(selected_path_ids))
    useful_path_choices = {}
    for path in raw_paths:
        if path.get("path_id") not in useful_path_ids:
            continue
        payload = path.get("path", {})
        choice_key = stable_json({"evidence_ids": path.get("evidence_ids", []), "synthesis_id": payload.get("synthesis_id"), "kind": payload.get("kind"), "verse_refs": payload.get("verse_refs", [])})
        useful_path_choices.setdefault(choice_key, []).append(path.get("path_id"))
    selected_choice_count = sum(bool(set(ids) & set(selected_path_ids)) for ids in useful_path_choices.values())
    unselected_choice_count = sum(not bool(set(ids) & set(selected_path_ids)) for ids in useful_path_choices.values())
    distinct_useful_claims = len({normalize_claim(row["claim"], row["ckl_title"]) for row in evidence_trace if row["evidence_item_id"] in useful_ids})
    synthesis_classification = []
    for unit in synthesis.synthesis_units:
        classifications = sorted({row["relevance_classification"] for row in evidence_trace if row["evidence_item_id"] in unit.evidence_ids})
        synthesis_classification.append({
            "synthesis_id": unit.id, "synthesis_kind": unit.kind, "synthesis_confidence": unit.confidence,
            "interpretation_level": unit.interpretation_level, "passage_scope": unit.passage_scope,
            "evidence_ids": unit.evidence_ids, "relevance_classifications": classifications,
            "selected_path_ids": sorted({p for eid in unit.evidence_ids for p in next((row["resulting_provenance_path_ids"] for row in evidence_trace if row["evidence_item_id"] == eid), []) if p in selected_path_ids}),
        })
    distinct_source_objects = sorted({row["ckl_object_id"] for row in evidence_trace if row["ckl_object_id"] != "unavailable"})
    distinct_kinds = sorted({p.get("path", {}).get("kind", "unavailable") for p in raw_paths})
    distinct_scopes = sorted({tuple(p.get("path", {}).get("verse_refs", [])) for p in raw_paths})
    report = {
        "case": case_key,
        "reference": spec["reference"],
        "source_bundle": {"path": str(spec["bundle"].relative_to(ROOT)), "sha256": sha256_file(spec["bundle"]), "recorded_evidence_hash": bundle.evidence_hash},
        "production_input": {"path": str(production_input_path(case_key).relative_to(ROOT)) if production_input_path(case_key) else "unavailable", "sha256": sha256_file(production_input_path(case_key)) if production_input_path(case_key) else "unavailable"},
        "reproduced_synthesis": {"synthesis_hash": synthesis.synthesis_hash, "unit_count": len(synthesis.synthesis_units), "expected_binding_synthesis_hash": binding.get("paths", [{}])[0].get("path", {}).get("ancestry_hashes", {}).get("synthesis_hash", "unavailable")},
        "retrieval": {"query": f"{spec['book']} {spec['chapter']}:1-{max_verse(spec['book'], spec['chapter'])}", "result_count": len(retrieval_results), "objects": retrieval_audit, "mechanism": "book-index candidate lookup plus parsed ScriptureReferenceSpan interval overlap; no string/token, relationship, reverse-reference, or cross-reference expansion"},
        "evidence_trace": evidence_trace,
        "synthesis_units": [u.to_dict() for u in synthesis.synthesis_units],
        "synthesis_classification": synthesis_classification,
        "paths": [{"path_id": p.get("path_id"), "path_class": p.get("path_class", "unavailable"), "evidence_ids": p.get("evidence_ids", []), "path": p.get("path", {}), "selected": p.get("path_id") in selected} for p in raw_paths],
        "renderer": {
            "selected_path_ids": selected_path_ids,
            "quality_gate": parsed.get("validation_result", {}).get("gate_result", "unavailable"),
            "gate_diagnostics": {key: parsed.get("validation_result", {}).get(key, "unavailable") for key in ("core_coverage", "weighted_coverage", "category_coverage", "eligible_idea_utilization", "projected_idea_count", "final_chapter_classification", "rejection_codes")},
            "qualitative_review": parsed.get("validation_result", {}).get("qualitative_review", {}),
            "word_count": parsed.get("validation_result", {}).get("word_count", "unavailable"),
        },
        "duplicate_groups": duplicates,
        "coverage": {"chapter_verse_count": len(all_verses), "any_evidence_verses": sorted(any_covered), "useful_evidence_verses": sorted(useful_covered), "any_evidence_percentage": round(100 * len(any_covered) / len(all_verses), 2), "useful_evidence_percentage": round(100 * len(useful_covered) / len(all_verses), 2), "spans": coverage},
        "metrics": {
            "raw_evidence_count": len(bundle.evidence_items), "raw_synthesis_count": len(synthesis.synthesis_units), "raw_fallback_or_priority_path_count": len(raw_paths),
            "directly_relevant_count": sum(row["relevance_classification"] == "DIRECTLY_RELEVANT" for row in evidence_trace),
            "defensible_context_count": sum(row["relevance_classification"] == "DEFENSIBLE_CONTEXT" for row in evidence_trace),
            "generic_count": sum(row["relevance_classification"] == "GENERIC_CONTEXT" for row in evidence_trace),
            "suspicious_count": sum(row["relevance_classification"] == "SUSPICIOUS_ASSOCIATION" for row in evidence_trace),
            "false_positive_count": sum(row["relevance_classification"] == "CLEAR_FALSE_POSITIVE" for row in evidence_trace),
            "distinct_useful_claim_count": distinct_useful_claims,
            "duplicate_or_near_duplicate_group_count": len(duplicates),
            "selected_useful_claim_count": len({normalize_claim(row["claim"], row["ckl_title"]) for row in evidence_trace if row["evidence_item_id"] in selected_useful}),
            "useful_unselected_claim_count": len({normalize_claim(row["claim"], row["ckl_title"]) for row in evidence_trace if row["evidence_item_id"] in useful_ids - selected_useful}),
            "selected_useful_path_count": selected_choice_count,
            "useful_path_count": len(useful_path_choices),
            "useful_unselected_path_count": unselected_choice_count,
        },
        "fallback_catalog": {
            "compiled_synthesis_unit_count": len(synthesis.synthesis_units), "fallback_path_count": len(raw_paths),
            "distinct_verse_scopes": [list(scope) for scope in distinct_scopes], "distinct_kinds": distinct_kinds,
            "distinct_source_objects": distinct_source_objects, "distinct_factual_claims": len({normalize_claim(row["claim"], row["ckl_title"]) for row in evidence_trace}),
            "duplicate_groups": duplicates, "suspicious_or_false_positive_count": sum(row["relevance_classification"] in {"SUSPICIOUS_ASSOCIATION", "CLEAR_FALSE_POSITIVE"} for row in evidence_trace),
            "useful_path_ids": useful_path_ids, "renderer_selected_path_ids": selected_path_ids,
            "selected_useful_path_ids": selected_useful_path_ids, "useful_unselected_path_ids": useful_unselected_path_ids,
            "distinct_useful_path_choice_count": len(useful_path_choices), "distinct_selected_useful_path_choice_count": selected_choice_count,
        },
        "renderer_assessment": "GOOD_RESTRAINT" if case_key in {"psalms_019", "numbers_002", "numbers_001"} else "SOURCE_LIMITED",
        "classification": {
            "primary": "CKL_SOURCE_ANCHOR_POLLUTION" if case_key in {"2_kings_004", "psalms_019"} else ("REDUNDANCY_COLLAPSE" if case_key == "psalms_103" else "PASSAGE_COVERAGE_GAP"),
            "secondary": (["EVIDENCE_BUNDLE_OVERINCLUSION", "SYNTHESIS_OVERINCLUSION", "PASSAGE_COVERAGE_GAP"] if case_key == "2_kings_004" else ["EVIDENCE_BUNDLE_OVERINCLUSION", "SYNTHESIS_OVERINCLUSION", "PASSAGE_COVERAGE_GAP", "CANONICAL_TEXT_INTEGRITY"] if case_key == "psalms_019" else ["PASSAGE_COVERAGE_GAP", "EVIDENCE_BUNDLE_OVERINCLUSION", "SYNTHESIS_OVERINCLUSION"] if case_key == "psalms_103" else []),
        },
        "quality_counterfactual": "Using every genuinely useful current-packet path would not plausibly cure under-explanation." if case_key != "psalms_019" else "Both genuinely useful Torah paths are already selected; better coverage requires additional accurate source ancestry, not more selection from this packet.",
    }
    return report


def canonical_integrity() -> dict[str, Any]:
    raw = read_json(CANONICAL_PATH)
    resolved = bible.resolve_chapter("Psalms", 19)
    verse14 = next(v for v in raw["books"] if v["name"] == "Psalms")["chapters"][18]["verses"][13]["text"]
    resolved14 = resolved["verses"][13]["text"]
    prompt_paths = [production_input_path("psalms_019")]
    prompt_path = prompt_paths[0]
    prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path else ""
    return {
        "source_path": str(CANONICAL_PATH.relative_to(ROOT)), "source_sha256": sha256_file(CANONICAL_PATH),
        "resolve_chapter_loader": "bhf_agent.bible.resolve_chapter", "passage_text_stage": "bhf_agent.bible.passage_text joins resolved verse texts without altering verse text",
        "raw_authoritative_psalm_19_verse_14": verse14, "resolved_psalm_19_verse_14": resolved14,
        "contains_adjacent_psalm_20_heading": "Psalm 20 For the Chief Musician. A Psalm of David." in verse14,
        "prompt_path": str(prompt_path.relative_to(ROOT)) if prompt_path else "unavailable", "prompt_sha256": sha256_file(prompt_path) if prompt_path else "unavailable", "prompt_contains_adjacent_heading": "Psalm 20 For the Chief Musician. A Psalm of David." in prompt_text,
        "classification": "source Bible-data contamination",
    }


def git_value(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def run(output_dir: Path | None = None) -> Path:
    lib = current_ckl()
    case_reports = {key: make_case_report(key, lib) for key in CASES}
    identity_payload = {key: {"bundle": value["source_bundle"], "synthesis": value["reproduced_synthesis"]["synthesis_hash"]} for key, value in case_reports.items()}
    identity = sha256_bytes(stable_json({"starting_sha": git_value(["rev-parse", "HEAD"]), "contracts": read_json(PRESENTATION_DIR / "contract-identities.json"), "inputs": identity_payload}).encode())[:24]
    target = output_dir or ROOT / f".bhf-data/bhf-commentary-candidates/commentary-v1.2-upstream-evidence-quality-diagnostic-v1-{identity}"
    target.mkdir(parents=True, exist_ok=True)
    (target / "traces").mkdir(exist_ok=True)
    (target / "chapter-reports").mkdir(exist_ok=True)
    for key, report in case_reports.items():
        (target / "traces" / f"{key}.json").write_text(json.dumps(report["evidence_trace"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (target / "retrieval-path-traces").mkdir(exist_ok=True)
        (target / "retrieval-path-traces" / f"{key}.json").write_text(json.dumps({"retrieval": report["retrieval"], "paths": report["paths"]}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (target / "chapter-reports" / f"{key}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "artifact_version": "commentary-v1.2-upstream-evidence-quality-diagnostic-v1",
        "identity": identity, "branch": git_value(["branch", "--show-current"]), "starting_sha": git_value(["rev-parse", "HEAD"]),
        "repository": "mcscwizzy/biblical-hermeneutics-framework", "model_calls_performed": 0, "production_behavior_changed": False,
        "source_inputs_are_immutable_references": True, "contracts_unchanged": ["Prompt 1.8", "reader-provenance-binding-v2", "reader-provenance-renderer-reference-presentation-v1", "commentary-output-conformance-v1", "GPT-5.6 Sol", "medium effort"],
        "source_trace_method": "exact renderer input identities plus immutable evidence bundles and deterministic synthesis recompilation; current CKL queried read-only for retrieval explanation",
        "files": {"presentation_namespace": str(PRESENTATION_DIR.relative_to(ROOT)), "canonical_data": str(CANONICAL_PATH.relative_to(ROOT)), "bundles": {key: str(value["bundle"].relative_to(ROOT)) for key, value in CASES.items()}},
        "controls": ["numbers_002", "numbers_001"], "failing_cases": ["2_kings_004", "psalms_103", "psalms_019"],
    }
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    contracts = read_json(PRESENTATION_DIR / "contract-identities.json")
    (target / "contract-identities.json").write_text(json.dumps(contracts, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = {"artifact_version": manifest["artifact_version"], "identity": identity, "chapters": case_reports, "canonical_text_integrity": canonical_integrity(), "overall_root_cause_classification": "MIXED: CKL_SOURCE_ANCHOR_POLLUTION plus PASSAGE_COVERAGE_GAP, with EVIDENCE_BUNDLE_OVERINCLUSION and REDUNDANCY_COLLAPSE materially contributing; no renderer underselection was demonstrated.", "prompt_1_8_implicated": False, "binding_v2_implicated": False, "quality_gate_appears_mismatched": True, "smallest_next_remediation_boundary": "Repair/curate source-anchor and legacy-field provenance at the CKL-to-evidence boundary, then re-audit chapter coverage; leave Prompt 1.8, binding, renderer, and Gate unchanged until that audit is complete."}
    (target / "final-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksums = {}
    for path in sorted(target.rglob("*")):
        if path.is_file() and path.name != "checksums.json":
            checksums[str(path.relative_to(target))] = sha256_file(path)
    (target / "checksums.json").write_text(json.dumps(checksums, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    print(run(args.output_dir))


if __name__ == "__main__":
    main()
