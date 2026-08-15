"""CLI entry point for inspecting the packaged CKL release."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import CanonicalLibrary, CanonicalValidationError
from .database_builder import build_database, database_info, verify_database
from .database_migrations import migrate_database
from .database_schema import DEFAULT_CKL_DATABASE_PATH
from .public_cache import (
    load_framework_version,
    load_framework_version_fingerprint,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect the installed Canonical Knowledge Library release."
    )
    subparsers = parser.add_subparsers(dest="command")

    build_db = subparsers.add_parser("build-db", help="Build the generated CKL SQLite runtime database")
    build_db.add_argument("--root", help="CKL root containing manifest.json and objects/")
    build_db.add_argument("--output", default=DEFAULT_CKL_DATABASE_PATH, help="SQLite output path")

    verify_db = subparsers.add_parser("verify-db", help="Verify a generated CKL SQLite database")
    verify_db.add_argument("--root", help="CKL root to compare fingerprints against")
    verify_db.add_argument("--database", default=DEFAULT_CKL_DATABASE_PATH, help="SQLite database path")
    verify_db.add_argument(
        "--skip-fingerprint",
        action="store_true",
        help="Verify structure and integrity without comparing to source JSON",
    )

    info_db = subparsers.add_parser("db-info", help="Display CKL SQLite database metadata")
    info_db.add_argument("--database", default=DEFAULT_CKL_DATABASE_PATH, help="SQLite database path")
    info_db.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable database metadata",
    )

    migrate_db = subparsers.add_parser("migrate-db", help="Migrate an existing CKL SQLite database")
    migrate_db.add_argument("--database", default=DEFAULT_CKL_DATABASE_PATH, help="SQLite database path")
    migrate_db.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create the default versioned backup before migration",
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
        if args.command == "build-db":
            result = build_database(args.root, args.output)
            print(f"Built CKL SQLite database: {result.path}")
            print(f"Object count: {result.object_count}")
            print(f"Inventory fingerprint: {result.inventory_fingerprint}")
            return 0
        if args.command == "verify-db":
            report = verify_database(
                args.database,
                root=args.root,
                compare_fingerprint=not args.skip_fingerprint,
            )
            print("CKL SQLite database verified")
            _print_db_report(report)
            return 0
        if args.command == "db-info":
            report = database_info(args.database)
            if args.json:
                print(json.dumps(report, indent=2, ensure_ascii=True))
            else:
                _print_db_report(report)
            return 0
        if args.command == "migrate-db":
            report = migrate_database(args.database, backup=not args.no_backup)
            print(json.dumps(report, indent=2, ensure_ascii=True))
            return 0

        library = _load_library(args.root)
        report = _build_report(library)
    except (CanonicalValidationError, FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        print(f"error: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        _print_human_report(report)
    return 0


def _print_db_report(report: dict[str, object]) -> None:
    print(f"Database path: {report.get('database_path') or report.get('path')}")
    print(f"Database schema version: {report.get('database_schema_version')}")
    print(f"Retrieval index version: {report.get('retrieval_index_version')}")
    print(f"Framework version: {report.get('framework_version')}")
    print(f"CKL schema version: {report.get('schema_version')}")
    print(f"CKL object count: {report.get('object_count')}")
    print(f"Claim count: {report.get('claim_count')}")
    print(f"Source count: {report.get('source_count')}")
    print(f"Evidence count: {report.get('evidence_count')}")
    print(f"Build timestamp: {report.get('build_timestamp')}")
    print(f"Inventory fingerprint: {report.get('inventory_fingerprint')}")
    print(f"Database file size: {report.get('database_file_size') or report.get('file_size')} bytes")


if __name__ == "__main__":
    raise SystemExit(main())
