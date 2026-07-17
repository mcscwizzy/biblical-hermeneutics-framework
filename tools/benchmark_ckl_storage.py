#!/usr/bin/env python3
"""Benchmark JSON and SQLite CKL runtime storage locally."""

from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.canonical_library import CanonicalLibrary
from framework.canonical_library.database_builder import build_database
from framework.canonical_library.sqlite_repository import SQLiteCanonicalLibrary


MetricFn = Callable[[CanonicalLibrary], object]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare JSON and SQLite CKL storage performance")
    parser.add_argument("--root", default="framework/canonical_library", help="CKL JSON root")
    parser.add_argument("--database", help="Existing SQLite database path")
    parser.add_argument("--iterations", type=int, default=100, help="Repeated lookup iterations")
    args = parser.parse_args()

    root = Path(args.root)
    if args.database:
        database = Path(args.database)
    else:
        tmp = tempfile.TemporaryDirectory()
        database = Path(tmp.name) / "ckl.sqlite"
        build_database(root, database)

    measurements: list[tuple[str, str, str]] = []
    json_library, json_init_ms, json_peak_kb = _measure_init(lambda: CanonicalLibrary(root=root).load())
    sqlite_library, sqlite_init_ms, sqlite_peak_kb = _measure_init(
        lambda: SQLiteCanonicalLibrary.from_path(database, root=root)
    )

    measurements.append(("Cold initialization (ms)", _fmt(json_init_ms), _fmt(sqlite_init_ms)))
    measurements.append(("Peak init memory (KiB)", _fmt(json_peak_kb), _fmt(sqlite_peak_kb)))

    benchmarks: list[tuple[str, MetricFn]] = [
        ("Exact ID lookup (ms)", lambda library: library.retrieve_by_id("john")),
        ("Exact alias lookup (ms)", lambda library: library.retrieve_exact("John")),
        ("Title lookup (ms)", lambda library: library.resolve_entity(("John",), ("book",))),
        ("Keyword retrieval (ms)", lambda library: library.retrieve_by_keywords("covenant abraham", limit=5)),
        ("Scripture lookup (ms)", lambda library: library.retrieve_by_scripture_reference("Joshua 24", limit=5)),
        ("Relationship lookup (ms)", lambda library: library.trace_relationship_graph("Shechem", max_depth=1, limit=4)),
    ]
    for label, fn in benchmarks:
        measurements.append((label, _fmt(_time_call(fn, json_library)), _fmt(_time_call(fn, sqlite_library))))

    repeat_count = max(args.iterations, 1)
    measurements.append(
        (
            f"{repeat_count} repeated exact lookups (ms)",
            _fmt(_time_repeated(lambda: json_library.retrieve_exact("John"), repeat_count)),
            _fmt(_time_repeated(lambda: sqlite_library.retrieve_exact("John"), repeat_count)),
        )
    )
    thousand = 1000
    measurements.append(
        (
            "1000 repeated exact lookups (ms)",
            _fmt(_time_repeated(lambda: json_library.retrieve_exact("John"), thousand)),
            _fmt(_time_repeated(lambda: sqlite_library.retrieve_exact("John"), thousand)),
        )
    )

    print(f"CKL root: {root}")
    print(f"SQLite database: {database}")
    print()
    print(f"{'Metric':35} {'JSON':>14} {'SQLite':>14}")
    print("-" * 65)
    for metric, json_value, sqlite_value in measurements:
        print(f"{metric:35} {json_value:>14} {sqlite_value:>14}")
    return 0


def _measure_init(factory: Callable[[], CanonicalLibrary]) -> tuple[CanonicalLibrary, float, float]:
    tracemalloc.start()
    start = time.perf_counter()
    library = factory()
    elapsed_ms = (time.perf_counter() - start) * 1000
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return library, elapsed_ms, peak / 1024


def _time_call(fn: MetricFn, library: CanonicalLibrary) -> float:
    samples: list[float] = []
    for _ in range(5):
        start = time.perf_counter()
        fn(library)
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)


def _time_repeated(fn: Callable[[], object], count: int) -> float:
    start = time.perf_counter()
    for _ in range(count):
        fn()
    return (time.perf_counter() - start) * 1000


def _fmt(value: float) -> str:
    return f"{value:.2f}"


if __name__ == "__main__":
    raise SystemExit(main())
