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


function loadCompanion() {
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
    },
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
