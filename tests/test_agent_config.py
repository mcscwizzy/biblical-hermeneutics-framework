import argparse
import json
import tempfile
import unittest
from pathlib import Path

from bhf_agent.__main__ import config_from_args
from bhf_agent.config import AgentConfig, ConfigError


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
                base_url=None,
                model="override-model",
                temperature=0.1,
                max_tokens=None,
                show_debug=True,
            )

            config = config_from_args(args)

        self.assertEqual(config.profile, "scholar")
        self.assertEqual(config.model, "override-model")
        self.assertEqual(config.temperature, 0.1)
        self.assertTrue(config.debug)

    def test_missing_required_openai_compatible_values_are_clear(self):
        with self.assertRaisesRegex(ConfigError, "base_url is required"):
            AgentConfig.from_mapping({"model": "local-model"})

    def test_api_key_is_redacted_when_serialized(self):
        config = AgentConfig(
            base_url="http://localhost:1234/v1",
            model="local-model",
            api_key="secret",
        )

        self.assertEqual(config.to_dict()["api_key"], "<redacted>")


if __name__ == "__main__":
    unittest.main()
