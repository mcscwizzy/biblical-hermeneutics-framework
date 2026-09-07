from __future__ import annotations

import json
from pathlib import Path

from tools.commentary_v11_expansion import GENRE_GUIDANCE, build_priority_report


def _coverage_fixture():
    rows = []
    for book, chapter, status, count, raw in [
        ("Numbers", 3, "DATA_GAP", 0, 2),
        ("Numbers", 4, "DATA_GAP", 0, 1),
        ("Numbers", 16, "THIN", 1, 1),
        ("Psalms", 1, "AVAILABLE", 4, 4),
    ]:
        rows.append({
            "book": book,
            "chapter": chapter,
            "reference": f"{book} {chapter}",
            "status": status,
            "valid_anchored_evidence": count,
            "raw_ckl_candidates": raw,
            "rejected_candidates": raw - count,
        })
    return {"coverage_totals": {"chapters_analyzed": 4, "evidence_available": 1, "thin": 1, "data_gaps": 2}, "chapter_results": rows}


class _Object:
    def __init__(self, object_id, object_type):
        self.id = object_id
        self.type = object_type
        self.title = object_id

    def to_dict(self):
        return {"id": self.id, "type": self.type, "title": self.title, "sources": []}


class _Result:
    def __init__(self, obj):
        self.object = obj


class _Library:
    _book_alias_lookup = {}

    def retrieve_by_scripture_reference(self, reference, limit=100, include_placeholders=False):
        if reference == "Numbers 4":
            return [_Result(_Object("numbers", "book"))]
        return []


def test_priority_report_excludes_object_only_structural_cases(monkeypatch):
    monkeypatch.setattr("tools.commentary_v11_expansion.load_canonical_library", lambda config: _Library())
    report = build_priority_report(_coverage_fixture())

    assert report["data_gap_scope"]["strict_data_gaps"] == 2
    assert report["data_gap_scope"]["object_only_structural_cases"] == 1
    assert report["data_gap_scope"]["likely_true_ckl_data_gaps"] == 1
    assert report["selected_batches"]["data_gap_initial"][0]["reference"] == "Numbers 3"


def test_genre_guidance_has_non_narrative_controls():
    assert "parallelism" in GENRE_GUIDANCE["poetry"]["evidence"]
    assert "metaphor" in GENRE_GUIDANCE["wisdom"]["evidence"]
    assert "symbolic actions" in GENRE_GUIDANCE["prophecy"]["evidence"]

