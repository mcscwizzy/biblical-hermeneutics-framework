"""Dependency-free ranking evaluation for optional CKL retrievers."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


def load_relevance_corpus(path: str | Path) -> dict[str, Any]:
    corpus = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(corpus, dict) or not isinstance(corpus.get("queries"), list):
        raise ValueError("relevance corpus must contain a queries list")
    for position, case in enumerate(corpus["queries"]):
        if not isinstance(case, dict):
            raise ValueError(f"relevance query {position} must be an object")
        if not str(case.get("id") or "").strip() or not str(case.get("query") or "").strip():
            raise ValueError(f"relevance query {position} requires id and query")
        if not case.get("relevant_ids"):
            raise ValueError(f"relevance query {case.get('id')} requires relevant_ids")
    return corpus


def load_candidate_rankings(path: str | Path) -> dict[str, list[str]]:
    """Load model-produced rankings without importing a model SDK."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        payload = payload["results"]
    if isinstance(payload, dict):
        return {
            str(case_id): [str(value) for value in values]
            for case_id, values in payload.items()
            if isinstance(values, list)
        }
    if isinstance(payload, list):
        return {
            str(item["id"]): [str(value) for value in item.get("result_ids", [])]
            for item in payload
            if isinstance(item, dict) and item.get("id")
        }
    raise ValueError("candidate rankings must be an id-to-results mapping or results list")


def evaluate_rankings(
    corpus: Mapping[str, Any],
    rankings: Mapping[str, Sequence[str]],
    *,
    system: str,
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for case in corpus.get("queries", []):
        case_id = str(case["id"])
        limit = max(int(case.get("limit", 8)), 1)
        relevant = {str(value) for value in case["relevant_ids"]}
        ranked = [str(value) for value in rankings.get(case_id, ())][:limit]
        hits = [value for value in ranked if value in relevant]
        reciprocal_rank = 0.0
        for index, value in enumerate(ranked, start=1):
            if value in relevant:
                reciprocal_rank = 1.0 / index
                break
        dcg = sum(1.0 / math.log2(index + 1) for index, value in enumerate(ranked, start=1) if value in relevant)
        ideal_hits = min(len(relevant), limit)
        ideal_dcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
        cases.append(
            {
                "id": case_id,
                "result_ids": ranked,
                "missing_relevant_ids": sorted(relevant - set(ranked)),
                "recall_at_k": round(len(set(hits)) / len(relevant), 4),
                "reciprocal_rank": round(reciprocal_rank, 4),
                "ndcg_at_k": round(dcg / ideal_dcg, 4) if ideal_dcg else 0.0,
            }
        )
    count = max(len(cases), 1)
    return {
        "system": system,
        "query_count": len(cases),
        "mean_recall_at_k": round(sum(case["recall_at_k"] for case in cases) / count, 4),
        "mean_reciprocal_rank": round(
            sum(case["reciprocal_rank"] for case in cases) / count, 4
        ),
        "mean_ndcg_at_k": round(sum(case["ndcg_at_k"] for case in cases) / count, 4),
        "queries": cases,
    }


def compare_rankings(
    corpus: Mapping[str, Any],
    baseline: Mapping[str, Sequence[str]],
    candidate: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """Evaluate a candidate only in relation to the deterministic baseline."""

    baseline_report = evaluate_rankings(corpus, baseline, system="deterministic-baseline")
    candidate_report = evaluate_rankings(corpus, candidate, system="optional-candidate")
    return {
        "baseline": baseline_report,
        "candidate": candidate_report,
        "delta": {
            metric: round(candidate_report[metric] - baseline_report[metric], 4)
            for metric in ("mean_recall_at_k", "mean_reciprocal_rank", "mean_ndcg_at_k")
        },
    }
