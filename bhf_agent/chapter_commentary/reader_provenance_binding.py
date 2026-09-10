"""Deterministic renderer provenance binding for reader-level ancestry paths.

The renderer chooses a complete, precomputed reader-level ancestry path.  This
module resolves that choice into the existing ``synthesis_ids`` and
``evidence_ids`` fields after generation.  It deliberately does not change
projection grouping, synthesis semantics, scoring, or the canonical
commentary schema.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


READER_PROVENANCE_BINDING_VERSION = "reader-provenance-binding-v1"
READER_PROVENANCE_BINDING_IMPLEMENTATION = (
    "bhf_agent.chapter_commentary.reader_provenance_binding"
)

_PATH_ID_RE = re.compile(
    r"^reader_path_[a-z0-9_]+_[0-9]{3}_[0-9a-f]{24}$"
)


class ProvenanceBindingError(ValueError):
    """A renderer provenance reference cannot be safely resolved."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def build_provenance_binding(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Build a deterministic path catalog from one validated envelope.

    The input envelope is treated as immutable.  A path ID is content-derived
    from the chapter identity, reader idea identity, and the complete existing
    ancestry path.  No synthesis/evidence relationship is created here.
    """

    _require_envelope_shape(envelope)
    paths: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    for idea in envelope.get("ideas", []):
        idea_id = _text(idea, "idea_id")
        if not idea_id:
            raise ProvenanceBindingError(
                "PROVENANCE_PATH_IDENTITY_MISMATCH",
                "every envelope idea must have a stable idea_id",
            )
        for path in idea.get("ancestry_paths", []):
            path_data = _path_data(path)
            basis = {
                "reference": _text(envelope, "reference"),
                "book": _text(envelope, "book"),
                "chapter": int(envelope.get("chapter", 0)),
                "reader_idea_id": idea_id,
                "path": path_data,
            }
            path_hash = _sha256_json(basis)
            path_id = (
                f"reader_path_{_scope(envelope)}_{path_hash[:24]}"
            )
            if path_id in seen_ids or path_hash in seen_hashes:
                raise ProvenanceBindingError(
                    "PROVENANCE_PATH_IDENTITY_MISMATCH",
                    f"duplicate deterministic path identity for {path_id}",
                )
            seen_ids.add(path_id)
            seen_hashes.add(path_hash)
            paths.append(
                {
                    "path_id": path_id,
                    "path_hash": path_hash,
                    "reader_idea_id": idea_id,
                    "reader_idea_label": _text(idea, "label"),
                    "synthesis_id": path_data["synthesis_id"],
                    "evidence_ids": list(path_data["evidence_ids"]),
                    "path": path_data,
                }
            )

    base = {
        "artifact_version": READER_PROVENANCE_BINDING_VERSION,
        "implementation_identity": READER_PROVENANCE_BINDING_IMPLEMENTATION,
        "reference": _text(envelope, "reference"),
        "book": _text(envelope, "book"),
        "chapter": int(envelope.get("chapter", 0)),
        "envelope_version": _text(envelope, "artifact_version"),
        "envelope_hash": _text(envelope, "envelope_hash"),
        "paths": paths,
        "binding_audit": {
            "path_count": len(paths),
            "path_ids_unique": len({path["path_id"] for path in paths}) == len(paths),
            "path_hashes_unique": len({path["path_hash"] for path in paths}) == len(paths),
            "synthetic_parentage_created": False,
            "cross_synthesis_evidence_leakage": [],
        },
    }
    return {**base, "binding_hash": _sha256_json(base)}


def audit_provenance_binding(
    binding: Mapping[str, Any], envelope: Mapping[str, Any]
) -> dict[str, Any]:
    """Rebuild and compare a stored path catalog without changing it."""

    try:
        expected = build_provenance_binding(envelope)
    except ProvenanceBindingError as exc:
        return {
            "valid": False,
            "binding_hash": binding.get("binding_hash"),
            "expected_binding_hash": None,
            "failure_code": exc.code,
            "failure": str(exc),
        }
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


def resolve_provenance_refs(
    provenance_refs: Any,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve a block's path references into canonical ancestry fields."""

    _assert_binding(binding)
    if not isinstance(provenance_refs, list) or not provenance_refs:
        raise ProvenanceBindingError(
            "MALFORMED_PROVENANCE_REFERENCE",
            "provenance_refs must be a non-empty array",
        )
    if any(not isinstance(value, str) or not value for value in provenance_refs):
        raise ProvenanceBindingError(
            "MALFORMED_PROVENANCE_REFERENCE",
            "every provenance reference must be a non-empty string",
        )
    if len(set(provenance_refs)) != len(provenance_refs):
        raise ProvenanceBindingError(
            "DUPLICATE_PROVENANCE_REFERENCE",
            "a block may not repeat a provenance path",
        )

    by_id = {path["path_id"]: path for path in binding.get("paths", [])}
    selected: list[dict[str, Any]] = []
    expected_scope = _scope(binding)
    for path_id in provenance_refs:
        if not _PATH_ID_RE.fullmatch(path_id):
            raise ProvenanceBindingError(
                "MALFORMED_PROVENANCE_REFERENCE",
                f"invalid provenance path format: {path_id}",
            )
        path = by_id.get(path_id)
        if path is None:
            if not path_id.startswith(f"reader_path_{expected_scope}_"):
                raise ProvenanceBindingError(
                    "OUT_OF_CHAPTER_PROVENANCE_PATH",
                    f"path {path_id} is not scoped to {_text(binding, 'reference')}",
                )
            raise ProvenanceBindingError(
                "UNKNOWN_PROVENANCE_PATH",
                f"path {path_id} is not in the current binding",
            )
        selected.append(path)

    synthesis_ids = _unique(path["synthesis_id"] for path in selected)
    evidence_ids = _unique(
        evidence_id
        for path in selected
        for evidence_id in path["evidence_ids"]
    )
    # This assertion is intentionally redundant with path construction: it is
    # the boundary guarantee that prevents cross-synthesis evidence leakage.
    for path in selected:
        if path["synthesis_id"] not in synthesis_ids or any(
            evidence_id not in evidence_ids for evidence_id in path["evidence_ids"]
        ):
            raise ProvenanceBindingError(
                "PROVENANCE_PATH_IDENTITY_MISMATCH",
                f"resolved path {path['path_id']} lost its own ancestry",
            )
    return {
        "provenance_refs": list(provenance_refs),
        "paths": copy.deepcopy(selected),
        "reader_idea_ids": _unique(path["reader_idea_id"] for path in selected),
        "synthesis_ids": synthesis_ids,
        "evidence_ids": evidence_ids,
    }


def normalize_renderer_payload(
    payload: Mapping[str, Any], binding: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Normalize raw path-only renderer output to the existing schema.

    The raw response remains untouched.  The returned commentary payload has
    only the existing canonical ``synthesis_ids`` and ``evidence_ids`` fields;
    binding metadata is returned separately for diagnostic storage.
    """

    _assert_binding(binding)
    normalized = copy.deepcopy(dict(payload))
    block_records: list[dict[str, Any]] = []
    sections = normalized.get("sections", [])
    if not isinstance(sections, list):
        raise ProvenanceBindingError(
            "MALFORMED_PROVENANCE_REFERENCE",
            "sections must be an array before provenance normalization",
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
            if "provenance_refs" not in block:
                raise ProvenanceBindingError(
                    "MISSING_PROVENANCE_REFERENCES",
                    f"section[{section_index}].block[{block_index}] has no provenance_refs",
                )
            resolved = resolve_provenance_refs(block["provenance_refs"], binding)
            block["synthesis_ids"] = resolved["synthesis_ids"]
            block["evidence_ids"] = resolved["evidence_ids"]
            block.pop("provenance_refs", None)
            block_records.append(
                {
                    "section_index": section_index,
                    "block_index": block_index,
                    "block_id": block.get("id"),
                    "provenance_refs": resolved["provenance_refs"],
                    "reader_idea_ids": resolved["reader_idea_ids"],
                    "synthesis_ids": resolved["synthesis_ids"],
                    "evidence_ids": resolved["evidence_ids"],
                }
            )
    metadata = {
        "artifact_version": READER_PROVENANCE_BINDING_VERSION,
        "binding_hash": binding["binding_hash"],
        "block_count": len(block_records),
        "blocks": block_records,
    }
    return normalized, metadata


def render_provenance_binding_section(
    envelope: Mapping[str, Any], binding: Mapping[str, Any]
) -> str:
    """Render the path catalog that the renderer is allowed to select."""

    _assert_binding(binding)
    paths_by_idea: dict[str, list[Mapping[str, Any]]] = {}
    for path in binding.get("paths", []):
        paths_by_idea.setdefault(path["reader_idea_id"], []).append(path)
    lines = [
        "READER PROVENANCE BINDING",
        "",
        f"Binding version: {READER_PROVENANCE_BINDING_VERSION}",
        "Choose one or more complete provenance_refs for each prose block.",
        "A provenance reference selects one precomputed reader-idea ancestry path.",
        "BHF will resolve each selected path to the canonical synthesis and evidence",
        "fields after generation. Do not choose or emit synthesis_ids or evidence_ids",
        "manually, and do not combine evidence from different paths.",
        "Only path IDs listed below are valid for this chapter.",
        "",
    ]
    for idea in envelope.get("ideas", []):
        idea_id = _text(idea, "idea_id")
        lines.append(f"IDEA {idea_id}: {_text(idea, 'label')}")
        for path in paths_by_idea.get(idea_id, []):
            path_data = path["path"]
            lines.append(
                "- "
                + json.dumps(
                    {
                        "provenance_ref": path["path_id"],
                        "synthesis_unit": path["synthesis_id"],
                        "kind": path_data.get("kind"),
                        "passage_scope": path_data.get("passage_scope"),
                        "verse_refs": path_data.get("verse_refs", []),
                        "evidence_count": len(path["evidence_ids"]),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        lines.append("")
    lines.extend(
        [
            "PROVENANCE OUTPUT ADAPTER:",
            "In every block, replace the example synthesis_ids/evidence_ids fields",
            "with exactly this field:",
            '  \"provenance_refs\": [\"reader_path_...\"]',
            "Use one or more listed path IDs when a block combines distinct supported",
            "ideas. Do not emit any path ID from another chapter or invent one.",
            "This adapter changes only machine-readable provenance selection; keep",
            "the prompt 1.7 prose, breadth, uncertainty, and reader-facing rules.",
        ]
    )
    return "\n".join(lines)


def add_provenance_binding_to_prompt(
    existing_prompt: str,
    envelope: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> str:
    """Append the path-only output adapter to an existing prompt-1.7 input."""

    marker = "READER PROVENANCE BINDING"
    if marker in existing_prompt:
        raise ProvenanceBindingError(
            "PROVENANCE_PATH_IDENTITY_MISMATCH",
            "prompt already contains a provenance binding",
        )
    return existing_prompt.rstrip() + "\n\n" + render_provenance_binding_section(envelope, binding) + "\n"


def _assert_binding(binding: Mapping[str, Any]) -> None:
    if not isinstance(binding, Mapping):
        raise ProvenanceBindingError(
            "PROVENANCE_PATH_IDENTITY_MISMATCH", "binding must be an object"
        )
    version = _text(binding, "artifact_version")
    if version != READER_PROVENANCE_BINDING_VERSION:
        raise ProvenanceBindingError(
            "PROVENANCE_PATH_IDENTITY_MISMATCH",
            f"unsupported binding version: {version}",
        )
    envelope_version = _text(binding, "envelope_version")
    if not envelope_version:
        raise ProvenanceBindingError(
            "PROVENANCE_PATH_IDENTITY_MISMATCH", "binding envelope version is missing"
        )
    actual_base = {
        key: value for key, value in binding.items() if key != "binding_hash"
    }
    if binding.get("binding_hash") != _sha256_json(actual_base):
        raise ProvenanceBindingError(
            "PROVENANCE_PATH_IDENTITY_MISMATCH",
            "binding identity hash does not match its immutable definition",
        )
    expected_scope = _scope(binding)
    for path in binding.get("paths", []):
        path_id = _text(path, "path_id")
        if not _PATH_ID_RE.fullmatch(path_id) or not path_id.startswith(
            f"reader_path_{expected_scope}_"
        ):
            raise ProvenanceBindingError(
                "PROVENANCE_PATH_IDENTITY_MISMATCH",
                f"path ID is not scoped to its binding: {path_id}",
            )
        path_data = path.get("path")
        if not isinstance(path_data, Mapping):
            raise ProvenanceBindingError(
                "PROVENANCE_PATH_IDENTITY_MISMATCH",
                f"path definition missing for {path_id}",
            )
        if path.get("synthesis_id") != path_data.get("synthesis_id") or list(
            path.get("evidence_ids", [])
        ) != list(path_data.get("evidence_ids", [])):
            raise ProvenanceBindingError(
                "PROVENANCE_PATH_IDENTITY_MISMATCH",
                f"denormalized ancestry changed for {path_id}",
            )
        basis = {
            "reference": _text(binding, "reference"),
            "book": _text(binding, "book"),
            "chapter": int(binding.get("chapter", 0)),
            "reader_idea_id": _text(path, "reader_idea_id"),
            "path": dict(path_data),
        }
        if _sha256_json(basis) != path.get("path_hash"):
            raise ProvenanceBindingError(
                "PROVENANCE_PATH_IDENTITY_MISMATCH",
                f"immutable path definition changed for {path_id}",
            )


def _require_envelope_shape(envelope: Mapping[str, Any]) -> None:
    if not isinstance(envelope, Mapping):
        raise ProvenanceBindingError(
            "PROVENANCE_PATH_IDENTITY_MISMATCH", "envelope must be an object"
        )
    if not _text(envelope, "envelope_hash"):
        raise ProvenanceBindingError(
            "PROVENANCE_PATH_IDENTITY_MISMATCH", "envelope hash is required"
        )
    if not _text(envelope, "artifact_version"):
        raise ProvenanceBindingError(
            "PROVENANCE_PATH_IDENTITY_MISMATCH", "envelope version is required"
        )


def _path_data(path: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "synthesis_id": _text(path, "synthesis_id"),
        "evidence_ids": [str(value) for value in path.get("evidence_ids", [])],
        "synthesis_confidence": _text(path, "synthesis_confidence"),
        "interpretation_level": _text(path, "interpretation_level"),
        "disputed": bool(path.get("disputed", False)),
        "passage_scope": _text(path, "passage_scope"),
        "kind": _text(path, "kind"),
        "verse_refs": [str(value) for value in path.get("verse_refs", [])],
        "source_anchors": [str(value) for value in path.get("source_anchors", [])],
        "ancestry_hashes": copy.deepcopy(path.get("ancestry_hashes", {})),
    }


def _scope(value: Mapping[str, Any]) -> str:
    book = _text(value, "book").casefold()
    book = re.sub(r"[^a-z0-9]+", "_", book).strip("_")
    chapter = int(value.get("chapter", 0))
    return f"{book}_{chapter:03d}"


def _unique(values: Sequence[str] | Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _text(value: Any, field: str) -> str:
    raw = value.get(field) if isinstance(value, Mapping) else getattr(value, field, "")
    return str(raw or "")


def _sha256_json(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
