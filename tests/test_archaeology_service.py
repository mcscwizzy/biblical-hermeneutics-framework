from __future__ import annotations

from bhf_agent.archaeology_service import ArchaeologyService
from bhf_agent.archaeology_validation import validate_cross_domain_archaeology_relationships
from bhf_agent.ckl import load_canonical_library
from bhf_agent.study_db import initialize_database


def test_archaeology_service_browses_and_resolves_cross_domain_links(tmp_path) -> None:
    database = tmp_path / "study.sqlite"
    initialize_database(database)
    service = ArchaeologyService(database)

    records = service.search("Pilate", biblical_book="Matthew")
    assert [record["id"] for record in records] == ["pilate-stone"]
    compact_records = service.search(
        "Pilate",
        biblical_book="Matthew",
        include_media=False,
    )
    assert compact_records[0]["media"] == []
    assert compact_records[0]["primary_media"] is None
    detail = service.get_item("pilate-stone")
    assert any(link["ckl_object_id"] == "pontius-pilate" for link in detail["related_ckl"])
    assert any(record["id"] == "pilate-stone" for record in service.related_to_ckl("pontius-pilate"))


def test_cross_domain_archaeology_links_validate_against_ckl(tmp_path) -> None:
    database = tmp_path / "study.sqlite"
    initialize_database(database)
    validate_cross_domain_archaeology_relationships(
        load_canonical_library().objects_by_id.values(), path=database
    )
