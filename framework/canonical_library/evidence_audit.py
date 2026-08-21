"""Read-only audit signals for future CKL evidence review pipelines."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable, Mapping

from .normalization import normalize_text
from .schema import CanonicalObject


PRIMARY_SOURCE_TYPES = frozenset(
    {"scripture", "ancient-primary-source", "excavation-report", "museum-collection"}
)
ACADEMIC_SECONDARY_SOURCE_TYPES = frozenset(
    {"academic-book", "journal-article", "lexicon", "grammar", "reference-work"}
)
LOCATOR_EXPECTED_SOURCE_TYPES = frozenset(
    {
        "ancient-primary-source",
        "academic-book",
        "journal-article",
        "lexicon",
        "grammar",
        "excavation-report",
        "museum-collection",
    }
)
INTERNAL_SOURCE_MARKERS = (
    "internal ckl",
    "canonical knowledge library",
    "canonical historical orientation",
)
CONTEXT_FIELDS: tuple[tuple[str, str], ...] = (
    ("historical", "historical_context"),
    ("ancient_near_east", "ancient_near_east_context"),
    ("hebraic_worldview", "hebraic_worldview"),
    ("second_temple", "second_temple_context"),
    ("canonical", "canonical_context"),
    ("later_christian_reception", "later_christian_reception"),
)
GENERIC_PROSE_MARKERS = (
    "as the relevant passages require",
    "depending on the passage",
    "is located by its canonical setting this entry connects",
    "belongs within the scriptural setting around",
    "helps anchor the biblical world in physical evidence and archaeological context",
    "without letting comparison replace the biblical witness",
    "serves as a canonical event anchor",
    "serves as a canonical person anchor",
    "serves as a canonical place anchor",
    "serves as a material culture anchor",
)
GENERIC_QUESTION_PATTERNS = (
    re.compile(r"^what does .+ teach$"),
    re.compile(r"^how does .+ fit the biblical storyline$"),
    re.compile(r"^what should readers avoid when interpreting .+$"),
    re.compile(r"^why does this (event|figure|place|theme) matter"),
    re.compile(r"^what (covenant|theological) (theme|pattern) does this"),
)


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
    with_primary_sources = 0
    with_academic_secondary_sources = 0
    with_chronology = 0
    with_passage_relevance = 0
    disputed_count = 0
    worldview_count = 0
    archaeology_linked_count = 0
    internal_only_evidence: list[dict[str, str]] = []
    missing_locator_sources: set[tuple[str, str]] = set()
    missing_confidence_rationale_count = 0
    generic_boilerplate_records: dict[str, list[str]] = {}
    overbroad_applicability_records: list[str] = []

    for obj in object_list:
        source_map = {source.id: source for source in obj.sources}
        generic_fields = _generic_boilerplate_fields(obj)
        if generic_fields:
            generic_boilerplate_records[obj.id] = generic_fields
            issues.append(
                EvidenceAuditIssue(
                    code="generic-legacy-boilerplate",
                    severity="warning",
                    object_id=obj.id,
                    evidence_id="",
                    message="Generic or template-like prose needs object-specific review: "
                    + ", ".join(generic_fields),
                )
            )
        applicability_issue = _context_applicability_issue(obj, generic_fields)
        if applicability_issue:
            overbroad_applicability_records.append(obj.id)
            issues.append(
                EvidenceAuditIssue(
                    code="overbroad-context-applicability",
                    severity="warning",
                    object_id=obj.id,
                    evidence_id="",
                    message=applicability_issue,
                )
            )

        for item in obj.evidence_items:
            evidence_count += 1
            selected_sources = [source_map[source_id] for source_id in item.source_ids if source_id in source_map]
            source_types = {source.source_type for source in selected_sources}
            has_chronology = bool(item.temporal_scope.periods or item.temporal_scope.start_year is not None)
            with_primary_sources += bool(source_types & PRIMARY_SOURCE_TYPES)
            with_academic_secondary_sources += bool(source_types & ACADEMIC_SECONDARY_SOURCE_TYPES)
            with_chronology += has_chronology
            with_passage_relevance += bool(item.passage_relevance.strip())
            disputed_count += item.dispute_status != "not_disputed"
            worldview_count += item.evidence_type == "worldview-concept"
            archaeology_linked_count += any(
                reference.domain in {"archaeology-item", "archaeology-site"}
                for reference in item.external_references
            )
            missing_confidence_rationale_count += not bool(item.confidence_rationale.strip())

            fingerprint = normalize_text(item.title + " " + item.primary_observation)
            if fingerprint:
                fingerprints[fingerprint].append((obj.id, item.id))
            if not has_chronology:
                issues.append(_issue("missing-chronology", "warning", obj, item, "Evidence has no date range or historical period."))
            if any(link.temporal_relation == "unknown" for link in item.scripture_references):
                issues.append(_issue("unknown-passage-chronology", "warning", obj, item, "A passage relationship has unknown chronological relevance."))
            if item.confidence == "high" and (
                item.certainty in {"disputed", "speculative", "insufficient_evidence"}
                or item.dispute_status not in {"not_disputed", "minor_scholarly_disagreement"}
            ):
                issues.append(_issue("dispute-confidence-mismatch", "error", obj, item, "High confidence is paired with disputed or uncertain evidence."))
            weak_sources = sorted(
                source_id for source_id in item.source_ids if source_map.get(source_id) is not None and source_map[source_id].source_type == "other"
            )
            if weak_sources:
                issues.append(_issue("weak-source-type", "warning", obj, item, "Evidence relies on unclassified source(s): " + ", ".join(weak_sources)))
            missing_sources = sorted(set(item.source_ids) - set(source_map))
            if missing_sources:
                issues.append(_issue("missing-evidence-source", "error", obj, item, "Evidence references missing source(s): " + ", ".join(missing_sources)))
            if item.confidence == "high" and selected_sources and not (source_types & PRIMARY_SOURCE_TYPES):
                issues.append(_issue("high-confidence-secondary-only", "warning", obj, item, "High-confidence evidence is supported only by secondary sources."))
            for source in selected_sources:
                if source.source_type in LOCATOR_EXPECTED_SOURCE_TYPES and not source.locator.strip():
                    missing_locator_sources.add((obj.id, source.id))
                    issues.append(_issue("source-missing-locator", "warning", obj, item, f'Source "{source.id}" has no passage, object, page, or edition locator.'))
            if selected_sources and all(_is_internal_source(source) for source in selected_sources):
                internal_only_evidence.append({"object_id": obj.id, "evidence_id": item.id})
                issues.append(_issue("internal-source-only", "warning", obj, item, "External historical evidence relies only on an internal CKL orientation source."))
            if (
                item.evidence_type == "worldview-concept"
                and len(selected_sources) == 1
                and selected_sources[0].source_type in ACADEMIC_SECONDARY_SOURCE_TYPES
            ):
                issues.append(_issue("worldview-single-modern-source", "warning", obj, item, "Worldview reconstruction relies on only one modern secondary source."))
            if (
                item.primary_observation
                and normalize_text(item.primary_observation) == normalize_text(item.scholarly_interpretation)
            ):
                issues.append(_issue("observation-interpretation-duplicate", "warning", obj, item, "Primary observation and scholarly interpretation are identical."))
            if any(
                link.temporal_relation in {"earlier-comparative", "later-comparative"}
                and link.relationship not in {"comparative", "contrast", "disputed"}
                for link in item.scripture_references
            ):
                issues.append(_issue("unsupported-cross-period-link", "warning", obj, item, "A cross-period link is not labeled comparative, contrastive, or disputed."))
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
        "evidence_with_primary_sources_count": with_primary_sources,
        "evidence_with_academic_secondary_sources_count": with_academic_secondary_sources,
        "evidence_with_chronology_count": with_chronology,
        "evidence_with_passage_relevance_count": with_passage_relevance,
        "disputed_evidence_count": disputed_count,
        "worldview_evidence_count": worldview_count,
        "archaeology_linked_evidence_count": archaeology_linked_count,
        "internal_source_only_evidence_count": len(internal_only_evidence),
        "internal_source_only_evidence": internal_only_evidence,
        "missing_source_locator_count": len(missing_locator_sources),
        "missing_confidence_rationale_count": missing_confidence_rationale_count,
        "generic_boilerplate_count": sum(len(fields) for fields in generic_boilerplate_records.values()),
        "generic_boilerplate_record_count": len(generic_boilerplate_records),
        "generic_boilerplate_records": generic_boilerplate_records,
        "overbroad_context_applicability_count": len(overbroad_applicability_records),
        "overbroad_context_applicability_records": overbroad_applicability_records,
        "issue_count": len(issues),
        "error_count": sum(issue.severity == "error" for issue in issues),
        "warning_count": sum(issue.severity == "warning" for issue in issues),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_groups": duplicate_groups,
        "issues": [issue.to_dict() for issue in issues],
    }


def _issue(code: str, severity: str, obj: CanonicalObject, item: Any, message: str) -> EvidenceAuditIssue:
    return EvidenceAuditIssue(code, severity, obj.id, item.id, message)


def _is_internal_source(source: Any) -> bool:
    text = normalize_text(" ".join((source.id, source.title, source.publisher, source.notes)))
    return any(marker in text for marker in INTERNAL_SOURCE_MARKERS)


def _generic_boilerplate_fields(obj: CanonicalObject) -> list[str]:
    fields: list[str] = []
    for _, field_name in CONTEXT_FIELDS:
        text = normalize_text(str(getattr(obj, field_name, "") or ""))
        if text and any(marker in text for marker in GENERIC_PROSE_MARKERS):
            fields.append(field_name)
    canonical_role = normalize_text(str(getattr(obj, "canonical_role", "") or ""))
    if canonical_role and any(marker in canonical_role for marker in GENERIC_PROSE_MARKERS):
        fields.append("canonical_role")
    if any(
        pattern.search(normalize_text(question))
        for question in getattr(obj, "common_questions", [])
        for pattern in GENERIC_QUESTION_PATTERNS
    ):
        fields.append("common_questions")
    return list(dict.fromkeys(fields))


def _context_applicability_issue(obj: CanonicalObject, generic_fields: list[str]) -> str:
    applicability: Mapping[str, bool] = obj.context_applicability
    enabled = [key for key, _ in CONTEXT_FIELDS if applicability.get(key, False)]
    empty_enabled = [
        key
        for key, field_name in CONTEXT_FIELDS
        if applicability.get(key, False) and not str(getattr(obj, field_name, "") or "").strip()
    ]
    generic_enabled = [
        key
        for key, field_name in CONTEXT_FIELDS
        if applicability.get(key, False) and field_name in generic_fields
    ]
    if empty_enabled:
        return "Applicable context dimensions have no authored content: " + ", ".join(empty_enabled)
    if len(enabled) >= 5 and generic_enabled:
        return "Nearly every context dimension is enabled while generic prose remains in: " + ", ".join(generic_enabled)
    return ""


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
