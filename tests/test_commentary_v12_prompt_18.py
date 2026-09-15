"""Focused contract tests for the bounded Commentary prompt 1.8 remediation."""

import hashlib

from bhf_agent.chapter_commentary.models import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_RENDERER_RENDERABILITY_PROMPT_VERSION,
    COMMENTARY_RENDERER_SELECTION_BREADTH_PROMPT_VERSION,
)
from bhf_agent.chapter_commentary.prompts import (
    CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17,
    CHAPTER_COMMENTARY_SYSTEM_PROMPT_V18,
    CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17,
    CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V18,
    system_prompt_for_version,
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_prompt_17_identity_and_dispatch_remain_frozen():
    assert COMMENTARY_RENDERER_SELECTION_BREADTH_PROMPT_VERSION == "1.7"
    assert system_prompt_for_version("1.7") == CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17
    assert _sha256(CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17) == (
        "cbe6a47cb9ec7b7186347aa3e25ff05d2b9387f72e6297ce0bce44515283f614"
    )
    assert "1.8" not in CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17
    assert "renderability" not in CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17.casefold()
    assert "renderability" not in CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17.casefold()


def test_prompt_18_adds_projection_renderability_distinction_without_changing_defaults():
    assert COMMENTARY_PROMPT_VERSION == "1.5"
    assert COMMENTARY_RENDERER_RENDERABILITY_PROMPT_VERSION == "1.8"
    assert system_prompt_for_version("1.8") == CHAPTER_COMMENTARY_SYSTEM_PROMPT_V18
    assert CHAPTER_COMMENTARY_SYSTEM_PROMPT_V18 != CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17
    assert CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V18 != CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17
    assert "CORE: None" in CHAPTER_COMMENTARY_SYSTEM_PROMPT_V18
    assert "RELEVANT: None" in CHAPTER_COMMENTARY_SYSTEM_PROMPT_V18
    assert "do not mean that the authoritative compiled chapter synthesis is empty or unusable" in CHAPTER_COMMENTARY_SYSTEM_PROMPT_V18
    assert "THIN means concise, not empty" in CHAPTER_COMMENTARY_SYSTEM_PROMPT_V18
    assert "sections: []` is valid only when no legally renderable reader-facing content exists" in CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V18
    assert "smallest useful supported commentary" in CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V18
    assert "not a minimum section, block, word, or synthesis-unit quota" in CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V18


def test_prompt_18_preserves_grounding_dispute_ancestry_and_no_dump_constraints():
    combined = (CHAPTER_COMMENTARY_SYSTEM_PROMPT_V18 + "\n" + CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V18).casefold()
    for phrase in (
        "preserve uncertainty and dispute status",
        "confidence cannot exceed",
        "evidence ancestry",
        "provenance",
        "do not invent",
        "no-dump",
        "do not promote material into core or relevant",
    ):
        assert phrase in combined
    assert "always return" not in combined
    assert "always create" not in combined
    assert combined.count("minimum word count") == (
        CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17 + "\n" + CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17
    ).casefold().count("minimum word count")
    assert combined.count("fixed section count") == (
        CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17 + "\n" + CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17
    ).casefold().count("fixed section count")


def test_prompt_18_has_a_distinct_reproducible_identity():
    system_hash = _sha256(CHAPTER_COMMENTARY_SYSTEM_PROMPT_V18)
    user_hash = _sha256(CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V18)
    assert system_hash == "1a263b613067895b37592994f490a2d422fdda65d42aaa2e0dafe3a4eda783ff"
    assert user_hash == "02bcb4c2256d2212770bacbb2e02db628852dfb635e43b7bfc43e654ad49a976"
    assert system_hash != _sha256(CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17)
    assert user_hash != _sha256(CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17)
