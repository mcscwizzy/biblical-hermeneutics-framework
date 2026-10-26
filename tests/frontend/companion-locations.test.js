const test = require("node:test");
const assert = require("node:assert/strict");

const locations = require("../../bhf_web/static/companion-locations.js");


class FakeElement {
  constructor(tagName, ownerDocument) {
    this.tagName = String(tagName).toUpperCase();
    this.ownerDocument = ownerDocument;
    this.children = [];
    this.className = "";
    this.dataset = {};
    this.hidden = false;
    this.disabled = false;
    this.textContent = "";
    this.type = "";
    this.attributes = {};
    this.listeners = {};
    this.classList = {add: (...names) => { this.className = [...new Set([...this.className.split(/\s+/).filter(Boolean), ...names])].join(" "); }};
  }

  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(type, listener) { (this.listeners[type] ||= []).push(listener); }
  focus() { this.focused = true; }
  async click() {
    if (typeof this.onclick === "function") await this.onclick({target: this, currentTarget: this});
    for (const listener of this.listeners.click || []) await listener({target: this, currentTarget: this});
  }
}


function fixturePanel() {
  const document = {createElement: (tagName) => new FakeElement(tagName, document)};
  const selectors = {
    "[data-companion-locations-section]": new FakeElement("section", document),
    "[data-companion-locations-list]": new FakeElement("ol", document),
    "[data-companion-locations-status]": new FakeElement("p", document),
    "[data-companion-locations-more]": new FakeElement("button", document),
  };
  selectors["[data-companion-locations-section]"].append(
    selectors["[data-companion-locations-list]"],
    selectors["[data-companion-locations-status]"],
    selectors["[data-companion-locations-more]"],
  );
  return {document, selectors, panel: {querySelector: (selector) => selectors[selector] || null}};
}


function mapItem(id, title = `Place ${id}`) {
  return {
    id,
    origin: "maps",
    title,
    references: ["Acts 27:2"],
    relationship: "directly_named",
    map_focus_id: id,
    map_confidence: "likely",
    provenance: {name: "OpenBible map catalog"},
  };
}


function cklItem(id, title) {
  return {
    id,
    origin: "ckl",
    title,
    reference: "Acts 27:8",
    references: ["Acts 27:8"],
    review_status: "unreviewed",
    content_status: "draft",
    provenance: {name: "Canonical Knowledge Library", sources: ["Acts 27"]},
    canonical_href: `/api/canonical/objects/${id}`,
  };
}


function findAll(node, predicate, found = []) {
  if (predicate(node)) found.push(node);
  for (const child of node.children || []) findAll(child, predicate, found);
  return found;
}


test("Locations renders independent items with native accessible actions and exact map focus", async () => {
  const {panel, selectors} = fixturePanel();
  const opened = [];
  locations.render(panel, {
    reference: "Acts 27",
    items: [mapItem("openbible-exact-id", "Myra")],
    total: 1,
    page_size: 5,
    next_cursor: null,
  }, {
    selection: {book: "Acts", chapter: 27},
    openMap: async (id) => { opened.push(id); return {status: "selected", selectedId: id}; },
  });

  const section = selectors["[data-companion-locations-section]"];
  const action = findAll(section, (item) => item.dataset.locationAction === "open-map")[0];
  assert.equal(section.hidden, false);
  assert.equal(action.tagName, "BUTTON");
  assert.equal(action.type, "button");
  assert.equal(action.dataset.locationId, "openbible-exact-id");
  await action.click();
  assert.deepEqual(opened, ["openbible-exact-id"]);
  assert.match(selectors["[data-companion-locations-status]"].textContent, /Maps focused on Myra/);
});


test("View All loads bounded pages, preserves duplicate names with different IDs, and keeps keyboard focus", async () => {
  const {panel, selectors} = fixturePanel();
  const requests = [];
  const initial = Array.from({length: 5}, (_value, index) => mapItem(`map-${index}`, index === 0 ? "Twin" : `Place ${index}`));
  const pageOne = Array.from({length: 25}, (_value, index) => mapItem(`map-${index + 5}`, index === 0 ? "Twin" : `Place ${index + 5}`));
  const pageTwo = Array.from({length: 25}, (_value, index) => mapItem(`map-${index + 30}`, `Place ${index + 30}`));
  const pages = {
    "5": {items: pageOne, total: 55, next_cursor: "30"},
    "30": {items: pageTwo, total: 55, next_cursor: null},
  };
  locations.render(panel, {
    reference: "Joshua 15", items: initial, total: 55, page_size: 5, next_cursor: "5",
  }, {
    selection: {book: "Joshua", chapter: 15},
    loadPage: async ({cursor, limit}) => {
      requests.push({cursor, limit});
      return pages[cursor];
    },
  });

  const more = selectors["[data-companion-locations-more]"];
  assert.equal(more.tagName, "BUTTON");
  assert.equal(more.type, "button");
  await more.click();

  const list = selectors["[data-companion-locations-list]"];
  assert.deepEqual(requests, [{cursor: "5", limit: 25}, {cursor: "30", limit: 25}]);
  assert.equal(list.children.length, 55);
  assert.equal(more.hidden, true);
  assert.equal(selectors["[data-companion-locations-status]"].focused, true);
  const labels = findAll(list, (item) => item.tagName === "H4").filter((item) => item.textContent === "Twin");
  assert.equal(labels.length, 2);
});


test("CKL-only places open CKL details and do not acquire a map action", async () => {
  const {panel, selectors} = fixturePanel();
  const opened = [];
  locations.render(panel, {
    reference: "Acts 27", items: [cklItem("ckl-lasea", "Lasea")], total: 1, page_size: 5,
  }, {
    selection: {book: "Acts", chapter: 27},
    openCkl: async (id) => opened.push(id),
  });

  const section = selectors["[data-companion-locations-section]"];
  assert.equal(findAll(section, (item) => item.dataset.locationAction === "open-map").length, 0);
  const action = findAll(section, (item) => item.dataset.locationAction === "open-ckl")[0];
  assert.equal(action.dataset.locationId, "ckl-lasea");
  await action.click();
  assert.deepEqual(opened, ["ckl-lasea"]);
});


test("disputed map identification is labeled as catalog uncertainty", () => {
  const {panel, selectors} = fixturePanel();
  locations.render(panel, {
    reference: "Genesis 14",
    items: [{
      ...mapItem("uncertain-place", "Possible Site"),
      modern_location: "Possible modern area",
      map_confidence: "possible",
      identification_uncertainty: "The map catalog rates this identification as possible; that rating does not establish historical or archaeological certainty.",
    }],
    total: 1,
  });

  const text = findAll(selectors["[data-companion-locations-list]"], (item) => item.tagName === "P")
    .map((item) => item.textContent).join(" ");
  assert.match(text, /Possible modern location in the map catalog/);
  assert.match(text, /does not establish historical or archaeological certainty/);
});


test("the Locations section is absent when no eligible physical geography is available", () => {
  const {panel, selectors} = fixturePanel();
  const state = locations.render(panel, {reference: "Psalm 82", items: [], total: 0});

  assert.equal(state, null);
  assert.equal(selectors["[data-companion-locations-section]"].hidden, true);
  assert.equal(selectors["[data-companion-locations-list]"].children.length, 0);
});


test("offline leaves the initial cached locations visible and disables View All with an explanation", () => {
  const {panel, selectors} = fixturePanel();
  locations.render(panel, {
    reference: "Genesis 14", items: Array.from({length: 5}, (_value, index) => mapItem(String(index))),
    total: 24, page_size: 5, next_cursor: "5",
  }, {offline: true, selection: {book: "Genesis", chapter: 14}});

  assert.equal(selectors["[data-companion-locations-list]"].children.length, 5);
  assert.equal(selectors["[data-companion-locations-more]"].disabled, true);
  assert.match(selectors["[data-companion-locations-status]"].textContent, /connect|online/i);
});


test("changing chapters replaces old locations and builds a chapter-scoped paging URL", () => {
  const {panel, selectors} = fixturePanel();
  locations.render(panel, {
    reference: "Acts 27", items: [mapItem("acts-place")], total: 2, page_size: 1, next_cursor: "1",
  }, {selection: {book: "Acts", chapter: 27}});
  locations.render(panel, {
    reference: "Jonah 1", items: [mapItem("jonah-place")], total: 1, page_size: 5, next_cursor: null,
  }, {selection: {book: "Jonah", chapter: 1}});

  const names = findAll(selectors["[data-companion-locations-list]"], (item) => item.tagName === "H4")
    .map((item) => item.textContent);
  assert.deepEqual(names, ["Place jonah-place"]);
  assert.match(locations.urlFor({book: "Jonah", chapter: 1, startVerse: 2}, "5"), /book=Jonah/);
  assert.match(locations.urlFor({book: "Jonah", chapter: 1, startVerse: 2}, "5"), /verse_start=2/);
  assert.match(locations.urlFor({book: "Jonah", chapter: 1, startVerse: 2}, "5"), /cursor=5/);
});
