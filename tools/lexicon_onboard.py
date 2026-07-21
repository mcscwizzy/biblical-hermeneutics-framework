#!/usr/bin/env python3
"""Validate lexical source manifests and runtime coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.canonical_library.database_schema import DEFAULT_CKL_DATABASE_PATH
from framework.canonical_library.lexicon_onboarding import (
    build_onboarding_report,
    format_onboarding_report,
    report_has_failures,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate local lexical source onboarding and SQLite coverage."
    )
    parser.add_argument(
        "--manifest",
        help="Local lexicon source manifest JSON to validate",
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_CKL_DATABASE_PATH,
        help="CKL SQLite database to check for lexical coverage",
    )
    parser.add_argument(
        "--coverage-json",
        help="Optional JSON list of coverage checks; defaults to John 1:1 and Psalm 23:6",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = build_onboarding_report(
            manifest_path=args.manifest,
            database_path=args.database,
            coverage_path=args.coverage_json,
        )
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(format_onboarding_report(report))
    return 1 if report_has_failures(report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
