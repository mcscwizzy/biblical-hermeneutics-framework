"""Public cache interfaces for future approved-answer reuse.

This module deliberately stops at interface and placeholder implementation
level. It does not persist anything and does not connect to the AI pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PublicCacheEntry:
    normalized_question: str
    answer: str
    quality_score: float
    usage_count: int
    review_status: str
    framework_version: str
    created_at: str | None = None
    updated_at: str | None = None


class PublicAnswerCache(Protocol):
    def lookup(self, normalized_question: str) -> PublicCacheEntry | None:
        ...

    def store(self, entry: PublicCacheEntry) -> None:
        ...

    def increment_usage(self, normalized_question: str) -> None:
        ...

    def update_review_status(self, normalized_question: str, status: str) -> None:
        ...


class NullPublicAnswerCache:
    """No-op placeholder implementation."""

    def lookup(self, normalized_question: str) -> PublicCacheEntry | None:
        return None

    def store(self, entry: PublicCacheEntry) -> None:  # noqa: ARG002 - interface
        return None

    def increment_usage(self, normalized_question: str) -> None:  # noqa: ARG002 - interface
        return None

    def update_review_status(self, normalized_question: str, status: str) -> None:  # noqa: ARG002 - interface
        return None

