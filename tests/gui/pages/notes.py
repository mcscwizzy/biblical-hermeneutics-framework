from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base import BasePage
from .reader import BibleReaderPage


class NotesPage(BasePage):
    def add_note(self, text: str):
        reader = BibleReaderPage(self.driver, self.wait, self.base_url)
        reader.select_verse(1)
        self.click('[data-testid="add-note-button"]')
        textarea = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="note-textarea"]')))
        textarea.clear()
        textarea.send_keys(text)
        self.click('[data-testid="save-note-button"]')
        return self

    def assert_note_visible(self, text: str):
        self.wait.until(lambda driver: text in driver.find_element(By.CSS_SELECTOR, "#notes-list").text)
        return self
