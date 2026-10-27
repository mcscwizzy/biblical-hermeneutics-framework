from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage


pytestmark = [pytest.mark.gui]


def _select_verses(driver, wait, book, chapter, verses):
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value(book)
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection?.getState?.().book === arguments[0];",
        book,
    ))
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value(str(chapter))
    wait.until(lambda browser: browser.execute_script(
        "const s=window.BHFStudySelection?.getState?.(); "
        "return s?.book === arguments[0] && s.chapter === Number(arguments[1]);",
        book,
        chapter,
    ))
    driver.execute_script("performance.clearResourceTimings();")
    for verse in verses:
        driver.find_element(
            By.CSS_SELECTOR,
            f'#chapter-reader .reader-pane.is-active [data-verse="{verse}"] [data-verse-select]',
        ).click()
    expected = ",".join(str(verse) for verse in verses)
    wait.until(lambda browser: browser.execute_script(
        "const s=window.BHFStudySelection?.getState?.(); "
        "return s?.book === arguments[0] && s.chapter === Number(arguments[1]) "
        "&& s.selectedVerses?.join(',') === arguments[2];",
        book,
        chapter,
        expected,
    ))


def _connection_action(driver, identity):
    try:
        for card in driver.find_elements(By.CSS_SELECTOR, ".companion-discovery-card"):
            details = card.find_element(By.CSS_SELECTOR, "details")
            driver.execute_script("arguments[0].open = true;", details)
            for button in card.find_elements(By.CSS_SELECTOR, "[data-presentation-action='explore_connection']"):
                actual = {
                    "object_id": button.get_attribute("data-presentation-object-id"),
                    "record_kind": button.get_attribute("data-presentation-record-kind"),
                    "record_id": button.get_attribute("data-presentation-record-id"),
                }
                if actual == identity and button.is_displayed():
                    return card, button
    except StaleElementReferenceException:
        return None
    return None


def _context_identity(driver, record_id):
    return driver.execute_script(
        """
        const context = window.BHFStudyCompanion?.getContext?.();
        const cards = context?.presentation_packet?.cards || [];
        const evidence = (context?.presentation_evidence || []).find(item => item.id === arguments[0]);
        return {
          reference: context?.reference || '',
          cardIds: cards.filter(card => card.type === 'did_you_know').map(card => card.id),
          cited: cards.some(card => (card.evidence_ids || []).includes(arguments[0])),
          identity: evidence?.ckl_record_identity || null,
          claim: evidence?.claim || '',
          sourceIds: (evidence?.sources || []).map(source => source.id),
        };
        """,
        record_id,
    )


def _request_counts(driver):
    return driver.execute_script(
        """
        const entries = performance.getEntriesByType('resource').map(entry => entry.name);
        return {
          companion: entries.filter(name => name.includes('/api/study/companion-context')).length,
          narrativeExplorer: entries.filter(name => name.includes('/api/narrative-explorer/v1/passages/')).length,
        };
        """
    )


def _render_real_projection(driver):
    return driver.execute_async_script(
        """
        const done = arguments[0];
        (async () => {
          const selection = window.BHFStudySelection.getState();
          const context = window.BHFStudyCompanion.getContext();
          const projection = await window.BHFNarrativeExplorer.load(selection);
          const cards = context?.presentation_packet?.cards || [];
          const matches = cards.flatMap(card =>
            window.BHFCompanionDiscoveries.findVerifiedConnections(
              card,
              context,
              projection,
              {narrativeExplorerEnabled: true},
            ).map(route => route.id)
          );
          window.BHFCompanionDiscoveries.render(
            document.querySelector('[data-study-companion]'),
            context,
            {visible: true, narrativeExplorerEnabled: true, verifiedProjection: projection},
          );
          return {
            reference: context?.reference || '',
            relatedState: projection?.related_passages?.state || '',
            queryStatus: projection?.related_passages?.query_status || '',
            authoredRoutes: (projection?.related_passages?.authored_relationships || []).map(route => route.id),
            bridgeRoutes: (projection?.related_passages?.evidence_backed_bridges || []).map(route => route.id),
            matches,
            actionCount: document.querySelectorAll("[data-presentation-action='explore_connection']").length,
          };
        })().then(done).catch(error => done({error: String(error)}));
        """
    )


def _route_article(driver, wait, route_id):
    return wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR,
        f"[data-route-id='{route_id}'][aria-current='true']",
    ))


def _click_related_passage(driver, wait, article, reference):
    button = article.find_element(
        By.CSS_SELECTOR,
        "button[data-narrative-focus-id^='related-passage:']",
    )
    assert reference in button.text
    button.click()
    wait.until(lambda browser: browser.execute_script(
        "const s=window.BHFStudySelection?.getState?.(); "
        "return s?.reference === arguments[0];",
        reference,
    ))


def _return_to_origin(driver, wait, expected_reference, expected_verses):
    return_button = wait.until(lambda browser: (
        browser.find_element(By.CSS_SELECTOR, ".narrative-explorer-return-origin")
        if browser.find_elements(By.CSS_SELECTOR, ".narrative-explorer-return-origin")
        else False
    ))
    return_button.click()
    wait.until(lambda browser: browser.execute_script(
        "const s=window.BHFStudySelection?.getState?.(); "
        "return s?.reference === arguments[0] "
        "&& s.selectedVerses?.join(',') === arguments[1];",
        expected_reference,
        ",".join(str(verse) for verse in expected_verses),
    ))
    trail = driver.execute_script(
        "return window.history.state?.bhfStudyCompanion?.trail || null;"
    )
    assert trail is not None
    assert trail["activeIndex"] == 0
    return trail


def test_real_ckl_jonah_and_matthew_handoffs_preserve_direction_and_return(
    driver,
    base_url,
):
    wait = WebDriverWait(driver, 90)
    driver.set_window_size(1440, 1200)
    HomePage(driver, wait, base_url).open().wait_loaded()

    _select_verses(driver, wait, "Jonah", 1, [17])
    identity = {"object_id": "jonah", "record_kind": "claim", "record_id": "jonah-three-days"}
    source_evidence = wait.until(lambda browser: _context_identity(browser, "jonah-three-days")
        if _context_identity(browser, "jonah-three-days")["cited"] else False)
    assert source_evidence["reference"] == "Jonah 1:17"
    assert len(source_evidence["cardIds"]) <= 3
    assert source_evidence["identity"] == identity
    assert "later becomes important in Matthew 12:40" in source_evidence["claim"]
    assert {"jonah-masoretic", "jonah-new-testament"} <= set(source_evidence["sourceIds"])

    source_card, source_action = wait.until(lambda browser: _connection_action(browser, identity))
    assert "Three days and three nights is a narrated duration" in source_card.text
    assert source_card.find_element(By.CSS_SELECTOR, ".companion-discovery-meta").text
    assert source_action.text == "Explore this connection"
    assert source_action.get_attribute("aria-label") == "Explore this connection"
    source_action.click()
    route_id = "jonah-1-17-matthew-12-40-sign-of-jonah"
    article = _route_article(driver, wait, route_id)
    route_text = article.text.casefold()
    assert "later canonical reception" in route_text
    assert "jonah 1:17 → matthew 12:40" in route_text
    assert "this route can be followed from either passage" in route_text
    details = article.find_element(By.CSS_SELECTOR, ".narrative-explorer-related-passage-details")
    driver.execute_script("arguments[0].open = true;", details)
    details_text = details.text
    assert "ckl:jonah#claim:jonah-three-days" in details_text
    assert "jonah-masoretic" in details_text
    assert "jonah-new-testament" in details_text
    assert "chronology" in details_text.casefold()
    assert "idiom" in details_text.casefold()
    assert "heart of the earth" in details_text.casefold()
    _click_related_passage(driver, wait, article, "Matthew 12:40")
    source_trail = driver.execute_script(
        "return window.history.state?.bhfStudyCompanion?.trail || null;"
    )
    assert source_trail is not None
    assert source_trail["activeIndex"] > 0
    assert {"Jonah 1:17", "Matthew 12:40"} <= {
        node.get("reference") for node in source_trail.get("nodes", [])
    }
    returned_trail = _return_to_origin(driver, wait, "Jonah 1:17", [17])
    assert {"Jonah 1:17", "Matthew 12:40"} <= {
        node.get("reference") for node in returned_trail.get("nodes", [])
    }
    jonah_counts = _request_counts(driver)

    # Start a fresh Companion session so this is a direct Matthew endpoint
    # journey, not a route reached from the Jonah trail above.
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "Matthew", 12, [40])
    reverse_evidence = wait.until(lambda browser: _context_identity(browser, "jonah-three-days")
        if _context_identity(browser, "jonah-three-days")["cited"] else False)
    assert reverse_evidence["reference"] == "Matthew 12:40"
    assert reverse_evidence["identity"] == identity
    _card, reverse_action = wait.until(lambda browser: _connection_action(browser, identity))
    assert reverse_action.text == "Explore this connection", reverse_action.get_attribute("outerHTML")
    reverse_action.click()
    reverse_article = _route_article(driver, wait, route_id)
    direction = reverse_article.find_element(
        By.CSS_SELECTOR,
        ".narrative-explorer-related-passage-direction",
    ).text
    assert "Jonah 1:17 → Matthew 12:40" in direction
    assert "followed from either passage" in direction
    _click_related_passage(driver, wait, reverse_article, "Jonah 1:17")
    reverse_trail = driver.execute_script(
        "return window.history.state?.bhfStudyCompanion?.trail || null;"
    )
    assert reverse_trail is not None
    assert reverse_trail["activeIndex"] > 0
    assert {"Jonah 1:17", "Matthew 12:40"} <= {
        node.get("reference") for node in reverse_trail.get("nodes", [])
    }
    _return_to_origin(driver, wait, "Matthew 12:40", [40])
    matthew_counts = _request_counts(driver)
    print(f"NE11D1 Jonah 1:17 browser request counts: {jonah_counts}")
    print(f"NE11D1 Matthew 12:40 browser request counts: {matthew_counts}")


def test_real_ckl_genesis_john_handoff_is_unchanged(driver, base_url):
    wait = WebDriverWait(driver, 90)
    driver.set_window_size(1440, 1200)
    HomePage(driver, wait, base_url).open().wait_loaded()

    _select_verses(driver, wait, "Genesis", 1, [1, 2, 3, 4, 5])
    identity = {"object_id": "john", "record_kind": "claim", "record_id": "john-logos"}
    genesis_evidence = wait.until(lambda browser: _context_identity(browser, "john-logos")
        if _context_identity(browser, "john-logos")["cited"] else False)
    assert genesis_evidence["reference"] == "Genesis 1:1-5"
    assert genesis_evidence["identity"] == identity
    _card, action = wait.until(lambda browser: _connection_action(browser, identity))
    assert action.text == "Explore this connection"
    action.click()

    route_id = "genesis-1-john-1-creation-word"
    article = _route_article(driver, wait, route_id)
    route_text = article.text.casefold()
    assert "interpretive association" in route_text
    details = article.find_element(By.CSS_SELECTOR, ".narrative-explorer-related-passage-details")
    driver.execute_script("arguments[0].open = true;", details)
    assert "not proof of direct borrowing" in details.text.casefold()
    _click_related_passage(driver, wait, article, "John 1:1-5")
    trail = driver.execute_script(
        "return window.history.state?.bhfStudyCompanion?.trail || null;"
    )
    assert trail is not None
    assert trail["activeIndex"] > 0
    _return_to_origin(driver, wait, "Genesis 1:1-5", [1, 2, 3, 4, 5])
    counts = _request_counts(driver)
    print(f"NE11D1 Genesis 1:1-5 browser request counts: {counts}")


@pytest.mark.parametrize(
    ("book", "chapter", "verses", "reference", "held_route_id"),
    [
        ("Psalms", 22, [1], "Psalms 22:1", "psalm-22-mark-15"),
        (
            "Deuteronomy",
            32,
            [8, 9],
            "Deuteronomy 32:8-9",
            "deuteronomy-32-psalm-82-job-1-divine-assembly",
        ),
    ],
)
def test_real_ckl_negative_controls_have_no_companion_handoff(
    driver,
    base_url,
    book,
    chapter,
    verses,
    reference,
    held_route_id,
):
    wait = WebDriverWait(driver, 90)
    driver.set_window_size(1440, 1200)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, book, chapter, verses)
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion?.getContext?.()?.reference === arguments[0];",
        reference,
    ))

    result = _render_real_projection(driver)

    assert "error" not in result
    assert result["reference"] == reference
    assert result["queryStatus"] == "complete"
    assert result["authoredRoutes"] == []
    assert result["bridgeRoutes"] == []
    assert result["matches"] == []
    assert result["actionCount"] == 0
    assert held_route_id not in result["bridgeRoutes"]
    print(f"NE11D1 {reference} browser request counts: {_request_counts(driver)}")
