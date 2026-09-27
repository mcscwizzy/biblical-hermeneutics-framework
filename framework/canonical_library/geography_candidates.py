"""Deterministic conversion of verified geography source locks into CKL candidates.

The source-lock queue remains authoritative. Eligible LOCKED records become
evidence candidates when their sources and target identities resolve locally.
The converter stages draft entities for explicit typed families, rejects
ambiguous identities, and never applies them to production CKL.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from .normalization import normalize_id
from .schema import CanonicalObject
from .source_locks import validate_source_lock_queue_against_repository


_ELIGIBLE_GENERATION = "eligible"
_SUPPORTED_READINESS = {
    "ready-for-book-evidence-item": "book",
    "ready-for-place-evidence-item": "subject",
    "requires-source-registration-on-target": "subject",
}
_TYPED_FAMILIES = {
    ("requires-entity-bootstrap", "encamped-between", "place-pair"): "pair",
    ("requires-entity-bootstrap", "river-water-context", "water-feature-pair"): "pair",
    ("requires-entity-bootstrap", "narrated-navigation-markers", "maritime-narrative-sequence"): "maritime",
    ("requires-entity-bootstrap", "near", "textual-field"): "field",
    ("requires-entity-bootstrap", "ruled-by", "person-ruler"): "person",
    ("requires-entity-bootstrap", "located-in", "territory"): "territory",
    ("ready-for-institution-evidence-item", "territorial-inheritance", "territorial-entitlement"): "entitlement",
    ("ready-for-institution-evidence-item", "tithe-as-inheritance", "economic-entitlement"): "entitlement",
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

    family = _TYPED_FAMILIES.get((
        readiness, str(claim.get("relationship_type") or ""), str(target.get("entity_type") or ""),
    ))
    if family:
        return _typed_candidate_record(base, claim, family=family, sources=sources, library=library, root=root)
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


def _typed_candidate_record(
    base: dict[str, Any], claim: Mapping[str, Any], *, family: str,
    sources: Mapping[str, Mapping[str, Any]], library: Any, root: Path,
) -> dict[str, Any]:
    relationship = str(claim["relationship_type"])
    subject = _mapping(claim.get("subject"))
    target = _mapping(claim.get("target"))
    if family in {"pair", "maritime"}:
        book = re.match(r"^(.+?)\s+\d+:\d+", _compound_anchor(claim))
        target_id = normalize_id(book.group(1)) if book else ""
    elif family == "field":
        target_id = "sychar" if subject.get("label") == "Sychar" else ""
    else:
        target_id = normalize_id(str(subject.get("entity_id") or ""))
    if not target_id:
        return {**base, "outcome": "REJECTED", "rejection_reason": "typed-subject-unresolved"}

    source_records, reason = _source_records(claim, sources=sources, root=root)
    if reason:
        return {**base, "outcome": "REJECTED", "rejection_reason": reason}
    # The CKL source can span a whole book. Preserve each locked Scripture
    # locator in a distinct source record so provenance survives deduplication.
    for lock in claim["source_locks"]:
        source = sources.get(str(lock["source_id"]))
        if source is None:
            return {**base, "outcome": "REJECTED", "rejection_reason": "source-record-unresolved"}
        if source.get("registry_status") != "existing-ckl-object-source":
            continue
        original_id = normalize_id(str(_mapping(source.get("provenance")).get("record_source_id") or ""))
        matching = next(
            (record for record in source_records if normalize_id(str(record["id"])) == original_id),
            None,
        )
        if matching is None:
            return {**base, "outcome": "REJECTED", "rejection_reason": "source-record-unresolved"}
        source_records.append({
            **matching,
            "id": normalize_id(f"{claim['id']}-{lock['source_id']}-lock"),
            "locator": str(lock["locator"]),
        })
    try:
        targets, named_entities = _typed_targets(claim, family=family, library=library, root=root)
        bootstraps = [
            _bootstrap_entity(entity_id, label, claim, sources=sources, record=record)
            for entity_id, label, record in named_entities
            if _object(library, entity_id) is None
        ]
        if _object(library, target_id) is None and target_id not in {item["id"] for item in bootstraps}:
            raise ValueError("target-entity-unresolved")
    except ValueError as exc:
        return {**base, "outcome": "REJECTED", "rejection_reason": str(exc)}

    evidence = _evidence_item(
        claim, target_id=target_id, source_records=source_records,
        readiness=str(claim["candidate_readiness"]),
    )
    evidence["evidence_targets"] = targets
    evidence["related_objects"] = []
    evidence["geography_ids"] = []
    candidate_payload = {
        "source_lock_id": claim["id"], "source_lock_status": "LOCKED",
        "dimension": "geography", "target_object_id": target_id,
        "passage_reference": _compound_anchor(claim), "relationship": relationship,
        "source_locks": [dict(item) for item in claim["source_locks"]],
        "source_records": source_records, "evidence_item": evidence,
        "entity_bootstraps": bootstraps,
    }
    if bootstraps:
        candidate_payload["locked_identity_claim"] = {
            "id": claim["id"],
            "subject": dict(subject),
            "target": dict(target),
            "source_locks": [dict(item) for item in claim["source_locks"]],
        }
        candidate_payload["entity_designations"] = [
            {
                "entity_id": entity_id,
                "identity_kind": "openbible-place" if record is not None else family,
                "label": label,
                **({"imported_record_id": record["id"]} if record is not None else {}),
            }
            for entity_id, label, record in named_entities
            if any(bootstrap["id"] == entity_id for bootstrap in bootstraps)
        ]
    target_object = _object(library, target_id)
    return {
        **base, "outcome": "NEW", "target_ckl_object_id": target_id,
        "target_ckl_object_type": _value(target_object, "type") if target_object else "place",
        "target_ckl_file": _source_path(library, target_id, root) if target_object else "",
        "candidate_payload": candidate_payload,
    }


def _typed_targets(
    claim: Mapping[str, Any], *, family: str, library: Any, root: Path,
) -> tuple[list[dict[str, Any]], list[tuple[str, str, Mapping[str, Any] | None]]]:
    relationship = str(claim["relationship_type"])
    label = str(_mapping(claim.get("target")).get("label") or "")
    entities: list[tuple[str, str, Mapping[str, Any] | None]] = []
    roles: list[str] = []
    if family == "pair":
        pattern = r"^([A-Z][A-Za-z]+) and ([A-Z][A-Za-z]+)(?: as rivers of Damascus)?$"
        match = re.fullmatch(pattern, label)
        if not match:
            raise ValueError("malformed-named-pair")
        names = list(match.groups())
        roles = ["boundary" if relationship == "encamped-between" else "compared-river"] * 2
    elif family == "maritime":
        match = re.fullmatch(
            r"^([A-Z][A-Za-z ]+) intended; ([A-Z][A-Za-z]+) and ([A-Z][A-Za-z]+) reached; "
            r"([A-Z][A-Za-z]+), ([A-Z][A-Za-z]+), and ([A-Z][A-Za-z]+) passed; "
            r"([A-Z][A-Za-z ]+) reached and ([A-Z][A-Za-z]+) nearby$", label,
        )
        if not match:
            raise ValueError("malformed-maritime-sequence")
        names = list(match.groups())
        roles = ["intended-destination", "reached", "reached", "passed", "passed", "passed", "reached", "nearby"]
    elif family in {"field", "person", "territory"}:
        if family == "field":
            if label != "field Jacob gave to Joseph" or _mapping(claim.get("subject")).get("label") != "Sychar":
                raise ValueError("ambiguous-textual-field")
            names = ["Sychar"]
        elif family == "person":
            if label != "Archelaus":
                raise ValueError("unregistered-person")
            names = [label]
        else:
            if label != "Judah":
                raise ValueError("unregistered-territory")
            names = [label]
    elif family == "entitlement":
        expected = (
            "no inheritance among Israel, with land context stated to Aaron"
            if relationship == "territorial-inheritance" else
            "Israel's tithes assigned as inheritance for Levite service"
        )
        if label != expected:
            raise ValueError("unregistered-entitlement-vocabulary")
        qualifiers = [{"kind": "domain", "normalized_value": "territorial" if relationship == "territorial-inheritance" else "economic"}]
        if relationship == "territorial-inheritance":
            qualifiers.extend([
                {"kind": "scope", "normalized_value": "among-israel"},
                {"kind": "contextual-addressee", "entity_id": "aaron"},
            ])
        else:
            qualifiers.extend([{"kind": "source", "normalized_value": "israel"}, {"kind": "basis", "normalized_value": "levite-service"}])
        return [{"kind": "value", "relationship": relationship, "value_type": "entitlement",
                 "normalized_value": "none" if relationship == "territorial-inheritance" else "tithe",
                 "display_value": label, "qualifiers": qualifiers}], []
    else:
        raise ValueError("unsupported-typed-family")

    openbible = json.loads((root / "bhf_agent/data/openbible_places.json").read_text(encoding="utf-8"))
    by_name = {str(item["name"]).casefold(): item for item in openbible}
    locks = [_mapping(item) for item in claim["source_locks"]]
    identity_locks = [item for item in locks if item.get("support_type") == "entity-identification-and-occurrence"]
    locator = str(identity_locks[0].get("locator") or "") if len(identity_locks) == 1 else ""
    locked_ids = set(re.findall(r"openbible-[a-z0-9]+", locator))
    selected_ids: set[str] = set()
    for name in names:
        if family in {"person", "territory"}:
            entity_id = "archelaus" if family == "person" else "judah-territory"
            record = None
        else:
            record = by_name.get(name.casefold())
            if record is None and name == "Socoh":
                record = by_name.get("socoh 1")
            if record is None or record["id"] not in locked_ids:
                raise ValueError("openbible-identity-unresolved")
            entity_id = record["source_url"].rstrip("/").rsplit("/", 1)[-1]
            if f"/{entity_id}" not in locator and family != "maritime":
                raise ValueError("openbible-location-unlocked")
            selected_ids.add(record["id"])
            if not _openbible_occurs_in_anchor(record, _compound_anchor(claim)):
                raise ValueError("openbible-occurrence-unresolved")
        entities.append((entity_id, name, record))
    if family not in {"person", "territory"} and selected_ids != locked_ids:
        raise ValueError("openbible-identity-count-mismatch")
    if family == "field":
        return [{"kind": "value", "relationship": "near", "value_type": "geographic-feature",
                 "normalized_value": "field", "display_value": label,
                 "qualifiers": [{"kind": "attributed-giver", "entity_id": "jacob"},
                                {"kind": "attributed-recipient", "entity_id": "joseph"}]}], entities
    return [
        {"kind": "entity", "relationship": relationship, "entity_id": entity_id,
         **({"role": roles[index]} if roles else {}),
         **({"sequence": index + 1} if family == "maritime" else {})}
        for index, (entity_id, _, _) in enumerate(entities)
    ], entities


def _openbible_occurs_in_anchor(record: Mapping[str, Any], anchor: str) -> bool:
    match = re.match(r"^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$", anchor)
    if not match:
        return False
    book, chapter, start, end = match.groups()
    for reference in record.get("references", []):
        if (str(reference.get("book")).casefold() == book.casefold()
            and reference.get("chapter") == int(chapter)
            and int(reference.get("verse_start", 0)) <= int(end or start)
            and int(reference.get("verse_end", 0)) >= int(start)):
            return True
    return False


def _bootstrap_entity(
    entity_id: str, label: str, claim: Mapping[str, Any], *,
    sources: Mapping[str, Mapping[str, Any]], record: Mapping[str, Any] | None,
) -> dict[str, Any]:
    locks = [_mapping(item) for item in claim["source_locks"]]
    direct = next((item for item in locks if item.get("support_type") == "direct-textual"), None)
    if direct is None:
        raise ValueError("bootstrap-direct-scripture-lock-required")
    anchor = _compound_anchor(claim)
    source_records = [{
        "id": str(direct["source_id"]), "title": str(sources[str(direct["source_id"])]["title"]),
        "author": "", "publisher": "", "year": None,
        "locator": str(direct["locator"]), "url": "", "source_type": "scripture", "supports": [],
        "notes": "Locked Scripture identity and occurrence source.",
    }]
    if record is not None:
        source_records.append({
            "id": "openbible-geocoding-data", "title": "OpenBible.info Bible Geocoding Data",
            "author": "", "publisher": "OpenBible.info", "year": None,
            "locator": "https://www.openbible.info/geo/atlas/", "url": "https://www.openbible.info/geo/atlas/",
            "source_type": "reference-work", "supports": [],
            "notes": "Imported passage-indexed place records.",
        })
    evidence = _evidence_item(
        claim, target_id=entity_id, source_records=source_records,
        readiness=str(claim["candidate_readiness"]),
    )
    evidence.update({
        "id": normalize_id(f"{entity_id}-{claim['id']}-identity"), "title": f"{label} identity",
        "description": f"{label} is named in {anchor}.",
        "passage_relevance": f"{label} is named in {anchor}.",
        "primary_observation": f"{label} is named in {anchor}.",
        "source_ids": [item["id"] for item in source_records],
        "external_references": ([{"domain": "map-place", "id": record["id"],
                                 "relationship": "same-evidence", "notes": record["source_url"]}]
                                if record is not None else []),
        "related_objects": [], "geography_ids": [],
    })
    object_type = "person" if entity_id == "archelaus" else "place"
    bootstrap = CanonicalObject(
        id=entity_id, type=object_type, title=label if entity_id != "judah-territory" else "Judah territory",
        aliases=[f"{label} in {anchor}"], summary=f"{label} is named in {anchor}.",
        content_status="draft", review_status="unreviewed", human_review_required=True,
    ).to_dict()
    bootstrap["scripture_references"] = [{"reference": anchor, "relationship": "primary", "notes": "Locked textual identity."}]
    bootstrap["sources"] = source_records
    bootstrap["evidence_items"] = [evidence]
    return bootstrap


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
