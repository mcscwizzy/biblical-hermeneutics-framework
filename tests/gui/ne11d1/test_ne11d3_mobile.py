import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import (
    _click_related_passage, _connection_action, _context_identity,
    _return_to_origin, _route_article,
)


def test_jonah_mobile_handoff_and_return(driver, base_url, artifacts_dir):
    _journey(driver, base_url, 390, True, artifacts_dir)


@pytest.mark.parametrize(("width", "mobile"), [(320, True), (768, False), (1440, False)])
def test_jonah_handoff_other_viewports(driver, base_url, width, mobile, artifacts_dir):
    _journey(driver, base_url, width, mobile, artifacts_dir)


def _journey(driver, base_url, width, mobile, artifacts_dir):
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": width, "height": 844, "deviceScaleFactor": 1, "mobile": mobile,
    })
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value("Jonah")
    wait.until(lambda b: b.execute_script("return window.BHFStudySelection?.getState?.().book === 'Jonah'"))
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("1")
    verse = wait.until(lambda b: b.find_element(By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active [data-verse="17"] [data-verse-select]'))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", verse)
    verse.click()
    peek = driver.find_element(By.CSS_SELECTOR, '.companion-peek[data-companion-state-control="study"]')
    if peek.is_displayed():
        peek.click()
    wait.until(lambda b: _context_identity(b, "jonah-three-days")["cited"])
    action_layout = driver.execute_script(
        """
        const row = document.querySelector(".companion-overview-actions");
        const bounds = row.getBoundingClientRect();
        const style = getComputedStyle(row);
        return {width: bounds.width, clientWidth: row.clientWidth, scrollWidth: row.scrollWidth,
          overflowX: style.overflowX,
          buttons: [...row.querySelectorAll("button")].map(button => {
            const rect = button.getBoundingClientRect();
            return {name: button.textContent.trim(), left: rect.left, right: rect.right,
              clippedByRow: rect.left < bounds.left || rect.right > bounds.right,
              textWidth: button.scrollWidth, textClientWidth: button.clientWidth,
              textClipped: button.scrollWidth > button.clientWidth + 1};
          })};
        """
    )
    print(f"NE11D4_COMPANION_ACTION_LAYOUT_{width}={action_layout}", flush=True)
    identity = {"object_id": "jonah", "record_kind": "claim", "record_id": "jonah-three-days"}
    card, action = wait.until(lambda b: _connection_action(b, identity))
    assert card.is_displayed()
    discovery_readability = _clipping_report(driver, card)
    assert discovery_readability["widths"][0] > 0, discovery_readability
    assert discovery_readability["clipped"] == [], discovery_readability
    assert driver.save_screenshot(str(artifacts_dir / f"ne11d4-discovery-{width}.png"))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", action)
    action.click()
    article = _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
    assert "Jonah 1:17 → Matthew 12:40" in article.text
    details = article.find_element(By.CSS_SELECTOR, ".narrative-explorer-related-passage-details")
    driver.execute_script("arguments[0].open = true;", details)
    assert "jonah-masoretic" in details.text
    assert "chronology" in details.text.lower()
    route_readability = _clipping_report(driver, article)
    assert route_readability["widths"][0] > 0, route_readability
    assert route_readability["clipped"] == [], route_readability
    metrics = driver.execute_script("return {width: innerWidth, client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth}")
    assert metrics["width"] == width
    assert metrics["scroll"] <= metrics["client"]
    assert driver.save_screenshot(str(artifacts_dir / f"ne11d4-route-{width}.png"))
    button = article.find_element(By.CSS_SELECTOR, "button[data-narrative-focus-id^='related-passage:']")
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
    _click_related_passage(driver, wait, article, "Matthew 12:40")
    _return_to_origin(driver, wait, "Jonah 1:17", [17])
    if width < 800:
        close = driver.find_element(By.CSS_SELECTOR, '[data-companion-state-control="closed"]')
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", close)
        close.click()
        assert driver.execute_script("return window.BHFStudyCompanion.getState().state") == "closed"


def _clipping_report(driver, *roots):
    return driver.execute_script(
        """
        const roots = arguments[0];
        const clipped = [];
        const widths = [];
        for (const root of roots) {
          widths.push(root.getBoundingClientRect().width);
          const candidates = [root, ...root.querySelectorAll("h1,h2,h3,h4,h5,h6,p,summary,button,li,dt,dd")];
          for (const element of candidates) {
            if (!element.getClientRects().length || !element.textContent.trim()) continue;
            const style = getComputedStyle(element);
            const horizontal = element.clientWidth > 0 && element.scrollWidth > element.clientWidth + 1;
            const vertical = ["hidden", "clip"].includes(style.overflowY)
              && element.scrollHeight > element.clientHeight + 1;
            const clamped = Number.parseInt(style.webkitLineClamp || "0", 10) > 0
              && element.scrollHeight > element.clientHeight + 1;
            if (horizontal || vertical || clamped) {
              clipped.push({tag: element.tagName, text: element.textContent.trim().slice(0, 100),
                horizontal, vertical, clamped, overflowX: style.overflowX, overflowY: style.overflowY});
            }
          }
        }
        return {widths, clipped};
        """,
        list(roots),
    )
