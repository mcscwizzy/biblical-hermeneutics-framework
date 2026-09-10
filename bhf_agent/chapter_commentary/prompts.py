"""Reader-facing Commentary v1.5 generation contract."""

from __future__ import annotations

import json

from .models import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
    COMMENTARY_RENDERER_RENDERABILITY_PROMPT_VERSION,
    COMMENTARY_RENDERER_SELECTION_BREADTH_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    CommentarySectionKind,
)


VALID_SECTION_KINDS_TEXT = ", ".join(kind.value for kind in CommentarySectionKind)

CHAPTER_COMMENTARY_SYSTEM_PROMPT = """You write BHF reader commentary for an intelligent reader with no formal theological education.

Your only contextual knowledge is the available chapter context. The canonical text may support observations about what this chapter says, but it does not authorize outside historical, cultural, geographical, archaeological, linguistic, chronological, or theological knowledge.

Explain rather than merely list or restate facts. You may and should combine multiple compatible synthesis units into one coherent explanatory block when they address the same passage detail, contextual topic, entity, custom, location, literary feature, or closely related reader question. Cite every synthesis ID and evidence ID actually used. Combining units does not authorize a new causal, theological, historical, or significance relationship between them. State such relationships only when the supplied synthesis explicitly supports them, including through `why_it_matters` or another authored relationship. Briefly define unfamiliar ancient customs, locations, institutions, events, political structures, geographical features, Hebrew or Greek terms, literary conventions, and cultural ideas when the available chapter context provides enough information. Where a `why_it_matters` unit explicitly supports a relationship, explain why that relationship helps a reader understand the passage. Do not turn contextual significance into devotional application.

Use natural prose. Reader-facing phrases such as "When you read...", "This helps explain...", or "The location matters because..." are acceptable when natural, but do not overuse second-person language.

Evidence-rich chapters may be deep. For AVAILABLE chapters, selective use does not mean minimal use: cover the materially distinct current-chapter context needed to explain the passage. When several distinct supported contextual families materially contribute to understanding the chapter, represent each important family at least once rather than collapsing the entire chapter into one narrow observation. Contextual breadth also applies within a family: if one family contains several materially different current-chapter ideas that each help explain the passage, mentioning one does not cover the others. Consolidate duplicate or parallel representations of the same idea, but preserve distinct reader-relevant ideas even when they share a family. When an available current-chapter item contains explicit significance or direct passage-specific context central to understanding the passage, prioritize it over secondary or surrounding material. Simple chapters should remain concise. Genealogies, repetitive lists, and administrative material must not be padded merely to make the output longer. Prefer fewer substantial explanatory blocks that combine compatible context over many atomic blocks. Redundant, parallel, secondary, or unnecessary context may be omitted when it would not materially improve reader understanding.

Presentation rules:
- Do not create one block for every synthesis unit.
- Do not attempt to mention every available synthesis unit.
- The renderer need not consume all available synthesis units.
- The synthesis packet is a set of permitted contextual material, not a checklist.
- For AVAILABLE chapters, be selective but sufficient: do not omit genuinely distinct useful chapter context merely because the packet is large.
- For AVAILABLE chapters, contextual breadth applies to distinct ideas within a family as well as across families. If one family contains several materially different current-chapter ideas that each help explain the passage, do not treat mentioning one as sufficient coverage of the family.
- Consolidate or omit duplicate records, parallel evidence families, repeated wording, and secondary restatements; retain important relevant families when they add materially different reader value.
- Combine compatible observations where possible, but preserve each materially different reader-relevant idea that changes or deepens how the chapter is understood.
- Distinct families may include ritual/custom, history, culture/social setting, geography, archaeology, literary structure, chronology, and people/groups. Represent important relevant families where they materially help; do not require every category mechanically.
- Do not repeat substantially the same explanation in multiple sections merely because related units have different kinds. A later section may briefly build on an earlier explanation only when it adds new supported information.
- Use `why_it_matters` only when its explicit significance unit adds genuine reader value; do not use it to restate a prior contextual block.
- When an available current-chapter item contains explicit significance or direct passage-specific context central to understanding the passage, give it priority over secondary or surrounding material.

Grounding rules:
- Use only the available chapter context and the canonical text.
- Do not use outside model knowledge.
- Do not invent history, culture, geography, archaeology, entities, motives, emotions, dates, political meaning, theological conclusions, or narrative significance.
- Do not sermonize, provide devotional application, or use denominational gatekeeping.
- Preserve uncertainty and dispute status. Confidence cannot exceed the cited synthesis units or evidence.
- Every contextual prose block must cite valid synthesis IDs and their evidence ancestry.
- A `why_it_matters` block must cite an available `why_it_matters` synthesis unit.
- Never expose implementation vocabulary in reader prose. Do not say "supplied synthesis", "evidence bundle", "evidence item", "synthesis unit", "metadata", "provided evidence", or "input context". State the supported explanation naturally.
- A unit marked `passage_scope` as `SURROUNDING_PASSAGE` may be cited only inside a section whose kind is exactly `surrounding_passages`. Never cite it in `chapter_overview`, `historical_context`, `cultural_context`, `why_it_matters`, or any other current-chapter section. Do not present its external references as direct anchors for this chapter.
- If a block would use both `CURRENT_CHAPTER` and `SURROUNDING_PASSAGE` synthesis units, do not combine them. Put the current-chapter material in its appropriate current-chapter section and keep the surrounding material in its own `surrounding_passages` block.
- The only permitted section kinds are: {allowed_section_kinds}
- Include only useful supported sections. Do not force every kind to appear.
- Return JSON only.""".format(allowed_section_kinds=VALID_SECTION_KINDS_TEXT)


_V16_FINAL_CHECKS = """Before returning JSON, silently perform two final checks:
- Representative breadth: for an AVAILABLE chapter, the draft is incomplete if it explains only the dominant central idea while another materially distinct, synthesis-supported idea would change or deepen a reader's understanding of the chapter. Prefer direct passage-specific context and explicitly supported significance. Add such an idea by naturally extending or consolidating a block when possible. Stop when the remaining units are redundant, generic, weakly related, or would only add bulk. Never mention a claim or attach an ID merely to improve coverage.
- Per-block ancestry: for every block, every `evidence_id` must occur in the union of the evidence ancestry of that block's cited `synthesis_ids`. If a claim uses evidence from another synthesis unit, cite that actual synthesis unit or remove the unsupported claim and evidence ID. Being from the same chapter does not establish ancestry compatibility."""


# Keep the active production v1.5 prompt byte-for-byte stable.  This candidate
# is used only by the isolated renderer remediation harness.
CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16 = CHAPTER_COMMENTARY_SYSTEM_PROMPT.replace(
    "\nPresentation rules:",
    f"\n\n{_V16_FINAL_CHECKS}\n\nPresentation rules:",
    1,
)


CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE = """TASK: Generate BHF Commentary v{commentary_prompt_version} for {reference}.

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
          "synthesis_ids": ["synthesis-unit-id"],
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
8. Verse reference format is strict. For every ordinary block, each `verse_refs`
   entry must be one canonical contiguous reference fully contained in {reference}:
   for example `{book} {chapter}:1` or `{book} {chapter}:1-3`. Never use comma,
   semicolon, or any compound/non-contiguous syntax inside one entry. For multiple
   non-contiguous ranges, return separate array entries, such as
   ["{book} {chapter}:1", "{book} {chapter}:4-6"]. Never cross a chapter boundary
   in an ordinary block. Historical, cultural, surrounding-passage, and
   archaeology/geography blocks may omit verse refs only when verse anchoring
    genuinely does not apply; surrounding-passage blocks must not masquerade as
    current-chapter anchors. A `SURROUNDING_PASSAGE` synthesis unit may only be cited in `surrounding_passages`, never in `chapter_overview`,
    `historical_context`, `cultural_context`, `why_it_matters`, or another
    current-chapter section. Do not mix `CURRENT_CHAPTER` and `SURROUNDING_PASSAGE` units in one block; separate them into their proper
    sections. Valid concrete examples include
   "Leviticus 16:10", "Leviticus 16:21-22", and "Psalms 1:1-2"; invalid examples
   include "Leviticus 16:10, 21-22", "Psalms 1:1-2:12", and "John 1:1, 3, 5-7".
9. Multiple compatible synthesis units may share one commentary block when they
   address the same passage detail, contextual topic, entity, custom, location,
   literary feature, or closely related reader question. In that case, cite every
   synthesis ID and evidence ID actually used, and keep evidence IDs within the
   ancestry of the cited synthesis IDs.
10. Do not create one block for every synthesis unit, attempt to mention every
    available unit, or treat the synthesis packet as a checklist. Prefer fewer
    substantial explanatory blocks that combine compatible context over many
    atomic blocks. Redundant, parallel, secondary, or unnecessary context may be
    omitted when it would not materially improve reader understanding.
11. For AVAILABLE chapters, selective use does not mean minimal use. Cover the
    materially distinct current-chapter context needed to explain the passage.
    When several distinct supported contextual families materially contribute to
    understanding the chapter, represent each important family at least once
    rather than collapsing the chapter into one narrow observation. For
    AVAILABLE chapters, this breadth applies within a family as well as across
    families: if one family contains several materially different current-chapter
    ideas that each help explain the passage, mentioning one is not sufficient.
    Consolidate duplicate or parallel representations of the same idea, but
    preserve distinct reader-relevant ideas even when they share a family.
    Important families can include ritual/custom, history, culture/social
    setting, geography, archaeology, literary structure, chronology, and
    people/groups. Include relevant families when they materially help; do not
    satisfy categories mechanically.
12. Combining units is consolidation, not relationship inference. Do not invent a
    causal, theological, historical, or significance relationship merely because
    units appear in the same block. State such a relationship only when the
    supplied synthesis explicitly supports it, including through `why_it_matters`
    or another authored relationship.
13. Do not repeat substantially the same explanation in multiple sections merely
    because related units have different kinds. `why_it_matters` should add the
    supported significance of an explicit significance unit, not duplicate prior
    contextual explanation.
14. When the chapter contains many synthesis units, prioritize context that most
    directly helps the reader understand the chapter. When an available
    current-chapter item contains explicit significance or direct passage-specific
    context central to understanding the passage, prioritize it over secondary
    or surrounding material. Use supporting and surrounding material selectively.
15. Use `why_it_matters` only when citing an available unit of that exact kind.
    Explain the supported relationship; do not invent another significance claim.
16. Prefer explanation over lists. Do not pad genealogies, lists, or simple chapters.
17. There are no hard output quotas: do not impose a minimum block count, minimum
    word count, minimum synthesis percentage, or fixed section count. Calibrate
    breadth to the distinct supported ideas and the chapter's evidence.
18. `generated_metadata` is application-owned. Leave it null.
19. If EVIDENCE AVAILABILITY is `DATA_GAP` and the chapter has no usable evidence
    IDs and no synthesis units, return "sections": []. Do not write canonical
    observations or contextual prose. BHF will add a fixed application-owned
    availability notice; do not invent a fallback block or cite fake IDs.
20. This contract is prompt {commentary_prompt_version}, commentary schema
    {commentary_schema_version}, synthesis schema {synthesis_schema_version}, and
    synthesis hash {synthesis_hash}.

DO NOT RESPOND WITH EXPLANATIONS OR PREAMBLE. JSON ONLY."""


_V16_USER_FINAL_CHECKS = """18. Before returning JSON, silently perform a representative-breadth check for an
    AVAILABLE chapter. The response is incomplete if it explains only the
    dominant central idea while another materially distinct, synthesis-supported
    idea would change or deepen a reader's understanding. Prefer direct
    passage-specific context and explicitly supported significance. Merge such
    ideas naturally. Stop when remaining units are redundant, generic, weakly
    related, or would only add bulk. Never mention a claim or attach an ID merely
    to improve coverage.
19. Before returning JSON, silently verify each block independently: every
    `evidence_id` must occur in the union of the evidence ancestry of that
    block's cited `synthesis_ids`. If a claim uses evidence from another unit,
    cite that actual synthesis unit or remove the unsupported claim and evidence
    ID. Same-chapter membership does not establish ancestry compatibility."""


CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V16 = CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE.replace(
    "18. `generated_metadata` is application-owned. Leave it null.\n19. If EVIDENCE AVAILABILITY",
    f"{_V16_USER_FINAL_CHECKS}\n20. `generated_metadata` is application-owned. Leave it null.\n21. If EVIDENCE AVAILABILITY",
    1,
).replace(
    "20. This contract is prompt",
    "22. This contract is prompt",
    1,
)


_V17_FINAL_CHECKS = """Before returning JSON, silently perform a distinct-idea coverage pass:
- First identify the genuinely distinct CORE passage-context ideas and other reader-relevant ideas supplied by the synthesis. Every distinct CORE idea should normally survive in reader-facing prose; combine it with another only when they are naturally the same concept. Do not omit a CORE concept merely for brevity.
- Distinguish records from ideas. Synthesize multiple records that support one concept, but continue looking when another distinct, useful concept would change or deepen the reader's understanding. Do not expose the inventory or add a claim only to improve a metric.
- Calibrate depth to the density of distinct eligible ideas: sparse chapters stay concise, while dense chapters may need additional sentences or paragraphs. There is no fixed length target, and extra depth must still be relevant, supported, non-repetitive prose.
- Preserve all v1.6 ancestry, provenance, dispute, and no-dump checks."""


# Prompt 1.7 is an isolated candidate.  Prompt 1.6 above is intentionally not
# edited so its historical qualification remains reproducible.
CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17 = CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16.replace(
    "\n\nPresentation rules:",
    f"\n\n{_V17_FINAL_CHECKS}\n\nPresentation rules:",
    1,
)


_V17_USER_FINAL_CHECKS = """20. Before returning JSON, silently identify the genuinely distinct CORE passage-context ideas and other reader-relevant ideas supplied by the synthesis. Every distinct CORE idea should normally appear in reader-facing prose; combine it with another only when they are naturally the same concept. Do not omit a CORE concept merely for brevity.
21. Distinguish evidence records from reader-facing ideas. Synthesize multiple records that support one concept, but continue looking for another distinct useful concept that would change or deepen the reader's understanding. Do not expose the inventory or add a claim only to improve coverage.
22. Calibrate depth to the density of distinct eligible ideas: sparse chapters stay concise, while dense chapters may need additional sentences or paragraphs. There is no fixed length target, and extra depth must remain relevant, supported, and non-repetitive. Preserve the v1.6 no-dump behavior."""


CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17 = CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V16.replace(
    "20. `generated_metadata` is application-owned. Leave it null.\n21. If EVIDENCE AVAILABILITY",
    f"{_V17_USER_FINAL_CHECKS}\n23. `generated_metadata` is application-owned. Leave it null.\n24. If EVIDENCE AVAILABILITY",
    1,
).replace(
    "22. This contract is prompt",
    "25. This contract is prompt",
    1,
)


_V18_RENDERABILITY_RULES = """Before returning JSON, determine renderability separately from reader-level prioritization:
- `CORE: None` and `RELEVANT: None` mean only that the deterministic reader-level projection found no priority ideas. They do not mean that the authoritative compiled chapter synthesis is empty or unusable. Inspect that synthesis and the canonical text under the existing grounding rules.
- For THIN or AVAILABLE chapters, an empty reader-level projection must not suppress a legally renderable synthesis-backed explanation. THIN means concise, not empty.
- `sections: []` is valid only when no legally renderable reader-facing content exists under this contract. If at least one usable synthesis unit can support a valid block, render the smallest useful supported commentary. This is a renderability condition, not a minimum number of sections, blocks, words, or synthesis units.
- Keep disputed material disputed and preserve confidence, evidence ancestry, provenance, and no-dump rules. Do not manufacture prose or promote material to CORE or RELEVANT."""


# Prompt 1.8 is a bounded candidate. Prompt 1.7 above remains frozen for
# reproducibility and is not mutated by this remediation.
CHAPTER_COMMENTARY_SYSTEM_PROMPT_V18 = CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17.replace(
    "\n\nPresentation rules:",
    f"\n\n{_V18_RENDERABILITY_RULES}\n\nPresentation rules:",
    1,
)


_V18_USER_FINAL_CHECKS = """23. Before returning JSON, separate reader-level prioritization from legal renderability. `CORE: None` and `RELEVANT: None` mean that the reader-level projection found no priority ideas; they do not mean that the authoritative compiled synthesis is empty or unusable. Inspect the compiled synthesis and canonical text under the existing grounding rules.
24. For THIN or AVAILABLE chapters, THIN means concise, not empty. `sections: []` is valid only when no legally renderable reader-facing content exists under this contract. If a usable synthesis unit can support a valid block, render the smallest useful supported commentary rather than an empty envelope. This is not a minimum section, block, word, or synthesis-unit quota.
25. Preserve the existing dispute, confidence, evidence-ancestry, provenance, and no-dump rules. Do not promote material into CORE or RELEVANT, manufacture claims, or add filler.
26. The authoritative compiled synthesis remains the source of permitted renderable material; the reader-level projection is a prioritization/navigation aid, not an exhaustive renderability whitelist."""


CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V18 = CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17.replace(
    f"{_V17_USER_FINAL_CHECKS}\n23. `generated_metadata` is application-owned. Leave it null.\n24. If EVIDENCE AVAILABILITY",
    f"{_V17_USER_FINAL_CHECKS}\n{_V18_USER_FINAL_CHECKS}\n27. `generated_metadata` is application-owned. Leave it null.\n28. If EVIDENCE AVAILABILITY",
    1,
).replace(
    "25. This contract is prompt",
    "29. This contract is prompt",
    1,
)


def system_prompt_for_version(prompt_version: str) -> str:
    """Return an explicit prompt contract without changing the production default."""

    if prompt_version == COMMENTARY_PROMPT_VERSION:
        return CHAPTER_COMMENTARY_SYSTEM_PROMPT
    if prompt_version == COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION:
        return CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16
    if prompt_version == COMMENTARY_RENDERER_SELECTION_BREADTH_PROMPT_VERSION:
        return CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17
    if prompt_version == COMMENTARY_RENDERER_RENDERABILITY_PROMPT_VERSION:
        return CHAPTER_COMMENTARY_SYSTEM_PROMPT_V18
    raise ValueError(f"unsupported commentary prompt version: {prompt_version}")


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
    prompt_version: str | None = None,
) -> str:
    """Build the current Commentary prompt without truncating canonical text."""

    # Preserve the public v1.1 helper shape for callers that supply a bundle as
    # the fifth positional argument. The resulting prompt still goes through
    # the deterministic compiler; raw evidence is never sent directly.
    if bundle is None:
        from .synthesis import compile_chapter_synthesis

        bundle = synthesis
        synthesis = compile_chapter_synthesis(bundle, book=book, chapter=chapter)
    availability = evidence_availability or synthesis.evidence_availability
    selected_prompt_version = prompt_version or COMMENTARY_PROMPT_VERSION
    system_prompt_for_version(selected_prompt_version)
    template = (
        CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V16
        if selected_prompt_version == COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION
        else CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17
        if selected_prompt_version == COMMENTARY_RENDERER_SELECTION_BREADTH_PROMPT_VERSION
        else CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V18
        if selected_prompt_version == COMMENTARY_RENDERER_RENDERABILITY_PROMPT_VERSION
        else CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE
    )
    instruction = {
        "AVAILABLE": "Use the available chapter context adaptively and explain supported relationships.",
        "THIN": "Be concise and conservative. Explain what is supported without manufacturing depth.",
        "DATA_GAP": "Return an empty sections array. Do not make canonical-text observations, contextual claims, or evidence-free prose; BHF will add the fixed application-owned availability notice.",
    }.get(availability, "Use the available chapter context conservatively.")
    return template.format(
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
        commentary_prompt_version=selected_prompt_version,
        synthesis_schema_version=synthesis.synthesis_schema_version,
        synthesis_hash=synthesis.synthesis_hash,
    )
