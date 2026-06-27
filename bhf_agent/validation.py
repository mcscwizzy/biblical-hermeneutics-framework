"""Lightweight method-oriented response validation."""

from __future__ import annotations

import re

from .models import GenreContext, QuestionContext, ReferenceContext, ValidationResult


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
CAUTIONS_HEADING_RE = re.compile(
    r"(?i)(?:^|\s)#{1,6}\s*(?:5\.\s*)?cautions(?:\s*/\s*uncertainty)?\b",
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
ORIGINAL_LANGUAGE_WORD_RE = re.compile(
    r"\b(hebrew|greek|ruach|rûaḥ|ruaḥ|nephesh|shalom|hesed|elohim|yahweh|"
    r"agape|logos|pneuma|ekklesia|charis|pistis)\b|[\u0590-\u05ff]|[\u0370-\u03ff]",
    re.IGNORECASE,
)
SEMANTIC_RANGE_RE = re.compile(
    r"\b(semantic range|range of meaning|basic meaning|can mean|may mean|"
    r"means|meaning|wind|spirit|breath|love|word|grace|faith)\b",
    re.IGNORECASE,
)
CONTEXT_DEPENDENCE_RE = re.compile(
    r"\b(context matters|depends on (?:the )?(?:passage )?context|"
    r"meaning depends|in context|usage depends)\b",
    re.IGNORECASE,
)
LITERALLY_HOLY_SPIRIT_RE = re.compile(
    r"\b(?:ruach|rûaḥ|ruaḥ|pneuma)?[^.\n]{0,40}literally means[^.\n]{0,40}holy spirit\b",
    re.IGNORECASE,
)
UNQUALIFIED_LITERALLY_RE = re.compile(r"\bliterally means\b", re.IGNORECASE)
NEPHESH_QOL_RE = re.compile(r"\b(nephesh|qol)\b", re.IGNORECASE)
RUACH_RE = re.compile(r"\b(ruach|rûaḥ|ruaḥ)\b|רוּחַ", re.IGNORECASE)
NEPHESH_QOL_PRIMARY_RE = re.compile(
    r"\b(nephesh|qol)\b[^.\n]{0,80}\b(?:also|primary|answer|word|term|consider)\b|"
    r"\b(?:also|primary|answer|word|term|consider)\b[^.\n]{0,80}\b(nephesh|qol)\b",
    re.IGNORECASE,
)
HISTORICAL_SETTING_RE = re.compile(
    r"\b(historical|cultural|ancient|setting|background|near eastern|greco-roman|first-century)\b",
    re.IGNORECASE,
)
LITERARY_SETTING_RE = re.compile(
    r"\b(literary setting|literary context|book context|genre|narrative|epistle|poetry|torah)\b",
    re.IGNORECASE,
)
KEY_BIBLICAL_DATA_RE = re.compile(
    r"\b(key biblical data|biblical data|scripture|passage|texts?|paul|jesus|old testament|new testament)\b",
    re.IGNORECASE,
)
MAJOR_VIEWS_RE = re.compile(
    r"\b(major views|interpretive views|some interpreters|others|range of interpretation|debated)\b",
    re.IGNORECASE,
)
APPLICATION_SEPARATION_RE = re.compile(
    r"\b(application|apply|today|modern readers|responsible application)\b",
    re.IGNORECASE,
)


def validate_response(
    answer: str,
    question_context: QuestionContext | None = None,
    reference_context: ReferenceContext | None = None,
    genre_context: GenreContext | None = None,
) -> ValidationResult:
    question_type = (
        question_context.question_type
        if question_context and question_context.question_type
        else "passage_study"
    )
    if question_type == "word_study":
        return _validate_word_study(answer, question_context)
    if question_type == "historical_context":
        return _validate_historical_context(answer)
    if question_type == "topic_study":
        return _validate_topic_study(answer)
    return _validate_passage_study(answer)


def _validate_passage_study(answer: str) -> ValidationResult:
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


def _validate_word_study(
    answer: str,
    question_context: QuestionContext | None,
) -> ValidationResult:
    warnings: list[str] = []
    suggestions: list[str] = []
    score = 100

    checks = [
        (
            ORIGINAL_LANGUAGE_WORD_RE.search(answer),
            "Original-language word or transliteration is not clear.",
            "Give the Hebrew/Greek word or a cautious transliteration when known.",
            20,
        ),
        (
            SEMANTIC_RANGE_RE.search(answer),
            "Basic meaning or semantic range is not clear.",
            "Summarize the word's basic semantic range.",
            20,
        ),
        (
            CONTEXT_DEPENDENCE_RE.search(answer),
            "Context dependence is not clearly explained.",
            "State that word meaning depends on passage context.",
            20,
        ),
        (
            UNCERTAINTY_RE.search(answer) or CAUTIONS_HEADING_RE.search(answer),
            "Caution or uncertainty is not clearly labeled.",
            "Add cautious language where the lexical claim is limited.",
            10,
        ),
    ]
    for passed, warning, suggestion, penalty in checks:
        if not passed:
            warnings.append(warning)
            suggestions.append(suggestion)
            score -= penalty

    if LITERALLY_HOLY_SPIRIT_RE.search(answer):
        warnings.append("Possible overclaim: ruach/pneuma is equated too directly with Holy Spirit.")
        suggestions.append("Distinguish lexical range from later theological categories.")
        score -= 20
    elif UNQUALIFIED_LITERALLY_RE.search(answer) or UNQUALIFIED_LANGUAGE_RE.search(answer):
        warnings.append("Possible unsupported original-language claim detected.")
        suggestions.append("Qualify Hebrew/Greek claims and avoid unqualified 'literally means' language.")
        score -= 15

    if _is_hebrew_spirit_wind_question(question_context) and not RUACH_RE.search(answer):
        warnings.append("The Hebrew spirit/wind answer does not clearly mention ruach.")
        suggestions.append("Name ruach as the primary Hebrew lexical target for spirit/wind.")
        score -= 20

    if _is_spirit_wind_question(question_context) and _has_nephesh_qol_primary_issue(answer):
        warnings.append(
            "The answer may be treating nephesh or qol as primary answers for spirit/wind."
        )
        suggestions.append(
            "Present nephesh or qol only as cautionary contrasts unless a specific passage requires them."
        )
        score -= 10

    score = max(0, min(100, score))
    return ValidationResult(
        passed=score >= 70,
        score=score,
        warnings=warnings,
        suggestions=suggestions,
    )


def _validate_historical_context(answer: str) -> ValidationResult:
    return _score_checks(
        answer,
        [
            (
                HISTORICAL_SETTING_RE.search(answer),
                "Historical or cultural setting is not clear.",
                "Describe the historical/cultural setting briefly.",
                20,
            ),
            (
                LITERARY_SETTING_RE.search(answer),
                "Literary setting is not clear.",
                "Locate the passage or book in its literary setting.",
                20,
            ),
            (
                UNCERTAINTY_RE.search(answer),
                "Uncertainty or debated limits are not clear.",
                "State what is debated or uncertain.",
                15,
            ),
        ],
    )


def _validate_topic_study(answer: str) -> ValidationResult:
    return _score_checks(
        answer,
        [
            (
                KEY_BIBLICAL_DATA_RE.search(answer),
                "Key biblical data is not clear.",
                "Name representative biblical texts or categories.",
                20,
            ),
            (
                MAJOR_VIEWS_RE.search(answer),
                "Major interpretive views or range of interpretation is not clear.",
                "Mention major views or explain the range of interpretation.",
                20,
            ),
            (
                APPLICATION_SEPARATION_RE.search(answer),
                "Application is not clearly separated from original meaning.",
                "Separate responsible application from original meaning.",
                15,
            ),
            (
                UNCERTAINTY_RE.search(answer),
                "Uncertainty or limits are not clear.",
                "Name limits or debated areas.",
                10,
            ),
        ],
    )


def _score_checks(answer: str, checks) -> ValidationResult:
    warnings: list[str] = []
    suggestions: list[str] = []
    score = 100

    for passed, warning, suggestion, penalty in checks:
        if not passed:
            warnings.append(warning)
            suggestions.append(suggestion)
            score -= penalty

    if OVERREACH_RE.search(answer):
        warnings.append("Possible doctrinal overreach detected.")
        suggestions.append("Present responsible interpretive ranges without coercing conclusions.")
        score -= 20

    score = max(0, min(100, score))
    return ValidationResult(
        passed=score >= 70 and not OVERREACH_RE.search(answer),
        score=score,
        warnings=warnings,
        suggestions=suggestions,
    )


def _is_spirit_wind_question(question_context: QuestionContext | None) -> bool:
    if not question_context:
        return False
    return bool({"spirit", "wind"}.intersection(set(question_context.target_terms)))


def _is_hebrew_spirit_wind_question(question_context: QuestionContext | None) -> bool:
    if not _is_spirit_wind_question(question_context):
        return False
    return (question_context.target_language or "").lower() == "hebrew"


def _has_nephesh_qol_primary_issue(answer: str) -> bool:
    if not NEPHESH_QOL_RE.search(answer):
        return False
    lowered = answer.lower()
    if (
        "not the normal hebrew word" in lowered
        or "not primary" in lowered
        or "not a primary" in lowered
        or "not the primary" in lowered
    ):
        return False
    return bool(NEPHESH_QOL_PRIMARY_RE.search(answer))
