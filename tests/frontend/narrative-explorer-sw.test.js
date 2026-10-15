const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const workerSource = fs.readFileSync(
  path.join(__dirname, "../../bhf_web/static/sw.js"),
  "utf8",
);

function createWorker() {
  const listeners = new Map();
  const cacheAssets = new Map();
  const deletedCaches = [];
  const networkRequests = [];
  const makeCache = (name) => ({
    add: async (asset) => {
      const entries = cacheAssets.get(name) || new Set();
      entries.add(asset);
      cacheAssets.set(name, entries);
    },
    put: async (request) => {
      const entries = cacheAssets.get(name) || new Set();
      entries.add(request.url);
      cacheAssets.set(name, entries);
    },
  });
  const caches = {
    open: async (name) => makeCache(name),
    match: async () => undefined,
    keys: async () => ["bhf-shell-v45", "bhf-static-v45", "bhf-api-v45"],
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
      return new Response("network asset", {status: 200});
    },
  };
  vm.runInNewContext(workerSource, sandbox, {filename: "sw.js"});
  return {listeners, cacheAssets, deletedCaches, networkRequests};
}

test("service worker precaches the explorer module and retires the previous cache version", async () => {
  const worker = createWorker();
  let installPromise;
  worker.listeners.get("install")({
    waitUntil: (promise) => { installPromise = promise; },
  });
  await installPromise;

  assert.equal(worker.cacheAssets.get("bhf-static-v46")?.has("/static/narrative-explorer.js"), true);

  let activatePromise;
  worker.listeners.get("activate")({
    waitUntil: (promise) => { activatePromise = promise; },
  });
  await activatePromise;
  assert.deepEqual(worker.deletedCaches.sort(), ["bhf-api-v45", "bhf-shell-v45", "bhf-static-v45"]);
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
