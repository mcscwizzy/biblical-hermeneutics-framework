"""Read-only audit signals for future CKL evidence review pipelines."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .normalization import normalize_text
from .schema import CanonicalObject


@dataclass(frozen=True)
class EvidenceAuditIssue:
    code: str
    severity: str
    object_id: str
    evidence_id: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def audit_evidence(objects: Iterable[CanonicalObject]) -> dict[str, Any]:
    """Flag review risks without converting heuristic findings into facts."""

    object_list = sorted(objects, key=lambda item: item.id)
    issues: list[EvidenceAuditIssue] = []
    fingerprints: dict[str, list[tuple[str, str]]] = defaultdict(list)
    evidence_count = 0

    for obj in object_list:
        source_types = {source.id: source.source_type for source in obj.sources}
        for item in obj.evidence_items:
            evidence_count += 1
            fingerprint = normalize_text(item.title + " " + item.primary_observation)
            if fingerprint:
                fingerprints[fingerprint].append((obj.id, item.id))
            if not item.temporal_scope.periods and item.temporal_scope.start_year is None:
                issues.append(_issue("missing-chronology", "warning", obj, item, "Evidence has no date range or historical period."))
            if any(link.temporal_relation == "unknown" for link in item.scripture_references):
                issues.append(_issue("unknown-passage-chronology", "warning", obj, item, "A passage relationship has unknown chronological relevance."))
            if item.confidence == "high" and (
                item.certainty in {"disputed", "speculative", "insufficient_evidence"}
                or item.dispute_status
                not in {"not_disputed", "minor_scholarly_disagreement"}
            ):
                issues.append(_issue("dispute-confidence-mismatch", "error", obj, item, "High confidence is paired with disputed or uncertain evidence."))
            weak_sources = sorted(
                source_id for source_id in item.source_ids if source_types.get(source_id) == "other"
            )
            if weak_sources:
                issues.append(_issue("weak-source-type", "warning", obj, item, "Evidence relies on unclassified source(s): " + ", ".join(weak_sources)))
            image_url = item.metadata.get("image_source_url", "")
            if image_url and not item.metadata.get("image_license"):
                issues.append(_issue("missing-image-license", "error", obj, item, "Image URL has no recorded license."))
            if image_url and not item.metadata.get("image_attribution"):
                issues.append(_issue("missing-image-attribution", "error", obj, item, "Image URL has no recorded attribution."))
            if _questionable_temporal_alignment(obj, item):
                issues.append(_issue("questionable-chronology", "warning", obj, item, "Evidence labeled contemporary or near-contemporary does not overlap the subject range."))

    duplicate_groups = [
        [{"object_id": object_id, "evidence_id": evidence_id} for object_id, evidence_id in members]
        for _, members in sorted(fingerprints.items())
        if len(members) > 1
    ]
    for group in duplicate_groups:
        for member in group:
            issues.append(
                EvidenceAuditIssue(
                    code="possible-duplicate-evidence",
                    severity="warning",
                    object_id=member["object_id"],
                    evidence_id=member["evidence_id"],
                    message="Evidence title and primary observation duplicate another record.",
                )
            )
    issues.sort(key=lambda item: (item.severity, item.code, item.object_id, item.evidence_id))
    return {
        "evidence_count": evidence_count,
        "issue_count": len(issues),
        "error_count": sum(issue.severity == "error" for issue in issues),
        "warning_count": sum(issue.severity == "warning" for issue in issues),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_groups": duplicate_groups,
        "issues": [issue.to_dict() for issue in issues],
    }


def _issue(code: str, severity: str, obj: CanonicalObject, item: Any, message: str) -> EvidenceAuditIssue:
    return EvidenceAuditIssue(code, severity, obj.id, item.id, message)


def _questionable_temporal_alignment(obj: CanonicalObject, item: Any) -> bool:
    subject = obj.temporal_scope
    evidence = item.temporal_scope
    if subject.start_year is None or subject.end_year is None:
        return False
    if evidence.start_year is None or evidence.end_year is None:
        return False
    relations = {link.temporal_relation for link in item.scripture_references}
    if not relations.intersection({"contemporary", "near-contemporary"}):
        return False
    tolerance = 100 if "near-contemporary" in relations else 0
    return evidence.end_year < subject.start_year - tolerance or evidence.start_year > subject.end_year + tolerance
