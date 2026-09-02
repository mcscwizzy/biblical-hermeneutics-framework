import asyncio
import json
import sqlite3
import threading
import time
from types import SimpleNamespace

import pytest
import httpx
from fastapi import FastAPI

from bhf_web.jobs import AskJobStore
from bhf_web.routes.study import register_study_routes
from bhf_web.services.companion_context import StalePresentationEvidenceError


EVIDENCE_HASH = "a" * 64


def _presentation_payload(mode="generated", evidence_hash=EVIDENCE_HASH):
    return {
        "reference": "John 4:23",
        "evidence_bundle": {"evidence_hash": evidence_hash},
        "presentation_packet": {
            "cards": [{"id": "ai-card"}],
            "presentation_mode": mode,
            "generated_from": {
                "evidence_hash": evidence_hash,
                "prompt_version": "presentation-v4",
                "model": "test:model",
            },
        },
        "presentation_evidence": [],
    }


class _Runtime:
    def __init__(self, provider=object()):
        self.provider = provider
        self.settings = SimpleNamespace(timeout_seconds=20)
        self.calls = []

    def provider_for_request(self, profile, transient_api_key):
        self.calls.append((profile, transient_api_key))
        return self.provider, "test:model"


class _Service:
    def __init__(self, operation=None):
        self.operation = operation or (lambda values: _presentation_payload())
        self.calls = []

    def build(self, **_values):
        return {
            "reference": "John 4:23",
            "presentation_packet": {
                "cards": [{"id": "local-card"}],
                "presentation_mode": "deterministic_fallback",
            },
        }

    def enhance_presentation(self, **values):
        self.calls.append(values)
        return self.operation(values)


def _app(tmp_path, service, runtime=None, *, transport="job"):
    store = AskJobStore(tmp_path / "jobs.sqlite")
    app = FastAPI()
    app.state.presentation_runtime = runtime or _Runtime()
    register_study_routes(
        app,
        study_db_path="unused.sqlite",
        templates=None,
        job_store=store,
        companion_context_service=service,
        presentation_transport=transport,
    )
    return app, store


def _request(app, method, url, **kwargs):
    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(send())


def _submit(app, **overrides):
    payload = {
        "book": "John",
        "chapter": 4,
        "verse_start": 23,
        "verse_end": 23,
        "evidence_hash": EVIDENCE_HASH,
    }
    payload.update(overrides)
    return _request(app, "POST", "/api/study/presentation", json=payload)


def _wait_for_done(store, job_id, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = store.get_presentation(job_id)
        if job is not None and job.done:
            return job
        time.sleep(0.01)
    raise AssertionError("presentation job did not finish")


@pytest.fixture
def synchronous_threadpool(monkeypatch):
    """Exercise attached thread execution without AnyIO's test-process worker."""

    async def run(callable_, *args, **kwargs):
        outcome = []
        errors = []

        def invoke():
            try:
                outcome.append(callable_(*args, **kwargs))
            except BaseException as exc:  # noqa: BLE001 - re-raise on request task
                errors.append(exc)

        worker = threading.Thread(target=invoke)
        worker.start()
        worker.join()
        if errors:
            raise errors[0]
        return outcome[0]

    monkeypatch.setattr("bhf_web.routes.study.run_in_threadpool", run)


def test_submission_returns_before_blocking_provider_and_context_stays_immediate(tmp_path):
    started = threading.Event()
    release = threading.Event()

    def block(_values):
        started.set()
        release.wait(2)
        return _presentation_payload()

    service = _Service(block)
    app, store = _app(tmp_path, service)
    before = time.monotonic()
    response = _submit(app)
    elapsed = time.monotonic() - before

    assert response.status_code == 202
    assert elapsed < 0.5
    assert started.wait(0.5)
    assert store.get_presentation(response.json()["job_id"]).done is False
    context = service.build(book="John", chapter=4, verse_start=23)
    assert context["presentation_packet"]["cards"][0]["id"] == "local-card"
    release.set()
    assert _wait_for_done(store, response.json()["job_id"]).status == "succeeded"


def test_successful_job_polls_to_sanitized_generated_presentation(tmp_path):
    app, store = _app(tmp_path, _Service())
    submission = _submit(app)
    job = _wait_for_done(store, submission.json()["job_id"])

    response = _request(app, "GET", f"/api/study/presentation/jobs/{job.job_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert response.json()["result"]["presentation_packet"]["presentation_mode"] == "generated"


def test_provider_failure_is_publicly_classified_without_exception_details(tmp_path):
    def fail(_values):
        raise RuntimeError("transient-secret https://internal.example/provider")

    app, store = _app(tmp_path, _Service(fail))
    submission = _submit(app)
    job = _wait_for_done(store, submission.json()["job_id"])
    payload = _request(
        app, "GET", f"/api/study/presentation/jobs/{job.job_id}"
    ).json()

    assert payload["status"] == "failed"
    assert payload["error_category"] == "provider_failure"
    assert "transient-secret" not in json.dumps(payload)
    assert "internal.example" not in json.dumps(payload)


def test_provider_timeout_terminates_job(tmp_path):
    def timeout(_values):
        raise TimeoutError("raw provider timeout")

    app, store = _app(tmp_path, _Service(timeout))
    submission = _submit(app)
    job = _wait_for_done(store, submission.json()["job_id"])

    assert job.status == "failed"
    assert job.error_category == "provider_timeout"


def test_stale_evidence_fails_without_returning_a_mismatched_packet(tmp_path):
    def stale(_values):
        raise StalePresentationEvidenceError("new evidence hash is secret")

    app, store = _app(tmp_path, _Service(stale))
    submission = _submit(app)
    job = _wait_for_done(store, submission.json()["job_id"])
    payload = _request(
        app, "GET", f"/api/study/presentation/jobs/{job.job_id}"
    ).json()

    assert payload["status"] == "failed"
    assert payload["error_category"] == "stale_evidence"
    assert "result" not in payload


def test_deterministic_fallback_is_a_failed_enhancement_not_a_success(tmp_path):
    service = _Service(lambda _values: _presentation_payload("deterministic_fallback"))
    app, store = _app(tmp_path, service)
    submission = _submit(app)
    job = _wait_for_done(store, submission.json()["job_id"])

    assert job.status == "failed"
    assert job.error_category == "presentation_unavailable"
    assert job.result["presentation_packet"]["presentation_mode"] == "deterministic_fallback"


def test_cached_success_completes_without_invoking_provider_from_the_job_layer(tmp_path):
    class ProviderThatMustNotRun:
        def generate(self, *_args, **_kwargs):
            raise AssertionError("cached presentation should not call provider")

    service = _Service(lambda _values: _presentation_payload("cached"))
    app, store = _app(tmp_path, service, _Runtime(ProviderThatMustNotRun()))
    submission = _submit(app)
    job = _wait_for_done(store, submission.json()["job_id"])

    assert job.status == "succeeded"
    assert job.result["presentation_packet"]["presentation_mode"] == "cached"


def test_expired_and_missing_jobs_stop_polling_with_compact_public_state(tmp_path):
    service = _Service()
    app, store = _app(tmp_path, service)
    job = store.create_presentation(
        reference="John 4:23",
        evidence_hash=EVIDENCE_HASH,
        deadline_seconds=30,
    )
    job.deadline_at = "2000-01-01T00:00:00Z"
    job._save()

    expired = _request(
        app, "GET", f"/api/study/presentation/jobs/{job.job_id}"
    )
    missing = _request(app, "GET", "/api/study/presentation/jobs/missing")

    assert expired.status_code == 200
    assert expired.json()["status"] == "expired"
    assert expired.json()["error_category"] == "provider_timeout"
    assert missing.status_code == 404
    assert missing.json()["error_category"] == "presentation_unavailable"


def test_browser_openrouter_key_never_enters_job_serialization_or_status(tmp_path):
    secret = "sk-or-transient-test-secret"
    runtime = _Runtime(provider=SimpleNamespace(memory_only_secret=secret))
    app, store = _app(tmp_path, _Service(), runtime)
    response = _request(
        app,
        "POST",
        "/api/study/presentation",
        headers={"X-BHF-OpenRouter-Key": secret},
        json={
            "book": "John",
            "chapter": 4,
            "verse_start": 23,
            "verse_end": 23,
            "evidence_hash": EVIDENCE_HASH,
            "ai_profile": {"adapter": "openrouter", "model": "test:model"},
        },
    )
    job = _wait_for_done(store, response.json()["job_id"])
    public_payload = _request(
        app, "GET", f"/api/study/presentation/jobs/{job.job_id}"
    ).json()
    with sqlite3.connect(store.path) as connection:
        stored_payload = connection.execute(
            "SELECT payload FROM presentation_jobs WHERE job_id = ?",
            (job.job_id,),
        ).fetchone()[0]

    assert response.status_code == 202
    assert runtime.calls[0][1] == secret
    assert secret not in json.dumps(response.json())
    assert secret not in json.dumps(public_payload)
    assert secret not in stored_payload


@pytest.mark.parametrize(
    ("adapter", "base_url"),
    [
        ("openai_compatible", "http://127.0.0.1:8000/v1"),
        ("openai_compatible", "http://169.254.169.254/latest/meta-data"),
        ("ollama", "http://nas.internal:11434"),
    ],
)
def test_browser_provider_ssrf_profiles_are_rejected_before_job_creation(
    tmp_path, adapter, base_url
):
    runtime = _Runtime()
    service = _Service()
    app, store = _app(tmp_path, service, runtime)
    response = _submit(
        app,
        ai_profile={"adapter": adapter, "model": "bad", "base_url": base_url},
    )

    assert response.status_code == 400
    assert runtime.calls == []
    assert service.calls == []
    with sqlite3.connect(store.path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM presentation_jobs").fetchone()[0]
    assert count == 0


def test_unavailable_transport_refuses_presentation_work(tmp_path):
    runtime = _Runtime()
    service = _Service()
    app, store = _app(tmp_path, service, runtime, transport="unavailable")
    response = _submit(app)

    assert response.status_code == 503
    assert response.json()["error_category"] == "presentation_unavailable"
    assert runtime.calls == []
    assert service.calls == []
    with sqlite3.connect(store.path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM presentation_jobs").fetchone()[0]
    assert count == 0


def test_synchronous_success_returns_final_presentation_without_creating_a_job(
    tmp_path, synchronous_threadpool,
):
    runtime = _Runtime()
    service = _Service()
    app, store = _app(tmp_path, service, runtime, transport="synchronous")

    response = _submit(app)

    assert response.status_code == 200
    assert response.json()["presentation_packet"]["presentation_mode"] == "generated"
    assert len(service.calls) == 1
    with sqlite3.connect(store.path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM presentation_jobs").fetchone()[0]
    assert count == 0


def test_synchronous_cache_hit_returns_cached_packet_without_job_or_provider_call(
    tmp_path, synchronous_threadpool,
):
    class ProviderThatMustNotRun:
        def generate(self, *_args, **_kwargs):
            raise AssertionError("cached presentation should not call provider")

    service = _Service(lambda _values: _presentation_payload("cached"))
    app, store = _app(
        tmp_path,
        service,
        _Runtime(ProviderThatMustNotRun()),
        transport="synchronous",
    )

    response = _submit(app)

    assert response.status_code == 200
    assert response.json()["presentation_packet"]["presentation_mode"] == "cached"
    with sqlite3.connect(store.path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM presentation_jobs").fetchone()[0]
    assert count == 0


def test_synchronous_provider_timeout_returns_controlled_failure_without_job(
    tmp_path, synchronous_threadpool
):
    def timeout(_values):
        raise TimeoutError("secret provider detail")

    app, store = _app(
        tmp_path,
        _Service(timeout),
        transport="synchronous",
    )

    response = _submit(app)

    assert response.status_code == 503
    assert response.status_code != 504
    assert response.json()["error_category"] == "provider_timeout"
    assert "secret provider detail" not in response.text
    with sqlite3.connect(store.path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM presentation_jobs").fetchone()[0]
    assert count == 0


def test_synchronous_validation_fallback_is_returned_for_deterministic_ui(
    tmp_path, synchronous_threadpool
):
    service = _Service(lambda _values: _presentation_payload("deterministic_fallback"))
    app, store = _app(tmp_path, service, transport="synchronous")

    response = _submit(app)

    assert response.status_code == 200
    assert (
        response.json()["presentation_packet"]["presentation_mode"]
        == "deterministic_fallback"
    )
    with sqlite3.connect(store.path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM presentation_jobs").fetchone()[0]
    assert count == 0


def test_synchronous_browser_key_stays_request_scoped_and_out_of_public_state(
    tmp_path, caplog, synchronous_threadpool
):
    secret = "sk-or-synchronous-transient-secret"

    def fail_with_secret(_values):
        raise RuntimeError(f"provider rejected {secret}")

    runtime = _Runtime(provider=SimpleNamespace(memory_only_secret=secret))
    app, store = _app(
        tmp_path,
        _Service(fail_with_secret),
        runtime,
        transport="synchronous",
    )
    response = _request(
        app,
        "POST",
        "/api/study/presentation",
        headers={"X-BHF-OpenRouter-Key": secret},
        json={
            "book": "John",
            "chapter": 4,
            "verse_start": 23,
            "verse_end": 23,
            "evidence_hash": EVIDENCE_HASH,
            "ai_profile": {"adapter": "openrouter", "model": "test:model"},
        },
    )

    assert response.status_code == 503
    assert response.json()["error_category"] == "provider_failure"
    assert runtime.calls[0][1] == secret
    assert secret not in response.text
    assert secret not in caplog.text
    with sqlite3.connect(store.path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM presentation_jobs").fetchone()[0]
    assert count == 0


@pytest.mark.parametrize(
    ("adapter", "base_url"),
    [
        ("openai_compatible", "http://127.0.0.1:8000/v1"),
        ("openai_compatible", "http://169.254.169.254/latest/meta-data"),
        ("ollama", "http://nas.internal:11434"),
    ],
)
def test_synchronous_ssrf_profiles_are_rejected_before_provider_creation(
    tmp_path, adapter, base_url, synchronous_threadpool
):
    runtime = _Runtime()
    service = _Service()
    app, store = _app(tmp_path, service, runtime, transport="synchronous")

    response = _submit(
        app,
        ai_profile={"adapter": adapter, "model": "bad", "base_url": base_url},
    )

    assert response.status_code == 400
    assert runtime.calls == []
    assert service.calls == []
    with sqlite3.connect(store.path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM presentation_jobs").fetchone()[0]
    assert count == 0
