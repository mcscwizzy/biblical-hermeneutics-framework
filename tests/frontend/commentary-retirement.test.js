const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

function read(path) {
  return fs.readFileSync(path, "utf8");
}

test("reader shell keeps Tyndale, personal study, translations, and optional Explorer controls", () => {
  const template = read("bhf_web/templates/index.html");

  assert.doesNotMatch(template, /BHF Context|data-bhf-commentary|bhf-commentary-card\.js/);
  assert.match(template, /data-commentary-panel aria-label="Tyndale Study Notes"/);
  assert.match(template, /data-companion-resource="translation_comparison"/);
  assert.match(template, /data-workspace-tab="notes"/);
  assert.match(template, /data-workspace-tab="highlights"/);
  assert.match(template, /data-companion-resource-label="Explore the Narrative"/);
  assert.match(template, /if runtime_config\.narrativeExplorerEnabled/);
});

test("browser API and service worker keep Tyndale caching and drop generated Commentary caching", () => {
  const api = read("bhf_web/static/api/http.js");
  const worker = read("bhf_web/static/sw.js");
  const offline = read("bhf_web/offline.py");

  for (const source of [api, worker, offline]) {
    assert.doesNotMatch(source, /\/api\/bhf-commentary\/|bhf-commentary-card\.js/);
  }
  assert.doesNotMatch(api, /commentaryRelease|isCurrentCommentaryPayload/);
  assert.match(api, /"\/api\/commentary\/"/);
  assert.match(worker, /"\/api\/commentary\/"/);
  assert.match(offline, /"\/api\/commentary\/"/);
});

test("translation comparison fallback no longer targets the retired panel", () => {
  const source = read("bhf_web/static/htmx-lite.js");

  assert.match(source, /openResource\("translation_comparison"/);
  assert.doesNotMatch(source, /data-bhf-commentary-status/);
});
