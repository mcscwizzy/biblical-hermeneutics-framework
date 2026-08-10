from __future__ import annotations

import json
from pathlib import Path
import unittest

from framework.canonical_library.schema import validate_object


ROOT = Path(__file__).resolve().parents[2] / "framework" / "canonical_library"
OBJECT_IDS = {
    "kinship-inheritance-and-redemption",
    "patronage-hospitality-and-debt",
    "ritual-purity-and-communal-holiness",
    "synagogue-life-and-exclusion",
    "roman-citizenship-and-legal-process",
}


class CulturalBackgroundExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.objects = []
        for object_id in sorted(OBJECT_IDS):
            path = ROOT / "objects" / "cultural_background" / f"{object_id}.json"
            cls.objects.append(validate_object(json.loads(path.read_text(encoding="utf-8"))))

    def test_new_objects_are_source_backed_review_candidates(self) -> None:
        self.assertEqual({obj.id for obj in self.objects}, OBJECT_IDS)
        self.assertEqual(sum(len(obj.claims) for obj in self.objects), 9)
        for obj in self.objects:
            with self.subTest(object_id=obj.id):
                self.assertEqual(obj.type, "cultural_background")
                self.assertEqual(obj.review_status, "in_review")
                self.assertTrue(obj.human_review_required)
                self.assertNotIn(obj.review_status, {"reviewed", "approved"})
                source_ids = {source.id for source in obj.sources}
                self.assertTrue(any(source.source_type != "scripture" for source in obj.sources))
                for claim in obj.claims:
                    self.assertTrue(claim.source_ids)
                    self.assertTrue(set(claim.source_ids).issubset(source_ids))
                    self.assertTrue(claim.scripture_references)

    def test_topics_cover_the_prioritized_cultural_lanes(self) -> None:
        searchable = " ".join(
            " ".join(
                [obj.title, obj.summary, *obj.aliases, *obj.retrieval_metadata["semantic_keywords"]]
            ).lower()
            for obj in self.objects
        )
        for term in (
            "kinship",
            "inheritance",
            "redemption",
            "marriage",
            "household",
            "patronage",
            "hospitality",
            "debt",
            "purity",
            "synagogue",
            "citizenship",
        ):
            with self.subTest(term=term):
                self.assertIn(term, searchable)


if __name__ == "__main__":
    unittest.main()
