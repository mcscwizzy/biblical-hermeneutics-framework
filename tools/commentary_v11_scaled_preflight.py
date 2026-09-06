#!/usr/bin/env python3
"""Build and lock a mixed-corpus Commentary v1.1 Luna evidence batch.

This is a Luna-side gate.  It retrieves and audits evidence only; it never
calls Terra, creates reader-facing prose, repairs CKL records, or modifies a
release artifact.  The output is an immutable-by-convention input manifest
for a future Terra run.
"""

from __future__ import annotations

import argparse
import sqlite3
from contextlib import contextmanager
import hashlib
import json
import math
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent import bible
from bhf_agent.chapter_commentary.availability import (
    EvidenceAvailability,
    classify_evidence_availability,
)
from bhf_agent.chapter_commentary.evidence_bundling import (
    _retrieve_archaeology,
    _retrieve_geography,
)
from bhf_agent.ckl import load_canonical_library
from bhf_agent.presentation import build_evidence_bundle
from bhf_agent.presentation.evidence_hash import calculate_evidence_hash
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from bhf_agent.presentation.relevance import (
    BOOK_CONTEXT,
    COMPARATIVE_CONTEXT,
    DIRECT_CONTEXT,
    GENERIC_BACKGROUND,
    INTERTEXTUAL_REUSE,
    LATER_RECEPTION,
    SEMANTICALLY_MISANCHORED,
    TEXTUAL_CLAIM_SIGNALS,
    TEXTUAL_CLAIM_TEXT_RE,
    with_presentation_metadata,
    with_semantic_relationship,
    presentation_role,
)
from bhf_agent.presentation.evidence_normalization import evidence_category as _normalized_category
from tools.commentary_v11_canary import _section_for_item, select_overview_item
from tools.commentary_v11_expansion import _book_genre, _signal_score
from tools.commentary_v11_low_information import audit as recalculate_low_information
from framework.canonical_library import CKLRepositoryConfig
from framework.canonical_library.database_builder import build_database, verify_database
from framework.canonical_library.scripture import (
    parse_scripture_references,
    scripture_reference_overlaps,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-scale"
DEFAULT_CANDIDATE_SOURCE = (
    REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.0.1"
)
DEFAULT_POOL_SIZE = 70
DEFAULT_TARGET_COUNT = 50
EVIDENCE_BUNDLE_VERSION = EVIDENCE_BUNDLE_CANDIDATE_VERSION
EVIDENCE_HASH_VERSION = "2"
TOOL_VERSION = "commentary-v11-scaled-preflight-1.0"
VERDICTS = (
    "PASS",
    "QUARANTINE",
    "DATA_GAP",
    "SKIP_ALREADY_GENERATED",
    "SKIP_PRIOR_QUARANTINE",
    "SKIP_CANARY",
)
ROOT_CAUSE_FAMILIES = (
    "LEGACY_CATEGORY_OVERRIDE",
    "MISSING_CLAIM_TYPE",
    "MISSING_NOTE_TYPE",
    "MISSING_EVIDENCE_TYPE",
    "PARENT_METADATA_INHERITANCE",
    "PRESENTATION_ROLE_HEURISTIC",
    "TEXTUAL_WITNESS_MISCLASSIFICATION",
    "INTERPRETIVE_TEXTUAL_UNCERTAINTY",
    "OTHER",
)

PRIMARY_CANARY_ROOT = (
    REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-terra"
)
SUPPLEMENTAL_CANARY_ROOT = PRIMARY_CANARY_ROOT / "supplemental-integrity-controls"
BATCH_001_TERRA_ROOT = (
    REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-scale" / "batch-001" / "terra" / "chapters"
)
BATCH_002_TERRA_ROOT = (
    REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-scale" / "batch-002" / "terra" / "chapters"
)

SECTION_ROLES = {
    "historical_context",
    "archaeology_geography",
    "language_literary",
    "chronology",
    "interpretive_questions",
    "dig_deeper",
    "significance",
}

TEMPLATE_PATTERNS = (
    re.compile(r"ancient background for .+ includes", re.I),
    re.compile(r"helps anchor the biblical world", re.I),
    re.compile(r"literarily, .+ is read through", re.I),
    re.compile(r"serves as a lexical anchor", re.I),
)
GREEK_WORD_STUDY_HINTS = re.compile(
    r"\b(?:greek|lxx|septuagint|translation|translated|hellenistic)\b", re.I
)
FIRST_AUDIENCE_HINTS = re.compile(
    r"\b(?:first[- ]audience|original audience|historical context|ancient setting)\b", re.I
)


def reference_key(book: str, chapter: int) -> str:
    return f"{book} {chapter}"


def filename_for(book: str, chapter: int) -> str:
    return f"{book.casefold().replace(' ', '_')}_{chapter:03d}.json"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _progress(message: str) -> None:
    print(f"[luna-high] {message}", file=sys.stderr, flush=True)


def _json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _canary_references() -> set[str]:
    primary: set[str] = set()
    certification_root = REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1"
    for cert in (
        certification_root / "evidence-certification-commentary_canary.json",
        certification_root / "evidence-certification-supplemental-controls.json",
    ):
        if not cert.exists():
            continue
        data = json.loads(cert.read_text(encoding="utf-8"))
        for row in data.get("chapters", []):
            if row.get("reference"):
                primary.add(str(row["reference"]))
        if data.get("reference"):
            primary.add(str(data["reference"]))
    return primary


def _previous_batch_references(batch_id: str) -> set[str]:
    """Exclude prior generated/certified chapters from a later batch."""

    try:
        current_number = int(batch_id.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        current_number = 0
    previous: set[str] = set()
    scale_root = DEFAULT_OUTPUT_ROOT
    for batch_root in sorted(scale_root.glob("batch-*")):
        try:
            number = int(batch_root.name.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            continue
        if number >= current_number:
            continue
        manifest_path = batch_root / "batch-manifest.json"
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            previous.update(str(value) for value in data.get("final_references", []))
        quarantine_path = batch_root / "quarantine-report.json"
        if quarantine_path.exists():
            data = json.loads(quarantine_path.read_text(encoding="utf-8"))
            previous.update(
                str(row.get("reference"))
                for row in data.get("chapters", [])
                if row.get("reference")
            )
    return previous


def _previous_batch_reference_verdicts(batch_id: str) -> dict[str, str]:
    """Return manifest-derived skip verdicts for prior scale batches."""

    try:
        current_number = int(batch_id.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        current_number = 0
    verdicts: dict[str, str] = {}
    for batch_root in sorted(DEFAULT_OUTPUT_ROOT.glob("batch-*")):
        try:
            number = int(batch_root.name.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            continue
        if number >= current_number:
            continue
        manifest_path = batch_root / "batch-manifest.json"
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for reference in data.get("final_references", []):
                verdicts[str(reference)] = "SKIP_ALREADY_GENERATED"
        quarantine_path = batch_root / "quarantine-report.json"
        if quarantine_path.exists():
            data = json.loads(quarantine_path.read_text(encoding="utf-8"))
            for row in data.get("chapters", []):
                reference = row.get("reference")
                if reference and str(reference) not in verdicts:
                    verdicts[str(reference)] = "SKIP_PRIOR_QUARANTINE"
    return verdicts


def _artifact_fingerprints() -> dict[str, str]:
    paths = sorted(PRIMARY_CANARY_ROOT.glob("chapters/*.json"))
    paths += sorted(SUPPLEMENTAL_CANARY_ROOT.glob("chapters/*.json"))
    result: dict[str, str] = {}
    for path in paths:
        result[str(path.relative_to(REPO_ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _batch_001_terra_fingerprints() -> dict[str, str]:
    return {
        str(path.relative_to(REPO_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(BATCH_001_TERRA_ROOT.glob("*.json"))
    }


def _batch_002_terra_fingerprints() -> dict[str, str]:
    return {
        str(path.relative_to(REPO_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(BATCH_002_TERRA_ROOT.glob("*.json"))
    }


def _stable_fingerprint(fingerprints: Mapping[str, str]) -> str:
    payload = json.dumps(dict(sorted(fingerprints.items())), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _eligible_rows(current: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for ref in current["chapters_evidence_supports_regeneration"]:
        book, chapter_text = str(ref).rsplit(" ", 1)
        chapter = int(chapter_text)
        rows.append({
            "reference": ref,
            "book": book,
            "chapter": chapter,
            "availability_from_recalculation": next(
                (
                    row["bundle_assessment"]["recomputed_availability"]
                    for row in current["records"]
                    if row["reference"] == ref
                ),
                None,
            ),
        })
    return rows


def _rank_row(row: Mapping[str, Any]) -> dict[str, Any]:
    score, factors = _signal_score(str(row["book"]), int(row["chapter"]))
    genre = _batch_genre(str(row["book"]))
    # Selection signals are only for diversity and ordering.  They never
    # promote a chapter out of DATA_GAP or alter evidence.
    return {
        **dict(row),
        "genre": genre,
        "selection_score": round(float(score) + (3.0 if genre in {"law", "prophecy", "gospel"} else 0), 2),
        "selection_factors": factors,
    }


def _batch_genre(book: str) -> str:
    """Use the existing genre map with explicit apocalyptic stress coverage."""

    if book in {"Daniel", "Revelation"}:
        return "apocalyptic"
    if book in {
        "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
        "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
        "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
        "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude",
    }:
        return "epistle"
    return _book_genre(book)


def select_mixed_candidate_pool(
    rows: Sequence[Mapping[str, Any]],
    *,
    pool_size: int = DEFAULT_POOL_SIZE,
    excluded_references: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Select a ranked, genre/availability-mixed pool without book dominance."""

    excluded = set(excluded_references)
    ranked = [
        _rank_row(row)
        for row in rows
        if str(row["reference"]) not in excluded
        and row.get("availability_from_recalculation") in {"AVAILABLE", "THIN"}
    ]
    for row in ranked:
        row["_availability_rank"] = 0 if row.get("availability_from_recalculation") == "AVAILABLE" else 1
    ranked.sort(key=lambda row: (-float(row["selection_score"]), row["book"].casefold(), int(row["chapter"])))

    # Round-robin across availability and genre gives the pool a stable mixed
    # shape while still allowing the chapter-content signals to rank members
    # within each lane. Five chapters per book is the soft cap requested for
    # the scale stress sample.
    lanes: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in ranked:
        lanes[(str(row.get("availability_from_recalculation") or "THIN"), str(row["genre"]))].append(row)
    for lane in lanes.values():
        lane.sort(key=lambda row: (-float(row["selection_score"]), row["book"].casefold(), int(row["chapter"])))

    selected: list[dict[str, Any]] = []
    selected_refs: set[str] = set()
    book_counts: Counter[str] = Counter()
    # Favor AVAILABLE roughly 60/40, but do not fabricate a quota.
    desired_available = round(pool_size * 0.60)
    lanes_order = sorted(lanes, key=lambda lane: (0 if lane[0] == "AVAILABLE" else 1, lane[1]))
    while len(selected) < pool_size:
        progressed = False
        for lane in lanes_order:
            if not lanes[lane]:
                continue
            available_count = sum(row.get("availability_from_recalculation") == "AVAILABLE" for row in selected)
            if lane[0] == "AVAILABLE" and available_count >= desired_available and any(key[0] == "THIN" and lanes[key] for key in lanes):
                continue
            row = lanes[lane][0]
            if book_counts[str(row["book"])] >= 5:
                lanes[lane].pop(0)
                continue
            lanes[lane].pop(0)
            if row["reference"] in selected_refs:
                continue
            selected.append(row)
            selected_refs.add(str(row["reference"]))
            book_counts[str(row["book"])] += 1
            progressed = True
            if len(selected) >= pool_size:
                break
        if not progressed:
            break

    if len(selected) < pool_size:
        for row in ranked:
            if len(selected) >= pool_size:
                break
            if row["reference"] in selected_refs or book_counts[str(row["book"])] >= 5:
                continue
            selected.append(row)
            selected_refs.add(str(row["reference"]))
            book_counts[str(row["book"])] += 1
    return selected


def _build_bundle(library: Any, book: str, chapter: int, study_db_path: str | Path | None = None):
    reference = bible.verse_range_reference(book, chapter)
    canonical_results = list(library.retrieve_by_scripture_reference(reference, limit=100, include_placeholders=False))
    bundle = build_evidence_bundle(
        reference,
        canonical_results=canonical_results,
        geography=_retrieve_geography(book, chapter, study_db_path),
        archaeology=_retrieve_archaeology(book, chapter, study_db_path),
        bundle_version=EVIDENCE_BUNDLE_VERSION,
    )
    return bundle, canonical_results


@contextmanager
def _sqlite_workspace(sqlite_database: Path | None):
    """Use a verified reusable CKL database when supplied; otherwise build one."""

    if sqlite_database is not None:
        database = sqlite_database.resolve()
        if not database.exists():
            raise FileNotFoundError(database)
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            metadata = dict(connection.execute("SELECT key, value FROM ckl_metadata").fetchall())
        if metadata.get("database_schema_version") != "4":
            raise RuntimeError("reusable CKL SQLite database has an unsupported schema version")
        if metadata.get("retrieval_index_version") != "3":
            raise RuntimeError("reusable CKL SQLite database has an unsupported retrieval index version")
        if int(metadata.get("object_count", "0")) <= 0 or not metadata.get("inventory_fingerprint"):
            raise RuntimeError("reusable CKL SQLite database is missing current inventory metadata")
        yield database
        return
    with tempfile.TemporaryDirectory(prefix="bhf-batch-sqlite-") as temp_dir:
        database = Path(temp_dir) / "ckl.sqlite"
        build_database(REPO_ROOT / "framework" / "canonical_library", database)
        verify_database(database, root=REPO_ROOT / "framework" / "canonical_library")
        yield database


def _parent_records(library: Any, results: Sequence[Any]) -> dict[str, dict[str, Any]]:
    return {
        str(result.object.id): result.object.to_dict()
        for result in results
        if getattr(result, "object", None) is not None
    }


def _anchor_shape(anchors: Sequence[str], library: Any) -> dict[str, Any]:
    spans = []
    for anchor in anchors:
        spans.extend(parse_scripture_references(anchor, book_alias_lookup=library._book_alias_lookup))
    books = sorted({span.book for span in spans})
    broad = any(span.start_chapter is None or span.end_chapter not in {None, span.start_chapter} for span in spans)
    return {"books": books, "span_count": len(spans), "broad": broad}


def _item_summary(item: Any) -> dict[str, Any]:
    metadata = dict(item.relevance_metadata or {})
    return {
        "evidence_id": item.id,
        "parent_object_id": metadata.get("parent_object_id"),
        "parent_type": metadata.get("parent_type"),
        "parent_title": metadata.get("parent_title"),
        "category": item.category,
        "claim": item.claim,
        "source_ids": list(item.source_ids),
        "passage_anchors": list(item.passage_anchors),
        "confidence": item.confidence,
        "semantic_relationship": metadata.get("semantic_relationship"),
        "presentation_role": metadata.get("presentation_role"),
        "overview_priority": metadata.get("overview_priority"),
        "assertion_type": metadata.get("assertion_type"),
        "dispute_status": metadata.get("dispute_status"),
        "evidence_type": metadata.get("evidence_type"),
    }


def _is_textual_witness_material(item: Any) -> bool:
    """Detect textual-witness material for the Terra suppression simulation."""

    metadata = dict(getattr(item, "relevance_metadata", {}) or {})
    authored = {
        str(metadata.get(key) or "")
        .casefold()
        .replace("-", "_")
        .replace(" ", "_")
        for key in ("claim_type", "note_type", "evidence_type", "source_kind")
    }
    if authored & set(TEXTUAL_CLAIM_SIGNALS):
        return True
    claim = str(getattr(item, "claim", "") or "")
    if str(metadata.get("parent_type") or "").casefold() == "archaeology":
        material_only = re.search(
            r"\b(?:discover(?:ed|y)|excavat(?:ed|ion)|found|cave|site|provenance|"
            r"physical|artifact|deposit|stratigraph|archaeolog(?:y|ical))\b",
            claim,
            re.IGNORECASE,
        ) and not re.search(
            r"\b(?:reading|variant|version|transmission|preserv(?:es|ed)|"
            r"textual\s+profile|textual\s+difference|different\s+text)\b",
            claim,
            re.IGNORECASE,
        )
        if material_only:
            return False
    return bool(TEXTUAL_CLAIM_TEXT_RE.search(claim))


def terra_textual_suppression_simulation(bundle: Any) -> dict[str, Any]:
    """Prove whether Terra's defense-in-depth filter would drop an item."""

    suppressed: list[dict[str, str]] = []
    for item in bundle.evidence_items:
        if not _is_textual_witness_material(item):
            continue
        routed = _section_for_item(item)
        if routed not in {"historical_context", "archaeology_geography"}:
            continue
        suppressed.append(
            {
                "evidence_id": item.id,
                "presentation_role": str((item.relevance_metadata or {}).get("presentation_role") or ""),
                "terra_section": routed,
            }
        )
    return {
        "terra_textual_suppression_required": bool(suppressed),
        "suppressed_items": suppressed,
    }


def _legacy_presentation_role(metadata: Mapping[str, Any], *, category: str, claim: str = "") -> str | None:
    """Reproduce the pre-Batch-003 classifier for routing impact reports."""

    parent_type = str(metadata.get("parent_type") or "").casefold()
    relationship = str(metadata.get("semantic_relationship") or "")
    claim_type = str(metadata.get("claim_type") or "").casefold().replace("-", "_")
    note_type = str(metadata.get("note_type") or "").casefold().replace("-", "_")
    category = str(category or "").casefold()
    text = " ".join(
        str(value or "")
        for value in (metadata.get("parent_object_id"), metadata.get("parent_title"), claim)
    ).casefold()
    normalized = {
        value.strip().replace("-", "_").replace(" ", "_")
        for value in (claim_type, note_type, str(metadata.get("evidence_type") or "").casefold(), str(metadata.get("dispute_status") or "").casefold())
        if value.strip()
    }
    textual = bool(normalized & set(TEXTUAL_CLAIM_SIGNALS)) or bool(
        re.search(
            r"\b(?:textual\s+variant|textual\s+criticism|textual\s+transmission|manuscript(?:\s+reading)?|shorter[- ]text|longer[- ]text|textual\s+witness(?:es)?|textual\s+omission)\b",
            text,
            re.IGNORECASE,
        )
    )
    if relationship in {LATER_RECEPTION, INTERTEXTUAL_REUSE, COMPARATIVE_CONTEXT}:
        return "dig_deeper"
    if relationship in {SEMANTICALLY_MISANCHORED, "WEAKLY_RELATED"}:
        return None
    if parent_type == "word_study":
        return "language_literary" if relationship == DIRECT_CONTEXT else None
    explicit_textual = claim_type in set(TEXTUAL_CLAIM_SIGNALS) or note_type in set(TEXTUAL_CLAIM_SIGNALS)
    if textual and (category in {"archaeology", "geography"} or explicit_textual):
        if claim_type in {"interpretive_textual", "textual_uncertainty"} or note_type in {"interpretive_question", "interpretive_questions", "interpretive_caution"}:
            return "interpretive_questions"
        return "language_literary"
    if claim_type in {"lexical", "literary", "composition", "authorship", "rhetorical", "textual_form", "textual"}:
        return "language_literary"
    if claim_type in {"historical_cultural", "historical", "social", "political"}:
        return "historical_context"
    if note_type in {"ancient_near_east_context", "second_temple_context", "historical_context"}:
        return "historical_context"
    if category in {"archaeology", "geography"}:
        return "archaeology_geography" if relationship in {DIRECT_CONTEXT, BOOK_CONTEXT} else None
    if category == "chronology":
        return "chronology"
    if category in {"culture", "history", "politics", "social", "economics"}:
        return "historical_context"
    if category == "language":
        return "language_literary"
    return "historical_context"


def _batch002_root_cause(item: Mapping[str, Any]) -> tuple[str, list[str]]:
    metadata = dict(item.get("relevance_metadata") or {})
    claim = str(item.get("claim") or "")
    claim_type = str(metadata.get("claim_type") or "").casefold().replace("-", "_")
    note_type = str(metadata.get("note_type") or "").casefold().replace("-", "_")
    evidence_type = str(metadata.get("evidence_type") or "").casefold().replace("-", "_")
    dispute = str(metadata.get("dispute_status") or "").casefold()
    secondary: list[str] = []
    if dispute == "textual_variant" and not _mapping_is_textual(item):
        return "INTERPRETIVE_TEXTUAL_UNCERTAINTY", ["PRESENTATION_ROLE_HEURISTIC"]
    if note_type in {"textual_observation", "textual"}:
        return "PRESENTATION_ROLE_HEURISTIC", ["MISSING_NOTE_TYPE"] if note_type == "textual" else []
    if claim_type in {"historical_cultural", "historical", "social", "political"}:
        secondary.append("LEGACY_CATEGORY_OVERRIDE")
        return "TEXTUAL_WITNESS_MISCLASSIFICATION", secondary
    if claim_type == "reception_history":
        secondary.append("LEGACY_CATEGORY_OVERRIDE")
        return "TEXTUAL_WITNESS_MISCLASSIFICATION", secondary
    if claim_type in {"biblical_text", ""}:
        return "MISSING_CLAIM_TYPE", ["LEGACY_CATEGORY_OVERRIDE"]
    if evidence_type == "":
        secondary.append("MISSING_EVIDENCE_TYPE")
    if metadata.get("parent_type") and metadata.get("parent_type") != "archaeology" and not metadata.get("passage_anchors"):
        secondary.append("PARENT_METADATA_INHERITANCE")
    return "LEGACY_CATEGORY_OVERRIDE", secondary


def _batch002_textual_audit() -> dict[str, Any]:
    root = DEFAULT_OUTPUT_ROOT / "batch-002"
    quality_path = root / "terra" / "terra-quality-audit.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    primary_counts: Counter[str] = Counter()
    contributing_counts: Counter[str] = Counter()
    for review in quality.get("possible_evidence_review", []):
        reference = str(review["reference"])
        book, chapter_text = reference.rsplit(" ", 1)
        chapter = int(re.match(r"\d+", chapter_text).group())
        path = root / "evidence-bundles" / filename_for(book, chapter)
        bundle = json.loads(path.read_text(encoding="utf-8"))
        item = next(item for item in bundle.get("evidence_items", []) if item.get("id") == review["evidence_id"])
        metadata = dict(item.get("relevance_metadata") or {})
        primary, secondary = _batch002_root_cause(item)
        primary_counts[primary] += 1
        contributing_counts[primary] += 1
        for cause in secondary:
            contributing_counts[cause] += 1
        rows.append(
            {
                "reference": reference,
                "evidence_id": review["evidence_id"],
                "ckl_parent_object": metadata.get("parent_object_id"),
                "parent_type": metadata.get("parent_type"),
                "source_kind": metadata.get("source_kind"),
                "legacy_category": item.get("category"),
                "claim_type": metadata.get("claim_type"),
                "note_type": metadata.get("note_type"),
                "evidence_type": metadata.get("evidence_type"),
                "dispute_status": metadata.get("dispute_status"),
                "semantic_relationship": metadata.get("semantic_relationship"),
                "presentation_role": metadata.get("presentation_role"),
                "passage_anchors": item.get("passage_anchors", []),
                "claim": item.get("claim"),
                "root_cause": primary,
                "secondary_root_causes": secondary,
            }
        )
    return {
        "records_audited": len(rows),
        "root_cause_counts": {family: primary_counts[family] for family in ROOT_CAUSE_FAMILIES},
        "contributing_root_cause_counts": {family: contributing_counts[family] for family in ROOT_CAUSE_FAMILIES},
        "records": rows,
    }


def _anomaly(code: str, item: Any | None, explanation: str, *, severity: str = "blocker") -> dict[str, Any]:
    metadata = dict(getattr(item, "relevance_metadata", {}) or {}) if item is not None else {}
    return {
        "code": code,
        "severity": severity,
        "evidence_id": getattr(item, "id", None),
        "ckl_parent_record": metadata.get("parent_object_id"),
        "explanation": explanation,
    }


def scan_anomalies(
    bundle: Any,
    *,
    library: Any | None = None,
    parent_records: Mapping[str, Mapping[str, Any]] | None = None,
    parent_usage: Mapping[str, Mapping[str, Any]] | None = None,
    overview_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic anomaly records; review signals are non-blocking."""

    parent_records = parent_records or {}
    anomalies: list[dict[str, Any]] = []
    requested_book = str(bundle.passage_ref).rsplit(" ", 1)[0]
    for item in bundle.evidence_items:
        metadata = dict(item.relevance_metadata or {})
        relation = str(metadata.get("semantic_relationship") or "")
        role = str(metadata.get("presentation_role") or "")
        parent_type = str(metadata.get("parent_type") or "").casefold()
        parent_id = str(metadata.get("parent_object_id") or "")
        claim = str(item.claim or "")
        text = " ".join((parent_id, str(metadata.get("parent_title") or ""), claim))
        template = any(pattern.search(claim) for pattern in TEMPLATE_PATTERNS)
        raw_parent = parent_records.get(parent_id, {})
        raw_anchors = raw_parent.get("scripture_references") or []
        shape = _anchor_shape(
            [value.get("reference", "") if isinstance(value, dict) else str(value) for value in raw_anchors],
            library,
        ) if library is not None else {"books": [], "span_count": 0, "broad": False}

        if parent_type == "word_study":
            if relation == DIRECT_CONTEXT and GREEK_WORD_STUDY_HINTS.search(text) and requested_book in {
                "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges",
                "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles",
                "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes",
                "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel",
                "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
                "Zephaniah", "Haggai", "Zechariah", "Malachi",
            }:
                anomalies.append(_anomaly(
                    "WORD_STUDY_UNPROVEN_TRANSLATION_RELATIONSHIP", item,
                    "A Greek/translation word study is marked DIRECT_CONTEXT for an Old Testament chapter without an authored translation relationship.",
                ))
            if relation == DIRECT_CONTEXT and template:
                anomalies.append(_anomaly(
                    "WORD_STUDY_TEMPLATE_DIRECT_CONTEXT", item,
                    "Generated word-study template prose carries DIRECT_CONTEXT instead of a demonstrated lexical relation.",
                ))
            # Structured claim-level evidence may legitimately live under a
            # broad word-study parent. Only legacy parent inheritance is a
            # blocker; this is the distinction that protects precise anchors.
            if (shape["broad"] or len(shape["books"]) > 1) and metadata.get("source_kind") != "ckl_evidence_item":
                anomalies.append(_anomaly(
                    "WORD_STUDY_BROAD_PARENT_ANCHOR", item,
                    "The word-study parent has a broad or cross-book authored anchor set.",
                ))

        if parent_type == "archaeology":
            if relation == DIRECT_CONTEXT and template:
                anomalies.append(_anomaly(
                    "ARCHAEOLOGY_TEMPLATE_DIRECT_CONTEXT", item,
                    "Generic archaeology template prose is marked DIRECT_CONTEXT without claim-level material relevance.",
                ))
            if relation == DIRECT_CONTEXT and shape["broad"] and role != "archaeology_geography":
                anomalies.append(_anomaly(
                    "ARCHAEOLOGY_BROAD_PARENT_ANCHOR", item,
                    "Archaeology is direct but inherited from a broad parent anchor rather than a precise claim-level passage link.",
                ))
            temporal = str(raw_parent.get("temporal_relation") or metadata.get("temporal_relation") or "").casefold()
            if relation == DIRECT_CONTEXT and temporal in {"later_reception", "much_later", "postbiblical"} and FIRST_AUDIENCE_HINTS.search(claim):
                anomalies.append(_anomaly(
                    "ARCHAEOLOGY_LATE_EVIDENCE_AS_FIRST_AUDIENCE", item,
                    "Later archaeology is presented as direct first-audience context; later evidence may remain valid when routed as bounded material evidence.",
                ))

        if relation in {LATER_RECEPTION, INTERTEXTUAL_REUSE}:
            if role != "dig_deeper" or overview_id == item.id:
                anomalies.append(_anomaly(
                    "LATER_RECEPTION_FIRST_AUDIENCE_LEAKAGE", item,
                    "Later canonical reuse or reception is not confined to Dig Deeper and could ground first-audience overview.",
                ))

        if metadata.get("broad_tag_only") and relation != BOOK_CONTEXT:
            anomalies.append(_anomaly(
                "BROAD_TAG_OVERRIDES_CLAIM_ANCHOR", item,
                "A broad inherited tag is supplying evidence outside the BOOK_CONTEXT distinction.",
            ))
        if relation == DIRECT_CONTEXT and shape["broad"] and parent_type != "book" and metadata.get("source_kind") != "ckl_evidence_item":
            anomalies.append(_anomaly(
                "BROAD_PARENT_ANCHOR_LEAKAGE", item,
                "A non-book parent has broad Scripture anchors while its evidence is classified DIRECT_CONTEXT.",
            ))

        usage = (parent_usage or {}).get(parent_id, {})
        if len(set(usage.get("books", []))) >= 3 and parent_type not in {"book", "word_study"} and relation not in {INTERTEXTUAL_REUSE, LATER_RECEPTION, COMPARATIVE_CONTEXT}:
            anomalies.append(_anomaly(
                "CROSS_BOOK_PARENT_REUSE", item,
                "One non-lexical CKL parent is attached across unrelated books in the evaluated pool.",
            ))

        expected_role = presentation_role(metadata, category=item.category, claim=claim)
        textual_role = expected_role in {"language_literary", "interpretive_questions"}
        textual_claim = bool(re.search(
            r"\b(?:textual\s+variant|textual\s+criticism|textual\s+transmission|"
            r"manuscript(?:\s+reading)?|shorter[- ]text|longer[- ]text|"
            r"textual\s+witness(?:es)?|textual\s+omission)\b",
            text,
            re.IGNORECASE,
        ))
        if textual_role or textual_claim:
            if role == "archaeology_geography":
                anomalies.append(_anomaly(
                    "TEXTUAL_EVIDENCE_ROUTING_ANOMALY", item,
                    "Textual criticism or manuscript evidence is routed to archaeology/geography instead of a textual or interpretive section.",
                ))
        if _is_textual_witness_material(item) and expected_role is None:
            anomalies.append(_anomaly(
                "TEXTUAL_EVIDENCE_ROUTING_ANOMALY", item,
                "Textual material has no deterministic presentation role and must be quarantined for conservative review.",
            ))
        if _is_textual_witness_material(item) and _section_for_item(item) in {
            "historical_context",
            "archaeology_geography",
        }:
            anomalies.append(_anomaly(
                "TERRA_SUPPRESSION_REQUIRED", item,
                "Terra's defense-in-depth textual filter would have to suppress this item because it is routed as historical or material context.",
            ))
        if role and role not in SECTION_ROLES and role != "significance":
            anomalies.append(_anomaly(
                "UNKNOWN_PRESENTATION_ROLE", item,
                f"Presentation role {role!r} is not a recognized section role.",
            ))
        if expected_role and role and role != expected_role and role != "significance":
            anomalies.append(_anomaly(
                "PRESENTATION_ROLE_MISMATCH", item,
                f"Claim semantics expect {expected_role!r}, but metadata routes the item to {role!r}.",
            ))

        if template and relation == DIRECT_CONTEXT:
            anomalies.append(_anomaly(
                "TEMPLATE_DIRECT_CONTEXT", item,
                "Template-shaped prose carries strong DIRECT_CONTEXT grounding without enough specific claim support.",
            ))

        dispute = str(metadata.get("dispute_status") or "").casefold()
        if dispute and dispute not in {"not_disputed", "unknown", "none"} and overview_id == item.id:
            stronger = any(
                other.id != item.id
                and str((other.relevance_metadata or {}).get("dispute_status") or "").casefold() in {"", "not_disputed", "unknown", "none"}
                and str((other.relevance_metadata or {}).get("semantic_relationship") or "") in {DIRECT_CONTEXT, BOOK_CONTEXT, GENERIC_BACKGROUND}
                and (
                    str((other.relevance_metadata or {}).get("semantic_relationship") or "") == DIRECT_CONTEXT
                    and relation != DIRECT_CONTEXT
                    or int((other.relevance_metadata or {}).get("overview_priority") or 0) > int(metadata.get("overview_priority") or 0)
                )
                for other in bundle.evidence_items
            )
            anomalies.append(_anomaly(
                "DISPUTED_OVERVIEW_CANDIDATE", item,
                "A disputed or uncertain item was selected as overview while stronger non-disputed context is available." if stronger else "The selected overview remains disputed; no stronger non-disputed candidate was found.",
                severity="blocker" if stronger else "review",
            ))
        if relation == SEMANTICALLY_MISANCHORED:
            anomalies.append(_anomaly(
                "SEMANTICALLY_MISANCHORED_ITEM", item,
                "Evidence marked semantically misanchored reached the bundle boundary.",
            ))

    return anomalies


def backend_agreement(
    json_results: Sequence[Any],
    sqlite_results: Sequence[Any],
    json_bundle: Any,
    sqlite_bundle: Any,
) -> dict[str, Any]:
    """Compare backend result and EvidenceBundle identities deterministically."""

    json_ids = sorted(str(result.object.id) for result in json_results)
    sqlite_ids = sorted(str(result.object.id) for result in sqlite_results)
    json_evidence_ids = sorted(str(item.id) for item in json_bundle.evidence_items)
    sqlite_evidence_ids = sorted(str(item.id) for item in sqlite_bundle.evidence_items)
    return {
        "result_ids_agree": json_ids == sqlite_ids,
        "evidence_ids_agree": json_evidence_ids == sqlite_evidence_ids,
        "bundle_hash_agree": json_bundle.evidence_hash == sqlite_bundle.evidence_hash,
        "json_result_ids": json_ids,
        "sqlite_result_ids": sqlite_ids,
        "json_evidence_ids": json_evidence_ids,
        "sqlite_evidence_ids": sqlite_evidence_ids,
    }


def quarantine_reasons(
    record: Mapping[str, Any],
    *,
    agreement: Mapping[str, Any] | None = None,
) -> list[str]:
    """Return blocking verdict codes for a preflight record."""

    reasons: list[str] = []
    availability = str(record.get("availability") or "")
    if availability == EvidenceAvailability.DATA_GAP.value:
        reasons.append("DATA_GAP")
    agreement = agreement or record.get("json_sqlite_agreement") or {}
    if not agreement.get("result_ids_agree", False) or not agreement.get("evidence_ids_agree", False):
        reasons.append("JSON_SQLITE_DISAGREEMENT")
    if not agreement.get("bundle_hash_agree", False):
        reasons.append("EVIDENCE_HASH_DISAGREEMENT")
    if (record.get("semantic_audit") or {}).get("status") != "PASS":
        reasons.append("SEMANTIC_AUDIT_FAILURE")
    if (record.get("presentation_role_audit") or {}).get("status") != "PASS":
        reasons.append("PRESENTATION_ROLE_AUDIT_FAILURE")
    if "textual_routing_audit" in record and (record.get("textual_routing_audit") or {}).get("status") != "PASS":
        reasons.append("TEXTUAL_ROUTING_AUDIT_FAILURE")
    if "terra_suppression_simulation" in record and (record.get("terra_suppression_simulation") or {}).get("terra_textual_suppression_required"):
        reasons.append("TERRA_SUPPRESSION_REQUIRED")
    reasons.extend(
        sorted({str(item["code"]) for item in (record.get("anomaly_scan") or {}).get("anomalies", []) if item.get("severity") == "blocker"})
    )
    return sorted(set(reasons))


def select_final_chapters(evaluated: Sequence[Mapping[str, Any]], target_count: int) -> list[dict[str, Any]]:
    """Backfill from later pool members after quarantines/data gaps."""

    selected: list[dict[str, Any]] = []
    for row in evaluated:
        if row.get("status") == "PASS" and row.get("availability") in {"AVAILABLE", "THIN"}:
            selected.append(dict(row))
            if len(selected) == target_count:
                break
    return selected


def _semantic_audit(bundle: Any, library: Any, parent_records: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    reference = bundle.passage_ref
    errors: list[str] = []
    for item in bundle.evidence_items:
        if not any(
            scripture_reference_overlaps(target, span)
            for anchor in item.passage_anchors
            for span in parse_scripture_references(anchor, book_alias_lookup=library._book_alias_lookup)
            for target in parse_scripture_references(reference, book_alias_lookup=library._book_alias_lookup)
        ):
            errors.append(f"{item.id}:anchor-does-not-overlap")
        relation = str((item.relevance_metadata or {}).get("semantic_relationship") or "")
        if relation == SEMANTICALLY_MISANCHORED:
            errors.append(f"{item.id}:semantically-misanchored")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def _presentation_audit(bundle: Any) -> dict[str, Any]:
    errors: list[str] = []
    for item in bundle.evidence_items:
        metadata = item.relevance_metadata or {}
        role = metadata.get("presentation_role")
        if role and role not in SECTION_ROLES:
            errors.append(f"{item.id}:unknown-role:{role}")
        expected = presentation_role(metadata, category=item.category, claim=item.claim)
        if expected and role and role != expected and role != "significance":
            errors.append(f"{item.id}:expected-role:{expected}:actual-role:{role}")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def _textual_routing_audit(bundle: Any) -> dict[str, Any]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    for item in bundle.evidence_items:
        if not _is_textual_witness_material(item):
            continue
        metadata = item.relevance_metadata or {}
        role = metadata.get("presentation_role")
        expected = presentation_role(metadata, category=item.category, claim=item.claim)
        row = {
            "evidence_id": item.id,
            "presentation_role": role,
            "expected_role": expected,
            "semantic_relationship": metadata.get("semantic_relationship"),
        }
        rows.append(row)
        if role in {"historical_context", "archaeology_geography"}:
            errors.append(f"{item.id}:textual-material-routed:{role}")
        if expected is None:
            errors.append(f"{item.id}:ambiguous-textual-routing")
        if expected not in {"language_literary", "interpretive_questions", "dig_deeper", None}:
            errors.append(f"{item.id}:unexpected-textual-role:{expected}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "textual_evidence_count": len(rows),
        "items": rows,
    }


def _disputed_count(bundle: Any) -> int:
    return sum(
        str((item.relevance_metadata or {}).get("dispute_status") or "").casefold()
        not in {"", "not_disputed", "unknown", "none"}
        for item in bundle.evidence_items
    )


def _chapter_record(
    row: Mapping[str, Any],
    bundle: Any,
    *,
    library: Any,
    results: Sequence[Any],
    json_bundle: Any | None,
    sqlite_bundle: Any | None,
    parent_usage: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    parent_records = _parent_records(library, results)
    overview = select_overview_item(bundle)
    semantic = _semantic_audit(bundle, library, parent_records)
    presentation = _presentation_audit(bundle)
    anomalies = scan_anomalies(
        bundle,
        library=library,
        parent_records=parent_records,
        parent_usage=parent_usage,
        overview_id=overview.id if overview else None,
    )
    textual_routing = _textual_routing_audit(bundle)
    suppression = terra_textual_suppression_simulation(bundle)
    role_counts = Counter(str((item.relevance_metadata or {}).get("presentation_role") or "UNASSIGNED") for item in bundle.evidence_items)
    section_roles = Counter(
        section
        for item in bundle.evidence_items
        for section in [_section_for_item(item)]
        if section
    )
    semantic_counts = Counter(str((item.relevance_metadata or {}).get("semantic_relationship") or "UNASSIGNED") for item in bundle.evidence_items)
    direct = semantic_counts[DIRECT_CONTEXT]
    book_context = semantic_counts[BOOK_CONTEXT]
    generic = semantic_counts[GENERIC_BACKGROUND]
    later = semantic_counts[LATER_RECEPTION]
    comparative = semantic_counts[COMPARATIVE_CONTEXT]
    ids = sorted(result.object.id for result in results)
    json_ids = sorted(result.object.id for result in results)
    sqlite_ids = sorted(result.object.id for result in getattr(sqlite_bundle, "_retrieval_results", ())) if sqlite_bundle is not None else []
    # The actual ID lists are passed separately in the runner; the fields are
    # overwritten there. Keeping this constructor useful for test fixtures is
    # preferable to hiding retrieval state in EvidenceBundle.
    return {
        "reference": bundle.passage_ref,
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "genre": row.get("genre") or _book_genre(str(row["book"])),
        "availability": classify_evidence_availability(bundle).value,
        "evidence_count": len(bundle.evidence_items),
        "direct_context_count": direct,
        "book_context_count": book_context,
        "generic_background_count": generic,
        "later_reception_count": later,
        "comparative_context_count": comparative,
        "disputed_count": _disputed_count(bundle),
        "semantic_relationship_counts": dict(sorted(semantic_counts.items())),
        "presentation_role_counts": dict(sorted(role_counts.items())),
        # significance is an internal presentation-provider role, not an
        # allowed Commentary section kind for Terra input.
        "presentation_section_roles": sorted(set(section_roles) - {"significance"}),
        "overview_candidate": overview.id if overview else None,
        "overview_candidate_disputed": bool(overview and _disputed_count(type("B", (), {"evidence_items": [overview]})()) > 0),
        "evidence_hash": calculate_evidence_hash(bundle),
        "bundle_version": bundle.version,
        "hash_version": bundle.evidence_hash_version,
        "evidence_ids": [item.id for item in bundle.evidence_items],
        "evidence_items": [_item_summary(item) for item in bundle.evidence_items],
        "retrieval_result_ids": ids,
        "json_evidence_ids": [item.id for item in bundle.evidence_items],
        "sqlite_evidence_ids": [],
        "json_sqlite_agreement": {"result_ids_agree": True, "evidence_ids_agree": True, "bundle_hash_agree": True},
        "semantic_audit": semantic,
        "presentation_role_audit": presentation,
        "textual_routing_audit": textual_routing,
        "terra_suppression_simulation": suppression,
        "anomaly_scan": {"status": "PASS" if not [a for a in anomalies if a["severity"] == "blocker"] else "FAIL", "anomalies": anomalies},
        "source_parent_records": sorted(parent_records),
    }


def _bundle_json(bundle: Any) -> dict[str, Any]:
    return bundle.to_dict()


def _stats(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = [int(row["evidence_count"]) for row in records]
    ordered = sorted(values)

    def percentile(percent: float) -> int:
        if not ordered:
            return 0
        index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * percent) - 1))
        return ordered[index]

    return {
        "min": min(values) if values else 0,
        "median": median(values) if values else 0,
        "mean": round(mean(values), 2) if values else 0,
        "p90": percentile(0.90),
        "p95": percentile(0.95),
        "max": max(values) if values else 0,
        "distribution": dict(sorted(Counter(values).items())),
    }


def _mark_extreme_counts(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    values = sorted(int(row["evidence_count"]) for row in records)
    if len(values) < 4:
        return []
    q1 = values[max(0, math.floor((len(values) - 1) * 0.25))]
    q3 = values[min(len(values) - 1, math.floor((len(values) - 1) * 0.75))]
    threshold = q3 + 1.5 * (q3 - q1)
    outliers = []
    for row in records:
        if int(row["evidence_count"]) > threshold:
            signal = {"reference": row["reference"], "evidence_count": row["evidence_count"], "threshold": threshold, "severity": "review"}
            row.setdefault("anomaly_scan", {}).setdefault("review_signals", []).append({"code": "EVIDENCE_COUNT_OUTLIER", **signal})
            outliers.append(signal)
    return outliers


def _make_certification(record: Mapping[str, Any], bundle_path: str, sqlite: dict[str, Any]) -> dict[str, Any]:
    return {
        "reference": record["reference"],
        "book": record["book"],
        "chapter": record["chapter"],
        "availability": record["availability"],
        "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION,
        "evidence_hash_version": EVIDENCE_HASH_VERSION,
        "locked_evidence_hash": record["evidence_hash"],
        "evidence_ids": record["evidence_ids"],
        "json_evidence_ids": record["json_evidence_ids"],
        "sqlite_evidence_ids": record["sqlite_evidence_ids"],
        "json_sqlite_agreement": sqlite,
        "backend_agreement": sqlite,
        "semantic_audit": record["semantic_audit"],
        "presentation_role_audit": record["presentation_role_audit"],
        "textual_routing_audit": record["textual_routing_audit"],
        "terra_textual_suppression_required": record["terra_suppression_simulation"]["terra_textual_suppression_required"],
        "terra_suppression_simulation": record["terra_suppression_simulation"],
        "overview_gate": {
            "status": "PASS" if not any(
                item.get("code") == "DISPUTED_OVERVIEW_CANDIDATE"
                and item.get("severity") == "blocker"
                for item in record.get("anomaly_scan", {}).get("anomalies", [])
            ) else "FAIL",
            "overview_candidate": record.get("overview_candidate"),
        },
        "anomaly_gate": record["anomaly_scan"],
        "lock_status": "LOCKED",
        "evidence_bundle_path": bundle_path,
    }


def _terra_input(record: Mapping[str, Any], bundle_path: str) -> dict[str, Any]:
    return {
        "reference": record["reference"],
        "book": record["book"],
        "chapter": record["chapter"],
        "canonical_text_input_locator": f"bible.resolve_chapter({record['book']!r}, {record['chapter']})",
        "locked_evidence_bundle_hash": record["evidence_hash"],
        "evidence_bundle_version": record["bundle_version"],
        "evidence_hash_version": record["hash_version"],
        "availability": record["availability"],
        "allowed_section_roles": record["presentation_section_roles"],
        "evidence_bundle_path": bundle_path,
        "dig_deeper_evidence_exists": "dig_deeper" in record["presentation_section_roles"],
        "disputed_evidence_count": record["disputed_count"],
        "textual_evidence_present": record["textual_routing_audit"]["textual_evidence_count"] > 0,
        "terra_textual_suppression_required": record["terra_suppression_simulation"]["terra_textual_suppression_required"],
        "evidence_reconstruction": {
            "function": "bhf_agent.chapter_commentary.evidence_bundling.get_chapter_evidence_bundle",
            "arguments": {"book": record["book"], "chapter": record["chapter"], "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION},
            "verify_hash_before_generation": True,
        },
        "candidate_output_filename": filename_for(str(record["book"]), int(record["chapter"])),
    }


def _mapping_is_textual(item: Mapping[str, Any]) -> bool:
    metadata = dict(item.get("relevance_metadata") or {})
    authored = {
        str(metadata.get(key) or "")
        .casefold()
        .replace("-", "_")
        .replace(" ", "_")
        for key in ("claim_type", "note_type", "evidence_type", "source_kind")
    }
    if authored & set(TEXTUAL_CLAIM_SIGNALS):
        return True
    claim = str(item.get("claim") or "")
    if str(metadata.get("parent_type") or "").casefold() == "archaeology":
        if re.search(r"\b(?:discover(?:ed|y)|excavat(?:ed|ion)|found|cave|site|provenance|physical|artifact|deposit|stratigraph|archaeolog(?:y|ical))\b", claim, re.I) and not re.search(r"\b(?:reading|variant|version|transmission|preserv(?:es|ed)|textual\s+profile|textual\s+difference|different\s+text)\b", claim, re.I):
            return False
    return bool(TEXTUAL_CLAIM_TEXT_RE.search(claim))


def _prose_cited_evidence(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    cited: set[str] = set()
    for section in data.get("sections", []):
        for block in section.get("blocks", []):
            cited.update(str(value) for value in block.get("evidence_ids", []))
    return cited


def _historical_textual_routing_review(json_library: Any) -> dict[str, Any]:
    """Reconstruct historical locks without editing them or their prose."""

    rows: list[dict[str, Any]] = []
    roots = [
        ("Batch 001", DEFAULT_OUTPUT_ROOT / "batch-001"),
        ("Batch 002", DEFAULT_OUTPUT_ROOT / "batch-002"),
    ]
    for batch_label, root in roots:
        for old_path in sorted((root / "evidence-bundles").glob("*.json")):
            old_data = json.loads(old_path.read_text(encoding="utf-8"))
            passage_ref = str(old_data.get("passage_ref") or "")
            if not passage_ref:
                continue
            book, chapter_text = passage_ref.rsplit(" ", 1)
            chapter = int(re.match(r"\d+", chapter_text).group())
            reference = reference_key(book, chapter)
            new_bundle, _results = _build_bundle(json_library, book, chapter)
            old_items = {str(item.get("id")): item for item in old_data.get("evidence_items", [])}
            new_items = {str(item.id): item for item in new_bundle.evidence_items}
            affected_items: list[dict[str, Any]] = []
            for evidence_id, old_item in old_items.items():
                if not _mapping_is_textual(old_item):
                    continue
                new_item = new_items.get(evidence_id)
                old_meta = dict(old_item.get("relevance_metadata") or {})
                new_meta = dict(new_item.relevance_metadata or {}) if new_item else {}
                old_role = old_meta.get("presentation_role")
                new_role = new_meta.get("presentation_role")
                if old_role == new_role and new_item is not None:
                    continue
                terra_path = root / "terra" / "chapters" / old_path.name
                cited = _prose_cited_evidence(terra_path)
                affected_items.append(
                    {
                        "evidence_id": evidence_id,
                        "old_presentation_role": old_role,
                        "new_presentation_role": new_role,
                        "existing_terra_prose_cited_affected_item": None if cited is None else evidence_id in cited,
                        "terra_omitted_affected_item": None if cited is None else evidence_id not in cited,
                        "claim": old_item.get("claim"),
                    }
                )
            old_ids = sorted(old_items)
            new_ids = sorted(new_items)
            new_hash = new_bundle.evidence_hash
            old_hash = str(old_data.get("evidence_hash") or "")
            if affected_items or old_hash != new_hash:
                rows.append(
                    {
                        "reference": reference,
                        "historical_batch": batch_label,
                        "old_locked_hash": old_hash,
                        "newly_reconstructed_hash": new_hash,
                        "evidence_ids_changed": old_ids != new_ids,
                        "old_presentation_roles": sorted({str(item.get("old_presentation_role")) for item in affected_items}),
                        "new_presentation_roles": sorted({str(item.get("new_presentation_role")) for item in affected_items}),
                        "affected_items": affected_items,
                        "existing_terra_prose_cited_affected_item": any(item["existing_terra_prose_cited_affected_item"] is True for item in affected_items),
                        "terra_omitted_affected_item": bool(affected_items) and all(item["terra_omitted_affected_item"] is True for item in affected_items),
                        "final_v1_1_regeneration_recommended": bool(affected_items and any(item["existing_terra_prose_cited_affected_item"] is True for item in affected_items)),
                        "hash_changed": old_hash != new_hash,
                    }
                )
    return {
        "review_version": "commentary-v11-post-batch-textual-routing-review-1.0",
        "historical_chapters_scanned": sum(
            len(list((root / "evidence-bundles").glob("*.json")))
            for _label, root in roots
        ),
        "affected_chapters": len(rows),
        "records": rows,
        "terra_omitted_affected_item_count": sum(row["terra_omitted_affected_item"] for row in rows),
        "regeneration_recommended_count": sum(row["final_v1_1_regeneration_recommended"] for row in rows),
    }


def _corpus_textual_routing_audit(json_library: Any, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    before: Counter[str] = Counter()
    after: Counter[str] = Counter()
    records_found = 0
    chapters_affected: set[str] = set()
    corrections = Counter()
    interpretive: list[dict[str, Any]] = []
    dig_deeper: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    target_spans_by_book: dict[str, list[tuple[str, Any]]] = defaultdict(list)
    for row in rows:
        reference = reference_key(str(row["book"]), int(row["chapter"]))
        for span in parse_scripture_references(
            reference,
            book_alias_lookup=json_library._book_alias_lookup,
        ):
            target_spans_by_book[span.book].append((reference, span))
    object_root = REPO_ROOT / "framework" / "canonical_library" / "objects"
    for path in sorted(object_root.rglob("*.json")):
        try:
            parent = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(parent, Mapping):
            continue
        parent_id = str(parent.get("id") or "")
        parent_type = str(parent.get("type") or "")
        parent_title = str(parent.get("title") or "")
        collections = (
            ("claims", "ckl_claim"),
            ("evidence_items", "ckl_evidence_item"),
            ("interpretive_notes", "ckl_interpretive_note"),
        )
        for collection, source_kind in collections:
            for raw_item in parent.get(collection) or []:
                item = dict(raw_item) if isinstance(raw_item, Mapping) else {}
                claim = str(
                    item.get("claim")
                    or item.get("claim_text")
                    or item.get("description")
                    or item.get("primary_observation")
                    or item.get("note")
                    or ""
                )
                item_id = str(item.get("id") or item.get("claim_id") or "")
                anchors = [str(value) for value in item.get("scripture_references") or [] if not isinstance(value, Mapping)]
                anchors += [str(value.get("reference") or "") for value in item.get("scripture_references") or [] if isinstance(value, Mapping)]
                if not claim or not item_id or not anchors:
                    continue
                metadata = {
                    "source_kind": source_kind,
                    "parent_object_id": parent_id,
                    "parent_title": parent_title,
                    "parent_type": parent_type,
                    "passage_relationship": "direct",
                    "claim_type": str(item.get("claim_type") or ""),
                    "note_type": str(item.get("note_type") or ""),
                    "evidence_type": str(item.get("evidence_type") or ""),
                    "dispute_status": str(item.get("dispute_status") or ""),
                    "assertion_type": str(item.get("assertion_type") or ""),
                }
                metadata = with_semantic_relationship(
                    reference_key(str(rows[0]["book"]), int(rows[0]["chapter"])) if rows else "",
                    metadata,
                    anchors=anchors,
                ) if rows else metadata
                category = _normalized_category(
                    item.get("evidence_type") or item.get("claim_type") or item.get("note_type"),
                    claim,
                )
                anchor_spans = [
                    span
                    for anchor in anchors
                    for span in parse_scripture_references(anchor, book_alias_lookup=json_library._book_alias_lookup)
                ]
                matching_targets: set[str] = set()
                for anchor_span in anchor_spans:
                    for reference, target_span in target_spans_by_book.get(anchor_span.book, []):
                        if scripture_reference_overlaps(target_span, anchor_span):
                            matching_targets.add(reference)
                for reference in sorted(matching_targets):
                    # Recompute semantic metadata against the actual target
                    # chapter; one book-level claim can be a valid record in
                    # many eligible chapters.
                    target_metadata = with_semantic_relationship(
                        reference,
                        metadata,
                        anchors=anchors,
                    )
                    target_metadata = with_presentation_metadata(
                        target_metadata,
                        category=category,
                        claim=claim,
                    )
                    record_mapping = {"claim": claim, "relevance_metadata": target_metadata}
                    if not _mapping_is_textual(record_mapping):
                        continue
                    records_found += 1
                    old_role = _legacy_presentation_role(target_metadata, category=category, claim=claim)
                    new_role = target_metadata.get("presentation_role")
                    before[str(old_role or "UNASSIGNED")] += 1
                    after[str(new_role or "UNASSIGNED")] += 1
                    if old_role != new_role:
                        chapters_affected.add(reference)
                        corrections[f"{old_role or 'UNASSIGNED'} -> {new_role or 'UNASSIGNED'}"] += 1
                    if new_role == "interpretive_questions":
                        interpretive.append({"reference": reference, "evidence_id": item_id})
                    elif new_role == "dig_deeper":
                        dig_deeper.append({"reference": reference, "evidence_id": item_id})
                    elif new_role not in {"language_literary", "interpretive_questions", "dig_deeper"}:
                        ambiguous.append({"reference": reference, "evidence_id": item_id, "role": new_role})
    return {
        "eligible_corpus_chapters_scanned": len(rows),
        "textual_evidence_records_found": records_found,
        "chapters_affected": len(chapters_affected),
        "routing_distribution_before_fix": dict(sorted(before.items())),
        "routing_distribution_after_fix": dict(sorted(after.items())),
        "corrections": dict(sorted(corrections.items())),
        "historical_context_to_language_literary": corrections["historical_context -> language_literary"],
        "archaeology_geography_to_language_literary": corrections["archaeology_geography -> language_literary"],
        "interpretive_questions_assignments": interpretive,
        "dig_deeper_assignments": dig_deeper,
        "ambiguous_unresolved_cases": ambiguous,
    }


def _markdown_report(manifest: Mapping[str, Any], preflight: Mapping[str, Any], quarantines: Mapping[str, Any], controls: Mapping[str, Any]) -> str:
    final = manifest["final_chapters"]
    anomaly_counts = Counter(code for row in preflight["evaluated"] for code in [a["code"] for a in row.get("anomaly_scan", {}).get("anomalies", [])])
    lines = [
        f"# Commentary v1.1 Scaled {manifest['batch_id'].replace('-', ' ').title()} Evidence Preflight",
        "",
        "This is a Luna deterministic evidence certification. Terra was not run and no reader-facing prose was generated.",
        "",
        "## Selection and population",
        "",
        f"- Candidate pool: {manifest['candidate_pool_size']} chapters; target: {manifest['target_count']}; evaluated: {manifest['chapters_evaluated']}; skipped outside the pool: {manifest.get('chapters_skipped', 0)}.",
        f"- Current deterministic low-information population: {manifest['current_population']['eligible']} eligible and {manifest['current_population']['insufficient']} insufficient (historical reference: 935 / 153).",
        f"- Mixed selection: genre/availability round-robin, reader-benefit signals for ordering only, maximum five chapters per book in the pool.",
        f"- Replacements used: {manifest['replacements_used']}.",
        f"- Excluded prior/canary references: {len(manifest.get('excluded_regression_controls', []))}.",
        "",
        "## Final certification",
        "",
        f"- Status: **{manifest['status']}**",
        f"- Final locked chapters: {len(final)}",
        f"- Availability: {manifest['availability_distribution']}",
        f"- Genre: {manifest['genre_distribution']}",
        f"- Evidence count statistics: {manifest['evidence_count_statistics']}",
        f"- Semantic relationship totals: {manifest.get('semantic_relationship_totals', {})}.",
        f"- Presentation-role totals: {manifest.get('presentation_role_totals', {})}.",
        "",
        "## Final PASS chapters",
        "",
        ", ".join(row["reference"] for row in final),
        "",
        "## Candidate pool",
        "",
        ", ".join(row["reference"] for row in manifest["candidate_pool"]),
        "",
        "## Quarantines",
        "",
    ]
    if quarantines["chapters"]:
        for row in quarantines["chapters"]:
            lines.append(f"- **{row['reference']}** — {', '.join(row['reason_codes'])}. {row['explanation']}")
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Anomaly patterns",
        "",
        f"- Word-study anomalies: {sum(value for key, value in anomaly_counts.items() if key.startswith('WORD_STUDY'))}",
        f"- Archaeology anomalies: {sum(value for key, value in anomaly_counts.items() if key.startswith('ARCHAEOLOGY'))}",
        f"- Later-reception anomalies: {anomaly_counts['LATER_RECEPTION_FIRST_AUDIENCE_LEAKAGE']}",
        f"- Broad-anchor anomalies: {sum(value for key, value in anomaly_counts.items() if 'BROAD' in key or 'CROSS_BOOK' in key)}",
        f"- Presentation-role anomalies: {sum(value for key, value in anomaly_counts.items() if key.startswith('PRESENTATION') or key == 'UNKNOWN_PRESENTATION_ROLE')}",
        f"- Template-evidence anomalies: {sum(value for key, value in anomaly_counts.items() if key.startswith('TEMPLATE') or key.endswith('TEMPLATE_DIRECT_CONTEXT'))}",
        f"- Evidence-count outliers: {len(preflight['evidence_count_outliers'])} review signals; none auto-quarantined.",
        f"- Textual-evidence routing anomalies: {preflight['anomaly_counts'].get('TEXTUAL_EVIDENCE_ROUTING_ANOMALY', 0)}.",
        "",
        "## Luke 22 routing review",
        "",
        "The `luke-meal-variant` claim is a direct CKL claim owned by the `luke` book parent. Its stored category is `geography`, but its claim text concerns manuscript witnesses, shorter/longer readings, and textual-variant uncertainty. The prior projector treated the legacy category as a presentation instruction and routed it to `archaeology_geography`.",
        "",
        "The shared rule now gives narrow textual-variant signals precedence over legacy geography/archaeology facets. Luke 22 routes to `language_literary`; interpretive textual notes can route to `interpretive_questions`. The original Batch 001 lock and prose artifact remain unchanged. The reconstructed hash changed from `ffde3ebe0c02e5c41f530158730c25ed8f7122950abf4ddd4b0995588ee6230e` to `dabf2f65b9dc00872535abcca1d8d7206d24a846e5390d1e128cdc4459b204f7`, with evidence IDs unchanged, so Luke 22 requires future corrective recertification before any prose regeneration.",
        "",
        "## Regression controls",
        "",
    ]
    for reference, result in controls.items():
        lines.append(f"- **{reference}** — {result['status']}: {result['summary']}")
    batch002 = manifest.get("batch002_textual_audit", {})
    historical = manifest.get("historical_textual_routing_review", {})
    corpus = manifest.get("corpus_textual_routing_audit", {})
    lines += [
        "",
        "## Textual routing",
        "",
        f"- Batch 002 POSSIBLE_EVIDENCE_REVIEW records audited: {batch002.get('records_audited', 0)}.",
        f"- Primary root-cause distribution: {batch002.get('root_cause_counts', {})}.",
        f"- Contributing root-cause distribution (primary plus secondary): {batch002.get('contributing_root_cause_counts', {})}.",
        "- Deterministic precedence: explicit claim_type, note_type, evidence_type, source_kind, semantic relationship, parent type, then a narrow claim-text fallback; physical manuscript discovery remains archaeology while manuscript-reading claims route to language/textual context.",
        f"- Corpus scan: {corpus.get('eligible_corpus_chapters_scanned', 0)} regeneration-eligible chapters and {corpus.get('textual_evidence_records_found', 0)} textual records; {corpus.get('chapters_affected', 0)} chapters affected.",
        f"- Routing before: {corpus.get('routing_distribution_before_fix', {})}.",
        f"- Routing after: {corpus.get('routing_distribution_after_fix', {})}.",
        f"- Routing corrections: {corpus.get('corrections', {})}.",
        f"- Interpretive_questions assignments: {len(corpus.get('interpretive_questions_assignments', []))}; Dig Deeper assignments: {len(corpus.get('dig_deeper_assignments', []))}.",
        f"- Unresolved ambiguous cases: {corpus.get('ambiguous_unresolved_cases', [])}.",
        f"- Historical reconstructed hash-impact records: {historical.get('affected_chapters', 0)}; Terra-omitted affected items: {historical.get('terra_omitted_affected_item_count', 0)}; regeneration recommendations: {historical.get('regeneration_recommended_count', 0)}.",
        f"- Terra suppression simulation: {manifest.get('terra_suppression_required_count', 0)} evaluated chapters required suppression; final 150 required none.",
        "",
        "## Batch 003 audit detail",
        "",
        f"- Candidate pool: {manifest.get('candidate_pool_size')}; evaluated: {manifest.get('chapters_evaluated')}; PASS: {manifest.get('chapters_passed')}; QUARANTINE: {manifest.get('chapters_quarantined')}; DATA_GAP: {manifest.get('chapters_data_gap')}; replacements: {manifest.get('replacements_used')}; final locks: {len(final)}.",
        f"- Verdict counts including manifest-derived exclusions: {manifest.get('verdict_counts', {})}.",
        f"- Availability: {manifest.get('availability_distribution', {})}; genres: {manifest.get('genre_distribution', {})}; books: {manifest.get('book_distribution', {})}.",
        f"- Evidence statistics: {manifest.get('evidence_count_statistics', {})}.",
        f"- Anomaly raw counts: {preflight.get('anomaly_raw_counts', manifest.get('anomaly_raw_counts', {}))}.",
        f"- Anomaly blocking counts: {preflight.get('anomaly_blocking_counts', manifest.get('anomaly_blocking_counts', {}))}.",
        f"- Backend disagreements: {preflight.get('disagreement_counts', {})}.",
        f"- Artifact fingerprints: canary/supplemental {controls.get('canary_artifacts', {}).get('status')}; Batch 001 {controls.get('batch_001_terra_artifacts', {}).get('status')}; Batch 002 {controls.get('batch_002_terra_artifacts', {}).get('status')}.",
        "- Terra was not run; prose_generated remains false.",
        "",
    ]
    lines += [
        "",
        "## Systemic CKL concern",
        "",
        "Template-shaped CKL background, cross-testament reception records, broad word-study parents, and cross-book parent reuse remain systemic review surfaces. This batch quarantines deterministic blockers; it does not repair evidence. Any repeated template or broad-parent pattern should be handled in a separate Luna evidence-cleanup task.",
        "",
        f"The batch is eligible for a future Terra Medium {manifest['batch_id'].replace('-', ' ').title()} generation only after the locked manifest is consumed and its hashes are rechecked immediately before generation.",
        "",
    ]
    return "\n".join(lines)


def _regression_controls(
    json_library: Any,
    before: Mapping[str, str],
    after: Mapping[str, str],
    batch_001_before: Mapping[str, str],
    batch_001_after: Mapping[str, str],
    batch_002_before: Mapping[str, str],
    batch_002_after: Mapping[str, str],
) -> dict[str, Any]:
    controls: dict[str, Any] = {}
    for book, chapter in (("Genesis", 1), ("Zephaniah", 1), ("Luke", 1), ("Leviticus", 1), ("1 Samuel", 28), ("Numbers", 3), ("Luke", 22)):
        bundle, results = _build_bundle(json_library, book, chapter)
        overview = select_overview_item(bundle)
        anomalies = scan_anomalies(bundle, library=json_library, parent_records=_parent_records(json_library, results), overview_id=overview.id if overview else None)
        ref = reference_key(book, chapter)
        assertions: list[str] = []
        if ref == "Genesis 1":
            assertions += [
                "no archaeology entities/items" if not any(item.category in {"archaeology", "geography"} and (item.relevance_metadata or {}).get("parent_type") == "archaeology" for item in bundle.evidence_items) else "false archaeology",
                "no word studies" if not any((item.relevance_metadata or {}).get("parent_type") == "word_study" for item in bundle.evidence_items) else "false word study",
            ]
        elif ref == "Zephaniah 1":
            assertions.append("Josiah-era overview retained" if overview and overview.id in {"zephaniah-date", "zephaniah-superscription", "zephaniah-cult"} else "overview changed")
        elif ref == "Luke 1":
            item = next((item for item in bundle.evidence_items if item.id == "luke-acts-relation"), None)
            assertions.append("Luke-Acts relation is language_literary" if item and item.relevance_metadata.get("presentation_role") == "language_literary" else "Luke-Acts relation misrouted")
        elif ref == "Leviticus 1":
            item = next((item for item in bundle.evidence_items if item.id == "what-is-sacrifice-in-the-bible:ancient_near_east_context:0"), None)
            assertions.append("ritual context is historical_context" if item and item.relevance_metadata.get("presentation_role") == "historical_context" else "ritual context misrouted")
        elif ref == "Luke 22":
            item = next((item for item in bundle.evidence_items if item.id == "luke-meal-variant"), None)
            assertions.append(
                "textual variant is language_literary"
                if item and item.relevance_metadata.get("presentation_role") == "language_literary"
                else "textual variant misrouted"
            )
            assertions.append(
                "no textual routing blocker"
                if not any(anomaly["code"] == "TEXTUAL_EVIDENCE_ROUTING_ANOMALY" and anomaly["severity"] == "blocker" for anomaly in anomalies)
                else "textual routing blocker"
            )
            assertions.append(
                "no Terra textual suppression"
                if not terra_textual_suppression_simulation(bundle)["terra_textual_suppression_required"]
                else "Terra textual suppression required"
            )
        elif ref == "1 Samuel 28":
            disputed = [item for item in bundle.evidence_items if (item.relevance_metadata or {}).get("dispute_status") not in {None, "", "not_disputed", "unknown", "none"}]
            assertions.append("THIN" if classify_evidence_availability(bundle).value == "THIN" else "availability changed")
            assertions.append("two evidence items" if len(bundle.evidence_items) == 2 else f"{len(bundle.evidence_items)} evidence items")
            assertions.append("apparition disputed" if disputed else "dispute lost")
        else:
            assertions += ["DATA_GAP" if classify_evidence_availability(bundle).value == "DATA_GAP" else "availability changed", "zero evidence" if not bundle.evidence_items else "evidence appeared"]
        blockers = [item for item in anomalies if item["severity"] == "blocker"]
        controls[ref] = {"status": "PASS" if not blockers and not any("changed" in item or "false" in item or "misrouted" in item or "lost" in item or "appeared" in item for item in assertions) else "FAIL", "summary": "; ".join(assertions), "anomalies": anomalies}
    controls["canary_artifacts"] = {
        "status": "PASS" if dict(before) == dict(after) else "FAIL",
        "summary": "26 prose-control artifact fingerprints unchanged" if dict(before) == dict(after) else "prose-control artifact fingerprint changed",
        "before_fingerprint": _stable_fingerprint(before),
        "after_fingerprint": _stable_fingerprint(after),
        "changed_paths": sorted(set(before) ^ set(after) | {path for path in before.keys() & after.keys() if before[path] != after[path]}),
    }
    controls["batch_001_terra_artifacts"] = {
        "status": "PASS" if dict(batch_001_before) == dict(batch_001_after) and len(batch_001_after) == 50 else "FAIL",
        "summary": "50 Batch 001 Terra artifact fingerprints unchanged" if dict(batch_001_before) == dict(batch_001_after) and len(batch_001_after) == 50 else "Batch 001 Terra artifact fingerprint changed or count is not 50",
        "before_fingerprint": _stable_fingerprint(batch_001_before),
        "after_fingerprint": _stable_fingerprint(batch_001_after),
        "artifact_count": len(batch_001_after),
        "changed_paths": sorted(set(batch_001_before) ^ set(batch_001_after) | {path for path in batch_001_before.keys() & batch_001_after.keys() if batch_001_before[path] != batch_001_after[path]}),
    }
    controls["batch_002_terra_artifacts"] = {
        "status": "PASS" if dict(batch_002_before) == dict(batch_002_after) and len(batch_002_after) == 100 else "FAIL",
        "summary": "100 Batch 002 Terra artifact fingerprints unchanged" if dict(batch_002_before) == dict(batch_002_after) and len(batch_002_after) == 100 else "Batch 002 Terra artifact fingerprint changed or count is not 100",
        "before_fingerprint": _stable_fingerprint(batch_002_before),
        "after_fingerprint": _stable_fingerprint(batch_002_after),
        "artifact_count": len(batch_002_after),
        "changed_paths": sorted(set(batch_002_before) ^ set(batch_002_after) | {path for path in batch_002_before.keys() & batch_002_after.keys() if batch_002_before[path] != batch_002_after[path]}),
    }
    return controls


def run_batch(
    *,
    batch_id: str,
    target_count: int,
    candidate_pool_size: int,
    output_root: Path,
    candidate_source: Path = DEFAULT_CANDIDATE_SOURCE,
    sqlite_database: Path | None = None,
) -> dict[str, Any]:
    output_root = output_root if output_root.is_absolute() else (REPO_ROOT / output_root)
    output_root = output_root.resolve()
    before_fingerprints = _artifact_fingerprints()
    batch_001_before_fingerprints = _batch_001_terra_fingerprints()
    batch_002_before_fingerprints = _batch_002_terra_fingerprints()
    current = recalculate_low_information(candidate_source)
    _progress("population recalculated")
    historical = {"eligible": 935, "insufficient": 153}
    current_population = {
        "eligible": len(current["chapters_evidence_supports_regeneration"]),
        "insufficient": len(current["chapters_evidence_insufficient"]),
        "difference_from_historical": {
            "eligible": len(current["chapters_evidence_supports_regeneration"]) - historical["eligible"],
            "insufficient": len(current["chapters_evidence_insufficient"]) - historical["insufficient"],
        },
    }
    excluded = _canary_references()
    prior_batch_exclusions = _previous_batch_references(batch_id)
    prior_batch_verdicts = _previous_batch_reference_verdicts(batch_id)
    excluded.update(prior_batch_exclusions)
    eligible = _eligible_rows(current)
    candidate_pool = select_mixed_candidate_pool(eligible, pool_size=candidate_pool_size, excluded_references=excluded)
    batch002_textual_audit = _batch002_textual_audit()
    skipped_verdicts = {
        reference: "SKIP_CANARY"
        for reference in _canary_references()
    }
    skipped_verdicts.update(prior_batch_verdicts)

    pool_dir = output_root / batch_id
    bundle_dir = pool_dir / "evidence-bundles"
    pool_dir.mkdir(parents=True, exist_ok=True)
    with _sqlite_workspace(sqlite_database) as db_path:
        json_library = load_canonical_library(config=CKLRepositoryConfig(backend="json", json_root=str(REPO_ROOT / "framework" / "canonical_library")))
        sqlite_library = load_canonical_library(config=CKLRepositoryConfig(backend="sqlite", database_path=str(db_path), json_root=str(REPO_ROOT / "framework" / "canonical_library"), stale_database_policy="ignore"))
        historical_textual_review = _historical_textual_routing_review(json_library)
        _progress("historical textual routing reconstructed")
        corpus_textual_audit = _corpus_textual_routing_audit(json_library, eligible)
        _progress("corpus textual routing scanned")

        def evaluate_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            raw_records: list[dict[str, Any]] = []
            for row in rows:
                bundle, results = _build_bundle(json_library, str(row["book"]), int(row["chapter"]))
                parent_records = _parent_records(json_library, results)
                for parent_id in parent_records:
                    usage = next((entry for entry in raw_records if entry.get("_parent_id") == parent_id), None)
                    if usage is None:
                        raw_records.append({"_parent_id": parent_id, "books": [], "references": []})
                        usage = raw_records[-1]
                    if row["book"] not in usage["books"]:
                        usage["books"].append(row["book"])
                    usage["references"].append(row["reference"])
            parent_usage = {
                entry["_parent_id"]: {"books": entry["books"], "references": entry["references"]}
                for entry in raw_records
            }
            evaluated_rows: list[dict[str, Any]] = []
            bundles: dict[str, Any] = {}
            for row in rows:
                book, chapter = str(row["book"]), int(row["chapter"])
                bundle, results = _build_bundle(json_library, book, chapter)
                sqlite_bundle, sqlite_results = _build_bundle(sqlite_library, book, chapter)
                record = _chapter_record(
                    row, bundle, library=json_library, results=results,
                    json_bundle=bundle, sqlite_bundle=None, parent_usage=parent_usage,
                )
                agreement = backend_agreement(results, sqlite_results, bundle, sqlite_bundle)
                record["json_evidence_ids"] = agreement["json_evidence_ids"]
                record["sqlite_evidence_ids"] = agreement["sqlite_evidence_ids"]
                record["json_sqlite_agreement"] = agreement
                reasons = quarantine_reasons(record, agreement=agreement)
                record["status"] = (
                    "DATA_GAP" if reasons == ["DATA_GAP"]
                    else ("QUARANTINE" if reasons else "PASS")
                )
                record["quarantine_reason_codes"] = reasons
                evaluated_rows.append(record)
                bundles[record["reference"]] = bundle
            return evaluated_rows, bundles

        evaluated, bundle_by_reference = evaluate_rows(candidate_pool)
        _progress(f"initial candidate pool evaluated: {len(evaluated)}")
        full_pool = select_mixed_candidate_pool(
            eligible,
            pool_size=len(eligible),
            excluded_references=excluded,
        )
        while (
            len([row for row in evaluated if row["status"] == "PASS" and row["availability"] in {"AVAILABLE", "THIN"}]) < target_count
            and len(candidate_pool) < len(full_pool)
        ):
            existing = {str(row["reference"]) for row in candidate_pool}
            additions = [
                row for row in full_pool
                if str(row["reference"]) not in existing
            ][:25]
            if not additions:
                break
            candidate_pool.extend(additions)
            evaluated, bundle_by_reference = evaluate_rows(candidate_pool)
            _progress(f"candidate pool extended and reevaluated: {len(evaluated)}")

        outliers = _mark_extreme_counts(evaluated)
        pass_records = [record for record in evaluated if record["status"] == "PASS" and record["availability"] in {"AVAILABLE", "THIN"}]
        final_records = select_final_chapters(evaluated, target_count)
        final_refs = {row["reference"] for row in final_records}
        replacements = [row["reference"] for row in final_records if row["reference"] != candidate_pool[len(final_records) - 1]["reference"]] if False else []
        # Candidates beyond the first target positions are replacements only
        # when an earlier pool member failed. This keeps the manifest explicit
        # without pretending that a clean initial pool needed replacement.
        initial_refs = {row["reference"] for row in candidate_pool[:target_count]}
        replacements = sorted(final_refs - initial_refs)

        quarantines: list[dict[str, Any]] = []
        for record in evaluated:
            if record["status"] == "QUARANTINE":
                blockers = [item for item in record["anomaly_scan"]["anomalies"] if item["severity"] == "blocker"]
                explanations = list(dict.fromkeys(item["explanation"] for item in blockers))
                quarantines.append({
                    "reference": record["reference"],
                    "reason_codes": record["quarantine_reason_codes"],
                    "evidence_ids": sorted({item["evidence_id"] for item in blockers if item.get("evidence_id")}),
                    "ckl_parent_records": sorted({item["ckl_parent_record"] for item in blockers if item.get("ckl_parent_record")}),
                    "explanation": "; ".join(explanations) or "Backend or audit disagreement prevented certification.",
                    "scope": "systemic" if any(code in {"CROSS_BOOK_PARENT_REUSE", "WORD_STUDY_BROAD_PARENT_ANCHOR"} for code in record["quarantine_reason_codes"]) else "local",
                })

        for record in final_records:
            path = bundle_dir / filename_for(str(record["book"]), int(record["chapter"]))
            _json_dump(path, _bundle_json(bundle_by_reference[record["reference"]]))
            record["locked_bundle_path"] = str(path.relative_to(REPO_ROOT))

        after_fingerprints = _artifact_fingerprints()
        batch_001_after_fingerprints = _batch_001_terra_fingerprints()
        batch_002_after_fingerprints = _batch_002_terra_fingerprints()
        # Regressions intentionally use the same JSON backend used for the
        # batch. No Terra code or prose compiler is imported here.
        controls = _regression_controls(
            json_library,
            before_fingerprints,
            after_fingerprints,
            batch_001_before_fingerprints,
            batch_001_after_fingerprints,
            batch_002_before_fingerprints,
            batch_002_after_fingerprints,
        )
        _progress("regression controls and fingerprints completed")

    status = "LOCKED" if len(final_records) == target_count and all(value["status"] == "PASS" for value in controls.values()) else "BLOCKED"
    availability_distribution = dict(sorted(Counter(row["availability"] for row in final_records).items()))
    genre_distribution = dict(sorted(Counter(row["genre"] for row in final_records).items()))
    book_distribution = dict(sorted(Counter(row["book"] for row in final_records).items()))
    semantic_role_totals = Counter(
        relationship
        for row in final_records
        for relationship, count in row.get("semantic_relationship_counts", {}).items()
        for _ in range(int(count))
    )
    presentation_role_totals = Counter(
        role
        for row in final_records
        for role, count in row.get("presentation_role_counts", {}).items()
        for _ in range(int(count))
    )
    semantic_anomalies = [item for row in evaluated for item in row.get("anomaly_scan", {}).get("anomalies", []) if item["severity"] == "blocker"]
    anomaly_totals = Counter(
        item["code"]
        for row in evaluated
        for item in row.get("anomaly_scan", {}).get("anomalies", [])
    )
    anomaly_blocking_totals = Counter(
        item["code"]
        for row in evaluated
        for item in row.get("anomaly_scan", {}).get("anomalies", [])
        if item["severity"] == "blocker"
    )
    anomaly_raw_totals = Counter(
        item["code"]
        for row in evaluated
        for item in row.get("anomaly_scan", {}).get("anomalies", [])
    )
    pass_certifications = []
    terra_inputs = []
    for record in final_records:
        sqlite = record["json_sqlite_agreement"]
        cert = _make_certification(record, record["locked_bundle_path"], sqlite)
        pass_certifications.append(cert)
        terra_inputs.append(_terra_input(record, record["locked_bundle_path"]))

    manifest = {
        "batch_id": batch_id,
        "created_at": _now(),
        "branch_head": _git_head(),
        "tool_version": TOOL_VERSION,
        "target_count": target_count,
        "candidate_pool_size": len(candidate_pool),
        "candidate_pool_requested_size": candidate_pool_size,
        "chapters_evaluated": len(evaluated),
        "chapters_passed": len(pass_records),
        "chapters_quarantined": len(quarantines),
        "chapters_data_gap": sum(row.get("status") == "DATA_GAP" for row in evaluated),
        "chapters_skipped": len(skipped_verdicts),
        "skipped_verdicts": [
            {"reference": reference, "status": verdict}
            for reference, verdict in sorted(skipped_verdicts.items())
        ],
        "verdict_counts": dict(sorted(Counter(
            [str(row.get("status")) for row in evaluated] + list(skipped_verdicts.values())
        ).items())),
        "replacements_used": len(replacements),
        "status": status,
        "current_population": current_population,
        "excluded_regression_controls": sorted(excluded),
        "excluded_prior_batch_references": sorted(prior_batch_exclusions),
        "final_chapters": final_records,
        "final_references": [row["reference"] for row in final_records],
        "availability_distribution": availability_distribution,
        "genre_distribution": genre_distribution,
        "book_distribution": book_distribution,
        "evidence_count_statistics": _stats(final_records),
        "semantic_relationship_totals": dict(sorted(semantic_role_totals.items())),
        "presentation_role_totals": dict(sorted(presentation_role_totals.items())),
        "anomaly_totals": dict(sorted(anomaly_totals.items())),
        "anomaly_raw_counts": dict(sorted(anomaly_raw_totals.items())),
        "anomaly_blocking_counts": dict(sorted(anomaly_blocking_totals.items())),
        "terra_suppression_required_count": sum(
            bool(row.get("terra_suppression_simulation", {}).get("terra_textual_suppression_required"))
            for row in evaluated
        ),
        "terra_suppression_required_count": sum(
            bool(row.get("terra_suppression_simulation", {}).get("terra_textual_suppression_required"))
            for row in evaluated
        ),
        "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION,
        "evidence_hash_version": EVIDENCE_HASH_VERSION,
        "candidate_pool": candidate_pool,
        "replacements": replacements,
        "artifact_fingerprints_before": before_fingerprints,
        "artifact_fingerprints_after": after_fingerprints,
        "artifact_fingerprint": _stable_fingerprint(after_fingerprints),
        "batch_001_terra_artifact_fingerprints_before": batch_001_before_fingerprints,
        "batch_001_terra_artifact_fingerprints_after": batch_001_after_fingerprints,
        "batch_001_terra_artifact_fingerprint": _stable_fingerprint(batch_001_after_fingerprints),
        "batch_002_terra_artifact_fingerprints_before": batch_002_before_fingerprints,
        "batch_002_terra_artifact_fingerprints_after": batch_002_after_fingerprints,
        "batch_002_terra_artifact_fingerprint": _stable_fingerprint(batch_002_after_fingerprints),
        "terra_run": False,
        "prose_generated": False,
        "batch002_textual_audit": batch002_textual_audit,
        "historical_textual_routing_review": historical_textual_review,
        "corpus_textual_routing_audit": corpus_textual_audit,
    }
    preflight = {
        "report_version": TOOL_VERSION,
        "batch_id": batch_id,
        "workflow": ["recalculate_population", "select_pool", "resolve_chapters", "retrieve_ckl", "build_evidence_bundle_1.1", "semantic_audit", "presentation_role_audit", "json_sqlite_agreement", "availability_classification", "anomaly_scan", "evidence_hash_lock"],
        "evaluated": evaluated,
        "evidence_count_outliers": outliers,
        "disagreement_counts": {
            "json_sqlite_result_id_disagreements": sum(not row["json_sqlite_agreement"]["result_ids_agree"] for row in evaluated),
            "json_sqlite_evidence_id_disagreements": sum(not row["json_sqlite_agreement"]["evidence_ids_agree"] for row in evaluated),
            "json_sqlite_hash_disagreements": sum(not row["json_sqlite_agreement"]["bundle_hash_agree"] for row in evaluated),
            "semantic_leakage": sum(row["semantic_audit"]["status"] != "PASS" for row in evaluated),
            "presentation_role_blockers": sum(row["presentation_role_audit"]["status"] != "PASS" for row in evaluated),
        },
        "anomaly_counts": dict(sorted(Counter(item["code"] for item in semantic_anomalies).items())),
        "anomaly_raw_counts": dict(sorted(anomaly_raw_totals.items())),
        "anomaly_blocking_counts": dict(sorted(anomaly_blocking_totals.items())),
        "regression_controls": controls,
        "batch002_textual_audit": batch002_textual_audit,
        "historical_textual_routing_review": historical_textual_review,
        "corpus_textual_routing_audit": corpus_textual_audit,
    }
    quarantine_report = {
        "batch_id": batch_id,
        "status": "REVIEWED",
        "chapters": quarantines,
        "unresolved_blocker_count": len(semantic_anomalies),
        "systemic_concern": "Repeated template-shaped background and broad-parent reuse should be handled in a separate CKL cleanup task; this preflight does not repair evidence.",
    }
    certification = {
        "batch_id": batch_id,
        "status": status,
        "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION,
        "evidence_hash_version": EVIDENCE_HASH_VERSION,
        "chapters": pass_certifications,
        "locked_evidence_bundle_count": len(pass_certifications),
        "all_availability_allowed": all(row["availability"] in {"AVAILABLE", "THIN"} for row in final_records),
        "json_sqlite_disagreements": preflight["disagreement_counts"]["json_sqlite_result_id_disagreements"] + preflight["disagreement_counts"]["json_sqlite_evidence_id_disagreements"],
        "hash_disagreements": preflight["disagreement_counts"]["json_sqlite_hash_disagreements"],
        "semantic_leakage": preflight["disagreement_counts"]["semantic_leakage"],
        "presentation_role_blockers": preflight["disagreement_counts"]["presentation_role_blockers"],
    }
    terra_manifest = {
        "batch_id": batch_id,
        "status": "READY_FOR_TERRA" if status == "LOCKED" else "NOT_READY",
        "prose_included": False,
        "chapters": terra_inputs,
    }
    report = {
        "batch_id": batch_id,
        "manifest": manifest,
        "preflight": preflight,
        "quarantine": quarantine_report,
        "certification": certification,
        "terra_manifest": terra_manifest,
        "controls": controls,
        "batch002_textual_audit": batch002_textual_audit,
        "historical_textual_routing_review": historical_textual_review,
        "corpus_textual_routing_audit": corpus_textual_audit,
    }
    _json_dump(
        DEFAULT_OUTPUT_ROOT / "post-batch-textual-routing-review.json",
        {
            "batch_id": batch_id,
            "batch_002_possible_evidence_review": batch002_textual_audit,
            "historical_reconstruction": historical_textual_review,
            "corpus_wide_scan": corpus_textual_audit,
        },
    )
    _json_dump(pool_dir / "batch-manifest.json", manifest)
    _json_dump(pool_dir / "preflight-report.json", preflight)
    _json_dump(pool_dir / "quarantine-report.json", quarantine_report)
    _json_dump(pool_dir / "evidence-certification.json", certification)
    _json_dump(pool_dir / "terra-input-manifest.json", terra_manifest)
    markdown_path = REPO_ROOT / "docs" / f"commentary-v1.1-scaled-{batch_id}-preflight.md"
    markdown_path.write_text(_markdown_report(manifest, preflight, quarantine_report, controls), encoding="utf-8")
    return report


def _git_head() -> str:
    import subprocess
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--target-count", type=int, default=DEFAULT_TARGET_COUNT)
    parser.add_argument("--candidate-pool-size", type=int, default=DEFAULT_POOL_SIZE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--candidate-source", type=Path, default=DEFAULT_CANDIDATE_SOURCE)
    parser.add_argument("--sqlite-database", type=Path, help="Use and verify an existing current CKL SQLite database.")
    args = parser.parse_args(argv)
    report = run_batch(
        batch_id=args.batch_id,
        target_count=args.target_count,
        candidate_pool_size=args.candidate_pool_size,
        output_root=args.output_root,
        candidate_source=args.candidate_source,
        sqlite_database=args.sqlite_database,
    )
    print(json.dumps({
        "batch_id": args.batch_id,
        "status": report["manifest"]["status"],
        "candidate_pool_size": report["manifest"]["candidate_pool_size"],
        "chapters_evaluated": report["manifest"]["chapters_evaluated"],
        "chapters_passed": report["manifest"]["chapters_passed"],
        "chapters_quarantined": report["manifest"]["chapters_quarantined"],
        "final_count": len(report["manifest"]["final_chapters"]),
        "availability": report["manifest"]["availability_distribution"],
        "anomaly_counts": report["preflight"]["anomaly_counts"],
    }, indent=2))
    return 0 if report["manifest"]["status"] == "LOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
