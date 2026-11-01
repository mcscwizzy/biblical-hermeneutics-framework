#!/usr/bin/env python3
"""Deterministic, read-only ED-1A CKL evidence depth audit.

The chapter census is delegated to the established Narrative Explorer audit so
eligibility, source hydration, and section assignment use current runtime rules.
This script adds typed-domain counts and source traceability to that census; the
counts are evidence inventory signals, not completeness scores.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from contextlib import nullcontext
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from bhf_agent.db.common import DEFAULT_DB_PATH
from bhf_agent.presentation.narrative_explorer import _child_local_id, _ckl_stable_id
from bhf_agent.presentation.narrative_explorer_curations import CURATED_RELATIONSHIPS
from bhf_agent.presentation.narrative_explorer_passages import (
    load_passage_bridges,
    validate_passage_bridge_registry,
)
from bhf_agent.presentation.references import _BOOK_ALIASES
from bhf_agent.bible import load_asv_bible
from framework.canonical_library import CanonicalLibrary
from framework.canonical_library.scripture import (
    format_scripture_reference,
    parse_scripture_query,
    parse_scripture_references,
    scripture_reference_overlaps,
)

from scripts import audit_narrative_explorer_coverage as nea1


DOMAINS = (
    "historical_cultural",
    "lexical_language",
    "literary_textual",
    "ancient_primary_sources",
    "archaeology_geography",
    "narrative_connections",
    "scholarly_discussion",
)

_HISTORICAL_EVIDENCE_TYPES = {
    "historical-event", "person", "people-group", "institution",
    "cultural-practice", "historical-period", "worldview-concept",
}
_LITERARY_EVIDENCE_TYPES = {"literary-convention"}
_PRIMARY_EVIDENCE_TYPES = {"ancient-text", "manuscript", "primary-source", "inscription"}
_ARCHAEOLOGY_EVIDENCE_TYPES = {
    "artifact", "archaeological-site", "inscription", "material-culture",
    "geography-environment",
}
_HISTORICAL_CLAIM_TYPES = {"historical_cultural"}
_LEXICAL_CLAIM_TYPES = {"lexical"}
_LITERARY_CLAIM_TYPES = {"literary"}
_NARRATIVE_CLAIM_TYPES = {"reception_history"}
_HISTORICAL_NOTE_TYPES = {
    "historical-context", "ancient-near-east-context", "hebraic-worldview",
    "second-temple-context",
}
_LITERARY_NOTE_TYPES = {"literary-observation"}
_NARRATIVE_NOTE_TYPES = {"canonical-connection", "later-reception"}
_UNCERTAINTY_CERTAINTIES = {"disputed", "speculative", "insufficient_evidence"}
_UNCERTAINTY_DISPUTES = {
    "minor_scholarly_disagreement", "major_scholarly_disagreement",
    "denominational_disagreement", "textual_variant", "lexical_uncertainty",
    "historical_uncertainty", "chronological_uncertainty",
    "archaeological_uncertainty", "identification_uncertainty",
    "interpretive_uncertainty", "disputed", "minority", "confessional",
}
_LOCATOR_EXPECTED_SOURCE_TYPES = {
    "ancient-primary-source", "academic-book", "journal-article", "lexicon",
    "grammar", "excavation-report", "museum-collection",
}
_BIBLIOGRAPHIC_DETAIL_FIELDS = ("author", "publisher", "year", "locator", "url")
_SCOPE_RANK = {"book": 1, "multi_chapter": 2, "chapter": 3, "verse": 4}
_RETAINED_JSON_CHAPTER_FIELDS = {"review_statuses_json", "content_statuses_json"}


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        mapped = to_dict()
        return dict(mapped) if isinstance(mapped, Mapping) else {}
    return {}


def _sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return [value]


def _reference_text(value: Any) -> str:
    data = _mapping(value)
    raw = data.get("reference") if data else value
    return str(raw or "").strip()


def projected_ckl_record_id(parent_id: str, record_kind: str, local_id: str | None = None) -> str:
    """Return the exact stable identity used by the Narrative Explorer projector."""

    return _ckl_stable_id(parent_id, record_kind, local_id)


@lru_cache(maxsize=1)
def _canonical_verse_counts() -> dict[str, dict[int, int]]:
    return {
        str(book["name"]): {
            int(chapter["chapter"]): len(chapter.get("verses", []))
            for chapter in book.get("chapters", [])
        }
        for book in load_asv_bible()["books"]
    }


def classify_anchor_scope(
    reference: str,
    chapter_reference: str,
    chapter_verse_counts: Mapping[str, Mapping[int, int]] | None = None,
) -> str:
    """Return the narrowest valid overlapping anchor scope for one chapter."""

    counts = chapter_verse_counts or _canonical_verse_counts()
    query = parse_scripture_query(chapter_reference, book_alias_lookup=_BOOK_ALIASES)
    spans = parse_scripture_references(reference, book_alias_lookup=_BOOK_ALIASES)
    if query is None or not spans:
        return "invalid"
    valid_overlaps: list[str] = []
    saw_invalid_overlap = False
    for span in spans:
        canonical = nea1.scripture_reference_is_canonical(
            format_scripture_reference(span), counts, book_alias_lookup=_BOOK_ALIASES
        )
        if not canonical:
            if span.book.casefold() == query.book.casefold():
                saw_invalid_overlap = True
            continue
        if not scripture_reference_overlaps(query, span):
            continue
        if span.start_chapter is None:
            valid_overlaps.append("book")
        elif span.end_chapter is not None and span.end_chapter != span.start_chapter:
            valid_overlaps.append("multi_chapter")
        elif span.start_verse is None and span.end_verse is None:
            valid_overlaps.append("chapter")
        else:
            valid_overlaps.append("verse")
    if valid_overlaps:
        return max(valid_overlaps, key=lambda value: _SCOPE_RANK[value])
    return "invalid" if saw_invalid_overlap else "not_overlapping"


def record_domain_tags(
    record_kind: str,
    parent_type: str,
    record: Mapping[str, Any],
    source_types: Iterable[str] = (),
) -> tuple[str, ...]:
    """Map explicit CKL type/status fields to audit domains, never prose terms."""

    del parent_type  # Parent scope is tracked separately from typed child evidence.
    if record_kind not in {"claim", "evidence", "interpretive_note"}:
        return ()
    domains: set[str] = set()
    if record_kind == "claim":
        claim_type = str(record.get("claim_type") or "").casefold().replace("-", "_")
        if claim_type in _HISTORICAL_CLAIM_TYPES:
            domains.add("historical_cultural")
        if claim_type in _LEXICAL_CLAIM_TYPES:
            domains.add("lexical_language")
        if claim_type in _LITERARY_CLAIM_TYPES:
            domains.add("literary_textual")
        if claim_type == "archaeology":
            domains.add("archaeology_geography")
        if claim_type in _NARRATIVE_CLAIM_TYPES:
            domains.add("narrative_connections")
    elif record_kind == "evidence":
        evidence_type = str(record.get("evidence_type") or "").casefold().replace("_", "-")
        if evidence_type in _HISTORICAL_EVIDENCE_TYPES:
            domains.add("historical_cultural")
        if evidence_type in _LITERARY_EVIDENCE_TYPES:
            domains.add("literary_textual")
        if evidence_type in _PRIMARY_EVIDENCE_TYPES:
            domains.add("ancient_primary_sources")
        if evidence_type in _ARCHAEOLOGY_EVIDENCE_TYPES:
            domains.add("archaeology_geography")
    else:
        note_type = str(record.get("note_type") or "").casefold().replace("_", "-")
        if note_type in _HISTORICAL_NOTE_TYPES:
            domains.add("historical_cultural")
        if note_type in _LITERARY_NOTE_TYPES:
            domains.add("literary_textual")
        if note_type in _NARRATIVE_NOTE_TYPES:
            domains.add("narrative_connections")

    normalized_source_types = {str(value).casefold() for value in source_types}
    if normalized_source_types & {"ancient-primary-source"}:
        domains.add("ancient_primary_sources")

    certainty = str(record.get("certainty") or "").casefold().replace("-", "_")
    dispute = str(record.get("dispute_status") or "").casefold().replace("-", "_")
    if certainty in _UNCERTAINTY_CERTAINTIES or dispute in _UNCERTAINTY_DISPUTES:
        domains.add("scholarly_discussion")
    return tuple(domain for domain in DOMAINS if domain in domains)


def source_is_traceable(source: Mapping[str, Any]) -> bool:
    """Use the NE-A1 bibliography threshold: title plus one bibliographic field."""

    return bool(
        str(source.get("title") or "").strip()
        and any(str(source.get(field) or "").strip() for field in _BIBLIOGRAPHIC_DETAIL_FIELDS)
    )


def _record_scope(record: Mapping[str, Any], chapter_reference: str) -> tuple[str, str]:
    own_references = [
        _reference_text(value)
        for value in _sequence(record.get("data", {}).get("scripture_references"))
        if _reference_text(value)
    ]
    if own_references:
        scopes = [classify_anchor_scope(value, chapter_reference) for value in own_references]
        matching = [scope for scope in scopes if scope in _SCOPE_RANK]
        if matching:
            return max(matching, key=lambda value: _SCOPE_RANK[value]), "own"
        if "invalid" in scopes:
            return "invalid", "own"
        return "not_overlapping", "own"
    parent_references = [
        _reference_text(value)
        for value in _sequence(record.get("parent_scripture_references"))
        if _reference_text(value)
    ]
    parent_scopes = [classify_anchor_scope(value, chapter_reference) for value in parent_references]
    matching_parent = [scope for scope in parent_scopes if scope in _SCOPE_RANK]
    if matching_parent:
        return max(matching_parent, key=lambda value: _SCOPE_RANK[value]), "inherited"
    if "invalid" in parent_scopes:
        return "invalid", "inherited"
    return "unanchored", "none"


def _record_source_ids(record: Mapping[str, Any]) -> list[str]:
    data = record.get("data", {})
    if record.get("record_kind") == "interpretive_note":
        raw_values = data.get("sources", [])
    else:
        raw_values = data.get("source_ids", [])
    ids = []
    for value in _sequence(raw_values):
        mapped = _mapping(value)
        source_id = str(mapped.get("id") if mapped else value or "").strip()
        if source_id and source_id not in ids:
            ids.append(source_id)
    return ids


def summarize_chapter_records(
    chapter_reference: str,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """Count scoped, sourced typed records while keeping broad context distinct."""

    result: dict[str, int] = {
        "typed_child_record_count": 0,
        "verse_scoped_record_count": 0,
        "chapter_scoped_record_count": 0,
        "broad_context_record_count": 0,
        "inherited_parent_scope_record_count": 0,
        "unanchored_record_count": 0,
        "invalid_anchor_record_count": 0,
        "source_reference_count": 0,
        "resolved_source_reference_count": 0,
        "traceable_source_reference_count": 0,
        "source_traceable_record_count": 0,
        "unresolved_source_reference_count": 0,
    }
    for domain in DOMAINS:
        result[f"{domain}_record_count"] = 0
        result[f"{domain}_source_traceable_count"] = 0

    for item in records:
        if item.get("record_kind") not in {"claim", "evidence", "interpretive_note"}:
            continue
        result["typed_child_record_count"] += 1
        data = _mapping(item.get("data"))
        scope, source_scope = _record_scope({**item, "data": data}, chapter_reference)
        if scope == "verse":
            result["verse_scoped_record_count"] += 1
        elif scope == "chapter":
            result["chapter_scoped_record_count"] += 1
        elif scope in {"book", "multi_chapter"}:
            result["broad_context_record_count"] += 1
        elif scope == "unanchored":
            result["unanchored_record_count"] += 1
        elif scope == "invalid":
            result["invalid_anchor_record_count"] += 1
        if source_scope == "inherited":
            result["inherited_parent_scope_record_count"] += 1

        bibliography = {
            str(_mapping(source).get("id") or ""): _mapping(source)
            for source in item.get("sources", [])
            if _mapping(source).get("id")
        }
        source_ids = _record_source_ids({**item, "data": data})
        traceable = False
        for source_id in source_ids:
            result["source_reference_count"] += 1
            source = bibliography.get(source_id)
            if source is None:
                result["unresolved_source_reference_count"] += 1
                continue
            result["resolved_source_reference_count"] += 1
            if source_is_traceable(source):
                result["traceable_source_reference_count"] += 1
                traceable = True
        result["source_traceable_record_count"] += int(traceable)

        if scope not in _SCOPE_RANK:
            continue
        source_types = [
            str(bibliography[source_id].get("source_type") or "")
            for source_id in source_ids if source_id in bibliography
        ]
        for domain in record_domain_tags(
            str(item.get("record_kind") or ""),
            str(item.get("parent_type") or ""),
            data,
            source_types=source_types,
        ):
            result[f"{domain}_record_count"] += 1
            result[f"{domain}_source_traceable_count"] += int(traceable)
    return result


def _record_index(library: CanonicalLibrary) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for object_id in sorted(library.objects_by_id):
        obj = library.objects_by_id[object_id]
        parent = _mapping(obj)
        bibliography = [_mapping(value) for value in _sequence(parent.get("sources"))]
        parent_references = _sequence(parent.get("scripture_references"))
        records[projected_ckl_record_id(object_id, "object")] = {
            "id": object_id,
            "record_kind": "object",
            "parent_type": str(parent.get("type") or ""),
            "data": parent,
            "sources": bibliography,
            "parent_scripture_references": parent_references,
        }
        for field, kind in (
            ("claims", "claim"),
            ("evidence_items", "evidence"),
            ("interpretive_notes", "interpretive_note"),
        ):
            for raw_value in _sequence(parent.get(field)):
                value = _mapping(raw_value)
                local_id = str(value.get("id") or "")
                if kind == "interpretive_note" and not local_id:
                    local_id = _child_local_id(kind, value)
                if not local_id:
                    continue
                identity = projected_ckl_record_id(object_id, kind, local_id)
                records[identity] = {
                    "id": identity,
                    "record_kind": kind,
                    "parent_type": str(parent.get("type") or ""),
                    "data": value,
                    "sources": bibliography,
                    "parent_scripture_references": parent_references,
                }
    return records


def _read_census(census_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    census_path = census_dir / "chapter-census.csv"
    validation_path = census_dir / "methodology-validation.json"
    if not census_path.is_file() or not validation_path.is_file():
        raise FileNotFoundError(
            "census directory must contain chapter-census.csv and methodology-validation.json"
        )
    with census_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    return rows, validation


def compact_chapter_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Keep deterministic chapter counts while omitting repeated ID inventories."""

    return {
        key: value
        for key, value in row.items()
        if not key.endswith("_json") or key in _RETAINED_JSON_CHAPTER_FIELDS
    }


def _source_inventory(objects: Iterable[Any]) -> dict[str, Any]:
    source_entries: list[dict[str, Any]] = []
    child_source_references: list[tuple[str, str]] = []
    for obj in objects:
        data = _mapping(obj)
        parent_id = str(data.get("id") or "")
        for raw_source in _sequence(data.get("sources")):
            source = _mapping(raw_source)
            if source:
                source_entries.append(source)
        for field, kind in (("claims", "claim"), ("evidence_items", "evidence"), ("interpretive_notes", "interpretive_note")):
            for raw_record in _sequence(data.get(field)):
                record = _mapping(raw_record)
                values = record.get("sources", []) if kind == "interpretive_note" else record.get("source_ids", [])
                for raw_id in _sequence(values):
                    source_data = _mapping(raw_id)
                    source_id = str(source_data.get("id") if source_data else raw_id or "").strip()
                    if source_id:
                        child_source_references.append((parent_id, source_id))

    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in source_entries:
        source_id = str(source.get("id") or "").strip()
        if source_id:
            by_id[source_id].append(source)
    unique_sources = {}
    for source_id, entries in sorted(by_id.items()):
        unique_sources[source_id] = max(
            entries,
            key=lambda source: (
                int(source_is_traceable(source)),
                sum(bool(str(source.get(field) or "").strip()) for field in ("author", "publisher", "year", "locator", "url")),
                str(source.get("title") or ""),
            ),
        )
    source_refs = [(parent_id, source_id) for parent_id, source_id in child_source_references]
    source_ids_by_parent: dict[str, set[str]] = defaultdict(set)
    for obj in objects:
        parent_id = str(_mapping(obj).get("id") or "")
        source_ids_by_parent[parent_id].update(
            str(_mapping(source).get("id") or "")
            for source in _sequence(_mapping(obj).get("sources"))
            if _mapping(source).get("id")
        )
    resolved = [
        (parent_id, source_id)
        for parent_id, source_id in source_refs
        if source_id in source_ids_by_parent.get(parent_id, set())
    ]
    traceable_ids = {source_id for source_id, source in unique_sources.items() if source_is_traceable(source)}
    expected_locator_ids = {
        source_id for source_id, source in unique_sources.items()
        if str(source.get("source_type") or "") in _LOCATOR_EXPECTED_SOURCE_TYPES
    }
    missing_locator_ids = sorted(
        source_id for source_id in expected_locator_ids
        if not str(unique_sources[source_id].get("locator") or "").strip()
    )
    thin_by_type = Counter(
        str(source.get("source_type") or "missing")
        for source in unique_sources.values()
        if not source_is_traceable(source)
    )
    identity_metadata_variation: dict[str, dict[str, list[str]]] = {}
    locator_variation: dict[str, list[str]] = {}
    identity_fields = ("title", "author", "publisher", "year", "source_type", "url")
    for source_id, entries in sorted(by_id.items()):
        differing_identity_fields = {
            field: values
            for field in identity_fields
            if len(values := sorted({str(entry.get(field) or "").strip() for entry in entries if str(entry.get(field) or "").strip()})) > 1
        }
        if differing_identity_fields:
            identity_metadata_variation[source_id] = differing_identity_fields
        differing_locators = sorted({
            str(entry.get("locator") or "").strip()
            for entry in entries
            if str(entry.get("locator") or "").strip()
        })
        if len(differing_locators) > 1:
            locator_variation[source_id] = differing_locators
    return {
        "source_record_occurrence_count": len(source_entries),
        "source_identity_count": len(unique_sources),
        "source_id_missing_count": len(source_entries) - sum(bool(str(source.get("id") or "").strip()) for source in source_entries),
        "source_ids_with_title_and_bibliographic_detail_count": len(traceable_ids),
        "source_ids_missing_title_or_bibliographic_detail_count": len(unique_sources) - len(traceable_ids),
        "source_ids_missing_locator_when_expected_count": len(missing_locator_ids),
        "source_ids_missing_locator_when_expected": missing_locator_ids,
        "source_ids_missing_title_or_bibliographic_detail_by_type": dict(sorted(thin_by_type.items())),
        "child_source_reference_count": len(source_refs),
        "resolved_child_source_reference_count": len(resolved),
        "unresolved_child_source_reference_count": len(source_refs) - len(resolved),
        "distinct_source_ids_by_type": dict(sorted(Counter(
            str(source.get("source_type") or "other") for source in unique_sources.values()
        ).items())),
        "source_ids_with_nonempty_identity_metadata_variation_count": len(identity_metadata_variation),
        "source_identity_metadata_variation": identity_metadata_variation,
        "source_ids_with_locator_variation_count": len(locator_variation),
        "source_locator_variation": locator_variation,
    }


def _lexicon_inventory() -> dict[str, Any]:
    """Count packaged lexicon availability without confusing it with CKL exegesis."""

    asset = REPOSITORY_ROOT / "framework/lexical/database/lexicon.sqlite.gz"
    compressed = asset.read_bytes()
    database_bytes = gzip.decompress(compressed)
    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(database_bytes)
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        entries = dict(connection.execute(
            "SELECT language, COUNT(*) FROM lexical_entries GROUP BY language ORDER BY language"
        ).fetchall())
        verse_words = dict(connection.execute(
            "SELECT language, COUNT(*) FROM verse_words GROUP BY language ORDER BY language"
        ).fetchall())
        chapter_count = int(connection.execute(
            "SELECT COUNT(*) FROM (SELECT DISTINCT book, chapter FROM verse_words)"
        ).fetchone()[0])
        sources = [
            {"source": str(row[0]), "license": str(row[1]), "revision": str(row[2])}
            for row in connection.execute(
                "SELECT source, license, revision FROM lexical_sources ORDER BY source"
            ).fetchall()
        ]
    finally:
        connection.close()
    return {
        "asset": str(asset.relative_to(REPOSITORY_ROOT)),
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
        "sqlite_integrity_check": integrity,
        "entry_count_by_language": entries,
        "verse_word_count_by_language": verse_words,
        "verse_word_row_count": sum(int(value) for value in verse_words.values()),
        "chapters_with_verse_word_rows": chapter_count,
        "source_count": len(sources),
        "sources": sources,
        "interpretation_boundary": "Packaged entries and verse tokens provide general lexical lookup, not passage-specific curated lexical analysis.",
    }


def _bridge_inventory(library: CanonicalLibrary, chapter_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    bridges = load_passage_bridges()
    verified_count = validate_passage_bridge_registry(bridges, library.objects_by_id.get)
    held_path = REPOSITORY_ROOT / "framework/canonical_library/curations/narrative-explorer/ne10/research-candidates-held.json"
    held_document = json.loads(held_path.read_text(encoding="utf-8"))
    held_candidates = held_document.get("candidates", [])
    row_by_ref = {str(row["reference"]): row for row in chapter_rows}
    for bridge in bridges:
        for reference in bridge.get("passages", []):
            spans = parse_scripture_references(reference, book_alias_lookup=_BOOK_ALIASES)
            for span in spans:
                if span.start_chapter is None or span.end_chapter not in (None, span.start_chapter):
                    continue
                chapter_ref = f"{span.book} {span.start_chapter}"
                if chapter_ref in row_by_ref:
                    row_by_ref[chapter_ref]["ne10_verified_bridge_endpoint_count"] = int(
                        row_by_ref[chapter_ref].get("ne10_verified_bridge_endpoint_count", 0)
                    ) + 1
    return {
        "verified_bridge_record_count": verified_count,
        "held_candidate_count": len(held_candidates),
        "bridge_categories": dict(sorted(Counter(str(item.get("relationship_category") or "unknown") for item in bridges).items())),
        "endpoint_projection_count": sum(len(item.get("passages", [])) for item in bridges),
    }


def _enrich_chapters(
    census_rows: Sequence[dict[str, Any]],
    library: CanonicalLibrary,
) -> tuple[list[dict[str, Any]], int]:
    record_index = _record_index(library)
    rows: list[dict[str, Any]] = []
    unmapped_identity_count = 0
    for original in census_rows:
        row = dict(original)
        reference = str(row["reference"])
        item_ids = json.loads(str(row.get("ckl_item_ids_json") or "[]"))
        records = []
        for item_id in item_ids:
            record = record_index.get(str(item_id))
            if record is None:
                unmapped_identity_count += 1
            else:
                records.append(record)
        summary = summarize_chapter_records(reference, records)
        row.update(summary)
        row["ne10_verified_bridge_endpoint_count"] = 0
        row["section_assigned_ckl_item_count"] = max(
            0,
            int(row.get("eligible_ckl_item_count", 0) or 0)
            - int(row.get("unclassified_ckl_item_count", 0) or 0),
        )
        for field in ("ckl_item_ids_json", "ckl_parent_object_ids_json", "unclassified_ckl_item_ids_json"):
            row.pop(field, None)
        rows.append(compact_chapter_row(row))
    return rows, unmapped_identity_count


def _book_summaries(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["book"])].append(row)
    summaries = []
    for book, book_rows in grouped.items():
        summary: dict[str, Any] = {
            "book": book,
            "chapter_count": len(book_rows),
            "coverage_categories": dict(sorted(Counter(str(row["coverage_category"]) for row in book_rows).items())),
            "chapters_with_any_traceable_typed_child": sum(int(row["source_traceable_record_count"]) > 0 for row in book_rows),
            "chapters_with_unclassified_projected_items": sum(int(row.get("unclassified_ckl_item_count", 0) or 0) > 0 for row in book_rows),
            "no_eligible_ckl_chapters": sum(row["coverage_category"] == "no_eligible_ckl_material" for row in book_rows),
        }
        for domain in DOMAINS:
            summary[f"chapters_with_{domain}_records"] = sum(int(row[f"{domain}_record_count"]) > 0 for row in book_rows)
            summary[f"chapters_with_{domain}_traceable_records"] = sum(int(row[f"{domain}_source_traceable_count"]) > 0 for row in book_rows)
        summaries.append(summary)
    return summaries


def _summary(
    library: CanonicalLibrary,
    census_validation: Mapping[str, Any],
    chapter_rows: Sequence[dict[str, Any]],
    unmapped_identity_count: int,
    bridge_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    objects = list(library.objects_by_id.values())
    raw_objects = [_mapping(obj) for obj in objects]
    source_inventory = _source_inventory(objects)
    claim_types = Counter()
    evidence_types = Counter()
    note_types = Counter()
    textual_observation_note_count = 0
    claim_count = evidence_count = note_count = 0
    source_backed_child_count = 0
    authored_object_relationship_count = 0
    authored_evidence_relationship_count = 0
    for parent in raw_objects:
        bibliography = {str(source.get("id") or ""): source for source in _sequence(parent.get("sources")) if _mapping(source).get("id")}
        authored_object_relationship_count += len(_sequence(parent.get("related_objects")))
        for field, kind, counter, type_field in (
            ("claims", "claim", claim_types, "claim_type"),
            ("evidence_items", "evidence", evidence_types, "evidence_type"),
            ("interpretive_notes", "interpretive_note", note_types, "note_type"),
        ):
            records = [_mapping(value) for value in _sequence(parent.get(field))]
            if kind == "evidence":
                authored_evidence_relationship_count += sum(
                    len(_sequence(record.get("related_evidence"))) for record in records
                )
            if kind == "claim":
                claim_count += len(records)
            elif kind == "evidence":
                evidence_count += len(records)
            else:
                note_count += len(records)
            for record in records:
                counter[str(record.get(type_field) or "missing")] += 1
                if kind == "interpretive_note" and str(record.get("note_type") or "").casefold().replace("_", "-") == "textual-observation":
                    textual_observation_note_count += 1
                if any(
                    str(_mapping(source).get("id") if _mapping(source) else source or "") in bibliography
                    and source_is_traceable(bibliography[str(_mapping(source).get("id") if _mapping(source) else source or "")])
                    for source in _sequence(record.get("sources") if kind == "interpretive_note" else record.get("source_ids"))
                ):
                    source_backed_child_count += 1

    coverage_categories = Counter(str(row["coverage_category"]) for row in chapter_rows)
    scope_fields = (
        "typed_child_record_count",
        "verse_scoped_record_count",
        "chapter_scoped_record_count",
        "broad_context_record_count",
        "inherited_parent_scope_record_count",
        "unanchored_record_count",
        "invalid_anchor_record_count",
    )
    scope_placements = {
        field: sum(int(row.get(field, 0) or 0) for row in chapter_rows)
        for field in scope_fields
    }
    domain_summary = {}
    for domain in DOMAINS:
        domain_summary[domain] = {
            "traceable_record_placements": sum(int(row[f"{domain}_source_traceable_count"]) for row in chapter_rows),
            "chapters_with_any_typed_record": sum(int(row[f"{domain}_record_count"]) > 0 for row in chapter_rows),
            "chapters_with_a_traceable_record": sum(int(row[f"{domain}_source_traceable_count"]) > 0 for row in chapter_rows),
        }
    return {
        "audit_version": "ed1a-1",
        "baseline_commit": census_validation.get("baseline_commit"),
        "ckl": {
            "object_count": len(objects),
            "manifest_object_count": int(library.manifest.get("object_count", -1)),
            "inventory_fingerprint": library.inventory_fingerprint(),
            "claim_count": claim_count,
            "claim_types": dict(sorted(claim_types.items())),
            "typed_evidence_item_count": evidence_count,
            "evidence_types": dict(sorted(evidence_types.items())),
            "interpretive_note_count": note_count,
            "interpretive_note_types": dict(sorted(note_types.items())),
            "textual_observation_note_count_unclassified_for_language_domain": textual_observation_note_count,
            "source_backed_child_record_count": source_backed_child_count,
            "authored_relationships": {
                "related_objects_edge_count": authored_object_relationship_count,
                "related_evidence_edge_count": authored_evidence_relationship_count,
            },
            "object_type_counts": dict(sorted(Counter(str(parent.get("type") or "missing") for parent in raw_objects).items())),
        },
        "sources": source_inventory,
        "lexicon": _lexicon_inventory(),
        "chapter_inventory": {
            "book_count": len({str(row["book"]) for row in chapter_rows}),
            "chapter_count": len(chapter_rows),
            "unique_chapter_count": len({(str(row["book"]), int(row["chapter"])) for row in chapter_rows}),
            "coverage_categories": dict(sorted(coverage_categories.items())),
            "unmapped_projected_record_identity_count": unmapped_identity_count,
            "unclassified_projected_record_placements": sum(int(row.get("unclassified_ckl_item_count", 0) or 0) for row in chapter_rows),
            "chapters_with_unclassified_projected_records": sum(int(row.get("unclassified_ckl_item_count", 0) or 0) > 0 for row in chapter_rows),
            "passage_specific_source_backed_child_placements": sum(int(row.get("source_backed_claim_or_evidence_count", 0) or 0) for row in chapter_rows),
            "projected_child_record_scope_placements": scope_placements,
            "by_book": _book_summaries(chapter_rows),
        },
        "evidence_domains": domain_summary,
        "narrative_explorer": {
            "validation_status": census_validation.get("validation_status"),
            "sample_check_count": len(census_validation.get("sample_checks", [])),
            "live_api_sample_count": census_validation.get("live_api_sample_count"),
            "section_item_chapter_placements": census_validation.get("section_ckl_item_chapter_placements", {}),
            "authored_object_relationship_count": census_validation.get("relationships", {}).get("authored_object_relationship_count"),
            "accepted_curation_registry_record_count": len(CURATED_RELATIONSHIPS),
            "accepted_curation_registry_by_kind": dict(sorted(Counter(
                str(entry.get("relationship_kind") or "unknown") for entry in CURATED_RELATIONSHIPS
            ).items())),
            "verified_ne10": dict(bridge_inventory),
            "explicit_external_links": census_validation.get("study_db", {}).get("snapshot_metrics", {}),
        },
        "source_identity_audit": census_validation.get("sources", {}),
        "reproduction": {
            "chapter_source": "Committed ASV chapter inventory checked against bhf_agent.references.BOOKS.",
            "projector_source": "scripts/audit_narrative_explorer_coverage.py (NE-A1) current eligibility, section, and source projection logic.",
            "typed_domain_method": "Only claim_type, evidence_type, interpretive-note type, certainty, dispute_status, and resolved attached source_type fields; prose keywords do not classify records.",
            "language_domain_boundary": "Lexical language counts only claim_type=lexical. Literary counts use literary claims, literary-convention evidence, and literary-observation notes. Generic biblical_text claims and textual-observation notes remain in the inventory but are not presumed to be lexical research or textual criticism.",
            "record_scope_method": "Use each projected child record's own Scripture references. If the child has none, parent references are labeled inherited context and do not count as a child-scoped citation.",
            "bibliography_method": "A traceable source has a title and at least one author, publisher, year, locator, or URL; parent bibliography membership alone does not prove a child record cites the source.",
            "limitations": [
                "Domain counts indicate represented typed records, not scholarly adequacy or a completeness score.",
                "No typed tag means unknown or unclassified until human review; it does not establish irrelevance or absence of evidence.",
                "Dynamic map and archaeology resolver coverage is sampled by NE-A1; full-corpus figures here are explicit stored passage links only.",
            ],
        },
    }


def _write_outputs(output_dir: Path, chapter_rows: Sequence[dict[str, Any]], summary: Mapping[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in chapter_rows for key in row))
    with (output_dir / "chapter-coverage.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(chapter_rows)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )


def run_audit(
    output_dir: Path,
    *,
    census_dir: Path | None = None,
    study_db_path: Path = DEFAULT_DB_PATH,
    repo_root: Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    temp_context = tempfile.TemporaryDirectory(prefix="ed1a-ne-a1-") if census_dir is None else nullcontext(None)
    with temp_context as temporary_path:
        active_census_dir = Path(temporary_path) if temporary_path else Path(census_dir or "")
        if census_dir is None:
            census_validation = nea1.run_audit(active_census_dir, study_db_path, repo_root)
        census_rows, loaded_validation = _read_census(active_census_dir)
        if census_dir is not None:
            census_validation = loaded_validation
        library = CanonicalLibrary.load_default()
        if len(library.objects_by_id) != int(library.manifest.get("object_count", -1)):
            raise ValueError("validated CKL object count disagrees with its manifest")
        if census_validation.get("ckl_inventory_fingerprint") != library.inventory_fingerprint():
            raise ValueError("NE-A1 census CKL fingerprint does not match the current validated CKL")
        expected = int(census_validation.get("chapter_row_count", -1))
        if expected != nea1.EXPECTED_CHAPTERS or len(census_rows) != expected:
            raise ValueError(f"NE-A1 census has {len(census_rows)} rows; expected {nea1.EXPECTED_CHAPTERS}")
        chapter_rows, unmapped_identities = _enrich_chapters(census_rows, library)
        bridge_inventory = _bridge_inventory(library, chapter_rows)
        summary = _summary(library, census_validation, chapter_rows, unmapped_identities, bridge_inventory)
        _write_outputs(output_dir, chapter_rows, summary)
        return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/evidence-depth/ed1a"))
    parser.add_argument("--census-dir", type=Path, help="Reuse a completed NE-A1 census directory")
    parser.add_argument("--study-db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--repo-root", type=Path, default=REPOSITORY_ROOT)
    args = parser.parse_args(argv)
    summary = run_audit(
        args.output_dir,
        census_dir=args.census_dir,
        study_db_path=args.study_db,
        repo_root=args.repo_root,
    )
    print(json.dumps({
        "audit_version": summary["audit_version"],
        "baseline_commit": summary["baseline_commit"],
        "ckl_objects": summary["ckl"]["object_count"],
        "chapter_rows": summary["chapter_inventory"]["chapter_count"],
        "validation_status": summary["narrative_explorer"]["validation_status"],
        "unmapped_record_identities": summary["chapter_inventory"]["unmapped_projected_record_identity_count"],
    }, sort_keys=True))
    return 0 if summary["chapter_inventory"]["chapter_count"] == nea1.EXPECTED_CHAPTERS else 1


if __name__ == "__main__":
    raise SystemExit(main())
