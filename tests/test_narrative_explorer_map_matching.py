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
