from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from .pages import BibleReaderPage, HomePage


def test_mobile_locations_support_keyboard_actions_focus_ack_and_chapter_changes(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    reader = BibleReaderPage(driver, wait, base_url)
    reader.select_book("Genesis").set_chapter(12)
    wait.until(lambda _driver: _driver.execute_script(
        "const state = window.BHFStudySelection.getState(); return state.book === 'Genesis' && state.chapter === 12;"
    ))

    driver.find_element(
        By.CSS_SELECTOR,
        '#chapter-reader .reader-pane.is-active [data-verse="1"] .verse-text',
    ).click()
    driver.find_element(By.CSS_SELECTOR, '[data-passage-action="explore"]').click()
    section = wait.until(lambda _driver: _driver.find_element(
        By.CSS_SELECTOR,
        "[data-companion-locations-section]",
    ))
    wait.until(lambda _driver: not section.get_attribute("hidden"))
    wait.until(lambda _driver: len(section.find_elements(By.CSS_SELECTOR, ".companion-location-card")) == 5)

    layout = driver.execute_script(
        """
        const section = document.querySelector('[data-companion-locations-section]');
        const button = section.querySelector('.companion-location-action');
        const rect = button.getBoundingClientRect();
        return {
          viewport: window.innerWidth,
          document: document.documentElement.scrollWidth,
          section: section.getBoundingClientRect().width,
          actionHeight: rect.height,
          actionWidth: rect.width,
        };
        """
    )
    assert layout["document"] <= layout["viewport"]
    assert layout["section"] <= layout["viewport"]
    assert layout["actionHeight"] >= 44
    assert layout["actionWidth"] > 0

    titles_before_navigation = [
        heading.text
        for heading in section.find_elements(By.CSS_SELECTOR, ".companion-location-card h4")
    ]
    view_all = section.find_element(By.CSS_SELECTOR, "[data-companion-locations-more]")
    view_all.send_keys(Keys.ENTER)
    wait.until(lambda _driver: "all 10 locations" in section.find_element(
        By.CSS_SELECTOR,
        "[data-companion-locations-status]",
    ).text.lower())
    assert section.find_element(By.CSS_SELECTOR, "[data-companion-locations-status]").get_attribute("role") == "status"

    reader.next_chapter()
    wait.until(lambda _driver: _driver.execute_script(
        "const state = window.BHFStudySelection.getState(); return state.book === 'Genesis' && state.chapter === 13;"
    ))
    wait.until(lambda _driver: section.find_element(
        By.CSS_SELECTOR,
        ".companion-location-reference",
    ).text.startswith("Genesis 13:"))
    titles_after_navigation = [
        heading.text
        for heading in section.find_elements(By.CSS_SELECTOR, ".companion-location-card h4")
    ]
    assert titles_after_navigation != titles_before_navigation
