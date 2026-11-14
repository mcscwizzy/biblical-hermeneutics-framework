from __future__ import annotations

import pytest
from selenium.webdriver.support.ui import WebDriverWait

from .pages.base import BasePage


pytestmark = [pytest.mark.gui]


def test_driver_window_size_sets_exact_effective_viewport(driver):
    driver.set_window_size(390, 844)

    viewport = driver.execute_script(
        """
        return {
          innerWidth: window.innerWidth,
          innerHeight: window.innerHeight,
          clientWidth: document.documentElement.clientWidth,
          clientHeight: document.documentElement.clientHeight,
        };
        """
    )

    assert viewport == {
        "innerWidth": 390,
        "innerHeight": 844,
        "clientWidth": 390,
        "clientHeight": 844,
    }


def test_page_click_waits_until_overlay_stops_covering_target(driver, wait, base_url):
    driver.execute_script(
        """
        const style = document.createElement('style');
        style.textContent = `
          #ed5-click-readiness-target, #ed5-click-readiness-overlay {
            position: fixed; left: 20px; top: 120px; width: 260px; height: 52px;
          }
          #ed5-click-readiness-target { z-index: 1; }
          #ed5-click-readiness-overlay {
            z-index: 2; background: rgba(0, 0, 0, .85);
            transition: transform 600ms linear;
          }
          #ed5-click-readiness-overlay.is-leaving { transform: translateY(-80px); }
        `;
        document.head.append(style);
        const target = document.createElement('button');
        target.id = 'ed5-click-readiness-target';
        target.textContent = 'Click after the overlay clears';
        target.addEventListener('click', () => { target.dataset.clicked = 'true'; });
        const overlay = document.createElement('div');
        overlay.id = 'ed5-click-readiness-overlay';
        document.body.append(target, overlay);
        void overlay.offsetWidth;
        overlay.classList.add('is-leaving');
        """
    )
    wait.until(
        lambda browser: browser.execute_script(
            """
            return document.querySelector('#ed5-click-readiness-overlay')
              .getAnimations().some((animation) => animation.playState === 'running');
            """
        )
    )

    BasePage(driver, wait, base_url).click("#ed5-click-readiness-target")

    assert driver.find_element("id", "ed5-click-readiness-target").get_attribute("data-clicked") == "true"


def test_page_click_uses_native_scroll_for_offscreen_target(driver, wait, base_url):
    driver.execute_script(
        """
        const spacer = document.createElement('div');
        spacer.style.height = '2400px';
        const target = document.createElement('button');
        target.id = 'ed5-offscreen-click-target';
        target.textContent = 'Click after native scrolling';
        target.addEventListener('click', () => { target.dataset.clicked = 'true'; });
        document.body.append(spacer, target);
        """
    )

    BasePage(driver, wait, base_url).click("#ed5-offscreen-click-target")

    assert driver.find_element("id", "ed5-offscreen-click-target").get_attribute("data-clicked") == "true"
    assert driver.execute_script("return window.scrollY > 0")


def test_page_click_repositions_target_away_from_fixed_overlay(driver, base_url):
    driver.set_window_size(1440, 1000)
    driver.execute_script(
        """
        const target = document.createElement('button');
        target.id = 'ed5-fixed-overlay-click-target';
        target.textContent = 'Click after moving clear of the fixed overlay';
        target.style.cssText = 'position:absolute;top:850px;left:20px;z-index:1';
        target.addEventListener('click', () => { target.dataset.clicked = 'true'; });
        const spacer = document.createElement('div');
        spacer.style.height = '600px';
        const overlay = document.createElement('div');
        overlay.id = 'ed5-fixed-overlay-click-cover';
        overlay.style.cssText = 'position:fixed;inset:auto 0 0;height:230px;z-index:2;background:#333';
        document.body.append(target, spacer, overlay);
        """
    )
    assert driver.execute_script(
        "const target=document.querySelector('#ed5-fixed-overlay-click-target');"
        "const rect=target.getBoundingClientRect();"
        "return document.elementFromPoint(rect.left+rect.width/2, rect.top+rect.height/2)?.id;"
    ) == "ed5-fixed-overlay-click-cover"

    BasePage(driver, WebDriverWait(driver, 2), base_url).click("#ed5-fixed-overlay-click-target")

    assert driver.find_element("id", "ed5-fixed-overlay-click-target").get_attribute("data-clicked") == "true"
