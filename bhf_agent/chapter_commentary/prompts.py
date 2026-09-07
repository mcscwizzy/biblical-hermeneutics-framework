"""Reader-facing Commentary v1.2 generation contract."""

from __future__ import annotations

import json

from .models import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    CommentarySectionKind,
)


VALID_SECTION_KINDS_TEXT = ", ".join(kind.value for kind in CommentarySectionKind)

CHAPTER_COMMENTARY_SYSTEM_PROMPT = """You write BHF reader commentary for an intelligent reader with no formal theological education.

Your only contextual knowledge is the supplied CompiledChapterSynthesis. The canonical text may support observations about what this chapter says, but it does not authorize outside historical, cultural, geographical, archaeological, linguistic, chronological, or theological knowledge.

Explain rather than merely list or restate facts. Connect facts only where a synthesis unit has already grouped them. Briefly define unfamiliar ancient customs, locations, institutions, events, political structures, geographical features, Hebrew or Greek terms, literary conventions, and cultural ideas when the supplied synthesis provides enough information. Where a `why_it_matters` unit explicitly supports a relationship, explain why that relationship helps a reader understand the passage. Do not turn contextual significance into devotional application.

Use natural prose. Reader-facing phrases such as "When you read...", "This helps explain...", or "The location matters because..." are acceptable when natural, but do not overuse second-person language.

Evidence-rich chapters may be deep. Simple chapters should remain concise. Genealogies, repetitive lists, and administrative material must not be padded merely to make the output longer. Prefer coherent paragraphs over inventories.

Grounding rules:
- Use only supplied synthesis facts and the canonical text.
- Do not use outside model knowledge.
- Do not invent history, culture, geography, archaeology, entities, motives, emotions, dates, political meaning, theological conclusions, or narrative significance.
- Do not sermonize, provide devotional application, or use denominational gatekeeping.
- Preserve uncertainty and dispute status. Confidence cannot exceed the cited synthesis units or evidence.
- Every contextual prose block must cite valid synthesis IDs and their evidence ancestry.
- A `why_it_matters` block must cite a supplied `why_it_matters` synthesis unit.
- The only permitted section kinds are: {allowed_section_kinds}
- Include only useful supported sections. Do not force every kind to appear.
- Return JSON only.""".format(allowed_section_kinds=VALID_SECTION_KINDS_TEXT)


CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE = """TASK: Generate BHF Commentary v1.2 for {reference}.

EVIDENCE AVAILABILITY: {evidence_availability}
{availability_instruction}

CANONICAL TEXT:
{canonical_text}

COMPILED CHAPTER SYNTHESIS:
{synthesis_summary}

PERMITTED EVIDENCE CITATIONS:
{citation_summary}

RESPOND WITH ONLY VALID JSON. Use this exact envelope:
{{
  "reference": "{reference}",
  "book": "{book}",
  "chapter": {chapter},
  "status": "pending",
  "sections": [
    {{
      "kind": "chapter_overview",
      "title": "Overview",
      "blocks": [
        {{
          "id": "block_1",
          "text": "Natural reader-facing explanation",
          "verse_refs": ["{book} {chapter}:1"],
          "evidence_ids": ["evidence-id-in-cited-synthesis-unit"],
          "synthesis_ids": ["supplied-synthesis-unit-id"],
          "confidence": "high",
          "interpretation_level": "fact"
        }}
      ]
    }}
  ],
  "generated_metadata": null
}}

RULES:
1. JSON only: no preamble, Markdown fence, or trailing explanation.
2. Every evidence ID must belong to at least one cited synthesis unit.
3. Every synthesis ID must appear in COMPILED CHAPTER SYNTHESIS.
4. `confidence` must not exceed either cited synthesis or cited evidence.
5. Disputed synthesis cannot become `fact`.
6. Each block text must be at most 2,000 characters.
7. Only the following section kinds are allowed: {allowed_section_kinds}
   Never invent values such as section, textual_section, contextual_notes, or textual_notes.
8. Ordinary blocks cite verse references inside {reference}. Historical, cultural,
   surrounding-passage, and archaeology/geography blocks may omit verse refs only
   when verse anchoring genuinely does not apply.
9. Use `why_it_matters` only when citing a supplied unit of that exact kind. Explain
   the supplied relationship; do not invent another significance claim.
10. Prefer explanation over lists. Do not pad genealogies, lists, or simple chapters.
11. `generated_metadata` is application-owned. Leave it null.
12. This contract is prompt {commentary_prompt_version}, commentary schema
    {commentary_schema_version}, synthesis schema {synthesis_schema_version}, and
    synthesis hash {synthesis_hash}.

DO NOT RESPOND WITH EXPLANATIONS OR PREAMBLE. JSON ONLY."""


def generate_synthesis_summary(synthesis) -> str:
    """Serialize only deterministic understanding units for prose generation."""

    if not synthesis.synthesis_units:
        return json.dumps(
            {
                "synthesis_hash": synthesis.synthesis_hash,
                "units": [],
                "evidence_gaps": [gap.to_dict() for gap in synthesis.evidence_gaps],
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "synthesis_hash": synthesis.synthesis_hash,
            "units": [unit.to_dict() for unit in synthesis.synthesis_units],
            "evidence_gaps": [gap.to_dict() for gap in synthesis.evidence_gaps],
            "coverage": synthesis.coverage.to_dict(),
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def generate_citation_summary(bundle) -> str:
    """Expose provenance needed to cite units without duplicating raw claims."""

    records = [
        {
            "id": item.id,
            "source_ids": sorted(item.source_ids),
            "confidence": item.confidence,
            "passage_anchors": sorted(item.passage_anchors),
        }
        for item in sorted(bundle.evidence_items, key=lambda value: value.id)
    ]
    return json.dumps(records, sort_keys=True, ensure_ascii=False)


def build_user_prompt(
    reference: str,
    book: str,
    chapter: int,
    canonical_text: str,
    synthesis,
    bundle=None,
    evidence_availability: str | None = None,
) -> str:
    """Build the v1.2 prompt without truncating canonical chapter text."""

    # Preserve the public v1.1 helper shape for callers that supply a bundle as
    # the fifth positional argument. The resulting prompt still goes through
    # the deterministic v1.2 compiler; raw evidence is never sent directly.
    if bundle is None:
        from .synthesis import compile_chapter_synthesis

        bundle = synthesis
        synthesis = compile_chapter_synthesis(bundle, book=book, chapter=chapter)
    availability = evidence_availability or synthesis.evidence_availability
    instruction = {
        "AVAILABLE": "Use the supplied synthesis adaptively and explain supported relationships.",
        "THIN": "Be concise and conservative. Explain what is supported without manufacturing depth.",
        "DATA_GAP": "Make only modest canonical-text observations. Do not make contextual claims or cite nonexistent evidence.",
    }.get(availability, "Use the supplied synthesis conservatively.")
    return CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE.format(
        reference=reference,
        book=book,
        chapter=chapter,
        canonical_text=canonical_text,
        synthesis_summary=generate_synthesis_summary(synthesis),
        citation_summary=generate_citation_summary(bundle),
        evidence_availability=availability,
        availability_instruction=instruction,
        allowed_section_kinds=VALID_SECTION_KINDS_TEXT,
        commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
        commentary_prompt_version=COMMENTARY_PROMPT_VERSION,
        synthesis_schema_version=synthesis.synthesis_schema_version,
        synthesis_hash=synthesis.synthesis_hash,
    )
