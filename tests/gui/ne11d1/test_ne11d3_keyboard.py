from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import pytest
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.viewport import set_viewport
from tests.gui.ne11d1.test_real_ckl_handoff import _context_identity, _route_article


def _tab_until(driver, predicate, limit=120):
    for _ in range(limit):
        element = driver.switch_to.active_element
        if predicate(element):
            return element
        element.send_keys(Keys.TAB)
    raise AssertionError("target was not reached by keyboard Tab")


def _wait_for_sheet_transition(driver, wait):
    wait.until(lambda browser: browser.execute_script(
        """
        const panel = document.querySelector('[data-study-companion]');
        return panel && panel.getAnimations().every(animation => animation.playState !== 'running');
        """
    ))


@pytest.mark.parametrize(("width", "mobile"), [(320, True), (390, True), (768, False), (1440, False)])
def test_keyboard_discovery_route_focus_and_escape(driver, base_url, width, mobile):
    set_viewport(driver, width, 844, mobile)
    wait = WebDriverWait(driver, 90)
    page = HomePage(driver, wait, base_url).open().wait_loaded()
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
        page.click('.companion-peek[data-companion-state-control="study"]')
        wait.until(lambda browser: peek.get_attribute("aria-expanded") == "true")
        _wait_for_sheet_transition(driver, wait)
    wait.until(lambda b: _context_identity(b, "jonah-three-days")["cited"])
    entry = driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]')
    if width <= 900:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", entry)
    entry.click()
    follow = wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR,
        ".narrative-explorer-follow-connection",
    ))
    wait.until(lambda browser: follow.is_displayed() and follow.is_enabled())
    follow = _tab_until(driver, lambda element: "narrative-explorer-follow-connection" in (element.get_attribute("class") or ""))
    follow_name = follow.get_attribute("aria-label")
    assert follow_name == "Follow a Connection from Jonah 1:17", follow_name

    ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()
    wait.until(lambda b: b.execute_script(
        "return document.activeElement !== arguments[0] "
        "&& ['SUMMARY', 'BUTTON', 'A', 'INPUT'].includes(document.activeElement?.tagName) "
        "&& document.activeElement?.getClientRects().length > 0;",
        follow,
    ))
    driver.switch_to.active_element.send_keys(Keys.TAB)
    wait.until(lambda b: b.execute_script(
        "return document.activeElement?.classList?.contains('narrative-explorer-follow-connection') === true;"
    ))
    follow = driver.switch_to.active_element
    follow.send_keys(Keys.SPACE)
    wait.until(lambda b: b.find_element(
        By.CSS_SELECTOR,
        ".narrative-explorer-header h3",
    ).text == "Themes & Biblical Connections")
    route_id = "jonah-1-17-matthew-12-40-sign-of-jonah"
    route_button = wait.until(lambda browser: next((button for button in browser.find_elements(
        By.CSS_SELECTOR,
        "button[data-narrative-focus-id^='related-passage:']",
    ) if button.get_attribute("data-narrative-focus-id") == f"related-passage:{route_id}"), False))
    route_name = route_button.get_attribute("aria-label") or route_button.text.strip()
    assert route_name == "Open related passage: Matthew 12:40", route_name
    route_button = _tab_until(
        driver,
        lambda element: element.get_attribute("data-narrative-focus-id") == f"related-passage:{route_id}",
    )
    route_button.send_keys(Keys.ENTER)
    wait.until(lambda b: b.execute_script(
        "return window.BHFStudySelection?.getState?.().reference === 'Matthew 12:40';"
    ))
    article = _route_article(driver, wait, route_id)
    wait.until(lambda b: b.execute_script(
        "return document.activeElement?.dataset?.narrativeRouteFocusId === arguments[0];",
        route_id,
    ))
    accessibility = driver.execute_script(
        """
        const explorer = document.querySelector("[data-companion-resource-host] .narrative-explorer");
        const live = document.querySelector("[data-passage-action-reference]");
        const routeHeading = arguments[0].querySelector("[data-narrative-route-focus-id]");
        return {
          headings: [...explorer.querySelectorAll("h1,h2,h3,h4,h5,h6")].map(node => ({tag: node.tagName, text: node.textContent.trim()})),
          routeName: routeHeading?.textContent.trim() || "",
          liveRole: live?.getAttribute("role") || "",
          liveMode: live?.getAttribute("aria-live") || "",
          liveText: live?.textContent.trim() || "",
        };
        """,
        article,
    )
    assert {"tag": "H3", "text": "Themes & Biblical Connections"} in accessibility["headings"], accessibility
    assert {"tag": "H4", "text": "Related Biblical Passages"} in accessibility["headings"], accessibility
    assert accessibility["routeName"] == "Connection to Jonah 1:17", accessibility
    assert accessibility["liveMode"] == "polite", accessibility
    assert accessibility["liveText"] == "Matthew 12:40", accessibility

    driver.switch_to.active_element.send_keys(Keys.ESCAPE)
    wait.until(lambda b: b.execute_script(
        "const state = window.BHFStudyCompanion.getState(); "
        "return state.resource === 'narrative_explorer' "
        "&& window.history.state?.bhfStudyCompanion?.narrativeView?.kind === 'category' "
        "&& window.BHFStudySelection?.getState?.().reference === 'Jonah 1:17';"
    ))
    wait.until(lambda browser: browser.execute_script(
        "return document.activeElement?.dataset?.narrativePrimary === 'true';"
    ))
    driver.switch_to.active_element.send_keys(Keys.ESCAPE)
    wait.until(lambda b: b.execute_script(
        "return window.BHFStudyCompanion.getState().resource === 'narrative_explorer' "
        "&& window.history.state?.bhfStudyCompanion?.narrativeView?.kind === 'overview';"
    ))
    wait.until(lambda browser: browser.execute_script(
        "return document.activeElement?.dataset?.narrativePrimary === 'true';"
    ))
    driver.switch_to.active_element.send_keys(Keys.ESCAPE)
    wait.until(lambda b: b.execute_script(
        "return window.BHFStudyCompanion.getState().resource === null;"
    ))
    wait.until(lambda browser: browser.execute_script(
        "return document.activeElement?.getAttribute('data-testid') === 'companion-narrative-explorer';"
    ))
