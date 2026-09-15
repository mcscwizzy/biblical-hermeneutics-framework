"""Deterministic evidence-versus-synthesis richness diagnostics."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from bhf_agent import bible
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION

from .availability import classify_evidence_availability, evidence_contribution
from .evidence_bundling import get_chapter_evidence_bundle
from .storage import load_commentary


RICHNESS_AUDIT_VERSION = "commentary-richness-v1.2"
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?")
_VERSE_RE = re.compile(r"^(.+?)\s+(\d+):(\d+)(?:-(?:(\d+):)?(\d+))?$")
_BOILERPLATE = (
    "read the chapter with this setting in view",
    "it gives a starting point for following the chapter's own movement",
    "the chapter itself should determine how far the point is taken",
    "for its historical and cultural setting, note that",
    "this background clarifies the setting assumed by the passage",
    "it does not by itself settle every question raised by the chapter",
    "a literary feature to notice is that",
    "this form helps organize the chapter's claims",
    "notice it before drawing broader conclusions",
    "for a later or comparative connection, note that",
    "it can be traced further without replacing the chapter's own setting",
)
_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have he her his in is it its of on or that the their them they this to was were which who with".split()
)
_BACKLOG_CATEGORIES = (
    "history", "culture", "social", "politics", "geography", "archaeology",
    "language", "literary", "chronology", "people", "places", "events",
    "institutions", "customs", "surrounding_narrative",
)


class RichnessStatus(str, Enum):
    RICH_ENOUGH = "RICH_ENOUGH"
    SYNTHESIS_GAP = "SYNTHESIS_GAP"
    EVIDENCE_GAP = "EVIDENCE_GAP"


@dataclass(frozen=True)
class RichnessThresholds:
    """Explicit policy; callers may tune it without changing the algorithm."""

    meaningful_thin_score: float = 0.5
    rich_min_words: int = 90
    small_evidence_min_words: int = 45
    rich_min_sections: int = 2
    rich_min_unique_evidence: int = 2
    rich_min_evidence_coverage: float = 0.35
    boilerplate_ratio_limit: float = 0.6
    boundary_repetition_ratio: float = 0.65


def audit_chapter(
    book: str,
    chapter: int,
    commentary: Any,
    bundle: Any,
    *,
    thresholds: RichnessThresholds = RichnessThresholds(),
) -> dict[str, Any]:
    chapter_data = bible.resolve_chapter(book, chapter)
    verses = list(chapter_data.get("verses", []))
    reference = f"{chapter_data['book']} {chapter}"
    evidence_items = list(getattr(bundle, "evidence_items", []) or [])
    evidence_ids = {item.id for item in evidence_items}
    contributions = [evidence_contribution(item, bundle.passage_ref) for item in evidence_items]
    availability = classify_evidence_availability(bundle).value
    category_counts = Counter(item.category for item in evidence_items)
    sections = list(getattr(commentary, "sections", []) or [])
    blocks = [block for section in sections for block in section.blocks]
    prose = " ".join(block.text for block in blocks).strip()
    cited = {evidence_id for block in blocks for evidence_id in block.evidence_ids}
    valid_cited = cited.intersection(evidence_ids)
    unused = evidence_ids - valid_cited
    word_count = len(_words(prose))
    boilerplate_hits = [phrase for phrase in _BOILERPLATE if phrase in prose.casefold()]
    boilerplate_ratio = round(len(boilerplate_hits) / max(1, len(blocks)), 4)
    boundary_ratio = _boundary_overlap(prose, verses)
    verse_anchors = _covered_verses(blocks, chapter_data["book"], chapter)
    verse_total = len(verses)
    evidence_coverage = round(len(valid_cited) / len(evidence_ids), 4) if evidence_ids else 0.0
    total_score = round(sum(value.score for value in contributions), 4)
    specific_count = sum(value.specific for value in contributions)
    mostly_boundary = bool(
        prose and boundary_ratio >= thresholds.boundary_repetition_ratio and len(valid_cited) <= 1
    )
    contextually_thin = _contextually_thin(
        availability=availability,
        evidence_count=len(evidence_ids),
        section_count=len(sections),
        word_count=word_count,
        unique_consumed=len(valid_cited),
        evidence_coverage=evidence_coverage,
        boilerplate_ratio=boilerplate_ratio,
        mostly_boundary=mostly_boundary,
        thresholds=thresholds,
    )
    richness, reasons = classify_richness(
        evidence_availability=availability,
        evidence_count=len(evidence_ids),
        evidence_score=total_score,
        specific_evidence_count=specific_count,
        category_diversity=len(category_counts),
        contextually_thin=contextually_thin,
        thresholds=thresholds,
    )
    entity_counts = {
        bucket: len(bundle.entities.get(bucket, []))
        for bucket in ("people", "places", "groups", "events", "artifacts")
    }
    return {
        "reference": reference,
        "commentary_status": getattr(commentary, "status", "missing") if commentary else "missing",
        "validation_status": getattr(commentary, "status", "failed") if commentary else "failed",
        "richness_status": richness.value,
        "richness_reasons": reasons,
        "evidence_availability": availability,
        "evidence_item_count": len(evidence_ids),
        "specific_evidence_count": specific_count,
        "evidence_score": total_score,
        "evidence_category_diversity": len(category_counts),
        "evidence_categories": dict(sorted(category_counts.items())),
        "entity_counts": entity_counts,
        "people_count": entity_counts["people"],
        "places_count": entity_counts["places"],
        "events_groups_artifacts_count": entity_counts["events"] + entity_counts["groups"] + entity_counts["artifacts"],
        "geography_evidence_count": category_counts["geography"],
        "archaeology_evidence_count": category_counts["archaeology"],
        "section_count": len(sections),
        "commentary_block_count": len(blocks),
        "commentary_prose_char_count": len(prose),
        "commentary_prose_word_count": word_count,
        "verse_anchor_count": len(verse_anchors),
        "verse_anchor_coverage": round(len(verse_anchors) / verse_total, 4) if verse_total else 0.0,
        "evidence_ids_referenced": sorted(cited),
        "unique_evidence_ids_consumed": len(valid_cited),
        "evidence_consumption_ratio": evidence_coverage,
        "unused_evidence_ids": sorted(unused),
        "unused_evidence_count": len(unused),
        "unknown_evidence_ids": sorted(cited - evidence_ids),
        "boilerplate_detected": bool(boilerplate_hits),
        "boilerplate_phrases": boilerplate_hits,
        "boilerplate_ratio": boilerplate_ratio,
        "mostly_repeats_opening_or_closing_verses": mostly_boundary,
        "opening_closing_lexical_overlap": boundary_ratio,
        "validated_but_contextually_thin": bool(
            commentary and commentary.status == "validated" and contextually_thin
        ),
    }


def classify_richness(
    *,
    evidence_availability: str,
    evidence_count: int,
    evidence_score: float,
    specific_evidence_count: int,
    category_diversity: int,
    contextually_thin: bool,
    thresholds: RichnessThresholds = RichnessThresholds(),
) -> tuple[RichnessStatus, list[str]]:
    """Keep evidence insufficiency distinct from prose/synthesis insufficiency."""

    evidence_reasons: list[str] = []
    if evidence_availability == "DATA_GAP" or evidence_count == 0:
        evidence_reasons.append("no passage-scoped evidence")
    if evidence_availability == "THIN" and evidence_score < thresholds.meaningful_thin_score:
        evidence_reasons.append("thin evidence score is below the meaningful threshold")
    if evidence_availability == "THIN" and specific_evidence_count == 0:
        evidence_reasons.append("thin evidence has no chapter- or verse-specific support")
    if evidence_count and category_diversity == 0:
        evidence_reasons.append("evidence has no classified contextual category")
    if evidence_reasons:
        return RichnessStatus.EVIDENCE_GAP, evidence_reasons
    if contextually_thin:
        return RichnessStatus.SYNTHESIS_GAP, [
            "meaningful evidence exists but reader commentary underuses or weakly explains it"
        ]
    return RichnessStatus.RICH_ENOUGH, ["supported evidence is materially represented in reader commentary"]


def audit_corpus(
    storage_dir: str | Path,
    *,
    thresholds: RichnessThresholds = RichnessThresholds(),
    chapters: Iterable[tuple[str, int]] | None = None,
) -> dict[str, Any]:
    canonical = list(chapters or _canonical_chapters())
    rows: list[dict[str, Any]] = []
    for book, chapter in canonical:
        bundle = get_chapter_evidence_bundle(
            book,
            chapter,
            evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
        )
        if bundle is None:
            raise RuntimeError(f"unable to build EvidenceBundle for {book} {chapter}")
        rows.append(
            audit_chapter(
                book,
                chapter,
                load_commentary(storage_dir, book, chapter),
                bundle,
                thresholds=thresholds,
            )
        )
    counts = Counter(row["richness_status"] for row in rows)
    availability = Counter(row["evidence_availability"] for row in rows)
    validation = Counter(row["validation_status"] for row in rows)
    backlog = evidence_gap_backlog(rows)
    return {
        "audit_schema_version": RICHNESS_AUDIT_VERSION,
        "thresholds": asdict(thresholds),
        "chapter_count": len(rows),
        "validation_status_counts": dict(sorted(validation.items())),
        "evidence_availability_counts": dict(sorted(availability.items())),
        "richness_status_counts": {
            status.value: counts[status.value] for status in RichnessStatus
        },
        "chapters": rows,
        "evidence_gap_backlog": backlog,
    }


def evidence_gap_backlog(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        if row["richness_status"] != RichnessStatus.EVIDENCE_GAP.value:
            continue
        existing = set(row["evidence_categories"])
        result.append(
            {
                "reference": row["reference"],
                "missing_categories": [value for value in _BACKLOG_CATEGORIES if value not in existing],
                "existing_evidence_categories": sorted(existing),
                "evidence_availability": row["evidence_availability"],
                "reason": "; ".join(row["richness_reasons"]),
                "suggested_ckl_family": _suggested_family(existing),
            }
        )
    return result


def render_human_report(audit: dict[str, Any]) -> str:
    counts = audit["richness_status_counts"]
    availability = audit["evidence_availability_counts"]
    thin = sum(row["validated_but_contextually_thin"] for row in audit["chapters"])
    boilerplate = sum(row["boilerplate_detected"] for row in audit["chapters"])
    return "\n".join(
        [
            "# Commentary v1.2 richness audit",
            "",
            f"Chapters audited: {audit['chapter_count']}",
            "",
            "## Richness outcomes",
            "",
            f"- RICH_ENOUGH: {counts.get('RICH_ENOUGH', 0)}",
            f"- SYNTHESIS_GAP: {counts.get('SYNTHESIS_GAP', 0)}",
            f"- EVIDENCE_GAP: {counts.get('EVIDENCE_GAP', 0)}",
            "",
            "## Evidence availability",
            "",
            f"- AVAILABLE: {availability.get('AVAILABLE', 0)}",
            f"- THIN: {availability.get('THIN', 0)}",
            f"- DATA_GAP: {availability.get('DATA_GAP', 0)}",
            "",
            f"Validated but contextually thin: {thin}",
            f"Chapters with detected v1.1 boilerplate: {boilerplate}",
            f"Targeted CKL backlog entries: {len(audit['evidence_gap_backlog'])}",
            "",
            "Validation status and richness status are independent dimensions.",
            "Thresholds and every per-chapter measurement are recorded in the JSON artifact.",
            "",
        ]
    )


def _contextually_thin(
    *, availability: str, evidence_count: int, section_count: int, word_count: int,
    unique_consumed: int, evidence_coverage: float, boilerplate_ratio: float,
    mostly_boundary: bool, thresholds: RichnessThresholds,
) -> bool:
    if availability == "DATA_GAP":
        return False
    if evidence_count <= 2:
        return (
            unique_consumed < evidence_count
            or word_count < thresholds.small_evidence_min_words
            or boilerplate_ratio >= thresholds.boilerplate_ratio_limit
            or mostly_boundary
        )
    return (
        unique_consumed < min(thresholds.rich_min_unique_evidence, evidence_count)
        or evidence_coverage < thresholds.rich_min_evidence_coverage
        or word_count < thresholds.rich_min_words
        or section_count < thresholds.rich_min_sections
        or boilerplate_ratio >= thresholds.boilerplate_ratio_limit
        or mostly_boundary
    )


def _covered_verses(blocks: Iterable[Any], book: str, chapter: int) -> set[int]:
    covered: set[int] = set()
    for block in blocks:
        for reference in block.verse_refs:
            match = _VERSE_RE.match(" ".join(reference.split()))
            if not match or match.group(1).casefold() != book.casefold() or int(match.group(2)) != chapter:
                continue
            if match.group(4) and int(match.group(4)) != chapter:
                continue
            start = int(match.group(3))
            end = int(match.group(5) or start)
            covered.update(range(start, end + 1))
    return covered


def _boundary_overlap(prose: str, verses: list[dict[str, Any]]) -> float:
    if not prose or not verses:
        return 0.0
    boundary = " ".join(str(item.get("text") or "") for item in (verses[:1] + verses[-1:]))
    prose_words = set(_words(prose)) - _STOPWORDS
    boundary_words = set(_words(boundary)) - _STOPWORDS
    if not prose_words:
        return 0.0
    return round(len(prose_words.intersection(boundary_words)) / len(prose_words), 4)


def _words(value: str) -> list[str]:
    return [match.group(0).casefold() for match in _WORD_RE.finditer(value)]


def _canonical_chapters() -> Iterable[tuple[str, int]]:
    for book in bible.list_books():
        for chapter in range(1, int(book["chapters"]) + 1):
            yield str(book["name"]), chapter


def _suggested_family(existing: set[str]) -> str:
    if not existing:
        return "passage-scoped contextual record"
    if not existing.intersection({"culture", "social", "economics", "politics"}):
        return "cultural_background"
    if not existing.intersection({"history", "chronology"}):
        return "events_or_historical_context"
    if not existing.intersection({"geography", "archaeology"}):
        return "place_or_archaeology"
    return "chapter-specific claims on the existing CKL family"
