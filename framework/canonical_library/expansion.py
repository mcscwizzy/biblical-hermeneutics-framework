"""Shared validation and change tracking for CKL evidence expansion.

Expansion candidates are intentionally data-only.  This adapter validates the
candidate against the same object/library validators used by CKL authoring,
then applies the existing Scripture-anchor and provenance rules before any
caller is allowed to write a record.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from .normalization import normalize_id
from .schema import (
    CanonicalObject,
    validate_library,
    validate_object,
    validate_source_entry,
)
from .semantic_deduplication import semantic_claim_fingerprint
from .scripture import (
    build_book_alias_lookup,
    format_scripture_reference,
    parse_scripture_references,
    scripture_reference_overlaps,
)


_INTERPRETIVE_CLAIM_TYPES = frozenset(
    {
        "biblical_theology",
        "systematic_theology",
        "pastoral_application",
        "denominational_interpretation",
    }
)
_INTERPRETIVE_MARKERS = frozenset(
    {"symbolizes", "spiritual", "theologically", "represents", "fulfills", "means"}
)
_TEMPORAL_RELATIONSHIPS = frozenset(
    {"controlled-by", "territory-of", "part-of", "region-of", "located-in", "ruled-by", "political-context"}
)
_TEMPORAL_CLAIM_PATTERNS = (
    re.compile(r"\bcontrolled by\b", re.IGNORECASE),
    re.compile(r"\b(?:province|district) of\b", re.IGNORECASE),
    re.compile(r"\bunder (?:the )?(?:rule|control|empire|kingdom) of\b", re.IGNORECASE),
)
_PARENT_FIELDS_PROJECTED_WITH_CHILDREN = frozenset(
    {
        "confidence",
        "content_status",
        "human_review_required",
        "importance",
        "object_version",
        "review_status",
        "title",
        "type",
    }
)


@dataclass(frozen=True)
class CandidateValidation:
    accepted: bool
    candidate: dict[str, Any]
    reasons: list[str] = field(default_factory=list)
    normalized_claim: dict[str, Any] | None = None
    normalized_evidence_item: dict[str, Any] | None = None
    changed_references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateApplication:
    """Result of a dry-run or explicit CKL candidate transaction."""

    decisions: list[CandidateValidation]
    changed_object_ids: list[str]
    changed_references: list[str]
    changed_chapters: list[str]
    wrote: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_count": len(self.decisions),
            "accepted": [item.to_dict() for item in self.decisions if item.accepted],
            "rejected": [item.to_dict() for item in self.decisions if not item.accepted],
            "changed_object_ids": list(self.changed_object_ids),
            "changed_references": list(self.changed_references),
            "changed_chapters": list(self.changed_chapters),
            "wrote": self.wrote,
        }


def validate_candidate(
    candidate: Mapping[str, Any],
    *,
    library: Any,
) -> CandidateValidation:
    """Validate one candidate without mutating the loaded CKL."""

    payload = dict(candidate)
    reasons: list[str] = []
    dimension = normalize_id(str(payload.get("dimension") or ""))
    target_id = normalize_id(str(payload.get("target_object_id") or ""))
    claim = dict(payload.get("claim") or {}) if isinstance(payload.get("claim"), Mapping) else {}
    evidence_item = (
        dict(payload.get("evidence_item") or {})
        if isinstance(payload.get("evidence_item"), Mapping)
        else {}
    )
    passage_reference = str(payload.get("passage_reference") or "").strip()
    if not dimension:
        reasons.append("dimension-required")
    if not target_id:
        reasons.append("target-object-required")
    if bool(claim) == bool(evidence_item):
        reasons.append("exactly-one-child-required")

    target = _get_object(library, target_id)
    if target is None and target_id:
        reasons.append("target-object-not-found")

    child = evidence_item or claim
    evidence = bool(evidence_item)
    if dimension == "geography" and target is not None:
        allowed_types = {"place", "event", "book"}
        numbers_18_levites = (
            evidence
            and target_id == "levites"
            and passage_reference.startswith("Numbers 18:")
            and bool(evidence_item.get("temporal_scope"))
            and any(
                normalize_id(str(_mapping(item).get("relationship") or "")) == "territory-of"
                and re.search(
                    r"\b(?:negative|no|without|excluded)\b",
                    str(_mapping(item).get("notes") or "").casefold(),
                )
                for item in _sequence(evidence_item.get("related_objects"))
            )
        )
        if _value(target, "type") not in allowed_types and not (
            _value(target, "type") == "institution" and numbers_18_levites
        ):
            reasons.append("geography-target-not-relevant")
    anchors = _claim_anchors(child, evidence=evidence)
    if not anchors:
        reasons.append("scripture-anchor-required")
    elif not _parseable(anchors):
        reasons.append("scripture-anchor-unparseable")
    elif passage_reference and not _anchors_overlap(passage_reference, anchors):
        reasons.append("scripture-anchor-not-eligible")

    source_ids = _string_list(child.get("source_ids"))
    source_map = _object_sources(target) if target is not None else {}
    candidate_sources = _candidate_sources(payload)
    for candidate_source in candidate_sources:
        source_map[normalize_id(str(candidate_source["id"]))] = candidate_source
    if not source_ids:
        reasons.append("source-provenance-required")
    elif any(source_id not in source_map for source_id in source_ids):
        reasons.append("source-provenance-unresolved")

    claim_type = normalize_id(str(child.get("claim_type") or child.get("evidence_type") or ""))
    claim_text = str(
        child.get("claim")
        or child.get("description")
        or child.get("primary_observation")
        or ""
    )
    if claim_type in _INTERPRETIVE_CLAIM_TYPES or _INTERPRETIVE_MARKERS.intersection(
        set(re.findall(r"[a-z]+", claim_text.casefold()))
    ):
        reasons.append("interpretive-claim")
    relationships = {
        normalize_id(str(payload.get("relationship") or "")),
        *{
            normalize_id(str(_mapping(item).get("relationship") or ""))
            for item in _sequence(child.get("related_objects"))
        },
    }
    temporal_relationship = bool(relationships.intersection(_TEMPORAL_RELATIONSHIPS)) or any(
        pattern.search(claim_text)
        for pattern in _TEMPORAL_CLAIM_PATTERNS
    )
    if temporal_relationship:
        temporal_scope = child.get("temporal_scope") if evidence else payload.get("temporal_scope")
        if not temporal_scope:
            reasons.append("historical-relationship-requires-temporal-scope")
        elif not evidence:
            # CanonicalClaim has no temporal_scope field.  Accepting this
            # queue entry as a claim would silently discard the qualifier and
            # create a timeless relationship.  A future writer must represent
            # it as a CanonicalEvidenceItem, whose schema can retain time.
            reasons.append("historical-relationship-requires-temporal-evidence-item")
    elif payload.get("temporal_scope") and not evidence:
        # This candidate adapter currently merges CanonicalClaim records only.
        # Never accept an out-of-schema qualifier that the merge would drop.
        reasons.append("historical-relationship-requires-temporal-evidence-item")

    if target is not None and _semantic_duplicate(target, child):
        reasons.append("semantic-duplicate")

    normalized_claim: dict[str, Any] | None = None
    normalized_evidence_item: dict[str, Any] | None = None
    if target is not None and not reasons:
        normalized_child = _validate_merged_target(
            target,
            child,
            candidate_sources,
            library=library,
            child_field="evidence_items" if evidence else "claims",
        )
        if normalized_child is None:
            reasons.append("ckl-validation-failed")
        elif evidence:
            normalized_evidence_item = normalized_child
        else:
            normalized_claim = normalized_child

    return CandidateValidation(
        accepted=not reasons,
        candidate=payload,
        reasons=list(dict.fromkeys(reasons)),
        normalized_claim=normalized_claim,
        normalized_evidence_item=normalized_evidence_item,
        changed_references=_canonical_anchor_strings(anchors),
    )


def validate_candidates(
    candidates: Iterable[Mapping[str, Any]],
    *,
    library: Any,
) -> list[CandidateValidation]:
    """Validate and semantically deduplicate a candidate queue."""

    decisions: list[CandidateValidation] = []
    seen: set[str] = set()
    for candidate in candidates:
        decision = validate_candidate(candidate, library=library)
        if decision.accepted:
            child = decision.normalized_evidence_item or decision.normalized_claim or {}
            fingerprint = "|".join(
                (
                    normalize_id(str(candidate.get("target_object_id") or "")),
                    semantic_claim_fingerprint(
                        child.get("claim")
                        or child.get("description")
                        or child.get("primary_observation"),
                        child.get("claim_type") or child.get("evidence_type"),
                    ),
                )
            )
            if fingerprint in seen:
                decision = CandidateValidation(
                    accepted=False,
                    candidate=decision.candidate,
                    reasons=[*decision.reasons, "semantic-duplicate"],
                    normalized_claim=decision.normalized_claim,
                    normalized_evidence_item=decision.normalized_evidence_item,
                    changed_references=decision.changed_references,
                )
            else:
                seen.add(fingerprint)
        decisions.append(decision)
    return decisions


def apply_candidate_queue(
    root: str | Path,
    candidates: Iterable[Mapping[str, Any]],
    *,
    write: bool = False,
) -> CandidateApplication:
    """Validate a queue as one transaction and optionally write its accepted children.

    A dry run exercises the same object and library validators as an apply but
    never changes disk.  Applying is explicit and touches only source files of
    accepted target objects after the whole resulting library validates.
    """

    from .loader import CanonicalLibrary

    library = CanonicalLibrary(root=Path(root)).load()
    candidate_values = [dict(item) for item in candidates]
    decisions = validate_candidates(candidate_values, library=library)
    accepted = [item for item in decisions if item.accepted]
    before_objects = list(library.objects_by_id.values())
    after_data = {object_id: object_value.to_dict() for object_id, object_value in library.objects_by_id.items()}
    changed_object_ids: set[str] = set()

    for decision in accepted:
        target_id = normalize_id(str(decision.candidate.get("target_object_id") or ""))
        target = after_data.get(target_id)
        if target is None:
            raise ValueError(f"accepted candidate target disappeared: {target_id}")
        if decision.normalized_evidence_item is not None:
            child_field = "evidence_items"
            child = decision.normalized_evidence_item
        elif decision.normalized_claim is not None:
            child_field = "claims"
            child = decision.normalized_claim
        else:
            raise ValueError(f"accepted candidate has no normalized child: {target_id}")

        target[child_field] = [
            *[dict(_mapping(item)) for item in _sequence(target.get(child_field))],
            dict(child),
        ]
        target["sources"] = _merge_candidate_sources(
            _sequence(target.get("sources")),
            _candidate_sources(decision.candidate),
            target_id=target_id,
        )
        changed_object_ids.add(target_id)

    source_paths = {
        object_id: path
        for object_id in after_data
        if (path := library.source_path_for(object_id)) is not None
    }
    try:
        after_objects = [
            validate_object(after_data[object_id], path=source_paths.get(object_id))
            for object_id in sorted(after_data)
        ]
        validate_library(
            after_objects,
            manifest=library.manifest,
            source_paths=source_paths,
        )
    except Exception as exc:  # noqa: BLE001 - preserve fail-closed transaction boundary
        raise ValueError(f"candidate queue fails final CKL validation: {exc}") from exc

    changed = changed_references(before_objects, after_objects)
    chapters = changed_chapter_references(before_objects, after_objects)
    if write:
        for object_id in sorted(changed_object_ids):
            path = source_paths.get(object_id)
            if path is None:
                raise ValueError(f"no writable source path for accepted candidate target: {object_id}")
            _write_json_atomically(path, after_data[object_id])

    return CandidateApplication(
        decisions=decisions,
        changed_object_ids=sorted(changed_object_ids),
        changed_references=changed,
        changed_chapters=chapters,
        wrote=write,
    )


def _write_json_atomically(path: Path, value: Mapping[str, Any]) -> None:
    """Replace one already-resolved CKL object after all validation succeeds."""

    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(value, indent=2, ensure_ascii=True) + "\n")
        temp_path.replace(path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def changed_references(
    before: Iterable[CanonicalObject | Mapping[str, Any]],
    after: Iterable[CanonicalObject | Mapping[str, Any]],
) -> list[str]:
    """Return only Scripture anchors affected by changed parent/child records."""

    before_map = _object_map(before)
    after_map = _object_map(after)
    changed: set[str] = set()
    for object_id in sorted(set(before_map) | set(after_map)):
        old = before_map.get(object_id)
        new = after_map.get(object_id)
        if old is None or new is None:
            changed.update(_object_anchors(new or old))
            continue

        old_children = _children_by_id(old)
        new_children = _children_by_id(new)
        for child_id in sorted(set(old_children) | set(new_children)):
            if old_children.get(child_id) == new_children.get(child_id):
                continue
            changed.update(_child_anchors(old_children.get(child_id) or {}))
            changed.update(_child_anchors(new_children.get(child_id) or {}))
        if _parent_without_children(old) != _parent_without_children(new):
            changed.update(_parent_change_anchors(old, new))
    return _canonical_anchor_strings(changed)


def changed_chapter_references(
    before: Iterable[CanonicalObject | Mapping[str, Any]],
    after: Iterable[CanonicalObject | Mapping[str, Any]],
) -> list[str]:
    """Expand changed anchors to deterministic chapter references."""

    lookup = build_book_alias_lookup(())
    chapters: set[str] = set()
    for reference in changed_references(before, after):
        for span in parse_scripture_references(reference, book_alias_lookup=lookup):
            if span.start_chapter is None:
                chapters.add(format_scripture_reference(span))
                continue
            end = span.end_chapter or span.start_chapter
            for chapter in range(span.start_chapter, end + 1):
                chapters.add(f"{span.book} {chapter}")
    return sorted(chapters)


def selective_recompile(
    references: Iterable[str],
    *,
    chapter_preparer: Any | None = None,
    bundle_builder: Any | None = None,
    synthesis_compiler: Any | None = None,
    study_db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Rebuild requested v1.2 evidence/synthesis identities without writing prose."""

    from framework.commentary.v12_config import V12_PIPELINE_VERSION

    identities: dict[str, tuple[str, int]] = {}
    for value in references:
        raw = str(value).strip()
        if not raw:
            continue
        book, chapter = _chapter_identity(raw)
        identities[f"{book} {chapter}"] = (book, chapter)

    if bundle_builder is not None or synthesis_compiler is not None:
        raise ValueError(
            "legacy bundle_builder/synthesis_compiler hooks cannot certify Commentary v1.2 inputs"
        )

    preparer = chapter_preparer
    if preparer is None:
        from framework.commentary.production.inputs import prepare_chapter

        def prepare_current_v12(book: str, chapter: int) -> Any:
            return prepare_chapter(
                book,
                chapter,
                study_db_path=study_db_path,
                read_only_inputs=True,
            )

        preparer = prepare_current_v12

    results: list[dict[str, Any]] = []
    for reference in sorted(identities):
        book, chapter = identities[reference]
        prepared = preparer(book, chapter)
        if prepared is None or not hasattr(prepared, "bundle") or not hasattr(prepared, "synthesis"):
            raise ValueError(f"prepared chapter is required for {reference}")
        bundle = prepared.bundle
        synthesis = prepared.synthesis
        _validate_v12_prepared_identity(reference, book, chapter, bundle, synthesis)
        from bhf_agent.chapter_commentary.synthesis import validate_synthesis

        errors = validate_synthesis(synthesis, bundle)
        if errors:
            raise ValueError(
                f"v1.2 synthesis validation failed for {reference}: {'; '.join(errors)}"
            )

        synthesis_value = synthesis.to_dict() if hasattr(synthesis, "to_dict") else (
            dict(synthesis) if isinstance(synthesis, Mapping) else {}
        )
        bundle_value = bundle.to_dict() if hasattr(bundle, "to_dict") else (
            dict(bundle) if isinstance(bundle, Mapping) else {}
        )
        result = {
            "reference": reference,
            "pipeline": V12_PIPELINE_VERSION,
            "operation": "evidence-synthesis-only",
        }
        for key, value in (
            ("evidence_bundle_version", getattr(bundle, "version", bundle_value.get("version"))),
            ("evidence_hash", getattr(bundle, "evidence_hash", bundle_value.get("evidence_hash"))),
            ("synthesis_schema_version", getattr(synthesis, "synthesis_schema_version", synthesis_value.get("synthesis_schema_version"))),
            ("synthesis_compiler_version", getattr(synthesis, "synthesis_compiler_version", synthesis_value.get("synthesis_compiler_version"))),
            ("synthesis_hash", getattr(synthesis, "synthesis_hash", synthesis_value.get("synthesis_hash"))),
            ("evidence_availability", getattr(synthesis, "evidence_availability", synthesis_value.get("evidence_availability"))),
        ):
            if value not in (None, ""):
                result[key] = value
        units = getattr(synthesis, "synthesis_units", synthesis_value.get("synthesis_units"))
        if units is not None:
            result["synthesis_unit_count"] = len(units)
        results.append(result)
    return results


def _validate_v12_prepared_identity(
    reference: str,
    book: str,
    chapter: int,
    bundle: Any,
    synthesis: Any,
) -> None:
    """Reject fixtures or alternate compilers that impersonate v1.2 output."""

    from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION

    bundle_version = getattr(bundle, "version", None)
    bundle_reference = getattr(bundle, "passage_ref", None)
    if bundle_version != EVIDENCE_BUNDLE_CANDIDATE_VERSION:
        raise ValueError(
            f"current v1.2 evidence bundle required for {reference}: {bundle_version!r}"
        )
    try:
        bundle_identity = _chapter_identity(str(bundle_reference or ""))
    except ValueError as exc:
        raise ValueError(f"bundle identity mismatch for {reference}") from exc
    if bundle_identity != (book, chapter):
        raise ValueError(f"bundle identity mismatch for {reference}: {bundle_reference}")

    synthesis_identity = (
        getattr(synthesis, "book", None),
        getattr(synthesis, "chapter", None),
    )
    if synthesis_identity != (book, chapter):
        raise ValueError(
            f"synthesis identity mismatch for {reference}: {synthesis_identity!r}"
        )
    if getattr(synthesis, "evidence_bundle_version", None) != bundle_version:
        raise ValueError(f"synthesis bundle version mismatch for {reference}")


def _validate_merged_target(
    target: Any,
    child: Mapping[str, Any],
    candidate_sources: Sequence[Mapping[str, Any]],
    *,
    library: Any,
    child_field: str,
) -> dict[str, Any] | None:
    raw = _mapping(target)
    merged = dict(raw)
    merged_children = [dict(_mapping(item)) for item in _sequence(raw.get(child_field))]
    merged_children.append(dict(child))
    merged[child_field] = merged_children
    merged["sources"] = _merge_candidate_sources(
        _sequence(raw.get("sources")),
        candidate_sources,
        target_id=str(raw.get("id") or ""),
    )
    try:
        validated = validate_object(merged)
        # Re-run library-level referential checks with the merged target in
        # the complete loaded library.  Validating the target in isolation
        # would incorrectly reject legitimate references to sibling objects.
        objects = _library_objects(library)
        if objects:
            target_id = normalize_id(str(merged.get("id") or ""))
            objects = [
                validated if normalize_id(str(_mapping(item).get("id") or "")) == target_id else item
                for item in objects
            ]
            validate_library(objects)
        else:
            validate_library([validated])
    except Exception:  # noqa: BLE001 - adapter turns validator details into a gate reason
        return None
    return dict(child)


def _library_objects(library: Any) -> list[Any]:
    objects = getattr(library, "objects_by_id", {})
    if isinstance(objects, Mapping):
        return list(objects.values())
    list_by_type = getattr(library, "list_by_type", None)
    if callable(list_by_type):
        result: list[Any] = []
        for object_type in ("book", "event", "group", "institution", "place", "person", "theme"):
            result.extend(list_by_type(object_type))
        return result
    return []


def _get_object(library: Any, object_id: str) -> Any | None:
    getter = getattr(library, "get_by_id", None)
    if callable(getter):
        return getter(object_id)
    objects = getattr(library, "objects_by_id", {})
    return objects.get(object_id)


def _candidate_sources(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Read the legacy single source and the multi-source candidate form."""

    values: list[dict[str, Any]] = []
    for raw in (candidate.get("source"), *_sequence(candidate.get("source_records"))):
        source = _mapping(raw)
        if source.get("id"):
            values.append(dict(source))
    by_id: dict[str, dict[str, Any]] = {}
    for source in values:
        source_id = normalize_id(str(source["id"]))
        existing = by_id.get(source_id)
        if existing is not None and existing != source:
            raise ValueError(f"candidate contains conflicting source declarations: {source_id}")
        by_id[source_id] = source
    return [by_id[source_id] for source_id in sorted(by_id)]


def _merge_candidate_sources(
    existing: Sequence[Any],
    candidates: Sequence[Mapping[str, Any]],
    *,
    target_id: str,
) -> list[dict[str, Any]]:
    merged = [dict(_mapping(item)) for item in existing]
    by_id = {
        normalize_id(str(item.get("id") or "")): item
        for item in merged
        if item.get("id")
    }
    for source in candidates:
        source_id = normalize_id(str(source.get("id") or ""))
        if not source_id:
            continue
        existing_source = by_id.get(source_id)
        if existing_source is not None:
            if not _sources_equivalent(existing_source, source):
                raise ValueError(f"candidate source conflicts with existing source: {target_id}:{source_id}")
            continue
        value = dict(source)
        merged.append(value)
        by_id[source_id] = value
    return merged


def _sources_equivalent(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    """Compare source records after CKL's normal default expansion."""

    try:
        return validate_source_entry(left).to_dict() == validate_source_entry(right).to_dict()
    except Exception:  # noqa: BLE001 - the regular object validator reports malformed sources
        return left == right


def _object_map(values: Iterable[CanonicalObject | Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for value in values:
        raw = _mapping(value)
        object_id = normalize_id(str(raw.get("id") or ""))
        if object_id:
            result[object_id] = raw
    return result


def _children_by_id(value: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for field_name in ("claims", "evidence_items"):
        for child in _sequence(value.get(field_name)):
            raw = _mapping(child)
            child_id = normalize_id(str(raw.get("id") or ""))
            if child_id:
                result[f"{field_name}:{child_id}"] = raw
    for index, child in enumerate(_sequence(value.get("interpretive_notes"))):
        raw = _mapping(child)
        if raw:
            result[f"interpretive_notes:{index}"] = raw
    return result


def _parent_without_children(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value[key]
        for key in sorted(value)
        if key not in {"claims", "evidence_items", "interpretive_notes"}
    }


def _parent_change_anchors(
    old: Mapping[str, Any],
    new: Mapping[str, Any],
) -> list[str]:
    """Return anchors whose EvidenceBundle projection a parent change affects."""

    changed: set[str] = set()
    old_direct = set(_claim_anchors(old))
    new_direct = set(_claim_anchors(new))
    old_children = list(_children_by_id(old).values())
    new_children = list(_children_by_id(new).values())
    structured_children = [*old_children, *new_children]

    old_parent = _parent_without_children(old)
    new_parent = _parent_without_children(new)
    changed_fields = {
        key
        for key in set(old_parent) | set(new_parent)
        if old_parent.get(key) != new_parent.get(key)
    }

    # A directly anchored parent projects its own content and existing source
    # provenance.  Adding a source solely for a newly added child leaves that
    # parent projection unchanged; a modification/removal of an existing
    # source remains relevant to the parent anchor.
    non_source_changed_fields = changed_fields - {"sources"}
    source_changes_parent_projection = (
        "sources" in changed_fields
        and bool(_modified_source_ids(old.get("sources"), new.get("sources")))
    )
    if non_source_changed_fields or source_changes_parent_projection:
        changed.update(old_direct)
        changed.update(new_direct)

    if changed_fields.intersection(_PARENT_FIELDS_PROJECTED_WITH_CHILDREN):
        for child in structured_children:
            changed.update(_child_anchors(child))

    if "sources" in changed_fields:
        source_ids = _changed_source_ids(old.get("sources"), new.get("sources"))
        modified_source_ids = _modified_source_ids(old.get("sources"), new.get("sources"))
        for child in structured_children:
            child_sources = set(_string_list(child.get("source_ids")))
            # A child with an explicit source consumes that source.  A
            # source-less legacy child inherits its existing parent source,
            # so an edit to that source can change it.  Adding a distinct
            # source cannot rewrite the inherited evidence and must not fan
            # out to every old child of this object.
            if child_sources.intersection(source_ids) or (
                not child_sources and modified_source_ids
            ):
                changed.update(_child_anchors(child))

    # Legacy parents without structured children can project their own fields,
    # but only through their direct anchors (already added above).
    return list(changed)


def _changed_source_ids(old: Any, new: Any) -> set[str]:
    old_map = {
        normalize_id(str(_mapping(item).get("id") or "")): _mapping(item)
        for item in _sequence(old)
        if _mapping(item).get("id")
    }
    new_map = {
        normalize_id(str(_mapping(item).get("id") or "")): _mapping(item)
        for item in _sequence(new)
        if _mapping(item).get("id")
    }
    return {
        source_id
        for source_id in set(old_map) | set(new_map)
        if old_map.get(source_id) != new_map.get(source_id)
    }


def _modified_source_ids(old: Any, new: Any) -> set[str]:
    """Return only source IDs present in both versions whose record changed."""

    old_map = {
        normalize_id(str(_mapping(item).get("id") or "")): _mapping(item)
        for item in _sequence(old)
        if _mapping(item).get("id")
    }
    new_map = {
        normalize_id(str(_mapping(item).get("id") or "")): _mapping(item)
        for item in _sequence(new)
        if _mapping(item).get("id")
    }
    return {
        source_id
        for source_id in set(old_map).intersection(new_map)
        if old_map[source_id] != new_map[source_id]
    }


def _object_anchors(value: Mapping[str, Any] | None) -> list[str]:
    raw = value or {}
    anchors = _claim_anchors(raw)
    for field_name in ("claims", "evidence_items"):
        for child in _sequence(raw.get(field_name)):
            anchors.extend(_child_anchors(_mapping(child)))
    return list(dict.fromkeys(anchors))


def _child_anchors(value: Mapping[str, Any]) -> list[str]:
    return _claim_anchors(value, evidence="evidence_type" in value)


def _claim_anchors(value: Mapping[str, Any], evidence: bool = False) -> list[str]:
    raw = value.get("scripture_references") or []
    result: list[str] = []
    for item in _sequence(raw):
        if isinstance(item, Mapping):
            result.append(str(item.get("reference") or "").strip())
        else:
            result.append(str(item or "").strip())
    return [item for item in result if item]


def _canonical_anchor_strings(values: Iterable[str]) -> list[str]:
    lookup = build_book_alias_lookup(())
    result: set[str] = set()
    for value in values:
        parsed = parse_scripture_references(str(value), book_alias_lookup=lookup)
        if parsed:
            result.update(format_scripture_reference(item) for item in parsed)
    return sorted(result)


def _anchors_overlap(passage_reference: str, anchors: Sequence[str]) -> bool:
    lookup = build_book_alias_lookup(())
    query_values = parse_scripture_references(passage_reference, book_alias_lookup=lookup)
    if not query_values:
        return False
    return any(
        scripture_reference_overlaps(query, candidate)
        for anchor in anchors
        for candidate in parse_scripture_references(anchor, book_alias_lookup=lookup)
        for query in query_values
    )


def _parseable(anchors: Sequence[str]) -> bool:
    lookup = build_book_alias_lookup(())
    return all(parse_scripture_references(anchor, book_alias_lookup=lookup) for anchor in anchors)


def _semantic_duplicate(target: Any, claim: Mapping[str, Any]) -> bool:
    candidate = semantic_claim_fingerprint(
        claim.get("claim") or claim.get("description") or claim.get("primary_observation"),
        claim.get("claim_type") or claim.get("evidence_type"),
    )
    if not candidate:
        return False
    for field_name in ("claims", "evidence_items"):
        for item in _sequence(_value(target, field_name)):
            raw = _mapping(item)
            text = raw.get("claim") or raw.get("description") or raw.get("primary_observation")
            fingerprint = semantic_claim_fingerprint(
                text,
                raw.get("claim_type") or raw.get("evidence_type"),
            )
            if fingerprint == candidate:
                return True
    return False


def _object_sources(value: Any) -> dict[str, Mapping[str, Any]]:
    return {
        normalize_id(str(_value(item, "id"))): _mapping(item)
        for item in _sequence(_value(value, "sources"))
        if _value(item, "id")
    }


def _value(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return {}


def _sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in _sequence(value) if str(item).strip()]


__all__ = [
    "CandidateApplication",
    "CandidateValidation",
    "apply_candidate_queue",
    "changed_chapter_references",
    "changed_references",
    "selective_recompile",
    "validate_candidate",
    "validate_candidates",
]


def _chapter_identity(reference: str) -> tuple[str, int]:
    lookup = build_book_alias_lookup(())
    parsed = parse_scripture_references(reference, book_alias_lookup=lookup)
    if (
        len(parsed) != 1
        or parsed[0].start_chapter is None
        or (parsed[0].end_chapter or parsed[0].start_chapter) != parsed[0].start_chapter
    ):
        raise ValueError(f"reference must identify a single canonical chapter: {reference}")
    return parsed[0].book, parsed[0].start_chapter
