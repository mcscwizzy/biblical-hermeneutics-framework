/* One debounced caller-facing API for compact Study Companion availability. */
(function () {
  "use strict";

  const memoryCache = new Map();
  const MAX_CACHE_ENTRIES = 40;
  const DEFAULT_TTL_MS = 5 * 60 * 1000;
  const RESOURCE_CHANGE_EVENTS = [
    "bhf:study-resources-changed",
    "bhf:translation-installed",
    "bhf:translation-removed",
    "bhf:canonical-changed",
    "bhf:archaeology-changed",
    "bhf:commentary-changed",
    "bhf:offline-pack-changed",
  ];

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
    const cached = memoryCache.get(key);
    const ttl = Number.isFinite(Number(options.ttl))
      ? Math.max(0, Number(options.ttl))
      : DEFAULT_TTL_MS;
    if (!options.refresh && cached && Date.now() - cached.cachedAt < ttl) {
      return cached.value;
    }
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
    const normalized = normalize(data);
    remember(key, normalized);
    return normalized;
  }

  async function enhance(selection, context, options = {}) {
    const evidenceHash = String(
      context?.presentation_enhancement?.evidence_hash
      || context?.evidence_bundle?.evidence_hash
      || "",
    ).trim();
    if (!selection?.book || !selection?.chapter || !evidenceHash) {
      throw new Error("Passage evidence is required for presentation enhancement.");
    }
    const transport = presentationTransport();
    if (transport === "unavailable") return null;
    const providerOptions = options.presentationOptions
      || (window.BHFModelSettings?.getPresentationRequestOptions
        ? await window.BHFModelSettings.getPresentationRequestOptions(
          context?.presentation_enhancement?.server_configured === true,
        )
        : {enabled: false, reason: "provider_unavailable", headers: {}, profile: null});
    if (providerOptions.enabled !== true) return null;
    const requestOptions = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(providerOptions.headers || {}),
      },
      signal: options.signal,
      body: JSON.stringify({
        book: selection.book,
        chapter: selection.chapter,
        verse_start: selection.startVerse || null,
        verse_end: selection.endVerse || null,
        evidence_hash: evidenceHash,
        ai_profile: providerOptions.profile || null,
      }),
    };
    document.dispatchEvent(new CustomEvent("bhf:companion-presentation-request", {
      detail: {key: requestKey(selection), evidenceHash},
    }));
    const submission = window.BHFApi?.requestJson
      ? await window.BHFApi.requestJson(
        "/api/study/presentation",
        requestOptions,
        "Presentation enhancement is unavailable.",
      )
      : await requestWithFetch("/api/study/presentation", requestOptions);
    if (options.signal?.aborted) throw new DOMException("Aborted", "AbortError");
    if (transport === "synchronous") {
      return submission && typeof submission === "object" ? submission : {};
    }
    if (String(submission?.status || "") === "succeeded") {
      return submission?.result || {};
    }
    const jobId = String(submission?.job_id || "").trim();
    if (!jobId) throw new Error("Presentation job submission did not return a job ID.");
    const pollUrl = `/api/study/presentation/jobs/${encodeURIComponent(jobId)}`;
    if (typeof window.BHFJobFlow?.pollJsonJob !== "function") {
      throw new Error("Presentation job polling is unavailable.");
    }
    return window.BHFJobFlow.pollJsonJob({
      signal: options.signal,
      poll: () => {
        const pollOptions = {
          headers: {Accept: "application/json"},
          signal: options.signal,
        };
        return window.BHFApi?.requestJson
          ? window.BHFApi.requestJson(
            pollUrl,
            pollOptions,
            "Presentation job status is unavailable.",
          )
          : requestWithFetch(pollUrl, pollOptions);
      },
    });
  }

  async function getEnhancementAvailability(context) {
    const enhancement = context?.presentation_enhancement;
    if (enhancement?.supported !== true && enhancement?.available !== true) {
      return {available: false, reason: "unsupported", requestOptions: null};
    }
    if (presentationTransport() === "unavailable") {
      return {available: false, reason: "presentation_unavailable", requestOptions: null};
    }
    if (!window.BHFModelSettings?.getPresentationRequestOptions) {
      return {available: false, reason: "provider_unavailable", requestOptions: null};
    }
    const options = await window.BHFModelSettings.getPresentationRequestOptions(
      enhancement?.server_configured === true,
    );
    return {
      available: options.enabled === true,
      reason: options.enabled === true ? "" : String(options.reason || "unavailable"),
      requestOptions: options,
    };
  }

  async function canEnhance(context) {
    return (await getEnhancementAvailability(context)).available;
  }

  function presentationTransport() {
    const configured = String(
      window.BHFRuntimeConfig?.presentationTransport || "",
    ).trim().toLowerCase();
    if (["job", "synchronous", "unavailable"].includes(configured)) {
      return configured;
    }
    return window.BHFRuntimeConfig?.presentationJobs === false
      ? "unavailable"
      : "job";
  }

  async function requestWithFetch(url, options) {
    let resolvedUrl = url;
    if (window.BHFBackendRouting?.resolveUrl) {
      resolvedUrl = window.BHFBackendRouting.resolveUrl(
        url,
        window.BHFRuntimeConfig || {},
      );
    } else if (String(window.BHFRuntimeConfig?.backendMode || "same-origin") === "remote") {
      throw new Error("BHF backend is not configured for this deployment.");
    }
    const response = await fetch(resolvedUrl, options);
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
        groups: array(source.entities?.groups),
        events: array(source.entities?.events),
      },
      summaries: source.summaries && typeof source.summaries === "object" ? source.summaries : {},
    };
  }

  function array(value) {
    return Array.isArray(value) ? value : [];
  }

  function remember(key, value) {
    if (!memoryCache.has(key) && memoryCache.size >= MAX_CACHE_ENTRIES) {
      memoryCache.delete(memoryCache.keys().next().value);
    }
    memoryCache.set(key, {value, cachedAt: Date.now()});
  }

  function invalidate(target, options = {}) {
    let removed = 0;
    if (!target) {
      removed = memoryCache.size;
      memoryCache.clear();
    } else {
      const key = typeof target === "string" ? target : requestKey(target);
      removed = memoryCache.delete(key) ? 1 : 0;
    }
    if (options.announce !== false) {
      document.dispatchEvent(new CustomEvent("bhf:companion-context-invalidated", {
        detail: {key: target ? (typeof target === "string" ? target : requestKey(target)) : null, removed},
      }));
    }
    return removed;
  }

  RESOURCE_CHANGE_EVENTS.forEach((eventName) => {
    document.addEventListener(eventName, () => invalidate());
  });

  window.BHFCompanionContext = Object.freeze({
    canEnhance,
    enhance,
    getEnhancementAvailability,
    load,
    urlFor,
    requestKey,
    invalidate,
    clear: () => invalidate(null, {announce: false}),
  });
})();
