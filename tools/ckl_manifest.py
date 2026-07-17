#!/usr/bin/env python3
"""Regenerate the CKL manifest from the current object inventory."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.canonical_library.authoring import (
    DEFAULT_AUTHORING_ROOT,
    build_manifest,
    format_validation_summary,
    resolve_authoring_root,
    scan_library,
    write_json_file,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Regenerate the CKL manifest.")
    parser.add_argument(
        "--root",
        default=str(DEFAULT_AUTHORING_ROOT),
        help="CKL root directory",
    )
    parser.add_argument(
        "--output",
        help="Write the manifest to this path instead of the default manifest.json",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the regenerated manifest to the default location",
    )
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="Stamp the manifest with the current UTC timestamp",
    )
    return parser


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        root = resolve_authoring_root(args.root)
        audit = scan_library(root, include_manifest=False)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}")
        return 1
    if audit.has_errors:
        print(format_validation_summary(audit))
        return 1

    manifest = audit.generated_manifest or build_manifest(audit.valid_objects.values())
    if args.stamp:
        manifest = dict(manifest)
        manifest["generated_at"] = _timestamp()

    output_path = None
    if args.output:
        output_path = Path(args.output)
    elif args.write:
        output_path = root / "manifest.json"

    if output_path is not None:
        try:
            write_json_file(output_path, manifest)
        except OSError as exc:
            print(f"error: {exc}")
            return 1
        print(f"wrote {output_path}")
        return 0

    print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
