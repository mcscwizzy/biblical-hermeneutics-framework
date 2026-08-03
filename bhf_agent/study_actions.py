"""Deterministic Scripture/CKL study action routing."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from framework.canonical_library import CanonicalLibrary

from .bible import BibleError, load_translation_bible, resolve_passage, verse_range_reference
from .ckl import load_canonical_library
from .context_pipeline import (
    build_context_evidence_packet,
    deterministic_context_presentation,
)
from .lexicon import WordStudyResult, WordStudyService
from .models import Serializable


ACTION_ALIASES = {
    "ancient_context": "cultural_context",
    "ancient_cultural_context": "cultural_context",
    "related_ot_themes": "themes",
}

DETERMINISTIC_ACTIONS = frozenset(
    {
        "full_context",
        "historical_context",
        "cultural_context",
        "original_audience",
        "covenant_context",
        "literary_context",
        "word_study",
        "cross_references",
        "people",
        "places",
        "themes",
    }
)

DETERMINISTIC_ONLY_ACTIONS = frozenset({"cross_references", "people", "places"})

AGENT_FALLBACK_ACTIONS = frozenset(
    {
        "full_context",
        "historical_context",
        "cultural_context",
        "original_audience",
        "covenant_context",
        "literary_context",
        "themes",
    }
)

FIELD_GROUPS: dict[str, list[tuple[str, str]]] = {
    "historical_context": [
        ("Historical Context", "historical_context"),
        ("Historical Setting", "historical_setting"),
        ("Date Ranges", "date_ranges"),
        ("Timeline", "timeline"),
    ],
    "cultural_context": [
        ("Ancient Near East Context", "ancient_near_east_context"),
        ("Hebraic Worldview", "hebraic_worldview"),
        ("Second Temple Context", "second_temple_context"),
    ],
    "original_audience": [
        ("Original Audience", "original_audience"),
        ("Historical Setting", "historical_setting"),
    ],
    "covenant_context": [
        ("Covenantal Significance", "covenantal_significance"),
        ("Canonical Context", "canonical_context"),
        ("Canonical Placement", "canonical_placement"),
    ],
    "literary_context": [
        ("Literary Context", "literary_context"),
        ("Genre", "genre"),
        ("Structure", "structure"),
    ],
}

FULL_CONTEXT_ORDER = [
    "historical_context",
    "cultural_context",
    "original_audience",
    "covenant_context",
    "literary_context",
]

ACTION_TITLES = {
    "full_context": "Full Context",
    "historical_context": "Historical Context",
    "cultural_context": "Cultural Context",
    "original_audience": "Original Audience",
    "covenant_context": "Covenant Context",
    "literary_context": "Literary Context",
    "word_study": "Word Study",
    "cross_references": "Cross References",
    "people": "People",
    "places": "Places",
    "themes": "Themes",
}


@dataclass
class StudyActionResult(Serializable):
    action: str
    status: str
    source: str
    title: str
    sections: list[dict[str, Any]] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    confidence: float = 0.0
    missing_fields: list[str] = field(default_factory=list)
    agent_fallback_allowed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    presentation: dict[str, Any] | None = None
    evidence_packet: dict[str, Any] | None = None


class StudyActionRouter:
    """Route study actions to deterministic Scripture/CKL results first."""

    def __init__(self, engine: "DeterministicStudyEngine | None" = None) -> None:
        self.engine = engine or DeterministicStudyEngine()

    def execute(
        self,
        action: str,
        *,
        passage: Mapping[str, Any] | None = None,
        selection: Mapping[str, Any] | None = None,
        query: str | None = None,
        fallback: Callable[[StudyActionResult], StudyActionResult] | None = None,
        allow_partial_fallback: bool = False,
    ) -> StudyActionResult:
        result = self.engine.execute(action, passage=passage, selection=selection, query=query)
        should_fallback = (
            fallback is not None
            and result.agent_fallback_allowed
            and (result.status == "unavailable" or (allow_partial_fallback and result.status == "partial"))
        )
        if should_fallback:
            return fallback(result)
        return result


class DeterministicStudyEngine:
    def __init__(
        self,
        library: CanonicalLibrary | None = None,
        word_study_service: WordStudyService | None = None,
    ) -> None:
        self._library = library
        self._word_study_service = word_study_service

    @property
    def library(self) -> CanonicalLibrary:
        if self._library is None:
            self._library = load_canonical_library()
        return self._library

    @property
    def word_study_service(self) -> WordStudyService:
        if self._word_study_service is None:
            self._word_study_service = WordStudyService()
        return self._word_study_service

    def execute(
        self,
        action: str,
        *,
        passage: Mapping[str, Any] | None = None,
        selection: Mapping[str, Any] | None = None,
        query: str | None = None,
    ) -> StudyActionResult:
        canonical_action = normalize_action(action)
        if canonical_action not in DETERMINISTIC_ACTIONS:
            raise ValueError(f"Unsupported deterministic study action: {action}")

        passage_data = self._resolve_passage(passage or selection or {})
        reference = str(passage_data.get("reference") or "").strip()
        objects = self._objects_for_passage(passage_data)
        sections: list[dict[str, Any]] = []
        missing_fields: list[str] = []
        word_study: WordStudyResult | None = None
        evidence_packet: dict[str, Any] | None = None
        presentation: dict[str, Any] | None = None

        if canonical_action in {
            "full_context",
            "historical_context",
            "cultural_context",
            "original_audience",
            "covenant_context",
            "literary_context",
        }:
            evidence_packet = build_context_evidence_packet(
                objects,
                target_book=str(passage_data.get("book") or ""),
                reference=reference,
                action=canonical_action,
                selected_text=str(passage_data.get("selected_text") or ""),
                trusted_record_ids=self._trusted_context_record_ids(passage_data, objects),
            )
            presentation = deterministic_context_presentation(evidence_packet)
            sections.extend(self._context_sections(evidence_packet, canonical_action))
            if not sections and evidence_packet.get("excluded"):
                missing_fields.append("validated_context_evidence")
        elif canonical_action in FIELD_GROUPS:
            sections.extend(self._scripture_sections(passage_data))
            grouped_sections, missing_fields = self._field_sections(canonical_action, objects)
            sections.extend(grouped_sections)
        elif canonical_action == "word_study":
            word_study = self.word_study_service.build_word_study(passage_data, query=query)
            sections.extend(self._word_study_sections(word_study))
            if word_study.status in {"ambiguous", "unavailable"}:
                missing_fields.append(f"word_study_{word_study.status}")
        elif canonical_action == "cross_references":
            sections.extend(self._cross_reference_sections(objects, current_reference=reference))
        elif canonical_action == "people":
            sections.extend(self._entity_sections(objects, "People", ("key_people", "related_people"), "person"))
        elif canonical_action == "places":
            sections.extend(self._entity_sections(objects, "Places", ("key_places", "related_places"), "place"))
        elif canonical_action == "themes":
            sections.extend(self._entity_sections(objects, "Themes", ("major_themes",), "theme"))

        sections = _dedupe_sections(sections)
        references = _unique([reference, *self._references_from_sections(sections)])
        object_ids = [str(getattr(obj, "id", "")) for obj in objects if getattr(obj, "id", "")]
        status = "complete" if sections else "unavailable"
        if canonical_action == "word_study" and "word_study_ambiguous" in missing_fields:
            status = "partial"
        elif canonical_action == "word_study" and "word_study_unavailable" in missing_fields:
            status = "unavailable"
        if sections and missing_fields:
            status = "partial"
        section_sources = {str(section.get("source") or "") for section in sections}
        if "scripture" in section_sources and "ckl" in section_sources:
            source = "scripture_and_ckl"
        elif "scripture" in section_sources and "lexical_sqlite" in section_sources:
            source = "scripture_and_lexical"
        elif "lexical_sqlite" in section_sources:
            source = "lexical_sqlite"
        elif "ckl" in section_sources:
            source = "ckl"
        elif "scripture" in section_sources:
            source = "scripture"
        elif sections:
            source = "deterministic"
        else:
            source = "deterministic"

        return StudyActionResult(
            action=canonical_action,
            status=status,
            source=source,
            title=f"{ACTION_TITLES[canonical_action]} for {reference or 'selected passage'}",
            sections=sections,
            references=references,
            confidence=self._confidence(status, object_ids, sections),
            missing_fields=_unique(missing_fields),
            agent_fallback_allowed=(
                bool(word_study and word_study.is_complete)
                if canonical_action == "word_study"
                else canonical_action in AGENT_FALLBACK_ACTIONS
            ),
            metadata={
                "reference": reference,
                "book": passage_data.get("book"),
                "chapter": passage_data.get("chapter"),
                "start_verse": passage_data.get("start_verse"),
                "end_verse": passage_data.get("end_verse"),
                "object_ids": object_ids,
                "deterministic_only": canonical_action in DETERMINISTIC_ONLY_ACTIONS,
                **(
                    {
                        "word_study": word_study.to_dict(),
                        "word_study_prompt_context": word_study.prompt_context,
                    }
                    if canonical_action == "word_study" and word_study is not None
                    else {}
                ),
            },
            presentation=presentation,
            evidence_packet=evidence_packet,
        )

    def _resolve_passage(self, context: Mapping[str, Any]) -> dict[str, Any]:
        book = _first(context, "book", "reader_book")
        chapter = _first(context, "chapter", "reader_chapter")
        if not book or not chapter:
            raise ValueError("book and chapter are required for deterministic study actions")
        start_verse = _first(context, "start_verse", "verse_start", "reader_start_verse")
        end_verse = _first(context, "end_verse", "verse_end", "reader_end_verse")
        translation_id = str(_first(context, "translation", "reader_translation", "source_translation") or "asv")
        # Device-only imports are intentionally not uploaded to the server. The
        # browser still sends the selected verse text, so deterministic context
        # actions should remain usable when their translation is unavailable to
        # this process. Use the bundled ASV only for the surrounding passage;
        # preserve the requested translation id for the selected-text section.
        try:
            data = load_translation_bible(translation_id)
        except ValueError:
            data = load_translation_bible("asv")
        try:
            resolved = resolve_passage(book, chapter, start_verse or None, end_verse or None, data=data)
        except BibleError:
            resolved = resolve_passage(book, chapter, start_verse or None, end_verse or None)
        selected_text = str(_first(context, "selected_text", "reader_selected_text", "text") or "").strip()
        if selected_text:
            resolved["selected_text"] = selected_text
        for key in (
            "word_position",
            "position",
            "token_position",
            "selected_word_position",
            "strongs_number",
            "strongs",
            "selected_strongs",
            "lemma",
            "selected_lemma",
            "language",
            "source_language",
            "surface_form",
            "selected_surface_form",
        ):
            value = context.get(key)
            if value not in (None, ""):
                resolved[key] = value
        resolved["translation_id"] = translation_id
        return resolved

    def _objects_for_passage(self, passage_data: Mapping[str, Any]) -> list[Any]:
        results = []
        book = str(passage_data.get("book") or "").strip()
        reference = str(passage_data.get("reference") or "").strip()
        if book:
            exact = self.library.retrieve_exact(book)
            if exact is not None:
                results.append(exact)
        if reference:
            results.extend(self.library.retrieve_by_scripture_reference(reference, limit=8))
        return _dedupe_results(results)

    def _trusted_context_record_ids(
        self,
        passage_data: Mapping[str, Any],
        objects: list[Any],
    ) -> set[str]:
        """Return records allowed to provide original-passage context.

        A topic can cite a passage as a supporting connection without being a
        historical or cultural source for that passage.  The exact book record
        and records with a primary scripture anchor are trusted; other records
        may contribute only explicitly-related later connections.
        """

        trusted: set[str] = set()
        book = str(passage_data.get("book") or "").strip().casefold()
        reference = str(passage_data.get("reference") or "").strip().casefold()
        chapter_match = re.search(r"\s(\d+)(?::|$)", reference)
        chapter = chapter_match.group(1) if chapter_match else ""
        exact = self.library.retrieve_exact(str(passage_data.get("book") or ""))
        if exact is not None and getattr(exact.object, "id", None):
            trusted.add(str(exact.object.id))
        for obj in objects:
            object_id = str(getattr(obj, "id", "") or "")
            object_type = str(getattr(obj, "type", "") or "").casefold()
            if object_type in {"theme", "biblical_theology", "theology", "doctrine"}:
                continue
            for item in getattr(obj, "scripture_references", None) or []:
                item_reference = str(getattr(item, "reference", "") or "").casefold()
                relationship = str(getattr(item, "relationship", "") or "").casefold().replace("-", "_")
                if (
                    relationship == "primary"
                    and item_reference.startswith(f"{book} {chapter}:")
                    and object_id
                ):
                    trusted.add(object_id)
        return trusted

    def _scripture_sections(self, passage_data: Mapping[str, Any]) -> list[dict[str, Any]]:
        text = str(passage_data.get("selected_text") or "").strip()
        if not text:
            return []
        translation = str(passage_data.get("translation_id") or "asv").upper()
        return [
            {
                "title": "Selected Scripture",
                "items": [text],
                "source": "scripture",
                "references": [str(passage_data.get("reference") or "")],
                "metadata": {"translation": translation},
            }
        ]

    def _field_sections(self, action: str, objects: list[Any]) -> tuple[list[dict[str, Any]], list[str]]:
        sections: list[dict[str, Any]] = []
        missing: list[str] = []
        for label, field_name in FIELD_GROUPS[action]:
            items = []
            for obj in objects:
                items.extend(_items_from_value(getattr(obj, field_name, None)))
            if items:
                sections.append({"title": label, "items": _unique(items), "source": "ckl"})
            else:
                missing.append(field_name)
        return sections, missing

    def _context_sections(
        self,
        packet: Mapping[str, Any],
        action: str,
    ) -> list[dict[str, Any]]:
        """Keep legacy section output while sourcing it from scoped evidence."""

        selected = list(packet.get("evidence") or [])
        if action != "full_context":
            primary_scopes = {
                "historical_context": {"historical_background", "same_book", "direct_passage", "same_chapter"},
                "cultural_context": {"cultural_background", "ancient_world_background", "same_book", "direct_passage", "same_chapter"},
                "original_audience": {"original_audience", "historical_background", "same_book", "direct_passage", "same_chapter"},
                "covenant_context": {"covenant_context", "same_book", "direct_passage", "same_chapter"},
                "literary_context": {"same_book", "direct_passage", "same_chapter"},
            }.get(action, set())
            selected = [item for item in selected if item.get("scope") in primary_scopes]
        else:
            selected = [
                item
                for item in selected
                if str(item.get("candidate_book") or "").casefold()
                == str(packet.get("target", {}).get("book") or "").casefold()
                and item.get("scope") not in {"weak_or_unverified", "canonical_theme"}
            ]
        grouped: dict[str, list[str]] = defaultdict(list)
        for item in selected:
            label = _context_section_label(str(item.get("evidence_type") or ""))
            grouped[label].append(str(item.get("fact") or ""))
        return [
            {
                "title": title,
                "items": _unique(items),
                "source": "scripture" if title == "Selected Scripture" else "ckl",
                "evidence_ids": [
                    str(item.get("evidence_id"))
                    for item in selected
                    if _context_section_label(str(item.get("evidence_type") or "")) == title
                ],
            }
            for title, items in grouped.items()
            if _unique(items)
        ]

    def _word_study_sections(self, result: WordStudyResult) -> list[dict[str, Any]]:
        if result.is_ambiguous:
            items = [
                f"{index}. {word.surface_form}"
                + (f" - {word.gloss}" if word.gloss else "")
                + f" ({word.lemma}; {_strongs_label(word.strongs_number)}; position {word.position})"
                for index, word in enumerate(result.ambiguities, start=1)
            ]
            return [
                {
                    "title": result.message or "Multiple possible original-language words found",
                    "items": items,
                    "source": "lexical_sqlite",
                    "metadata": {"status": result.status},
                }
            ]
        if not result.is_complete:
            return []

        details = [
            f"Original Word: {result.surface_form}",
            f"Lemma: {result.lemma}",
            f"Language: {result.language}",
        ]
        if result.transliteration:
            details.append(f"Transliteration: {result.transliteration}")
        if result.strongs_number:
            details.append(f"Strong's: {result.strongs_number}")
        morphology = _plain_morphology(result.morphology)
        if morphology:
            details.append(f"Morphology: {morphology}")
        elif result.morphology_code:
            details.append(f"Morphology: {result.morphology_code}")

        occurrence_items = [
            f"{word.reference}: {word.surface_form}"
            + (f" ({word.morphology_code})" if word.morphology_code else "")
            for word in result.representative_occurrences[:5]
        ]
        source_items = [
            " - ".join(
                value
                for value in (
                    str(source.get("name") or ""),
                    str(source.get("license") or ""),
                    str(source.get("attribution") or ""),
                )
                if value
            )
            for source in result.sources
        ]
        sections = [
            {
                "title": "Original Word",
                "items": details,
                "source": "lexical_sqlite",
                "metadata": {"status": result.status},
            },
            {
                "title": "Meaning Range",
                "items": result.lexical_range,
                "source": "lexical_sqlite",
            },
            {
                "title": "Contextual Information",
                "items": result.contextual_information,
                "source": "lexical_sqlite",
            },
        ]
        if occurrence_items:
            sections.append(
                {
                    "title": "Representative Occurrences",
                    "items": occurrence_items,
                    "source": "lexical_sqlite",
                    "references": [word.reference for word in result.representative_occurrences[:5]],
                }
            )
        sections.append({"title": "Word Study Safeguards", "items": result.guardrails, "source": "deterministic"})
        if source_items:
            sections.append({"title": "Sources", "items": source_items, "source": "lexical_sqlite"})
        return sections

    def _cross_reference_sections(self, objects: list[Any], *, current_reference: str) -> list[dict[str, Any]]:
        refs: list[str] = []
        for obj in objects:
            refs.extend(_references_from_value(getattr(obj, "cross_references", None)))
            refs.extend(_references_from_value(getattr(obj, "scripture_references", None)))
            refs.extend(_references_from_value(getattr(obj, "new_testament_connections", None)))
        refs = [ref for ref in _unique(refs) if ref and ref != current_reference]
        if not refs:
            return []
        return [{"title": "Cross References", "items": refs, "source": "ckl", "references": refs}]

    def _entity_sections(
        self,
        objects: list[Any],
        title: str,
        fields: Iterable[str],
        related_type: str,
    ) -> list[dict[str, Any]]:
        items: list[str] = []
        related_ids: list[str] = []
        for obj in objects:
            for field_name in fields:
                items.extend(_items_from_value(getattr(obj, field_name, None)))
            related_ids.extend(_items_from_value(getattr(obj, "related_objects", None)))
        for object_id in related_ids:
            result = self.library.retrieve_by_id(object_id)
            if result is not None and getattr(result.object, "type", "") == related_type:
                items.append(str(getattr(result.object, "title", object_id)))
        items = _unique(items)
        if not items:
            return []
        return [{"title": title, "items": items, "source": "ckl"}]

    def _references_from_sections(self, sections: list[dict[str, Any]]) -> list[str]:
        refs: list[str] = []
        for section in sections:
            refs.extend(_items_from_value(section.get("references")))
        return refs

    @staticmethod
    def _confidence(status: str, object_ids: list[str], sections: list[dict[str, Any]]) -> float:
        if status == "unavailable":
            return 0.0
        if object_ids:
            return 0.92 if status == "complete" else 0.78
        return 0.86 if sections else 0.0


def normalize_action(value: Any) -> str:
    action = str(value or "").strip().lower()
    return ACTION_ALIASES.get(action, action)


def _context_section_label(evidence_type: str) -> str:
    return {
        "historical_context": "Historical Context",
        "historical_setting": "Historical Setting",
        "date_ranges": "Dates and Setting",
        "timeline": "Timeline",
        "ancient_near_east_context": "Ancient World Background",
        "hebraic_worldview": "Cultural Background",
        "second_temple_context": "Cultural Background",
        "original_audience": "Original Audience",
        "covenantal_significance": "Covenant Context",
        "literary_context": "Literary Context",
        "summary": "Overview",
        "selected_scripture": "Selected Scripture",
    }.get(evidence_type, "Context Evidence")


def compact_fact_packet(result: StudyActionResult | Mapping[str, Any], *, max_chars: int = 1400) -> dict[str, Any]:
    data = result.to_dict() if isinstance(result, StudyActionResult) else dict(result)
    sections = []
    used = 0
    for section in list(data.get("sections") or [])[:8]:
        items = [str(item) for item in list(section.get("items") or [])[:6]]
        compact_items = []
        for item in items:
            remaining = max_chars - used
            if remaining <= 0:
                break
            snippet = item[:remaining]
            compact_items.append(snippet)
            used += len(snippet)
        if compact_items:
            sections.append(
                {
                    "title": str(section.get("title") or "Section"),
                    "items": compact_items,
                    "source": str(section.get("source") or "deterministic"),
                }
            )
    evidence_packet = data.get("evidence_packet")
    compact_evidence = []
    if isinstance(evidence_packet, Mapping):
        for evidence in list(evidence_packet.get("evidence") or [])[:24]:
            compact_evidence.append(
                {
                    key: evidence.get(key)
                    for key in (
                        "evidence_id",
                        "record_id",
                        "fact",
                        "evidence_type",
                        "scope",
                        "relationship",
                        "reference",
                        "candidate_book",
                        "confidence",
                    )
                }
            )
    return {
        "action": data.get("action"),
        "status": data.get("status"),
        "source": data.get("source"),
        "title": data.get("title"),
        "sections": sections,
        "references": list(data.get("references") or [])[:12],
        "confidence": data.get("confidence"),
        "metadata": {
            "reference": (data.get("metadata") or {}).get("reference"),
            "object_ids": list((data.get("metadata") or {}).get("object_ids") or [])[:12],
            "word_study_prompt_context": (data.get("metadata") or {}).get("word_study_prompt_context"),
        },
        "presentation": data.get("presentation"),
        "evidence_packet": {
            "target": (evidence_packet or {}).get("target") if isinstance(evidence_packet, Mapping) else None,
            "allowed_references": (evidence_packet or {}).get("allowed_references", []) if isinstance(evidence_packet, Mapping) else [],
            "evidence": compact_evidence,
        },
    }


def format_fact_packet_for_prompt(packet: Mapping[str, Any]) -> str:
    lines = [
        "# Deterministic BHF Fact Packet",
        "",
        "Use these Scripture/CKL facts as the controlling context. Do not invent missing facts.",
        f"Title: {packet.get('title') or 'Deterministic study result'}",
        f"Action: {packet.get('action') or 'study_action'}",
        f"Status: {packet.get('status') or 'unknown'}",
        f"Source: {packet.get('source') or 'deterministic'}",
    ]
    references = [str(ref) for ref in packet.get("references") or [] if str(ref).strip()]
    if references:
        lines.append("References: " + "; ".join(references))
    lexical_context = str((packet.get("metadata") or {}).get("word_study_prompt_context") or "").strip()
    if lexical_context:
        lines.extend(["", lexical_context])
        return "\n".join(lines)
    for section in packet.get("sections") or []:
        title = str(section.get("title") or "Section")
        lines.extend(["", f"## {title}"])
        for item in section.get("items") or []:
            lines.append(f"- {item}")
    for evidence in packet.get("evidence_packet", {}).get("evidence", []) or []:
        lines.append(
            f"- [evidence_id={evidence.get('evidence_id')}] "
            f"[{evidence.get('scope')}] {evidence.get('fact')}"
        )
    return "\n".join(lines)


def _first(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _dedupe_results(results: Iterable[Any]) -> list[Any]:
    objects = []
    seen = set()
    for result in results:
        obj = getattr(result, "object", result)
        object_id = getattr(obj, "id", None)
        if not object_id or object_id in seen:
            continue
        seen.add(object_id)
        objects.append(obj)
    return objects


def _items_from_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Mapping):
        reference = value.get("reference")
        note = value.get("note") or value.get("summary") or value.get("title")
        if reference and note:
            return [f"{reference}: {note}"]
        if reference:
            return [str(reference)]
        return [str(item).strip() for item in value.values() if str(item).strip()]
    if isinstance(value, (list, tuple, set)):
        items = []
        for item in value:
            if hasattr(item, "to_dict"):
                item = item.to_dict()
            items.extend(_items_from_value(item))
        return items
    return [str(value).strip()] if str(value).strip() else []


def _references_from_value(value: Any) -> list[str]:
    refs = []
    for item in _items_from_value(value):
        match = re.match(r"^([1-3]?\s?[A-Za-z]+(?:\s+[A-Za-z]+)?\s+\d+(?::\d+(?:-\d+)?)?)", item)
        refs.append(match.group(1) if match else item)
    return refs


def _dedupe_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen = set()
    for section in sections:
        items = _unique([str(item) for item in section.get("items") or [] if str(item).strip()])
        if not items:
            continue
        key = (section.get("title"), tuple(items))
        if key in seen:
            continue
        seen.add(key)
        copy = dict(section)
        copy["items"] = items
        deduped.append(copy)
    return deduped


def _unique(values: Iterable[str]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _plain_morphology(morphology: Mapping[str, Any]) -> str:
    ordered_keys = (
        "part_of_speech",
        "stem",
        "conjugation",
        "tense",
        "voice",
        "mood",
        "person",
        "gender",
        "number",
        "case",
        "state",
    )
    return ", ".join(str(morphology[key]) for key in ordered_keys if morphology.get(key))


def _strongs_label(value: str | None) -> str:
    return value if value else "no Strong's id"
