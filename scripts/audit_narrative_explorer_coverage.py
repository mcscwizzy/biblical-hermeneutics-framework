#!/usr/bin/env python3
"""Reproducible, read-only CKL coverage audit for Narrative Explorer NE-5B.

The census indexes the validated CKL inventory once, then runs the existing
passage projector over each chapter's in-memory candidate set. The study DB is
opened with SQLite ``mode=ro`` for explicit passage-link inventories. A small,
deterministic sample is additionally checked through the normal NE service.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import resource
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# Running ``python scripts/...py`` places only the scripts directory on
# sys.path; keep the checked-out repository packages importable in that mode.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent.bible import load_asv_bible, normalize_book_name
from bhf_agent.db.common import DEFAULT_DB_PATH
from bhf_agent.presentation.narrative_explorer import (
    DomainLookup,
    _CONNECTION_TYPE_BY_LABEL,
    _child_local_id,
    _normalized_label,
    project_narrative_explorer,
)
from bhf_agent.presentation.references import _BOOK_ALIASES, anchor_specificity
from bhf_agent.presentation.relevance import (
    SEMANTICALLY_MISANCHORED,
    classify_semantic_relationship,
)
from bhf_web.services.narrative_explorer import NarrativeExplorerService
from framework.canonical_library import CanonicalLibrary, evidence_graph_edges
from framework.canonical_library.scripture import (
    parse_scripture_references,
    parse_scripture_query,
    scripture_reference_overlaps,
)
from bhf_agent.references import BOOKS


AUDIT_VERSION = "ne-a1-1"
SAMPLE_SEED = 20261015
EXPECTED_CHAPTERS = 1189
NE_ANCESTRY = {
    "NE-1": "a924d9ee68bf20d1076d3113ee86f90524d31562",
    "NE-2": "b2182561fcc518d49601fdcd965f877270373b57",
    "NE-3": "5a986e88bff9b79e0efea95583965d7045506487",
    "NE-4": "8c1ae5643ebe679633cb7b5cb7616b3c13bf4279",
    "NE-5A": "bf1c4772f03f4aa12aef2a0faa5a5aaa1e54b005",
    "NE-5B": "8e6283a68c020691161278504127e566f63c41a4",
}
PILOT_REFERENCES = (
    "Genesis 1",
    "Genesis 2",
    "Genesis 3",
    "Genesis 6",
    "Deuteronomy 32",
    "Psalms 82",
    "Exodus 3",
)
PILOT_REQUEST_LABELS = (
    "Genesis 1", "Genesis 2", "Genesis 3", "Genesis 6", "Deuteronomy 32", "Psalm 82", "Exodus 3",
)
SECTION_IDS = (
    "biblical_narrative",
    "archaeology_ancient_history",
    "biblical_geography",
    "divine_council_cosmic_geography",
    "themes_biblical_connections",
    "people_events_relationships",
)
SECTION_COLUMNS = {
    "biblical_narrative": "biblical_narrative_ckl_item_count",
    "archaeology_ancient_history": "archaeology_ancient_history_ckl_item_count",
    "biblical_geography": "biblical_geography_ckl_item_count",
    "divine_council_cosmic_geography": "cosmic_geography_ckl_item_count",
    "themes_biblical_connections": "themes_biblical_connections_ckl_item_count",
    "people_events_relationships": "people_events_relationships_ckl_item_count",
}
ENTITY_OBJECT_TYPES = {"person", "people_group", "group", "place", "event"}
ARCHAEOLOGY_EVIDENCE_TYPES = {
    "artifact", "archaeological-site", "inscription", "material-culture",
}
ANCIENT_TEXT_EVIDENCE_TYPES = {"ancient-text", "manuscript", "primary-source"}
DIRECT_RELATIONSHIPS = {
    "direct", "primary", "quotation", "direct-quotation", "explicit-textual-reference",
}
COMPARATIVE_RELATIONSHIPS = {"comparative", "contrast", "background", "contextual"}

# This is an explicit, reviewable topic seed list. Records are admitted only by
# stable authored CKL identity and their own passage anchors/relationships.
TOPIC_OBJECTS: dict[str, tuple[str, ...]] = {
    "Creation and new creation": (
        "creation", "creation-theme", "new-creation-theme", "creation-doctrine-framework",
        "new-jerusalem-theme", "new-temple-theme",
    ),
    "Eden and sacred space": ("genesis",),
    "Divine presence": (
        "presence-theme", "divine-presence", "tabernacle-presence-access-and-mobility",
        "tabernacle", "temple",
    ),
    "Divine council and heavenly assembly": (
        "ancient-divine-assembly-imagery", "genesis-flood-postflood-context",
    ),
    "Nations and territorial imagery": (
        "genesis-nations-babel-context", "judgment-against-the-nations", "land-theme",
        "joshua", "acts",
    ),
    "Cosmic mountain and holy ground": ("genesis", "mountain-theme", "sinai-covenant"),
    "Temple and tabernacle": (
        "tabernacle", "temple", "temple-theme", "new-temple-theme",
        "dedication-of-solomons-temple", "rebuilding-the-temple",
        "ancient-portable-sanctuaries-and-tabernacle-comparisons",
    ),
    "Covenant": (
        "abrahamic-covenant-framework", "covenant-theme", "new-covenant-theme",
        "abrahamic-covenant", "sinai-covenant", "davidic-covenant",
        "covenant-renewal-at-shechem", "new-covenant-prophecy",
    ),
    "Exile and restoration": (
        "exile-and-return-storyline", "exile-theme", "restoration-theme",
        "assyrian-exile-of-israel", "babylonian-exile", "return-from-exile",
        "restoration-prophecy", "persian-restoration-and-yehud-administration",
    ),
    "Flood and ancient Near Eastern comparisons": (
        "the-flood", "genesis-flood-postflood-context", "mesopotamian-creation-and-flood-comparisons",
    ),
    "Kingship and kingdom": (
        "kingship", "kingdom-theme", "kingdom-theology", "theology-of-the-kingdom",
        "egyptian-kingship-and-divine-order", "division-of-the-kingdom",
    ),
    "Judgment, chaos, and renewal": (
        "judgment", "final-judgment", "great-white-throne-judgment",
        "judgment-against-the-nations", "new-creation-theme", "restoration-theme",
    ),
}
TOPIC_CHILD_ALLOWLIST: dict[str, dict[str, tuple[str, ...]]] = {
    "Eden and sacred space": {
        "genesis": ("g2-garden-planting-presence", "g2-rivers-and-eden-geographic-limits", "g3-cherubim-biblical-sacred-space-context"),
    },
    "Divine council and heavenly assembly": {
        "genesis-flood-postflood-context": (
            "g6-sons-of-god-interpretive-positions", "g6-second-temple-watchers-reception",
        ),
        "ancient-divine-assembly-imagery": (
            "psalm-82-assembly-text", "ugaritic-divine-assembly-comparison",
            "psalm-82-assembly-language", "ugaritic-council-comparison",
        ),
    },
    "Cosmic mountain and holy ground": {
        "genesis": ("g2-garden-planting-presence", "g3-cherubim-biblical-sacred-space-context"),
    },
    "Nations and territorial imagery": {
        "joshua": ("joshua-fulfilled-and-remaining-land",),
        "acts": ("acts-geographic-program", "acts-cornelius", "acts-decree"),
    },
}


def coverage_category(
    items: Sequence[Any],
    *,
    lookup_status: str,
) -> str:
    """Describe CKL chapter coverage without ranking theological importance."""

    if lookup_status != "complete":
        return "incomplete_or_unknown"
    if not items:
        return "no_eligible_ckl_material"
    if any(
        getattr(item, "record_kind", "") in {"claim", "evidence"}
        and any(_source_is_traceable(source) for source in getattr(item, "sources", ()))
        for item in items
    ):
        return "passage_specific_evidence"
    if all(
        getattr(item, "record_kind", "") == "object"
        and str(getattr(item, "object_type", "") or "").casefold().replace("-", "_")
        in ENTITY_OBJECT_TYPES
        for item in items
    ):
        return "entity_only_coverage"
    return "contextual_coverage"


def _source_is_traceable(source: Any) -> bool:
    if not getattr(source, "details_available", False):
        return False
    details = _as_mapping(getattr(source, "bibliographic_details", None))
    title = str(details.get("title") or "").strip()
    useful_detail = any(
        str(details.get(key) or "").strip()
        for key in ("author", "publisher", "year", "locator", "url")
    )
    return bool(title and useful_detail)


def select_stratified_sample(
    chapters: Sequence[Mapping[str, Any]],
    *,
    seed: int = SAMPLE_SEED,
    per_stratum: int = 1,
) -> list[dict[str, Any]]:
    """Select a stable sample with at least one chapter from each stratum."""

    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for chapter in chapters:
        groups[str(chapter.get("stratum") or "Unclassified")].append(chapter)
    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    for stratum in sorted(groups):
        values = sorted(
            groups[stratum],
            key=lambda row: (int(row.get("canonical_order", 0)), str(row.get("reference", ""))),
        )
        selected.extend(dict(row) for row in rng.sample(values, min(max(1, per_stratum), len(values))))
    return selected


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        mapped = value.to_dict()
        return dict(mapped) if isinstance(mapped, Mapping) else {}
    if is_dataclass(value):
        return asdict(value)
    return {}


def _sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return [value]


def _record_refs(value: Any) -> list[str]:
    refs: list[str] = []
    for raw in _sequence(value):
        data = _as_mapping(raw)
        raw_reference = data.get("reference") if data else raw
        if isinstance(raw_reference, str) and raw_reference.strip():
            refs.append(raw_reference.strip())
    return refs


def scripture_reference_is_canonical(
    reference: str,
    chapter_verse_counts: Mapping[str, Mapping[int, int]],
    book_alias_lookup: Mapping[str, str] = _BOOK_ALIASES,
) -> bool:
    """Check parsed Scripture spans against the canonical book/chapter/verse inventory."""

    spans = parse_scripture_references(reference, book_alias_lookup=book_alias_lookup)
    if not spans:
        return False
    for span in spans:
        book_counts = chapter_verse_counts.get(span.book)
        if book_counts is None:
            return False
        if span.start_chapter is None:
            if span.start_verse is not None or span.end_chapter is not None or span.end_verse is not None:
                return False
            continue
        start_chapter = span.start_chapter
        end_chapter = span.end_chapter or start_chapter
        if start_chapter not in book_counts or end_chapter not in book_counts or end_chapter < start_chapter:
            return False
        if span.start_verse is not None and span.start_verse < 1:
            return False
        if span.end_verse is not None and span.end_verse < 1:
            return False
        if span.start_verse is not None and span.start_verse > book_counts[start_chapter]:
            return False
        if span.end_verse is not None and span.end_verse > book_counts[end_chapter]:
            return False
    return True


def _stratum(book: str) -> str:
    if book in {"Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"}:
        return "Pentateuch"
    if book in {"Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther"}:
        return "Historical books"
    if book in {"Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Songs"}:
        return "Poetry and wisdom"
    if book in {"Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel"}:
        return "Major prophets"
    if book in {"Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi"}:
        return "Minor prophets"
    if book in {"Matthew", "Mark", "Luke", "John"}:
        return "Gospels"
    if book == "Acts":
        return "Acts"
    if book == "Revelation":
        return "Revelation"
    return "Epistles"


def load_chapters(bible: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Use the committed ASV chapter inventory and BHF's canonical book table."""

    bible = bible or load_asv_bible()
    chapters: list[dict[str, Any]] = []
    order = 0
    names = [str(book.get("name") or "") for book in bible["books"]]
    if len(names) != 66 or set(names) != set(BOOKS):
        raise ValueError("ASV and BHF canonical book inventories do not match 66 books")
    for book in bible["books"]:
        name = str(book["name"])
        testament, genre, _aliases = BOOKS[name]
        for chapter in book.get("chapters", []):
            number = int(chapter["chapter"])
            order += 1
            chapters.append({
                "canonical_order": order,
                "book": name,
                "chapter": number,
                "reference": f"{name} {number}",
                "testament": testament,
                "bible_genre": genre,
                "stratum": _stratum(name),
                "verse_count": len(chapter.get("verses", [])),
            })
    if len(chapters) != EXPECTED_CHAPTERS:
        raise ValueError(f"canonical chapter inventory has {len(chapters)} rows, expected {EXPECTED_CHAPTERS}")
    identities = [(row["book"], row["chapter"]) for row in chapters]
    if len(set(identities)) != len(identities):
        raise ValueError("canonical chapter inventory contains duplicate identities")
    return chapters


def build_candidate_index(
    library: CanonicalLibrary,
    chapters: Sequence[Mapping[str, Any]],
) -> dict[str, list[str]]:
    """Batch exact candidate IDs using the loader's normalized Scripture index."""

    index: dict[str, list[str]] = {}
    for chapter in chapters:
        reference = str(chapter["reference"])
        query = parse_scripture_query(reference, book_alias_lookup=library._book_alias_lookup)
        if query is None:
            raise ValueError(f"cannot parse canonical chapter {reference}")
        candidate_ids = []
        for object_id in sorted(library._scripture_book_index.get(query.book, set())):
            obj = library.objects_by_id[object_id]
            if not library._is_retrievable(obj, include_placeholders=True):
                continue
            if any(
                scripture_reference_overlaps(query, candidate)
                for candidate in library._scripture_references_by_object.get(object_id, ())
            ):
                candidate_ids.append(object_id)
        index[reference] = candidate_ids
    return index


def chapters_for_reference(reference: str, chapter_counts: Mapping[str, int]) -> list[int]:
    """Expand an authored reference to chapter identities without verse fuzz."""

    result: set[int] = set()
    for span in parse_scripture_references(reference, book_alias_lookup=_BOOK_ALIASES):
        total = chapter_counts.get(span.book)
        if total is None:
            continue
        start = 1 if span.start_chapter is None else span.start_chapter
        end = span.end_chapter or span.start_chapter or total
        if start < 1 or end < start:
            continue
        result.update(range(start, min(end, total) + 1))
    return sorted(result)


def _authored_anchor_records(obj: Any) -> Iterable[tuple[str, str, str, str]]:
    """Yield (kind, id, reference, relationship) without serializing the parent."""

    for anchor in _sequence(getattr(obj, "scripture_references", ())):
        data = anchor if isinstance(anchor, Mapping) else None
        reference_value = (data or {}).get("reference") if data is not None else getattr(anchor, "reference", anchor if isinstance(anchor, str) else "")
        reference = str(reference_value or "").strip()
        if reference:
            relationship_value = (data or {}).get("relationship") if data is not None else getattr(anchor, "relationship", "contextual")
            yield "object", "", reference, str(relationship_value or "contextual")
    for child, kind in (
        *((child, "claim") for child in _sequence(getattr(obj, "claims", ()))),
        *((child, "evidence") for child in _sequence(getattr(obj, "evidence_items", ()))),
        *((child, "interpretive_note") for child in _sequence(getattr(obj, "interpretive_notes", ()))),
    ):
        child_data = child if isinstance(child, Mapping) else None
        local_id = str((child_data or {}).get("id") if child_data is not None else getattr(child, "id", "") or "")
        if kind == "interpretive_note" and not local_id:
            local_id = _child_local_id(kind, _as_mapping(child))
        raw_references = (child_data or {}).get("scripture_references") if child_data is not None else getattr(child, "scripture_references", ())
        for reference_value in _sequence(raw_references):
            anchor = reference_value if isinstance(reference_value, Mapping) else None
            reference_value_text = (anchor or {}).get("reference") if anchor is not None else getattr(reference_value, "reference", reference_value if isinstance(reference_value, str) else "")
            reference = str(reference_value_text or "").strip()
            if reference:
                relationship_value = (anchor or {}).get("relationship") if anchor is not None else getattr(reference_value, "relationship", "contextual")
                yield kind, local_id, reference, str(relationship_value or "contextual")


def build_anchor_audit_index(
    library: CanonicalLibrary,
    chapters: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Parse each authored anchor once and index its exact chapter scope."""

    counts = {
        str(chapter["reference"]): {
            "matching_authored_anchor_count": 0,
            "semantically_misanchored_anchor_count": 0,
            "book_level_anchor_keys": set(),
            "multi_chapter_anchor_keys": set(),
        }
        for chapter in chapters
    }
    chapter_counts: dict[str, int] = {}
    for chapter in chapters:
        chapter_counts[str(chapter["book"])] = max(
            chapter_counts.get(str(chapter["book"]), 0), int(chapter["chapter"])
        )
    chapter_refs_by_book: dict[str, list[str]] = defaultdict(list)
    for chapter in chapters:
        chapter_refs_by_book[str(chapter["book"])].append(str(chapter["reference"]))

    for object_number, obj in enumerate(library.objects_by_id.values(), start=1):
        if object_number % 100 == 0:
            print(f"[ne-a1] anchor audit scanned {object_number}/{len(library.objects_by_id)} CKL objects", file=sys.stderr, flush=True)
        if not library._is_retrievable(obj, include_placeholders=True):
            continue
        parent_type = str(obj.type or "")
        parent_title = str(obj.title or "")
        for kind, local_id, raw_reference, relationship in _authored_anchor_records(obj):
            spans = parse_scripture_references(raw_reference, book_alias_lookup=library._book_alias_lookup)
            if not spans:
                continue
            touched: set[str] = set()
            narrow_touched: set[str] = set()
            for span in spans:
                if span.book not in chapter_refs_by_book:
                    continue
                if span.start_chapter is None:
                    touched.update(chapter_refs_by_book[span.book])
                    for passage_ref in chapter_refs_by_book[span.book]:
                        counts[passage_ref]["book_level_anchor_keys"].add((obj.id, kind, local_id, raw_reference))
                else:
                    start = span.start_chapter
                    end = span.end_chapter or start
                    if end < start:
                        continue
                    for number in range(start, min(end, chapter_counts[span.book]) + 1):
                        chapter_ref = f"{span.book} {number}"
                        touched.add(chapter_ref)
                        narrow_touched.add(chapter_ref)
                        if end > start:
                            counts[chapter_ref]["multi_chapter_anchor_keys"].add((obj.id, kind, local_id, raw_reference))
            for passage_ref in touched:
                entry = counts.get(passage_ref)
                if entry is None:
                    continue
                entry["matching_authored_anchor_count"] += 1
                if passage_ref not in narrow_touched:
                    continue
                semantic = classify_semantic_relationship(
                    passage_ref,
                    anchors=[raw_reference],
                    metadata={
                        "parent_object_id": obj.id,
                        "parent_type": parent_type,
                        "parent_title": parent_title,
                        "source_kind": {
                            "object": "ckl_legacy_field",
                            "claim": "ckl_claim",
                            "evidence": "ckl_evidence_item",
                            "interpretive_note": "ckl_interpretive_note",
                        }[kind],
                        "passage_relationship": relationship or "contextual",
                    },
                )
                if semantic == SEMANTICALLY_MISANCHORED:
                    entry["semantically_misanchored_anchor_count"] += 1

    result: dict[str, dict[str, Any]] = {}
    for reference, entry in counts.items():
        result[reference] = {
            "matching_authored_anchor_count": int(entry["matching_authored_anchor_count"]),
            "semantically_misanchored_anchor_count": int(entry["semantically_misanchored_anchor_count"]),
            "book_level_anchor_keys": entry["book_level_anchor_keys"],
            "multi_chapter_anchor_keys": entry["multi_chapter_anchor_keys"],
        }
    return result


def _all_object_refs(obj: Any) -> list[tuple[str, str, str]]:
    """Return (record kind, local id, raw reference) for authored anchors."""

    return [
        (kind, local_id, reference)
        for kind, local_id, reference, _relationship in _authored_anchor_records(obj)
    ]


def _chapter_verse_counts(chapters: Sequence[Mapping[str, Any]]) -> dict[str, dict[int, int]]:
    counts: dict[str, dict[int, int]] = defaultdict(dict)
    for chapter in chapters:
        counts[str(chapter["book"])][int(chapter["chapter"])] = int(chapter["verse_count"])
    return dict(counts)


def _invalid_anchor_details(
    library: CanonicalLibrary,
    chapters: Sequence[Mapping[str, Any]],
    chapter_verse_counts: Mapping[str, Mapping[int, int]],
) -> tuple[dict[str, int], list[dict[str, str]]]:
    chapter_counts: Counter[str] = Counter()
    invalid: list[dict[str, str]] = []
    aliases = sorted(library._book_alias_lookup, key=lambda item: (-len(item), item))
    for obj in library.objects_by_id.values():
        for kind, local_id, reference in _all_object_refs(obj):
            parsed = parse_scripture_references(reference, book_alias_lookup=library._book_alias_lookup)
            if parsed and scripture_reference_is_canonical(reference, chapter_verse_counts, library._book_alias_lookup):
                continue
            invalid.append({
                "object_id": obj.id,
                "record_kind": kind,
                "local_id": local_id,
                "reference": reference,
                "failure_kind": "out_of_canonical_bounds" if parsed else "unparseable_reference",
            })
            normalized = " ".join(reference.casefold().split())
            matched_books = {span.book for span in parsed}
            if not matched_books:
                matched_book = next((library._book_alias_lookup[alias] for alias in aliases if normalized == alias or normalized.startswith(alias + " ")), None)
                if matched_book:
                    matched_books.add(matched_book)
            for chapter in chapters:
                if chapter["book"] in matched_books:
                    chapter_counts[str(chapter["reference"])] += 1
    return dict(chapter_counts), invalid


def _item_source_metrics(items: Sequence[Any]) -> dict[str, Any]:
    source_ids: list[str] = []
    source_details_by_id: dict[str, bool] = {}
    source_bibliography_by_id: dict[str, bool] = {}
    source_details = 0
    source_bibliography = 0
    child_with_sources = 0
    child_without_sources = 0
    source_grounded_children = 0
    for item in items:
        ids = list(getattr(item, "source_ids", ()) or ())
        if ids:
            child_with_sources += int(getattr(item, "record_kind", "") in {"claim", "evidence", "interpretive_note"})
        elif getattr(item, "record_kind", "") in {"claim", "evidence", "interpretive_note"}:
            child_without_sources += 1
        available_for_item = False
        for source in getattr(item, "sources", ()):
            source_id = str(getattr(source, "id", ""))
            source_ids.append(source_id)
            has_details = bool(getattr(source, "details_available", False))
            source_details_by_id[source_id] = source_details_by_id.get(source_id, False) or has_details
            if has_details:
                source_details += 1
            details = _as_mapping(getattr(source, "bibliographic_details", None))
            title = str(details.get("title") or "").strip()
            useful_detail = any(str(details.get(key) or "").strip() for key in ("author", "publisher", "year", "locator", "url"))
            source_bibliography += int(bool(title and useful_detail))
            source_bibliography_by_id[source_id] = source_bibliography_by_id.get(source_id, False) or bool(title and useful_detail)
            available_for_item = available_for_item or bool(has_details and title and useful_detail)
        source_grounded_children += int(
            getattr(item, "record_kind", "") in {"claim", "evidence"} and available_for_item
        )
    unique_sources = sorted(set(value for value in source_ids if value))
    return {
        "source_reference_count": len(source_ids),
        "source_id_count": len(unique_sources),
        "source_details_available_count": source_details,
        "source_details_available_id_count": sum(source_details_by_id.values()),
        "source_bibliography_resolvable_count": source_bibliography,
        "source_bibliography_resolvable_id_count": sum(source_bibliography_by_id.values()),
        "source_bibliography_incomplete_id_count": sum(
            bool(source_id) and not source_bibliography_by_id.get(source_id, False)
            for source_id in set(source_ids)
        ),
        "unresolved_source_reference_count": max(0, len(source_ids) - source_details),
        "source_backed_claim_or_evidence_count": source_grounded_children,
        "child_records_with_source_ids": child_with_sources,
        "child_records_without_source_ids": child_without_sources,
        "source_ids_json": json.dumps(unique_sources, separators=(",", ":")),
    }


def _status_counts(items: Sequence[Any]) -> dict[str, Any]:
    review = Counter(str(getattr(item, "review_status", "") or "missing") for item in items)
    content = Counter(str(getattr(item, "content_status", "") or "missing") for item in items)
    certainty = Counter(str(getattr(item, "certainty", "") or "missing") for item in items)
    disputes = Counter(str(getattr(item, "dispute_status", "") or "missing") for item in items)
    return {
        "missing_review_metadata_count": review.get("missing", 0),
        "reviewed_or_approved_item_count": sum(review.get(status, 0) for status in ("reviewed", "approved")),
        "content_status_missing_count": content.get("missing", 0),
        "human_review_required_count": sum(bool(getattr(item, "human_review_required", False)) for item in items),
        "certainty_missing_count": certainty.get("missing", 0),
        "dispute_metadata_missing_count": disputes.get("missing", 0),
        "explicitly_disputed_item_count": sum(
            str(getattr(item, "interpretation_state", "unknown")).casefold() == "disputed"
            or str(getattr(item, "dispute_status", "unknown")).casefold().replace("-", "_") in {"disputed", "contested"}
            for item in items
        ),
        "explicitly_uncertain_item_count": sum(
            str(getattr(item, "interpretation_state", "unknown")).casefold()
            in {"plausible", "speculative", "insufficient_evidence"}
            for item in items
        ),
        "interpretation_state_unknown_or_unestablished_count": sum(
            str(getattr(item, "interpretation_state", "unknown")).casefold() in {"unknown", "not_established"}
            for item in items
        ),
        "disputed_or_uncertain_item_count": sum(
            str(getattr(item, "interpretation_state", "unknown")).casefold()
            in {"disputed", "plausible", "speculative", "insufficient_evidence"}
            or str(getattr(item, "dispute_status", "unknown")).casefold().replace("-", "_") in {"disputed", "contested"}
            for item in items
        ),
        "review_statuses_json": json.dumps(dict(sorted(review.items())), separators=(",", ":")),
        "content_statuses_json": json.dumps(dict(sorted(content.items())), separators=(",", ":")),
    }


def _relationship_metrics(connections: Sequence[Any]) -> dict[str, Any]:
    typed = Counter(str(getattr(edge, "connection_type", "uncategorized")) for edge in connections)
    return {
        "projected_connection_count": len(connections),
        "direct_connection_count": sum(getattr(edge, "relationship_mode", "") == "direct" for edge in connections),
        "inferred_connection_count": sum(getattr(edge, "relationship_mode", "") == "inferred" for edge in connections),
        "uncategorized_connection_count": typed.get("uncategorized", 0),
        "reciprocal_connection_count": sum(getattr(edge, "direction", "") == "reciprocal" for edge in connections),
        "one_way_connection_count": sum(getattr(edge, "direction", "") == "one_way" for edge in connections),
        "connection_types_json": json.dumps(dict(sorted(typed.items())), separators=(",", ":")),
    }


def _matching_anchor_counts(
    anchor_audit: Mapping[str, Any],
    items: Sequence[Any],
) -> dict[str, int]:
    projected_anchor_keys: set[tuple[str, str, str, str]] = set()
    for item in items:
        for anchor in item.applicable_passage_anchors:
            projected_anchor_keys.add((
                str(item.object_id or ""), str(item.record_kind), str(item.local_id or ""),
                str(anchor.get("reference") or ""),
            ))
    book_level_keys = set(anchor_audit.get("book_level_anchor_keys", set()))
    multi_chapter_keys = set(anchor_audit.get("multi_chapter_anchor_keys", set()))
    book_level_excluded = book_level_keys - projected_anchor_keys
    multi_chapter_excluded = multi_chapter_keys - projected_anchor_keys
    book_level_excluded_records = {(object_id, kind, local_id) for object_id, kind, local_id, _ref in book_level_excluded}
    multi_chapter_excluded_records = {(object_id, kind, local_id) for object_id, kind, local_id, _ref in multi_chapter_excluded}
    multi_chapter_projected_records = {
        (object_id, kind, local_id)
        for object_id, kind, local_id, reference in multi_chapter_keys & projected_anchor_keys
    }
    return {
        "matching_authored_anchor_count": int(anchor_audit.get("matching_authored_anchor_count", 0)),
        "semantically_misanchored_anchor_count": int(anchor_audit.get("semantically_misanchored_anchor_count", 0)),
        "book_level_anchor_reference_count": len(book_level_keys),
        "multi_chapter_anchor_reference_count": len(multi_chapter_keys),
        "book_level_anchor_reference_excluded_count": len(book_level_excluded),
        "multi_chapter_anchor_reference_excluded_count": len(multi_chapter_excluded),
        "broad_parent_records_excluded_count": len({key for key in book_level_excluded_records | multi_chapter_excluded_records if key[1] == "object"}),
        "broad_anchor_records_excluded_count": len(book_level_excluded_records | multi_chapter_excluded_records),
        "multi_chapter_parent_records_projected_count": sum(kind == "object" for _object_id, kind, _local_id in multi_chapter_projected_records),
    }


def _context_counts(items: Sequence[Any], candidates: Sequence[Any]) -> dict[str, int]:
    parent_ids = {str(item.object_id or item.id) for item in items if item.record_kind == "object"}
    child_parent_ids = {str(item.parent_object_id) for item in items if item.record_kind != "object"}
    broad_context = 0
    for obj in candidates:
        if obj.id not in parent_ids or obj.id in child_parent_ids:
            continue
        if str(obj.type or "").casefold().replace("-", "_") in ENTITY_OBJECT_TYPES:
            continue
        if any(str(value or "").strip() for value in (obj.summary, obj.historical_context, obj.ancient_near_east_context, obj.literary_context)):
            broad_context += 1
    return {
        "broad_context_only_parent_count": broad_context,
        "eligible_entity_parent_count": sum(
            item.record_kind == "object"
            and str(item.object_type or "").casefold().replace("-", "_") in ENTITY_OBJECT_TYPES
            for item in items
        ),
    }


def _chapter_census_row(
    chapter: Mapping[str, Any],
    candidate_ids: Sequence[str],
    anchor_audit: Mapping[str, Any],
    library: CanonicalLibrary,
    *,
    unresolved_anchor_count: int = 0,
    external_links: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], Any]:
    candidates = [library.objects_by_id[object_id] for object_id in candidate_ids]
    lookup_status = "partial" if unresolved_anchor_count else "complete"
    projection = project_narrative_explorer(
        str(chapter["reference"]),
        canonical_lookup=DomainLookup(domain="ckl", records=candidates, query_status=lookup_status),
    )
    items = [item for item in projection.items if item.domain == "ckl"]
    connections = [
        edge for edge in projection.connections
        if edge.basis.get("kind", "").startswith("ckl_")
    ]
    source_metrics = _item_source_metrics(items)
    row: dict[str, Any] = dict(chapter)
    row.update({
        "ckl_lookup_status": lookup_status,
        "raw_candidate_parent_count": len(candidate_ids),
        "eligible_parent_object_count": sum(item.record_kind == "object" for item in items),
        "passage_anchored_claim_count": sum(item.record_kind == "claim" for item in items),
        "passage_anchored_evidence_item_count": sum(item.record_kind == "evidence" for item in items),
        "passage_specific_interpretive_note_count": sum(item.record_kind == "interpretive_note" for item in items),
        "eligible_ckl_item_count": len(items),
        "unclassified_ckl_item_count": sum(not item.section_ids for item in items),
        "unclassified_ckl_item_ids_json": json.dumps(sorted(item.id for item in items if not item.section_ids), separators=(",", ":")),
        "verse_scoped_eligible_item_count": sum(
            any(anchor_specificity(str(anchor.get("reference") or "")) == "verse" for anchor in item.applicable_passage_anchors)
            for item in items
        ),
        "chapter_scoped_eligible_item_count": sum(
            any(anchor_specificity(str(anchor.get("reference") or "")) == "chapter" for anchor in item.applicable_passage_anchors)
            for item in items
        ),
        "eligible_explicit_scripture_anchor_count": sum(len(item.applicable_passage_anchors) for item in items),
        "ckl_physical_place_item_count": sum(item.record_kind == "object" and item.object_type == "place" for item in items),
        "ckl_physical_place_item_ids_json": json.dumps(sorted(item.id for item in items if item.record_kind == "object" and item.object_type == "place"), separators=(",", ":")),
        "ckl_unknown_or_uncertain_place_identification_count": sum(
            item.record_kind == "object"
            and item.object_type == "place"
            and str(item.place_identification_confidence or "unknown").casefold().replace("-", "_")
            in {"unknown", "low", "disputed", "unidentified", "uncertain", "insufficient_evidence"}
            for item in items
        ),
        "lookup_unresolved_anchor_count": unresolved_anchor_count,
        "coverage_category": coverage_category(items, lookup_status=lookup_status),
        "ckl_item_ids_json": json.dumps([item.id for item in items], separators=(",", ":")),
        "ckl_parent_object_ids_json": json.dumps(sorted({item.object_id for item in items if item.object_id}), separators=(",", ":")),
    })
    row.update(source_metrics)
    row.update(_status_counts(items))
    row.update(_relationship_metrics(connections))
    row.update(_matching_anchor_counts(anchor_audit, items))
    row.update(_context_counts(items, candidates))
    for section in SECTION_IDS:
        row[SECTION_COLUMNS[section]] = sum(section in item.section_ids for item in items)
    row["cosmic_geography_ckl_item_ids_json"] = json.dumps(
        sorted(item.id for item in items if "divine_council_cosmic_geography" in item.section_ids),
        separators=(",", ":"),
    )

    claims = [item for item in items if item.record_kind == "claim"]
    evidence = [item for item in items if item.record_kind == "evidence"]
    notes = [item for item in items if item.record_kind == "interpretive_note"]
    row["historical_context_claim_count"] = sum(str(item.claim_type or "").casefold().replace("-", "_") in {"historical_cultural", "historical", "social", "political"} for item in claims)
    row["historical_context_note_count"] = sum("archaeology_ancient_history" in item.section_ids for item in notes)
    row["cultural_background_parent_count"] = sum(item.record_kind == "object" and item.object_type == "cultural_background" for item in items)
    row["ckl_archaeology_parent_count"] = sum(item.record_kind == "object" and item.object_type == "archaeology" for item in items)
    row["ckl_archaeology_evidence_item_count"] = sum(
        item.record_kind == "evidence" and str(item.evidence_category or "").casefold().replace("_", "-") in ARCHAEOLOGY_EVIDENCE_TYPES
        for item in evidence
    )
    row["ckl_ancient_text_or_manuscript_evidence_item_count"] = sum(
        item.record_kind == "evidence" and str(item.evidence_category or "").casefold().replace("_", "-") in ANCIENT_TEXT_EVIDENCE_TYPES
        for item in evidence
    )
    row["ckl_original_passage_evidence_anchor_count"] = 0
    row["ckl_comparative_background_evidence_anchor_count"] = 0
    row["ckl_unspecified_evidence_anchor_count"] = 0
    for item in evidence:
        for anchor in item.applicable_passage_anchors:
            relationship = str(anchor.get("relationship") or "").casefold().replace("_", "-")
            if relationship in DIRECT_RELATIONSHIPS:
                row["ckl_original_passage_evidence_anchor_count"] += 1
            elif relationship in COMPARATIVE_RELATIONSHIPS:
                row["ckl_comparative_background_evidence_anchor_count"] += 1
            else:
                row["ckl_unspecified_evidence_anchor_count"] += 1
    row.update(external_links or {})
    row["map_api_lookup_state"] = "unknown_not_run"
    row["archaeology_api_lookup_state"] = "unknown_not_run"
    row["map_api_item_count"] = ""
    row["archaeology_api_item_count"] = ""
    row["map_live_ids_json"] = "[]"
    row["archaeology_live_ids_json"] = "[]"
    row["map_ids_hidden_from_live_sample_json"] = "[]"
    row["archaeology_ids_hidden_from_live_sample_json"] = "[]"
    row["validation_sample"] = False
    row["validation_sample_reason"] = ""
    row["live_api_status"] = "not_run"
    return row, projection


def _read_only_sqlite_snapshot(path: Path, bible: Mapping[str, Any]) -> dict[str, Any]:
    """Read domain link contracts without invoking any database writer."""

    if not path.is_file():
        return {"status": "unknown_database_missing", "path": str(path), "links_by_chapter": {}, "metrics": {}}
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    try:
        schema = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        table_names = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {
            "biblical_places", "place_references", "map_routes", "route_references",
            "political_context_layers", "political_context_references",
            "archaeology_items", "archaeology_scripture_links", "manuscript_items",
            "manuscript_scripture_links",
        }
        if int(schema or 0) < 37 or not required.issubset(table_names) or integrity != "ok":
            return {
                "status": "unknown_database_schema_or_integrity",
                "path": str(path), "schema_version": int(schema or 0),
                "integrity_check": integrity, "links_by_chapter": {}, "metrics": {},
            }
        bible_counts = {
            str(book["name"]): {
                int(chapter["chapter"]): len(chapter.get("verses", []))
                for chapter in book.get("chapters", [])
            }
            for book in bible["books"]
        }
        link_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        metrics: dict[str, Any] = {
            "schema_version": int(schema),
            "integrity_check": integrity,
            "reference_rows": {},
            "valid_reference_rows": {},
            "invalid_reference_rows": {},
            "broken_target_rows": {},
            "distinct_linked_target_counts": {},
            "map_place_catalog_confidence_counts": {},
            "map_place_low_or_unknown_catalog_confidence_counts": {},
        }
        specifications = (
            ("map_places", "place_references", "place_id", "biblical_places", "physical_place"),
            ("map_routes", "route_references", "route_id", "map_routes", "route"),
            ("map_territories", "political_context_references", "context_id", "political_context_layers", "political_territory"),
            ("archaeology_service", "archaeology_scripture_links", "item_id", "archaeology_items", "archaeology_item"),
            ("manuscript_service", "manuscript_scripture_links", "item_id", "manuscript_items", "manuscript_item"),
        )
        for domain, link_table, target_field, target_table, geography_kind in specifications:
            raw_rows = [dict(row) for row in connection.execute(f'SELECT * FROM "{link_table}" ORDER BY book, chapter, verse_start, verse_end, {target_field}')]
            target_rows = [dict(row) for row in connection.execute(f'SELECT * FROM "{target_table}"')]
            target_by_id = {str(row.get("id") or ""): row for row in target_rows}
            targets_by_chapter: dict[str, set[str]] = defaultdict(set)
            valid_link_target_ids: set[str] = set()
            broken = 0
            invalid = 0
            valid = 0
            for row in raw_rows:
                target_id = str(row.get(target_field) or "")
                broken += int(target_id not in target_by_id)
                try:
                    book = normalize_book_name(str(row.get("book") or ""))
                    chapter = int(row.get("chapter"))
                    start = int(row.get("verse_start") or 1)
                    end = int(row.get("verse_end") or start)
                    verse_total = bible_counts[book][chapter]
                    is_valid = start > 0 and end >= start and end <= verse_total
                except (KeyError, TypeError, ValueError):
                    is_valid = False
                    book = ""
                    chapter = 0
                    start = end = 0
                if not is_valid:
                    invalid += 1
                    continue
                valid += 1
                if not book or not target_id:
                    continue
                target = target_by_id.get(target_id, {})
                if target_id in target_by_id:
                    valid_link_target_ids.add(target_id)
                if domain == "map_places":
                    confidence = str(target.get("confidence") or "unknown").casefold()
                    metrics["map_place_catalog_confidence_counts"][confidence] = metrics["map_place_catalog_confidence_counts"].get(confidence, 0) + 1
                    if confidence in {"unknown", "low", "disputed", "unidentified", "uncertain"}:
                        metrics["map_place_low_or_unknown_catalog_confidence_counts"][confidence] = metrics["map_place_low_or_unknown_catalog_confidence_counts"].get(confidence, 0) + 1
                link = {
                    "domain": domain,
                    "target_id": target_id,
                    "relationship": str(row.get("relationship_type") or ""),
                    "geography_kind": geography_kind,
                    "target_exists": target_id in target_by_id,
                    "target_confidence": str(target.get("confidence") or "unknown"),
                    "start_verse": start,
                    "end_verse": end,
                }
                key = f"{book} {chapter}"
                link_rows[key].append(link)
                targets_by_chapter[key].add(target_id)
            metrics["reference_rows"][domain] = len(raw_rows)
            metrics.setdefault("inventory_item_counts", {})[domain] = len(target_rows)
            metrics["valid_reference_rows"][domain] = valid
            metrics["invalid_reference_rows"][domain] = invalid
            metrics["broken_target_rows"][domain] = broken
            metrics["distinct_linked_target_counts"][domain] = sum(len(ids) for ids in targets_by_chapter.values())
            metrics.setdefault("targets_with_valid_passage_link_counts", {})[domain] = len(valid_link_target_ids)
            metrics.setdefault("items_without_valid_passage_link_counts", {})[domain] = len(target_rows) - len(valid_link_target_ids)
            metrics["map_place_catalog_confidence_counts"] = dict(sorted(metrics["map_place_catalog_confidence_counts"].items()))
            metrics["map_place_low_or_unknown_catalog_confidence_counts"] = dict(sorted(metrics["map_place_low_or_unknown_catalog_confidence_counts"].items()))
        for key, rows in link_rows.items():
            link_rows[key] = sorted(rows, key=lambda row: (row["domain"], row["target_id"], row["start_verse"], row["end_verse"]))
        return {
            "status": "complete",
            "path": str(path),
            "schema_version": int(schema),
            "integrity_check": integrity,
            "links_by_chapter": dict(link_rows),
            "metrics": metrics,
        }
    finally:
        connection.close()


def _static_map_feature_links(chapters: Sequence[Mapping[str, Any]], repo_root: Path) -> dict[str, Any]:
    index: dict[str, list[dict[str, str]]] = defaultdict(list)
    invalid: list[dict[str, str]] = []
    layer_root = repo_root / "bhf_web" / "static" / "data" / "mapLayers"
    if not layer_root.is_dir():
        return {"status": "unknown_static_map_layers_missing", "by_chapter": {}, "invalid": []}
    chapter_names = {str(row["reference"]) for row in chapters}
    for path in sorted(layer_root.glob("*.json")):
        try:
            layer = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            invalid.append({"file": path.name, "reference": "<file unreadable>"})
            continue
        for feature in layer.get("features", []) if isinstance(layer, Mapping) else []:
            if not isinstance(feature, Mapping):
                continue
            feature_id = str(feature.get("id") or feature.get("name") or "")
            for reference in _record_refs(feature.get("passages") or feature.get("scripture_references")):
                spans = parse_scripture_references(reference, book_alias_lookup=_BOOK_ALIASES)
                if not spans:
                    invalid.append({"file": path.name, "reference": reference})
                    continue
                for chapter in chapters:
                    query = parse_scripture_query(str(chapter["reference"]), book_alias_lookup=_BOOK_ALIASES)
                    if query and any(scripture_reference_overlaps(query, span) for span in spans):
                        index[str(chapter["reference"])].append({
                            "layer_file": path.name,
                            "feature_id": feature_id,
                            "geography_kind": str(feature.get("geography_kind") or "unknown"),
                            "reference": reference,
                        })
    return {"status": "complete", "by_chapter": dict(index), "invalid": invalid}


def _attach_external_counts(row: dict[str, Any], links: Sequence[Mapping[str, Any]], static_links: Sequence[Mapping[str, Any]]) -> None:
    counts = Counter(str(link.get("domain") or "") for link in links)
    valid_targets = Counter(str(link.get("domain") or "") for link in links if link.get("target_exists"))
    low_or_unknown_catalog_confidence = sum(
        link.get("domain") == "map_places"
        and str(link.get("target_confidence") or "unknown").casefold() in {"unknown", "low", "disputed", "unidentified", "uncertain"}
        for link in links
    )
    row.update({
        "map_place_explicit_link_count": counts.get("map_places", 0),
        "map_place_resolvable_link_count": valid_targets.get("map_places", 0),
        "map_route_explicit_link_count": counts.get("map_routes", 0),
        "map_route_resolvable_link_count": valid_targets.get("map_routes", 0),
        "map_territory_explicit_link_count": counts.get("map_territories", 0),
        "map_territory_resolvable_link_count": valid_targets.get("map_territories", 0),
        "map_place_low_or_unknown_catalog_confidence_link_count": low_or_unknown_catalog_confidence,
        "archaeology_service_explicit_link_count": counts.get("archaeology_service", 0),
        "archaeology_service_resolvable_link_count": valid_targets.get("archaeology_service", 0),
        "manuscript_service_explicit_link_count": counts.get("manuscript_service", 0),
        "static_map_feature_passage_link_count": len(static_links),
        "static_map_feature_ids_json": json.dumps(sorted({str(link.get("feature_id") or "") for link in static_links}), separators=(",", ":")),
        "external_explicit_link_state": "complete" if links else "complete_empty",
    })


def _source_id_audit(
    library: CanonicalLibrary,
    chapter_verse_counts: Mapping[str, Mapping[int, int]],
) -> dict[str, Any]:
    source_ids: set[str] = set()
    missing: list[dict[str, Any]] = []
    poor_bibliography: list[dict[str, str]] = []
    repeated: list[dict[str, str]] = []
    source_record_count = 0
    child_source_reference_count = 0
    resolved_child_source_reference_count = 0
    anchor_inventory: dict[str, Counter[str]] = defaultdict(Counter)
    archaeology_unanchored_ids: list[str] = []
    ancient_text_unanchored_ids: list[str] = []
    historical_claims_unanchored_ids: list[str] = []

    def record_anchor_state(kind: str, record: Mapping[str, Any], stable_id: str) -> None:
        references = _record_refs(record.get("scripture_references"))
        valid_references = [reference for reference in references if scripture_reference_is_canonical(reference, chapter_verse_counts, library._book_alias_lookup)]
        state = "no_explicit_anchor" if not references else ("valid_anchor" if len(valid_references) == len(references) else ("partially_invalid" if valid_references else "invalid_anchor_only"))
        anchor_inventory[kind]["record_count"] += 1
        anchor_inventory[kind][state] += 1
        anchor_inventory[kind]["explicit_anchor_reference_count"] += len(references)
        anchor_inventory[kind]["valid_anchor_reference_count"] += len(valid_references)
        if kind != "evidence" or valid_references:
            return
        evidence_category = str(record.get("evidence_type") or record.get("evidence_category") or "unclassified").casefold().replace("_", "-")
        if evidence_category in ARCHAEOLOGY_EVIDENCE_TYPES:
            archaeology_unanchored_ids.append(stable_id)
        if evidence_category in ANCIENT_TEXT_EVIDENCE_TYPES:
            ancient_text_unanchored_ids.append(stable_id)

    for obj in library.objects_by_id.values():
        data = _as_mapping(obj)
        record_anchor_state("object", data, obj.id)
        sources: dict[str, dict[str, Any]] = {}
        for raw_source in _sequence(data.get("sources")):
            source = _as_mapping(raw_source)
            source_id = str(source.get("id") or "")
            if source_id:
                sources[source_id] = source
                source_ids.add(source_id)
                source_record_count += 1
        for field, kind in (("claims", "claim"), ("evidence_items", "evidence"), ("interpretive_notes", "interpretive_note")):
            for raw_child in _sequence(data.get(field)):
                child = _as_mapping(raw_child)
                child_id = str(child.get("id") or (_child_local_id(kind, child) if kind == "interpretive_note" else ""))
                record_anchor_state(kind, child, f"{obj.id}#{kind}:{child_id}")
                if kind == "claim" and str(child.get("claim_type") or "").casefold().replace("-", "_") in {"historical", "historical_cultural", "social", "political"}:
                    refs = _record_refs(child.get("scripture_references"))
                    if not any(scripture_reference_is_canonical(reference, chapter_verse_counts, library._book_alias_lookup) for reference in refs):
                        historical_claims_unanchored_ids.append(f"{obj.id}#claim:{child_id}")
                ids = child.get("source_ids") if kind != "interpretive_note" else child.get("sources")
                for raw_id in _sequence(ids):
                    value = _as_mapping(raw_id)
                    source_id = str(value.get("id") if value else raw_id or "")
                    if not source_id:
                        continue
                    child_source_reference_count += 1
                    source_ids.add(source_id)
                    if source_id not in sources:
                        missing.append({
                            "object_id": obj.id,
                            "record_kind": kind,
                            "record_id": child_id,
                            "item_id": f"{obj.id}#{kind}:{child_id}",
                            "source_id": source_id,
                            "scripture_references": _record_refs(child.get("scripture_references")),
                        })
                        continue
                    resolved_child_source_reference_count += 1
                    source = sources[source_id]
                    title = str(source.get("title") or "").strip()
                    useful = any(str(source.get(key) or "").strip() for key in ("author", "publisher", "year", "locator", "url"))
                    if not title or not useful:
                        poor_bibliography.append({"object_id": obj.id, "record_kind": kind, "record_id": str(child.get("id") or ""), "source_id": source_id})
        for field in ("related_objects",):
            edge_keys = []
            for raw_edge in _sequence(data.get(field)):
                edge = _as_mapping(raw_edge)
                key = (str(edge.get("id") or ""), str(edge.get("relationship") or ""))
                if key in edge_keys:
                    repeated.append({"object_id": obj.id, "target_id": key[0], "relationship": key[1]})
                edge_keys.append(key)
    return {
        "unique_source_ids": len(source_ids),
        "source_record_count": source_record_count,
        "child_source_reference_count": child_source_reference_count,
        "resolved_child_source_reference_count": resolved_child_source_reference_count,
        "unresolved_child_source_reference_count": child_source_reference_count - resolved_child_source_reference_count,
        "anchor_inventory_by_record_kind": {kind: dict(sorted(counts.items())) for kind, counts in sorted(anchor_inventory.items())},
        "archaeological_evidence_items_without_valid_passage_anchor_count": len(archaeology_unanchored_ids),
        "archaeological_evidence_items_without_valid_passage_anchor_ids": sorted(archaeology_unanchored_ids),
        "ancient_text_or_manuscript_evidence_items_without_valid_passage_anchor_count": len(ancient_text_unanchored_ids),
        "ancient_text_or_manuscript_evidence_items_without_valid_passage_anchor_ids": sorted(ancient_text_unanchored_ids),
        "historical_cultural_claims_without_valid_passage_anchor_count": len(historical_claims_unanchored_ids),
        "historical_cultural_claims_without_valid_passage_anchor_ids": sorted(historical_claims_unanchored_ids),
        "missing_source_id_references": missing,
        "poor_bibliography_references": poor_bibliography,
        "duplicate_object_relationships": repeated,
    }


def _relationship_audit(library: CanonicalLibrary) -> dict[str, Any]:
    object_edges: list[tuple[str, str, str, str]] = []
    evidence_edges: list[tuple[str, str, str, str]] = []
    missing_targets: list[dict[str, str]] = []
    untyped_legacy: Counter[str] = Counter()
    legacy_fields: Counter[str] = Counter()
    duplicate_edge_count = 0
    book_level_relationship_count = 0
    for obj in library.objects_by_id.values():
        data = _as_mapping(obj)
        seen: set[tuple[str, str, str]] = set()
        for raw in _sequence(data.get("related_objects")):
            rel = _as_mapping(raw)
            target = str(rel.get("id") or "")
            relationship = str(rel.get("relationship") or "")
            label = _normalized_label(relationship)
            if label not in {_normalized_label(value) for value in _CONNECTION_TYPE_BY_LABEL}:
                untyped_legacy[relationship or "<missing>"] += 1
            if target:
                object_edges.append((obj.id, target, relationship, str(rel.get("notes") or "")))
                book_level_relationship_count += int(obj.type == "book")
                key = (target, relationship, str(rel.get("weight") or "1"))
                duplicate_edge_count += int(key in seen)
                seen.add(key)
                if target not in library.objects_by_id:
                    missing_targets.append({"source_id": obj.id, "target_id": target, "relationship": relationship, "kind": "related_object"})
        for raw in _sequence(data.get("evidence_items")):
            evidence = _as_mapping(raw)
            evidence_id = str(evidence.get("id") or "")
            for relationship in _sequence(evidence.get("related_objects")):
                rel = _as_mapping(relationship)
                target = str(rel.get("id") or "")
                label = str(rel.get("relationship") or "")
                evidence_edges.append((f"{obj.id}#evidence:{evidence_id}", target, label, str(rel.get("notes") or "")))
                if target not in library.objects_by_id:
                    missing_targets.append({"source_id": f"{obj.id}#evidence:{evidence_id}", "target_id": target, "relationship": label, "kind": "evidence_related_object"})
            known_evidence = {str(_as_mapping(item).get("id") or "") for item in _sequence(data.get("evidence_items"))}
            for relationship in _sequence(evidence.get("related_evidence")):
                rel = _as_mapping(relationship)
                target = str(rel.get("id") or "")
                evidence_edges.append((f"{obj.id}#evidence:{evidence_id}", f"{obj.id}#evidence:{target}", str(rel.get("relationship") or ""), str(rel.get("notes") or "")))
                if target not in known_evidence:
                    missing_targets.append({"source_id": f"{obj.id}#evidence:{evidence_id}", "target_id": target, "relationship": str(rel.get("relationship") or ""), "kind": "related_evidence"})
        for field in ("related_entries", "cross_references", "new_testament_connections", "intertextuality"):
            legacy_fields[field] += len(_sequence(data.get(field)))
    edge_keys = {(source, target, relation) for source, target, relation, _notes in object_edges}
    reciprocal = sum((target, source, relation) in edge_keys for source, target, relation, _notes in object_edges) // 2
    typed = Counter(_CONNECTION_TYPE_BY_LABEL.get(_normalized_label(relationship), "uncategorized") for _s, _t, relationship, _n in object_edges)
    graph = evidence_graph_edges(library.objects_by_id.values())
    passage_edges = sum(edge.source_kind == "passage" for edge in graph)
    return {
        "authored_object_relationship_count": len(object_edges),
        "authored_evidence_relationship_count": len(evidence_edges),
        "relationship_type_counts": dict(sorted(typed.items())),
        "uncategorized_legacy_relationship_count": typed.get("uncategorized", 0),
        "uncategorized_relationship_labels": dict(sorted(untyped_legacy.items())),
        "legacy_free_text_relationship_field_counts": dict(sorted(legacy_fields.items())),
        "book_level_related_object_count_excluded_from_ne_projection": book_level_relationship_count,
        "resolvable_object_relationship_count": sum(target in library.objects_by_id for _source, target, _rel, _notes in object_edges),
        "missing_destination_count": len(missing_targets),
        "missing_destinations": missing_targets,
        "genuinely_reciprocal_object_relationship_pairs": reciprocal,
        "one_way_object_relationship_count": len(object_edges) - 2 * reciprocal,
        "duplicate_object_relationship_count": duplicate_edge_count,
        "graph_edge_count": len(graph),
        "explicit_passage_graph_edge_count": passage_edges,
    }


def _attach_unresolved_source_ids(rows: Sequence[dict[str, Any]], source_audit: Mapping[str, Any]) -> None:
    missing_by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unresolved in source_audit["missing_source_id_references"]:
        missing_by_item[str(unresolved["item_id"])].append(unresolved)
    for row in rows:
        eligible_item_ids = set(json.loads(str(row["ckl_item_ids_json"])))
        unresolved_for_chapter = [
            unresolved
            for item_id in sorted(eligible_item_ids)
            for unresolved in missing_by_item.get(item_id, [])
        ]
        row["unresolved_source_id_reference_count"] = len(unresolved_for_chapter)
        row["unresolved_source_id_references_json"] = json.dumps(
            [
                {
                    "item_id": unresolved["item_id"],
                    "source_id": unresolved["source_id"],
                    "scripture_references": unresolved["scripture_references"],
                }
                for unresolved in unresolved_for_chapter
            ],
            separators=(",", ":"),
        )


def _theme_inventory(library: CanonicalLibrary) -> dict[str, Any]:
    authored_edges: list[dict[str, str]] = []
    adjacency: dict[str, set[str]] = defaultdict(set)
    for obj in library.objects_by_id.values():
        for raw in _sequence(_as_mapping(obj).get("related_objects")):
            rel = _as_mapping(raw)
            source, target = obj.id, str(rel.get("id") or "")
            if target and target in library.objects_by_id:
                adjacency[source].add(target)
                authored_edges.append({"source_id": source, "target_id": target, "relationship": str(rel.get("relationship") or ""), "notes": str(rel.get("notes") or "")})
    topics: dict[str, Any] = {}
    for topic, object_ids in TOPIC_OBJECTS.items():
        present = [object_id for object_id in object_ids if object_id in library.objects_by_id]
        missing = [object_id for object_id in object_ids if object_id not in library.objects_by_id]
        records: list[dict[str, Any]] = []
        for object_id in present:
            obj = library.objects_by_id[object_id]
            data = _as_mapping(obj)
            allowlist = TOPIC_CHILD_ALLOWLIST.get(topic, {}).get(object_id)
            sources_by_id = {
                str(_as_mapping(source).get("id") or ""): _as_mapping(source)
                for source in _sequence(data.get("sources"))
                if _as_mapping(source).get("id")
            }
            for kind, field in (("object", ""), ("claim", "claims"), ("evidence", "evidence_items"), ("interpretive_note", "interpretive_notes")):
                values = [data] if kind == "object" else [_as_mapping(item) for item in _sequence(data.get(field))]
                for value in values:
                    local_id = str(value.get("id") or "")
                    if allowlist is not None:
                        if kind == "object" or local_id not in allowlist:
                            continue
                    refs = _record_refs(value.get("scripture_references"))
                    if not refs:
                        continue
                    source_values = value.get("source_ids") if kind in {"claim", "evidence"} else value.get("sources")
                    source_values = _sequence(source_values)
                    source_ids = [str(_as_mapping(item).get("id") or item) for item in source_values]
                    traceable_source_ids = sorted({
                        source_id for source_id in source_ids
                        if source_id in sources_by_id
                        and str(sources_by_id[source_id].get("title") or "").strip()
                        and any(str(sources_by_id[source_id].get(key) or "").strip() for key in ("author", "publisher", "year", "locator", "url"))
                    })
                    anchor_values = _sequence(value.get("scripture_references"))
                    records.append({
                        "object_id": object_id,
                        "record_kind": kind,
                        "record_id": local_id or (_child_local_id(kind, value) if kind == "interpretive_note" else None),
                        "passage_anchors": refs,
                        "passage_anchor_details": [
                            {
                                "reference": str(_as_mapping(anchor).get("reference") or anchor) if isinstance(anchor, (Mapping, str)) else str(getattr(anchor, "reference", "")),
                                "relationship": _as_mapping(anchor).get("relationship") if isinstance(anchor, Mapping) else getattr(anchor, "relationship", None),
                                "temporal_relation": _as_mapping(anchor).get("temporal_relation") if isinstance(anchor, Mapping) else getattr(anchor, "temporal_relation", None),
                                "relevance_rationale": _as_mapping(anchor).get("relevance_rationale") if isinstance(anchor, Mapping) else getattr(anchor, "relevance_rationale", None),
                            }
                            for anchor in anchor_values
                        ],
                        "source_ids": sorted(set(value for value in source_ids if value)),
                        "traceable_source_ids": traceable_source_ids,
                        "certainty": value.get("certainty"),
                        "dispute_status": value.get("dispute_status"),
                        "evidence_type": value.get("evidence_type"),
                        "claim_type": value.get("claim_type"),
                    })
        within_edges = [edge for edge in authored_edges if edge["source_id"] in present and edge["target_id"] in present]
        covered_ids = {record["object_id"] for record in records}
        source_backed_records = [
            record for record in records
            if record["record_kind"] in {"claim", "evidence"} and record["traceable_source_ids"]
        ]
        gap_flags = []
        if missing:
            gap_flags.append("expected_seed_object_id_missing")
        if set(present) - covered_ids:
            gap_flags.append("seed_object_has_no_selected_explicit_anchor")
        if not source_backed_records:
            gap_flags.append("no_traceable_source_backed_claim_or_evidence_in_selected_records")
        if not within_edges:
            gap_flags.append("no_direct_authored_relationship_between_selected_seed_objects")
        topics[topic] = {
            "seed_object_ids": present,
            "missing_seed_object_ids": missing,
            "anchored_record_count": len(records),
            "explicit_passage_anchors": sorted({anchor for record in records for anchor in record["passage_anchors"]}),
            "source_backed_record_count": len(source_backed_records),
            "source_backed_claim_or_evidence_record_ids": [
                f"{record['object_id']}#{record['record_kind']}:{record['record_id']}"
                for record in source_backed_records
            ],
            "records": records,
            "authored_traversable_connections": within_edges,
            "authored_connection_count": len(within_edges),
            "seed_objects_without_anchored_records": sorted(set(present) - covered_ids),
            "within_seed_inventory_gap_flags": gap_flags,
            "topic_trail_state": "traversable_authored_links" if within_edges else ("anchored_objects_without_direct_authored_inter_object_link" if records else "no_anchored_records_in_seed_set"),
        }
    return {
        "topics": topics,
        "authored_object_relationship_count": len(authored_edges),
        "topic_link_limits": "Only exact IDs in the topic seed list and authored CKL relationship edges are included. Shared subject matter, search terms, or thematic similarity do not create a traversable edge.",
    }


def _sample_reasons(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    reasons: dict[str, set[str]] = defaultdict(set)
    by_ref = {str(row["reference"]): row for row in rows}
    for reference in PILOT_REFERENCES:
        if reference in by_ref:
            reasons[reference].add("established_pilot")
    for chapter in select_stratified_sample(rows, seed=SAMPLE_SEED, per_stratum=1):
        reasons[str(chapter["reference"])].add(f"stratum:{chapter['stratum']}")
    ordered = sorted(rows, key=lambda row: int(row["canonical_order"]))
    if ordered:
        sparse = min(ordered, key=lambda row: (int(row["eligible_ckl_item_count"]), int(row["canonical_order"])))
        dense = max(ordered, key=lambda row: (int(row["eligible_ckl_item_count"]), -int(row["canonical_order"])))
        reasons[str(sparse["reference"])].add("sparse_ckl_case")
        reasons[str(dense["reference"])].add("dense_ckl_case")
    cases = (
        ("book_level_anchor_case", lambda row: int(row["book_level_anchor_reference_count"]) > 0),
        ("multi_chapter_anchor_case", lambda row: int(row["multi_chapter_anchor_reference_count"]) > 0),
        ("verse_scoped_case", lambda row: int(row["verse_scoped_eligible_item_count"]) > 0),
        ("unclassified_or_misanchor_case", lambda row: int(row["unclassified_ckl_item_count"]) > 0 or int(row["semantically_misanchored_anchor_count"]) > 0),
        ("unknown_or_uncertain_physical_identity_case", lambda row: int(row.get("ckl_unknown_or_uncertain_place_identification_count", 0)) > 0),
        ("empty_ckl_case", lambda row: row["coverage_category"] == "no_eligible_ckl_material"),
    )
    for reason, predicate in cases:
        match = next((row for row in ordered if predicate(row)), None)
        if match:
            reasons[str(match["reference"])].add(reason)
    return {reference: sorted(values) for reference, values in reasons.items()}


def _projected_ckl_signature(projection: Any) -> tuple[list[tuple[str, tuple[str, ...], tuple[str, ...]]], list[str]]:
    items = sorted(
        (item.id, tuple(item.section_ids), tuple(item.source_ids))
        for item in projection.items if item.domain == "ckl"
    )
    connections = sorted(
        edge.id for edge in projection.connections
        if str(edge.basis.get("kind") or "").startswith("ckl_")
    )
    return items, connections


def _validate_sample(
    chapters: Sequence[Mapping[str, Any]],
    rows_by_ref: dict[str, dict[str, Any]],
    projections: dict[str, Any],
    library: CanonicalLibrary,
    sample_reasons: Mapping[str, Sequence[str]],
    study_db_path: Path,
    live_api_references: set[str],
) -> list[dict[str, Any]]:
    service = NarrativeExplorerService(study_db_path=study_db_path)
    chapter_by_ref = {str(row["reference"]): row for row in chapters}
    results: list[dict[str, Any]] = []
    ordered_references = sorted(sample_reasons, key=lambda value: int(chapter_by_ref[value]["canonical_order"]))
    for sample_number, reference in enumerate(ordered_references, start=1):
        print(f"[ne-a1] validating sample {sample_number}/{len(ordered_references)}: {reference}", file=sys.stderr, flush=True)
        chapter = chapter_by_ref[reference]
        exact_results = library.retrieve_by_scripture_reference(
            reference,
            limit=max(1, len(library.objects_by_id)),
            include_placeholders=True,
        )
        expected_ids = [result.object.id for result in exact_results]
        indexed_ids = [
            object_id for object_id in rows_by_ref[reference].get("_candidate_ids", [])
        ]
        exact_candidates_match = set(expected_ids) == set(indexed_ids)
        expected_projection = project_narrative_explorer(
            reference,
            canonical_lookup=DomainLookup(domain="ckl", records=exact_results, query_status="complete"),
        )
        expected_signature = _projected_ckl_signature(expected_projection)
        census_signature = _projected_ckl_signature(projections[reference])
        ckl_projection_match = expected_signature == census_signature
        entry: dict[str, Any] = {
            "reference": reference,
            "reasons": list(sample_reasons[reference]),
            "candidate_count": len(indexed_ids),
            "normal_retrieval_candidate_count": len(expected_ids),
            "candidate_index_matches_normal_retrieval": exact_candidates_match,
            "projector_ckl_signature_matches_normal_retrieval": ckl_projection_match,
            "expected_ckl_item_count": len(expected_signature[0]),
            "expected_ckl_connection_count": len(expected_signature[1]),
            "live_api_sampled": reference in live_api_references,
            "live_api_status": "not_run_sample_scope",
        }
        try:
            if reference not in live_api_references:
                row = rows_by_ref[reference]
                row["validation_sample"] = True
                row["validation_sample_reason"] = "|".join(sample_reasons[reference])
                row["live_api_status"] = entry["live_api_status"]
                results.append(entry)
                continue
            actual = service.build(chapter["book"], int(chapter["chapter"]))
            actual_ckl_items = [item for item in actual["items"] if item.get("domain") == "ckl"]
            actual_ckl_connections = [
                edge for edge in actual["connections"]
                if str(edge.get("basis", {}).get("kind") or "").startswith("ckl_")
            ]
            actual_signature = (
                sorted((str(item.get("id")), tuple(item.get("section_ids") or ()), tuple(item.get("source_ids") or ())) for item in actual_ckl_items),
                sorted(str(edge.get("id")) for edge in actual_ckl_connections),
            )
            entry.update({
                "live_api_status": "complete",
                "live_api_ckl_projection_matches_census": actual_signature == census_signature,
                "live_api_ckl_item_count": len(actual_ckl_items),
                "live_api_ckl_connection_count": len(actual_ckl_connections),
                "live_api_map_status": next((coverage.get("query_status") for coverage in actual["coverage"] if coverage.get("domain") == "maps"), "unknown"),
                "live_api_archaeology_status": next((coverage.get("query_status") for coverage in actual["coverage"] if coverage.get("domain") == "archaeology"), "unknown"),
                "live_api_map_item_ids": sorted(str(item.get("object_id") or "") for item in actual["items"] if item.get("domain") == "maps"),
                "live_api_archaeology_item_ids": sorted(str(item.get("object_id") or "") for item in actual["items"] if item.get("domain") == "archaeology"),
                "live_api_map_geography_kinds": sorted(str(item.get("geography_kind") or "unknown") for item in actual["items"] if item.get("domain") == "maps"),
                "live_api_map_item_count": sum(item.get("domain") == "maps" for item in actual["items"]),
                "live_api_archaeology_item_count": sum(item.get("domain") == "archaeology" for item in actual["items"]),
                "live_api_sections": {section["id"]: {"state": section["state"], "item_count": len(section["item_ids"])} for section in actual["sections"]},
            })
        except Exception as exc:  # pragma: no cover - depends on deployment-shaped local indexes
            entry["live_api_status"] = "failed"
            entry["live_api_failure_type"] = type(exc).__name__
            entry["live_api_failure"] = str(exc)[:240]
        row = rows_by_ref[reference]
        row["validation_sample"] = True
        row["validation_sample_reason"] = "|".join(sample_reasons[reference])
        row["live_api_status"] = entry["live_api_status"]
        if entry["live_api_status"] == "complete":
            row["map_api_lookup_state"] = str(entry["live_api_map_status"])
            row["archaeology_api_lookup_state"] = str(entry["live_api_archaeology_status"])
            row["map_api_item_count"] = int(entry["live_api_map_item_count"])
            row["archaeology_api_item_count"] = int(entry["live_api_archaeology_item_count"])
            row["map_live_ids_json"] = json.dumps(entry["live_api_map_item_ids"], separators=(",", ":"))
            row["archaeology_live_ids_json"] = json.dumps(entry["live_api_archaeology_item_ids"], separators=(",", ":"))
            explicit_map = {
                str(link["target_id"]) for link in row.get("_external_links", [])
                if link.get("domain") in {"map_places", "map_routes"} and link.get("target_exists")
            }
            explicit_arch = {
                str(link["target_id"]) for link in row.get("_external_links", [])
                if link.get("domain") == "archaeology_service" and link.get("target_exists")
            }
            live_map = set(entry["live_api_map_item_ids"])
            live_arch = set(entry["live_api_archaeology_item_ids"])
            row["map_ids_hidden_from_live_sample_json"] = json.dumps(sorted(explicit_map - live_map), separators=(",", ":"))
            row["archaeology_ids_hidden_from_live_sample_json"] = json.dumps(sorted(explicit_arch - live_arch), separators=(",", ":"))
        results.append(entry)
    return results


def _data_quality_summary(rows: Sequence[Mapping[str, Any]], library: CanonicalLibrary, relationship_audit: Mapping[str, Any], source_audit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "eligible_ckl_item_count_sum": sum(int(row["eligible_ckl_item_count"]) for row in rows),
        "eligible_parent_object_chapter_links": sum(int(row["eligible_parent_object_count"]) for row in rows),
        "unique_objects_projected_anywhere": len({
            object_id for row in rows for object_id in json.loads(str(row["ckl_parent_object_ids_json"]))
        }),
        "unique_claims_or_evidence_ids_projected": len({
            item_id for row in rows for item_id in json.loads(str(row["ckl_item_ids_json"])) if "#claim:" in item_id or "#evidence:" in item_id
        }),
        "chapter_counts_by_coverage_category": dict(sorted(Counter(str(row["coverage_category"]) for row in rows).items())),
        "chapters_with_source_grounded_claim_or_evidence": sum(int(row["source_backed_claim_or_evidence_count"]) > 0 for row in rows),
        "chapters_with_passage_specific_evidence": sum(row["coverage_category"] == "passage_specific_evidence" for row in rows),
        "chapters_with_contextual_or_entity_only_coverage": sum(row["coverage_category"] in {"contextual_coverage", "entity_only_coverage"} for row in rows),
        "chapters_with_no_eligible_ckl_material": sum(row["coverage_category"] == "no_eligible_ckl_material" for row in rows),
        "chapters_with_unknown_or_incomplete_ckl_coverage": sum(row["coverage_category"] == "incomplete_or_unknown" for row in rows),
        "chapters_with_broad_parent_scope_exclusions": sum(int(row["broad_parent_records_excluded_count"]) > 0 for row in rows),
        "chapters_with_book_level_anchors": sum(int(row["book_level_anchor_reference_count"]) > 0 for row in rows),
        "chapters_with_multi_chapter_anchors": sum(int(row["multi_chapter_anchor_reference_count"]) > 0 for row in rows),
        "chapters_with_broad_anchor_exclusions": sum(int(row["broad_anchor_records_excluded_count"]) > 0 for row in rows),
        "multi_chapter_anchor_reference_count": sum(int(row["multi_chapter_anchor_reference_count"]) for row in rows),
        "chapters_with_semantic_misanchor_suppression": sum(int(row["semantically_misanchored_anchor_count"]) > 0 for row in rows),
        "chapters_with_unclassified_projected_items": sum(int(row["unclassified_ckl_item_count"]) > 0 for row in rows),
        "chapters_with_only_contextual_parent_summaries": sum(int(row["broad_context_only_parent_count"]) > 0 and int(row["source_backed_claim_or_evidence_count"]) == 0 for row in rows),
        "projected_item_placement_quality_counts": {
            "eligible_item_placements": sum(int(row["eligible_ckl_item_count"]) for row in rows),
            "missing_review_metadata": sum(int(row["missing_review_metadata_count"]) for row in rows),
            "content_status_missing": sum(int(row["content_status_missing_count"]) for row in rows),
            "certainty_missing": sum(int(row["certainty_missing_count"]) for row in rows),
            "dispute_metadata_missing": sum(int(row["dispute_metadata_missing_count"]) for row in rows),
            "human_review_required": sum(int(row["human_review_required_count"]) for row in rows),
            "disputed_or_uncertain": sum(int(row["disputed_or_uncertain_item_count"]) for row in rows),
            "interpretation_state_unknown_or_unestablished": sum(int(row["interpretation_state_unknown_or_unestablished_count"]) for row in rows),
            "explicitly_disputed": sum(int(row["explicitly_disputed_item_count"]) for row in rows),
            "explicitly_uncertain": sum(int(row["explicitly_uncertain_item_count"]) for row in rows),
        },
        "sum_of_chapter_source_metrics": {
            "source_references": sum(int(row["source_reference_count"]) for row in rows),
            "source_ids": sum(int(row["source_id_count"]) for row in rows),
            "bibliography_resolvable_ids": sum(int(row["source_bibliography_resolvable_id_count"]) for row in rows),
            "bibliography_incomplete_ids": sum(int(row["source_bibliography_incomplete_id_count"]) for row in rows),
            "unresolved_source_references": sum(int(row["unresolved_source_reference_count"]) for row in rows),
            "unresolved_source_id_reference_chapter_placements": sum(int(row["unresolved_source_id_reference_count"]) for row in rows),
        },
        "source_audit_counts": {
            "unique_source_ids": int(source_audit["unique_source_ids"]),
            "source_record_count": int(source_audit["source_record_count"]),
            "child_source_references": int(source_audit["child_source_reference_count"]),
            "unresolved_source_id_references": len(source_audit["missing_source_id_references"]),
            "poor_bibliography_references": len(source_audit["poor_bibliography_references"]),
        },
        "relationship_audit_counts": {key: value for key, value in relationship_audit.items() if isinstance(value, (int, float))},
        "object_count": len(library.objects_by_id),
    }


def _book_findings(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["book"])].append(row)
    findings = []
    for book, chapters in grouped.items():
        chapters = sorted(chapters, key=lambda row: int(row["chapter"]))
        findings.append({
            "book": book,
            "testament": chapters[0]["testament"],
            "bible_genre": chapters[0]["bible_genre"],
            "stratum": chapters[0]["stratum"],
            "chapter_denominator": len(chapters),
            "passage_specific_chapters": sum(row["coverage_category"] == "passage_specific_evidence" for row in chapters),
            "contextual_chapters": sum(row["coverage_category"] == "contextual_coverage" for row in chapters),
            "entity_only_chapters": sum(row["coverage_category"] == "entity_only_coverage" for row in chapters),
            "no_eligible_ckl_chapters": sum(row["coverage_category"] == "no_eligible_ckl_material" for row in chapters),
            "unknown_chapters": sum(row["coverage_category"] == "incomplete_or_unknown" for row in chapters),
            "eligible_item_total": sum(int(row["eligible_ckl_item_count"]) for row in chapters),
            "source_grounded_children_total": sum(int(row["source_backed_claim_or_evidence_count"]) for row in chapters),
            "chapter_map_place_links": sum(int(row.get("map_place_explicit_link_count", 0)) for row in chapters),
            "chapter_archaeology_links": sum(int(row.get("archaeology_service_explicit_link_count", 0)) for row in chapters),
            **{column: sum(int(row.get(column, 0)) for row in chapters) for column in SECTION_COLUMNS.values()},
        })
    return findings


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [key for key in rows[0] if not key.startswith("_")]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: json.dumps(value, separators=(",", ":"), sort_keys=True) if isinstance(value, (list, dict, tuple)) else value
                for key, value in row.items()
            })


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _git_output(repo_root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(["git", *arguments], cwd=repo_root, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _database_marker(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False}
    stat = path.stat()
    return {"exists": True, "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "inode": stat.st_ino}


def _read_only_db_integrity(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "status": "missing"}
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only = ON")
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        schema_version = None
        if "ckl_metadata" in tables:
            schema_version = dict(connection.execute("SELECT key, value FROM ckl_metadata")).get("schema_version")
        return {"path": str(path), "integrity_check": integrity, "schema_version": schema_version, "table_count": len(tables), "status": "complete" if integrity == "ok" else "failed"}
    finally:
        connection.close()


def _collect_docs(
    output_dir: Path,
    *,
    rows: Sequence[Mapping[str, Any]],
    book_findings: Sequence[Mapping[str, Any]],
    totals: Mapping[str, Any],
    domain_metrics: Mapping[str, Any],
    relationships: Mapping[str, Any],
    source_audit: Mapping[str, Any],
    themes: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> None:
    summary_lines = [
        "# NE-A1 CKL coverage audit — executive summary", "",
        f"**Baseline:** NE-5B `{NE_ANCESTRY['NE-5B']}`; audit branch base is identified in `methodology-validation.json`.",
        f"**CKL inventory:** {totals['object_count']} validated objects; fingerprint `{validation['ckl_inventory_fingerprint']}`.",
        f"**Census:** {len(rows):,} of {EXPECTED_CHAPTERS:,} canonical chapters; all rows are generated from the authoritative ASV/BHF book list.", "",
        "## Chapter coverage", "",
        f"- Passage-specific evidence: {totals['chapters_with_passage_specific_evidence']} chapters; {totals['chapters_with_source_grounded_claim_or_evidence']} chapters have at least one sourced claim/evidence placement, including any chapter whose lookup remains incomplete.",
        f"- Contextual or entity-only coverage: {totals['chapters_with_contextual_or_entity_only_coverage']} chapters.",
        f"- No eligible CKL material under NE-5B passage rules: {totals['chapters_with_no_eligible_ckl_material']} chapters.",
        f"- Incomplete or unknown CKL coverage: {totals['chapters_with_unknown_or_incomplete_ckl_coverage']} chapter{'s' if totals['chapters_with_unknown_or_incomplete_ckl_coverage'] != 1 else ''}.",
        f"- Broad-scope parent records excluded in {totals['chapters_with_broad_parent_scope_exclusions']} chapters; unscoped book anchors occur in {totals['chapters_with_book_level_anchors']} chapters; multi-chapter anchors occur in {totals['chapters_with_multi_chapter_anchors']} chapters.",
        "", "These are inventory states, not judgments about whether a chapter should have archaeology, physical geography, or cosmic-geography material. A completed empty CKL lookup is not evidence that external scholarship contains nothing relevant.", "",
        "## External domains", "",
        f"- Explicit map/place links: {domain_metrics.get('reference_rows', {}).get('map_places', 0)} stored rows; {domain_metrics.get('valid_reference_rows', {}).get('map_places', 0)} pass book/chapter/verse checks; {domain_metrics.get('broken_target_rows', {}).get('map_places', 0)} target IDs do not resolve.",
        f"- Explicit route links: {domain_metrics.get('reference_rows', {}).get('map_routes', 0)} rows; territory/context links: {domain_metrics.get('reference_rows', {}).get('map_territories', 0)} rows.",
        f"- Archaeology service: {domain_metrics.get('inventory_item_counts', {}).get('archaeology_service', 0)} items; {domain_metrics.get('targets_with_valid_passage_link_counts', {}).get('archaeology_service', 0)} have valid passage links and {domain_metrics.get('items_without_valid_passage_link_counts', {}).get('archaeology_service', 0)} do not. It has {domain_metrics.get('reference_rows', {}).get('archaeology_service', 0)} explicit link rows; manuscript service is separate.",
        "- Full-corpus map and archaeology API counts are not inferred from the explicit-link tables. The API prefers passage-text matches before reference-link fallback, so only sampled chapters have live resolver results; other API states remain unknown in the CSV.",
        "", "## Provenance and relationships", "",
        f"- Unique source IDs referenced: {source_audit['unique_source_ids']}; unresolved source IDs: {len(source_audit['missing_source_id_references'])}; records with weak bibliography fields: {len(source_audit['poor_bibliography_references'])}.",
        f"- Authored object relationships: {relationships['authored_object_relationship_count']}; resolvable destinations: {relationships['resolvable_object_relationship_count']}; missing destinations: {relationships['missing_destination_count']}; exact reciprocal pairs: {relationships['genuinely_reciprocal_object_relationship_pairs']}; {relationships['uncategorized_legacy_relationship_count']} fall into the current `uncategorized` projection type.",
        f"- Projected CKL records without a Narrative Explorer section: {totals['chapters_with_unclassified_projected_items']} chapters contain at least one; investigate classification before adding evidence.",
        "", "## Validation", "",
        f"- Deterministic stratified sample seed: `{validation['sample_seed']}`; actual chapters compared: {len(validation['sample_checks'])}.",
        f"- Resolver-backed builds: {validation['live_api_sample_count']} targeted chapters; all selected chapters passed local normal-retrieval/projector comparison: {validation['candidate_index_matches_normal_retrieval']}.",
        f"- Census rows: {validation['chapter_row_count']}; unique identities: {validation['unique_chapter_identity_count']}; checks: `{validation['validation_status']}`.",
        "- CKL, map, and archaeology source records were not edited. Read-only database checks and sample details are in `methodology-validation.json`.",
    ]
    _write_markdown(output_dir / "01-executive-summary.md", "\n".join(summary_lines))

    method = [
        "# NE-A1 methodology", "",
        "## Corpus and baseline", "",
        f"- NE-5B base: `{NE_ANCESTRY['NE-5B']}`; known NE-1 through NE-5B hashes are recorded in `methodology-validation.json`.",
        f"- CKL source: validated committed JSON under `framework/canonical_library/objects/`; manifest declares {validation['ckl_manifest_object_count']} objects and loader validated {validation['ckl_object_count']}.",
        f"- Canonical chapter identity: committed ASV `books[].chapters[]`, cross-checked against `bhf_agent.references.BOOKS` (66 names; 1,189 chapters).", "",
        "## Census algorithm", "",
        "1. Load `CanonicalLibrary` once. Use its normalized Scripture book index and parsed per-object reference spans to construct candidate object IDs for all chapters. Candidate matching uses the repository's `scripture_reference_overlaps` semantics and the same retrieval status filters (`include_placeholders=True`, deprecated/rejected excluded).",
        "2. Pass each chapter's candidate objects to `project_narrative_explorer` with a complete CKL lookup. The projector applies the existing broad-anchor and semantic-misanchor rules, parent/child distinction, NE-5A section taxonomy, source hydration, and CKL relationship projection.",
        "3. Count projected parents, claims, evidence items, and interpretive notes separately. Passage-specific coverage requires a projected claim or evidence item whose source ID resolves to a parent bibliography entry with a title and at least one author/publisher/year/locator/URL field. Object counts alone do not qualify.",
        "4. Check CKL references against the canonical book/chapter/verse bounds. Read existing map and archaeology link tables using SQLite URI `mode=ro` plus `PRAGMA query_only=ON`; validate targets and bounds, then associate valid rows with chapters by overlap. These are explicit link inventory counts, not complete resolver results.",
        "5. Run a seeded cross-canon sample through standard CKL Scripture retrieval and the normal `NarrativeExplorerService.build` path. Compare candidate IDs, projected CKL item IDs, section assignment, and CKL connection IDs for every selected chapter. Run full resolver-backed builds only for the seven pilots plus one seeded chapter per stratum; record map/archaeology IDs and states separately.", "",
        "## Coverage definitions", "",
        "- `passage_specific_evidence`: complete CKL lookup and at least one directly projected claim or evidence item with resolvable source details.",
        "- `contextual_coverage`: CKL items are projected, but no source-grounded claim/evidence item meets the definition above.",
        "- `entity_only_coverage`: only eligible parent entities of type person, people-group, place, or event are represented.",
        "- `no_eligible_ckl_material`: completed CKL retrieval/projection returned no eligible item for that chapter.",
        "- `incomplete_or_unknown`: retrieval/index coverage or an unparseable/out-of-canon anchor associated with a book prevents a conclusive chapter judgment.",
        "- Map/archaeology full API resolution is `unknown_not_run` outside the sample. An empty explicit-link table is not a claim that no relevant evidence exists.", "",
        "## Assumptions and limits", "",
        "- CKL source anchors are parsed with BHF's canonical Scripture parser; no generic keyword classification is used for the cosmic-geography section.",
        "- The exact NE-5A special cosmic rules are left unchanged. A physical location, general presence/temple/mountain theme, or generic worldview-concept does not gain a cosmic label by this audit.",
        "- Source bibliography resolution is reported by resolvable source ID and a stricter title-plus-author/publisher/year/locator/URL check; passage-specific category requires the stricter traceability check.",
        "- Physical coordinates and geometry are never generated. Stored coordinates do not establish site identification.",
        "- Topic trails use explicit stable IDs and authored relationship edges only. Shared terms do not create an intertextual relationship.",
        "- Dynamic map text matches, archaeological text-first matches, and empty resolver results are exact only for the sampled live builds; other per-chapter resolver states remain unknown.",
        "- Run: `python3 scripts/audit_narrative_explorer_coverage.py --output-dir docs/narrative-explorer/coverage-audit`.",
    ]
    _write_markdown(output_dir / "02-methodology.md", "\n".join(method))

    book_headers = [
        "| Book | Testament | Genre | Stratum | Chapters | Passage-specific | Contextual | Entity-only | No eligible CKL | Unknown | CKL items | Sourced children | Map place links | Archaeology links |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for entry in book_findings:
        book_headers.append(
            "| {book} | {testament} | {genre} | {stratum} | {chapter_denominator} | {passage_specific_chapters} | {contextual_chapters} | {entity_only_chapters} | {no_eligible_ckl_chapters} | {unknown_chapters} | {eligible_item_total} | {source_grounded_children_total} | {chapter_map_place_links} | {chapter_archaeology_links} |".format(
                **{**entry, "genre": entry["bible_genre"]}
            )
        )
    _write_markdown(output_dir / "03-book-level-findings.md", "# Book-level coverage findings\n\nEach row uses chapter denominator from the canonical BHF/ASV inventory. CKL items are summed chapter projections; one object may appear in multiple chapters. Map and archaeology counts are explicit link rows, not complete resolver results.\n\n" + "\n".join(book_headers))

    domain_lines = [
        "# Evidence-domain findings", "",
        "## CKL context and evidence types", "",
        f"- Eligible cultural-background parent records across chapter projections: {sum(int(row['cultural_background_parent_count']) for row in rows)}.",
        f"- Passage-anchored historical/cultural claims: {sum(int(row['historical_context_claim_count']) for row in rows)}; historical/ANE/Second Temple notes: {sum(int(row['historical_context_note_count']) for row in rows)}.",
        f"- CKL archaeology parent projections: {sum(int(row['ckl_archaeology_parent_count']) for row in rows)} across {sum(int(row['ckl_archaeology_parent_count']) > 0 for row in rows)} chapters; typed artifact/site/inscription/material-culture evidence items: {sum(int(row['ckl_archaeology_evidence_item_count']) for row in rows)} across {sum(int(row['ckl_archaeology_evidence_item_count']) > 0 for row in rows)} chapters; unanchored CKL archaeology evidence items: {source_audit['archaeological_evidence_items_without_valid_passage_anchor_count']}.",
        f"- Ancient-text/manuscript/primary-source CKL evidence items: {sum(int(row['ckl_ancient_text_or_manuscript_evidence_item_count']) for row in rows)} across {sum(int(row['ckl_ancient_text_or_manuscript_evidence_item_count']) > 0 for row in rows)} chapters. These are literature/manuscript evidence classifications and do not automatically represent archaeological sites.", "",
        "## Archaeology service", "",
        f"- Inventory items: {domain_metrics.get('inventory_item_counts', {}).get('archaeology_service', 0)}; items with valid passage links: {domain_metrics.get('targets_with_valid_passage_link_counts', {}).get('archaeology_service', 0)}; items without one: {domain_metrics.get('items_without_valid_passage_link_counts', {}).get('archaeology_service', 0)}.",
        f"- Explicit passage-link rows: {domain_metrics.get('reference_rows', {}).get('archaeology_service', 0)}; valid references: {domain_metrics.get('valid_reference_rows', {}).get('archaeology_service', 0)}; invalid references: {domain_metrics.get('invalid_reference_rows', {}).get('archaeology_service', 0)}; broken targets: {domain_metrics.get('broken_target_rows', {}).get('archaeology_service', 0)}.",
        f"- Manuscript service is separate: {domain_metrics.get('inventory_item_counts', {}).get('manuscript_service', 0)} items, {domain_metrics.get('targets_with_valid_passage_link_counts', {}).get('manuscript_service', 0)} with valid passage links, {domain_metrics.get('items_without_valid_passage_link_counts', {}).get('manuscript_service', 0)} without.",
        f"- Chapters with at least one explicit archaeology-service link: {sum(int(row.get('archaeology_service_explicit_link_count', 0)) > 0 for row in rows)}.",
        "- A zero link count means no matching explicit row in this service index; it does not prove that no relevant historical or archaeological evidence exists.", "",
        "## Physical geography", "",
        f"- Place catalog: {domain_metrics.get('inventory_item_counts', {}).get('map_places', 0)} items; {domain_metrics.get('targets_with_valid_passage_link_counts', {}).get('map_places', 0)} have valid passage associations and {domain_metrics.get('items_without_valid_passage_link_counts', {}).get('map_places', 0)} do not. Passage-linked place rows: {domain_metrics.get('reference_rows', {}).get('map_places', 0)} across {sum(int(row.get('map_place_explicit_link_count', 0)) > 0 for row in rows)} chapters; route links: {domain_metrics.get('reference_rows', {}).get('map_routes', 0)}; territorial/political links: {domain_metrics.get('reference_rows', {}).get('map_territories', 0)}.",
        f"- Place-catalog confidence rows labeled unknown/low/disputed: {sum(domain_metrics.get('map_place_low_or_unknown_catalog_confidence_counts', {}).values())}. This is the catalog's general confidence field, not a separate site-identification judgment.",
        f"- CKL place objects with unknown/uncertain identification status: {sum(int(row.get('ckl_unknown_or_uncertain_place_identification_count', 0)) for row in rows)} chapter placements; this is separate from coordinate presence and general map-catalog confidence.",
        f"- Static map feature passage links: {domain_metrics.get('static_map_feature_passage_link_total', 0)} across committed map layer JSON; the NE service map lookup reads linked place/route repositories and does not query those static layer files.",
        "- Missing destinations and invalid anchors are recorded per source table in the validation JSON. CKL identification metadata and general map-catalog confidence are separate; stored coordinates do not establish identification.", "",
        "## Cosmic geography", "",
        f"- CKL cosmic-section item projections: {sum(int(row['cosmic_geography_ckl_item_count']) for row in rows)} across {sum(int(row['cosmic_geography_ckl_item_count']) > 0 for row in rows)} chapters, under the unmodified NE-5A special evidence rules.",
        f"- Current map records use physical place/route categories; explicit typed sacred-space map links found in the sampled service outputs: {validation.get('live_api_sacred_space_map_item_count', 0)}.",
        "- The current SQLite place/route link schema has no authored `geography_kind` field. General mountain, temple, presence, kingship, sea, or wilderness references were not promoted to cosmic geography.",
        "- Exact cosmic-section item IDs are in `cosmic_geography_ckl_item_ids_json` by chapter in the CSV; cross-canonical topic anchors are in `06-narrative-trails.md` and the topic inventory in validation JSON.", "",
        "## Narrative Explorer sections and retrieval", "",
    ]
    for section, column in SECTION_COLUMNS.items():
        domain_lines.append(f"- `{section}`: {sum(int(row[column]) for row in rows)} CKL projected item-chapter placements.")
    domain_lines.extend([
        f"- Projected CKL items with no current section assignment: {sum(int(row['unclassified_ckl_item_count']) for row in rows)} placements.",
        f"- CKL object relationships: {relationships['authored_object_relationship_count']} authored relationships; {relationships['uncategorized_legacy_relationship_count']} map to `uncategorized` under the current projection taxonomy; {relationships['explicit_passage_graph_edge_count']} explicit passage graph edges; {relationships['book_level_related_object_count_excluded_from_ne_projection']} book-level edges are excluded from NE projection.",
        f"- Projected relationship placements: {sum(int(row['direct_connection_count']) for row in rows)} direct and {sum(int(row['inferred_connection_count']) for row in rows)} inferred; placements repeat an edge across applicable chapters. In the underlying object graph, {relationships['genuinely_reciprocal_object_relationship_pairs']} relationship pairs are genuinely reciprocal and {relationships['one_way_object_relationship_count']} edges are one-way.",
        f"- Source IDs in the global inventory: {source_audit['unique_source_ids']}; unresolved child source references: {len(source_audit['missing_source_id_references'])}; weak bibliography references: {len(source_audit['poor_bibliography_references'])}; unresolved passage anchors: {len(validation['invalid_or_unresolved_ckl_anchors'])}.",
        "- The sample identifies records present in explicit-link tables but absent from normal text-first API results. Acts 7 has one explicit place link (`openbible-a012705`) absent from the sampled live map output. Unqueried map and archaeology API results remain unknown, not empty.",
        "",
        "## Provenance and content review", "",
        f"- Source records: {source_audit['source_record_count']} records and {source_audit['unique_source_ids']} distinct IDs; {source_audit['child_source_reference_count']} child source references, {source_audit['resolved_child_source_reference_count']} resolving to a parent bibliography entry, and {source_audit['unresolved_child_source_reference_count']} unresolved. The two unresolved IDs (`harland-associations`, `glancy-slavery`) occur on one interpretive note with no note-level Scripture anchor, so it has no eligible chapter placement.",
        f"- Records without a valid explicit passage association: {source_audit['archaeological_evidence_items_without_valid_passage_anchor_count']} archaeological evidence items, {source_audit['ancient_text_or_manuscript_evidence_items_without_valid_passage_anchor_count']} ancient-text/manuscript items, and {source_audit['historical_cultural_claims_without_valid_passage_anchor_count']} historical/cultural claims. Stable IDs and per-record anchor states are in validation JSON.",
        f"- Across projected chapter-item placements: {totals['projected_item_placement_quality_counts']['missing_review_metadata']} lack review metadata; {totals['projected_item_placement_quality_counts']['certainty_missing']} lack certainty metadata; {totals['projected_item_placement_quality_counts']['dispute_metadata_missing']} lack dispute metadata; {totals['projected_item_placement_quality_counts']['human_review_required']} require human review; {totals['projected_item_placement_quality_counts']['explicitly_disputed']} are explicitly disputed and {totals['projected_item_placement_quality_counts']['explicitly_uncertain']} explicitly marked plausible, speculative, or insufficiently evidenced. A further {totals['projected_item_placement_quality_counts']['interpretation_state_unknown_or_unestablished']} have unknown or unestablished interpretation state.",
        "- These are chapter-placement totals, so one CKL item can appear in more than one chapter. The CSV has chapter-local source and review fields.",
    ])
    _write_markdown(output_dir / "04-evidence-domain-findings.md", "\n".join(domain_lines))

    gap_lines = [
        "# Prioritized gaps and recommended work", "",
        "Priority is an editorial recommendation based on reader impact, existing source availability, reuse across passages, and severity of a broken link. It is not a numeric certainty score.", "",
        "## A. Retrieval and projection", "",
        f"1. **Expose already-anchored but unclassified CKL items.** {sum(int(row['unclassified_ckl_item_count']) for row in rows)} projected item placements have no NE section. Audit the concrete IDs in `chapter-census.csv` before changing policy; keep NE-5A safeguards in force.",
        f"2. **Map authored relationships to supported projection types.** All {relationships['authored_object_relationship_count']} authored object relationships currently map to `uncategorized`; review the label-to-type mapping and add examples for supported relationship kinds without inventing new edges.",
        "3. **Investigate the sampled Acts 7 map miss.** The explicit place link `openbible-a012705` was not returned by the live map resolver; trace the resolver's text-first filtering and fallback before changing display behavior.",
        f"4. **Review broad parent anchors.** {totals['chapters_with_broad_parent_scope_exclusions']} chapters have broad-scope parent anchors excluded by the projector; {totals['chapters_with_book_level_anchors']} chapters contain unscoped book-level anchors and {totals['chapters_with_multi_chapter_anchors']} contain multi-chapter anchors. The multi-chapter count is a scope inventory, not a quota or demonstrated failure.",
        f"5. **Review semantic-misanchor suppression.** Current guard suppresses matching authored anchors in {totals['chapters_with_semantic_misanchor_suppression']} chapters. Preserve negative controls; fix only proven authoring or scope errors.",
        "6. **Connect political-context/territory links to the Narrative Explorer map lookup if desired.** The current NE provider calls place and route resolvers; it does not query the existing `political_context_references` repository. Keep these results distinct from physical place identification.", "",
        "## B. Relationship curation", "",
        f"1. Resolve {relationships['missing_destination_count']} authored relationships with missing destinations; preserve rationale and target identity.",
        f"2. Review the rationale and scope of one-way object edges ({relationships['one_way_object_relationship_count']}); {relationships['genuinely_reciprocal_object_relationship_pairs']} reciprocal pairs are present and {relationships['duplicate_object_relationship_count']} exact duplicate entries were found.",
        "3. Preserve passage-specific anchors and their relationship types while curating cross-book trails. The trail audit lists where CKL has objects but no authored traversable object-to-object relationship.", "",
        "## C. Genuine CKL evidence gaps", "",
        f"- {totals['chapters_with_no_eligible_ckl_material']} chapters currently have no passage-eligible CKL item under NE-5A rules. Treat this as an inventory gap only; commission research where the narrative and available scholarship justify it, not to meet a chapter quota.",
        "- Use the pilot and stratified cases to identify high-value episodes where source material already exists but CKL lacks an explicit, supported passage link. Add evidence only in a future, separately reviewed CKL curation transaction.",
        "- Do not count ancient literary comparisons as archaeology records or infer physical site identification from coordinates.", "",
        "## D. Provenance and review", "",
        f"- Resolve {len(source_audit['missing_source_id_references'])} child citations whose source ID is absent from the parent source list. Both occur on the same interpretive note without a note-level Scripture anchor; add bibliography entries and anchor scope only if its applicability is supported.",
        f"- Harden {len(source_audit['poor_bibliography_references'])} source references lacking a title plus author/publisher/year/locator/URL detail.",
        "- Target eligible records missing certainty, dispute, review, or human-review metadata before expanding their section reach. Uncertainty belongs with disputed evidence rather than being hidden.", "",
        "## E. Domain completeness uncertainty", "",
        "- The all-chapter map and archaeology service outputs were not requested 1,189 times. Explicit link tables are fully enumerated; text-first resolver results are established only for the validation sample. Keep all other API result states unknown.",
        "- A passage with zero archaeological link rows is not a verified absence of relevant historical evidence. Research and source-aware linkage are separate next steps.",
        "- The map link tables establish a linked-record inventory, not whether a stored physical identification is accepted or certain.",
    ]
    _write_markdown(output_dir / "05-prioritized-gaps.md", "\n".join(gap_lines))

    trail_lines = [
        "# Existing cross-canonical narrative trails", "",
        "The inventory below starts from exact CKL object IDs listed in the audit script. Genesis, Joshua, and Acts book objects are narrowed to named passage records where a motif-specific allowlist is given. A traversable edge exists only when CKL authors a relationship with a resolvable destination; no edge is inferred from shared topics. Reported gaps are limited to this explicit seed set and do not prove that related material is absent elsewhere in CKL.", "",
        "| Narrative thread | Present seed objects | Explicitly anchored records | Traceable sourced claims/evidence | Direct authored links among seed objects | Current trail state |",
        "|---|---:|---:|---:|---:|",
    ]
    for topic, details in themes["topics"].items():
        trail_lines.append(
            f"| {topic} | {len(details['seed_object_ids'])} | {details['anchored_record_count']} | {details['source_backed_record_count']} | {details['authored_connection_count']} | {details['topic_trail_state']} |"
        )
    for topic, details in themes["topics"].items():
        trail_lines.extend(["", f"## {topic}", ""])
        trail_lines.append("Objects: " + (", ".join(f"`{value}`" for value in details["seed_object_ids"]) or "none in current CKL"))
        trail_lines.append("Anchors: " + (", ".join(f"`{value}`" for value in details["explicit_passage_anchors"][:24]) or "none among selected authored records"))
        if len(details["explicit_passage_anchors"]) > 24:
            trail_lines.append(f"Additional explicit anchors: {len(details['explicit_passage_anchors']) - 24} (see validation JSON).")
        source_record_ids = details["source_backed_claim_or_evidence_record_ids"]
        trail_lines.append("Traceable source-backed claim/evidence IDs: " + (", ".join(f"`{value}`" for value in source_record_ids[:20]) or "none in selected records"))
        if len(source_record_ids) > 20:
            trail_lines.append(f"Additional source-backed claim/evidence IDs: {len(source_record_ids) - 20} (see validation JSON).")
        if details["within_seed_inventory_gap_flags"]:
            trail_lines.append("Observed gaps within this seed inventory: " + ", ".join(details["within_seed_inventory_gap_flags"]))
        if details["authored_traversable_connections"]:
            trail_lines.append("Traversable authored links: " + "; ".join(f"`{edge['source_id']}` —{edge['relationship'] or 'uncategorized'}→ `{edge['target_id']}`" for edge in details["authored_traversable_connections"]))
        else:
            trail_lines.append("Traversable authored links: none between the selected seed objects; any cross-book navigation remains limited to the objects' explicit passage anchors or links to other objects outside this seed set.")
        if details["missing_seed_object_ids"]:
            trail_lines.append("Missing expected seed IDs: " + ", ".join(f"`{value}`" for value in details["missing_seed_object_ids"]))
        if details["seed_objects_without_anchored_records"]:
            trail_lines.append("Seed objects without an explicit Scripture-anchored record in this inventory: " + ", ".join(f"`{value}`" for value in details["seed_objects_without_anchored_records"]))
    _write_markdown(output_dir / "06-narrative-trails.md", "\n".join(trail_lines))


def run_audit(output_dir: Path, study_db_path: Path, repo_root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    print("[ne-a1] checking read-only database snapshots", file=sys.stderr, flush=True)
    db_before = _database_marker(study_db_path)
    study_integrity_before = _read_only_db_integrity(study_db_path)
    ckl_db_path = repo_root / ".bhf" / "ckl.sqlite"
    ckl_integrity_before = _read_only_db_integrity(ckl_db_path)
    bible = load_asv_bible()
    chapters = load_chapters(bible)
    library = CanonicalLibrary.load_default()
    print(f"[ne-a1] loaded {len(library.objects_by_id)} CKL objects; indexing chapter candidates", file=sys.stderr, flush=True)
    fingerprint = library.inventory_fingerprint()
    if len(library.objects_by_id) != int(library.manifest.get("object_count", -1)):
        raise ValueError("validated CKL object count disagrees with manifest")
    candidate_index = build_candidate_index(library, chapters)
    print("[ne-a1] building one-pass anchor applicability audit", file=sys.stderr, flush=True)
    anchor_audit_index = build_anchor_audit_index(library, chapters)
    chapter_verse_counts = _chapter_verse_counts(chapters)
    invalid_by_chapter, invalid_anchors = _invalid_anchor_details(library, chapters, chapter_verse_counts)
    external_snapshot = _read_only_sqlite_snapshot(study_db_path, bible)
    static_maps = _static_map_feature_links(chapters, repo_root)
    if external_snapshot.get("status") == "complete":
        external_snapshot["metrics"]["static_map_feature_passage_link_total"] = sum(len(values) for values in static_maps.get("by_chapter", {}).values())
        external_snapshot["metrics"]["static_map_feature_files"] = len(list((repo_root / "bhf_web" / "static" / "data" / "mapLayers").glob("*.json")))
        external_snapshot["metrics"]["static_map_invalid_reference_count"] = len(static_maps.get("invalid", []))
    rows: list[dict[str, Any]] = []
    projections: dict[str, Any] = {}
    rows_by_ref: dict[str, dict[str, Any]] = {}
    for chapter_number, chapter in enumerate(chapters, start=1):
        reference = str(chapter["reference"])
        external_links = external_snapshot.get("links_by_chapter", {}).get(reference, [])
        static_links = static_maps.get("by_chapter", {}).get(reference, [])
        row, projection = _chapter_census_row(
            chapter,
            candidate_index[reference],
            anchor_audit_index[reference],
            library,
            unresolved_anchor_count=invalid_by_chapter.get(reference, 0),
        )
        if external_snapshot.get("status") == "complete":
            _attach_external_counts(row, external_links, static_links)
        else:
            row.update({
                "map_place_explicit_link_count": "unknown",
                "map_place_resolvable_link_count": "unknown",
                "map_route_explicit_link_count": "unknown",
                "map_route_resolvable_link_count": "unknown",
                "map_territory_explicit_link_count": "unknown",
                "map_territory_resolvable_link_count": "unknown",
        "map_place_low_or_unknown_catalog_confidence_link_count": "unknown",
                "archaeology_service_explicit_link_count": "unknown",
                "archaeology_service_resolvable_link_count": "unknown",
                "manuscript_service_explicit_link_count": "unknown",
                "static_map_feature_passage_link_count": "unknown",
                "static_map_feature_ids_json": "[]",
                "external_explicit_link_state": external_snapshot.get("status", "unknown"),
            })
        row["lookup_unresolved_anchor_count"] = invalid_by_chapter.get(reference, 0)
        row["ckl_lookup_status"] = "partial" if invalid_by_chapter.get(reference, 0) else "complete"
        row["coverage_category"] = coverage_category(
            [item for item in projection.items if item.domain == "ckl"],
            lookup_status=row["ckl_lookup_status"],
        )
        row["_candidate_ids"] = candidate_index[reference]
        row["_external_links"] = external_links
        rows.append(row)
        rows_by_ref[reference] = row
        projections[reference] = projection
        if chapter_number % 200 == 0:
            print(f"[ne-a1] projected {chapter_number}/{len(chapters)} chapters", file=sys.stderr, flush=True)

    sample_reasons = _sample_reasons(rows)
    stratified_references = {
        str(chapter["reference"])
        for chapter in select_stratified_sample(chapters, seed=SAMPLE_SEED, per_stratum=1)
    }
    live_api_references = set(PILOT_REFERENCES) | stratified_references
    print(f"[ne-a1] validating {len(sample_reasons)} deterministic sample chapters against retrieval/projection; running {len(live_api_references)} targeted service builds", file=sys.stderr, flush=True)
    sample_checks = _validate_sample(chapters, rows_by_ref, projections, library, sample_reasons, study_db_path, live_api_references)
    for row in rows:
        row.pop("_candidate_ids", None)
        row.pop("_external_links", None)
    relationship_audit = _relationship_audit(library)
    source_audit = _source_id_audit(library, chapter_verse_counts)
    _attach_unresolved_source_ids(rows, source_audit)
    themes = _theme_inventory(library)
    print("[ne-a1] writing audit artifacts", file=sys.stderr, flush=True)
    book_findings = _book_findings(rows)
    totals = _data_quality_summary(rows, library, relationship_audit, source_audit)
    study_integrity_after = _read_only_db_integrity(study_db_path)
    ckl_integrity_after = _read_only_db_integrity(ckl_db_path)
    db_after = _database_marker(study_db_path)
    elapsed = round(time.perf_counter() - started, 3)
    peak_rss_kib = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    study_marker_unchanged = db_before == db_after
    all_candidate_checks_pass = all(check["candidate_index_matches_normal_retrieval"] and check["projector_ckl_signature_matches_normal_retrieval"] for check in sample_checks)
    live_api_sample_checks = [check for check in sample_checks if check.get("live_api_sampled")]
    live_api_checks_pass = bool(live_api_sample_checks) and all(
        check.get("live_api_status") == "complete" and check.get("live_api_ckl_projection_matches_census", False)
        for check in live_api_sample_checks
    )
    known_hashes_exist = all(_git_output(repo_root, "cat-file", "-t", commit) == "commit" for commit in NE_ANCESTRY.values())
    base_commit = _git_output(repo_root, "rev-parse", "HEAD")
    ancestry_verified = bool(base_commit and all(
        subprocess.run(["git", "merge-base", "--is-ancestor", commit, base_commit], cwd=repo_root, check=False, capture_output=True).returncode == 0
        for commit in NE_ANCESTRY.values()
    ))
    chapter_identities = [(str(row["book"]), int(row["chapter"])) for row in rows]
    section_counts: dict[str, int] = {section: sum(int(row[SECTION_COLUMNS[section]]) for row in rows) for section in SECTION_IDS}
    live_api_sacred_space_count = sum(
        kind == "sacred_space"
        for check in sample_checks
        for kind in check.get("live_api_map_geography_kinds", [])
    )
    sample_reasons_present = {reason for reasons in sample_reasons.values() for reason in reasons}
    required_case_reasons = (
        "sparse_ckl_case", "dense_ckl_case", "book_level_anchor_case", "multi_chapter_anchor_case", "verse_scoped_case",
        "unknown_or_uncertain_physical_identity_case",
    )
    sample_case_inventory = {
        reason: next((reference for reference, reasons in sample_reasons.items() if reason in reasons), None)
        for reason in required_case_reasons
    }
    chapter_by_ref = {str(chapter["reference"]): chapter for chapter in chapters}
    sampled_strata = sorted({str(chapter_by_ref[reference]["stratum"]) for reference in sample_reasons})
    validation = {
        "audit_version": AUDIT_VERSION,
        "baseline_commit": base_commit,
        "branch": _git_output(repo_root, "branch", "--show-current"),
        "ne_ancestry": NE_ANCESTRY,
        "ne_ancestry_hashes_exist": known_hashes_exist,
        "ne_ancestry_is_ancestor_of_baseline": ancestry_verified,
        "master_contains_ne5b_at_audit_time": bool(subprocess.run(["git", "merge-base", "--is-ancestor", NE_ANCESTRY["NE-5B"], "origin/master"], cwd=repo_root, check=False, capture_output=True).returncode == 0) if _git_output(repo_root, "rev-parse", "--verify", "origin/master") else None,
        "ckl_object_count": len(library.objects_by_id),
        "ckl_manifest_object_count": int(library.manifest.get("object_count", 0)),
        "ckl_manifest_categories": library.manifest.get("categories", {}),
        "ckl_inventory_fingerprint": fingerprint,
        "canonical_book_count": len({row["book"] for row in chapters}),
        "chapter_row_count": len(rows),
        "unique_chapter_identity_count": len(set(chapter_identities)),
        "chapter_identity_order_sha256": hashlib.sha256("\n".join(f"{book}|{chapter}" for book, chapter in chapter_identities).encode()).hexdigest(),
        "chapter_total_matches_expected": len(rows) == EXPECTED_CHAPTERS,
        "validation_status": "pass" if len(rows) == EXPECTED_CHAPTERS and len(set(chapter_identities)) == EXPECTED_CHAPTERS and known_hashes_exist and ancestry_verified and all_candidate_checks_pass and live_api_checks_pass and len(sampled_strata) == 9 and study_marker_unchanged and study_integrity_before.get("integrity_check") == "ok" and study_integrity_after.get("integrity_check") == "ok" and ckl_integrity_before.get("integrity_check") == "ok" and ckl_integrity_after.get("integrity_check") == "ok" and external_snapshot.get("status") == "complete" else "blocked_or_mismatch",
        "sample_seed": SAMPLE_SEED,
        "sample_method": "One chapter per canonical stratum selected by Python random.Random(seed), plus all seven established pilots and deterministic sparse/dense/book-level/multi-chapter/verse-scope/uncertainty/empty-category edge cases; duplicate chapters merge reason labels. Exact normal-retrieval and projector parity is checked for every selected chapter. Full resolver-backed service builds run only for the seven pilots plus the stratified chapters (overlap deduplicated).",
        "live_api_sample_method": "Seven established pilots plus one seeded chapter per canonical stratum; duplicate references are built once.",
        "live_api_sample_count": len(live_api_sample_checks),
        "established_pilot_requested_labels": list(PILOT_REQUEST_LABELS),
        "established_pilot_canonical_references": list(PILOT_REFERENCES),
        "sample_checks": sample_checks,
        "sample_strata": sampled_strata,
        "sample_strata_coverage_complete": len(sampled_strata) == 9,
        "required_case_samples": sample_case_inventory,
        "required_case_samples_found": {reason: reason in sample_reasons_present for reason in required_case_reasons},
        "candidate_index_matches_normal_retrieval": all_candidate_checks_pass,
        "live_api_ckl_projection_matches_census": live_api_checks_pass,
        "live_api_sacred_space_map_item_count": live_api_sacred_space_count,
        "study_db": {
            "path": str(study_db_path),
            "snapshot_status": external_snapshot.get("status"),
            "snapshot_metrics": external_snapshot.get("metrics", {}),
            "integrity_before": study_integrity_before,
            "integrity_after": study_integrity_after,
            "marker_before": db_before,
            "marker_after": db_after,
            "marker_unchanged": study_marker_unchanged,
        },
        "ckl_sqlite_index": {
            "path": str(ckl_db_path),
            "integrity_before": ckl_integrity_before,
            "integrity_after": ckl_integrity_after,
            "verified_integrity": ckl_integrity_before.get("integrity_check") == "ok" and ckl_integrity_after.get("integrity_check") == "ok",
        },
        "invalid_or_unresolved_ckl_anchors": invalid_anchors,
        "static_map_invalid_anchors": static_maps.get("invalid", []),
        "section_ckl_item_chapter_placements": section_counts,
        "reproduction": {
            "python_version": sys.version.split()[0],
            "resource_peak_rss_kib": peak_rss_kib,
            "runtime_seconds": elapsed,
            "runtime_scope": "whole audit runner, including library load, 1,189 CKL projections, read-only link census, deterministic sample API builds, graph/source checks, and output serialization",
        },
    }
    external_snapshot.get("metrics", {}).update({
        "static_map_feature_passage_link_total": sum(int(row.get("static_map_feature_passage_link_count", 0) or 0) for row in rows if str(row.get("static_map_feature_passage_link_count", "")).isdigit()),
    })
    validation["study_db"]["snapshot_metrics"] = external_snapshot.get("metrics", {})
    validation["totals"] = totals
    validation["relationships"] = relationship_audit
    validation["sources"] = source_audit
    validation["narrative_topics"] = themes
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "chapter-census.csv", rows)
    _write_json(output_dir / "methodology-validation.json", validation)
    _collect_docs(
        output_dir,
        rows=rows,
        book_findings=book_findings,
        totals=totals,
        domain_metrics=external_snapshot.get("metrics", {}),
        relationships=relationship_audit,
        source_audit=source_audit,
        themes=themes,
        validation=validation,
    )
    return validation


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/narrative-explorer/coverage-audit"))
    parser.add_argument("--study-db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    validation = run_audit(args.output_dir, args.study_db, args.repo_root)
    print(json.dumps({
        "validation_status": validation["validation_status"],
        "chapter_rows": validation["chapter_row_count"],
        "ckl_objects": validation["ckl_object_count"],
        "sample_checks": len(validation["sample_checks"]),
        "runtime_seconds": validation["reproduction"]["runtime_seconds"],
        "peak_rss_kib": validation["reproduction"]["resource_peak_rss_kib"],
    }, sort_keys=True))
    return 0 if validation["validation_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
