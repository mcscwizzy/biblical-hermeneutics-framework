from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .pages import HomePage


pytestmark = [pytest.mark.gui]


def _drag_sheet(driver, handle, delta_y):
    driver.execute_script(
        """
        const handle = arguments[0];
        const deltaY = arguments[1];
        const rect = handle.getBoundingClientRect();
        const clientX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        const pointerId = 41;
        handle.dispatchEvent(new PointerEvent('pointerdown', {
          bubbles: true, pointerId, pointerType: 'touch', isPrimary: true,
          button: 0, buttons: 1, clientX, clientY: startY,
        }));
        window.dispatchEvent(new PointerEvent('pointermove', {
          bubbles: true, pointerId, pointerType: 'touch', isPrimary: true,
          button: 0, buttons: 1, clientX, clientY: startY + deltaY,
        }));
        window.dispatchEvent(new PointerEvent('pointerup', {
          bubbles: true, pointerId, pointerType: 'touch', isPrimary: true,
          button: 0, buttons: 0, clientX, clientY: startY + deltaY,
        }));
        """,
        handle,
        delta_y,
    )


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
        const available = Object.fromEntries(
          Object.keys(engine.resources).map((id) => [id, {state: 'available', available: true, count: 1}])
        );
        return {
          genesis: engine.rank({book: 'Genesis', hasPassageSelection: true}, available).recommended.map((item) => item.id),
          psalms: engine.rank({book: 'Psalms', hasPassageSelection: true}, available).recommended.map((item) => item.id),
          romans: engine.rank({book: 'Romans', hasPassageSelection: true}, available).recommended.map((item) => item.id),
          explicitOnly: engine.rank(
            {book: 'John', hasPassageSelection: true},
            {resources: {
              commentary: {state: 'available', available: true, count: 2},
              maps: {state: 'unavailable', available: false, count: 0},
            }}
          ).all.map((item) => item.id),
        };
        """
    )
    assert ranked["genesis"] != ranked["psalms"]
    assert ranked["psalms"] != ranked["romans"]
    assert "literary_context" in ranked["psalms"]
    assert "original_audience" in ranked["romans"]
    assert ranked["explicitOnly"] == ["commentary"]


def test_chapter_companion_uses_one_compact_context_request(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()

    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudyCompanion?.getContext?.()?.scope === 'chapter';"
    ))
    chapter_context = driver.execute_script("return window.BHFStudyCompanion.getContext();")
    assert chapter_context["reference"] == "John 1"
    assert all("state" in value and "count" in value for value in chapter_context["resources"].values())

    driver.execute_script(
        """
        window.__companionRequests = [];
        document.addEventListener('bhf:companion-context-request', (event) => {
          window.__companionRequests.push(event.detail.url);
        });
        """
    )
    driver.find_element(By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active [data-verse="2"] .verse-text').click()
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudyCompanion?.getContext?.()?.reference === 'John 1:2';"
    ))
    requests = driver.execute_script("return window.__companionRequests;")
    assert requests == ["/api/study/companion-context?book=John&chapter=1&verse_start=2&verse_end=2&translation=asv"]
    assert "passage_text" not in requests[0]


def test_explore_browses_resources_without_a_verse_selection(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    assert driver.execute_script("return window.BHFStudySelection.getState().level;") == "chapter"

    driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-explore"]').click()
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-companion-resource="people"]'))).click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-companion-resource-host] .companion-detail-body")))

    shell_class = driver.find_element(By.CSS_SELECTOR, ".study-companion").get_attribute("class")
    assert "is-native-resource" in shell_class
    assert "People" in driver.find_element(By.CSS_SELECTOR, "[data-companion-resource-host]").text
    selection = driver.execute_script("return window.BHFStudySelection.getState();")
    assert selection["level"] == "chapter"
    assert selection["selectedVerses"] == []


def test_mobile_sheet_drag_snap_and_non_gesture_controls(driver, wait, base_url):
    from selenium.webdriver.common.keys import Keys

    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    driver.find_element(By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active [data-verse="1"] .verse-text').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "peek")

    peek = driver.find_element(By.CSS_SELECTOR, ".companion-peek")
    _drag_sheet(driver, peek, -430)
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")

    driver.find_element(By.CSS_SELECTOR, ".companion-collapse-button").click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "peek")

    peek = driver.find_element(By.CSS_SELECTOR, ".companion-peek")
    _drag_sheet(driver, peek, -10)
    assert panel.get_attribute("data-companion-state") == "peek"

    peek.click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")
    driver.find_element(By.CSS_SELECTOR, '[data-companion-state-control="full"]').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "full")

    handle = driver.find_element(By.CSS_SELECTOR, ".companion-sheet-handle")
    _drag_sheet(driver, handle, 300)
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")

    overview = driver.find_element(By.CSS_SELECTOR, "[data-companion-overview]")
    scroll_style = driver.execute_script(
        "const style = getComputedStyle(arguments[0]); return {overflowY: style.overflowY, touchAction: style.touchAction};",
        overview,
    )
    assert scroll_style["overflowY"] == "auto"
    assert scroll_style["touchAction"] != "none"

    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "peek")


def test_stale_context_response_cannot_replace_newer_selection(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudyCompanion?.getContext?.()?.scope === 'chapter';"
    ))

    driver.execute_script(
        """
        window.__originalCompanionFetch = window.fetch;
        window.__delayedCompanionRequests = [];
        window.fetch = async function(url, options = {}) {
          const value = String(url);
          if (!value.includes('/api/study/companion-context')) {
            return window.__originalCompanionFetch(url, options);
          }
          const parsed = new URL(value, window.location.origin);
          const verse = Number(parsed.searchParams.get('verse_start'));
          window.__delayedCompanionRequests.push(verse);
          await new Promise((resolve) => setTimeout(resolve, verse === 3 ? 500 : 20));
          return new Response(JSON.stringify({
            reference: `John 1:${verse}`,
            scope: 'passage',
            resources: {commentary: {state: 'available', available: true, count: verse}},
            entities: {people: [], places: [], themes: []},
            summaries: {},
            subsystems: {},
          }), {status: 200, headers: {'Content-Type': 'application/json'}});
        };
        """
    )
    try:
        driver.execute_script(
            "window.BHFStudySelection.setSelection({book: 'John', chapter: 1, startVerse: 3, endVerse: 3, selectedVerses: [3], selectedText: 'All things were made through him.', translation: 'asv'}, 'race-test');"
        )
        wait.until(lambda _driver: 3 in _driver.execute_script("return window.__delayedCompanionRequests;"))
        driver.execute_script(
            "window.BHFStudySelection.setSelection({book: 'John', chapter: 1, startVerse: 14, endVerse: 14, selectedVerses: [14], selectedText: 'The Word became flesh.', translation: 'asv'}, 'race-test');"
        )
        wait.until(lambda _driver: _driver.execute_script(
            "return window.BHFStudyCompanion.getContext()?.reference === 'John 1:14';"
        ))
        driver.execute_async_script("const done = arguments[0]; setTimeout(done, 650);")
        assert driver.execute_script("return window.BHFStudyCompanion.getContext().reference;") == "John 1:14"
    finally:
        driver.execute_script("window.fetch = window.__originalCompanionFetch;")


def test_ask_fields_follow_exact_shared_selection_and_clear_stale_word(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()

    selected = driver.execute_script(
        """
        window.BHFStudySelection.setSelection({
          book: 'John', chapter: 1,
          startVerse: 1, endVerse: 2,
          selectedVerses: [1, 2],
          selectedText: 'Exact current selection',
          translation: 'kjv',
          selectedWord: {surfaceForm: 'Word', lemma: 'logos', strongsNumber: 'G3056', wordPosition: 4},
        }, 'ask-sync-test');
        window.BHFStudyActions.syncAskSelection();
        const form = document.querySelector('.ask-form');
        return Object.fromEntries([
          'reader_book', 'reader_chapter', 'reader_start_verse', 'reader_end_verse',
          'reader_selected_verses', 'reader_selected_text', 'reader_selected_word', 'reader_translation'
        ].map((name) => [name, form.elements[name].value]));
        """
    )

    assert selected == {
        "reader_book": "John",
        "reader_chapter": "1",
        "reader_start_verse": "1",
        "reader_end_verse": "2",
        "reader_selected_verses": "[1,2]",
        "reader_selected_text": "Exact current selection",
        "reader_selected_word": '{"surfaceForm":"Word","lemma":"logos","strongsNumber":"G3056","wordPosition":4}',
        "reader_translation": "kjv",
    }

    cleared = driver.execute_script(
        """
        window.BHFStudySelection.setChapter({book: 'John', chapter: 2, translation: 'asv'}, 'ask-sync-test');
        window.BHFStudyActions.syncAskSelection();
        const form = document.querySelector('.ask-form');
        return Object.fromEntries([
          'reader_book', 'reader_chapter', 'reader_start_verse', 'reader_end_verse',
          'reader_selected_verses', 'reader_selected_text', 'reader_selected_word', 'reader_translation'
        ].map((name) => [name, form.elements[name].value]));
        """
    )
    assert cleared == {
        "reader_book": "John",
        "reader_chapter": "2",
        "reader_start_verse": "",
        "reader_end_verse": "",
        "reader_selected_verses": "",
        "reader_selected_text": "",
        "reader_selected_word": "",
        "reader_translation": "asv",
    }


def test_word_study_choice_updates_and_restores_shared_selection(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    driver.find_element(
        By.CSS_SELECTOR,
        '#chapter-reader .reader-pane.is-active [data-verse="1"] .verse-text',
    ).click()

    result = driver.execute_async_script(
        """
        const done = arguments[0];
        window.BHFStudyCompanion.openResource('word_study')
          .then(() => done({ok: true}))
          .catch((error) => done({ok: false, error: String(error)}));
        """
    )
    assert result["ok"], result
    choice = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-word-study-position]")))
    choice.click()
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudySelection.getState().level === 'word';"
    ))
    selected_word = driver.execute_script("return window.BHFStudySelection.getState().selectedWord;")
    assert selected_word["wordPosition"] > 0
    assert selected_word["surfaceForm"]

    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-word-study-back]"))).click()
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudySelection.getState().level === 'verse';"
    ))
    assert driver.execute_script("return window.BHFStudySelection.getState().selectedWord;") is None


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
