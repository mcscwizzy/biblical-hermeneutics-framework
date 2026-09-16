from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from .pages import AskPage, BibleReaderPage, HomePage


pytestmark = [pytest.mark.gui]


def test_ask_bhf_opens_one_contextual_handoff_modal(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = AskPage(driver, wait, base_url)
    assert len(driver.find_elements(By.CSS_SELECTOR, "[data-ask-bhf]")) == 1

    page.open_workspace()

    assert page.reference() == "John 1"
    assert driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-question]").is_displayed()
    assert driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-prepared]").get_attribute("readonly") is not None
    assert driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-status]").get_attribute("aria-live") == "polite"


def test_ask_bhf_rejects_an_empty_question_inline(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = AskPage(driver, wait, base_url)
    page.open_workspace()
    page.click("[data-ask-bhf-primary]")

    assert "Please enter a question" in page.status()


def test_ask_bhf_reads_current_chapter_on_each_open(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    reader = BibleReaderPage(driver, wait, base_url)
    page = AskPage(driver, wait, base_url)
    reader.select_book("James")
    wait.until(lambda _driver: "James 1" in reader.active_pane_heading().text)
    page.open_workspace()
    assert page.reference() == "James 1"
    page.close()

    reader.set_chapter(2)
    wait.until(lambda _driver: "James 2" in reader.active_pane_heading().text)
    page.open_workspace()
    assert page.reference() == "James 2"


def test_ask_bhf_restores_focus_to_its_trigger_on_close(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = AskPage(driver, wait, base_url)
    page.open_workspace()
    page.close()

    assert driver.execute_script("return document.activeElement.matches('[data-ask-bhf]');")


def test_escape_closes_handoff_without_collapsing_companion(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = AskPage(driver, wait, base_url)
    page.open_workspace()
    companion = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    before = companion.get_attribute("data-companion-state")

    driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-question]").send_keys(Keys.ESCAPE)

    wait.until(lambda _driver: not driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-dialog]").is_displayed())
    assert companion.get_attribute("data-companion-state") == before
