"""Deterministic selection-sufficiency assessment for locked commentary inputs.

This contract evaluates whether validated renderer prose expresses enough of
the materially important, legally renderable source ideas. It does not replace
schema/provenance validation or the separate presentation-quality gate.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping

from .evidence_applicability import evaluate_evidence_applicability
from .richness_clusters import (
    CORE_CLASSIFIER_V2,
    RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    RICHNESS_POLICY_VERSION_V3,
    CoverageEligibility,
    QualityClass,
    score_synthesis_richness,
)


SELECTION_SUFFICIENCY_VERSION = "commentary-renderer-selection-sufficiency-v1"
RENDERER_SELECTION_COLLAPSE = "RENDERER_SELECTION_COLLAPSE"
RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE = (
    "RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE"
)
LEGACY_SELECTION_EXCEPTION_VERSION = (
    "commentary-renderer-selection-legacy-exception-v1"
)
LEGACY_SELECTION_EXCEPTION_DECISION = (
    "ACCEPT_WITH_SELECTION_ASSESSMENT_UNAVAILABLE"
)
SELECTION_WEIGHTED_COVERAGE_MIN = 0.75
SELECTION_CORE_COVERAGE_MIN = 1.0

_WORD_RE = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?")
_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have he her his in is it its of on or "
    "that the their them they this to was were which who with about after before "
    "chapter context describe explains includes later passage presents reads says "
    "shows text what when where while within idea ideas fact facts claim claims "
    "mark marks role roles use uses help helps reader readers understand understanding".split()
)
_ELIGIBLE_COVERAGE = frozenset(
    {CoverageEligibility.REQUIRED.value, CoverageEligibility.RELEVANT.value}
)


@dataclass(frozen=True)
class SelectionSufficiencyAssessment:
    """Machine-readable selection decision and its complete denominator audit."""

    assessment_version: str
    status: str
    diagnostic_code: str | None
    source_identity: dict[str, Any]
    renderer_versions: dict[str, str | None]
    classifiers: dict[str, str]
    counts: dict[str, int]
    weighted_eligible_coverage: float | None
    thresholds: dict[str, float]
    consumed_synthesis_ids: list[str] = field(default_factory=list)
    legally_renderable_synthesis_ids: list[str] = field(default_factory=list)
    eligible_synthesis_ids: list[str] = field(default_factory=list)
    represented_synthesis_ids: list[str] = field(default_factory=list)
    represented_cluster_ids: list[str] = field(default_factory=list)
    omitted_cluster_ids: list[str] = field(default_factory=list)
    omitted_core_cluster_ids: list[str] = field(default_factory=list)
    materially_omitted_cluster_ids: list[str] = field(default_factory=list)
    disputed_cluster_ids: list[str] = field(default_factory=list)
    surrounding_cluster_ids: list[str] = field(default_factory=list)
    redundant_or_parallel_cluster_ids: list[str] = field(default_factory=list)
    eligible_evidence_ids: list[str] = field(default_factory=list)
    directly_cited_evidence_ids: list[str] = field(default_factory=list)
    excluded_inherited_evidence_ids: list[str] = field(default_factory=list)
    excluded_inherited_cited_ids: list[str] = field(default_factory=list)
    applicability_exclusions: list[dict[str, Any]] = field(default_factory=list)
    denominator_definitions: dict[str, Any] = field(default_factory=dict)
    evidence_category_representation: dict[str, Any] = field(default_factory=dict)
    synthesis_kind_representation: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    dimensions: dict[str, str] = field(
        default_factory=lambda: {
            "technical_validity": "NOT_ASSESSED_BY_SELECTION_GATE",
            "selection_sufficiency": "ASSESSMENT_UNAVAILABLE",
            "presentation_quality": "NOT_ASSESSED_BY_SELECTION_GATE",
        }
    )
    assessment_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_selection_sufficiency(
    synthesis: Any | None,
    bundle: Any | None,
    commentary: Any,
    *,
    passage_text: str = "",
    source_identity: Mapping[str, Any] | None = None,
    renderer_prompt_version: str | None = None,
    renderer_schema_version: str | None = None,
) -> SelectionSufficiencyAssessment:
    """Assess validated prose against its locked, eligible synthesis context.

    A cluster counts as represented only when the response cites a synthesis
    unit and eligible evidence from that cluster, and its prose shares a
    deterministic lexical anchor with an authored synthesis fact. This keeps
    citation consumption distinct from idea expression. The lexical test is
    intentionally conservative and auditable; it cannot establish semantic
    equivalence for every paraphrase.
    """

    source = _source_identity(synthesis, bundle, source_identity)
    versions = {
        "renderer_prompt_version": renderer_prompt_version,
        "renderer_schema_version": renderer_schema_version,
    }
    unavailable = _locked_context_errors(
        synthesis,
        bundle,
        source,
        renderer_prompt_version,
        renderer_schema_version,
    )
    if unavailable:
        return _unavailable_assessment(source, versions, unavailable)

    units = list(getattr(synthesis, "synthesis_units", ()) or ())
    evidence_items = list(getattr(bundle, "evidence_items", ()) or ())
    evidence_by_id = {_text(item, "id"): item for item in evidence_items}
    reference = _text(synthesis, "reference")
    applicability = {
        evidence_id: evaluate_evidence_applicability(item, reference)
        for evidence_id, item in evidence_by_id.items()
    }
    eligible_evidence_ids = {
        evidence_id
        for evidence_id, decision in applicability.items()
        if decision.current_chapter_eligible
    }
    exclusions = [
        {
            "evidence_id": evidence_id,
            "status": decision.status,
            "reason": decision.reason,
            "scope": decision.applicability_scope,
            "inherited_from_parent": decision.inherited_from_parent,
        }
        for evidence_id, decision in sorted(applicability.items())
        if not decision.current_chapter_eligible
    ]
    inherited_ids = sorted(
        evidence_id
        for evidence_id, decision in applicability.items()
        if not decision.current_chapter_eligible
        and decision.inherited_from_parent is True
    )

    legally_renderable_units = [
        unit
        for unit in units
        if _sequence(unit, "evidence_ids")
        and set(_sequence(unit, "evidence_ids")).issubset(eligible_evidence_ids)
    ]
    legally_renderable_ids = {
        _text(unit, "id") for unit in legally_renderable_units
    }
    score = score_synthesis_richness(
        legally_renderable_units,
        evidence_items=[evidence_by_id[value] for value in sorted(eligible_evidence_ids)],
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=passage_text,
    )
    unit_map = {_text(unit, "id"): unit for unit in legally_renderable_units}
    clusters = list(score.clusters)
    eligible_clusters = [
        cluster
        for cluster in clusters
        if cluster.coverage_eligibility in _ELIGIBLE_COVERAGE
    ]
    core_clusters = [
        cluster
        for cluster in eligible_clusters
        if cluster.quality_class == QualityClass.CORE.value
    ]
    disputed_clusters = [
        cluster
        for cluster in clusters
        if cluster.dispute_present
        or cluster.quality_class == QualityClass.DISPUTED.value
    ]
    surrounding_clusters = [
        cluster
        for cluster in clusters
        if cluster.passage_scope == "SURROUNDING_PASSAGE"
    ]

    blocks = _blocks(commentary)
    consumed_ids = {
        synthesis_id
        for block in blocks
        for synthesis_id in _sequence(block, "synthesis_ids")
    }
    cited_evidence_ids = {
        evidence_id
        for block in blocks
        for evidence_id in _sequence(block, "evidence_ids")
    }
    directly_cited_eligible = cited_evidence_ids.intersection(eligible_evidence_ids)
    expressed_units: set[str] = set()
    expressed_evidence: set[str] = set()
    represented_clusters: set[str] = set()
    citation_only_cluster_ids: set[str] = set()

    for cluster in eligible_clusters:
        cluster_units = set(cluster.synthesis_ids)
        cluster_evidence = set(cluster.evidence_ids).intersection(eligible_evidence_ids)
        represented_by_block = False
        for block in blocks:
            cited_units = set(_sequence(block, "synthesis_ids")).intersection(
                cluster_units
            )
            cited_evidence = set(_sequence(block, "evidence_ids")).intersection(
                cluster_evidence
            )
            if not cited_units or not cited_evidence:
                continue
            text = _text(block, "text")
            expressed_here = {
                synthesis_id
                for synthesis_id in cited_units
                if _expresses_unit(text, unit_map.get(synthesis_id))
            }
            if expressed_here:
                represented_by_block = True
                expressed_units.update(expressed_here)
                expressed_evidence.update(cited_evidence)
            else:
                citation_only_cluster_ids.add(cluster.id)
        if represented_by_block:
            represented_clusters.add(cluster.id)

    omitted_clusters = {
        cluster.id for cluster in eligible_clusters
    } - represented_clusters
    omitted_core = {
        cluster.id for cluster in core_clusters
    } - represented_clusters
    denominator_weight = sum(cluster.importance_weight for cluster in eligible_clusters)
    represented_weight = sum(
        cluster.importance_weight
        for cluster in eligible_clusters
        if cluster.id in represented_clusters
    )
    weighted_coverage = (
        1.0
        if denominator_weight == 0
        else round(represented_weight / denominator_weight, 4)
    )
    core_coverage = (
        1.0
        if not core_clusters
        else round(
            sum(cluster.id in represented_clusters for cluster in core_clusters)
            / len(core_clusters),
            4,
        )
    )
    reasons: list[str] = []
    if omitted_core:
        reasons.append(
            "OMITTED_CORE_IDEA_CLUSTERS: " + ", ".join(sorted(omitted_core))
        )
    if weighted_coverage < SELECTION_WEIGHTED_COVERAGE_MIN:
        reasons.append(
            "WEIGHTED_ELIGIBLE_COVERAGE_BELOW_MINIMUM: "
            f"{weighted_coverage:.4f} < {SELECTION_WEIGHTED_COVERAGE_MIN:.4f}"
        )
    if citation_only_cluster_ids and (
        omitted_core or weighted_coverage < SELECTION_WEIGHTED_COVERAGE_MIN
    ):
        reasons.append(
            "IDEA_CITATIONS_NOT_EXPRESSED: "
            + ", ".join(sorted(citation_only_cluster_ids))
        )
    passed = (
        core_coverage >= SELECTION_CORE_COVERAGE_MIN
        and weighted_coverage >= SELECTION_WEIGHTED_COVERAGE_MIN
    )
    status = "PASS" if passed else "FAIL"
    diagnostic_code = None if passed else RENDERER_SELECTION_COLLAPSE
    material_omissions = sorted(omitted_clusters) if not passed else []

    evidence_categories_available = sorted(
        {
            _text(evidence_by_id[value], "category")
            for value in eligible_evidence_ids
            if _text(evidence_by_id[value], "category")
        }
    )
    evidence_categories_cited = sorted(
        {
            _text(evidence_by_id[value], "category")
            for value in directly_cited_eligible
            if _text(evidence_by_id[value], "category")
        }
    )
    evidence_categories_expressed = sorted(
        {
            _text(evidence_by_id[value], "category")
            for value in expressed_evidence
            if _text(evidence_by_id[value], "category")
        }
    )
    available_kinds = sorted(
        {
            _text(unit, "kind")
            for unit in legally_renderable_units
            if _text(unit, "kind")
        }
    )
    represented_kinds = sorted(
        {
            _text(unit_map[value], "kind")
            for value in expressed_units
            if value in unit_map and _text(unit_map[value], "kind")
        }
    )
    excluded_inherited_cited = sorted(cited_evidence_ids.intersection(inherited_ids))
    redundant = sorted(
        cluster.id
        for cluster in eligible_clusters
        if cluster.duplicate_reason != "DISTINCT"
    )
    counts = {
        "evidence_records_in_bundle": len(evidence_items),
        "eligible_evidence_ids": len(eligible_evidence_ids),
        "excluded_background_evidence_ids": len(exclusions),
        "excluded_inherited_background_ids": len(inherited_ids),
        "available_synthesis_units": len(units),
        "legally_renderable_synthesis_units": len(legally_renderable_units),
        "eligible_synthesis_units": score.eligible_synthesis_count,
        "consumed_synthesis_units": len(consumed_ids),
        "represented_synthesis_units": len(expressed_units),
        "available_idea_clusters": len(clusters),
        "eligible_idea_clusters": len(eligible_clusters),
        "core_idea_clusters": len(core_clusters),
        "other_relevant_idea_clusters": len(eligible_clusters) - len(core_clusters),
        "contextual_or_optional_idea_clusters": len(clusters) - len(eligible_clusters),
        "disputed_idea_clusters": len(disputed_clusters),
        "surrounding_idea_clusters": len(surrounding_clusters),
        "represented_idea_clusters": len(represented_clusters),
        "omitted_idea_clusters": len(omitted_clusters),
        "materially_omitted_idea_clusters": len(material_omissions),
        "redundant_or_parallel_idea_clusters": len(redundant),
        "directly_cited_eligible_evidence_ids": len(directly_cited_eligible),
    }
    evidence_categories = {
        "available": evidence_categories_available,
        "directly_cited": evidence_categories_cited,
        "expressed_with_idea": evidence_categories_expressed,
        "directly_cited_count": len(evidence_categories_cited),
        "available_count": len(evidence_categories_available),
        "direct_citation_coverage": _ratio(
            len(evidence_categories_cited), len(evidence_categories_available)
        ),
        "is_direct_citation_metric": True,
    }
    synthesis_kinds = {
        "available": available_kinds,
        "represented": represented_kinds,
        "represented_count": len(represented_kinds),
        "available_count": len(available_kinds),
        "coverage": _ratio(len(represented_kinds), len(available_kinds)),
    }
    source = {
        **source,
        "reference": reference,
        "evidence_hash": _text(bundle, "evidence_hash"),
        "synthesis_hash": _text(synthesis, "synthesis_hash"),
        "evidence_bundle_version": _text(bundle, "version"),
        "synthesis_schema_version": _text(synthesis, "synthesis_schema_version"),
        "synthesis_compiler_version": _text(synthesis, "synthesis_compiler_version"),
    }
    data = {
        "assessment_version": SELECTION_SUFFICIENCY_VERSION,
        "status": status,
        "diagnostic_code": diagnostic_code,
        "source_identity": source,
        "renderer_versions": versions,
        "classifiers": {
            "richness_clustering_version": RICHNESS_CLUSTER_AUDIT_VERSION_V2,
            "reader_relevance_policy_version": RICHNESS_POLICY_VERSION_V3,
            "core_classifier_version": CORE_CLASSIFIER_V2,
            "evidence_applicability_version": "commentary-evidence-applicability-v1",
            "representation_heuristic_version": "authored-fact-lexical-anchor-v1",
        },
        "counts": counts,
        "weighted_eligible_coverage": weighted_coverage,
        "thresholds": {
            "weighted_eligible_coverage_min": SELECTION_WEIGHTED_COVERAGE_MIN,
            "core_coverage_min": SELECTION_CORE_COVERAGE_MIN,
        },
        "consumed_synthesis_ids": sorted(consumed_ids),
        "legally_renderable_synthesis_ids": sorted(legally_renderable_ids),
        "eligible_synthesis_ids": sorted(
            {
                synthesis_id
                for cluster in eligible_clusters
                for synthesis_id in cluster.synthesis_ids
            }
        ),
        "represented_synthesis_ids": sorted(expressed_units),
        "represented_cluster_ids": sorted(represented_clusters),
        "omitted_cluster_ids": sorted(omitted_clusters),
        "omitted_core_cluster_ids": sorted(omitted_core),
        "materially_omitted_cluster_ids": material_omissions,
        "disputed_cluster_ids": sorted(cluster.id for cluster in disputed_clusters),
        "surrounding_cluster_ids": sorted(cluster.id for cluster in surrounding_clusters),
        "redundant_or_parallel_cluster_ids": redundant,
        "eligible_evidence_ids": sorted(eligible_evidence_ids),
        "directly_cited_evidence_ids": sorted(directly_cited_eligible),
        "excluded_inherited_evidence_ids": inherited_ids,
        "excluded_inherited_cited_ids": excluded_inherited_cited,
        "applicability_exclusions": exclusions,
        "denominator_definitions": {
            "eligible_evidence_ids": (
                "EvidenceBundle records for which the unchanged applicability policy "
                "returns current_chapter_eligible=true. Excluded inherited/background "
                "records are never part of the selection denominator."
            ),
            "legally_renderable_synthesis_units": (
                "Compiled units with non-empty evidence ancestry wholly contained in "
                "the eligible evidence ID set."
            ),
            "eligible_idea_clusters": (
                "V3 clusters classified REQUIRED or RELEVANT; duplicate/parallel "
                "units count once, while contextual/optional clusters are excluded."
            ),
            "weighted_eligible_coverage": (
                "Sum of the existing quality-class cluster weights for represented "
                "eligible clusters divided by the same sum for all eligible clusters; "
                "a zero denominator is vacuously 1.0."
            ),
            "excluded_inherited_evidence_ids": inherited_ids,
            "all_applicability_exclusion_ids": [item["evidence_id"] for item in exclusions],
        },
        "evidence_category_representation": evidence_categories,
        "synthesis_kind_representation": synthesis_kinds,
        "reasons": reasons,
        "dimensions": {
            "technical_validity": "NOT_ASSESSED_BY_SELECTION_GATE",
            "selection_sufficiency": status,
            "presentation_quality": "NOT_ASSESSED_BY_SELECTION_GATE",
        },
    }
    assessment_hash = _hash_json(data)
    data["assessment_hash"] = assessment_hash
    return SelectionSufficiencyAssessment(**data)


def validate_legacy_selection_exception(
    exception: Any,
    expected_source_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate an explicit human review for a legacy artifact lacking context.

    The exception is bound to exact source/output identities. It cannot waive a
    recorded selection failure and is intended only for promotion code that has
    already established technical validation and provenance.
    """

    if not isinstance(exception, Mapping):
        return {"valid": False, "reasons": ["LEGACY_REVIEW_RECORD_REQUIRED"]}
    reasons: list[str] = []
    if exception.get("artifact_version") != LEGACY_SELECTION_EXCEPTION_VERSION:
        reasons.append("LEGACY_REVIEW_RECORD_VERSION_MISMATCH")
    if exception.get("decision") != LEGACY_SELECTION_EXCEPTION_DECISION:
        reasons.append("LEGACY_REVIEW_DECISION_MISMATCH")
    reviewer = str(exception.get("reviewer") or "").strip()
    if not reviewer:
        reasons.append("LEGACY_REVIEWER_REQUIRED")
    rationale = str(exception.get("rationale") or "").strip()
    if len(rationale) < 20:
        reasons.append("LEGACY_REVIEW_RATIONALE_TOO_SHORT")
    reviewed_at = str(exception.get("reviewed_at") or "").strip()
    try:
        parsed = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            reasons.append("LEGACY_REVIEW_TIMESTAMP_MUST_INCLUDE_TIMEZONE")
    except ValueError:
        reasons.append("LEGACY_REVIEW_TIMESTAMP_INVALID")
    if dict(exception.get("source_identity") or {}) != dict(expected_source_identity):
        reasons.append("LEGACY_REVIEW_SOURCE_IDENTITY_MISMATCH")
    return {
        "valid": not reasons,
        "reasons": reasons,
        "exception": {
            "artifact_version": exception.get("artifact_version"),
            "decision": exception.get("decision"),
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "rationale": rationale,
            "source_identity": dict(exception.get("source_identity") or {}),
        }
        if not reasons
        else None,
    }


def validate_selection_assessment(
    assessment: Any,
    expected_source_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Check a persisted v1 assessment and bind it to the expected source/output.

    Acceptance and release code use this helper before trusting a recorded PASS.
    The assessment hash protects the full deterministic audit payload, while
    the source identity check prevents replaying a PASS for another artifact.
    """

    if not isinstance(assessment, Mapping):
        return {"valid": False, "status": "ASSESSMENT_UNAVAILABLE", "reasons": ["SELECTION_ASSESSMENT_MISSING"]}
    reasons: list[str] = []
    if assessment.get("assessment_version") != SELECTION_SUFFICIENCY_VERSION:
        reasons.append("SELECTION_ASSESSMENT_VERSION_MISMATCH")
    status = assessment.get("status")
    if status not in {"PASS", "FAIL", "ASSESSMENT_UNAVAILABLE"}:
        reasons.append("SELECTION_ASSESSMENT_STATUS_INVALID")
    expected_diagnostic = {
        "PASS": None,
        "FAIL": RENDERER_SELECTION_COLLAPSE,
        "ASSESSMENT_UNAVAILABLE": RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE,
    }.get(status)
    if assessment.get("diagnostic_code") != expected_diagnostic:
        reasons.append("SELECTION_ASSESSMENT_DIAGNOSTIC_STATUS_MISMATCH")
    supplied_hash = assessment.get("assessment_hash")
    unsigned = dict(assessment)
    unsigned.pop("assessment_hash", None)
    if not isinstance(supplied_hash, str) or supplied_hash != _hash_json(unsigned):
        reasons.append("SELECTION_ASSESSMENT_HASH_MISMATCH")
    source_identity = assessment.get("source_identity")
    if not isinstance(source_identity, Mapping):
        reasons.append("SELECTION_ASSESSMENT_SOURCE_IDENTITY_MISSING")
        source_identity = {}
    for key, expected in (expected_source_identity or {}).items():
        if source_identity.get(key) != expected:
            reasons.append(f"SELECTION_ASSESSMENT_SOURCE_IDENTITY_MISMATCH:{key}")
    return {
        "valid": not reasons,
        "status": status if not reasons else "ASSESSMENT_UNAVAILABLE",
        "reasons": reasons,
        "source_identity": dict(source_identity),
    }


def _source_identity(
    synthesis: Any | None,
    bundle: Any | None,
    supplied: Mapping[str, Any] | None,
) -> dict[str, Any]:
    result = dict(supplied or {})
    if bundle is not None:
        result.setdefault("evidence_hash", _text(bundle, "evidence_hash"))
        result.setdefault("evidence_bundle_version", _text(bundle, "version"))
        result.setdefault("reference", _text(bundle, "passage_ref"))
    if synthesis is not None:
        result.setdefault("synthesis_hash", _text(synthesis, "synthesis_hash"))
        result.setdefault("synthesis_schema_version", _text(synthesis, "synthesis_schema_version"))
        result.setdefault("synthesis_compiler_version", _text(synthesis, "synthesis_compiler_version"))
        result.setdefault("reference", _text(synthesis, "reference"))
    return result


def _locked_context_errors(
    synthesis: Any | None,
    bundle: Any | None,
    source: Mapping[str, Any],
    prompt_version: str | None,
    schema_version: str | None,
) -> list[str]:
    errors: list[str] = []
    if synthesis is None or bundle is None:
        errors.append("LOCKED_BUNDLE_AND_SYNTHESIS_REQUIRED")
        return errors
    if not prompt_version or not schema_version:
        errors.append("RENDERER_PROMPT_AND_SCHEMA_VERSIONS_REQUIRED")
    synthesis_reference = _text(synthesis, "reference")
    if not synthesis_reference or synthesis_reference != _text(bundle, "passage_ref"):
        errors.append("SOURCE_REFERENCE_MISMATCH")
    for key, actual in (
        ("evidence_hash", _text(bundle, "evidence_hash")),
        ("synthesis_hash", _text(synthesis, "synthesis_hash")),
    ):
        if not actual or not source.get(key) or source.get(key) != actual:
            errors.append(f"LOCKED_{key.upper()}_MISSING_OR_MISMATCHED")
    if _text(synthesis, "evidence_hash") != _text(bundle, "evidence_hash"):
        errors.append("SYNTHESIS_EVIDENCE_HASH_MISMATCH")
    if _text(synthesis, "evidence_bundle_version") != _text(bundle, "version"):
        errors.append("SYNTHESIS_EVIDENCE_BUNDLE_VERSION_MISMATCH")
    return errors


def _unavailable_assessment(
    source: Mapping[str, Any], versions: Mapping[str, str | None], reasons: list[str]
) -> SelectionSufficiencyAssessment:
    data = {
        "assessment_version": SELECTION_SUFFICIENCY_VERSION,
        "status": "ASSESSMENT_UNAVAILABLE",
        "diagnostic_code": RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE,
        "source_identity": dict(source),
        "renderer_versions": dict(versions),
        "classifiers": {
            "richness_clustering_version": RICHNESS_CLUSTER_AUDIT_VERSION_V2,
            "reader_relevance_policy_version": RICHNESS_POLICY_VERSION_V3,
            "core_classifier_version": CORE_CLASSIFIER_V2,
            "evidence_applicability_version": "commentary-evidence-applicability-v1",
            "representation_heuristic_version": "authored-fact-lexical-anchor-v1",
        },
        "counts": {},
        "weighted_eligible_coverage": None,
        "thresholds": {
            "weighted_eligible_coverage_min": SELECTION_WEIGHTED_COVERAGE_MIN,
            "core_coverage_min": SELECTION_CORE_COVERAGE_MIN,
        },
        "reasons": sorted(set(reasons)),
        "dimensions": {
            "technical_validity": "NOT_ASSESSED_BY_SELECTION_GATE",
            "selection_sufficiency": "ASSESSMENT_UNAVAILABLE",
            "presentation_quality": "NOT_ASSESSED_BY_SELECTION_GATE",
        },
    }
    data["assessment_hash"] = _hash_json(data)
    return SelectionSufficiencyAssessment(**data)


def _blocks(commentary: Any) -> list[Any]:
    sections = commentary.get("sections", []) if isinstance(commentary, Mapping) else getattr(commentary, "sections", [])
    return [
        block
        for section in sections or []
        for block in (
            section.get("blocks", [])
            if isinstance(section, Mapping)
            else getattr(section, "blocks", [])
        ) or []
    ]


def _expresses(text: str, fact: str) -> bool:
    response_terms = _content_terms(text)
    fact_terms = _content_terms(fact)
    if not response_terms or not fact_terms:
        return False
    shared = response_terms.intersection(fact_terms)
    needed = 1 if len(fact_terms) <= 2 else max(2, math.ceil(len(fact_terms) * 0.25))
    return len(shared) >= needed


def _expresses_unit(text: str, unit: Any | None) -> bool:
    return bool(
        unit is not None
        and any(_expresses(text, fact) for fact in _sequence(unit, "facts"))
    )


def _content_terms(value: str) -> set[str]:
    return {
        token
        for token in _WORD_RE.findall(value.casefold())
        if len(token) >= 3 and not token.isdigit() and token not in _STOPWORDS
    }


def _sequence(value: Any, field: str) -> list[str]:
    raw = value.get(field, []) if isinstance(value, Mapping) else getattr(value, field, [])
    return [str(item) for item in (raw or [])]


def _text(value: Any, field: str) -> str:
    raw = value.get(field, "") if isinstance(value, Mapping) else getattr(value, field, "")
    return str(raw or "")


def _ratio(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 else round(numerator / denominator, 4)


def _hash_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "LEGACY_SELECTION_EXCEPTION_DECISION",
    "LEGACY_SELECTION_EXCEPTION_VERSION",
    "RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE",
    "RENDERER_SELECTION_COLLAPSE",
    "SELECTION_CORE_COVERAGE_MIN",
    "SELECTION_SUFFICIENCY_VERSION",
    "SELECTION_WEIGHTED_COVERAGE_MIN",
    "SelectionSufficiencyAssessment",
    "assess_selection_sufficiency",
    "validate_legacy_selection_exception",
    "validate_selection_assessment",
]
