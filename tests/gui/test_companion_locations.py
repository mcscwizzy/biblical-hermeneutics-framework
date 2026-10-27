from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from .pages import BibleReaderPage, HomePage


def test_chapter_options_stay_available_when_book_chapter_load_finishes(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    driver.execute_script(
        """
        const originalFetch = window.fetch.bind(window);
        window.fetch = async (input, init) => {
          const href = input instanceof Request ? input.url : String(input);
          if (new URL(href, window.location.href).pathname === "/api/bible/Genesis/1") {
            await new Promise((resolve) => window.setTimeout(resolve, 800));
          }
          return originalFetch(input, init);
        };
        """
    )

    BibleReaderPage(driver, wait, base_url).select_book("Genesis")
    chapter_twelve = wait.until(lambda _driver: _driver.find_element(
        By.CSS_SELECTOR,
        '[data-testid="chapter-input"] option[value="12"]',
    ))
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudySelection.getState().book === 'Genesis' "
        "&& window.BHFStudySelection.getState().chapter === 1 "
        "&& !document.querySelector('#chapter-reader').hasAttribute('aria-busy');"
    ))

    assert chapter_twelve.is_enabled()


def test_mobile_locations_support_keyboard_actions_pagination_and_chapter_changes(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    reader = BibleReaderPage(driver, wait, base_url)
    reader.select_book("Genesis").set_chapter(12)
    wait.until(lambda _driver: _driver.execute_script(
        "const state = window.BHFStudySelection.getState(); return state.book === 'Genesis' && state.chapter === 12;"
    ))

    driver.execute_script(
        """
        const selectVerse = (number, shiftKey = false) => {
          const target = document.querySelector(
            `#chapter-reader .reader-pane.is-active [data-verse="${number}"] .verse-text`,
          );
          target.dispatchEvent(new MouseEvent("click", {
            bubbles: true,
            cancelable: true,
            shiftKey,
          }));
        };
        selectVerse(5);
        selectVerse(9, true);
        """
    )
    wait.until(lambda _driver: _driver.execute_script(
        "const state = window.BHFStudySelection.getState(); "
        "return state.reference === 'Genesis 12:5-9';"
    ))
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
    wait.until(lambda _driver: "all 9 locations" in section.find_element(
        By.CSS_SELECTOR,
        "[data-companion-locations-status]",
    ).text.lower())
    assert section.find_element(By.CSS_SELECTOR, "[data-companion-locations-status]").get_attribute("role") == "status"

    driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-bible"]').click()
    wait.until(lambda _driver: _driver.find_element(By.ID, "study-panel").get_attribute("data-companion-state") == "closed")
    reader.set_chapter(13)
    wait.until(lambda _driver: _driver.execute_script(
        "const state = window.BHFStudySelection.getState(); return state.book === 'Genesis' && state.chapter === 13;"
    ))
    wait.until(lambda _driver: _driver.execute_script(
        "const context = window.BHFStudyCompanion.getContext(); "
        "return context?.reference === 'Genesis 13' && context.locations?.total === 10;"
    ))
    wait.until(lambda _driver: _driver.execute_script(
        "const section = document.querySelector('[data-companion-locations-section]'); "
        "return Array.from(section?.querySelectorAll('.companion-location-reference') || []) "
        ".some((item) => item.textContent.trim().startsWith('Genesis 13:'));"
    ))
    titles_after_navigation = driver.execute_script(
        "return Array.from(document.querySelectorAll("
        "'[data-companion-locations-section] .companion-location-card h4')) "
        ".map((heading) => heading.textContent.trim());"
    )
    assert titles_after_navigation != titles_before_navigation
