"""Build the CKL SQLite index as a Vercel Python function artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .database_builder import build_database, verify_database


def package_source_root() -> Path:
    """Return the checked-out CKL JSON inventory bundled with the application."""

    return Path(__file__).resolve().parent


def package_database_path() -> Path:
    """Return the generated index path included in the Vercel function bundle."""

    return package_source_root() / "data" / "ckl.sqlite"


def build_vercel_ckl_index(
    *,
    source_root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, object]:
    """Build from committed JSON and return a fresh structural/source report."""

    source = Path(source_root).resolve() if source_root is not None else package_source_root()
    output = Path(output_path).resolve() if output_path is not None else package_database_path()
    if not (source / "manifest.json").is_file() or not (source / "objects").is_dir():
        raise FileNotFoundError(f"CKL source inventory is incomplete at {source}")
    if output.name == "ckl.sqlite" and ".bhf" in output.parts:
        raise ValueError("the Vercel CKL build cannot use a local .bhf database path")

    build_database(source, output)
    report = verify_database(output, root=source, compare_fingerprint=True)
    report["path"] = str(output)
    report["source_root"] = str(source)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and verify the packaged Vercel CKL SQLite index")
    parser.add_argument("--source-root", type=Path, default=None, help="CKL JSON source root (defaults to package sources)")
    parser.add_argument("--output", type=Path, default=None, help="SQLite output path (defaults to package data/ckl.sqlite)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    report = build_vercel_ckl_index(source_root=arguments.source_root, output_path=arguments.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
