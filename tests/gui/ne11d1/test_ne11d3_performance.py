import json
import pytest
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import (
    _click_related_passage, _connection_action, _context_identity,
    _return_to_origin, _route_article, _select_verses,
)


@pytest.mark.parametrize(("book", "chapter", "verses", "object_id", "record_id", "route_id", "destination", "reset_book"), [
    ("Genesis", 1, [1, 2, 3, 4, 5], "john", "john-logos", "genesis-1-john-1-creation-word", "John 1:1-5", "Matthew"),
    ("Matthew", 12, [40], "jonah", "jonah-three-days", "jonah-1-17-matthew-12-40-sign-of-jonah", "Jonah 1:17", "Genesis"),
])
def test_other_repeated_journey_timings(driver, base_url, book, chapter, verses, object_id, record_id, route_id, destination, reset_book):
    _sample_journey(driver, base_url, book, chapter, verses, object_id, record_id, route_id, destination, reset_book)


def test_jonah_repeated_journey_timings(driver, base_url):
    _sample_journey(driver, base_url, "Jonah", 1, [17], "jonah", "jonah-three-days", "jonah-1-17-matthew-12-40-sign-of-jonah", "Matthew 12:40", "Genesis")


def _sample_journey(driver, base_url, book, chapter, verses, object_id, record_id, route_id, destination, reset_book):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    identity = {"object_id": object_id, "record_kind": "claim", "record_id": record_id}
    samples = []
    for index in range(3):
        HomePage(driver, wait, base_url).open().wait_loaded()
        Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value(reset_book)
        wait.until(lambda b: b.execute_script("return window.BHFStudySelection?.getState?.().book === arguments[0]", reset_book))
        _select_verses(driver, wait, book, chapter, verses)
        wait.until(lambda b: _context_identity(b, record_id)["cited"])
        _, action = wait.until(lambda b: _connection_action(b, identity))
        started = time.monotonic()
        action.click()
        article = _route_article(driver, wait, route_id)
        wait.until(lambda b: b.execute_script("return document.activeElement?.dataset?.narrativeRouteFocusId === arguments[0]", route_id))
        focus_ms = (time.monotonic() - started) * 1000
        started = time.monotonic()
        _click_related_passage(driver, wait, article, destination)
        navigation_ms = (time.monotonic() - started) * 1000
        _return_to_origin(driver, wait, f"{book} {chapter}:{verses[0]}" + (f"-{verses[-1]}" if len(verses) > 1 else ""), verses)
        entries = driver.execute_script("""
          return performance.getEntriesByType('resource').filter(e =>
            e.name.includes('/api/study/companion-context') || e.name.includes('/api/narrative-explorer/v1/passages/')
          ).map(e => ({kind: e.name.includes('companion-context') ? 'companion' : 'projection',
                       name: e.name, duration: e.duration, transfer: e.transferSize, encoded: e.encodedBodySize}));
        """)
        samples.append({"sample": index + 1, "action_to_route_ms": round(focus_ms, 1),
                        "destination_ms": round(navigation_ms, 1), "entries": entries})
        print(f"NE11D3_{book.upper()}_SAMPLE=" + json.dumps(samples[-1], sort_keys=True), flush=True)
    print(f"NE11D3_{book.upper()}_SAMPLES=" + json.dumps(samples, sort_keys=True))
