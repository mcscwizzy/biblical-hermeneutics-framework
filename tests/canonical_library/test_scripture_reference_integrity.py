from __future__ import annotations

from types import SimpleNamespace

import pytest

from bhf_agent.presentation import build_evidence_bundle
from framework.canonical_library import CanonicalLibrary, SQLiteCanonicalLibrary, build_database
from framework.canonical_library.scripture import (
    build_book_alias_lookup,
    parse_scripture_reference,
    parse_scripture_references,
)

from .helpers import make_object, write_library


def _ref(reference: str, relationship: str = "primary") -> dict[str, str]:
    return {"reference": reference, "relationship": relationship, "notes": "fixture"}


def _fixture_library(tmp_path):
    objects = [
        make_object(
            "genesis-exact",
            "cultural_background",
            "Genesis exact",
            ["genesis exact"],
            scripture_references=[_ref("Genesis 13")],
            claims=[
                {
                    "id": "genesis-exact-claim",
                    "claim": "A claim anchored to Genesis 13.",
                    "claim_type": "historical_cultural",
                    "certainty": "strong_consensus",
                    "dispute_status": "not_disputed",
                    "scripture_references": ["Genesis 13"],
                    "source_ids": [],
                    "traditions": ["Academic"],
                    "rationale": "Fixture.",
                    "notes": "",
                }
            ],
        ),
        make_object(
            "genesis-verse",
            "cultural_background",
            "Genesis verse range",
            ["genesis verse"],
            scripture_references=[_ref("Genesis 13:5-12")],
        ),
        make_object(
            "genesis-spanning",
            "cultural_background",
            "Genesis spanning range",
            ["genesis spanning"],
            scripture_references=[_ref("Genesis 12:10-13:18")],
        ),
        make_object(
            "other-genesis-chapter",
            "cultural_background",
            "Other Genesis chapter",
            ["other genesis chapter"],
            scripture_references=[_ref("Genesis 31")],
        ),
        make_object(
            "same-chapter-other-book",
            "cultural_background",
            "Romans 13",
            ["same chapter other book"],
            scripture_references=[_ref("Romans 13")],
        ),
        make_object(
            "same-verse-other-book",
            "cultural_background",
            "Jude 1:13",
            ["same verse other book"],
            scripture_references=[_ref("Jude 1:13")],
        ),
        make_object(
            "unanchored-semantic",
            "cultural_background",
            "Unanchored semantic result",
            ["unanchored semantic"],
            summary="This is not passage evidence.",
        ),
    ]
    root = tmp_path / "ckl"
    write_library(root, objects)
    return CanonicalLibrary(root=root).load()


@pytest.fixture(scope="module")
def default_library():
    return CanonicalLibrary.load_default()


def test_compound_references_are_independent_spans() -> None:
    lookup = build_book_alias_lookup(())
    assert parse_scripture_reference("Genesis 12:3; 15:6", book_alias_lookup=lookup) is None
    spans = parse_scripture_references("Genesis 12:3; 15:6", book_alias_lookup=lookup)
    assert [(span.book, span.start_chapter, span.start_verse) for span in spans] == [
        ("Genesis", 12, 3),
        ("Genesis", 15, 6),
    ]


def test_chapter_ranges_are_not_parsed_as_chapter_verse_spans() -> None:
    lookup = build_book_alias_lookup(())
    spans = parse_scripture_references("1 Samuel 1-31", book_alias_lookup=lookup)
    assert [(span.book, span.start_chapter, span.start_verse, span.end_chapter, span.end_verse) for span in spans] == [
        ("1 Samuel", 1, None, 31, None)
    ]


def test_malformed_compound_reference_is_not_silently_accepted() -> None:
    lookup = build_book_alias_lookup(())
    assert parse_scripture_references("Genesis 12:3; not-a-reference", book_alias_lookup=lookup) == []
    assert parse_scripture_references("Genesis 12:3,15:6", book_alias_lookup=lookup) == []


def test_scripture_lookup_requires_book_and_overlapping_chapter(tmp_path) -> None:
    library = _fixture_library(tmp_path)
    ids = {result.object.id for result in library.retrieve_by_scripture_reference("Genesis 13", limit=20)}
    assert ids == {"genesis-exact", "genesis-verse", "genesis-spanning"}
    bundle = build_evidence_bundle(
        "Genesis 13",
        canonical_results=library.retrieve_by_scripture_reference("Genesis 13", limit=20),
    )
    assert "genesis-exact-claim" in {item.id for item in bundle.evidence_items}


def test_zero_anchored_chapter_returns_no_scripture_results(tmp_path) -> None:
    library = _fixture_library(tmp_path)
    assert library.retrieve_by_scripture_reference("Genesis 99", limit=20) == []


def test_scripture_aliases_and_cross_book_collisions(tmp_path) -> None:
    library = _fixture_library(tmp_path)
    abbreviated = {result.object.id for result in library.retrieve_by_scripture_reference("Gen 13", limit=20)}
    assert abbreviated == {"genesis-exact", "genesis-verse", "genesis-spanning"}
    assert not {
        result.object.id
        for result in library.retrieve_by_scripture_reference("Romans 13", limit=20)
    } & {"genesis-exact", "genesis-verse", "genesis-spanning"}
    assert not {
        result.object.id
        for result in library.retrieve_by_scripture_reference("Genesis 13:13", limit=20)
    } & {"same-chapter-other-book", "same-verse-other-book"}


def test_unanchored_semantic_result_is_excluded_from_commentary_bundle(tmp_path) -> None:
    library = _fixture_library(tmp_path)
    result = SimpleNamespace(object=library.objects_by_id["unanchored-semantic"], score=0.99)
    bundle = build_evidence_bundle("Genesis 13", canonical_results=[result])
    assert bundle.evidence_items == []


def test_explicitly_anchored_interpretive_note_reaches_bundle(tmp_path) -> None:
    library = _fixture_library(tmp_path)
    obj = make_object(
        "samuel-note-parent",
        "book",
        "1 Samuel",
        ["samuel note parent"],
        scripture_references=[_ref("1 Samuel 28")],
        sources=[
            {
                "id": "commentary-source",
                "title": "Commentary source",
                "author": "Author",
                "publisher": "Publisher",
                "year": 2020,
                "locator": "chapter",
                "url": "https://example.test/source",
                "source_type": "reference-work",
                "supports": ["interpretive_notes"],
                "notes": "Fixture source.",
            }
        ],
        interpretive_notes=[
            {
                "note": "The narrator calls the figure Samuel, while interpretations of the appearance remain disputed.",
                "note_type": "interpretive-caution",
                "certainty": "disputed",
                "dispute_status": "denominational_disagreement",
                "sources": ["commentary-source"],
                "scripture_references": ["1 Samuel 28:3-25"],
                "rationale": "The designation is textual; the ontology is disputed.",
            }
        ],
    )
    result = SimpleNamespace(object=library.objects_by_id["unanchored-semantic"], score=0.1)
    # The fixture object is intentionally added as a direct result so this
    # test isolates bundle projection from object retrieval.
    from framework.canonical_library.schema import CanonicalObject

    parent = CanonicalObject.from_mapping(obj)
    bundle = build_evidence_bundle(
        "1 Samuel 28",
        canonical_results=[SimpleNamespace(object=parent, score=0.9), result],
    )
    assert [item.id for item in bundle.evidence_items] == [
        "samuel-note-parent:interpretive_note:0"
    ]
    item = bundle.evidence_items[0]
    assert item.passage_anchors == ["1 Samuel 28:3-25"]
    assert item.confidence == "low"
    assert item.relevance_metadata["dispute_status"] == "denominational_disagreement"


def test_structured_claim_without_its_own_anchor_does_not_inherit_parent_cross_reference(tmp_path) -> None:
    objects = [
        make_object(
            "cross-book-parent",
            "book",
            "Jude",
            ["cross book parent"],
            scripture_references=[_ref("Jude 1:1-25"), _ref("Genesis 19:1-29", "background")],
            historical_context="This parent text is not a Genesis 19 claim.",
            claims=[
                {
                    "id": "unanchored-parent-claim",
                    "claim": "This claim belongs to the parent record, not Genesis 19.",
                    "claim_type": "reception_history",
                    "certainty": "strong_consensus",
                    "dispute_status": "historical_uncertainty",
                    "scripture_references": [],
                    "source_ids": [],
                    "traditions": ["Academic"],
                    "rationale": "Fixture.",
                    "notes": "",
                }
            ],
        )
    ]
    root = tmp_path / "ckl"
    write_library(root, objects)
    library = CanonicalLibrary(root=root).load()
    results = library.retrieve_by_scripture_reference("Genesis 19", limit=10)
    bundle = build_evidence_bundle("Genesis 19", canonical_results=results)
    assert results
    assert bundle.evidence_items == []


def test_claim_scripture_anchors_are_indexed_in_json_and_sqlite(tmp_path) -> None:
    objects = [
        make_object(
            "claim-only",
            "cultural_background",
            "Claim-only anchor",
            ["claim only"],
            claims=[
                {
                    "id": "claim-only-genesis-16",
                    "claim": "A claim whose only passage anchor is Genesis 16.",
                    "claim_type": "historical_cultural",
                    "certainty": "probable",
                    "dispute_status": "historical_uncertainty",
                    "scripture_references": ["Genesis 16"],
                    "source_ids": [],
                    "traditions": ["Academic"],
                    "rationale": "Fixture.",
                    "notes": "",
                }
            ],
        )
    ]
    root = tmp_path / "ckl"
    write_library(root, objects)
    json_library = CanonicalLibrary(root=root).load()
    database = tmp_path / "ckl.sqlite"
    build_database(root, database)
    sqlite_library = SQLiteCanonicalLibrary.from_path(database, root=root)
    try:
        assert json_library.retrieve_by_scripture_reference("Genesis 16", limit=10)[0].object.id == "claim-only"
        assert sqlite_library.retrieve_by_scripture_reference("Genesis 16", limit=10)[0].object.id == "claim-only"
        assert "claims" in sqlite_library.retrieve_by_scripture_reference("Genesis 16", limit=10)[0].matched_fields
    finally:
        sqlite_library.close()


def test_existing_genesis_one_to_ten_anchor_remains_retrievable(default_library) -> None:
    library = default_library
    results = library.retrieve_by_scripture_reference("Genesis 1", limit=100)
    assert results
    assert all(result.match_type == "scripture" for result in results)
    assert all(result.object.id != "galatians-abraham-promise-seed" for result in results)


def test_real_first_samuel_28_note_is_scoped_to_its_chapter(default_library) -> None:
    for reference in ("1 Samuel 27", "1 Samuel 28", "1 Samuel 29"):
        results = default_library.retrieve_by_scripture_reference(reference, limit=100)
        bundle = build_evidence_bundle(reference, canonical_results=results)
        note_ids = {
            item.id
            for item in bundle.evidence_items
            if item.relevance_metadata.get("source_kind") == "ckl_interpretive_note"
        }
        if reference == "1 Samuel 28":
            assert note_ids == {"1-samuel:interpretive_note:3"}
            assert bundle.evidence_items[0].passage_anchors == ["1 Samuel 28:3-25"]
        else:
            assert note_ids == set()


def test_interpretive_note_only_anchor_is_indexed_in_json_and_sqlite(tmp_path) -> None:
    objects = [
        make_object(
            "note-only",
            "cultural_background",
            "Note-only anchor",
            ["note only"],
            sources=[
                {
                    "id": "note-source",
                    "title": "Note source",
                    "author": "Author",
                    "publisher": "Publisher",
                    "year": 2020,
                    "locator": "chapter",
                    "url": "https://example.test/note-source",
                    "source_type": "reference-work",
                    "supports": ["interpretive_notes"],
                    "notes": "Fixture source.",
                }
            ],
            interpretive_notes=[
                {
                    "note": "A note whose only passage anchor is Genesis 16.",
                    "note_type": "interpretive-caution",
                    "certainty": "probable",
                    "dispute_status": "historical_uncertainty",
                    "sources": ["note-source"],
                    "scripture_references": ["Genesis 16"],
                    "rationale": "Fixture.",
                }
            ],
        )
    ]
    root = tmp_path / "ckl"
    write_library(root, objects)
    json_library = CanonicalLibrary(root=root).load()
    database = tmp_path / "ckl.sqlite"
    build_database(root, database)
    sqlite_library = SQLiteCanonicalLibrary.from_path(database, root=root)
    try:
        assert [result.object.id for result in json_library.retrieve_by_scripture_reference("Genesis 16", limit=10)] == ["note-only"]
        assert [result.object.id for result in sqlite_library.retrieve_by_scripture_reference("Genesis 16", limit=10)] == ["note-only"]
    finally:
        sqlite_library.close()


def test_json_and_sqlite_scripture_indexes_agree_for_adjacent_chapters(tmp_path) -> None:
    objects = [
        make_object(
            "samuel-book",
            "book",
            "1 Samuel",
            ["samuel book"],
            scripture_references=[_ref("1 Samuel 1-31")],
        ),
        make_object(
            "samuel-27-context",
            "cultural_background",
            "1 Samuel 27 context",
            ["samuel 27 context"],
            scripture_references=[_ref("1 Samuel 27")],
        ),
    ]
    root = tmp_path / "ckl"
    write_library(root, objects)
    json_library = CanonicalLibrary(root=root).load()
    database = tmp_path / "ckl.sqlite"
    build_database(root, database)
    sqlite_library = SQLiteCanonicalLibrary.from_path(database, root=root)
    try:
        for reference in ("1 Samuel 27", "1 Samuel 28", "1 Samuel 29"):
            json_ids = [
                result.object.id
                for result in json_library.retrieve_by_scripture_reference(reference, limit=20)
            ]
            sqlite_ids = [
                result.object.id
                for result in sqlite_library.retrieve_by_scripture_reference(reference, limit=20)
            ]
            assert sqlite_ids == json_ids
    finally:
        sqlite_library.close()


def test_real_genesis_contamination_cases_are_not_admitted(default_library) -> None:
    genesis_13 = default_library.retrieve_by_scripture_reference("Genesis 13", limit=100)
    assert "pauline-israel-jewish-gentile-relations-abraham-torah-circumcision-justification-faith-election-hardening-remnant-olive-tree-and-all-israel" not in {
        result.object.id for result in genesis_13
    }

    for reference, forbidden in (
        ("Genesis 19", "jude-reception"),
        ("Genesis 25", "malachi-love-edom"),
    ):
        results = default_library.retrieve_by_scripture_reference(reference, limit=100)
        bundle = build_evidence_bundle(
            reference,
            canonical_results=results,
        )
        assert forbidden not in {item.id for item in bundle.evidence_items}
