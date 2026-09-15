"""Versioned renderer provenance binding with a narrow renderability bridge.

Reader-level projection is a prioritization contract, not an exhaustive index
of safe citation capability.  Binding v2 preserves the v1 projected paths and
adds content-addressed fallback paths only for chapters with no projected
priority paths and at least one independently renderable synthesis unit.

The canonical commentary schema is unchanged.  Renderers select path IDs;
this module remains authoritative for resolving those IDs to synthesis and
evidence ancestry.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .reader_provenance_binding import (
    READER_PROVENANCE_BINDING_VERSION as V1_VERSION,
    build_provenance_binding as build_v1_provenance_binding,
)


READER_PROVENANCE_BINDING_V2_VERSION = "reader-provenance-binding-v2"
READER_PROVENANCE_BINDING_V2_IMPLEMENTATION = (
    "bhf_agent.chapter_commentary.reader_provenance_binding_v2"
)

_READER_PATH_ID_RE = re.compile(r"^reader_path_[a-z0-9_]+_[0-9]{3}_[0-9a-f]{24}$")
_FALLBACK_PATH_ID_RE = re.compile(r"^render_path_[a-z0-9_]+_[0-9a-f]{24}$")
_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
_INTERPRETATION_LEVELS = frozenset({"fact", "inference", "disputed"})
_PASSAGE_SCOPES = frozenset({"CURRENT_CHAPTER", "SURROUNDING_PASSAGE"})
_KINDS = frozenset(
    {
        "chapter_overview",
        "historical_context",
        "cultural_context",
        "people_places",
        "archaeology_geography",
        "language_literary",
        "chronology",
        "surrounding_passages",
        "interpretive_questions",
        "things_easy_to_miss",
        "why_it_matters",
    }
)
_DISPUTED_LEVELS = frozenset(
    {"disputed", "speculative", "insufficient_evidence", "contested", "uncertain"}
)


class ProvenanceBindingV2Error(ValueError):
    """A v2 provenance path cannot be safely built or resolved."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def build_provenance_binding_v2(
    envelope: Mapping[str, Any],
    synthesis: Any,
    evidence_items: Iterable[Any] | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build priority paths and, only when needed, fallback renderability paths.

    The priority path objects are copied byte-for-byte from the frozen v1
    binding.  Fallback paths are derived from the compiled synthesis unit and
    its own evidence IDs; no reader idea or parentage is created.
    """

    v1 = build_v1_provenance_binding(envelope)
    priority_paths = copy.deepcopy(v1["paths"])
    fallback_paths: list[dict[str, Any]] = []
    units = _sequence_objects(synthesis, "synthesis_units")
    evidence = _mapping_by_id(evidence_items)
    if not priority_paths:
        for unit in units:
            if _fallback_eligible(unit, synthesis, evidence):
                fallback_paths.append(
                    _fallback_path(envelope, unit, evidence, synthesis)
                )

    active_paths = priority_paths if priority_paths else fallback_paths
    synthesis_ancestry = {
        _text(unit, "id"): _sequence(unit, "evidence_ids") for unit in units
    }
    for path in active_paths:
        if path["synthesis_id"] not in synthesis_ancestry or list(
            path["evidence_ids"]
        ) != synthesis_ancestry[path["synthesis_id"]]:
            raise ProvenanceBindingV2Error(
                "PROVENANCE_PATH_IDENTITY_MISMATCH",
                f"path {path['path_id']} does not match exact synthesis ancestry",
            )
    base = {
        "artifact_version": READER_PROVENANCE_BINDING_V2_VERSION,
        "implementation_identity": READER_PROVENANCE_BINDING_V2_IMPLEMENTATION,
        "reference": _text(envelope, "reference"),
        "book": _text(envelope, "book"),
        "chapter": int(envelope.get("chapter", 0)),
        "envelope_version": _text(envelope, "artifact_version"),
        "envelope_hash": _text(envelope, "envelope_hash"),
        "v1_binding_version": V1_VERSION,
        "v1_binding_hash": v1["binding_hash"],
        "priority_paths": priority_paths,
        "fallback_renderable_paths": fallback_paths,
        "paths": active_paths,
        "synthesis_ancestry": synthesis_ancestry,
        "binding_audit": {
            "priority_path_count": len(priority_paths),
            "fallback_renderable_path_count": len(fallback_paths),
            "active_path_count": len(active_paths),
            "fallback_paths_active": not priority_paths and bool(fallback_paths),
            "fallback_paths_suppressed_when_priority_exists": bool(priority_paths),
            "fallback_eligible_synthesis_ids": [
                path["synthesis_id"] for path in fallback_paths
            ],
            "synthetic_reader_idea_created": False,
            "synthetic_parentage_created": False,
            "cross_synthesis_evidence_leakage": [],
        },
    }
    return {**base, "binding_hash": _sha256_json(base)}


def audit_provenance_binding_v2(
    binding: Mapping[str, Any],
    envelope: Mapping[str, Any],
    synthesis: Any,
    evidence_items: Iterable[Any] | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild a v2 binding and compare its immutable definition."""

    try:
        expected = build_provenance_binding_v2(envelope, synthesis, evidence_items)
    except ProvenanceBindingV2Error as exc:
        return {"valid": False, "failure_code": exc.code, "failure": str(exc)}
    actual_base = {key: value for key, value in binding.items() if key != "binding_hash"}
    expected_base = {key: value for key, value in expected.items() if key != "binding_hash"}
    expected_hash = _sha256_json(actual_base)
    hash_valid = binding.get("binding_hash") == expected_hash
    shape_matches = actual_base == expected_base
    return {
        "valid": hash_valid and shape_matches,
        "binding_hash": binding.get("binding_hash"),
        "expected_binding_hash": expected_hash,
        "hash_valid": hash_valid,
        "shape_matches_deterministic_rebuild": shape_matches,
        "failure_code": None if hash_valid and shape_matches else "PROVENANCE_PATH_IDENTITY_MISMATCH",
    }


def resolve_provenance_refs_v2(
    provenance_refs: Any,
    binding: Mapping[str, Any],
    *,
    section_kind: str | None = None,
) -> dict[str, Any]:
    """Resolve only active, listed paths and retain each path's exact ancestry."""

    _assert_binding_v2(binding)
    if not isinstance(provenance_refs, list) or not provenance_refs:
        raise ProvenanceBindingV2Error(
            "MALFORMED_PROVENANCE_REFERENCE",
            "provenance_refs must be a non-empty array",
        )
    if any(not isinstance(value, str) or not value for value in provenance_refs):
        raise ProvenanceBindingV2Error(
            "MALFORMED_PROVENANCE_REFERENCE",
            "every provenance reference must be a non-empty string",
        )
    if len(set(provenance_refs)) != len(provenance_refs):
        raise ProvenanceBindingV2Error(
            "DUPLICATE_PROVENANCE_REFERENCE",
            "a block may not repeat a provenance path",
        )

    by_id = {path["path_id"]: path for path in binding.get("paths", [])}
    selected: list[dict[str, Any]] = []
    scope = _scope(binding)
    for path_id in provenance_refs:
        if not (_READER_PATH_ID_RE.fullmatch(path_id) or _FALLBACK_PATH_ID_RE.fullmatch(path_id)):
            raise ProvenanceBindingV2Error(
                "MALFORMED_PROVENANCE_REFERENCE",
                f"invalid provenance path format: {path_id}",
            )
        path = by_id.get(path_id)
        if path is None:
            prefix = "reader_path_" if path_id.startswith("reader_path_") else "render_path_"
            if not path_id.startswith(f"{prefix}{scope}_"):
                raise ProvenanceBindingV2Error(
                    "OUT_OF_CHAPTER_PROVENANCE_PATH",
                    f"path {path_id} is not scoped to {_text(binding, 'reference')}",
                )
            raise ProvenanceBindingV2Error(
                "UNKNOWN_PROVENANCE_PATH", f"path {path_id} is not in the current binding"
            )
        selected.append(path)

    _validate_combination(selected, section_kind)
    synthesis_ids = _unique(path["synthesis_id"] for path in selected)
    evidence_ids = _unique(
        evidence_id for path in selected for evidence_id in path["evidence_ids"]
    )
    for path in selected:
        if path["synthesis_id"] not in synthesis_ids or not set(path["evidence_ids"]).issubset(evidence_ids):
            raise ProvenanceBindingV2Error(
                "PROVENANCE_PATH_IDENTITY_MISMATCH",
                f"resolved path {path['path_id']} lost its own ancestry",
            )
    return {
        "provenance_refs": list(provenance_refs),
        "paths": copy.deepcopy(selected),
        "path_classes": [path.get("path_class", "priority") for path in selected],
        "reader_idea_ids": _unique(
            path["reader_idea_id"]
            for path in selected
            if path.get("reader_idea_id")
        ),
        "synthesis_ids": synthesis_ids,
        "evidence_ids": evidence_ids,
    }


def normalize_renderer_payload_v2(
    payload: Mapping[str, Any], binding: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve path-only output into the unchanged canonical commentary fields."""

    _assert_binding_v2(binding)
    normalized = copy.deepcopy(dict(payload))
    block_records: list[dict[str, Any]] = []
    sections = normalized.get("sections", [])
    if not isinstance(sections, list):
        raise ProvenanceBindingV2Error(
            "MALFORMED_PROVENANCE_REFERENCE", "sections must be an array"
        )
    for section_index, section in enumerate(sections):
        if not isinstance(section, Mapping):
            continue
        blocks = section.get("blocks", [])
        if not isinstance(blocks, list):
            continue
        for block_index, block in enumerate(blocks):
            if not isinstance(block, Mapping):
                continue
            if "synthesis_ids" in block or "evidence_ids" in block:
                raise ProvenanceBindingV2Error(
                    "PROVENANCE_PATH_IDENTITY_MISMATCH",
                    f"section[{section_index}].block[{block_index}] must not author canonical IDs",
                )
            if "provenance_refs" not in block:
                raise ProvenanceBindingV2Error(
                    "MISSING_PROVENANCE_REFERENCES",
                    f"section[{section_index}].block[{block_index}] has no provenance_refs",
                )
            resolved = resolve_provenance_refs_v2(
                block["provenance_refs"], binding, section_kind=_text(section, "kind")
            )
            block["synthesis_ids"] = resolved["synthesis_ids"]
            block["evidence_ids"] = resolved["evidence_ids"]
            block.pop("provenance_refs", None)
            block_records.append(
                {
                    "section_index": section_index,
                    "block_index": block_index,
                    "block_id": block.get("id"),
                    "provenance_refs": resolved["provenance_refs"],
                    "path_classes": resolved["path_classes"],
                    "reader_idea_ids": resolved["reader_idea_ids"],
                    "synthesis_ids": resolved["synthesis_ids"],
                    "evidence_ids": resolved["evidence_ids"],
                    "exact_paths": resolved["paths"],
                }
            )
    metadata = {
        "artifact_version": READER_PROVENANCE_BINDING_V2_VERSION,
        "binding_hash": binding["binding_hash"],
        "block_count": len(block_records),
        "blocks": block_records,
    }
    return normalized, metadata


def response_ancestry_audit_v2(
    response: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    """Audit canonical IDs against the exact active paths used by v2."""

    _assert_binding_v2(binding)
    paths_by_synthesis: dict[str, list[dict[str, Any]]] = {}
    for path in binding.get("paths", []):
        paths_by_synthesis.setdefault(path["synthesis_id"], []).append(path)
    blocks: list[dict[str, Any]] = []
    for section_index, section in enumerate(response.get("sections", [])):
        if not isinstance(section, Mapping):
            continue
        for block_index, block in enumerate(section.get("blocks", [])):
            if not isinstance(block, Mapping):
                continue
            synthesis_ids = [str(value) for value in block.get("synthesis_ids", [])]
            evidence_ids = [str(value) for value in block.get("evidence_ids", [])]
            cited_paths = [
                path
                for synthesis_id in synthesis_ids
                for path in paths_by_synthesis.get(synthesis_id, [])
            ]
            owners = {
                evidence_id: sorted(
                    {
                        path["synthesis_id"]
                        for path in cited_paths
                        if evidence_id in path.get("evidence_ids", [])
                    }
                )
                for evidence_id in evidence_ids
            }
            outside = sorted(eid for eid, owner_ids in owners.items() if not owner_ids)
            blocks.append(
                {
                    "section_index": section_index,
                    "block_index": block_index,
                    "block_id": block.get("id"),
                    "cited_synthesis_ids": synthesis_ids,
                    "cited_evidence_ids": evidence_ids,
                    "evidence_path_owners": owners,
                    "evidence_outside_cited_paths": outside,
                    "ancestry_valid": not outside,
                }
            )
    return {
        "block_count": len(blocks),
        "blocks": blocks,
        "ancestry_mismatch_count": sum(bool(block["evidence_outside_cited_paths"]) for block in blocks),
        "valid": all(block["ancestry_valid"] for block in blocks),
    }


def render_provenance_binding_section_v2(
    envelope: Mapping[str, Any], binding: Mapping[str, Any]
) -> str:
    """Render only the active path class while retaining machine-facing detail."""

    _assert_binding_v2(binding)
    priority = binding.get("priority_paths", [])
    fallback = binding.get("fallback_renderable_paths", [])
    lines = [
        "READER PROVENANCE BINDING",
        "",
        f"Binding version: {READER_PROVENANCE_BINDING_V2_VERSION}",
        "Choose one or more complete provenance_refs for each prose block.",
        "BHF resolves each selected path to canonical synthesis_ids and evidence_ids after generation.",
        "Do not choose or emit synthesis_ids or evidence_ids manually.",
        "Only path IDs listed below are valid for this chapter.",
        "",
    ]
    if priority:
        lines.extend(
            [
                "Priority paths are projected reader-level CORE/RELEVANT ancestry and are preferred.",
                "This chapter has no active fallback paths because priority paths are available.",
                "",
            ]
        )
    elif fallback:
        lines.extend(
            [
                "There are no projected reader-priority provenance paths for this chapter.",
                "The fallback paths below represent exact synthesis/evidence ancestry that remains",
                "legally renderable under Prompt 1.8. They are renderability-only paths, not CORE or",
                "RELEVANT ideas. Use only what materially helps, preserve dispute/confidence status,",
                "and produce the smallest useful supported commentary.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "No priority or fallback renderability paths are available; sections may be empty",
                "only under the existing no-legally-renderable-content rules.",
                "",
            ]
        )
    for path in binding.get("paths", []):
        data = path["path"]
        lines.append(
            "- "
            + json.dumps(
                {
                    "provenance_ref": path["path_id"],
                    "path_class": path.get("path_class", "priority"),
                    "synthesis_unit": path["synthesis_id"],
                    "kind": data.get("kind"),
                    "passage_scope": data.get("passage_scope"),
                    "verse_refs": data.get("verse_refs", []),
                    "confidence": data.get("synthesis_confidence"),
                    "interpretation_level": data.get("interpretation_level"),
                    "disputed": data.get("disputed"),
                    "evidence_count": len(path["evidence_ids"]),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    lines.extend(
        [
            "",
            "OUTPUT ENVELOPE NOTE:",
            "The example object above defines field structure only; its example values are illustrative.",
            "Use the actual supplied chapter contract for kind, confidence, interpretation_level, verse_refs,",
            "and provenance_refs. Do not copy example values when they conflict with the supplied ancestry.",
            "",
            "PROVENANCE OUTPUT ADAPTER:",
            'In every block, use exactly this field: "provenance_refs": ["<listed path ID>"]',
            "Do not emit any path ID from another chapter or invent one.",
        ]
    )
    return "\n".join(lines)


def add_provenance_binding_to_prompt_v2(
    existing_prompt: str, envelope: Mapping[str, Any], binding: Mapping[str, Any]
) -> str:
    """Append the v2 selection adapter without changing Prompt 1.8 itself."""

    if "READER PROVENANCE BINDING" in existing_prompt:
        raise ProvenanceBindingV2Error(
            "PROVENANCE_PATH_IDENTITY_MISMATCH", "prompt already contains a provenance binding"
        )
    return existing_prompt.rstrip() + "\n\n" + render_provenance_binding_section_v2(envelope, binding) + "\n"


def _fallback_eligible(unit: Any, synthesis: Any, evidence: Mapping[str, Any]) -> bool:
    """Conservatively mirror existing synthesis/renderer legality constraints."""

    synthesis_availability = _text(synthesis, "evidence_availability")
    if synthesis_availability == "DATA_GAP":
        return False
    unit_id = _text(unit, "id")
    kind = _text(unit, "kind")
    scope = _text(unit, "passage_scope")
    confidence = _text(unit, "confidence")
    interpretation = _text(unit, "interpretation_level")
    evidence_ids = _sequence(unit, "evidence_ids")
    verse_refs = _sequence(unit, "verse_refs")
    if not unit_id or kind not in _KINDS or scope not in _PASSAGE_SCOPES:
        return False
    if confidence not in _CONFIDENCE_RANK or interpretation not in _INTERPRETATION_LEVELS:
        return False
    if not evidence_ids or len(set(evidence_ids)) != len(evidence_ids):
        return False
    if not evidence or any(evidence_id not in evidence for evidence_id in evidence_ids):
        return False
    supported = [evidence[evidence_id] for evidence_id in evidence_ids]
    if any(_confidence_rank(_text(item, "confidence")) < _confidence_rank(confidence) for item in supported):
        return False
    disputed = interpretation in _DISPUTED_LEVELS or any(_evidence_disputed(item) for item in supported)
    if interpretation == "fact" and disputed:
        return False
    if scope == "CURRENT_CHAPTER":
        if not verse_refs:
            return False
        if any(not _is_current_chapter_reference(ref, _text(synthesis, "book"), int(_value(synthesis, "chapter", 0))) for ref in verse_refs):
            return False
    if scope == "SURROUNDING_PASSAGE" and kind != "surrounding_passages":
        return False
    return True


def _fallback_path(
    envelope: Mapping[str, Any],
    unit: Any,
    evidence: Mapping[str, Any],
    synthesis: Any,
) -> dict[str, Any]:
    path = _unit_path(unit, evidence, synthesis)
    basis = {
        "artifact_version": READER_PROVENANCE_BINDING_V2_VERSION,
        "path_class": "fallback_renderable",
        "reference": _text(envelope, "reference"),
        "book": _text(envelope, "book"),
        "chapter": int(envelope.get("chapter", 0)),
        "synthesis_id": path["synthesis_id"],
        "path": path,
    }
    path_hash = _sha256_json(basis)
    return {
        "path_id": f"render_path_{_scope(envelope)}_{path_hash[:24]}",
        "path_hash": path_hash,
        "path_class": "fallback_renderable",
        "synthesis_id": path["synthesis_id"],
        "evidence_ids": list(path["evidence_ids"]),
        "path": path,
    }


def _unit_path(unit: Any, evidence: Mapping[str, Any], synthesis: Any) -> dict[str, Any]:
    interpretation = _text(unit, "interpretation_level")
    disputed = interpretation in _DISPUTED_LEVELS or any(
        _evidence_disputed(evidence[evidence_id])
        for evidence_id in _sequence(unit, "evidence_ids")
        if evidence_id in evidence
    )
    return {
        "synthesis_id": _text(unit, "id"),
        "evidence_ids": _sequence(unit, "evidence_ids"),
        "synthesis_confidence": _text(unit, "confidence"),
        "interpretation_level": interpretation,
        "disputed": disputed,
        "passage_scope": _text(unit, "passage_scope"),
        "kind": _text(unit, "kind"),
        "verse_refs": _sequence(unit, "verse_refs"),
        "source_anchors": _sequence(unit, "source_anchors"),
        "ancestry_hashes": {
            "evidence_hash": _text(synthesis, "evidence_hash"),
            "synthesis_hash": _text(synthesis, "synthesis_hash"),
        },
    }


def _assert_binding_v2(binding: Mapping[str, Any]) -> None:
    if not isinstance(binding, Mapping) or _text(binding, "artifact_version") != READER_PROVENANCE_BINDING_V2_VERSION:
        raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "unsupported binding version")
    if binding.get("binding_hash") != _sha256_json({key: value for key, value in binding.items() if key != "binding_hash"}):
        raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "binding identity hash does not match")
    priority = list(binding.get("priority_paths", []))
    fallback = list(binding.get("fallback_renderable_paths", []))
    active = list(binding.get("paths", []))
    if priority and fallback:
        raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "fallback paths must be suppressed when priority paths exist")
    if active != (priority if priority else fallback):
        raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "active paths do not match the selected path class")
    scope = _scope(binding)
    ids: set[str] = set()
    hashes: set[str] = set()
    for path in priority:
        if not _READER_PATH_ID_RE.fullmatch(_text(path, "path_id")) or not _text(path, "path_id").startswith(f"reader_path_{scope}_"):
            raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "priority path is not chapter-scoped")
        ids.add(path["path_id"])
        hashes.add(path.get("path_hash", ""))
    for path in fallback:
        path_id = _text(path, "path_id")
        if not _FALLBACK_PATH_ID_RE.fullmatch(path_id) or not path_id.startswith(f"render_path_{scope}_"):
            raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "fallback path is not chapter-scoped")
        if path.get("path_class") != "fallback_renderable" or path.get("reader_idea_id"):
            raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "fallback path has reader-level identity")
        path_data = path.get("path")
        if not isinstance(path_data, Mapping) or path.get("synthesis_id") != path_data.get("synthesis_id") or list(path.get("evidence_ids", [])) != list(path_data.get("evidence_ids", [])):
            raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "fallback ancestry was altered")
        basis = {
            "artifact_version": READER_PROVENANCE_BINDING_V2_VERSION,
            "path_class": "fallback_renderable",
            "reference": _text(binding, "reference"),
            "book": _text(binding, "book"),
            "chapter": int(binding.get("chapter", 0)),
            "synthesis_id": path_data.get("synthesis_id"),
            "path": dict(path_data),
        }
        if path.get("path_hash") != _sha256_json(basis):
            raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "fallback path identity changed")
        ids.add(path_id)
        hashes.add(path.get("path_hash", ""))
    ancestry = binding.get("synthesis_ancestry")
    if not isinstance(ancestry, Mapping):
        raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "synthesis ancestry index is missing")
    for path in active:
        if path.get("synthesis_id") not in ancestry or list(path.get("evidence_ids", [])) != list(ancestry[path["synthesis_id"]]):
            raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "path evidence is outside exact synthesis ancestry")
    if len(ids) != len(priority) + len(fallback) or len(hashes) != len(priority) + len(fallback):
        raise ProvenanceBindingV2Error("DUPLICATE_PROVENANCE_REFERENCE", "binding contains duplicate paths")


def _validate_combination(paths: Sequence[Mapping[str, Any]], section_kind: str | None) -> None:
    scopes = {_text(path.get("path", {}), "passage_scope") for path in paths}
    if len(scopes) > 1:
        raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "a block cannot mix passage scopes")
    if section_kind and section_kind != "surrounding_passages" and "SURROUNDING_PASSAGE" in scopes:
        raise ProvenanceBindingV2Error("OUT_OF_CHAPTER_PROVENANCE_PATH", "surrounding synthesis requires surrounding_passages")
    if section_kind == "surrounding_passages" and any(
        _text(path.get("path", {}), "kind") != "surrounding_passages" for path in paths
    ):
        raise ProvenanceBindingV2Error("PROVENANCE_PATH_IDENTITY_MISMATCH", "only surrounding synthesis belongs in surrounding_passages")


def _evidence_disputed(item: Any) -> bool:
    metadata = getattr(item, "relevance_metadata", None) or (_value(item, "relevance_metadata", {}) or {})
    return bool(metadata.get("disputed") is True or str(metadata.get("dispute_status") or "").casefold() in _DISPUTED_LEVELS or str(metadata.get("certainty") or "").casefold() in _DISPUTED_LEVELS)


def _is_current_chapter_reference(reference: str, book: str, chapter: int) -> bool:
    match = re.match(r"^(.+?)\s+(\d+):\d+(?:-\d+)?$", reference)
    return bool(match and match.group(1).casefold() == book.casefold() and int(match.group(2)) == chapter)


def _confidence_rank(value: str) -> int:
    return _CONFIDENCE_RANK.get(value, -1)


def _scope(value: Mapping[str, Any]) -> str:
    book = re.sub(r"[^a-z0-9]+", "_", _text(value, "book").casefold()).strip("_")
    return f"{book}_{int(value.get('chapter', 0)):03d}"


def _mapping_by_id(values: Iterable[Any] | Mapping[str, Any] | None) -> dict[str, Any]:
    if values is None:
        return {}
    if isinstance(values, Mapping):
        return {str(key): value for key, value in values.items()}
    return {_text(value, "id"): value for value in values}


def _sequence(value: Any, field: str) -> list[str]:
    raw = value.get(field) if isinstance(value, Mapping) else getattr(value, field, [])
    return [str(item) for item in (raw or [])]


def _sequence_objects(value: Any, field: str) -> list[Any]:
    raw = value.get(field) if isinstance(value, Mapping) else getattr(value, field, [])
    return list(raw or [])


def _text(value: Any, field: str) -> str:
    raw = value.get(field) if isinstance(value, Mapping) else getattr(value, field, "")
    return str(raw or "")


def _value(value: Any, field: str, default: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get(field, default)
    return getattr(value, field, default)


def _unique(values: Sequence[str] | Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
