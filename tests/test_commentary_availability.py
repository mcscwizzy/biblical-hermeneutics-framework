from types import SimpleNamespace

from bhf_agent.chapter_commentary.availability import EvidenceAvailability, classify_evidence_availability
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary


def bundle(count):
    items = [SimpleNamespace(id=f'e{i}', confidence='high', relevance_metadata={}) for i in range(count)]
    return SimpleNamespace(evidence_items=items, evidence_by_id={i.id: i for i in items}, evidence_hash='h', version='1.0')


def scored_bundle(*items):
    return SimpleNamespace(
        passage_ref='1 Samuel 28',
        evidence_items=list(items),
        evidence_by_id={item.id: item for item in items},
        evidence_hash='h',
        version='1.0',
    )


def evidence_item(
    item_id,
    anchor,
    *,
    confidence='high',
    category='history',
    dispute_status='not_disputed',
):
    return SimpleNamespace(
        id=item_id,
        passage_anchors=[anchor],
        confidence=confidence,
        category=category,
        relevance_metadata={'dispute_status': dispute_status, 'passage_relationship': 'direct'},
    )


def test_availability_thresholds():
    assert classify_evidence_availability(bundle(0)) is EvidenceAvailability.DATA_GAP
    assert classify_evidence_availability(bundle(2), threshold=3) is EvidenceAvailability.THIN
    assert classify_evidence_availability(bundle(3), threshold=3) is EvidenceAvailability.AVAILABLE


def test_whole_book_evidence_alone_is_thin():
    value = scored_bundle(evidence_item('book', '1 Samuel 1-31'))

    assert classify_evidence_availability(value) is EvidenceAvailability.THIN


def test_low_confidence_disputed_chapter_evidence_is_conservative():
    value = scored_bundle(
        evidence_item(
            'note',
            '1 Samuel 28:3-25',
            confidence='low',
            category='culture',
            dispute_status='denominational_disagreement',
        ),
        evidence_item('book', '1 Samuel 1-31'),
    )

    assert classify_evidence_availability(value) is EvidenceAvailability.THIN


def test_two_strong_chapter_specific_items_are_available():
    value = scored_bundle(
        evidence_item('history', '1 Samuel 28'),
        evidence_item('geography', '1 Samuel 28:1-25', category='geography'),
    )

    assert classify_evidence_availability(value) is EvidenceAvailability.AVAILABLE


def test_broad_evidence_contributes_thin_coverage():
    value = scored_bundle(
        evidence_item('movement', '1 Samuel 1-31', category='politics'),
        evidence_item('background', '1 Samuel 24-30', category='history'),
    )

    assert classify_evidence_availability(value) is EvidenceAvailability.THIN


def test_no_scored_evidence_remains_data_gap():
    value = scored_bundle(
        evidence_item('unknown', 'not a scripture reference', category='unknown'),
    )

    assert classify_evidence_availability(value) is EvidenceAvailability.DATA_GAP


def metadata():
    return {'evidence_hash':'h','evidence_bundle_version':'1.0','commentary_schema_version':'1.0','commentary_prompt_version':'1.1','model':'fixture'}


def test_data_gap_allows_only_uncited_canonical_overview():
    raw = {'reference':'Genesis 1','book':'Genesis','chapter':1,'status':'pending','evidence_availability':'DATA_GAP','generated_metadata':metadata(),'sections':[{'kind':'chapter_overview','title':'Overview','blocks':[{'id':'b','text':'The chapter opens with creation.','verse_refs':['Genesis 1:1'],'evidence_ids':[],'confidence':'high','interpretation_level':'fact'}]}]}
    result = validate_chapter_commentary(raw, bundle(0), expected_reference='Genesis 1', expected_book='Genesis', expected_chapter=1)
    assert result.valid


def test_model_cannot_override_availability():
    raw = {'reference':'Genesis 1','book':'Genesis','chapter':1,'status':'pending','evidence_availability':'AVAILABLE','generated_metadata':metadata(),'sections':[]}
    result = validate_chapter_commentary(raw, bundle(0), expected_reference='Genesis 1', expected_book='Genesis', expected_chapter=1)
    assert not result.valid
