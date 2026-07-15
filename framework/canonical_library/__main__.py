"""CLI entry point for inspecting the packaged CKL release."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import CanonicalLibrary, CanonicalValidationError
from .public_cache import (
    load_framework_version,
    load_framework_version_fingerprint,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect the installed Canonical Knowledge Library release."
    )
    parser.add_argument(
        "--root",
        help="Inspect a CKL checkout at this path instead of the packaged inventory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable release metadata",
    )
    return parser


def _load_library(root: str | None) -> CanonicalLibrary:
    if root:
        return CanonicalLibrary(root=Path(root)).load()
    return CanonicalLibrary.load_default()


def _build_report(library: CanonicalLibrary) -> dict[str, object]:
    manifest = dict(library.manifest)
    return {
        "distribution_name": "biblical-hermeneutics-framework",
        "framework_version": load_framework_version(),
        "framework_version_fingerprint": load_framework_version_fingerprint(),
        "ckl_root": str(library.root),
        "ckl_manifest_framework_version": manifest.get("framework_version"),
        "ckl_manifest_schema_version": manifest.get("schema_version"),
        "ckl_object_count": manifest.get("object_count"),
        "ckl_categories": manifest.get("categories"),
        "ckl_inventory_fingerprint": library.inventory_fingerprint(),
    }


def _print_human_report(report: dict[str, object]) -> None:
    print(f"BHF release version: {report['framework_version']}")
    print(f"BHF release fingerprint: {report['framework_version_fingerprint']}")
    print(f"CKL root: {report['ckl_root']}")
    print(
        "CKL manifest version: "
        f"{report['ckl_manifest_framework_version']} / "
        f"{report['ckl_manifest_schema_version']}"
    )
    print(f"CKL object count: {report['ckl_object_count']}")
    print(f"CKL inventory fingerprint: {report['ckl_inventory_fingerprint']}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        library = _load_library(args.root)
        report = _build_report(library)
    except (CanonicalValidationError, FileNotFoundError, ValueError, OSError) as exc:
        print(f"error: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        _print_human_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
