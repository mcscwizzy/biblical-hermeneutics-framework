from __future__ import annotations

import unittest
from types import SimpleNamespace

from bhf_agent.context_pipeline import (
    build_context_evidence_packet,
    deterministic_context_presentation,
    present_context_with_ai,
    validate_context_presentation,
)
from bhf_agent.study_actions import StudyActionRouter


def ckl_object(
    object_id: str,
    title: str,
    *,
    historical_context: str = "",
    scripture_references: list[dict[str, str]] | None = None,
    confidence: str = "high",
    object_type: str = "event",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=object_id,
        title=title,
        type=object_type,
        confidence=confidence,
        historical_context=historical_context,
        historical_setting="",
        date_ranges=[],
        timeline=[],
        ancient_near_east_context="",
        hebraic_worldview="",
        second_temple_context="",
        original_audience="",
        covenantal_significance="",
        literary_context="",
        summary="",
        canonical_context="",
        canonical_placement="",
        canonical_role="",
        intertextuality=[],
        scripture_references=scripture_references or [],
        cross_references=[],
        new_testament_connections=[],
    )


class ContextPipelineTests(unittest.TestCase):
    def test_generic_cross_book_keyword_record_is_rejected(self):
        packet = build_context_evidence_packet(
            [
                ckl_object(
                    "john",
                    "John",
                    historical_context="John discusses light, life, word, and creation.",
                    scripture_references=[{"reference": "John 1:1-5", "relationship": "primary"}],
                )
            ],
            target_book="Genesis",
            reference="Genesis 1:1",
            action="historical_context",
        )

        self.assertEqual(packet["primary_evidence"], [])
        self.assertTrue(packet["excluded"])

    def test_curated_cross_book_reference_is_later_connection_only(self):
        packet = build_context_evidence_packet(
            [
                ckl_object(
                    "creation",
                    "Creation",
                    historical_context="Genesis presents creation as ordered by God.",
                    scripture_references=[
                        {"reference": "Genesis 1:1-31", "relationship": "primary", "notes": "creation"},
                        {"reference": "John 1:1-5", "relationship": "allusion", "notes": "later echo"},
                    ],
                )
            ],
            target_book="Genesis",
            reference="Genesis 1:1",
            action="historical_context",
            trusted_record_ids={"creation"},
        )

        self.assertTrue(any("ordered by God" in item["fact"] for item in packet["primary_evidence"]))
        self.assertEqual([item["reference"] for item in packet["later_biblical_connections"]], ["John 1:1-5"])
        self.assertNotIn("John", " ".join(item["fact"] for item in packet["primary_evidence"]))

    def test_duplicate_facts_are_collapsed(self):
        packet = build_context_evidence_packet(
            [
                ckl_object("genesis", "Genesis", historical_context="One ordered creation account."),
                ckl_object("creation", "Creation", historical_context="One ordered creation account."),
            ],
            target_book="Genesis",
            reference="Genesis 1:1",
            action="historical_context",
        )

        self.assertEqual(
            [item["fact"] for item in packet["primary_evidence"]].count("One ordered creation account."),
            1,
        )

    def test_invalid_presentation_cannot_add_reference_or_cross_book_fact(self):
        packet = build_context_evidence_packet(
            [ckl_object("creation", "Creation", historical_context="Ordered creation.")],
            target_book="Genesis",
            reference="Genesis 1:1",
            action="historical_context",
        )
        presentation = {
            "summary": "Genesis 1:1 and John 1:1 establish an unsupported claim.",
            "summary_evidence_ids": ["ckl:creation:historical_context:0"],
            "key_facts": [
                {
                    "fact": "John 1:1 proves this original context.",
                    "why_it_matters": "It matters.",
                    "evidence_ids": ["ckl:creation:historical_context:0"],
                    "confidence": "high",
                }
            ],
            "later_biblical_connections": [],
            "important_caution": None,
            "caution_evidence_ids": [],
        }

        valid, errors = validate_context_presentation(presentation, packet)

        self.assertFalse(valid)
        self.assertTrue(any("unsupported Bible reference" in error for error in errors))

    def test_malformed_ai_output_uses_deterministic_fallback(self):
        packet = build_context_evidence_packet(
            [ckl_object("creation", "Creation", historical_context="Ordered creation.")],
            target_book="Genesis",
            reference="Genesis 1:1",
            action="historical_context",
        )
        adapter = SimpleNamespace(chat=lambda request: SimpleNamespace(text="not json"))

        result = present_context_with_ai(packet, adapter=adapter, model="fixture")

        self.assertEqual(result["mode"], "deterministic_fallback")
        self.assertTrue(result["key_facts"])

    def test_genesis_reader_context_separates_john(self):
        result = StudyActionRouter().execute(
            "historical_context",
            passage={
                "book": "Genesis",
                "chapter": 1,
                "start_verse": 1,
                "end_verse": 1,
                "selected_text": "In the beginning God created the heavens and the earth.",
            },
        )

        historical_text = " ".join(
            item
            for section in result.sections
            if section["title"] in {"Historical Context", "Historical Setting", "Dates and Setting", "Timeline", "Overview"}
            for item in section["items"]
        )
        later_text = " ".join(item["connection"] for item in result.presentation["later_biblical_connections"])
        self.assertNotIn("John 1:1-5", historical_text)
        self.assertIn("John 1:1-5", later_text)


if __name__ == "__main__":
    unittest.main()
