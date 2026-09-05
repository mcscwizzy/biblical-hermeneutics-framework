"""Read-only coverage snapshot for the local Commentary improvement workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .bhf_commentary import COMMENTARY_RELEASE


def _health_report(storage_dir: str | Path) -> dict[str, Any]:
    from tools.commentary_health_report import report

    return report(storage_dir)


def _ckl_report(scope: str | None) -> dict[str, Any]:
    from tools.ckl_coverage_report import scan

    return scan(scope)


def build_commentary_coverage_snapshot(
    storage_dir: str | Path,
    *,
    scope: str | None = None,
    health_report: Callable[[str | Path], dict[str, Any]] = _health_report,
    ckl_report: Callable[[str | None], dict[str, Any]] = _ckl_report,
) -> dict[str, Any]:
    """Combine current on-disk commentary health with strict CKL coverage."""
    health = health_report(storage_dir)
    coverage = ckl_report(scope)
    return {
        "release": COMMENTARY_RELEASE,
        "scope": coverage.get("scope", scope or "entire Bible"),
        "commentary": {
            "corpus_counts": health.get("corpus_counts", {}),
            "evidence_availability_distribution": health.get("evidence_availability_distribution", {}),
            "structure": health.get("structure", {}),
            "content_size": health.get("content_size", {}),
            "citation_statistics": health.get("citation_statistics", {}),
        },
        "ckl": {
            "coverage_totals": coverage.get("coverage_totals", {}),
            "book_summaries": coverage.get("book_summaries", {}),
            "chapter_results": coverage.get("chapter_results", []),
            "evidence_density": coverage.get("evidence_density", {}),
            "category_distribution": coverage.get("category_distribution", {}),
            "expansion_candidates": coverage.get("expansion_candidates", []),
        },
    }
