"""Developer-only CKL inspection helpers for the web app."""

from __future__ import annotations

import time
from typing import Any, Mapping

from bhf_agent.ckl import (
    build_canonical_context,
    build_canonical_query,
    canonical_context_has_strong_match,
    format_canonical_context_for_prompt,
    load_canonical_library,
)
from framework.canonical_library import (
    CKLRetrievalService,
    build_canonical_prompt_context,
)
from framework.canonical_library.retrieval.models import QueryAnalysis


NO_STRONG_MATCH_PROMPT = (
    "The Canonical Knowledge Library did not find a strong match for this question. "
    "Answer generally without inventing CKL facts, and state briefly if the library does not yet cover the topic."
)

INSPECTOR_LIMIT = 8
INSPECTOR_MAX_CONTEXT_TOKENS = 3000


def build_search_inspector_payload(
    query: str,
    *,
    limit: int = INSPECTOR_LIMIT,
    answer_mode: str = "study",
    max_context_tokens: int = INSPECTOR_MAX_CONTEXT_TOKENS,
    debug: bool = True,
) -> dict[str, Any]:
    normalized_query = str(query or "").strip()
    resolved_limit = _clamp_limit(limit)
    service = CKLRetrievalService.load_default()

    retrieval_started_at = time.perf_counter()
    search_response = service.search(normalized_query, limit=resolved_limit, debug=debug)
    retrieval_duration_ms = int(round((time.perf_counter() - retrieval_started_at) * 1000))

    canonical_library = load_canonical_library()
    canonical_context = None
    prompt_preview = ""
    prompt_note = None
    prompt_kind = "no_match"

    if normalized_query:
        canonical_context = build_canonical_context(
            canonical_library,
            normalized_query,
            max_results=resolved_limit,
            answer_mode=answer_mode,
            max_context_tokens=max_context_tokens,
        )

    prompt_preview, prompt_note, prompt_kind = _prompt_preview_for_context(
        canonical_context,
        answer_mode=answer_mode,
        max_context_tokens=max_context_tokens,
    )
    prompt_context = _build_prompt_context(
        canonical_context,
        answer_mode=answer_mode,
        max_context_tokens=max_context_tokens,
    )

    analysis = _analysis_payload(search_response.analysis)
    search_results = [result.to_dict(debug=debug) for result in search_response.results]

    return {
        "question": normalized_query,
        "canonical_query": normalized_query,
        "analysis": analysis,
        "search": {
            "normalized_query": search_response.normalized_query,
            "results": search_results,
            "stats": search_response.stats.to_dict(),
        },
        "retrieval": {
            "duration_ms": retrieval_duration_ms,
            "result_count": len(search_results),
            "selected_entry_ids": list(
                prompt_context.get("metadata", {}).get("selected_entry_ids") or []
            ),
            "context_token_count": int(
                prompt_context.get("metadata", {}).get("estimated_tokens") or 0
            ),
            "prompt_mode": prompt_kind,
            "strong_match": bool(canonical_context and canonical_context_has_strong_match(canonical_context)),
        },
        "prompt": {
            "kind": prompt_kind,
            "note": prompt_note,
            "preview": prompt_preview,
            "context": prompt_context,
        },
        "model": {
            "duration_ms": None,
            "provider": None,
            "model": None,
        },
    }


def build_result_inspector_payload(
    question: str,
    result: Any,
    *,
    limit: int = INSPECTOR_LIMIT,
    max_context_tokens: int = INSPECTOR_MAX_CONTEXT_TOKENS,
    debug: bool = True,
) -> dict[str, Any]:
    resolved_limit = _clamp_limit(limit)
    model_metadata = dict(getattr(result, "model_metadata", {}) or {})
    pipeline = model_metadata.get("pipeline") if isinstance(model_metadata.get("pipeline"), Mapping) else {}
    reference_context = getattr(result, "reference_context", None)
    question_context = getattr(result, "question_context", None)
    answer_mode = str(model_metadata.get("answer_mode") or pipeline.get("answer_mode") or "study").strip() or "study"

    canonical_query = build_canonical_query(question, reference_context, question_context)
    canonical_context = model_metadata.get("canonical_library_context")
    if not isinstance(canonical_context, Mapping):
        canonical_context = None

    if canonical_context is None and canonical_query:
        canonical_library = load_canonical_library()
        canonical_context = build_canonical_context(
            canonical_library,
            canonical_query,
            max_results=resolved_limit,
            answer_mode=answer_mode,
            max_context_tokens=max_context_tokens,
        )
    rollout_mode = _canonical_library_rollout_mode(pipeline, canonical_context)

    retrieval_duration_ms = _safe_int(pipeline.get("canonical_library_retrieval_duration_ms"))
    model_duration_ms = _safe_int(
        pipeline.get("model_request_duration_ms") or model_metadata.get("latency_ms")
    )
    model_provider = (
        model_metadata.get("provider")
        or model_metadata.get("adapter_type")
        or pipeline.get("provider")
    )
    model_name = model_metadata.get("model") or model_metadata.get("configured_model") or pipeline.get("model")

    search_started_at = time.perf_counter()
    search_response = CKLRetrievalService.load_default().search(
        canonical_query or question,
        limit=resolved_limit,
        debug=debug,
    )
    search_duration_ms = int(round((time.perf_counter() - search_started_at) * 1000))
    analysis = _analysis_payload(search_response.analysis)
    search_results = [result.to_dict(debug=debug) for result in search_response.results]
    prompt_context = _build_prompt_context(
        canonical_context,
        answer_mode=answer_mode,
        max_context_tokens=max_context_tokens,
    )
    prompt_preview, prompt_note, prompt_kind = _prompt_preview_for_pipeline(
        canonical_context,
        answer_mode=answer_mode,
        max_context_tokens=max_context_tokens,
        prompt_mode=str(pipeline.get("canonical_library_prompt_mode") or "").strip(),
        rollout_mode=rollout_mode,
    )
    shadow_prompt_preview = ""
    shadow_prompt_note = None
    shadow_prompt_kind = None
    if rollout_mode == "shadow":
        shadow_prompt_preview, shadow_prompt_note, shadow_prompt_kind = _prompt_preview_for_context(
            canonical_context,
            answer_mode=answer_mode,
            max_context_tokens=max_context_tokens,
        )
        if pipeline.get("canonical_library_error"):
            shadow_prompt_note = (
                "CKL retrieval reported an error while running in shadow mode."
            )

    return {
        "question": str(question or "").strip(),
        "canonical_query": canonical_query,
        "analysis": analysis,
        "search": {
            "normalized_query": search_response.normalized_query,
            "results": search_results,
            "stats": search_response.stats.to_dict(),
        },
        "retrieval": {
            "duration_ms": retrieval_duration_ms if retrieval_duration_ms is not None else search_duration_ms,
            "result_count": len(search_results),
            "selected_entry_ids": list(
                prompt_context.get("metadata", {}).get("selected_entry_ids") or []
            ),
            "context_token_count": _safe_int(
                pipeline.get("canonical_library_prompt_tokens")
            )
            or int(prompt_context.get("metadata", {}).get("estimated_tokens") or 0),
            "prompt_mode": prompt_kind,
            "rollout_mode": rollout_mode,
            "shadow_mode": rollout_mode == "shadow",
            "strong_match": bool(
                canonical_context and canonical_context_has_strong_match(canonical_context)
            ),
        },
        "prompt": {
            "kind": prompt_kind,
            "note": prompt_note,
            "preview": prompt_preview,
            "shadow_kind": shadow_prompt_kind,
            "shadow_note": shadow_prompt_note,
            "shadow_preview": shadow_prompt_preview,
            "context": prompt_context,
        },
        "model": {
            "duration_ms": model_duration_ms,
            "provider": model_provider,
            "model": model_name,
        },
    }


def _analysis_payload(analysis: QueryAnalysis) -> dict[str, Any]:
    payload = analysis.to_dict()
    payload["scripture_reference_texts"] = [
        _scripture_reference_text(reference)
        for reference in analysis.scripture_references
    ]
    return payload


def _build_prompt_context(
    canonical_context: Mapping[str, Any] | None,
    *,
    answer_mode: str,
    max_context_tokens: int,
) -> dict[str, Any]:
    if not canonical_context:
        return _empty_prompt_context(
            answer_mode=answer_mode,
            max_context_tokens=max_context_tokens,
        )
    max_entries, max_facts_per_entry, max_scripture_references_per_entry, max_caution_notes_per_entry = _prompt_limits(
        answer_mode
    )
    return build_canonical_prompt_context(
        canonical_context,
        max_context_tokens=max_context_tokens,
        max_entries=max_entries,
        max_facts_per_entry=max_facts_per_entry,
        max_scripture_references_per_entry=max_scripture_references_per_entry,
        max_caution_notes_per_entry=max_caution_notes_per_entry,
    )


def _prompt_preview_for_context(
    canonical_context: Mapping[str, Any] | None,
    *,
    answer_mode: str,
    max_context_tokens: int,
) -> tuple[str, str | None, str]:
    if not canonical_context:
        return "", "CKL search did not return a usable context block.", "no_match"

    if canonical_context_has_strong_match(canonical_context):
        preview = format_canonical_context_for_prompt(
            canonical_context,
            max_context_tokens=max_context_tokens,
            answer_mode=answer_mode,
        )
        return preview, None, "summary"

    return NO_STRONG_MATCH_PROMPT, "CKL retrieval found context, but not a strong enough match to inject the full block.", "no_strong_match"


def _prompt_preview_for_pipeline(
    canonical_context: Mapping[str, Any] | None,
    *,
    answer_mode: str,
    max_context_tokens: int,
    prompt_mode: str,
    rollout_mode: str,
) -> tuple[str, str | None, str]:
    if rollout_mode == "shadow":
        return (
            "",
            "CKL was retrieved in shadow mode, so the model did not receive the CKL block.",
            "disabled",
        )
    if prompt_mode == "summary" and canonical_context:
        preview = format_canonical_context_for_prompt(
            canonical_context,
            max_context_tokens=max_context_tokens,
            answer_mode=answer_mode,
        )
        return preview, None, "summary"
    if prompt_mode == "no_strong_match":
        return (
            NO_STRONG_MATCH_PROMPT,
            "The model received the CKL no-strong-match instruction instead of the full context block.",
            "no_strong_match",
        )
    if prompt_mode == "retrieval_failed":
        return (
            "",
            "CKL retrieval failed, so no CKL prompt block was injected.",
            "retrieval_failed",
        )
    if prompt_mode == "disabled":
        return "", "CKL retrieval is disabled for this request.", "disabled"
    if canonical_context and canonical_context_has_strong_match(canonical_context):
        preview = format_canonical_context_for_prompt(
            canonical_context,
            max_context_tokens=max_context_tokens,
            answer_mode=answer_mode,
        )
        return preview, None, "summary"
    if canonical_context:
        return (
            NO_STRONG_MATCH_PROMPT,
            "CKL retrieval found context, but not a strong enough match to inject the full block.",
            "no_strong_match",
        )
    return "", "CKL did not contribute a prompt block for this request.", "no_match"


def _canonical_library_rollout_mode(
    pipeline: Mapping[str, Any],
    canonical_context: Mapping[str, Any] | None,
) -> str:
    rollout_mode = str(pipeline.get("canonical_library_rollout_mode") or "").strip()
    if rollout_mode:
        return rollout_mode
    if bool(pipeline.get("canonical_library_shadow_mode")) and not bool(
        pipeline.get("canonical_library_enabled", True)
    ):
        return "shadow"
    if bool(pipeline.get("canonical_library_loaded")) or canonical_context is not None:
        return "enabled"
    return "disabled"


def _empty_prompt_context(
    *,
    answer_mode: str,
    max_context_tokens: int,
) -> dict[str, Any]:
    max_entries, max_facts_per_entry, max_scripture_references_per_entry, max_caution_notes_per_entry = _prompt_limits(
        answer_mode
    )
    return {
        "entries": [],
        "metadata": {
            "token_budget": max_context_tokens,
            "max_entries": max_entries,
            "max_facts_per_entry": max_facts_per_entry,
            "max_scripture_references_per_entry": max_scripture_references_per_entry,
            "max_caution_notes_per_entry": max_caution_notes_per_entry,
            "entry_count": 0,
            "fact_count": 0,
            "scripture_reference_count": 0,
            "caution_note_count": 0,
            "estimated_tokens": 0,
            "remaining_tokens": max_context_tokens,
            "truncated": False,
            "selected_entry_ids": [],
            "selected_entry_versions": [],
        },
    }


def _prompt_limits(answer_mode: str) -> tuple[int, int, int, int]:
    normalized = str(answer_mode or "study").strip().lower()
    if normalized == "concise":
        return 4, 2, 3, 1
    if normalized in {"study", "teaching"}:
        return 6, 3, 5, 2
    return 8, 5, 6, 3


def _scripture_reference_text(reference: Any) -> str:
    if hasattr(reference, "book"):
        book = str(getattr(reference, "book", "") or "").strip()
        start_chapter = getattr(reference, "start_chapter", None)
        start_verse = getattr(reference, "start_verse", None)
        end_chapter = getattr(reference, "end_chapter", None)
        end_verse = getattr(reference, "end_verse", None)
    elif isinstance(reference, Mapping):
        book = str(reference.get("book") or "").strip()
        start_chapter = reference.get("start_chapter")
        start_verse = reference.get("start_verse")
        end_chapter = reference.get("end_chapter")
        end_verse = reference.get("end_verse")
    else:
        return str(reference or "").strip()

    if not book:
        return ""
    if start_chapter is None:
        return book

    text = f"{book} {start_chapter}"
    if start_verse is not None:
        text += f":{start_verse}"
        if end_chapter is not None and end_verse is not None:
            text += f"-{end_chapter}:{end_verse}"
        elif end_verse is not None:
            text += f"-{end_verse}"
    return text


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _clamp_limit(value: Any) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return INSPECTOR_LIMIT
    return max(1, min(limit, INSPECTOR_LIMIT))
