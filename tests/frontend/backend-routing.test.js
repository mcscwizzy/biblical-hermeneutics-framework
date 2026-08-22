const test = require("node:test");
const assert = require("node:assert/strict");

const routing = require("../../bhf_web/static/api/backend-routing.js");

const sameOrigin = {backendMode: "same-origin", apiBaseUrl: ""};
const sameOriginPwa = {mode: "pwa", backendMode: "same-origin", apiBaseUrl: ""};
const remote = {
  mode: "pwa",
  backendMode: "remote",
  apiBaseUrl: "https://backend.example.com",
};

test("same-origin and NAS PWA backend requests stay relative", () => {
  for (const runtime of [
    sameOrigin,
    sameOriginPwa,
    {mode: "pwa", backendMode: "same-origin", apiBaseUrl: "https://ignored.example"},
    {mode: "pwa", apiBaseUrl: "https://not-inferred.example"},
  ]) {
    assert.equal(routing.resolveUrl("/ask/jobs", runtime), "/ask/jobs");
    assert.equal(routing.resolveUrl("/ask/status/abc", runtime), "/ask/status/abc");
  }
});

test("the full async flow and API calls use the remote backend", () => {
  for (const path of [
    "/ask/jobs",
    "/ask/status/abc",
    "/ask/result/abc",
    "/api/health",
    "/api/bible/search/fallback/jobs",
    "/api/bible/search/fallback/status/abc",
    "/api/bible/search/fallback/result/abc",
  ]) {
    assert.equal(routing.resolveUrl(path, remote), `https://backend.example.com${path}`);
  }
});

test("absolute URLs and frontend assets are never rewritten", () => {
  for (const url of [
    "https://cdn.example.com/file.js",
    "//cdn.example.com/file.js",
    "data:text/plain,hello",
    "blob:https://frontend.example.com/id",
    "/static/api/http.js",
    "/manifest.webmanifest",
    "/sw.js",
    "/icons/icon.svg",
  ]) {
    assert.equal(routing.resolveUrl(url, remote), url);
  }
});

test("remote mode without a valid API URL refuses backend requests", () => {
  for (const apiBaseUrl of ["", "not-a-url", "ftp://backend.example.com"]) {
    const runtime = {backendMode: "remote", apiBaseUrl};
    assert.equal(routing.configurationError(runtime), routing.CONFIGURATION_MESSAGE);
    assert.throws(
      () => routing.resolveUrl("/ask/jobs", runtime),
      {name: "BHFBackendConfigurationError", message: routing.CONFIGURATION_MESSAGE},
    );
  }
});
