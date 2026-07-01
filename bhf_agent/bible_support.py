"""Shared Bible lookup tables and parsing helpers."""

from __future__ import annotations

import re

from .references import BOOK_ALIASES


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

_SEARCH_REFERENCE_RE = re.compile(
    rf"(?P<book>{'|'.join(re.escape(name) for name in sorted(BOOK_ALIASES, key=len, reverse=True))})\.?\s+"
    r"(?P<chapter>\d{1,3})"
    r"(?:\s*:\s*(?P<verse_start>\d{1,3})(?:\s*-\s*(?P<verse_end>\d{1,3}))?)?$",
    re.IGNORECASE,
)

_TOPIC_HINT_WORDS = {
    "about",
    "where",
    "verses",
    "passages",
    "mentions",
    "mentioned",
    "topic",
    "themes",
    "theme",
    "regarding",
    "concerning",
    "what",
    "who",
    "why",
    "how",
}

_TOPICAL_SINGLE_TERMS = {
    "forgiveness",
    "mercy",
    "grace",
    "faith",
    "hope",
    "love",
    "sin",
    "salvation",
    "egypt",
    "exodus",
    "covenant",
    "temple",
    "kingdom",
    "wisdom",
    "babylon",
    "jerusalem",
}
