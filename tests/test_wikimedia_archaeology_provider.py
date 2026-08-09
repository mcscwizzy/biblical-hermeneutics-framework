from __future__ import annotations

import json

from bhf_agent.archaeology import media_can_bundle, validate_media_record
from bhf_agent.archaeology_import import MetOpenAccessProvider, WikimediaCommonsProvider


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_wikimedia_fetch_normalizes_reviewed_file_metadata() -> None:
    payload = {
        "query": {
            "pages": [
                {
                    "title": "File:Reviewed archaeology.jpg",
                    "imageinfo": [
                        {
                            "url": "https://upload.wikimedia.org/example.jpg",
                            "thumburl": "https://upload.wikimedia.org/thumb.jpg",
                            "width": 2400,
                            "height": 1600,
                            "mime": "image/jpeg",
                            "extmetadata": {
                                "Artist": {"value": "<b>Jane Archaeologist</b>"},
                                "Credit": {"value": "Example Museum"},
                                "ImageDescription": {"value": "<i>Reviewed artifact photograph</i>"},
                                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
                            },
                        }
                    ],
                }
            ]
        }
    }
    provider = WikimediaCommonsProvider(opener=lambda *args, **kwargs: _Response(payload))

    record = provider.normalize_record(provider.fetch_record("Reviewed archaeology.jpg"))

    assert record["source_record_id"] == "File:Reviewed archaeology.jpg"
    assert record["source_url"].endswith("File%3AReviewed_archaeology.jpg")
    assert record["image_url"] == "https://upload.wikimedia.org/example.jpg"
    assert record["thumbnail_url"] == "https://upload.wikimedia.org/thumb.jpg"
    assert record["creator"] == "Jane Archaeologist"
    assert record["institution"] == "Example Museum"
    assert record["rights_status"] == "cc_by_sa"
    assert record["can_redistribute"] is True
    assert "CC BY-SA 4.0" in record["attribution_text"]


def test_wikimedia_license_normalization_is_fail_closed_for_nonfree_metadata() -> None:
    provider = WikimediaCommonsProvider(opener=lambda *args, **kwargs: _Response({}))

    assert provider.normalize_license("CC0 1.0") == "cc0"
    assert provider.normalize_license("CC BY 4.0") == "cc_by"
    assert provider.normalize_license("CC BY-SA 4.0") == "cc_by_sa"
    assert provider.normalize_license("All rights reserved") == "unknown"

    record = provider.normalize_record({"id": "nonfree", "license_id": "All rights reserved"})
    assert record["rights_status"] == "unknown"
    assert record["can_redistribute"] is False
    assert record["can_cache"] is False
    assert not media_can_bundle(
        validate_media_record(
            {"id": "nonfree", "archaeology_item_id": "item", **record},
            archaeology_item_ids={"item"},
        )
    )


def test_wikimedia_search_returns_candidates_without_importing_them() -> None:
    payload = {"query": {"search": [{"title": "File:Potential match.jpg"}]}}
    provider = WikimediaCommonsProvider(opener=lambda *args, **kwargs: _Response(payload))

    assert provider.search("Potential match") == [
        {
            "external_id": "File:Potential match.jpg",
            "title": "File:Potential match.jpg",
            "source_url": "https://commons.wikimedia.org/wiki/File%3APotential_match.jpg",
        }
    ]


def test_met_open_access_provider_normalizes_only_public_domain_objects() -> None:
    payload = {
        "objectID": 324434,
        "isPublicDomain": True,
        "primaryImage": "https://images.metmuseum.org/original.jpg",
        "primaryImageSmall": "https://images.metmuseum.org/small.jpg",
        "title": "Battle scene of Assyrians storming a citadel",
        "objectDate": "ca. 704–681 BCE",
        "culture": "Assyrian",
        "medium": "Gypsum alabaster",
        "repository": "Metropolitan Museum of Art, New York, NY",
        "accessionNumber": "55.121.4a, b",
        "objectURL": "https://www.metmuseum.org/art/collection/search/324434",
    }
    provider = MetOpenAccessProvider(opener=lambda *args, **kwargs: _Response(payload))

    record = provider.normalize_record(provider.fetch_record("324434"))

    assert record["source_record_id"] == "324434"
    assert record["rights_status"] == "public_domain"
    assert record["can_redistribute"] is True
    assert record["thumbnail_url"] == "https://images.metmuseum.org/small.jpg"
    assert "Metropolitan Museum" in record["attribution_text"]


def test_met_open_access_provider_rejects_non_public_or_imageless_objects() -> None:
    for payload in (
        {"objectID": 1, "isPublicDomain": False, "primaryImage": "https://example.org/image.jpg"},
        {"objectID": 1, "isPublicDomain": True, "primaryImage": ""},
    ):
        provider = MetOpenAccessProvider(opener=lambda *args, **kwargs: _Response(payload))
        try:
            provider.fetch_record("1")
        except ValueError:
            pass
        else:
            raise AssertionError("ineligible Met record should not be importable")
