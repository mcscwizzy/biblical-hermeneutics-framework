import os
import unittest
from pathlib import Path
from unittest.mock import patch

from bhf_agent.config import AgentConfig
from bhf_web.ai_config import (
    DEFAULT_OPENROUTER_MODEL,
    OPENROUTER_BASE_URL,
    browser_ai_config,
)
from bhf_web.forms import config_from_form, load_web_defaults


ROOT = Path(__file__).resolve().parents[1]


class AISetupConfigurationTests(unittest.TestCase):
    def test_central_openrouter_defaults_are_exposed(self):
        loaded = load_web_defaults(path=ROOT / ".missing-bhf-web-config.json")
        self.assertEqual(loaded.config.max_tokens, 2048)
        self.assertEqual(loaded.config.context_window, 12288)
        self.assertEqual(
            browser_ai_config()["providerDefaults"]["openrouter"],
            {"max_tokens": 4096, "context_window": 16384},
        )
        self.assertEqual(loaded.config.runtime_profile_mode, "compact")
        self.assertFalse(loaded.config.memory_enabled)

    def test_openrouter_uses_fixed_base_url_and_central_default_model(self):
        defaults = AgentConfig(
            adapter="openai_compatible",
            base_url="http://localhost:11434/v1",
            model="llama3.1:8b",
            temperature=0.3,
        )
        config = config_from_form(
            {
                "adapter": "openrouter",
                "model": "",
                "base_url": "https://attacker.example.invalid/",
                "max_tokens": "2048",
                "context_window": "12288",
            },
            defaults,
            transient_api_key="test-key",
        )
        self.assertEqual(config.model, DEFAULT_OPENROUTER_MODEL)
        self.assertEqual(config.base_url, OPENROUTER_BASE_URL)

    def test_openrouter_web_defaults_use_recommended_token_budgets(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openrouter",
                "BHF_BASE_URL": OPENROUTER_BASE_URL,
                "BHF_API_KEY": "test-key",
            },
            clear=True,
        ):
            loaded = load_web_defaults(path=ROOT / ".missing-bhf-web-config.json")
        self.assertEqual(loaded.config.adapter, "openrouter")
        self.assertEqual(loaded.config.max_tokens, 4096)
        self.assertEqual(loaded.config.context_window, 16384)

    def test_normal_web_form_does_not_render_removed_controls(self):
        template = (ROOT / "bhf_web" / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('name="temperature"', template)
        self.assertNotIn('name="memory_enabled"', template)
        self.assertNotIn('name="session_id"', template)
        self.assertNotIn('name="memory_path"', template)
        self.assertNotIn('name="memory_max_turns"', template)
        self.assertIn("data-ai-setup", template)
        self.assertIn("data-ai-continue-without", template)

    def test_callback_and_service_worker_security_markers_exist(self):
        model_settings = (ROOT / "bhf_web" / "static" / "model-settings.js").read_text(encoding="utf-8")
        service_worker = (ROOT / "bhf_web" / "static" / "sw.js").read_text(encoding="utf-8")
        self.assertIn('code_challenge_method: "S256"', model_settings)
        self.assertIn("sessionStorage", model_settings)
        self.assertIn("replaceState", model_settings)
        self.assertIn("ciphertext", model_settings)
        self.assertIn("isAuthCallbackUrl", service_worker)
        self.assertIn("event.respondWith(fetch(event.request))", service_worker)

    def test_initial_ai_setup_does_not_cover_translation_workflows(self):
        model_settings = (ROOT / "bhf_web" / "static" / "model-settings.js").read_text(encoding="utf-8")

        self.assertIn('document.body?.classList.contains("translation-selector-open")', model_settings)
        self.assertIn('return false;', model_settings)


if __name__ == "__main__":
    unittest.main()
