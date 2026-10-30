from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import _select_verses, _render_real_projection, _return_to_origin


def test_narrative_explorer_discovery_and_focused_category_history(driver, base_url, artifacts_dir):
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value("Genesis")
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("1")
    wait.until(lambda b: b.execute_script("return window.BHFStudySelection?.getState?.().reference === 'Genesis 1'"))
    driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()

    explorer = wait.until(lambda b: b.find_element(By.CSS_SELECTOR, ".narrative-explorer"))
    cards = explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-category-card")
    assert len(cards) == 6
    assert not explorer.find_elements(By.CSS_SELECTOR, "article.narrative-explorer-item")
    assert "Current passage: Genesis 1" in explorer.text
    assert "Follow a Connection" in explorer.text
    assert driver.save_screenshot(str(artifacts_dir / "ui03-discovery-desktop.png"))

    explorer.find_element(By.CSS_SELECTOR, '[data-section-id="themes_biblical_connections"]').click()
    wait.until(lambda b: b.find_element(By.CSS_SELECTOR, ".narrative-explorer-header h3").text == "Themes & Biblical Connections")
    assert driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-category-controls").is_displayed()
    assert driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-related-passages").is_displayed()
    assert driver.save_screenshot(str(artifacts_dir / "ui03-connections-desktop.png"))

    driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-back-topics").click()
    wait.until(lambda b: b.find_elements(By.CSS_SELECTOR, ".narrative-explorer-topic-choices"))
    driver.forward()
    wait.until(lambda b: b.find_element(By.CSS_SELECTOR, ".narrative-explorer-header h3").text == "Themes & Biblical Connections")
    driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-return-passage").click()
    wait.until(lambda b: b.find_elements(By.CSS_SELECTOR, ".narrative-explorer-topic-choices"))
    assert driver.execute_script("return window.BHFStudySelection?.getState?.().reference") == "Genesis 1"

    driver.set_window_size(390, 844)
    wait.until(lambda b: b.execute_script("return window.innerWidth === 390"))
    explorer = wait.until(lambda b: b.find_element(By.CSS_SELECTOR, ".narrative-explorer"))
    cards = explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-category-card")
    assert len(cards) == 6
    assert driver.execute_script("return document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    assert driver.save_screenshot(str(artifacts_dir / "ui03-discovery-mobile.png"))


def test_exodus_geography_and_cosmic_categories_keep_distinct_availability(driver, base_url):
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "Exodus", 3, [2])
    wait.until(lambda b: b.execute_script(
        "return window.BHFStudyCompanion?.getContext?.()?.reference === 'Exodus 3:2'"
    ))
    driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()
    explorer = wait.until(lambda b: b.find_element(By.CSS_SELECTOR, ".narrative-explorer"))
    assert len(explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-category-card")) == 6
    assert "Current passage: Exodus 3:2" in explorer.text

    explorer.find_element(By.CSS_SELECTOR, '[data-section-id="biblical_geography"]').click()
    geography = wait.until(lambda b:b.find_element(
        By.CSS_SELECTOR,
        ".narrative-explorer-section[data-section-id='biblical_geography']",
    ))
    assert "Biblical Geography" in driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-header h3").text
    assert geography.find_elements(By.CSS_SELECTOR, ".narrative-explorer-previews article")

    driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-back-topics").click()
    explorer = wait.until(lambda b:b.find_element(By.CSS_SELECTOR, ".narrative-explorer-topic-choices"))
    cosmic_card = explorer.find_element(By.CSS_SELECTOR, '[data-section-id="divine_council_cosmic_geography"]')
    assert "Availability could not be checked" in cosmic_card.text
    cosmic_card.click()
    cosmic = wait.until(lambda b:b.find_element(
        By.CSS_SELECTOR,
        ".narrative-explorer-section[data-section-id='divine_council_cosmic_geography']",
    ))
    assert "Availability could not be checked" in cosmic.text
    assert not cosmic.find_elements(By.CSS_SELECTOR, ".narrative-explorer-item-action")
    assert "Open map" not in cosmic.text
    assert not any(token in cosmic.text.lower() for token in ("latitude", "longitude", "coordinates"))

    driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-return-passage").click()
    wait.until(lambda b: b.find_elements(By.CSS_SELECTOR, ".narrative-explorer-category-card"))
    assert driver.execute_script("return window.BHFStudySelection?.getState?.().reference") == "Exodus 3:2"


def test_acts_authored_psalm_route_and_return(driver, base_url):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "Acts", 2, [34, 35])
    wait.until(lambda b: b.execute_script("return window.BHFStudyCompanion?.getContext?.()?.reference === 'Acts 2:34-35'"))
    result = _render_real_projection(driver)
    assert result["queryStatus"] == "complete", result
    assert "psalm-110-acts-2-enthronement" not in result["bridgeRoutes"]
    assert len(result["authoredRoutes"]) >= 2, result
    assert result["matches"] == [] and result["actionCount"] == 0, result
    driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()
    wait.until(lambda b: b.find_elements(By.CSS_SELECTOR, ".narrative-explorer-category-card"))
    driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-follow-connection").click()
    article = wait.until(lambda b: next((a for a in b.find_elements(By.CSS_SELECTOR, '.narrative-explorer-related-passage') if 'Psalm 110' in a.text), False))
    details = article.find_element(By.CSS_SELECTOR, ".narrative-explorer-related-passage-details")
    driver.execute_script("arguments[0].open = true;", details)
    detail_text = details.text
    assert "authored CKL relationship" in detail_text
    assert "ckl:messiah-theme#source:luke-24" in detail_text
    assert "ckl:messiah-theme#source:psalm-110" in detail_text
    assert "ckl:resurrection-theme#source:1-corinthians-15" in detail_text
    button = article.find_element(By.CSS_SELECTOR, "button[data-narrative-focus-id^='related-passage:']")
    button.click()
    wait.until(lambda b: b.execute_script("return window.BHFStudySelection?.getState?.().book === 'Psalms' && window.BHFStudySelection?.getState?.().chapter === 110"))
    driver.back()
    wait.until(lambda b: b.execute_script("return window.BHFStudySelection?.getState?.().reference === 'Acts 2:34-35'"))
    driver.forward()
    wait.until(lambda b: b.execute_script("return window.BHFStudySelection?.getState?.().book === 'Psalms' && window.BHFStudySelection?.getState?.().chapter === 110"))
    _return_to_origin(driver, wait, "Acts 2:34-35", [34, 35])


def test_psalm_22_generic_cross_references_do_not_promote_held_bridge(driver, base_url):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "Psalms", 22, [1])
    wait.until(lambda b: b.execute_script("return window.BHFStudyCompanion?.getContext?.()?.reference === 'Psalms 22:1'"))
    result = _render_real_projection(driver)
    assert result["queryStatus"] == "complete"
    assert result["bridgeRoutes"] == [] and result["matches"] == [] and result["actionCount"] == 0
    button = wait.until(lambda b: b.find_element(By.CSS_SELECTOR, '[data-companion-resource="cross_references"]'))
    button.click()
    body = wait.until(lambda b: b.find_element(By.CSS_SELECTOR, '.companion-detail-body'))
    assert "Cross References" in body.text
    assert not driver.find_elements(By.CSS_SELECTOR, '[data-route-id="psalm-22-mark-15"]')


def test_real_jonah_verification_interrupted_by_chapter_change(driver, base_url):
    from selenium.webdriver.support.ui import Select
    from tests.gui.ne11d1.test_real_ckl_handoff import _connection_action, _context_identity

    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "Jonah", 1, [17])
    wait.until(lambda b: _context_identity(b, "jonah-three-days")["cited"])
    identity = {"object_id": "jonah", "record_kind": "claim", "record_id": "jonah-three-days"}
    _, action = wait.until(lambda b: _connection_action(b, identity))
    driver.execute_script("""
      const original = window.fetch;
      window.ne11d3Release = null;
      window.ne11d3RequestOutcomes = [];
      window.fetch = function(input, options) {
        const request = original.call(this, input, options);
        if (!String(input).includes('/api/narrative-explorer/v1/passages/')) return request;
        const signal = options?.signal;
        const outcome = {status: null, bodyBytes: null, abortObserved: false, released: false};
        window.ne11d3RequestOutcomes.push(outcome);
        signal?.addEventListener('abort', () => { outcome.abortObserved = true; }, {once: true});
        return request.then(async response => {
          outcome.status = response.status;
          outcome.bodyBytes = (await response.clone().arrayBuffer()).byteLength;
          return new Promise(resolve => {
            window.ne11d3Release = () => { outcome.released = true; resolve(response); };
          });
        });
      };
    """)
    action.click()
    wait.until(lambda b: b.execute_script("return window.ne11d3Release !== null"))
    outcome = driver.execute_script("return window.ne11d3RequestOutcomes[0]")
    assert outcome and outcome["status"] == 200 and outcome["bodyBytes"] > 0, outcome
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("2")
    wait.until(lambda b: b.execute_script("return window.BHFStudySelection?.getState?.().chapter === 2"))
    outcome = driver.execute_script("return window.ne11d3RequestOutcomes[0]")
    assert outcome["abortObserved"] is True, outcome
    driver.execute_script("window.ne11d3Release();")
    wait.until(lambda b: b.execute_script("return window.BHFStudyCompanion?.getContext?.()?.reference === 'Jonah 2'"))
    assert not driver.find_elements(By.CSS_SELECTOR, '[data-route-id="jonah-1-17-matthew-12-40-sign-of-jonah"][aria-current="true"]')
    assert driver.execute_script("return window.history.state?.bhfStudyCompanion?.trail || null") is None
    outcome = driver.execute_script("return window.ne11d3RequestOutcomes[0]")
    assert outcome["released"] is True and outcome["abortObserved"] is True, outcome
    print("NE11D4_CANCELLED_ACTIVATION=" + str(outcome), flush=True)
