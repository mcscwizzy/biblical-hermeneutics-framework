from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from .pages import HomePage, MapsPage


pytestmark = [pytest.mark.gui]


def _assert_no_severe_browser_errors(driver):
    try:
        logs = driver.get_log("browser")
    except Exception:
        return
    severe = [entry for entry in logs if entry.get("level") == "SEVERE"]
    assert not severe, severe


def test_maps_tab_loads(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = MapsPage(driver, wait, base_url)
    page.open_maps()
    assert page.find('[data-testid="map-search-input"]').is_displayed()
    assert page.find('[data-testid="map-search-button"]').is_displayed()
    assert page.find("#map-panel").is_displayed()


def test_map_catalog_search(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = MapsPage(driver, wait, base_url)
    page.open_maps()
    page.search_map_catalog("Jerusalem")
    page.assert_results_or_empty_state()
    assert page.find("#map-search-results").is_displayed()


def test_maps_tab_includes_journeys(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    MapsPage(driver, wait, base_url).open_maps()
    assert driver.find_element(By.CSS_SELECTOR, '[data-testid="journey-search-input"]').is_displayed()
    _assert_no_severe_browser_errors(driver)
