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
  const historyCalls = [];
  const discoveryRenders = [];
  const projectionCalls = [];
  let selectionListener = null;
  let contextOptions = null;
  let resourceRouterOptions = null;
  let narrativeView = {kind: "overview"};
  const window = {
    BHFRuntimeConfig: {narrativeExplorerEnabled: options.narrativeExplorerEnabled !== false},
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
    BHFCompanionContext: {
      requestKey(value) {
        return [value?.book, value?.chapter, value?.startVerse || 0, value?.endVerse || 0].join("|");
      },
    },
    BHFCompanionDiscoveries: {
      render(_panel, context, renderOptions) {
        discoveryRenders.push({context, renderOptions});
      },
    },
    BHFNarrativeExplorer: {
      urlFor(value) {
        return `/api/narrative-explorer/v1/passages/${value?.book}/${value?.chapter}`
          + (value?.startVerse ? `?verse_start=${value.startVerse}&verse_end=${value.endVerse || value.startVerse}` : "");
      },
      ...(options.narrativeExplorer || {
        load(selection, requestOptions) {
          projectionCalls.push({selection, requestOptions});
          return Promise.resolve(null);
        },
      }),
    },
    BHFResourceRouter: {
      create(routerOptions) {
        resourceRouterOptions = routerOptions;
        return {
          open(...args) {
            routerCalls.push(args);
            if (args[1]?.routeHandoff) {
              if (options.routeHandoffReady === false) return Promise.resolve(false);
              routerOptions.onVerifiedRouteHandoff?.();
              routerOptions.onNarrativeTrailChange?.({originSelection: {reference: "Jonah 1:17"}, nodes: [], activeIndex: 0}, {push: false});
            }
            return Promise.resolve(true);
          },
          close() {},
          getNarrativeTrail() { return null; },
          getNarrativeView() { return narrativeView; },
          cancelPendingRouteHandoff() {},
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
          push(snapshot) { historyCalls.push({kind: "push", snapshot}); },
          replace(snapshot) { historyCalls.push({kind: "replace", snapshot}); },
          backFromResource() { return true; },
        };
      },
    },
  };
  const context = vm.createContext({window, document, console, setTimeout, clearTimeout, Promise, AbortController});
  vm.runInContext(fs.readFileSync("bhf_web/static/study-companion.js", "utf8"), context);
  listeners.get("DOMContentLoaded")();
  return {
    companion: window.BHFStudyCompanion,
    panel,
    contextOptions,
    select(next) { selectionListener(next); },
    routerCalls,
    historyCalls,
    discoveryRenders,
    projectionCalls,
    resourceRouterOptions,
    setNarrativeView(value) { narrativeView = value; },
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

test("Narrative Explorer focused view changes are included in Companion history snapshots", async () => {
  const fixture = loadCompanion();
  const view = {kind: "category", categoryId: "themes_biblical_connections"};
  await fixture.companion.openResource("narrative_explorer");
  fixture.setNarrativeView(view);

  fixture.resourceRouterOptions.onNarrativeViewChange(view, {push: true});

  const historyChange = fixture.historyCalls.at(-1);
  assert.equal(historyChange.kind, "push");
  assert.equal(historyChange.snapshot.resource, "narrative_explorer");
  assert.deepEqual(historyChange.snapshot.narrativeView, view);
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


test("Places & Locations preflights exact Walk the Land records through Narrative Explorer", async () => {
  let resolveProjection;
  const fixture = loadCompanion({
    selection: {
      book: "Jonah",
      chapter: 1,
      startVerse: 17,
      endVerse: 17,
      reference: "Jonah 1:17",
      hasPassageSelection: true,
    },
    narrativeExplorer: {
      load(selection, requestOptions) {
        fixture.projectionCalls.push({selection, requestOptions});
        return new Promise((resolve) => { resolveProjection = resolve; });
      },
    },
  });
  const selection = {
    book: "Jonah",
    chapter: 1,
    startVerse: 17,
    endVerse: 17,
    reference: "Jonah 1:17",
    hasPassageSelection: true,
  };
  fixture.select(selection);
  const context = {
    reference: "Jonah 1:17",
    presentation_packet: {
      cards: [{type: "walk_the_land", evidence_ids: ["jonah-three-days"]}],
    },
    presentation_evidence: [{
      id: "jonah-three-days",
      ckl_record_identity: {object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"},
    }],
  };

  await fixture.companion.openResource("places_locations");
  fixture.resourceRouterOptions.onPlacesLocationsRendered(context, fixture.panel, selection);
  await Promise.resolve();

  assert.equal(fixture.projectionCalls.length, 1);
  assert.equal(fixture.projectionCalls[0].selection.startVerse, 17);
  assert.equal(fixture.projectionCalls[0].selection.endVerse, 17);
  assert.equal(fixture.projectionCalls[0].requestOptions.signal.aborted, false);
  const projection = {
    passage: {reference: "Jonah 1:17"},
    related_passages: {state: "available", query_status: "complete", authored_relationships: [], evidence_backed_bridges: []},
  };
  resolveProjection(projection);
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(fixture.discoveryRenders.at(-1).renderOptions.verifiedProjection, projection);
  assert.equal(fixture.discoveryRenders.at(-1).renderOptions.narrativeExplorerEnabled, true);
});


test("projection preflight aborts and discards a stale chapter response", async () => {
  const pending = [];
  const fixture = loadCompanion({
    narrativeExplorer: {
      load(selection, requestOptions) {
        return new Promise((resolve) => pending.push({selection, signal: requestOptions.signal, resolve}));
      },
    },
  });
  const firstSelection = {book: "Jonah", chapter: 1, startVerse: 17, endVerse: 17, reference: "Jonah 1:17"};
  const secondSelection = {book: "Matthew", chapter: 12, startVerse: 40, endVerse: 40, reference: "Matthew 12:40"};
  const contextFor = (reference, recordId) => ({
    reference,
    presentation_packet: {cards: [{type: "walk_the_land", evidence_ids: [recordId]}]},
    presentation_evidence: [{
      id: recordId,
      ckl_record_identity: {object_id: "jonah", record_kind: "claim", record_id: recordId},
    }],
  });

  await fixture.companion.openResource("places_locations");
  fixture.resourceRouterOptions.onPlacesLocationsRendered(
    contextFor("Jonah 1:17", "jonah-three-days"), fixture.panel, firstSelection,
  );
  await new Promise((resolve) => setImmediate(resolve));
  fixture.select(secondSelection);
  fixture.resourceRouterOptions.onPlacesLocationsRendered(
    contextFor("Matthew 12:40", "matthew-sign-of-jonah"), fixture.panel, secondSelection,
  );
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(pending.length, 2);
  assert.equal(pending[0].signal.aborted, true);
  const staleProjection = {passage: {reference: "Jonah 1:17"}, related_passages: {state: "available", query_status: "complete"}};
  pending[0].resolve(staleProjection);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(fixture.discoveryRenders.some((entry) => entry.renderOptions.verifiedProjection === staleProjection), false);

  const currentProjection = {passage: {reference: "Matthew 12:40"}, related_passages: {state: "available", query_status: "complete"}};
  pending[1].resolve(currentProjection);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(fixture.discoveryRenders.at(-1).renderOptions.verifiedProjection, currentProjection);
});


test("disabled Narrative Explorer does not trigger a route projection request", async () => {
  const fixture = loadCompanion({
    selection: {book: "Jonah", chapter: 1, startVerse: 17, endVerse: 17, reference: "Jonah 1:17"},
    narrativeExplorerEnabled: false,
  });
  const selection = {book: "Jonah", chapter: 1, startVerse: 17, endVerse: 17, reference: "Jonah 1:17"};
  fixture.select(selection);
  const context = {
    reference: "Jonah 1:17",
    presentation_packet: {cards: [{type: "did_you_know", evidence_ids: ["jonah-three-days"]}]},
    presentation_evidence: [{
      id: "jonah-three-days",
      ckl_record_identity: {object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"},
    }],
  };
  await fixture.companion.openResource("places_locations");
  fixture.resourceRouterOptions.onPlacesLocationsRendered(context, fixture.panel, selection);
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(fixture.projectionCalls.length, 0);
  assert.equal(fixture.discoveryRenders.at(-1).renderOptions.narrativeExplorerEnabled, false);
});


test("Did You Know only evidence does not trigger a projection for the removed overview section", async () => {
  const fixture = loadCompanion({
    selection: {book: "Jonah", chapter: 1, startVerse: 17, endVerse: 17, reference: "Jonah 1:17"},
  });
  const selection = {book: "Jonah", chapter: 1, startVerse: 17, endVerse: 17, reference: "Jonah 1:17"};
  const context = {
    reference: "Jonah 1:17",
    presentation_packet: {cards: [{type: "did_you_know", evidence_ids: ["jonah-three-days"]}]},
    presentation_evidence: [{
      id: "jonah-three-days",
      ckl_record_identity: {object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"},
    }],
  };

  fixture.contextOptions.onReady(context, selection);
  await Promise.resolve();
  assert.equal(fixture.projectionCalls.length, 0);

  await fixture.companion.openResource("places_locations");
  fixture.resourceRouterOptions.onPlacesLocationsRendered(context, fixture.panel, selection);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(fixture.projectionCalls.length, 0);
});


test("route handoff records origin history only after the router confirms the verified relationship", async () => {
  const fixture = loadCompanion({
    selection: {book: "Jonah", chapter: 1, startVerse: 17, endVerse: 17, reference: "Jonah 1:17"},
  });
  const routeHandoff = {
    routeId: "jonah-1-17-matthew-12-40-sign-of-jonah",
    identity: {object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"},
    passageReference: "Jonah 1:17",
  };

  assert.equal(await fixture.companion.openResource("narrative_explorer", {routeHandoff}), true);
  assert.deepEqual(fixture.routerCalls[0][1].routeHandoff, routeHandoff);
  assert.deepEqual(fixture.historyCalls.map((call) => call.kind), ["push", "replace"]);
  assert.equal(fixture.historyCalls[0].snapshot.resource, null);
  assert.equal(fixture.historyCalls[1].snapshot.resource, "narrative_explorer");
  assert.equal(fixture.companion.getState().resource, "narrative_explorer");
});


test("failed route handoff leaves the Companion origin and browser history unchanged", async () => {
  const fixture = loadCompanion({
    selection: {book: "Jonah", chapter: 1, startVerse: 17, endVerse: 17, reference: "Jonah 1:17"},
    routeHandoffReady: false,
  });
  const result = await fixture.companion.openResource("narrative_explorer", {
    routeHandoff: {
      routeId: "jonah-1-17-matthew-12-40-sign-of-jonah",
      identity: {object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"},
      passageReference: "Jonah 1:17",
    },
  });

  assert.equal(result, false);
  assert.equal(fixture.historyCalls.length, 0);
  assert.equal(fixture.companion.getState().resource, null);
});
