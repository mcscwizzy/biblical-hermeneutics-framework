from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base import BasePage


class MapsPage(BasePage):
    def open_maps(self):
        self.driver.execute_script(
            """
            window.BHFStudyCompanion.showPersonalResource('map-browser', 'Maps');
            window.BHFStudyActions.perform('open_map_panel');
            """
        )
        browse_buttons = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="map-browse-button"]')
        if browse_buttons and browse_buttons[0].is_displayed():
            browse_buttons[0].click()
        search_inputs = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="map-search-input"]')
        if not search_inputs or not search_inputs[0].is_displayed():
            navigator_buttons = self.driver.find_elements(By.CSS_SELECTOR, '[data-map-navigator-open]')
            if navigator_buttons and navigator_buttons[0].is_displayed():
                navigator_buttons[0].click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="map-search-input"]')))
        navigator_buttons = self.driver.find_elements(By.CSS_SELECTOR, '[data-map-navigator-open]')
        if navigator_buttons and navigator_buttons[0].get_attribute("aria-expanded") == "true":
            self.click('[data-map-navigator-close]')
            self.wait.until(lambda driver: navigator_buttons[0].get_attribute("aria-expanded") == "false")
        return self

    def search_map_catalog(self, text: str):
        self.type_into('[data-testid="map-search-input"]', text)
        self.click('[data-testid="map-search-button"]')
        return self

    def assert_results_or_empty_state(self):
        self.wait.until(
            lambda driver: (
                len(driver.find_elements(By.CSS_SELECTOR, "#map-search-results .map-search-result")) > 0
                or "No browse results" in driver.find_element(By.CSS_SELECTOR, "#map-search-results-list").text
            )
        )
        return self
