const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const workerSource = fs.readFileSync(
  path.join(__dirname, "../../bhf_web/static/sw.js"),
  "utf8",
);

function createWorker({fetchResponse, cachePut, cachedResponse, cachedMapEntries = []} = {}) {
  const listeners = new Map();
  const cacheAssets = new Map();
  const cacheResponses = new Map();
  const deletedCaches = [];
  const deletedRequests = [];
  const networkRequests = [];
  const cachePutCalls = [];
  for (const entry of cachedMapEntries) {
    const url = String(entry.url);
    const entries = cacheAssets.get("bhf-api-v53") || new Set();
    entries.add(url);
    cacheAssets.set("bhf-api-v53", entries);
    cacheResponses.set(`bhf-api-v53:${url}`, entry.response.clone());
  }
  const makeCache = (name) => ({
    add: async (asset) => {
      const entries = cacheAssets.get(name) || new Set();
      entries.add(asset);
      cacheAssets.set(name, entries);
      const absoluteUrl = new URL(asset, self.location.origin).href;
      cacheResponses.set(`${name}:${absoluteUrl}`, new Response(`cached ${asset}`, {status: 200}));
    },
    put: async (request, response) => {
      cachePutCalls.push(request.url);
      if (cachePut) await cachePut(request, response);
      const entries = cacheAssets.get(name) || new Set();
      entries.add(request.url);
      cacheAssets.set(name, entries);
      cacheResponses.set(`${name}:${request.url}`, response.clone());
    },
    keys: async () => Array.from(cacheAssets.get(name) || []).map((url) => new Request(url)),
    match: async (request) => cacheResponses.get(`${name}:${request.url || String(request)}`)?.clone(),
    delete: async (request) => {
      const url = request.url || String(request);
      deletedRequests.push(url);
      cacheAssets.get(name)?.delete(url);
      cacheResponses.delete(`${name}:${url}`);
      return true;
    },
  });
  const caches = {
    open: async (name) => makeCache(name),
    match: async (request) => {
      if (cachedResponse) return cachedResponse.clone?.() || cachedResponse;
      const url = request?.url || new URL(String(request), self.location.origin).href;
      for (const [key, response] of cacheResponses.entries()) {
        if (key.endsWith(`:${url}`)) return response.clone();
      }
      return undefined;
    },
    keys: async () => ["bhf-shell-v48", "bhf-static-v48", "bhf-api-v48"],
    delete: async (name) => {
      deletedCaches.push(name);
      return true;
    },
  };
  const self = {
    location: {origin: "https://reader.example"},
    clients: {claim: async () => undefined},
    addEventListener: (name, callback) => listeners.set(name, callback),
    skipWaiting: () => undefined,
  };
  const sandbox = {
    self,
    caches,
    URL,
    Request,
    Response,
    Headers,
    Promise,
    fetch: async (request) => {
      networkRequests.push(request.url || String(request));
      return fetchResponse ? fetchResponse(request) : new Response("network asset", {status: 200});
    },
  };
  vm.runInNewContext(workerSource, sandbox, {filename: "sw.js"});
  return {listeners, cacheAssets, cacheResponses, deletedCaches, deletedRequests, networkRequests, cachePutCalls};
}

test("service worker precaches the explorer module and retires the previous cache version", async () => {
  const worker = createWorker();
  let installPromise;
  worker.listeners.get("install")({
    waitUntil: (promise) => { installPromise = promise; },
  });
  await installPromise;

  assert.equal(worker.cacheAssets.get("bhf-static-v53")?.has("/static/narrative-explorer.js"), true);
  assert.equal(worker.cacheAssets.get("bhf-static-v53")?.has("/static/maps/MapFocusAcknowledgment.js"), true);
  assert.equal(worker.cacheAssets.get("bhf-static-v53")?.has("/static/companion-locations.js"), true);
  assert.equal(worker.cacheAssets.get("bhf-static-v53")?.has("/static/companion-places-locations.js"), true);
  assert.equal(worker.cacheAssets.get("bhf-static-v53")?.has("/static/commentary.js"), true);
  assert.equal(worker.cacheAssets.get("bhf-static-v53")?.has("/static/commentary.js?v=20261030a"), true);

  let activatePromise;
  worker.listeners.get("activate")({
    waitUntil: (promise) => { activatePromise = promise; },
  });
  await activatePromise;
  assert.deepEqual(worker.deletedCaches.sort(), ["bhf-api-v48", "bhf-shell-v48", "bhf-static-v48"]);
});


test("the exact versioned Tyndale script stays available after an offline reload", async () => {
  const worker = createWorker({fetchResponse: async () => { throw new Error("offline"); }});
  let installPromise;
  worker.listeners.get("install")({waitUntil: (promise) => { installPromise = promise; }});
  await installPromise;

  const url = "https://reader.example/static/commentary.js?v=20261030a";
  let responsePromise = null;
  worker.listeners.get("fetch")({
    request: new Request(url),
    respondWith: (promise) => { responsePromise = promise; },
  });

  const response = await responsePromise;
  assert.equal(response.status, 200);
  assert.equal(await response.text(), "cached /static/commentary.js?v=20261030a");
  assert.deepEqual(worker.networkRequests, [url]);
});

test("Narrative Explorer API requests bypass service-worker caching", async () => {
  const worker = createWorker();
  let responsePromise = null;
  const request = new Request(
    "https://reader.example/api/narrative-explorer/v1/passages/Genesis/1",
    {method: "GET"},
  );
  worker.listeners.get("fetch")({
    request,
    respondWith: (promise) => { responsePromise = promise; },
  });

  assert.equal(responsePromise, null);
  assert.deepEqual(worker.networkRequests, []);
  assert.equal(worker.cacheAssets.size, 0);
});


test("Study Companion location pages use network-first caching and remain readable offline", async () => {
  const url = "https://reader.example/api/study/companion-locations?book=Joshua&chapter=15&cursor=25&limit=25";
  const worker = createWorker({
    cachedResponse: new Response(JSON.stringify({items: [{id: "map-id"}], next_cursor: null}), {
      status: 200,
      headers: {"Content-Type": "application/json"},
    }),
    fetchResponse: async () => { throw new Error("offline"); },
  });
  let responsePromise = null;
  worker.listeners.get("fetch")({
    request: new Request(url),
    respondWith: (promise) => { responsePromise = promise; },
    waitUntil: () => {},
  });

  const response = await responsePromise;
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("X-BHF-Offline"), "true");
  assert.deepEqual(await response.json(), {items: [{id: "map-id"}], next_cursor: null});
  assert.deepEqual(worker.networkRequests, [url]);
});

test("service worker lifetime includes successful map response cache writes", async () => {
  let finishCacheWrite;
  const pendingCacheWrite = new Promise((resolve) => { finishCacheWrite = resolve; });
  const worker = createWorker({
    fetchResponse: async () => new Response("{}", {
      status: 200,
      headers: {"Content-Type": "application/json", "Content-Length": "2"},
    }),
    cachePut: async () => pendingCacheWrite,
  });
  let responsePromise = null;
  let lifetimePromise = null;
  worker.listeners.get("fetch")({
    request: new Request("https://reader.example/api/maps/catalog"),
    respondWith: (promise) => { responsePromise = promise; },
    waitUntil: (promise) => { lifetimePromise = promise; },
  });

  const response = await responsePromise;
  assert.equal(await response.text(), "{}");
  while (worker.cachePutCalls.length === 0) await Promise.resolve();
  assert.deepEqual(worker.cachePutCalls, ["https://reader.example/api/maps/catalog"]);
  let lifetimeFinished = false;
  lifetimePromise.then(() => { lifetimeFinished = true; });
  await Promise.resolve();
  assert.equal(lifetimeFinished, false);
  finishCacheWrite();
  await lifetimePromise;
  assert.equal(lifetimeFinished, true);
});

test("small map responses remain cached", async () => {
  const worker = createWorker({
    fetchResponse: async () => new Response("small map response", {
      status: 200,
      headers: {"Content-Type": "application/json", "Content-Length": "18"},
    }),
  });
  let responsePromise = null;
  let lifetimePromise = null;
  worker.listeners.get("fetch")({
    request: new Request("https://reader.example/api/maps/catalog"),
    respondWith: (promise) => { responsePromise = promise; },
    waitUntil: (promise) => { lifetimePromise = promise; },
  });

  const response = await responsePromise;
  assert.equal(await response.text(), "small map response");
  await lifetimePromise;
  assert.deepEqual(worker.cachePutCalls, ["https://reader.example/api/maps/catalog"]);
});

test("oversized map responses reach the page intact without a Cache Storage clone", async () => {
  const payload = JSON.stringify({markers: [{id: "zion"}], padding: "x".repeat(600_000)});
  const worker = createWorker({
    fetchResponse: async () => new Response(payload, {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Content-Length": String(new TextEncoder().encode(payload).byteLength),
      },
    }),
  });
  let responsePromise = null;
  let lifetimePromise = null;
  worker.listeners.get("fetch")({
    request: new Request("https://reader.example/api/maps/related-passages-for-place?place_id=zion"),
    respondWith: (promise) => { responsePromise = promise; },
    waitUntil: (promise) => { lifetimePromise = promise; },
  });

  const response = await responsePromise;
  const received = await response.text();
  await lifetimePromise;

  assert.equal(received, payload);
  assert.deepEqual(worker.cachePutCalls, []);
});

test("map responses prefer the network so an older cached source cannot override current data", async () => {
  const worker = createWorker({
    cachedResponse: new Response('{"source":"stale"}', {
      status: 200,
      headers: {"Content-Type": "application/json", "Content-Length": "18"},
    }),
    fetchResponse: async () => new Response('{"source":"current"}', {
      status: 200,
      headers: {"Content-Type": "application/json", "Content-Length": "20"},
    }),
  });
  let responsePromise = null;
  worker.listeners.get("fetch")({
    request: new Request("https://reader.example/api/maps/catalog"),
    respondWith: (promise) => { responsePromise = promise; },
    waitUntil: () => {},
  });

  const response = await responsePromise;
  assert.deepEqual(await response.json(), {source: "current"});
  assert.deepEqual(worker.networkRequests, ["https://reader.example/api/maps/catalog"]);
});

test("network refresh preserves the offline-pack retention marker on the updated cache entry", async () => {
  const url = "https://reader.example/api/maps/archaeology";
  const worker = createWorker({
    cachedMapEntries: [{url, response: new Response('{"source":"pack"}', {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Content-Length": "17",
        "X-BHF-Offline-Pack": "maps",
      },
    })}],
    fetchResponse: async () => new Response('{"source":"current"}', {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Content-Length": "20",
      },
    }),
  });
  let responsePromise = null;
  let lifetimePromise = null;
  worker.listeners.get("fetch")({
    request: new Request(url),
    respondWith: (promise) => { responsePromise = promise; },
    waitUntil: (promise) => { lifetimePromise = promise; },
  });

  assert.deepEqual(await (await responsePromise).json(), {source: "current"});
  await lifetimePromise;
  const cached = worker.cacheResponses.get(`bhf-api-v53:${url}`);
  assert.equal(cached.headers.get("X-BHF-Offline-Pack"), "maps");
  assert.deepEqual(await cached.json(), {source: "current"});
});

test("map cache keeps a fixed number of the newest small responses", async () => {
  const worker = createWorker({
    fetchResponse: async () => new Response("{}", {
      status: 200,
      headers: {"Content-Type": "application/json", "Content-Length": "2"},
    }),
  });

  for (let index = 0; index < 40; index += 1) {
    let responsePromise = null;
    let lifetimePromise = null;
    worker.listeners.get("fetch")({
      request: new Request(`https://reader.example/api/maps/search?q=${index}`),
      respondWith: (promise) => { responsePromise = promise; },
      waitUntil: (promise) => { lifetimePromise = promise; },
    });
    const response = await responsePromise;
    assert.equal(await response.text(), "{}");
    await lifetimePromise;
  }

  const storedMapRequests = Array.from(worker.cacheAssets.get("bhf-api-v53") || [])
    .filter((url) => url.includes("/api/maps/"));
  assert.equal(storedMapRequests.length, 32);
  assert.equal(storedMapRequests[0], "https://reader.example/api/maps/search?q=8");
  assert.equal(storedMapRequests.at(-1), "https://reader.example/api/maps/search?q=39");
});

test("an uncached large map response produces an explicit offline miss", async () => {
  const worker = createWorker({
    fetchResponse: async () => { throw new Error("network unavailable"); },
  });
  let responsePromise = null;
  worker.listeners.get("fetch")({
    request: new Request("https://reader.example/api/maps/places-for-passage?include_related_passages=true"),
    respondWith: (promise) => { responsePromise = promise; },
    waitUntil: () => {},
  });

  const response = await responsePromise;
  const payload = await response.json();
  assert.equal(response.status, 503);
  assert.equal(payload.offline, true);
  assert.equal(payload.cache_status, "miss");
  assert.match(payload.error, /not available offline/);
});

test("large Maps offline-pack envelopes are returned but not cloned into Cache Storage", async () => {
  const payload = JSON.stringify({pack_id: "maps", responses: [], padding: "x".repeat(600_000)});
  const worker = createWorker({
    fetchResponse: async () => new Response(payload, {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Content-Length": String(new TextEncoder().encode(payload).byteLength),
      },
    }),
  });
  let responsePromise = null;
  let lifetimePromise = null;
  worker.listeners.get("fetch")({
    request: new Request("https://reader.example/api/offline/packs/maps"),
    respondWith: (promise) => { responsePromise = promise; },
    waitUntil: (promise) => { lifetimePromise = promise; },
  });

  const response = await responsePromise;
  assert.deepEqual(await response.json(), {pack_id: "maps", responses: [], padding: "x".repeat(600_000)});
  await lifetimePromise;
  assert.deepEqual(worker.cachePutCalls, []);
});

test("map cache enforces an aggregate eight-megabyte bound", async () => {
  const worker = createWorker({
    fetchResponse: async () => new Response("{}", {
      status: 200,
      headers: {"Content-Type": "application/json", "Content-Length": "400000"},
    }),
  });

  for (let index = 0; index < 24; index += 1) {
    let responsePromise = null;
    let lifetimePromise = null;
    worker.listeners.get("fetch")({
      request: new Request(`https://reader.example/api/maps/search?large=${index}`),
      respondWith: (promise) => { responsePromise = promise; },
      waitUntil: (promise) => { lifetimePromise = promise; },
    });
    const response = await responsePromise;
    await response.text();
    await lifetimePromise;
  }

  const storedMapRequests = Array.from(worker.cacheAssets.get("bhf-api-v53") || [])
    .filter((url) => url.includes("/api/maps/search?large="));
  assert.equal(storedMapRequests.length, 20);
  assert.equal(storedMapRequests[0], "https://reader.example/api/maps/search?large=4");
  assert.equal(storedMapRequests.at(-1), "https://reader.example/api/maps/search?large=23");
});
