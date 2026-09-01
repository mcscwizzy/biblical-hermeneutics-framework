"""Normalize passage-scoped CKL, map, and archaeology data into EvidenceBundle V1."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable, Mapping, Sequence

from .evidence_normalization import (
    ENTITY_BUCKET_BY_TYPE as _ENTITY_BUCKET_BY_TYPE,
    LEGACY_FIELDS as _LEGACY_FIELDS,
    certainty_confidence as _certainty_confidence,
    confidence as _confidence,
    evidence_category as _category,
    normalize_geography as _normalize_geography,
    number as _float,
    sequence as _sequence,
    strings as _strings,
    text as _text,
    unique as _unique,
)
from .evidence_hash import calculate_evidence_hash
from .eligibility import (
    canonical_object_anchors,
    is_canonical_object_passage_eligible,
    passage_matching_scripture_anchors,
    scripture_anchors,
)
from .models import EVIDENCE_BUNDLE_VERSION, EntityRef, EvidenceBundle, EvidenceItem, mapping
from .references import anchor_specificity, reference_distance, references_overlap


def build_evidence_bundle(
    passage_ref: str,
    *,
    canonical_results: Sequence[Any] = (),
    geography: Mapping[str, Any] | None = None,
    archaeology: Sequence[Mapping[str, Any]] = (),
) -> EvidenceBundle:
    """Build a stable, UI/model-independent record of passage knowledge.

    Only explicitly overlapping Scripture anchors (or passage-indexed map and
    archaeology records supplied by their resolvers) enter the bundle. This is
    the primary boundary that prevents broad retrieval tags from leaking
    unrelated entities into a passage presentation.
    """

    normalized_reference = " ".join(str(passage_ref or "").split())
    if not normalized_reference:
        raise ValueError("passage_ref is required")

    entities: dict[str, dict[str, EntityRef]] = {
        bucket: {} for bucket in ("people", "places", "groups", "events", "artifacts")
    }
    evidence: dict[str, EvidenceItem] = {}
    sources: dict[str, dict[str, Any]] = {}
    object_provenance: list[dict[str, Any]] = []

    prepared_objects: list[tuple[dict[str, Any], float]] = []
    for result in canonical_results:
        raw_object = getattr(result, "object", result)
        data = mapping(raw_object)
        if not data:
            continue
        score = _float(getattr(result, "score", None), default=0.0)
        prepared_objects.append((data, score))

        object_id = _text(data.get("id"))
        eligible = is_canonical_object_passage_eligible(normalized_reference, data)
        bucket = _ENTITY_BUCKET_BY_TYPE.get(_text(data.get("type")).casefold())
        if bucket and eligible and object_id:
            entities[bucket][object_id] = _entity_from_object(data, score)

        if object_id:
            object_provenance.append(
                {
                    "id": object_id,
                    "type": _text(data.get("type")),
                    "title": _text(data.get("title")),
                    "object_version": _text(data.get("object_version")),
                    "review_status": _text(data.get("review_status")),
                    "retrieval_score": score,
                }
            )
            _register_object_sources(data, sources)

    normalized_geography = _normalize_geography(geography or {})
    for place in normalized_geography["places"]:
        place_id = _text(place.get("id"))
        if place_id:
            entities["places"].setdefault(
                place_id,
                EntityRef(
                    id=place_id,
                    title=_text(place.get("title") or place.get("name") or place_id),
                    type="place",
                    aliases=_strings(place.get("ancient_names") or place.get("aliases")),
                    metadata={key: value for key, value in place.items() if key not in {"id", "title", "name", "aliases"}},
                ),
            )

    for kind in ("place", "route"):
        bucket = "places" if kind == "place" else "routes"
        for record in normalized_geography[bucket]:
            _append_geography_evidence(
                normalized_reference,
                record,
                kind=kind,
                evidence=evidence,
                sources=sources,
            )

    for record in archaeology:
        record_data = mapping(record)
        record_id = _text(record_data.get("record_id") or record_data.get("id"))
        if not record_id:
            continue
        entities["artifacts"].setdefault(
            record_id,
            EntityRef(
                id=record_id,
                title=_text(record_data.get("title") or record_id),
                type="artifact",
                metadata={
                    key: record_data[key]
                    for key in ("period", "place_id", "site_id", "kind")
                    if record_data.get(key) not in (None, "")
                },
            ),
        )
        source_ids = _archaeology_source_ids(record_data, record_id, sources)
        claim = _text(record_data.get("summary") or record_data.get("description"))
        if claim:
            archaeology_metadata = {
                "source_kind": "archaeology_resolver",
                "passage_relationship": "direct",
                "anchor_specificity": anchor_specificity(normalized_reference),
                "verse_distance": 0,
                "exploration_potential": 1.0,
                "presentation_role": "significance",
                "interpretive_caution": _text(record_data.get("caution")),
            }
            _add_evidence(
                evidence,
                EvidenceItem(
                    id=record_id,
                    claim=claim,
                    category="archaeology",
                    source_ids=source_ids,
                    related_entity_ids=_unique([record_id, _text(record_data.get("place_id") or record_data.get("site_id"))]),
                    passage_anchors=[normalized_reference],
                    confidence=_confidence(record_data.get("confidence")),
                    relevance_metadata=archaeology_metadata,
                ),
            )

    known_entity_ids = {
        entity_id for bucket in entities.values() for entity_id in bucket
    }
    for data, retrieval_score in prepared_objects:
        _append_object_evidence(
            normalized_reference,
            data,
            retrieval_score,
            known_entity_ids,
            evidence,
            sources,
        )

    for item in evidence.values():
        for source_id in item.source_ids:
            sources.setdefault(
                source_id,
                {
                    "id": source_id,
                    "title": source_id,
                    "source_type": "unresolved-source-reference",
                },
            )

    contributing_object_ids = {
        str(item.relevance_metadata.get("parent_object_id") or "")
        for item in evidence.values()
    }
    contributing_object_ids.update(
        entity.id
        for bucket in entities.values()
        for entity in bucket.values()
    )
    contributing_object_ids.discard("")
    referenced_source_ids = {
        source_id for item in evidence.values() for source_id in item.source_ids
    }
    contributing_sources: dict[str, dict[str, Any]] = {}
    for data, _score in prepared_objects:
        if _text(data.get("id")) in contributing_object_ids:
            _register_object_sources(data, contributing_sources)
    normalized_sources = {
        source_id: (
            contributing_sources[source_id]
            if source_id in contributing_sources
            else sources[source_id]
        )
        for source_id in referenced_source_ids
        if source_id in contributing_sources or source_id in sources
    }
    bundle = EvidenceBundle(
        passage_ref=normalized_reference,
        entities={
            bucket: sorted(values.values(), key=lambda item: (item.title.casefold(), item.id))
            for bucket, values in entities.items()
        },
        evidence_items=sorted(evidence.values(), key=lambda item: item.id),
        geography=normalized_geography,
        provenance={
            "sources": sorted(
                (
                    source
                    for source_id, source in normalized_sources.items()
                ),
                key=lambda item: _text(item.get("id")),
            ),
            "canonical_objects": sorted(
                (
                    item
                    for item in object_provenance
                    if item["id"] in contributing_object_ids
                ),
                key=lambda item: item["id"],
            ),
            "resolvers": ["canonical_knowledge_library", "passage_maps", "archaeology"],
        },
        version=EVIDENCE_BUNDLE_VERSION,
    )
    return replace(bundle, evidence_hash=calculate_evidence_hash(bundle))


def _append_geography_evidence(
    passage_ref: str,
    record: Mapping[str, Any],
    *,
    kind: str,
    evidence: dict[str, EvidenceItem],
    sources: dict[str, dict[str, Any]],
) -> None:
    """Turn a passage-indexed map summary into source-addressable evidence."""

    record_id = _text(record.get("id"))
    claim = _text(record.get("summary") or record.get("description"))
    if not record_id or not claim:
        return
    source_id = f"passage-map:{record_id}"
    source = {
        "id": source_id,
        "title": _text(record.get("source_name")) or "BHF passage map catalog",
        "source_type": "map-dataset",
        "resource_id": record_id,
    }
    source_url = _text(record.get("source_url"))
    if source_url:
        source["url"] = source_url
    sources[source_id] = source
    relationship = _text(record.get("relationship")).casefold().replace("_", "-")
    _add_evidence(
        evidence,
        EvidenceItem(
            id=f"map-{kind}:{record_id}",
            claim=claim,
            category="geography",
            source_ids=[source_id],
            related_entity_ids=[record_id] if kind == "place" else [],
            passage_anchors=[passage_ref],
            confidence=_confidence(record.get("confidence")),
            relevance_metadata={
                "source_kind": f"passage_map_{kind}",
                "passage_relationship": "direct",
                "map_resource_kind": kind,
                "map_resource_id": record_id,
                "map_relationship": relationship or "passage-map-link",
                "anchor_specificity": anchor_specificity(passage_ref),
                "verse_distance": 0,
                "exploration_potential": 1.0,
            },
        ),
    )
def _append_object_evidence(
    passage_ref: str,
    data: dict[str, Any],
    retrieval_score: float,
    known_entity_ids: set[str],
    evidence: dict[str, EvidenceItem],
    sources: dict[str, dict[str, Any]],
) -> None:
    object_id = _text(data.get("id"))
    if not object_id:
        return
    parent_anchors = _object_anchors(data)
    parent_sources = _source_ids(data) or [_internal_source(object_id, data, sources)]
    parent_confidence = _confidence(data.get("confidence"))
    linked_claims: set[str] = set()
    added = 0

    for raw in _sequence(data.get("evidence_items")):
        item = mapping(raw)
        item_id = _text(item.get("id"))
        if not item_id:
            continue
        declared_anchors = _evidence_anchors(item)
        anchors = declared_anchors or parent_anchors
        matched = (
            passage_matching_scripture_anchors(passage_ref, item)
            if declared_anchors
            else [anchor for anchor in anchors if references_overlap(passage_ref, anchor)]
        )
        if not matched:
            continue
        linked_claims.update(_strings(item.get("claim_ids")))
        related = [
            _text(value.get("id"))
            for value in (mapping(entry) for entry in _sequence(item.get("related_objects")))
        ]
        related.extend(_strings(item.get("geography_ids")))
        related.extend(
            _text(value.get("id"))
            for value in (mapping(entry) for entry in _sequence(item.get("external_references")))
        )
        if object_id in known_entity_ids:
            related.append(object_id)
        metadata = _relevance_metadata(
            passage_ref,
            matched,
            source_kind="ckl_evidence_item",
            data=data,
            item=item,
            retrieval_score=retrieval_score,
        )
        _add_evidence(
            evidence,
            EvidenceItem(
                id=item_id,
                claim=_text(item.get("description") or item.get("primary_observation")),
                category=_category(
                    item.get("evidence_type"),
                    _text(item.get("description") or item.get("primary_observation")),
                ),
                source_ids=_strings(item.get("source_ids")) or parent_sources,
                related_entity_ids=[value for value in _unique(related) if value in known_entity_ids],
                passage_anchors=_unique(matched),
                confidence=_confidence(item.get("confidence") or parent_confidence),
                relevance_metadata=metadata,
            ),
        )
        passage_relevance = _text(item.get("passage_relevance"))
        if passage_relevance and passage_relevance != _text(
            item.get("description") or item.get("primary_observation")
        ):
            significance_metadata = dict(metadata)
            significance_metadata.update(
                {
                    "presentation_role": "significance",
                    "supports_evidence_ids": [item_id],
                }
            )
            _add_evidence(
                evidence,
                EvidenceItem(
                    id=f"{item_id}:passage-relevance",
                    claim=passage_relevance,
                    category=_category(
                        item.get("evidence_type"),
                        _text(item.get("description") or item.get("primary_observation")),
                    ),
                    source_ids=_strings(item.get("source_ids")) or parent_sources,
                    related_entity_ids=[
                        value for value in _unique(related) if value in known_entity_ids
                    ],
                    passage_anchors=_unique(matched),
                    confidence=_confidence(item.get("confidence") or parent_confidence),
                    relevance_metadata=significance_metadata,
                ),
            )
        added += 1

    for raw in _sequence(data.get("claims")):
        claim = mapping(raw)
        claim_id = _text(claim.get("id") or claim.get("claim_id"))
        if not claim_id or claim_id in linked_claims:
            continue
        declared_anchors = _strings(claim.get("scripture_references"))
        anchors = declared_anchors or parent_anchors
        matched = (
            passage_matching_scripture_anchors(passage_ref, claim)
            if declared_anchors
            else [anchor for anchor in anchors if references_overlap(passage_ref, anchor)]
        )
        if not matched:
            continue
        related = [object_id] if object_id in known_entity_ids else []
        _add_evidence(
            evidence,
            EvidenceItem(
                id=claim_id,
                claim=_text(claim.get("claim") or claim.get("claim_text")),
                category=_category(claim.get("claim_type"), _text(claim.get("claim") or claim.get("claim_text"))),
                source_ids=_strings(claim.get("source_ids")) or parent_sources,
                related_entity_ids=related,
                passage_anchors=_unique(matched),
                confidence=_certainty_confidence(claim.get("certainty"), parent_confidence),
                relevance_metadata=_relevance_metadata(
                    passage_ref,
                    matched,
                    source_kind="ckl_claim",
                    data=data,
                    item=claim,
                    retrieval_score=retrieval_score,
                ),
            ),
        )
        added += 1

    # Older CKL records do not all have claim-level evidence yet. Preserve a
    # narrow, source-addressable bridge without turning the entire object into
    # commentary prose.
    if added == 0:
        matched_parent = [anchor for anchor in parent_anchors if references_overlap(passage_ref, anchor)]
        if not matched_parent:
            return
        for field_name, category in _LEGACY_FIELDS.items():
            for index, value in enumerate(_sequence(data.get(field_name))):
                claim_text = _text(value)
                if not claim_text:
                    continue
                _add_evidence(
                    evidence,
                    EvidenceItem(
                        id=f"{object_id}:{field_name}:{index}",
                        claim=claim_text,
                        category=category,
                        source_ids=parent_sources,
                        related_entity_ids=[object_id] if object_id in known_entity_ids else [],
                        passage_anchors=_unique(matched_parent),
                        confidence=parent_confidence,
                        relevance_metadata=_legacy_relevance_metadata(
                            passage_ref,
                            matched_parent,
                            data=data,
                            field_name=field_name,
                            retrieval_score=retrieval_score,
                        ),
                    ),
                )


def _relevance_metadata(
    passage_ref: str,
    anchors: list[str],
    *,
    source_kind: str,
    data: Mapping[str, Any],
    item: Mapping[str, Any],
    retrieval_score: float,
) -> dict[str, Any]:
    distances = [reference_distance(passage_ref, anchor) for anchor in anchors]
    numeric_distances = [distance for distance in distances if distance is not None]
    specificities = [anchor_specificity(anchor) for anchor in anchors]
    relationship = _strongest_relationship(item)
    return {
        "source_kind": source_kind,
        "parent_object_id": _text(data.get("id")),
        "parent_title": _text(data.get("title")),
        "parent_type": _text(data.get("type")),
        "object_importance": int(_float(data.get("importance"), default=0.0)),
        "retrieval_score": round(retrieval_score, 4),
        "passage_relationship": relationship,
        "anchor_specificity": _strongest_specificity(specificities),
        "verse_distance": min(numeric_distances) if numeric_distances else None,
        "certainty": _text(item.get("certainty")),
        "dispute_status": _text(item.get("dispute_status")),
        "assertion_type": _text(item.get("assertion_type")),
        "exploration_potential": _exploration_potential(item, data),
        "broad_tag_only": False,
    }


def _legacy_relevance_metadata(
    passage_ref: str,
    anchors: list[str],
    *,
    data: Mapping[str, Any],
    field_name: str,
    retrieval_score: float,
) -> dict[str, Any]:
    metadata = _relevance_metadata(
        passage_ref,
        anchors,
        source_kind="ckl_legacy_field",
        data=data,
        item={"field": field_name},
        retrieval_score=retrieval_score,
    )
    if _text(data.get("type")).casefold() == "book":
        metadata["passage_relationship"] = "background"
        metadata["broad_tag_only"] = True
    return metadata


def _object_anchors(data: Mapping[str, Any]) -> list[str]:
    return canonical_object_anchors(data)


def _evidence_anchors(data: Mapping[str, Any]) -> list[str]:
    return scripture_anchors(data)


def _register_object_sources(data: Mapping[str, Any], target: dict[str, dict[str, Any]]) -> None:
    object_id = _text(data.get("id"))
    for raw in _sequence(data.get("sources")):
        source = mapping(raw)
        source_id = _text(source.get("id") or source.get("source_id"))
        if not source_id:
            continue
        if source_id not in target:
            normalized = dict(source)
            normalized["id"] = source_id
            normalized["canonical_object_ids"] = []
            target[source_id] = normalized
        canonical_ids = target[source_id].setdefault("canonical_object_ids", [])
        if object_id and object_id not in canonical_ids:
            canonical_ids.append(object_id)
            canonical_ids.sort()


def _internal_source(object_id: str, data: Mapping[str, Any], target: dict[str, dict[str, Any]]) -> str:
    source_id = f"ckl:{object_id}"
    target.setdefault(
        source_id,
        {
            "id": source_id,
            "title": _text(data.get("title") or object_id),
            "source_type": "canonical-knowledge-record",
            "canonical_object_ids": [object_id],
        },
    )
    return source_id


def _source_ids(data: Mapping[str, Any]) -> list[str]:
    return _unique(
        _text(mapping(value).get("id") or mapping(value).get("source_id"))
        for value in _sequence(data.get("sources"))
    )


def _archaeology_source_ids(
    data: Mapping[str, Any],
    record_id: str,
    target: dict[str, dict[str, Any]],
) -> list[str]:
    source = mapping(data.get("source"))
    source_id = _text(source.get("id") or source.get("source_id"))
    if source_id:
        normalized = dict(source)
        normalized["id"] = source_id
        target.setdefault(source_id, normalized)
        return [source_id]
    source_id = f"archaeology:{record_id}"
    target.setdefault(
        source_id,
        {
            "id": source_id,
            "title": _text(source.get("label") or data.get("title") or record_id),
            "source_type": "archaeology-record",
            "record_id": record_id,
        },
    )
    return [source_id]


def _entity_from_object(data: Mapping[str, Any], score: float) -> EntityRef:
    return EntityRef(
        id=_text(data.get("id")),
        title=_text(data.get("title") or data.get("id")),
        type=_text(data.get("type")),
        aliases=_strings(data.get("aliases")),
        metadata={
            "summary": _text(data.get("summary")),
            "importance": int(_float(data.get("importance"), default=0.0)),
            "retrieval_score": score,
            "ancient_names": _strings(data.get("ancient_names")),
            "modern_identification": _text(data.get("modern_identification")),
            "region": _text(data.get("region")),
            "terrain": _text(data.get("terrain")),
            "elevation": data.get("elevation"),
            "archaeology": _strings(data.get("archaeology")),
            "related_passages": _object_anchors(data),
        },
    )


def _strongest_relationship(item: Mapping[str, Any]) -> str:
    relationships = [
        _text(mapping(value).get("relationship"))
        for value in _sequence(item.get("scripture_references"))
    ]
    for candidate in ("direct", "primary", "contextual", "supporting", "background", "comparative", "disputed"):
        if candidate in relationships:
            return candidate
    return "direct" if relationships else "contextual"


def _strongest_specificity(values: Iterable[str]) -> str:
    collected = list(values)
    for value in ("verse", "chapter", "book", "unknown"):
        if value in collected:
            return value
    return "unknown"


def _exploration_potential(item: Mapping[str, Any], parent: Mapping[str, Any]) -> float:
    score = 0.25
    if _sequence(item.get("related_objects")):
        score += 0.25
    if _sequence(item.get("external_references")):
        score += 0.25
    if _sequence(item.get("geography_ids")) or _text(parent.get("type")) == "place":
        score += 0.25
    return min(score, 1.0)


def _add_evidence(target: dict[str, EvidenceItem], item: EvidenceItem) -> None:
    if not item.id or not item.claim or item.id in target:
        return
    target[item.id] = item
