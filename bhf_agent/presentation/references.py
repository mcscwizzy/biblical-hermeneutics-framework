"""Small Scripture-reference helpers shared by evidence and ranking."""

from __future__ import annotations

from framework.canonical_library.scripture import (
    build_book_alias_lookup,
    parse_scripture_reference,
    scripture_reference_overlaps,
)


_BOOK_ALIASES = build_book_alias_lookup(())


def references_overlap(left: str, right: str) -> bool:
    left_span = parse_scripture_reference(str(left or ""), book_alias_lookup=_BOOK_ALIASES)
    right_span = parse_scripture_reference(str(right or ""), book_alias_lookup=_BOOK_ALIASES)
    return bool(
        left_span
        and right_span
        and scripture_reference_overlaps(left_span, right_span)
    )


def reference_distance(target: str, anchor: str) -> int | None:
    """Return a coarse verse distance; different books are not comparable."""

    target_span = parse_scripture_reference(str(target or ""), book_alias_lookup=_BOOK_ALIASES)
    anchor_span = parse_scripture_reference(str(anchor or ""), book_alias_lookup=_BOOK_ALIASES)
    if not target_span or not anchor_span or target_span.book.casefold() != anchor_span.book.casefold():
        return None
    if target_span.start_chapter is None or anchor_span.start_chapter is None:
        return 10_000
    if target_span.start_chapter != anchor_span.start_chapter:
        return abs(target_span.start_chapter - anchor_span.start_chapter) * 100
    target_verse = target_span.start_verse or 1
    anchor_verse = anchor_span.start_verse or 1
    return abs(target_verse - anchor_verse)


def anchor_specificity(reference: str) -> str:
    span = parse_scripture_reference(str(reference or ""), book_alias_lookup=_BOOK_ALIASES)
    if not span:
        return "unknown"
    if span.start_verse is not None:
        return "verse"
    if span.start_chapter is not None:
        return "chapter"
    return "book"
