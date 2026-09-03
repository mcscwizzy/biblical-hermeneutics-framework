"""Prompts for generating BHF chapter commentary."""

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
- Include only relevant sections
- No padding or filler
- Simple chapters get shorter commentary
- Rich chapters with much evidence get deeper commentary

The commentary should sound like an excellent historical/cultural Bible study guide.
Avoid robotic language. Prefer natural explanation over repetitive evidence citations."""

CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE = """TASK: Generate BHF chapter commentary for {reference}.

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
          "verse_refs": ["Genesis 1:1"],
          "evidence_ids": ["evidence-id-from-supplied-list"],
          "confidence": "high",
          "interpretation_level": "fact"
        }}
      ]
    }}
  ],
  "generated_metadata": {{
    "evidence_hash": "{evidence_hash}",
    "evidence_bundle_version": "1.0",
    "commentary_schema_version": "1.0",
    "commentary_prompt_version": "1.0",
    "model": "haiku"
  }}
}}

RULES:
1. Return ONLY JSON - nothing else
2. Each block.evidence_ids must contain actual IDs from supplied evidence
3. confidence <= evidence confidence
4. disputed evidence cannot be "fact"
5. text <= 2000 chars
6. Only sections with real evidence

DO NOT RESPOND WITH EXPLANATIONS OR PREAMBLE. JSON ONLY."""


def generate_evidence_summary(bundle) -> str:
    """Generate a text summary of supplied evidence for the prompt."""
    if not bundle.evidence_items:
        return "No contextual evidence provided."

    lines = []
    for item in bundle.evidence_items:
        lines.append(f"- {item.claim} (ID: {item.id}, confidence: {item.confidence})")

    if bundle.entities.get("people"):
        lines.append(f"\nPeople mentioned: {len(bundle.entities['people'])}")
    if bundle.entities.get("places"):
        lines.append(f"Places mentioned: {len(bundle.entities['places'])}")

    return "\n".join(lines)


def build_user_prompt(reference: str, book: str, chapter: int, canonical_text: str, bundle) -> str:
    """Build the user prompt for commentary generation."""
    evidence_summary = generate_evidence_summary(bundle)

    return CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE.format(
        reference=reference,
        book=book,
        chapter=chapter,
        canonical_text=canonical_text[:2000],  # Limit text length
        evidence_summary=evidence_summary,
        evidence_hash=bundle.evidence_hash,
    )
