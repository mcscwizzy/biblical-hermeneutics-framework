from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from .pages import HomePage, WorkspacePage


pytestmark = [pytest.mark.gui]


def test_workspace_tabs_switch(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = WorkspacePage(driver, wait, base_url)
    tab_bar = lambda: driver.find_element(By.CSS_SELECTOR, "[data-workspace-tab-bar]")

    page.open_app_section("bible")
    wait.until(lambda _driver: page.active_app_section() == "bible")
    page.assert_tab_visible("ask")
    wait.until(lambda _driver: not tab_bar().is_displayed())

    page.open_app_section("notes")
    wait.until(lambda _driver: page.active_app_section() == "notes")
    wait.until(lambda _driver: tab_bar().is_displayed())
    page.open_tab("highlights")
    page.assert_tab_visible("highlights")
    assert page.active_app_section() == "notes"

    page.open_app_section("bible")
    wait.until(lambda _driver: page.active_app_section() == "bible")
    page.assert_tab_visible("ask")
    wait.until(lambda _driver: not tab_bar().is_displayed())

    page.open_app_section("notes")
    wait.until(lambda _driver: page.active_app_section() == "notes")
    page.assert_tab_visible("highlights")
    page.open_tab("notes")
    page.assert_tab_visible("notes")
    assert page.active_app_section() == "notes"

    page.open_app_section("studies")
    wait.until(lambda _driver: page.active_app_section() == "studies")
    page.assert_tab_visible("saved")
    wait.until(lambda _driver: not tab_bar().is_displayed())

    page.open_app_section("explore")
    wait.until(lambda _driver: page.active_app_section() == "explore")
    wait.until(lambda _driver: tab_bar().is_displayed())
    page.open_tab("journey")
    page.assert_tab_visible("journey")
    assert page.active_app_section() == "explore"


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
