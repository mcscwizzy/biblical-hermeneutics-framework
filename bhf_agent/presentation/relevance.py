"""Deterministic semantic roles for passage-scoped evidence.

Scripture-anchor overlap answers a retrieval question.  The functions in this
module answer the narrower presentation question: what kind of relationship
does the evidence have to the requested chapter, and which sections may use
it?  This is intentionally rule-based; it is not a model-inference layer.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from framework.canonical_library.scripture import parse_scripture_references

from .references import _BOOK_ALIASES
from bhf_agent.references import BOOKS


DIRECT_CONTEXT = "DIRECT_CONTEXT"
BOOK_CONTEXT = "BOOK_CONTEXT"
INTERTEXTUAL_REUSE = "INTERTEXTUAL_REUSE"
LATER_RECEPTION = "LATER_RECEPTION"
COMPARATIVE_CONTEXT = "COMPARATIVE_CONTEXT"
GENERIC_BACKGROUND = "GENERIC_BACKGROUND"
WEAKLY_RELATED = "WEAKLY_RELATED"
SEMANTICALLY_MISANCHORED = "SEMANTICALLY_MISANCHORED"

SEMANTIC_RELATIONSHIPS = frozenset(
    {
        DIRECT_CONTEXT,
        BOOK_CONTEXT,
        INTERTEXTUAL_REUSE,
        LATER_RECEPTION,
        COMPARATIVE_CONTEXT,
        GENERIC_BACKGROUND,
        WEAKLY_RELATED,
        SEMANTICALLY_MISANCHORED,
    }
)

PRESENTATION_SECTIONS = frozenset(
    {
        "historical_context",
        "archaeology_geography",
        "language_literary",
        "chronology",
        "interpretive_questions",
        "dig_deeper",
    }
)

# These are the word-study relationships actually reachable from the v1.1
# canary.  A Greek translation term is not treated as the Hebrew source word
# merely because a lexicon record was tagged to the same passage.
WORD_STUDY_PASSAGE_RELATIONSHIPS = {
    ("torah", "Psalms"): DIRECT_CONTEXT,
    ("makarios", "Psalms"): COMPARATIVE_CONTEXT,
    ("nomos", "Psalms"): COMPARATIVE_CONTEXT,
}

# These are the confirmed v1.1 canary defects.  Keeping the guard in the
# projection layer prevents an unrebuilt SQLite database or an ad-hoc fixture
# from reintroducing the same bad chapter evidence.
KNOWN_SEMANTICALLY_MISANCHORED = {
    "arad-ostraca",
    "caesarea-maritima-excavations",
    "ein-gedi-scroll",
    "herodium-excavations",
    "kurkh-monolith",
    "masada-excavations",
    "pool-of-bethesda-excavation",
    "samaria-ostraca",
    "samaria-palace",
    "shiloh-excavations",
}

_BOOK_ORDER = {book: index for index, book in enumerate(BOOKS, start=1)}
_BOOK_TOKEN_RE = re.compile(r"^\s*(?P<book>.+?)\s+\d+")


def requested_book(reference: str) -> str:
    """Return the canonical book name in a passage reference."""

    match = _BOOK_TOKEN_RE.match(str(reference or ""))
    if not match:
        return ""
    candidate = " ".join(match.group("book").split())
    return _BOOK_ALIASES.get(candidate.casefold(), candidate)


def _source_book(metadata: Mapping[str, Any]) -> str:
    title = " ".join(str(metadata.get("parent_title") or "").split())
    return _BOOK_ALIASES.get(title.casefold(), title)


def _anchor_is_book_context(passage_ref: str, anchors: list[str]) -> bool:
    target_book = requested_book(passage_ref)
    target_chapter = next(
        (
            span.start_chapter
            for span in parse_scripture_references(
                passage_ref, book_alias_lookup=_BOOK_ALIASES
            )
            if span.start_chapter is not None
        ),
        None,
    )
    for anchor in anchors:
        for span in parse_scripture_references(anchor, book_alias_lookup=_BOOK_ALIASES):
            if span.book != target_book or target_chapter is None:
                continue
            if span.end_chapter is not None and span.end_chapter != target_chapter:
                return True
    return False


def classify_semantic_relationship(
    passage_ref: str,
    *,
    anchors: list[str],
    metadata: Mapping[str, Any],
) -> str:
    """Classify an admitted item using authored metadata and source identity."""

    parent_id = str(metadata.get("parent_object_id") or "").casefold()
    parent_type = str(metadata.get("parent_type") or "").casefold()
    source_kind = str(metadata.get("source_kind") or "").casefold()
    relationship = str(metadata.get("passage_relationship") or "").casefold()
    requested = requested_book(passage_ref)
    source_book = _source_book(metadata)

    if parent_type == "word_study":
        word_relationship = WORD_STUDY_PASSAGE_RELATIONSHIPS.get(
            (parent_id, requested)
        )
        if word_relationship:
            return word_relationship

    if parent_id in KNOWN_SEMANTICALLY_MISANCHORED and parent_type == "archaeology":
        target = requested_book(passage_ref)
        if target == "Genesis" and any(
            anchor.casefold().startswith("genesis 1") for anchor in anchors
        ):
            return SEMANTICALLY_MISANCHORED
    if relationship in {"comparative", "comparison"}:
        return COMPARATIVE_CONTEXT
    if parent_type == "archaeology" and source_kind == "ckl_evidence_item":
        return DIRECT_CONTEXT
    if parent_type == "book":
        if source_book and source_book != requested:
            source_testament = BOOKS.get(source_book, ("",))[0]
            requested_testament = BOOKS.get(requested, ("",))[0]
            return (
                LATER_RECEPTION
                if source_testament and source_testament != requested_testament
                else INTERTEXTUAL_REUSE
            )
        return (
            BOOK_CONTEXT
            if _anchor_is_book_context(passage_ref, anchors)
            else DIRECT_CONTEXT
        )
    if source_kind == "ckl_evidence_item":
        return DIRECT_CONTEXT if relationship in {"direct", "primary"} else GENERIC_BACKGROUND
    if source_kind == "ckl_interpretive_note":
        if source_book and source_book != requested:
            source_testament = BOOKS.get(source_book, ("",))[0]
            requested_testament = BOOKS.get(requested, ("",))[0]
            return (
                LATER_RECEPTION
                if source_testament and source_testament != requested_testament
                else INTERTEXTUAL_REUSE
            )
        return DIRECT_CONTEXT
    if source_kind == "ckl_legacy_field":
        if parent_type == "archaeology":
            return GENERIC_BACKGROUND
        if parent_type == "book":
            return BOOK_CONTEXT
        if parent_type in {"theme", "faq", "word_study", "theology", "doctrine"}:
            return GENERIC_BACKGROUND
        if relationship in {"background", "contextual", "supporting"}:
            return GENERIC_BACKGROUND
    return WEAKLY_RELATED


def presentation_role(
    metadata: Mapping[str, Any],
    *,
    category: str,
    claim: str = "",
) -> str | None:
    """Return the deterministic section role for an evidence item.

    CKL category is an index facet, not a presentation instruction.  This
    layer gives authored claim type and semantic relationship precedence over
    legacy category labels, especially for word studies and literary claims
    that happen to be indexed as geography.
    """

    parent_type = str(metadata.get("parent_type") or "").casefold()
    source_kind = str(metadata.get("source_kind") or "").casefold()
    relationship = str(metadata.get("semantic_relationship") or "")
    claim_type = str(metadata.get("claim_type") or "").casefold().replace("-", "_")
    note_type = str(metadata.get("note_type") or "").casefold().replace("-", "_")
    category = str(category or "").casefold()
    text = " ".join(
        str(value or "")
        for value in (
            metadata.get("parent_object_id"),
            metadata.get("parent_title"),
            claim,
        )
    ).casefold()

    if relationship in {LATER_RECEPTION, INTERTEXTUAL_REUSE, COMPARATIVE_CONTEXT}:
        return "dig_deeper"
    if relationship in {SEMANTICALLY_MISANCHORED, WEAKLY_RELATED}:
        return None

    if parent_type == "word_study":
        # Only the explicitly audited direct lexical mapping may ground the
        # language section.  Generic generated word-study prose is retained
        # in the locked bundle but is not first-audience language context.
        return "language_literary" if relationship == DIRECT_CONTEXT else None

    if claim_type in {
        "lexical",
        "literary",
        "composition",
        "authorship",
        "rhetorical",
        "textual_form",
        "textual",
    }:
        return "language_literary"
    if claim_type in {"historical_cultural", "historical", "social", "political"}:
        return "historical_context"
    if note_type in {"ancient_near_east_context", "second_temple_context", "historical_context"}:
        return "historical_context"

    literary_terms = {
        "authorship",
        "coordinated production",
        "composition",
        "literary relationship",
        "literary unity",
        "narrative continuation",
        "publication history",
        "theophilus",
        "common authorship",
        "sequel",
        "prologue",
        "source",
    }
    if category in {"geography", "archaeology"} and any(
        term in text for term in literary_terms
    ):
        return "language_literary"

    if category in {"archaeology", "geography"}:
        return (
            "archaeology_geography"
            if relationship in {DIRECT_CONTEXT, BOOK_CONTEXT}
            else None
        )
    if category == "chronology":
        return "chronology"
    if category in {"culture", "history", "politics", "social", "economics"}:
        return "historical_context"
    if category == "language":
        return "language_literary"
    if parent_type == "faq" and relationship in {
        DIRECT_CONTEXT,
        BOOK_CONTEXT,
        GENERIC_BACKGROUND,
    }:
        return "historical_context"
    return "historical_context"


def overview_priority(
    metadata: Mapping[str, Any],
    *,
    category: str,
    claim: str = "",
) -> int:
    """Score first-reader usefulness without using evidence IDs as a signal."""

    relationship = str(metadata.get("semantic_relationship") or "")
    parent_type = str(metadata.get("parent_type") or "").casefold()
    source_kind = str(metadata.get("source_kind") or "").casefold()
    category = str(category or "").casefold()
    text = " ".join(
        str(value or "")
        for value in (
            metadata.get("parent_object_id"),
            metadata.get("parent_title"),
            claim,
        )
    ).casefold()
    score = {
        DIRECT_CONTEXT: 60,
        BOOK_CONTEXT: 50,
        GENERIC_BACKGROUND: 25,
    }.get(relationship, 0)
    # First-audience, passage-specific evidence must outrank book movement or
    # generic background when reader-usefulness signals are otherwise close.
    score += {
        DIRECT_CONTEXT: 15,
        BOOK_CONTEXT: 0,
        GENERIC_BACKGROUND: -5,
    }.get(relationship, 0)
    score += {
        "history": 15,
        "culture": 15,
        "social": 15,
        "politics": 15,
        "economics": 10,
        "archaeology": 8,
        "geography": 8,
        "language": 6,
        "chronology": 5,
    }.get(category, 0)
    if parent_type == "book" and source_kind in {"ckl_claim", "ckl_evidence_item"}:
        score += 8
    if presentation_role(metadata, category=category, claim=claim) == "historical_context":
        score += 5

    reader_context_terms = {
        "setting", "historical", "josiah", "judah", "jerusalem", "assyrian",
        "roman", "jewish", "social", "official", "royal", "cult", "idolatry",
        "sacrifice", "day of y", "judgment", "practice", "institution", "temple",
        "theophilus", "narrative", "creation-scale",
    }
    demotion_terms = {
        "textual witness", "textual witnesses", "manuscript", "transmission", "pesharim", "textual plurality",
        "authorship", "composition", "source-critical", "source criticism", "provenance",
        "lexical side", "translation history", "reception history", "reception", "modern reception",
    }
    score += 15 if any(term in text for term in reader_context_terms) else 0
    score -= 35 if any(term in text for term in demotion_terms) else 0
    if relationship in {LATER_RECEPTION, INTERTEXTUAL_REUSE, COMPARATIVE_CONTEXT}:
        score -= 80
    if str(metadata.get("dispute_status") or "").casefold() not in {"", "not_disputed", "unknown", "none"}:
        score -= 8
    return max(0, score)


def with_presentation_metadata(
    metadata: Mapping[str, Any],
    *,
    category: str,
    claim: str = "",
) -> dict[str, Any]:
    result = dict(metadata)
    result["presentation_role"] = presentation_role(
        result, category=category, claim=claim
    )
    result["overview_priority"] = overview_priority(
        result, category=category, claim=claim
    )
    return result


def with_semantic_relationship(
    passage_ref: str,
    metadata: Mapping[str, Any],
    *,
    anchors: list[str],
) -> dict[str, Any]:
    result = dict(metadata)
    result["semantic_relationship"] = classify_semantic_relationship(
        passage_ref, anchors=anchors, metadata=result
    )
    return result


def is_semantically_relevant(item: Any) -> bool:
    """Whether an item can support grounded regeneration."""

    metadata = getattr(item, "relevance_metadata", {}) or {}
    relationship = metadata.get("semantic_relationship")
    if relationship in {SEMANTICALLY_MISANCHORED, WEAKLY_RELATED}:
        return False
    return bool(
        getattr(item, "claim", "").strip()
        and getattr(item, "source_ids", ())
        and getattr(item, "passage_anchors", ())
    )
