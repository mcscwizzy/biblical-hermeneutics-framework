from fastapi import FastAPI
from fastapi.testclient import TestClient

from bhf_agent.presentation import (
    PresentationEngine,
    SQLitePresentationCache,
    deterministic_presentation,
    presentation_cache_key,
    rank_evidence,
)
from bhf_agent.study_db import initialize_database
from bhf_web.routes.study import register_study_routes
from bhf_web.services.companion_context import CompanionContextService


def _service(tmp_path, *, presentation_engine=None):
    study_db_path = tmp_path / "study.sqlite"
    return CompanionContextService(
        study_db_path=study_db_path,
        commentary_db_path=tmp_path / "commentary.sqlite",
        presentation_engine=presentation_engine,
        presentation_cache_path=tmp_path / "presentation-cache.sqlite",
    )


def test_ckl_backed_companion_api_cites_jonah_reception_on_visible_discovery(tmp_path):
    study_db_path = tmp_path / "study.sqlite"
    service = _service(tmp_path)
    bundle = service.build_evidence_bundle_for_passage(
        book="Jonah",
        chapter=1,
        verse_start=17,
        verse_end=17,
    )
    baseline_packet = deterministic_presentation(
        bundle,
        rank_evidence(bundle, limit=8),
    )
    app = FastAPI()
    register_study_routes(
        app,
        study_db_path=str(study_db_path),
        templates=None,
        commentary_db_path=tmp_path / "commentary.sqlite",
        companion_context_service=service,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/study/companion-context",
            params={
                "book": "Jonah",
                "chapter": 1,
                "verse_start": 17,
                "verse_end": 17,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reference"] == "Jonah 1:17"
    cards = [
        card
        for card in payload["presentation_packet"]["cards"]
        if card["type"] == "did_you_know"
    ]
    assert len(cards) == 3
    assert [card["id"] for card in cards] == [
        "did-you-know-jonah-great-fish",
        "did-you-know-jonah-numbering",
        "did-you-know-jonah-prayer-composition",
    ]
    for card, baseline_card in zip(cards, baseline_packet.cards, strict=True):
        assert card["headline"] == baseline_card.headline
        assert card["body"] == baseline_card.body
        assert card["confidence"] == baseline_card.confidence
        assert card["interpretation_level"] == baseline_card.interpretation_level
    fish_discovery = cards[0]
    assert fish_discovery["evidence_ids"] == [
        "jonah-great-fish",
        "jonah-three-days",
    ]

    evidence = {item["id"]: item for item in payload["presentation_evidence"]}
    assert evidence["jonah-three-days"]["ckl_record_identity"] == {
        "object_id": "jonah",
        "record_kind": "claim",
        "record_id": "jonah-three-days",
    }
    assert "later becomes important in Matthew 12:40" in evidence["jonah-three-days"]["claim"]
    assert {source["id"] for source in evidence["jonah-three-days"]["sources"]} >= {
        "jonah-masoretic",
        "jonah-new-testament",
    }


def test_ckl_backed_cached_companion_packet_cites_the_same_support_record(tmp_path):
    study_db_path = tmp_path / "study.sqlite"
    initialize_database(study_db_path)
    cache = SQLitePresentationCache(tmp_path / "presentation-cache.sqlite")
    engine = PresentationEngine(cache=cache)
    service = _service(tmp_path, presentation_engine=engine)
    bundle = service.build_evidence_bundle_for_passage(
        book="Jonah",
        chapter=1,
        verse_start=17,
        verse_end=17,
    )
    cached_packet = deterministic_presentation(
        bundle,
        rank_evidence(bundle, limit=8),
    ).to_dict()
    cached_packet["generated_from"]["prompt_version"] = engine.prompt_version
    cache_key = presentation_cache_key(
        bundle,
        prompt_version=engine.prompt_version,
    )
    cache.put(cache_key, cached_packet)
    cached_result = engine.present_local(bundle)
    assert cached_result.mode == "cached"
    cached_fish_discovery = next(
        card
        for card in cached_result.packet.cards
        if card.id == "did-you-know-jonah-great-fish"
    )
    assert cached_fish_discovery.evidence_ids == [
        "jonah-great-fish",
        "jonah-three-days",
    ]

    app = FastAPI()
    register_study_routes(
        app,
        study_db_path=str(study_db_path),
        templates=None,
        commentary_db_path=tmp_path / "commentary.sqlite",
        companion_context_service=service,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/study/companion-context",
            params={
                "book": "Jonah",
                "chapter": 1,
                "verse_start": 17,
                "verse_end": 17,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    fish_discovery = next(
        card
        for card in payload["presentation_packet"]["cards"]
        if card["id"] == "did-you-know-jonah-great-fish"
    )
    assert fish_discovery["evidence_ids"] == ["jonah-great-fish", "jonah-three-days"]
    evidence = {item["id"]: item for item in payload["presentation_evidence"]}
    assert evidence["jonah-three-days"]["ckl_record_identity"] == {
        "object_id": "jonah",
        "record_kind": "claim",
        "record_id": "jonah-three-days",
    }


def test_ckl_backed_unrelated_passages_keep_their_uncached_card_evidence(tmp_path):
    study_db_path = tmp_path / "study.sqlite"
    initialize_database(study_db_path)
    service = _service(tmp_path)
    passages = (
        ("Genesis", 1, 1, 5),
        ("Acts", 2, 1, 47),
        ("Psalm", 22, 1, 1),
        ("Deuteronomy", 32, 8, 9),
    )

    for book, chapter, verse_start, verse_end in passages:
        bundle = service.build_evidence_bundle_for_passage(
            book=book,
            chapter=chapter,
            verse_start=verse_start,
            verse_end=verse_end,
        )
        ranked = rank_evidence(bundle, limit=8)
        baseline = deterministic_presentation(bundle, ranked)
        result = service.presentation_engine.present_local(bundle)

        assert [card.id for card in result.packet.cards] == [
            card.id for card in baseline.cards
        ]
        assert [card.evidence_ids for card in result.packet.cards] == [
            card.evidence_ids for card in baseline.cards
        ]
        assert len(result.packet.cards) <= 3
