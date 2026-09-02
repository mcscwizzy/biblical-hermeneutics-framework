"""Fixture loading and reporting for local presentation evaluations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .evaluation import evaluate_presentation_case
from .evaluation_expectations import validate_presentation_expectations
from .evaluation_models import PresentationEvalSuiteResult


def load_presentation_fixtures(path: str | Path) -> list[dict[str, Any]]:
    """Load the existing list format or a suite object containing ``cases``."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(value, Mapping):
        value = value.get("cases")
    if not isinstance(value, list):
        raise ValueError("presentation fixture must be a list or an object with cases")
    fixtures: list[dict[str, Any]] = []
    for index, case in enumerate(value):
        if not isinstance(case, Mapping):
            raise ValueError(f"presentation fixture case {index + 1} must be an object")
        reference = str(case.get("reference") or "").strip()
        objects = case.get("objects", [])
        if not reference:
            raise ValueError(f"presentation fixture case {index + 1} requires reference")
        if not isinstance(objects, list):
            raise ValueError(f"presentation fixture case {reference} objects must be a list")
        validate_presentation_expectations(
            case.get("presentation_expectations"),
            reference=reference,
        )
        fixtures.append(dict(case))
    return fixtures


def evaluate_presentation_fixtures(
    path: str | Path,
    *,
    references: Sequence[str] = (),
    candidate_limit: int = 8,
    maximum_cards: int = 3,
) -> PresentationEvalSuiteResult:
    fixtures = load_presentation_fixtures(path)
    selected = {_reference_key(value) for value in references if value.strip()}
    if selected:
        fixtures = [value for value in fixtures if _reference_key(value["reference"]) in selected]
        found = {_reference_key(value["reference"]) for value in fixtures}
        missing = sorted(selected - found)
        if missing:
            raise ValueError(f"presentation fixture reference not found: {', '.join(missing)}")
    cases = [
        evaluate_presentation_case(
            fixture,
            candidate_limit=candidate_limit,
            maximum_cards=maximum_cards,
        )
        for fixture in fixtures
    ]
    passed_count = sum(case.passed for case in cases)
    return PresentationEvalSuiteResult(
        fixture_path=str(Path(path)),
        passed=bool(cases) and passed_count == len(cases),
        passed_count=passed_count,
        failed_count=len(cases) - passed_count,
        cases=cases,
    )


def format_presentation_eval(result: PresentationEvalSuiteResult) -> str:
    lines = [
        f"Presentation evaluation: {'PASS' if result.passed else 'FAIL'}",
        f"Cases: {result.passed_count}/{len(result.cases)} passed",
    ]
    for case in result.cases:
        lines.extend(
            [
                "",
                f"{case.passage_ref}: {'PASS' if case.passed else 'FAIL'}",
                (
                    f"  Evidence {case.evidence_count} | ranked {case.ranked_count} | "
                    f"cards {case.card_count} | mode {case.presentation_mode}"
                ),
            ]
        )
        for check in case.checks:
            lines.append(f"  {'PASS' if check.passed else 'FAIL'} {check.id}")
        if case.ranked_evidence:
            ranked = ", ".join(
                f"{value['id']} ({value['score']:.4f})" for value in case.ranked_evidence
            )
            lines.append(f"  Ranked: {ranked}")
        if case.cards:
            cards = ", ".join(f"{value['type']}:{value['id']}" for value in case.cards)
            lines.append(f"  Cards: {cards}")
    return "\n".join(lines)


def _reference_key(value: Any) -> str:
    return " ".join(str(value).split()).casefold()
