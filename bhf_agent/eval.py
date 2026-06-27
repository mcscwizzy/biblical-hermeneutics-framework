"""Local deterministic eval helpers for BHF Agent answers."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import AgentConfig
from .runner import BHFAgent


@dataclass(frozen=True)
class EvalBehavior:
    id: str
    description: str
    pattern: str | None = None
    keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvalFixture:
    id: str
    question: str
    profile: str
    answer_mode: str
    expected_behaviors: list[EvalBehavior]
    forbidden_behaviors: list[EvalBehavior]
    pass_threshold: int


@dataclass(frozen=True)
class BehaviorMatch:
    id: str
    description: str
    matched: bool


@dataclass(frozen=True)
class EvalResult:
    fixture_id: str
    score: int
    passed: bool
    pass_threshold: int
    expected: list[BehaviorMatch]
    forbidden: list[BehaviorMatch]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_fixture(path: str | Path) -> EvalFixture:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("eval fixture must be a JSON object")
    required = {
        "id",
        "question",
        "profile",
        "answer_mode",
        "expected_behaviors",
        "forbidden_behaviors",
        "pass_threshold",
    }
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"eval fixture missing field(s): {', '.join(missing)}")
    return EvalFixture(
        id=str(data["id"]),
        question=str(data["question"]),
        profile=str(data["profile"]),
        answer_mode=str(data["answer_mode"]),
        expected_behaviors=[
            _behavior_from_value(value) for value in data["expected_behaviors"]
        ],
        forbidden_behaviors=[
            _behavior_from_value(value) for value in data["forbidden_behaviors"]
        ],
        pass_threshold=int(data["pass_threshold"]),
    )


def score_answer(answer_text: str, fixture: EvalFixture) -> EvalResult:
    expected = [
        BehaviorMatch(
            id=behavior.id,
            description=behavior.description,
            matched=matches_behavior(answer_text, behavior),
        )
        for behavior in fixture.expected_behaviors
    ]
    forbidden = [
        BehaviorMatch(
            id=behavior.id,
            description=behavior.description,
            matched=matches_behavior(answer_text, behavior),
        )
        for behavior in fixture.forbidden_behaviors
    ]

    expected_total = len(expected)
    expected_hits = sum(1 for result in expected if result.matched)
    base_score = 100 if expected_total == 0 else round(expected_hits / expected_total * 100)
    penalty = 20 * sum(1 for result in forbidden if result.matched)
    score = max(0, min(100, base_score - penalty))
    return EvalResult(
        fixture_id=fixture.id,
        score=score,
        passed=score >= fixture.pass_threshold,
        pass_threshold=fixture.pass_threshold,
        expected=expected,
        forbidden=forbidden,
    )


def matches_behavior(answer_text: str, behavior: EvalBehavior) -> bool:
    if behavior.pattern:
        return re.search(behavior.pattern, answer_text, flags=re.IGNORECASE | re.DOTALL) is not None
    if behavior.keywords:
        normalized = answer_text.lower()
        return all(keyword.lower() in normalized for keyword in behavior.keywords)
    return behavior.description.lower() in answer_text.lower()


def answer_from_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def answer_from_agent(fixture: EvalFixture, config_path: str | Path) -> str:
    config = AgentConfig.from_json_file(config_path).with_overrides(
        profile=fixture.profile,
        answer_mode=fixture.answer_mode,
    )
    return BHFAgent(config).ask(fixture.question).answer_text


def format_human_summary(result: EvalResult) -> str:
    lines = [
        f"Fixture: {result.fixture_id}",
        f"Score: {result.score}/{result.pass_threshold}",
        f"Passed: {str(result.passed).lower()}",
        "",
        "Expected behaviors:",
    ]
    for item in result.expected:
        mark = "PASS" if item.matched else "MISS"
        lines.append(f"- {mark}: {item.id} - {item.description}")
    lines.append("")
    lines.append("Forbidden behaviors:")
    if not result.forbidden:
        lines.append("- none")
    for item in result.forbidden:
        mark = "HIT" if item.matched else "clear"
        lines.append(f"- {mark}: {item.id} - {item.description}")
    return "\n".join(lines)


def result_to_json(result: EvalResult) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True)


def _behavior_from_value(value: Any) -> EvalBehavior:
    if isinstance(value, str):
        return EvalBehavior(id=_slugify(value), description=value)
    if not isinstance(value, dict):
        raise ValueError("eval behavior must be a string or object")
    behavior_id = str(value.get("id") or _slugify(str(value.get("description", ""))))
    description = str(value.get("description") or behavior_id)
    pattern = value.get("pattern")
    keywords = value.get("keywords", [])
    if not isinstance(keywords, list):
        raise ValueError(f"keywords for behavior {behavior_id} must be a list")
    return EvalBehavior(
        id=behavior_id,
        description=description,
        pattern=str(pattern) if pattern is not None else None,
        keywords=[str(keyword) for keyword in keywords],
    )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "behavior"
