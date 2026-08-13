"""Small standard-library realization helpers for CKL evidence."""

from __future__ import annotations

import re
from typing import Iterable

from .certainty import qualify_text
from .models import NarratedSentence
from .ranking import EvidenceCandidate


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text.strip())
    return [part.strip() for part in parts if part.strip()]


def realize_candidate(candidate: EvidenceCandidate) -> list[NarratedSentence]:
    """Realize authored text while copying provenance onto every sentence."""

    # Interpretive notes are already authored qualifications.  Repeating
    # their certainty/dispute metadata in front of the note makes a compact
    # caution read like a metadata dump; the metadata remains on the item.
    qualified = (
        candidate.text.strip()
        if candidate.origin == "note"
        else qualify_text(candidate.text, candidate.certainty, candidate.dispute_status)
    )
    if qualified and qualified[-1:] not in ".!?":
        qualified += "."
    parts = _split_sentences(qualified)
    if not parts:
        return []
    return [
        NarratedSentence(
            text=part,
            role=candidate.role,
            claim_ids=[candidate.claim_id] if candidate.claim_id else [],
            source_ids=list(candidate.source_ids),
            source_details=[dict(source) for source in candidate.source_details],
            scripture_references=list(candidate.scripture_references),
            parent_object_id=candidate.parent_id or None,
            parent_title=candidate.parent_title or None,
            certainty=candidate.certainty or None,
            dispute_status=candidate.dispute_status or None,
            evidence_ids=[candidate.evidence_id],
            content_status=candidate.content_status or None,
            review_status=candidate.review_status or None,
            human_review_required=candidate.human_review_required,
        )
        for part in parts
    ]


def realize_candidates(candidates: Iterable[EvidenceCandidate], *, limit: int) -> list[NarratedSentence]:
    sentences: list[NarratedSentence] = []
    seen: set[str] = set()
    for candidate in candidates:
        for sentence in realize_candidate(candidate):
            key = sentence.text.casefold()
            if key in seen:
                continue
            sentences.append(sentence)
            seen.add(key)
            if len(sentences) >= limit:
                return sentences
    return sentences
