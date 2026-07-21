from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from framework.canonical_library.database_builder import build_database
from framework.canonical_library.lexicon_repository import LexiconRepository
from framework.canonical_library.lexicon_source_importer import (
    import_source_manifest,
    normalized_payload_from_source_manifest,
)

from .helpers import make_object, write_library


class LexiconSourceImporterTests(unittest.TestCase):
    def test_source_manifest_imports_local_json_and_tsv_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            database = _build_test_database(tmp_path)
            manifest = _write_source_manifest(tmp_path)

            payload, content_hash = normalized_payload_from_source_manifest(manifest)

            self.assertEqual(len(payload["sources"]), 2)
            self.assertEqual(payload["entries"][0]["strongs_number"], "G3056")
            self.assertEqual(payload["verse_words"][0]["surface_form"], "λόγος")
            self.assertEqual(len(content_hash), 64)

            counts = import_source_manifest(database, manifest, rebuild=True)

            self.assertEqual(counts["sources"], 2)
            self.assertEqual(counts["entries"], 1)
            self.assertEqual(counts["verse_words"], 1)

            repository = LexiconRepository(database)
            try:
                self.assertEqual(repository.lookup_by_strongs("G03056")[0].lemma, "λόγος")
                word = repository.get_word_at_position("John", 1, 1, 3)
                self.assertIsNotNone(word)
                self.assertEqual(word.surface_form, "λόγος")
                self.assertEqual(word.morphology["part_of_speech"], "noun")
            finally:
                repository.close()

    def test_source_manifest_rejects_missing_license_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifest = _write_source_manifest(tmp_path)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["sources"][0].pop("license")
            manifest.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "license"):
                normalized_payload_from_source_manifest(manifest)


def _build_test_database(tmp_path: Path) -> Path:
    root = tmp_path / "ckl"
    database = tmp_path / "ckl.sqlite"
    write_library(root, [make_object("john", "book", "John", ["Gospel of John"])])
    build_database(root, database)
    return database


def _write_source_manifest(tmp_path: Path) -> Path:
    lexicon_path = tmp_path / "greek-strongs.json"
    lexicon_path.write_text(
        json.dumps(
            [
                {
                    "language": "greek",
                    "lemma": "λόγος",
                    "transliteration": "logos",
                    "strongs": "G03056",
                    "pos": "noun",
                    "glosses": ["word", "message", "account"],
                    "definition": "Concise local fixture definition.",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    verse_words_path = tmp_path / "morphgnt.tsv"
    verse_words_path.write_text(
        "\t".join(
            [
                "book",
                "chapter",
                "verse",
                "word_position",
                "language",
                "surface_form",
                "lemma",
                "transliteration",
                "strongs_number",
                "morphology_code",
                "source_word_id",
            ]
        )
        + "\n"
        + "\t".join(
            [
                "John",
                "1",
                "1",
                "3",
                "greek",
                "λόγος",
                "λόγος",
                "logos",
                "G3056",
                "N-NSM",
                "jn1-1-w3",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "sources": [
            {
                "name": "local-greek-strongs",
                "kind": "openscriptures_strongs_json",
                "path": str(lexicon_path.name),
                "repository_url": "https://example.invalid/greek-strongs",
                "revision": "fixture-revision",
                "license": "test-license",
                "attribution": "Test fixture",
                "redistribution_status": "test-only",
            },
            {
                "name": "local-morphgnt",
                "kind": "morphgnt_tsv",
                "path": str(verse_words_path.name),
                "repository_url": "https://example.invalid/morphgnt",
                "revision": "fixture-revision",
                "license": "test-license",
                "attribution": "Test fixture",
                "redistribution_status": "test-only",
            },
        ]
    }
    manifest_path = tmp_path / "lexicon-sources.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


if __name__ == "__main__":
    unittest.main()
