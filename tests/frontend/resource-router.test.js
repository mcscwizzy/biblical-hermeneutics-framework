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
  const records = {trailChanges: [], viewChanges: [], handoffs: [], rendered: [], sessions: []};
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
    get content() { return currentView; },
  };
  const panel = {querySelector: (selector) => selector === "[data-companion-resource-host]" ? host : null};
  const shell = {classList: {add() {}, remove() {}}};
  const document = {
    querySelector() { return null; },
    createElement(tagName) {
      return {
        tagName: String(tagName || "div").toUpperCase(),
        attributes: {},
        dataset: {},
        children: [],
        textContent: "",
        setAttribute(name, value) { this.attributes[name] = String(value); },
        append(...children) { this.children.push(...children); },
      };
    },
    createDocumentFragment() {
      return {
        children: [],
        append(child) { this.children.push(child); },
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
    BHFApi: options.api || {
      async requestJson(url) {
        records.apiRequests = [...(records.apiRequests || []), url];
        if (options.canonicalDetail) return options.canonicalDetail;
        throw new Error(`Unexpected API request: ${url}`);
      },
    },
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
    getContextRecord: () => options.contextRecord || {key: "", status: "ready", context: null},
    onVerifiedRouteHandoff: (...args) => records.handoffs.push(args),
    onNarrativeTrailChange: (...args) => records.trailChanges.push(args),
    onNarrativeViewChange: (...args) => records.viewChanges.push(args),
    backNarrativeView: () => options.backNarrativeView?.() ?? false,
  });
  return {
    router,
    records,
    host,
    heading,
    setSelection(value) { selection = value; },
    getSelection() { return selection; },
  };
}

function nodesWithin(node) {
  return [node, ...(node?.children || []).flatMap(nodesWithin)];
}

function renderedText(node) {
  return nodesWithin(node).map((item) => item?.textContent || "").join(" ");
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

test("canonical Companion cards disclose pending editorial review without inventing approval", async () => {
  const notice = "Draft evidence — awaiting human review";
  const draft = fixture({
    contextRecord: {
      key: "",
      status: "ready",
      context: {
        summaries: {
          canonical: [{
            id: "genesis-context",
            title: "Genesis context",
            type: "cultural background",
            summary: "Existing canonical summary.",
            content_status: "draft",
            review_status: "in_review",
            human_review_required: true,
          }],
        },
      },
    },
  });
  await draft.router.open("canonical");
  const draftNodes = nodesWithin(draft.host.content);
  const draftCard = draftNodes.find((item) => item?.className === "companion-summary-card");
  const noticeNode = draftNodes.find((item) =>
    item?.className?.split(/\s+/).includes("companion-summary-governance"));

  assert.ok(draftCard);
  assert.ok(noticeNode);
  assert.equal(noticeNode.textContent, notice);
  assert.match(draftCard.attributes["aria-label"], /Draft evidence — awaiting human review/);
  assert.match(renderedText(draft.host.content), /Genesis context/);
  assert.match(renderedText(draft.host.content), /Existing canonical summary\./);
  assert.match(renderedText(draft.host.content), /cultural background/);

  for (const governance of [
    {content_status: "complete", review_status: "approved", human_review_required: false},
    {},
  ]) {
    const other = fixture({
      contextRecord: {
        key: "",
        status: "ready",
        context: {summaries: {canonical: [{id: "other-context", title: "Other context", ...governance}]}},
      },
    });
    await other.router.open("canonical");
    assert.doesNotMatch(renderedText(other.host.content), /Draft evidence — awaiting human review/);
    assert.doesNotMatch(
      nodesWithin(other.host.content).find((item) => item?.className === "companion-summary-card")
        ?.attributes?.["aria-label"] || "",
      /approved/i,
    );
  }
});

test("canonical detail uses exact object lookup and keeps source links attached to their evidence", async () => {
  const objectId = "genesis-abraham-call-covenant-context";
  const detail = {
    id: objectId,
    title: "Genesis Abraham Call and Covenant Context",
    summary: "The selected Genesis 12 context record.",
    content_status: "draft",
    review_status: "in_review",
    human_review_required: true,
    sources: [{
      id: "target-source",
      title: "Target source title",
      author: "Recorded author",
      publisher: "Recorded publisher",
      year: 2024,
      locator: "Genesis 12:1–4",
      source_type: "commentary",
      url: "https://example.test/target-source",
      supports: ["target-evidence"],
      notes: "Recorded source note.",
    }],
    evidence_items: [{
      id: "target-evidence",
      title: "Target evidence item",
      description: "Evidence text linked to the target source.",
      source_ids: ["target-source"],
      claim_ids: [],
    }],
  };
  const value = fixture({canonicalDetail: detail});

  await value.router.openCanonicalDetail(objectId);

  assert.deepEqual(value.records.apiRequests, [
    `/api/canonical/objects/${objectId}`,
  ]);
  const body = value.host.content;
  const text = renderedText(body);
  const sourceDisclosure = nodesWithin(body).find((item) =>
    item?.className?.split(/\s+/).includes("companion-canonical-sources"));
  const sourceRecord = nodesWithin(body).find((item) =>
    item?.className?.split(/\s+/).includes("companion-canonical-source"));
  const evidenceRecord = nodesWithin(body).find((item) =>
    item?.dataset?.evidenceId === "target-evidence");

  assert.equal(body.dataset.canonicalObjectId, objectId);
  assert.equal(body.children[0].textContent, "Genesis Abraham Call and Covenant Context");
  assert.match(text, /The selected Genesis 12 context record\./);
  assert.match(text, /Draft evidence — awaiting human review/);
  assert.equal(sourceDisclosure.tagName, "DETAILS");
  assert.match(renderedText(sourceDisclosure), /Sources and attribution · 1 record/);
  assert.equal(sourceRecord.dataset.sourceId, "target-source");
  assert.match(renderedText(sourceRecord), /Recorded author/);
  assert.match(renderedText(sourceRecord), /Recorded publisher/);
  assert.match(renderedText(sourceRecord), /2024/);
  assert.match(renderedText(sourceRecord), /Genesis 12:1–4/);
  assert.match(renderedText(sourceRecord), /Recorded source note\./);
  assert.match(renderedText(sourceRecord), /Recorded support links/);
  assert.match(renderedText(sourceRecord), /Target evidence item/);
  assert.equal(evidenceRecord.tagName, "DETAILS");
  assert.match(renderedText(evidenceRecord), /Target source title/);
  assert.doesNotMatch(text, /abraham-only-source/);
});

test("canonical detail safely reports missing source records and partial attribution", async () => {
  const noSources = fixture({canonicalDetail: {
    id: "ordinary-context",
    title: "Ordinary context",
    summary: "A non-draft CKL record.",
    content_status: "complete",
    review_status: "in_review",
    human_review_required: true,
    sources: [],
    evidence_items: [],
  }});
  await noSources.router.openCanonicalDetail("ordinary-context");
  assert.match(renderedText(noSources.host.content), /No source records are recorded/);
  assert.doesNotMatch(renderedText(noSources.host.content), /Draft evidence — awaiting human review/);

  const unavailable = fixture({canonicalDetail: {
    id: "unavailable-context",
    title: "Unavailable context",
    evidence_items: [],
  }});
  await unavailable.router.openCanonicalDetail("unavailable-context");
  assert.match(renderedText(unavailable.host.content), /Source details are unavailable/);

  const partial = fixture({canonicalDetail: {
    id: "partial-context",
    title: "Partial context",
    sources: [{id: "only-an-id", supports: []}],
    evidence_items: [],
  }});
  await partial.router.openCanonicalDetail("partial-context");
  assert.match(renderedText(partial.host.content), /only-an-id/);
  assert.doesNotMatch(renderedText(partial.host.content), /approved/i);
});

test("canonical detail rejects a response for a different object ID", async () => {
  const value = fixture({canonicalDetail: {
    id: "abraham",
    title: "Abraham",
    sources: [{id: "abraham-only-source", title: "Unrelated source"}],
  }});

  await value.router.openCanonicalDetail("genesis-abraham-call-covenant-context");

  assert.doesNotMatch(renderedText(value.host.content), /Unrelated source/);
  assert.match(renderedText(value.host.content), /does not match the selected canonical record/i);
});

test("canonical detail failure leaves the selected passage intact and exposes an alert", async () => {
  const value = fixture({api: {
    async requestJson(url) {
      value.records.apiRequests = [...(value.records.apiRequests || []), url];
      throw new Error("canonical object not found");
    },
  }});

  await value.router.openCanonicalDetail("not-a-real-ckl-object");

  const alert = nodesWithin(value.host.content).find((item) => item?.attributes?.role === "alert");
  assert.ok(alert);
  assert.match(renderedText(alert), /canonical object not found/);
  assert.equal(value.getSelection().reference, "Jonah 1:17");
});

test("a delayed canonical detail response cannot replace a newer exact selection", async () => {
  const targetId = "genesis-abraham-call-covenant-context";
  let resolveTarget;
  const value = fixture({api: {
    requestJson(url) {
      value.records.apiRequests = [...(value.records.apiRequests || []), url];
      if (url.endsWith(targetId)) {
        return new Promise((resolve) => { resolveTarget = resolve; });
      }
      return Promise.resolve({
        id: "shechem",
        title: "Shechem",
        summary: "Newer selected object.",
        sources: [],
        evidence_items: [],
      });
    },
  }});

  const delayed = value.router.openCanonicalDetail(targetId);
  await Promise.resolve();
  await value.router.openCanonicalDetail("shechem");
  resolveTarget({
    id: targetId,
    title: "Genesis Abraham Call and Covenant Context",
    sources: [{id: "stale-source", title: "Stale target source"}],
    evidence_items: [],
  });
  await delayed;

  assert.equal(value.host.content.dataset.canonicalObjectId, "shechem");
  assert.doesNotMatch(renderedText(value.host.content), /Stale target source/);
  assert.equal(value.getSelection().reference, "Jonah 1:17");
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

test("Narrative Explorer router restores a focused category from its view option without another projection", async () => {
  const value = fixture();
  const view = {kind: "category", categoryId: "themes_biblical_connections"};

  assert.equal(await value.router.open("narrative_explorer", {view}), true);

  assert.equal(value.router.getNarrativeView().kind, view.kind);
  assert.equal(value.router.getNarrativeView().categoryId, view.categoryId);
  assert.equal(value.records.rendered.at(-1).view.kind, view.kind);
  assert.equal(value.records.rendered.at(-1).view.categoryId, view.categoryId);
  assert.equal(value.records.sessions.length, 1);
});

test("category navigation reuses the passage projection and supports Back to topics", async () => {
  let historyBacks = 0;
  const value = fixture({backNarrativeView: () => { historyBacks += 1; return false; }});
  assert.equal(await value.router.open("narrative_explorer"), true);
  const initialSessions = value.records.sessions.length;
  const card = {dataset: {narrativeFocusId: "themes_biblical_connections"}};

  value.records.rendered.at(-1).onOpenCategory("themes_biblical_connections", card);

  assert.equal(value.router.getNarrativeView().categoryId, "themes_biblical_connections");
  assert.equal(value.records.rendered.at(-1).view.categoryId, "themes_biblical_connections");
  assert.equal(value.records.sessions.length, initialSessions);
  assert.equal(value.records.viewChanges[0][0].kind, "category");
  assert.equal(value.records.viewChanges[0][0].categoryId, "themes_biblical_connections");
  assert.equal(value.records.viewChanges[0][1].push, true);

  value.records.rendered.at(-1).onBackToOverview(card);

  assert.equal(historyBacks, 1);
  assert.equal(value.router.getNarrativeView().kind, "overview");
  assert.equal(value.records.rendered.at(-1).view.kind, "overview");
  assert.equal(value.records.sessions.length, initialSessions);
});

test("closing during verification discards the delayed route and history", async () => {
  let resolveProjection;
  const value = fixture({loadProjection: () => new Promise((resolve) => { resolveProjection = resolve; })});
  const pending = value.router.open("narrative_explorer", {routeHandoff: handoff()});
  await Promise.resolve();
  value.router.close();
  resolveProjection(projection());
  assert.equal(await pending, false);
  assert.equal(value.records.handoffs.length, 0);
  assert.equal(value.records.trailChanges.length, 0);
  assert.equal(value.heading.focused, false);
  assert.equal(value.router.getNarrativeTrail(), null);
});

test("a removed route at activation does not open or add history", async () => {
  const value = fixture({projectionOverrides: {related_passages: {
    state: "available", query_status: "complete", authored_relationships: [], evidence_backed_bridges: [],
  }}});
  assert.equal(await value.router.open("narrative_explorer", {routeHandoff: handoff()}), false);
  assert.equal(value.records.handoffs.length, 0);
  assert.equal(value.records.trailChanges.length, 0);
  assert.equal(value.heading.focused, false);
});

test("a second rapid activation wins when the first response arrives last", async () => {
  const pending = [];
  const secondRoute = {...route, id: "second-route"};
  const value = fixture({loadProjection: () => new Promise((resolve) => pending.push(resolve))});
  const first = value.router.open("narrative_explorer", {routeHandoff: handoff()});
  await Promise.resolve();
  const second = value.router.open("narrative_explorer", {routeHandoff: handoff({routeId: secondRoute.id})});
  await Promise.resolve();
  const both = projection({related_passages: {state: "available", query_status: "complete", authored_relationships: [], evidence_backed_bridges: [route, secondRoute]}});
  pending[1](both);
  assert.equal(await second, true);
  pending[0](both);
  assert.equal(await first, false);
  assert.equal(value.records.handoffs.length, 1);
  assert.equal(value.records.trailChanges.length, 1);
  assert.equal(value.records.rendered.at(-1).selectedRouteId, secondRoute.id);
});

test("opening a different resource cancels delayed verification", async () => {
  let resolveProjection;
  const value = fixture({loadProjection: () => new Promise((resolve) => { resolveProjection = resolve; })});
  const pending = value.router.open("narrative_explorer", {routeHandoff: handoff()});
  await Promise.resolve();
  const other = value.router.open("cross_references");
  resolveProjection(projection());
  assert.equal(await pending, false);
  assert.equal(await other, true);
  assert.equal(value.records.handoffs.length, 0);
  assert.equal(value.records.trailChanges.length, 0);
  assert.equal(value.heading.focused, false);
  assert.equal(value.router.getNarrativeTrail(), null);
});
