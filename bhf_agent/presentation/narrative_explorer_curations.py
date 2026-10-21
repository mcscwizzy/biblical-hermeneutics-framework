"""Validated, data-driven curation for exact Narrative Explorer relationships.

Curation records live in version-controlled JSON under the CKL curation
directory. This module exposes the existing tuple and projection behavior,
plus an immutable exact-identity lookup index.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .references import references_overlap


_CURATION_DATA_ROOT = (
    Path(__file__).resolve().parents[2]
    / "framework"
    / "canonical_library"
    / "curations"
    / "narrative-explorer"
    / "ne9c"
)


def _identity(entry: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        entry["relationship_kind"],
        entry["source_id"],
        entry["target_id"],
        entry["original_relationship_type"],
        entry["original_notes"],
        entry["original_weight"],
    )


def build_curation_index(
    entries: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> Mapping[tuple[Any, ...], Mapping[str, Any]]:
    """Validate entries and build a deterministic, read-only identity index."""

    index: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for entry in entries:
        validate_curation(entry, require_authored_direction=True)
        identity = _identity(entry)
        if identity in index:
            raise ValueError(f"duplicate curated relationship identity: {identity!r}")
        index[identity] = MappingProxyType(dict(entry))
    return MappingProxyType(index)


def _load_curations() -> tuple[Mapping[str, Any], ...]:
    entries: list[Mapping[str, Any]] = []
    for path in sorted(_CURATION_DATA_ROOT.rglob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read curation data file {path}: {exc}") from exc
        if not isinstance(document, Mapping) or document.get("schema_version") != 1:
            raise ValueError(f"unsupported curation data document: {path}")
        if not isinstance(document.get("curations"), list):
            raise ValueError(f"curation data file has no entry list: {path}")
        for entry in document["curations"]:
            if not isinstance(entry, Mapping):
                raise ValueError(f"curation data file contains a malformed entry: {path}")
            validate_curation(entry, require_authored_direction=True)
            entries.append(dict(entry))
    if not entries:
        raise ValueError(f"no Narrative Explorer curation data found under {_CURATION_DATA_ROOT}")
    return tuple(entries)


def _public_curation(entry: Mapping[str, Any]) -> dict[str, Any]:
    """Keep authored registry metadata internal to preserve the API payload."""

    return {key: value for key, value in entry.items() if key != "authored_direction"}


def curate_connection(connection: Any, passage_reference: str) -> Any:
    """Return a passage-eligible connection with its reviewed annotation."""

    kind = "evidence" if connection.basis.get("kind") == "ckl_related_evidence" else "object"
    identity = (
        kind,
        connection.source_id,
        connection.target_id,
        connection.original_relationship_type,
        connection._authored_notes,
        connection.basis.get("weight"),
    )
    entry = CURATION_BY_IDENTITY.get(identity)
    if entry is None or not any(
        references_overlap(passage_reference, reference)
        for reference in entry["applicable_passages"]
    ):
        return connection
    if kind == "evidence" and connection.basis.get("target_resolution_status") != "eligible":
        return connection
    from dataclasses import replace

    basis = dict(connection.basis)
    if "notes" in basis:
        basis["notes"] = entry["original_notes"]
    return replace(
        connection,
        connection_type=entry["classification"],
        basis=basis,
        curation=_public_curation(entry),
    )


def validate_curation(
    entry: Mapping[str, Any], *, require_authored_direction: bool = False
) -> None:
    """Validate a curation record before it enters a registry or projection."""

    if not isinstance(entry, Mapping):
        raise ValueError("curated relationship must be a mapping")
    required_text = (
        "relationship_kind", "source_id", "target_id", "original_relationship_type",
        "classification", "textual_observation", "why",
        "uncertainty", "curation_confidence", "curation_status", "human_scholarly_approval",
    )
    if any(not isinstance(entry.get(key), str) or not entry[key] for key in required_text):
        raise ValueError("curated relationship has missing explanatory metadata")
    if "original_notes" not in entry or (entry["original_notes"] is not None and not isinstance(entry["original_notes"], str)):
        raise ValueError("curated relationship has invalid authored notes metadata")
    if entry["relationship_kind"] not in {"object", "evidence"}:
        raise ValueError("curated relationship has an invalid relationship kind")
    if not entry["source_id"].startswith("ckl:") or not entry["target_id"].startswith("ckl:"):
        raise ValueError("curated relationship has malformed CKL endpoint IDs")
    if require_authored_direction and entry.get("authored_direction") not in {"one_way", "reciprocal"}:
        raise ValueError("curated relationship has a missing or invalid authored direction")
    if entry["classification"] not in {
        "direct_quotation", "explicit_textual_reference", "shared_literary_motif",
        "narrative_parallel", "thematic_relationship", "later_canonical_reception",
        "proposed_intertextual_echo", "interpretive_association",
    }:
        raise ValueError("curated relationship has an invalid classification")
    if entry["curation_confidence"] not in {"high", "moderate", "low"}:
        raise ValueError("curated relationship has an invalid curation confidence")
    if type(entry.get("original_weight")) is not int:
        raise ValueError("curated relationship has an invalid original weight")
    if entry["curation_status"] != "curated_for_explorer":
        raise ValueError("curated relationship has an invalid curation status")
    if entry["human_scholarly_approval"] != "not_recorded":
        raise ValueError("curated relationship has an invalid human approval status")
    evidence_certainty = entry.get("ckl_evidence_certainty")
    if not isinstance(evidence_certainty, Mapping) or evidence_certainty.get("status") not in {"not_recorded", "recorded"}:
        raise ValueError("curated relationship has invalid CKL evidence certainty metadata")
    if not isinstance(evidence_certainty.get("records"), list):
        raise ValueError("curated relationship has invalid CKL evidence certainty records")
    if entry["relationship_kind"] == "object" and evidence_certainty != {"status": "not_recorded", "records": []}:
        raise ValueError("object relationships cannot claim evidence certainty that CKL does not record")
    if entry["relationship_kind"] == "evidence" and evidence_certainty.get("status") != "recorded":
        raise ValueError("evidence relationships must preserve their CKL evidence certainty")
    if entry["relationship_kind"] == "evidence" and any(
        not isinstance(record, Mapping)
        or any(
            not isinstance(record.get(key), str) or not record[key]
            for key in ("record_id", "certainty")
        )
        for record in evidence_certainty["records"]
    ):
        raise ValueError("evidence curation is missing its recorded certainty provenance")
    if not isinstance(entry.get("supporting_comparative_material", []), list):
        raise ValueError("curated relationship has invalid comparative material metadata")
    if not all(
        isinstance(entry.get(key), list)
        and entry[key]
        and all(isinstance(value, str) and value for value in entry[key])
        for key in ("applicable_passages", "supporting_passages", "supporting_records")
    ):
        raise ValueError("curated relationship has incomplete passage or record support")
    from framework.canonical_library.scripture import build_book_alias_lookup, parse_scripture_references

    aliases = build_book_alias_lookup(())
    for reference in entry["applicable_passages"]:
        spans = parse_scripture_references(reference, book_alias_lookup=aliases)
        if (
            len(spans) != 1
            or spans[0].start_chapter is None
            or spans[0].start_chapter < 1
            or (spans[0].end_chapter is not None and spans[0].end_chapter != spans[0].start_chapter)
        ):
            raise ValueError("curated relationship applicability must identify a passage in a single chapter")
    if not isinstance(entry.get("supporting_ckl_sources"), list) or not entry["supporting_ckl_sources"]:
        raise ValueError("curated relationship has no CKL source provenance")
    for source in entry["supporting_ckl_sources"]:
        if not isinstance(source, Mapping) or any(
            not isinstance(source.get(key), str) or not source[key]
            for key in ("object_id", "source_id")
        ):
            raise ValueError("curated relationship has invalid CKL source provenance")
    for material in entry.get("supporting_comparative_material", []):
        if not isinstance(material, Mapping) or any(
            not isinstance(material.get(key), str) or not material[key]
            for key in ("kind", "reference", "source_id")
        ):
            raise ValueError("curated relationship has invalid comparative source provenance")


CURATED_RELATIONSHIPS: tuple[Mapping[str, Any], ...] = _load_curations()
CURATION_BY_IDENTITY = build_curation_index(CURATED_RELATIONSHIPS)
