from __future__ import annotations

from bhf_agent.archaeology_expansion import ARCHAEOLOGY_ITEMS as EXPANSION_ITEMS
from bhf_agent.archaeology_resolver import resolve_archaeology_evidence
from bhf_agent.archaeology_service import ArchaeologyService
from bhf_agent.study_db import initialize_database, list_archaeology_items


def test_curated_archaeology_corpus_has_cross_period_depth_and_required_evidence(tmp_path) -> None:
    database = tmp_path / "study.sqlite"
    initialize_database(database)
    items = list_archaeology_items(path=database)

    assert len(items) >= 70
    assert len({item["id"] for item in items}) == len(items)
    assert {"Broad / uncertain period", "Divided Kingdom", "Assyrian period", "Babylonian period", "Persian period", "Hellenistic period", "NT / Roman period"}.issubset(
        {period for item in items for period in item["periods"]}
    )

    expansion_ids = {item["id"] for item in EXPANSION_ITEMS}
    for item in items:
        if item["id"] not in expansion_ids:
            continue
        assert item["source_name"]
        assert item["source_url"].startswith("https://")
        details = item["evidence_details"]
        for key in ("description", "evidence_summary", "biblical_relevance", "interpretive_caution"):
            assert details[key]


def test_major_passage_clusters_surface_multiple_specific_evidence_records(tmp_path) -> None:
    database = tmp_path / "study.sqlite"
    initialize_database(database)

    clusters = {
        ("2 Kings", 18): {"lachish-siege-ramp", "lachish-destruction-level"},
        ("Jeremiah", 39): {"jerusalem-babylonian-destruction"},
        ("John", 2): {"jerusalem-mikvaot", "jewish-stone-vessels"},
        ("Acts", 18): {"gallio-inscription", "corinth-excavations", "corinth-bema"},
        ("Acts", 19): {"ephesus-theater", "temple-artemis-ephesus"},
        ("Revelation", 2): {"smyrna-roman-city", "pergamum-imperial-cult", "thyatira-trade-and-inscriptions"},
    }
    for (book, chapter), expected in clusters.items():
        result = resolve_archaeology_evidence(book=book, chapter=chapter, path=database)
        returned = {item["id"] for item in result["archaeological_items"]}
        assert expected.issubset(returned)


def test_expansion_preserves_visible_uncertainty_and_reviewed_media_rights(tmp_path) -> None:
    database = tmp_path / "study.sqlite"
    initialize_database(database)
    items = list_archaeology_items(path=database)

    disputed = {
        item["id"]
        for item in items
        if item["evidence_details"].get("dispute_status") != "not_disputed"
    }
    assert {"bethsaida-identification", "khirbet-qeiyafa-fortress", "al-yahudu-tablets", "laodicea-water-system"}.issubset(disputed)

    media = [record for item in items for record in item["media"]]
    assert len(media) >= 30
    assert all(record["can_redistribute"] and record["can_cache"] for record in media)


def test_browse_exposes_full_corpus_and_existing_filters_at_75_records(tmp_path) -> None:
    database = tmp_path / "study.sqlite"
    initialize_database(database)
    service = ArchaeologyService(database)

    assert len(service.browse()) >= 75
    assert {item["id"] for item in service.search("Ephesus")} >= {"ephesus-theater", "temple-artemis-ephesus"}
    assert {item["id"] for item in service.search(period="Persian period")} >= {"yehud-coinage"}
    assert {item["id"] for item in service.search(item_type="synagogue")} >= {"magdala-synagogue", "sardis-synagogue"}
    assert {item["id"] for item in service.search(biblical_book="Revelation")} >= {"laodicea-water-system", "pergamum-imperial-cult"}
    assert all(item["confidence"] == "likely" for item in service.search(confidence="likely"))
