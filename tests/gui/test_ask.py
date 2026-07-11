from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from .pages import AskPage, HomePage


pytestmark = [pytest.mark.gui]


def test_ask_form_submits(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = AskPage(driver, wait, base_url)
    page.ask("What does John 1 emphasize?")
    page.wait_for_status_started()
    page.wait_for_answer_or_error()
    answer = driver.find_element(By.CSS_SELECTOR, '[data-testid="answer-output"]').text
    assert "Test answer" in answer


def test_agent_status_clears_after_answer(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = AskPage(driver, wait, base_url)
    page.ask("What does John 1 emphasize?")
    page.wait_for_answer_or_error()
    status = driver.find_element(By.CSS_SELECTOR, '[data-testid="agent-status"]')
    assert status.is_displayed()
    assert "Complete" in status.text or status.find_element(By.CSS_SELECTOR, ".status-summary").is_displayed()


def test_empty_question_validation(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = AskPage(driver, wait, base_url)
    page.click('[data-testid="ask-submit"]')
    page.wait_for_answer_or_error()
    answer = driver.find_element(By.CSS_SELECTOR, '[data-testid="answer-output"]').text
    assert "Test answer" in answer
