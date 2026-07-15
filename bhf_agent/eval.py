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
class EvalMetadataCheck:
    id: str
    description: str
    field: str
    equals: Any | None = None
    any_of: list[Any] = field(default_factory=list)
    contains: list[Any] = field(default_factory=list)
    excludes: list[Any] = field(default_factory=list)
    at_least: float | int | None = None
    at_most: float | int | None = None
    pattern: str | None = None
    allow_missing: bool = False


@dataclass(frozen=True)
class EvalFixture:
    id: str
    question: str
    profile: str
    answer_mode: str
    expected_behaviors: list[EvalBehavior]
    forbidden_behaviors: list[EvalBehavior]
    pass_threshold: int
    config_overrides: dict[str, Any] = field(default_factory=dict)
    metadata_checks: list[EvalMetadataCheck] = field(default_factory=list)


@dataclass(frozen=True)
class BehaviorMatch:
    id: str
    description: str
    matched: bool


@dataclass(frozen=True)
class MetadataMatch:
    id: str
    description: str
    field: str
    observed: Any
    matched: bool
    details: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvalResult:
    fixture_id: str
    score: int
    passed: bool
    pass_threshold: int
    expected: list[BehaviorMatch]
    forbidden: list[BehaviorMatch]
    metadata_checks: list[MetadataMatch] = field(default_factory=list)
    metadata_passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvalRun:
    answer_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalSuite:
    id: str
    description: str
    cases: list[EvalFixture]


@dataclass(frozen=True)
class EvalSuiteResult:
    suite_id: str
    description: str
    results: list[EvalResult]
    passed_count: int
    failed_count: int
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_fixture(path: str | Path) -> EvalFixture:
    return _fixture_from_mapping(_load_json(path))


def load_suite(path: str | Path) -> EvalSuite:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise ValueError("eval suite must be a JSON object")
    required = {"id", "cases"}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"eval suite missing field(s): {', '.join(missing)}")
    cases = data["cases"]
    if not isinstance(cases, list):
        raise ValueError("eval suite cases must be a list")
    return EvalSuite(
        id=str(data["id"]),
        description=str(data.get("description") or ""),
        cases=[_fixture_from_mapping(value) for value in cases],
    )


def score_answer(
    answer_text: str,
    fixture: EvalFixture,
    metadata: dict[str, Any] | None = None,
) -> EvalResult:
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
    metadata_checks = [
        _score_metadata_check(metadata, check) for check in fixture.metadata_checks
    ]

    expected_total = len(expected)
    expected_hits = sum(1 for result in expected if result.matched)
    base_score = 100 if expected_total == 0 else round(expected_hits / expected_total * 100)
    penalty = 20 * sum(1 for result in forbidden if result.matched)
    score = max(0, min(100, base_score - penalty))
    metadata_passed = all(match.matched for match in metadata_checks) if metadata_checks else True
    return EvalResult(
        fixture_id=fixture.id,
        score=score,
        passed=score >= fixture.pass_threshold and metadata_passed,
        pass_threshold=fixture.pass_threshold,
        expected=expected,
        forbidden=forbidden,
        metadata_checks=metadata_checks,
        metadata_passed=metadata_passed,
    )


def run_agent(fixture: EvalFixture, config: AgentConfig | str | Path) -> EvalRun:
    if isinstance(config, AgentConfig):
        base_config = config
    else:
        base_config = AgentConfig.from_json_file(config)
    run_config = base_config.with_overrides(
        **fixture.config_overrides,
        profile=fixture.profile,
        answer_mode=fixture.answer_mode,
    )
    result = BHFAgent(run_config).ask(fixture.question)
    metadata = getattr(result, "model_metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return EvalRun(answer_text=result.answer_text, metadata=metadata)


def run_suite(suite: EvalSuite, config: AgentConfig | str | Path) -> EvalSuiteResult:
    results: list[EvalResult] = []
    for fixture in suite.cases:
        run = run_agent(fixture, config)
        results.append(score_answer(run.answer_text, fixture, metadata=run.metadata))
    passed_count = sum(1 for result in results if result.passed)
    failed_count = len(results) - passed_count
    return EvalSuiteResult(
        suite_id=suite.id,
        description=suite.description,
        results=results,
        passed_count=passed_count,
        failed_count=failed_count,
        passed=failed_count == 0,
    )


def answer_from_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def answer_from_agent(fixture: EvalFixture, config_path: str | Path) -> str:
    return run_agent(fixture, config_path).answer_text


def format_human_summary(result: EvalResult) -> str:
    lines = [
        f"Fixture: {result.fixture_id}",
        f"Score: {result.score}/{result.pass_threshold}",
        f"Passed: {str(result.passed).lower()}",
        f"Metadata passed: {str(result.metadata_passed).lower()}",
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
    lines.append("")
    lines.append("Metadata checks:")
    if not result.metadata_checks:
        lines.append("- none")
    for item in result.metadata_checks:
        mark = "PASS" if item.matched else "MISS"
        lines.append(f"- {mark}: {item.id} - {item.description}")
        lines.append(f"  Field: {item.field}")
        lines.append(f"  Observed: {_format_observed_value(item.observed)}")
        if item.details:
            lines.append(f"  Details: {'; '.join(item.details)}")
    return "\n".join(lines)


def format_suite_summary(result: EvalSuiteResult) -> str:
    lines = [
        f"Suite: {result.suite_id}",
        f"Passed: {str(result.passed).lower()}",
        f"Cases passed: {result.passed_count}/{len(result.results)}",
        "",
    ]
    for item in result.results:
        lines.append(
            f"- {item.fixture_id}: {'PASS' if item.passed else 'FAIL'} "
            f"({item.score}/{item.pass_threshold})"
        )
        if item.metadata_checks:
            lines.append(
                f"  Metadata: {'passed' if item.metadata_passed else 'failed'}"
            )
    return "\n".join(lines)


def result_to_json(result: EvalResult) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True)


def suite_result_to_json(result: EvalSuiteResult) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True)


def matches_behavior(answer_text: str, behavior: EvalBehavior) -> bool:
    if behavior.pattern:
        return (
            re.search(behavior.pattern, answer_text, flags=re.IGNORECASE | re.DOTALL)
            is not None
        )
    if behavior.keywords:
        normalized = answer_text.lower()
        return all(keyword.lower() in normalized for keyword in behavior.keywords)
    return behavior.description.lower() in answer_text.lower()


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _fixture_from_mapping(data: Any) -> EvalFixture:
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
    config_overrides = data.get("config_overrides", {})
    if config_overrides is None:
        config_overrides = {}
    if not isinstance(config_overrides, dict):
        raise ValueError("eval fixture config_overrides must be an object")
    metadata_checks = data.get("metadata_checks", [])
    if metadata_checks is None:
        metadata_checks = []
    if not isinstance(metadata_checks, list):
        raise ValueError("eval fixture metadata_checks must be a list")
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
        config_overrides=dict(config_overrides),
        metadata_checks=[_metadata_check_from_value(value) for value in metadata_checks],
    )


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


def _metadata_check_from_value(value: Any) -> EvalMetadataCheck:
    if not isinstance(value, dict):
        raise ValueError("eval metadata check must be an object")
    field_name = str(value.get("field") or "").strip()
    if not field_name:
        raise ValueError("eval metadata check field is required")
    check_id = str(value.get("id") or _slugify(field_name))
    description = str(value.get("description") or field_name)
    return EvalMetadataCheck(
        id=check_id,
        description=description,
        field=field_name,
        equals=value.get("equals"),
        any_of=_coerce_list_value(value.get("any_of")),
        contains=_coerce_list_value(value.get("contains")),
        excludes=_coerce_list_value(value.get("excludes")),
        at_least=_coerce_number(value.get("at_least")),
        at_most=_coerce_number(value.get("at_most")),
        pattern=str(value.get("pattern")) if value.get("pattern") is not None else None,
        allow_missing=bool(value.get("allow_missing", False)),
    )


def _coerce_list_value(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _coerce_number(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"metadata check comparison must be numeric: {value!r}") from exc
    if number.is_integer():
        return int(number)
    return number


def _score_metadata_check(
    metadata: dict[str, Any] | None,
    check: EvalMetadataCheck,
) -> MetadataMatch:
    observed, found = _lookup_metadata_value(metadata, check.field)
    if not found:
        if check.allow_missing:
            return MetadataMatch(
                id=check.id,
                description=check.description,
                field=check.field,
                observed=None,
                matched=True,
                details=["missing value allowed"],
            )
        return MetadataMatch(
            id=check.id,
            description=check.description,
            field=check.field,
            observed=None,
            matched=False,
            details=["field missing"],
        )

    normalized_observed = _normalize_metadata_value(observed)

    if check.equals is not None:
        expected = _normalize_metadata_value(check.equals)
        if normalized_observed != expected:
            return MetadataMatch(
                id=check.id,
                description=check.description,
                field=check.field,
                observed=observed,
                matched=False,
                details=[f"expected {expected!r}"],
            )

    if check.any_of:
        allowed = [_normalize_metadata_value(value) for value in check.any_of]
        if normalized_observed not in allowed:
            return MetadataMatch(
                id=check.id,
                description=check.description,
                field=check.field,
                observed=observed,
                matched=False,
                details=[f"expected one of {[_metadata_repr(value) for value in allowed]!r}"],
            )

    if check.contains:
        missing = [
            value
            for value in check.contains
            if not _metadata_contains(observed, value)
        ]
        if missing:
            return MetadataMatch(
                id=check.id,
                description=check.description,
                field=check.field,
                observed=observed,
                matched=False,
                details=[
                    f"missing {[_normalize_metadata_value(value) for value in missing]!r}"
                ],
            )

    if check.excludes:
        forbidden = [
            value
            for value in check.excludes
            if _metadata_contains(observed, value)
        ]
        if forbidden:
            return MetadataMatch(
                id=check.id,
                description=check.description,
                field=check.field,
                observed=observed,
                matched=False,
                details=[
                    f"forbidden {[_normalize_metadata_value(value) for value in forbidden]!r}"
                ],
            )

    if check.pattern:
        if (
            re.search(
                check.pattern,
                _metadata_string(observed),
                flags=re.IGNORECASE | re.DOTALL,
            )
            is None
        ):
            return MetadataMatch(
                id=check.id,
                description=check.description,
                field=check.field,
                observed=observed,
                matched=False,
                details=[f"pattern {check.pattern!r} did not match"],
            )

    observed_count = _metadata_count(observed)
    if check.at_least is not None:
        if observed_count is None or observed_count < check.at_least:
            return MetadataMatch(
                id=check.id,
                description=check.description,
                field=check.field,
                observed=observed,
                matched=False,
                details=[
                    f"expected at least {check.at_least}, observed {observed_count}"
                ],
            )

    if check.at_most is not None:
        if observed_count is None or observed_count > check.at_most:
            return MetadataMatch(
                id=check.id,
                description=check.description,
                field=check.field,
                observed=observed,
                matched=False,
                details=[
                    f"expected at most {check.at_most}, observed {observed_count}"
                ],
            )

    return MetadataMatch(
        id=check.id,
        description=check.description,
        field=check.field,
        observed=observed,
        matched=True,
        details=[],
    )


def _lookup_metadata_value(metadata: dict[str, Any] | None, field: str) -> tuple[Any, bool]:
    if not metadata:
        return None, False
    current: Any = metadata
    for part in field.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if 0 <= index < len(current):
                current = current[index]
                continue
            return None, False
        return None, False
    return current, True


def _normalize_metadata_value(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, dict):
        return {str(key): _normalize_metadata_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_normalize_metadata_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_metadata_value(item) for item in value)
    if isinstance(value, set):
        return sorted(_normalize_metadata_value(item) for item in value)
    return value


def _metadata_contains(observed: Any, expected: Any) -> bool:
    normalized_expected = _normalize_metadata_value(expected)
    if isinstance(observed, (list, tuple, set)):
        normalized_observed = [_normalize_metadata_value(item) for item in observed]
        return normalized_expected in normalized_observed
    normalized_observed = _normalize_metadata_value(observed)
    if isinstance(normalized_observed, dict):
        haystack = json.dumps(
            normalized_observed,
            sort_keys=True,
            ensure_ascii=True,
        )
        return str(normalized_expected) in haystack
    return str(normalized_expected) in str(normalized_observed)


def _metadata_count(observed: Any) -> float | None:
    if isinstance(observed, (list, tuple, set, dict, str)):
        return float(len(observed))
    if isinstance(observed, (int, float)):
        return float(observed)
    return None


def _metadata_string(observed: Any) -> str:
    if isinstance(observed, (dict, list, tuple, set)):
        return json.dumps(
            _normalize_metadata_value(observed),
            sort_keys=True,
            ensure_ascii=True,
        )
    return str(observed)


def _format_observed_value(value: Any) -> str:
    if isinstance(value, (dict, list, tuple, set)):
        return _metadata_string(value)
    return str(value)


def _metadata_repr(value: Any) -> str:
    if isinstance(value, (dict, list, tuple, set)):
        return _metadata_string(value)
    return repr(value)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "behavior"
