(function () {
  function resolveUrl(url) {
    const raw = String(url || "");
    if (/^(?:[a-z]+:)?\/\//i.test(raw) || raw.startsWith("data:") || raw.startsWith("blob:")) {
      return raw;
    }
    const runtime = window.BHFRuntimeConfig || {};
    const base = String(runtime.apiBaseUrl || "").replace(/\/+$/, "");
    if (!base) {
      return raw;
    }
    if (raw.startsWith("/")) {
      return `${base}${raw}`;
    }
    return `${base}/${raw}`;
  }

  async function requestJson(url, options = {}, fallbackMessage = "Request failed.") {
    const resolvedUrl = resolveUrl(url);
    const method = String(options.method || "GET").toUpperCase();
    if (isDeviceOnlyPersonalPath(url)) {
      if (method === "GET") {
        return (await localJsonResponse(url)) || emptyDeviceOnlyResponse(url);
      }
      if (isOfflineMutation(url, method)) {
        const result = await applyOfflineMutation(url, method, options, window.BHFOfflineDB);
        notifyOfflineSyncChanged();
        return result;
      }
    }
    const preferLiveTranslationState =
      method === "GET" &&
      isLiveTranslationStateRequest(url) &&
      navigator.onLine !== false;
    if (method === "GET" && isCacheableOfflineGet(url) && !preferLiveTranslationState) {
      const local = await localJsonResponse(url);
      if (local) {
        return local;
      }
    }
    try {
      const requestOptions = preferLiveTranslationState
        ? withRefreshHeader(options)
        : options;
      const response = await fetch(resolvedUrl, requestOptions);
      const data = await response.json();
      if (!response.ok) {
        if (data && data.offline) {
          const fallback = await offlineFallback(url, method, options);
          if (fallback) {
            return fallback;
          }
        }
        throw new Error(data.error || fallbackMessage);
      }
      await cacheSuccessfulJson(url, method, data);
      return data;
    } catch (error) {
      const fallback = await offlineFallback(url, method, options);
      if (fallback) {
        return fallback;
      }
      throw error;
    }
  }

  function withRefreshHeader(options) {
    const headers = new Headers(options.headers || {});
    headers.set("X-BHF-Refresh", "true");
    return {...options, headers};
  }

  async function requestText(url, options = {}, fallbackMessage = "Request failed.") {
    const local = await offlineTextFallback(url);
    if (local) {
      return local;
    }
    if (isDeviceOnlyPersonalPath(url)) {
      throw new Error("This saved study is not available on this device.");
    }
    try {
      const response = await fetch(resolveUrl(url), options);
      const data = await response.text();
      if (!response.ok) {
        const fallback = await offlineTextFallback(url);
        if (fallback) {
          return fallback;
        }
        throw new Error(data || fallbackMessage);
      }
      return data;
    } catch (error) {
      const fallback = await offlineTextFallback(url);
      if (fallback) {
        return fallback;
      }
      throw error;
    }
  }

  async function offlineTextFallback(url) {
    const offlineDb = window.BHFOfflineDB;
    if (!offlineDb || typeof offlineDb.readTextResponse !== "function") {
      return null;
    }
    try {
      return await offlineDb.readTextResponse(url);
    } catch (_error) {
      return null;
    }
  }

  async function cacheSuccessfulJson(url, method, data) {
    const offlineDb = window.BHFOfflineDB;
    if (!offlineDb) {
      return;
    }
    try {
      if (method === "GET" && isCacheableOfflineGet(url) && typeof offlineDb.cacheApiResponse === "function") {
        await offlineDb.cacheApiResponse(url, data);
      } else if (method !== "GET" && typeof offlineDb.applyOnlineMutationResponse === "function") {
        await offlineDb.applyOnlineMutationResponse(url, method, data);
      }
    } catch (_error) {
      // Offline caching should never block the live UI.
    }
  }

  async function localJsonResponse(url) {
    const offlineDb = window.BHFOfflineDB;
    if (!offlineDb || typeof offlineDb.readApiResponse !== "function") {
      return null;
    }
    try {
      return await offlineDb.readApiResponse(url);
    } catch (_error) {
      return null;
    }
  }

  async function offlineFallback(url, method, options) {
    const offlineDb = window.BHFOfflineDB;
    if (!offlineDb) {
      return null;
    }
    if (method === "GET" && isCacheableOfflineGet(url) && typeof offlineDb.readApiResponse === "function") {
      try {
        return await offlineDb.readApiResponse(url);
      } catch (_error) {
        return null;
      }
    }
    if (isOfflineMutation(url, method)) {
      const result = await applyOfflineMutation(url, method, options, offlineDb);
      notifyOfflineSyncChanged();
      return result;
    }
    return null;
  }

  async function applyOfflineMutation(url, method, options, offlineDb) {
    const body = await parseRequestBody(options);
    const path = new URL(String(url || "/"), window.location.origin).pathname;
    if (path === "/api/notes" && method === "POST" && typeof offlineDb.upsertOfflineNote === "function") {
      return offlineDb.upsertOfflineNote(body, method, path);
    }
    if (path.startsWith("/api/notes/") && method === "PUT" && typeof offlineDb.upsertOfflineNote === "function") {
      const noteId = decodeURIComponent(path.slice("/api/notes/".length));
      return offlineDb.upsertOfflineNote({ ...body, id: noteId }, method, path);
    }
    if (path.startsWith("/api/notes/") && method === "DELETE" && typeof offlineDb.deleteOfflineNote === "function") {
      const noteId = decodeURIComponent(path.slice("/api/notes/".length));
      return offlineDb.deleteOfflineNote(noteId, path);
    }
    if (path === "/api/highlights" && method === "POST" && typeof offlineDb.upsertOfflineHighlight === "function") {
      return offlineDb.upsertOfflineHighlight(body, method, path);
    }
    if (path.startsWith("/api/highlights/") && method === "DELETE" && typeof offlineDb.deleteOfflineHighlight === "function") {
      const highlightId = decodeURIComponent(path.slice("/api/highlights/".length));
      return offlineDb.deleteOfflineHighlight(highlightId, path);
    }
    if (path === "/api/map-studies" && method === "POST" && typeof offlineDb.upsertOfflineMapStudy === "function") {
      return offlineDb.upsertOfflineMapStudy(body, method, path);
    }
    if (path.startsWith("/api/map-studies/") && method === "DELETE" && typeof offlineDb.deleteOfflineMapStudy === "function") {
      const studyId = decodeURIComponent(path.slice("/api/map-studies/".length));
      return offlineDb.deleteOfflineMapStudy(studyId, path);
    }
    if (path.startsWith("/api/saved-studies/") && method === "DELETE" && typeof offlineDb.deleteOfflineSavedStudy === "function") {
      const studyId = decodeURIComponent(path.slice("/api/saved-studies/".length));
      return offlineDb.deleteOfflineSavedStudy(studyId, path);
    }
    if (path === "/api/saved-studies" && method === "POST" && typeof offlineDb.upsertOfflineSavedStudy === "function") {
      return offlineDb.upsertOfflineSavedStudy(body);
    }
    if (typeof offlineDb.enqueueMutation === "function") {
      const queued = await offlineDb.enqueueMutation({ method, url: path, body });
      return {
        queued: true,
        offline: true,
        sync_status: "pending",
        mutation_id: queued.id,
      };
    }
    return null;
  }

  async function parseRequestBody(options) {
    const raw = options && "body" in options ? options.body : null;
    if (!raw) {
      return {};
    }
    if (typeof raw === "string") {
      try {
        return JSON.parse(raw);
      } catch (_error) {
        return { raw_body: raw };
      }
    }
    if (raw instanceof FormData) {
      return Object.fromEntries(raw.entries());
    }
    if (typeof raw === "object") {
      return raw;
    }
    return {};
  }

  function isCacheableOfflineGet(url) {
    const path = new URL(String(url || "/"), window.location.origin).pathname;
    if (isAiOnlyPath(path)) {
      return false;
    }
    return [
      "/api/offline/manifest",
      "/api/offline/packs/",
      "/api/translations",
      "/api/translations/installed",
      "/api/translations/catalog",
      "/api/settings/reader",
      "/api/bible/books",
      "/api/bible/search",
      "/api/bible/",
      "/api/notes/",
      "/api/highlights/",
      "/api/saved-studies",
      "/api/canonical/search",
      "/api/canonical/objects/",
      "/api/maps/",
      "/api/map-studies",
      "/api/sources",
    ].some((prefix) => path === prefix || path.startsWith(prefix));
  }

  function isDeviceOnlyPersonalPath(url) {
    const path = new URL(String(url || "/"), window.location.origin).pathname;
    return path === "/api/notes"
      || path.startsWith("/api/notes/")
      || path === "/api/highlights"
      || path.startsWith("/api/highlights/")
      || path === "/api/saved-studies"
      || path.startsWith("/api/saved-studies/");
  }

  function emptyDeviceOnlyResponse(url) {
    const path = new URL(String(url || "/"), window.location.origin).pathname;
    if (path.startsWith("/api/notes/")) {
      return { notes: [], offline: true, device_only: true, cache_status: "generated" };
    }
    if (path.startsWith("/api/highlights/")) {
      return { highlights: [], offline: true, device_only: true, cache_status: "generated" };
    }
    return { saved_studies: [], offline: true, device_only: true, cache_status: "generated" };
  }

  function isLiveTranslationStateRequest(url) {
    const path = new URL(String(url || "/"), window.location.origin).pathname;
    return [
      "/api/translations",
      "/api/translations/installed",
      "/api/translations/catalog",
    ].includes(path);
  }

  function isOfflineMutation(url, method) {
    const path = new URL(String(url || "/"), window.location.origin).pathname;
    if (isAiOnlyPath(path)) {
      return false;
    }
    if (method === "POST" && ["/api/notes", "/api/highlights", "/api/saved-studies", "/api/map-studies", "/api/map-notes"].includes(path)) {
      return true;
    }
    if (method === "PUT" && (path.startsWith("/api/notes/") || path === "/api/settings/reader")) {
      return true;
    }
    if (method === "DELETE" && (
      path.startsWith("/api/notes/")
      || path.startsWith("/api/highlights/")
      || path.startsWith("/api/saved-studies/")
      || path.startsWith("/api/map-studies/")
    )) {
      return true;
    }
    return false;
  }

  function isAiOnlyPath(path) {
    return [
      "/ask",
      "/api/llm/health",
      "/api/bible/search/fallback",
      "/api/debug/ckl-search",
    ].some((prefix) => path === prefix || path.startsWith(prefix));
  }

  function notifyOfflineSyncChanged() {
    if (window.BHFPWA && typeof window.BHFPWA.refreshOfflineSyncControls === "function") {
      window.BHFPWA.refreshOfflineSyncControls();
    }
  }

  window.BHFApi = {
    requestJson,
    requestText,
    resolveUrl,
  };
})();
