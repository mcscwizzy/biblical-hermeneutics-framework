"""Conservative aggregation between evidence planning and realization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .ranking import EvidenceCandidate
from .selection import candidates_are_redundant, select_diverse, token_similarity


@dataclass(frozen=True)
class NarrativeUnit:
    """One proposition backed by one or more compatible CKL facts."""

    candidates: tuple[EvidenceCandidate, ...]

    @property
    def representative(self) -> EvidenceCandidate:
        return self.candidates[0]


def _same_qualification_issue(left: EvidenceCandidate, right: EvidenceCandidate) -> bool:
    return bool(
        left.is_caution
        and right.is_caution
        and left.parent_id
        and left.parent_id == right.parent_id
        and left.dispute_status
        and left.dispute_status == right.dispute_status
        and token_similarity(left.text, right.text) >= 0.45
    )


def aggregate_candidates(candidates: Sequence[EvidenceCandidate]) -> list[NarrativeUnit]:
    """Merge only facts whose relationship is explicit or strongly redundant.

    The strongest candidate remains the surface proposition.  Every supporting
    candidate remains attached to the unit so its provenance is retained.
    """

    units: list[NarrativeUnit] = []
    for candidate in candidates:
        match_index = next(
            (
                index
                for index, unit in enumerate(units)
                if candidates_are_redundant(unit.representative, candidate)
                or _same_qualification_issue(unit.representative, candidate)
            ),
            None,
        )
        if match_index is None:
            units.append(NarrativeUnit((candidate,)))
            continue
        existing = units[match_index]
        units[match_index] = NarrativeUnit((*existing.candidates, candidate))
    return units


def select_narrative_units(
    units: Sequence[NarrativeUnit],
    *,
    limit: int,
    role_preferences: Sequence[str] = (),
) -> list[NarrativeUnit]:
    selected = select_diverse(
        [unit.representative for unit in units],
        limit=limit,
        role_preferences=role_preferences,
    )
    selected_ids = {id(candidate): index for index, candidate in enumerate(selected)}
    return sorted(
        (unit for unit in units if id(unit.representative) in selected_ids),
        key=lambda unit: selected_ids[id(unit.representative)],
    )
