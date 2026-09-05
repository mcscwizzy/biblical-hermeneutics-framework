const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");


function loadApi({cachedPayload, fetchResponse, fetchError} = {}) {
  const cached = [];
  const window = {
    location: {origin: "http://test"},
    BHFBackendRouting: {resolveUrl: (url) => url},
    BHFRuntimeConfig: {},
    BHFOfflineDB: {
      readApiResponse: async () => cachedPayload,
      cacheApiResponse: async (_url, payload) => cached.push(payload),
    },
  };
  const navigator = {onLine: true};
  const fetch = async () => {
    if (fetchError) throw fetchError;
    return {
      ok: true,
      headers: {get: () => "application/json"},
      text: async () => JSON.stringify(fetchResponse),
    };
  };
  const context = vm.createContext({window, navigator, fetch, URL, Headers, FormData});
  vm.runInContext(fs.readFileSync("bhf_web/static/api/http.js", "utf8"), context);
  return {api: window.BHFApi, cached};
}


test("commentary cache ignores an older release and caches the current release", async () => {
  const {api, cached} = loadApi({
    cachedPayload: {release: "commentary-v0.9", commentary: "old"},
    fetchResponse: {release: "commentary-v1.0", commentary: "current"},
  });

  const result = await api.requestJson("/api/bhf-commentary/Genesis/1");
  assert.equal(result.commentary, "current");
  assert.equal(cached.length, 1);
  assert.equal(cached[0].release, "commentary-v1.0");
});


test("offline commentary does not fall back to an older release", async () => {
  const {api} = loadApi({
    cachedPayload: {release: "commentary-v0.9", commentary: "old"},
    fetchError: new Error("offline"),
  });

  await assert.rejects(
    api.requestJson("/api/bhf-commentary/Genesis/1"),
    /offline/,
  );
});
