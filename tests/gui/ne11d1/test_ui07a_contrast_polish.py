from __future__ import annotations

import json
from pathlib import Path

import pytest
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait

from tests.gui.pages import HomePage


pytestmark = [pytest.mark.gui]

SCREENSHOTS = Path("docs/ui-modernization/ui07a/screenshots")


def _select_jonah_1_17(driver, wait):
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="book-select"]')).select_by_value("Jonah")
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection?.getState?.().book === 'Jonah';"
    ))
    Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="chapter-input"]')).select_by_value("1")
    wait.until(lambda browser: browser.execute_script(
        "const s=window.BHFStudySelection?.getState?.(); return s?.book === 'Jonah' && s.chapter === 1;"
    ))
    driver.find_element(
        By.CSS_SELECTOR,
        '#chapter-reader .reader-pane.is-active [data-verse="17"] [data-verse-select]',
    ).click()
    wait.until(lambda browser: browser.execute_script(
        "return window.BHFStudySelection?.getState?.().reference === 'Jonah 1:17';"
    ))
    wait.until(lambda browser: browser.execute_script(
        "const record=window.BHFStudyCompanion?.getContextRecord?.(); "
        "return record?.status === 'ready' && record.key === window.BHFCompanionContext.requestKey(window.BHFStudySelection.getState());"
    ))


def _set_theme(driver, theme):
    driver.execute_script(
        "document.documentElement.dataset.theme = arguments[0]; "
        "localStorage.setItem('bhf-theme', arguments[0]);",
        theme,
    )


def _contrast_report(driver, selector):
    return driver.execute_script(
        """
        const parse = value => {
          const srgb = value.match(/color\\(srgb\\s+([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)(?:\\s*\\/\\s*([\\d.]+))?\\)/);
          if (srgb) return [Number(srgb[1]) * 255, Number(srgb[2]) * 255, Number(srgb[3]) * 255, Number(srgb[4] ?? 1)];
          const numbers = value.match(/[\\d.]+/g)?.map(Number) || [];
          return [numbers[0] || 0, numbers[1] || 0, numbers[2] || 0, numbers[3] ?? 1];
        };
        const composite = (front, back) => front.map((value, index) =>
          index < 3 ? value * front[3] + back[index] * (1 - front[3]) : 1
        );
        const luminance = ([red, green, blue]) => {
          const linear = channel => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
          return 0.2126 * linear(red / 255) + 0.7152 * linear(green / 255) + 0.0722 * linear(blue / 255);
        };
        const contrast = (front, back) => {
          const first = luminance(front), second = luminance(back);
          return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
        };
        const visible = element => !!(element.offsetWidth || element.offsetHeight || element.getClientRects().length);
        return Array.from(document.querySelectorAll(arguments[0])).filter(visible).map(element => {
          let background = [255, 255, 255, 1];
          const ancestors = [];
          for (let ancestor = element; ancestor; ancestor = ancestor.parentElement) ancestors.push(ancestor);
          ancestors.reverse().forEach(ancestor => {
            const layer = parse(getComputedStyle(ancestor).backgroundColor);
            if (layer[3] > 0) background = composite(layer, background);
          });
          const foreground = parse(getComputedStyle(element).color);
          const computedBackground = background.slice(0, 3);
          const computedForeground = composite(foreground, computedBackground);
          return {
            text: element.textContent.trim().replace(/\\s+/g, ' ').slice(0, 90),
            color: getComputedStyle(element).color,
            background: `rgb(${computedBackground.join(', ')})`,
            ratio: Number(contrast(computedForeground, computedBackground).toFixed(2)),
            fontSize: getComputedStyle(element).fontSize,
            fontWeight: getComputedStyle(element).fontWeight,
            opacity: getComputedStyle(element).opacity,
          };
        });
        """,
        selector,
    )


def _matched_declarations(driver, selector):
    driver.execute_cdp_cmd("DOM.enable", {})
    driver.execute_cdp_cmd("CSS.enable", {})
    document = driver.execute_cdp_cmd("DOM.getDocument", {})["root"]["nodeId"]
    node_id = driver.execute_cdp_cmd(
        "DOM.querySelector", {"nodeId": document, "selector": selector}
    )["nodeId"]
    matched = driver.execute_cdp_cmd("CSS.getMatchedStylesForNode", {"nodeId": node_id})
    properties = {"color", "background", "background-color", "border", "border-color", "opacity"}
    rules = []
    for item in matched.get("matchedCSSRules", []):
        declarations = [
            {"name": prop["name"], "value": prop["value"], "important": prop.get("important", False)}
            for prop in item["rule"].get("style", {}).get("cssProperties", [])
            if prop.get("name") in properties and prop.get("status") != "overloaded"
        ]
        if declarations:
            rules.append({
                "selectors": [part["text"] for part in item["rule"].get("selectorList", {}).get("selectors", [])],
                "declarations": declarations,
            })
    return rules


def _capture(driver, name):
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOTS / name
    assert driver.save_screenshot(str(path))


def _open_responsive_companion(driver, wait):
    peek = driver.find_element(By.CSS_SELECTOR, '.companion-peek[data-companion-state-control="study"]')
    if peek.is_displayed():
        driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", peek)
        wait.until(lambda browser: browser.find_element(
            By.CSS_SELECTOR, "[data-study-companion]"
        ).get_attribute("data-companion-state") == "study")
    wait.until(lambda browser: browser.execute_script(
        "return Array.from(document.querySelectorAll('[data-companion-primary-research] .companion-narrative-card'))"
        ".every(button => button.getBoundingClientRect().width > 0);"
    ))


def _render_status_fixture(driver):
    return driver.execute_script(
        """
        const states = ['available', 'available', 'partial', 'unknown', 'not_represented', 'partial'];
        const projection = {
          passage: {reference: 'Jonah 1:17'},
          sections: window.BHFNarrativeExplorer.SECTIONS.map((section, index) => ({
            id: section.id,
            state: states[index],
            item_ids: states[index] === 'available' || states[index] === 'partial' ? [`fixture-${index}`] : [],
            source_domains: [],
          })),
          items: [], connections: [], coverage: [],
          related_passages: {state: 'unknown'},
        };
        const fixture = window.BHFNarrativeExplorer.renderOverview(projection);
        fixture.dataset.contrastStatusFixture = 'true';
        fixture.style.cssText = 'position:fixed;left:-10000px;top:0;width:900px;z-index:-1';
        document.body.append(fixture);
        return Array.from(fixture.querySelectorAll('.narrative-explorer-category-card')).map(card => ({
          title: card.querySelector('.narrative-explorer-category-title').textContent,
          status: card.querySelector('.narrative-explorer-category-availability').textContent,
          statusClass: card.querySelector('.narrative-explorer-category-availability').className,
          count: card.querySelector('.narrative-explorer-category-count')?.textContent || null,
          titleWeight: getComputedStyle(card.querySelector('.narrative-explorer-category-title')).fontWeight,
          descriptionWeight: getComputedStyle(card.querySelector('.narrative-explorer-category-description')).fontWeight,
          statusWeight: getComputedStyle(card.querySelector('.narrative-explorer-category-availability')).fontWeight,
          countWeight: card.querySelector('.narrative-explorer-category-count')
            ? getComputedStyle(card.querySelector('.narrative-explorer-category-count')).fontWeight : null,
        }));
        """,
    )


def _contrast_status_fixture(driver):
    return _contrast_report(
        driver,
        "[data-contrast-status-fixture] .narrative-explorer-category-title, "
        "[data-contrast-status-fixture] .narrative-explorer-category-description, "
        "[data-contrast-status-fixture] .narrative-explorer-category-availability, "
        "[data-contrast-status-fixture] .narrative-explorer-category-count",
    )


def _status_border_contrast(driver):
    return driver.execute_script(
        """
        const parse=value=>{
          const srgb=value.match(/color\\(srgb\\s+([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)(?:\\s*\\/\\s*([\\d.]+))?\\)/);
          if(srgb)return [Number(srgb[1])*255,Number(srgb[2])*255,Number(srgb[3])*255,Number(srgb[4]??1)];
          const numbers=value.match(/[\\d.]+/g)?.map(Number)||[];
          return [numbers[0]||0,numbers[1]||0,numbers[2]||0,numbers[3]??1];
        };
        const composite=(front,back)=>front.map((value,index)=>index<3?value*front[3]+back[index]*(1-front[3]):1);
        const luminance=([r,g,b])=>{
          const linear=channel=>channel<=0.04045?channel/12.92:((channel+0.055)/1.055)**2.4;
          return 0.2126*linear(r/255)+0.7152*linear(g/255)+0.0722*linear(b/255);
        };
        const contrast=(first,second)=>{
          const a=luminance(first),b=luminance(second);
          return (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
        };
        return Array.from(document.querySelectorAll('[data-contrast-status-fixture] .narrative-explorer-category-availability')).map(element=>{
          let adjacent=[255,255,255,1], ancestors=[];
          for(let current=element.parentElement;current;current=current.parentElement)ancestors.push(current);
          ancestors.reverse().forEach(current=>{const color=parse(getComputedStyle(current).backgroundColor);if(color[3]>0)adjacent=composite(color,adjacent);});
          const border=parse(getComputedStyle(element).borderTopColor);
          return {text:element.textContent.trim(),borderColor:getComputedStyle(element).borderTopColor,
            adjacentBackground:`rgb(${adjacent.slice(0,3).join(', ')})`,
            ratio:Number(contrast(composite(border,adjacent.slice(0,3)),adjacent.slice(0,3)).toFixed(2)),
            borderStyle:getComputedStyle(element).borderTopStyle};
        });
        """
    )


def _active_focus_state(driver):
    return driver.execute_script(
        """
        const element=document.activeElement, style=getComputedStyle(element);
        const parse=value=>{
          const srgb=value.match(/color\\(srgb\\s+([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)(?:\\s*\\/\\s*([\\d.]+))?\\)/);
          if(srgb)return [Number(srgb[1])*255,Number(srgb[2])*255,Number(srgb[3])*255,Number(srgb[4]??1)];
          const numbers=value.match(/[\\d.]+/g)?.map(Number)||[];
          return [numbers[0]||0,numbers[1]||0,numbers[2]||0,numbers[3]??1];
        };
        const composite=(front,back)=>front.map((value,index)=>index<3?value*front[3]+back[index]*(1-front[3]):1);
        const luminance=([r,g,b])=>{
          const linear=channel=>channel<=0.04045?channel/12.92:((channel+0.055)/1.055)**2.4;
          return 0.2126*linear(r/255)+0.7152*linear(g/255)+0.0722*linear(b/255);
        };
        let background=[255,255,255,1], ancestors=[];
        for(let current=element.parentElement;current;current=current.parentElement)ancestors.push(current);
        ancestors.reverse().forEach(current=>{const color=parse(getComputedStyle(current).backgroundColor);if(color[3]>0)background=composite(color,background);});
        const adjacent=background.slice(0,3), ring=composite(parse(style.outlineColor),adjacent);
        const top=Math.max(luminance(ring),luminance(adjacent)),bottom=Math.min(luminance(ring),luminance(adjacent));
        return {className:element.className,focusVisible:element.matches(':focus-visible'),outlineColor:style.outlineColor,
          outlineStyle:style.outlineStyle,outlineWidth:style.outlineWidth,adjacentBackground:`rgb(${adjacent.join(',')})`,
          contrast:Number(((top+0.05)/(bottom+0.05)).toFixed(2))};
        """
    )


def test_ui07a_dark_and_light_cards_meet_rendered_text_contrast(driver, ne11d1_base_url):
    wait = WebDriverWait(driver, 90)
    driver.set_window_size(1440, 1400)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    _select_jonah_1_17(driver, wait)

    contrast_results = {}
    diagnostics = {}
    dig_deeper_selectors = (
        ".companion-narrative-card-copy strong, .companion-narrative-card-copy small, "
        ".companion-narrative-card-icon, .companion-narrative-card-arrow"
    )
    explorer_selectors = (
        ".narrative-explorer-follow-connection, .narrative-explorer-availability, "
        ".narrative-explorer-understand-passage strong, .narrative-explorer-understand-passage span, "
        ".narrative-explorer-category-icon, .narrative-explorer-category-title, "
        ".narrative-explorer-category-description, .narrative-explorer-category-availability, "
        ".narrative-explorer-category-count, .narrative-explorer-browse-sources"
    )

    surfaces = {}
    status_fixture = {}
    status_border_contrast = {}
    interaction_contrast = {}
    source_control_contrast = {}

    for theme in ("dark", "light"):
        _set_theme(driver, theme)
        ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, "h1")).perform()
        _capture(driver, f"after-{theme}-dig-deeper-desktop.png")
        contrast_results[theme] = {
            "dig_deeper": _contrast_report(driver, dig_deeper_selectors),
        }
        surfaces[theme] = driver.execute_script(
            "return Array.from(document.querySelectorAll('.companion-primary-research .companion-narrative-card'))"
            ".map(button => { const s=getComputedStyle(button); return {color:s.color,background:s.backgroundColor,"
            "border:s.borderColor,icon:getComputedStyle(button.querySelector('.companion-narrative-card-icon')).color,"
            "arrow:getComputedStyle(button.querySelector('.companion-narrative-card-arrow')).color}; });"
        )
        cards = driver.find_elements(By.CSS_SELECTOR, ".companion-primary-research .companion-narrative-card")
        for card in cards:
            ActionChains(driver).move_to_element(card).perform()
            hovered = _contrast_report(driver, dig_deeper_selectors)
            assert hovered and all(item["ratio"] >= 4.5 for item in hovered), hovered
        ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, "h1")).perform()
        driver.execute_script("arguments[0].focus();", cards[0])
        cards[0].send_keys(Keys.TAB)
        focused_card = driver.execute_script(
            "return {element:document.activeElement, visible:document.activeElement.matches(':focus-visible'), "
            "width:getComputedStyle(document.activeElement).outlineWidth};"
        )
        assert driver.execute_script("return document.activeElement === arguments[0];", cards[1]), focused_card
        assert focused_card["visible"] and focused_card["width"] == "3px", focused_card
        focus_state = _active_focus_state(driver)
        assert focus_state["contrast"] >= 3, focus_state
        ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, "h1")).perform()
        if theme == "dark":
            diagnostics["dig_deeper"] = {
                "explore_card": {
                    "computed": driver.execute_script(
                        "const e=document.querySelector('.narrative-explorer-entry'); "
                        "const s=getComputedStyle(e); return {color:s.color, background:s.backgroundColor, "
                        "border:s.borderColor, opacity:s.opacity};"
                    ),
                    "matched_rules": _matched_declarations(driver, ".narrative-explorer-entry"),
                },
                "places_card": {
                    "computed": driver.execute_script(
                        "const e=document.querySelector('.companion-places-locations-entry'); "
                        "const s=getComputedStyle(e); return {color:s.color, background:s.backgroundColor, "
                        "border:s.borderColor, opacity:s.opacity};"
                    ),
                    "matched_rules": _matched_declarations(driver, ".companion-places-locations-entry"),
                },
            }

        driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()
        wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, ".narrative-explorer-category-card"))
        ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-header")).perform()
        _capture(driver, f"after-{theme}-narrative-explorer-desktop.png")
        contrast_results[theme]["narrative_explorer"] = _contrast_report(driver, explorer_selectors)
        status_fixture[theme] = _render_status_fixture(driver)
        contrast_results[theme]["status_fixture"] = _contrast_status_fixture(driver)
        status_border_contrast[theme] = _status_border_contrast(driver)
        assert all(item["ratio"] >= 3 for item in status_border_contrast[theme]), status_border_contrast[theme]
        driver.execute_script("document.querySelector('[data-contrast-status-fixture]')?.remove();")

        expected_titles = {
            "Biblical Narrative",
            "Archaeology & Ancient History",
            "Biblical Geography",
            "Divine Council & Cosmic Geography",
            "Themes & Biblical Connections",
            "People, Events & Relationships",
        }
        assert {node.text for node in driver.find_elements(By.CSS_SELECTOR, ".narrative-explorer-category-title")} == expected_titles

        first_category = driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-category-card")
        ActionChains(driver).move_to_element(first_category).perform()
        interaction_contrast[theme] = _contrast_report(
            driver,
            ".narrative-explorer-category-title, .narrative-explorer-category-description, "
            ".narrative-explorer-category-availability, .narrative-explorer-category-count",
        )
        follow = driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-follow-connection")
        ActionChains(driver).move_to_element(follow).perform()
        follow_hover_contrast = _contrast_report(driver, ".narrative-explorer-follow-connection")
        assert follow_hover_contrast and all(item["ratio"] >= 4.5 for item in follow_hover_contrast), follow_hover_contrast
        ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-header")).perform()

        context_entry = driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-understand-passage")
        driver.execute_script("arguments[0].focus();", context_entry)
        context_entry.send_keys(Keys.TAB)
        focused_category = driver.execute_script(
            "const e=document.activeElement,s=getComputedStyle(e); return {className:e.className, visible:e.matches(':focus-visible'), "
            "outline:s.outline, outlineWidth:s.outlineWidth};"
        )
        assert "narrative-explorer-category-card" in focused_category["className"]
        assert focused_category["visible"] and focused_category["outlineWidth"] == "3px", focused_category
        focus_state = _active_focus_state(driver)
        assert focus_state["contrast"] >= 3 and focus_state["outlineStyle"] != "none", focus_state

        driver.find_element(By.CSS_SELECTOR, "[data-section-id='biblical_geography']").click()
        wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, ".narrative-explorer-inspect"))
        disabled_inspect = driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-inspect")
        assert disabled_inspect.get_attribute("disabled") is not None
        assert disabled_inspect.text == "No records available"
        contrast_results[theme]["disabled_no_results"] = _contrast_report(
            driver, ".narrative-explorer-inspect:disabled"
        )
        driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-back-topics").click()

        if theme == "dark":
            diagnostics["narrative_category"] = {
                "computed": driver.execute_script(
                    "const e=document.querySelector('.narrative-explorer-category-card'); "
                    "const s=getComputedStyle(e); return {color:s.color, background:s.backgroundColor, "
                    "border:s.borderColor, opacity:s.opacity};"
                ),
                "matched_rules": _matched_declarations(driver, ".narrative-explorer-category-card"),
            }

        driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-browse-sources").click()
        source_controls = wait.until(lambda browser: browser.find_elements(
            By.CSS_SELECTOR,
            ".companion-research-sources-view .narrative-explorer-category-controls button",
        ))
        assert len(source_controls) == 2
        _capture(driver, f"after-{theme}-browse-sources-desktop.png")
        source_control_contrast[theme] = _contrast_report(
            driver,
            ".companion-research-sources-view .narrative-explorer-category-controls button",
        )
        back_button, return_button = source_controls
        driver.execute_script("arguments[0].focus();", back_button)
        back_button.send_keys(Keys.TAB)
        assert driver.execute_script(
            "return document.activeElement === arguments[0] && document.activeElement.matches(':focus-visible');",
            return_button,
        )
        assert driver.execute_script("return getComputedStyle(arguments[0]).outlineWidth;", return_button) == "3px"
        focus_state = _active_focus_state(driver)
        assert focus_state["contrast"] >= 3 and focus_state["focusVisible"], focus_state
        return_button.send_keys(Keys.SHIFT, Keys.TAB)
        assert driver.execute_script(
            "return document.activeElement === arguments[0] && document.activeElement.matches(':focus-visible');",
            back_button,
        )
        assert driver.execute_script("return getComputedStyle(arguments[0]).outlineWidth;", back_button) == "3px"
        focus_state = _active_focus_state(driver)
        assert focus_state["contrast"] >= 3 and focus_state["focusVisible"], focus_state
        back_button.click()
        wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, ".narrative-explorer-follow-connection"))
        driver.find_element(By.CSS_SELECTOR, ".companion-back").click()
        wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, "[data-companion-primary-research]"))

    print("UI-07A rendered minimum contrast:", json.dumps({
        theme: round(min(
            item["ratio"]
            for entries in views.values()
            for item in entries
        ), 2)
        for theme, views in contrast_results.items()
    }))
    representative = {}
    for theme, views in contrast_results.items():
        def select(items, predicate):
            item = next((candidate for candidate in items if predicate(candidate["text"])), None)
            assert item is not None, (theme, items)
            return {key: item[key] for key in ("text", "color", "background", "ratio")}

        explorer = views["narrative_explorer"]
        fixture = views["status_fixture"]
        representative[theme] = {
            "dig_deeper_title": select(views["dig_deeper"], lambda text: text == "Explore the Narrative"),
            "dig_deeper_description": select(views["dig_deeper"], lambda text: text.startswith("Follow connections across")),
            "follow_button": select(explorer, lambda text: text == "Follow a Connection"),
            "topic_title": select(explorer, lambda text: text == "Biblical Narrative"),
            "topic_description": select(explorer, lambda text: text.startswith("Story, structure, and literary observations.")),
            "available_status": select(fixture, lambda text: text == "Source lookup complete"),
            "partial_status": select(fixture, lambda text: text == "Some results may be missing"),
            "unknown_status": select(fixture, lambda text: text == "Availability could not be checked"),
            "unavailable_status": select(fixture, lambda text: text == "No linked records returned"),
            "linked_record_count": select(fixture, lambda text: "linked record" in text),
            "status_border_contrast": status_border_contrast[theme],
            "disabled_no_records": select(views["disabled_no_results"], lambda text: text == "No records available"),
            "browse_sources": select(explorer, lambda text: text == "Browse research sources"),
            "source_navigation": [
                {key: item[key] for key in ("text", "color", "background", "ratio")}
                for item in source_control_contrast[theme]
            ],
        }
    print("UI-07A representative composited contrast:", json.dumps(representative, indent=2))
    print("UI-07A dark-mode cascade:", json.dumps(diagnostics, indent=2))
    all_contrast = {
        theme: [entry for entries in views.values() for entry in entries]
        + interaction_contrast[theme] + source_control_contrast[theme]
        for theme, views in contrast_results.items()
    }
    failing = {
        theme: [item for item in entries if item["ratio"] < 4.5]
        for theme, entries in all_contrast.items()
    }
    assert all(not entries for entries in failing.values()), json.dumps(failing, indent=2)
    assert all(len(cards) == 2 and cards[0] == cards[1] for cards in surfaces.values()), json.dumps(surfaces, indent=2)
    assert all(len(items) == 6 for items in status_fixture.values()), json.dumps(status_fixture, indent=2)
    for statuses in status_fixture.values():
        assert {item["status"] for item in statuses} == {
            "Source lookup complete", "Some results may be missing",
            "Availability could not be checked", "No linked records returned",
        }, statuses
        assert statuses[3]["count"] is None and statuses[4]["count"] is None, statuses
        assert all(item["titleWeight"] == "760" for item in statuses), statuses
        assert all(item["descriptionWeight"] == "500" for item in statuses), statuses
        assert all(item["statusWeight"] == "700" for item in statuses), statuses
        assert all(item["countWeight"] in (None, "500") for item in statuses), statuses


def test_ui07a_cards_fit_desktop_tablet_and_chrome_mobile(driver, ne11d1_base_url):
    wait = WebDriverWait(driver, 90)
    driver.set_window_size(1440, 1400)
    HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
    _select_jonah_1_17(driver, wait)

    measurements = {}
    for theme in ("dark", "light"):
        _set_theme(driver, theme)
        for width in (1440, 768, 390):
            if width == 390:
                driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": 390,
                    "height": 844,
                    "deviceScaleFactor": 1,
                    "mobile": True,
                    "screenWidth": 390,
                    "screenHeight": 844,
                })
            else:
                driver.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})
                driver.set_window_size(width, 1400)
            wait.until(lambda browser: browser.execute_script("return window.innerWidth") == width)
            if width <= 900:
                _open_responsive_companion(driver, wait)
            overview = driver.execute_script(
                """
                const grid=document.querySelector('[data-companion-primary-research]');
                const buttons=Array.from(grid.querySelectorAll('.companion-narrative-card'));
                const rects=buttons.map(button=>button.getBoundingClientRect());
                const host=document.querySelector('[data-companion-resource-host]');
                return {
                  width:innerWidth,
                  columns:getComputedStyle(grid).gridTemplateColumns,
                  twoColumns:rects.length===2 && Math.abs(rects[0].top-rects[1].top)<2,
                  stacked:rects.length===2 && rects[1].top>=rects[0].bottom-1,
                  cardWidths:rects.map(rect=>Math.round(rect.width)),
                  cardBounds:rects.map(rect=>({left:rect.left,right:rect.right,bottom:rect.bottom})),
                  pageOverflow:document.documentElement.scrollWidth-innerWidth,
                  hostOverflow:host ? host.scrollWidth-host.clientWidth : 0,
                  descriptionClipped:buttons.some(button=>Array.from(button.querySelectorAll('strong,small')).some(text=>text.scrollHeight>text.clientHeight+1)),
                };
                """
            )
            measurements[f"{theme}-{width}-overview"] = overview
            assert overview["width"] == width and len(overview["cardWidths"]) == 2, overview
            assert overview["pageOverflow"] <= 1 and overview["hostOverflow"] <= 1, overview
            assert not overview["descriptionClipped"], overview
            if width == 390:
                assert overview["stacked"], overview
                _capture(driver, f"after-{theme}-dig-deeper-mobile-390.png")
            else:
                assert overview["twoColumns"], overview
                assert overview["cardWidths"][0] > 0, overview

            driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()
            wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, ".narrative-explorer-category-card"))
            if width == 390:
                driver.execute_script("document.querySelector('[data-companion-resource-host]').scrollTop=0;")
                _capture(driver, f"after-{theme}-narrative-explorer-mobile-390.png")
            categories = driver.execute_script(
                """
                const grid=document.querySelector('.narrative-explorer-sections');
                const cards=Array.from(grid.querySelectorAll('.narrative-explorer-category-card'));
                const rects=cards.map(card=>card.getBoundingClientRect());
                const host=document.querySelector('[data-companion-resource-host]');
                const descriptions=cards.map(card=>card.querySelector('.narrative-explorer-category-description'));
                return {
                  width:innerWidth,
                  columns:getComputedStyle(grid).gridTemplateColumns,
                  twoColumns:rects.length===6 && Math.abs(rects[0].top-rects[1].top)<2,
                  oneColumn:rects.length===6 && rects[1].top>=rects[0].bottom-1,
                  cardBounds:rects.map(rect=>({left:rect.left,right:rect.right,bottom:rect.bottom})),
                  pageOverflow:document.documentElement.scrollWidth-innerWidth,
                  hostOverflow:host.scrollWidth-host.clientWidth,
                  clipped:descriptions.some(text=>text.scrollHeight>text.clientHeight+1),
                };
                """
            )
            measurements[f"{theme}-{width}-categories"] = categories
            assert categories["width"] == width and len(categories["cardBounds"]) == 6, categories
            assert categories["pageOverflow"] <= 1 and categories["hostOverflow"] <= 1, categories
            assert not categories["clipped"], categories
            if width == 1440:
                assert categories["twoColumns"], categories
            else:
                assert categories["oneColumn"], categories
            driver.find_element(By.CSS_SELECTOR, ".companion-back").click()
            wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, "[data-companion-primary-research]"))

    print("UI-07A responsive measurements:", json.dumps(measurements, indent=2))
