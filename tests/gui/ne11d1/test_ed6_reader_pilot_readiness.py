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
        "dispute_status": "interpretive_uncertainty",
        "section_id": "divine_council_cosmic_geography",
        "record_id": "ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language",
        "source_id": "psalm-82-hebrew-text", "witness": "Psalm 82",
    },
    {
        "name": "deuteronomy32", "book": "Deuteronomy", "chapter": 32, "verses": [8, 9],
        "reference": "Deuteronomy 32:8-9", "anchor": "Deuteronomy 32:8-9",
        "dispute_status": "textual_variant",
        "section_id": "archaeology_ancient_history",
        "record_id": "ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant",
        "source_id": "deuteronomy-32-text", "secondary_source_id": "ulrich-biblical-qumran-scrolls-2010",
        "witness": "4QDeuteronomy-j",
    },
]


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_ed6_passage_tasks_show_exact_record_source_and_review_limits(
    driver, ne11d1_base_url, case
):
    """Verify two pilot records in current remote Chromium using live reader UI."""
    browser = _assert_chromium(driver)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    _select_verses(driver, wait, case["book"], case["chapter"], case["verses"])

    explorer = _open_narrative_explorer(driver, wait)
    assert f"Current passage: {case['reference']}" in explorer.text
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
    record = button.find_element(
        By.XPATH,
        "./ancestor::article[contains(@class, 'narrative-explorer-item')]",
    )
    assert record.find_element(By.CSS_SELECTOR, ".narrative-explorer-item-kind").text
    provenance = record.find_element(By.CSS_SELECTOR, ".narrative-explorer-provenance")
    provenance.find_element(By.CSS_SELECTOR, "summary").click()
    provenance_text = provenance.text
    assert f"Projected source identity: {case['record_id']}" in provenance_text
    assert f"Evidence ID: {case['record_id'].split('#evidence:', 1)[1]}" in provenance_text
    assert case["anchor"] in provenance_text
    assert case["source_id"] in provenance_text
    assert f"Dispute status: {case['dispute_status']}" in provenance_text
    assert "Content status: draft" in provenance_text
    assert "Review status: in_review" in provenance_text
    assert "Human review required: Yes" in provenance_text
    assert case["witness"] in provenance_text

    button.click()
    detail = wait.until(lambda page: page.find_element(By.CSS_SELECTOR, '[aria-label="Evidence detail"]'))
    review = detail.find_element(By.CSS_SELECTOR, ".narrative-explorer-detail-review")
    review.find_element(By.CSS_SELECTOR, "summary").click()
    assert "primary observation" in review.text.lower()
    assert "scholarly interpretation" in review.text.lower()
    assert "Content state: draft" in review.text
    assert "Review state: in_review" in review.text
    assert "human review required: yes" in review.text.lower()

    sources = detail.find_element(By.CSS_SELECTOR, ".narrative-explorer-detail-sources")
    sources.find_element(By.CSS_SELECTOR, "summary").click()
    assert case["source_id"] in sources.text
    if case.get("secondary_source_id"):
        assert case["secondary_source_id"] in sources.text
        assert "The Biblical Qumran Scrolls" in sources.text
        assert "4QDeuteronomy-j (4Q37), Deuteronomy 32:8-9" in sources.text
    else:
        assert case["anchor"] in sources.text

    print("ED6_CHROMIUM_TASK=" + json.dumps({
        "task": case["name"], "browser": browser,
        "reference": case["reference"], "record_id": case["record_id"],
        "source_id": case["source_id"], "draft_review": True,
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
    result = wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR,
        '[data-canonical-browser-results] [data-canonical-object-id="1-john"]',
    ))
    result.find_element(By.CSS_SELECTOR, '[data-testid="canonical-result-view-button"]').click()
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
