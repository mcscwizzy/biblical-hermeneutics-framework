from __future__ import annotations

import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from bhf_agent.models import ChatResponse
from bhf_agent.presentation import (
    AdapterPresentationProvider,
    GeneratedFrom,
    MemoryPresentationCache,
    PRESENTATION_BUNDLE_FORMAT,
    PRESENTATION_BUNDLE_VERSION,
    PresentationBundleError,
    PresentationEngine,
    PresentationProvider,
    PresentationResult,
    SQLitePresentationCache,
    build_evidence_bundle,
    default_presentation_cache_path,
    deterministic_presentation,
    load_presentation_bundle,
    presentation_cache_key,
    rank_evidence,
    validate_presentation_packet,
)
from bhf_agent.presentation.providers import PRESENTATION_PROMPT_VERSION


FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "presentation_passages.json").read_text(encoding="utf-8")
)


def _results(objects):
    return [SimpleNamespace(object=value, score=0.92) for value in objects]


def test_presentation_result_diagnostics_require_explicit_serialization_opt_in():
    bundle = build_evidence_bundle("Mark 5:1-20")
    result = PresentationResult(
        packet=deterministic_presentation(bundle),
        mode="deterministic_fallback",
        diagnostics=("provider failure: secret-token-123",),
    )

    assert "diagnostics" not in result.to_dict()
    assert result.to_dict(include_diagnostics=True)["diagnostics"] == [
        "provider failure: secret-token-123"
    ]


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda value: value["reference"])
def test_evidence_bundle_vertical_slice_handles_distinct_passages(fixture):
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
        geography=fixture.get("geography", {}),
    )

    assert bundle.version == "1.0"
    assert len(bundle.evidence_hash) == 64
    assert bundle.evidence_items
    assert set(fixture["expected_categories"]).intersection(
        item.category for item in bundle.evidence_items
    )
    assert all(item.source_ids for item in bundle.evidence_items)
    assert all(item.passage_anchors for item in bundle.evidence_items)
    ranked = rank_evidence(bundle)
    assert 1 <= len(ranked) <= 8
    packet = PresentationEngine().present(bundle)
    assert packet.mode == "deterministic_fallback"
    assert 1 <= len(packet.packet.cards) <= 3


def test_evidence_ids_and_hash_are_stable():
    fixture = FIXTURES[0]
    first = build_evidence_bundle(fixture["reference"], canonical_results=_results(fixture["objects"]))
    second = build_evidence_bundle(fixture["reference"], canonical_results=_results(fixture["objects"]))

    assert [item.id for item in first.evidence_items] == [item.id for item in second.evidence_items]
    assert first.evidence_hash == second.evidence_hash


def test_unrelated_retrieval_does_not_change_evidence_hash():
    fixture = FIXTURES[0]
    unrelated = {
        "id": "cornelius",
        "type": "person",
        "title": "Cornelius",
        "scripture_references": [{"reference": "Acts 10:1-48"}],
        "historical_context": "A centurion in Caesarea.",
        "sources": [{"id": "unrelated-source", "title": "Unrelated source"}],
    }
    baseline = build_evidence_bundle(
        fixture["reference"], canonical_results=_results(fixture["objects"])
    )
    with_unrelated = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results([*fixture["objects"], unrelated]),
    )

    assert with_unrelated.evidence_hash == baseline.evidence_hash
    assert "cornelius" not in {
        item["id"] for item in with_unrelated.provenance["canonical_objects"]
    }


def test_relevant_claim_and_source_changes_invalidate_evidence_hash():
    fixture = FIXTURES[0]
    changed_claim = copy.deepcopy(fixture["objects"])
    changed_claim[1]["evidence_items"][0]["description"] += " Changed."
    changed_source = copy.deepcopy(fixture["objects"])
    changed_source[1]["sources"][1]["title"] += " Revised"

    baseline = build_evidence_bundle(
        fixture["reference"], canonical_results=_results(fixture["objects"])
    )
    claim_bundle = build_evidence_bundle(
        fixture["reference"], canonical_results=_results(changed_claim)
    )
    source_bundle = build_evidence_bundle(
        fixture["reference"], canonical_results=_results(changed_source)
    )

    assert claim_bundle.evidence_hash != baseline.evidence_hash
    assert source_bundle.evidence_hash != baseline.evidence_hash


def test_entity_presentation_metadata_does_not_change_evidence_hash():
    fixture = FIXTURES[0]
    changed = copy.deepcopy(fixture["objects"])
    changed[0]["terrain"] = "New presentation-only terrain description"
    changed[0]["modern_identification"] = "New presentation-only label"

    baseline = build_evidence_bundle(
        fixture["reference"], canonical_results=_results(fixture["objects"])
    )
    rebuilt = build_evidence_bundle(
        fixture["reference"], canonical_results=_results(changed)
    )

    assert rebuilt.evidence_hash == baseline.evidence_hash


def test_map_presentation_metadata_does_not_change_evidence_hash():
    base_place = {
        "id": "jerusalem",
        "title": "Jerusalem",
        "summary": "Jerusalem is the passage setting.",
        "source_name": "Curated map source",
        "coordinates": [31.7, 35.2],
        "marker_color": "blue",
    }
    changed_place = {
        **base_place,
        "coordinates": [31.8, 35.3],
        "marker_color": "gold",
    }

    baseline = build_evidence_bundle(
        "Acts 2:1", geography={"places": [base_place], "routes": []}
    )
    rebuilt = build_evidence_bundle(
        "Acts 2:1", geography={"places": [changed_place], "routes": []}
    )

    assert rebuilt.evidence_hash == baseline.evidence_hash


def test_passage_map_place_becomes_grounded_walk_the_land_card():
    bundle = build_evidence_bundle(
        "1 Samuel 25:2-7",
        geography={
            "places": [{
                "id": "carmel-judah",
                "title": "Carmel in Judah",
                "summary": "Carmel was a settlement in the hill country, near the setting of Nabal's flocks.",
                "modern_location": "Khirbet el-Karmil",
                "confidence": "strong",
                "relationship": "directly_named",
                "source_name": "Curated Bible map",
                "source_url": "https://example.test/carmel",
            }],
            "routes": [],
        },
    )

    evidence = bundle.evidence_by_id["map-place:carmel-judah"]
    packet = deterministic_presentation(bundle)
    card = packet.cards[0]

    assert evidence.category == "geography"
    assert evidence.confidence == "high"
    assert evidence.source_ids == ["passage-map:carmel-judah"]
    assert card.type == "walk_the_land"
    assert len(packet.cards) == 1
    assert card.evidence_ids == [evidence.id]
    assert card.map_focus == {"kind": "place", "target_id": "carmel-judah"}
    assert card.dig_deeper_actions[0].type == "open_map"
    assert validate_presentation_packet(packet.to_dict(), bundle).valid


def test_passage_map_route_becomes_traceable_walk_the_land_card():
    bundle = build_evidence_bundle(
        "Acts 13:4-5",
        geography={
            "places": [],
            "routes": [{
                "id": "paul-first-route",
                "title": "Paul's first journey",
                "summary": "The route leaves Antioch for Seleucia and crosses to Cyprus.",
                "confidence": "likely",
                "relationship": "direct",
                "source_name": "Curated Bible map",
            }],
        },
    )

    packet = deterministic_presentation(bundle)
    card = packet.cards[0]

    assert bundle.geography["map_route_refs"] == ["paul-first-route"]
    assert card.type == "walk_the_land"
    assert len(packet.cards) == 1
    assert card.map_focus == {"kind": "route", "target_id": "paul-first-route"}
    assert card.dig_deeper_actions[0].type == "show_route"
    assert validate_presentation_packet(packet.to_dict(), bundle).valid


def test_walk_the_land_requires_a_matching_fulfillable_map_action():
    bundle = build_evidence_bundle(
        "Mark 5:1",
        geography={
            "places": [{
                "id": "gerasa",
                "title": "Gerasa",
                "summary": "Gerasa lies east of the Sea of Galilee.",
                "confidence": "likely",
            }],
            "routes": [],
        },
    )
    packet = deterministic_presentation(bundle).to_dict()
    packet["cards"][0]["dig_deeper_actions"] = [
        action
        for action in packet["cards"][0]["dig_deeper_actions"]
        if action["type"] == "show_evidence"
    ]

    result = validate_presentation_packet(packet, bundle)

    assert not result.valid
    assert any("matching map action" in error for error in result.errors)


def test_no_evidence_returns_valid_zero_card_packet():
    bundle = build_evidence_bundle("1 Corinthians 8")

    result = PresentationEngine().present(bundle)

    assert result.packet.cards == []
    assert validate_presentation_packet(result.packet.to_dict(), bundle).valid


def test_explicit_ckl_passage_relevance_becomes_why_it_matters_card():
    evidence_item = {
        "id": "corinth-meal-visibility",
        "evidence_type": "cultural-practice",
        "description": "Meals in a sanctuary dining room were visible social acts, not merely private food choices.",
        "passage_relevance": "This makes the passage's concern with another person's seeing and conscience part of the social setting.",
        "assertion_type": "secondary-evidence",
        "confidence": "medium",
        "certainty": "probable",
        "dispute_status": "not_disputed",
        "source_ids": ["corinth-meals"],
        "scripture_references": [{"reference": "1 Corinthians 8:7-10", "relationship": "direct"}],
    }
    bundle = build_evidence_bundle(
        "1 Corinthians 8:7-10",
        canonical_results=_results([{
            "id": "corinth-meals",
            "type": "cultural_background",
            "title": "Meals and visibility in Corinth",
            "confidence": "medium",
            "scripture_references": [{"reference": "1 Corinthians 8:7-10"}],
            "sources": [{"id": "corinth-meals", "title": "Corinthian meal study"}],
            "evidence_items": [evidence_item],
            "claims": [],
        }]),
    )

    significance = bundle.evidence_by_id["corinth-meal-visibility:passage-relevance"]
    packet = deterministic_presentation(bundle)
    card = next(card for card in packet.cards if card.type == "why_it_matters")

    assert significance.relevance_metadata["presentation_role"] == "significance"
    assert significance.relevance_metadata["supports_evidence_ids"] == ["corinth-meal-visibility"]
    assert card.type == "why_it_matters"
    assert card.evidence_ids == ["corinth-meal-visibility", significance.id]
    assert card.interpretation_level == "inference"
    assert [card.type for card in packet.cards] == ["did_you_know", "why_it_matters"]
    assert validate_presentation_packet(packet.to_dict(), bundle).valid

    as_fact = packet.to_dict()
    next(
        card for card in as_fact["cards"] if card["type"] == "why_it_matters"
    )["interpretation_level"] = "fact"
    invalid = validate_presentation_packet(as_fact, bundle)
    assert not invalid.valid
    assert any("inference or disputed" in error for error in invalid.errors)


def test_did_you_know_keeps_a_slot_when_map_and_significance_evidence_exist():
    objects = copy.deepcopy(FIXTURES[0]["objects"])
    objects[1]["evidence_items"][0]["passage_relevance"] = (
        "The provisioning custom explains why the request carries social weight here."
    )
    bundle = build_evidence_bundle(
        "1 Samuel 25",
        canonical_results=_results(objects),
        geography={
            "places": [{
                "id": "carmel-judah",
                "title": "Carmel in Judah",
                "summary": "Carmel was near the setting of Nabal's flocks.",
                "confidence": "strong",
            }],
            "routes": [],
        },
    )

    packet = deterministic_presentation(bundle, maximum_cards=3)

    assert [card.type for card in packet.cards] == [
        "did_you_know",
        "walk_the_land",
        "why_it_matters",
    ]
    assert validate_presentation_packet(packet.to_dict(), bundle).valid


def test_map_only_evidence_does_not_manufacture_did_you_know():
    bundle = build_evidence_bundle(
        "Mark 5:1",
        geography={
            "places": [{
                "id": "gerasa",
                "title": "Gerasa",
                "summary": "Gerasa lies east of the Sea of Galilee.",
            }],
            "routes": [],
        },
    )

    packet = deterministic_presentation(bundle, maximum_cards=3)

    assert [card.type for card in packet.cards] == ["walk_the_land"]


def test_archaeology_passage_significance_uses_existing_archaeology_explorer():
    bundle = build_evidence_bundle(
        "John 9:7-11",
        archaeology=[{
            "id": "pool-of-siloam",
            "title": "Pool of Siloam",
            "summary": "The pool gives concrete urban context for John's reference to Siloam.",
            "caution": "The remains do not determine the passage's interpretation.",
            "confidence": "strong",
        }],
    )

    packet = deterministic_presentation(bundle)
    card = packet.cards[0]

    assert card.type == "why_it_matters"
    assert card.confidence == "high"
    assert card.interpretation_level == "inference"
    assert any(action.type == "archaeology" for action in card.dig_deeper_actions)
    assert validate_presentation_packet(packet.to_dict(), bundle).valid


def test_why_it_matters_rejects_evidence_without_explicit_significance_role():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
    )
    packet = deterministic_presentation(bundle).to_dict()
    packet["cards"][0]["type"] = "why_it_matters"
    packet["cards"][0]["interpretation_level"] = "inference"

    result = validate_presentation_packet(packet, bundle)

    assert not result.valid
    assert any("explicit significance evidence" in error for error in result.errors)


def test_unrelated_entities_and_evidence_are_suppressed_before_ranking():
    target = FIXTURES[0]
    unrelated = {
        "id": "cornelius",
        "type": "person",
        "title": "Cornelius",
        "importance": 99,
        "confidence": "high",
        "scripture_references": [{"reference": "Acts 10:1-48", "relationship": "primary"}],
        "sources": [{"id": "acts-greek", "title": "Acts 10", "source_type": "scripture"}],
        "claims": [{
            "id": "cornelius-centurion",
            "claim": "Cornelius was a centurion in Caesarea.",
            "claim_type": "historical_cultural",
            "certainty": "textually_explicit",
            "dispute_status": "not_disputed",
            "scripture_references": ["Acts 10:1"],
            "source_ids": ["acts-greek"],
        }],
        "evidence_items": [],
    }
    bundle = build_evidence_bundle(
        target["reference"],
        canonical_results=_results([*target["objects"], unrelated]),
    )

    assert "cornelius" not in bundle.entities_by_id
    assert "cornelius-centurion" not in bundle.evidence_by_id
    assert all("Cornelius" not in item.claim for item in bundle.evidence_items)


def test_broad_parent_retains_explicit_passage_specific_evidence():
    broad_parent = {
        "id": "ruth-book-background",
        "type": "person",
        "title": "Broad Ruth background",
        "scripture_references": [{"reference": "Ruth"}],
        "historical_context": "Broad book-level context must not become evidence.",
        "sources": [{"id": "ruth-source", "title": "Ruth source"}],
        "claims": [],
        "evidence_items": [{
            "id": "ruth-1-specific-evidence",
            "evidence_type": "historical-event",
            "description": "Naomi and Ruth arrived in Bethlehem together.",
            "passage_relevance": "The arrival establishes the passage's immediate setting.",
            "confidence": "high",
            "certainty": "textually_explicit",
            "dispute_status": "not_disputed",
            "source_ids": ["ruth-source"],
            "scripture_references": [{
                "reference": "Ruth 1:19-22",
                "relationship": "direct",
            }],
        }],
    }

    bundle = build_evidence_bundle(
        "Ruth 1:19-22",
        canonical_results=_results([broad_parent]),
    )
    packet = deterministic_presentation(bundle)

    assert "ruth-book-background" not in bundle.entities_by_id
    assert "ruth-1-specific-evidence" in bundle.evidence_by_id
    assert all(
        "Broad book-level context" not in item.claim
        for item in bundle.evidence_items
    )
    assert any(
        "ruth-1-specific-evidence" in card.evidence_ids
        for card in packet.cards
    )


@pytest.mark.parametrize(
    ("target_reference", "entity_id", "entity_title", "unrelated_anchor"),
    [
        ("Ruth 1", "cornelius", "Cornelius", "Acts 10:1-48"),
        ("Genesis 1", "john", "John", "John 1:1-18"),
        ("Ezra 7", "ezra-census-person", "A person from Ezra's census", "Ezra"),
    ],
)
def test_known_entity_leak_patterns_are_rejected(target_reference, entity_id, entity_title, unrelated_anchor):
    unrelated = {
        "id": entity_id,
        "type": "person",
        "title": entity_title,
        "importance": 100,
        "confidence": "high",
        "scripture_references": [{"reference": unrelated_anchor, "relationship": "primary"}],
        "sources": [{"id": "source", "title": "Source"}],
        "claims": [],
        "evidence_items": [],
    }

    bundle = build_evidence_bundle(target_reference, canonical_results=_results([unrelated]))

    assert entity_id not in bundle.entities_by_id


def test_valid_packet_parses_and_invalid_evidence_id_is_rejected():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(fixture["reference"], canonical_results=_results(fixture["objects"]))
    packet = deterministic_presentation(bundle).to_dict()

    valid = validate_presentation_packet(packet, bundle)
    assert valid.valid, valid.errors

    packet["cards"][0]["evidence_ids"] = ["model-invented-evidence"]
    invalid = validate_presentation_packet(packet, bundle)
    assert not invalid.valid
    assert any("unsupported evidence IDs" in error for error in invalid.errors)


def test_detectable_unsupported_model_date_is_rejected():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(fixture["reference"], canonical_results=_results(fixture["objects"]))
    packet = deterministic_presentation(bundle).to_dict()
    packet["cards"][0]["body"] += " This happened in AD 325."

    invalid = validate_presentation_packet(packet, bundle)
    assert not invalid.valid
    assert any("unsupported date" in error for error in invalid.errors)


def test_dig_in_summary_is_optional_bounded_and_checked_against_cited_evidence():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"], canonical_results=_results(fixture["objects"])
    )
    packet = deterministic_presentation(bundle).to_dict()
    packet["cards"][0]["dig_in_summary"] = (
        "The cited evidence connects visibility and social influence in the setting. "
        "It helps explain why the action was not merely private."
    )

    assert validate_presentation_packet(packet, bundle).valid

    too_long = copy.deepcopy(packet)
    too_long["cards"][0]["dig_in_summary"] = "x" * 801
    assert any(
        "dig_in_summary exceeds 800" in error
        for error in validate_presentation_packet(too_long, bundle).errors
    )

    unsupported = copy.deepcopy(packet)
    unsupported["cards"][0]["dig_in_summary"] += " This began in AD 325."
    assert any(
        "unsupported date" in error
        for error in validate_presentation_packet(unsupported, bundle).errors
    )


@pytest.mark.parametrize(
    "date_text",
    ["70 AD", "70 CE", "586 BC", "586 BCE", "AD 70", "BC 586", "c. 586 BC", "approximately 586 BC"],
)
def test_date_validator_recognizes_only_clear_era_dates(date_text):
    bundle = build_evidence_bundle(
        "2 Kings 25:1",
        geography={
            "places": [{
                "id": "jerusalem",
                "title": "Jerusalem",
                "summary": "Jerusalem has evidence associated with 70 AD and 586 BC.",
            }],
            "routes": [],
        },
    )
    packet = deterministic_presentation(bundle).to_dict()
    packet["cards"][0]["body"] = f"The supplied chronology includes {date_text}."

    result = validate_presentation_packet(packet, bundle)

    assert result.valid, result.errors


def test_plain_quantity_is_not_treated_as_a_date():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"], canonical_results=_results(fixture["objects"])
    )
    packet = deterministic_presentation(bundle).to_dict()
    packet["cards"][0]["body"] += " The account mentions 500 people."

    result = validate_presentation_packet(packet, bundle)

    assert result.valid, result.errors


class _InvalidProvider(PresentationProvider):
    model = "fixture-model"

    def generate(self, bundle, ranked, generated_from):
        return {
            "passage_ref": bundle.passage_ref,
            "cards": [{
                "id": "bad",
                "type": "did_you_know",
                "headline": "Unsupported",
                "body": "Unsupported model claim.",
                "evidence_ids": ["invented"],
                "confidence": "high",
                "interpretation_level": "fact",
                "related_entity_ids": [],
                "map_focus": None,
                "dig_deeper_actions": [],
            }],
            "generated_from": generated_from.to_dict(),
        }


def test_cache_from_a_different_model_is_not_reused():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(fixture["reference"], canonical_results=_results(fixture["objects"]))
    cached = deterministic_presentation(bundle).to_dict()
    cached["generated_from"]["prompt_version"] = PRESENTATION_PROMPT_VERSION
    cached["generated_from"]["model"] = "previous-compatible-model"
    cache = MemoryPresentationCache()
    cache.put(presentation_cache_key(bundle, prompt_version=PRESENTATION_PROMPT_VERSION), cached)

    engine = PresentationEngine(provider=_InvalidProvider(), cache=cache)
    result = engine.present(bundle)

    assert result.mode == "deterministic_fallback"
    assert result.packet.cards
    assert any("unsupported evidence IDs" in item for item in result.diagnostics)
    assert engine.diagnostics()["provider"] == {
        "attempts": 1,
        "failures": 0,
        "parse_failures": 0,
        "rejections": 1,
        "saturated": 0,
    }


def test_cache_key_changes_when_evidence_changes():
    first_fixture, second_fixture = FIXTURES[0], FIXTURES[2]
    first = build_evidence_bundle(first_fixture["reference"], canonical_results=_results(first_fixture["objects"]))
    second = build_evidence_bundle(second_fixture["reference"], canonical_results=_results(second_fixture["objects"]))

    assert presentation_cache_key(first, prompt_version="v1") != presentation_cache_key(second, prompt_version="v1")
    assert presentation_cache_key(first, prompt_version="v1") != presentation_cache_key(first, prompt_version="v2")


def test_sqlite_cache_persists_packets_and_prunes_old_entries(tmp_path):
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
    )
    packet = deterministic_presentation(bundle).to_dict()
    path = tmp_path / "presentation-cache.sqlite"
    cache = SQLitePresentationCache(path, maximum_entries=2)

    cache.put("first", packet)
    cache.put("second", packet)
    cache.put("third", packet)

    reopened = SQLitePresentationCache(path, maximum_entries=2)
    assert reopened.get("third") == packet
    assert reopened.diagnostics()["entry_count"] == 2
    assert reopened.diagnostics()["healthy"] is True


def test_default_presentation_cache_is_separate_from_study_database(tmp_path):
    study_path = tmp_path / "study.sqlite"

    cache_path = default_presentation_cache_path(study_path)

    assert cache_path == tmp_path / "study.presentation-cache.sqlite"
    assert cache_path != study_path


def test_versioned_presentation_bundle_is_fingerprinted_and_grounded(tmp_path):
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
    )
    packet = deterministic_presentation(bundle).to_dict()
    packet["generated_from"]["prompt_version"] = PRESENTATION_PROMPT_VERSION
    packet["generated_from"]["model"] = "pre-generated-fixture"
    path = tmp_path / "presentation-bundle.json"
    path.write_text(
        json.dumps(
            {
                "format": PRESENTATION_BUNDLE_FORMAT,
                "version": PRESENTATION_BUNDLE_VERSION,
                "packets": [packet],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_presentation_bundle(path)
    result = PresentationEngine(bundled_packets=loaded).present(bundle)

    assert len(loaded) == 1
    assert result.mode == "bundled"
    assert result.packet.to_dict() == packet


def test_duplicate_bundle_fingerprint_rejects_the_entire_file(tmp_path):
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
    )
    packet = deterministic_presentation(bundle).to_dict()
    packet["generated_from"]["prompt_version"] = PRESENTATION_PROMPT_VERSION
    path = tmp_path / "duplicate-presentation-bundle.json"
    path.write_text(
        json.dumps(
            {
                "format": PRESENTATION_BUNDLE_FORMAT,
                "version": PRESENTATION_BUNDLE_VERSION,
                "packets": [packet, packet],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PresentationBundleError, match="duplicates a fingerprint"):
        load_presentation_bundle(path)


def test_loaded_bundle_packet_is_still_grounded_against_current_evidence(tmp_path):
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
    )
    packet = deterministic_presentation(bundle).to_dict()
    packet["generated_from"]["prompt_version"] = PRESENTATION_PROMPT_VERSION
    packet["cards"][0]["evidence_ids"] = ["unsupported-bundled-evidence"]
    path = tmp_path / "ungrounded-presentation-bundle.json"
    path.write_text(
        json.dumps(
            {
                "format": PRESENTATION_BUNDLE_FORMAT,
                "version": PRESENTATION_BUNDLE_VERSION,
                "packets": [packet],
            }
        ),
        encoding="utf-8",
    )

    engine = PresentationEngine(bundled_packets=load_presentation_bundle(path))
    result = engine.present(bundle)

    assert result.mode == "deterministic_fallback"
    assert any("bundled: card[0] cites unsupported evidence IDs" in item for item in result.diagnostics)
    assert engine.diagnostics()["bundles"]["grounding_rejections"] == 1


class _WorkingProvider(PresentationProvider):
    model = "fixture-model"

    def generate(self, bundle, ranked, generated_from):
        packet = deterministic_presentation(bundle).to_dict()
        packet["generated_from"] = generated_from.to_dict()
        return packet


class _FailingProvider(PresentationProvider):
    model = "fixture-model"

    def generate(self, bundle, ranked, generated_from):
        raise RuntimeError("provider unavailable")


class _ProfileProvider(PresentationProvider):
    def __init__(self, model, adapter="openrouter"):
        self.model = model
        self.generation_profile = f"{adapter}:{model}"
        self.calls = 0

    def generate(self, bundle, ranked, generated_from):
        self.calls += 1
        packet = deterministic_presentation(bundle).to_dict()
        packet["generated_from"] = generated_from.to_dict()
        return packet


def test_switching_models_uses_a_distinct_credential_free_cache_profile():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"], canonical_results=_results(fixture["objects"])
    )
    cache = MemoryPresentationCache()
    engine = PresentationEngine(cache=cache)
    model_a = _ProfileProvider("model-a")
    model_b = _ProfileProvider("model-b")

    first = engine.present_with_provider(bundle, model_a)
    second = engine.present_with_provider(bundle, model_b)

    assert first.mode == "generated"
    assert second.mode == "generated"
    assert model_a.calls == model_b.calls == 1
    assert len(cache._values) == 2
    assert "api-key" not in json.dumps(cache._values)


def test_same_model_through_different_adapters_uses_distinct_cache_profiles():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"], canonical_results=_results(fixture["objects"])
    )
    cache = MemoryPresentationCache()
    engine = PresentationEngine(cache=cache)
    openrouter = _ProfileProvider("test-model", adapter="openrouter")
    compatible = _ProfileProvider("test-model", adapter="openai_compatible")

    first = engine.present_with_provider(bundle, openrouter)
    second = engine.present_with_provider(bundle, compatible)

    assert first.mode == "generated"
    assert second.mode == "generated"
    assert openrouter.calls == compatible.calls == 1
    assert len(cache._values) == 2


def test_durable_cache_survives_provider_failure(tmp_path):
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
    )
    path = tmp_path / "presentation-cache.sqlite"

    generated = PresentationEngine(
        provider=_WorkingProvider(),
        cache=SQLitePresentationCache(path),
    ).present(bundle)
    cached = PresentationEngine(
        provider=_FailingProvider(),
        cache=SQLitePresentationCache(path),
    ).present(bundle)

    assert generated.mode == "generated"
    assert cached.mode == "cached"
    assert cached.packet.to_dict() == generated.packet.to_dict()
    assert cached.diagnostics == ()


def test_provider_exception_payload_is_not_retained_or_logged(caplog):
    secret = "private-provider-payload-123"

    class SecretFailingProvider(PresentationProvider):
        model = "fixture-model"

        def generate(self, bundle, ranked, generated_from):
            raise RuntimeError(secret)

    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
    )

    with caplog.at_level("WARNING", logger="bhf_agent.presentation.engine"):
        result = PresentationEngine(provider=SecretFailingProvider()).present(bundle)

    assert result.mode == "deterministic_fallback"
    assert result.diagnostics == ("provider failure: RuntimeError",)
    assert secret not in caplog.text
    assert secret not in str(result.diagnostics)


def test_rejected_durable_packet_is_discarded(tmp_path):
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
    )
    path = tmp_path / "presentation-cache.sqlite"
    cache = SQLitePresentationCache(path)
    key = presentation_cache_key(bundle, prompt_version=PRESENTATION_PROMPT_VERSION)
    incompatible = deterministic_presentation(bundle).to_dict()
    cache.put(key, incompatible)

    result = PresentationEngine(cache=cache).present(bundle)

    assert result.mode == "deterministic_fallback"
    assert any("cached: generated_from.prompt_version" in item for item in result.diagnostics)
    assert cache.get(key) is None


def test_cache_read_failure_never_breaks_deterministic_fallback():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
    )

    class BrokenCache:
        def get(self, key):
            raise OSError("unreadable cache")

        def put(self, key, packet):
            raise OSError("unwritable cache")

    engine = PresentationEngine(cache=BrokenCache())
    result = engine.present(bundle)

    assert result.mode == "deterministic_fallback"
    assert result.packet.cards
    assert any("cache read failure: OSError" in item for item in result.diagnostics)
    assert engine.diagnostics()["cache"]["read_failures"] == 1


def test_cache_write_failure_still_returns_valid_generated_packet():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
    )

    class WriteBrokenCache:
        def get(self, key):
            return None

        def put(self, key, packet):
            raise OSError("unwritable cache")

    engine = PresentationEngine(
        provider=_WorkingProvider(),
        cache=WriteBrokenCache(),
    )
    result = engine.present(bundle)

    assert result.mode == "generated"
    assert result.packet.cards
    assert any("cache write failure: OSError" in item for item in result.diagnostics)
    assert engine.diagnostics()["cache"]["write_failures"] == 1


def test_cache_first_engine_coalesces_simultaneous_generation_requests():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
    )
    worker_count = 6

    class SimultaneousMissCache(MemoryPresentationCache):
        def __init__(self):
            super().__init__()
            self._initial_reads = 0
            self._reads_lock = threading.Lock()
            self._initial_read_barrier = threading.Barrier(worker_count)

        def get(self, key):
            value = super().get(key)
            with self._reads_lock:
                self._initial_reads += 1
                initial_read = self._initial_reads <= worker_count
            if initial_read:
                self._initial_read_barrier.wait(timeout=3)
            return value

    class CountingProvider(_WorkingProvider):
        def __init__(self):
            self.calls = 0
            self._calls_lock = threading.Lock()

        def generate(self, bundle, ranked, generated_from):
            with self._calls_lock:
                self.calls += 1
            return super().generate(bundle, ranked, generated_from)

    provider = CountingProvider()
    engine = PresentationEngine(
        provider=provider,
        cache=SimultaneousMissCache(),
    )

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(executor.map(engine.present, [bundle] * worker_count))

    assert provider.calls == 1
    assert all(result.packet.to_dict() == results[0].packet.to_dict() for result in results)
    assert {result.mode for result in results}.issubset({"generated", "cached"})
    assert any(result.mode == "generated" for result in results)
    activity = engine.diagnostics()
    assert activity["requests_total"] == worker_count
    assert sum(activity["outcomes"].values()) == worker_count
    assert activity["provider"]["attempts"] == 1


def test_provider_gate_rejects_distinct_concurrent_miss_and_preserves_fallback():
    first_fixture, second_fixture = FIXTURES[0], FIXTURES[2]
    first_bundle = build_evidence_bundle(
        first_fixture["reference"],
        canonical_results=_results(first_fixture["objects"]),
    )
    second_bundle = build_evidence_bundle(
        second_fixture["reference"],
        canonical_results=_results(second_fixture["objects"]),
    )
    provider_started = threading.Event()
    release_provider = threading.Event()

    class BlockingProvider(_WorkingProvider):
        def __init__(self):
            self.calls = 0

        def generate(self, bundle, ranked, generated_from):
            self.calls += 1
            provider_started.set()
            if not release_provider.wait(timeout=3):
                raise TimeoutError("test did not release provider")
            return super().generate(bundle, ranked, generated_from)

    provider = BlockingProvider()
    engine = PresentationEngine(
        provider=provider,
        maximum_concurrent_provider_requests=1,
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        first_future = executor.submit(engine.present, first_bundle)
        assert provider_started.wait(timeout=3)
        saturated = engine.present(second_bundle)
        release_provider.set()
        first = first_future.result(timeout=3)

    assert first.mode == "generated"
    assert saturated.mode == "deterministic_fallback"
    assert provider.calls == 1
    assert any(
        "provider capacity unavailable" in item
        for item in saturated.diagnostics
    )
    activity = engine.diagnostics()
    assert activity["provider"] == {
        "attempts": 1,
        "failures": 0,
        "parse_failures": 0,
        "rejections": 0,
        "saturated": 1,
    }
    assert activity["provider_gate"] == {
        "enabled": True,
        "limit": 1,
        "active": 0,
        "peak_active": 1,
    }


def test_adapter_provider_receives_only_ranked_evidence_and_strict_grounding_prompt():
    fixture = FIXTURES[2]
    bundle = build_evidence_bundle(fixture["reference"], canonical_results=_results(fixture["objects"]))
    ranked = rank_evidence(bundle, limit=1)
    requests = []

    class Adapter:
        def supports_json_schema_response_format(self):
            return False

        def chat(self, request):
            requests.append(request)
            supplied = json.loads(request.user_prompt)
            return ChatResponse(text=json.dumps({
                "passage_ref": bundle.passage_ref,
                "cards": [],
                "generated_from": supplied["generated_from_must_equal"],
            }))

    generated_from = GeneratedFrom(
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        presentation_schema_version="1.0",
        prompt_version=PRESENTATION_PROMPT_VERSION,
        model="fixture-model",
    )
    provider = AdapterPresentationProvider(Adapter(), model="fixture-model")

    result = provider.generate(bundle, ranked, generated_from)

    assert result["cards"] == []
    assert len(json.loads(requests[0].user_prompt)["evidence"]) == 1
    supplied = json.loads(requests[0].user_prompt)
    assert all(
        set(entity).issubset({"id", "title", "type", "aliases"})
        for entity in supplied["entities"]
    )
    assert all("metadata" not in entity for entity in supplied["entities"])
    assert all(
        set(item["relevance_metadata"]).issubset({
            "passage_relationship",
            "anchor_specificity",
            "certainty",
            "dispute_status",
            "assertion_type",
            "presentation_role",
            "supports_evidence_ids",
            "map_resource_kind",
            "map_resource_id",
        })
        for item in supplied["evidence"]
    )
    assert all("parent_title" not in item["relevance_metadata"] for item in supplied["evidence"])
    assert ranked[0].item.id in requests[0].user_prompt
    assert "use model memory as a factual source" in requests[0].system_prompt
    assert "return no card" in requests[0].system_prompt
    assert "Use why_it_matters only" in requests[0].system_prompt
    assert "do not add application, doctrine" in requests[0].system_prompt
    assert "dig_in_summary" in supplied["output_shape"]["cards"][0]
    assert supplied["limits"]["dig_in_summary_characters"] == 800
    assert "same response" in requests[0].system_prompt
    assert "those same" in requests[0].system_prompt


def test_provider_receives_only_ranked_geography_resources():
    bundle = build_evidence_bundle(
        "Mark 5:1",
        geography={
            "places": [
                {"id": "gerasa", "title": "Gerasa", "summary": "Gerasa lies east of the lake.", "confidence": "likely"},
                {"id": "decapolis", "title": "Decapolis", "summary": "The Decapolis was a wider region.", "confidence": "likely"},
            ],
            "routes": [],
        },
    )
    ranked = rank_evidence(bundle, limit=1)
    requests = []

    class Adapter:
        def supports_json_schema_response_format(self):
            return False

        def chat(self, request):
            requests.append(request)
            supplied = json.loads(request.user_prompt)
            return ChatResponse(text=json.dumps({
                "passage_ref": bundle.passage_ref,
                "cards": [],
                "generated_from": supplied["generated_from_must_equal"],
            }))

    generated_from = GeneratedFrom(
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        presentation_schema_version="1.0",
        prompt_version=PRESENTATION_PROMPT_VERSION,
        model="fixture-model",
    )
    AdapterPresentationProvider(Adapter(), model="fixture-model").generate(bundle, ranked, generated_from)
    supplied = json.loads(requests[0].user_prompt)

    assert len(supplied["geography"]["places"]) == 1
    assert supplied["geography"]["places"][0]["id"] == ranked[0].item.relevance_metadata["map_resource_id"]
    assert set(supplied["geography"]["places"][0]) == {"id", "title", "kind"}
    assert "summary" not in supplied["geography"]["places"][0]
    assert supplied["limits"]["card_types"] == [
        "did_you_know",
        "walk_the_land",
        "why_it_matters",
    ]
