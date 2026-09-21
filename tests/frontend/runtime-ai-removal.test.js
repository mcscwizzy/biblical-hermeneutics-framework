const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

function read(path) {
  return fs.readFileSync(path, "utf8");
}

test("browser deterministic search has no runtime provider state or fallback", () => {
  const source = read("bhf_web/static/htmx-search.js")
    + read("bhf_web/static/maps/MapPanelSearch.js");

  assert.equal(source.includes("BHFModelSettings"), false);
  assert.equal(source.includes("X-BHF-OpenRouter-Key"), false);
  assert.equal(source.includes("/api/bible/search/fallback"), false);
});

test("browser companion context has no provider presentation request", () => {
  const source = read("bhf_web/static/companion-context.js")
    + read("bhf_web/static/companion-context-controller.js");

  assert.equal(source.includes("ai_profile"), false);
  assert.equal(source.includes("/api/study/presentation"), false);
  assert.equal(source.includes("BHFModelSettings"), false);
});

test("service worker excludes deleted runtime AI endpoints and asset", () => {
  const source = read("bhf_web/static/sw.js");

  assert.equal(source.includes("/api/llm/health"), false);
  assert.equal(source.includes("/api/study/presentation"), false);
  assert.equal(source.includes("/api/bible/search/fallback"), false);
  assert.equal(source.includes("/static/model-settings.js"), false);
});

test("reader controller has no internal conversational submit surface", () => {
  const source = read("bhf_web/static/htmx-lite.js")
    + read("bhf_web/static/api/http.js")
    + read("bhf_web/static/api/backend-routing.js");

  assert.equal(source.includes("BHFModelSettings"), false);
  assert.equal(source.includes("/ask"), false);
  assert.equal(source.includes("/api/study/presentation"), false);
  assert.equal(source.includes("presentation: \"ai\""), false);
});
