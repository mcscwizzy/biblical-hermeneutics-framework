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

CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE = """Generate BHF chapter commentary for {reference}.

CANONICAL TEXT:
{canonical_text}

SUPPLIED EVIDENCE:
{evidence_summary}

OUTPUT FORMAT (as JSON):
{{
  "reference": "{reference}",
  "book": "{book}",
  "chapter": {chapter},
  "status": "pending",
  "sections": [
    {{
      "kind": "chapter_overview|historical_context|people_places|archaeology_geography|language_literary|chronology|interpretive_questions|things_easy_to_miss|dig_deeper",
      "title": "Section title",
      "blocks": [
        {{
          "id": "block_1",
          "text": "Clear, grounded prose block",
          "verse_refs": ["Genesis 1:1", "Genesis 1:5"],
          "evidence_ids": ["evidence-id-1", "evidence-id-2"],
          "confidence": "high|medium|low",
          "interpretation_level": "fact|inference|disputed"
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

CONSTRAINTS:
- Each block must cite at least one evidence_id from the supplied evidence
- confidence must match or be lower than cited evidence confidence
- disputed evidence cannot become "fact" interpretation
- Do NOT invent evidence IDs - only use ones provided
- Section kinds must be from the allowed list
- Block text must not exceed 2000 characters
- Generate only sections with genuine supporting evidence
- It is OK to have few or zero sections if evidence is sparse

Begin your response with the JSON object only - no preamble."""


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
