"""G6B Genesis 45–50 evidence, provenance, and exact-impact gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from framework.canonical_library.loader import CanonicalLibrary
from framework.canonical_library.schema import validate_base_object


ROOT = Path(__file__).resolve().parents[1]
CKL_ROOT = ROOT / "framework/canonical_library"
ARTIFACTS = ROOT / ".bhf-data/bhf-commentary-candidates/genesis-g6b-joseph-reconciliation-conclusion-evidence-expansion"
OBJECT_ID = "genesis-joseph-reconciliation-conclusion-context"
OBJECT_PATH = CKL_ROOT / "objects/cultural_background/genesis-joseph-reconciliation-conclusion-context.json"
TARGET_CHAPTERS = {f"Genesis {chapter}" for chapter in range(45, 51)}
CONTROLS = {
    "Genesis 1", "Genesis 2", "Genesis 5", "Genesis 6", "Genesis 9", "Genesis 10",
    "Genesis 11", "Genesis 12", "Genesis 15", "Genesis 18", "Genesis 22", "Genesis 26",
    "Genesis 31", "Genesis 34", "Genesis 36", "Genesis 37", "Genesis 38", "Genesis 41",
    "Genesis 44", "Exodus 1", "Exodus 25", "Isaiah 36", "Acts 7", "Acts 16",
    "Revelation 12", "Revelation 18",
}


def _read(path: Path):
    return json.loads(path.read_text())


def _owner_rows(raw_objects):
    return sorted(
        (str(obj.get("id") or ""), str(source.get("id") or ""))
        for obj in raw_objects
        for source in obj.get("sources", []) or []
        if source.get("id")
    )


def _owner_hash(rows):
    payload = [{"owner": owner, "source_id": source_id} for owner, source_id in rows]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()


_LIBRARY = None


def _library():
    global _LIBRARY
    if _LIBRARY is None:
        _LIBRARY = CanonicalLibrary(root=CKL_ROOT).load()
    return _LIBRARY


def test_g6b_object_candidates_sources_and_direct_anchors_are_isolated():
    assert OBJECT_PATH.is_file(), "G6B reconciliation/conclusion object has not been applied"
    library = _library()
    production = _read(OBJECT_PATH)
    assert validate_base_object(production, path=OBJECT_PATH)
    obj = library.objects_by_id[OBJECT_ID]
    packet = _read(ARTIFACTS / "g6b-candidate-evidence.json")
    replay = _read(ARTIFACTS / "g6b-candidate-replay-final.json")
    source_lock = _read(ARTIFACTS / "g6b-source-lock.json")
    production_items = {item["id"]: item for item in production["evidence_items"]}
    candidate_items = {
        candidate["evidence_item"]["id"]: candidate["evidence_item"]
        for candidate in packet["candidates"]
    }

    assert obj.type == "cultural_background"
    assert candidate_items == production_items
    assert packet["target_object_id"] == OBJECT_ID
    assert packet["candidate_count"] == len(production_items)
    assert replay["result"] == "PASS"
    assert set(replay["chapters"]) == TARGET_CHAPTERS
    assert len(library.objects_by_id) == 687
    assert sum(len(item.evidence_items) for item in library.objects_by_id.values()) == 1215 + len(production_items)

    source_ids = {source.id for source in obj.sources}
    assert source_ids == {source["id"] for source in production["sources"]}
    assert source_lock["source_count"] == len(obj.sources)
    source_rows = {source["id"]: source for source in production["sources"]}
    for locked in source_lock["sources"]:
        source = source_rows[locked["source_id"]]
        digest = hashlib.sha256(
            json.dumps(source, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        assert digest == locked["sha256"]
        assert locked["supported_evidence_ids"] == source["supports"]
    for item in production["evidence_items"]:
        assert item["source_ids"]
        assert set(item["source_ids"]) <= source_ids
        assert item["scripture_references"]
        for ref in item["scripture_references"]:
            assert ref["relationship"] == "direct"
            assert ref["reference"].startswith(tuple(f"Genesis {chapter}:" for chapter in range(45, 51)))
    assert {
        int(ref.reference.split()[1].split(":")[0]) for ref in obj.scripture_references
    } == set(range(45, 51))

    target_results = _read(ARTIFACTS / "g6b-g0-target-results.json")["targets"]
    assert set(target_results) == TARGET_CHAPTERS
    for chapter in range(45, 51):
        selected = library.retrieve_evidence_items(
            "Joseph reconciliation", [OBJECT_ID],
            scripture_references=[f"Genesis {chapter}"], limit_per_object=100,
        )
        selected_ids = {item.evidence_id for item in selected[OBJECT_ID]}
        chapter_ids = {
            item_id
            for item_id, item in production_items.items()
            if item["scripture_references"][0]["reference"].startswith(f"Genesis {chapter}:")
        }
        assert chapter_ids <= selected_ids


def test_g6b_source_aliases_leave_historical_owner_rows_unchanged():
    library = _library()
    obj = library.objects_by_id[OBJECT_ID]
    audit = _read(ARTIFACTS / "g6b-source-ownership-audit.json")
    assert audit["existing_historical_source_owner_rows_changed"] == 0
    assert audit["post_apply_audit"]["result"] == "PASS"

    fields = ("title", "author", "publisher", "year", "locator", "url", "source_type")
    raw_objects = [
        _read(path)
        for path in CKL_ROOT.joinpath("objects").rglob("*.json")
        if _read(path).get("id") != OBJECT_ID
    ]
    for alias in audit["source_aliases"]:
        local = next(source for source in obj.sources if source.id == alias["local_source_id"])
        historical = [
            source
            for other in raw_objects
            for source in other.get("sources", []) or []
            if source.get("id") == alias["historical_source_id"]
        ]
        assert any(all(getattr(local, field) == source.get(field) for field in fields) for source in historical)
        assert "same publication/work" in local.notes

    base = _read(ARTIFACTS / "g6b-existing-evidence-audit.json")["historical_source_owner_rows"]
    current = _owner_rows(raw_objects)
    assert len(current) == base["count"]
    assert _owner_hash(current) == base["sha256"]


def test_g6b_relationships_are_typed_one_way_and_comparative_material_is_context_only():
    library = _library()
    obj = library.objects_by_id[OBJECT_ID]
    audit = _read(ARTIFACTS / "g6b-comparative-applicability-audit.json")
    assert audit["result"] == "PASS"
    assert audit["out_of_scope_scripture_applicability_anchors"] == []
    assert audit["reverse_applicability_created"] is False
    assert obj.related_objects
    assert all(link.id in library.objects_by_id for link in obj.related_objects)
    assert not any(
        relationship.id == OBJECT_ID
        for other_id, other in library.objects_by_id.items()
        if other_id != OBJECT_ID
        for relationship in other.related_objects
    )
    for item in obj.evidence_items:
        assert all(link.id in library.objects_by_id for link in item.related_objects)
        assert all(geography_id in library.objects_by_id for geography_id in item.geography_ids)


def test_g6b_exact_impact_controls_and_frozen_candidate_history_remain_recorded():
    _library()
    impact = _read(ARTIFACTS / "g6b-chapter-impact.json")
    post = _read(ARTIFACTS / "g6b-post-apply-validation.json")
    assert impact["base_chapter_count"] == 1189
    assert post["changed_chapters"] == [f"Genesis {chapter}" for chapter in range(45, 51)]
    assert post["whole_corpus_exact_set_pass"] is True
    assert set(post["controls"]) == CONTROLS
    assert all(post["controls"].values())

    stale = _read(ARTIFACTS / "g6b-genesis-commentary-stale-set.json")
    assert stale["chapters"] == sorted(stale["chapters"], key=lambda item: int(item["reference"].split()[1]))
    assert {item["reference"] for item in stale["chapters"]} >= TARGET_CHAPTERS
    assert all(item["commentary_v1_2_frozen"] for item in stale["chapters"])
