"""Deterministic narrative recipes and compression budgets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .models import NarratedSection, NarrationLimits
from .ranking import EvidenceCandidate
from .realization import realize_candidates
from .roles import NarrativeRole, context_type_alias, section_heading


@dataclass(frozen=True)
class PlannedSection:
    section_type: str
    heading: str
    candidates: tuple[EvidenceCandidate, ...]
    limit: int


def _recipe_roles(context_type: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return primary and caution roles for a context recipe."""

    if context_type == "historical_context":
        return (
            (NarrativeRole.SETTING, NarrativeRole.BACKGROUND, NarrativeRole.OBSERVATION, NarrativeRole.COVENANT_CONTEXT),
            (NarrativeRole.INTERPRETIVE_CAUTION, NarrativeRole.DISPUTED_VIEW),
        )
    if context_type == "cultural_context":
        return (
            (NarrativeRole.CULTURAL_PRACTICE, NarrativeRole.OBSERVATION, NarrativeRole.BACKGROUND, NarrativeRole.COVENANT_CONTEXT),
            (NarrativeRole.INTERPRETIVE_CAUTION, NarrativeRole.DISPUTED_VIEW),
        )
    if context_type == "literary_context":
        return (
            (NarrativeRole.LITERARY_FUNCTION, NarrativeRole.OBSERVATION, NarrativeRole.BACKGROUND),
            (NarrativeRole.INTERPRETIVE_CAUTION, NarrativeRole.DISPUTED_VIEW),
        )
    if context_type == "archaeology":
        return (
            (NarrativeRole.ARCHAEOLOGICAL_SUPPORT, NarrativeRole.OBSERVATION, NarrativeRole.BACKGROUND),
            (NarrativeRole.INTERPRETIVE_CAUTION, NarrativeRole.DISPUTED_VIEW),
        )
    if context_type == "canonical_context":
        return (
            (NarrativeRole.CANONICAL_CONNECTION, NarrativeRole.COVENANT_CONTEXT, NarrativeRole.OBSERVATION, NarrativeRole.BACKGROUND),
            (NarrativeRole.INTERPRETIVE_CAUTION, NarrativeRole.DISPUTED_VIEW),
        )
    if context_type == "covenant_context":
        return (
            (NarrativeRole.COVENANT_CONTEXT, NarrativeRole.CANONICAL_CONNECTION, NarrativeRole.OBSERVATION),
            (NarrativeRole.INTERPRETIVE_CAUTION, NarrativeRole.DISPUTED_VIEW),
        )
    return (
        (
            NarrativeRole.SETTING,
            NarrativeRole.CULTURAL_PRACTICE,
            NarrativeRole.LITERARY_FUNCTION,
            NarrativeRole.ARCHAEOLOGICAL_SUPPORT,
            NarrativeRole.CANONICAL_CONNECTION,
            NarrativeRole.COVENANT_CONTEXT,
            NarrativeRole.OBSERVATION,
            NarrativeRole.BACKGROUND,
        ),
        (NarrativeRole.INTERPRETIVE_CAUTION, NarrativeRole.DISPUTED_VIEW),
    )


def plan_sections(
    candidates: Sequence[EvidenceCandidate],
    *,
    context_type: str = "",
    limits: NarrationLimits | None = None,
) -> list[PlannedSection]:
    limits = limits or NarrationLimits()
    normalized_type = context_type_alias(context_type)
    primary_roles, caution_roles = _recipe_roles(normalized_type)
    selected = candidates

    if normalized_type:
        allowed = set(primary_roles) | set(caution_roles)
        selected = [candidate for candidate in candidates if candidate.role in allowed]

    sections: list[PlannedSection] = []
    primary_candidates = [candidate for candidate in selected if candidate.role in primary_roles]
    role_priority = {role: index for index, role in enumerate(primary_roles)}
    primary_candidates.sort(key=lambda candidate: (role_priority.get(candidate.role, len(primary_roles)), -candidate.score, candidate.evidence_id))
    if primary_candidates:
        # A single compact primary section is intentional: the recipe controls
        # the order through ranking rather than dumping one section per field.
        primary_role = next((role for role in primary_roles if any(item.role == role for item in primary_candidates)), primary_roles[0])
        section_type, heading = section_heading(normalized_type, primary_role)
        sections.append(
            PlannedSection(
                section_type=section_type,
                heading=heading,
                candidates=tuple(primary_candidates),
                limit=limits.max_archaeology_items if normalized_type == "archaeology" else limits.max_primary_facts,
            )
        )

    caution_candidates = [candidate for candidate in selected if candidate.role in caution_roles]
    if normalized_type == "archaeology":
        archaeology_terms = ("archaeolog", "artifact", "material", "battle", "settlement", "chronolog", "correlation", "site")
        caution_candidates = [
            candidate
            for candidate in caution_candidates
            if any(term in candidate.text.casefold() for term in archaeology_terms)
        ]
    if caution_candidates:
        section_type, heading = section_heading(normalized_type, NarrativeRole.INTERPRETIVE_CAUTION)
        sections.append(
            PlannedSection(
                section_type=section_type,
                heading=heading,
                candidates=tuple(caution_candidates),
                limit=limits.max_cautions,
            )
        )
    return sections


def realize_plan(plan: Sequence[PlannedSection]) -> list[NarratedSection]:
    sections: list[NarratedSection] = []
    for planned in plan:
        sentences = realize_candidates(planned.candidates, limit=max(0, planned.limit))
        if sentences:
            sections.append(NarratedSection(planned.section_type, planned.heading, sentences))
    return sections
