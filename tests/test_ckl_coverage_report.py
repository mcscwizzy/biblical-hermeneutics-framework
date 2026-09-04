import json
from types import SimpleNamespace

import tools.ckl_coverage_report as report


def test_scope_filters_book_and_range(monkeypatch):
    monkeypatch.setattr(report.bible, 'list_books', lambda: [{'name': 'Genesis', 'chapters': 3}, {'name': 'Leviticus', 'chapters': 2}])
    assert report.chapters_for('Genesis 2-3') == [('Genesis', 2), ('Genesis', 3)]


def test_strict_counts_ignore_unanchored_and_cross_book(monkeypatch):
    monkeypatch.setattr(report.bible, 'list_books', lambda: [{'name': 'Genesis', 'chapters': 1}])
    monkeypatch.setattr(report.bible, 'verse_range_reference', lambda b, c: 'Genesis 1:1-31')
    item = SimpleNamespace(category='history', id='anchored')
    fake = SimpleNamespace(_book_alias_lookup={}, _scripture_book_index={'Genesis': {'a', 'b', 'c'}}, retrieve_by_scripture_reference=lambda ref, limit: ['a'])
    monkeypatch.setattr(report, 'load_canonical_library', lambda config: fake)
    monkeypatch.setattr(report, 'parse_scripture_query', lambda ref, book_alias_lookup: SimpleNamespace(book='Genesis'))
    monkeypatch.setattr(report, 'build_evidence_bundle', lambda ref, canonical_results: SimpleNamespace(evidence_items=[item]))
    data = report.scan('Genesis')
    assert data['coverage_totals']['evidence_available'] == 0
    assert data['coverage_totals']['thin'] == 1
    assert data['chapter_results'][0]['valid_anchored_evidence'] == 1


def test_empty_scope_result_serializes(monkeypatch):
    monkeypatch.setattr(report.bible, 'list_books', lambda: [])
    data = report.scan()
    assert data['coverage_totals']['chapters_analyzed'] == 0
    json.dumps(data)
