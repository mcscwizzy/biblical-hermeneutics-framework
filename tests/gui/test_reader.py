from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from .pages import BibleReaderPage, HomePage


pytestmark = [pytest.mark.gui]


def test_default_chapter_loads(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    passage = driver.find_element(By.CSS_SELECTOR, '[data-testid="reader-passage"]')
    assert passage.text.strip()
    assert len(driver.find_elements(By.CSS_SELECTOR, "#chapter-reader [data-verse]")) > 0


def test_change_book_and_chapter(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = BibleReaderPage(driver, wait, base_url)
    page.select_book("Genesis")
    wait.until(lambda _driver: "Genesis 1" in _driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
    assert "Genesis 1" in driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text
    page.set_chapter(1)
    page.next_chapter()
    wait.until(lambda _driver: "Genesis 2" in _driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
    assert "Genesis 2" in driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text
    page.previous_chapter()
    wait.until(lambda _driver: "Genesis 1" in _driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
    assert "Genesis 1" in driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text


def test_clicking_verse_number_selects_entire_verse(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()

    driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"] [data-verse-select]').click()

    wait.until(lambda _driver: "selected" in _driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"]').get_attribute("class"))
    assert driver.find_element(By.CSS_SELECTOR, '.ask-form [name="reader_start_verse"]').get_attribute("value") == "1"
    assert driver.find_element(By.CSS_SELECTOR, '.ask-form [name="reader_end_verse"]').get_attribute("value") == "1"
    assert driver.find_element(By.CSS_SELECTOR, '.ask-form [name="reader_selected_text"]').get_attribute("value")


def test_bible_search(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = BibleReaderPage(driver, wait, base_url)
    page.search("beginning")
    wait.until(lambda _driver: len(_driver.find_elements(By.CSS_SELECTOR, "#reader-search-results .search-result-card")) > 0)
    assert driver.find_element(By.CSS_SELECTOR, "#reader-search-results").is_displayed()
    page.clear_search()
    wait.until(lambda _driver: not _driver.find_element(By.CSS_SELECTOR, "#reader-search-results").is_displayed())
