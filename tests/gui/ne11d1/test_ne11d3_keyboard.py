from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pytest
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import _context_identity, _route_article


def _tab_until(driver, predicate, limit=120):
    for _ in range(limit):
        element = driver.switch_to.active_element
        if predicate(element):
            return element
        element.send_keys(Keys.TAB)
    raise AssertionError("target was not reached by keyboard Tab")


@pytest.mark.parametrize(("width", "mobile"), [(320, True), (390, True), (768, False), (1440, False)])
def test_keyboard_discovery_route_focus_and_escape(driver, base_url, width, mobile):
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": width, "height": 844, "deviceScaleFactor": 1, "mobile": mobile,
    })
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value("Jonah")
    wait.until(lambda browser: browser.execute_script("return window.BHFStudySelection?.getState?.().book === 'Jonah'"))
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("1")
    verse = wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active [data-verse="17"] [data-verse-select]'
    ))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", verse)
    verse.click()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection?.getState?.().reference === 'Jonah 1:17'"
    ))
    peek = driver.find_element(By.CSS_SELECTOR, '.companion-peek[data-companion-state-control="study"]')
    if peek.is_displayed():
        peek.click()
    wait.until(lambda b: _context_identity(b, "jonah-three-days")["cited"])
    wait.until(lambda b: b.find_elements(By.CSS_SELECTOR, "[data-presentation-action='explore_connection']"))
    summary = _tab_until(driver, lambda e: e.tag_name == "summary" and e.find_elements(By.XPATH, "ancestor::article[contains(@class,'companion-discovery-card')]//*[@data-presentation-action='explore_connection']"))
    summary.send_keys(Keys.SPACE)
    wait.until(lambda b: b.find_elements(By.CSS_SELECTOR, "[data-presentation-action='explore_connection']"))
    action = _tab_until(driver, lambda e: e.get_attribute("data-presentation-action") == "explore_connection")
    assert action.get_attribute("aria-label") == "Explore this connection"
    action.send_keys(Keys.ENTER)
    article = _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
    wait.until(lambda b: b.execute_script("return document.activeElement?.dataset?.narrativeRouteFocusId === 'jonah-1-17-matthew-12-40-sign-of-jonah'"))
    accessibility = driver.execute_script(
        """
        const explorer = document.querySelector("[data-companion-resource-host] .narrative-explorer");
        const live = document.querySelector("[data-passage-action-reference]");
        const routeButton = arguments[0].querySelector("button[data-narrative-focus-id^='related-passage:']");
        return {
          headings: [...explorer.querySelectorAll("h1,h2,h3,h4,h5,h6")].map(node => ({tag: node.tagName, text: node.textContent.trim()})),
          actionName: document.querySelector("[data-presentation-action='explore_connection']")?.getAttribute("aria-label") || "",
          routeName: routeButton?.getAttribute("aria-label") || routeButton?.textContent.trim() || "",
          liveRole: live?.getAttribute("role") || "",
          liveMode: live?.getAttribute("aria-live") || "",
          liveText: live?.textContent.trim() || "",
        };
        """,
        article,
    )
    assert {"tag": "H3", "text": "Narrative evidence and connections"} in accessibility["headings"], accessibility
    assert {"tag": "H4", "text": "Related Biblical Passages"} in accessibility["headings"], accessibility
    assert accessibility["actionName"] == "Explore this connection", accessibility
    assert accessibility["routeName"] == "Open related passage: Matthew 12:40", accessibility
    assert accessibility["liveMode"] == "polite", accessibility
    assert accessibility["liveText"] == "Jonah 1:17", accessibility
    driver.switch_to.active_element.send_keys(Keys.ESCAPE)
    wait.until(lambda b: b.execute_script("return window.BHFStudyCompanion.getState().resource === null"))
    assert driver.execute_script("return document.activeElement?.dataset?.presentationAction === 'explore_connection'")
