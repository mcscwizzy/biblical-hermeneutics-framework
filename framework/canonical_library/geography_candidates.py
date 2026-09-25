"""Deterministic conversion of verified geography source locks into CKL candidates.

The source-lock queue remains authoritative.  This module only turns an
eligible, LOCKED record into an existing ``CanonicalEvidenceItem`` shape when
both its target object and every source record can be resolved locally.  It
records every other lock as a rejection; it never creates an entity, resolves
an ambiguous label, or performs an apply.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .normalization import normalize_id
from .source_locks import validate_source_lock_queue_against_repository


_ELIGIBLE_GENERATION = "eligible"
_SUPPORTED_READINESS = {
    "ready-for-book-evidence-item": "book",
    "ready-for-place-evidence-item": "subject",
    "requires-source-registration-on-target": "subject",
}


def build_geography_candidate_queue(
    source_lock_queue: Mapping[str, Any],
    *,
    library: Any,
    root: str | Path,
) -> dict[str, Any]:
    """Build a deterministic, non-mutating geography candidate queue.

    The returned records include rejected LOCKED claims so a dry-run report
    exposes schema and entity limitations instead of silently reducing scope.
    """

    repository_root = Path(root).resolve()
    source_lock_report = validate_source_lock_queue_against_repository(
        source_lock_queue,
        root=repository_root,
    )
    sources = _source_definitions(source_lock_queue)
    records: list[dict[str, Any]] = []

    for chapter in source_lock_queue.get("chapters", []):
        if not isinstance(chapter, Mapping):
            continue
        if chapter.get("candidate_generation") != _ELIGIBLE_GENERATION:
            continue
        chapter_reference = str(chapter.get("reference") or "")
        for claim in chapter.get("claims", []):
            if not isinstance(claim, Mapping) or claim.get("status") != "LOCKED":
                continue
            records.append(
                _candidate_record(
                    chapter_reference,
                    claim,
                    sources=sources,
                    library=library,
                    root=repository_root,
                )
            )

    records.sort(key=lambda item: str(item["source_lock_id"]))
    return {
        "schema_version": "1.0",
        "queue_id": "ckl-geography-pilot-candidates",
        "source_lock_queue_id": source_lock_queue.get("queue_id"),
        "source_lock_validation": source_lock_report.to_dict(),
        "dry_run_only": True,
        "candidates": records,
    }


def _candidate_record(
    chapter_reference: str,
    claim: Mapping[str, Any],
    *,
    sources: Mapping[str, Mapping[str, Any]],
    library: Any,
    root: Path,
) -> dict[str, Any]:
    claim_id = str(claim["id"])
    subject = _mapping(claim.get("subject"))
    target = _mapping(claim.get("target"))
    readiness = str(claim.get("candidate_readiness") or "")
    base = {
        "source_lock_id": claim_id,
        "source_lock_status": "LOCKED",
        "chapter_reference": chapter_reference,
        "subject": dict(subject),
        "relationship_type": str(claim.get("relationship_type") or ""),
        "target": dict(target),
        "scripture_anchors": [dict(item) for item in claim.get("scripture_anchors", [])],
        "temporal_scope": dict(_mapping(claim.get("temporal_scope"))),
        "confidence": dict(_mapping(claim.get("confidence"))),
        "provenance": dict(_mapping(claim.get("provenance"))),
        "material_relevance": str(claim.get("material_relevance") or ""),
        "source_locks": [dict(item) for item in claim.get("source_locks", [])],
        "candidate_readiness": readiness,
        "operation": "append-evidence-item",
    }

    target_id, reason = _target_object_id(claim, sources=sources)
    if reason:
        return {**base, "outcome": "REJECTED", "rejection_reason": reason}
    target_object = _object(library, target_id)
    if target_object is None:
        return {**base, "outcome": "REJECTED", "rejection_reason": "target-entity-unresolved"}

    source_records, source_reason = _source_records(claim, sources=sources, root=root)
    if source_reason:
        return {**base, "outcome": "REJECTED", "rejection_reason": source_reason}
    evidence = _evidence_item(
        claim,
        target_id=target_id,
        source_records=source_records,
        readiness=readiness,
    )
    path = _source_path(library, target_id, root)
    candidate_payload = {
        "source_lock_id": claim_id,
        "source_lock_status": "LOCKED",
        "dimension": "geography",
        "target_object_id": target_id,
        "passage_reference": _compound_anchor(claim),
        "relationship": str(claim.get("relationship_type") or ""),
        "source_records": source_records,
        "evidence_item": evidence,
    }
    return {
        **base,
        "outcome": "NEW",
        "target_ckl_object_id": target_id,
        "target_ckl_object_type": _value(target_object, "type"),
        "target_ckl_file": path,
        "candidate_payload": candidate_payload,
    }


def _target_object_id(
    claim: Mapping[str, Any],
    *,
    sources: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str]:
    readiness = str(claim.get("candidate_readiness") or "")
    mode = _SUPPORTED_READINESS.get(readiness)
    if mode is None:
        if readiness == "ready-for-institution-evidence-item":
            return "", "schema-lacks-typed-target-value"
        return "", "entity-bootstrap-required"
    if mode == "subject":
        subject_id = normalize_id(str(_mapping(claim.get("subject")).get("entity_id") or ""))
        return (subject_id, "") if subject_id else ("", "entity-bootstrap-required")

    for source_lock in claim.get("source_locks", []):
        source = sources.get(str(_mapping(source_lock).get("source_id") or ""))
        if source and source.get("registry_status") == "existing-ckl-object-source":
            provenance = _mapping(source.get("provenance"))
            target_id = normalize_id(str(provenance.get("record_object_id") or ""))
            if target_id:
                return target_id, ""
    return "", "source-record-unresolved"


def _source_records(
    claim: Mapping[str, Any],
    *,
    sources: Mapping[str, Mapping[str, Any]],
    root: Path,
) -> tuple[list[dict[str, Any]], str]:
    records: list[dict[str, Any]] = []
    for lock in claim.get("source_locks", []):
        lock_value = _mapping(lock)
        source = sources.get(str(lock_value.get("source_id") or ""))
        if source is None:
            return [], "source-record-unresolved"
        if source.get("registry_status") != "existing-ckl-object-source":
            continue
        provenance = _mapping(source.get("provenance"))
        record_path = root / str(provenance.get("record_path") or "")
        source_id = normalize_id(str(provenance.get("record_source_id") or ""))
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return [], "source-record-unresolved"
        matched = next(
            (
                dict(item)
                for item in record.get("sources", [])
                if normalize_id(str(_mapping(item).get("id") or "")) == source_id
            ),
            None,
        )
        if matched is None:
            return [], "source-record-unresolved"
        if all(normalize_id(str(item.get("id") or "")) != source_id for item in records):
            records.append(matched)
    if not records:
        return [], "source-record-unresolved"
    return records, ""


def _evidence_item(
    claim: Mapping[str, Any],
    *,
    target_id: str,
    source_records: list[dict[str, Any]],
    readiness: str,
) -> dict[str, Any]:
    source_locks = [_mapping(item) for item in claim.get("source_locks", [])]
    anchors = [_mapping(item) for item in claim.get("scripture_anchors", [])]
    subject = _mapping(claim.get("subject"))
    target = _mapping(claim.get("target"))
    relationship = str(claim.get("relationship_type") or "")
    related_objects: list[dict[str, Any]] = []
    if readiness == "requires-source-registration-on-target":
        target_entity_id = normalize_id(str(target.get("entity_id") or ""))
        if target_entity_id:
            related_objects.append(
                {
                    "id": target_entity_id,
                    "relationship": relationship,
                    "weight": 10,
                    "notes": _lock_locators(source_locks),
                }
            )
    external_references = [
        {
            "domain": "external-dataset",
            "id": str(lock["source_id"]),
            "relationship": str(lock["support_type"]),
            "notes": str(lock["locator"]),
        }
        for lock in source_locks
        if str(lock.get("source_id") or "") == "openbible-geocoding-data"
    ]
    confidence = str(_mapping(claim.get("confidence")).get("level") or "low")
    return {
        "id": normalize_id(f"source-lock-{claim['id']}"),
        "title": str(claim["id"]),
        "evidence_type": "geography-environment",
        "description": str(claim["material_relevance"]),
        "assertion_type": "primary-evidence",
        "confidence": {"moderate": "medium"}.get(confidence, confidence),
        "confidence_rationale": str(_mapping(claim.get("confidence")).get("rationale") or ""),
        "passage_relevance": str(claim["material_relevance"]),
        "primary_observation": str(_mapping(claim.get("confidence")).get("rationale") or ""),
        "temporal_scope": dict(_mapping(claim.get("temporal_scope"))),
        "geography_ids": [target_id] if readiness == "ready-for-place-evidence-item" else [],
        "related_objects": related_objects,
        "related_evidence": [],
        "scripture_references": [
            {
                "reference": str(anchor["reference"]),
                "relationship": str(anchor.get("eligibility") or "direct"),
                "temporal_relation": "unknown",
                "relevance_rationale": str(claim["material_relevance"]),
                "weight": 10,
            }
            for anchor in anchors
        ],
        "source_ids": [normalize_id(str(item["id"])) for item in source_records],
        "claim_ids": [],
        "external_references": external_references,
        "metadata": {},
        "notes": _provenance_note(claim, subject=subject, target=target, relationship=relationship),
    }


def _provenance_note(
    claim: Mapping[str, Any],
    *,
    subject: Mapping[str, Any],
    target: Mapping[str, Any],
    relationship: str,
) -> str:
    locks = _lock_locators([_mapping(item) for item in claim.get("source_locks", [])])
    return (
        f"Source-lock identity: {claim['id']}; status: LOCKED. "
        f"Subject: {subject.get('label')} [{subject.get('entity_type')}]. "
        f"Relationship: {relationship}. "
        f"Target: {target.get('label')} [{target.get('entity_type')}]. "
        f"Source locks: {locks}"
    )


def _lock_locators(locks: list[Mapping[str, Any]]) -> str:
    return "; ".join(
        f"{lock.get('source_id')} @ {lock.get('locator')} ({lock.get('support_type')})"
        for lock in locks
    )


def _compound_anchor(claim: Mapping[str, Any]) -> str:
    return "; ".join(str(_mapping(anchor).get("reference") or "") for anchor in claim.get("scripture_anchors", []))


def _source_definitions(queue: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(source["id"]): source
        for source in queue.get("sources", [])
        if isinstance(source, Mapping) and source.get("id")
    }


def _source_path(library: Any, object_id: str, root: Path) -> str:
    getter = getattr(library, "source_path_for", None)
    path = getter(object_id) if callable(getter) else None
    if path is None:
        return ""
    return Path(path).resolve().relative_to(root).as_posix()


def _object(library: Any, object_id: str) -> Any | None:
    objects = getattr(library, "objects_by_id", {})
    return objects.get(object_id) if isinstance(objects, Mapping) else None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _value(value: Any, name: str) -> str:
    if isinstance(value, Mapping):
        return str(value.get(name) or "")
    return str(getattr(value, name, "") or "")
