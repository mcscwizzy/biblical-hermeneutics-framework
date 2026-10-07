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
    assert all(
        control.get_attribute("aria-pressed") is None
        for control in panel.find_elements(By.CSS_SELECTOR, "[data-companion-state-control]")
    )
    assert driver.find_element(By.CSS_SELECTOR, ".reader-column").get_attribute("aria-hidden") == "true"
    driver.find_element(By.CSS_SELECTOR, '[data-companion-state-control="closed"]').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "closed")
    closed_spacing = driver.execute_script(
        """
        const actions = document.querySelector('[data-passage-action-strip]').getBoundingClientRect();
        const dock = document.querySelector('[data-app-dock]').getBoundingClientRect();
        return {gap: dock.top - actions.bottom};
        """
    )
    assert 0 <= closed_spacing["gap"] <= 10


def test_mobile_maps_explorer_opens_visible_map_workspace(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()

    driver.find_element(By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active [data-verse="1"] .verse-text').click()
    panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "peek")
    driver.find_element(By.CSS_SELECTOR, '[data-passage-action="explore"]').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")

    driver.find_element(By.CSS_SELECTOR, '[data-companion-route="maps"]').click()
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, '[data-workspace-tab="maps"]').get_attribute("aria-selected") == "true")
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, "#map-panel").is_displayed())
    assert panel.get_attribute("data-companion-state") == "full"

    driver.find_element(By.CSS_SELECTOR, '[data-companion-state-control="closed"]').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "closed")


def test_explore_questions_use_general_scope_instead_of_reader_selection(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()

    driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-explore"]').click()
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudyCompanion.getState().mode === 'explore';"
    ))

    assert driver.find_element(By.CSS_SELECTOR, "#companion-ask-title").text == "Explore BHF"
    quick_ask = driver.find_element(By.CSS_SELECTOR, "#companion-question")
    assert quick_ask.get_attribute("placeholder") == "Search or ask about the Bible…"
    quick_ask.send_keys("Who was Paul?")
    driver.find_element(By.CSS_SELECTOR, "[data-companion-quick-ask] button[type='submit']").click()

    wait.until(lambda _driver: _driver.execute_script(
        "return document.querySelector('.ask-form [name=question_scope]').value === 'general_question';"
    ))
    assert driver.execute_script("return document.body.dataset.appSection;") == "explore"
    assert driver.find_element(By.CSS_SELECTOR, '[data-workspace-tab="ask"]').get_attribute("aria-selected") == "true"
    assert driver.find_element(By.CSS_SELECTOR, "[data-ask-heading]").text == "Explore BHF"
    assert driver.find_element(By.CSS_SELECTOR, '[data-testid="ask-submit"]').text == "Search BHF"


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

    expand = driver.find_element(By.CSS_SELECTOR, '[data-companion-state-control="full"]')
    expand.click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "full")
    expanded_metrics = driver.execute_script(
        """
        const panel = document.querySelector('[data-study-companion]');
        const rect = panel.getBoundingClientRect();
        return {
          position: getComputedStyle(panel).position,
          left: rect.left,
          top: rect.top,
          width: rect.width,
          viewportWidth: window.innerWidth,
          bodyOverflow: getComputedStyle(document.body).overflow,
        };
        """
    )
    assert expanded_metrics["position"] == "fixed"
    assert expanded_metrics["left"] <= 12
    assert expanded_metrics["top"] <= 12
    assert expanded_metrics["width"] >= expanded_metrics["viewportWidth"] - 24
    assert expanded_metrics["bodyOverflow"] == "hidden"
    assert expand.get_attribute("aria-label") == "Collapse Study Companion"

    expand.click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")
    assert driver.execute_script(
        "return getComputedStyle(document.querySelector('[data-study-companion]')).position;"
    ) == "sticky"
    assert expand.get_attribute("aria-label") == "Expand Study Companion"

    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-companion-resource="canonical"]'))).click()
    wait.until(lambda _driver: "is-resource-detail" in _driver.find_element(By.CSS_SELECTOR, ".study-companion").get_attribute("class"))
    back = driver.find_element(By.CSS_SELECTOR, "[data-companion-back]")
    assert back.is_displayed()
    assert back.get_attribute("tabindex") != "-1"
    assert driver.find_element(By.CSS_SELECTOR, "#chapter-reader").is_displayed()

    back.click()
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


def test_bible_reference_follows_selection_while_explore_is_open(driver, wait, base_url):
    driver.set_window_size(1440, 1000)
    HomePage(driver, wait, base_url).open().wait_loaded()

    first_verse = driver.find_element(
        By.CSS_SELECTOR,
        '#chapter-reader .reader-pane.is-active [data-verse="1"] .verse-text',
    )
    first_verse.click()
    reference = driver.find_element(By.CSS_SELECTOR, "[data-passage-action-reference]")
    wait.until(lambda _driver: reference.text == "John 1:1")

    driver.execute_script(
        "window.BHFStudyCompanion.showOverview({mode: 'explore', focus: false, history: false});"
    )
    wait.until(
        lambda _driver: _driver.execute_script(
            "return window.BHFStudyCompanion.getState().mode === 'explore';"
        )
    )

    driver.find_element(
        By.CSS_SELECTOR,
        '#chapter-reader .reader-pane.is-active [data-verse="2"] .verse-text',
    ).click()

    wait.until(lambda _driver: reference.text == "John 1:1-2")
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().reference;"
    ) == "John 1:1-2"


def test_explore_browses_resources_without_a_verse_selection(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    assert driver.execute_script("return window.BHFStudySelection.getState().level;") == "chapter"

    driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-explore"]').click()
    people = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-companion-resource="people"]')))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", people)
    wait.until(
        lambda _driver: _driver.execute_script(
            """
            const resource = arguments[0].getBoundingClientRect();
            const dock = document.querySelector('[data-app-dock]').getBoundingClientRect();
            return resource.bottom <= dock.top;
            """,
            people,
        )
    )
    people.click()
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


def test_native_resource_never_renders_previous_selection_context(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudyCompanion?.getContext?.()?.scope === 'chapter';"
    ))

    driver.execute_script(
        """
        window.__originalCompanionFetch = window.fetch;
        window.BHFCompanionContext.clear();
        window.fetch = async function(url, options = {}) {
          const value = String(url);
          if (!value.includes('/api/study/companion-context')) {
            return window.__originalCompanionFetch(url, options);
          }
          const parsed = new URL(value, window.location.origin);
          const verse = Number(parsed.searchParams.get('verse_start'));
          if (verse === 5) await new Promise((resolve) => setTimeout(resolve, 450));
          const label = verse === 4 ? 'A stale place' : 'B current place';
          return new Response(JSON.stringify({
            reference: `John 1:${verse}`,
            scope: 'passage',
            resources: {maps: {state: 'available', available: true, count: 1}},
            entities: {people: [], places: [], themes: []},
            summaries: {maps: {places: [{id: `place-${verse}`, title: label}], routes: []}},
            subsystems: {},
          }), {status: 200, headers: {'Content-Type': 'application/json'}});
        };
        """
    )
    try:
        driver.execute_script(
            "window.BHFStudySelection.setSelection({book: 'John', chapter: 1, startVerse: 4, endVerse: 4, selectedVerses: [4], selectedText: 'Selection A', translation: 'asv'}, 'stale-resource-test');"
        )
        wait.until(lambda _driver: _driver.execute_script(
            "return window.BHFStudyCompanion.getContext()?.reference === 'John 1:4';"
        ))

        driver.execute_script(
            """
            window.BHFStudySelection.setSelection({book: 'John', chapter: 1, startVerse: 5, endVerse: 5, selectedVerses: [5], selectedText: 'Selection B', translation: 'asv'}, 'stale-resource-test');
            window.BHFStudyCompanion.openResource('maps');
            """
        )
        host = driver.find_element(By.CSS_SELECTOR, "[data-companion-resource-host]")
        wait.until(lambda _driver: "Loading John 1:5 resources" in host.text)
        assert "A stale place" not in host.text
        assert driver.execute_script("return window.BHFStudyCompanion.getContext();") is None

        wait.until(lambda _driver: "B current place" in host.text)
        assert "A stale place" not in host.text
        assert driver.execute_script("return window.BHFStudyCompanion.getContext().reference;") == "John 1:5"
    finally:
        driver.execute_script("window.fetch = window.__originalCompanionFetch;")


def test_save_passage_state_follows_exact_current_selection(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    button = driver.find_element(By.CSS_SELECTOR, '[data-companion-action="save"]')

    def select(verse, text):
        driver.execute_script(
            """
            window.BHFStudySelection.setSelection({
              book: 'John', chapter: 1,
              startVerse: arguments[0], endVerse: arguments[0], selectedVerses: [arguments[0]],
              selectedText: arguments[1], translation: 'asv'
            }, 'save-state-test');
            window.BHFStudyCompanion.showOverview({state: 'study', focus: false, reload: false, history: false});
            """,
            verse,
            text,
        )

    select(33, "Selection A")
    wait.until(lambda _driver: button.is_enabled())
    button.click()
    wait.until(lambda _driver: button.get_attribute("data-saved") == "true")
    assert "Passage Saved" in button.text
    assert button.get_attribute("aria-label") == "John 1:33 is saved"

    select(34, "Selection B")
    wait.until(lambda _driver: button.is_enabled() and button.get_attribute("data-saved") == "false")
    assert button.text == "☆ Save Passage"
    assert "John 1:34 is saved" not in button.get_attribute("aria-label")

    select(33, "Selection A")
    wait.until(lambda _driver: button.get_attribute("data-saved") == "true")
    assert "Passage Saved" in button.text


def test_save_passage_requires_a_verse_or_range_selection(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    button = driver.find_element(By.CSS_SELECTOR, '[data-companion-action="save"]')

    assert driver.execute_script(
        "return window.BHFStudySelection.getState().hasPassageSelection;"
    ) is False
    assert not button.is_enabled()
    assert button.get_attribute("aria-disabled") == "true"
    assert button.get_attribute("aria-label") == "Save Passage unavailable; select a verse or passage"

    driver.execute_script(
        """
        window.BHFStudySelection.setSelection({
          book: 'John', chapter: 1,
          startVerse: 45, endVerse: 45, selectedVerses: [45],
          selectedText: 'Single verse', translation: 'asv'
        }, 'save-selection-test');
        """
    )
    wait.until(lambda _driver: button.get_attribute("data-save-state") == "not-saved")
    assert button.is_enabled()
    assert button.get_attribute("aria-disabled") == "false"

    driver.execute_script(
        """
        window.BHFStudySelection.setSelection({
          book: 'John', chapter: 1,
          startVerse: 45, endVerse: 46, selectedVerses: [45, 46],
          selectedText: 'Verse range', translation: 'asv'
        }, 'save-selection-test');
        """
    )
    wait.until(lambda _driver: button.get_attribute("data-save-state") == "not-saved")
    assert button.is_enabled()
    assert button.get_attribute("aria-label") == "Save John 1:45-46"

    driver.execute_script(
        "window.BHFStudySelection.setChapter({book: 'John', chapter: 1, translation: 'asv'}, 'save-selection-test');"
    )
    wait.until(lambda _driver: not button.is_enabled())
    assert driver.execute_script(
        "return window.BHFStudySelection.getState().hasPassageSelection;"
    ) is False
    assert button.get_attribute("data-save-state") == "not-saved"
    assert button.get_attribute("aria-disabled") == "true"
    assert button.get_attribute("aria-label") == "Save Passage unavailable; select a verse or passage"


def test_saved_passage_empty_and_unavailable_states_are_distinct(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    button = driver.find_element(By.CSS_SELECTOR, '[data-companion-action="save"]')

    driver.execute_script(
        """
        window.BHFStudySelection.setSelection({
          book: 'John', chapter: 2,
          startVerse: 1, endVerse: 1, selectedVerses: [1],
          selectedText: 'Successful empty lookup', translation: 'asv'
        }, 'saved-lookup-test');
        """
    )
    wait.until(lambda _driver: button.get_attribute("data-save-state") == "not-saved")
    assert button.is_enabled()
    assert button.get_attribute("data-saved") == "false"
    assert button.get_attribute("aria-label") == "Save John 2:1"

    driver.execute_script(
        """
        window.__originalSavedLookupRead = window.BHFOfflineDB.readApiResponse;
        window.BHFOfflineDB.readApiResponse = function(url) {
          if (String(url).includes('/api/saved-studies?') && String(url).includes('chapter=3')) {
            return Promise.reject(new Error('lookup unavailable'));
          }
          return window.__originalSavedLookupRead.call(this, url);
        };
        window.BHFStudySelection.setSelection({
          book: 'John', chapter: 3,
          startVerse: 1, endVerse: 1, selectedVerses: [1],
          selectedText: 'Failed lookup', translation: 'asv'
        }, 'saved-lookup-test');
        """
    )
    try:
        wait.until(lambda _driver: button.get_attribute("data-save-state") == "unavailable")
        assert not button.is_enabled()
        assert button.get_attribute("data-saved") == "unknown"
        assert button.get_attribute("aria-busy") == "false"
        assert button.get_attribute("aria-disabled") == "true"
        assert "saved status could not be confirmed" in button.get_attribute("aria-label")
    finally:
        driver.execute_script(
            "window.BHFOfflineDB.readApiResponse = window.__originalSavedLookupRead;"
        )


def test_successful_save_reloads_saved_studies_once(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    button = driver.find_element(By.CSS_SELECTOR, '[data-companion-action="save"]')

    driver.execute_script(
        """
        window.BHFStudySelection.setSelection({
          book: 'John', chapter: 1,
          startVerse: 49, endVerse: 49, selectedVerses: [49],
          selectedText: 'Single reload regression', translation: 'asv'
        }, 'save-reload-test');
        window.BHFStudyCompanion.showOverview({
          state: 'study', focus: false, reload: false, history: false
        });
        """
    )
    wait.until(
        lambda _driver: button.is_displayed()
        and button.is_enabled()
        and button.get_attribute("data-save-state") == "not-saved"
    )

    driver.execute_script(
        """
        window.__originalSavedStudyRead = window.BHFOfflineDB.readApiResponse;
        window.__originalSavedStudyUpsert = window.BHFOfflineDB.upsertOfflineSavedStudy;
        window.__savedStudyReadCount = 0;
        window.__savedStudyUpsertCount = 0;
        window.BHFOfflineDB.readApiResponse = function(url) {
          if (String(url).startsWith('/api/saved-studies?')) window.__savedStudyReadCount += 1;
          return window.__originalSavedStudyRead.call(this, url);
        };
        window.BHFOfflineDB.upsertOfflineSavedStudy = function(payload) {
          window.__savedStudyUpsertCount += 1;
          return window.__originalSavedStudyUpsert.call(this, payload);
        };
        """
    )
    try:
        button.click()
        wait.until(lambda _driver: button.get_attribute("data-save-state") == "saved")
        assert "Passage Saved" in button.text
        counts = driver.execute_script(
            "return {reads: window.__savedStudyReadCount, upserts: window.__savedStudyUpsertCount};"
        )
        assert counts == {"reads": 1, "upserts": 1}
    finally:
        driver.execute_script(
            """
            window.BHFOfflineDB.readApiResponse = window.__originalSavedStudyRead;
            window.BHFOfflineDB.upsertOfflineSavedStudy = window.__originalSavedStudyUpsert;
            """
        )


def test_browser_back_unwinds_resource_then_companion_overview(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")

    driver.find_element(By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active [data-verse="1"] .verse-text').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "peek")
    driver.find_element(By.CSS_SELECTOR, '[data-passage-action="explore"]').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")
    driver.execute_script("window.BHFStudyCompanion.openResource('maps');")
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudyCompanion.getState().resource === 'maps';"
    ))

    driver.back()
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudyCompanion.getState().resource === null;"
    ))
    assert panel.get_attribute("data-companion-state") == "study"
    assert driver.find_element(By.CSS_SELECTOR, "[data-companion-overview]").is_displayed()

    driver.back()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "peek")
    assert driver.current_url.startswith(base_url)


def test_breakpoint_and_orientation_transitions_preserve_resource_and_selection(driver, wait, base_url):
    driver.set_window_size(1024, 768)
    HomePage(driver, wait, base_url).open().wait_loaded()
    panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")

    driver.set_window_size(768, 1024)
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "closed")
    driver.set_window_size(1024, 768)
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")

    driver.execute_script(
        "window.BHFStudySelection.setSelection({book: 'John', chapter: 1, startVerse: 7, endVerse: 7, selectedVerses: [7], selectedText: 'Selection remains', translation: 'asv'}, 'resize-test');"
    )
    driver.execute_script("window.BHFStudyCompanion.openResource('canonical');")
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudyCompanion.getState().resource === 'canonical';"
    ))

    driver.set_window_size(768, 1024)
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "full")
    assert driver.execute_script("return window.BHFStudySelection.getState().reference;") == "John 1:7"
    assert driver.execute_script("return window.BHFStudyCompanion.getState().resource;") == "canonical"

    driver.set_window_size(1024, 768)
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")
    assert driver.execute_script("return window.BHFStudyCompanion.getState().resource;") == "canonical"
    assert driver.execute_script("return window.BHFStudySelection.getState().reference;") == "John 1:7"


def test_companion_context_cache_refreshes_after_explicit_invalidation(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()

    result = driver.execute_async_script(
        """
        const done = arguments[0];
        const selection = {book: 'Romans', chapter: 16, startVerse: 1, endVerse: 1, translation: 'asv'};
        const originalFetch = window.fetch;
        let calls = 0;
        window.fetch = async function(url, options = {}) {
          if (!String(url).includes('/api/study/companion-context')) return originalFetch(url, options);
          calls += 1;
          return new Response(JSON.stringify({
            reference: 'Romans 16:1', scope: 'passage',
            resources: {commentary: {state: 'available', available: true, count: calls}},
            entities: {people: [], places: [], themes: []}, summaries: {}, subsystems: {}
          }), {status: 200, headers: {'Content-Type': 'application/json'}});
        };
        (async () => {
          window.BHFCompanionContext.clear();
          const first = await window.BHFCompanionContext.load(selection);
          const cached = await window.BHFCompanionContext.load(selection);
          window.BHFCompanionContext.invalidate(selection);
          const refreshed = await window.BHFCompanionContext.load(selection);
          window.fetch = originalFetch;
          done({calls, first: first.resources.commentary.count, cached: cached.resources.commentary.count, refreshed: refreshed.resources.commentary.count});
        })().catch((error) => {
          window.fetch = originalFetch;
          done({error: String(error)});
        });
        """
    )
    assert result == {"calls": 2, "first": 1, "cached": 1, "refreshed": 2}


def test_mobile_companion_input_focus_uses_keyboard_safe_layout(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    driver.find_element(By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active [data-verse="1"] .verse-text').click()
    driver.find_element(By.CSS_SELECTOR, '[data-passage-action="explore"]').click()
    quick_ask = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#companion-question")))
    quick_ask.click()
    wait.until(lambda _driver: _driver.execute_script(
        "return document.body.classList.contains('companion-input-focused');"
    ))
    metrics = driver.execute_script(
        """
        const field = arguments[0].getBoundingClientRect();
        const panel = document.querySelector('[data-study-companion]').getBoundingClientRect();
        const dock = document.querySelector('[data-app-dock]');
        return {
          fieldBottom: field.bottom, panelBottom: panel.bottom,
          dockVisibility: getComputedStyle(dock).visibility,
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
        };
        """,
        quick_ask,
    )
    assert metrics["fieldBottom"] <= metrics["panelBottom"] + 1
    assert metrics["dockVisibility"] == "hidden"
    assert metrics["scrollWidth"] <= metrics["clientWidth"]

    driver.find_element(By.CSS_SELECTOR, "[data-companion-quick-ask] button[type='submit']").click()
    wait.until(lambda _driver: _driver.execute_script(
        "return window.BHFStudyCompanion.getState().resource === 'ask';"
    ))
    textarea = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.ask-form [name="question"]')))
    wait.until(lambda _driver: _driver.execute_script("return document.activeElement === arguments[0];", textarea))
    assert driver.find_element(By.CSS_SELECTOR, ".reader-column").get_attribute("inert") is not None


def test_explore_canonical_entity_detail_stays_native(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-explore"]').click()
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-companion-resource="places"]'))).click()
    card = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-companion-resource-host] [data-canonical-id]")))
    expected = card.find_element(By.CSS_SELECTOR, "h4").text
    card.click()
    host = driver.find_element(By.CSS_SELECTOR, "[data-companion-resource-host]")
    wait.until(lambda _driver: expected in host.text and "Back to results" in host.text)
    assert "is-native-resource" in driver.find_element(By.CSS_SELECTOR, ".study-companion").get_attribute("class")
    assert not driver.find_element(By.CSS_SELECTOR, "#workspace-pane-context").is_displayed()

    panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
    driver.find_element(By.CSS_SELECTOR, '[data-companion-state-control="closed"]').click()
    wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "closed")


def test_archaeology_record_opens_its_curated_evidence_detail(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().wait_loaded()
    driver.execute_script(
        """
        window.BHFStudySelection.setSelection({
          book: "John", chapter: 9, startVerse: 7, endVerse: 11,
          selectedVerses: [7, 8, 9, 10, 11], selectedText: "John 9:7-11",
          translation: "KJV", reference: "John 9:7-11", hasPassageSelection: true,
        }, "archaeology-detail-test");
        """
    )
    driver.execute_async_script(
        """
        const done = arguments[arguments.length - 1];
        window.BHFStudyCompanion.openResource("archaeology", {state: "full"})
          .then(() => done())
          .catch((error) => done(String(error)));
        """
    )
    card = wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        '[data-companion-resource-host] [data-archaeology-id="pool-of-siloam"]',
    )))
    card.click()
    host = driver.find_element(By.CSS_SELECTOR, "[data-companion-resource-host]")
    wait.until(lambda _driver: "What you’re looking at" in host.text)
    assert "Pool of Siloam" in host.text
    assert "Related Scripture" in host.text
    assert host.find_element(By.CSS_SELECTOR, "[data-native-resource-back]").is_displayed()


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


def test_tyndale_companion_tab_remains_independent_and_follows_chapter_and_selection(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().assert_shell_visible()
    wait.until(lambda _driver: driver.execute_script("return Boolean(window.BHFCommentary);"))
    driver.execute_script(
        """
        window.__tyndaleRequests = [];
        window.BHFApi.requestJson = async (url) => {
          const value = String(url);
          window.__tyndaleRequests.push(value);
          if (value.endsWith('/3')) return {available: false, reason: 'commentary_not_installed'};
          const chapter = Number(value.match(/\\/(\\d+)$/)?.[1] || 1);
          return {
            available: true, book: 'John', chapter,
            entries: [{
              id: `tyndale-${chapter}`, title: `Tyndale note ${chapter}`,
              kind: 'study_note', body: `Published Tyndale text for ${chapter}.`,
              anchor: {book: 'John', start_chapter: chapter, start_verse: 4, end_chapter: chapter, end_verse: 4},
            }],
            source: {name: 'Tyndale Open Study Notes', attribution: 'Published secondary study notes'},
          };
        };
        """
    )
    tab = driver.find_element(By.CSS_SELECTOR, '[data-workspace-tab="commentary"]')
    driver.execute_script("window.BHFStudyActions.openWorkspaceTab('commentary');")
    wait.until(lambda _driver: tab.get_attribute("aria-selected") == "true")
    result = driver.execute_async_script(
        """
        const done = arguments[0];
        (async () => {
          await window.BHFCommentary.loadChapter('John', 1);
          window.BHFCommentary.focusSelection({book: 'John', chapter: 1, startVerse: 4, endVerse: 4});
          const focused = document.querySelector('[data-commentary-body] .commentary-entry')?.classList.contains('is-focused');
          await window.BHFCommentary.loadChapter('John', 2);
          const chapterTwo = document.querySelector('[data-commentary-body]').textContent;
          await window.BHFCommentary.loadChapter('John', 3);
          const missingDatabase = document.querySelector('[data-commentary-body]').textContent;
          done({focused, chapterTwo, missingDatabase, requests: window.__tyndaleRequests});
        })().catch((error) => done({error: String(error)}));
        """
    )

    assert "error" not in result, result
    assert result["focused"] is True
    assert "Published Tyndale text for 2." in result["chapterTwo"]
    assert "not installed" in result["missingDatabase"].lower()
    assert result["requests"][:3] == [
        "/api/commentary/John/1", "/api/commentary/John/2", "/api/commentary/John/3",
    ]
    assert "/api/commentary/John/4" in result["requests"]
    assert tab.get_attribute("data-workspace-tab") == "commentary"
    assert driver.find_element(By.CSS_SELECTOR, "[data-commentary-panel]").get_attribute("aria-label") == "Tyndale Study Notes"


def test_translation_comparison_reads_cached_bible_text_offline(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().assert_shell_visible()
    wait.until(lambda _driver: driver.execute_script("return Boolean(window.BHFOfflineDB && window.BHFStudySelection);"))
    result = driver.execute_async_script(
        """
        const done = arguments[0];
        (async () => {
          const installed = [{id: 'kjv', abbreviation: 'KJV', name: 'King James Version', installed: true}];
          await window.BHFOfflineDB.cacheApiResponse('/api/translations/installed', {
            translations: installed, sections: {installed}, default_translation: 'kjv',
          });
          Object.defineProperty(navigator, 'onLine', {configurable: true, value: false});
          window.BHFStudySelection.setSelection({
            book: 'John', chapter: 1, translation: 'kjv', selectedVerses: [1],
            startVerse: 1, endVerse: 1, reference: 'John 1:1',
          }, 'offline-comparison-test');
          window.BHFStudyCompanion.showOverview({state: 'study', focus: false, reload: false, history: false});
          await window.BHFStudyActions.perform('compare_translations');
          done({online: navigator.onLine});
        })().catch((error) => done({error: String(error)}));
        """
    )
    assert "error" not in result, result
    wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-companion-resource-host] .translation-comparison-verse-text"))
    )
    comparison = driver.find_element(By.CSS_SELECTOR, ".translation-comparison")
    assert comparison.find_element(By.CSS_SELECTOR, "[data-comparison-reference]").text == "John 1:1"
    assert comparison.find_element(By.CSS_SELECTOR, "[data-comparison-translation='kjv']").text.strip().startswith("KJV")
    assert "Install or import another translation" in comparison.text


def test_bhf_context_compare_translations_opens_translation_comparison_resource(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().assert_shell_visible()
    wait.until(
        lambda _driver: driver.execute_script("return Boolean(window.BHFStudySelection);")
    )
    driver.execute_script(
        "window.BHFStudySelection.setChapter({book: 'John', chapter: 1, translation: 'kjv'}, 'comparison-test');"
    )
    selected_tab = driver.find_element(
        By.CSS_SELECTOR, "[data-workspace-tab][aria-selected='true']"
    ).get_attribute("data-workspace-tab")

    driver.execute_script(
        """
        const card = document.querySelector('[data-bhf-commentary-card]');
        card.hidden = false;
        card.querySelector('[data-bhf-commentary-personal-action="compare_translations"]').click();
        """
    )
    wait.until(
        lambda _driver: driver.execute_script(
            "return window.BHFStudyCompanion.getState().resource === 'translation_comparison';"
        )
    )

    assert driver.find_element(
        By.CSS_SELECTOR, "[data-workspace-tab][aria-selected='true']"
    ).get_attribute("data-workspace-tab") == selected_tab


def _prepare_translation_comparison(driver, selection, translations):
    driver.execute_script(
        """
        const selection = arguments[0];
        const translations = arguments[1];
        const requests = [];
        window.__translationComparisonRequests = requests;
        window.BHFApi.requestJson = async (url) => {
          requests.push(String(url));
          if (String(url).startsWith('/api/translations/installed')) {
            return {translations, sections: {installed: translations}, default_translation: selection.translation};
          }
          if (String(url).startsWith('/api/translations/catalog')) {
            return {translations, sections: {installed: translations}, default_translation: selection.translation};
          }
          if (String(url).startsWith('/api/bible/')) {
            const translationId = new URL(String(url), location.origin).searchParams.get('translation');
            const entry = translations.find((item) => item.id.toLowerCase() === translationId);
            if (!entry?.installed) throw new Error('translation is not installed');
            return {
              book: selection.book,
              chapter: selection.chapter,
              translation: {id: entry.abbreviation || entry.id.toUpperCase(), name: entry.name},
              verses: Array.from({length: 7}, (_item, index) => ({
                book: selection.book, chapter: selection.chapter, verse: index + 1,
                text: `${entry.abbreviation || entry.id.toUpperCase()} verse ${index + 1}`,
              })),
            };
          }
          throw new Error(`Unexpected request: ${url}`);
        };
        window.BHFStudySelection.setSelection(selection, 'translation-comparison-test');
        """,
        selection,
        translations,
    )


def test_translation_comparison_preserves_selected_range_and_reads_unique_installed_text(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().assert_shell_visible()
    wait.until(lambda _driver: driver.execute_script("return Boolean(window.BHFStudySelection);"))
    selection = {
        "book": "John", "chapter": 4, "startVerse": 4, "endVerse": 6,
        "selectedVerses": [4, 5, 6], "selectedText": "selected source text",
        "translation": "kjv", "reference": "John 4:4-6",
    }
    translations = [
        {"id": "asv", "abbreviation": "ASV", "name": "American Standard Version", "installed": True},
        {"id": "kjv", "abbreviation": "KJV", "name": "King James Version", "installed": True},
        {"id": "asv", "abbreviation": "ASV", "name": "Duplicate ASV", "installed": True},
        {"id": "niv", "abbreviation": "NIV", "name": "Not installed", "installed": False},
    ]
    _prepare_translation_comparison(driver, selection, translations)
    before = driver.execute_script("return window.BHFStudySelection.getState();")
    driver.execute_script(
        "document.querySelector('[data-bhf-commentary-card]').hidden = false;"
        "document.querySelector('[data-bhf-commentary-personal-action=compare_translations]').click();"
    )

    host = wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-companion-resource-host] .translation-comparison"))
    )
    rendered = driver.execute_script(
        """
        const root = document.querySelector('.translation-comparison');
        return {
          reference: root.querySelector('[data-comparison-reference]')?.textContent,
          translations: Array.from(root.querySelectorAll('[data-comparison-translation]')).map((node) => ({
            id: node.dataset.comparisonTranslation,
            title: node.querySelector('h4')?.textContent,
            verses: Array.from(node.querySelectorAll('[data-comparison-verse]')).map((verse) => Number(verse.dataset.comparisonVerse)),
          })),
          selection: window.BHFStudySelection.getState(),
          requests: window.__translationComparisonRequests,
        };
        """
    )
    assert host.is_displayed()
    assert rendered["reference"] == "John 4:4-6"
    assert [item["id"] for item in rendered["translations"]] == ["kjv", "asv"]
    assert all(item["verses"] == [4, 5, 6] for item in rendered["translations"])
    assert "King James Version" in rendered["translations"][0]["title"]
    assert "Not installed" not in str(rendered["translations"])
    assert rendered["selection"] == before
    assert any("/api/bible/John/4?translation=kjv" in url for url in rendered["requests"])
    assert any("/api/bible/John/4?translation=asv" in url for url in rendered["requests"])


def test_translation_comparison_shows_chapter_and_single_translation_management_action(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().assert_shell_visible()
    wait.until(lambda _driver: driver.execute_script("return Boolean(window.BHFStudySelection);"))
    selection = {
        "book": "John", "chapter": 4, "translation": "kjv", "selectedVerses": [],
        "reference": "John 4", "level": "chapter",
    }
    translations = [
        {"id": "kjv", "abbreviation": "KJV", "name": "King James Version", "installed": True},
    ]
    _prepare_translation_comparison(driver, selection, translations)
    before = driver.execute_script("return window.BHFStudySelection.getState();")
    driver.execute_script("window.BHFStudyActions.perform('compare_translations');")
    wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-companion-resource-host] .translation-comparison"))
    )

    root = driver.find_element(By.CSS_SELECTOR, ".translation-comparison")
    assert root.find_element(By.CSS_SELECTOR, "[data-comparison-reference]").text == "John 4"
    assert len(root.find_elements(By.CSS_SELECTOR, "[data-comparison-verse]")) == 7
    assert "Install or import another translation" in root.text
    driver.find_element(By.CSS_SELECTOR, "[data-open-translation-management]").click()
    assert driver.find_element(By.CSS_SELECTOR, "[data-translation-selector]").is_displayed()
    assert driver.execute_script("return window.BHFStudySelection.getState();") == before


def test_translation_comparison_mobile_layout_back_navigation_and_focus(driver, wait, base_url):
    driver.set_window_size(390, 844)
    HomePage(driver, wait, base_url).open().assert_shell_visible()
    wait.until(lambda _driver: driver.execute_script("return Boolean(window.BHFStudySelection);"))
    selection = {
        "book": "John", "chapter": 4, "translation": "kjv", "selectedVerses": [4],
        "startVerse": 4, "endVerse": 4, "reference": "John 4:4",
    }
    translations = [
        {"id": "kjv", "abbreviation": "KJV", "name": "King James Version", "installed": True},
    ]
    _prepare_translation_comparison(driver, selection, translations)
    companion_state_before = driver.execute_script(
        "return window.BHFStudyCompanion.getState().state;"
    )
    driver.execute_script(
        """
        window.BHFStudyCompanion.showOverview({state: 'study', focus: false, reload: false, history: false});
        const card = document.querySelector('[data-bhf-commentary-card]');
        card.hidden = false;
        const action = card.querySelector('[data-bhf-commentary-personal-action="compare_translations"]');
        window.__comparisonAction = action;
        action.focus();
        window.__comparisonTriggerHadFocus = document.activeElement === action;
        action.click();
        """
    )
    wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-companion-resource-host] .translation-comparison"))
    )
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".translation-comparison-verse-text"))
    )

    layout = driver.execute_script(
        """
        const host = document.querySelector('[data-companion-resource-host]');
        const text = document.querySelector('.translation-comparison-verse-text');
        return {
          viewportWidth: window.innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          hostOverflowY: getComputedStyle(host).overflowY,
          hostOverflowX: getComputedStyle(host).overflowX,
          textWrap: getComputedStyle(text).overflowWrap,
          verseNumbers: Array.from(document.querySelectorAll('.translation-comparison-verse')).map((verse) => Number(verse.dataset.comparisonVerse)),
          heading: document.querySelector('.translation-comparison-section h4')?.textContent,
        };
        """
    )
    assert layout["documentWidth"] <= layout["viewportWidth"]
    assert layout["hostOverflowY"] == "auto"
    assert layout["hostOverflowX"] == "hidden"
    assert layout["textWrap"] == "anywhere"
    assert layout["verseNumbers"] == [4]
    assert layout["heading"].startswith("KJV")

    driver.find_element(By.CSS_SELECTOR, "[data-companion-back]").click()
    wait.until(
        lambda _driver: driver.execute_script(
            "return window.BHFStudyCompanion.getState().resource === null;"
        )
    )
    assert driver.execute_script(
        "return window.BHFStudyCompanion.getState().state;"
    ) == companion_state_before
    wait.until(
        lambda _driver: driver.execute_script(
            """
            const trigger = window.__comparisonAction;
            const canReturnToTrigger = trigger?.isConnected
              && !trigger.closest('[hidden], [inert]')
              && trigger.getClientRects().length > 0;
            return canReturnToTrigger
              ? document.activeElement === trigger
              : window.BHFStudyCompanion.getState().state === 'peek'
                ? document.activeElement.matches('[data-companion-state-control="study"]')
                : document.activeElement.matches('[data-companion-reference]');
            """
        ),
        message=str(driver.execute_script(
            "return {triggerHadFocus: window.__comparisonTriggerHadFocus, triggerConnected: window.__comparisonAction?.isConnected, activeTag: document.activeElement?.tagName, activeAction: document.activeElement?.dataset?.bhfCommentaryPersonalAction, state: window.BHFStudyCompanion.getState()};"
        )),
    )
