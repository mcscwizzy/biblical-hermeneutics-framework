from __future__ import annotations

import json

from selenium.webdriver.support.ui import WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import (
    _click_related_passage,
    _context_identity,
    _open_follow_connection,
    _return_to_origin,
    _route_article,
    _select_verses,
)


def test_fresh_matthew_session_follows_jonah_source_without_prior_jonah_visit(driver, base_url):
    """Start an independent browser session at Matthew and preserve Jonah as source."""
    driver.set_window_size(1440, 1200)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()

    _select_verses(driver, wait, "Matthew", 12, [40])
    identity = {"object_id": "jonah", "record_kind": "claim", "record_id": "jonah-three-days"}
    evidence = wait.until(lambda browser: (
        _context_identity(browser, "jonah-three-days")
        if _context_identity(browser, "jonah-three-days")["cited"]
        else False
    ))
    assert evidence["reference"] == "Matthew 12:40"
    assert evidence["identity"] == identity
    assert {"jonah-masoretic", "jonah-new-testament"} <= set(evidence["sourceIds"])

    _open_follow_connection(driver, wait)

    article = _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
    route_text = article.text.casefold()
    assert "later canonical reception" in route_text
    assert "jonah 1:17 → matthew 12:40" in route_text
    assert "mt/lxx jonah 2:1" in route_text
    details = article.find_element(
        "css selector", ".narrative-explorer-related-passage-details"
    )
    driver.execute_script("arguments[0].open = true;", details)
    detail_text = details.text.casefold()
    assert "chronology" in detail_text
    assert "idiom" in detail_text
    assert "heart of the earth" in detail_text

    _click_related_passage(driver, wait, article, "Jonah 1:17")
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == "Jonah 1:17"
    _return_to_origin(driver, wait, "Matthew 12:40", [40])
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == "Matthew 12:40"
    print("NE11H_FRESH_MATTHEW=" + json.dumps({
        "start": evidence["reference"],
        "record": evidence["identity"],
        "source_ids": evidence["sourceIds"],
        "relationship": "later_canonical_reception",
        "historical_direction": "Jonah 1:17 → Matthew 12:40",
        "related_destination": "Jonah 1:17",
        "return": "Matthew 12:40",
    }, ensure_ascii=False), flush=True)
