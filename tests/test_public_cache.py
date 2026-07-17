from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from framework.canonical_library import (
    JsonPublicAnswerCache,
    PublicCacheEntry,
    load_framework_version,
    load_framework_version_fingerprint,
    normalize_public_question,
    public_cache_key,
)


class PublicAnswerCacheTests(unittest.TestCase):
    def test_store_lookup_and_increment_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "public-cache.json"
            cache = JsonPublicAnswerCache(path, minimum_quality_score=80.0)
            question = normalize_public_question(
                "Why did Israel renew the covenant at Shechem?"
            )
            fingerprint = load_framework_version_fingerprint()
            entry = PublicCacheEntry(
                normalized_question=question,
                answer_mode="study",
                answer="Israel renewed the covenant at Shechem.",
                quality_score=94.2,
                usage_count=2,
                review_status="approved",
                framework_version=load_framework_version(),
                framework_version_fingerprint=fingerprint,
                ckl_version_fingerprint="ckl-fingerprint",
                object_dependency_ids=("shechem", "abraham", "joshua"),
                expires_at="2030-01-01T00:00:00Z",
            )

            cache.store(entry)
            hit = cache.lookup(
                question,
                "study",
                ckl_version_fingerprint="ckl-fingerprint",
                framework_version_fingerprint=fingerprint,
            )
            self.assertIsNotNone(hit)
            assert hit is not None
            self.assertEqual(hit.answer, entry.answer)
            self.assertEqual(hit.object_dependency_ids, entry.object_dependency_ids)
            self.assertEqual(hit.usage_count, 2)

            cache.increment_usage(question, "study")
            hit_after_increment = cache.lookup(
                question,
                "study",
                ckl_version_fingerprint="ckl-fingerprint",
                framework_version_fingerprint=fingerprint,
            )
            self.assertIsNotNone(hit_after_increment)
            assert hit_after_increment is not None
            self.assertEqual(hit_after_increment.usage_count, 3)
            self.assertEqual(cache.last_lookup_status, "hit")

    def test_lookup_is_keyed_by_answer_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "public-cache.json"
            cache = JsonPublicAnswerCache(path)
            question = normalize_public_question("What is Shechem?")
            fingerprint = load_framework_version_fingerprint()
            cache.store(
                PublicCacheEntry(
                    normalized_question=question,
                    answer_mode="study",
                    answer="Shechem is a key covenant location.",
                    quality_score=92.0,
                    review_status="approved",
                    framework_version=load_framework_version(),
                    framework_version_fingerprint=fingerprint,
                    ckl_version_fingerprint="ckl-fingerprint",
                    object_dependency_ids=("shechem",),
                    expires_at="2030-01-01T00:00:00Z",
                )
            )

            hit = cache.lookup(
                question,
                "teaching",
                ckl_version_fingerprint="ckl-fingerprint",
                framework_version_fingerprint=fingerprint,
            )

        self.assertIsNone(hit)
        self.assertEqual(cache.last_lookup_status, "miss")

    def test_lookup_filters_review_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "public-cache.json"
            cache = JsonPublicAnswerCache(path, allowed_review_statuses=("approved",))
            question = normalize_public_question("Why is covenant important?")
            fingerprint = load_framework_version_fingerprint()
            cache.store(
                PublicCacheEntry(
                    normalized_question=question,
                    answer_mode="study",
                    answer="Covenant is central to biblical theology.",
                    quality_score=90.0,
                    review_status="reviewed",
                    framework_version=load_framework_version(),
                    framework_version_fingerprint=fingerprint,
                    ckl_version_fingerprint="ckl-fingerprint",
                    object_dependency_ids=("covenant",),
                    expires_at="2030-01-01T00:00:00Z",
                )
            )

            hit = cache.lookup(
                question,
                "study",
                ckl_version_fingerprint="ckl-fingerprint",
                framework_version_fingerprint=fingerprint,
            )

        self.assertIsNone(hit)
        self.assertEqual(cache.last_lookup_status, "filtered")

    def test_lookup_invalidates_stale_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "public-cache.json"
            cache = JsonPublicAnswerCache(path)
            question = normalize_public_question("Why did Israel renew the covenant at Shechem?")
            old_framework_fingerprint = "old-framework-fingerprint"
            old_ckl_fingerprint = "old-ckl-fingerprint"
            cache.store(
                PublicCacheEntry(
                    normalized_question=question,
                    answer_mode="study",
                    answer="Israel renewed the covenant at Shechem.",
                    quality_score=95.0,
                    review_status="approved",
                    framework_version="0.1.0",
                    framework_version_fingerprint=old_framework_fingerprint,
                    ckl_version_fingerprint=old_ckl_fingerprint,
                    object_dependency_ids=("shechem", "abraham", "joshua"),
                    expires_at="2030-01-01T00:00:00Z",
                )
            )

            hit = cache.lookup(
                question,
                "study",
                ckl_version_fingerprint="new-ckl-fingerprint",
                framework_version_fingerprint="new-framework-fingerprint",
            )

            state = json.loads(path.read_text(encoding="utf-8"))
            entry = state["entries"][public_cache_key(question, "study")]

        self.assertIsNone(hit)
        self.assertEqual(cache.last_lookup_status, "stale")
        self.assertIn("changed", cache.last_lookup_reason or "")
        self.assertIsNotNone(entry["invalidated_at"])
        self.assertTrue(entry["invalidated_reason"])


if __name__ == "__main__":
    unittest.main()
