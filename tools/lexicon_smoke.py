#!/usr/bin/env python3
"""Run deterministic Word Study smoke checks against a CKL SQLite database."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.lexicon import LexiconRepository, WordStudyService
from bhf_agent.study_actions import DeterministicStudyEngine, StudyActionRouter
from framework.canonical_library import CanonicalLibrary
from framework.canonical_library.database_schema import DEFAULT_CKL_DATABASE_PATH
from framework.canonical_library.lexicon_onboarding import load_coverage_checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Smoke-test the real deterministic Word Study action path."
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_CKL_DATABASE_PATH,
        help="CKL SQLite database with lexical tables",
    )
    parser.add_argument(
        "--ckl-root",
        default="framework/canonical_library",
        help="CKL JSON root used for non-lexical deterministic context",
    )
    parser.add_argument(
        "--coverage-json",
        help="Optional JSON list of coverage checks; defaults to John 1:1 and Psalm 23:6",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    return parser


def run_smoke(
    *,
    database_path: str | Path,
    ckl_root: str | Path,
    coverage_path: str | Path | None = None,
) -> dict[str, Any]:
    checks = load_coverage_checks(coverage_path)
    library = CanonicalLibrary(root=Path(ckl_root)).load()
    repository = LexiconRepository(database_path)
    service = WordStudyService(repository=repository)
    router = StudyActionRouter(DeterministicStudyEngine(library, word_study_service=service))
    results = []
    try:
        for check in checks:
            results.append(_run_check(router, check))
    finally:
        repository.close()
    passed = sum(1 for result in results if result["status"] == "pass")
    return {
        "database_path": str(Path(database_path)),
        "ckl_root": str(Path(ckl_root)),
        "check_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


def format_smoke_report(report: Mapping[str, Any]) -> str:
    lines = [
        "Word Study smoke report",
        f"Database: {report.get('database_path')}",
        f"CKL root: {report.get('ckl_root')}",
        f"Passed: {report.get('passed')}/{report.get('check_count')}",
    ]
    for result in report.get("results") or []:
        marker = "PASS" if result.get("status") == "pass" else "FAIL"
        lines.append(f"- {marker}: {result.get('reference')} {result.get('expected')}")
        if result.get("matched"):
            lines.append(f"  Matched: {result.get('matched')}")
        if result.get("message"):
            lines.append(f"  {result.get('message')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = run_smoke(
            database_path=args.database,
            ckl_root=args.ckl_root,
            coverage_path=args.coverage_json,
        )
    except (FileNotFoundError, ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
        print(f"error: {exc}")
        return 1
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(format_smoke_report(report))
    return 1 if int(report.get("failed") or 0) else 0


def _run_check(router: StudyActionRouter, check: Mapping[str, Any]) -> dict[str, Any]:
    result = router.execute(
        "word_study",
        passage={
            "book": check.get("book"),
            "chapter": check.get("chapter"),
            "start_verse": check.get("verse"),
            "end_verse": check.get("verse"),
            "strongs_number": check.get("strongs_number"),
            "lemma": check.get("lemma"),
            "language": check.get("language"),
        },
    )
    word_study = result.metadata.get("word_study") or {}
    expected = ", ".join(
        str(value)
        for value in (check.get("strongs_number"), check.get("lemma"))
        if value
    )
    matched = ", ".join(
        str(value)
        for value in (
            word_study.get("surface_form"),
            word_study.get("lemma"),
            word_study.get("strongs_number"),
        )
        if value
    )
    passed = (
        result.status == "complete"
        and _same_text(word_study.get("strongs_number"), check.get("strongs_number"))
        and (not check.get("lemma") or _same_text(word_study.get("lemma"), check.get("lemma")))
    )
    return {
        "status": "pass" if passed else "fail",
        "reference": check.get("reference") or f"{check.get('book')} {check.get('chapter')}:{check.get('verse')}",
        "expected": expected,
        "matched": matched or None,
        "message": None if passed else f"Study action returned {result.status}.",
    }


def _same_text(left: Any, right: Any) -> bool:
    return str(left or "").strip().casefold() == str(right or "").strip().casefold()


if __name__ == "__main__":
    raise SystemExit(main())
