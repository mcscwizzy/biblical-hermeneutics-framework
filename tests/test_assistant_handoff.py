import os
from unittest.mock import patch

from bhf_web.runtime import load_runtime_config


def _runtime_route_paths():
    from bhf_web.app import create_app

    return {
        route.path
        for route in create_app().routes
        if getattr(route, "path", None)
    }


def test_runtime_app_has_no_interactive_ai_routes():
    """Removing runtime inference must make its public route surface unreachable."""
    routes = _runtime_route_paths()

    assert "/api/llm/health" not in routes
    assert "/ask" not in routes
    assert not any(route.startswith("/ask/") for route in routes)
    assert not any(route.startswith("/api/study/presentation") for route in routes)
    assert not any(route.startswith("/api/bible/search/fallback") for route in routes)


def test_deterministic_companion_context_route_remains():
    """The web reader still exposes deterministic companion-context data."""
    assert "/api/study/companion-context" in _runtime_route_paths()


def test_companion_context_has_no_runtime_provider_enhancement_method():
    from bhf_web.services.companion_context import CompanionContextService

    assert not hasattr(CompanionContextService, "enhance_presentation")


def test_runtime_config_exposes_generic_assistant_destination():
    with patch.dict(os.environ, {}, clear=True):
        config = load_runtime_config()

    assert config["assistantUrl"].startswith("https://chatgpt.com/")
    assert "ai" not in config
    assert "asyncJobs" not in config
    assert "presentationTransport" not in config
    assert "presentationJobs" not in config


def test_runtime_config_uses_configured_assistant_destination():
    with patch.dict(
        os.environ,
        {"BHF_ASSISTANT_URL": "https://assistant.example/bhf"},
        clear=True,
    ):
        config = load_runtime_config()

    assert config["assistantUrl"] == "https://assistant.example/bhf"


def test_runtime_config_uses_default_for_blank_assistant_destination():
    for value in ("", "   ", "\t\n"):
        with patch.dict(os.environ, {"BHF_ASSISTANT_URL": value}, clear=True):
            config = load_runtime_config()

        assert config["assistantUrl"].startswith("https://chatgpt.com/")
