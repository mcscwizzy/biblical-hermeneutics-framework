from bhf_web.services.commentary_coverage import build_commentary_coverage_snapshot


def test_coverage_snapshot_is_read_only_and_preserves_report_sections():
    health = {
        "corpus_counts": {"generated": 2, "total_chapters": 1189, "validated": 2},
        "evidence_availability_distribution": {"AVAILABLE": 1, "DATA_GAP": 1},
        "structure": {"sections": {"average": 1.0}},
        "content_size": {"average": 100},
        "citation_statistics": {"valid_percentage": 100},
    }
    coverage = {
        "scope": "Leviticus 1-5",
        "coverage_totals": {"chapters_analyzed": 5, "data_gaps": 3},
        "book_summaries": {"Leviticus": {"chapters": 5}},
        "chapter_results": [{"book": "Leviticus", "chapter": 2, "status": "DATA_GAP"}],
        "evidence_density": {"average": 0.4},
        "category_distribution": {"religion": 2},
        "expansion_candidates": [{"reference": "Leviticus 2"}],
    }
    result = build_commentary_coverage_snapshot(
        "/tmp/unused-commentary-path",
        scope="Leviticus 1-5",
        health_report=lambda _path: health,
        ckl_report=lambda _scope: coverage,
    )

    assert result["release"] == "commentary-v1.1"
    assert result["scope"] == "Leviticus 1-5"
    assert result["commentary"]["corpus_counts"]["generated"] == 2
    assert result["ckl"]["coverage_totals"]["data_gaps"] == 3
    assert result["ckl"]["expansion_candidates"] == [{"reference": "Leviticus 2"}]
