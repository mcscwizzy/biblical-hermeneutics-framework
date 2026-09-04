from types import SimpleNamespace

from bhf_agent.chapter_commentary.availability import EvidenceAvailability, classify_evidence_availability
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary


def bundle(count):
    items = [SimpleNamespace(id=f'e{i}', confidence='high', relevance_metadata={}) for i in range(count)]
    return SimpleNamespace(evidence_items=items, evidence_by_id={i.id: i for i in items}, evidence_hash='h', version='1.0')


def test_availability_thresholds():
    assert classify_evidence_availability(bundle(0)) is EvidenceAvailability.DATA_GAP
    assert classify_evidence_availability(bundle(2), threshold=3) is EvidenceAvailability.THIN
    assert classify_evidence_availability(bundle(3), threshold=3) is EvidenceAvailability.AVAILABLE


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
