"""G4A Genesis 12–17 isolation, provenance, and applicability checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bhf_agent.chapter_commentary import evidence_bundling
from framework.canonical_library.loader import CanonicalLibrary
from framework.commentary.production.inputs import prepare_chapter


ROOT = Path(__file__).resolve().parents[1]
CKL_ROOT = ROOT / "framework/canonical_library"
ARTIFACTS = ROOT / ".bhf-data/bhf-commentary-candidates/genesis-g4a-abraham-call-covenant-evidence-expansion"
OBJECT_ID = "genesis-abraham-call-covenant-context"
OBJECT_PATH = CKL_ROOT / "objects/cultural_background/genesis-abraham-call-covenant-context.json"
TARGET_CHAPTERS = {f"Genesis {chapter}" for chapter in range(12, 18)}


def _read(path: Path):
    return json.loads(path.read_text())


def _identity(prepared):
    return {
        "evidence_count": prepared.row["evidence_count"],
        "evidence_hash": prepared.row["input_identity"]["evidence_hash"],
        "synthesis_unit_count": prepared.row["synthesis_unit_count"],
        "synthesis_hash": prepared.row["input_identity"]["synthesis_hash"],
    }


_LIBRARY = None


def _library():
    global _LIBRARY
    if _LIBRARY is None:
        _LIBRARY = CanonicalLibrary(root=CKL_ROOT).load()
    evidence_bundling._CANONICAL_LIBRARY_CACHE = _LIBRARY
    return _LIBRARY


def test_g4a_object_and_candidate_queue_are_passage_scoped_and_synthesis_usable():
    library = _library()
    assert OBJECT_PATH.is_file()
    obj = library.objects_by_id[OBJECT_ID]
    production = _read(OBJECT_PATH)
    packet = _read(ARTIFACTS / "g4a-candidate-evidence.json")
    production_items = {item["id"]: item for item in production["evidence_items"]}
    candidate_items = {
        candidate["evidence_item"]["id"]: candidate["evidence_item"]
        for candidate in packet["candidates"]
    }

    assert obj.type == "cultural_background"
    assert len(obj.evidence_items) == 46
    assert candidate_items == production_items
    assert packet["candidate_replay"]["result"] == "PASS"
    assert packet["candidate_replay"]["changed_chapters"] == sorted(
        TARGET_CHAPTERS, key=lambda value: int(value.rsplit(" ", 1)[1])
    )

    allowed = {f"Genesis {chapter}:" for chapter in range(12, 18)}
    for item in production["evidence_items"]:
        assert item["source_ids"]
        assert set(item["source_ids"]) <= {source.id for source in obj.sources}
        assert item["scripture_references"]
        assert all(ref["relationship"] == "direct" for ref in item["scripture_references"])
        assert all(ref["reference"].startswith(tuple(allowed)) for ref in item["scripture_references"])

    for chapter in range(12, 18):
        prepared = prepare_chapter("Genesis", chapter)
        bundled = {item.id for item in prepared.bundle.evidence_items}
        synthesized = {
            evidence_id
            for unit in prepared.synthesis.synthesis_units
            for evidence_id in unit.evidence_ids
        }
        chapter_ids = {
            item_id
            for item_id in production_items
            if any(ref["reference"].startswith(f"Genesis {chapter}:") for ref in production_items[item_id]["scripture_references"])
        }
        assert chapter_ids <= bundled
        assert chapter_ids <= synthesized


def test_g4a_sources_are_local_and_historical_owner_rows_are_unchanged():
    library = _library()
    obj = library.objects_by_id[OBJECT_ID]
    audit = _read(ARTIFACTS / "g4a-source-ownership-audit.json")
    assert audit["existing_historical_source_owner_rows_changed"] == 0
    assert audit["post_apply_audit"]["result"] == "PASS"
    assert len(obj.sources) == 17

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
        assert "same publication/work" in local.notes or "same work" in local.notes

    local_ids = {source.id for source in obj.sources}
    historical_ids = {
        source.id
        for other_id, other in library.objects_by_id.items()
        if other_id != OBJECT_ID
        for source in other.sources
    }
    assert local_ids.isdisjoint(historical_ids)


def test_g4a_links_are_one_way_and_comparative_reception_is_context_only():
    library = _library()
    obj = library.objects_by_id[OBJECT_ID]
    audit = _read(ARTIFACTS / "g4a-comparative-applicability-audit.json")
    assert audit["result"] == "PASS"
    assert audit["comparative_or_later_passages_used_as_applicability_anchors"] == []
    assert audit["reverse_applicability_created"] is False
    assert {ref.reference for ref in obj.scripture_references} == {
        "Genesis 12:1-20",
        "Genesis 13:1-18",
        "Genesis 14:1-24",
        "Genesis 15:1-21",
        "Genesis 16:1-16",
        "Genesis 17:1-27",
    }
    assert all(target.id in library.objects_by_id for target in obj.related_objects)
    assert not any(
        relationship.id == OBJECT_ID
        for other_id, other in library.objects_by_id.items()
        if other_id != OBJECT_ID
        for relationship in other.related_objects
    )


def test_g4a_all_1189_chapter_identities_and_frozen_commentary_match_contract():
    _library()
    impact = _read(ARTIFACTS / "g4a-chapter-impact.json")
    post = _read(ARTIFACTS / "g4a-post-apply-validation.json")
    assert impact["base_chapter_count"] == 1189
    assert post["changed_chapters"] == sorted(
        TARGET_CHAPTERS, key=lambda value: int(value.rsplit(" ", 1)[1])
    )
    assert post["whole_corpus_exact_set_pass"] is True
    assert all(post["controls"].values())

    frozen = _read(ARTIFACTS / "g4a-existing-evidence-audit.json")["base_commentary_v1_2_identity"]
    release_dir = ROOT / ".bhf-data/bhf-commentary-v1.2"
    manifest = _read(release_dir / ".bhf-commentary-release.json")
    checksum_path = release_dir / ".bhf-commentary-release-checksums.json"
    assert manifest["manifest_identity"] == frozen["manifest_identity"]
    assert hashlib.sha256(checksum_path.read_bytes()).hexdigest() == frozen["checksum_index_sha256"]


def test_g4a_keeps_genesis_one_legacy_theme_fallback_exact():
    prepared = prepare_chapter("Genesis", 1)
    fallback_ids = {
        item.id
        for item in prepared.bundle.evidence_items
        if item.relevance_metadata.get("parent_object_id") == "image-of-god-theme"
        and item.relevance_metadata.get("source_kind") == "ckl_legacy_field"
    }
    assert fallback_ids == {
        "image-of-god-theme:ancient_near_east_context:0",
        "image-of-god-theme:hebraic_worldview:0",
        "image-of-god-theme:historical_context:0",
        "image-of-god-theme:second_temple_context:0",
    }
    g4a_ids = {item.id for item in _library().objects_by_id[OBJECT_ID].evidence_items}
    assert not g4a_ids.intersection(item.id for item in prepared.bundle.evidence_items)
