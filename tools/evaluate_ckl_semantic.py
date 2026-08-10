#!/usr/bin/env python3
"""Compare optional semantic rankings with the deterministic CKL baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.canonical_library.database_schema import DEFAULT_CKL_DATABASE_PATH
from framework.canonical_library.evaluation import (
    compare_rankings,
    evaluate_rankings,
    load_candidate_rankings,
    load_relevance_corpus,
)
from framework.canonical_library.sqlite_repository import SQLiteCanonicalLibrary

DEFAULT_CORPUS = (
    REPO_ROOT / "framework" / "canonical_library" / "benchmarks" / "semantic_relevance.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate optional semantic results against deterministic CKL retrieval"
    )
    parser.add_argument("--database", default=DEFAULT_CKL_DATABASE_PATH)
    parser.add_argument("--root", default="framework/canonical_library")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument(
        "--candidate-results",
        help="Optional JSON id-to-result-IDs mapping produced by any semantic retriever",
    )
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    corpus = load_relevance_corpus(args.corpus)
    library = SQLiteCanonicalLibrary.from_path(args.database, root=args.root)
    try:
        baseline = {
            str(case["id"]): [
                result.object.id
                for result in library.retrieve_hybrid(
                    str(case["query"]),
                    limit=int(case.get("limit", 8)),
                    apply_thresholds=False,
                )
            ]
            for case in corpus["queries"]
        }
    finally:
        library.close()

    if args.candidate_results:
        report = compare_rankings(corpus, baseline, load_candidate_rankings(args.candidate_results))
    else:
        report = {"baseline": evaluate_rankings(corpus, baseline, system="deterministic-baseline")}
    rendered = json.dumps(report, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
