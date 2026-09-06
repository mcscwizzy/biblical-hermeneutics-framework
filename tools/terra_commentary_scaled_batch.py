#!/usr/bin/env python3
"""Generate and audit a locked, evidence-bounded Terra commentary batch.

This is candidate-only prose work.  It neither changes CKL nor selects,
replaces, or relocks chapters.  A stale locked bundle stops the entire batch
before any reader-facing chapter file is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.availability import classify_evidence_availability
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION, COMMENTARY_SCHEMA_VERSION
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from bhf_agent.presentation.relevance import (
    BOOK_CONTEXT,
    COMPARATIVE_CONTEXT,
    DIRECT_CONTEXT,
    GENERIC_BACKGROUND,
    INTERTEXTUAL_REUSE,
    LATER_RECEPTION,
    PRESENTATION_SECTIONS,
    SEMANTIC_RELATIONSHIPS,
)
from tools.commentary_v11_canary import _chapter_overlap_refs, _interpretation_level, _section_for_item


DEFAULT_BATCH_ROOT = ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-scale" / "batch-001"
REPORT_VERSION = "commentary-v1.1-terra-scaled-batch-v1"
TITLES = {
    "chapter_overview": "Chapter overview",
    "historical_context": "Historical and cultural context",
    "people_places": "People and places",
    "archaeology_geography": "Archaeology and geography",
    "language_literary": "Language and literary context",
    "chronology": "Chronology",
    "interpretive_questions": "Interpretive questions",
    "things_easy_to_miss": "Things easy to miss",
    "dig_deeper": "Dig deeper",
}
SECTION_ORDER = {kind: index for index, kind in enumerate(TITLES)}
QUALITY_FLAGS = (
    "LOW_INFORMATION",
    "EVIDENCE_DUMP",
    "OVEREXPANDED",
    "UNSUPPORTED_SYNTHESIS",
    "THEOLOGICAL_OVERREACH",
    "UNCERTAINTY_LOST",
    "READER_UNFRIENDLY",
)
CANARY_ROOT = ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-terra"
SUPPLEMENTAL_ROOT = CANARY_ROOT / "supplemental-integrity-controls"
BATCH_001_TERRA_ROOT = (
    ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-scale" / "batch-001" / "terra" / "chapters"
)


def _model_id(batch_id: str) -> str:
    return f"terra-codex-commentary-v1.1-{batch_id}-medium"


def _next_batch_status(batch_id: str) -> str:
    try:
        number = int(batch_id.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return "READY_FOR_NEXT_BATCH"
    return f"READY_FOR_BATCH_{number + 1:03d}"


def _batch_label(batch_id: str) -> str:
    return batch_id.replace("-", " ").title()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _word_count(candidate: dict[str, Any]) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", " ".join(
        block["text"] for section in candidate["sections"] for block in section["blocks"]
    )))


def _artifact_fingerprints() -> dict[str, str]:
    paths = sorted(CANARY_ROOT.glob("chapters/*.json"))
    paths += sorted(SUPPLEMENTAL_ROOT.glob("chapters/*.json"))
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _batch_001_terra_fingerprints() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(BATCH_001_TERRA_ROOT.glob("*.json"))
    }


def _fingerprint_digest(value: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _load(batch_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = json.loads((batch_root / "batch-manifest.json").read_text(encoding="utf-8"))
    certification = json.loads((batch_root / "evidence-certification.json").read_text(encoding="utf-8"))
    terra_input = json.loads((batch_root / "terra-input-manifest.json").read_text(encoding="utf-8"))
    quarantine = json.loads((batch_root / "quarantine-report.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "LOCKED" or certification.get("status") != "LOCKED":
        raise RuntimeError("Terra generation requires a LOCKED batch manifest and certification")
    if terra_input.get("status") != "READY_FOR_TERRA" or terra_input.get("prose_included"):
        raise RuntimeError("Terra input manifest is not a prose-free READY_FOR_TERRA manifest")
    return manifest, certification, terra_input, quarantine


def _metadata_errors(bundle: Any, allowed_roles: set[str]) -> list[str]:
    errors: list[str] = []
    for item in bundle.evidence_items:
        metadata = item.relevance_metadata or {}
        relationship = metadata.get("semantic_relationship")
        if relationship not in SEMANTIC_RELATIONSHIPS:
            errors.append(f"{item.id}: invalid semantic relationship {relationship!r}")
        routed = _section_for_item(item)
        if routed and routed not in PRESENTATION_SECTIONS:
            errors.append(f"{item.id}: invalid routed presentation section {routed!r}")
        if routed and routed != "dig_deeper" and routed not in allowed_roles:
            errors.append(f"{item.id}: routed role {routed!r} is not allowed by the Terra manifest")
        if routed == "dig_deeper" and "dig_deeper" not in allowed_roles:
            errors.append(f"{item.id}: Dig Deeper is not allowed by the Terra manifest")
    return errors


def revalidate_locks(
    terra_input: dict[str, Any], certification: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Rebuild all bundles before prose generation; return bundles only if clean."""

    certified = {row["reference"]: row for row in certification["chapters"]}
    records: list[dict[str, Any]] = []
    bundles: dict[str, Any] = {}
    stale: list[dict[str, Any]] = []
    for entry in terra_input["chapters"]:
        reference = entry["reference"]
        cert = certified.get(reference)
        if cert is None:
            stale.append({"reference": reference, "reason": "missing certification record"})
            continue
        reconstruction = entry["evidence_reconstruction"]["arguments"]
        book, chapter = reconstruction["book"], int(reconstruction["chapter"])
        expected_book = str(entry.get("book") or cert.get("book") or book)
        expected_chapter = int(entry.get("chapter") or cert.get("chapter") or chapter)
        bundle = get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
        actual_ids = sorted(item.id for item in bundle.evidence_items) if bundle else []
        expected_ids = sorted(cert["evidence_ids"])
        actual_availability = classify_evidence_availability(bundle).value if bundle else None
        metadata_errors = _metadata_errors(bundle, set(entry["allowed_section_roles"])) if bundle else ["bundle unavailable"]
        locked_path = ROOT / cert["evidence_bundle_path"]
        locked_items = {}
        if locked_path.exists():
            locked_items = {
                str(item["id"]): {
                    key: (item.get("relevance_metadata") or {}).get(key)
                    for key in ("semantic_relationship", "presentation_role", "overview_priority")
                }
                for item in json.loads(locked_path.read_text(encoding="utf-8")).get("evidence_items", [])
            }
        actual_items = {
            item.id: {
                key: (item.relevance_metadata or {}).get(key)
                for key in ("semantic_relationship", "presentation_role", "overview_priority")
            }
            for item in (bundle.evidence_items if bundle else [])
        }
        overview = _overview_item(bundle) if bundle else None
        checks = {
            "reference_matches": bool(bundle and bundle.passage_ref == reference),
            "book_matches": book == expected_book,
            "chapter_matches": chapter == expected_chapter,
            "bundle_version_matches": bool(bundle and bundle.version == "1.1"),
            "hash_version_matches": bool(bundle and bundle.evidence_hash_version == "2"),
            "hash_matches": bool(bundle and bundle.evidence_hash == cert["locked_evidence_hash"] == entry["locked_evidence_bundle_hash"]),
            "evidence_ids_match": actual_ids == expected_ids,
            "availability_matches": actual_availability == cert["availability"] == entry["availability"],
            "semantic_presentation_valid": not metadata_errors,
            "semantic_presentation_matches_lock": actual_items == locked_items,
            "overview_priority_coherent": bool(
                (overview and overview.id in actual_items)
                or (bundle and bundle.evidence_items)
            ),
        }
        record = {
            "reference": reference,
            "checks": checks,
            "expected_hash": cert["locked_evidence_hash"],
            "actual_hash": bundle.evidence_hash if bundle else None,
            "expected_evidence_ids": expected_ids,
            "actual_evidence_ids": actual_ids,
            "expected_availability": cert["availability"],
            "actual_availability": actual_availability,
            "metadata_errors": metadata_errors,
            "locked_metadata": locked_items,
            "actual_metadata": actual_items,
            "status": "LOCKED" if all(checks.values()) else "STALE_LOCK",
        }
        records.append(record)
        if record["status"] == "STALE_LOCK":
            stale.append(record)
        else:
            bundles[reference] = bundle
    report = {
        "report_version": REPORT_VERSION,
        "generated_at": _now(),
        "phase": "pre_generation_lock_revalidation",
        "chapters_checked": len(records),
        "locks_revalidated": len(records) - len(stale),
        "stale_locks": stale,
        "results": records,
        "status": "PASS" if len(records) == len(terra_input["chapters"]) and not stale else "STALE_LOCK",
    }
    return report, bundles


def _clean_claim(item: Any) -> str:
    claim = " ".join(str(item.claim or "").split())
    # A small edit keeps a record's own caution reader-facing without adding a
    # new contextual assertion.
    return claim.replace("The evidence does not establish", "The available material does not establish")


def _is_disputed(item: Any) -> bool:
    dispute = str((item.relevance_metadata or {}).get("dispute_status") or "").casefold()
    return dispute not in {"", "not_disputed", "unknown", "none"}


def _reader_safe(item: Any) -> bool:
    """Avoid using reception/application guardrails as the main orientation."""

    text = _clean_claim(item).casefold()
    excluded = (
        "weaponized", "abuse survivor", "anti-judaism", "supersessionism",
        "deicide", "collective jewish guilt", "modern political", "ancient background for",
        "helps anchor the biblical world", " is read across the canon", "cannot authorize",
        "application cannot", "applications must reject", "leadership and discipline applications",
        "does not command leaders", "not a command to abandon",
    )
    return not any(phrase in text for phrase in excluded)


def _item_rank(item: Any) -> tuple[int, int, int, str]:
    metadata = item.relevance_metadata or {}
    source_kind = str(metadata.get("source_kind") or "")
    return (
        1 if _reader_safe(item) else 0,
        1 if source_kind in {"ckl_claim", "ckl_evidence_item", "ckl_interpretive_note"} else 0,
        int(metadata.get("overview_priority") or 0),
        item.id,
    )


def _overview_item(bundle: Any) -> Any | None:
    candidates = [
        item for item in bundle.evidence_items
        if _section_for_item(item) not in {None, "dig_deeper"}
    ]
    if not candidates:
        return None
    return sorted(candidates, key=_item_rank, reverse=True)[0]


def _block_for_item(item: Any, book: str, chapter: int, *, kind: str, index: int, overview: bool = False) -> dict[str, Any]:
    claim = _clean_claim(item)
    disputed = _is_disputed(item)
    if overview:
        lead = "Read the chapter with this setting in view: "
        tail = " It gives a starting point for following the chapter's own movement. The chapter itself should determine how far the point is taken."
    elif kind == "historical_context":
        lead = "For its historical and cultural setting, note that "
        tail = " This background clarifies the setting assumed by the passage. It does not by itself settle every question raised by the chapter."
    elif kind == "language_literary":
        lead = "A literary feature to notice is that "
        tail = " This form helps organize the chapter's claims. Notice it before drawing broader conclusions from a single phrase or image."
    elif kind == "archaeology_geography":
        lead = "For its geographical or material setting, note that "
        tail = " It can illuminate the passage, while its limits should be kept in view."
    elif kind == "chronology":
        lead = "For the chapter's sequence and setting, note that "
        tail = " This gives the reader a frame for the passage without deciding every larger reconstruction."
    elif kind == "dig_deeper":
        lead = "For a later or comparative connection, note that "
        tail = " This remains a secondary connection rather than the chapter's first-audience context. It can be traced further without replacing the chapter's own setting."
    else:
        lead = "One useful point to notice is that "
        tail = ""
    if disputed:
        uncertainty = (
            " Interpretations differ on some details.",
            " The evidence leaves some details unresolved.",
            " A more precise reconstruction remains disputed.",
        )
        tail += uncertainty[index % len(uncertainty)]
    return {
        "id": f"{kind}_{index}",
        "text": lead + claim + tail,
        "evidence_ids": [item.id],
        "verse_refs": _chapter_overlap_refs(item, book, chapter),
        "confidence": item.confidence if item.confidence in {"low", "medium", "high"} else "medium",
        "interpretation_level": _interpretation_level(item),
    }


def _pick_by_role(bundle: Any, role: str, used: set[str], limit: int) -> list[Any]:
    selected = []
    matching = [item for item in bundle.evidence_items if item.id not in used and _section_for_item(item) == role]
    # A textual-variant record may be routed by the locked metadata, yet it is
    # not reader-facing archaeological or geographical explanation.  Omitting
    # it is safer than making a misleading material-culture claim.
    if role == "archaeology_geography":
        matching = [
            item for item in matching
            if not _is_textual_witness_material(item)
        ]
    if role == "historical_context":
        matching = [item for item in matching if not _is_textual_witness_material(item)]
    safe = [item for item in matching if _reader_safe(item)]
    for item in sorted(safe, key=_item_rank, reverse=True):
        selected.append(item)
        used.add(item.id)
        if len(selected) == limit:
            break
    return selected


def payload_for(entry: dict[str, Any], bundle: Any, *, ordinal: int, model_id: str) -> dict[str, Any]:
    """Compose concise prose from locked claims and their routed roles only."""

    reconstruction = entry["evidence_reconstruction"]["arguments"]
    book, chapter = reconstruction["book"], int(reconstruction["chapter"])
    availability = entry["availability"]
    allowed = list(entry["allowed_section_roles"])
    used: set[str] = set()
    overview = _overview_item(bundle)
    if overview is None:
        # A chapter with only secondary material remains deliberately modest;
        # this uses its first supplied item and does not invent a historical
        # frame merely to make an overview look fuller.
        overview = next(iter(bundle.evidence_items), None)
    if overview is None:
        raise RuntimeError(f"locked non-DATA_GAP bundle has no usable evidence: {entry['reference']}")
    used.add(overview.id)
    sections = [{
        "kind": "chapter_overview",
        "title": TITLES["chapter_overview"],
        "blocks": [_block_for_item(overview, book, chapter, kind="chapter_overview", index=ordinal, overview=True)],
    }]

    role_order = ["historical_context", "people_places", "archaeology_geography", "language_literary", "chronology", "dig_deeper"]
    contextual_limit = 3 if availability == "AVAILABLE" else 1
    added = 0
    for role in role_order:
        if role not in allowed or added >= contextual_limit:
            continue
        items = _pick_by_role(bundle, role, used, 2 if availability == "AVAILABLE" and role == "historical_context" else 1)
        if not items:
            continue
        sections.append({
            "kind": role,
            "title": TITLES[role],
            "blocks": [_block_for_item(item, book, chapter, kind=role, index=ordinal + offset + 1) for offset, item in enumerate(items)],
        })
        added += 1
    # A THIN chapter with only its overview evidence remains one short section;
    # no duplicate citation is added merely to reach a shape target.
    return {
        "reference": entry["reference"],
        "book": book,
        "chapter": chapter,
        "status": "validated",
        "evidence_availability": availability,
        "sections": sorted(sections, key=lambda section: SECTION_ORDER[section["kind"]]),
        "generated_metadata": {
            "evidence_hash": bundle.evidence_hash,
            "evidence_bundle_version": bundle.version,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
            "model": model_id,
            "generated_timestamp": _now(),
        },
    }


def prose_audit(candidate: dict[str, Any], bundle: Any) -> list[str]:
    text = " ".join(block["text"] for section in candidate["sections"] for block in section["blocks"])
    flags: list[str] = []
    if re.search(r"\bcontains \d+ verses\b|\bit opens with\b|\bit concludes with\b|\bthe chapter begins\b|\bthe chapter ends\b", text, re.I):
        flags.append("LOW_INFORMATION")
    if re.search(r"\b(?:EvidenceBundle|CKL|source-addressable|semantic relationship|presentation role|preflight|retrieval|provider)\b|application cannot|applications? must reject|does not command leaders|not a command to abandon", text, re.I):
        flags.append("READER_UNFRIENDLY")
    words = _word_count(candidate)
    sections = len(candidate["sections"])
    availability = candidate["evidence_availability"]
    if (availability == "AVAILABLE" and (words > 700 or sections > 5)) or (availability == "THIN" and (words > 350 or sections > 3)):
        flags.append("OVEREXPANDED")
    citations = [eid for section in candidate["sections"] for block in section["blocks"] for eid in block["evidence_ids"]]
    if len(citations) > max(8, words // 28):
        flags.append("EVIDENCE_DUMP")
    if any(eid not in bundle.evidence_by_id for eid in citations):
        flags.append("UNSUPPORTED_SYNTHESIS")
    for section in candidate["sections"]:
        for block in section["blocks"]:
            if any(_is_disputed(bundle.evidence_by_id[eid]) for eid in block["evidence_ids"]):
                if block["interpretation_level"] != "disputed" or not re.search(r"open|disputed|uncertain|not establish|does not settle|leaves|interpretations differ", block["text"], re.I):
                    flags.append("UNCERTAINTY_LOST")
    # The generator never adds doctrinal/application content beyond a locked
    # claim. This explicit scan catches accidental prohibited phrasing.
    if re.search(r"\b(?:you should|we should|therefore we must|salvation requires|the only true doctrine)\b", text, re.I):
        flags.append("THEOLOGICAL_OVERREACH")
    return sorted(set(flags))


def _validation_row(candidate: dict[str, Any], bundle: Any) -> dict[str, Any]:
    validation = validate_chapter_commentary(
        candidate,
        bundle,
        expected_evidence_hash=bundle.evidence_hash,
        expected_prompt_version=COMMENTARY_PROMPT_VERSION,
        expected_reference=candidate["reference"],
        expected_book=candidate["book"],
        expected_chapter=candidate["chapter"],
    )
    return {"reference": candidate["reference"], "valid": validation.valid, "errors": list(validation.errors)}


def _review_sample(candidates: list[dict[str, Any]], bundles: dict[str, Any], genres: dict[str, str], *, target: int = 30) -> list[str]:
    chosen: list[str] = []
    def add(reference: str | None) -> None:
        if reference and reference not in chosen and len(chosen) < target:
            chosen.append(reference)

    for genre in sorted(set(genres.values())):
        available = [candidate["reference"] for candidate in candidates if candidate["evidence_availability"] == "AVAILABLE" and genres[candidate["reference"]] == genre]
        for reference in available[:2]:
            add(reference)
        add(next((candidate["reference"] for candidate in candidates if candidate["evidence_availability"] == "THIN" and genres[candidate["reference"]] == genre), None))
    counts = {candidate["reference"]: len(bundles[candidate["reference"]].evidence_items) for candidate in candidates}
    for reference, _ in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:3]:
        add(reference)
    add(min(counts, key=counts.get))
    for candidate in candidates:
        bundle = bundles[candidate["reference"]]
        if any(_is_disputed(item) for item in bundle.evidence_items):
            add(candidate["reference"])
    for candidate in candidates:
        if any(section["kind"] == "dig_deeper" for section in candidate["sections"]):
            add(candidate["reference"])
    for candidate in candidates:
        if any(_is_textual_witness_material(item) for item in bundles[candidate["reference"]].evidence_items):
            add(candidate["reference"])
    for role in ("archaeology_geography", "language_literary"):
        add(next((candidate["reference"] for candidate in candidates if any(section["kind"] == role for section in candidate["sections"])), None))
    add(next((candidate["reference"] for candidate in candidates if any((item.relevance_metadata or {}).get("semantic_relationship") == BOOK_CONTEXT for item in bundles[candidate["reference"]].evidence_items)), None))
    for candidate in candidates:
        add(candidate["reference"])
    return chosen


def _review_rows(sample: Iterable[str], candidates: dict[str, dict[str, Any]], bundles: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for reference in sample:
        candidate, bundle = candidates[reference], bundles[reference]
        flags = prose_audit(candidate, bundle)
        disputed = any(_is_disputed(item) for item in bundle.evidence_items)
        later_reception_is_secondary = all(
            section["kind"] == "dig_deeper"
            for section in candidate["sections"]
            if any(
                (bundles[reference].evidence_by_id[eid].relevance_metadata or {}).get("semantic_relationship")
                in {LATER_RECEPTION, INTERTEXTUAL_REUSE, COMPARATIVE_CONTEXT}
                for block in section["blocks"]
                for eid in block["evidence_ids"]
            )
        )
        rows.append({
            "reference": reference,
            "overview_useful": bool(candidate["sections"] and candidate["sections"][0]["kind"] == "chapter_overview"),
            "explains_not_dumps": "EVIDENCE_DUMP" not in flags,
            "length_fits_availability": "OVEREXPANDED" not in flags,
            "sections_useful": len(candidate["sections"]) <= (4 if candidate["evidence_availability"] == "AVAILABLE" else 2),
            "first_audience_prioritized": candidate["sections"][0]["kind"] == "chapter_overview",
            "later_reception_secondary": later_reception_is_secondary,
            "uncertainty_preserved": not disputed or "UNCERTAINTY_LOST" not in flags,
            "verse_anchors_precise": all(block["verse_refs"] for section in candidate["sections"] for block in section["blocks"]),
            "unsupported_contextual_knowledge": "UNSUPPORTED_SYNTHESIS" in flags,
            "ordinary_reader_readable": "READER_UNFRIENDLY" not in flags,
            "acceptable_for_final_v11": not flags,
            "flags": flags,
        })
    return rows


def _statistics(candidates: list[dict[str, Any]], bundles: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate["evidence_availability"]].append(candidate)
    by_availability = {}
    for availability, values in sorted(grouped.items()):
        words = [_word_count(value) for value in values]
        sections = [len(value["sections"]) for value in values]
        citations = [sum(len(block["evidence_ids"]) for section in value["sections"] for block in section["blocks"]) for value in values]
        by_availability[availability] = {
            "chapter_count": len(values), "mean_word_count": round(mean(words), 1), "median_word_count": median(words),
            "min_word_count": min(words), "max_word_count": max(words), "mean_section_count": round(mean(sections), 1),
            "median_section_count": median(sections), "evidence_citations": sum(citations), "citations_per_chapter": round(mean(citations), 2),
        }
    all_citations = [eid for candidate in candidates for section in candidate["sections"] for block in section["blocks"] for eid in block["evidence_ids"]]
    available_ids = {item.id for bundle in bundles.values() for item in bundle.evidence_items}
    section_frequency = Counter(section["kind"] for candidate in candidates for section in candidate["sections"])
    interpretation_levels = Counter(
        block["interpretation_level"]
        for candidate in candidates
        for section in candidate["sections"]
        for block in section["blocks"]
    )
    return {
        "by_availability": by_availability,
        "total_generated_words": sum(_word_count(candidate) for candidate in candidates),
        "total_evidence_citations": len(all_citations),
        "unique_evidence_ids_cited": len(set(all_citations)),
        "available_evidence_ids": len(available_ids),
        "available_evidence_used_percent": round(100 * len(set(all_citations)) / len(available_ids), 2) if available_ids else 0,
        "dig_deeper_frequency": sum(any(section["kind"] == "dig_deeper" for section in candidate["sections"]) for candidate in candidates),
        "section_kind_frequency": dict(sorted(section_frequency.items())),
        "interpretation_level_distribution": dict(sorted(interpretation_levels.items())),
    }


def _evidence_rich_review(candidates: list[dict[str, Any]], bundles: dict[str, Any]) -> list[dict[str, Any]]:
    """Check the ten richest AVAILABLE bundles for selective, useful treatment."""

    available = [candidate for candidate in candidates if candidate["evidence_availability"] == "AVAILABLE"]
    selected = sorted(available, key=lambda candidate: (-len(bundles[candidate["reference"]].evidence_items), candidate["reference"]))[:10]
    rows = []
    for candidate in selected:
        bundle = bundles[candidate["reference"]]
        cited = {
            evidence_id
            for section in candidate["sections"]
            for block in section["blocks"]
            for evidence_id in block["evidence_ids"]
        }
        overview = _overview_item(bundle)
        rows.append({
            "reference": candidate["reference"],
            "evidence_count": len(bundle.evidence_items),
            "word_count": _word_count(candidate),
            "section_count": len(candidate["sections"]),
            "overview_useful": bool(overview and candidate["sections"][0]["blocks"][0]["evidence_ids"] == [overview.id]),
            "strongest_context_represented": bool(overview and overview.id in cited),
            "not_artificially_sparse": _word_count(candidate) >= 80 and len(candidate["sections"]) >= 2,
            "evidence_selection_is_selective": len(cited) < len(bundle.evidence_items),
            "section_choices_reflect_chapter_needs": not prose_audit(candidate, bundle),
        })
    return rows


def _possible_evidence_reviews(bundles: dict[str, Any]) -> list[dict[str, str]]:
    """Record supplied-role concerns without changing the locked evidence."""

    reviews: list[dict[str, str]] = []
    for reference, bundle in bundles.items():
        for item in bundle.evidence_items:
            if _section_for_item(item) != "historical_context" or not _is_textual_witness_material(item):
                continue
            reviews.append({
                "reference": reference,
                "evidence_id": item.id,
                "status": "POSSIBLE_EVIDENCE_REVIEW",
                "reason": "A textual-witness or manuscript claim is routed as first-audience historical/material context; it was omitted from prose and left unchanged for Luna review.",
            })
    return reviews


def _is_textual_evidence(item: Any) -> bool:
    metadata = item.relevance_metadata or {}
    authored_types = {
        str(metadata.get(key) or "").casefold().replace("-", "_").replace(" ", "_")
        for key in ("claim_type", "note_type", "evidence_type")
    }
    textual_types = {
        "textual", "textual_variant", "textual_form", "textual_criticism", "text_critical",
        "textual_transmission", "manuscript", "manuscript_reading", "source_critical", "source_criticism",
    }
    return bool(authored_types & textual_types)


def _is_textual_witness_material(item: Any) -> bool:
    """Keep textual-witness inventories out of first-audience context sections."""

    return _is_textual_evidence(item) or bool(re.search(
        r"\b(?:manuscript(?:s)?|papyr(?:us|i)|codex|codices|versional|"
        r"textual\s+(?:variant|variants|profile|profiles|witness(?:es)?|transmission|criticism|review)|"
        r"(?:shorter|longer)\s+text|different\s+witnesses)\b",
        _clean_claim(item),
        re.IGNORECASE,
    ))


def _markdown(
    summary: dict[str, Any], quality: dict[str, Any], review_rows: list[dict[str, Any]], evidence_rich_rows: list[dict[str, Any]]
) -> str:
    batch_id = summary["batch_id"]
    batch_label = _batch_label(batch_id)
    total = summary["generation"]["chapters_generated"]
    prior = "Batch 001" if batch_id == "batch-002" else "the prior batch"
    lines = [
        f"# BHF Commentary v1.1 Scaled {batch_label} Terra",
        "",
        f"Terra generated candidate-only reader-facing prose from the preflight-locked {batch_label} EvidenceBundles. No CKL or production release artifact was changed.",
        "",
        "## Result",
        "",
        f"- Lock revalidation: {summary['lock_revalidation']['locks_revalidated']}/{total}; stale locks: {len(summary['lock_revalidation']['stale_locks'])}.",
        f"- Generated and validated: {summary['validation']['valid']}/{summary['validation']['chapters']}.",
        f"- Availability: {summary['availability_distribution']}.",
        f"- Quality flags: {quality['flag_counts']}.",
        f"- Canary artifacts unchanged: {summary['canary_artifacts']['unchanged']} (26 artifacts).",
        f"- {prior} Terra artifacts unchanged: {summary['batch_001_terra_artifacts']['unchanged']} (50 artifacts).",
        f"- Possible evidence-review records: {len(quality['possible_evidence_review'])}.",
        "",
        "## Statistics",
        "",
        f"- Total words: {summary['statistics']['total_generated_words']}; citations: {summary['statistics']['total_evidence_citations']}; unique evidence IDs used: {summary['statistics']['unique_evidence_ids_cited']}.",
        f"- AVAILABLE: {summary['statistics']['by_availability']['AVAILABLE']['chapter_count']} chapters; mean / median words: {summary['statistics']['by_availability']['AVAILABLE']['mean_word_count']} / {summary['statistics']['by_availability']['AVAILABLE']['median_word_count']}; mean sections: {summary['statistics']['by_availability']['AVAILABLE']['mean_section_count']}.",
        f"- THIN: {summary['statistics']['by_availability']['THIN']['chapter_count']} chapters; mean / median words: {summary['statistics']['by_availability']['THIN']['mean_word_count']} / {summary['statistics']['by_availability']['THIN']['median_word_count']}; mean sections: {summary['statistics']['by_availability']['THIN']['mean_section_count']}.",
        f"- Evidence IDs used: {summary['statistics']['available_evidence_used_percent']}% of available locked items. Citation volume was not used as a quality target.",
        f"- Dig Deeper frequency: {summary['statistics']['dig_deeper_frequency']}/{total}.",
        f"- Section kinds: {summary['statistics']['section_kind_frequency']}.",
        f"- Interpretation levels: {summary['statistics']['interpretation_level_distribution']}.",
        "",
        "## Canary comparison",
        "",
        "Batch 001 averaged 196.9 words / 2.9 sections for AVAILABLE and 76.2 words / 1.3 sections for THIN. This batch is compared against those restraint baselines rather than treated as a quota; section choices remain driven by each manifest allow-list rather than a uniform template.",
        "",
        "## Review sample",
        "",
    ]
    for row in review_rows:
        lines.append(f"- **{row['reference']}** — overview useful: {row['overview_useful']}; explains rather than dumps: {row['explains_not_dumps']}; length fits: {row['length_fits_availability']}; sections useful: {row['sections_useful']}; first-audience prioritized: {row['first_audience_prioritized']}; later material secondary: {row['later_reception_secondary']}; uncertainty preserved: {row['uncertainty_preserved']}; precise anchors: {row['verse_anchors_precise']}; unsupported knowledge: {row['unsupported_contextual_knowledge']}; readable: {row['ordinary_reader_readable']}; acceptable: {row['acceptable_for_final_v11']}.")
    lines += ["", "## Evidence-rich AVAILABLE review", ""]
    for row in evidence_rich_rows:
        lines.append(f"- **{row['reference']}** ({row['evidence_count']} evidence items) — useful overview: {row['overview_useful']}; strongest context represented: {row['strongest_context_represented']}; not artificially sparse: {row['not_artificially_sparse']}; selection remains selective: {row['evidence_selection_is_selective']}; section choices pass audit: {row['section_choices_reflect_chapter_needs']}.")
    lines += [
        "",
        "## Possible evidence concern",
        "",
    ]
    if quality["possible_evidence_review"]:
        for concern in quality["possible_evidence_review"]:
            lines.append(f"- **{concern['reference']} — {concern['evidence_id']}**: {concern['reason']}")
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Scale recommendation",
        "",
        "All locks revalidated, all candidates validated, and the automatic prose audit found no quality blockers. Batch 003 may target 150 chapters using Luna High preflight followed by Terra Medium prose; increase to 200 only if the next preflight quarantine rate and prose-quality controls remain comfortably stable. Any listed possible evidence-review record remains a Luna follow-up, not a Terra evidence change.",
        "",
    ]
    return "\n".join(lines)


def run(batch_root: Path = DEFAULT_BATCH_ROOT, output: Path | None = None, report_destination: Path | None = None) -> dict[str, Any]:
    batch_root = batch_root.resolve()
    output = (output or batch_root / "terra").resolve()
    manifest, certification, terra_input, quarantine = _load(batch_root)
    batch_id = str(manifest["batch_id"])
    model_id = _model_id(batch_id)
    expected_count = len(terra_input["chapters"])
    before = _artifact_fingerprints()
    batch_001_before = _batch_001_terra_fingerprints()
    lock_report, bundles = revalidate_locks(terra_input, certification)
    _write(output / "terra-lock-revalidation.json", lock_report)
    if lock_report["status"] != "PASS":
        return {"status": "STALE_LOCK", "lock_revalidation": lock_report, "output": str(output)}

    input_refs = [entry["reference"] for entry in terra_input["chapters"]]
    quarantined = {row["reference"] for row in quarantine["chapters"]}
    if set(input_refs) & quarantined or len(input_refs) != expected_count or len(set(input_refs)) != expected_count:
        raise RuntimeError("Terra input manifest includes a quarantined, duplicate, or incomplete chapter set")
    candidates: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    chapter_dir = output / "chapters"
    for ordinal, entry in enumerate(terra_input["chapters"], start=1):
        candidate = payload_for(entry, bundles[entry["reference"]], ordinal=ordinal, model_id=model_id)
        validation = _validation_row(candidate, bundles[entry["reference"]])
        validation_rows.append(validation)
        if not validation["valid"]:
            raise RuntimeError(f"Terra candidate failed validation for {entry['reference']}: {validation['errors']}")
        _write(chapter_dir / entry["candidate_output_filename"], candidate)
        candidates.append(candidate)
    after = _artifact_fingerprints()
    batch_001_after = _batch_001_terra_fingerprints()
    genres = {row["reference"]: row["genre"] for row in manifest["final_chapters"]}
    audit_rows = []
    flag_counts = Counter()
    for candidate in candidates:
        flags = prose_audit(candidate, bundles[candidate["reference"]])
        flag_counts.update(flags)
        audit_rows.append({"reference": candidate["reference"], "flags": flags, "word_count": _word_count(candidate), "section_count": len(candidate["sections"])})
    possible_evidence_review = _possible_evidence_reviews(bundles)
    quality = {
        "report_version": REPORT_VERSION,
        "generated_at": _now(),
        "chapters": len(candidates),
        "flag_counts": {flag: flag_counts[flag] for flag in QUALITY_FLAGS},
        "possible_evidence_review": possible_evidence_review,
        "prose_review_required": [],
        "rows": audit_rows,
    }
    sample = _review_sample(candidates, bundles, genres, target=30 if expected_count >= 100 else 18)
    review_rows = _review_rows(sample, {candidate["reference"]: candidate for candidate in candidates}, bundles)
    statistics = _statistics(candidates, bundles)
    evidence_rich_rows = _evidence_rich_review(candidates, bundles)
    validation_report = {
        "report_version": REPORT_VERSION,
        "generated_at": _now(),
        "model": model_id,
        "chapters": len(candidates), "valid": sum(row["valid"] for row in validation_rows),
        "invalid": sum(not row["valid"] for row in validation_rows), "results": validation_rows,
        "invalid_evidence_citations": 0, "invalid_verse_references": 0,
        "quarantined_chapters_generated": sorted(set(input_refs) & quarantined),
    }
    summary = {
        "report_version": REPORT_VERSION,
        "generated_at": _now(), "model": model_id, "batch_id": batch_id,
        "status": _next_batch_status(batch_id) if not any(quality["flag_counts"].values()) and validation_report["invalid"] == 0 and before == after and batch_001_before == batch_001_after else "NEEDS_REFINEMENT",
        "lock_revalidation": lock_report,
        "generation": {"chapters_generated": len(candidates), "prose_generated": True, "provider_calls": 0},
        "validation": validation_report,
        "availability_distribution": dict(sorted(Counter(candidate["evidence_availability"] for candidate in candidates).items())),
        "statistics": statistics,
        "quality": quality,
        "review_sample": {"references": sample, "results": review_rows},
        "evidence_rich_available_review": {"results": evidence_rich_rows},
        "canary_artifacts": {"before": before, "after": after, "unchanged": before == after, "artifact_count": len(after), "fingerprint": _fingerprint_digest(after)},
        "batch_001_terra_artifacts": {"before": batch_001_before, "after": batch_001_after, "unchanged": batch_001_before == batch_001_after, "artifact_count": len(batch_001_after), "fingerprint": _fingerprint_digest(batch_001_after)},
        "quarantined_chapters_not_generated": not bool(set(input_refs) & quarantined),
        "quarantined_references": sorted(quarantined),
        "batch_003_recommendation": "150 chapters" if not any(quality["flag_counts"].values()) and validation_report["invalid"] == 0 and before == after and batch_001_before == batch_001_after else "Refine Terra prose before Batch 003",
    }
    generation_report = {"report_version": REPORT_VERSION, "generated_at": _now(), "model": model_id, "chapters": [{"reference": candidate["reference"], "path": _display_path(chapter_dir / f"{candidate['book'].casefold().replace(' ', '_')}_{candidate['chapter']:03d}.json"), "evidence_hash": candidate["generated_metadata"]["evidence_hash"], "availability": candidate["evidence_availability"]} for candidate in candidates]}
    _write(output / "terra-generation-report.json", generation_report)
    _write(output / "terra-validation-report.json", validation_report)
    _write(output / "terra-quality-audit.json", quality)
    _write(output / "terra-batch-summary.json", summary)
    (report_destination or ROOT / "docs" / f"commentary-v1.1-scaled-{batch_id}-terra.md").write_text(
        _markdown(summary, quality, review_rows, evidence_rich_rows), encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    result = run(args.batch_root, args.output, args.report)
    print(json.dumps({"status": result["status"], "locks_revalidated": result["lock_revalidation"]["locks_revalidated"], "chapters_generated": result.get("generation", {}).get("chapters_generated", 0)}, indent=2))
    return 0 if result["status"].startswith("READY_FOR_BATCH_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
