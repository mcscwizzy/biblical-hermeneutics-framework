from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from framework.canonical_library.database_builder import build_database
from framework.canonical_library.lexicon_importer import import_normalized_lexicon_file
from framework.canonical_library.lexicon_models import WordStudyContext
from framework.canonical_library.lexicon_morphology import (
    decode_greek_morphology,
    decode_hebrew_morphology,
)
from framework.canonical_library.lexicon_normalization import (
    normalize_script_form,
    normalize_strongs_number,
    normalize_transliteration,
)
from framework.canonical_library.lexicon_repository import LexiconRepository

from .helpers import make_object, write_library


FIXTURE = Path("tests/fixtures/lexicon_phase1.json")


class LexiconSchemaAndRepositoryTests(unittest.TestCase):
    def test_generated_database_contains_lexical_tables_and_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ckl"
            database = Path(tmp) / "ckl.sqlite"
            write_library(root, [make_object("john", "book", "John", ["Gospel of John"])])
            build_database(root, database)

            conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
            try:
                tables = {
                    row[0]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
                }
                indexes = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex%'"
                    )
                }
            finally:
                conn.close()

        self.assertIn("lexicon_entries", tables)
        self.assertIn("verse_words", tables)
        self.assertIn("lexicon_sources", tables)
        self.assertIn("idx_lexicon_entries_strongs", indexes)
        self.assertIn("idx_verse_words_reference_position", indexes)

    def test_import_is_idempotent_and_repository_finds_exact_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = _build_test_database(Path(tmp))
            first = import_normalized_lexicon_file(database, FIXTURE, rebuild=True)
            second = import_normalized_lexicon_file(database, FIXTURE)

            self.assertEqual(first["entries"], 2)
            self.assertEqual(second["entries"], 2)
            conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
            try:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM lexicon_entries").fetchone()[0], 2)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM word_forms").fetchone()[0], 2)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM verse_words").fetchone()[0], 3)
            finally:
                conn.close()

            repository = LexiconRepository(database)
            try:
                hesed = repository.lookup_by_strongs("H02617")
                self.assertEqual(hesed[0].lemma, "חֶסֶד")
                self.assertEqual(hesed[0].senses[0].gloss, "steadfast love")
                self.assertEqual(repository.lookup_by_strongs("2617")[0].strongs_number, "H2617")
                self.assertEqual(repository.lookup_by_lemma("hebrew", "חסד")[0].strongs_number, "H2617")
                self.assertEqual(repository.lookup_by_lemma("greek", "λογος")[0].strongs_number, "G3056")
                self.assertEqual(repository.lookup_word_form("greek", "logos")[0].lemma, "λόγος")
                self.assertEqual(repository.get_word_at_position("Psalms", 23, 6, 1).surface_form, "חֶסֶד")
                self.assertEqual(len(repository.get_verse_words("Psalms", 23, 6)), 2)
                self.assertEqual(repository.find_occurrences("hebrew", "חֶסֶד", book="Psalms")[0].word_position, 1)
                self.assertEqual(repository.sources()[0].content_hash, repository.sources()[1].content_hash)
            finally:
                repository.close()

    def test_import_rolls_back_on_malformed_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            database = _build_test_database(tmp_path)
            bad_fixture = tmp_path / "bad.json"
            data = json.loads(FIXTURE.read_text(encoding="utf-8"))
            data["entries"][0].pop("lemma")
            bad_fixture.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "lemma"):
                import_normalized_lexicon_file(database, bad_fixture, rebuild=True)

            conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
            try:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM lexicon_sources").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM lexicon_entries").fetchone()[0], 0)
            finally:
                conn.close()

    def test_unicode_and_strongs_normalization(self) -> None:
        self.assertEqual(normalize_script_form("חֶסֶד", language="hebrew"), "חסד")
        self.assertEqual(normalize_script_form("λόγος", language="greek"), "λογοσ")
        self.assertEqual(normalize_script_form("λογος", language="greek"), "λογοσ")
        self.assertEqual(normalize_transliteration("ḥesed"), "hesed")
        self.assertEqual(normalize_strongs_number("G03056"), "G3056")
        self.assertEqual(normalize_strongs_number("3056"), "3056")

    def test_morphology_decoders_preserve_unknowns(self) -> None:
        hebrew_noun = decode_hebrew_morphology("Ncmsa")
        self.assertEqual(hebrew_noun["part_of_speech"], "noun")
        self.assertEqual(hebrew_noun["noun_type"], "common")
        self.assertEqual(hebrew_noun["gender"], "masculine")
        self.assertEqual(hebrew_noun["number"], "singular")
        self.assertEqual(hebrew_noun["state"], "absolute")

        hebrew_verb = decode_hebrew_morphology("Vqp3ms")
        self.assertEqual(hebrew_verb["part_of_speech"], "verb")
        self.assertEqual(hebrew_verb["stem"], "qal")
        self.assertEqual(hebrew_verb["conjugation"], "perfect")
        self.assertEqual(hebrew_verb["person"], "third")
        self.assertEqual(decode_hebrew_morphology("Afsd")["part_of_speech"], "adjective")
        self.assertEqual(decode_hebrew_morphology("P3ms")["part_of_speech"], "pronoun")
        self.assertEqual(decode_hebrew_morphology("C")["part_of_speech"], "conjunction")
        self.assertEqual(decode_hebrew_morphology("R")["part_of_speech"], "preposition")

        greek_noun = decode_greek_morphology("N-NSM")
        self.assertEqual(greek_noun["part_of_speech"], "noun")
        self.assertEqual(greek_noun["case"], "nominative")
        self.assertEqual(greek_noun["number"], "singular")
        self.assertEqual(greek_noun["gender"], "masculine")

        greek_verb = decode_greek_morphology("V-2AAI-3S")
        self.assertEqual(greek_verb["part_of_speech"], "verb")
        self.assertEqual(greek_verb["tense"], "aorist")
        self.assertEqual(greek_verb["voice"], "active")
        self.assertEqual(greek_verb["mood"], "indicative")
        self.assertEqual(greek_verb["person"], "third")
        greek_present = decode_greek_morphology("V-PAI-3S")
        self.assertEqual(greek_present["tense"], "present")
        self.assertEqual(greek_present["voice"], "active")
        self.assertEqual(greek_present["mood"], "indicative")
        self.assertEqual(decode_greek_morphology("A-NSM")["part_of_speech"], "adjective")
        self.assertEqual(decode_greek_morphology("RA----NSM")["part_of_speech"], "article")
        self.assertEqual(decode_greek_morphology("RP-NSM")["part_of_speech"], "pronoun")
        self.assertEqual(decode_greek_morphology("C---------")["part_of_speech"], "conjunction")
        self.assertEqual(decode_greek_morphology("P---------")["part_of_speech"], "preposition")

        self.assertEqual(decode_greek_morphology("?")["unknown_code"], "?")

    def test_word_study_prompt_context_is_compact_and_guarded(self) -> None:
        context = WordStudyContext(
            reference="Psalm 23:6",
            language="hebrew",
            surface_form="חֶסֶד",
            lemma="חֶסֶד",
            transliteration="ḥesed",
            strongs_number="H2617",
            morphology={"part_of_speech": "noun", "gender": "common", "number": "singular"},
            short_glosses=("steadfast love", "loyalty", "kindness"),
        )

        prompt = context.to_prompt_context(max_tokens=80)

        self.assertIn("LEXICAL CONTEXT", prompt)
        self.assertIn("Original form: חֶסֶד", prompt)
        self.assertIn("Strong's: H2617", prompt)
        self.assertIn("Do not import the entire semantic range", prompt)
        self.assertNotIn("tests/fixtures", prompt)


def _build_test_database(tmp_path: Path) -> Path:
    root = tmp_path / "ckl"
    database = tmp_path / "ckl.sqlite"
    write_library(root, [make_object("psalms", "book", "Psalms", ["Psalm"])])
    build_database(root, database)
    return database


if __name__ == "__main__":
    unittest.main()
