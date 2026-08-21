"""Deterministic, concise certainty and dispute language."""

from __future__ import annotations

import re


CERTAINTY_LANGUAGE: dict[str, str] = {
    "textually_explicit": "",
    "strong_consensus": "",
    "probable": "Likely",
    "plausible": "Possibly",
    "disputed": "This remains debated",
    "tradition_dependent": "Interpretations differ across traditions",
    "speculative": "This is a proposal with limited evidence",
    "insufficient_evidence": "The available evidence does not establish this",
    "high": "",
    "medium": "",
    "low": "Evidence remains limited",
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


def _lower_initial_article(value: str) -> str:
    for article in ("The ", "A ", "An "):
        if value.startswith(article):
            return value[0].lower() + value[1:]
    return value


def _lower_qualification(value: str) -> str:
    if value.startswith("Christian "):
        return value
    return value[0].lower() + value[1:] if value else value


def _scoped_dispute(rationale: object) -> str:
    text = str(rationale or "").strip()
    if not text:
        return ""
    clauses = re.split(r";|,\s+while\s+|\bwhile\s+", text, flags=re.IGNORECASE)
    for clause in clauses:
        value = clause.strip(" .")
        if not any(term in value.casefold() for term in ("debated", "disagreement concerns", "remains disputed", "remains uncertain")):
            continue
        disagreement = re.match(r"disagreement concerns\s+(.*)", value, flags=re.IGNORECASE)
        if disagreement:
            subject = disagreement.group(1).strip(" .")
            return f"{subject[0].upper() + subject[1:]} remains debated."
        return f"{value[0].upper() + value[1:]}."
    return ""


def certainty_phrase(value: object) -> str:
    """Return a readable certainty phrase without exposing CKL taxonomy."""

    return CERTAINTY_LANGUAGE.get(_key(value), "")


def dispute_phrase(value: object) -> str:
    """Return a readable dispute qualification without exposing metadata keys."""

    return DISPUTE_LANGUAGE.get(_key(value), "")


def qualification_key(certainty: object = "", dispute_status: object = "") -> str:
    """Return a deterministic issue family for qualification budgeting."""

    dispute_key = _key(dispute_status)
    if dispute_key and dispute_key not in {"not_disputed", "broad_consensus"}:
        return dispute_key
    certainty_key = _key(certainty)
    if certainty_key in {
        "probable", "plausible", "disputed", "tradition_dependent",
        "speculative", "insufficient_evidence", "low",
    }:
        return certainty_key
    return ""


def qualify_text(
    text: str,
    certainty: object = "",
    dispute_status: object = "",
    *,
    include_dispute: bool = True,
    rationale: object = "",
) -> str:
    """Add only useful qualifications; authored CKL wording remains intact."""

    value = str(text or "").strip()
    if not value:
        return ""
    certainty_key = _key(certainty)
    if certainty_key in {"probable", "plausible"}:
        adverb = "Likely" if certainty_key == "probable" else "Possibly"
        if not value.casefold().startswith(adverb.casefold()):
            value = f"{adverb}, {_lower_initial_article(value)}"
    elif certainty_key in {"disputed", "tradition_dependent"}:
        qualifier = certainty_phrase(certainty_key)
        value = f"{value.rstrip('.!?')}; {qualifier[0].lower() + qualifier[1:]}."
    elif certainty_key == "speculative":
        value = f"{value.rstrip('.!?')}; this proposal has limited evidence."
    elif certainty_key == "insufficient_evidence":
        value = f"{value.rstrip('.!?')}; the available evidence does not establish it."
    elif certainty_key == "low":
        value = f"{value.rstrip('.!?')}; evidence remains limited."

    dispute = _scoped_dispute(rationale) or dispute_phrase(dispute_status)
    if include_dispute and dispute and certainty_key not in {"disputed", "tradition_dependent"}:
        lowered = value.lower()
        if not any(token in lowered for token in ("debated", "disagree", "uncertain", "differ")):
            qualification = _lower_qualification(dispute.rstrip(".!?"))
            value = f"{value.rstrip('.!?')}; {qualification}"
    if value[-1:] not in ".!?":
        value += "."
    return value
