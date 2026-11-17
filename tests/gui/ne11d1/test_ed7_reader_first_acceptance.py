from __future__ import annotations

import json

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.viewport import set_viewport
from tests.gui.ne11d1.test_ed5_mobile_acceptance import (
    _assert_chromium,
    _open_narrative_explorer,
)
from tests.gui.ne11d1.test_real_ckl_handoff import (
    _click_related_passage,
    _route_article,
    _select_verses,
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
        "source_limit": "That discussion was not compared with an image of 4Q385a or another manuscript.",
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
        "source_limit": "That discussion was not checked against a fragment image or critical edition.",
    },
]

VIEWPORTS = [
    (1440, 1200, False, "desktop"),
    (390, 844, True, "390px"),
    (320, 844, True, "320px"),
]

OPENING_CASES = [
    {"name": "genesis6", "book": "Genesis", "chapter": 6, "verses": [1, 2, 3, 4], "reference": "Genesis 6:1-4"},
    {"name": "john1", "book": "John", "chapter": 1, "verses": [1], "reference": "John 1:1"},
    {"name": "jeremiah32", "book": "Jeremiah", "chapter": 32, "verses": [1], "reference": "Jeremiah 32:1"},
    {"name": "genesis12", "book": "Genesis", "chapter": 12, "verses": [1, 2, 3], "reference": "Genesis 12:1-3"},
    {"name": "psalm82", "book": "Psalms", "chapter": 82, "verses": [1, 2, 3, 4, 5, 6, 7, 8], "reference": "Psalms 82:1-8"},
]


def _select_passage(driver, wait, case: dict) -> None:
    _select_verses(driver, wait, case["book"], case["chapter"], case["verses"])
    wait.until(lambda page: page.execute_script(
        "return window.BHFStudySelection?.getState?.().reference === arguments[0];",
        case["reference"],
    ))


def _open_explorer(driver, wait):
    if driver.execute_script("return window.innerWidth > 900 && document.body.dataset.appSection !== 'explore'"):
        driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-explore"]').click()
        wait.until(lambda page: page.execute_script("return document.body.dataset.appSection === 'explore'"))
    return _open_narrative_explorer(driver, wait)


@pytest.mark.parametrize("case", FEATURED, ids=[case["name"] for case in FEATURED])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=[entry[3] for entry in VIEWPORTS])
def test_ed7_featured_discoveries_disclose_sources_without_editorial_diagnostics(
    driver, ne11d1_base_url, artifacts_dir, case, viewport
):
    browser = _assert_chromium(driver)
    wait = WebDriverWait(driver, 90)
    width, height, mobile, label = viewport
    set_viewport(driver, width, height, mobile=mobile)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    set_viewport(driver, width, height, mobile=mobile)
    _select_passage(driver, wait, case)

    explorer = _open_explorer(driver, wait)
    card = wait.until(lambda page: page.find_element(By.CSS_SELECTOR, ".narrative-explorer-featured-card"))
    assert f"Current passage: {case['reference']}" not in explorer.text
    assert case["reference"] in explorer.find_element(By.CSS_SELECTOR, ".narrative-explorer-header h3").get_attribute("aria-label")
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
    assert "The cited work and its relevant pages are listed below." in source_text
    assert "Some citation details are unavailable." in source_text
    assert "automated check" not in source_text.lower()
    assert "human scholarly review" not in source_text.lower()
    assert "The citation is missing" not in source_text
    assert not any(token in source_text for token in ("ckl:", "source_id", "human_review_required"))
    assert driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth"), width

    screenshot = artifacts_dir / f"{case['name']}-{label}-how-we-know.png"
    assert driver.save_screenshot(str(screenshot))
    print("ED7_CHROMIUM_SOURCE=" + json.dumps({
        "case": case["name"],
        "browser": browser,
        "reference": case["reference"],
        "viewport": width,
        "source_title": case["source_title"],
        "source_limit": case["source_limit"],
        "internal_labels_visible": False,
        "screenshot": screenshot.name,
    }, sort_keys=True), flush=True)


@pytest.mark.parametrize("case", OPENING_CASES, ids=[case["name"] for case in OPENING_CASES])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=[entry[3] for entry in VIEWPORTS])
def test_ed7_overview_only_shows_qualified_discoveries_and_reader_pathways(
    driver, ne11d1_base_url, artifacts_dir, case, viewport
):
    browser = _assert_chromium(driver)
    wait = WebDriverWait(driver, 90)
    width, height, mobile, label = viewport
    set_viewport(driver, width, height, mobile=mobile)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    set_viewport(driver, width, height, mobile=mobile)
    _select_passage(driver, wait, case)

    explorer = _open_explorer(driver, wait)
    assert f"Current passage: {case['reference']}" not in explorer.text
    assert case["reference"] in explorer.find_element(By.CSS_SELECTOR, ".narrative-explorer-header h3").get_attribute("aria-label")
    featured_sections = explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-featured-discoveries")
    featured_cards = explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-featured-card")
    if featured_sections:
        assert featured_cards
    else:
        assert not featured_cards
    assert not explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-featured-empty")
    assert len(explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-category-card")) == 6
    pathways = explorer.find_element(By.CSS_SELECTOR, ".narrative-explorer-pathways")
    assert pathways.find_element(By.CSS_SELECTOR, ".narrative-explorer-understand-passage").is_displayed()
    assert pathways.find_element(By.CSS_SELECTOR, ".narrative-explorer-follow-connection").is_displayed()
    assert driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth"), width

    screenshot = artifacts_dir / f"{case['name']}-{label}.png"
    assert driver.save_screenshot(str(screenshot))
    print("ED7_CHROMIUM_OPENING=" + json.dumps({
        "case": case["name"], "browser": browser, "reference": case["reference"],
        "viewport": width, "featured_cards": len(featured_cards), "study_topics": 6,
        "compact_pathways": True, "horizontal_overflow": False,
        "screenshot": screenshot.name,
    }, sort_keys=True), flush=True)


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=[entry[3] for entry in VIEWPORTS])
def test_ed7_jonah_to_matthew_connection_keeps_direction_and_navigation(
    driver, ne11d1_base_url, artifacts_dir, viewport
):
    browser = _assert_chromium(driver)
    wait = WebDriverWait(driver, 90)
    width, height, mobile, label = viewport
    set_viewport(driver, width, height, mobile=mobile)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    set_viewport(driver, width, height, mobile=mobile)
    _select_passage(driver, wait, {
        "book": "Jonah",
        "chapter": 1,
        "verses": [17],
        "reference": "Jonah 1:17",
    })
    explorer = _open_explorer(driver, wait)
    assert not explorer.find_elements(By.CSS_SELECTOR, ".narrative-explorer-featured-empty")
    assert explorer.find_element(By.CSS_SELECTOR, ".narrative-explorer-pathways .narrative-explorer-follow-connection").is_displayed()
    assert driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth"), width
    explorer.find_element(By.CSS_SELECTOR, ".narrative-explorer-follow-connection").click()
    wait.until(lambda page: page.find_element(By.CSS_SELECTOR, ".narrative-explorer-related-passages"))
    article = _route_article(driver, wait, "jonah-1-17-matthew-12-40-sign-of-jonah")
    assert "Connection to Matthew 12:40" in article.text
    assert "The earlier text is Jonah 1:17; the later passage is Matthew 12:40." in article.text
    assert "Matthew 12:40 explicitly compares" in article.text
    assert "Ancient time reckoning and idiom leave the chronology unsettled" in article.text
    assert not any(token in article.text for token in (
        "ckl:", "source_id", "human_review_required", "Connection type:",
    ))
    assert driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth"), width

    support = article.find_element(By.CSS_SELECTOR, "details")
    support.find_element(By.CSS_SELECTOR, "summary").click()
    support_text = driver.execute_script("return arguments[0].innerText", support)
    assert "Supporting sources" in support_text
    assert "Masoretic Text of Jonah" in support_text
    assert "New Testament sign-of-Jonah passages" in support_text
    before = artifacts_dir / f"jonah-matthew-{label}-route.png"
    assert driver.save_screenshot(str(before))

    _click_related_passage(driver, wait, article, "Matthew 12:40")
    assert driver.execute_script("return window.BHFStudySelection?.getState?.().reference") == "Matthew 12:40"
    wait.until(lambda page: "Matthew 12:40" in page.find_element(
        By.CSS_SELECTOR,
        ".narrative-explorer-header h3",
    ).get_attribute("aria-label"))
    assert "Current passage: Matthew 12:40" not in driver.find_element(By.CSS_SELECTOR, ".narrative-explorer").text
    assert driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth"), width
    after = artifacts_dir / f"jonah-matthew-{label}-destination.png"
    assert driver.save_screenshot(str(after))
    print("ED7_CHROMIUM_CONNECTION=" + json.dumps({
        "browser": browser,
        "source": "Jonah 1:17",
        "destination": "Matthew 12:40",
        "viewport": width,
        "navigation_verified": True,
        "screenshots": [before.name, after.name],
    }, sort_keys=True), flush=True)
