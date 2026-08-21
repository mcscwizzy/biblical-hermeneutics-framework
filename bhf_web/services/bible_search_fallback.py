"""Deterministic Bible-search fallback helpers.

The local ASV verse search already handles direct and phrase matches.
This module builds a small, deterministic passage-suggestion payload when
that local search misses and the UI wants likely passages to explore next.
"""

from __future__ import annotations

from typing import Any, Sequence

from bhf_agent.bible import parse_reference_query, resolve_passage
from bhf_agent.ckl import load_canonical_library
from bhf_agent.config import CanonicalLibraryConfig
from framework.canonical_library.normalization import (
    STOP_WORDS,
    normalize_alias,
    tokenize_query,
)

DEFAULT_FALLBACK_LIMIT = 8


def build_bible_search_fallback_payload(
    query: str,
    *,
    canonical_library: CanonicalLibraryConfig | None = None,
    limit: int = DEFAULT_FALLBACK_LIMIT,
) -> dict[str, Any]:
    normalized_query = " ".join(str(query or "").split())
    if not normalized_query:
        return {
            "source": "ckl_fallback",
            "query": "",
            "results": [],
            "message": "Search query is required.",
        }

    config = canonical_library or CanonicalLibraryConfig()
    if not _canonical_library_enabled(config):
        return {
            "source": "ckl_fallback",
            "query": normalized_query,
            "results": [],
            "message": "The Canonical Knowledge Library is disabled for this request.",
        }

    max_results = max(
        1,
        min(
            int(limit),
            int(getattr(config, "max_results", limit) or limit),
            DEFAULT_FALLBACK_LIMIT,
        ),
    )
    query_terms = _query_terms(normalized_query)
    library = load_canonical_library(config=config)
    search_results = library.retrieve_hybrid(
        normalized_query,
        limit=max_results * 2,
        include_placeholders=bool(getattr(config, "include_placeholders", False)),
        allowed_statuses=(
            tuple(getattr(config, "allowed_statuses", ()))
            if getattr(config, "allowed_statuses", None)
            else None
        ),
    )

    passages: list[dict[str, Any]] = []
    group_counts: dict[tuple[str, int], int] = {}
    seen_references: set[tuple[str, int, int | None, int | None]] = set()
    for result in search_results:
        selected_reference = _select_scripture_reference(
            getattr(result.object, "scripture_references", []) or [],
            query_terms=query_terms,
        )
        if selected_reference is None:
            continue

        parsed_reference = parse_reference_query(selected_reference.reference)
        if parsed_reference is None:
            continue

        reference_key = (
            str(parsed_reference["book"]),
            int(parsed_reference["chapter"]),
            parsed_reference.get("verse_start"),
            parsed_reference.get("verse_end"),
        )
        if reference_key in seen_references:
            continue

        try:
            passage = resolve_passage(
                parsed_reference["book"],
                parsed_reference["chapter"],
                parsed_reference.get("verse_start"),
                parsed_reference.get("verse_end"),
            )
        except Exception:
            continue

        group_key = (str(passage["book"]).lower(), int(passage["chapter"]))
        group_counts[group_key] = group_counts.get(group_key, 0) + 1
        passages.append(
            {
                "book": passage["book"],
                "chapter": passage["chapter"],
                "verse_start": passage["start_verse"],
                "verse_end": passage["end_verse"],
                "reference": passage["reference"],
                "reason": _result_reason(result),
                "confidence": _confidence_label(float(result.score or 0.0)),
                "match_type": "ckl_reference",
            }
        )
        seen_references.add(reference_key)
    passages.sort(
        key=lambda item: (
            -group_counts.get((str(item["book"]).lower(), int(item["chapter"])), 0),
            -float(item.get("confidence") == "strong"),
        )
    )
    passages = passages[:max_results]

    if passages:
        return {
            "source": "ckl_fallback",
            "query": normalized_query,
            "results": passages,
            "message": _success_message(passages),
        }

    return {
        "source": "ckl_fallback",
        "query": normalized_query,
        "results": [],
        "message": (
            "The Canonical Knowledge Library does not yet cover this topic well enough "
            "to suggest likely passages."
        ),
    }


def _canonical_library_enabled(config: CanonicalLibraryConfig) -> bool:
    return bool(config.enabled or config.shadow_mode)


def _query_terms(query: str) -> set[str]:
    return {
        token
        for token in tokenize_query(query)
        if token not in STOP_WORDS
    }


def _select_scripture_reference(
    references: Sequence[Any],
    *,
    query_terms: set[str],
) -> Any | None:
    ordered: list[Any] = []
    matched: list[Any] = []
    for reference in references:
        reference_text = str(getattr(reference, "reference", "") or "").strip()
        if not reference_text:
            continue
        parsed = parse_reference_query(reference_text)
        if parsed is None:
            continue
        ordered.append(reference)
        if normalize_alias(str(parsed["book"])) in query_terms:
            matched.append(reference)
    if matched:
        return matched[0]
    if ordered:
        return ordered[0]
    return None


def _result_reason(result: Any) -> str:
    summary = str(getattr(result.object, "summary", "") or "").strip()
    if summary:
        return summary
    title = str(getattr(result.object, "title", "") or "").strip()
    if title:
        return f"Referenced by the CKL entry for {title}."
    return "Referenced by the Canonical Knowledge Library."


def _confidence_label(score: float) -> str:
    if score >= 0.9:
        return "strong"
    if score >= 0.75:
        return "likely"
    if score >= 0.6:
        return "possible"
    return "uncertain"


def _success_message(passages: Sequence[dict[str, Any]]) -> str:
    count = len(passages)
    suffix = "" if count == 1 else "s"
    return (
        f"BHF suggested {count} likely passage{suffix} from the Canonical Knowledge Library."
    )
