from __future__ import annotations

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


class BasePage:
    def __init__(self, driver, wait, base_url: str):
        self.driver = driver
        self.wait = wait
        self.base_url = base_url.rstrip("/")

    def open_path(self, path: str = "/"):
        self.driver.get(f"{self.base_url}{path}")
        return self

    def find(self, selector: str):
        return self.driver.find_element(By.CSS_SELECTOR, selector)

    def find_all(self, selector: str):
        return self.driver.find_elements(By.CSS_SELECTOR, selector)

    def click(self, selector: str):
        locator = (By.CSS_SELECTOR, selector)
        last_click_status = {"reason": "target was not checked"}
        center_scroll_attempted = False

        def click_when_ready(driver):
            nonlocal center_scroll_attempted, last_click_status
            try:
                element = driver.find_element(*locator)
                if not element.is_displayed() or not element.is_enabled():
                    last_click_status = {"reason": "element is hidden or disabled"}
                    return False

                target_status = driver.execute_script(
                    """
                    const element = arguments[0];
                    if (!element.isConnected) return {ready: false, reason: "disconnected"};
                    const rect = element.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) return {ready: false, reason: "empty bounds"};
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2;
                    const hit = document.elementFromPoint(x, y);
                    const scrollableAncestors = [];
                    for (let ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement) {
                      const style = getComputedStyle(ancestor);
                      if (ancestor.scrollHeight > ancestor.clientHeight + 2 || /auto|scroll/.test(style.overflowY)) {
                        scrollableAncestors.push({
                          tag: ancestor.tagName,
                          className: String(ancestor.className || ""),
                          clientHeight: ancestor.clientHeight,
                          scrollHeight: ancestor.scrollHeight,
                          scrollTop: ancestor.scrollTop,
                          overflowY: style.overflowY,
                        });
                      }
                    }
                    const common = {
                      rect: {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom},
                      point: {x, y},
                      viewport: {width: window.innerWidth, height: window.innerHeight},
                      scroll: {x: window.scrollX, y: window.scrollY},
                      bodyClass: document.body.className,
                      bodyOverflowY: getComputedStyle(document.body).overflowY,
                      htmlOverflowY: getComputedStyle(document.documentElement).overflowY,
                      documentHeight: document.documentElement.scrollHeight,
                      scrollableAncestors,
                    };
                    const outsideViewport = rect.bottom <= 0 || rect.top >= window.innerHeight
                      || rect.right <= 0 || rect.left >= window.innerWidth;
                    if (outsideViewport) {
                      return {...common, ready: false, reason: "outside viewport"};
                    }
                    const animationAncestors = new Set();
                    for (let ancestor = element; ancestor; ancestor = ancestor.parentElement) {
                      animationAncestors.add(ancestor);
                    }
                    for (let ancestor = hit; ancestor; ancestor = ancestor.parentElement) {
                      animationAncestors.add(ancestor);
                    }
                    for (const ancestor of animationAncestors) {
                      const moving = ancestor.getAnimations().find((animation) => animation.playState === "running");
                      if (moving) {
                        return {
                          ...common,
                          ready: false,
                          reason: "ancestor animation is running",
                          animationTarget: `${ancestor.tagName}.${String(ancestor.className || "").replace(/\\s+/g, ".")}`,
                        };
                      }
                    }
                    if (!hit || (hit !== element && !element.contains(hit))) {
                      return {
                        ...common,
                        ready: false,
                        reason: "center is covered",
                        hit: hit ? `${hit.tagName}.${String(hit.className || "").replace(/\\s+/g, ".")}` : null,
                      };
                    }
                    return {...common, ready: true};
                    """,
                    element,
                )
                last_click_status = target_status
                if not target_status["ready"]:
                    if target_status["reason"] == "outside viewport":
                        # WebDriver's native click scrolls through the browser's
                        # actual scroll root; JS scrollIntoView can leave a target
                        # offscreen when a nested layout or active focus state owns
                        # scrolling. Native clicking also preserves hit testing.
                        element.click()
                        return True
                    if target_status["reason"] == "center is covered" and not center_scroll_attempted:
                        center_scroll_attempted = True
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'});",
                            element,
                        )
                    return False

                element.click()
                return True
            except ElementClickInterceptedException as exc:
                last_click_status = {"reason": "native click was intercepted", "error": str(exc)[:240]}
                return False
            except (ElementNotInteractableException, StaleElementReferenceException) as exc:
                last_click_status = {"reason": type(exc).__name__, "error": str(exc)[:240]}
                return False

        try:
            self.wait.until(click_when_ready)
        except TimeoutException as exc:
            raise TimeoutException(
                f"Click target {selector!r} did not become ready: {last_click_status}"
            ) from exc

    def type_into(self, selector: str, text: str, clear: bool = True):
        element = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
        if clear:
            element.clear()
        element.send_keys(text)
        return element

    def select_value(self, selector: str, value: str):
        element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        Select(element).select_by_value(str(value))

    def wait_visible(self, selector: str):
        return self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))

    def wait_hidden(self, selector: str):
        return self.wait.until(lambda driver: not driver.find_element(By.CSS_SELECTOR, selector).is_displayed())

    def text_of(self, selector: str) -> str:
        return self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector))).text
