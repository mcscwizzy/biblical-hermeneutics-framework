import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from tests.gui.pages import HomePage
from tests.gui.viewport import set_viewport
from tests.gui.ne11d1.test_ed7_reader_first_acceptance import _open_explorer, _select_passage

@pytest.mark.gui
def test_reader_topics_on_mobile(driver, ne11d1_base_url):
    wait = WebDriverWait(driver, 90)
    cases = [
        {'book':'Jeremiah','chapter':32,'verses':[1], 'reference':'Jeremiah 32:1'},
        {'book':'Genesis','chapter':6,'verses':[1,2,3,4], 'reference':'Genesis 6:1-4'},
        {'book':'Psalms','chapter':82,'verses':[1,2,3,4,5,6,7,8], 'reference':'Psalms 82:1-8'},
        {'book':'Jonah','chapter':1,'verses':[17], 'reference':'Jonah 1:17'},
    ]
    sources = 0
    cited_sources = 0
    for case in cases:
        set_viewport(driver, 390, 844, mobile=True)
        HomePage(driver, wait, ne11d1_base_url).open().wait_loaded()
        set_viewport(driver, 390, 844, mobile=True)
        _select_passage(driver, wait, case)
        explorer = _open_explorer(driver, wait)
        explorer = wait.until(lambda d: d.find_element(By.CSS_SELECTOR, '.narrative-explorer'))
        assert f"Current passage: {case['reference']}" not in explorer.text
        assert case['reference'] in explorer.find_element(By.CSS_SELECTOR, '.narrative-explorer-header h3').get_attribute('aria-label')
        assert len(explorer.find_elements(By.CSS_SELECTOR, '.narrative-explorer-category-card')) == 6
        assert 'Find a source' not in explorer.text
        ids = [x.get_attribute('data-section-id') for x in explorer.find_elements(By.CSS_SELECTOR, '.narrative-explorer-category-card')]
        for ident in ids:
            button = driver.find_element(By.CSS_SELECTOR, f'.narrative-explorer-category-card[data-section-id="{ident}"]')
            driver.execute_script('arguments[0].click()', button)
            pane = driver.find_element(By.CSS_SELECTOR, '.narrative-explorer')
            assert 'Browse more research' not in pane.text
            assert not pane.find_elements(By.CSS_SELECTOR, '.narrative-explorer-record-list')
            for disclosure in pane.find_elements(By.CSS_SELECTOR, 'details.narrative-explorer-provenance'):
                assert disclosure.find_element(By.CSS_SELECTOR, 'summary').text == 'Supporting sources'
                assert not disclosure.get_attribute('open')
                if disclosure.find_elements(By.CSS_SELECTOR, '.narrative-explorer-bibliography-entry'):
                    driver.execute_script('arguments[0].click()', disclosure.find_element(By.CSS_SELECTOR, 'summary'))
                    assert disclosure.get_attribute('open') is not None
                    assert disclosure.find_element(By.CSS_SELECTOR, '.narrative-explorer-bibliography-entry').text.strip()
                    cited_sources += 1
                sources += 1
            if case['book'] == 'Jonah' and ident == 'themes_biblical_connections':
                assert any('Matthew 12:40' in article.text for article in pane.find_elements(By.CSS_SELECTOR, '.narrative-explorer-related-passage'))
            assert driver.execute_script('return document.documentElement.scrollWidth <= window.innerWidth')
            driver.execute_script('arguments[0].click()', pane.find_element(By.CSS_SELECTOR, '.narrative-explorer-back-topics'))
    assert sources > 0
    assert cited_sources > 0
    print(f'Mobile four passages passed; {sources} supporting source disclosures')
