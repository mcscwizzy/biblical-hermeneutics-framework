"""Shared storage and XML parsing helpers for local Bible translations."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from .references import BOOK_ALIASES, BOOKS
from .runtime_paths import RUNTIME_DATA_PATHS


DATA_PATH = Path(__file__).resolve().parent / "data" / "asv_bible.json"
LEGACY_KJV_DATA_PATH = Path(__file__).resolve().parent / "data" / "kjv_bible.json"
TRANSLATIONS_PATH = RUNTIME_DATA_PATHS.translations_path


class TranslationStorageError(ValueError):
    """Raised when a translation dataset or storage path cannot be resolved."""


def normalize_translation_id(translation_id: str) -> str:
    normalized = str(translation_id or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,31}", normalized):
        raise TranslationStorageError(
            "translation id must be 2-32 lowercase letters, numbers, underscores, or hyphens"
        )
    return normalized


def translations_root() -> Path:
    return TRANSLATIONS_PATH


def installed_translation_path(translation_id: str) -> Path:
    normalized = normalize_translation_id(translation_id)
    return translations_root() / f"{normalized}.json"


def installed_translation_metadata_path(translation_id: str) -> Path:
    normalized = normalize_translation_id(translation_id)
    return translations_root() / f"{normalized}.metadata.json"


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    temp_path = Path(temp_name)
    try:
        temp_path.replace(path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise


def load_bible_dataset(path: str | Path) -> dict[str, Any]:
    bible_path = Path(path)
    try:
        data = json.loads(bible_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TranslationStorageError(f"Bible dataset not found: {bible_path}") from exc
    except json.JSONDecodeError as exc:
        raise TranslationStorageError(f"Bible dataset is invalid JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("books"), list):
        data = _normalize_dataset(data, bible_path)
    return data


def load_asv_bible(path: str | Path = DATA_PATH) -> dict[str, Any]:
    return load_bible_dataset(path)


def load_legacy_kjv_bible(path: str | Path = LEGACY_KJV_DATA_PATH) -> dict[str, Any]:
    return load_bible_dataset(path)


def load_installed_translation_bible(translation_id: str) -> dict[str, Any]:
    normalized = normalize_translation_id(translation_id)
    if normalized == "asv":
        return load_asv_bible()
    if normalized == "kjv":
        return load_legacy_kjv_bible()
    installed = installed_translation_path(normalized)
    if installed.exists():
        return load_bible_dataset(installed)
    raise TranslationStorageError(f"translation is not installed: {normalized}")


def count_bible_statistics(data: dict[str, Any]) -> dict[str, int]:
    books = list(data.get("books", []))
    chapter_count = 0
    verse_count = 0
    for book in books:
        for chapter in book.get("chapters", []):
            chapter_count += 1
            verse_count += len(chapter.get("verses", []))
    return {
        "book_count": len(books),
        "chapter_count": chapter_count,
        "verse_count": verse_count,
    }


def parse_bible_xml(
    xml_content: bytes,
    *,
    translation_id: str,
    translation_name: str | None = None,
    source_filename: str = "",
) -> dict[str, Any]:
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise TranslationStorageError(f"Bible XML is not well-formed: {exc}") from exc

    normalized_id = normalize_translation_id(translation_id)
    translation = {
        "id": normalized_id.upper(),
        "name": translation_name
        or root.attrib.get("biblename")
        or root.attrib.get("name")
        or normalized_id.upper(),
        "language": root.attrib.get("language") or root.attrib.get("language_code") or "en",
        "publication_year": None,
        "license": "User imported local XML; BHF does not provide or verify this file",
        "source": source_filename,
        "source_note": "Manual local XML import. Private to this BHF instance.",
    }

    parsed_books = _parse_nested_bible_xml(root)
    if not parsed_books:
        raise TranslationStorageError("Bible XML format is not supported or contains no verses")
    return {"translation": translation, "books": parsed_books}


def _parse_nested_bible_xml(root: ElementTree.Element) -> list[dict[str, Any]]:
    books_by_name: dict[str, dict[int, list[dict[str, Any]]]] = {}
    ordered_books = list(BOOKS.keys())
    for book_element in root.iter():
        if _xml_local_name(book_element.tag) not in {"book", "biblebook"}:
            continue
        book_name = _book_name_from_xml_element(book_element, ordered_books)
        if not book_name:
            continue
        chapters = books_by_name.setdefault(book_name, {})
        for chapter_element in list(book_element):
            if _xml_local_name(chapter_element.tag) != "chapter":
                continue
            chapter_number = _xml_positive_int(
                chapter_element.attrib.get("cnumber")
                or chapter_element.attrib.get("number")
                or chapter_element.attrib.get("n")
                or chapter_element.attrib.get("id")
            )
            if chapter_number is None:
                continue
            verses = chapters.setdefault(chapter_number, [])
            for verse_element in list(chapter_element):
                if _xml_local_name(verse_element.tag) not in {"verse", "vers"}:
                    continue
                verse_number = _xml_positive_int(
                    verse_element.attrib.get("vnumber")
                    or verse_element.attrib.get("number")
                    or verse_element.attrib.get("n")
                    or verse_element.attrib.get("id")
                )
                if verse_number is None:
                    continue
                text = " ".join("".join(verse_element.itertext()).split())
                verses.append(
                    {
                        "book": book_name,
                        "chapter": chapter_number,
                        "verse": verse_number,
                        "text": text,
                    }
                )

    books = []
    for order, canonical_book in enumerate(ordered_books, start=1):
        chapter_map = books_by_name.get(canonical_book, {})
        if not chapter_map:
            continue
        chapters = []
        for chapter_number in sorted(chapter_map):
            chapters.append(
                {
                    "chapter": chapter_number,
                    "verses": sorted(
                        chapter_map[chapter_number],
                        key=lambda verse: int(verse["verse"]),
                    ),
                }
            )
        books.append({"name": canonical_book, "order": order, "chapters": chapters})
    return books


def _book_name_from_xml_element(
    element: ElementTree.Element,
    ordered_books: list[str],
) -> str | None:
    raw_name = (
        element.attrib.get("bname")
        or element.attrib.get("name")
        or element.attrib.get("book")
        or element.attrib.get("osisID")
        or ""
    )
    if raw_name:
        try:
            return normalize_book_name(raw_name)
        except TranslationStorageError:
            pass
    book_number = _xml_positive_int(
        element.attrib.get("bnumber")
        or element.attrib.get("number")
        or element.attrib.get("n")
        or element.attrib.get("id")
    )
    if book_number and 1 <= book_number <= len(ordered_books):
        return ordered_books[book_number - 1]
    return None


def normalize_book_name(name: str) -> str:
    compact = re.sub(r"\s+", " ", name.strip().lower().replace(".", ""))
    if compact in BOOK_ALIASES:
        return BOOK_ALIASES[compact]
    for canonical in BOOKS:
        if compact == canonical.lower():
            return canonical
    raise TranslationStorageError(f"unknown Bible book: {name}")


def _xml_local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1].lower()


def _xml_positive_int(value: Any) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return None
    number = int(match.group(0))
    return number if number > 0 else None


def _normalize_dataset(data: dict[str, Any], bible_path: Path) -> dict[str, Any]:
    resultset = data.get("resultset")
    if not isinstance(resultset, dict) or not isinstance(resultset.get("row"), list):
        raise TranslationStorageError("Bible dataset must contain a books list")

    ordered_books = list(BOOKS.keys())
    books_map: dict[str, dict[int, list[dict[str, Any]]]] = {}
    for row in resultset["row"]:
        field = row.get("field") if isinstance(row, dict) else None
        if not isinstance(field, list) or len(field) < 5:
            continue
        try:
            book_index = int(field[1])
            chapter_number = int(field[2])
            verse_number = int(field[3])
        except (TypeError, ValueError):
            continue
        if not 1 <= book_index <= len(ordered_books):
            continue
        canonical_book = ordered_books[book_index - 1]
        chapter_bucket = books_map.setdefault(canonical_book, {})
        verses = chapter_bucket.setdefault(chapter_number, [])
        verses.append(
            {
                "book": canonical_book,
                "chapter": chapter_number,
                "verse": verse_number,
                "text": str(field[4]),
            }
        )

    books = []
    for order, canonical_book in enumerate(ordered_books, start=1):
        chapters = []
        for chapter_number in sorted(books_map.get(canonical_book, {})):
            verses = sorted(
                books_map[canonical_book][chapter_number],
                key=lambda verse: int(verse["verse"]),
            )
            chapters.append(
                {
                    "chapter": chapter_number,
                    "verses": verses,
                }
            )
        if chapters:
            books.append(
                {
                    "name": canonical_book,
                    "order": order,
                    "chapters": chapters,
                }
            )

    stem = bible_path.stem.lower()
    translation_id = "KJV" if "kjv" in stem else data.get("translation", {}).get("id", "")
    translation_name = "King James Version" if translation_id == "KJV" else data.get("translation", {}).get("name", translation_id)
    translation = {
        "id": translation_id or bible_path.stem.upper(),
        "name": translation_name or bible_path.stem.upper(),
        "language": "en",
        "publication_year": 1769 if translation_id == "KJV" else None,
        "license": "Public domain in the United States",
        "source": "https://raw.githubusercontent.com/bibleapi/bibleapi-bibles-json/master/kjv.json"
        if translation_id == "KJV"
        else str(bible_path),
        "source_note": "Normalized from the bibleapi/bibleapi-bibles-json KJV JSON corpus for offline local study."
        if translation_id == "KJV"
        else "Normalized local Bible dataset for offline study.",
    }
    return {"translation": translation, "books": books}
