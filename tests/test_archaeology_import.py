from __future__ import annotations

import json

from bhf_agent.archaeology_import import FixtureArchaeologyMediaProvider, import_archaeology_manifest
from bhf_agent.study_db import initialize_database, list_archaeology_media


def test_fixture_import_is_manifest_driven_and_uses_normalized_license(tmp_path) -> None:
    database = tmp_path / "study.sqlite"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "records": {
                    "fixture-pilate": {
                        "image_url": "https://example.org/pilate.jpg",
                        "creator": "Fixture Photographer",
                        "license_id": "CC BY 4.0",
                        "license_url": "https://creativecommons.org/licenses/by/4.0/",
                        "can_redistribute": True,
                        "can_cache": True,
                    }
                },
                "entries": [
                    {
                        "external_id": "fixture-pilate",
                        "id": "fixture-pilate-media",
                        "archaeology_item_id": "pilate-stone",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    initialize_database(database)

    imported = import_archaeology_manifest(
        manifest,
        provider=FixtureArchaeologyMediaProvider(
            json.loads(manifest.read_text(encoding="utf-8"))["records"]
        ),
        database_path=database,
    )

    assert imported[0]["id"] == "fixture-pilate-media"
    assert list_archaeology_media(item_id="pilate-stone", path=database)[0]["rights_status"] == "cc_by"
