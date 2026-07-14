"""Authoring, validation, reporting, and migration helpers for CKL."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from bhf_agent.bible import BibleError, parse_reference_query, resolve_chapter, resolve_passage

from .normalization import normalize_alias, normalize_id, normalize_text
from .schema import (
    CATEGORY_FOLDERS,
    MANIFEST_CATEGORY_KEYS,
    SUPPORTED_CATEGORIES,
    SUPPORTED_FRAMEWORK_VERSION,
    SUPPORTED_OBJECT_VERSION,
    SUPPORTED_SCHEMA_VERSION,
    CanonicalObject,
    CanonicalValidationError,
    validate_library,
    validate_object,
)


DEFAULT_AUTHORING_ROOT = Path(__file__).resolve().parent
DEFAULT_OBJECTS_ROOT = DEFAULT_AUTHORING_ROOT / "objects"
DEFAULT_MANIFEST_PATH = DEFAULT_AUTHORING_ROOT / "manifest.json"

COMPLETE_REQUIRED_FIELDS: tuple[str, ...] = (
    "summary",
    "historical_context",
    "literary_context",
    "scripture_references",
    "related_objects",
    "sources",
    "common_questions",
    "interpretive_notes",
)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str | None = None
    object_id: str | None = None
    severity: str = "error"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LibraryAudit:
    root: Path
    object_paths: list[Path] = field(default_factory=list)
    valid_objects: dict[str, CanonicalObject] = field(default_factory=dict)
    validation_issues: list[ValidationIssue] = field(default_factory=list)
    duplicate_id_issues: list[ValidationIssue] = field(default_factory=list)
    alias_collision_issues: list[ValidationIssue] = field(default_factory=list)
    unresolved_relationship_issues: list[ValidationIssue] = field(default_factory=list)
    broken_scripture_reference_issues: list[ValidationIssue] = field(default_factory=list)
    missing_content_issues: list[ValidationIssue] = field(default_factory=list)
    manifest_issues: list[ValidationIssue] = field(default_factory=list)
    content_status_counts: Counter[str] = field(default_factory=Counter)
    review_status_counts: Counter[str] = field(default_factory=Counter)
    category_counts: Counter[str] = field(default_factory=Counter)
    raw_id_occurrences: dict[str, list[str]] = field(default_factory=dict)
    generated_manifest: dict[str, Any] | None = None

    @property
    def issue_count(self) -> int:
        return sum(
            len(bucket)
            for bucket in (
                self.validation_issues,
                self.duplicate_id_issues,
                self.alias_collision_issues,
                self.unresolved_relationship_issues,
                self.broken_scripture_reference_issues,
                self.missing_content_issues,
                self.manifest_issues,
            )
        )

    @property
    def has_errors(self) -> bool:
        return self.issue_count > 0

    @property
    def raw_object_count(self) -> int:
        return len(self.object_paths)

    @property
    def valid_object_count(self) -> int:
        return len(self.valid_objects)

    def issues(self) -> list[ValidationIssue]:
        return [
            *self.validation_issues,
            *self.duplicate_id_issues,
            *self.alias_collision_issues,
            *self.unresolved_relationship_issues,
            *self.broken_scripture_reference_issues,
            *self.missing_content_issues,
            *self.manifest_issues,
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "object_paths": [str(path) for path in self.object_paths],
            "raw_object_count": self.raw_object_count,
            "valid_object_count": self.valid_object_count,
            "issue_count": self.issue_count,
            "content_status_counts": dict(self.content_status_counts),
            "review_status_counts": dict(self.review_status_counts),
            "category_counts": dict(self.category_counts),
            "raw_id_occurrences": self.raw_id_occurrences,
            "generated_manifest": self.generated_manifest,
            "issues": [issue.to_dict() for issue in self.issues()],
        }

    def summary_lines(self) -> list[str]:
        lines = [
            f"CKL audit for {self.root}",
            f"- Files scanned: {self.raw_object_count}",
            f"- Valid objects: {self.valid_object_count}",
            f"- Issues found: {self.issue_count}",
        ]
        if self.content_status_counts:
            lines.append("- Content statuses: " + _format_counter(self.content_status_counts))
        if self.review_status_counts:
            lines.append("- Review statuses: " + _format_counter(self.review_status_counts))
        if self.category_counts:
            lines.append("- Categories: " + _format_counter(self.category_counts))
        return lines


def canonical_object_template(
    object_type: str,
    object_id: str,
    *,
    title: str | None = None,
    aliases: Sequence[str] | None = None,
) -> CanonicalObject:
    normalized_type = str(object_type).strip().lower().replace("-", "_").replace(" ", "_")
    if normalized_type not in SUPPORTED_CATEGORIES:
        raise ValueError(
            f"unknown CKL type '{object_type}'. Expected one of: {', '.join(SUPPORTED_CATEGORIES)}"
        )

    normalized_id = normalize_id(object_id)
    if not normalized_id:
        raise ValueError("object_id must not be blank")

    display_title = str(title or _title_from_id(normalized_id)).strip()
    alias_list = _normalize_aliases(
        aliases or _default_aliases(normalized_type, display_title, normalized_id)
    )
    if not alias_list:
        alias_list = _default_aliases(normalized_type, display_title, normalized_id)

    return CanonicalObject(
        id=normalized_id,
        type=normalized_type,
        title=display_title,
        aliases=alias_list,
    )


def build_manifest(
    objects: Iterable[CanonicalObject],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    items = list(objects)
    counts = Counter(obj.type for obj in items)
    return {
        "framework_version": SUPPORTED_FRAMEWORK_VERSION,
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "generated_at": generated_at,
        "object_count": len(items),
        "categories": {
            manifest_key: counts.get(category, 0)
            for category, manifest_key in CATEGORY_FOLDERS.items()
        },
    }


def dump_json_text(data: Mapping[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"


def read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_json_text(data), encoding="utf-8")


def iter_object_paths(root: Path) -> list[Path]:
    objects_root = _objects_root(root)
    if not objects_root.exists():
        return []
    return sorted(
        path
        for path in objects_root.rglob("*.json")
        if path.is_file()
        and path.name != "manifest.json"
        and not path.name.startswith("_")
    )


def resolve_authoring_root(path: Path | str | None = None) -> Path:
    candidate = Path(path) if path is not None else DEFAULT_AUTHORING_ROOT
    candidate = candidate.resolve()
    if candidate.name == "objects" and candidate.parent.exists():
        return candidate.parent
    if (candidate / "objects").exists():
        return candidate
    nested = candidate / "framework" / "canonical_library"
    if (nested / "objects").exists():
        return nested
    if candidate.name == "canonical_library" and (candidate / "objects").exists():
        return candidate
    raise FileNotFoundError(
        f"could not locate the CKL root at {candidate}; expected an objects/ directory"
    )


def validate_object_payload(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> tuple[CanonicalObject | None, list[ValidationIssue]]:
    try:
        obj = validate_object(data, path=path)
    except CanonicalValidationError as exc:
        return None, _issues_from_validation_error(exc, path=path)
    return obj, []


def scan_library(root: Path | str, *, include_manifest: bool = True) -> LibraryAudit:
    ckl_root = resolve_authoring_root(root)
    audit = LibraryAudit(root=ckl_root)
    object_paths = iter_object_paths(ckl_root)
    audit.object_paths = object_paths

    source_paths: dict[str, str] = {}
    raw_id_occurrences: dict[str, list[str]] = defaultdict(list)

    for path in object_paths:
        relative = _relative_path(ckl_root, path)
        try:
            raw = read_json_file(path)
        except Exception as exc:  # noqa: BLE001 - surface parser failures
            audit.validation_issues.append(
                ValidationIssue(
                    code="parse_error",
                    message=str(exc),
                    path=relative,
                    severity="error",
                )
            )
            continue

        if not isinstance(raw, Mapping):
            audit.validation_issues.append(
                ValidationIssue(
                    code="parse_error",
                    message="CKL object must be a JSON object",
                    path=relative,
                    severity="error",
                )
            )
            continue

        raw_id = raw.get("id")
        if isinstance(raw_id, str) and raw_id.strip():
            raw_id_occurrences[normalize_id(raw_id)].append(relative)

        obj, issues = validate_object_payload(raw, path=relative)
        _route_issues(audit, issues)
        if obj is None:
            continue

        source_paths[obj.id] = relative
        audit.valid_objects[obj.id] = obj
        audit.content_status_counts[obj.content_status] += 1
        audit.review_status_counts[obj.review_status] += 1
        audit.category_counts[obj.type] += 1

        audit.missing_content_issues.extend(_complete_content_issues(obj, relative))
        audit.broken_scripture_reference_issues.extend(
            _scripture_reference_issues(obj, relative)
        )

    for normalized_id, paths in raw_id_occurrences.items():
        if len(paths) > 1:
            audit.duplicate_id_issues.append(
                ValidationIssue(
                    code="duplicate_id",
                    message=(
                        f"duplicate canonical id '{normalized_id}' found in "
                        + ", ".join(paths)
                    ),
                    severity="error",
                    details={"paths": paths},
                )
            )

    audit.raw_id_occurrences = {key: list(paths) for key, paths in raw_id_occurrences.items()}

    unique_objects = list(audit.valid_objects.values())
    unique_source_paths = {
        obj.id: source_paths[obj.id]
        for obj in unique_objects
        if obj.id in source_paths
    }
    audit.content_status_counts = Counter(obj.content_status for obj in unique_objects)
    audit.review_status_counts = Counter(obj.review_status for obj in unique_objects)
    audit.category_counts = Counter(obj.type for obj in unique_objects)

    audit.generated_manifest = build_manifest(unique_objects)
    try:
        validate_library(unique_objects, source_paths=unique_source_paths)
    except CanonicalValidationError as exc:
        _route_issues(audit, _issues_from_validation_error(exc))

    if include_manifest:
        try:
            manifest = _read_manifest(ckl_root)
        except Exception as exc:  # noqa: BLE001 - surface manifest parser failures
            audit.manifest_issues.append(
                ValidationIssue(
                    code="manifest_parse",
                    message=f"{_relative_path(ckl_root, ckl_root / 'manifest.json')}: {exc}",
                    severity="error",
                )
            )
        else:
            if manifest is None:
                audit.manifest_issues.append(
                    ValidationIssue(
                        code="missing_manifest",
                        message=(
                            f"{_relative_path(ckl_root, ckl_root / 'manifest.json')}: "
                            "manifest is missing"
                        ),
                        severity="error",
                    )
                )
            elif audit.generated_manifest is not None:
                audit.manifest_issues.extend(
                    _compare_manifest(manifest, audit.generated_manifest, root=ckl_root)
                )

    return audit


def validate_single_object(path: Path | str) -> LibraryAudit:
    file_path = Path(path).resolve()
    ckl_root = _guess_root_for_file(file_path)
    audit = LibraryAudit(root=ckl_root, object_paths=[file_path])

    try:
        raw = read_json_file(file_path)
    except Exception as exc:  # noqa: BLE001 - surface parser failures
        audit.validation_issues.append(
            ValidationIssue(
                code="parse_error",
                message=str(exc),
                path=_relative_path(ckl_root, file_path),
                severity="error",
            )
        )
        return audit

    if not isinstance(raw, Mapping):
        audit.validation_issues.append(
            ValidationIssue(
                code="parse_error",
                message="CKL object must be a JSON object",
                path=_relative_path(ckl_root, file_path),
                severity="error",
            )
        )
        return audit

    obj, issues = validate_object_payload(raw, path=_relative_path(ckl_root, file_path))
    _route_issues(audit, issues)
    if obj is None:
        return audit

    audit.valid_objects[obj.id] = obj
    audit.content_status_counts[obj.content_status] += 1
    audit.review_status_counts[obj.review_status] += 1
    audit.category_counts[obj.type] += 1
    audit.missing_content_issues.extend(
        _complete_content_issues(obj, _relative_path(ckl_root, file_path))
    )
    audit.broken_scripture_reference_issues.extend(
        _scripture_reference_issues(obj, _relative_path(ckl_root, file_path))
    )
    audit.generated_manifest = build_manifest([obj])
    return audit


def normalize_object_mapping(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> tuple[dict[str, Any], bool]:
    obj = validate_object(data, path=path)
    normalized = obj.to_dict()
    changed = _normalize_jsonable(data) != _normalize_jsonable(normalized)
    return normalized, changed


def migrate_object_file(path: Path | str) -> tuple[dict[str, Any], bool]:
    file_path = Path(path).resolve()
    raw = read_json_file(file_path)
    if not isinstance(raw, Mapping):
        raise CanonicalValidationError("CKL object must be a JSON object")
    return normalize_object_mapping(raw, path=file_path)


def format_validation_summary(audit: LibraryAudit) -> str:
    lines = audit.summary_lines()
    if audit.duplicate_id_issues:
        lines.append("")
        lines.append("Duplicate IDs:")
        lines.extend(f"- {issue.message}" for issue in audit.duplicate_id_issues)
    if audit.alias_collision_issues:
        lines.append("")
        lines.append("Alias collisions:")
        lines.extend(f"- {issue.message}" for issue in audit.alias_collision_issues)
    if audit.unresolved_relationship_issues:
        lines.append("")
        lines.append("Unresolved relationships:")
        lines.extend(f"- {issue.message}" for issue in audit.unresolved_relationship_issues)
    if audit.broken_scripture_reference_issues:
        lines.append("")
        lines.append("Broken scripture references:")
        lines.extend(f"- {issue.message}" for issue in audit.broken_scripture_reference_issues)
    if audit.missing_content_issues:
        lines.append("")
        lines.append("Missing required content:")
        lines.extend(f"- {issue.message}" for issue in audit.missing_content_issues)
    if audit.validation_issues:
        lines.append("")
        lines.append("Validation errors:")
        lines.extend(f"- {issue.message}" for issue in audit.validation_issues)
    if audit.manifest_issues:
        lines.append("")
        lines.append("Manifest issues:")
        lines.extend(f"- {issue.message}" for issue in audit.manifest_issues)
    return "\n".join(lines).strip()


def _complete_content_issues(
    obj: CanonicalObject,
    path: str,
) -> list[ValidationIssue]:
    if obj.content_status != "complete":
        return []
    issues: list[ValidationIssue] = []
    for field_name in COMPLETE_REQUIRED_FIELDS:
        value = getattr(obj, field_name, None)
        if _is_empty_field_value(value):
            issues.append(
                ValidationIssue(
                    code="missing_required_content",
                    message=(
                        f'field "{field_name}" must be populated when content_status is "complete"'
                    ),
                    path=path,
                    object_id=obj.id,
                    details={"field": field_name},
                )
            )
    return issues


def _scripture_reference_issues(
    obj: CanonicalObject,
    path: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for reference in obj.scripture_references:
        reference_text = str(reference.reference).strip()
        if not reference_text:
            issues.append(
                ValidationIssue(
                    code="broken_scripture_reference",
                    message='field "reference" must not be blank',
                    path=path,
                    object_id=obj.id,
                )
            )
            continue
        parsed = parse_reference_query(reference_text)
        if parsed is None:
            issues.append(
                ValidationIssue(
                    code="broken_scripture_reference",
                    message=f'unsupported scripture reference "{reference_text}"',
                    path=path,
                    object_id=obj.id,
                )
            )
            continue
        try:
            if "verse_start" in parsed:
                resolve_passage(
                    parsed["book"],
                    parsed["chapter"],
                    parsed.get("verse_start"),
                    parsed.get("verse_end"),
                )
            else:
                resolve_chapter(parsed["book"], parsed["chapter"])
        except BibleError as exc:
            issues.append(
                ValidationIssue(
                    code="broken_scripture_reference",
                    message=str(exc),
                    path=path,
                    object_id=obj.id,
                )
            )
    return issues


def _compare_manifest(
    manifest: Mapping[str, Any],
    generated_manifest: Mapping[str, Any],
    *,
    root: Path,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if manifest.get("framework_version") != SUPPORTED_FRAMEWORK_VERSION:
        issues.append(
            ValidationIssue(
                code="manifest_version",
                message=(
                    f'manifest framework_version {manifest.get("framework_version")!r} '
                    f"is unsupported; expected {SUPPORTED_FRAMEWORK_VERSION!r}"
                ),
                severity="error",
            )
        )
    if manifest.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        issues.append(
            ValidationIssue(
                code="manifest_version",
                message=(
                    f'manifest schema_version {manifest.get("schema_version")!r} '
                    f"is unsupported; expected {SUPPORTED_SCHEMA_VERSION!r}"
                ),
                severity="error",
            )
        )
    if manifest.get("object_count") != generated_manifest.get("object_count"):
        issues.append(
            ValidationIssue(
                code="manifest_count",
                message=(
                    f'manifest object_count {manifest.get("object_count")!r} does not match '
                    f'generated object count {generated_manifest.get("object_count")!r}'
                ),
                severity="error",
            )
        )

    manifest_categories = manifest.get("categories")
    if not isinstance(manifest_categories, Mapping):
        issues.append(
            ValidationIssue(
                code="manifest_structure",
                message='manifest field "categories" must be a mapping',
                severity="error",
            )
        )
        return issues

    generated_categories = generated_manifest.get("categories", {})
    for category in SUPPORTED_CATEGORIES:
        manifest_key = CATEGORY_FOLDERS[category]
        expected = generated_categories.get(manifest_key, 0)
        actual = manifest_categories.get(manifest_key)
        if actual is None and category in manifest_categories:
            actual = manifest_categories.get(category)
        if actual != expected:
            issues.append(
                ValidationIssue(
                    code="manifest_count",
                    message=(
                        f'manifest category count mismatch for "{manifest_key}": '
                        f"expected {expected}, found {actual!r}"
                    ),
                    severity="error",
                )
            )

    extra_categories = sorted(
        set(manifest_categories) - (set(SUPPORTED_CATEGORIES) | set(MANIFEST_CATEGORY_KEYS))
    )
    if extra_categories:
        issues.append(
            ValidationIssue(
                code="manifest_structure",
                message="manifest contains unsupported categories: " + ", ".join(extra_categories),
                severity="error",
            )
        )
    return issues


def _read_manifest(root: Path) -> dict[str, Any] | None:
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return None
    raw = read_json_file(manifest_path)
    if not isinstance(raw, dict):
        raise CanonicalValidationError("manifest must be a JSON object")
    return raw


def _guess_root_for_file(path: Path) -> Path:
    for candidate in path.parents:
        if (candidate / "objects").exists():
            return candidate
    raise FileNotFoundError(
        f"could not locate a CKL root for {path}; expected an ancestor with objects/"
    )


def _objects_root(root: Path) -> Path:
    if root.name == "objects":
        return root
    if (root / "objects").exists():
        return root / "objects"
    return root


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_aliases(aliases: Sequence[str]) -> list[str]:
    cleaned = [normalize_alias(alias) for alias in aliases if normalize_alias(alias)]
    return list(dict.fromkeys(cleaned))


def _default_aliases(object_type: str, title: str, object_id: str) -> list[str]:
    phrase = normalize_text(title) or normalize_text(object_id)
    defaults = {
        "book": [
            f"book of {phrase}",
            f"what is {phrase} about",
            f"tell me about {phrase}",
        ],
        "person": [
            f"who is {phrase}",
            f"tell me about {phrase}",
            f"why is {phrase} important",
        ],
        "place": [
            f"where is {phrase}",
            f"tell me about {phrase}",
            f"why is {phrase} important",
        ],
        "event": [
            f"what happened in {phrase}",
            f"tell me about {phrase}",
            f"why is {phrase} important",
        ],
        "theology": [
            f"what is {phrase}",
            f"tell me about {phrase}",
            f"why is {phrase} important",
        ],
        "theme": [
            f"what is {phrase}",
            f"tell me about {phrase}",
            f"why is {phrase} important",
        ],
        "word_study": [
            f"what does {phrase} mean",
            f"tell me about {phrase}",
            f"why is {phrase} important",
        ],
        "archaeology": [
            f"what is {phrase}",
            f"tell me about {phrase}",
            f"why is {phrase} important",
        ],
        "institution": [
            f"what is {phrase}",
            f"tell me about {phrase}",
            f"why is {phrase} important",
        ],
        "prophecy": [
            f"what is {phrase}",
            f"tell me about {phrase}",
            f"why is {phrase} important",
        ],
        "faq": [
            f"what is {phrase}",
            f"tell me about {phrase}",
            f"why is {phrase} important",
        ],
    }
    return _normalize_aliases(defaults.get(object_type, defaults["theme"]))


def _title_from_id(object_id: str) -> str:
    return " ".join(part.capitalize() for part in object_id.replace("-", " ").split())


def _normalize_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_jsonable(item) for item in value]
    return value


def _is_empty_field_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _format_counter(counter: Counter[str]) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counter.items()))


def _issues_from_validation_error(
    exc: CanonicalValidationError,
    *,
    path: str | Path | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for line in str(exc).splitlines():
        message = line.strip()
        if not message:
            continue
        issues.append(
            ValidationIssue(
                code=_classify_validation_message(message),
                message=message,
                path=str(path) if path is not None else None,
                object_id=_extract_object_id(message),
                severity="error",
            )
        )
    return issues


def _route_issues(audit: LibraryAudit, issues: Sequence[ValidationIssue]) -> None:
    for issue in issues:
        if issue.code == "duplicate_id":
            audit.duplicate_id_issues.append(issue)
        elif issue.code in {"duplicate_alias", "alias_title_collision"}:
            audit.alias_collision_issues.append(issue)
        elif issue.code == "unresolved_relationship":
            audit.unresolved_relationship_issues.append(issue)
        elif issue.code == "missing_required_content":
            audit.missing_content_issues.append(issue)
        elif issue.code == "broken_scripture_reference":
            audit.broken_scripture_reference_issues.append(issue)
        elif issue.code == "manifest":
            audit.manifest_issues.append(issue)
        else:
            audit.validation_issues.append(issue)


def _classify_validation_message(message: str) -> str:
    lowered = message.lower()
    if "duplicate canonical id" in lowered:
        return "duplicate_id"
    if "alias collision" in lowered:
        return "duplicate_alias"
    if "normalized alias" in lowered and "collides with title" in lowered:
        return "alias_title_collision"
    if "references unknown canonical id" in lowered:
        return "unresolved_relationship"
    if "must be populated when content_status is \"complete\"" in lowered:
        return "missing_required_content"
    if "scripture_references" in lowered and "approved" in lowered:
        return "missing_required_content"
    if "sources" in lowered and "approved" in lowered:
        return "missing_required_content"
    if "confidence" in lowered and "approved" in lowered:
        return "missing_required_content"
    if "manifest" in lowered:
        return "manifest"
    return "validation_error"


def _extract_object_id(message: str) -> str | None:
    id_match = re.search(r"\[id=([^\]]+)\]", message)
    if id_match:
        return id_match.group(1)
    duplicate_match = re.search(r"duplicate canonical id '([^']+)'", message)
    if duplicate_match:
        return duplicate_match.group(1)
    return None
