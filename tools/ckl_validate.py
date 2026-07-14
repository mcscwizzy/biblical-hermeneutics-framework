#!/usr/bin/env python3
"""Validate CKL objects or the full library."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.canonical_library.authoring import (
    DEFAULT_AUTHORING_ROOT,
    format_validation_summary,
    scan_library,
    validate_single_object,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate CKL objects.")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--path", help="Validate a single object file")
    scope.add_argument(
        "--root",
        default=str(DEFAULT_AUTHORING_ROOT),
        help="Validate the CKL library under this root",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the audit as JSON instead of a human-readable summary",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        audit = validate_single_object(args.path) if args.path else scan_library(args.root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}")
        return 1

    if args.json:
        print(json.dumps(audit.to_dict(), indent=2, ensure_ascii=True))
    else:
        print(format_validation_summary(audit))
    return 1 if audit.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
