"""Deterministic prompt construction for BHF agent calls."""

from __future__ import annotations

from typing import ClassVar

from .models import GenreContext, ReferenceContext


AGENT_INSTRUCTIONS = """# BHF Agent Runtime Instructions

Use the BHF profile as method guidance, not as a doctrinal conclusion.

The profile content is the source of hermeneutics.
The prompt strategy only shapes runtime answer format and model steering.
"""


class PromptStrategy:
    """Base prompt strategy for profile-aware runtime steering."""

    profile_names: ClassVar[tuple[str, ...]] = ()

    def runtime_instructions(self, show_method_notes: bool) -> str:
        raise NotImplementedError

    def detected_context(self, reference_context: ReferenceContext, genre_context: GenreContext, show_method_notes: bool) -> str:
        return build_detected_context(reference_context, genre_context, show_method_notes)


class MinimalPromptStrategy(PromptStrategy):
    profile_names: ClassVar[tuple[str, ...]] = ("minimal-7b",)

    def runtime_instructions(self, show_method_notes: bool) -> str:
        return "\n".join(
            [
                "# Minimal Runtime Strategy",
                "- Keep answers short.",
                "- Use simple sentences.",
                "- Avoid scholarly surveys.",
                "- Avoid precise dates unless they are supplied in the question or profile.",
                "- Say uncertain instead of guessing.",
                "- Use this required answer order and headings exactly: Genre; Original Audience / Ancient Context; Observation; Interpretation; Application; Cautions / Uncertainty.",
                "- Keep each section brief.",
                "- Do not add extra sections or long caveats.",
            ]
        )


class StandardPromptStrategy(PromptStrategy):
    profile_names: ClassVar[tuple[str, ...]] = ("standard",)

    def runtime_instructions(self, show_method_notes: bool) -> str:
        lines = [
            "# Standard Runtime Strategy",
            "- Use a structured answer with clear headings.",
            "- Include brief method notes when enabled.",
            "- Mention major interpretive views when they are relevant.",
            "- Avoid denominational overreach.",
            "- Stay grounded in the supplied profile and detected context.",
            "- Do not invent scholars, citations, dates, or language claims.",
        ]
        if not show_method_notes:
            lines.append("- Keep method notes concise or omit them if they would interrupt the answer.")
        return "\n".join(lines)


class ScholarPromptStrategy(PromptStrategy):
    profile_names: ClassVar[tuple[str, ...]] = ("scholar",)

    def runtime_instructions(self, show_method_notes: bool) -> str:
        lines = [
            "# Scholar Runtime Strategy",
            "- Allow deeper answers with historical context and careful interpretation.",
            "- Discuss intertextuality when it helps the reading.",
            "- Note language cautions when relevant.",
            "- Present multiple interpretive options when the evidence supports them.",
            "- Use careful confidence labels for claims and alternatives.",
            "- Do not invent scholars, citations, dates, manuscripts, or language claims.",
            "- Do not overstate certainty when the evidence is mixed or incomplete.",
        ]
        if not show_method_notes:
            lines.append("- Keep method notes concise if you include them.")
        return "\n".join(lines)


STRATEGY_CLASSES: tuple[type[PromptStrategy], ...] = (
    MinimalPromptStrategy,
    StandardPromptStrategy,
    ScholarPromptStrategy,
)


def build_detected_context(
    reference_context: ReferenceContext,
    genre_context: GenreContext,
    show_method_notes: bool,
) -> str:
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
    return "\n".join(context_lines)


def strategy_for_profile(profile_name: str) -> PromptStrategy:
    for strategy_cls in STRATEGY_CLASSES:
        if profile_name in strategy_cls.profile_names:
            return strategy_cls()
    return StandardPromptStrategy()


def build_prompt(
    profile_name: str,
    profile_content: str,
    reference_context: ReferenceContext,
    genre_context: GenreContext,
    question: str,
    show_method_notes: bool = True,
) -> tuple[str, str]:
    """Return `(system_prompt, user_prompt)` for a BHF agent call."""

    # TODO: Add context-window-aware profile/module selection before loading
    # large profile content into small local runtimes.
    strategy = strategy_for_profile(profile_name)

    system_prompt = "\n\n".join(
        [
            profile_content.strip(),
            AGENT_INSTRUCTIONS.strip(),
            strategy.runtime_instructions(show_method_notes).strip(),
            strategy.detected_context(reference_context, genre_context, show_method_notes).strip(),
        ]
    )
    user_prompt = question.strip()
    return system_prompt, user_prompt
