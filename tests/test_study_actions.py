import unittest
import tempfile
from pathlib import Path

from bhf_agent.lexicon import LexiconRepository, WordStudyService
from bhf_agent.study_actions import (
    DeterministicStudyEngine,
    StudyActionRouter,
    compact_fact_packet,
    format_fact_packet_for_prompt,
    normalize_action,
)
from framework.canonical_library import CanonicalLibrary
from framework.canonical_library.database_builder import build_database
from framework.canonical_library.lexicon_importer import import_normalized_lexicon_file
from framework.lexical.tools.build_lexicon_database import build_lexicon_database
from framework.lexical.tools.import_verse_tokens import import_verse_tokens, read_morphgnt, read_oshb_osis

from tests.canonical_library.helpers import make_object, write_library


LEXICON_FIXTURE = Path("tests/fixtures/lexicon_phase1.json")


class StudyActionRouterTests(unittest.TestCase):
    def test_context_action_returns_structured_result_without_agent(self):
        result = StudyActionRouter().execute(
            "historical_context",
            passage={
                "book": "John",
                "chapter": 1,
                "start_verse": 1,
                "end_verse": 3,
                "translation": "asv",
            },
        )

        self.assertEqual(result.action, "historical_context")
        self.assertIn(result.status, {"complete", "partial"})
        self.assertIn(result.source, {"scripture", "ckl", "scripture_and_ckl"})
        self.assertGreaterEqual(len(result.sections), 1)
        self.assertEqual(result.metadata["reference"], "John 1:1-3")
        self.assertTrue(result.agent_fallback_allowed)

    def test_reference_actions_are_deterministic_only(self):
        result = StudyActionRouter().execute(
            "people",
            passage={"book": "John", "chapter": 1, "start_verse": 1, "end_verse": 3},
        )

        self.assertEqual(result.action, "people")
        self.assertFalse(result.agent_fallback_allowed)
        self.assertTrue(result.metadata["deterministic_only"])

    def test_related_ot_themes_aliases_to_themes(self):
        self.assertEqual(normalize_action("related_ot_themes"), "themes")

    def test_compact_fact_packet_has_agent_safe_shape(self):
        result = StudyActionRouter().execute(
            "literary_context",
            passage={"book": "John", "chapter": 1, "start_verse": 1, "end_verse": 3},
        )

        packet = compact_fact_packet(result)

        self.assertEqual(packet["action"], "literary_context")
        self.assertIn("sections", packet)
        self.assertIn("metadata", packet)
        self.assertIn("reference", packet["metadata"])

    def test_word_study_service_resolves_john_1_1_logos(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = _build_lexicon_database(Path(tmp))
            service = WordStudyService(repository=LexiconRepository(database))

            result = service.build_word_study(
                {
                    "book": "John",
                    "chapter": 1,
                    "start_verse": 1,
                    "reference": "John 1:1",
                    "selected_text": "Word",
                }
            )

            self.assertEqual(result.status, "complete")
            self.assertEqual(result.surface_form, "λόγος")
            self.assertEqual(result.lemma, "λόγος")
            self.assertEqual(result.strongs_number, "G3056")
            self.assertIn("word", result.lexical_range)
            self.assertIn("test-morphgnt", {source["name"] for source in result.sources})
            self.assertIn("LEXICAL CONTEXT", result.prompt_context)

    def test_word_study_service_resolves_psalm_23_6_hesed_by_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = _build_lexicon_database(Path(tmp))
            service = WordStudyService(repository=LexiconRepository(database))

            result = service.build_word_study(
                {
                    "book": "Psalms",
                    "chapter": 23,
                    "start_verse": 6,
                    "reference": "Psalm 23:6",
                    "word_position": 1,
                }
            )

            self.assertEqual(result.status, "complete")
            self.assertEqual(result.surface_form, "חֶסֶד")
            self.assertEqual(result.lemma, "חֶסֶד")
            self.assertEqual(result.strongs_number, "H2617")
            self.assertEqual(result.morphology["part_of_speech"], "noun")

    def test_word_study_service_resolves_proverbs_1_1_from_installed_lexical_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "hebrew.xml"
            source.write_text(
                """<lexicon>
                  <entry id="H2451">
                    <lemma>חָכְמָה</lemma>
                    <transliteration>ḥokmāh</transliteration>
                    <definition>Wisdom and skill for rightly ordered living.</definition>
                    <part_of_speech>noun</part_of_speech>
                  </entry>
                </lexicon>""",
                encoding="utf-8",
            )
            database = root / "lexicon.sqlite"
            build_lexicon_database(hebrew=source, output=database)
            service = WordStudyService(database_path=database)

            result = service.build_word_study(
                {
                    "book": "Proverbs",
                    "chapter": 1,
                    "start_verse": 1,
                    "reference": "Proverbs 1:1",
                    "language": "hebrew",
                    "lemma": "חָכְמָה",
                }
            )

            self.assertEqual(result.status, "complete")
            self.assertEqual(result.reference, "Proverbs 1:1")
            self.assertEqual(result.language, "hebrew")
            self.assertEqual(result.lemma, "חָכְמָה")
            self.assertEqual(result.strongs_number, "H2451")
            self.assertEqual(result.lexical_entries[0].source, "Open Scriptures Hebrew Lexicon")

    def test_word_study_service_resolves_genesis_from_standalone_verse_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "hebrew.xml"
            source.write_text(
                """<lexicon>
                  <entry id="H7225">
                    <lemma>רֵאשִׁית</lemma>
                    <transliteration>reshith</transliteration>
                    <definition>Beginning, first, or chief part.</definition>
                    <part_of_speech>noun</part_of_speech>
                  </entry>
                </lexicon>""",
                encoding="utf-8",
            )
            database = root / "lexicon.sqlite"
            build_lexicon_database(hebrew=source, output=database)
            osis = root / "Gen.xml"
            osis.write_text(
                """<?xml version="1.0" encoding="UTF-8"?>
                <osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace">
                  <osisText>
                    <div type="book" osisID="Gen">
                      <chapter osisID="Gen.1">
                        <verse osisID="Gen.1.1">
                          <w lemma="b/7225" n="1.0" morph="HR/Ncfsa" id="01xeN">בְּ/רֵאשִׁ֖ית</w>
                        </verse>
                      </chapter>
                    </div>
                  </osisText>
                </osis>""",
                encoding="utf-8",
            )
            import_verse_tokens(
                database,
                source={
                    "name": "test-oshb",
                    "revision": "fixture",
                    "license": "CC BY 4.0",
                    "attribution": "Fixture OSHB-style data.",
                },
                verse_words=read_oshb_osis(osis),
            )
            service = WordStudyService(database_path=database)

            result = service.build_word_study(
                {"book": "Genesis", "chapter": 1, "start_verse": 1, "reference": "Genesis 1:1"}
            )

            self.assertEqual(result.status, "complete")
            self.assertEqual(result.surface_form, "בְּ/רֵאשִׁ֖ית")
            self.assertEqual(result.strongs_number, "H7225")
            self.assertEqual(result.lemma, "רֵאשִׁית")

    def test_word_study_service_resolves_morphgnt_tokens_by_lemma(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "greek.xml"
            source.write_text(
                """<dictionary xmlns="urn:test">
                  <entry strongs="G3056">
                    <word>λόγος</word>
                    <translit>logos</translit>
                    <strongs_def>word, message, or account.</strongs_def>
                    <morphology>noun</morphology>
                  </entry>
                </dictionary>""",
                encoding="utf-8",
            )
            database = root / "lexicon.sqlite"
            build_lexicon_database(greek=source, output=database)
            morphgnt = root / "64-Jn-morphgnt.txt"
            morphgnt.write_text(
                "\n".join(
                    [
                        "040101 P- -------- Ἐν Ἐν ἐν ἐν",
                        "040101 N- ----DSF- ἀρχῇ ἀρχῇ ἀρχῇ ἀρχή",
                        "040101 V- 3IAI-S-- ἦν ἦν ἦν εἰμί",
                        "040101 RA ----NSM- ὁ ὁ ὁ ὁ",
                        "040101 N- ----NSM- λόγος, λόγος λόγος λόγος",
                    ]
                ),
                encoding="utf-8",
            )
            import_verse_tokens(
                database,
                source={
                    "name": "test-morphgnt",
                    "revision": "fixture",
                    "license": "CC BY-SA 3.0",
                    "attribution": "Fixture MorphGNT-style data.",
                },
                verse_words=read_morphgnt(morphgnt),
            )
            service = WordStudyService(database_path=database)

            result = service.build_word_study(
                {
                    "book": "John",
                    "chapter": 1,
                    "start_verse": 1,
                    "reference": "John 1:1",
                    "word_position": 5,
                }
            )

            self.assertEqual(result.status, "complete")
            self.assertEqual(result.surface_form, "λόγος")
            self.assertEqual(result.lemma, "λόγος")
            self.assertEqual(result.strongs_number, "G3056")

    def test_word_study_action_returns_unavailable_for_imported_token_without_lexicon_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "greek.xml"
            source.write_text(
                """<dictionary xmlns="urn:test">
                  <entry strongs="G3056">
                    <word>λόγος</word>
                    <translit>logos</translit>
                    <strongs_def>word, message, or account.</strongs_def>
                  </entry>
                </dictionary>""",
                encoding="utf-8",
            )
            database = root / "lexicon.sqlite"
            build_lexicon_database(greek=source, output=database)
            import_verse_tokens(
                database,
                source={
                    "name": "incomplete-imported-tokens",
                    "revision": "fixture",
                    "license": "CC BY 4.0",
                    "attribution": "Fixture token data.",
                },
                verse_words=[
                    {
                        "book": "John",
                        "chapter": 1,
                        "verse": 2,
                        "word_position": 1,
                        "language": "greek",
                        "surface_form": "φαντασία",
                        "lemma": "φαντασία",
                        "strongs_number": "G9999",
                        "morphology_code": "N-NSF",
                    }
                ],
            )
            write_library(root / "ckl", [make_object("john", "book", "John", ["Gospel of John"])])
            library = CanonicalLibrary(root=root / "ckl").load()
            service = WordStudyService(database_path=database)
            router = StudyActionRouter(DeterministicStudyEngine(library, word_study_service=service))

            result = router.execute(
                "word_study",
                passage={
                    "book": "John",
                    "chapter": 1,
                    "start_verse": 2,
                    "end_verse": 2,
                    "word_position": 1,
                },
            )

            self.assertEqual(result.status, "unavailable")
            self.assertFalse(result.agent_fallback_allowed)
            self.assertEqual(result.metadata["word_study"]["status"], "unavailable")
            self.assertIn("no lexicon entry resolved", result.metadata["word_study"]["message"])

    def test_word_study_action_uses_sqlite_lexical_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            database = _build_lexicon_database(tmp_path)
            library = CanonicalLibrary(root=tmp_path / "ckl").load()
            service = WordStudyService(repository=LexiconRepository(database))
            router = StudyActionRouter(DeterministicStudyEngine(library, word_study_service=service))

            result = router.execute(
                "word_study",
                passage={
                    "book": "John",
                    "chapter": 1,
                    "start_verse": 1,
                    "end_verse": 1,
                    "selected_text": "Word",
                },
            )

            self.assertEqual(result.status, "complete")
            self.assertTrue(result.agent_fallback_allowed)
            self.assertEqual(result.metadata["word_study"]["strongs_number"], "G3056")
            self.assertTrue(any(section["title"] == "Original Word" for section in result.sections))
            packet = compact_fact_packet(result)
            prompt = format_fact_packet_for_prompt(packet)
            self.assertIn("LEXICAL CONTEXT", prompt)
            self.assertIn("Strong's: G3056", prompt)

    def test_word_study_action_reports_ambiguity_without_guessing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            database = _build_lexicon_database(tmp_path)
            library = CanonicalLibrary(root=tmp_path / "ckl").load()
            service = WordStudyService(repository=LexiconRepository(database))
            router = StudyActionRouter(DeterministicStudyEngine(library, word_study_service=service))

            result = router.execute(
                "word_study",
                passage={"book": "Psalms", "chapter": 23, "start_verse": 6, "end_verse": 6},
            )

            self.assertEqual(result.status, "partial")
            self.assertFalse(result.agent_fallback_allowed)
            self.assertIn("Multiple possible original-language words", result.sections[0]["title"])
            self.assertIn("steadfast love", result.sections[0]["items"][0])

    def test_word_study_action_resolves_selected_ambiguity_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            database = _build_lexicon_database(tmp_path)
            library = CanonicalLibrary(root=tmp_path / "ckl").load()
            service = WordStudyService(repository=LexiconRepository(database))
            router = StudyActionRouter(DeterministicStudyEngine(library, word_study_service=service))

            result = router.execute(
                "word_study",
                passage={
                    "book": "Psalms",
                    "chapter": 23,
                    "start_verse": 6,
                    "end_verse": 6,
                    "word_position": 1,
                },
            )

            self.assertEqual(result.status, "complete")
            self.assertEqual(result.metadata["word_study"]["surface_form"], "חֶסֶד")
            self.assertEqual(result.metadata["word_study"]["strongs_number"], "H2617")

    def test_word_study_api_returns_complete_when_lexical_data_exists(self):
        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient

            from bhf_web.routes.study import register_study_routes
        except ModuleNotFoundError:
            self.skipTest("FastAPI test dependencies are not installed")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            database = _build_lexicon_database(tmp_path)
            library = CanonicalLibrary(root=tmp_path / "ckl").load()
            service = WordStudyService(repository=LexiconRepository(database))
            router = StudyActionRouter(DeterministicStudyEngine(library, word_study_service=service))
            app = FastAPI()
            register_study_routes(
                app,
                study_db_path=str(tmp_path / "study.sqlite"),
                templates=None,
                job_store=None,
                study_action_router=router,
            )

            response = TestClient(app).post(
                "/api/study/actions",
                json={
                    "action": "word_study",
                    "book": "John",
                    "chapter": 1,
                    "start_verse": 1,
                    "end_verse": 1,
                    "selected_text": "Word",
                },
            )

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "complete")
            self.assertEqual(data["metadata"]["word_study"]["strongs_number"], "G3056")


def _build_lexicon_database(tmp_path: Path) -> Path:
    root = tmp_path / "ckl"
    database = tmp_path / "ckl.sqlite"
    write_library(root, [make_object("john", "book", "John", ["Gospel of John"])])
    build_database(root, database)
    import_normalized_lexicon_file(database, LEXICON_FIXTURE, rebuild=True)
    return database


if __name__ == "__main__":
    unittest.main()
