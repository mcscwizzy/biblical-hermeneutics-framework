import json

from tools.commentary_health_report import report


def write_fixture(tmp_path, *, verse='Genesis 1:1', evidence='e1'):
    (tmp_path / 'genesis_001.json').write_text(json.dumps({
        'book': 'Genesis', 'chapter': 1, 'reference': 'Genesis 1:1-31', 'status': 'validated', 'evidence_availability': 'AVAILABLE',
        'generated_metadata': {'commentary_prompt_version': '1.1', 'commentary_schema_version': '1.0', 'evidence_hash': 'x', 'evidence_bundle_version': '1.0', 'model': 'fixture', 'generated_timestamp': '2026-01-01T00:00:00Z'},
        'sections': [{'kind': 'chapter_overview', 'title': 'Overview', 'blocks': [{'id': 'b1', 'text': 'Text', 'verse_refs': [verse], 'evidence_ids': [evidence], 'confidence': 'high', 'interpretation_level': 'fact'}]}]
    }))


def test_report_counts_disk_and_structure(tmp_path):
    write_fixture(tmp_path)
    data = report(tmp_path)
    assert data['corpus_counts']['validated'] == 1
    assert data['corpus_counts']['pending'] == 1188
    assert data['structure']['section_kind_distribution'] == {'chapter_overview': 1}
    assert data['evidence_statistics']['items_per_chapter']['average'] == 1
    assert data['evidence_availability_distribution'] == {'AVAILABLE': 1}


def test_report_detects_invalid_verse(tmp_path):
    write_fixture(tmp_path, verse='Romans 1:1')
    data = report(tmp_path)
    assert data['verse_statistics']['invalid'] == 1
    assert data['verse_statistics']['out_of_chapter'] == 1


def test_empty_corpus_is_valid_json_shape(tmp_path):
    data = report(tmp_path)
    assert data['corpus_counts']['generated'] == 0
    assert data['citation_statistics']['valid_percentage'] == 100
    json.dumps(data)
