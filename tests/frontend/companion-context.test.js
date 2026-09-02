const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");


function loadContextApi({
  presentationOptions,
  fetchImpl,
  runtime = {presentationTransport: "job", presentationJobs: true},
}) {
  const document = {
    addEventListener: () => {},
    dispatchEvent: () => {},
  };
  const window = {
    BHFModelSettings: {
      getPresentationRequestOptions: async () => presentationOptions,
    },
    BHFJobFlow: {
      pollJsonJob: async ({poll, signal}) => {
        for (let attempt = 0; attempt < 5; attempt += 1) {
          if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
          const status = await poll();
          if (status.status === "succeeded") return status.result;
          if (status.status === "failed" || status.status === "expired") {
            const error = new Error(status.message || "failed");
            error.code = status.error_category;
            throw error;
          }
        }
        throw new Error("polling expired");
      },
    },
    BHFRuntimeConfig: runtime,
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
        json: async () => url === "/api/study/presentation"
          ? {job_id: "job-25", status: "queued"}
          : {
            status: "succeeded",
            result: {evidence_bundle: {evidence_hash: "hash-25"}},
          },
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

  assert.equal(requests.length, 2);
  assert.equal(requests[0].url, "/api/study/presentation");
  assert.equal(requests[0].options.headers["X-BHF-OpenRouter-Key"], "transient-secret");
  const payload = JSON.parse(requests[0].options.body);
  assert.equal(payload.ai_profile.adapter, "openrouter");
  assert.equal(payload.ai_profile.model, "openrouter/free");
  assert.equal(JSON.stringify(payload).includes("transient-secret"), false);
  assert.equal(requests[1].url, "/api/study/presentation/jobs/job-25");
  assert.equal("X-BHF-OpenRouter-Key" in requests[1].options.headers, false);
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


test("synchronous transport returns the final presentation without polling", async () => {
  const requests = [];
  const api = loadContextApi({
    runtime: {presentationTransport: "synchronous", presentationJobs: false},
    presentationOptions: {
      enabled: true,
      headers: {"X-BHF-OpenRouter-Key": "transient-secret"},
      profile: {adapter: "openrouter", model: "test:model"},
    },
    fetchImpl: async (url, options) => {
      requests.push({url, options});
      return {
        ok: true,
        json: async () => ({
          evidence_bundle: {evidence_hash: "hash-4"},
          presentation_packet: {
            cards: [{id: "ai-card"}],
            presentation_mode: "generated",
          },
        }),
      };
    },
  });

  const availability = await api.getEnhancementAvailability({
    presentation_enhancement: {supported: true, server_configured: false},
  });
  const result = await api.enhance(
    {book: "John", chapter: 4},
    {presentation_enhancement: {evidence_hash: "hash-4"}},
  );

  assert.equal(availability.available, true);
  assert.equal(result.presentation_packet.cards[0].id, "ai-card");
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, "/api/study/presentation");
  assert.equal(requests[0].options.headers["X-BHF-OpenRouter-Key"], "transient-secret");
});


test("unavailable presentation transport retains deterministic presentation", async () => {
  let requests = 0;
  const api = loadContextApi({
    runtime: {presentationTransport: "unavailable", presentationJobs: false},
    presentationOptions: {
      enabled: true,
      headers: {"X-BHF-OpenRouter-Key": "transient-secret"},
      profile: {adapter: "openrouter", model: "test:model"},
    },
    fetchImpl: async () => { requests += 1; },
  });

  const availability = await api.getEnhancementAvailability({
    presentation_enhancement: {supported: true, server_configured: false},
  });
  const result = await api.enhance(
    {book: "John", chapter: 4},
    {presentation_enhancement: {evidence_hash: "hash-4"}},
  );

  assert.equal(availability.available, false);
  assert.equal(availability.reason, "presentation_unavailable");
  assert.equal(result, null);
  assert.equal(requests, 0);
});


test("aborting a synchronous presentation aborts its one fetch silently", async () => {
  let fetchSignal;
  const controller = new AbortController();
  const api = loadContextApi({
    runtime: {presentationTransport: "synchronous", presentationJobs: false},
    presentationOptions: {
      enabled: true,
      headers: {},
      profile: null,
    },
    fetchImpl: async (_url, options) => {
      fetchSignal = options.signal;
      return new Promise((_resolve, reject) => {
        options.signal.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        }, {once: true});
      });
    },
  });

  const pending = api.enhance(
    {book: "John", chapter: 4},
    {presentation_enhancement: {evidence_hash: "hash-4"}},
    {signal: controller.signal},
  );
  await new Promise((resolve) => setImmediate(resolve));
  controller.abort();

  await assert.rejects(pending, (error) => error.name === "AbortError");
  assert.equal(fetchSignal.aborted, true);
});
