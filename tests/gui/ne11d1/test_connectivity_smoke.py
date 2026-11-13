from __future__ import annotations

import json

import pytest


pytestmark = [pytest.mark.gui]


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
