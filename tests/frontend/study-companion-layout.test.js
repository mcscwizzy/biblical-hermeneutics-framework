const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const template = fs.readFileSync(
  path.resolve(__dirname, "../../bhf_web/templates/index.html"),
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
  assert.match(overview, /data-ask-bhf/);
  assert.equal([...overview.matchAll(/data-testid="companion-narrative-explorer"/g)].length, 1);
  assert.doesNotMatch(overview.slice(actions, ask), /data-testid="companion-narrative-explorer"/);
});


test("Dig Deeper groups the gated Narrative Explorer, passage research, and advanced workspaces", () => {
  const deeper = sectionWithAttribute(template, "data-companion-dig-deeper");
  const narrative = deeper.indexOf('data-testid="companion-narrative-explorer"');
  const locations = deeper.indexOf("data-companion-locations-section");
  const discoveries = deeper.indexOf("data-companion-discoveries-section");
  const land = deeper.indexOf("data-companion-land-section");
  const resources = deeper.indexOf("data-companion-recommended");
  const remainingResources = deeper.indexOf("data-companion-deeper");
  const entities = deeper.indexOf("data-companion-entities-section");
  const advanced = deeper.indexOf("companion-advanced-links");

  assert.ok(narrative >= 0 && narrative < locations);
  assert.ok(locations < discoveries && discoveries < land);
  assert.ok(land < resources && resources < entities);
  assert.ok(resources < remainingResources && remainingResources < entities && entities < advanced);
  assert.match(deeper, /\{% if runtime_config\.narrativeExplorerEnabled %\}[\s\S]*?data-testid="companion-narrative-explorer"[\s\S]*?\{% endif %\}/);
});
