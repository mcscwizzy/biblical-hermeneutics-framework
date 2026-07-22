"""Typed lexical records returned by the BHF word-study service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bhf_agent.models import Serializable


WORD_STUDY_GUARDRAILS = (
    "Strong's is an index identifier, not the meaning of every occurrence.",
    "Do not assume every gloss in the lexical range applies in this passage.",
    "Do not derive the contextual meaning from roots or etymology alone.",
    "English words do not map one-to-one with Greek or Hebrew words.",
    "Context is constrained by grammar, syntax, sentence, paragraph, author, genre, and historical setting.",
)


@dataclass
class LexicalEntry(Serializable):
    language: str
    lemma: str
    transliteration: str | None = None
    strongs_number: str | None = None
    glosses: list[str] = field(default_factory=list)
    definition: str | None = None
    part_of_speech: str | None = None
    source: str = ""
    source_entry_id: str | None = None
    license: str | None = None
    attribution: str | None = None
    senses: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WordOccurrence(Serializable):
    book: str
    chapter: int
    verse: int
    position: int
    language: str
    surface_form: str
    lemma: str
    strongs_number: str | None = None
    morphology: dict[str, Any] = field(default_factory=dict)
    transliteration: str | None = None
    morphology_code: str | None = None
    source: str | None = None
    source_word_id: str | None = None
    gloss: str | None = None

    @property
    def reference(self) -> str:
        return f"{self.book} {self.chapter}:{self.verse}"


@dataclass
class WordStudyResult(Serializable):
    reference: str
    status: str
    language: str | None = None
    surface_form: str | None = None
    lemma: str | None = None
    strongs_number: str | None = None
    transliteration: str | None = None
    morphology: dict[str, Any] = field(default_factory=dict)
    morphology_code: str | None = None
    lexical_range: list[str] = field(default_factory=list)
    lexical_entries: list[LexicalEntry] = field(default_factory=list)
    representative_occurrences: list[WordOccurrence] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    contextual_information: list[str] = field(default_factory=list)
    ambiguities: list[WordOccurrence] = field(default_factory=list)
    message: str | None = None
    guardrails: list[str] = field(default_factory=lambda: list(WORD_STUDY_GUARDRAILS))
    prompt_context: str = ""
    confidence: float = 0.0

    @property
    def is_complete(self) -> bool:
        return self.status == "complete"

    @property
    def is_ambiguous(self) -> bool:
        return self.status == "ambiguous"
