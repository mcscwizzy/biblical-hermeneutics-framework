#!/usr/bin/env python3
"""Validate an offline presentation bundle before deployment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.presentation import (
    PresentationBundleError,
    inspect_presentation_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Structurally validate a versioned offline presentation bundle "
            "without making model or network calls."
        )
    )
    parser.add_argument("--bundle", required=True, help="presentation bundle JSON path")
    parser.add_argument(
        "--expect-prompt-version",
        help="require every packet to use this prompt version",
    )
    parser.add_argument(
        "--expect-model",
        help="require every packet to use this model identifier",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="accept a structurally valid bundle containing no packets",
    )
    parser.add_argument("--json", action="store_true", help="emit a JSON summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = inspect_presentation_bundle(
            args.bundle,
            expected_prompt_version=args.expect_prompt_version,
            expected_model=args.expect_model,
            require_packets=not args.allow_empty,
        )
    except (OSError, PresentationBundleError) as exc:
        if args.json:
            print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        else:
            print(f"invalid presentation bundle: {exc}", file=sys.stderr)
        return 1

    summary = result.to_dict()
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(f"valid presentation bundle: {result.path}")
        print(f"packets: {result.packet_count}")
        print(f"bytes: {result.byte_count}")
        print(f"prompt versions: {', '.join(result.prompt_versions)}")
        print(f"models: {', '.join(result.models)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
