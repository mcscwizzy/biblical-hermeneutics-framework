from __future__ import annotations

import pytest

from bhf_agent.archaeology import (
    ArchaeologyValidationError,
    media_can_bundle,
    validate_media_record,
)
from bhf_agent.study_db import create_archaeology_media, initialize_database, list_archaeology_media


def test_unknown_rights_fail_closed_without_losing_remote_metadata() -> None:
    with pytest.raises(ArchaeologyValidationError, match="cannot be marked"):
        validate_media_record(
            {
                "id": "media-unknown-invalid",
                "archaeology_item_id": "pilate-stone",
                "rights_status": "unknown",
                "can_redistribute": True,
                "can_cache": True,
            },
            archaeology_item_ids={"pilate-stone"},
        )

    record = validate_media_record(
        {
            "id": "media-unknown",
            "archaeology_item_id": "pilate-stone",
            "source_url": "https://example.org/source",
            "image_url": "https://example.org/image.jpg",
            "rights_status": "unknown",
        },
        archaeology_item_ids={"pilate-stone"},
    )

    assert record["can_redistribute"] is False
    assert record["can_cache"] is False
    assert not media_can_bundle(record)
    assert record["image_url"].startswith("https://")


def test_cc_by_requires_attribution_and_can_be_bundled() -> None:
    record = validate_media_record(
        {
            "id": "media-cc-by",
            "archaeology_site_id": "jerusalem",
            "rights_status": "cc_by",
            "creator": "Jane Smith",
            "institution": "BHF Test Archive",
            "license_id": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "can_redistribute": True,
            "can_cache": True,
        },
        archaeology_site_ids={"jerusalem"},
    )

    assert record["attribution_text"] == "Jane Smith\nBHF Test Archive\nCC BY 4.0"
    assert media_can_bundle(record)

    with pytest.raises(ArchaeologyValidationError, match="requires"):
        validate_media_record(
            {
                "id": "media-no-attribution",
                "archaeology_site_id": "jerusalem",
                "rights_status": "cc_by",
                "can_redistribute": True,
                "can_cache": True,
            },
            archaeology_site_ids={"jerusalem"},
        )


def test_media_must_reference_one_existing_archaeology_record() -> None:
    with pytest.raises(ArchaeologyValidationError, match="exactly one"):
        validate_media_record({"id": "media-missing-target", "rights_status": "public_domain"})

    with pytest.raises(ArchaeologyValidationError, match="missing archaeology item"):
        validate_media_record(
            {
                "id": "media-broken-target",
                "archaeology_item_id": "does-not-exist",
                "rights_status": "public_domain",
                "can_redistribute": True,
                "can_cache": True,
            },
            archaeology_item_ids={"pilate-stone"},
        )


def test_media_migration_and_item_serialization(tmp_path) -> None:
    path = tmp_path / "study.sqlite"
    initialize_database(path)
    created = create_archaeology_media(
        {
            "id": "pilate-stone-test-image",
            "archaeology_item_id": "pilate-stone",
            "media_type": "artifact-photo",
            "title": "Test artifact image",
            "source_url": "https://example.org/pilate",
            "image_url": "https://example.org/pilate.jpg",
            "rights_status": "public_domain",
            "can_redistribute": True,
            "can_cache": True,
        },
        path,
    )

    assert created["rights_status"] == "public_domain"
    assert created["can_cache"] is True
    assert list_archaeology_media(item_id="pilate-stone", path=path)[0]["id"] == created["id"]
