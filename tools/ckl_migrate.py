#!/usr/bin/env python3
"""Normalize CKL object JSON to the current schema shape."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.canonical_library.authoring import (
    DEFAULT_AUTHORING_ROOT,
    dump_json_text,
    format_validation_summary,
    migrate_object_file,
    normalize_object_mapping,
    read_json_file,
    resolve_authoring_root,
    scan_library,
    write_json_file,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize CKL object JSON.")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--path", help="Normalize a single CKL object file")
    scope.add_argument(
        "--root",
        default=str(DEFAULT_AUTHORING_ROOT),
        help="Normalize every object file under this CKL root",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write normalized JSON back to disk",
    )
    return parser


def _migrate_single(path: str, *, write: bool) -> int:
    file_path = Path(path)
    try:
        normalized, changed = migrate_object_file(file_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}")
        return 1
    if write:
        try:
            write_json_file(file_path, normalized)
        except OSError as exc:
            print(f"error: {exc}")
            return 1
        print(f"{'updated' if changed else 'checked'} {file_path}")
        return 0
    print(dump_json_text(normalized), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.path:
        return _migrate_single(args.path, write=args.write)

    try:
        root = resolve_authoring_root(args.root)
        audit = scan_library(root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}")
        return 1
    if audit.has_errors:
        print(format_validation_summary(audit))
        return 1

    changed_paths: list[str] = []
    for path in audit.object_paths:
        raw = read_json_file(path)
        normalized, changed = normalize_object_mapping(raw, path=path.relative_to(root).as_posix())
        if changed and args.write:
            try:
                write_json_file(path, normalized)
            except OSError as exc:
                print(f"error: {exc}")
                return 1
        if changed:
            changed_paths.append(path.relative_to(root).as_posix())

    if args.write:
        if changed_paths:
            print("updated " + ", ".join(changed_paths))
        else:
            print("library already normalized")
    else:
        if changed_paths:
            print("would update " + ", ".join(changed_paths))
        else:
            print("library already normalized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
