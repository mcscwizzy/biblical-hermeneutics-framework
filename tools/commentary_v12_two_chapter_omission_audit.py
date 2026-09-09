#!/usr/bin/env python3
"""Build the immutable forensic audit for the prompt-1.7 dense chapters.

This tool is deliberately read-only with respect to production inputs.  It
reads the frozen prompt-1.7 diagnostic, its historical prompt-1.6 comparison,
and the current evidence/synthesis authorities only to verify hashes and add
human-readable evidence claims to the audit.  It never calls the scorer,
changes a contract, regenerates a response, or changes CKL/synthesis data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.commentary.production.inputs import prepare_chapter
from framework.commentary.production.models import sha256_bytes, sha256_json, write_immutable


PROMPT_17_ID = "renderer-remediation-prompt-1.7-selection-breadth-7e1f844705a27ef5d2a1"
PROMPT_16_ID = "renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-15f2be7cfcc60bb5ea31"
PROMPT_17_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates" / PROMPT_17_ID
PROMPT_16_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates" / PROMPT_16_ID
ARTIFACT_VERSION = "commentary-v1.2-two-chapter-omission-audit-v1"
CHAPTERS = (
    ("1 Corinthians 14", "1 Corinthians", 14, "003_1_corinthians_014", "016_1_corinthians_014"),
    ("Revelation 21", "Revelation", 21, "005_revelation_021", "021_revelation_021"),
)


JUDGMENTS: dict[str, dict[str, dict[str, Any]]] = {
    "1 Corinthians 14": {
        "idea_cluster_118df255769d": {
            "concept": "The disputed women-or-wives silence commands must be read with manuscript placement, the letter's assumption that women pray and prophesy, and the chapter's contextual use of silence for other speakers.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["interpretive_questions: Participation, Discernment, and Silence / block_6"],
            "closest_prose": "Block 6 directly explains the textual variation, the three silence contexts, and the disputed scope of the command.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Explicit and repeated in early and late interpretive/why-it-matters units.",
            "mixed_with_unrelated": True,
        },
        "idea_cluster_2d1bfc883aaf": {
            "concept": "Chapter 13 functions inside the gifts discussion: love's patience, truthfulness, and noncoercion govern correction, gifts, and leadership.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["surrounding_passages: The Love Chapter in Its Literary Setting / block_1"],
            "closest_prose": "Block 1 places the love chapter between chapters 12 and 14 and explains its role in the gifts discussion.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Two surrounding-passage units are adjacent in the middle of the synthesis.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_5b79903d041c": {
            "concept": "The chapter's central reader-level pattern is intelligible, accountable, and participatory speech: tongues remain uncertain and require interpretation, prophecy builds up and is tested, and order protects access and peace.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": [
                "interpretive_questions: Tongues, Prophecy, and Understanding / block_2",
                "interpretive_questions: Tongues, Prophecy, and Understanding / block_3",
                "interpretive_questions: Tongues, Prophecy, and Understanding / block_4",
                "interpretive_questions: Participation, Discernment, and Silence / block_5",
                "why_it_matters: Why the Chapter's Boundaries Matter / block_7",
                "why_it_matters: Why the Chapter's Boundaries Matter / block_8",
            ],
            "closest_prose": "Blocks 2 through 5 explain the tongues, prophecy, sign, participation, and order material; blocks 7-8 carry its medical and safeguarding boundaries.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Explicitly repeated across twelve interpretive and why-it-matters units, spanning early through late positions.",
            "mixed_with_unrelated": True,
        },
        "idea_cluster_621a6a3ced67": {
            "concept": "Assembly order serves edification, intelligibility, learning, encouragement, self-control, and peace, while claimed revelation remains open to communal weighing and correction.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["interpretive_questions: Participation, Discernment, and Silence / block_5"],
            "closest_prose": "Block 5 explains the order-purpose and communal evaluation of prophecy.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Explicit, with interpretive and why-it-matters copies at early and late positions.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_6ae289a10247": {
            "concept": "Chapter 13 is literary context for the gifts discussion, and manuscript witnesses show transmission variation without allowing one witness or a preferred theology to settle partition claims.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["surrounding_passages: The Love Chapter in Its Literary Setting / block_1"],
            "closest_prose": "Block 1 directly explains the chapter 13 setting; its cited synthesis also carries the relevant transmission context.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Five surrounding-passage units occur together in the middle of the prompt.",
            "mixed_with_unrelated": True,
        },
        "idea_cluster_018650e9fc74": {
            "concept": "The chapter's linked questions about tongues, prophecy, communal discernment, and the disputed silence of women or wives; the silence commands are contextual rather than a settled permanent ban.",
            "prose_presence": "PARTIAL_EQUIVALENT",
            "closest_prose_locations": [
                "interpretive_questions: Tongues, Prophecy, and Understanding / block_2",
                "interpretive_questions: Tongues, Prophecy, and Understanding / block_3",
                "interpretive_questions: Tongues, Prophecy, and Understanding / block_4",
                "interpretive_questions: Participation, Discernment, and Silence / block_5",
                "interpretive_questions: Participation, Discernment, and Silence / block_6",
                "why_it_matters: Why the Chapter's Boundaries Matter / block_7",
                "why_it_matters: Why the Chapter's Boundaries Matter / block_8",
            ],
            "closest_prose": "The response expresses the component ideas across its tongues, prophecy, order, silence, and safeguarding blocks, but cites parallel synthesis clusters instead of this aggregate cluster.",
            "omission_reason": "This is a broad six-unit aggregate with many overlapping facts. Its component ideas are already represented through parallel clusters, so the frozen scorer records a cluster miss even though the reader-facing prose is substantially equivalent.",
            "classification": "POSSIBLE_SCORING_MISMATCH",
            "cause_domain": "SCORING_SEMANTIC",
            "closest_rendered_clusters": [
                "idea_cluster_5b79903d041c",
                "idea_cluster_118df255769d",
                "idea_cluster_621a6a3ced67",
            ],
            "boundary_assessment": "SEMANTICALLY_EQUIVALENT",
            "scorer_distinct_but_prose_equivalent": True,
            "prompt_assessment": "Explicit but broad and distributed across duplicated interpretive and why-it-matters units.",
            "mixed_with_unrelated": True,
        },
        "idea_cluster_5aa8529568c8": {
            "concept": "Acts depicts recognizable diaspora languages at Pentecost, while the exact relationship between that scene and Corinthian tongues remains debated.",
            "prose_presence": "PARTIAL_EQUIVALENT",
            "closest_prose_locations": [
                "interpretive_questions: Tongues, Prophecy, and Understanding / block_2",
            ],
            "closest_prose": "The response warns that Acts 2 must not define Corinthian tongues in advance, which preserves the comparison's caution but does not state the positive Pentecost language observation.",
            "omission_reason": "The only synthesis unit is a surrounding-passage comparison at the middle of the prompt. A much larger interpretive cluster also contains Acts 2 material, so the renderer retained the caution without selecting this separately cited historical comparison.",
            "classification": "POSSIBLE_SCORING_MISMATCH",
            "cause_domain": "PROMPT_SALIENCE_AND_SCORING_SEMANTIC",
            "closest_rendered_clusters": ["idea_cluster_5b79903d041c"],
            "boundary_assessment": "PARTIALLY_OVERLAPPING",
            "scorer_distinct_but_prose_equivalent": True,
            "prompt_assessment": "Explicit single unit, middle-positioned, surrounding material, and lower weight than the larger interpretive cluster.",
            "mixed_with_unrelated": False,
        },
    },
    "Revelation 21": {
        "idea_cluster_20992f8315ab": {
            "concept": "New Jerusalem is the biblical story's final hope, reshaping Zion imagery after judgment and exile.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["historical_context: Historical Context / block_2"],
            "closest_prose": "Block 2 explicitly calls New Jerusalem the final hope after judgment and exile.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "One explicit historical unit in the late-middle input.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_243e0cbb763d": {
            "concept": "The temple sequence moves from wilderness tabernacle through Solomon, destruction, restored Second Temple worship, and Jesus' temple fulfillment to God's direct dwelling in New Jerusalem.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["chronology: Temple and Presence Across the Story / block_6"],
            "closest_prose": "Block 6 gives the full temple chronology and its completion in New Jerusalem.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Explicit chronology units at the beginning and late significance position.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_3729f716ef6f": {
            "concept": "Revelation recomposes Ezekielian throne, measuring, battle, city, river, and tree imagery within its own literary sequence.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["surrounding_passages: Surrounding Passages / block_9"],
            "closest_prose": "Block 9 directly explains the wider Ezekielian reuse.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "One explicit surrounding-passage unit late in the synthesis.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_4e3d8895d7fe": {
            "concept": "Jerusalem's history moves from Jebusite city to Davidic capital and temple center, then through exile and return into messianic expectation.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["historical_context: Historical Context / block_2"],
            "closest_prose": "Block 2 directly traces Jerusalem's historical trajectory and expectation.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Two historical units occur in the late-middle synthesis.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_568f3b9a8d27": {
            "concept": "The ending joins new creation and God's dwelling with a communal, international horizon in which nations walk by the city's light and kings bring their glory.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["why_it_matters: Why It Matters / block_7"],
            "closest_prose": "Block 7 directly holds cosmic renewal, divine dwelling, nations, and kings together.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Interpretive and why-it-matters copies occur late in the synthesis.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_842f9f3cf63c": {
            "concept": "New Jerusalem combines city, bride, sanctuary, Eden, and renewed-Zion imagery while Revelation reworks Israel's Scriptures.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["surrounding_passages: Surrounding Passages / block_9"],
            "closest_prose": "Block 9 directly explains the overlapping images and scriptural reuse.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Two surrounding-passage units occur late in the synthesis.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_919fb0668c76": {
            "concept": "Sanctuary images share dwelling and holiness language but remain distinct across tabernacle, temples, Christological/community metaphors, heavenly sanctuary, and new creation; later readings cannot justify antisemitism or institutional immunity.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["why_it_matters: Why It Matters / block_8"],
            "closest_prose": "Block 8 directly preserves the distinctions and the ethical boundary.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Interpretive and why-it-matters copies appear together near the end.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_b4f1b03ed9c8": {
            "concept": "Ancient temples functioned as divine dwelling and royal-cultic centers, while Israel's temple joined covenant holiness, sacred access, sacrifice, priesthood, pilgrimage, and Second Temple authority disputes.",
            "prose_presence": "DIRECT",
            "closest_prose_locations": ["cultural_context: Cultural Context / block_5"],
            "closest_prose": "Block 5 directly explains the ancient temple comparison, Israel's covenant holiness, and Second Temple setting.",
            "omission_reason": None,
            "classification": None,
            "cause_domain": None,
            "closest_rendered_clusters": [],
            "boundary_assessment": "DISTINCT_AND_RENDERED",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Explicit cultural and why-it-matters units at early and late positions.",
            "mixed_with_unrelated": True,
        },
        "idea_cluster_0eab3d8c1fbd": {
            "concept": "Jerusalem carries a distinctive royal, cultic, pilgrimage, imperial-pressure, repentance, judgment, and restored-worship meaning; the Second Temple setting makes the name New Jerusalem historically dense.",
            "prose_presence": "PARTIAL_EQUIVALENT",
            "closest_prose_locations": [
                "historical_context: Historical Context / block_2",
                "cultural_context: Cultural Context / block_5",
            ],
            "closest_prose": "Block 2 gives Jerusalem's historical trajectory and block 5 gives the temple's Second Temple setting, but neither presents Jerusalem's own royal-cultic and pilgrimage significance as a distinct reader-facing idea.",
            "omission_reason": "The relevant cultural units occur in the early-middle synthesis, but their why-it-matters parallel is the final unit. The flat input also contains adjacent Jerusalem history and temple-culture alternatives, allowing the renderer to cover neighboring concepts and stop without this distinct cultural framing.",
            "classification": "PROMPT_SALIENCE_WEAKNESS",
            "cause_domain": "PROMPT_INPUT_PRESENTATION",
            "closest_rendered_clusters": ["idea_cluster_4e3d8895d7fe", "idea_cluster_b4f1b03ed9c8"],
            "boundary_assessment": "PARTIALLY_OVERLAPPING",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Explicit but distributed across two cultural units and a late significance unit; competes with Jerusalem history and temple context.",
            "mixed_with_unrelated": True,
        },
        "idea_cluster_440d7c941173": {
            "concept": "Ancient temples were royal-cultic centers, while Israel's temple was distinguished by covenant holiness and atonement under one God.",
            "prose_presence": "SEMANTIC_EQUIVALENT",
            "closest_prose_locations": [
                "cultural_context: Cultural Context / block_5",
            ],
            "closest_prose": "Block 5 says ancient temples were divine dwellings and royal-cultic centers, then contrasts Israel's covenant holiness, sacrifice, priesthood, purity, and consecrated access.",
            "omission_reason": "The response selected a parallel temple-culture cluster and expressed the same contrast with different synthesis and evidence IDs. The scorer does not credit this parallel cluster.",
            "classification": "LIKELY_SEMANTIC_REDUNDANCY",
            "cause_domain": "SCORING_SEMANTIC",
            "closest_rendered_clusters": ["idea_cluster_b4f1b03ed9c8"],
            "boundary_assessment": "SEMANTICALLY_EQUIVALENT",
            "scorer_distinct_but_prose_equivalent": True,
            "prompt_assessment": "Explicit, but three near-parallel temple-culture units compete with the rendered temple-culture cluster immediately nearby.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_a3997c8def39": {
            "concept": "The new creation completes a canonical sequence from good creation and human vocation through the disordering fall, worship's confession of the Creator, Christ's role in creation, and the promised renewal.",
            "prose_presence": "PARTIAL_EQUIVALENT",
            "closest_prose_locations": [
                "cultural_context: Cultural Context / block_3",
                "why_it_matters: Why It Matters / block_7",
            ],
            "closest_prose": "The response explains creation's goodness and the broad new-heaven-and-earth hope, but does not give the chronological sequence or explain why the renewal is more than a new city.",
            "omission_reason": "The chronology is split between an early one-fact unit, a second early sequence unit, and a late why-it-matters duplicate. Nearby cultural creation material is easier to render as a paragraph, while the chronological arc is not surfaced as one compact reader-level unit.",
            "classification": "SYNTHESIS_PRESENTATION_WEAKNESS",
            "cause_domain": "PROMPT_INPUT_PRESENTATION",
            "closest_rendered_clusters": ["idea_cluster_568f3b9a8d27", "idea_cluster_14dc4f566ee0"],
            "boundary_assessment": "PARTIALLY_OVERLAPPING",
            "scorer_distinct_but_prose_equivalent": False,
            "prompt_assessment": "Explicit but split across early and late units; competes with broader creation-culture and cosmic-renewal concepts.",
            "mixed_with_unrelated": True,
        },
        "idea_cluster_b9f92a2e8940": {
            "concept": "Temple imagery develops from tabernacle instruction through Solomon's temple, exile and return, and the New Testament's rereading of sacred space.",
            "prose_presence": "SEMANTIC_EQUIVALENT",
            "closest_prose_locations": [
                "chronology: Temple and Presence Across the Story / block_6",
            ],
            "closest_prose": "Block 6 gives the same temple sequence and its completion in New Jerusalem, citing the parallel chronology cluster.",
            "omission_reason": "The single historical unit is a concise parallel to the rendered temple chronology and is naturally covered by that block's prose.",
            "classification": "LIKELY_SEMANTIC_REDUNDANCY",
            "cause_domain": "SCORING_SEMANTIC",
            "closest_rendered_clusters": ["idea_cluster_243e0cbb763d"],
            "boundary_assessment": "SEMANTICALLY_EQUIVALENT",
            "scorer_distinct_but_prose_equivalent": True,
            "prompt_assessment": "Explicit single unit in the middle of a large group of overlapping temple histories.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_c4b6236fce0e": {
            "concept": "Temple language in the ancient Near East concerns divine presence and royal order, while Israel's temple emphasizes holiness, covenant, atonement, mediation, pilgrimage, and Second Temple life.",
            "prose_presence": "SEMANTIC_EQUIVALENT",
            "closest_prose_locations": [
                "cultural_context: Cultural Context / block_5",
            ],
            "closest_prose": "Block 5 covers the ancient temple comparison, Israelite holiness, sacred access, and Second Temple pilgrimage and authority context through the parallel temple-symbol cluster.",
            "omission_reason": "The response renders the same cultural family under a different parallel cluster. The frozen scorer is provenance-based and does not infer that the prose covers this cluster's alternate evidence ancestry.",
            "classification": "LIKELY_SEMANTIC_REDUNDANCY",
            "cause_domain": "SCORING_SEMANTIC",
            "closest_rendered_clusters": ["idea_cluster_b4f1b03ed9c8", "idea_cluster_440d7c941173"],
            "boundary_assessment": "SEMANTICALLY_EQUIVALENT",
            "scorer_distinct_but_prose_equivalent": True,
            "prompt_assessment": "Explicit but duplicate cultural units at early and late positions; directly competes with rendered temple culture.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_e29624b106d8": {
            "concept": "The vision reuses familiar ancient city and temple imagery but transforms it around God's direct presence.",
            "prose_presence": "SEMANTIC_EQUIVALENT",
            "closest_prose_locations": [
                "chronology: Temple and Presence Across the Story / block_6",
                "surrounding_passages: Surrounding Passages / block_9",
            ],
            "closest_prose": "Block 6 expresses direct divine presence replacing a separate temple, while block 9 explains the wider city, sanctuary, Eden, and renewed-Zion imagery.",
            "omission_reason": "The one cultural unit is covered compositionally by two rendered blocks, but neither cites its unit ID. This is a plausible scorer-versus-prose boundary rather than a wholly absent reader idea.",
            "classification": "POSSIBLE_SCORING_MISMATCH",
            "cause_domain": "SCORING_SEMANTIC",
            "closest_rendered_clusters": ["idea_cluster_243e0cbb763d", "idea_cluster_842f9f3cf63c", "idea_cluster_919fb0668c76"],
            "boundary_assessment": "PARTIALLY_OVERLAPPING",
            "scorer_distinct_but_prose_equivalent": True,
            "prompt_assessment": "Explicit single unit in the early-middle input, competing with several directly adjacent city, temple, sanctuary, and presence concepts.",
            "mixed_with_unrelated": True,
        },
        "idea_cluster_e56f67d45e11": {
            "concept": "The temple grows from tabernacle patterns, reaches classical form under Solomon, survives exilic memory, and is rebuilt in the Second Temple period.",
            "prose_presence": "SEMANTIC_EQUIVALENT",
            "closest_prose_locations": [
                "chronology: Temple and Presence Across the Story / block_6",
            ],
            "closest_prose": "Block 6 gives the same historical development, adding its completion in New Jerusalem.",
            "omission_reason": "Three duplicate historical units are naturally consolidated into the rendered temple chronology block; the scorer credits only the cited parallel cluster.",
            "classification": "LIKELY_SEMANTIC_REDUNDANCY",
            "cause_domain": "SCORING_SEMANTIC",
            "closest_rendered_clusters": ["idea_cluster_243e0cbb763d"],
            "boundary_assessment": "SEMANTICALLY_EQUIVALENT",
            "scorer_distinct_but_prose_equivalent": True,
            "prompt_assessment": "Explicit but triplicated across middle and late synthesis positions among many temple-history units.",
            "mixed_with_unrelated": False,
        },
        "idea_cluster_ebe19d7ddf91": {
            "concept": "Temple symbolism spans tabernacle worship, monarchy, Second Temple Judaism, Jesus' temple actions, and New Testament imagery for Christ and the church.",
            "prose_presence": "SEMANTIC_EQUIVALENT",
            "closest_prose_locations": [
                "chronology: Temple and Presence Across the Story / block_6",
                "why_it_matters: Why It Matters / block_8",
            ],
            "closest_prose": "Block 6 covers the tabernacle-to-Jesus temple sequence, and block 8 names Christological and community sanctuary metaphors while preserving distinctions.",
            "omission_reason": "The historical-symbolic cluster is rendered through two adjacent parallel explanations with different synthesis IDs; its reader-facing content is not genuinely absent.",
            "classification": "LIKELY_SEMANTIC_REDUNDANCY",
            "cause_domain": "SCORING_SEMANTIC",
            "closest_rendered_clusters": ["idea_cluster_243e0cbb763d", "idea_cluster_919fb0668c76"],
            "boundary_assessment": "SEMANTICALLY_EQUIVALENT",
            "scorer_distinct_but_prose_equivalent": True,
            "prompt_assessment": "Explicit but split between middle historical and late significance units; competes with several temple chronology clusters.",
            "mixed_with_unrelated": True,
        },
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _prompt_parts(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    synthesis = json.loads(lines[lines.index("COMPILED CHAPTER SYNTHESIS:") + 1])
    citations = json.loads(lines[lines.index("PERMITTED EVIDENCE CITATIONS:") + 1])
    return synthesis, citations, {
        "line_count": len(lines),
        "word_count": sum(len(line.split()) for line in lines),
        "synthesis_json_sha256": sha256_bytes(json.dumps(synthesis, ensure_ascii=False, separators=(",", ":")).encode()),
        "citation_json_sha256": sha256_bytes(json.dumps(citations, ensure_ascii=False, separators=(",", ":")).encode()),
    }


def _band(first: int, last: int, count: int) -> str:
    def one(value: int) -> str:
        ratio = value / max(count, 1)
        return "early" if ratio <= 1 / 3 else "middle" if ratio <= 2 / 3 else "late"

    first_band, last_band = one(first), one(last)
    return first_band if first_band == last_band else f"{first_band}->{last_band}"


def _location(section: dict[str, Any], block: dict[str, Any]) -> str:
    return f"{section['kind']}: {section['title']} / {block['id']}"


def _response_blocks(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    commentary = parsed["validated_commentary"]
    result = []
    for section in commentary["sections"]:
        for block in section["blocks"]:
            result.append(
                {
                    "location": _location(section, block),
                    "section_kind": section["kind"],
                    "title": section["title"],
                    "block_id": block["id"],
                    "text": block["text"],
                    "evidence_ids": block.get("evidence_ids", []),
                    "synthesis_ids": block.get("synthesis_ids", []),
                }
            )
    return result


def _consumed_locations(parsed: dict[str, Any]) -> dict[str, list[str]]:
    locations: dict[str, list[str]] = {}
    for block in _response_blocks(parsed):
        for synthesis_id in block["synthesis_ids"]:
            locations.setdefault(synthesis_id, []).append(block["location"])
    return locations


def _evidence_records(prepared: Any, evidence_ids: set[str]) -> dict[str, dict[str, Any]]:
    records = {}
    for evidence_id in sorted(evidence_ids):
        item = prepared.bundle.evidence_by_id[evidence_id]
        records[evidence_id] = {
            "id": item.id,
            "claim": item.claim,
            "category": item.category,
            "confidence": item.confidence,
            "source_ids": sorted(item.source_ids),
            "passage_anchors": sorted(item.passage_anchors),
        }
    return records


def _synthesis_records(
    synthesis: dict[str, Any],
    synthesis_ids: set[str],
    evidence_positions: dict[str, int],
) -> dict[str, dict[str, Any]]:
    units = {unit["id"]: unit for unit in synthesis["units"]}
    positions = {unit["id"]: index for index, unit in enumerate(synthesis["units"], 1)}
    records = {}
    for synthesis_id in sorted(synthesis_ids):
        unit = units[synthesis_id]
        ordinal = positions[synthesis_id]
        evidence_ordinal = sorted(evidence_positions[evidence_id] for evidence_id in unit.get("evidence_ids", []))
        records[synthesis_id] = {
            "id": synthesis_id,
            "kind": unit["kind"],
            "facts": unit.get("facts", []),
            "confidence": unit["confidence"],
            "interpretation_level": unit["interpretation_level"],
            "passage_scope": unit["passage_scope"],
            "source_anchors": unit.get("source_anchors", []),
            "verse_refs": unit.get("verse_refs", []),
            "evidence_ids": unit.get("evidence_ids", []),
            "metadata": unit.get("metadata", {}),
            "prompt_unit_ordinal": ordinal,
            "prompt_unit_band": _band(ordinal, ordinal, len(synthesis["units"])),
            "evidence_prompt_ordinals": evidence_ordinal,
        }
    return records


def _cluster_row(
    reference: str,
    cluster: dict[str, Any],
    synthesis: dict[str, Any],
    evidence_positions: dict[str, int],
    locations: dict[str, list[str]],
) -> dict[str, Any]:
    judgment = JUDGMENTS[reference][cluster["id"]]
    synthesis_positions = {
        synthesis_id: next(index for index, unit in enumerate(synthesis["units"], 1) if unit["id"] == synthesis_id)
        for synthesis_id in cluster["synthesis_ids"]
    }
    evidence_prompt_positions = sorted(evidence_positions[evidence_id] for evidence_id in cluster["evidence_ids"])
    first_unit = min(synthesis_positions.values())
    last_unit = max(synthesis_positions.values())
    scorer_rendered_locations = sorted(
        {location for synthesis_id in cluster["synthesis_ids"] for location in locations.get(synthesis_id, [])}
    )
    rendered = bool(scorer_rendered_locations)
    return {
        "cluster_id": cluster["id"],
        "category": cluster.get("categories", []),
        "weight": cluster["importance_weight"],
        "eligibility_classification": cluster["coverage_eligibility"],
        "core_status": "CORE" if cluster.get("quality_class") == "CORE" else "NON_CORE",
        "quality_class": cluster.get("quality_class"),
        "duplicate_reason_from_scorer": cluster.get("duplicate_reason"),
        "evidence_ids": cluster["evidence_ids"],
        "synthesis_unit_ids": cluster["synthesis_ids"],
        "concept": judgment["concept"],
        "rendered_by_scorer": rendered,
        "prose_presence": judgment["prose_presence"],
        "exact_commentary_locations": scorer_rendered_locations,
        "closest_prose_locations": judgment["closest_prose_locations"],
        "closest_prose": judgment["closest_prose"],
        "likely_omission_reason": None if rendered else judgment["omission_reason"],
        "omission_classification": None if rendered else judgment["classification"],
        "cause_domain": None if rendered else judgment["cause_domain"],
        "prompt_placement": {
            "synthesis_unit_ordinals": synthesis_positions,
            "synthesis_first_ordinal": first_unit,
            "synthesis_last_ordinal": last_unit,
            "synthesis_band": _band(first_unit, last_unit, len(synthesis["units"])),
            "evidence_prompt_ordinals": {
                evidence_id: evidence_positions[evidence_id] for evidence_id in cluster["evidence_ids"]
            },
            "evidence_first_ordinal": min(evidence_prompt_positions),
            "evidence_last_ordinal": max(evidence_prompt_positions),
            "evidence_band": _band(min(evidence_prompt_positions), max(evidence_prompt_positions), len(evidence_positions)),
            "representation_count": len(cluster["synthesis_ids"]),
            "explicitness_assessment": judgment["prompt_assessment"],
            "mixed_with_unrelated_material": judgment["mixed_with_unrelated"],
        },
        "redundancy_audit": {
            "closest_rendered_clusters": judgment["closest_rendered_clusters"],
            "boundary_assessment": judgment["boundary_assessment"],
            "scorer_distinct_but_prose_equivalent": judgment["scorer_distinct_but_prose_equivalent"],
        },
        "pipeline_trace": {
            "evidence_clearly_represents_idea": True,
            "synthesis_clearly_represents_idea": True,
            "prompt_contains_idea": True,
            "prompt_sections": ["COMPILED CHAPTER SYNTHESIS", "PERMITTED EVIDENCE CITATIONS"],
            "renderer_output_assessment": "directly cited" if rendered else judgment["prose_presence"].lower(),
            "scorer_result": "covered" if rendered else "uncovered",
        },
    }


def _identity_data(packet: dict[str, Any], parsed: dict[str, Any], prompt_meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_id": packet["packet_id"],
        "packet_hash": packet["packet_hash"],
        "source_packet_id": packet["source_packet_id"],
        "source_packet_hash": packet["source_packet_hash"],
        "source_packet_file_sha256": packet["source_packet_file_sha256"],
        "system_prompt_sha256": packet["system_prompt_sha256"],
        "user_prompt_sha256": packet["user_prompt_sha256"],
        "raw_response_sha256": parsed["raw_sha256"],
        "prompt_version": packet["commentary_prompt_version"],
        "renderer": packet["renderer"],
        "renderer_effort": packet["renderer_effort"],
        "evidence_hash": packet["evidence_hash"],
        "synthesis_hash": packet["synthesis_hash"],
        "prompt_line_count": prompt_meta["line_count"],
        "prompt_word_count": prompt_meta["word_count"],
        "synthesis_json_sha256": prompt_meta["synthesis_json_sha256"],
        "citation_json_sha256": prompt_meta["citation_json_sha256"],
    }


def _old_snapshot(reference: str, stem: str) -> dict[str, Any]:
    evaluation = _read_json(PROMPT_16_ROOT / "evaluation/chapters" / f"{stem}.json")
    parsed = _read_json(PROMPT_16_ROOT / "parsed" / f"{stem}.json")
    score = evaluation["full_result"]["score"]
    locations = _consumed_locations(parsed)
    rendered = sorted(
        cluster["id"]
        for cluster in score["clusters"]
        if cluster.get("coverage_eligibility") != "CONTEXTUAL_OPTIONAL"
        and any(locations.get(synthesis_id) for synthesis_id in cluster["synthesis_ids"])
    )
    return {
        "reference": reference,
        "prompt_version": "1.6",
        "packet_id": _read_json(PROMPT_16_ROOT / "packets" / f"{stem}.json")["packet_id"],
        "raw_response_sha256": parsed["raw_sha256"],
        "metrics": {
            "weighted_coverage": score["weighted_idea_coverage"],
            "eligible_idea_utilization": score["idea_cluster_coverage"],
            "core_coverage": score["core_cluster_coverage"],
            "category_coverage": score["category_coverage"],
            "eligible_weighted_denominator": score["eligible_weighted_denominator"],
            "consumed_eligible_weight": score["consumed_eligible_weight"],
            "eligible_cluster_count": len([c for c in score["clusters"] if c.get("coverage_eligibility") != "CONTEXTUAL_OPTIONAL"]),
            "consumed_cluster_count": score["consumed_cluster_count"],
            "word_count": evaluation["full_result"]["word_count"],
            "block_count": evaluation["full_result"]["block_count"],
        },
        "rendered_eligible_cluster_ids": rendered,
    }


def _chapter_audit(
    reference: str,
    book: str,
    chapter: int,
    prompt_stem: str,
    old_stem: str,
) -> dict[str, Any]:
    packet = _read_json(PROMPT_17_ROOT / "packets" / f"{prompt_stem}.json")
    parsed = _read_json(PROMPT_17_ROOT / "parsed" / f"{prompt_stem}.json")
    evaluation = _read_json(PROMPT_17_ROOT / "evaluation/chapters" / f"{prompt_stem}.json")
    prompt_path = PROMPT_17_ROOT / "handoff" / prompt_stem / "user_prompt.txt"
    synthesis, citations, prompt_meta = _prompt_parts(prompt_path)
    prepared = prepare_chapter(book, chapter)
    if prepared.bundle.evidence_hash != packet["evidence_hash"]:
        raise RuntimeError(f"evidence hash drift for {reference}")
    if prepared.synthesis.synthesis_hash != packet["synthesis_hash"]:
        raise RuntimeError(f"synthesis hash drift for {reference}")
    if parsed["validation_errors"]:
        raise RuntimeError(f"frozen response is not structurally clean for {reference}")

    score = evaluation["full_result"]["score"]
    locations = _consumed_locations(parsed)
    eligible_clusters = [
        cluster for cluster in score["clusters"] if cluster.get("coverage_eligibility") != "CONTEXTUAL_OPTIONAL"
    ]
    relevant_evidence_ids = {evidence_id for cluster in eligible_clusters for evidence_id in cluster["evidence_ids"]}
    relevant_synthesis_ids = {synthesis_id for cluster in eligible_clusters for synthesis_id in cluster["synthesis_ids"]}
    evidence_positions = {item["id"]: index for index, item in enumerate(citations, 1)}
    cluster_rows = [
        _cluster_row(reference, cluster, synthesis, evidence_positions, locations)
        for cluster in eligible_clusters
    ]
    rendered_ids = sorted(row["cluster_id"] for row in cluster_rows if row["rendered_by_scorer"])
    missed_ids = sorted(row["cluster_id"] for row in cluster_rows if not row["rendered_by_scorer"])
    old = _old_snapshot(reference, old_stem)
    new_metrics = {
        "weighted_coverage": score["weighted_idea_coverage"],
        "eligible_idea_utilization": score["idea_cluster_coverage"],
        "core_coverage": score["core_cluster_coverage"],
        "category_coverage": score["category_coverage"],
        "eligible_weighted_denominator": score["eligible_weighted_denominator"],
        "consumed_eligible_weight": score["consumed_eligible_weight"],
        "eligible_cluster_count": len(eligible_clusters),
        "consumed_cluster_count": score["consumed_cluster_count"],
        "consumed_eligible_synthesis_count": score["consumed_eligible_synthesis_count"],
        "word_count": evaluation["full_result"]["word_count"],
        "block_count": evaluation["full_result"]["block_count"],
        "section_count": len(parsed["validated_commentary"]["sections"]),
        "max_block_characters": max(len(block["text"]) for block in _response_blocks(parsed)),
        "schema_block_character_limit": 2000,
        "dump_severity": evaluation["full_result"]["dump_severity"],
        "quality_gate_outcome": evaluation["full_result"]["quality_gate_outcome"],
        "category_families": score["category_families"],
        "consumed_category_families": score["consumed_category_families"],
        "core_cluster_count": score["core_cluster_count"],
        "consumed_core_cluster_count": score["consumed_core_cluster_count"],
    }
    return {
        "reference": reference,
        "metadata": {
            "book": book,
            "chapter": chapter,
            "evidence_availability": packet["evidence_availability"],
            "evidence_count": packet["evidence_count"],
            "synthesis_unit_count": packet["synthesis_unit_count"],
            "meaningful_cluster_count": score["meaningful_cluster_count"],
            "eligible_cluster_count": len(eligible_clusters),
            "prompt_1_7_diagnostic_id": packet["diagnostic_id"],
            "prompt_1_7_manifest_identity": _read_json(PROMPT_17_ROOT / "manifest.json")["manifest_identity"],
        },
        "identities": _identity_data(packet, parsed, prompt_meta),
        "structural_validation": {
            "parse_status": parsed["parse_status"],
            "validation_errors": parsed["validation_errors"],
            "structural_result": evaluation["new_prompt_1_7"]["structural_result"],
            "generated_metadata_is_null_in_raw_response": _read_json(PROMPT_17_ROOT / "responses/raw" / f"{prompt_stem}.json")["generated_metadata"] is None,
        },
        "metrics_prompt_1_6": old["metrics"],
        "metrics_prompt_1_7": new_metrics,
        "eligible_idea_audit": cluster_rows,
        "evidence_records": _evidence_records(prepared, relevant_evidence_ids),
        "synthesis_records": _synthesis_records(synthesis, relevant_synthesis_ids, evidence_positions),
        "generated_response_blocks": _response_blocks(parsed),
        "selection_set_comparison": {
            "prompt_1_6_rendered_eligible_cluster_ids": old["rendered_eligible_cluster_ids"],
            "prompt_1_7_rendered_eligible_cluster_ids": rendered_ids,
            "prompt_1_6_only": sorted(set(old["rendered_eligible_cluster_ids"]) - set(rendered_ids)),
            "prompt_1_7_only": sorted(set(rendered_ids) - set(old["rendered_eligible_cluster_ids"])),
            "intersection": sorted(set(rendered_ids) & set(old["rendered_eligible_cluster_ids"])),
        },
        "prompt_salience_summary": {
            "prompt_structure": {
                "compiled_synthesis_line": 10,
                "permitted_evidence_citations_line": 13,
                "synthesis_units_are_flat_json": True,
                "eligibility_classifications_are_not_in_renderer_prompt": True,
                "cluster_boundaries_are_not_in_renderer_prompt": True,
            },
            "eligible_cluster_prompt_bands": {
                row["cluster_id"]: row["prompt_placement"]["synthesis_band"] for row in cluster_rows
            },
            "finding": "Prompt 1.7 adds prose instructions but presents the same flat synthesis and citation payload as prompt 1.6; it does not surface the scorer's eligible cluster boundaries or distinguish parallel records at input time.",
        },
        "response_capacity_audit": {
            "finding": "No hard schema or token-capacity boundary is evidenced. The largest block is below the 2,000-character rule, there is no truncation, and the response remains structurally valid. A soft shape limit is observable: the renderer completes a compact coherent narrative arc and stops after the final surrounding-passage block.",
            "practical_shape": {
                "section_count": new_metrics["section_count"],
                "block_count": new_metrics["block_count"],
                "word_count": new_metrics["word_count"],
                "max_block_characters": new_metrics["max_block_characters"],
                "uses_fixed_length_schema": False,
                "sections_are_full_or_truncated": "full paragraphs; no truncation evidence",
            },
        },
    }


def build_audit(repo_root: Path = ROOT) -> dict[str, Any]:
    del repo_root  # The diagnostic is intentionally anchored to this repository checkout.
    chapters = [_chapter_audit(*chapter) for chapter in CHAPTERS]
    manifest = _read_json(PROMPT_17_ROOT / "manifest.json")
    identity_basis = {
        "artifact_version": ARTIFACT_VERSION,
        "prompt_1_7_diagnostic_id": PROMPT_17_ID,
        "prompt_1_7_manifest_identity": manifest["manifest_identity"],
        "chapters": [
            {
                "reference": chapter["reference"],
                "packet_hash": chapter["identities"]["packet_hash"],
                "raw_response_sha256": chapter["identities"]["raw_response_sha256"],
            }
            for chapter in chapters
        ],
    }
    audit_id = f"prompt-1.7-omission-audit-{sha256_json(identity_basis)[:20]}"
    namespace = f".bhf-data/bhf-commentary-candidates/{audit_id}"
    one_cor = next(chapter for chapter in chapters if chapter["reference"] == "1 Corinthians 14")
    rev21 = next(chapter for chapter in chapters if chapter["reference"] == "Revelation 21")
    rev20_eval = _read_json(PROMPT_17_ROOT / "evaluation/chapters/004_revelation_020.json")
    rev20_score = rev20_eval["full_result"]["score"]
    rev20 = {
        "reference": "Revelation 20",
        "comparison_only": True,
        "metrics_prompt_1_6": rev20_eval["old_prompt_1_6"],
        "metrics_prompt_1_7": rev20_eval["new_prompt_1_7"],
        "delta": rev20_eval["delta"],
        "synthesis_unit_count": rev20_score["synthesis_unit_count"],
        "eligible_cluster_count": len([c for c in rev20_score["clusters"] if c.get("coverage_eligibility") != "CONTEXTUAL_OPTIONAL"]),
        "meaningful_cluster_count": rev20_score["meaningful_cluster_count"],
        "eligible_density": "6 relevant clusters / 21 synthesis units",
        "category_count": len(rev20_score["category_families"]),
        "prose_shape": {"word_count": rev20_eval["full_result"]["word_count"], "block_count": rev20_eval["full_result"]["block_count"]},
        "finding": "Revelation 20 presents six relevant clusters in only 21 synthesis units, with fewer semantic competitors and a six-block arc. Prompt 1.7 therefore has a tractable selection problem; Revelation 21 presents 16 relevant clusters in 119 units, 24 optional clusters, and numerous parallel temple/Jerusalem/creation records.",
    }
    audit = {
        "artifact_version": ARTIFACT_VERSION,
        "audit_id": audit_id,
        "immutable_namespace": namespace,
        "audit_scope": ["1 Corinthians 14", "Revelation 21"],
        "audit_mode": "FORENSIC_OMISSION_ONLY",
        "prohibited_actions_confirmed": [
            "no_prompt_1_8",
            "no_scoring_change",
            "no_ckl_change",
            "no_synthesis_change",
            "no_evidence_routing_change",
            "no_commentary_regeneration",
        ],
        "source": {
            "branch": "feat/commentary-v1.2-enrichment",
            "starting_sha": "96c23a1d265548b8742abb6c1272853dc867ef36",
            "prompt_1_7_diagnostic_id": PROMPT_17_ID,
            "prompt_1_7_manifest_identity": manifest["manifest_identity"],
            "prompt_1_6_qualification_id": PROMPT_16_ID,
            "prompt_1_7_prompt_version": "1.7",
            "renderer": "gpt-5.6-sol",
            "renderer_effort": "medium",
            "system_prompt_sha256": chapters[0]["identities"]["system_prompt_sha256"],
            "frozen_contracts": manifest["contract_versions"],
        },
        "chapters": chapters,
        "revelation_20_comparison": rev20,
        "cross_chapter_diagnosis": {
            "1 Corinthians 14": {
                "primary_cause": "POSSIBLE_SCORING_MISMATCH",
                "primary_statement": "Prompt 1.7 selected the same five of seven relevant scorer clusters as prompt 1.6. One missed cluster is an aggregate whose component ideas are expressed through parallel cited clusters; the other is a partially implied Acts comparison. The .8333 category result is a history-category omission in the scorer, not evidence of a broad prose failure.",
                "secondary_contributors": ["PROMPT_SALIENCE_WEAKNESS for the single surrounding Acts comparison"],
                "reader_facing_assessment": "No additional renderer selection was established. The remaining metric shortfall is not materially useful enough to justify a chapter-specific renderer change.",
            },
            "Revelation 21": {
                "primary_cause": "SYNTHESIS_PRESENTATION_WEAKNESS",
                "primary_statement": "The renderer receives 119 flat synthesis units and no scorer eligibility or cluster boundaries. Prompt 1.7 adds selection prose but does not surface the 16 relevant reader-level ideas. The renderer therefore follows a coherent temple/Jerusalem/creation arc, expresses six missed clusters through parallel prose, and leaves two distinct concepts only partially expressed.",
                "secondary_contributors": [
                    "LIKELY_SEMANTIC_REDUNDANCY across six missed clusters",
                    "POSSIBLE_SCORING_MISMATCH where alternate evidence ancestry supports prose-equivalent ideas",
                    "soft narrative stopping behavior, with no hard schema or token limit",
                ],
                "reader_facing_assessment": "The shortfall is real for Jerusalem's cultural density and the creation chronology, but the majority of the apparent misses are duplicate/parallel scoring boundaries rather than absent natural prose.",
            },
        },
        "specific_questions": {
            "1 Corinthians 14": {
                "category_coverage_failure": {
                    "missing_category": "history",
                    "available_categories": one_cor["metrics_prompt_1_7"]["category_families"],
                    "consumed_categories": one_cor["metrics_prompt_1_7"]["consumed_category_families"],
                    "eligible_clusters_in_category": [
                        "idea_cluster_018650e9fc74",
                        "idea_cluster_5aa8529568c8",
                    ],
                    "reader_value": "The Acts/Pentecost comparison can clarify why Acts 2 should not be used to settle Corinthian tongues, but the response already states the caution. It is useful context, not a material explanation gap.",
                },
                "synthesis_ancestry_mismatch": {
                    "resolved": True,
                    "prompt_1_7_validation_errors": [],
                    "prompt_1_7_rejection_codes": [],
                    "evidence_hash_verified": True,
                    "synthesis_hash_verified": True,
                },
            },
            "Revelation 21": {
                "missed_major_concepts": [
                    {
                        "cluster_id": row["cluster_id"],
                        "concept": row["concept"],
                        "classification": row["omission_classification"],
                    }
                    for row in rev21["eligible_idea_audit"]
                    if not row["rendered_by_scorer"]
                ],
                "pattern": "Seven of eight scorer misses concern Jerusalem/temple framing; the eighth is the creation chronology. Six of eight are prose-equivalent or substantially overlapping with rendered blocks. The two less-equivalent misses are distributed or split in the flat input and compete with more salient parallel concepts.",
                "not_a_late_only_pattern": True,
                "not_a_category_failure": True,
                "all_six_categories_consumed": True,
            },
        },
        "recommendation": {
            "choice": "B",
            "label": "Prompt/input-presentation remediation",
            "bounded_action": "Design one bounded diagnostic that presents dense chapters' distinct eligible reader-level ideas and their synthesis ancestry as an explicit, deterministic selection view while leaving CKL, evidence routing, synthesis content, scoring, and prompt-1.7 artifacts unchanged. Limit the next experiment to Revelation 21-style dense inputs; do not create prompt 1.8 in this audit.",
            "why_this_is_smallest": "A prompt-only change cannot reliably act on cluster distinctions that are absent from the renderer input. A scoring review is not yet sufficient because two Revelation 21 concepts are genuinely under-presented, while the semantic-equivalence flags are plausible rather than proven scorer defects.",
        },
    }
    audit["audit_identity"] = sha256_json({key: value for key, value in audit.items() if key != "audit_identity"})
    return audit


def write_audit(repo_root: Path = ROOT) -> dict[str, Any]:
    audit = build_audit(repo_root)
    root = repo_root / audit["immutable_namespace"]
    payload = (json.dumps(audit, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    digest = write_immutable(root / "audit.json", payload)
    return {"status": "WRITTEN", "audit_id": audit["audit_id"], "namespace": audit["immutable_namespace"], "path": str(root / "audit.json"), "sha256": digest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "write"), nargs="?", default="check")
    args = parser.parse_args()
    result = build_audit() if args.command == "check" else write_audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
