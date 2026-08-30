"""Serializable result contracts for presentation evaluations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PresentationEvalCheck:
    id: str
    passed: bool
    observed: Any
    expected: Any


@dataclass(frozen=True)
class PresentationEvalCaseResult:
    passage_ref: str
    passed: bool
    evidence_hash: str
    evidence_count: int
    ranked_count: int
    card_count: int
    presentation_mode: str
    checks: list[PresentationEvalCheck]
    ranked_evidence: list[dict[str, Any]] = field(default_factory=list)
    cards: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PresentationEvalSuiteResult:
    fixture_path: str
    passed: bool
    passed_count: int
    failed_count: int
    cases: list[PresentationEvalCaseResult]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
