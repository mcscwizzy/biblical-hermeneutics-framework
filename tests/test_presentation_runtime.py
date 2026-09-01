from __future__ import annotations

import json

from bhf_agent.config import AgentConfig
from bhf_agent.models import ChatResponse
from bhf_agent.presentation import (
    PRESENTATION_BUNDLE_FORMAT,
    PRESENTATION_BUNDLE_VERSION,
    build_evidence_bundle,
    deterministic_presentation,
)
from bhf_agent.presentation.providers import PRESENTATION_PROMPT_VERSION
from bhf_web.presentation_runtime import (
    DEFAULT_MAXIMUM_CONCURRENT_PRESENTATION_REQUESTS,
    DEFAULT_PRESENTATION_TIMEOUT_SECONDS,
    MAXIMUM_CONCURRENT_PRESENTATION_REQUESTS,
    MAXIMUM_PRESENTATION_TIMEOUT_SECONDS,
    configure_presentation_runtime,
    load_presentation_runtime_settings,
)


def _agent_config(*, timeout_seconds: float = 600) -> AgentConfig:
    return AgentConfig(
        adapter="openai_compatible",
        base_url="https://provider.invalid/v1",
        model="fixture-model",
        timeout_seconds=timeout_seconds,
    )


def _bundle():
    return build_evidence_bundle(
        "Mark 5:1",
        geography={
            "places": [
                {
                    "id": "gerasa",
                    "title": "Gerasa",
                    "summary": "Gerasa lies east of the Sea of Galilee.",
                    "confidence": "likely",
                }
            ],
            "routes": [],
        },
    )


def _write_bundle(path, bundle):
    packet = deterministic_presentation(bundle).to_dict()
    packet["generated_from"]["prompt_version"] = PRESENTATION_PROMPT_VERSION
    packet["generated_from"]["model"] = "pre-generated-fixture"
    path.write_text(
        json.dumps(
            {
                "format": PRESENTATION_BUNDLE_FORMAT,
                "version": PRESENTATION_BUNDLE_VERSION,
                "packets": [packet],
            }
        ),
        encoding="utf-8",
    )


class _ValidAdapter:
    def __init__(self) -> None:
        self.requests = []

    def supports_json_schema_response_format(self) -> bool:
        return False

    def chat(self, request):
        self.requests.append(request)
        supplied = json.loads(request.user_prompt)
        return ChatResponse(
            text=json.dumps(
                {
                    "passage_ref": supplied["passage_ref"],
                    "cards": [],
                    "generated_from": supplied["generated_from_must_equal"],
                }
            )
        )


class _FailingAdapter(_ValidAdapter):
    def chat(self, request):
        self.requests.append(request)
        raise TimeoutError("fixture deadline")


def test_legacy_environment_flag_is_only_an_off_browser_default(tmp_path):
    adapter = _ValidAdapter()
    adapter_calls = []

    def adapter_factory(config):
        adapter_calls.append(config)
        return adapter

    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={},
        agent_config=_agent_config(),
        adapter_factory=adapter_factory,
    )

    result = runtime.engine.present(_bundle())

    assert runtime.settings.enabled is False
    assert runtime.configured is True
    assert runtime.engine.provider is not None
    assert len(adapter_calls) == 1
    assert result.mode == "generated"


def test_legacy_enabled_default_does_not_invent_a_server_provider(tmp_path):
    adapter_calls = []
    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={"BHF_PRESENTATION_ENABLED": "true"},
        adapter_factory=lambda config: adapter_calls.append(config),
    )

    assert runtime.settings.enabled is True
    assert runtime.configured is False
    assert runtime.engine.provider is None
    assert adapter_calls == []


def test_enabled_generation_uses_bounded_shared_adapter_and_reuses_cache(tmp_path):
    adapter = _ValidAdapter()
    configured = []

    def adapter_factory(config):
        configured.append(config)
        return adapter

    cache_path = tmp_path / "presentation.sqlite"
    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={
            "BHF_PRESENTATION_ENABLED": "true",
            "BHF_PRESENTATION_TIMEOUT_SECONDS": "120",
            "BHF_PRESENTATION_CACHE_PATH": str(cache_path),
        },
        agent_config=_agent_config(timeout_seconds=600),
        adapter_factory=adapter_factory,
    )

    first = runtime.engine.present(_bundle())
    second = runtime.engine.present(_bundle())

    assert runtime.configured is True
    assert configured[0].timeout_seconds == MAXIMUM_PRESENTATION_TIMEOUT_SECONDS
    assert first.mode == "generated"
    assert second.mode == "cached"
    assert len(adapter.requests) == 1
    assert cache_path.exists()
    activity = runtime.diagnostics()["activity"]
    assert activity["requests_total"] == 2
    assert activity["outcomes"]["generated"] == 1
    assert activity["outcomes"]["cached"] == 1
    assert activity["provider"] == {
        "attempts": 1,
        "failures": 0,
        "rejections": 0,
        "saturated": 0,
    }
    assert activity["provider_gate"]["limit"] == (
        DEFAULT_MAXIMUM_CONCURRENT_PRESENTATION_REQUESTS
    )
    assert activity["latency_ms"]["average"] >= 0
    assert "Mark 5" not in json.dumps(activity)
    assert "Gerasa" not in json.dumps(activity)


def test_enabled_provider_failure_falls_back_without_breaking_reader(tmp_path):
    adapter = _FailingAdapter()
    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={"BHF_PRESENTATION_ENABLED": "yes"},
        agent_config=_agent_config(timeout_seconds=5),
        adapter_factory=lambda config: adapter,
    )

    result = runtime.engine.present(_bundle())

    assert runtime.configured is True
    assert result.mode == "deterministic_fallback"
    assert result.packet.cards
    assert any("provider failure: TimeoutError" in item for item in result.diagnostics)
    assert len(adapter.requests) == 1
    activity = runtime.diagnostics()["activity"]
    assert activity["requests_total"] == 1
    assert activity["outcomes"]["deterministic_fallback"] == 1
    assert activity["provider"]["attempts"] == 1
    assert activity["provider"]["failures"] == 1


def test_invalid_enable_value_fails_closed_and_invalid_timeout_uses_default(tmp_path):
    settings = load_presentation_runtime_settings(
        {
            "BHF_PRESENTATION_ENABLED": "sometimes",
            "BHF_PRESENTATION_TIMEOUT_SECONDS": "forever",
            "BHF_PRESENTATION_MAX_CONCURRENT_REQUESTS": "many",
        }
    )

    assert settings.enabled is False
    assert settings.timeout_seconds == DEFAULT_PRESENTATION_TIMEOUT_SECONDS
    assert (
        settings.maximum_concurrent_requests
        == DEFAULT_MAXIMUM_CONCURRENT_PRESENTATION_REQUESTS
    )
    assert "browser default remains off" in str(settings.warning)
    assert "20-second default" in str(settings.warning)
    assert "2-request default" in str(settings.warning)


def test_presentation_concurrency_setting_is_positive_and_capped():
    capped = load_presentation_runtime_settings(
        {"BHF_PRESENTATION_MAX_CONCURRENT_REQUESTS": "200"}
    )
    invalid = load_presentation_runtime_settings(
        {"BHF_PRESENTATION_MAX_CONCURRENT_REQUESTS": "0"}
    )

    assert capped.maximum_concurrent_requests == MAXIMUM_CONCURRENT_PRESENTATION_REQUESTS
    assert (
        invalid.maximum_concurrent_requests
        == DEFAULT_MAXIMUM_CONCURRENT_PRESENTATION_REQUESTS
    )
    assert "2-request default" in str(invalid.warning)


def test_enabled_configuration_error_fails_closed(tmp_path):
    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={"BHF_PRESENTATION_ENABLED": "on"},
        agent_config=AgentConfig(
            adapter="openai_compatible",
            base_url="https://provider.invalid/v1",
            model=None,
        ),
    )

    result = runtime.engine.present(_bundle())

    assert runtime.settings.enabled is True
    assert runtime.configured is False
    assert runtime.engine.provider is None
    assert runtime.error == "ValueError: the configured model is blank"
    assert result.mode == "deterministic_fallback"


def test_legacy_default_off_runtime_can_use_a_valid_local_presentation_bundle(tmp_path):
    bundle = _bundle()
    bundle_path = tmp_path / "presentation-bundle.json"
    _write_bundle(bundle_path, bundle)
    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={"BHF_PRESENTATION_BUNDLE_PATH": str(bundle_path)},
    )

    result = runtime.engine.present(bundle)
    diagnostics = runtime.diagnostics()["bundled_packets"]

    assert runtime.configured is False
    assert result.mode == "bundled"
    assert diagnostics["configured"] is True
    assert diagnostics["loaded"] == 1
    assert "error" not in diagnostics


def test_valid_bundle_avoids_provider_request(tmp_path):
    bundle = _bundle()
    bundle_path = tmp_path / "presentation-bundle.json"
    _write_bundle(bundle_path, bundle)
    adapter = _FailingAdapter()
    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={
            "BHF_PRESENTATION_ENABLED": "true",
            "BHF_PRESENTATION_BUNDLE_PATH": str(bundle_path),
        },
        agent_config=_agent_config(),
        adapter_factory=lambda config: adapter,
    )

    result = runtime.engine.present(bundle)

    assert result.mode == "bundled"
    assert len(adapter.requests) == 0
    assert result.diagnostics == ()
    assert runtime.diagnostics()["activity"]["outcomes"]["bundled"] == 1


def test_invalid_local_bundle_fails_closed_to_deterministic_rendering(tmp_path):
    bundle_path = tmp_path / "invalid-presentation-bundle.json"
    bundle_path.write_text("{", encoding="utf-8")
    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={"BHF_PRESENTATION_BUNDLE_PATH": str(bundle_path)},
    )

    result = runtime.engine.present(_bundle())
    diagnostics = runtime.diagnostics()["bundled_packets"]

    assert result.mode == "deterministic_fallback"
    assert diagnostics["loaded"] == 0
    assert str(diagnostics["error"]).startswith("PresentationBundleError:")


def test_transient_openrouter_key_builds_request_scoped_provider_without_leaking(
    tmp_path, caplog
):
    secret = "transient-openrouter-secret"
    adapter = _ValidAdapter()
    configured = []

    def adapter_factory(config):
        configured.append(config)
        return adapter

    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={"BHF_PRESENTATION_CACHE_PATH": str(tmp_path / "presentation.sqlite")},
        agent_config=_agent_config(),
        adapter_factory=adapter_factory,
    )

    provider, profile = runtime.provider_for_request(
        {"adapter": "openrouter", "model": "openrouter/free"},
        secret,
    )
    result = runtime.engine.present_with_provider(
        _bundle(), provider, generation_profile=profile
    )

    assert configured[-1].adapter == "openrouter"
    assert configured[-1].api_key == secret
    assert result.mode == "generated"
    public_values = {
        "response": result.to_dict(),
        "diagnostics": runtime.diagnostics(),
        "cache": runtime.engine.cache.entries_for_export(),
        "evidence_hash": _bundle().evidence_hash,
    }
    assert secret not in json.dumps(public_values)
    assert secret not in caplog.text
