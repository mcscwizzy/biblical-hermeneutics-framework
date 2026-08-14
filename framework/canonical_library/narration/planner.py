"""Deterministic narrative recipes and compression budgets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .discourse import aggregate_candidates, select_narrative_units
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
    qualification_budget: int = 1
    role_preferences: tuple[str, ...] = ()


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
    primary_limit = limits.max_archaeology_items if normalized_type == "archaeology" else limits.max_primary_facts
    if primary_candidates:
        # A single compact primary section is intentional; discourse selection
        # orders the evidence rather than dumping one section per source field.
        primary_role = primary_candidates[0].role
        section_type, heading = section_heading(normalized_type, primary_role)
        sections.append(
            PlannedSection(
                section_type=section_type,
                heading=heading,
                candidates=tuple(primary_candidates),
                limit=primary_limit,
                qualification_budget=limits.max_visible_qualifications_per_section,
                role_preferences=primary_roles,
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
    if caution_candidates and sections:
        section_type, heading = section_heading(normalized_type, NarrativeRole.INTERPRETIVE_CAUTION)
        sections.append(
            PlannedSection(
                section_type=section_type,
                heading=heading,
                candidates=tuple(caution_candidates),
                limit=limits.max_cautions,
                qualification_budget=limits.max_visible_qualifications_per_section,
                role_preferences=caution_roles,
            )
        )
    return sections


def realize_plan(plan: Sequence[PlannedSection]) -> list[NarratedSection]:
    sections: list[NarratedSection] = []
    for planned in plan:
        units = aggregate_candidates(planned.candidates)
        units = select_narrative_units(
            units,
            limit=planned.limit,
            role_preferences=planned.role_preferences,
        )
        sentences = realize_candidates(
            units,
            limit=max(0, planned.limit),
            max_visible_qualifications=planned.qualification_budget,
        )
        if sentences:
            sections.append(NarratedSection(planned.section_type, planned.heading, sentences))
    return sections
