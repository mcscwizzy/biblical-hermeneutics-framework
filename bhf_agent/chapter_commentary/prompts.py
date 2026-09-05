"""Prompts for generating BHF chapter commentary."""

from __future__ import annotations

import json

from .models import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    CommentarySectionKind,
)


VALID_SECTION_KINDS_TEXT = ", ".join(kind.value for kind in CommentarySectionKind)

CHAPTER_COMMENTARY_SYSTEM_PROMPT = """You are an expert biblical commentator writing for the BHF (Biblical Hermeneutics Framework).

Your commentary must be grounded exclusively in the evidence provided. You DO NOT use your own biblical knowledge.

Core principles:
- Use ONLY evidence supplied in the bundle
- If evidence is missing, say so clearly
- No invented historical context
- No invented archaeological claims
- No invented dates or geography without evidence
- No sermonizing or devotional application
- No unsupported theological conclusions
- No denominational gatekeeping

You may:
- Organize supplied evidence into clear sections
- Summarize supplied evidence in plain language
- Connect compatible supplied evidence
- Express supplied uncertainty clearly
- Describe what the passage itself says
- Make academic observations when evidence supports them

Each prose block must cite specific evidence IDs that actually appear in the bundle.
If a block cannot cite valid evidence, do not include it.

Structure commentary adaptively:
- The ONLY permitted section kind values are: {allowed_section_kinds}
- Never invent values such as section, textual_section, contextual_notes, or textual_notes
- Include only relevant sections; do not force every permitted section to appear
- Include a section only when the supplied evidence supports useful commentary for it
- No padding or filler
- Simple chapters get shorter commentary
- Rich chapters with much evidence get deeper commentary

The commentary should sound like an excellent historical/cultural Bible study guide.
Avoid robotic language. Prefer natural explanation over repetitive evidence citations.""".format(
    allowed_section_kinds=VALID_SECTION_KINDS_TEXT
)

CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE = """TASK: Generate BHF chapter commentary for {reference}.

EVIDENCE AVAILABILITY: {evidence_availability}
{availability_instruction}

CANONICAL TEXT:
{canonical_text}

SUPPLIED EVIDENCE:
{evidence_summary}

RESPOND WITH ONLY VALID JSON - NO PREAMBLE, NO EXPLANATION, NO TEXT BEFORE OR AFTER.

The JSON must have this exact structure:
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
          "text": "Prose grounded in supplied evidence only",
          "verse_refs": ["{book} {chapter}:1"],
          "evidence_ids": ["evidence-id-from-supplied-list"],
          "confidence": "high",
          "interpretation_level": "fact"
        }}
      ]
    }},
    {{
      "kind": "historical_context",
      "title": "Historical Context",
      "blocks": [
        {{
          "id": "block_2",
          "text": "Contextual prose grounded in supplied evidence only",
          "verse_refs": [],
          "evidence_ids": ["evidence-id-from-supplied-list"],
          "confidence": "medium",
          "interpretation_level": "inference"
        }}
      ]
    }}
  ],
  "generated_metadata": null
}}

RULES:
1. Return ONLY JSON - nothing else
2. Each block.evidence_ids must contain actual IDs from supplied evidence
3. confidence <= evidence confidence
4. disputed evidence cannot be "fact"
5. text <= 2000 chars
6. Only sections with real evidence
7. The ONLY allowed section kind values are: {allowed_section_kinds}
   Never invent values such as section, textual_section, contextual_notes, or textual_notes.
8. Ordinary blocks must cite {reference}; historical_context and archaeology_geography
   may omit verse_refs when verse anchoring genuinely does not apply.
9. generated_metadata is application-owned. Leave it null; do not provide model,
   timestamp, hash, or version provenance.
10. This generation contract is prompt version {commentary_prompt_version} and schema
    version {commentary_schema_version}.

DO NOT RESPOND WITH EXPLANATIONS OR PREAMBLE. JSON ONLY."""


_SUMMARY_METADATA_KEYS = (
    "dispute_status",
    "certainty",
    "assertion_type",
    "interpretive_caution",
    "passage_relationship",
    "anchor_specificity",
    "verse_distance",
    "source_kind",
)


def _compact_metadata(metadata) -> dict[str, object]:
    """Select stable, useful metadata without exposing raw internal objects."""
    return {
        key: metadata[key]
        for key in _SUMMARY_METADATA_KEYS
        if key in metadata and metadata[key] not in (None, "", [], {})
    }


def generate_evidence_summary(bundle) -> str:
    """Generate a text summary of supplied evidence for the prompt."""
    if not bundle.evidence_items:
        return "No contextual evidence provided."

    lines = ["AVAILABLE EVIDENCE (use these IDs in your blocks):"]
    for item in bundle.evidence_items:
        lines.append(json.dumps({
            "id": item.id,
            "claim": item.claim,
            "confidence": item.confidence,
            "category": item.category,
            "source_ids": sorted(item.source_ids),
            "passage_anchors": sorted(item.passage_anchors),
            "metadata": _compact_metadata(item.relevance_metadata),
        }, sort_keys=True, ensure_ascii=False))

    for bucket, label in (("people", "PEOPLE ENTITIES"), ("places", "PLACE ENTITIES")):
        entities = bundle.entities.get(bucket, [])
        if entities:
            records = [
                {"id": entity.id, "title": entity.title, "type": entity.type}
                for entity in sorted(entities, key=lambda value: value.id)
            ]
            lines.append(f"{label}: {json.dumps(records, sort_keys=True, ensure_ascii=False)}")

    return "\n".join(lines)


def build_user_prompt(reference: str, book: str, chapter: int, canonical_text: str, bundle, evidence_availability: str | None = None) -> str:
    """Build the user prompt without truncating canonical chapter text."""
    return CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE.format(
        reference=reference,
        book=book,
        chapter=chapter,
        canonical_text=canonical_text,
        evidence_summary=generate_evidence_summary(bundle),
        evidence_availability=evidence_availability or "AVAILABLE",
        availability_instruction={"AVAILABLE": "Use supplied evidence normally.", "THIN": "Be concise and conservative; do not expand beyond supplied evidence.", "DATA_GAP": "Make only canonical-text observations. Do not make external contextual claims or cite evidence."}.get(evidence_availability or "AVAILABLE", "Use supplied evidence normally."),
        allowed_section_kinds=VALID_SECTION_KINDS_TEXT,
        commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
        commentary_prompt_version=COMMENTARY_PROMPT_VERSION,
    )
