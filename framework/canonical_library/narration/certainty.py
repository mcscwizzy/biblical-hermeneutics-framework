"""Deterministic, concise certainty and dispute language."""

from __future__ import annotations

import re


CERTAINTY_LANGUAGE: dict[str, str] = {
    "textually_explicit": "The text explicitly states",
    "strong_consensus": "There is broad agreement that",
    "probable": "The evidence likely indicates",
    "plausible": "One plausible explanation is",
    "disputed": "Scholars disagree about this point",
    "tradition_dependent": "Interpretations differ across traditions",
    "speculative": "This has been proposed, but the evidence is limited",
    "insufficient_evidence": "The available evidence does not establish",
    "high": "The evidence is strong",
    "medium": "The evidence is moderate",
    "low": "The evidence is limited",
    "unknown": "",
}

DISPUTE_LANGUAGE: dict[str, str] = {
    "minor_scholarly_disagreement": "Some details remain debated.",
    "major_scholarly_disagreement": "Scholars disagree about the precise reconstruction.",
    "textual_variant": "Ancient textual witnesses differ at this point.",
    "historical_uncertainty": "The historical reconstruction remains uncertain.",
    "chronological_uncertainty": "The chronology remains debated.",
    "archaeological_uncertainty": "The archaeological correlation remains debated.",
    "lexical_uncertainty": "The lexical evidence allows more than one interpretation.",
    "denominational_disagreement": "Christian traditions interpret this differently.",
    "disputed": "The point remains disputed.",
    "minority": "A minority interpretation differs on this point.",
    "broad_consensus": "The main point is broadly accepted, although details may differ.",
}


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def certainty_phrase(value: object) -> str:
    """Return a readable certainty phrase without exposing CKL taxonomy."""

    return CERTAINTY_LANGUAGE.get(_key(value), "")


def dispute_phrase(value: object) -> str:
    """Return a readable dispute qualification without exposing metadata keys."""

    return DISPUTE_LANGUAGE.get(_key(value), "")


def qualify_text(text: str, certainty: object = "", dispute_status: object = "") -> str:
    """Add only useful qualifications; authored CKL wording remains intact."""

    value = str(text or "").strip()
    if not value:
        return ""
    certainty_key = _key(certainty)
    prefix = certainty_phrase(certainty)
    visible_prefixes = {
        "textually_explicit",
        "strong_consensus",
        "probable",
        "plausible",
        "disputed",
        "tradition_dependent",
        "speculative",
        "insufficient_evidence",
    }
    if certainty_key in visible_prefixes and prefix and not value.lower().startswith(prefix.lower()):
        if certainty_key == "strong_consensus":
            value = f"{prefix} {value[0].lower() + value[1:] if value else value}"
        else:
            value = f"{prefix}: {value}"

    dispute = dispute_phrase(dispute_status)
    if dispute and certainty_key not in {"disputed", "tradition_dependent"}:
        lowered = value.lower()
        if not any(token in lowered for token in ("debated", "disagree", "uncertain", "differ")):
            qualification = dispute.rstrip('.!?')
            if qualification:
                qualification = qualification[0].lower() + qualification[1:]
            value = f"{value.rstrip('.!?')}; {qualification}"
    if value[-1:] not in ".!?":
        value += "."
    return value
