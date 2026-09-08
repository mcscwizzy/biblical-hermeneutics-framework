"""Deterministic idea-density and reader-enrichment diagnostics.

This module deliberately sits beside :mod:`richness`.  It measures whether
compiled synthesis records collapse into a smaller set of reader-level ideas;
it does not alter EvidenceBundle, synthesis, commentary, or safety contracts.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Any, Iterable, Mapping

from .availability import evidence_contribution


RICHNESS_CLUSTER_AUDIT_VERSION = "commentary-richness-clusters-v1"
RICHNESS_POLICY_VERSION = "commentary-richness-policy-v2-proposed"
RICHNESS_GATE_V2_VERSION = "commentary-richness-gate-v2.1"
CORE_CLASSIFIER_V1 = "current-chapter-context-v1"
CORE_CLASSIFIER_V2 = "essential-passage-context-v2"

_WORD_RE = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?")
_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have he her his in is it its of on or that the their them they this to was were which who with".split()
)
_DUPLICATE_PRIORITY = {
    "DISTINCT": 0,
    "HIGH_FACT_OVERLAP": 1,
    "PARENT_PARALLEL": 2,
    "ANCESTRY_DUPLICATE": 3,
    "EXACT_DUPLICATE": 4,
}
_CLASS_PRIORITY = {
    "OPTIONAL": 0,
    "SURROUNDING": 1,
    "SUPPORTING": 2,
    "DISPUTED": 3,
    "CORE": 4,
}
_CLASS_WEIGHT = {
    "CORE": 1.0,
    "SUPPORTING": 0.7,
    "DISPUTED": 0.5,
    "OPTIONAL": 0.35,
    "SURROUNDING": 0.25,
}
_CATEGORY_FAMILIES = {
    "archaeology": "archaeology",
    "geography": "geography",
    "history": "history",
    "politics": "history",
    "culture": "culture",
    "social": "culture",
    "economics": "culture",
    "language": "language_literary",
    "literary": "language_literary",
    "chronology": "chronology",
}


class DuplicateReason(str, Enum):
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    ANCESTRY_DUPLICATE = "ANCESTRY_DUPLICATE"
    PARENT_PARALLEL = "PARENT_PARALLEL"
    HIGH_FACT_OVERLAP = "HIGH_FACT_OVERLAP"
    DISTINCT = "DISTINCT"


class QualityClass(str, Enum):
    CORE = "CORE"
    SUPPORTING = "SUPPORTING"
    OPTIONAL = "OPTIONAL"
    SURROUNDING = "SURROUNDING"
    DISPUTED = "DISPUTED"


class GateClass(str, Enum):
    """Chapter-level quality expectation selected from evidence and baseline."""

    ENRICHMENT_TARGET = "ENRICHMENT_TARGET"
    RICH_CONTROL = "RICH_CONTROL"
    EVIDENCE_LIMITED_CONTROL = "EVIDENCE_LIMITED_CONTROL"
    DATA_GAP_CONTROL = "DATA_GAP_CONTROL"


class DumpSeverity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class GateOutcome(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNING = "PASS_WITH_WARNING"
    QUALITY_FAIL = "QUALITY_FAIL"
    SAFETY_FAIL = "SAFETY_FAIL"


@dataclass(frozen=True)
class SynthesisIdeaCluster:
    """One deterministic reader-level idea represented by one or more units."""

    id: str
    kind: str
    synthesis_ids: list[str]
    evidence_ids: list[str]
    passage_scope: str
    concept_signature: str
    importance_weight: float
    duplicate_reason: str
    confidence: str
    quality_class: str
    unit_kinds: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    importance_basis: list[str] = field(default_factory=list)
    dispute_present: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceDumpDiagnostics:
    """Warnings, not safety failures, for record-shaped commentary."""

    signals: list[str]
    block_count: int
    consumed_synthesis_count: int
    consumed_cluster_count: int
    mean_evidence_ids_per_block: float
    block_to_synthesis_ratio: float
    consolidation_ratio: float
    repeated_block_count: int
    meaningful_cluster_count: int = 0
    block_to_cluster_ratio: float = 0.0
    consumed_unit_ratio: float = 0.0
    repeated_block_ratio: float = 0.0
    words_per_meaningful_cluster: float = 0.0
    normalized_signals: list[str] = field(default_factory=list)
    severity: str = DumpSeverity.NONE.value

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["signal_count"] = self.signal_count
        return result


@dataclass(frozen=True)
class RichnessClusterScore:
    """Comparable raw, cluster, weighted, category, and consolidation metrics."""

    synthesis_unit_count: int
    meaningful_cluster_count: int
    consumed_synthesis_count: int
    consumed_cluster_count: int
    raw_synthesis_coverage: float
    idea_cluster_coverage: float
    weighted_idea_coverage: float
    core_cluster_count: int
    consumed_core_cluster_count: int
    core_cluster_coverage: float
    available_category_count: int
    consumed_category_count: int
    category_coverage: float
    category_families: list[str]
    consumed_category_families: list[str]
    consolidation_ratio: float
    dump_diagnostics: EvidenceDumpDiagnostics
    clusters: list[SynthesisIdeaCluster]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["dump_diagnostics"] = self.dump_diagnostics.to_dict()
        return result


@dataclass(frozen=True)
class ProposedGateThresholds:
    """Candidate v2 thresholds; these are intentionally not the active gate."""

    weighted_idea_coverage_min: float = 0.55
    core_cluster_coverage_min: float = 0.75
    category_coverage_min: float = 0.60
    evidence_use_delta_min: int = 1
    max_dump_signals: int = 1
    max_boundary_repetition_ratio: float = 0.65


@dataclass(frozen=True)
class GateV2Thresholds:
    """Calibrated candidate thresholds for the scoring-only Gate v2."""

    weighted_idea_coverage_min: float = 0.50
    core_cluster_coverage_min: float = 0.75
    category_coverage_min: float = 0.60
    minimum_material_improvement_signals: int = 1
    dense_cluster_min: int = 16
    small_cluster_max: int = 5
    moderate_dump_signal_min: int = 2
    high_dump_signal_min: int = 3
    exhaustive_unit_ratio_min: float = 0.95
    one_block_unit_ratio_min: float = 0.95
    block_cluster_ratio_min: float = 1.75
    words_per_cluster_min: float = 55.0
    low_consolidation_max: float = 0.45
    repeated_block_ratio_min: float = 0.15
    control_word_max: int = 250
    max_boundary_repetition_ratio: float = 0.65


@dataclass(frozen=True)
class GateV2Assessment:
    """Auditable result for one chapter after independent safety checks."""

    gate_class: str
    outcome: str
    safety_pass: bool
    safety_checks: dict[str, bool]
    quality_checks: dict[str, bool]
    material_improvement_signals: list[str]
    reasons: list[str]
    dump_severity: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def cluster_synthesis_units(
    units: Iterable[Any],
    evidence_items: Iterable[Any] | Mapping[str, Any] | None = None,
    *,
    core_classifier: str = CORE_CLASSIFIER_V2,
) -> list[SynthesisIdeaCluster]:
    """Cluster units with stable IDs using only structural/textual signals.

    Union-find makes overlap transitive, while pair decisions are made from
    sorted units so input ordering cannot change the result.
    """

    ordered = sorted(list(units), key=lambda unit: _text(unit, "id"))
    evidence = _evidence_map(evidence_items)
    parents = list(range(len(ordered)))
    reasons: dict[tuple[int, int], str] = {}
    for left_index, left in enumerate(ordered):
        for right_index in range(left_index + 1, len(ordered)):
            right = ordered[right_index]
            reason = _duplicate_reason(left, right, evidence)
            if reason != DuplicateReason.DISTINCT.value:
                reasons[(left_index, right_index)] = reason
                _union(parents, left_index, right_index)

    groups: dict[int, list[int]] = {}
    for index in range(len(ordered)):
        groups.setdefault(_find(parents, index), []).append(index)

    clusters: list[SynthesisIdeaCluster] = []
    for indexes in groups.values():
        members = [ordered[index] for index in indexes]
        member_ids = sorted(_text(unit, "id") for unit in members)
        pair_reasons = [
            reason
            for (left, right), reason in reasons.items()
            if left in indexes and right in indexes
        ]
        duplicate_reason = max(
            pair_reasons or [DuplicateReason.DISTINCT.value],
            key=lambda value: _DUPLICATE_PRIORITY[value],
        )
        cluster_id = _cluster_id(member_ids)
        classifications = [
            _classify_unit_with_basis(unit, evidence, core_classifier)
            for unit in members
        ]
        classes = [value[0] for value in classifications]
        if all(value == QualityClass.SURROUNDING.value for value in classes):
            quality_class = QualityClass.SURROUNDING.value
        elif QualityClass.CORE.value in classes:
            quality_class = QualityClass.CORE.value
        elif QualityClass.DISPUTED.value in classes:
            quality_class = QualityClass.DISPUTED.value
        else:
            quality_class = max(classes, key=lambda value: _CLASS_PRIORITY[value])
        importance_basis = sorted(
            {
                basis
                for classified, bases in classifications
                if classified == quality_class
                for basis in bases
            }
        )
        categories = sorted(
            {
                family
                for unit in members
                for family in _unit_categories(unit, evidence)
            }
        )
        cluster_kind = _cluster_kind(members)
        scope = (
            "CURRENT_CHAPTER"
            if any(_text(unit, "passage_scope") == "CURRENT_CHAPTER" for unit in members)
            else "SURROUNDING_PASSAGE"
        )
        clusters.append(
            SynthesisIdeaCluster(
                id=cluster_id,
                kind=cluster_kind,
                synthesis_ids=member_ids,
                evidence_ids=sorted(
                    {
                        evidence_id
                        for unit in members
                        for evidence_id in _sequence(unit, "evidence_ids")
                    }
                ),
                passage_scope=scope,
                concept_signature=_concept_signature(members, evidence),
                importance_weight=_CLASS_WEIGHT[quality_class],
                duplicate_reason=duplicate_reason,
                confidence=_cluster_confidence(duplicate_reason),
                quality_class=quality_class,
                unit_kinds=sorted({_text(unit, "kind") for unit in members}),
                categories=categories,
                importance_basis=importance_basis,
                dispute_present=QualityClass.DISPUTED.value in classes,
            )
        )
    return sorted(clusters, key=lambda cluster: cluster.id)


def score_synthesis_richness(
    units: Iterable[Any],
    *,
    evidence_items: Iterable[Any] | Mapping[str, Any] | None = None,
    consumed_synthesis_ids: Iterable[str] = (),
    blocks: Iterable[Any] | None = None,
    passage_ref: str = "",
    core_classifier: str = CORE_CLASSIFIER_V2,
) -> RichnessClusterScore:
    """Calculate proposed v2 metrics without changing current richness."""

    ordered_units = list(units)
    clusters = cluster_synthesis_units(
        ordered_units, evidence_items, core_classifier=core_classifier
    )
    cluster_by_unit = {
        synthesis_id: cluster
        for cluster in clusters
        for synthesis_id in cluster.synthesis_ids
    }
    consumed_ids = {
        str(value) for value in consumed_synthesis_ids if str(value) in cluster_by_unit
    }
    consumed_clusters = {
        cluster.id
        for synthesis_id in consumed_ids
        for cluster in [cluster_by_unit[synthesis_id]]
    }
    meaningful = [cluster for cluster in clusters if cluster.quality_class != QualityClass.OPTIONAL.value]
    consumed_meaningful = [cluster for cluster in meaningful if cluster.id in consumed_clusters]
    raw_denominator = len(ordered_units)
    meaningful_denominator = len(meaningful)
    weighted_total = sum(cluster.importance_weight for cluster in meaningful)
    weighted_consumed = sum(
        cluster.importance_weight for cluster in consumed_meaningful
    )
    core = [cluster for cluster in meaningful if cluster.quality_class == QualityClass.CORE.value]
    consumed_core = [cluster for cluster in core if cluster.id in consumed_clusters]
    categories = sorted({category for cluster in meaningful for category in cluster.categories})
    consumed_categories = sorted(
        {
            category
            for cluster in consumed_meaningful
            if cluster.id in consumed_clusters
            for category in cluster.categories
        }
    )
    dump = evidence_dump_diagnostics(
        blocks or (),
        cluster_by_unit=cluster_by_unit,
        consumed_synthesis_ids=consumed_ids,
        passage_ref=passage_ref,
        meaningful_cluster_count=meaningful_denominator,
        synthesis_unit_count=raw_denominator,
    )
    return RichnessClusterScore(
        synthesis_unit_count=raw_denominator,
        meaningful_cluster_count=meaningful_denominator,
        consumed_synthesis_count=len(consumed_ids),
        consumed_cluster_count=len(consumed_clusters.intersection({c.id for c in meaningful})),
        raw_synthesis_coverage=_ratio(len(consumed_ids), raw_denominator),
        idea_cluster_coverage=_ratio(len(consumed_meaningful), meaningful_denominator),
        weighted_idea_coverage=_ratio(weighted_consumed, weighted_total),
        core_cluster_count=len(core),
        consumed_core_cluster_count=len(consumed_core),
        core_cluster_coverage=(
            1.0 if not core else _ratio(len(consumed_core), len(core))
        ),
        available_category_count=len(categories),
        consumed_category_count=len(consumed_categories),
        category_coverage=_ratio(len(consumed_categories), len(categories)),
        category_families=categories,
        consumed_category_families=consumed_categories,
        consolidation_ratio=dump.consolidation_ratio,
        dump_diagnostics=dump,
        clusters=clusters,
    )


def evidence_dump_diagnostics(
    blocks: Iterable[Any],
    *,
    cluster_by_unit: Mapping[str, SynthesisIdeaCluster] | None = None,
    consumed_synthesis_ids: Iterable[str] = (),
    passage_ref: str = "",
    meaningful_cluster_count: int | None = None,
    synthesis_unit_count: int | None = None,
    thresholds: GateV2Thresholds = GateV2Thresholds(),
) -> EvidenceDumpDiagnostics:
    """Detect record-shaped output using a density-normalized severity.

    A one-block-per-unit shape is deliberately not suspicious for a small
    chapter.  HIGH requires a dense chapter, near-exhaustive unit consumption,
    near one-block-per-unit output, and weak consolidation plus at least one
    additional density signal.  The individual normalized signals remain
    visible for audit and calibration.
    """

    values = list(blocks)
    consumed = {str(value) for value in consumed_synthesis_ids}
    block_synthesis = [
        [value for value in _sequence(block, "synthesis_ids") if not consumed or value in consumed]
        for block in values
    ]
    cluster_by_unit = cluster_by_unit or {}
    consumed_units = len(consumed)
    consumed_clusters = {
        cluster_by_unit[value].id
        for value in consumed
        if value in cluster_by_unit
    }
    evidence_counts = [len(set(_sequence(block, "evidence_ids"))) for block in values]
    mean_evidence = sum(evidence_counts) / len(evidence_counts) if evidence_counts else 0.0
    block_to_unit = _ratio(len(values), consumed_units)
    consolidation = _ratio(
        sum(max(0, count - 1) for count in evidence_counts),
        sum(evidence_counts),
    )
    repeated_blocks = _repeated_block_count(values)
    cluster_count = max(
        0,
        meaningful_cluster_count
        if meaningful_cluster_count is not None
        else len({cluster.id for cluster in consumed_clusters}),
    )
    block_cluster_ratio = _ratio(len(values), cluster_count)
    consumed_unit_ratio = _ratio(
        consumed_units,
        synthesis_unit_count if synthesis_unit_count is not None else max(consumed_units, 1),
    )
    repeated_ratio = _ratio(repeated_blocks, len(values))
    words_per_cluster = _ratio(_word_count(values), cluster_count)
    dense = cluster_count >= thresholds.dense_cluster_min
    normalized_signals: list[str] = []
    if dense and consumed_units and consumed_unit_ratio >= thresholds.exhaustive_unit_ratio_min:
        normalized_signals.append("DENSE_NEAR_EXHAUSTIVE_UNIT_CONSUMPTION")
    if dense and consumed_units and block_to_unit >= thresholds.one_block_unit_ratio_min:
        normalized_signals.append("DENSE_ONE_BLOCK_PER_UNIT")
    if dense and block_cluster_ratio >= thresholds.block_cluster_ratio_min:
        normalized_signals.append("HIGH_BLOCK_TO_CLUSTER_RATIO")
    if dense and words_per_cluster >= thresholds.words_per_cluster_min:
        normalized_signals.append("HIGH_WORDS_PER_CLUSTER")
    if dense and consolidation <= thresholds.low_consolidation_max:
        normalized_signals.append("LOW_CLUSTER_CONSOLIDATION")
    if len(values) >= 10 and mean_evidence <= 1.25:
        normalized_signals.append("LOW_EVIDENCE_PER_BLOCK_CONSOLIDATION")
    if len(values) >= 10 and repeated_ratio >= thresholds.repeated_block_ratio_min:
        normalized_signals.append("REPEATED_BLOCK_TEXT_DENSITY")

    # Preserve the v1 signal list exactly for historical comparison. These
    # signals are diagnostic only; v2 severity is based on normalized signals.
    signals: list[str] = []
    if consumed_units >= 10 and block_to_unit >= 0.9:
        signals.append("ONE_BLOCK_PER_SYNTHESIS_UNIT")
    if len(values) >= 10 and mean_evidence <= 1.25:
        signals.append("LOW_EVIDENCE_PER_BLOCK_CONSOLIDATION")
    if len(values) >= 20 and _word_count(values) > 1200:
        signals.append("HIGH_PROSE_WITH_MANY_RECORD_BLOCKS")
    if repeated_blocks:
        signals.append("REPEATED_BLOCK_TEXT")

    strong_density_signals = sum(
        value in normalized_signals
        for value in (
            "DENSE_NEAR_EXHAUSTIVE_UNIT_CONSUMPTION",
            "DENSE_ONE_BLOCK_PER_UNIT",
            "HIGH_BLOCK_TO_CLUSTER_RATIO",
            "HIGH_WORDS_PER_CLUSTER",
            "REPEATED_BLOCK_TEXT_DENSITY",
        )
    )
    high = (
        dense
        and "DENSE_NEAR_EXHAUSTIVE_UNIT_CONSUMPTION" in normalized_signals
        and "DENSE_ONE_BLOCK_PER_UNIT" in normalized_signals
        and "LOW_CLUSTER_CONSOLIDATION" in normalized_signals
        and strong_density_signals >= thresholds.high_dump_signal_min
    )
    if high:
        severity = DumpSeverity.HIGH.value
    elif dense and strong_density_signals >= thresholds.moderate_dump_signal_min:
        severity = DumpSeverity.MODERATE.value
    elif normalized_signals:
        severity = DumpSeverity.LOW.value
    else:
        severity = DumpSeverity.NONE.value
    return EvidenceDumpDiagnostics(
        signals=signals,
        block_count=len(values),
        consumed_synthesis_count=consumed_units,
        consumed_cluster_count=len(consumed_clusters),
        mean_evidence_ids_per_block=round(mean_evidence, 4),
        block_to_synthesis_ratio=round(block_to_unit, 4),
        consolidation_ratio=round(consolidation, 4),
        repeated_block_count=repeated_blocks,
        meaningful_cluster_count=cluster_count,
        block_to_cluster_ratio=round(block_cluster_ratio, 4),
        consumed_unit_ratio=round(consumed_unit_ratio, 4),
        repeated_block_ratio=round(repeated_ratio, 4),
        words_per_meaningful_cluster=round(words_per_cluster, 4),
        normalized_signals=normalized_signals,
        severity=severity,
    )


def proposed_gate_passes(
    *,
    score: RichnessClusterScore,
    evidence_availability: str,
    validation_clean: bool,
    boilerplate_detected: bool,
    evidence_use_delta: int,
    boundary_repetition_ratio: float = 0.0,
    thresholds: ProposedGateThresholds = ProposedGateThresholds(),
) -> tuple[bool, dict[str, bool]]:
    """Evaluate candidate quality semantics after independent safety checks."""

    checks = {
        "evidence_available": evidence_availability == "AVAILABLE",
        "validation_clean": validation_clean,
        "boilerplate_absent": not boilerplate_detected,
        "core_coverage_adequate": score.core_cluster_coverage >= thresholds.core_cluster_coverage_min,
        "weighted_idea_coverage_adequate": score.weighted_idea_coverage >= thresholds.weighted_idea_coverage_min,
        "category_coverage_adequate": score.category_coverage >= thresholds.category_coverage_min,
        "evidence_use_increased": evidence_use_delta >= thresholds.evidence_use_delta_min,
        "evidence_dump_below_limit": score.dump_diagnostics.signal_count <= thresholds.max_dump_signals,
        "boundary_repetition_below_limit": boundary_repetition_ratio < thresholds.max_boundary_repetition_ratio,
    }
    return all(checks.values()), checks


def classify_gate_class(evidence_availability: str, baseline_richness: str) -> str:
    """Select a chapter expectation without conflating evidence and quality."""

    if evidence_availability == "DATA_GAP":
        return GateClass.DATA_GAP_CONTROL.value
    if baseline_richness == "RICH_ENOUGH":
        return GateClass.RICH_CONTROL.value
    if evidence_availability == "THIN" or baseline_richness == "EVIDENCE_GAP":
        return GateClass.EVIDENCE_LIMITED_CONTROL.value
    if evidence_availability == "AVAILABLE" and baseline_richness == "SYNTHESIS_GAP":
        return GateClass.ENRICHMENT_TARGET.value
    raise ValueError(
        f"cannot classify chapter with availability={evidence_availability!r} "
        f"and baseline={baseline_richness!r}"
    )


def assess_gate_v2(
    *,
    score: RichnessClusterScore,
    evidence_availability: str,
    baseline_richness: str,
    after_richness: str | None,
    safety_checks: Mapping[str, bool] | None = None,
    validation_clean: bool | None = None,
    boilerplate_detected: bool = False,
    evidence_use_delta: int = 0,
    section_delta: int = 0,
    boilerplate_removed: bool = False,
    boundary_repetition_ratio: float = 0.0,
    commentary_word_count: int | None = None,
    unique_evidence_ids_consumed: int | None = None,
    thresholds: GateV2Thresholds = GateV2Thresholds(),
) -> GateV2Assessment:
    """Apply class-specific v2.1 quality after mandatory safety assessment.

    ``safety_checks`` is deliberately explicit so callers cannot accidentally
    turn a quality score into a substitute for validation/provenance gates.
    The compatibility ``validation_clean`` argument supports focused unit
    tests and is folded into the same hard safety result.
    """

    gate_class = classify_gate_class(evidence_availability, baseline_richness)
    checks = dict(safety_checks or {})
    if validation_clean is not None:
        checks["validation_clean"] = validation_clean
    if not checks:
        checks["validation_clean"] = True
    safety_pass = all(checks.values())
    quality: dict[str, bool] = {}
    improvement_signals: list[str] = []
    reasons: list[str] = []
    dump_severity = score.dump_diagnostics.severity

    if evidence_use_delta > 0:
        improvement_signals.append("evidence_utilization")
    if score.consumed_cluster_count > 0:
        improvement_signals.append("idea_cluster_coverage")
    if section_delta > 0:
        improvement_signals.append("useful_sections")
    if boilerplate_removed:
        improvement_signals.append("boilerplate_removed")
    if score.consolidation_ratio >= 0.2:
        improvement_signals.append("coherent_consolidation")

    if gate_class == GateClass.ENRICHMENT_TARGET.value:
        quality = {
            "boilerplate_absent": not boilerplate_detected,
            "core_coverage_adequate": score.core_cluster_coverage >= thresholds.core_cluster_coverage_min,
            "weighted_coverage_adequate": score.weighted_idea_coverage >= thresholds.weighted_idea_coverage_min,
            "category_coverage_adequate": score.category_coverage >= thresholds.category_coverage_min,
            "material_improvement": len(set(improvement_signals)) >= thresholds.minimum_material_improvement_signals,
            "boundary_repetition_below_limit": boundary_repetition_ratio < thresholds.max_boundary_repetition_ratio,
            "not_high_dump": dump_severity != DumpSeverity.HIGH.value,
        }
        reasons.append("AVAILABLE + SYNTHESIS_GAP requires calibrated enrichment signals")
    elif gate_class == GateClass.RICH_CONTROL.value:
        quality = {
            "remains_rich_enough": after_richness == "RICH_ENOUGH",
            "no_evidence_regression": evidence_use_delta >= -1,
            "no_new_boilerplate": not boilerplate_detected,
            "not_high_dump": dump_severity != DumpSeverity.HIGH.value,
        }
        reasons.append("baseline RICH_ENOUGH requires non-regression only")
    elif gate_class == GateClass.EVIDENCE_LIMITED_CONTROL.value:
        quality = {
            "post_render_classification_valid": after_richness in {"EVIDENCE_GAP", "SYNTHESIS_GAP", "RICH_ENOUGH"},
            "supported_evidence_represented": (
                score.meaningful_cluster_count == 0
                or score.consumed_cluster_count > 0
            ),
            "no_unsupported_enrichment": evidence_use_delta >= 0,
            "no_forced_filler": not boilerplate_detected,
            "proportionate_to_evidence": (
                commentary_word_count is None
                or commentary_word_count <= thresholds.control_word_max
            ),
            "not_high_dump": dump_severity != DumpSeverity.HIGH.value,
        }
        reasons.append("THIN or EVIDENCE_GAP is judged for safe, proportionate restraint, not enrichment thresholds")
    else:
        quality = {
            "remains_evidence_gap": after_richness == "EVIDENCE_GAP",
            "zero_evidence_consumed": (unique_evidence_ids_consumed or 0) == 0,
            "concise": commentary_word_count is None or commentary_word_count <= thresholds.control_word_max,
            "not_high_dump": dump_severity != DumpSeverity.HIGH.value,
        }
        reasons.append("DATA_GAP is judged for safe restraint, not enrichment")

    if not safety_pass:
        outcome = GateOutcome.SAFETY_FAIL.value
        reasons.append("mandatory safety checks failed")
    elif not all(quality.values()):
        outcome = GateOutcome.QUALITY_FAIL.value
        reasons.append("one or more class-specific quality checks failed")
    elif dump_severity in {DumpSeverity.LOW.value, DumpSeverity.MODERATE.value}:
        outcome = GateOutcome.PASS_WITH_WARNING.value
        reasons.append(f"dump severity is {dump_severity}; retained as warning")
    else:
        outcome = GateOutcome.PASS.value

    return GateV2Assessment(
        gate_class=gate_class,
        outcome=outcome,
        safety_pass=safety_pass,
        safety_checks=checks,
        quality_checks=quality,
        material_improvement_signals=sorted(set(improvement_signals)),
        reasons=reasons,
        dump_severity=dump_severity,
    )


def _duplicate_reason(left: Any, right: Any, evidence: Mapping[str, Any]) -> str:
    left_ids = set(_sequence(left, "evidence_ids"))
    right_ids = set(_sequence(right, "evidence_ids"))
    left_facts = _fact_signature(left)
    right_facts = _fact_signature(right)
    if left_facts == right_facts and left_facts:
        return DuplicateReason.EXACT_DUPLICATE.value
    if left_ids == right_ids and left_ids:
        return DuplicateReason.ANCESTRY_DUPLICATE.value
    if set(_sequence(left, "related_unit_ids")).intersection({_text(right, "id")}) or set(
        _sequence(right, "related_unit_ids")
    ).intersection({_text(left, "id")}):
        return DuplicateReason.ANCESTRY_DUPLICATE.value
    left_parents = _parent_families(left, evidence)
    right_parents = _parent_families(right, evidence)
    same_shape = (
        _text(left, "kind") == _text(right, "kind")
        and _text(left, "passage_scope") == _text(right, "passage_scope")
    )
    # Relationship units are already linked to their source unit.  Allowing
    # parent-parallel matching between two ``why_it_matters`` units would let
    # unrelated source kinds merge transitively through a generic parent.
    if (
        same_shape
        and _text(left, "kind") != "why_it_matters"
        and left_parents.intersection(right_parents)
    ):
        return DuplicateReason.PARENT_PARALLEL.value
    if same_shape and _fact_overlap(left_facts, right_facts):
        return DuplicateReason.HIGH_FACT_OVERLAP.value
    return DuplicateReason.DISTINCT.value


def classify_unit_v1(unit: Any, evidence: Mapping[str, Any]) -> str:
    """Preserve the pre-v2 CORE heuristic for historical comparison."""

    if _text(unit, "passage_scope") == "SURROUNDING_PASSAGE":
        return QualityClass.SURROUNDING.value
    items = [evidence[item_id] for item_id in _sequence(unit, "evidence_ids") if item_id in evidence]
    if _text(unit, "interpretation_level") == "disputed" or any(_is_disputed(item) for item in items):
        return QualityClass.DISPUTED.value
    metadata = getattr(unit, "metadata", None) or _mapping(unit, "metadata")
    if metadata.get("explicit_significance"):
        return QualityClass.CORE.value
    if any((getattr(item, "relevance_metadata", None) or {}).get("presentation_role") == "dig_deeper" for item in items):
        return QualityClass.OPTIONAL.value
    if _text(unit, "kind") in {"chapter_overview", "things_easy_to_miss"}:
        return QualityClass.CORE.value
    if _text(unit, "kind") == "why_it_matters":
        return QualityClass.SUPPORTING.value
    if _sequence(unit, "entity_ids"):
        return QualityClass.CORE.value
    if any(
        evidence_contribution(item, "").specific
        and _text(item, "category") in {"archaeology", "geography", "chronology", "language"}
        for item in items
    ):
        return QualityClass.SUPPORTING.value
    return QualityClass.SUPPORTING.value


def _classify_unit_with_basis(
    unit: Any,
    evidence: Mapping[str, Any],
    core_classifier: str,
) -> tuple[str, list[str]]:
    if core_classifier == CORE_CLASSIFIER_V1:
        value = classify_unit_v1(unit, evidence)
        return value, ["legacy_current_chapter_context"] if value == QualityClass.CORE.value else []
    if core_classifier != CORE_CLASSIFIER_V2:
        raise ValueError(f"unknown core classifier: {core_classifier}")
    items = [
        evidence[item_id]
        for item_id in _sequence(unit, "evidence_ids")
        if item_id in evidence
    ]
    if _text(unit, "interpretation_level") == "disputed" or any(
        _is_disputed(item) for item in items
    ):
        return QualityClass.DISPUTED.value, ["disputed_or_contested_evidence"]
    metadata = getattr(unit, "metadata", None) or _mapping(unit, "metadata")
    if metadata.get("explicit_significance"):
        return QualityClass.CORE.value, ["explicit_passage_significance"]
    if any(
        (getattr(item, "relevance_metadata", None) or {}).get("presentation_role")
        == "dig_deeper"
        for item in items
    ):
        return QualityClass.OPTIONAL.value, ["dig_deeper_presentation_role"]
    if _text(unit, "kind") in {"chapter_overview", "things_easy_to_miss"}:
        return QualityClass.CORE.value, ["passage_understanding_unit_kind"]
    direct = any(
        str((getattr(item, "relevance_metadata", None) or {}).get("passage_relationship"))
        .casefold()
        == "direct"
        or str((getattr(item, "relevance_metadata", None) or {}).get("semantic_relationship"))
        .casefold()
        == "direct_context"
        or str((getattr(item, "relevance_metadata", None) or {}).get("claim_type"))
        .casefold()
        == "biblical_text"
        for item in items
    )
    if direct:
        return QualityClass.CORE.value, ["direct_passage_context"]
    if _text(unit, "passage_scope") == "SURROUNDING_PASSAGE":
        return QualityClass.SURROUNDING.value, ["surrounding_passage_scope"]
    if _sequence(unit, "entity_ids"):
        return QualityClass.SUPPORTING.value, ["entity_background_not_direct_passage_context"]
    if any(
        evidence_contribution(item, "").specific
        and _text(item, "category") in {"archaeology", "geography", "chronology", "language"}
        for item in items
    ):
        return QualityClass.SUPPORTING.value, ["specific_contextual_support"]
    return QualityClass.SUPPORTING.value, ["general_contextual_support"]


def _classify_unit(unit: Any, evidence: Mapping[str, Any]) -> str:
    """Return the v2 class used by the current diagnostic default."""

    return _classify_unit_with_basis(unit, evidence, CORE_CLASSIFIER_V2)[0]


def _unit_categories(unit: Any, evidence: Mapping[str, Any]) -> set[str]:
    categories = set()
    for item_id in _sequence(unit, "evidence_ids"):
        item = evidence.get(item_id)
        category = _text(item, "category") if item is not None else ""
        if category in _CATEGORY_FAMILIES:
            categories.add(_CATEGORY_FAMILIES[category])
    kind = _text(unit, "kind")
    if kind == "interpretive_questions":
        categories.add("interpretive_questions")
    elif kind == "surrounding_passages":
        categories.add("surrounding_passages")
    return categories


def _parent_families(unit: Any, evidence: Mapping[str, Any]) -> set[str]:
    values = set()
    for item_id in _sequence(unit, "evidence_ids"):
        item = evidence.get(item_id)
        metadata = (getattr(item, "relevance_metadata", None) or {}) if item is not None else {}
        parent = str(metadata.get("parent_object_id") or "").strip().casefold()
        if parent.startswith("what-is-the-"):
            parent = parent[len("what-is-the-"):]
        elif parent.startswith("what-is-"):
            parent = parent[len("what-is-"):]
        if parent:
            values.add(parent)
    return values


def _concept_signature(units: list[Any], evidence: Mapping[str, Any]) -> str:
    kinds = sorted({_text(unit, "kind") for unit in units})
    parents = sorted({parent for unit in units for parent in _parent_families(unit, evidence)})
    facts = sorted({_fact_signature(unit) for unit in units})
    return "|".join(["kind=" + ",".join(kinds), "parents=" + ",".join(parents), "facts=" + ";".join(facts)])


def _cluster_kind(units: list[Any]) -> str:
    values = sorted({_text(unit, "kind") for unit in units})
    non_derived = [value for value in values if value != "why_it_matters"]
    return non_derived[0] if non_derived else values[0]


def _cluster_confidence(reason: str) -> str:
    if reason in {DuplicateReason.EXACT_DUPLICATE.value, DuplicateReason.ANCESTRY_DUPLICATE.value}:
        return "high"
    if reason == DuplicateReason.PARENT_PARALLEL.value:
        return "medium"
    return "low"


def _fact_signature(unit: Any) -> str:
    facts = sorted(_normalize_fact(value) for value in _sequence(unit, "facts"))
    return ";".join(value for value in facts if value)


def _normalize_fact(value: Any) -> str:
    words = [word for word in _WORD_RE.findall(str(value).casefold()) if word not in _STOPWORDS]
    return " ".join(words)


def _fact_overlap(left: str, right: str) -> bool:
    if not left or not right:
        return False
    sequence = SequenceMatcher(None, left, right).ratio()
    left_words, right_words = set(left.split()), set(right.split())
    shared = left_words.intersection(right_words)
    containment = len(shared) / max(1, min(len(left_words), len(right_words)))
    return sequence >= 0.78 or (containment >= 0.70 and len(shared) >= 4)


def _evidence_map(values: Iterable[Any] | Mapping[str, Any] | None) -> dict[str, Any]:
    if values is None:
        return {}
    if isinstance(values, Mapping):
        return {str(key): value for key, value in values.items()}
    return {_text(value, "id"): value for value in values}


def _is_disputed(item: Any) -> bool:
    metadata = getattr(item, "relevance_metadata", None) or {}
    if metadata.get("disputed") is True:
        return True
    status = str(metadata.get("dispute_status") or "").casefold()
    certainty = str(metadata.get("certainty") or "").casefold()
    return status not in {"", "not_disputed", "undisputed", "supported", "established", "none", "unknown"} or certainty in {"disputed", "speculative", "insufficient_evidence", "contested", "uncertain"}


def _repeated_block_count(blocks: list[Any]) -> int:
    seen: Counter[str] = Counter(_normalize_fact(_text(block, "text")) for block in blocks)
    return sum(count - 1 for count in seen.values() if count > 1)


def _word_count(blocks: list[Any]) -> int:
    return sum(len(_WORD_RE.findall(_text(block, "text"))) for block in blocks)


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _cluster_id(synthesis_ids: list[str]) -> str:
    payload = "\n".join(synthesis_ids).encode("utf-8")
    return "idea_cluster_" + hashlib.sha256(payload).hexdigest()[:12]


def _find(parents: list[int], index: int) -> int:
    while parents[index] != index:
        parents[index] = parents[parents[index]]
        index = parents[index]
    return index


def _union(parents: list[int], left: int, right: int) -> None:
    left_root, right_root = _find(parents, left), _find(parents, right)
    if left_root != right_root:
        parents[right_root] = left_root


def _text(value: Any, field: str) -> str:
    if value is None:
        return ""
    if isinstance(value, Mapping):
        return str(value.get(field) or "")
    return str(getattr(value, field, "") or "")


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        result = value.get(field) or {}
    else:
        result = getattr(value, field, {}) or {}
    return dict(result) if isinstance(result, Mapping) else {}


def _sequence(value: Any, field: str) -> list[str]:
    if isinstance(value, Mapping):
        result = value.get(field) or []
    else:
        result = getattr(value, field, []) or []
    return [str(item) for item in result]
