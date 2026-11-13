"""Fail-fast connectivity gate for the remote Chrome GUI test stack."""

from __future__ import annotations

import json
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit

import requests
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.remote.client_config import ClientConfig


def _safe_exception(exc: Exception) -> str:
    message = str(exc).splitlines()[0]
    message = re.sub(r"(?i)(https?://)([^/@\s]+@)", r"\1[redacted]@", message)
    return f"{type(exc).__name__}: {message[:300]}"


def _proxy_summary(host: str) -> None:
    configured = False
    for name in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        value = os.environ.get(name)
        if not value:
            print(f"PROXY {name}=unset", flush=True)
            continue
        configured = True
        parsed = urlsplit(value if "://" in value else f"http://{value}")
        endpoint = parsed.hostname or "unknown"
        if parsed.port:
            endpoint = f"{endpoint}:{parsed.port}"
        print(f"PROXY {name}=set endpoint={endpoint} auth={'yes' if parsed.username or parsed.password else 'no'}", flush=True)

    no_proxy = os.environ.get("NO_PROXY", os.environ.get("no_proxy", ""))
    bypass_tokens = {token.strip().lower() for token in no_proxy.split(",")}
    bypasses_host = (
        "*" in bypass_tokens
        or host.lower() in bypass_tokens
        or any(token.startswith(".") and host.lower().endswith(token) for token in bypass_tokens)
    )
    print(f"PROXY_CONFIGURED={configured} NO_PROXY_BHF_WEB={bypasses_host}", flush=True)


def _probe_runner_routes(base_url: str) -> None:
    parsed = urlsplit(base_url)
    if parsed.scheme != "http" or not parsed.hostname:
        raise RuntimeError(f"GUI base URL must be an HTTP service URL: {base_url!r}")
    port = parsed.port or 80
    addresses = sorted({entry[4][0] for entry in socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)})
    print(f"GUI_TESTS_DNS={parsed.hostname}:{port} -> {addresses}", flush=True)
    with socket.create_connection((parsed.hostname, port), timeout=3):
        print(f"GUI_TESTS_TCP={parsed.hostname}:{port} connected", flush=True)

    _proxy_summary(parsed.hostname)
    for route in ("/api/health", "/offline"):
        url = f"{base_url.rstrip('/')}{route}"
        for mode, trust_env in (("environment", True), ("direct", False)):
            session = requests.Session()
            session.trust_env = trust_env
            try:
                response = session.get(url, timeout=5)
                print(f"GUI_TESTS_HTTP_{mode.upper()} {route} status={response.status_code}", flush=True)
                response.raise_for_status()
            finally:
                session.close()
        if route == "/api/health":
            payload = response.json()
            print(f"GUI_TESTS_HEALTH={payload.get('status')}", flush=True)
            if payload.get("status") != "ok":
                raise RuntimeError(f"{route} did not report healthy application status")


def _proxy_capability_summary(capabilities: dict) -> dict:
    proxy = capabilities.get("proxy") or {}
    proxy_fields = {"httpProxy", "sslProxy", "socksProxy", "proxyAutoconfigUrl"}
    return {
        "proxy_type": proxy.get("proxyType"),
        "has_proxy_endpoint": any(proxy.get(field) for field in proxy_fields),
    }


def _probe_remote_browser(base_url: str, remote_url: str, artifacts_dir: Path | None) -> None:
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1400")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--hide-scrollbars")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    browser = None
    try:
        browser = webdriver.Remote(
            command_executor=remote_url,
            options=options,
            client_config=ClientConfig(remote_url, timeout=20),
        )
        print("REMOTE_SESSION_CREATED=1", flush=True)
        browser.set_page_load_timeout(15)
        browser.set_script_timeout(10)
        capabilities = browser.capabilities
        print(
            "REMOTE_BROWSER="
            + json.dumps(
                {
                    "name": capabilities.get("browserName"),
                    "version": capabilities.get("browserVersion"),
                    "driver": capabilities.get("chrome", {}).get("chromedriverVersion"),
                    "proxy": _proxy_capability_summary(capabilities),
                },
                sort_keys=True,
            ),
            flush=True,
        )

        browser.get(f"{base_url.rstrip('/')}/api/health")
        health = json.loads(browser.find_element("tag name", "body").text)
        print(f"CHROME_HEALTH={health.get('status')} URL={browser.current_url}", flush=True)
        if health.get("status") != "ok":
            raise RuntimeError(f"Chrome health response was not healthy: {health!r}")

        browser.get(f"{base_url.rstrip('/')}/offline")
        offline = browser.execute_script(
            "return {url:location.href, path:location.pathname, title:document.title, "
            "ready:document.readyState, responseStatus:performance.getEntriesByType('navigation')[0]?.responseStatus};"
        )
        print("CHROME_OFFLINE=" + json.dumps(offline, sort_keys=True), flush=True)
        if offline["path"] != "/offline" or offline["ready"] != "complete":
            raise RuntimeError(f"Chrome did not finish loading /offline: {offline!r}")
        if offline.get("responseStatus") not in (None, 200):
            raise RuntimeError(f"Chrome loaded /offline with HTTP {offline['responseStatus']}")

        if artifacts_dir:
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            screenshot = artifacts_dir / "gui-connectivity-smoke.png"
            browser.save_screenshot(str(screenshot))
            print(f"CHROME_SCREENSHOT={screenshot}", flush=True)
    except Exception as exc:
        print(f"GUI_CONNECTIVITY_BROWSER_FAILURE={_safe_exception(exc)}", flush=True)
        if browser is not None:
            try:
                print(f"CHROME_CURRENT_URL={browser.current_url}", flush=True)
            except WebDriverException:
                pass
            if artifacts_dir:
                try:
                    artifacts_dir.mkdir(parents=True, exist_ok=True)
                    screenshot = artifacts_dir / "gui-connectivity-smoke-failure.png"
                    browser.save_screenshot(str(screenshot))
                    print(f"CHROME_FAILURE_SCREENSHOT={screenshot}", flush=True)
                except WebDriverException:
                    pass
        raise
    finally:
        if browser is not None:
            try:
                browser.quit()
                print("REMOTE_SESSION_QUIT=1", flush=True)
            except WebDriverException as exc:
                print(f"REMOTE_SESSION_QUIT_ERROR={_safe_exception(exc)}", flush=True)


def main() -> None:
    base_url = os.environ.get("BHF_GUI_BASE_URL", "").strip()
    remote_url = os.environ.get("BHF_WEBDRIVER_URL", "").strip()
    if not base_url or not remote_url:
        raise SystemExit("BHF_GUI_BASE_URL and BHF_WEBDRIVER_URL are required for GUI connectivity smoke")

    artifact_setting = os.environ.get("BHF_GUI_ARTIFACTS_DIR", "").strip()
    artifacts_dir = Path(artifact_setting) if artifact_setting else None
    _probe_runner_routes(base_url.rstrip("/"))
    _probe_remote_browser(base_url, remote_url, artifacts_dir)
    print("GUI_CONNECTIVITY_SMOKE=PASS", flush=True)


if __name__ == "__main__":
    main()
