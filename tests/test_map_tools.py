import tempfile
import unittest
from pathlib import Path

from bhf_agent.map_tools import (
    build_map_tool_context,
    getArchaeologyForPassage,
    getHistoricalContextForPeriod,
    getPlaceDetails,
    getPlacesForPassage,
    getRelatedPassagesByPlace,
    getRoutesForPassage,
)
from bhf_agent.models import QuestionContext, ReferenceContext
from bhf_agent.study_db import initialize_database


class MapToolTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmpdir.name) / "study.sqlite"
        initialize_database(path=self.path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_passage_tools_return_curated_data(self):
        places = getPlacesForPassage("Acts 10:1-48", path=self.path)
        archaeology = getArchaeologyForPassage("John 9:7-11", path=self.path)
        routes = getRoutesForPassage("Acts 13:1-52", path=self.path)

        self.assertFalse(places["empty_state"])
        self.assertIn("caesarea-maritima", places["matched_place_ids"])
        self.assertFalse(archaeology["empty_state"])
        self.assertIn("pool-of-siloam", archaeology["matched_archaeology_ids"])
        self.assertFalse(routes["empty_state"])

    def test_place_and_period_tools_return_related_context(self):
        place = getPlaceDetails("jerusalem", path=self.path)
        related = getRelatedPassagesByPlace("jerusalem", path=self.path)
        historical = getHistoricalContextForPeriod("NT / Roman period", path=self.path)

        self.assertEqual(place["id"], "jerusalem")
        self.assertIn("related_passages", place)
        self.assertGreater(related["count"], 0)
        self.assertGreater(len(historical["historical_layers"]), 0)
        self.assertGreater(len(historical["political_context_layers"]), 0)

    def test_map_tool_context_triggers_for_archaeology_question(self):
        reference = ReferenceContext(
            book="John",
            chapter=9,
            verse=7,
            testament="New Testament",
            is_reference_based=True,
            confidence=0.95,
        )
        question_context = QuestionContext(question_type="historical_context", confidence=0.8)

        context = build_map_tool_context(
            "What archaeology is connected with John 9?",
            reference_context=reference,
            question_context=question_context,
            path=self.path,
        )

        self.assertIsNotNone(context)
        assert context is not None
        self.assertIn("getPlacesForPassage", context["requested_tools"])
        self.assertIn("getArchaeologyForPassage", context["requested_tools"])
        self.assertIn("historical_context", context)

    def test_map_tool_context_skips_non_map_questions(self):
        reference = ReferenceContext(
            book="Romans",
            chapter=8,
            verse=1,
            testament="New Testament",
            is_reference_based=True,
            confidence=0.95,
        )
        question_context = QuestionContext(question_type="passage_study", confidence=0.7)

        context = build_map_tool_context(
            "What does Romans 8 mean?",
            reference_context=reference,
            question_context=question_context,
            path=self.path,
        )

        self.assertIsNone(context)
