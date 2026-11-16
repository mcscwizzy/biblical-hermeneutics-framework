from __future__ import annotations

import json

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.viewport import set_viewport
from tests.gui.ne11d1.test_ed5_mobile_acceptance import (
    _assert_chromium,
    _open_narrative_explorer,
)
from tests.gui.ne11d1.test_real_ckl_handoff import (
    _click_related_passage,
    _route_article,
)


pytestmark = [pytest.mark.gui]


FEATURED = [
    {
        "name": "nahum3",
        "book": "Nahum",
        "chapter": 3,
        "verses": [8, 9],
        "reference": "Nahum 3:8-9",
        "title": "Does Nahum 3:8–9 compare Nineveh with No-Amon?",
        "source_title": "A Tale of One City",
        "source_author": "Nesina Grütter",
        "source_limit": "No 4Q385a or other manuscript image inspected.",
    },
    {
        "name": "proverbs15",
        "book": "Proverbs",
        "chapter": 15,
        "verses": [25],
        "reference": "Proverbs 15:25",
        "title": "Hebrew and Greek versions arrange part of Proverbs 15:25–16:9 differently.",
        "source_title": "De Yhwh la réponse de la langue",
        "source_author": "Jean-Daniel Macchi",
        "source_limit": "no fragment image or critical edition independently inspected.",
    },
]


def _select_passage(driver, wait, case: dict) -> None:
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value(case["book"])
    wait.until(lambda page: page.execute_script(
        "return window.BHFStudySelection?.getState?.().book === arguments[0];",
        case["book"],
    ))
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value(str(case["chapter"]))
    wait.until(lambda page: page.execute_script(
        "return window.BHFStudySelection?.getState?.().chapter === Number(arguments[0]);",
        str(case["chapter"]),
    ))
    driver.execute_script(
        "window.BHFStudySelection.setSelection({book: arguments[0], chapter: Number(arguments[1]), "
        "selectedVerses: arguments[2], translation: 'kjv', reference: arguments[3]}, 'ed7-reader-journey');",
        case["book"],
        case["chapter"],
        case["verses"],
        case["reference"],
    )
    wait.until(lambda page: page.execute_script(
        "return window.BHFStudySelection?.getState?.().reference === arguments[0];",
        case["reference"],
    ))


def _open_explorer(driver, wait):
    if driver.execute_script("return document.body.dataset.appSection !== 'explore'"):
        driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-explore"]').click()
        wait.until(lambda page: page.execute_script("return document.body.dataset.appSection === 'explore'"))
    return _open_narrative_explorer(driver, wait)


@pytest.mark.parametrize("case", FEATURED, ids=[case["name"] for case in FEATURED])
def test_ed7_featured_discoveries_disclose_sources_without_editorial_diagnostics(
    driver, ne11d1_base_url, artifacts_dir, case
):
    browser = _assert_chromium(driver)
    wait = WebDriverWait(driver, 90)
    set_viewport(driver, 1440, 1200, mobile=False)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    set_viewport(driver, 1440, 1200, mobile=False)
    _select_passage(driver, wait, case)

    explorer = _open_explorer(driver, wait)
    card = wait.until(lambda page: page.find_element(By.CSS_SELECTOR, ".narrative-explorer-featured-card"))
    assert f"Current passage: {case['reference']}" in explorer.text
    assert case["title"] in card.text
    assert card.find_element(By.CSS_SELECTOR, ".narrative-explorer-featured-uncertainty").text
    assert not any(token in explorer.text.lower() for token in (
        "human_review_required", "content status", "review status", "source_domain", "ckl:",
    ))

    source = card.find_element(By.CSS_SELECTOR, ".narrative-explorer-provenance")
    source.find_element(By.CSS_SELECTOR, "summary").click()
    source_text = driver.execute_script("return arguments[0].innerText", source)
    assert case["source_title"] in source_text
    assert case["source_author"] in source_text
    assert case["source_limit"].lower() in source_text.lower()
    assert "This automated check is not a human scholarly review." in source_text
    assert "Some cited sources do not include full publication details here." in source_text
    assert "The citation is missing" not in source_text
    assert not any(token in source_text for token in ("ckl:", "source_id", "human_review_required"))

    screenshot = artifacts_dir / f"ed7-{case['name']}-how-we-know.png"
    assert driver.save_screenshot(str(screenshot))
    print("ED7_CHROMIUM_SOURCE=" + json.dumps({
        "case": case["name"],
        "browser": browser,
        "reference": case["reference"],
        "source_title": case["source_title"],
        "source_limit": case["source_limit"],
        "internal_labels_visible": False,
        "screenshot": screenshot.name,
    }, sort_keys=True), flush=True)


def test_ed7_jonah_to_matthew_connection_keeps_direction_and_navigation(
    driver, ne11d1_base_url, artifacts_dir
):
    browser = _assert_chromium(driver)
    wait = WebDriverWait(driver, 90)
    set_viewport(driver, 1440, 1200, mobile=False)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    set_viewport(driver, 1440, 1200, mobile=False)
    _select_passage(driver, wait, {
        "book": "Jonah",
        "chapter": 1,
        "verses": [17],
        "reference": "Jonah 1:17",
    })
    explorer = _open_explorer(driver, wait)
    explorer.find_element(By.CSS_SELECTOR, ".narrative-explorer-follow-connection").click()
    wait.until(lambda page: page.find_element(By.CSS_SELECTOR, ".narrative-explorer-related-passages"))
    article = _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
    assert "Connection to Matthew 12:40" in article.text
    assert "The earlier text is Jonah 1:17; the later passage is Matthew 12:40." in article.text
    assert "Matthew 12:40 explicitly compares" in article.text
    assert not any(token in article.text for token in (
        "ckl:", "source_id", "human_review_required", "Connection type:",
    ))

    support = article.find_element(By.CSS_SELECTOR, "details")
    support.find_element(By.CSS_SELECTOR, "summary").click()
    support_text = driver.execute_script("return arguments[0].innerText", support)
    assert "How this connection is supported" in support_text
    assert "Jonah 1:17" in support_text and "Matthew 12:40" in support_text
    before = artifacts_dir / "ed7-jonah-matthew-route.png"
    assert driver.save_screenshot(str(before))

    _click_related_passage(driver, wait, article, "Matthew 12:40")
    assert driver.execute_script("return window.BHFStudySelection?.getState?.().reference") == "Matthew 12:40"
    wait.until(lambda page: "Current passage: Matthew 12:40" in page.find_element(
        By.CSS_SELECTOR,
        ".narrative-explorer",
    ).text)
    after = artifacts_dir / "ed7-jonah-matthew-destination.png"
    assert driver.save_screenshot(str(after))
    print("ED7_CHROMIUM_CONNECTION=" + json.dumps({
        "browser": browser,
        "source": "Jonah 1:17",
        "destination": "Matthew 12:40",
        "navigation_verified": True,
        "screenshots": [before.name, after.name],
    }, sort_keys=True), flush=True)
