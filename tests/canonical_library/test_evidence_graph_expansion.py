from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from bhf_agent.archaeology_content import ARCHAEOLOGY_ITEMS
from bhf_web.routes.canonical import _serialize_object, _serialize_topic
from framework.canonical_library import (
    CanonicalContextBuilder,
    CanonicalLibrary,
    CanonicalValidationError,
    SQLiteCanonicalLibrary,
    audit_evidence,
    build_canonical_prompt_context,
    build_database,
    evidence_graph_edges,
    migrate_database,
    rank_evidence_items,
    validate_object,
)

from .helpers import make_object, write_library


def _source(source_id: str, title: str, source_type: str = "ancient-primary-source") -> dict[str, object]:
    return {
        "id": source_id,
        "title": title,
        "author": "",
        "publisher": "Open fixture source",
        "year": None,
        "locator": "fixture locator",
        "url": "https://example.test/source/" + source_id,
        "source_type": source_type,
        "supports": [],
        "notes": "Test provenance.",
    }


def _link(reference: str, temporal_relation: str, relationship: str = "comparative") -> dict[str, object]:
    return {
        "reference": reference,
        "relationship": relationship,
        "temporal_relation": temporal_relation,
        "relevance_rationale": "Authored relevance for this exact passage and chronological relationship.",
        "weight": 8,
    }


def _item(
    evidence_id: str,
    title: str,
    reference: str,
    temporal_relation: str,
    source_id: str,
    *,
    start_year: int,
    end_year: int,
    evidence_type: str = "ancient-text",
    external: bool = False,
    claim_ids: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "id": evidence_id,
        "title": title,
        "evidence_type": evidence_type,
        "description": title + " supplies controlled historical comparison.",
        "assertion_type": "primary-evidence",
        "confidence": "high",
        "confidence_rationale": "The fixture has an identified source and an explicit limitation.",
        "passage_relevance": "This evidence clarifies context without determining the passage's theology.",
        "certainty": "strong_consensus",
        "dispute_status": "not_disputed",
        "primary_observation": title + " primary observation.",
        "scholarly_interpretation": "Its relevance is a separate scholarly comparison.",
        "temporal_scope": {
            "start_year": start_year,
            "end_year": end_year,
            "approximate": True,
            "periods": ["fixture period"],
            "narrative_setting": "Fixture setting",
            "source_composition_start_year": start_year,
            "source_composition_end_year": end_year,
            "source_composition_approximate": True,
            "notes": "Broad test chronology.",
        },
        "geography_ids": ["mesopotamia"],
        "related_objects": [
            {"id": "mesopotamia", "relationship": "regional-context", "weight": 8, "notes": "fixture"}
        ],
        "related_evidence": [],
        "scripture_references": [_link(reference, temporal_relation)],
        "source_ids": [source_id],
        "claim_ids": list(claim_ids),
        "external_references": (
            [{"domain": "archaeology-item", "id": evidence_id, "relationship": "same-evidence", "notes": "peer domain"}]
            if external
            else []
        ),
        "metadata": {
            "archaeological_period": "fixture period",
            "associated_biblical_geography": "Mesopotamia",
        },
        "notes": "",
    }


def evidence_fixture_objects() -> list[dict[str, object]]:
    return [
        make_object(
            "creation-context",
            "cultural_background",
            "Creation Context",
            ["creation backgrounds"],
            summary="Chronologically bounded comparisons for Genesis creation language.",
            temporal_scope={
                "start_year": -1200,
                "end_year": -500,
                "approximate": True,
                "periods": ["Iron Age textual horizon"],
                "narrative_setting": "Primeval narrative",
                "source_composition_start_year": -1200,
                "source_composition_end_year": -500,
                "source_composition_approximate": True,
                "notes": "Narrative time is not assigned an artificial calendar date.",
            },
            scripture_references=[],
            sources=[
                _source("ane-tablet", "Ancient Near Eastern tablet"),
                _source("rabbinic-text", "Later rabbinic comparison"),
                _source("john-text", "John 1", "scripture"),
            ],
            claims=[
                {
                    "id": "creation-comparison",
                    "claim": "The ancient source is comparative evidence rather than a biblical manuscript.",
                    "claim_type": "historical_cultural",
                    "certainty": "strong_consensus",
                    "dispute_status": "not_disputed",
                    "scripture_references": ["Genesis 1:1-5"],
                    "source_ids": ["ane-tablet"],
                    "traditions": ["Academic"],
                    "rationale": "The corpora have distinct provenance.",
                    "notes": "",
                }
            ],
            evidence_items=[
                _item("ane-creation-tablet", "ANE creation tablet", "Genesis 1:1-2:3", "earlier-comparative", "ane-tablet", start_year=-1700, end_year=-1600, external=True, claim_ids=("creation-comparison",)),
                _item("later-rabbinic-reading", "Later rabbinic reading", "Genesis 1:1-2:3", "later-comparative", "rabbinic-text", start_year=200, end_year=500),
                _item("john-prologue", "Johannine creation vocabulary", "John 1:1-5", "later-comparative", "john-text", start_year=80, end_year=100),
            ],
        ),
        make_object(
            "mesopotamia",
            "place",
            "Mesopotamia",
            ["ancient Mesopotamia"],
            summary="A broad ancient region used by the fixture.",
        ),
    ]


def _build_fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "ckl"
    database = tmp_path / "ckl.sqlite"
    write_library(root, evidence_fixture_objects())
    build_database(root, database)
    return root, database


def test_schema_requires_provenance_relevance_and_unique_evidence_ids() -> None:
    payload = evidence_fixture_objects()[0]
    payload["evidence_items"][0]["source_ids"] = []  # type: ignore[index]
    with pytest.raises(CanonicalValidationError, match="must cite at least one source_id"):
        validate_object(payload)

    payload = evidence_fixture_objects()[0]
    payload["evidence_items"].append(dict(payload["evidence_items"][0]))  # type: ignore[union-attr,index]
    with pytest.raises(CanonicalValidationError, match="duplicate evidence item id"):
        validate_object(payload)

    payload = evidence_fixture_objects()[0]
    payload["evidence_items"][0]["metadata"]["image_source_url"] = "https://example.test/image.jpg"  # type: ignore[index]
    with pytest.raises(CanonicalValidationError, match="requires image_license"):
        validate_object(payload)


@pytest.mark.parametrize(
    "evidence_type",
    [
        "cultural-practice",
        "geography-environment",
        "institution",
        "literary-convention",
        "worldview-concept",
    ],
)
def test_contextual_evidence_categories_share_the_auditable_contract(evidence_type: str) -> None:
    payload = evidence_fixture_objects()[0]
    payload["evidence_items"] = [
        _item(
            evidence_type + "-fixture",
            evidence_type.replace("-", " ").title(),
            "Genesis 1:1-5",
            "earlier-comparative",
            "ane-tablet",
            start_year=-1700,
            end_year=-1600,
            evidence_type=evidence_type,
        )
    ]
    obj = validate_object(payload)
    assert obj.evidence_items[0].evidence_type == evidence_type
    assert obj.evidence_items[0].passage_relevance
    assert obj.evidence_items[0].geography_ids == ["mesopotamia"]


def test_temporal_filter_blocks_johannine_contamination_but_keeps_explicit_later_comparison(tmp_path: Path) -> None:
    root, _ = _build_fixture(tmp_path)
    obj = CanonicalLibrary(root=root).load().objects_by_id["creation-context"]
    first = rank_evidence_items(
        "What comparative creation evidence helps with Genesis 1?",
        obj,
        scripture_references=("Genesis 1:1-5",),
        requested_dimensions=("ancient near eastern background",),
        limit=10,
    )
    second = rank_evidence_items(
        "What comparative creation evidence helps with Genesis 1?",
        obj,
        scripture_references=("Genesis 1:1-5",),
        requested_dimensions=("ancient near eastern background",),
        limit=10,
    )
    assert [item.evidence_id for item in first] == [item.evidence_id for item in second]
    assert "john-prologue" not in {item.evidence_id for item in first}
    assert "later-rabbinic-reading" in {item.evidence_id for item in first}
    later = next(item for item in first if item.evidence_id == "later-rabbinic-reading")
    assert later.chronological_relation == "later-comparative"
    assert "chronology: later-comparative" in later.retrieval_reason


def test_sqlite_normalizes_evidence_relationships_sources_and_indexes(tmp_path: Path) -> None:
    root, database = _build_fixture(tmp_path)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM canonical_evidence_items").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM canonical_evidence_claims").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM canonical_evidence_sources").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM canonical_evidence_external_references").fetchone()[0] == 1
        assert connection.execute(
            "SELECT temporal_relation FROM canonical_evidence_scripture_references WHERE evidence_id = 'later-rabbinic-reading'"
        ).fetchone()[0] == "later-comparative"
        indexes = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
        assert "idx_evidence_scripture_reference" in indexes
        assert "idx_evidence_relationships_target" in indexes

    json_library = CanonicalLibrary(root=root).load()
    sqlite_library = SQLiteCanonicalLibrary.from_path(database, root=root)
    assert json_library.retrieve_by_scripture_reference("Genesis 1:1")[0].object.id == "creation-context"
    assert sqlite_library.retrieve_by_scripture_reference("Genesis 1:1")[0].object.id == "creation-context"
    arguments = {
        "scripture_references": ("Genesis 1:1-5",),
        "requested_dimensions": ("ancient near eastern background",),
        "limit_per_object": 10,
    }
    json_result = json_library.retrieve_evidence_items("Genesis creation background", ["creation-context"], **arguments)
    sqlite_result = sqlite_library.retrieve_evidence_items("Genesis creation background", ["creation-context"], **arguments)
    sqlite_library.close()
    assert [item.to_dict() for item in json_result["creation-context"]] == [
        item.to_dict() for item in sqlite_result["creation-context"]
    ]
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE ckl_metadata SET value = '2' WHERE key = 'retrieval_index_version'"
        )
    with pytest.raises(RuntimeError, match="retrieval index version 3 is required"):
        SQLiteCanonicalLibrary.from_path(database, root=root)


def test_context_prompt_and_api_package_explainable_evidence(tmp_path: Path) -> None:
    root, _ = _build_fixture(tmp_path)
    library = CanonicalLibrary(root=root).load()
    context = CanonicalContextBuilder(library).build(
        "What ancient background helps explain Genesis 1:1-5?",
        limit=2,
    )
    topic = next(topic for topic in context["retrieved_topics"] if topic["id"] == "creation-context")
    assert topic["selected_evidence"]
    assert all(item["confidence_rationale"] for item in topic["selected_evidence"])
    prompt = build_canonical_prompt_context(context, max_entries=2, max_context_tokens=1000)
    assert prompt["entries"][0]["selected_evidence"]
    assert any(
        section["heading"] == "Contextual Evidence"
        for entry in prompt["entries"]
        for section in entry["sections"]
    )

    serialized = _serialize_object(library.objects_by_id["creation-context"])
    assert serialized["temporal_scope"]["periods"] == ["Iron Age textual horizon"]
    assert serialized["evidence_items"][0]["passage_relevance"]
    assert serialized["sources"][0]["id"]
    search_payload = _serialize_topic(topic, library, browse=False)
    assert search_payload["selected_evidence"][0]["retrieval_reason"]
    assert search_payload["evidence_count"] == 3


def test_evidence_graph_projects_passage_subject_claim_source_and_external_edges(tmp_path: Path) -> None:
    root, _ = _build_fixture(tmp_path)
    objects = CanonicalLibrary(root=root).load().objects_by_id.values()
    edges = evidence_graph_edges(objects)
    kinds = {(edge.source_kind, edge.target_kind, edge.relationship) for edge in edges}
    assert ("passage", "subject", "evidence-for-subject") in kinds
    assert ("subject", "evidence", "has-evidence") in kinds
    assert ("subject", "claim", "has-claim") in kinds
    assert ("passage", "evidence", "comparative") in kinds
    assert ("claim", "evidence", "supported-by") in kinds
    assert ("evidence", "source", "documented-by") in kinds
    assert any(edge.target_kind == "archaeology-item" for edge in edges)


def test_evidence_audit_flags_confidence_chronology_duplicates_and_image_rights(tmp_path: Path) -> None:
    payloads = evidence_fixture_objects()
    first = payloads[0]["evidence_items"][0]  # type: ignore[index]
    first["confidence"] = "high"  # type: ignore[index]
    first["certainty"] = "disputed"  # type: ignore[index]
    first["dispute_status"] = "interpretive_uncertainty"  # type: ignore[index]
    first["metadata"]["image_source_url"] = "https://example.test/image.jpg"  # type: ignore[index]
    first["metadata"]["image_license"] = "CC0"  # type: ignore[index]
    first["metadata"]["image_attribution"] = "Fixture creator"  # type: ignore[index]
    duplicate = dict(payloads[0])
    duplicate["id"] = "creation-context-copy"
    duplicate["title"] = "Creation Context Copy"
    duplicate["aliases"] = ["creation context copy"]
    duplicate["evidence_items"] = [dict(first)]
    duplicate["evidence_items"][0]["id"] = "ane-creation-tablet-copy"
    duplicate["evidence_items"][0]["geography_ids"] = ["mesopotamia"]
    root = tmp_path / "audit"
    write_library(root, [*payloads, duplicate])
    loaded = list(CanonicalLibrary(root=root).load().objects_by_id.values())
    original = next(obj for obj in loaded if obj.id == "creation-context")
    unsafe_item = replace(
        original.evidence_items[0],
        metadata={"image_source_url": "https://example.test/image.jpg"},
    )
    unsafe_object = replace(original, evidence_items=[unsafe_item, *original.evidence_items[1:]])
    objects = [unsafe_object if obj.id == original.id else obj for obj in loaded]
    report = audit_evidence(objects)
    codes = {issue["code"] for issue in report["issues"]}
    assert "dispute-confidence-mismatch" in codes
    assert "missing-image-license" in codes
    assert "missing-image-attribution" in codes
    assert "possible-duplicate-evidence" in codes


def test_version_three_database_migrates_additively_and_old_json_defaults(tmp_path: Path) -> None:
    old_payload = make_object("legacy", "theme", "Legacy", ["legacy topic"])
    old_payload.pop("temporal_scope")
    old_payload.pop("evidence_items")
    validated = validate_object(old_payload)
    assert validated.evidence_items == []
    assert validated.temporal_scope.start_year is None

    database = tmp_path / "legacy.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE ckl_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE canonical_objects (
                id TEXT PRIMARY KEY, type TEXT NOT NULL, title TEXT NOT NULL,
                normalized_title TEXT NOT NULL, summary TEXT, content_status TEXT NOT NULL,
                review_status TEXT NOT NULL, confidence TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 0, object_version TEXT,
                source_path TEXT, payload_json TEXT NOT NULL
            );
            CREATE TABLE legacy_runtime_data (id INTEGER PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO legacy_runtime_data (value) VALUES ('preserve me');
            """
        )
        connection.executemany(
            "INSERT INTO ckl_metadata (key, value) VALUES (?, ?)",
            [("database_schema_version", "3"), ("retrieval_index_version", "2")],
        )
        connection.execute(
            "INSERT INTO canonical_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                validated.id,
                validated.type,
                validated.title,
                validated.title.casefold(),
                validated.summary,
                validated.content_status,
                validated.review_status,
                validated.confidence,
                validated.importance,
                validated.object_version,
                "objects/themes/legacy.json",
                json.dumps(validated.to_dict()),
            ),
        )
    result = migrate_database(database, backup=True)
    assert result["changed"] is True
    assert result["from_version"] == "3"
    assert result["to_version"] == "4"
    backup_path = Path(result["backup_path"])
    assert backup_path.exists()
    with sqlite3.connect(backup_path) as backup_connection:
        assert dict(backup_connection.execute("SELECT key, value FROM ckl_metadata"))["database_schema_version"] == "3"
    with sqlite3.connect(database) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM ckl_metadata"))
        assert metadata["database_schema_version"] == "4"
        assert metadata["retrieval_index_version"] == "3"
        assert connection.execute("SELECT COUNT(*) FROM canonical_temporal_scopes").fetchone()[0] == 1
        assert connection.execute("SELECT value FROM legacy_runtime_data").fetchone()[0] == "preserve me"


def test_curated_david_assyrian_and_persian_evidence_records_are_sourced() -> None:
    library = CanonicalLibrary.load_default()
    expected = {
        "david-and-goliath": {"goliath-weapon-description", "tell-es-safi-metal-production"},
        "sennacherib-prism": {"taylor-prism-annals"},
        "cyrus-cylinder": {"cyrus-cylinder-restoration-context"},
    }
    for object_id, evidence_ids in expected.items():
        obj = library.objects_by_id[object_id]
        assert {item.id for item in obj.evidence_items} == evidence_ids
        source_ids = {source.id for source in obj.sources}
        for item in obj.evidence_items:
            assert item.source_ids
            assert set(item.source_ids) <= source_ids
            assert item.confidence_rationale
            assert item.passage_relevance
            assert item.scripture_references
    assert library.objects_by_id["sennacherib-prism"].evidence_items[0].external_references[0].id == "sennacherib-prism"
    assert library.objects_by_id["cyrus-cylinder"].evidence_items[0].external_references[0].id == "cyrus-cylinder"
    archaeology_ids = {item["id"] for item in ARCHAEOLOGY_ITEMS}
    assert {"sennacherib-prism", "cyrus-cylinder"} <= archaeology_ids

    context = CanonicalContextBuilder(library).build(
        "What evidence helps explain Goliath's weapons in 1 Samuel 17:4-7?",
        limit=8,
    )
    david_topic = next(topic for topic in context["retrieved_topics"] if topic["id"] == "david-and-goliath")
    assert [item["evidence_id"] for item in david_topic["selected_evidence"]] == [
        "goliath-weapon-description",
        "tell-es-safi-metal-production",
    ]
    assert david_topic["selected_evidence"][1]["chronological_relation"] == "later-comparative"
