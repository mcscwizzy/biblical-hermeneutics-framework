#!/usr/bin/env python3
"""Build and lock a mixed-corpus Commentary v1.1 Luna evidence batch.

This is a Luna-side gate.  It retrieves and audits evidence only; it never
calls Terra, creates reader-facing prose, repairs CKL records, or modifies a
release artifact.  The output is an immutable-by-convention input manifest
for a future Terra run.
"""

from __future__ import annotations

import argparse
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
    presentation_role,
)
from tools.commentary_v11_canary import select_overview_item
from tools.commentary_v11_expansion import _book_genre, _signal_score
from tools.commentary_v11_low_information import audit as recalculate_low_information
from framework.canonical_library import CKLRepositoryConfig
from framework.canonical_library.database_builder import build_database, verify_database
from framework.canonical_library.scripture import (
    parse_scripture_references,
    scripture_reference_overlaps,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates"
DEFAULT_CANDIDATE_SOURCE = (
    REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.0.1"
)
DEFAULT_POOL_SIZE = 70
DEFAULT_TARGET_COUNT = 50
EVIDENCE_BUNDLE_VERSION = EVIDENCE_BUNDLE_CANDIDATE_VERSION
EVIDENCE_HASH_VERSION = "2"
TOOL_VERSION = "commentary-v11-scaled-preflight-1.0"

PRIMARY_CANARY_ROOT = (
    REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-terra"
)
SUPPLEMENTAL_CANARY_ROOT = PRIMARY_CANARY_ROOT / "supplemental-integrity-controls"

SECTION_ROLES = {
    "historical_context",
    "archaeology_geography",
    "language_literary",
    "chronology",
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


def _json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _canary_references() -> set[str]:
    primary = set()
    cert = REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1" / "evidence-certification-commentary_canary.json"
    if cert.exists():
        primary.update(str(row["reference"]) for row in json.loads(cert.read_text())["chapters"])
    primary.update({"1 Samuel 28"})
    return primary


def _artifact_fingerprints() -> dict[str, str]:
    paths = sorted(PRIMARY_CANARY_ROOT.glob("chapters/*.json"))
    paths += sorted(SUPPLEMENTAL_CANARY_ROOT.glob("chapters/*.json"))
    result: dict[str, str] = {}
    for path in paths:
        result[str(path.relative_to(REPO_ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


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
    return _book_genre(book)


def select_mixed_candidate_pool(
    rows: Sequence[Mapping[str, Any]],
    *,
    pool_size: int = DEFAULT_POOL_SIZE,
    excluded_references: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Select a ranked, genre/availability-mixed pool without book dominance."""

    excluded = set(excluded_references)
    ranked = [_rank_row(row) for row in rows if str(row["reference"]) not in excluded]
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
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


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
    role_counts = Counter(str((item.relevance_metadata or {}).get("presentation_role") or "UNASSIGNED") for item in bundle.evidence_items)
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
        "presentation_section_roles": sorted(role_counts),
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
        "anomaly_scan": {"status": "PASS" if not [a for a in anomalies if a["severity"] == "blocker"] else "FAIL", "anomalies": anomalies},
        "source_parent_records": sorted(parent_records),
    }


def _bundle_json(bundle: Any) -> dict[str, Any]:
    return bundle.to_dict()


def _stats(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = [int(row["evidence_count"]) for row in records]
    return {
        "min": min(values) if values else 0,
        "median": median(values) if values else 0,
        "mean": round(mean(values), 2) if values else 0,
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
        "semantic_audit": "PASS",
        "presentation_role_audit": "PASS",
        "anomaly_scan": "PASS",
        "lock_status": "LOCKED",
        "evidence_bundle_path": bundle_path,
    }


def _terra_input(record: Mapping[str, Any], bundle_path: str) -> dict[str, Any]:
    return {
        "reference": record["reference"],
        "canonical_text_input_locator": f"bible.resolve_chapter({record['book']!r}, {record['chapter']})",
        "locked_evidence_bundle_hash": record["evidence_hash"],
        "availability": record["availability"],
        "allowed_section_roles": record["presentation_section_roles"],
        "evidence_bundle_path": bundle_path,
        "evidence_reconstruction": {
            "function": "bhf_agent.chapter_commentary.evidence_bundling.get_chapter_evidence_bundle",
            "arguments": {"book": record["book"], "chapter": record["chapter"], "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION},
            "verify_hash_before_generation": True,
        },
        "candidate_output_filename": filename_for(str(record["book"]), int(record["chapter"])),
    }


def _markdown_report(manifest: Mapping[str, Any], preflight: Mapping[str, Any], quarantines: Mapping[str, Any], controls: Mapping[str, Any]) -> str:
    final = manifest["final_chapters"]
    anomaly_counts = Counter(code for row in preflight["evaluated"] for code in [a["code"] for a in row.get("anomaly_scan", {}).get("anomalies", [])])
    lines = [
        "# Commentary v1.1 Scaled Batch 001 Evidence Preflight",
        "",
        "This is a Luna deterministic evidence certification. Terra was not run and no reader-facing prose was generated.",
        "",
        "## Selection and population",
        "",
        f"- Candidate pool: {manifest['candidate_pool_size']} chapters; target: {manifest['target_count']}; evaluated: {manifest['chapters_evaluated']}.",
        f"- Current deterministic low-information population: {manifest['current_population']['eligible']} eligible and {manifest['current_population']['insufficient']} insufficient (historical reference: 935 / 153).",
        f"- Mixed selection: genre/availability round-robin, reader-benefit signals for ordering only, maximum five chapters per book in the pool.",
        f"- Replacements used: {manifest['replacements_used']}.",
        "",
        "## Final certification",
        "",
        f"- Status: **{manifest['status']}**",
        f"- Final locked chapters: {len(final)}",
        f"- Availability: {manifest['availability_distribution']}",
        f"- Genre: {manifest['genre_distribution']}",
        f"- Evidence count statistics: {manifest['evidence_count_statistics']}",
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
        "",
        "## Regression controls",
        "",
    ]
    for reference, result in controls.items():
        lines.append(f"- **{reference}** — {result['status']}: {result['summary']}")
    lines += [
        "",
        "## Systemic CKL concern",
        "",
        "Template-shaped CKL background and cross-testament reception records remain a systemic review surface. This batch quarantines only deterministic semantic/presentation blockers; it does not repair CKL records. Any repeated template or broad-parent pattern should be handled in a separate Luna evidence-cleanup task.",
        "",
        "The batch is eligible for a future Terra Medium Batch 001 generation only after the locked manifest is consumed and its hashes are rechecked immediately before generation.",
        "",
    ]
    return "\n".join(lines)


def _regression_controls(json_library: Any, before: Mapping[str, str], after: Mapping[str, str]) -> dict[str, Any]:
    controls: dict[str, Any] = {}
    for book, chapter in (("Genesis", 1), ("Zephaniah", 1), ("Luke", 1), ("Leviticus", 1), ("1 Samuel", 28), ("Numbers", 3)):
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
    return controls


def run_batch(
    *,
    batch_id: str,
    target_count: int,
    candidate_pool_size: int,
    output_root: Path,
    candidate_source: Path = DEFAULT_CANDIDATE_SOURCE,
) -> dict[str, Any]:
    output_root = output_root if output_root.is_absolute() else (REPO_ROOT / output_root)
    output_root = output_root.resolve()
    before_fingerprints = _artifact_fingerprints()
    current = recalculate_low_information(candidate_source)
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
    eligible = _eligible_rows(current)
    candidate_pool = select_mixed_candidate_pool(eligible, pool_size=candidate_pool_size, excluded_references=excluded)

    pool_dir = output_root / batch_id
    bundle_dir = pool_dir / "evidence-bundles"
    pool_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"bhf-{batch_id}-sqlite-") as temp_dir:
        db_path = Path(temp_dir) / "ckl.sqlite"
        build_database(REPO_ROOT / "framework" / "canonical_library", db_path)
        verify_database(db_path, root=REPO_ROOT / "framework" / "canonical_library")
        json_library = load_canonical_library(config=CKLRepositoryConfig(backend="json", json_root=str(REPO_ROOT / "framework" / "canonical_library")))
        sqlite_library = load_canonical_library(config=CKLRepositoryConfig(backend="sqlite", database_path=str(db_path), json_root=str(REPO_ROOT / "framework" / "canonical_library"), stale_database_policy="ignore"))

        raw_records: list[dict[str, Any]] = []
        for row in candidate_pool:
            bundle, results = _build_bundle(json_library, str(row["book"]), int(row["chapter"]))
            parent_records = _parent_records(json_library, results)
            for parent_id, data in parent_records.items():
                usage = next((entry for entry in raw_records if entry.get("_parent_id") == parent_id), None)
                if usage is None:
                    raw_records.append({"_parent_id": parent_id, "books": [], "references": []})
                    usage = raw_records[-1]
                if row["book"] not in usage["books"]:
                    usage["books"].append(row["book"])
                usage["references"].append(row["reference"])
        parent_usage = {entry["_parent_id"]: {"books": entry["books"], "references": entry["references"]} for entry in raw_records}

        evaluated: list[dict[str, Any]] = []
        bundle_by_reference: dict[str, Any] = {}
        json_ids_by_reference: dict[str, list[str]] = {}
        sqlite_ids_by_reference: dict[str, list[str]] = {}
        for row in candidate_pool:
            book, chapter = str(row["book"]), int(row["chapter"])
            bundle, results = _build_bundle(json_library, book, chapter)
            sqlite_bundle, sqlite_results = _build_bundle(sqlite_library, book, chapter)
            record = _chapter_record(
                row, bundle, library=json_library, results=results,
                json_bundle=bundle, sqlite_bundle=None, parent_usage=parent_usage,
            )
            agreement = backend_agreement(results, sqlite_results, bundle, sqlite_bundle)
            ids_agree = agreement["result_ids_agree"]
            evidence_ids_agree = agreement["evidence_ids_agree"]
            hashes_agree = agreement["bundle_hash_agree"]
            json_evidence_ids = agreement["json_evidence_ids"]
            sqlite_evidence_ids = agreement["sqlite_evidence_ids"]
            record["json_evidence_ids"] = json_evidence_ids
            record["sqlite_evidence_ids"] = sqlite_evidence_ids
            record["json_sqlite_agreement"] = agreement
            record["status"] = "DATA_GAP" if record["availability"] == EvidenceAvailability.DATA_GAP.value else "PASS"
            blockers = [item for item in record["anomaly_scan"]["anomalies"] if item["severity"] == "blocker"]
            reasons = quarantine_reasons(record, agreement=agreement)
            record["status"] = "DATA_GAP" if reasons == ["DATA_GAP"] else ("QUARANTINE" if reasons else "PASS")
            record["quarantine_reason_codes"] = reasons
            evaluated.append(record)
            bundle_by_reference[record["reference"]] = bundle
            json_ids_by_reference[record["reference"]] = json_evidence_ids
            sqlite_ids_by_reference[record["reference"]] = sqlite_evidence_ids

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
                quarantines.append({
                    "reference": record["reference"],
                    "reason_codes": record["quarantine_reason_codes"],
                    "evidence_ids": sorted({item["evidence_id"] for item in blockers if item.get("evidence_id")}),
                    "ckl_parent_records": sorted({item["ckl_parent_record"] for item in blockers if item.get("ckl_parent_record")}),
                    "explanation": "; ".join(item["explanation"] for item in blockers) or "Backend or audit disagreement prevented certification.",
                    "scope": "systemic" if any(code in {"CROSS_BOOK_PARENT_REUSE", "WORD_STUDY_BROAD_PARENT_ANCHOR"} for code in record["quarantine_reason_codes"]) else "local",
                })

        for record in final_records:
            path = bundle_dir / filename_for(str(record["book"]), int(record["chapter"]))
            _json_dump(path, _bundle_json(bundle_by_reference[record["reference"]]))
            record["locked_bundle_path"] = str(path.relative_to(REPO_ROOT))

        after_fingerprints = _artifact_fingerprints()
        # Regressions intentionally use the same JSON backend used for the
        # batch. No Terra code or prose compiler is imported here.
        controls = _regression_controls(json_library, before_fingerprints, after_fingerprints)

    status = "LOCKED" if len(final_records) == target_count and all(value["status"] == "PASS" for value in controls.values()) else "BLOCKED"
    availability_distribution = dict(sorted(Counter(row["availability"] for row in final_records).items()))
    genre_distribution = dict(sorted(Counter(row["genre"] for row in final_records).items()))
    book_distribution = dict(sorted(Counter(row["book"] for row in final_records).items()))
    semantic_anomalies = [item for row in evaluated for item in row.get("anomaly_scan", {}).get("anomalies", []) if item["severity"] == "blocker"]
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
        "replacements_used": len(replacements),
        "status": status,
        "current_population": current_population,
        "excluded_regression_controls": sorted(excluded),
        "final_chapters": final_records,
        "final_references": [row["reference"] for row in final_records],
        "availability_distribution": availability_distribution,
        "genre_distribution": genre_distribution,
        "book_distribution": book_distribution,
        "evidence_count_statistics": _stats(final_records),
        "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION,
        "evidence_hash_version": EVIDENCE_HASH_VERSION,
        "candidate_pool": candidate_pool,
        "replacements": replacements,
        "artifact_fingerprints_before": before_fingerprints,
        "artifact_fingerprints_after": after_fingerprints,
        "artifact_fingerprint": _stable_fingerprint(after_fingerprints),
        "terra_run": False,
        "prose_generated": False,
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
        "regression_controls": controls,
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
    }
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
    args = parser.parse_args(argv)
    report = run_batch(
        batch_id=args.batch_id,
        target_count=args.target_count,
        candidate_pool_size=args.candidate_pool_size,
        output_root=args.output_root,
        candidate_source=args.candidate_source,
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
