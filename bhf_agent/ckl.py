"""Runtime helpers for integrating the Canonical Knowledge Library."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from framework.canonical_library import CanonicalContextBuilder, CanonicalLibrary
from framework.canonical_library.normalization import tokenize_query

from .models import QuestionContext, ReferenceContext


def _estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


QUESTION_STARTERS = {
    "how",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "can",
    "could",
    "did",
    "do",
    "does",
    "explain",
    "is",
    "may",
    "please",
    "should",
    "tell",
    "was",
    "were",
    "will",
    "would",
}

THEME_QUERY_TOKENS = {
    "adoption",
    "blessing",
    "covenant",
    "creation",
    "exile",
    "exodus",
    "faithfulness",
    "fall",
    "fire",
    "glory",
    "hope",
    "holy",
    "justice",
    "kingdom",
    "land",
    "light",
    "messiah",
    "mercy",
    "new",
    "peace",
    "presence",
    "prayer",
    "priesthood",
    "promise",
    "righteousness",
    "resurrection",
    "restoration",
    "sabbath",
    "sacrifice",
    "sanctuary",
    "shepherd",
    "spirit",
    "temple",
    "word",
    "worship",
    "water",
}

CAPITALIZED_TERM_RE = re.compile(r"\b[A-Z][A-Za-z0-9'-]+\b")


@lru_cache(maxsize=1)
def _load_default_canonical_library() -> CanonicalLibrary:
    return CanonicalLibrary.load_default()


def load_canonical_library(root: str | Path | None = None) -> CanonicalLibrary:
    """Return a loaded CKL instance, caching the default inventory in memory."""

    if root is None:
        return _load_default_canonical_library()
    return CanonicalLibrary(root=Path(root)).load()


def build_canonical_query(
    question: str,
    reference_context: ReferenceContext | None = None,
    question_context: QuestionContext | None = None,
) -> str:
    parts: list[str] = []

    def add_part(value: str | None) -> None:
        text = str(value or "").strip()
        if text and text not in parts:
            parts.append(text)

    add_part(question)
    if reference_context is not None:
        add_part(reference_context.book)
        if reference_context.book and reference_context.chapter is not None:
            add_part(f"{reference_context.book} {reference_context.chapter}")
            if reference_context.verse is not None:
                add_part(
                    f"{reference_context.book} {reference_context.chapter}:{reference_context.verse}"
                )
        add_part(reference_context.topic)
    if question_context is not None:
        add_part(question_context.target_language)
        for term in question_context.target_terms:
            add_part(term)

    return " ".join(parts).strip()


def _candidate_exact_queries(
    question: str,
    reference_context: ReferenceContext | None = None,
    question_context: QuestionContext | None = None,
) -> list[str]:
    candidates: list[str] = []

    def add(value: str | None) -> None:
        text = str(value or "").strip()
        if text and text not in candidates:
            candidates.append(text)

    if reference_context is not None:
        add(reference_context.book)
        add(reference_context.topic)
    if question_context is not None:
        for term in question_context.target_terms:
            add(term)

    for match in CAPITALIZED_TERM_RE.finditer(question):
        candidate = match.group(0).strip()
        if candidate.lower() in QUESTION_STARTERS:
            continue
        add(candidate)

    if question_context is None or question_context.question_type != "word_study":
        for token in tokenize_query(question):
            if token in THEME_QUERY_TOKENS:
                add(f"{token} theme")

    add(question)
    return candidates


def build_canonical_context(
    library: CanonicalLibrary,
    question: str,
    reference_context: ReferenceContext | None = None,
    question_context: QuestionContext | None = None,
    *,
    max_results: int = 5,
    include_placeholders: bool = True,
    allowed_statuses: Sequence[str] | None = None,
) -> dict[str, Any] | None:
    """Retrieve a compact CKL context package for one question."""

    query = build_canonical_query(question, reference_context, question_context)
    search_limit = max(max_results * 4, max_results, 12)
    builder = CanonicalContextBuilder(
        library,
        max_topics=search_limit,
        max_relationship_depth=0,
        max_expanded_topics=0,
    )
    context = builder.build(
        query,
        limit=search_limit,
        include_placeholders=include_placeholders,
        allowed_statuses=tuple(allowed_statuses) if allowed_statuses is not None else None,
    )

    broad_topics = list(context.get("retrieved_topics") or [])
    selected_topics: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    exact_queries = _candidate_exact_queries(question, reference_context, question_context)
    exact_count = 0
    for search_text in exact_queries:
        if len(selected_topics) >= max_results:
            break
        result = library.retrieve_exact(
            search_text,
            include_placeholders=include_placeholders,
            allowed_statuses=tuple(allowed_statuses) if allowed_statuses is not None else None,
        )
        if result is None or result.object.id in seen_ids:
            continue
        builder._append_topic(
            selected_topics,
            result.object,
            inclusion_type="primary",
            seen_ids=seen_ids,
            score=result.score,
            match_type=result.match_type,
            matched_alias=result.matched_alias,
            matched_terms=result.matched_terms,
            matched_fields=result.matched_fields,
        )
        exact_count += 1

    if len(selected_topics) < max_results:
        for topic in broad_topics:
            object_id = str(topic.get("id") or "").strip()
            if not object_id or object_id in seen_ids:
                continue
            selected_topics.append(topic)
            seen_ids.add(object_id)
            if len(selected_topics) >= max_results:
                break

    retrieved_topics = selected_topics
    if not retrieved_topics:
        return None

    metadata = dict(context.get("metadata") or {})
    retrieved_object_ids = [str(topic.get("id") or "").strip() for topic in retrieved_topics]
    retrieved_object_ids = [object_id for object_id in retrieved_object_ids if object_id]
    retrieval_method = "exact" if exact_count and exact_count == len(retrieved_topics) else "exact+keyword"
    if not exact_count:
        retrieval_method = str(metadata.get("retrieval_method") or "keyword").strip() or "keyword"
    metadata.update(
        {
            "query": query,
            "retrieved_object_ids": retrieved_object_ids,
            "retrieval_method": retrieval_method,
            "topic_count": len(retrieved_topics),
            "primary_topic_count": exact_count,
            "expanded_topic_count": 0,
            "max_results": max_results,
            "include_placeholders": include_placeholders,
            "allowed_statuses": list(allowed_statuses) if allowed_statuses is not None else None,
        }
    )
    context["metadata"] = metadata
    context["question"] = question
    context["query"] = query
    context["retrieved_object_ids"] = retrieved_object_ids
    return context


def format_canonical_context_for_prompt(
    context: Mapping[str, Any] | None,
    *,
    max_context_tokens: int = 1200,
) -> str:
    if not context:
        return ""

    retrieved_topics = list(context.get("retrieved_topics") or [])
    if not retrieved_topics:
        return ""

    metadata = dict(context.get("metadata") or {})
    lines: list[str] = [
        "# Canonical Knowledge Library",
        "Use this retrieved canonical context as grounding before inventing biblical details.",
        "Treat placeholder or unreviewed entries as scaffolding unless review policy says otherwise.",
    ]

    query = str(context.get("query") or metadata.get("query") or "").strip()
    if query:
        lines.append(f"- Query: {query}")

    retrieval_method = str(metadata.get("retrieval_method") or "none").strip()
    lines.append(f"- Retrieval method: {retrieval_method}")

    retrieved_ids = _render_list(metadata.get("retrieved_object_ids") or context.get("retrieved_object_ids"))
    if retrieved_ids:
        lines.append(f"- Retrieved object IDs: {retrieved_ids}")

    topic_count = metadata.get("topic_count")
    if topic_count is not None:
        lines.append(f"- Topic count: {topic_count}")

    primary_topic_count = metadata.get("primary_topic_count")
    if primary_topic_count is not None:
        lines.append(f"- Primary topic count: {primary_topic_count}")

    expanded_topic_count = metadata.get("expanded_topic_count")
    if expanded_topic_count is not None:
        lines.append(f"- Expanded topic count: {expanded_topic_count}")

    include_placeholders = metadata.get("include_placeholders")
    allowed_statuses = metadata.get("allowed_statuses")
    if include_placeholders is not None or allowed_statuses is not None:
        filter_bits = []
        if include_placeholders is not None:
            filter_bits.append(f"include_placeholders={str(bool(include_placeholders)).lower()}")
        if allowed_statuses:
            filter_bits.append(
                "allowed_statuses=" + ", ".join(str(value) for value in allowed_statuses)
            )
        if filter_bits:
            lines.append(f"- Status filter: {'; '.join(filter_bits)}")

    lines.extend(["", "## Retrieved Objects"])

    remaining_tokens = max(max_context_tokens, 1) - _estimate_tokens("\n".join(lines))
    rendered_topics = 0
    truncated = False
    for topic in retrieved_topics:
        block = _render_topic_block(topic, compact=False)
        block_tokens = _estimate_tokens(block)
        if block_tokens > remaining_tokens and rendered_topics == 0:
            block = _render_topic_block(topic, compact=True)
            block_tokens = _estimate_tokens(block)
        if block_tokens > remaining_tokens:
            truncated = True
            break
        lines.extend(block.splitlines())
        lines.append("")
        remaining_tokens -= block_tokens
        rendered_topics += 1

    if truncated:
        lines.extend(
            [
                "- Canonical context truncated to fit the token budget.",
                "",
            ]
        )

    shared_sections = [
        ("Historical Context", context.get("historical_context") or []),
        ("Ancient Near East Context", context.get("ancient_near_east_context") or []),
        ("Literary Context", context.get("literary_context") or []),
        ("Covenantal Significance", context.get("covenantal_significance") or []),
        ("Cross References", context.get("cross_references") or []),
        ("Word Studies", context.get("word_studies") or []),
        ("Related Topics", context.get("related_topics") or []),
        ("Timeline", context.get("timeline") or []),
        ("Archaeology", context.get("archaeology") or []),
        ("New Testament Connections", context.get("new_testament_connections") or []),
    ]
    shared_lines: list[str] = []
    for title, values in shared_sections:
        rendered = _render_list(values)
        if rendered:
            shared_lines.append(f"- {title}: {rendered}")
    if shared_lines and remaining_tokens > 0:
        lines.extend(["## Shared Context", *shared_lines, ""])

    prompt = "\n".join(line for line in lines if line is not None).strip()
    if _estimate_tokens(prompt) > max_context_tokens:
        prompt = _shrink_prompt(prompt, max_context_tokens)
    return prompt


def _render_topic_block(topic: Mapping[str, Any], *, compact: bool) -> str:
    object_id = str(topic.get("id") or "").strip() or "unknown"
    title = str(topic.get("title") or object_id).strip()
    type_name = str(topic.get("type") or "unknown").strip()
    match_type = str(topic.get("match_type") or "unknown").strip()
    inclusion_type = str(topic.get("inclusion_type") or "primary").strip()
    score = topic.get("score")
    content_status = str(topic.get("content_status") or "placeholder").strip()
    review_status = str(topic.get("review_status") or "unreviewed").strip()

    lines = [
        f"- {title} (`{object_id}`) [{type_name}]",
        f"  - Match: {match_type} ({inclusion_type})",
        f"  - Status: {content_status} / {review_status}",
    ]
    if score is not None:
        lines.append(f"  - Score: {float(score):.4f}")
    if compact:
        return "\n".join(lines)

    aliases = _render_list(topic.get("aliases") or [])
    if aliases:
        lines.append(f"  - Aliases: {aliases}")
    summary = str(topic.get("summary") or "").strip()
    if summary:
        lines.append(f"  - Summary: {summary}")
    historical_context = str(topic.get("historical_context") or "").strip()
    if historical_context:
        lines.append(f"  - Historical context: {historical_context}")
    ancient_near_east_context = str(topic.get("ancient_near_east_context") or "").strip()
    if ancient_near_east_context:
        lines.append(f"  - Ancient Near East context: {ancient_near_east_context}")
    literary_context = str(topic.get("literary_context") or "").strip()
    if literary_context:
        lines.append(f"  - Literary context: {literary_context}")
    covenantal_significance = str(topic.get("covenantal_significance") or "").strip()
    if covenantal_significance:
        lines.append(f"  - Covenantal significance: {covenantal_significance}")
    scripture_references = _render_scripture_references(topic.get("scripture_references") or [])
    if scripture_references:
        lines.append(f"  - Scripture references: {scripture_references}")
    related_objects = _render_related_objects(topic.get("related_objects") or [])
    if related_objects:
        lines.append(f"  - Related objects: {related_objects}")
    common_questions = _render_list(topic.get("common_questions") or [])
    if common_questions:
        lines.append(f"  - Common questions: {common_questions}")
    interpretive_notes = _render_list(topic.get("interpretive_notes") or [])
    if interpretive_notes:
        lines.append(f"  - Interpretive notes: {interpretive_notes}")
    sources = _render_sources(topic.get("sources") or [])
    if sources:
        lines.append(f"  - Sources: {sources}")
    return "\n".join(lines)


def _render_list(values: Any) -> str:
    if not isinstance(values, (list, tuple)):
        if values:
            return str(values)
        return ""
    rendered = [str(value).strip() for value in values if str(value).strip()]
    return ", ".join(rendered)


def _render_scripture_references(values: Any) -> str:
    if not isinstance(values, (list, tuple)):
        return ""
    rendered: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            reference = str(value.get("reference") or "").strip()
            relationship = str(value.get("relationship") or "").strip()
            if reference and relationship:
                rendered.append(f"{reference} ({relationship})")
            elif reference:
                rendered.append(reference)
        elif str(value).strip():
            rendered.append(str(value).strip())
    return ", ".join(rendered)


def _render_related_objects(values: Any) -> str:
    if not isinstance(values, (list, tuple)):
        return ""
    rendered: list[str] = []
    for value in values:
        if not isinstance(value, Mapping):
            if str(value).strip():
                rendered.append(str(value).strip())
            continue
        object_id = str(value.get("id") or "").strip()
        relationship = str(value.get("relationship") or "").strip()
        weight = value.get("weight")
        notes = str(value.get("notes") or "").strip()
        parts = [part for part in [object_id, relationship] if part]
        if weight is not None:
            parts.append(f"weight {weight}")
        if notes:
            parts.append(notes)
        if parts:
            rendered.append(" / ".join(parts))
    if rendered:
        return ", ".join(rendered)
    return ""


def _render_sources(values: Any) -> str:
    if not isinstance(values, (list, tuple)):
        return ""
    rendered: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            title = str(value.get("title") or "").strip()
            source_type = str(value.get("source_type") or "").strip()
            locator = str(value.get("locator") or "").strip()
            if title and locator:
                rendered.append(f"{title} [{locator}]")
            elif title:
                rendered.append(title)
            elif locator:
                rendered.append(locator)
            elif source_type:
                rendered.append(source_type)
        elif str(value).strip():
            rendered.append(str(value).strip())
    return ", ".join(rendered)


def _shrink_prompt(prompt: str, max_context_tokens: int) -> str:
    if _estimate_tokens(prompt) <= max_context_tokens:
        return prompt
    max_chars = max_context_tokens * 4
    trimmed = prompt[:max_chars].rstrip()
    if trimmed and not trimmed.endswith("..."):
        trimmed = trimmed.rstrip() + "\n..."
    return trimmed
