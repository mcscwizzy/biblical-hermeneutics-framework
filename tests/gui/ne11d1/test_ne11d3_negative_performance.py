import json
import pytest
from selenium.webdriver.support.ui import WebDriverWait
from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import _render_real_projection, _select_verses


@pytest.mark.parametrize(("book", "chapter", "verse", "reference"), [
    ("Psalms", 22, 1, "Psalms 22:1"),
    ("Psalms", 119, 176, "Psalms 119:176"),
])
def test_negative_projection_measurement(driver, base_url, book, chapter, verse, reference):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, book, chapter, [verse])
    wait.until(lambda b: b.execute_script("return window.BHFStudyCompanion?.getContext?.()?.reference === arguments[0]", reference))
    result = _render_real_projection(driver)
    assert result["queryStatus"] == "complete"
    assert result["matches"] == [] and result["actionCount"] == 0
    entries = driver.execute_script("""return performance.getEntriesByType('resource').filter(e =>
      e.name.includes('/api/study/companion-context') || e.name.includes('/api/narrative-explorer/v1/passages/'))
      .map(e => ({name: e.name, duration: e.duration, encoded: e.encodedBodySize, transfer: e.transferSize}));""")
    items = driver.execute_async_script("""const done = arguments[0];
      window.BHFNarrativeExplorer.load(window.BHFStudySelection.getState())
        .then(p => done(p.items.length)).catch(e => done({error: String(e)}));""")
    print("NE11D3_NEGATIVE=" + json.dumps({"reference": reference, "result": result, "items": items, "entries": entries}), flush=True)
