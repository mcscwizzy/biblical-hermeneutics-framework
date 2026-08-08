from __future__ import annotations

from bhf_agent.archaeology_resolver import resolve_archaeology_evidence
from bhf_agent.study_db import initialize_database


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
