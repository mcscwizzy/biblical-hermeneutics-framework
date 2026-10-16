const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const workerSource = fs.readFileSync(
  path.join(__dirname, "../../bhf_web/static/sw.js"),
  "utf8",
);

function createWorker({fetchResponse, cachePut} = {}) {
  const listeners = new Map();
  const cacheAssets = new Map();
  const deletedCaches = [];
  const networkRequests = [];
  const cachePutCalls = [];
  const makeCache = (name) => ({
    add: async (asset) => {
      const entries = cacheAssets.get(name) || new Set();
      entries.add(asset);
      cacheAssets.set(name, entries);
    },
    put: async (request, response) => {
      cachePutCalls.push(request.url);
      if (cachePut) await cachePut(request, response);
      const entries = cacheAssets.get(name) || new Set();
      entries.add(request.url);
      cacheAssets.set(name, entries);
    },
  });
  const caches = {
    open: async (name) => makeCache(name),
    match: async () => undefined,
    keys: async () => ["bhf-shell-v47", "bhf-static-v47", "bhf-api-v47"],
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
  return {listeners, cacheAssets, deletedCaches, networkRequests, cachePutCalls};
}

test("service worker precaches the explorer module and retires the previous cache version", async () => {
  const worker = createWorker();
  let installPromise;
  worker.listeners.get("install")({
    waitUntil: (promise) => { installPromise = promise; },
  });
  await installPromise;

  assert.equal(worker.cacheAssets.get("bhf-static-v48")?.has("/static/narrative-explorer.js"), true);
  assert.equal(worker.cacheAssets.get("bhf-static-v48")?.has("/static/maps/MapFocusAcknowledgment.js"), true);

  let activatePromise;
  worker.listeners.get("activate")({
    waitUntil: (promise) => { activatePromise = promise; },
  });
  await activatePromise;
  assert.deepEqual(worker.deletedCaches.sort(), ["bhf-api-v47", "bhf-shell-v47", "bhf-static-v47"]);
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

test("service worker lifetime includes successful map response cache writes", async () => {
  let finishCacheWrite;
  const pendingCacheWrite = new Promise((resolve) => { finishCacheWrite = resolve; });
  const worker = createWorker({
    fetchResponse: async () => new Response("complete map response", {status: 200}),
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
  assert.equal(await response.text(), "complete map response");
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
      headers: {"Content-Length": "18"},
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
