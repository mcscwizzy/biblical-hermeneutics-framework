from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from .pages import HomePage, WorkspacePage


pytestmark = [pytest.mark.gui]


def _set_mobile_viewport(driver):
    driver.set_window_size(390, 844)


def _hidden_or_absent(driver, selector: str) -> bool:
    elements = driver.find_elements(By.CSS_SELECTOR, selector)
    return not elements or not elements[0].is_displayed()


def _enter_reader_mode(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#chapter-reader .chapter-text")))
    WorkspacePage(driver, wait, base_url).toggle_reader_mode()
    wait.until(lambda _driver: "reader-mode" in _driver.find_element(By.TAG_NAME, "body").get_attribute("class"))


def test_reader_mode_hides_chrome_and_keeps_only_passage_text_visible(driver, wait, base_url):
    _set_mobile_viewport(driver)
    _enter_reader_mode(driver, wait, base_url)

    hidden_chrome = [
        '[data-testid="app-header"]',
        ".notice",
        ".reader-toolbar",
        "#reader-search-results",
        "#study-panel",
        "[data-app-dock]",
        ".reader-chapter-header",
        ".reader-chapter-footer",
        ".reader-translation-badge",
        ".verse-number",
        ".verse-actions-button",
        ".verse-state-indicators",
    ]
    for selector in hidden_chrome:
        assert _hidden_or_absent(driver, selector), f"Expected reader mode to hide {selector}"

    passage = driver.find_element(By.CSS_SELECTOR, "#chapter-reader .chapter-text")
    assert passage.is_displayed()
    assert passage.text.strip()


def test_tapping_passage_restores_reader_controls(driver, wait, base_url):
    _set_mobile_viewport(driver)
    _enter_reader_mode(driver, wait, base_url)

    driver.find_element(By.CSS_SELECTOR, "#chapter-reader .verse-text").click()
    wait.until(lambda _driver: "reader-mode" not in _driver.find_element(By.TAG_NAME, "body").get_attribute("class"))

    assert driver.find_element(By.CSS_SELECTOR, '[data-testid="app-header"]').is_displayed()
    assert driver.find_element(By.CSS_SELECTOR, ".reader-toolbar").is_displayed()
    assert driver.find_element(By.CSS_SELECTOR, '[data-testid="reader-controls-trigger"]').is_displayed()


def test_escape_restores_controls_and_other_sections_leave_reader_mode(driver, wait, base_url):
    _set_mobile_viewport(driver)
    _enter_reader_mode(driver, wait, base_url)

    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    wait.until(lambda _driver: "reader-mode" not in _driver.find_element(By.TAG_NAME, "body").get_attribute("class"))

    WorkspacePage(driver, wait, base_url).toggle_reader_mode()
    wait.until(lambda _driver: "reader-mode" in _driver.find_element(By.TAG_NAME, "body").get_attribute("class"))
    driver.execute_script("document.querySelector('[data-testid=\"app-dock-notes\"]').click();")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "notes")
    wait.until(lambda _driver: "reader-mode" not in _driver.find_element(By.TAG_NAME, "body").get_attribute("class"))
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#workspace-pane-notes')))
