from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .pages import AskPage, BibleReaderPage, HomePage, WorkspacePage


pytestmark = [pytest.mark.gui]


def _set_mobile_viewport(driver):
    driver.set_window_size(390, 844)


def _scroll_to_center(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)


def _hidden_or_absent(driver, selector: str) -> bool:
    elements = driver.find_elements(By.CSS_SELECTOR, selector)
    return not elements or not elements[0].is_displayed()


def _click_context_action(driver, wait, action: str):
    button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-context-action="{action}"]')))
    if not button.is_displayed():
        trigger = button.find_element(By.XPATH, "ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' context-menu-section ')][1]//*[@data-context-submenu]")
        trigger.click()
        wait.until(lambda _driver: button.is_displayed())
    driver.execute_script(
        """
        const button = arguments[0];
        const menu = button.closest("#reader-context-menu");
        if (menu) {
          menu.scrollTop = button.offsetTop - Math.max(0, (menu.clientHeight - button.offsetHeight) / 2);
        }
        """,
        button,
    )
    wait.until(lambda _driver: button.is_displayed() and button.is_enabled())
    button.click()


def _assert_mobile_context_menu_leaves_room_for_submenu(driver, wait):
    menu = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#reader-context-menu")))
    trigger = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-context-submenu="reference"]')))
    trigger.click()
    submenu = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[aria-label="Reference actions"]')))
    rects = driver.execute_script(
        """
        const menu = arguments[0].getBoundingClientRect();
        const submenu = arguments[1].getBoundingClientRect();
        return {
          menu: { left: menu.left, right: menu.right },
          submenu: { left: submenu.left, right: submenu.right },
          viewportWidth: window.innerWidth,
          opensLeft: arguments[0].classList.contains("opens-left")
        };
        """,
        menu,
        submenu,
    )
    assert rects["menu"]["left"] <= 12
    assert rects["submenu"]["left"] >= rects["menu"]["right"] - 4
    assert rects["submenu"]["right"] <= rects["viewportWidth"] - 8
    assert rects["opensLeft"] is False


def test_mobile_branding_and_header_controls_are_compact(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()

    assert "BHF Bible Reader" in driver.title
    assert "BHF Bible Reader" in driver.find_element(By.CSS_SELECTOR, '[data-testid="app-title"]').text
    assert "BHF ASV Reader" not in driver.find_element(By.TAG_NAME, "body").text
    assert driver.find_element(By.CSS_SELECTOR, '[data-testid="app-subtitle"]').is_displayed()
    assert "Read Scripture. Explore context. Ask deeper questions." in driver.find_element(By.CSS_SELECTOR, '[data-testid="app-subtitle"]').text
    assert _hidden_or_absent(driver, '[data-testid="desktop-reader-controls-trigger"]')
    assert _hidden_or_absent(driver, '[data-testid="theme-toggle"]')
    assert _hidden_or_absent(driver, '[data-testid="reader-mode-toggle"]')
    assert _hidden_or_absent(driver, '[data-testid="workspace-expand-toggle"]')
    assert _hidden_or_absent(driver, '[data-testid="workspace-drawer-toggle"]')


def test_mobile_reader_controls_are_compact_and_search_clear_is_contextual(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()

    layout = driver.execute_script(
        """
        const book = document.querySelector('[data-testid="book-select"]').getBoundingClientRect();
        const chapter = document.querySelector('[data-testid="chapter-input"]').getBoundingClientRect();
        return {
          bookTop: book.top,
          chapterTop: chapter.top,
          bookRight: book.right,
          chapterRight: chapter.right,
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth
        };
        """
    )
    assert abs(layout["bookTop"] - layout["chapterTop"]) <= 2
    assert layout["bookRight"] < layout["chapterRight"]
    assert layout["scrollWidth"] <= layout["clientWidth"]

    search_input = driver.find_element(By.CSS_SELECTOR, '[data-testid="bible-search-input"]')
    clear_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="bible-search-clear"]')
    assert search_input.get_attribute("placeholder") == "Search Scripture"
    assert not clear_button.is_displayed()

    search_input.send_keys("beginning")
    wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, '[data-testid="bible-search-clear"]').is_displayed())


def test_mobile_reader_settings_sheet_controls_existing_state(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()

    trigger = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="reader-controls-trigger"]')))
    assert trigger.is_displayed()
    trigger.click()
    sheet = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#reader-controls-sheet[open]")))
    assert "Settings" in sheet.text
    assert "Appearance" in sheet.text
    assert "Reader mode" in sheet.text
    assert "Expand workspace" not in sheet.text

    sheet.find_element(By.CSS_SELECTOR, '[data-testid="mobile-theme-toggle"]').click()
    wait.until(lambda _driver: _driver.execute_script("return document.documentElement.dataset.theme") == "dark")
    wait.until(lambda _driver: not _driver.find_element(By.ID, "reader-controls-sheet").is_displayed())
    assert driver.execute_script("return document.activeElement === arguments[0];", trigger)

    trigger.click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#reader-controls-sheet[open]")))
    driver.find_element(By.CSS_SELECTOR, '[data-testid="mobile-reader-mode-toggle"]').click()
    wait.until(lambda _driver: "reader-mode" in _driver.find_element(By.TAG_NAME, "body").get_attribute("class"))

    page = WorkspacePage(driver, wait, base_url)
    page.open_app_section("ask")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "ask")
    page.assert_tab_visible("ask")
    page.open_tab("context")
    page.assert_tab_visible("context")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "ask")
    workspace_toggle = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="workspace-expand-toggle"]')))
    assert workspace_toggle.is_enabled()
    workspace_toggle.click()
    wait.until(lambda _driver: "workspace-expanded" in _driver.find_element(By.TAG_NAME, "body").get_attribute("class"))


def test_mobile_passage_heading_updates_with_translation_badge(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = BibleReaderPage(driver, wait, base_url)

    wait.until(lambda _driver: "John 1" in _driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
    assert driver.find_element(By.CSS_SELECTOR, ".reader-translation-badge").text == "ASV"

    page.select_book("Genesis")
    wait.until(lambda _driver: "Genesis 1" in _driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
    page.set_chapter(2)
    wait.until(lambda _driver: "Genesis 2" in _driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
    assert driver.find_element(By.CSS_SELECTOR, ".reader-translation-badge").text == "ASV"


@pytest.mark.parametrize(
    ("width", "height", "is_phone"),
    [
        (320, 740, True),
        (375, 812, True),
        (390, 844, True),
        (430, 932, True),
        (768, 1024, False),
        (1440, 1000, False),
    ],
)
def test_reader_responsive_widths_do_not_overflow(driver, wait, base_url, width, height, is_phone):
    driver.set_window_size(width, height)
    HomePage(driver, wait, base_url).open().wait_loaded()

    metrics = driver.execute_script(
        """
        const book = document.querySelector('[data-testid="book-select"]').getBoundingClientRect();
        const chapter = document.querySelector('[data-testid="chapter-input"]').getBoundingClientRect();
        const verse = document.querySelector('#chapter-reader [data-verse="1"]').getBoundingClientRect();
        const dock = document.querySelector('[data-app-dock]').getBoundingClientRect();
        return {
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          bookTop: book.top,
          chapterTop: chapter.top,
          verseTop: verse.top,
          dockTop: dock.top,
          viewportHeight: window.innerHeight
        };
        """
    )
    assert metrics["scrollWidth"] <= metrics["clientWidth"]
    assert metrics["dockTop"] >= 0

    if is_phone:
        assert abs(metrics["bookTop"] - metrics["chapterTop"]) <= 2
        assert metrics["verseTop"] < metrics["viewportHeight"]
        assert _hidden_or_absent(driver, '[data-testid="desktop-reader-controls-trigger"]')
        assert _hidden_or_absent(driver, '[data-testid="theme-toggle"]')
        assert driver.find_element(By.CSS_SELECTOR, '[data-testid="reader-controls-trigger"]').is_displayed()
    else:
        assert _hidden_or_absent(driver, '[data-testid="desktop-reader-controls-trigger"]')
        assert driver.find_element(By.CSS_SELECTOR, '[data-testid="reader-controls-trigger"]').is_displayed()


def test_app_dock_hides_at_page_bottom_on_mobile(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#chapter-reader [data-verse="1"]')))

    driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
    wait.until(lambda _driver: _driver.execute_script("return document.body.classList.contains('app-dock-hidden-at-bottom')"))
    wait.until(
        lambda _driver: _driver.execute_script(
            """
            const dock = document.querySelector('[data-app-dock]').getBoundingClientRect();
            return dock.top >= window.innerHeight - 1;
            """
        )
    )

    bottom_metrics = driver.execute_script(
        """
        const dock = document.querySelector('[data-app-dock]');
        const dockRect = dock.getBoundingClientRect();
        const verses = Array.from(document.querySelectorAll('#chapter-reader [data-verse]'));
        const lastVerse = verses[verses.length - 1].getBoundingClientRect();
        return {
          dockTop: dockRect.top,
          dockHidden: dock.getAttribute('aria-hidden'),
          dockInert: dock.hasAttribute('inert'),
          lastVerseBottom: lastVerse.bottom,
          viewportHeight: window.innerHeight
        };
        """
    )
    assert bottom_metrics["dockTop"] >= bottom_metrics["viewportHeight"] - 1
    assert bottom_metrics["dockHidden"] == "true"
    assert bottom_metrics["dockInert"] is True
    assert bottom_metrics["lastVerseBottom"] < bottom_metrics["viewportHeight"]

    driver.execute_script("window.scrollTo(0, 0);")
    wait.until(lambda _driver: not _driver.execute_script("return document.body.classList.contains('app-dock-hidden-at-bottom')"))
    wait.until(
        lambda _driver: _driver.execute_script(
            """
            const dock = document.querySelector('[data-app-dock]').getBoundingClientRect();
            return dock.bottom <= window.innerHeight + 1;
            """
        )
    )


def test_app_dock_switches_between_bible_and_ask_on_mobile(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()

    page = WorkspacePage(driver, wait, base_url)
    assert page.find('[data-testid="app-dock-bible"]').is_displayed()

    page.open_app_section("ask")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "ask")
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="question-input"]')))
    assert page.find("#study-panel").is_displayed()

    page.open_app_section("bible")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "bible")
    wait.until(lambda _driver: not _driver.find_element(By.ID, "study-panel").is_displayed())


@pytest.mark.parametrize(("width", "height"), [(280, 640), (390, 844), (1440, 1000)])
def test_app_dock_uses_labeled_groups(driver, wait, base_url, width, height):
    driver.set_window_size(width, height)
    HomePage(driver, wait, base_url).open().wait_loaded()

    dock = driver.find_element(By.CSS_SELECTOR, "[data-app-dock]")
    note_button = dock.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-notes"]')
    metrics = driver.execute_script(
        """
        const dock = arguments[0].getBoundingClientRect();
        const button = arguments[1].getBoundingClientRect();
        return { dockHeight: dock.height, buttonWidth: button.width };
        """,
        dock,
        note_button,
    )

    assert note_button.get_attribute("aria-label") == "Notes"
    assert note_button.find_element(By.CSS_SELECTOR, "svg.app-dock-icon").is_displayed()
    assert note_button.text == "Notes"
    assert metrics["dockHeight"] <= 78
    assert metrics["buttonWidth"] > 42
    assert [label.text for label in dock.find_elements(By.CSS_SELECTOR, ".app-dock-group-label")] == [
        "Read", "Study", "Explore", "App"
    ]

    if width < 900:
        scroll_metrics = driver.execute_script(
            """
            const dock = arguments[0];
            dock.scrollLeft = dock.scrollWidth;
            return {
              clientWidth: dock.clientWidth,
              scrollLeft: dock.scrollLeft,
              scrollWidth: dock.scrollWidth,
            };
            """,
            dock,
        )
        assert scroll_metrics["scrollWidth"] > scroll_metrics["clientWidth"]
        assert scroll_metrics["scrollLeft"] > 0


def test_mobile_ask_submit_still_works(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()

    page = WorkspacePage(driver, wait, base_url)
    page.open_app_section("ask")
    question = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="question-input"]')))
    question.clear()
    question.send_keys("What does John 1 emphasize?")
    page.click('[data-testid="ask-submit"]')
    AskPage(driver, wait, base_url).wait_for_status_started()
    wait.until(lambda _driver: "Test answer" in _driver.find_element(By.CSS_SELECTOR, '[data-testid="answer-output"]').text)


def test_mobile_verse_actions_support_notes_and_highlights(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()

    page = WorkspacePage(driver, wait, base_url)
    page.open_app_section("bible")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "bible")

    verse_one = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#chapter-reader [data-verse="1"]')))
    action_button = verse_one.find_element(By.CSS_SELECTOR, "[data-verse-actions]")
    assert action_button.is_displayed()
    assert action_button.text == "⋮"
    assert action_button.get_attribute("aria-label") == "Verse actions"

    _scroll_to_center(driver, action_button)
    action_button.click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#reader-context-menu")))
    _assert_mobile_context_menu_leaves_room_for_submenu(driver, wait)
    _click_context_action(driver, wait, "note")
    note_editor = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="note-editor"]')))
    textarea = note_editor.find_element(By.CSS_SELECTOR, '[data-testid="note-textarea"]')
    textarea.clear()
    textarea.send_keys("Mobile note for John 1")
    page.click('[data-testid="save-note-button"]')
    wait.until(lambda _driver: "Mobile note for John 1" in _driver.find_element(By.CSS_SELECTOR, "#notes-list").text)

    page.open_app_section("bible")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "bible")
    verse_one = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#chapter-reader [data-verse="1"]')))
    action_button = verse_one.find_element(By.CSS_SELECTOR, "[data-verse-actions]")
    _scroll_to_center(driver, action_button)
    action_button.click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#reader-context-menu")))
    _click_context_action(driver, wait, "highlight")
    wait.until(lambda _driver: "highlight-yellow" in _driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"]').get_attribute("class"))


def test_app_dock_remembers_group_subtabs_on_mobile(driver, wait, base_url):
    _set_mobile_viewport(driver)
    HomePage(driver, wait, base_url).open().wait_loaded()

    page = WorkspacePage(driver, wait, base_url)
    tab_bar = lambda: driver.find_element(By.CSS_SELECTOR, "[data-workspace-tab-bar]")

    page.open_app_section("notes")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "notes")
    wait.until(lambda _driver: tab_bar().is_displayed())
    page.open_tab("highlights")
    page.open_app_section("bible")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "bible")
    page.open_app_section("notes")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "notes")
    page.assert_tab_visible("highlights")
    page.open_tab("notes")
    page.open_app_section("bible")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "bible")
    page.open_app_section("notes")
    page.assert_tab_visible("notes")

    page.open_app_section("explore")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "explore")
    page.assert_tab_visible("maps")
    wait.until(lambda _driver: not tab_bar().is_displayed())
    page.open_app_section("bible")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "bible")
    page.open_app_section("explore")
    page.assert_tab_visible("maps")

    page.open_app_section("studies")
    wait.until(lambda _driver: _driver.execute_script("return document.body.dataset.appSection") == "studies")
    page.assert_tab_visible("saved")
    wait.until(lambda _driver: not tab_bar().is_displayed())
