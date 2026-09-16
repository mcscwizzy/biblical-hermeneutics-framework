import os
from unittest.mock import patch

from bhf_web.runtime import load_runtime_config


def test_runtime_config_exposes_generic_assistant_destination():
    with patch.dict(os.environ, {}, clear=True):
        config = load_runtime_config()

    assert config["assistantUrl"].startswith("https://chatgpt.com/")
    assert "ai" not in config


def test_runtime_config_uses_configured_assistant_destination():
    with patch.dict(
        os.environ,
        {"BHF_ASSISTANT_URL": "https://assistant.example/bhf"},
        clear=True,
    ):
        config = load_runtime_config()

    assert config["assistantUrl"] == "https://assistant.example/bhf"
