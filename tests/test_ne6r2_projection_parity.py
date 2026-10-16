from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.responses import JSONResponse

from bhf_agent.presentation.narrative_explorer import DomainLookup
from bhf_web.services.narrative_explorer import NarrativeExplorerService
from framework.canonical_library import CanonicalLibrary
from framework.canonical_library.database_builder import build_database, verify_database
from framework.canonical_library.sqlite_repository import SQLiteCanonicalLibrary


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CKL_ROOT = PROJECT_ROOT / "framework" / "canonical_library"
PILOT_SCOPES = (
    ("Genesis", 1, None, None),
    ("Genesis", 2, None, None),
    ("Genesis", 2, 8, 14),
    ("Genesis", 3, None, None),
    ("Genesis", 6, None, None),
    ("Genesis", 6, 1, 4),
    ("Deuteronomy", 32, None, None),
    ("Deuteronomy", 32, 8, 9),
    ("Psalm", 82, None, None),
    ("Exodus", 3, None, None),
    ("Exodus", 3, 1, 6),
    ("Acts", 7, None, None),
    ("Joshua", 1, None, None),
    ("Joshua", 1, 1, 9),
)


def _map_record(
    item_id: str,
    name: str,
    reference: str,
    *,
    coordinates: tuple[float, float] | None = (31.0, 35.0),
    identification_status: str | None = None,
    identification_confidence: str | None = None,
    dispute_status: str | None = None,
) -> dict[str, Any]:
    book, scope = reference.split(" ", 1)
    chapter_text, verse_text = scope.split(":", 1)
    start_text, _, end_text = verse_text.partition("-")
    record: dict[str, Any] = {
        "id": item_id,
        "name": name,
        "marker_kind": "place",
        "description": f"Stored map record for {name}.",
        "confidence": "high",
        "source_id": f"map-source-{item_id}",
        "source_name": "BHF map catalog fixture",
        "source_url": "https://example.test/map-source",
        "periods": ["Broad / uncertain period"],
        "related_references": [
            {
                "book": book,
                "chapter": int(chapter_text),
                "verse_start": int(start_text),
                "verse_end": int(end_text or start_text),
                "relationship_type": "contextual",
                "notes": "Stored passage anchor.",
            }
        ],
    }
    if coordinates is not None:
        record["latitude"], record["longitude"] = coordinates
    if identification_status is not None:
        record["physical_identification_status"] = identification_status
    if identification_confidence is not None:
        record["place_identification_confidence"] = identification_confidence
    if dispute_status is not None:
        record["dispute_status"] = dispute_status
    return record


def _maps_lookup(**request: Any) -> DomainLookup:
    book = request["book"]
    chapter = request["chapter"]
    records: list[dict[str, Any]] = []
    if book == "Genesis" and chapter in {2, 3}:
        reference = "Genesis 2:8-14" if chapter == 2 else "Genesis 3:8-24"
        records.append(
            _map_record(
                "eden",
                "Garden of Eden",
                reference,
                identification_status="unresolved",
                identification_confidence="unknown",
            )
        )
    elif book == "Exodus" and chapter == 3:
        records.append(
            _map_record(
                "horeb-sinai",
                "Horeb / Sinai",
                "Exodus 3:1-6",
                identification_status="disputed",
                identification_confidence="disputed",
                dispute_status="identification_uncertainty",
            )
        )
    elif book == "Acts" and chapter == 7:
        records.append(
            _map_record(
                "openbible-a012705",
                "Nile",
                "Acts 7:19",
                coordinates=None,
                identification_status="unresolved",
                identification_confidence="unknown",
            )
        )
    elif book == "Joshua" and chapter == 1:
        records.append(
            _map_record(
                "openbible-a1cb244",
                "Negeb",
                "Joshua 1:4",
            )
        )
    return DomainLookup(domain="maps", records=records, query_status="complete")


def _empty_archaeology_lookup(**_request: Any) -> DomainLookup:
    return DomainLookup(domain="archaeology", records=(), query_status="complete")


@pytest.fixture(scope="module")
def projection_sources(tmp_path_factory: pytest.TempPathFactory):
    work_dir = tmp_path_factory.mktemp("ne6r2-parity")
    index_path = work_dir / "ckl.sqlite"
    build_database(CKL_ROOT, index_path)
    index_report = verify_database(index_path, root=CKL_ROOT)
    json_library = CanonicalLibrary(root=CKL_ROOT).load()
    sqlite_library = SQLiteCanonicalLibrary.from_path(index_path, root=CKL_ROOT)
    json_service = NarrativeExplorerService(
        study_db_path=work_dir / "unused-study.sqlite",
        canonical_library_provider=lambda: json_library,
        maps_lookup_provider=_maps_lookup,
        archaeology_lookup_provider=_empty_archaeology_lookup,
    )
    sqlite_service = NarrativeExplorerService(
        study_db_path=work_dir / "unused-study.sqlite",
        canonical_library_provider=lambda: sqlite_library,
        maps_lookup_provider=_maps_lookup,
        archaeology_lookup_provider=_empty_archaeology_lookup,
    )
    try:
        yield json_service, sqlite_service, index_report
    finally:
        sqlite_library.close()


def test_indexed_and_json_narrative_projections_have_exact_serialized_parity(projection_sources) -> None:
    json_service, sqlite_service, index_report = projection_sources

    assert index_report["database_schema_version"] == "4"
    assert index_report["retrieval_index_version"] == "3"
    assert index_report["source_manifest_fingerprint"]
    assert index_report["source_inventory_signature"]

    comparisons: list[tuple[str, int, int | None, int | None, str]] = []
    for book, chapter, verse_start, verse_end in PILOT_SCOPES:
        json_projection = json_service.build(
            book,
            chapter,
            verse_start=verse_start,
            verse_end=verse_end,
        )
        sqlite_projection = sqlite_service.build(
            book,
            chapter,
            verse_start=verse_start,
            verse_end=verse_end,
        )
        json_bytes = JSONResponse(json_projection).body
        sqlite_bytes = JSONResponse(sqlite_projection).body
        assert json.loads(sqlite_bytes) == json.loads(json_bytes), (
            f"projection field mismatch for {book} {chapter}:{verse_start}-{verse_end}"
        )
        canonical_json = json.dumps(
            json_projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        canonical_sqlite = json.dumps(
            sqlite_projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        assert canonical_sqlite == canonical_json, (
            f"canonical serialized projection mismatch for {book} {chapter}:{verse_start}-{verse_end}"
        )
        comparisons.append(
            (book, chapter, verse_start, verse_end, hashlib.sha256(canonical_sqlite).hexdigest())
        )

    assert len(comparisons) == len(PILOT_SCOPES)
