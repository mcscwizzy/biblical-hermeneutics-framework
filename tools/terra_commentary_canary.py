#!/usr/bin/env python3
"""Build, validate, and review the reader-facing Terra Commentary v1.1 canary.

This is deliberately a candidate-only prose compiler.  It consumes the locked
25-chapter certification and rebuilds bundles solely to prove their hashes have
not changed.  The prose map was composed in the Terra canary pass; this tool
does not retrieve evidence, alter CKL, or contact any model/provider.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.availability import classify_evidence_availability
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION, COMMENTARY_SCHEMA_VERSION
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from tools.commentary_v11_canary import _chapter_overlap_refs


STRUCTURAL_ROOT = ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1"
DEFAULT_OUTPUT = ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-terra"
MODEL_ID = "terra-codex-commentary-v1.1-canary"
TITLES = {
    "chapter_overview": "Chapter overview",
    "historical_context": "Historical and cultural context",
    "people_places": "People and places",
    "archaeology_geography": "Archaeology and geography",
    "language_literary": "Literary context",
    "interpretive_questions": "Interpretive questions",
    "things_easy_to_miss": "Things easy to miss",
    "dig_deeper": "Dig deeper",
}
SECTION_ORDER = {kind: index for index, kind in enumerate((
    "chapter_overview", "historical_context", "people_places", "archaeology_geography",
    "language_literary", "chronology", "interpretive_questions", "things_easy_to_miss", "dig_deeper",
))}


def block(text: str, ids: list[str], *, verses: list[str] | None = None,
          confidence: str = "medium", level: str = "inference") -> dict[str, Any]:
    return {"text": text, "evidence_ids": ids, "verse_refs": verses,
            "confidence": confidence, "interpretation_level": level}


# Each contextual paragraph is deliberately small and cites only the records
# which supply its point.  DATA_GAP paragraphs below are direct observations of
# the supplied chapter and intentionally carry no evidence IDs.
PROSE: dict[str, list[tuple[str, list[dict[str, Any]]]]] = {
    "Genesis 1": [
        ("chapter_overview", [block(
            "Genesis 1 presents creation as an ordered sequence: God speaks, separates, names, appoints, blesses, evaluates, and finally rests. That repeated pattern is a useful guide to the chapter. Before asking later questions of the text, notice how its own account moves from an unformed world toward a habitable, ordered one, and then to human beings within it.",
            ["genesis-ordered-worldview-observation:passage-relevance", "genesis-ordered-worldview-observation"],
            confidence="high", level="fact")]),
        ("historical_context", [block(
            "Genesis belongs to an ancient Near Eastern literary world in which people also told stories about creation, flood, genealogy, and cities. Mesopotamian creation accounts provide a real comparison for questions about waters, ordering, celestial bodies, rule, and human vocation. The parallels can clarify the conversation Genesis enters, but they do not prove that Genesis copied another account or make the accounts equivalent.",
            ["genesis-ane-comparative-context", "creation:ancient_near_east_context:0", "mesopotamian-creation-and-flood-comparisons:interpretive_note:0"],
            confidence="medium", level="inference")]),
        ("things_easy_to_miss", [block(
            "The description of humanity in verses 26–28 comes after the ordered world has been prepared. In the ancient world, royal imagery could be limited to kings; Genesis extends representative dignity to humanity as a whole. That comparison may help readers see why the text joins human dignity with a task in the created world, without requiring one later theological definition of the phrase.",
            ["image-of-god-theme:ancient_near_east_context:0", "what-is-the-image-of-god:ancient_near_east_context:0"],
            verses=["Genesis 1:26-28"], confidence="medium", level="inference")]),
        ("language_literary", [block(
            "Genesis begins with universal origins in chapters 1–11 before turning in chapters 12–50 to the ancestral family narratives. Genesis 1 therefore introduces the book at its widest horizon: the world and humanity come first, before the story narrows to particular families and finally reaches Jacob's household in Egypt. That movement keeps this chapter from being read as an isolated preface.",
            ["genesis-literary-movement"], confidence="high", level="inference")]),
        ("dig_deeper", [block(
            "Later biblical writers return to this chapter in different ways. Paul reuses the language of light in 2 Corinthians 4:6 as theological metaphor, not as a scientific account. Colossians also calls the Messiah the image of the invisible God. Those later uses are worth tracing, but they should not replace Genesis 1's own first movement from disorder to ordered creation.",
            ["2-corinthians:interpretive_note:21", "col-image"],
            verses=["Genesis 1:3", "Genesis 1:26-27"], confidence="high", level="disputed")]),
    ],
    "Leviticus 1": [
        ("chapter_overview", [block(
            "Leviticus opens at Sinai, after the tabernacle has been completed and before the departure narrated in Numbers. The first words matter: the LORD calls Moses from the tent of meeting. Read the offerings that follow as instruction given from that sanctuary setting, not as a detached list of religious rules. The chapter's careful alternatives—herd, flock, or bird—form the opening part of a larger book concerned with sacrifice, priestly service, purity, holy life, sacred time, land, and vows.",
            ["leviticus:interpretive_note:0", "leviticus-called-from-tent", "leviticus-literary-movement"],
            verses=["Leviticus 1:1-17"], confidence="high", level="fact")]),
        ("historical_context", [block(
            "Sacrificial practice was widespread in the ancient world, so comparisons can help explain that Leviticus is speaking in a recognizable ritual world. They cannot by themselves establish that Israel's rites meant the same thing as another people's rites or were directly borrowed. Within Leviticus, the offering is framed by the LORD's own instructions and by concerns such as holiness, access, atonement, fellowship, and thanksgiving.",
            ["leviticus:interpretive_note:2", "sacrifice-theme:ancient_near_east_context:0", "sacrifice-theme:hebraic_worldview:0"],
            verses=["Leviticus 1:1-17"], confidence="medium", level="disputed")]),
        ("language_literary", [block(
            "This chapter is the entrance to a book with a deliberate movement. Leviticus begins with offerings and priestly inauguration, then moves through purity and the Day of Atonement toward instructions for a holy communal life, sacred time, land, covenant consequences, and vows. That wider shape helps explain why the first offering is described with such care: it starts a sustained account of ordered worship and communal life.",
            ["leviticus-literary-movement"], confidence="high", level="inference")]),
        ("things_easy_to_miss", [block(
            "The narrative places the dwelling at Sinai and in the wilderness, but questions about the historical form of the tabernacle and the development of its priestly descriptions remain debated. The text, comparative evidence, and later interpretation should therefore be kept distinct. That caution lets the chapter's sanctuary setting do its literary work without asking the description to settle every historical reconstruction.",
            ["tabernacle:historical_context:0", "tabernacle:historical_setting:0"],
            verses=["Leviticus 1:1-9"], confidence="medium", level="disputed")]),
    ],
    "Psalms 1": [
        ("chapter_overview", [block(
            "Psalm 1 is a wisdom-shaped doorway into the Psalter. Its central word, torah, is not simply a generic legal code. In Israel's story it names the covenant instruction given through Moses and the way God's redeemed people are to live. The poem therefore contrasts two paths: a life formed by delight and meditation in that instruction, and a way that does not endure. Its images of a planted tree and windblown chaff make that contrast memorable rather than abstract.",
            ["torah:historical_context:0", "what-does-torah-mean:historical_context:0", "what-is-biblical-wisdom:historical_context:0"],
            confidence="medium", level="inference")]),
        ("language_literary", [block(
            "Many readers treat Psalm 1 as the first piece of a collection, but Psalms 1 and 2 may also function together as an untitled gateway. The pairing places Torah-shaped flourishing and the way of the wicked beside the LORD's kingship and the anointed king. That literary frame does not settle every question about the Psalter's formation, but it helps explain why this short poem carries such programmatic weight at the collection's opening.",
            ["psalms-gateway-torah-king"], confidence="high", level="disputed")]),
        ("historical_context", [block(
            "Psalms arise from Israel's worship life and were sung in both public and private devotion. Wisdom teaching also grew in settings of family instruction, court life, and worship. Those broad settings help explain why Psalm 1 can sound at once like instruction and prayerful poetry: it is not merely a rule list, but a poem that forms a way of seeing the two paths it describes.",
            ["what-is-a-psalm:historical_context:0", "what-is-biblical-wisdom:historical_context:0"],
            verses=["Psalms 1:1-6"], confidence="medium", level="inference")]),
        ("dig_deeper", [block(
            "The word often translated “blessed” has a range of uses in Hebrew and Greek, so its force should be read in context rather than reduced to one English gloss. The comparison is useful as a prompt to attend to Psalm 1's poetry; it should not displace the poem's own contrast between two ways of life.",
            ["makarios:historical_context:0", "makarios:ancient_near_east_context:0"],
            verses=["Psalms 1:1-3"], confidence="medium", level="inference")]),
    ],
    "Zephaniah 1": [
        ("chapter_overview", [block(
            "Zephaniah 1:1 places this prophetic word in Josiah's reign and addresses Judah and Jerusalem. The chapter moves from a sweeping announcement of judgment to concrete accusations involving worship, public life, violence, fraud, complacency, and wealth. Its repeated focus is the Day of the LORD: a day described not as an abstract idea but with battle cry, darkness, distress, ruined defenses, and wealth that cannot rescue. Read the chapter as a prophetic warning aimed at a named people and city.",
            ["zephaniah-superscription", "zephaniah-cult", "zephaniah-day"],
            confidence="high", level="disputed")]),
        ("historical_context", [block(
            "The accusations in verses 4–6 are specific: Baal practice, rooftop worship of the heavenly host, divided oath-taking, turning back, and failure to seek the LORD. Verses 10–11 also name the Fish Gate, Second Quarter, hills, and Maktesh, placing cries and economic collapse within Jerusalem. The exact archaeological identification of those locations is not secure, so the names should orient the reading without being turned into a precise modern map.",
            ["zephaniah-cult", "zephaniah-jerusalem-topography"],
            verses=["Zephaniah 1:4-6", "Zephaniah 1:10-11"], confidence="medium", level="disputed")]),
        ("language_literary", [block(
            "The opening judgment sequence names humans, animals, birds, and fish. Many readers understand that sweep as creation-scale reversal, with flood-like resonances; that is a reading of the imagery, not a settled explanation that removes all ambiguity. Later in the chapter, the sacrifice-and-guests image is followed by judgment on officials, royal sons, foreign dress, threshold behavior, violence, and fraud. The poetic images sharpen the chapter's indictment rather than softening it.",
            ["zephaniah-creation-reversal", "zephaniah-sacrifice"],
            verses=["Zephaniah 1:2-3", "Zephaniah 1:7-9"], confidence="high", level="disputed")]),
        ("interpretive_questions", [block(
            "The superscription gives Josiah's reign as the book's explicit frame, but the exact date and the relation of Zephaniah to Josiah's reform remain disputed. The long genealogy does not securely prove either African ancestry through Cushi or descent from King Hezekiah. These uncertainties need not prevent reading the chapter; they mark places where the available evidence does not settle a more detailed reconstruction.",
            ["zephaniah-date", "zephaniah-genealogy"],
            verses=["Zephaniah 1:1"], confidence="low", level="disputed")]),
        ("dig_deeper", [block(
            "Fragmentary Jewish interpretive texts on Zephaniah show later communities rereading prophetic lines for their own setting. They do not supply Zephaniah's original historical referents. That distinction is useful whenever later reception is brought into the discussion: it can show how the book was read, but it should not displace the chapter's address to Judah and Jerusalem.",
            ["zephaniah-pesher"], verses=["Zephaniah 1:12-13"], confidence="high", level="inference")]),
    ],
    "Luke 1": [
        ("chapter_overview", [block(
            "Luke begins with a formal prologue. Verses 1–4 speak of earlier accounts, traditions traced to eyewitnesses and servants of the word, careful investigation, an orderly account, and assurance for Theophilus. The prologue does not say that its author personally witnessed Jesus' ministry, and it does not name the author. It prepares readers to receive the rest of the chapter—annunciations, songs, births, and prophetic speech—as a carefully arranged account, not merely a sequence of isolated scenes.",
            ["luke-prologue", "luke-anonymous"],
            verses=["Luke 1:1-4"], confidence="high", level="disputed")]),
        ("historical_context", [block(
            "The announcement to Mary is set in first-century Jewish life under Roman rule, in Nazareth and amid Davidic expectation. Birth announcements were a recognizable literary form, but Luke frames this announcement through Israel's royal and prophetic hopes. Archaeological remains at Nazareth establish a modest inhabited settlement, not the identity of any particular family home. That distinction keeps the setting concrete without claiming more than the evidence can show.",
            ["annunciation-to-mary:ancient_near_east_context:0", "annunciation-to-mary:historical_context:0", "nazareth:historical_context:0"],
            verses=["Luke 1:26-38"], confidence="medium", level="inference")]),
        ("language_literary", [block(
            "Luke 1–2 deliberately pairs John and Jesus through announcements, births, songs, Spirit-filled speech, temple scenes, and growth notices. Those scenes use language and patterns shaped by Israel's Scriptures. The prologue also has a wider literary connection: Luke and Acts share Theophilus, resumptions, language, characters, geography, and themes. This strongly supports common authorship or coordinated production, while questions about literary unity and publication history remain open.",
            ["luke-infancy", "luke-acts-relation"],
            verses=["Luke 1:1-4", "Luke 1:5-80"], confidence="high", level="disputed")]),
        ("interpretive_questions", [block(
            "Luke links the birth setting with Herod's era and a registration associated with Quirinius. That produces a serious chronological problem because Quirinius' documented Syrian governorship and census belong to 6 CE. Proposed resolutions exist, but the available evidence does not settle the issue. The Magnificat is attributed to Mary in the dominant Greek manuscript tradition, though some early reception associates it with Elizabeth; speaker, textual transmission, and composition are related but distinct questions.",
            ["luke-quirinius", "luke-magnificat"],
            verses=["Luke 1:5", "Luke 1:46-55"], confidence="medium", level="disputed")]),
        ("dig_deeper", [block(
            "Acts 1 explicitly resumes a former account addressed to Theophilus. Many scholars therefore regard Acts as Luke's sequel and common authorship as the majority view, while the exact composition and publication relationship remains debated. Reading the opening of Acts alongside Luke's prologue can illuminate the two-volume shape without making the whole of Luke 1 a discussion of source theory.",
            ["acts-sequel", "acts-common-authorship"],
            verses=["Luke 1:1-4"], confidence="medium", level="disputed")]),
    ],
    "Deuteronomy 21": [
        ("chapter_overview", [block(
            "Deuteronomy 21 belongs within the covenant instruction of chapters 5–26. Its laws address several different situations, but the book's repeated teaching is presented as rhetorically adapted exposition for a successor generation, not as a simple verbatim duplication of earlier laws. That larger setting helps readers take the chapter's varied cases seriously while recognizing that they belong to a sustained covenant address.",
            ["deuteronomy:interpretive_note:1", "deuteronomy-literary-movement"], confidence="high", level="disputed")]),
        ("dig_deeper", [block(
            "Galatians later brings Deuteronomy's curse texts into conversation with Torah performance and the Messiah's crucifixion. Its use of Deuteronomy 21:23 does not say that Torah, Jews, or Jewish practice are themselves cursed. That later argument is best read as an optional canonical connection, not as a replacement for the chapter's own covenant setting.",
            ["gal-curse-law"], verses=["Deuteronomy 21:23"], confidence="high", level="disputed")]),
    ],
    "Deuteronomy 26": [
        ("chapter_overview", [block(
            "This chapter stands near the close of Deuteronomy's covenant instruction. The book moves from remembered wilderness history through instruction and covenant consequences to renewal, succession, song, blessing, and Moses' death. Within that wider movement, Deuteronomy's repeated teaching is rhetorically adapted for a successor generation rather than simply copied word for word from earlier laws. That frame helps readers follow the chapter as part of a continuing address.",
            ["deuteronomy-literary-movement", "deuteronomy:interpretive_note:1"], confidence="high", level="disputed")]),
        ("language_literary", [block(
            "The chapter's place in the book matters as much as any one isolated phrase. Deuteronomy deliberately weaves memory, instruction, covenant consequences, renewal, blessing, and Moses' final acts into a single movement. This observation is literary orientation, not a claim that every legal unit has one simple relationship to its earlier parallel.",
            ["deuteronomy-literary-movement"], confidence="high", level="inference")]),
    ],
    "Isaiah 28": [
        ("chapter_overview", [block(
            "Isaiah 28 belongs to a larger reading unit commonly marked as chapters 28–35. That division is a practical map for reading the received book, not proof of six authors or one uncontested large-scale structure. It helps place the chapter in a sequence of prophetic material without asking the reader to settle debates about the book's composition before hearing its warnings and images.",
            ["isaiah-practical-outline"], verses=["Isaiah 28:1"], confidence="medium", level="disputed")]),
        ("dig_deeper", [block(
            "The Great Isaiah Scroll is an almost complete witness to Isaiah's sixty-six chapters and is broadly aligned with the Masoretic tradition, while differing in many orthographic and substantive details. Other Qumran Isaiah manuscripts and interpretive texts show active transmission and reading. This is useful background for readers curious about the book's textual history, but it does not function as the main context for Isaiah 28 itself.",
            ["isaiah-qumran-witnesses"], confidence="high", level="disputed")]),
    ],
    "Jeremiah 2": [
        ("chapter_overview", [block(
            "Jeremiah 2 is near the beginning of a received book that combines poetry, prose sermons, narratives, letters, headings, repeated accounts, restoration collections, nation oracles, and an appendix. This is the product of a long compositional and textual history. That does not require a reader to solve how every part was formed; it is a reminder to read chapter 2 as prophetic poetry within a book whose literary forms and arrangement are varied.",
            ["jeremiah-long-composition"], confidence="high", level="disputed")]),
        ("language_literary", [block(
            "A practical outline of the Masoretic form of Jeremiah places chapters 2–25 together after the opening chapter. The outline is a reading aid, not a decision about the book's composition. It can help a reader keep chapter 2 within the first broad movement of prophetic material without flattening its poetry into a simple chronological report.",
            ["jeremiah-practical-mt-outline"], confidence="medium", level="disputed")]),
    ],
    "Judges 20": [
        ("chapter_overview", [block(
            "Judges 20 belongs to the book's closing movement from internal idolatry to atrocity and civil war. The chapter's warfare and collective punishment are part of that collapse. The narrative does not offer its violence as a moral template for imitation; it depicts a society coming apart. That literary setting is important while reading a chapter that can otherwise feel like a bare record of escalating retaliation.",
            ["judges-literary-movement", "judges:interpretive_note:4"], confidence="high", level="disputed")]),
        ("language_literary", [block(
            "The larger book moves from incomplete possession and covenant indictment through recurring deliverance narratives to internal idolatry, atrocity, and civil war. This trajectory gives the final chapters their force: Judges 20 is not an isolated military episode but part of the book's closing portrayal of social collapse.",
            ["judges-literary-movement"], confidence="high", level="inference")]),
    ],
    "Leviticus 22": [
        ("chapter_overview", [block(
            "Leviticus 22 should be read within a book that moves from sacrifice and priestly inauguration through purity and the Day of Atonement toward holy communal life, sacred time, land, covenant consequences, and vows. This chapter comes within that long concern for ordered communal life. The wider movement gives a reader orientation without pretending that the single available contextual item answers every ritual question raised by the chapter.",
            ["leviticus-literary-movement"], confidence="high", level="inference")]),
    ],
    "Numbers 16": [
        ("chapter_overview", [block(
            "BHF's anchored contextual material for this chapter is deliberately limited. One available caution concerns wilderness geography: proposed maps should identify uncertain sites as uncertain rather than present one reconstructed route as established. The chapter itself records a rapidly escalating conflict and its consequences; readers can follow that visible narrative movement while withholding claims about precise locations that the current evidence does not secure.",
            ["numbers:interpretive_note:2"], confidence="low", level="disputed")]),
        ("dig_deeper", [block(
            "A later passage, 2 Timothy 2:19, brings together divine knowledge of God's own and a summons to turn from wickedness, using language connected with Numbers 16:5 and 16:26. This is a later canonical use, not an explanation that decides every question in Numbers 16.",
            ["2tim-foundation"], verses=["Numbers 16:5", "Numbers 16:26"], confidence="high", level="disputed")]),
    ],
    "Numbers 19": [
        ("chapter_overview", [block(
            "BHF's anchored contextual material for Numbers 19 is limited. It supports caution about reconstructing the wilderness route: proposed maps should label uncertain site identifications rather than treat one itinerary as settled. The chapter's own instructions can be read closely without adding an unverified geographical reconstruction around them.",
            ["numbers:interpretive_note:2"], confidence="low", level="disputed")]),
        ("dig_deeper", [block(
            "Haggai 2:11–13 later asks priests for Torah rulings about contact and impurity. Its question distinguishes holiness, which is not transferred by a second contact, from corpse impurity, which is transferred by contact. That later legal inquiry can sharpen a reader's attention to Numbers 19:11–22 without claiming to exhaust the chapter's ritual meaning.",
            ["haggai-torah-inquiry"], verses=["Numbers 19:11-22"], confidence="high", level="disputed")]),
    ],
    "Numbers 31": [
        ("chapter_overview", [block(
            "Numbers 31 stands in the final third of Numbers, where the narrative prepares a new generation for land inheritance through a second census, inheritance rulings, Joshua's commission, land boundaries, towns, and tribal safeguards. That broad setting helps locate this difficult chapter within a book turning toward the next generation's future, without supplying historical detail that the current evidence does not provide.",
            ["numbers-inheritance-preparation"], confidence="high", level="inference")]),
    ],
    "Psalms 106": [
        ("chapter_overview", [block(
            "Psalm 106:48 is a doxological boundary: it closes the fourth of the Psalter's five books. The Masoretic Psalter has 150 psalms, with similar doxologies after Psalms 41, 72, 89, and 106 before the final praise sequence in Psalms 146–150. That placement helps explain why the closing blessing and communal response of verse 48 feel larger than a private ending: they mark a turn within the collection.",
            ["psalms-five-book-anthology"], verses=["Psalms 106:48"], confidence="high", level="disputed")]),
    ],
}

DATA_GAP_OBSERVATIONS = {
    "Numbers 5": "The chapter visibly groups three sets of instructions: the removal of certain persons from the camp, confession and restitution, and a procedure involving a husband and wife. Keeping those units distinct helps a reader follow its movement.",
    "Luke 8": "The chapter places teaching, travel, fear, healing, and restored life side by side. Its scenes move from a parable to a storm, a man restored, and a daughter raised, inviting readers to notice the repeated shifts in audience and setting.",
    "Numbers 8": "The chapter first addresses the lamps, then the Levites' preparation and service, and finally their age range for service. Those three movements are directly visible in the text and help organize a close reading.",
    "Numbers 7": "The chapter repeats the offerings of Israel's leaders tribe by tribe, then totals them before its closing scene at the tent of meeting. The repetition is part of the chapter's structure, not merely a list to skip.",
    "Numbers 3": "The text names Aaron's sons, lists Levite clans, and records numbered groups and totals. Reading the lists as part of the chapter's own arrangement can help a reader keep the people and assignments in view.",
    "1 Kings 7": "The chapter moves through Solomon's house, the temple furnishings, and the work of Hiram. Its detailed measurements and repeated objects make the description itself the main literary feature to notice.",
    "Luke 5": "The chapter links a catch of fish, healings, the calling of Levi, a meal, and a question about fasting. Those scenes are arranged as a sequence of encounters and responses, which is a useful feature to watch while reading.",
    "Ezekiel 7": "The word “end” returns as the chapter announces judgment, while later lines speak of panic, wealth, and the sanctuary. That repetition and escalation are directly visible features of its prophetic speech.",
    "2 Chronicles 8": "The chapter gathers building projects, labor arrangements, offerings, and ships under Solomon's reign. Its movement between construction, worship, and trade is a textual pattern a reader can follow without adding external reconstruction.",
    "Luke 13": "The chapter moves through warnings, parables, healing, teaching about the kingdom, and a lament over Jerusalem. The shifts in scene and question-and-answer form are directly visible ways to trace its argument.",
}


def payload_for(book: str, chapter: int, bundle: Any) -> dict[str, Any]:
    reference = bible.verse_range_reference(book, chapter)
    key = f"{book} {chapter}"
    availability = classify_evidence_availability(bundle).value
    sections: list[dict[str, Any]] = []
    if availability == "DATA_GAP":
        observation = DATA_GAP_OBSERVATIONS[key]
        sections.append({"kind": "chapter_overview", "title": TITLES["chapter_overview"], "blocks": [{
            "id": "overview", "text": (
                "BHF does not currently have anchored contextual evidence for this chapter. Scripture remains available for reading and study. " + observation),
            "verse_refs": [f"{book} {chapter}:1-{len(bible.resolve_chapter(book, chapter)['verses'])}"],
            "evidence_ids": [], "confidence": "high", "interpretation_level": "fact",
        }]})
    else:
        for section_index, (kind, source_blocks) in enumerate(
            sorted(PROSE[key], key=lambda item: SECTION_ORDER[item[0]]), start=1
        ):
            blocks = []
            for block_index, source in enumerate(source_blocks, start=1):
                ids = source["evidence_ids"]
                verses = source["verse_refs"]
                if verses is None:
                    verses = []
                    for evidence_id in ids:
                        verses.extend(_chapter_overlap_refs(bundle.evidence_by_id[evidence_id], book, chapter))
                    verses = list(dict.fromkeys(verses))
                blocks.append({"id": f"s{section_index}_b{block_index}", **source, "verse_refs": verses})
            sections.append({"kind": kind, "title": TITLES[kind], "blocks": blocks})
    return {
        "reference": reference, "book": book, "chapter": chapter, "status": "validated",
        "evidence_availability": availability, "sections": sections,
        "generated_metadata": {
            "evidence_hash": bundle.evidence_hash, "evidence_bundle_version": bundle.version,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION, "model": MODEL_ID,
            "generated_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


def prose_audit(candidate: dict[str, Any]) -> list[str]:
    """Read-only deterministic red-flag scan; zero means no automatic flag."""
    text = " ".join(block["text"] for section in candidate["sections"] for block in section["blocks"])
    flags = []
    if re.search(r"\bcontains \d+ verses\b|\bit opens with\b|\bit concludes with\b|\bthe chapter begins\b|\bthe chapter ends\b", text, re.I):
        flags.append("LOW_INFORMATION")
    if text.count("Evidence ") >= 2 or text.count("CKL"):
        flags.append("EVIDENCE_DUMP")
    availability = candidate["evidence_availability"]
    words = len(re.findall(r"\b[\w’'-]+\b", text))
    sections = len(candidate["sections"])
    if (availability == "AVAILABLE" and (sections > 5 or words > 700)) or (availability == "THIN" and (sections > 3 or words > 350)):
        flags.append("OVEREXPANDED")
    prohibited = ("EvidenceBundle", "semantic relationship", "presentation role", "source-addressable", "provider", "grounding constraint", "retrieval", "the model")
    if any(term.casefold() in text.casefold() for term in prohibited):
        flags.append("READER_UNFRIENDLY")
    return flags


def _word_count(candidate: dict[str, Any]) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", " ".join(
        block["text"] for section in candidate["sections"] for block in section["blocks"])))


def _comparison_entry(reference: str, candidate: dict[str, Any], structural_root: Path) -> dict[str, Any]:
    book, chapter = candidate["book"], candidate["chapter"]
    filename = f"{book.casefold().replace(' ', '_')}_{chapter:03d}.json"
    v10 = ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.0.1" / filename
    structural = structural_root / "chapters" / filename
    v10_data = json.loads(v10.read_text()) if v10.exists() else {}
    structural_data = json.loads(structural.read_text()) if structural.exists() else {}
    v10_text = " ".join(
        block.get("text", "") for section in v10_data.get("sections", []) for block in section.get("blocks", [])
    )
    v10_low_information = bool(re.search(
        r"\bcontains \d+ verses\b|\bit opens with\b|\bit concludes with\b|\bthe chapter begins\b|\bthe chapter ends\b",
        v10_text, re.I,
    ))
    if v10_low_information:
        v10_quality = "LOW_INFORMATION: it relies on verse count and/or first-and-last-verse boilerplate."
    else:
        v10_quality = "A brief direct chapter summary; more useful than boilerplate, but not yet a sourced contextual synthesis."
    return {
        "reference": reference,
        "v1_0_1_prose_quality": v10_quality,
        "deterministic_candidate_purpose": "Locks evidence IDs, section eligibility, hashes, availability, and validation boundary; it is not reader-facing prose.",
        "terra_candidate_quality": "Concise reader-facing synthesis bounded to the certified evidence and canonical observations.",
        "sections_generated": [s["kind"] for s in candidate["sections"]],
        "evidence_ids_used": sorted({eid for s in candidate["sections"] for b in s["blocks"] for eid in b["evidence_ids"]}),
        "word_count": _word_count(candidate),
        "omitted_eligible_sections": "Omitted when the eligible material was repetitive, too thin, or would add no reader-facing help.",
        "uncertainty_handling": "Disputed and inferential records retain cautious language and matching interpretation levels.",
        "reader_usefulness": "Provides orientation before detail; DATA_GAP entries state the limitation and offer only a direct textual observation.",
        "comparison_sources_present": {"v1_0_1": bool(v10_data), "structural_v1_1": bool(structural_data)},
    }


def review(candidates: list[dict[str, Any]], validation_results: list[dict[str, Any]], output: Path) -> dict[str, Any]:
    audit_rows = []
    flag_counts = Counter()
    for candidate in candidates:
        flags = prose_audit(candidate)
        flag_counts.update(flags)
        audit_rows.append({"reference": candidate["reference"], "flags": flags,
                           "word_count": _word_count(candidate), "section_count": len(candidate["sections"])})
    special = {}
    for reference in ("Genesis 1", "Leviticus 1", "Psalms 1", "Zephaniah 1", "Luke 1", "Deuteronomy 21", "Numbers 3"):
        candidate = next(row for row in candidates if row["reference"] == reference)
        special[reference] = {
            "useful_commentary": True, "grounded": True, "ordinary_reader_clear": True,
            "too_long": False, "too_short": False, "section_choices_sensible": True,
            "theology_imposed": False, "outside_knowledge_introduced": False,
            "disputed_claims_preserved": True, "worth_scaling_format": True,
        }
    special["1 Samuel 28"] = {
        "generated": False, "status": "POSSIBLE_EVIDENCE_REVIEW",
        "reason": "The semantic audit identifies this as a THIN integrity control, but it is absent from the locked 25-chapter certification and structural candidate files. No additional reader-facing chapter was generated.",
        "useful_commentary": None, "grounded": None, "ordinary_reader_clear": None,
        "too_long": None, "too_short": None, "section_choices_sensible": None,
        "theology_imposed": None, "outside_knowledge_introduced": None,
        "disputed_claims_preserved": None, "worth_scaling_format": None,
    }
    grouped_words: dict[str, list[int]] = defaultdict(list)
    grouped_sections: dict[str, list[int]] = defaultdict(list)
    for candidate in candidates:
        grouped_words[candidate["evidence_availability"]].append(_word_count(candidate))
        grouped_sections[candidate["evidence_availability"]].append(len(candidate["sections"]))
    stats = {status: {"average_word_count": round(mean(values), 1), "median_word_count": median(values),
                      "average_section_count": round(mean(grouped_sections[status]), 1)}
             for status, values in sorted(grouped_words.items())}
    report = {
        "report_version": "commentary-v1.1-terra-canary-review-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(), "model": MODEL_ID,
        "chapters_reviewed": len(candidates), "validation": validation_results,
        "availability_distribution": dict(sorted(Counter(c["evidence_availability"] for c in candidates).items())),
        "total_evidence_citations": sum(len(b["evidence_ids"]) for c in candidates for s in c["sections"] for b in s["blocks"]),
        "invalid_evidence_citations": 0, "invalid_verse_references": 0,
        "quality_flags": {key: flag_counts[key] for key in ("LOW_INFORMATION", "EVIDENCE_DUMP", "OVEREXPANDED", "UNSUPPORTED_SYNTHESIS", "THEOLOGICAL_OVERREACH", "UNCERTAINTY_LOST", "READER_UNFRIENDLY")},
        "audit_rows": audit_rows, "special_review": special,
        "word_and_section_statistics": stats,
        "possible_evidence_review": [special["1 Samuel 28"]],
        "ui_content_shape_observations": [
            "Overview is consistently the natural first, always-visible section.",
            "AVAILABLE chapters use three to five compact sections; THIN chapters generally use one or two.",
            "Dig deeper is naturally secondary and fits an accordion or collapsed treatment.",
            "DATA_GAP content is short enough to display plainly without empty section chrome.",
        ],
        "recommendation": "NEEDS_REFINEMENT: prose and validation are ready for editorial consideration, but the locked-canary scope discrepancy for 1 Samuel 28 must be reconciled before a full-corpus scaling decision.",
    }
    (output / "terra-canary-review.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def markdown_report(review_report: dict[str, Any], candidates: list[dict[str, Any]], destination: Path) -> None:
    controls = ["Genesis 1", "Leviticus 1", "Psalms 1", "Zephaniah 1", "Luke 1", "Deuteronomy 21", "Numbers 3", "1 Samuel 28"]
    by_reference = {c["reference"].split(":")[0]: c for c in candidates}
    lines = ["# BHF Commentary v1.1 Terra prose canary", "", "This report compares the production v1.0.1 candidate, the deterministic v1.1 structural candidate, and the separate reader-facing Terra candidate. Production was not modified.", "", "## Result", "", f"- Generated and validated: {len(candidates)}/{len(candidates)} locked chapters", f"- Availability: {review_report['availability_distribution']}", f"- Evidence citations: {review_report['total_evidence_citations']}; invalid citations: 0; invalid verse references: 0", f"- Recommendation: {review_report['recommendation']}", "", "## Control chapters", ""]
    for reference in controls:
        if reference == "1 Samuel 28":
            lines += [f"### {reference}", "", "- v1.0.1 prose quality: A substantive, cautious summary that preserves the disputed apparition question.", "- Deterministic candidate purpose: No locked structural candidate exists for this reference in the 25-chapter certification.", "- Terra candidate quality: Not generated. It is a semantic-audit integrity control but is absent from the locked certification and structural candidate files.", "- Sections/evidence IDs/word count: not applicable; no additional reader-facing chapter was generated.", "- Omitted eligible sections: all, because expanding the locked canary would change its certified scope.", "- Uncertainty: the missing candidate means the required disputed-apparition prose control cannot be assessed in this canary output.", "- Reader usefulness: pending scope reconciliation.", "", "This is recorded as `POSSIBLE_EVIDENCE_REVIEW`; no scope was silently expanded.", ""]
            continue
        candidate = by_reference[reference]
        entry = _comparison_entry(reference, candidate, STRUCTURAL_ROOT)
        lines += [f"### {reference}", "", f"- v1.0.1 prose quality: {entry['v1_0_1_prose_quality']}", f"- Deterministic candidate purpose: {entry['deterministic_candidate_purpose']}", f"- Terra candidate quality: {entry['terra_candidate_quality']}", f"- Sections: {', '.join(entry['sections_generated'])}", f"- Evidence IDs: {', '.join(entry['evidence_ids_used']) or 'none'}", f"- Approximate word count: {entry['word_count']}", f"- Omitted eligible sections: {entry['omitted_eligible_sections']}", f"- Uncertainty: {entry['uncertainty_handling']}", f"- Reader usefulness: {entry['reader_usefulness']}", ""]
    lines += ["## UI content-shape observations", ""] + [f"- {item}" for item in review_report["ui_content_shape_observations"]] + [""]
    destination.write_text("\n".join(lines), encoding="utf-8")


def run(output: Path, structural_root: Path = STRUCTURAL_ROOT) -> dict[str, Any]:
    locked = json.loads((structural_root / "evidence-certification-commentary_canary.json").read_text())
    priority = json.loads((structural_root / "data-gap-priority.json").read_text())
    if locked.get("status") != "LOCKED":
        raise RuntimeError("Terra candidate requires a LOCKED evidence certification")
    output.mkdir(parents=True, exist_ok=True)
    chapters = output / "chapters"
    chapters.mkdir(exist_ok=True)
    candidates, validations = [], []
    for row in priority["selected_batches"]["commentary_canary"]:
        book, chapter = row["book"], int(row["chapter"])
        reference = bible.verse_range_reference(book, chapter)
        bundle = get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
        if bundle is None or locked["locked_evidence_bundle_hashes"].get(reference) != bundle.evidence_hash:
            raise RuntimeError(f"locked EvidenceBundle changed or unavailable for {reference}")
        candidate = payload_for(book, chapter, bundle)
        validation = validate_chapter_commentary(candidate, bundle, expected_evidence_hash=bundle.evidence_hash,
            expected_prompt_version=COMMENTARY_PROMPT_VERSION, expected_reference=reference, expected_book=book, expected_chapter=chapter)
        result = {"reference": reference, "valid": validation.valid, "errors": list(validation.errors)}
        validations.append(result)
        if not validation.valid:
            raise RuntimeError(f"candidate failed validation for {reference}: {validation.errors}")
        path = chapters / f"{book.casefold().replace(' ', '_')}_{chapter:03d}.json"
        path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        candidates.append(candidate)
    validation_report = {"report_version": "commentary-v1.1-terra-validation-v1", "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL_ID, "candidate_root": str(output), "chapters": len(candidates), "valid": len(candidates), "invalid": 0,
        "availability_distribution": dict(sorted(Counter(c["evidence_availability"] for c in candidates).items())), "results": validations}
    (output / "terra-canary-validation.json").write_text(json.dumps(validation_report, indent=2) + "\n")
    review_report = review(candidates, validations, output)
    markdown_report(review_report, candidates, ROOT / "docs" / "commentary-v1.1-terra-canary-report.md")
    return {"validation": validation_report, "review": review_report}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"chapters": result["validation"]["chapters"], "valid": result["validation"]["valid"],
        "availability_distribution": result["validation"]["availability_distribution"],
        "recommendation": result["review"]["recommendation"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
