from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .pages import HomePage, WorkspacePage


pytestmark = [pytest.mark.gui]


def test_workspace_tabs_switch(driver, wait, base_url):
    driver.set_window_size(1440, 1000)
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = WorkspacePage(driver, wait, base_url)
    tab_bar = lambda: driver.find_element(By.CSS_SELECTOR, "[data-workspace-tab-bar]")
    overview = lambda: driver.find_element(By.CSS_SELECTOR, "[data-companion-overview]")

    page.open_app_section("bible")
    wait.until(lambda _driver: page.active_app_section() == "bible")
    wait.until(lambda _driver: overview().is_displayed())
    assert not tab_bar().is_displayed()

    driver.execute_script("window.BHFStudyCompanion.openResource('ask');")
    ask_dialog = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-ask-bhf-dialog][open]")))
    assert "John 1" in ask_dialog.find_element(By.CSS_SELECTOR, "[data-ask-bhf-reference]").text
    assert not driver.find_elements(By.CSS_SELECTOR, "#workspace-pane-ask")
    assert page.active_app_section() == "bible"
    driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-close]").click()
    wait.until(lambda _driver: not driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-dialog]").get_attribute("open"))

    page.open_app_section("notes")
    wait.until(lambda _driver: page.active_app_section() == "notes")
    wait.until(lambda _driver: tab_bar().is_displayed())
    page.open_tab("highlights")
    page.assert_tab_visible("highlights")
    page.open_tab("saved")
    page.assert_tab_visible("saved")
    assert page.active_app_section() == "notes"

    page.open_app_section("bible")
    wait.until(lambda _driver: page.active_app_section() == "bible")
    wait.until(lambda _driver: overview().is_displayed())
    assert driver.execute_script("return window.BHFStudyCompanion.getState().resource;") is None
    wait.until(lambda _driver: not tab_bar().is_displayed())

    page.open_app_section("notes")
    wait.until(lambda _driver: page.active_app_section() == "notes")
    page.assert_tab_visible("saved")
    page.open_tab("notes")
    page.assert_tab_visible("notes")
    assert page.active_app_section() == "notes"

    page.open_app_section("explore")
    wait.until(lambda _driver: page.active_app_section() == "explore")
    wait.until(lambda _driver: overview().is_displayed())
    assert driver.execute_script("return window.BHFStudyCompanion.getState().mode;") == "explore"
    wait.until(lambda _driver: not tab_bar().is_displayed())


def test_desktop_primary_navigation_preserves_reader_split(driver, wait, base_url):
    driver.set_window_size(1440, 1000)
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = WorkspacePage(driver, wait, base_url)

    def assert_split():
        assert driver.find_element(By.CSS_SELECTOR, '[data-testid="reader-passage"]').is_displayed()
        assert driver.find_element(By.ID, "study-panel").is_displayed()

    page.open_app_section("bible")
    wait.until(lambda _driver: page.active_app_section() == "bible")
    assert_split()

    driver.execute_script("window.BHFStudyCompanion.openResource('ask');")
    ask_dialog = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-ask-bhf-dialog][open]")))
    assert "John 1" in ask_dialog.find_element(By.CSS_SELECTOR, "[data-ask-bhf-reference]").text
    assert not driver.find_elements(By.CSS_SELECTOR, "#workspace-pane-ask")
    assert_split()
    driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-close]").click()
    wait.until(lambda _driver: not driver.find_element(By.CSS_SELECTOR, "[data-ask-bhf-dialog]").get_attribute("open"))

    page.open_app_section("notes")
    wait.until(lambda _driver: page.active_app_section() == "notes")
    page.assert_tab_visible("notes")
    page.open_tab("saved")
    page.assert_tab_visible("saved")
    assert_split()

    page.open_app_section("explore")
    wait.until(lambda _driver: page.active_app_section() == "explore")
    wait.until(
        lambda _driver: _driver.execute_script(
            "return window.BHFStudyCompanion.getState().mode === 'explore';"
        )
    )
    assert_split()


def test_context_result_header_keeps_title_readable_in_study_panel(driver, wait, base_url):
    driver.set_window_size(1440, 1000)
    HomePage(driver, wait, base_url).open().wait_loaded()
    driver.find_element(
        By.CSS_SELECTOR,
        '#chapter-reader .reader-pane.is-active [data-verse="1"] .verse-text',
    ).click()
    open_result = driver.execute_async_script(
        """
        const done = arguments[0];
        window.BHFStudyCompanion.openResource('word_study')
          .then(() => done({ok: true}))
          .catch((error) => done({ok: false, error: String(error)}));
        """
    )
    assert open_result["ok"], open_result
    wait.until(lambda _driver: driver.find_elements(By.CSS_SELECTOR, "#lexicon-panel [data-deterministic-study-result]"))

    # The retired embedded Ask answer host is gone. Exercise the same shared
    # deterministic result header in the current Lexicon output panel.
    metrics = driver.execute_script(
        """
        const output = document.querySelector('#lexicon-panel');
        const header = output.querySelector('.answer-header').getBoundingClientRect();
        const title = output.querySelector('.answer-header > div').getBoundingClientRect();
        const eyebrow = output.querySelector('.answer-eyebrow').getBoundingClientRect();
        return {
          headerWidth: header.width,
          titleWidth: title.width,
          eyebrowHeight: eyebrow.height,
          eyebrowFontSize: parseFloat(getComputedStyle(output.querySelector('.answer-eyebrow')).fontSize),
        };
        """
    )

    assert metrics["titleWidth"] >= min(256, metrics["headerWidth"])
    assert metrics["eyebrowHeight"] <= metrics["eyebrowFontSize"] * 1.5


def test_workspace_expand_and_minimize(driver, wait, base_url):
    driver.set_window_size(1440, 1000)
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = WorkspacePage(driver, wait, base_url)
    page.open_app_section("notes")
    page.assert_tab_visible("notes")
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
