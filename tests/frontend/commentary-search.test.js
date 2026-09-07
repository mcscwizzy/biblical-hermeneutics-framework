const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
test("reader Scripture search does not invoke or render BHF commentary search", () => {
  const source = fs.readFileSync("bhf_web/static/htmx-search.js", "utf8");

  assert.match(source, /\/api\/bible\/search\?/);
  assert.match(source, /runBibleSearchFallback/);
  assert.doesNotMatch(source, /\/api\/bhf-commentary\/search/);
  assert.doesNotMatch(source, /loadCommentarySearch/);
  assert.doesNotMatch(source, /commentary-search/);
});
