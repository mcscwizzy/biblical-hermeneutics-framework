"""Deterministic import helpers for normalized lexical source payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .lexicon_morphology import decode_morphology
from .lexicon_normalization import (
    normalize_language,
    normalize_script_form,
    normalize_strongs_number,
    normalize_transliteration,
    strongs_digits,
)

LEXICAL_TABLES = (
    "lexicon_relations",
    "verse_words",
    "word_forms",
    "lexicon_senses",
    "lexicon_entries",
    "lexicon_sources",
)


def import_normalized_lexicon_file(
    database_path: str | Path,
    payload_path: str | Path,
    *,
    rebuild: bool = False,
) -> dict[str, int]:
    """Import a small normalized lexical JSON payload into an existing CKL DB."""

    db_path = Path(database_path)
    source_path = Path(payload_path)
    payload_bytes = source_path.read_bytes()
    content_hash = hashlib.sha256(payload_bytes).hexdigest()
    payload = json.loads(payload_bytes.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("normalized lexical payload must be a JSON object")
    return import_normalized_lexicon_payload(
        db_path,
        payload,
        rebuild=rebuild,
        content_hash=content_hash,
    )


def import_normalized_lexicon_payload(
    database_path: str | Path,
    payload: Mapping[str, Any],
    *,
    rebuild: bool = False,
    content_hash: str,
) -> dict[str, int]:
    if not Path(database_path).exists():
        raise FileNotFoundError(
            f"CKL SQLite database not found: {database_path}. "
            "Build it first with: python -m framework.canonical_library build-db"
        )
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    counts = {
        "sources": 0,
        "entries": 0,
        "senses": 0,
        "word_forms": 0,
        "verse_words": 0,
        "relations": 0,
    }
    try:
        with conn:
            _assert_required_tables(conn)
            if rebuild:
                _clear_lexical_tables(conn)
            sources = _required_list(payload, "sources")
            entries = _required_list(payload, "entries")
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            source_revisions = _import_sources(
                conn,
                sources,
                imported_at=now,
                content_hash=content_hash,
            )
            counts["sources"] = len(sources)
            entry_ids = _import_entries(conn, entries, source_revisions=source_revisions)
            counts["entries"] = len(entries)
            counts["senses"] = _import_senses(conn, entries, entry_ids=entry_ids)
            counts["word_forms"] = _import_word_forms(
                conn,
                _optional_list(payload, "word_forms"),
                entry_ids=entry_ids,
            )
            counts["verse_words"] = _import_verse_words(
                conn,
                _optional_list(payload, "verse_words"),
                entry_ids=entry_ids,
            )
            counts["relations"] = _import_relations(conn, _optional_list(payload, "relations"))
    finally:
        conn.close()
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import explicit local lexical data into the generated CKL SQLite database."
    )
    parser.add_argument("--output", default=".bhf/ckl.sqlite", help="CKL SQLite database path")
    parser.add_argument(
        "--normalized-json",
        action="append",
        default=[],
        help="Normalized lexical JSON payload to import; repeat for multiple files",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete generated lexical tables before importing the first payload",
    )
    args = parser.parse_args(argv)
    if not args.normalized_json:
        parser.error("--normalized-json is required for the phase-1 importer")
    total = {
        "sources": 0,
        "entries": 0,
        "senses": 0,
        "word_forms": 0,
        "verse_words": 0,
        "relations": 0,
    }
    for index, payload_path in enumerate(args.normalized_json):
        counts = import_normalized_lexicon_file(
            args.output,
            payload_path,
            rebuild=args.rebuild and index == 0,
        )
        for key, value in counts.items():
            total[key] += value
    print("Imported lexical data:")
    for key in sorted(total):
        print(f"  {key}: {total[key]}")
    return 0


def _assert_required_tables(conn: sqlite3.Connection) -> None:
    names = {
        str(row["name"])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    missing = sorted(set(LEXICAL_TABLES) - names)
    if missing:
        raise RuntimeError(
            "CKL SQLite database is missing lexical tables: "
            + ", ".join(missing)
            + ". Rebuild it with: python -m framework.canonical_library build-db"
        )


def _clear_lexical_tables(conn: sqlite3.Connection) -> None:
    for table in LEXICAL_TABLES:
        conn.execute(f"DELETE FROM {table}")


def _import_sources(
    conn: sqlite3.Connection,
    sources: list[Any],
    *,
    imported_at: str,
    content_hash: str,
) -> dict[str, str]:
    revisions: dict[str, str] = {}
    for source in sources:
        data = _required_mapping(source, "source")
        name = _required_text(data, "name")
        revision = _required_text(data, "revision")
        license_name = _required_text(data, "license")
        attribution = _required_text(data, "attribution")
        revisions[name] = revision
        conn.execute(
            """
            INSERT OR REPLACE INTO lexicon_sources (
                name, repository_url, revision, license, attribution,
                redistribution_status, imported_at, content_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                str(data.get("repository_url") or ""),
                revision,
                license_name,
                attribution,
                str(data.get("redistribution_status") or "unknown"),
                imported_at,
                content_hash,
            ),
        )
    return revisions


def _import_entries(
    conn: sqlite3.Connection,
    entries: list[Any],
    *,
    source_revisions: Mapping[str, str],
) -> dict[tuple[str, str], int]:
    entry_ids: dict[tuple[str, str], int] = {}
    for entry in entries:
        data = _required_mapping(entry, "entry")
        source_name = _required_text(data, "source_name")
        source_entry_id = _required_text(data, "source_entry_id")
        if source_name not in source_revisions:
            raise ValueError(f"entry references unknown source_name: {source_name}")
        language = normalize_language(_required_text(data, "language"))
        lemma = _required_text(data, "lemma")
        strongs = normalize_strongs_number(data.get("strongs_number"))
        transliteration = _optional_text(data.get("transliteration"))
        conn.execute(
            """
            INSERT INTO lexicon_entries (
                language, lemma, normalized_lemma, transliteration,
                normalized_transliteration, pronunciation, strongs_number,
                normalized_strongs_number, strongs_digits, part_of_speech,
                short_gloss, definition, source_name, source_entry_id,
                source_revision, license, attribution
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_name, source_entry_id) DO UPDATE SET
                language = excluded.language,
                lemma = excluded.lemma,
                normalized_lemma = excluded.normalized_lemma,
                transliteration = excluded.transliteration,
                normalized_transliteration = excluded.normalized_transliteration,
                pronunciation = excluded.pronunciation,
                strongs_number = excluded.strongs_number,
                normalized_strongs_number = excluded.normalized_strongs_number,
                strongs_digits = excluded.strongs_digits,
                part_of_speech = excluded.part_of_speech,
                short_gloss = excluded.short_gloss,
                definition = excluded.definition,
                source_revision = excluded.source_revision,
                license = excluded.license,
                attribution = excluded.attribution
            """,
            (
                language,
                lemma,
                normalize_script_form(lemma, language=language),
                transliteration,
                normalize_transliteration(transliteration),
                _optional_text(data.get("pronunciation")),
                strongs,
                strongs,
                strongs_digits(strongs),
                _optional_text(data.get("part_of_speech")),
                _optional_text(data.get("short_gloss")),
                _optional_text(data.get("definition")),
                source_name,
                source_entry_id,
                source_revisions[source_name],
                _required_text(data, "license"),
                _required_text(data, "attribution"),
            ),
        )
        row = conn.execute(
            "SELECT id FROM lexicon_entries WHERE source_name = ? AND source_entry_id = ?",
            (source_name, source_entry_id),
        ).fetchone()
        entry_ids[(source_name, source_entry_id)] = int(row["id"])
    return entry_ids


def _import_senses(
    conn: sqlite3.Connection,
    entries: list[Any],
    *,
    entry_ids: Mapping[tuple[str, str], int],
) -> int:
    count = 0
    for entry in entries:
        data = _required_mapping(entry, "entry")
        source_name = _required_text(data, "source_name")
        source_entry_id = _required_text(data, "source_entry_id")
        entry_id = entry_ids[(source_name, source_entry_id)]
        conn.execute("DELETE FROM lexicon_senses WHERE lexicon_entry_id = ?", (entry_id,))
        for index, sense in enumerate(_optional_list(data, "senses"), start=1):
            sense_data = _required_mapping(sense, "sense")
            conn.execute(
                """
                INSERT INTO lexicon_senses (
                    lexicon_entry_id, sense_order, gloss, definition,
                    semantic_domain, usage_note, source_name, source_sense_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    int(sense_data.get("sense_order") or index),
                    _required_text(sense_data, "gloss"),
                    _optional_text(sense_data.get("definition")),
                    _optional_text(sense_data.get("semantic_domain")),
                    _optional_text(sense_data.get("usage_note")),
                    str(sense_data.get("source_name") or source_name),
                    _optional_text(sense_data.get("source_sense_id")),
                ),
            )
            count += 1
    return count


def _import_word_forms(
    conn: sqlite3.Connection,
    forms: list[Any],
    *,
    entry_ids: Mapping[tuple[str, str], int],
) -> int:
    count = 0
    for form in forms:
        data = _required_mapping(form, "word_form")
        source_name = _optional_text(data.get("source_name"))
        source_word_id = _optional_text(data.get("source_word_id"))
        language = normalize_language(_required_text(data, "language"))
        lemma = _required_text(data, "lemma")
        surface_form = _required_text(data, "surface_form")
        entry_id = _entry_id_for(data, entry_ids)
        morphology_code = _optional_text(data.get("morphology_code"))
        morphology = data.get("morphology") or decode_morphology(language, morphology_code)
        strongs = normalize_strongs_number(data.get("strongs_number"))
        conn.execute(
            """
            INSERT INTO word_forms (
                language, surface_form, normalized_form, lemma, normalized_lemma,
                transliteration, normalized_transliteration, strongs_number,
                normalized_strongs_number, strongs_digits, morphology_code,
                morphology_json, lexicon_entry_id, source_name, source_word_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_name, source_word_id) DO UPDATE SET
                language = excluded.language,
                surface_form = excluded.surface_form,
                normalized_form = excluded.normalized_form,
                lemma = excluded.lemma,
                normalized_lemma = excluded.normalized_lemma,
                transliteration = excluded.transliteration,
                normalized_transliteration = excluded.normalized_transliteration,
                strongs_number = excluded.strongs_number,
                normalized_strongs_number = excluded.normalized_strongs_number,
                strongs_digits = excluded.strongs_digits,
                morphology_code = excluded.morphology_code,
                morphology_json = excluded.morphology_json,
                lexicon_entry_id = excluded.lexicon_entry_id
            """,
            (
                language,
                surface_form,
                normalize_script_form(surface_form, language=language),
                lemma,
                normalize_script_form(lemma, language=language),
                _optional_text(data.get("transliteration")),
                normalize_transliteration(data.get("transliteration")),
                strongs,
                strongs,
                strongs_digits(strongs),
                morphology_code,
                json.dumps(morphology, sort_keys=True, ensure_ascii=False),
                entry_id,
                source_name,
                source_word_id,
            ),
        )
        count += 1
    return count


def _import_verse_words(
    conn: sqlite3.Connection,
    verse_words: list[Any],
    *,
    entry_ids: Mapping[tuple[str, str], int],
) -> int:
    count = 0
    for word in verse_words:
        data = _required_mapping(word, "verse_word")
        language = normalize_language(_required_text(data, "language"))
        lemma = _required_text(data, "lemma")
        surface_form = _required_text(data, "surface_form")
        morphology_code = _optional_text(data.get("morphology_code"))
        morphology = data.get("morphology") or decode_morphology(language, morphology_code)
        strongs = normalize_strongs_number(data.get("strongs_number"))
        conn.execute(
            """
            INSERT INTO verse_words (
                book, chapter, verse, word_position, source_word_id, language,
                surface_form, normalized_form, lemma, normalized_lemma,
                transliteration, normalized_transliteration, strongs_number,
                normalized_strongs_number, strongs_digits, morphology_code,
                morphology_json, lexicon_entry_id, source_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(book, chapter, verse, word_position, language) DO UPDATE SET
                source_word_id = excluded.source_word_id,
                surface_form = excluded.surface_form,
                normalized_form = excluded.normalized_form,
                lemma = excluded.lemma,
                normalized_lemma = excluded.normalized_lemma,
                transliteration = excluded.transliteration,
                normalized_transliteration = excluded.normalized_transliteration,
                strongs_number = excluded.strongs_number,
                normalized_strongs_number = excluded.normalized_strongs_number,
                strongs_digits = excluded.strongs_digits,
                morphology_code = excluded.morphology_code,
                morphology_json = excluded.morphology_json,
                lexicon_entry_id = excluded.lexicon_entry_id,
                source_name = excluded.source_name
            """,
            (
                _required_text(data, "book"),
                int(data.get("chapter")),
                int(data.get("verse")),
                int(data.get("word_position")),
                _optional_text(data.get("source_word_id")),
                language,
                surface_form,
                normalize_script_form(surface_form, language=language),
                lemma,
                normalize_script_form(lemma, language=language),
                _optional_text(data.get("transliteration")),
                normalize_transliteration(data.get("transliteration")),
                strongs,
                strongs,
                strongs_digits(strongs),
                morphology_code,
                json.dumps(morphology, sort_keys=True, ensure_ascii=False),
                _entry_id_for(data, entry_ids),
                _optional_text(data.get("source_name")),
            ),
        )
        count += 1
    return count


def _import_relations(conn: sqlite3.Connection, relations: list[Any]) -> int:
    count = 0
    for relation in relations:
        data = _required_mapping(relation, "relation")
        conn.execute(
            """
            INSERT OR REPLACE INTO lexicon_relations (
                source_entry_id, relation_type, target_entry_id, source_name
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                _required_text(data, "source_entry_id"),
                _required_text(data, "relation_type"),
                _required_text(data, "target_entry_id"),
                _required_text(data, "source_name"),
            ),
        )
        count += 1
    return count


def _entry_id_for(data: Mapping[str, Any], entry_ids: Mapping[tuple[str, str], int]) -> int | None:
    source_name = _optional_text(data.get("source_name"))
    source_entry_id = _optional_text(data.get("source_entry_id"))
    if not source_name or not source_entry_id:
        return None
    try:
        return entry_ids[(source_name, source_entry_id)]
    except KeyError as exc:
        raise ValueError(
            f"record references unknown lexicon entry: {source_name}/{source_entry_id}"
        ) from exc


def _required_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"normalized lexical payload field {key!r} must be a list")
    return value


def _optional_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"normalized lexical payload field {key!r} must be a list")
    return value


def _required_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _required_text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"required lexical field missing: {key}")
    return text


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


if __name__ == "__main__":
    raise SystemExit(main())
