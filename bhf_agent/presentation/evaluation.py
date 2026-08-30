"""Local, deterministic evaluation for contextual presentation fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .engine import PresentationEngine
from .evidence import build_evidence_bundle
from .evaluation_expectations import validate_presentation_expectations
from .evaluation_models import PresentationEvalCaseResult, PresentationEvalCheck
from .ranking import rank_evidence
from .validation import validate_presentation_packet


@dataclass(frozen=True)
class _CanonicalResult:
    object: Mapping[str, Any]
    score: float


def evaluate_presentation_case(
    fixture: Mapping[str, Any],
    *,
    candidate_limit: int = 8,
    maximum_cards: int = 3,
) -> PresentationEvalCaseResult:
    """Build, rank, render, validate, and inspect one provider-free fixture."""

    reference = str(fixture.get("reference") or "").strip()
    if not reference:
        raise ValueError("presentation fixture requires reference")
    if candidate_limit < 1:
        raise ValueError("candidate_limit must be at least 1")
    if maximum_cards < 0:
        raise ValueError("maximum_cards cannot be negative")
    expectations = validate_presentation_expectations(
        fixture.get("presentation_expectations"),
        reference=reference,
    )
    raw_objects = fixture.get("objects", [])
    if not isinstance(raw_objects, Sequence) or isinstance(raw_objects, (str, bytes)):
        raise ValueError(f"presentation fixture case {reference} objects must be a list")
    score = _number(fixture.get("retrieval_score"), 0.92)
    canonical_results = [
        _CanonicalResult(object=dict(value), score=score)
        for value in raw_objects
        if isinstance(value, Mapping)
    ]
    geography = _mapping(fixture.get("geography"))
    archaeology = fixture.get("archaeology", [])
    if not isinstance(archaeology, Sequence) or isinstance(archaeology, (str, bytes)):
        raise ValueError(f"presentation fixture case {reference} archaeology must be a list")

    bundle = build_evidence_bundle(
        reference,
        canonical_results=canonical_results,
        geography=geography,
        archaeology=[dict(value) for value in archaeology if isinstance(value, Mapping)],
    )
    rebuilt = build_evidence_bundle(
        reference,
        canonical_results=canonical_results,
        geography=geography,
        archaeology=[dict(value) for value in archaeology if isinstance(value, Mapping)],
    )
    ranked = rank_evidence(bundle, limit=candidate_limit)
    result = PresentationEngine(
        maximum_cards=maximum_cards,
        candidate_limit=candidate_limit,
    ).present(bundle)
    validation = validate_presentation_packet(
        result.packet.to_dict(),
        bundle,
        maximum_cards=maximum_cards,
    )

    checks = _core_checks(
        bundle=bundle,
        rebuilt=rebuilt,
        ranked=ranked,
        packet=result.packet,
        validation=validation,
        candidate_limit=candidate_limit,
        maximum_cards=maximum_cards,
    )
    checks.extend(
        _expectation_checks(
            fixture=fixture,
            expectations=expectations,
            bundle=bundle,
            ranked=ranked,
            packet=result.packet,
            presentation_mode=result.mode,
        )
    )
    return PresentationEvalCaseResult(
        passage_ref=reference,
        passed=all(check.passed for check in checks),
        evidence_hash=bundle.evidence_hash,
        evidence_count=len(bundle.evidence_items),
        ranked_count=len(ranked),
        card_count=len(result.packet.cards),
        presentation_mode=result.mode,
        checks=checks,
        ranked_evidence=[
            {
                "id": value.item.id,
                "category": value.item.category,
                "score": value.score,
                "reasons": list(value.reasons),
            }
            for value in ranked
        ],
        cards=[
            {
                "id": card.id,
                "type": card.type,
                "evidence_ids": list(card.evidence_ids),
                "interpretation_level": card.interpretation_level,
                "action_types": [action.type for action in card.dig_deeper_actions],
            }
            for card in result.packet.cards
        ],
    )


def _core_checks(
    *,
    bundle: Any,
    rebuilt: Any,
    ranked: Sequence[Any],
    packet: Any,
    validation: Any,
    candidate_limit: int,
    maximum_cards: int,
) -> list[PresentationEvalCheck]:
    source_ids = {
        str(source.get("id"))
        for source in bundle.provenance.get("sources", [])
        if isinstance(source, Mapping) and source.get("id")
    }
    referenced_sources = {
        source_id for item in bundle.evidence_items for source_id in item.source_ids
    }
    return [
        _check(
            "stable_evidence_identity",
            bundle.evidence_hash == rebuilt.evidence_hash
            and [item.id for item in bundle.evidence_items]
            == [item.id for item in rebuilt.evidence_items],
            {"hash": bundle.evidence_hash, "ids": [item.id for item in bundle.evidence_items]},
            "identical hash and evidence IDs on rebuild",
        ),
        _check(
            "source_provenance_complete",
            referenced_sources <= source_ids,
            sorted(referenced_sources - source_ids),
            "no missing source IDs",
        ),
        _check(
            "candidate_limit",
            len(ranked) <= candidate_limit,
            len(ranked),
            f"<= {candidate_limit}",
        ),
        _check(
            "card_limit",
            len(packet.cards) <= maximum_cards,
            len(packet.cards),
            f"<= {maximum_cards}",
        ),
        _check(
            "packet_validation",
            validation.valid,
            list(validation.errors),
            "valid grounded PresentationPacket",
        ),
    ]


def _expectation_checks(
    *,
    fixture: Mapping[str, Any],
    expectations: Mapping[str, Any],
    bundle: Any,
    ranked: Sequence[Any],
    packet: Any,
    presentation_mode: str,
) -> list[PresentationEvalCheck]:
    checks: list[PresentationEvalCheck] = []
    categories = {item.category for item in bundle.evidence_items}
    legacy_categories = _strings(fixture.get("expected_categories"))
    if legacy_categories:
        checks.append(
            _check(
                "expected_category_overlap",
                bool(categories.intersection(legacy_categories)),
                sorted(categories),
                {"any_of": legacy_categories},
            )
        )
    checks.extend(
        _set_expectation_checks(
            actual={card.type for card in packet.cards},
            required=_strings(expectations.get("required_card_types")),
            forbidden=_strings(expectations.get("forbidden_card_types")),
            required_id="required_card_types",
            forbidden_id="forbidden_card_types",
        )
    )
    checks.extend(
        _set_expectation_checks(
            actual=categories,
            required=_strings(expectations.get("required_categories")),
            forbidden=_strings(expectations.get("forbidden_categories")),
            required_id="required_categories",
            forbidden_id="forbidden_categories",
        )
    )
    cited = {evidence_id for card in packet.cards for evidence_id in card.evidence_ids}
    checks.extend(
        _set_expectation_checks(
            actual=cited,
            required=_strings(expectations.get("required_cited_evidence_ids")),
            forbidden=_strings(expectations.get("forbidden_cited_evidence_ids")),
            required_id="required_cited_evidence_ids",
            forbidden_id="forbidden_cited_evidence_ids",
        )
    )
    action_types = {
        action.type for card in packet.cards for action in card.dig_deeper_actions
    }
    checks.extend(
        _set_expectation_checks(
            actual=action_types,
            required=_strings(expectations.get("required_action_types")),
            forbidden=_strings(expectations.get("forbidden_action_types")),
            required_id="required_action_types",
            forbidden_id="forbidden_action_types",
        )
    )
    for key, actual in (
        ("minimum_evidence", len(bundle.evidence_items)),
        ("minimum_ranked", len(ranked)),
        ("minimum_cards", len(packet.cards)),
    ):
        if key in expectations:
            expected = int(expectations[key])
            checks.append(_check(key, actual >= expected, actual, f">= {expected}"))
    for key, actual in (
        ("maximum_evidence", len(bundle.evidence_items)),
        ("maximum_ranked", len(ranked)),
        ("maximum_cards", len(packet.cards)),
    ):
        if key in expectations:
            expected = int(expectations[key])
            checks.append(_check(key, actual <= expected, actual, f"<= {expected}"))
    if expectations.get("expected_mode") is not None:
        expected_mode = str(expectations["expected_mode"])
        checks.append(
            _check(
                "expected_mode",
                presentation_mode == expected_mode,
                presentation_mode,
                expected_mode,
            )
        )
    return checks


def _set_expectation_checks(
    *,
    actual: set[str],
    required: list[str],
    forbidden: list[str],
    required_id: str,
    forbidden_id: str,
) -> list[PresentationEvalCheck]:
    checks: list[PresentationEvalCheck] = []
    if required:
        checks.append(_check(required_id, set(required) <= actual, sorted(actual), required))
    if forbidden:
        checks.append(
            _check(forbidden_id, not actual.intersection(forbidden), sorted(actual), forbidden)
        )
    return checks


def _check(check_id: str, passed: bool, observed: Any, expected: Any) -> PresentationEvalCheck:
    return PresentationEvalCheck(check_id, bool(passed), observed, expected)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [str(item) for item in value]


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
