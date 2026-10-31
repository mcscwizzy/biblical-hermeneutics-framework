const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const template = fs.readFileSync(
  path.resolve(__dirname, "../../bhf_web/templates/index.html"),
  "utf8",
);
const commentary = fs.readFileSync(
  path.resolve(__dirname, "../../bhf_web/static/commentary.js"),
  "utf8",
);
const companionStyles = fs.readFileSync(
  path.resolve(__dirname, "../../bhf_web/static/styles/companion.css"),
  "utf8",
);


function sectionWithAttribute(source, attribute) {
  const opening = new RegExp(`<section\\b[^>]*${attribute}[^>]*>`, "i").exec(source);
  assert.ok(opening, `expected a section with ${attribute}`);
  const start = opening.index;
  const tags = /<\/?section\b[^>]*>/gi;
  tags.lastIndex = start;
  let depth = 0;
  let match;
  while ((match = tags.exec(source))) {
    if (/^<\//.test(match[0])) depth -= 1;
    else depth += 1;
    if (depth === 0) return source.slice(start, tags.lastIndex);
  }
  assert.fail(`expected a closing section for ${attribute}`);
}


test("Study Companion puts personal actions and Ask BHF before its reserved Tyndale slot", () => {
  const overview = sectionWithAttribute(template, "data-companion-overview");
  const actions = overview.indexOf("companion-overview-actions");
  const ask = overview.indexOf("companion-ask-card");
  const tyndaleSlot = overview.indexOf("data-companion-tyndale-card-slot");
  const deeper = overview.indexOf("data-companion-dig-deeper");

  assert.ok(actions >= 0 && actions < ask);
  assert.ok(ask < tyndaleSlot && tyndaleSlot < deeper);
  assert.match(overview, /data-companion-tyndale-card-slot[^>]*aria-label="Tyndale passage notes"/);
  assert.match(overview, /data-ask-bhf/);
  assert.equal([...overview.matchAll(/data-testid="companion-narrative-explorer"/g)].length, 1);
  assert.doesNotMatch(overview.slice(actions, ask), /data-testid="companion-narrative-explorer"/);
});


test("the Tyndale card exposes a named heading, live status, and full workspace action", () => {
  assert.match(commentary, /title\.textContent = "Tyndale Study Notes"/);
  assert.match(commentary, /card\.setAttribute\("aria-labelledby", "companion-tyndale-title"\)/);
  assert.match(commentary, /status\.setAttribute\("role", "status"\)/);
  assert.match(commentary, /status\.setAttribute\("aria-live", "polite"\)/);
  assert.match(commentary, /button\.textContent = "Open full Tyndale workspace"/);
  assert.match(commentary, /openWorkspaceTab\?\.\("commentary"\)/);
});


test("Tyndale card styles wrap note text and keep native disclosures free of nested scrolling", () => {
  const cardRule = /\.companion-tyndale-card\s*\{([^}]*)\}/.exec(companionStyles);
  assert.ok(cardRule, "expected a first-class Tyndale card rule");
  assert.match(cardRule[1], /min-width:\s*0/);
  assert.match(cardRule[1], /overflow-wrap:\s*anywhere/);
  assert.doesNotMatch(cardRule[1], /overflow-y\s*:/);
  assert.match(companionStyles, /\.tyndale-note-details\s+summary[\s\S]*?min-height:\s*44px/);
  assert.match(companionStyles, /@media\s*\(max-width:\s*680px\)[\s\S]*?\.companion-tyndale-card/);
});


test("Dig Deeper keeps one prominent Narrative Explorer and Places & Locations entry", () => {
  const deeper = sectionWithAttribute(template, "data-companion-dig-deeper");
  const narrative = deeper.indexOf('data-testid="companion-narrative-explorer"');
  const places = deeper.indexOf('data-companion-resource="places_locations"');
  const resources = deeper.indexOf("data-companion-recommended");
  const remainingResources = deeper.indexOf("data-companion-deeper");
  const advanced = deeper.indexOf("companion-advanced-links");

  assert.ok(narrative >= 0 && narrative < places);
  assert.ok(places < resources);
  assert.ok(resources < remainingResources && remainingResources < advanced);
  assert.equal([...deeper.matchAll(/data-companion-resource="places_locations"/g)].length, 1);
  assert.match(deeper, /<strong>Places &amp; Locations<\/strong>/);
  assert.match(deeper, /Explore biblical places, geography, maps, and journeys connected to this passage\./);
  assert.doesNotMatch(deeper, /Did You Know\?|data-companion-locations-section|data-companion-discoveries-section|data-companion-land-section|data-companion-entities-section|People &amp; Places/);
  assert.match(deeper, /\{% if runtime_config\.narrativeExplorerEnabled %\}[\s\S]*?data-testid="companion-narrative-explorer"[\s\S]*?\{% endif %\}/);
});
