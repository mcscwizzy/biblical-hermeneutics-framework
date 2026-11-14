from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.viewport import set_viewport
from tests.gui.ne11d1.test_real_ckl_handoff import (
    _select_verses, _context_identity, _open_follow_connection, _route_article,
    _click_related_passage, _return_to_origin,
)


def test_fresh_matthew_handoff(driver, base_url):
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "Matthew", 12, [40])
    identity = {"object_id": "jonah", "record_kind": "claim", "record_id": "jonah-three-days"}
    evidence = wait.until(lambda browser: _context_identity(browser, "jonah-three-days")
        if _context_identity(browser, "jonah-three-days")["cited"] else False)
    assert evidence["reference"] == "Matthew 12:40"
    assert evidence["identity"] == identity
    assert "later becomes important in Matthew 12:40" in evidence["claim"]
    assert {"jonah-masoretic", "jonah-new-testament"} <= set(evidence["sourceIds"])

    _open_follow_connection(driver, wait)
    article = _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
    assert "Jonah 1:17 → Matthew 12:40" in article.text
    _click_related_passage(driver, wait, article, "Jonah 1:17")
    trail = driver.execute_script("return window.history.state?.bhfStudyCompanion?.trail || null;")
    assert trail is not None and trail["activeIndex"] > 0
    assert {"Jonah 1:17", "Matthew 12:40"} <= {
        node.get("reference") for node in trail.get("nodes", [])
    }
    returned = _return_to_origin(driver, wait, "Matthew 12:40", [40])
    assert {"Jonah 1:17", "Matthew 12:40"} <= {
        node.get("reference") for node in returned.get("nodes", [])
    }


def test_mobile_viewport_measurement(driver, base_url):
    set_viewport(driver, 390, 844, mobile=True)
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
