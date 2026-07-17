"""Deterministic normalization helpers for the Canonical Knowledge Library.

These helpers are intentionally conservative:
- they lowercase input,
- collapse punctuation and repeated whitespace,
- preserve word boundaries,
- and avoid aggressive stemming or synonym expansion.

That keeps exact retrieval predictable and reduces false matches for biblical
names and terms.
"""

from __future__ import annotations

import re

STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "about",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "me",
        "of",
        "on",
        "tell",
        "the",
        "to",
        "what",
        "when",
        "where",
        "why",
        "with",
    }
)

_APOSTROPHE_TRANSLATION = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "‛": "'",
        "´": "'",
        "`": "'",
    }
)


def normalize_text(value: str) -> str:
    """Return a conservative normalized text form.

    Apostrophes are removed, punctuation becomes whitespace, and repeated
    whitespace collapses to a single space.
    """

    if not isinstance(value, str):
        raise TypeError("value must be a string")
    text = value.translate(_APOSTROPHE_TRANSLATION).strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[\u2010-\u2015_/]+", " ", text)
    text = re.sub(r"[^a-z0-9\s'-]+", " ", text)
    text = text.replace("'", "")
    text = re.sub(r"[-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_id(value: str) -> str:
    """Normalize an identifier into lowercase kebab-case."""

    normalized = normalize_text(value)
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized


def normalize_alias(value: str) -> str:
    """Normalize an alias or question phrase for exact comparison."""

    return normalize_text(value)


def tokenize_query(value: str) -> list[str]:
    """Split normalized text into tokens without stemming or synonym logic."""

    normalized = normalize_text(value)
    if not normalized:
        return []
    return normalized.split()

