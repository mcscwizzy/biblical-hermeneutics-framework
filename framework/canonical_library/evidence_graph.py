"""Deterministic graph projection for CKL evidence relationships.

The projection is deliberately computed from authored CKL records.  It gives
auditors and retrieval code graph-shaped edges without introducing a graph
database or a second source of truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .normalization import normalize_id
from .schema import CanonicalObject


@dataclass(frozen=True)
class EvidenceGraphEdge:
    source_id: str
    source_kind: str
    target_id: str
    target_kind: str
    relationship: str
    weight: int = 1
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evidence_graph_edges(objects: Iterable[CanonicalObject]) -> list[EvidenceGraphEdge]:
    """Project Passage -> Subject -> Claim -> Evidence -> Source edges.

    Object-local claim, source, and evidence identifiers are namespaced so
    independently authored CKL objects cannot collide in an audit export.
    """

    edges: list[EvidenceGraphEdge] = []
    for obj in sorted(objects, key=lambda item: item.id):
        subject_id = normalize_id(obj.id)
        for reference in obj.scripture_references:
            edges.append(
                EvidenceGraphEdge(
                    source_id=_passage_id(reference.reference),
                    source_kind="passage",
                    target_id=subject_id,
                    target_kind="subject",
                    relationship="references-subject",
                    weight=8,
                    notes=reference.notes,
                )
            )
        for claim in sorted(obj.claims, key=lambda item: item.id):
            claim_id = _local_id(subject_id, "claim", claim.id)
            edges.append(
                EvidenceGraphEdge(
                    source_id=subject_id,
                    source_kind="subject",
                    target_id=claim_id,
                    target_kind="claim",
                    relationship="has-claim",
                    weight=9,
                )
            )
            for reference in claim.scripture_references:
                edges.append(
                    EvidenceGraphEdge(
                        source_id=_passage_id(reference),
                        source_kind="passage",
                        target_id=claim_id,
                        target_kind="claim",
                        relationship="supports-claim",
                        weight=8,
                    )
                )
        for evidence in sorted(obj.evidence_items, key=lambda item: item.id):
            evidence_id = _local_id(subject_id, "evidence", evidence.id)
            edges.append(
                EvidenceGraphEdge(
                    source_id=subject_id,
                    source_kind="subject",
                    target_id=evidence_id,
                    target_kind="evidence",
                    relationship="has-evidence",
                    weight=10,
                )
            )
            for link in evidence.scripture_references:
                edges.append(
                    EvidenceGraphEdge(
                        source_id=_passage_id(link.reference),
                        source_kind="passage",
                        target_id=subject_id,
                        target_kind="subject",
                        relationship="evidence-for-subject",
                        weight=link.weight,
                        notes=f"chronology={link.temporal_relation}; {link.relevance_rationale}",
                    )
                )
                edges.append(
                    EvidenceGraphEdge(
                        source_id=_passage_id(link.reference),
                        source_kind="passage",
                        target_id=evidence_id,
                        target_kind="evidence",
                        relationship=link.relationship,
                        weight=link.weight,
                        notes=f"chronology={link.temporal_relation}; {link.relevance_rationale}",
                    )
                )
            for claim_id in evidence.claim_ids:
                edges.append(
                    EvidenceGraphEdge(
                        source_id=_local_id(subject_id, "claim", claim_id),
                        source_kind="claim",
                        target_id=evidence_id,
                        target_kind="evidence",
                        relationship="supported-by",
                        weight=8,
                    )
                )
            for source_id in evidence.source_ids:
                edges.append(
                    EvidenceGraphEdge(
                        source_id=evidence_id,
                        source_kind="evidence",
                        target_id=_local_id(subject_id, "source", source_id),
                        target_kind="source",
                        relationship="documented-by",
                        weight=8,
                    )
                )
            for geography_id in evidence.geography_ids:
                edges.append(
                    EvidenceGraphEdge(
                        source_id=evidence_id,
                        source_kind="evidence",
                        target_id=normalize_id(geography_id),
                        target_kind="geography",
                        relationship="located-in",
                        weight=8,
                    )
                )
            for relationship in evidence.related_objects:
                edges.append(
                    EvidenceGraphEdge(
                        source_id=evidence_id,
                        source_kind="evidence",
                        target_id=normalize_id(relationship.id),
                        target_kind="subject",
                        relationship=relationship.relationship,
                        weight=relationship.weight,
                        notes=relationship.notes,
                    )
                )
            for relationship in evidence.related_evidence:
                edges.append(
                    EvidenceGraphEdge(
                        source_id=evidence_id,
                        source_kind="evidence",
                        target_id=_local_id(subject_id, "evidence", relationship.id),
                        target_kind="evidence",
                        relationship=relationship.relationship,
                        weight=relationship.weight,
                        notes=relationship.notes,
                    )
                )
            for period in evidence.temporal_scope.periods:
                edges.append(
                    EvidenceGraphEdge(
                        source_id=evidence_id,
                        source_kind="evidence",
                        target_id="period:" + normalize_id(period),
                        target_kind="historical-period",
                        relationship="dated-to",
                        weight=8,
                    )
                )
            for reference in evidence.external_references:
                edges.append(
                    EvidenceGraphEdge(
                        source_id=evidence_id,
                        source_kind="evidence",
                        target_id=f"external:{reference.domain}:{reference.id}",
                        target_kind=reference.domain,
                        relationship=reference.relationship,
                        weight=8,
                        notes=reference.notes,
                    )
                )
    return sorted(
        edges,
        key=lambda edge: (
            edge.source_kind,
            edge.source_id,
            edge.target_kind,
            edge.target_id,
            edge.relationship,
        ),
    )


def _local_id(object_id: str, kind: str, local_id: str) -> str:
    return f"{object_id}#{kind}:{normalize_id(local_id)}"


def _passage_id(reference: str) -> str:
    return "passage:" + normalize_id(reference)
