"""Structured result models for deterministic CKL retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ..scripture import ScriptureReferenceSpan


@dataclass(frozen=True)
class ScoreSignal:
    name: str
    value: float
    matched_terms: list[str] = field(default_factory=list)
    matched_fields: list[str] = field(default_factory=list)
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QueryAnalysis:
    raw_query: str
    normalized_query: str
    terms: list[str] = field(default_factory=list)
    phrases: list[str] = field(default_factory=list)
    scripture_references: list[ScriptureReferenceSpan] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    object_categories: list[str] = field(default_factory=list)
    matched_terms_by_category: dict[str, list[str]] = field(default_factory=dict)
    intent: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scripture_references"] = [
            asdict(reference) if hasattr(reference, "__dict__") else reference
            for reference in self.scripture_references
        ]
        return data


@dataclass(frozen=True)
class CKLSearchResult:
    id: str
    category: str
    title: str
    score: float
    matched_terms: list[str] = field(default_factory=list)
    matched_fields: list[str] = field(default_factory=list)
    summary: str = ""
    source_path: str | None = None
    aliases: list[str] = field(default_factory=list)
    scripture_references: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    related_entries: list[str] = field(default_factory=list)
    content_status: str | None = None
    review_status: str | None = None
    confidence: str | None = None
    importance: int = 0
    score_details: list[ScoreSignal] = field(default_factory=list)

    def to_dict(self, *, debug: bool = False) -> dict[str, Any]:
        data = asdict(self)
        if not debug:
            data.pop("score_details", None)
        return data


@dataclass(frozen=True)
class CKLIndexStats:
    scanned_files: int = 0
    valid_documents: int = 0
    invalid_documents: int = 0
    indexed_entries: int = 0
    build_duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CKLSearchResponse:
    query: str
    normalized_query: str
    analysis: QueryAnalysis
    results: list[CKLSearchResult] = field(default_factory=list)
    stats: CKLIndexStats = field(default_factory=CKLIndexStats)

    def to_dict(self, *, debug: bool = False) -> dict[str, Any]:
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "analysis": self.analysis.to_dict(),
            "results": [result.to_dict(debug=debug) for result in self.results],
            "stats": self.stats.to_dict(),
        }
