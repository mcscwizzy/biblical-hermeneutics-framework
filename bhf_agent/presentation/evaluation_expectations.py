"""Strict fixture expectations for presentation evaluations."""

from __future__ import annotations

from typing import Any, Mapping


LIST_FIELDS = frozenset(
    {
        "required_card_types",
        "forbidden_card_types",
        "required_categories",
        "forbidden_categories",
        "required_cited_evidence_ids",
        "forbidden_cited_evidence_ids",
        "required_action_types",
        "forbidden_action_types",
    }
)
COUNT_FIELDS = frozenset(
    {
        "minimum_evidence",
        "maximum_evidence",
        "minimum_ranked",
        "maximum_ranked",
        "minimum_cards",
        "maximum_cards",
    }
)
ALLOWED_FIELDS = LIST_FIELDS | COUNT_FIELDS | {"expected_mode"}


def validate_presentation_expectations(
    value: Any,
    *,
    reference: str,
) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(
            f"presentation fixture case {reference} presentation_expectations must be an object"
        )
    unknown = sorted(set(value) - ALLOWED_FIELDS)
    if unknown:
        raise ValueError(
            f"presentation fixture case {reference} has unknown expectation(s): "
            f"{', '.join(unknown)}"
        )
    normalized = dict(value)
    for field_name in LIST_FIELDS.intersection(value):
        items = value[field_name]
        if not isinstance(items, list) or not all(
            isinstance(item, str) and item.strip() for item in items
        ):
            raise ValueError(
                f"presentation fixture case {reference} {field_name} must be a list "
                "of non-empty strings"
            )
        normalized[field_name] = [item.strip() for item in items]
    for field_name in COUNT_FIELDS.intersection(value):
        count = value[field_name]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(
                f"presentation fixture case {reference} {field_name} must be a "
                "non-negative integer"
            )
    if "expected_mode" in value:
        mode = value["expected_mode"]
        if not isinstance(mode, str) or not mode.strip():
            raise ValueError(
                f"presentation fixture case {reference} expected_mode must be a non-empty string"
            )
        normalized["expected_mode"] = mode.strip()
    return normalized
