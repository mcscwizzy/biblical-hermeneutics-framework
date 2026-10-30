from __future__ import annotations

import json

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage


GENESIS_RECORDS = [
    (6, "genesis-flood-postflood-context", "Genesis Flood and Post-Flood Context"),
    (10, "genesis-nations-babel-context", "Genesis Nations and Babel Context"),
    (12, "genesis-abraham-call-covenant-context", "Genesis Abraham Call and Covenant Context"),
    (18, "genesis-abraham-late-cycle-context", "Genesis Abraham Late Cycle Context"),
    (26, "genesis-isaac-jacob-transition-context", "Genesis Isaac–Jacob Transition Context"),
]


@pytest.mark.parametrize(("chapter", "record_id", "title"), GENESIS_RECORDS)
def test_genesis_draft_record_disclosure_and_detail(
    driver, base_url, chapter, record_id, title
):
    """Verify the actual CKL ID, draft notice, and existing detail view."""
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value("Genesis")
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value(str(chapter))
    reference = f"Genesis {chapter}"
    wait.until(lambda browser: browser.execute_script(
        "const state = window.BHFStudySelection?.getState?.(); "
        "return state?.book === 'Genesis' && state?.chapter === Number(arguments[0]);",
        chapter,
    ))
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion?.getContext?.()?.reference === arguments[0];",
        reference,
    ))

    record = wait.until(lambda browser: browser.execute_script(
        "const records = window.BHFStudyCompanion?.getContext?.()?.summaries?.canonical || []; "
        "return records.find(item => item.id === arguments[0]) || null;",
        record_id,
    ))
    assert record["id"] == record_id, {"reference": reference, "record": record}
    assert record["title"] == title
    assert record["content_status"] == "draft"
    assert record["review_status"] == "in_review"
    assert record["human_review_required"] is True

    driver.execute_script("window.BHFStudyCompanion.openResource('canonical');")
    card = wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR,
        f'[data-companion-resource-host] [data-canonical-id="{record_id}"]',
    )))
    notice = card.find_element(By.CSS_SELECTOR, ".companion-summary-governance")
    assert card.find_element(By.CSS_SELECTOR, "h4").text == title
    assert record["summary"] in card.text
    notice_text = notice.text
    accessible_name = card.get_attribute("aria-label")
    assert notice_text == "Draft evidence — awaiting human review"
    assert notice_text in accessible_name

    card.click()
    host = driver.find_element(By.CSS_SELECTOR, "[data-companion-resource-host]")
    wait.until(lambda _browser: "Back to results" in host.text)
    detail = host.find_element(By.CSS_SELECTOR, ".companion-detail-body")
    assert detail.find_element(By.CSS_SELECTOR, "h3").text == title
    assert record["summary"] in detail.find_element(
        By.CSS_SELECTOR, ".companion-detail-intro"
    ).text
    detail_text = detail.text
    assert "approved" not in accessible_name.casefold()
    source_cards = host.find_elements(By.CSS_SELECTOR, ".canonical-source-card")
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == reference

    print("NE11H_GOVERNANCE=" + json.dumps({
        "reference": reference,
        "ckl_id": record["id"],
        "title": title,
        "summary_displayed": record["summary"] in detail_text,
        "notice_visible": notice_text,
        "accessible_name_includes_notice": notice_text in accessible_name,
        "details_opened": True,
        "source_card_count": len(source_cards),
        "source_evidence_displayed_in_detail": bool(source_cards),
        "selection_preserved": True,
    }, ensure_ascii=False), flush=True)
