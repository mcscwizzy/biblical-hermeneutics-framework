"""Compact, deterministic resource availability for the Study Companion."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from bhf_agent.bible import normalize_book_name
from bhf_agent.ckl import load_canonical_library
from bhf_agent.lexicon import WordStudyService
from bhf_agent.presentation import (
    EvidenceBundle,
    PresentationEngine,
    PresentationResult,
    SQLitePresentationCache,
    build_evidence_bundle,
    default_presentation_cache_path,
    deterministic_presentation,
)
from bhf_agent.presentation.eligibility import is_canonical_object_passage_eligible
from bhf_agent.study_db import (
    list_archaeology_passage_summaries,
    list_passage_map_summaries,
)
from bhf_agent.translation_installer import list_installed_translations
from framework.commentary.service import CommentaryService
from framework.canonical_library import CKLRepositoryConfig
from framework.canonical_library.narration import CanonicalNarrator
from framework.lexical.service import DEFAULT_LEXICAL_DATABASE_PATH


AVAILABLE = "available"
UNAVAILABLE = "unavailable"
UNKNOWN = "unknown"

_ENTITY_TYPES = {
    "person", "place", "theme", "people_group", "people-group", "group",
    "institution", "event", "timeline",
}
_CULTURAL_FIELDS = (
    "ancient_near_east_context",
    "hebraic_worldview",
    "second_temple_context",
)


class StalePresentationEvidenceError(ValueError):
    """The browser requested presentation for an evidence fingerprint that changed."""


def _default_canonical_library() -> Any:
    """Prefer the persistent Scripture index while retaining JSON fallback."""

    return load_canonical_library(config=CKLRepositoryConfig())


def _default_word_study_service() -> WordStudyService:
    configured = str(os.environ.get("BHF_LEXICAL_DATABASE_PATH") or "").strip()
    packaged = Path(DEFAULT_LEXICAL_DATABASE_PATH)
    local_runtime = Path(".bhf/lexicon.sqlite")
    path = Path(configured) if configured else packaged if packaged.exists() else local_runtime
    return WordStudyService(database_path=path)


class CompanionContextService:
    """Build one lightweight response from local, passage-indexed sources."""

    def __init__(
        self,
        *,
        study_db_path: str | Path,
        commentary_db_path: str | Path,
        canonical_library_provider: Callable[[], Any] = _default_canonical_library,
        translation_provider: Callable[[], list[dict[str, Any]]] = list_installed_translations,
        word_study_service: WordStudyService | None = None,
        commentary_service: CommentaryService | None = None,
        canonical_narrator: CanonicalNarrator | None = None,
        presentation_engine: PresentationEngine | None = None,
        presentation_cache_path: str | Path | None = None,
    ) -> None:
        self.study_db_path = Path(study_db_path)
        self.canonical_library_provider = canonical_library_provider
        self.translation_provider = translation_provider
        self.word_study = word_study_service or _default_word_study_service()
        self.commentary = commentary_service or CommentaryService(commentary_db_path)
        self.canonical_narrator = canonical_narrator or CanonicalNarrator()
        if presentation_engine is not None:
            self.presentation_engine = presentation_engine
        else:
            configured_cache = str(
                presentation_cache_path
                or os.environ.get("BHF_PRESENTATION_CACHE_PATH")
                or default_presentation_cache_path(self.study_db_path)
            ).strip()
            self.presentation_engine = PresentationEngine(
                cache=SQLitePresentationCache(configured_cache)
            )
        self._canonical_library: Any | None = None
        self._translation_cache: list[dict[str, Any]] | None = None
        self._translation_cache_time = 0.0
        self._canonical_cache_lock = threading.RLock()
        self._translation_cache_lock = threading.RLock()

    def invalidate_canonical_cache(self) -> None:
        """Drop the cached CKL view after local curation changes."""

        with self._canonical_cache_lock:
            self._canonical_library = None

    def invalidate_translation_cache(self) -> None:
        """Refresh installed-translation availability after local mutations."""

        with self._translation_cache_lock:
            self._translation_cache = None
            self._translation_cache_time = 0.0

    def build(
        self,
        *,
        book: str,
        chapter: int,
        verse_start: int | None = None,
        verse_end: int | None = None,
        translation: str | None = None,
    ) -> dict[str, Any]:
        canonical_book = normalize_book_name(str(book))
        chapter_number = _positive_int(chapter, "chapter")
        start = _optional_positive_int(verse_start, "verse_start")
        end = _optional_positive_int(verse_end, "verse_end") or start
        if start is not None and end is not None and end < start:
            raise ValueError("verse_end must be greater than or equal to verse_start")
        range_start, range_end = (start or 1), (end or 9999)
        reference = _format_reference(canonical_book, chapter_number, start, end)

        resources: dict[str, dict[str, Any]] = {}
        subsystems: dict[str, dict[str, Any]] = {}
        summaries: dict[str, Any] = {}

        commentary_count = self._probe(
            "commentary",
            subsystems,
            lambda: self._commentary_count(
                canonical_book,
                chapter_number,
                start,
                end,
            ),
        )
        resources["commentary"] = _resource_from_count(commentary_count)

        word_count = self._probe(
            "word_study",
            subsystems,
            lambda: self._word_count(canonical_book, chapter_number, start, end),
        )
        resources["word_study"] = _resource_from_count(word_count)

        map_context = self._probe(
            "maps",
            subsystems,
            lambda: self._map_context(canonical_book, chapter_number, range_start, range_end),
        )
        map_count = None if map_context is None else len(map_context["places"]) + len(map_context["routes"])
        resources["maps"] = _resource_from_count(map_count)
        summaries["maps"] = map_context or {"places": [], "routes": []}

        archaeology = self._probe(
            "archaeology",
            subsystems,
            lambda: list_archaeology_passage_summaries(
                canonical_book,
                chapter_number,
                range_start,
                range_end,
                path=self.study_db_path,
                limit=8,
                prepare_schema=False,
            ),
        )
        resources["archaeology"] = _resource_from_probe(archaeology)
        summaries["archaeology"] = archaeology or []

        canonical = self._probe(
            "canonical",
            subsystems,
            lambda: self._canonical_context(reference),
        )
        if canonical is None:
            canonical_results: list[Any] = []
            entities = {
                "people": [], "places": [], "themes": [], "groups": [], "events": []
            }
            for resource_id in (
                "canonical",
                "people",
                "themes",
                "timeline",
                "cross_references",
                "historical_context",
                "cultural_context",
                "literary_context",
                "original_audience",
                "covenant_context",
            ):
                resources[resource_id] = _resource(UNKNOWN, 0, error="canonical_unavailable")
            canonical_places: list[dict[str, Any]] = []
        else:
            canonical_results = list(canonical.pop("_results", []))
            entities = canonical["entities"]
            canonical_places = entities["places"]
            resources.update(canonical["resources"])
            summaries.update(canonical["summaries"])

        map_places = (map_context or {}).get("places", [])
        combined_places = _unique_summaries([*canonical_places, *map_places])
        entities["places"] = combined_places
        if map_context is not None:
            if canonical is not None or combined_places:
                resources["places"] = _resource_from_count(len(combined_places))

        translations = self._probe(
            "translations",
            subsystems,
            self._translations,
        )
        translation_count = None if translations is None else len(
            {
                str(item.get("translation_id") or item.get("id") or "").strip().casefold()
                for item in translations
                if item.get("installed", True)
                and str(item.get("translation_id") or item.get("id") or "").strip()
            }
        )
        resources["compare_translations"] = _resource_from_count(
            translation_count,
            minimum_available=2,
        )
        if translation:
            resources["compare_translations"]["selected_translation"] = str(translation).strip().casefold()

        evidence_bundle = build_evidence_bundle(
            reference,
            canonical_results=canonical_results,
            geography=map_context or {},
            archaeology=archaeology or [],
        )
        presentation = self._probe(
            "presentation",
            subsystems,
            lambda: self._local_presentation(evidence_bundle),
        )
        if presentation is None:
            presentation = PresentationResult(
                packet=deterministic_presentation(
                    evidence_bundle,
                    [],
                    maximum_cards=0,
                ),
                mode="deterministic_fallback",
                diagnostics=("presentation subsystem unavailable",),
            )
        resources["discoveries"] = _resource_from_count(len(presentation.packet.cards))

        presentation_payload = _presentation_payload(evidence_bundle, presentation)
        return {
            "reference": reference,
            "scope": "passage" if start is not None else "chapter",
            "resources": resources,
            "entities": entities,
            "summaries": summaries,
            "narration": summaries.get("narration", {"reference": reference, "by_context": {}}),
            **presentation_payload,
            "presentation_enhancement": {
                "available": bool(
                    getattr(self.presentation_engine, "enhancement_available", False)
                ),
                "evidence_hash": evidence_bundle.evidence_hash,
            },
            "subsystems": subsystems,
        }

    def enhance_presentation(
        self,
        *,
        book: str,
        chapter: int,
        evidence_hash: str,
        verse_start: int | None = None,
        verse_end: int | None = None,
    ) -> dict[str, Any]:
        """Generate optional prose only after an explicit browser request."""

        canonical_book = normalize_book_name(str(book))
        chapter_number = _positive_int(chapter, "chapter")
        start = _optional_positive_int(verse_start, "verse_start")
        end = _optional_positive_int(verse_end, "verse_end") or start
        if start is not None and end is not None and end < start:
            raise ValueError("verse_end must be greater than or equal to verse_start")
        expected_hash = str(evidence_hash or "").strip()
        if not expected_hash:
            raise ValueError("evidence_hash is required")
        range_start, range_end = (start or 1), (end or 9999)
        reference = _format_reference(canonical_book, chapter_number, start, end)
        bundle = build_evidence_bundle(
            reference,
            canonical_results=self._canonical_results(reference),
            geography=self._map_context(
                canonical_book, chapter_number, range_start, range_end
            ),
            archaeology=list_archaeology_passage_summaries(
                canonical_book,
                chapter_number,
                range_start,
                range_end,
                path=self.study_db_path,
                limit=8,
                prepare_schema=False,
            ),
        )
        if bundle.evidence_hash != expected_hash:
            raise StalePresentationEvidenceError(
                "Passage evidence changed; reload Companion context before enhancing it."
            )
        presentation = self.presentation_engine.present(bundle)
        return {
            "reference": reference,
            **_presentation_payload(bundle, presentation),
        }

    def _local_presentation(self, bundle: EvidenceBundle) -> PresentationResult:
        local = getattr(self.presentation_engine, "present_local", None)
        if callable(local):
            return local(bundle)
        return PresentationResult(
            packet=deterministic_presentation(bundle),
            mode="deterministic_fallback",
        )

    @staticmethod
    def _probe(
        name: str,
        subsystems: dict[str, dict[str, Any]],
        operation: Callable[[], Any],
    ) -> Any | None:
        try:
            value = operation()
        except Exception as exc:  # noqa: BLE001 - one resource must not break the companion
            subsystems[name] = {
                "status": UNKNOWN,
                "error": type(exc).__name__,
            }
            return None
        subsystems[name] = {"status": AVAILABLE}
        return value

    def _map_context(
        self,
        book: str,
        chapter: int,
        verse_start: int,
        verse_end: int,
    ) -> dict[str, list[dict[str, Any]]]:
        return list_passage_map_summaries(
            book,
            chapter,
            verse_start,
            verse_end,
            path=self.study_db_path,
            limit=12,
            prepare_schema=False,
        )

    def _word_count(
        self,
        book: str,
        chapter: int,
        verse_start: int | None,
        verse_end: int | None,
    ) -> int:
        database_path = getattr(self.word_study, "database_path", None)
        if database_path is not None and not Path(database_path).exists():
            return 0
        return self.word_study.repository.count_passage_words(
            book, chapter, verse_start, verse_end
        )

    def _commentary_count(
        self,
        book: str,
        chapter: int,
        verse_start: int | None,
        verse_end: int | None,
    ) -> int:
        repository = getattr(self.commentary, "repository", None)
        if repository is not None and not bool(getattr(repository, "available", True)):
            return 0
        if verse_start is not None:
            return self.commentary.count_passage(
                book,
                chapter,
                verse_start,
                verse_end,
            )
        return self.commentary.count_chapter(book, chapter)

    def _translations(self) -> list[dict[str, Any]]:
        with self._translation_cache_lock:
            now = time.monotonic()
            if self._translation_cache is None or now - self._translation_cache_time >= 30:
                self._translation_cache = self.translation_provider()
                self._translation_cache_time = now
            return self._translation_cache

    def _canonical_context(self, reference: str) -> dict[str, Any]:
        results = self._canonical_results(reference)
        objects = [item.object for item in results]
        eligible_objects = [
            item
            for item in objects
            if is_canonical_object_passage_eligible(reference, item)
        ]

        entities: dict[str, list[dict[str, Any]]] = {
            "people": [],
            "places": [],
            "themes": [],
            "groups": [],
            "events": [],
        }
        eligible_ids = {
            str(getattr(item, "id", "") or "") for item in eligible_objects
        }
        for item, result in zip(objects, results):
            object_type = str(getattr(item, "type", "") or "").casefold()
            object_id = str(getattr(item, "id", "") or "")
            if object_type not in _ENTITY_TYPES or object_id not in eligible_ids:
                continue
            entities[_entity_bucket(object_type)].append(
                {
                    "id": object_id,
                    "title": str(getattr(item, "title", "") or ""),
                    "type": object_type,
                    "summary": str(getattr(item, "summary", "") or ""),
                    "relationship": "direct Scripture anchor",
                    "score": float(getattr(result, "score", 0.0) or 0.0),
                }
            )
        entities = {key: _unique_summaries(value) for key, value in entities.items()}

        cross_references = _unique_strings(
            value
            for item in objects
            for value in [
                *list(getattr(item, "cross_references", []) or []),
                *list(getattr(item, "intertextuality", []) or []),
            ]
        )
        timeline_objects = [
            item
            for item in eligible_objects
            if str(getattr(item, "type", "") or "").casefold() in {"event", "timeline"}
        ]
        resources = {
            "canonical": _resource_from_count(len(objects)),
            "people": _resource_from_count(len(entities["people"])),
            "places": _resource_from_count(len(entities["places"])),
            "themes": _resource_from_count(len(entities["themes"])),
            "timeline": _resource_from_count(len(timeline_objects)),
            "cross_references": _resource_from_count(len(cross_references)),
            "historical_context": _resource_from_count(_field_count(objects, ("historical_context", "historical_setting", "date_ranges"))),
            "cultural_context": _resource_from_count(_field_count(objects, _CULTURAL_FIELDS)),
            "literary_context": _resource_from_count(_field_count(objects, ("literary_context", "genre", "structure"))),
            "original_audience": _resource_from_count(_field_count(objects, ("original_audience",))),
            "covenant_context": _resource_from_count(_field_count(objects, ("covenantal_significance",))),
        }
        narrations = {}
        for narration_type in (
            "historical_context",
            "cultural_context",
            "original_audience",
            "literary_context",
            "archaeology",
            "canonical_context",
            "covenant_context",
        ):
            narrated = self.canonical_narrator.narrate(
                results,
                reference=reference,
                context_type=narration_type,
            )
            if narrated.has_content:
                narrations[narration_type] = narrated.to_dict()
        return {
            "_results": results,
            "entities": entities,
            "resources": resources,
            "summaries": {
                "cross_references": cross_references[:12],
                "timeline": [
                    {
                        "id": str(getattr(item, "id", "") or ""),
                        "title": str(getattr(item, "title", "") or ""),
                        "summary": str(getattr(item, "summary", "") or ""),
                    }
                    for item in timeline_objects[:8]
                ],
                "canonical": [
                    {
                        "id": str(getattr(item, "id", "") or ""),
                        "title": str(getattr(item, "title", "") or ""),
                        "type": str(getattr(item, "type", "") or ""),
                        "summary": str(getattr(item, "summary", "") or ""),
                    }
                    for item in objects[:12]
                ],
                "narration": {
                    "reference": reference,
                    "by_context": narrations,
                },
            },
        }

    def _canonical_results(self, reference: str) -> list[Any]:
        with self._canonical_cache_lock:
            if self._canonical_library is None:
                self._canonical_library = self.canonical_library_provider()
            library = self._canonical_library
        lookup = getattr(library, "retrieve_by_scripture_reference", None)
        if not callable(lookup):
            raise RuntimeError("canonical Scripture index is unavailable")
        return list(lookup(reference, limit=100, include_placeholders=False))


def _resource(state: str, count: int, *, error: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "state": state,
        "available": state == AVAILABLE,
        "count": max(0, int(count)),
    }
    if error:
        value["error"] = error
    return value


def _resource_from_count(value: int | None, *, minimum_available: int = 1) -> dict[str, Any]:
    if value is None:
        return _resource(UNKNOWN, 0)
    count = max(0, int(value))
    return _resource(AVAILABLE if count >= minimum_available else UNAVAILABLE, count)


def _resource_from_probe(value: Any | None) -> dict[str, Any]:
    if value is None:
        return _resource(UNKNOWN, 0)
    try:
        count = len(value)
    except TypeError:
        count = int(value or 0)
    return _resource_from_count(count)


def _field_count(objects: Iterable[Any], fields: Iterable[str]) -> int:
    return sum(
        1
        for item in objects
        if any(bool(getattr(item, field, None)) for field in fields)
    )


def _unique_strings(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if text and key not in seen:
            result.append(text)
            seen.add(key)
    return result


def _unique_summaries(values: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        key = str(value.get("id") or value.get("title") or "").strip().casefold()
        if key and key not in seen:
            result.append(value)
            seen.add(key)
    return result


def _entity_bucket(object_type: str) -> str:
    return {
        "person": "people",
        "place": "places",
        "theme": "themes",
        "people_group": "groups",
        "people-group": "groups",
        "group": "groups",
        "institution": "groups",
        "event": "events",
        "timeline": "events",
    }[object_type]


def _presentation_payload(
    bundle: EvidenceBundle,
    presentation: PresentationResult,
) -> dict[str, Any]:
    """Serialize only evidence required by the cards visible to the reader."""

    evidence_ids = {
        evidence_id
        for card in presentation.packet.cards
        for evidence_id in card.evidence_ids
    }
    sources_by_id = {
        str(source.get("id") or ""): source
        for source in bundle.provenance.get("sources", [])
    }
    compact_evidence = []
    for item in bundle.evidence_items:
        if item.id not in evidence_ids:
            continue
        compact_evidence.append(
            {
                "id": item.id,
                "claim": item.claim,
                "category": item.category,
                "confidence": item.confidence,
                "sources": [
                    {
                        "id": source_id,
                        "title": str(
                            sources_by_id.get(source_id, {}).get("title") or source_id
                        ),
                        "source_type": str(
                            sources_by_id.get(source_id, {}).get("source_type") or ""
                        ),
                    }
                    for source_id in item.source_ids
                ],
            }
        )
    return {
        # A compatibility shell retains fingerprint and map navigation fields
        # without exposing the full internal EvidenceBundle to the browser.
        "evidence_bundle": {
            "passage_ref": bundle.passage_ref,
            "version": bundle.version,
            "evidence_hash": bundle.evidence_hash,
            "compact": True,
            "entities": {
                bucket: [
                    {"id": entity.id, "title": entity.title, "type": entity.type}
                    for entity in bundle.entities.get(bucket, [])
                ]
                for bucket in bundle.entities
            },
            "geography": {
                "map_location_refs": list(
                    bundle.geography.get("map_location_refs") or []
                ),
                "map_route_refs": list(bundle.geography.get("map_route_refs") or []),
            },
        },
        "presentation_packet": presentation.to_dict(include_diagnostics=False),
        "presentation_evidence": compact_evidence,
    }


def _positive_int(value: Any, label: str) -> int:
    number = _optional_positive_int(value, label)
    if number is None:
        raise ValueError(f"{label} must be a positive integer")
    return number


def _optional_positive_int(value: Any, label: str) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive integer") from exc
    if number <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return number


def _format_reference(book: str, chapter: int, start: int | None, end: int | None) -> str:
    base = f"{book} {chapter}"
    if start is None:
        return base
    return f"{base}:{start}" if not end or end == start else f"{base}:{start}-{end}"


__all__ = ["AVAILABLE", "UNAVAILABLE", "UNKNOWN", "CompanionContextService"]
