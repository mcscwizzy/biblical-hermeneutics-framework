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
from framework.canonical_library.quality_report import (
    build_quality_report,
    format_quality_markdown,
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
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Include Phase 1 depth, graph, sourcing, duplicate, and governance metrics",
    )
    parser.add_argument(
        "--output",
        help="Write the report to this file instead of standard output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.deep:
        report = build_quality_report(args.root)
        if args.json:
            rendered = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
        else:
            rendered = format_quality_markdown(report)
    else:
        audit = scan_library(args.root)
        if args.json:
            rendered = json.dumps(audit.to_dict(), indent=2, ensure_ascii=True) + "\n"
        else:
            rendered = format_validation_summary(audit) + "\n"
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        print(f"wrote {output_path}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
