#!/usr/bin/env python3
"""Explicitly freeze or verify the current Commentary v1.2 source lineage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.commentary.v12_current_lineage import CurrentLineageError, prepare, verify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify"))
    args = parser.parse_args(argv)
    try:
        result = prepare(ROOT) if args.command == "prepare" else verify(ROOT)
    except CurrentLineageError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
