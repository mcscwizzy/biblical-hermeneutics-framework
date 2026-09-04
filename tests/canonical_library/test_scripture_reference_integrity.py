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


def test_malformed_compound_reference_is_not_silently_accepted() -> None:
    lookup = build_book_alias_lookup(())
    assert parse_scripture_references("Genesis 12:3; not-a-reference", book_alias_lookup=lookup) == []
    assert parse_scripture_references("Genesis 12:3,15:6", book_alias_lookup=lookup) == []


def test_scripture_lookup_requires_book_and_overlapping_chapter(tmp_path) -> None:
    library = _fixture_library(tmp_path)
    ids = {result.object.id for result in library.retrieve_by_scripture_reference("Genesis 13", limit=20)}
    assert ids == {"genesis-exact", "genesis-verse", "genesis-spanning"}


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
