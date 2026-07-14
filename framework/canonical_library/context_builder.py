"""Build structured context packages from canonical library retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .loader import CanonicalLibrary
from .normalization import normalize_id
from .retrieval import RetrievalResult


LEGACY_RELATIONSHIP_TYPES: dict[str, str] = {
    "related_people": "associated-person",
    "related_places": "associated-place",
    "related_events": "associated-event",
}


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
    ) -> list[RetrievalResult]:
        primary_results: list[RetrievalResult] = []
        if limit <= 0:
            return primary_results

        primary = self.library.retrieve_exact(
            question,
            approved_only=approved_only,
            exclude_deprecated=exclude_deprecated,
            exclude_rejected=exclude_rejected,
        )
        if primary is not None:
            primary_results.append(primary)

        if len(primary_results) < limit:
            for result in self.library.retrieve_by_keywords(
                question,
                limit=limit,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
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
    ) -> list[dict[str, Any]]:
        expanded: list[dict[str, Any]] = []
        current_frontier = list(seed_entries)
        current_depth = 0

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
