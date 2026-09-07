"""Deterministic grouping primitives for bounded prose remediation.

The Terra remediation runner deliberately accepts no more than three chapters
per invocation.  This module owns only the reusable grouping and plan-shape
rules needed to coordinate any number of those bounded invocations.  It does
not select evidence, alter CKL data, or change the per-chapter retry policy.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from bhf_agent.references import BOOKS


MAX_REMEDIATION_GROUP_SIZE = 3
_REFERENCE_RE = re.compile(r"^(?P<book>.+?)\s+(?P<chapter>\d+)$")
_BOOK_ORDER = {book: index for index, book in enumerate(BOOKS, start=1)}


def canonical_reference_sort_key(reference: str) -> tuple[int, int, str]:
    """Return the repository's stable book/chapter ordering key."""

    value = str(reference)
    match = _REFERENCE_RE.match(value)
    if not match:
        return (len(_BOOK_ORDER) + 1, 0, value)
    return (
        _BOOK_ORDER.get(match.group("book"), len(_BOOK_ORDER) + 1),
        int(match.group("chapter")),
        value,
    )


def ordered_unique_references(references: Iterable[str]) -> list[str]:
    """Normalize, deduplicate, and canonically order references."""

    return sorted({str(reference) for reference in references}, key=canonical_reference_sort_key)


def chunk_references(
    references: Iterable[str],
    maximum: int = MAX_REMEDIATION_GROUP_SIZE,
) -> list[list[str]]:
    """Partition references into deterministic bounded groups."""

    if maximum < 1:
        raise ValueError("remediation group maximum must be positive")
    ordered = ordered_unique_references(references)
    return [ordered[index:index + maximum] for index in range(0, len(ordered), maximum)]


def build_remediation_groups(
    references: Iterable[str],
    *,
    attempt: int = 1,
    maximum: int = MAX_REMEDIATION_GROUP_SIZE,
) -> list[dict[str, Any]]:
    """Build durable plan records for bounded groups."""

    return [
        {
            "group_id": f"group-{index:03d}",
            "references": group,
            "attempt": attempt,
            "status": "PENDING",
        }
        for index, group in enumerate(chunk_references(references, maximum), start=1)
    ]
