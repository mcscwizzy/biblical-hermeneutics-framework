import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import (
    _click_related_passage, _connection_action, _context_identity,
    _return_to_origin, _route_article,
)


def test_jonah_mobile_handoff_and_return(driver, base_url):
    _journey(driver, base_url, 390, True)


@pytest.mark.parametrize(("width", "mobile"), [(320, True), (768, False), (1440, False)])
def test_jonah_handoff_other_viewports(driver, base_url, width, mobile):
    _journey(driver, base_url, width, mobile)


def _journey(driver, base_url, width, mobile):
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
    identity = {"object_id": "jonah", "record_kind": "claim", "record_id": "jonah-three-days"}
    card, action = wait.until(lambda b: _connection_action(b, identity))
    assert card.is_displayed()
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", action)
    action.click()
    article = _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
    assert "Jonah 1:17 → Matthew 12:40" in article.text
    details = article.find_element(By.CSS_SELECTOR, ".narrative-explorer-related-passage-details")
    driver.execute_script("arguments[0].open = true;", details)
    assert "jonah-masoretic" in details.text
    assert "chronology" in details.text.lower()
    metrics = driver.execute_script("return {width: innerWidth, client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth}")
    assert metrics["width"] == width
    assert metrics["scroll"] <= metrics["client"]
    button = article.find_element(By.CSS_SELECTOR, "button[data-narrative-focus-id^='related-passage:']")
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
    _click_related_passage(driver, wait, article, "Matthew 12:40")
    _return_to_origin(driver, wait, "Jonah 1:17", [17])
    if width < 800:
        close = driver.find_element(By.CSS_SELECTOR, '[data-companion-state-control="closed"]')
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", close)
        close.click()
        assert driver.execute_script("return window.BHFStudyCompanion.getState().state") == "closed"
