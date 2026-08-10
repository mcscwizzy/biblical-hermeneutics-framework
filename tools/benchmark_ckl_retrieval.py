#!/usr/bin/env python3
"""Benchmark the fixed CKL hybrid-retrieval corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.canonical_library.benchmarking import load_retrieval_corpus, run_retrieval_benchmark
from framework.canonical_library.database_schema import DEFAULT_CKL_DATABASE_PATH
from framework.canonical_library.sqlite_repository import SQLiteCanonicalLibrary

DEFAULT_CORPUS = (
    REPO_ROOT / "framework" / "canonical_library" / "benchmarks" / "retrieval_latency.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark repeatable CKL hybrid queries")
    parser.add_argument("--database", default=DEFAULT_CKL_DATABASE_PATH)
    parser.add_argument("--root", default="framework/canonical_library")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--output", help="Write the full JSON report to this path")
    parser.add_argument("--max-median-ms", type=float)
    parser.add_argument("--max-p95-ms", type=float)
    args = parser.parse_args(argv)

    corpus = load_retrieval_corpus(args.corpus)
    library = SQLiteCanonicalLibrary.from_path(args.database, root=args.root)
    try:
        report = run_retrieval_benchmark(
            lambda query, limit: library.retrieve_hybrid(
                query, limit=limit, apply_thresholds=False
            ),
            corpus,
            iterations=args.iterations,
            warmups=args.warmups,
        )
    finally:
        library.close()

    rendered = json.dumps(report, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    if args.as_json:
        print(rendered)
    else:
        print(
            f"CKL hybrid corpus: {report['query_count']} queries, "
            f"median {report['median_ms']:.2f} ms, p95 {report['p95_ms']:.2f} ms"
        )
        for case in report["queries"]:
            print(
                f"{case['id']:24} median={case['median_ms']:8.2f} ms "
                f"p95={case['p95_ms']:8.2f} ms  {','.join(case['result_ids'])}"
            )
        print(f"Result fingerprint: {report['result_fingerprint']}")

    failed = bool(report["anchor_failures"])
    if args.max_median_ms is not None and report["median_ms"] > args.max_median_ms:
        failed = True
    if args.max_p95_ms is not None and report["p95_ms"] > args.max_p95_ms:
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
