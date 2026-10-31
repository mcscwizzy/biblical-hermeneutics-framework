from __future__ import annotations

from pathlib import Path

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from .pages import HomePage


pytestmark = [pytest.mark.gui]


def test_feature_disabled_overview_keeps_compact_context_and_source_fallback(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    driver.execute_script(
        """
        window.__ui07OriginalFetch = window.fetch.bind(window);
        window.fetch = async (input, options) => {
          const raw = input instanceof Request ? input.url : String(input);
          if (new URL(raw, location.href).pathname === '/api/study/companion-context') {
            return new Response(JSON.stringify({reference: 'John 1:1', resources: {}, entities: {}, summaries: {}}), {status: 200, headers: {'Content-Type': 'application/json'}});
          }
          return window.__ui07OriginalFetch(input, options);
        };
        """
    )
    verse = driver.find_element(
        By.CSS_SELECTOR,
        '#chapter-reader .reader-pane.is-active [data-verse="1"] .verse-text',
    )
    verse.click()
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudyCompanion.getContextRecord()?.status === 'ready';"
    ))
    panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "peek")
    driver.find_element(By.CSS_SELECTOR, '[data-passage-action="explore"]').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")

    assert not driver.execute_script("return window.BHFRuntimeConfig.narrativeExplorerEnabled")
    assert driver.find_element(By.CSS_SELECTOR, "[data-companion-overview]").is_displayed()
    fallback = driver.find_element(By.CSS_SELECTOR, "[data-companion-research-fallback]")
    assert fallback.is_displayed()
    assert "Explore the Narrative is unavailable" in fallback.text
    assert len(driver.find_elements(By.CSS_SELECTOR, "[data-companion-primary-research] .companion-narrative-card")) == 1
    assert fallback.find_element(By.CSS_SELECTOR, '[data-companion-resource="understand_passage"]')
    assert fallback.find_element(By.CSS_SELECTOR, '[data-companion-resource="browse_research"]')
    assert driver.find_element(By.CSS_SELECTOR, '[data-companion-resource="places_locations"]').is_displayed()
    assert not driver.find_element(By.CSS_SELECTOR, "[data-companion-explore-catalogue]").is_displayed()
    driver.find_element(By.CSS_SELECTOR, '[data-companion-resource="understand_passage"]').click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-understand-passage], .companion-context-topic-status")))
    assert "Understand the Passage" in driver.find_element(By.CSS_SELECTOR, "[data-companion-resource-host]").text
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    wait.until(lambda _driver: driver.find_element(By.CSS_SELECTOR, "[data-companion-overview]").is_displayed())

    metrics = driver.execute_script(
        "return {width: innerWidth, body: document.documentElement.scrollWidth, overview: document.querySelector('[data-companion-overview]').scrollWidth};"
    )
    assert metrics["width"] == 390
    assert metrics["body"] <= metrics["width"]
    assert metrics["overview"] <= metrics["width"]

    driver.find_element(By.CSS_SELECTOR, '[data-companion-resource="browse_research"]').click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".companion-research-sources-view")))
    sources = driver.find_element(By.CSS_SELECTOR, "[data-companion-resource-host]")
    assert "Open Canonical Knowledge" in sources.text
    assert "Open Maps Explorer" in sources.text
    assert "Open Archaeology Library" in sources.text
    assert "Open Cross References" in sources.text
    assert "Open Timeline" in sources.text
    assert "Open passage Archaeology" in sources.text
    assert "Open Places & Locations" in sources.text
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    wait.until(lambda _driver: driver.find_element(By.CSS_SELECTOR, "[data-companion-overview]").is_displayed())


def test_feature_disabled_context_fallback_explains_offline_lookup(driver, wait, base_url):
    driver.set_window_size(1440, 1000)
    HomePage(driver, wait, base_url).open().wait_loaded()
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.emulateNetworkConditions", {
            "offline": True,
            "latency": 0,
            "downloadThroughput": 0,
            "uploadThroughput": 0,
        })
    except Exception as exc:
        pytest.skip(f"Browser does not support offline network emulation: {exc}")

    try:
        driver.execute_script("window.BHFCompanionContext.clear();")
        driver.find_element(
            By.CSS_SELECTOR,
            '#chapter-reader .reader-pane.is-active [data-verse="2"] [data-verse-select]',
        ).click()
        wait.until(lambda _driver: _driver.execute_script(
            "return window.BHFStudySelection.getState().selectedVerses.includes(2);"
        ))
        wait.until(lambda _driver: _driver.execute_script(
            "return window.BHFStudyCompanion.getContextRecord()?.status === 'error';"
        ))
        driver.find_element(By.CSS_SELECTOR, '[data-companion-resource="understand_passage"]').click()
        status = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".companion-context-topic-status")))
        assert "unavailable offline" in status.text.casefold()
        assert driver.find_element(By.CSS_SELECTOR, ".companion-browse-research").is_displayed()
    finally:
        driver.execute_cdp_cmd("Network.emulateNetworkConditions", {
            "offline": False,
            "latency": 0,
            "downloadThroughput": -1,
            "uploadThroughput": -1,
        })
