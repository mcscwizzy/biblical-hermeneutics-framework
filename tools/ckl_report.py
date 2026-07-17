#!/usr/bin/env python3
"""Report CKL inventory status."""

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
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report CKL inventory status.")
    parser.add_argument(
        "--root",
        default=str(DEFAULT_AUTHORING_ROOT),
        help="CKL root directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the inventory audit as JSON instead of text",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    audit = scan_library(args.root)
    if args.json:
        print(json.dumps(audit.to_dict(), indent=2, ensure_ascii=True))
    else:
        print(format_validation_summary(audit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
