"""Build structured context packages from canonical library retrieval."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

from .loader import CanonicalLibrary
from .normalization import normalize_id, normalize_text, tokenize_query
from .retrieval import RetrievalResult


LEGACY_RELATIONSHIP_TYPES: dict[str, str] = {
    "related_people": "associated-person",
    "related_places": "associated-place",
    "related_events": "associated-event",
}

CKL_MAX_CONTEXT_TOKENS = 3000
CKL_MAX_ENTRIES = 8
CKL_MAX_FACTS_PER_ENTRY = 5
CKL_MAX_SCRIPTURE_REFERENCES_PER_ENTRY = 6
CKL_MAX_CAUTIONS_PER_ENTRY = 3

_PROMPT_FACT_FIELD_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("covenantal_significance", 120),
    ("historical_context", 110),
    ("literary_context", 100),
    ("ancient_near_east_context", 95),
    ("timeline", 85),
    ("archaeology", 80),
    ("new_testament_connections", 75),
)

_PROMPT_CAUTION_FIELD_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("interpretive_notes", 100),
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_SPLIT_RE = re.compile(r"\s*;\s*")


def _dedupe_extend(target: list[Any], values: list[Any], *, limit: int | None = None) -> None:
    seen = set(target)
    for value in values:
        if not value or value in seen:
            continue
        target.append(value)
        seen.add(value)
        if limit is not None and len(target) >= limit:
            return


def _dedupe_relationships_extend(target: list[dict[str, Any]], values: list[dict[str, Any]]) -> None:
    seen = {(item["id"], item["relationship"]) for item in target}
    for value in values:
        key = (value["id"], value["relationship"])
        if key in seen:
            continue
        target.append(value)
        seen.add(key)


def _relationship_to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
    elif isinstance(value, Mapping):
        candidate = dict(value)
    else:
        raise TypeError(f"unsupported related object type: {type(value).__name__}")

    return {
        "id": normalize_id(str(candidate["id"])),
        "relationship": str(candidate["relationship"]),
        "weight": candidate["weight"],
        "notes": candidate["notes"],
    }


def _estimate_text_tokens(value: Any) -> int:
    if value is None:
        return 0
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0
        return max(1, round(len(text) / 4))
    if isinstance(value, Mapping):
        total = 0
        for key in (
            "id",
            "reference",
            "relationship",
            "notes",
            "title",
            "locator",
            "source_type",
            "author",
            "publisher",
            "url",
        ):
            total += _estimate_text_tokens(value.get(key))
        return total
    if isinstance(value, list):
        return sum(_estimate_text_tokens(item) for item in value)
    text = str(value).strip()
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def _estimate_object_tokens(obj: Any) -> int:
    return sum(
        _estimate_text_tokens(getattr(obj, field_name, None))
        for field_name in (
            "id",
            "title",
            "aliases",
            "summary",
            "historical_context",
            "ancient_near_east_context",
            "literary_context",
            "covenantal_significance",
            "scripture_references",
            "common_questions",
            "interpretive_notes",
            "sources",
            "related_objects",
            "timeline",
            "archaeology",
            "new_testament_connections",
        )
    )


@dataclass
class CanonicalContextBuilder:
    library: CanonicalLibrary
    max_topics: int = 5
    max_cross_references: int = 10
    max_related_topics: int = 10
    max_timeline_entries: int = 10
    max_archaeology_entries: int = 10
    max_expanded_topics: int = 8
    max_relationship_depth: int = 1
    min_relationship_weight: int = 1

    def build(
        self,
        question: str,
        limit: int | None = None,
        *,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
        include_placeholders: bool = True,
        allowed_statuses: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        self.library._ensure_loaded()
        topic_limit = self.max_topics if limit is None else max(0, min(limit, self.max_topics))
        retrieved: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        primary_results = self._retrieve_primary_topics(
            question,
            limit=topic_limit,
            approved_only=approved_only,
            exclude_deprecated=exclude_deprecated,
            exclude_rejected=exclude_rejected,
            include_placeholders=include_placeholders,
            allowed_statuses=allowed_statuses,
        )
        for result in primary_results:
            self._append_topic(
                retrieved,
                result.object,
                inclusion_type="primary",
                seen_ids=seen_ids,
                score=result.score,
                match_type=result.match_type,
                matched_alias=result.matched_alias,
                matched_terms=result.matched_terms,
                matched_fields=result.matched_fields,
            )

        expanded: list[dict[str, Any]] = []
        if self.max_relationship_depth > 0 and self.max_expanded_topics > 0 and retrieved:
            expanded = self._expand_relationships(
                retrieved,
                seen_ids,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            )
            retrieved.extend(expanded)

        context = {
            "question": question,
            "retrieved_topics": retrieved,
            "historical_context": [],
            "ancient_near_east_context": [],
            "literary_context": [],
            "covenantal_significance": [],
            "cross_references": [],
            "word_studies": [],
            "related_topics": [],
            "related_objects": [],
            "timeline": [],
            "archaeology": [],
            "new_testament_connections": [],
            "metadata": {
                "retrieval_method": retrieved[0]["match_type"] if retrieved else "none",
                "framework_version": self.library.manifest.get("framework_version", "1.0"),
                "topic_count": len(retrieved),
                "primary_topic_count": len(primary_results),
                "expanded_topic_count": len(expanded),
                "requested_limit": topic_limit,
                "include_placeholders": include_placeholders,
                "allowed_statuses": list(allowed_statuses) if allowed_statuses is not None else None,
                "estimated_topic_tokens": sum(
                    int(item.get("estimated_tokens") or 0) for item in retrieved
                ),
                "retrieved_object_versions": [
                    {
                        "id": str(item.get("id") or "").strip(),
                        "object_version": str(item.get("object_version") or "").strip(),
                    }
                    for item in retrieved
                    if str(item.get("id") or "").strip()
                ],
            },
        }

        for result in retrieved:
            obj = self.library.objects_by_id[result["id"]]
            _dedupe_extend(context["historical_context"], [obj.historical_context] if obj.historical_context else [])
            _dedupe_extend(
                context["ancient_near_east_context"],
                [obj.ancient_near_east_context] if obj.ancient_near_east_context else [],
            )
            _dedupe_extend(context["literary_context"], [obj.literary_context] if obj.literary_context else [])
            _dedupe_extend(
                context["covenantal_significance"],
                [obj.covenantal_significance] if obj.covenantal_significance else [],
            )
            _dedupe_extend(context["cross_references"], obj.cross_references, limit=self.max_cross_references)
            _dedupe_extend(context["word_studies"], obj.hebrew_words + obj.greek_words)
            relationships = result["related_objects"]
            _dedupe_relationships_extend(context["related_objects"], relationships)
            _dedupe_extend(
                context["related_topics"],
                [relationship["id"] for relationship in relationships],
                limit=self.max_related_topics,
            )
            _dedupe_extend(context["timeline"], obj.timeline, limit=self.max_timeline_entries)
            _dedupe_extend(context["archaeology"], obj.archaeology, limit=self.max_archaeology_entries)
            _dedupe_extend(context["new_testament_connections"], obj.new_testament_connections)

        return context

    def _retrieve_primary_topics(
        self,
        question: str,
        *,
        limit: int,
        approved_only: bool,
        exclude_deprecated: bool,
        exclude_rejected: bool,
        include_placeholders: bool,
        allowed_statuses: tuple[str, ...] | None,
    ) -> list[RetrievalResult]:
        primary_results: list[RetrievalResult] = []
        if limit <= 0:
            return primary_results

        primary = self.library.retrieve_exact(
            question,
            approved_only=approved_only,
            exclude_deprecated=exclude_deprecated,
            exclude_rejected=exclude_rejected,
            include_placeholders=include_placeholders,
            allowed_statuses=allowed_statuses,
        )
        if primary is not None:
            primary_results.append(primary)

        if len(primary_results) < limit:
            for result in self.library.retrieve_hybrid(
                question,
                limit=limit,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            ):
                if result.object.id in {item.object.id for item in primary_results}:
                    continue
                primary_results.append(result)
                if len(primary_results) >= limit:
                    break

        return primary_results

    def _append_topic(
        self,
        target: list[dict[str, Any]],
        obj: Any,
        *,
        inclusion_type: str,
        seen_ids: set[str],
        score: float,
        match_type: str,
        matched_alias: str | None = None,
        matched_terms: list[str] | None = None,
        matched_fields: list[str] | None = None,
        included_from: str | None = None,
        relationship: str | None = None,
        relationship_weight: int | None = None,
        relationship_depth: int = 0,
    ) -> None:
        if obj.id in seen_ids:
            return
        target.append(
            {
                "id": obj.id,
                "type": obj.type,
                "title": obj.title,
                "aliases": list(obj.aliases),
                "summary": obj.summary,
                "historical_context": obj.historical_context,
                "ancient_near_east_context": obj.ancient_near_east_context,
                "literary_context": obj.literary_context,
                "covenantal_significance": obj.covenantal_significance,
                "scripture_references": [
                    reference.to_dict() if hasattr(reference, "to_dict") else reference
                    for reference in obj.scripture_references
                ],
                "common_questions": list(obj.common_questions),
                "interpretive_notes": list(obj.interpretive_notes),
                "sources": [
                    source.to_dict() if hasattr(source, "to_dict") else source
                    for source in obj.sources
                ],
                "content_status": obj.content_status,
                "review_status": obj.review_status,
                "confidence": obj.confidence,
                "importance": obj.importance,
                "object_version": obj.object_version,
                "matched_alias": matched_alias,
                "match_type": match_type,
                "score": score,
                "matched_terms": matched_terms or [],
                "matched_fields": matched_fields or [],
                "related_objects": self._normalize_related_objects(obj),
                "inclusion_type": inclusion_type,
                "included_from": included_from,
                "relationship": relationship,
                "relationship_weight": relationship_weight,
                "relationship_depth": relationship_depth,
                "estimated_tokens": _estimate_object_tokens(obj),
            }
        )
        seen_ids.add(obj.id)

    def _expand_relationships(
        self,
        seed_entries: list[dict[str, Any]],
        seen_ids: set[str],
        *,
        approved_only: bool,
        exclude_deprecated: bool,
        exclude_rejected: bool,
        include_placeholders: bool,
        allowed_statuses: tuple[str, ...] | None,
        token_budget: int | None = None,
    ) -> list[dict[str, Any]]:
        expanded: list[dict[str, Any]] = []
        current_frontier = list(seed_entries)
        current_depth = 0
        remaining_tokens = None if token_budget is None else max(0, int(token_budget))

        while (
            current_frontier
            and current_depth < max(self.max_relationship_depth, 0)
            and len(expanded) < self.max_expanded_topics
        ):
            candidates: list[tuple[int, int, str, str, str, str, int]] = []
            for source_index, source_entry in enumerate(current_frontier):
                source_obj = self.library.objects_by_id.get(source_entry["id"])
                if source_obj is None:
                    continue
                for rel_index, relationship in enumerate(self._ordered_relationships_for_expansion(source_obj)):
                    target_id = relationship["id"]
                    if target_id in seen_ids:
                        continue
                    if int(relationship["weight"]) < self.min_relationship_weight:
                        continue
                    target_obj = self.library.objects_by_id.get(target_id)
                    if target_obj is None:
                        continue
                    if not self.library._is_retrievable(
                        target_obj,
                        approved_only=approved_only,
                        exclude_deprecated=exclude_deprecated,
                        exclude_rejected=exclude_rejected,
                        include_placeholders=include_placeholders,
                        allowed_statuses=allowed_statuses,
                    ):
                        continue
                    candidates.append(
                        (
                            -int(relationship["weight"]),
                            source_index,
                            rel_index,
                            target_id,
                            str(relationship["relationship"]),
                            str(relationship["notes"]),
                            int(relationship["weight"]),
                        )
                    )

            if not candidates:
                break

            candidates.sort()
            next_frontier: list[dict[str, Any]] = []
            for _, source_index, _, target_id, relationship_name, _notes, relationship_weight in candidates:
                if len(expanded) >= self.max_expanded_topics or target_id in seen_ids:
                    continue
                source_entry = current_frontier[source_index]
                target_obj = self.library.objects_by_id[target_id]
                estimated_tokens = _estimate_object_tokens(target_obj)
                if remaining_tokens is not None and estimated_tokens > remaining_tokens and expanded:
                    continue
                self._append_topic(
                    expanded,
                    target_obj,
                    inclusion_type="relationship",
                    seen_ids=seen_ids,
                    score=0.0,
                    match_type="relationship",
                    included_from=source_entry["id"],
                    relationship=relationship_name,
                    relationship_weight=relationship_weight,
                    relationship_depth=current_depth + 1,
                )
                next_frontier.append(expanded[-1])
                if remaining_tokens is not None:
                    remaining_tokens = max(0, remaining_tokens - estimated_tokens)

            current_frontier = next_frontier
            current_depth += 1

        return expanded

    def _ordered_relationships_for_expansion(self, obj: Any) -> list[dict[str, Any]]:
        relationships = self._normalize_related_objects(obj)
        return sorted(
            relationships,
            key=lambda relationship: (
                -int(relationship["weight"]),
                relationship["relationship"],
                relationship["id"],
                relationship["notes"],
            ),
        )

    def _normalize_related_objects(self, obj: Any) -> list[dict[str, Any]]:
        relationships: list[dict[str, Any]] = []
        for value in getattr(obj, "related_objects", []):
            relationships.append(_relationship_to_dict(value))
        for field_name, relationship_type in LEGACY_RELATIONSHIP_TYPES.items():
            for related_id in getattr(obj, field_name, []):
                relationships.append(
                    {
                        "id": normalize_id(str(related_id)),
                        "relationship": relationship_type,
                        "weight": 1,
                        "notes": "",
                    }
                )

        deduped: list[dict[str, Any]] = []
        _dedupe_relationships_extend(deduped, relationships)
        return deduped


def build_canonical_prompt_context(
    context: Mapping[str, Any] | None,
    *,
    max_context_tokens: int = CKL_MAX_CONTEXT_TOKENS,
    max_entries: int = CKL_MAX_ENTRIES,
    max_facts_per_entry: int = CKL_MAX_FACTS_PER_ENTRY,
    max_scripture_references_per_entry: int = CKL_MAX_SCRIPTURE_REFERENCES_PER_ENTRY,
    max_caution_notes_per_entry: int = CKL_MAX_CAUTIONS_PER_ENTRY,
) -> dict[str, Any]:
    """Project rich CKL retrieval output into a compact prompt-safe structure."""

    token_budget = max(0, int(max_context_tokens))
    entry_limit = max(0, int(max_entries))
    fact_limit = max(0, int(max_facts_per_entry))
    reference_limit = max(0, int(max_scripture_references_per_entry))
    caution_limit = max(0, int(max_caution_notes_per_entry))

    retrieved_topics = list(context.get("retrieved_topics") or []) if context else []
    if not retrieved_topics or token_budget <= 0 or entry_limit <= 0:
        return {
            "entries": [],
            "metadata": {
                "token_budget": token_budget,
                "max_entries": entry_limit,
                "max_facts_per_entry": fact_limit,
                "max_scripture_references_per_entry": reference_limit,
                "max_caution_notes_per_entry": caution_limit,
                "entry_count": 0,
                "fact_count": 0,
                "scripture_reference_count": 0,
                "caution_note_count": 0,
                "estimated_tokens": 0,
                "remaining_tokens": token_budget,
                "truncated": False,
                "selected_entry_ids": [],
            },
        }

    query_source = str((context or {}).get("query") or (context or {}).get("question") or "").strip()
    query_terms = tuple(dict.fromkeys(tokenize_query(query_source))) if query_source else ()

    prompt_entries: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    seen_references: set[str] = set()
    remaining_tokens = token_budget
    truncated = False

    for topic in retrieved_topics[:entry_limit]:
        entry, entry_tokens, entry_truncated = _build_prompt_context_entry(
            topic,
            query_terms=query_terms,
            remaining_tokens=remaining_tokens,
            max_facts_per_entry=fact_limit,
            max_scripture_references_per_entry=reference_limit,
            max_caution_notes_per_entry=caution_limit,
            seen_texts=seen_texts,
            seen_references=seen_references,
        )
        if entry is None:
            continue
        if entry_tokens > remaining_tokens and prompt_entries:
            truncated = True
            break

        prompt_entries.append(entry)
        remaining_tokens = max(0, remaining_tokens - entry_tokens)
        truncated = truncated or entry_truncated

        for text in (entry.get("summary"), *entry.get("facts", []), *entry.get("caution_notes", [])):
            key = normalize_text(str(text or "").strip())
            if key:
                seen_texts.add(key)
        for reference in entry.get("scripture_references", []):
            key = normalize_text(str(reference or "").strip())
            if key:
                seen_references.add(key)

        if remaining_tokens <= 0:
            if len(prompt_entries) < len(retrieved_topics):
                truncated = True
            break

    metadata = {
        "token_budget": token_budget,
        "max_entries": entry_limit,
        "max_facts_per_entry": fact_limit,
        "max_scripture_references_per_entry": reference_limit,
        "max_caution_notes_per_entry": caution_limit,
        "entry_count": len(prompt_entries),
        "fact_count": sum(len(entry.get("facts") or []) for entry in prompt_entries),
        "scripture_reference_count": sum(len(entry.get("scripture_references") or []) for entry in prompt_entries),
        "caution_note_count": sum(len(entry.get("caution_notes") or []) for entry in prompt_entries),
        "estimated_tokens": sum(_estimate_prompt_context_entry_tokens(entry) for entry in prompt_entries),
        "remaining_tokens": remaining_tokens,
        "truncated": truncated or len(prompt_entries) < len(retrieved_topics),
        "selected_entry_ids": [str(entry.get("id") or "").strip() for entry in prompt_entries if str(entry.get("id") or "").strip()],
        "selected_entry_versions": [
            {
                "id": str(entry.get("id") or "").strip(),
                "object_version": str(entry.get("object_version") or "").strip(),
            }
            for entry in prompt_entries
            if str(entry.get("id") or "").strip()
        ],
    }
    return {"entries": prompt_entries, "metadata": metadata}


def _build_prompt_context_entry(
    topic: Mapping[str, Any],
    *,
    query_terms: Sequence[str],
    remaining_tokens: int,
    max_facts_per_entry: int,
    max_scripture_references_per_entry: int,
    max_caution_notes_per_entry: int,
    seen_texts: set[str],
    seen_references: set[str],
) -> tuple[dict[str, Any] | None, int, bool]:
    object_id = normalize_id(str(topic.get("id") or "").strip())
    if not object_id or remaining_tokens <= 0:
        return None, 0, False

    title = _normalize_prompt_text(topic.get("title") or object_id) or object_id
    category = _humanize_prompt_category(topic.get("type"))

    local_seen_texts = set(seen_texts)
    local_seen_references = set(seen_references)

    summary = _first_prompt_sentence(topic.get("summary"))
    summary = _trim_prompt_text(summary, min(remaining_tokens, 64))
    summary_key = normalize_text(summary)
    if summary_key:
        local_seen_texts.add(summary_key)

    fact_candidates = _collect_ranked_prompt_texts(
        topic,
        field_weights=_PROMPT_FACT_FIELD_WEIGHTS,
        query_terms=query_terms,
        seen_keys=local_seen_texts,
    )
    if not summary and fact_candidates:
        summary_candidate = fact_candidates.pop(0)
        summary = _trim_prompt_text(summary_candidate["text"], min(remaining_tokens, 64))
        summary_key = normalize_text(summary)
        if summary_key:
            local_seen_texts.add(summary_key)

    selected_facts = _select_ranked_prompt_texts(
        fact_candidates,
        limit=max_facts_per_entry,
        seen_keys=local_seen_texts,
    )

    reference_candidates = _collect_ranked_scripture_references(
        topic,
        query_terms=query_terms,
        seen_keys=local_seen_references,
    )
    selected_references = _select_ranked_prompt_texts(
        reference_candidates,
        limit=max_scripture_references_per_entry,
        seen_keys=local_seen_references,
    )

    caution_candidates = _collect_ranked_prompt_texts(
        topic,
        field_weights=_PROMPT_CAUTION_FIELD_WEIGHTS,
        query_terms=query_terms,
        seen_keys=local_seen_texts,
    )
    selected_cautions = _select_ranked_prompt_texts(
        caution_candidates,
        limit=max_caution_notes_per_entry,
        seen_keys=local_seen_texts,
    )

    if not selected_cautions:
        content_status = str(topic.get("content_status") or "").strip().lower()
        review_status = str(topic.get("review_status") or "").strip().lower()
        if content_status and content_status not in {"complete", "approved"}:
            selected_cautions.append(
                "Treat this entry as provisional and confirm the cited passages before drawing a final conclusion."
            )
        elif review_status and review_status not in {"reviewed", "approved"}:
            selected_cautions.append(
                "Treat this entry carefully and confirm the cited passages before drawing a final conclusion."
            )
        if selected_cautions:
            local_seen_texts.add(normalize_text(selected_cautions[0]))

    entry: dict[str, Any] = {
        "id": object_id,
        "title": title,
        "category": category,
        "object_version": str(topic.get("object_version") or "").strip(),
        "summary": summary,
        "facts": selected_facts,
        "scripture_references": selected_references,
        "caution_notes": selected_cautions,
        "source_ids": [object_id],
    }

    entry_tokens = _estimate_prompt_context_entry_tokens(entry)
    truncated = False
    entry, entry_tokens, trimmed = _shrink_prompt_context_entry(entry, remaining_tokens)
    truncated = truncated or trimmed

    if entry_tokens <= 0:
        return None, 0, truncated

    return entry, entry_tokens, truncated


def _collect_ranked_prompt_texts(
    topic: Mapping[str, Any],
    *,
    field_weights: tuple[tuple[str, int], ...],
    query_terms: Sequence[str],
    seen_keys: set[str],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for field_order, (field_name, base_weight) in enumerate(field_weights):
        for value_index, text in enumerate(_iter_prompt_text_segments(topic.get(field_name))):
            normalized = normalize_text(text)
            if not normalized or normalized in seen_keys:
                continue
            score = base_weight + _prompt_query_bonus(normalized, query_terms)
            candidates.append(
                {
                    "score": score,
                    "field_order": field_order,
                    "value_index": value_index,
                    "text": text,
                    "key": normalized,
                }
            )
    candidates.sort(key=lambda item: (-int(item["score"]), int(item["field_order"]), int(item["value_index"]), str(item["text"])))
    return candidates


def _collect_ranked_scripture_references(
    topic: Mapping[str, Any],
    *,
    query_terms: Sequence[str],
    seen_keys: set[str],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for value_index, value in enumerate(topic.get("scripture_references") or []):
        reference = ""
        notes = ""
        if isinstance(value, Mapping):
            reference = _normalize_prompt_text(value.get("reference"))
            notes = _normalize_prompt_text(value.get("notes"))
        else:
            reference = _normalize_prompt_text(value)
        if not reference:
            continue
        normalized = normalize_text(reference)
        if not normalized or normalized in seen_keys:
            continue
        rendered = reference if not notes else f"{reference} - {notes}"
        score = 100 + _prompt_query_bonus(reference, query_terms) + _prompt_query_bonus(notes, query_terms)
        candidates.append(
            {
                "score": score,
                "field_order": value_index,
                "value_index": value_index,
                "text": rendered,
                "key": normalized,
            }
        )
    candidates.sort(key=lambda item: (-int(item["score"]), int(item["field_order"]), int(item["value_index"]), str(item["text"])))
    return candidates


def _select_ranked_prompt_texts(
    candidates: list[dict[str, Any]],
    *,
    limit: int,
    seen_keys: set[str],
) -> list[str]:
    if limit <= 0:
        return []
    selected: list[str] = []
    for candidate in candidates:
        if len(selected) >= limit:
            break
        key = str(candidate.get("key") or "").strip()
        if not key or key in seen_keys:
            continue
        text = _normalize_prompt_text(candidate.get("text"))
        if not text:
            continue
        selected.append(text)
        seen_keys.add(key)
    return selected


def _normalize_prompt_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _prompt_query_bonus(text: str, query_terms: Sequence[str]) -> int:
    normalized = normalize_text(text)
    if not normalized or not query_terms:
        return 0
    matches = 0
    for term in dict.fromkeys(query_terms):
        term_text = normalize_text(str(term or "").strip())
        if term_text and term_text in normalized:
            matches += 1
    return matches * 20


def _iter_prompt_text_segments(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return _split_prompt_text_segments(value)
    if isinstance(value, Mapping):
        pieces: list[str] = []
        for nested_value in value.values():
            pieces.extend(_iter_prompt_text_segments(nested_value))
        return pieces
    if isinstance(value, (list, tuple)):
        pieces: list[str] = []
        for item in value:
            pieces.extend(_iter_prompt_text_segments(item))
        return pieces
    text = _normalize_prompt_text(value)
    return [text] if text else []


def _split_prompt_text_segments(text: str) -> list[str]:
    normalized = _normalize_prompt_text(text)
    if not normalized:
        return []
    segments: list[str] = []
    for sentence in _SENTENCE_SPLIT_RE.split(normalized):
        sentence = _normalize_prompt_text(sentence)
        if not sentence:
            continue
        for clause in _CLAUSE_SPLIT_RE.split(sentence):
            clause = _normalize_prompt_text(clause)
            if clause:
                segments.append(clause)
    return segments or [normalized]


def _first_prompt_sentence(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        segments = _split_prompt_text_segments(value)
        return segments[0] if segments else _normalize_prompt_text(value)
    if isinstance(value, Mapping):
        for nested_value in value.values():
            sentence = _first_prompt_sentence(nested_value)
            if sentence:
                return sentence
        return ""
    if isinstance(value, (list, tuple)):
        for item in value:
            sentence = _first_prompt_sentence(item)
            if sentence:
                return sentence
        return ""
    return _normalize_prompt_text(value)


def _trim_prompt_text(value: str, max_tokens: int) -> str:
    text = _normalize_prompt_text(value)
    if not text:
        return ""
    if max_tokens <= 0 or _estimate_text_tokens(text) <= max_tokens:
        return text
    max_chars = max(16, int(max_tokens) * 4)
    trimmed = text[:max_chars].rstrip()
    if not trimmed:
        return text[:max(1, max_chars)].strip()
    if len(trimmed) < len(text):
        trimmed = trimmed.rstrip(" ,;:.-") + "..."
    return trimmed


def _humanize_prompt_category(value: Any) -> str:
    text = _normalize_prompt_text(value)
    if not text:
        return "Unknown"
    return text.replace("_", " ").title()


def _estimate_prompt_context_entry_tokens(entry: Mapping[str, Any]) -> int:
    lines = [
        f"## Entry: {str(entry.get('title') or entry.get('id') or 'unknown').strip()}",
        f"Category: {_normalize_prompt_text(entry.get('category')) or 'Unknown'}",
    ]
    summary = _normalize_prompt_text(entry.get("summary"))
    if summary:
        lines.append(f"Summary: {summary}")
    facts = [str(item).strip() for item in entry.get("facts") or [] if str(item).strip()]
    if facts:
        lines.append("Relevant facts:")
        lines.extend(f"- {fact}" for fact in facts)
    scripture_references = [str(item).strip() for item in entry.get("scripture_references") or [] if str(item).strip()]
    if scripture_references:
        lines.append("Scripture references:")
        lines.extend(f"- {reference}" for reference in scripture_references)
    caution_notes = [str(item).strip() for item in entry.get("caution_notes") or [] if str(item).strip()]
    if caution_notes:
        lines.append("Caution / interpretation notes:")
        lines.extend(f"- {note}" for note in caution_notes)
    source_ids = [str(item).strip() for item in entry.get("source_ids") or [] if str(item).strip()]
    if source_ids:
        lines.append(f"Source ID: {source_ids[0]}")
    return _estimate_text_tokens("\n".join(lines))


def _shrink_prompt_context_entry(
    entry: dict[str, Any],
    max_tokens: int,
) -> tuple[dict[str, Any], int, bool]:
    truncated = False
    budget = max(0, int(max_tokens))
    if budget <= 0:
        return entry, 0, False

    entry = dict(entry)
    entry["facts"] = list(entry.get("facts") or [])
    entry["scripture_references"] = list(entry.get("scripture_references") or [])
    entry["caution_notes"] = list(entry.get("caution_notes") or [])
    entry["source_ids"] = list(entry.get("source_ids") or [])
    entry["summary"] = _normalize_prompt_text(entry.get("summary"))

    def entry_tokens() -> int:
        return _estimate_prompt_context_entry_tokens(entry)

    while entry_tokens() > budget and entry["caution_notes"]:
        entry["caution_notes"].pop()
        truncated = True
    while entry_tokens() > budget and entry["scripture_references"]:
        entry["scripture_references"].pop()
        truncated = True
    while entry_tokens() > budget and entry["facts"]:
        entry["facts"].pop()
        truncated = True

    if entry["summary"]:
        while entry_tokens() > budget:
            shorter = _trim_prompt_text(entry["summary"], max(4, budget // 2))
            if not shorter or shorter == entry["summary"]:
                break
            entry["summary"] = shorter
            truncated = True
    if entry["summary"] and entry_tokens() > budget:
        entry["summary"] = ""
        truncated = True

    tokens = entry_tokens()
    if tokens > budget:
        minimal_entry = {
            "id": entry.get("id"),
            "title": entry.get("title"),
            "category": entry.get("category"),
            "summary": "",
            "facts": [],
            "scripture_references": [],
            "caution_notes": [],
            "source_ids": list(entry.get("source_ids") or []),
        }
        minimal_tokens = _estimate_prompt_context_entry_tokens(minimal_entry)
        if minimal_tokens <= budget:
            return minimal_entry, minimal_tokens, True
        return entry, tokens, truncated

    return entry, tokens, truncated
