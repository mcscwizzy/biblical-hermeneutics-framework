from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import (
    _context_identity,
    _open_follow_connection,
    _route_article,
    _select_verses,
)


def test_offline_failure_cached_reading_and_recovery(driver, base_url):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="translation-select"]')).select_by_value("kjv")
    _select_verses(driver, wait, "Jonah", 1, [17])
    wait.until(lambda b: _context_identity(b, "jonah-three-days")["cited"])
    explorer_entry = wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR,
        '[data-testid="companion-narrative-explorer"]',
    ))
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.emulateNetworkConditions", {"offline": True, "latency": 0, "downloadThroughput": 0, "uploadThroughput": 0})
    try:
        explorer_entry.click()
        wait.until(lambda browser: browser.find_element(
            By.CSS_SELECTOR,
            ".narrative-explorer-state h3",
        ).text == "Not available offline")
        assert "No saved Narrative Explorer projection is available for Jonah 1:17" in driver.find_element(
            By.CSS_SELECTOR,
            ".narrative-explorer-state",
        ).text
        assert not driver.find_elements(By.CSS_SELECTOR, '[data-route-id="jonah-1-17-matthew-12-40-sign-of-jonah"][aria-current="true"]')
        Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("2")
        wait.until(lambda b: b.execute_script("return window.BHFStudySelection?.getState?.().chapter === 2"))
        wait.until(lambda b: "prayed" in b.find_element(By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active [data-verse="1"]').text.lower())
    finally:
        driver.execute_cdp_cmd("Network.emulateNetworkConditions", {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1})
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "Jonah", 1, [17])
    wait.until(lambda b: _context_identity(b, "jonah-three-days")["cited"])
    _open_follow_connection(driver, wait)
    _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
