from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import _context_identity, _route_article, _select_verses


def _tab_until(driver, predicate, limit=120):
    for _ in range(limit):
        element = driver.switch_to.active_element
        if predicate(element):
            return element
        element.send_keys(Keys.TAB)
    raise AssertionError("target was not reached by keyboard Tab")


def test_keyboard_discovery_route_focus_and_escape(driver, base_url):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "Jonah", 1, [17])
    wait.until(lambda b: _context_identity(b, "jonah-three-days")["cited"])
    wait.until(lambda b: b.find_elements(By.CSS_SELECTOR, "[data-presentation-action='explore_connection']"))
    summary = _tab_until(driver, lambda e: e.tag_name == "summary" and e.find_elements(By.XPATH, "ancestor::article[contains(@class,'companion-discovery-card')]//*[@data-presentation-action='explore_connection']"))
    summary.send_keys(Keys.SPACE)
    wait.until(lambda b: b.find_elements(By.CSS_SELECTOR, "[data-presentation-action='explore_connection']"))
    action = _tab_until(driver, lambda e: e.get_attribute("data-presentation-action") == "explore_connection")
    assert action.get_attribute("aria-label") == "Explore this connection"
    action.send_keys(Keys.ENTER)
    _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
    wait.until(lambda b: b.execute_script("return document.activeElement?.dataset?.narrativeRouteFocusId === 'jonah-1-17-matthew-12-40-sign-of-jonah'"))
    assert driver.find_elements(By.CSS_SELECTOR, '[role="status"][aria-live]')
    driver.switch_to.active_element.send_keys(Keys.ESCAPE)
    wait.until(lambda b: b.execute_script("return window.BHFStudyCompanion.getState().resource === null"))
    assert driver.execute_script("return document.activeElement?.dataset?.presentationAction === 'explore_connection'")
