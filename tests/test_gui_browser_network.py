from tests.gui.network import gui_test_server_endpoint


def test_local_browser_uses_loopback_for_test_server(monkeypatch):
    monkeypatch.delenv("BHF_WEBDRIVER_URL", raising=False)
    monkeypatch.delenv("BHF_GUI_BROWSER_HOST", raising=False)

    bind_host, base_url = gui_test_server_endpoint(43210)

    assert bind_host == "127.0.0.1"
    assert base_url == "http://127.0.0.1:43210"


def test_remote_browser_uses_compose_service_address(monkeypatch):
    monkeypatch.setenv("BHF_WEBDRIVER_URL", "http://selenium-chrome:4444/wd/hub")
    monkeypatch.delenv("BHF_GUI_BROWSER_HOST", raising=False)

    bind_host, base_url = gui_test_server_endpoint(43210)

    assert bind_host == "0.0.0.0"
    assert base_url == "http://gui-tests:43210"


def test_remote_browser_host_can_be_overridden(monkeypatch):
    monkeypatch.setenv("BHF_WEBDRIVER_URL", "http://selenium-chrome:4444/wd/hub")
    monkeypatch.setenv("BHF_GUI_BROWSER_HOST", "gui-runner")

    bind_host, base_url = gui_test_server_endpoint(43210)

    assert bind_host == "0.0.0.0"
    assert base_url == "http://gui-runner:43210"
