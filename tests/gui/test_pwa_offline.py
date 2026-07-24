from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .pages import HomePage, WorkspacePage


pytestmark = [pytest.mark.gui]


def test_pwa_reader_search_context_and_sync_status_work_offline(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    _wait_for_service_worker_control(driver, wait)
    _install_offline_packs(driver, "study", "maps", "sources")
    _refresh_all_offline_data(driver)
    _enqueue_pending_note(driver)

    _set_chrome_offline(driver, True)
    try:
        driver.refresh()
        HomePage(driver, wait, base_url).wait_loaded()

        assert len(driver.find_elements(By.CSS_SELECTOR, "#chapter-reader [data-verse]")) > 0

        search_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="bible-search-input"]')))
        search_input.clear()
        search_input.send_keys("beginning")
        driver.find_element(By.CSS_SELECTOR, '[data-testid="bible-search-button"]').click()
        wait.until(lambda _driver: len(_driver.find_elements(By.CSS_SELECTOR, "#reader-search-results .search-result-card")) > 0)

        page = WorkspacePage(driver, wait, base_url)
        page.open_app_section("ask")
        page.open_tab("context")
        page.assert_tab_visible("context")

        canonical_search = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="canonical-search-input"]')))
        canonical_search.clear()
        canonical_search.send_keys("Shechem")
        page.click('[data-testid="canonical-search-button"]')
        wait.until(lambda _driver: _driver.find_element(By.CSS_SELECTOR, '[data-canonical-browser-count]').text.strip() != "0")
        wait.until(lambda _driver: "shechem" in _driver.find_element(By.CSS_SELECTOR, '[data-canonical-browser-results]').text.lower())

        page.open_reader_settings()
        assert driver.find_element(By.CSS_SELECTOR, '[data-testid="pwa-install"]').is_displayed()
        assert driver.find_element(By.CSS_SELECTOR, '[data-testid="pwa-update"]').is_displayed()
        assert driver.find_element(By.CSS_SELECTOR, '[data-testid="offline-clear-caches"]').is_displayed()
        assert driver.find_element(By.CSS_SELECTOR, '[data-testid="offline-snapshot-export"]').is_displayed()
        assert driver.find_element(By.CSS_SELECTOR, '[data-testid="offline-snapshot-import"]').is_displayed()
        wait.until(lambda _driver: "offline ready" in _driver.find_element(By.CSS_SELECTOR, "[data-offline-readiness-status]").text.lower())
        driver.find_element(By.CSS_SELECTOR, "[data-offline-readiness-details] summary").click()
        wait.until(lambda _driver: "study and maps installed" in _driver.find_element(By.CSS_SELECTOR, "[data-offline-readiness-list]").text.lower())
        _assert_snapshot_export_contains_queue(driver)
        wait.until(
            lambda _driver: "checking storage" not in _driver.find_element(
                By.CSS_SELECTOR, "[data-offline-storage-status]"
            ).text.lower()
        )
        wait.until(lambda _driver: "queued" in _driver.find_element(By.CSS_SELECTOR, "[data-offline-sync-status]").text.lower())
        assert "Retry" in driver.find_element(By.CSS_SELECTOR, "[data-offline-sync-label]").text
        driver.find_element(By.CSS_SELECTOR, "[data-offline-sync-details] summary").click()
        wait.until(lambda _driver: "create note" in _driver.find_element(By.CSS_SELECTOR, "[data-offline-sync-list]").text.lower())
        assert "Discard" in driver.find_element(By.CSS_SELECTOR, "[data-offline-sync-list]").text
        assert "Not installed" not in driver.find_element(By.CSS_SELECTOR, '[data-testid="offline-pack-study"]').text
    finally:
        _set_chrome_offline(driver, False)


def test_offline_readiness_service_worker_row_becomes_active(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    _wait_for_service_worker_control(driver, wait)

    WorkspacePage(driver, wait, base_url).open_reader_settings()
    driver.find_element(By.CSS_SELECTOR, "[data-offline-readiness-details] summary").click()
    wait.until(
        lambda _driver: "service worker" in _driver.find_element(
            By.CSS_SELECTOR, "[data-offline-readiness-list]"
        ).text.lower()
    )

    result = driver.execute_async_script(
        """
        const done = arguments[0];
        (async () => {
          if (window.BHFPWA && typeof window.BHFPWA.refreshOfflineReadinessControls === "function") {
            await window.BHFPWA.refreshOfflineReadinessControls(true);
          }
          const rows = Array.from(document.querySelectorAll("[data-offline-readiness-list] li"));
          const row = rows.find((item) => item.textContent.toLowerCase().includes("service worker"));
          const registration = "serviceWorker" in navigator
            ? await navigator.serviceWorker.getRegistration("/")
            : null;
          done({
            rowText: row ? row.textContent : "",
            controller: Boolean(navigator.serviceWorker && navigator.serviceWorker.controller),
            active: Boolean(registration && registration.active),
            waiting: Boolean(registration && registration.waiting),
            installing: Boolean(registration && registration.installing),
          });
        })().catch((error) => done({ error: String(error && error.message || error) }));
        """
    )
    assert result["rowText"].lower().endswith("active"), result


def _wait_for_service_worker_control(driver, wait) -> None:
    result = driver.execute_async_script(
        """
        const done = arguments[0];
        (async () => {
          if (!("serviceWorker" in navigator)) {
            done("service workers unavailable");
            return;
          }
          await navigator.serviceWorker.ready;
          if (!navigator.serviceWorker.controller) {
            location.reload();
            done("reload");
            return;
          }
          done(true);
        })().catch((error) => done(String(error && error.message || error)));
        """
    )
    if result == "reload":
        HomePage(driver, wait, driver.current_url.rsplit("/", 1)[0]).wait_loaded()
    elif result is not True:
        pytest.skip(f"Service worker is unavailable: {result}")
    wait.until(lambda _driver: _driver.execute_script("return Boolean(navigator.serviceWorker && navigator.serviceWorker.controller)"))


def _install_offline_packs(driver, *pack_ids: str) -> None:
    result = driver.execute_async_script(
        """
        const packs = Array.from(arguments).slice(0, -1);
        const done = arguments[arguments.length - 1];
        (async () => {
          if (!window.BHFPWA || typeof window.BHFPWA.installOfflinePack !== "function") {
            done("PWA pack installer unavailable");
            return;
          }
          for (const pack of packs) {
            await window.BHFPWA.installOfflinePack(pack);
          }
          done(true);
        })().catch((error) => done(String(error && error.message || error)));
        """,
        *pack_ids,
    )
    assert result is True, result


def _refresh_all_offline_data(driver) -> None:
    result = driver.execute_async_script(
        """
        const done = arguments[0];
        (async () => {
          if (!window.BHFPWA || typeof window.BHFPWA.refreshAllOfflineData !== "function") {
            done("offline refresh unavailable");
            return;
          }
          const result = await window.BHFPWA.refreshAllOfflineData(document.createElement("button"));
          done(result);
        })().catch((error) => done(String(error && error.message || error)));
        """
    )
    assert "study" in result["refreshed_packs"]
    assert "maps" in result["refreshed_packs"]
    assert "sources" in result["refreshed_packs"]


def test_clear_rebuildable_offline_cache_preserves_queue(driver, wait, base_url):
    HomePage(driver, wait, base_url).open().wait_loaded()
    _wait_for_service_worker_control(driver, wait)
    _install_offline_packs(driver, "study", "maps")
    _enqueue_pending_note(driver)

    result = driver.execute_async_script(
        """
        const done = arguments[0];
        (async () => {
          const before = await window.BHFOfflineDB.readinessReport();
          const button = document.createElement("button");
          const clearResult = await window.BHFPWA.clearRebuildableOfflineData(button);
          const after = await window.BHFOfflineDB.readinessReport();
          done({
            beforeMissing: before.missing_required_packs,
            afterMissing: after.missing_required_packs,
            queue: after.queue.queued_count,
            cleared: clearResult.cleared_count
          });
        })().catch((error) => done(String(error && error.message || error)));
        """
    )
    assert result["beforeMissing"] == []
    assert "study" in result["afterMissing"]
    assert "maps" in result["afterMissing"]
    assert result["queue"] >= 1
    assert result["cleared"] > 0


def _enqueue_pending_note(driver) -> None:
    result = driver.execute_async_script(
        """
        const done = arguments[0];
        (async () => {
          if (!window.BHFOfflineDB || typeof window.BHFOfflineDB.enqueueMutation !== "function") {
            done("offline DB unavailable");
            return;
          }
          await window.BHFOfflineDB.enqueueMutation({
            method: "POST",
            url: "/api/notes",
            body: {
              id: "note-offline-gui",
              book: "John",
              chapter: 1,
              start_verse: 1,
              end_verse: 1,
              selected_text: "In the beginning",
              body: "Offline GUI queued note"
            }
          });
          if (window.BHFPWA && typeof window.BHFPWA.refreshOfflineSyncControls === "function") {
            await window.BHFPWA.refreshOfflineSyncControls();
          }
          done(true);
        })().catch((error) => done(String(error && error.message || error)));
        """
    )
    assert result is True, result


def _assert_snapshot_export_contains_queue(driver) -> None:
    result = driver.execute_async_script(
        """
        const done = arguments[0];
        (async () => {
          if (!window.BHFOfflineDB || typeof window.BHFOfflineDB.exportSnapshot !== "function") {
            done("offline snapshot exporter unavailable");
            return;
          }
          const snapshot = await window.BHFOfflineDB.exportSnapshot();
          const queued = Array.isArray(snapshot.stores?.mutationQueue) ? snapshot.stores.mutationQueue : [];
          done({
            app: snapshot.app,
            queued: queued.length,
            hasNote: queued.some((mutation) => mutation.body?.id === "note-offline-gui")
          });
        })().catch((error) => done(String(error && error.message || error)));
        """
    )
    assert result["app"] == "bhf-bible-reader"
    assert result["queued"] >= 1
    assert result["hasNote"] is True


def _set_chrome_offline(driver, offline: bool) -> None:
    if not hasattr(driver, "execute_cdp_cmd"):
        pytest.skip("Chrome DevTools Protocol is unavailable for offline emulation.")
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd(
            "Network.emulateNetworkConditions",
            {
                "offline": bool(offline),
                "latency": 0,
                "downloadThroughput": 0 if offline else 500000,
                "uploadThroughput": 0 if offline else 500000,
            },
        )
    except Exception as exc:
        pytest.skip(f"Chrome offline emulation is unavailable: {exc}")
