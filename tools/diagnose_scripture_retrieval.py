#!/usr/bin/env python3
"""Development-only explainable CKL Scripture-reference retrieval diagnostic.

This utility intentionally uses the same CKL loader and EvidenceBundle
projection as chapter commentary. It does not call an AI provider or write CKL
or commentary data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bhf_agent.ckl import load_canonical_library
from bhf_agent.presentation import build_evidence_bundle
from framework.canonical_library import CKLRepositoryConfig
from framework.canonical_library.scripture import (
    format_scripture_reference,
    parse_scripture_query,
    parse_scripture_references,
    scripture_reference_overlaps,
)


def _reference_entries(library: Any, obj: Any) -> list[dict[str, Any]]:
    data = obj.to_dict()
    entries: list[dict[str, Any]] = []

    def add(source: str, raw: Any) -> None:
        value = str(raw or "").strip()
        spans = parse_scripture_references(value, book_alias_lookup=library._book_alias_lookup)
        entries.append(
            {
                "source": source,
                "raw": value,
                "normalized": [format_scripture_reference(span) for span in spans],
            }
        )

    for index, reference in enumerate(data.get("scripture_references") or []):
        add(f"object.scripture_references[{index}]", reference.get("reference") if isinstance(reference, dict) else reference)
    for collection_name in ("evidence_items", "claims", "interpretive_notes"):
        for index, item in enumerate(data.get(collection_name) or []):
            if not isinstance(item, dict):
                continue
            values = item.get("scripture_references") or item.get("scripture_anchors") or []
            if not isinstance(values, (list, tuple)):
                values = [values]
            for ref_index, reference in enumerate(values):
                raw = reference.get("reference") if isinstance(reference, dict) else reference
                add(f"{collection_name}[{index}].scripture_references[{ref_index}]", raw)
    return entries


def diagnose(reference: str, library: Any) -> dict[str, Any]:
    query = parse_scripture_query(reference, book_alias_lookup=library._book_alias_lookup)
    results = library.retrieve_by_scripture_reference(reference, limit=100)
    result_by_id = {result.object.id: result for result in results}

    candidate_ids = sorted(library._scripture_book_index.get(query.book, set())) if query else []
    bundle = build_evidence_bundle(reference, canonical_results=results)
    admitted_by_parent: dict[str, list[str]] = {}
    for item in bundle.evidence_items:
        parent_id = str(item.relevance_metadata.get("parent_object_id") or "")
        if parent_id:
            admitted_by_parent.setdefault(parent_id, []).append(item.id)

    candidates: list[dict[str, Any]] = []
    for object_id in candidate_ids:
        obj = library.objects_by_id[object_id]
        anchors = _reference_entries(library, obj)
        overlaps = [
            anchor
            for anchor in anchors
            if any(
                scripture_reference_overlaps(query, span)
                for span in parse_scripture_references(
                    anchor["raw"],
                    book_alias_lookup=library._book_alias_lookup,
                )
            )
        ]
        # The exact overlap test is delegated to the production result set;
        # this field explains whether the record survived that same filter.
        candidates.append(
            {
                "record_id": object_id,
                "record_type": obj.type,
                "title": obj.title,
                "scripture_anchors": anchors,
                "overlapping_anchor_entries": overlaps,
                "match": "scripture" if object_id in result_by_id else "rejected",
                "score": getattr(result_by_id.get(object_id), "score", None),
                "admissible_for_chapter_commentary": bool(admitted_by_parent.get(object_id)),
                "admitted_evidence_ids": admitted_by_parent.get(object_id, []),
            }
        )

    return {
        "requested_reference": reference,
        "raw_candidate_count": len(candidate_ids),
        "valid_scripture_anchored_result_count": len(results),
        "rejected_candidate_count": sum(candidate["match"] == "rejected" for candidate in candidates),
        "evidence_categories": sorted({item.category for item in bundle.evidence_items}),
        "commentary_evidence_count": len(bundle.evidence_items),
        "data_gap": not bool(bundle.evidence_items),
        "candidates": candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("references", nargs="+", help="Scripture references to diagnose")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    library = load_canonical_library(config=CKLRepositoryConfig())
    payload = [diagnose(reference, library) for reference in args.references]
    text = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
