from __future__ import annotations

import sqlite3

import pytest

from bhf_agent.archaeology_resolver import resolve_archaeology_evidence
from bhf_agent.study_db import initialize_database, list_archaeology_items


def test_exact_scripture_links_are_ranked_and_bounded(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    result = resolve_archaeology_evidence(
        book="John",
        chapter=9,
        verse_start=7,
        verse_end=11,
        passage_text="Then he sent him away to the pool of Siloam.",
        path=path,
    )

    assert result["reference"] == "John 9:7-11"
    assert result["archaeological_items"][0]["id"] == "pool-of-siloam"
    assert result["archaeological_items"][0]["biblical_relationship"] == "direct_context"
    assert result["archaeological_items"][0]["coordinates"]["latitude"] is not None
    assert len(result["archaeological_items"]) <= 8


def test_chapter_and_verse_range_resolution_use_link_overlap(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    chapter = resolve_archaeology_evidence(book="2 Kings", chapter=20, path=path)
    verse_range = resolve_archaeology_evidence(
        book="2 Kings", chapter=20, verse_start=20, verse_end=20, path=path
    )

    chapter_ids = {item["id"] for item in chapter["archaeological_items"]}
    range_ids = {item["id"] for item in verse_range["archaeological_items"]}
    assert {"siloam-inscription", "hezekiahs-tunnel-item"}.issubset(chapter_ids)
    assert range_ids == {"siloam-inscription", "hezekiahs-tunnel-item"}


def test_generic_terms_do_not_create_archaeology_matches(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    result = resolve_archaeology_evidence(
        book="John",
        chapter=1,
        verse_start=1,
        verse_end=5,
        passage_text="The king went into the city and saw a stone.",
        path=path,
    )

    assert result["archaeological_items"] == []
    assert result["empty_state"] is True


def test_enriched_records_keep_evidence_and_passage_relevance_distinct(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    items = list_archaeology_items(path=path)
    assert len(items) >= 20
    result = resolve_archaeology_evidence(
        book="John", chapter=9, verse_start=7, verse_end=11, path=path
    )
    card = result["archaeological_items"][0]

    assert card["id"] == "pool-of-siloam"
    assert card["description"]
    assert card["biblical_relevance"]
    assert card["description"] != card["significance"]
    assert card["discovery_context"]
    assert card["evidence_summary"]
    assert card["cautions"]
    assert card["media"]


def test_seeded_media_covers_major_ot_and_nt_archaeology_examples(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    media_by_id = {
        item["id"]: item["media"]
        for item in list_archaeology_items(path=path)
    }

    for item_id in (
        "tel-dan-stele",
        "siloam-inscription",
        "pool-of-siloam",
        "pool-of-bethesda",
        "caesarea-maritima-excavations",
        "capernaum-excavations",
    ):
        assert media_by_id[item_id]
        assert media_by_id[item_id][0]["source_url"].startswith("https://commons.wikimedia.org/")
        assert media_by_id[item_id][0]["can_redistribute"] is True


def test_open_context_provenance_is_exposed_as_reviewed_evidence_metadata(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    result = resolve_archaeology_evidence(
        book="2 Kings", chapter=9, verse_start=14, verse_end=15, path=path
    )
    card = next(
        item for item in result["archaeological_items"]
        if item["id"] == "black-obelisk"
    )

    assert card["evidence_sources"] == [
        {
            "label": "Open Context: Iraq Heritage Program (Nimrud/Calah provenance)",
            "url": "https://opencontext.org/projects/b0a915f3-43cd-1d81-cc89-043d7e11e7c9",
            "license": "CC BY 4.0",
            "record_id": "b0a915f3-43cd-1d81-cc89-043d7e11e7c9",
        }
    ]


def test_cross_period_corpus_expansion_keeps_links_specific_and_caveated(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    items = {item["id"]: item for item in list_archaeology_items(path=path)}
    assert len(items) >= 30
    for item_id in (
        "merneptah-stele",
        "shoshenq-karnak-relief",
        "arad-ostraca",
        "temple-warning-inscription",
        "gallio-inscription",
    ):
        assert items[item_id]["evidence_details"]["interpretive_caution"]
        assert items[item_id]["source_url"].startswith("https://")

    acts = resolve_archaeology_evidence(
        book="Acts", chapter=18, verse_start=12, verse_end=17, path=path
    )
    gallio = next(item for item in acts["archaeological_items"] if item["id"] == "gallio-inscription")
    assert gallio["biblical_relationship"] == "historical_context"
    assert "does not mention Paul" in gallio["interpretive_caution"]


def test_babylon_context_is_upgraded_from_text_first_to_reviewed_media(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM archaeology_scripture_links WHERE item_id = ?",
            ("babylon-ishtar-gate-context",),
        )
        connection.execute(
            "DELETE FROM archaeology_items WHERE id = ?",
            ("babylon-ishtar-gate-context",),
        )
        connection.execute("DELETE FROM archaeology_sites WHERE id = ?", ("babylon",))
        connection.execute("DELETE FROM schema_migrations WHERE version = 32")
        connection.execute("DELETE FROM schema_migrations WHERE version = 33")

    initialize_database(path)
    item = next(
        item
        for item in list_archaeology_items(path=path)
        if item["id"] == "babylon-ishtar-gate-context"
    )
    assert item["site_id"] == "babylon"
    assert {record["id"] for record in item["media"]} == {"wm-babylon-ishtar-gate-1932"}
    assert item["evidence_details"]["interpretive_caution"]

    result = resolve_archaeology_evidence(
        book="Daniel", chapter=1, verse_start=1, verse_end=7, path=path
    )
    card = next(
        candidate
        for candidate in result["archaeological_items"]
        if candidate["id"] == "babylon-ishtar-gate-context"
    )
    assert card["biblical_relationship"] == "historical_setting"
    assert {record["id"] for record in card["media"]} == {"wm-babylon-ishtar-gate-1932"}


def test_cross_period_records_have_reviewed_reusable_media(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    items = {item["id"]: item for item in list_archaeology_items(path=path)}
    assert sum(len(item["media"]) for item in items.values()) >= 20
    expected_media = {
        "merneptah-stele": "wm-merneptah-stele",
        "shoshenq-karnak-relief": "wm-shoshenq-karnak-relief",
        "arad-ostraca": "wm-arad-ostracon-18",
        "temple-warning-inscription": "wm-temple-warning-inscription",
        "gallio-inscription": "wm-gallio-inscription",
    }
    for item_id, media_id in expected_media.items():
        media = next(record for record in items[item_id]["media"] if record["id"] == media_id)
        assert media["source_url"].startswith("https://commons.wikimedia.org/")
        assert media["can_redistribute"] is True
        assert media["can_cache"] is True
        assert media["attribution_text"]


def test_every_seeded_archaeology_record_has_reviewed_image_attribution(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    items = list_archaeology_items(path=path)

    assert items
    assert all(item["media"] for item in items)
    assert all(item["media"][0]["image_url"] for item in items)
    assert all(item["media"][0]["attribution_text"] for item in items)


def test_v20_backfills_cross_period_corpus_for_existing_database(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    item_ids = (
        "merneptah-stele",
        "shoshenq-karnak-relief",
        "arad-ostraca",
        "temple-warning-inscription",
        "gallio-inscription",
    )
    with sqlite3.connect(path) as connection:
        placeholders = ", ".join("?" for _ in item_ids)
        connection.execute(
            f"DELETE FROM archaeology_scripture_links WHERE item_id IN ({placeholders})",
            item_ids,
        )
        connection.execute(
            f"DELETE FROM archaeology_items WHERE id IN ({placeholders})",
            item_ids,
        )
        connection.execute(
            "DELETE FROM archaeology_sites WHERE id IN (?, ?, ?, ?)",
            ("thebes", "karnak", "arad", "delphi"),
        )
        connection.execute("DELETE FROM schema_migrations WHERE version = 20")

    initialize_database(path)
    restored_ids = {item["id"] for item in list_archaeology_items(path=path)}
    assert set(item_ids).issubset(restored_ids)


def test_v21_backfills_reviewed_cross_period_media_for_existing_database(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    media_ids = (
        "wm-merneptah-stele",
        "wm-shoshenq-karnak-relief",
        "wm-arad-ostracon-18",
        "wm-temple-warning-inscription",
        "wm-gallio-inscription",
    )
    with sqlite3.connect(path) as connection:
        placeholders = ", ".join("?" for _ in media_ids)
        connection.execute(f"DELETE FROM archaeology_media WHERE id IN ({placeholders})", media_ids)
        connection.execute(
            "UPDATE archaeology_items SET notes = 'stale text-only note' WHERE id = ?",
            ("merneptah-stele",),
        )
        connection.execute("DELETE FROM schema_migrations WHERE version = 21")

    initialize_database(path)
    items = {item["id"]: item for item in list_archaeology_items(path=path)}
    restored_media_ids = {
        record["id"]
        for item in items.values()
        for record in item["media"]
    }
    assert set(media_ids).issubset(restored_media_ids)
    assert "text-only" not in items["merneptah-stele"]["notes"]


def test_v22_backfills_reviewed_taylor_prism_media_for_existing_database(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM archaeology_media WHERE id = ?",
            ("wm-sennacherib-taylor-prism",),
        )
        connection.execute(
            "UPDATE archaeology_items SET notes = 'stale text-only note' WHERE id = ?",
            ("sennacherib-prism",),
        )
        connection.execute("DELETE FROM schema_migrations WHERE version = 22")

    initialize_database(path)
    item = next(item for item in list_archaeology_items(path=path) if item["id"] == "sennacherib-prism")
    assert {record["id"] for record in item["media"]} == {"wm-sennacherib-taylor-prism"}
    assert item["media"][0]["rights_status"] == "public_domain"
    assert "text-only" not in item["notes"]


def test_v23_backfills_reviewed_pilate_stone_media_for_existing_database(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM archaeology_media WHERE id = ?", ("wm-pilate-stone",))
        connection.execute(
            "UPDATE archaeology_items SET notes = 'stale text-only note' WHERE id = ?",
            ("pilate-stone",),
        )
        connection.execute("DELETE FROM schema_migrations WHERE version = 23")

    initialize_database(path)
    item = next(item for item in list_archaeology_items(path=path) if item["id"] == "pilate-stone")
    assert {record["id"] for record in item["media"]} == {"wm-pilate-stone"}
    assert item["media"][0]["rights_status"] == "cc0"
    assert "text-only" not in item["notes"]


def test_v24_backfills_reviewed_hezekiahs_tunnel_media_for_existing_database(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM archaeology_media WHERE id = ?",
            ("wm-hezekiahs-tunnel-conduit",),
        )
        connection.execute(
            "UPDATE archaeology_items SET notes = 'stale text-only note' WHERE id = ?",
            ("hezekiahs-tunnel-item",),
        )
        connection.execute("DELETE FROM schema_migrations WHERE version = 24")

    initialize_database(path)
    item = next(
        item
        for item in list_archaeology_items(path=path)
        if item["id"] == "hezekiahs-tunnel-item"
    )
    assert {record["id"] for record in item["media"]} == {"wm-hezekiahs-tunnel-conduit"}
    assert item["media"][0]["rights_status"] == "cc_by_sa"
    assert "text-only" not in item["notes"]


def test_v25_backfills_reviewed_lachish_letter_media_for_existing_database(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM archaeology_media WHERE id = ?",
            ("wm-lachish-letter-israel-museum",),
        )
        connection.execute(
            "UPDATE archaeology_items SET notes = 'stale text-only note' WHERE id = ?",
            ("lachish-letters",),
        )
        connection.execute("DELETE FROM schema_migrations WHERE version = 25")

    initialize_database(path)
    item = next(item for item in list_archaeology_items(path=path) if item["id"] == "lachish-letters")
    assert {record["id"] for record in item["media"]} == {"wm-lachish-letter-israel-museum"}
    assert item["media"][0]["rights_status"] == "cc0"
    assert "text-only" not in item["notes"]


def test_v26_backfills_reviewed_ketef_hinnom_media_for_existing_database(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM archaeology_media WHERE id = ?",
            ("wm-ketef-hinnom-scrolls",),
        )
        connection.execute(
            "UPDATE archaeology_items SET notes = 'stale text-only note' WHERE id = ?",
            ("ketef-hinnom-scrolls",),
        )
        connection.execute("DELETE FROM schema_migrations WHERE version = 26")

    initialize_database(path)
    item = next(
        item for item in list_archaeology_items(path=path) if item["id"] == "ketef-hinnom-scrolls"
    )
    assert {record["id"] for record in item["media"]} == {"wm-ketef-hinnom-scrolls"}
    assert item["media"][0]["rights_status"] == "cc_by_sa"
    assert "text-only" not in item["notes"]


def test_v27_backfills_reviewed_broad_wall_media_for_existing_database(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM archaeology_media WHERE id = ?",
            ("wm-jerusalem-broad-wall",),
        )
        connection.execute(
            "UPDATE archaeology_items SET notes = 'stale text-only note' WHERE id = ?",
            ("broad-wall-jerusalem",),
        )
        connection.execute("DELETE FROM schema_migrations WHERE version = 27")

    initialize_database(path)
    item = next(
        item for item in list_archaeology_items(path=path) if item["id"] == "broad-wall-jerusalem"
    )
    assert {record["id"] for record in item["media"]} == {"wm-jerusalem-broad-wall"}
    assert item["media"][0]["rights_status"] == "cc_by"
    assert "text-only" not in item["notes"]


@pytest.mark.parametrize(
    ("version", "item_id", "media_id", "rights_status"),
    [
        (28, "dead-sea-scrolls", "wm-dead-sea-scrolls-before-unraveled", "public_domain"),
        (29, "hazor-excavations", "wm-tel-hazor-zone-m4", "cc0"),
        (30, "megiddo-excavations", "wm-tel-megiddo-excavation", "cc_by"),
        (31, "city-of-david-excavations", "wm-city-of-david-excavation-site", "cc_by_sa"),
        (33, "babylon-ishtar-gate-context", "wm-babylon-ishtar-gate-1932", "public_domain"),
    ],
)
def test_remaining_reviewed_media_backfills_for_existing_database(
    tmp_path, version, item_id, media_id, rights_status
) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)

    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM archaeology_media WHERE id = ?", (media_id,))
        connection.execute(
            "UPDATE archaeology_items SET notes = 'stale text-only note' WHERE id = ?",
            (item_id,),
        )
        connection.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))

    initialize_database(path)
    item = next(item for item in list_archaeology_items(path=path) if item["id"] == item_id)
    assert {record["id"] for record in item["media"]} == {media_id}
    assert item["media"][0]["rights_status"] == rights_status
    assert "text-only" not in item["notes"]
