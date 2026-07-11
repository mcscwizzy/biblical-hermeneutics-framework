from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .pages import HomePage, WorkspacePage


pytestmark = [pytest.mark.gui]


def _set_mobile_viewport(driver):
    driver.set_window_size(390, 844)


def test_app_dock_switches_between_bible_and_ask_on_mobile(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()

    page = WorkspacePage(driver, wait, base_url)
    assert page.find('[data-testid="app-dock-bible"]').is_displayed()

    page.open_app_section("ask")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "ask")
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="question-input"]')))
    assert page.find("#study-panel").is_displayed()

    page.open_app_section("bible")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "bible")
    wait.until(lambda _driver: not _driver.find_element(By.ID, "study-panel").is_displayed())


def test_mobile_ask_submit_still_works(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()

    page = WorkspacePage(driver, wait, base_url)
    page.open_app_section("ask")
    question = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="question-input"]')))
    question.clear()
    question.send_keys("What does John 1 emphasize?")
    page.click('[data-testid="ask-submit"]')
    wait.until(lambda _driver: "Deterministic test answer" in _driver.find_element(By.CSS_SELECTOR, '[data-testid="answer-output"]').text)


def test_mobile_verse_actions_support_notes_and_highlights(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()

    page = WorkspacePage(driver, wait, base_url)
    page.open_app_section("bible")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "bible")

    verse_one = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#chapter-reader [data-verse="1"]')))
    assert verse_one.find_element(By.CSS_SELECTOR, "[data-verse-actions]").is_displayed()

    verse_one.find_element(By.CSS_SELECTOR, "[data-verse-actions]").click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#reader-context-menu")))
    page.click('[data-context-action="note"]')
    note_editor = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="note-editor"]')))
    textarea = note_editor.find_element(By.CSS_SELECTOR, '[data-testid="note-textarea"]')
    textarea.clear()
    textarea.send_keys("Mobile note for John 1")
    page.click('[data-testid="save-note-button"]')
    wait.until(lambda _driver: "Mobile note for John 1" in _driver.find_element(By.CSS_SELECTOR, "#notes-list").text)

    page.open_app_section("bible")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "bible")
    verse_one = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#chapter-reader [data-verse="1"]')))
    verse_one.find_element(By.CSS_SELECTOR, "[data-verse-actions]").click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#reader-context-menu")))
    page.click('[data-context-action="highlight"]')
    wait.until(lambda _driver: "highlight-yellow" in _driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"]').get_attribute("class"))


def test_app_dock_remembers_group_subtabs_on_mobile(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()

    page = WorkspacePage(driver, wait, base_url)
    page.open_app_section("studies")
    page.open_tab("highlights")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "studies")
    page.open_app_section("bible")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "bible")
    page.open_app_section("studies")
    page.assert_tab_visible("highlights")

    page.open_app_section("explore")
    page.open_tab("journey")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "explore")
    page.open_app_section("bible")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "bible")
    page.open_app_section("explore")
    page.assert_tab_visible("journey")
