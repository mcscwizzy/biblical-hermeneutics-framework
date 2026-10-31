const test = require("node:test");
const assert = require("node:assert/strict");

const geography = require("../../bhf_web/static/companion-places-locations.js");


class FakeElement {
  constructor(tagName, ownerDocument) {
    this.tagName = String(tagName).toUpperCase();
    this.ownerDocument = ownerDocument;
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.className = "";
    this.textContent = "";
    this.hidden = false;
    this.classList = {add: (...names) => {
      this.className = [...new Set([...this.className.split(/\s+/).filter(Boolean), ...names])].join(" ");
    }};
  }

  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener() {}
  querySelector(selector) {
    const match = /^\[data-([a-z0-9-]+)\]$/.exec(selector);
    if (!match) return null;
    const key = match[1].replace(/-([a-z])/g, (_all, letter) => letter.toUpperCase());
    return findAll(this, (node) => Object.hasOwn(node.dataset || {}, key))[0] || null;
  }
}


function fixtureDocument() {
  const document = {};
  document.createElement = (tagName) => new FakeElement(tagName, document);
  return document;
}


function findAll(node, predicate, found = []) {
  if (predicate(node)) found.push(node);
  for (const child of node.children || []) findAll(child, predicate, found);
  return found;
}


function context(overrides = {}) {
  return {
    reference: "Acts 27:8",
    offline: false,
    locations: {reference: "Acts 27:8", items: [], total: 0, next_cursor: null},
    entities: {places: []},
    summaries: {maps: {places: []}},
    subsystems: {locations: {status: "available"}, maps: {status: "available"}, canonical: {status: "available"}},
    presentation_packet: {cards: []},
    ...overrides,
  };
}


test("composite view keeps Maps locations and CKL places distinct and deduplicates only exact CKL IDs", () => {
  const document = fixtureDocument();
  const locationsRendered = [];
  const walkRendered = [];
  const currentContext = context({
    locations: {
      reference: "Acts 27:8",
      items: [
        {id: "openbible-jerusalem", origin: "maps", title: "Jerusalem"},
        {id: "jerusalem", origin: "ckl", title: "Jerusalem"},
      ],
      total: 2,
      next_cursor: null,
    },
    summaries: {
      maps: {places: [{id: "openbible-jerusalem", title: "Jerusalem", type: "place", relationship: "directly_named"}]},
    },
    entities: {places: [
      {id: "jerusalem", title: "Jerusalem", type: "place", relationship: "direct Scripture anchor"},
      {id: "ckl-second-jerusalem", title: "Jerusalem", type: "place", relationship: "direct Scripture anchor"},
      {id: "ckl-second-jerusalem", title: "Jerusalem", type: "place", relationship: "direct Scripture anchor"},
      {id: "openbible-jerusalem", title: "Jerusalem", type: "place", relationship: "directly_named"},
    ]},
  });

  const body = geography.render(currentContext, {
    document,
    selection: {book: "Acts", chapter: 27, startVerse: 8, endVerse: 8},
    locationRenderer: {
      render(target, payload, options) { locationsRendered.push({target, payload, options}); },
    },
    renderWalkTheLand(target, value) { walkRendered.push({target, value}); },
  });

  const sections = findAll(body, (node) => node.tagName === "SECTION");
  assert.deepEqual(sections.map((section) => section.dataset.geographySection), [
    "locations", "biblical-places", "walk-the-land",
  ]);
  const biblicalPlaces = findAll(body, (node) => node.dataset.biblicalPlaceList === "")[0];
  const recordIds = findAll(biblicalPlaces, (node) => node.dataset.canonicalId)
    .map((node) => node.dataset.canonicalId);
  assert.deepEqual(recordIds, ["ckl-second-jerusalem"]);
  assert.equal(locationsRendered[0].payload, currentContext.locations);
  assert.deepEqual(locationsRendered[0].options.selection, {
    book: "Acts", chapter: 27, startVerse: 8, endVerse: 8,
  });
  assert.equal(walkRendered.length, 1);
  assert.equal(walkRendered[0].value, currentContext);
});


test("a later exact CKL location removes its duplicate Biblical Places row without matching by name", () => {
  const document = fixtureDocument();
  let locationOptions;
  const body = geography.render(context({
    locations: {
      reference: "Acts 27:8",
      items: [{id: "maps-jerusalem", origin: "maps", title: "Jerusalem"}],
      total: 2,
      next_cursor: "next",
    },
    entities: {places: [
      {id: "ckl-jerusalem", title: "Jerusalem", type: "place", relationship: "direct Scripture anchor"},
      {id: "ckl-other-jerusalem", title: "Jerusalem", type: "place", relationship: "direct Scripture anchor"},
    ]},
  }), {
    document,
    locationRenderer: {render(_target, _payload, options) { locationOptions = options; }},
  });

  const placeList = findAll(body, (node) => node.dataset.biblicalPlaceList === "")[0];
  assert.deepEqual(placeList.children.map((node) => node.dataset.canonicalId), ["ckl-jerusalem", "ckl-other-jerusalem"]);
  locationOptions.onChange({items: [
    {id: "maps-jerusalem", origin: "maps", title: "Jerusalem"},
    {id: "ckl-jerusalem", origin: "ckl", title: "Jerusalem"},
  ]});
  assert.deepEqual(placeList.children.map((node) => node.dataset.canonicalId), ["ckl-other-jerusalem"]);
});


test("offline, partial, and empty geography states remain visible", () => {
  const document = fixtureDocument();
  const emptyView = geography.render(context(), {document});
  const state = findAll(emptyView, (node) => node.dataset.geographyStatus === "")[0];
  const emptyMessages = findAll(emptyView, (node) => node.dataset.geographyEmpty === "")
    .map((node) => node.textContent);

  assert.equal(state.textContent, "");
  assert.match(emptyMessages.join(" "), /No source-grounded locations/);
  assert.match(emptyMessages.join(" "), /No CKL place records/);
  assert.match(emptyMessages.join(" "), /No source-grounded journeys/);

  const offlineView = geography.render(context({offline: true}), {document});
  const offline = findAll(offlineView, (node) => node.dataset.geographyStatus === "")[0];
  assert.match(offline.textContent, /offline/i);
  assert.match(offline.textContent, /available/i);

  const priorNavigator = Object.getOwnPropertyDescriptor(globalThis, "navigator");
  Object.defineProperty(globalThis, "navigator", {configurable: true, value: {onLine: false}});
  try {
    const browserOfflineView = geography.render(context(), {document});
    const browserOffline = findAll(browserOfflineView, (node) => node.dataset.geographyStatus === "")[0];
    assert.equal(browserOffline.dataset.geographyState, "offline");
  } finally {
    Object.defineProperty(globalThis, "navigator", priorNavigator);
  }

  const partialView = geography.render(context({
    subsystems: {locations: {status: "unknown"}, maps: {status: "available"}, canonical: {status: "available"}},
  }), {document});
  const partial = findAll(partialView, (node) => node.dataset.geographyStatus === "")[0];
  assert.match(partial.textContent, /partial/i);
});
