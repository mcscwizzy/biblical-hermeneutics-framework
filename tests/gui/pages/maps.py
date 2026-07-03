from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base import BasePage


class MapsPage(BasePage):
    def open_maps(self):
        self.click('[data-testid="maps-tab"]')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="map-browse-button"]')))
        self.click('[data-testid="map-browse-button"]')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="map-search-input"]')))
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
                or "Search the map catalog" in driver.find_element(By.CSS_SELECTOR, "#map-panel-status").text
                or driver.find_element(By.CSS_SELECTOR, "#map-search-results").is_displayed()
            )
        )
        return self
