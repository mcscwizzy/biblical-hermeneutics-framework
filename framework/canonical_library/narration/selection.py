"""Deterministic lead, novelty, and role-diversity selection."""

from __future__ import annotations

import re
from typing import Sequence

from .ranking import EvidenceCandidate
from .roles import NarrativeRole, context_type_alias
from .scripture import PassageScope


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "has", "have", "in", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "was", "were", "which", "with",
}


def normalized_tokens(text: object) -> frozenset[str]:
    return frozenset(
        token
        for token in re.findall(r"[a-z0-9]+", str(text or "").casefold())
        if len(token) > 2 and token not in _STOP_WORDS
    )


def token_similarity(left: object, right: object) -> float:
    left_tokens = normalized_tokens(left)
    right_tokens = normalized_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def candidates_are_redundant(left: EvidenceCandidate, right: EvidenceCandidate) -> bool:
    """Use conservative provenance and lexical signals for near-duplicates."""

    if left.claim_id and left.claim_id == right.claim_id:
        return True
    same_parent_role = bool(
        left.parent_id
        and left.parent_id == right.parent_id
        and left.role == right.role
    )
    same_anchors = bool(
        left.scripture_references
        and set(left.scripture_references) == set(right.scripture_references)
    )
    similarity = token_similarity(left.text, right.text)
    if similarity >= 0.78:
        return True
    return same_parent_role and same_anchors and similarity >= 0.62


def _base_value(candidate: EvidenceCandidate) -> float:
    value = (int(PassageScope.UNRELATED) - min(candidate.scope, int(PassageScope.UNRELATED))) * 10.0
    value += candidate.score
    value += 2.0 if candidate.origin == "claim" else 1.0 if candidate.origin == "note" else 0.0
    value += 1.0 if candidate.review_status in {"approved", "reviewed"} else 0.0
    return value


def select_diverse(
    candidates: Sequence[EvidenceCandidate],
    *,
    limit: int,
    role_preferences: Sequence[str] = (),
) -> list[EvidenceCandidate]:
    """Greedily select relevant facts while rewarding complementary roles."""

    remaining = list(candidates)
    selected: list[EvidenceCandidate] = []
    role_bonus = {
        role: (len(role_preferences) - index) * 0.5
        for index, role in enumerate(role_preferences)
    }
    while remaining and len(selected) < max(0, limit):
        eligible = [
            candidate
            for candidate in remaining
            if not any(candidates_are_redundant(candidate, prior) for prior in selected)
        ]
        if not eligible:
            break
        used_roles = {candidate.role for candidate in selected}
        best = max(
            eligible,
            key=lambda candidate: (
                _base_value(candidate)
                + role_bonus.get(candidate.role, 0.0)
                + (1.25 if candidate.role not in used_roles else 0.0),
                -len(candidate.text),
                candidate.evidence_id,
            ),
        )
        selected.append(best)
        remaining.remove(best)
    return selected


def lead_score(candidate: EvidenceCandidate, *, context_type: str = "") -> tuple[float, ...]:
    """Score how well one fact answers the passage reader's first question."""

    normalized_type = context_type_alias(context_type)
    preferred_roles = {
        "historical_context": {NarrativeRole.SETTING, NarrativeRole.OBSERVATION, NarrativeRole.BACKGROUND},
        "cultural_context": {NarrativeRole.CULTURAL_PRACTICE, NarrativeRole.OBSERVATION},
        "literary_context": {NarrativeRole.LITERARY_FUNCTION, NarrativeRole.OBSERVATION},
        "archaeology": {NarrativeRole.ARCHAEOLOGICAL_SUPPORT, NarrativeRole.OBSERVATION},
        "canonical_context": {NarrativeRole.CANONICAL_CONNECTION, NarrativeRole.COVENANT_CONTEXT},
        "covenant_context": {NarrativeRole.COVENANT_CONTEXT, NarrativeRole.CANONICAL_CONNECTION},
    }.get(normalized_type, set())
    certainty = re.sub(r"[^a-z0-9]+", "_", candidate.certainty.casefold()).strip("_")
    certainty_value = {
        "textually_explicit": 3.0,
        "strong_consensus": 2.5,
        "high": 2.5,
        "probable": 1.5,
        "medium": 1.0,
        "plausible": 0.5,
        "disputed": 0.0,
        "speculative": -1.0,
        "insufficient_evidence": -2.0,
        "low": -1.0,
    }.get(certainty, 0.5)
    clarity = 1.0 if 35 <= len(candidate.text) <= 260 else 0.0
    return (
        float(int(PassageScope.UNRELATED) - min(candidate.scope, int(PassageScope.UNRELATED))),
        1.0 if candidate.origin == "claim" else 0.5 if candidate.origin == "note" else 0.0,
        1.0 if candidate.review_status in {"approved", "reviewed"} else 0.0,
        certainty_value,
        1.0 if candidate.role in preferred_roles else 0.0,
        candidate.score,
        clarity,
        -float(len(candidate.text)),
    )


def select_lead(
    candidates: Sequence[EvidenceCandidate],
    *,
    context_type: str = "",
) -> EvidenceCandidate | None:
    eligible = [candidate for candidate in candidates if not candidate.is_caution]
    if not eligible:
        return None
    # Negating the stable identifier makes max() deterministic without relying
    # on caller order; sorting keeps the final tie-break straightforward.
    return sorted(
        eligible,
        key=lambda candidate: (
            tuple(-value for value in lead_score(candidate, context_type=context_type)),
            candidate.evidence_id,
        ),
    )[0]
