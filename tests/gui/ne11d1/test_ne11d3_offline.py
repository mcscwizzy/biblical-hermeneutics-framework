from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import _connection_action, _context_identity, _route_article, _select_verses


def test_offline_failure_cached_reading_and_recovery(driver, base_url):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="translation-select"]')).select_by_value("kjv")
    _select_verses(driver, wait, "Jonah", 1, [17])
    wait.until(lambda b: _context_identity(b, "jonah-three-days")["cited"])
    identity = {"object_id": "jonah", "record_kind": "claim", "record_id": "jonah-three-days"}
    _, action = wait.until(lambda b: _connection_action(b, identity))
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.emulateNetworkConditions", {"offline": True, "latency": 0, "downloadThroughput": 0, "uploadThroughput": 0})
    try:
        action.click()
        wait.until(lambda b: b.execute_script("return window.BHFStudyCompanion.getState().resource === 'cross_references'"))
        assert not driver.find_elements(By.CSS_SELECTOR, '[data-route-id="jonah-1-17-matthew-12-40-sign-of-jonah"][aria-current="true"]')
        Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("2")
        wait.until(lambda b: b.execute_script("return window.BHFStudySelection?.getState?.().chapter === 2"))
        wait.until(lambda b: "prayed" in b.find_element(By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active [data-verse="1"]').text.lower())
    finally:
        driver.execute_cdp_cmd("Network.emulateNetworkConditions", {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1})
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "Jonah", 1, [17])
    wait.until(lambda b: _context_identity(b, "jonah-three-days")["cited"])
    _, action = wait.until(lambda b: _connection_action(b, identity))
    action.click()
    _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
