const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");


function node() {
  return {
    dataset: {},
    hidden: false,
    inert: false,
    classList: {add() {}, remove() {}, toggle() {}},
    addEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    setAttribute() {},
    removeAttribute() {},
  };
}


function loadCompanion(options = {}) {
  const listeners = new Map();
  const panel = node();
  const shell = node();
  const overview = node();
  panel.querySelector = (selector) => ({
    ".study-companion": shell,
    "[data-companion-overview]": overview,
  })[selector] || null;
  const document = {
    body: node(),
    addEventListener(type, callback) { listeners.set(type, callback); },
    querySelector(selector) { return selector === "[data-study-companion]" ? panel : null; },
  };
  const routerCalls = [];
  let selectionListener = null;
  let contextOptions = null;
  const window = {
    BHFRuntimeConfig: {narrativeExplorerEnabled: true},
    matchMedia: () => ({matches: false}),
    addEventListener() {},
    requestAnimationFrame(callback) { callback(); },
    BHFStudySelection: {
      subscribe(callback) { selectionListener = callback; },
      getState() { return options.selection || null; },
    },
    BHFMaps: options.openMapPanel
      ? {openMapPanel: options.openMapPanel}
      : undefined,
    BHFStudyRecommendations: {
      rank() { return {reason: "", recommended: [], deeper: [], all: []}; },
    },
    BHFResourceRouter: {
      create() {
        return {
          open(...args) { routerCalls.push(args); return Promise.resolve(true); },
          close() {},
          getNarrativeTrail() { return null; },
        };
      },
    },
    BHFCompanionContextController: {
      create(options) {
        contextOptions = options;
        return {
          setSelection() { return {changed: true}; },
          getRecord() { return {context: null}; },
          invalidate() { return true; },
        };
      },
    },
    BHFCompanionHistory: {
      create() {
        return {
          initialize() {},
          current() { return {resource: null}; },
          push() {},
          replace() {},
          backFromResource() { return true; },
        };
      },
    },
  };
  const context = vm.createContext({window, document, console, setTimeout, clearTimeout, Promise});
  vm.runInContext(fs.readFileSync("bhf_web/static/study-companion.js", "utf8"), context);
  listeners.get("DOMContentLoaded")();
  return {
    companion: window.BHFStudyCompanion,
    contextOptions,
    select(next) { selectionListener(next); },
    routerCalls,
  };
}


test("reader selection changes leave Narrative Explorer passage navigation to its trail", async () => {
  const fixture = loadCompanion();
  await fixture.companion.openResource("narrative_explorer");
  assert.equal(fixture.routerCalls.length, 1);

  fixture.select({book: "Acts", chapter: 7, reference: "Acts 7:19", hasPassageSelection: true});
  assert.equal(fixture.routerCalls.length, 1);

  fixture.contextOptions.onReady({});
  fixture.contextOptions.onError("unavailable");
  assert.equal(fixture.routerCalls.length, 1);
});


test("other passage-bound resources still refresh when the reader selection changes", async () => {
  const fixture = loadCompanion();
  await fixture.companion.openResource("archaeology");
  assert.equal(fixture.routerCalls.length, 1);

  fixture.select({book: "Acts", chapter: 7, reference: "Acts 7:19", hasPassageSelection: true});
  assert.equal(fixture.routerCalls.length, 2);
  assert.equal(fixture.routerCalls[1][0], "archaeology");
});


test("Companion returns requested Maps focus acknowledgment without changing legacy opens", async () => {
  const calls = [];
  const acknowledgment = {
    status: "not_found",
    requestedKind: "place",
    requestedId: "openbible-a012705",
    selectedKind: null,
    selectedId: null,
    reason: "requested_item_not_found",
  };
  const fixture = loadCompanion({
    selection: {book: "Acts", chapter: 7, startVerse: 19, endVerse: 19},
    openMapPanel: async (context) => {
      calls.push(context);
      return acknowledgment;
    },
  });

  const result = await fixture.companion.openResource("maps", {
    mapFocus: {kind: "place", targetId: "openbible-a012705", acknowledgeFocus: true},
  });
  const legacy = await fixture.companion.openResource("maps", {
    mapFocus: {kind: "place", targetId: "openbible-a012705"},
  });

  assert.deepEqual(result, acknowledgment);
  assert.equal(calls[0].focusPlaceId, "openbible-a012705");
  assert.equal(calls[0].focusKind, "place");
  assert.equal(calls[0].focusTargetId, "openbible-a012705");
  assert.equal(calls[0].acknowledgeFocus, true);
  assert.equal(legacy, undefined);
  assert.equal(calls[1].acknowledgeFocus, undefined);
});


test("a requested map focus reports unavailable while the MapPanel module is loading", async () => {
  const fixture = loadCompanion({
    selection: {book: "Joshua", chapter: 1, startVerse: 4, endVerse: 4},
  });

  const result = await fixture.companion.openResource("maps", {
    mapFocus: {kind: "place", targetId: "negeb", acknowledgeFocus: true},
  });

  assert.equal(result.status, "unavailable");
  assert.equal(result.requestedKind, "place");
  assert.equal(result.requestedId, "negeb");
  assert.equal(result.reason, "map_panel_not_ready");
});
