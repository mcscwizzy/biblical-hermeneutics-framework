import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from tests.gui.pages import HomePage


@pytest.mark.parametrize("width", [320, 390])
def test_draft_canonical_card_disclosure_is_visible_and_usable_on_phone_widths(
    driver,
    wait,
    base_url,
    width,
):
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": width,
        "height": 844,
        "deviceScaleFactor": 1,
        "mobile": True,
    })
    HomePage(driver, wait, base_url).open().wait_loaded()
    driver.execute_script(
        """
        const current = window.BHFStudySelection.getState();
        window.BHFStudySelection.setSelection({
          ...current,
          book: "Genesis",
          chapter: 6,
          startVerse: null,
          endVerse: null,
          selectedVerses: [],
          selectedText: "",
          reference: "Genesis 6",
          hasPassageSelection: false,
        }, "ne11g-governance-mobile");
        """
    )
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection?.getState?.().book === 'Genesis';"
    ))
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection?.getState?.().chapter === 6;"
    ))
    driver.set_script_timeout(120)
    fetched = driver.execute_async_script(
        """
        const done = arguments[0];
        window.BHFCompanionContext.load(window.BHFStudySelection.getState())
          .then((context) => done({
            reference: context.reference,
            hasDraft: context.summaries.canonical.some((item) =>
              item.content_status === "draft"
              && item.review_status === "in_review"
              && item.human_review_required === true),
          }))
          .catch((error) => done({error: String(error)}));
        """
    )
    assert fetched == {"reference": "Genesis 6", "hasDraft": True}
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudyCompanion?.getContextRecord?.().status === 'ready';"
    ))
    driver.execute_script("window.BHFStudyCompanion.openResource('canonical');")

    host = driver.find_element(By.CSS_SELECTOR, "[data-companion-resource-host]")
    notice = wait.until(lambda _driver: host.find_element(
        By.CSS_SELECTOR,
        ".companion-summary-governance",
    ))
    card = notice.find_element(By.XPATH, "ancestor::article[contains(@class, 'companion-summary-card')]")
    assert notice.text == "Draft evidence — awaiting human review"
    assert card.get_attribute("role") == "button"
    assert "Draft evidence — awaiting human review" in card.get_attribute("aria-label")

    layout = driver.execute_script(
        """
        const notice = arguments[0];
        const card = notice.closest('.companion-summary-card');
        return {
          noticeWidth: notice.clientWidth,
          noticeScrollWidth: notice.scrollWidth,
          cardWidth: card.clientWidth,
          cardScrollWidth: card.scrollWidth,
          viewportWidth: document.documentElement.clientWidth,
          viewportScrollWidth: document.documentElement.scrollWidth,
        };
        """,
        notice,
    )
    assert layout["noticeWidth"] > 0
    assert layout["noticeScrollWidth"] <= layout["noticeWidth"] + 1, layout
    assert layout["cardScrollWidth"] <= layout["cardWidth"] + 1, layout
    assert layout["viewportWidth"] == width, layout
    assert layout["viewportScrollWidth"] <= layout["viewportWidth"], layout

    card.click()
    WebDriverWait(driver, 15).until(lambda browser: "Back to results" in host.text)
