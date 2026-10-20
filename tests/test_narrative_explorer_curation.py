"""Regression tests for passage-scoped Narrative Explorer relationship curation."""

from importlib import import_module
import json
from pathlib import Path


_OBJECT_ROOT = Path(__file__).resolve().parents[1] / "framework" / "canonical_library" / "objects"


def _load_objects(*paths):
    return [
        json.loads((_OBJECT_ROOT / path).read_text(encoding="utf-8"))
        for path in paths
    ]


def _project(reference, records):
    module = import_module("bhf_agent.presentation.narrative_explorer")
    lookup = module.DomainLookup(domain="ckl", records=records, query_status="complete")
    return module.project_narrative_explorer(reference, canonical_lookup=lookup).to_dict()


def _all_objects():
    return {
        record["id"]: record
        for path in _OBJECT_ROOT.rglob("*.json")
        for record in [json.loads(path.read_text(encoding="utf-8"))]
    }


def _edge(projection, source_id, target_id, relationship=None):
    return next(
        connection
        for connection in projection["connections"]
        if connection["source_id"] == source_id
        and connection["target_id"] == target_id
        and (relationship is None or connection["original_relationship_type"] == relationship)
    )


def test_creation_to_new_creation_edge_explains_its_canonical_theme_link():
    records = _load_objects("events/creation.json", "themes/new-creation-theme.json")
    projection = _project("Genesis 1", records)
    edge = next(
        connection
        for connection in projection["connections"]
        if connection["source_id"] == "ckl:creation"
        and connection["target_id"] == "ckl:new-creation-theme"
    )

    assert edge["connection_type"] == "thematic_relationship"
    assert edge["original_relationship_type"] == "eschatological-fulfillment"
    assert edge["basis"]["notes"] == "renewed creation"
    assert edge["basis"]["weight"] == 9
    assert edge["direction"] == "one_way"
    assert edge["curation"]["review_status"] == "curated_for_explorer"
    assert "Revelation 21:1-5" in edge["curation"]["supporting_passages"]
    assert edge["curation"]["why"]
    assert edge["curation"]["uncertainty"]


def test_curated_registry_matches_exact_authored_identities_and_provenance():
    from bhf_agent.presentation.narrative_explorer_curations import CURATED_RELATIONSHIPS

    objects = _all_objects()
    assert 10 <= len(CURATED_RELATIONSHIPS) <= 20
    seen = set()
    for curation in CURATED_RELATIONSHIPS:
        identity = (
            curation["relationship_kind"],
            curation["source_id"],
            curation["target_id"],
            curation["original_relationship_type"],
            curation["original_notes"],
            curation["original_weight"],
        )
        assert identity not in seen
        seen.add(identity)
        assert curation["classification"] != "uncategorized"
        assert curation["review_status"] == "curated_for_explorer"
        assert curation["applicable_passages"]
        assert curation["supporting_passages"]
        assert curation["supporting_records"]
        assert curation["supporting_ckl_sources"]
        assert curation["textual_observation"]
        assert curation["why"]
        assert curation["uncertainty"]

        if curation["relationship_kind"] == "object":
            source_object_id = curation["source_id"].removeprefix("ckl:")
            target_object_id = curation["target_id"].removeprefix("ckl:")
            source = objects[source_object_id]
            matches = [
                edge for edge in source["related_objects"]
                if edge["id"] == target_object_id
                and edge["relationship"] == curation["original_relationship_type"]
                and edge["notes"] == curation["original_notes"]
                and edge["weight"] == curation["original_weight"]
            ]
            assert len(matches) == 1
        else:
            source_parent_id, source_suffix = curation["source_id"].removeprefix("ckl:").split("#evidence:", 1)
            target_parent_id, target_suffix = curation["target_id"].removeprefix("ckl:").split("#evidence:", 1)
            assert source_parent_id == target_parent_id
            source = objects[source_parent_id]
            source_evidence = next(item for item in source["evidence_items"] if item["id"] == source_suffix)
            matches = [
                edge for edge in source_evidence["related_evidence"]
                if edge["id"] == target_suffix
                and edge["relationship"] == curation["original_relationship_type"]
                and edge["notes"] == curation["original_notes"]
                and edge["weight"] == curation["original_weight"]
            ]
            assert len(matches) == 1

        source_ids = {source["id"] for source in source["sources"]}
        for support in curation["supporting_ckl_sources"]:
            source_record = next(
                record for record in objects[support["object_id"]]["sources"]
                if record["id"] == support["source_id"]
            )
            assert support["source_id"] in {
                record["id"]
                for record in objects[support["object_id"]]["sources"]
            }
            for metadata_key in ("title", "author", "year"):
                if metadata_key in support:
                    assert support[metadata_key] == source_record[metadata_key]
            assert support["source_id"] in source_ids or support["object_id"] != source["id"]
        if curation["relationship_kind"] == "object":
            assert curation["supporting_records"] == [
                f"ckl:{support['object_id']}#source:{support['source_id']}"
                for support in curation["supporting_ckl_sources"]
            ]


def test_each_curated_relationship_projects_with_its_exact_basis_and_direction():
    from bhf_agent.presentation.narrative_explorer_curations import CURATED_RELATIONSHIPS

    objects = _all_objects()
    for curation in CURATED_RELATIONSHIPS:
        if curation["relationship_kind"] == "object":
            source_object_id = curation["source_id"].removeprefix("ckl:")
            target_object_id = curation["target_id"].removeprefix("ckl:")
            record_ids = {source_object_id, target_object_id}
        else:
            record_ids = {curation["source_id"].removeprefix("ckl:").split("#", 1)[0]}
        projection = _project(
            curation["applicable_passages"][0],
            [objects[record_id] for record_id in sorted(record_ids)],
        )
        edge = _edge(
            projection,
            curation["source_id"],
            curation["target_id"],
            curation["original_relationship_type"],
        )

        assert edge["connection_type"] == curation["classification"]
        assert edge["basis"]["notes"] == curation["original_notes"]
        assert edge["basis"]["weight"] == curation["original_weight"]
        reverse = [
            candidate for candidate in projection["connections"]
            if candidate["source_id"] == edge["target_id"]
            and candidate["target_id"] == edge["source_id"]
            and candidate["original_relationship_type"] == edge["original_relationship_type"]
        ]
        if reverse:
            assert len(reverse) == 1
            assert edge["direction"] == "reciprocal"
            assert edge["reverse_edge_id"] == reverse[0]["id"]
        else:
            assert edge["direction"] == "one_way"
            assert edge["reverse_edge_id"] is None
        assert edge["curation"]["supporting_passages"] == curation["supporting_passages"]
        assert edge["curation"]["supporting_records"] == curation["supporting_records"]
        assert edge["curation"]["uncertainty"] == curation["uncertainty"]
        if curation["relationship_kind"] == "evidence":
            assert edge["basis"]["target_resolution_status"] == "eligible"


def test_curated_connection_scope_is_narrower_than_its_parent_anchor_scope():
    records = _load_objects("events/new-jerusalem.json", "themes/new-creation-theme.json")
    in_scope = _project("Revelation 21:1-5", records)
    projection = _project("Revelation 22", records)
    in_scope_edge = _edge(
        in_scope,
        "ckl:new-jerusalem",
        "ckl:new-creation-theme",
        "canonical-fulfillment",
    )
    edge = _edge(
        projection,
        "ckl:new-jerusalem",
        "ckl:new-creation-theme",
        "canonical-fulfillment",
    )

    assert edge["connection_type"] == "uncategorized"
    assert edge["curation"] is None
    assert edge["basis"]["notes"] == "renewed heaven and earth"
    assert edge["id"] == in_scope_edge["id"]


def test_generic_related_book_level_and_shared_vocabulary_edges_stay_uncategorized():
    creation_theme, new_creation_theme = _load_objects(
        "themes/creation-theme.json",
        "themes/new-creation-theme.json",
    )
    theme_projection = _project("Genesis 1", [creation_theme, new_creation_theme])
    reverse_concept = _edge(
        theme_projection,
        "ckl:new-creation-theme",
        "ckl:creation-theme",
        "related-concept",
    )
    assert reverse_concept["connection_type"] == "uncategorized"
    assert reverse_concept["curation"] is None

    assembly, deuteronomy = _load_objects(
        "cultural_background/ancient-divine-assembly-imagery.json",
        "books/deuteronomy.json",
    )
    book_projection = _project("Deuteronomy 32", [assembly, deuteronomy])
    broad_book_edge = _edge(
        book_projection,
        "ckl:ancient-divine-assembly-imagery",
        "ckl:deuteronomy",
        "textual-variant-context",
    )
    assert broad_book_edge["connection_type"] == "uncategorized"
    assert broad_book_edge["curation"] is None

    vocabulary_records = [
        {
            "id": "vocabulary-source",
            "type": "event",
            "title": "Creation wording",
            "scripture_references": [{"reference": "Genesis 1:1-5", "relationship": "primary"}],
            "related_objects": [{
                "id": "vocabulary-target",
                "relationship": "related",
                "weight": 1,
                "notes": "Both use similar creation vocabulary.",
            }],
            "claims": [],
            "evidence_items": [],
        },
        {
            "id": "vocabulary-target",
            "type": "theme",
            "title": "Creation vocabulary",
            "scripture_references": [{"reference": "Genesis 1:1-5", "relationship": "primary"}],
            "related_objects": [],
            "claims": [],
            "evidence_items": [],
        },
    ]
    vocabulary_projection = _project("Genesis 1", vocabulary_records)
    vocabulary_edge = _edge(vocabulary_projection, "ckl:vocabulary-source", "ckl:vocabulary-target")
    assert vocabulary_edge["connection_type"] == "uncategorized"
    assert vocabulary_edge["curation"] is None


def test_original_relationship_metadata_mismatch_cannot_receive_curated_status():
    source, target = _load_objects("events/creation.json", "themes/new-creation-theme.json")
    next(edge for edge in source["related_objects"] if edge["id"] == "new-creation-theme")["notes"] = "rewritten note"
    projection = _project("Genesis 1", [source, target])
    edge = _edge(projection, "ckl:creation", "ckl:new-creation-theme", "eschatological-fulfillment")

    assert edge["connection_type"] == "uncategorized"
    assert edge["basis"]["notes"] == "rewritten note"
    assert edge["curation"] is None
