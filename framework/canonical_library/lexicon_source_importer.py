"""Source-manifest importer for local lexical datasets.

The source manifest layer converts inspected local source exports into the
normalized lexical payload consumed by ``lexicon_importer``. It never downloads
data and never runs during application startup.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .lexicon_importer import import_normalized_lexicon_payload
from .lexicon_normalization import normalize_strongs_number


SOURCE_KINDS = frozenset(
    {
        "lexicon_json",
        "openscriptures_strongs_json",
        "openscriptures_hebrewlexicon_json",
        "verse_words_tsv",
        "morphgnt_tsv",
        "morphhb_tsv",
        "word_forms_tsv",
    }
)


def import_source_manifest(
    database_path: str | Path,
    manifest_path: str | Path,
    *,
    rebuild: bool = False,
) -> dict[str, int]:
    manifest_file = Path(manifest_path)
    payload, content_hash = normalized_payload_from_source_manifest(manifest_file)
    return import_normalized_lexicon_payload(
        database_path,
        payload,
        rebuild=rebuild,
        content_hash=content_hash,
    )


def normalized_payload_from_source_manifest(
    manifest_path: str | Path,
) -> tuple[dict[str, Any], str]:
    manifest_file = Path(manifest_path)
    raw = json.loads(manifest_file.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("lexicon source manifest must be a JSON object")
    manifest_dir = manifest_file.parent
    payload: dict[str, Any] = {
        "sources": [],
        "entries": [],
        "word_forms": [],
        "verse_words": [],
        "relations": [],
    }
    hash_parts = [manifest_file.read_bytes()]
    for source in _required_list(raw, "sources"):
        source_data = _required_mapping(source, "source")
        kind = _required_text(source_data, "kind")
        if kind not in SOURCE_KINDS:
            raise ValueError(f"unsupported lexicon source kind: {kind}")
        source_path = _source_path(manifest_dir, source_data)
        hash_parts.append(source_path.read_bytes())
        source_record = _source_record(source_data)
        payload["sources"].append(source_record)
        if kind in {
            "lexicon_json",
            "openscriptures_strongs_json",
            "openscriptures_hebrewlexicon_json",
        }:
            payload["entries"].extend(_parse_lexicon_json(source_path, source_record))
        elif kind in {"verse_words_tsv", "morphgnt_tsv", "morphhb_tsv"}:
            payload["verse_words"].extend(_parse_delimited_rows(source_path, source_record))
        elif kind == "word_forms_tsv":
            payload["word_forms"].extend(_parse_delimited_rows(source_path, source_record))
    content_hash = hashlib.sha256(b"\n".join(hash_parts)).hexdigest()
    return payload, content_hash


def _parse_lexicon_json(path: Path, source: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    records = raw.values() if isinstance(raw, Mapping) else raw
    if not isinstance(records, Iterable):
        raise ValueError(f"lexicon JSON source must contain a list or object: {path}")
    entries: list[dict[str, Any]] = []
    for record in records:
        data = _required_mapping(record, "lexicon entry")
        lemma = _first_text(data, "lemma", "word", "headword")
        strongs = normalize_strongs_number(_first_text(data, "strongs_number", "strongs", "number", "id"))
        source_entry_id = _first_text(data, "source_entry_id", "id", "strongs_number", "strongs", "number") or strongs
        language = _first_text(data, "language") or _language_from_strongs(strongs)
        if not lemma or not language or not source_entry_id:
            raise ValueError(f"lexicon entry missing lemma, language, or source id in {path}")
        glosses = _glosses_from_record(data)
        entry = {
            "language": language,
            "lemma": lemma,
            "transliteration": _optional_first_text(data, "transliteration", "xlit"),
            "strongs_number": strongs,
            "part_of_speech": _optional_first_text(data, "part_of_speech", "pos"),
            "short_gloss": "; ".join(glosses),
            "definition": _optional_first_text(data, "definition", "description", "meaning"),
            "source_name": source["name"],
            "source_entry_id": source_entry_id,
            "license": source["license"],
            "attribution": source["attribution"],
            "senses": _senses_from_record(data, glosses),
        }
        entries.append(entry)
    return entries


def _parse_delimited_rows(path: Path, source: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        dialect = csv.excel_tab if path.suffix.lower() in {".tsv", ".tab"} else csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        if reader.fieldnames is None:
            raise ValueError(f"delimited lexical source must include a header row: {path}")
        for index, row in enumerate(reader, start=2):
            normalized = _clean_row(row)
            try:
                rows.append(_delimited_record(normalized, source))
            except ValueError as exc:
                raise ValueError(f"{path}:{index}: {exc}") from exc
    return rows


def _delimited_record(row: Mapping[str, str], source: Mapping[str, Any]) -> dict[str, Any]:
    language = _first_text(row, "language") or _language_from_strongs(
        _first_text(row, "strongs_number", "strongs")
    )
    if not language:
        raise ValueError("row missing language or prefixed Strong's number")
    record = {
        "language": language,
        "surface_form": _required_any(row, "surface_form", "form", "word"),
        "lemma": _required_any(row, "lemma", "normalized_lemma"),
        "transliteration": _optional_first_text(row, "transliteration", "xlit"),
        "strongs_number": normalize_strongs_number(_first_text(row, "strongs_number", "strongs")),
        "morphology_code": _optional_first_text(row, "morphology_code", "morph", "parse"),
        "source_name": source["name"],
        "source_word_id": _optional_first_text(row, "source_word_id", "word_id", "id"),
    }
    if _first_text(row, "book"):
        record.update(
            {
                "book": _required_any(row, "book"),
                "chapter": int(_required_any(row, "chapter")),
                "verse": int(_required_any(row, "verse")),
                "word_position": int(_required_any(row, "word_position", "position")),
            }
        )
    source_entry_id = _optional_first_text(row, "source_entry_id", "entry_id")
    if source_entry_id:
        record["source_entry_id"] = source_entry_id
    morphology_json = _optional_first_text(row, "morphology_json")
    if morphology_json:
        parsed = json.loads(morphology_json)
        if not isinstance(parsed, Mapping):
            raise ValueError("morphology_json must be a JSON object")
        record["morphology"] = dict(parsed)
    return record


def _source_record(source: Mapping[str, Any]) -> dict[str, str]:
    return {
        "name": _required_text(source, "name"),
        "repository_url": str(source.get("repository_url") or ""),
        "revision": _required_text(source, "revision"),
        "license": _required_text(source, "license"),
        "attribution": _required_text(source, "attribution"),
        "redistribution_status": str(source.get("redistribution_status") or "unknown"),
    }


def _source_path(manifest_dir: Path, source: Mapping[str, Any]) -> Path:
    raw_path = Path(_required_text(source, "path"))
    path = raw_path if raw_path.is_absolute() else manifest_dir / raw_path
    if not path.exists():
        raise FileNotFoundError(f"lexicon source file not found: {path}")
    return path


def _glosses_from_record(data: Mapping[str, Any]) -> list[str]:
    value = data.get("glosses") or data.get("gloss") or data.get("short_gloss")
    if isinstance(value, list):
        values = value
    else:
        values = str(value or "").replace(",", ";").split(";")
    return _unique_texts(str(item).strip() for item in values)


def _senses_from_record(data: Mapping[str, Any], glosses: list[str]) -> list[dict[str, Any]]:
    raw_senses = data.get("senses")
    if isinstance(raw_senses, list):
        senses = []
        for index, sense in enumerate(raw_senses, start=1):
            sense_data = _required_mapping(sense, "sense")
            gloss = _first_text(sense_data, "gloss", "label")
            if not gloss:
                continue
            senses.append(
                {
                    "sense_order": int(sense_data.get("sense_order") or index),
                    "gloss": gloss,
                    "definition": _optional_first_text(sense_data, "definition", "description"),
                    "semantic_domain": _optional_first_text(sense_data, "semantic_domain", "domain"),
                    "usage_note": _optional_first_text(sense_data, "usage_note", "note"),
                    "source_sense_id": _optional_first_text(sense_data, "source_sense_id", "id"),
                }
            )
        return senses
    definition = _optional_first_text(data, "definition", "description", "meaning")
    return [
        {"sense_order": index, "gloss": gloss, "definition": definition}
        for index, gloss in enumerate(glosses, start=1)
    ]


def _clean_row(row: Mapping[str, Any]) -> dict[str, str]:
    return {str(key or "").strip(): str(value or "").strip() for key, value in row.items()}


def _language_from_strongs(strongs: str | None) -> str | None:
    normalized = normalize_strongs_number(strongs)
    if not normalized:
        return None
    if normalized.startswith("H"):
        return "hebrew"
    if normalized.startswith("G"):
        return "greek"
    return None


def _required_list(data: Mapping[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise ValueError(f"lexicon source manifest field {key!r} must be a list")
    return value


def _required_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _required_text(data: Mapping[str, Any], key: str) -> str:
    value = str(data.get(key) or "").strip()
    if not value:
        raise ValueError(f"required source manifest field missing: {key}")
    return value


def _required_any(data: Mapping[str, Any], *keys: str) -> str:
    value = _first_text(data, *keys)
    if not value:
        raise ValueError(f"row missing required field: {'/'.join(keys)}")
    return value


def _optional_first_text(data: Mapping[str, Any], *keys: str) -> str | None:
    return _first_text(data, *keys) or None


def _first_text(data: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _unique_texts(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output
