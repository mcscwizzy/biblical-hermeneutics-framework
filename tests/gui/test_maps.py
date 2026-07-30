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


def test_maps_tab_omits_unused_navigator_controls(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    MapsPage(driver, wait, base_url).open_maps()
    assert not driver.find_elements(By.CSS_SELECTOR, '[data-testid="journey-selector"]')
    assert not driver.find_elements(By.CSS_SELECTOR, "[data-map-journey-toggle]")
    assert not driver.find_elements(By.CSS_SELECTOR, "[data-map-study-mode]")
    assert driver.find_element(By.CSS_SELECTOR, "[data-map-navigator-close]").get_attribute("aria-label") == "Close navigator"
    assert not driver.find_elements(By.CSS_SELECTOR, "[data-map-journeys]")
    _assert_no_severe_browser_errors(driver)


def test_mobile_map_navigator_can_be_closed(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    MapsPage(driver, wait, base_url).open_maps()

    navigator = driver.find_element(By.CSS_SELECTOR, "#map-study-navigator")
    open_button = driver.find_element(By.CSS_SELECTOR, "[data-map-navigator-open]")
    close_button = driver.find_element(By.CSS_SELECTOR, "[data-map-navigator-close]")

    open_button.click()
    wait.until(lambda _driver: "is-mobile-open" in navigator.get_attribute("class"))
    assert close_button.is_displayed()

    close_button.click()
    wait.until(lambda _driver: "is-mobile-open" not in navigator.get_attribute("class"))
    assert open_button.get_attribute("aria-expanded") == "false"
    _assert_no_severe_browser_errors(driver)


def test_mobile_map_details_can_be_closed(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    MapsPage(driver, wait, base_url).open_maps()

    details = driver.find_element(By.CSS_SELECTOR, "#map-details-column")
    open_button = driver.find_element(By.CSS_SELECTOR, "[data-map-details-open]")
    close_button = driver.find_element(By.CSS_SELECTOR, "[data-map-details-close]")

    open_button.click()
    wait.until(lambda _driver: "is-mobile-open" in details.get_attribute("class"))
    assert close_button.is_displayed()

    close_button.click()
    wait.until(lambda _driver: "is-mobile-open" not in details.get_attribute("class"))
    assert open_button.get_attribute("aria-expanded") == "false"
    _assert_no_severe_browser_errors(driver)
