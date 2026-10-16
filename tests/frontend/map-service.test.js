const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const {pathToFileURL} = require("node:url");

class MemoryStorage {
  #values = new Map();

  get length() { return this.#values.size; }
  key(index) { return Array.from(this.#values.keys())[index] || null; }
  getItem(key) { return this.#values.get(String(key)) ?? null; }
  setItem(key, value) { this.#values.set(String(key), String(value)); }
  removeItem(key) { this.#values.delete(String(key)); }
}

async function createMapService(t, fetchImpl, {legacyEntries = []} = {}) {
  const priorWindow = globalThis.window;
  const priorLocalStorage = globalThis.localStorage;
  const priorFetch = globalThis.fetch;
  const localStorage = new MemoryStorage();
  for (const [key, value] of legacyEntries) localStorage.setItem(key, value);
  globalThis.window = {};
  globalThis.localStorage = localStorage;
  globalThis.fetch = fetchImpl;
  t.after(() => {
    globalThis.window = priorWindow;
    globalThis.localStorage = priorLocalStorage;
    globalThis.fetch = priorFetch;
  });
  const modulePath = pathToFileURL(path.join(__dirname, "../../bhf_web/static/maps/mapService.js"));
  modulePath.searchParams.set("test", `${Date.now()}-${Math.random()}`);
  const service = await import(modulePath.href);
  return {service, localStorage};
}

function jsonResponse(value) {
  const body = JSON.stringify(value);
  return new Response(body, {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Content-Length": String(new TextEncoder().encode(body).byteLength),
    },
  });
}

test("passage Maps can explicitly request compact related-passage mode", async (t) => {
  let requestedUrl = "";
  const {service, localStorage} = await createMapService(t, async (url) => {
    requestedUrl = String(url);
    return jsonResponse({markers: [{id: "zion", related_references: []}], matched_place_ids: ["zion"]});
  });

  const result = await service.loadPlacesForPassage({
    book: "John", chapter: 2, includeRelatedPassages: false,
  });

  const url = new URL(requestedUrl, "https://reader.example");
  assert.equal(url.searchParams.get("include_related_passages"), "false");
  assert.equal(result.markers[0].id, "zion");
  assert.equal(localStorage.length, 1);
  assert.ok(localStorage.key(0).startsWith("bhf.map-service:v2:"));
});

test("existing passage map-service callers keep the full API default", async (t) => {
  let requestedUrl = "";
  const {service} = await createMapService(t, async (url) => {
    requestedUrl = String(url);
    return jsonResponse({markers: [{id: "zion", related_passages: {groups: []}}]});
  });

  const result = await service.loadPlacesForPassage({book: "John", chapter: 2});

  const url = new URL(requestedUrl, "https://reader.example");
  assert.equal(url.searchParams.has("include_related_passages"), false);
  assert.deepEqual(result.markers[0].related_passages, {groups: []});
});

test("passage-mode catalog requests can ask only for timeline metadata", async (t) => {
  let requestedUrl = "";
  const {service} = await createMapService(t, async (url) => {
    requestedUrl = String(url);
    return jsonResponse({timeline: {period_options: [{value: "all", label: "All periods"}]}});
  });

  const result = await service.loadMapCatalog({includeRecords: false});

  const url = new URL(requestedUrl, "https://reader.example");
  assert.equal(url.searchParams.get("include_records"), "false");
  assert.deepEqual(result, {timeline: {period_options: [{value: "all", label: "All periods"}]}});
});

test("map-service cache migration clears legacy unbounded local-storage entries", async (t) => {
  const legacyKey = "bhf.map-service:/api/maps/places-for-passage?book=John&chapter=2";
  const {localStorage} = await createMapService(t, async () => jsonResponse({}), {
    legacyEntries: [[legacyKey, JSON.stringify({value: {markers: [], padding: "x".repeat(1_000_000)}})]],
  });

  assert.equal(localStorage.getItem(legacyKey), null);
  assert.equal(localStorage.length, 0);
});

test("oversized details stay in memory and report cached data accurately when the network fails", async (t) => {
  let online = true;
  const value = {place_id: "zion", groups: [], padding: "x".repeat(300_000)};
  const {service, localStorage} = await createMapService(t, async () => {
    if (!online) throw new Error("offline");
    return jsonResponse(value);
  });

  const onlineResult = await service.loadRelatedPassagesForPlace("zion");
  assert.equal(onlineResult.place_id, "zion");
  assert.equal(localStorage.length, 0);
  online = false;
  const offlineResult = await service.loadRelatedPassagesForPlace("zion");
  assert.equal(offlineResult.offline, true);
  assert.equal(offlineResult.cache_status, "stale");
  assert.equal(offlineResult.padding.length, value.padding.length);
});

test("Service Worker cached Maps responses retain the offline state without being rewritten", async (t) => {
  const responseBody = JSON.stringify({markers: [{id: "zion"}]});
  const {service, localStorage} = await createMapService(t, async () => new Response(responseBody, {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Content-Length": String(new TextEncoder().encode(responseBody).byteLength),
      "X-BHF-Offline": "true",
    },
  }));

  const result = await service.loadPlacesForPassage({book: "John", chapter: 2});

  assert.equal(result.offline, true);
  assert.equal(result.cache_status, "service_worker");
  assert.equal(localStorage.length, 0);
});

test("persistent Maps storage stays within the entry-count and byte caps", async (t) => {
  const {service, localStorage} = await createMapService(t, async (url) => {
    const period = new URL(String(url), "https://reader.example").searchParams.get("period");
    return jsonResponse({period, padding: "x".repeat(20_000)});
  });

  for (let index = 0; index < 22; index += 1) {
    await service.loadMapCatalog({period: `test-period-${index}`});
  }

  let storedBytes = 0;
  for (let index = 0; index < localStorage.length; index += 1) {
    storedBytes += localStorage.getItem(localStorage.key(index)).length * 2;
  }
  assert.ok(localStorage.length <= 16);
  assert.ok(storedBytes <= 2 * 1024 * 1024);
});
