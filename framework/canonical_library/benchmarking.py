"""Repeatable, dependency-free retrieval latency measurements for CKL."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


def load_retrieval_corpus(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate a versioned retrieval benchmark corpus."""

    corpus = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(corpus, dict) or not isinstance(corpus.get("queries"), list):
        raise ValueError("retrieval benchmark corpus must contain a queries list")
    seen: set[str] = set()
    for position, case in enumerate(corpus["queries"]):
        if not isinstance(case, dict):
            raise ValueError(f"benchmark query {position} must be an object")
        case_id = str(case.get("id") or "").strip()
        query = str(case.get("query") or "").strip()
        if not case_id or not query:
            raise ValueError(f"benchmark query {position} requires id and query")
        if case_id in seen:
            raise ValueError(f"duplicate benchmark query id: {case_id}")
        seen.add(case_id)
    return corpus


def run_retrieval_benchmark(
    search: Callable[[str, int], Sequence[Any]],
    corpus: Mapping[str, Any],
    *,
    iterations: int = 5,
    warmups: int = 1,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """Measure a corpus and retain result IDs for ranking-change detection."""

    iteration_count = max(int(iterations), 1)
    warmup_count = max(int(warmups), 0)
    cases: list[dict[str, Any]] = []
    all_samples: list[float] = []
    anchor_failures: list[dict[str, Any]] = []
    fingerprints: list[str] = []

    for case in corpus.get("queries", []):
        case_id = str(case["id"])
        query = str(case["query"])
        limit = max(int(case.get("limit", 8)), 1)
        for _ in range(warmup_count):
            search(query, limit)
        samples: list[float] = []
        result_ids: list[str] = []
        for _ in range(iteration_count):
            started = clock()
            results = search(query, limit)
            samples.append((clock() - started) * 1000.0)
            result_ids = [_result_id(result) for result in results]
        expected_anchors = [str(value) for value in case.get("expected_anchors", [])]
        missing_anchors = [value for value in expected_anchors if value not in result_ids]
        if missing_anchors:
            anchor_failures.append(
                {"id": case_id, "missing_anchors": missing_anchors, "result_ids": result_ids}
            )
        all_samples.extend(samples)
        fingerprints.append(f"{case_id}:{','.join(result_ids)}")
        cases.append(
            {
                "id": case_id,
                "query": query,
                "limit": limit,
                "samples_ms": [round(value, 3) for value in samples],
                "median_ms": round(statistics.median(samples), 3),
                "p95_ms": round(percentile(samples, 0.95), 3),
                "result_ids": result_ids,
                "missing_anchors": missing_anchors,
            }
        )

    return {
        "corpus_version": corpus.get("version"),
        "iterations": iteration_count,
        "warmups": warmup_count,
        "query_count": len(cases),
        "median_ms": round(statistics.median(all_samples), 3) if all_samples else 0.0,
        "p95_ms": round(percentile(all_samples, 0.95), 3) if all_samples else 0.0,
        "maximum_query_median_ms": round(
            max((float(case["median_ms"]) for case in cases), default=0.0), 3
        ),
        "result_fingerprint": hashlib.sha256("\n".join(fingerprints).encode("utf-8")).hexdigest(),
        "anchor_failures": anchor_failures,
        "queries": cases,
    }


def percentile(values: Sequence[float], fraction: float) -> float:
    """Return a deterministic nearest-rank percentile."""

    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    rank = max(1, math.ceil(min(max(fraction, 0.0), 1.0) * len(ordered)))
    return ordered[rank - 1]


def _result_id(result: Any) -> str:
    obj = getattr(result, "object", None)
    if obj is not None and getattr(obj, "id", None):
        return str(obj.id)
    if getattr(result, "id", None):
        return str(result.id)
    if isinstance(result, Mapping):
        return str(result.get("id") or result.get("object_id") or "")
    return str(result)
