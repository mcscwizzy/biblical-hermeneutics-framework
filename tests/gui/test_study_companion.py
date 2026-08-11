from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .pages import HomePage


pytestmark = [pytest.mark.gui]


def test_mobile_selection_opens_accessible_companion_states(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()

    panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    assert panel.get_attribute("data-companion-state") == "closed"
    dock_labels = driver.execute_script(
        """
        return Array.from(document.querySelectorAll('[data-app-dock] .app-dock-item, [data-app-dock] .app-dock-utility'))
          .filter((item) => item.getClientRects().length)
          .map((item) => ({label: item.querySelector('.app-dock-label')?.textContent.trim(), left: item.getBoundingClientRect().left}))
          .sort((a, b) => a.left - b.left)
          .map((item) => item.label);
        """
    )
    assert dock_labels == ["Bible", "Explore", "My Study", "More"]

    driver.find_element(By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active [data-verse="1"] .verse-text').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "peek")

    shared = driver.execute_script("return window.BHFStudySelection.getState();")
    assert shared["book"] == "John"
    assert shared["chapter"] == 1
    assert shared["selectedVerses"] == [1]
    assert shared["reference"] == "John 1:1"
    assert driver.find_element(By.CSS_SELECTOR, "[data-passage-action-strip]").is_displayed()

    driver.find_element(By.CSS_SELECTOR, '[data-passage-action="explore"]').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")
    overview = driver.find_element(By.CSS_SELECTOR, "[data-companion-overview]")
    overview_debug = driver.execute_script(
        """
        const node = document.querySelector('[data-companion-overview]');
        const panel = document.querySelector('[data-study-companion]');
        return {hidden: node.hidden, display: getComputedStyle(node).display, panelDisplay: getComputedStyle(panel).display, panelVisibility: getComputedStyle(panel).visibility, shellClass: node.parentElement.className};
        """
    )
    assert overview.is_displayed(), overview_debug
    assert driver.find_element(By.CSS_SELECTOR, "#chapter-reader").is_displayed()
    sheet_metrics = driver.execute_script(
        """
        const rect = document.querySelector('[data-study-companion]').getBoundingClientRect();
        return {top: rect.top, bottom: rect.bottom, viewport: window.innerHeight};
        """
    )
    assert sheet_metrics["top"] > 48
    assert sheet_metrics["bottom"] < sheet_metrics["viewport"]

    driver.find_element(By.CSS_SELECTOR, '[data-companion-state-control="full"]').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "full")
    driver.find_element(By.CSS_SELECTOR, '[data-companion-state-control="closed"]').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "closed")


def test_desktop_companion_is_docked_and_routes_resource_details(driver, wait, base_url):
    driver.set_window_size(1440, 1000)
    HomePage(driver, wait, base_url).open().wait_loaded()

    panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")
    assert driver.find_element(By.CSS_SELECTOR, "[data-companion-overview]").is_displayed()
    assert driver.find_element(By.CSS_SELECTOR, "#chapter-reader").is_displayed()
    assert not driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-ask"]').is_displayed()
    assert not driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-archaeology"]').is_displayed()

    metrics = driver.execute_script(
        """
        const reader = document.querySelector('.reader-column').getBoundingClientRect();
        const companion = document.querySelector('[data-study-companion]').getBoundingClientRect();
        return {reader: reader.width, companion: companion.width};
        """
    )
    assert metrics["companion"] > metrics["reader"]

    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-companion-resource="canonical"]'))).click()
    wait.until(lambda _driver: "is-resource-detail" in _driver.find_element(By.CSS_SELECTOR, ".study-companion").get_attribute("class"))
    assert driver.find_element(By.CSS_SELECTOR, "[data-companion-back]").is_displayed()
    assert driver.find_element(By.CSS_SELECTOR, "#chapter-reader").is_displayed()

    driver.find_element(By.CSS_SELECTOR, "[data-companion-back]").click()
    wait.until(lambda _driver: "is-resource-detail" not in _driver.find_element(By.CSS_SELECTOR, ".study-companion").get_attribute("class"))
    assert driver.find_element(By.CSS_SELECTOR, "[data-companion-overview]").is_displayed()


def test_recommendations_differ_by_biblical_genre(driver, wait, base_url):
    driver.set_window_size(1366, 900)
    HomePage(driver, wait, base_url).open().wait_loaded()

    ranked = driver.execute_script(
        """
        const engine = window.BHFStudyRecommendations;
        const available = {commentary: true, word_study: true, maps: true, archaeology: true, people: true, places: true};
        return {
          genesis: engine.rank({book: 'Genesis', hasPassageSelection: true}, available).recommended.map((item) => item.id),
          psalms: engine.rank({book: 'Psalms', hasPassageSelection: true}, available).recommended.map((item) => item.id),
          romans: engine.rank({book: 'Romans', hasPassageSelection: true}, available).recommended.map((item) => item.id),
        };
        """
    )
    assert ranked["genesis"] != ranked["psalms"]
    assert ranked["psalms"] != ranked["romans"]
    assert "literary_context" in ranked["psalms"]
    assert "original_audience" in ranked["romans"]


def test_my_study_consolidates_personal_material(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()

    driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-notes"]').click()
    panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "full")
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#workspace-pane-notes")))

    visible_tabs = [
        tab.text
        for tab in driver.find_elements(By.CSS_SELECTOR, "[data-workspace-tab]")
        if tab.is_displayed()
    ]
    assert visible_tabs == ["Notes", "Highlights", "Saved"]
    assert driver.find_element(By.CSS_SELECTOR, '[data-testid="new-note-panel-button"]').is_displayed()
