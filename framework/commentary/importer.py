"""Safe, deterministic importer for locally downloaded Tyndale archives."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import os
import re
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from bhf_agent.bible import BibleError, normalize_book_name

from .database_schema import DEFAULT_COMMENTARY_DATABASE_PATH, initialize_database

IMPORTER_VERSION = "tyndale-2"
SOURCE_ID = "tyndale_open_study_notes"
SOURCE_NAME = "Tyndale Open Study Notes"
SOURCE_LICENSE = "CC BY-SA 4.0"
SOURCE_LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
SOURCE_ATTRIBUTION = (
    "Tyndale Open Study Notes\n"
    "Copyright © 2022 Tyndale House Publishers\n"
    "Licensed under CC BY-SA 4.0\n"
    "Adapted from Tyndale Open Study Notes. Formatting and storage structure were converted for BHF. "
    "The underlying commentary text was not intentionally altered."
)
MAX_MEMBER_BYTES = 100 * 1024 * 1024
REFERENCE_RE = re.compile(
    r"(?P<book>(?:[1-3]\s+)?[A-Za-z][A-Za-z' -]+?)\s+"
    r"(?P<chapter>\d{1,3})(?::(?P<verse>\d{1,3})(?:[-–](?P<end_verse>\d{1,3}))?)?"
)


class CommentaryImportError(ValueError):
    """Raised when an archive cannot be safely or meaningfully imported."""


def import_tyndale_archive(
    source_path: str | Path,
    output_path: str | Path = DEFAULT_COMMENTARY_DATABASE_PATH,
    *,
    source_url: str | None = None,
    fail_on_unmapped: bool = False,
) -> dict[str, Any]:
    source = Path(source_path)
    if not source.is_file():
        raise CommentaryImportError(f"source archive does not exist: {source}")
    source_sha256 = _sha256(source)
    records, diagnostics = _read_archive(source)
    parsed = []
    for index, record in enumerate(records, start=1):
        item = _parse_record(record, index)
        if item is None:
            diagnostics["unrecognized_records"].append(index)
        else:
            parsed.append(item)
    mapped = [item for item in parsed if item is not None]
    diagnostics["records_seen"] = len(records)
    diagnostics["parsed_records"] = len(mapped)
    diagnostics["unmapped_records"] = [
        item["record_index"]
        for item in mapped
        if item["anchor"] is None and item["has_anchor_hint"]
    ]
    diagnostics["unanchored_records"] = [
        item["record_index"]
        for item in mapped
        if item["anchor"] is None and not item["has_anchor_hint"]
    ]
    diagnostics.update(
        {
            "source_sha256": source_sha256,
            "entry_count": len(mapped),
            "anchor_count": sum(1 for item in mapped if item["anchor"]),
            "entry_counts_by_kind": _counts(item["kind"] for item in mapped),
            "recognized_books": sorted({item["anchor"]["book"] for item in mapped if item["anchor"]}),
        }
    )
    if diagnostics["unmapped_records"]:
        diagnostics["warnings"].append(
            "Some records contained a Scripture reference but could not be mapped; "
            "review unmapped_records before production use."
        )
    if fail_on_unmapped and diagnostics["unmapped_records"]:
        raise CommentaryImportError(
            "archive contains unmapped Scripture records: "
            + ", ".join(str(index) for index in diagnostics["unmapped_records"])
        )

    database_path = Path(output_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_fd, temporary_name = tempfile.mkstemp(
        prefix=f".{database_path.name}.", suffix=".tmp", dir=database_path.parent
    )
    os.close(temporary_fd)
    temporary_path = Path(temporary_name)
    imported_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        initialize_database(temporary_path)
        with sqlite3.connect(temporary_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """INSERT INTO commentary_sources
                   (id, name, copyright, license, license_url, attribution, source_url,
                    source_sha256, imported_at, importer_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    SOURCE_ID, SOURCE_NAME, "Copyright © 2022 Tyndale House Publishers",
                    SOURCE_LICENSE, SOURCE_LICENSE_URL, SOURCE_ATTRIBUTION, source_url,
                    source_sha256, imported_at, IMPORTER_VERSION,
                ),
            )
            for item in mapped:
                cursor = connection.execute(
                    """INSERT INTO commentary_entries
                       (source_id, external_id, kind, title, body, sort_order, source_locator, payload_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        SOURCE_ID, item["external_id"], item["kind"], item["title"], item["body"],
                        item["sort_order"], item["source_locator"],
                        json.dumps(item["payload"], ensure_ascii=False, sort_keys=True) if item["payload"] else None,
                    ),
                )
                if item["anchor"]:
                    anchor = item["anchor"]
                    connection.execute(
                        """INSERT INTO commentary_anchors
                           (entry_id, book, start_chapter, start_verse, end_chapter, end_verse, relationship)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (cursor.lastrowid, anchor["book"], anchor["start_chapter"], anchor["start_verse"],
                         anchor["end_chapter"], anchor["end_verse"], anchor["relationship"]),
                    )
            connection.execute(
                "INSERT INTO commentary_metadata(key, value) VALUES('import_diagnostics', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (json.dumps(diagnostics, ensure_ascii=False, sort_keys=True),),
            )
        os.replace(temporary_path, database_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return {"output": str(database_path), **diagnostics}


def _read_archive(source: Path) -> tuple[list[Any], dict[str, Any]]:
    diagnostics: dict[str, Any] = {"warnings": [], "unrecognized_records": [], "recognized_files": []}
    if source.suffix.lower() != ".zip":
        return _parse_member(source.name, source.read_bytes(), diagnostics)
    try:
        with zipfile.ZipFile(source) as archive:
            members = archive.infolist()
            files: list[tuple[str, bytes]] = []
            for member in members:
                _validate_zip_member(member)
                if member.is_dir():
                    continue
                if member.file_size > MAX_MEMBER_BYTES:
                    raise CommentaryImportError(f"archive member is too large: {member.filename}")
                files.append((member.filename, archive.read(member)))
    except zipfile.BadZipFile as exc:
        raise CommentaryImportError(f"invalid ZIP archive: {source}") from exc

    records: list[Any] = []
    for name, content in sorted(files, key=lambda item: item[0].lower()):
        try:
            member_records, recognized = _parse_member(name, content, diagnostics)
        except CommentaryImportError:
            raise
        records.extend(member_records)
        if recognized:
            diagnostics["recognized_files"].append(name)
    if not records:
        diagnostics["warnings"].append("No structured commentary records were recognized in the archive.")
    return records, diagnostics


def _validate_zip_member(member: zipfile.ZipInfo) -> None:
    name = member.filename.replace("\\", "/")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or name.startswith("/"):
        raise CommentaryImportError(f"unsafe ZIP member path: {member.filename}")
    # Unix symlink mode is stored in the upper external-attribute bits.
    if (member.external_attr >> 16) & 0o170000 == 0o120000:
        raise CommentaryImportError(f"symlinks are not allowed in commentary archives: {member.filename}")


def _parse_member(name: str, content: bytes, diagnostics: dict[str, Any]) -> tuple[list[Any], bool]:
    suffix = Path(name).suffix.lower()
    if suffix in {".json", ".jsonl"}:
        try:
            if suffix == ".jsonl":
                return [json.loads(line) for line in content.decode("utf-8").splitlines() if line.strip()], True
            value = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            diagnostics["warnings"].append(f"Could not parse {name}: {exc}")
            return [], False
        return _records_from_container(value), True
    if suffix in {".csv", ".tsv"}:
        try:
            delimiter = "\t" if suffix == ".tsv" else ","
            return list(csv.DictReader(io.StringIO(content.decode("utf-8")), delimiter=delimiter)), True
        except UnicodeDecodeError as exc:
            diagnostics["warnings"].append(f"Could not parse {name}: {exc}")
            return [], False
    if suffix == ".xml":
        return _parse_xml(content, name, diagnostics), True
    return [], False


def _records_from_container(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("entries", "notes", "records", "items", "commentary"):
            if isinstance(value.get(key), list):
                return value[key]
        return [value]
    return []


def _parse_xml(content: bytes, name: str, diagnostics: dict[str, Any]) -> list[Any]:
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(content)
    except (UnicodeDecodeError, ET.ParseError) as exc:
        diagnostics["warnings"].append(f"Could not parse {name}: {exc}")
        return []
    records = []
    for element in root.iter():
        children = list(element)
        text = "".join(element.itertext()).strip()
        if text and (not children or any(key in element.attrib for key in ("book", "reference", "ref", "id"))):
            records.append({**element.attrib, "body": text, "kind": element.tag})
    return records


def _parse_record(record: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    body = _clean_text(_first(record, "body", "text", "content", "note", "commentary", "description"))
    if not body:
        return None
    anchor = _parse_anchor(record)
    kind = _normalize_kind(_first(record, "kind", "type", "content_type", "section"), anchor, record)
    return {
        "external_id": _string(_first(record, "external_id", "id", "uid", "key")) or f"record-{index}",
        "kind": kind,
        "title": _clean_text(_first(record, "title", "heading", "name")) or None,
        "body": body,
        "sort_order": _integer(_first(record, "sort_order", "order", "position"), index),
        "source_locator": _string(_first(record, "source_locator", "locator", "path", "file")) or None,
        "anchor": anchor,
        "record_index": index,
        "has_anchor_hint": _has_anchor_hint(record),
        "payload": record,
    }


def _has_anchor_hint(record: dict[str, Any]) -> bool:
    return any(
        _first(record, key) not in (None, "")
        for key in (
            "reference", "ref", "osis_ref", "osis", "scripture", "passage", "anchor",
            "book", "book_name", "book_id", "start_chapter", "chapter", "chapter_start",
            "start_verse", "verse", "verse_start", "end_chapter", "chapter_end",
            "end_verse", "verse_end",
        )
    )


def _parse_anchor(record: dict[str, Any]) -> dict[str, Any] | None:
    reference = _first(record, "reference", "ref", "osis_ref", "osis", "scripture", "passage", "anchor")
    book = _first(record, "book", "book_name", "book_id")
    chapter = _first(record, "start_chapter", "chapter", "chapter_start")
    verse = _first(record, "start_verse", "verse", "verse_start")
    end_chapter = _first(record, "end_chapter", "chapter_end")
    end_verse = _first(record, "end_verse", "verse_end")
    if reference and (not book or not chapter):
        match = REFERENCE_RE.search(str(reference).replace(".", " "))
        if match:
            book, chapter, verse, end_verse = match.group("book"), match.group("chapter"), match.group("verse"), match.group("end_verse")
    if not book:
        return None
    try:
        canonical_book = normalize_book_name(str(book).strip())
    except BibleError:
        return None
    start_chapter = _integer(chapter, None)
    if not start_chapter:
        return {
            "book": canonical_book, "start_chapter": None, "start_verse": None,
            "end_chapter": None, "end_verse": None,
            "relationship": _string(_first(record, "relationship", "relation", "anchor_type")),
        }
    start_verse = _integer(verse, None)
    end_chapter = _integer(end_chapter, None) or start_chapter
    end_verse = _integer(end_verse, None) or start_verse
    if end_verse is not None and start_verse is not None and end_verse < start_verse and end_chapter == start_chapter:
        return None
    relationship = _string(_first(record, "relationship", "relation", "anchor_type"))
    return {
        "book": canonical_book, "start_chapter": start_chapter, "start_verse": start_verse,
        "end_chapter": end_chapter, "end_verse": end_verse, "relationship": relationship,
    }


def _normalize_kind(value: Any, anchor: dict[str, Any] | None, record: dict[str, Any]) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    if normalized in {"verse", "verse_note", "note", "commentary"}:
        return "verse_note" if anchor and anchor.get("start_verse") else "chapter_note"
    if normalized in {"introduction", "book_intro", "book_introduction"}:
        return "book_introduction"
    if normalized in {"profile", "theme", "theme_article", "article", "chapter_note", "range_note", "verse_note"}:
        return normalized
    if anchor and anchor.get("start_verse"):
        return "range_note" if anchor.get("end_verse") != anchor.get("start_verse") else "verse_note"
    if anchor:
        return "chapter_note"
    title = str(_first(record, "title", "heading", "name") or "").lower()
    if "intro" in title:
        return "book_introduction"
    return normalized or "other"


def _first(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _string(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def _integer(value: Any, default: int | None) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    return result if result > 0 else default


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))
