from __future__ import annotations

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

from .pages import HomePage, NotesPage


pytestmark = [pytest.mark.gui]


def _highlights_count(driver) -> int:
    text = driver.execute_script("return document.querySelector('#highlights-count')?.textContent || '0';")
    return int(str(text).strip() or "0")


def test_add_note_to_current_chapter(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = NotesPage(driver, wait, base_url)
    page.add_note("GUI test note for John 1")
    page.assert_note_visible("GUI test note for John 1")
    wait.until(lambda _driver: len(_driver.find_elements(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"] .verse-state-note')) >= 1)


def test_highlight_selected_verse_can_be_removed_from_context_menu(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    verse = driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="3"]')
    ActionChains(driver).context_click(verse).perform()
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, "#reader-context-menu").is_displayed())
    driver.find_element(By.CSS_SELECTOR, '[data-context-action="highlight"]').click()
    wait.until(lambda _driver: _highlights_count(_driver) >= 1)
    assert _highlights_count(driver) >= 1
    assert "highlight-yellow" in driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="3"]').get_attribute("class")
    assert driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="3"] .verse-state-highlight').is_displayed()

    verse = driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="3"]')
    ActionChains(driver).context_click(verse).perform()
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, '[data-context-action="highlight"]').text == "Remove Highlight")
    driver.find_element(By.CSS_SELECTOR, '[data-context-action="highlight"]').click()
    wait.until(lambda _driver: "highlight-yellow" not in _driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="3"]').get_attribute("class"))
