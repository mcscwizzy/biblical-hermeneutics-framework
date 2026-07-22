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


def test_ask_follow_up_appends_to_chat(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    page = AskPage(driver, wait, base_url)
    page.ask("What does John 1 emphasize?")
    page.wait_for_chat_turns(1)

    page.ask("How does that connect to creation?")
    page.wait_for_chat_turns(2)

    user_messages = driver.find_elements(By.CSS_SELECTOR, '[data-testid="ask-chat-user-message"]')
    assistant_messages = driver.find_elements(By.CSS_SELECTOR, '[data-testid="ask-chat-assistant-message"]')
    assert len(user_messages) == 2
    assert len(assistant_messages) == 2
    assert "What does John 1 emphasize?" in user_messages[0].text
    assert "How does that connect to creation?" in user_messages[1].text
    assert all("Test answer" in message.text for message in assistant_messages)


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
