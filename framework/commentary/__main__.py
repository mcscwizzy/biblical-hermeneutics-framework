"""Command-line tools for local commentary databases."""

from __future__ import annotations

import argparse
import json

from .database_schema import DEFAULT_COMMENTARY_DATABASE_PATH
from .importer import import_tyndale_archive


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and inspect BHF commentary resources.")
    commands = parser.add_subparsers(dest="command", required=True)
    importer = commands.add_parser("import-tyndale", help="Import a local official Tyndale Open Study Notes archive")
    importer.add_argument("--source", required=True, help="Path to the locally downloaded official archive")
    importer.add_argument("--output", default=str(DEFAULT_COMMENTARY_DATABASE_PATH), help="SQLite output path")
    importer.add_argument("--source-url", default=None, help="Official source URL to retain as provenance")
    importer.add_argument(
        "--fail-on-unmapped",
        action="store_true",
        help="Abort without replacing the output when Scripture references cannot be mapped",
    )
    importer.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect and validate the archive without creating or replacing the output database",
    )
    importer.add_argument(
        "--strict",
        action="store_true",
        help="Reject unmapped references, unsupported records, parser warnings, and empty archives",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "import-tyndale":
        print(json.dumps(
            import_tyndale_archive(
                args.source,
                args.output,
                source_url=args.source_url,
                fail_on_unmapped=args.fail_on_unmapped,
                dry_run=args.dry_run,
                strict=args.strict,
            ),
            indent=2,
            sort_keys=True,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
