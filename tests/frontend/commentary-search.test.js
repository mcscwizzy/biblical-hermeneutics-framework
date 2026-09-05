const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function loadSearch() {
  const context = vm.createContext({
    window: {},
    document: {},
    escapeHtml: (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;"),
  });
  vm.runInContext(fs.readFileSync("bhf_web/static/htmx-search.js", "utf8"), context);
  return context;
}

test("commentary search result renders availability and chapter navigation", () => {
  const search = loadSearch();
  const html = search.renderCommentarySearchResult({
    book: "Genesis",
    chapter: 13,
    availability: "THIN",
    commentary: "A concise contextual observation.",
    evidence_count: 1,
    verse_references: ["Genesis 13:5-12"],
    section_kinds: ["chapter_overview"],
  });

  assert.match(html, /Genesis 13/);
  assert.match(html, /Limited context/);
  assert.match(html, /Genesis 13:5-12/);
  assert.match(html, /data-commentary-search-action="open-chapter"/);
});
