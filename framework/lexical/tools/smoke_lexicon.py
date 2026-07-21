"""Smoke-test the standalone lexical runtime database."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ..service import (
    DEFAULT_LEXICAL_DATABASE_PATH,
    LexicalLookupService,
    lexical_database_missing_message,
)
from .validate_lexicon import validate_database


DEFAULT_CHECKS = (
    {"language": "greek", "strongs": "G3056", "label": "Greek logos / G3056"},
    {"language": "hebrew", "strongs": "H2617", "label": "Hebrew hesed / H2617"},
)


def smoke_lexical_database(
    database_path: str | Path = DEFAULT_LEXICAL_DATABASE_PATH,
    *,
    checks: tuple[Mapping[str, str], ...] = DEFAULT_CHECKS,
) -> dict[str, Any]:
    """Validate the DB and verify representative lookups fail clearly."""

    database = Path(database_path)
    if not database.is_file():
        raise FileNotFoundError(lexical_database_missing_message(database))

    validation = validate_database(database)
    service = LexicalLookupService(database)
    results: list[dict[str, Any]] = []
    try:
        for check in checks:
            entries = service.lookup(
                language=str(check["language"]),
                strongs=str(check["strongs"]),
            )
            results.append(
                {
                    "label": check["label"],
                    "language": check["language"],
                    "strongs": check["strongs"],
                    "status": "pass" if entries else "fail",
                    "matched": entries[0].lemma if entries else None,
                }
            )
    finally:
        service.close()

    passed = sum(1 for result in results if result["status"] == "pass")
    return {
        "database_path": str(database),
        "entries": validation["entries"],
        "sources": validation["sources"],
        "check_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


def format_smoke_report(report: Mapping[str, Any]) -> str:
    lines = [
        "Lexical database smoke report",
        f"Database: {report.get('database_path')}",
        f"Entries: {report.get('entries')}",
        f"Sources: {report.get('sources')}",
        f"Passed: {report.get('passed')}/{report.get('check_count')}",
    ]
    for result in report.get("results") or []:
        marker = "PASS" if result.get("status") == "pass" else "FAIL"
        lines.append(f"- {marker}: {result.get('label')}")
        if result.get("matched"):
            lines.append(f"  Matched lemma: {result.get('matched')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(DEFAULT_LEXICAL_DATABASE_PATH),
        help="Runtime lexical SQLite database to smoke-test",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    try:
        report = smoke_lexical_database(args.database)
    except (FileNotFoundError, ValueError, OSError, sqlite3.Error) as exc:
        print(f"error: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(format_smoke_report(report))
    return 1 if int(report.get("failed") or 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
