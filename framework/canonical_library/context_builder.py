"""Build structured context packages from canonical library retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .loader import CanonicalLibrary


def _dedupe_extend(target: list[Any], values: list[Any], *, limit: int | None = None) -> None:
    seen = set(target)
    for value in values:
        if not value or value in seen:
            continue
        target.append(value)
        seen.add(value)
        if limit is not None and len(target) >= limit:
            return


@dataclass
class CanonicalContextBuilder:
    library: CanonicalLibrary
    max_topics: int = 5
    max_cross_references: int = 10
    max_related_topics: int = 10
    max_timeline_entries: int = 10
    max_archaeology_entries: int = 10

    def build(self, question: str, limit: int | None = None) -> dict[str, Any]:
        self.library._ensure_loaded()
        topic_limit = self.max_topics if limit is None else limit
        retrieved: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        primary = self.library.retrieve_exact(question)
        if primary is not None:
            self._append_result(retrieved, primary, seen_ids)

        keyword_limit = max(topic_limit - len(retrieved), 0)
        if keyword_limit > 0:
            for result in self.library.retrieve_by_keywords(question, limit=topic_limit):
                if result.object.id in seen_ids:
                    continue
                self._append_result(retrieved, result, seen_ids)
                if len(retrieved) >= topic_limit:
                    break

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
            "timeline": [],
            "archaeology": [],
            "new_testament_connections": [],
            "metadata": {
                "retrieval_method": retrieved[0]["match_type"] if retrieved else "none",
                "framework_version": self.library.manifest.get("framework_version", "1.0"),
                "topic_count": len(retrieved),
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
            related = obj.related_people + obj.related_places + obj.related_events
            _dedupe_extend(context["related_topics"], related, limit=self.max_related_topics)
            _dedupe_extend(context["timeline"], obj.timeline, limit=self.max_timeline_entries)
            _dedupe_extend(context["archaeology"], obj.archaeology, limit=self.max_archaeology_entries)
            _dedupe_extend(context["new_testament_connections"], obj.new_testament_connections)

        return context

    def _append_result(
        self,
        target: list[dict[str, Any]],
        result: Any,
        seen_ids: set[str],
    ) -> None:
        if result.object.id in seen_ids:
            return
        target.append(
            {
                "id": result.object.id,
                "type": result.object.type,
                "title": result.object.title,
                "matched_alias": result.matched_alias,
                "match_type": result.match_type,
                "score": result.score,
            }
        )
        seen_ids.add(result.object.id)
