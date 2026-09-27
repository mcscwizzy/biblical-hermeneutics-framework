"""Shared validation and change tracking for CKL evidence expansion.

Expansion candidates are intentionally data-only.  This adapter validates the
candidate against the same object/library validators used by CKL authoring,
then applies the existing Scripture-anchor and provenance rules before any
caller is allowed to write a record.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from .evidence_models import CanonicalEvidenceItem, EvidenceValidationError
from .normalization import normalize_alias, normalize_id
from .schema import (
    CATEGORY_FOLDERS,
    CanonicalObject,
    validate_library,
    validate_object,
    validate_source_entry,
)
from .semantic_deduplication import evidence_structural_fingerprint, semantic_claim_fingerprint
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
    classification: str = "new"
    survivor_evidence_id: str = ""
    contributing_source_ids: list[str] = field(default_factory=list)
    provenance_conflicts: list[dict[str, Any]] = field(default_factory=list)

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
    simulated_objects: dict[str, dict[str, Any]] = field(default_factory=dict)

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


class CanonicalStructuralDuplicateConflict(ValueError):
    """Multiple loaded canonical evidence items share one typed structure."""


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
        typed_entitlement = evidence and any(
            _mapping(item).get("kind") == "value"
            and _mapping(item).get("relationship") in {"territorial-inheritance", "tithe-as-inheritance"}
            and _mapping(item).get("value_type") == "entitlement"
            for item in _sequence(evidence_item.get("evidence_targets"))
        )
        if _value(target, "type") not in allowed_types and not (
            _value(target, "type") == "institution" and typed_entitlement
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
    provenance_conflicts: list[dict[str, Any]] = []
    try:
        candidate_sources = _candidate_sources(payload)
    except ValueError:
        candidate_sources = []
        reasons.append("provenance-conflict")
    for candidate_source in candidate_sources:
        source_id = normalize_id(str(candidate_source["id"]))
        prior = source_map.get(source_id)
        if prior is not None and not _sources_equivalent(prior, candidate_source):
            reasons.append("provenance-conflict")
            provenance_conflicts.append({
                "source_id": source_id,
                "existing": dict(prior),
                "candidate": dict(candidate_source),
            })
        else:
            source_map[source_id] = candidate_source
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

    if target is not None and not evidence_item.get("evidence_targets") and _semantic_duplicate(target, child):
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
            replace_child_id=str(evidence_item.get("id") or "") if evidence_item.get("evidence_targets") else "",
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
        classification="new" if not reasons else (
            "provenance-conflict" if "provenance-conflict" in reasons else
            "duplicate-existing" if "semantic-duplicate" in reasons else "rejected"
        ),
        provenance_conflicts=provenance_conflicts,
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
        if decision.accepted and not (decision.normalized_evidence_item or {}).get("evidence_targets"):
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
                    classification="duplicate-pilot",
                )
            else:
                seen.add(fingerprint)
        decisions.append(decision)
    return decisions


def _stage_bootstraps(
    library: Any, candidates: Sequence[Mapping[str, Any]],
) -> dict[str, CanonicalObject]:
    staged: dict[str, CanonicalObject] = {}
    label_owners: dict[str, str] = {}
    source_identities: dict[str, list[dict[str, Any]]] = {}
    for obj in library.objects_by_id.values():
        for label in (obj.id, obj.title, *obj.aliases):
            label_owners.setdefault(normalize_alias(label), obj.id)
        for source in obj.sources:
            source_identities.setdefault(source.id, []).append(source.to_dict())

    for candidate in candidates:
        raw_bootstraps = candidate.get("entity_bootstraps", [])
        if not isinstance(raw_bootstraps, list):
            raise ValueError("bootstrap entity_bootstraps must be a list")
        for raw in raw_bootstraps:
            if not isinstance(raw, Mapping):
                raise ValueError("bootstrap entry must be a canonical object mapping")
            object_id = normalize_id(str(raw.get("id") or ""))
            if not object_id:
                raise ValueError("bootstrap id is required")
            try:
                obj = validate_object(raw, path=Path(library.root) / f"{object_id}.json")
            except Exception as exc:
                raise ValueError(f"bootstrap validation failed for {object_id}: {exc}") from exc
            prior = staged.get(obj.id) or library.objects_by_id.get(obj.id)
            if prior is not None:
                if prior.to_dict() != obj.to_dict():
                    raise ValueError(f"bootstrap id conflict: {obj.id}")
                _validate_bootstrap_provenance(obj, candidate)
                continue
            for label_type, label in (
                ("id", obj.id), ("title", obj.title),
                *(("alias", alias) for alias in obj.aliases),
            ):
                owner = label_owners.get(normalize_alias(label))
                if owner is not None and owner != obj.id:
                    raise ValueError(f"bootstrap {label_type} collision: {label} with {owner}")
            for source in obj.sources:
                prior_sources = source_identities.get(source.id, [])
                if prior_sources and any(not _sources_equivalent(previous, source.to_dict()) for previous in prior_sources):
                    raise ValueError(f"bootstrap source-identity collision: {source.id}")
            _validate_bootstrap_provenance(obj, candidate)
            staged[obj.id] = obj
            for label in (obj.id, obj.title, *obj.aliases):
                label_owners[normalize_alias(label)] = obj.id
            for source in obj.sources:
                source_identities.setdefault(source.id, []).append(source.to_dict())
    return staged


def _validate_bootstrap_provenance(obj: CanonicalObject, candidate: Mapping[str, Any]) -> None:
    if obj.content_status != "draft" or obj.review_status != "unreviewed" or not obj.human_review_required:
        raise ValueError(f"bootstrap {obj.id} must be draft, unreviewed, and human-review-required")
    anchors = [str(_value(item, "reference") or "") for item in obj.scripture_references]
    passage = str(candidate.get("passage_reference") or "")
    if not anchors or not _anchors_overlap(passage, anchors):
        raise ValueError(f"bootstrap anchor must overlap passage: {obj.id}")
    if not obj.evidence_items:
        raise ValueError(f"bootstrap identity evidence is required: {obj.id}")
    source_map = {source.id: source for source in obj.sources}
    locks = [_mapping(lock) for lock in _sequence(candidate.get("source_locks"))]
    if not locks:
        raise ValueError(f"bootstrap source locks are required: {obj.id}")
    identity = _bootstrap_identity_designation(obj, candidate)
    direct = [lock for lock in locks if lock.get("support_type") == "direct-textual"]
    if not any(
        source_id in source_map
        and source_map[source_id].source_type == "scripture"
        and _anchors_overlap(str(lock.get("locator") or ""), anchors)
        and _anchors_overlap(source_map[source_id].locator, anchors)
        and any(
            source_id in evidence.source_ids
            and _anchors_overlap(passage, [link.reference for link in evidence.scripture_references])
            for evidence in obj.evidence_items
        )
        for lock in direct
        if (source_id := normalize_id(str(lock.get("source_id") or "")))
    ):
        raise ValueError(f"bootstrap direct Scripture source/anchor overlap is required: {obj.id}")

    identity_locks = [
        lock for lock in locks
        if lock.get("support_type") == "entity-identification-and-occurrence"
    ]
    if identity_locks and obj.type != "place":
        raise ValueError(f"bootstrap type must be place for OpenBible identity: {obj.id}")
    for lock in identity_locks:
        locator = str(lock.get("locator") or "")
        source_id = normalize_id(str(lock.get("source_id") or ""))
        if source_id not in source_map or not any(
            source_id in evidence.source_ids for evidence in obj.evidence_items
        ):
            raise ValueError(f"bootstrap OpenBible source is not attached to identity evidence: {obj.id}")
        record_ids = set(re.findall(r"openbible-[a-z0-9]+", locator))
        external_ids = {
            reference.id
            for evidence in obj.evidence_items
            for reference in evidence.external_references
            if reference.domain == "map-place"
        }
        locked_external_ids = record_ids.intersection(external_ids)
        if not locked_external_ids or not _openbible_import_matches(locked_external_ids, obj.id, anchors):
            raise ValueError(f"bootstrap OpenBible identity/occurrence lock mismatch: {obj.id}")
    _validate_bootstrap_identity(obj, identity, candidate, identity_locks, anchors)


def _bootstrap_identity_designation(
    obj: CanonicalObject, candidate: Mapping[str, Any],
) -> Mapping[str, Any]:
    claim = _mapping(candidate.get("locked_identity_claim"))
    source_locks = list(_sequence(candidate.get("source_locks")))
    if (
        claim.get("id") != candidate.get("source_lock_id")
        or claim.get("source_locks") != source_locks
        or not isinstance(claim.get("subject"), Mapping)
        or not isinstance(claim.get("target"), Mapping)
    ):
        raise ValueError(f"bootstrap identity-binding requires the locked claim: {obj.id}")
    identities = [
        _mapping(value) for value in _sequence(candidate.get("entity_designations"))
        if _mapping(value).get("entity_id") == obj.id
    ]
    if len(identities) != 1:
        raise ValueError(f"bootstrap identity-binding requires one entity designation: {obj.id}")
    identity = identities[0]
    label = str(identity.get("label") or "").strip()
    structured_labels = (
        str(_mapping(claim["subject"]).get("label") or ""),
        str(_mapping(claim["target"]).get("label") or ""),
    )
    name = normalize_alias(label)
    if not name or not any(
        re.search(rf"(?<!\w){re.escape(name)}(?!\w)", normalize_alias(text))
        for text in structured_labels
    ):
        raise ValueError(f"bootstrap identity-binding designation is absent from the locked claim: {obj.id}")
    return identity


def _validate_bootstrap_identity(
    obj: CanonicalObject, identity: Mapping[str, Any], candidate: Mapping[str, Any],
    identity_locks: list[Mapping[str, Any]], anchors: list[str],
) -> None:
    kind = str(identity.get("identity_kind") or "")
    label = str(identity.get("label") or "").strip()
    claim = _mapping(candidate["locked_identity_claim"])
    target = _mapping(claim["target"])
    approved_titles = {normalize_alias(label)}
    approved_aliases = set(approved_titles)
    if kind == "openbible-place":
        record_id = str(identity.get("imported_record_id") or "")
        locked_ids = {
            record_id_value
            for lock in identity_locks
            for record_id_value in re.findall(r"openbible-[a-z0-9]+", str(lock.get("locator") or ""))
        }
        imported = _openbible_imported_record(record_id, obj.id, anchors)
        if obj.type != "place" or record_id not in locked_ids or imported is None:
            raise ValueError(f"bootstrap identity-binding imported place mismatch: {obj.id}")
        imported_designations = {
            normalize_alias(str(name))
            for name in (imported.get("name"), *_sequence(imported.get("aliases")))
            if name
        }
        if normalize_alias(label) not in imported_designations:
            raise ValueError(f"bootstrap identity-binding label is not an imported name or alias: {obj.id}")
        if not any(
            reference.domain == "map-place" and reference.id == record_id
            for evidence in obj.evidence_items for reference in evidence.external_references
        ):
            raise ValueError(f"bootstrap identity-binding imported record is not attached: {obj.id}")
        imported_name = str(imported.get("name") or "")
        if imported_name:
            approved_titles.add(normalize_alias(imported_name))
        approved_aliases.update(imported_designations)
    elif kind in {"person", "territory"}:
        expected_type = "person" if kind == "person" else "place"
        expected_target_type = "person-ruler" if kind == "person" else "territory"
        expected_title = label if kind == "person" else f"{label} territory"
        if (
            obj.type != expected_type
            or target.get("entity_type") != expected_target_type
            or normalize_alias(str(target.get("label") or "")) != normalize_alias(label)
            or obj.id != normalize_id(expected_title)
            or identity_locks
        ):
            raise ValueError(f"bootstrap identity-binding typed designation mismatch: {obj.id}")
        if kind == "territory":
            approved_titles = {normalize_alias(expected_title)}
        approved_titles.add(normalize_alias(expected_title))
        approved_aliases.add(normalize_alias(expected_title))
    else:
        raise ValueError(f"bootstrap identity-binding unknown identity kind: {obj.id}")
    if normalize_alias(obj.title) not in approved_titles:
        raise ValueError(f"bootstrap identity-binding canonical title mismatch: {obj.id}")
    approved_aliases.update({
        normalize_alias(f"{label} in {anchor}") for anchor in anchors
    })
    if any(normalize_alias(alias) not in approved_aliases for alias in obj.aliases):
        raise ValueError(f"bootstrap identity-binding alias mismatch: {obj.id}")


def _openbible_imported_record(
    record_id: str, object_id: str, anchors: list[str],
) -> Mapping[str, Any] | None:
    import_path = Path(__file__).resolve().parents[2] / "bhf_agent/data/openbible_places.json"
    try:
        imported = json.loads(import_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return next((
        entry for entry in imported if isinstance(entry, Mapping)
        and entry.get("id") == record_id
        and str(entry.get("source_url") or "").rstrip("/").endswith(f"/{object_id}")
        and any(
            _anchors_overlap(
                f"{reference.get('book')} {reference.get('chapter')}:{reference.get('verse_start')}-{reference.get('verse_end')}",
                anchors,
            )
            for reference in _sequence(entry.get("references"))
            if isinstance(reference, Mapping)
        )
    ), None)


def _openbible_import_matches(record_ids: set[str], object_id: str, anchors: list[str]) -> bool:
    import_path = Path(__file__).resolve().parents[2] / "bhf_agent/data/openbible_places.json"
    try:
        imported = json.loads(import_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return any(
        entry.get("id") in record_ids
        and str(entry.get("source_url") or "").rstrip("/").endswith(f"/{object_id}")
        and any(
            _anchors_overlap(
                f"{reference.get('book')} {reference.get('chapter')}:{reference.get('verse_start')}-{reference.get('verse_end')}",
                anchors,
            )
            for reference in _sequence(entry.get("references"))
            if isinstance(reference, Mapping)
        )
        for entry in imported if isinstance(entry, Mapping)
    )


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
    if write and any(_sequence(item.get("entity_bootstraps")) for item in candidate_values):
        raise ValueError("write=True is forbidden for bootstrap-bearing candidate transactions")
    before_objects = list(library.objects_by_id.values())
    staged_bootstraps = _stage_bootstraps(library, candidate_values)
    library.objects_by_id.update(staged_bootstraps)
    if staged_bootstraps:
        staged_paths = {
            object_id: path for object_id in library.objects_by_id
            if (path := library.source_path_for(object_id)) is not None
        }
        staged_paths.update({
            object_id: Path(root) / "objects" / CATEGORY_FOLDERS[obj.type] / f"{object_id}.json"
            for object_id, obj in staged_bootstraps.items()
        })
        staged_manifest = dict(library.manifest)
        categories = dict(staged_manifest.get("categories") or {})
        for obj in staged_bootstraps.values():
            folder = CATEGORY_FOLDERS[obj.type]
            categories[folder] = int(categories.get(folder, 0)) + 1
        staged_manifest["object_count"] = len(library.objects_by_id)
        staged_manifest["categories"] = categories
        try:
            validate_library(
                list(library.objects_by_id.values()),
                manifest=staged_manifest, source_paths=staged_paths,
            )
        except Exception as exc:
            raise ValueError(f"candidate queue fails final CKL validation: {exc}") from exc
    decisions = validate_candidates(candidate_values, library=library)
    # A staged object is part of the transaction only while an accepted
    # candidate owns it. Revalidate after pruning because another candidate
    # may have relied on an object owned solely by a rejected candidate.
    while True:
        accepted_bootstrap_ids = {
            normalize_id(str(raw.get("id") or ""))
            for decision in decisions if decision.accepted
            for raw in _sequence(decision.candidate.get("entity_bootstraps"))
            if isinstance(raw, Mapping)
        }
        orphan_ids = set(staged_bootstraps) - accepted_bootstrap_ids
        if not orphan_ids:
            break
        for object_id in orphan_ids:
            staged_bootstraps.pop(object_id)
            library.objects_by_id.pop(object_id)
        decisions = validate_candidates(candidate_values, library=library)
    after_data = {object_id: object_value.to_dict() for object_id, object_value in library.objects_by_id.items()}
    changed_object_ids: set[str] = set(staged_bootstraps)

    loaded_typed: dict[tuple[str, str], dict[str, Any]] = {}
    for parent_id, parent in after_data.items():
        for raw in _sequence(parent.get("evidence_items")):
            item = dict(_mapping(raw))
            if not item.get("evidence_targets"):
                continue
            key = (parent_id, evidence_structural_fingerprint(parent_id, item))
            if key in loaded_typed:
                raise CanonicalStructuralDuplicateConflict(
                    f"canonical-structural-duplicate-conflict: {parent_id}:{key[1]}"
                )
            loaded_typed[key] = item

    typed_groups: dict[tuple[str, str], list[int]] = {}
    for index, decision in enumerate(decisions):
        child = decision.normalized_evidence_item or {}
        if decision.accepted and child.get("evidence_targets"):
            parent_id = normalize_id(str(decision.candidate.get("target_object_id") or ""))
            key = (parent_id, evidence_structural_fingerprint(parent_id, child))
            typed_groups.setdefault(key, []).append(index)

    for decision in decisions:
        if not decision.accepted or (decision.normalized_evidence_item or {}).get("evidence_targets"):
            continue
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

    for (parent_id, fingerprint), indices in sorted(typed_groups.items()):
        target = after_data[parent_id]
        previous_payload = _canonical_json(target)
        loaded = loaded_typed.get((parent_id, fingerprint))
        ordered = sorted(indices, key=lambda index: (
            str((decisions[index].normalized_evidence_item or {}).get("id") or ""),
            str(decisions[index].candidate.get("source_lock_id") or ""),
        ))
        survivor = dict(loaded or decisions[ordered[0]].normalized_evidence_item or {})
        survivor_id = str(survivor["id"])
        merged_sources = list(_sequence(target.get("sources")))
        merged_source_ids = list(_sequence(survivor.get("source_ids")))
        merged_links = list(_sequence(survivor.get("scripture_references")))
        merged_external = list(_sequence(survivor.get("external_references")))
        contributing_sources: set[str] = set(str(value) for value in merged_source_ids)
        survivors_added = False
        for index in ordered:
            decision = decisions[index]
            child = dict(decision.normalized_evidence_item or {})
            if child["id"] == survivor_id and _non_provenance_fields(child) != _non_provenance_fields(survivor):
                decisions[index] = replace(
                    decision, accepted=False, reasons=[*decision.reasons, "identity-conflict"],
                    classification="identity-conflict", survivor_evidence_id=survivor_id,
                )
                continue
            candidate_sources = _candidate_sources(decision.candidate)
            try:
                next_sources = _merge_candidate_sources(
                    merged_sources, candidate_sources, target_id=parent_id,
                )
            except ValueError:
                conflicts = _source_conflict_details(merged_sources, candidate_sources)
                decisions[index] = replace(
                    decision, accepted=False, reasons=[*decision.reasons, "provenance-conflict"],
                    classification="provenance-conflict", survivor_evidence_id=survivor_id,
                    provenance_conflicts=conflicts,
                )
                continue
            old_provenance = (
                _canonical_json(merged_sources), _canonical_json(merged_source_ids),
                _canonical_json(merged_links), _canonical_json(merged_external),
            )
            merged_sources = next_sources
            merged_source_ids = _canonical_union([*merged_source_ids, *_sequence(child.get("source_ids"))])
            merged_links = _canonical_union([*merged_links, *_sequence(child.get("scripture_references"))])
            merged_external = _canonical_union([*merged_external, *_sequence(child.get("external_references"))])
            contributing_sources.update(str(value) for value in _sequence(child.get("source_ids")))
            new_provenance = (
                _canonical_json(merged_sources), _canonical_json(merged_source_ids),
                _canonical_json(merged_links), _canonical_json(merged_external),
            )
            added_provenance = new_provenance != old_provenance
            if loaded is not None:
                classification = "duplicate-existing-provenance-merged" if added_provenance else "duplicate-existing"
            elif not survivors_added and child["id"] == survivor_id:
                classification = "new"
            else:
                classification = "duplicate-pilot-provenance-merged" if added_provenance else "duplicate-pilot"
            decisions[index] = replace(
                decision, classification=classification, survivor_evidence_id=survivor_id,
                contributing_source_ids=sorted(contributing_sources),
            )
            survivors_added = True
        if not survivors_added:
            continue
        for index in ordered:
            if decisions[index].accepted:
                decisions[index] = replace(
                    decisions[index], contributing_source_ids=sorted(contributing_sources),
                )
        survivor["source_ids"] = merged_source_ids
        survivor["scripture_references"] = merged_links
        survivor["external_references"] = merged_external
        target["sources"] = sorted(merged_sources, key=_canonical_json)
        evidence_items = list(_sequence(target.get("evidence_items")))
        if loaded is not None:
            evidence_items = [
                survivor if _mapping(item).get("id") == survivor_id else dict(_mapping(item))
                for item in evidence_items
            ]
        else:
            if any(_mapping(item).get("id") == survivor_id for item in evidence_items):
                raise ValueError(f"identity-conflict: {parent_id}:{survivor_id}")
            evidence_items.append(survivor)
        target["evidence_items"] = evidence_items
        if _canonical_json(target) != previous_payload:
            changed_object_ids.add(parent_id)

    accepted_bootstrap_ids = {
        normalize_id(str(raw.get("id") or ""))
        for decision in decisions if decision.accepted
        for raw in _sequence(decision.candidate.get("entity_bootstraps"))
        if isinstance(raw, Mapping)
    }
    for object_id in set(staged_bootstraps) - accepted_bootstrap_ids:
        staged_bootstraps.pop(object_id)
        after_data.pop(object_id)
        changed_object_ids.discard(object_id)

    source_paths = {
        object_id: path
        for object_id in after_data
        if (path := library.source_path_for(object_id)) is not None
    }
    for object_id, obj in staged_bootstraps.items():
        source_paths[object_id] = Path(root) / "objects" / CATEGORY_FOLDERS[obj.type] / f"{object_id}.json"
    simulated_manifest = dict(library.manifest)
    if staged_bootstraps:
        categories = dict(simulated_manifest.get("categories") or {})
        for obj in staged_bootstraps.values():
            folder = CATEGORY_FOLDERS[obj.type]
            categories[folder] = int(categories.get(folder, 0)) + 1
        simulated_manifest["object_count"] = len(after_data)
        simulated_manifest["categories"] = categories
    try:
        after_objects = [
            validate_object(after_data[object_id], path=source_paths.get(object_id))
            for object_id in sorted(after_data)
        ]
        validate_library(
            after_objects,
            manifest=simulated_manifest,
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
        simulated_objects=after_data,
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
    replace_child_id: str = "",
) -> dict[str, Any] | None:
    raw = _mapping(target)
    merged = dict(raw)
    merged_children = [
        dict(_mapping(item)) for item in _sequence(raw.get(child_field))
        if not replace_child_id or _mapping(item).get("id") != replace_child_id
    ]
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


def _source_conflict_details(
    existing: Sequence[Any], candidates: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {
        normalize_id(str(_mapping(source).get("id") or "")): dict(_mapping(source))
        for source in existing
    }
    return [
        {
            "source_id": source_id,
            "existing": by_id[source_id],
            "candidate": dict(source),
        }
        for source in candidates
        if (source_id := normalize_id(str(source.get("id") or ""))) in by_id
        and not _sources_equivalent(by_id[source_id], source)
    ]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _canonical_union(values: Sequence[Any]) -> list[Any]:
    by_json = {_canonical_json(value): value for value in values}
    return [by_json[key] for key in sorted(by_json)]


def _non_provenance_fields(evidence: Mapping[str, Any]) -> dict[str, Any]:
    normalized = CanonicalEvidenceItem.from_mapping(evidence).to_dict()
    return {
        key: value for key, value in normalized.items()
        if key not in {"source_ids", "scripture_references", "external_references"}
    }


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
