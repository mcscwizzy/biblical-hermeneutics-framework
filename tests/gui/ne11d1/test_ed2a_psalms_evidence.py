from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select

from tests.gui.pages import HomePage
from tests.gui.viewport import set_viewport


pytestmark = [pytest.mark.gui]


CASES = [
    (
        "Psalm 145 textual witness",
        145,
        [13],
        "psalm-145-nun-verse-witness",
        "archaeology_ancient_history",
        "Psalm 145:13",
        "sanders-11qpsa-1965",
        "Manuscript/textual witness",
    ),
    (
        "Psalm 44 communal lament",
        44,
        [23],
        "psalm-44-communal-lament-and-book-context",
        "themes_biblical_connections",
        "Psalm 44:1-26",
        "verde-psalms-trauma-2022",
        "Scholarly interpretation",
    ),
]


def _select_passage_verses(driver, wait, book, chapter, verses):
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
    for verse in verses:
        element = driver.find_element(
            By.CSS_SELECTOR,
            f'#chapter-reader .reader-pane.is-active [data-verse="{verse}"] [data-verse-select]',
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();",
            element,
        )
    expected = ",".join(str(verse) for verse in verses)
    wait.until(lambda browser: browser.execute_script(
        "const s=window.BHFStudySelection?.getState?.(); "
        "return s?.book === arguments[0] && s.chapter === Number(arguments[1]) "
        "&& s.selectedVerses?.join(',') === arguments[2];",
        book,
        chapter,
        expected,
    ))


@pytest.mark.parametrize(
    ("width", "height", "mobile", "device"),
    [(1440, 1200, False, "desktop"), (390, 844, True, "mobile")],
    ids=["desktop", "mobile"],
)
@pytest.mark.parametrize(
    ("case", "chapter", "verses", "evidence_id", "section_id", "anchor", "source_id", "label"),
    CASES,
    ids=["psalm145", "psalm44"],
)
def test_psalms_evidence_is_contextual_scoped_traceable_and_readable(
    driver,
    ne11d1_base_url,
    artifacts_dir,
    width,
    height,
    mobile,
    device,
    case,
    chapter,
    verses,
    evidence_id,
    section_id,
    anchor,
    source_id,
    label,
):
    set_viewport(driver, width, height, mobile)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    _select_passage_verses(driver, wait, "Psalms", chapter, verses)
    peek = driver.find_element(By.CSS_SELECTOR, '.companion-peek[data-companion-state-control="study"]')
    if peek.is_displayed():
        peek.click()
    wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR,
        ".companion-overview-actions",
    ).is_displayed())
    explorer_button = wait.until(lambda browser: next(
        (button for button in browser.find_elements(
            By.CSS_SELECTOR,
            '[data-testid="companion-narrative-explorer"]',
        ) if button.is_displayed()),
        False,
    ))
    explorer_button.click()
    explorer = wait.until(lambda browser: browser.find_element(By.CSS_SELECTOR, ".narrative-explorer"))
    section_card = explorer.find_element(By.CSS_SELECTOR, f'[data-section-id="{section_id}"]')
    assert section_card.is_displayed(), case
    section_card.click()

    section = wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR,
        f'.narrative-explorer-section[data-section-id="{section_id}"]',
    ))
    browse = section.find_element(By.CSS_SELECTOR, ".narrative-explorer-inspect")
    browse.click()
    projected_id = f"ckl:psalms#evidence:{evidence_id}"
    selector = f'button[data-narrative-item-id="{projected_id}"]'

    def locate_item(browser):
        matches = [
            item for item in browser.find_elements(By.CSS_SELECTOR, selector)
            if item.is_displayed()
        ]
        if matches:
            return matches[0]
        more = browser.find_elements(By.CSS_SELECTOR, ".narrative-explorer-more")
        if more and more[0].is_displayed():
            more[0].click()
        return False

    evidence_button = wait.until(locate_item)
    record = evidence_button.find_element(
        By.XPATH,
        "./ancestor::article[contains(@class, 'narrative-explorer-item')]",
    )
    item_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
    assert len([item for item in item_buttons if item.is_displayed()]) == 1
    assert label in record.find_element(By.CSS_SELECTOR, ".narrative-explorer-item-kind").text
    assert (
        "Some conclusions about this evidence remain unsettled." in record.text
        or "Interpretation status is disputed." in record.text
        or "Textual variant" in record.text
    )

    provenance = record.find_element(By.CSS_SELECTOR, ".narrative-explorer-provenance")
    summary = provenance.find_element(By.CSS_SELECTOR, "summary")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", summary)
    summary.click()
    rationale = provenance.find_element(By.CSS_SELECTOR, ".narrative-explorer-recorded-rationale")
    driver.execute_script(
        "arguments[0].open = true;",
        rationale,
    )
    provenance_text = provenance.text
    assert f"Projected source identity: {projected_id}" in provenance_text
    assert f"Evidence ID: {evidence_id}" in provenance_text
    assert f"Passage relationship: {anchor}" in provenance_text
    assert source_id in provenance_text
    assert "Primary Observation" in provenance_text
    assert "Scholarly Interpretation" in provenance_text
    assert "Confidence:" in provenance_text
    assert "Dispute status:" in provenance_text
    assert "Review status: in_review" in provenance_text
    assert "Content status: draft" in provenance_text
    assert "Human review required: Yes" in provenance_text

    if chapter == 145:
        assert "rahlfs-hanhart-septuaginta-2006" in provenance_text
        assert "gentry-textual-criticism-2020" in provenance_text
        assert "column XVII, lines 2–4" in provenance_text
        assert "Psalm 145:13b" in provenance_text
    else:
        assert "pp. 347–349" in provenance_text
        assert "Persian-period" in provenance_text
        assert "does not identify one original battle" in provenance_text

    layout = driver.execute_script(
        """
        const article = arguments[0];
        const bounds = article.getBoundingClientRect();
        return {
          viewportWidth: document.documentElement.clientWidth,
          documentWidth: document.documentElement.scrollWidth,
          itemLeft: bounds.left,
          itemRight: bounds.right,
          itemWidth: bounds.width,
        };
        """,
        record,
    )
    assert layout["documentWidth"] <= layout["viewportWidth"], layout
    assert layout["itemLeft"] >= 0 and layout["itemRight"] <= layout["viewportWidth"], layout
    assert layout["itemWidth"] <= layout["viewportWidth"], layout
    print(
        f"ED2A_PSALMS_READER_{device}: {case}, anchor={anchor!r}, "
        f"source_id={source_id!r}, document_width="
        f"{layout['documentWidth']}/{layout['viewportWidth']}px",
        flush=True,
    )
    assert driver.save_screenshot(
        str(artifacts_dir / f"ed2a-psalm-{chapter}-{device}.png")
    )
