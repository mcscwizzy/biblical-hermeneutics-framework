(function () {
  const runtime = window.BHFRuntimeConfig || {};
  const enableServiceWorker = runtime.enableServiceWorker !== false;
  const CACHE_VERSION = "v17";
  const API_CACHE_PREFIX = "bhf-api-";
  const API_CACHE = `${API_CACHE_PREFIX}${CACHE_VERSION}`;
  const DEFAULT_AUTO_PACKS = ["study", "maps"];
  let deferredInstallPrompt = null;
  let serviceWorkerRegistration = null;
  let serviceWorkerReady = false;

  if (enableServiceWorker && "serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker
        .register("/sw.js", { scope: "/" })
        .then((registration) => {
          serviceWorkerRegistration = registration;
          wireServiceWorkerUpdateStatus(registration);
          refreshPwaLifecycleControls();
          refreshOfflineReadinessControls();
        })
        .catch((error) => {
          console.warn("BHF service worker registration failed:", error);
        });
      navigator.serviceWorker.ready
        .then((registration) => {
          serviceWorkerRegistration = registration;
          serviceWorkerReady = true;
          refreshPwaLifecycleControls();
          refreshOfflineReadinessControls();
        })
        .catch(() => undefined);
    });
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    refreshPwaLifecycleControls();
  });

  window.addEventListener("appinstalled", () => {
    deferredInstallPrompt = null;
    refreshPwaLifecycleControls();
  });

  window.addEventListener("load", () => {
    wirePwaLifecycleControls();
    wireOfflineSnapshotControls();
    wireOfflinePackControls();
    wireOfflineSyncControls();
    warmOfflineManifest();
    warmInstalledTranslations();
    warmDefaultOfflinePacks();
    replayQueuedMutations();
    refreshOfflinePackControls();
    refreshOfflineSyncControls();
    refreshOfflineReadinessControls();
    refreshPwaLifecycleControls();
  });

  window.addEventListener("online", () => {
    replayQueuedMutations();
    document.documentElement.dataset.offline = "false";
  });

  window.addEventListener("offline", () => {
    document.documentElement.dataset.offline = "true";
    refreshOfflineSyncControls();
    refreshOfflineReadinessControls();
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      refreshPwaLifecycleControls();
      refreshOfflineReadinessControls();
    }
  });

  function wireServiceWorkerUpdateStatus(registration) {
    if (!registration) {
      return;
    }
    registration.addEventListener("updatefound", () => {
      const installing = registration.installing;
      setPwaUpdateStatus("Downloading app update...", "Checking", true);
      if (!installing) {
        return;
      }
      installing.addEventListener("statechange", () => {
        if (installing.state === "installed") {
          setPwaUpdateStatus(
            navigator.serviceWorker.controller ? "Update ready on next reload" : "App ready for offline use",
            "Check",
            false
          );
        } else if (installing.state === "activated") {
          serviceWorkerReady = true;
          setPwaUpdateStatus("App is up to date", "Check", false);
          refreshOfflineReadinessControls();
        }
      });
    });
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      serviceWorkerReady = true;
      setPwaUpdateStatus("App update activated", "Check", false);
      refreshPwaLifecycleControls();
      refreshOfflineReadinessControls();
    });
  }

  async function refreshServiceWorkerRegistration() {
    if (!enableServiceWorker || !("serviceWorker" in navigator)) {
      return null;
    }
    try {
      if (typeof navigator.serviceWorker.getRegistration === "function") {
        const registration = await navigator.serviceWorker.getRegistration();
        if (registration) {
          serviceWorkerRegistration = registration;
          serviceWorkerReady = Boolean(serviceWorkerReady || navigator.serviceWorker.controller || registration.active);
        }
      }
    } catch (_error) {
      // A stale registration should not block the rest of the readiness report.
    }
    return serviceWorkerRegistration;
  }

  function wirePwaLifecycleControls() {
    document.querySelectorAll("[data-pwa-install]").forEach((button) => {
      if (button.dataset.pwaInstallBound) {
        return;
      }
      button.dataset.pwaInstallBound = "true";
      button.addEventListener("click", async () => {
        await promptForInstall(button);
      });
    });
    document.querySelectorAll("[data-pwa-update]").forEach((button) => {
      if (button.dataset.pwaUpdateBound) {
        return;
      }
      button.dataset.pwaUpdateBound = "true";
      button.addEventListener("click", async () => {
        await checkForAppUpdate(button);
      });
    });
    document.querySelectorAll("[data-offline-storage-refresh]").forEach((button) => {
      if (button.dataset.offlineStorageBound) {
        return;
      }
      button.dataset.offlineStorageBound = "true";
      button.addEventListener("click", async () => {
        await refreshOfflineStorageControls(true);
      });
    });
    document.querySelectorAll("[data-offline-readiness-refresh]").forEach((button) => {
      if (button.dataset.offlineReadinessBound) {
        return;
      }
      button.dataset.offlineReadinessBound = "true";
      button.addEventListener("click", async () => {
        await refreshOfflineReadinessControls(true);
      });
    });
    document.querySelectorAll("[data-offline-refresh-all]").forEach((button) => {
      if (button.dataset.offlineRefreshAllBound) {
        return;
      }
      button.dataset.offlineRefreshAllBound = "true";
      button.addEventListener("click", async () => {
        await refreshAllOfflineData(button);
      });
    });
    document.querySelectorAll("[data-offline-clear-caches]").forEach((button) => {
      if (button.dataset.offlineClearCachesBound) {
        return;
      }
      button.dataset.offlineClearCachesBound = "true";
      button.addEventListener("click", async () => {
        if (!window.confirm("Clear rebuildable offline caches? Notes, highlights, saved work, and queued changes are preserved.")) {
          return;
        }
        await clearRebuildableOfflineData(button);
      });
    });
  }

  function wireOfflineSnapshotControls() {
    document.querySelectorAll("[data-offline-snapshot-export]").forEach((button) => {
      if (button.dataset.offlineSnapshotExportBound) {
        return;
      }
      button.dataset.offlineSnapshotExportBound = "true";
      button.addEventListener("click", async () => {
        await exportOfflineSnapshot(button);
      });
    });
    document.querySelectorAll("[data-offline-snapshot-import]").forEach((button) => {
      if (button.dataset.offlineSnapshotImportBound) {
        return;
      }
      button.dataset.offlineSnapshotImportBound = "true";
      button.addEventListener("click", () => {
        const input = document.querySelector("[data-offline-snapshot-file]");
        input?.click();
      });
    });
    document.querySelectorAll("[data-offline-snapshot-file]").forEach((input) => {
      if (input.dataset.offlineSnapshotFileBound) {
        return;
      }
      input.dataset.offlineSnapshotFileBound = "true";
      input.addEventListener("change", async () => {
        const file = input.files?.[0];
        if (file) {
          await importOfflineSnapshot(file);
        }
        input.value = "";
      });
    });
  }

  async function exportOfflineSnapshot(button) {
    const offlineDb = window.BHFOfflineDB;
    if (!offlineDb || typeof offlineDb.exportSnapshot !== "function") {
      setLifecycleButtonState(button, "Offline snapshots unavailable", "Export", true, "offlineSnapshotExport");
      return;
    }
    setLifecycleButtonState(button, "Building snapshot...", "Working", true, "offlineSnapshotExport");
    try {
      const snapshot = await offlineDb.exportSnapshot();
      downloadJson(snapshot, `bhf-offline-snapshot-${new Date().toISOString().slice(0, 10)}.json`);
      setLifecycleButtonState(button, `${snapshotRecordCount(snapshot)} records exported`, "Export", false, "offlineSnapshotExport");
    } catch (error) {
      setLifecycleButtonState(button, error?.message || "Export failed", "Retry", false, "offlineSnapshotExport");
    }
  }

  async function importOfflineSnapshot(file) {
    const offlineDb = window.BHFOfflineDB;
    const buttons = Array.from(document.querySelectorAll("[data-offline-snapshot-import]"));
    if (!offlineDb || typeof offlineDb.importSnapshot !== "function") {
      for (const button of buttons) {
        setLifecycleButtonState(button, "Offline snapshots unavailable", "Import", true, "offlineSnapshotImport");
      }
      return;
    }
    for (const button of buttons) {
      setLifecycleButtonState(button, "Importing snapshot...", "Working", true, "offlineSnapshotImport");
    }
    try {
      const snapshot = JSON.parse(await file.text());
      const result = await offlineDb.importSnapshot(snapshot);
      for (const button of buttons) {
        setLifecycleButtonState(button, `${result.imported_count} records imported`, "Import", false, "offlineSnapshotImport");
      }
      await refreshOfflinePackControls();
      await refreshOfflineSyncControls();
      await refreshPwaLifecycleControls();
      await refreshOfflineReadinessControls();
    } catch (error) {
      for (const button of buttons) {
        setLifecycleButtonState(button, error?.message || "Import failed", "Retry", false, "offlineSnapshotImport");
      }
    }
  }

  function downloadJson(payload, filename) {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.rel = "noopener";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  function snapshotRecordCount(snapshot) {
    return Object.values(snapshot?.stores || {}).reduce((total, records) => {
      return total + (Array.isArray(records) ? records.length : 0);
    }, 0);
  }

  async function refreshAllOfflineData(button) {
    if (navigator.onLine === false) {
      setLifecycleButtonState(button, "Connect to refresh offline data", "Refresh", true, "offlineRefreshAll");
      return { refreshed_packs: [], failed_packs: ["offline"] };
    }
    setLifecycleButtonState(button, "Refreshing offline data...", "Working", true, "offlineRefreshAll");
    await warmOfflineManifest({force: true});
    await warmInstalledTranslations({force: true});
    const packIds = await refreshableOfflinePackIds();
    const failed = [];
    for (const packId of packIds) {
      try {
        await installOfflinePack(packId);
      } catch (_error) {
        failed.push(packId);
      }
    }
    await refreshOfflinePackControls();
    await refreshOfflineSyncControls();
    await refreshOfflineReadinessControls();
    await refreshPwaLifecycleControls();
    const refreshed = packIds.filter((packId) => !failed.includes(packId));
    if (failed.length) {
      setLifecycleButtonState(button, `${refreshed.length} refreshed · ${failed.length} failed`, "Retry", false, "offlineRefreshAll");
    } else {
      setLifecycleButtonState(button, `${refreshed.length} pack${refreshed.length === 1 ? "" : "s"} refreshed`, "Refresh", false, "offlineRefreshAll");
    }
    return { refreshed_packs: refreshed, failed_packs: failed };
  }

  async function clearRebuildableOfflineData(button) {
    const offlineDb = window.BHFOfflineDB;
    if (!offlineDb || typeof offlineDb.clearRebuildableCaches !== "function") {
      setLifecycleButtonState(button, "Offline cache cleanup unavailable", "Clear", true, "offlineClearCaches");
      return { cleared_count: 0 };
    }
    setLifecycleButtonState(button, "Clearing rebuildable caches...", "Working", true, "offlineClearCaches");
    const result = await offlineDb.clearRebuildableCaches();
    await clearApiCaches();
    await refreshOfflinePackControls();
    await refreshOfflineSyncControls();
    await refreshOfflineReadinessControls();
    await refreshPwaLifecycleControls();
    setLifecycleButtonState(button, `${result.cleared_count} records cleared`, "Clear", false, "offlineClearCaches");
    return result;
  }

  async function clearApiCaches() {
    if (!("caches" in window)) {
      return 0;
    }
    try {
      const keys = await caches.keys();
      const apiKeys = keys.filter((key) => key.startsWith(API_CACHE_PREFIX));
      await Promise.all(apiKeys.map((key) => caches.delete(key)));
      return apiKeys.length;
    } catch (_error) {
      return 0;
    }
  }

  async function refreshableOfflinePackIds() {
    const packIds = new Set(runtime.autoInstallOfflinePacks === false ? [] : DEFAULT_AUTO_PACKS);
    const offlineDb = window.BHFOfflineDB;
    if (offlineDb && typeof offlineDb.list === "function") {
      try {
        const metadata = await offlineDb.list("metadata");
        for (const entry of metadata) {
          const match = String(entry.id || "").match(/^pack:(.+)$/);
          if (match) {
            packIds.add(match[1]);
          }
        }
      } catch (_error) {
        // Default packs are still refreshable even if optional metadata is unavailable.
      }
    }
    return Array.from(packIds).sort();
  }

  async function refreshPwaLifecycleControls() {
    refreshInstallControls();
    refreshUpdateControls();
    await refreshOfflineStorageControls(false);
  }

  async function refreshOfflineReadinessControls(force) {
    const offlineDb = window.BHFOfflineDB;
    const buttons = Array.from(document.querySelectorAll("[data-offline-readiness-refresh]"));
    const lists = Array.from(document.querySelectorAll("[data-offline-readiness-list]"));
    if (!buttons.length && !lists.length) {
      return;
    }
    if (!offlineDb || typeof offlineDb.readinessReport !== "function") {
      setReadinessUnavailable(buttons, lists);
      return;
    }
    if (force) {
      for (const button of buttons) {
        setLifecycleButtonState(button, "Checking offline readiness...", "Working", true, "offlineReadiness");
      }
    }
    try {
      await refreshServiceWorkerRegistration();
      const report = await offlineDb.readinessReport();
      for (const button of buttons) {
        setLifecycleButtonState(button, readinessSummary(report), "Refresh", false, "offlineReadiness");
      }
      for (const list of lists) {
        list.replaceChildren(...readinessNodes(report));
      }
    } catch (_error) {
      setReadinessUnavailable(buttons, lists);
    }
  }

  function setReadinessUnavailable(buttons, lists) {
    for (const button of buttons) {
      setLifecycleButtonState(button, "Readiness unavailable", "Refresh", true, "offlineReadiness");
    }
    for (const list of lists) {
      list.replaceChildren(readinessNode("Offline database", "Unavailable", false));
    }
  }

  function readinessSummary(report) {
    const serviceWorkerStatus = currentServiceWorkerStatus();
    const missing = Array.isArray(report.missing_required_packs) ? report.missing_required_packs : [];
    const queued = Number(report.queue?.queued_count || 0);
    if (!serviceWorkerStatus.ready) {
      return `Service worker ${serviceWorkerStatus.label.toLowerCase()}`;
    }
    if (missing.length) {
      return `Missing ${missing.join(", ")} pack${missing.length === 1 ? "" : "s"}`;
    }
    if (Number(report.translations_count || 0) === 0) {
      return "No cached translations";
    }
    if (queued > 0) {
      return `${queued} queued change${queued === 1 ? "" : "s"} · offline ready`;
    }
    return "Offline ready";
  }

  function readinessNodes(report) {
    const missing = Array.isArray(report.missing_required_packs) ? report.missing_required_packs : [];
    const installedPacks = Array.isArray(report.installed_packs) ? report.installed_packs : [];
    const counts = report.counts || {};
    const queue = report.queue || {};
    const serviceWorkerStatus = currentServiceWorkerStatus();
    return [
      readinessNode("Service worker", serviceWorkerStatus.label, serviceWorkerStatus.ready),
      readinessNode(
        "Translations",
        `${Number(report.translations_count || 0)} cached`,
        Number(report.translations_count || 0) > 0
      ),
      readinessNode(
        "Required packs",
        missing.length ? `Missing ${missing.join(", ")}` : "Study and maps installed",
        missing.length === 0
      ),
      readinessNode(
        "Installed packs",
        installedPacks.length ? installedPacks.map((pack) => pack.id).join(", ") : "None installed",
        installedPacks.length > 0
      ),
      readinessNode(
        "Study data",
        `${Number(counts.canonicalObjects || 0)} objects · ${Number(counts.sources || 0)} sources`,
        Number(counts.canonicalObjects || 0) > 0
      ),
      readinessNode(
        "Local records",
        `${Number(counts.notes || 0)} notes · ${Number(counts.highlights || 0)} highlights`,
        true
      ),
      readinessNode(
        "Sync queue",
        `${Number(queue.queued_count || 0)} queued${queue.last_error ? ` · ${queue.last_error}` : ""}`,
        Number(queue.failed_count || 0) === 0
      ),
    ];
  }

  function currentServiceWorkerStatus() {
    if (!enableServiceWorker || !("serviceWorker" in navigator)) {
      if (!isSecureServiceWorkerContext()) {
        return { label: "Needs HTTPS", ready: false };
      }
      return { label: "Unavailable", ready: false };
    }
    if (navigator.serviceWorker.controller) {
      return { label: "Active", ready: true };
    }
    if (serviceWorkerReady || serviceWorkerRegistration?.active) {
      return { label: "Installed, restart app", ready: false };
    }
    if (serviceWorkerRegistration?.installing) {
      return { label: "Installing", ready: false };
    }
    if (serviceWorkerRegistration?.waiting) {
      return { label: "Waiting", ready: false };
    }
    return { label: "Starting", ready: false };
  }

  function isSecureServiceWorkerContext() {
    const hostname = window.location.hostname;
    return Boolean(
      window.isSecureContext
        || hostname === "localhost"
        || hostname === "127.0.0.1"
        || hostname === "::1"
        || hostname === "[::1]"
    );
  }

  function readinessNode(label, value, ready) {
    const item = document.createElement("li");
    item.className = `offline-readiness-item${ready ? " is-ready" : " is-warn"}`;

    const labelNode = document.createElement("span");
    labelNode.className = "offline-readiness-label";
    labelNode.textContent = label;

    const valueNode = document.createElement("span");
    valueNode.className = "offline-readiness-value";
    valueNode.textContent = value;

    item.append(labelNode, valueNode);
    return item;
  }

  function refreshInstallControls() {
    const installed = isStandaloneDisplay();
    document.querySelectorAll("[data-pwa-install]").forEach((button) => {
      if (installed) {
        setLifecycleButtonState(button, "Installed as an app", "Open", true, "pwaInstall");
      } else if (deferredInstallPrompt) {
        setLifecycleButtonState(button, "Ready to install", "Install", false, "pwaInstall");
      } else {
        setLifecycleButtonState(button, "Use the browser install menu", "Install", true, "pwaInstall");
      }
    });
  }

  function refreshUpdateControls() {
    document.querySelectorAll("[data-pwa-update]").forEach((button) => {
      if (!enableServiceWorker || !("serviceWorker" in navigator)) {
        setLifecycleButtonState(button, "Updates unavailable", "Check", true, "pwaUpdate");
      } else if (!serviceWorkerRegistration) {
        setLifecycleButtonState(button, "Service worker starting", "Check", true, "pwaUpdate");
      } else {
        setLifecycleButtonState(button, "App is up to date", "Check", false, "pwaUpdate");
      }
    });
  }

  async function refreshOfflineStorageControls(force) {
    const buttons = Array.from(document.querySelectorAll("[data-offline-storage-refresh]"));
    if (!buttons.length) {
      return;
    }
    if (!("storage" in navigator) || typeof navigator.storage.estimate !== "function") {
      for (const button of buttons) {
        setLifecycleButtonState(button, "Storage estimate unavailable", "Refresh", true, "offlineStorage");
      }
      return;
    }
    if (force) {
      for (const button of buttons) {
        setLifecycleButtonState(button, "Checking storage...", "Working", true, "offlineStorage");
      }
    }
    try {
      const estimate = await navigator.storage.estimate();
      const used = formatBytes(estimate.usage || 0);
      const quota = estimate.quota ? formatBytes(estimate.quota) : "";
      const status = quota ? `${used} used of ${quota}` : `${used} used`;
      for (const button of buttons) {
        setLifecycleButtonState(button, status, "Refresh", false, "offlineStorage");
      }
    } catch (_error) {
      for (const button of buttons) {
        setLifecycleButtonState(button, "Storage estimate unavailable", "Refresh", false, "offlineStorage");
      }
    }
  }

  async function promptForInstall(button) {
    if (isStandaloneDisplay()) {
      setLifecycleButtonState(button, "Installed as an app", "Open", true, "pwaInstall");
      return;
    }
    if (!deferredInstallPrompt) {
      setLifecycleButtonState(button, "Use the browser install menu", "Install", true, "pwaInstall");
      return;
    }
    setLifecycleButtonState(button, "Opening install prompt...", "Working", true, "pwaInstall");
    deferredInstallPrompt.prompt();
    const choice = await deferredInstallPrompt.userChoice.catch(() => null);
    deferredInstallPrompt = null;
    if (choice?.outcome === "accepted") {
      setLifecycleButtonState(button, "Install accepted", "Install", true, "pwaInstall");
    } else {
      setLifecycleButtonState(button, "Install dismissed", "Install", true, "pwaInstall");
    }
  }

  async function checkForAppUpdate(button) {
    if (!serviceWorkerRegistration || typeof serviceWorkerRegistration.update !== "function") {
      setLifecycleButtonState(button, "Service worker starting", "Check", true, "pwaUpdate");
      return;
    }
    setLifecycleButtonState(button, "Checking for update...", "Working", true, "pwaUpdate");
    try {
      await serviceWorkerRegistration.update();
      setLifecycleButtonState(button, "App is up to date", "Check", false, "pwaUpdate");
    } catch (error) {
      setLifecycleButtonState(button, error?.message || "Update check failed", "Retry", false, "pwaUpdate");
    }
  }

  function setPwaUpdateStatus(status, label, disabled) {
    document.querySelectorAll("[data-pwa-update]").forEach((button) => {
      setLifecycleButtonState(button, status, label, disabled, "pwaUpdate");
    });
  }

  function setLifecycleButtonState(button, status, label, disabled, namespace) {
    const statusNode = button.querySelector(`[data-${dashCase(namespace)}-status]`);
    const labelNode = button.querySelector(`[data-${dashCase(namespace)}-label]`);
    if (statusNode) {
      statusNode.textContent = status;
    }
    if (labelNode) {
      labelNode.textContent = label;
    }
    button.disabled = Boolean(disabled);
  }

  function dashCase(value) {
    return String(value || "").replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
  }

  function isStandaloneDisplay() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      window.matchMedia("(display-mode: fullscreen)").matches ||
      window.navigator.standalone === true
    );
  }

  function formatBytes(value) {
    const bytes = Number(value || 0);
    if (!Number.isFinite(bytes) || bytes <= 0) {
      return "0 B";
    }
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let index = 0;
    while (size >= 1024 && index < units.length - 1) {
      size /= 1024;
      index += 1;
    }
    return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
  }

  async function warmOfflineManifest({force = false} = {}) {
    const offlineDb = window.BHFOfflineDB;
    if (!offlineDb || typeof offlineDb.cacheApiResponse !== "function") {
      return;
    }
    try {
      if (!force && typeof offlineDb.readApiResponse === "function" && await offlineDb.readApiResponse("/api/offline/manifest")) {
        return;
      }
      const response = await fetch("/api/offline/manifest", {
        headers: { Accept: "application/json", ...(force ? {"X-BHF-Refresh": "true"} : {}) },
      });
      if (!response.ok) {
        return;
      }
      await offlineDb.cacheApiResponse("/api/offline/manifest", await response.json());
    } catch (_error) {
      // The service worker and IndexedDB fallback handle actual offline use.
    }
  }

  async function warmInstalledTranslations({force = false} = {}) {
    const offlineDb = window.BHFOfflineDB;
    if (!offlineDb || typeof offlineDb.cacheApiResponse !== "function") {
      return;
    }
    try {
      let data = null;
      const refreshFromServer = force || navigator.onLine !== false;
      let loadedFromServer = false;
      if (!refreshFromServer && typeof offlineDb.readApiResponse === "function") {
        data = await offlineDb.readApiResponse("/api/translations/installed");
      }
      if (!data) {
        const response = await fetch("/api/translations/installed", {
          headers: {
            Accept: "application/json",
            ...(refreshFromServer ? {"X-BHF-Refresh": "true"} : {}),
          },
        });
        if (!response.ok) {
          return;
        }
        data = await response.json();
        await offlineDb.cacheApiResponse("/api/translations/installed", data);
        loadedFromServer = true;
      }
      const installed = Array.isArray(data.translations) ? data.translations : [];
      if (loadedFromServer) {
        await reconcileCachedTranslations(
          offlineDb,
          installed.map((translation) => String(translation?.id || "").toLowerCase()),
        );
      }
      for (const translation of installed) {
        if (!translation?.id || translation.can_select === false) {
          continue;
        }
        await warmTranslationDataset(translation.id, offlineDb, {force});
      }
    } catch (_error) {
      // Offline packs are opportunistic; the app remains usable with cached data.
    }
  }

  async function reconcileCachedTranslations(offlineDb, installedIds) {
    if (typeof offlineDb.list !== "function" || typeof offlineDb.remove !== "function") {
      return;
    }
    const installed = new Set(installedIds.filter(Boolean));
    installed.add("asv");

    const cachedTranslations = await offlineDb.list("translations");
    for (const entry of cachedTranslations) {
      if (entry?.payload?.installation?.device_local) {
        installed.add(String(entry.id || "").toLowerCase());
      }
    }
    await Promise.all(
      cachedTranslations
        .filter((entry) => !installed.has(String(entry?.id || "").toLowerCase()))
        .map((entry) => {
          const id = String(entry?.id || "").toLowerCase();
          return Promise.all([
            offlineDb.remove("translations", entry.id),
            offlineDb.remove("apiResponses", `/api/translations/${encodeURIComponent(id)}/offline-data`),
          ]);
        }),
    );

    for (const url of ["/api/translations", "/api/translations/installed", "/api/translations/catalog"]) {
      const cached = typeof offlineDb.get === "function"
        ? await offlineDb.get("apiResponses", url)
        : null;
      if (!cached?.payload) {
        continue;
      }
      const payload = sanitizeTranslationState(cached.payload, installed);
      await offlineDb.cacheApiResponse(url, payload);
    }
  }

  function sanitizeTranslationState(payload, installedIds) {
    const state = {...payload};
    if (Array.isArray(state.translations)) {
      state.translations = state.translations.filter((entry) => {
        const id = String(entry?.id || "").toLowerCase();
        return !entry?.installed || installedIds.has(id);
      });
    }
    if (Array.isArray(state.catalog)) {
      state.catalog = state.catalog.filter((entry) => {
        const id = String(entry?.id || "").toLowerCase();
        return !entry?.installed || installedIds.has(id);
      });
    }
    state.sections = {...(state.sections || {})};
    if (Array.isArray(state.sections.installed)) {
      state.sections.installed = state.sections.installed.filter((entry) =>
        installedIds.has(String(entry?.id || "").toLowerCase()),
      );
    }
    return state;
  }

  async function warmTranslationDataset(translationId, offlineDb, {force = false} = {}) {
    const url = `/api/translations/${encodeURIComponent(String(translationId).toLowerCase())}/offline-data`;
    try {
      if (!force) {
        const localDataset = typeof offlineDb.get === "function"
          ? await offlineDb.get("translations", String(translationId).toLowerCase())
          : null;
        const localResponse = typeof offlineDb.readApiResponse === "function"
          ? await offlineDb.readApiResponse(url)
          : null;
        if (localDataset || localResponse) {
          return;
        }
      }
      const response = await fetch(url, {
        headers: { Accept: "application/json", ...(force ? {"X-BHF-Refresh": "true"} : {}) },
      });
      if (response.ok) {
        await offlineDb.cacheApiResponse(url, await response.json());
      }
    } catch (_error) {
      // Individual translations can fail without blocking other offline data.
    }
  }

  async function warmDefaultOfflinePacks() {
    if (runtime.autoInstallOfflinePacks === false) {
      return;
    }
    for (const packId of DEFAULT_AUTO_PACKS) {
      const offlineDb = window.BHFOfflineDB;
      const installed = offlineDb && typeof offlineDb.get === "function"
        ? await offlineDb.get("metadata", `pack:${packId}`)
        : null;
      if (!installed) {
        await installOfflinePack(packId);
      }
    }
  }

  async function installOfflinePack(packId) {
    const normalized = String(packId || "").trim().toLowerCase();
    if (!normalized) {
      return null;
    }
    const offlineDb = window.BHFOfflineDB;
    const packUrl = `/api/offline/packs/${encodeURIComponent(normalized)}`;
    const response = await fetch(packUrl, {
      headers: { Accept: "application/json", "X-BHF-Refresh": "true" },
    });
    const pack = await response.json();
    if (!response.ok) {
      throw new Error(pack.error || `Could not install offline pack: ${normalized}`);
    }
    if (offlineDb && typeof offlineDb.cacheApiResponse === "function") {
      await offlineDb.cacheApiResponse(packUrl, pack);
      for (const entry of Array.isArray(pack.responses) ? pack.responses : []) {
        if (entry?.url && entry.payload !== undefined) {
          await offlineDb.cacheApiResponse(entry.url, entry.payload);
        }
      }
    }
    await ensureServiceWorkerReady();
    await cachePackResponses(pack);
    await refreshOfflinePackControls();
    await refreshOfflineReadinessControls();
    return pack;
  }

  async function ensureServiceWorkerReady(timeoutMs = 4000) {
    if (!enableServiceWorker || !("serviceWorker" in navigator)) {
      return null;
    }
    if (navigator.serviceWorker.controller || serviceWorkerReady) {
      return serviceWorkerRegistration;
    }
    await refreshServiceWorkerRegistration();
    if (navigator.serviceWorker.controller || serviceWorkerReady) {
      return serviceWorkerRegistration;
    }
    try {
      const registration = await Promise.race([
        navigator.serviceWorker.ready,
        new Promise((resolve) => window.setTimeout(() => resolve(null), timeoutMs)),
      ]);
      if (registration) {
        serviceWorkerRegistration = registration;
        serviceWorkerReady = true;
      }
    } catch (_error) {
      // Cache Storage may still be available even when Safari delays controller ownership.
    }
    return serviceWorkerRegistration;
  }

  function wireOfflinePackControls() {
    document.querySelectorAll("[data-offline-pack]").forEach((button) => {
      if (button.dataset.offlinePackBound) {
        return;
      }
      button.dataset.offlinePackBound = "true";
      button.addEventListener("click", async () => {
        const packId = button.dataset.offlinePack || "";
        setPackButtonState(button, "Installing...", "Working", true);
        try {
          await installOfflinePack(packId);
        } catch (error) {
          setPackButtonState(button, error?.message || "Install failed", "Retry", false);
        }
      });
    });
  }

  async function refreshOfflinePackControls() {
    const offlineDb = window.BHFOfflineDB;
    if (!offlineDb || typeof offlineDb.get !== "function") {
      return;
    }
    const buttons = Array.from(document.querySelectorAll("[data-offline-pack]"));
    for (const button of buttons) {
      const packId = button.dataset.offlinePack || "";
      try {
        const entry = await offlineDb.get("metadata", `pack:${packId}`);
        if (!entry) {
          setPackButtonState(button, "Not installed", "Install", false);
          continue;
        }
        const payload = entry.payload || {};
        const count = payload.object_count ?? payload.response_count;
        const detail = Number.isFinite(Number(count)) ? `${count} item${Number(count) === 1 ? "" : "s"}` : "Ready";
        setPackButtonState(button, `${detail} · ${formatPackTime(entry.cachedAt)}`, "Refresh", false);
      } catch (_error) {
        setPackButtonState(button, "Unavailable", "Install", false);
      }
    }
    await refreshOfflineReadinessControls();
  }

  function setPackButtonState(button, status, label, disabled) {
    const statusNode = button.querySelector("[data-offline-pack-status]");
    const labelNode = button.querySelector("[data-offline-pack-label]");
    if (statusNode) {
      statusNode.textContent = status;
    }
    if (labelNode) {
      labelNode.textContent = label;
    }
    button.disabled = Boolean(disabled);
  }

  function formatPackTime(value) {
    if (!value) {
      return "installed";
    }
    try {
      return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
    } catch (_error) {
      return "installed";
    }
  }

  async function cachePackResponses(pack) {
    if (!("caches" in window)) {
      return;
    }
    const cache = await openApiCache();
    if (!cache) {
      return;
    }
    for (const entry of Array.isArray(pack.responses) ? pack.responses : []) {
      if (!entry?.url || entry.payload === undefined) {
        continue;
      }
      await cache.put(
        new Request(entry.url, { headers: { Accept: "application/json" } }),
        new Response(JSON.stringify(entry.payload), {
          headers: {
            "Content-Type": "application/json",
            "X-BHF-Offline-Pack": pack.pack_id || "unknown",
          },
        })
      );
    }
  }

  async function openApiCache() {
    try {
      const keys = await caches.keys();
      const existing =
        keys.find((key) => key === API_CACHE) ||
        keys.find((key) => key.startsWith(API_CACHE_PREFIX));
      return caches.open(existing || API_CACHE);
    } catch (_error) {
      return null;
    }
  }

  async function replayQueuedMutations() {
    const offlineDb = window.BHFOfflineDB;
    if (!offlineDb || typeof offlineDb.queuedMutations !== "function" || typeof offlineDb.removeMutation !== "function") {
      return;
    }
    if (typeof offlineDb.purgeDeviceOnlyMutations === "function") {
      try {
        await offlineDb.purgeDeviceOnlyMutations();
      } catch (_error) {
        // Purging obsolete personal sync entries should not block map sync.
      }
    }
    if (navigator.onLine === false) {
      await refreshOfflineSyncControls();
      return;
    }
    let mutations = [];
    try {
      mutations = await offlineDb.queuedMutations();
    } catch (_error) {
      return;
    }
    for (const mutation of mutations) {
      try {
        const response = await fetch(mutation.url, requestOptionsForMutation(mutation));
        if (response.ok || (mutation.method === "DELETE" && response.status === 404)) {
          if (typeof offlineDb.markMutationAttempt === "function") {
            await offlineDb.markMutationAttempt(mutation.id, { failed: false });
          }
          await offlineDb.removeMutation(mutation.id);
        } else {
          if (typeof offlineDb.markMutationAttempt === "function") {
            await offlineDb.markMutationAttempt(mutation.id, {
              failed: true,
              error: await responseErrorMessage(response),
            });
          }
          break;
        }
      } catch (error) {
        if (typeof offlineDb.markMutationAttempt === "function") {
          await offlineDb.markMutationAttempt(mutation.id, {
            failed: true,
            error: error?.message || "Network unavailable.",
          });
        }
        break;
      }
    }
    await refreshOfflineSyncControls();
  }

  function wireOfflineSyncControls() {
    document.querySelectorAll("[data-offline-sync-retry]").forEach((button) => {
      if (button.dataset.offlineSyncBound) {
        return;
      }
      button.dataset.offlineSyncBound = "true";
      button.addEventListener("click", async () => {
        setSyncButtonState(button, "Syncing queued changes...", "Working", true);
        await replayQueuedMutations();
      });
    });
    document.querySelectorAll("[data-offline-sync-list]").forEach((list) => {
      if (list.dataset.offlineSyncListBound) {
        return;
      }
      list.dataset.offlineSyncListBound = "true";
      list.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-offline-sync-discard]");
        if (!button) {
          return;
        }
        const offlineDb = window.BHFOfflineDB;
        if (!offlineDb || typeof offlineDb.removeMutation !== "function") {
          return;
        }
        button.disabled = true;
        await offlineDb.removeMutation(button.dataset.offlineSyncDiscard || "");
        await refreshOfflineSyncControls();
      });
    });
  }

  async function refreshOfflineSyncControls() {
    const offlineDb = window.BHFOfflineDB;
    const buttons = Array.from(document.querySelectorAll("[data-offline-sync-retry]"));
    const lists = Array.from(document.querySelectorAll("[data-offline-sync-list]"));
    if ((!buttons.length && !lists.length) || !offlineDb || typeof offlineDb.mutationQueueSummary !== "function") {
      return;
    }
    if (typeof offlineDb.purgeDeviceOnlyMutations === "function") {
      try {
        await offlineDb.purgeDeviceOnlyMutations();
      } catch (_error) {
        // Obsolete personal queue entries should not block map sync status.
      }
    }
    let summary = null;
    try {
      summary = await offlineDb.mutationQueueSummary();
    } catch (_error) {
      summary = null;
    }
    for (const button of buttons) {
      if (!summary) {
        setSyncButtonState(button, "Sync status unavailable", "Retry", false);
      } else if (navigator.onLine === false && Number(summary.queued_count || 0) > 0) {
        setSyncButtonState(button, `${summary.queued_count} queued · offline`, "Retry", true);
      } else if (Number(summary.queued_count || 0) === 0) {
        setSyncButtonState(button, "All local changes synced", "Retry", false);
      } else if (Number(summary.failed_count || 0) > 0) {
        setSyncButtonState(button, `${summary.queued_count} queued · ${summary.last_error || "needs retry"}`, "Retry", false);
      } else {
        setSyncButtonState(button, `${summary.queued_count} queued`, "Retry", false);
      }
    }
    await renderOfflineSyncDetails();
  }

  function setSyncButtonState(button, status, label, disabled) {
    const statusNode = button.querySelector("[data-offline-sync-status]");
    const labelNode = button.querySelector("[data-offline-sync-label]");
    if (statusNode) {
      statusNode.textContent = status;
    }
    if (labelNode) {
      labelNode.textContent = label;
    }
    button.disabled = Boolean(disabled);
  }

  async function renderOfflineSyncDetails() {
    const offlineDb = window.BHFOfflineDB;
    const lists = Array.from(document.querySelectorAll("[data-offline-sync-list]"));
    if (!lists.length) {
      return;
    }
    if (!offlineDb || typeof offlineDb.queuedMutations !== "function") {
      for (const list of lists) {
        list.replaceChildren(emptySyncNode("Offline queue unavailable."));
      }
      return;
    }
    let mutations = [];
    try {
      mutations = await offlineDb.queuedMutations();
    } catch (_error) {
      for (const list of lists) {
        list.replaceChildren(emptySyncNode("Offline queue unavailable."));
      }
      return;
    }
    for (const list of lists) {
      if (!mutations.length) {
        list.replaceChildren(emptySyncNode("No queued offline changes."));
        continue;
      }
      list.replaceChildren(...mutations.map((mutation) => mutationNode(mutation)));
    }
  }

  function emptySyncNode(message) {
    const node = document.createElement("p");
    node.className = "offline-sync-empty";
    node.textContent = message;
    return node;
  }

  function mutationNode(mutation) {
    const item = document.createElement("article");
    item.className = "offline-sync-item";

    const copy = document.createElement("span");
    copy.className = "offline-sync-copy";

    const title = document.createElement("strong");
    title.textContent = mutationTitle(mutation);

    const meta = document.createElement("span");
    meta.className = "offline-sync-meta";
    meta.textContent = mutationMeta(mutation);

    copy.append(title, meta);
    if (mutation.lastError) {
      const error = document.createElement("span");
      error.className = "offline-sync-error";
      error.textContent = mutation.lastError;
      copy.append(error);
    }

    const discard = document.createElement("button");
    discard.type = "button";
    discard.className = "offline-sync-discard";
    discard.dataset.offlineSyncDiscard = mutation.id || "";
    discard.textContent = "Discard";
    discard.title = "Remove this queued offline change";

    item.append(copy, discard);
    return item;
  }

  function mutationTitle(mutation) {
    const method = String(mutation.method || "GET").toUpperCase();
    const url = String(mutation.url || "");
    const action = method === "DELETE" ? "Delete" : method === "PUT" || method === "PATCH" ? "Update" : "Create";
    if (url.startsWith("/api/notes")) {
      return `${action} note`;
    }
    if (url.startsWith("/api/highlights")) {
      return `${action} highlight`;
    }
    if (url.startsWith("/api/saved-studies")) {
      return `${action} saved study`;
    }
    return `${method} ${url || "queued change"}`;
  }

  function mutationMeta(mutation) {
    const parts = [];
    if (mutation.store) {
      parts.push(String(mutation.store));
    }
    if (mutation.recordId) {
      parts.push(String(mutation.recordId));
    }
    if (Number(mutation.attempts || 0) > 0) {
      parts.push(`${mutation.attempts} attempt${Number(mutation.attempts) === 1 ? "" : "s"}`);
    }
    if (mutation.createdAt) {
      parts.push(formatQueueTime(mutation.createdAt));
    }
    return parts.join(" · ") || "Waiting to sync";
  }

  function formatQueueTime(value) {
    try {
      return new Date(value).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_error) {
      return "Queued";
    }
  }

  async function responseErrorMessage(response) {
    try {
      const data = await response.clone().json();
      return data.error || `Sync failed with HTTP ${response.status}.`;
    } catch (_error) {
      return `Sync failed with HTTP ${response.status}.`;
    }
  }

  function requestOptionsForMutation(mutation) {
    const method = String(mutation.method || "GET").toUpperCase();
    const options = {
      method,
      headers: { Accept: "application/json" },
    };
    if (method !== "GET" && method !== "DELETE") {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(mutation.body || {});
    }
    return options;
  }

  window.BHFPWA = {
    installOfflinePack,
    replayQueuedMutations,
    refreshOfflinePackControls,
    refreshOfflineSyncControls,
    renderOfflineSyncDetails,
    refreshPwaLifecycleControls,
    refreshOfflineReadinessControls,
    refreshAllOfflineData,
    clearRebuildableOfflineData,
    exportOfflineSnapshot,
    importOfflineSnapshot,
  };
})();
