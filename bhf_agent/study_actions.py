"""Deterministic Scripture/CKL study action routing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from framework.canonical_library import CanonicalLibrary

from .bible import BibleError, load_translation_bible, resolve_passage, verse_range_reference
from .ckl import load_canonical_library
from .knowledge import LexicalEntry, load_lexical_entries
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
        "word_study",
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
    def __init__(self, library: CanonicalLibrary | None = None) -> None:
        self._library = library

    @property
    def library(self) -> CanonicalLibrary:
        if self._library is None:
            self._library = load_canonical_library()
        return self._library

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

        if canonical_action == "full_context":
            sections.extend(self._scripture_sections(passage_data))
            for grouped_action in FULL_CONTEXT_ORDER:
                grouped_sections, grouped_missing = self._field_sections(grouped_action, objects)
                sections.extend(grouped_sections)
                missing_fields.extend(grouped_missing)
        elif canonical_action in FIELD_GROUPS:
            sections.extend(self._scripture_sections(passage_data))
            grouped_sections, missing_fields = self._field_sections(canonical_action, objects)
            sections.extend(grouped_sections)
        elif canonical_action == "word_study":
            sections.extend(self._word_study_sections(passage_data, query=query))
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
        if sections and missing_fields:
            status = "partial"
        section_sources = {str(section.get("source") or "") for section in sections}
        if "scripture" in section_sources and "ckl" in section_sources:
            source = "scripture_and_ckl"
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
            agent_fallback_allowed=canonical_action in AGENT_FALLBACK_ACTIONS,
            metadata={
                "reference": reference,
                "book": passage_data.get("book"),
                "chapter": passage_data.get("chapter"),
                "start_verse": passage_data.get("start_verse"),
                "end_verse": passage_data.get("end_verse"),
                "object_ids": object_ids,
                "deterministic_only": canonical_action in DETERMINISTIC_ONLY_ACTIONS,
            },
        )

    def _resolve_passage(self, context: Mapping[str, Any]) -> dict[str, Any]:
        book = _first(context, "book", "reader_book")
        chapter = _first(context, "chapter", "reader_chapter")
        if not book or not chapter:
            raise ValueError("book and chapter are required for deterministic study actions")
        start_verse = _first(context, "start_verse", "verse_start", "reader_start_verse")
        end_verse = _first(context, "end_verse", "verse_end", "reader_end_verse")
        translation_id = str(_first(context, "translation", "reader_translation", "source_translation") or "asv")
        data = load_translation_bible(translation_id)
        try:
            resolved = resolve_passage(book, chapter, start_verse or None, end_verse or None, data=data)
        except BibleError:
            resolved = resolve_passage(book, chapter, start_verse or None, end_verse or None)
            translation_id = "asv"
        selected_text = str(_first(context, "selected_text", "reader_selected_text", "text") or "").strip()
        if selected_text:
            resolved["selected_text"] = selected_text
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

    def _word_study_sections(self, passage_data: Mapping[str, Any], *, query: str | None = None) -> list[dict[str, Any]]:
        haystack = " ".join(
            value
            for value in (
                query or "",
                str(passage_data.get("selected_text") or ""),
                str(passage_data.get("reference") or ""),
            )
            if value
        ).lower()
        entries = [
            entry
            for entry in load_lexical_entries().values()
            if _lexical_entry_matches(entry, haystack)
        ]
        if not entries:
            return []
        sections = []
        for entry in entries:
            label = entry.transliteration
            if entry.original:
                label = f"{entry.original} / {label}"
            items = [
                f"Language: {entry.language}",
                f"Glosses: {', '.join(entry.glosses)}",
                *entry.semantic_range,
            ]
            if entry.cautions:
                items.append("Cautions: " + " ".join(entry.cautions))
            if entry.notes:
                items.append(entry.notes)
            sections.append({"title": label, "items": items, "source": "deterministic"})
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
    for section in packet.get("sections") or []:
        title = str(section.get("title") or "Section")
        lines.extend(["", f"## {title}"])
        for item in section.get("items") or []:
            lines.append(f"- {item}")
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


def _lexical_entry_matches(entry: LexicalEntry, haystack: str) -> bool:
    candidates = [entry.key, entry.transliteration, *(entry.glosses or [])]
    if entry.original:
        candidates.append(entry.original)
    return any(candidate and str(candidate).lower() in haystack for candidate in candidates)


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
