from __future__ import annotations

import os
from pathlib import Path

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

from tests.gui.pages import HomePage


pytestmark = [pytest.mark.gui]

SCREENSHOTS = Path("docs/ui-modernization/ui07/screenshots")


def _select_jonah_1_17(driver, wait):
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value("Jonah")
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection?.getState?.().book === 'Jonah';"
    ))
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("1")
    wait.until(lambda browser: browser.execute_script(
        "const s=window.BHFStudySelection?.getState?.(); return s?.book === 'Jonah' && s.chapter === 1;"
    ))
    driver.execute_script(
        """
        window.__ui07Fetch = window.fetch.bind(window);
        window.__ui07ContextRequests = 0;
        window.fetch = async (input, options) => {
          const raw = input instanceof Request ? input.url : String(input);
          if (new URL(raw, location.href).pathname === '/api/study/companion-context') {
            window.__ui07ContextRequests += 1;
            const verse = new URL(raw, location.href).searchParams.get('verse_start') || '17';
            const reference = `Jonah 1:${verse}`;
            const topics = {
              historical_context: [`Historical setting preserved from the Companion. Passage: ${reference}.`, 'source-historical'],
              original_audience: [`Original audience wording remains attributed. Passage: ${reference}.`, 'source-audience'],
              literary_context: [`Literary summary stays in the context source. Passage: ${reference}.`, 'source-literary'],
              cultural_context: [`Cultural summary keeps its recorded qualification. Passage: ${reference}.`, 'source-cultural'],
              covenant_context: [`Covenant summary remains separately identified. Passage: ${reference}.`, 'source-covenant'],
            };
            const resources = Object.fromEntries(Object.keys(topics).map(id => [id, {state: 'available', available: true, count: 1}]));
            const by_context = Object.fromEntries(Object.entries(topics).map(([id, [text, source]]) => [id, {
              has_content: true,
              source_count: 1,
              lead: {text, certainty: id === 'historical_context' ? 'probable' : 'qualified', dispute_status: 'under_discussion', content_status: 'draft', review_status: 'in_review', human_review_required: true, claim_ids: [`claim-${id}`], source_ids: [source], source_details: [{id: source, title: `Recorded source ${id}`, locator: 'section 2'}]},
              sections: [],
            }]));
            return new Response(JSON.stringify({reference, resources, entities: {}, summaries: {narration: {by_context}}}), {status: 200, headers: {'Content-Type': 'application/json'}});
          }
          return window.__ui07Fetch(input, options);
        };
        """
    )
    driver.execute_script("performance.clearResourceTimings();")
    driver.find_element(
        By.CSS_SELECTOR,
        '#chapter-reader .reader-pane.is-active [data-verse="17"] [data-verse-select]',
    ).click()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection?.getState?.().reference === 'Jonah 1:17';"
    ))
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion?.getContext?.()?.reference === 'Jonah 1:17';"
    ))


def _save_screenshot(driver, name):
    if os.environ.get("BHF_UI07_CAPTURE_SCREENSHOTS") != "1":
        return
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    driver.save_screenshot(str(SCREENSHOTS / name))


def _minimum_text_contrast(driver, selector):
    return driver.execute_script(
        """
        const parse = value => {
          const srgb = value.match(/color\\(srgb\\s+([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)(?:\\s*\\/\\s*([\\d.]+))?\\)/);
          if (srgb) return [Number(srgb[1]) * 255, Number(srgb[2]) * 255, Number(srgb[3]) * 255, Number(srgb[4] ?? 1)];
          const numbers = value.match(/[\\d.]+/g)?.map(Number) || [];
          return [numbers[0] || 0, numbers[1] || 0, numbers[2] || 0, numbers[3] ?? 1];
        };
        const composite = (front, back) => front.map((value, index) =>
          index < 3 ? value * front[3] + back[index] * (1 - front[3]) : 1
        );
        const luminance = ([red, green, blue]) => {
          const linear = channel => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
          return 0.2126 * linear(red / 255) + 0.7152 * linear(green / 255) + 0.0722 * linear(blue / 255);
        };
        const ratio = (left, right) => {
          const first = luminance(left), second = luminance(right);
          return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
        };
        return Array.from(document.querySelectorAll(arguments[0])).filter(element => element.offsetParent !== null).map(element => {
          const foreground = parse(getComputedStyle(element).color);
          let background = [255, 255, 255, 1];
          const ancestors = [];
          for (let ancestor = element; ancestor; ancestor = ancestor.parentElement) {
            ancestors.push(ancestor);
          }
          ancestors.reverse().forEach(ancestor => {
            const layer = parse(getComputedStyle(ancestor).backgroundColor);
            if (layer[3] > 0) background = composite(layer, background);
          });
          return {text: element.textContent.trim().slice(0, 60), ratio: ratio(foreground, background)};
        });
        """,
        selector,
    )


def test_enabled_narrative_hub_keeps_context_summaries_and_reader_state(driver, wait, base_url):
    wait = WebDriverWait(driver, 90)
    driver.set_window_size(1440, 1200)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_jonah_1_17(driver, wait)

    panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    overview = driver.find_element(By.CSS_SELECTOR, "[data-companion-overview]")
    assert overview.is_displayed()
    assert len(driver.find_elements(By.CSS_SELECTOR, "[data-companion-primary-research] .companion-narrative-card")) == 2
    assert not driver.find_element(By.CSS_SELECTOR, "[data-companion-explore-catalogue]").is_displayed()
    assert not any(element.is_displayed() for element in driver.find_elements(By.CSS_SELECTOR, ".companion-research-tools, .companion-advanced-links"))
    assert driver.find_element(By.CSS_SELECTOR, '[data-companion-resource="translation_comparison"]').is_displayed()
    assert driver.find_element(By.CSS_SELECTOR, '[data-companion-action="note"]').is_displayed()
    assert driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf]").is_displayed()
    assert driver.find_element(By.CSS_SELECTOR, '[data-companion-tyndale-card-slot]')
    _save_screenshot(driver, "after-overview-desktop.png")

    driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer")))
    assert {node.text for node in driver.find_elements(By.CSS_SELECTOR, ".narrative-explorer-category-title")} == {
        "Biblical Narrative",
        "Archaeology & Ancient History",
        "Biblical Geography",
        "Divine Council & Cosmic Geography",
        "Themes & Biblical Connections",
        "People, Events & Relationships",
    }
    follow = driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-follow-connection")
    assert follow.is_displayed()
    context_entry = driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-understand-passage")
    assert context_entry.find_element(By.CSS_SELECTOR, ".narrative-explorer-context-copy strong").text == "Understand the Passage"
    assert "Explore the historical setting, original audience, literary structure, and cultural background." in context_entry.text

    projection_count = driver.execute_script(
        "return performance.getEntriesByType('resource').filter(entry => entry.name.includes('/api/narrative-explorer/v1/passages/')).length;"
    )
    context_count = driver.execute_script("return window.__ui07ContextRequests;")
    context_entry.click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-understand-passage]")))
    topic_buttons = driver.find_elements(By.CSS_SELECTOR, "[data-context-topic-id]")
    assert [button.get_attribute("data-context-topic-id") for button in topic_buttons] == [
        "historical_context", "original_audience", "literary_context", "cultural_context", "covenant_context",
    ]
    assert len(driver.find_elements(By.CSS_SELECTOR, "[data-context-topic-panel]")) == 1
    passage_view = driver.find_element(By.CSS_SELECTOR, "[data-companion-resource-host]")
    assert "Historical setting preserved from the Companion." in passage_view.text
    driver.execute_script("arguments[0].open = true;", passage_view.find_element(By.CSS_SELECTOR, "details"))
    passage_view = driver.find_element(By.CSS_SELECTOR, "[data-companion-resource-host]")
    assert "Certainty: probable" in passage_view.text
    assert "Dispute: under discussion" in passage_view.text
    assert "Status: draft" in passage_view.text
    assert "Review: in review" in passage_view.text
    assert "Human review required" in passage_view.text
    assert "Recorded source historical_context · section 2" in passage_view.text
    assert "separate from Narrative Explorer evidence records" in passage_view.text
    assert driver.execute_script(
        "return performance.getEntriesByType('resource').filter(entry => entry.name.includes('/api/narrative-explorer/v1/passages/')).length;"
    ) == projection_count
    assert driver.execute_script("return window.__ui07ContextRequests;") == context_count
    _save_screenshot(driver, "after-understand-passage-desktop.png")

    driver.execute_script(
        "const current=window.BHFStudySelection.getState(); "
        "window.BHFStudySelection.setSelection({...current, startVerse:16, endVerse:16, "
        "selectedVerses:[16], reference:'Jonah 1:16', selectedText:'Jonah 1:16'}, 'ui07-reader-change');"
    )
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection.getState().reference === 'Jonah 1:16';"
    ))
    wait.until(lambda browser: browser.execute_script(
        "const record=window.BHFStudyCompanion.getContextRecord(); "
        "return record?.status === 'ready' && record.key === window.BHFCompanionContext.requestKey(window.BHFStudySelection.getState());"
    ))
    wait.until(lambda browser: "Passage: Jonah 1:16." in browser.find_element(
        By.CSS_SELECTOR, "[data-context-topic-panel]"
    ).text)
    assert "Passage: Jonah 1:17." not in driver.find_element(By.CSS_SELECTOR, "[data-context-topic-panel]").text
    assert driver.execute_script(
        "return window.history.state?.bhfStudyCompanion?.trail?.originSelection?.reference;"
    ) == "Jonah 1:16"
    driver.execute_script(
        "const current=window.BHFStudySelection.getState(); "
        "window.BHFStudySelection.setSelection({...current, startVerse:17, endVerse:17, "
        "selectedVerses:[17], reference:'Jonah 1:17', selectedText:'Jonah 1:17'}, 'ui07-reader-change');"
    )
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection.getState().reference === 'Jonah 1:17';"
    ))
    wait.until(lambda browser: browser.execute_script(
        "const record=window.BHFStudyCompanion.getContextRecord(); "
        "return record?.status === 'ready' && record.key === window.BHFCompanionContext.requestKey(window.BHFStudySelection.getState());"
    ))
    wait.until(lambda browser: "Passage: Jonah 1:17." in browser.find_element(
        By.CSS_SELECTOR, "[data-context-topic-panel]"
    ).text)

    driver.back()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-follow-connection")))
    wait.until(lambda browser: browser.execute_script(
        "return document.activeElement?.dataset?.narrativeFocusId === 'understand-passage';"
    ))
    driver.forward()
    wait.until(lambda browser: browser.find_element(By.CSS_SELECTOR, "[data-context-topic-id='historical_context']").get_attribute("aria-pressed") == "true")
    driver.find_element(By.CSS_SELECTOR, "[data-context-topic-id='original_audience']").click()
    wait.until(lambda browser: browser.find_element(By.CSS_SELECTOR, "[data-context-topic-panel]").text.find("Original audience wording remains attributed.") >= 0)
    assert "Historical setting preserved from the Companion." not in driver.find_element(By.CSS_SELECTOR, "[data-context-topic-panel]").text

    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-follow-connection")))
    wait.until(lambda browser: browser.execute_script(
        "return document.activeElement?.dataset?.narrativeFocusId === 'understand-passage';"
    ))
    driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-understand-passage").click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-understand-passage]")))
    driver.find_element(By.CSS_SELECTOR, ".companion-context-return").click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-follow-connection")))
    for category in (
        "biblical_narrative",
        "archaeology_ancient_history",
        "biblical_geography",
        "divine_council_cosmic_geography",
        "themes_biblical_connections",
        "people_events_relationships",
    ):
        driver.find_element(By.CSS_SELECTOR, f"[data-section-id='{category}']").click()
        wait.until(lambda browser: browser.execute_script(
            "return window.history.state?.bhfStudyCompanion?.narrativeView?.categoryId === arguments[0];", category
        ))
        driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-back-topics").click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-follow-connection")))

    driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-follow-connection").click()
    route_button = wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR,
        "button[data-narrative-focus-id^='related-passage:']",
    )))
    assert "Matthew 12:40" in route_button.text
    route_button.click()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection.getState().reference === 'Matthew 12:40';"
    ))
    trail = driver.execute_script("return window.history.state?.bhfStudyCompanion?.trail || null;")
    assert trail and trail["activeIndex"] > 0
    assert {node.get("reference") for node in trail["nodes"]} >= {"Jonah 1:17", "Matthew 12:40"}
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-return-origin"))).click()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection.getState().reference === 'Jonah 1:17';"
    ))
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-follow-connection")))

    driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-browse-sources").click()
    sources = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".companion-research-sources-view")))
    assert "Open Canonical Knowledge" in sources.text
    assert "Open Maps Explorer" in sources.text
    assert "Open Archaeology Library" in sources.text
    assert "Open Cross References" in sources.text

    driver.set_window_size(390, 844)
    wait.until(lambda browser: browser.execute_script("return window.innerWidth === 390;"))
    driver.find_element(By.CSS_SELECTOR, ".companion-research-sources-view nav button").click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-follow-connection")))
    _save_screenshot(driver, "after-overview-mobile-390.png")
    overview_contrast = _minimum_text_contrast(
        driver,
        ".narrative-explorer-follow-connection, "
        ".narrative-explorer-understand-passage strong, "
        ".narrative-explorer-understand-passage span, "
        ".narrative-explorer-category-title, .narrative-explorer-browse-sources",
    )
    assert overview_contrast and min(item["ratio"] for item in overview_contrast) >= 4.5, overview_contrast
    overflow = driver.execute_script(
        "return {width: innerWidth, document: document.documentElement.scrollWidth, host: document.querySelector('[data-companion-resource-host]').scrollWidth};"
    )
    assert overflow["document"] <= overflow["width"]
    assert overflow["host"] <= overflow["width"]
    driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-understand-passage").click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-understand-passage]")))
    driver.execute_script("document.querySelector('[data-companion-resource-host]').scrollTop = 0;")
    _save_screenshot(driver, "after-understand-passage-mobile-390.png")
    context_contrast = _minimum_text_contrast(
        driver,
        "[data-understand-passage] .companion-context-provenance, "
        "[data-understand-passage] .companion-context-topic, "
        "[data-understand-passage] .companion-context-topic-panel h4, "
        "[data-understand-passage] .companion-context-topic-status, "
        "[data-understand-passage] .companion-context-actions button",
    )
    assert context_contrast and min(item["ratio"] for item in context_contrast) >= 4.5, context_contrast
    overflow = driver.execute_script(
        "return {width: innerWidth, document: document.documentElement.scrollWidth, host: document.querySelector('[data-companion-resource-host]').scrollWidth};"
    )
    assert overflow["document"] <= overflow["width"]
    assert overflow["host"] <= overflow["width"]
