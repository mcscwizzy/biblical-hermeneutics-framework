"""Typed lexical records used by the SQLite lexical layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


WORD_STUDY_GUARDRAILS = (
    "Do not import the entire semantic range into one occurrence.",
    "A Strong's number is an index identifier, not the final contextual meaning.",
    "A word's meaning is constrained by its sentence, discourse, author, genre, and historical setting.",
    "The inflected form and grammatical role matter.",
    "Historical roots or etymology must not override contextual usage.",
)


@dataclass(frozen=True)
class LexiconSource:
    name: str
    repository_url: str
    revision: str
    license: str
    attribution: str
    imported_at: str
    content_hash: str
    redistribution_status: str = "unknown"


@dataclass(frozen=True)
class LexiconSense:
    gloss: str
    definition: str | None = None
    semantic_domain: str | None = None
    usage_note: str | None = None
    source_name: str | None = None
    source_sense_id: str | None = None
    sense_order: int = 1


@dataclass(frozen=True)
class LexiconEntry:
    id: int | None
    language: str
    lemma: str
    normalized_lemma: str
    transliteration: str | None
    normalized_transliteration: str | None
    pronunciation: str | None
    strongs_number: str | None
    normalized_strongs_number: str | None
    strongs_digits: str | None
    part_of_speech: str | None
    short_gloss: str | None
    definition: str | None
    source_name: str
    source_entry_id: str
    source_revision: str
    license: str
    attribution: str
    senses: tuple[LexiconSense, ...] = ()


@dataclass(frozen=True)
class WordForm:
    id: int | None
    language: str
    surface_form: str
    normalized_form: str
    lemma: str
    normalized_lemma: str
    transliteration: str | None
    normalized_transliteration: str | None
    strongs_number: str | None
    normalized_strongs_number: str | None
    strongs_digits: str | None
    morphology_code: str | None
    morphology: dict[str, Any]
    lexicon_entry_id: int | None
    source_name: str | None = None
    source_word_id: str | None = None


@dataclass(frozen=True)
class VerseWord:
    id: int | None
    book: str
    chapter: int
    verse: int
    word_position: int
    source_word_id: str | None
    language: str
    surface_form: str
    normalized_form: str
    lemma: str
    normalized_lemma: str
    transliteration: str | None
    normalized_transliteration: str | None
    strongs_number: str | None
    normalized_strongs_number: str | None
    strongs_digits: str | None
    morphology_code: str | None
    morphology: dict[str, Any]
    lexicon_entry_id: int | None
    source_name: str | None = None


@dataclass(frozen=True)
class RepresentativeOccurrence:
    reference: str
    surface_form: str
    morphology_code: str | None
    morphology: dict[str, Any]
    source_word_id: str | None = None


@dataclass(frozen=True)
class WordStudyContext:
    reference: str
    language: str | None = None
    surface_form: str | None = None
    lemma: str | None = None
    transliteration: str | None = None
    pronunciation: str | None = None
    strongs_number: str | None = None
    morphology_code: str | None = None
    morphology: dict[str, Any] = field(default_factory=dict)
    short_glosses: tuple[str, ...] = ()
    contextual_sense: str | None = None
    contextual_explanation: str | None = None
    representative_occurrences: tuple[RepresentativeOccurrence, ...] = ()
    source_entries: tuple[LexiconEntry, ...] = ()
    guardrails: tuple[str, ...] = WORD_STUDY_GUARDRAILS
    confidence: str = "deterministic"
    ambiguities: tuple[str, ...] = ()

    def to_prompt_context(self, *, max_tokens: int = 350) -> str:
        lines = [
            "LEXICAL CONTEXT",
            f"Reference: {self.reference}",
        ]
        if self.surface_form:
            lines.append(f"Original form: {self.surface_form}")
        if self.lemma:
            lines.append(f"Lemma: {self.lemma}")
        if self.transliteration:
            lines.append(f"Transliteration: {self.transliteration}")
        if self.strongs_number:
            lines.append(f"Strong's: {self.strongs_number}")
        plain_morphology = _plain_morphology(self.morphology)
        if plain_morphology:
            lines.append(f"Morphology: {plain_morphology}")
        if self.short_glosses:
            lines.append("Documented gloss range:")
            lines.extend(f"- {gloss}" for gloss in self.short_glosses[:5])
        if self.representative_occurrences:
            lines.append("Representative uses:")
            for occurrence in self.representative_occurrences[:5]:
                lines.append(f"- {occurrence.reference}: {occurrence.surface_form}")
        lines.append("Interpretation cautions:")
        lines.extend(f"- {guardrail}" for guardrail in self.guardrails[:3])
        if self.source_entries:
            lines.append("Sources:")
            source_names = sorted({entry.source_name for entry in self.source_entries})
            lines.extend(f"- {source_name}" for source_name in source_names[:5])
        return _truncate_words("\n".join(lines), max_tokens=max_tokens)


def _plain_morphology(morphology: dict[str, Any]) -> str:
    ordered_keys = (
        "part_of_speech",
        "stem",
        "conjugation",
        "tense",
        "voice",
        "mood",
        "person",
        "gender",
        "number",
        "case",
        "state",
    )
    return ", ".join(str(morphology[key]) for key in ordered_keys if morphology.get(key))


def _truncate_words(value: str, *, max_tokens: int) -> str:
    words = value.split()
    if len(words) <= max_tokens:
        return value
    return " ".join(words[:max_tokens]).rstrip() + " ..."
