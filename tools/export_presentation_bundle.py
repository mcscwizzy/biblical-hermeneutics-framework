#!/usr/bin/env python3
"""Export validated cached presentation packets for offline deployment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.presentation import (
    PresentationBundleExportError,
    export_cached_presentations,
    load_presentation_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export the disposable SQLite presentation cache as a versioned "
            "offline bundle without making model or network calls."
        )
    )
    parser.add_argument("--cache", required=True, help="presentation cache SQLite path")
    parser.add_argument("--output", required=True, help="destination bundle JSON path")
    parser.add_argument(
        "--force",
        action="store_true",
        help="atomically replace an existing destination",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = export_cached_presentations(
            args.cache,
            args.output,
            force=args.force,
        )
        loaded = load_presentation_bundle(result.output_path)
        if len(loaded) != result.packet_count:
            raise PresentationBundleExportError(
                "written bundle did not pass round-trip packet verification"
            )
    except (OSError, PresentationBundleExportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"exported {result.packet_count} packet(s) to {result.output_path} "
        f"({result.byte_count} bytes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
