"""Build structured context packages from canonical library retrieval."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

from .loader import CanonicalLibrary
from .normalization import normalize_id, normalize_text, tokenize_query
from .query_analysis import (
    MULTIPLE_ENTITIES,
    SCRIPTURE,
    SINGLE_ENTITY,
    AmbiguousEntityResolution,
    QueryAnalysis,
    analyze_query as analyze_canonical_query,
)
from .retrieval import RetrievalResult
from .schema import interpretive_note_texts


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
    ("hebraic_worldview", 98),
    ("second_temple_context", 96),
    ("canonical_context", 94),
    ("later_christian_reception", 72),
    ("authorship_positions", 90),
    ("date_ranges", 88),
    ("original_audience", 92),
    ("historical_setting", 94),
    ("genre", 86),
    ("structure", 84),
    ("major_themes", 96),
    ("canonical_placement", 82),
    ("key_people", 88),
    ("key_places", 88),
    ("key_events", 88),
    ("primary_sources", 90),
    ("timeline", 85),
    ("archaeology", 80),
    ("new_testament_connections", 75),
)

_PROMPT_CAUTION_FIELD_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("interpretive_notes", 100),
    ("interpretive_disputes", 95),
)

_CONTEXT_FIELD_APPLICABILITY_KEYS: tuple[tuple[str, str], ...] = (
    ("historical_context", "historical"),
    ("ancient_near_east_context", "ancient_near_east"),
    ("hebraic_worldview", "hebraic_worldview"),
    ("second_temple_context", "second_temple"),
    ("canonical_context", "canonical"),
    ("later_christian_reception", "later_christian_reception"),
)

_CONTEXT_APPLICABILITY_DEFAULTS: dict[str, bool] = {
    applicability_key: True for _, applicability_key in _CONTEXT_FIELD_APPLICABILITY_KEYS
}

_CONTEXT_FIELD_APPLICABILITY_LOOKUP: dict[str, str] = {
    field_name: applicability_key for field_name, applicability_key in _CONTEXT_FIELD_APPLICABILITY_KEYS
}

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


def _context_applicability_for(obj: Any) -> dict[str, bool]:
    raw_value = getattr(obj, "context_applicability", None)
    applicability = dict(_CONTEXT_APPLICABILITY_DEFAULTS)
    if isinstance(raw_value, Mapping):
        for _, applicability_key in _CONTEXT_FIELD_APPLICABILITY_KEYS:
            value = raw_value.get(applicability_key)
            if isinstance(value, bool):
                applicability[applicability_key] = value
    return applicability


def _context_field_value(obj: Any, field_name: str, applicability: Mapping[str, bool]) -> str:
    applicability_key = _CONTEXT_FIELD_APPLICABILITY_LOOKUP.get(field_name)
    if applicability_key is not None and not applicability.get(applicability_key, True):
        return ""
    value = getattr(obj, field_name, "")
    text = str(value or "").strip()
    return text


def _topic_applicability_for(topic: Mapping[str, Any]) -> dict[str, bool]:
    raw_value = topic.get("context_applicability")
    applicability = dict(_CONTEXT_APPLICABILITY_DEFAULTS)
    if isinstance(raw_value, Mapping):
        for _, applicability_key in _CONTEXT_FIELD_APPLICABILITY_KEYS:
            value = raw_value.get(applicability_key)
            if isinstance(value, bool):
                applicability[applicability_key] = value
    return applicability


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
            "year",
            "url",
            "supports",
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
    applicability = _context_applicability_for(obj)
    context_field_names = frozenset(_CONTEXT_FIELD_APPLICABILITY_LOOKUP)
    total = 0
    for field_name in (
        "id",
        "title",
        "aliases",
        "summary",
        "authorship_positions",
        "date_ranges",
        "original_audience",
        "historical_setting",
        "genre",
        "structure",
        "major_themes",
        "canonical_placement",
        "key_people",
        "key_places",
        "key_events",
        "interpretive_disputes",
        "primary_sources",
        "cross_references",
        "intertextuality",
        "historical_context",
        "ancient_near_east_context",
        "hebraic_worldview",
        "second_temple_context",
        "canonical_context",
        "later_christian_reception",
        "literary_context",
        "covenantal_significance",
        "scripture_references",
        "common_questions",
        "interpretive_notes",
        "sources",
        "related_objects",
        "hebrew_words",
        "greek_words",
        "timeline",
        "archaeology",
        "new_testament_connections",
    ):
        if field_name == "interpretive_notes":
            total += _estimate_text_tokens(" ".join(interpretive_note_texts(getattr(obj, field_name, None))))
            continue
        if not _context_field_value(obj, field_name, applicability) and field_name in context_field_names:
            continue
        total += _estimate_text_tokens(getattr(obj, field_name, None))
    return total


def _prioritize_query_scripture_references(
    retrieved: list[dict[str, Any]],
    analysis: QueryAnalysis,
) -> None:
    if not analysis.scripture_references:
        return
    prefixes = {
        normalize_text(
            f"{reference.book} {reference.start_chapter}"
            + (f" {reference.start_verse}" if reference.start_verse is not None else "")
        )
        for reference in analysis.scripture_references
        if reference.start_chapter is not None
    }
    if not prefixes:
        return
    for topic in retrieved:
        references = topic.get("scripture_references")
        if not isinstance(references, list):
            continue
        topic["scripture_references"] = sorted(
            references,
            key=lambda reference: (
                0 if _reference_matches_prefix(reference, prefixes) else 1,
                str(reference.get("reference") if isinstance(reference, Mapping) else reference),
            ),
        )


def _reference_matches_prefix(reference: Any, prefixes: set[str]) -> bool:
    if isinstance(reference, Mapping):
        text = str(reference.get("reference") or "")
    else:
        text = str(reference or "")
    normalized = normalize_text(text)
    return any(normalized.startswith(prefix) for prefix in prefixes)


@dataclass
class CanonicalContextBuilder:
    library: CanonicalLibrary
    max_topics: int = 5
    max_cross_references: int = 10
    max_related_topics: int = 10
    max_timeline_entries: int = 10
    max_archaeology_entries: int = 10
    max_expanded_topics: int = 0
    max_relationship_depth: int = 0
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
        analysis = analyze_canonical_query(
            question,
            book_alias_lookup=self.library._book_alias_lookup,
        )
        retrieval_trace: dict[str, Any] = {
            "method": "none",
            "primary_count": 0,
            "expanded_count": 0,
            "fallback_used": False,
            "threshold_applied": False,
        }
        ambiguity: AmbiguousEntityResolution | None = None

        primary_results = self._retrieve_primary_topics(
            question,
            analysis=analysis,
            trace=retrieval_trace,
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
                ranking_score=result.ranking_score,
                retrieval_confidence=result.confidence,
            )

        expanded: list[dict[str, Any]] = []
        ambiguity = retrieval_trace.pop("ambiguity", None)
        if (
            analysis.include_related
            and self.max_relationship_depth > 0
            and self.max_expanded_topics > 0
            and retrieved
        ):
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
        _prioritize_query_scripture_references(retrieved, analysis)
        retrieval_trace["primary_count"] = len(primary_results)
        retrieval_trace["expanded_count"] = len(expanded)

        context = {
            "question": question,
            "retrieved_topics": retrieved,
            "historical_context": [],
            "ancient_near_east_context": [],
            "hebraic_worldview": [],
            "second_temple_context": [],
            "canonical_context": [],
            "later_christian_reception": [],
            "literary_context": [],
            "covenantal_significance": [],
            "cross_references": [],
            "intertextuality": [],
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
                "query_analysis": analysis.to_dict(),
                "retrieval": retrieval_trace,
                "ambiguity": ambiguity.to_dict() if ambiguity is not None else None,
            },
        }

        for result in retrieved:
            obj = self.library.objects_by_id[result["id"]]
            applicability = _context_applicability_for(obj)
            for field_name, _applicability_key in _CONTEXT_FIELD_APPLICABILITY_KEYS:
                value = _context_field_value(obj, field_name, applicability)
                if value:
                    _dedupe_extend(context[field_name], [value])
            _dedupe_extend(context["literary_context"], [obj.literary_context] if obj.literary_context else [])
            _dedupe_extend(
                context["covenantal_significance"],
                [obj.covenantal_significance] if obj.covenantal_significance else [],
            )
            _dedupe_extend(context["cross_references"], obj.cross_references, limit=self.max_cross_references)
            _dedupe_extend(context["intertextuality"], obj.intertextuality, limit=self.max_related_topics)
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
        analysis: QueryAnalysis,
        trace: dict[str, Any],
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

        if analysis.scope in {SINGLE_ENTITY, SCRIPTURE} and analysis.entity_candidates:
            resolved = self.library.resolve_entity_with_status(
                analysis.entity_candidates,
                analysis.preferred_categories,
                category_confidence=analysis.category_confidence,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            )
            if isinstance(resolved, RetrievalResult):
                trace["method"] = "exact_entity"
                primary_results.append(resolved)
                if resolved.match_type in {"id", "title", "alias"}:
                    return primary_results
            elif isinstance(resolved, AmbiguousEntityResolution):
                trace["method"] = "ambiguous_entity"
                trace["ambiguity"] = resolved
                return primary_results

        if analysis.scope == MULTIPLE_ENTITIES and analysis.entity_candidates:
            trace["method"] = "exact_entities"
            seen: set[str] = set()
            for candidate in analysis.entity_candidates:
                resolved = self.library.resolve_entity_with_status(
                    (candidate,),
                    analysis.preferred_categories,
                    category_confidence=analysis.category_confidence,
                    approved_only=approved_only,
                    exclude_deprecated=exclude_deprecated,
                    exclude_rejected=exclude_rejected,
                    include_placeholders=include_placeholders,
                    allowed_statuses=allowed_statuses,
                )
                if isinstance(resolved, AmbiguousEntityResolution):
                    trace["ambiguity"] = resolved
                    continue
                if not isinstance(resolved, RetrievalResult) or resolved.object.id in seen:
                    continue
                primary_results.append(resolved)
                seen.add(resolved.object.id)
                if len(primary_results) >= limit:
                    break
            if primary_results:
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
            trace["method"] = "exact_entity"
            primary_results.append(primary)
            return primary_results

        if len(primary_results) < limit:
            trace["method"] = "ranked" if not primary_results else "exact_plus_ranked"
            trace["fallback_used"] = bool(primary_results)
            trace["threshold_applied"] = True
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
        ranking_score: float | None = None,
        retrieval_confidence: float | None = None,
        included_from: str | None = None,
        relationship: str | None = None,
        relationship_weight: int | None = None,
        relationship_depth: int = 0,
    ) -> None:
        if obj.id in seen_ids:
            return
        applicability = _context_applicability_for(obj)
        target.append(
            {
                "id": obj.id,
                "type": obj.type,
                "title": obj.title,
                "aliases": list(obj.aliases),
                "summary": obj.summary,
                "authorship_positions": list(obj.authorship_positions),
                "date_ranges": list(obj.date_ranges),
                "original_audience": obj.original_audience,
                "historical_setting": obj.historical_setting,
                "genre": list(obj.genre),
                "structure": list(obj.structure),
                "major_themes": list(obj.major_themes),
                "canonical_placement": obj.canonical_placement,
                "key_people": list(obj.key_people),
                "key_places": list(obj.key_places),
                "key_events": list(obj.key_events),
                "interpretive_disputes": list(obj.interpretive_disputes),
                "primary_sources": list(obj.primary_sources),
                "cross_references": list(obj.cross_references),
                "intertextuality": list(obj.intertextuality),
                "historical_context": _context_field_value(obj, "historical_context", applicability),
                "ancient_near_east_context": _context_field_value(
                    obj,
                    "ancient_near_east_context",
                    applicability,
                ),
                "hebraic_worldview": _context_field_value(obj, "hebraic_worldview", applicability),
                "second_temple_context": _context_field_value(obj, "second_temple_context", applicability),
                "canonical_context": _context_field_value(obj, "canonical_context", applicability),
                "later_christian_reception": _context_field_value(
                    obj,
                    "later_christian_reception",
                    applicability,
                ),
                "context_applicability": applicability,
                "literary_context": obj.literary_context,
                "covenantal_significance": obj.covenantal_significance,
                "scripture_references": [
                    reference.to_dict() if hasattr(reference, "to_dict") else reference
                    for reference in obj.scripture_references
                ],
                "common_questions": list(obj.common_questions),
                "interpretive_notes": [
                    note.to_dict() if hasattr(note, "to_dict") else note
                    for note in obj.interpretive_notes
                ],
                "sources": [
                    source.to_dict() if hasattr(source, "to_dict") else source
                    for source in obj.sources
                ],
                "hebrew_words": list(obj.hebrew_words),
                "greek_words": list(obj.greek_words),
                "content_status": obj.content_status,
                "review_status": obj.review_status,
                "confidence": obj.confidence,
                "importance": obj.importance,
                "object_version": obj.object_version,
                "matched_alias": matched_alias,
                "match_type": match_type,
                "score": score,
                "ranking_score": score if ranking_score is None else ranking_score,
                "retrieval_confidence": retrieval_confidence,
                "matched_terms": matched_terms or [],
                "matched_fields": matched_fields or [],
                "related_objects": self._normalize_related_objects(obj),
                "timeline": list(obj.timeline),
                "archaeology": list(obj.archaeology),
                "new_testament_connections": list(obj.new_testament_connections),
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


_PROMPT_CONTEXT_SECTION_ORDER: tuple[str, ...] = (
    "Immediate Literary Context",
    "Historical Context",
    "Ancient Near Eastern Context",
    "Hebraic Worldview",
    "Second Temple Context",
    "Covenant and Canonical Context",
    "Intertextual Connections",
    "New Testament Connections",
)

_CULTURAL_CONTEXT_SECTION_ORDER: tuple[str, ...] = (
    "Relevant Cultural Background",
    "Meaning for the Passage",
)

_PROMPT_CONTEXT_MODE_LIMITS: dict[str, dict[str, int | bool]] = {
    "concise": {
        "context_sections": 2,
        "section_items": 1,
        "scripture_references": 2,
        "caution_notes": 1,
        "sources": 1,
        "later_reception": 0,
    },
    "study": {
        "context_sections": 8,
        "section_items": 1,
        "scripture_references": 2,
        "caution_notes": 1,
        "sources": 1,
        "later_reception": 1,
    },
    "teaching": {
        "context_sections": 8,
        "section_items": 1,
        "scripture_references": 2,
        "caution_notes": 1,
        "sources": 1,
        "later_reception": 1,
    },
    "scholar": {
        "context_sections": 8,
        "section_items": 2,
        "scripture_references": 3,
        "caution_notes": 2,
        "sources": 2,
        "later_reception": 1,
    },
}

_PROMPT_SECTION_FIELD_WEIGHTS: dict[str, tuple[tuple[str, int], ...]] = {
    "Immediate Literary Context": (
        ("literary_context", 110),
        ("genre", 90),
        ("structure", 85),
    ),
    "Historical Context": (
        ("historical_context", 120),
        ("historical_setting", 110),
        ("original_audience", 100),
        ("date_ranges", 90),
    ),
    "Ancient Near Eastern Context": (("ancient_near_east_context", 110),),
    "Hebraic Worldview": (("hebraic_worldview", 110),),
    "Second Temple Context": (("second_temple_context", 110),),
    "Covenant and Canonical Context": (
        ("canonical_context", 125),
        ("covenantal_significance", 120),
        ("canonical_placement", 90),
    ),
    "Intertextual Connections": (
        ("intertextuality", 110),
        ("cross_references", 95),
    ),
    "New Testament Connections": (("new_testament_connections", 110),),
    "Interpretive Disputes and Cautions": (
        ("interpretive_disputes", 115),
        ("interpretive_notes", 110),
        ("common_questions", 85),
    ),
    "Later Christian Reception": (("later_christian_reception", 100),),
}

_CULTURAL_PROMPT_SECTION_FIELD_WEIGHTS: dict[str, tuple[tuple[str, int], ...]] = {
    "Relevant Cultural Background": (
        ("ancient_near_east_context", 120),
        ("hebraic_worldview", 120),
        ("second_temple_context", 115),
        ("archaeology", 105),
        ("summary", 95),
        ("common_questions", 75),
    ),
    "Meaning for the Passage": (
        ("summary", 105),
        ("scripture_references", 95),
        ("common_questions", 80),
    ),
    "Interpretive Disputes and Cautions": (("interpretive_notes", 100),),
    "Later Christian Reception": (),
}


def _normalize_prompt_answer_mode(answer_mode: str | None) -> str:
    mode = str(answer_mode or "study").strip().lower()
    return mode if mode in _PROMPT_CONTEXT_MODE_LIMITS else "study"


def _prompt_context_mode_limits(answer_mode: str | None) -> dict[str, int | bool]:
    return _PROMPT_CONTEXT_MODE_LIMITS[_normalize_prompt_answer_mode(answer_mode)]


def _prompt_section_field_weights(
    answer_mode: str | None,
    scope: str = "general",
) -> dict[str, tuple[tuple[str, int], ...]]:
    normalized = _normalize_prompt_answer_mode(answer_mode)
    if str(scope or "").strip().lower() == "cultural_context":
        return dict(_CULTURAL_PROMPT_SECTION_FIELD_WEIGHTS)
    weights = {section: tuple(fields) for section, fields in _PROMPT_SECTION_FIELD_WEIGHTS.items()}
    if normalized == "scholar":
        weights["Historical Context"] = weights["Historical Context"] + (
            ("timeline", 88),
            ("archaeology", 84),
        )
        weights["Interpretive Disputes and Cautions"] = weights["Interpretive Disputes and Cautions"] + (
            ("hebrew_words", 80),
            ("greek_words", 80),
        )
    return weights


def _select_prompt_sources(values: Any, *, limit: int, seen_keys: set[str]) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    if not isinstance(values, (list, tuple)):
        values = [values]

    selected: list[dict[str, Any]] = []
    for value in values:
        if hasattr(value, "to_dict"):
            candidate = value.to_dict()
        elif isinstance(value, Mapping):
            candidate = dict(value)
        else:
            candidate = {"title": str(value or "").strip()}

        key_parts = [
            str(candidate.get("id") or "").strip(),
            str(candidate.get("title") or "").strip(),
            str(candidate.get("locator") or "").strip(),
            str(candidate.get("author") or "").strip(),
            str(candidate.get("publisher") or "").strip(),
            str(candidate.get("year") or "").strip(),
            str(candidate.get("source_type") or "").strip(),
        ]
        key = normalize_text(" ".join(part for part in key_parts if part))
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        selected.append(candidate)
        if limit > 0 and len(selected) >= limit:
            break
    return selected


def build_canonical_prompt_context(
    context: Mapping[str, Any] | None,
    *,
    max_context_tokens: int = CKL_MAX_CONTEXT_TOKENS,
    max_entries: int = CKL_MAX_ENTRIES,
    max_facts_per_entry: int = CKL_MAX_FACTS_PER_ENTRY,
    max_scripture_references_per_entry: int = CKL_MAX_SCRIPTURE_REFERENCES_PER_ENTRY,
    max_caution_notes_per_entry: int = CKL_MAX_CAUTIONS_PER_ENTRY,
    answer_mode: str = "study",
    scope: str = "general",
) -> dict[str, Any]:
    """Project rich CKL retrieval output into a compact prompt-safe structure."""

    token_budget = max(0, int(max_context_tokens))
    entry_limit = max(0, int(max_entries))
    fact_limit = max(0, int(max_facts_per_entry))
    reference_limit = max(0, int(max_scripture_references_per_entry))
    caution_limit = max(0, int(max_caution_notes_per_entry))
    normalized_answer_mode = _normalize_prompt_answer_mode(answer_mode)
    normalized_scope = str(scope or "general").strip().lower() or "general"
    mode_limits = _prompt_context_mode_limits(normalized_answer_mode)

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
                "answer_mode": normalized_answer_mode,
                "scope": normalized_scope,
                "context_section_limit": int(mode_limits["context_sections"]),
                "section_item_limit": int(mode_limits["section_items"]),
                "source_limit": int(mode_limits["sources"]),
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
    selected_entry_count = min(entry_limit, len(retrieved_topics))
    # Reserve a small floor for each selected entry so later entries can still keep a summary.
    minimum_entry_budget = 0
    if selected_entry_count > 0:
        minimum_entry_budget = max(32, min(96, token_budget // selected_entry_count))

    for index, topic in enumerate(retrieved_topics[:entry_limit]):
        remaining_selected = selected_entry_count - index - 1
        entry_budget = remaining_tokens
        if remaining_selected > 0 and minimum_entry_budget > 0:
            reserved_for_later = remaining_selected * minimum_entry_budget
            if remaining_tokens > reserved_for_later:
                entry_budget = remaining_tokens - reserved_for_later
            entry_budget = max(minimum_entry_budget, entry_budget)
            entry_budget = min(entry_budget, remaining_tokens)
        entry, entry_tokens, entry_truncated = _build_prompt_context_entry(
            topic,
            query_terms=query_terms,
            remaining_tokens=entry_budget,
            max_facts_per_entry=fact_limit,
            max_scripture_references_per_entry=reference_limit,
            max_caution_notes_per_entry=caution_limit,
            seen_texts=seen_texts,
            seen_references=seen_references,
            answer_mode=normalized_answer_mode,
            scope=normalized_scope,
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
        "answer_mode": normalized_answer_mode,
        "scope": normalized_scope,
        "context_section_limit": int(mode_limits["context_sections"]),
        "section_item_limit": int(mode_limits["section_items"]),
        "source_limit": int(mode_limits["sources"]),
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
    answer_mode: str,
    scope: str = "general",
) -> tuple[dict[str, Any] | None, int, bool]:
    object_id = normalize_id(str(topic.get("id") or "").strip())
    if not object_id or remaining_tokens <= 0:
        return None, 0, False

    title = _normalize_prompt_text(topic.get("title") or object_id) or object_id
    category = _humanize_prompt_category(topic.get("type"))
    mode_limits = _prompt_context_mode_limits(answer_mode)
    section_weights = _prompt_section_field_weights(answer_mode, scope)

    local_seen_texts = set(seen_texts)
    local_seen_references = set(seen_references)

    summary = _first_prompt_sentence(topic.get("summary"))
    summary = _trim_prompt_text(summary, min(remaining_tokens, 64))
    summary_key = normalize_text(summary)
    if summary_key:
        local_seen_texts.add(summary_key)

    sections: list[dict[str, Any]] = []
    facts: list[str] = []
    selected_references: list[str] = []
    selected_cautions: list[str] = []
    source_objects = _select_prompt_sources(
        topic.get("sources"),
        limit=int(mode_limits["sources"]),
        seen_keys=set(),
    )

    if summary:
        sections.append({"heading": "Summary", "items": [summary]})

    reference_limit = min(max_scripture_references_per_entry, int(mode_limits["scripture_references"]))
    reference_candidates = _collect_ranked_scripture_references(
        topic,
        query_terms=query_terms,
        seen_keys=local_seen_references,
    )
    selected_references = _select_ranked_prompt_texts(
        reference_candidates,
        limit=reference_limit,
        seen_keys=local_seen_references,
    )
    if selected_references:
        sections.append({"heading": "Primary Scripture References", "items": selected_references})

    context_section_limit = int(mode_limits["context_sections"])
    context_item_limit = min(max(1, max_facts_per_entry), int(mode_limits["section_items"]))
    context_sections_added = 0
    summary_fallback = ""
    section_order = (
        _CULTURAL_CONTEXT_SECTION_ORDER
        if scope == "cultural_context"
        else _PROMPT_CONTEXT_SECTION_ORDER
    )
    for section_heading in section_order:
        if context_sections_added >= context_section_limit:
            break
        candidates = _collect_ranked_prompt_texts(
            topic,
            field_weights=section_weights[section_heading],
            query_terms=query_terms,
            seen_keys=local_seen_texts,
        )
        selected_items = _select_ranked_prompt_texts(
            candidates,
            limit=context_item_limit,
            seen_keys=local_seen_texts,
        )
        if not selected_items:
            continue
        if not summary and not summary_fallback:
            summary_fallback = selected_items.pop(0)
            summary = _trim_prompt_text(summary_fallback, min(remaining_tokens, 64))
            summary_key = normalize_text(summary)
            if summary_key:
                local_seen_texts.add(summary_key)
            if not selected_items:
                continue
        sections.append({"heading": section_heading, "items": selected_items})
        context_sections_added += 1
        for item in selected_items:
            key = normalize_text(item)
            if key:
                local_seen_texts.add(key)
                if len(facts) < max_facts_per_entry:
                    facts.append(item)

    if not summary and summary_fallback:
        summary = _trim_prompt_text(summary_fallback, min(remaining_tokens, 64))
        summary_key = normalize_text(summary)
        if summary_key:
            local_seen_texts.add(summary_key)
    sections = [section for section in sections if str(section.get("heading") or "").strip() != "Summary"]
    if summary:
        sections.insert(0, {"heading": "Summary", "items": [summary]})

    caution_candidates = [] if scope == "cultural_context" else _collect_ranked_prompt_texts(
        topic,
        field_weights=section_weights["Interpretive Disputes and Cautions"],
        query_terms=query_terms,
        seen_keys=local_seen_texts,
    )
    caution_limit = min(max_caution_notes_per_entry, int(mode_limits["caution_notes"]))
    selected_cautions = _select_ranked_prompt_texts(
        caution_candidates,
        limit=caution_limit,
        seen_keys=local_seen_texts,
    )
    if scope != "cultural_context" and not selected_cautions:
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
    if selected_cautions:
        sections.append({"heading": "Interpretive Disputes and Cautions", "items": selected_cautions})

    if scope != "cultural_context" and int(mode_limits["later_reception"]) > 0:
        later_candidates = _collect_ranked_prompt_texts(
            topic,
            field_weights=section_weights["Later Christian Reception"],
            query_terms=query_terms,
            seen_keys=local_seen_texts,
        )
        selected_later = _select_ranked_prompt_texts(
            later_candidates,
            limit=int(mode_limits["later_reception"]),
            seen_keys=local_seen_texts,
        )
        if selected_later:
            sections.append({"heading": "Later Christian Reception", "items": selected_later})
            for item in selected_later:
                key = normalize_text(item)
                if key:
                    local_seen_texts.add(key)
                if len(facts) < max_facts_per_entry:
                    facts.append(item)

    entry: dict[str, Any] = {
        "id": object_id,
        "title": title,
        "category": category,
        "object_version": str(topic.get("object_version") or "").strip(),
        "summary": summary,
        "_fact_limit": max_facts_per_entry,
        "facts": facts,
        "scripture_references": selected_references,
        "caution_notes": selected_cautions,
        "source_ids": [object_id],
        "sections": sections,
        "sources": source_objects,
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
    applicability = _topic_applicability_for(topic)
    for field_order, (field_name, base_weight) in enumerate(field_weights):
        applicability_key = _CONTEXT_FIELD_APPLICABILITY_LOOKUP.get(field_name)
        if applicability_key is not None and not applicability.get(applicability_key, True):
            continue
        if field_name == "interpretive_notes":
            field_values = interpretive_note_texts(topic.get(field_name))
        else:
            field_values = _iter_prompt_text_segments(topic.get(field_name))
        for value_index, text in enumerate(field_values):
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
    return _estimate_text_tokens("\n".join(_render_prompt_context_entry_lines(entry)))


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
    entry["sections"] = [
        {
            "heading": str(section.get("heading") or "").strip(),
            "items": list(section.get("items") or []),
        }
        for section in entry.get("sections") or []
        if str(section.get("heading") or "").strip()
    ]
    entry["sources"] = list(entry.get("sources") or [])
    entry["summary"] = _normalize_prompt_text(entry.get("summary"))

    def entry_tokens() -> int:
        return _estimate_prompt_context_entry_tokens(entry)

    while entry_tokens() > budget:
        if _trim_prompt_context_sections(entry):
            truncated = True
            continue
        if entry["summary"]:
            shorter = _trim_prompt_text(entry["summary"], max(4, budget // 2))
            if shorter and shorter != entry["summary"]:
                entry["summary"] = shorter
                for section in entry.get("sections") or []:
                    if str(section.get("heading") or "").strip() == "Summary":
                        section["items"] = [shorter]
                        break
                _sync_prompt_context_entry_fields(entry)
                truncated = True
                continue
            entry["summary"] = ""
            for section in entry.get("sections") or []:
                if str(section.get("heading") or "").strip() == "Summary":
                    section["items"] = []
                    break
            _sync_prompt_context_entry_fields(entry)
            truncated = True
            continue
        break

    tokens = entry_tokens()
    if tokens > budget:
        minimal_entry = {
            "id": entry.get("id"),
            "title": entry.get("title"),
            "category": entry.get("category"),
            "summary": "",
            "_fact_limit": entry.get("_fact_limit"),
            "facts": [],
            "scripture_references": [],
            "caution_notes": [],
            "source_ids": list(entry.get("source_ids") or []),
            "sections": [],
            "sources": [],
        }
        minimal_tokens = _estimate_prompt_context_entry_tokens(minimal_entry)
        if minimal_tokens <= budget:
            return minimal_entry, minimal_tokens, True
        return entry, tokens, truncated

    return entry, tokens, truncated


def _render_prompt_context_entry_lines(entry: Mapping[str, Any]) -> list[str]:
    lines = [
        f"## Entry: {str(entry.get('title') or entry.get('id') or 'unknown').strip()}",
        f"Category: {_normalize_prompt_text(entry.get('category')) or 'Unknown'}",
    ]

    sections = list(entry.get("sections") or [])
    if sections:
        for section in sections:
            heading = str(section.get("heading") or "").strip()
            raw_items = list(section.get("items") or [])
            items: list[str] = []
            for raw_item in raw_items:
                text = _render_prompt_context_source_item(raw_item) if heading == "Sources" else str(raw_item).strip()
                if text:
                    items.append(text)
            if not heading or not items:
                continue
            if heading == "Summary":
                lines.append(f"Summary: {items[0]}")
                continue
            lines.append(f"{heading}:")
            if heading == "Sources":
                source_ids = [str(item).strip() for item in entry.get("source_ids") or [] if str(item).strip()]
                if source_ids:
                    if len(source_ids) == 1:
                        lines.append(f"Source ID: {source_ids[0]}")
                    else:
                        lines.append("Source IDs: " + ", ".join(source_ids))
            lines.extend(f"- {item}" for item in items)
        return lines

    summary = _normalize_prompt_text(entry.get("summary"))
    if summary:
        lines.append(f"Summary: {summary}")
    facts = [str(item).strip() for item in entry.get("facts") or [] if str(item).strip()]
    if facts:
        lines.append("Relevant facts:")
        lines.extend(f"- {fact}" for fact in facts)
    scripture_references = [
        str(item).strip()
        for item in entry.get("scripture_references") or []
        if str(item).strip()
    ]
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
    return lines


def _render_prompt_context_source_item(value: Any) -> str:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if isinstance(value, Mapping):
        title = str(value.get("title") or "").strip()
        author = str(value.get("author") or "").strip()
        publisher = str(value.get("publisher") or "").strip()
        year = value.get("year")
        source_type = str(value.get("source_type") or "").strip()
        locator = str(value.get("locator") or "").strip()
        notes = str(value.get("notes") or "").strip()

        parts: list[str] = []
        primary = title or author or source_type
        if primary:
            parts.append(primary)
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


def _trim_prompt_context_sections(entry: dict[str, Any]) -> bool:
    sections = list(entry.get("sections") or [])
    if not sections:
        return False

    for index in range(len(sections) - 1, -1, -1):
        section = sections[index]
        heading = str(section.get("heading") or "").strip()
        items = [item for item in list(section.get("items") or []) if str(item).strip()]
        if not heading or not items:
            del sections[index]
            entry["sections"] = sections
            _sync_prompt_context_entry_fields(entry)
            return True
        if heading == "Summary":
            continue
        items.pop()
        if items:
            section["items"] = items
        else:
            del sections[index]
        entry["sections"] = sections
        _sync_prompt_context_entry_fields(entry)
        return True
    return False


def _sync_prompt_context_entry_fields(entry: dict[str, Any]) -> None:
    sections = list(entry.get("sections") or [])
    if not sections:
        return

    summary = _normalize_prompt_text(entry.get("summary"))
    facts: list[str] = []
    scripture_references: list[str] = []
    caution_notes: list[str] = []

    for section in sections:
        heading = str(section.get("heading") or "").strip()
        items = [str(item).strip() for item in section.get("items") or [] if str(item).strip()]
        if not heading or not items:
            continue
        if heading == "Summary":
            summary = items[0]
            continue
        if heading == "Primary Scripture References":
            scripture_references.extend(items)
            continue
        if heading == "Interpretive Disputes and Cautions":
            caution_notes.extend(items)
            continue
        if heading == "Later Christian Reception":
            facts.extend(items)
            continue
        if heading == "Sources":
            continue
        facts.extend(items)

    entry["summary"] = summary
    fact_limit = entry.get("_fact_limit")
    deduped_facts = _dedupe_text_list(facts)
    if isinstance(fact_limit, int) and fact_limit >= 0:
        deduped_facts = deduped_facts[:fact_limit]
    entry["facts"] = deduped_facts
    entry["scripture_references"] = _dedupe_text_list(scripture_references)
    entry["caution_notes"] = _dedupe_text_list(caution_notes)


def _dedupe_text_list(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = normalize_text(text)
        if not text or not key or key in seen:
            continue
        seen.add(key)
        deduped.append(text)
    return deduped
