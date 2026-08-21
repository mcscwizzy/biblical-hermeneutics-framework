from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .pages import HomePage, NotesPage


pytestmark = [pytest.mark.gui]


def test_add_note_to_current_chapter(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = NotesPage(driver, wait, base_url)
    page.add_note("GUI test note for John 1")
    page.assert_note_visible("GUI test note for John 1")
    wait.until(lambda _driver: len(_driver.find_elements(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"] .verse-state-note')) >= 1)


def test_standalone_note_can_be_autosaved_and_found_in_all_notes(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()

    driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-notes"]').click()
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="new-note-panel-button"]'))).click()
    textarea = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="note-textarea"]')))
    textarea.send_keys("A standalone sermon note")
    wait.until(lambda _driver: "Saved" in _driver.find_element(By.CSS_SELECTOR, "[data-note-save-status]").text)

    driver.find_element(By.CSS_SELECTOR, '[data-testid="all-notes-button"]').click()
    wait.until(lambda _driver: "A standalone sermon note" in _driver.find_element(By.CSS_SELECTOR, "#notes-list").text)
    assert "Standalone note" in driver.find_element(By.CSS_SELECTOR, "#notes-list").text
    assert not driver.find_elements(By.CSS_SELECTOR, "#chapter-reader .verse-state-note")
