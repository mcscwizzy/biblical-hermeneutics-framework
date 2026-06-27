#!/usr/bin/env python3
"""Run local deterministic BHF Agent evals."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.config import ConfigError
from bhf_agent.eval import (
    answer_from_agent,
    answer_from_file,
    format_human_summary,
    load_fixture,
    result_to_json,
    score_answer,
)
from bhf_agent.profiles import ProfileError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score a BHF Agent answer with local deterministic heuristics."
    )
    parser.add_argument("--fixture", required=True, help="JSON eval fixture path")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--answer-file", help="Saved answer text file to score")
    source.add_argument("--config", help="Agent config JSON for optional model-call mode")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        fixture = load_fixture(args.fixture)
        if args.answer_file:
            answer = answer_from_file(args.answer_file)
        else:
            answer = answer_from_agent(fixture, args.config)
        result = score_answer(answer, fixture)
    except (ConfigError, FileNotFoundError, ProfileError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(result_to_json(result))
    else:
        print(format_human_summary(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
