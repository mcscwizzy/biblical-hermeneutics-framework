"""Relational ancestry presentation for reader-level projection diagnostics.

The reader-level projection remains a flat, deterministic idea index.  This
module adds a content-addressed presentation view that keeps each synthesis
unit paired with exactly the evidence IDs owned by that unit.  It is
intentionally downstream of projection v1 and does not alter source objects,
grouping, evidence, validation, scoring, or gate behavior.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from .reader_level_projection import READER_LEVEL_IDEA_PROJECTION_VERSION


READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION = (
    "reader-level-idea-ancestry-envelope-v1"
)
READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_IMPLEMENTATION = (
    "bhf_agent.chapter_commentary.reader_idea_ancestry_envelope"
)

_DISPUTED_INTERPRETATION_LEVELS = frozenset(
    {"disputed", "speculative", "insufficient_evidence", "contested", "uncertain"}
)


class AncestryEnvelopeError(ValueError):
    """Raised when a relational ancestry view cannot be built safely."""


def build_ancestry_envelope(
    projection: Any,
    synthesis: Any,
    evidence_items: Iterable[Any] | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an explicit synthesis-unit-to-evidence view for every idea.

    The function reads projection and synthesis data only.  It does not copy
    the projection's flat evidence list into the rendered view; the only
    evidence exposed to the renderer is nested under the synthesis unit that
    owns it.
    """

    projection_version = _text(projection, "projection_version")
    if projection_version != READER_LEVEL_IDEA_PROJECTION_VERSION:
        raise AncestryEnvelopeError(
            "ancestry envelope requires reader-level-idea-projection-v1"
        )

    projection_hash = _text(projection, "projection_hash")
    evidence_hash = _text(projection, "evidence_hash")
    synthesis_hash = _text(projection, "synthesis_hash")
    if not projection_hash or not evidence_hash or not synthesis_hash:
        raise AncestryEnvelopeError("projection identity hashes are required")

    units = _sequence_objects(synthesis, "synthesis_units")
    unit_map = {_text(unit, "id"): unit for unit in units}
    if not unit_map or len(unit_map) != len(units):
        raise AncestryEnvelopeError("synthesis units must have unique non-empty IDs")

    evidence_map = _mapping_by_id(evidence_items)
    ideas: list[dict[str, Any]] = []
    source_synthesis_ids: set[str] = set()
    source_evidence_ids: set[str] = set()
    path_synthesis_ids: set[str] = set()
    path_evidence_ids: set[str] = set()
    leakage: list[dict[str, Any]] = []

    for raw_idea in _sequence_objects(projection, "ideas"):
        idea_id = _text(raw_idea, "idea_id")
        if not idea_id:
            raise AncestryEnvelopeError("projected ideas require non-empty IDs")
        unit_ids = _sequence(raw_idea, "synthesis_unit_ids")
        flat_evidence_ids = _sequence(raw_idea, "evidence_ids")
        if len(set(unit_ids)) != len(unit_ids):
            raise AncestryEnvelopeError(f"idea {idea_id} repeats a synthesis unit")

        source_synthesis_ids.update(unit_ids)
        source_evidence_ids.update(flat_evidence_ids)
        paths: list[dict[str, Any]] = []
        idea_path_evidence: set[str] = set()
        for synthesis_id in unit_ids:
            unit = unit_map.get(synthesis_id)
            if unit is None:
                raise AncestryEnvelopeError(
                    f"idea {idea_id} references unknown synthesis unit {synthesis_id}"
                )
            unit_evidence_ids = _sequence(unit, "evidence_ids")
            if evidence_map:
                unknown = sorted(set(unit_evidence_ids) - set(evidence_map))
                if unknown:
                    raise AncestryEnvelopeError(
                        f"synthesis unit {synthesis_id} references unknown evidence: {unknown}"
                    )
            idea_path_evidence.update(unit_evidence_ids)
            path_synthesis_ids.add(synthesis_id)
            path_evidence_ids.update(unit_evidence_ids)
            paths.append(_path_for(unit, evidence_hash, synthesis_hash))

        missing_from_paths = sorted(set(flat_evidence_ids) - idea_path_evidence)
        missing_from_projection = sorted(idea_path_evidence - set(flat_evidence_ids))
        if missing_from_paths or missing_from_projection:
            raise AncestryEnvelopeError(
                f"idea {idea_id} flat ancestry disagrees with synthesis paths: "
                f"missing_from_paths={missing_from_paths}, "
                f"missing_from_projection={missing_from_projection}"
            )

        for path in paths:
            outside = sorted(
                set(path["evidence_ids"])
                - set(_sequence(unit_map[path["synthesis_id"]], "evidence_ids"))
            )
            if outside:
                leakage.append(
                    {
                        "idea_id": idea_id,
                        "synthesis_id": path["synthesis_id"],
                        "evidence_ids": outside,
                    }
                )

        ideas.append(
            {
                "idea_id": idea_id,
                "label": _text(raw_idea, "label"),
                "importance": _text(raw_idea, "importance"),
                "categories": _sequence(raw_idea, "categories"),
                "cluster_ids": _sequence(raw_idea, "cluster_ids"),
                "disputed": bool(_value(raw_idea, "disputed", False)),
                "status": _text(raw_idea, "status"),
                "confidence": _text(raw_idea, "confidence"),
                "ancestry_paths": paths,
            }
        )

    base = {
        "artifact_version": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
        "implementation_identity": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_IMPLEMENTATION,
        "reference": _text(projection, "reference"),
        "book": _text(projection, "book"),
        "chapter": int(_value(projection, "chapter", 0)),
        "projection_version": projection_version,
        "projection_hash": projection_hash,
        "evidence_hash": evidence_hash,
        "synthesis_hash": synthesis_hash,
        "ideas": ideas,
        "ancestry_audit": {
            "source_idea_count": len(_sequence_objects(projection, "ideas")),
            "envelope_idea_count": len(ideas),
            "idea_ids_preserved": [
                _text(idea, "idea_id") for idea in _sequence_objects(projection, "ideas")
            ]
            == [idea["idea_id"] for idea in ideas],
            "source_synthesis_unit_ids": sorted(source_synthesis_ids),
            "path_synthesis_unit_ids": sorted(path_synthesis_ids),
            "synthesis_unit_ids_preserved": source_synthesis_ids == path_synthesis_ids,
            "source_evidence_ids": sorted(source_evidence_ids),
            "path_evidence_ids": sorted(path_evidence_ids),
            "evidence_ids_preserved": source_evidence_ids == path_evidence_ids,
            "paths_have_exact_unit_ancestry": not leakage,
            "cross_synthesis_evidence_leakage": leakage,
            "flat_idea_evidence_lists_rendered": False,
            "synthetic_parentage_created": False,
            "invented_synthesis_ids": sorted(path_synthesis_ids - set(unit_map)),
            "invented_evidence_ids": sorted(
                path_evidence_ids - set(evidence_map)
            )
            if evidence_map
            else [],
        },
    }
    audit = base["ancestry_audit"]
    if not audit["idea_ids_preserved"]:
        raise AncestryEnvelopeError("idea identity was not preserved")
    if not audit["synthesis_unit_ids_preserved"]:
        raise AncestryEnvelopeError("synthesis ancestry was not preserved")
    if not audit["evidence_ids_preserved"]:
        raise AncestryEnvelopeError("evidence ancestry was not preserved")
    if audit["invented_synthesis_ids"] or audit["invented_evidence_ids"]:
        raise AncestryEnvelopeError("envelope invented ancestry IDs")
    if leakage:
        raise AncestryEnvelopeError("envelope path contains cross-synthesis evidence")

    envelope = dict(base)
    envelope["envelope_hash"] = _sha256_json(base)
    return envelope


def audit_ancestry_envelope(
    envelope: Mapping[str, Any],
    projection: Any,
    synthesis: Any,
) -> dict[str, Any]:
    """Audit a stored envelope and response-independent path preservation."""

    expected = build_ancestry_envelope(projection, synthesis)
    actual_base = {key: value for key, value in envelope.items() if key != "envelope_hash"}
    expected_hash = _sha256_json(actual_base)
    hash_valid = envelope.get("envelope_hash") == expected_hash
    shape_equal = actual_base == {
        key: value for key, value in expected.items() if key != "envelope_hash"
    }
    return {
        "envelope_hash": envelope.get("envelope_hash"),
        "expected_envelope_hash": expected_hash,
        "hash_valid": hash_valid,
        "shape_matches_deterministic_rebuild": shape_equal,
        "ancestry_audit": envelope.get("ancestry_audit", {}),
        "valid": hash_valid and shape_equal,
    }


def render_ancestry_envelope_section(envelope: Mapping[str, Any]) -> str:
    """Render relational paths as explicit renderer grounding instructions."""

    lines = [
        "READER-LEVEL IDEA ANCESTRY ENVELOPE",
        "",
        "This is an additive relational presentation of the reader-level ideas",
        "above. The projection and compiled synthesis remain authoritative.",
        "Each listed ancestry path pairs one synthesis unit with only the evidence",
        "IDs descended from that unit. When citing synthesis and evidence IDs for",
        "a prose block, only pair evidence IDs with synthesis IDs from the same",
        "listed ancestry path. Do not treat IDs from the same reader-level idea",
        "as interchangeable. If a block uses multiple paths, cite the synthesis",
        "and evidence IDs from each path actually used.",
        "",
    ]
    for idea in envelope.get("ideas", []):
        lines.append(
            f"IDEA {idea['idea_id']}: {idea.get('label', '')} "
            f"(importance: {idea.get('importance', '')}; "
            f"categories: {', '.join(idea.get('categories') or [])})"
        )
        lines.append("Allowed ancestry paths:")
        for index, path in enumerate(idea.get("ancestry_paths", []), 1):
            path_json = json.dumps(
                {
                    "synthesis_id": path["synthesis_id"],
                    "evidence_ids": path["evidence_ids"],
                    "confidence": path.get("synthesis_confidence"),
                    "interpretation_level": path.get("interpretation_level"),
                    "disputed": path.get("disputed"),
                    "passage_scope": path.get("passage_scope"),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            lines.append(f"- path_{index}: {path_json}")
        lines.append("")
    lines.extend(
        [
            "Use the paths for citation pairing and the ideas for conceptual breadth.",
            "Do not create one block per path or expose this implementation view in",
            "reader-facing prose.",
        ]
    )
    return "\n".join(lines)


def add_ancestry_envelope_to_prompt(
    projection_prompt: str, envelope: Mapping[str, Any]
) -> str:
    """Add the envelope to an existing prompt-1.7 projection prompt."""

    marker = "CANONICAL TEXT:\n"
    if marker not in projection_prompt:
        raise AncestryEnvelopeError("projection prompt lacks canonical-text marker")
    if "READER-LEVEL IDEA ANCESTRY ENVELOPE" in projection_prompt:
        raise AncestryEnvelopeError("prompt already contains an ancestry envelope")
    section = render_ancestry_envelope_section(envelope)
    return projection_prompt.replace(marker, f"{section}\n\n{marker}", 1)


def response_ancestry_audit(
    response: Mapping[str, Any], envelope: Mapping[str, Any]
) -> dict[str, Any]:
    """Audit each response block against the explicit envelope paths."""

    paths_by_synthesis: dict[str, list[dict[str, Any]]] = {}
    for idea in envelope.get("ideas", []):
        for path in idea.get("ancestry_paths", []):
            paths_by_synthesis.setdefault(path["synthesis_id"], []).append(path)

    blocks: list[dict[str, Any]] = []
    for section_index, section in enumerate(response.get("sections", [])):
        for block_index, block in enumerate(section.get("blocks", [])):
            synthesis_ids = [str(value) for value in block.get("synthesis_ids", [])]
            evidence_ids = [str(value) for value in block.get("evidence_ids", [])]
            cited_paths = [
                path
                for synthesis_id in synthesis_ids
                for path in paths_by_synthesis.get(synthesis_id, [])
            ]
            evidence_owners: dict[str, list[str]] = {
                evidence_id: sorted(
                    {
                        path["synthesis_id"]
                        for path in cited_paths
                        if evidence_id in path.get("evidence_ids", [])
                    }
                )
                for evidence_id in evidence_ids
            }
            outside = sorted(
                evidence_id
                for evidence_id, owners in evidence_owners.items()
                if not owners
            )
            blocks.append(
                {
                    "section_index": section_index,
                    "block_index": block_index,
                    "block_id": block.get("id"),
                    "cited_synthesis_ids": synthesis_ids,
                    "cited_evidence_ids": evidence_ids,
                    "evidence_path_owners": evidence_owners,
                    "evidence_outside_cited_paths": outside,
                    "ancestry_valid": not outside,
                }
            )
    return {
        "block_count": len(blocks),
        "blocks": blocks,
        "ancestry_mismatch_count": sum(
            bool(block["evidence_outside_cited_paths"]) for block in blocks
        ),
        "valid": all(block["ancestry_valid"] for block in blocks),
    }


def _path_for(unit: Any, evidence_hash: str, synthesis_hash: str) -> dict[str, Any]:
    interpretation_level = _text(unit, "interpretation_level")
    return {
        "synthesis_id": _text(unit, "id"),
        "evidence_ids": _sequence(unit, "evidence_ids"),
        "synthesis_confidence": _text(unit, "confidence"),
        "interpretation_level": interpretation_level,
        "disputed": interpretation_level in _DISPUTED_INTERPRETATION_LEVELS,
        "passage_scope": _text(unit, "passage_scope"),
        "kind": _text(unit, "kind"),
        "verse_refs": _sequence(unit, "verse_refs"),
        "source_anchors": _sequence(unit, "source_anchors"),
        "ancestry_hashes": {
            "evidence_hash": evidence_hash,
            "synthesis_hash": synthesis_hash,
        },
    }


def _sha256_json(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
