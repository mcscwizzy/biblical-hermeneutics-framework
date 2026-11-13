from __future__ import annotations

import os


def gui_test_server_endpoint(port: int) -> tuple[str, str]:
    """Return the listener and browser URL for an app hosted by gui-tests."""

    remote_browser = bool(os.environ.get("BHF_WEBDRIVER_URL", "").strip())
    default_browser_host = "gui-tests" if remote_browser else "127.0.0.1"
    browser_host = os.environ.get("BHF_GUI_BROWSER_HOST", default_browser_host).strip()
    if not browser_host:
        browser_host = default_browser_host

    bind_host = "127.0.0.1" if browser_host.lower() in {"127.0.0.1", "localhost"} else "0.0.0.0"
    return bind_host, f"http://{browser_host}:{port}"
