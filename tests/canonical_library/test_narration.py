"""Focused tests for the offline CKL presentation layer."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from framework.canonical_library.narration import (
    CanonicalNarrator,
    NarrativeRole,
    NarrationLimits,
    PassageScope,
    certainty_phrase,
    dispute_phrase,
    parse_scripture_span,
)
from framework.canonical_library.narration.ranking import collect_evidence, rank_evidence


ROOT = Path(__file__).resolve().parents[2]


def load_object(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def narration_text(result) -> str:
    return " ".join(
        [result.lead.text if result.lead else ""]
        + [sentence.text for section in result.sections for sentence in section.sentences]
    )


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

    def test_dispute_wording_uses_ckl_rationale_to_scope_the_issue(self) -> None:
        record = load_object("framework/canonical_library/objects/books/ruth.json")
        result = CanonicalNarrator().narrate(
            record,
            reference="Ruth 4:1-12",
            context_type="cultural_context",
        )

        self.assertIn("legal reconstruction", result.lead.text)
        self.assertNotIn("Scholars disagree about this point", result.lead.text)

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
        self.assertEqual(certainty_phrase("probable"), "Likely")
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
        self.assertIn("Likely", text)
        self.assertIn("chronology remains debated", text)

    def test_high_certainty_is_metadata_first_not_boilerplate(self) -> None:
        result = CanonicalNarrator().narrate(
            {"claims": [{
                "id": "explicit",
                "claim": "The passage names Jerusalem",
                "claim_type": "biblical_text",
                "certainty": "textually_explicit",
                "scripture_references": ["John 2:13"],
            }]},
            reference="John 2:13",
        )

        self.assertEqual(result.lead.text, "The passage names Jerusalem.")
        self.assertEqual(result.lead.certainty, "textually_explicit")

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

    def test_cross_book_anchor_does_not_import_unscoped_john_literary_notes(self) -> None:
        record = load_object("framework/canonical_library/objects/books/john.json")

        literary = CanonicalNarrator().narrate(
            record,
            reference="Genesis 1:1-5",
            context_type="literary_context",
        )
        canonical = CanonicalNarrator().narrate(
            record,
            reference="Genesis 1:1-5",
            context_type="canonical_context",
        )
        canonical_text = " ".join(
            [canonical.lead.text if canonical.lead else ""]
            + [sentence.text for section in canonical.sections for sentence in section.sentences]
        )

        self.assertFalse(literary.has_content)
        self.assertIn("Logos", canonical_text)
        self.assertNotIn("John 19:35", canonical_text)
        self.assertNotIn("John the Baptist", canonical_text)

    def test_scripture_span_parser_supports_ckl_reference_forms(self) -> None:
        examples = (
            "John 1",
            "John 1:2",
            "John 1:2-5",
            "John 1-2",
            "John 1:2-2:5",
        )
        self.assertTrue(all(parse_scripture_span(reference) for reference in examples))
        cross_chapter = parse_scripture_span("John 1:2-2:5")
        self.assertEqual((cross_chapter.end_chapter, cross_chapter.end_verse), (2, 5))

    def test_verse_specific_claim_is_the_lead_over_chapter_and_book_context(self) -> None:
        record = {
            "id": "samuel-scope",
            "type": "book",
            "title": "1 Samuel",
            "review_status": "approved",
            "scripture_references": ["1 Samuel 1-31"],
            "historical_setting": "Israel and Philistia remained in regional conflict.",
            "claims": [
                {
                    "id": "earlier",
                    "claim": "The armies assembled earlier in the chapter",
                    "claim_type": "historical",
                    "certainty": "high",
                    "scripture_references": ["1 Samuel 17:1-11"],
                },
                {
                    "id": "chapter",
                    "claim": "The chapter presents conflict with the Philistines",
                    "claim_type": "historical",
                    "certainty": "high",
                    "scripture_references": ["1 Samuel 17"],
                },
                {
                    "id": "selected-verses",
                    "claim": "David rejects Saul's armor before approaching Goliath",
                    "claim_type": "biblical_text",
                    "certainty": "textually_explicit",
                    "scripture_references": ["1 Samuel 17:32-40"],
                },
            ],
        }

        ranked = rank_evidence(
            collect_evidence(record, reference="1 Samuel 17:32-40"),
            reference="1 Samuel 17:32-40",
        )
        scopes = {candidate.evidence_id: candidate.scope for candidate in ranked}
        result = CanonicalNarrator().narrate(
            record,
            reference="1 Samuel 17:32-40",
            context_type="historical_context",
        )

        self.assertEqual(scopes["selected-verses"], PassageScope.EXACT)
        self.assertEqual(scopes["earlier"], PassageScope.SAME_CHAPTER)
        self.assertEqual(result.lead.claim_ids, ["selected-verses"])
        self.assertNotIn("regional conflict", narration_text(result))

    def test_near_duplicate_facts_merge_without_losing_provenance(self) -> None:
        record = [
            {
                "id": "duplicate-background-a",
                "title": "Ruth legal setting",
                "type": "cultural_background",
                "claims": [{
                    "id": "claim-a",
                    "claim": "The city gate served as the public setting for legal transactions",
                    "claim_type": "cultural",
                    "scripture_references": ["Ruth 4:1-12"],
                    "source_ids": ["source-a"],
                }],
            },
            {
                "id": "duplicate-background-b",
                "title": "Ruth public transactions",
                "type": "cultural_background",
                "claims": [{
                    "id": "claim-b",
                    "claim": "The city gate was the public setting for legal transactions",
                    "claim_type": "cultural",
                    "scripture_references": ["Ruth 4:1-12"],
                    "source_ids": ["source-b"],
                }],
            },
        ]
        result = CanonicalNarrator().narrate(
            record,
            reference="Ruth 4:1-12",
            context_type="cultural_context",
        )

        self.assertEqual(result.lead.claim_ids, ["claim-a", "claim-b"])
        self.assertEqual(result.lead.evidence_ids, ["claim-a", "claim-b"])
        self.assertEqual(result.lead.source_ids, ["source-a", "source-b"])
        self.assertEqual(
            [record["id"] for record in result.lead.parent_records],
            ["duplicate-background-a", "duplicate-background-b"],
        )
        self.assertEqual(narration_text(result).casefold().count("legal transactions"), 1)

    def test_complementary_roles_are_preferred_to_repetitive_background(self) -> None:
        record = {
            "id": "diverse",
            "title": "Example",
            "scripture_references": ["Acts 16:11-15"],
            "historical_setting": "The city stood within a Roman provincial setting.",
            "historical_context": "The Roman provincial setting shaped civic life.",
            "cultural_context": "Households could serve as centers of patronage and assembly.",
            "literary_context": "The scene moves the narrative into Macedonia.",
        }
        result = CanonicalNarrator(
            limits=NarrationLimits(max_primary_facts=3),
        ).narrate(record, reference="Acts 16:11-15")
        roles = {result.lead.role, *(sentence.role for section in result.sections for sentence in section.sentences)}

        self.assertGreaterEqual(len(roles), 2)
        self.assertIn(NarrativeRole.SETTING, roles)
        self.assertTrue({NarrativeRole.CULTURAL_PRACTICE, NarrativeRole.LITERARY_FUNCTION} & roles)

    def test_qualification_budget_suppresses_repeated_boilerplate(self) -> None:
        record = {
            "id": "chronology",
            "title": "Chronology",
            "claims": [
                {
                    "id": "chronology-a",
                    "claim": "The event may belong to the earlier proposed chronology",
                    "claim_type": "historical",
                    "certainty": "probable",
                    "dispute_status": "chronological_uncertainty",
                    "scripture_references": ["Judges 4"],
                },
                {
                    "id": "chronology-b",
                    "claim": "The event may fit the proposed earlier chronology",
                    "claim_type": "historical",
                    "certainty": "probable",
                    "dispute_status": "chronological_uncertainty",
                    "scripture_references": ["Judges 4"],
                },
            ],
        }
        result = CanonicalNarrator().narrate(
            record,
            reference="Judges 4",
            context_type="historical_context",
        )
        text = narration_text(result).casefold()

        self.assertLessEqual(text.count("chronology remains debated"), 1)
        self.assertTrue(result.lead.dispute_statuses)

    def test_speculative_evidence_is_not_presented_as_certain(self) -> None:
        result = CanonicalNarrator().narrate({
            "claims": [{
                "id": "proposal",
                "claim": "A particular reconstruction connects the two events",
                "claim_type": "historical",
                "certainty": "speculative",
                "scripture_references": ["Acts 18:1-4"],
            }],
        }, reference="Acts 18:1-4", context_type="historical_context")

        self.assertIn("limited evidence", result.lead.text.casefold())
        self.assertEqual(result.lead.certainty, "speculative")

    def test_archaeology_caution_follows_positive_evidence(self) -> None:
        record = load_object("framework/canonical_library/objects/books/1-samuel.json")
        result = CanonicalNarrator().narrate(record, reference="1 Samuel 17", context_type="archaeology")
        section_types = [section.section_type for section in result.sections]

        self.assertEqual(result.lead.role, NarrativeRole.ARCHAEOLOGICAL_SUPPORT)
        if "caution" in section_types:
            self.assertGreater(section_types.index("caution"), -1)

    def test_caution_only_input_does_not_lead_without_a_proposition(self) -> None:
        result = CanonicalNarrator().narrate({
            "interpretive_notes": [{
                "id": "caution-only",
                "note": "This reconstruction remains debated.",
                "note_type": "interpretive_caution",
                "scripture_references": ["John 1:1"],
            }],
        }, reference="John 1:1", context_type="literary_context")

        self.assertFalse(result.has_content)

    def test_quality_corpus_is_deterministic_compact_and_traceable(self) -> None:
        corpus = load_object("tests/canonical_library/narration_quality_corpus.json")
        narrator = CanonicalNarrator()
        for scenario in corpus:
            with self.subTest(reference=scenario["reference"], context=scenario["context_type"]):
                record = load_object(f"framework/canonical_library/{scenario['record']}")
                first = narrator.narrate(
                    record,
                    reference=scenario["reference"],
                    context_type=scenario["context_type"],
                ).to_dict()
                second = narrator.narrate(
                    record,
                    reference=scenario["reference"],
                    context_type=scenario["context_type"],
                ).to_dict()
                self.assertEqual(first, second)
                self.assertLessEqual(sum(len(section["sentences"]) for section in first["sections"]), 5)
                for section in first["sections"]:
                    self.assertTrue(all(sentence["evidence_ids"] for sentence in section["sentences"]))

    def test_empty_evidence_returns_no_narration(self) -> None:
        result = CanonicalNarrator().narrate({}, context_type="historical_context")
        self.assertFalse(result.has_content)
        self.assertEqual(result.sections, [])
        self.assertEqual(result.additional_evidence_count, 0)


if __name__ == "__main__":
    unittest.main()
