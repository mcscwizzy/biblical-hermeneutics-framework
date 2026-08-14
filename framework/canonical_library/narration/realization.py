"""Small standard-library realization helpers for CKL evidence."""

from __future__ import annotations

import re
from typing import Iterable

from .certainty import qualification_key, qualify_text
from .discourse import NarrativeUnit
from .models import NarratedSentence
from .provenance import merge_unique
from .ranking import EvidenceCandidate


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text.strip())
    return [part.strip() for part in parts if part.strip()]


def _source_details(unit: NarrativeUnit) -> list[dict]:
    details: list[dict] = []
    seen: set[str] = set()
    for candidate in unit.candidates:
        for source in candidate.source_details:
            key = str(source.get("id") or source.get("source_id") or source.get("title") or source).casefold()
            if key not in seen:
                details.append(dict(source))
                seen.add(key)
    return details


def realize_unit(
    unit: NarrativeUnit,
    *,
    include_dispute: bool = True,
) -> list[NarratedSentence]:
    """Realize authored text while copying provenance onto every sentence."""

    candidate = unit.representative
    # Interpretive notes are already authored qualifications.  Repeating
    # their certainty/dispute metadata in front of the note makes a compact
    # caution read like a metadata dump; the metadata remains on the item.
    qualified = (
        candidate.text.strip()
        if candidate.origin == "note"
        else qualify_text(
            candidate.text,
            candidate.certainty,
            candidate.dispute_status,
            include_dispute=include_dispute,
            rationale=candidate.rationale,
        )
    )
    if qualified and qualified[-1:] not in ".!?":
        qualified += "."
    parts = _split_sentences(qualified)
    if not parts:
        return []
    claim_ids: list[str] = []
    source_ids: list[str] = []
    scripture_references: list[str] = []
    evidence_ids: list[str] = []
    certainties: list[str] = []
    dispute_statuses: list[str] = []
    parent_records: list[dict[str, str | None]] = []
    seen_parents: set[tuple[str, str]] = set()
    for evidence in unit.candidates:
        claim_ids = merge_unique(claim_ids, [evidence.claim_id] if evidence.claim_id else [])
        source_ids = merge_unique(source_ids, evidence.source_ids)
        scripture_references = merge_unique(scripture_references, evidence.scripture_references)
        evidence_ids = merge_unique(evidence_ids, [evidence.evidence_id])
        certainties = merge_unique(certainties, [evidence.certainty] if evidence.certainty else [])
        dispute_statuses = merge_unique(
            dispute_statuses,
            [evidence.dispute_status] if evidence.dispute_status else [],
        )
        parent_key = (evidence.parent_id, evidence.parent_title)
        if any(parent_key) and parent_key not in seen_parents:
            parent_records.append({
                "id": evidence.parent_id or None,
                "title": evidence.parent_title or None,
            })
            seen_parents.add(parent_key)
    return [
        NarratedSentence(
            text=part,
            role=candidate.role,
            claim_ids=claim_ids,
            source_ids=source_ids,
            source_details=_source_details(unit),
            scripture_references=scripture_references,
            parent_object_id=candidate.parent_id or None,
            parent_title=candidate.parent_title or None,
            parent_records=parent_records,
            certainty=candidate.certainty or None,
            dispute_status=candidate.dispute_status or None,
            certainties=certainties,
            dispute_statuses=dispute_statuses,
            evidence_ids=evidence_ids,
            content_status=candidate.content_status or None,
            review_status=candidate.review_status or None,
            human_review_required=candidate.human_review_required,
        )
        for part in parts
    ]


def realize_candidate(candidate: EvidenceCandidate) -> list[NarratedSentence]:
    return realize_unit(NarrativeUnit((candidate,)))


def realize_candidates(
    candidates: Iterable[EvidenceCandidate | NarrativeUnit],
    *,
    limit: int,
    max_visible_qualifications: int = 1,
) -> list[NarratedSentence]:
    sentences: list[NarratedSentence] = []
    seen: set[str] = set()
    qualification_counts: dict[str, int] = {}
    qualification_budget = max(1, max_visible_qualifications)
    for item in candidates:
        unit = item if isinstance(item, NarrativeUnit) else NarrativeUnit((item,))
        candidate = unit.representative
        issue = qualification_key(candidate.certainty, candidate.dispute_status)
        include_dispute = not issue or qualification_counts.get(issue, 0) < qualification_budget
        if issue and include_dispute:
            # Each materially different issue gets its own budget, so distinct
            # disputes remain visible while repeated boilerplate is bounded.
            qualification_counts[issue] = qualification_counts.get(issue, 0) + 1
        for sentence in realize_unit(unit, include_dispute=include_dispute):
            key = sentence.text.casefold()
            if key in seen:
                continue
            sentences.append(sentence)
            seen.add(key)
            if len(sentences) >= limit:
                return sentences
    return sentences
