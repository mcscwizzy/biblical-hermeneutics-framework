"""Deep, read-only quality reporting for the Canonical Knowledge Library.

The quality report deliberately sits above the current schema validator.  It
measures migration debt without changing object loading, retrieval, or SQLite
serialization, which keeps Phase 1 safe for the existing runtime.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .authoring import COMPLETE_REQUIRED_FIELDS, resolve_authoring_root, scan_library
from .graph import graph_audit
from .normalization import normalize_alias, normalize_id, normalize_text
from .schema import (
    CATEGORY_FOLDERS,
    CURRENT_CERTAINTY_VALUES,
    CURRENT_DISPUTE_STATUS_VALUES,
    KNOWLEDGE_LAYER_VALUES,
    required_sections_for_type,
)


NEAR_DUPLICATE_THRESHOLD = 0.92
TEMPLATE_REPEAT_MINIMUM = 3
INTERNAL_SOURCE_PUBLISHERS = frozenset({"canonical knowledge library", "ckl"})
INTERNAL_SOURCE_MARKERS = (
    "internal ckl",
    "canonical historical orientation",
    "canonical knowledge library orientation",
)
REFERENCE_LIST_FIELDS: tuple[str, ...] = (
    "related_people",
    "related_places",
    "related_events",
    "related_entries",
)
TEMPLATE_SENSITIVE_FIELDS: tuple[str, ...] = (
    "summary",
    "historical_context",
    "ancient_near_east_context",
    "hebraic_worldview",
    "second_temple_context",
    "canonical_context",
    "later_christian_reception",
    "original_audience",
    "historical_setting",
    "canonical_role",
    "canonical_placement",
    "key_people",
    "key_places",
    "key_events",
    "major_themes",
)
CANDIDATE_QUALITY_SECTION_PATHS: tuple[str, ...] = (
    "canonical_story.phase",
    "canonical_story.role",
    "hermeneutical_lens.immediate_literary_context",
    "hermeneutical_lens.book_context",
    "hermeneutical_lens.canonical_context",
    "hermeneutical_lens.historical_context",
    "hermeneutical_lens.original_audience",
    "hermeneutical_lens.genre",
    "hermeneutical_lens.major_interpretive_views",
    "hermeneutical_lens.common_misinterpretations",
    "retrieval_metadata.search_terms",
    "retrieval_metadata.common_questions",
)
NON_COVERAGE_FIELDS = frozenset(
    {
        "id",
        "type",
        "title",
        "framework_version",
        "object_version",
        "importance",
    }
)


@dataclass(frozen=True)
class RawRecord:
    """One parseable CKL JSON record with its repository-relative path."""

    path: str
    payload: Mapping[str, Any]

    @property
    def object_id(self) -> str:
        return _safe_normalize_id(self.payload.get("id", ""))

    @property
    def object_type(self) -> str:
        return _safe_normalize_id(self.payload.get("type", "")).replace("-", "_")


def _safe_normalize_id(value: Any) -> str:
    return normalize_id(value) if isinstance(value, str) else ""


def _safe_normalize_text(value: Any) -> str:
    return normalize_text(value) if isinstance(value, str) else ""


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (Mapping, Sequence, set)) and not isinstance(value, str):
        return len(value) == 0
    return False


def _round_average(total: int, count: int) -> float:
    return round(total / count, 2) if count else 0.0


def _flatten_leaf_fields(
    value: Any,
    *,
    prefix: str = "",
) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(nested, Mapping):
                yield from _flatten_leaf_fields(nested, prefix=child)
            else:
                yield child, nested


def _load_raw_records(root: Path) -> tuple[list[RawRecord], list[dict[str, str]]]:
    records: list[RawRecord] = []
    failures: list[dict[str, str]] = []
    objects_root = root / "objects"
    for path in sorted(objects_root.rglob("*.json")) if objects_root.exists() else []:
        relative = path.relative_to(root).as_posix()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            failures.append({"path": relative, "error": str(exc)})
            continue
        if not isinstance(payload, Mapping):
            failures.append({"path": relative, "error": "root value is not an object"})
            continue
        records.append(RawRecord(path=relative, payload=payload))
    return records, failures


def _record_key(record: RawRecord) -> str:
    return record.object_id or record.path


def _field_coverage(records: Sequence[RawRecord]) -> dict[str, Any]:
    by_category: dict[str, list[RawRecord]] = defaultdict(list)
    for record in records:
        by_category[record.object_type or "<invalid>"].append(record)

    report: dict[str, Any] = {}
    for category, category_records in sorted(by_category.items()):
        field_names: set[str] = set()
        flattened: list[dict[str, Any]] = []
        for record in category_records:
            values = dict(_flatten_leaf_fields(record.payload))
            flattened.append(values)
            field_names.update(values)
        field_names -= NON_COVERAGE_FIELDS

        populated: dict[str, int] = {}
        empty: dict[str, int] = {}
        missing: dict[str, int] = {}
        for field_name in sorted(field_names):
            present_values = [values[field_name] for values in flattened if field_name in values]
            populated[field_name] = sum(not _is_empty(value) for value in present_values)
            empty[field_name] = sum(_is_empty(value) for value in present_values)
            missing[field_name] = len(flattened) - len(present_values)
        report[category] = {
            "object_count": len(category_records),
            "populated": populated,
            "empty": empty,
            "missing": missing,
        }
    return report


def _is_internal_source(source: Mapping[str, Any]) -> bool:
    publisher = _safe_normalize_text(source.get("publisher", ""))
    combined = normalize_text(
        " ".join(
            str(source.get(field_name, ""))
            for field_name in ("id", "title", "publisher", "notes")
        )
    )
    return publisher in INTERNAL_SOURCE_PUBLISHERS or any(
        marker in combined for marker in INTERNAL_SOURCE_MARKERS
    )


def _source_metrics(records: Sequence[RawRecord]) -> dict[str, Any]:
    unresolved: list[dict[str, str]] = []
    unsupported: list[dict[str, str]] = []
    invalid_support_targets: list[dict[str, str]] = []
    internally_only_supported: list[str] = []
    external_count = 0
    source_count = 0

    for record in records:
        payload = record.payload
        raw_sources = payload.get("sources", [])
        sources = [source for source in raw_sources if isinstance(source, Mapping)]
        source_count += len(sources)
        external_sources = [
            source
            for source in sources
            if _safe_normalize_id(source.get("source_type", "")) != "scripture"
            and not _is_internal_source(source)
        ]
        external_count += len(external_sources)

        source_ids = {
            _safe_normalize_id(source.get("id", ""))
            for source in sources
            if _safe_normalize_id(source.get("id", ""))
        }
        referenced_source_ids: set[str] = set()
        valid_support_targets = {
            _safe_normalize_id(field_name)
            for field_name, value in _flatten_leaf_fields(payload)
            if not _is_empty(value)
        }
        valid_support_targets.update(
            _safe_normalize_id(claim.get("id", ""))
            for claim in payload.get("claims", []) or []
            if isinstance(claim, Mapping)
        )
        valid_support_targets.discard("")
        for index, note in enumerate(payload.get("interpretive_notes", []) or []):
            if not isinstance(note, Mapping):
                continue
            for source_id in note.get("sources", []) or []:
                normalized = _safe_normalize_id(source_id)
                if not normalized:
                    continue
                referenced_source_ids.add(normalized)
                if normalized not in source_ids:
                    unresolved.append(
                        {
                            "object_id": _record_key(record),
                            "reference": f"interpretive_notes[{index}].sources",
                            "source_id": normalized,
                        }
                    )
        for index, claim in enumerate(payload.get("claims", []) or []):
            if not isinstance(claim, Mapping):
                continue
            for source_id in claim.get("source_ids", []) or []:
                normalized = _safe_normalize_id(source_id)
                if not normalized:
                    continue
                referenced_source_ids.add(normalized)
                if normalized not in source_ids:
                    unresolved.append(
                        {
                            "object_id": _record_key(record),
                            "reference": f"claims[{index}].source_ids",
                            "source_id": normalized,
                        }
                    )

        for source in sources:
            source_id = _safe_normalize_id(source.get("id", "")) or "<missing-id>"
            supports = source.get("supports", []) or []
            normalized_supports = {
                _safe_normalize_id(support)
                for support in supports
                if _safe_normalize_id(support)
            }
            invalid_targets = sorted(normalized_supports - valid_support_targets)
            for target in invalid_targets:
                invalid_support_targets.append(
                    {
                        "object_id": _record_key(record),
                        "source_id": source_id,
                        "support_target": target,
                    }
                )
            has_valid_support = bool(normalized_supports & valid_support_targets)
            if not has_valid_support and source_id not in referenced_source_ids:
                unsupported.append(
                    {"object_id": _record_key(record), "source_id": source_id}
                )

        has_claim_bearing_content = any(
            not _is_empty(payload.get(field_name))
            for field_name in (
                "historical_context",
                "ancient_near_east_context",
                "hebraic_worldview",
                "second_temple_context",
                "later_christian_reception",
                "interpretive_notes",
                "claims",
            )
        )
        has_internal = any(_is_internal_source(source) for source in sources)
        if has_claim_bearing_content and has_internal and not external_sources:
            internally_only_supported.append(_record_key(record))

    return {
        "source_count": source_count,
        "external_source_count": external_count,
        "average_external_sources_per_object": _round_average(
            external_count, len(records)
        ),
        "unresolved_source_reference_count": len(unresolved),
        "unresolved_source_references": unresolved,
        "sources_supporting_no_field_or_claim_count": len(unsupported),
        "sources_supporting_no_field_or_claim": unsupported,
        "invalid_source_support_target_count": len(invalid_support_targets),
        "invalid_source_support_targets": invalid_support_targets,
        "internally_self_cited_without_external_support_count": len(
            internally_only_supported
        ),
        "internally_self_cited_without_external_support": sorted(
            set(internally_only_supported)
        ),
    }


def _governance_metrics(records: Sequence[RawRecord]) -> dict[str, Any]:
    no_reviewers: list[str] = []
    human_review_required: list[str] = []
    unknown_certainty: list[str] = []
    unknown_dispute: list[str] = []
    unknown_certainty_notes = 0
    unknown_dispute_notes = 0

    for record in records:
        object_key = _record_key(record)
        if _is_empty(record.payload.get("reviewed_by")):
            no_reviewers.append(object_key)
        if record.payload.get("human_review_required") is True:
            human_review_required.append(object_key)
        for note in record.payload.get("interpretive_notes", []) or []:
            if not isinstance(note, Mapping):
                continue
            if _safe_normalize_id(note.get("certainty", "")) in {"", "unknown"}:
                unknown_certainty_notes += 1
                unknown_certainty.append(object_key)
            if _safe_normalize_id(note.get("dispute_status", "")) in {"", "unknown"}:
                unknown_dispute_notes += 1
                unknown_dispute.append(object_key)

    return {
        "records_with_no_reviewed_by_count": len(no_reviewers),
        "records_with_no_reviewed_by": sorted(no_reviewers),
        "records_requiring_human_review_count": len(human_review_required),
        "records_requiring_human_review": sorted(human_review_required),
        "records_with_unknown_certainty_count": len(set(unknown_certainty)),
        "records_with_unknown_certainty": sorted(set(unknown_certainty)),
        "interpretive_notes_with_unknown_certainty_count": unknown_certainty_notes,
        "records_with_unknown_dispute_status_count": len(set(unknown_dispute)),
        "records_with_unknown_dispute_status": sorted(set(unknown_dispute)),
        "interpretive_notes_with_unknown_dispute_status_count": unknown_dispute_notes,
    }


def _normalized_for_similarity(value: Any) -> str:
    text = _safe_normalize_text(value)
    return re.sub(r"[^a-z0-9 ]+", "", text)


def _duplicate_text_groups(
    records: Sequence[RawRecord],
    field_name: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    values: list[tuple[str, str, str, Counter[str], float]] = []
    exact_index: dict[str, list[str]] = defaultdict(list)
    for record in records:
        raw_value = record.payload.get(field_name, "")
        if not isinstance(raw_value, str):
            continue
        normalized = _normalized_for_similarity(raw_value)
        if not normalized:
            continue
        object_key = _record_key(record)
        tokens = Counter(normalized.split())
        norm = math.sqrt(sum(count * count for count in tokens.values()))
        values.append((object_key, raw_value.strip(), normalized, tokens, norm))
        exact_index[normalized].append(object_key)

    exact = [
        {"value": normalized, "object_ids": sorted(object_ids)}
        for normalized, object_ids in sorted(exact_index.items())
        if len(object_ids) > 1
    ]
    near: list[dict[str, Any]] = []
    for index, (
        left_id,
        left_raw,
        left_normalized,
        left_tokens,
        left_norm,
    ) in enumerate(values):
        for (
            right_id,
            right_raw,
            right_normalized,
            right_tokens,
            right_norm,
        ) in values[index + 1 :]:
            if left_normalized == right_normalized:
                continue
            shorter = min(len(left_normalized), len(right_normalized))
            if shorter < 24 and field_name == "summary":
                continue
            length_ratio = shorter / max(len(left_normalized), len(right_normalized))
            if length_ratio < 0.75:
                continue
            if field_name == "summary":
                dot_product = sum(
                    count * right_tokens.get(token, 0)
                    for token, count in left_tokens.items()
                )
                ratio = (
                    dot_product / (left_norm * right_norm)
                    if left_norm and right_norm
                    else 0.0
                )
            else:
                ratio = SequenceMatcher(
                    None, left_normalized, right_normalized
                ).ratio()
            if ratio >= NEAR_DUPLICATE_THRESHOLD:
                near.append(
                    {
                        "left_id": left_id,
                        "right_id": right_id,
                        "similarity": round(ratio, 4),
                        "left_value": left_raw,
                        "right_value": right_raw,
                    }
                )
    return exact, sorted(
        near, key=lambda item: (-item["similarity"], item["left_id"], item["right_id"])
    )


def _alias_metrics(records: Sequence[RawRecord]) -> dict[str, Any]:
    aliases: dict[str, list[dict[str, str]]] = defaultdict(list)
    duplicate_within: list[dict[str, Any]] = []
    for record in records:
        seen: Counter[str] = Counter()
        for alias in record.payload.get("aliases", []) or []:
            if not isinstance(alias, str) or not normalize_alias(alias):
                continue
            normalized = normalize_alias(alias)
            seen[normalized] += 1
            aliases[normalized].append(
                {
                    "object_id": _record_key(record),
                    "object_type": record.object_type,
                }
            )
        for alias, count in seen.items():
            if count > 1:
                duplicate_within.append(
                    {
                        "object_id": _record_key(record),
                        "alias": alias,
                        "count": count,
                    }
                )

    collisions: list[dict[str, Any]] = []
    unrelated_collisions: list[dict[str, Any]] = []
    for alias, occurrences in sorted(aliases.items()):
        object_ids = sorted({item["object_id"] for item in occurrences})
        if len(object_ids) < 2:
            continue
        item = {"alias": alias, "object_ids": object_ids}
        collisions.append(item)
        if len({item["object_type"] for item in occurrences}) > 1:
            unrelated_collisions.append(item)
    return {
        "duplicate_aliases_within_record_count": len(duplicate_within),
        "duplicate_aliases_within_record": duplicate_within,
        "alias_collision_count": len(collisions),
        "alias_collisions": collisions,
        "unrelated_alias_collision_count": len(unrelated_collisions),
        "unrelated_alias_collisions": unrelated_collisions,
    }


def _retrieval_gaps(records: Sequence[RawRecord]) -> dict[str, Any]:
    no_search_terms: list[str] = []
    no_common_questions: list[str] = []
    no_canonical_placement: list[str] = []
    for record in records:
        metadata = record.payload.get("retrieval_metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        if _is_empty(metadata.get("search_terms")):
            no_search_terms.append(_record_key(record))
        if _is_empty(metadata.get("common_questions")) and _is_empty(
            record.payload.get("common_questions")
        ):
            no_common_questions.append(_record_key(record))
        if _is_empty(record.payload.get("canonical_placement")):
            no_canonical_placement.append(_record_key(record))
    return {
        "objects_without_retrieval_search_terms_count": len(no_search_terms),
        "objects_without_retrieval_search_terms": sorted(no_search_terms),
        "objects_without_common_questions_count": len(no_common_questions),
        "objects_without_common_questions": sorted(no_common_questions),
        "objects_without_canonical_placement_count": len(no_canonical_placement),
        "objects_without_canonical_placement": sorted(no_canonical_placement),
    }


def _template_repetition(records: Sequence[RawRecord]) -> dict[str, Any]:
    occurrences: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for record in records:
        for field_name in TEMPLATE_SENSITIVE_FIELDS:
            value = record.payload.get(field_name)
            if _is_empty(value):
                continue
            if isinstance(value, list):
                normalized_value = json.dumps(
                    sorted(_safe_normalize_text(item) for item in value),
                    sort_keys=True,
                )
            elif isinstance(value, str):
                normalized_value = _normalized_for_similarity(value)
            else:
                continue
            if len(normalized_value) < 16:
                continue
            occurrences[(field_name, normalized_value)].append(
                (_record_key(record), record.object_type)
            )

    repeated = [
        {
            "field": field_name,
            "object_types": sorted({object_type for _object_id, object_type in entries}),
            "occurrence_count": len(entries),
            "object_ids": sorted(object_id for object_id, _object_type in entries),
        }
        for (field_name, _value), entries in occurrences.items()
        if len(entries) >= TEMPLATE_REPEAT_MINIMUM
    ]
    repeated.sort(
        key=lambda item: (
            -item["occurrence_count"],
            item["field"],
            item["object_ids"],
        )
    )
    affected = {
        object_id for item in repeated for object_id in item["object_ids"]
    }
    return {
        "suspicious_template_repetition_group_count": len(repeated),
        "suspicious_template_repetition_record_count": len(affected),
        "suspicious_template_repetitions": repeated,
    }


def _reference_and_type_issues(
    records: Sequence[RawRecord],
) -> dict[str, Any]:
    known_ids = {record.object_id for record in records if record.object_id}
    unresolved_legacy: list[dict[str, str]] = []
    inconsistent: list[dict[str, str]] = []

    for record in records:
        payload = record.payload
        for field_name in REFERENCE_LIST_FIELDS:
            for value in payload.get(field_name, []) or []:
                target_id = _safe_normalize_id(value)
                if target_id and target_id not in known_ids:
                    unresolved_legacy.append(
                        {
                            "object_id": _record_key(record),
                            "field": field_name,
                            "target_id": target_id,
                        }
                    )
        story = payload.get("canonical_story")
        if isinstance(story, Mapping):
            for field_name in ("preceded_by", "followed_by"):
                for value in story.get(field_name, []) or []:
                    target_id = _safe_normalize_id(value)
                    if target_id and target_id not in known_ids:
                        unresolved_legacy.append(
                            {
                                "object_id": _record_key(record),
                                "field": f"canonical_story.{field_name}",
                                "target_id": target_id,
                            }
                        )

        path = Path(record.path)
        actual_folder = path.parent.name
        expected_folder = CATEGORY_FOLDERS.get(record.object_type)
        if expected_folder and actual_folder != expected_folder:
            inconsistent.append(
                {
                    "object_id": _record_key(record),
                    "issue": "object type does not match directory",
                    "expected": expected_folder,
                    "actual": actual_folder,
                }
            )
        if record.object_id and path.stem != record.object_id:
            inconsistent.append(
                {
                    "object_id": _record_key(record),
                    "issue": "object id does not match filename",
                    "expected": record.object_id,
                    "actual": path.stem,
                }
            )

    return {
        "unresolved_legacy_object_reference_count": len(unresolved_legacy),
        "unresolved_legacy_object_references": unresolved_legacy,
        "type_or_path_inconsistency_count": len(inconsistent),
        "type_or_path_inconsistencies": inconsistent,
    }


def _complete_record_gaps(records: Sequence[RawRecord]) -> dict[str, Any]:
    gaps: list[dict[str, Any]] = []
    candidate_section_gaps: list[dict[str, Any]] = []
    for record in records:
        if _safe_normalize_id(record.payload.get("content_status", "")) != "complete":
            continue
        empty_fields = [
            field_name
            for field_name in COMPLETE_REQUIRED_FIELDS
            if _is_empty(record.payload.get(field_name))
        ]
        if empty_fields:
            gaps.append(
                {"object_id": _record_key(record), "empty_fields": empty_fields}
            )
        flattened = dict(_flatten_leaf_fields(record.payload))
        empty_candidate_sections = [
            field_path
            for field_path in CANDIDATE_QUALITY_SECTION_PATHS
            if _is_empty(flattened.get(field_path))
        ]
        if empty_candidate_sections:
            candidate_section_gaps.append(
                {
                    "object_id": _record_key(record),
                    "empty_sections": empty_candidate_sections,
                }
            )
    return {
        "complete_records_with_empty_required_fields_count": len(gaps),
        "complete_records_with_empty_required_fields": gaps,
        "complete_records_with_candidate_quality_gaps_count": len(
            candidate_section_gaps
        ),
        "complete_records_with_candidate_quality_gaps": candidate_section_gaps,
    }


def _foundation_migration_metrics(records: Sequence[RawRecord]) -> dict[str, Any]:
    missing_section_status: list[str] = []
    incomplete_required_sections: list[dict[str, Any]] = []
    missing_knowledge_layers: list[str] = []
    invalid_knowledge_layers: list[dict[str, str]] = []
    primary_layer_counts: Counter[str] = Counter()
    current_notes = 0
    legacy_notes = 0
    claim_count = 0

    for record in records:
        object_key = _record_key(record)
        section_status = record.payload.get("section_status")
        if not isinstance(section_status, Mapping):
            missing_section_status.append(object_key)
            incomplete = list(required_sections_for_type(record.object_type))
        else:
            incomplete = [
                section_name
                for section_name in required_sections_for_type(record.object_type)
                if section_status.get(section_name) not in {"complete", "not_applicable"}
            ]
        if incomplete:
            incomplete_required_sections.append(
                {"object_id": object_key, "sections": incomplete}
            )

        knowledge_layers = record.payload.get("knowledge_layers")
        if not isinstance(knowledge_layers, Mapping):
            missing_knowledge_layers.append(object_key)
        else:
            primary = str(knowledge_layers.get("primary") or "").strip()
            if primary not in KNOWLEDGE_LAYER_VALUES:
                invalid_knowledge_layers.append(
                    {"object_id": object_key, "primary": primary}
                )
            else:
                primary_layer_counts[primary] += 1

        for note in record.payload.get("interpretive_notes", []) or []:
            if not isinstance(note, Mapping):
                legacy_notes += 1
                continue
            if (
                note.get("certainty") in CURRENT_CERTAINTY_VALUES
                and note.get("dispute_status") in CURRENT_DISPUTE_STATUS_VALUES
            ):
                current_notes += 1
            else:
                legacy_notes += 1
        claim_count += len(record.payload.get("claims", []) or [])

    return {
        "records_missing_section_status_count": len(missing_section_status),
        "records_missing_section_status": sorted(missing_section_status),
        "records_with_incomplete_required_sections_count": len(
            incomplete_required_sections
        ),
        "records_with_incomplete_required_sections": incomplete_required_sections,
        "records_missing_knowledge_layers_count": len(missing_knowledge_layers),
        "records_missing_knowledge_layers": sorted(missing_knowledge_layers),
        "invalid_primary_knowledge_layer_count": len(invalid_knowledge_layers),
        "invalid_primary_knowledge_layers": invalid_knowledge_layers,
        "primary_knowledge_layer_counts": dict(sorted(primary_layer_counts.items())),
        "interpretive_notes_using_current_taxonomies_count": current_notes,
        "interpretive_notes_using_legacy_taxonomies_count": legacy_notes,
        "claim_count": claim_count,
    }


def build_quality_report(
    root: Path | str,
    *,
    include_manifest: bool = True,
) -> dict[str, Any]:
    """Build the machine-readable Phase 1 CKL quality report."""

    ckl_root = resolve_authoring_root(root)
    audit = scan_library(ckl_root, include_manifest=include_manifest)
    records, parse_failures = _load_raw_records(ckl_root)
    objects = list(audit.valid_objects.values())
    graph = graph_audit(objects)

    title_exact, title_near = _duplicate_text_groups(records, "title")
    summary_exact, summary_near = _duplicate_text_groups(records, "summary")
    source_metrics = _source_metrics(records)
    governance = _governance_metrics(records)
    aliases = _alias_metrics(records)
    retrieval = _retrieval_gaps(records)
    templates = _template_repetition(records)
    references = _reference_and_type_issues(records)
    complete_gaps = _complete_record_gaps(records)
    foundation_migration = _foundation_migration_metrics(records)

    summary_characters = sum(
        len(str(record.payload.get("summary", "")).strip()) for record in records
    )
    scripture_count = sum(
        len(record.payload.get("scripture_references", []) or []) for record in records
    )
    relationship_count = sum(
        len(record.payload.get("related_objects", []) or []) for record in records
    )
    issue_codes = Counter(issue.code for issue in audit.issues())
    duplicate_ids = [
        {"id": object_id, "paths": paths}
        for object_id, paths in sorted(audit.raw_id_occurrences.items())
        if len(paths) > 1
    ]

    return {
        "report_version": "1.1",
        "root": str(ckl_root),
        "inventory": {
            "raw_object_count": len(records) + len(parse_failures),
            "parseable_object_count": len(records),
            "valid_object_count": audit.valid_object_count,
            "parse_failure_count": len(parse_failures),
            "parse_failures": parse_failures,
            "category_counts": dict(
                sorted(Counter(record.object_type for record in records).items())
            ),
            "content_status_counts": dict(sorted(audit.content_status_counts.items())),
            "review_status_counts": dict(sorted(audit.review_status_counts.items())),
        },
        "field_coverage_by_category": _field_coverage(records),
        "averages": {
            "summary_characters": _round_average(summary_characters, len(records)),
            "scripture_references": _round_average(scripture_count, len(records)),
            "external_sources": source_metrics[
                "average_external_sources_per_object"
            ],
            "relationships": _round_average(relationship_count, len(records)),
        },
        "graph": {
            "edge_count": graph.edge_count,
            "dangling_relationship_count": len(graph.unknown_target_edges),
            "dangling_relationships": [
                edge.to_dict() for edge in graph.unknown_target_edges
            ],
            "missing_reciprocal_relationship_count": len(
                graph.missing_reverse_edges
            ),
            "missing_reciprocal_relationships": [
                suggestion.to_dict() for suggestion in graph.missing_reverse_edges
            ],
            "orphaned_object_count": len(graph.orphaned_object_ids),
            "orphaned_object_ids": graph.orphaned_object_ids,
        },
        "completeness": complete_gaps,
        "foundation_migration": foundation_migration,
        "governance": governance,
        "duplicates": {
            "duplicate_id_count": len(duplicate_ids),
            "duplicate_ids": duplicate_ids,
            "duplicate_title_group_count": len(title_exact),
            "duplicate_title_groups": title_exact,
            "near_duplicate_title_pair_count": len(title_near),
            "near_duplicate_title_pairs": title_near,
            "duplicate_summary_group_count": len(summary_exact),
            "duplicate_summary_groups": summary_exact,
            "near_duplicate_summary_pair_count": len(summary_near),
            "near_duplicate_summary_pairs": summary_near,
            **aliases,
        },
        "retrieval_gaps": retrieval,
        "template_repetition": templates,
        "references": {
            "scripture_reference_error_count": sum(
                issue_codes[code]
                for code in ("broken_scripture_reference",)
            ),
            "scripture_reference_errors": [
                issue.to_dict()
                for issue in audit.issues()
                if issue.code == "broken_scripture_reference"
            ],
            **references,
        },
        "sources": {
            key: value
            for key, value in source_metrics.items()
            if key != "average_external_sources_per_object"
        },
        "validation": {
            "issue_count": audit.issue_count,
            "warning_count": audit.warning_count,
            "error_count": audit.error_count,
            "issue_counts_by_code": dict(sorted(issue_codes.items())),
            "issues": [issue.to_dict() for issue in audit.issues()],
        },
    }


def _count_line(label: str, value: Any) -> str:
    return f"- {label}: {value}"


def _sample_ids(values: Sequence[Any], *, limit: int) -> str:
    samples: list[str] = []
    for value in values[:limit]:
        if isinstance(value, Mapping):
            object_id = value.get("object_id") or value.get("id")
            samples.append(str(object_id or value))
        else:
            samples.append(str(value))
    suffix = f" … (+{len(values) - limit} more)" if len(values) > limit else ""
    return ", ".join(samples) + suffix


def format_quality_markdown(
    report: Mapping[str, Any],
    *,
    sample_limit: int = 10,
) -> str:
    """Render a compact human-readable counterpart to the JSON report."""

    inventory = report["inventory"]
    averages = report["averages"]
    graph = report["graph"]
    completeness = report["completeness"]
    foundation = report["foundation_migration"]
    governance = report["governance"]
    duplicates = report["duplicates"]
    retrieval = report["retrieval_gaps"]
    templates = report["template_repetition"]
    references = report["references"]
    sources = report["sources"]
    validation = report["validation"]

    lines = [
        "# CKL Deep Quality Report",
        "",
        f"Root: `{report['root']}`",
        "",
        "## Inventory",
        "",
        _count_line("Object files scanned", inventory["raw_object_count"]),
        _count_line("Parseable object records", inventory["parseable_object_count"]),
        _count_line("Schema-valid unique objects", inventory["valid_object_count"]),
        _count_line("Parse failures", inventory["parse_failure_count"]),
        _count_line(
            "Categories",
            ", ".join(
                f"{key}={value}"
                for key, value in inventory["category_counts"].items()
            ),
        ),
        "",
        "## Depth averages",
        "",
        _count_line("Summary length (characters)", averages["summary_characters"]),
        _count_line("Scripture references per object", averages["scripture_references"]),
        _count_line("External sources per object", averages["external_sources"]),
        _count_line("Relationships per object", averages["relationships"]),
        "",
        "## Graph and references",
        "",
        _count_line("Dangling relationship IDs", graph["dangling_relationship_count"]),
        _count_line(
            "Missing reciprocal relationships",
            graph["missing_reciprocal_relationship_count"],
        ),
        _count_line("Orphaned objects", graph["orphaned_object_count"]),
        _count_line(
            "Unresolved legacy object references",
            references["unresolved_legacy_object_reference_count"],
        ),
        _count_line(
            "Scripture reference format/range errors",
            references["scripture_reference_error_count"],
        ),
        _count_line(
            "Type/path inconsistencies", references["type_or_path_inconsistency_count"]
        ),
        "",
        "## Completeness and governance",
        "",
        _count_line(
            "Complete records with empty required fields",
            completeness["complete_records_with_empty_required_fields_count"],
        ),
        _count_line(
            "Complete records with candidate Phase 2 section gaps",
            completeness["complete_records_with_candidate_quality_gaps_count"],
        ),
        _count_line(
            "Records missing section_status",
            foundation["records_missing_section_status_count"],
        ),
        _count_line(
            "Records with incomplete type-required sections",
            foundation["records_with_incomplete_required_sections_count"],
        ),
        _count_line(
            "Records missing knowledge_layers",
            foundation["records_missing_knowledge_layers_count"],
        ),
        _count_line(
            "Interpretive notes using current taxonomies",
            foundation["interpretive_notes_using_current_taxonomies_count"],
        ),
        _count_line(
            "Interpretive notes still using legacy taxonomies",
            foundation["interpretive_notes_using_legacy_taxonomies_count"],
        ),
        _count_line("Granular claims", foundation["claim_count"]),
        _count_line(
            "Records with unknown certainty",
            governance["records_with_unknown_certainty_count"],
        ),
        _count_line(
            "Records with unknown dispute status",
            governance["records_with_unknown_dispute_status_count"],
        ),
        _count_line(
            "Records with no human reviewer",
            governance["records_with_no_reviewed_by_count"],
        ),
        _count_line(
            "Records requiring human review",
            governance["records_requiring_human_review_count"],
        ),
        "",
        "## Duplicate and template signals",
        "",
        _count_line("Duplicate IDs", duplicates["duplicate_id_count"]),
        _count_line(
            "Duplicate/near-duplicate title findings",
            duplicates["duplicate_title_group_count"]
            + duplicates["near_duplicate_title_pair_count"],
        ),
        _count_line(
            "Duplicate/near-duplicate summary findings",
            duplicates["duplicate_summary_group_count"]
            + duplicates["near_duplicate_summary_pair_count"],
        ),
        _count_line("Alias collisions", duplicates["alias_collision_count"]),
        _count_line(
            "Alias collisions across object types",
            duplicates["unrelated_alias_collision_count"],
        ),
        _count_line(
            "Suspicious template-repetition groups",
            templates["suspicious_template_repetition_group_count"],
        ),
        "",
        "## Retrieval gaps",
        "",
        _count_line(
            "Objects without search terms",
            retrieval["objects_without_retrieval_search_terms_count"],
        ),
        _count_line(
            "Objects without common questions",
            retrieval["objects_without_common_questions_count"],
        ),
        _count_line(
            "Objects without canonical placement",
            retrieval["objects_without_canonical_placement_count"],
        ),
        "",
        "## Source integrity",
        "",
        _count_line(
            "Unresolved source IDs", sources["unresolved_source_reference_count"]
        ),
        _count_line(
            "Sources supporting no field or claim",
            sources["sources_supporting_no_field_or_claim_count"],
        ),
        _count_line(
            "Invalid source support targets",
            sources["invalid_source_support_target_count"],
        ),
        _count_line(
            "Internally self-cited records without external support",
            sources["internally_self_cited_without_external_support_count"],
        ),
        "",
        "## Existing validator",
        "",
        _count_line("Warnings", validation["warning_count"]),
        _count_line("Errors", validation["error_count"]),
    ]

    sample_sections = (
        (
            "Complete-record gap samples",
            completeness["complete_records_with_empty_required_fields"],
        ),
        (
            "Unknown-certainty record samples",
            governance["records_with_unknown_certainty"],
        ),
        (
            "Template-repetition record samples",
            sorted(
                {
                    object_id
                    for item in templates["suspicious_template_repetitions"]
                    for object_id in item["object_ids"]
                }
            ),
        ),
        (
            "Internal-only source samples",
            sources["internally_self_cited_without_external_support"],
        ),
    )
    for heading, values in sample_sections:
        if values:
            lines.extend(
                [
                    "",
                    f"### {heading}",
                    "",
                    _sample_ids(values, limit=sample_limit),
                ]
            )

    lines.extend(
        [
            "",
        "## Interpretation note",
        "",
        "These are triage signals, not factual-review verdicts. Near-duplicate and "
        "template checks are deterministic heuristics; source-support counts use "
        "the current inline source model. The Phase 2 type-specific completion "
        "rules now expose migration debt without rewriting or approving records.",
    ]
    )
    return "\n".join(lines) + "\n"
