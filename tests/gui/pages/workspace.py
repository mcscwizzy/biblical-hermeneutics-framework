from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base import BasePage


class WorkspacePage(BasePage):
    def open_tab(self, name: str):
        self.click(f'[data-testid="{name}-tab"]')
        return self

    def open_app_section(self, name: str):
        self.click(f'[data-testid="app-dock-{name}"]')
        return self

    def assert_tab_visible(self, name: str):
        pane = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f'#workspace-pane-{name}')))
        self.wait.until(lambda driver: pane.is_displayed())
        tabs = self.driver.find_elements(By.CSS_SELECTOR, f'[data-testid="{name}-tab"]')
        if tabs and tabs[0].is_displayed():
            self.wait.until(lambda driver: tabs[0].get_attribute("aria-selected") == "true")
        return self

    def active_app_section(self):
        return self.driver.execute_script("return document.body.dataset.appSection || ''")

    def open_reader_settings(self):
        triggers = self.driver.find_elements(By.CSS_SELECTOR, "[data-reader-controls-trigger]")
        for trigger in triggers:
            if trigger.is_displayed() and trigger.is_enabled():
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", trigger)
                self.driver.execute_script("arguments[0].click();", trigger)
                return self
        raise AssertionError("No settings trigger is visible")

    def toggle_dark_mode(self):
        self.open_reader_settings()
        self.click('[data-testid="mobile-theme-toggle"]')
        self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "#reader-controls-sheet[open]")))
        return self

    def toggle_reader_mode(self):
        self.open_reader_settings()
        self.click('[data-testid="mobile-reader-mode-toggle"]')
        self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "#reader-controls-sheet[open]")))
        return self

    def toggle_expand_workspace(self):
        toggle = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="workspace-expand-toggle"]')))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", toggle)
        self.driver.execute_script("arguments[0].click();", toggle)
        return self
