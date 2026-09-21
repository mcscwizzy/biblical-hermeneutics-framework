from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base import BasePage


class AskPage(BasePage):
    def open_workspace(self):
        self.click("[data-ask-bhf]")
        self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-ask-bhf-dialog]"))
        )
        return self

    def ask(self, question: str):
        self.open_workspace()
        question_box = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-ask-bhf-question]"))
        )
        question_box.clear()
        question_box.send_keys(question)
        self.click("[data-ask-bhf-primary]")
        return self

    def reference(self):
        return self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-ask-bhf-reference]"))
        ).text

    def status(self):
        return self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-ask-bhf-status]"))
        ).text

    def close(self):
        self.click("[data-ask-bhf-close]")
        return self
