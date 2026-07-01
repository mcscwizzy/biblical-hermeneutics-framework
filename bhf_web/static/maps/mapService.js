const CACHE_PREFIX = "bhf.map-service:";
const memoryCache = new Map();
const inFlightRequests = new Map();

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

function writeCachedValue(url, value) {
  memoryCache.set(url, value);
  if (typeof localStorage === "undefined") {
    return;
  }
  try {
    localStorage.setItem(
      cacheKeyFor(url),
      JSON.stringify({
        cachedAt: new Date().toISOString(),
        value,
      })
    );
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

async function fetchJson(url) {
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

async function loadCachedJson(url, fallbackErrorMessage, { allowOfflineFallback = true } = {}) {
  if (inFlightRequests.has(url)) {
    return inFlightRequests.get(url);
  }
  const request = (async () => {
    try {
      const data = await fetchJson(url);
      writeCachedValue(url, data);
      return data;
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
  if (context.selectedText || context.passageText || context.text) {
    params.set("passage_text", context.selectedText || context.passageText || context.text);
  }
  if (context.period && String(context.period).trim().toLowerCase() !== "all") {
    params.set("period", String(context.period));
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
  if (context.selectedText || context.passageText || context.text) {
    params.set("passage_text", context.selectedText || context.passageText || context.text);
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
  if (context.selectedText || context.passageText || context.text) {
    params.set("passage_text", context.selectedText || context.passageText || context.text);
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
  if (context.selectedText || context.passageText || context.text) {
    params.set("passage_text", context.selectedText || context.passageText || context.text);
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
  if (context.selectedText || context.passageText || context.text) {
    params.set("passage_text", context.selectedText || context.passageText || context.text);
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
  return loadCachedJson(url, "Could not search the map catalog.", { allowOfflineFallback: false });
}

export async function loadSavedMapStudies(context = {}) {
  const params = new URLSearchParams();
  if (context.book) {
    params.set("book", context.book);
  }
  if (context.chapter) {
    params.set("chapter", String(context.chapter));
  }
  const url = params.toString() ? `/api/map-studies?${params.toString()}` : "/api/map-studies";
  return loadCachedJson(url, "Could not load saved map studies.");
}

export async function loadSavedMapStudy(studyId) {
  const url = `/api/map-studies/${encodeURIComponent(studyId)}`;
  return loadCachedJson(url, "Could not load saved map study.");
}
