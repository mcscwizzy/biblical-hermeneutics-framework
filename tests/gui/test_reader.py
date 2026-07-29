from __future__ import annotations

import pytest
from selenium.common.exceptions import StaleElementReferenceException
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


def test_last_reader_location_is_stored_locally_and_restored_after_refresh(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = BibleReaderPage(driver, wait, base_url)
    page.select_book("Genesis")
    wait.until(lambda _driver: "Genesis 1" in _driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
    driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="5"] [data-verse-select]').click()

    stored = driver.execute_async_script(
        """
        const done = arguments[arguments.length - 1];
        window.setTimeout(() => {
          window.BHFOfflineDB.get("metadata", "reader-location")
            .then((record) => done(record?.payload || null))
            .catch((error) => done({error: String(error)}));
        }, 350);
        """
    )
    assert stored["book"] == "Genesis"
    assert stored["chapter"] == 1
    assert stored["verse"] == 5

    driver.refresh()
    HomePage(driver, wait, base_url).wait_loaded()
    wait.until(lambda _driver: "Genesis 1" in _driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
    verse_position = driver.execute_script(
        """
        const verse = document.querySelector('#chapter-reader [data-verse="5"]');
        return {top: verse.getBoundingClientRect().top, viewport: window.innerHeight};
        """
    )
    assert abs(verse_position["top"] - verse_position["viewport"] / 2) < 250


def test_bible_search(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = BibleReaderPage(driver, wait, base_url)
    page.search("beginning")
    wait.until(lambda _driver: len(_driver.find_elements(By.CSS_SELECTOR, "#reader-search-results .search-result-card")) > 0)
    assert driver.find_element(By.CSS_SELECTOR, "#reader-search-results").is_displayed()
    page.clear_search()
    wait.until(lambda _driver: not _driver.find_element(By.CSS_SELECTOR, "#reader-search-results").is_displayed())


def test_import_dialog_uses_user_supplied_translation_name(driver, wait, base_url, tmp_path):
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

    name_input = driver.find_element(By.CSS_SELECTOR, "[data-translation-import-name]")
    name_input.send_keys("Christian Standard Bible")
    file_input = driver.find_element(By.CSS_SELECTOR, "[data-translation-import-file]")
    file_input.send_keys(str(xml_path))

    assert driver.find_element(By.CSS_SELECTOR, "[data-translation-import-name]").get_attribute("value") == "Christian Standard Bible"
    assert page.current_translation_abbreviation() == "ASV"


def test_import_dialog_opens_with_empty_translation_name(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = BibleReaderPage(driver, wait, base_url)

    page.click('[data-testid="translation-import-button"]')
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, "[data-translation-import-dialog]").is_displayed())

    name_input = driver.find_element(By.CSS_SELECTOR, "[data-translation-import-name]")
    name_input.send_keys("Temporary Translation")

    driver.find_element(By.CSS_SELECTOR, "[data-close-translation-import]").click()
    wait.until(lambda _driver: not _driver.find_element(By.CSS_SELECTOR, "[data-translation-import-dialog]").is_displayed())

    page.click('[data-testid="translation-import-button"]')
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, "[data-translation-import-name]").get_attribute("value") == "")
