from __future__ import annotations

import pytest
import requests
from selenium.webdriver.common.by import By

from .pages import HomePage, WorkspacePage


pytestmark = [pytest.mark.gui, pytest.mark.smoke]


def _assert_no_severe_browser_errors(driver):
    try:
        logs = driver.get_log("browser")
    except Exception:
        return
    severe = [entry for entry in logs if entry.get("level") == "SEVERE"]
    assert not severe, severe


def test_home_page_loads(driver, wait, base_url):
    page = HomePage(driver, wait, base_url)
    page.open().wait_loaded().assert_shell_visible()
    assert "BHF" in page.driver.title
    assert "ASV Reader" in page.find('[data-testid="app-title"]').text


def test_health_endpoint_available(base_url):
    response = requests.get(f"{base_url}/api/health", timeout=5)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_static_assets_load(driver, wait, base_url):
    page = HomePage(driver, wait, base_url)
    page.open().wait_loaded()
    _assert_no_severe_browser_errors(driver)
    assert page.find('[data-testid="book-select"]').is_displayed()
    assert page.find('[data-testid="chapter-input"]').is_displayed()
    assert not page.find('[data-testid="mobile-nav-bible"]').is_displayed()
    WorkspacePage(driver, wait, base_url).toggle_dark_mode()
    assert driver.execute_script("return document.documentElement.dataset.theme") == "dark"
    WorkspacePage(driver, wait, base_url).toggle_dark_mode()
    assert driver.execute_script("return document.documentElement.dataset.theme") == "light"
