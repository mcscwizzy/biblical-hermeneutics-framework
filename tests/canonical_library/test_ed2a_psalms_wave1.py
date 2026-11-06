from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PSALMS_PATH = (
    REPO_ROOT / "framework" / "canonical_library" / "objects" / "books" / "psalms.json"
)


class Ed2aPsalmsWave1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.psalms = json.loads(PSALMS_PATH.read_text(encoding="utf-8"))
        cls.evidence = {
            item["id"]: item for item in cls.psalms.get("evidence_items", [])
        }
        cls.sources = {
            source["id"]: source for source in cls.psalms.get("sources", [])
        }

    def test_wave_additions_are_bounded_and_passage_scoped(self) -> None:
        expected = {
            "psalm-06-embodied-lament-language": "Psalm 6:2-8",
            "psalm-15-ethical-entrance-liturgy": "Psalm 15:1-5",
            "psalm-30-superscription-and-reuse": "Psalm 30:1-12",
            "psalm-37-acrostic-gap-debate": "Psalm 37:1-40",
            "psalm-44-communal-lament-and-book-context": "Psalm 44:1-26",
            "psalm-47-enthronement-hymn-setting-debate": "Psalm 47:1-9",
            "psalm-67-jussive-call-and-cultic-setting-debate": "Psalm 67:1-7",
            "psalm-96-kingship-hymn-and-memory-proposal": "Psalm 96:1-13",
            "psalm-145-nun-verse-witness": "Psalm 145:13",
        }
        added_ids = set(expected)
        self.assertEqual(9, len(added_ids))
        self.assertTrue(added_ids.issubset(self.evidence))
        self.assertEqual(10, len(self.evidence))  # Includes the ED-1B Psalm 72 control.

        for item_id, reference in expected.items():
            with self.subTest(item=item_id):
                item = self.evidence[item_id]
                self.assertIn(
                    reference,
                    {entry["reference"] for entry in item["scripture_references"]},
                )
                self.assertTrue(item["primary_observation"].strip())
                self.assertTrue(item["scholarly_interpretation"].strip())
                self.assertNotEqual(
                    item["primary_observation"].strip(),
                    item["scholarly_interpretation"].strip(),
                )
                self.assertTrue(item["passage_relevance"].strip())
                self.assertTrue(item["source_ids"])
                self.assertTrue(set(item["source_ids"]).issubset(self.sources))
                self.assertTrue(item["confidence_rationale"].strip())
                self.assertTrue(item["certainty"])
                self.assertTrue(item["dispute_status"])
                self.assertTrue(item["temporal_scope"]["notes"].strip())
                self.assertTrue(item["scripture_references"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])

    def test_additions_preserve_in_review_governance_and_psalm72_control(self) -> None:
        self.assertEqual("draft", self.psalms["content_status"])
        self.assertEqual("in_review", self.psalms["review_status"])
        self.assertEqual([], self.psalms["reviewed_by"])
        self.assertIsNone(self.psalms["last_reviewed"])
        self.assertTrue(self.psalms["human_review_required"])
        self.assertIn("psalm-72-royal-justice-setting", self.evidence)
        control = self.evidence["psalm-72-royal-justice-setting"]
        self.assertEqual(["psalms-masoretic", "human-psalm72-leadership"], control["source_ids"])
        self.assertEqual("Psalm 72:1-14", control["scripture_references"][0]["reference"])

    def test_added_source_entries_have_distinct_bibliographic_identities(self) -> None:
        new_ids = {
            "wessels-coetzee-psalms-body-2013",
            "boloje-groenewald-psalm15-2016",
            "sommer-psalm30-2022",
            "benun-acrostics-psalms-2006",
            "verde-psalms-trauma-2022",
            "perdue-psalm47-1974",
            "botha-psalm67-2004",
            "hays-psalm96-2023",
            "sanders-11qpsa-1965",
            "rahlfs-hanhart-septuaginta-2006",
            "gentry-textual-criticism-2020",
            "iaa-11q5-digital-library",
        }
        self.assertTrue(new_ids.issubset(self.sources))
        for source_id in new_ids:
            with self.subTest(source=source_id):
                source = self.sources[source_id]
                self.assertTrue(source.get("title"))
                self.assertTrue(source.get("source_type"))
                self.assertTrue(source.get("url"))
                self.assertTrue(source.get("supports"))


if __name__ == "__main__":
    unittest.main()
