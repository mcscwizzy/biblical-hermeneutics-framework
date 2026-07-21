import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path

from bhf_agent.__main__ import config_from_args
from bhf_agent.config import (
    AgentConfig,
    CanonicalLibraryConfig,
    ConfigError,
    ObservabilityConfig,
    PublicCacheConfig,
)


class AgentConfigTests(unittest.TestCase):
    def test_load_config_from_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.json"
            path.write_text(
                json.dumps(
                    {
                        "config_version": 1,
                        "adapter": "openai_compatible",
                        "base_url": "http://localhost:1234/v1",
                        "api_key": "local",
                        "model": "local-model",
                        "profile": "minimal-7b",
                        "temperature": 0.3,
                        "max_tokens": 2048,
                        "timeout_seconds": 120,
                        "show_method_notes": True,
                        "debug": False,
                    }
                ),
                encoding="utf-8",
            )

            config = AgentConfig.from_json_file(path)

        self.assertEqual(config.adapter, "openai_compatible")
        self.assertEqual(config.profile, "minimal-7b")
        self.assertEqual(config.model, "local-model")
        self.assertEqual(config.context_window, 12288)
        self.assertEqual(config.response_format_policy, "auto")
        self.assertEqual(config.runtime_profile_mode, "compact")

    def test_response_format_policy_accepts_supported_values(self):
        for policy in ("auto", "json_schema", "json_object", "off"):
            config = AgentConfig.from_mapping(
                {
                    "adapter": "ollama",
                    "base_url": "http://ollama:11434",
                    "model": "gemma2:2b",
                    "profile": "minimal-7b",
                    "response_format_policy": policy,
                }
            )
            self.assertEqual(config.response_format_policy, policy)

    def test_response_format_policy_rejects_unknown_value(self):
        with self.assertRaisesRegex(ConfigError, "response_format_policy"):
            AgentConfig.from_mapping(
                {
                    "adapter": "ollama",
                    "base_url": "http://ollama:11434",
                    "model": "gemma2:2b",
                    "profile": "minimal-7b",
                    "response_format_policy": "xml",
                }
            )

    def test_cli_overrides_config_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.json"
            path.write_text(
                json.dumps(
                    {
                        "config_version": 1,
                        "adapter": "openai_compatible",
                        "base_url": "http://localhost:1234/v1",
                        "model": "original-model",
                        "profile": "standard",
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                config=str(path),
                profile="scholar",
                answer_mode=None,
                base_url=None,
                model="override-model",
                temperature=0.1,
                max_tokens=None,
                auto_repair=None,
                max_repair_attempts=None,
                repair_threshold=None,
                show_debug=True,
            )

            config = config_from_args(args)

        self.assertEqual(config.profile, "scholar")
        self.assertEqual(config.model, "override-model")
        self.assertEqual(config.temperature, 0.1)
        self.assertTrue(config.debug)

    def test_old_config_without_repair_fields_uses_defaults(self):
        config = AgentConfig.from_mapping(
            {
                "config_version": 1,
                "adapter": "openai_compatible",
                "base_url": "http://localhost:1234/v1",
                "model": "local-model",
                "profile": "minimal-7b",
            }
        )

        self.assertFalse(config.auto_repair)
        self.assertEqual(config.max_repair_attempts, 1)
        self.assertEqual(config.repair_threshold, 80)
        self.assertEqual(config.answer_mode, "study")
        self.assertEqual(config.runtime_profile_mode, "compact")
        self.assertEqual(config.max_tokens, 8192)
        self.assertEqual(config.context_window, 12288)
        self.assertFalse(config.memory_enabled)
        self.assertIsNone(config.session_id)
        self.assertIsNone(config.memory_path)
        self.assertEqual(config.memory_max_turns, 8)
        self.assertTrue(config.canonical_library.enabled)
        self.assertFalse(config.canonical_library.shadow_mode)
        self.assertTrue(config.canonical_library.fallback_to_model)
        self.assertFalse(config.canonical_library.strict_mode)
        self.assertEqual(config.canonical_library.minimum_relevance_score, 0.85)
        self.assertFalse(config.canonical_library.include_placeholders)
        self.assertEqual(
            config.canonical_library.allowed_statuses,
            ("in_review", "reviewed", "approved"),
        )
        self.assertFalse(config.public_cache.enabled)
        self.assertEqual(
            config.public_cache.path,
            ".bhf/public-answer-cache.json",
        )
        self.assertEqual(
            config.public_cache.allowed_review_statuses,
            ("reviewed", "approved"),
        )
        self.assertTrue(config.lexicon.enabled)
        self.assertEqual(config.lexicon.database_path, ".bhf/ckl.sqlite")
        self.assertEqual(config.lexicon.max_occurrences, 5)
        self.assertEqual(config.lexicon.max_prompt_tokens, 350)
        self.assertFalse(config.lexicon.include_full_definitions)

    def test_runtime_profile_mode_accepts_supported_values(self):
        for mode in ("compact", "full"):
            with self.subTest(mode=mode):
                config = AgentConfig.from_mapping(
                    {
                        "adapter": "ollama",
                        "base_url": "http://ollama:11434",
                        "model": "gemma2:2b",
                        "profile": "minimal-7b",
                        "runtime_profile_mode": mode,
                    }
                )
                self.assertEqual(config.runtime_profile_mode, mode)

    def test_runtime_profile_mode_rejects_unknown_value(self):
        with self.assertRaisesRegex(ConfigError, "runtime_profile_mode must be one of"):
            AgentConfig.from_mapping(
                {
                    "adapter": "ollama",
                    "base_url": "http://ollama:11434",
                    "model": "gemma2:2b",
                    "profile": "minimal-7b",
                    "runtime_profile_mode": "profile-md",
                }
            )

    def test_config_accepts_canonical_library_section(self):
        config = AgentConfig.from_mapping(
            {
                "config_version": 1,
                "adapter": "openai_compatible",
                "base_url": "http://localhost:1234/v1",
                "model": "local-model",
                "profile": "standard",
                "canonical_library": {
                    "enabled": True,
                    "shadow_mode": True,
                    "fallback_to_model": False,
                    "strict_mode": True,
                    "minimum_relevance_score": 0.9,
                    "max_results": 4,
                    "max_context_tokens": 900,
                    "include_placeholders": False,
                    "allowed_statuses": ["approved", "reviewed"],
                },
            }
        )

        self.assertTrue(config.canonical_library.enabled)
        self.assertTrue(config.canonical_library.shadow_mode)
        self.assertFalse(config.canonical_library.fallback_to_model)
        self.assertTrue(config.canonical_library.strict_mode)
        self.assertEqual(config.canonical_library.minimum_relevance_score, 0.9)
        self.assertEqual(config.canonical_library.max_results, 4)
        self.assertEqual(config.canonical_library.max_context_tokens, 900)
        self.assertFalse(config.canonical_library.include_placeholders)
        self.assertEqual(config.canonical_library.allowed_statuses, ("approved", "reviewed"))

    def test_config_serializes_canonical_library_section(self):
        config = AgentConfig(
            base_url="http://localhost:1234/v1",
            model="local-model",
            canonical_library=CanonicalLibraryConfig(
                enabled=False,
                shadow_mode=True,
                fallback_to_model=False,
                strict_mode=True,
                minimum_relevance_score=0.9,
                cache_enabled=False,
                cache_max_entries=96,
                max_results=3,
                max_context_tokens=750,
                include_placeholders=False,
                allowed_statuses=("approved",),
            ),
        )

        self.assertFalse(config.to_dict()["canonical_library"]["cache_enabled"])
        self.assertEqual(config.to_dict()["canonical_library"]["cache_max_entries"], 96)
        self.assertEqual(config.to_dict()["canonical_library"]["max_results"], 3)
        self.assertFalse(config.to_dict()["canonical_library"]["enabled"])
        self.assertTrue(config.to_dict()["canonical_library"]["shadow_mode"])
        self.assertFalse(config.to_dict()["canonical_library"]["fallback_to_model"])
        self.assertTrue(config.to_dict()["canonical_library"]["strict_mode"])
        self.assertEqual(config.to_dict()["canonical_library"]["minimum_relevance_score"], 0.9)
        self.assertEqual(
            config.to_dict()["canonical_library"]["allowed_statuses"],
            ("approved",),
        )

    def test_config_accepts_canonical_library_cache_settings(self):
        config = AgentConfig.from_mapping(
            {
                "config_version": 1,
                "adapter": "openai_compatible",
                "base_url": "http://localhost:1234/v1",
                "model": "local-model",
                "profile": "standard",
                "canonical_library": {
                    "enabled": True,
                    "cache_enabled": True,
                    "cache_max_entries": 128,
                    "max_results": 4,
                    "max_context_tokens": 900,
                },
            }
        )

        self.assertTrue(config.canonical_library.cache_enabled)
        self.assertEqual(config.canonical_library.cache_max_entries, 128)

    def test_config_rejects_invalid_canonical_library_cache_size(self):
        with self.assertRaisesRegex(ConfigError, "cache_max_entries"):
            AgentConfig.from_mapping(
                {
                    "config_version": 1,
                    "adapter": "openai_compatible",
                    "base_url": "http://localhost:1234/v1",
                    "model": "local-model",
                    "profile": "standard",
                    "canonical_library": {
                        "cache_max_entries": 0,
                    },
                }
            )

    def test_config_rejects_invalid_canonical_library_relevance_threshold(self):
        with self.assertRaisesRegex(ConfigError, "minimum_relevance_score"):
            AgentConfig.from_mapping(
                {
                    "config_version": 1,
                    "adapter": "openai_compatible",
                    "base_url": "http://localhost:1234/v1",
                    "model": "local-model",
                    "profile": "standard",
                    "canonical_library": {
                        "minimum_relevance_score": 1.5,
                    },
                }
            )

    def test_config_accepts_public_cache_section(self):
        config = AgentConfig.from_mapping(
            {
                "config_version": 1,
                "adapter": "openai_compatible",
                "base_url": "http://localhost:1234/v1",
                "model": "local-model",
                "profile": "standard",
                "public_cache": {
                    "enabled": True,
                    "path": ".bhf/custom-public-cache.json",
                    "minimum_quality_score": 92.5,
                    "default_ttl_days": 90,
                    "allowed_review_statuses": ["approved"],
                },
            }
        )

        self.assertTrue(config.public_cache.enabled)
        self.assertEqual(config.public_cache.path, ".bhf/custom-public-cache.json")
        self.assertEqual(config.public_cache.minimum_quality_score, 92.5)
        self.assertEqual(config.public_cache.default_ttl_days, 90)
        self.assertEqual(config.public_cache.allowed_review_statuses, ("approved",))

    def test_config_accepts_lexicon_section(self):
        config = AgentConfig.from_mapping(
            {
                "config_version": 1,
                "adapter": "openai_compatible",
                "base_url": "http://localhost:1234/v1",
                "model": "local-model",
                "profile": "standard",
                "lexicon": {
                    "enabled": True,
                    "database_path": ".bhf/custom-lexicon.sqlite",
                    "max_occurrences": 3,
                    "max_prompt_tokens": 250,
                    "include_full_definitions": True,
                    "allow_model_context_explanation": False,
                },
            }
        )

        self.assertTrue(config.lexicon.enabled)
        self.assertEqual(config.lexicon.database_path, ".bhf/custom-lexicon.sqlite")
        self.assertEqual(config.lexicon.max_occurrences, 3)
        self.assertEqual(config.lexicon.max_prompt_tokens, 250)
        self.assertTrue(config.lexicon.include_full_definitions)
        self.assertFalse(config.lexicon.allow_model_context_explanation)

    def test_config_rejects_invalid_lexicon_section(self):
        with self.assertRaisesRegex(ConfigError, "lexicon.max_occurrences"):
            AgentConfig.from_mapping(
                {
                    "config_version": 1,
                    "adapter": "openai_compatible",
                    "base_url": "http://localhost:1234/v1",
                    "model": "local-model",
                    "profile": "standard",
                    "lexicon": {"max_occurrences": 0},
                }
            )

    def test_lexicon_env_overrides_apply_without_config_section(self):
        previous = {
            key: os.environ.get(key)
            for key in (
                "BHF_LEXICON_ENABLED",
                "BHF_LEXICON_DATABASE_PATH",
                "BHF_LEXICON_MAX_OCCURRENCES",
                "BHF_LEXICON_MAX_PROMPT_TOKENS",
            )
        }
        os.environ["BHF_LEXICON_ENABLED"] = "false"
        os.environ["BHF_LEXICON_DATABASE_PATH"] = ".bhf/env-lexicon.sqlite"
        os.environ["BHF_LEXICON_MAX_OCCURRENCES"] = "7"
        os.environ["BHF_LEXICON_MAX_PROMPT_TOKENS"] = "275"
        try:
            config = AgentConfig.from_mapping(
                {
                    "config_version": 1,
                    "adapter": "openai_compatible",
                    "base_url": "http://localhost:1234/v1",
                    "model": "local-model",
                    "profile": "standard",
                }
            )
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertFalse(config.lexicon.enabled)
        self.assertEqual(config.lexicon.database_path, ".bhf/env-lexicon.sqlite")
        self.assertEqual(config.lexicon.max_occurrences, 7)
        self.assertEqual(config.lexicon.max_prompt_tokens, 275)

    def test_config_allows_public_cache_when_canonical_library_runs_in_shadow_mode(self):
        config = AgentConfig.from_mapping(
            {
                "config_version": 1,
                "adapter": "openai_compatible",
                "base_url": "http://localhost:1234/v1",
                "model": "local-model",
                "profile": "standard",
                "public_cache": {
                    "enabled": True,
                },
                "canonical_library": {
                    "enabled": False,
                    "shadow_mode": True,
                },
            }
        )

        self.assertTrue(config.public_cache.enabled)
        self.assertFalse(config.canonical_library.enabled)
        self.assertTrue(config.canonical_library.shadow_mode)

    def test_config_serializes_public_cache_section(self):
        config = AgentConfig(
            base_url="http://localhost:1234/v1",
            model="local-model",
            public_cache=PublicCacheConfig(
                enabled=True,
                path=".bhf/public-cache.json",
                minimum_quality_score=91.0,
                default_ttl_days=120,
                allowed_review_statuses=("reviewed",),
            ),
        )

        self.assertTrue(config.to_dict()["public_cache"]["enabled"])
        self.assertEqual(config.to_dict()["public_cache"]["path"], ".bhf/public-cache.json")
        self.assertEqual(config.to_dict()["public_cache"]["minimum_quality_score"], 91.0)
        self.assertEqual(config.to_dict()["public_cache"]["allowed_review_statuses"], ("reviewed",))

    def test_config_accepts_observability_section(self):
        config = AgentConfig.from_mapping(
            {
                "config_version": 1,
                "adapter": "openai_compatible",
                "base_url": "http://localhost:1234/v1",
                "model": "local-model",
                "profile": "standard",
                "observability": {
                    "enabled": True,
                    "verbose": True,
                    "redact_sensitive": False,
                },
            }
        )

        self.assertTrue(config.observability.enabled)
        self.assertTrue(config.observability.verbose)
        self.assertFalse(config.observability.redact_sensitive)

    def test_config_serializes_observability_section(self):
        config = AgentConfig(
            base_url="http://localhost:1234/v1",
            model="local-model",
            observability=ObservabilityConfig(
                enabled=True,
                verbose=False,
                redact_sensitive=False,
            ),
        )

        self.assertTrue(config.to_dict()["observability"]["enabled"])
        self.assertFalse(config.to_dict()["observability"]["verbose"])
        self.assertFalse(config.to_dict()["observability"]["redact_sensitive"])

    def test_config_accepts_valid_answer_modes(self):
        for answer_mode in ("concise", "study", "teaching", "scholar"):
            with self.subTest(answer_mode=answer_mode):
                config = AgentConfig.from_mapping(
                    {
                        "config_version": 1,
                        "adapter": "openai_compatible",
                        "base_url": "http://localhost:1234/v1",
                        "model": "local-model",
                        "profile": "standard",
                        "answer_mode": answer_mode,
                    }
                )

                self.assertEqual(config.answer_mode, answer_mode)

    def test_config_accepts_ollama_adapter(self):
        config = AgentConfig.from_mapping(
            {
                "config_version": 1,
                "adapter": "ollama",
                "base_url": "http://ollama:11434",
                "model": "qwen2.5:0.5b",
                "profile": "standard",
            }
        )

        self.assertEqual(config.adapter, "ollama")
        self.assertEqual(config.base_url, "http://ollama:11434")

    def test_config_rejects_invalid_answer_mode(self):
        with self.assertRaisesRegex(ConfigError, "answer_mode must be one of"):
            AgentConfig.from_mapping(
                {
                    "config_version": 1,
                    "adapter": "openai_compatible",
                    "base_url": "http://localhost:1234/v1",
                    "model": "local-model",
                    "profile": "standard",
                    "answer_mode": "doctrine",
                }
            )

    def test_cli_repair_overrides_config_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.json"
            path.write_text(
                json.dumps(
                    {
                        "config_version": 1,
                        "adapter": "openai_compatible",
                        "base_url": "http://localhost:1234/v1",
                        "model": "local-model",
                        "profile": "standard",
                        "auto_repair": False,
                        "max_repair_attempts": 0,
                        "repair_threshold": 70,
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                config=str(path),
                profile=None,
                answer_mode=None,
                base_url=None,
                model=None,
                temperature=None,
                max_tokens=None,
                auto_repair=True,
                max_repair_attempts=1,
                repair_threshold=85,
                show_debug=False,
            )

            config = config_from_args(args)

        self.assertTrue(config.auto_repair)
        self.assertEqual(config.max_repair_attempts, 1)
        self.assertEqual(config.repair_threshold, 85)

    def test_cli_answer_mode_overrides_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.json"
            path.write_text(
                json.dumps(
                    {
                        "config_version": 1,
                        "adapter": "openai_compatible",
                        "base_url": "http://localhost:1234/v1",
                        "model": "local-model",
                        "profile": "standard",
                        "answer_mode": "study",
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                config=str(path),
                profile=None,
                answer_mode="teaching",
                base_url=None,
                model=None,
                temperature=None,
                max_tokens=None,
                auto_repair=None,
                max_repair_attempts=None,
                repair_threshold=None,
                show_debug=False,
            )

            config = config_from_args(args)

        self.assertEqual(config.answer_mode, "teaching")

    def test_cli_no_repair_disables_repair(self):
        args = argparse.Namespace(
            config=None,
            profile=None,
            answer_mode=None,
            base_url="http://localhost:1234/v1",
            model="local-model",
            temperature=None,
            max_tokens=None,
            auto_repair=False,
            max_repair_attempts=None,
            repair_threshold=None,
            show_debug=False,
        )

        config = config_from_args(args)

        self.assertFalse(config.auto_repair)

    def test_cli_memory_overrides_config_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.json"
            path.write_text(
                json.dumps(
                    {
                        "config_version": 1,
                        "adapter": "openai_compatible",
                        "base_url": "http://localhost:1234/v1",
                        "model": "local-model",
                        "profile": "standard",
                        "memory_enabled": False,
                        "memory_max_turns": 8,
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                config=str(path),
                profile=None,
                answer_mode=None,
                base_url=None,
                model=None,
                temperature=None,
                max_tokens=None,
                auto_repair=None,
                max_repair_attempts=None,
                repair_threshold=None,
                memory_enabled=True,
                session_id="lesson-1",
                memory_path=str(Path(tmp) / "sessions"),
                memory_max_turns=3,
                show_debug=False,
            )

            config = config_from_args(args)

        self.assertTrue(config.memory_enabled)
        self.assertEqual(config.session_id, "lesson-1")
        self.assertEqual(config.memory_max_turns, 3)

    def test_config_rejects_invalid_memory_max_turns(self):
        with self.assertRaisesRegex(ConfigError, "memory_max_turns"):
            AgentConfig.from_mapping(
                {
                    "config_version": 1,
                    "adapter": "openai_compatible",
                    "base_url": "http://localhost:1234/v1",
                    "model": "local-model",
                    "profile": "standard",
                    "memory_max_turns": 0,
                }
            )

    def test_missing_required_openai_compatible_values_are_clear(self):
        with self.assertRaisesRegex(ConfigError, "base_url is required"):
            AgentConfig.from_mapping({"model": "local-model"})

    def test_missing_required_ollama_values_are_clear(self):
        with self.assertRaisesRegex(ConfigError, "base_url is required"):
            AgentConfig.from_mapping(
                {
                    "adapter": "ollama",
                    "model": "qwen2.5:0.5b",
                    "profile": "standard",
                }
            )

    def test_api_key_is_redacted_when_serialized(self):
        config = AgentConfig(
            base_url="http://localhost:1234/v1",
            model="local-model",
            api_key="secret",
        )

        self.assertEqual(config.to_dict()["api_key"], "<redacted>")


if __name__ == "__main__":
    unittest.main()
