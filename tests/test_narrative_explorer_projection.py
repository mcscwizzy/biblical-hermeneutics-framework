"""Contract tests for the read-only Narrative Explorer projection."""

from copy import deepcopy
from importlib import import_module
from importlib.util import find_spec
import json
from pathlib import Path

import pytest


def test_projection_adapter_module_is_available():
    assert find_spec("bhf_agent.presentation.narrative_explorer") is not None


def _public(name):
    module = import_module("bhf_agent.presentation.narrative_explorer")
    value = getattr(module, name, None)
    assert value is not None, f"public adapter contract {name!r} is missing"
    return value


def _lookup(
    domain,
    *,
    records=(),
    query_status="complete",
    reason_code=None,
    missing_subdomains=(),
):
    domain_lookup = _public("DomainLookup")
    return domain_lookup(
        domain=domain,
        records=records,
        query_status=query_status,
        reason_code=reason_code,
        missing_subdomains=missing_subdomains,
    )


def _project(reference, *, canonical=None, maps=None, archaeology=None):
    project = _public("project_narrative_explorer")
    return project(
        reference,
        canonical_lookup=canonical or _lookup("ckl"),
        map_lookup=maps,
        archaeology_lookup=archaeology,
    ).to_dict()


_OBJECT_ROOT = Path(__file__).resolve().parents[1] / "framework" / "canonical_library" / "objects"


def _load_ckl(*object_paths):
    return [
        json.loads((_OBJECT_ROOT / object_path).read_text(encoding="utf-8"))
        for object_path in object_paths
    ]


def _item(result, stable_id):
    return next(item for item in result["items"] if item["id"] == stable_id)


def _map_place(
    item_id,
    name,
    reference,
    *,
    latitude=31.0,
    longitude=35.0,
    **overrides,
):
    record = {
        "id": item_id,
        "name": name,
        "marker_kind": "place",
        "description": f"Map evidence for {name}.",
        "latitude": latitude,
        "longitude": longitude,
        "confidence": "high",
        "source_id": "map-source",
        "source": {"id": "map-source", "label": "Curated map source", "url": "https://example.test/map"},
        "related_references": [
            {
                "book": reference.split()[0],
                "chapter": int(reference.split()[1].split(":")[0]),
                "verse_start": int(reference.split(":")[1].split("-")[0]),
                "verse_end": int(reference.split(":")[1].split("-")[-1]),
                "relationship_type": "direct",
                "notes": "Authored map passage link.",
            }
        ],
    }
    record.update(overrides)
    return record


def test_projection_normalizes_chapter_and_verse_range_and_exposes_v1_envelope():
    result = _project(
        "Gen 6",
        maps=_lookup("maps", query_status="failed", reason_code="resolver_unavailable"),
        archaeology=_lookup("archaeology"),
    )

    assert set(result) == {
        "schema_version",
        "passage",
        "coverage",
        "sections",
        "items",
        "connections",
        "navigation",
    }
    assert result["schema_version"] == "1.0"
    assert result["passage"] == {
        "reference": "Genesis 6",
        "book": "Genesis",
        "chapter": 6,
        "verse_start": None,
        "verse_end": None,
        "scope": "chapter",
    }
    coverage = {item["domain"]: item for item in result["coverage"]}
    assert coverage["ckl"]["source_domain"] == "canonical_knowledge_library"
    assert coverage["ckl"]["state"] == "not_represented"
    assert coverage["maps"]["state"] == "unknown"
    assert coverage["maps"]["reason_code"] == "resolver_unavailable"
    assert coverage["archaeology"]["state"] == "not_represented"
    assert {
        "id": "navigation:passage:Genesis 6",
        "kind": "passage",
        "target_id": "Genesis 6",
        "href": "/api/study/companion-context?book=Genesis&chapter=6",
    } in result["navigation"]

    verse_result = _project("Genesis 6:1-4")
    assert verse_result["passage"] == {
        "reference": "Genesis 6:1-4",
        "book": "Genesis",
        "chapter": 6,
        "verse_start": 1,
        "verse_end": 4,
        "scope": "verse_range",
    }
    passage_navigation = next(item for item in verse_result["navigation"] if item["kind"] == "passage")
    assert passage_navigation["href"] == (
        "/api/study/companion-context?book=Genesis&chapter=6&verse_start=1&verse_end=4"
    )


@pytest.mark.parametrize("reference", ["", "Genesis", "Genesis 6:0", "Genesis 1-2"])
def test_projection_rejects_invalid_or_unsupported_passage_scope(reference):
    with pytest.raises(ValueError):
        _project(reference)


def test_projection_is_stable_and_does_not_mutate_supplied_records():
    records = [
        {
            "id": "book-fixture",
            "type": "book",
            "title": "Genesis",
            "scripture_references": [{"reference": "Genesis 6:1-22", "relationship": "primary"}],
            "sources": [{"id": "genesis-source", "title": "Genesis", "year": None}],
            "private_notes": ["must not cross the projection boundary"],
        }
    ]
    before = deepcopy(records)
    lookup = _lookup("ckl", records=records)

    first = _project("Genesis 6", canonical=lookup)
    second = _project("Genesis 6", canonical=lookup)

    assert first == second
    assert records == before


def test_unsupplied_lookup_is_unknown_not_a_completed_empty_query():
    result = _project("Genesis 6")
    maps = next(entry for entry in result["coverage"] if entry["domain"] == "maps")
    archaeology = next(entry for entry in result["coverage"] if entry["domain"] == "archaeology")

    assert maps["query_status"] == archaeology["query_status"] == "not_run"
    assert maps["state"] == archaeology["state"] == "unknown"
    assert maps["query_returned_count"] is None
    assert maps["reason_code"] == "lookup_not_supplied"
    assert "passage_maps" in maps["description"]


def test_partial_lookup_and_empty_partial_lookup_keep_distinct_coverage_states():
    partial_item = _map_place("midian", "Midian", "Exodus 3:1-2")
    with_records = _project(
        "Exodus 3",
        maps=_lookup(
            "maps",
            records=[partial_item],
            query_status="partial",
            reason_code="routes_unavailable",
            missing_subdomains=["routes"],
        ),
    )
    maps_with_records = next(entry for entry in with_records["coverage"] if entry["domain"] == "maps")
    geography_section = next(section for section in with_records["sections"] if section["id"] == "biblical_geography")
    assert maps_with_records["state"] == "partial"
    assert maps_with_records["missing_subdomains"] == ["routes"]
    assert maps_with_records["reason_code"] == "routes_unavailable"
    assert "passage_maps" in maps_with_records["description"]
    assert geography_section["state"] == "partial"

    empty_partial = _project(
        "Exodus 3",
        maps=_lookup("maps", query_status="partial", missing_subdomains=["places"]),
    )
    maps_without_records = next(entry for entry in empty_partial["coverage"] if entry["domain"] == "maps")
    assert maps_without_records["state"] == "unknown"
    assert maps_without_records["query_returned_count"] == 0


def test_genesis_2_eden_coordinates_are_preserved_as_unverified_not_displayable():
    eden = _map_place("eden", "Garden of Eden", "Genesis 2:10-14")
    eden.pop("source")
    eden["source_name"] = "Existing BHF map catalog"
    eden["source_url"] = "https://example.test/map-catalog"
    eden["related_references"].append(
        {
            "book": "Genesis",
            "chapter": 3,
            "verse_start": 8,
            "verse_end": 8,
            "relationship_type": "contextual",
        }
    )
    original = deepcopy(eden)
    result = _project("Genesis 2", maps=_lookup("maps", records=[eden]))

    item = _item(result, "maps:eden")
    assert item["geography_kind"] == "physical_place"
    assert item["place_identification_confidence"] == "unknown"
    assert item["stored_coordinates"] == {"latitude": 31.0, "longitude": 35.0}
    assert item["coordinates_displayable"] is False
    assert item["coordinate_display_reason"] == "physical_identification_not_established"
    assert item["source_ids"] == ["map-source"]
    assert item["sources"][0]["id"] == "map-source"
    assert item["sources"][0]["details_available"] is True
    assert item["sources"][0]["bibliographic_details"]["source_name"] == "Existing BHF map catalog"
    assert item["parent_object_id"] is None
    assert item["applicable_passage_anchors"][0]["reference"] == "Genesis 2:10-14"
    assert eden == original

    genesis_three = _project("Genesis 3", maps=_lookup("maps", records=[eden]))
    garden_scene = _item(genesis_three, "maps:eden")
    assert garden_scene["applicable_passage_anchors"][0]["reference"] == "Genesis 3:8"
    assert garden_scene["coordinates_displayable"] is False


def test_external_items_require_their_own_overlapping_verse_anchor():
    eden = _map_place("eden", "Garden of Eden", "Genesis 2:10-14")
    result = _project(
        "Genesis 2:8-9",
        maps=_lookup("maps", records=[eden]),
    )
    assert not any(item["id"] == "maps:eden" for item in result["items"])
    assert next(entry for entry in result["coverage"] if entry["domain"] == "maps")["state"] == "not_represented"


def test_malformed_external_scripture_references_do_not_create_passage_anchors():
    from bhf_agent.presentation.narrative_explorer import _external_anchor_entries

    record = {
        "id": "malformed-map-reference",
        "scripture_references": ["Genesis chapter one"],
        "related_references": [{"book": "Genesis", "chapter": "one", "verse_start": 1}],
    }

    assert _external_anchor_entries(record, "maps") == []


def test_map_navigation_marks_collection_or_kml_destinations_for_client_side_selection():
    route = {
        "id": "wilderness-route",
        "name": "Wilderness route",
        "marker_kind": "route",
        "scripture_links": [
            {
                "book": "Exodus",
                "chapter": 3,
                "verse_start": 1,
                "verse_end": 4,
                "relationship_type": "contextual",
            }
        ],
    }
    result = _project(
        "Exodus 3",
        maps=_lookup("maps", records=[_map_place("midian", "Midian", "Exodus 3:1-2"), route]),
    )

    destinations = {entry["target_id"]: entry for entry in result["navigation"]}
    assert destinations["midian"]["href"] == "/api/maps/biblical-places"
    assert destinations["midian"]["selection_required"] is True
    assert destinations["wilderness-route"]["href"] == "/api/maps/routes/wilderness-route.kml"
    assert destinations["wilderness-route"]["selection_required"] is True


def test_exodus_3_physical_map_items_retain_uncertain_horeb_identification():
    midian = _map_place(
        "midian",
        "Midian",
        "Exodus 3:1-2",
        physical_identification_status="established",
        place_identification_confidence="high",
    )
    horeb = _map_place(
        "horeb-sinai",
        "Horeb / Sinai identification",
        "Exodus 3:1-6",
        place_identification_status="disputed",
        place_identification_confidence="disputed",
        dispute_status="identification_uncertainty",
    )
    canonical_records = _load_ckl(
        "places/midian.json",
        "places/mount-sinai.json",
        "theology/divine-presence.json",
    )
    result = _project(
        "Exodus 3",
        canonical=_lookup("ckl", records=canonical_records),
        maps=_lookup("maps", records=[midian, horeb]),
    )

    physical = _item(result, "maps:midian")
    uncertain = _item(result, "maps:horeb-sinai")
    textual_place = _item(result, "ckl:midian")
    presence = _item(result, "ckl:divine-presence")
    assert physical["geography_kind"] == "physical_place"
    assert physical["place_identification_confidence"] == "high"
    assert physical["coordinates_displayable"] is True
    assert uncertain["geography_kind"] == "physical_place"
    assert uncertain["place_identification_confidence"] == "disputed"
    assert uncertain["dispute_status"] == "identification_uncertainty"
    assert uncertain["coordinates_displayable"] is False
    assert textual_place["object_type"] == "place"
    assert textual_place["applicable_passage_anchors"][0]["reference"] == "Exodus 3:1-15"
    assert presence["object_type"] == "theology"
    assert presence["geography_kind"] == "unknown"
    assert presence["stored_coordinates"] is None
    assert "themes_biblical_connections" in presence["section_ids"]


def test_sacred_space_never_projects_coordinates_as_physical_geometry():
    sacred_space = _map_place(
        "eden-sacred-space",
        "Eden sacred-space concept",
        "Genesis 2:8-10",
        geography_kind="sacred_space",
    )
    result = _project("Genesis 2", maps=_lookup("maps", records=[sacred_space]))
    item = _item(result, "maps:eden-sacred-space")

    assert item["geography_kind"] == "sacred_space"
    assert item["coordinates_displayable"] is False
    assert item["coordinate_display_reason"] == "conceptual_geography_has_no_physical_marker"
    assert item["stored_coordinates"] == {"latitude": 31.0, "longitude": 35.0}
    assert item["section_ids"] == [
        "biblical_geography",
        "divine_council_cosmic_geography",
    ]
    cosmic = next(
        section
        for section in result["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    assert cosmic["source_domains"] == [
        "canonical_knowledge_library",
        "passage_maps",
    ]
    assert cosmic["item_ids"].count(item["id"]) == 1
    assert sum(candidate["id"] == item["id"] for candidate in result["items"]) == 1


def test_route_geometry_requires_an_established_physical_identification():
    route = {
        "id": "wilderness-route",
        "name": "Wilderness route concept",
        "marker_kind": "route",
        "route_type": "narrative route",
        "geojson": {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[35.0, 31.0], [36.0, 32.0]]},
        },
        "scripture_links": [
            {
                "book": "Exodus",
                "chapter": 3,
                "verse_start": 1,
                "verse_end": 4,
                "relationship_type": "contextual",
            }
        ],
    }
    result = _project("Exodus 3", maps=_lookup("maps", records=[route]))
    item = _item(result, "maps:wilderness-route")

    assert item["geography_kind"] == "route"
    assert item["stored_geometry"]["coordinates"] == [[35.0, 31.0], [36.0, 32.0]]
    assert item["geometry_displayable"] is False
    assert item["geometry_display_reason"] == "geographic_identification_not_established"


def test_verified_route_geometry_can_be_displayable_when_source_identification_is_established():
    route = {
        "id": "verified-route-fixture",
        "name": "Verified route test fixture",
        "marker_kind": "route",
        "route_identification_status": "verified",
        "dispute_status": "not_disputed",
        "geojson": {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[35.0, 31.0], [36.0, 32.0]]},
        },
        "scripture_links": [
            {
                "book": "Exodus",
                "chapter": 3,
                "verse_start": 1,
                "verse_end": 4,
                "relationship_type": "direct",
            }
        ],
    }
    result = _project("Exodus 3", maps=_lookup("maps", records=[route]))
    item = _item(result, "maps:verified-route-fixture")

    assert item["geography_kind"] == "route"
    assert item["stored_geometry"]["coordinates"] == [[35.0, 31.0], [36.0, 32.0]]
    assert item["geometry_displayable"] is True
    assert item["geometry_display_reason"] is None


def test_archaeology_projection_preserves_explicit_source_and_uncertainty():
    record = {
        "id": "exodus-inscription",
        "title": "Inscription with a stated historical connection",
        "item_type": "inscription",
        "site_id": "tell-example",
        "site_name": "Tell Example",
        "summary": "An authored archaeological summary.",
        "confidence": "low",
        "dispute_status": "disputed_identification",
        "source_id": "archaeology-source",
        "source": {"id": "archaeology-source", "title": "Catalog entry", "year": None},
        "scripture_links": [
            {
                "book": "Exodus",
                "chapter": 3,
                "verse_start": 1,
                "verse_end": 5,
                "relationship_type": "historical_context",
                "notes": "Catalogued as historical context.",
            }
        ],
    }
    result = _project("Exodus 3:1-3", archaeology=_lookup("archaeology", records=[record]))

    item = _item(result, "archaeology:exodus-inscription")
    assert item["record_kind"] == "archaeology_item"
    assert item["evidence_category"] == "inscription"
    assert item["parent_object_id"] == "tell-example"
    assert item["claim_text"] == "An authored archaeological summary."
    assert item["confidence"] == "low"
    assert item["dispute_status"] == "disputed_identification"
    assert item["sources"][0]["id"] == "archaeology-source"
    assert item["sources"][0]["details_available"] is True
    assert item["applicable_passage_anchors"][0]["reference"] == "Exodus 3:1-5"
    archaeology_edge = next(
        edge for edge in result["connections"] if edge["source_id"] == "archaeology:exodus-inscription"
    )
    assert archaeology_edge["original_relationship_type"] == "historical_context"
    assert archaeology_edge["relationship_mode"] == "direct"
    assert archaeology_edge["connection_type"] == "uncategorized"
    assert all(edge["connection_type"] != "direct_quotation" for edge in result["connections"])


def test_genesis_6_projects_cultural_background_and_comparison_as_distinct_evidence():
    records = _load_ckl(
        "cultural_background/genesis-flood-postflood-context.json",
        "cultural_background/mesopotamian-creation-and-flood-comparisons.json",
    )
    result = _project("Genesis 6", canonical=_lookup("ckl", records=records))

    sons = _item(
        result,
        "ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions",
    )
    assert sons["object_type"] == "cultural_background"
    assert sons["evidence_category"] == "worldview-concept"
    assert sons["certainty"] == "disputed"
    assert sons["cosmic_geography_role"] == "disputed_divine_beings_interpretation"
    assert sons["dispute_status"] == "major_scholarly_disagreement"
    assert sons["interpretation_state"] == "disputed"
    assert sons["claim_text"]
    assert sons["parent_object_id"] == "genesis-flood-postflood-context"
    assert sons["object_id"] == "genesis-flood-postflood-context"
    assert sons["record_kind"] == "evidence"
    assert sons["source_ids"] == [
        "g2r2-local-genesis-1-50",
        "g2r2-local-sarna-genesis",
        "g2r2-local-hamilton-genesis-1-17",
        "g2-doedens-sons-god",
    ]
    assert [anchor["reference"] for anchor in sons["applicable_passage_anchors"]] == [
        "Genesis 6:1-4"
    ]
    assert any(
        source["id"] == "g2-doedens-sons-god"
        and source["details_available"]
        and source["bibliographic_details"]["year"] == 2019
        for source in sons["sources"]
    )

    comparative = _item(
        result,
        "ckl:mesopotamian-creation-and-flood-comparisons#evidence:gilgamesh-tablet-xi-flood-comparison",
    )
    assert comparative["evidence_category"] == "ancient-text"
    assert comparative["object_type"] == "cultural_background"
    assert comparative["passage_anchors"][0]["relationship"] == "comparative"
    assert comparative["temporal_relation"] == "diachronic"
    assert comparative["certainty"] == "probable"
    assert comparative["id"] != sons["id"]

    violence = _item(
        result,
        "ckl:genesis-flood-postflood-context#evidence:g6-evil-intention-and-violence",
    )
    cosmic = next(
        section
        for section in result["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    themes = next(
        section
        for section in result["sections"]
        if section["id"] == "themes_biblical_connections"
    )
    assert sons["id"] in cosmic["item_ids"]
    assert sons["section_ids"] == [
        "divine_council_cosmic_geography",
        "themes_biblical_connections",
    ]
    assert violence["id"] not in cosmic["item_ids"]
    assert violence["id"] in themes["item_ids"]


def test_psalm_82_cultural_context_is_discoverable_without_a_theme_object():
    record = _load_ckl("cultural_background/ancient-divine-assembly-imagery.json")
    result = _project("Psalm 82", canonical=_lookup("ckl", records=record))

    claim = _item(result, "ckl:ancient-divine-assembly-imagery#claim:psalm-82-assembly-text")
    evidence = _item(result, "ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language")
    comparison = _item(
        result,
        "ckl:ancient-divine-assembly-imagery#evidence:ugaritic-council-comparison",
    )
    assert claim["object_type"] == evidence["object_type"] == "cultural_background"
    assert claim["claim_type"] == "biblical_text"
    assert claim["certainty"] == "textually_explicit"
    assert claim["dispute_status"] == "major_scholarly_disagreement"
    assert claim["interpretation_state"] == "disputed"
    cosmic = next(section for section in result["sections"] if section["id"] == "divine_council_cosmic_geography")
    assert claim["id"] in cosmic["item_ids"]
    assert evidence["id"] in cosmic["item_ids"]
    assert evidence["object_id"] == "ancient-divine-assembly-imagery"
    assert evidence["record_kind"] == "evidence"
    assert evidence["evidence_category"] == "worldview-concept"
    assert evidence["cosmic_geography_role"] == "divine_assembly_text"
    assert evidence["certainty"] == "textually_explicit"
    assert evidence["dispute_status"] == "interpretive_uncertainty"
    assert evidence["source_ids"] == [
        "psalm-82-hebrew-text",
        "smith-origins-biblical-monotheism-2001",
        "lewis-origin-character-god-2020",
    ]
    assert [anchor["reference"] for anchor in evidence["applicable_passage_anchors"]] == [
        "Psalm 82:1-8"
    ]
    assert comparison["id"] in cosmic["item_ids"]
    assert comparison["object_id"] == "ancient-divine-assembly-imagery"
    assert comparison["record_kind"] == "evidence"
    assert comparison["evidence_category"] == "ancient-text"
    assert comparison["cosmic_geography_role"] == "divine_assembly_comparison"
    assert comparison["certainty"] == "probable"
    assert comparison["dispute_status"] == "major_scholarly_disagreement"
    assert comparison["source_ids"] == [
        "smith-ugaritic-baal-cycle-1994",
        "smith-origins-biblical-monotheism-2001",
        "lewis-origin-character-god-2020",
    ]
    assert comparison["applicable_passage_anchors"][0]["reference"] == "Psalm 82:1-8"
    assert comparison["applicable_passage_anchors"][0]["relationship"] == "comparative"
    assert "archaeology_ancient_history" in comparison["section_ids"]
    assert not any(item["object_type"] == "theme" for item in result["items"])


def test_deuteronomy_32_manuscript_evidence_survives_empty_archaeology_lookup():
    record = _load_ckl("cultural_background/ancient-divine-assembly-imagery.json")
    result = _project(
        "Deuteronomy 32",
        canonical=_lookup("ckl", records=record),
        archaeology=_lookup("archaeology"),
    )

    variant = _item(
        result,
        "ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant",
    )
    assert variant["evidence_category"] == "manuscript"
    assert variant["assertion_type"] == "primary-evidence"
    assert variant["certainty"] == "disputed"
    assert variant["dispute_status"] == "textual_variant"
    assert "ulrich-biblical-qumran-scrolls-2010" in variant["source_ids"]
    coverage = {entry["domain"]: entry for entry in result["coverage"]}
    assert coverage["archaeology"]["state"] == "not_represented"
    assert coverage["ckl"]["state"] == "available"
    assert all(edge["connection_type"] != "direct_quotation" for edge in result["connections"])
    cosmic = next(
        section
        for section in result["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    history = next(
        section
        for section in result["sections"]
        if section["id"] == "archaeology_ancient_history"
    )
    assert variant["id"] in history["item_ids"]
    assert variant["id"] not in cosmic["item_ids"]


def test_genesis_6_does_not_inherit_genesis_book_cross_references():
    records = _load_ckl(
        "books/genesis.json",
        "cultural_background/genesis-flood-postflood-context.json",
    )
    result = _project("Genesis 6", canonical=_lookup("ckl", records=records))

    assert any(item["id"].startswith("ckl:genesis#claim:") for item in result["items"])
    assert not any(
        "Exodus 1" in str(connection)
        or "Psalm 105" in str(connection)
        or "Matthew 1" in str(connection)
        for connection in result["connections"]
    )
    assert not any(
        reference.startswith(("Exodus 1", "Psalm 105", "Matthew 1"))
        for item in result["items"]
        for reference in item["related_passages"]
    )
    assert not any(
        key in item for item in result["items"] for key in ("cross_references", "intertextuality")
    )
    assert not any(
        "genesis-ends-in-egypt" in item["id"]
        for item in result["items"]
    )


def test_genesis_6_verse_range_excludes_evidence_anchored_elsewhere_in_chapter():
    record = _load_ckl("cultural_background/genesis-flood-postflood-context.json")
    result = _project("Genesis 6:1-2", canonical=_lookup("ckl", records=record))

    included_ids = {item["evidence_id"] for item in result["items"] if item["evidence_id"]}
    assert "g6-sons-of-god-interpretive-positions" in included_ids
    assert "g6-nephilim-and-mighty-men" not in included_ids
    assert "g6-evil-intention-and-violence" not in included_ids
    assert "g6-one-hundred-twenty-years" not in included_ids
    assert all(
        "Genesis 6:1-4" in item["related_passages"]
        for item in result["items"]
        if item["record_kind"] == "evidence"
    )


def test_genesis_1_keeps_passage_anchored_themes_and_comparative_sources():
    records = _load_ckl(
        "books/genesis.json",
        "events/creation.json",
        "themes/creation-theme.json",
        "cultural_background/mesopotamian-creation-and-flood-comparisons.json",
    )
    result = _project("Genesis 1", canonical=_lookup("ckl", records=records))

    assert any(item["object_id"] == "creation-theme" for item in result["items"])
    assert any(item["evidence_category"] == "ancient-text" for item in result["items"])
    ordered_worldview = _item(
        result,
        "ckl:mesopotamian-creation-and-flood-comparisons#evidence:genesis-ordered-worldview-observation",
    )
    ancient_cosmology = _item(
        result,
        "ckl:mesopotamian-creation-and-flood-comparisons#evidence:enuma-elish-cosmic-ordering-comparison",
    )
    cosmic = next(
        section
        for section in result["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    themes = next(
        section
        for section in result["sections"]
        if section["id"] == "themes_biblical_connections"
    )
    history = next(
        section
        for section in result["sections"]
        if section["id"] == "archaeology_ancient_history"
    )
    assert ordered_worldview["id"] in themes["item_ids"]
    assert ordered_worldview["id"] not in cosmic["item_ids"]
    assert ancient_cosmology["id"] in cosmic["item_ids"]
    assert ancient_cosmology["id"] in history["item_ids"]
    assert ancient_cosmology["certainty"] == "probable"
    assert ancient_cosmology["dispute_status"] == "major_scholarly_disagreement"
    assert ancient_cosmology["applicable_passage_anchors"][0]["relationship"] == "comparative"
    assert ancient_cosmology["object_id"] == "mesopotamian-creation-and-flood-comparisons"
    assert ancient_cosmology["record_kind"] == "evidence"
    assert ancient_cosmology["source_ids"] == [
        "lambert-babylonian-creation-2013",
        "sarna-genesis-comparison",
    ]
    assert ancient_cosmology["section_ids"] == [
        "archaeology_ancient_history",
        "divine_council_cosmic_geography",
    ]
    assert not any(
        item["claim_id"] == "genesis-blessing-for-families"
        or item["claim_id"] == "genesis-ends-in-egypt"
        for item in result["items"]
    )


def test_genesis_2_and_3_keep_qualified_sacred_space_evidence_scoped_and_distinct():
    genesis = _load_ckl("books/genesis.json")

    genesis_two = _project("Genesis 2", canonical=_lookup("ckl", records=genesis))
    garden = _item(genesis_two, "ckl:genesis#evidence:g2-garden-planting-presence")
    cosmic_two = next(
        section
        for section in genesis_two["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    geography_two = next(
        section
        for section in genesis_two["sections"]
        if section["id"] == "biblical_geography"
    )
    assert garden["evidence_category"] == "geography-environment"
    assert garden["cosmic_geography_role"] == "sacred_space_interpretation"
    assert garden["certainty"] == "plausible"
    assert garden["dispute_status"] == "interpretive_uncertainty"
    assert garden["source_ids"] == ["genesis-1-50", "sarna-genesis", "g1-amit-eden-exposition"]
    assert [anchor["reference"] for anchor in garden["applicable_passage_anchors"]] == [
        "Genesis 2:8-10"
    ]
    assert garden["id"] in cosmic_two["item_ids"]
    assert garden["id"] in geography_two["item_ids"]
    assert garden["id"] in {item["id"] for item in genesis_two["items"]}
    assert len({item["id"] for item in genesis_two["items"]}) == len(genesis_two["items"])

    genesis_three = _project("Genesis 3", canonical=_lookup("ckl", records=genesis))
    cherubim = _item(
        genesis_three,
        "ckl:genesis#evidence:g3-cherubim-biblical-sacred-space-context",
    )
    serpent = _item(genesis_three, "ckl:genesis#evidence:g3-serpent-genesis-characterization")
    cosmic_three = next(
        section
        for section in genesis_three["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    assert cherubim["certainty"] == "strong_consensus"
    assert cherubim["dispute_status"] == "minor_scholarly_disagreement"
    assert cherubim["object_id"] == "genesis"
    assert cherubim["record_kind"] == "evidence"
    assert cherubim["evidence_category"] == "worldview-concept"
    assert cherubim["cosmic_geography_role"] == "sacred_space_guarding_context"
    assert serpent["cosmic_geography_role"] is None
    assert cherubim["source_ids"] == [
        "genesis-1-50",
        "g1-exodus-text",
        "g1-kings-text",
        "g1-lexham-cherubim",
    ]
    assert [anchor["reference"] for anchor in cherubim["applicable_passage_anchors"]] == [
        "Genesis 3:24"
    ]
    assert cherubim["id"] in cosmic_three["item_ids"]
    assert serpent["id"] not in cosmic_three["item_ids"]


def test_exodus_3_does_not_promote_presence_or_physical_places_to_sacred_space():
    records = _load_ckl(
        "books/exodus.json",
        "events/burning-bush.json",
        "places/mount-sinai.json",
        "themes/presence-theme.json",
        "themes/glory-theme.json",
        "theology/divine-presence.json",
        "themes/water-theme.json",
    )
    result = _project(
        "Exodus 3",
        canonical=_lookup("ckl", records=records),
        maps=_lookup("maps"),
        archaeology=_lookup("archaeology"),
    )

    presence_theme = _item(result, "ckl:presence-theme")
    divine_presence = _item(result, "ckl:divine-presence")
    burning_bush = _item(result, "ckl:burning-bush")
    mount_sinai = _item(result, "ckl:mount-sinai")
    cosmic = next(
        section
        for section in result["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    themes = next(
        section
        for section in result["sections"]
        if section["id"] == "themes_biblical_connections"
    )
    coverage = {entry["domain"]: entry for entry in result["coverage"]}

    assert presence_theme["id"] in themes["item_ids"]
    assert divine_presence["id"] in themes["item_ids"]
    assert presence_theme["id"] not in cosmic["item_ids"]
    assert divine_presence["id"] not in cosmic["item_ids"]
    assert burning_bush["id"] not in cosmic["item_ids"]
    assert mount_sinai["id"] not in cosmic["item_ids"]
    assert cosmic["item_ids"] == []
    assert cosmic["state"] == "unknown"
    assert "Passage-specific availability could not be established" in cosmic["description"]
    assert coverage["ckl"]["state"] == "available"


@pytest.mark.parametrize(
    ("reference", "object_path", "object_id", "expected_section"),
    [
        ("Exodus 3", "themes/presence-theme.json", "presence-theme", "themes_biblical_connections"),
        ("Exodus 3", "theology/divine-presence.json", "divine-presence", "themes_biblical_connections"),
        ("Exodus 3", "themes/glory-theme.json", "glory-theme", "themes_biblical_connections"),
        ("Exodus 15", "themes/worship-theme.json", "worship-theme", "themes_biblical_connections"),
        ("Psalm 2", "themes/kingdom-theme.json", "kingdom-theme", "themes_biblical_connections"),
        ("Exodus 25", "themes/temple-theme.json", "temple-theme", "themes_biblical_connections"),
        ("Exodus 19", "themes/mountain-theme.json", "mountain-theme", "themes_biblical_connections"),
        ("Exodus 3", "places/mount-sinai.json", "mount-sinai", "biblical_geography"),
    ],
)
def test_general_presence_worship_kingship_temple_glory_and_mountain_are_not_cosmic_by_title(
    reference, object_path, object_id, expected_section
):
    result = _project(reference, canonical=_lookup("ckl", records=_load_ckl(object_path)))
    item = _item(result, f"ckl:{object_id}")
    cosmic = next(
        section
        for section in result["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )

    assert expected_section in item["section_ids"]
    assert item["id"] not in cosmic["item_ids"]


def test_cosmic_section_coverage_uses_map_status_without_hiding_ckl_evidence():
    record = _load_ckl("cultural_background/ancient-divine-assembly-imagery.json")
    failed_maps = _project(
        "Psalm 82",
        canonical=_lookup("ckl", records=record),
        maps=_lookup("maps", query_status="failed", reason_code="maps_unavailable"),
        archaeology=_lookup("archaeology"),
    )
    failed_cosmic = next(
        section
        for section in failed_maps["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    evidence_id = "ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language"
    assert failed_cosmic["state"] == "partial"
    assert evidence_id in failed_cosmic["item_ids"]
    assert failed_cosmic["source_domains"] == [
        "canonical_knowledge_library",
        "passage_maps",
    ]

    complete_empty_maps = _project(
        "Psalm 82",
        canonical=_lookup("ckl", records=record),
        maps=_lookup("maps"),
        archaeology=_lookup("archaeology"),
    )
    complete_cosmic = next(
        section
        for section in complete_empty_maps["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    assert complete_cosmic["state"] == "available"
    assert evidence_id in complete_cosmic["item_ids"]

    all_complete_empty = _project(
        "Psalm 82",
        canonical=_lookup("ckl"),
        maps=_lookup("maps"),
        archaeology=_lookup("archaeology"),
    )
    empty_cosmic = next(
        section
        for section in all_complete_empty["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )
    assert empty_cosmic["item_ids"] == []
    assert empty_cosmic["state"] == "not_represented"


def test_unclassified_passage_eligible_ckl_item_keeps_cosmic_coverage_unknown():
    record = {
        "id": "unclassified-genesis-evidence",
        "type": "cultural_background",
        "title": "Unclassified passage evidence",
        "evidence_items": [
            {
                "id": "unmapped-evidence-kind",
                "description": "Passage-linked source record with an unmapped evidence type.",
                "evidence_type": "unmapped-evidence-kind",
                "scripture_references": [
                    {
                        "reference": "Genesis 1:1-3",
                        "relationship": "direct",
                        "relevance_rationale": "The source explicitly applies to this passage.",
                    }
                ],
                "source_ids": ["unclassified-source-record"],
                "certainty": "plausible",
                "dispute_status": "interpretive_uncertainty",
            }
        ],
    }
    result = _project(
        "Genesis 1",
        canonical=_lookup("ckl", records=[record]),
        maps=_lookup("maps"),
        archaeology=_lookup("archaeology"),
    )
    item = _item(
        result,
        "ckl:unclassified-genesis-evidence#evidence:unmapped-evidence-kind",
    )
    cosmic = next(
        section
        for section in result["sections"]
        if section["id"] == "divine_council_cosmic_geography"
    )

    assert item["section_ids"] == []
    assert item["applicable_passage_anchors"][0]["reference"] == "Genesis 1:1-3"
    assert next(entry for entry in result["coverage"] if entry["domain"] == "ckl")["state"] == "available"
    assert cosmic["item_ids"] == []
    assert cosmic["state"] == "unknown"


def test_authoritative_semantic_misanchor_guard_still_excludes_bad_genesis_evidence():
    misanchored = {
        "id": "kurkh-monolith",
        "type": "archaeology",
        "title": "Assyrian royal inscription",
        "scripture_references": [
            {"reference": "Genesis 1:1-5", "relationship": "primary"}
        ],
        "evidence_items": [
            {
                "id": "unrelated-witness",
                "description": "An unrelated item with the same bad anchor.",
                "evidence_type": "inscription",
                "scripture_references": ["Genesis 1:1-5"],
            }
        ],
    }
    result = _project("Genesis 1", canonical=_lookup("ckl", records=[misanchored]))

    assert not any(item["object_id"] == "kurkh-monolith" for item in result["items"])


def test_read_only_genesis_fixtures_are_not_mutated():
    records = _load_ckl(
        "books/genesis.json",
        "cultural_background/genesis-flood-postflood-context.json",
    )
    before = deepcopy(records)

    _project("Genesis 6", canonical=_lookup("ckl", records=records))

    assert records == before


def test_parent_qualified_ids_and_unavailable_source_details_are_preserved():
    records = [
        {
            "id": "parent-one",
            "type": "cultural_background",
            "title": "One",
            "scripture_references": [],
            "sources": [],
            "claims": [],
            "evidence_items": [
                {
                    "id": "shared-local-id",
                    "title": "First witness",
                    "description": "One recorded claim.",
                    "evidence_type": "manuscript",
                    "assertion_type": "primary-evidence",
                    "scripture_references": [{"reference": "Genesis 6:1-4", "relationship": "direct"}],
                    "source_ids": ["missing-source"],
                }
            ],
        },
        {
            "id": "parent-two",
            "type": "cultural_background",
            "title": "Two",
            "sources": [],
            "evidence_items": [
                {
                    "id": "shared-local-id",
                    "title": "Second witness",
                    "description": "A distinct recorded claim.",
                    "evidence_type": "ancient-text",
                    "assertion_type": "secondary-evidence",
                    "scripture_references": [{"reference": "Genesis 6:1-4", "relationship": "comparative"}],
                }
            ],
        },
    ]
    result = _project("Genesis 6", canonical=_lookup("ckl", records=records))

    first_id = "ckl:parent-one#evidence:shared-local-id"
    second_id = "ckl:parent-two#evidence:shared-local-id"
    first = _item(result, first_id)
    second = _item(result, second_id)
    assert first_id != second_id
    assert first["parent_object_id"] == "parent-one"
    assert second["parent_object_id"] == "parent-two"
    assert first["sources"] == [
        {
            "id": "missing-source",
            "details_available": False,
            "unavailable_reason": "source_not_found_in_ckl",
        }
    ]


def test_ambiguous_relationships_stay_uncategorized_and_do_not_gain_reverse_edges():
    record = {
        "id": "relation-parent",
        "type": "cultural_background",
        "title": "Relation fixture",
        "scripture_references": [],
        "claims": [],
        "evidence_items": [
            {
                "id": "relation-evidence",
                "title": "Recorded edge",
                "description": "A claim with an authored but ambiguous edge.",
                "evidence_type": "worldview-concept",
                "assertion_type": "inference",
                "scripture_references": [{"reference": "Genesis 6:1-4", "relationship": "direct"}],
                "related_objects": [
                    {"id": "other-parent", "relationship": "associated-with", "notes": "Authored note."}
                ],
            }
        ],
    }
    result = _project("Genesis 6", canonical=_lookup("ckl", records=[record]))

    edge = next(edge for edge in result["connections"] if edge["target_id"] == "ckl:other-parent")
    assert edge["connection_type"] == "uncategorized"
    assert edge["original_relationship_type"] == "associated-with"
    assert edge["relationship_mode"] == "inferred"
    assert edge["direction"] == "one_way"
    assert edge["reverse_edge_id"] is None
    assert edge["basis"]["notes"] == "Authored note."
    assert all(
        connection["connection_type"] != "direct_quotation"
        for connection in result["connections"]
        if connection["original_relationship_type"] == "direct"
    )


def test_related_evidence_cannot_pull_an_unanchored_sibling_into_scope():
    record = {
        "id": "siblings",
        "type": "cultural_background",
        "title": "Sibling evidence fixture",
        "evidence_items": [
            {
                "id": "in-scope",
                "description": "Evidence linked to the selected passage.",
                "evidence_type": "ancient-text",
                "scripture_references": ["Genesis 6:1-2"],
                "related_evidence": [
                    {"id": "out-of-scope", "relationship": "supports", "notes": "Sibling relation."}
                ],
            },
            {
                "id": "out-of-scope",
                "description": "Evidence linked elsewhere in the chapter.",
                "title": "Filtered sibling title must stay hidden.",
                "evidence_type": "ancient-text",
                "scripture_references": ["Genesis 6:10-12"],
            },
        ],
        "claims": [],
    }
    result = _project("Genesis 6:1-2", canonical=_lookup("ckl", records=[record]))

    assert "ckl:siblings#evidence:in-scope" in {item["id"] for item in result["items"]}
    assert "ckl:siblings#evidence:out-of-scope" not in {item["id"] for item in result["items"]}
    edge = next(
        edge for edge in result["connections"]
        if edge["source_id"] == "ckl:siblings#evidence:in-scope"
        and edge["basis"].get("kind") == "ckl_related_evidence"
    )
    assert edge["target_id"] == "ckl:siblings#evidence:out-of-scope"
    assert edge["basis"]["target_resolution_status"] == "filtered"
    assert "Filtered sibling title must stay hidden." not in json.dumps(result)


def test_related_evidence_target_status_is_unavailable_when_lookup_is_partial():
    record = {
        "id": "partial-parent",
        "type": "cultural_background",
        "evidence_items": [{
            "id": "source-evidence",
            "description": "Source item.",
            "evidence_type": "ancient-text",
            "scripture_references": ["Genesis 6:1-4"],
            "related_evidence": [{"id": "not-returned", "relationship": "compared-with"}],
        }],
        "claims": [],
    }
    result = _project(
        "Genesis 6",
        canonical=_lookup("ckl", records=[record], query_status="partial"),
    )

    edge = next(edge for edge in result["connections"] if edge["basis"].get("kind") == "ckl_related_evidence")
    assert edge["basis"]["target_resolution_status"] == "unavailable"
    assert "ckl:partial-parent#evidence:not-returned" not in {item["id"] for item in result["items"]}


def test_related_evidence_target_status_is_invalid_for_an_unknown_id_in_a_complete_parent():
    record = {
        "id": "complete-parent",
        "type": "cultural_background",
        "evidence_items": [{
            "id": "source-evidence",
            "description": "Source item.",
            "evidence_type": "ancient-text",
            "scripture_references": ["Genesis 6:1-4"],
            "related_evidence": [{"id": "missing-evidence", "relationship": "compared-with"}],
        }],
        "claims": [],
    }
    result = _project("Genesis 6", canonical=_lookup("ckl", records=[record]))

    edge = next(edge for edge in result["connections"] if edge["basis"].get("kind") == "ckl_related_evidence")
    assert edge["target_id"] == "ckl:complete-parent#evidence:missing-evidence"
    assert edge["basis"]["target_resolution_status"] == "invalid"


def test_related_evidence_malformed_target_id_is_invalid():
    record = {
        "id": "malformed-parent",
        "type": "cultural_background",
        "evidence_items": [{
            "id": "source-evidence",
            "description": "Source item.",
            "evidence_type": "ancient-text",
            "scripture_references": ["Genesis 6:1-4"],
            "related_evidence": [{"id": "not a valid id", "relationship": "compared-with"}],
        }],
        "claims": [],
    }
    result = _project("Genesis 6", canonical=_lookup("ckl", records=[record]))

    edge = next(edge for edge in result["connections"] if edge["basis"].get("kind") == "ckl_related_evidence")
    assert edge["basis"]["target_resolution_status"] == "invalid"
    assert edge["target_id"] == "ckl:malformed-parent#evidence:not a valid id"


def test_related_evidence_never_resolves_a_target_from_another_parent():
    source_parent = {
        "id": "source-parent",
        "type": "cultural_background",
        "evidence_items": [{
            "id": "source-evidence",
            "description": "Source item.",
            "evidence_type": "ancient-text",
            "scripture_references": ["Genesis 6:1-4"],
            "related_evidence": [{"id": "shared-target", "relationship": "compared-with"}],
        }],
        "claims": [],
    }
    other_parent = {
        "id": "other-parent",
        "type": "cultural_background",
        "evidence_items": [{
            "id": "shared-target",
            "title": "A different parent's evidence",
            "description": "This content must not resolve the source parent's edge.",
            "evidence_type": "ancient-text",
            "scripture_references": ["Genesis 6:1-4"],
        }],
        "claims": [],
    }
    result = _project(
        "Genesis 6",
        canonical=_lookup("ckl", records=[source_parent, other_parent]),
    )

    edge = next(edge for edge in result["connections"] if edge["basis"].get("kind") == "ckl_related_evidence")
    assert edge["target_id"] == "ckl:source-parent#evidence:shared-target"
    assert edge["basis"]["target_resolution_status"] == "invalid"
    assert "ckl:other-parent#evidence:shared-target" in {item["id"] for item in result["items"]}
    assert "This content must not resolve the source parent's edge." not in json.dumps(edge)


def test_real_genesis_one_comparison_evidence_targets_are_independently_eligible():
    parent = _load_ckl("cultural_background/mesopotamian-creation-and-flood-comparisons.json")[0]
    result = _project("Genesis 1", canonical=_lookup("ckl", records=[parent]))
    source_id = "ckl:mesopotamian-creation-and-flood-comparisons#evidence:genesis-ordered-worldview-observation"
    target_id = "ckl:mesopotamian-creation-and-flood-comparisons#evidence:enuma-elish-cosmic-ordering-comparison"
    source = _item(result, source_id)
    target = _item(result, target_id)
    edge = next(edge for edge in result["connections"] if edge["source_id"] == source_id and edge["target_id"] == target_id)

    assert [anchor["reference"] for anchor in source["applicable_passage_anchors"]] == ["Genesis 1:1-2:3"]
    assert [anchor["reference"] for anchor in target["applicable_passage_anchors"]] == ["Genesis 1:1-2:3"]
    assert source["source_ids"] == ["genesis-1-11-text", "sarna-genesis-comparison"]
    assert target["source_ids"] == ["lambert-babylonian-creation-2013", "sarna-genesis-comparison"]
    assert edge["original_relationship_type"] == "compared-with"
    assert edge["direction"] == "reciprocal"
    assert edge["basis"]["target_resolution_status"] == "eligible"


@pytest.mark.parametrize(
    ("reference", "object_path", "expected_id"),
    [
        (
            "Genesis 6",
            "cultural_background/genesis-flood-postflood-context.json",
            "ckl:genesis-flood-postflood-context#evidence:g6-second-temple-watchers-reception",
        ),
        (
            "Psalm 82",
            "cultural_background/ancient-divine-assembly-imagery.json",
            "ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language",
        ),
        (
            "Deuteronomy 32",
            "cultural_background/ancient-divine-assembly-imagery.json",
            "ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant",
        ),
        (
            "Genesis 2",
            "books/genesis.json",
            "ckl:genesis#evidence:g2-garden-planting-presence",
        ),
    ],
)
def test_requested_passage_projection_retains_eligible_evidence(reference, object_path, expected_id):
    records = _load_ckl(object_path)
    result = _project(reference, canonical=_lookup("ckl", records=records))

    item = _item(result, expected_id)
    assert item["record_kind"] == "evidence"
    assert item["applicable_passage_anchors"]


def test_only_explicit_relationship_labels_receive_specific_connection_types():
    record = {
        "id": "explicit-relations",
        "type": "event",
        "title": "A literary motif title does not determine the edge",
        "scripture_references": [{"reference": "Genesis 6:1-4", "relationship": "primary"}],
        "related_objects": [
            {"id": "quoted-source", "relationship": "direct-quotation", "notes": "Authored quotation relation."},
            {"id": "word-match", "relationship": "associated-with", "notes": "Same vocabulary is not a typed relation."},
        ],
        "claims": [],
        "evidence_items": [],
    }
    result = _project("Genesis 6", canonical=_lookup("ckl", records=[record]))

    edges = {edge["target_id"]: edge for edge in result["connections"]}
    assert edges["ckl:quoted-source"]["connection_type"] == "direct_quotation"
    assert edges["ckl:quoted-source"]["relationship_mode"] == "direct"
    assert edges["ckl:word-match"]["connection_type"] == "uncategorized"
    assert edges["ckl:word-match"]["original_relationship_type"] == "associated-with"


def test_ne_a2_classifies_only_explicit_ckl_types_and_labels():
    records = [
        {
            "id": "cultural-record",
            "type": "cultural_background",
            "title": "Cultural record",
            "scripture_references": [{"reference": "Genesis 1:1", "relationship": "primary"}],
            "related_objects": [
                {"id": "themed", "relationship": "thematic-anchor", "notes": "Authored theme edge.", "weight": 0.7},
                {"id": "unsafe", "relationship": "canonical-fulfillment", "notes": "Authored proposal."},
            ],
            "claims": [
                {
                    "id": "archaeology-claim",
                    "claim": "An archaeological claim.",
                    "claim_type": "archaeology",
                    "certainty": "likely",
                    "dispute_status": "none",
                    "scripture_references": ["Genesis 1:1"],
                }
            ],
            "evidence_items": [
                {
                    "id": "practice-evidence",
                    "description": "A cultural practice record.",
                    "evidence_type": "cultural-practice",
                    "certainty": "possible",
                    "dispute_status": "contested",
                    "scripture_references": ["Genesis 1:1"],
                    "sources": [{"id": "source-1"}],
                }
            ],
        },
        {
            "id": "theology-record",
            "type": "biblical_theology",
            "title": "Theology record",
            "scripture_references": [{"reference": "Genesis 1:1", "relationship": "primary"}],
            "claims": [
                {
                    "id": "biblical-theology-claim",
                    "claim": "A biblical-theology claim.",
                    "claim_type": "biblical_theology",
                    "certainty": "likely",
                    "dispute_status": "none",
                    "scripture_references": ["Genesis 1:1"],
                }
            ],
            "evidence_items": [],
        },
    ]
    result = _project("Genesis 1", canonical=_lookup("ckl", records=records))
    items = {item["id"]: item for item in result["items"]}

    assert "archaeology_ancient_history" in items["ckl:cultural-record"]["section_ids"]
    assert "archaeology_ancient_history" in items["ckl:cultural-record#claim:archaeology-claim"]["section_ids"]
    evidence = items["ckl:cultural-record#evidence:practice-evidence"]
    assert evidence["section_ids"] == ["archaeology_ancient_history"]
    assert evidence["certainty"] == "possible"
    assert evidence["dispute_status"] == "contested"
    assert evidence["sources"] == [{"id": "source-1", "details_available": False, "unavailable_reason": "source_not_found_in_ckl"}]
    theology_claim = items["ckl:theology-record#claim:biblical-theology-claim"]
    assert theology_claim["section_ids"] == ["themes_biblical_connections"]
    assert "divine_council_cosmic_geography" not in evidence["section_ids"]

    edges = {edge["target_id"]: edge for edge in result["connections"] if edge["target_id"].startswith("ckl:")}
    thematic = edges["ckl:themed"]
    assert thematic["connection_type"] == "thematic_relationship"
    assert thematic["original_relationship_type"] == "thematic-anchor"
    assert thematic["basis"]["notes"] == "Authored theme edge."
    assert thematic["basis"]["weight"] == 0.7
    fulfillment = edges["ckl:unsafe"]
    assert fulfillment["connection_type"] == "uncategorized"
    assert fulfillment["original_relationship_type"] == "canonical-fulfillment"


def test_ne_a2_relationship_policy_preserves_direction_mode_and_temporal_status():
    record = {
        "id": "typed-edges",
        "type": "event",
        "title": "Typed authored edges",
        "scripture_references": [{"reference": "Jeremiah 31:31-34", "relationship": "primary"}],
        "related_objects": [
            {"id": "hebrews", "relationship": "new-covenant-quotation", "notes": "Hebrews quotes Jeremiah.", "weight": 0.9},
            {"id": "reception", "relationship": "later-reception", "notes": "Later receiving text.", "weight": 0.8},
            {"id": "typology", "relationship": "typological-connection", "notes": "Authored typological reading."},
            {"id": "fulfillment", "relationship": "canonical-fulfillment", "notes": "Proposal retained as authored."},
        ],
        "claims": [],
        "evidence_items": [],
    }
    result = _project("Jeremiah 31", canonical=_lookup("ckl", records=[record]))
    edges = {edge["target_id"]: edge for edge in result["connections"] if edge["target_id"].startswith("ckl:")}

    quotation = edges["ckl:hebrews"]
    assert quotation["connection_type"] == "direct_quotation"
    assert quotation["relationship_mode"] == "not_recorded"
    assert quotation["direction"] == "one_way"
    assert quotation["temporal_layer"] == "unknown"
    assert quotation["original_relationship_type"] == "new-covenant-quotation"
    assert quotation["basis"]["notes"] == "Hebrews quotes Jeremiah."
    assert quotation["basis"]["weight"] == 0.9

    reception = edges["ckl:reception"]
    assert reception["connection_type"] == "later_canonical_reception"
    assert reception["relationship_mode"] == "not_recorded"
    assert reception["temporal_layer"] == "later_reception"
    assert reception["direction"] == "one_way"
    assert edges["ckl:typology"]["connection_type"] == "interpretive_association"
    assert edges["ckl:typology"]["relationship_mode"] == "not_recorded"
    assert edges["ckl:fulfillment"]["connection_type"] == "uncategorized"


def test_ne_a2_thematic_reciprocity_requires_the_authored_reverse_edge():
    records = [
        {
            "id": "source-event",
            "type": "event",
            "title": "Source",
            "scripture_references": [{"reference": "Genesis 1:1", "relationship": "primary"}],
            "related_objects": [{"id": "target-theme", "relationship": "thematic-anchor"}],
            "claims": [],
            "evidence_items": [],
        },
        {
            "id": "target-theme",
            "type": "theme",
            "title": "Target",
            "scripture_references": [{"reference": "Genesis 1:1", "relationship": "primary"}],
            "related_objects": [{"id": "source-event", "relationship": "thematic-anchor"}],
            "claims": [],
            "evidence_items": [],
        },
    ]
    reciprocal = _project("Genesis 1", canonical=_lookup("ckl", records=records))
    reciprocal_edges = [edge for edge in reciprocal["connections"] if edge["target_id"].startswith("ckl:")]
    assert len(reciprocal_edges) == 2
    assert {edge["direction"] for edge in reciprocal_edges} == {"reciprocal"}

    records[1]["related_objects"] = []
    one_way = _project("Genesis 1", canonical=_lookup("ckl", records=records))
    one_way_edges = [edge for edge in one_way["connections"] if edge["target_id"].startswith("ckl:")]
    assert len(one_way_edges) == 1
    assert one_way_edges[0]["direction"] == "one_way"
    assert one_way_edges[0]["reverse_edge_id"] is None


def test_not_established_is_distinct_from_unknown_and_recorded_certainty():
    record = {
        "id": "epistemic-state",
        "type": "cultural_background",
        "title": "Epistemic state fixture",
        "claims": [
            {
                "id": "not-established",
                "claim": "The evidence does not establish the proposed identification.",
                "claim_type": "historical_cultural",
                "certainty": "insufficient_evidence",
                "dispute_status": "identification_uncertainty",
                "interpretation_status": "not_established",
                "scripture_references": ["Genesis 6:1-4"],
            }
        ],
        "evidence_items": [],
    }
    result = _project("Genesis 6", canonical=_lookup("ckl", records=[record]))

    claim = _item(result, "ckl:epistemic-state#claim:not-established")
    assert claim["interpretation_state"] == "not_established"
    assert claim["certainty"] == "insufficient_evidence"
    assert claim["dispute_status"] == "identification_uncertainty"
    assert result["coverage"][0]["state"] == "available"


def test_missing_interpretation_values_remain_unknown_and_private_fields_are_excluded():
    record = {
        "id": "unknown-parent",
        "type": "cultural_background",
        "title": "Unknown fixture",
        "review_status": "approved",
        "content_status": "active",
        "human_review_required": False,
        "sources": [],
        "claims": [
            {
                "id": "unknown-claim",
                "claim": "A source claim with no certainty metadata.",
                "claim_type": "historical_cultural",
                "scripture_references": ["Genesis 6:1-4"],
                "private_notes": "not reader evidence",
            }
        ],
        "evidence_items": [],
        "private_highlights": ["never project"],
    }
    result = _project("Genesis 6", canonical=_lookup("ckl", records=[record]))

    claim = _item(result, "ckl:unknown-parent#claim:unknown-claim")
    assert claim["certainty"] is None
    assert claim["dispute_status"] is None
    assert claim["interpretation_state"] == "unknown"
    assert claim["review_status"] == "approved"
    assert claim["content_status"] == "active"
    assert claim["human_review_required"] is False
    assert "private_notes" not in claim
    assert "private_highlights" not in str(result)


def test_nested_personal_metadata_is_removed_without_dropping_authored_metadata():
    record = {
        "id": "nested-metadata",
        "type": "cultural_background",
        "title": "Nested metadata fixture",
        "claims": [
            {
                "id": "claim",
                "claim": "An authored claim with a passage anchor.",
                "scripture_references": ["Genesis 6:1-4"],
                "metadata": {
                    "display_label": "Ancient context",
                    "citation_context": {"edition": "Critical edition"},
                    "private_notes": ["personal note"],
                    "highlights": ["personal highlight"],
                    "study_history": [{"date": "private"}],
                    "nested": {"personal_study_notes": "private"},
                },
            }
        ],
    }
    result = _project("Genesis 6", canonical=_lookup("ckl", records=[record]))
    item = _item(result, "ckl:nested-metadata#claim:claim")

    metadata = item["source_metadata"]["metadata"]
    assert metadata["display_label"] == "Ancient context"
    assert metadata["citation_context"] == {"edition": "Critical edition"}
    assert "private_notes" not in str(result)
    assert "highlights" not in str(result)
    assert "study_history" not in str(result)
    assert "personal_study_notes" not in str(result)


def test_source_id_without_bibliographic_details_is_retained_as_unresolved():
    record = {
        "id": "source-details",
        "type": "cultural_background",
        "title": "Source details fixture",
        "sources": [{"id": "empty-source"}],
        "claims": [
            {
                "id": "claim",
                "claim": "An authored claim with a passage anchor.",
                "scripture_references": ["Genesis 6:1-4"],
                "source_ids": ["empty-source", "missing-source"],
            }
        ],
    }
    result = _project("Genesis 6", canonical=_lookup("ckl", records=[record]))
    item = _item(result, "ckl:source-details#claim:claim")
    sources = {source["id"]: source for source in item["sources"]}

    assert item["source_ids"] == ["empty-source", "missing-source"]
    assert sources["empty-source"]["details_available"] is False
    assert sources["empty-source"]["unavailable_reason"] == "source_record_has_no_bibliographic_details"
    assert sources["missing-source"]["details_available"] is False
    assert sources["missing-source"]["unavailable_reason"] == "source_not_found_in_ckl"


def test_projection_validator_rejects_malformed_navigation_and_connection_shapes():
    project = _public("project_narrative_explorer")
    validate = _public("validate_projection")
    projection = project("Genesis 6", canonical_lookup=_lookup("ckl")).to_dict()

    malformed_navigation = deepcopy(projection)
    malformed_navigation["navigation"] = {"id": "not-a-list"}
    with pytest.raises(ValueError, match="navigation"):
        validate(malformed_navigation)

    malformed_connection = deepcopy(projection)
    malformed_connection["connections"] = [{"id": "bad", "connection_type": "uncategorized"}]
    with pytest.raises(ValueError, match="connection"):
        validate(malformed_connection)


@pytest.mark.parametrize("mismatch", ["evidence_type", "anchor_relation"])
def test_cosmic_role_requires_exact_source_identity_evidence_type_and_relation(mismatch):
    records = deepcopy(_load_ckl("books/genesis.json"))
    genesis = records[0]
    garden = next(
        evidence
        for evidence in genesis["evidence_items"]
        if evidence["id"] == "g2-garden-planting-presence"
    )
    if mismatch == "evidence_type":
        garden["evidence_type"] = "worldview-concept"
        garden["title"] = "A title mentioning sacred space and heavenly beings"
    else:
        garden["scripture_references"][0]["relationship"] = "comparative"

    result = _project("Genesis 2", canonical=_lookup("ckl", records=records))
    projected = _item(result, "ckl:genesis#evidence:g2-garden-planting-presence")

    assert projected["cosmic_geography_role"] is None
    assert "divine_council_cosmic_geography" not in projected["section_ids"]


def test_physical_location_metadata_and_identification_uncertainty_are_preserved():
    place = _map_place(
        "uncertain-place",
        "An uncertain ancient place",
        "Joshua 1:4",
        latitude=91.0,
        longitude=35.0,
        ancient_name="Ancient name",
        modern_name="Modern name",
        region="Negeb",
        territory="Judah",
        period="Iron Age",
        physical_identification_status="unidentified",
        place_identification_confidence="low",
        dispute_status="identification_uncertainty",
    )
    result = _project("Joshua 1", maps=_lookup("maps", records=[place]))
    projected = _item(result, "maps:uncertain-place")

    assert projected["object_id"] == "uncertain-place"
    assert projected["title"] == "An uncertain ancient place"
    assert projected["source_metadata"]["ancient_name"] == "Ancient name"
    assert projected["source_metadata"]["modern_name"] == "Modern name"
    assert projected["source_metadata"]["region"] == "Negeb"
    assert projected["source_metadata"]["territory"] == "Judah"
    assert projected["source_metadata"]["period"] == "Iron Age"
    assert projected["source_metadata"]["physical_identification_status"] == "unidentified"
    assert projected["physical_identification_status"] == "unidentified"
    assert projected["place_identification_confidence"] == "low"
    assert projected["dispute_status"] == "identification_uncertainty"
    assert projected["related_passages"] == ["Joshua 1:4"]
    assert projected["original_relationship_types"] == ["direct"]
    assert projected["sources"][0]["id"] == "map-source"
    assert projected["stored_coordinates"] == {"latitude": 91.0, "longitude": 35.0}
    assert projected["coordinates_displayable"] is False
    assert projected["coordinate_display_reason"] == "invalid_stored_coordinates"
