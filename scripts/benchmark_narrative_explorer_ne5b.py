#!/usr/bin/env python3
"""Matched local benchmark and response fixture capture for NE-5B."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import sqlite3
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
from fastapi import FastAPI
from starlette.responses import JSONResponse

from bhf_agent.runtime_paths import RUNTIME_DATA_PATHS
from bhf_web.routes.narrative_explorer import register_narrative_explorer_routes
from bhf_web.services.narrative_explorer import NarrativeExplorerService
from framework.canonical_library.repository import repository_config_from_env


PILOTS = (
    ("Genesis", 1, (1, 2)),
    ("Genesis", 2, (8, 14)),
    ("Genesis", 3, (22, 24)),
    ("Genesis", 6, (1, 4)),
    ("Deuteronomy", 32, (8, 9)),
    ("Psalm", 82, (1, 8)),
    ("Exodus", 3, (1, 6)),
)
ROUTE = "/api/narrative-explorer/v1/passages/{book}/{chapter}"


class Recorder:
    def __init__(self) -> None:
        self.enabled = False
        self.stage = ""
        self.timings: Counter[str] = Counter()
        self.calls: Counter[str] = Counter()

    def reset(self) -> None:
        self.timings.clear()
        self.calls.clear()

    def timed(self, name: str, function: Callable[..., Any], *, stage: str | None = None):
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            old_stage = self.stage
            if stage is not None:
                self.stage = stage
            started = time.perf_counter_ns() if self.enabled else 0
            try:
                return function(*args, **kwargs)
            finally:
                if self.enabled:
                    self.timings[name] += time.perf_counter_ns() - started
                self.stage = old_stage

        wrapped.__name__ = getattr(function, "__name__", "wrapped")
        wrapped.__doc__ = getattr(function, "__doc__")
        return wrapped

    def counted(self, name: str, function: Callable[..., Any], *, during: str | None = None):
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if self.enabled and (during is None or self.stage == during):
                self.calls[name] += 1
            return function(*args, **kwargs)

        wrapped.__name__ = getattr(function, "__name__", "wrapped")
        wrapped.__doc__ = getattr(function, "__doc__")
        return wrapped

    def snapshot(self) -> dict[str, Any]:
        return {
            "stage_ms": {name: round(value / 1_000_000, 3) for name, value in self.timings.items()},
            "calls": dict(self.calls),
        }


RECORDER = Recorder()


def _install_instrumentation() -> None:
    import re

    import bhf_agent.archaeology_resolver as archaeology_resolver
    import bhf_agent.presentation.evidence as evidence
    import bhf_agent.presentation.eligibility as eligibility
    import bhf_agent.presentation.narrative_explorer as projection
    import bhf_agent.presentation.references as references
    import bhf_agent.presentation.relevance as relevance
    import bhf_web.map_service as map_service
    import bhf_web.services.map_matching as map_matching
    import bhf_web.services.narrative_explorer as service_module
    import framework.canonical_library.scripture as scripture

    parser = RECORDER.counted("scripture_reference_parse", scripture.parse_scripture_references)
    _replace_loaded_aliases(scripture.parse_scripture_references, parser)
    overlap = RECORDER.counted("reference_overlap", references.references_overlap)
    _replace_loaded_aliases(references.references_overlap, overlap)

    original_search = re.search
    re.search = RECORDER.counted("regex_search", original_search, during="maps")
    map_service._term_in_text = RECORDER.counted(
        "map_term_match", map_service._term_in_text, during="maps"
    )
    map_matching.term_in_text = map_service._term_in_text
    matcher_type = getattr(map_matching, "PassageTextMatcher", None)
    if matcher_type is not None:
        matcher_type.contains = RECORDER.counted(
            "map_term_match", matcher_type.contains, during="maps"
        )

    for method_name, stage in (
        ("_lookup_canonical", "ckl_lookup"),
        ("_lookup_maps", "maps"),
        ("_lookup_archaeology", "archaeology"),
    ):
        method = getattr(NarrativeExplorerService, method_name)
        setattr(NarrativeExplorerService, method_name, RECORDER.timed(stage, method, stage=stage))

    original_factory = NarrativeExplorerService._default_canonical_library
    NarrativeExplorerService._default_canonical_library = staticmethod(
        RECORDER.timed("ckl_initialization_and_fingerprint", original_factory)
    )

    projection.project_narrative_explorer = RECORDER.timed(
        "projection_total", projection.project_narrative_explorer
    )
    service_module.project_narrative_explorer = projection.project_narrative_explorer
    projection._project_ckl_lookup = RECORDER.timed(
        "ckl_applicability_filter", projection._project_ckl_lookup
    )
    original_external = projection._project_external_lookup

    def timed_external(passage: Any, lookup: Any):
        return RECORDER.timed(
            f"{lookup.domain}_external_projection", original_external
        )(passage, lookup)

    projection._project_external_lookup = timed_external

    original_validation = projection.validate_projection
    projection.validate_projection = RECORDER.timed(
        "projection_validation", original_validation
    )
    service_module.validate_projection = projection.validate_projection

    for name in ("resolve_places_for_passage", "get_map_routes_for_passage"):
        function = getattr(map_service, name)
        setattr(map_service, name, RECORDER.timed(f"{name}", function))
        setattr(service_module, name, getattr(map_service, name))

    archaeology_resolver.resolve_archaeology_evidence = RECORDER.timed(
        "archaeology_resolver", archaeology_resolver.resolve_archaeology_evidence
    )

    original_connect = sqlite3.connect
    sqlite3.connect = RECORDER.counted("sqlite_connection", original_connect)

    JSONResponse.render = RECORDER.timed("json_serialization", JSONResponse.render)


def _new_app() -> tuple[FastAPI, NarrativeExplorerService]:
    service = NarrativeExplorerService(study_db_path=RUNTIME_DATA_PATHS.study_db_path)
    app = FastAPI()
    register_narrative_explorer_routes(app, service=service)
    return app, service


async def _request(
    client: httpx.AsyncClient,
    book: str,
    chapter: int,
    bounds: tuple[int, int] | None,
    *,
    fixture_dir: Path | None,
    label: str,
    compare_fixtures: bool,
) -> dict[str, Any]:
    path = ROUTE.format(book=book, chapter=chapter)
    params = None if bounds is None else {"verse_start": bounds[0], "verse_end": bounds[1]}
    RECORDER.reset()
    RECORDER.enabled = True
    started = time.perf_counter_ns()
    response = await client.get(path, params=params)
    wall_ms = (time.perf_counter_ns() - started) / 1_000_000
    RECORDER.enabled = False
    if response.status_code != 200:
        raise RuntimeError(f"{path} returned {response.status_code}: {response.text[:300]}")

    payload = response.json()
    raw = response.content
    digest = hashlib.sha256(raw).hexdigest()
    scenario = f"{book} {chapter}" if bounds is None else f"{book} {chapter}:{bounds[0]}-{bounds[1]}"
    if fixture_dir is not None:
        safe_name = scenario.lower().replace(" ", "_").replace(":", "_").replace("-", "_")
        fixture_path = fixture_dir / f"{safe_name}.json"
        if compare_fixtures:
            expected = fixture_path.read_bytes()
            if raw != expected:
                expected_hash = hashlib.sha256(expected).hexdigest()
                raise AssertionError(
                    f"{scenario} differs from {fixture_path}: "
                    f"expected sha256 {expected_hash}, got {digest}"
                )
        else:
            fixture_path.write_bytes(raw)
    coverage = {item["domain"]: item for item in payload["coverage"]}
    return {
        "label": label,
        "scenario": scenario,
        "wall_ms": round(wall_ms, 3),
        "response_bytes": len(raw),
        "sha256": digest,
        "items": len(payload["items"]),
        "connections": len(payload["connections"]),
        "domain_states": {key: value["state"] for key, value in coverage.items()},
        "query_statuses": {key: value["query_status"] for key, value in coverage.items()},
        "section_states": {item["id"]: item["state"] for item in payload["sections"]},
        **RECORDER.snapshot(),
    }


async def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    fixture_dir = Path(args.fixtures) if args.fixtures else None
    if fixture_dir is not None:
        fixture_dir.mkdir(parents=True, exist_ok=True)

    _install_instrumentation()
    cold_samples: list[dict[str, Any]] = []
    warm_samples: list[dict[str, Any]] = []
    initialization_ms: list[float] = []
    last_service: NarrativeExplorerService | None = None

    # Fresh service and app objects measure service initialization on each
    # sample; the host OS page cache intentionally remains under normal control.
    for index in range(args.cold_repetitions):
        started = time.perf_counter_ns()
        app, service = _new_app()
        initialization_ms.append((time.perf_counter_ns() - started) / 1_000_000)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            cold_samples.append(
                await _request(
                    client,
                    "Genesis",
                    1,
                    None,
                    fixture_dir=fixture_dir if index == 0 else None,
                    label=f"cold_service_{index + 1}",
                    compare_fixtures=args.compare_fixtures,
                )
            )
        last_service = service

    assert last_service is not None
    # Reuse the last fresh service/provider instance for repeated requests.
    service = last_service
    app = FastAPI()
    register_narrative_explorer_routes(app, service=service)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        cases = [(book, chapter, None) for book, chapter, _bounds in PILOTS]
        cases.extend((book, chapter, bounds) for book, chapter, bounds in PILOTS)
        for book, chapter, bounds in cases:
            for repetition in range(args.warm_repetitions):
                fixture_target = fixture_dir if repetition == 0 else None
                warm_samples.append(
                    await _request(
                        client,
                        book,
                        chapter,
                        bounds,
                        fixture_dir=fixture_target,
                        label=f"warm_{repetition + 1}",
                    compare_fixtures=args.compare_fixtures,
                    )
                )

    return {
        "revision": args.revision,
        "branch": args.branch,
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": sys.version,
            "study_db_path": str(Path(RUNTIME_DATA_PATHS.study_db_path).resolve()),
            "study_db_sha256": _sha256(Path(RUNTIME_DATA_PATHS.study_db_path)),
            "ckl_backend_config": repository_config_from_env().backend,
            "ckl_db_path": str(Path(repository_config_from_env().database_path).resolve()),
            "ckl_db_sha256": _sha256(Path(repository_config_from_env().database_path)),
            "api_route": "/api/narrative-explorer/v1/passages/{book}/{chapter}",
            "schema_version": "1.0",
            "classification_policy": "ne5a-1",
            "os_page_cache_flushed": False,
        },
        "repetitions": {
            "cold_service": args.cold_repetitions,
            "warm_each_scope": args.warm_repetitions,
        },
        "service_initialization_ms": [round(value, 3) for value in initialization_ms],
        "cold_first_passage": cold_samples,
        "warm_requests": warm_samples,
        "summary": _summarize(initialization_ms, cold_samples, warm_samples),
        "database_hashes_after": {
            "study_db_sha256": _sha256(Path(RUNTIME_DATA_PATHS.study_db_path)),
            "ckl_db_sha256": _sha256(Path(repository_config_from_env().database_path)),
        },
    }


def _summarize(
    initialization_ms: list[float],
    cold_samples: list[dict[str, Any]],
    warm_samples: list[dict[str, Any]],
) -> dict[str, Any]:
    by_scope: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in warm_samples:
        by_scope[sample["scenario"]].append(sample)
    warm_walls = [sample["wall_ms"] for sample in warm_samples]

    def stats(values: list[float]) -> dict[str, float]:
        ordered = sorted(values)
        return {
            "median_ms": round(statistics.median(ordered), 3),
            "min_ms": round(min(ordered), 3),
            "max_ms": round(max(ordered), 3),
            "p95_ms": round(ordered[max(0, int(0.95 * len(ordered) + 0.999) - 1)], 3)
            if len(ordered) >= 20
            else None,
        }

    return {
        "service_initialization": stats(initialization_ms),
        "cold_first_passage": stats([sample["wall_ms"] for sample in cold_samples]),
        "warm_all_requests": stats(warm_walls),
        "warm_by_scope": {
            name: {
                **stats([sample["wall_ms"] for sample in values]),
                "response_bytes": values[0]["response_bytes"],
                "items": values[0]["items"],
                "connections": values[0]["connections"],
                "sha256": values[0]["sha256"],
            }
            for name, values in sorted(by_scope.items())
        },
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _replace_loaded_aliases(original: Callable[..., Any], replacement: Callable[..., Any]) -> None:
    """Count calls through direct imports as well as the defining module."""

    for module in tuple(sys.modules.values()):
        namespace = getattr(module, "__dict__", None)
        if not namespace:
            continue
        for name, value in tuple(namespace.items()):
            if value is original:
                setattr(module, name, replacement)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fixtures")
    parser.add_argument(
        "--compare-fixtures",
        action="store_true",
        help="compare raw response bytes with existing fixtures instead of writing them",
    )
    parser.add_argument("--cold-repetitions", type=int, default=3)
    parser.add_argument("--warm-repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.compare_fixtures and not args.fixtures:
        parser.error("--compare-fixtures requires --fixtures")
    if args.compare_fixtures and not Path(args.fixtures).is_dir():
        parser.error("--compare-fixtures requires an existing fixture directory")
    result = asyncio.run(run_benchmark(args))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
