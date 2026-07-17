"""Graph helpers for CKL relationship hygiene."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

from .normalization import normalize_id
from .schema import CanonicalObject, CanonicalRelationship


INVERSE_RELATIONSHIPS: dict[str, str] = {
    "related": "related",
    "related-theme": "related-theme",
    "related-person": "related-person",
    "related-place": "related-place",
    "related-event": "related-event",
    "related-book": "related-book",
    "context-for": "has-context",
    "has-context": "context-for",
    "part-of": "contains",
    "contains": "part-of",
    "fulfilled-by": "fulfills",
    "fulfills": "fulfilled-by",
    "typologically-related": "typologically-related",
    "background-for": "has-background",
    "has-background": "background-for",
    "quoted-by": "quotes",
    "quotes": "quoted-by",
    "alluded-to-by": "alludes-to",
    "alludes-to": "alluded-to-by",
}


@dataclass(frozen=True)
class GraphEdge:
    source_id: str
    target_id: str
    relationship: str
    weight: int = 1
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "weight": self.weight,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ReverseRelationshipSuggestion:
    source_id: str
    target_id: str
    relationship: str
    suggested_relationship: str
    weight: int
    notes: str

    def to_relationship(self) -> CanonicalRelationship:
        return CanonicalRelationship(
            id=self.source_id,
            relationship=self.suggested_relationship,
            weight=self.weight,
            notes=self.notes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "suggested_relationship": self.suggested_relationship,
            "weight": self.weight,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CKLGraphAudit:
    object_count: int
    edge_count: int
    missing_reverse_edges: list[ReverseRelationshipSuggestion]
    orphaned_object_ids: list[str]
    unknown_target_edges: list[GraphEdge]

    @property
    def has_orphans(self) -> bool:
        return bool(self.orphaned_object_ids)

    @property
    def has_missing_reverse_edges(self) -> bool:
        return bool(self.missing_reverse_edges)

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_count": self.object_count,
            "edge_count": self.edge_count,
            "missing_reverse_edges": [
                suggestion.to_dict() for suggestion in self.missing_reverse_edges
            ],
            "orphaned_object_ids": list(self.orphaned_object_ids),
            "unknown_target_edges": [edge.to_dict() for edge in self.unknown_target_edges],
        }


def graph_audit(objects: Iterable[CanonicalObject] | Mapping[str, CanonicalObject]) -> CKLGraphAudit:
    object_map = _object_map(objects)
    edges = relationship_edges(object_map.values())
    known_ids = set(object_map)
    unknown_edges = [edge for edge in edges if edge.target_id not in known_ids]
    known_edges = [edge for edge in edges if edge.target_id in known_ids]
    missing_reverse = missing_reverse_relationships(object_map)
    connected_ids: set[str] = set()
    for edge in known_edges:
        connected_ids.add(edge.source_id)
        connected_ids.add(edge.target_id)
    orphaned = sorted(known_ids - connected_ids)
    return CKLGraphAudit(
        object_count=len(object_map),
        edge_count=len(edges),
        missing_reverse_edges=missing_reverse,
        orphaned_object_ids=orphaned,
        unknown_target_edges=unknown_edges,
    )


def relationship_edges(objects: Iterable[CanonicalObject]) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    for obj in objects:
        source_id = normalize_id(obj.id)
        for relationship in obj.related_objects:
            target_id = normalize_id(relationship.id)
            if not target_id:
                continue
            edges.append(
                GraphEdge(
                    source_id=source_id,
                    target_id=target_id,
                    relationship=normalize_id(relationship.relationship) or "related",
                    weight=relationship.weight,
                    notes=relationship.notes,
                )
            )
    return edges


def missing_reverse_relationships(
    objects: Iterable[CanonicalObject] | Mapping[str, CanonicalObject],
) -> list[ReverseRelationshipSuggestion]:
    object_map = _object_map(objects)
    existing = {
        (edge.source_id, edge.target_id, edge.relationship)
        for edge in relationship_edges(object_map.values())
    }
    suggestions: list[ReverseRelationshipSuggestion] = []
    seen: set[tuple[str, str, str]] = set()
    for edge in relationship_edges(object_map.values()):
        if edge.target_id not in object_map:
            continue
        inverse = inverse_relationship(edge.relationship)
        key = (edge.target_id, edge.source_id, inverse)
        if key in existing or key in seen:
            continue
        suggestions.append(
            ReverseRelationshipSuggestion(
                source_id=edge.source_id,
                target_id=edge.target_id,
                relationship=edge.relationship,
                suggested_relationship=inverse,
                weight=edge.weight,
                notes=f"Auto-generated reverse edge for {edge.source_id} -> {edge.target_id}.",
            )
        )
        seen.add(key)
    return suggestions


def with_bidirectional_relationships(
    objects: Sequence[CanonicalObject],
) -> list[CanonicalObject]:
    object_map = _object_map(objects)
    additions: dict[str, list[CanonicalRelationship]] = {object_id: [] for object_id in object_map}
    for suggestion in missing_reverse_relationships(object_map):
        additions[suggestion.target_id].append(suggestion.to_relationship())

    updated: list[CanonicalObject] = []
    for obj in objects:
        extra = additions.get(obj.id, [])
        if not extra:
            updated.append(obj)
            continue
        updated.append(replace(obj, related_objects=[*obj.related_objects, *extra]))
    return updated


def inverse_relationship(relationship: str) -> str:
    normalized = normalize_id(relationship) or "related"
    return INVERSE_RELATIONSHIPS.get(normalized, "related")


def _object_map(
    objects: Iterable[CanonicalObject] | Mapping[str, CanonicalObject],
) -> dict[str, CanonicalObject]:
    if isinstance(objects, Mapping):
        return {normalize_id(key): value for key, value in objects.items()}
    return {normalize_id(obj.id): obj for obj in objects}
