#!/usr/bin/env python3
"""Write deterministic Commentary richness JSON, report, and CKL backlog."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent.chapter_commentary.richness import audit_corpus, render_human_report
from bhf_agent.runtime_paths import RUNTIME_DATA_PATHS


DEFAULT_OUTPUT_ROOT = Path(
    ".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/audit"
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage-dir", default=str(RUNTIME_DATA_PATHS.bhf_commentary_storage_path)
    )
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    args = parser.parse_args(argv)
    output = Path(args.output_root)
    audit = audit_corpus(args.storage_dir)
    _write(output / "commentary-richness-audit.json", json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    _write(output / "commentary-richness-audit.md", render_human_report(audit))
    _write(
        output / "targeted-ckl-expansion-backlog.json",
        json.dumps(
            {
                "artifact_version": "commentary-v1.2-ckl-backlog-v1",
                "count": len(audit["evidence_gap_backlog"]),
                "chapters": audit["evidence_gap_backlog"],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
    )
    print(render_human_report(audit), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
