from __future__ import annotations

import json

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tests.gui.pages import HomePage, WorkspacePage
from tests.gui.ne11d1.test_ed5_mobile_acceptance import _assert_chromium, _open_narrative_explorer
from tests.gui.ne11d1.test_real_ckl_handoff import _select_verses


pytestmark = [pytest.mark.gui]

CASES = [
    {
        "name": "psalm82", "book": "Psalms", "chapter": 82, "verses": [1, 2],
        "reference": "Psalms 82:1-2", "anchor": "Psalm 82:1-8",
        "uncertainty": "The identity of the figures addressed in Psalm 82 remains disputed.",
        "section_id": "divine_council_cosmic_geography",
        "record_id": "ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language",
        "witness": "Psalm 82",
    },
    {
        "name": "deuteronomy32", "book": "Deuteronomy", "chapter": 32, "verses": [8, 9],
        "reference": "Deuteronomy 32:8-9", "anchor": "Deuteronomy 32:8-9",
        "uncertainty": "The manuscripts preserve different wording at Deuteronomy 32:8; which reading is earliest remains debated.",
        "section_id": "archaeology_ancient_history",
        "record_id": "ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant",
        "witness": "4QDeuteronomy-j",
    },
]


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_ed6_passage_tasks_show_exact_source_and_natural_uncertainty(
    driver, ne11d1_base_url, case
):
    """Verify two pilot records in current remote Chromium using live reader UI."""
    browser = _assert_chromium(driver)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    _select_verses(driver, wait, case["book"], case["chapter"], case["verses"])

    explorer = _open_narrative_explorer(driver, wait)
    assert f"Current passage: {case['reference']}" not in explorer.text
    assert case["reference"] in explorer.find_element(
        By.CSS_SELECTOR, ".narrative-explorer-header h3"
    ).get_attribute("aria-label")
    explorer.find_element(By.CSS_SELECTOR, f'[data-section-id="{case["section_id"]}"]').click()
    section = wait.until(lambda page: page.find_element(
        By.CSS_SELECTOR,
        f'.narrative-explorer-section[data-section-id="{case["section_id"]}"]',
    ))
    section.find_element(By.CSS_SELECTOR, ".narrative-explorer-inspect").click()
    button = wait.until(lambda page: next((item for item in page.find_elements(
        By.CSS_SELECTOR,
        f'button[data-narrative-item-id="{case["record_id"]}"]',
    ) if item.is_displayed()), False))
    assert button.get_attribute("data-narrative-item-id") == case["record_id"]
    record = button.find_element(
        By.XPATH,
        "./ancestor::article[contains(@class, 'narrative-explorer-item')]",
    )
    assert record.find_element(By.CSS_SELECTOR, ".narrative-explorer-item-kind").text
    assert case["uncertainty"] in record.text
    provenance = record.find_element(By.CSS_SELECTOR, ".narrative-explorer-provenance")
    provenance.find_element(By.CSS_SELECTOR, "summary").click()
    provenance_text = driver.execute_script("return arguments[0].innerText", provenance)
    source_titles = driver.execute_async_script(
        """
        const recordId = arguments[0];
        const done = arguments[arguments.length - 1];
        window.BHFNarrativeExplorer.load(window.BHFStudySelection.getState())
          .then(projection => {
            const item = projection.items.find(candidate => candidate.id === recordId);
            done((item?.sources || []).map(source => source.bibliographic_details?.title || source.title || '')
              .filter(Boolean));
          }).catch(error => done({error: String(error)}));
        """,
        case["record_id"],
    )
    assert source_titles and any(title in provenance_text for title in source_titles), (source_titles, provenance_text)
    assert case["witness"] in provenance_text or case["witness"] in record.text
    assert "source is cited, but its support for this claim was not independently checked" in provenance_text
    assert not any(token in provenance_text for token in (
        "human_review_required", "in_review", "Content status", "Review status",
        "Evidence ID:", "Projected source identity:", "CKL subject:",
    ))

    button.click()
    detail = wait.until(lambda page: page.find_element(By.CSS_SELECTOR, '[aria-label="Evidence detail"]'))
    assert case["uncertainty"] in detail.text
    assert not detail.find_elements(By.CSS_SELECTOR, ".narrative-explorer-detail-review")

    sources = detail.find_element(By.CSS_SELECTOR, ".narrative-explorer-detail-sources")
    sources.find_element(By.CSS_SELECTOR, "summary").click()
    source_text = driver.execute_script("return arguments[0].innerText", sources)
    assert case["anchor"] in source_text
    assert any(title in source_text for title in source_titles), (source_titles, source_text)
    assert "source is cited, but its support for this claim was not independently checked" in source_text

    print("ED6_CHROMIUM_TASK=" + json.dumps({
        "task": case["name"], "browser": browser,
        "reference": case["reference"], "record_id": case["record_id"],
        "source_titles": source_titles, "uncertainty": True,
    }, sort_keys=True), flush=True)


def test_ed6_natural_language_task_finds_1_john_in_canonical_workspace(
    driver, ne11d1_base_url
):
    """Exercise the browser search route used by the 1 John retrieval task."""
    browser = _assert_chromium(driver)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    driver.execute_script(
        "window.BHFStudyCompanion.showPersonalResource('canonical-browser', 'Canonical Knowledge');"
        "window.BHFStudyActions.openWorkspaceTab('context');"
    )
    page = WorkspacePage(driver, wait, ne11d1_base_url)
    page.assert_tab_visible("context")
    query = "What does 1 John 3:19-24 say about a condemning heart?"
    search = wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR, '[data-testid="canonical-search-input"]'
    )))
    search.send_keys(query)
    page.click('[data-testid="canonical-search-button"]')
    wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR,
        '[data-canonical-browser-results] [data-canonical-object-id="1-john"]',
    ))
    clicked = driver.execute_script(
        """
        const result = document.querySelector(
          '[data-canonical-browser-results] [data-canonical-object-id="1-john"]'
        );
        const button = result?.querySelector('[data-testid="canonical-result-view-button"]');
        if (!button || !button.getClientRects().length || button.disabled) return false;
        button.click();
        return true;
        """
    )
    assert clicked, "The 1 John result view button was not available after the search rendered."
    wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR, "[data-canonical-detail-title]"
    ).text == "1 John")
    details = driver.find_element(By.CSS_SELECTOR, "[data-canonical-detail-sources]")
    assert "SBL Greek New Testament: 1 John" in details.text
    assert "Raymond E. Brown" in details.text
    assert "Stephen S. Smalley" in details.text
    print("ED6_CHROMIUM_TASK=" + json.dumps({
        "task": "retrieve-1john3", "browser": browser,
        "query": query, "result_opened": "1-john",
        "claim_id": "1jn-heart",
    }, sort_keys=True), flush=True)
