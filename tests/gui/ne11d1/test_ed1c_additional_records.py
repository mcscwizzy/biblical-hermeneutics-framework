from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import _select_verses


pytestmark = [pytest.mark.gui]


@pytest.mark.parametrize(
    ("width", "height", "mobile", "label"),
    [(1440, 1200, False, "desktop"), (390, 844, True, "mobile")],
)
def test_kephale_additional_record_is_passage_scoped_and_readable(
    driver, base_url, artifacts_dir, width, height, mobile, label
):
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": width,
        "height": height,
        "deviceScaleFactor": 1,
        "mobile": mobile,
    })
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "1 Corinthians", 11, [3])
    peek = driver.find_element(By.CSS_SELECTOR, '.companion-peek[data-companion-state-control="study"]')
    if peek.is_displayed():
        peek.click()
    wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR,
        ".companion-overview-actions",
    ).is_displayed())

    driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()
    explorer = wait.until(lambda browser: browser.find_element(By.CSS_SELECTOR, ".narrative-explorer"))
    toggle = wait.until(lambda browser: browser.find_element(
        By.CSS_SELECTOR,
        ".narrative-explorer-additional-records-toggle",
    ))
    assert toggle.get_attribute("aria-expanded") == "false"
    assert not explorer.find_elements(
        By.CSS_SELECTOR,
        'button[data-narrative-item-id="ckl:1-corinthians#claim:1cor-kephale"]',
    )
    assert driver.save_screenshot(str(artifacts_dir / f"ed1c-kephale-{label}-collapsed.png"))

    toggle.click()
    assert "applicable Scripture anchor for this passage" in explorer.text
    item_selector = 'button[data-narrative-item-id="ckl:1-corinthians#claim:1cor-kephale"]'
    item_buttons = wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, item_selector))
    assert len(item_buttons) == 1
    record = item_buttons[0].find_element(
        By.XPATH,
        "./ancestor::article[contains(@class, 'narrative-explorer-item')]",
    )
    assert len(explorer.find_elements(By.CSS_SELECTOR, item_selector)) == 1
    assert "Lexical research" in record.text
    assert "Evidence type not recorded" not in record.text

    provenance = record.find_element(By.CSS_SELECTOR, ".narrative-explorer-provenance")
    summary = provenance.find_element(By.CSS_SELECTOR, "summary")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", summary)
    summary.click()
    assert provenance.get_attribute("open") is not None
    provenance_text = provenance.text
    assert "Projected source identity: ckl:1-corinthians#claim:1cor-kephale" in provenance_text
    assert "Claim ID: 1cor-kephale" in provenance_text
    assert "Claim type: lexical" in provenance_text
    assert "Passage relationship: 1 Corinthians 11:3" in provenance_text
    assert "bdag" in provenance_text
    assert "thiselton-1cor" in provenance_text
    assert "Certainty: disputed" in provenance_text
    assert "Dispute status: lexical_uncertainty" in provenance_text
    assert "no assigned topic" in explorer.text

    layout = driver.execute_script(
        """
        const toggle = document.querySelector('.narrative-explorer-additional-records-toggle');
        const bounds = toggle.getBoundingClientRect();
        return {
          viewportWidth: document.documentElement.clientWidth,
          documentWidth: document.documentElement.scrollWidth,
          toggleLeft: bounds.left,
          toggleRight: bounds.right,
          toggleHeight: bounds.height,
          expanded: toggle.getAttribute('aria-expanded'),
        };
        """
    )
    assert layout["documentWidth"] <= layout["viewportWidth"], layout
    assert layout["toggleLeft"] >= 0 and layout["toggleRight"] <= layout["viewportWidth"], layout
    assert layout["toggleHeight"] >= 44, layout
    assert layout["expanded"] == "true"
    print(
        f"ED1C_READER_ACCEPTANCE_{label}: "
        f"viewport={width}x{height}, disclosure={toggle.text!r}, "
        f"exact_anchor='1 Corinthians 11:3', source_ids='bdag,thiselton-1cor', "
        f"document_width={layout['documentWidth']}/{layout['viewportWidth']}px, "
        f"disclosure_height={layout['toggleHeight']}px",
        flush=True,
    )
    assert driver.save_screenshot(str(artifacts_dir / f"ed1c-kephale-{label}-expanded.png"))
