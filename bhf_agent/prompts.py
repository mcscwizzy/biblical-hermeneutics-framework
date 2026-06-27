"""Deterministic prompt construction for BHF agent calls."""

from __future__ import annotations

from .models import GenreContext, ReferenceContext


AGENT_INSTRUCTIONS = """# BHF Agent Runtime Instructions

Use the BHF profile as method guidance, not as a doctrinal conclusion.

For the response:
- Begin with original audience, ancient context, and literary setting when relevant.
- Identify the genre before drawing interpretive conclusions.
- Separate observation, interpretation, and application.
- Distinguish consensus, majority view, minority view, and speculation.
- Admit uncertainty where evidence is limited or disputed.
- Avoid hallucinated Hebrew, Greek, history, archaeology, or scholarly claims.
- Avoid denominational overreach; present responsible ranges of interpretation.
- Do not treat contemporary application as the text's original meaning.
- Teach interpretation method rather than forcing conclusions.
"""


def build_prompt(
    profile_content: str,
    reference_context: ReferenceContext,
    genre_context: GenreContext,
    question: str,
    show_method_notes: bool = True,
) -> tuple[str, str]:
    """Return `(system_prompt, user_prompt)` for a BHF agent call."""

    # TODO: Add context-window-aware profile/module selection before loading
    # large profile content into small local runtimes.
    context_lines = [
        "# Detected Context",
        f"- Reference based: {reference_context.is_reference_based}",
        f"- Book: {reference_context.book or 'not detected'}",
        f"- Chapter: {reference_context.chapter or 'not detected'}",
        f"- Verse: {reference_context.verse or 'not detected'}",
        f"- Testament: {reference_context.testament or 'not detected'}",
        f"- Topic: {reference_context.topic or 'not detected'}",
        f"- Reference confidence: {reference_context.confidence:.2f}",
        f"- Primary genre: {genre_context.primary_genre or 'not detected'}",
        f"- Secondary genres: {', '.join(genre_context.secondary_genres) or 'none'}",
        f"- Historical context hint: {genre_context.historical_context_hint or 'none'}",
        f"- Recommended modules: {', '.join(genre_context.recommended_modules) or 'none'}",
        f"- Genre confidence: {genre_context.confidence:.2f}",
    ]
    if not show_method_notes:
        context_lines.append(
            "- Keep method notes concise; prioritize the answer while preserving method."
        )

    system_prompt = "\n\n".join(
        [
            profile_content.strip(),
            AGENT_INSTRUCTIONS.strip(),
            "\n".join(context_lines),
        ]
    )
    user_prompt = question.strip()
    return system_prompt, user_prompt
