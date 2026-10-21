"""Measure JSON-backed NE-10 startup, route counts, and projection payloads."""

from __future__ import annotations

import json
from pathlib import Path
import statistics
import sys
import time
from dataclasses import replace
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bhf_agent.presentation.models import mapping
from bhf_agent.presentation.narrative_explorer import (
    DomainLookup,
    _child_local_id,
    _ckl_stable_id,
    _related_evidence_connection,
    _related_object_connection,
)
from bhf_agent.presentation.narrative_explorer_curations import CURATION_BY_IDENTITY, curate_connection
from bhf_agent.presentation.narrative_explorer_passages import _authored_pathways
from bhf_agent.presentation.references import references_overlap
from bhf_web.services.narrative_explorer import NarrativeExplorerService
from framework.canonical_library.json_repository import JsonCanonicalRepository


PASSAGES = (
    ("Genesis", 1),
    ("Genesis", 3),
    ("Genesis", 6),
    ("Deuteronomy", 32),
    ("Psalm", 82),
    ("Job", 1),
    ("Isaiah", 43),
    ("Ezekiel", 37),
    ("John", 1),
    ("Revelation", 21),
)


def empty_maps(**_request: object) -> DomainLookup:
    return DomainLookup(domain="maps", query_status="complete")


def empty_archaeology(**_request: object) -> DomainLookup:
    return DomainLookup(domain="archaeology", query_status="complete")


def _reference_texts(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        reference.strip()
        for item in value
        if isinstance((reference := item.get("reference") if isinstance(item, dict) else item), str)
        and reference.strip()
    ]


def _records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def count_authored_passage_routes(library: Any) -> int:
    """Count active curated edge/destination pairs across the CKL corpus."""

    objects = [mapping(value) for value in library.objects_by_id.values()]
    target_scopes: dict[str, dict[str, list[str]]] = {}
    for parent in objects:
        parent_id = parent.get("id")
        if not isinstance(parent_id, str):
            continue
        target_scopes[parent_id] = {
            local_id: _reference_texts(record.get("scripture_references"))
            for record in _records(parent.get("evidence_items"))
            if (local_id := _child_local_id("evidence", record))
        }

    routes: set[tuple[str, str]] = set()

    def add_edge(edge: Any, passage_scopes: list[str], parent_id: str) -> None:
        if edge is None:
            return
        kind = "evidence" if edge.basis.get("kind") == "ckl_related_evidence" else "object"
        identity = (
            kind,
            edge.source_id,
            edge.target_id,
            edge.original_relationship_type,
            edge._authored_notes,
            edge.basis.get("weight"),
        )
        curation = CURATION_BY_IDENTITY.get(identity)
        if curation is None:
            return
        for applicable in curation["applicable_passages"]:
            if not any(references_overlap(applicable, scope) for scope in passage_scopes):
                continue
            candidate = edge
            if kind == "evidence":
                target_id = edge.basis.get("target_evidence_id")
                scopes = target_scopes.get(parent_id, {}).get(target_id, [])
                if not isinstance(target_id, str) or not any(
                    references_overlap(applicable, scope) for scope in scopes
                ):
                    continue
                candidate = replace(
                    edge,
                    basis={**edge.basis, "target_resolution_status": "eligible"},
                )
            curated = curate_connection(candidate, applicable)
            if curated.curation is None:
                continue
            for route in _authored_pathways(applicable, [curated.to_dict()]):
                routes.add((route["id"], route["destination_passage"]))

    for parent in objects:
        parent_id = parent.get("id")
        if not isinstance(parent_id, str):
            continue
        if str(parent.get("type") or "").casefold() != "book":
            for relation in _records(parent.get("related_objects")):
                add_edge(
                    _related_object_connection(
                        source_id=f"ckl:{parent_id}",
                        parent_id=parent_id,
                        local_id=None,
                        relation=relation,
                        assertion_type=None,
                    ),
                    _reference_texts(parent.get("scripture_references")),
                    parent_id,
                )
        for collection, record_kind in (
            ("claims", "claim"),
            ("evidence_items", "evidence"),
            ("interpretive_notes", "interpretive_note"),
        ):
            for record in _records(parent.get(collection)):
                local_id = _child_local_id(record_kind, record)
                if not local_id:
                    continue
                source_id = _ckl_stable_id(parent_id, record_kind, local_id)
                passage_scopes = _reference_texts(record.get("scripture_references"))
                for relation in _records(record.get("related_objects")):
                    add_edge(
                        _related_object_connection(
                            source_id=source_id,
                            parent_id=parent_id,
                            local_id=local_id,
                            relation=relation,
                            assertion_type=record.get("assertion_type"),
                        ),
                        passage_scopes,
                        parent_id,
                    )
                for relation in _records(record.get("related_evidence")):
                    add_edge(
                        _related_evidence_connection(
                            source_id=source_id,
                            parent_id=parent_id,
                            local_id=local_id,
                            relation=relation,
                            assertion_type=record.get("assertion_type"),
                        ),
                        passage_scopes,
                        parent_id,
                    )
    return len(routes)


def main() -> None:
    root = PROJECT_ROOT / "framework" / "canonical_library"
    started = time.perf_counter()
    library = JsonCanonicalRepository(root=root).library
    index_load_ms = (time.perf_counter() - started) * 1000
    service = NarrativeExplorerService(
        study_db_path=PROJECT_ROOT / ".bhf-data" / "study.sqlite",
        canonical_library_provider=lambda: library,
        maps_lookup_provider=empty_maps,
        archaeology_lookup_provider=empty_archaeology,
    )

    durations_ms: list[float] = []
    payload_bytes: list[int] = []
    base_payload_bytes: list[int] = []
    authored_routes: set[str] = set()
    bridge_routes: set[str] = set()
    route_rows = {"authored_relationships": 0, "evidence_backed_bridges": 0}
    per_passage: list[dict[str, object]] = []
    for book, chapter in PASSAGES:
        before = time.perf_counter()
        payload = service.build(book, chapter)
        durations_ms.append((time.perf_counter() - before) * 1000)
        payload_bytes.append(len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))
        base_payload = {key: value for key, value in payload.items() if key != "related_passages"}
        base_payload_bytes.append(len(json.dumps(base_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))
        routes = payload["related_passages"]
        route_rows["authored_relationships"] += len(routes["authored_relationships"])
        route_rows["evidence_backed_bridges"] += len(routes["evidence_backed_bridges"])
        authored_routes.update(route["id"] for route in routes["authored_relationships"])
        bridge_routes.update(route["id"] for route in routes["evidence_backed_bridges"])
        per_passage.append({
            "passage": f"{book} {chapter}",
            "projection_ms": round(durations_ms[-1], 2),
            "payload_bytes": payload_bytes[-1],
            "related_passages_payload_delta_bytes": payload_bytes[-1] - base_payload_bytes[-1],
            "authored_relationships": len(routes["authored_relationships"]),
            "evidence_backed_bridges": len(routes["evidence_backed_bridges"]),
        })

    deltas = [after - before for after, before in zip(payload_bytes, base_payload_bytes)]
    result = {
        "backend": "JSON CKL repository, same fallback path used when the SQLite index is absent",
        "index_load_ms": round(index_load_ms, 2),
        "passage_count": len(PASSAGES),
        "first_passage_projection_ms": round(durations_ms[0], 2),
        "median_passage_projection_ms": round(statistics.median(durations_ms), 2),
        "max_passage_projection_ms": round(max(durations_ms), 2),
        "median_payload_bytes": int(statistics.median(payload_bytes)),
        "max_payload_bytes": max(payload_bytes),
        "median_related_passages_payload_delta_bytes": int(statistics.median(deltas)),
        "max_related_passages_payload_delta_bytes": max(deltas),
        "route_rows_by_provenance": route_rows,
        "unique_authored_route_ids": len(authored_routes),
        "unique_evidence_bridge_ids": len(bridge_routes),
        "corpus_authored_passage_route_count": count_authored_passage_routes(library),
        "per_passage": per_passage,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
