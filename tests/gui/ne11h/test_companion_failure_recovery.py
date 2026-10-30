from __future__ import annotations

import json

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import _select_verses


def test_failed_companion_request_keeps_reader_and_recovers_after_retry(driver, base_url):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "John", 1, [14])
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion?.getContext?.()?.reference === 'John 1:14';"
    ))

    driver.execute_script(
        """
        window.__ne11hOriginalFetch = window.fetch;
        window.__ne11hCompanionFailures = 0;
        window.fetch = function(input, options = {}) {
          const rawUrl = typeof input === "string" ? input : (input?.url || String(input));
          if (rawUrl.includes("/api/study/companion-context")
              && window.__ne11hCompanionFailures === 0) {
            window.__ne11hCompanionFailures += 1;
            return Promise.reject(new TypeError("Failed to fetch"));
          }
          return window.__ne11hOriginalFetch.call(this, input, options);
        };
        const current = window.BHFStudySelection.getState();
        window.BHFStudySelection.setSelection({
          ...current, startVerse: 13, endVerse: 13, selectedVerses: [13],
          selectedText: "These things have I spoken unto you.",
          reference: "John 1:13", hasPassageSelection: true,
        }, "ne11h-failure-injection");
        """
    )

    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion?.getContextRecord?.()?.status === 'error';"
    ))
    error = wait.until(lambda browser: browser.find_element(
        "css selector", ".companion-availability-error[role='alert']"
    ))
    assert error.is_displayed()
    error_text = error.text
    assert error_text
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == "John 1:13"
    assert driver.find_element(
        "css selector", '#chapter-reader .reader-pane.is-active [data-verse="13"]'
    ).is_displayed()

    driver.execute_script(
        """
        window.fetch = window.__ne11hOriginalFetch;
        const current = window.BHFStudySelection.getState();
        window.BHFStudySelection.setSelection({
          ...current, startVerse: 14, endVerse: 14, selectedVerses: [14],
          selectedText: "And the Word was made flesh, and dwelt among us.",
          reference: "John 1:14", hasPassageSelection: true,
        }, "ne11h-reconnect");
        """
    )
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion?.getContextRecord?.()?.status === 'ready' "
        "&& window.BHFStudyCompanion.getContext()?.reference === 'John 1:14';"
    ))
    assert not driver.find_elements(
        "css selector", ".companion-availability-error[role='alert']"
    )
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == "John 1:14"
    print("NE11H_COMPANION_RECOVERY=" + json.dumps({
        "failed_request_count": 1,
        "error_state_visible": True,
        "error_text": error_text,
        "scripture_preserved_during_failure": "John 1:13",
        "retry_recovered": True,
    }), flush=True)


def test_browser_back_during_map_loading_restores_study_overview(driver, base_url):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    verse = driver.find_element(
        By.CSS_SELECTOR,
        '#chapter-reader .reader-pane.is-active [data-verse="1"] .verse-text',
    )
    verse.click()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection.getState().reference === 'John 1:1';"
    ))
    panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    wait.until(lambda _browser: panel.get_attribute("data-companion-state") == "study")

    driver.execute_script(
        """
        window.__ne11hOriginalFetch = window.fetch;
        window.__ne11hMapPending = [];
        window.fetch = function(input, options = {}) {
          const rawUrl = typeof input === "string" ? input : (input?.url || String(input));
          if (new URL(rawUrl, location.href).pathname !== "/api/maps/catalog") {
            return window.__ne11hOriginalFetch.call(this, input, options);
          }
          return window.__ne11hOriginalFetch.call(this, input, options).then(response => new Promise(resolve => {
            window.__ne11hMapPending.push({url: rawUrl, release: () => resolve(response)});
          }));
        };
        window.BHFStudyCompanion.openResource("maps");
        """
    )
    wait.until(lambda browser: browser.execute_script(
        "return window.__ne11hMapPending?.length > 0;"
    ))
    map_status = driver.find_element(By.CSS_SELECTOR, "#map-panel-status")
    assert map_status.is_displayed() and "Loading" in map_status.text
    loading_text = map_status.text

    driver.back()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion.getState().resource === null "
        "&& window.BHFStudyCompanion.getState().state === 'study';"
    ))
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == "John 1:1"

    driver.execute_script(
        """
        window.__ne11hMapPending.forEach(entry => entry.release());
        window.fetch = window.__ne11hOriginalFetch;
        """
    )
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion.getState().resource === null;"
    ))
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == "John 1:1"
    print("NE11H_BACK_DURING_LOADING=" + json.dumps({
        "delayed_request": "/api/maps/catalog",
        "loading_state_observed": loading_text,
        "back_restored": "study overview",
        "selection_preserved": "John 1:1",
        "late_response_overwrote_state": False,
    }), flush=True)
