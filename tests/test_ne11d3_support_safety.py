from dataclasses import replace

import pytest

from bhf_agent.presentation import deterministic_presentation, rank_evidence
from bhf_agent.presentation.fallback import attach_relevant_support_evidence
from bhf_agent.presentation.ranking import RankedEvidence
from tests.test_ne11d1_jonah_handoff import _service


@pytest.fixture
def case(tmp_path):
    bundle = _service(tmp_path).build_evidence_bundle_for_passage(
        book="Jonah", chapter=1, verse_start=17, verse_end=17
    )
    ranked = rank_evidence(bundle, limit=8)
    packet = deterministic_presentation(bundle, ranked)
    primary = bundle.evidence_by_id["jonah-great-fish"]
    support = bundle.evidence_by_id["jonah-three-days"]
    return bundle, packet, primary, support


def attach(bundle, packet, support):
    return attach_relevant_support_evidence(bundle, packet, [RankedEvidence(support, 1.0, ())])


def test_shared_word_and_source_do_not_make_unrelated_claim_support(case):
    bundle, packet, _, support = case
    unrelated = replace(support, id="unrelated-fish-trade", claim="The fish trade was important in a later economy.",
                        relevance_metadata={**support.relevance_metadata, "semantic_relationship": "COMPARATIVE_CONTEXT"})
    assert attach(bundle, packet, unrelated) == packet


def test_same_source_does_not_link_unrelated_meaning(case):
    bundle, packet, _, support = case
    unrelated = replace(support, id="unrelated-commerce", claim="A later economy depended on trade.",
                        relevance_metadata={**support.relevance_metadata, "semantic_relationship": "COMPARATIVE_CONTEXT"})
    assert attach(bundle, packet, unrelated) == packet


def test_reviewed_jonah_support_still_attaches_once(case):
    bundle, packet, _, support = case
    result = attach(bundle, packet, support)
    assert result.cards[0].evidence_ids == ["jonah-great-fish", "jonah-three-days"]
    assert attach(bundle, result, support) == result


@pytest.mark.parametrize("change", [
    {"parent_object_id": "other"},
    {"semantic_relationship": "WEAKLY_RELATED"},
    {"applicability_scope": "book"},
])
def test_incompatible_metadata_cannot_attach(case, change):
    bundle, packet, _, support = case
    altered = replace(support, relevance_metadata={**support.relevance_metadata, **change})
    assert attach(bundle, packet, altered) == packet


def test_different_anchor_or_source_cannot_attach(case):
    bundle, packet, _, support = case
    assert attach(bundle, packet, replace(support, passage_anchors=["Jonah 2:1"])) == packet
    assert attach(bundle, packet, replace(support, source_ids=["unrelated"])) == packet


def test_unreviewed_candidate_does_not_displace_reviewed_support(case):
    bundle, packet, _, support = case
    unrelated = replace(support, id="unrelated-fish-trade", claim="The fish trade was important in a later economy.",
                        relevance_metadata={**support.relevance_metadata, "semantic_relationship": "COMPARATIVE_CONTEXT"})
    ranked = [RankedEvidence(unrelated, 2.0, ()), RankedEvidence(support, 1.0, ()), RankedEvidence(support, 0.5, ())]
    result = attach_relevant_support_evidence(bundle, packet, ranked)
    assert result.cards[0].evidence_ids == ["jonah-great-fish", "jonah-three-days"]
    assert attach_relevant_support_evidence(bundle, result, ranked) == result


def test_multiple_reviewed_support_records_attach_only_first(case, monkeypatch):
    from bhf_agent.presentation import fallback

    bundle, packet, _, support = case
    second = replace(support, id="second-fish-reception",
                     claim="The fish account's duration is later compared with Matthew 12:40.")
    monkeypatch.setattr(fallback, "_REVIEWED_SUPPORT_PAIRS", fallback._REVIEWED_SUPPORT_PAIRS | {
        ("jonah", "jonah-great-fish", second.id),
    })
    ranked = [RankedEvidence(support, 2.0, ()), RankedEvidence(second, 1.0, ())]
    result = attach_relevant_support_evidence(bundle, packet, ranked)
    assert result.cards[0].evidence_ids == ["jonah-great-fish", "jonah-three-days"]


def test_cached_and_uncached_packets_do_not_attach_unrelated_shared_word(case, tmp_path):
    from bhf_agent.presentation import PresentationEngine, SQLitePresentationCache, presentation_cache_key

    bundle, _, _, support = case
    unrelated = replace(support, id="unrelated-fish-trade", claim="The fish trade was important in a later economy.",
                        relevance_metadata={**support.relevance_metadata, "semantic_relationship": "COMPARATIVE_CONTEXT"})
    bundle = replace(bundle, evidence_items=[unrelated if item.id == support.id else item for item in bundle.evidence_items])
    ranked = rank_evidence(bundle, limit=8)
    assert unrelated.id in [entry.item.id for entry in ranked]
    baseline = deterministic_presentation(bundle, ranked)
    engine = PresentationEngine(cache=SQLitePresentationCache(tmp_path / "safety-cache.sqlite"))
    uncached = engine.present_local(bundle)
    assert unrelated.id not in uncached.packet.cards[0].evidence_ids
    cached = baseline.to_dict()
    cached["generated_from"]["prompt_version"] = engine.prompt_version
    engine.cache.put(presentation_cache_key(bundle, prompt_version=engine.prompt_version), cached)
    result = engine.present_local(bundle)
    assert result.mode == "cached"
    assert unrelated.id not in result.packet.cards[0].evidence_ids
