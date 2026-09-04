"""Small Scripture-reference helpers shared by evidence and ranking."""

from __future__ import annotations

from framework.canonical_library.scripture import (
    build_book_alias_lookup,
    parse_scripture_references,
    scripture_reference_overlaps,
)


_BOOK_ALIASES = build_book_alias_lookup(())


def references_overlap(left: str, right: str) -> bool:
    left_spans = parse_scripture_references(str(left or ""), book_alias_lookup=_BOOK_ALIASES)
    right_spans = parse_scripture_references(str(right or ""), book_alias_lookup=_BOOK_ALIASES)
    return any(
        scripture_reference_overlaps(left_span, right_span)
        for left_span in left_spans
        for right_span in right_spans
    )


def reference_distance(target: str, anchor: str) -> int | None:
    """Return a coarse verse distance; different books are not comparable."""

    target_spans = parse_scripture_references(str(target or ""), book_alias_lookup=_BOOK_ALIASES)
    anchor_spans = parse_scripture_references(str(anchor or ""), book_alias_lookup=_BOOK_ALIASES)
    distances: list[int] = []
    for target_span in target_spans:
        for anchor_span in anchor_spans:
            if target_span.book.casefold() != anchor_span.book.casefold():
                continue
            if target_span.start_chapter is None or anchor_span.start_chapter is None:
                distances.append(10_000)
            elif target_span.start_chapter != anchor_span.start_chapter:
                distances.append(abs(target_span.start_chapter - anchor_span.start_chapter) * 100)
            else:
                target_verse = target_span.start_verse or 1
                anchor_verse = anchor_span.start_verse or 1
                distances.append(abs(target_verse - anchor_verse))
    return min(distances) if distances else None


def anchor_specificity(reference: str) -> str:
    spans = parse_scripture_references(str(reference or ""), book_alias_lookup=_BOOK_ALIASES)
    if not spans:
        return "unknown"
    if any(span.start_verse is not None for span in spans):
        return "verse"
    if any(span.start_chapter is not None for span in spans):
        return "chapter"
    return "book"
