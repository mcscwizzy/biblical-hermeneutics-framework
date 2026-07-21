"""Validation helpers for lexical data onboarding."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .database_schema import DEFAULT_CKL_DATABASE_PATH
from .lexicon_normalization import normalize_script_form, normalize_strongs_number
from .lexicon_repository import LexiconRepository
from .lexicon_source_importer import normalized_payload_from_source_manifest


DEFAULT_COVERAGE_CHECKS = (
    {
        "reference": "John 1:1",
        "book": "John",
        "chapter": 1,
        "verse": 1,
        "strongs_number": "G3056",
        "lemma": "λόγος",
        "language": "greek",
    },
    {
        "reference": "Psalm 23:6",
        "book": "Psalms",
        "chapter": 23,
        "verse": 6,
        "strongs_number": "H2617",
        "lemma": "חֶסֶד",
        "language": "hebrew",
    },
)


def validate_source_manifest(manifest_path: str | Path) -> dict[str, Any]:
    """Parse a local source manifest and return a deterministic summary."""

    payload, content_hash = normalized_payload_from_source_manifest(manifest_path)
    return {
        "manifest_path": str(Path(manifest_path)),
        "content_hash": content_hash,
        "source_count": len(payload.get("sources") or []),
        "entry_count": len(payload.get("entries") or []),
        "word_form_count": len(payload.get("word_forms") or []),
        "verse_word_count": len(payload.get("verse_words") or []),
        "relation_count": len(payload.get("relations") or []),
        "sources": [str(source.get("name") or "") for source in payload.get("sources") or []],
    }


def load_coverage_checks(path: str | Path | None = None) -> list[dict[str, Any]]:
    if path is None:
        return [dict(check) for check in DEFAULT_COVERAGE_CHECKS]
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("lexicon coverage checks must be a JSON list")
    checks = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("each lexicon coverage check must be an object")
        checks.append(dict(item))
    return checks


def validate_database_coverage(
    database_path: str | Path = DEFAULT_CKL_DATABASE_PATH,
    *,
    checks: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Check whether a lexical SQLite database contains expected tokens."""

    selected_checks = list(checks or DEFAULT_COVERAGE_CHECKS)
    repository = LexiconRepository(database_path)
    results: list[dict[str, Any]] = []
    try:
        for check in selected_checks:
            results.append(_coverage_result(repository, check))
    finally:
        repository.close()
    passed = sum(1 for result in results if result["status"] == "pass")
    return {
        "database_path": str(Path(database_path)),
        "check_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


def build_onboarding_report(
    *,
    manifest_path: str | Path | None = None,
    database_path: str | Path = DEFAULT_CKL_DATABASE_PATH,
    coverage_path: str | Path | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {}
    if manifest_path is not None:
        report["manifest"] = validate_source_manifest(manifest_path)
    if Path(database_path).exists():
        report["coverage"] = validate_database_coverage(
            database_path,
            checks=load_coverage_checks(coverage_path),
        )
    else:
        report["coverage"] = {
            "database_path": str(Path(database_path)),
            "check_count": 0,
            "passed": 0,
            "failed": 0,
            "results": [],
            "warning": "database not found",
        }
    return report


def report_has_failures(report: Mapping[str, Any]) -> bool:
    coverage = report.get("coverage")
    if isinstance(coverage, Mapping) and int(coverage.get("failed") or 0) > 0:
        return True
    if isinstance(coverage, Mapping) and coverage.get("warning"):
        return True
    return False


def format_onboarding_report(report: Mapping[str, Any]) -> str:
    lines = ["Lexicon onboarding report"]
    manifest = report.get("manifest")
    if isinstance(manifest, Mapping):
        lines.extend(
            [
                "",
                f"Manifest: {manifest.get('manifest_path')}",
                f"Sources: {manifest.get('source_count')}",
                f"Entries: {manifest.get('entry_count')}",
                f"Word forms: {manifest.get('word_form_count')}",
                f"Verse words: {manifest.get('verse_word_count')}",
                f"Content hash: {manifest.get('content_hash')}",
            ]
        )
    coverage = report.get("coverage")
    if isinstance(coverage, Mapping):
        lines.extend(
            [
                "",
                f"Database: {coverage.get('database_path')}",
                f"Coverage: {coverage.get('passed')}/{coverage.get('check_count')} checks passed",
            ]
        )
        if coverage.get("warning"):
            lines.append(f"Warning: {coverage.get('warning')}")
        for result in coverage.get("results") or []:
            marker = "PASS" if result.get("status") == "pass" else "FAIL"
            lines.append(f"- {marker}: {result.get('reference')} {result.get('expected')}")
            if result.get("matched"):
                lines.append(f"  Matched: {result.get('matched')}")
            if result.get("message"):
                lines.append(f"  {result.get('message')}")
    return "\n".join(lines)


def _coverage_result(repository: LexiconRepository, check: Mapping[str, Any]) -> dict[str, Any]:
    book = _required_text(check, "book")
    chapter = int(check.get("chapter"))
    verse = int(check.get("verse"))
    language = str(check.get("language") or "").strip().lower()
    strongs = normalize_strongs_number(check.get("strongs_number"))
    lemma = str(check.get("lemma") or "").strip()
    expected = ", ".join(value for value in (strongs, lemma) if value)
    words = repository.get_verse_words(book, chapter, verse)
    for word in words:
        if language and word.language != language:
            continue
        if strongs and normalize_strongs_number(word.strongs_number) != strongs:
            continue
        if lemma and normalize_script_form(word.lemma, language=word.language) != normalize_script_form(
            lemma,
            language=word.language,
        ):
            continue
        return {
            "status": "pass",
            "reference": str(check.get("reference") or f"{book} {chapter}:{verse}"),
            "expected": expected,
            "matched": f"{word.surface_form} / {word.lemma} / {word.strongs_number}",
        }
    return {
        "status": "fail",
        "reference": str(check.get("reference") or f"{book} {chapter}:{verse}"),
        "expected": expected,
        "matched": None,
        "message": f"Found {len(words)} lexical token(s) for the verse, but none matched the expectation.",
    }


def _required_text(data: Mapping[str, Any], key: str) -> str:
    value = str(data.get(key) or "").strip()
    if not value:
        raise ValueError(f"coverage check missing required field: {key}")
    return value
