"""The small semantic taxonomy used by the deterministic narrator."""

from __future__ import annotations

import re


class NarrativeRole:
    SETTING = "SETTING"
    OBSERVATION = "OBSERVATION"
    BACKGROUND = "BACKGROUND"
    CULTURAL_PRACTICE = "CULTURAL_PRACTICE"
    AUDIENCE = "AUDIENCE"
    LITERARY_FUNCTION = "LITERARY_FUNCTION"
    CANONICAL_CONNECTION = "CANONICAL_CONNECTION"
    COVENANT_CONTEXT = "COVENANT_CONTEXT"
    ARCHAEOLOGICAL_SUPPORT = "ARCHAEOLOGICAL_SUPPORT"
    SIGNIFICANCE = "SIGNIFICANCE"
    INTERPRETIVE_CAUTION = "INTERPRETIVE_CAUTION"
    DISPUTED_VIEW = "DISPUTED_VIEW"
    SOURCE_NOTE = "SOURCE_NOTE"


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def context_type_alias(value: object) -> str:
    """Normalize public resource names to recipe names."""

    key = _key(value)
    return {
        "historical": "historical_context",
        "historical_setting": "historical_context",
        "cultural": "cultural_context",
        "literary": "literary_context",
        "archaeological": "archaeology",
        "archaeological_context": "archaeology",
        "archaeological_support": "archaeology",
        "canonical": "canonical_context",
        "covenant": "covenant_context",
    }.get(key, key)


def role_for(
    *,
    field_name: object = "",
    claim_type: object = "",
    note_type: object = "",
    object_type: object = "",
) -> str:
    """Map CKL taxonomy and field names to one presentation role."""

    field = _key(field_name)
    claim = _key(claim_type)
    note = _key(note_type)
    object_kind = _key(object_type)

    if note in {"interpretive_caution", "caution", "common_misinterpretation"}:
        return NarrativeRole.INTERPRETIVE_CAUTION
    if note in {"literary_observation", "literary_context"}:
        return NarrativeRole.LITERARY_FUNCTION
    if note in {"textual_observation", "textual", "manuscript_evidence"}:
        return NarrativeRole.OBSERVATION
    if note in {"canonical_connection", "later_reception"}:
        return NarrativeRole.CANONICAL_CONNECTION
    if note == "historical_context":
        return NarrativeRole.SETTING
    if note in {"ancient_near_east_context", "hebraic_worldview", "second_temple_context"}:
        return NarrativeRole.CULTURAL_PRACTICE

    if field in {"historical_setting", "historical_context", "date_ranges"}:
        return NarrativeRole.SETTING
    if field == "original_audience":
        return NarrativeRole.AUDIENCE
    if field in {"ancient_near_east_context", "hebraic_worldview", "second_temple_context"}:
        return NarrativeRole.CULTURAL_PRACTICE
    if field in {"cultural_context", "cultural_practice", "custom", "institution"}:
        return NarrativeRole.CULTURAL_PRACTICE
    if field in {"literary_context", "genre", "structure"} or claim in {"literary", "literary_observation"}:
        return NarrativeRole.LITERARY_FUNCTION
    if field in {"canonical_context", "canonical_role", "intertextuality", "cross_references", "new_testament_connections"}:
        return NarrativeRole.CANONICAL_CONNECTION
    if field in {"covenantal_significance", "covenant_context"}:
        return NarrativeRole.COVENANT_CONTEXT
    if field in {"archaeology", "archaeological_evidence", "archaeological_context"} or object_kind in {"archaeology", "archaeological_evidence"}:
        return NarrativeRole.ARCHAEOLOGICAL_SUPPORT
    if field in {"interpretive_disputes", "disputed_views"} or claim in {"interpretive", "disputed_view", "reception_history"}:
        return NarrativeRole.DISPUTED_VIEW
    if field in {"sources", "primary_sources"}:
        return NarrativeRole.SOURCE_NOTE

    if claim in {"historical_setting", "historical", "historical_cultural_context", "ancient_near_eastern", "ancient_near_east"}:
        return NarrativeRole.SETTING
    if claim == "historical_cultural":
        # The legacy combined type covers both social-history records and
        # book-level historical claims. Keep a claim in one context lane so
        # the companion does not repeat it under multiple headings.
        if object_kind in {"cultural_background", "institution"}:
            return NarrativeRole.CULTURAL_PRACTICE
        return NarrativeRole.SETTING
    if claim in {"cultural_practice", "cultural", "custom", "institution"}:
        return NarrativeRole.CULTURAL_PRACTICE
    if claim in {"biblical_text", "textual", "textual_observation", "manuscript", "lexical"}:
        if object_kind in {"cultural_background", "institution"}:
            return NarrativeRole.CULTURAL_PRACTICE
        return NarrativeRole.OBSERVATION
    if claim in {"canonical", "biblical_theology", "canonical_connection"}:
        return NarrativeRole.CANONICAL_CONNECTION
    if claim in {"theological", "theological_interpretation", "covenant", "covenantal_significance"}:
        return NarrativeRole.COVENANT_CONTEXT
    if claim in {"archaeology", "archaeological", "material_evidence"}:
        return NarrativeRole.ARCHAEOLOGICAL_SUPPORT

    if object_kind == "archaeology":
        return NarrativeRole.ARCHAEOLOGICAL_SUPPORT
    return NarrativeRole.BACKGROUND


def section_heading(context_type: str, role: str) -> tuple[str, str]:
    """Return stable section type and human-facing heading."""

    if role == NarrativeRole.INTERPRETIVE_CAUTION or role == NarrativeRole.DISPUTED_VIEW:
        if context_type == "archaeology":
            return "caution", "What the evidence does not establish"
        return "caution", "Important distinction"
    if context_type == "historical_context":
        if role == NarrativeRole.SIGNIFICANCE:
            return "significance", "Why it matters"
        return "historical_background", "Historical Setting"
    if context_type == "cultural_context":
        if role == NarrativeRole.SIGNIFICANCE:
            return "significance", "Why it matters"
        return "cultural_background", "Cultural Background"
    if context_type == "original_audience":
        return "original_audience", "Original Audience"
    if context_type == "literary_context":
        if role == NarrativeRole.SIGNIFICANCE:
            return "significance", "Why it matters"
        return "literary_context", "Literary Context"
    if context_type == "archaeology":
        return "archaeological_context", "Archaeological Context"
    if context_type in {"canonical_context", "covenant_context"}:
        if role == NarrativeRole.COVENANT_CONTEXT:
            return "covenant_context", "Covenant Connection"
        return "canonical_context", "Canonical Context"
    return {
        NarrativeRole.SETTING: ("setting", "Setting"),
        NarrativeRole.CULTURAL_PRACTICE: ("cultural_background", "Cultural Background"),
        NarrativeRole.AUDIENCE: ("original_audience", "Original Audience"),
        NarrativeRole.LITERARY_FUNCTION: ("literary_context", "Literary Context"),
        NarrativeRole.ARCHAEOLOGICAL_SUPPORT: ("archaeological_context", "Archaeological Context"),
        NarrativeRole.COVENANT_CONTEXT: ("covenant_context", "Covenant Context"),
        NarrativeRole.CANONICAL_CONNECTION: ("canonical_context", "Canonical Context"),
    }.get(role, ("context", "Context"))
