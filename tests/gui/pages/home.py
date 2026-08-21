from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base import BasePage


class HomePage(BasePage):
    def open(self):
        return self.open_path("/")

    def wait_loaded(self):
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="reader-passage"]')))
        self.wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "#chapter-reader [data-verse]")) > 0)
        return self

    def assert_shell_visible(self):
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="app-shell"]')))
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="book-select"]')))
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="app-dock-bible"]')))
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="app-dock-explore"]')))
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="app-dock-notes"]')))
        return self
