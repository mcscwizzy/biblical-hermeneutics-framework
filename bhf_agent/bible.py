"""Local ASV Bible dataset helpers."""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from .references import BOOK_ALIASES, BOOKS
from . import translation_storage
from .translation_installer import install_xml_translation, list_installed_translations
from .bible_support import (
    _GEOGRAPHY_GUIDES,
    _SEARCH_REFERENCE_RE,
    _TIMELINE_GUIDES,
    _TOPICAL_SINGLE_TERMS,
    _TOPIC_HINT_WORDS,
)


DATA_PATH = Path(__file__).resolve().parent / "data" / "asv_bible.json"
KJV_DATA_PATH = Path(__file__).resolve().parent / "data" / "kjv_bible.json"
IMPORTED_TRANSLATIONS_DIR = Path(
    os.environ.get("BHF_TRANSLATIONS_PATH", str(translation_storage.TRANSLATIONS_PATH))
)


class BibleError(ValueError):
    """Raised when a Bible lookup cannot be resolved."""


@lru_cache(maxsize=1)
def load_asv_bible(path: str | Path = DATA_PATH) -> dict[str, Any]:
    """Load the committed ASV dataset."""

    return load_bible_dataset(path)


@lru_cache(maxsize=4)
def load_bible_dataset(path: str | Path) -> dict[str, Any]:
    """Load a committed Bible dataset from disk."""

    bible_path = Path(path)
    try:
        data = json.loads(bible_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BibleError(f"Bible dataset not found: {bible_path}") from exc
    except json.JSONDecodeError as exc:
        raise BibleError(f"Bible dataset is invalid JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("books"), list):
        data = _normalize_dataset(data, bible_path)
    return data


@lru_cache(maxsize=1)
def load_kjv_bible(path: str | Path = KJV_DATA_PATH) -> dict[str, Any]:
    """Load the committed KJV dataset."""

    return load_bible_dataset(path)


def load_translation_bible(translation_id: str) -> dict[str, Any]:
    """Load an installed local Bible dataset by catalog translation id."""

    normalized = translation_storage.normalize_translation_id(translation_id or "asv")
    if normalized == "asv":
        return load_asv_bible()
    try:
        return translation_storage.load_installed_translation_bible(normalized)
    except translation_storage.TranslationStorageError as exc:
        raise BibleError(str(exc)) from exc


def list_translation_books(translation_id: str = "asv") -> list[dict[str, Any]]:
    """List books for an installed local translation."""

    return list_books(load_translation_bible(translation_id))


def resolve_translation_chapter(
    translation_id: str,
    book: str,
    chapter: int | str,
) -> dict[str, Any]:
    """Resolve a chapter from an installed local translation."""

    return resolve_chapter(book, chapter, load_translation_bible(translation_id))


def imported_translation_path(translation_id: str) -> Path:
    normalized = _normalize_translation_id(translation_id)
    return translation_storage.installed_translation_path(normalized)


def save_imported_xml_translation(
    translation_id: str,
    xml_content: bytes,
    *,
    source_filename: str,
    translation_name: str | None = None,
) -> dict[str, Any]:
    """Normalize a user-provided XML Bible into local-only JSON storage."""

    normalized_id = _normalize_translation_id(translation_id)
    catalog_entry = {
        "id": normalized_id,
        "name": translation_name or normalized_id.upper(),
        "language_code": "en",
        "language": "English",
        "license_status": "user_supplied",
        "validation": {},
    }
    result = install_xml_translation(
        normalized_id,
        xml_content,
        source_type="manual_xml_import",
        source_url=source_filename,
        source_repository=None,
        source_filename=source_filename,
        translation_name=translation_name,
        catalog_entry=catalog_entry,
    )
    return result


def parse_bible_xml(
    xml_content: bytes,
    *,
    translation_id: str,
    translation_name: str | None = None,
    source_filename: str = "",
) -> dict[str, Any]:
    """Parse common Bible XML shapes into BHF's local dataset format."""
    try:
        return translation_storage.parse_bible_xml(
            xml_content,
            translation_id=translation_id,
            translation_name=translation_name,
            source_filename=source_filename,
        )
    except translation_storage.TranslationStorageError as exc:
        raise BibleError(str(exc)) from exc


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
        except BibleError:
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


def _xml_local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1].lower()


def _xml_positive_int(value: Any) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return None
    number = int(match.group(0))
    return number if number > 0 else None


def _normalize_translation_id(translation_id: str) -> str:
    normalized = str(translation_id or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,31}", normalized):
        raise BibleError("translation id must be 2-32 lowercase letters, numbers, underscores, or hyphens")
    return normalized


def _build_bible_search_index_from_data(bible: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for book in bible.get("books", []):
        for chapter in book.get("chapters", []):
            for verse in chapter.get("verses", []):
                text = str(verse.get("text") or "").strip()
                entries.append(
                    {
                        "book": str(verse.get("book") or book.get("name") or ""),
                        "chapter": int(verse.get("chapter") or chapter.get("chapter") or 0),
                        "verse": int(verse.get("verse") or 0),
                        "text": text,
                        "normalized_text": _normalize_search_text(text),
                        "tokens": _tokenize_search_query(text),
                    }
                )
    return entries


@lru_cache(maxsize=16)
def build_bible_search_index(translation_id: str = "asv") -> list[dict[str, Any]]:
    """Build a flattened per-verse search index for one installed translation."""

    bible = load_translation_bible(translation_id)
    return _build_bible_search_index_from_data(bible)


def clear_bible_search_cache() -> None:
    build_bible_search_index.cache_clear()


def _normalize_dataset(data: dict[str, Any], bible_path: Path) -> dict[str, Any]:
    resultset = data.get("resultset")
    if not isinstance(resultset, dict) or not isinstance(resultset.get("row"), list):
        raise BibleError("Bible dataset must contain a books list")

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


def list_books(data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    bible = data or load_asv_bible()
    books = []
    for book in bible["books"]:
        chapters = book.get("chapters", [])
        books.append(
            {
                "name": book["name"],
                "order": book.get("order"),
                "chapters": len(chapters),
            }
        )
    return books


def normalize_book_name(name: str) -> str:
    normalized = _alias_key(name)
    if normalized in BOOK_ALIASES:
        return BOOK_ALIASES[normalized]
    raise BibleError(f"unknown Bible book: {name}")


def resolve_chapter(
    book: str,
    chapter: int | str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bible = data or load_asv_bible()
    canonical = normalize_book_name(book)
    chapter_number = _positive_int(chapter, "chapter")
    for book_data in bible["books"]:
        if book_data.get("name") != canonical:
            continue
        for chapter_data in book_data.get("chapters", []):
            if int(chapter_data.get("chapter", 0)) == chapter_number:
                return {
                    "translation": bible.get("translation", {}),
                    "book": canonical,
                    "chapter": chapter_number,
                    "verses": chapter_data.get("verses", []),
                }
        raise BibleError(f"{canonical} has no chapter {chapter_number}")
    raise BibleError(f"unknown Bible book: {book}")


def resolve_passage(
    book: str,
    chapter: int | str,
    start_verse: int | str | None = None,
    end_verse: int | str | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    chapter_data = resolve_chapter(book, chapter, data)
    verses = chapter_data["verses"]
    if start_verse is None:
        selected = verses
        start = int(verses[0]["verse"]) if verses else None
        end = int(verses[-1]["verse"]) if verses else None
    else:
        start = _positive_int(start_verse, "start_verse")
        end = _positive_int(end_verse, "end_verse") if end_verse else start
        if end < start:
            raise BibleError("end_verse must be greater than or equal to start_verse")
        selected = [
            verse
            for verse in verses
            if start <= int(verse.get("verse", 0)) <= end
        ]
        if (
            not selected
            or int(selected[0]["verse"]) != start
            or int(selected[-1]["verse"]) != end
        ):
            raise BibleError(
                f"{chapter_data['book']} {chapter_data['chapter']} has no verses {start}-{end}"
            )

    return {
        **chapter_data,
        "start_verse": start,
        "end_verse": end,
        "reference": verse_range_reference(
            chapter_data["book"],
            chapter_data["chapter"],
            start,
            end,
        ),
        "selected_verses": selected,
        "selected_text": passage_text(selected),
        "chapter_text": passage_text(verses),
    }


def verse_range_reference(
    book: str,
    chapter: int | str,
    start_verse: int | str | None = None,
    end_verse: int | str | None = None,
) -> str:
    canonical = normalize_book_name(book)
    chapter_number = _positive_int(chapter, "chapter")
    if start_verse is None:
        return f"{canonical} {chapter_number}"
    start = _positive_int(start_verse, "start_verse")
    end = _positive_int(end_verse, "end_verse") if end_verse else start
    suffix = str(start) if start == end else f"{start}-{end}"
    return f"{canonical} {chapter_number}:{suffix}"


def passage_text(verses: list[dict[str, Any]]) -> str:
    return " ".join(
        f"{int(verse['verse'])}. {str(verse.get('text', '')).strip()}"
        for verse in verses
        if verse.get("text")
    )


def build_selected_passage_context(
    book: str,
    chapter: int | str,
    start_verse: int | str | None = None,
    end_verse: int | str | None = None,
    selected_text: str | None = None,
    include_chapter_context: bool = True,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    passage = resolve_passage(book, chapter, start_verse, end_verse, data)
    chosen_text = " ".join((selected_text or "").split()) or passage["selected_text"]
    context = {
        "translation": passage["translation"],
        "book": passage["book"],
        "chapter": passage["chapter"],
        "start_verse": passage["start_verse"],
        "end_verse": passage["end_verse"],
        "reference": passage["reference"],
        "selected_text": chosen_text,
    }
    if include_chapter_context:
        context["chapter_context"] = passage["chapter_text"]
    return context


def compare_translation_passages(
    book: str,
    chapter: int | str,
    start_verse: int | str | None = None,
    end_verse: int | str | None = None,
    *,
    translations: list[tuple[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Compare the same passage across local translation datasets."""

    if translations is None:
        translation_sets = [("asv", load_asv_bible())]
        for installation in list_installed_translations():
            translation_id = str(installation.get("translation_id") or "").lower()
            if translation_id == "asv":
                continue
            try:
                translation_sets.append((translation_id, load_translation_bible(translation_id)))
            except BibleError:
                continue
    else:
        translation_sets = translations
    passages = []
    verse_rows: list[dict[str, Any]] = []
    reference: str | None = None
    first_context: dict[str, Any] | None = None
    for translation_id, bible in translation_sets:
        passage = resolve_passage(
            book,
            chapter,
            start_verse,
            end_verse,
            data=bible,
        )
        chapter_context = passage["chapter_text"]
        selected_text = passage["selected_text"]
        translation_meta = dict(bible.get("translation", {}))
        translation_meta.setdefault("id", translation_id.upper())
        passages.append(
            {
                "id": translation_meta.get("id", translation_id),
                "name": translation_meta.get("name", translation_id),
                "translation": translation_meta,
                "reference": passage["reference"],
                "selected_text": selected_text,
                "chapter_context": chapter_context,
            }
        )
        reference = passage["reference"]
        if first_context is None:
            first_context = passage
        if not verse_rows:
            verse_rows = [
                {
                    "verse": verse["verse"],
                    "book": verse["book"],
                    "chapter": verse["chapter"],
                    "texts": {str(translation_meta.get("id", translation_id)).upper(): verse["text"]},
                }
                for verse in passage["selected_verses"]
            ]
        else:
            for row, verse in zip(verse_rows, passage["selected_verses"], strict=True):
                row["texts"][str(translation_meta.get("id", translation_id)).upper()] = verse["text"]
    return {
        "book": normalize_book_name(book),
        "chapter": _positive_int(chapter, "chapter"),
        "start_verse": first_context["start_verse"] if first_context else None,
        "end_verse": first_context["end_verse"] if first_context else None,
        "reference": reference or verse_range_reference(book, chapter, start_verse, end_verse),
        "translations": passages,
        "verse_rows": verse_rows,
    }


def testament_for_book(book: str) -> str:
    canonical = normalize_book_name(book)
    return BOOKS[canonical][0]


def timeline_for_book(book: str) -> dict[str, str]:
    canonical = normalize_book_name(book)
    return _TIMELINE_GUIDES.get(canonical, _TIMELINE_GUIDES["Default"])


def geography_for_book(book: str) -> dict[str, str]:
    canonical = normalize_book_name(book)
    return _GEOGRAPHY_GUIDES.get(canonical, _GEOGRAPHY_GUIDES["Default"])


def search_bible_text(
    query: str,
    *,
    limit: int = 25,
    translation: str = "asv",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_query = _normalize_search_text(query)
    if not normalized_query:
        raise BibleError("search query is required")

    capped_limit = max(1, min(int(limit), 100))
    search_bible = data or load_translation_bible(translation)
    direct_reference = parse_reference_query(query)
    if direct_reference:
        passage = resolve_passage(
            direct_reference["book"],
            direct_reference["chapter"],
            direct_reference.get("verse_start"),
            direct_reference.get("verse_end"),
            data=search_bible,
        )
        return {
            "query": query,
            "normalized_query": normalized_query,
            "results": [_passage_to_search_result(passage, match_type="direct_reference", score=1000)],
            "total_results": 1,
            "direct_reference": True,
            "ai_fallback_eligible": False,
            "translation": str((passage.get("translation") or {}).get("id") or translation).upper(),
        }

    tokens = _tokenize_search_query(normalized_query)
    bible = search_bible
    index = _build_bible_search_index_from_data(bible)
    scored: list[dict[str, Any]] = []
    canonical_books = list(BOOKS)
    translation_meta = dict(bible.get("translation", {}))
    translation_label = str(translation_meta.get("id") or translation).upper()
    for entry in index:
        phrase_hit = normalized_query in str(entry["normalized_text"])
        entry_tokens = set(entry["tokens"])
        overlap = len([token for token in tokens if token in entry_tokens])
        if not phrase_hit and overlap == 0:
            continue
        score = 0
        match_type = "term"
        if phrase_hit:
            match_type = "phrase"
            score += 500 + min(len(normalized_query), 180)
        if overlap:
            score += overlap * 20
            score += int((overlap / max(len(tokens), 1)) * 100)
        if entry_tokens == set(tokens):
            score += 25
        scored.append(
            {
                "book": entry["book"],
                "chapter": entry["chapter"],
                "verse_start": entry["verse"],
                "verse_end": entry["verse"],
                "reference": verse_range_reference(entry["book"], entry["chapter"], entry["verse"], entry["verse"]),
                "excerpt": entry["text"],
                "match_type": match_type,
                "score": score,
            }
        )
    scored.sort(
        key=lambda item: (
            -int(item["score"]),
            canonical_books.index(str(item["book"])),
            int(item["chapter"]),
            int(item["verse_start"]),
        )
    )
    results = scored[:capped_limit]
    return {
        "query": query,
            "normalized_query": normalized_query,
            "results": results,
            "total_results": len(scored),
            "direct_reference": False,
            "ai_fallback_eligible": not results and is_topic_style_search_query(query),
            "no_results_message": f"No local {translation_label} matches were found." if not results else None,
            "translation": translation_label,
        }


def parse_reference_query(query: str) -> dict[str, Any] | None:
    normalized = " ".join(str(query or "").strip().split())
    if not normalized:
        return None
    match = _SEARCH_REFERENCE_RE.fullmatch(normalized)
    if not match:
        return None
    try:
        book = normalize_book_name(match.group("book"))
        chapter = _positive_int(match.group("chapter"), "chapter")
        verse_start = match.group("verse_start")
        verse_end = match.group("verse_end")
        result: dict[str, Any] = {"book": book, "chapter": chapter}
        if verse_start:
            result["verse_start"] = _positive_int(verse_start, "verse_start")
            result["verse_end"] = _positive_int(verse_end, "verse_end") if verse_end else result["verse_start"]
        return result
    except BibleError:
        return None


def is_topic_style_search_query(query: str) -> bool:
    normalized = " ".join(str(query or "").strip().split())
    lowered = normalized.lower()
    if not lowered:
        return False
    if parse_reference_query(normalized):
        return False
    if '"' in normalized or "'" in normalized:
        return False
    if lowered.endswith("?"):
        return True
    tokens = _tokenize_search_query(normalized)
    if not tokens:
        return False
    if any(token in _TOPIC_HINT_WORDS for token in tokens):
        return True
    if len(tokens) >= 3:
        return True
    if len(tokens) == 1 and tokens[0] in _TOPICAL_SINGLE_TERMS:
        return True
    return False


def _passage_to_search_result(
    passage: dict[str, Any],
    *,
    match_type: str,
    score: int,
) -> dict[str, Any]:
    return {
        "book": passage["book"],
        "chapter": passage["chapter"],
        "verse_start": passage.get("start_verse"),
        "verse_end": passage.get("end_verse"),
        "reference": passage["reference"],
        "excerpt": passage["selected_text"],
        "match_type": match_type,
        "score": score,
    }


def _alias_key(value: str) -> str:
    compact = re.sub(r"\s+", " ", value.strip().lower().replace(".", ""))
    return compact


def _normalize_search_text(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s:.-]", " ", str(value).lower()).split())


def _tokenize_search_query(value: str) -> list[str]:
    return [token for token in re.split(r"\W+", _normalize_search_text(value)) if token]


def _positive_int(value: int | str, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise BibleError(f"{label} must be a positive integer") from exc
    if number <= 0:
        raise BibleError(f"{label} must be a positive integer")
    return number
