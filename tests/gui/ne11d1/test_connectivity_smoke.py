from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from scripts import gui_connectivity_smoke


pytestmark = [pytest.mark.gui]


def test_grid_status_extracts_only_active_sessions():
    payload = {
        "value": {
            "nodes": [
                {
                    "slots": [
                        {"session": {"sessionId": "active-session"}},
                        {"session": None},
                    ]
                }
            ]
        }
    }

    assert gui_connectivity_smoke._active_session_ids(payload) == {"active-session"}


def test_smoke_cleanup_releases_only_sessions_created_by_the_failed_probe(monkeypatch):
    monkeypatch.setattr(
        gui_connectivity_smoke,
        "_grid_status",
        lambda _remote_url: (False, {"preexisting-session", "orphaned-session"}),
    )
    released = []
    monkeypatch.setattr(
        gui_connectivity_smoke,
        "_delete_grid_session",
        lambda remote_url, session_id: released.append((remote_url, session_id)),
    )

    cleaned = gui_connectivity_smoke._release_new_sessions(
        "http://selenium-chrome:4444/wd/hub",
        {"preexisting-session"},
    )

    assert cleaned == {"orphaned-session"}
    assert released == [
        ("http://selenium-chrome:4444/wd/hub", "orphaned-session")
    ]


def test_remote_chrome_reaches_ne11d1_test_server(driver, base_url):
    driver.get(f"{base_url}/api/health")
    health = json.loads(driver.find_element("tag name", "body").text)
    assert health.get("status") == "ok", health

    driver.get(f"{base_url}/offline")
    offline = driver.execute_script(
        "return {path:location.pathname, ready:document.readyState, "
        "responseStatus:performance.getEntriesByType('navigation')[0]?.responseStatus};"
    )
    assert offline["path"] == "/offline", offline
    assert offline["ready"] == "complete", offline
    assert offline.get("responseStatus") in (None, 200), offline
    print(
        "GUI_TEST_SERVER_CHROME="
        + json.dumps({"base_url": base_url, "health": health["status"], "offline": offline}, sort_keys=True),
        flush=True,
    )
