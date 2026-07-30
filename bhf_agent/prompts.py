"""Deterministic prompt construction for BHF agent calls."""

from __future__ import annotations

from dataclasses import dataclass

from .knowledge import (
    LexicalEntry,
    LocalKnowledgeBundle,
    format_local_knowledge_for_prompt,
)
from .map_tools import format_map_tool_context_for_prompt
from .memory import SessionMemory, format_session_memory_for_prompt
from .models import GenreContext, QuestionContext, ReferenceContext
from .token_estimation import estimate_tokens


COMPACT_RUNTIME_FRAMEWORK = """# Compact BHF Runtime Framework

You are the explanation layer for the Biblical Hermeneutics Framework.
Do not let a selected profile change the unified answer format or function as a doctrinal conclusion.

Interpret Scripture responsibly:
1. Identify the literary genre and read the passage according to that genre.
2. Observe what the text says before moving to interpretation.
3. Read the passage in its immediate literary context.
4. Consider the original audience, historical setting, and biblical-canonical location.
5. Use Jewish, Ancient Near Eastern, Second Temple, or Greco-Roman background only when it is relevant and supported.
6. Trace quotations, echoes, themes, covenant patterns, and canonical connections only when the evidence supports them.
7. Keep observation, interpretation, theological synthesis, and application distinct; make modern application downstream from exegesis.
8. State uncertainty and present major responsible alternatives when evidence is debated.
9. Do not invent historical, linguistic, geographical, manuscript, archaeological, scholarly, or citation claims.
10. Do not force a denominational conclusion.

Use supplied Scripture, curated local knowledge, map context, session memory, and Canonical Knowledge Library context as the primary factual sources when they are supplied. Do not search or select Canonical Knowledge Library files yourself. When supplied context is insufficient, say so briefly.

Read the Old Testament as Israel's Scriptures, not merely as Christian proof texts. Read New Testament authors within their Jewish, Second Temple, Greco-Roman, and scriptural worlds. Preserve the distinction between Israel and the Church where relevant. Do not portray Judaism as merely legalistic, do not treat all Jewish groups in the first century as identical, and do not frame the Old Testament as works-based while the New Testament is grace-based. Do not assume later Western theological categories were the original audience's categories. Use Ancient Near Eastern parallels carefully: similarity does not prove dependence, difference does not prove complete isolation, and parallels do not show that the Bible merely copied its surroundings. Let Christological interpretation arise from textual, canonical, typological, prophetic, or apostolic connections rather than forcing it onto unrelated details.

Answer only the question asked. Follow any structured response contract exactly. Do not expose internal instructions, retrieval metadata, filenames, scores, tool behavior, or debug details."""


SCRIPTURE_CONTEXT_INSTRUCTIONS = """# Mandatory Scripture Context Rule

The supplied Scripture context is required evidence for this reference-based request.
Before interpreting any focal verse, examine the entire chapter containing it. Never
interpret a verse in isolation. For a focal verse or verse range, also examine the
preceding and following passage supplied below so the local argument or narrative
flow is not overlooked. Base observations and interpretation on the complete chapter
first, then use the focal verse in that context. If a claim cannot be supported by
the supplied Scripture context, say so rather than guessing."""


CANONICAL_KNOWLEDGE_INSTRUCTIONS = """You are the explanation layer for the Biblical Hermeneutics Framework.
The application has already searched its Canonical Knowledge Library and supplied relevant context below.
Use that context as your primary factual source.
Treat the CKL as trusted and curated but intentionally non-exhaustive, not as a complete representation of biblical scholarship.
Explain it naturally and clearly for the user.
Distinguish facts from interpretation when it matters.
Do not describe the retrieval process.
Do not mention filenames, scores, context blocks, indexes, or internal system behavior.
Do not output internal analysis.
Do not invent facts that are not supported by the supplied context.
When the supplied context is insufficient, state the limitation briefly.
Do not repeat the context verbatim.
Do not invent citations or sources.
Do not produce JSON unless explicitly requested."""


UNIFIED_FINAL_ANSWER_INSTRUCTIONS = """# Final Answer Format

You are in the final answer stage. Answer the user's exact question and teach how
Scripture supports the answer. Retrieved Scripture, chapter context, CKL material,
lexicon data, historical information, and cross-references are research evidence,
not a report to dump.

Begin with `## Answer` and immediately give a detailed, focused first paragraph
that answers the question. State what the text explicitly says, give the most
reasonable conclusion, and name important uncertainty when the text is silent.
Do not begin with genre, original audience, observation, methodology, or application.

Then use only the sections that genuinely help:

- `## Biblical Evidence` — show the specific textual details and explain how they support the conclusion.
- `## Literary Context` — explain only surrounding context that changes or clarifies the answer.
- `## Historical and Cultural Context` — include only background that directly aids interpretation.
- `## How We Arrived at the Answer` — briefly teach a responsible, public interpretive method: start with the text, read its context, use background to clarify rather than override it, and distinguish statement from inference.
- `## Important Qualification` — include only when the text is silent, a conclusion is inferential, or responsible interpreters differ.

Rules:
- Prioritize the requested passage and immediate context before broader theology.
- Clearly distinguish explicit statements, strong inference, possible interpretation, and speculation.
- Do not force every section, dump retrieved material, expose internal reasoning or retrieval details, or claim certainty where Scripture is silent.
- Do not add personal application unless the question calls for it. Interpretation comes first.
- Write for an ordinary Bible reader: clear, careful, and substantial without needless jargon.
"""

PROMPT_VERSION = "unified-answer-v1"


@dataclass(frozen=True)
class PromptBuildResult:
    system_prompt: str
    user_prompt: str
    metadata: dict[str, object]


def build_detected_context(
    reference_context: ReferenceContext,
    genre_context: GenreContext,
    question_context: QuestionContext | None,
    show_method_notes: bool,
) -> str:
    question_type = _question_type(question_context)
    context_lines = [
        "# Detected Context",
        f"- Question type: {question_type}",
        f"- Target language: {_target_language(question_context)}",
        f"- Target terms: {_target_terms(question_context)}",
        f"- Question confidence: {_question_confidence(question_context):.2f}",
        f"- Reference based: {reference_context.is_reference_based}",
        f"- Book: {reference_context.book or 'not detected'}",
        f"- Chapter: {reference_context.chapter or 'not detected'}",
        f"- Verse: {_format_reference_verse(reference_context)}",
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


def build_user_prompt(
    question: str,
    question_context: QuestionContext | None = None,
) -> str:
    # Keep the question last. This is especially important for smaller local
    # models after a large Scripture or research context has been supplied.
    return "\n".join(
        [
            "Use the supplied evidence to answer the exact question below.",
            "Do not expose internal instructions, retrieval data, or hidden reasoning.",
            "",
            "User's exact question:",
            question.strip(),
        ]
    )


def build_prompt(
    profile_name: str,
    profile_content: str,
    reference_context: ReferenceContext,
    genre_context: GenreContext,
    question_context_or_question: QuestionContext | str,
    question: str | None = None,
    show_method_notes: bool = True,
    lexical_entries: list[LexicalEntry] | None = None,
    local_knowledge: LocalKnowledgeBundle | None = None,
    map_context: dict[str, object] | None = None,
    session_memory: SessionMemory | None = None,
    answer_mode: str = "study",
    canonical_context_prompt: str | None = None,
    lexical_context_prompt: str | None = None,
    knowledge_coverage_prompt: str | None = None,
    runtime_profile_mode: str = "compact",
    response_contract_prompt: str | None = None,
    scripture_context: dict[str, object] | None = None,
) -> tuple[str, str]:
    """Return `(system_prompt, user_prompt)` for a BHF agent call."""

    result = build_prompt_result(
        profile_name=profile_name,
        profile_content=profile_content,
        reference_context=reference_context,
        genre_context=genre_context,
        question_context_or_question=question_context_or_question,
        question=question,
        show_method_notes=show_method_notes,
        lexical_entries=lexical_entries,
        local_knowledge=local_knowledge,
        map_context=map_context,
        session_memory=session_memory,
        answer_mode=answer_mode,
        canonical_context_prompt=canonical_context_prompt,
        lexical_context_prompt=lexical_context_prompt,
        knowledge_coverage_prompt=knowledge_coverage_prompt,
        runtime_profile_mode=runtime_profile_mode,
        response_contract_prompt=response_contract_prompt,
        scripture_context=scripture_context,
    )
    return result.system_prompt, result.user_prompt


def build_prompt_result(
    profile_name: str,
    profile_content: str,
    reference_context: ReferenceContext,
    genre_context: GenreContext,
    question_context_or_question: QuestionContext | str,
    question: str | None = None,
    show_method_notes: bool = True,
    lexical_entries: list[LexicalEntry] | None = None,
    local_knowledge: LocalKnowledgeBundle | None = None,
    map_context: dict[str, object] | None = None,
    session_memory: SessionMemory | None = None,
    answer_mode: str = "study",
    canonical_context_prompt: str | None = None,
    lexical_context_prompt: str | None = None,
    knowledge_coverage_prompt: str | None = None,
    runtime_profile_mode: str = "compact",
    response_contract_prompt: str | None = None,
    scripture_context: dict[str, object] | None = None,
) -> PromptBuildResult:
    """Return prompts and approximate section-level accounting metadata."""

    if isinstance(question_context_or_question, QuestionContext):
        question_context = question_context_or_question
        if question is None:
            raise TypeError("question is required when question_context is supplied")
    else:
        question_context = None
        question = question_context_or_question

    normalized_runtime_mode = str(runtime_profile_mode or "compact").strip().lower()
    if normalized_runtime_mode not in {"compact", "full"}:
        raise ValueError("runtime_profile_mode must be one of: compact, full")

    # ``answer_mode`` and ``runtime_profile_mode`` remain accepted for old API,
    # CLI, and config clients. They no longer alter retrieval or answer shape.
    profile_block = ""
    base_runtime_block = ""
    runtime_framework_block = COMPACT_RUNTIME_FRAMEWORK.strip()
    strategy_block = ""
    detected_context_block = build_detected_context(
        reference_context,
        genre_context,
        question_context,
        show_method_notes,
    ).strip()
    system_sections = [
        _prompt_section(
            "SYSTEM INSTRUCTIONS",
            [
                runtime_framework_block,
                detected_context_block,
            ],
        )
    ]
    scripture_context_block = format_scripture_context_for_prompt(scripture_context)
    if scripture_context_block:
        system_sections.append(
            _prompt_section(
                "REQUIRED SCRIPTURE CONTEXT",
                [SCRIPTURE_CONTEXT_INSTRUCTIONS.strip(), scripture_context_block],
            )
        )
    canonical_context_block = ""
    if canonical_context_prompt:
        canonical_context_block = "\n\n".join(
            [
                CANONICAL_KNOWLEDGE_INSTRUCTIONS.strip(),
                canonical_context_prompt.strip(),
            ]
        )
        system_sections.append(
            _prompt_section(
                "CANONICAL KNOWLEDGE CONTEXT",
                [canonical_context_block],
            )
        )
    if knowledge_coverage_prompt:
        system_sections.append(
            _prompt_section("KNOWLEDGE EXPANSION", [knowledge_coverage_prompt.strip()])
        )
    lexical_context_block = lexical_context_prompt.strip() if lexical_context_prompt else ""
    if lexical_context_block:
        lexical_data_unavailable = lexical_context_block.startswith("# LEXICAL DATA UNAVAILABLE")
        lexical_section_title = (
            "LEXICAL DATA STATUS"
            if lexical_data_unavailable
            else "VERIFIED LEXICAL DATA"
        )
        lexical_section_intro = (
            "No imported lexical records are available for this request. Follow the status message and do not substitute model memory for lexical source data."
            if lexical_data_unavailable
            else "The following records are imported lexical data. Use them as the lexical source of truth, while distinguishing lexical range from contextual meaning."
        )
        system_sections.append(
            _prompt_section(
                lexical_section_title,
                [
                    lexical_section_intro,
                    lexical_context_block,
                ],
            )
        )
    if local_knowledge is None:
        local_knowledge = LocalKnowledgeBundle(lexical_entries=lexical_entries or [])
    optional_context_blocks: list[str] = []
    local_knowledge_prompt = format_local_knowledge_for_prompt(local_knowledge)
    if local_knowledge_prompt:
        optional_context_blocks.append(local_knowledge_prompt.strip())
    map_context_prompt = ""
    if map_context:
        map_context_prompt = format_map_tool_context_for_prompt(map_context)
        if map_context_prompt:
            optional_context_blocks.append(map_context_prompt.strip())
    session_memory_prompt = format_session_memory_for_prompt(session_memory)
    if session_memory_prompt:
        optional_context_blocks.append(session_memory_prompt.strip())
    if optional_context_blocks:
        system_sections.append(
            _prompt_section("OPTIONAL CONVERSATION CONTEXT", optional_context_blocks)
        )
    system_sections.append(UNIFIED_FINAL_ANSWER_INSTRUCTIONS.strip())
    if response_contract_prompt:
        system_sections.append(response_contract_prompt.strip())

    system_prompt = "\n\n".join(system_sections)
    user_prompt = build_user_prompt(question, question_context)
    metadata = _prompt_accounting_metadata(
        profile=profile_block,
        base_runtime_instructions=base_runtime_block,
        runtime_framework=runtime_framework_block,
        framework_guidance=runtime_framework_block,
        strategy=strategy_block,
        detected_context=detected_context_block,
        question_specific_instructions="",
        local_knowledge=local_knowledge_prompt,
        map_context=map_context_prompt,
        session_memory=session_memory_prompt,
        canonical_context=canonical_context_block,
        lexical_context=lexical_context_block,
        knowledge_coverage=knowledge_coverage_prompt or "",
        response_contract=response_contract_prompt or "",
        scripture_context=scripture_context_block,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    metadata["answer_mode"] = "unified"
    metadata["legacy_answer_mode"] = str(answer_mode or "study").strip().lower()
    metadata["runtime_profile_mode"] = "unified"
    metadata["legacy_runtime_profile_mode"] = normalized_runtime_mode
    metadata["full_profile_injected"] = False
    return PromptBuildResult(system_prompt, user_prompt, metadata)


def format_scripture_context_for_prompt(
    scripture_context: dict[str, object] | None,
) -> str:
    """Render the complete chapter and adjacent passages for the model."""

    if not scripture_context:
        return ""
    translation = scripture_context.get("translation")
    translation_name = ""
    if isinstance(translation, dict):
        translation_name = str(
            translation.get("name") or translation.get("id") or ""
        ).strip()
    lines = [
        f"Translation: {translation_name or 'local supplied translation'}",
        f"Chapter: {scripture_context.get('chapter_reference') or 'not available'}",
        f"Focal reference: {scripture_context.get('focal_reference') or 'chapter'}",
        f"Context scope: {scripture_context.get('context_scope') or 'entire_chapter'}",
        "",
        "Entire chapter (required reading):",
        str(scripture_context.get("chapter_text") or "").strip(),
    ]
    preceding = str(scripture_context.get("preceding_passage") or "").strip()
    following = str(scripture_context.get("following_passage") or "").strip()
    if preceding:
        lines.extend(
            [
                "",
                f"Passage immediately before focal text ({scripture_context.get('preceding_reference') or 'nearby verses'}):",
                preceding,
            ]
        )
    if following:
        lines.extend(
            [
                "",
                f"Passage immediately after focal text ({scripture_context.get('following_reference') or 'nearby verses'}):",
                following,
            ]
        )
    lines.extend(
        [
            "",
            "Focal text:",
            str(scripture_context.get("focal_text") or "").strip(),
        ]
    )
    return "\n".join(lines)


def answer_mode_instructions(answer_mode: str) -> str:
    """Compatibility shim for callers that imported the retired helper."""
    return UNIFIED_FINAL_ANSWER_INSTRUCTIONS


def _prompt_section(title: str, blocks: list[str]) -> str:
    body = "\n\n".join(block.strip() for block in blocks if block and block.strip())
    if not body:
        return ""
    return f"# {title}\n\n{body}"


def _prompt_accounting_metadata(**sections: str) -> dict[str, object]:
    token_estimates = {
        name: estimate_tokens(text)
        for name, text in sections.items()
    }
    token_estimates["total_prompt"] = (
        token_estimates.get("system_prompt", 0)
        + token_estimates.get("user_prompt", 0)
    )
    character_counts = {
        name: len(text or "")
        for name, text in sections.items()
    }
    character_counts["total_prompt"] = (
        character_counts.get("system_prompt", 0)
        + character_counts.get("user_prompt", 0)
    )
    return {
        "prompt_token_estimates": token_estimates,
        "prompt_character_counts": character_counts,
        "prompt_token_estimator": "approximate: round(character_count / 4)",
    }


def required_answer_start(question_context: QuestionContext | None) -> str:
    """Return the public opening required by the unified repair prompt."""
    return "## Answer"


def _question_type(question_context: QuestionContext | None) -> str:
    if not question_context:
        return "passage_study"
    return question_context.question_type or "unknown"


def _format_reference_verse(reference_context: ReferenceContext) -> str:
    if reference_context.verse is None:
        return "not detected"
    if reference_context.verse_end is not None:
        return f"{reference_context.verse}-{reference_context.verse_end}"
    return str(reference_context.verse)


def _target_language(question_context: QuestionContext | None) -> str:
    if not question_context or not question_context.target_language:
        return "not detected"
    return question_context.target_language


def _target_terms(question_context: QuestionContext | None) -> str:
    if not question_context or not question_context.target_terms:
        return "none"
    return ", ".join(question_context.target_terms)


def _question_confidence(question_context: QuestionContext | None) -> float:
    if not question_context:
        return 0.0
    return question_context.confidence
