from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from .pages import HomePage, WorkspacePage


pytestmark = [pytest.mark.gui]


def test_workspace_tabs_switch(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = WorkspacePage(driver, wait, base_url)
    tabs = ["ask", "notes", "highlights", "saved", "maps", "journey"]
    expected_sections = {
        "ask": "ask",
        "notes": "notes",
        "highlights": "studies",
        "saved": "studies",
        "maps": "explore",
        "journey": "explore",
    }
    for name in tabs:
        page.open_tab(name)
        page.assert_tab_visible(name)
        active_section = driver.find_element(By.CSS_SELECTOR, "[data-app-section][aria-pressed='true']")
        assert active_section.get_attribute("data-app-section") == expected_sections[name]
        for other in tabs:
            tab = driver.find_element(By.CSS_SELECTOR, f'[data-testid="{other}-tab"]')
            pane = driver.find_element(By.CSS_SELECTOR, f"#workspace-pane-{other}")
            if other == name:
                assert pane.is_displayed()
                assert tab.get_attribute("aria-selected") == "true"
            else:
                assert tab.get_attribute("aria-selected") == "false"
                assert not pane.is_displayed()


def test_app_dock_desktop_preserves_reader_split(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = WorkspacePage(driver, wait, base_url)

    expected_tabs = {
        "ask": "ask",
        "notes": "notes",
        "studies": "saved",
        "explore": "maps",
    }
    for section, tab_name in expected_tabs.items():
        page.open_app_section(section)
        wait.until(lambda _driver: page.active_app_section() == section)
        page.assert_tab_visible(tab_name)
        assert driver.find_element(By.CSS_SELECTOR, '[data-testid="reader-passage"]').is_displayed()
        assert driver.find_element(By.ID, "study-panel").is_displayed()


def test_workspace_expand_and_minimize(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = WorkspacePage(driver, wait, base_url)
    page.toggle_expand_workspace()
    assert "workspace-expanded" in driver.find_element(By.TAG_NAME, "body").get_attribute("class")
    page.toggle_expand_workspace()
    assert "workspace-expanded" not in driver.find_element(By.TAG_NAME, "body").get_attribute("class")


def test_dark_mode_reader_mode(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = WorkspacePage(driver, wait, base_url)
    page.toggle_dark_mode()
    assert driver.execute_script("return document.documentElement.dataset.theme") == "dark"
    page.toggle_reader_mode()
    assert "reader-mode" in driver.find_element(By.TAG_NAME, "body").get_attribute("class")
