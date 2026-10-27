from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import (
    _select_verses, _context_identity, _connection_action, _route_article,
    _click_related_passage, _return_to_origin,
)


def test_fresh_matthew_handoff(driver, base_url):
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "Matthew", 12, [40])
    identity = {"object_id": "jonah", "record_kind": "claim", "record_id": "jonah-three-days"}
    wait.until(lambda browser: _context_identity(browser, "jonah-three-days")["cited"])
    _, action = wait.until(lambda browser: _connection_action(browser, identity))
    action.click()
    article = _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
    assert "Jonah 1:17 → Matthew 12:40" in article.text
    _click_related_passage(driver, wait, article, "Jonah 1:17")
    _return_to_origin(driver, wait, "Matthew 12:40", [40])


def test_mobile_viewport_measurement(driver, base_url):
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True,
    })
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value("Jonah")
    wait.until(lambda b: b.execute_script("return window.BHFStudySelection?.getState?.().book === 'Jonah'"))
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("1")
    verse = wait.until(lambda b: b.find_element(By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active [data-verse="17"] [data-verse-select]'))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", verse)
    verse.click()
    wait.until(lambda b: _context_identity(b, "jonah-three-days")["cited"])
    metrics = driver.execute_script("return {inner: innerWidth, client: document.documentElement.clientWidth, dpr: devicePixelRatio, scroll: document.documentElement.scrollWidth}")
    print("NE11D2 mobile metrics", metrics)
    assert metrics["client"] == 390
    assert metrics["scroll"] <= metrics["client"]
    assert driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
