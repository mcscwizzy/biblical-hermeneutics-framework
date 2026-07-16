#!/usr/bin/env python3
"""Populate wave 4 CKL content deterministically.

This backfills theology, themes, prophecy, word studies, and archaeology
records that still have placeholder content.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.canonical_library import normalize_id
from framework.canonical_library.schema import CanonicalValidationError, validate_object

CKL_ROOT = ROOT / "framework" / "canonical_library"
OBJECTS_ROOT = CKL_ROOT / "objects"
CURRENT_DATE = "2026-07-16"
REVIEWED_BY = ["codex-phase-10"]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def tokens(text: str) -> set[str]:
    return {tok for tok in norm(text).split() if tok}


def complete_meta(data: dict[str, Any]) -> dict[str, Any]:
    data = dict(data)
    data["content_status"] = "complete"
    data["review_status"] = "in_review"
    data["reviewed_by"] = REVIEWED_BY[:]
    data["last_reviewed"] = CURRENT_DATE
    data["confidence"] = "medium"
    return data


def make_refs(refs: list[str]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for index, ref in enumerate(refs):
        entries.append(
            {
                "reference": ref,
                "relationship": "primary" if index == 0 else "supporting",
                "notes": "",
            }
        )
    return entries


def questions(title: str) -> list[str]:
    return [
        f"What does {title} teach?",
        f"How does {title} fit the biblical storyline?",
        f"What should readers avoid when interpreting {title}?",
    ]


def generic_notes(title: str) -> list[str]:
    return [
        f"Read {title} in its immediate context before generalizing.",
        "Do not flatten distinct passages into one slogan; let the canon keep its own shape.",
    ]


def filter_related(existing: set[str], preferred: list[str], *, self_id: str, fallback: list[str]) -> list[dict[str, Any]]:
    chosen: list[str] = []
    for candidate in preferred + fallback:
        candidate = normalize_id(candidate)
        if candidate == self_id or candidate not in existing or candidate in chosen:
            continue
        chosen.append(candidate)
    if not chosen:
        for candidate in sorted(existing):
            if candidate != self_id:
                chosen.append(candidate)
                break
    return [
        {
            "id": candidate,
            "relationship": "related-concept",
            "weight": 10 - index,
            "notes": "",
        }
        for index, candidate in enumerate(chosen[:5])
    ]


THEOLOGY_THEME_GROUPS: dict[str, dict[str, Any]] = {
    "covenant": {
        "phrase": "covenant promise, loyalty, and fulfillment",
        "refs": ["Genesis 9:8-17", "Genesis 12:1-3", "Exodus 19:1-6", "Jeremiah 31:31-34", "Luke 22:20", "Hebrews 8:6-13"],
        "sources": ["Genesis 9, 12, 15, 17", "Exodus 19-24", "Jeremiah 31", "Hebrews 8-10"],
        "related": ["covenant-theme", "covenant-theology", "new-covenant", "abraham", "moses", "jeremiah", "hebrews"],
        "importance": 96,
    },
    "creation": {
        "phrase": "ordered creation and renewed creation",
        "refs": ["Genesis 1:1-31", "Genesis 2:1-25", "Psalm 8:1-9", "John 1:1-5", "Romans 8:18-25", "Revelation 21:1-5"],
        "sources": ["Genesis 1-2", "Psalm 8", "John 1", "Romans 8", "Revelation 21"],
        "related": ["creation-theme", "creation-doctrine", "genesis", "adam", "revelation"],
        "importance": 95,
    },
    "messiah": {
        "phrase": "royal messianic hope, suffering, and vindication",
        "refs": ["2 Samuel 7:8-16", "Psalm 2:1-12", "Isaiah 11:1-10", "Isaiah 53:1-12", "Luke 24:25-27", "Acts 2:22-36"],
        "sources": ["2 Samuel 7", "Psalm 2", "Isaiah 11", "Isaiah 53", "Luke 24", "Acts 2"],
        "related": ["messiah-theme", "christology", "jesus", "david", "isaiah", "matthew", "hebrews"],
        "importance": 96,
    },
    "spirit": {
        "phrase": "the Spirit's presence, power, and new-covenant life",
        "refs": ["Genesis 1:1-2", "Ezekiel 36:24-28", "Joel 2:28-32", "John 14:15-26", "Acts 2:1-18", "Romans 8:1-17"],
        "sources": ["Genesis 1", "Ezekiel 36-37", "Joel 2", "John 14-16", "Acts 2", "Romans 8"],
        "related": ["spirit-theme", "theology-of-the-spirit", "pneumatology", "acts", "john"],
        "importance": 95,
    },
    "kingdom": {
        "phrase": "God's reign, rule, and coming fulfillment",
        "refs": ["Psalm 2:1-12", "Daniel 2:31-45", "Daniel 7:13-14", "Matthew 4:17", "Matthew 13:31-33", "Revelation 11:15"],
        "sources": ["Psalm 2", "Daniel 2", "Daniel 7", "Matthew 4", "Matthew 13", "Revelation 11"],
        "related": ["kingdom-theme", "theology-of-the-kingdom", "matthew", "daniel", "revelation", "luke"],
        "importance": 95,
    },
    "temple": {
        "phrase": "God's dwelling presence among his people",
        "refs": ["Exodus 25:8-9", "Exodus 40:34-38", "1 Kings 8:10-13", "John 1:14", "John 2:19-21", "Ephesians 2:19-22", "Revelation 21:1-3"],
        "sources": ["Exodus 25-40", "1 Kings 8", "John 1-2", "Ephesians 2", "Revelation 21"],
        "related": ["temple-theme", "what-is-the-temple", "tabernacle", "sanctuary-theme", "hebrews", "ezra"],
        "importance": 95,
    },
    "holiness": {
        "phrase": "set-apart holiness",
        "refs": ["Leviticus 19:1-2", "Isaiah 6:1-8", "1 Peter 1:13-16", "Hebrews 12:14"],
        "sources": ["Leviticus 19", "Isaiah 6", "1 Peter 1", "Hebrews 12"],
        "related": ["holiness-theme", "divine-holiness", "leviticus", "1-peter", "isaiah"],
        "importance": 92,
    },
    "justice": {
        "phrase": "righteous justice and covenant accountability",
        "refs": ["Deuteronomy 32:3-4", "Micah 6:6-8", "Romans 2:1-11", "Revelation 19:1-2"],
        "sources": ["Deuteronomy 32", "Micah 6", "Romans 2", "Revelation 19"],
        "related": ["justice-theme", "divine-justice", "amos", "micah", "romans"],
        "importance": 92,
    },
    "mercy": {
        "phrase": "mercy, grace, and steadfast love",
        "refs": ["Exodus 34:6-7", "Psalm 103:8-13", "Micah 7:18-20", "Ephesians 2:4-10", "Titus 2:11-14"],
        "sources": ["Exodus 34", "Psalm 103", "Micah 7", "Ephesians 2", "Titus 2"],
        "related": ["mercy-theme", "divine-mercy", "grace", "hesed", "eleos", "ephesians"],
        "importance": 93,
    },
    "faith": {
        "phrase": "faith, trust, and covenant fidelity",
        "refs": ["Genesis 15:6", "Habakkuk 2:4", "Romans 4:16-25", "Hebrews 11:1-6"],
        "sources": ["Genesis 15", "Habakkuk 2", "Romans 4", "Hebrews 11"],
        "related": ["faith", "faithfulness-theme", "abraham", "romans", "hebrews"],
        "importance": 93,
    },
    "eschatology": {
        "phrase": "final judgment, resurrection, and renewed creation",
        "refs": ["Daniel 7:13-14", "Daniel 12:1-3", "Matthew 24:29-31", "1 Thessalonians 4:13-18", "1 Corinthians 15:20-28", "Revelation 21:1-5"],
        "sources": ["Daniel 7", "Daniel 12", "Matthew 24", "1 Thessalonians 4", "1 Corinthians 15", "Revelation 21"],
        "related": ["eschatology", "second-coming", "final-judgment", "revelation", "daniel", "1-thessalonians"],
        "importance": 93,
    },
    "church": {
        "phrase": "God's gathered people and their shared life",
        "refs": ["Matthew 16:13-19", "Acts 2:42-47", "Ephesians 2:19-22", "Ephesians 4:1-16", "1 Peter 2:4-10"],
        "sources": ["Matthew 16", "Acts 2", "Ephesians 2", "Ephesians 4", "1 Peter 2"],
        "related": ["ecclesiology", "people-of-god-theme", "ekklesia", "acts", "ephesians", "1-peter"],
        "importance": 91,
    },
    "scripture": {
        "phrase": "the word, law, and witness of Scripture",
        "refs": ["Deuteronomy 6:4-9", "Psalm 19:7-11", "Psalm 119:9-16", "Luke 24:25-27", "2 Timothy 3:14-17", "Hebrews 1:1-4"],
        "sources": ["Deuteronomy 6", "Psalm 19", "Psalm 119", "Luke 24", "2 Timothy 3", "Hebrews 1"],
        "related": ["bibliology", "inspiration", "inerrancy", "word-of-god-theme", "deuteronomy", "psalms", "john"],
        "importance": 92,
    },
    "mission": {
        "phrase": "witness, proclamation, and sending",
        "refs": ["Genesis 12:1-3", "Matthew 28:18-20", "Acts 1:8", "Romans 15:18-21", "1 Peter 2:9-12"],
        "sources": ["Genesis 12", "Matthew 28", "Acts 1", "Romans 15", "1 Peter 2"],
        "related": ["mission", "witness-theme", "martyria", "kerygma", "acts", "matthew"],
        "importance": 90,
    },
    "adoption": {
        "phrase": "familial belonging and sonship",
        "refs": ["Romans 8:14-17", "Galatians 4:4-7", "Ephesians 1:3-6", "1 John 3:1-3"],
        "sources": ["Romans 8", "Galatians 4", "Ephesians 1", "1 John 3"],
        "related": ["adoption", "adoption-theme", "romans", "galatians", "ephesians", "abba"],
        "importance": 90,
    },
    "resurrection": {
        "phrase": "life from death and future bodily renewal",
        "refs": ["Daniel 12:1-3", "John 11:17-27", "Luke 24:1-12", "1 Corinthians 15:20-28", "Revelation 21:1-5"],
        "sources": ["Daniel 12", "John 11", "Luke 24", "1 Corinthians 15", "Revelation 21"],
        "related": ["resurrection-doctrine", "resurrection-theme", "1-corinthians", "john", "romans", "revelation"],
        "importance": 94,
    },
    "sacrifice": {
        "phrase": "atonement, priesthood, and substitutionary access",
        "refs": ["Leviticus 16:1-34", "Isaiah 53:4-12", "Hebrews 9:11-28", "Hebrews 10:1-18", "1 John 2:1-2"],
        "sources": ["Leviticus 16", "Isaiah 53", "Hebrews 9-10", "1 John 2"],
        "related": ["sacrifice-theme", "atonement", "leviticus", "hebrews", "isaiah", "romans"],
        "importance": 94,
    },
    "sanctification": {
        "phrase": "growth in holiness and faithful perseverance",
        "refs": ["Leviticus 20:7-8", "John 17:17-19", "Romans 6:11-14", "1 Thessalonians 4:1-8", "Hebrews 12:14"],
        "sources": ["Leviticus 20", "John 17", "Romans 6", "1 Thessalonians 4", "Hebrews 12"],
        "related": ["sanctification", "perseverance", "grace", "1-thessalonians", "philippians"],
        "importance": 90,
    },
    "prayer": {
        "phrase": "communion with God in dependence and praise",
        "refs": ["Psalm 4:1-8", "Matthew 6:5-13", "Luke 11:1-13", "Philippians 4:4-7", "James 5:13-18"],
        "sources": ["Psalm 4", "Matthew 6", "Luke 11", "Philippians 4", "James 5"],
        "related": ["theology-of-prayer", "prayer-theme", "psalms", "matthew", "luke", "philippians"],
        "importance": 90,
    },
    "worship": {
        "phrase": "reverent response to God's worth and presence",
        "refs": ["Exodus 15:1-18", "Psalm 95:1-7", "John 4:19-24", "Romans 12:1-2", "Revelation 4:1-11"],
        "sources": ["Exodus 15", "Psalm 95", "John 4", "Romans 12", "Revelation 4"],
        "related": ["theology-of-worship", "worship-theme", "psalms", "john", "revelation", "romans"],
        "importance": 91,
    },
    "suffering": {
        "phrase": "suffering, the cross, and faithful endurance",
        "refs": ["Job 1:1-22", "Psalm 22:1-31", "Isaiah 53:1-12", "Romans 5:1-5", "1 Peter 4:12-19"],
        "sources": ["Job 1-2", "Psalm 22", "Isaiah 53", "Romans 5", "1 Peter 4"],
        "related": ["theology-of-suffering", "theology-of-the-cross", "job", "isaiah", "romans", "1-peter"],
        "importance": 89,
    },
    "trinity": {
        "phrase": "the one God who is Father, Son, and Spirit",
        "refs": ["Matthew 28:18-20", "John 1:1-18", "John 14:15-26", "2 Corinthians 13:14", "Ephesians 4:4-6"],
        "sources": ["Matthew 28", "John 1", "John 14-16", "2 Corinthians 13", "Ephesians 4"],
        "related": ["trinity", "matthew", "john", "2-corinthians", "ephesians"],
        "importance": 95,
    },
    "typology": {
        "phrase": "patterns of promise and fulfillment across the canon",
        "refs": ["Exodus 12:1-14", "Numbers 21:4-9", "Romans 5:12-21", "1 Corinthians 10:1-13", "Hebrews 8:1-6"],
        "sources": ["Exodus 12", "Numbers 21", "Romans 5", "1 Corinthians 10", "Hebrews 8"],
        "related": ["typology", "what-is-typology", "hebrews", "romans", "1-corinthians", "luke"],
        "importance": 90,
    },
    "union": {
        "phrase": "shared life with Christ",
        "refs": ["John 15:1-11", "Romans 6:1-11", "Galatians 2:19-20", "Ephesians 2:1-10", "Colossians 3:1-17"],
        "sources": ["John 15", "Romans 6", "Galatians 2", "Ephesians 2", "Colossians 3"],
        "related": ["union-with-christ", "romans", "galatians", "ephesians", "colossians"],
        "importance": 92,
    },
    "restoration": {
        "phrase": "exile, return, and renewed hope",
        "refs": ["Deuteronomy 30:1-10", "Isaiah 40:1-11", "Ezekiel 36:24-28", "Joel 2:28-32", "Revelation 21:1-5"],
        "sources": ["Deuteronomy 30", "Isaiah 40", "Ezekiel 36", "Joel 2", "Revelation 21"],
        "related": ["exile-theme", "why-is-exile-important", "restoration-prophecy", "remnant-prophecy", "new-jerusalem-theme", "new-temple-theme"],
        "importance": 92,
    },
    "wisdom": {
        "phrase": "wise, skillful living",
        "refs": ["Proverbs 1:1-7", "Proverbs 8:1-36", "James 1:5-8", "James 3:13-18"],
        "sources": ["Proverbs 1", "Proverbs 8", "James 1", "James 3"],
        "related": ["wisdom-theme", "sophia", "sophos", "proverbs", "james"],
        "importance": 88,
    },
    "light": {
        "phrase": "revelation and moral contrast",
        "refs": ["Genesis 1:1-5", "Psalm 27:1", "John 1:1-9", "Ephesians 5:8-14", "1 John 1:5-10"],
        "sources": ["Genesis 1", "Psalm 27", "John 1", "Ephesians 5", "1 John 1"],
        "related": ["phos", "skotia", "light-and-darkness-theme", "john", "ephesians", "1-john"],
        "importance": 88,
    },
    "provision": {
        "phrase": "God's provision",
        "refs": ["Exodus 16:1-36", "Deuteronomy 8:1-20", "John 6:1-59"],
        "sources": ["Exodus 16", "Deuteronomy 8", "John 6"],
        "related": ["manna", "exodus-pattern-theme", "john", "exodus"],
        "importance": 86,
    },
    "presence": {
        "phrase": "presence and dwelling",
        "refs": ["Exodus 3:1-6", "Exodus 40:34-38", "1 Kings 8:10-13", "John 1:14", "Revelation 21:1-3"],
        "sources": ["Exodus 3", "Exodus 40", "1 Kings 8", "John 1", "Revelation 21"],
        "related": ["shekinah", "presence-theme", "glory-theme", "sanctuary-theme", "temple-theme"],
        "importance": 90,
    },
    "peace": {
        "phrase": "shalom and wholeness",
        "refs": ["Numbers 6:22-27", "Psalm 85:8-13", "Isaiah 26:1-4", "John 14:27", "Ephesians 2:14-18", "Philippians 4:4-7"],
        "sources": ["Numbers 6", "Psalm 85", "Isaiah 26", "John 14", "Ephesians 2", "Philippians 4"],
        "related": ["shalom", "peace-theme", "mercy-theme"],
        "importance": 87,
    },
    "perseverance": {
        "phrase": "endurance in faith",
        "refs": ["Romans 5:1-5", "Hebrews 3:14", "Hebrews 10:19-39", "Hebrews 12:1-3", "James 1:2-4"],
        "sources": ["Romans 5", "Hebrews 3", "Hebrews 10", "Hebrews 12", "James 1"],
        "related": ["hupomone", "perseverance", "sanctification"],
        "importance": 87,
    },
    "anthropology": {
        "phrase": "humanity and fleshly existence",
        "refs": ["Genesis 1:26-28", "Psalm 8:1-9", "Romans 5:12-21", "Romans 7:14-25", "Galatians 5:13-26"],
        "sources": ["Genesis 1", "Psalm 8", "Romans 5", "Romans 7", "Galatians 5"],
        "related": ["sarx", "image-of-god-theme", "creation-theme"],
        "importance": 86,
    },
    "blessedness": {
        "phrase": "blessedness before God",
        "refs": ["Psalm 1:1-3", "Psalm 32:1-2", "Matthew 5:1-12", "Luke 6:20-23"],
        "sources": ["Psalm 1", "Psalm 32", "Matthew 5", "Luke 6"],
        "related": ["makarios", "wisdom-theme", "psalms", "matthew", "luke"],
        "importance": 86,
    },
}


THEOLOGY_THEME_MATCHERS: list[tuple[list[str], str]] = [
    (["new covenant", "new-covenant"], "covenant"),
    (["new creation", "new-creation"], "creation"),
    (["new exodus", "new-exodus"], "restoration"),
    (["new jerusalem", "new-jerusalem"], "restoration"),
    (["new temple", "new-temple"], "temple"),
    (["land"], "restoration"),
    (["covenant"], "covenant"),
    (["creation"], "creation"),
    (["messiah", "christology", "incarnation", "christos"], "messiah"),
    (["spirit", "pneumatology", "pneuma", "parakletos"], "spirit"),
    (["kingdom"], "kingdom"),
    (["temple", "tabernacle", "sanctuary", "shekinah"], "temple"),
    (["holiness", "qadosh"], "holiness"),
    (["justice", "righteousness", "mishpat", "tsedeq"], "justice"),
    (["mercy", "grace", "hesed", "eleos", "charis"], "mercy"),
    (["faith"], "faith"),
    (["eschatology", "second coming", "second-coming", "final judgment", "final-judgment", "parousia"], "eschatology"),
    (["church", "ecclesiology", "people of god", "people-of-god"], "church"),
    (["scripture", "bibliology", "inspiration", "inerrancy", "word of god", "word-of-god"], "scripture"),
    (["mission", "witness", "martyria", "kerygma"], "mission"),
    (["adoption", "sonship"], "adoption"),
    (["resurrection", "anastasis"], "resurrection"),
    (["sacrifice", "atonement", "priesthood"], "sacrifice"),
    (["sanctification"], "sanctification"),
    (["prayer"], "prayer"),
    (["worship"], "worship"),
    (["suffering", "cross"], "suffering"),
    (["trinity"], "trinity"),
    (["typology"], "typology"),
    (["union with christ", "union-with-christ"], "union"),
    (["repentance", "metanoia"], "restoration"),
    (["remnant"], "restoration"),
    (["restoration"], "restoration"),
    (["hope"], "restoration"),
    (["light", "darkness"], "light"),
    (["water", "spirit"], "presence"),
    (["glory"], "presence"),
    (["presence"], "presence"),
    (["shepherd"], "restoration"),
    (["seed"], "restoration"),
    (["day of the lord", "day-of-the-lord"], "restoration"),
    (["peace"], "peace"),
    (["faithfulness"], "covenant"),
    (["promise"], "covenant"),
    (["redemption"], "restoration"),
    (["blessing", "curse"], "covenant"),
    (["providence"], "restoration"),
    (["perseverance"], "perseverance"),
    (["glorification"], "eschatology"),
    (["final judgment", "final-judgment"], "eschatology"),
]


def theology_theme_group(title: str) -> str:
    lowered = norm(title)
    for needles, group in THEOLOGY_THEME_MATCHERS:
        if any(needle in lowered for needle in needles):
            return group
    return "covenant"


def build_theology_theme(data: dict[str, Any], category: str, existing_ids: set[str]) -> dict[str, Any]:
    title = data["title"]
    group = theology_theme_group(title)
    spec = THEOLOGY_THEME_GROUPS.get(group, THEOLOGY_THEME_GROUPS["covenant"])
    kind = "theological doctrine" if category == "theology" else "biblical motif"
    payload = dict(data)
    payload["summary"] = f"{title} is a {kind} that traces {spec['phrase']} across Scripture."
    payload["historical_context"] = f"{title} is read across the canon as Scripture develops this theme from Israel's story into the New Testament witness."
    payload["ancient_near_east_context"] = "Ancient covenant, royal, wisdom, and temple backgrounds provide comparison points, but Scripture gives the topic its own theological shape."
    payload["literary_context"] = "The topic appears in narrative, poetry, prophecy, Gospel, epistle, and apocalyptic writing as context requires."
    payload["covenantal_significance"] = f"{title} helps show how covenant promises are stated, tested, and fulfilled in Scripture."
    payload["interpretive_notes"] = generic_notes(title)
    payload["common_questions"] = questions(title)
    payload["sources"] = list(spec["sources"])
    payload["scripture_references"] = make_refs(list(spec["refs"]))
    payload["related_objects"] = filter_related(existing_ids, list(spec["related"]), self_id=payload["id"], fallback=["covenant-theme", "creation-theme", "messiah-theme", "temple-theme", "exile-theme"])
    payload["importance"] = int(spec["importance"])
    return complete_meta(payload)


WORD_GROUPS: dict[str, dict[str, Any]] = {
    "divine_name": {"summary_label": "God's identity and covenant name", "refs": ["Exodus 3:13-15", "Deuteronomy 6:4-5", "Psalm 23:1", "John 1:1-18"], "sources": ["Exodus 3", "Deuteronomy 6", "Psalm 23", "John 1"], "related": ["yahweh", "elohim", "adonai", "theos", "kyrios"], "importance": 92},
    "adoption": {"summary_label": "familial belonging and sonship", "refs": ["Romans 8:14-17", "Galatians 4:4-7", "Ephesians 1:3-6", "1 John 3:1-3"], "sources": ["Romans 8", "Galatians 4", "Ephesians 1", "1 John 3"], "related": ["abba", "adoption-theme", "romans", "galatians", "ephesians"], "importance": 90},
    "messiah": {"summary_label": "the anointed king and deliverer", "refs": ["2 Samuel 7:8-16", "Psalm 2:1-12", "Isaiah 11:1-10", "Micah 5:2-5", "Luke 24:25-27"], "sources": ["2 Samuel 7", "Psalm 2", "Isaiah 11", "Micah 5", "Luke 24"], "related": ["christos", "mashiach", "messiah-theme", "christology", "jesus"], "importance": 92},
    "covenant": {"summary_label": "covenant promise and instruction", "refs": ["Genesis 9:8-17", "Deuteronomy 6:4-9", "Jeremiah 31:31-34", "Hebrews 8:6-13"], "sources": ["Genesis 9", "Deuteronomy 6", "Jeremiah 31", "Hebrews 8"], "related": ["berit", "diatheke", "covenant-theme", "covenant-theology", "what-is-covenant"], "importance": 90},
    "scripture": {"summary_label": "the word, law, and witness of Scripture", "refs": ["Psalm 19:7-11", "Psalm 119:9-16", "John 1:1-18", "2 Timothy 3:14-17", "Hebrews 4:12-13"], "sources": ["Psalm 19", "Psalm 119", "John 1", "2 Timothy 3", "Hebrews 4"], "related": ["dabar", "logos", "torah", "bibliology", "inspiration", "inerrancy"], "importance": 90},
    "grace": {"summary_label": "mercy, favor, and steadfast love", "refs": ["Exodus 34:6-7", "Psalm 103:8-13", "Micah 7:18-20", "Ephesians 2:4-10", "Titus 2:11-14"], "sources": ["Exodus 34", "Psalm 103", "Micah 7", "Ephesians 2", "Titus 2"], "related": ["charis", "eleos", "hesed", "grace", "mercy-theme", "divine-mercy"], "importance": 90},
    "faith": {"summary_label": "trust and covenant fidelity", "refs": ["Genesis 15:6", "Habakkuk 2:4", "Romans 4:16-25", "Hebrews 11:1-6"], "sources": ["Genesis 15", "Habakkuk 2", "Romans 4", "Hebrews 11"], "related": ["pistis", "faith", "faithfulness-theme", "abraham", "romans", "hebrews"], "importance": 90},
    "holiness": {"summary_label": "set-apart holiness", "refs": ["Leviticus 19:1-2", "Isaiah 6:1-8", "1 Peter 1:13-16", "Hebrews 12:14"], "sources": ["Leviticus 19", "Isaiah 6", "1 Peter 1", "Hebrews 12"], "related": ["qadosh", "holiness-theme", "divine-holiness", "leviticus", "1-peter"], "importance": 89},
    "justice": {"summary_label": "righteous justice and covenant accountability", "refs": ["Deuteronomy 32:3-4", "Micah 6:6-8", "Romans 2:1-11", "Revelation 19:1-2"], "sources": ["Deuteronomy 32", "Micah 6", "Romans 2", "Revelation 19"], "related": ["mishpat", "tsedeq", "justice-theme", "divine-justice", "amos", "micah"], "importance": 89},
    "spirit": {"summary_label": "the Spirit's work", "refs": ["Genesis 1:1-2", "Ezekiel 36:24-28", "John 14:15-26", "Acts 2:1-18", "Romans 8:1-17"], "sources": ["Genesis 1", "Ezekiel 36", "John 14-16", "Acts 2", "Romans 8"], "related": ["pneuma", "parakletos", "spirit-theme", "theology-of-the-spirit", "acts", "john"], "importance": 91},
    "community": {"summary_label": "assembly and shared life", "refs": ["Acts 2:42-47", "Ephesians 4:1-16", "1 Peter 2:4-10", "Hebrews 10:19-25"], "sources": ["Acts 2", "Ephesians 4", "1 Peter 2", "Hebrews 10"], "related": ["ekklesia", "qahal", "ecclesiology", "people-of-god-theme", "acts", "ephesians"], "importance": 88},
    "wisdom": {"summary_label": "wise, skillful living", "refs": ["Proverbs 1:1-7", "Proverbs 8:1-36", "James 1:5-8", "James 3:13-18"], "sources": ["Proverbs 1", "Proverbs 8", "James 1", "James 3"], "related": ["sophia", "sophos", "wisdom-theme", "proverbs", "james"], "importance": 88},
    "eschatology": {"summary_label": "the coming age and resurrection hope", "refs": ["Daniel 12:1-3", "1 Corinthians 15:20-28", "1 Thessalonians 4:13-18", "Revelation 21:1-5"], "sources": ["Daniel 12", "1 Corinthians 15", "1 Thessalonians 4", "Revelation 21"], "related": ["anastasis", "parousia", "eschatology", "second-coming", "final-judgment", "revelation"], "importance": 90},
    "salvation": {"summary_label": "deliverance and rescue", "refs": ["Isaiah 53:4-12", "John 3:16-18", "Romans 3:21-26", "Ephesians 2:1-10", "Titus 3:4-7"], "sources": ["Isaiah 53", "John 3", "Romans 3", "Ephesians 2", "Titus 3"], "related": ["soteria", "grace", "ephesians", "romans", "titus"], "importance": 90},
    "law": {"summary_label": "instruction and covenant obligation", "refs": ["Exodus 20:1-17", "Deuteronomy 6:4-9", "Psalm 1:1-3", "Romans 7:7-25", "Galatians 3:19-29"], "sources": ["Exodus 20", "Deuteronomy 6", "Psalm 1", "Romans 7", "Galatians 3"], "related": ["nomos", "torah", "law-and-gospel", "deuteronomy", "romans"], "importance": 88},
    "praise": {"summary_label": "prayerful praise and blessing", "refs": ["Psalm 103:1-5", "Psalm 145:1-21", "Matthew 21:9", "Revelation 5:11-14"], "sources": ["Psalm 103", "Psalm 145", "Matthew 21", "Revelation 5"], "related": ["amen", "hallelujah", "hosanna", "worship-theme", "psalms"], "importance": 87},
    "service": {"summary_label": "service and ministry", "refs": ["Mark 10:42-45", "John 13:1-17", "Romans 12:1-8", "Ephesians 4:11-16"], "sources": ["Mark 10", "John 13", "Romans 12", "Ephesians 4"], "related": ["diakonia", "doulos", "mission", "acts", "philippians"], "importance": 87},
    "time": {"summary_label": "the day, seasons, and Sabbath rhythms", "refs": ["Psalm 90:1-12", "Ecclesiastes 3:1-15", "Ephesians 5:15-17", "1 Thessalonians 5:1-11"], "sources": ["Psalm 90", "Ecclesiastes 3", "Ephesians 5", "1 Thessalonians 5"], "related": ["hemera", "sabbaton", "day-of-the-lord-theme", "ecclesiastes", "1-thessalonians"], "importance": 86},
    "glory": {"summary_label": "honor, radiance, and divine glory", "refs": ["Exodus 33:18-23", "Isaiah 6:1-4", "John 1:14", "2 Corinthians 3:7-18", "Revelation 21:22-26"], "sources": ["Exodus 33", "Isaiah 6", "John 1", "2 Corinthians 3", "Revelation 21"], "related": ["doxa", "glory-theme", "temple-theme", "john", "revelation"], "importance": 89},
    "creation": {"summary_label": "creation and workmanship", "refs": ["Genesis 1:1-31", "Psalm 8:1-9", "Romans 8:18-25", "Revelation 21:1-5"], "sources": ["Genesis 1-2", "Psalm 8", "Romans 8", "Revelation 21"], "related": ["katabole", "poiema", "creation-theme", "genesis", "revelation"], "importance": 90},
    "repentance": {"summary_label": "turning back to God", "refs": ["Deuteronomy 30:1-10", "Ezekiel 18:30-32", "Mark 1:14-15", "Luke 15:11-32", "Acts 2:36-41"], "sources": ["Deuteronomy 30", "Ezekiel 18", "Mark 1", "Luke 15", "Acts 2"], "related": ["metanoia", "repentance", "restoration-prophecy", "mark", "acts"], "importance": 88},
    "light": {"summary_label": "revelation and moral contrast", "refs": ["Genesis 1:1-5", "Psalm 27:1", "John 1:1-9", "Ephesians 5:8-14", "1 John 1:5-10"], "sources": ["Genesis 1", "Psalm 27", "John 1", "Ephesians 5", "1 John 1"], "related": ["phos", "skotia", "light-and-darkness-theme", "john", "ephesians", "1-john"], "importance": 88},
    "provision": {"summary_label": "God's provision", "refs": ["Exodus 16:1-36", "Deuteronomy 8:1-20", "John 6:1-59"], "sources": ["Exodus 16", "Deuteronomy 8", "John 6"], "related": ["manna", "exodus-pattern-theme", "john", "exodus"], "importance": 86},
    "presence": {"summary_label": "presence and dwelling", "refs": ["Exodus 3:1-6", "Exodus 40:34-38", "1 Kings 8:10-13", "John 1:14", "Revelation 21:1-3"], "sources": ["Exodus 3", "Exodus 40", "1 Kings 8", "John 1", "Revelation 21"], "related": ["shekinah", "presence-theme", "glory-theme", "sanctuary-theme", "temple-theme"], "importance": 90},
    "peace": {"summary_label": "shalom and wholeness", "refs": ["Numbers 6:22-27", "Psalm 85:8-13", "Isaiah 26:1-4", "John 14:27", "Ephesians 2:14-18", "Philippians 4:4-7"], "sources": ["Numbers 6", "Psalm 85", "Isaiah 26", "John 14", "Ephesians 2", "Philippians 4"], "related": ["shalom", "peace-theme", "mercy-theme"], "importance": 87},
    "perseverance": {"summary_label": "endurance in faith", "refs": ["Romans 5:1-5", "Hebrews 3:14", "Hebrews 10:19-39", "Hebrews 12:1-3", "James 1:2-4"], "sources": ["Romans 5", "Hebrews 3", "Hebrews 10", "Hebrews 12", "James 1"], "related": ["hupomone", "perseverance", "sanctification"], "importance": 87},
    "anthropology": {"summary_label": "humanity and fleshly existence", "refs": ["Genesis 1:26-28", "Psalm 8:1-9", "Romans 5:12-21", "Romans 7:14-25", "Galatians 5:13-26"], "sources": ["Genesis 1", "Psalm 8", "Romans 5", "Romans 7", "Galatians 5"], "related": ["sarx", "image-of-god-theme", "creation-theme"], "importance": 86},
    "blessedness": {"summary_label": "blessedness before God", "refs": ["Psalm 1:1-3", "Psalm 32:1-2", "Matthew 5:1-12", "Luke 6:20-23"], "sources": ["Psalm 1", "Psalm 32", "Matthew 5", "Luke 6"], "related": ["makarios", "wisdom-theme", "psalms", "matthew", "luke"], "importance": 86},
}


WORD_TO_GROUP: dict[str, str] = {
    "abba": "adoption",
    "adonai": "divine_name",
    "agape": "grace",
    "agios": "holiness",
    "amen": "praise",
    "anastasis": "eschatology",
    "apostolos": "service",
    "basileia": "covenant",
    "berit": "covenant",
    "charis": "grace",
    "christos": "messiah",
    "dabar": "scripture",
    "diakonia": "service",
    "diatheke": "covenant",
    "doxa": "glory",
    "doulos": "service",
    "ekklesia": "community",
    "eleos": "grace",
    "elohim": "divine_name",
    "emet": "faith",
    "hallelujah": "praise",
    "hamartia": "salvation",
    "hemera": "time",
    "hesed": "grace",
    "hosanna": "praise",
    "hupomone": "perseverance",
    "katabole": "creation",
    "kerygma": "mission",
    "koinonia": "community",
    "kyrios": "divine_name",
    "logos": "scripture",
    "makarios": "blessedness",
    "manna": "provision",
    "mashiach": "messiah",
    "metanoia": "repentance",
    "mishpat": "justice",
    "nomos": "law",
    "parakletos": "spirit",
    "parousia": "eschatology",
    "pascha": "covenant",
    "phos": "light",
    "pistis": "faith",
    "poiema": "creation",
    "pneuma": "spirit",
    "qahal": "community",
    "qadosh": "holiness",
    "sarx": "anthropology",
    "sabbaton": "time",
    "shekinah": "presence",
    "shema": "law",
    "skotia": "light",
    "sophia": "wisdom",
    "sophos": "wisdom",
    "soteria": "salvation",
    "teleios": "wisdom",
    "theos": "divine_name",
    "torah": "law",
    "tsedeq": "justice",
    "yahweh": "divine_name",
}


def build_word(data: dict[str, Any], existing_ids: set[str]) -> dict[str, Any]:
    title = data["title"]
    group = WORD_TO_GROUP.get(norm(data["id"]), "scripture")
    spec = WORD_GROUPS[group]
    payload = dict(data)
    payload["summary"] = f"{title} is a biblical term associated with {spec['summary_label']}."
    payload["historical_context"] = f"In Hebrew and Greek usage, {title} carries a range of meaning, so context determines how the term functions in a given passage."
    payload["ancient_near_east_context"] = "Ancient language and culture shape how the term is heard in covenant, worship, wisdom, and narrative settings."
    payload["literary_context"] = "The term appears wherever the canon needs it, so context and genre determine its force."
    payload["covenantal_significance"] = f"Tracking {title} helps readers hear how Scripture describes God, people, and covenant life with precision."
    payload["interpretive_notes"] = [
        f"Do not reduce {title} to a single English gloss.",
        "Check the immediate context and genre before drawing theological conclusions.",
    ]
    payload["common_questions"] = questions(title)
    payload["sources"] = list(spec["sources"])
    payload["scripture_references"] = make_refs(list(spec["refs"]))
    payload["related_objects"] = filter_related(existing_ids, list(spec["related"]), self_id=payload["id"], fallback=["torah", "covenant-theme", "what-is-canonical-theology"])
    payload["importance"] = int(spec["importance"])
    return complete_meta(payload)


PROPHECY_SPECS: dict[str, dict[str, Any]] = {
    "messianic-prophecy": {
        "phrase": "a coming Davidic deliverer",
        "refs": ["2 Samuel 7:8-16", "Psalm 2:1-12", "Isaiah 11:1-10", "Micah 5:2-5", "Luke 24:25-27", "Acts 2:22-36"],
        "sources": ["2 Samuel 7", "Psalm 2", "Isaiah 11", "Micah 5", "Luke 24", "Acts 2"],
        "related": ["messiah-theme", "christology", "jesus", "david", "isaiah"],
        "importance": 96,
        "historical": "Messianic hope develops from the Davidic covenant and the prophetic search for a righteous king who will heal exile and injustice.",
    },
    "suffering-servant-prophecy": {
        "phrase": "the servant who suffers and is vindicated",
        "refs": ["Isaiah 42:1-9", "Isaiah 49:1-7", "Isaiah 50:4-11", "Isaiah 52:13-53:12", "Acts 8:26-40", "1 Peter 2:21-25"],
        "sources": ["Isaiah 42", "Isaiah 49", "Isaiah 50", "Isaiah 52-53", "Acts 8", "1 Peter 2"],
        "related": ["isaiah", "jesus", "messiah-theme", "sacrifice-theme"],
        "importance": 96,
        "historical": "The servant songs emerge from Isaiah's prophetic world and hold together Israel's vocation, suffering, and restoration.",
    },
    "day-of-the-lord-prophecy": {
        "phrase": "the decisive day of judgment and rescue",
        "refs": ["Joel 2:1-11", "Amos 5:18-20", "Zephaniah 1:14-18", "1 Thessalonians 5:1-11", "2 Peter 3:10-13"],
        "sources": ["Joel 2", "Amos 5", "Zephaniah 1", "1 Thessalonians 5", "2 Peter 3"],
        "related": ["day-of-the-lord-theme", "eschatology", "final-judgment", "revelation"],
        "importance": 95,
        "historical": "These warnings address covenant breach and imperial pressure, then project judgment and deliverance into the future.",
    },
    "new-covenant-prophecy": {
        "phrase": "inner renewal and forgiven sin",
        "refs": ["Jeremiah 31:31-34", "Ezekiel 36:24-28", "Luke 22:20", "2 Corinthians 3:1-6", "Hebrews 8:6-13"],
        "sources": ["Jeremiah 31", "Ezekiel 36", "Luke 22", "2 Corinthians 3", "Hebrews 8"],
        "related": ["new-covenant-theme", "covenant-theme", "jeremiah", "ezekiel", "hebrews"],
        "importance": 95,
        "historical": "The promise rises from exile and the need for heart change, forgiveness, and covenant renewal.",
    },
    "restoration-prophecy": {
        "phrase": "return, cleansing, and renewed community",
        "refs": ["Isaiah 40:1-11", "Jeremiah 30:1-24", "Ezekiel 36:24-38", "Ezekiel 37:1-28", "Zechariah 8:1-23", "Revelation 21:1-5"],
        "sources": ["Isaiah 40", "Jeremiah 30-33", "Ezekiel 36-37", "Zechariah 8", "Revelation 21"],
        "related": ["exile-theme", "remnant-prophecy", "new-jerusalem-prophecy", "new-covenant-prophecy"],
        "importance": 93,
        "historical": "These oracles speak to exile, displacement, and the rebuilding of life under God's mercy.",
    },
    "remnant-prophecy": {
        "phrase": "the faithful remnant preserved through judgment",
        "refs": ["Isaiah 10:20-23", "Zephaniah 3:11-20", "Romans 9:27-29", "Romans 11:1-6"],
        "sources": ["Isaiah 10", "Zephaniah 3", "Romans 9", "Romans 11"],
        "related": ["restoration-prophecy", "exile-theme", "romans", "isaiah"],
        "importance": 90,
        "historical": "Remnant prophecy emerges as prophets explain how judgment does not end God's covenant purposes.",
    },
    "branch-prophecy": {
        "phrase": "a righteous branch from David's line",
        "refs": ["Jeremiah 23:1-6", "Jeremiah 33:14-18", "Zechariah 3:8-10", "Zechariah 6:9-15"],
        "sources": ["Jeremiah 23", "Jeremiah 33", "Zechariah 3", "Zechariah 6"],
        "related": ["messiah-theme", "christology", "david", "isaiah"],
        "importance": 90,
        "historical": "The branch image appears after the collapse of monarchy and promises a renewed Davidic ruler.",
    },
    "immanuel-prophecy": {
        "phrase": "God with us in the midst of crisis",
        "refs": ["Isaiah 7:10-17", "Isaiah 8:1-10", "Matthew 1:18-25"],
        "sources": ["Isaiah 7", "Isaiah 8", "Matthew 1"],
        "related": ["messiah-theme", "christology", "isaiah", "matthew"],
        "importance": 92,
        "historical": "The sign belongs to the Syro-Ephraimite crisis and the fear of political collapse in Judah.",
    },
    "new-jerusalem-prophecy": {
        "phrase": "a renewed city where God dwells with his people",
        "refs": ["Isaiah 65:17-25", "Isaiah 66:22-24", "Ezekiel 40:1-48:35", "Revelation 21:1-22:5"],
        "sources": ["Isaiah 65-66", "Ezekiel 40-48", "Revelation 21-22"],
        "related": ["new-jerusalem-theme", "new-creation-theme", "temple-theme", "revelation"],
        "importance": 92,
        "historical": "The vision grows from exile and temple loss into a picture of final dwelling and restored holiness.",
    },
    "judgment-against-the-nations": {
        "phrase": "oracles of judgment on the nations",
        "refs": ["Isaiah 13:1-22", "Jeremiah 46:1-51:64", "Amos 1:3-2:16", "Obadiah 1:1-21", "Nahum 1:1-3:19", "Zephaniah 2:1-15"],
        "sources": ["Isaiah 13", "Jeremiah 46-51", "Amos 1-2", "Obadiah", "Nahum", "Zephaniah 2"],
        "related": ["day-of-the-lord-theme", "justice-theme", "amos", "jeremiah", "nahum"],
        "importance": 91,
        "historical": "These oracles respond to imperial aggression and the moral order of the nations.",
    },
    "generic": {
        "phrase": "prophetic proclamation",
        "refs": ["Isaiah 1:1-20", "Jeremiah 1:1-19", "Ezekiel 1:1-28", "Amos 3:1-15"],
        "sources": ["Isaiah 1", "Jeremiah 1", "Ezekiel 1", "Amos 3"],
        "related": ["isaiah", "jeremiah", "ezekiel", "amos"],
        "importance": 88,
        "historical": "Prophetic speech addresses real covenant crises in Israel, Judah, and the nations.",
    },
}


def build_prophecy(data: dict[str, Any], existing_ids: set[str]) -> dict[str, Any]:
    slug = normalize_id(data["id"])
    spec = PROPHECY_SPECS.get(slug, PROPHECY_SPECS["generic"])
    title = data["title"]
    payload = dict(data)
    payload["summary"] = f"{title} gathers prophetic texts about {spec['phrase']}."
    payload["historical_context"] = spec["historical"]
    payload["ancient_near_east_context"] = "Prophetic literature addresses imperial pressure, covenant breach, temple life, and national collapse within the ancient Near East."
    payload["literary_context"] = "Prophetic speech uses poetry, oracle forms, sign actions, and symbolic imagery to confront and comfort the covenant people."
    payload["covenantal_significance"] = f"{title} shows how judgment, mercy, and hope serve the covenant storyline."
    payload["interpretive_notes"] = [
        "Read the oracle first in its own historical setting.",
        "Prophetic speech is covenantal proclamation before it is prediction.",
    ]
    payload["common_questions"] = questions(title)
    payload["sources"] = list(spec["sources"])
    payload["scripture_references"] = make_refs(list(spec["refs"]))
    payload["related_objects"] = filter_related(existing_ids, list(spec["related"]), self_id=payload["id"], fallback=["messiah-theme", "day-of-the-lord-theme", "restoration-prophecy", "new-covenant-prophecy"])
    payload["importance"] = int(spec["importance"])
    return complete_meta(payload)


ARCHAEOLOGY_DATA_FILES = [
    ROOT / "bhf_web" / "static" / "data" / "archaeology" / "artifacts.json",
    ROOT / "bhf_web" / "static" / "data" / "archaeology" / "archaeologySites.json",
    ROOT / "bhf_web" / "static" / "data" / "archaeology" / "excavationReports.json",
    ROOT / "bhf_web" / "static" / "data" / "archaeology" / "museums.json",
]

ARCHAEOLOGY_HINTS: list[tuple[str, str]] = [
    ("dead sea scrolls", "dead-sea-scrolls"),
    ("qumran caves", "qumran-scroll-caves"),
    ("qumran archaeological site", "qumran"),
    ("siloam inscription", "siloam-inscription"),
    ("pool of siloam", "siloam-inscription"),
    ("hezekiahs tunnel", "siloam-inscription"),
    ("city of david", "jerusalem-city-of-david-survey"),
    ("caesarea maritima", "caesarea-roman-harbor"),
    ("lachish", "lachish-assyrian-siege"),
    ("megiddo", "megiddo-stratigraphy"),
    ("babylonian chronicles", "babylon-exile-context"),
    ("babylon", "babylon-exile-context"),
    ("nineveh", "nineveh-palace-excavations"),
    ("ephesus", "ephesus-urban-excavations"),
    ("cyrus cylinder", "cyrus-cylinder"),
    ("taylor prism", "taylor-prism"),
    ("black obelisk", "black-obelisk"),
    ("merneptah stele", "merneptah-stele"),
    ("tel dan", "tel-dan-stele"),
    ("mesha stele", "mesha-stele"),
    ("moabite stone", "mesha-stele"),
    ("pilate stone", "pilate-stone"),
    ("ketef hinnom", "ketef-hinnom-silver-scrolls"),
    ("lachish reliefs", "lachish-reliefs"),
    ("james ossuary", "james-ossuary"),
    ("beth shean", "beth-shean"),
    ("jericho", "jericho"),
    ("hazor", "hazor"),
    ("gezer", "gezer"),
    ("capernaum", "capernaum"),
    ("nazareth", "nazareth"),
    ("magdala", "magdala"),
]


def load_archaeology_candidates() -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for path in ARCHAEOLOGY_DATA_FILES:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            continue
        for item in raw:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                candidates[item["id"]] = item
    return candidates


def best_archaeology_candidate(title: str, candidates: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    slug = norm(title)
    for needle, candidate_id in ARCHAEOLOGY_HINTS:
        if needle in slug and candidate_id in candidates:
            return candidates[candidate_id]
    title_tokens = tokens(title)
    best: dict[str, Any] | None = None
    best_score = 0
    for item in candidates.values():
        text_fields = [
            item.get("name"),
            item.get("title"),
            item.get("description"),
            item.get("significance"),
            item.get("historicalSignificance"),
            item.get("biblicalConnections"),
            item.get("summary"),
            item.get("currentLocation"),
            item.get("siteType"),
        ]
        cand_tokens = set()
        for field in text_fields:
            if isinstance(field, str):
                cand_tokens.update(tokens(field))
        overlap = len(title_tokens & cand_tokens)
        if overlap > best_score:
            best_score = overlap
            best = item
    return best if best_score >= 1 else None


def archaeology_kind(title: str) -> str:
    slug = norm(title)
    if "scroll" in slug:
        return "manuscript or scroll collection"
    if "inscription" in slug:
        return "inscription"
    if any(piece in slug for piece in ["stele", "obelisk", "prism", "monolith", "cylinder"]):
        return "royal inscription or monument"
    if "ossuary" in slug:
        return "ossuary"
    if any(piece in slug for piece in ["excavation", "excavations", "site", "survey", "finds", "discovery"]):
        return "archaeological site or excavation"
    if any(piece in slug for piece in ["letters", "chronicles", "papyri", "tablets", "archives"]):
        return "documentary corpus"
    if any(piece in slug for piece in ["altar", "palace", "gate", "road", "pool", "workshop", "temple"]):
        return "archaeological feature"
    return "archaeological find"


def archaeology_refs(title: str, match: dict[str, Any] | None) -> list[str]:
    if match:
        passages = match.get("relatedPassages")
        if isinstance(passages, list) and passages:
            refs = [
                str(item)
                for item in passages
                if isinstance(item, str) and item.strip() and re.search(r"\d", item)
            ]
            if refs:
                return refs
    slug = norm(title)
    if "dead sea scrolls" in slug or "qumran" in slug:
        return ["Isaiah 40:1-11", "Daniel 7:1-28", "Matthew 3:1-12", "Luke 3:1-18"]
    if "siloam" in slug or "hezekiah" in slug:
        return ["2 Kings 20:20", "2 Chronicles 32:30", "John 9:1-12"]
    if "cyrus" in slug or "babylon" in slug:
        return ["2 Chronicles 36:22-23", "Ezra 1:1-4", "Jeremiah 29:1-14"]
    if any(word in slug for word in ["assyria", "sennacherib", "taylor prism", "black obelisk", "lachish"]):
        return ["2 Kings 18:13-37", "2 Kings 19:1-37", "Isaiah 36:1-37:38"]
    if "pilate" in slug or "caiaphas" in slug or "james ossuary" in slug:
        return ["Matthew 26:57-68", "Matthew 27:1-26", "John 18:28-40"]
    if "bronze snake" in slug:
        return ["Numbers 21:4-9", "2 Kings 18:1-4", "John 3:14-15"]
    if "ketef hinnom" in slug:
        return ["Numbers 6:22-27", "Deuteronomy 6:4-9"]
    if "balaam" in slug:
        return ["Numbers 22:1-41", "Numbers 23:1-30", "Numbers 24:1-25"]
    if "mount ebal" in slug:
        return ["Deuteronomy 27:1-8", "Joshua 8:30-35"]
    if "gibeon" in slug:
        return ["Joshua 9:1-27", "2 Samuel 2:12-17"]
    if "jerusalem" in slug or "city of david" in slug:
        return ["2 Samuel 5:1-12", "2 Kings 25:8-17", "Psalm 122:1-9", "Luke 19:41-44", "Acts 1:1-8"]
    if "megiddo" in slug:
        return ["Joshua 12:7-24", "1 Kings 9:15-19", "Revelation 16:12-16"]
    if "hazor" in slug:
        return ["Joshua 11:1-15", "1 Kings 9:15-19", "2 Kings 15:29"]
    if "gezer" in slug:
        return ["Joshua 10:33", "1 Kings 9:15-17", "1 Chronicles 7:28"]
    if "beth shean" in slug:
        return ["1 Samuel 31:1-13", "1 Kings 4:7-19"]
    if "nazareth" in slug:
        return ["Matthew 2:19-23", "Luke 1:26-38", "Luke 4:16-30", "Mark 6:1-6"]
    if "capernaum" in slug:
        return ["Matthew 4:12-17", "Mark 1:21-34", "Luke 4:31-41", "John 6:1-71"]
    if "ephesus" in slug:
        return ["Acts 19:1-41", "Ephesians 1:1-23", "Revelation 2:1-7"]
    if "laodicea" in slug:
        return ["Revelation 3:14-22", "Colossians 4:13-16"]
    return ["Genesis 1:1-2", "Psalm 19:1-6", "Romans 1:20"]


def archaeology_related(title: str, match: dict[str, Any] | None, existing_ids: set[str]) -> list[dict[str, Any]]:
    slug = norm(title)
    related: list[str] = []
    if match and isinstance(match.get("siteId"), str):
        site_id = normalize_id(str(match["siteId"]))
        site_overrides = {
            "beth-shean": "beth-shean-excavations",
            "caesarea-maritima": "caesarea-maritima-excavations",
            "dhiban": "moabite-stone",
            "gezer": "gezer-excavations",
            "hazor": "hazor-excavations",
            "lachish": "lachish-city-gate",
            "megiddo": "megiddo-excavations",
            "qumran": "qumran-archaeological-site",
            "tel-dan": "tell-dan-excavations",
        }
        related.append(site_overrides.get(site_id, site_id))
    if "jerusalem" in slug or "city of david" in slug:
        related.extend(["city-of-david-excavations", "jerusalem", "hezekiahs-tunnel-inscription-context", "isaiah"])
    elif "qumran" in slug or "dead sea scrolls" in slug:
        related.extend(["qumran-archaeological-site", "qumran-caves", "dead-sea-scrolls", "isaiah", "daniel-the-exile", "psalms"])
    elif "siloam" in slug or "hezekiah" in slug:
        related.extend(["city-of-david-excavations", "jerusalem", "hezekiahs-tunnel-inscription-context", "isaiah", "john"])
    elif "caesarea" in slug or "pilate" in slug:
        related.extend(["caesarea-maritima-excavations", "pilate-stone", "matthew", "john"])
    elif "lachish" in slug:
        related.extend(["lachish-city-gate", "lachish-reliefs", "isaiah", "jeremiah", "2-kings"])
    elif "megiddo" in slug:
        related.extend(["megiddo-excavations", "joshua", "1-kings", "revelation"])
    elif "hazor" in slug:
        related.extend(["hazor-excavations", "joshua", "1-kings"])
    elif "gezer" in slug:
        related.extend(["gezer-excavations", "joshua", "1-kings"])
    elif "beth shean" in slug:
        related.extend(["beth-shean-excavations", "1-samuel", "1-kings"])
    elif "nazareth" in slug:
        related.extend(["nazareth", "matthew", "luke", "mark"])
    elif "capernaum" in slug:
        related.extend(["capernaum", "matthew", "mark", "luke", "john"])
    elif "ephesus" in slug:
        related.extend(["ephesus", "acts", "ephesians", "revelation"])
    elif "babylon" in slug:
        related.extend(["babylon-1", "daniel", "jeremiah", "ezra"])
    elif "nineveh" in slug:
        related.extend(["nimrud-reliefs", "sennacherib-prism", "jonah", "nahum"])
    else:
        related.extend(["jerusalem", "joshua", "hebrews"])
    filtered: list[str] = []
    for candidate in related:
        candidate = normalize_id(candidate)
        if candidate in existing_ids and candidate != normalize_id(title) and candidate not in filtered:
            filtered.append(candidate)
    if not filtered:
        for candidate in ["jerusalem", "joshua", "hebrews"]:
            candidate = normalize_id(candidate)
            if candidate in existing_ids and candidate != normalize_id(title):
                filtered.append(candidate)
    return [
        {
            "id": candidate,
            "relationship": "historical-background",
            "weight": 10 - index,
            "notes": "",
        }
        for index, candidate in enumerate(filtered[:5])
    ]


def archaeology_text(title: str, kind: str, match: dict[str, Any] | None) -> tuple[str, str, str, str, list[str]]:
    if match:
        summary = str(match.get("description") or "").strip()
        if not summary and isinstance(match.get("title"), str):
            summary = f"{match['title']} illuminates the biblical world through material remains and historical context."
        historical = str(match.get("historicalSignificance") or match.get("significance") or "").strip()
        if not historical:
            historical = f"{title} helps anchor the biblical world in physical evidence and archaeological context."
        ancient = "The item belongs to the broader imperial, cultic, and urban world of the ancient Near East and the biblical periods reflected in the dataset."
        literary = str(match.get("biblicalConnections") or "").strip() or "The biblical text uses this kind of evidence as historical background rather than as a replacement for Scripture."
        caution = str(match.get("caution") or "").strip() or "Archaeology contextualizes the text but does not by itself settle every interpretive question."
        extras: list[str] = []
        for field in ("museum", "currentLocation", "siteId"):
            value = match.get(field)
            if isinstance(value, str) and value.strip():
                extras.append(value.strip())
        return summary, historical, ancient, literary, [caution, *extras]
    summary = f"{title} is an archaeological {kind} associated with the biblical world."
    historical = f"{title} provides a concrete setting for reading the biblical narrative, even when the exact interpretive link remains debated."
    ancient = "The item sits within the political, administrative, and cultic world of the Levant and broader ancient Near East."
    literary = "The Bible often reads material evidence as historical background that supports, contextualizes, or contrasts with the literary text."
    caution = "Archaeology should be read carefully and should not be treated as a substitute for the biblical text itself."
    return summary, historical, ancient, literary, [caution]


def archaeology_sources(title: str, kind: str, match: dict[str, Any] | None, refs: list[str]) -> list[str]:
    sources: list[str] = []
    if match:
        for field in ("name", "title", "museum", "currentLocation", "siteType", "artifactType"):
            value = match.get(field)
            if isinstance(value, str) and value.strip() and value not in sources:
                sources.append(value.strip())
    if not sources:
        sources.append(f"{title} archaeological literature")
    sources.extend(refs[:2])
    if kind == "inscription":
        sources.append("Epigraphic study and museum catalogue")
    elif kind == "manuscript or scroll collection":
        sources.append("Manuscript study and textual criticism")
    elif kind == "royal inscription or monument":
        sources.append("Imperial inscription and historical comparison")
    elif kind == "ossuary":
        sources.append("Second Temple burial practice")
    elif kind == "documentary corpus":
        sources.append("Ancient documentary and archive study")
    elif kind == "archaeological site or excavation":
        sources.append("Excavation report and stratigraphic study")
    else:
        sources.append("Archaeological survey and historical background")
    deduped: list[str] = []
    for item in sources:
        if item not in deduped:
            deduped.append(item)
    return deduped[:5]


def build_archaeology(data: dict[str, Any], candidates: dict[str, dict[str, Any]], existing_ids: set[str]) -> dict[str, Any]:
    title = data["title"]
    kind = archaeology_kind(title)
    match = best_archaeology_candidate(title, candidates)
    refs = archaeology_refs(title, match)
    summary, historical, ancient, literary, note_parts = archaeology_text(title, kind, match)
    payload = dict(data)
    payload["summary"] = summary
    payload["historical_context"] = historical
    payload["ancient_near_east_context"] = ancient
    payload["literary_context"] = literary
    payload["covenantal_significance"] = f"{title} helps anchor biblical claims in historical reality while reminding readers that archaeology supports rather than replaces interpretation."
    payload["interpretive_notes"] = [*note_parts, "Use the item as context for the biblical text, not as a shortcut around it."]
    payload["common_questions"] = questions(title)
    payload["sources"] = archaeology_sources(title, kind, match, refs)
    payload["scripture_references"] = make_refs(refs)
    payload["related_objects"] = archaeology_related(title, match, existing_ids)
    payload["importance"] = 94 if match and isinstance(match.get("id"), str) and match["id"] in {"dead-sea-scrolls", "siloam-inscription", "cyrus-cylinder", "tel-dan-stele", "pilate-stone", "taylor-prism", "black-obelisk", "merneptah-stele", "lachish-reliefs", "ketef-hinnom-silver-scrolls", "james-ossuary"} else 90 if match else 86
    return complete_meta(payload)


def build_existing_ids() -> set[str]:
    existing_ids: set[str] = set()
    for category in ["theology", "themes", "prophecy", "word_studies", "archaeology", "faq", "books", "people", "places", "events", "institutions"]:
        folder = OBJECTS_ROOT / category
        if not folder.exists():
            continue
        for path in folder.glob("*.json"):
            if path.name == "manifest.json":
                continue
            try:
                raw = read_json(path)
            except Exception:
                continue
            if isinstance(raw, dict) and isinstance(raw.get("id"), str):
                existing_ids.add(normalize_id(raw["id"]))
    return existing_ids


def main() -> int:
    existing_ids = build_existing_ids()
    candidates = load_archaeology_candidates()
    updated: list[str] = []
    for category in ["theology", "themes", "prophecy", "word_studies", "archaeology"]:
        folder = OBJECTS_ROOT / category
        for path in sorted(folder.glob("*.json")):
            raw = read_json(path)
            if str(raw.get("content_status", "")).strip().lower() == "complete":
                continue
            if category in {"theology", "themes"}:
                payload = build_theology_theme(raw, "theology" if category == "theology" else "theme", existing_ids)
            elif category == "prophecy":
                payload = build_prophecy(raw, existing_ids)
            elif category == "word_studies":
                payload = build_word(raw, existing_ids)
            else:
                payload = build_archaeology(raw, candidates, existing_ids)
            try:
                validate_object(payload, path=path.relative_to(CKL_ROOT).as_posix())
            except CanonicalValidationError as exc:
                raise SystemExit(f"validation failed for {path}: {exc}")
            write_json(path, payload)
            updated.append(path.relative_to(CKL_ROOT).as_posix())
    print(f"Updated {len(updated)} CKL objects.")
    counts = {}
    for entry in updated:
        category = entry.split("/")[1]
        counts[category] = counts.get(category, 0) + 1
    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
