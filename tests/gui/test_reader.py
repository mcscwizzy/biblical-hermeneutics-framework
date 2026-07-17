from __future__ import annotations

import pytest
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

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


def test_import_dialog_infers_translation_from_filename(driver, wait, base_url, tmp_path):
    xml_path = tmp_path / "csb.xml"
    xml_path.write_text(
        """
        <XMLBIBLE biblename="Imported CSB" language="en">
          <BIBLEBOOK bnumber="43" bname="John">
            <CHAPTER cnumber="1">
              <VERS vnumber="1">Imported CSB text.</VERS>
            </CHAPTER>
          </BIBLEBOOK>
        </XMLBIBLE>
        """.strip(),
        encoding="utf-8",
    )

    HomePage(driver, wait, base_url).open().wait_loaded()
    page = BibleReaderPage(driver, wait, base_url)
    page.click('[data-testid="translation-import-button"]')
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, "[data-translation-import-dialog]").is_displayed())

    file_input = driver.find_element(By.CSS_SELECTOR, "[data-translation-import-file]")
    file_input.send_keys(str(xml_path))

    wait.until(
        lambda _driver: Select(
            _driver.find_element(By.CSS_SELECTOR, "[data-translation-import-id]")
        ).first_selected_option.get_attribute("value") == "csb"
    )

    driver.find_element(By.CSS_SELECTOR, "[data-translation-import-confirm]").click()
    driver.find_element(By.CSS_SELECTOR, "[data-translation-import-form] button[type='submit']").click()

    def badge_is_csb(_driver):
        try:
            return _driver.find_element(By.CSS_SELECTOR, ".reader-translation-badge").text == "CSB"
        except StaleElementReferenceException:
            return False

    wait.until(badge_is_csb)
    assert "Imported CSB text." in driver.find_element(By.CSS_SELECTOR, "#chapter-reader").text


def test_import_dialog_remembers_last_manual_choice(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = BibleReaderPage(driver, wait, base_url)

    page.click('[data-testid="translation-import-button"]')
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, "[data-translation-import-dialog]").is_displayed())

    select = Select(driver.find_element(By.CSS_SELECTOR, "[data-translation-import-id]"))
    select.select_by_value("csb")
    wait.until(
        lambda _driver: Select(
            _driver.find_element(By.CSS_SELECTOR, "[data-translation-import-id]")
        ).first_selected_option.get_attribute("value") == "csb"
    )

    driver.find_element(By.CSS_SELECTOR, "[data-close-translation-import]").click()
    wait.until(lambda _driver: not _driver.find_element(By.CSS_SELECTOR, "[data-translation-import-dialog]").is_displayed())

    page.click('[data-testid="translation-import-button"]')
    wait.until(
        lambda _driver: Select(
            _driver.find_element(By.CSS_SELECTOR, "[data-translation-import-id]")
        ).first_selected_option.get_attribute("value") == "csb"
    )
