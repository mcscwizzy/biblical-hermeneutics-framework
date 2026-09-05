"""CKL indexing for deterministic model-free retrieval."""

from __future__ import annotations

import logging
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Iterable, Mapping

from ..normalization import normalize_alias, normalize_id, normalize_text
from ..scripture import (
    ScriptureReferenceSpan,
    build_book_alias_lookup,
    format_scripture_reference,
    parse_scripture_references,
)
from ..schema import CanonicalObject, CanonicalValidationError, interpretive_note_texts
from ..schema.validator import validate_base_object
from .legacy import collect_field_search_terms
from .models import CKLIndexStats


LOGGER = logging.getLogger(__name__)
_INDEX_CACHE_LOCK = RLock()
_INDEX_CACHE: dict[str, tuple[str, CKLIndex]] = {}


@dataclass(frozen=True)
class IndexedCKLEntry:
    id: str
    category: str
    title: str
    aliases: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    scripture_references: list[str] = field(default_factory=list)
    summary: str = ""
    facts: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    related_entries: list[str] = field(default_factory=list)
    knowledge_layer: str | None = None
    source_path: str | None = None
    content_status: str | None = None
    review_status: str | None = None
    confidence: str | None = None
    importance: int = 0
    field_terms: dict[str, set[str]] = field(default_factory=dict)
    search_text: str = ""
    high_signal_text: str = ""
    scripture_spans: list[ScriptureReferenceSpan] = field(default_factory=list)
    related_edges: list[dict[str, Any]] = field(default_factory=list)
    normalized_title: str = ""
    normalized_aliases: list[str] = field(default_factory=list)
    normalized_keywords: list[str] = field(default_factory=list)
    normalized_themes: list[str] = field(default_factory=list)
    normalized_facts: list[str] = field(default_factory=list)
    temporal_scope: dict[str, Any] = field(default_factory=dict)
    evidence_temporal_relations_by_book: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "aliases": list(self.aliases),
            "keywords": list(self.keywords),
            "scripture_references": list(self.scripture_references),
            "summary": self.summary,
            "facts": list(self.facts),
            "themes": list(self.themes),
            "related_entries": list(self.related_entries),
            "knowledge_layer": self.knowledge_layer,
            "source_path": self.source_path,
            "content_status": self.content_status,
            "review_status": self.review_status,
            "confidence": self.confidence,
            "importance": self.importance,
            "temporal_scope": dict(self.temporal_scope),
            "evidence_temporal_relations_by_book": {
                book: list(values)
                for book, values in self.evidence_temporal_relations_by_book.items()
            },
        }


@dataclass
class CKLIndex:
    entries_by_id: dict[str, IndexedCKLEntry] = field(default_factory=dict)
    title_index: dict[str, set[str]] = field(default_factory=dict)
    alias_index: dict[str, set[str]] = field(default_factory=dict)
    keyword_index: dict[str, set[str]] = field(default_factory=dict)
    scripture_index: dict[str, set[str]] = field(default_factory=dict)
    category_index: dict[str, set[str]] = field(default_factory=dict)
    related_index: dict[str, set[str]] = field(default_factory=dict)
    reverse_related_index: dict[str, set[str]] = field(default_factory=dict)
    book_alias_lookup: dict[str, str] = field(default_factory=dict)
    stats: CKLIndexStats = field(default_factory=CKLIndexStats)

    @property
    def entry_count(self) -> int:
        return len(self.entries_by_id)

    @classmethod
    def from_library(cls, library: Any) -> "CKLIndex":
        start = time.perf_counter()
        ensure_loaded = getattr(library, "load", None)
        if callable(ensure_loaded):
            library = ensure_loaded()

        index = cls()
        objects = list(getattr(library, "objects_by_id", {}).values())
        index.book_alias_lookup = build_book_alias_lookup(
            obj for obj in objects if getattr(obj, "type", None) == "book"
        )

        scanned_files = _count_scanned_files(getattr(library, "objects_root", None))
        valid_count = 0
        invalid_count = 0

        for obj in objects:
            source_path = None
            source_path_for = getattr(library, "source_path_for", None)
            if callable(source_path_for):
                path = source_path_for(obj.id)
                if path is not None:
                    source_path = path.as_posix()
            try:
                validate_base_object(obj.to_dict(), path=source_path)
            except CanonicalValidationError as exc:
                LOGGER.error("Skipping invalid CKL entry during indexing: %s", exc)
                invalid_count += 1
                continue
            entry = _index_object(library, obj, index.book_alias_lookup)
            index.entries_by_id[entry.id] = entry
            index.title_index.setdefault(entry.normalized_title, set()).add(entry.id)
            for alias in entry.normalized_aliases:
                index.alias_index.setdefault(alias, set()).add(entry.id)
            for keyword in entry.normalized_keywords:
                index.keyword_index.setdefault(keyword, set()).add(entry.id)
            for reference in entry.scripture_spans:
                index.scripture_index.setdefault(reference.book, set()).add(entry.id)
            index.category_index.setdefault(entry.category, set()).add(entry.id)
            for related_id in entry.related_entries:
                index.related_index.setdefault(entry.id, set()).add(related_id)
                index.reverse_related_index.setdefault(related_id, set()).add(entry.id)

            valid_count += 1

        build_duration_ms = int((time.perf_counter() - start) * 1000)
        index.stats = CKLIndexStats(
            scanned_files=scanned_files,
            valid_documents=valid_count,
            invalid_documents=invalid_count,
            indexed_entries=len(index.entries_by_id),
            build_duration_ms=build_duration_ms,
        )
        LOGGER.info(
            "Built CKL index: scanned_files=%d valid_documents=%d invalid_documents=%d indexed_entries=%d build_duration_ms=%d",
            scanned_files,
            valid_count,
            invalid_count,
            len(index.entries_by_id),
            build_duration_ms,
        )
        return index

    @classmethod
    def from_root(cls, root: str | Path | None = None) -> "CKLIndex":
        from ..loader import CanonicalLibrary

        library = CanonicalLibrary(root=Path(root)) if root is not None else CanonicalLibrary.load_default()
        return cls.from_library(library)

    def iter_entries(self) -> Iterable[IndexedCKLEntry]:
        return self.entries_by_id.values()


def inventory_signature(root: str | Path | None = None) -> str:
    root_path = _resolve_root(root)
    payload: list[tuple[str, int, int, str]] = []
    for path in _inventory_paths(root_path):
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        payload.append((path.relative_to(root_path).as_posix(), stat.st_size, stat.st_mtime_ns, "json"))
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def inventory_content_signature(root: str | Path | None = None) -> str:
    """Hash authored inventory bytes without parsing or validating CKL objects."""

    root_path = _resolve_root(root)
    digest = hashlib.sha256()
    for path in _inventory_paths(root_path):
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            continue
        relative_path = path.relative_to(root_path).as_posix().encode("utf-8")
        digest.update(len(relative_path).to_bytes(8, "big"))
        digest.update(relative_path)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def load_index(root: str | Path | None = None, *, refresh: bool = False) -> CKLIndex:
    root_path = _resolve_root(root)
    root_key = root_path.resolve().as_posix()
    signature = inventory_signature(root_path)

    with _INDEX_CACHE_LOCK:
        cached = _INDEX_CACHE.get(root_key)
        if cached is not None and not refresh:
            cached_signature, cached_index = cached
            if cached_signature == signature:
                LOGGER.debug(
                    "Reusing cached CKL index: root=%s signature=%s entries=%d",
                    root_key,
                    signature,
                    cached_index.entry_count,
                )
                return cached_index

    index = CKLIndex.from_root(root_path)

    with _INDEX_CACHE_LOCK:
        _INDEX_CACHE[root_key] = (signature, index)

    return index


def refresh_index(root: str | Path | None = None) -> CKLIndex:
    return load_index(root, refresh=True)


def clear_index_cache(root: str | Path | None = None) -> None:
    with _INDEX_CACHE_LOCK:
        if root is None:
            _INDEX_CACHE.clear()
            return
        root_key = _resolve_root(root).resolve().as_posix()
        _INDEX_CACHE.pop(root_key, None)


def _index_object(
    library: Any,
    obj: CanonicalObject,
    book_alias_lookup: Mapping[str, str],
) -> IndexedCKLEntry:
    source_path = None
    source_path_for = getattr(library, "source_path_for", None)
    if callable(source_path_for):
        path = source_path_for(obj.id)
        if path is not None:
            source_path = path.as_posix()

    field_terms = _expand_field_search_terms(collect_field_search_terms(obj))
    evidence_search_values = [
        text
        for item in getattr(obj, "evidence_items", []) or []
        for text in (
            item.title,
            item.description,
            item.primary_observation,
            item.scholarly_interpretation,
            item.passage_relevance,
            item.confidence_rationale,
            item.evidence_type,
        )
        if text
    ]
    if evidence_search_values:
        field_terms["evidence_items"] = set(
            normalize_alias(" ".join(evidence_search_values)).split()
        )
    keywords = sorted({term for terms in field_terms.values() for term in terms})
    normalized_keywords = sorted({normalize_alias(keyword) for keyword in keywords if normalize_alias(keyword)})

    script_refs: list[str] = []
    scripture_spans: list[ScriptureReferenceSpan] = []
    for reference in getattr(obj, "scripture_references", []) or []:
        reference_text = str(getattr(reference, "reference", reference) or "").strip()
        if reference_text:
            for parsed in parse_scripture_references(reference_text, book_alias_lookup=book_alias_lookup):
                script_refs.append(format_scripture_reference(parsed))
                scripture_spans.append(parsed)

    evidence_temporal_relations_by_book: dict[str, list[str]] = {}
    for item in getattr(obj, "evidence_items", []) or []:
        for reference in item.scripture_references:
            for parsed in parse_scripture_references(
                reference.reference,
                book_alias_lookup=book_alias_lookup,
            ):
                script_refs.append(format_scripture_reference(parsed))
                scripture_spans.append(parsed)
                relations = evidence_temporal_relations_by_book.setdefault(parsed.book, [])
                if reference.temporal_relation not in relations:
                    relations.append(reference.temporal_relation)

    for claim in getattr(obj, "claims", []) or []:
        for reference in claim.scripture_references:
            for parsed in parse_scripture_references(
                reference,
                book_alias_lookup=book_alias_lookup,
            ):
                script_refs.append(format_scripture_reference(parsed))
                scripture_spans.append(parsed)

    related_edges = [_normalize_related_edge(item) for item in getattr(obj, "related_objects", []) or []]
    legacy_related_ids = (
        [str(item) for item in getattr(obj, "related_people", []) or []]
        + [str(item) for item in getattr(obj, "related_places", []) or []]
        + [str(item) for item in getattr(obj, "related_events", []) or []]
    )
    for related_id in legacy_related_ids:
        related_edges.append(
            {
                "id": normalize_id(related_id),
                "relationship": "related",
                "weight": 1,
                "notes": "",
            }
        )
    for item in getattr(obj, "evidence_items", []) or []:
        for relationship in item.related_objects:
            related_edges.append(_normalize_related_edge(relationship))

    related_entries = sorted(
        {
            str(edge["id"])
            for edge in related_edges
            if str(edge.get("id") or "").strip()
        }
    )

    facts = _entry_facts(obj)
    themes = _entry_themes(obj)
    knowledge_layers = getattr(obj, "knowledge_layers", {}) or {}
    knowledge_layer = (
        str(knowledge_layers.get("primary") or "")
        if isinstance(knowledge_layers, Mapping)
        else ""
    )

    search_parts = [
        str(getattr(obj, "id", "") or ""),
        str(getattr(obj, "title", "") or ""),
        " ".join(getattr(obj, "aliases", []) or []),
        " ".join(getattr(obj, "common_questions", []) or []),
        " ".join(getattr(obj, "related_entries", []) or []),
        " ".join(getattr(obj, "keywords", []) or []),
        str(getattr(obj, "summary", "") or ""),
        str(getattr(obj, "canonical_role", "") or ""),
        str(getattr(obj, "historical_context", "") or ""),
        str(getattr(obj, "ancient_near_east_context", "") or ""),
        str(getattr(obj, "hebraic_worldview", "") or ""),
        str(getattr(obj, "second_temple_context", "") or ""),
        str(getattr(obj, "canonical_context", "") or ""),
        str(getattr(obj, "later_christian_reception", "") or ""),
        str(getattr(obj, "literary_context", "") or ""),
        str(getattr(obj, "covenantal_significance", "") or ""),
        _metadata_text(getattr(obj, "canonical_story", {}) or {}),
        _metadata_text(getattr(obj, "hermeneutical_lens", {}) or {}),
        _metadata_text(getattr(obj, "retrieval_metadata", {}) or {}),
        _metadata_text(knowledge_layers),
        " ".join(facts),
        " ".join(themes),
        " ".join(script_refs),
        " ".join(related_entries),
        " ".join(evidence_search_values),
    ]
    search_text = normalize_text(" ".join(part for part in search_parts if part.strip()))
    high_signal_parts = [
        str(getattr(obj, "id", "") or ""),
        str(getattr(obj, "title", "") or ""),
        " ".join(getattr(obj, "aliases", []) or []),
        " ".join(script_refs),
    ]
    high_signal_text = normalize_text(" ".join(part for part in high_signal_parts if part.strip()))
    derived_aliases = _derived_normalized_aliases(obj)

    return IndexedCKLEntry(
        id=str(getattr(obj, "id")),
        category=str(getattr(obj, "type") or ""),
        title=str(getattr(obj, "title") or ""),
        aliases=list(getattr(obj, "aliases", []) or []),
        keywords=keywords,
        scripture_references=script_refs,
        summary=str(getattr(obj, "summary", "") or ""),
        facts=facts,
        themes=themes,
        related_entries=related_entries,
        knowledge_layer=knowledge_layer or None,
        source_path=source_path,
        content_status=str(getattr(obj, "content_status", "") or "") or None,
        review_status=str(getattr(obj, "review_status", "") or "") or None,
        confidence=str(getattr(obj, "confidence", "") or "") or None,
        importance=int(getattr(obj, "importance", 0) or 0),
        field_terms=field_terms,
        search_text=search_text,
        high_signal_text=high_signal_text,
        scripture_spans=scripture_spans,
        related_edges=related_edges,
        normalized_title=normalize_alias(str(getattr(obj, "title", "") or "")),
        normalized_aliases=[
            *[normalize_alias(alias) for alias in getattr(obj, "aliases", []) or [] if normalize_alias(alias)],
            *derived_aliases,
        ],
        normalized_keywords=normalized_keywords,
        normalized_themes=[normalize_alias(theme) for theme in themes if normalize_alias(theme)],
        normalized_facts=[normalize_alias(fact) for fact in facts if normalize_alias(fact)],
        temporal_scope=(
            obj.temporal_scope.to_dict()
            if hasattr(getattr(obj, "temporal_scope", None), "to_dict")
            else dict(getattr(obj, "temporal_scope", {}) or {})
        ),
        evidence_temporal_relations_by_book=evidence_temporal_relations_by_book,
    )


def _count_scanned_files(objects_root: Any) -> int:
    if not isinstance(objects_root, Path) or not objects_root.exists():
        return 0
    count = 0
    for path in objects_root.rglob("*.json"):
        if path.is_file() and not path.name.startswith("_"):
            count += 1
    return count


def _resolve_root(root: str | Path | None) -> Path:
    if root is None:
        return Path(__file__).resolve().parents[1]
    return Path(root)


def _inventory_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        paths.append(manifest_path)
    objects_root = root / "objects"
    if objects_root.exists():
        paths.extend(sorted(path for path in objects_root.rglob("*.json") if path.is_file()))
    return paths


def _normalize_related_edge(item: Any) -> dict[str, Any]:
    if hasattr(item, "to_dict"):
        item = item.to_dict()
    if not isinstance(item, Mapping):
        return {
            "id": normalize_id(str(item)),
            "relationship": "related",
            "weight": 1,
            "notes": "",
        }
    return {
        "id": normalize_id(str(item.get("id") or "")),
        "relationship": str(item.get("relationship") or "related"),
        "weight": int(item.get("weight") or 1),
        "notes": str(item.get("notes") or ""),
    }


def _metadata_text(value: Any) -> str:
    if not isinstance(value, Mapping):
        return ""
    parts: list[str] = []
    for item in value.values():
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, list):
            parts.extend(str(nested) for nested in item if isinstance(nested, str))
    return " ".join(parts)


def _entry_facts(obj: CanonicalObject) -> list[str]:
    candidates = [
        getattr(obj, "summary", ""),
        getattr(obj, "canonical_role", ""),
        getattr(obj, "historical_context", ""),
        getattr(obj, "ancient_near_east_context", ""),
        getattr(obj, "hebraic_worldview", ""),
        getattr(obj, "second_temple_context", ""),
        getattr(obj, "canonical_context", ""),
        getattr(obj, "later_christian_reception", ""),
        getattr(obj, "literary_context", ""),
        getattr(obj, "covenantal_significance", ""),
        _metadata_text(getattr(obj, "canonical_story", {}) or {}),
        _metadata_text(getattr(obj, "hermeneutical_lens", {}) or {}),
    ]
    candidates.extend(interpretive_note_texts(getattr(obj, "interpretive_notes", [])))
    for claim in getattr(obj, "claims", []) or []:
        if hasattr(claim, "to_dict"):
            claim = claim.to_dict()
        if not isinstance(claim, Mapping):
            continue
        candidates.extend(
            [
                str(claim.get("claim") or ""),
                str(claim.get("rationale") or ""),
                str(claim.get("notes") or ""),
            ]
        )
    for item in getattr(obj, "evidence_items", []) or []:
        candidates.extend(
            [
                item.title,
                item.description,
                item.primary_observation,
                item.scholarly_interpretation,
                item.passage_relevance,
                item.confidence_rationale,
            ]
        )
    candidates.extend(getattr(obj, "common_questions", []) or [])
    facts: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        text = str(value or "").strip()
        if not text:
            continue
        normalized = normalize_text(text)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        facts.append(text)
    return facts


def _entry_themes(obj: CanonicalObject) -> list[str]:
    values = getattr(obj, "themes", None)
    if isinstance(values, list):
        themes = [str(value).strip() for value in values if str(value).strip()]
        if themes:
            return themes
    if getattr(obj, "type", None) in {"theme", "theology"}:
        return [str(getattr(obj, "title", "") or "").strip()]
    return []


def _derived_normalized_aliases(obj: CanonicalObject) -> list[str]:
    title = normalize_alias(str(getattr(obj, "title", "") or ""))
    if not title:
        return []

    aliases: list[str] = []
    for alias in _derived_alias_overrides(title):
        if alias not in aliases:
            aliases.append(alias)
    if getattr(obj, "type", None) == "person":
        title_tokens = title.split()
        if len(title_tokens) >= 2 and title_tokens[0] not in {"the", "a", "an"}:
            aliases.append(title_tokens[0])
    return aliases


def _derived_alias_overrides(title: str) -> list[str]:
    overrides: dict[str, tuple[str, ...]] = {
        "shechem": ("sichem",),
    }
    return list(overrides.get(title, ()))


def _expand_field_search_terms(field_terms: Mapping[str, set[str]]) -> dict[str, set[str]]:
    expanded: dict[str, set[str]] = {}
    for field_name, terms in field_terms.items():
        expanded_terms: set[str] = set()
        for term in terms:
            normalized = normalize_alias(term)
            if not normalized:
                continue
            expanded_terms.add(normalized)
            singular = _singularize_term(normalized)
            if singular:
                expanded_terms.add(singular)
        if expanded_terms:
            expanded[field_name] = expanded_terms
    return expanded


def _singularize_term(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("sses") or token.endswith("shes") or token.endswith("ches") or token.endswith("xes") or token.endswith("zes"):
        return token[:-2]
    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]
    return token
