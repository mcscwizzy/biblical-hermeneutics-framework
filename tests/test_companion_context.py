import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bhf_agent.study_db import (
    initialize_database,
    list_archaeology_passage_summaries,
    list_passage_map_summaries,
)
from bhf_web.routes.study import register_study_routes
from bhf_web.services.companion_context import CompanionContextService
from bhf_web.services.web_helpers import build_ask_question, reader_context_from_form


class _Commentary:
    def __init__(self, entries=None):
        self.entries = list(entries or [])
        self.calls = []

    def lookup_passage(self, book, chapter, verse_start, verse_end):
        self.calls.append(("passage", book, chapter, verse_start, verse_end))
        return self.entries

    def lookup_chapter(self, book, chapter):
        self.calls.append(("chapter", book, chapter))
        return self.entries

    def count_passage(self, book, chapter, verse_start, verse_end):
        self.calls.append(("count_passage", book, chapter, verse_start, verse_end))
        return len(self.entries)

    def count_chapter(self, book, chapter):
        self.calls.append(("count_chapter", book, chapter))
        return len(self.entries)


class _WordRepository:
    def __init__(self, count):
        self.count = count
        self.calls = []

    def count_passage_words(self, book, chapter, verse_start, verse_end):
        self.calls.append((book, chapter, verse_start, verse_end))
        return self.count


class _WordService:
    def __init__(self, count):
        self.repository = _WordRepository(count)


class _CanonicalLibrary:
    def __init__(self, objects=None):
        self.objects = list(objects or [])
        self.calls = []

    def retrieve_by_scripture_reference(self, reference, **options):
        self.calls.append((reference, options))
        return [SimpleNamespace(object=item, score=1.0) for item in self.objects]


def _canonical_objects():
    return [
        SimpleNamespace(
            id="jesus",
            title="Jesus",
            type="person",
            summary="Jesus speaks with the Samaritan woman.",
            cross_references=["John 3:16"],
            intertextuality=[],
            historical_context="Roman Judea",
            literary_context="Gospel dialogue",
            original_audience="Johannine audience",
        ),
        SimpleNamespace(
            id="worship",
            title="Worship",
            type="theme",
            summary="Worship in spirit and truth.",
            cross_references=["Romans 12:1"],
            intertextuality=["Psalm 95:6"],
            second_temple_context="Temple and Samaritan worship",
            covenantal_significance="New-covenant worship",
        ),
        SimpleNamespace(
            id="samaritan-mission",
            title="Samaritan Mission",
            type="event",
            summary="The good news reaches Samaria.",
            cross_references=["Acts 8:5"],
            intertextuality=[],
            timeline="First-century mission",
            date_ranges=["AD 30-40"],
        ),
    ]


class CompanionContextServiceTests(unittest.TestCase):
    def _service(self, *, commentary=None, word_count=9, objects=None, translations=2):
        library = _CanonicalLibrary(_canonical_objects() if objects is None else objects)
        service = CompanionContextService(
            study_db_path="unused-study.sqlite",
            commentary_db_path="unused-commentary.sqlite",
            commentary_service=commentary or _Commentary([object(), object()]),
            word_study_service=_WordService(word_count),
            canonical_library_provider=lambda: library,
            translation_provider=lambda: [
                {"translation_id": f"translation-{index}", "installed": True}
                for index in range(translations)
            ],
        )
        return service, library

    def test_translation_cache_can_be_invalidated_after_local_install(self):
        installed = [{"translation_id": "asv", "installed": True}]
        calls = []
        service = CompanionContextService(
            study_db_path="unused-study.sqlite",
            commentary_db_path="unused-commentary.sqlite",
            commentary_service=_Commentary(),
            word_study_service=_WordService(0),
            canonical_library_provider=lambda: _CanonicalLibrary(),
            translation_provider=lambda: calls.append(True) or list(installed),
        )

        self.assertEqual(len(service._translations()), 1)
        installed.append({"translation_id": "kjv", "installed": True})
        self.assertEqual(len(service._translations()), 1)
        service.invalidate_translation_cache()
        self.assertEqual(len(service._translations()), 2)
        self.assertEqual(len(calls), 2)

    @patch("bhf_web.services.companion_context.list_archaeology_passage_summaries")
    @patch("bhf_web.services.companion_context.list_passage_map_summaries")
    def test_single_verse_uses_actual_compact_availability(self, map_lookup, archaeology_lookup):
        map_lookup.return_value = {
            "places": [{"id": "sychar", "title": "Sychar", "type": "place"}],
            "routes": [],
        }
        archaeology_lookup.return_value = [
            {"id": "jacobs-well", "title": "Jacob's Well", "summary": "A linked site."}
        ]
        commentary = _Commentary([object(), object()])
        service, library = self._service(commentary=commentary, word_count=6)

        result = service.build(
            book="John",
            chapter=4,
            verse_start=23,
            verse_end=23,
            translation="ASV",
        )

        self.assertEqual(result["reference"], "John 4:23")
        self.assertEqual(result["scope"], "passage")
        self.assertEqual(result["resources"]["commentary"]["count"], 2)
        self.assertEqual(result["resources"]["word_study"]["count"], 6)
        self.assertTrue(result["resources"]["maps"]["available"])
        self.assertTrue(result["resources"]["archaeology"]["available"])
        self.assertTrue(result["resources"]["people"]["available"])
        self.assertTrue(result["resources"]["themes"]["available"])
        self.assertTrue(result["resources"]["timeline"]["available"])
        self.assertEqual(result["resources"]["compare_translations"]["count"], 2)
        self.assertEqual(result["resources"]["compare_translations"]["selected_translation"], "asv")
        self.assertNotIn("media", result["summaries"]["archaeology"][0])
        self.assertIn("narration", result["summaries"])
        self.assertIn("historical_context", result["summaries"]["narration"]["by_context"])
        self.assertIn("original_audience", result["summaries"]["narration"]["by_context"])
        self.assertEqual(result["narration"], result["summaries"]["narration"])
        self.assertEqual(commentary.calls, [("count_passage", "John", 4, 23, 23)])
        self.assertEqual(library.calls[0][0], "John 4:23")
        map_lookup.assert_called_once_with("John", 4, 23, 23, path=service.study_db_path, limit=12, prepare_schema=False)

    @patch("bhf_web.services.companion_context.list_archaeology_passage_summaries", return_value=[])
    @patch("bhf_web.services.companion_context.list_passage_map_summaries", return_value={"places": [], "routes": []})
    def test_passage_range_and_whole_chapter_preserve_scope(self, _map_lookup, _archaeology_lookup):
        commentary = _Commentary([object()])
        service, library = self._service(commentary=commentary)

        passage = service.build(book="John", chapter=4, verse_start=21, verse_end=24)
        chapter = service.build(book="John", chapter=4)

        self.assertEqual(passage["reference"], "John 4:21-24")
        self.assertEqual(chapter["reference"], "John 4")
        self.assertEqual(chapter["scope"], "chapter")
        self.assertIn(("count_chapter", "John", 4), commentary.calls)
        self.assertEqual(service.word_study.repository.calls[-1], ("John", 4, None, None))
        self.assertEqual([call[0] for call in library.calls], ["John 4:21-24", "John 4"])

    @patch("bhf_web.services.companion_context.list_archaeology_passage_summaries", return_value=[])
    @patch("bhf_web.services.companion_context.list_passage_map_summaries", return_value={"places": [], "routes": []})
    def test_empty_sources_are_explicitly_unavailable(self, _map_lookup, _archaeology_lookup):
        service, _library = self._service(
            commentary=_Commentary([]),
            word_count=0,
            objects=[],
            translations=1,
        )

        result = service.build(book="John", chapter=4, verse_start=99)

        for resource_id in (
            "commentary",
            "word_study",
            "maps",
            "archaeology",
            "people",
            "places",
            "themes",
            "timeline",
            "cross_references",
            "canonical",
            "compare_translations",
        ):
            self.assertEqual(result["resources"][resource_id]["state"], "unavailable")
            self.assertFalse(result["resources"][resource_id]["available"])

    @patch("bhf_web.services.companion_context.list_archaeology_passage_summaries", return_value=[])
    @patch("bhf_web.services.companion_context.list_passage_map_summaries", return_value={"places": [], "routes": []})
    def test_missing_commentary_database_is_unavailable_not_unknown(self, _map_lookup, _archaeology_lookup):
        commentary = SimpleNamespace(repository=SimpleNamespace(available=False))
        service, _library = self._service(commentary=commentary)

        result = service.build(book="John", chapter=4, verse_start=23)

        self.assertEqual(result["resources"]["commentary"]["state"], "unavailable")
        self.assertEqual(result["resources"]["commentary"]["count"], 0)

    @patch("bhf_web.services.companion_context.list_archaeology_passage_summaries", return_value=[])
    @patch("bhf_web.services.companion_context.list_passage_map_summaries", side_effect=RuntimeError("map database unavailable"))
    def test_one_subsystem_failure_does_not_fail_context(self, _map_lookup, _archaeology_lookup):
        service, _library = self._service()

        result = service.build(book="John", chapter=4, verse_start=23)

        self.assertEqual(result["resources"]["maps"]["state"], "unknown")
        self.assertEqual(result["subsystems"]["maps"]["error"], "RuntimeError")
        self.assertTrue(result["resources"]["commentary"]["available"])
        self.assertTrue(result["resources"]["word_study"]["available"])
        self.assertTrue(result["resources"]["canonical"]["available"])


class CompactPassageRepositoryTests(unittest.TestCase):
    def test_map_and_archaeology_summaries_use_passage_links_without_heavy_payloads(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "study.sqlite"
            initialize_database(path)

            maps = list_passage_map_summaries(
                "Acts", 10, 1, 48, path=path, prepare_schema=False
            )
            archaeology = list_archaeology_passage_summaries(
                "John", 9, 7, 11, path=path, prepare_schema=False
            )

        self.assertIn("caesarea-maritima", [item["id"] for item in maps["places"]])
        self.assertIn("pool-of-siloam", [item["id"] for item in archaeology])
        self.assertTrue(all("geojson" not in item for item in maps["routes"]))
        self.assertTrue(all("media" not in item for item in archaeology))


class CompanionContextRouteTests(unittest.TestCase):
    def test_api_accepts_reference_fields_and_returns_compact_context(self):
        class FakeService:
            def __init__(self):
                self.calls = []

            def build(self, **values):
                self.calls.append(values)
                return {
                    "reference": "John 4:23",
                    "scope": "passage",
                    "resources": {"commentary": {"state": "available", "available": True, "count": 1}},
                    "entities": {"people": [], "places": [], "themes": []},
                    "summaries": {},
                    "subsystems": {},
                }

        service = FakeService()
        app = FastAPI()
        register_study_routes(
            app,
            study_db_path="unused.sqlite",
            templates=None,
            job_store=None,
            companion_context_service=service,
        )

        response = TestClient(app).get(
            "/api/study/companion-context",
            params={
                "book": "John",
                "chapter": 4,
                "verse_start": 23,
                "verse_end": 23,
                "translation": "asv",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reference"], "John 4:23")
        self.assertEqual(
            service.calls,
            [{
                "book": "John",
                "chapter": 4,
                "verse_start": 23,
                "verse_end": 23,
                "translation": "asv",
            }],
        )
        self.assertNotIn("selected_text", response.json())


class AskSelectionContextTests(unittest.TestCase):
    @staticmethod
    def _translation():
        return {
            "translation": {"id": "KJV", "name": "King James Version", "language": "en"},
            "books": [{
                "name": "John",
                "chapters": [{
                    "chapter": 4,
                    "verses": [
                        {"book": "John", "chapter": 4, "verse": 21, "text": "Woman, believe me."},
                        {"book": "John", "chapter": 4, "verse": 22, "text": "Ye worship ye know not what."},
                        {"book": "John", "chapter": 4, "verse": 23, "text": "The true worshippers shall worship the Father."},
                        {"book": "John", "chapter": 4, "verse": 24, "text": "God is a Spirit."},
                    ],
                }],
            }],
        }

    @patch("bhf_web.services.web_helpers.load_translation_bible")
    def test_reader_context_matches_single_range_chapter_translation_and_word(self, load_translation):
        load_translation.return_value = self._translation()

        single = reader_context_from_form({
            "reader_book": "John",
            "reader_chapter": "4",
            "reader_start_verse": "23",
            "reader_end_verse": "23",
            "reader_selected_verses": "[23]",
            "reader_selected_text": "The true worshippers shall worship the Father.",
            "reader_selected_word": '{"surfaceForm":"worshippers","lemma":"proskynetes","strongsNumber":"G4353","wordPosition":2}',
            "reader_translation": "kjv",
        })
        passage_range = reader_context_from_form({
            "reader_book": "John",
            "reader_chapter": "4",
            "reader_start_verse": "21",
            "reader_end_verse": "24",
            "reader_selected_verses": "[21,22,23,24]",
            "reader_selected_text": "Exact selected range text.",
            "reader_translation": "kjv",
        })
        chapter = reader_context_from_form({
            "reader_book": "John",
            "reader_chapter": "4",
            "reader_translation": "kjv",
        })

        self.assertEqual(single["reference"], "John 4:23")
        self.assertEqual(single["selected_text"], "The true worshippers shall worship the Father.")
        self.assertEqual(single["translation_id"], "kjv")
        self.assertEqual(single["selected_word"], {
            "surface_form": "worshippers",
            "lemma": "proskynetes",
            "strongs_number": "G4353",
            "word_position": "2",
        })
        self.assertEqual(passage_range["reference"], "John 4:21-24")
        self.assertEqual(passage_range["selected_text"], "Exact selected range text.")
        self.assertEqual(chapter["reference"], "John 4")
        self.assertIsNone(chapter["start_verse"])
        self.assertIsNone(chapter["end_verse"])
        self.assertEqual(chapter["selected_verses"], [])

    @patch("bhf_web.services.web_helpers.load_translation_bible")
    def test_ask_prompt_inherits_selected_word_without_restatement(self, load_translation):
        load_translation.return_value = self._translation()
        question, reference = build_ask_question({
            "reader_book": "John",
            "reader_chapter": "4",
            "reader_start_verse": "23",
            "reader_end_verse": "23",
            "reader_selected_verses": "[23]",
            "reader_selected_text": "worshippers",
            "reader_selected_word": '{"surfaceForm":"worshippers","lemma":"proskynetes","strongsNumber":"G4353"}',
            "reader_translation": "kjv",
            "question": "Why does this word matter?",
        })

        self.assertEqual(reference, "John 4:23")
        self.assertIn("Using BHF, explain KJV John 4:23.", question)
        self.assertIn("Selected text (KJV John 4:23):\nworshippers", question)
        self.assertIn("Selected word: worshippers, lemma proskynetes, Strong's G4353", question)


if __name__ == "__main__":
    unittest.main()
