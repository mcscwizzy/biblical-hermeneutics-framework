from __future__ import annotations

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

from .pages import HomePage, NotesPage


pytestmark = [pytest.mark.gui]


def test_add_note_to_current_chapter(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = NotesPage(driver, wait, base_url)
    page.add_note("GUI test note for John 1")
    page.assert_note_visible("GUI test note for John 1")


def test_highlight_selected_verse(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    verse = driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"]')
    ActionChains(driver).context_click(verse).perform()
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, "#reader-context-menu").is_displayed())
    driver.find_element(By.CSS_SELECTOR, '[data-context-action="highlight"]').click()
    wait.until(lambda _driver: int(_driver.find_element(By.CSS_SELECTOR, "#highlights-count").text) >= 1)
    assert int(driver.find_element(By.CSS_SELECTOR, "#highlights-count").text) >= 1
    assert "highlight-yellow" in driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"]').get_attribute("class")
