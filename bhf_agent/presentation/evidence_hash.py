"""Deterministic fingerprints for meaningful passage evidence state."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import EvidenceBundle


def calculate_evidence_hash(bundle: EvidenceBundle) -> str:
    """Hash grounding inputs while excluding UI-only and unrelated metadata."""

    source_ids = {
        source_id for item in bundle.evidence_items for source_id in item.source_ids
    }
    object_ids = {
        str(item.relevance_metadata.get("parent_object_id") or "")
        for item in bundle.evidence_items
    }
    object_ids.update(bundle.entities_by_id)
    object_ids.discard("")
    payload: dict[str, Any] = {
        "passage_ref": bundle.passage_ref,
        "version": bundle.version,
        "entities": {
            bucket: [
                {
                    "id": entity.id,
                    "title": entity.title,
                    "type": entity.type,
                    "aliases": entity.aliases,
                }
                for entity in bundle.entities.get(bucket, [])
            ]
            for bucket in bundle.entities
        },
        # Retrieval scores are backend-specific ranking metadata.  JSON and
        # SQLite must produce the same grounding identity even when their
        # equivalent rankers represent a score with slightly different
        # floating-point values.  The score remains visible in the bundle for
        # ranking and diagnostics; it is not evidence state.
        "evidence_items": [_stable_evidence_item(item) for item in bundle.evidence_items],
        "geography": {
            kind: [
                {
                    "id": _text(item.get("id")),
                    "title": _text(item.get("title") or item.get("name")),
                }
                for item in bundle.geography.get(kind, [])
            ]
            for kind in ("places", "routes")
        },
        "provenance": {
            "sources": [
                source
                for source in bundle.provenance.get("sources", [])
                if str(source.get("id") or "") in source_ids
            ],
            "canonical_objects": [
                {
                    key: item.get(key)
                    for key in ("id", "type", "object_version", "review_status")
                }
                for item in bundle.provenance.get("canonical_objects", [])
                if str(item.get("id") or "") in object_ids
            ],
        },
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _stable_evidence_item(item: Any) -> dict[str, Any]:
    """Return evidence content without volatile retrieval-ranking metadata."""

    data = item.to_dict()
    metadata = dict(data.get("relevance_metadata") or {})
    metadata.pop("retrieval_score", None)
    data["relevance_metadata"] = metadata
    return data
