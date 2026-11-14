from __future__ import annotations

from selenium.common.exceptions import StaleElementReferenceException
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
        self.driver.execute_script(
            "document.querySelector(arguments[0])?.scrollIntoView({block: 'center', inline: 'nearest'});",
            selector,
        )

        def click_when_ready(driver):
            try:
                element = driver.find_element(*locator)
                if not element.is_displayed() or not element.is_enabled():
                    return False
                element.click()
                return True
            except StaleElementReferenceException:
                return False

        self.wait.until(click_when_ready)

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
