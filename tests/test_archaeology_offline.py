from __future__ import annotations

import pytest

from bhf_agent.study_db import create_archaeology_media, initialize_database

pytest.importorskip("fastapi")

from bhf_web.offline import build_offline_pack


def test_archaeology_offline_pack_excludes_unknown_rights(tmp_path) -> None:
    database = tmp_path / "study.sqlite"
    initialize_database(database)
    create_archaeology_media(
        {
            "id": "allowed-offline-media",
            "archaeology_item_id": "pilate-stone",
            "image_url": "https://example.org/allowed.jpg",
            "rights_status": "public_domain",
            "can_redistribute": True,
            "can_cache": True,
        },
        database,
    )
    create_archaeology_media(
        {
            "id": "remote-only-media",
            "archaeology_item_id": "pilate-stone",
            "image_url": "https://example.org/remote.jpg",
            "rights_status": "remote_display_only",
        },
        database,
    )

    pack = build_offline_pack("archaeology", study_db_path=database)

    assert {item["id"] for item in pack["media"]} == {"allowed-offline-media"}
