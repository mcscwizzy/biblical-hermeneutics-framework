const CACHE_PREFIX = "bhf.map-service:v2:";
const LEGACY_CACHE_PREFIX = "bhf.map-service:";
const MAX_LOCAL_ENTRY_BYTES = 512 * 1024;
const MAX_LOCAL_TOTAL_BYTES = 2 * 1024 * 1024;
const MAX_LOCAL_ENTRIES = 16;
const memoryCache = new Map();
const inFlightRequests = new Map();

function clearLegacyMapCache() {
  if (typeof localStorage === "undefined") return;
  try {
    const legacyKeys = [];
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (key?.startsWith(LEGACY_CACHE_PREFIX) && !key.startsWith(CACHE_PREFIX)) {
        legacyKeys.push(key);
      }
    }
    for (const key of legacyKeys) localStorage.removeItem(key);
  } catch {
    // Ignore storage access failures; versioned URLs and the Service Worker still isolate current data.
  }
}

clearLegacyMapCache();

function cacheKeyFor(url) {
  return `${CACHE_PREFIX}${url}`;
}

function readCachedValue(url) {
  if (memoryCache.has(url)) {
    return memoryCache.get(url);
  }
  if (typeof localStorage === "undefined") {
    return null;
  }
  try {
    const raw = localStorage.getItem(cacheKeyFor(url));
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || !("value" in parsed)) {
      return null;
    }
    memoryCache.set(url, parsed.value);
    return parsed.value;
  } catch {
    return null;
  }
}

function localCacheEntries() {
  if (typeof localStorage === "undefined") {
    return [];
  }
  const entries = [];
  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index);
    if (!key || !key.startsWith(CACHE_PREFIX)) continue;
    try {
      const raw = localStorage.getItem(key);
      const parsed = raw ? JSON.parse(raw) : null;
      entries.push({
        key,
        bytes: raw ? raw.length * 2 : 0,
        cachedAt: String(parsed?.cachedAt || ""),
      });
    } catch {
      entries.push({key, bytes: 0, cachedAt: ""});
    }
  }
  return entries.sort((left, right) => left.cachedAt.localeCompare(right.cachedAt));
}

function writeCachedValue(url, value, responseBytes) {
  memoryCache.set(url, value);
  if (
    typeof localStorage === "undefined"
    || !Number.isFinite(responseBytes)
    || responseBytes < 0
    || responseBytes > MAX_LOCAL_ENTRY_BYTES
  ) {
    return;
  }
  try {
    const key = cacheKeyFor(url);
    const serialized = JSON.stringify({cachedAt: new Date().toISOString(), value});
    const bytes = serialized.length * 2;
    if (bytes > MAX_LOCAL_ENTRY_BYTES) return;

    const entries = localCacheEntries();
    let totalBytes = entries.reduce((total, entry) => total + entry.bytes, 0);
    let entryCount = entries.length;
    const previous = entries.find((entry) => entry.key === key);
    if (previous) {
      localStorage.removeItem(key);
      totalBytes -= previous.bytes;
      entryCount -= 1;
    }
    for (const entry of entries) {
      if (totalBytes + bytes <= MAX_LOCAL_TOTAL_BYTES && entryCount < MAX_LOCAL_ENTRIES) break;
      if (entry.key === key) continue;
      localStorage.removeItem(entry.key);
      totalBytes -= entry.bytes;
      entryCount -= 1;
    }
    if (totalBytes + bytes > MAX_LOCAL_TOTAL_BYTES || entryCount >= MAX_LOCAL_ENTRIES) return;
    localStorage.setItem(key, serialized);
  } catch {
    // Ignore storage quota and privacy-mode failures.
  }
}

export function invalidateMapCache(match = "") {
  const matcher = String(match || "").trim();
  for (const key of Array.from(memoryCache.keys())) {
    if (!matcher || key.includes(matcher)) {
      memoryCache.delete(key);
    }
  }
  if (typeof localStorage === "undefined") {
    return;
  }
  try {
    const keys = [];
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (key && key.startsWith(CACHE_PREFIX) && (!matcher || key.includes(matcher))) {
        keys.push(key);
      }
    }
    for (const key of keys) {
      localStorage.removeItem(key);
    }
  } catch {
    // Ignore storage access failures.
  }
}

async function fetchJson(url, { forceRefresh = false } = {}) {
  const headers = { Accept: "application/json" };
  // Catalog search must reflect the current curated-place dataset. In
  // particular, do not let a previously cached empty result mask a location
  // that was subsequently restored or imported.
  if (forceRefresh) {
    headers["X-BHF-Refresh"] = "true";
  }
  let resolvedUrl = url;
  if (window.BHFApi?.resolveUrl) {
    resolvedUrl = window.BHFApi.resolveUrl(url);
  } else if (String(window.BHFRuntimeConfig?.backendMode || "same-origin") === "remote") {
    throw new Error("BHF backend is not configured for this deployment.");
  }
  const response = await fetch(resolvedUrl, {
    headers,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  const rawContentLength = response.headers.get("Content-Length");
  const responseBytes = rawContentLength !== null && /^\d+$/.test(rawContentLength)
    ? Number(rawContentLength)
    : null;
  return {
    data,
    responseBytes,
    offline: response.headers.get("X-BHF-Offline") === "true",
  };
}

async function loadCachedJson(
  url,
  fallbackErrorMessage,
  { allowOfflineFallback = true, forceRefresh = false } = {}
) {
  if (inFlightRequests.has(url)) {
    return inFlightRequests.get(url);
  }
  const request = (async () => {
    try {
      const {data, responseBytes, offline} = await fetchJson(url, { forceRefresh });
      if (!offline) {
        writeCachedValue(url, data, responseBytes);
        return data;
      }
      return {
        ...data,
        offline: true,
        cache_status: data?.cache_status || "service_worker",
      };
    } catch (error) {
      if (!allowOfflineFallback) {
        throw new Error(error?.message || fallbackErrorMessage);
      }
      const cached = readCachedValue(url);
      if (cached) {
        return {
          ...cached,
          offline: true,
          cache_status: "stale",
        };
      }
      throw new Error(error?.message || fallbackErrorMessage);
    }
  })();
  inFlightRequests.set(url, request);
  try {
    return await request;
  } finally {
    inFlightRequests.delete(url);
  }
}

export async function loadPlacesForPassage(context = {}) {
  const params = new URLSearchParams();
  if (context.book) {
    params.set("book", context.book);
  }
  if (context.chapter) {
    params.set("chapter", String(context.chapter));
  }
  if (context.verseStart || context.startVerse) {
    params.set("verse_start", String(context.verseStart || context.startVerse));
  }
  if (context.verseEnd || context.endVerse) {
    params.set("verse_end", String(context.verseEnd || context.endVerse));
  }
  if (context.period && String(context.period).trim().toLowerCase() !== "all") {
    params.set("period", String(context.period));
  }
  if (typeof context.includeRelatedPassages === "boolean") {
    params.set("include_related_passages", String(context.includeRelatedPassages));
  }

  const url = params.toString()
    ? `/api/maps/places-for-passage?${params.toString()}`
    : "/api/maps/places-for-passage";
  return loadCachedJson(url, "Could not load passage map markers.");
}

export async function loadRelatedPassagesForPlace(placeId, context = {}) {
  const params = new URLSearchParams();
  params.set("place_id", placeId);
  if (context.period && String(context.period).trim().toLowerCase() !== "all") {
    params.set("period", String(context.period));
  }

  const url = params.toString()
    ? `/api/maps/related-passages-for-place?${params.toString()}`
    : "/api/maps/related-passages-for-place";
  return loadCachedJson(url, "Could not load related passages.");
}

export async function loadRoutesForPassage(context = {}) {
  const params = new URLSearchParams();
  if (context.book) {
    params.set("book", context.book);
  }
  if (context.chapter) {
    params.set("chapter", String(context.chapter));
  }
  if (context.verseStart || context.startVerse) {
    params.set("verse_start", String(context.verseStart || context.startVerse));
  }
  if (context.verseEnd || context.endVerse) {
    params.set("verse_end", String(context.verseEnd || context.endVerse));
  }
  if (context.period && String(context.period).trim().toLowerCase() !== "all") {
    params.set("period", String(context.period));
  }

  const url = params.toString()
    ? `/api/maps/routes-for-passage?${params.toString()}`
    : "/api/maps/routes";
  return loadCachedJson(url, "Could not load passage routes.");
}

export async function loadHistoricalLayers(context = {}) {
  const params = new URLSearchParams();
  if (context.period && String(context.period).trim() && String(context.period).trim().toLowerCase() !== "all") {
    params.set("period", String(context.period));
  }

  const url = params.toString()
    ? `/api/maps/historical-layers?${params.toString()}`
    : "/api/maps/historical-layers";
  return loadCachedJson(url, "Could not load historical layers.");
}

export async function loadPoliticalContextForPassage(context = {}) {
  const params = new URLSearchParams();
  if (context.book) {
    params.set("book", context.book);
  }
  if (context.chapter) {
    params.set("chapter", String(context.chapter));
  }
  if (context.verseStart || context.startVerse) {
    params.set("verse_start", String(context.verseStart || context.startVerse));
  }
  if (context.verseEnd || context.endVerse) {
    params.set("verse_end", String(context.verseEnd || context.endVerse));
  }
  if (context.period && String(context.period).trim().toLowerCase() !== "all") {
    params.set("period", String(context.period));
  }

  const url = params.toString()
    ? `/api/maps/political-context-for-passage?${params.toString()}`
    : "/api/maps/political-context";
  return loadCachedJson(url, "Could not load political context layers.");
}

export async function loadArchaeologyForPassage(context = {}) {
  const params = new URLSearchParams();
  if (context.book) {
    params.set("book", context.book);
  }
  if (context.chapter) {
    params.set("chapter", String(context.chapter));
  }
  if (context.verseStart || context.startVerse) {
    params.set("verse_start", String(context.verseStart || context.startVerse));
  }
  if (context.verseEnd || context.endVerse) {
    params.set("verse_end", String(context.verseEnd || context.endVerse));
  }
  if (context.period && String(context.period).trim().toLowerCase() !== "all") {
    params.set("period", String(context.period));
  }

  const url = params.toString()
    ? `/api/maps/archaeology-for-passage?${params.toString()}`
    : "/api/maps/archaeology";
  return loadCachedJson(url, "Could not load archaeology markers.");
}

export async function loadManuscriptsForPassage(context = {}) {
  const params = new URLSearchParams();
  if (context.book) {
    params.set("book", context.book);
  }
  if (context.chapter) {
    params.set("chapter", String(context.chapter));
  }
  if (context.verseStart || context.startVerse) {
    params.set("verse_start", String(context.verseStart || context.startVerse));
  }
  if (context.verseEnd || context.endVerse) {
    params.set("verse_end", String(context.verseEnd || context.endVerse));
  }
  if (context.period && String(context.period).trim().toLowerCase() !== "all") {
    params.set("period", String(context.period));
  }

  const url = params.toString()
    ? `/api/maps/manuscripts-for-passage?${params.toString()}`
    : "/api/maps/manuscripts";
  return loadCachedJson(url, "Could not load manuscript markers.");
}

export async function loadMapCatalog(context = {}) {
  const params = new URLSearchParams();
  if (context.period && String(context.period).trim().toLowerCase() !== "all") {
    params.set("period", String(context.period));
  }
  if (context.includeRecords === false) {
    params.set("include_records", "false");
  }
  const url = params.toString() ? `/api/maps/catalog?${params.toString()}` : "/api/maps/catalog";
  return loadCachedJson(url, "Could not load map catalog.");
}

export async function searchMapCatalog(query, context = {}) {
  const params = new URLSearchParams();
  params.set("q", String(query || ""));
  if (context.kind && String(context.kind).trim()) {
    params.set("kind", String(context.kind));
  }
  if (context.period && String(context.period).trim().toLowerCase() !== "all") {
    params.set("period", String(context.period));
  }
  if (context.limit) {
    params.set("limit", String(context.limit));
  }
  const url = `/api/maps/search?${params.toString()}`;
  return loadCachedJson(url, "Could not search the map catalog.", {
    allowOfflineFallback: false,
    forceRefresh: true,
  });
}
