const test = require("node:test");
const assert = require("node:assert/strict");

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
