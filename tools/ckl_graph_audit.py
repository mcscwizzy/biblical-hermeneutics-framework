#!/usr/bin/env python3
"""Audit CKL relationship graph hygiene."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.canonical_library import CanonicalLibrary, graph_audit
from framework.canonical_library.authoring import DEFAULT_AUTHORING_ROOT, resolve_authoring_root
from framework.canonical_library.normalization import normalize_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit CKL relationship graph edges.")
    parser.add_argument(
        "--root",
        default=str(DEFAULT_AUTHORING_ROOT),
        help="CKL root directory",
    )
    parser.add_argument(
        "--object",
        action="append",
        dest="object_ids",
        default=[],
        help="Limit missing reverse-edge suggestions to edges touching this object id; repeat to add more.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum missing reverse-edge suggestions to print",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of text",
    )
    return parser


def _filtered_suggestions(audit: Any, object_ids: list[str]) -> list[Any]:
    wanted = {normalize_id(object_id) for object_id in object_ids if normalize_id(object_id)}
    if not wanted:
        return list(audit.missing_reverse_edges)
    return [
        suggestion
        for suggestion in audit.missing_reverse_edges
        if suggestion.source_id in wanted or suggestion.target_id in wanted
    ]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        root = resolve_authoring_root(args.root)
        library = CanonicalLibrary(root=root).load()
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}")
        return 1

    audit = graph_audit(library.objects_by_id)
    suggestions = _filtered_suggestions(audit, args.object_ids)
    shown = suggestions[: max(args.limit, 0)]

    payload = {
        "object_count": audit.object_count,
        "edge_count": audit.edge_count,
        "missing_reverse_edge_count": len(audit.missing_reverse_edges),
        "filtered_missing_reverse_edge_count": len(suggestions),
        "orphaned_object_count": len(audit.orphaned_object_ids),
        "unknown_target_edge_count": len(audit.unknown_target_edges),
        "orphaned_object_ids": audit.orphaned_object_ids,
        "unknown_target_edges": [edge.to_dict() for edge in audit.unknown_target_edges],
        "missing_reverse_edges": [suggestion.to_dict() for suggestion in shown],
    }

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    print("CKL relationship graph audit")
    print(f"- Objects: {payload['object_count']}")
    print(f"- Edges: {payload['edge_count']}")
    print(f"- Missing reverse edges: {payload['missing_reverse_edge_count']}")
    if args.object_ids:
        print(f"- Filtered missing reverse edges: {payload['filtered_missing_reverse_edge_count']}")
    print(f"- Orphaned objects: {payload['orphaned_object_count']}")
    print(f"- Unknown target edges: {payload['unknown_target_edge_count']}")

    if audit.orphaned_object_ids:
        print("\nOrphaned objects:")
        for object_id in audit.orphaned_object_ids[: args.limit]:
            print(f"- {object_id}")

    if shown:
        print("\nMissing reverse edge suggestions:")
        for index, suggestion in enumerate(shown, start=1):
            print(
                f"{index}. {suggestion.target_id} -> {suggestion.source_id} "
                f"({suggestion.suggested_relationship}, weight={suggestion.weight})"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
