from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import _select_verses, _render_real_projection, _return_to_origin


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
    article = wait.until(lambda b: next((a for a in b.find_elements(By.CSS_SELECTOR, '.narrative-explorer-related-passage') if 'Psalm 110' in a.text), False))
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
