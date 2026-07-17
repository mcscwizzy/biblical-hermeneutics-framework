#!/usr/bin/env python3
"""Generate deterministic CKL placeholder objects and manifest.

The generator is intentionally conservative:
- it never overwrites existing populated content unless ``--force`` is passed,
- it validates duplicate ids and filename mismatches,
- it writes stable, formatted JSON,
- and it can be rerun safely.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Iterable
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bhf_agent.references import BOOKS
from framework.canonical_library import (
    CATEGORY_FOLDERS,
    CanonicalLibrary,
    CanonicalObject,
    CanonicalValidationError,
    normalize_alias,
    normalize_id,
)


ROOT = REPO_ROOT
PACKAGE_ROOT = ROOT / "framework" / "canonical_library"
OBJECTS_ROOT = PACKAGE_ROOT / "objects"
MANIFEST_PATH = PACKAGE_ROOT / "manifest.json"
OPENBIBLE_PLACES_PATH = ROOT / "bhf_agent" / "data" / "openbible_places.json"
ARCHAEOLOGY_SOURCE_PATHS = [
    ROOT / "bhf_web" / "static" / "data" / "archaeology" / "artifacts.json",
    ROOT / "bhf_web" / "static" / "data" / "archaeology" / "archaeologySites.json",
    ROOT / "bhf_web" / "static" / "data" / "archaeology" / "museums.json",
    ROOT / "bhf_web" / "static" / "data" / "archaeology" / "excavationReports.json",
]

TARGET_COUNTS = {
    "theology": 50,
    "theme": 50,
    "person": 100,
    "place": 75,
    "event": 75,
    "book": 66,
    "word_study": 50,
    "archaeology": 50,
    "institution": 34,
    "prophecy": 10,
    "faq": 50,
}


THEOLOGY_TITLES = [
    "Trinity",
    "Atonement",
    "Justification",
    "Sanctification",
    "Incarnation",
    "Election",
    "Covenant Theology",
    "New Covenant",
    "Kingdom Theology",
    "Christology",
    "Pneumatology",
    "Ecclesiology",
    "Eschatology",
    "Hamartiology",
    "Bibliology",
    "Providence",
    "Imago Dei",
    "Union with Christ",
    "Adoption",
    "Glorification",
    "Perseverance",
    "Grace",
    "Faith",
    "Repentance",
    "Mission",
    "Creation Doctrine",
    "Divine Holiness",
    "Divine Mercy",
    "Divine Justice",
    "Divine Wrath",
    "Resurrection Doctrine",
    "Judgment",
    "Covenant Faithfulness",
    "Divine Presence",
    "Messianic Hope",
    "Remnant",
    "Law and Gospel",
    "Priesthood of Believers",
    "Typology",
    "Sacramental Theology",
    "Spiritual Gifts",
    "Second Coming",
    "Final Judgment",
    "Inspiration",
    "Inerrancy",
    "Theology of Prayer",
    "Theology of Worship",
    "Theology of Suffering",
    "Theology of the Kingdom",
    "Theology of the Cross",
    "Theology of the Spirit",
    "Theology of the Word",
]

THEME_TITLES = [
    "Covenant Theme",
    "Exile Theme",
    "Temple Theme",
    "Holiness Theme",
    "Sacrifice Theme",
    "Resurrection Theme",
    "Creation Theme",
    "New Creation Theme",
    "Faithfulness Theme",
    "Mercy Theme",
    "Justice Theme",
    "Blessing and Curse Theme",
    "Remnant Theme",
    "Kingdom Theme",
    "Presence Theme",
    "Wisdom Theme",
    "Spirit Theme",
    "Promise Theme",
    "Redemption Theme",
    "Sabbath Theme",
    "Glory Theme",
    "Seed Theme",
    "Land Theme",
    "Shepherd Theme",
    "Water Theme",
    "Fire Theme",
    "Mountain Theme",
    "Wedding Theme",
    "Sonship Theme",
    "Adoption Theme",
    "Prayer Theme",
    "Worship Theme",
    "Righteousness Theme",
    "Peace Theme",
    "Hope Theme",
    "Restoration Theme",
    "Exodus Pattern Theme",
    "Messiah Theme",
    "New Covenant Theme",
    "New Exodus Theme",
    "New Temple Theme",
    "New Jerusalem Theme",
    "People of God Theme",
    "Image of God Theme",
    "Word of God Theme",
    "Light and Darkness Theme",
    "Water and Spirit Theme",
    "Witness Theme",
    "Sanctuary Theme",
    "Priestly Mediation Theme",
    "Life and Death Theme",
    "Day of the Lord Theme",
]

PEOPLE_TITLES = [
    "Adam",
    "Eve",
    "Abel",
    "Cain",
    "Noah",
    "Abraham",
    "Sarah",
    "Isaac",
    "Rebekah",
    "Jacob",
    "Joseph",
    "Moses",
    "Aaron",
    "Miriam",
    "Joshua son of Nun",
    "Caleb",
    "Rahab",
    "Deborah",
    "Gideon",
    "Samson",
    "David",
    "Solomon",
    "Elijah",
    "Elisha",
    "Esther the Queen",
    "Mordecai",
    "Ezra the Scribe",
    "Nehemiah the Governor",
    "Hannah",
    "Samuel the Prophet",
    "Saul",
    "Nathan the Prophet",
    "Bathsheba",
    "Ruth the Moabite",
    "Boaz",
    "Jethro",
    "Balaam",
    "Korah",
    "Phinehas",
    "Job the Sufferer",
    "Jonah the Prophet",
    "Isaiah the Prophet",
    "Jeremiah the Prophet",
    "Ezekiel the Prophet",
    "Daniel the Exile",
    "Zechariah the Priest",
    "Zechariah the Prophet",
    "John the Baptist",
    "Mary, Mother of Jesus",
    "Joseph, Husband of Mary",
    "Mary Magdalene",
    "Peter",
    "Paul",
    "Barnabas",
    "Silas",
    "Timothy",
    "Titus the Companion",
    "Priscilla",
    "Aquila",
    "Lydia",
    "Stephen",
    "Philip the Evangelist",
    "Apollos",
    "Mark the Evangelist",
    "Luke the Physician",
    "James, Brother of Jesus",
    "Jude of Jerusalem",
    "Nicodemus",
    "Martha",
    "Lazarus",
    "Caiaphas",
    "Pontius Pilate",
    "Herod the Great",
    "Cornelius",
    "Onesimus",
    "Philemon of Colossae",
    "Phoebe",
    "Dorcas",
    "Simeon the Just",
    "Anna the Prophetess",
    "Elizabeth",
    "Zechariah, Father of John",
    "Andrew",
    "James son of Zebedee",
    "John son of Zebedee",
    "Philip the Apostle",
    "Bartholomew",
    "Thomas",
    "Matthew the Tax Collector",
    "James son of Alphaeus",
    "Thaddaeus",
    "Simon the Zealot",
    "Judas Iscariot",
    "Matthias",
    "Tabitha",
    "Tychicus",
    "Epaphroditus",
    "Phoebe of Cenchreae",
    "Eunice",
    "Lois",
    "Junia",
    "Tertius",
    "Gaius",
    "Demetrius",
    "Trophimus",
    "Epaphras",
    "Demas",
    "Erastus",
    "Aphia",
    "Artemas",
    "Zenas",
    "Nympha",
    "Rufus",
    "Elymas",
    "Agabus",
    "Mnason",
    "Jason",
    "Aeneas",
]

EVENT_TITLES = [
    "Creation",
    "The Fall",
    "The Flood",
    "Babel",
    "Call of Abraham",
    "Binding of Isaac",
    "Joseph Sold into Egypt",
    "Moses' Birth",
    "Burning Bush",
    "Plagues of Egypt",
    "Passover",
    "The Exodus",
    "Red Sea Crossing",
    "Sinai Covenant",
    "Golden Calf",
    "Wilderness Wandering",
    "Conquest of Jericho",
    "Judges Cycle",
    "Hannah's Prayer",
    "Rise of Saul",
    "David Anointed",
    "David and Goliath",
    "Ark Brought to Jerusalem",
    "Davidic Covenant",
    "Solomon Builds the Temple",
    "Division of the Kingdom",
    "Elijah on Mount Carmel",
    "Fall of Samaria",
    "Assyrian Exile of Israel",
    "Hezekiah's Reforms",
    "Fall of Jerusalem",
    "Babylonian Exile",
    "Return from Exile",
    "Rebuilding the Temple",
    "Rebuilding the Walls",
    "Birth of Jesus",
    "Baptism of Jesus",
    "Temptation of Jesus",
    "Sermon on the Mount",
    "Transfiguration",
    "Triumphal Entry",
    "Crucifixion",
    "Burial of Jesus",
    "Resurrection",
    "Ascension",
    "Pentecost",
    "Conversion of Paul",
    "Council of Jerusalem",
    "First Missionary Journey",
    "Second Missionary Journey",
    "Third Missionary Journey",
    "Paul in Prison",
    "Writing of Revelation",
    "Letters to the Seven Churches",
    "Fall of Babylon",
    "New Jerusalem",
    "Great White Throne Judgment",
    "Marriage Supper of the Lamb",
    "Feeding of the Five Thousand",
    "Institution of the Lord's Supper",
    "Peter's Denial",
    "Paul before Agrippa",
]

INSTITUTION_TITLES = [
    "Temple",
    "Tabernacle",
    "Synagogue",
    "Sanhedrin",
    "Priesthood",
    "Kingship",
    "Prophets",
    "Elders",
    "Household",
    "Roman Governorship",
    "Pharisees",
    "Sadducees",
    "Scribes",
    "High Priesthood",
    "Levites",
    "Baptism",
    "Lord's Supper",
    "Diaconate",
    "Apostleship",
    "Patronage",
    "Priestly Service",
    "Levitical Service",
    "Covenant Assembly",
    "Temple Tax",
    "Feast Calendar",
    "Roman Army",
    "Roman Citizenship",
    "Herodian Court",
    "Village Elders",
    "Second Temple Administration",
    "Household Codes",
    "Synagogue Leadership",
    "Sacrificial System",
    "Public Reading of Scripture",
    "Covenant Sign",
    "Priestly Blessing",
    "Temple Treasury",
    "Passover Meal",
    "Festival Pilgrimage",
]

WORD_STUDY_TITLES = [
    "hesed",
    "shalom",
    "ruach",
    "nephesh",
    "torah",
    "berit",
    "emet",
    "tsedeq",
    "mishpat",
    "qadosh",
    "dabar",
    "shema",
    "yahweh",
    "elohim",
    "adonai",
    "abba",
    "agape",
    "logos",
    "pneuma",
    "ekklesia",
    "charis",
    "pistis",
    "soteria",
    "metanoia",
    "parakletos",
    "koinonia",
    "sarx",
    "kyrios",
    "christos",
    "basileia",
    "diatheke",
    "eleos",
    "doxa",
    "hamartia",
    "anastasis",
    "parousia",
    "agios",
    "apostolos",
    "diakonia",
    "martyria",
    "sophia",
    "phos",
    "skotia",
    "katabole",
    "nomos",
    "teleios",
    "makarios",
    "hupomone",
    "theos",
    "mashiach",
    "pascha",
    "hosanna",
    "hallelujah",
    "amen",
    "qahal",
    "manna",
    "pascha",
    "hosanna",
    "shekinah",
    "sabbaton",
    "mashiach",
    "sophos",
    "kerygma",
    "hemera",
    "doulos",
    "poiema",
]

PROPHECY_TITLES = [
    "Messianic Prophecy",
    "Suffering Servant Prophecy",
    "Day of the Lord Prophecy",
    "New Covenant Prophecy",
    "Restoration Prophecy",
    "Remnant Prophecy",
    "Branch Prophecy",
    "Immanuel Prophecy",
    "New Jerusalem Prophecy",
    "Judgment Against the Nations",
]

FAQ_TITLES = [
    "What is Covenant?",
    "What is the Temple?",
    "Why is Exile Important?",
    "Who was Abraham?",
    "Who was Moses?",
    "Who was David?",
    "Who was Paul?",
    "Who was Peter?",
    "What is the Kingdom of God?",
    "What is Holiness?",
    "What is Sacrifice in the Bible?",
    "What is Resurrection?",
    "What is the Holy Spirit?",
    "What is Justification?",
    "What is the New Covenant?",
    "What is the Tabernacle?",
    "What is the Synagogue?",
    "What is the Messiah?",
    "What does hesed mean?",
    "What does shalom mean?",
    "What does ruach mean?",
    "What does Torah mean?",
    "Why are Genealogies Included?",
    "Why does the Bible repeat themes?",
    "How should I read prophecy?",
    "How should I read apocalyptic literature?",
    "What is the significance of Jerusalem?",
    "What is the significance of the Resurrection?",
    "How do the Old and New Testaments connect?",
    "What is the Day of the Lord?",
    "What is the Image of God?",
    "What is the role of priests?",
    "What is a covenant sign?",
    "What is the significance of Passover?",
    "What is the significance of the Sabbath?",
    "What is biblical wisdom?",
    "What is a parable?",
    "What is a psalm?",
    "What is a prophet?",
    "What is the Kingdom of Israel?",
    "What is the Kingdom of Judah?",
    "What is the Second Temple?",
    "What is the Roman Empire in the Bible?",
    "What is the Ancient Near East?",
    "What is typology?",
    "What is intertextuality?",
    "What is canonical theology?",
    "What is the significance of the Temple?",
    "What is the significance of the Exile?",
    "What is the significance of the Holy Spirit?",
    "What is the significance of the New Jerusalem?",
    "Why does the Bible mention archaeology?",
]

ARCHAEOLOGY_TITLES = [
    "Dead Sea Scrolls",
    "Tel Dan Stele",
    "Merneptah Stele",
    "Siloam Inscription",
    "Pilate Stone",
    "Cyrus Cylinder",
    "Lachish Reliefs",
    "Ketef Hinnom Silver Scrolls",
    "Mesha Stele",
    "Black Obelisk",
    "Arad Ostraca",
    "Lachish Ostraca",
    "Samaria Ostraca",
    "Hezekiah's Tunnel Inscription Context",
    "Pool of Siloam Discovery",
    "Pool of Bethesda Excavation",
    "Qumran Archaeological Site",
    "City of David Excavations",
    "Caesarea Maritima Excavations",
    "Masada Excavations",
    "Herodium Excavations",
    "Mount Ebal Altar Discovery",
    "Balaam Inscription",
    "Taylor Prism",
    "Sennacherib Prism",
    "Kurkh Monolith",
    "Nimrud Reliefs",
    "Elephantine Papyri",
    "Babylonian Chronicles",
    "Moabite Stone",
    "Gibeon Wine Jars",
    "Temple Warning Inscription",
    "Caiaphas Ossuary",
    "James Ossuary",
    "Wadi Murabba'at Scrolls",
    "Ein Gedi Scroll",
    "Tell Dan Excavations",
    "Lachish City Gate",
    "Hazor Excavations",
    "Megiddo Excavations",
    "Gezer Excavations",
    "Shiloh Excavations",
    "Beth Shean Excavations",
    "Tell es-Safi Excavations",
    "Qumran Caves",
    "Pilgrimage Road in Jerusalem",
    "Temple Mount Area Finds",
    "Bronze Snake",
    "Samaria Palace",
    "Tel Rehov Honey Workshop",
    "Tel Motza Temple",
    "Lachish Letters",
    "Jericho Excavations",
    "Ebla Tablets",
    "Ugarit Tablets",
    "Mari Archives",
    "Amarna Letters",
    "Larsa Tablets",
]


def unique_normalized(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = normalize_alias(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(value)
    return output


def question_topic(title: str) -> str:
    normalized = normalize_alias(title)
    prefixes = (
        "what is the ",
        "what is ",
        "who was ",
        "who is ",
        "why is the ",
        "why is ",
        "why does the ",
        "why does ",
        "how should i ",
        "how should we ",
        "how should ",
        "how do i ",
        "how do we ",
        "how do ",
        "what does the ",
        "what does ",
        "why are the ",
        "why are ",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    normalized = normalized.rstrip("?").strip()
    return normalized


def stripped_base(title: str, suffix: str) -> str:
    normalized = normalize_alias(title)
    if normalized.endswith(suffix):
        return normalized[: -len(suffix)].strip()
    return normalized


def build_aliases(category: str, title: str, extra_aliases: Iterable[str] = ()) -> list[str]:
    base = normalize_alias(title)
    aliases: list[str]

    if category == "book":
        aliases = [f"book of {base}", f"what is {base} about", f"tell me about {base}"]
        if base and base[0].isdigit():
            parts = base.split(" ", 1)
            if len(parts) == 2:
                ordinal = {"1": "first", "2": "second", "3": "third"}.get(parts[0])
                if ordinal:
                    aliases.append(f"{ordinal} {parts[1]}")
        if title == "Song of Songs":
            aliases.append("song of solomon")
    elif category == "person":
        aliases = [f"who is {base}", f"tell me about {base}", f"why is {base} important"]
    elif category == "place":
        aliases = [f"where is {base}", f"tell me about {base}", f"why is {base} important"]
    elif category == "event":
        aliases = [f"what happened in {base}", f"tell me about {base}", f"why is {base} important"]
    elif category == "theme":
        base = stripped_base(title, "theme")
        aliases = [f"{base} theme", f"{base} motif", f"{base} pattern", f"{base} thematic thread"]
    elif category == "theology":
        base = stripped_base(title, "theology") or stripped_base(title, "doctrine") or base
        aliases = [f"{base} theology", f"{base} doctrine", f"{base} in biblical theology", f"{base} teaching"]
    elif category == "institution":
        aliases = [f"{base} institution", f"{base} in scripture", f"{base} structure", f"{base} role"]
    elif category == "word_study":
        aliases = [f"meaning of {base}", f"{base} lexical study", f"{base} in scripture", f"{base} meaning"]
    elif category == "archaeology":
        aliases = [f"{base} artifact", f"{base} discovery", f"{base} excavation", f"{base} find"]
    elif category == "prophecy":
        aliases = [f"{base} oracle", f"{base} prophecy", f"{base} vision", f"{base} prediction"]
    elif category == "faq":
        topic = question_topic(title)
        aliases = [f"{topic} question", f"{topic} in the bible", f"{topic} overview"]
    else:
        aliases = [f"tell me about {base}"]

    aliases.extend(extra_aliases)
    aliases = unique_normalized(aliases)
    title_key = normalize_alias(title)
    filtered = [alias for alias in aliases if normalize_alias(alias) != title_key]
    if filtered:
        return filtered
    return [f"tell me about {base}"]


def placeholder_title(category: str, index: int) -> str:
    label = category.replace("_", " ").title()
    return f"{label} Placeholder {index:02d}"


def pad_titles(category: str, titles: list[str], target: int) -> list[str]:
    padded = list(titles)
    index = 1
    while len(padded) < target:
        candidate = placeholder_title(category, index)
        if candidate not in padded:
            padded.append(candidate)
        index += 1
    return padded[:target]


def load_json_list(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def select_places(limit: int) -> list[str]:
    if not OPENBIBLE_PLACES_PATH.exists():
        return [placeholder_title("place", index) for index in range(1, limit + 1)]

    raw = json.loads(OPENBIBLE_PLACES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return [placeholder_title("place", index) for index in range(1, limit + 1)]

    seeds = [
        "Jerusalem",
        "Shechem",
        "Bethel",
        "Hebron",
        "Babylon",
        "Nineveh",
        "Nazareth",
        "Capernaum",
        "Antioch",
        "Rome",
        "Bethlehem",
        "Egypt",
        "Sinai",
        "Samaria",
        "Jericho",
        "Damascus",
        "Corinth",
        "Ephesus",
        "Philippi",
        "Thessalonica",
    ]
    selected: list[str] = []
    seen: set[str] = set()
    by_name: dict[str, dict[str, object]] = {}
    candidates: list[tuple[int, int, str, str]] = []

    for item in raw:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        key = normalize_id(name)
        if key in by_name:
            continue
        by_name[key] = item
        references = item.get("references")
        ref_count = len(references) if isinstance(references, list) else 0
        confidence_rank = int(item.get("confidence_rank") or 0)
        candidates.append((-ref_count, -confidence_rank, normalize_alias(name), name))

    for _, _, _, name in sorted(candidates):
        key = normalize_id(name)
        if key in seen:
            continue
        selected.append(name)
        seen.add(key)
        if len(selected) >= limit:
            break

    ordered: list[str] = []
    seen.clear()
    for seed in seeds:
        key = normalize_id(seed)
        if key in by_name and key not in seen:
            ordered.append(str(by_name[key]["name"]))  # type: ignore[index]
            seen.add(key)
    for title in selected:
        key = normalize_id(title)
        if key in seen:
            continue
        ordered.append(title)
        seen.add(key)
    return pad_titles("place", ordered, limit)


def select_archaeology_titles(limit: int) -> list[str]:
    return pad_titles("archaeology", unique_normalized(ARCHAEOLOGY_TITLES), limit)


def build_titles(category: str) -> list[str]:
    if category == "book":
        return list(BOOKS)
    if category == "place":
        return select_places(TARGET_COUNTS[category])
    if category == "archaeology":
        return select_archaeology_titles(TARGET_COUNTS[category])
    curated = {
        "theology": THEOLOGY_TITLES,
        "theme": THEME_TITLES,
        "person": PEOPLE_TITLES,
        "event": EVENT_TITLES,
        "word_study": WORD_STUDY_TITLES,
        "institution": INSTITUTION_TITLES,
        "prophecy": PROPHECY_TITLES,
        "faq": FAQ_TITLES,
    }[category]
    return pad_titles(category, unique_normalized(curated), TARGET_COUNTS[category])


def write_json(path: Path, payload: object, *, force: bool) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == text:
            return
        if not force:
            raise FileExistsError(f"{path} already exists and differs; rerun with --force to overwrite")
    path.write_text(text, encoding="utf-8")


def build_objects() -> list[CanonicalObject]:
    objects: list[CanonicalObject] = []
    for category in TARGET_COUNTS:
        for title in build_titles(category):
            object_id = normalize_id(title)
            aliases = build_aliases(
                category,
                title,
            )
            objects.append(
                CanonicalObject(
                    id=object_id,
                    type=category,
                    title=title,
                    aliases=aliases,
                )
            )
    return objects


def write_inventory(objects: list[CanonicalObject], *, force: bool) -> dict[str, int]:
    if force and OBJECTS_ROOT.exists():
        for path in OBJECTS_ROOT.rglob("*.json"):
            if path.is_file():
                path.unlink()
    if force and MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()

    by_category: dict[str, list[CanonicalObject]] = {category: [] for category in TARGET_COUNTS}
    for obj in objects:
        by_category.setdefault(obj.type, []).append(obj)

    for category, entries in by_category.items():
        folder = OBJECTS_ROOT / CATEGORY_FOLDERS[category]
        folder.mkdir(parents=True, exist_ok=True)
        for entry in entries:
            path = folder / f"{entry.id}.json"
            write_json(path, entry.to_dict(), force=force)

    counts = {category: len(entries) for category, entries in by_category.items()}
    manifest = {
        "framework_version": "1.0",
        "schema_version": "1.0",
        "generated_at": None,
        "object_count": sum(counts.values()),
        "categories": {
            manifest_category: counts.get(category, 0)
            for category, manifest_category in CATEGORY_FOLDERS.items()
        },
    }
    write_json(MANIFEST_PATH, manifest, force=force)
    return counts


def validate_written_inventory() -> None:
    library = CanonicalLibrary(root=PACKAGE_ROOT).load()
    if len(library.objects_by_id) != sum(TARGET_COUNTS.values()):
        raise CanonicalValidationError(
            f"loaded object count {len(library.objects_by_id)} does not match expected total {sum(TARGET_COUNTS.values())}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite existing generated files")
    args = parser.parse_args()

    objects = build_objects()
    counts = Counter(obj.type for obj in objects)
    for category, expected in TARGET_COUNTS.items():
        actual = counts[category]
        if actual != expected:
            raise CanonicalValidationError(
                f"expected {expected} objects for {category}, built {actual}"
            )

    write_inventory(objects, force=args.force)
    validate_written_inventory()
    print(
        f"Generated {sum(TARGET_COUNTS.values())} placeholder objects under {OBJECTS_ROOT}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
