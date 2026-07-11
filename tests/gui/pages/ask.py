from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base import BasePage


class AskPage(BasePage):
    def ask(self, question: str):
        self.click('[data-testid="ask-tab"]')
        question_box = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="question-input"]')))
        question_box.clear()
        question_box.send_keys(question)
        self.click('[data-testid="ask-submit"]')
        return self

    def wait_for_status_started(self):
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="agent-status"]')))
        self.wait.until(lambda driver: driver.find_element(By.CSS_SELECTOR, '[data-testid="agent-status"]').text.strip() != "")
        return self

    def wait_for_answer_or_error(self):
        self.wait.until(
            lambda driver: (
                "Could not ask BHF" in driver.find_element(By.CSS_SELECTOR, '[data-testid="answer-output"]').text
                or "Deterministic test answer" in driver.find_element(By.CSS_SELECTOR, '[data-testid="answer-output"]').text
                or "Test answer" in driver.find_element(By.CSS_SELECTOR, '[data-testid="answer-output"]').text
                or "Answer" in driver.find_element(By.CSS_SELECTOR, '[data-testid="answer-output"]').text
            )
        )
        return self
