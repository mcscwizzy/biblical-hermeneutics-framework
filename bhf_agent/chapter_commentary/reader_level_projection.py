"""Deterministic reader-level idea projection for renderer diagnostics.

This module is intentionally downstream of compiled synthesis and richness
eligibility.  It is a navigation/index layer: it does not change evidence,
synthesis, scoring, or commentary validation, and it never calls a model.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from typing import Any, Iterable, Mapping

from .richness_clusters import CoverageEligibility


READER_LEVEL_IDEA_PROJECTION_VERSION = "reader-level-idea-projection-v1"
READER_LEVEL_IDEA_PROJECTION_IMPLEMENTATION = (
    "bhf_agent.chapter_commentary.reader_level_projection"
)

_ELIGIBLE = frozenset(
    {CoverageEligibility.REQUIRED.value, CoverageEligibility.RELEVANT.value}
)
_DISPUTED_VALUES = frozenset(
    {"disputed", "speculative", "insufficient_evidence", "contested", "uncertain"}
)
_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have he her his in is it its of on or that the their them they this to was were which who with".split()
)
_WORD_RE = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?")
_PARENT_PREFIX_RE = re.compile(
    r"^(?:what-is-the-significance-of|what-is-the|what-is|significance-of)-?"
)
_GENERIC_PARENT_TOKENS = frozenset({"the", "theme", "symbol", "significance"})
_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
_KIND_FAMILIES = {
    "chapter_overview": "overview",
    "historical_context": "history",
    "cultural_context": "culture",
    "people_places": "entities",
    "archaeology_geography": "place",
    "language_literary": "language",
    "chronology": "chronology",
    "surrounding_passages": "surrounding",
    "interpretive_questions": "interpretive",
    "things_easy_to_miss": "overview",
    "why_it_matters": "significance",
}


@dataclass(frozen=True)
class ReaderLevelIdea:
    """One auditable reader-level concept projected from eligible clusters."""

    idea_id: str
    label: str
    label_source: str
    importance: str
    categories: list[str]
    cluster_ids: list[str]
    synthesis_unit_ids: list[str]
    evidence_ids: list[str]
    ancestry_hashes: dict[str, str]
    disputed: bool
    status: str
    confidence: str
    source_order: dict[str, Any]
    grouping_reason: str
    grouping_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectionPairAudit:
    """Why two eligible clusters were or were not grouped."""

    left_cluster_id: str
    right_cluster_id: str
    decision: str
    reason: str
    shared_synthesis_ids: list[str] = field(default_factory=list)
    shared_evidence_ids: list[str] = field(default_factory=list)
    shared_parent_topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReaderLevelIdeaProjection:
    """Content-addressed projection and its complete grouping audit."""

    reference: str
    book: str
    chapter: int
    projection_version: str
    implementation_identity: str
    evidence_hash: str
    synthesis_hash: str
    synthesis_schema_version: str
    synthesis_compiler_version: str
    evidence_bundle_version: str
    source_synthesis_unit_count: int
    source_cluster_count: int
    eligible_cluster_count: int
    ideas: list[ReaderLevelIdea]
    pair_audit: list[ProjectionPairAudit]
    ambiguous_cluster_ids: list[str]
    ancestry_audit: dict[str, Any]
    projection_hash: str

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        result = {
            "reference": self.reference,
            "book": self.book,
            "chapter": self.chapter,
            "projection_version": self.projection_version,
            "implementation_identity": self.implementation_identity,
            "evidence_hash": self.evidence_hash,
            "synthesis_hash": self.synthesis_hash,
            "synthesis_schema_version": self.synthesis_schema_version,
            "synthesis_compiler_version": self.synthesis_compiler_version,
            "evidence_bundle_version": self.evidence_bundle_version,
            "source_synthesis_unit_count": self.source_synthesis_unit_count,
            "source_cluster_count": self.source_cluster_count,
            "eligible_cluster_count": self.eligible_cluster_count,
            "ideas": [idea.to_dict() for idea in self.ideas],
            "pair_audit": [audit.to_dict() for audit in self.pair_audit],
            "ambiguous_cluster_ids": self.ambiguous_cluster_ids,
            "ancestry_audit": self.ancestry_audit,
        }
        if include_hash:
            result["projection_hash"] = self.projection_hash
        return result


def project_reader_level_ideas(
    synthesis: Any,
    clusters: Iterable[Any],
    evidence_items: Iterable[Any] | Mapping[str, Any] | None = None,
) -> ReaderLevelIdeaProjection:
    """Project eligible richness clusters into deterministic reader ideas.

    ``clusters`` should be the output of the frozen richness cluster contract.
    Passing all clusters is supported; non-eligible records are excluded by
    their existing coverage classification and are never silently promoted.
    """

    synthesis_units = _sequence_objects(synthesis, "synthesis_units")
    unit_map = {_text(unit, "id"): unit for unit in synthesis_units}
    if len(unit_map) != len(synthesis_units):
        raise ProjectionError("synthesis contains duplicate unit IDs")
    evidence = _mapping_by_id(evidence_items)
    all_clusters = sorted(list(clusters), key=lambda cluster: _text(cluster, "id"))
    cluster_ids = [_text(cluster, "id") for cluster in all_clusters]
    if not all(value for value in cluster_ids) or len(set(cluster_ids)) != len(cluster_ids):
        raise ProjectionError("clusters must have unique non-empty IDs")
    eligible = [
        cluster
        for cluster in all_clusters
        if _text(cluster, "coverage_eligibility") in _ELIGIBLE
    ]
    for cluster in eligible:
        _validate_cluster_ancestry(cluster, unit_map)

    unit_order = {
        _text(unit, "id"): index + 1
        for index, unit in enumerate(_sequence_objects(synthesis, "synthesis_units"))
    }
    pair_audit = _pair_audits(eligible, unit_map, evidence)
    groups = _complete_linkage_groups(eligible, pair_audit)
    ideas = [
        _idea_for_group(
            group,
            unit_map=unit_map,
            evidence=evidence,
            unit_order=unit_order,
            synthesis=synthesis,
            pair_audit=pair_audit,
        )
        for group in groups
    ]
    ideas.sort(key=lambda idea: (idea.source_order["first_unit_ordinal"], idea.idea_id))
    ambiguous_cluster_ids = sorted(
        {
            cluster_id
            for audit in pair_audit
            if audit.decision == "KEEP_SEPARATE_AMBIGUOUS"
            for cluster_id in (audit.left_cluster_id, audit.right_cluster_id)
        }
    )
    source_eligible_ids = {
        _text(cluster, "id") for cluster in eligible
    }
    projected_ids = {cluster_id for idea in ideas for cluster_id in idea.cluster_ids}
    source_units = {
        unit_id
        for cluster in eligible
        for unit_id in _sequence(cluster, "synthesis_ids")
    }
    projected_units = {unit_id for idea in ideas for unit_id in idea.synthesis_unit_ids}
    source_evidence = {
        evidence_id
        for cluster in eligible
        for evidence_id in _sequence(cluster, "evidence_ids")
    }
    projected_evidence = {evidence_id for idea in ideas for evidence_id in idea.evidence_ids}
    ancestry_audit = {
        "eligible_cluster_ids_preserved": source_eligible_ids == projected_ids,
        "synthesis_unit_ids_preserved": source_units == projected_units,
        "evidence_ids_preserved": source_evidence == projected_evidence,
        "invented_synthesis_ids": sorted(projected_units - set(unit_map)),
        "invented_evidence_ids": sorted(projected_evidence - set(evidence))
        if evidence
        else [],
        "eligible_clusters_without_ideas": sorted(source_eligible_ids - projected_ids),
        "source_eligible_cluster_count": len(source_eligible_ids),
        "projected_cluster_count": len(projected_ids),
        "source_synthesis_unit_count": len(source_units),
        "projected_synthesis_unit_count": len(projected_units),
        "source_evidence_count": len(source_evidence),
        "projected_evidence_count": len(projected_evidence),
    }
    if not all(
        ancestry_audit[key]
        for key in (
            "eligible_cluster_ids_preserved",
            "synthesis_unit_ids_preserved",
            "evidence_ids_preserved",
        )
    ):
        raise ProjectionError(f"projection ancestry loss: {ancestry_audit}")
    if ancestry_audit["invented_synthesis_ids"] or ancestry_audit["invented_evidence_ids"]:
        raise ProjectionError(f"projection invented ancestry: {ancestry_audit}")

    base = {
        "reference": _text(synthesis, "reference"),
        "book": _text(synthesis, "book"),
        "chapter": int(_value(synthesis, "chapter", 0)),
        "projection_version": READER_LEVEL_IDEA_PROJECTION_VERSION,
        "implementation_identity": READER_LEVEL_IDEA_PROJECTION_IMPLEMENTATION,
        "evidence_hash": _text(synthesis, "evidence_hash"),
        "synthesis_hash": _text(synthesis, "synthesis_hash"),
        "synthesis_schema_version": _text(synthesis, "synthesis_schema_version"),
        "synthesis_compiler_version": _text(synthesis, "synthesis_compiler_version"),
        "evidence_bundle_version": _text(synthesis, "evidence_bundle_version"),
        "source_synthesis_unit_count": len(unit_map),
        "source_cluster_count": len(all_clusters),
        "eligible_cluster_count": len(eligible),
        "ideas": [idea.to_dict() for idea in ideas],
        "pair_audit": [audit.to_dict() for audit in pair_audit],
        "ambiguous_cluster_ids": ambiguous_cluster_ids,
        "ancestry_audit": ancestry_audit,
    }
    projection_hash = _sha256_json(base)
    return ReaderLevelIdeaProjection(
        reference=base["reference"],
        book=base["book"],
        chapter=base["chapter"],
        projection_version=base["projection_version"],
        implementation_identity=base["implementation_identity"],
        evidence_hash=base["evidence_hash"],
        synthesis_hash=base["synthesis_hash"],
        synthesis_schema_version=base["synthesis_schema_version"],
        synthesis_compiler_version=base["synthesis_compiler_version"],
        evidence_bundle_version=base["evidence_bundle_version"],
        source_synthesis_unit_count=base["source_synthesis_unit_count"],
        source_cluster_count=base["source_cluster_count"],
        eligible_cluster_count=base["eligible_cluster_count"],
        ideas=ideas,
        pair_audit=pair_audit,
        ambiguous_cluster_ids=ambiguous_cluster_ids,
        ancestry_audit=ancestry_audit,
        projection_hash=projection_hash,
    )


def render_projection_input_section(projection: ReaderLevelIdeaProjection) -> str:
    """Render a deterministic navigation section for a diagnostic prompt."""

    lines = [
        "DISTINCT READER-LEVEL IDEAS",
        "",
        "The following deterministic index groups existing synthesis records into",
        "distinct reader-relevant ideas. It is a navigation aid, not a replacement",
        "for the compiled synthesis or citation ancestry below.",
        "",
        "CORE:",
    ]
    core = [idea for idea in projection.ideas if idea.importance == "CORE"]
    relevant = [idea for idea in projection.ideas if idea.importance == "RELEVANT"]
    lines.extend(_render_idea_line(idea) for idea in core)
    if not core:
        lines.append("- None")
    lines.extend(
        [
            "",
            "RELEVANT:",
        ]
    )
    lines.extend(_render_idea_line(idea) for idea in relevant)
    if not relevant:
        lines.append("- None")
    lines.extend(
        [
            "",
            "Each item is grounded in the synthesis ancestry supplied below.",
            "Use these ideas to ensure conceptual breadth. Do not treat this list",
            "as a requirement to create one sentence per item. Synthesize naturally",
            "and avoid repetition.",
        ]
    )
    return "\n".join(lines)


def _render_idea_line(idea: ReaderLevelIdea) -> str:
    categories = ", ".join(idea.categories) or "uncategorized"
    return f"- {idea.idea_id}: {idea.label} (categories: {categories})"


def add_projection_to_prompt(
    original_prompt: str, projection: ReaderLevelIdeaProjection
) -> str:
    """Add the experimental projection view without changing prompt 1.7 text."""

    marker = "CANONICAL TEXT:\n"
    if marker not in original_prompt:
        raise ProjectionError("prompt does not contain the canonical-text marker")
    section = render_projection_input_section(projection)
    return original_prompt.replace(marker, f"{section}\n\n{marker}", 1)


class ProjectionError(ValueError):
    """Raised when a projection input violates existing ancestry contracts."""


def _pair_audits(
    clusters: list[Any], unit_map: Mapping[str, Any], evidence: Mapping[str, Any]
) -> list[ProjectionPairAudit]:
    audits: list[ProjectionPairAudit] = []
    for index, left in enumerate(clusters):
        for right in clusters[index + 1 :]:
            audits.append(_pair_audit(left, right, unit_map, evidence))
    return audits


def _pair_audit(
    left: Any,
    right: Any,
    unit_map: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> ProjectionPairAudit:
    left_units = set(_sequence(left, "synthesis_ids"))
    right_units = set(_sequence(right, "synthesis_ids"))
    left_evidence = set(_sequence(left, "evidence_ids"))
    right_evidence = set(_sequence(right, "evidence_ids"))
    shared_units = sorted(left_units & right_units)
    shared_evidence = sorted(left_evidence & right_evidence)
    left_scope = _text(left, "passage_scope")
    right_scope = _text(right, "passage_scope")
    left_parents = _parent_topics(left, evidence)
    right_parents = _parent_topics(right, evidence)
    shared_parents = sorted(left_parents & right_parents)
    if left_scope != right_scope:
        return _pair_result(
            left,
            right,
            "KEEP_SEPARATE_SCOPE",
            "SCOPE_BOUNDARY",
            shared_units,
            shared_evidence,
            shared_parents,
        )
    if shared_units or shared_evidence:
        return _pair_result(
            left,
            right,
            "GROUP",
            "EXACT_ANCESTRY_OVERLAP",
            shared_units,
            shared_evidence,
            shared_parents,
        )
    cross_related = bool(
        set(_related_unit_ids(left, unit_map)) & right_units
        or set(_related_unit_ids(right, unit_map)) & left_units
    )
    if cross_related:
        return _pair_result(
            left,
            right,
            "GROUP",
            "EXPLICIT_UNIT_RELATIONSHIP",
            shared_units,
            shared_evidence,
            shared_parents,
        )
    high_fact_overlap = _high_fact_overlap(left, right, unit_map)
    same_kind_family = _kind_families(left, unit_map) & _kind_families(right, unit_map)
    if shared_parents:
        return _pair_result(
            left,
            right,
            "GROUP",
            "SHARED_NORMALIZED_PARENT_TOPIC_AND_COMPATIBLE_SCOPE",
            shared_units,
            shared_evidence,
            shared_parents,
        )
    if high_fact_overlap and same_kind_family:
        return _pair_result(
            left,
            right,
            "GROUP",
            "HIGH_FACT_OVERLAP_WITH_COMPATIBLE_KIND_FAMILY",
            shared_units,
            shared_evidence,
            shared_parents,
        )
    if shared_parents or high_fact_overlap:
        return _pair_result(
            left,
            right,
            "KEEP_SEPARATE_AMBIGUOUS",
            "AMBIGUOUS_PARENT_OR_FACT_OVERLAP",
            shared_units,
            shared_evidence,
            shared_parents,
        )
    return _pair_result(
        left,
        right,
        "KEEP_SEPARATE_DISTINCT",
        "NO_SAFE_EXPLAINABLE_OVERLAP",
        shared_units,
        shared_evidence,
        shared_parents,
    )


def _complete_linkage_groups(
    clusters: list[Any], audits: list[ProjectionPairAudit]
) -> list[list[Any]]:
    groups: list[list[Any]] = [[cluster] for cluster in clusters]
    audit_by_pair = {
        (audit.left_cluster_id, audit.right_cluster_id): audit for audit in audits
    }
    changed = True
    while changed:
        changed = False
        for left_index in range(len(groups)):
            for right_index in range(left_index + 1, len(groups)):
                cross = [
                    audit_by_pair[tuple(sorted((
                        _text(left, "id"),
                        _text(right, "id"),
                    )))]
                    for left in groups[left_index]
                    for right in groups[right_index]
                ]
                if cross and all(audit.decision == "GROUP" for audit in cross):
                    groups[left_index].extend(groups[right_index])
                    del groups[right_index]
                    changed = True
                    break
            if changed:
                break
    return [sorted(group, key=lambda cluster: _text(cluster, "id")) for group in groups]


def _idea_for_group(
    group: list[Any],
    *,
    unit_map: Mapping[str, Any],
    evidence: Mapping[str, Any],
    unit_order: Mapping[str, int],
    synthesis: Any,
    pair_audit: list[ProjectionPairAudit],
) -> ReaderLevelIdea:
    cluster_ids = sorted(_text(cluster, "id") for cluster in group)
    unit_ids = sorted(
        {
            unit_id for cluster in group for unit_id in _sequence(cluster, "synthesis_ids")
        },
        key=lambda value: (unit_order.get(value, 10**9), value),
    )
    evidence_ids = sorted(
        {
            evidence_id for cluster in group for evidence_id in _sequence(cluster, "evidence_ids")
        }
    )
    categories = sorted(
        {category for cluster in group for category in _sequence(cluster, "categories")}
    )
    importance = (
        "CORE"
        if any(
            _text(cluster, "quality_class") == "CORE"
            or _text(cluster, "coverage_eligibility") == CoverageEligibility.REQUIRED.value
            for cluster in group
        )
        else "RELEVANT"
    )
    disputed = any(
        bool(_value(cluster, "dispute_present", False))
        or _text(cluster, "quality_class") == "DISPUTED"
        or any(_text(unit_map[unit_id], "interpretation_level") == "disputed" for unit_id in _sequence(cluster, "synthesis_ids"))
        for cluster in group
    )
    confidence = _conservative_confidence(group, unit_ids, unit_map, evidence)
    first_unit_id = min(unit_ids, key=lambda value: (unit_order.get(value, 10**9), value))
    first_unit = unit_map[first_unit_id]
    label, label_source = _source_label(first_unit, group, evidence)
    first_ordinal = min(unit_order.get(unit_id, 10**9) for unit_id in unit_ids)
    last_ordinal = max(unit_order.get(unit_id, 10**9) for unit_id in unit_ids)
    group_cluster_ids = set(cluster_ids)
    reasons = sorted(
        {
            audit.reason
            for audit in pair_audit
            if audit.decision == "GROUP"
            and audit.left_cluster_id in group_cluster_ids
            and audit.right_cluster_id in group_cluster_ids
        }
    )
    if len(group) == 1:
        grouping_reason = "UNGROUPED_DISTINCT_CLUSTER"
        if any(
            audit.decision == "KEEP_SEPARATE_AMBIGUOUS"
            for audit in pair_audit
            if audit.left_cluster_id in group_cluster_ids
            or audit.right_cluster_id in group_cluster_ids
        ):
            grouping_reason = "UNGROUPED_AMBIGUOUS_CONCEPT"
    else:
        grouping_reason = ";".join(reasons) or "GROUPED_EXPLAINABLE_OVERLAP"
    idea_id = "reader_idea_" + hashlib.sha256(
        "\n".join(cluster_ids).encode("utf-8")
    ).hexdigest()[:16]
    return ReaderLevelIdea(
        idea_id=idea_id,
        label=label,
        label_source=label_source,
        importance=importance,
        categories=categories,
        cluster_ids=cluster_ids,
        synthesis_unit_ids=unit_ids,
        evidence_ids=evidence_ids,
        ancestry_hashes={
            "evidence_hash": _text(synthesis, "evidence_hash"),
            "synthesis_hash": _text(synthesis, "synthesis_hash"),
        },
        disputed=disputed,
        status="DISPUTED" if disputed else "SUPPORTED",
        confidence=confidence,
        source_order={
            "first_unit_ordinal": first_ordinal,
            "last_unit_ordinal": last_ordinal,
            "unit_ordinals": [unit_order[unit_id] for unit_id in unit_ids],
            "cluster_ids_in_source_order": sorted(
                cluster_ids,
                key=lambda cluster_id: min(
                    unit_order.get(unit_id, 10**9)
                    for cluster in group
                    if _text(cluster, "id") == cluster_id
                    for unit_id in _sequence(cluster, "synthesis_ids")
                ),
            ),
        },
        grouping_reason=grouping_reason,
        grouping_reasons=reasons,
    )


def _source_label(
    first_unit: Any, group: list[Any], evidence: Mapping[str, Any]
) -> tuple[str, str]:
    shared_parents = set.intersection(
        *(_parent_topics(cluster, evidence) for cluster in group)
    ) if group else set()
    if len(group) > 1 and len(shared_parents) == 1:
        return next(iter(shared_parents)).replace("-", " ").title(), "normalized_evidence_parent"
    facts = _sequence(first_unit, "facts")
    if facts:
        source = " ".join(str(facts[0]).split())
        return _trim_label(source), "first_synthesis_fact"
    parents = sorted(_parent_topics(cluster, evidence) for cluster in group)
    flattened = [value for values in parents for value in values]
    if flattened:
        return flattened[0].replace("-", " ").title(), "normalized_evidence_parent"
    kind = _text(first_unit, "kind").replace("_", " ").title()
    return kind or "Reader-level idea", "synthesis_unit_kind"


def _trim_label(value: str, limit: int = 132) -> str:
    if len(value) <= limit:
        return value
    words = value[: limit + 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return words + "…"


def _conservative_confidence(
    group: list[Any],
    unit_ids: list[str],
    unit_map: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> str:
    values = [_text(cluster, "confidence") for cluster in group]
    values.extend(_text(unit_map[unit_id], "confidence") for unit_id in unit_ids)
    values.extend(_text(evidence[evidence_id], "confidence") for cluster in group for evidence_id in _sequence(cluster, "evidence_ids") if evidence_id in evidence)
    values = [value for value in values if value in _CONFIDENCE_RANK]
    return min(values, key=lambda value: _CONFIDENCE_RANK[value]) if values else "low"


def _validate_cluster_ancestry(cluster: Any, unit_map: Mapping[str, Any]) -> None:
    unit_ids = set(_sequence(cluster, "synthesis_ids"))
    if not unit_ids:
        raise ProjectionError(f"cluster {_text(cluster, 'id')} has no synthesis ancestry")
    missing = sorted(unit_ids - set(unit_map))
    if missing:
        raise ProjectionError(
            f"cluster {_text(cluster, 'id')} references unknown synthesis IDs: {missing}"
        )
    unit_evidence = {
        evidence_id
        for unit_id in unit_ids
        for evidence_id in _sequence(unit_map[unit_id], "evidence_ids")
    }
    invented = sorted(set(_sequence(cluster, "evidence_ids")) - unit_evidence)
    if invented:
        raise ProjectionError(
            f"cluster {_text(cluster, 'id')} references evidence outside unit ancestry: {invented}"
        )


def _parent_topics(cluster: Any, evidence: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    for evidence_id in _sequence(cluster, "evidence_ids"):
        item = evidence.get(evidence_id)
        metadata = _mapping(item, "relevance_metadata")
        raw = str(metadata.get("parent_object_id") or "").strip().casefold()
        if not raw:
            continue
        raw = _PARENT_PREFIX_RE.sub("", raw.replace("_", "-"))
        tokens = [token for token in raw.split("-") if token]
        tokens = [token for token in tokens if token not in _GENERIC_PARENT_TOKENS]
        if tokens:
            result.add("-".join(tokens))
    return result


def _high_fact_overlap(left: Any, right: Any, unit_map: Mapping[str, Any]) -> bool:
    left_facts = [fact for unit_id in _sequence(left, "synthesis_ids") for fact in _sequence(unit_map[unit_id], "facts")]
    right_facts = [fact for unit_id in _sequence(right, "synthesis_ids") for fact in _sequence(unit_map[unit_id], "facts")]
    for left_fact in left_facts:
        for right_fact in right_facts:
            left_text = _normalize_text(left_fact)
            right_text = _normalize_text(right_fact)
            if not left_text or not right_text:
                continue
            shared = set(left_text.split()) & set(right_text.split())
            containment = len(shared) / max(1, min(len(set(left_text.split())), len(set(right_text.split()))))
            sequence = SequenceMatcher(None, left_text, right_text).ratio()
            if sequence >= 0.78 or (containment >= 0.70 and len(shared) >= 4):
                return True
    return False


def _kind_families(cluster: Any, unit_map: Mapping[str, Any]) -> set[str]:
    return {
        _KIND_FAMILIES.get(_text(unit_map[unit_id], "kind"), _text(unit_map[unit_id], "kind"))
        for unit_id in _sequence(cluster, "synthesis_ids")
    }


def _related_unit_ids(cluster: Any, unit_map: Mapping[str, Any]) -> list[str]:
    return [
        related_id
        for unit_id in _sequence(cluster, "synthesis_ids")
        for related_id in _sequence(unit_map[unit_id], "related_unit_ids")
    ]


def _pair_result(left: Any, right: Any, decision: str, reason: str, units: list[str], evidence: list[str], parents: list[str]) -> ProjectionPairAudit:
    return ProjectionPairAudit(
        left_cluster_id=_text(left, "id"),
        right_cluster_id=_text(right, "id"),
        decision=decision,
        reason=reason,
        shared_synthesis_ids=units,
        shared_evidence_ids=evidence,
        shared_parent_topics=parents,
    )


def _normalize_text(value: Any) -> str:
    return " ".join(
        token for token in _WORD_RE.findall(str(value).casefold()) if token not in _STOPWORDS
    )


def _mapping_by_id(values: Iterable[Any] | Mapping[str, Any] | None) -> dict[str, Any]:
    if values is None:
        return {}
    if isinstance(values, Mapping):
        return {str(key): value for key, value in values.items()}
    return {_text(value, "id"): value for value in values}


def _sequence(value: Any, field: str) -> list[str]:
    raw = value.get(field) if isinstance(value, Mapping) else getattr(value, field, [])
    return [str(item) for item in (raw or [])]


def _sequence_objects(value: Any, field: str) -> list[Any]:
    raw = value.get(field) if isinstance(value, Mapping) else getattr(value, field, [])
    return list(raw or [])


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    raw = value.get(field) if isinstance(value, Mapping) else getattr(value, field, {})
    return dict(raw or {}) if isinstance(raw, Mapping) else {}


def _value(value: Any, field: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(field, default)
    return getattr(value, field, default)


def _text(value: Any, field: str) -> str:
    raw = _value(value, field, "")
    return str(raw or "")


def _sha256_json(value: Any) -> str:
    import json

    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
