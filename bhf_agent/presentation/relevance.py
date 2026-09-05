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
