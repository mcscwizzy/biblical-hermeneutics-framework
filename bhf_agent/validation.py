"""Lightweight method-oriented response validation."""

from __future__ import annotations

import re

from .models import ValidationResult


ORIGINAL_CONTEXT_RE = re.compile(
    r"\b(original audience|ancient context|historical context|first-century|"
    r"second temple|ancient near eastern|israelite|early church)\b",
    re.IGNORECASE,
)
GENRE_RE = re.compile(
    r"\b(genre|gospel|epistle|letter|wisdom|poetry|narrative|law|torah|"
    r"prophecy|prophetic|apocalyptic|lament|proverb)\b",
    re.IGNORECASE,
)
OBSERVE_RE = re.compile(r"\b(observation|observe|text says|notice)\b", re.IGNORECASE)
INTERPRET_RE = re.compile(r"\b(interpretation|interpret|means|meaning)\b", re.IGNORECASE)
APPLY_RE = re.compile(r"\b(application|apply|today|modern readers)\b", re.IGNORECASE)
UNCERTAINTY_RE = re.compile(
    r"\b(may|might|probably|likely|uncertain|debated|some scholars|"
    r"majority|minority|speculation|confidence)\b",
    re.IGNORECASE,
)
OVERREACH_RE = re.compile(
    r"\b(the only faithful view|all true christians|no christian can|"
    r"the bible clearly settles every detail|anyone who disagrees)\b",
    re.IGNORECASE,
)
UNQUALIFIED_LANGUAGE_RE = re.compile(
    r"\b(the (hebrew|greek) literally means|in the original (hebrew|greek),? it means)\b",
    re.IGNORECASE,
)


def validate_response(answer: str) -> ValidationResult:
    warnings: list[str] = []
    suggestions: list[str] = []
    score = 100

    checks = [
        (
            ORIGINAL_CONTEXT_RE.search(answer),
            "Original audience or ancient context is not clear.",
            "Briefly locate the passage in its original audience and setting.",
            15,
        ),
        (
            GENRE_RE.search(answer),
            "Genre is not clearly identified.",
            "Name the passage's literary genre before interpreting it.",
            15,
        ),
        (
            OBSERVE_RE.search(answer)
            and INTERPRET_RE.search(answer)
            and APPLY_RE.search(answer),
            "Observation, interpretation, and application are not clearly distinguished.",
            "Separate observation, interpretation, and application.",
            20,
        ),
        (
            UNCERTAINTY_RE.search(answer),
            "Uncertainty or confidence level is not clearly labeled.",
            "Label consensus, majority/minority views, or uncertainty where relevant.",
            10,
        ),
    ]

    for passed, warning, suggestion, penalty in checks:
        if not passed:
            warnings.append(warning)
            suggestions.append(suggestion)
            score -= penalty

    if OVERREACH_RE.search(answer):
        warnings.append("Possible doctrinal overreach detected.")
        suggestions.append("Present responsible interpretive ranges without coercing conclusions.")
        score -= 20

    if UNQUALIFIED_LANGUAGE_RE.search(answer):
        warnings.append("Possible unsupported original-language claim detected.")
        suggestions.append("Qualify Hebrew/Greek claims and avoid saying 'literally means' without support.")
        score -= 15

    score = max(0, min(100, score))
    return ValidationResult(
        passed=score >= 70 and not OVERREACH_RE.search(answer),
        score=score,
        warnings=warnings,
        suggestions=suggestions,
    )
