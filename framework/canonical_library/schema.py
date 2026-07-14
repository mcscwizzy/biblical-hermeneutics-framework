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

DEFAULT_GOVERNANCE_METADATA: dict[str, Any] = {
    "content_status": "placeholder",
    "review_status": "unreviewed",
    "reviewed_by": [],
    "last_reviewed": None,
    "confidence": "unrated",
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
    "framework_version",
    "object_version",
    "content_status",
    "review_status",
    "confidence",
)

LIST_FIELDS: tuple[str, ...] = (
    "aliases",
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
    "sources",
)

INT_FIELDS: tuple[str, ...] = ("importance",)

OPTIONAL_FIELDS: tuple[str, ...] = ("last_reviewed",)

GOVERNANCE_LIST_FIELDS: tuple[str, ...] = ("reviewed_by",)

ALL_FIELDS: tuple[str, ...] = STRING_FIELDS + LIST_FIELDS + INT_FIELDS + OPTIONAL_FIELDS + GOVERNANCE_LIST_FIELDS


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
    intertextuality: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    maps: list[str] = field(default_factory=list)
    archaeology: list[str] = field(default_factory=list)
    hebrew_words: list[str] = field(default_factory=list)
    greek_words: list[str] = field(default_factory=list)
    related_people: list[str] = field(default_factory=list)
    related_places: list[str] = field(default_factory=list)
    related_events: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    new_testament_connections: list[str] = field(default_factory=list)
    interpretive_notes: list[str] = field(default_factory=list)
    common_questions: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
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
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "CanonicalObject":
        values: dict[str, Any] = {}
        normalized = _apply_governance_defaults(mapping)
        for field_name in ALL_FIELDS:
            values[field_name] = normalized[field_name]
        return cls(**values)


def _apply_governance_defaults(data: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    for field_name, default_value in DEFAULT_GOVERNANCE_METADATA.items():
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
    if last_reviewed is None:
        return
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
    return CanonicalObject.from_mapping(normalized_data)


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

    for obj in items:
        if obj.id in seen_ids:
            errors.append(f"duplicate canonical id '{obj.id}'")
            continue
        seen_ids[obj.id] = obj
        try:
            validate_governance_metadata(
                obj.to_dict(),
                path=source_paths.get(obj.id) if source_paths else None,
            )
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
