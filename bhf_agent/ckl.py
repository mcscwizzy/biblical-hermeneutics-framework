"""Runtime helpers for integrating the Canonical Knowledge Library."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from framework.canonical_library import CanonicalContextBuilder, CanonicalLibrary
from framework.canonical_library.normalization import normalize_text, tokenize_query

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

ANSWER_MODE_DETAIL_LEVELS: dict[str, int] = {
    "concise": 0,
    "study": 1,
    "teaching": 1,
    "scholar": 2,
}

CONTEXT_TOPIC_BUDGET_RATIOS: dict[str, float] = {
    "concise": 0.5,
    "study": 0.65,
    "teaching": 0.6,
    "scholar": 0.8,
}

TOPIC_FIELDS_BY_DETAIL_LEVEL: dict[int, tuple[str, ...]] = {
    0: (
        "aliases",
        "summary",
        "scripture_references",
        "common_questions",
        "related_objects",
        "sources",
    ),
    1: (
        "aliases",
        "summary",
        "historical_context",
        "literary_context",
        "covenantal_significance",
        "scripture_references",
        "common_questions",
        "interpretive_notes",
        "related_objects",
        "sources",
    ),
    2: (
        "aliases",
        "summary",
        "historical_context",
        "ancient_near_east_context",
        "literary_context",
        "covenantal_significance",
        "scripture_references",
        "common_questions",
        "interpretive_notes",
        "timeline",
        "archaeology",
        "new_testament_connections",
        "related_objects",
        "sources",
    ),
}

SHARED_SECTION_FIELDS_BY_DETAIL_LEVEL: dict[int, tuple[tuple[str, str], ...]] = {
    0: (
        ("Historical Context", "historical_context"),
        ("Literary Context", "literary_context"),
        ("Cross References", "cross_references"),
        ("Related Topics", "related_topics"),
    ),
    1: (
        ("Historical Context", "historical_context"),
        ("Ancient Near East Context", "ancient_near_east_context"),
        ("Literary Context", "literary_context"),
        ("Covenantal Significance", "covenantal_significance"),
        ("Cross References", "cross_references"),
        ("Word Studies", "word_studies"),
        ("Related Topics", "related_topics"),
        ("Timeline", "timeline"),
        ("New Testament Connections", "new_testament_connections"),
    ),
    2: (
        ("Historical Context", "historical_context"),
        ("Ancient Near East Context", "ancient_near_east_context"),
        ("Literary Context", "literary_context"),
        ("Covenantal Significance", "covenantal_significance"),
        ("Cross References", "cross_references"),
        ("Word Studies", "word_studies"),
        ("Related Topics", "related_topics"),
        ("Timeline", "timeline"),
        ("Archaeology", "archaeology"),
        ("New Testament Connections", "new_testament_connections"),
    ),
}

SOURCE_LIMITS_BY_DETAIL_LEVEL: dict[int, int] = {
    0: 2,
    1: 3,
    2: 5,
}


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


def _normalize_answer_mode(answer_mode: str | None) -> str:
    mode = str(answer_mode or "study").strip().lower()
    return mode if mode in ANSWER_MODE_DETAIL_LEVELS else "study"


def _context_detail_level(answer_mode: str | None) -> int:
    return ANSWER_MODE_DETAIL_LEVELS[_normalize_answer_mode(answer_mode)]


def _topic_token_budget(max_context_tokens: int | None, answer_mode: str | None) -> int | None:
    if max_context_tokens is None:
        return None
    return max(0, int(max_context_tokens * CONTEXT_TOPIC_BUDGET_RATIOS[_normalize_answer_mode(answer_mode)]))


def _fact_key(value: str) -> str:
    return normalize_text(value)


def _record_fact(seen_facts: set[str] | None, value: str) -> bool:
    key = _fact_key(value)
    if not key:
        return False
    if seen_facts is not None:
        if key in seen_facts:
            return False
        seen_facts.add(key)
    return True


def _render_fact_list(
    values: Any,
    *,
    limit: int | None = None,
    seen_facts: set[str] | None = None,
) -> str:
    if not isinstance(values, (list, tuple)):
        text = str(values or "").strip()
        if text and _record_fact(seen_facts, text):
            return text
        return ""

    rendered: list[str] = []
    local_seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = _fact_key(text)
        if not key or key in local_seen:
            continue
        if seen_facts is not None and key in seen_facts:
            continue
        local_seen.add(key)
        if seen_facts is not None:
            seen_facts.add(key)
        rendered.append(text)
        if limit is not None and len(rendered) >= limit:
            break
    return ", ".join(rendered)


def _render_scripture_references(
    values: Any,
    *,
    limit: int | None = None,
    seen_facts: set[str] | None = None,
) -> str:
    if not isinstance(values, (list, tuple)):
        return ""
    rendered: list[str] = []
    local_seen: set[str] = set()
    for value in values:
        text = ""
        if isinstance(value, Mapping):
            reference = str(value.get("reference") or "").strip()
            relationship = str(value.get("relationship") or "").strip()
            if reference and relationship:
                text = f"{reference} ({relationship})"
            elif reference:
                text = reference
        else:
            text = str(value).strip()
        if not text:
            continue
        key = _fact_key(text)
        if not key or key in local_seen:
            continue
        if seen_facts is not None and key in seen_facts:
            continue
        local_seen.add(key)
        if seen_facts is not None:
            seen_facts.add(key)
        rendered.append(text)
        if limit is not None and len(rendered) >= limit:
            break
    return ", ".join(rendered)


def _render_related_objects(
    values: Any,
    *,
    limit: int | None = None,
    seen_facts: set[str] | None = None,
) -> str:
    if not isinstance(values, (list, tuple)):
        return ""
    rendered: list[str] = []
    local_seen: set[str] = set()
    for value in values:
        if isinstance(value, Mapping):
            object_id = str(value.get("id") or "").strip()
            relationship = str(value.get("relationship") or "").strip()
            weight = value.get("weight")
            notes = str(value.get("notes") or "").strip()
            parts = [part for part in [object_id, relationship] if part]
            if weight is not None:
                parts.append(f"weight {weight}")
            if notes:
                parts.append(notes)
            text = " / ".join(parts)
        else:
            text = str(value).strip()
        if not text:
            continue
        key = _fact_key(text)
        if not key or key in local_seen:
            continue
        if seen_facts is not None and key in seen_facts:
            continue
        local_seen.add(key)
        if seen_facts is not None:
            seen_facts.add(key)
        rendered.append(text)
        if limit is not None and len(rendered) >= limit:
            break
    return ", ".join(rendered)


def _render_source_entry(value: Any, *, detail_level: int) -> str:
    if isinstance(value, Mapping):
        title = str(value.get("title") or "").strip()
        locator = str(value.get("locator") or "").strip()
        author = str(value.get("author") or "").strip()
        publisher = str(value.get("publisher") or "").strip()
        source_type = str(value.get("source_type") or "").strip()
        notes = str(value.get("notes") or "").strip()
        year = value.get("year")

        parts: list[str] = []
        if title:
            parts.append(title)
        elif author:
            parts.append(author)
        elif source_type:
            parts.append(source_type)

        if detail_level <= 1:
            if locator:
                parts.append(f"[{locator}]")
            return " ".join(part for part in parts if part)

        if author and author not in parts:
            parts.append(author)
        if publisher:
            parts.append(publisher)
        if year is not None:
            parts.append(str(year))
        if source_type:
            parts.append(source_type)
        if locator:
            parts.append(locator)
        if notes:
            parts.append(notes)
        return " / ".join(part for part in parts if part)

    return str(value or "").strip()


def _render_sources(
    values: Any,
    *,
    detail_level: int,
    seen_facts: set[str] | None = None,
    limit: int | None = None,
) -> str:
    if not isinstance(values, (list, tuple)):
        text = _render_source_entry(values, detail_level=detail_level)
        if text and _record_fact(seen_facts, text):
            return text
        return ""

    rendered: list[str] = []
    local_seen: set[str] = set()
    effective_limit = limit if limit is not None else SOURCE_LIMITS_BY_DETAIL_LEVEL[detail_level]
    for value in values:
        text = _render_source_entry(value, detail_level=detail_level)
        if not text:
            continue
        key = _fact_key(text)
        if not key or key in local_seen:
            continue
        if seen_facts is not None and key in seen_facts:
            continue
        local_seen.add(key)
        if seen_facts is not None:
            seen_facts.add(key)
        rendered.append(text)
        if effective_limit is not None and len(rendered) >= effective_limit:
            break
    return ", ".join(rendered)


def _topic_fields_for_detail_level(detail_level: int, compact: bool) -> tuple[str, ...]:
    adjusted_level = max(0, detail_level - 1) if compact else detail_level
    if adjusted_level >= 2:
        return TOPIC_FIELDS_BY_DETAIL_LEVEL[2]
    if adjusted_level == 1:
        return TOPIC_FIELDS_BY_DETAIL_LEVEL[1]
    return TOPIC_FIELDS_BY_DETAIL_LEVEL[0]


def _shared_sections_for_detail_level(detail_level: int) -> tuple[tuple[str, str], ...]:
    return SHARED_SECTION_FIELDS_BY_DETAIL_LEVEL.get(
        detail_level,
        SHARED_SECTION_FIELDS_BY_DETAIL_LEVEL[1],
    )


def _render_topic_field(
    label: str,
    value: Any,
    *,
    detail_level: int,
    seen_facts: set[str] | None,
    compact: bool,
) -> str:
    if value is None:
        return ""

    limit = None
    if compact:
        limit_map = {
            "Aliases": 2,
            "Scripture references": 2,
            "Common questions": 1,
            "Interpretive notes": 1,
            "Related objects": 2,
            "Sources": max(1, SOURCE_LIMITS_BY_DETAIL_LEVEL[detail_level] - 1),
        }
        limit = limit_map.get(label)
    elif label in {"Aliases", "Scripture references", "Related objects"}:
        limit = 3
    elif label in {"Common questions", "Interpretive notes"}:
        limit = 2

    if label == "Scripture references":
        rendered = _render_scripture_references(value, limit=limit, seen_facts=seen_facts)
    elif label == "Related objects":
        rendered = _render_related_objects(value, limit=limit, seen_facts=seen_facts)
    elif label == "Sources":
        rendered = _render_sources(value, detail_level=detail_level, seen_facts=seen_facts, limit=limit)
    else:
        rendered = _render_fact_list(value, limit=limit, seen_facts=seen_facts)

    if not rendered:
        return ""
    return f"  - {label}: {rendered}"


def build_canonical_context(
    library: CanonicalLibrary,
    question: str,
    reference_context: ReferenceContext | None = None,
    question_context: QuestionContext | None = None,
    *,
    max_results: int = 5,
    include_placeholders: bool = True,
    allowed_statuses: Sequence[str] | None = None,
    answer_mode: str = "study",
    max_context_tokens: int | None = None,
) -> dict[str, Any] | None:
    """Retrieve a compact CKL context package for one question."""

    normalized_answer_mode = _normalize_answer_mode(answer_mode)
    query = build_canonical_query(question, reference_context, question_context)
    search_limit = max(max_results * 4, max_results, 12)
    topic_budget = _topic_token_budget(max_context_tokens, normalized_answer_mode)
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
    scripture_count = 0
    topic_tokens_used = 0

    def _track_topic_tokens(topic: Mapping[str, Any]) -> None:
        nonlocal topic_tokens_used
        topic_tokens_used += int(topic.get("estimated_tokens") or 0)

    def _within_topic_budget(topic: Mapping[str, Any]) -> bool:
        if topic_budget is None:
            return True
        if not selected_topics:
            return True
        estimated = int(topic.get("estimated_tokens") or 0)
        return topic_tokens_used + estimated <= topic_budget

    if reference_context is not None and reference_context.book:
        scripture_results = library.retrieve_by_scripture_reference(
            reference_context,
            limit=search_limit,
            include_placeholders=include_placeholders,
            allowed_statuses=tuple(allowed_statuses) if allowed_statuses is not None else None,
        )
        for result in scripture_results:
            if len(selected_topics) >= max_results:
                break
            if result.object.id in seen_ids:
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
            _track_topic_tokens(selected_topics[-1])
            scripture_count += 1

    if len(selected_topics) < max_results:
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
            _track_topic_tokens(selected_topics[-1])
            exact_count += 1

    expanded_count = 0
    if reference_context is not None and selected_topics and len(selected_topics) < max_results:
        graph_builder = CanonicalContextBuilder(
            library,
            max_topics=search_limit,
            max_relationship_depth=2 if normalized_answer_mode == "scholar" else 1,
            max_expanded_topics=max_results - len(selected_topics),
        )
        expanded_topics = graph_builder._expand_relationships(
            selected_topics,
            seen_ids,
            approved_only=False,
            exclude_deprecated=True,
            exclude_rejected=True,
            include_placeholders=include_placeholders,
            allowed_statuses=tuple(allowed_statuses) if allowed_statuses is not None else None,
            token_budget=max(topic_budget - topic_tokens_used, 0) if topic_budget is not None else None,
        )
        for topic in expanded_topics:
            if topic_budget is not None and not _within_topic_budget(topic):
                continue
            selected_topics.append(topic)
            _track_topic_tokens(topic)
        expanded_count = len(selected_topics) - exact_count - scripture_count

    if len(selected_topics) < max_results:
        for topic in broad_topics:
            object_id = str(topic.get("id") or "").strip()
            if not object_id or object_id in seen_ids:
                continue
            if topic_budget is not None and not _within_topic_budget(topic):
                continue
            selected_topics.append(topic)
            seen_ids.add(object_id)
            _track_topic_tokens(topic)
            if len(selected_topics) >= max_results:
                break

    retrieved_topics = selected_topics
    if not retrieved_topics:
        return None

    metadata = dict(context.get("metadata") or {})
    retrieved_object_ids = [str(topic.get("id") or "").strip() for topic in retrieved_topics]
    retrieved_object_ids = [object_id for object_id in retrieved_object_ids if object_id]
    retrieval_steps: list[str] = []
    if exact_count:
        retrieval_steps.append("exact")
    if scripture_count:
        retrieval_steps.append("scripture")
    if expanded_count:
        retrieval_steps.append("relationship")
    if len(retrieved_topics) > exact_count + scripture_count + expanded_count:
        retrieval_steps.append("keyword")
    retrieval_method = "+".join(dict.fromkeys(retrieval_steps))
    if not retrieval_method:
        retrieval_method = str(metadata.get("retrieval_method") or "keyword").strip() or "keyword"
    metadata.update(
        {
            "query": query,
            "retrieved_object_ids": retrieved_object_ids,
            "retrieval_method": retrieval_method,
            "answer_mode": normalized_answer_mode,
            "topic_count": len(retrieved_topics),
            "primary_topic_count": exact_count,
            "scripture_topic_count": scripture_count,
            "expanded_topic_count": expanded_count,
            "relationship_topic_count": expanded_count,
            "max_results": max_results,
            "max_context_tokens": max_context_tokens,
            "topic_token_budget": topic_budget,
            "estimated_topic_tokens": sum(int(topic.get("estimated_tokens") or 0) for topic in retrieved_topics),
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
    answer_mode: str = "study",
) -> str:
    if not context:
        return ""

    retrieved_topics = list(context.get("retrieved_topics") or [])
    if not retrieved_topics:
        return ""

    metadata = dict(context.get("metadata") or {})
    normalized_answer_mode = _normalize_answer_mode(answer_mode or metadata.get("answer_mode") or "study")
    detail_level = _context_detail_level(normalized_answer_mode)
    lines: list[str] = [
        "# Canonical Knowledge Library",
        "Use this retrieved canonical context as grounding before inventing biblical details.",
        "Treat placeholder or unreviewed entries as scaffolding unless review policy says otherwise.",
        f"- Answer mode: {normalized_answer_mode}",
        f"- Context tier: { {0: 'compact', 1: 'study', 2: 'scholar'}.get(detail_level, 'study') }",
    ]

    query = str(context.get("query") or metadata.get("query") or "").strip()
    if query:
        lines.append(f"- Query: {query}")

    retrieval_method = str(metadata.get("retrieval_method") or "none").strip()
    lines.append(f"- Retrieval method: {retrieval_method}")

    retrieved_ids = _render_fact_list(
        metadata.get("retrieved_object_ids") or context.get("retrieved_object_ids")
    )
    if retrieved_ids:
        lines.append(f"- Retrieved object IDs: {retrieved_ids}")

    topic_count = metadata.get("topic_count")
    if topic_count is not None:
        lines.append(f"- Topic count: {topic_count}")

    estimated_topic_tokens = metadata.get("estimated_topic_tokens")
    if estimated_topic_tokens is not None:
        lines.append(f"- Estimated topic tokens: {estimated_topic_tokens}")

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
    seen_facts: set[str] = set()
    for topic in retrieved_topics:
        compact = detail_level == 0
        block = _render_topic_block(
            topic,
            answer_mode=normalized_answer_mode,
            compact=compact,
            seen_facts=seen_facts,
        )
        block_tokens = _estimate_tokens(block)
        if block_tokens > remaining_tokens and not compact:
            compact_block = _render_topic_block(
                topic,
                answer_mode=normalized_answer_mode,
                compact=True,
                seen_facts=seen_facts,
            )
            compact_tokens = _estimate_tokens(compact_block)
            if compact_tokens <= remaining_tokens or rendered_topics == 0:
                block = compact_block
                block_tokens = compact_tokens
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

    shared_lines: list[str] = []
    for title, field_name in _shared_sections_for_detail_level(detail_level):
        rendered = _render_fact_list(context.get(field_name) or [], seen_facts=seen_facts)
        if rendered:
            shared_lines.append(f"- {title}: {rendered}")
    if shared_lines and remaining_tokens > 0:
        lines.extend(["## Shared Context", *shared_lines, ""])

    prompt = "\n".join(line for line in lines if line is not None).strip()
    if _estimate_tokens(prompt) > max_context_tokens:
        prompt = _shrink_prompt(prompt, max_context_tokens)
    return prompt



def _render_topic_block(
    topic: Mapping[str, Any],
    *,
    answer_mode: str,
    compact: bool,
    seen_facts: set[str] | None = None,
) -> str:
    object_id = str(topic.get("id") or "").strip() or "unknown"
    title = str(topic.get("title") or object_id).strip()
    type_name = str(topic.get("type") or "unknown").strip()
    match_type = str(topic.get("match_type") or "unknown").strip()
    inclusion_type = str(topic.get("inclusion_type") or "primary").strip()
    score = topic.get("score")
    content_status = str(topic.get("content_status") or "placeholder").strip()
    review_status = str(topic.get("review_status") or "unreviewed").strip()
    detail_level = _context_detail_level(answer_mode)

    lines = [
        f"- {title} (`{object_id}`) [{type_name}]",
        f"  - Match: {match_type} ({inclusion_type})",
        f"  - Status: {content_status} / {review_status}",
    ]
    if score is not None:
        lines.append(f"  - Score: {float(score):.4f}")

    estimated_tokens = topic.get("estimated_tokens")
    if estimated_tokens is not None:
        lines.append(f"  - Estimated tokens: {int(estimated_tokens)}")

    fields = _topic_fields_for_detail_level(detail_level, compact)
    label_map = {
        "aliases": "Aliases",
        "summary": "Summary",
        "historical_context": "Historical context",
        "ancient_near_east_context": "Ancient Near East context",
        "literary_context": "Literary context",
        "covenantal_significance": "Covenantal significance",
        "scripture_references": "Scripture references",
        "common_questions": "Common questions",
        "interpretive_notes": "Interpretive notes",
        "timeline": "Timeline",
        "archaeology": "Archaeology",
        "new_testament_connections": "New Testament connections",
        "related_objects": "Related objects",
        "sources": "Sources",
    }
    for field_name in fields:
        rendered = _render_topic_field(
            label_map[field_name],
            topic.get(field_name),
            detail_level=detail_level,
            seen_facts=seen_facts,
            compact=compact,
        )
        if rendered:
            lines.append(rendered)
    return "\n".join(lines)

def _shrink_prompt(prompt: str, max_context_tokens: int) -> str:
    if _estimate_tokens(prompt) <= max_context_tokens:
        return prompt
    max_chars = max_context_tokens * 4
    trimmed = prompt[:max_chars].rstrip()
    if trimmed and not trimmed.endswith("..."):
        trimmed = trimmed.rstrip() + "\n..."
    return trimmed
