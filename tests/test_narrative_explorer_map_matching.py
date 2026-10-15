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
