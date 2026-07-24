from __future__ import annotations

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from .pages import HomePage, NotesPage


pytestmark = [pytest.mark.gui]


def _highlights_count(driver) -> int:
    text = driver.execute_script("return document.querySelector('#highlights-count')?.textContent || '0';")
    return int(str(text).strip() or "0")


def _click_context_action(driver, wait, action: str):
    button = wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, f'[data-context-action="{action}"]'))
    if not button.is_displayed():
        trigger = button.find_element(By.XPATH, "ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' context-menu-section ')][1]//*[@data-context-submenu]")
        trigger.click()
        wait.until(lambda _driver: button.is_displayed())
    button.click()


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
    _click_context_action(driver, wait, "highlight")
    wait.until(lambda _driver: _highlights_count(_driver) >= 1)
    assert _highlights_count(driver) >= 1
    assert "highlight-yellow" in driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="3"]').get_attribute("class")
    assert driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="3"] .verse-state-highlight').is_displayed()
    assert driver.find_element(By.CSS_SELECTOR, "#selection-summary").text == ""
    assert driver.find_element(By.CSS_SELECTOR, '.ask-form [name="reader_start_verse"]').get_attribute("value") == ""
    assert driver.find_element(By.CSS_SELECTOR, '.ask-form [name="reader_end_verse"]').get_attribute("value") == ""
    assert driver.find_element(By.CSS_SELECTOR, '.ask-form [name="reader_selected_text"]').get_attribute("value") == ""

    verse = driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="3"]')
    ActionChains(driver).context_click(verse).perform()
    wait.until(lambda _driver: _driver.execute_script("return document.querySelector('[data-context-action=\"highlight\"]')?.textContent") == "Remove Highlight")
    _click_context_action(driver, wait, "highlight")
    wait.until(lambda _driver: "highlight-yellow" not in _driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="3"]').get_attribute("class"))


def test_highlighted_verse_can_be_removed_by_tapping_verse(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    verse = driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="4"]')
    ActionChains(driver).context_click(verse).perform()
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, "#reader-context-menu").is_displayed())
    _click_context_action(driver, wait, "highlight")
    wait.until(lambda _driver: "highlight-yellow" in _driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="4"]').get_attribute("class"))
    count_after_create = _highlights_count(driver)

    driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="4"] .verse-text').click()
    wait.until(lambda _driver: "highlight-yellow" not in _driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="4"]').get_attribute("class"))
    wait.until(lambda _driver: _highlights_count(_driver) < count_after_create)


def test_shift_click_range_can_be_highlighted_from_context_menu(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()

    driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"] [data-verse-select]').click()
    verse_three_select = driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="3"] [data-verse-select]')
    ActionChains(driver).key_down(Keys.SHIFT).click(verse_three_select).key_up(Keys.SHIFT).perform()

    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, '.ask-form [name="reader_end_verse"]').get_attribute("value") == "3")
    for verse_number in (1, 2, 3):
        assert "selected" in driver.find_element(By.CSS_SELECTOR, f'#chapter-reader [data-verse="{verse_number}"]').get_attribute("class")

    verse_two = driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="2"]')
    ActionChains(driver).context_click(verse_two).perform()
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, "#reader-context-menu").is_displayed())
    _click_context_action(driver, wait, "highlight")

    for verse_number in (1, 2, 3):
        wait.until(lambda _driver, number=verse_number: "highlight-yellow" in _driver.find_element(By.CSS_SELECTOR, f'#chapter-reader [data-verse="{number}"]').get_attribute("class"))


def test_ask_bhf_context_action_inserts_selected_text_without_replacing_prompt(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()

    verse_one = driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"]')
    ActionChains(driver).context_click(verse_one).perform()
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, "#reader-context-menu").is_displayed())
    _click_context_action(driver, wait, "ask_bhf")

    question = driver.find_element(By.CSS_SELECTOR, '[data-testid="question-input"]')
    selected_text = driver.find_element(By.CSS_SELECTOR, '.ask-form [name="reader_selected_text"]').get_attribute("value")
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, '[data-testid="question-input"]').get_attribute("value") == selected_text)
    assert selected_text
    assert "Selected" not in question.get_attribute("value")

    question.clear()
    question.send_keys("Keep my typed question.")

    verse_two = driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="2"]')
    ActionChains(driver).context_click(verse_two).perform()
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, "#reader-context-menu").is_displayed())
    _click_context_action(driver, wait, "ask_bhf")

    selected_text = driver.find_element(By.CSS_SELECTOR, '.ask-form [name="reader_selected_text"]').get_attribute("value")
    value = question.get_attribute("value")
    assert value.startswith("Keep my typed question.")
    assert selected_text in value
