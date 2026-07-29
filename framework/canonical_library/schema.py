"""Canonical object schema and validation utilities."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from .normalization import normalize_alias, normalize_id


SUPPORTED_FRAMEWORK_VERSION = "1.0"
SUPPORTED_SCHEMA_VERSION = "1.0"
SUPPORTED_OBJECT_VERSION = "1"

CONTENT_STATUS_VALUES: tuple[str, ...] = (
    "placeholder",
    "draft",
    "complete",
    "deprecated",
)

REVIEW_STATUS_VALUES: tuple[str, ...] = (
    "unreviewed",
    "in_review",
    "reviewed",
    "approved",
    "rejected",
)

CONFIDENCE_VALUES: tuple[str, ...] = (
    "unrated",
    "low",
    "medium",
    "high",
)

SCRIPTURE_REFERENCE_RELATIONSHIP_VALUES: tuple[str, ...] = (
    "primary",
    "supporting",
    "background",
    "quotation",
    "allusion",
    "typology",
    "fulfillment",
    "contrast",
    "parallel",
)

SOURCE_TYPE_VALUES: tuple[str, ...] = (
    "scripture",
    "ancient-primary-source",
    "academic-book",
    "journal-article",
    "lexicon",
    "grammar",
    "excavation-report",
    "museum-collection",
    "reference-work",
    "confessional-source",
    "other",
)

PROVENANCE_TYPE_VALUES: tuple[str, ...] = (
    "ai",
    "human",
    "import",
    "migration",
    "other",
)

LEGACY_SOURCE_TYPE_ALIASES: dict[str, str] = {
    "biblical-text": "scripture",
    "book": "academic-book",
    "journal": "journal-article",
    "commentary": "reference-work",
    "dictionary": "reference-work",
    "encyclopedia": "reference-work",
    "archaeological-report": "excavation-report",
    "museum": "museum-collection",
    "primary-source": "ancient-primary-source",
    "website": "other",
}

SUBSTANTIVE_SOURCE_TYPE_VALUES: tuple[str, ...] = (
    "scripture",
    "ancient-primary-source",
    "academic-book",
    "journal-article",
    "lexicon",
    "grammar",
    "excavation-report",
    "museum-collection",
    "reference-work",
    "confessional-source",
)

LEGACY_SCRIPTURE_BOOK_TITLES: tuple[str, ...] = (
    "Genesis",
    "Exodus",
    "Leviticus",
    "Numbers",
    "Deuteronomy",
    "Joshua",
    "Judges",
    "Ruth",
    "1 Samuel",
    "2 Samuel",
    "1 Kings",
    "2 Kings",
    "1 Chronicles",
    "2 Chronicles",
    "Ezra",
    "Nehemiah",
    "Esther",
    "Job",
    "Psalms",
    "Proverbs",
    "Ecclesiastes",
    "Song of Songs",
    "Isaiah",
    "Jeremiah",
    "Lamentations",
    "Ezekiel",
    "Daniel",
    "Hosea",
    "Joel",
    "Amos",
    "Obadiah",
    "Jonah",
    "Micah",
    "Nahum",
    "Habakkuk",
    "Zephaniah",
    "Haggai",
    "Zechariah",
    "Malachi",
    "Matthew",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Romans",
    "1 Corinthians",
    "2 Corinthians",
    "Galatians",
    "Ephesians",
    "Philippians",
    "Colossians",
    "1 Thessalonians",
    "2 Thessalonians",
    "1 Timothy",
    "2 Timothy",
    "Titus",
    "Philemon",
    "Hebrews",
    "James",
    "1 Peter",
    "2 Peter",
    "1 John",
    "2 John",
    "3 John",
    "Jude",
    "Revelation",
)

INTERPRETIVE_NOTE_TYPE_VALUES: tuple[str, ...] = (
    "textual-observation",
    "literary-observation",
    "historical-context",
    "ancient-near-east-context",
    "hebraic-worldview",
    "second-temple-context",
    "canonical-connection",
    "theological-interpretation",
    "interpretive-caution",
    "later-reception",
)

INTERPRETIVE_NOTE_CERTAINTY_VALUES: tuple[str, ...] = (
    "textually_explicit",
    "strong_consensus",
    "probable",
    "plausible",
    "disputed",
    "tradition_dependent",
    "speculative",
    "insufficient_evidence",
    # Legacy values remain readable during the controlled migration.
    "high",
    "medium",
    "low",
    "unknown",
)

INTERPRETIVE_NOTE_DISPUTE_STATUS_VALUES: tuple[str, ...] = (
    "not_disputed",
    "minor_scholarly_disagreement",
    "major_scholarly_disagreement",
    "denominational_disagreement",
    "textual_variant",
    "historical_uncertainty",
    "chronological_uncertainty",
    "archaeological_uncertainty",
    "lexical_uncertainty",
    # Legacy values remain readable during the controlled migration.
    "consensus",
    "broad-consensus",
    "majority",
    "disputed",
    "minority",
    "confessional",
    "unknown",
)

CURRENT_CERTAINTY_VALUES: tuple[str, ...] = (
    "textually_explicit",
    "strong_consensus",
    "probable",
    "plausible",
    "disputed",
    "tradition_dependent",
    "speculative",
    "insufficient_evidence",
)

CURRENT_DISPUTE_STATUS_VALUES: tuple[str, ...] = (
    "not_disputed",
    "minor_scholarly_disagreement",
    "major_scholarly_disagreement",
    "denominational_disagreement",
    "textual_variant",
    "historical_uncertainty",
    "chronological_uncertainty",
    "archaeological_uncertainty",
    "lexical_uncertainty",
)

SECTION_STATUS_VALUES: tuple[str, ...] = (
    "missing",
    "generated",
    "draft",
    "needs_review",
    "reviewed",
    "complete",
    "not_applicable",
)

SECTION_STATUS_FIELDS: tuple[str, ...] = (
    "core_summary",
    "scripture_anchors",
    "historical_context",
    "literary_context",
    "canonical_context",
    "original_audience",
    "lexical_links",
    "intertextuality",
    "interpretive_views",
    "common_misinterpretations",
    "sources",
    "relationships",
    "retrieval_metadata",
    "human_review",
)

KNOWLEDGE_LAYER_VALUES: tuple[str, ...] = (
    "biblical_text",
    "historical_cultural",
    "ancient_near_eastern",
    "second_temple_jewish",
    "greco_roman",
    "literary",
    "lexical",
    "archaeology",
    "biblical_theology",
    "systematic_theology",
    "reception_history",
    "denominational_interpretation",
    "pastoral_application",
)

KNOWLEDGE_LAYER_PRIORITY: tuple[str, ...] = (
    "biblical_text",
    "literary",
    "historical_cultural",
    "ancient_near_eastern",
    "second_temple_jewish",
    "greco_roman",
    "lexical",
    "archaeology",
    "biblical_theology",
    "systematic_theology",
    "reception_history",
    "denominational_interpretation",
    "pastoral_application",
)

CLAIM_TYPE_VALUES: tuple[str, ...] = (
    "biblical_text",
    "literary",
    "historical_cultural",
    "lexical",
    "archaeology",
    "biblical_theology",
    "systematic_theology",
    "reception_history",
    "denominational_interpretation",
    "pastoral_application",
)

CONTEXT_APPLICABILITY_FIELDS: tuple[str, ...] = (
    "historical",
    "ancient_near_east",
    "hebraic_worldview",
    "second_temple",
    "canonical",
    "later_christian_reception",
)


def default_context_applicability() -> dict[str, bool]:
    return {field_name: True for field_name in CONTEXT_APPLICABILITY_FIELDS}


def default_section_status() -> dict[str, str]:
    return {field_name: "missing" for field_name in SECTION_STATUS_FIELDS}


DEFAULT_PRIMARY_KNOWLEDGE_LAYER_BY_TYPE: dict[str, str] = {
    "archaeology": "archaeology",
    "biblical_theology": "biblical_theology",
    "book": "biblical_text",
    "covenant": "biblical_theology",
    "cultural_background": "historical_cultural",
    "doctrine": "systematic_theology",
    "event": "biblical_text",
    "faq": "pastoral_application",
    "institution": "historical_cultural",
    "literary_device": "literary",
    "person": "biblical_text",
    "place": "historical_cultural",
    "prophecy": "biblical_text",
    "symbol": "literary",
    "theme": "biblical_theology",
    "theology": "systematic_theology",
    "timeline": "historical_cultural",
    "word_study": "lexical",
}


def default_knowledge_layers(object_type: str | None = None) -> dict[str, Any]:
    primary = DEFAULT_PRIMARY_KNOWLEDGE_LAYER_BY_TYPE.get(
        str(object_type or "").strip().lower(),
        "biblical_text",
    )
    return {"primary": primary, "secondary": []}

DEFAULT_GOVERNANCE_METADATA: dict[str, Any] = {
    "content_status": "placeholder",
    "review_status": "unreviewed",
    "generated_by": [],
    "edited_by": [],
    "reviewed_by": [],
    "last_reviewed": None,
    "confidence": "unrated",
    "human_review_required": True,
}

DEFAULT_CANONICAL_METADATA: dict[str, Any] = {
    **DEFAULT_GOVERNANCE_METADATA,
    "context_applicability": default_context_applicability(),
    "authorship_positions": [],
    "date_ranges": [],
    "original_audience": "",
    "historical_setting": "",
    "canonical_role": "",
    "hebraic_worldview": "",
    "second_temple_context": "",
    "canonical_context": "",
    "later_christian_reception": "",
    "genre": [],
    "structure": [],
    "major_themes": [],
    "canonical_placement": "",
    "key_people": [],
    "key_places": [],
    "key_events": [],
    "interpretive_disputes": [],
    "primary_sources": [],
    "related_entries": [],
    "keywords": [],
    "related_objects": [],
    "scripture_references": [],
    "sources": [],
    "claims": [],
    "section_status": default_section_status(),
    "knowledge_layers": default_knowledge_layers(),
    "canonical_story": {
        "phase": "",
        "role": "",
        "preceded_by": [],
        "followed_by": [],
    },
    "hermeneutical_lens": {
        "immediate_literary_context": "",
        "book_context": "",
        "canonical_context": "",
        "covenant_context": "",
        "historical_context": "",
        "ancient_near_east_context": "",
        "second_temple_jewish_context": "",
        "original_audience": "",
        "genre": "",
        "intertextual_connections": [],
        "biblical_theology_themes": [],
        "messianic_christological_trajectory": "",
        "major_interpretive_views": [],
        "historical_interpretation": "",
        "authorial_intent": "",
        "typological_connections": [],
        "christological_significance": "",
        "modern_application_principles": [],
        "common_misinterpretations": [],
    },
    "retrieval_metadata": {
        "aliases": [],
        "search_terms": [],
        "common_questions": [],
        "related_topics": [],
        "frequently_confused_with": [],
        "semantic_keywords": [],
    },
}

SUPPORTED_CATEGORIES: tuple[str, ...] = (
    "theology",
    "theme",
    "person",
    "place",
    "event",
    "book",
    "word_study",
    "archaeology",
    "institution",
    "prophecy",
    "faq",
    "timeline",
    "covenant",
    "biblical_theology",
    "cultural_background",
    "symbol",
    "literary_device",
    "doctrine",
)

COMMON_REQUIRED_SECTIONS: tuple[str, ...] = (
    "core_summary",
    "scripture_anchors",
    "sources",
    "relationships",
    "retrieval_metadata",
    "human_review",
)

TYPE_SPECIFIC_REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "archaeology": (
        "historical_context",
        "canonical_context",
        "interpretive_views",
        "common_misinterpretations",
    ),
    "biblical_theology": (
        "canonical_context",
        "intertextuality",
        "interpretive_views",
        "common_misinterpretations",
    ),
    "book": (
        "historical_context",
        "literary_context",
        "canonical_context",
        "original_audience",
        "intertextuality",
        "interpretive_views",
        "common_misinterpretations",
    ),
    "covenant": (
        "historical_context",
        "canonical_context",
        "intertextuality",
        "interpretive_views",
        "common_misinterpretations",
    ),
    "cultural_background": (
        "historical_context",
        "canonical_context",
        "common_misinterpretations",
    ),
    "doctrine": (
        "canonical_context",
        "interpretive_views",
        "common_misinterpretations",
    ),
    "event": ("historical_context", "canonical_context"),
    "faq": ("canonical_context", "common_misinterpretations"),
    "institution": ("historical_context", "canonical_context"),
    "literary_device": (
        "literary_context",
        "interpretive_views",
        "common_misinterpretations",
    ),
    "person": ("historical_context", "canonical_context"),
    "place": ("historical_context", "canonical_context"),
    "prophecy": (
        "historical_context",
        "literary_context",
        "canonical_context",
        "original_audience",
        "intertextuality",
        "interpretive_views",
        "common_misinterpretations",
    ),
    "symbol": (
        "literary_context",
        "canonical_context",
        "intertextuality",
        "common_misinterpretations",
    ),
    "theme": (
        "canonical_context",
        "intertextuality",
        "interpretive_views",
        "common_misinterpretations",
    ),
    "theology": (
        "canonical_context",
        "interpretive_views",
        "common_misinterpretations",
    ),
    "timeline": ("historical_context", "canonical_context"),
    "word_study": (
        "lexical_links",
        "canonical_context",
        "interpretive_views",
        "common_misinterpretations",
    ),
}


def required_sections_for_type(object_type: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            (
                *COMMON_REQUIRED_SECTIONS,
                *TYPE_SPECIFIC_REQUIRED_SECTIONS.get(object_type, ()),
            )
        )
    )


CATEGORY_FOLDERS: dict[str, str] = {
    "theology": "theology",
    "theme": "themes",
    "person": "people",
    "place": "places",
    "event": "events",
    "book": "books",
    "word_study": "word_studies",
    "archaeology": "archaeology",
    "institution": "institutions",
    "prophecy": "prophecy",
    "faq": "faq",
    "timeline": "timeline",
    "covenant": "covenants",
    "biblical_theology": "biblical_theology",
    "cultural_background": "cultural_background",
    "symbol": "symbols",
    "literary_device": "literary_devices",
    "doctrine": "doctrine",
}

MANIFEST_CATEGORY_KEYS: tuple[str, ...] = tuple(dict.fromkeys(CATEGORY_FOLDERS.values()))

REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "type",
    "title",
    "aliases",
    "framework_version",
    "object_version",
    "importance",
)

STRING_FIELDS: tuple[str, ...] = (
    "id",
    "type",
    "title",
    "summary",
    "historical_context",
    "canonical_role",
    "ancient_near_east_context",
    "hebraic_worldview",
    "second_temple_context",
    "canonical_context",
    "later_christian_reception",
    "literary_context",
    "covenantal_significance",
    "original_audience",
    "historical_setting",
    "canonical_placement",
    "framework_version",
    "object_version",
    "content_status",
    "review_status",
    "confidence",
)

LIST_FIELDS: tuple[str, ...] = (
    "aliases",
    "authorship_positions",
    "date_ranges",
    "genre",
    "structure",
    "major_themes",
    "key_people",
    "key_places",
    "key_events",
    "interpretive_disputes",
    "primary_sources",
    "intertextuality",
    "timeline",
    "maps",
    "archaeology",
    "hebrew_words",
    "greek_words",
    "related_people",
    "related_places",
    "related_events",
    "cross_references",
    "new_testament_connections",
    "interpretive_notes",
    "common_questions",
    "related_entries",
    "keywords",
)

UNIQUE_NORMALIZED_LIST_FIELDS: tuple[str, ...] = ("major_themes",)

PROVENANCE_FIELDS: tuple[str, ...] = ("generated_by",)

RELATED_OBJECT_FIELDS: tuple[str, ...] = ("related_objects",)

SCRIPTURE_REFERENCE_FIELDS: tuple[str, ...] = ("scripture_references",)

SOURCE_FIELDS: tuple[str, ...] = ("sources",)

CLAIM_FIELDS: tuple[str, ...] = ("claims",)

MAPPING_FIELDS: tuple[str, ...] = (
    "context_applicability",
    "section_status",
    "knowledge_layers",
    "canonical_story",
    "hermeneutical_lens",
    "retrieval_metadata",
)

CANONICAL_STORY_STRING_FIELDS: tuple[str, ...] = ("phase", "role")
CANONICAL_STORY_LIST_FIELDS: tuple[str, ...] = ("preceded_by", "followed_by")

HERMENEUTICAL_LENS_STRING_FIELDS: tuple[str, ...] = (
    "immediate_literary_context",
    "book_context",
    "canonical_context",
    "covenant_context",
    "historical_context",
    "ancient_near_east_context",
    "second_temple_jewish_context",
    "original_audience",
    "genre",
    "messianic_christological_trajectory",
    "historical_interpretation",
    "authorial_intent",
    "christological_significance",
)
HERMENEUTICAL_LENS_LIST_FIELDS: tuple[str, ...] = (
    "intertextual_connections",
    "biblical_theology_themes",
    "major_interpretive_views",
    "typological_connections",
    "modern_application_principles",
    "common_misinterpretations",
)

RETRIEVAL_METADATA_LIST_FIELDS: tuple[str, ...] = (
    "aliases",
    "search_terms",
    "common_questions",
    "related_topics",
    "frequently_confused_with",
    "semantic_keywords",
)

KNOWLEDGE_LAYER_STRING_FIELDS: tuple[str, ...] = ("primary",)
KNOWLEDGE_LAYER_LIST_FIELDS: tuple[str, ...] = ("secondary",)

RELATED_OBJECT_REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "relationship",
    "weight",
    "notes",
)

RELATED_OBJECT_RELATIONSHIP_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SCRIPTURE_REFERENCE_REQUIRED_FIELDS: tuple[str, ...] = (
    "reference",
    "relationship",
    "notes",
)

INT_FIELDS: tuple[str, ...] = ("importance",)

BOOLEAN_FIELDS: tuple[str, ...] = ("human_review_required",)

OPTIONAL_FIELDS: tuple[str, ...] = ("last_reviewed",)

GOVERNANCE_LIST_FIELDS: tuple[str, ...] = ("edited_by", "reviewed_by")

ALL_FIELDS: tuple[str, ...] = (
    STRING_FIELDS
    + LIST_FIELDS
    + PROVENANCE_FIELDS
    + MAPPING_FIELDS
    + RELATED_OBJECT_FIELDS
    + SCRIPTURE_REFERENCE_FIELDS
    + SOURCE_FIELDS
    + CLAIM_FIELDS
    + INT_FIELDS
    + BOOLEAN_FIELDS
    + OPTIONAL_FIELDS
    + GOVERNANCE_LIST_FIELDS
)


class CanonicalValidationError(ValueError):
    """Raised when a canonical object or library fails validation."""


def _type_name(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return "list"
        item_types = {type(item).__name__ for item in value}
        if item_types == {"str"}:
            return "list[str]"
        return f"list[{', '.join(sorted(item_types))}]"
    return type(value).__name__


def _path_text(path: str | Path | None) -> str:
    if path is None:
        return "<in-memory>"
    return str(path)


def _error(
    message: str,
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> CanonicalValidationError:
    prefix = "Invalid canonical object"
    if path is not None:
        prefix = f"{prefix} in {_path_text(path)}"
    if object_id:
        prefix = f"{prefix} [id={object_id}]"
    return CanonicalValidationError(f"{prefix}: {message}")


def _expected_actual_error(
    field: str,
    expected: str,
    actual: Any,
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> CanonicalValidationError:
    return _error(
        f'field "{field}" expected {expected}, received {_type_name(actual)}',
        path=path,
        object_id=object_id,
    )


def _category_folder(type_name: str) -> str | None:
    return CATEGORY_FOLDERS.get(type_name)


def _normalize_source_type_label(value: Any) -> str:
    normalized = re.sub(r"[\s_]+", "-", str(value).strip().lower())
    return LEGACY_SOURCE_TYPE_ALIASES.get(normalized, normalized)


def _legacy_source_looks_like_scripture(value: str) -> bool:
    normalized = re.sub(r"[,;()\[\]]", " ", value).strip().lower()
    if not normalized:
        return False

    for book_title in sorted(LEGACY_SCRIPTURE_BOOK_TITLES, key=len, reverse=True):
        alias = book_title.lower()
        if normalized == alias:
            return True
        if not normalized.startswith(f"{alias} "):
            continue
        remainder = normalized[len(alias) :].strip()
        if not remainder:
            return True
        if re.fullmatch(r"[0-9][0-9\s:,\-–;&]*", remainder):
            return True

    return False


def _classify_legacy_source_string(value: str) -> str:
    if _legacy_source_looks_like_scripture(value):
        return "scripture"
    return "reference-work"


def _normalize_source_supports(
    value: Any,
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise _expected_actual_error(
            "supports",
            "list[str]",
            value,
            path=path,
            object_id=object_id,
        )

    supports: list[str] = []
    for support in value:
        if not isinstance(support, str):
            raise _expected_actual_error(
                "supports",
                "list[str]",
                value,
                path=path,
                object_id=object_id,
            )
        normalized_support = normalize_id(support)
        if not normalized_support:
            raise _error(
                'field "supports" cannot contain blank values',
                path=path,
                object_id=object_id,
            )
        supports.append(normalized_support)

    return list(dict.fromkeys(supports))


@dataclass(frozen=True)
class CanonicalRelationship:
    id: str
    relationship: str
    weight: int = 1
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "CanonicalRelationship":
        if isinstance(mapping, CanonicalRelationship):
            return mapping
        return validate_related_object_entry(mapping)


@dataclass(frozen=True)
class CanonicalScriptureReference:
    reference: str
    relationship: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "CanonicalScriptureReference":
        if isinstance(mapping, CanonicalScriptureReference):
            return mapping
        return validate_scripture_reference_entry(mapping)


@dataclass(frozen=True)
class CanonicalSource:
    title: str
    author: str = ""
    publisher: str = ""
    year: int | None = None
    locator: str = ""
    url: str = ""
    source_type: str = "other"
    supports: list[str] = field(default_factory=list)
    notes: str = ""
    id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "CanonicalSource":
        if isinstance(mapping, CanonicalSource):
            return mapping
        if isinstance(mapping, str):
            return cls.from_legacy_string(mapping)
        return validate_source_entry(mapping)

    @classmethod
    def from_legacy_string(cls, value: str) -> "CanonicalSource":
        normalized = value.strip()
        if not normalized:
            raise CanonicalValidationError("legacy source strings must not be blank")
        return cls(
            id=normalize_id(normalized),
            title=normalized,
            source_type=_classify_legacy_source_string(normalized),
        )


@dataclass(frozen=True)
class CanonicalProvenance:
    type: str
    name: str
    workflow: str
    date: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "CanonicalProvenance":
        if isinstance(mapping, CanonicalProvenance):
            return mapping
        return validate_provenance_entry(mapping)


@dataclass(frozen=True)
class CanonicalInterpretiveNote:
    note: str
    note_type: str = "textual-observation"
    certainty: str = "unknown"
    dispute_status: str = "unknown"
    sources: list[str] = field(default_factory=list)
    scripture_references: list[str] = field(default_factory=list)
    traditions: list[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, mapping: Any) -> "CanonicalInterpretiveNote":
        if isinstance(mapping, CanonicalInterpretiveNote):
            return mapping
        if isinstance(mapping, str):
            return cls.from_legacy_string(mapping)
        return validate_interpretive_note_entry(mapping)

    @classmethod
    def from_legacy_string(cls, value: str) -> "CanonicalInterpretiveNote":
        normalized = value.strip()
        if not normalized:
            raise CanonicalValidationError("legacy interpretive note strings must not be blank")
        return cls(note=normalized)


@dataclass(frozen=True)
class CanonicalClaim:
    id: str
    claim: str
    claim_type: str
    certainty: str
    dispute_status: str
    scripture_references: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    traditions: list[str] = field(default_factory=list)
    rationale: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "CanonicalClaim":
        if isinstance(mapping, CanonicalClaim):
            return mapping
        return validate_claim_entry(mapping)


@dataclass(frozen=True)
class CanonicalObject:
    id: str
    type: str
    title: str
    aliases: list[str] = field(default_factory=list)
    summary: str = ""
    historical_context: str = ""
    ancient_near_east_context: str = ""
    hebraic_worldview: str = ""
    second_temple_context: str = ""
    canonical_context: str = ""
    later_christian_reception: str = ""
    context_applicability: dict[str, bool] = field(default_factory=default_context_applicability)
    literary_context: str = ""
    covenantal_significance: str = ""
    authorship_positions: list[str] = field(default_factory=list)
    date_ranges: list[str] = field(default_factory=list)
    original_audience: str = ""
    historical_setting: str = ""
    canonical_role: str = ""
    genre: list[str] = field(default_factory=list)
    structure: list[str] = field(default_factory=list)
    major_themes: list[str] = field(default_factory=list)
    canonical_placement: str = ""
    key_people: list[str] = field(default_factory=list)
    key_places: list[str] = field(default_factory=list)
    key_events: list[str] = field(default_factory=list)
    interpretive_disputes: list[str] = field(default_factory=list)
    primary_sources: list[str] = field(default_factory=list)
    related_entries: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    intertextuality: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    maps: list[str] = field(default_factory=list)
    archaeology: list[str] = field(default_factory=list)
    hebrew_words: list[str] = field(default_factory=list)
    greek_words: list[str] = field(default_factory=list)
    related_people: list[str] = field(default_factory=list)
    related_places: list[str] = field(default_factory=list)
    related_events: list[str] = field(default_factory=list)
    related_objects: list[CanonicalRelationship] = field(default_factory=list)
    scripture_references: list[CanonicalScriptureReference] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    new_testament_connections: list[str] = field(default_factory=list)
    interpretive_notes: list[CanonicalInterpretiveNote] = field(default_factory=list)
    common_questions: list[str] = field(default_factory=list)
    sources: list[CanonicalSource] = field(default_factory=list)
    claims: list[CanonicalClaim] = field(default_factory=list)
    section_status: dict[str, str] = field(default_factory=default_section_status)
    knowledge_layers: dict[str, Any] = field(default_factory=default_knowledge_layers)
    canonical_story: dict[str, Any] = field(
        default_factory=lambda: _clone_default_value(DEFAULT_CANONICAL_METADATA["canonical_story"])
    )
    hermeneutical_lens: dict[str, Any] = field(
        default_factory=lambda: _clone_default_value(DEFAULT_CANONICAL_METADATA["hermeneutical_lens"])
    )
    retrieval_metadata: dict[str, Any] = field(
        default_factory=lambda: _clone_default_value(DEFAULT_CANONICAL_METADATA["retrieval_metadata"])
    )
    importance: int = 0
    framework_version: str = SUPPORTED_FRAMEWORK_VERSION
    object_version: str = SUPPORTED_OBJECT_VERSION
    content_status: str = DEFAULT_GOVERNANCE_METADATA["content_status"]
    review_status: str = DEFAULT_GOVERNANCE_METADATA["review_status"]
    generated_by: list[CanonicalProvenance] = field(default_factory=list)
    edited_by: list[str] = field(default_factory=list)
    reviewed_by: list[str] = field(default_factory=list)
    last_reviewed: str | None = DEFAULT_GOVERNANCE_METADATA["last_reviewed"]
    confidence: str = DEFAULT_GOVERNANCE_METADATA["confidence"]
    human_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(
        cls,
        mapping: Mapping[str, Any],
        *,
        path: str | Path | None = None,
    ) -> "CanonicalObject":
        values: dict[str, Any] = {}
        normalized = _apply_governance_defaults(mapping)
        object_id = normalized.get("id") if isinstance(normalized.get("id"), str) else None
        for field_name in ALL_FIELDS:
            if field_name == "related_objects":
                values[field_name] = validate_related_objects_field(
                    normalized,
                    path=path,
                    object_id=object_id,
                )
            elif field_name == "generated_by":
                values[field_name] = normalize_generated_by_field(
                    normalized,
                    path=path,
                    object_id=object_id,
                )
            elif field_name == "scripture_references":
                values[field_name] = validate_scripture_references_field(
                    normalized,
                    path=path,
                    object_id=object_id,
                )
            elif field_name == "sources":
                values[field_name] = normalize_sources_field(
                    normalized,
                    path=path,
                    object_id=object_id,
                )
            elif field_name == "interpretive_notes":
                values[field_name] = normalize_interpretive_notes_field(
                    normalized,
                    path=path,
                    object_id=object_id,
                )
            elif field_name == "claims":
                values[field_name] = validate_claims_field(
                    normalized,
                    path=path,
                    object_id=object_id,
                )
            else:
                values[field_name] = normalized[field_name]
        return cls(**values)


def _apply_governance_defaults(data: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    knowledge_layers_were_missing = "knowledge_layers" not in normalized
    for field_name, default_value in DEFAULT_CANONICAL_METADATA.items():
        if field_name not in normalized:
            normalized[field_name] = _clone_default_value(default_value)
        elif field_name == "context_applicability" and isinstance(normalized[field_name], Mapping):
            normalized[field_name] = {
                **default_context_applicability(),
                **dict(normalized[field_name]),
            }
        elif field_name in {
            "section_status",
            "knowledge_layers",
            "canonical_story",
            "hermeneutical_lens",
            "retrieval_metadata",
        } and isinstance(
            normalized[field_name],
            Mapping,
        ):
            normalized[field_name] = {
                **_clone_default_value(default_value),
                **dict(normalized[field_name]),
            }
    if knowledge_layers_were_missing:
        normalized["knowledge_layers"] = default_knowledge_layers(
            normalized.get("type") if isinstance(normalized.get("type"), str) else None
        )
    normalized = _normalize_governance_metadata(normalized)
    return normalized


def _normalize_provenance_workflow_label(value: Any) -> str:
    return re.sub(r"[\s_]+", "-", str(value).strip().lower())


def _is_legacy_ai_reviewer(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    return bool(normalized) and normalized.startswith("codex")


def _provenance_date(data: Mapping[str, Any]) -> str:
    last_reviewed = data.get("last_reviewed")
    if isinstance(last_reviewed, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", last_reviewed):
        return last_reviewed
    return date.today().isoformat()


def _normalize_provenance_dict(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> CanonicalProvenance:
    if isinstance(data, CanonicalProvenance):
        return data
    if not isinstance(data, Mapping):
        raise _expected_actual_error(
            "generated_by",
            "list[dict]",
            data,
            path=path,
            object_id=object_id,
        )

    unknown_fields = sorted(set(data) - {"type", "name", "workflow", "date"})
    if unknown_fields:
        raise _error(
            f'unknown provenance field(s): {", ".join(unknown_fields)}',
            path=path,
            object_id=object_id,
        )

    provenance_type = _normalize_provenance_workflow_label(data.get("type"))
    if provenance_type not in PROVENANCE_TYPE_VALUES:
        raise _error(
            f'field "type" must be one of {", ".join(PROVENANCE_TYPE_VALUES)}',
            path=path,
            object_id=object_id,
        )

    name = data.get("name")
    workflow = data.get("workflow")
    provenance_date = data.get("date")
    for field_name, value in (("name", name), ("workflow", workflow), ("date", provenance_date)):
        if not isinstance(value, str) or not value.strip():
            raise _error(
                f'field "{field_name}" is required and must be a non-empty string',
                path=path,
                object_id=object_id,
            )
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", provenance_date):
        raise _error(
            'field "date" must use YYYY-MM-DD format',
            path=path,
            object_id=object_id,
        )
    try:
        date.fromisoformat(provenance_date)
    except ValueError as exc:
        raise _error(
            'field "date" must be a valid YYYY-MM-DD date',
            path=path,
            object_id=object_id,
        ) from exc

    return CanonicalProvenance(
        type=provenance_type,
        name=name.strip(),
        workflow=_normalize_provenance_workflow_label(workflow),
        date=provenance_date,
    )


def validate_provenance_entry(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> CanonicalProvenance:
    return _normalize_provenance_dict(data, path=path, object_id=object_id)


def normalize_generated_by_field(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> list[CanonicalProvenance]:
    if "generated_by" not in data:
        return []
    generated_by = data["generated_by"]
    if generated_by is None:
        raise _expected_actual_error(
            "generated_by",
            "list[dict]",
            generated_by,
            path=path,
            object_id=object_id,
        )
    if not isinstance(generated_by, list):
        raise _expected_actual_error(
            "generated_by",
            "list[dict]",
            generated_by,
            path=path,
            object_id=object_id,
        )

    normalized_generated_by: list[CanonicalProvenance] = []
    for item in generated_by:
        normalized_generated_by.append(
            validate_provenance_entry(item, path=path, object_id=object_id)
        )
    return normalized_generated_by


def normalize_string_list_field(
    values: Any,
    *,
    field_name: str,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> list[str]:
    if values is None:
        raise _expected_actual_error(field_name, "list[str]", values, path=path, object_id=object_id)
    if not isinstance(values, list):
        raise _expected_actual_error(field_name, "list[str]", values, path=path, object_id=object_id)

    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise _error(
                f'field "{field_name}" must be a list of strings',
                path=path,
                object_id=object_id,
            )
        normalized_value = value.strip()
        if not normalized_value:
            raise _error(
                f'field "{field_name}" cannot contain blank values',
                path=path,
                object_id=object_id,
            )
        if normalized_value not in normalized:
            normalized.append(normalized_value)
    return normalized


def _build_ai_provenance_record(
    *,
    data: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "type": "ai",
        "name": "codex",
        "workflow": "ane-hebraic-context-expansion",
        "date": _provenance_date(data),
    }


def _merge_unique_provenance(
    existing: list[CanonicalProvenance],
    values: Sequence[Mapping[str, Any]],
) -> list[CanonicalProvenance]:
    seen = {
        (
            item.type,
            item.name,
            item.workflow,
            item.date,
        )
        for item in existing
    }
    for value in values:
        provenance = validate_provenance_entry(value)
        key = (provenance.type, provenance.name, provenance.workflow, provenance.date)
        if key in seen:
            continue
        existing.append(provenance)
        seen.add(key)
    return existing


def _normalize_governance_metadata(data: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    object_id = normalized.get("id") if isinstance(normalized.get("id"), str) else None

    raw_generated_by = normalized.get("generated_by")
    generated_by = [] if raw_generated_by is None else normalize_generated_by_field(
        normalized,
        object_id=object_id,
    )

    raw_edited_by = normalized.get("edited_by", [])
    edited_by = normalize_string_list_field(
        raw_edited_by,
        field_name="edited_by",
        object_id=object_id,
    )

    raw_reviewed_by = normalized.get("reviewed_by", [])
    reviewed_by = normalize_string_list_field(
        raw_reviewed_by,
        field_name="reviewed_by",
        object_id=object_id,
    )

    migrated_reviewers: list[str] = []
    human_reviewers: list[str] = []
    for reviewer in reviewed_by:
        if _is_legacy_ai_reviewer(reviewer):
            migrated_reviewers.append(reviewer)
        else:
            human_reviewers.append(reviewer)

    if migrated_reviewers:
        migrated_records = [
            _build_ai_provenance_record(data=normalized)
            for _reviewer in migrated_reviewers
        ]
        generated_by = _merge_unique_provenance(generated_by, migrated_records)

    normalized["generated_by"] = [item.to_dict() for item in generated_by]
    normalized["edited_by"] = edited_by
    normalized["reviewed_by"] = human_reviewers

    review_status = str(normalized.get("review_status") or "unreviewed").strip().lower()
    normalized["human_review_required"] = review_status in {"unreviewed", "in_review"} or not human_reviewers

    return normalized


def _clone_default_value(value: Any) -> Any:
    if isinstance(value, list):
        return [_clone_default_value(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _clone_default_value(item) for key, item in value.items()}
    return value


def validate_required_fields(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> None:
    object_id = data.get("id") if isinstance(data.get("id"), str) else None
    for field_name in REQUIRED_FIELDS:
        if field_name not in data:
            raise _error(f'field "{field_name}" is required', path=path, object_id=object_id)
        value = data[field_name]
        if field_name == "aliases":
            if not isinstance(value, list):
                raise _expected_actual_error(
                    "aliases",
                    "list[str]",
                    value,
                    path=path,
                    object_id=object_id,
                )
            if not value:
                raise _error(
                    'field "aliases" must contain at least one alias',
                    path=path,
                    object_id=object_id,
                )
            continue
        if field_name in {"id", "type", "title", "framework_version", "object_version"}:
            if not isinstance(value, str) or not value.strip():
                raise _error(
                    f'field "{field_name}" is required and must be a non-empty string',
                    path=path,
                    object_id=object_id,
                )
            continue
        if field_name == "importance":
            if isinstance(value, bool) or not isinstance(value, int):
                raise _error(
                    'field "importance" is required and must be an integer',
                    path=path,
                    object_id=object_id,
                )


def _validate_mapping_string_field(
    mapping: Mapping[str, Any],
    *,
    parent_field: str,
    field_name: str,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> None:
    value = mapping.get(field_name, "")
    if not isinstance(value, str):
        raise _expected_actual_error(
            f"{parent_field}.{field_name}",
            "str",
            value,
            path=path,
            object_id=object_id,
        )


def _validate_mapping_string_list_field(
    mapping: Mapping[str, Any],
    *,
    parent_field: str,
    field_name: str,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> None:
    value = mapping.get(field_name, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise _expected_actual_error(
            f"{parent_field}.{field_name}",
            "list[str]",
            value,
            path=path,
            object_id=object_id,
        )


def _validate_structured_mapping_field(
    data: Mapping[str, Any],
    *,
    field_name: str,
    string_fields: Sequence[str] = (),
    list_fields: Sequence[str] = (),
    path: str | Path | None = None,
    object_id: str | None = None,
) -> None:
    if field_name not in data:
        return
    value = data[field_name]
    if not isinstance(value, Mapping):
        raise _expected_actual_error(
            field_name,
            "dict",
            value,
            path=path,
            object_id=object_id,
        )
    allowed_fields = set(string_fields) | set(list_fields)
    unknown_fields = sorted(set(value) - allowed_fields)
    if unknown_fields:
        raise _error(
            f'unknown {field_name} field(s): {", ".join(unknown_fields)}',
            path=path,
            object_id=object_id,
        )
    for nested_field in string_fields:
        _validate_mapping_string_field(
            value,
            parent_field=field_name,
            field_name=nested_field,
            path=path,
            object_id=object_id,
        )
    for nested_field in list_fields:
        _validate_mapping_string_list_field(
            value,
            parent_field=field_name,
            field_name=nested_field,
            path=path,
            object_id=object_id,
        )


def validate_field_types(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> None:
    object_id = data.get("id") if isinstance(data.get("id"), str) else None
    for field_name in STRING_FIELDS:
        if field_name not in data:
            continue
        value = data[field_name]
        if not isinstance(value, str):
            raise _expected_actual_error(
                field_name,
                "str",
                value,
                path=path,
                object_id=object_id,
            )
    for field_name in PROVENANCE_FIELDS:
        if field_name not in data:
            continue
        value = data[field_name]
        if not isinstance(value, list):
            raise _expected_actual_error(
                field_name,
                "list[dict]",
                value,
                path=path,
                object_id=object_id,
            )
        if any(not isinstance(item, Mapping) for item in value):
            raise _expected_actual_error(
                field_name,
                "list[dict]",
                value,
                path=path,
                object_id=object_id,
            )
    for field_name in LIST_FIELDS:
        if field_name not in data:
            continue
        value = data[field_name]
        if field_name == "interpretive_notes":
            if not isinstance(value, list):
                raise _expected_actual_error(
                    field_name,
                    "list[str] or list[dict]",
                    value,
                    path=path,
                    object_id=object_id,
                )
            if any(not isinstance(item, (str, Mapping)) for item in value):
                raise _expected_actual_error(
                    field_name,
                    "list[str] or list[dict]",
                    value,
                    path=path,
                    object_id=object_id,
                )
            if any(isinstance(item, str) and not item.strip() for item in value):
                raise _error(
                    'field "interpretive_notes" cannot contain blank legacy note strings',
                    path=path,
                    object_id=object_id,
                )
            continue
        if not isinstance(value, list):
            raise _expected_actual_error(
                field_name,
                "list[str]",
                value,
                path=path,
                object_id=object_id,
            )
        if any(not isinstance(item, str) for item in value):
            raise _expected_actual_error(
                field_name,
                "list[str]",
                value,
                path=path,
                object_id=object_id,
            )
    for field_name in GOVERNANCE_LIST_FIELDS:
        if field_name not in data:
            continue
        value = data[field_name]
        if not isinstance(value, list):
            raise _expected_actual_error(
                field_name,
                "list[str]",
                value,
                path=path,
                object_id=object_id,
            )
        if any(not isinstance(item, str) for item in value):
            raise _error(
                f'field "{field_name}" must be a list of strings',
                path=path,
                object_id=object_id,
            )
    for field_name in BOOLEAN_FIELDS:
        if field_name not in data:
            continue
        value = data[field_name]
        if not isinstance(value, bool):
            raise _expected_actual_error(
                field_name,
                "bool",
                value,
                path=path,
                object_id=object_id,
            )
    if "related_objects" in data:
        value = data["related_objects"]
        if not isinstance(value, list):
            raise _expected_actual_error(
                "related_objects",
                "list[dict]",
                value,
                path=path,
                object_id=object_id,
            )
        if any(not isinstance(item, Mapping) for item in value):
            raise _expected_actual_error(
                "related_objects",
                "list[dict]",
                value,
                path=path,
                object_id=object_id,
            )
    if "scripture_references" in data:
        value = data["scripture_references"]
        if not isinstance(value, list):
            raise _expected_actual_error(
                "scripture_references",
                "list[dict]",
                value,
                path=path,
                object_id=object_id,
            )
        if any(not isinstance(item, Mapping) for item in value):
            raise _expected_actual_error(
                "scripture_references",
                "list[dict]",
                value,
                path=path,
                object_id=object_id,
            )
    if "sources" in data:
        value = data["sources"]
        if not isinstance(value, list):
            raise _expected_actual_error(
                "sources",
                "list[str] or list[dict]",
                value,
                path=path,
                object_id=object_id,
            )
        if any(not isinstance(item, (str, Mapping)) for item in value):
            raise _expected_actual_error(
                "sources",
                "list[str] or list[dict]",
                value,
                path=path,
                object_id=object_id,
            )
        if any(isinstance(item, str) and not item.strip() for item in value):
            raise _error(
                'field "sources" cannot contain blank legacy source strings',
                path=path,
                object_id=object_id,
            )
    if "claims" in data:
        value = data["claims"]
        if not isinstance(value, list) or any(
            not isinstance(item, Mapping) for item in value
        ):
            raise _expected_actual_error(
                "claims",
                "list[dict]",
                value,
                path=path,
                object_id=object_id,
            )
    if "context_applicability" in data:
        value = data["context_applicability"]
        if not isinstance(value, Mapping):
            raise _expected_actual_error(
                "context_applicability",
                "dict[str, bool]",
                value,
                path=path,
                object_id=object_id,
            )
        unknown_fields = sorted(set(value) - set(CONTEXT_APPLICABILITY_FIELDS))
        if unknown_fields:
            raise _error(
                f'unknown context applicability field(s): {", ".join(unknown_fields)}',
                path=path,
                object_id=object_id,
            )
        for field_name, flag in value.items():
            if isinstance(flag, bool):
                continue
            raise _expected_actual_error(
                field_name,
                "bool",
                flag,
                path=path,
                object_id=object_id,
            )
    if "section_status" in data:
        value = data["section_status"]
        if not isinstance(value, Mapping):
            raise _expected_actual_error(
                "section_status",
                "dict[str, str]",
                value,
                path=path,
                object_id=object_id,
            )
        unknown_fields = sorted(set(value) - set(SECTION_STATUS_FIELDS))
        if unknown_fields:
            raise _error(
                f'unknown section status field(s): {", ".join(unknown_fields)}',
                path=path,
                object_id=object_id,
            )
        for section_name, status in value.items():
            if not isinstance(status, str) or status not in SECTION_STATUS_VALUES:
                raise _error(
                    f'field "section_status.{section_name}" must be one of '
                    f'{", ".join(SECTION_STATUS_VALUES)}',
                    path=path,
                    object_id=object_id,
                )
    _validate_structured_mapping_field(
        data,
        field_name="knowledge_layers",
        string_fields=KNOWLEDGE_LAYER_STRING_FIELDS,
        list_fields=KNOWLEDGE_LAYER_LIST_FIELDS,
        path=path,
        object_id=object_id,
    )
    knowledge_layers = data.get("knowledge_layers")
    if isinstance(knowledge_layers, Mapping):
        primary = knowledge_layers.get("primary")
        secondary = knowledge_layers.get("secondary", [])
        if primary not in KNOWLEDGE_LAYER_VALUES:
            raise _error(
                'field "knowledge_layers.primary" must be one of '
                + ", ".join(KNOWLEDGE_LAYER_VALUES),
                path=path,
                object_id=object_id,
            )
        invalid_secondary = [
            value for value in secondary if value not in KNOWLEDGE_LAYER_VALUES
        ]
        if invalid_secondary:
            raise _error(
                'field "knowledge_layers.secondary" contains unsupported '
                f'layer(s): {", ".join(invalid_secondary)}',
                path=path,
                object_id=object_id,
            )
        if len(secondary) != len(set(secondary)):
            raise _error(
                'field "knowledge_layers.secondary" must not contain duplicates',
                path=path,
                object_id=object_id,
            )
        if primary in secondary:
            raise _error(
                'field "knowledge_layers.secondary" must not repeat the primary layer',
                path=path,
                object_id=object_id,
            )
    _validate_structured_mapping_field(
        data,
        field_name="canonical_story",
        string_fields=CANONICAL_STORY_STRING_FIELDS,
        list_fields=CANONICAL_STORY_LIST_FIELDS,
        path=path,
        object_id=object_id,
    )
    _validate_structured_mapping_field(
        data,
        field_name="hermeneutical_lens",
        string_fields=HERMENEUTICAL_LENS_STRING_FIELDS,
        list_fields=HERMENEUTICAL_LENS_LIST_FIELDS,
        path=path,
        object_id=object_id,
    )
    _validate_structured_mapping_field(
        data,
        field_name="retrieval_metadata",
        list_fields=RETRIEVAL_METADATA_LIST_FIELDS,
        path=path,
        object_id=object_id,
    )
    for field_name in OPTIONAL_FIELDS:
        if field_name not in data:
            continue
        value = data[field_name]
        if value is not None and not isinstance(value, str):
            raise _expected_actual_error(
                field_name,
                "null or str",
                value,
                path=path,
                object_id=object_id,
            )
    if "importance" in data and (isinstance(data["importance"], bool) or not isinstance(data["importance"], int)):
        raise _expected_actual_error(
            "importance",
            "int",
            data["importance"],
            path=path,
            object_id=object_id,
        )


def validate_related_object_entry(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
    allow_self_reference: bool = False,
) -> CanonicalRelationship:
    if isinstance(data, CanonicalRelationship):
        return data
    if not isinstance(data, Mapping):
        raise _expected_actual_error(
            "related_objects",
            "list[dict]",
            data,
            path=path,
            object_id=object_id,
        )

    unknown_fields = sorted(set(data) - set(RELATED_OBJECT_REQUIRED_FIELDS))
    if unknown_fields:
        raise _error(
            f'unknown relationship field(s): {", ".join(unknown_fields)}',
            path=path,
            object_id=object_id,
        )

    for field_name in RELATED_OBJECT_REQUIRED_FIELDS:
        if field_name not in data:
            raise _error(f'field "{field_name}" is required', path=path, object_id=object_id)

    relationship_id = data["id"]
    if not isinstance(relationship_id, str) or not relationship_id.strip():
        raise _error(
            'field "id" is required and must be a non-empty string',
            path=path,
            object_id=object_id,
        )
    if relationship_id != relationship_id.lower() or normalize_id(relationship_id) != relationship_id:
        raise _error(
            'field "id" must use lowercase kebab-case',
            path=path,
            object_id=object_id,
        )

    relationship_name = data["relationship"]
    if not isinstance(relationship_name, str) or not relationship_name.strip():
        raise _error(
            'field "relationship" is required and must be a non-empty string',
            path=path,
            object_id=object_id,
        )
    if relationship_name != relationship_name.lower() or not RELATED_OBJECT_RELATIONSHIP_PATTERN.fullmatch(
        relationship_name
    ):
        raise _error(
            'field "relationship" must use lowercase kebab-case',
            path=path,
            object_id=object_id,
        )

    weight = data["weight"]
    if isinstance(weight, bool) or not isinstance(weight, int):
        raise _error(
            'field "weight" must be an integer between 1 and 10',
            path=path,
            object_id=object_id,
        )
    if weight < 1 or weight > 10:
        raise _error(
            'field "weight" must be an integer between 1 and 10',
            path=path,
            object_id=object_id,
        )

    notes = data["notes"]
    if not isinstance(notes, str):
        raise _expected_actual_error(
            "notes",
            "str",
            notes,
            path=path,
            object_id=object_id,
        )

    if not allow_self_reference and object_id is not None and relationship_id == object_id:
        raise _error(
            f'field "related_objects" cannot reference the object itself ({relationship_id})',
            path=path,
            object_id=object_id,
        )

    return CanonicalRelationship(
        id=relationship_id,
        relationship=relationship_name,
        weight=weight,
        notes=notes,
    )


def validate_related_objects_field(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
    allow_self_reference: bool = False,
) -> list[CanonicalRelationship]:
    if "related_objects" not in data:
        return []
    related_objects = data["related_objects"]
    if related_objects is None:
        raise _expected_actual_error(
            "related_objects",
            "list[dict]",
            related_objects,
            path=path,
            object_id=object_id,
        )
    if not isinstance(related_objects, list):
        raise _expected_actual_error(
            "related_objects",
            "list[dict]",
            related_objects,
            path=path,
            object_id=object_id,
        )

    normalized_related_objects: list[CanonicalRelationship] = []
    seen_relationships: set[tuple[str, str]] = set()
    for item in related_objects:
        relationship = validate_related_object_entry(
            item,
            path=path,
            object_id=object_id,
            allow_self_reference=allow_self_reference,
        )
        key = (relationship.id, relationship.relationship)
        if key in seen_relationships:
            raise _error(
                f'field "related_objects" contains a duplicate relationship to "{relationship.id}" '
                f'with type "{relationship.relationship}"',
                path=path,
                object_id=object_id,
            )
        seen_relationships.add(key)
        normalized_related_objects.append(relationship)

    return normalized_related_objects


def validate_scripture_reference_entry(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> CanonicalScriptureReference:
    if isinstance(data, CanonicalScriptureReference):
        return data
    if not isinstance(data, Mapping):
        raise _expected_actual_error(
            "scripture_references",
            "list[dict]",
            data,
            path=path,
            object_id=object_id,
        )

    unknown_fields = sorted(set(data) - set(SCRIPTURE_REFERENCE_REQUIRED_FIELDS))
    if unknown_fields:
        raise _error(
            f'unknown scripture reference field(s): {", ".join(unknown_fields)}',
            path=path,
            object_id=object_id,
        )

    for field_name in SCRIPTURE_REFERENCE_REQUIRED_FIELDS:
        if field_name not in data:
            raise _error(f'field "{field_name}" is required', path=path, object_id=object_id)

    reference = data["reference"]
    if not isinstance(reference, str) or not reference.strip():
        raise _error(
            'field "reference" is required and must be a non-empty string',
            path=path,
            object_id=object_id,
        )

    relationship = data["relationship"]
    if not isinstance(relationship, str) or not relationship.strip():
        raise _error(
            'field "relationship" is required and must be a non-empty string',
            path=path,
            object_id=object_id,
        )
    if relationship not in SCRIPTURE_REFERENCE_RELATIONSHIP_VALUES:
        raise _error(
            f'field "relationship" must be one of {", ".join(SCRIPTURE_REFERENCE_RELATIONSHIP_VALUES)}',
            path=path,
            object_id=object_id,
        )

    notes = data["notes"]
    if not isinstance(notes, str):
        raise _expected_actual_error(
            "notes",
            "str",
            notes,
            path=path,
            object_id=object_id,
        )

    return CanonicalScriptureReference(
        reference=reference.strip(),
        relationship=relationship,
        notes=notes,
    )


def validate_scripture_references_field(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> list[CanonicalScriptureReference]:
    if "scripture_references" not in data:
        return []
    scripture_references = data["scripture_references"]
    if scripture_references is None:
        raise _expected_actual_error(
            "scripture_references",
            "list[dict]",
            scripture_references,
            path=path,
            object_id=object_id,
        )
    if not isinstance(scripture_references, list):
        raise _expected_actual_error(
            "scripture_references",
            "list[dict]",
            scripture_references,
            path=path,
            object_id=object_id,
        )

    normalized_scripture_references: list[CanonicalScriptureReference] = []
    for item in scripture_references:
        normalized_scripture_references.append(
            validate_scripture_reference_entry(item, path=path, object_id=object_id)
        )

    return normalized_scripture_references


def validate_source_entry(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> CanonicalSource:
    if isinstance(data, CanonicalSource):
        return data
    if not isinstance(data, Mapping):
        raise _expected_actual_error(
            "sources",
            "list[str] or list[dict]",
            data,
            path=path,
            object_id=object_id,
        )

    required_fields = (
        "title",
        "author",
        "publisher",
        "year",
        "locator",
        "url",
        "source_type",
        "notes",
    )
    optional_fields = ("id", "supports")
    unknown_fields = sorted(set(data) - set(required_fields) - set(optional_fields))
    if unknown_fields:
        raise _error(
            f'unknown source field(s): {", ".join(unknown_fields)}',
            path=path,
            object_id=object_id,
        )

    for field_name in required_fields:
        if field_name not in data:
            raise _error(f'field "{field_name}" is required', path=path, object_id=object_id)

    title = data["title"]
    if not isinstance(title, str) or not title.strip():
        raise _error(
            'field "title" is required and must be a non-empty string',
            path=path,
            object_id=object_id,
        )

    for field_name in ("author", "publisher", "locator", "url", "notes"):
        value = data[field_name]
        if not isinstance(value, str):
            raise _expected_actual_error(field_name, "str", value, path=path, object_id=object_id)

    year = data["year"]
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        raise _expected_actual_error("year", "null or int", year, path=path, object_id=object_id)

    source_type = data["source_type"]
    if not isinstance(source_type, str) or not source_type.strip():
        raise _error(
            'field "source_type" is required and must be a non-empty string',
            path=path,
            object_id=object_id,
        )
    normalized_source_type = _normalize_source_type_label(source_type)
    if normalized_source_type not in SOURCE_TYPE_VALUES:
        raise _error(
            f'field "source_type" must be one of {", ".join(SOURCE_TYPE_VALUES)}',
            path=path,
            object_id=object_id,
        )

    source_id = data.get("id")
    if source_id is None or (isinstance(source_id, str) and not source_id.strip()):
        source_id = normalize_id(title)
    if not isinstance(source_id, str):
        raise _expected_actual_error("id", "str", source_id, path=path, object_id=object_id)
    normalized_source_id = normalize_id(source_id)
    if not normalized_source_id:
        raise _error(
            'field "id" is required and must resolve to a non-empty canonical id',
            path=path,
            object_id=object_id,
        )

    supports = _normalize_source_supports(data.get("supports"), path=path, object_id=object_id)

    return CanonicalSource(
        id=normalized_source_id,
        title=title.strip(),
        author=data["author"],
        publisher=data["publisher"],
        year=year,
        locator=data["locator"],
        url=data["url"],
        source_type=normalized_source_type,
        supports=supports,
        notes=data["notes"],
    )


def normalize_sources_field(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> list[CanonicalSource]:
    if "sources" not in data:
        return []
    sources = data["sources"]
    if sources is None:
        raise _expected_actual_error(
            "sources",
            "list[str] or list[dict]",
            sources,
            path=path,
            object_id=object_id,
        )
    if not isinstance(sources, list):
        raise _expected_actual_error(
            "sources",
            "list[str] or list[dict]",
            sources,
            path=path,
            object_id=object_id,
        )

    normalized_sources: list[CanonicalSource] = []
    for item in sources:
        if isinstance(item, str):
            normalized_sources.append(CanonicalSource.from_legacy_string(item))
            continue
        normalized_sources.append(validate_source_entry(item, path=path, object_id=object_id))

    return normalized_sources


def _normalize_interpretive_note_label(value: Any) -> str:
    return re.sub(r"[\s_]+", "-", str(value).strip().lower())


def _normalize_taxonomy_label(value: Any, allowed: Sequence[str]) -> str:
    normalized = str(value).strip().lower()
    if normalized in allowed:
        return normalized
    underscore_candidate = re.sub(r"[\s-]+", "_", normalized)
    if underscore_candidate in allowed:
        return underscore_candidate
    hyphen_candidate = re.sub(r"[\s_]+", "-", normalized)
    return hyphen_candidate


def _normalize_nonempty_string_list(
    value: Any,
    *,
    field_name: str,
    path: str | Path | None = None,
    object_id: str | None = None,
    normalize_as_ids: bool = False,
) -> list[str]:
    if value is None or not isinstance(value, list):
        raise _expected_actual_error(
            field_name,
            "list[str]",
            value,
            path=path,
            object_id=object_id,
        )
    normalized_values: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise _error(
                f'field "{field_name}" must contain non-empty strings',
                path=path,
                object_id=object_id,
            )
        normalized_values.append(normalize_id(item) if normalize_as_ids else item.strip())
    return list(dict.fromkeys(normalized_values))


def validate_interpretive_note_entry(
    data: Any,
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> CanonicalInterpretiveNote:
    if isinstance(data, CanonicalInterpretiveNote):
        return data
    if isinstance(data, str):
        return CanonicalInterpretiveNote.from_legacy_string(data)
    if not isinstance(data, Mapping):
        raise _expected_actual_error(
            "interpretive_notes",
            "list[str] or list[dict]",
            data,
            path=path,
            object_id=object_id,
        )

    required_fields = ("note",)
    optional_fields = (
        "note_type",
        "certainty",
        "dispute_status",
        "sources",
        "scripture_references",
        "traditions",
        "rationale",
    )
    unknown_fields = sorted(set(data) - set(required_fields) - set(optional_fields))
    if unknown_fields:
        raise _error(
            f'unknown interpretive note field(s): {", ".join(unknown_fields)}',
            path=path,
            object_id=object_id,
        )

    note = data.get("note")
    if not isinstance(note, str) or not note.strip():
        raise _error(
            'field "note" is required and must be a non-empty string',
            path=path,
            object_id=object_id,
        )

    note_type = _normalize_interpretive_note_label(data.get("note_type", "textual-observation"))
    if note_type not in INTERPRETIVE_NOTE_TYPE_VALUES:
        raise _error(
            f'field "note_type" must be one of {", ".join(INTERPRETIVE_NOTE_TYPE_VALUES)}',
            path=path,
            object_id=object_id,
        )

    certainty = _normalize_taxonomy_label(
        data.get("certainty", "unknown"),
        INTERPRETIVE_NOTE_CERTAINTY_VALUES,
    )
    if certainty not in INTERPRETIVE_NOTE_CERTAINTY_VALUES:
        raise _error(
            f'field "certainty" must be one of {", ".join(INTERPRETIVE_NOTE_CERTAINTY_VALUES)}',
            path=path,
            object_id=object_id,
        )

    dispute_status = _normalize_taxonomy_label(
        data.get("dispute_status", "unknown"),
        INTERPRETIVE_NOTE_DISPUTE_STATUS_VALUES,
    )
    if dispute_status not in INTERPRETIVE_NOTE_DISPUTE_STATUS_VALUES:
        raise _error(
            f'field "dispute_status" must be one of {", ".join(INTERPRETIVE_NOTE_DISPUTE_STATUS_VALUES)}',
            path=path,
            object_id=object_id,
        )

    sources = _normalize_nonempty_string_list(
        data.get("sources", []),
        field_name="sources",
        path=path,
        object_id=object_id,
        normalize_as_ids=True,
    )
    scripture_references = _normalize_nonempty_string_list(
        data.get("scripture_references", []),
        field_name="scripture_references",
        path=path,
        object_id=object_id,
    )
    traditions = _normalize_nonempty_string_list(
        data.get("traditions", []),
        field_name="traditions",
        path=path,
        object_id=object_id,
    )
    rationale = data.get("rationale", "")
    if not isinstance(rationale, str):
        raise _expected_actual_error(
            "rationale",
            "str",
            rationale,
            path=path,
            object_id=object_id,
        )
    return CanonicalInterpretiveNote(
        note=note.strip(),
        note_type=note_type,
        certainty=certainty,
        dispute_status=dispute_status,
        sources=sources,
        scripture_references=scripture_references,
        traditions=traditions,
        rationale=rationale.strip(),
    )


def normalize_interpretive_notes_field(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> list[CanonicalInterpretiveNote]:
    if "interpretive_notes" not in data:
        return []
    interpretive_notes = data["interpretive_notes"]
    if interpretive_notes is None:
        raise _expected_actual_error(
            "interpretive_notes",
            "list[str] or list[dict]",
            interpretive_notes,
            path=path,
            object_id=object_id,
        )
    if not isinstance(interpretive_notes, list):
        raise _expected_actual_error(
            "interpretive_notes",
            "list[str] or list[dict]",
            interpretive_notes,
            path=path,
            object_id=object_id,
        )

    normalized_notes: list[CanonicalInterpretiveNote] = []
    for item in interpretive_notes:
        normalized_notes.append(
            validate_interpretive_note_entry(item, path=path, object_id=object_id)
        )
    return normalized_notes


def validate_claim_entry(
    data: Any,
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> CanonicalClaim:
    if isinstance(data, CanonicalClaim):
        return data
    if not isinstance(data, Mapping):
        raise _expected_actual_error(
            "claims",
            "list[dict]",
            data,
            path=path,
            object_id=object_id,
        )

    required_fields = (
        "id",
        "claim",
        "claim_type",
        "certainty",
        "dispute_status",
    )
    optional_fields = (
        "scripture_references",
        "source_ids",
        "traditions",
        "rationale",
        "notes",
    )
    unknown_fields = sorted(set(data) - set(required_fields) - set(optional_fields))
    if unknown_fields:
        raise _error(
            f'unknown claim field(s): {", ".join(unknown_fields)}',
            path=path,
            object_id=object_id,
        )

    missing_fields = [field_name for field_name in required_fields if field_name not in data]
    if missing_fields:
        raise _error(
            f'claim is missing required field(s): {", ".join(missing_fields)}',
            path=path,
            object_id=object_id,
        )

    claim_id = data.get("id")
    if (
        not isinstance(claim_id, str)
        or not claim_id.strip()
        or normalize_id(claim_id) != claim_id
    ):
        raise _error(
            'field "claims.id" must use lowercase kebab-case',
            path=path,
            object_id=object_id,
        )
    claim_text = data.get("claim")
    if not isinstance(claim_text, str) or not claim_text.strip():
        raise _error(
            'field "claims.claim" must be a non-empty string',
            path=path,
            object_id=object_id,
        )

    claim_type = _normalize_taxonomy_label(data.get("claim_type"), CLAIM_TYPE_VALUES)
    if claim_type not in CLAIM_TYPE_VALUES:
        raise _error(
            f'field "claims.claim_type" must be one of {", ".join(CLAIM_TYPE_VALUES)}',
            path=path,
            object_id=object_id,
        )
    certainty = _normalize_taxonomy_label(data.get("certainty"), CURRENT_CERTAINTY_VALUES)
    if certainty not in CURRENT_CERTAINTY_VALUES:
        raise _error(
            f'field "claims.certainty" must be one of {", ".join(CURRENT_CERTAINTY_VALUES)}',
            path=path,
            object_id=object_id,
        )
    dispute_status = _normalize_taxonomy_label(
        data.get("dispute_status"),
        CURRENT_DISPUTE_STATUS_VALUES,
    )
    if dispute_status not in CURRENT_DISPUTE_STATUS_VALUES:
        raise _error(
            'field "claims.dispute_status" must be one of '
            + ", ".join(CURRENT_DISPUTE_STATUS_VALUES),
            path=path,
            object_id=object_id,
        )

    scripture_references = _normalize_nonempty_string_list(
        data.get("scripture_references", []),
        field_name="claims.scripture_references",
        path=path,
        object_id=object_id,
    )
    source_ids = _normalize_nonempty_string_list(
        data.get("source_ids", []),
        field_name="claims.source_ids",
        path=path,
        object_id=object_id,
        normalize_as_ids=True,
    )
    traditions = _normalize_nonempty_string_list(
        data.get("traditions", []),
        field_name="claims.traditions",
        path=path,
        object_id=object_id,
    )
    rationale = data.get("rationale", "")
    notes = data.get("notes", "")
    for field_name, value in (("claims.rationale", rationale), ("claims.notes", notes)):
        if not isinstance(value, str):
            raise _expected_actual_error(
                field_name,
                "str",
                value,
                path=path,
                object_id=object_id,
            )

    return CanonicalClaim(
        id=claim_id,
        claim=claim_text.strip(),
        claim_type=claim_type,
        certainty=certainty,
        dispute_status=dispute_status,
        scripture_references=scripture_references,
        source_ids=source_ids,
        traditions=traditions,
        rationale=rationale.strip(),
        notes=notes.strip(),
    )


def validate_claims_field(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    object_id: str | None = None,
) -> list[CanonicalClaim]:
    claims = data.get("claims", [])
    if not isinstance(claims, list):
        raise _expected_actual_error(
            "claims",
            "list[dict]",
            claims,
            path=path,
            object_id=object_id,
        )

    normalized_claims: list[CanonicalClaim] = []
    seen_ids: set[str] = set()
    for item in claims:
        claim = validate_claim_entry(item, path=path, object_id=object_id)
        if claim.id in seen_ids:
            raise _error(
                f'field "claims" contains duplicate claim id "{claim.id}"',
                path=path,
                object_id=object_id,
            )
        seen_ids.add(claim.id)
        normalized_claims.append(claim)
    return normalized_claims


def validate_claim_source_references(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> None:
    object_id = data.get("id") if isinstance(data.get("id"), str) else None
    source_ids = {
        source.id
        for source in normalize_sources_field(data, path=path, object_id=object_id)
    }
    for claim in validate_claims_field(data, path=path, object_id=object_id):
        missing_sources = sorted(set(claim.source_ids) - source_ids)
        if missing_sources:
            raise _error(
                f'claim "{claim.id}" references missing source IDs: '
                + ", ".join(missing_sources),
                path=path,
                object_id=object_id,
            )


def interpretive_note_texts(value: Any) -> list[str]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if isinstance(value, Mapping):
        note = str(value.get("note") or "").strip()
        return [note] if note else []
    if isinstance(value, (list, tuple)):
        texts: list[str] = []
        for item in value:
            texts.extend(interpretive_note_texts(item))
        return texts
    text = str(value).strip()
    return [text] if text else []


def section_completion_issues(data: Mapping[str, Any] | CanonicalObject) -> list[str]:
    """Return required sections that are not complete for this object type."""

    mapping = data.to_dict() if isinstance(data, CanonicalObject) else dict(data)
    section_status = mapping.get("section_status")
    if not isinstance(section_status, Mapping):
        return list(required_sections_for_type(str(mapping.get("type") or "")))
    return [
        section_name
        for section_name in required_sections_for_type(str(mapping.get("type") or ""))
        if section_status.get(section_name) not in {"complete", "not_applicable"}
    ]


def content_completeness_issues(
    data: Mapping[str, Any] | CanonicalObject,
    *,
    known_object_ids: set[str] | None = None,
) -> list[str]:
    """Return deterministic reasons an object is not globally complete."""

    mapping = data.to_dict() if isinstance(data, CanonicalObject) else dict(data)
    issues = [
        f'section_status.{section_name} is not complete'
        for section_name in section_completion_issues(mapping)
    ]
    if mapping.get("content_status") != "complete":
        issues.append("content_status is not complete")
    if mapping.get("review_status") not in {"reviewed", "approved"}:
        issues.append("human review has not occurred")
    if mapping.get("human_review_required") is not False:
        issues.append("human_review_required is not false")
    if not mapping.get("reviewed_by"):
        issues.append("reviewed_by is empty")

    source_ids = {
        str(source.get("id") if isinstance(source, Mapping) else getattr(source, "id", "") or "")
        for source in mapping.get("sources", [])
    }
    for note in normalize_interpretive_notes_field(mapping):
        if (
            note.certainty not in CURRENT_CERTAINTY_VALUES
            or note.dispute_status not in CURRENT_DISPUTE_STATUS_VALUES
        ):
            issues.append("interpretive note uses legacy or unknown certainty metadata")
        missing_note_sources = sorted(set(note.sources) - source_ids)
        if missing_note_sources:
            issues.append(
                "interpretive note references missing source IDs: "
                + ", ".join(missing_note_sources)
            )
    for claim in validate_claims_field(mapping):
        if not claim.scripture_references and not claim.source_ids:
            issues.append(f'claim "{claim.id}" has no supporting evidence')
        missing_claim_sources = sorted(set(claim.source_ids) - source_ids)
        if missing_claim_sources:
            issues.append(
                f'claim "{claim.id}" references missing source IDs: '
                + ", ".join(missing_claim_sources)
            )

    if known_object_ids is not None:
        for relationship in mapping.get("related_objects", []):
            target_id = (
                relationship.get("id")
                if isinstance(relationship, Mapping)
                else getattr(relationship, "id", None)
            )
            if target_id and target_id not in known_object_ids:
                issues.append(f'relationship target "{target_id}" does not resolve')
    return list(dict.fromkeys(issues))


def is_globally_complete(
    data: Mapping[str, Any] | CanonicalObject,
    *,
    known_object_ids: set[str] | None = None,
) -> bool:
    return not content_completeness_issues(data, known_object_ids=known_object_ids)


def validate_approved_content_requirements(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> None:
    normalized = _normalize_governance_metadata(data)
    object_id = normalized.get("id") if isinstance(normalized.get("id"), str) else None
    if normalized.get("review_status") != "approved":
        return

    summary = normalized.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise _error(
            'field "summary" is required when review_status is "approved"',
            path=path,
            object_id=object_id,
        )

    scripture_references = normalized.get("scripture_references")
    if not isinstance(scripture_references, list) or not scripture_references:
        raise _error(
            'field "scripture_references" must contain at least one reference when review_status is "approved"',
            path=path,
            object_id=object_id,
        )

    sources = normalized.get("sources")
    if not isinstance(sources, list) or not sources:
        raise _error(
            'field "sources" must contain at least one source when review_status is "approved"',
            path=path,
            object_id=object_id,
        )
    normalized_sources = normalize_sources_field(normalized, path=path, object_id=object_id)
    if not any(
        source.source_type in SUBSTANTIVE_SOURCE_TYPE_VALUES for source in normalized_sources
    ):
        raise _error(
            'field "sources" must include at least one substantive source when review_status is "approved"',
            path=path,
            object_id=object_id,
        )

    confidence = normalized.get("confidence")
    if confidence == "unrated":
        raise _error(
            'field "confidence" must not be "unrated" when review_status is "approved"',
            path=path,
            object_id=object_id,
        )

    if normalized.get("human_review_required") is True:
        raise _error(
            'field "human_review_required" must be false when review_status is "approved"',
            path=path,
            object_id=object_id,
        )

    incomplete_sections = section_completion_issues(normalized)
    if incomplete_sections:
        raise _error(
            'approved content requires complete or not_applicable section status for: '
            + ", ".join(incomplete_sections),
            path=path,
            object_id=object_id,
        )

    source_ids = {source.id for source in normalized_sources}
    for note in normalize_interpretive_notes_field(
        normalized,
        path=path,
        object_id=object_id,
    ):
        if (
            note.certainty not in CURRENT_CERTAINTY_VALUES
            or note.dispute_status not in CURRENT_DISPUTE_STATUS_VALUES
        ):
            raise _error(
                "approved interpretive notes must use current certainty and dispute taxonomies",
                path=path,
                object_id=object_id,
            )
        if not note.rationale:
            raise _error(
                "approved interpretive notes must include a certainty rationale",
                path=path,
                object_id=object_id,
            )
        missing_sources = sorted(set(note.sources) - source_ids)
        if missing_sources:
            raise _error(
                "interpretive note references missing source IDs: "
                + ", ".join(missing_sources),
                path=path,
                object_id=object_id,
            )

    for claim in validate_claims_field(normalized, path=path, object_id=object_id):
        if not claim.rationale:
            raise _error(
                f'approved claim "{claim.id}" must include a certainty rationale',
                path=path,
                object_id=object_id,
            )
        if not claim.scripture_references and not claim.source_ids:
            raise _error(
                f'approved claim "{claim.id}" must include supporting evidence',
                path=path,
                object_id=object_id,
            )
        missing_sources = sorted(set(claim.source_ids) - source_ids)
        if missing_sources:
            raise _error(
                f'claim "{claim.id}" references missing source IDs: '
                + ", ".join(missing_sources),
                path=path,
                object_id=object_id,
            )


def validate_governance_metadata(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> None:
    normalized = _normalize_governance_metadata(data)
    object_id = normalized.get("id") if isinstance(normalized.get("id"), str) else None

    for field_name, allowed_values in (
        ("content_status", CONTENT_STATUS_VALUES),
        ("review_status", REVIEW_STATUS_VALUES),
        ("confidence", CONFIDENCE_VALUES),
    ):
        value = normalized.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise _error(
                f'field "{field_name}" is required and must be a non-empty string',
                path=path,
                object_id=object_id,
            )
        if value not in allowed_values:
            raise _error(
                f'field "{field_name}" must be one of {", ".join(allowed_values)}',
                path=path,
                object_id=object_id,
            )

    content_status = normalized.get("content_status")
    review_status = normalized.get("review_status")

    generated_by = normalized.get("generated_by")
    if not isinstance(generated_by, list):
        raise _expected_actual_error(
            "generated_by",
            "list[dict]",
            generated_by,
            path=path,
            object_id=object_id,
        )
    for item in generated_by:
        validate_provenance_entry(item, path=path, object_id=object_id)

    edited_by = normalized.get("edited_by")
    if not isinstance(edited_by, list):
        raise _expected_actual_error(
            "edited_by",
            "list[str]",
            edited_by,
            path=path,
            object_id=object_id,
        )
    if any(not isinstance(item, str) for item in edited_by):
        raise _error(
            'field "edited_by" must be a list of strings',
            path=path,
            object_id=object_id,
        )

    reviewed_by = normalized.get("reviewed_by")
    if not isinstance(reviewed_by, list):
        raise _expected_actual_error(
            "reviewed_by",
            "list[str]",
            reviewed_by,
            path=path,
            object_id=object_id,
        )
    if any(not isinstance(item, str) for item in reviewed_by):
        raise _error(
            'field "reviewed_by" must be a list of strings',
            path=path,
            object_id=object_id,
        )

    human_review_required = normalized.get("human_review_required")
    if not isinstance(human_review_required, bool):
        raise _expected_actual_error(
            "human_review_required",
            "bool",
            human_review_required,
            path=path,
            object_id=object_id,
        )

    last_reviewed = normalized.get("last_reviewed")
    if last_reviewed is not None:
        if not isinstance(last_reviewed, str):
            raise _expected_actual_error(
                "last_reviewed",
                "null or YYYY-MM-DD string",
                last_reviewed,
                path=path,
                object_id=object_id,
            )
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", last_reviewed):
            raise _error(
                'field "last_reviewed" must use YYYY-MM-DD format',
                path=path,
                object_id=object_id,
            )
        try:
            date.fromisoformat(last_reviewed)
        except ValueError as exc:
            raise _error(
                'field "last_reviewed" must be a valid YYYY-MM-DD date',
                path=path,
                object_id=object_id,
            ) from exc

    if review_status in {"reviewed", "approved", "rejected"}:
        if not reviewed_by:
            raise _error(
                'field "reviewed_by" must contain at least one reviewer when review_status is "reviewed", "approved", or "rejected"',
                path=path,
                object_id=object_id,
            )
        if last_reviewed is None:
            raise _error(
                'field "last_reviewed" is required when review_status is "reviewed", "approved", or "rejected"',
                path=path,
                object_id=object_id,
            )

    if review_status == "approved" and content_status != "complete":
        raise _error(
            'field "content_status" must be "complete" when review_status is "approved"',
            path=path,
            object_id=object_id,
        )

    if review_status in {"reviewed", "approved", "rejected"} and human_review_required:
        raise _error(
            'field "human_review_required" must be false when review_status is "reviewed", "approved", or "rejected"',
            path=path,
            object_id=object_id,
        )

    if review_status in {"unreviewed", "in_review"} and not human_review_required:
        raise _error(
            'field "human_review_required" must be true when review_status is "unreviewed" or "in_review"',
            path=path,
            object_id=object_id,
        )


def validate_category_type(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> None:
    object_id = data.get("id") if isinstance(data.get("id"), str) else None
    object_type = data.get("type")
    if object_type not in SUPPORTED_CATEGORIES:
        raise _error(
            f'field "type" must be one of {", ".join(SUPPORTED_CATEGORIES)}',
            path=path,
            object_id=object_id,
        )
    if path is not None:
        path_obj = Path(path)
        parts = path_obj.parts
        if "objects" in parts:
            objects_index = parts.index("objects")
            if len(parts) > objects_index + 1:
                folder = parts[objects_index + 1]
                expected = _category_folder(str(object_type))
                if expected is not None and folder != expected:
                    raise _error(
                        f'file is stored under "{folder}" but field "type" is "{object_type}"',
                        path=path,
                        object_id=object_id,
                    )


def validate_aliases(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> None:
    object_id = data.get("id") if isinstance(data.get("id"), str) else None
    aliases = data.get("aliases")
    if not isinstance(aliases, list):
        raise _expected_actual_error("aliases", "list[str]", aliases, path=path, object_id=object_id)
    if not aliases:
        raise _error('field "aliases" must contain at least one alias', path=path, object_id=object_id)
    seen: set[str] = set()
    for alias in aliases:
        if not isinstance(alias, str):
            raise _expected_actual_error("aliases", "list[str]", aliases, path=path, object_id=object_id)
        normalized = normalize_alias(alias)
        if not normalized:
            raise _error('field "aliases" cannot contain blank values', path=path, object_id=object_id)
        if normalized in seen:
            raise _error(
                f'field "aliases" contains a duplicate normalized alias "{normalized}"',
                path=path,
                object_id=object_id,
            )
        seen.add(normalized)


def validate_unique_normalized_list_field(
    data: Mapping[str, Any],
    *,
    field_name: str,
    path: str | Path | None = None,
) -> None:
    object_id = data.get("id") if isinstance(data.get("id"), str) else None
    values = data.get(field_name)
    if not isinstance(values, list):
        raise _expected_actual_error(
            field_name,
            "list[str]",
            values,
            path=path,
            object_id=object_id,
        )

    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise _expected_actual_error(
                field_name,
                "list[str]",
                values,
                path=path,
                object_id=object_id,
            )
        normalized = normalize_id(value)
        if not normalized:
            raise _error(
                f'field "{field_name}" cannot contain blank values',
                path=path,
                object_id=object_id,
            )
        if normalized in seen:
            raise _error(
                f'field "{field_name}" contains a duplicate normalized theme id "{normalized}"',
                path=path,
                object_id=object_id,
            )
        seen.add(normalized)


def validate_object(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> CanonicalObject:
    if not isinstance(data, Mapping):
        raise _error(
            f"expected mapping, received {_type_name(data)}",
            path=path,
        )
    unknown_fields = sorted(set(data) - set(ALL_FIELDS))
    object_id = data.get("id") if isinstance(data.get("id"), str) else None
    if unknown_fields:
        raise _error(
            f"unknown field(s): {', '.join(unknown_fields)}",
            path=path,
            object_id=object_id,
        )
    normalized_data = _apply_governance_defaults(data)
    validate_required_fields(normalized_data, path=path)
    validate_field_types(normalized_data, path=path)
    validate_claim_source_references(normalized_data, path=path)
    validate_category_type(normalized_data, path=path)
    validate_aliases(normalized_data, path=path)
    for field_name in UNIQUE_NORMALIZED_LIST_FIELDS:
        validate_unique_normalized_list_field(normalized_data, field_name=field_name, path=path)
    validate_governance_metadata(normalized_data, path=path)
    validate_approved_content_requirements(normalized_data, path=path)

    missing_fields = [field_name for field_name in ALL_FIELDS if field_name not in normalized_data]
    if missing_fields:
        raise _error(
            f'field(s) missing: {", ".join(missing_fields)}',
            path=path,
            object_id=object_id,
        )

    object_id = str(normalized_data["id"])
    if object_id != object_id.lower():
        raise _error('field "id" must be lowercase', path=path, object_id=object_id)
    if normalize_id(object_id) != object_id:
        raise _error(
            'field "id" must use lowercase kebab-case',
            path=path,
            object_id=object_id,
        )
    if path is not None and Path(path).suffix == ".json" and Path(path).stem != object_id:
        raise _error(
            f'filename "{Path(path).name}" must match canonical id "{object_id}.json"',
            path=path,
            object_id=object_id,
        )
    if normalized_data["framework_version"] != SUPPORTED_FRAMEWORK_VERSION:
        raise _error(
            f'field "framework_version" must be "{SUPPORTED_FRAMEWORK_VERSION}"',
            path=path,
            object_id=object_id,
        )
    if normalized_data["object_version"] != SUPPORTED_OBJECT_VERSION:
        raise _error(
            f'field "object_version" must be "{SUPPORTED_OBJECT_VERSION}"',
            path=path,
            object_id=object_id,
        )
    if normalized_data["importance"] < 0:
        raise _error('field "importance" must be greater than or equal to zero', path=path, object_id=object_id)
    return CanonicalObject.from_mapping(normalized_data, path=path)


def validate_library(
    objects: Mapping[str, CanonicalObject] | list[CanonicalObject],
    *,
    manifest: Mapping[str, Any] | None = None,
    source_paths: Mapping[str, str | Path] | None = None,
) -> None:
    if isinstance(objects, Mapping):
        items = list(objects.values())
    else:
        items = list(objects)

    errors: list[str] = []
    seen_ids: dict[str, CanonicalObject] = {}
    alias_lookup: dict[str, set[str]] = {}
    title_lookup: dict[str, set[str]] = {}
    id_lookup: dict[str, str] = {}
    related_objects_lookup: dict[str, list[CanonicalRelationship]] = {}

    for obj in items:
        if obj.id in seen_ids:
            errors.append(f"duplicate canonical id '{obj.id}'")
            continue
        seen_ids[obj.id] = obj
        try:
            validated_obj = validate_object(
                obj.to_dict(),
                path=source_paths.get(obj.id) if source_paths else None,
            )
            related_objects_lookup[obj.id] = validated_obj.related_objects
        except CanonicalValidationError as exc:
            errors.append(str(exc))
        title_key = normalize_alias(obj.title)
        title_lookup.setdefault(title_key, set()).add(obj.id)
        id_lookup[normalize_id(obj.id)] = obj.id
        for alias in obj.aliases:
            alias_key = normalize_alias(alias)
            alias_lookup.setdefault(alias_key, set()).add(obj.id)

    if source_paths:
        for obj in items:
            path = Path(source_paths[obj.id])
            if path.suffix != ".json" or path.stem != obj.id:
                errors.append(
                    f"filename mismatch for id '{obj.id}': expected {obj.id}.json, found {path.name}"
                )
            parts = path.parts
            if "objects" in parts:
                index = parts.index("objects")
                if len(parts) > index + 1:
                    folder = parts[index + 1]
                    expected_folder = _category_folder(obj.type)
                    if expected_folder and folder != expected_folder:
                        errors.append(
                            f"file { _path_text(path) } stored in '{folder}' but object type is '{obj.type}'"
                        )

    for alias, ids in alias_lookup.items():
        if len(ids) > 1:
            errors.append(f'alias collision for "{alias}": {", ".join(sorted(ids))}')
            continue
        alias_id = next(iter(ids))
        if alias in id_lookup and id_lookup[alias] != alias_id:
            errors.append(
                f'normalized alias "{alias}" collides with canonical id "{id_lookup[alias]}"'
            )
        if alias in title_lookup and title_lookup[alias] != ids:
            errors.append(
                f'normalized alias "{alias}" collides with title for ids: {", ".join(sorted(title_lookup[alias]))}'
            )

    for obj in items:
        relationships = related_objects_lookup.get(obj.id, [])
        path = source_paths.get(obj.id) if source_paths else None
        for relationship in relationships:
            if relationship.id not in seen_ids:
                errors.append(
                    str(
                        _error(
                            f'field "related_objects" references unknown canonical id "{relationship.id}"',
                            path=path,
                            object_id=obj.id,
                        )
                    )
                )

    counts = {category: 0 for category in SUPPORTED_CATEGORIES}
    for obj in items:
        counts[obj.type] = counts.get(obj.type, 0) + 1

    if manifest is not None:
        manifest_framework_version = manifest.get("framework_version")
        if manifest_framework_version != SUPPORTED_FRAMEWORK_VERSION:
            errors.append(
                f'manifest framework_version {manifest_framework_version!r} is unsupported; expected {SUPPORTED_FRAMEWORK_VERSION!r}'
            )
        manifest_schema_version = manifest.get("schema_version")
        if manifest_schema_version != SUPPORTED_SCHEMA_VERSION:
            errors.append(
                f'manifest schema_version {manifest_schema_version!r} is unsupported; expected {SUPPORTED_SCHEMA_VERSION!r}'
            )
        manifest_object_count = manifest.get("object_count")
        if manifest_object_count != len(items):
            errors.append(
                f'manifest object_count {manifest_object_count!r} does not match loaded object count {len(items)}'
            )
        manifest_categories = manifest.get("categories")
        if not isinstance(manifest_categories, Mapping):
            errors.append('manifest field "categories" must be a mapping')
        else:
            for category in SUPPORTED_CATEGORIES:
                expected = counts.get(category, 0)
                manifest_key = CATEGORY_FOLDERS[category]
                actual = manifest_categories.get(manifest_key)
                if actual is None and category in manifest_categories:
                    actual = manifest_categories.get(category)
                if actual != expected:
                    errors.append(
                        f'manifest category count mismatch for "{manifest_key}": expected {expected}, found {actual!r}'
                    )
            extra_categories = sorted(set(manifest_categories) - (set(SUPPORTED_CATEGORIES) | set(MANIFEST_CATEGORY_KEYS)))
            if extra_categories:
                errors.append(
                    f'manifest contains unsupported categories: {", ".join(extra_categories)}'
                )

    if errors:
        raise CanonicalValidationError("\n".join(errors))
