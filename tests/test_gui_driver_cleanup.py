from types import SimpleNamespace

import pytest


def test_remote_driver_is_quit_when_offline_seed_fails(monkeypatch, tmp_path):
    selenium = pytest.importorskip("selenium")
    from selenium import webdriver

    from tests.gui import conftest as gui_conftest

    class FakeBrowser:
        quit_called = False

        def set_page_load_timeout(self, _timeout):
            pass

        def set_script_timeout(self, _timeout):
            pass

        def quit(self):
            self.quit_called = True

    browser = FakeBrowser()
    monkeypatch.setattr(webdriver, "Remote", lambda **_kwargs: browser)
    monkeypatch.setattr(
        gui_conftest,
        "_seed_browser_offline_fixture",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("offline navigation refused")),
    )
    request = SimpleNamespace(
        node=SimpleNamespace(path=SimpleNamespace(name="test_gui_case.py")),
        getfixturevalue=lambda name: "http://bhf-web:8080" if name == "base_url" else None,
    )

    fixture = gui_conftest.driver.__wrapped__(request, tmp_path, "http://selenium-chrome:4444/wd/hub")

    with pytest.raises(RuntimeError, match="offline navigation refused"):
        next(fixture)

    assert browser.quit_called
