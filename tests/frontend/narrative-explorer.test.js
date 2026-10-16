const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const explorer = require("../../bhf_web/static/narrative-explorer.js");

class FakeElement {
  constructor(tagName) {
    this.tagName = String(tagName).toUpperCase();
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.hidden = false;
    this.className = "";
    this.listeners = {};
    this._text = "";
  }

  set textContent(value) {
    this._text = String(value ?? "");
    this.children = [];
  }

  get textContent() {
    return this._text + this.children.map((child) => child.textContent).join("");
  }

  append(...children) {
    this.children.push(...children);
  }

  replaceChildren(...children) {
    this._text = "";
    this.children = children;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  addEventListener(name, callback) {
    this.listeners[name] = callback;
  }

  click() {
    this.listeners.click?.({currentTarget: this, target: this});
  }
}

function fakeDocument() {
  return {createElement: (tagName) => new FakeElement(tagName)};
}

function descendants(element) {
  return [element, ...element.children.flatMap(descendants)];
}

function section(id, itemIds = [], state = "not_represented") {
  return {
    id,
    state,
    item_ids: itemIds,
    source_domains: ["canonical_knowledge_library"],
    description: "Passage-linked records returned by the completed source lookup.",
  };
}

function projection(overrides = {}) {
  return {
    schema_version: "1.0",
    passage: {reference: "Genesis 1", book: "Genesis", chapter: 1, verse_start: null, verse_end: null, scope: "chapter"},
    coverage: [
      {domain: "ckl", source_domain: "canonical_knowledge_library", state: "available", query_status: "complete", query_returned_count: 1, projected_item_count: 3, reason_code: null, missing_subdomains: [], description: "CKL returned eligible records."},
      {domain: "maps", source_domain: "passage_maps", state: "not_represented", query_status: "complete", query_returned_count: 0, projected_item_count: 0, reason_code: "no_eligible_records", missing_subdomains: [], description: "The completed map lookup returned no eligible records."},
      {domain: "archaeology", source_domain: "archaeology_passage_resolver", state: "not_represented", query_status: "complete", query_returned_count: 0, projected_item_count: 0, reason_code: "no_eligible_records", missing_subdomains: [], description: "The completed archaeology lookup returned no eligible records."},
    ],
    sections: [
      section("biblical_narrative", ["ckl:creation#claim:days"], "available"),
      section("archaeology_ancient_history", ["ckl:creation#evidence:comparison"], "available"),
      {...section("biblical_geography"), source_domains: ["canonical_knowledge_library", "passage_maps"]},
      section("divine_council_cosmic_geography", ["ckl:creation#evidence:cosmos"], "available"),
      section("themes_biblical_connections"),
      section("people_events_relationships"),
    ],
    items: [
      {
        id: "ckl:creation#claim:days",
        domain: "ckl",
        record_kind: "claim",
        object_id: "creation",
        parent_object_id: "creation",
        claim_id: "days",
        evidence_id: null,
        object_type: "book",
        title: "Ordered sequence",
        claim_text: "The text arranges creation in a sequence.",
        description: null,
        evidence_category: null,
        claim_type: "literary",
        assertion_type: "textual-observation",
        source_ids: ["genesis-text"],
        sources: [{id: "genesis-text", details_available: true, bibliographic_details: {title: "Genesis 1", year: null}, unavailable_reason: null}],
        passage_anchors: [{reference: "Genesis 1:1-31", relationship: "direct"}],
        applicable_passage_anchors: [{reference: "Genesis 1:1-31", relationship: "direct"}],
        related_passages: ["Genesis 1:1-31"],
        original_relationship_types: ["direct"],
        confidence: "high",
        certainty: "probable",
        dispute_status: "not_disputed",
        interpretation_state: "known",
        review_status: "approved",
        content_status: "published",
        human_review_required: false,
        temporal_relation: null,
        temporal_relations: [],
        temporal_scope: null,
        rationale: {basis: "Explicit literary observation."},
        source_metadata: {},
        geography_kind: "unknown",
        place_identification_confidence: "unknown",
        stored_coordinates: null,
        coordinates_displayable: null,
        coordinate_display_reason: null,
        stored_geometry: null,
        geometry_displayable: null,
        geometry_display_reason: null,
        section_ids: ["biblical_narrative"],
        navigation: {id: "navigation:ckl:creation", kind: "canonical_object", target_id: "creation", href: "/api/canonical/objects/creation"},
      },
      {
        id: "ckl:creation#evidence:comparison",
        domain: "ckl",
        record_kind: "evidence",
        object_id: "creation",
        parent_object_id: "creation",
        claim_id: null,
        evidence_id: "comparison",
        object_type: "book",
        title: "Ancient textual comparison",
        claim_text: null,
        description: "A source records a literary comparison.",
        evidence_category: "ancient-text",
        claim_type: null,
        assertion_type: null,
        source_ids: ["tablet-k"],
        sources: [{id: "tablet-k", details_available: false, bibliographic_details: null, unavailable_reason: "source_details_unavailable"}],
        passage_anchors: [{reference: "Genesis 1:1", relationship: "comparative"}],
        applicable_passage_anchors: [{reference: "Genesis 1:1", relationship: "comparative"}],
        related_passages: ["Genesis 1:1"],
        original_relationship_types: ["comparative"],
        confidence: null,
        certainty: null,
        dispute_status: "unknown",
        interpretation_state: "unknown",
        review_status: null,
        content_status: null,
        human_review_required: null,
        temporal_relation: "earlier-comparative",
        temporal_relations: [],
        temporal_scope: null,
        rationale: {},
        source_metadata: {},
        geography_kind: "unknown",
        place_identification_confidence: "unknown",
        stored_coordinates: null,
        coordinates_displayable: null,
        coordinate_display_reason: null,
        stored_geometry: null,
        geometry_displayable: null,
        geometry_display_reason: null,
        section_ids: ["archaeology_ancient_history"],
        navigation: null,
      },
      {
        id: "ckl:creation#evidence:cosmos",
        domain: "ckl",
        record_kind: "evidence",
        object_id: "creation",
        parent_object_id: "creation",
        claim_id: null,
        evidence_id: "cosmos",
        object_type: "book",
        title: "Cosmic language",
        claim_text: "<img src=x onerror=alert(1)>",
        description: null,
        evidence_category: "worldview-concept",
        claim_type: null,
        assertion_type: null,
        source_ids: [],
        sources: [],
        passage_anchors: [{reference: "Genesis 1:1", relationship: "textual"}],
        applicable_passage_anchors: [{reference: "Genesis 1:1", relationship: "textual"}],
        related_passages: ["Genesis 1:1"],
        original_relationship_types: ["textual"],
        confidence: null,
        certainty: null,
        dispute_status: "disputed",
        interpretation_state: "unknown",
        review_status: null,
        content_status: null,
        human_review_required: null,
        temporal_relation: null,
        temporal_relations: [],
        temporal_scope: null,
        rationale: {},
        source_metadata: {},
        geography_kind: "cosmic_textual",
        place_identification_confidence: "unknown",
        stored_coordinates: {latitude: 40, longitude: -74},
        coordinates_displayable: false,
        coordinate_display_reason: "conceptual_geography",
        stored_geometry: null,
        geometry_displayable: false,
        geometry_display_reason: "conceptual_geography",
        section_ids: ["divine_council_cosmic_geography"],
        navigation: {id: "navigation:ckl:creation", kind: "canonical_object", target_id: "creation", href: "/api/canonical/objects/creation"},
      },
    ],
    connections: [],
    navigation: [],
    ...overrides,
  };
}

test("chapter and verse selections map to the NE-3 route contract", () => {
  assert.equal(
    explorer.urlFor({book: "Genesis", chapter: 1}),
    "/api/narrative-explorer/v1/passages/Genesis/1",
  );
  assert.equal(
    explorer.urlFor({book: "Song of Songs", chapter: 2, startVerse: 3, endVerse: 7}),
    "/api/narrative-explorer/v1/passages/Song%20of%20Songs/2?verse_start=3&verse_end=7",
  );
});

test("simultaneous loads for the same passage share one uncached network response", async () => {
  let requests = 0;
  let requestedUrl = "";
  let cacheMode = "";
  const payload = JSON.stringify(projection());
  const fetcher = async (url, options) => {
    requests += 1;
    requestedUrl = url;
    cacheMode = options.cache;
    return {ok: true, status: 200, text: async () => payload};
  };

  const [first, second] = await Promise.all([
    explorer.load({book: "Mark", chapter: 1}, {fetcher, resolveUrl: (url) => url}),
    explorer.load({book: "Mark", chapter: 1}, {fetcher, resolveUrl: (url) => url}),
  ]);

  assert.equal(requests, 1);
  assert.equal(cacheMode, "no-store");
  assert.equal(requestedUrl, "/api/narrative-explorer/v1/passages/Mark/1");
  assert.equal(first.schema_version, "1.0");
  assert.equal(second.schema_version, "1.0");
});

test("aborting one duplicate subscriber does not cancel the other passage reader", async () => {
  let resolveFetch;
  let networkSignal;
  const fetcher = (_url, options) => {
    networkSignal = options.signal;
    return new Promise((resolve) => { resolveFetch = resolve; });
  };
  const firstController = new AbortController();
  const secondController = new AbortController();
  const first = explorer.load({book: "Mark", chapter: 2}, {
    fetcher,
    resolveUrl: (url) => url,
    signal: firstController.signal,
  });
  const second = explorer.load({book: "Mark", chapter: 2}, {
    fetcher,
    resolveUrl: (url) => url,
    signal: secondController.signal,
  });
  firstController.abort();
  await assert.rejects(first, {name: "AbortError"});
  assert.equal(networkSignal.aborted, false);
  resolveFetch({ok: true, status: 200, text: async () => JSON.stringify(projection())});

  const result = await second;

  assert.equal(result.schema_version, "1.0");
});

test("a disabled explorer session does not issue a Narrative Explorer request", async () => {
  let requests = 0;
  const session = explorer.createSession({
    enabled: false,
    fetchProjection: async () => { requests += 1; return projection(); },
  });

  const result = await session.open({book: "Genesis", chapter: 1});

  assert.equal(result.status, "disabled");
  assert.equal(requests, 0);
});

test("one open passage reuses its pending request and older responses cannot replace a newer passage", async () => {
  const resolvers = [];
  const ready = [];
  const session = explorer.createSession({
    enabled: true,
    fetchProjection: (selection) => new Promise((resolve) => resolvers.push(() => resolve(projection({
      passage: {reference: `${selection.book} ${selection.chapter}`},
    })))),
    onReady: (value) => ready.push(value.passage.reference),
  });

  const first = session.open({book: "Genesis", chapter: 1});
  const duplicate = session.open({book: "Genesis", chapter: 1});
  await Promise.resolve();
  assert.equal(resolvers.length, 1);
  const newer = session.open({book: "Genesis", chapter: 2});
  await Promise.resolve();
  assert.equal(resolvers.length, 2);
  resolvers[1]();
  await newer;
  resolvers[0]();
  await Promise.all([first, duplicate]);

  assert.deepEqual(ready, ["Genesis 2"]);
});

test("closing a passage session aborts its request and ignores the late result", async () => {
  let resolveProjection;
  let receivedSignal;
  const ready = [];
  const session = explorer.createSession({
    enabled: true,
    fetchProjection: (_selection, {signal}) => {
      receivedSignal = signal;
      return new Promise((resolve) => { resolveProjection = resolve; });
    },
    onReady: (value) => ready.push(value),
  });

  const pending = session.open({book: "Psalm", chapter: 82});
  await Promise.resolve();
  session.close();
  resolveProjection(projection());
  const result = await pending;

  assert.equal(receivedSignal.aborted, true);
  assert.equal(result.status, "stale");
  assert.equal(ready.length, 0);
});

test("an offline miss is announced and retried after the browser returns online", async () => {
  let onlineHandler;
  let attempts = 0;
  const ready = [];
  const errors = [];
  const session = explorer.createSession({
    enabled: true,
    eventTarget: {addEventListener: (name, callback) => { if (name === "online") onlineHandler = callback; }},
    fetchProjection: async () => {
      attempts += 1;
      if (attempts === 1) throw new TypeError("Failed to fetch");
      return projection();
    },
    onError: (state) => errors.push(state),
    onReady: (value) => ready.push(value.passage.reference),
  });

  const first = await session.open({book: "Psalm", chapter: 82});
  onlineHandler();
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(first.state, "offline");
  assert.deepEqual(errors, ["offline"]);
  assert.equal(attempts, 2);
  assert.deepEqual(ready, ["Genesis 1"]);
});

test("overview renders bounded source records, coverage and provenance without HTML interpretation", () => {
  const document = fakeDocument();
  const created = [];
  const trackedDocument = {
    createElement(tagName) {
      const element = document.createElement(tagName);
      created.push(element);
      return element;
    },
  };
  const manyItems = Array.from({length: 80}, (_, index) => ({
    ...projection().items[0],
    id: `ckl:creation#claim:${index}`,
    claim_id: String(index),
    title: `Claim ${index}`,
    section_ids: ["biblical_narrative"],
  }));
  const mapItems = [
    {id: "maps:00-eden-safe", title: "Supported site", coordinates_displayable: true},
    {id: "maps:01-eden-uncertain", title: "Eden", coordinates_displayable: false, coordinate_display_reason: "identification_unresolved"},
    {id: "maps:02-no-selection", title: "Collection-only place", coordinates_displayable: false, coordinate_display_reason: "identification_unresolved", selection_required: false},
    {id: "maps:99-conceptual", title: "Conceptual map result", coordinates_displayable: true, geography_kind: "unknown"},
  ].map((entry) => ({
    ...projection().items[1],
    ...entry,
    domain: "maps",
    record_kind: "map_place",
    object_id: entry.id,
    parent_object_id: null,
    evidence_id: null,
    section_ids: ["biblical_geography"],
    geography_kind: entry.geography_kind || "physical_place",
    navigation: {id: `navigation:${entry.id}`, kind: "map_place", target_id: entry.id, href: "/api/maps/biblical-places", selection_required: entry.selection_required !== false},
  }));
  const cosmicMapTrap = {
    ...projection().items[2],
    navigation: {id: "navigation:map-trap", kind: "map_place", target_id: "cosmos", href: "/api/maps/biblical-places", selection_required: true},
  };
  const data = projection({
    coverage: projection().coverage.map((entry) => entry.domain === "maps"
      ? {...entry, state: "available", query_returned_count: 3, projected_item_count: 3, description: "Map lookup returned eligible records."}
      : entry),
    sections: [
      section("biblical_narrative", manyItems.map((item) => item.id), "available"),
      ...projection().sections.slice(1).map((entry) => entry.id === "archaeology_ancient_history"
        ? {...entry, source_domains: ["canonical_knowledge_library", "archaeology_passage_resolver"]}
        : entry),
      {...section("biblical_geography", mapItems.map((item) => item.id), "available"), source_domains: ["canonical_knowledge_library", "passage_maps"]},
    ],
    items: [...manyItems, projection().items[1], ...mapItems, cosmicMapTrap],
  });

  const navigations = [];
  const root = explorer.renderOverview(data, {document: trackedDocument, onNavigate: (item, action) => navigations.push({item, action})});
  const sectionsHost = root.children.find((child) => child.className === "narrative-explorer-sections");
  const narrativeCard = sectionsHost.children.find((child) => child.dataset.sectionId === "biblical_narrative");
  const geographyCard = sectionsHost.children.find((child) => child.dataset.sectionId === "biblical_geography");
  const cosmicCard = sectionsHost.children.find((child) => child.dataset.sectionId === "divine_council_cosmic_geography");
  const narrativePreviewList = narrativeCard.children.find((element) => element.className === "narrative-explorer-previews");

  assert.match(root.textContent, /Biblical Narrative/);
  assert.match(root.textContent, /Archaeology & Ancient History/);
  assert.match(root.textContent, /Biblical Geography/);
  assert.match(root.textContent, /Divine Council & Cosmic Geography/);
  assert.match(root.textContent, /Themes & Biblical Connections/);
  assert.match(root.textContent, /People, Events & Relationships/);
  assert.match(root.textContent, /No linked records are represented here yet/);
  assert.match(root.textContent, /Maps: lookup completed; 3 source records returned/);
  assert.match(root.textContent, /Archaeology service: lookup completed; no linked archaeology-service records returned/);
  assert.equal(narrativePreviewList.children.length, 2);
  assert.match(narrativeCard.textContent, /80 claims/);
  assert.match(root.textContent, /Genesis 1:1-31/);
  assert.match(root.textContent, /high/);
  assert.match(root.textContent, /probable/);
  assert.match(root.textContent, /direct/);
  assert.match(root.textContent, /tablet-k/);
  assert.match(root.textContent, /Original relationship types: direct/);
  assert.match(root.textContent, /<img src=x onerror=alert\(1\)>/);
  assert.equal(created.some((element) => element.tagName === "IMG"), false);
  assert.match(root.textContent, /Map point withheld: identification_unresolved/);
  assert.doesNotMatch(root.textContent, /40|latitude|longitude/);
  assert.equal(descendants(geographyCard).filter((element) => element.className.includes("narrative-explorer-item-action")).length, 2);
  assert.equal(descendants(cosmicCard).filter((element) => element.className.includes("narrative-explorer-item-action")).length, 0);
  const mapActions = descendants(geographyCard).filter((element) => element.className.includes("narrative-explorer-item-action"));
  mapActions[0].click();
  mapActions[1].click();
  assert.deepEqual(navigations.map((entry) => entry.action.mapFocusAllowed), [true, false]);
  assert.deepEqual(navigations.map((entry) => entry.item.navigation.target_id), ["maps:00-eden-safe", "maps:01-eden-uncertain"]);
  assert.match(mapActions[0].textContent, /try to focus this item/);
  assert.match(mapActions[1].textContent, /general Maps Explorer/);
  const inspect = geographyCard.children.find((element) => element.className.includes("narrative-explorer-inspect"));
  inspect.click();
  const unsupportedCard = descendants(geographyCard).find((element) => element.tagName === "ARTICLE" && element.textContent.includes("Collection-only place"));
  assert.equal(descendants(unsupportedCard).filter((element) => element.className.includes("narrative-explorer-item-action")).length, 0);
  assert.doesNotMatch(root.textContent, /shared motifs prove direct quotation/i);
});

test("unavailable states are announced without turning a network failure into an empty result", () => {
  const failure = explorer.renderFailure("offline", {reference: "Exodus 3"}, {document: fakeDocument()});

  assert.equal(failure.attributes.role, "alert");
  assert.match(failure.textContent, /Not available offline/);
  assert.match(failure.textContent, /No saved Narrative Explorer projection is available for Exodus 3/);
  assert.match(failure.textContent, /Reconnect and try again/);
});

test("overview exposes an inspect control with the exact projected item identity", () => {
  const data = projection();
  const inspected = [];
  const root = explorer.renderOverview(data, {
    document: fakeDocument(),
    onInspect: (item, button) => inspected.push({id: item.id, control: button.dataset.narrativeItemId}),
  });
  const button = descendants(root).find((element) => element.dataset.narrativeItemId === data.items[0].id);

  assert.ok(button, "each visible projected item should be openable by its stable ID");
  button.click();

  assert.deepEqual(inspected, [{id: data.items[0].id, control: data.items[0].id}]);
});

test("trail state preserves the original passage and limits relationship hops", () => {
  const origin = {
    book: "Genesis",
    chapter: 2,
    startVerse: 8,
    endVerse: 10,
    selectedVerses: [8, 9, 10],
    selectedText: "Garden passage",
    translation: "kjv",
    reference: "Genesis 2:8-10",
  };
  let trail = explorer.createTrail(origin);
  trail = explorer.addEvidenceStep(trail, {
    id: "ckl:genesis#evidence:g2-garden-planting-presence",
    parent_object_id: "genesis",
    title: "Eden evidence",
  }, "item:ckl:genesis#evidence:g2-garden-planting-presence");

  const first = explorer.followSubject(trail, {
    targetId: "creation",
    title: "Creation",
  }, {
    id: "connection-one",
    direction: "one_way",
    connectionType: "uncategorized",
    originalRelationshipType: "narrative-context",
  }, "connection:connection-one");
  assert.equal(first.error, null);
  trail = first.state;
  const second = explorer.followSubject(trail, {targetId: "temple", title: "Temple"}, {
    id: "connection-two",
    direction: "one_way",
    originalRelationshipType: "later-sanctuary-development",
  }, "connection:connection-two").state;
  const third = explorer.followPassage(second, {
    reference: "John 1:14",
    selection: {book: "John", chapter: 1, startVerse: 14, endVerse: 14, reference: "John 1:14"},
  }, {id: "scripture-one", originalRelationshipType: "direct"}, "scripture:John 1:14");

  assert.equal(third.error, null);
  assert.equal(third.state.nodes.at(-1).relationshipHops, 3);
  assert.deepEqual(third.state.originSelection, explorer.createTrail(origin).originSelection);
  const blocked = explorer.followSubject(third.state, {targetId: "temple-theme", title: "Temple Theme"}, {
    id: "connection-four",
    direction: "one_way",
    originalRelationshipType: "related-concept",
  }, "connection:connection-four");
  assert.equal(blocked.error, "depth_limit");
});

test("trail detects cycles and can return to its originating passage", () => {
  const initial = explorer.createTrail({book: "Exodus", chapter: 3, reference: "Exodus 3"});
  const evidence = explorer.addEvidenceStep(initial, {
    id: "ckl:presence-theme#claim:presence",
    parent_object_id: "presence-theme",
    title: "Presence evidence",
  }, "item:presence");
  const cycle = explorer.followSubject(evidence, {targetId: "presence-theme", title: "Presence Theme"}, {
    id: "self-edge",
    direction: "one_way",
    originalRelationshipType: "related-concept",
  }, "connection:self-edge");
  const linkedPassage = explorer.followPassage(evidence, {
    reference: "Exodus 40:34-38",
    selection: {book: "Exodus", chapter: 40, startVerse: 34, endVerse: 38, reference: "Exodus 40:34-38"},
  }, {id: "anchor", originalRelationshipType: "scripture-anchor"}, "scripture:Exodus 40:34-38");
  const returned = explorer.returnToOrigin(linkedPassage.state);

  assert.equal(cycle.error, "cycle");
  assert.equal(returned.nodes[returned.activeIndex].id, "passage:Exodus 3");
  assert.deepEqual(returned.originSelection, initial.originSelection);
});

test("Scripture destinations require a canonical reader book, chapter, and valid verse range", () => {
  const books = [
    {value: "Genesis", chapters: 50},
    {value: "John", chapters: 21},
  ];

  assert.deepEqual(explorer.validateScriptureReference("john 1:14", books), {
    valid: true,
    book: "John",
    chapter: 1,
    startVerse: 14,
    endVerse: 14,
    reference: "John 1:14",
  });
  assert.equal(explorer.validateScriptureReference("Unknown 1:1", books).valid, false);
  assert.equal(explorer.validateScriptureReference("John 22:1", books).valid, false);
  assert.equal(explorer.validateScriptureReference("John 1:8-3", books).valid, false);
  assert.equal(explorer.validateScriptureReference("John 1:0", books).valid, false);
});

test("evidence detail displays only item provenance, uncertainty, bibliography, and safe connections", () => {
  const data = projection();
  const item = {
    ...data.items[1],
    title: "Ugaritic assembly comparison",
    evidence_category: "ancient-text",
    certainty: "probable",
    dispute_status: "major_scholarly_disagreement",
    interpretation_state: "disputed",
    review_status: "in_review",
    content_status: "draft",
    human_review_required: true,
    parent_summary: "This parent narrative must not appear in child evidence detail.",
    sources: [{
      id: "ugaritic-study",
      details_available: true,
      bibliographic_details: {
        title: "The Baal Cycle",
        author: "Mark S. Smith",
        publisher: "Brill",
        year: 1994,
        locator: "Tablet II",
        url: "https://example.test/baal-cycle",
      },
    }, {
      id: "unsafe-source-url",
      details_available: true,
      bibliographic_details: {title: "Unsafe source URL", url: "javascript:alert(1)"},
    }],
  };
  const connections = [
    {
      id: "edge-one-way",
      source_id: item.id,
      target_id: "ckl:tabernacle",
      connection_type: "uncategorized",
      original_relationship_type: "later-sanctuary-development",
      relationship_mode: "not_recorded",
      direction: "one_way",
      reverse_edge_id: null,
      temporal_layer: "unknown",
      basis: {kind: "ckl_related_object", notes: "The CKL records a later sanctuary-development association."},
    },
    {
      id: "edge-reciprocal",
      source_id: item.id,
      target_id: "ckl:temple-theme",
      connection_type: "thematic_relationship",
      original_relationship_type: "thematic-anchor",
      relationship_mode: "not_recorded",
      direction: "reciprocal",
      reverse_edge_id: "reverse-edge",
      temporal_layer: "unknown",
      basis: {kind: "ckl_related_object", notes: "The reverse edge is recorded."},
    },
    {
      id: "reverse-edge",
      source_id: "ckl:temple-theme",
      target_id: item.id,
      connection_type: "thematic_relationship",
      original_relationship_type: "thematic-anchor",
      relationship_mode: "not_recorded",
      direction: "reciprocal",
      reverse_edge_id: "edge-reciprocal",
      temporal_layer: "unknown",
      basis: {kind: "ckl_related_object", notes: "The authored reverse edge confirms reciprocity."},
    },
    {
      id: "incoming-one-way",
      source_id: "ckl:unrelated-source",
      target_id: item.id,
      connection_type: "narrative_parallel",
      original_relationship_type: "incoming-only",
      relationship_mode: "not_recorded",
      direction: "one_way",
      reverse_edge_id: null,
      temporal_layer: "unknown",
      basis: {kind: "ckl_related_object", parent_object_id: "unrelated-source"},
    },
  ];
  const view = explorer.renderEvidenceDetail(item, connections, explorer.createTrail({
    book: "Psalm", chapter: 82, reference: "Psalm 82",
  }), {
    document: fakeDocument(),
    knownBooks: [{value: "Psalm", chapters: 150}],
    onFollowConnection: () => {},
  });

  assert.match(view.textContent, /ckl:creation#evidence:comparison/);
  assert.match(view.textContent, /Ancient comparative literature/);
  assert.match(view.textContent, /probable/);
  assert.match(view.textContent, /major_scholarly_disagreement/);
  assert.match(view.textContent, /in_review/);
  assert.match(view.textContent, /draft/);
  assert.match(view.textContent, /Human review required: Yes/);
  assert.match(view.textContent, /The Baal Cycle/);
  assert.match(view.textContent, /Mark S\. Smith/);
  assert.match(view.textContent, /Brill/);
  assert.match(view.textContent, /1994/);
  assert.match(view.textContent, /Tablet II/);
  assert.match(view.textContent, /ugaritic-study/);
  assert.match(view.textContent, /original CKL label: later-sanctuary-development/);
  assert.match(view.textContent, /Direction:.*one-way/);
  assert.match(view.textContent, /Direction:.*reciprocal/);
  assert.match(view.textContent, /incoming-only/);
  assert.match(view.textContent, /does not create a reverse navigation edge/);
  assert.match(view.textContent, /reciprocal CKL edge is recorded/i);
  assert.match(view.textContent, /not, by itself, evidence of borrowing, quotation, fulfillment, or dependence/i);
  assert.doesNotMatch(view.textContent, /This parent narrative must not appear/);
  assert.equal(descendants(view).filter((element) => element.className.includes("narrative-explorer-trail-action")).length, 2);
  assert.equal(descendants(view).some((element) => element.tagName === "IMG"), false);
  assert.equal(descendants(view).some((element) => element.tagName === "A" && /^(?:javascript|data):/i.test(element.attributes.href || "")), false);
  assert.match(view.textContent, /Unsafe source URL/);

  const malformedReciprocal = explorer.renderEvidenceDetail(
    item,
    [connections[1]],
    explorer.createTrail({book: "Psalm", chapter: 82, reference: "Psalm 82"}),
    {document: fakeDocument()},
  );
  assert.match(malformedReciprocal.textContent, /Direction:.*one-way/);
  assert.doesNotMatch(malformedReciprocal.textContent, /A reciprocal CKL edge is recorded/);
});

test("projected CKL connections follow the recorded target object and retain their relationship metadata", () => {
  const item = {
    id: "ckl:tabernacle#evidence:tabernacle-textual-evidence",
    parent_object_id: "tabernacle",
    title: "Tabernacle textual evidence",
    evidence_category: "historical_context",
    passage_anchors: [{reference: "Exodus 25:8-9", relationship: "direct"}],
    applicable_passage_anchors: [{reference: "Exodus 25:8-9", relationship: "direct"}],
  };
  const edge = {
    id: "tabernacle-temple-edge",
    source_id: item.id,
    target_id: "ckl:temple",
    connection_type: "uncategorized",
    original_relationship_type: "later-sanctuary-development",
    relationship_mode: "not_recorded",
    direction: "one_way",
    reverse_edge_id: null,
    temporal_layer: "unknown",
    basis: {
      kind: "ckl_related_object",
      parent_object_id: "tabernacle",
      notes: "The Jerusalem temple is a distinct permanent structure.",
    },
  };
  const opened = [];
  const trail = explorer.addEvidenceStep(
    explorer.createTrail({book: "Exodus", chapter: 25, reference: "Exodus 25"}),
    item,
  );
  const view = explorer.renderEvidenceDetail(item, [edge], trail, {
    document: fakeDocument(),
    onFollowConnection: (...args) => opened.push(args),
  });

  const targetButton = descendants(view).find((element) => element.tagName === "BUTTON" && element.textContent.includes("temple"));
  assert.ok(targetButton);
  targetButton.click();
  assert.deepEqual(opened[0][0], {targetId: "temple", title: "temple"});
  assert.equal(opened[0][1].originalRelationshipType, "later-sanctuary-development");
  assert.equal(opened[0][1].id, "tabernacle-temple-edge");
});

test("the rendered evidence trail stops CKL and Scripture navigation at its hop limit", () => {
  const origin = explorer.createTrail({book: "Exodus", chapter: 25, reference: "Exodus 25"});
  const atLimit = {
    ...origin,
    nodes: [origin.nodes[0], {
      kind: "subject",
      id: "ckl:temple",
      subjectId: "temple",
      targetId: "temple",
      label: "Temple",
      relationshipHops: explorer.MAX_RELATIONSHIP_HOPS,
      focusControlId: "",
    }],
    activeIndex: 1,
  };
  const item = {
    id: "ckl:temple#evidence:temple-text",
    parent_object_id: "temple",
    title: "Temple textual evidence",
  };
  const edge = {
    id: "temple-related-edge",
    source_id: item.id,
    target_id: "ckl:presence-theme",
    connection_type: "thematic_relationship",
    original_relationship_type: "related-concept",
    direction: "one_way",
  };
  const evidenceView = explorer.renderEvidenceDetail(item, [edge], atLimit, {
    document: fakeDocument(),
    onFollowConnection() {},
  });
  const subjectView = explorer.renderSubjectDetail({
    id: "temple",
    type: "institution",
    title: "Temple",
    scripture_references: [{reference: "Genesis 1:1", relationship: "related"}],
    related_object_links: [{id: "presence-theme", title: "Presence Theme", relationship: "related-concept"}],
  }, atLimit, {
    document: fakeDocument(),
    knownBooks: [{value: "Genesis", chapters: 50}],
    onOpenPassage() {},
    onFollowSubject() {},
  });

  for (const view of [evidenceView, subjectView]) {
    assert.match(view.textContent, /maximum of 3 relationship hops/i);
    assert.equal(descendants(view).some((element) => element.tagName === "BUTTON" && /Open (?:connected CKL subject|linked passage)/.test(element.textContent)), false);
  }
});

test("evidence detail exposes labelled trail landmarks and keyboard-native controls", () => {
  const trail = explorer.addEvidenceStep(
    explorer.createTrail({book: "Psalm", chapter: 82, reference: "Psalm 82"}),
    {id: "ckl:psalm-82#evidence:assembly", title: "Assembly-language evidence"},
    "overview-item:ckl:psalm-82#evidence:assembly",
  );
  const view = explorer.renderEvidenceDetail(
    {id: "ckl:psalm-82#evidence:assembly", title: "Assembly-language evidence"},
    [],
    trail,
    {document: fakeDocument(), onBack() {}, onReturnToOrigin() {}},
  );
  const nodes = descendants(view);
  const navigation = nodes.find((element) => element.tagName === "NAV");
  const currentStep = nodes.find((element) => element.attributes["aria-current"] === "page");
  const heading = nodes.find((element) => element.dataset.narrativePrimary === "true");
  const buttons = nodes.filter((element) => element.tagName === "BUTTON");

  assert.equal(navigation.attributes["aria-label"], "Evidence trail");
  assert.equal(currentStep.textContent, "Assembly-language evidence");
  assert.equal(heading.attributes.tabindex, "-1");
  assert.equal(buttons.length, 2);
  assert.ok(buttons.every((button) => button.type === "button"));
  assert.ok(buttons.some((button) => button.textContent === "Back to previous trail step"));
  assert.ok(buttons.some((button) => button.textContent.startsWith("Return to Psalm 82")));
});

test("canonical subject identity must match the requested target ID", () => {
  assert.equal(explorer.subjectMatchesId("temple", {id: "temple", type: "place"}), true);
  assert.equal(explorer.subjectMatchesId("temple", {id: "tabernacle", type: "place"}), false);
  assert.equal(explorer.subjectMatchesId("temple", {id: "temple"}), false);
  assert.equal(explorer.subjectMatchesId("tabernacle", {id: "tabernacle", type: "archaeology_compatibility", status: "deprecated"}), false);
});

test("connected CKL detail follows only authored targets and validates Scripture links", () => {
  const origin = explorer.createTrail({book: "Exodus", chapter: 25, reference: "Exodus 25"});
  const evidence = explorer.addEvidenceStep(origin, {
    id: "ckl:tabernacle#evidence:tabernacle-textual-evidence",
    parent_object_id: "exodus",
    title: "Tabernacle evidence",
  });
  const subjectStep = explorer.followSubject(evidence, {targetId: "tabernacle", title: "Tabernacle"}, {
    originalRelationshipType: "authored-object-reference",
  }).state;
  const opened = [];
  const subject = {
    id: "tabernacle",
    type: "institution",
    title: "Tabernacle",
    summary: "A portable sanctuary in Israel's wilderness narrative.",
    confidence: "medium",
    review_status: "in_review",
    content_status: "complete",
    human_review_required: true,
    source_ids: ["exodus-text"],
    sources: [{id: "exodus-text", title: "Exodus", author: "Canonical biblical text", locator: "Exodus 25"}],
    scripture_references: [{reference: "Exodus 25:8-9", relationship: "primary", notes: "The text describes the dwelling."}],
    related_object_links: [{
      id: "temple",
      title: "Temple",
      type: "institution",
      relationship: "later-sanctuary-development",
      notes: "The Jerusalem temple is a distinct permanent structure.",
    }],
  };
  const view = explorer.renderSubjectDetail(subject, subjectStep, {
    document: fakeDocument(),
    knownBooks: [{value: "Exodus", chapters: 40}],
    onFollowSubject: (...args) => opened.push({kind: "subject", args}),
    onOpenPassage: (...args) => opened.push({kind: "passage", args}),
  });
  const buttons = descendants(view).filter((element) => element.tagName === "BUTTON");

  assert.match(view.textContent, /A portable sanctuary in Israel's wilderness narrative/);
  assert.match(view.textContent, /later-sanctuary-development/);
  assert.match(view.textContent, /without upgrading it/);
  assert.match(view.textContent, /Exodus 25:8-9/);
  assert.equal(buttons.length, 2);
  buttons.find((button) => button.textContent.includes("Exodus 25:8-9")).click();
  buttons.find((button) => button.textContent.includes("Temple")).click();
  assert.equal(opened[0].kind, "passage");
  assert.equal(opened[0].args[0].reference, "Exodus 25:8-9");
  assert.deepEqual(opened[1].args[0], {targetId: "temple", title: "Temple"});
  assert.equal(opened[1].args[1].originalRelationshipType, "later-sanctuary-development");
});

test("canonical subject loader fetches only on demand and shares identical pending requests", async () => {
  let requests = 0;
  let resolveRequest;
  const loader = explorer.createSubjectLoader({
    resolveUrl: (url) => url,
    fetcher: (_url, options) => {
      requests += 1;
      assert.equal(options.cache, "no-store");
      return new Promise((resolve) => { resolveRequest = resolve; });
    },
  });

  assert.equal(requests, 0);
  const first = loader.get("presence-theme");
  const second = loader.get("presence-theme");
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(requests, 1);
  resolveRequest({ok: true, status: 200, text: async () => JSON.stringify({id: "presence-theme", type: "theme", title: "Presence Theme"})});
  assert.deepEqual(await first, {id: "presence-theme", type: "theme", title: "Presence Theme"});
  assert.deepEqual(await second, {id: "presence-theme", type: "theme", title: "Presence Theme"});
});

test("canonical subject loader rejects an authoritative response with the wrong identity", async () => {
  const loader = explorer.createSubjectLoader({
    resolveUrl: (url) => url,
    fetcher: async () => ({ok: true, status: 200, text: async () => JSON.stringify({id: "other-object", type: "theme", title: "Wrong target"})}),
  });
  await assert.rejects(loader.get("presence-theme"), /identity did not match/);
});

test("aborting the last subject subscriber cancels the pending target request", async () => {
  let requests = 0;
  let requestedSignal;
  const loader = explorer.createSubjectLoader({
    resolveUrl: (url) => url,
    fetcher: (_url, options) => {
      requests += 1;
      requestedSignal = options.signal;
      return new Promise((_resolve, reject) => {
        options.signal.addEventListener("abort", () => {
          const error = new Error("request aborted");
          error.name = "AbortError";
          reject(error);
        }, {once: true});
      });
    },
  });
  const subscriber = new AbortController();
  const pending = loader.get("presence-theme", subscriber.signal);
  await new Promise((resolve) => setImmediate(resolve));
  subscriber.abort();
  await assert.rejects(pending, {name: "AbortError"});

  assert.equal(requests, 1);
  assert.equal(requestedSignal.aborted, true);
});

test("real NE-5A pilot projections retain their evidence distinctions and exact child identities", () => {
  const fixturePath = (name) => path.join(__dirname, "../fixtures/narrative_explorer/ne5a_baseline", name);
  const readItem = (name, id) => {
    const data = JSON.parse(fs.readFileSync(fixturePath(name), "utf8"));
    const item = data.items.find((candidate) => candidate.id === id);
    assert.ok(item, `expected ${id} in ${name}`);
    return {data, item};
  };
  const render = ({data, item}) => explorer.renderEvidenceDetail(
    item,
    data.connections.filter((edge) => edge.source_id === item.id || edge.target_id === item.id),
    explorer.createTrail({book: data.passage.book, chapter: data.passage.chapter, reference: data.passage.reference}),
    {document: fakeDocument(), knownBooks: [{value: data.passage.book, chapters: 150}]},
  );

  const garden = render(readItem("genesis_2.json", "ckl:genesis#evidence:g2-garden-planting-presence"));
  assert.match(garden.textContent, /geography and identification/i);
  assert.match(garden.textContent, /Eden-as-sacred-space or temple analogies are interpretations/);
  assert.match(garden.textContent, /interpretive_uncertainty/);

  const cherubim = render(readItem("genesis_3.json", "ckl:genesis#evidence:g3-cherubim-biblical-sacred-space-context"));
  assert.match(cherubim.textContent, /ckl:genesis#evidence:g3-cherubim-biblical-sacred-space-context/);
  assert.match(cherubim.textContent, /Scholarly interpretation/);
  assert.match(cherubim.textContent, /Exodus 25:18/);

  const sons = render(readItem("genesis_6.json", "ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions"));
  const watchers = render(readItem("genesis_6.json", "ckl:genesis-flood-postflood-context#evidence:g6-second-temple-watchers-reception"));
  assert.match(sons.textContent, /disputed position/i);
  assert.match(sons.textContent, /major_scholarly_disagreement/);
  assert.match(watchers.textContent, /Later reception/);
  assert.match(watchers.textContent, /attest later interpretation rather than adding details to Genesis/);

  const assembly = render(readItem("psalm_82.json", "ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language"));
  const ugaritic = render(readItem("psalm_82.json", "ckl:ancient-divine-assembly-imagery#evidence:ugaritic-council-comparison"));
  assert.match(assembly.textContent, /Original biblical text · worldview language/);
  assert.match(assembly.textContent, /Primary Observation/);
  assert.match(assembly.textContent, /Scholarly Interpretation/);
  assert.match(ugaritic.textContent, /Ancient comparative literature/);
  assert.match(ugaritic.textContent, /does not decide the referents/);
  assert.match(ugaritic.textContent, /not, by itself, evidence of borrowing, quotation, fulfillment, or dependence/);

  const manuscript = render(readItem("deuteronomy_32.json", "ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant"));
  assert.match(manuscript.textContent, /Manuscript\/textual witness/);
  assert.match(manuscript.textContent, /textual_variant/);
  assert.match(manuscript.textContent, /earliest reading and its conceptual implications remains a textual-critical judgment/);
  assert.match(manuscript.textContent, /ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant/);
});
