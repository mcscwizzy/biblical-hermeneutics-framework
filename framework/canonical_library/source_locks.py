"""Validation for non-mutating, claim-level geography source-lock queues.

The queue is deliberately upstream of CKL expansion candidates.  It records
what a source actually supports, how it is located, and whether entity work
would still be required before a candidate can be produced.  Keeping this
validation separate makes a missing source lock fail before any CKL object is
considered for mutation.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


_STATUSES = frozenset({"LOCKED", "CONFLICTED", "UNRESOLVED", "REJECTED"})
_TEMPORAL_RELATIONSHIPS = frozenset(
    {
        "territory-of",
        "region-of",
        "part-of",
        "controlled-by",
        "political-context",
        "administrative-context",
        "territorial-inheritance",
        "located-in",
        "ruled-by",
    }
)
_KEBAB_CASE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SourceLockValidationError(ValueError):
    """Raised when a queue would treat an untraceable fact as source-locked."""


@dataclass(frozen=True)
class SourceLockValidationReport:
    chapter_count: int
    source_count: int
    claim_count: int
    status_counts: dict[str, int]
    relationship_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_count": self.chapter_count,
            "source_count": self.source_count,
            "claim_count": self.claim_count,
            "status_counts": dict(self.status_counts),
            "relationship_counts": dict(self.relationship_counts),
        }


def validate_source_lock_queue(payload: Mapping[str, Any]) -> SourceLockValidationReport:
    """Validate a source-lock queue without reading or writing CKL objects.

    ``LOCKED`` is intentionally strict: a claim needs a registered source,
    claim-specific locator, direct passage eligibility, a confidence statement,
    provenance that does not name a model as its source, and safe temporal
    scope where the relationship is historically variable.  Other statuses
    retain their research outcome without masquerading as ready evidence.
    """

    if not isinstance(payload, Mapping):
        raise SourceLockValidationError("source-lock queue must be an object")
    if str(payload.get("schema_version") or "") != "1.0":
        raise SourceLockValidationError("source-lock queue requires schema_version 1.0")
    if not _nonempty(payload.get("queue_id")):
        raise SourceLockValidationError("source-lock queue requires queue_id")

    approved = _string_list(payload.get("approved_pilot_references"), "approved_pilot_references")
    if not approved or len(set(approved)) != len(approved):
        raise SourceLockValidationError("approved_pilot_references must be non-empty and unique")

    sources = _mapping_list(payload.get("sources"), "sources")
    source_index: dict[str, Mapping[str, Any]] = {}
    for source in sources:
        source_id = _nonempty(source.get("id"))
        if not source_id:
            raise SourceLockValidationError("each source requires id")
        if source_id in source_index:
            raise SourceLockValidationError(f"duplicate source id: {source_id}")
        for field in ("title", "source_type", "registry_status", "locator"):
            if not _nonempty(source.get(field)):
                raise SourceLockValidationError(f"source {source_id} requires {field}")
        provenance = source.get("provenance")
        if not isinstance(provenance, Mapping):
            raise SourceLockValidationError(f"source {source_id} requires provenance")
        if _contains_model_as_source(provenance):
            raise SourceLockValidationError(f"source {source_id} cannot name a model as its source")
        source_index[source_id] = source

    chapters = _mapping_list(payload.get("chapters"), "chapters")
    chapter_refs: list[str] = []
    claim_ids: set[str] = set()
    claim_fingerprints: set[tuple[str, str, str, str, tuple[str, ...]]] = set()
    status_counts: Counter[str] = Counter()
    relationship_counts: Counter[str] = Counter()

    for chapter in chapters:
        reference = _nonempty(chapter.get("reference"))
        if not reference:
            raise SourceLockValidationError("each chapter requires reference")
        chapter_refs.append(reference)
        if reference not in approved:
            raise SourceLockValidationError(f"chapter {reference} is outside the approved pilot")
        if not _nonempty(chapter.get("classification_before")):
            raise SourceLockValidationError(f"chapter {reference} requires classification_before")
        if not _nonempty(chapter.get("geography_gap")):
            raise SourceLockValidationError(f"chapter {reference} requires geography_gap")
        generation = _nonempty(chapter.get("candidate_generation"))
        if generation not in {"eligible", "withheld", "no-write"}:
            raise SourceLockValidationError(f"chapter {reference} has invalid candidate_generation")

        claims = _mapping_list(chapter.get("claims"), f"claims for {reference}")
        if not claims:
            raise SourceLockValidationError(f"chapter {reference} requires an explicit source-lock outcome")
        for claim in claims:
            claim_id = _nonempty(claim.get("id"))
            if not claim_id:
                raise SourceLockValidationError(f"chapter {reference} has a claim without id")
            if claim_id in claim_ids:
                raise SourceLockValidationError(f"duplicate claim id: {claim_id}")
            claim_ids.add(claim_id)

            status = _nonempty(claim.get("status"))
            if status not in _STATUSES:
                raise SourceLockValidationError(f"claim {claim_id} has invalid status {status!r}")
            status_counts[status] += 1
            if generation == "no-write" and (
                status in {"LOCKED", "CONFLICTED"}
                or _nonempty(claim.get("candidate_readiness")).startswith("ready-")
            ):
                raise SourceLockValidationError(f"no-write chapter {reference} cannot have a candidate-ready claim")
            if generation == "withheld" and _nonempty(claim.get("candidate_readiness")).startswith("ready-"):
                raise SourceLockValidationError(f"withheld chapter {reference} has a candidate-ready claim")

            subject = _entity(claim.get("subject"), "subject", claim_id)
            target = _entity(claim.get("target"), "target", claim_id)
            relationship = _nonempty(claim.get("relationship_type"))
            if not relationship or not _KEBAB_CASE.fullmatch(relationship):
                raise SourceLockValidationError(f"claim {claim_id} relationship_type must be kebab-case")
            relationship_counts[relationship] += 1
            anchors = _anchors(claim.get("scripture_anchors"), claim_id, reference)
            temporal_scope = claim.get("temporal_scope")
            if relationship in _TEMPORAL_RELATIONSHIPS and not _has_temporal_scope(temporal_scope):
                raise SourceLockValidationError(
                    f"claim {claim_id} requires temporal scope for {relationship}"
                )

            if status in {"LOCKED", "CONFLICTED"}:
                if _is_ambiguous_entity(subject) or _is_ambiguous_entity(target):
                    raise SourceLockValidationError(
                        f"claim {claim_id} has ambiguous same-name entity resolution"
                    )
                locks = _mapping_list(claim.get("source_locks"), f"source_locks for {claim_id}")
                if not locks:
                    raise SourceLockValidationError(f"claim {claim_id} is {status} without source locks")
                if status == "CONFLICTED" and len(locks) < 2:
                    raise SourceLockValidationError(
                        f"claim {claim_id} is CONFLICTED but has fewer than two source locks"
                    )
                if status == "CONFLICTED":
                    alternatives = _mapping_list(
                        claim.get("alternatives", []), f"alternatives for {claim_id}"
                    )
                    identities = []
                    for alternative in alternatives:
                        identities.append(_entity_identity(_entity(alternative.get("target"), "alternative target", claim_id)))
                        supporting = _mapping_list(
                            alternative.get("source_locks", []),
                            f"alternative source_locks for {claim_id}",
                        )
                        if not supporting or any(
                            lock not in locks for lock in supporting
                        ):
                            raise SourceLockValidationError(
                                f"claim {claim_id} alternatives need their own registered source locks"
                            )
                    if len(set(identities)) < 2:
                        raise SourceLockValidationError(
                            f"claim {claim_id} requires distinct source-backed alternatives"
                        )
                for lock in locks:
                    source_id = _nonempty(lock.get("source_id"))
                    if source_id not in source_index:
                        raise SourceLockValidationError(
                            f"claim {claim_id} references unknown source {source_id!r}"
                        )
                    if not _nonempty(lock.get("locator")):
                        raise SourceLockValidationError(f"claim {claim_id} source lock requires locator")
                    if not _nonempty(lock.get("support_type")):
                        raise SourceLockValidationError(
                            f"claim {claim_id} source lock requires support_type"
                        )
                    if source_index[source_id]["source_type"] == "scripture":
                        locator_verses = _scripture_locator_verses(_nonempty(lock["locator"]), reference)
                        if not locator_verses:
                            raise SourceLockValidationError(
                                f"claim {claim_id} Scripture locator must identify verses in {reference}"
                            )
                        overlaps = [
                            bool(locator_verses.intersection(
                                _scripture_locator_verses(_nonempty(anchor["reference"]), reference)
                            ))
                            for anchor in anchors
                        ]
                        if (status == "LOCKED" and not all(overlaps)) or (
                            status == "CONFLICTED" and not any(overlaps)
                        ):
                            raise SourceLockValidationError(
                                f"claim {claim_id} Scripture locator must overlap its anchor"
                            )
                if not any(
                    source_index[_nonempty(lock.get("source_id"))]["source_type"]
                    not in {"external-dataset"}
                    and not _nonempty(lock.get("support_type")).startswith("entity-identification")
                    for lock in locks
                ):
                    raise SourceLockValidationError(
                        f"claim {claim_id} needs a substantive Scripture or reviewed source lock"
                    )
                confidence = claim.get("confidence")
                if not isinstance(confidence, Mapping) or not _nonempty(confidence.get("level")):
                    raise SourceLockValidationError(f"claim {claim_id} requires confidence")
                if _nonempty(confidence.get("level")) not in {"high", "moderate", "low"}:
                    raise SourceLockValidationError(f"claim {claim_id} has invalid confidence level")
                if not _nonempty(confidence.get("rationale")):
                    raise SourceLockValidationError(f"claim {claim_id} requires confidence rationale")
                if not _nonempty(claim.get("material_relevance")):
                    raise SourceLockValidationError(f"claim {claim_id} requires material_relevance")
                provenance = claim.get("provenance")
                if not isinstance(provenance, Mapping) or _contains_model_as_source(provenance):
                    raise SourceLockValidationError(
                        f"claim {claim_id} requires non-model provenance metadata"
                    )

                fingerprint = (
                    reference,
                    _entity_identity(subject),
                    relationship,
                    _entity_identity(target),
                    tuple(sorted(anchor["reference"] for anchor in anchors)),
                )
                if fingerprint in claim_fingerprints:
                    raise SourceLockValidationError(f"duplicate semantic source-lock claim: {claim_id}")
                claim_fingerprints.add(fingerprint)

            if status in {"UNRESOLVED", "REJECTED"} and not _nonempty(claim.get("disposition_reason")):
                raise SourceLockValidationError(
                    f"claim {claim_id} with status {status} requires disposition_reason"
                )

        if generation == "eligible" and not any(
            claim.get("status") == "LOCKED" for claim in claims
        ):
            raise SourceLockValidationError(
                f"chapter {reference} requires a locked minimum for candidate generation"
            )

    if len(set(chapter_refs)) != len(chapter_refs):
        raise SourceLockValidationError("duplicate chapter reference")
    if set(chapter_refs) != set(approved):
        raise SourceLockValidationError("chapters must exactly match approved_pilot_references")

    return SourceLockValidationReport(
        chapter_count=len(chapters),
        source_count=len(sources),
        claim_count=sum(status_counts.values()),
        status_counts=dict(sorted(status_counts.items())),
        relationship_counts=dict(sorted(relationship_counts.items())),
    )


def validate_source_lock_queue_against_repository(
    payload: Mapping[str, Any],
    *,
    root: Path,
) -> SourceLockValidationReport:
    """Resolve declared local source and OpenBible record identities read-only.

    Structural validation intentionally does not depend on a checkout.  This
    companion check proves that a queue's assertions about reusing BHF source
    records are true for the repository supplied to it.  It never alters the
    source registry, CKL inventory, OpenBible import, or Commentary artifacts.
    """

    report = validate_source_lock_queue(payload)
    root = Path(root).resolve()
    source_index = {
        _nonempty(source.get("id")): source
        for source in _mapping_list(payload.get("sources"), "sources")
    }
    openbible_rows: dict[str, Mapping[str, Any]] | None = None

    for source in source_index.values():
        provenance = source["provenance"]
        source_path = _local_path(root, _nonempty(provenance.get("record_path")))
        registry_status = _nonempty(source.get("registry_status"))
        if registry_status == "existing-ckl-object-source":
            if not source_path.is_file():
                raise SourceLockValidationError(f"source record path does not exist: {source_path}")
            try:
                record = json.loads(source_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise SourceLockValidationError(f"source record is not valid JSON: {source_path}") from exc
            object_id = _nonempty(provenance.get("record_object_id"))
            source_id = _nonempty(provenance.get("record_source_id"))
            if record.get("id") != object_id:
                raise SourceLockValidationError(
                    f"source record object id mismatch for {source['id']}: {object_id!r}"
                )
            known = {
                _nonempty(item.get("id"))
                for item in record.get("sources", [])
                if isinstance(item, Mapping)
            }
            if source_id not in known:
                raise SourceLockValidationError(
                    f"source id {source_id!r} is not present in {source_path}"
                )
        elif registry_status == "existing-repository-dataset":
            if not source_path.is_file():
                raise SourceLockValidationError(f"repository dataset path does not exist: {source_path}")
            try:
                dataset = json.loads(source_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise SourceLockValidationError(f"repository dataset is not valid JSON: {source_path}") from exc
            if not isinstance(dataset, list):
                raise SourceLockValidationError(f"repository dataset must be a list: {source_path}")
            openbible_rows = {
                _nonempty(item.get("id")): item
                for item in dataset
                if isinstance(item, Mapping)
            }

    if openbible_rows is not None:
        for chapter in _mapping_list(payload.get("chapters"), "chapters"):
            for claim in _mapping_list(chapter.get("claims"), "claims"):
                for lock in _mapping_list(claim.get("source_locks", []), "source_locks"):
                    if _nonempty(lock.get("source_id")) != "openbible-geocoding-data":
                        continue
                    ids = set(re.findall(r"\bopenbible-[a-z0-9]+\b", _nonempty(lock.get("locator"))))
                    if not ids:
                        raise SourceLockValidationError(
                            f"OpenBible source lock on {claim.get('id')} requires an imported record id"
                        )
                    missing = sorted(ids - openbible_rows.keys())
                    if missing:
                        raise SourceLockValidationError(
                            f"OpenBible record(s) not present for {claim.get('id')}: {', '.join(missing)}"
                        )
                    if _nonempty(lock.get("support_type")) == "entity-identification-and-occurrence":
                        for record_id in ids:
                            references = openbible_rows[record_id].get("references", [])
                            if not any(
                                _openbible_reference_matches_anchor(item, anchor)
                                for item in references
                                for anchor in claim["scripture_anchors"]
                            ):
                                raise SourceLockValidationError(
                                    f"OpenBible record {record_id} has no anchor occurrence for {claim.get('id')}"
                                )

    return report


def _nonempty(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SourceLockValidationError(f"{label} must be a list")
    values = [_nonempty(item) for item in value]
    if any(not item for item in values):
        raise SourceLockValidationError(f"{label} must contain only non-empty strings")
    return values


def _mapping_list(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SourceLockValidationError(f"{label} must be a list")
    if any(not isinstance(item, Mapping) for item in value):
        raise SourceLockValidationError(f"{label} must contain only objects")
    return list(value)


def _entity(value: Any, label: str, claim_id: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SourceLockValidationError(f"claim {claim_id} requires {label} entity")
    for field in ("label", "entity_type", "resolution"):
        if not _nonempty(value.get(field)):
            raise SourceLockValidationError(f"claim {claim_id} {label} requires {field}")
    return value


def _anchors(value: Any, claim_id: str, chapter_reference: str) -> list[Mapping[str, str]]:
    anchors = _mapping_list(value, f"scripture_anchors for {claim_id}")
    if not anchors:
        raise SourceLockValidationError(f"claim {claim_id} requires Scripture anchor")
    for anchor in anchors:
        reference = _nonempty(anchor.get("reference"))
        if not reference:
            raise SourceLockValidationError(f"claim {claim_id} Scripture anchor requires reference")
        if not _scripture_locator_verses(reference, chapter_reference):
            raise SourceLockValidationError(
                f"claim {claim_id} has chapter-ineligible or malformed Scripture anchor {reference}"
            )
        if _nonempty(anchor.get("eligibility")) not in {"direct", "contextual", "disputed"}:
            raise SourceLockValidationError(
                f"claim {claim_id} Scripture anchor requires known eligibility"
            )
    return anchors


def _scripture_locator_verses(locator: str, chapter_reference: str) -> set[int]:
    match = re.fullmatch(rf"{re.escape(chapter_reference)}:(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)", locator)
    if not match:
        return set()
    verses: set[int] = set()
    for part in match.group(1).split(","):
        ends = [int(value) for value in part.strip().split("-")]
        start, end = (ends[0], ends[0]) if len(ends) == 1 else ends
        if start < 1 or end < start:
            return set()
        verses.update(range(start, end + 1))
    return verses


def _openbible_reference_matches_anchor(reference: Any, anchor: Mapping[str, Any]) -> bool:
    if not isinstance(reference, Mapping):
        return False
    anchor_match = re.fullmatch(r"(.+?) (\d+):(\d+)(?:-(\d+))?", _nonempty(anchor.get("reference")))
    if anchor_match is None:
        return False
    book, chapter, start, end = anchor_match.groups()
    return (
        reference.get("book") == book
        and reference.get("chapter") == int(chapter)
        and int(reference.get("verse_start") or 0) <= int(end or start)
        and int(reference.get("verse_end") or 0) >= int(start)
    )


def _has_temporal_scope(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(_nonempty(item) for item in value.values() if isinstance(item, str)) or any(
        bool(item) for item in value.values() if not isinstance(item, str)
    )


def _is_ambiguous_entity(entity: Mapping[str, Any]) -> bool:
    resolution = _nonempty(entity.get("resolution")).lower()
    return "ambiguous" in resolution or "person-place" in resolution


def _entity_identity(entity: Mapping[str, Any]) -> str:
    return _nonempty(entity.get("entity_id")) or _nonempty(entity.get("label")).lower()


def _contains_model_as_source(value: Mapping[str, Any]) -> bool:
    for key, item in value.items():
        if "source" in str(key).lower() and "model" in str(item).lower():
            return True
    return False


def _local_path(root: Path, relative_path: str) -> Path:
    if not relative_path:
        raise SourceLockValidationError("local source provenance requires record_path")
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SourceLockValidationError(f"source record path leaves repository: {relative_path}") from exc
    return candidate


__all__ = [
    "SourceLockValidationError",
    "SourceLockValidationReport",
    "validate_source_lock_queue",
    "validate_source_lock_queue_against_repository",
]
