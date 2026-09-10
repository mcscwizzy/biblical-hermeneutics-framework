"""Versioned, fail-closed presentation of provenance verse references.

The reader-provenance binding remains the immutable source contract.  This
module derives renderer-facing reference strings only when a chapter-only
reference is mechanically proven to mean the whole current chapter.  It never
changes path identity, synthesis ancestry, evidence ancestry, confidence, or
dispute state.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from bhf_agent import bible
from bhf_agent.presentation.references import _BOOK_ALIASES
from framework.canonical_library.scripture import (
    format_scripture_reference,
    parse_scripture_reference,
)


RENDERER_REFERENCE_PRESENTATION_VERSION = "reader-provenance-renderer-reference-presentation-v1"
RENDERER_REFERENCE_PRESENTATION_IMPLEMENTATION = (
    "bhf_agent.chapter_commentary.renderer_reference_presentation_v1"
)
CANONICAL_BOUNDARY_SOURCE = "bhf_agent/data/asv_bible.json"

VALID_ALREADY = "VALID_ALREADY"
SAFE_FULL_CHAPTER_SCOPE = "SAFE_FULL_CHAPTER_SCOPE"
AMBIGUOUS = "AMBIGUOUS"
INVALID_SOURCE_REFERENCE = "INVALID_SOURCE_REFERENCE"

_VERSE_REF_RE = re.compile(r"^.+?\s+\d+:\d+(?:-\d+)?$")


class RendererReferencePresentationError(ValueError):
    """A renderer reference presentation cannot be proven safe."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def canonical_chapter_boundary(
    book: str,
    chapter: int,
    *,
    data: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a deterministic full-chapter range from the BHF Bible data."""

    chapter_data = bible.resolve_chapter(book, chapter, dict(data) if data else None)
    verses = [int(item["verse"]) for item in chapter_data.get("verses", [])]
    if not verses or verses[0] != 1 or len(set(verses)) != len(verses):
        raise RendererReferencePresentationError(
            "CANONICAL_CHAPTER_BOUNDARY_UNAVAILABLE",
            f"{book} {chapter} has no deterministic contiguous verse boundary",
        )
    verses = sorted(verses)
    if verses != list(range(1, verses[-1] + 1)):
        raise RendererReferencePresentationError(
            "CANONICAL_CHAPTER_BOUNDARY_UNAVAILABLE",
            f"{book} {chapter} has a non-contiguous canonical verse sequence",
        )
    canonical_book = str(chapter_data["book"])
    final_verse = verses[-1]
    return {
        "book": canonical_book,
        "chapter": int(chapter),
        "first_verse": 1,
        "final_verse": final_verse,
        "renderer_reference": bible.verse_range_reference(
            canonical_book, chapter, 1, final_verse
        ),
        "source": {
            "kind": "BHF_COMMITTED_CANONICAL_BIBLE_DATA",
            "path": CANONICAL_BOUNDARY_SOURCE,
            "identity": _sha256_bytes(bible.DATA_PATH.read_bytes()),
            "loader": "bhf_agent.bible.resolve_chapter",
        },
    }


def present_binding(
    binding: Mapping[str, Any],
    synthesis: Any,
    evidence_items: Iterable[Any] | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create an immutable derived renderer presentation for a v2 binding."""

    evidence = _mapping_by_id(evidence_items)
    units = _mapping_by_id(_objects(synthesis, "synthesis_units"))
    boundary = canonical_chapter_boundary(
        _text(binding, "book"), int(binding.get("chapter", 0))
    )
    paths: list[dict[str, Any]] = []
    for path in binding.get("paths", []):
        paths.append(_present_path(path, binding, units, evidence, boundary))
    base = {
        "artifact_version": RENDERER_REFERENCE_PRESENTATION_VERSION,
        "implementation_identity": RENDERER_REFERENCE_PRESENTATION_IMPLEMENTATION,
        "binding_version": _text(binding, "artifact_version"),
        "binding_hash": _text(binding, "binding_hash"),
        "reference": _text(binding, "reference"),
        "book": _text(binding, "book"),
        "chapter": int(binding.get("chapter", 0)),
        "canonical_boundary": boundary,
        "paths": paths,
    }
    return {**base, "presentation_hash": _sha256_json(base)}


def audit_active_paths(
    binding: Mapping[str, Any],
    synthesis: Any,
    evidence_items: Iterable[Any] | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify every active path without changing any source artifact."""

    presentation = present_binding(binding, synthesis, evidence_items)
    counts = {VALID_ALREADY: 0, SAFE_FULL_CHAPTER_SCOPE: 0, AMBIGUOUS: 0, INVALID_SOURCE_REFERENCE: 0}
    affected = {key: [] for key in counts}
    for path in presentation["paths"]:
        classification = path["canonicalization"]["classification"]
        counts[classification] += 1
        affected[classification].append(path["path_id"])
    return {
        "artifact_version": f"{RENDERER_REFERENCE_PRESENTATION_VERSION}-audit",
        "presentation_hash": presentation["presentation_hash"],
        "counts": counts,
        "affected_path_ids": affected,
        "paths": presentation["paths"],
    }


def add_presentation_to_prompt(
    existing_prompt: str,
    envelope: Mapping[str, Any],
    binding: Mapping[str, Any],
    synthesis: Any,
    evidence_items: Iterable[Any] | Mapping[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Replace only the v2 renderer catalog with the versioned presentation."""

    marker = "READER PROVENANCE BINDING"
    if marker not in existing_prompt:
        raise RendererReferencePresentationError(
            "PROVENANCE_PRESENTATION_INPUT_MISMATCH",
            "the v2 prompt catalog is missing",
        )
    presentation = present_binding(binding, synthesis, evidence_items)
    prefix = existing_prompt.split(marker, 1)[0].rstrip()
    return prefix + "\n\n" + _render_section(envelope, presentation) + "\n", presentation


def normalize_selected_chapter_scope_refs(
    payload: Mapping[str, Any],
    binding: Mapping[str, Any],
    presentation: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Safely normalize chapter-only output only for selected proven paths."""

    normalized = copy.deepcopy(dict(payload))
    by_id = {path["path_id"]: path for path in presentation.get("paths", [])}
    events: list[dict[str, Any]] = []
    for section in normalized.get("sections", []):
        if not isinstance(section, Mapping):
            continue
        for block in section.get("blocks", []):
            if not isinstance(block, Mapping):
                continue
            selected_ids = block.get("provenance_refs")
            if not isinstance(selected_ids, list) or not selected_ids:
                continue
            selected = [by_id.get(path_id) for path_id in selected_ids]
            if any(path is None for path in selected):
                continue
            safe = [path for path in selected if path and path["canonicalization"]["classification"] == SAFE_FULL_CHAPTER_SCOPE]
            if len(safe) != len(selected) or not safe:
                continue
            renderer_refs = {ref for path in safe for ref in path["renderer_verse_refs"]}
            source_refs = {ref for path in safe for ref in path["source_verse_refs"]}
            if len(renderer_refs) != 1 or len(source_refs) != 1:
                continue
            renderer_ref = next(iter(renderer_refs))
            source_ref = next(iter(source_refs))
            refs = block.get("verse_refs")
            if not isinstance(refs, list):
                continue
            for index, value in enumerate(refs):
                if value != source_ref:
                    continue
                block["verse_refs"][index] = renderer_ref  # type: ignore[index]
                for path in safe:
                    events.append(
                        {
                            "code": "CHAPTER_SCOPE_REFERENCE_EXPANDED",
                            "path": f"block.verse_refs[{index}]",
                            "source_reference": source_ref,
                            "renderer_reference": renderer_ref,
                            "book": presentation["book"],
                            "chapter": presentation["chapter"],
                            "final_verse": presentation["canonical_boundary"]["final_verse"],
                            "reason": "selected CURRENT_CHAPTER path is proven whole-chapter scope",
                            "source_provenance_path_id": path["path_id"],
                        }
                    )
    return normalized, events


def _present_path(
    path: Mapping[str, Any],
    binding: Mapping[str, Any],
    units: Mapping[str, Any],
    evidence: Mapping[str, Any],
    boundary: Mapping[str, Any],
) -> dict[str, Any]:
    path_data = path.get("path") if isinstance(path.get("path"), Mapping) else {}
    source_refs = [str(value) for value in path_data.get("verse_refs", [])]
    classification, reason = _classify(
        source_refs, path_data, binding, units.get(path.get("synthesis_id")), evidence, boundary
    )
    renderer_refs = (
        [boundary["renderer_reference"]] * len(source_refs)
        if classification == SAFE_FULL_CHAPTER_SCOPE
        else list(source_refs)
    )
    return {
        "path_id": _text(path, "path_id"),
        "synthesis_id": _text(path, "synthesis_id"),
        "path_class": _text(path, "path_class") or "priority",
        "passage_scope": _text(path_data, "passage_scope"),
        "source_verse_refs": source_refs,
        "renderer_verse_refs": renderer_refs,
        "canonicalization": {
            "classification": classification,
            "reason": reason,
            "source_reference_preserved": True,
            "canonical_boundary_source": boundary["source"],
        },
    }


def _classify(
    source_refs: list[str],
    path_data: Mapping[str, Any],
    binding: Mapping[str, Any],
    unit: Any,
    evidence: Mapping[str, Any],
    boundary: Mapping[str, Any],
) -> tuple[str, str]:
    if not source_refs:
        return INVALID_SOURCE_REFERENCE, "path has no source verse references"
    parsed = []
    for reference in source_refs:
        span = parse_scripture_reference(reference, book_alias_lookup=_BOOK_ALIASES)
        if span is None:
            return INVALID_SOURCE_REFERENCE, f"source reference is not parseable: {reference}"
        parsed.append(span)
    expected = parse_scripture_reference(_text(binding, "reference"), book_alias_lookup=_BOOK_ALIASES)
    if expected is None or expected.start_verse is not None:
        return INVALID_SOURCE_REFERENCE, "binding reference is not an unambiguous chapter reference"
    canonical_expected = (expected.book, expected.start_chapter)
    if any((span.book, span.start_chapter) != canonical_expected for span in parsed):
        return AMBIGUOUS, "source reference does not exactly match the current chapter"
    if _text(path_data, "passage_scope") != "CURRENT_CHAPTER":
        return AMBIGUOUS, "chapter-only reference is not CURRENT_CHAPTER scope"
    if not isinstance(unit, Mapping) and not hasattr(unit, "passage_scope"):
        return INVALID_SOURCE_REFERENCE, "synthesis unit for path is unavailable"
    if _text(unit, "passage_scope") != "CURRENT_CHAPTER":
        return AMBIGUOUS, "underlying synthesis unit is not chapter scope"
    has_verse = any(span.start_verse is not None for span in parsed)
    has_chapter_only = any(span.start_verse is None for span in parsed)
    if has_verse and has_chapter_only:
        return AMBIGUOUS, "mixed chapter-only and verse-specific references prevent expansion"
    if has_verse:
        if all(_valid_verse_reference(span, reference, boundary) for span, reference in zip(parsed, source_refs, strict=True)):
            return VALID_ALREADY, "all source references are canonical verse-level references"
        return INVALID_SOURCE_REFERENCE, "a source verse reference is outside the canonical chapter"
    if any(format_scripture_reference(span) != _text(binding, "reference") for span in parsed):
        return AMBIGUOUS, "chapter-only source reference is not canonical current-chapter identity"
    unit_refs = _sequence(unit, "verse_refs")
    if unit_refs != source_refs:
        return AMBIGUOUS, "path references do not exactly match the synthesis scope"
    anchors = _sequence(unit, "source_anchors") + _evidence_anchors(path_data, evidence)
    if any(_has_verse_component(anchor) for anchor in anchors):
        return AMBIGUOUS, "a competing verse-specific anchor narrows the source scope"
    if any(not _is_exact_chapter(anchor, binding) for anchor in anchors):
        return AMBIGUOUS, "a source anchor is not the exact current chapter"
    return SAFE_FULL_CHAPTER_SCOPE, "explicit whole-current-chapter scope has deterministic boundaries"


def _render_section(envelope: Mapping[str, Any], presentation: Mapping[str, Any]) -> str:
    lines = [
        "READER PROVENANCE BINDING",
        "",
        f"Binding version: {_text(presentation, 'binding_version')}",
        f"Reference presentation: {RENDERER_REFERENCE_PRESENTATION_VERSION}",
        "Choose one or more complete provenance_refs for each prose block.",
        "BHF resolves each selected path to canonical synthesis_ids and evidence_ids after generation.",
        "Do not choose or emit synthesis_ids or evidence_ids manually.",
        "Only path IDs listed below are valid for this chapter.",
        "",
    ]
    lines.extend([
        "SOURCE SCOPE AND RENDERER SERIALIZATION:",
        "source_verse_refs preserves the exact synthesis/provenance scope. renderer_verse_refs is the",
        "validator-legal serialization of that same scope only when the presentation audit proves exact",
        "whole-chapter equivalence. Do not narrow or invent a verse reference.",
        "",
    ])
    for path in presentation.get("paths", []):
        lines.append(
            "- "
            + json.dumps(
                {
                    "provenance_ref": path["path_id"],
                    "path_class": path["path_class"],
                    "synthesis_unit": path["synthesis_id"],
                    "passage_scope": path["passage_scope"],
                    "source_verse_refs": path["source_verse_refs"],
                    "renderer_verse_refs": path["renderer_verse_refs"],
                    "canonicalization": path["canonicalization"]["classification"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    lines.extend(
        [
            "",
            "OUTPUT ENVELOPE NOTE:",
            "Use the supplied renderer_verse_refs for ordinary block verse_refs. The source scope remains",
            "the source_verse_refs shown above. Never invent a narrower verse or copy a chapter-only value",
            "when a renderer_verse_refs value is supplied.",
            "",
            'In every block, use exactly this field: "provenance_refs": ["<listed path ID>"]',
            "Do not emit any path ID from another chapter or invent one.",
        ]
    )
    return "\n".join(lines)


def _valid_verse_reference(span: Any, raw: str, boundary: Mapping[str, Any]) -> bool:
    return (
        _VERSE_REF_RE.fullmatch(raw) is not None
        and format_scripture_reference(span) == raw
        and span.book == boundary["book"]
        and span.start_chapter == boundary["chapter"]
        and span.start_verse is not None
        and span.end_chapter in (None, span.start_chapter)
        and (span.end_verse or span.start_verse) <= boundary["final_verse"]
    )


def _has_verse_component(reference: str) -> bool:
    span = parse_scripture_reference(reference, book_alias_lookup=_BOOK_ALIASES)
    return span is None or span.start_verse is not None


def _is_exact_chapter(reference: str, binding: Mapping[str, Any]) -> bool:
    span = parse_scripture_reference(reference, book_alias_lookup=_BOOK_ALIASES)
    return bool(
        span
        and span.book.casefold() == _text(binding, "book").casefold()
        and span.start_chapter == int(binding.get("chapter", 0))
        and span.start_verse is None
        and span.end_chapter is None
    )


def _evidence_anchors(path_data: Mapping[str, Any], evidence: Mapping[str, Any]) -> list[str]:
    anchors: list[str] = []
    for evidence_id in path_data.get("evidence_ids", []):
        item = evidence.get(str(evidence_id))
        anchors.extend(_sequence(item, "passage_anchors"))
    return anchors


def _mapping_by_id(values: Iterable[Any] | Mapping[str, Any] | None) -> dict[str, Any]:
    if values is None:
        return {}
    if isinstance(values, Mapping):
        return {str(key): value for key, value in values.items()}
    return {_text(value, "id"): value for value in values}


def _objects(value: Any, field: str) -> list[Any]:
    raw = value.get(field) if isinstance(value, Mapping) else getattr(value, field, [])
    return list(raw or [])


def _sequence(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    raw = value.get(field) if isinstance(value, Mapping) else getattr(value, field, [])
    return [str(item) for item in (raw or [])]


def _text(value: Any, field: str) -> str:
    if value is None:
        return ""
    raw = value.get(field) if isinstance(value, Mapping) else getattr(value, field, "")
    return str(raw or "")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
