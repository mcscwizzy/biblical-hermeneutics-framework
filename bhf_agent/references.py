"""Deterministic first-pass Bible reference detection."""

from __future__ import annotations

import re
from typing import Optional

from .models import ReferenceContext


BOOKS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "Genesis": ("Old Testament", "Torah", ("gen", "ge", "gn")),
    "Exodus": ("Old Testament", "Torah", ("exod", "exo", "ex")),
    "Leviticus": ("Old Testament", "Torah", ("lev", "le")),
    "Numbers": ("Old Testament", "Torah", ("num", "nu", "nm")),
    "Deuteronomy": ("Old Testament", "Torah", ("deut", "dt")),
    "Joshua": ("Old Testament", "Narrative", ("josh",)),
    "Judges": ("Old Testament", "Narrative", ("judg", "jdg")),
    "Ruth": ("Old Testament", "Narrative", ("ru",)),
    "1 Samuel": ("Old Testament", "Narrative", ("1 sam", "1sam", "i samuel")),
    "2 Samuel": ("Old Testament", "Narrative", ("2 sam", "2sam", "ii samuel")),
    "1 Kings": ("Old Testament", "Narrative", ("1 kgs", "1kgs", "1 ki")),
    "2 Kings": ("Old Testament", "Narrative", ("2 kgs", "2kgs", "2 ki")),
    "1 Chronicles": ("Old Testament", "Narrative", ("1 chr", "1chr")),
    "2 Chronicles": ("Old Testament", "Narrative", ("2 chr", "2chr")),
    "Ezra": ("Old Testament", "Narrative", ()),
    "Nehemiah": ("Old Testament", "Narrative", ("neh",)),
    "Esther": ("Old Testament", "Narrative", ("esth", "est")),
    "Job": ("Old Testament", "Wisdom", ()),
    "Psalms": ("Old Testament", "Poetry", ("psalm", "ps", "psa")),
    "Proverbs": ("Old Testament", "Wisdom", ("prov", "pr")),
    "Ecclesiastes": ("Old Testament", "Wisdom", ("eccl", "ecc")),
    "Song of Songs": (
        "Old Testament",
        "Poetry",
        ("song of solomon", "song", "sos"),
    ),
    "Isaiah": ("Old Testament", "Prophecy", ("isa",)),
    "Jeremiah": ("Old Testament", "Prophecy", ("jer",)),
    "Lamentations": ("Old Testament", "Poetry", ("lam",)),
    "Ezekiel": ("Old Testament", "Prophecy", ("ezek", "eze")),
    "Daniel": ("Old Testament", "Apocalyptic", ("dan",)),
    "Hosea": ("Old Testament", "Prophecy", ("hos",)),
    "Joel": ("Old Testament", "Prophecy", ()),
    "Amos": ("Old Testament", "Prophecy", ()),
    "Obadiah": ("Old Testament", "Prophecy", ("obad",)),
    "Jonah": ("Old Testament", "Prophecy", ()),
    "Micah": ("Old Testament", "Prophecy", ("mic",)),
    "Nahum": ("Old Testament", "Prophecy", ("nah",)),
    "Habakkuk": ("Old Testament", "Prophecy", ("hab",)),
    "Zephaniah": ("Old Testament", "Prophecy", ("zeph",)),
    "Haggai": ("Old Testament", "Prophecy", ("hag",)),
    "Zechariah": ("Old Testament", "Prophecy", ("zech",)),
    "Malachi": ("Old Testament", "Prophecy", ("mal",)),
    "Matthew": ("New Testament", "Gospel", ("matt", "mt")),
    "Mark": ("New Testament", "Gospel", ("mk",)),
    "Luke": ("New Testament", "Gospel", ("lk",)),
    "John": ("New Testament", "Gospel", ("jn",)),
    "Acts": ("New Testament", "Narrative", ("act",)),
    "Romans": ("New Testament", "Epistle", ("rom",)),
    "1 Corinthians": ("New Testament", "Epistle", ("1 cor", "1cor")),
    "2 Corinthians": ("New Testament", "Epistle", ("2 cor", "2cor")),
    "Galatians": ("New Testament", "Epistle", ("gal",)),
    "Ephesians": ("New Testament", "Epistle", ("eph",)),
    "Philippians": ("New Testament", "Epistle", ("phil",)),
    "Colossians": ("New Testament", "Epistle", ("col",)),
    "1 Thessalonians": ("New Testament", "Epistle", ("1 thess", "1thess")),
    "2 Thessalonians": ("New Testament", "Epistle", ("2 thess", "2thess")),
    "1 Timothy": ("New Testament", "Epistle", ("1 tim", "1tim")),
    "2 Timothy": ("New Testament", "Epistle", ("2 tim", "2tim")),
    "Titus": ("New Testament", "Epistle", ()),
    "Philemon": ("New Testament", "Epistle", ("phlm",)),
    "Hebrews": ("New Testament", "Epistle", ("heb",)),
    "James": ("New Testament", "Epistle", ("jas",)),
    "1 Peter": ("New Testament", "Epistle", ("1 pet", "1pet")),
    "2 Peter": ("New Testament", "Epistle", ("2 pet", "2pet")),
    "1 John": ("New Testament", "Epistle", ("1 jn", "1jn")),
    "2 John": ("New Testament", "Epistle", ("2 jn", "2jn")),
    "3 John": ("New Testament", "Epistle", ("3 jn", "3jn")),
    "Jude": ("New Testament", "Epistle", ()),
    "Revelation": ("New Testament", "Apocalyptic", ("rev", "re")),
}

BOOK_ALIASES: dict[str, str] = {}
for canonical_book, (_, _, aliases) in BOOKS.items():
    BOOK_ALIASES[canonical_book.lower()] = canonical_book
    for alias in aliases:
        BOOK_ALIASES[alias.lower()] = canonical_book

BOOK_PATTERN = "|".join(
    re.escape(name) for name in sorted(BOOK_ALIASES, key=len, reverse=True)
)
REFERENCE_RE = re.compile(
    rf"\b(?P<book>{BOOK_PATTERN})\.?\s+"
    r"(?P<chapter>\d{1,3})"
    r"(?:\s*:\s*(?P<verse>\d{1,3}))?\b",
    re.IGNORECASE,
)


def detect_reference(question: str) -> ReferenceContext:
    match = REFERENCE_RE.search(question)
    if match:
        book = BOOK_ALIASES[match.group("book").lower()]
        chapter = int(match.group("chapter"))
        verse = int(match.group("verse")) if match.group("verse") else None
        testament = BOOKS[book][0]
        return ReferenceContext(
            book=book,
            chapter=chapter,
            verse=verse,
            testament=testament,
            is_reference_based=True,
            topic=None,
            confidence=0.92 if verse else 0.84,
        )

    topic = _topic_from_question(question)
    return ReferenceContext(
        is_reference_based=False,
        topic=topic,
        confidence=0.55 if topic else 0.25,
    )


def _topic_from_question(question: str) -> Optional[str]:
    normalized = " ".join(question.strip().split())
    if not normalized:
        return None
    lowered = normalized.lower().rstrip("?")
    prefixes = (
        "what does the bible say about ",
        "what does paul say about ",
        "what does scripture say about ",
        "what does revelation mean by ",
        "what does jesus say about ",
        "explain ",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return normalized[len(prefix) :].rstrip(" ?")
    return normalized.rstrip("?")
