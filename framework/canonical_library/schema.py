"""Canonical object schema and validation utilities."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Mapping

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
    "biblical-text",
    "book",
    "journal",
    "commentary",
    "dictionary",
    "encyclopedia",
    "archaeological-report",
    "museum",
    "primary-source",
    "website",
    "other",
)

DEFAULT_GOVERNANCE_METADATA: dict[str, Any] = {
    "content_status": "placeholder",
    "review_status": "unreviewed",
    "reviewed_by": [],
    "last_reviewed": None,
    "confidence": "unrated",
}

DEFAULT_CANONICAL_METADATA: dict[str, Any] = {
    **DEFAULT_GOVERNANCE_METADATA,
    "authorship_positions": [],
    "date_ranges": [],
    "original_audience": "",
    "historical_setting": "",
    "genre": [],
    "structure": [],
    "major_themes": [],
    "canonical_placement": "",
    "key_people": [],
    "key_places": [],
    "key_events": [],
    "interpretive_disputes": [],
    "primary_sources": [],
    "related_objects": [],
    "scripture_references": [],
    "sources": [],
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
    "ancient_near_east_context",
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
)

RELATED_OBJECT_FIELDS: tuple[str, ...] = ("related_objects",)

SCRIPTURE_REFERENCE_FIELDS: tuple[str, ...] = ("scripture_references",)

SOURCE_FIELDS: tuple[str, ...] = ("sources",)

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

OPTIONAL_FIELDS: tuple[str, ...] = ("last_reviewed",)

GOVERNANCE_LIST_FIELDS: tuple[str, ...] = ("reviewed_by",)

ALL_FIELDS: tuple[str, ...] = (
    STRING_FIELDS
    + LIST_FIELDS
    + RELATED_OBJECT_FIELDS
    + SCRIPTURE_REFERENCE_FIELDS
    + SOURCE_FIELDS
    + INT_FIELDS
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
    notes: str = ""

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
        return cls(title=normalized)


@dataclass(frozen=True)
class CanonicalObject:
    id: str
    type: str
    title: str
    aliases: list[str] = field(default_factory=list)
    summary: str = ""
    historical_context: str = ""
    ancient_near_east_context: str = ""
    literary_context: str = ""
    covenantal_significance: str = ""
    authorship_positions: list[str] = field(default_factory=list)
    date_ranges: list[str] = field(default_factory=list)
    original_audience: str = ""
    historical_setting: str = ""
    genre: list[str] = field(default_factory=list)
    structure: list[str] = field(default_factory=list)
    major_themes: list[str] = field(default_factory=list)
    canonical_placement: str = ""
    key_people: list[str] = field(default_factory=list)
    key_places: list[str] = field(default_factory=list)
    key_events: list[str] = field(default_factory=list)
    interpretive_disputes: list[str] = field(default_factory=list)
    primary_sources: list[str] = field(default_factory=list)
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
    interpretive_notes: list[str] = field(default_factory=list)
    common_questions: list[str] = field(default_factory=list)
    sources: list[CanonicalSource] = field(default_factory=list)
    importance: int = 0
    framework_version: str = SUPPORTED_FRAMEWORK_VERSION
    object_version: str = SUPPORTED_OBJECT_VERSION
    content_status: str = DEFAULT_GOVERNANCE_METADATA["content_status"]
    review_status: str = DEFAULT_GOVERNANCE_METADATA["review_status"]
    reviewed_by: list[str] = field(default_factory=list)
    last_reviewed: str | None = DEFAULT_GOVERNANCE_METADATA["last_reviewed"]
    confidence: str = DEFAULT_GOVERNANCE_METADATA["confidence"]

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
            else:
                values[field_name] = normalized[field_name]
        return cls(**values)


def _apply_governance_defaults(data: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    for field_name, default_value in DEFAULT_CANONICAL_METADATA.items():
        if field_name not in normalized:
            normalized[field_name] = list(default_value) if isinstance(default_value, list) else default_value
    return normalized


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
    for field_name in LIST_FIELDS:
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
            raise _expected_actual_error(
                field_name,
                "list[str]",
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
    unknown_fields = sorted(set(data) - set(required_fields))
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
    if source_type not in SOURCE_TYPE_VALUES:
        raise _error(
            f'field "source_type" must be one of {", ".join(SOURCE_TYPE_VALUES)}',
            path=path,
            object_id=object_id,
        )

    return CanonicalSource(
        title=title.strip(),
        author=data["author"],
        publisher=data["publisher"],
        year=year,
        locator=data["locator"],
        url=data["url"],
        source_type=source_type,
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


def validate_approved_content_requirements(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> None:
    object_id = data.get("id") if isinstance(data.get("id"), str) else None
    if data.get("review_status") != "approved":
        return

    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise _error(
            'field "summary" is required when review_status is "approved"',
            path=path,
            object_id=object_id,
        )

    scripture_references = data.get("scripture_references")
    if not isinstance(scripture_references, list) or not scripture_references:
        raise _error(
            'field "scripture_references" must contain at least one reference when review_status is "approved"',
            path=path,
            object_id=object_id,
        )

    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise _error(
            'field "sources" must contain at least one source when review_status is "approved"',
            path=path,
            object_id=object_id,
        )
    if any(isinstance(source, str) for source in sources):
        raise _error(
            'field "sources" must use structured source objects when review_status is "approved"',
            path=path,
            object_id=object_id,
        )
    if not any(
        isinstance(source, Mapping)
        and isinstance(source.get("source_type"), str)
        and source["source_type"] not in {"website", "other"}
        for source in sources
    ):
        raise _error(
            'field "sources" must include at least one substantive source when review_status is "approved"',
            path=path,
            object_id=object_id,
        )

    confidence = data.get("confidence")
    if confidence == "unrated":
        raise _error(
            'field "confidence" must not be "unrated" when review_status is "approved"',
            path=path,
            object_id=object_id,
        )


def validate_governance_metadata(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> None:
    object_id = data.get("id") if isinstance(data.get("id"), str) else None

    for field_name, allowed_values in (
        ("content_status", CONTENT_STATUS_VALUES),
        ("review_status", REVIEW_STATUS_VALUES),
        ("confidence", CONFIDENCE_VALUES),
    ):
        value = data.get(field_name)
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

    content_status = data.get("content_status")
    review_status = data.get("review_status")

    reviewed_by = data.get("reviewed_by")
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

    last_reviewed = data.get("last_reviewed")
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

    if review_status != "unreviewed":
        if not reviewed_by:
            raise _error(
                'field "reviewed_by" must contain at least one reviewer when review_status is not "unreviewed"',
                path=path,
                object_id=object_id,
            )
        if last_reviewed is None:
            raise _error(
                'field "last_reviewed" is required when review_status is not "unreviewed"',
                path=path,
                object_id=object_id,
            )

    if review_status == "approved" and content_status != "complete":
        raise _error(
            'field "content_status" must be "complete" when review_status is "approved"',
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
    validate_category_type(normalized_data, path=path)
    validate_aliases(normalized_data, path=path)
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
