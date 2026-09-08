"""Application-owned normalization immediately before Commentary validation.

Raw renderer bytes are deliberately not changed here.  This module produces a
separate validation payload and a small audit record explaining every derived
field.  In particular, the fixed DATA_GAP availability notice belongs to BHF,
not to a renderer.
"""

from __future__ import annotations

from typing import Any

from bhf_agent.chapter_commentary.models import data_gap_fallback_payload


DATA_GAP_NORMALIZATION_VERSION = "commentary-production-data-gap-normalization-v1"


def normalize_data_gap_fallback(
    payload: dict[str, Any],
    *,
    expected_evidence_availability: str,
    evidence_item_count: int,
    synthesis_unit_count: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Add only the application-owned true-DATA_GAP fallback.

    An empty list is intentionally required rather than treating absent or
    malformed sections as an empty renderer response.  Identity, metadata,
    and status are not repaired here; the canonical validator still owns
    their validation.
    """

    normalized = dict(payload)
    renderer_sections = payload.get("sections")
    true_data_gap = (
        expected_evidence_availability == "DATA_GAP"
        and evidence_item_count == 0
        and synthesis_unit_count == 0
    )
    empty_renderer_sections = renderer_sections == []
    applied = true_data_gap and empty_renderer_sections
    if applied:
        # This supplies the fixed notice shape, but intentionally leaves the
        # renderer's identity fields intact for canonical validation.
        fallback = data_gap_fallback_payload("", "", 1)
        normalized["data_gap_fallback"] = True
        normalized["sections"] = fallback["sections"]

    audit = {
        "normalization_version": DATA_GAP_NORMALIZATION_VERSION,
        "kind": "APPLICATION_OWNED_DATA_GAP_FALLBACK",
        "applied": applied,
        "authoritative_conditions": {
            "expected_evidence_availability": expected_evidence_availability,
            "evidence_item_count": evidence_item_count,
            "synthesis_unit_count": synthesis_unit_count,
            "renderer_sections_exactly_empty": empty_renderer_sections,
        },
        "raw_renderer_data_gap_fallback": payload.get("data_gap_fallback"),
    }
    return normalized, audit

