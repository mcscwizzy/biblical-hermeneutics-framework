const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const explorerCore = require("../../bhf_web/static/narrative-explorer.js");

const route = {
  id: "jonah-1-17-matthew-12-40-sign-of-jonah",
  provenance: "ckl_documented_claim",
  source_passage: "Jonah 1:17",
  destination_passage: "Matthew 12:40",
  relationship_category: "later_canonical_reception",
  explanation: "Matthew compares Jonah's narrated duration with the Son of Man's time in the earth.",
  uncertainty: "The idiom and chronology remain uncertain.",
  supporting_records: [{object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"}],
};
const identity = {object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"};

function projection(overrides = {}) {
  return {
    schema_version: "1.0",
    passage: {reference: "Jonah 1:17", book: "Jonah", chapter: 1, verse_start: 17, verse_end: 17},
    coverage: [],
    sections: [],
    items: [],
    connections: [],
    navigation: [],
    related_passages: {
      state: "available",
      query_status: "complete",
      authored_relationships: [],
      evidence_backed_bridges: [route],
    },
    ...overrides,
  };
}

function fixture(options = {}) {
  const records = {trailChanges: [], handoffs: [], rendered: [], sessions: []};
  let selection = {
    book: "Jonah",
    chapter: 1,
    startVerse: 17,
    endVerse: 17,
    reference: "Jonah 1:17",
    selectedVerses: [17],
  };
  const heading = {
    dataset: {narrativeRouteFocusId: route.id},
    focused: false,
    scrolled: false,
    focus() { this.focused = true; },
    scrollIntoView() { this.scrolled = true; },
  };
  let currentView = null;
  const host = {
    hidden: true,
    attributes: {},
    listeners: {},
    addEventListener(type, listener) { this.listeners[type] = listener; },
    replaceChildren(view) { currentView = view; },
    setAttribute(name, value) { this.attributes[name] = String(value); },
    removeAttribute(name) { delete this.attributes[name]; },
    querySelectorAll(selector) {
      if (selector === "[data-narrative-route-focus-id]" && currentView?.options?.selectedRouteId) return [heading];
      return [];
    },
    querySelector() { return null; },
  };
  const panel = {querySelector: (selector) => selector === "[data-companion-resource-host]" ? host : null};
  const shell = {classList: {add() {}, remove() {}}};
  const document = {
    querySelector() { return null; },
    createElement() {
      return {
        setAttribute() {},
        append() {},
        children: [],
      };
    },
  };
  const explorer = {
    ...explorerCore,
    createSubjectLoader() { return {get: async () => null}; },
    renderOverview(_data, renderOptions) {
      records.rendered.push(renderOptions);
      return {options: renderOptions};
    },
    createSession(sessionOptions) {
      let generation = 0;
      const session = {
        close() { generation += 1; },
        async open(passageSelection) {
          const activeGeneration = generation;
          records.sessions.push({...passageSelection});
          sessionOptions.onLoading?.(passageSelection);
          const response = await (options.loadProjection?.(passageSelection) ?? Promise.resolve(projection(options.projectionOverrides)));
          if (generation !== activeGeneration) return {status: "stale"};
          sessionOptions.onReady?.(response, passageSelection);
          return {status: "ready", projection: response};
        },
      };
      return session;
    },
  };
  let router;
  const window = {
    BHFRuntimeConfig: {narrativeExplorerEnabled: options.enabled !== false},
    BHFNarrativeExplorer: explorer,
    BHFReader: {
      async navigateToPassage(book, chapter, startVerse, endVerse, settings = {}) {
        const selectedVerses = settings.selectedVerses || [];
        selection = {
          book,
          chapter,
          startVerse,
          endVerse,
          selectedVerses,
          reference: `${book} ${chapter}:${startVerse}${endVerse && endVerse !== startVerse ? `-${endVerse}` : ""}`,
        };
        const chapterSelection = {
          book,
          chapter,
          startVerse: null,
          endVerse: null,
          selectedVerses: [],
          reference: `${book} ${chapter}`,
        };
        records.managedSelection = [
          router.isManagedReaderSelection(chapterSelection, {source: "reader-chapter"}),
          router.isManagedReaderSelection(selection),
        ];
      },
    },
    requestAnimationFrame(callback) { callback(); },
    performance: {now: () => 1},
  };
  const context = vm.createContext({window, document, console, AbortController, URLSearchParams, performance: {now: () => 1}});
  vm.runInContext(fs.readFileSync("bhf_web/static/resource-router.js", "utf8"), context);
  router = window.BHFResourceRouter.create({
    panel,
    shell,
    getSelection: () => selection,
    onVerifiedRouteHandoff: (...args) => records.handoffs.push(args),
    onNarrativeTrailChange: (...args) => records.trailChanges.push(args),
  });
  return {
    router,
    records,
    host,
    heading,
    setSelection(value) { selection = value; },
  };
}

function handoff(overrides = {}) {
  return {
    routeId: route.id,
    identity,
    passageReference: "Jonah 1:17",
    ...overrides,
  };
}

test("verified route handoff retains verse scope, replaces history only after validation, and focuses the selected route", async () => {
  const value = fixture();
  const opened = await value.router.open("narrative_explorer", {routeHandoff: handoff()});

  assert.equal(opened, true);
  assert.equal(value.records.sessions.length, 1);
  assert.deepEqual(value.records.sessions[0].selectedVerses, [17]);
  assert.equal(value.records.handoffs.length, 1);
  assert.equal(value.records.trailChanges.length, 1);
  assert.equal(value.records.trailChanges[0][1].push, false);
  assert.equal(value.records.rendered[0].selectedRouteId, route.id);
  assert.equal(value.heading.focused, true);
  assert.equal(value.heading.scrolled, true);
  assert.equal(value.router.getNarrativeTrail().originSelection.reference, "Jonah 1:17");
});

test("partial, mismatched, and disabled route handoffs leave no trail or reader visible error", async () => {
  for (const overrides of [
    {related_passages: {state: "available", query_status: "partial", authored_relationships: [], evidence_backed_bridges: [route]}},
    {passage: {reference: "Jonah 2:1"}},
    {related_passages: {state: "unavailable", query_status: "failed", authored_relationships: [], evidence_backed_bridges: []}},
  ]) {
    const value = fixture({projectionOverrides: overrides});
    assert.equal(await value.router.open("narrative_explorer", {routeHandoff: handoff()}), false);
    assert.equal(value.records.handoffs.length, 0);
    assert.equal(value.records.trailChanges.length, 0);
    assert.equal(value.host.hidden, true);
  }
  const disabled = fixture({enabled: false});
  assert.equal(await disabled.router.open("narrative_explorer", {routeHandoff: handoff()}), false);
  assert.equal(disabled.records.sessions.length, 0);
  assert.equal(disabled.records.trailChanges.length, 0);
});

test("a chapter change cancels an in-flight route handoff and prevents a stale trail", async () => {
  let resolveProjection;
  const value = fixture({loadProjection: () => new Promise((resolve) => { resolveProjection = resolve; })});
  const pending = value.router.open("narrative_explorer", {routeHandoff: handoff()});
  await Promise.resolve();
  value.setSelection({book: "Jonah", chapter: 2, reference: "Jonah 2:1"});
  value.router.cancelPendingRouteHandoff();
  resolveProjection(projection());

  assert.equal(await pending, false);
  assert.equal(value.records.handoffs.length, 0);
  assert.equal(value.records.trailChanges.length, 0);
  assert.equal(value.router.getNarrativeTrail(), null);
});

test("a wrong CKL identity fails closed even when the route ID exists", async () => {
  const value = fixture();
  assert.equal(await value.router.open("narrative_explorer", {
    routeHandoff: handoff({identity: {object_id: "matthew", record_kind: "claim", record_id: "jonah-three-days"}}),
  }), false);
  assert.equal(value.records.handoffs.length, 0);
  assert.equal(value.records.trailChanges.length, 0);
});

test("router-driven destination selection preserves the existing origin trail", async () => {
  const origin = {
    book: "Jonah",
    chapter: 1,
    startVerse: 17,
    endVerse: 17,
    selectedVerses: [17],
    reference: "Jonah 1:17",
  };
  const destination = {
    book: "Matthew",
    chapter: 12,
    startVerse: 40,
    endVerse: 40,
    selectedVerses: [40],
    reference: "Matthew 12:40",
  };
  const initialTrail = explorerCore.createTrail(origin);
  const followedTrail = explorerCore.followPassage(
    initialTrail,
    {reference: destination.reference, selection: destination},
    route,
  ).state;
  const value = fixture({
    loadProjection: () => Promise.resolve(projection({
      passage: {reference: "Matthew 12:40", book: "Matthew", chapter: 12, verse_start: 40, verse_end: 40},
    })),
  });

  assert.equal(await value.router.open("narrative_explorer", {trail: followedTrail}), true);
  assert.deepEqual(value.records.managedSelection, [true, true]);
  assert.equal(value.records.sessions.length, 1);
  assert.equal(value.router.getNarrativeTrail().originSelection.reference, "Jonah 1:17");
  assert.equal(value.router.getNarrativeTrail().nodes[value.router.getNarrativeTrail().activeIndex].reference, "Matthew 12:40");
});
