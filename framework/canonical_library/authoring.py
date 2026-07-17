"""Authoring, validation, reporting, and migration helpers for CKL."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, replace
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
    normalize_sources_field,
    validate_library,
    validate_object,
)


DEFAULT_AUTHORING_ROOT = Path(__file__).resolve().parent
DEFAULT_OBJECTS_ROOT = DEFAULT_AUTHORING_ROOT / "objects"
DEFAULT_MANIFEST_PATH = DEFAULT_AUTHORING_ROOT / "manifest.json"

COMPLETE_REQUIRED_FIELDS: tuple[str, ...] = (
    "summary",
    "canonical_role",
    "historical_context",
    "literary_context",
    "scripture_references",
    "related_objects",
    "sources",
    "common_questions",
    "interpretive_notes",
)

MATURE_REVIEW_STATUSES: tuple[str, ...] = ("reviewed", "approved", "rejected")

SEMANTIC_CONTEXT_FIELDS: tuple[str, ...] = (
    "historical_context",
    "ancient_near_east_context",
    "hebraic_worldview",
    "second_temple_context",
    "canonical_context",
    "later_christian_reception",
)

SEMANTIC_TEXT_FIELDS: tuple[str, ...] = (
    "summary",
    "historical_context",
    "ancient_near_east_context",
    "hebraic_worldview",
    "second_temple_context",
    "canonical_context",
    "later_christian_reception",
    "literary_context",
    "covenantal_significance",
)

HISTORICAL_SOURCE_TYPES: tuple[str, ...] = (
    "academic-book",
    "journal-article",
    "reference-work",
    "ancient-primary-source",
    "excavation-report",
    "museum-collection",
)

LEXICAL_SOURCE_TYPES: tuple[str, ...] = (
    "lexicon",
    "grammar",
    "reference-work",
    "academic-book",
    "journal-article",
)

ARCHAEOLOGICAL_SOURCE_TYPES: tuple[str, ...] = (
    "excavation-report",
    "museum-collection",
    "ancient-primary-source",
    "academic-book",
    "journal-article",
    "reference-work",
)

GENERIC_REPEATED_PROSE_MIN_OCCURRENCES = 3

LEGACY_AI_REVIEWER_PREFIXES: tuple[str, ...] = ("codex",)

_BROAD_GENERALIZATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bhebrew thought always\b", re.IGNORECASE),
    re.compile(r"\bthe jews believed\b", re.IGNORECASE),
    re.compile(r"\ball jews\b", re.IGNORECASE),
    re.compile(r"\balways\b", re.IGNORECASE),
)

_SIMPLISTIC_WORLDVIEW_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bhebrew\s+thought\b", re.IGNORECASE),
    re.compile(r"\bgreek\s+thought\b", re.IGNORECASE),
    re.compile(r"\bhebrew\s+versus\s+greek\b", re.IGNORECASE),
    re.compile(r"\bgreek\s+versus\s+hebrew\b", re.IGNORECASE),
    re.compile(r"\bconcrete\b", re.IGNORECASE),
    re.compile(r"\babstract\b", re.IGNORECASE),
)

_ANE_GENERIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bancient near eastern\b", re.IGNORECASE),
    re.compile(r"\bancient near east\b", re.IGNORECASE),
    re.compile(r"\bane\b", re.IGNORECASE),
)

_ANE_SPECIFIC_ANCHORS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bassyrian\b", re.IGNORECASE),
    re.compile(r"\bbabylonian\b", re.IGNORECASE),
    re.compile(r"\bcanaanite\b", re.IGNORECASE),
    re.compile(r"\begyptian\b", re.IGNORECASE),
    re.compile(r"\bhittite\b", re.IGNORECASE),
    re.compile(r"\bmesopotamian\b", re.IGNORECASE),
    re.compile(r"\bugaritic\b", re.IGNORECASE),
    re.compile(r"\bakkadian\b", re.IGNORECASE),
    re.compile(r"\bsumerian\b", re.IGNORECASE),
    re.compile(r"\bpersian\b", re.IGNORECASE),
    re.compile(r"\broman\b", re.IGNORECASE),
    re.compile(r"\blevantine\b", re.IGNORECASE),
    re.compile(r"\bsecond temple\b", re.IGNORECASE),
    re.compile(r"\btemple\b", re.IGNORECASE),
    re.compile(r"\btreaty\b", re.IGNORECASE),
    re.compile(r"\bhousehold\b", re.IGNORECASE),
    re.compile(r"\bpatronage\b", re.IGNORECASE),
    re.compile(r"\bscribal\b", re.IGNORECASE),
    re.compile(r"\bcultic\b", re.IGNORECASE),
    re.compile(r"\bimperial\b", re.IGNORECASE),
    re.compile(r"\bvassal\b", re.IGNORECASE),
)

_CONFESSIONAL_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bconfessional\b", re.IGNORECASE),
    re.compile(r"\bthe church has always\b", re.IGNORECASE),
    re.compile(r"\bchristians have long\b", re.IGNORECASE),
    re.compile(r"\breformed\b", re.IGNORECASE),
    re.compile(r"\bcatholic\b", re.IGNORECASE),
    re.compile(r"\borthodox\b", re.IGNORECASE),
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
    warning_issues: list[ValidationIssue] = field(default_factory=list)
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
                self.warning_issues,
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
    def warning_count(self) -> int:
        return len(self.warning_issues)

    @property
    def error_count(self) -> int:
        return self.issue_count - self.warning_count

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0

    @property
    def has_warnings(self) -> bool:
        return self.warning_count > 0

    @property
    def raw_object_count(self) -> int:
        return len(self.object_paths)

    @property
    def valid_object_count(self) -> int:
        return len(self.valid_objects)

    def issues(self) -> list[ValidationIssue]:
        return [
            *self.warning_issues,
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
            "warning_count": self.warning_count,
            "error_count": self.error_count,
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
            f"- Warnings: {self.warning_count}",
            f"- Errors: {self.error_count}",
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
        obj = validate_object(
            _normalize_legacy_sources(
                data,
                path=path,
                promote_approved_legacy_sources=True,
            ),
            path=path,
        )
    except CanonicalValidationError as exc:
        return None, _issues_from_validation_error(exc, path=path)
    return obj, []


def _semantic_issue_severity(obj: CanonicalObject) -> str:
    review_status = str(getattr(obj, "review_status", "") or "").strip().lower()
    return "error" if review_status in MATURE_REVIEW_STATUSES else "warning"


def _is_legacy_ai_reviewer(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    return bool(normalized) and any(normalized.startswith(prefix) for prefix in LEGACY_AI_REVIEWER_PREFIXES)


def _normalized_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return normalize_text(value)


def _is_mature_context_record(obj: CanonicalObject) -> bool:
    review_status = str(getattr(obj, "review_status", "") or "").strip().lower()
    return review_status in MATURE_REVIEW_STATUSES


def _source_types_for(obj: CanonicalObject) -> set[str]:
    source_types: set[str] = set()
    for source in getattr(obj, "sources", []) or []:
        source_type = str(getattr(source, "source_type", "") or "").strip().lower()
        if source_type:
            source_types.add(source_type)
    return source_types


def _has_any_source_type(obj: CanonicalObject, allowed_types: Sequence[str]) -> bool:
    source_types = _source_types_for(obj)
    return any(source_type in source_types for source_type in allowed_types)


def _object_text_fields(obj: CanonicalObject) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for field_name in SEMANTIC_TEXT_FIELDS:
        value = getattr(obj, field_name, "")
        if not isinstance(value, str):
            continue
        text = value.strip()
        if text:
            values.append((field_name, text))
    return values


def _interpretive_note_texts(obj: CanonicalObject) -> list[tuple[str, str, str, str]]:
    texts: list[tuple[str, str, str, str]] = []
    for index, note in enumerate(getattr(obj, "interpretive_notes", []) or []):
        note_text = str(getattr(note, "note", "") or "").strip()
        if not note_text:
            continue
        note_type = str(getattr(note, "note_type", "") or "").strip().lower()
        certainty = str(getattr(note, "certainty", "") or "").strip().lower()
        dispute_status = str(getattr(note, "dispute_status", "") or "").strip().lower()
        texts.append((f"interpretive_notes[{index}]", note_text, note_type, dispute_status))
    return texts


def _matches_any_pattern(text: str, patterns: Sequence[re.Pattern[str]]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _is_broad_generalization(text: str) -> bool:
    lowered = text.lower()
    if "hebrew thought always" in lowered or "the jews believed" in lowered:
        return True
    if "jews believed" in lowered and any(marker in lowered for marker in ("always", "never", "all", "every")):
        return True
    if "hebrew" in lowered and "jew" in lowered and any(marker in lowered for marker in ("always", "never", "all", "every")):
        return True
    return _matches_any_pattern(text, _BROAD_GENERALIZATION_PATTERNS[:1])


def _is_simplistic_worldview_claim(text: str) -> bool:
    lowered = text.lower()
    if "hebrew thought always" in lowered or "the jews believed" in lowered:
        return True
    if "hebrew" in lowered and "greek" in lowered and any(
        marker in lowered for marker in ("concrete", "abstract", "opposite", "opposites", "versus", "vs")
    ):
        return True
    return _matches_any_pattern(text, _SIMPLISTIC_WORLDVIEW_PATTERNS[:2])


def _is_generic_ane_comparison(text: str) -> bool:
    lowered = text.lower()
    if not any(pattern.search(lowered) for pattern in _ANE_GENERIC_PATTERNS):
        return False
    return not any(pattern.search(lowered) for pattern in _ANE_SPECIFIC_ANCHORS)


def _is_confessional_consensus_claim(text: str, note_type: str, dispute_status: str) -> bool:
    if note_type not in {"theological-interpretation", "later-reception"}:
        return False
    if dispute_status not in {"consensus", "broad-consensus", "majority"}:
        return False
    return _matches_any_pattern(text, _CONFESSIONAL_MARKERS)


def _shorten_text(text: str, *, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _collect_semantic_issues(
    raw: Mapping[str, Any],
    obj: CanonicalObject,
    *,
    path: str | None = None,
    include_legacy_ai_reviewer_issue: bool = True,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    object_id = obj.id
    severity = _semantic_issue_severity(obj)

    if include_legacy_ai_reviewer_issue:
        raw_reviewed_by = raw.get("reviewed_by")
        if isinstance(raw_reviewed_by, list):
            legacy_reviewers = [
                str(reviewer).strip()
                for reviewer in raw_reviewed_by
                if isinstance(reviewer, str) and _is_legacy_ai_reviewer(reviewer)
            ]
            if legacy_reviewers:
                issues.append(
                    ValidationIssue(
                        code="legacy_ai_reviewer",
                        message='field "reviewed_by" contains legacy AI reviewer strings',
                        path=path,
                        object_id=object_id,
                        severity=severity,
                        details={
                            "reviewers": list(dict.fromkeys(legacy_reviewers)),
                        },
                    )
                )

    if _is_mature_context_record(obj):
        applicability = getattr(obj, "context_applicability", {})
        for field_name, applicability_key in (
            ("historical_context", "historical"),
            ("ancient_near_east_context", "ancient_near_east"),
            ("hebraic_worldview", "hebraic_worldview"),
            ("second_temple_context", "second_temple"),
            ("canonical_context", "canonical"),
            ("later_christian_reception", "later_christian_reception"),
        ):
            flag = applicability.get(applicability_key)
            if not isinstance(flag, bool) or not flag:
                continue
            text = getattr(obj, field_name, "")
            if isinstance(text, str) and text.strip():
                continue
            issues.append(
                ValidationIssue(
                    code="empty_applicable_context",
                    message=f'field "{field_name}" is marked applicable but is empty',
                    path=path,
                    object_id=object_id,
                    severity=severity,
                    details={"field": field_name, "applicability_key": applicability_key},
                )
            )

    if getattr(obj, "historical_context", "").strip():
        if not _has_any_source_type(obj, HISTORICAL_SOURCE_TYPES):
            issues.append(
                ValidationIssue(
                    code="historical_source_support",
                    message='field "historical_context" should be supported by a historical or academic source',
                    path=path,
                    object_id=object_id,
                    severity=severity,
                    details={"allowed_source_types": list(HISTORICAL_SOURCE_TYPES)},
                )
            )

    if obj.type == "word_study" or getattr(obj, "hebrew_words", []) or getattr(obj, "greek_words", []):
        if not _has_any_source_type(obj, LEXICAL_SOURCE_TYPES):
            issues.append(
                ValidationIssue(
                    code="lexical_source_support",
                    message='word-study material should cite a lexicon, grammar, or recognized language source',
                    path=path,
                    object_id=object_id,
                    severity=severity,
                    details={"allowed_source_types": list(LEXICAL_SOURCE_TYPES)},
                )
            )

    if obj.type == "archaeology" or getattr(obj, "archaeology", []):
        if not _has_any_source_type(obj, ARCHAEOLOGICAL_SOURCE_TYPES):
            issues.append(
                ValidationIssue(
                    code="archaeological_source_support",
                    message='archaeological material should cite excavation, museum, or academic sources',
                    path=path,
                    object_id=object_id,
                    severity=severity,
                    details={"allowed_source_types": list(ARCHAEOLOGICAL_SOURCE_TYPES)},
                )
            )

    for field_name, text in _object_text_fields(obj):
        if _is_broad_generalization(text):
            issues.append(
                ValidationIssue(
                    code="broad_generalization",
                    message=f'field "{field_name}" uses an overly broad generalization',
                    path=path,
                    object_id=object_id,
                    severity=severity,
                    details={"field": field_name, "text": text},
                )
            )
        if _is_simplistic_worldview_claim(text):
            issues.append(
                ValidationIssue(
                    code="simplistic_worldview",
                    message=f'field "{field_name}" uses a simplistic Hebrew-versus-Greek worldview contrast',
                    path=path,
                    object_id=object_id,
                    severity=severity,
                    details={"field": field_name, "text": text},
                )
            )
        if field_name == "ancient_near_east_context" and _is_generic_ane_comparison(text):
            issues.append(
                ValidationIssue(
                    code="generic_ane_comparison",
                    message=(
                        'field "ancient_near_east_context" compares the passage to the ancient Near East '
                        "without naming a specific culture, practice, source, or institution"
                    ),
                    path=path,
                    object_id=object_id,
                    severity=severity,
                    details={"field": field_name, "text": text},
                )
            )

    for note_field, note_text, note_type, dispute_status in _interpretive_note_texts(obj):
        if _is_confessional_consensus_claim(note_text, note_type, dispute_status):
            issues.append(
                ValidationIssue(
                    code="confessional_consensus",
                    message=(
                        f'{note_field} presents a confessional claim as though it were broad consensus'
                    ),
                    path=path,
                    object_id=object_id,
                    severity=severity,
                    details={
                        "field": note_field,
                        "note_type": note_type,
                        "dispute_status": dispute_status,
                        "text": note_text,
                    },
                )
            )

    return issues


def _collect_legacy_ai_reviewer_occurrences(
    raw: Mapping[str, Any],
    *,
    path: str,
) -> list[str]:
    reviewed_by = raw.get("reviewed_by")
    if not isinstance(reviewed_by, list):
        return []
    reviewers: list[str] = []
    for value in reviewed_by:
        if isinstance(value, str) and _is_legacy_ai_reviewer(value):
            normalized = value.strip()
            if normalized not in reviewers:
                reviewers.append(normalized)
    return reviewers


def _build_legacy_ai_reviewer_issues(
    occurrences: Mapping[str, list[str]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for reviewer, paths in sorted(occurrences.items()):
        if not paths:
            continue
        issues.append(
            ValidationIssue(
                code="legacy_ai_reviewer",
                message=(
                    f'field "reviewed_by" contains legacy AI reviewer string "{reviewer}" '
                    f"in {len(paths)} object(s)"
                ),
                severity="warning",
                details={
                    "reviewer": reviewer,
                    "count": len(paths),
                    "paths": list(dict.fromkeys(paths[:10])),
                },
            )
        )
    return issues


def _collect_repeated_text_occurrences(
    obj: CanonicalObject,
    *,
    path: str,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    occurrences: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for field_name, text in _object_text_fields(obj):
        normalized = _normalized_text(text)
        if not normalized:
            continue
        occurrences[(field_name, normalized)].append(
            {
                "path": path,
                "object_id": obj.id,
                "text": text,
                "review_status": str(getattr(obj, "review_status", "") or "").strip().lower(),
            }
        )
    return occurrences


def _coalesce_validation_issues(issues: Sequence[ValidationIssue]) -> list[ValidationIssue]:
    grouped: dict[tuple[str, str, str], ValidationIssue] = {}
    for issue in issues:
        key = (issue.code, issue.severity, issue.message)
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = issue
            continue

        details = dict(existing.details)
        existing_paths = details.get("paths")
        if isinstance(existing_paths, list):
            merged_paths = list(existing_paths)
        else:
            merged_paths = []
        if issue.path:
            merged_paths.append(issue.path)
        merged_paths = list(dict.fromkeys(path for path in merged_paths if path))

        existing_object_ids = details.get("object_ids")
        if isinstance(existing_object_ids, list):
            merged_object_ids = list(existing_object_ids)
        else:
            merged_object_ids = []
        if issue.object_id:
            merged_object_ids.append(issue.object_id)
        merged_object_ids = list(dict.fromkeys(object_id for object_id in merged_object_ids if object_id))

        count = int(details.get("count", 1)) + int(issue.details.get("count", 1))
        details["count"] = count
        if merged_paths:
            details["paths"] = merged_paths
        if merged_object_ids:
            details["object_ids"] = merged_object_ids
        for field_name, value in issue.details.items():
            if field_name in {"count", "paths", "object_ids"}:
                continue
            details.setdefault(field_name, value)
        grouped[key] = ValidationIssue(
            code=existing.code,
            message=existing.message,
            path=existing.path,
            object_id=existing.object_id,
            severity=existing.severity,
            details=details,
        )
    return list(grouped.values())


def _build_repeated_prose_issues(
    occurrences: Mapping[tuple[str, str], list[dict[str, Any]]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for (field_name, normalized_text), entries in sorted(occurrences.items()):
        if len(entries) < GENERIC_REPEATED_PROSE_MIN_OCCURRENCES:
            continue
        example_text = _shorten_text(str(entries[0].get("text") or ""))
        sample_paths = [str(entry["path"]) for entry in entries[:5]]
        sample_object_ids = [str(entry["object_id"]) for entry in entries[:5] if entry.get("object_id")]
        severity = "error" if any(entry.get("review_status") in MATURE_REVIEW_STATUSES for entry in entries) else "warning"
        issues.append(
            ValidationIssue(
                code="repeated_prose",
                message=(
                    f'field "{field_name}" repeats boilerplate prose across {len(entries)} object(s): '
                    f'"{example_text}"'
                ),
                severity=severity,
                details={
                    "field": field_name,
                    "count": len(entries),
                    "paths": sample_paths,
                    "object_ids": sample_object_ids,
                    "normalized_text": normalized_text,
                },
            )
        )
    return issues


def _format_issue_line(issue: ValidationIssue) -> str:
    location = issue.path
    if issue.object_id:
        object_fragment = f"[id={issue.object_id}]"
        location = f"{location} {object_fragment}" if location else object_fragment
    if location:
        return f"{location}: {issue.message}"
    if "paths" in issue.details and isinstance(issue.details["paths"], list):
        sample_paths = ", ".join(str(path) for path in issue.details["paths"][:3])
        if sample_paths:
            return f"{issue.message} (examples: {sample_paths})"
    return issue.message


def scan_library(root: Path | str, *, include_manifest: bool = True) -> LibraryAudit:
    ckl_root = resolve_authoring_root(root)
    audit = LibraryAudit(root=ckl_root)
    object_paths = iter_object_paths(ckl_root)
    audit.object_paths = object_paths

    source_paths: dict[str, str] = {}
    raw_id_occurrences: dict[str, list[str]] = defaultdict(list)
    legacy_ai_reviewer_paths: dict[str, list[str]] = defaultdict(list)
    repeated_text_occurrences: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

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

        for reviewer in _collect_legacy_ai_reviewer_occurrences(raw, path=relative):
            legacy_ai_reviewer_paths[reviewer].append(relative)
        for key, entries in _collect_repeated_text_occurrences(obj, path=relative).items():
            repeated_text_occurrences[key].extend(entries)

        _route_issues(
            audit,
            _collect_semantic_issues(
                raw,
                obj,
                path=relative,
                include_legacy_ai_reviewer_issue=False,
            ),
        )
        _route_issues(audit, _complete_content_issues(obj, relative))
        _route_issues(audit, _scripture_reference_issues(obj, relative))

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

    _route_issues(audit, _build_legacy_ai_reviewer_issues(legacy_ai_reviewer_paths))
    _route_issues(audit, _build_repeated_prose_issues(repeated_text_occurrences))
    audit.warning_issues = _coalesce_validation_issues(audit.warning_issues)

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
    _route_issues(
        audit,
        _collect_semantic_issues(raw, obj, path=_relative_path(ckl_root, file_path)),
    )
    _route_issues(audit, _complete_content_issues(obj, _relative_path(ckl_root, file_path)))
    _route_issues(
        audit,
        _scripture_reference_issues(obj, _relative_path(ckl_root, file_path)),
    )
    audit.generated_manifest = build_manifest([obj])
    return audit


def normalize_object_mapping(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
) -> tuple[dict[str, Any], bool]:
    candidate = _normalize_legacy_sources(
        data,
        path=path,
        promote_approved_legacy_sources=True,
    )
    obj = validate_object(candidate, path=path)
    normalized = obj.to_dict()
    if (
        isinstance(data.get("sources"), list)
        and str(data.get("review_status", "")).strip().lower() == "approved"
    ):
        legacy_sources = _normalize_legacy_sources(data, path=path)
        normalized["sources"] = legacy_sources["sources"]
    changed = _normalize_jsonable(data) != _normalize_jsonable(normalized)
    return normalized, changed


def migrate_object_file(path: Path | str) -> tuple[dict[str, Any], bool]:
    file_path = Path(path).resolve()
    raw = read_json_file(file_path)
    if not isinstance(raw, Mapping):
        raise CanonicalValidationError("CKL object must be a JSON object")
    return normalize_object_mapping(raw, path=file_path)


def _normalize_legacy_sources(
    data: Mapping[str, Any],
    *,
    path: str | Path | None = None,
    promote_approved_legacy_sources: bool = False,
) -> dict[str, Any]:
    candidate = dict(data)
    sources_value = candidate.get("sources")
    if not isinstance(sources_value, list):
        return candidate

    object_id = candidate.get("id") if isinstance(candidate.get("id"), str) else None
    review_status = str(candidate.get("review_status", "")).strip().lower()
    normalized_sources = normalize_sources_field(
        candidate,
        path=path,
        object_id=object_id,
    )
    if review_status == "approved" and promote_approved_legacy_sources:
        promoted_sources: list[dict[str, Any]] = []
        for raw_source, source in zip(sources_value, normalized_sources):
            if (
                isinstance(raw_source, str)
                and source.source_type in {"other", "website"}
            ):
                source = replace(source, source_type="reference-work")
            promoted_sources.append(source.to_dict())
        candidate["sources"] = promoted_sources
    else:
        candidate["sources"] = [source.to_dict() for source in normalized_sources]
    return candidate


def format_validation_summary(audit: LibraryAudit) -> str:
    lines = audit.summary_lines()
    if audit.warning_issues:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"- {_format_issue_line(issue)}" for issue in audit.warning_issues)
    if audit.duplicate_id_issues:
        lines.append("")
        lines.append("Duplicate IDs:")
        lines.extend(f"- {_format_issue_line(issue)}" for issue in audit.duplicate_id_issues)
    if audit.alias_collision_issues:
        lines.append("")
        lines.append("Alias collisions:")
        lines.extend(f"- {_format_issue_line(issue)}" for issue in audit.alias_collision_issues)
    if audit.unresolved_relationship_issues:
        lines.append("")
        lines.append("Unresolved relationships:")
        lines.extend(f"- {_format_issue_line(issue)}" for issue in audit.unresolved_relationship_issues)
    if audit.broken_scripture_reference_issues:
        lines.append("")
        lines.append("Broken scripture references:")
        lines.extend(f"- {_format_issue_line(issue)}" for issue in audit.broken_scripture_reference_issues)
    if audit.missing_content_issues:
        lines.append("")
        lines.append("Missing required content:")
        lines.extend(f"- {_format_issue_line(issue)}" for issue in audit.missing_content_issues)
    if audit.validation_issues:
        lines.append("")
        lines.append("Validation errors:")
        lines.extend(f"- {_format_issue_line(issue)}" for issue in audit.validation_issues)
    if audit.manifest_issues:
        lines.append("")
        lines.append("Manifest issues:")
        lines.extend(f"- {_format_issue_line(issue)}" for issue in audit.manifest_issues)
    return "\n".join(lines).strip()


def _complete_content_issues(
    obj: CanonicalObject,
    path: str,
) -> list[ValidationIssue]:
    if obj.content_status != "complete":
        return []
    issues: list[ValidationIssue] = []
    severity = _semantic_issue_severity(obj)
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
                    severity=severity,
                    details={"field": field_name},
                )
            )
    return issues


def _scripture_reference_issues(
    obj: CanonicalObject,
    path: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    severity = _semantic_issue_severity(obj)
    for reference in obj.scripture_references:
        reference_text = str(reference.reference).strip()
        if not reference_text:
            issues.append(
                ValidationIssue(
                    code="broken_scripture_reference",
                    message='field "reference" must not be blank',
                    path=path,
                    object_id=obj.id,
                    severity=severity,
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
                    severity=severity,
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
                    severity=severity,
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
        if issue.severity == "warning":
            audit.warning_issues.append(issue)
        elif issue.code == "duplicate_id":
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
