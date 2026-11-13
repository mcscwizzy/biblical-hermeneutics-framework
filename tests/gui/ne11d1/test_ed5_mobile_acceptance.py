from __future__ import annotations

import json

import pytest
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage
from tests.gui.ne11d1.test_real_ckl_handoff import _select_verses


pytestmark = [pytest.mark.gui]


VIEWPORTS = [
    (1440, 1200, False, "desktop"),
    (390, 844, True, "mobile"),
    (320, 844, True, "narrow-mobile"),
]

EXPECTED_TERMS = [
    "Textual witness",
    "Masoretic Text",
    "Septuagint",
    "Critical apparatus",
    "Redaction",
    "Reception history",
    "Literary convention",
    "Parallelism",
    "Lexical range",
    "Historical reconstruction",
    "Ancient Near East",
    "Divine Council",
    "Intertextual relationship",
    "Disputed reading",
]


def _set_viewport(driver, width: int, height: int, mobile: bool) -> dict:
    driver.execute_cdp_cmd(
        "Emulation.setDeviceMetricsOverride",
        {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": mobile},
    )
    metrics = driver.execute_script(
        "return {innerWidth: window.innerWidth, clientWidth: document.documentElement.clientWidth};"
    )
    assert metrics["innerWidth"] == width, metrics
    assert metrics["clientWidth"] == width, metrics
    return metrics


def _open_narrative_explorer(driver, wait):
    if driver.execute_script("return window.innerWidth <= 900"):
        panel = driver.find_element(By.CSS_SELECTOR, "[data-study-companion]")
        state = panel.get_attribute("data-companion-state")
        if state == "peek":
            driver.find_element(
                By.CSS_SELECTOR,
                '.companion-peek[data-companion-state-control="study"]',
            ).click()
            wait.until(lambda _driver: panel.get_attribute("data-companion-state") == "study")
        elif state == "closed":
            driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-explore"]').click()
            wait.until(lambda page: page.execute_script(
                "return document.body.dataset.appSection === 'explore';"
            ))

    entry = wait.until(lambda page: next((button for button in page.find_elements(
        By.CSS_SELECTOR,
        '[data-testid="companion-narrative-explorer"]',
    ) if button.is_displayed() and button.is_enabled()), False))
    entry.click()
    return wait.until(lambda page: page.find_element(By.CSS_SELECTOR, ".narrative-explorer"))


def _assert_chromium(driver) -> dict:
    capabilities = driver.capabilities
    assert capabilities.get("browserName", "").lower() == "chrome", capabilities
    details = {
        "browser": capabilities.get("browserName"),
        "version": capabilities.get("browserVersion"),
        "driver": capabilities.get("chrome", {}).get("chromedriverVersion"),
    }
    assert details["version"], capabilities
    print("ED5_BROWSER=" + json.dumps(details, sort_keys=True), flush=True)
    return details


def _contrast_ratio(foreground: str, background: str) -> float:
    def luminance(value: str) -> float:
        if value.startswith("#"):
            raw = value.removeprefix("#")
            if len(raw) == 3:
                raw = "".join(character * 2 for character in raw)
            channels = [int(raw[index : index + 2], 16) / 255 for index in (0, 2, 4)]
        else:
            digits = value[value.find("(") + 1 : value.find(")")].split(",")[:3]
            channels = [int(part.strip()) / 255 for part in digits]
        linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)


def _measure_overview(driver) -> dict:
    return driver.execute_script(
        """
        const explorer = document.querySelector('.narrative-explorer');
        const notice = explorer.querySelector('.narrative-explorer-empty-research');
        const guide = explorer.querySelector('.narrative-explorer-terms-guide');
        const summary = guide.querySelector('summary');
        const terms = [...guide.querySelectorAll('dt')];
        const definitions = [...guide.querySelectorAll('dd')];
        const rootStyle = getComputedStyle(document.documentElement);
        const summaryStyle = getComputedStyle(summary);
        const noticeStyle = getComputedStyle(notice.querySelector('p'));
        const definitionStyle = getComputedStyle(definitions[0]);
        const bounds = element => {
          const rect = element.getBoundingClientRect();
          return {left: rect.left, right: rect.right, width: rect.width, height: rect.height,
            clientWidth: element.clientWidth, scrollWidth: element.scrollWidth,
            clientHeight: element.clientHeight, scrollHeight: element.scrollHeight,
            text: element.textContent.trim()};
        };
        return {
          viewport: {innerWidth: window.innerWidth, clientWidth: document.documentElement.clientWidth,
            scrollWidth: document.documentElement.scrollWidth},
          notice: bounds(notice),
          summary: bounds(summary),
          termCount: terms.length,
          terms: terms.map(term => term.textContent.trim()),
          definitionCount: definitions.length,
          definitions: definitions.map(bounds),
          colors: {
            summaryForeground: summaryStyle.color,
            pageMuted: definitionStyle.color,
            pageText: getComputedStyle(terms[0]).color,
            surface: rootStyle.getPropertyValue('--surface').trim(),
            surfaceMuted: rootStyle.getPropertyValue('--surface-muted').trim(),
            summaryBackground: rootStyle.getPropertyValue('--surface').trim(),
            noticeBackground: rootStyle.getPropertyValue('--surface-muted').trim(),
            noticeForeground: noticeStyle.color,
          },
        };
        """
    )


def _assert_no_horizontal_overflow(metrics: dict, width: int) -> None:
    assert metrics["viewport"]["innerWidth"] == width, metrics
    assert metrics["viewport"]["clientWidth"] == width, metrics
    assert metrics["viewport"]["scrollWidth"] <= width, metrics
    for name in ("notice", "summary", *[f"term-{index}" for index in range(14)]):
        measurement = metrics["notice"] if name == "notice" else metrics["summary"] if name == "summary" else metrics["definitions"][int(name[5:])]
        assert measurement["left"] >= -1 and measurement["right"] <= width + 1, (name, measurement)
        assert measurement["scrollWidth"] <= measurement["clientWidth"] + 1, (name, measurement)


@pytest.mark.parametrize(("width", "height", "mobile", "label"), VIEWPORTS)
def test_ed5_empty_notice_and_terminology_guide_acceptance(
    driver, base_url, artifacts_dir, width, height, mobile, label
):
    browser = _assert_chromium(driver)
    driver.execute_cdp_cmd(
        "Emulation.setDeviceMetricsOverride",
        {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": mobile},
    )
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    viewport = _set_viewport(driver, width, height, mobile)

    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value("1 Kings")
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("2")
    wait.until(lambda page: page.execute_script(
        "return window.BHFStudySelection?.getState?.().reference === '1 Kings 2';"
    ))
    explorer = _open_narrative_explorer(driver, wait)
    notice = wait.until(lambda page: page.find_element(
        By.CSS_SELECTOR,
        ".narrative-explorer-empty-research",
    ))
    assert notice.is_displayed()
    assert "No eligible Evidence library research is currently available for 1 Kings 2" in notice.text
    assert "does not imply that the passage lacks historical significance" in notice.text

    ckl_coverage = driver.execute_async_script(
        """
        const done = arguments[0];
        window.BHFNarrativeExplorer.load({book: '1 Kings', chapter: 2})
          .then(projection => done(projection.coverage.find(entry =>
            entry.source_domain === 'canonical_knowledge_library')))
          .catch(error => done({error: String(error)}));
        """
    )
    assert ckl_coverage.get("state") == "not_represented", ckl_coverage
    assert ckl_coverage.get("query_status") == "complete", ckl_coverage
    assert ckl_coverage.get("query_returned_count") == 0, ckl_coverage

    guide = explorer.find_element(By.CSS_SELECTOR, ".narrative-explorer-terms-guide")
    summary = guide.find_element(By.CSS_SELECTOR, "summary")
    assert guide.tag_name.lower() == "details"
    assert summary.tag_name.lower() == "summary"
    assert guide.get_attribute("open") is None
    assert summary.text == "Plain-language guide to research terms"
    guide_text = driver.execute_script("return arguments[0].textContent", guide)
    assert "These definitions explain terminology; they do not settle how a term applies to a passage." in guide_text
    guide_terms = driver.execute_script(
        "return Array.from(arguments[0].querySelectorAll('dt'), term => term.textContent.trim())",
        guide,
    )
    assert guide_terms == EXPECTED_TERMS
    assert len(guide.find_elements(By.CSS_SELECTOR, "dd")) == 14
    assert viewport["innerWidth"] == width

    noncomplete_notice_cases = driver.execute_async_script(
        """
        const done = arguments[0];
        (async () => {
          const projection = await window.BHFNarrativeExplorer.load({book: '1 Kings', chapter: 2});
          const coverage = projection.coverage.find(entry =>
            entry.source_domain === 'canonical_knowledge_library');
          const result = {};
          for (const [name, state, queryStatus] of [
            ['failed', 'unknown', 'failed'], ['partial', 'partial', 'partial'],
          ]) {
            const variant = structuredClone(projection);
            const ckl = variant.coverage.find(entry =>
              entry.source_domain === 'canonical_knowledge_library');
            ckl.state = state;
            ckl.query_status = queryStatus;
            const rendered = window.BHFNarrativeExplorer.renderOverview(variant, {document});
            result[name] = Boolean(rendered.querySelector('.narrative-explorer-empty-research'));
          }
          return {baseline: {state: coverage.state, query_status: coverage.query_status}, notices: result};
        })().then(done).catch(error => done({error: String(error)}));
        """
    )
    assert noncomplete_notice_cases["notices"] == {"failed": False, "partial": False}, noncomplete_notice_cases
    print(
        "ED5_EMPTY_NOTICE=" + json.dumps({
            "viewport": viewport,
            "baseline_ckl": ckl_coverage,
            "negative_states": noncomplete_notice_cases["notices"],
            "browser": browser,
        }, sort_keys=True),
        flush=True,
    )

    # Native details/summary keeps browser disclosure semantics and focus in place.
    browse_sources = explorer.find_element(By.CSS_SELECTOR, ".narrative-explorer-browse-sources")
    driver.execute_script("arguments[0].focus()", browse_sources)
    ActionChains(driver).send_keys(Keys.TAB).perform()
    assert driver.execute_script("return document.activeElement === arguments[0]", summary)
    focus = driver.execute_script(
        "const style=getComputedStyle(arguments[0]); return {width:style.outlineWidth, style:style.outlineStyle, color:style.outlineColor};",
        summary,
    )
    assert focus["width"] == "3px" and focus["style"] == "solid", focus
    ActionChains(driver).send_keys(Keys.ENTER).perform()
    assert guide.get_attribute("open") is not None
    assert driver.execute_script("return document.activeElement === arguments[0]", summary)
    ActionChains(driver).send_keys(Keys.SPACE).perform()
    assert guide.get_attribute("open") is None
    ActionChains(driver).send_keys(Keys.SPACE).perform()
    assert guide.get_attribute("open") is not None
    ActionChains(driver).send_keys(Keys.ENTER).perform()
    assert guide.get_attribute("open") is None
    assert driver.execute_script("return document.activeElement === arguments[0]", summary)

    driver.execute_cdp_cmd("Accessibility.enable", {})
    summary_object = driver.execute_cdp_cmd(
        "Runtime.evaluate",
        {"expression": "document.querySelector('.narrative-explorer-terms-guide summary')"},
    )["result"]["objectId"]
    accessibility = driver.execute_cdp_cmd(
        "Accessibility.getPartialAXTree",
        {"objectId": summary_object, "fetchRelatives": True},
    )
    summary_ax = next(
        node for node in accessibility["nodes"]
        if node.get("name", {}).get("value") == "Plain-language guide to research terms"
    )
    assert summary_ax.get("role", {}).get("value") in {"DisclosureTriangle", "button"}, summary_ax

    reduced_motion = driver.execute_cdp_cmd(
        "Emulation.setEmulatedMedia",
        {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]},
    )
    assert driver.execute_script("return matchMedia('(prefers-reduced-motion: reduce)').matches")
    print("ED5_DISCLOSURE_AX=" + json.dumps({
        "role": summary_ax.get("role", {}).get("value"),
        "name": summary_ax.get("name", {}).get("value"),
        "native_details": guide.tag_name,
        "native_summary": summary.tag_name,
        "focus": focus,
        "reduced_motion": True,
        "viewport": viewport,
    }, sort_keys=True), flush=True)

    theme_reports = {}
    for theme in ("light", "dark"):
        driver.execute_script("document.documentElement.dataset.theme = arguments[0]", theme)
        guide = driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-terms-guide")
        summary = guide.find_element(By.CSS_SELECTOR, "summary")
        driver.save_screenshot(str(artifacts_dir / f"ed5-empty-terms-{width}-{theme}-collapsed.png"))
        summary.click()
        metrics = _measure_overview(driver)
        assert metrics["termCount"] == 14 and metrics["definitionCount"] == 14, metrics
        assert metrics["terms"] == EXPECTED_TERMS, metrics["terms"]
        assert all(definition["text"] for definition in metrics["definitions"]), metrics
        _assert_no_horizontal_overflow(metrics, width)
        assert metrics["summary"]["height"] >= 44, metrics
        browse_height = driver.execute_script(
            "return document.querySelector('.narrative-explorer-browse-sources').getBoundingClientRect().height"
        )
        assert browse_height >= 44, browse_height

        colors = metrics["colors"]
        contrast = {
            "notice": round(_contrast_ratio(colors["noticeForeground"], colors["noticeBackground"]), 2),
            "terms": round(_contrast_ratio(colors["pageMuted"], colors["surface"]), 2),
            "summary": round(_contrast_ratio(colors["summaryForeground"], colors["summaryBackground"]), 2),
            "term_headings": round(_contrast_ratio(colors["pageText"], colors["surface"]), 2),
        }
        assert all(value >= 4.5 for value in contrast.values()), (theme, contrast, colors)
        longest_definition = max(metrics["definitions"], key=lambda definition: len(definition["text"]))
        assert len(longest_definition["text"]) > 120, longest_definition
        assert longest_definition["scrollHeight"] <= longest_definition["clientHeight"] + 1, longest_definition
        driver.save_screenshot(str(artifacts_dir / f"ed5-empty-terms-{width}-{theme}-expanded.png"))
        theme_reports[theme] = {
            "contrast_ratios": contrast,
            "summary_height": metrics["summary"]["height"],
            "browse_sources_height": browse_height,
            "document_width": metrics["viewport"]["scrollWidth"],
            "longest_definition_length": len(longest_definition["text"]),
            "longest_definition_scroll": longest_definition["scrollHeight"],
            "longest_definition_client": longest_definition["clientHeight"],
            "overflow_checked_elements": 17,
        }
        summary.click()

    print("ED5_VIEWPORT_ACCEPTANCE=" + json.dumps({
        "width": width,
        "height": height,
        "effective_viewport": viewport,
        "themes": theme_reports,
        "screenshots": [
            f"ed5-empty-terms-{width}-{theme}-{state}.png"
            for theme in ("light", "dark")
            for state in ("collapsed", "expanded")
        ],
        "reduced_motion_result": reduced_motion,
    }, sort_keys=True), flush=True)


@pytest.mark.parametrize(
    ("width", "height", "mobile", "label"),
    [(1440, 1200, False, "desktop"), (390, 844, True, "mobile")],
)
def test_genesis_12_source_disclosure_stays_attached_to_exact_record(
    driver, base_url, artifacts_dir, width, height, mobile, label
):
    _assert_chromium(driver)
    _set_viewport(driver, width, height, mobile)
    wait = WebDriverWait(driver, 90)
    HomePage(driver, wait, base_url).open().wait_loaded()
    _select_verses(driver, wait, "Genesis", 12, [1, 2, 3])
    assert _set_viewport(driver, width, height, mobile)["clientWidth"] == width
    explorer = _open_narrative_explorer(driver, wait)
    explorer.find_element(By.CSS_SELECTOR, '[data-section-id="biblical_narrative"]').click()
    section = wait.until(lambda page: page.find_element(
        By.CSS_SELECTOR,
        '.narrative-explorer-section[data-section-id="biblical_narrative"]',
    ))
    section.find_element(By.CSS_SELECTOR, ".narrative-explorer-inspect").click()
    item_selector = 'button[data-narrative-item-id="ckl:genesis#claim:genesis-blessing-for-families"]'
    item = wait.until(lambda page: page.find_element(By.CSS_SELECTOR, item_selector))
    record = item.find_element(
        By.XPATH,
        "./ancestor::article[contains(@class, 'narrative-explorer-item')]",
    )
    disclosure = record.find_element(By.CSS_SELECTOR, ".narrative-explorer-provenance")
    disclosure.find_element(By.CSS_SELECTOR, "summary").click()
    text = disclosure.text
    assert "Projected source identity: ckl:genesis#claim:genesis-blessing-for-families" in text
    assert "genesis-1-50" in text
    assert "hamilton-genesis-1-17" in text
    assert "Genesis 12:1-3" in text
    assert driver.execute_script(
        "return document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
    print("ED5_GENESIS12_SOURCES=" + json.dumps({
        "viewport": driver.execute_script(
            "return {innerWidth:innerWidth, clientWidth:document.documentElement.clientWidth}"
        ),
        "record_id": item.get_attribute("data-narrative-item-id"),
        "source_ids": ["genesis-1-50", "hamilton-genesis-1-17"],
        "anchor": "Genesis 12:1-3",
    }, sort_keys=True), flush=True)
    assert driver.save_screenshot(str(artifacts_dir / f"ed5-genesis12-sources-{label}.png"))
