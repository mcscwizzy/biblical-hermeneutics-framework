"""Local ASV Bible dataset helpers."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .references import BOOK_ALIASES, BOOKS


DATA_PATH = Path(__file__).resolve().parent / "data" / "asv_bible.json"
KJV_DATA_PATH = Path(__file__).resolve().parent / "data" / "kjv_bible.json"


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


def load_kjv_bible(path: str | Path = KJV_DATA_PATH) -> dict[str, Any]:
    """Load the committed KJV dataset."""

    return load_bible_dataset(path)


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

    translation_sets = translations or [
        ("ASV", load_asv_bible()),
        ("KJV", load_kjv_bible()),
    ]
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
        translation_meta.setdefault("id", translation_id)
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
                    "texts": {translation_id: verse["text"]},
                }
                for verse in passage["selected_verses"]
            ]
        else:
            for row, verse in zip(verse_rows, passage["selected_verses"], strict=True):
                row["texts"][translation_id] = verse["text"]
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


def _alias_key(value: str) -> str:
    compact = re.sub(r"\s+", " ", value.strip().lower().replace(".", ""))
    return compact


def _positive_int(value: int | str, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise BibleError(f"{label} must be a positive integer") from exc
    if number <= 0:
        raise BibleError(f"{label} must be a positive integer")
    return number


_TIMELINE_GUIDES: dict[str, dict[str, str]] = {
    "Default": {
        "period": "Biblical timeline",
        "notes": "Use the book's canonical setting and surrounding passages to describe a broad historical placement. Avoid fake precision.",
    },
    "Genesis": {
        "period": "Primeval and patriarchal setting",
        "notes": "Place the passage in the early biblical story of creation, fall, flood, and the patriarchs; dates are not fixed here.",
    },
    "Exodus": {
        "period": "Moses and the exodus / wilderness era",
        "notes": "Connect the passage to Israel's deliverance, covenant making, and wilderness formation without forcing a specific calendar date.",
    },
    "Leviticus": {
        "period": "Sinai covenant and tabernacle instruction",
        "notes": "Place the passage within Israel's wilderness covenant life and priestly ordering.",
    },
    "Numbers": {
        "period": "Wilderness journey toward the land",
        "notes": "Show how the passage fits Israel's movement from Sinai toward the promised land.",
    },
    "Deuteronomy": {
        "period": "Moab / covenant renewal",
        "notes": "Place the passage near the end of Moses' ministry as covenant renewal before entry into the land.",
    },
    "Joshua": {
        "period": "Conquest and land settlement",
        "notes": "Connect the passage to Israel's entrance into the land and the transfer from wilderness to settlement.",
    },
    "Judges": {
        "period": "Tribal settlement and recurring covenant failure",
        "notes": "Describe the period as a fractured pre-monarchic era marked by repeated cycles of deliverance and apostasy.",
    },
    "Ruth": {
        "period": "Judges-era family story",
        "notes": "Place the passage within the period of the judges, but focus on its literary role in the Davidic line.",
    },
    "1 Samuel": {
        "period": "Transition to monarchy",
        "notes": "Connect the passage to Israel's move from judges to kingship and the rise of Samuel, Saul, and David.",
    },
    "2 Samuel": {
        "period": "Davidic monarchy",
        "notes": "Place the passage in the establishment and testing of David's rule.",
    },
    "1 Kings": {
        "period": "Solomon and divided kingdom beginnings",
        "notes": "Connect the passage to the temple, royal administration, and the kingdom's fracture.",
    },
    "2 Kings": {
        "period": "Divided kingdom to exile",
        "notes": "Place the passage in the decline of Israel and Judah leading to exile.",
    },
    "Psalms": {
        "period": "Israel's worship across the monarchy and exile",
        "notes": "Treat many psalms as worship texts used across multiple settings rather than fixing one date unless the superscription is explicit.",
    },
    "Isaiah": {
        "period": "8th-century prophecy with later exile and restoration horizons",
        "notes": "Avoid claiming a single narrow date for every section; the book spans judgment and hope across a broad historical arc.",
    },
    "Jeremiah": {
        "period": "Late Judah and the Babylonian crisis",
        "notes": "Place the passage in the years leading to and including Jerusalem's fall and exile.",
    },
    "Ezekiel": {
        "period": "Exilic prophecy",
        "notes": "Place the passage in the Babylonian exile and its theological aftermath.",
    },
    "Daniel": {
        "period": "Exile / court setting with apocalyptic horizon",
        "notes": "Keep historical setting broad and distinguish narrative court scenes from apocalyptic visions.",
    },
    "Hosea": {
        "period": "Northern kingdom crisis",
        "notes": "Connect the passage to covenant unfaithfulness before the Assyrian collapse.",
    },
    "Amos": {
        "period": "Prosperity before judgment",
        "notes": "Place the passage in the period of social injustice and impending judgment in the northern kingdom.",
    },
    "Matthew": {
        "period": "Gospel period: Jesus' ministry",
        "notes": "Place the passage in the life, teaching, death, and resurrection of Jesus in the first-century Jewish world.",
    },
    "Mark": {
        "period": "Gospel period: Jesus' ministry",
        "notes": "Keep the focus on the movement of Jesus' ministry and suffering.",
    },
    "Luke": {
        "period": "Gospel period and the road to Acts",
        "notes": "Place the passage in the life of Jesus and its bridge into the early church.",
    },
    "John": {
        "period": "Gospel period: Jesus revealed as the Word",
        "notes": "Place the passage in the ministry of Jesus and the theological witness of the Fourth Gospel.",
    },
    "Acts": {
        "period": "Early church and apostolic mission",
        "notes": "Place the passage in the spread of the gospel after Jesus' resurrection and ascension.",
    },
    "Romans": {
        "period": "Pauline letter to the Roman church",
        "notes": "Place the passage within Paul's missionary-era correspondence to believers in Rome.",
    },
    "1 Corinthians": {
        "period": "Pauline correspondence to Corinth",
        "notes": "Place the passage in Paul's pastoral correction of a divided first-century church.",
    },
    "Revelation": {
        "period": "Late first-century apocalyptic witness",
        "notes": "Use broad first-century context and canonical imagery; avoid overconfident dating of individual visions.",
    },
}

_GEOGRAPHY_GUIDES: dict[str, dict[str, str]] = {
    "Default": {
        "region": "Biblical geography helper",
        "notes": "Mention places explicitly named in the passage and keep uncertain locations marked as uncertain.",
    },
    "Genesis": {
        "region": "Primeval and patriarchal geography",
        "notes": "Treat early Genesis locations as literary-geographic settings where some identifications are debated.",
    },
    "Exodus": {
        "region": "Egypt, the wilderness, and Sinai",
        "notes": "Focus on the movement from Egypt through the wilderness toward the land, and note when route details are debated.",
    },
    "Numbers": {
        "region": "Wilderness camp and travel routes",
        "notes": "Track encampments, travel stations, and boundary movements without pretending every site is certain.",
    },
    "Deuteronomy": {
        "region": "Transjordan and Moab",
        "notes": "Place the passage near the plains of Moab and the approach to the Jordan when the context supports it.",
    },
    "Joshua": {
        "region": "Jordan crossing and the land of Canaan",
        "notes": "Identify cities, tribal allotments, and campaign locations, but note debated identifications where needed.",
    },
    "Judges": {
        "region": "Tribal territory across hill country, lowland, and border zones",
        "notes": "Describe the geography of unstable settlement, local strongholds, and contested control.",
    },
    "1 Samuel": {
        "region": "Benjamin, Ephraim, and the transition into royal centers",
        "notes": "Use the geography of Saul, Samuel, and David's movement between local and royal spaces.",
    },
    "2 Samuel": {
        "region": "Judah, Jerusalem, and surrounding battle zones",
        "notes": "Keep the focus on Davidic centers, court movement, and battlefield geography.",
    },
    "Psalms": {
        "region": "Temple, Zion, and the wider land of Israel",
        "notes": "When a psalm names places, connect them to worship, pilgrimage, kingship, or distress.",
    },
    "Isaiah": {
        "region": "Judah, Jerusalem, and the nations",
        "notes": "Track the geography of Judah, Zion, Assyria, Babylon, and the wider nations as the book demands.",
    },
    "Jeremiah": {
        "region": "Jerusalem, Judah, and exile pathways",
        "notes": "Connect the passage to city, land, and exile geography without inventing precision for every move.",
    },
    "Ezekiel": {
        "region": "Jerusalem, Babylon, and visionary temple geography",
        "notes": "Distinguish between real-world locations and visionary geography in the book.",
    },
    "Daniel": {
        "region": "Babylonian and Persian imperial centers",
        "notes": "Place the narrative in court settings and imperial geography while keeping prophetic visions distinct.",
    },
    "Matthew": {
        "region": "Galilee, Judea, Jerusalem, and the road to the cross",
        "notes": "Tie locations to Jesus' ministry and movement through familiar first-century Jewish settings.",
    },
    "Mark": {
        "region": "Galilee, the road, and Jerusalem",
        "notes": "Mark's geography often tracks movement; identify the setting and its narrative role.",
    },
    "Luke": {
        "region": "Galilee, Judea, Jerusalem, and the spread outward",
        "notes": "Trace movement from local ministry to Jerusalem and then outward into Acts.",
    },
    "John": {
        "region": "Judea, Galilee, Jerusalem, and symbolic movement",
        "notes": "Note the Gospel's concrete locations and how they serve theological storytelling.",
    },
    "Acts": {
        "region": "Jerusalem, Samaria, Syria, Asia Minor, Greece, and Rome",
        "notes": "Follow the mission outward, noting cities and travel routes as the narrative unfolds.",
    },
    "Romans": {
        "region": "Rome and the wider Mediterranean world",
        "notes": "Keep the Roman setting in view, but do not force local geography into every argument.",
    },
    "Revelation": {
        "region": "Asia Minor churches and symbolic geography",
        "notes": "Distinguish the seven churches and other real locations from the book's symbolic geography.",
    },
}
