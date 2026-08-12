from __future__ import annotations

import json

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .pages import BibleReaderPage, HomePage, WorkspacePage


pytestmark = [pytest.mark.gui]


def _show_canonical_workspace(driver):
    driver.execute_script(
        """
        window.BHFStudyCompanion.showPersonalResource('canonical-browser', 'Canonical Knowledge');
        window.BHFStudyActions.openWorkspaceTab('context');
        """
    )


def _open_canonical_browser(driver, wait, base_url, query: str = "Shechem") -> WorkspacePage:
    driver.set_window_size(1440, 1000)
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = WorkspacePage(driver, wait, base_url)
    _show_canonical_workspace(driver)
    page.assert_tab_visible("context")

    search_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="canonical-search-input"]')))
    search_input.clear()
    search_input.send_keys(query)
    page.click('[data-testid="canonical-search-button"]')
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, '[data-canonical-browser-count]').text.strip() != "0")
    wait.until(
        lambda _driver: query.lower()
        in _driver.find_element(
            By.CSS_SELECTOR, '[data-canonical-browser-results]'
        ).get_attribute("textContent").lower()
    )
    return page


def test_canonical_browser_starts_empty_until_searched(driver, wait, base_url):
    driver.set_window_size(1440, 1000)
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = WorkspacePage(driver, wait, base_url)
    _show_canonical_workspace(driver)
    page.assert_tab_visible("context")

    assert driver.find_element(By.CSS_SELECTOR, '[data-canonical-browser-count]').text.strip() == "0"
    assert "Search the canonical library to see results." in driver.find_element(By.CSS_SELECTOR, '[data-canonical-browser-summary]').text
    assert not driver.find_elements(By.CSS_SELECTOR, '[data-canonical-browser-results] [data-canonical-object-id]')


def test_canonical_browser_search_detail_and_source_view(driver, wait, base_url):
    page = _open_canonical_browser(driver, wait, base_url)

    page.click('[data-testid="canonical-result-view-button"]')
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, '[data-canonical-detail-title]').text == "Shechem")

    assert driver.find_element(By.CSS_SELECTOR, '[data-canonical-detail-status]').text == "In Review"
    badges = driver.find_element(By.CSS_SELECTOR, '[data-canonical-detail-badges]').text
    assert "Place" in badges
    assert "Complete" in badges
    assert "Medium" in badges
    assert driver.find_element(By.CSS_SELECTOR, '[data-canonical-detail-reason]').text

    assert len(driver.find_elements(By.CSS_SELECTOR, '[data-canonical-detail-scripture] .canonical-detail-item')) > 0
    assert len(driver.find_elements(By.CSS_SELECTOR, '[data-canonical-detail-related] .canonical-detail-item')) > 0
    assert len(driver.find_elements(By.CSS_SELECTOR, '[data-canonical-detail-sources] .canonical-source-card')) > 0

    curation_href = driver.find_element(By.CSS_SELECTOR, '[data-testid="canonical-open-curation"]').get_attribute("href")
    assert "/curation?collection=place" in curation_href


def test_canonical_browser_linking_object_to_note_adds_canonical_ids(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    BibleReaderPage(driver, wait, base_url).select_verse(1)

    page = _open_canonical_browser(driver, wait, base_url)

    page.click('[data-testid="canonical-result-link-note"]')
    note_editor = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="note-editor"]')))
    canonical_ids = note_editor.find_element(By.CSS_SELECTOR, '[data-testid="note-canonical-object-ids"]')
    wait.until(lambda _driver: "shechem" in canonical_ids.get_attribute("value"))

    textarea = note_editor.find_element(By.CSS_SELECTOR, '[data-testid="note-textarea"]')
    textarea.clear()
    textarea.send_keys("Canonical browser note for Shechem")
    page.click('[data-testid="save-note-button"]')

    wait.until(lambda _driver: "Canonical browser note for Shechem" in _driver.find_element(By.CSS_SELECTOR, "#notes-list").text)
    wait.until(lambda _driver: len(_driver.find_elements(By.CSS_SELECTOR, "#notes-list [data-canonical-object-id='shechem']")) > 0)


def test_canonical_browser_opens_editor_for_draft_object(driver, wait, base_url):
    page = _open_canonical_browser(driver, wait, base_url, query="Joel")

    page.click('[data-testid="canonical-result-view-button"]')
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, '[data-canonical-detail-title]').text == "Joel")
    editor_link = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="canonical-open-editor"]')))
    assert editor_link.is_displayed()
    editor_link.click()

    editor_form = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="canonical-editor-form"]')))
    wait.until(lambda _driver: "CKL Draft Editor" in _driver.title)
    assert "Draft inventory" in driver.find_element(By.TAG_NAME, "body").text

    textarea = editor_form.find_element(By.CSS_SELECTOR, '[data-testid="canonical-editor-json"]')
    payload = json.loads(textarea.get_attribute("value"))
    payload["summary"] = "Joel is a draft prophetic-book record for the day of the Lord."
    driver.execute_script(
        """
        const textarea = arguments[0];
        const value = arguments[1];
        textarea.value = value;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        """,
        textarea,
        json.dumps(payload, indent=2, ensure_ascii=False),
    )
    page.click('[data-testid="canonical-editor-save"]')

    wait.until(lambda _driver: "Saved Joel." in _driver.find_element(By.TAG_NAME, "body").text)
    wait.until(lambda _driver: payload["summary"] in _driver.find_element(By.TAG_NAME, "body").text)
