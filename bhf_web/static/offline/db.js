(function () {
  const DB_NAME = "bhf-offline";
  const DB_VERSION = 6;
  const STORES = [
    "apiResponses",
    "translations",
    "canonicalObjects",
    "sources",
    "chapters",
    "searches",
    "notes",
    "highlights",
    "savedStudies",
    "mapStudies",
    "mutationQueue",
    "metadata",
    "modelSettings",
  ];
  const SNAPSHOT_STORES = ["notes", "highlights", "savedStudies", "mutationQueue", "metadata"];
  const REBUILDABLE_STORES = ["apiResponses", "translations", "canonicalObjects", "sources", "chapters", "searches"];
  const REQUIRED_OFFLINE_PACKS = ["study", "maps"];

  let dbPromise = null;

  function openDatabase() {
    if (dbPromise) {
      return dbPromise;
    }
    if (!("indexedDB" in window)) {
      dbPromise = Promise.reject(new Error("IndexedDB is not available."));
      return dbPromise;
    }
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        for (const storeName of STORES) {
          if (!db.objectStoreNames.contains(storeName)) {
            db.createObjectStore(storeName, { keyPath: "id" });
          }
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Could not open offline database."));
    });
    return dbPromise;
  }

  async function withStore(storeName, mode, callback) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(storeName, mode);
      const store = transaction.objectStore(storeName);
      let callbackResult;
      transaction.oncomplete = () => resolve(callbackResult);
      transaction.onerror = () => reject(transaction.error || new Error("Offline database transaction failed."));
      transaction.onabort = () => reject(transaction.error || new Error("Offline database transaction aborted."));
      callbackResult = callback(store);
    });
  }

  function requestToPromise(request) {
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Offline database request failed."));
    });
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function clientId(prefix) {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return `${prefix}-${window.crypto.randomUUID()}`;
    }
    return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  async function get(storeName, id) {
    return withStore(storeName, "readonly", (store) => requestToPromise(store.get(id)));
  }

  async function put(storeName, value) {
    return withStore(storeName, "readwrite", (store) => requestToPromise(store.put(value)));
  }

  async function remove(storeName, id) {
    return withStore(storeName, "readwrite", (store) => requestToPromise(store.delete(id)));
  }

  async function list(storeName) {
    return withStore(storeName, "readonly", (store) => requestToPromise(store.getAll()));
  }

  async function clearStore(storeName) {
    return withStore(storeName, "readwrite", (store) => requestToPromise(store.clear()));
  }

  async function cacheApiResponse(url, payload) {
    const id = normalizeUrlKey(url);
    await put("apiResponses", {
      id,
      url: id,
      cachedAt: nowIso(),
      payload,
    });
    if (isChapterUrl(id)) {
      await put("chapters", {
        id,
        url: id,
        cachedAt: nowIso(),
        payload,
      });
    }
    if (id.startsWith("/api/bible/search?")) {
      await put("searches", {
        id,
        url: id,
        cachedAt: nowIso(),
        payload,
      });
    }
    const translationMatch = id.match(/^\/api\/translations\/([^/?]+)\/offline-data$/);
    if (translationMatch && payload?.dataset) {
      await put("translations", {
        id: translationMatch[1].toLowerCase(),
        cachedAt: nowIso(),
        payload,
      });
    }
    if (id.startsWith("/api/offline/packs/study") && Array.isArray(payload?.objects)) {
      await Promise.all(payload.objects.map((object) => put("canonicalObjects", normalizeCanonicalObject(object))));
    }
    if (id.startsWith("/api/offline/packs/sources") && Array.isArray(payload?.details)) {
      await Promise.all(payload.details.map((source) => put("sources", normalizeSource(source))));
    }
    if (id.startsWith("/api/offline/packs/") && payload?.pack_id) {
      await put("metadata", {
        id: `pack:${payload.pack_id}`,
        cachedAt: nowIso(),
        payload: {
          pack_id: payload.pack_id,
          label: payload.label,
          strategy: payload.strategy,
          version_fingerprint: payload.version_fingerprint || "",
          object_count: Array.isArray(payload.objects) ? payload.objects.length : undefined,
          response_count: Array.isArray(payload.responses) ? payload.responses.length : undefined,
        },
      });
    }
    if (id.startsWith("/api/notes/") && Array.isArray(payload?.notes)) {
      await Promise.all(payload.notes.map((note) => put("notes", normalizeNote(note))));
    }
    if (id.startsWith("/api/highlights/") && Array.isArray(payload?.highlights)) {
      await Promise.all(payload.highlights.map((highlight) => put("highlights", normalizeHighlight(highlight))));
    }
    if (id === "/api/sources" && Array.isArray(payload?.sources)) {
      await Promise.all(payload.sources.map((source) => put("sources", normalizeSource(source))));
    }
    const sourceMatch = id.match(/^\/api\/sources\/([^/?]+)$/);
    if (sourceMatch && payload?.id) {
      await put("sources", normalizeSource(payload));
    }
    if (id.startsWith("/api/saved-studies") && Array.isArray(payload?.saved_studies)) {
      await Promise.all(payload.saved_studies.map((study) => put("savedStudies", normalizeSavedStudy(study))));
    }
    return payload;
  }

  async function readTextResponse(url) {
    const key = normalizeUrlKey(url);
    const savedStudyMatch = key.match(/^\/api\/saved-studies\/([^/?]+)$/);
    if (!savedStudyMatch) {
      return null;
    }
    const study = await get("savedStudies", decodeURIComponent(savedStudyMatch[1]));
    if (!study) {
      return null;
    }
    return renderSavedStudyHtml(study);
  }

  async function readApiResponse(url) {
    const generated = await generatedOfflineResponse(url);
    if (generated) {
      return generated;
    }
    const entry = await get("apiResponses", normalizeUrlKey(url));
    if (!entry) {
      return null;
    }
    return {
      ...entry.payload,
      offline: true,
      cache_status: "stale",
      cached_at: entry.cachedAt,
    };
  }

  async function generatedOfflineResponse(url) {
    const key = normalizeUrlKey(url);
    if (key.startsWith("/api/bible/search?")) {
      return generatedSearchResponse(key);
    }
    if (key.startsWith("/api/canonical/search")) {
      return generatedCanonicalSearchResponse(key);
    }
    const canonicalObjectMatch = key.match(/^\/api\/canonical\/objects\/([^/?]+)$/);
    if (canonicalObjectMatch) {
      const object = await get("canonicalObjects", normalizeCanonicalId(decodeURIComponent(canonicalObjectMatch[1])));
      if (object) {
        return { ...object, offline: true, cache_status: "generated" };
      }
      return null;
    }
    if (key === "/api/sources") {
      const storedSources = await list("sources");
      if (!storedSources.length) {
        return null;
      }
      const sources = storedSources
        .map((source) => sourceSummary(source))
        .sort((left, right) => String(left.label || "").localeCompare(String(right.label || "")));
      return { sources, offline: true, cache_status: "generated" };
    }
    const sourceMatch = key.match(/^\/api\/sources\/([^/?]+)$/);
    if (sourceMatch) {
      const source = await get("sources", decodeURIComponent(sourceMatch[1]));
      return source ? { ...source, offline: true, cache_status: "generated" } : null;
    }
    const notesMatch = key.match(/^\/api\/notes\/([^/?]+)\/(\d+)$/);
    if (notesMatch) {
      const notes = await notesForChapter(decodeURIComponent(notesMatch[1]), Number(notesMatch[2]));
      return { notes, offline: true, cache_status: "generated", device_only: true };
    }
    const highlightsMatch = key.match(/^\/api\/highlights\/([^/?]+)\/(\d+)$/);
    if (highlightsMatch) {
      const highlights = await highlightsForChapter(
        decodeURIComponent(highlightsMatch[1]),
        Number(highlightsMatch[2]),
      );
      return { highlights, offline: true, cache_status: "generated", device_only: true };
    }
    if (key.startsWith("/api/saved-studies") && !key.match(/^\/api\/saved-studies\/[^/?]+$/)) {
      const params = new URLSearchParams(key.split("?", 2)[1] || "");
      const studies = await savedStudiesForChapter(params.get("book"), params.get("chapter"));
      return { saved_studies: studies, offline: true, cache_status: "generated", device_only: true };
    }
    const chapterMatch = key.match(/^\/api\/bible\/([^/?]+)\/(\d+)(?:\?(.+))?$/);
    if (!chapterMatch) {
      return null;
    }
    const params = new URLSearchParams(chapterMatch[3] || "");
    const translationId = String(params.get("translation") || "asv").toLowerCase();
    const dataset = await get("translations", translationId);
    if (!dataset?.payload?.dataset) {
      return null;
    }
    const chapter = chapterFromDataset(
      dataset.payload.dataset,
      decodeURIComponent(chapterMatch[1]),
      Number(chapterMatch[2])
    );
    if (!chapter) {
      return null;
    }
    return { ...chapter, offline: true, cache_status: "generated" };
  }

  async function generatedSearchResponse(key) {
    const params = new URLSearchParams(key.split("?", 2)[1] || "");
    const query = String(params.get("q") || "").trim();
    if (!query) {
      return null;
    }
    const translationId = String(params.get("translation") || "asv").toLowerCase();
    const limit = Math.max(1, Math.min(Number(params.get("limit") || 25), 100));
    const dataset = await get("translations", translationId);
    if (!dataset?.payload?.dataset) {
      return null;
    }
    const normalizedQuery = normalizeSearchText(query);
    const tokens = normalizedQuery.split(/\s+/).filter(Boolean);
    const results = [];
    for (const book of dataset.payload.dataset.books || []) {
      for (const chapter of book.chapters || []) {
        const chapterNumber = Number(chapter.chapter || chapter.number);
        for (const verse of chapter.verses || []) {
          const verseNumber = Number(verse.verse || verse.number);
          const text = String(verse.text || "");
          const normalizedText = normalizeSearchText(text);
          const phraseHit = normalizedText.includes(normalizedQuery);
          const overlap = tokens.filter((token) => normalizedText.includes(token)).length;
          if (!phraseHit && overlap === 0) {
            continue;
          }
          results.push({
            book: book.name,
            chapter: chapterNumber,
            verse_start: verseNumber,
            verse_end: verseNumber,
            reference: `${book.name} ${chapterNumber}:${verseNumber}`,
            excerpt: text,
            match_type: phraseHit ? "phrase" : "term",
            score: (phraseHit ? 500 : 0) + overlap * 20,
          });
        }
      }
    }
    results.sort((left, right) => Number(right.score || 0) - Number(left.score || 0));
    const translationLabel = String(dataset.payload.dataset.translation?.id || translationId).toUpperCase();
    return {
      query,
      normalized_query: normalizedQuery,
      results: results.slice(0, limit),
      total_results: results.length,
      direct_reference: false,
      ai_fallback_eligible: false,
      no_results_message: results.length === 0 ? `No local ${translationLabel} matches were found.` : null,
      translation: translationLabel,
      offline: true,
      cache_status: "generated",
    };
  }

  function chapterFromDataset(dataset, requestedBook, requestedChapter) {
    const normalizedBook = normalizeBookName(requestedBook);
    const chapterNumber = Number(requestedChapter);
    const book = (dataset.books || []).find((item) => normalizeBookName(item.name) === normalizedBook);
    if (!book) {
      return null;
    }
    const chapter = (book.chapters || []).find((item) => Number(item.chapter || item.number) === chapterNumber);
    if (!chapter) {
      return null;
    }
    return {
      translation: dataset.translation || {},
      book: book.name,
      chapter: chapterNumber,
      verses: chapter.verses || [],
    };
  }

  function normalizeBookName(value) {
    return String(value || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "");
  }

  function normalizeSearchText(value) {
    return String(value || "").toLowerCase().replace(/[^a-z0-9\s]+/g, " ").replace(/\s+/g, " ").trim();
  }

  async function generatedCanonicalSearchResponse(key) {
    const params = new URLSearchParams(key.split("?", 2)[1] || "");
    const query = String(params.get("q") || "").trim();
    const limit = Math.max(1, Math.min(Number(params.get("limit") || 12), 25));
    const objectType = String(params.get("type") || "all").trim();
    const reviewStatus = String(params.get("review_status") || "all").trim();
    const contentStatus = String(params.get("content_status") || "all").trim();
    const includePlaceholders = params.get("include_placeholders") !== "false";
    const objects = (await list("canonicalObjects")).filter((object) => {
      if (objectType !== "all" && String(object.type || "") !== objectType) {
        return false;
      }
      if (reviewStatus !== "all" && String(object.review_status || "") !== reviewStatus) {
        return false;
      }
      if (contentStatus !== "all" && String(object.content_status || "") !== contentStatus) {
        return false;
      }
      if (!includePlaceholders && String(object.content_status || "") === "placeholder") {
        return false;
      }
      return true;
    });
    if (!objects.length) {
      return null;
    }
    const results = query
      ? scoreCanonicalObjects(objects, query)
      : objects
          .map((object) => ({
            ...object,
            reason: `Browse result ranked by importance ${object.importance || 0}.`,
            match_type: "browse",
            score: Number(object.importance || 0) / 100,
          }))
          .sort(compareCanonicalResults);
    return {
      query,
      limit,
      filters: {
        type: objectType,
        review_status: reviewStatus,
        content_status: contentStatus,
        include_placeholders: includePlaceholders,
      },
      metadata: {
        retrieval_method: "offline_pack",
        topic_count: Math.min(results.length, limit),
        query,
        max_results: limit,
        include_placeholders: includePlaceholders,
      },
      results: results.slice(0, limit),
      offline: true,
      cache_status: "generated",
    };
  }

  function scoreCanonicalObjects(objects, query) {
    const normalizedQuery = normalizeSearchText(query);
    const terms = normalizedQuery.split(/\s+/).filter(Boolean);
    return objects
      .map((object) => {
        const haystack = canonicalSearchText(object);
        const idMatch = normalizeCanonicalId(object.id) === normalizeCanonicalId(query);
        const titleMatch = normalizeSearchText(object.title) === normalizedQuery;
        const phraseHit = normalizedQuery && haystack.includes(normalizedQuery);
        const matchedTerms = terms.filter((term) => haystack.includes(term));
        let score = 0;
        let matchType = "keyword";
        if (idMatch) {
          score += 1000;
          matchType = "id";
        }
        if (titleMatch) {
          score += 800;
          matchType = "title";
        } else if (phraseHit) {
          score += 500;
          matchType = "phrase";
        }
        score += matchedTerms.length * 50;
        score += Number(object.importance || 0) / 100;
        return {
          ...object,
          reason: matchedTerms.length
            ? `Matched search fields: ${matchedTerms.join(", ")}.`
            : "Matched search fields: none.",
          match_type: matchType,
          matched_terms: matchedTerms,
          matched_fields: ["id", "title", "aliases", "summary", "scripture_references"],
          matched_alias: null,
          score,
        };
      })
      .filter((object) => Number(object.score || 0) > 0)
      .sort(compareCanonicalResults);
  }

  function canonicalSearchText(object) {
    const scripture = (object.scripture_references || []).map((reference) => reference.reference || "").join(" ");
    return normalizeSearchText([
      object.id,
      object.title,
      object.type,
      object.summary,
      ...(object.aliases || []),
      scripture,
    ].join(" "));
  }

  function compareCanonicalResults(left, right) {
    return Number(right.score || right.importance || 0) - Number(left.score || left.importance || 0)
      || String(left.type || "").localeCompare(String(right.type || ""))
      || String(left.title || "").localeCompare(String(right.title || ""));
  }

  function normalizeCanonicalObject(object) {
    const normalized = {
      ...object,
      id: normalizeCanonicalId(object.id),
      aliases: Array.isArray(object.aliases) ? object.aliases : [],
      related_objects: Array.isArray(object.related_objects) ? object.related_objects : [],
      scripture_references: Array.isArray(object.scripture_references) ? object.scripture_references : [],
      sources: Array.isArray(object.sources) ? object.sources : [],
    };
    normalized.source_count = normalized.sources.length;
    normalized.scripture_reference_count = normalized.scripture_references.length;
    normalized.related_object_count = normalized.related_objects.length;
    return normalized;
  }

  function normalizeCanonicalId(value) {
    return String(value || "").trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
  }

  async function enqueueMutation(mutation) {
    const queued = {
      id: clientId("mutation"),
      createdAt: nowIso(),
      attempts: 0,
      ...mutation,
    };
    await put("mutationQueue", queued);
    return queued;
  }

  async function queuedMutations() {
    const mutations = await list("mutationQueue");
    return mutations.sort((left, right) => String(left.createdAt).localeCompare(String(right.createdAt)));
  }

  async function mutationQueueSummary() {
    const mutations = await queuedMutations();
    const failed = mutations.filter((mutation) => mutation.lastError);
    const lastFailed = failed
      .slice()
      .sort((left, right) => String(right.lastAttemptAt || "").localeCompare(String(left.lastAttemptAt || "")))[0] || null;
    return {
      queued_count: mutations.length,
      failed_count: failed.length,
      last_error: lastFailed?.lastError || "",
      last_attempt_at: lastFailed?.lastAttemptAt || "",
    };
  }

  async function markMutationAttempt(id, { error = "", failed = false } = {}) {
    const existing = await get("mutationQueue", id);
    if (!existing) {
      return null;
    }
    const updated = {
      ...existing,
      attempts: Number(existing.attempts || 0) + 1,
      lastAttemptAt: nowIso(),
      lastError: failed ? String(error || "Sync failed.") : "",
    };
    await put("mutationQueue", updated);
    return updated;
  }

  async function removeMutation(id) {
    return remove("mutationQueue", id);
  }

  async function exportSnapshot() {
    const stores = {};
    for (const storeName of SNAPSHOT_STORES) {
      stores[storeName] = await list(storeName);
    }
    return {
      app: "bhf-bible-reader",
      schema_version: 1,
      db_name: DB_NAME,
      db_version: DB_VERSION,
      exported_at: nowIso(),
      stores,
    };
  }

  async function importSnapshot(snapshot) {
    if (!snapshot || snapshot.app !== "bhf-bible-reader" || !snapshot.stores || typeof snapshot.stores !== "object") {
      throw new Error("This is not a BHF offline snapshot.");
    }
    const counts = {};
    let imported = 0;
    for (const storeName of SNAPSHOT_STORES) {
      const records = (Array.isArray(snapshot.stores[storeName]) ? snapshot.stores[storeName] : [])
        .filter((record) => storeName !== "mutationQueue" || !isDeviceOnlyMutationUrl(record?.url));
      counts[storeName] = 0;
      for (const record of records) {
        if (!record || typeof record !== "object" || !record.id) {
          continue;
        }
        await put(storeName, record);
        counts[storeName] += 1;
        imported += 1;
      }
    }
    return {
      imported_count: imported,
      stores: counts,
    };
  }

  async function readinessReport() {
    const metadata = await list("metadata");
    const installedPacks = metadata
      .filter((entry) => String(entry.id || "").startsWith("pack:"))
      .map((entry) => ({
        id: String(entry.id || "").replace(/^pack:/, ""),
        label: entry.payload?.label || String(entry.id || "").replace(/^pack:/, ""),
        cachedAt: entry.cachedAt || "",
        object_count: entry.payload?.object_count,
        response_count: entry.payload?.response_count,
      }))
      .sort((left, right) => String(left.id).localeCompare(String(right.id)));
    const installedPackIds = new Set(installedPacks.map((pack) => pack.id));
    const translations = await list("translations");
    const queue = await mutationQueueSummary();
    const counts = {
      notes: (await list("notes")).length,
      highlights: (await list("highlights")).length,
      savedStudies: (await list("savedStudies")).length,
      canonicalObjects: (await list("canonicalObjects")).length,
      sources: (await list("sources")).length,
    };
    return {
      generated_at: nowIso(),
      translations_count: translations.length,
      translation_ids: translations.map((translation) => translation.id).sort(),
      installed_packs: installedPacks,
      required_packs: REQUIRED_OFFLINE_PACKS,
      missing_required_packs: REQUIRED_OFFLINE_PACKS.filter((packId) => !installedPackIds.has(packId)),
      queue,
      counts,
    };
  }

  async function clearRebuildableCaches() {
    const cleared = {};
    let clearedCount = 0;
    for (const storeName of REBUILDABLE_STORES) {
      const records = await list(storeName);
      const preserved = records.filter((record) => (
        (storeName === "translations" || storeName === "apiResponses")
        && Boolean(record?.payload?.installation?.device_local)
      ));
      const removableCount = records.length - preserved.length;
      cleared[storeName] = removableCount;
      clearedCount += removableCount;
      await clearStore(storeName);
      await Promise.all(preserved.map((record) => put(storeName, record)));
    }
    const metadata = await list("metadata");
    const packMetadata = metadata.filter((entry) => String(entry.id || "").startsWith("pack:"));
    for (const entry of packMetadata) {
      await remove("metadata", entry.id);
    }
    cleared.metadata = packMetadata.length;
    clearedCount += packMetadata.length;
    return {
      cleared_count: clearedCount,
      stores: cleared,
      preserved_device_translations: true,
      preserved_stores: SNAPSHOT_STORES.filter((storeName) => storeName !== "metadata"),
    };
  }

  async function upsertOfflineNote(payload, method = "POST", url = "/api/notes") {
    const note = normalizeNote(payload, "local");
    await put("notes", note);
    await cacheNotesForChapter(note.book, note.chapter);
    return { ...note, offline: true, device_only: true, sync_status: "local" };
  }

  async function deleteOfflineNote(noteId, url) {
    const existing = await get("notes", noteId);
    await remove("notes", noteId);
    if (existing) {
      await cacheNotesForChapter(existing.book, existing.chapter);
    }
    return { deleted: true, offline: true, device_only: true, sync_status: "local" };
  }

  async function notesForChapter(book, chapter) {
    const notes = await list("notes");
    return notes
      .filter((note) => sameChapter(note, book, chapter))
      .sort((left, right) => String(left.created_at || "").localeCompare(String(right.created_at || "")));
  }

  async function upsertOfflineHighlight(payload, method = "POST", url = "/api/highlights") {
    const highlight = normalizeHighlight(payload, "local");
    await put("highlights", highlight);
    await cacheHighlightsForChapter(highlight.book, highlight.chapter);
    return { ...highlight, offline: true, device_only: true, sync_status: "local" };
  }

  async function deleteOfflineHighlight(highlightId, url) {
    const existing = await get("highlights", highlightId);
    await remove("highlights", highlightId);
    if (existing) {
      await cacheHighlightsForChapter(existing.book, existing.chapter);
    }
    return { deleted: true, offline: true, device_only: true, sync_status: "local" };
  }

  async function highlightsForChapter(book, chapter) {
    const highlights = await list("highlights");
    return highlights
      .filter((highlight) => sameChapter(highlight, book, chapter))
      .sort((left, right) => String(left.created_at || "").localeCompare(String(right.created_at || "")));
  }

  async function deleteOfflineSavedStudy(studyId, url) {
    const existing = await get("savedStudies", studyId);
    await remove("savedStudies", studyId);
    if (existing) {
      await cacheSavedStudiesForChapter(existing.book, existing.chapter);
    }
    return { deleted: true, offline: true, device_only: true, sync_status: "local" };
  }

  async function upsertOfflineSavedStudy(payload) {
    const study = normalizeSavedStudy(payload, "local");
    await put("savedStudies", study);
    if (study.book && study.chapter) {
      await cacheSavedStudiesForChapter(study.book, study.chapter);
    }
    return { ...study, offline: true, device_only: true, sync_status: "local" };
  }

  function isDeviceOnlyMutationUrl(url) {
    const path = new URL(String(url || "/"), window.location.origin).pathname;
    return path === "/api/notes"
      || path.startsWith("/api/notes/")
      || path === "/api/highlights"
      || path.startsWith("/api/highlights/")
      || path === "/api/saved-studies"
      || path.startsWith("/api/saved-studies/");
  }

  async function purgeDeviceOnlyMutations() {
    const mutations = await queuedMutations();
    const deviceOnly = mutations.filter((mutation) => isDeviceOnlyMutationUrl(mutation.url));
    await Promise.all(deviceOnly.map((mutation) => removeMutation(mutation.id)));
    return { purged_count: deviceOnly.length };
  }

  async function applyOnlineMutationResponse(url, method, payload) {
    if (isDeviceOnlyMutationUrl(url)) {
      return;
    }
    const path = new URL(String(url || "/"), window.location.origin).pathname;
    if (method === "DELETE") {
      const matchers = [
        ["/api/notes/", "notes"],
        ["/api/highlights/", "highlights"],
        ["/api/saved-studies/", "savedStudies"],
      ];
      const match = matchers.find(([prefix]) => path.startsWith(prefix));
      if (match) {
        const recordId = decodeURIComponent(path.slice(match[0].length));
        const existing = await get(match[1], recordId);
        await remove(match[1], recordId);
        if (existing?.book && existing?.chapter) {
          if (match[1] === "notes") {
            await cacheNotesForChapter(existing.book, existing.chapter);
          } else if (match[1] === "highlights") {
            await cacheHighlightsForChapter(existing.book, existing.chapter);
          } else if (match[1] === "savedStudies") {
            await cacheSavedStudiesForChapter(existing.book, existing.chapter);
          }
        }
      }
      return;
    }
    if (!payload || typeof payload !== "object" || !payload.id) {
      return;
    }
    if (path === "/api/notes" || path.startsWith("/api/notes/")) {
      await put("notes", normalizeNote(payload, "synced"));
      await cacheNotesForChapter(payload.book, payload.chapter);
    } else if (path === "/api/highlights" || path.startsWith("/api/highlights/")) {
      await put("highlights", normalizeHighlight(payload, "synced"));
      await cacheHighlightsForChapter(payload.book, payload.chapter);
    } else if (path === "/api/saved-studies") {
      await put("savedStudies", normalizeSavedStudy(payload, "synced"));
      await cacheSavedStudiesForChapter(payload.book, payload.chapter);
    }
  }

  async function savedStudiesForChapter(book, chapter) {
    const studies = await list("savedStudies");
    return studies
      .filter((study) => !book || !chapter || sameChapter(study, book, chapter))
      .sort((left, right) => String(right.created_at || "").localeCompare(String(left.created_at || "")));
  }

  async function upsertOfflineMapStudy(study) {
    return put("mapStudies", { ...study, id: study?.id || clientId("map-study") });
  }

  async function deleteOfflineMapStudy(id) {
    return remove("mapStudies", id);
  }

  async function cacheNotesForChapter(book, chapter) {
    const notes = await notesForChapter(book, chapter);
    await cacheApiResponse(`/api/notes/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`, { notes });
  }

  async function cacheHighlightsForChapter(book, chapter) {
    const highlights = await highlightsForChapter(book, chapter);
    await cacheApiResponse(`/api/highlights/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`, { highlights });
  }

  async function cacheSavedStudiesForChapter(book, chapter) {
    const savedStudies = await savedStudiesForChapter(book, chapter);
    await cacheApiResponse(
      `/api/saved-studies?book=${encodeURIComponent(book)}&chapter=${encodeURIComponent(chapter)}`,
      { saved_studies: savedStudies }
    );
  }

  function normalizeNote(payload, syncStatus) {
    const now = nowIso();
    return {
      id: payload.id || clientId("note"),
      book: String(payload.book || ""),
      chapter: Number(payload.chapter || 0),
      start_verse: Number(payload.start_verse || 0),
      end_verse: Number(payload.end_verse || payload.start_verse || 0),
      selected_text: String(payload.selected_text || ""),
      body: String(payload.body || ""),
      canonical_object_ids: Array.isArray(payload.canonical_object_ids) ? payload.canonical_object_ids : [],
      created_at: payload.created_at || now,
      updated_at: now,
      sync_status: syncStatus || payload.sync_status || "synced",
    };
  }

  function normalizeHighlight(payload, syncStatus) {
    const now = nowIso();
    return {
      id: payload.id || clientId("highlight"),
      book: String(payload.book || ""),
      chapter: Number(payload.chapter || 0),
      start_verse: Number(payload.start_verse || 0),
      end_verse: Number(payload.end_verse || payload.start_verse || 0),
      selected_text: String(payload.selected_text || ""),
      color: String(payload.color || "yellow"),
      created_at: payload.created_at || now,
      updated_at: now,
      sync_status: syncStatus || payload.sync_status || "synced",
    };
  }

  function normalizeSavedStudy(payload, syncStatus) {
    const now = nowIso();
    return {
      id: payload.id || clientId("study"),
      title: String(payload.title || ""),
      book: String(payload.book || ""),
      chapter: Number(payload.chapter || 0),
      start_verse: Number(payload.start_verse || payload.verse_start || 0),
      end_verse: Number(payload.end_verse || payload.verse_end || payload.start_verse || payload.verse_start || 0),
      selected_text: String(payload.selected_text || ""),
      study_type: String(payload.study_type || ""),
      question: String(payload.question || ""),
      answer: String(payload.answer || ""),
      canonical_object_ids: Array.isArray(payload.canonical_object_ids) ? payload.canonical_object_ids : [],
      created_at: payload.created_at || now,
      updated_at: payload.updated_at || now,
      sync_status: syncStatus || payload.sync_status || "synced",
    };
  }

  function normalizeSource(payload) {
    return {
      ...payload,
      id: String(payload.id || "").trim(),
      label: String(payload.label || payload.id || "").trim(),
      url: String(payload.url || "").trim(),
      license: String(payload.license || "").trim(),
      notes: String(payload.notes || "").trim(),
      references: Array.isArray(payload.references) ? payload.references : [],
      reference_count: Number(payload.reference_count || 0),
    };
  }

  function sourceSummary(source) {
    return {
      id: source.id,
      label: source.label,
      url: source.url,
      license: source.license,
      notes: source.notes,
    };
  }

  function renderSavedStudyHtml(study) {
    const reference = formatStudyReference(study);
    const canonical = (study.canonical_object_ids || []).map((objectId) => `
      <button type="button" class="canonical-object-badge" data-canonical-object-id="${escapeHtml(objectId)}" data-canonical-object-title="${escapeHtml(objectId)}">
        <span class="canonical-object-badge-title">${escapeHtml(objectId)}</span>
        <span class="canonical-object-badge-meta">saved link</span>
      </button>
    `).join("");
    return `
      <article class="answer">
        <div class="answer-header">
          <div>
            <p class="saved-study-label">Saved study</p>
            <h2>${escapeHtml(study.title || reference)}</h2>
          </div>
        </div>
        <p class="answer-reference">ASV ${escapeHtml(reference)}</p>
        <div class="answer-body">${renderPlainAnswer(study.answer)}</div>
        ${canonical ? `
          <section class="answer-canonical-context" aria-labelledby="answer-canonical-context-heading-offline-${escapeHtml(study.id)}">
            <div class="panel-heading answer-canonical-heading">
              <div>
                <h3 id="answer-canonical-context-heading-offline-${escapeHtml(study.id)}">Canonical Context</h3>
                <p class="answer-canonical-subtitle">Saved canonical object links associated with this study.</p>
              </div>
              <button type="button" class="secondary" data-open-canonical-browser>Open browser</button>
            </div>
            <div class="canonical-answer-badges">${canonical}</div>
          </section>
        ` : ""}
      </article>
      <aside class="metadata">
        <h2>Metadata</h2>
        <dl>
          <dt>Title</dt><dd>${escapeHtml(study.title || reference)}</dd>
          <dt>Study type</dt><dd>${escapeHtml(study.study_type || "saved")}</dd>
          <dt>Created</dt><dd>${escapeHtml(study.created_at || "")}</dd>
          <dt>Updated</dt><dd>${escapeHtml(study.updated_at || "")}</dd>
          <dt>Offline</dt><dd>cached</dd>
        </dl>
      </aside>
    `;
  }

  function renderPlainAnswer(value) {
    const blocks = String(value || "").split(/\n{2,}/).map((block) => block.trim()).filter(Boolean);
    if (!blocks.length) {
      return `<p class="empty">No saved answer text is available offline.</p>`;
    }
    return blocks.map((block) => `<p>${escapeHtml(block).replace(/\n/g, "<br>")}</p>`).join("");
  }

  function formatStudyReference(study) {
    let reference = `${study.book || "Passage"} ${study.chapter || ""}`.trim();
    if (Number(study.start_verse || 0) > 0) {
      const start = Number(study.start_verse);
      const end = Number(study.end_verse || start);
      reference = `${reference}:${start === end ? start : `${start}-${end}`}`;
    }
    return reference;
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function sameChapter(record, book, chapter) {
    return String(record.book || "").toLowerCase() === String(book || "").toLowerCase()
      && Number(record.chapter || 0) === Number(chapter || 0);
  }

  function normalizeUrlKey(url) {
    const resolved = new URL(String(url || "/"), window.location.origin);
    resolved.hash = "";
    if (resolved.origin !== window.location.origin) {
      return resolved.toString();
    }
    return `${resolved.pathname}${resolved.search}`;
  }

  function isChapterUrl(url) {
    return /^\/api\/bible\/[^/?]+\/\d+(?:\?|$)/.test(url);
  }

  window.BHFOfflineDB = {
    openDatabase,
    get,
    put,
    remove,
    delete: remove,
    list,
    cacheApiResponse,
    readApiResponse,
    readTextResponse,
    applyOnlineMutationResponse,
    enqueueMutation,
    queuedMutations,
    mutationQueueSummary,
    markMutationAttempt,
    removeMutation,
    exportSnapshot,
    importSnapshot,
    readinessReport,
    clearRebuildableCaches,
    upsertOfflineNote,
    deleteOfflineNote,
    notesForChapter,
    upsertOfflineHighlight,
    deleteOfflineHighlight,
    highlightsForChapter,
    deleteOfflineSavedStudy,
    upsertOfflineSavedStudy,
    savedStudiesForChapter,
    upsertOfflineMapStudy,
    deleteOfflineMapStudy,
    purgeDeviceOnlyMutations,
  };
})();
