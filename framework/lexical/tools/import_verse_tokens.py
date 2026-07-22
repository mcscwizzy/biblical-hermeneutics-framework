"""Import original-language verse tokens into the standalone lexical database."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from framework.canonical_library.lexicon_morphology import decode_morphology

from ..service import DEFAULT_LEXICAL_DATABASE_PATH


TOKEN_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS word_forms (
    id INTEGER PRIMARY KEY,
    language TEXT NOT NULL CHECK (language IN ('hebrew', 'greek', 'aramaic')),
    surface_form TEXT NOT NULL,
    normalized_form TEXT NOT NULL,
    lemma TEXT NOT NULL,
    normalized_lemma TEXT NOT NULL,
    transliteration TEXT,
    normalized_transliteration TEXT,
    strongs_number TEXT,
    morphology_code TEXT,
    morphology_json TEXT NOT NULL DEFAULT '{}',
    lexicon_entry_id INTEGER,
    source TEXT,
    source_word_id TEXT,
    FOREIGN KEY (lexicon_entry_id) REFERENCES lexical_entries(id) ON DELETE SET NULL,
    UNIQUE (source, source_word_id)
);

CREATE TABLE IF NOT EXISTS verse_words (
    id INTEGER PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    word_position INTEGER NOT NULL,
    source_word_id TEXT,
    language TEXT NOT NULL CHECK (language IN ('hebrew', 'greek', 'aramaic')),
    surface_form TEXT NOT NULL,
    normalized_form TEXT NOT NULL,
    lemma TEXT NOT NULL,
    normalized_lemma TEXT NOT NULL,
    transliteration TEXT,
    normalized_transliteration TEXT,
    strongs_number TEXT,
    morphology_code TEXT,
    morphology_json TEXT NOT NULL DEFAULT '{}',
    lexicon_entry_id INTEGER,
    source TEXT,
    FOREIGN KEY (lexicon_entry_id) REFERENCES lexical_entries(id) ON DELETE SET NULL,
    UNIQUE (book, chapter, verse, word_position, language)
);

CREATE INDEX IF NOT EXISTS idx_word_forms_language_lemma
    ON word_forms(language, normalized_lemma);
CREATE INDEX IF NOT EXISTS idx_word_forms_strongs
    ON word_forms(strongs_number);
CREATE INDEX IF NOT EXISTS idx_word_forms_source_word
    ON word_forms(source_word_id);
CREATE INDEX IF NOT EXISTS idx_verse_words_reference
    ON verse_words(book, chapter, verse);
CREATE INDEX IF NOT EXISTS idx_verse_words_reference_position
    ON verse_words(book, chapter, verse, word_position);
CREATE INDEX IF NOT EXISTS idx_verse_words_strongs
    ON verse_words(strongs_number);
CREATE INDEX IF NOT EXISTS idx_verse_words_language_lemma
    ON verse_words(language, normalized_lemma);
CREATE INDEX IF NOT EXISTS idx_verse_words_source_word
    ON verse_words(source_word_id);
"""

OSIS_BOOKS = {
    "Gen": "Genesis",
    "Exod": "Exodus",
    "Lev": "Leviticus",
    "Num": "Numbers",
    "Deut": "Deuteronomy",
    "Josh": "Joshua",
    "Judg": "Judges",
    "Ruth": "Ruth",
    "1Sam": "1 Samuel",
    "2Sam": "2 Samuel",
    "1Kgs": "1 Kings",
    "2Kgs": "2 Kings",
    "1Chr": "1 Chronicles",
    "2Chr": "2 Chronicles",
    "Ezra": "Ezra",
    "Neh": "Nehemiah",
    "Esth": "Esther",
    "Job": "Job",
    "Ps": "Psalms",
    "Prov": "Proverbs",
    "Eccl": "Ecclesiastes",
    "Song": "Song of Songs",
    "Isa": "Isaiah",
    "Jer": "Jeremiah",
    "Lam": "Lamentations",
    "Ezek": "Ezekiel",
    "Dan": "Daniel",
    "Hos": "Hosea",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obad": "Obadiah",
    "Jonah": "Jonah",
    "Mic": "Micah",
    "Nah": "Nahum",
    "Hab": "Habakkuk",
    "Zeph": "Zephaniah",
    "Hag": "Haggai",
    "Zech": "Zechariah",
    "Mal": "Malachi",
}


def import_verse_tokens(
    database_path: str | Path,
    *,
    source: Mapping[str, str],
    verse_words: Iterable[Mapping[str, Any]] = (),
    word_forms: Iterable[Mapping[str, Any]] = (),
    rebuild_tokens: bool = False,
) -> dict[str, int]:
    database = Path(database_path)
    if not database.is_file():
        raise FileNotFoundError(f"lexical SQLite database not found: {database}")
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    counts = {"verse_words": 0, "word_forms": 0}
    try:
        with connection:
            ensure_token_schema(connection)
            _upsert_source(connection, source)
            if rebuild_tokens:
                connection.execute("DELETE FROM verse_words")
                connection.execute("DELETE FROM word_forms")
            for form in word_forms:
                _insert_word_form(connection, form, source_name=source["name"])
                counts["word_forms"] += 1
            for word in verse_words:
                _insert_verse_word(connection, word, source_name=source["name"])
                counts["verse_words"] += 1
            connection.execute("PRAGMA user_version = 2")
    finally:
        connection.close()
    return counts


def ensure_token_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(TOKEN_SCHEMA_SQL)


def read_tsv(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, dialect=csv.excel_tab)
        if reader.fieldnames is None:
            raise ValueError(f"TSV token source must include a header row: {path}")
        for index, row in enumerate(reader, start=2):
            clean = {str(key or "").strip(): str(value or "").strip() for key, value in row.items()}
            try:
                rows.append(_record_from_row(clean))
            except ValueError as exc:
                raise ValueError(f"{path}:{index}: {exc}") from exc
    return rows


def read_oshb_osis(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    root = ET.parse(file_path).getroot()
    rows: list[dict[str, Any]] = []
    position_by_reference: dict[tuple[str, int, int], int] = {}
    for verse in root.iter(_osis_tag("verse")):
        osis_id = str(verse.attrib.get("osisID") or "")
        match = re.fullmatch(r"([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)", osis_id)
        if not match:
            continue
        osis_book, chapter_text, verse_text = match.groups()
        book = OSIS_BOOKS.get(osis_book, osis_book)
        chapter = int(chapter_text)
        verse_number = int(verse_text)
        key = (book, chapter, verse_number)
        for word in verse.iter(_osis_tag("w")):
            surface = "".join(word.itertext()).strip()
            if not surface:
                continue
            position_by_reference[key] = position_by_reference.get(key, 0) + 1
            strongs = _strongs_from_oshb_lemma(word.attrib.get("lemma"))
            rows.append(
                {
                    "book": book,
                    "chapter": chapter,
                    "verse": verse_number,
                    "word_position": position_by_reference[key],
                    "language": "hebrew",
                    "surface_form": surface,
                    "lemma": _optional_text(word.attrib.get("lemma")),
                    "strongs_number": strongs,
                    "morphology_code": _optional_text(word.attrib.get("morph")),
                    "source_word_id": _optional_text(word.attrib.get("id")),
                }
            )
    return rows


def _insert_word_form(
    connection: sqlite3.Connection,
    row: Mapping[str, Any],
    *,
    source_name: str,
) -> None:
    language = _language(row)
    strongs = _normalize_strongs(row.get("strongs_number"), language)
    lemma, transliteration, entry_id = _entry_metadata(connection, language, strongs, row.get("lemma"))
    surface = _required_text(row, "surface_form")
    morphology_code = _optional_text(row.get("morphology_code"))
    morphology = _morphology(row, language, morphology_code)
    connection.execute(
        """
        INSERT INTO word_forms (
            language, surface_form, normalized_form, lemma, normalized_lemma,
            transliteration, normalized_transliteration, strongs_number,
            morphology_code, morphology_json, lexicon_entry_id, source,
            source_word_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source, source_word_id) DO UPDATE SET
            language = excluded.language,
            surface_form = excluded.surface_form,
            normalized_form = excluded.normalized_form,
            lemma = excluded.lemma,
            normalized_lemma = excluded.normalized_lemma,
            transliteration = excluded.transliteration,
            normalized_transliteration = excluded.normalized_transliteration,
            strongs_number = excluded.strongs_number,
            morphology_code = excluded.morphology_code,
            morphology_json = excluded.morphology_json,
            lexicon_entry_id = excluded.lexicon_entry_id
        """,
        (
            language,
            surface,
            _normalize_form(surface),
            lemma,
            _normalize_form(lemma),
            _optional_text(row.get("transliteration")) or transliteration,
            _normalize_transliteration(row.get("transliteration") or transliteration),
            strongs,
            morphology_code,
            json.dumps(morphology, sort_keys=True, ensure_ascii=False),
            entry_id,
            source_name,
            _optional_text(row.get("source_word_id")),
        ),
    )


def _insert_verse_word(
    connection: sqlite3.Connection,
    row: Mapping[str, Any],
    *,
    source_name: str,
) -> None:
    language = _language(row)
    strongs = _normalize_strongs(row.get("strongs_number"), language)
    lemma, transliteration, entry_id = _entry_metadata(connection, language, strongs, row.get("lemma"))
    surface = _required_text(row, "surface_form")
    morphology_code = _optional_text(row.get("morphology_code"))
    morphology = _morphology(row, language, morphology_code)
    connection.execute(
        """
        INSERT INTO verse_words (
            book, chapter, verse, word_position, source_word_id, language,
            surface_form, normalized_form, lemma, normalized_lemma,
            transliteration, normalized_transliteration, strongs_number,
            morphology_code, morphology_json, lexicon_entry_id, source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(book, chapter, verse, word_position, language) DO UPDATE SET
            source_word_id = excluded.source_word_id,
            surface_form = excluded.surface_form,
            normalized_form = excluded.normalized_form,
            lemma = excluded.lemma,
            normalized_lemma = excluded.normalized_lemma,
            transliteration = excluded.transliteration,
            normalized_transliteration = excluded.normalized_transliteration,
            strongs_number = excluded.strongs_number,
            morphology_code = excluded.morphology_code,
            morphology_json = excluded.morphology_json,
            lexicon_entry_id = excluded.lexicon_entry_id,
            source = excluded.source
        """,
        (
            _required_text(row, "book"),
            int(row.get("chapter") or 0),
            int(row.get("verse") or 0),
            int(row.get("word_position") or 0),
            _optional_text(row.get("source_word_id")),
            language,
            surface,
            _normalize_form(surface),
            lemma,
            _normalize_form(lemma),
            _optional_text(row.get("transliteration")) or transliteration,
            _normalize_transliteration(row.get("transliteration") or transliteration),
            strongs,
            morphology_code,
            json.dumps(morphology, sort_keys=True, ensure_ascii=False),
            entry_id,
            source_name,
        ),
    )


def _upsert_source(connection: sqlite3.Connection, source: Mapping[str, str]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        """
        INSERT INTO lexical_sources (
            source, license, attribution, source_url, revision, imported_at, source_file
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source) DO UPDATE SET
            license = excluded.license,
            attribution = excluded.attribution,
            source_url = excluded.source_url,
            revision = excluded.revision,
            imported_at = excluded.imported_at,
            source_file = excluded.source_file
        """,
        (
            _required_text(source, "name"),
            _required_text(source, "license"),
            _required_text(source, "attribution"),
            str(source.get("source_url") or source.get("repository_url") or ""),
            _required_text(source, "revision"),
            now,
            str(source.get("source_file") or ""),
        ),
    )


def _entry_metadata(
    connection: sqlite3.Connection,
    language: str,
    strongs: str | None,
    fallback_lemma: object,
) -> tuple[str, str | None, int | None]:
    row = None
    if strongs:
        row = connection.execute(
            """
            SELECT id, lemma, transliteration
            FROM lexical_entries
            WHERE language = ? AND strongs_number = ?
            ORDER BY source, id
            LIMIT 1
            """,
            (language, strongs),
        ).fetchone()
    if row is None and fallback_lemma:
        row = connection.execute(
            """
            SELECT id, lemma, transliteration
            FROM lexical_entries
            WHERE language = ? AND normalized_lemma = ?
            ORDER BY source, id
            LIMIT 1
            """,
            (language, _normalize_form(str(fallback_lemma))),
        ).fetchone()
    if row:
        return str(row["lemma"]), _optional_text(row["transliteration"]), int(row["id"])
    lemma = _optional_text(fallback_lemma) or strongs
    if not lemma:
        raise ValueError("token row must include lemma or Strong's number")
    return lemma, None, None


def _record_from_row(row: Mapping[str, str]) -> dict[str, Any]:
    language = _optional_text(row.get("language")) or _language_from_strongs(row.get("strongs_number") or row.get("strongs"))
    if not language:
        raise ValueError("row missing language or prefixed Strong's number")
    record = {
        "language": language,
        "surface_form": _required_any(row, "surface_form", "form", "word"),
        "lemma": _optional_first(row, "lemma", "normalized_lemma"),
        "transliteration": _optional_first(row, "transliteration", "xlit"),
        "strongs_number": _optional_first(row, "strongs_number", "strongs"),
        "morphology_code": _optional_first(row, "morphology_code", "morph", "parse"),
        "source_word_id": _optional_first(row, "source_word_id", "word_id", "id"),
    }
    if _optional_text(row.get("book")):
        record.update(
            {
                "book": _required_any(row, "book"),
                "chapter": int(_required_any(row, "chapter")),
                "verse": int(_required_any(row, "verse")),
                "word_position": int(_required_any(row, "word_position", "position")),
            }
        )
    if _optional_text(row.get("morphology_json")):
        parsed = json.loads(str(row["morphology_json"]))
        if not isinstance(parsed, Mapping):
            raise ValueError("morphology_json must be a JSON object")
        record["morphology"] = dict(parsed)
    return record


def _morphology(row: Mapping[str, Any], language: str, morphology_code: str | None) -> dict[str, Any]:
    raw = row.get("morphology")
    if isinstance(raw, Mapping):
        return dict(raw)
    return decode_morphology(language, morphology_code)


def _strongs_from_oshb_lemma(value: object) -> str | None:
    parts = [part.strip() for part in str(value or "").split("/") if part.strip()]
    for part in reversed(parts):
        match = re.search(r"(\d+)", part)
        if match:
            return f"H{int(match.group(1))}"
    return None


def _language(row: Mapping[str, Any]) -> str:
    language = _optional_text(row.get("language")) or _language_from_strongs(row.get("strongs_number"))
    if language not in {"hebrew", "greek", "aramaic"}:
        raise ValueError("language must be hebrew, greek, or aramaic")
    return language


def _language_from_strongs(value: object) -> str | None:
    raw = str(value or "").strip().upper()
    if raw.startswith("H"):
        return "hebrew"
    if raw.startswith("G"):
        return "greek"
    return None


def _normalize_strongs(value: object, language: str) -> str | None:
    raw = str(value or "").strip().upper()
    if not raw:
        return None
    match = re.fullmatch(r"([HG])?\s*0*([0-9]+)[A-Z]?", raw)
    if not match:
        return raw
    prefix, digits = match.groups()
    expected = "H" if language == "hebrew" else "G"
    if prefix and prefix != expected:
        raise ValueError(f"Strong's prefix {prefix} does not match language {language}")
    return f"{expected}{int(digits)}"


def _normalize_form(value: object) -> str:
    import unicodedata

    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.replace("ς", "σ").split())


def _normalize_transliteration(value: object) -> str | None:
    if not value:
        return None
    import unicodedata

    text = unicodedata.normalize("NFD", str(value).strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    for mark in ("ʾ", "ʿ", "ʼ", "‘", "’"):
        text = text.replace(mark, "")
    text = text.translate(str.maketrans({"ḥ": "h", "ḫ": "h", "š": "s", "ś": "s", "ṭ": "t", "ṣ": "s", "ẓ": "z"}))
    text = "".join(char for char in text if char.isalnum() or char.isspace())
    return " ".join(text.split()) or None


def _osis_tag(name: str) -> str:
    return f"{{http://www.bibletechnologies.net/2003/OSIS/namespace}}{name}"


def _required_any(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = _optional_text(row.get(key))
        if value:
            return value
    raise ValueError("required token field missing: " + " or ".join(keys))


def _optional_first(row: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _optional_text(row.get(key))
        if value:
            return value
    return None


def _required_text(row: Mapping[str, Any], key: str) -> str:
    value = _optional_text(row.get(key))
    if not value:
        raise ValueError(f"required token field missing: {key}")
    return value


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_LEXICAL_DATABASE_PATH))
    parser.add_argument("--verse-words-tsv", action="append", default=[], type=Path)
    parser.add_argument("--word-forms-tsv", action="append", default=[], type=Path)
    parser.add_argument("--oshb-osis", action="append", default=[], type=Path)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", default="")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--attribution", required=True)
    parser.add_argument("--rebuild-tokens", action="store_true")
    args = parser.parse_args(argv)

    verse_words: list[dict[str, Any]] = []
    word_forms: list[dict[str, Any]] = []
    source_files: list[str] = []
    for path in args.verse_words_tsv:
        verse_words.extend(read_tsv(path))
        source_files.append(str(path))
    for path in args.word_forms_tsv:
        word_forms.extend(read_tsv(path))
        source_files.append(str(path))
    for path in args.oshb_osis:
        verse_words.extend(read_oshb_osis(path))
        source_files.append(str(path))

    counts = import_verse_tokens(
        args.database,
        source={
            "name": args.source_name,
            "source_url": args.source_url,
            "revision": args.revision,
            "license": args.license,
            "attribution": args.attribution,
            "source_file": ";".join(source_files),
        },
        verse_words=verse_words,
        word_forms=word_forms,
        rebuild_tokens=args.rebuild_tokens,
    )
    print("Imported verse token data.")
    print(f"Verse words: {counts['verse_words']}")
    print(f"Word forms: {counts['word_forms']}")
    print(f"Database: {args.database}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
