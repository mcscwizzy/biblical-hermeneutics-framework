#!/usr/bin/env python3
"""Inspect and evaluate the provider-free contextual presentation pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.presentation.evaluation_suite import (
    evaluate_presentation_fixtures,
    format_presentation_eval,
)


DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "presentation_passages.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build, rank, render, and validate contextual presentation fixtures "
            "without a model or network call."
        )
    )
    parser.add_argument(
        "--fixture",
        default=str(DEFAULT_FIXTURE),
        help="presentation fixture JSON (defaults to the three evaluation passages)",
    )
    parser.add_argument(
        "--reference",
        action="append",
        default=[],
        help="evaluate one passage reference; repeat to select multiple cases",
    )
    parser.add_argument("--candidate-limit", type=int, default=8)
    parser.add_argument("--maximum-cards", type=int, default=3)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.candidate_limit < 1:
        print("error: --candidate-limit must be at least 1", file=sys.stderr)
        return 2
    if args.maximum_cards < 0:
        print("error: --maximum-cards cannot be negative", file=sys.stderr)
        return 2
    try:
        result = evaluate_presentation_fixtures(
            args.fixture,
            references=args.reference,
            candidate_limit=args.candidate_limit,
            maximum_cards=args.maximum_cards,
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_presentation_eval(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
