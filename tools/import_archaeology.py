#!/usr/bin/env python3
"""Import a curated archaeology media manifest through an explicit provider."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bhf_agent.archaeology_import import FixtureArchaeologyMediaProvider, import_archaeology_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("fixture",), required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=REPO_ROOT / ".bhf" / "study.sqlite")
    args = parser.parse_args()

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = payload.get("records", {}) if isinstance(payload, dict) else {}
    provider = FixtureArchaeologyMediaProvider(records)
    imported = import_archaeology_manifest(
        args.manifest,
        provider=provider,
        database_path=args.database,
    )
    print(json.dumps({"provider": args.provider, "imported": imported}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
