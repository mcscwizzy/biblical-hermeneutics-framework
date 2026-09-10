"""Deterministic commentary eligibility at the EvidenceBundle boundary.

Retrieval answers whether a parent or child record overlaps a requested
reference.  This module answers the narrower question used by commentary:
whether the evidence claim itself is allowed to be passage-specific.  It does
not inspect claim prose and does not infer semantic relevance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from bhf_agent.presentation.references import anchor_specificity, references_overlap


COMMENTARY_EVIDENCE_APPLICABILITY_VERSION = "commentary-evidence-applicability-v1"

_STRUCTURED_CHILD_SOURCE_KINDS = frozenset(
    {"ckl_evidence_item", "ckl_claim", "ckl_interpretive_note"}
)
_RESOLVER_SOURCE_KINDS = frozenset(
    {"archaeology_resolver", "passage_map_place", "passage_map_route"}
)
_CURRENT_SCOPES = frozenset({"passage", "section"})
_BROAD_SCOPES = frozenset(
    {"global", "testament", "book", "entity", "lexical"}
)
_SPECIFICITY_RANK = {"unknown": 0, "book": 1, "multi_chapter": 2, "chapter": 3, "verse": 4}


@dataclass(frozen=True)
class EvidenceApplicability:
    """Auditable policy result for one EvidenceBundle item."""

    policy_version: str
    status: str
    current_chapter_eligible: bool
    availability_specific: bool
    applicability_scope: str
    raw_anchor_specificity: str
    anchor_source: str
    inherited_from_parent: bool | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_evidence_applicability(
    item: Any,
    passage_ref: str,
) -> EvidenceApplicability:
    """Apply the versioned, fail-closed commentary applicability policy.

    Structured children with their own overlapping passage/section anchors and
    explicit child provenance remain eligible.  Legacy parent inheritance and
    broad authored scopes may remain retrievable/background evidence, but they
    cannot supply current-chapter commentary ancestry or specificity.
    """

    metadata = dict(getattr(item, "relevance_metadata", {}) or {})
    anchors = [str(value) for value in (getattr(item, "passage_anchors", ()) or ())]
    scope = _metadata_text(metadata, "applicability_scope")
    source_kind = _metadata_text(metadata, "source_kind")
    anchor_source = _metadata_text(metadata, "anchor_source")
    inherited = metadata.get("inherited_from_parent")
    raw_specificity = _raw_anchor_specificity(metadata, anchors)
    computed_specificity = _computed_anchor_specificity(anchors)

    def result(status: str, eligible: bool, specific: bool, reason: str) -> EvidenceApplicability:
        return EvidenceApplicability(
            policy_version=COMMENTARY_EVIDENCE_APPLICABILITY_VERSION,
            status=status,
            current_chapter_eligible=eligible,
            availability_specific=specific,
            applicability_scope=scope or "unknown",
            raw_anchor_specificity=raw_specificity,
            anchor_source=anchor_source or "unknown",
            inherited_from_parent=inherited if isinstance(inherited, bool) else None,
            reason=reason,
        )

    if not scope:
        return result("rejected", False, False, "missing_applicability_scope")
    if scope not in _CURRENT_SCOPES | _BROAD_SCOPES:
        return result("rejected", False, False, "unknown_applicability_scope")
    declared_specificity = _metadata_text(metadata, "anchor_specificity")
    if declared_specificity and declared_specificity != computed_specificity:
        return result("rejected", False, False, "contradictory_anchor_specificity")
    if inherited is not None and not isinstance(inherited, bool):
        return result("rejected", False, False, "contradictory_inherited_flag")
    if inherited is True and anchor_source != "parent":
        return result("rejected", False, False, "inherited_flag_requires_parent_anchor")
    if inherited is False and anchor_source == "parent":
        return result("rejected", False, False, "parent_anchor_marked_not_inherited")
    if anchor_source not in {"child", "parent", "resolver"}:
        return result("rejected", False, False, "missing_or_ambiguous_anchor_source")
    if not anchors:
        return result("rejected", False, False, "missing_authored_anchor")
    if not _overlaps(passage_ref, anchors):
        return result("rejected", False, False, "no_overlapping_authored_anchor")

    if source_kind == "ckl_legacy_field":
        if anchor_source != "parent" or inherited is not True:
            return result("rejected", False, False, "legacy_provenance_is_contradictory")
        if scope in _CURRENT_SCOPES:
            return result("rejected", False, False, "legacy_parent_anchor_cannot_promote_scope")
        return result("background", False, False, "legacy_parent_inheritance_is_background_only")

    if source_kind in _STRUCTURED_CHILD_SOURCE_KINDS:
        if anchor_source != "child" or inherited is True:
            return result("rejected", False, False, "structured_child_provenance_is_contradictory")
        if scope in _CURRENT_SCOPES:
            return result("eligible", True, True, "authored_child_anchor_supports_current_chapter")
        return result("background", False, False, "authored_child_scope_is_broad_context")

    if source_kind in _RESOLVER_SOURCE_KINDS:
        if anchor_source != "resolver" or inherited is True:
            return result("rejected", False, False, "resolver_provenance_is_contradictory")
        if scope in _CURRENT_SCOPES:
            return result("eligible", True, True, "resolver_owned_overlapping_anchor")
        return result("background", False, False, "resolver_scope_is_broad_context")

    return result("rejected", False, False, "unknown_evidence_provenance")


def commentary_eligible_evidence(
    items: Iterable[Any], passage_ref: str
) -> tuple[Any, ...]:
    """Return only evidence legal for current-chapter synthesis."""

    return tuple(
        item
        for item in items
        if evaluate_evidence_applicability(item, passage_ref).current_chapter_eligible
    )


def applicability_diagnostic(item: Any, passage_ref: str) -> dict[str, Any]:
    """Serialize the policy decision without changing the source item."""

    return evaluate_evidence_applicability(item, passage_ref).to_dict()


def _metadata_text(metadata: Mapping[str, Any], key: str) -> str:
    return str(metadata.get(key) or "").strip().casefold()


def _raw_anchor_specificity(metadata: Mapping[str, Any], anchors: list[str]) -> str:
    declared = _metadata_text(metadata, "anchor_specificity")
    if declared:
        return declared
    return _computed_anchor_specificity(anchors)


def _computed_anchor_specificity(anchors: Iterable[str]) -> str:
    best = "unknown"
    for anchor in anchors:
        value = anchor_specificity(anchor)
        if _SPECIFICITY_RANK.get(value, 0) > _SPECIFICITY_RANK.get(best, 0):
            best = value
    return best


def _overlaps(passage_ref: str, anchors: Iterable[str]) -> bool:
    return any(
        references_overlap(passage_ref, anchor)
        for anchor in anchors
    )
