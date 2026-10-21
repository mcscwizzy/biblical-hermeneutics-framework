"""Reader-facing passage routes backed by exact CKL records.

This module keeps authored CKL edges and CKL-documented passage pairs in
separate collections. It never infers a passage relationship from shared
objects, sources, anchors, or vocabulary.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from framework.canonical_library.scripture import (
    format_scripture_reference,
    parse_scripture_references,
)

from .references import _BOOK_ALIASES, references_overlap


_BRIDGE_DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "framework"
    / "canonical_library"
    / "curations"
    / "narrative-explorer"
    / "ne10"
    / "passage-bridges.json"
)
_RELATIONSHIP_CATEGORIES = {
    "direct_quotation",
    "explicit_textual_reference",
    "shared_literary_motif",
    "narrative_parallel",
    "thematic_relationship",
    "later_canonical_reception",
    "proposed_intertextual_echo",
    "interpretive_association",
}
_EVIDENCE_LAYERS = {
    "direct_textual_relationship",
    "thematic_interpretation",
    "later_reception",
    "historical_background",
    "ancient_comparative_evidence",
    "textual_critical_evidence",
    "lexical_comparison",
    "literary_parallel",
}
_DIRECTIONS = {
    "source_to_receiving_text",
    "bidirectional_comparison",
    "interpretive_comparison",
}
_RECORD_COLLECTIONS = {
    "claim": "claims",
    "evidence": "evidence_items",
    "interpretive_note": "interpretive_notes",
}


def _canonical_mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        return result if isinstance(result, Mapping) else None
    return None


@lru_cache(maxsize=1)
def load_passage_bridges() -> tuple[Mapping[str, Any], ...]:
    """Load the small, versioned NE-10 bridge registry."""

    try:
        document = json.loads(_BRIDGE_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read NE-10 passage bridge data: {exc}") from exc
    if not isinstance(document, Mapping) or document.get("schema_version") != 1:
        raise ValueError("unsupported NE-10 passage bridge schema")
    bridges = document.get("bridges")
    if not isinstance(bridges, list):
        raise ValueError("NE-10 passage bridge data has no bridge list")
    ids: set[str] = set()
    result: list[Mapping[str, Any]] = []
    for bridge in bridges:
        _validate_bridge_shape(bridge)
        if bridge["id"] in ids:
            raise ValueError(f"duplicate NE-10 passage bridge id: {bridge['id']}")
        ids.add(bridge["id"])
        result.append(dict(bridge))
    return tuple(result)


def _validate_bridge_shape(bridge: Any) -> None:
    if not isinstance(bridge, Mapping):
        raise ValueError("passage bridge must be an object")
    required_text = (
        "id", "direction", "relationship_category", "evidence_layer", "explanation", "uncertainty",
    )
    if any(not isinstance(bridge.get(key), str) or not bridge[key] for key in required_text):
        raise ValueError("passage bridge is missing explanatory metadata")
    if not isinstance(bridge.get("passages"), list) or len(bridge["passages"]) != 2:
        raise ValueError("passage bridge must identify exactly two passage scopes")
    if not isinstance(bridge.get("supporting_records"), list) or not bridge["supporting_records"]:
        raise ValueError("passage bridge must identify supporting CKL records")
    if bridge["direction"] not in _DIRECTIONS:
        raise ValueError("passage bridge has an invalid direction")
    if bridge["relationship_category"] not in _RELATIONSHIP_CATEGORIES:
        raise ValueError("passage bridge has an invalid relationship category")
    if bridge["evidence_layer"] not in _EVIDENCE_LAYERS:
        raise ValueError("passage bridge has an invalid evidence layer")
    normalized: list[str] = []
    for reference in bridge["passages"]:
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("passage bridge contains an invalid passage scope")
        spans = parse_scripture_references(reference, book_alias_lookup=_BOOK_ALIASES)
        if (
            len(spans) != 1
            or spans[0].start_chapter is None
            or (spans[0].end_chapter is not None and spans[0].end_chapter != spans[0].start_chapter)
        ):
            raise ValueError("passage bridge scope must fit one canonical chapter")
        normalized.append(format_scripture_reference(spans[0]))
    if normalized[0].casefold() == normalized[1].casefold():
        raise ValueError("passage bridge endpoints must differ")
    directional_fields = ("source_text_passage", "receiving_text_passage")
    if bridge["direction"] == "source_to_receiving_text":
        if any(not isinstance(bridge.get(key), str) or not bridge[key] for key in directional_fields):
            raise ValueError("source-to-receiving bridge must identify both historical text endpoints")
        for key in directional_fields:
            spans = parse_scripture_references(bridge[key], book_alias_lookup=_BOOK_ALIASES)
            if len(spans) != 1 or format_scripture_reference(spans[0]).casefold() not in {
                value.casefold() for value in normalized
            }:
                raise ValueError("historical text direction must use the bridge's exact passage endpoints")
        if (
            format_scripture_reference(
                parse_scripture_references(
                    bridge["source_text_passage"], book_alias_lookup=_BOOK_ALIASES
                )[0]
            ).casefold() != normalized[0].casefold()
            or format_scripture_reference(
                parse_scripture_references(
                    bridge["receiving_text_passage"], book_alias_lookup=_BOOK_ALIASES
                )[0]
            ).casefold() != normalized[1].casefold()
        ):
            raise ValueError("source-to-receiving bridge endpoints must be ordered source first")
        if bridge["source_text_passage"].casefold() == bridge["receiving_text_passage"].casefold():
            raise ValueError("historical source and receiving text endpoints must differ")
    elif any(key in bridge for key in directional_fields):
        raise ValueError("comparison bridge cannot claim a one-way historical text direction")
    for record in bridge["supporting_records"]:
        if not isinstance(record, Mapping) or any(
            not isinstance(record.get(key), str) or not record[key]
            for key in ("object_id", "record_kind")
        ):
            raise ValueError("passage bridge has an invalid supporting record")
        if record["record_kind"] not in _RECORD_COLLECTIONS:
            raise ValueError("passage bridge has an unsupported CKL record kind")
        if record["record_kind"] != "interpretive_note" and (
            not isinstance(record.get("record_id"), str) or not record["record_id"]
        ):
            raise ValueError("passage bridge support is missing its CKL record ID")
        if record["record_kind"] == "interpretive_note" and (
            not isinstance(record.get("content_hash"), str) or len(record["content_hash"]) != 64
        ):
            raise ValueError("unidentified interpretive-note support requires a content hash locator")
        if not isinstance(record.get("source_ids"), list) or not record["source_ids"] or any(
            not isinstance(source_id, str) or not source_id for source_id in record["source_ids"]
        ):
            raise ValueError("passage bridge support has no exact CKL source IDs")


def _record_reference_values(record: Mapping[str, Any]) -> list[str]:
    values = record.get("scripture_references")
    if not isinstance(values, list):
        return []
    references: list[str] = []
    for value in values:
        reference = value.get("reference") if isinstance(value, Mapping) else value
        if isinstance(reference, str) and reference.strip():
            references.append(reference.strip())
    return references


def _record_text(record: Mapping[str, Any]) -> str:
    return " ".join(
        str(record.get(key) or "")
        for key in ("claim", "note", "description", "primary_observation", "passage_relevance", "rationale", "notes")
    )


def _text_mentions_reference(record: Mapping[str, Any], reference: str) -> bool:
    normalize_dashes = lambda value: re.sub(r"[\u2010-\u2015\u2212]", "-", value)
    text = normalize_dashes(_record_text(record))
    value = normalize_dashes(reference)
    pattern = re.escape(value).replace(r"\ ", r"\s+")
    return re.search(rf"(?<![\w]){pattern}(?![\w])", text, flags=re.IGNORECASE) is not None


def _scope_contains(covering: Any, target: Any) -> bool:
    if covering.book.casefold() != target.book.casefold():
        return False

    def bounds(span: Any) -> tuple[tuple[int, int], tuple[int, int]]:
        if span.start_chapter is None:
            return (0, 0), (999, 999)
        start = (span.start_chapter, span.start_verse if span.start_verse is not None else 1)
        end_chapter = span.end_chapter if span.end_chapter is not None else span.start_chapter
        if span.end_verse is not None:
            end = (end_chapter, span.end_verse)
        elif span.start_verse is not None:
            end = (end_chapter, span.start_verse)
        else:
            end = (end_chapter, 999)
        return start, end

    covering_start, covering_end = bounds(covering)
    target_start, target_end = bounds(target)
    return covering_start <= target_start and target_end <= covering_end


def _supports_reference(record: Mapping[str, Any], reference: str) -> bool:
    target_spans = parse_scripture_references(reference, book_alias_lookup=_BOOK_ALIASES)
    if len(target_spans) != 1:
        return False
    for candidate in _record_reference_values(record):
        candidate_spans = parse_scripture_references(candidate, book_alias_lookup=_BOOK_ALIASES)
        if any(_scope_contains(scope, target_spans[0]) for scope in candidate_spans):
            return True
    return _text_mentions_reference(record, reference)


def _interpretive_note_hash(record: Mapping[str, Any]) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _find_support_record(
    object_record: Mapping[str, Any],
    support: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    values = object_record.get(_RECORD_COLLECTIONS[support["record_kind"]])
    if not isinstance(values, list):
        return None
    if support["record_kind"] == "interpretive_note":
        for value in values:
            if isinstance(value, Mapping) and _interpretive_note_hash(value) == support["content_hash"]:
                return value
        return None
    for value in values:
        if isinstance(value, Mapping) and value.get("id") == support["record_id"]:
            return value
    return None


def _resolve_bridge_support(
    bridge: Mapping[str, Any],
    source_resolver: Callable[[str], Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    support_payloads: list[dict[str, Any]] = []
    sources_by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    source_order: list[tuple[str, str]] = []
    endpoint_support = [False, False]
    for support in bridge["supporting_records"]:
        object_id = support["object_id"]
        parent = _canonical_mapping(source_resolver(object_id))
        if parent is None or parent.get("id") != object_id:
            return None
        record = _find_support_record(parent, support)
        if record is None:
            return None
        record_source_ids = record.get("source_ids", record.get("sources"))
        if not isinstance(record_source_ids, list) or not set(support["source_ids"]).issubset(set(record_source_ids)):
            return None
        source_records = parent.get("sources")
        if not isinstance(source_records, list):
            return None
        source_by_id = {
            value.get("id"): value
            for value in source_records
            if isinstance(value, Mapping) and isinstance(value.get("id"), str)
        }
        for source_id in support["source_ids"]:
            source = source_by_id.get(source_id)
            if source is None:
                return None
            source_identity = (object_id, source_id)
            if source_identity not in sources_by_identity:
                sources_by_identity[source_identity] = {
                    "id": source_id,
                    "object_id": object_id,
                    **{
                        key: source[key]
                        for key in ("title", "author", "publisher", "year", "locator", "url", "source_type", "supports", "notes")
                        if key in source
                    },
                }
                source_order.append(source_identity)
        for index, reference in enumerate(bridge["passages"]):
            endpoint_support[index] = endpoint_support[index] or _supports_reference(record, reference)
        stable_id = None
        identity_status = "recorded"
        record_id = support.get("record_id")
        if record_id:
            stable_id = f"ckl:{object_id}#{support['record_kind']}:{record_id}"
        else:
            identity_status = "no_standalone_id"
        summary = record.get("claim") or record.get("description") or record.get("note") or record.get("title") or ""
        support_payloads.append({
            "id": stable_id,
            "object_id": object_id,
            "record_kind": support["record_kind"],
            "record_id": record_id,
            "record_locator": (
                f"interpretive_note_sha256:{support['content_hash']}"
                if identity_status == "no_standalone_id"
                else None
            ),
            "identity_status": identity_status,
            "statement": str(summary),
            "certainty": record.get("certainty", record.get("confidence")),
            "dispute_status": record.get("dispute_status"),
            "source_ids": list(support["source_ids"]),
        })
    if not all(endpoint_support):
        return None
    return support_payloads, [sources_by_identity[key] for key in source_order]


def _valid_passage_reference(reference: Any) -> bool:
    if not isinstance(reference, str) or not reference.strip():
        return False
    spans = parse_scripture_references(reference, book_alias_lookup=_BOOK_ALIASES)
    return len(spans) == 1 and spans[0].start_chapter is not None and (
        spans[0].end_chapter is None or spans[0].end_chapter == spans[0].start_chapter
    )


def _authored_pathways(passage_reference: str, connections: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    pathways: dict[tuple[str, str], dict[str, Any]] = {}
    for connection in connections:
        if not isinstance(connection, Mapping):
            continue
        curation = connection.get("curation")
        basis = connection.get("basis")
        if not isinstance(curation, Mapping) or not isinstance(basis, Mapping):
            continue
        if basis.get("kind") not in {"ckl_related_object", "ckl_related_evidence"}:
            continue
        if not any(references_overlap(passage_reference, reference) for reference in curation.get("applicable_passages", []) if isinstance(reference, str)):
            continue
        for destination in curation.get("supporting_passages", []):
            if not _valid_passage_reference(destination) or references_overlap(passage_reference, destination):
                continue
            item = {
                "id": f"authored:{connection.get('id', '')}:{destination}",
                "provenance": "authored_ckl_relationship",
                "source_passage": passage_reference,
                "destination_passage": destination,
                "relationship_category": curation.get("classification", "uncategorized"),
                "original_relationship_type": connection.get("original_relationship_type"),
                "source_id": connection.get("source_id"),
                "target_id": connection.get("target_id"),
                "direction": connection.get("direction", "one_way"),
                "relationship_mode": connection.get("relationship_mode", "not_recorded"),
                "temporal_layer": connection.get("temporal_layer", "unknown"),
                "basis": dict(basis),
                "curation": dict(curation),
                "explanation": str(curation.get("why") or ""),
                "uncertainty": str(curation.get("uncertainty") or ""),
                "supporting_record_ids": list(curation.get("supporting_records") or []),
                "supporting_ckl_sources": list(curation.get("supporting_ckl_sources") or []),
            }
            pathways[(str(connection.get("id")), destination)] = item
    return [pathways[key] for key in sorted(pathways)]


def build_related_passages(
    passage_reference: str,
    *,
    connections: Sequence[Mapping[str, Any]],
    source_resolver: Callable[[str], Any],
    bridge_records: Sequence[Mapping[str, Any]] | None = None,
    query_status: str = "complete",
    reason_code: str | None = None,
) -> dict[str, Any]:
    """Build separate authored and evidence-backed passage route collections."""

    registry = tuple(bridge_records) if bridge_records is not None else load_passage_bridges()
    authored = _authored_pathways(passage_reference, connections)
    bridges: list[dict[str, Any]] = []
    support_unavailable = False
    resolved_objects: dict[str, Any] = {}
    attempted_objects: set[str] = set()

    def resolve_source(object_id: str) -> Any:
        if object_id not in attempted_objects:
            attempted_objects.add(object_id)
            try:
                resolved_objects[object_id] = source_resolver(object_id)
            except Exception:  # A failed support lookup must remain visibly incomplete.
                resolved_objects[object_id] = None
        return resolved_objects[object_id]

    for bridge in registry:
        _validate_bridge_shape(bridge)
        if not any(references_overlap(passage_reference, reference) for reference in bridge["passages"]):
            continue
        resolved = _resolve_bridge_support(bridge, resolve_source)
        if resolved is None:
            support_unavailable = True
            continue
        support_payloads, source_payloads = resolved
        source_passage, destination_passage = bridge["passages"]
        if references_overlap(passage_reference, destination_passage):
            source_passage, destination_passage = destination_passage, source_passage
        route = {
            "id": bridge["id"],
            "provenance": "ckl_documented_" + bridge["supporting_records"][0]["record_kind"],
            "source_passage": source_passage,
            "destination_passage": destination_passage,
            "relationship_category": bridge["relationship_category"],
            "evidence_layer": bridge["evidence_layer"],
            "direction": bridge["direction"],
            "relationship_mode": "documented_interpretation",
            "explanation": bridge["explanation"],
            "uncertainty": bridge["uncertainty"],
            "human_scholarly_approval": "not_recorded",
            "supporting_records": support_payloads,
            "supporting_sources": source_payloads,
        }
        if bridge["direction"] == "source_to_receiving_text":
            route["source_text_passage"] = bridge["source_text_passage"]
            route["receiving_text_passage"] = bridge["receiving_text_passage"]
        bridges.append(route)
    bridges.sort(key=lambda item: (item["destination_passage"], item["id"]))
    authored.sort(key=lambda item: (item["destination_passage"], item["id"]))

    source_status = query_status if query_status in {"complete", "partial", "failed"} else "failed"
    has_routes = bool(authored or bridges)
    if source_status == "failed":
        state = "unknown"
        description = "The CKL lookup did not finish; more passage routes may be available."
    elif source_status == "partial":
        state = "partial"
        description = "The CKL lookup is incomplete; more passage routes may be available."
    elif support_unavailable:
        state = "partial" if has_routes else "unknown"
        description = "Some CKL bridge records could not be verified; route availability is incomplete."
        reason_code = reason_code or "bridge_support_unavailable"
    elif has_routes:
        state = "available"
        description = "Passage routes are available from the records listed here."
    else:
        state = "not_represented"
        description = "No route was returned from this passage pathway. This does not establish that no relationship exists."
    return {
        "state": state,
        "query_status": source_status,
        "reason_code": reason_code,
        "description": description,
        "authored_relationships": authored,
        "evidence_backed_bridges": bridges,
    }


def validate_passage_bridge_registry(
    bridge_records: Sequence[Mapping[str, Any]],
    source_resolver: Callable[[str], Any],
) -> int:
    """Validate every registry entry against the exact current CKL record IDs."""

    seen: set[str] = set()
    for bridge in bridge_records:
        _validate_bridge_shape(bridge)
        if bridge["id"] in seen:
            raise ValueError(f"duplicate NE-10 passage bridge id: {bridge['id']}")
        seen.add(bridge["id"])
        if _resolve_bridge_support(bridge, source_resolver) is None:
            raise ValueError(f"passage bridge {bridge['id']} has missing, mismatched, or unscoped CKL support")
    return len(seen)


def validate_related_passages(value: Any) -> None:
    """Validate the reader-facing routes without merging their provenance."""

    if not isinstance(value, Mapping):
        raise ValueError("related passage routes must be an object")
    if value.get("state") not in {"available", "partial", "unknown", "not_represented"}:
        raise ValueError("related passage routes have an invalid state")
    if value.get("query_status") not in {"complete", "partial", "failed"}:
        raise ValueError("related passage routes have an invalid query status")
    if not isinstance(value.get("description"), str) or not value["description"]:
        raise ValueError("related passage routes require a coverage description")
    if value["query_status"] == "failed" and value["state"] != "unknown":
        raise ValueError("failed passage lookup cannot claim complete route coverage")
    if value["query_status"] == "partial" and value["state"] != "partial":
        raise ValueError("partial passage lookup cannot claim complete route coverage")
    if value["state"] == "not_represented" and (
        value["query_status"] != "complete" or "does not establish" not in value["description"]
    ):
        raise ValueError("only a complete route lookup may report not represented, with an absence caveat")
    for collection_name, provenance in (
        ("authored_relationships", "authored_ckl_relationship"),
        ("evidence_backed_bridges", None),
    ):
        collection = value.get(collection_name)
        if not isinstance(collection, list):
            raise ValueError(f"{collection_name} must be a list")
        seen: set[str] = set()
        for route in collection:
            if not isinstance(route, Mapping):
                raise ValueError("related passage route has an invalid shape")
            if not all(
                isinstance(route.get(key), str) and route[key]
                for key in ("id", "source_passage", "destination_passage", "relationship_category", "explanation", "uncertainty")
            ):
                raise ValueError("related passage route is missing its identity or explanation")
            if route["id"] in seen:
                raise ValueError("related passage route IDs must be unique within their provenance")
            seen.add(route["id"])
            if not _valid_passage_reference(route["source_passage"]) or not _valid_passage_reference(route["destination_passage"]):
                raise ValueError("related passage route has an invalid passage scope")
            if (
                provenance is not None and route.get("provenance") != provenance
            ) or (
                provenance is None and not str(route.get("provenance") or "").startswith("ckl_documented_")
            ):
                raise ValueError("related passage route provenance is mislabeled")
            if collection_name == "authored_relationships":
                if not isinstance(route.get("basis"), Mapping) or route["basis"].get("kind") not in {
                    "ckl_related_object", "ckl_related_evidence"
                }:
                    raise ValueError("authored passage route must preserve an authored CKL edge")
                if not isinstance(route.get("curation"), Mapping):
                    raise ValueError("authored passage route must preserve its curation record")
                if route.get("direction") not in {"one_way", "reciprocal"}:
                    raise ValueError("authored passage route must preserve its original direction")
                if not isinstance(route.get("supporting_record_ids"), list) or not route["supporting_record_ids"]:
                    raise ValueError("authored passage route must retain support record identity")
            else:
                if route.get("human_scholarly_approval") != "not_recorded":
                    raise ValueError("evidence-backed bridge cannot imply human approval")
                if route.get("relationship_mode") != "documented_interpretation":
                    raise ValueError("evidence-backed bridge must identify its interpretation provenance")
                if not isinstance(route.get("supporting_records"), list) or not route["supporting_records"]:
                    raise ValueError("evidence-backed bridge must retain CKL record identity")
                if not isinstance(route.get("supporting_sources"), list) or not route["supporting_sources"]:
                    raise ValueError("evidence-backed bridge must retain record-attached bibliography")
