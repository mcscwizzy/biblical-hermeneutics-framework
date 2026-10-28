from __future__ import annotations

import os
import socket
import threading
import time

import pytest
import requests
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage


VIEWPORTS = [(320, True), (390, True), (768, False), (1440, False)]


@pytest.fixture(scope="module")
def explorer_disabled_base_url(base_url):
    """Serve the same temporary CKL with the Narrative Explorer flag disabled."""

    original_flag = os.environ.get("BHF_NARRATIVE_EXPLORER_ENABLED")
    os.environ["BHF_NARRATIVE_EXPLORER_ENABLED"] = "0"
    try:
        from bhf_web import app as app_module
        from uvicorn import Config, Server

        app = app_module.create_app()
    finally:
        if original_flag is None:
            os.environ.pop("BHF_NARRATIVE_EXPLORER_ENABLED", None)
        else:
            os.environ["BHF_NARRATIVE_EXPLORER_ENABLED"] = original_flag

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    server = Server(Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    ))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 45
    while time.time() < deadline:
        try:
            response = requests.get(f"{base}/api/health", timeout=2)
            response.raise_for_status()
            if response.json().get("status") == "ok":
                break
        except requests.RequestException:
            time.sleep(0.25)
    else:
        server.should_exit = True
        thread.join(timeout=10)
        raise RuntimeError("Narrative Explorer disabled test server did not become healthy")

    yield base

    server.should_exit = True
    thread.join(timeout=10)


def test_overview_actions_fit_at_supported_widths_with_explorer_enabled(
    driver, base_url, artifacts_dir
):
    wait = WebDriverWait(driver, 90)
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 320, "height": 844, "deviceScaleFactor": 1, "mobile": True,
    })
    HomePage(driver, wait, base_url).open().wait_loaded()
    assert driver.execute_script(
        "return window.BHFRuntimeConfig.narrativeExplorerEnabled;"
    ) is True
    _assert_unselected_save_is_disabled(driver)
    _select_jonah_17_and_open_companion(driver, wait)

    saved = False
    for width, mobile in VIEWPORTS:
        _set_viewport(driver, width, mobile)
        metrics = _measure_actions(driver, artifacts_dir, width, expected_count=4)
        assert metrics["rowScrollWidth"] <= metrics["rowClientWidth"], metrics
        assert metrics["overviewScrollWidth"] <= metrics["overviewClientWidth"], metrics
        assert metrics["documentScrollWidth"] <= metrics["documentClientWidth"], metrics
        assert metrics["buttons"], metrics
        for button in metrics["buttons"]:
            assert button["insideRow"] and button["insideOverview"] and button["insidePanel"], (width, button)
            assert button["horizontalTextOverflow"] is False, (width, button)
            assert button["verticalTextOverflow"] is False, (width, button)
            assert button["accessibleName"], (width, button)
            assert button["height"] >= (44 if width <= 680 else 38), (width, button)
        save_label = "✓ Passage Saved" if saved else "☆ Save Passage"
        assert metrics["labels"] == [
            "＋ Add Note", save_label, "Explore the Narrative", "Compare Translations"
        ], (width, metrics)
        _assert_keyboard_order(driver, expected_count=4)

        if width == 320:
            _exercise_note_and_save_actions(driver, wait)
            saved = True

        _open_and_return_to_overview(driver, wait, "narrative_explorer", "companion-narrative-explorer")
        _open_and_return_to_overview(driver, wait, "translation_comparison", "translation_comparison")
        assert driver.execute_script(
            "return window.BHFStudySelection.getState().reference;"
        ) == "Jonah 1:17"


def test_overview_actions_fit_at_supported_widths_with_explorer_disabled(
    driver, explorer_disabled_base_url, artifacts_dir
):
    wait = WebDriverWait(driver, 90)
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 320, "height": 844, "deviceScaleFactor": 1, "mobile": True,
    })
    HomePage(driver, wait, explorer_disabled_base_url).open().wait_loaded()
    assert driver.execute_script(
        "return window.BHFRuntimeConfig.narrativeExplorerEnabled;"
    ) is False
    _assert_unselected_save_is_disabled(driver)
    _select_jonah_17_and_open_companion(driver, wait)

    for width, mobile in VIEWPORTS:
        _set_viewport(driver, width, mobile)
        metrics = _measure_actions(driver, artifacts_dir, width, expected_count=3, flag="off")
        assert metrics["rowScrollWidth"] <= metrics["rowClientWidth"], metrics
        assert metrics["overviewScrollWidth"] <= metrics["overviewClientWidth"], metrics
        assert metrics["documentScrollWidth"] <= metrics["documentClientWidth"], metrics
        for button in metrics["buttons"]:
            assert button["insideRow"] and button["insideOverview"] and button["insidePanel"], (width, button)
            assert button["horizontalTextOverflow"] is False, (width, button)
            assert button["verticalTextOverflow"] is False, (width, button)
            assert button["accessibleName"], (width, button)
            assert button["height"] >= (44 if width <= 680 else 38), (width, button)
        assert metrics["labels"] == ["＋ Add Note", "☆ Save Passage", "Compare Translations"], (width, metrics)
        _assert_keyboard_order(driver, expected_count=3)


def _set_viewport(driver, width, mobile):
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": width, "height": 844, "deviceScaleFactor": 1, "mobile": mobile,
    })
    WebDriverWait(driver, 10).until(
        lambda browser: browser.execute_script("return window.innerWidth") == width
    )


def _assert_unselected_save_is_disabled(driver):
    button = driver.find_element(By.CSS_SELECTOR, '[data-companion-action="save"]')
    assert not button.is_enabled()
    assert button.get_attribute("aria-disabled") == "true"
    assert button.get_attribute("aria-label") == "Save Passage unavailable; select a verse or passage"


def _select_jonah_17_and_open_companion(driver, wait):
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value("Jonah")
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection?.getState?.().book === 'Jonah';"
    ))
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("1")
    verse = wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR,
        '#chapter-reader .reader-pane.is-active [data-verse="17"] [data-verse-select]',
    ))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", verse)
    verse.click()
    peek = driver.find_element(By.CSS_SELECTOR, '.companion-peek[data-companion-state-control="study"]')
    if peek.is_displayed():
        peek.click()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion?.getContext?.()?.reference === 'Jonah 1:17';"
    ))
    wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR, ".companion-overview-actions"
    ).is_displayed())
    save = driver.find_element(By.CSS_SELECTOR, '[data-companion-action="save"]')
    wait.until(lambda _browser: save.get_attribute("data-save-state") == "not-saved")
    assert save.is_enabled()


def _measure_actions(driver, artifacts_dir, width, expected_count, flag="on"):
    row = driver.find_element(By.CSS_SELECTOR, ".companion-overview-actions")
    driver.execute_script("arguments[0].scrollIntoView({block:'start'});", row)
    assert driver.save_screenshot(str(artifacts_dir / f"ne11d5-actions-{flag}-{width}.png"))
    metrics = driver.execute_script(
        """
        const row = document.querySelector('.companion-overview-actions');
        const overview = row.closest('.companion-overview');
        const panel = row.closest('.study-panel');
        const rect = (element) => {
          const bounds = element.getBoundingClientRect();
          return {left: bounds.left, right: bounds.right, top: bounds.top, bottom: bounds.bottom};
        };
        const rowBounds = rect(row);
        const overviewBounds = rect(overview);
        const panelBounds = rect(panel);
        const overviewLeft = overviewBounds.left + overview.clientLeft;
        const overviewRight = overviewLeft + overview.clientWidth;
        const buttons = [...row.querySelectorAll('button')].filter(button => button.getClientRects().length);
        const measuredButtons = buttons.map(button => {
          const bounds = rect(button);
          return {
            label: button.textContent.trim().replace(/\\s+/g, ' '),
            accessibleName: button.getAttribute('aria-label') || button.textContent.trim(),
            left: bounds.left,
            right: bounds.right,
            top: bounds.top,
            bottom: bounds.bottom,
            height: bounds.bottom - bounds.top,
            insideRow: bounds.left >= rowBounds.left - 0.5 && bounds.right <= rowBounds.right + 0.5,
            insideOverview: bounds.left >= overviewLeft - 0.5 && bounds.right <= overviewRight + 0.5,
            insidePanel: bounds.left >= panelBounds.left - 0.5 && bounds.right <= panelBounds.right + 0.5,
            horizontalTextOverflow: button.scrollWidth > button.clientWidth + 1,
            verticalTextOverflow: button.scrollHeight > button.clientHeight + 1,
          };
        });
        return {
          viewportWidth: innerWidth,
          rowClientWidth: row.clientWidth,
          rowScrollWidth: row.scrollWidth,
          overviewClientWidth: overview.clientWidth,
          overviewScrollWidth: overview.scrollWidth,
          documentClientWidth: document.documentElement.clientWidth,
          documentScrollWidth: document.documentElement.scrollWidth,
          labels: measuredButtons.map(button => button.label),
          buttons: measuredButtons,
          expectedCount: arguments[0],
        };
        """,
        expected_count,
    )
    assert metrics["viewportWidth"] == width, metrics
    assert len(metrics["buttons"]) == expected_count, metrics
    button_bounds = [
        (button["label"], round(button["left"], 1), round(button["right"], 1), round(button["height"], 1))
        for button in metrics["buttons"]
    ]
    print(
        f"NE11D5_ACTION_LAYOUT_{flag}_{width}: "
        f"row={metrics['rowClientWidth']}/{metrics['rowScrollWidth']}px, "
        f"overview={metrics['overviewClientWidth']}/{metrics['overviewScrollWidth']}px, "
        f"document={metrics['documentClientWidth']}/{metrics['documentScrollWidth']}px, "
        f"buttons={button_bounds}",
        flush=True,
    )
    return metrics


def _assert_keyboard_order(driver, expected_count):
    buttons = driver.find_elements(By.CSS_SELECTOR, ".companion-overview-actions button")
    assert len(buttons) == expected_count
    enabled_buttons = [button for button in buttons if button.is_enabled()]
    assert enabled_buttons
    driver.execute_script("arguments[0].focus({preventScroll:true});", enabled_buttons[0])
    ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()
    ActionChains(driver).send_keys(Keys.TAB).perform()
    for index, button in enumerate(enabled_buttons):
        focus = driver.execute_script(
            """
            const button = arguments[0];
            const row = button.closest('.companion-overview-actions');
            const overview = row.closest('.companion-overview');
            const panel = row.closest('.study-panel');
            const bounds = button.getBoundingClientRect();
            const overviewBounds = overview.getBoundingClientRect();
            const panelBounds = panel.getBoundingClientRect();
            const style = getComputedStyle(button);
            const extent = (Number.parseFloat(style.outlineWidth) || 0)
              + Math.max(0, Number.parseFloat(style.outlineOffset) || 0);
            const left = overviewBounds.left + overview.clientLeft;
            const right = left + overview.clientWidth;
            return {
              active: document.activeElement === button,
              visible: button.matches(':focus-visible')
                && style.outlineStyle !== 'none'
                && (Number.parseFloat(style.outlineWidth) || 0) > 0,
              insideOverview: bounds.left - extent >= left - 0.5
                && bounds.right + extent <= right + 0.5,
              insidePanel: bounds.left - extent >= panelBounds.left - 0.5
                && bounds.right + extent <= panelBounds.right + 0.5,
            };
            """,
            button,
        )
        assert focus["active"] and focus["visible"], (index, focus)
        assert focus["insideOverview"] and focus["insidePanel"], (index, focus)
        if index + 1 < len(enabled_buttons):
            ActionChains(driver).send_keys(Keys.TAB).perform()


def _exercise_note_and_save_actions(driver, wait):
    selection = "window.BHFStudySelection.getState().reference"
    assert driver.execute_script(f"return {selection};") == "Jonah 1:17"
    driver.find_element(By.CSS_SELECTOR, '[data-companion-action="note"]').click()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion.getState().resource === 'note';"
    ))
    assert driver.execute_script(f"return {selection};") == "Jonah 1:17"
    driver.find_element(By.CSS_SELECTOR, "[data-companion-back]").click()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion.getState().resource === null;"
    ))

    save = driver.find_element(By.CSS_SELECTOR, '[data-companion-action="save"]')
    wait.until(lambda _browser: save.is_enabled())
    save.click()
    wait.until(lambda _browser: save.get_attribute("data-save-state") == "saved")
    assert "Passage Saved" in save.text
    assert not save.is_enabled()
    assert save.get_attribute("aria-disabled") == "true"
    assert driver.execute_script(f"return {selection};") == "Jonah 1:17"


def _open_and_return_to_overview(driver, wait, resource, selector):
    if selector == "translation_comparison":
        trigger = driver.find_element(
            By.CSS_SELECTOR, "[data-companion-resource='translation_comparison']"
        )
    else:
        trigger = driver.find_element(By.CSS_SELECTOR, f"[data-testid='{selector}']")
    trigger.click()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion.getState().resource === arguments[0];", resource
    ))
    back = driver.find_element(By.CSS_SELECTOR, "[data-companion-back]")
    back.click()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion.getState().resource === null"
        " && !document.querySelector('[data-companion-overview]').hidden"
        " && document.activeElement === arguments[0];",
        trigger,
    ))
