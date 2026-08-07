from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base import BasePage


class BibleReaderPage(BasePage):
    def current_translation_abbreviation(self):
        select = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="translation-select"]')))
        return (select.get_attribute("value") or "").upper()

    def select_book(self, book: str):
        self.select_value('[data-testid="book-select"]', book)
        return self

    def set_chapter(self, chapter: int | str):
        self.select_value('[data-testid="chapter-input"]', str(chapter))
        return self

    def next_chapter(self):
        self.click('#chapter-reader .reader-pane.is-active [data-next-chapter]')
        return self

    def previous_chapter(self):
        self.click('#chapter-reader .reader-pane.is-active [data-prev-chapter]')
        return self

    def new_reading_tab(self):
        self.click('[data-testid="reader-new-tab"]')
        return self

    def reader_tabs(self):
        return self.driver.find_elements(By.CSS_SELECTOR, '[data-reader-tab-select]')

    def reader_panes(self):
        return self.driver.find_elements(By.CSS_SELECTOR, '#chapter-reader [data-reader-pane]')

    def active_pane_heading(self):
        return self.driver.find_element(By.CSS_SELECTOR, '#chapter-reader .reader-pane.is-active h3')

    def select_reader_tab(self, index: int):
        tabs = self.reader_tabs()
        tabs[index].click()
        return self

    def close_reader_tab(self, index: int):
        items = self.driver.find_elements(By.CSS_SELECTOR, '[data-reader-tab]')
        items[index].find_element(By.CSS_SELECTOR, '[data-reader-tab-close]').click()
        return self

    def search(self, text: str):
        self.type_into('[data-testid="bible-search-input"]', text)
        self.click('[data-testid="bible-search-button"]')
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#reader-search-results")))
        return self

    def clear_search(self):
        self.click('[data-testid="bible-search-clear"]')
        self.wait.until(lambda driver: not driver.find_element(By.CSS_SELECTOR, "#reader-search-results").is_displayed())
        return self

    def select_verse(self, reference_or_index):
        if isinstance(reference_or_index, str):
            token = reference_or_index.strip().split(":")[-1]
            token = token.split("-")[0]
            verse_number = int(token)
        else:
            verse_number = int(reference_or_index)
        script = """
            const verseNumber = arguments[0];
            const verse = document.querySelector(`#chapter-reader .reader-pane.is-active [data-verse="${verseNumber}"]`);
            if (!verse) {
              return false;
            }
            const text = verse.querySelector('.verse-text') || verse;
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(text);
            selection.removeAllRanges();
            selection.addRange(range);
            document.dispatchEvent(new Event('selectionchange'));
            return true;
        """
        self.wait.until(lambda driver: driver.execute_script(script, verse_number))
        self.wait.until(lambda driver: driver.find_element(By.CSS_SELECTOR, f'#chapter-reader .reader-pane.is-active [data-verse="{verse_number}"]').get_attribute("class").find("selected") != -1)
        return self

    def open_verse_actions(self, verse_number: int | str):
        self.click(f'#chapter-reader .reader-pane.is-active [data-verse="{int(verse_number)}"] [data-verse-actions]')
        return self
