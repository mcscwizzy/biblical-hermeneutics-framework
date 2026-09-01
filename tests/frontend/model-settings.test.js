const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");


function loadModelSettings(records, runtimeAi = {}) {
  const events = [];
  const document = {
    title: "BHF",
    body: {classList: {contains: () => false}},
    querySelector: () => null,
    querySelectorAll: () => [],
    getElementById: () => null,
    dispatchEvent: (event) => events.push(event),
  };
  const window = {
    BHFTestMode: true,
    BHFRuntimeConfig: {ai: runtimeAi},
    BHFOfflineDB: {
      get: async (_store, id) => records.get(id) || null,
      put: async (_store, value) => {
        records.set(value.id, structuredClone(value));
        return value;
      },
      remove: async (_store, id) => records.delete(id),
    },
    location: {
      origin: "https://bhf.test",
      pathname: "/",
      protocol: "https:",
      hostname: "bhf.test",
      search: "",
      assign: () => {},
    },
    history: {replaceState: () => {}},
  };
  const context = vm.createContext({
    CustomEvent: class CustomEvent {
      constructor(type, options = {}) { this.type = type; this.detail = options.detail; }
    },
    URL,
    URLSearchParams,
    TextDecoder,
    TextEncoder,
    atob,
    btoa,
    console,
    document,
    fetch: async () => { throw new Error("unexpected request"); },
    navigator: {onLine: true},
    sessionStorage: {getItem: () => null, removeItem: () => {}, setItem: () => {}},
    structuredClone,
    window,
  });
  vm.runInContext(
    fs.readFileSync("bhf_web/static/model-settings.js", "utf8"),
    context,
  );
  return {api: window.BHFModelSettings, events};
}


test("AI passage summary preference defaults off and persists with model settings", async () => {
  const records = new Map();
  const first = loadModelSettings(records);
  await first.api.ready();

  assert.equal(await first.api.isAiPresentationEnabled(), false);
  await first.api.setAiPresentationEnabled(true);
  assert.equal(records.get("model-settings").aiPresentationEnabled, true);
  assert.equal(first.events.at(-1).type, "bhf:ai-presentation-setting-changed");

  const reloaded = loadModelSettings(records);
  await reloaded.api.ready();
  assert.equal(await reloaded.api.isAiPresentationEnabled(), true);
});


test("legacy deployment setting is only a default for users without a saved preference", async () => {
  const records = new Map();
  const first = loadModelSettings(records, {presentationDefaultEnabled: true});
  await first.api.ready();
  assert.equal(await first.api.isAiPresentationEnabled(), true);

  await first.api.setAiPresentationEnabled(false);
  const reloaded = loadModelSettings(records, {presentationDefaultEnabled: true});
  await reloaded.api.ready();
  assert.equal(await reloaded.api.isAiPresentationEnabled(), false);
});
