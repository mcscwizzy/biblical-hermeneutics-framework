#!/usr/bin/env python3
"""Create CKL object templates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.canonical_library import CATEGORY_FOLDERS
from framework.canonical_library.authoring import (
    canonical_object_template,
    dump_json_text,
    resolve_authoring_root,
    write_json_file,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a CKL object template.")
    parser.add_argument("--type", required=True, help="CKL object type, such as person or place")
    parser.add_argument("--id", required=True, help="Canonical object id")
    parser.add_argument("--title", help="Display title to use instead of deriving one from the id")
    parser.add_argument(
        "--alias",
        action="append",
        dest="aliases",
        default=[],
        help="Additional retrieval alias; repeat to add more",
    )
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT / "framework" / "canonical_library"),
        help="CKL root directory used to infer the default write path",
    )
    parser.add_argument(
        "--path",
        help="Explicit output path to use when writing the object",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the generated object to disk instead of stdout",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing file when used with --write",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        obj = canonical_object_template(
            args.type,
            args.id,
            title=args.title,
            aliases=args.aliases,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}")
        return 1

    if not args.write:
        print(dump_json_text(obj.to_dict()), end="")
        return 0

    if args.path:
        output_path = Path(args.path)
    else:
        root_candidate = Path(args.root)
        try:
            root = resolve_authoring_root(root_candidate)
        except FileNotFoundError:
            root = root_candidate.resolve()
        output_path = root / "objects" / CATEGORY_FOLDERS[obj.type] / f"{obj.id}.json"

    if output_path.exists() and not args.force:
        print(f"error: {output_path} already exists; pass --force to overwrite")
        return 1

    try:
        write_json_file(output_path, obj.to_dict())
    except OSError as exc:
        print(f"error: {exc}")
        return 1
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
