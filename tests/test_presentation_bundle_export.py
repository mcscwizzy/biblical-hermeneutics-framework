from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from bhf_agent.presentation import (
    PresentationBundleExportError,
    SQLitePresentationCache,
    build_evidence_bundle,
    deterministic_presentation,
    export_cached_presentations,
    load_presentation_bundle,
    presentation_cache_key_for_versions,
)


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "export_presentation_bundle.py"


def _cached_packet():
    bundle = build_evidence_bundle(
        "Mark 5:1",
        geography={
            "places": [
                {
                    "id": "gerasa",
                    "title": "Gerasa",
                    "summary": "Gerasa lies east of the Sea of Galilee.",
                    "confidence": "likely",
                }
            ],
            "routes": [],
        },
    )
    packet = deterministic_presentation(bundle).to_dict()
    metadata = packet["generated_from"]
    cache_key = presentation_cache_key_for_versions(
        passage_ref=packet["passage_ref"],
        evidence_hash=metadata["evidence_hash"],
        evidence_bundle_version=metadata["evidence_bundle_version"],
        presentation_schema_version=metadata["presentation_schema_version"],
        prompt_version=metadata["prompt_version"],
    )
    return cache_key, packet


def test_exported_cache_round_trips_through_bundle_loader(tmp_path):
    cache_path = tmp_path / "presentation.sqlite"
    output_path = tmp_path / "deployment" / "presentation-bundle.json"
    cache_key, packet = _cached_packet()
    cache = SQLitePresentationCache(cache_path)
    cache.put(cache_key, packet)

    result = export_cached_presentations(cache_path, output_path)
    loaded = load_presentation_bundle(output_path)

    assert result.output_path == output_path
    assert result.packet_count == 1
    assert result.byte_count == output_path.stat().st_size
    assert loaded == {cache_key: packet}
    assert cache.entries_for_export() == [(cache_key, packet)]


def test_export_refuses_overwrite_unless_force_is_explicit(tmp_path):
    cache_path = tmp_path / "presentation.sqlite"
    output_path = tmp_path / "presentation-bundle.json"
    cache_key, packet = _cached_packet()
    SQLitePresentationCache(cache_path).put(cache_key, packet)
    output_path.write_text("keep me", encoding="utf-8")

    with pytest.raises(PresentationBundleExportError, match="pass --force"):
        export_cached_presentations(cache_path, output_path)

    assert output_path.read_text(encoding="utf-8") == "keep me"
    result = export_cached_presentations(cache_path, output_path, force=True)
    assert result.packet_count == 1
    assert load_presentation_bundle(output_path) == {cache_key: packet}


def test_export_rejects_missing_or_empty_cache(tmp_path):
    missing = tmp_path / "missing.sqlite"
    output_path = tmp_path / "presentation-bundle.json"

    with pytest.raises(PresentationBundleExportError, match="does not exist"):
        export_cached_presentations(missing, output_path)

    empty = SQLitePresentationCache(tmp_path / "empty.sqlite")
    cache_key, packet = _cached_packet()
    empty.put(cache_key, packet)
    empty.discard(cache_key)
    with pytest.raises(PresentationBundleExportError, match="no packets"):
        export_cached_presentations(empty.path, output_path)
    assert not output_path.exists()


def test_export_reports_corrupt_cache_without_mutating_it(tmp_path):
    cache_path = tmp_path / "presentation.sqlite"
    output_path = tmp_path / "presentation-bundle.json"
    cache_key, packet = _cached_packet()
    cache = SQLitePresentationCache(cache_path)
    cache.put(cache_key, packet)
    with sqlite3.connect(cache_path) as connection:
        connection.execute(
            "UPDATE presentation_packets SET packet_json = ? WHERE cache_key = ?",
            ("{", cache_key),
        )

    with pytest.raises(PresentationBundleExportError, match="not valid JSON"):
        export_cached_presentations(cache_path, output_path)

    assert not output_path.exists()
    with sqlite3.connect(cache_path) as connection:
        encoded = connection.execute(
            "SELECT packet_json FROM presentation_packets WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()[0]
    assert encoded == "{"


def test_export_rejects_cache_key_that_does_not_match_packet_metadata(tmp_path):
    cache_path = tmp_path / "presentation.sqlite"
    output_path = tmp_path / "presentation-bundle.json"
    _, packet = _cached_packet()
    SQLitePresentationCache(cache_path).put("0" * 64, packet)

    with pytest.raises(PresentationBundleExportError, match="fingerprint"):
        export_cached_presentations(cache_path, output_path)

    assert not output_path.exists()


def test_export_never_replaces_its_source_cache_even_with_force(tmp_path):
    cache_path = tmp_path / "presentation.sqlite"
    cache_key, packet = _cached_packet()
    cache = SQLitePresentationCache(cache_path)
    cache.put(cache_key, packet)

    with pytest.raises(PresentationBundleExportError, match="source"):
        export_cached_presentations(cache_path, cache_path, force=True)

    assert cache.entries_for_export() == [(cache_key, packet)]


def test_export_cli_is_offline_and_round_trip_verifies_written_bundle(tmp_path):
    cache_path = tmp_path / "presentation.sqlite"
    output_path = tmp_path / "presentation-bundle.json"
    cache_key, packet = _cached_packet()
    SQLitePresentationCache(cache_path).put(cache_key, packet)

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--cache",
            str(cache_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "exported 1 packet(s)" in completed.stdout
    assert load_presentation_bundle(output_path) == {cache_key: packet}
