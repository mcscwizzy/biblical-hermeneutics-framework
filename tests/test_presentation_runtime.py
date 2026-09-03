from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from bhf_agent.config import AgentConfig
from bhf_agent.models import ChatResponse
from bhf_agent.providers.openrouter_config import OPENROUTER_BASE_URL
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


def _bundle(reference="Mark 5:1"):
    return build_evidence_bundle(
        reference,
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
        evidence = supplied["evidence"][0]
        constraints = evidence["output_constraints"]
        return ChatResponse(
            text=json.dumps(
                {
                    "passage_ref": supplied["passage_ref"],
                    "cards": [{
                        "id": "fixture-card",
                        "type": "did_you_know",
                        "headline": "A supplied detail",
                        "body": evidence["claim"],
                        "dig_in_summary": None,
                        "evidence_ids": [evidence["id"]],
                        "confidence": constraints["maximum_card_confidence"],
                        "interpretation_level": constraints["allowed_interpretation_levels"][0],
                        "related_entity_ids": [],
                        "map_focus": None,
                        "dig_deeper_actions": [],
                    }],
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


def test_runtime_construction_does_not_create_presentation_cache(tmp_path):
    cache_path = tmp_path / "missing" / "presentation.sqlite"

    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={"BHF_PRESENTATION_CACHE_PATH": str(cache_path)},
    )

    assert runtime.engine.cache.path == cache_path
    assert not cache_path.parent.exists()
    assert not cache_path.exists()


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
        "parse_failures": 0,
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
        {
            "adapter": "openrouter",
            "model": "openrouter/free",
            "base_url": "http://127.0.0.1:1234",
            "api_key": "request-body-secret",
            "headers": {"Authorization": "also-untrusted"},
        },
        secret,
    )
    result = runtime.engine.present_with_provider(
        _bundle(), provider, generation_profile=profile
    )

    assert configured[-1].adapter == "openrouter"
    assert configured[-1].base_url == OPENROUTER_BASE_URL
    assert configured[-1].api_key == secret
    assert profile == "openrouter:openrouter/free"
    assert result.mode == "generated"
    public_values = {
        "response": result.to_dict(),
        "diagnostics": runtime.diagnostics(),
        "cache": runtime.engine.cache.entries_for_export(),
        "evidence_hash": _bundle().evidence_hash,
    }
    assert secret not in json.dumps(public_values)
    assert secret not in caplog.text


@pytest.mark.parametrize(
    ("adapter_name", "base_url"),
    [
        ("openai_compatible", "http://127.0.0.1:1234"),
        ("openai_compatible", "http://169.254.169.254/"),
        ("ollama", "http://internal-service/"),
    ],
)
def test_request_scoped_provider_rejects_client_controlled_connection_targets(
    tmp_path, adapter_name, base_url
):
    configured = []
    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={},
        adapter_factory=lambda config: configured.append(config),
    )

    with pytest.raises(
        ValueError,
        match="supports OpenRouter browser credentials only",
    ):
        runtime.provider_for_request(
            {"adapter": adapter_name, "model": "test-model", "base_url": base_url},
            "transient-key",
        )

    assert configured == []


def test_request_profiles_without_browser_credentials_cannot_override_server_provider(
    tmp_path,
):
    adapter = _ValidAdapter()
    configured = []
    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={},
        agent_config=_agent_config(),
        adapter_factory=lambda config: configured.append(config) or adapter,
    )

    provider, profile = runtime.provider_for_request(
        {
            "adapter": "ollama",
            "model": "attacker-model",
            "base_url": "http://internal-service/",
        },
        None,
    )

    assert provider is runtime.engine.provider
    assert profile == "openai_compatible:fixture-model"
    assert len(configured) == 1
    assert configured[0].base_url == "https://provider.invalid/v1"


def test_openrouter_cache_profile_uses_adapter_and_model_but_not_browser_key(tmp_path):
    configured = []
    adapter = _ValidAdapter()
    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={},
        adapter_factory=lambda config: configured.append(config) or adapter,
    )

    first_provider, first_profile = runtime.provider_for_request(
        {"adapter": "openrouter", "model": "test-model"},
        "first-secret",
    )
    second_provider, second_profile = runtime.provider_for_request(
        {"adapter": "openrouter", "model": "test-model"},
        "second-secret",
    )
    _, other_model_profile = runtime.provider_for_request(
        {"adapter": "openrouter", "model": "other-model"},
        "first-secret",
    )

    assert first_profile == second_profile == "openrouter:test-model"
    assert other_model_profile == "openrouter:other-model"
    assert first_profile != other_model_profile
    first = runtime.engine.present_with_provider(
        _bundle(), first_provider, generation_profile=first_profile
    )
    second = runtime.engine.present_with_provider(
        _bundle(), second_provider, generation_profile=second_profile
    )
    assert first.mode == "generated"
    assert second.mode == "cached"
    assert len(adapter.requests) == 1
    assert [config.api_key for config in configured] == [
        "first-secret",
        "second-secret",
        "first-secret",
    ]
    assert all(config.base_url == OPENROUTER_BASE_URL for config in configured)


def test_request_scoped_openrouter_uses_shared_provider_gate_without_server_provider(
    tmp_path,
):
    two_active = threading.Event()
    release = threading.Event()
    lock = threading.Lock()

    class BlockingAdapter(_ValidAdapter):
        def __init__(self):
            super().__init__()
            self.active = 0
            self.peak_active = 0

        def chat(self, request):
            with lock:
                self.active += 1
                self.peak_active = max(self.peak_active, self.active)
                if self.active == 2:
                    two_active.set()
            try:
                if not release.wait(timeout=3):
                    raise TimeoutError("test did not release provider")
                return super().chat(request)
            finally:
                with lock:
                    self.active -= 1

    adapter = BlockingAdapter()
    runtime = configure_presentation_runtime(
        study_db_path=tmp_path / "study.sqlite",
        environ={"BHF_PRESENTATION_MAX_CONCURRENT_REQUESTS": "2"},
        adapter_factory=lambda config: adapter,
    )
    providers = [
        runtime.provider_for_request(
            {"adapter": "openrouter", "model": "test-model"},
            f"transient-key-{index}",
        )
        for index in range(5)
    ]
    bundles = [_bundle(f"Mark 5:{index + 1}") for index in range(5)]

    with ThreadPoolExecutor(max_workers=5) as executor:
        first_futures = [
            executor.submit(
                runtime.engine.present_with_provider,
                bundles[index],
                providers[index][0],
                generation_profile=providers[index][1],
            )
            for index in range(2)
        ]
        assert two_active.wait(timeout=3)
        saturated_futures = [
            executor.submit(
                runtime.engine.present_with_provider,
                bundles[index],
                providers[index][0],
                generation_profile=providers[index][1],
            )
            for index in range(2, 5)
        ]
        saturated = [future.result(timeout=3) for future in saturated_futures]
        release.set()
        generated = [future.result(timeout=3) for future in first_futures]

    assert runtime.configured is False
    assert runtime.engine.provider is None
    assert adapter.peak_active == 2
    assert all(result.mode == "generated" for result in generated)
    assert all(result.mode == "deterministic_fallback" for result in saturated)
    assert all(
        any("provider capacity unavailable" in item for item in result.diagnostics)
        for result in saturated
    )
    activity = runtime.diagnostics()["activity"]
    assert activity["provider"] == {
        "attempts": 2,
        "failures": 0,
        "parse_failures": 0,
        "rejections": 0,
        "saturated": 3,
    }
    assert activity["provider_gate"] == {
        "enabled": True,
        "limit": 2,
        "active": 0,
        "peak_active": 2,
    }
