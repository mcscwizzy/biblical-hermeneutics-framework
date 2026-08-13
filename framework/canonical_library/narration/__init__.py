"""Offline deterministic presentation of already-selected CKL evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Sequence

from .certainty import CERTAINTY_LANGUAGE, DISPUTE_LANGUAGE, certainty_phrase, dispute_phrase
from .models import NarratedSection, NarratedSentence, NarrationLimits, NarrationResult
from .planner import plan_sections, realize_plan
from .ranking import EvidenceCandidate, collect_evidence, rank_evidence
from .roles import NarrativeRole, context_type_alias, role_for


_RECIPE_TITLES = {
    "historical_context": "Historical Context",
    "cultural_context": "Cultural Context",
    "literary_context": "Literary Context",
    "archaeology": "Archaeological Context",
    "canonical_context": "Canonical Context",
    "covenant_context": "Covenant Context",
}


class CanonicalNarrator:
    """Turn selected CKL evidence into compact, provenance-bearing prose.

    The narrator accepts an object/list of already retrieved records.  It does
    not call a repository, perform broad retrieval, use an LLM, or write CKL
    data.  The same input produces the same output.
    """

    def __init__(self, *, limits: NarrationLimits | None = None) -> None:
        self.limits = limits or NarrationLimits()

    def narrate(
        self,
        context: Any,
        reference: str = "",
        context_type: str = "",
        title: str = "",
    ) -> NarrationResult:
        normalized_type = context_type_alias(context_type)
        candidates = collect_evidence(context, reference=reference)
        ranked = rank_evidence(candidates, reference=reference)
        plan = plan_sections(ranked, context_type=normalized_type, limits=self.limits)
        sections = realize_plan(plan)

        lead = None
        if sections and self.limits.max_lead_sentences:
            first = sections[0]
            if first.sentences:
                lead = first.sentences[0]
                remaining: list[NarratedSection] = []
                lead_removed = False
                for section in sections:
                    sentences = []
                    for sentence in section.sentences:
                        if not lead_removed and sentence == lead:
                            lead_removed = True
                            continue
                        sentences.append(sentence)
                    if sentences:
                        remaining.append(NarratedSection(section.section_type, section.heading, sentences))
                sections = remaining

        selected_ids = {
            evidence_id
            for section in sections
            for sentence in section.sentences
            for evidence_id in sentence.evidence_ids
        }
        if lead:
            selected_ids.update(lead.evidence_ids)
        source_ids = {
            source_id
            for sentence in ([lead] if lead else []) + [sentence for section in sections for sentence in section.sentences]
            for source_id in sentence.source_ids
        }
        entities, cross_references, statuses, reviews = _metadata(ranked, self.limits)
        return NarrationResult(
            reference=str(reference or ""),
            title=title.strip() or _RECIPE_TITLES.get(normalized_type, "Context"),
            lead=lead,
            sections=sections,
            evidence_count=len(ranked),
            additional_evidence_count=max(0, len(ranked) - len(selected_ids)),
            source_count=len(source_ids),
            entities=entities,
            cross_references=cross_references,
            content_statuses=statuses,
            review_statuses=reviews,
        )

    __call__ = narrate


ContextNarrator = CanonicalNarrator


def narrate_context(
    context: Any,
    *,
    reference: str = "",
    context_type: str = "",
    title: str = "",
    limits: NarrationLimits | None = None,
) -> dict[str, Any]:
    """Convenience API for callers that need JSON-ready narration."""

    return CanonicalNarrator(limits=limits).narrate(
        context,
        reference=reference,
        context_type=context_type,
        title=title,
    ).to_dict()


def _metadata(candidates: Sequence[EvidenceCandidate], limits: NarrationLimits) -> tuple[list[str], list[str], list[str], list[str]]:
    entities: list[str] = []
    references: list[str] = []
    statuses: list[str] = []
    reviews: list[str] = []
    for candidate in candidates:
        for value in [*candidate.entities, candidate.parent_title]:
            if value and value not in entities and len(entities) < limits.max_entities:
                entities.append(value)
        for value in [*candidate.cross_references, *candidate.scripture_references]:
            if value and value not in references and len(references) < limits.max_cross_references:
                references.append(value)
        if candidate.content_status and candidate.content_status not in statuses:
            statuses.append(candidate.content_status)
        if candidate.review_status and candidate.review_status not in reviews:
            reviews.append(candidate.review_status)
    return entities, references, statuses, reviews


__all__ = [
    "CERTAINTY_LANGUAGE",
    "DISPUTE_LANGUAGE",
    "CanonicalNarrator",
    "ContextNarrator",
    "EvidenceCandidate",
    "NarratedSection",
    "NarratedSentence",
    "NarrationLimits",
    "NarrationResult",
    "NarrativeRole",
    "certainty_phrase",
    "collect_evidence",
    "context_type_alias",
    "dispute_phrase",
    "narrate_context",
    "plan_sections",
    "rank_evidence",
    "realize_plan",
    "role_for",
]
