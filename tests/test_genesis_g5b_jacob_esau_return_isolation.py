"""G5B Genesis 31–36 object, provenance, synthesis, and isolation gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bhf_agent.chapter_commentary import evidence_bundling
from framework.canonical_library.loader import CanonicalLibrary
from framework.canonical_library.schema import validate_base_object
from framework.commentary.production.inputs import prepare_chapter


ROOT = Path(__file__).resolve().parents[1]
CKL_ROOT = ROOT / "framework/canonical_library"
ARTIFACTS = ROOT / ".bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion"
OBJECT_ID = "genesis-jacob-esau-return-context"
OBJECT_PATH = CKL_ROOT / "objects/cultural_background/genesis-jacob-esau-return-context.json"
TARGET_CHAPTERS = {f"Genesis {chapter}" for chapter in range(31, 37)}
CONTROLS = {
    "Genesis 1", "Genesis 5", "Genesis 6", "Genesis 9", "Genesis 10", "Genesis 11",
    "Genesis 12", "Genesis 15", "Genesis 17", "Genesis 18", "Genesis 22", "Genesis 25",
    "Genesis 26", "Genesis 28", "Genesis 30", "Genesis 37", "Genesis 38", "Genesis 50",
    "Isaiah 36", "Acts 16", "Revelation 18", "Exodus 25", "1 Kings 6", "Revelation 12",
}


def _read(path: Path):
    return json.loads(path.read_text())


_LIBRARY = None


def _library():
    global _LIBRARY
    if _LIBRARY is None:
        _LIBRARY = CanonicalLibrary(root=CKL_ROOT).load()
        evidence_bundling._CANONICAL_LIBRARY_CACHE = _LIBRARY
    return _LIBRARY


def _owner_rows(objects):
    return sorted(
        ((str(obj.get("id") or ""), str(source.get("id") or ""))
         for obj in objects
         for source in obj.get("sources", []) or []
         if source.get("id")),
        key=lambda row: row,
    )


def _owner_hash(rows):
    payload = [{"owner": owner, "source_id": source_id} for owner, source_id in rows]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()


def test_g5b_object_and_candidates_are_passage_scoped_and_synthesis_usable():
    library = _library()
    assert OBJECT_PATH.is_file()
    production = _read(OBJECT_PATH)
    obj = library.objects_by_id[OBJECT_ID]
    packet = _read(ARTIFACTS / "g5b-candidate-evidence.json")
    production_items = {item["id"]: item for item in production["evidence_items"]}
    candidate_items = {
        candidate["evidence_item"]["id"]: candidate["evidence_item"]
        for candidate in packet["candidates"]
    }

    assert obj.type == "cultural_background"
    assert validate_base_object(production, path=OBJECT_PATH)
    assert candidate_items == production_items
    assert packet["candidate_count"] == len(production_items) == 68
    assert packet["target_object_id"] == OBJECT_ID

    source_ids = {source.id for source in obj.sources}
    assert source_ids == {source["id"] for source in production["sources"]}
    for item in production["evidence_items"]:
        assert item["source_ids"]
        assert set(item["source_ids"]) <= source_ids
        assert item["scripture_references"]
        for ref in item["scripture_references"]:
            assert ref["relationship"] == "direct"
            assert ref["reference"].startswith(tuple(f"Genesis {chapter}:" for chapter in range(31, 37)))

    assert {
        int(ref.reference.split()[1].split(":")[0]) for ref in obj.scripture_references
    } == set(range(31, 37))
    for chapter in range(31, 37):
        prepared = prepare_chapter("Genesis", chapter)
        bundled = {item.id for item in prepared.bundle.evidence_items}
        synthesized = {
            evidence_id
            for unit in prepared.synthesis.synthesis_units
            for evidence_id in unit.evidence_ids
        }
        chapter_ids = {
            item_id for item_id, item in production_items.items()
            if item["scripture_references"][0]["reference"].startswith(f"Genesis {chapter}:")
        }
        assert chapter_ids <= bundled
        assert chapter_ids <= synthesized


def test_g5b_sources_are_local_and_historical_owner_rows_are_unchanged():
    library = _library()
    obj = library.objects_by_id[OBJECT_ID]
    audit = _read(ARTIFACTS / "g5b-source-ownership-audit.json")
    assert audit["existing_historical_source_owner_rows_changed"] == 0
    assert audit["post_apply_audit"]["result"] == "PASS"

    fields = ("title", "author", "publisher", "year", "locator", "url", "source_type")
    for alias in audit["source_aliases"]:
        local = next(source for source in obj.sources if source.id == alias["local_source_id"])
        historical = next(
            source
            for other_id, other in library.objects_by_id.items()
            if other_id != OBJECT_ID
            for source in other.sources
            if source.id == alias["historical_source_id"]
        )
        assert all(getattr(local, field) == getattr(historical, field) for field in fields)
        assert alias["historical_source_id"] in local.notes
        assert "same publication/work" in local.notes

    historical_objects = [
        json.loads(path.read_text())
        for path in CKL_ROOT.joinpath("objects").rglob("*.json")
        if json.loads(path.read_text()).get("id") != OBJECT_ID
    ]
    before = _read(ARTIFACTS / "g5b-existing-evidence-audit.json")["historical_source_owner_rows"]
    current_rows = _owner_rows(historical_objects)
    assert len(current_rows) == before["count"] == 5181
    assert _owner_hash(current_rows) == before["sha256"]


def test_g5b_links_are_typed_one_way_and_context_is_not_an_applicability_anchor():
    library = _library()
    obj = library.objects_by_id[OBJECT_ID]
    audit = _read(ARTIFACTS / "g5b-comparative-applicability-audit.json")
    assert audit["result"] == "PASS"
    assert audit["comparative_or_later_passages_used_as_applicability_anchors"] == []
    assert audit["reverse_applicability_created"] is False
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


def test_g5b_all_1189_identities_controls_and_frozen_commentary_match_contract():
    _library()
    impact = _read(ARTIFACTS / "g5b-chapter-impact.json")
    post = _read(ARTIFACTS / "g5b-post-apply-validation.json")
    assert impact["base_chapter_count"] == 1189
    assert post["changed_chapters"] == sorted(
        TARGET_CHAPTERS, key=lambda value: int(value.rsplit(" ", 1)[1])
    )
    assert post["whole_corpus_exact_set_pass"] is True
    assert set(post["controls"]) == CONTROLS
    assert all(post["controls"].values())

    frozen = _read(ARTIFACTS / "g5b-existing-evidence-audit.json")["base_commentary_v1_2_identity"]
    release_dir = ROOT / ".bhf-data/bhf-commentary-v1.2"
    manifest = _read(release_dir / ".bhf-commentary-release.json")
    checksum_path = release_dir / ".bhf-commentary-release-checksums.json"
    assert manifest["manifest_identity"] == frozen["manifest_identity"]
    assert hashlib.sha256(checksum_path.read_bytes()).hexdigest() == frozen["checksum_index_sha256"]
