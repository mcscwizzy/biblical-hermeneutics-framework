"""Scripture reference parsing and lookup helpers for CKL."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .normalization import normalize_alias


@dataclass(frozen=True)
class ScriptureReferenceSpan:
    """Normalized representation of a scripture reference or range."""

    book: str
    start_chapter: int | None = None
    start_verse: int | None = None
    end_chapter: int | None = None
    end_verse: int | None = None


def build_book_alias_lookup(objects: Iterable[Any]) -> dict[str, str]:
    """Build a normalized alias -> canonical book title lookup."""

    lookup: dict[str, str] = _standard_book_alias_lookup()
    for obj in objects:
        title = str(getattr(obj, "title", "") or "").strip()
        if not title:
            continue
        lookup[normalize_alias(title)] = title
        for alias in getattr(obj, "aliases", []):
            alias_text = str(alias or "").strip()
            if alias_text:
                lookup[normalize_alias(alias_text)] = title
    return lookup


def _standard_book_alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical_book, (_testament, _genre, aliases) in LEGACY_REFERENCE_BOOKS.items():
        canonical = normalize_alias(canonical_book)
        if canonical:
            lookup[canonical] = canonical_book
        for alias in aliases:
            alias_text = normalize_alias(alias)
            if alias_text:
                lookup[alias_text] = canonical_book
    return lookup


def _load_legacy_reference_books() -> dict[str, tuple[str, str, tuple[str, ...]]]:
    source_path = Path(__file__).resolve().parents[2] / "bhf_agent" / "references.py"
    if not source_path.exists():
        return {}
    try:
        module = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    except OSError:
        return {}
    for node in module.body:
        value_node = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value_node = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value_node = node.value
            if node.target is not None:
                targets = [node.target]
        else:
            continue
        for target in targets:
            if not isinstance(target, ast.Name) or target.id != "BOOKS":
                continue
            if value_node is None:
                return {}
            try:
                value = ast.literal_eval(value_node)
            except (ValueError, SyntaxError):
                return {}
            if isinstance(value, dict):
                return value
    return {}


LEGACY_REFERENCE_BOOKS: Mapping[str, tuple[str, str, tuple[str, ...]]] = (
    _load_legacy_reference_books()
)


def parse_scripture_reference(
    value: str,
    *,
    book_alias_lookup: Mapping[str, str],
) -> ScriptureReferenceSpan | None:
    """Parse a scripture reference string into a normalized span."""

    # A semicolon separates multiple references.  It must not be silently
    # normalized into a four-number cross-chapter range (for example,
    # ``Genesis 12:3; 15:6`` must not become Genesis 12:3-15:6).
    if not isinstance(value, str) or re.search(r"[;,]", value):
        return None

    normalized = normalize_alias(value)
    if not normalized:
        return None

    book_alias = _match_book_alias(normalized, book_alias_lookup)
    if book_alias is None:
        return None

    canonical_book = book_alias_lookup[book_alias]
    remainder = normalized[len(book_alias) :].strip()
    if not remainder:
        return ScriptureReferenceSpan(book=canonical_book)

    tokens = remainder.split()
    if not tokens or any(not token.isdigit() for token in tokens):
        return None

    numbers = [int(token) for token in tokens]
    if len(numbers) == 1:
        return ScriptureReferenceSpan(book=canonical_book, start_chapter=numbers[0])
    if len(numbers) == 2:
        return ScriptureReferenceSpan(
            book=canonical_book,
            start_chapter=numbers[0],
            start_verse=numbers[1],
        )
    if len(numbers) == 3:
        return ScriptureReferenceSpan(
            book=canonical_book,
            start_chapter=numbers[0],
            start_verse=numbers[1],
            end_verse=numbers[2],
        )
    if len(numbers) == 4:
        return ScriptureReferenceSpan(
            book=canonical_book,
            start_chapter=numbers[0],
            start_verse=numbers[1],
            end_chapter=numbers[2],
            end_verse=numbers[3],
        )
    return None


def parse_scripture_references(
    value: str,
    *,
    book_alias_lookup: Mapping[str, str],
) -> list[ScriptureReferenceSpan]:
    """Parse one or more semicolon-separated Scripture references.

    CKL stores some compound references in one field and abbreviates the book
    on subsequent clauses (``Genesis 12:3; 15:6``).  This helper expands those
    clauses into independent spans.  The singular parser remains strict so a
    compound value cannot accidentally become one artificial range.
    """

    if not isinstance(value, str) or not value.strip():
        return []

    parts = [part.strip() for part in re.split(r";", value) if part.strip()]
    if not parts:
        return []

    first = parse_scripture_reference(parts[0], book_alias_lookup=book_alias_lookup)
    if first is None:
        return []

    spans = [first]
    current_book = first.book
    for part in parts[1:]:
        normalized = normalize_alias(part)
        if _match_book_alias(normalized, book_alias_lookup) is None:
            part = f"{current_book} {part}"
        parsed = parse_scripture_reference(part, book_alias_lookup=book_alias_lookup)
        if parsed is None:
            return []
        spans.append(parsed)
        current_book = parsed.book
    return spans


def format_scripture_reference(span: ScriptureReferenceSpan) -> str:
    """Render a parsed Scripture span in the canonical compact form."""

    if span.start_chapter is None:
        return span.book
    value = f"{span.book} {span.start_chapter}"
    if span.start_verse is not None:
        value += f":{span.start_verse}"
    if span.end_chapter is not None:
        value += f"-{span.end_chapter}"
        if span.end_verse is not None:
            value += f":{span.end_verse}"
    elif span.end_verse is not None:
        value += f"-{span.end_verse}"
    return value


def parse_scripture_query(
    reference: Any,
    *,
    book_alias_lookup: Mapping[str, str],
) -> ScriptureReferenceSpan | None:
    """Parse a scripture query from a reference object or string."""

    if reference is None:
        return None
    if isinstance(reference, str):
        return parse_scripture_reference(reference, book_alias_lookup=book_alias_lookup)

    if isinstance(reference, Mapping):
        book = reference.get("book")
        chapter = reference.get("chapter")
        verse = reference.get("verse")
    else:
        book = getattr(reference, "book", None)
        chapter = getattr(reference, "chapter", None)
        verse = getattr(reference, "verse", None)

    book_text = str(book or "").strip()
    if not book_text:
        return None

    canonical_book = book_alias_lookup.get(normalize_alias(book_text), book_text)
    chapter_number = _coerce_int(chapter)
    verse_number = _coerce_int(verse)
    if chapter_number is None and verse_number is None:
        return ScriptureReferenceSpan(book=canonical_book)
    return ScriptureReferenceSpan(
        book=canonical_book,
        start_chapter=chapter_number,
        start_verse=verse_number,
    )


def scripture_query_terms(query: ScriptureReferenceSpan) -> list[str]:
    """Return simple terms for display and matching metadata."""

    terms = [normalize_alias(query.book)]
    if query.start_chapter is not None:
        terms.append(str(query.start_chapter))
    if query.start_verse is not None:
        terms.append(str(query.start_verse))
    if query.end_chapter is not None:
        terms.append(str(query.end_chapter))
    if query.end_verse is not None:
        terms.append(str(query.end_verse))
    return terms


def scripture_query_specificity(query: ScriptureReferenceSpan) -> float:
    """Return a deterministic specificity score for a scripture query."""

    if query.start_chapter is None:
        return 0.65
    if query.start_verse is None:
        return 0.82
    if query.end_chapter is not None:
        return 0.95
    if query.end_verse is not None and query.start_verse is not None:
        return 0.92
    return 0.9


def scripture_reference_overlaps(
    query: ScriptureReferenceSpan,
    candidate: ScriptureReferenceSpan,
) -> bool:
    """Return True when two scripture spans overlap."""

    if normalize_alias(query.book) != normalize_alias(candidate.book):
        return False
    if query.start_chapter is None or candidate.start_chapter is None:
        return True

    query_start, query_end = _range_bounds(query)
    candidate_start, candidate_end = _range_bounds(candidate)
    return not (candidate_end < query_start or query_end < candidate_start)


def scripture_match_score(
    query: ScriptureReferenceSpan,
    *,
    match_count: int = 1,
    importance: int = 0,
) -> float:
    """Return a deterministic ranking score for scripture matches."""

    score = scripture_query_specificity(query)
    if match_count > 1:
        score += min(match_count - 1, 3) * 0.02
    score += min(max(importance, 0), 100) / 1000.0
    return round(min(score, 1.0), 4)


def _match_book_alias(
    value: str,
    book_alias_lookup: Mapping[str, str],
) -> str | None:
    aliases = sorted(
        book_alias_lookup,
        key=lambda alias: (-len(alias.split()), -len(alias), alias),
    )
    for alias in aliases:
        if value == alias or value.startswith(f"{alias} "):
            return alias
    return None


def _coerce_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _range_bounds(span: ScriptureReferenceSpan) -> tuple[tuple[int, int], tuple[int, int]]:
    if span.start_chapter is None:
        return (1, 1), (999, 999)

    start = (span.start_chapter, span.start_verse if span.start_verse is not None else 1)
    end_chapter = span.end_chapter if span.end_chapter is not None else span.start_chapter
    if span.end_verse is not None:
        end = (end_chapter, span.end_verse)
    elif span.start_verse is not None:
        end = (end_chapter, span.start_verse)
    else:
        end = (end_chapter, 999)
    return start, end
