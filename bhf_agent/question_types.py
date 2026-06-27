"""Deterministic question-type classification for BHF routing."""

from __future__ import annotations

import re
import unicodedata

from .models import QuestionContext, ReferenceContext


SUPPORTED_QUESTION_TYPES = {
    "passage_study",
    "word_study",
    "topic_study",
    "historical_context",
    "unknown",
}

HEBREW_TERMS = {
    "ruach",
    "ruah",
    "nephesh",
    "shalom",
    "hesed",
    "elohim",
    "yahweh",
    "adonai",
    "torah",
    "sheol",
    "qadosh",
}
TERM_ALIASES = {
    "ruah": "ruach",
    "ruaḥ": "ruach",
    "rûaḥ": "ruach",
}
GREEK_TERMS = {
    "agape",
    "logos",
    "pneuma",
    "ekklesia",
    "charis",
    "pistis",
    "christos",
    "kyrios",
    "dikaiosune",
}

WORD_STUDY_RE = re.compile(
    r"\b("
    r"what\s+(?:is|are)\s+the\s+(?:hebrew|greek)\s+word"
    r"|what\s+does\s+[\w\u0080-\uffff'\-]+\s+mean"
    r"|(?:hebrew|greek)\s+word\s+for"
    r"|meaning\s+of\s+[\w\u0080-\uffff'\-]+"
    r")\b",
    re.IGNORECASE,
)
HISTORICAL_CONTEXT_RE = re.compile(
    r"\b("
    r"historical\s+context|cultural\s+context|ancient\s+near\s+eastern\s+background|"
    r"background\s+of|what\s+was\s+going\s+on\s+when|context\s+of"
    r")\b",
    re.IGNORECASE,
)
PASSAGE_STUDY_RE = re.compile(
    r"\b(what\s+does\s+.+\s+mean|explain|walk\s+me\s+through|what\s+is\s+.+\s+about)\b",
    re.IGNORECASE,
)
TOPIC_STUDY_RE = re.compile(
    r"\b(what\s+does\s+(?:the\s+bible|scripture|paul|jesus)\s+say\s+about|"
    r"what\s+is\s+.+\s+by\s+.+|doctrine\s+of|topic\s+of)\b",
    re.IGNORECASE,
)


def classify_question_type(
    question: str,
    reference_context: ReferenceContext | None = None,
) -> QuestionContext:
    """Classify a user question into a broad BHF answer workflow."""

    normalized = _normalize(question)
    lowered = normalized.lower()
    ascii_lowered = _ascii_fold(normalized).lower()

    if _is_word_study(lowered, ascii_lowered):
        language = _detect_language(lowered, ascii_lowered)
        return QuestionContext(
            question_type="word_study",
            target_language=language,
            target_terms=_extract_word_targets(question),
            confidence=0.86 if language else 0.78,
        )

    if HISTORICAL_CONTEXT_RE.search(lowered):
        return QuestionContext(
            question_type="historical_context",
            target_language=None,
            target_terms=[],
            confidence=0.82,
        )

    if reference_context and reference_context.is_reference_based:
        if PASSAGE_STUDY_RE.search(lowered) or reference_context.book:
            return QuestionContext(
                question_type="passage_study",
                target_language=None,
                target_terms=[],
                confidence=0.82,
            )

    if TOPIC_STUDY_RE.search(lowered):
        return QuestionContext(
            question_type="topic_study",
            target_language=None,
            target_terms=[],
            confidence=0.74,
        )

    if PASSAGE_STUDY_RE.search(lowered):
        return QuestionContext(
            question_type="passage_study",
            target_language=None,
            target_terms=[],
            confidence=0.58,
        )

    return QuestionContext(
        question_type="unknown",
        target_language=None,
        target_terms=[],
        confidence=0.25,
    )


def _is_word_study(lowered: str, ascii_lowered: str) -> bool:
    if WORD_STUDY_RE.search(lowered):
        return True
    if _contains_term(ascii_lowered, HEBREW_TERMS | GREEK_TERMS):
        return bool(re.search(r"\b(meaning|mean|word|hebrew|greek)\b", lowered))
    return False


def _detect_language(lowered: str, ascii_lowered: str) -> str | None:
    tokens = set(ascii_lowered.split())
    if "hebrew" in tokens or _contains_term(ascii_lowered, HEBREW_TERMS):
        return "Hebrew"
    if "greek" in tokens or _contains_term(ascii_lowered, GREEK_TERMS):
        return "Greek"
    return None


def _extract_word_targets(question: str) -> list[str]:
    normalized = _normalize(question)
    lowered = normalized.lower().rstrip("?")
    ascii_lowered = _ascii_fold(normalized).lower().rstrip("?")
    targets: list[str] = []

    for pattern in (
        r"\bword\s+for\s+(?:the\s+word\s+)?(.+)$",
        r"\bwhat\s+does\s+([\w\u0080-\uffff'\-]+)\s+mean\b",
        r"\bmeaning\s+of\s+([\w\u0080-\uffff'\-]+)\b",
    ):
        match = re.search(pattern, lowered, re.IGNORECASE)
        if match:
            targets.extend(_split_terms(match.group(1)))
            break

    for term in sorted(HEBREW_TERMS | GREEK_TERMS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(term)}\b", ascii_lowered):
            targets.append(term)

    return _unique_clean_terms(targets)


def _split_terms(raw_terms: str) -> list[str]:
    cleaned = re.sub(r"\b(in|the|a|an|hebrew|greek|word|for|of)\b", " ", raw_terms)
    parts = re.split(r"\s*(?:/|,|\bor\b|\band\b)\s*", cleaned)
    return [part.strip(" .?!'\"").lower() for part in parts if part.strip()]


def _unique_clean_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for term in terms:
        candidate = " ".join(term.split()).strip(" .?!'\"").lower()
        candidate = TERM_ALIASES.get(
            candidate,
            TERM_ALIASES.get(_ascii_fold(candidate), candidate),
        )
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        cleaned.append(candidate)
    return cleaned


def _normalize(question: str) -> str:
    return " ".join(question.strip().split())


def _ascii_fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _contains_term(text: str, terms: set[str]) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)
