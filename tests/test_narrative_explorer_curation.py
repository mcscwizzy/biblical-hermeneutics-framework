"""Regression tests for passage-scoped Narrative Explorer relationship curation."""

from importlib import import_module
import json
import hashlib
from pathlib import Path

import pytest

from bhf_agent.presentation.narrative_explorer_curations import CURATED_RELATIONSHIPS


_OBJECT_ROOT = Path(__file__).resolve().parents[1] / "framework" / "canonical_library" / "objects"
_CURATION_PASSAGE_CASES = [
    (entry, passage)
    for entry in CURATED_RELATIONSHIPS
    for passage in entry["applicable_passages"]
]


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
    assert edge["curation"]["curation_status"] == "curated_for_explorer"
    assert edge["curation"]["human_scholarly_approval"] == "not_recorded"
    assert edge["curation"]["ckl_evidence_certainty"]["status"] == "not_recorded"
    assert "Revelation 21:1-5" in edge["curation"]["supporting_passages"]
    assert edge["curation"]["why"]
    assert edge["curation"]["uncertainty"]


def test_curated_registry_matches_exact_authored_identities_and_provenance():
    from bhf_agent.presentation.narrative_explorer_curations import CURATED_RELATIONSHIPS

    objects = _all_objects()
    assert len(CURATED_RELATIONSHIPS) >= 25
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
        assert curation["curation_status"] == "curated_for_explorer"
        assert curation["human_scholarly_approval"] == "not_recorded"
        assert curation["curation_confidence"] in {"high", "moderate"}
        assert curation["ckl_evidence_certainty"]["status"] in {"not_recorded", "recorded"}
        assert curation["applicable_passages"]
        assert curation["supporting_passages"]
        assert "KTU 1.1-1.2" not in curation["supporting_passages"]
        assert curation["supporting_records"]
        assert curation["supporting_ckl_sources"]
        assert curation["textual_observation"]
        assert curation["why"]
        assert curation["uncertainty"]
        assert isinstance(curation["supporting_comparative_material"], list)

        for material in curation["supporting_comparative_material"]:
            assert material["kind"] == "ancient_comparative_literature"
            assert material["reference"]
            assert material["source_id"]
        certainty = curation["ckl_evidence_certainty"]
        if curation["relationship_kind"] == "evidence":
            assert certainty["status"] == "recorded"
            assert certainty["records"]
            assert all(record["certainty"] for record in certainty["records"])
        else:
            assert certainty == {"status": "not_recorded", "records": []}

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
            support_record_ids = set(curation["supporting_records"])
            bibliography_record_ids = {
                f"ckl:{support['object_id']}#source:{support['source_id']}"
                for support in curation["supporting_ckl_sources"]
            }
            assert bibliography_record_ids <= support_record_ids
            for support_record_id in support_record_ids:
                object_id, record_ref = support_record_id.removeprefix("ckl:").split("#", 1)
                record_kind, record_id = record_ref.split(":", 1)
                collection = {
                    "source": "sources",
                    "claim": "claims",
                    "evidence": "evidence_items",
                }[record_kind]
                assert any(
                    record.get("id") == record_id
                    for record in objects[object_id].get(collection, [])
                )


@pytest.mark.parametrize(
    "case",
    _CURATION_PASSAGE_CASES,
    ids=[
        f"{entry['source_id']}->{entry['target_id']}:{entry['original_relationship_type']}@{passage}"
        for entry, passage in _CURATION_PASSAGE_CASES
    ],
)
def test_each_curated_relationship_projects_with_its_exact_basis_and_direction(case):
    curation, passage_reference = case
    objects = _all_objects()
    if curation["relationship_kind"] == "object":
        source_object_id = curation["source_id"].removeprefix("ckl:")
        target_object_id = curation["target_id"].removeprefix("ckl:")
        record_ids = {source_object_id, target_object_id}
    else:
        record_ids = {curation["source_id"].removeprefix("ckl:").split("#", 1)[0]}
    projection = _project(
        passage_reference,
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
    assert edge["curation"]["curation_confidence"] == curation["curation_confidence"]
    assert edge["curation"]["human_scholarly_approval"] == "not_recorded"
    if curation["relationship_kind"] == "evidence":
        assert edge["basis"]["target_resolution_status"] == "eligible"


def test_later_canonical_reception_is_separate_from_unknown_ckl_temporal_layer():
    records = _load_objects("themes/messiah-theme.json", "themes/resurrection-theme.json")
    projection = _project("Acts 2:22-36", records)
    edge = _edge(
        projection,
        "ckl:messiah-theme",
        "ckl:resurrection-theme",
        "vindication-pattern",
    )

    assert edge["temporal_layer"] == "unknown"
    assert edge["connection_type"] == "later_canonical_reception"
    assert edge["curation"]["classification"] == "later_canonical_reception"
    assert edge["curation"]["curation_confidence"] == "moderate"
    assert edge["curation"]["ckl_evidence_certainty"]["status"] == "not_recorded"
    assert edge["curation"]["human_scholarly_approval"] == "not_recorded"


def test_comparative_ancient_material_is_not_mislabeled_as_scripture():
    from bhf_agent.presentation.narrative_explorer_curations import CURATED_RELATIONSHIPS

    entries = [entry for entry in CURATED_RELATIONSHIPS if entry["relationship_kind"] == "evidence"]
    assert entries
    for entry in entries:
        assert "KTU 1.1-1.2" not in entry["supporting_passages"]
        assert any(
            material["reference"] == "KTU 1.1-1.2"
            and material["kind"] == "ancient_comparative_literature"
            for material in entry["supporting_comparative_material"]
        )
        certainty = entry["ckl_evidence_certainty"]
        assert certainty["status"] == "recorded"
        assert {record["certainty"] for record in certainty["records"]} == {"textually_explicit", "probable"}


def test_registry_rejects_cross_chapter_applicability_the_projection_cannot_scope():
    from bhf_agent.presentation.narrative_explorer_curations import (
        CURATED_RELATIONSHIPS,
        validate_curation,
    )

    invalid = dict(CURATED_RELATIONSHIPS[0])
    invalid["applicable_passages"] = ["Genesis 1:1-2:3"]

    with pytest.raises(ValueError, match="single chapter"):
        validate_curation(invalid)


def test_curation_validation_reuses_the_cached_scripture_alias_lookup(monkeypatch):
    from framework.canonical_library import scripture
    from bhf_agent.presentation.narrative_explorer_curations import (
        CURATED_RELATIONSHIPS,
        validate_curation,
    )

    def unexpected_alias_rebuild(*args, **kwargs):
        pytest.fail("curation validation rebuilt the shared scripture alias lookup")

    monkeypatch.setattr(scripture, "build_book_alias_lookup", unexpected_alias_rebuild)
    validate_curation(CURATED_RELATIONSHIPS[0], require_authored_direction=True)


def test_batch_two_divine_assembly_and_restoration_edges_are_exact_and_scoped():
    from bhf_agent.presentation.narrative_explorer_curations import CURATED_RELATIONSHIPS

    by_identity = {
        (entry["source_id"], entry["target_id"], entry["original_relationship_type"]): entry
        for entry in CURATED_RELATIONSHIPS
    }
    expected = {
        ("ckl:ancient-divine-assembly-imagery", "ckl:deuteronomy", "textual-variant-context"): (
            "interpretive_association", ["Deuteronomy 32:8-9"],
        ),
        ("ckl:ancient-divine-assembly-imagery", "ckl:job", "heavenly-scene-context"): (
            "shared_literary_motif", ["Job 1:6-12", "Job 2:1-7"],
        ),
        ("ckl:ancient-divine-assembly-imagery", "ckl:psalms", "primary-textual-context"): (
            "interpretive_association", ["Psalm 82:1-8"],
        ),
        ("ckl:the-exodus", "ckl:new-exodus-theme", "fulfillment-framework"): (
            "thematic_relationship", ["Exodus 14:21-31"],
        ),
        ("ckl:exile-theme", "ckl:babylonian-exile", "historical-anchor"): (
            "thematic_relationship", ["2 Kings 24:8-20", "2 Kings 25:1-30"],
        ),
    }
    assert set(expected).issubset(by_identity)
    objects = _all_objects()
    for identity, (classification, passages) in expected.items():
        entry = by_identity[identity]
        assert entry["classification"] == classification
        assert entry["applicable_passages"] == passages
        source_id = entry["source_id"].removeprefix("ckl:")
        target_id = entry["target_id"].removeprefix("ckl:")
        for passage in passages:
            projection = _project(passage, [objects[source_id], objects[target_id]])
            edge = _edge(projection, *identity)
            assert edge["connection_type"] == classification
            assert edge["basis"]["notes"] == entry["original_notes"]
            assert edge["basis"]["weight"] == entry["original_weight"]
            assert edge["curation"]["supporting_ckl_sources"] == entry["supporting_ckl_sources"]
            assert edge["direction"] == "one_way"
            assert edge["reverse_edge_id"] is None


def test_batch_two_holds_unlinked_and_generic_divine_council_candidates():
    from bhf_agent.presentation.narrative_explorer_curations import CURATED_RELATIONSHIPS

    identities = {
        (entry["source_id"], entry["target_id"], entry["original_relationship_type"])
        for entry in CURATED_RELATIONSHIPS
    }
    assert ("ckl:daniel", "ckl:ancient-divine-assembly-imagery", "related") not in identities
    assert ("ckl:psalms", "ckl:ancient-divine-assembly-imagery", "passage-specific-worldview-evidence") not in identities
    assert ("ckl:jeremiah", "ckl:restoration-theme", "major-theological-theme") not in identities
    assert ("ckl:hosea", "ckl:exile-theme", "judgment-and-return") not in identities
    assert ("ckl:isaiah", "ckl:babylonian-exile", "exilic-context") not in identities
    assert ("ckl:ezekiel", "ckl:restoration-theme", "major-theological-theme") not in identities
    assert ("ckl:jeremiah", "ckl:daniel", "seventy-years-reception") not in identities
    assert ("ckl:new-exodus-theme", "ckl:exile-theme", "related-concept") not in identities
    assert ("ckl:restoration-theme", "ckl:exile-theme", "related-concept") not in identities


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

    psalms, job = _load_objects(
        "books/psalms.json",
        "books/job.json",
    )
    book_projection = _project("Psalm 89", [psalms, job])
    assert not any(
        edge["source_id"] == "ckl:psalms"
        and edge["target_id"] == "ckl:job"
        and edge["original_relationship_type"] == "wisdom-and-lament-dialogue"
        for edge in book_projection["connections"]
    )

    assembly, psalms = _load_objects(
        "cultural_background/ancient-divine-assembly-imagery.json",
        "books/psalms.json",
    )
    contextual_projection = _project("Psalm 82", [assembly, psalms])
    book_edge = _edge(
        contextual_projection,
        "ckl:ancient-divine-assembly-imagery",
        "ckl:psalms",
        "primary-textual-context",
    )
    assert book_edge["connection_type"] == "interpretive_association"
    assert book_edge["curation"]["applicable_passages"] == ["Psalm 82:1-8"]

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


def test_registry_loads_versioned_data_and_keeps_legacy_curation_payload_unchanged():
    from bhf_agent.presentation import narrative_explorer_curations as registry

    entries = list(registry.CURATED_RELATIONSHIPS)
    legacy_root = (
        Path(__file__).resolve().parents[1]
        / "framework" / "canonical_library" / "curations" / "narrative-explorer" / "ne9c" / "wave-legacy"
    )
    legacy_entries = []
    for path in sorted(legacy_root.glob("batch-*.json")):
        legacy_entries.extend(json.loads(path.read_text(encoding="utf-8"))["curations"])
    assert len(legacy_entries) == 25
    assert all(entry["authored_direction"] in {"one_way", "reciprocal"} for entry in entries)
    assert len(registry.CURATION_BY_IDENTITY) == len(entries)

    legacy_payloads = [
        {key: value for key, value in entry.items() if key != "authored_direction"}
        for entry in legacy_entries
    ]
    digest = hashlib.sha256(
        json.dumps(legacy_payloads, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert digest == "063c0d9879cfef585462392890868622206556933089475a847dfdb8103ed886"

    with pytest.raises(TypeError):
        registry.CURATION_BY_IDENTITY[next(iter(registry.CURATION_BY_IDENTITY))] = entries[0]


def test_registry_rejects_duplicate_and_malformed_data_entries():
    from bhf_agent.presentation import narrative_explorer_curations as registry

    entry = dict(registry.CURATED_RELATIONSHIPS[0])
    with pytest.raises(ValueError, match="duplicate"):
        registry.build_curation_index([entry, entry])

    malformed = dict(entry)
    malformed.pop("authored_direction")
    with pytest.raises(ValueError, match="direction"):
        registry.build_curation_index([malformed])


def test_registry_preserves_a_missing_authored_note_as_null_metadata():
    from bhf_agent.presentation import narrative_explorer_curations as registry

    entry = dict(registry.CURATED_RELATIONSHIPS[0])
    entry["original_notes"] = None

    registry.validate_curation(entry, require_authored_direction=True)


def test_cyrus_cylinder_and_return_edges_are_scoped_comparative_context_in_authored_directions():
    cyrus, return_event = _load_objects(
        "archaeology/cyrus-cylinder.json",
        "events/return-from-exile.json",
    )
    projection = _project("Ezra 1", [cyrus, return_event])
    forward = _edge(
        projection,
        "ckl:cyrus-cylinder",
        "ckl:return-from-exile",
        "comparative-restoration-context",
    )
    reverse = _edge(
        projection,
        "ckl:return-from-exile",
        "ckl:cyrus-cylinder",
        "comparative-imperial-context",
    )

    for edge in (forward, reverse):
        assert edge["connection_type"] == "interpretive_association"
        assert edge["curation"]["applicable_passages"] == ["Ezra 1:1-4", "2 Chronicles 36:22-23"]
        assert edge["curation"]["supporting_comparative_material"][0]["kind"] == "ancient_comparative_literature"
        assert edge["curation"]["human_scholarly_approval"] == "not_recorded"
        assert "authored_direction" not in edge["curation"]
        assert "not a quotation" in edge["curation"]["uncertainty"]

    assert forward["basis"]["notes"] == "The relationship is comparative because the cylinder does not name the Judean return."
    assert reverse["basis"]["notes"] == "The Babylonian inscription is not the Judean decree."
