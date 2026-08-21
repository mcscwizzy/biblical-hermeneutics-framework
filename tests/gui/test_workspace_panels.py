from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

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
    wait.until(
        lambda _driver: _driver.execute_script(
            "return window.BHFStudyCompanion.getState().resource === 'ask';"
        )
    )
    page.assert_tab_visible("ask")
    assert page.active_app_section() == "bible"

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
    page.assert_tab_visible("ask")
    assert_split()

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

    metrics = driver.execute_script(
        """
        const output = document.querySelector('[data-testid="answer-output"]');
        output.innerHTML = `
          <article class="answer deterministic-study-result context-presentation">
            <header class="answer-header">
              <div>
                <p class="answer-eyebrow">Validated CKL evidence</p>
                <h2>Full Context for John 1:1</h2>
              </div>
              <div class="answer-actions">
                <button type="button" class="secondary answer-save">Save Study</button>
                <button type="button" class="secondary">Explain with BHF</button>
                <button type="button" class="secondary">Ask a Question</button>
              </div>
            </header>
          </article>`;
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
