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
    assert.equal(routing.resolveUrl("/api/bible/search", runtime), "/api/bible/search");
    assert.equal(routing.resolveUrl("/api/study/companion-context", runtime), "/api/study/companion-context");
  }
});

test("an explicit deployment error blocks same-origin routing", () => {
  const runtime = {
    backendMode: "same-origin",
    apiBaseUrl: "",
    backendConfigError: "A durable backend is required.",
  };

  assert.equal(routing.configurationError(runtime), runtime.backendConfigError);
  assert.throws(
    () => routing.resolveUrl("/api/bible/search", runtime),
    {name: "BHFBackendConfigurationError", message: routing.CONFIGURATION_MESSAGE},
  );
});

test("the full async flow and API calls use the remote backend", () => {
  for (const path of [
    "/api/health",
    "/api/study/actions",
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
      () => routing.resolveUrl("/api/study/actions", runtime),
      {name: "BHFBackendConfigurationError", message: routing.CONFIGURATION_MESSAGE},
    );
  }
});
