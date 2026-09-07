"""Data-driven broad genre classification for biblical books."""

from __future__ import annotations

from .knowledge import lookup_book_context
from .models import GenreContext, ReferenceContext


GENRE_MAP: dict[str, GenreContext] = {
    "Genesis": GenreContext(
        "Torah",
        ["narrative"],
        "ancient Near Eastern context",
        ["genre.narrative", "context.ancient-near-east"],
        0.86,
    ),
    "Exodus": GenreContext(
        "Torah",
        ["narrative", "law", "covenant"],
        "covenant formation and ancient Near Eastern context",
        ["genre.narrative", "genre.law", "context.covenant"],
        0.86,
    ),
    "Leviticus": GenreContext(
        "Torah",
        ["law", "priestly instruction"],
        "priestly and covenant context",
        ["genre.law", "context.temple", "context.covenant"],
        0.88,
    ),
    "Numbers": GenreContext(
        "Torah",
        ["narrative", "law"],
        "wilderness generation and covenant context",
        ["genre.narrative", "genre.law", "context.covenant"],
        0.82,
    ),
    "Deuteronomy": GenreContext(
        "Torah",
        ["law", "covenant sermon"],
        "covenant renewal context",
        ["genre.law", "context.covenant"],
        0.86,
    ),
    "Psalms": GenreContext(
        "poetry",
        ["worship", "lament", "royal theology"],
        "Israel's worship and prayer traditions",
        ["genre.poetry"],
        0.88,
    ),
    "Proverbs": GenreContext(
        "wisdom literature",
        ["poetry", "instruction"],
        "wisdom tradition and observed patterns of life",
        ["genre.wisdom", "context.wisdom-tradition"],
        0.9,
    ),
    "Ecclesiastes": GenreContext(
        "wisdom literature",
        ["reflection", "poetry"],
        "wisdom tradition and philosophical reflection",
        ["genre.wisdom", "context.wisdom-tradition"],
        0.84,
    ),
    "Job": GenreContext(
        "wisdom literature",
        ["poetry", "dialogue"],
        "wisdom tradition and suffering discourse",
        ["genre.wisdom", "genre.poetry"],
        0.84,
    ),
    "Isaiah": GenreContext(
        "prophecy",
        ["poetry", "judgment", "hope"],
        "prophetic address in Israel/Judah's historical setting",
        ["genre.prophecy"],
        0.84,
    ),
    "Jeremiah": GenreContext(
        "prophecy",
        ["poetry", "judgment", "covenant"],
        "late monarchy and exile context",
        ["genre.prophecy", "context.exile-and-restoration"],
        0.84,
    ),
    "Ezekiel": GenreContext(
        "prophecy",
        ["visionary literature", "symbolic action"],
        "exilic prophetic context",
        ["genre.prophecy", "context.exile-and-restoration"],
        0.82,
    ),
    "Daniel": GenreContext(
        "apocalyptic",
        ["narrative", "court tale", "prophecy"],
        "exile and imperial court context",
        ["genre.apocalyptic", "genre.narrative"],
        0.78,
    ),
    "Matthew": GenreContext(
        "Gospel",
        ["ancient biography", "narrative"],
        "Second Temple Jewish context",
        ["genre.gospel", "context.second-temple-judaism"],
        0.88,
    ),
    "Mark": GenreContext(
        "Gospel",
        ["ancient biography", "narrative"],
        "Second Temple Jewish and Roman imperial context",
        ["genre.gospel", "context.second-temple-judaism"],
        0.88,
    ),
    "Luke": GenreContext(
        "Gospel",
        ["ancient biography", "narrative"],
        "Second Temple Jewish and Greco-Roman context",
        ["genre.gospel", "context.second-temple-judaism"],
        0.88,
    ),
    "John": GenreContext(
        "Gospel",
        ["ancient biography", "theological narrative"],
        "Second Temple Jewish context",
        ["genre.gospel", "context.second-temple-judaism"],
        0.88,
    ),
    "Acts": GenreContext(
        "narrative",
        ["early church history"],
        "first-century church and Greco-Roman context",
        ["genre.narrative", "context.greco-roman-world"],
        0.78,
    ),
    "Romans": GenreContext(
        "epistle",
        ["theological argument", "occasional letter"],
        "first-century church and Roman context",
        ["genre.epistle", "context.roman-empire"],
        0.86,
    ),
    "Revelation": GenreContext(
        "apocalyptic",
        ["prophecy", "letter"],
        "late first-century churches under imperial pressure",
        ["genre.apocalyptic", "genre.prophecy", "context.roman-empire"],
        0.86,
    ),
}

# Complete canonical coverage is kept separately from the richer guidance
# entries above.  This prevents an omitted book name (notably Song of Songs)
# from falling through to a low-confidence or narrative default.
CANONICAL_BOOK_GENRE_BUCKETS: dict[str, str] = {
    **{book: "Torah" for book in {"Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"}},
    **{
        book: "narrative"
        for book in {
            "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
            "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Acts",
        }
    },
    **{book: "wisdom literature" for book in {"Job", "Proverbs", "Ecclesiastes"}},
    **{book: "poetry" for book in {"Psalms", "Song of Songs", "Lamentations"}},
    **{
        book: "prophecy"
        for book in {
            "Isaiah", "Jeremiah", "Ezekiel", "Hosea", "Joel", "Amos", "Obadiah",
            "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
            "Zechariah", "Malachi",
        }
    },
    **{book: "apocalyptic" for book in {"Daniel", "Revelation"}},
    **{book: "Gospel" for book in {"Matthew", "Mark", "Luke", "John"}},
    **{
        book: "epistle"
        for book in {
            "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
            "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
            "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
            "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude",
        }
    },
}

NARRATIVE_BOOKS = {
    "Joshua",
    "Judges",
    "Ruth",
    "1 Samuel",
    "2 Samuel",
    "1 Kings",
    "2 Kings",
    "1 Chronicles",
    "2 Chronicles",
    "Ezra",
    "Nehemiah",
    "Esther",
}

PROPHETIC_BOOKS = {
    "Hosea",
    "Joel",
    "Amos",
    "Obadiah",
    "Jonah",
    "Micah",
    "Nahum",
    "Habakkuk",
    "Zephaniah",
    "Haggai",
    "Zechariah",
    "Malachi",
}

EPISTLE_BOOKS = {
    "1 Corinthians",
    "2 Corinthians",
    "Galatians",
    "Ephesians",
    "Philippians",
    "Colossians",
    "1 Thessalonians",
    "2 Thessalonians",
    "1 Timothy",
    "2 Timothy",
    "Titus",
    "Philemon",
    "Hebrews",
    "James",
    "1 Peter",
    "2 Peter",
    "1 John",
    "2 John",
    "3 John",
    "Jude",
}


def classify_genre(reference: ReferenceContext) -> GenreContext:
    if not reference.book:
        return GenreContext(
            primary_genre=None,
            secondary_genres=[],
            historical_context_hint="Topic-only question; identify relevant texts before applying genre rules.",
            recommended_modules=["core.genre-awareness"],
            confidence=0.35,
        )
    if reference.book in GENRE_MAP:
        genre = GENRE_MAP[reference.book]
        book_context = lookup_book_context(reference)
        if book_context:
            return GenreContext(
                primary_genre=genre.primary_genre,
                secondary_genres=list(genre.secondary_genres),
                historical_context_hint=book_context.historical_context_hint,
                recommended_modules=list(genre.recommended_modules),
                confidence=genre.confidence,
            )
        return genre
    if reference.book in CANONICAL_BOOK_GENRE_BUCKETS:
        primary = CANONICAL_BOOK_GENRE_BUCKETS[reference.book]
        return GenreContext(
            primary_genre=primary,
            secondary_genres=[],
            historical_context_hint=f"{primary} literary and historical context",
            recommended_modules=[f"genre.{primary.casefold().replace(' ', '-')}"],
            confidence=0.8,
        )
    if reference.book in NARRATIVE_BOOKS:
        return GenreContext(
            "narrative",
            ["historical narrative"],
            "Israel's historical and covenant context",
            ["genre.narrative"],
            0.72,
        )
    if reference.book in PROPHETIC_BOOKS:
        return GenreContext(
            "prophecy",
            ["oracle", "poetry"],
            "prophetic address to a concrete historical situation",
            ["genre.prophecy"],
            0.72,
        )
    if reference.book in EPISTLE_BOOKS:
        return GenreContext(
            "epistle",
            ["occasional letter"],
            "first-century church context",
            ["genre.epistle"],
            0.76,
        )
    return GenreContext(
        primary_genre=None,
        historical_context_hint="Book recognized, but genre mapping is uncertain.",
        recommended_modules=["core.genre-awareness"],
        confidence=0.25,
    )
