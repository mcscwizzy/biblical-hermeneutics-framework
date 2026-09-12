#!/usr/bin/env python3
"""Discover or run one bounded Commentary v1.2 corpus batch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.commentary.v12_corpus import (
    DEFAULT_BATCH_SIZE,
    V12CorpusRunner,
)
from framework.commentary.v12_config import load_v12_prose_configuration


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("dry-run", "prepare", "finalize", "generate"):
        command = sub.add_parser(name)
        if name in {"dry-run", "prepare", "generate"}:
            command.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
        if name in {"dry-run", "generate"}:
            command.add_argument("--config", type=Path, help="approved model configuration JSON")
    args = parser.parse_args(argv)
    try:
        if args.command == "dry-run":
            result = V12CorpusRunner(ROOT).dry_run(args.batch_size)
            configuration = load_v12_prose_configuration(ROOT, args.config)
            result["prose_renderer"] = {
                **configuration.metadata(), "renderer_mode": "codex_session",
            }
        elif args.command == "prepare":
            result = V12CorpusRunner(
                ROOT,
                generation_metadata={
                    "pipeline": "commentary-v1.2-enrichment",
                    "renderer_mode": "codex_session",
                    "requested_model": "gpt-5.6-terra",
                    "requested_effort": "high",
                },
            ).prepare(args.batch_size)
        elif args.command == "finalize":
            result = V12CorpusRunner(ROOT).finalize()
        else:
            configuration = load_v12_prose_configuration(ROOT, args.config)
            # Retain the legacy CLI transport behind the explicit generate
            # command; the session-render workflow is prepare/finalize.
            from framework.commentary.v12_corpus import CodexCliV12ChapterPipeline
            pipeline = CodexCliV12ChapterPipeline(
                model=configuration.config.model or "gpt-5.6-terra",
                effort=configuration.config.reasoning_effort or "high",
            )
            result = V12CorpusRunner(
                ROOT,
                pipeline=pipeline,
                generation_metadata=configuration.metadata(),
            ).run(args.batch_size)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
