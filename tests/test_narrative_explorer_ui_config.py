import asyncio

from bhf_web.app import create_app
from bhf_web.runtime import load_runtime_config
from httpx import ASGITransport, AsyncClient


def get_page(app):
    async def fetch():
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.get("/")

    return asyncio.run(fetch())


def test_narrative_explorer_ui_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("BHF_NARRATIVE_EXPLORER_ENABLED", raising=False)

    config = load_runtime_config()
    assert config.get("narrativeExplorerEnabled") is False
    assert "commentaryRelease" not in config


def test_narrative_explorer_ui_flag_can_be_enabled_for_preview(monkeypatch):
    monkeypatch.setenv("BHF_NARRATIVE_EXPLORER_ENABLED", "true")

    assert load_runtime_config().get("narrativeExplorerEnabled") is True


def test_disabled_flag_keeps_the_ordinary_reader_without_retired_commentary(monkeypatch):
    monkeypatch.delenv("BHF_NARRATIVE_EXPLORER_ENABLED", raising=False)
    app = create_app()

    response = get_page(app)

    assert response.status_code == 200
    assert 'data-companion-resource="narrative_explorer"' not in response.text
    assert "/narrative-explorer.js" not in response.text
    assert 'data-workspace-tab="commentary"' in response.text
    assert 'data-workspace-tab="context"' in response.text
    assert 'aria-label="Tyndale Study Notes"' in response.text
    assert 'data-companion-resource="translation_comparison"' in response.text
    assert "BHF Context" not in response.text
    assert "data-bhf-commentary-card" not in response.text
    assert "bhf-commentary-card.js" not in response.text
    assert "Tyndale Companion" in response.text
    assert 'data-workspace-tab="notes"' in response.text
    assert 'data-workspace-tab="highlights"' in response.text
    assert any(route.path == "/api/narrative-explorer/v1/passages/{book}/{chapter}" for route in app.routes)


def test_enabled_flag_exposes_only_the_passage_companion_entry(monkeypatch):
    monkeypatch.setenv("BHF_NARRATIVE_EXPLORER_ENABLED", "1")
    app = create_app()

    response = get_page(app)

    assert response.status_code == 200
    assert 'data-companion-resource="narrative_explorer"' in response.text
    assert 'data-companion-resource-label="Explore the Narrative"' in response.text
    assert "/narrative-explorer.js?v=20261015b" in response.text
    assert "BHF Context" not in response.text
    assert 'aria-label="Tyndale Study Notes"' in response.text
    assert '"narrativeExplorerEnabled": true' in response.text
