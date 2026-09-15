from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from framework.commentary.production.manifests import build_manifest, save_manifest
from framework.commentary.production.models import InputIdentity, ProductionError, PreparedChapter
from framework.commentary.production.runner import ProductionRunner
from framework.commentary.production.runtime import (
    build_runtime_adapter,
    redacted_preflight_report,
    resolve_runtime_config,
    runtime_config_identity,
)
from bhf_agent.config import AgentConfig, ConfigError


def _config(**overrides) -> AgentConfig:
    values = {
        "adapter": "openai_compatible",
        "base_url": "http://127.0.0.1:1234/v1",
        "model": "fixture-model",
        "api_key": "fixture-secret",
        "commentary_max_tokens": 4500,
    }
    values.update(overrides)
    return AgentConfig(**values)


def _prepared() -> PreparedChapter:
    identity = InputIdentity(
        "evidence", "synthesis", "1.5", "1.2", "1.1", "1.1",
        "commentary-richness-gate-v2.1", "validator", "packet-hash", "packet-id",
    )
    return PreparedChapter(
        row={
            "reference": "Genesis 1",
            "book": "Genesis",
            "chapter": 1,
            "canonical_ordinal": 1,
            "literary_category": "Pentateuch",
            "evidence_availability": "AVAILABLE",
            "evidence_count": 1,
            "synthesis_unit_count": 1,
            "density_bucket": "1-5",
            "input_identity": identity.to_dict(),
        },
        packet={"packet_id": "packet-id", "packet_hash": "packet-hash", "user_prompt": "fixture"},
    )


def _manifest(tmp_path: Path) -> Path:
    path = tmp_path / "planned.json"
    save_manifest(
        build_manifest(
            [_prepared()],
            batch_size=1,
            run_id="run-runtime",
            generation_config={
                "provider_adapter": "configured-at-run",
                "model": "configured-at-run",
            },
        ),
        path,
    )
    return path


def _config_file(tmp_path: Path, config: AgentConfig | None = None, **overrides) -> Path:
    config = config or _config(**overrides)
    path = tmp_path / "runtime-config.json"
    path.write_text(json.dumps(config.to_dict(redact_secrets=False)), encoding="utf-8")
    return path


def test_runner_without_config_fails_before_authorization(tmp_path):
    manifest_path = _manifest(tmp_path)
    with pytest.raises(ProductionError, match="PRODUCTION_RUNTIME_CONFIG_REQUIRED"):
        ProductionRunner(tmp_path).run_manifest(manifest_path, authorized_run=True)
    assert not (tmp_path / ".bhf-data/bhf-commentary-production/v1/runs/run-runtime/authorization.json").exists()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"model": None}, "model is required"),
        ({"model": "unknown"}, "intentional non-placeholder"),
        ({"base_url": None}, "base_url is required"),
        ({"adapter": "openrouter", "base_url": "https://openrouter.ai/api/v1", "api_key": None}, "api_key is required"),
    ],
)
def test_invalid_production_config_fails_closed(tmp_path, overrides, message):
    path = _config_file(tmp_path, **overrides)
    with pytest.raises(ProductionError, match="PRODUCTION_RUNTIME_CONFIG_INVALID") as exc_info:
        resolve_runtime_config(path)
    assert message in str(exc_info.value)


def test_runtime_identity_is_deterministic_and_excludes_api_key():
    first = runtime_config_identity(_config(api_key="secret-one"), reader_enabled=True)
    second = runtime_config_identity(_config(api_key="secret-two"), reader_enabled=True)
    changed = runtime_config_identity(_config(model="other-model"), reader_enabled=True)
    assert first == second
    assert first != changed


def test_adapter_construction_never_calls_chat(monkeypatch):
    calls = {"constructed": 0, "chat": 0}

    class Adapter:
        def chat(self, *args, **kwargs):
            calls["chat"] += 1
            raise AssertionError("preflight must not call chat")

    def fake_factory(config):
        calls["constructed"] += 1
        return Adapter()

    monkeypatch.setattr(
        "framework.commentary.production.runtime.build_chat_adapter", fake_factory
    )
    adapter = build_runtime_adapter(_config())
    assert adapter.__class__.__name__ == "Adapter"
    assert calls == {"constructed": 1, "chat": 0}


def test_preflight_constructs_adapter_without_chat(monkeypatch, tmp_path):
    import tools.commentary_production as production_cli

    calls = {"constructed": 0, "chat": 0}

    class Adapter:
        def chat(self, *args, **kwargs):
            calls["chat"] += 1
            raise AssertionError("preflight must not call chat")

    def fake_factory(config):
        calls["constructed"] += 1
        return Adapter()

    monkeypatch.setattr(
        "framework.commentary.production.runtime.build_chat_adapter", fake_factory
    )
    prepared = _prepared()
    monkeypatch.setattr(
        production_cli,
        "prepare_chapter",
        lambda book, chapter: prepared,
    )
    report = production_cli.preflight(
        Namespace(
            manifest=_manifest(tmp_path),
            config=_config_file(tmp_path),
            enable_reader=False,
        )
    )
    assert report["status"] == "READY"
    assert report["provider_called"] is False
    assert calls == {"constructed": 1, "chat": 0}


def test_preflight_report_is_redacted():
    report = redacted_preflight_report(
        {
            "manifest_identity": "manifest-id",
            "run_id": "run-id",
            "chapters": [{}],
            "status": "PLANNED_NOT_AUTHORIZED",
        },
        _config(api_key="super-secret"),
        reader_enabled=False,
        input_identities_match=True,
        adapter_constructed=True,
    )
    serialized = json.dumps(report)
    assert "super-secret" not in serialized
    assert report["runtime"]["credential_present"] is True
    assert report["provider_called"] is False


def test_same_runtime_resumes_and_changed_model_is_rejected(tmp_path, monkeypatch):
    manifest_path = _manifest(tmp_path)
    monkeypatch.setattr(
        ProductionRunner,
        "_run_batch",
        lambda self, manifest, batch_id, enable_reader: {"batch_id": batch_id, "status": "COMPLETE"},
    )
    first = ProductionRunner(tmp_path, config=_config()).run_manifest(
        manifest_path, authorized_run=True
    )
    second = ProductionRunner(tmp_path, config=_config()).run_manifest(
        manifest_path, authorized_run=True
    )
    assert first["run_id"] == second["run_id"] == "run-runtime"
    with pytest.raises(ProductionError, match="RUNTIME_CONFIG_MISMATCH"):
        ProductionRunner(tmp_path, config=_config(model="different-model")).run_manifest(
            manifest_path, authorized_run=True
        )
    with pytest.raises(ProductionError, match="RUNTIME_CONFIG_MISMATCH"):
        ProductionRunner(
            tmp_path,
            config=_config(adapter="ollama", base_url="http://127.0.0.1:11434"),
        ).run_manifest(manifest_path, authorized_run=True)
    with pytest.raises(ProductionError, match="RUNTIME_CONFIG_MISMATCH"):
        ProductionRunner(tmp_path, config=_config(temperature=0.7)).run_manifest(
            manifest_path, authorized_run=True
        )

    receipt = json.loads(
        (tmp_path / ".bhf-data/bhf-commentary-production/v1/runs/run-runtime/authorization.json").read_text()
    )
    serialized = json.dumps(receipt)
    assert "fixture-secret" not in serialized
    assert "api_key" not in receipt
    assert receipt["runtime_config_identity"]
    assert receipt["runtime"]["model"] == "fixture-model"
