from __future__ import annotations

import pytest

# Load the agent package before map_service to respect its existing import order.
import bhf_agent as _bhf_agent  # noqa: F401

import bhf_web.map_service as map_service
from bhf_web.services import map_matching


@pytest.mark.parametrize(
    ("term", "passage_text", "expected"),
    (
        ("Eden", "The garden of Eden was planted.", True),
        ("Dan", "They went to Dan before sunrise.", True),
        ("Dan", "They went to Dana before sunrise.", False),
        ("Ur of the Chaldeans", "Abram left Ur of the Chaldeans.", True),
        ("Cana", "They traveled through Canaan.", False),
        ("and", "The land and the sea.", False),
        ("", "A passage with no candidate term.", False),
        ("Beth-lehem", "They came to Beth—lehem.", True),
    ),
)
def test_passage_text_matcher_preserves_normalized_whole_term_matching(
    term: str,
    passage_text: str,
    expected: bool,
) -> None:
    matcher_type = getattr(map_matching, "PassageTextMatcher", None)
    assert matcher_type is not None, "a request-scoped passage matcher is required"

    existing_match = map_matching.term_in_text(
        term,
        map_matching.normalize_for_match(passage_text),
    )
    assert existing_match is expected
    matcher = matcher_type(passage_text)
    assert matcher.contains(term) is existing_match


def test_passage_text_matcher_cache_is_bounded_and_request_local() -> None:
    matcher_type = getattr(map_matching, "PassageTextMatcher", None)
    assert matcher_type is not None, "a request-scoped passage matcher is required"

    first = matcher_type("A short passage.")
    second = matcher_type("A short passage.")
    for index in range(matcher_type.MAX_CACHED_TERMS + 16):
        first.contains(f"Candidate {index}")

    assert len(first._term_cache) <= matcher_type.MAX_CACHED_TERMS
    assert first._term_cache is not second._term_cache
    assert first.matches_source("A short passage.")
    assert not first.matches_source("A short passage")


def test_map_resolver_preserves_duplicate_unanchored_names_and_aliases(monkeypatch) -> None:
    places = [
        {"id": "zion-a", "name": "Zion", "aliases": ["Holy City"]},
        {"id": "zion-b", "name": "Zion", "aliases": []},
    ]
    monkeypatch.setattr(map_service, "list_biblical_places", lambda **_kwargs: places)
    monkeypatch.setattr(
        map_service,
        "_place_to_marker",
        lambda place, *_args, **_kwargs: {"id": place["id"], "name": place["name"]},
    )
    matcher_type = getattr(map_matching, "PassageTextMatcher", None)
    assert matcher_type is not None, "a request-scoped passage matcher is required"
    passage_text = "Zion and the Holy City"

    without_shared_matcher = map_service.resolve_places_for_passage(
        passage_text=passage_text,
        include_related_passages=False,
    )
    with_shared_matcher = map_service.resolve_places_for_passage(
        passage_text=passage_text,
        include_related_passages=False,
        passage_matcher=matcher_type(passage_text),
    )

    assert with_shared_matcher == without_shared_matcher
    assert without_shared_matcher["matched_place_ids"] == ["zion-a", "zion-b"]
    assert without_shared_matcher["matched_terms"] == {
        "zion-a": ["Zion", "Holy City"],
        "zion-b": ["Zion"],
    }


def test_compact_passage_resolution_preserves_marker_contract_and_omits_only_expansion(monkeypatch) -> None:
    place = {
        "id": "zion-a",
        "name": "Zion",
        "aliases": ["Holy City"],
        "latitude": 31.78,
        "longitude": 35.23,
        "ancient_region": "Judea",
        "confidence": "possible",
        "related_references": [{
            "id": "zion-ref-1",
            "book": "John",
            "chapter": 2,
            "verse_start": 13,
            "verse_end": 22,
            "relationship_type": "directly_named",
        }],
    }

    def marker(place_record, *_args, include_related_passages=True, **_kwargs):
        result = {
            "id": place_record["id"],
            "name": place_record["name"],
            "aliases": place_record["aliases"],
            "latitude": place_record["latitude"],
            "longitude": place_record["longitude"],
            "ancient_region": place_record["ancient_region"],
            "confidence": place_record["confidence"],
            "related_references": place_record["related_references"],
            "reference_count": len(place_record["related_references"]),
        }
        if include_related_passages:
            result["related_passages"] = {"place_id": place_record["id"], "groups": [{"count": 1}]}
        return result

    monkeypatch.setattr(map_service, "list_biblical_places", lambda **_kwargs: [place])
    monkeypatch.setattr(map_service, "_place_to_marker", marker)

    complete = map_service.resolve_places_for_passage(passage_text="Zion appears here.")
    compact = map_service.resolve_places_for_passage(
        passage_text="Zion appears here.",
        include_related_passages=False,
    )

    assert complete["matched_place_ids"] == compact["matched_place_ids"] == ["zion-a"]
    assert complete["matched_terms"] == compact["matched_terms"] == {"zion-a": ["Zion"]}
    assert complete["markers"][0]["related_passages"]["place_id"] == "zion-a"
    assert "related_passages" not in compact["markers"][0]
    assert {key: value for key, value in complete["markers"][0].items() if key != "related_passages"} == compact["markers"][0]


def test_narrative_opt_in_place_resolution_adds_explicit_links_to_text_matches(monkeypatch) -> None:
    places = [
        {"id": "text-jericho", "name": "Jericho", "aliases": []},
        {"id": "anchor-nile", "name": "Nile", "aliases": []},
    ]
    monkeypatch.setattr(map_service, "list_biblical_places", lambda **_kwargs: places)
    monkeypatch.setattr(
        map_service,
        "_place_to_marker",
        lambda place, *_args, **_kwargs: {"id": place["id"], "name": place["name"]},
    )
    monkeypatch.setattr(
        map_service,
        "_resolve_from_reference",
        lambda **_kwargs: (
            [places[0], places[1], places[1]],
            {"text-jericho": ["Jericho"], "anchor-nile": ["Nile"]},
        ),
    )

    legacy_result = map_service.resolve_places_for_passage(
        book="Acts", chapter=7, verse_start=18, verse_end=20, passage_text="They came to Jericho."
    )
    explorer_result = map_service.resolve_places_for_passage(
        book="Acts",
        chapter=7,
        verse_start=18,
        verse_end=20,
        passage_text="They came to Jericho.",
        include_reference_matches=True,
    )

    assert legacy_result["matched_place_ids"] == ["text-jericho"]
    assert explorer_result["matched_place_ids"] == ["text-jericho", "anchor-nile"]
    assert explorer_result["matched_terms"] == {"text-jericho": ["Jericho"], "anchor-nile": ["Nile"]}
    assert [marker["id"] for marker in explorer_result["markers"]] == ["text-jericho", "anchor-nile"]


def test_acts7_nile_reference_survives_text_first_match_suppression(monkeypatch) -> None:
    jericho = {"id": "text-jericho", "name": "Jericho", "aliases": []}
    nile = {
        "id": "openbible-a012705",
        "name": "Nile",
        "aliases": [],
        "related_references": [
            {
                "id": "openbible-ref-openbible-a012705-45",
                "book": "Acts",
                "chapter": 7,
                "verse_start": 19,
                "verse_end": 19,
                "relationship_type": "directly_named",
                "notes": "Imported from OpenBible.info Bible Geocoding Data.",
            }
        ],
    }
    monkeypatch.setattr(map_service, "list_biblical_places", lambda **_kwargs: [jericho, nile])
    monkeypatch.setattr(
        map_service,
        "_place_to_marker",
        lambda place, *_args, **_kwargs: place,
    )
    monkeypatch.setattr(
        map_service,
        "_resolve_from_reference",
        lambda **_kwargs: ([nile], {"openbible-a012705": ["Nile"]}),
    )
    arguments = {
        "book": "Acts",
        "chapter": 7,
        "verse_start": None,
        "verse_end": None,
        "passage_text": "Jericho appears in this passage, but the river name does not.",
    }

    legacy_result = map_service.resolve_places_for_passage(**arguments)
    explorer_result = map_service.resolve_places_for_passage(
        **arguments,
        include_reference_matches=True,
    )

    assert legacy_result["matched_place_ids"] == ["text-jericho"]
    assert "openbible-a012705" not in legacy_result["matched_place_ids"]
    assert explorer_result["matched_place_ids"] == ["text-jericho", "openbible-a012705"]
    retrieved_nile = explorer_result["markers"][1]
    assert retrieved_nile["related_references"][0]["id"] == "openbible-ref-openbible-a012705-45"
    assert retrieved_nile["related_references"][0]["relationship_type"] == "directly_named"


def test_narrative_opt_in_route_resolution_adds_explicit_links_to_text_matches(monkeypatch) -> None:
    routes = [
        {"id": "text-route", "name": "Jericho route", "description": "", "period": ""},
        {"id": "anchor-route", "name": "Nile route", "description": "", "period": ""},
    ]
    monkeypatch.setattr(map_service, "list_map_routes", lambda **_kwargs: routes)
    monkeypatch.setattr(
        map_service,
        "_route_to_item",
        lambda route, *_args, **_kwargs: {"id": route["id"], "name": route["name"]},
    )
    monkeypatch.setattr(
        map_service,
        "_resolve_routes_from_reference",
        lambda **_kwargs: ([routes[1]], {"anchor-route": ["Nile route"]}),
    )

    explorer_result = map_service.get_map_routes_for_passage(
        book="Acts",
        chapter=7,
        verse_start=18,
        verse_end=20,
        passage_text="They came to the Jericho route.",
        include_reference_matches=True,
    )

    assert explorer_result["matched_route_ids"] == ["text-route", "anchor-route"]
    assert [route["id"] for route in explorer_result["routes"]] == ["text-route", "anchor-route"]


def test_map_marker_catalog_batches_place_references_without_changing_markers(monkeypatch, tmp_path) -> None:
    places = [
        {
            "id": "place-a", "name": "Place A", "latitude": 31.0, "longitude": 35.0,
            "ancient_region": "Judea", "description": "A place", "periods": [],
            "aliases": [], "modern_location": "", "confidence": "possible",
            "confidence_rank": 1, "source_id": "source-a", "source": None,
            "source_name": "Catalog", "source_url": "", "license": "", "notes": "",
        },
        {
            "id": "place-b", "name": "Place B", "latitude": None, "longitude": None,
            "ancient_region": "Galilee", "description": "Another place", "periods": [],
            "aliases": [], "modern_location": "", "confidence": "uncertain",
            "confidence_rank": 0, "source_id": "source-b", "source": None,
            "source_name": "Catalog", "source_url": "", "license": "", "notes": "",
        },
    ]
    references = [
        {"id": "ref-a", "place_id": "place-a", "book": "John", "chapter": 2,
         "verse_start": 1, "verse_end": 11, "relationship_type": "directly_named", "notes": ""},
        {"id": "ref-b", "place_id": "place-b", "book": "John", "chapter": 2,
         "verse_start": 12, "verse_end": 17, "relationship_type": "contextual", "notes": ""},
    ]
    requested_ids = []

    monkeypatch.setattr(
        map_service,
        "list_biblical_places",
        lambda **_kwargs: places,
    )

    def load_references(place_id=None, **_kwargs):
        requested_ids.append(place_id)
        if place_id is None:
            return references
        return [reference for reference in references if reference["place_id"] == place_id]

    monkeypatch.setattr(map_service, "list_place_references", load_references)

    markers = map_service.get_biblical_place_markers(path=tmp_path / "study.sqlite")

    assert requested_ids == [None]
    assert [marker["id"] for marker in markers] == ["place-a", "place-b"]
    assert [marker["related_references"] for marker in markers] == [
        [references[0]],
        [references[1]],
    ]
    assert [marker["reference_count"] for marker in markers] == [1, 1]
    assert markers[0]["has_coordinates"] is True
    assert markers[1]["has_coordinates"] is False
