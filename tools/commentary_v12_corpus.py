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

from bhf_agent.config import AgentConfig
from framework.commentary.v12_corpus import (
    DEFAULT_BATCH_SIZE,
    ExistingV12ChapterPipeline,
    V12CorpusRunner,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("dry-run", "generate"):
        command = sub.add_parser(name)
        command.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
        if name == "generate":
            command.add_argument("--config", type=Path, required=True, help="approved model configuration JSON")
    args = parser.parse_args(argv)
    try:
        if args.command == "dry-run":
            result = V12CorpusRunner(ROOT).dry_run(args.batch_size)
        else:
            config = AgentConfig.from_json_file(args.config)
            pipeline = ExistingV12ChapterPipeline(config)
            result = V12CorpusRunner(ROOT, pipeline=pipeline).run(args.batch_size)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
