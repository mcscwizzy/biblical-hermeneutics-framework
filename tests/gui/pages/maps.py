from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base import BasePage


class MapsPage(BasePage):
    def open_maps(self):
        explore_buttons = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="app-dock-explore"]')
        if explore_buttons and explore_buttons[0].is_displayed():
            explore_buttons[0].click()
        map_tabs = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="maps-tab"]')
        if map_tabs and map_tabs[0].is_displayed():
            self.click('[data-testid="maps-tab"]')
        browse_buttons = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="map-browse-button"]')
        if browse_buttons and browse_buttons[0].is_displayed():
            browse_buttons[0].click()
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
