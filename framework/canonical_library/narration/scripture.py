"""Small verse-aware Scripture spans for narration relevance.

This is intentionally not a general Scripture parser.  It supports the forms
stored by CKL and needed to compare an already-selected passage with evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import re


class PassageScope(IntEnum):
    """Ordered from most passage-specific to unrelated."""

    EXACT = 0
    OVERLAPPING_VERSES = 1
    SAME_CHAPTER = 2
    NEARBY_CHAPTER = 3
    SAME_BOOK = 4
    UNRELATED = 5


@dataclass(frozen=True)
class ScriptureSpan:
    book: str
    start_chapter: int
    start_verse: int | None = None
    end_chapter: int | None = None
    end_verse: int | None = None

    def __post_init__(self) -> None:
        if self.end_chapter is None:
            object.__setattr__(self, "end_chapter", self.start_chapter)

    @property
    def is_verse_specific(self) -> bool:
        return self.start_verse is not None


_REFERENCE = re.compile(
    r"^(?P<book>(?:[1-3]\s+)?[A-Za-z][A-Za-z ]*?)\s+"
    r"(?P<chapter>\d+)"
    r"(?:"
    r":(?P<verse>\d+)"
    r"(?:-(?:(?P<verse_end>\d+)|(?P<chapter_end>\d+):(?P<chapter_end_verse>\d+)))?"
    r"|-(?P<chapter_range_end>\d+)"
    r")?$"
)


def parse_scripture_span(reference: object) -> ScriptureSpan | None:
    text = re.sub(r"\s+", " ", str(reference or "").strip())
    text = text.replace("–", "-").replace("—", "-")
    match = _REFERENCE.fullmatch(text)
    if not match:
        return None
    book = match.group("book").strip().casefold()
    chapter = int(match.group("chapter"))
    verse = int(match.group("verse")) if match.group("verse") else None
    if match.group("chapter_end"):
        end_chapter = int(match.group("chapter_end"))
        end_verse = int(match.group("chapter_end_verse"))
    elif match.group("chapter_range_end"):
        end_chapter = int(match.group("chapter_range_end"))
        end_verse = None
    else:
        end_chapter = chapter
        end_verse = int(match.group("verse_end")) if match.group("verse_end") else verse
    if end_chapter < chapter or (
        end_chapter == chapter
        and verse is not None
        and end_verse is not None
        and end_verse < verse
    ):
        return None
    return ScriptureSpan(book, chapter, verse, end_chapter, end_verse)


def spans_overlap(left: ScriptureSpan, right: ScriptureSpan) -> bool:
    if left.book != right.book:
        return False
    left_start = (left.start_chapter, left.start_verse or 0)
    left_end = (left.end_chapter or left.start_chapter, left.end_verse or 9999)
    right_start = (right.start_chapter, right.start_verse or 0)
    right_end = (right.end_chapter or right.start_chapter, right.end_verse or 9999)
    return left_start <= right_end and right_start <= left_end


def passage_scope(requested: ScriptureSpan, candidate: ScriptureSpan) -> PassageScope:
    if requested.book != candidate.book:
        return PassageScope.UNRELATED
    if requested == candidate:
        return PassageScope.EXACT
    candidate_chapter_count = (candidate.end_chapter or candidate.start_chapter) - candidate.start_chapter + 1
    if candidate_chapter_count > 2:
        return PassageScope.SAME_BOOK
    if spans_overlap(requested, candidate):
        if requested.is_verse_specific and candidate.is_verse_specific:
            return PassageScope.OVERLAPPING_VERSES
        return PassageScope.SAME_CHAPTER
    requested_chapters = set(range(requested.start_chapter, (requested.end_chapter or requested.start_chapter) + 1))
    candidate_chapters = set(range(candidate.start_chapter, (candidate.end_chapter or candidate.start_chapter) + 1))
    if requested_chapters & candidate_chapters:
        return PassageScope.SAME_CHAPTER
    distance = min(abs(left - right) for left in requested_chapters for right in candidate_chapters)
    return PassageScope.NEARBY_CHAPTER if distance <= 2 else PassageScope.SAME_BOOK


def references_overlap(left: object, right: object) -> bool:
    left_span = parse_scripture_span(left)
    right_span = parse_scripture_span(right)
    if left_span is None or right_span is None:
        return str(left or "").strip().casefold() == str(right or "").strip().casefold()
    return spans_overlap(left_span, right_span)
