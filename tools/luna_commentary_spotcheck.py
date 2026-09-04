#!/usr/bin/env python3
"""Development-only Luna synthesis for the repaired Genesis spot-check.

This script deliberately bypasses CommentaryGenerator.generate(): Luna is the
model executing the development task. It still uses BHF retrieval, bundle
construction, validation, authoritative metadata, atomic storage, and the
normal progress rescan.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent import bible
from bhf_agent.chapter_commentary.builder import CommentaryBuilder
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
CHAPTERS = (13, 16, 19, 25, 34)
GENESIS_EVIDENCE = "genesis-literary-movement"
GALATIANS_EVIDENCE = "gal-allegory"


def block(block_id: str, text: str, verses: list[str], evidence: list[str], *, level: str = "fact") -> dict:
    return {
        "id": block_id,
        "text": text,
        "verse_refs": verses,
        "evidence_ids": evidence,
        "confidence": "high",
        "interpretation_level": level,
    }


def section(kind: str, title: str, blocks: list[dict]) -> dict:
    return {"kind": kind, "title": title, "blocks": blocks}


def payloads() -> dict[int, list[dict]]:
    return {
        13: [
            section("chapter_overview", "Abram and Lot separate", [
                block("overview", "Genesis 13 follows Abram and Lot back from Egypt into the South and then to the area between Bethel and Ai. Their flocks and herds become too numerous for them to remain together, so Abram proposes separation rather than continued strife. Lot chooses the well-watered Plain of the Jordan and moves toward Sodom, while Abram remains in Canaan and receives a renewed promise of land and descendants before settling by the oaks of Mamre at Hebron.", ["Genesis 13:1-18"], [GENESIS_EVIDENCE]),
            ]),
            section("interpretive_questions", "Choice, promise, and perspective", [
                block("choice", "The chapter places Lot's visual assessment of the Plain beside the divine words to Abram. Lot sees a well-watered region, while Abram is told to lift his eyes in every direction and to walk through the land. The text distinguishes the immediate attraction of a place from the promise spoken to Abram, without requiring the reader to treat every geographic or moral implication as an archaeological conclusion.", ["Genesis 13:8-18"], [GENESIS_EVIDENCE], level="inference"),
            ]),
        ],
        16: [
            section("chapter_overview", "Hagar, Ishmael, and the God who sees", [
                block("overview", "Genesis 16 narrates Sarai's decision to give Hagar, her Egyptian handmaid, to Abram because Sarai has no child. Hagar conceives, conflict follows, and Sarai deals harshly with her until Hagar flees. At a fountain in the wilderness on the way to Shur, the angel of Jehovah addresses Hagar, promises to multiply her seed, names her son Ishmael, and hears her affliction. Hagar returns, bears Ishmael, and Abram is eighty-six years old.", ["Genesis 16:1-16"], [GENESIS_EVIDENCE]),
            ]),
            section("interpretive_questions", "A later reading remains a later reading", [
                block("later-reading", "The supplied BHF evidence records that Galatians later calls its Hagar-and-Sarah construction an allegory and maps women, sons, mountains, covenants, and Jerusalems within a contested argument. That claim can illuminate a later reception of the Hagar-Sarah material, but it should not be merged with Genesis 16's own narrative setting or presented as though Paul supplied the chapter's original voice. The exact correspondences and their implications remain disputed in the supplied evidence.", ["Genesis 16:1-16"], [GALATIANS_EVIDENCE], level="disputed"),
            ]),
        ],
        19: [
            section("chapter_overview", "Rescue from Sodom and the aftermath", [
                block("overview", "Genesis 19 moves from the arrival of two angels at Sodom to Lot's attempted protection of his guests, the threatened destruction of the city, and the urgent escape of Lot, his wife, and his two daughters. Lot lingers, the visitors bring the family outside the city, and Lot is permitted to flee to Zoar. Jehovah then overthrows Sodom and Gomorrah and the Plain; Lot's wife looks back and becomes a pillar of salt. The chapter closes with Lot and his daughters in the mountain and the births of Moab and Ben-ammi.", ["Genesis 19:1-38"], [GENESIS_EVIDENCE]),
            ]),
            section("things_easy_to_miss", "The narrative's repeated movement", [
                block("movement", "The chapter repeatedly contrasts staying with leaving: Lot sits in Sodom's gate, urges the visitors to stay, lingers when warned, asks for Zoar instead of the mountain, and later leaves Zoar for the mountain because he fears to remain there. The text also says that God remembered Abraham and sent Lot out of the overthrow. These are narrative observations; the supplied BHF evidence does not justify importing later cross-reference claims into the original setting.", ["Genesis 19:1-30"], [GENESIS_EVIDENCE], level="inference"),
            ]),
        ],
        25: [
            section("chapter_overview", "Abraham's death and Isaac's sons", [
                block("overview", "Genesis 25 records Abraham's children by Keturah, his distinction between Isaac and the sons of his concubines, and his death at 175. Isaac and Ishmael bury him in the cave of Machpelah. The chapter then records Ishmael's twelve sons and their settlements before turning to Isaac and Rebekah, whose twins struggle in the womb. Esau is described as a hunter and Jacob as a quiet man in tents; their conflict over the birthright ends with Esau eating and departing after selling it to Jacob.", ["Genesis 25:1-34"], [GENESIS_EVIDENCE]),
            ]),
            section("people_places", "Names, kinship, and the birthright", [
                block("kinship", "The chapter organizes several family lines by names, generations, settlements, and burial. It gives Isaac the central inheritance while describing gifts and eastward sending for the sons of the concubines. The birth narrative then names Esau and Jacob, and the final scene explains the name Edom through the red pottage and frames the birthright exchange through Esau's hunger and Jacob's demand for an oath. The supplied contextual evidence is broad literary context, so no additional historical reconstruction is asserted.", ["Genesis 25:5-34"], [GENESIS_EVIDENCE], level="inference"),
            ]),
        ],
        34: [
            section("chapter_overview", "Dinah, Shechem, and violent retaliation", [
                block("overview", "Genesis 34 begins with Dinah going out to see the daughters of the land and Shechem taking her and lying with her. Hamor and Shechem seek marriage, while Jacob's sons answer with guile by requiring circumcision of the city's males. On the third day, when the men are sore, Simeon and Levi kill the males, retrieve Dinah, and the other sons plunder the city and take its people and goods. Jacob fears the consequences among the surrounding inhabitants, while his sons answer by appealing to what was done to their sister.", ["Genesis 34:1-31"], [GENESIS_EVIDENCE]),
            ]),
            section("interpretive_questions", "Description is not approval", [
                block("moral-tension", "The chapter gives no simple narrator's endorsement of the actions that follow Dinah's violation. It records Shechem's desire, the brothers' deception, the slaughter, the plunder, Jacob's fear, and the brothers' final question. Commentary should preserve those tensions and distinguish the canonical account of what the characters did from an unsupported claim that the text resolves every moral or cultural question surrounding their actions.", ["Genesis 34:1-31"], [GENESIS_EVIDENCE], level="inference"),
            ]),
        ],
    }


def run() -> None:
    config = AgentConfig(
        adapter="openai_compatible",
        base_url="luna-development://local",
        model="luna-codex-development",
    )
    stamper = CommentaryGenerator(config)
    chapters = payloads()
    for chapter in CHAPTERS:
        bundle = get_chapter_evidence_bundle("Genesis", chapter)
        if bundle is None:
            raise RuntimeError(f"No EvidenceBundle for Genesis {chapter}")
        reference = bible.verse_range_reference("Genesis", chapter)
        request = CommentaryGenerationRequest(
            "Genesis", chapter, reference, bundle.evidence_hash, force_regenerate=True
        )
        generated_metadata = stamper._authoritative_metadata(request, bundle).to_dict()
        raw = {
            "reference": reference,
            "book": "Genesis",
            "chapter": chapter,
            "status": CommentaryStatus.PENDING.value,
            "sections": chapters[chapter],
            "generated_metadata": generated_metadata,
        }
        missing = sorted({
            evidence_id
            for item in chapters[chapter]
            for generated_block in item["blocks"]
            for evidence_id in generated_block["evidence_ids"]
            if evidence_id not in bundle.evidence_by_id
        })
        if missing:
            raise RuntimeError(f"Genesis {chapter} missing evidence IDs: {missing}")
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
                generated_metadata=stamper._authoritative_metadata(request, bundle),
                failure_reason="Validator accepted no sections",
                validation_errors=list(validation.errors),
                validation_warnings=[],
            )
        path = save_commentary(commentary, STORE)
        accepted_blocks = sum(len(item.blocks) for item in commentary.sections)
        rejected_sections = sum(not result.valid for result in validation.section_results)
        rejected_blocks = sum(
            not result.valid
            for result in validation.section_results
            for result in result.block_results
        )
        print(
            f"{reference}: status={commentary.status} sections={len(commentary.sections)} "
            f"blocks={accepted_blocks} rejected_sections={rejected_sections} "
            f"rejected_blocks={rejected_blocks} errors={len(validation.errors)} file={path}",
            flush=True,
        )
        for error in validation.errors:
            print(f"  ERROR {error}", flush=True)

    progress = CommentaryBuilder(STORE, config=config).rescan_progress(check_evidence=False)
    print(f"Progress: {progress.to_dict()}", flush=True)


if __name__ == "__main__":
    run()
