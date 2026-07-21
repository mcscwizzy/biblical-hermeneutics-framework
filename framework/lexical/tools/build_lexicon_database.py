"""Build the standalone SQLite lexical database from local XML sources."""

from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..importers.openscriptures_greek import import_greek
from ..importers.openscriptures_hebrew import import_hebrew
from ..models import ImportStats


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE lexical_sources (
    source TEXT PRIMARY KEY,
    license TEXT NOT NULL,
    attribution TEXT NOT NULL,
    source_url TEXT NOT NULL DEFAULT '',
    revision TEXT NOT NULL DEFAULT 'unspecified',
    imported_at TEXT NOT NULL,
    source_file TEXT NOT NULL
);

CREATE TABLE lexical_entries (
    id INTEGER PRIMARY KEY,
    language TEXT NOT NULL CHECK (language IN ('hebrew', 'greek', 'aramaic')),
    strongs_number TEXT,
    lemma TEXT NOT NULL,
    transliteration TEXT,
    pronunciation TEXT,
    definition TEXT NOT NULL,
    short_definition TEXT,
    root TEXT,
    part_of_speech TEXT,
    morphology TEXT,
    semantic_domain TEXT,
    usage_notes TEXT,
    source TEXT NOT NULL,
    license TEXT NOT NULL,
    created_at TEXT NOT NULL,
    normalized_lemma TEXT NOT NULL,
    normalized_transliteration TEXT,
    FOREIGN KEY (source) REFERENCES lexical_sources(source)
);

CREATE INDEX idx_lexical_entries_language_strongs
    ON lexical_entries(language, strongs_number);
CREATE INDEX idx_lexical_entries_language_lemma
    ON lexical_entries(language, normalized_lemma);
CREATE INDEX idx_lexical_entries_language_transliteration
    ON lexical_entries(language, normalized_transliteration);
"""

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "database" / "lexicon.sqlite"


def build_lexicon_database(
    *,
    hebrew: str | Path | None = None,
    greek: str | Path | None = None,
    output: str | Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    """Create a fresh database atomically from one or both source files."""

    if hebrew is None and greek is None:
        raise ValueError("at least one of --hebrew or --greek is required")
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    stats: list[ImportStats] = []
    for importer, path in ((import_hebrew, hebrew), (import_greek, greek)):
        if path is None:
            continue
        imported, import_stats = importer(path)
        records.extend(imported)
        stats.append(import_stats)
    _validate_records(records)

    fd, temporary_name = tempfile.mkstemp(
        prefix=f"{output_path.name}.", suffix=".tmp", dir=str(output_path.parent)
    )
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        _write_database(temporary_path, records)
        from .validate_lexicon import validate_database

        validate_database(temporary_path)
        os.replace(temporary_path, output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return {
        "path": output_path,
        "hebrew": next((item.entries_imported for item in stats if item.language == "hebrew"), 0),
        "greek": next((item.entries_imported for item in stats if item.language == "greek"), 0),
        "total": len(records),
        "sources": sorted({str(record["source"]) for record in records}),
    }


# Stable descriptive alias for callers that use the shorter tool name.
build_database = build_lexicon_database


def _write_database(path: Path, records: list[dict[str, Any]]) -> None:
    imported_at = datetime.now(timezone.utc).isoformat()
    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA_SQL)
        sources: dict[str, dict[str, Any]] = {}
        for record in records:
            sources[str(record["source"])] = record
        for source, record in sources.items():
            connection.execute(
                """
                INSERT INTO lexical_sources
                    (source, license, attribution, source_url, revision, imported_at, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    record["license"],
                    record["attribution"],
                    record.get("source_url") or "",
                    record.get("revision") or "unspecified",
                    imported_at,
                    record.get("source_file") or "",
                ),
            )
        for record in records:
            connection.execute(
                """
                INSERT INTO lexical_entries
                    (language, strongs_number, lemma, transliteration, pronunciation,
                     definition, short_definition, root, part_of_speech, morphology,
                     semantic_domain, usage_notes, source, license, created_at,
                     normalized_lemma, normalized_transliteration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["language"], record.get("strongs_number"), record["lemma"],
                    record.get("transliteration"), record.get("pronunciation"),
                    record["definition"], record.get("short_definition"), record.get("root"),
                    record.get("part_of_speech"), record.get("morphology"),
                    record.get("semantic_domain"), record.get("usage_notes"), record["source"],
                    record["license"], record["created_at"],
                    _normalize_form(str(record["lemma"])),
                    _normalize_transliteration(record.get("transliteration")),
                ),
            )
        connection.execute("PRAGMA user_version = 1")
        connection.commit()
    finally:
        connection.close()


def _validate_records(records: Iterable[Mapping[str, Any]]) -> None:
    valid_languages = {"hebrew", "greek", "aramaic"}
    for index, record in enumerate(records, start=1):
        for field in ("language", "lemma", "definition", "source", "license", "created_at"):
            if not str(record.get(field) or "").strip():
                raise ValueError(f"lexical entry {index} is missing required field: {field}")
        if str(record["language"]).lower() not in valid_languages:
            raise ValueError(f"lexical entry {index} has unsupported language: {record['language']}")


def _normalize_form(value: str) -> str:
    import unicodedata

    text = unicodedata.normalize("NFD", value.strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return text.replace("ς", "σ").strip()


def _normalize_transliteration(value: object) -> str | None:
    if not value:
        return None
    import unicodedata

    text = unicodedata.normalize("NFD", str(value).strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.translate(str.maketrans({"ḥ": "h", "ḫ": "h", "š": "s", "ś": "s", "ṭ": "t", "ṣ": "s", "ẓ": "z"}))
    text = "".join(char for char in text if char.isalnum() or char.isspace())
    return " ".join(text.split()) or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            f"""
            Developer onboarding:
              1. Download or clone inspected Open Scriptures source repositories outside git-tracked paths:
                   mkdir -p sources/openscriptures
                   git clone https://github.com/openscriptures/HebrewLexicon sources/openscriptures/HebrewLexicon
                   git clone https://github.com/openscriptures/strongs sources/openscriptures/strongs
              2. Locate the XML dictionary exports:
                   find sources/openscriptures -name '*.xml'
              3. Import into the runtime location:
                   python -m framework.lexical.tools.build_lexicon_database \\
                     --hebrew <path-to-open-scriptures-hebrew-xml> \\
                     --greek <path-to-open-scriptures-greek-xml> \\
                     --output {DEFAULT_OUTPUT}
              4. Verify:
                   python -m framework.lexical.tools.smoke_lexicon --database {DEFAULT_OUTPUT}
            """
        ).strip(),
    )
    parser.add_argument("--hebrew", type=Path, help="local Open Scriptures Hebrew XML")
    parser.add_argument("--greek", type=Path, help="local Open Scriptures Greek XML")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = build_lexicon_database(hebrew=args.hebrew, greek=args.greek, output=args.output)
    print("Lexical import complete.")
    print(f"Hebrew: {result['hebrew']} entries imported")
    print(f"Greek: {result['greek']} entries imported")
    print(f"Database: {result['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
