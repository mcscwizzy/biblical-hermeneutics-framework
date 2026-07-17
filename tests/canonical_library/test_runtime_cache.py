import unittest

from framework.canonical_library import (
    CKLRuntimeCache,
    build_context_cache_key,
    build_model_signature,
    build_retrieval_cache_key,
    build_response_cache_key,
)


class RuntimeCacheTests(unittest.TestCase):
    def test_retrieval_cache_key_changes_with_inventory_and_settings(self):
        base = build_retrieval_cache_key(
            canonical_query="Why did Joshua renew the covenant at Shechem?",
            inventory_fingerprint="inventory-a",
            answer_mode="study",
            max_results=5,
            include_placeholders=False,
            allowed_statuses=("approved", "reviewed"),
            max_context_tokens=1200,
        )
        changed_inventory = build_retrieval_cache_key(
            canonical_query="Why did Joshua renew the covenant at Shechem?",
            inventory_fingerprint="inventory-b",
            answer_mode="study",
            max_results=5,
            include_placeholders=False,
            allowed_statuses=("approved", "reviewed"),
            max_context_tokens=1200,
        )
        changed_limits = build_retrieval_cache_key(
            canonical_query="Why did Joshua renew the covenant at Shechem?",
            inventory_fingerprint="inventory-a",
            answer_mode="study",
            max_results=8,
            include_placeholders=False,
            allowed_statuses=("approved", "reviewed"),
            max_context_tokens=1200,
        )

        self.assertNotEqual(base, changed_inventory)
        self.assertNotEqual(base, changed_limits)

    def test_context_cache_key_changes_with_entry_version(self):
        base = build_context_cache_key(
            canonical_query="Why did Joshua renew the covenant at Shechem?",
            retrieved_topics=[
                {"id": "places.shechem", "object_version": "1"},
                {"id": "people.joshua", "object_version": "4"},
            ],
            answer_mode="study",
            max_context_tokens=1200,
            prompt_mode="summary",
            prompt_version="phase12-v1",
        )
        changed = build_context_cache_key(
            canonical_query="Why did Joshua renew the covenant at Shechem?",
            retrieved_topics=[
                {"id": "places.shechem", "object_version": "2"},
                {"id": "people.joshua", "object_version": "4"},
            ],
            answer_mode="study",
            max_context_tokens=1200,
            prompt_mode="summary",
            prompt_version="phase12-v1",
        )

        self.assertNotEqual(base, changed)

    def test_response_cache_key_changes_with_prompt_version(self):
        model_signature = build_model_signature(
            adapter="openai_compatible",
            base_url="http://localhost:1234/v1",
            model="fake-model",
            temperature=0.3,
            max_tokens=2048,
        )
        base = build_response_cache_key(
            normalized_question="Why did Joshua renew the covenant at Shechem?",
            prompt_context_hash="prompt:alpha",
            model_signature=model_signature,
            response_contract="answer",
            prompt_version="phase12-v1",
        )
        changed = build_response_cache_key(
            normalized_question="Why did Joshua renew the covenant at Shechem?",
            prompt_context_hash="prompt:alpha",
            model_signature=model_signature,
            response_contract="answer",
            prompt_version="phase12-v2",
        )

        self.assertNotEqual(base, changed)

    def test_runtime_cache_eviction_discards_oldest_entries(self):
        cache = CKLRuntimeCache(enabled=True, max_entries=1)

        cache.store_retrieval("retrieval:first", {"id": "first"})
        cache.store_retrieval("retrieval:second", {"id": "second"})

        self.assertIsNone(cache.lookup_retrieval("retrieval:first"))
        self.assertEqual(cache.lookup_retrieval("retrieval:second"), {"id": "second"})

        snapshot = cache.snapshot()
        self.assertEqual(snapshot["retrieval"]["stores"], 2)
        self.assertEqual(snapshot["retrieval"]["evictions"], 1)
        self.assertEqual(snapshot["retrieval"]["hits"], 1)
        self.assertEqual(snapshot["retrieval"]["misses"], 1)


if __name__ == "__main__":
    unittest.main()
