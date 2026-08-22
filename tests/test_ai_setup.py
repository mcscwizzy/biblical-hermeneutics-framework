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
            {
                "max_tokens": 1536,
                "context_window": 8192,
                "timeout_seconds": 120,
            },
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
        self.assertEqual(config.model, "openrouter/free")
        self.assertEqual(config.base_url, OPENROUTER_BASE_URL)

    def test_openrouter_catalog_recommends_router_and_keeps_specific_free_models(self):
        openrouter = browser_ai_config()["openrouter"]
        models = openrouter["models"]
        model_ids = [model["id"] for model in models]
        recommended = [model for model in models if model.get("recommended")]

        self.assertEqual(openrouter["defaultModel"], "openrouter/free")
        self.assertEqual(
            recommended,
            [
                {
                    "id": "openrouter/free",
                    "label": "OpenRouter Free Router",
                    "description": "Automatically routes to an available free model.",
                    "recommended": True,
                }
            ],
        )
        self.assertEqual(
            model_ids,
            [
                "openrouter/free",
                "google/gemma-4-26b-a4b-it:free",
                "google/gemma-4-31b-it:free",
                "nvidia/nemotron-3-ultra-550b-a55b:free",
                "openai/gpt-oss-120b:free",
            ],
        )

    def test_openrouter_preserves_explicit_specific_model_selection(self):
        defaults = AgentConfig(
            adapter="openai_compatible",
            base_url="http://localhost:11434/v1",
            model="llama3.1:8b",
        )

        config = config_from_form(
            {
                "adapter": "openrouter",
                "model": "google/gemma-4-26b-a4b-it:free",
            },
            defaults,
            transient_api_key="test-key",
        )

        self.assertEqual(config.model, "google/gemma-4-26b-a4b-it:free")

    def test_openrouter_preserves_explicit_configured_default_model(self):
        defaults = AgentConfig(
            adapter="openrouter",
            base_url=OPENROUTER_BASE_URL,
            model="google/gemma-4-26b-a4b-it:free",
            api_key="configured-key",
        )

        config = config_from_form(
            {"adapter": "openrouter", "model": ""},
            defaults,
        )

        self.assertEqual(config.model, "google/gemma-4-26b-a4b-it:free")

    def test_openrouter_preserves_explicit_environment_model(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openrouter",
                "BHF_BASE_URL": OPENROUTER_BASE_URL,
                "BHF_MODEL": "google/gemma-4-26b-a4b-it:free",
                "BHF_API_KEY": "test-key",
            },
            clear=True,
        ):
            loaded = load_web_defaults(path=ROOT / ".missing-bhf-web-config.json")

        self.assertEqual(loaded.config.model, "google/gemma-4-26b-a4b-it:free")

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
        self.assertEqual(loaded.config.model, "openrouter/free")
        self.assertEqual(loaded.config.max_tokens, 1536)
        self.assertEqual(loaded.config.context_window, 8192)
        self.assertEqual(loaded.config.timeout_seconds, 120)

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

    def test_provider_switch_applies_provider_specific_runtime_limits(self):
        model_settings = (ROOT / "bhf_web" / "static" / "model-settings.js").read_text(encoding="utf-8")

        self.assertIn("field.value = saved[key]", model_settings)
        self.assertNotIn(
            'field && (!field.value || field.dataset.modelSettingsManaged === "true")',
            model_settings,
        )
        self.assertIn("settings.activeProvider = currentProvider(form)", model_settings)


if __name__ == "__main__":
    unittest.main()
