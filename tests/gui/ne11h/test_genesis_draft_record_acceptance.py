from __future__ import annotations

import json

import pytest
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage


GENESIS_RECORDS = [
    (6, "genesis-flood-postflood-context", "Genesis Flood and Post-Flood Context", 29, 25),
    (10, "genesis-nations-babel-context", "Genesis Nations and Babel Context", 20, 29),
    (12, "genesis-abraham-call-covenant-context", "Genesis Abraham Call and Covenant Context", 17, 46),
    (18, "genesis-abraham-late-cycle-context", "Genesis Abraham Late Cycle Context", 11, 71),
    (26, "genesis-isaac-jacob-transition-context", "Genesis Isaac–Jacob Transition Context", 12, 51),
]


@pytest.mark.parametrize(("chapter", "record_id", "title", "source_count", "evidence_count"), GENESIS_RECORDS)
def test_genesis_draft_record_disclosure_and_detail(
    driver, base_url, chapter, record_id, title, source_count, evidence_count
):
    """Verify exact CKL identity and inspect only that object's source records."""
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
    assert detail.get_attribute("data-canonical-object-id") == record_id
    assert detail.find_element(By.CSS_SELECTOR, "h3").text == title
    assert record["summary"] in detail.find_element(
        By.CSS_SELECTOR, ".companion-detail-intro"
    ).text
    detail_text = detail.text
    detail_notice = detail.find_element(By.CSS_SELECTOR, ".companion-summary-governance")
    detail_notice_text = detail_notice.text
    assert detail_notice_text == "Draft evidence — awaiting human review"
    assert "approved" not in accessible_name.casefold()
    assert detail.find_element(By.CSS_SELECTOR, ".companion-detail-action").text == "← Back to results"
    assert any(
        button.text == "Open Canonical Knowledge →"
        for button in detail.find_elements(By.CSS_SELECTOR, ".companion-detail-action")
    )

    selected_response = requests.get(
        f"{base_url}/api/canonical/objects/{record_id}", timeout=90
    )
    related_response = requests.get(f"{base_url}/api/canonical/objects/abraham", timeout=90)
    assert selected_response.status_code == 200
    assert related_response.status_code == 200
    selected_api = selected_response.json()
    related_api = related_response.json()
    assert selected_api["id"] == record_id
    assert selected_api["source_count"] == source_count
    assert len(selected_api["sources"]) == source_count
    assert selected_api["evidence_count"] == evidence_count
    assert len(selected_api["evidence_items"]) == evidence_count

    source_disclosure = detail.find_element(By.CSS_SELECTOR, ".companion-canonical-sources")
    source_disclosure.find_element(By.TAG_NAME, "summary").send_keys(Keys.ENTER)
    wait.until(lambda _browser: driver.execute_script("return arguments[0].open;", source_disclosure))
    source_records = detail.find_elements(By.CSS_SELECTOR, ".companion-canonical-source")
    source_ids = {item.get_attribute("data-source-id") for item in source_records}
    expected_source_ids = {item["id"] for item in selected_api["sources"]}
    unrelated_only_ids = {
        item["id"] for item in related_api.get("sources", [])
    } - expected_source_ids
    assert len(source_records) == source_count
    assert source_ids == expected_source_ids
    assert source_ids.isdisjoint(unrelated_only_ids)

    attributed_source = next(
        item for item in selected_api["sources"]
        if item.get("title") and item.get("author") and item.get("locator")
    )
    attributed_record = detail.find_element(
        By.CSS_SELECTOR,
        f'[data-source-id="{attributed_source["id"]}"]',
    )
    attributed_record.find_element(By.TAG_NAME, "summary").send_keys(Keys.SPACE)
    wait.until(lambda _browser: driver.execute_script("return arguments[0].open;", attributed_record))
    for value in (attributed_source["title"], attributed_source["author"], attributed_source["locator"]):
        assert value in attributed_record.text

    if record_id == "genesis-abraham-call-covenant-context":
        evidence_disclosure = detail.find_element(By.CSS_SELECTOR, ".companion-canonical-evidence")
        evidence_disclosure.find_element(By.TAG_NAME, "summary").send_keys(Keys.ENTER)
        evidence = next(
            item for item in selected_api["evidence_items"]
            if item["id"] == "g12-call-leave-household"
        )
        evidence_record = detail.find_element(
            By.CSS_SELECTOR,
            f'[data-evidence-id="{evidence["id"]}"]',
        )
        evidence_record.find_element(By.TAG_NAME, "summary").send_keys(Keys.ENTER)
        for source_id in evidence["source_ids"]:
            source = next(item for item in selected_api["sources"] if item["id"] == source_id)
            assert source["title"] in evidence_record.text
        assert "Recorded source links for this item" in evidence_record.text

        for width in (320, 390):
            driver.set_window_size(width, 1200)
            assert driver.execute_script(
                "return document.documentElement.scrollWidth <= window.innerWidth;"
            ), f"horizontal overflow at {width}px"
            assert detail.is_displayed()

    source_disclosure.find_element(By.TAG_NAME, "summary").send_keys(Keys.SPACE)
    wait.until(lambda _browser: not driver.execute_script("return arguments[0].open;", source_disclosure))
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == reference

    detail.find_element(By.CSS_SELECTOR, "[data-native-resource-back]").click()
    wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR,
        f'[data-companion-resource-host] [data-canonical-id="{record_id}"]',
    )))
    assert driver.execute_script(
        "return document.activeElement?.dataset?.canonicalId === arguments[0];",
        record_id,
    )
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
        "source_count": len(source_ids),
        "evidence_count": len(selected_api["evidence_items"]),
        "source_ids_exact": source_ids == expected_source_ids,
        "draft_notice_remains_in_detail": detail_notice_text == "Draft evidence — awaiting human review",
        "evidence_source_links_preserved": record_id != "genesis-abraham-call-covenant-context" or bool(evidence["source_ids"]),
        "selection_preserved": True,
        "back_focus_restored": True,
    }, ensure_ascii=False), flush=True)


def test_companion_non_draft_ckl_object_discloses_its_own_sources(driver, base_url):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value("Genesis")
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("12")
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection?.getState?.()?.reference === 'Genesis 12';"
    ))

    driver.execute_script("window.BHFStudyCompanion.openResource('places');")
    card = wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR,
        '[data-companion-resource-host] [data-canonical-id="shechem"]',
    )))
    card.click()
    detail = wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR,
        '[data-companion-resource-host] .companion-detail-body[data-canonical-object-id="shechem"]',
    )))
    assert detail.find_element(By.CSS_SELECTOR, "h3").text == "Shechem"
    assert not detail.find_elements(By.CSS_SELECTOR, ".companion-summary-governance")

    api_detail = requests.get(f"{base_url}/api/canonical/objects/shechem", timeout=90).json()
    assert api_detail["content_status"] == "complete"
    assert api_detail["review_status"] == "in_review"
    source_disclosure = detail.find_element(By.CSS_SELECTOR, ".companion-canonical-sources")
    source_disclosure.find_element(By.TAG_NAME, "summary").send_keys(Keys.ENTER)
    wait.until(lambda _browser: driver.execute_script("return arguments[0].open;", source_disclosure))
    displayed_source_ids = {
        item.get_attribute("data-source-id")
        for item in detail.find_elements(By.CSS_SELECTOR, ".companion-canonical-source")
    }
    assert displayed_source_ids == {item["id"] for item in api_detail["sources"]}
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == "Genesis 12"


def test_browser_back_and_forward_during_source_disclosure_preserve_passage(driver, base_url):
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value("Genesis")
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("12")
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection?.getState?.()?.reference === 'Genesis 12';"
    ))
    driver.execute_script("window.BHFStudyCompanion.openResource('canonical');")
    object_id = "genesis-abraham-call-covenant-context"
    card = wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR,
        f'[data-companion-resource-host] [data-canonical-id="{object_id}"]',
    )))
    card.click()
    detail = wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR,
        f'[data-companion-resource-host] .companion-detail-body[data-canonical-object-id="{object_id}"]',
    )))
    source_disclosure = detail.find_element(By.CSS_SELECTOR, ".companion-canonical-sources")
    before = driver.execute_script(
        "return {length: history.length, state: JSON.stringify(history.state)};"
    )
    source_disclosure.find_element(By.TAG_NAME, "summary").send_keys(Keys.ENTER)
    wait.until(lambda _browser: driver.execute_script("return arguments[0].open;", source_disclosure))
    after = driver.execute_script(
        "return {length: history.length, state: JSON.stringify(history.state)};"
    )
    assert after == before

    driver.execute_script("window.history.back();")
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion?.getState?.()?.resource !== 'canonical';"
    ))
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == "Genesis 12"

    driver.execute_script("window.history.forward();")
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion?.getState?.()?.resource === 'canonical';"
    ))
    wait.until(EC.visibility_of_element_located((
        By.CSS_SELECTOR,
        f'[data-companion-resource-host] [data-canonical-id="{object_id}"]',
    )))
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == "Genesis 12"
