"""Bounded, evidence-preserving prose remediation policy.

This module deliberately contains no evidence selection or CKL access.  It
answers only whether an already-certified prose failure is eligible for one
automatic readability retry.
"""

from __future__ import annotations

from typing import Iterable


ALLOWLISTED_PROSE_FINDINGS = frozenset({"READER_UNFRIENDLY"})
MAX_AUTOMATIC_REGENERATION_ATTEMPTS = 1

INTEGRITY_FINDINGS = frozenset({
    "provenance failure",
    "unsupported claim",
    "textual routing error",
    "evidence mismatch",
    "semantic leakage",
    "archaeology misclassification",
    "later-reception leakage",
    "hash disagreement",
    "identity disagreement",
    "corrupted artifact",
    "cross-chapter contamination",
})


def regeneration_eligibility(
    reasons: Iterable[str],
    *,
    integrity_clean: bool,
    evidence_lock_valid: bool,
    attempts: int,
) -> tuple[bool, list[str]]:
    """Return ``(eligible, reasons_for_decision)`` for one bounded retry."""

    normalized = {str(reason) for reason in reasons}
    diagnostics: list[str] = []
    if not normalized:
        diagnostics.append("no remediable quality finding")
    disallowed = sorted(normalized - ALLOWLISTED_PROSE_FINDINGS)
    if disallowed:
        diagnostics.append(f"non-allowlisted findings: {', '.join(disallowed)}")
    if normalized & INTEGRITY_FINDINGS:
        diagnostics.append("integrity finding blocks automatic regeneration")
    if not integrity_clean:
        diagnostics.append("integrity checks are not clean")
    if not evidence_lock_valid:
        diagnostics.append("locked evidence is not valid")
    if attempts >= MAX_AUTOMATIC_REGENERATION_ATTEMPTS:
        diagnostics.append("automatic regeneration attempt limit reached")
    if attempts < 0:
        diagnostics.append("invalid negative regeneration attempt count")
    return not diagnostics, diagnostics

