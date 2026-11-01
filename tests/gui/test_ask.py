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


def test_desktop_ask_bhf_recovers_when_clipboard_rejects_after_focus_loss(
    driver, wait, base_url
):
    driver.set_window_size(1440, 1000)
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = AskPage(driver, wait, base_url)
    page.open_workspace()
    driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-question]").send_keys(
        "What does John 1 emphasize?"
    )
    driver.execute_script(
        """
        window.__askBHFEvents = [];
        window.__askBHFFocusLost = false;
        window.open = (...args) => {
          window.__askBHFEvents.push("open");
          window.__askBHFFocusLost = true;
          return null;
        };
        Object.defineProperty(navigator, "clipboard", {
          configurable: true,
          value: {
            writeText(text) {
              window.__askBHFEvents.push("clipboard");
              return Promise.resolve().then(() => {
                if (window.__askBHFFocusLost) {
                  throw new DOMException("Simulated focus loss", "NotAllowedError");
                }
              });
            },
          },
        });
        """
    )

    driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-primary]").click()
    manual_copy = wait.until(
        lambda _driver: _driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-manual-copy]")
        if _driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-manual-copy]").is_displayed()
        else False
    )
    open_fallback = driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-open]")
    prepared = driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-prepared]")
    status = page.status()

    assert driver.execute_script("return window.__askBHFEvents;") == ["clipboard", "open"]
    assert "John 1" in prepared.get_attribute("value")
    assert "What does John 1 emphasize?" in prepared.get_attribute("value")
    assert driver.execute_script(
        """
        const prepared = document.querySelector("[data-ask-bhf-prepared]");
        return prepared.selectionStart === 0 && prepared.selectionEnd === prepared.value.length;
        """
    )
    assert "could not copy" in status.lower()
    assert "question copied" not in status.lower()
    assert manual_copy.is_displayed()
    assert open_fallback.is_displayed()
    assert open_fallback.get_attribute("href") == driver.execute_script(
        "return window.BHFRuntimeConfig.assistantUrl;"
    )
    assert open_fallback.get_attribute("target") == "_blank"
    assert open_fallback.get_attribute("rel") == "noopener noreferrer"

    driver.execute_script("window.__askBHFFocusLost = false;")
    manual_copy.click()
    wait.until(lambda _driver: "question copied" in page.status().lower())
    assert driver.execute_script("return window.__askBHFEvents;") == [
        "clipboard",
        "open",
        "clipboard",
    ]


def test_escape_closes_handoff_without_collapsing_companion(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-explore"]').click()
    wait.until(
        lambda _driver: any(
            resource.is_displayed()
            for resource in _driver.find_elements(
                By.CSS_SELECTOR, '[data-companion-resource="maps"]'
            )
        )
    )
    page = AskPage(driver, wait, base_url)
    page.open_workspace()
    companion = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    before = companion.get_attribute("data-companion-state")

    driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-question]").send_keys(Keys.ESCAPE)

    wait.until(lambda _driver: not driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-dialog]").is_displayed())
    assert companion.get_attribute("data-companion-state") == before
