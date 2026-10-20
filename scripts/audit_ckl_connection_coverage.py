#!/usr/bin/env python3
"""Export a deterministic, read-only inventory of CKL connection records."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _source_payload(source: Any) -> dict[str, Any]:
    return {
        "id": source.id,
        "title": source.title,
        "author": source.author,
        "publisher": source.publisher,
        "year": source.year,
        "locator": source.locator,
        "url": source.url,
        "source_type": source.source_type,
    }


def _object_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((root / "objects").rglob("*.json")):
        if not path.is_file() or path.name.startswith("_"):
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0")
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        digest.update(b"\0")
    return digest.hexdigest()


def _manifest_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _target_status(target_id: str, target_kind: str, objects: Mapping[str, Any], children: Mapping[str, Any], sources: Mapping[str, Any]) -> str:
    if target_kind == "subject":
        return "resolved_ckl_object" if target_id in objects else "unresolved_ckl_object"
    if target_kind in {"claim", "evidence"}:
        return "resolved_ckl_child" if target_id in children else "unresolved_ckl_child"
    if target_kind == "source":
        return "resolved_source_record" if target_id in sources else "unresolved_source_record"
    if target_kind == "passage":
        return "scripture_anchor_record"
    if target_kind == "historical-period":
        return "period_label_recorded"
    if target_kind in {"geography", "archaeology-item", "archaeology-site", "map-place", "external-dataset"}:
        return "external_target_recorded"
    return "target_recorded_untyped"


def _connection_type(label: str, mapping: Mapping[str, str], normalize: Any) -> str:
    return mapping.get(normalize(label), "uncategorized")


def build_rows(objects: list[Any], edge_fn: Any, connection_map: Mapping[str, str], normalize_id: Any, normalize_label: Any) -> tuple[list[dict[str, str]], dict[str, Any]]:
    object_map = {obj.id: obj for obj in objects}
    child_context: dict[str, tuple[Any, str, Any]] = {}
    source_map: dict[str, Any] = {}
    anchor_map: dict[tuple[str, str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    rows: list[dict[str, str]] = []
    relation_rows: list[dict[str, Any]] = []
    source_reference_ids: set[tuple[str, str]] = set()
    unresolved_sources: set[tuple[str, str]] = set()

    for obj in objects:
        for source in obj.sources:
            source_map[f"{obj.id}#source:{source.id}"] = source
        for claim in obj.claims:
            stable = f"{obj.id}#claim:{claim.id}"
            child_context[stable] = (obj, "claim", claim)
            for reference in claim.scripture_references:
                anchor_map[("passage:" + normalize_id(reference), stable, "supports-claim")].append({"reference": reference, "relationship": "claim-scripture-anchor", "rationale": claim.rationale})
        for evidence in obj.evidence_items:
            stable = f"{obj.id}#evidence:{evidence.id}"
            child_context[stable] = (obj, "evidence", evidence)
            for link in evidence.scripture_references:
                anchor_map[("passage:" + normalize_id(link.reference), obj.id, "evidence-for-subject")].append({"reference": link.reference, "relationship": link.relationship, "temporal_relation": link.temporal_relation, "weight": link.weight, "rationale": link.relevance_rationale, "evidence_id": stable})
                anchor_map[("passage:" + normalize_id(link.reference), stable, link.relationship)].append({"reference": link.reference, "relationship": link.relationship, "temporal_relation": link.temporal_relation, "weight": link.weight, "rationale": link.relevance_rationale, "evidence_id": stable})
        for note in obj.interpretive_notes:
            for reference in note.scripture_references:
                anchor_map[("passage:" + normalize_id(reference), f"{obj.id}#interpretive_note:{hashlib.sha256(note.note.encode()).hexdigest()}", "references-note")].append({"reference": reference, "relationship": "interpretive-note-anchor", "rationale": note.rationale})
        for reference in obj.scripture_references:
            anchor_map[("passage:" + normalize_id(reference.reference), obj.id, "references-subject")].append({"reference": reference.reference, "relationship": reference.relationship, "rationale": reference.notes})
        for source_id in (source.id for source in obj.sources):
            source_reference_ids.add((obj.id, source_id))
        for claim in obj.claims:
            for source_id in claim.source_ids:
                source_reference_ids.add((obj.id, source_id))
                if f"{obj.id}#source:{source_id}" not in source_map:
                    unresolved_sources.add((obj.id, source_id))
        for evidence in obj.evidence_items:
            for source_id in evidence.source_ids:
                source_reference_ids.add((obj.id, source_id))
                if f"{obj.id}#source:{source_id}" not in source_map:
                    unresolved_sources.add((obj.id, source_id))
        for note in obj.interpretive_notes:
            for source_id in note.sources:
                source_reference_ids.add((obj.id, source_id))
                if f"{obj.id}#source:{source_id}" not in source_map:
                    unresolved_sources.add((obj.id, source_id))

    def owner_for(source_id: str, target_id: str) -> tuple[Any | None, str | None, Any | None]:
        if source_id in object_map:
            return object_map[source_id], None, None
        if target_id in object_map:
            return object_map[target_id], None, None
        candidate = child_context.get(source_id) or child_context.get(target_id)
        if candidate:
            return candidate
        for endpoint in (source_id, target_id):
            if "#source:" in endpoint:
                owner_id = endpoint.split("#source:", 1)[0]
                if owner_id in object_map:
                    return object_map[owner_id], "source", source_map.get(endpoint)
        return None, None, None

    def source_refs_for(owner: Any | None, child_kind: str | None, child: Any | None, *, direct_source_id: str = "") -> tuple[list[str], list[dict[str, Any]]]:
        if owner is None:
            return [], []
        if direct_source_id:
            source = source_map.get(direct_source_id)
            source_id = direct_source_id.split("#source:", 1)[-1]
            return [source_id], [_source_payload(source)] if source else []
        if child_kind == "claim":
            ids = list(child.source_ids)
        elif child_kind == "evidence":
            ids = list(child.source_ids)
        else:
            ids = []
        refs = []
        for source_id in ids:
            source = source_map.get(f"{owner.id}#source:{source_id}")
            if source:
                refs.append(_source_payload(source))
        return ids, refs

    def status_payload(owner: Any | None, child_kind: str | None, child: Any | None, target_id: str) -> tuple[str, str]:
        if owner is None:
            return "", "{}"
        review = {"object_review_status": owner.review_status, "content_status": owner.content_status}
        uncertainty: dict[str, Any] = {"object_confidence": owner.confidence}
        if child_kind == "claim":
            uncertainty.update({"claim_certainty": child.certainty, "claim_dispute_status": child.dispute_status})
        elif child_kind == "evidence":
            uncertainty.update({"evidence_confidence": child.confidence, "evidence_certainty": child.certainty, "evidence_dispute_status": child.dispute_status, "assertion_type": child.assertion_type})
        if target_id in object_map:
            review["target_object_review_status"] = object_map[target_id].review_status
            review["target_object_content_status"] = object_map[target_id].content_status
        return _json(uncertainty), _json(review)

    def add_row(row_id: str, group: str, source_id: str, source_kind: str, target_id: str, target_kind: str, label: str, *, rationale: str = "", evidence_ids: list[str] | None = None, source_ids: list[str] | None = None, source_refs: list[dict[str, Any]] | None = None, scope: list[dict[str, Any]] | None = None, scope_basis: str = "not_recorded_on_link", temporal: Any = None, uncertainty: str = "{}", review: str = "", projection_type: str = "not_applicable", target_status: str = "", direction: str = "source_to_target", reverse_id: str = "") -> None:
        rows.append({
            "row_id": row_id,
            "relationship_group": group,
            "source_id": source_id,
            "source_kind": source_kind,
            "target_id": target_id,
            "target_kind": target_kind,
            "relationship_label": label,
            "direction": direction,
            "reverse_edge_id": reverse_id,
            "rationale": rationale,
            "evidence_ids": _json(evidence_ids or []),
            "source_ids": _json(source_ids or []),
            "source_references_json": _json(source_refs or []),
            "passage_scope_json": _json(scope or []),
            "scope_basis": scope_basis,
            "temporal_qualification_json": _json(temporal if temporal is not None else {"status": "not_recorded_on_link"}),
            "uncertainty_json": uncertainty,
            "review_status_json": review,
            "projection_connection_type": projection_type,
            "target_resolution_status": target_status,
        })

    # Use the repository's deterministic graph projection for anchors and the
    # evidence graph, then enrich rows from the same authored CKL fields.
    graph_edges = edge_fn(objects)
    graph_relation_index: dict[tuple[str, str, str], list[int]] = collections.defaultdict(list)
    for index, edge in enumerate(graph_edges):
        if edge.source_kind == "evidence" and edge.target_kind in {"subject", "evidence"}:
            graph_relation_index[(edge.source_id, edge.target_id, edge.relationship)].append(index)
    for index, edge in enumerate(graph_edges):
        owner, child_kind, child = owner_for(edge.source_id, edge.target_id)
        graph_group = "authored_graph_relationship"
        if edge.source_kind == "passage":
            graph_group = "passage_applicability_anchor"
        elif edge.source_kind == "subject" and edge.target_kind in {"claim", "evidence"}:
            graph_group = "nested_record_membership"
        elif edge.source_kind == "claim" and edge.target_kind == "evidence":
            graph_group = "claim_evidence_relationship"
        elif edge.source_kind == "evidence" and edge.target_kind == "source":
            graph_group = "evidence_source_provenance"
        elif edge.source_kind == "evidence" and edge.target_kind == "geography":
            graph_group = "evidence_geography_relationship"
        elif edge.source_kind == "evidence" and edge.target_kind == "historical-period":
            graph_group = "historical_period_relationship"
        elif edge.source_kind == "evidence" and edge.target_kind in {"subject", "evidence"}:
            graph_group = "authored_evidence_relationship"
        elif edge.source_kind == "evidence" and edge.target_kind not in {"source", "geography", "historical-period"}:
            graph_group = "external_evidence_reference"
        scope = anchor_map.get((edge.source_id, edge.target_id, edge.relationship), [])
        evidence_ids: list[str] = []
        if child_kind == "evidence" and child is not None:
            evidence_ids = [f"{owner.id}#evidence:{child.id}"]
        elif edge.target_kind == "evidence" and edge.target_id in child_context:
            evidence_ids = [edge.target_id]
        elif edge.source_kind == "evidence" and edge.source_id in child_context:
            evidence_ids = [edge.source_id]
        source_ids, source_refs = source_refs_for(owner, child_kind, child)
        if edge.target_kind == "source":
            source_id = edge.target_id
            direct_source = source_map.get(source_id)
            local_id = source_id.split("#source:", 1)[-1]
            source_ids = [local_id]
            source_refs = [_source_payload(direct_source)] if direct_source else []
        if graph_group == "passage_applicability_anchor" and not scope:
            scope_basis = "passage_id_from_existing_evidence_graph"
            scope = [{"normalized_passage_id": edge.source_id.removeprefix("passage:"), "relationship": edge.relationship, "rationale": edge.notes}]
        else:
            scope_basis = "authored_scope_metadata" if scope else "not_recorded_on_link"
        if child_kind == "evidence" and child is not None:
            temporal: Any = child.temporal_scope.to_dict()
        elif owner is not None and graph_group != "passage_applicability_anchor":
            temporal = owner.temporal_scope.to_dict()
        else:
            temporal = {"status": "not_recorded_on_link"}
        uncertainty, review = status_payload(owner, child_kind, child, edge.target_id)
        projection_type = _connection_type(edge.relationship, connection_map, normalize_label) if graph_group == "authored_evidence_relationship" else ("passage_anchor" if graph_group == "passage_applicability_anchor" else "not_applicable")
        row_id = f"graph:{index:07d}"
        direction = "passage_to_record" if graph_group == "passage_applicability_anchor" else "source_to_target"
        reverse_id = ""
        if graph_group == "authored_evidence_relationship":
            reverse_indices = graph_relation_index.get((edge.target_id, edge.source_id, edge.relationship), [])
            reverse_index = next((candidate for candidate in reverse_indices if candidate != index), None)
            direction = "reciprocal" if reverse_index is not None else "one_way"
            reverse_id = f"graph:{reverse_index:07d}" if reverse_index is not None else ""
        add_row(
            row_id, graph_group, edge.source_id, edge.source_kind, edge.target_id, edge.target_kind,
            edge.relationship, rationale=edge.notes, evidence_ids=evidence_ids, source_ids=source_ids,
            source_refs=source_refs, scope=scope, scope_basis=scope_basis, temporal=temporal,
            uncertainty=uncertainty, review=review, projection_type=projection_type,
            target_status=_target_status(edge.target_id, edge.target_kind, object_map, child_context, source_map),
            direction=direction, reverse_id=reverse_id,
        )

    # Emit formal object-to-object edges. The schema has no edge-level evidence,
    # citation, temporal or review fields; those remain explicitly unrecorded.
    relation_lookup: dict[tuple[str, str, str], list[str]] = collections.defaultdict(list)
    for obj in objects:
        for index, relation in enumerate(obj.related_objects):
            row_id = f"object:{obj.id}:related_objects:{index:04d}"
            relation_lookup[(obj.id, relation.id, relation.relationship)].append(row_id)
            relation_rows.append({"row_id": row_id, "source_id": obj.id, "target_id": relation.id, "label": relation.relationship, "owner": obj, "child_kind": None, "child": None, "rationale": relation.notes, "group": "authored_object_relationship", "target_kind": "subject"})
    for record in relation_rows:
        reverse_ids = relation_lookup.get((record["target_id"], record["source_id"], record["label"]), [])
        reverse_id = next((candidate for candidate in reverse_ids if candidate != record["row_id"]), "")
        direction = "reciprocal" if reverse_id else "one_way"
        owner = record["owner"]
        source_ids, source_refs = source_refs_for(owner, record["child_kind"], record["child"])
        evidence_ids = [record["source_id"]] if record["child_kind"] == "evidence" else []
        uncertainty, review = status_payload(owner, record["child_kind"], record["child"], record["target_id"])
        temporal = record["child"].temporal_scope.to_dict() if record["child_kind"] == "evidence" else {"status": "not_recorded_on_relationship"}
        add_row(record["row_id"], record["group"], record["source_id"], "evidence" if record["group"] == "authored_evidence_relationship" else "subject", record["target_id"], record["target_kind"], record["label"], rationale=record["rationale"], evidence_ids=evidence_ids, source_ids=source_ids, source_refs=source_refs if record["child_kind"] == "evidence" else [], scope=[], scope_basis="evidence_scope_not_edge_specific" if record["child_kind"] == "evidence" else "not_recorded_on_relationship; see separate passage-anchor rows", temporal=temporal, uncertainty=uncertainty, review=review, projection_type=_connection_type(record["label"], connection_map, normalize_label), target_status=_target_status(record["target_id"], record["target_kind"], object_map, child_context, source_map), direction=direction, reverse_id=reverse_id)

    # Explicit bibliographic relationships stored on objects, claims and notes.
    for obj in objects:
        for note_index, note in enumerate(obj.interpretive_notes):
            note_id = f"{obj.id}#interpretive_note:{hashlib.sha256(note.note.encode()).hexdigest()}"
            for reference_index, reference in enumerate(note.scripture_references):
                add_row(
                    f"anchor:{obj.id}:interpretive_note:{note_index:04d}:{reference_index:04d}",
                    "passage_applicability_anchor", "passage:" + normalize_id(reference), "passage", note_id,
                    "interpretive_note", "interpretive-note-anchor", rationale=note.rationale,
                    scope=[{"reference": reference, "relationship": "references-note", "rationale": note.rationale}],
                    scope_basis="interpretive_note_scripture_reference", temporal={"status": "not_recorded_on_anchor"},
                    uncertainty=_json({"certainty": note.certainty, "dispute_status": note.dispute_status}),
                    review=_json({"object_review_status": obj.review_status, "content_status": obj.content_status}),
                    target_status="resolved_ckl_child", direction="passage_to_record",
                )
        for index, source in enumerate(obj.sources):
            target = f"{obj.id}#source:{source.id}"
            uncertainty, review = status_payload(obj, None, None, target)
            add_row(f"source:{obj.id}:object:{index:04d}", "object_source_reference", obj.id, "subject", target, "source", "object-source-reference", source_ids=[source.id], source_refs=[_source_payload(source)], uncertainty=uncertainty, review=review, target_status="resolved_source_record", direction="source_to_target")
        for claim in obj.claims:
            source_stable = f"{obj.id}#claim:{claim.id}"
            uncertainty, review = status_payload(obj, "claim", claim, "")
            for index, source_id in enumerate(claim.source_ids):
                source = source_map.get(f"{obj.id}#source:{source_id}")
                add_row(f"source:{obj.id}:claim:{claim.id}:{index:04d}", "claim_source_provenance", source_stable, "claim", f"{obj.id}#source:{source_id}", "source", "supported-by-source", rationale=claim.rationale or claim.notes, source_ids=[source_id], source_refs=[_source_payload(source)] if source else [], uncertainty=uncertainty, review=review, target_status="resolved_source_record" if source else "unresolved_source_record", direction="source_to_target")
        for index, note in enumerate(obj.interpretive_notes):
            note_stable = f"{obj.id}#interpretive_note:{hashlib.sha256(note.note.encode()).hexdigest()}"
            uncertainty, review = status_payload(obj, None, None, "")
            for source_index, source_id in enumerate(note.sources):
                source = source_map.get(f"{obj.id}#source:{source_id}")
                add_row(f"source:{obj.id}:interpretive_note:{index:04d}:{source_index:04d}", "interpretive_note_source_provenance", note_stable, "interpretive_note", f"{obj.id}#source:{source_id}", "source", "supported-by-source", rationale=note.rationale, source_ids=[source_id], source_refs=[_source_payload(source)] if source else [], uncertainty=_json({"certainty": note.certainty, "dispute_status": note.dispute_status}), review=review, target_status="resolved_source_record" if source else "unresolved_source_record", direction="source_to_target")

    # Preserve authored person/place/event identifiers and historical-period
    # links that are stored outside the general related_objects list.
    entity_fields = {
        "related_people": "person", "key_people": "person",
        "related_places": "place", "key_places": "place",
        "related_events": "event", "key_events": "event",
        "related_entries": "ckl_object", "timeline": "historical_period_or_event",
        "maps": "map_place", "archaeology": "archaeology_record",
    }
    from framework.canonical_library.normalization import normalize_id
    for obj in objects:
        for field_name, target_kind in entity_fields.items():
            for index, target_value in enumerate(getattr(obj, field_name, []) or []):
                normalized = normalize_id(str(target_value))
                is_object_id = normalized in object_map
                status = "resolved_ckl_object" if is_object_id else "descriptive_domain_value_recorded"
                resolved_kind = target_kind if is_object_id else "authored_field_value"
                add_row(f"field:{obj.id}:{field_name}:{index:04d}", "authored_entity_or_domain_reference", obj.id, "subject", str(target_value), resolved_kind, field_name.replace("_", "-"), rationale="field-level association; value does not encode a claim/evidence edge" if is_object_id else "authored field value retained as descriptive text; not a CKL object ID", target_status=status, uncertainty=_json({"object_confidence": obj.confidence}), review=_json({"object_review_status": obj.review_status, "content_status": obj.content_status}), direction="source_to_target")
        for index, period in enumerate(obj.temporal_scope.periods):
            add_row(f"period:{obj.id}:temporal_scope:{index:04d}", "historical_period_relationship", obj.id, "subject", "period:" + normalize_id(period), "historical-period", "dated-to", rationale=obj.temporal_scope.notes, temporal=obj.temporal_scope.to_dict(), uncertainty=_json({"object_confidence": obj.confidence}), review=_json({"object_review_status": obj.review_status, "content_status": obj.content_status}), target_status="period_label_recorded", direction="source_to_target")
        story = obj.canonical_story if isinstance(obj.canonical_story, dict) else {}
        for story_field, label in (("preceded_by", "preceded-by"), ("followed_by", "followed-by")):
            for index, target in enumerate(story.get(story_field, []) or []):
                is_object_id = str(target) in object_map
                status = "resolved_ckl_object" if is_object_id else "descriptive_sequence_value_recorded"
                target_kind = "subject" if is_object_id else "sequence_label"
                add_row(f"story:{obj.id}:{story_field}:{index:04d}", "canonical_story_sequence_metadata", obj.id, "subject", str(target), target_kind, label, rationale=story.get("role", ""), target_status=status, uncertainty=_json({"object_confidence": obj.confidence}), review=_json({"object_review_status": obj.review_status, "content_status": obj.content_status}), direction="source_to_target")
        for evidence in obj.evidence_items:
            source_stable = f"{obj.id}#evidence:{evidence.id}"
            for index, target in enumerate(evidence.evidence_targets):
                if getattr(target, "kind", "") == "entity":
                    target_id = target.entity_id
                    target_kind = target.relationship
                    status = "resolved_ckl_object" if target_id in object_map else "unresolved_ckl_object_or_external_entity"
                else:
                    target_id = _json(target.to_dict())
                    target_kind = target.value_type
                    status = "typed_value_target_recorded"
                uncertainty, review = status_payload(obj, "evidence", evidence, target_id)
                add_row(f"target:{obj.id}:{evidence.id}:{index:04d}", "evidence_typed_target", source_stable, "evidence", target_id, target_kind, target.relationship, rationale=evidence.passage_relevance, evidence_ids=[source_stable], source_ids=list(evidence.source_ids), source_refs=[_source_payload(source_map[f"{obj.id}#source:{source_id}"]) for source_id in evidence.source_ids if f"{obj.id}#source:{source_id}" in source_map], scope=[{"reference": link.reference, "relationship": link.relationship, "temporal_relation": link.temporal_relation, "rationale": link.relevance_rationale} for link in evidence.scripture_references], scope_basis="evidence_record_scope_not_target_specific", temporal=evidence.temporal_scope.to_dict(), uncertainty=uncertainty, review=review, target_status=status, direction="source_to_target")

    rows.sort(key=lambda row: row["row_id"])
    frequencies = collections.Counter(row["relationship_group"] for row in rows)
    authored_object_edges = [row for row in rows if row["relationship_group"] == "authored_object_relationship"]
    mapped_edges = collections.Counter(row["projection_connection_type"] for row in authored_object_edges)
    exact_pairs: set[tuple[str, str, str]] = set()
    for row in authored_object_edges:
        reverse = (row["target_id"], row["source_id"], row["relationship_label"])
        if any((candidate["source_id"], candidate["target_id"], candidate["relationship_label"]) == reverse for candidate in authored_object_edges):
            key = tuple(sorted((row["source_id"], row["target_id"])) + [row["relationship_label"]])
            exact_pairs.add(key)
    return rows, {
        "inventory_row_count": len(rows),
        "relationship_group_counts": dict(sorted(frequencies.items())),
        "source_id_reference_count": len(source_reference_ids),
        "unique_source_ids_referenced": len({source_id for _, source_id in source_reference_ids}),
        "unresolved_source_id_reference_count": len(unresolved_sources),
        "unresolved_source_id_references": [{"object_id": object_id, "source_id": source_id} for object_id, source_id in sorted(unresolved_sources)],
        "authored_object_relationship_count": len(authored_object_edges),
        "authored_object_label_count": len({row["relationship_label"] for row in authored_object_edges}),
        "authored_object_projection_type_counts": dict(sorted(mapped_edges.items())),
        "authored_object_reciprocal_pairs": len(exact_pairs),
        "authored_object_reciprocal_edges": sum(1 for row in authored_object_edges if row["direction"] == "reciprocal"),
        "authored_object_one_way_edges": sum(1 for row in authored_object_edges if row["direction"] == "one_way"),
        "object_relationships_without_edge_rationale": sum(1 for row in authored_object_edges if not row["rationale"]),
    }


def validate_rows(rows: list[dict[str, str]], metrics: Mapping[str, Any]) -> None:
    """Check inventory invariants without changing the source library."""
    if len(rows) != metrics["inventory_row_count"]:
        raise ValueError("inventory row count does not match computed metrics")
    row_ids = [row["row_id"] for row in rows]
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("inventory row IDs are not unique")
    groups = collections.Counter(row["relationship_group"] for row in rows)
    if sum(groups.values()) != len(rows):
        raise ValueError("relationship group totals do not sum to inventory row count")

    for group, expected in (
        ("authored_object_relationship", metrics["authored_object_relationship_count"]),
        ("authored_evidence_relationship", groups["authored_evidence_relationship"]),
    ):
        edges = [row for row in rows if row["relationship_group"] == group]
        if len(edges) != expected:
            raise ValueError(f"{group} count does not match expected count")
        directions = collections.Counter(row["direction"] for row in edges)
        if directions["one_way"] + directions["reciprocal"] != len(edges):
            raise ValueError(f"{group} direction counts do not cover every edge")
        reciprocal_edges = [row for row in edges if row["direction"] == "reciprocal"]
        by_id = {row["row_id"]: row for row in edges}
        for row in reciprocal_edges:
            reverse = by_id.get(row["reverse_edge_id"])
            if reverse is None or reverse["source_id"] != row["target_id"] or reverse["target_id"] != row["source_id"] or reverse["relationship_label"] != row["relationship_label"]:
                raise ValueError(f"{group} reciprocal edge has an invalid reverse reference")
        if len(reciprocal_edges) % 2:
            raise ValueError(f"{group} reciprocal edge count is not an even number")

    object_edges = [row for row in rows if row["relationship_group"] == "authored_object_relationship"]
    if sum(metrics["authored_object_projection_type_counts"].values()) != len(object_edges):
        raise ValueError("top-level projection type counts do not sum to relationship count")
    anchors = [row for row in rows if row["relationship_group"] == "passage_applicability_anchor"]
    if any(row["source_kind"] != "passage" for row in anchors):
        raise ValueError("passage applicability row lacks a passage source")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="Full source checkout containing framework/canonical_library")
    parser.add_argument("--output", type=Path, required=True, help="CSV destination; source files are never written")
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    sys.path.insert(0, str(source_root))
    from framework.canonical_library.evidence_graph import evidence_graph_edges
    from framework.canonical_library.loader import CanonicalLibrary
    from framework.canonical_library.normalization import normalize_id
    from bhf_agent.presentation.narrative_explorer import _CONNECTION_TYPE_BY_LABEL, _normalized_label

    ckl_root = source_root / "framework" / "canonical_library"
    library = CanonicalLibrary(root=ckl_root).load()
    objects = [library.objects_by_id[key] for key in sorted(library.objects_by_id)]
    declared = int(library.manifest.get("object_count", -1))
    if len(objects) != declared:
        raise SystemExit(f"CKL object count mismatch: loaded={len(objects)} manifest={declared}")
    rows, metrics = build_rows(objects, evidence_graph_edges, _CONNECTION_TYPE_BY_LABEL, normalize_id, _normalized_label)
    validate_rows(rows, metrics)
    fields = list(rows[0]) if rows else []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    written_rows = 0
    written_ids: set[str] = set()
    with args.output.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            written_rows += 1
            if row["row_id"] in written_ids:
                raise ValueError("written CSV contains duplicate row IDs")
            written_ids.add(row["row_id"])
    if written_rows != len(rows):
        raise ValueError("written CSV row count differs from validated inventory")
    manifest = ckl_root / "manifest.json"
    summary = {
        "object_count": len(objects),
        "manifest_object_count": declared,
        "object_type_counts": dict(sorted(collections.Counter(obj.type for obj in objects).items())),
        "ckl_inventory_fingerprint": library.inventory_fingerprint(),
        "object_source_tree_sha256": _object_fingerprint(ckl_root),
        "manifest_sha256": _manifest_hash(manifest),
        "csv_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "csv_bytes": args.output.stat().st_size,
        "validation_status": "passed",
        **metrics,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
