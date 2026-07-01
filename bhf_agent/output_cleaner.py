"""Conservative cleanup for leaked runtime instruction text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


INTERNAL_HEADINGS = (
    "BHF Agent Runtime Instructions",
    "Minimal Runtime Strategy",
    "Standard Runtime Strategy",
    "Scholar Runtime Strategy",
    "Answer Generation",
)

ANSWER_HEADING_RE = re.compile(
    r"^\s*#{0,6}\s*(?:1\.\s*)?"
    r"(?:Short Answer|Genre|Historical / Cultural Setting|Key Biblical Data)\b",
    re.IGNORECASE,
)


@dataclass
class OutputCleanupResult:
    text: str
    applied: bool = False
    removed_headings: list[str] = field(default_factory=list)


def clean_model_output(text: str) -> OutputCleanupResult:
    """Remove obvious leading leaked runtime instructions.

    This intentionally only trims when the model starts with known internal
    headings and a user-facing answer heading appears later. It does not rewrite
    answer content or remove normal method explanations inside the answer.
    """

    if not text:
        return OutputCleanupResult(text=text)

    lines = text.splitlines()
    first_content_index = _first_content_line(lines)
    if first_content_index is None:
        return OutputCleanupResult(text=text)

    first_heading = _internal_heading(lines[first_content_index])
    if not first_heading:
        return OutputCleanupResult(text=text)

    answer_index = _first_answer_heading(lines, first_content_index + 1)
    if answer_index is None:
        return OutputCleanupResult(text=text)

    cleaned = "\n".join(lines[answer_index:]).strip()
    return OutputCleanupResult(
        text=cleaned,
        applied=cleaned != text.strip(),
        removed_headings=_internal_headings_in(lines[first_content_index:answer_index]),
    )


def _first_content_line(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if line.strip():
            return index
    return None


def _first_answer_heading(lines: list[str], start_index: int) -> int | None:
    for index in range(start_index, len(lines)):
        if ANSWER_HEADING_RE.search(lines[index]):
            return index
    return None


def _internal_headings_in(lines: list[str]) -> list[str]:
    headings: list[str] = []
    for line in lines:
        heading = _internal_heading(line)
        if heading and heading not in headings:
            headings.append(heading)
    return headings


def _internal_heading(line: str) -> str | None:
    normalized = line.strip().lstrip("#").strip().rstrip(":")
    for heading in INTERNAL_HEADINGS:
        if normalized.lower() == heading.lower():
            return heading
    return None
