from __future__ import annotations

import json
import time

import pytest
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import (
    _click_related_passage,
    _context_identity,
    _open_follow_connection,
    _route_article,
    _select_verses,
)


pytestmark = [pytest.mark.gui]


def test_controlled_empty_projection_has_no_actions_and_recovers(driver, ne11d1_base_url):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    assert driver.execute_script(
        "return window.BHFRuntimeConfig?.narrativeExplorerEnabled === true;"
    ), "NE-11D1 GUI fixture must serve a feature-enabled app"
    driver.execute_script(
        """
        window.__ne11d4EmptyFixtureCalls = 0;
        const originalFetch = window.fetch;
        window.fetch = async function(input, options) {
          const response = await originalFetch.call(this, input, options);
          const rawUrl = typeof input === "string" ? input : (input?.url || String(input));
          const url = new URL(rawUrl, location.href);
          if (url.pathname === "/api/narrative-explorer/v1/passages/Jonah/1"
              && url.searchParams.get("verse_start") === "17"
              && url.searchParams.get("verse_end") === "17") {
            const projection = await response.json();
            projection.items = [];
            projection.connections = [];
            projection.navigation = [];
            projection.coverage = [];
            projection.sections = (projection.sections || []).map(section => ({
              ...section, state: "not_represented", item_ids: [],
            }));
            projection.related_passages = {
              state: "not_represented",
              query_status: "complete",
              description: "No linked passage routes were found in this controlled empty-response fixture.",
              authored_relationships: [],
              evidence_backed_bridges: [],
            };
            window.__ne11d4EmptyFixtureCalls += 1;
            return new Response(JSON.stringify(projection), {
              status: 200, headers: {"Content-Type": "application/json"},
            });
          }
          return response;
        };
        """
    )

    _select_verses(driver, wait, "Jonah", 1, [17])
    wait.until(lambda browser: _context_identity(browser, "jonah-three-days")["reference"] == "Jonah 1:17")
    driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()
    wait.until(lambda browser: browser.execute_script("return window.__ne11d4EmptyFixtureCalls > 0"))
    wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, ".narrative-explorer"))
    explorer = driver.find_element(By.CSS_SELECTOR, ".narrative-explorer")
    assert "Jonah 1:17" in explorer.text
    assert len(explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-category-card")) == 6
    assert not explorer.find_elements(By.CSS_SELECTOR, "article.narrative-explorer-item")
    assert not explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-related-passage")
    explorer.find_element(By.CSS_SELECTOR, '[data-section-id="themes_biblical_connections"]').click()
    wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, ".narrative-explorer-related-passages"))
    explorer = driver.find_element(By.CSS_SELECTOR, ".narrative-explorer")
    assert "No linked passage routes were found in this controlled empty-response fixture." in explorer.text
    assert not explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-related-passage")
    assert not explorer.find_elements(By.CSS_SELECTOR, "button[data-narrative-focus-id^='related-passage:']")
    empty_controls = explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-inspect")
    assert empty_controls and all(control.get_attribute("disabled") is not None for control in empty_controls)
    assert all(control.text == "No records available" for control in empty_controls)
    selected = driver.execute_script("return window.BHFStudySelection.getState()")
    assert selected["reference"] == "Jonah 1:17" and selected["selectedVerses"] == [17], selected
    trail = driver.execute_script("return window.history.state?.bhfStudyCompanion?.trail || null")
    assert trail and trail["activeIndex"] == 0 and len(trail["nodes"]) == 1, trail
    assert trail["nodes"][0]["reference"] == "Jonah 1:17", trail

    # A fresh page removes only the test interception; the next normal projection and route handoff recover.
    driver.refresh()
    HomePage(driver, wait, ne11d1_base_url).wait_loaded()
    wait.until(lambda browser: _context_identity(browser, "jonah-three-days")["cited"])
    assert driver.execute_script("return window.BHFStudySelection.getState().reference") == "Jonah 1:17"
    _open_follow_connection(driver, wait)
    article = _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
    assert "Jonah 1:17 → Matthew 12:40" in article.text
    _click_related_passage(driver, wait, article, "Matthew 12:40")
    assert driver.execute_script("return window.BHFStudySelection.getState().reference") == "Matthew 12:40"


def test_controlled_cold_and_warm_genesis_endpoint_samples(ne11d1_base_url):
    url = f"{ne11d1_base_url}/api/narrative-explorer/v1/passages/Genesis/1"
    samples = []
    for label in ("cold", "warm"):
        started = time.monotonic()
        response = requests.get(url, params={"verse_start": 1, "verse_end": 5}, timeout=90)
        elapsed_ms = (time.monotonic() - started) * 1000
        response.raise_for_status()
        payload = response.json()
        assert payload["passage"]["reference"] == "Genesis 1:1-5"
        samples.append({
            "state": label,
            "elapsed_ms": round(elapsed_ms, 1),
            "status": response.status_code,
            "body_bytes": len(response.content),
            "body_sha256": __import__("hashlib").sha256(response.content).hexdigest(),
        })

    assert samples[0]["body_bytes"] == samples[1]["body_bytes"]
    assert samples[0]["body_sha256"] == samples[1]["body_sha256"]
    print("NE11D4_GENESIS_COLD_WARM=" + json.dumps(samples, sort_keys=True), flush=True)


@pytest.mark.parametrize(
    ("book", "chapter", "verse", "reference", "verse_start", "expected_items"),
    [
        ("Psalms", 22, 1, "Psalms 22:1", 1, 9),
        ("Psalms", 119, 176, "Psalms 119:176", 176, 7),
    ],
)
def test_negative_passage_projection_request_counts(
    driver, ne11d1_base_url, book, chapter, verse, reference, verse_start, expected_items
):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    driver.execute_script(
        """
        window.__ne11d4ProjectionEvents = [];
        const originalFetch = window.fetch.bind(window);
        window.fetch = function(input, options = {}) {
          const rawUrl = typeof input === "string" ? input : (input?.url || String(input));
          if (!rawUrl.includes("/api/narrative-explorer/v1/passages/")) {
            return originalFetch(input, options);
          }
          const event = {url: new URL(rawUrl, location.href).pathname + new URL(rawUrl, location.href).search,
            status: null, bodyBytes: null, outcome: "pending", abortObserved: false};
          window.__ne11d4ProjectionEvents.push(event);
          options.signal?.addEventListener("abort", () => { event.abortObserved = true; }, {once: true});
          return originalFetch(input, options).then(async response => {
            event.status = response.status;
            event.bodyBytes = (await response.clone().arrayBuffer()).byteLength;
            event.outcome = `http_${response.status}`;
            return response;
          }, error => {
            event.outcome = `error_${error.name || "unknown"}`;
            event.abortObserved = event.abortObserved || Boolean(options.signal?.aborted);
            throw error;
          });
        };
        """
    )
    _select_verses(driver, wait, book, chapter, [verse])
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion?.getContext?.()?.reference === arguments[0]", reference
    ))
    result = driver.execute_async_script(
        """
        const done = arguments[0];
        const selection = window.BHFStudySelection.getState();
        window.BHFNarrativeExplorer.load(selection).then(projection => {
          const context = window.BHFStudyCompanion.getContext();
          window.BHFCompanionDiscoveries.render(
            document.querySelector("[data-study-companion]"), context,
            {visible: true, narrativeExplorerEnabled: true, verifiedProjection: projection},
          );
          const path = `/api/narrative-explorer/v1/passages/${encodeURIComponent(selection.book)}/${selection.chapter}`;
          const events = window.__ne11d4ProjectionEvents.filter(event => event.url.startsWith(path));
          done({reference: projection.passage.reference, queryStatus: projection.related_passages.query_status,
            items: projection.items.length, authored: projection.related_passages.authored_relationships.length,
            bridges: projection.related_passages.evidence_backed_bridges.length,
            actionCount: document.querySelectorAll("button[data-presentation-action='explore_connection']").length,
            events});
        }).catch(error => done({error: String(error)}));
        """
    )
    assert "error" not in result, result
    assert result["reference"] == reference and result["queryStatus"] == "complete", result
    assert result["items"] == expected_items, result
    assert result["authored"] == 0 and result["bridges"] == 0 and result["actionCount"] == 0, result
    assert len(result["events"]) == 1, result
    assert f"verse_start={verse_start}" in result["events"][0]["url"], result
    assert f"verse_end={verse}" in result["events"][0]["url"], result
    assert all(event["status"] == 200 and event["bodyBytes"] > 0 for event in result["events"]), result
    print("NE11D4_NEGATIVE_REQUESTS=" + json.dumps(result, sort_keys=True), flush=True)
