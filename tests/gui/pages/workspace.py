from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base import BasePage


class WorkspacePage(BasePage):
    def open_tab(self, name: str):
        self.click(f'[data-testid="{name}-tab"]')
        return self

    def open_mobile_section(self, name: str):
        self.click(f'[data-testid="mobile-nav-{name}"]')
        return self

    def assert_tab_visible(self, name: str):
        tab = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, f'[data-testid="{name}-tab"]')))
        pane = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f'#workspace-pane-{name}')))
        self.wait.until(lambda driver: pane.is_displayed())
        self.wait.until(lambda driver: tab.get_attribute("aria-selected") == "true")
        return self

    def active_mobile_section(self):
        return self.driver.execute_script("return document.body.dataset.mobileSection || ''")

    def toggle_dark_mode(self):
        self.click('[data-testid="theme-toggle"]')
        return self

    def toggle_reader_mode(self):
        self.click('[data-testid="reader-mode-toggle"]')
        return self

    def toggle_expand_workspace(self):
        self.click('[data-testid="workspace-expand-toggle"]')
        return self
