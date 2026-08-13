"""Focused tests for the offline CKL presentation layer."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from framework.canonical_library.narration import (
    CanonicalNarrator,
    NarrativeRole,
    certainty_phrase,
    dispute_phrase,
)


ROOT = Path(__file__).resolve().parents[2]


def load_object(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class NarrationTests(unittest.TestCase):
    def test_claims_are_preferred_and_provenance_is_retained(self) -> None:
        record = load_object("framework/canonical_library/objects/cultural_background/kinship-inheritance-and-redemption.json")
        result = CanonicalNarrator().narrate(record, reference="Ruth 4:1-12", context_type="cultural_context")

        self.assertTrue(result.has_content)
        self.assertIn("Ruth 4 publicly joins", result.lead.text)
        self.assertEqual(result.lead.claim_ids, ["kinship-ruth-arrangement"])
        self.assertIn("ruth-4", result.lead.source_ids)
        self.assertEqual(result.lead.source_details[0]["title"], "Ruth 4")
        self.assertEqual(result.lead.parent_object_id, "kinship-inheritance-and-redemption")
        self.assertEqual(result.lead.scripture_references, ["Ruth 4:1-12"])
        self.assertTrue(all(sentence.evidence_ids for section in result.sections for sentence in section.sentences))

    def test_falls_back_to_context_fields_when_claims_are_missing(self) -> None:
        result = CanonicalNarrator().narrate(
            {
                "id": "legacy-context",
                "type": "book",
                "title": "Legacy Context",
                "summary": "A summary fallback.",
                "historical_context": "The community lived under imperial administration.",
                "literary_context": "The passage uses a repeated narrative pattern.",
                "scripture_references": [{"reference": "John 4:1-26", "relationship": "primary"}],
            },
            reference="John 4:1-26",
            context_type="historical_context",
        )

        self.assertTrue(result.has_content)
        self.assertIn("imperial administration", result.lead.text)
        self.assertFalse(any("No historical context" in sentence.text for section in result.sections for sentence in section.sentences))

    def test_certainty_and_dispute_language_is_deterministic(self) -> None:
        self.assertEqual(certainty_phrase("probable"), "The evidence likely indicates")
        self.assertEqual(dispute_phrase("textual_variant"), "Ancient textual witnesses differ at this point.")
        result = CanonicalNarrator().narrate(
            {
                "claims": [{
                    "id": "uncertain-claim",
                    "claim": "The chronology follows one reconstruction",
                    "claim_type": "historical_cultural",
                    "certainty": "probable",
                    "dispute_status": "chronological_uncertainty",
                }],
            },
            context_type="historical_context",
        )
        text = " ".join(
            [result.lead.text if result.lead else ""]
            + [sentence.text for section in result.sections for sentence in section.sentences]
        )
        self.assertIn("likely indicates", text)
        self.assertIn("chronology remains debated", text)

    def test_caution_and_archaeology_limitation_are_preserved(self) -> None:
        record = load_object("framework/canonical_library/objects/books/1-samuel.json")
        result = CanonicalNarrator().narrate(record, reference="1 Samuel 17", context_type="archaeology")

        caution_text = " ".join(
            [result.lead.text if result.lead else ""]
            + [sentence.text
            for section in result.sections
            for sentence in section.sentences]
        )
        self.assertIn("individual battle narratives", caution_text)

    def test_determinism_budgets_and_additional_evidence(self) -> None:
        record = load_object("framework/canonical_library/objects/cultural_background/kinship-inheritance-and-redemption.json")
        narrator = CanonicalNarrator()
        first = narrator.narrate(record, reference="Ruth 4:1-12", context_type="cultural_context").to_dict()
        second = narrator.narrate(record, reference="Ruth 4:1-12", context_type="cultural_context").to_dict()

        self.assertEqual(first, second)
        self.assertGreater(first["additional_evidence_count"], 0)
        self.assertLessEqual(sum(len(section["sentences"]) for section in first["sections"]), 5)

    def test_passage_scope_avoids_unrelated_1_samuel_claims(self) -> None:
        record = load_object("framework/canonical_library/objects/books/1-samuel.json")
        result = CanonicalNarrator().narrate(record, reference="1 Samuel 17", context_type="historical_context")
        text = " ".join(
            [result.lead.text if result.lead else ""]
            + [sentence.text for section in result.sections for sentence in section.sentences]
        )

        self.assertIn("Philistine", text)
        self.assertNotIn("Hannah's song", text)
        self.assertNotIn("At Endor", text)

    def test_empty_evidence_returns_no_narration(self) -> None:
        result = CanonicalNarrator().narrate({}, context_type="historical_context")
        self.assertFalse(result.has_content)
        self.assertEqual(result.sections, [])
        self.assertEqual(result.additional_evidence_count, 0)


if __name__ == "__main__":
    unittest.main()
