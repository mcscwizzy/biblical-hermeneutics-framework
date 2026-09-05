"""Development-only Luna synthesis harness for the Genesis 1-10 canary.

This intentionally does not invoke CommentaryGenerator.generate() or any AI
adapter. It retrieves BHF's real evidence bundles, validates the in-process
Luna payloads, and uses the normal atomic commentary storage.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent import bible
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.generator import CommentaryGenerator
from bhf_agent.chapter_commentary.models import (
    COMMENTARY_PROMPT_VERSION,
    ChapterCommentary,
    CommentaryGenerationRequest,
    CommentaryStatus,
)
from bhf_agent.chapter_commentary.storage import save_commentary
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from bhf_agent.config import AgentConfig


STORE = Path(".bhf-data/bhf-commentary")


def block(block_id, text, verses, evidence, confidence="medium", level="fact"):
    return {
        "id": block_id,
        "text": text,
        "verse_refs": verses,
        "evidence_ids": evidence,
        "confidence": confidence,
        "interpretation_level": level,
    }


def section(kind, title, blocks):
    return {"kind": kind, "title": title, "blocks": blocks}


def payloads():
    return {
        1: [
            section("chapter_overview", "Ordered creation and human vocation", [
                block("overview_1", "Genesis 1 presents God creating, separating, naming, blessing, and evaluating the ordered world. The chapter moves from light, sky, land, and vegetation to living creatures and finally to humanity, whose male-and-female creation is joined to a vocation of fruitfulness and dominion.", ["Genesis 1:1-31"], ["genesis-ordered-worldview-observation"], "high"),
            ]),
            section("language_literary", "Repetition and sequence", [
                block("literary_1", "The repeated pattern of divine speech, result, evaluation, and the evening-and-morning formula gives the chapter a deliberately ordered presentation. The text itself emphasizes sequence and differentiation rather than supplying a modern scientific description.", ["Genesis 1:3-31"], ["genesis-ordered-worldview-observation"], "high", "inference"),
            ]),
            section("people_places", "Image-bearing humanity", [
                block("humanity_1", "Humanity is created in the image and likeness of God, explicitly as male and female. The chapter connects that identity with blessing, responsibility toward the earth, and care or rule over other living creatures.", ["Genesis 1:26-30"], ["image-of-god-theme:hebraic_worldview:0"]),
            ]),
        ],
        2: [
            section("chapter_overview", "The garden, command, and companionship", [
                block("overview_1", "Genesis 2 first marks the completion and sanctifying of the seventh day, then focuses on the man formed from dust, placed in Eden, and given work and a command. The narrative proceeds to the animals, the woman, and the man’s recognition of a one-flesh relationship.", ["Genesis 2:1-25"], ["creation-doctrine:ancient_near_east_context:0"]),
            ]),
            section("people_places", "Eden and its named rivers", [
                block("places_1", "The chapter names Eden, the garden, and four rivers—Pishon, Gihon, Hiddekel, and Euphrates—while also naming Havilah, Cush, and Assyria. These names are part of the chapter’s geography, but the supplied evidence does not warrant identifying the garden’s exact modern location.", ["Genesis 2:8-14"], ["creation-doctrine:ancient_near_east_context:0"], level="inference"),
            ]),
            section("interpretive_questions", "Work, command, and human relationship", [
                block("questions_1", "The man is placed in the garden to dress and keep it before the prohibition concerning the tree of the knowledge of good and evil. The chapter therefore holds together human responsibility, a defined limit, and the recognition that the man is not meant to be alone; readers should distinguish these narrative observations from later theological systems.", ["Genesis 2:15-25"], ["creation-doctrine-framework:hebraic_worldview:0"], level="inference"),
            ]),
        ],
        3: [
            section("chapter_overview", "Disobedience and expulsion", [
                block("overview_1", "Genesis 3 narrates the serpent’s questioning, the woman’s and man’s eating, their changed awareness, God’s interrogation, judgments, clothing, and expulsion from Eden. The chapter ends with the way to the tree of life guarded by cherubim and a turning sword.", ["Genesis 3:1-24"], ["the-fall:historical_context:0"]),
            ]),
            section("interpretive_questions", "A root narrative of estrangement", [
                block("questions_1", "The supplied BHF evidence reads Genesis 3 as a foundational account of human estrangement and death. That contextual reading fits the chapter’s movement from hiding and blame to painful consequences and separation from the garden, while it does not settle every later question about the serpent or the exact mechanics of the event.", ["Genesis 3:7-24"], ["the-fall:historical_context:0", "the-fall:ancient_near_east_context:0"], level="inference"),
            ]),
        ],
        4: [
            section("chapter_overview", "Cain, Abel, and widening violence", [
                block("overview_1", "Genesis 4 contrasts Cain, a worker of the ground, with Abel, a keeper of sheep. After Cain kills Abel, the chapter follows judgment and protection for Cain, his settlement and descendants, Lamech’s violent boast, and the birth of Seth followed by the beginning of calling on the name of Jehovah.", ["Genesis 4:1-26"], ["cain:historical_context:0"]),
            ]),
            section("things_easy_to_miss", "The ground as witness", [
                block("ground_1", "The ground is not merely Cain’s occupation. It receives Abel’s blood, no longer yields its strength to Cain, and becomes part of Cain’s fugitive condition. The repeated ground language connects the murder to the created setting in which both brothers worked.", ["Genesis 4:8-14"], ["cain:ancient_near_east_context:0"], level="inference"),
            ]),
            section("interpretive_questions", "Sin at the threshold", [
                block("questions_1", "The warning that sin is crouching at the door and that Cain must rule over it comes before the murder. The text presents Cain’s anger and action as morally significant without explaining why Abel’s offering was regarded and Cain’s was not; that unanswered detail should remain an interpretive question.", ["Genesis 4:3-8"], ["cain:historical_context:0"], level="inference"),
            ]),
        ],
        5: [
            section("chapter_overview", "The generations from Adam to Noah", [
                block("overview_1", "Genesis 5 records a genealogy from Adam through Seth, Enosh, Kenan, Mahalalel, Jared, Enoch, Methuselah, Lamech, and Noah, then names Noah’s sons Shem, Ham, and Japheth. Its repeated pattern of begetting, years, sons and daughters, and death is interrupted by Enoch’s walking with God and by Lamech’s hope connected with Noah.", ["Genesis 5:1-32"], ["why-are-genealogies-included:historical_context:0"]),
            ]),
            section("people_places", "Image, likeness, and remembered lineage", [
                block("lineage_1", "The chapter opens by recalling that humanity was made in God’s likeness and that Adam’s son was in Adam’s own likeness and image. The genealogy thus links family succession with remembered identity, while the supplied BHF evidence describes genealogies as a way of preserving belonging, rights, and memory.", ["Genesis 5:1-3"], ["image-of-god-theme:historical_context:0", "why-are-genealogies-included:ancient_near_east_context:0"]),
            ]),
        ],
        6: [
            section("chapter_overview", "Corruption, judgment, and Noah’s preservation", [
                block("overview_1", "Genesis 6 describes growing human population, the sons of God and daughters of men, the Nephilim, pervasive wickedness, and a world filled with violence. God announces judgment, but Noah finds favor, walks with God, receives instructions for an ark, and is included with his family and living creatures in a covenant promise of preservation.", ["Genesis 6:1-22"], ["the-flood:historical_context:0", "the-flood:hebraic_worldview:0"], level="inference"),
            ]),
            section("interpretive_questions", "The sons of God and the Nephilim", [
                block("questions_1", "The chapter mentions the sons of God, the daughters of men, and the Nephilim, but the supplied evidence does not establish one uncontested interpretation of these figures. They should therefore remain a defined but unresolved feature of the passage rather than become a confident claim about divine beings, a divine council, or a particular hybrid origin.", ["Genesis 6:1-4"], ["genesis-ane-comparative-context"], level="disputed"),
            ]),
            section("historical_context", "Flood traditions and careful comparison", [
                block("comparison_1", "BHF places Genesis 1–11 within an ancient Near Eastern literary environment in which creation, flood, genealogy, and city-building traditions were also discussed. A supplied Mesopotamian comparison includes boat construction, preservation of life, birds, landing, and sacrifice, but the evidence explicitly treats comparison as contextual and disputed rather than proof of direct borrowing or identification with an archaeological deposit.", [], ["genesis-ane-comparative-context", "gilgamesh-tablet-xi-flood-comparison:passage-relevance"], level="disputed"),
            ]),
        ],
        7: [
            section("chapter_overview", "Entry into judgment", [
                block("overview_1", "Genesis 7 records Noah, his household, and the animals entering the ark; the rain, the rising waters, the covering of the mountains, and the death of life on dry land; and the waters prevailing for one hundred and fifty days. The repeated statements that Noah acted as commanded keep obedience and preservation at the center of the narrative.", ["Genesis 7:1-24"], ["the-flood:historical_context:0"]),
            ]),
            section("things_easy_to_miss", "The ark as a boundary of life", [
                block("ark_1", "The chapter distinguishes clean animals from animals not described as clean, gives different numbers for them, and repeatedly describes male-and-female pairs entering the ark. It also says that Jehovah shut Noah in, a detail that marks the ark’s boundary as part of the narrative’s preservation scene rather than merely a human construction.", ["Genesis 7:2-16"], ["the-flood:hebraic_worldview:0"], level="inference"),
            ]),
        ],
        8: [
            section("chapter_overview", "Waters recede and Noah leaves the ark", [
                block("overview_1", "Genesis 8 moves from God remembering Noah to the assuaging and retreat of the waters. The ark rests on the mountains of Ararat, birds test whether the ground is habitable, Noah removes the covering when the ground is dry, and God commands the occupants to leave and multiply.", ["Genesis 8:1-19"], ["the-flood:historical_context:0"]),
            ]),
            section("language_literary", "Repeated waiting and measured movement", [
                block("timing_1", "The chapter’s time markers—one hundred and fifty days, the seventh and tenth months, forty days, repeated seven-day waits, and the first and second months—slow the account and make the retreat of the waters a measured process. The text presents observation through the raven, the dove, and the visible drying of the ground rather than an abrupt transition.", ["Genesis 8:3-14"], ["the-flood:historical_context:0"], level="fact"),
            ]),
            section("interpretive_questions", "Memory, worship, and the earth’s rhythms", [
                block("worship_1", "After leaving the ark, Noah builds an altar and offers from the clean animals and birds. The divine response addresses both the continuing evil inclination of humanity and the continuing regularity of seedtime, harvest, cold, heat, summer, winter, day, and night; the passage joins judgment’s aftermath to ongoing creaturely life.", ["Genesis 8:20-22"], ["the-flood:hebraic_worldview:0"], level="inference"),
            ]),
        ],
        9: [
            section("chapter_overview", "Covenant with Noah and all flesh", [
                block("overview_1", "Genesis 9 blesses Noah and his sons, sets boundaries around eating blood and shedding human blood, and establishes a covenant with them and every living creature. The bow in the cloud is given as the covenant token. The chapter then closes with Noah’s vineyard, Ham’s conduct, the responses of Shem and Japheth, Noah’s words concerning Canaan, and Noah’s death.", ["Genesis 9:1-29"], ["the-flood:historical_context:0", "what-is-covenant:historical_context:0"]),
            ]),
            section("interpretive_questions", "Life, blood, and the image of God", [
                block("life_1", "The prohibition against eating flesh with its life, identified as blood, is followed by accountability for bloodshed and the statement that humans are made in the image of God. The supplied BHF evidence connects the post-flood account with human accountability and divine image, while the chapter itself does not invite the reader to treat human life as disposable.", ["Genesis 9:3-7"], ["the-flood:hebraic_worldview:0", "image-of-god-theme:hebraic_worldview:0"], level="inference"),
            ]),
            section("historical_context", "The bow as covenant sign", [
                block("sign_1", "The covenant is made not only with Noah and his descendants but also with every living creature. BHF’s supplied covenant evidence describes signs as markers of covenant identity and obligation and cautions against treating them as magical forces; in this chapter, the bow functions within God’s promise not to use a flood to destroy all flesh again.", [], ["what-is-a-covenant-sign:historical_context:0", "what-is-a-covenant-sign:ancient_near_east_context:0"], level="inference"),
            ]),
        ],
        10: [
            section("chapter_overview", "The families of the nations", [
                block("overview_1", "Genesis 10 traces the families of Japheth, Ham, and Shem after the flood. It organizes the material by families, tongues, lands, and nations, includes named peoples and places, highlights Cush’s son Nimrod and his kingdoms, and closes by repeating that these families were divided in the earth after the flood.", ["Genesis 10:1-32"], ["why-are-genealogies-included:historical_context:0"]),
            ]),
            section("people_places", "Names, lands, and limits of identification", [
                block("names_1", "The chapter names regions and settlements including Shinar, Babel, Erech, Accad, Assyria, Nineveh, Canaan, Sidon, and many others. BHF’s retrieval supplies a general genealogy-context claim about families preserving lineage and memory, but it does not support mapping every listed name to a certain modern location; the list should therefore be read as the chapter’s own people-and-place framework.", ["Genesis 10:5-32"], ["why-are-genealogies-included:ancient_near_east_context:0"], level="inference"),
            ]),
            section("historical_context", "Nimrod and the city-building notice", [
                block("nimrod_1", "Nimrod is introduced as a mighty one and hunter, and the beginning of his kingdom is associated with Babel, Erech, Accad, and Calneh before the notice turns toward Assyria and Nineveh. The supplied Babel evidence allows comparison with Mesopotamian monumental cities but specifically says that Genesis does not name a particular excavated ziggurat; no archaeological identification is asserted here.", [], ["babel:ancient_near_east_context:0", "babel:historical_context:0"], level="inference"),
            ]),
        ],
    }


def run():
    config = AgentConfig(
        adapter="openai_compatible",
        base_url="luna-development://local",
        model="luna-codex-development",
    )
    stamper = CommentaryGenerator(config)
    all_payloads = payloads()
    for chapter in range(1, 11):
        bundle = get_chapter_evidence_bundle("Genesis", chapter)
        if bundle is None:
            raise RuntimeError(f"No evidence bundle for Genesis {chapter}")
        for item in all_payloads[chapter]:
            for generated_block in item["blocks"]:
                missing = [eid for eid in generated_block["evidence_ids"] if eid not in bundle.evidence_by_id]
                if missing:
                    raise RuntimeError(f"Genesis {chapter} missing evidence: {missing}")
        reference = bible.verse_range_reference("Genesis", chapter)
        request = CommentaryGenerationRequest("Genesis", chapter, reference, bundle.evidence_hash, force_regenerate=True)
        metadata = stamper._authoritative_metadata(request, bundle).to_dict()
        raw = {"reference": reference, "book": "Genesis", "chapter": chapter, "status": "pending", "sections": all_payloads[chapter], "generated_metadata": metadata}
        validation = validate_chapter_commentary(
            raw,
            bundle,
            expected_evidence_hash=bundle.evidence_hash,
            expected_prompt_version=COMMENTARY_PROMPT_VERSION,
            expected_reference=reference,
            expected_book="Genesis",
            expected_chapter=chapter,
        )
        if validation.valid:
            status = CommentaryStatus.VALIDATED.value
        elif validation.partial:
            status = CommentaryStatus.PARTIAL.value
        else:
            status = CommentaryStatus.NEEDS_REVIEW.value
        if validation.commentary:
            commentary = ChapterCommentary(
                reference=reference,
                book="Genesis",
                chapter=chapter,
                status=status,
                sections=list(validation.accepted_sections),
                generated_metadata=validation.commentary.generated_metadata,
                failure_reason=None if validation.valid else "Some generated material was rejected",
                validation_errors=list(validation.errors),
                validation_warnings=[],
            )
        else:
            commentary = ChapterCommentary(
                reference=reference,
                book="Genesis",
                chapter=chapter,
                status=CommentaryStatus.FAILED.value,
                sections=[],
                generated_metadata=metadata,
                failure_reason="Validator accepted no sections",
                validation_errors=list(validation.errors),
                validation_warnings=[],
            )
        path = save_commentary(commentary, STORE)
        accepted_blocks = sum(len(s.blocks) for s in commentary.sections)
        rejected_sections = sum(not result.valid for result in validation.section_results)
        rejected_blocks = sum(not result.valid for result in validation.section_results for result in result.block_results)
        print(f"{reference}: status={commentary.status} sections={len(commentary.sections)} blocks={accepted_blocks} rejected_sections={rejected_sections} rejected_blocks={rejected_blocks} errors={len(validation.errors)} file={path}", flush=True)
        for error in validation.errors:
            print(f"  ERROR {error}", flush=True)


if __name__ == "__main__":
    run()
