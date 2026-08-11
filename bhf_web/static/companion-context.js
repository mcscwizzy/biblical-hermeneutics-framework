/* One debounced caller-facing API for compact Study Companion availability. */
(function () {
  "use strict";

  const memoryCache = new Map();
  const MAX_CACHE_ENTRIES = 40;

  function requestKey(selection) {
    return [
      String(selection?.book || "").trim(),
      Number(selection?.chapter || 0),
      Number(selection?.startVerse || 0),
      Number(selection?.endVerse || 0),
      String(selection?.translation || "").trim().toLowerCase(),
    ].join("|");
  }

  function urlFor(selection) {
    const parameters = new URLSearchParams({
      book: String(selection.book),
      chapter: String(selection.chapter),
    });
    if (selection.startVerse) parameters.set("verse_start", String(selection.startVerse));
    if (selection.endVerse) parameters.set("verse_end", String(selection.endVerse));
    if (selection.translation) parameters.set("translation", String(selection.translation));
    return `/api/study/companion-context?${parameters.toString()}`;
  }

  async function load(selection, options = {}) {
    if (!selection?.book || !selection?.chapter) {
      throw new Error("A book and chapter are required for Study Companion context.");
    }
    const key = requestKey(selection);
    if (!options.refresh && memoryCache.has(key)) return memoryCache.get(key);
    const url = urlFor(selection);
    document.dispatchEvent(new CustomEvent("bhf:companion-context-request", {
      detail: {url, key},
    }));
    const requestOptions = {
      headers: {Accept: "application/json"},
      signal: options.signal,
    };
    const data = window.BHFApi?.requestJson
      ? await window.BHFApi.requestJson(url, requestOptions, "Study Companion context is unavailable.")
      : await requestWithFetch(url, requestOptions);
    if (options.signal?.aborted) throw new DOMException("Aborted", "AbortError");
    remember(key, normalize(data));
    return memoryCache.get(key);
  }

  async function requestWithFetch(url, options) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
  }

  function normalize(data) {
    const source = data && typeof data === "object" ? data : {};
    const resources = {};
    Object.entries(source.resources || {}).forEach(([id, value]) => {
      const entry = value && typeof value === "object" ? value : {};
      const state = ["available", "unavailable", "unknown"].includes(entry.state)
        ? entry.state
        : entry.available === true
          ? "available"
          : entry.available === false
            ? "unavailable"
            : "unknown";
      resources[id] = {
        ...entry,
        state,
        available: state === "available" && entry.available !== false,
        count: Math.max(0, Number(entry.count || 0)),
      };
    });
    return {
      ...source,
      offline: source.offline === true || navigator.onLine === false,
      resources,
      entities: {
        people: array(source.entities?.people),
        places: array(source.entities?.places),
        themes: array(source.entities?.themes),
      },
      summaries: source.summaries && typeof source.summaries === "object" ? source.summaries : {},
    };
  }

  function array(value) {
    return Array.isArray(value) ? value : [];
  }

  function remember(key, value) {
    if (memoryCache.size >= MAX_CACHE_ENTRIES) {
      memoryCache.delete(memoryCache.keys().next().value);
    }
    memoryCache.set(key, value);
  }

  window.BHFCompanionContext = Object.freeze({
    load,
    urlFor,
    requestKey,
    clear: () => memoryCache.clear(),
  });
})();
