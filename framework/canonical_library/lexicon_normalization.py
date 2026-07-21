"""Conservative lexical normalization for Greek and Hebrew lookup."""

from __future__ import annotations

import re
import unicodedata

VALID_LEXICON_LANGUAGES = frozenset({"hebrew", "aramaic", "greek"})

_HEBREW_MARKS = re.compile(r"[\u0591-\u05bd\u05bf-\u05c7]")
_GREEK_COMBINING_MARKS = re.compile(r"[\u0300-\u036f]")
_PUNCTUATION = re.compile(r"[^0-9a-z\u0370-\u03ff\u0590-\u05ff\s]+")
_SPACE = re.compile(r"\s+")


def normalize_language(language: str) -> str:
    normalized = str(language or "").strip().lower()
    if normalized not in VALID_LEXICON_LANGUAGES:
        raise ValueError(
            "lexicon language must be one of: "
            + ", ".join(sorted(VALID_LEXICON_LANGUAGES))
        )
    return normalized


def normalize_script_form(value: str, *, language: str) -> str:
    """Normalize original-script forms without replacing the stored original."""

    normalized_language = normalize_language(language)
    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    if normalized_language in {"hebrew", "aramaic"}:
        text = _HEBREW_MARKS.sub("", text)
    elif normalized_language == "greek":
        text = _GREEK_COMBINING_MARKS.sub("", text)
        text = text.replace("ς", "σ")
    text = unicodedata.normalize("NFC", text)
    text = _PUNCTUATION.sub(" ", text)
    text = _SPACE.sub(" ", text).strip()
    return text


def normalize_transliteration(value: str | None) -> str:
    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    text = _GREEK_COMBINING_MARKS.sub("", text)
    text = text.replace("ʾ", "").replace("ʿ", "")
    text = re.sub(r"[^0-9a-z\s]+", " ", text)
    return _SPACE.sub(" ", text).strip()


def normalize_strongs_number(value: str | None) -> str | None:
    """Normalize Strong's identifiers while retaining H/G prefixes when present."""

    raw = str(value or "").strip().upper()
    if not raw:
        return None
    match = re.fullmatch(r"([HG])?\s*0*([0-9]+)[A-Z]?", raw)
    if match is None:
        compact = re.sub(r"[^A-Z0-9]+", "", raw)
        return compact or None
    prefix, digits = match.groups()
    if prefix:
        return f"{prefix}{int(digits)}"
    return str(int(digits))


def strongs_digits(value: str | None) -> str | None:
    normalized = normalize_strongs_number(value)
    if not normalized:
        return None
    match = re.fullmatch(r"[HG]?([0-9]+)", normalized)
    if match is None:
        return None
    return str(int(match.group(1)))
