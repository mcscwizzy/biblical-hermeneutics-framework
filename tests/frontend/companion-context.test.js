const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");


function loadContextApi({presentationOptions, fetchImpl}) {
  const document = {
    addEventListener: () => {},
    dispatchEvent: () => {},
  };
  const window = {
    BHFModelSettings: {
      getPresentationRequestOptions: async () => presentationOptions,
    },
    location: {origin: "https://bhf.test"},
  };
  const context = vm.createContext({
    CustomEvent: class CustomEvent {
      constructor(type, options = {}) { this.type = type; this.detail = options.detail; }
    },
    DOMException,
    URL,
    URLSearchParams,
    console,
    document,
    fetch: fetchImpl,
    navigator: {onLine: true},
    window,
  });
  vm.runInContext(
    fs.readFileSync("bhf_web/static/companion-context.js", "utf8"),
    context,
  );
  return window.BHFCompanionContext;
}


test("presentation request reuses transient OpenRouter header and selected model profile", async () => {
  const requests = [];
  const api = loadContextApi({
    presentationOptions: {
      enabled: true,
      headers: {"X-BHF-OpenRouter-Key": "transient-secret"},
      profile: {
        adapter: "openrouter",
        model: "openrouter/free",
        base_url: "https://openrouter.ai/api/v1",
      },
    },
    fetchImpl: async (url, options) => {
      requests.push({url, options});
      return {
        ok: true,
        json: async () => ({evidence_bundle: {evidence_hash: "hash-25"}}),
      };
    },
  });

  await api.enhance(
    {book: "1 Samuel", chapter: 25},
    {
      evidence_bundle: {evidence_hash: "hash-25"},
      presentation_enhancement: {supported: true, evidence_hash: "hash-25"},
    },
  );

  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, "/api/study/presentation");
  assert.equal(requests[0].options.headers["X-BHF-OpenRouter-Key"], "transient-secret");
  const payload = JSON.parse(requests[0].options.body);
  assert.equal(payload.ai_profile.adapter, "openrouter");
  assert.equal(payload.ai_profile.model, "openrouter/free");
  assert.equal(JSON.stringify(payload).includes("transient-secret"), false);
});


test("disabled presentation preference makes no network request", async () => {
  let requests = 0;
  const api = loadContextApi({
    presentationOptions: {enabled: false, headers: {}, profile: null},
    fetchImpl: async () => { requests += 1; },
  });

  const result = await api.enhance(
    {book: "John", chapter: 4},
    {
      evidence_bundle: {evidence_hash: "hash-4"},
      presentation_enhancement: {supported: true, evidence_hash: "hash-4"},
    },
  );

  assert.equal(result, null);
  assert.equal(requests, 0);
});


test("enhancement availability preserves provider-unavailable reason without requesting", async () => {
  let requests = 0;
  const api = loadContextApi({
    presentationOptions: {
      enabled: false,
      reason: "provider_unavailable",
      headers: {},
      profile: null,
    },
    fetchImpl: async () => { requests += 1; },
  });
  const context = {
    presentation_enhancement: {supported: true, server_configured: false},
  };

  const availability = await api.getEnhancementAvailability(context);

  assert.equal(availability.available, false);
  assert.equal(availability.reason, "provider_unavailable");
  assert.equal(requests, 0);
});
