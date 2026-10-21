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
    related_passages: {
      state: "not_represented",
      query_status: "complete",
      reason_code: null,
      description: "No route was returned from this passage pathway. This does not establish that no relationship exists.",
      authored_relationships: [],
      evidence_backed_bridges: [],
    },
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

test("related passage routes show provenance and uncertainty, then use the existing passage trail callback", () => {
  const opened = [];
  const data = projection({
    related_passages: {
      state: "available",
      query_status: "complete",
      reason_code: null,
      description: "Passage routes are available from the records listed here.",
      authored_relationships: [{
        id: "authored:ckl:genesis#evidence:new-creation:Revelation 21:1-5",
        provenance: "authored_ckl_relationship",
        source_passage: "Genesis 1:1-31",
        destination_passage: "Revelation 21:1-5",
        relationship_category: "thematic_relationship",
        original_relationship_type: "canonical-fulfillment",
        source_id: "ckl:genesis#evidence:new-creation",
        target_id: "ckl:new-creation-theme",
        direction: "one_way",
        relationship_mode: "inferred",
        temporal_layer: "later_reception",
        basis: {kind: "ckl_related_object", notes: "Original authored basis."},
        curation: {why: "This is the existing authored CKL pathway.", uncertainty: "This does not assert direct quotation."},
        explanation: "This is the existing authored CKL pathway.",
        uncertainty: "This does not assert direct quotation.",
        supporting_record_ids: ["ckl:genesis#evidence:new-creation"],
        supporting_ckl_sources: [{object_id: "genesis", source_id: "genesis-1-2"}],
      }],
      evidence_backed_bridges: [{
        id: "genesis-1-john-1-creation-word",
        provenance: "ckl_documented_claim",
        source_passage: "Genesis 1:1-5",
        destination_passage: "John 1:1-18",
        relationship_category: "interpretive_association",
        evidence_layer: "thematic_interpretation",
        direction: "interpretive_comparison",
        relationship_mode: "documented_interpretation",
        explanation: "John's prologue places the Logos in the beginning and associates it with creation and life.",
        uncertainty: "The conceptual genealogy is debated; this is not proof of direct borrowing.",
        human_scholarly_approval: "not_recorded",
        supporting_records: [{
          id: "ckl:john#claim:john-logos",
          object_id: "john",
          record_kind: "claim",
          record_id: "john-logos",
          identity_status: "recorded",
          statement: "John's prologue presents the Logos with God in the beginning.",
          certainty: "textually_explicit",
          dispute_status: "major_scholarly_disagreement",
          source_ids: ["john-greek", "boyarin-logos"],
        }],
        supporting_sources: [
          {id: "john-greek", title: "Greek New Testament", source_type: "scripture"},
          {id: "boyarin-logos", title: "The Jewish Gospels", author: "Daniel Boyarin", year: 2012},
        ],
      }],
    },
  });
  const root = explorer.renderOverview(data, {
    document: fakeDocument(),
    knownBooks: [{value: "John", chapters: 21}, {value: "Revelation", chapters: 22}],
    onOpenPassage: (destination, relationship) => opened.push({destination, relationship}),
  });

  assert.ok(descendants(root).some((item) => item.className === "narrative-explorer-passage" && item.textContent === "Current passage: Genesis 1"));
  assert.match(root.textContent, /Related Biblical Passages/);
  assert.match(root.textContent, /Existing authored CKL relationships/);
  assert.match(root.textContent, /Original relationship type: canonical-fulfillment/);
  assert.match(root.textContent, /Original CKL relationship: ckl:genesis#evidence:new-creation → ckl:new-creation-theme · one_way/);
  assert.match(root.textContent, /CKL-documented passage route/);
  assert.match(root.textContent, /Interpretive association/);
  assert.match(root.textContent, /major_scholarly_disagreement/);
  assert.match(root.textContent, /Human scholarly approval: not recorded/);
  assert.match(root.textContent, /ckl:john#claim:john-logos/);
  assert.match(root.textContent, /The Jewish Gospels/);
  const button = descendants(root).find((item) => item.tagName === "BUTTON" && item.textContent.includes("John 1:1-18"));
  assert.ok(button, "the exact destination passage should be an accessible route button");
  button.click();

  assert.equal(opened.length, 1);
  assert.equal(opened[0].destination.reference, "John 1:1-18");
  assert.equal(opened[0].destination.startVerse, 1);
  assert.equal(opened[0].destination.endVerse, 18);
  assert.equal(opened[0].relationship.provenance, "ckl_documented_claim");
  assert.equal(opened[0].relationship.uncertainty, "The conceptual genealogy is debated; this is not proof of direct borrowing.");
  assert.deepEqual(opened[0].relationship.supportingRecordIds, ["ckl:john#claim:john-logos"]);

  const originTrail = explorer.createTrail({book: "Genesis", chapter: 1, reference: "Genesis 1"});
  const followed = explorer.followPassage(originTrail, {
    reference: opened[0].destination.reference,
    selection: {
      book: opened[0].destination.book,
      chapter: opened[0].destination.chapter,
      startVerse: opened[0].destination.startVerse,
      endVerse: opened[0].destination.endVerse,
      reference: opened[0].destination.reference,
    },
  }, opened[0].relationship, "related-passage:genesis-1-john-1-creation-word");
  assert.equal(followed.error, null);
  const destinationView = explorer.renderOverview(projection({
    passage: {reference: "John 1:1-18", book: "John", chapter: 1, verse_start: 1, verse_end: 18, scope: "verse_range"},
  }), {document: fakeDocument(), trail: followed.state});
  assert.ok(descendants(destinationView).some((item) => item.className === "narrative-explorer-passage" && item.textContent === "Current passage: John 1:1-18"));
  assert.match(destinationView.textContent, /Connection used to open this passage/);
  assert.match(destinationView.textContent, /CKL-documented claim/);
  assert.match(destinationView.textContent, /ckl:john#claim:john-logos/);
  assert.match(destinationView.textContent, /The conceptual genealogy is debated/);
  const returned = explorer.returnToOrigin(followed.state);
  assert.equal(returned.nodes[returned.activeIndex].reference, "Genesis 1");
});

test("incomplete related passage coverage never reads as proof that a route does not exist", () => {
  const view = explorer.renderOverview(projection({
    related_passages: {
      state: "unknown",
      query_status: "failed",
      reason_code: "bridge_support_unavailable",
      description: "The CKL lookup did not finish; more passage routes may be available.",
      authored_relationships: [],
      evidence_backed_bridges: [],
    },
  }), {document: fakeDocument()});

  assert.match(view.textContent, /Related Biblical Passages/);
  assert.match(view.textContent, /lookup did not finish/);
  assert.match(view.textContent, /more passage routes may be available/);
  assert.doesNotMatch(view.textContent, /No biblical passage connection exists/);
});

test("related passage routes disclose long lists in keyboard-operable pages", () => {
  const routes = Array.from({length: 6}, (_value, index) => ({
    id: `route-${index + 1}`,
    provenance: "ckl_documented_claim",
    source_passage: "Genesis 1:1-5",
    destination_passage: `John 1:${index + 1}`,
    relationship_category: "interpretive_association",
    evidence_layer: "thematic_interpretation",
    direction: "interpretive_comparison",
    relationship_mode: "documented_interpretation",
    explanation: `Documented route ${index + 1}.`,
    uncertainty: "The relationship remains interpretive.",
    human_scholarly_approval: "not_recorded",
    supporting_records: [],
    supporting_sources: [],
  }));
  const view = explorer.renderOverview(projection({
    related_passages: {
      state: "available",
      query_status: "complete",
      description: "Passage routes are available from the records listed here.",
      authored_relationships: [],
      evidence_backed_bridges: routes,
    },
  }), {document: fakeDocument()});
  const list = descendants(view).find((element) => element.className === "narrative-explorer-related-passage-list");
  const more = descendants(view).find((element) => element.className.includes("narrative-explorer-more-passages"));

  assert.equal(list.children.length, 4);
  assert.ok(more);
  assert.equal(more.type, "button");
  more.click();
  assert.equal(list.children.length, 6);
  assert.equal(more.hidden, true);
});

test("reverse passage navigation displays the original source-to-receiver direction", () => {
  const view = explorer.renderOverview(projection({
    passage: {reference: "John 1:1-18", book: "John", chapter: 1, verse_start: 1, verse_end: 18, scope: "verse_range"},
    related_passages: {
      state: "available",
      query_status: "complete",
      description: "Passage routes are available from the records listed here.",
      authored_relationships: [],
      evidence_backed_bridges: [{
        id: "genesis-1-john-1-creation-word",
        provenance: "ckl_documented_claim",
        source_passage: "John 1:1-18",
        destination_passage: "Genesis 1:1-5",
        source_text_passage: "Genesis 1:1-5",
        receiving_text_passage: "John 1:1-18",
        relationship_category: "interpretive_association",
        evidence_layer: "thematic_interpretation",
        direction: "source_to_receiving_text",
        relationship_mode: "documented_interpretation",
        explanation: "John's prologue places the Logos with God in the beginning.",
        uncertainty: "Conceptual genealogy is debated.",
        human_scholarly_approval: "not_recorded",
        supporting_records: [],
        supporting_sources: [],
      }],
    },
  }), {document: fakeDocument()});

  assert.match(view.textContent, /Textual direction: Genesis 1:1-5 → John 1:1-18/);
  assert.match(view.textContent, /this route can be followed from either passage/i);
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
    {id: "maps:00-eden-safe", title: "Synthetic test fixture: identified physical site", coordinates_displayable: true},
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
  assert.match(root.textContent, /No linked records found/);
  assert.match(root.textContent, /Maps: 3 source records found/);
  assert.match(root.textContent, /Archaeology sources: no records were found for this passage/);
  assert.equal(narrativePreviewList.children.length, 2);
  assert.match(narrativeCard.textContent, /80 linked records/);
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

test("physical and conceptual geography details keep their evidence domains distinct", () => {
  const physical = {
    ...projection().items[1],
    id: "maps:pilot-place",
    object_id: "pilot-place",
    title: "Negeb",
    domain: "maps",
    record_kind: "map_place",
    geography_kind: "physical_region",
    physical_identification_status: "unidentified",
    place_identification_confidence: "low",
    dispute_status: "identification_uncertainty",
    coordinates_displayable: false,
    coordinate_display_reason: "identification_unresolved",
    geometry_displayable: false,
    geometry_display_reason: "no_geometry",
    stored_coordinates: {latitude: 33.4, longitude: 35.8},
    stored_geometry: {type: "Point", coordinates: [35.8, 33.4]},
    source_metadata: {
      ancient_names: ["Negeb (ancient region)"],
      modern_names: ["Negev"],
      modern_location: "Southern Levant",
      ancient_region: "Southern Levant",
      territories: ["Judah"],
      historical_periods: ["Iron Age"],
      source_name: "Test map catalog",
      source_url: "https://example.test/map-source",
      license: "CC BY 4.0",
    },
    original_relationship_types: ["direct"],
    applicable_passage_anchors: [{reference: "Joshua 1:4", relationship: "direct"}],
    related_passages: ["Joshua 1:4"],
    section_ids: ["biblical_geography"],
    navigation: {kind: "map_place", target_id: "pilot-place", selection_required: true},
  };
  const concepts = [
    ["sacred_space_interpretation", "Sacred-space interpretation"],
    ["sacred_space_guarding_context", "Sacred-space guarding context"],
    ["divine_assembly_text", "Heavenly assembly language"],
    ["ancient_cosmology_comparison", "Ancient cosmology comparison"],
    ["disputed_divine_beings_interpretation", "Divine beings with disputed interpretation"],
  ].map(([role, title], index) => ({
    ...projection().items[0],
    id: `ckl:concept-${index}`,
    title,
    domain: "ckl",
    cosmic_geography_role: role,
    section_ids: ["divine_council_cosmic_geography"],
    navigation: null,
  }));
  const keywordTrap = {
    ...projection().items[0],
    id: "ckl:keyword-trap",
    title: "Temple and mountain references",
    cosmic_geography_role: null,
    section_ids: ["divine_council_cosmic_geography"],
    navigation: null,
  };
  const data = projection({
    sections: projection().sections.map((entry) => entry.id === "biblical_geography"
      ? {...entry, state: "available", item_ids: [physical.id]}
      : entry.id === "divine_council_cosmic_geography"
        ? {...entry, state: "available", item_ids: [...concepts, keywordTrap].map((item) => item.id)}
        : {...entry, item_ids: []}),
    items: [physical, ...concepts, keywordTrap],
  });

  const view = explorer.renderOverview(data, {document: fakeDocument()});
  const cosmicCard = descendants(view).find((element) => element.dataset.sectionId === "divine_council_cosmic_geography");
  cosmicCard.children.find((element) => element.className.includes("narrative-explorer-inspect")).click();
  const lines = view.textContent;
  assert.match(lines, /Original map\/record ID: pilot-place/);
  assert.match(lines, /Ancient name: Negeb \(ancient region\)/);
  assert.match(lines, /Modern name: Negev/);
  assert.match(lines, /Modern location: Southern Levant/);
  assert.match(lines, /Region: Southern Levant/);
  assert.match(lines, /Territory: Judah/);
  assert.match(lines, /Historical period: Iron Age/);
  assert.match(lines, /Recorded map provenance: Source: Test map catalog · Source URL: https:\/\/example\.test\/map-source · License: CC BY 4\.0/);
  assert.match(lines, /Physical identification status: unidentified/);
  assert.match(lines, /Place identification confidence: low/);
  assert.match(lines, /Dispute status: identification_uncertainty/);
  assert.match(lines, /Passage relationship: Joshua 1:4 · direct/);
  assert.match(lines, /Original relationship types: direct/);
  assert.match(lines, /Map point withheld: identification_unresolved/);
  assert.match(lines, /Sacred-space interpretation/);
  assert.match(lines, /Sacred-space guarding context/);
  assert.match(lines, /Heavenly assembly language/);
  assert.match(lines, /Ancient cosmology comparison/);
  assert.match(lines, /Divine beings with disputed interpretation/);
  assert.match(lines, /not a literal map of heavenly realms and does not establish physical locations/i);
  assert.match(lines, /does not by itself prove borrowing/i);
  assert.doesNotMatch(lines, /33\.4|35\.8|\[35\.8,\s*33\.4\]|latitude|longitude/i);
  assert.doesNotMatch(lines, /Temple and mountain references.*(?:Sacred-space|Heavenly assembly)/);
});

test("unavailable states are announced without turning a network failure into an empty result", () => {
  const failure = explorer.renderFailure("offline", {reference: "Exodus 3"}, {document: fakeDocument()});

  assert.equal(failure.attributes.role, "alert");
  assert.match(failure.textContent, /Not available offline/);
  assert.match(failure.textContent, /No saved Narrative Explorer projection is available for Exodus 3/);
  assert.match(failure.textContent, /Reconnect and try again/);
});

test("overview exposes a reader-facing evidence action with the exact projected item identity", () => {
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

test("authored evidence relationships resolve the exact eligible target and count one hop", () => {
  const source = {
    id: "ckl:creation#evidence:source-item",
    parent_object_id: "creation",
    record_kind: "evidence",
    evidence_id: "source-item",
    local_id: "source-item",
    title: "Source evidence",
    applicable_passage_anchors: [{reference: "Genesis 1:1-2:3", relationship: "direct"}],
    source_ids: ["source-text"],
  };
  const target = {
    id: "ckl:creation#evidence:target-item",
    parent_object_id: "creation",
    record_kind: "evidence",
    evidence_id: "target-item",
    local_id: "target-item",
    title: "Target evidence",
    applicable_passage_anchors: [{reference: "Genesis 1:1-2:3", relationship: "comparative"}],
    description: "Recorded comparative evidence.",
    source_ids: ["target-study"],
    sources: [{id: "target-study", bibliographic_details: {title: "Comparative Study", author: "A. Scholar", year: 2013}}],
    certainty: "probable",
    dispute_status: "major_scholarly_disagreement",
    review_status: "in_review",
    content_status: "draft",
  };
  const edge = {
    id: "evidence-edge",
    source_id: source.id,
    target_id: target.id,
    connection_type: "uncategorized",
    original_relationship_type: "compared-with",
    relationship_mode: "not_recorded",
    direction: "one_way",
    reverse_edge_id: null,
    temporal_layer: "unknown",
    basis: {
      kind: "ckl_related_evidence",
      parent_object_id: "creation",
      local_record_id: "source-item",
      target_evidence_id: "target-item",
      target_resolution_status: "eligible",
      notes: "The comparison is recorded as secondary evidence.",
    },
    curation: {
      classification: "interpretive_association",
      textual_observation: "The two evidence records use separate corpora.",
      why: "Readers can inspect the comparison without treating it as borrowing.",
      supporting_passages: ["Psalm 82:1-8"],
      supporting_comparative_material: [{
        kind: "ancient_comparative_literature",
        reference: "KTU 1.1-1.2",
        source_id: "smith-ugaritic-baal-cycle-1994",
      }],
      supporting_records: [source.id, target.id],
      supporting_ckl_sources: [{
        object_id: "creation",
        source_id: "comparison-source",
        title: "A Comparative Study",
        author: "A. Scholar",
        year: 2013,
      }],
      uncertainty: "Comparison does not establish literary dependence.",
      curation_confidence: "moderate",
      curation_status: "curated_for_explorer",
      ckl_evidence_certainty: {
        status: "recorded",
        records: [
          {record_id: source.id, certainty: "textually_explicit", dispute_status: "interpretive_uncertainty"},
          {record_id: target.id, certainty: "probable", dispute_status: "major_scholarly_disagreement"},
        ],
      },
      human_scholarly_approval: "not_recorded",
    },
  };
  const trail = explorer.addEvidenceStep(
    explorer.createTrail({book: "Genesis", chapter: 1, reference: "Genesis 1"}),
    source,
    "overview-item:source",
  );
  assert.equal(explorer.currentRelationshipHops(trail), 0);
  const opened = [];
  const view = explorer.renderEvidenceDetail(source, [edge], trail, {
    document: fakeDocument(),
    resolveEvidenceTarget: (id) => id === target.id ? target : null,
    onFollowEvidence: (...args) => opened.push(args),
  });
  const button = descendants(view).find((element) => element.tagName === "BUTTON" && element.textContent.includes("Target evidence"));

  assert.ok(button);
  assert.match(view.textContent, /Recorded CKL relationships/);
  assert.match(view.textContent, /recorded CKL evidence relationship.*compared-with/i);
  assert.match(view.textContent, /Why this connects: Readers can inspect the comparison without treating it as borrowing/);
  assert.match(view.textContent, /Supporting Scripture passages: Psalm 82:1-8/);
  assert.match(view.textContent, /Ancient comparative material \(not Scripture\): KTU 1.1-1.2/);
  assert.match(view.textContent, /A. Scholar, 2013/);
  assert.match(view.textContent, /Interpretive uncertainty: Comparison does not establish literary dependence/);
  assert.match(view.textContent, /Curation confidence: moderate/);
  assert.match(view.textContent, /CKL evidence certainty:.*textually_explicit.*probable/);
  assert.match(view.textContent, /Human scholarly approval: not recorded/);
  assert.match(view.textContent, /Curation status: curated_for_explorer/);
  button.click();
  assert.equal(opened.length, 1);
  assert.equal(opened[0][0], target);
  assert.equal(opened[0][1].basisKind, "ckl_related_evidence");
  assert.equal(opened[0][1].notes, "The comparison is recorded as secondary evidence.");
  assert.equal(opened[0][2].dataset.narrativeFocusId, "connection:evidence-edge");
  assert.equal(explorer.followEvidence(trail, target, {...opened[0][1], sourceId: "ckl:other-parent#evidence:source-item"}).error, "invalid_relationship");

  const followed = explorer.followEvidence(trail, opened[0][0], opened[0][1], opened[0][2].dataset.narrativeFocusId);
  assert.equal(followed.error, null);
  assert.equal(followed.state.nodes.at(-1).id, target.id);
  assert.equal(followed.state.nodes.at(-1).relationshipHops, 1);
  assert.equal(followed.state.nodes.at(-1).relationship.basisKind, "ckl_related_evidence");
  assert.equal(followed.state.nodes.at(-1).relationship.curation.classification, "interpretive_association");
  const detail = explorer.renderEvidenceDetail(target, [], followed.state, {document: fakeDocument()});
  assert.match(detail.textContent, /Opened through recorded CKL evidence relationship: compared-with/i);
  assert.match(detail.textContent, /This recorded relationship is not a Scripture anchor/i);
  assert.match(detail.textContent, /Recorded evidence IDs: ckl:creation#evidence:source-item → ckl:creation#evidence:target-item/);
  assert.match(detail.textContent, /Destination resolution: eligible/);
  assert.match(detail.textContent, /does not establish literary borrowing or dependence/i);
  assert.match(detail.textContent, /Why this connects: Readers can inspect the comparison without treating it as borrowing/);
  assert.match(detail.textContent, /Human scholarly approval: not recorded/);
  assert.match(detail.textContent, /Curation confidence: moderate/);
  assert.match(detail.textContent, /probable/);
  assert.match(detail.textContent, /major_scholarly_disagreement/);
  assert.match(detail.textContent, /in_review/);
  assert.match(detail.textContent, /draft/);
  assert.match(detail.textContent, /Source identifier: target-study/);
  assert.match(detail.textContent, /Comparative Study/);
});

test("projected curation reaches the subject-detail consumer without confusing unknown temporal metadata", () => {
  const curation = {
    classification: "later_canonical_reception",
    textual_observation: "Acts 2:22-36 receives Psalms 16 and 110 in a resurrection and exaltation argument.",
    why: "The connection records a later Christian reception of Israel's Scriptures.",
    applicable_passages: ["Acts 2:22-36"],
    supporting_passages: ["Psalm 16:8-11", "Psalm 110:1-7", "Acts 2:22-36"],
    supporting_comparative_material: [],
    supporting_records: ["ckl:messiah-theme#source:psalm-110"],
    supporting_ckl_sources: [{object_id: "messiah-theme", source_id: "psalm-110", title: "Psalm 110"}],
    uncertainty: "Acts 2 is a later Christian interpretation; it does not settle the Psalms' original referent.",
    curation_confidence: "moderate",
    curation_status: "curated_for_explorer",
    ckl_evidence_certainty: {status: "not_recorded", records: []},
    human_scholarly_approval: "not_recorded",
  };
  const subject = {
    id: "messiah-theme",
    title: "Messiah theme",
    related_object_links: [{
      id: "resurrection-theme",
      title: "Resurrection theme",
      type: "theme",
      relationship: "vindication-pattern",
      notes: "suffering leads to vindication",
      weight: 8,
    }],
  };
  const apiEdge = {
    id: "ckl:messiah-theme->ckl:resurrection-theme:vindication-pattern",
    source_id: "ckl:messiah-theme",
    target_id: "ckl:resurrection-theme",
    connection_type: "later_canonical_reception",
    original_relationship_type: "vindication-pattern",
    direction: "one_way",
    reverse_edge_id: null,
    relationship_mode: "not_recorded",
    temporal_layer: "unknown",
    basis: {kind: "ckl_related_object", notes: "suffering leads to vindication", weight: 8},
    curation,
  };
  const decorated = explorer.applyProjectionCurationsToSubject(subject, {connections: [apiEdge]});
  assert.equal(decorated.related_object_links[0].curation.classification, "later_canonical_reception");

  const followed = [];
  const openedPassages = [];
  const view = explorer.renderSubjectDetail(decorated, explorer.createTrail({
    book: "Acts", chapter: 2, startVerse: 22, endVerse: 36, reference: "Acts 2:22-36",
  }), {
    document: fakeDocument(),
    knownBooks: [{value: "Acts", chapters: 28}, {value: "Psalms", chapters: 150}],
    onOpenPassage: (...args) => openedPassages.push(args),
    onFollowSubject: (...args) => followed.push(args),
  });
  assert.match(view.textContent, /Curated classification: Later canonical reception/);
  assert.match(view.textContent, /Curated passage scope: Acts 2:22-36/);
  assert.match(view.textContent, /Original CKL temporal layer: unknown/);
  assert.match(view.textContent, /separate curated relationship classification/i);
  assert.match(view.textContent, /Curation confidence: moderate/);
  assert.match(view.textContent, /CKL evidence certainty: not recorded/i);
  assert.match(view.textContent, /Human scholarly approval: not recorded/);

  const passageButtons = descendants(view).filter((element) => element.tagName === "BUTTON"
    && element.textContent.startsWith("Open supporting passage:"));
  assert.deepEqual(passageButtons.map((button) => button.textContent), [
    "Open supporting passage: Psalms 16:8-11",
    "Open supporting passage: Psalms 110:1-7",
  ]);
  assert.doesNotMatch(view.textContent, /Open supporting passage: Acts 2:22-36/);
  passageButtons[0].click();
  assert.equal(openedPassages.length, 1);
  assert.equal(openedPassages[0][0].reference, "Psalms 16:8-11");
  assert.equal(openedPassages[0][1].sourceId, apiEdge.source_id);
  assert.equal(openedPassages[0][1].targetId, apiEdge.target_id);
  assert.equal(openedPassages[0][1].curation.classification, "later_canonical_reception");

  const button = descendants(view).find((element) => element.tagName === "BUTTON" && element.textContent.includes("Resurrection theme"));
  assert.ok(button);
  button.click();
  assert.equal(followed.length, 1);
  assert.equal(followed[0][1].curation.classification, "later_canonical_reception");
  assert.equal(followed[0][1].temporal_layer, "unknown");
});

test("curated CKL relationships open their exact supporting Scripture passages", () => {
  const passages = [
    {reference: "Isaiah 43:16-21", book: "Isaiah", chapters: 66},
    {reference: "Isaiah 40:1-11", book: "Isaiah", chapters: 66},
  ];
  const opened = [];
  const trail = explorer.createTrail({
    book: "Genesis",
    chapter: 1,
    reference: "Genesis 1",
  });
  const curation = {
    classification: "thematic_relationship",
    textual_observation: "Exodus 14 narrates deliverance through the sea; Isaiah 43:16-21 recalls YHWH making a way through the sea and then announces a new thing.",
    why: "The exact textual route shows how Isaiah reuses exodus memory to describe a new deliverance and return.",
    applicable_passages: ["Exodus 14:21-31"],
    supporting_passages: ["Exodus 14:21-31", ...passages.map((passage) => passage.reference)],
    supporting_comparative_material: [],
    supporting_records: [],
    supporting_ckl_sources: [
      {object_id: "the-exodus", source_id: "exodus-1-15"},
      {object_id: "the-exodus", source_id: "isaiah-43"},
      {object_id: "new-exodus-theme", source_id: "isaiah-40"},
      {object_id: "new-exodus-theme", source_id: "new-exodus-theme-historical-orientation"},
    ],
    uncertainty: "New Exodus is a useful scholarly description for this cluster of images, not a quotation or a settled label for every restoration passage. The authored note in Christ is a later theological reading and is not presented as Isaiah’s original historical setting or claim.",
    curation_confidence: "moderate",
    curation_status: "curated_for_explorer",
    ckl_evidence_certainty: {status: "not_recorded", records: []},
    human_scholarly_approval: "not_recorded",
  };
  const edge = {
    id: "ckl:the-exodus->ckl:new-exodus-theme:fulfillment-framework",
    source_id: "ckl:the-exodus",
    target_id: "ckl:new-exodus-theme",
    connection_type: "thematic_relationship",
    original_relationship_type: "fulfillment-framework",
    direction: "one_way",
    reverse_edge_id: null,
    temporal_layer: "unknown",
    basis: {kind: "ckl_related_object", notes: "new exodus in Christ", weight: 9},
    curation,
  };
  const item = {
    id: "ckl:the-exodus",
    object_id: "the-exodus",
    record_kind: "object",
    title: "The Exodus",
    passage_anchors: [{reference: "Exodus 14:21-31", relationship: "primary"}],
    applicable_passage_anchors: [{reference: "Exodus 14:21-31", relationship: "primary"}],
  };
  const view = explorer.renderEvidenceDetail(item, [edge], trail, {
    document: fakeDocument(),
    knownBooks: passages.map(({book, chapters}) => ({value: book, chapters})),
    onOpenPassage: (...args) => opened.push(args),
  });

  assert.match(view.textContent, /Curated passage scope: Exodus 14:21-31/);
  assert.match(view.textContent, /CKL source records:.*the-exodus\/isaiah-43/);
  assert.match(view.textContent, /Interpretive uncertainty: New Exodus is a useful scholarly description/);
  assert.match(view.textContent, /Human scholarly approval: not recorded/);
  assert.match(view.textContent, /Source subject: the-exodus · Target subject: new-exodus-theme · Direction: the-exodus → new-exodus-theme \(one-way\)/);

  const controls = descendants(view).filter((element) => element.tagName === "BUTTON"
    && element.textContent.startsWith("Open supporting passage:"));
  assert.equal(controls.length, passages.length);
  for (const passage of passages) {
    const canonicalReference = passage.reference === "Psalm 82:1-8" ? "Psalms 82:1-8" : passage.reference;
    const control = controls.find((element) => element.textContent.endsWith(canonicalReference));
    assert.ok(control, `missing navigation for ${passage.reference}`);
    control.click();
    const [destination, relationship] = opened.at(-1);
    assert.equal(destination.reference, canonicalReference);
    assert.equal(relationship.sourceId, edge.source_id);
    assert.equal(relationship.targetId, edge.target_id);
    assert.equal(relationship.originalRelationshipType, edge.original_relationship_type);
    assert.equal(relationship.direction, "one_way");
    assert.equal(relationship.notes, edge.basis.notes);
    assert.equal(relationship.curation.classification, curation.classification);
  }
});

test("filtered, unavailable, invalid, and mismatched evidence targets never expose target content", () => {
  const source = {
    id: "ckl:parent#evidence:source",
    parent_object_id: "parent",
    record_kind: "evidence",
    evidence_id: "source",
    local_id: "source",
    title: "Source item",
    applicable_passage_anchors: [{reference: "Genesis 6:1-4", relationship: "direct"}],
  };
  const hiddenTarget = {
    id: "ckl:parent#evidence:target",
    parent_object_id: "parent",
    record_kind: "evidence",
    evidence_id: "target",
    local_id: "target",
    title: "Hidden target content",
  };
  const trail = explorer.addEvidenceStep(
    explorer.createTrail({book: "Genesis", chapter: 6, reference: "Genesis 6"}),
    source,
  );
  for (const [status, expected] of [
    ["filtered", /filtered from this passage projection/i],
    ["unavailable", /target could not be resolved in the current lookup/i],
    ["invalid", /recorded target ID is invalid/i],
    [undefined, /target cannot be verified from the current projection/i],
  ]) {
    let resolutionCalls = 0;
    const edge = {
      id: `edge-${status || "unknown"}`,
      source_id: source.id,
      target_id: hiddenTarget.id,
      original_relationship_type: "compared-with",
      direction: "one_way",
      basis: {
        kind: "ckl_related_evidence",
        parent_object_id: "parent",
        local_record_id: "source",
        target_evidence_id: "target",
        ...(status ? {target_resolution_status: status} : {}),
      },
    };
    const view = explorer.renderEvidenceDetail(source, [edge], trail, {
      document: fakeDocument(),
      resolveEvidenceTarget: () => { resolutionCalls += 1; return hiddenTarget; },
      onFollowEvidence() {},
    });
    assert.match(view.textContent, expected);
    assert.doesNotMatch(view.textContent, /Hidden target content/);
    assert.equal(descendants(view).some((element) => element.tagName === "BUTTON" && /Open linked evidence/.test(element.textContent)), false);
    assert.equal(resolutionCalls, 0);
  }

  const wrongParent = {...hiddenTarget, id: "ckl:other-parent#evidence:target", parent_object_id: "other-parent"};
  const edge = {
    id: "edge-wrong-parent",
    source_id: source.id,
    target_id: hiddenTarget.id,
    original_relationship_type: "compared-with",
    direction: "one_way",
    basis: {
      kind: "ckl_related_evidence",
      parent_object_id: "parent",
      local_record_id: "source",
      target_evidence_id: "target",
      target_resolution_status: "eligible",
    },
  };
  const wrongParentView = explorer.renderEvidenceDetail(source, [edge], trail, {
    document: fakeDocument(),
    resolveEvidenceTarget: () => wrongParent,
    onFollowEvidence() {},
  });
  assert.match(wrongParentView.textContent, /exact parent-qualified target could not be verified/i);
  assert.doesNotMatch(wrongParentView.textContent, /Hidden target content/);
});

test("evidence relationship navigation preserves edge direction, cycles, and the three-hop limit", () => {
  const source = {
    id: "ckl:parent#evidence:source",
    parent_object_id: "parent",
    record_kind: "evidence",
    evidence_id: "source",
    local_id: "source",
    title: "Source",
    applicable_passage_anchors: [{reference: "Genesis 1:1", relationship: "direct"}],
  };
  const reverse = {...source, id: "ckl:parent#evidence:reverse", evidence_id: "reverse", local_id: "reverse", title: "Reverse"};
  const incoming = {
    id: "incoming-edge",
    source_id: source.id,
    target_id: reverse.id,
    original_relationship_type: "supports",
    direction: "one_way",
    basis: {kind: "ckl_related_evidence", parent_object_id: "parent", local_record_id: "source", target_evidence_id: "reverse", target_resolution_status: "eligible"},
  };
  const incomingView = explorer.renderEvidenceDetail(reverse, [incoming], explorer.createTrail({book: "Genesis", chapter: 1, reference: "Genesis 1"}), {
    document: fakeDocument(),
    resolveEvidenceTarget: () => source,
    onFollowEvidence() {},
  });
  assert.match(incomingView.textContent, /does not create a reverse navigation edge/i);
  assert.equal(descendants(incomingView).some((element) => element.tagName === "BUTTON" && /Open linked evidence/.test(element.textContent)), false);

  const forwardReciprocal = {...incoming, direction: "reciprocal", reverse_edge_id: "reverse-edge"};
  const reverseEdge = {
    ...incoming,
    id: "reverse-edge",
    source_id: reverse.id,
    target_id: source.id,
    direction: "reciprocal",
    reverse_edge_id: "incoming-edge",
    basis: {kind: "ckl_related_evidence", parent_object_id: "parent", local_record_id: "reverse", target_evidence_id: "source", target_resolution_status: "eligible"},
  };
  const reciprocalOpened = [];
  const reciprocalView = explorer.renderEvidenceDetail(reverse, [forwardReciprocal, reverseEdge], explorer.createTrail({book: "Genesis", chapter: 1, reference: "Genesis 1"}), {
    document: fakeDocument(),
    resolveEvidenceTarget: () => source,
    onFollowEvidence: (...args) => reciprocalOpened.push(args),
  });
  const reciprocalButton = descendants(reciprocalView).find((element) => element.tagName === "BUTTON" && element.textContent.includes("Source"));
  assert.ok(reciprocalButton, "an independently verified authored reverse edge remains navigable");
  reciprocalButton.click();
  assert.equal(reciprocalOpened[0][0], source);

  const direct = explorer.addEvidenceStep(explorer.createTrail({book: "Genesis", chapter: 1, reference: "Genesis 1"}), source);
  const forwardRelationship = {
    id: "incoming-edge",
    sourceId: source.id,
    targetId: reverse.id,
    originalRelationshipType: "supports",
    direction: "one_way",
    basisKind: "ckl_related_evidence",
    parentObjectId: "parent",
    localRecordId: "source",
    targetEvidenceId: "reverse",
    targetResolutionStatus: "eligible",
  };
  const reverseRelationship = {
    id: "reverse-edge",
    sourceId: reverse.id,
    targetId: source.id,
    originalRelationshipType: "supports",
    direction: "reciprocal",
    basisKind: "ckl_related_evidence",
    parentObjectId: "parent",
    localRecordId: "reverse",
    targetEvidenceId: "source",
    targetResolutionStatus: "eligible",
  };
  const visited = explorer.followEvidence(direct, reverse, forwardRelationship);
  assert.equal(visited.error, null);
  assert.equal(explorer.followEvidence(visited.state, source, reverseRelationship).error, "cycle");
  const atLimit = {...visited.state, nodes: visited.state.nodes.map((node, index, nodes) => index === nodes.length - 1 ? {...node, relationshipHops: explorer.MAX_RELATIONSHIP_HOPS} : node)};
  assert.equal(explorer.followEvidence(atLimit, source, reverseRelationship).error, "depth_limit");
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
  const psalmBooks = [{value: "Psalms", chapters: 150}];
  assert.deepEqual(explorer.validateScriptureReference("Psalm 82:1-8", psalmBooks), {
    valid: true,
    book: "Psalms",
    chapter: 82,
    startVerse: 1,
    endVerse: 8,
    reference: "Psalms 82:1-8",
  });
  assert.deepEqual(explorer.validateScriptureReference("Psalms 82:1-8", psalmBooks), {
    valid: true,
    book: "Psalms",
    chapter: 82,
    startVerse: 1,
    endVerse: 8,
    reference: "Psalms 82:1-8",
  });
  assert.equal(explorer.validateScriptureReference("Unknown 1:1", books).valid, false);
  assert.equal(explorer.validateScriptureReference("John 22:1", books).valid, false);
  assert.equal(explorer.validateScriptureReference("John 1:8-3", books).valid, false);
  assert.equal(explorer.validateScriptureReference("John 1:0", books).valid, false);
});

test("Psalm anchor navigation canonicalizes the reader destination and preserves its CKL reference", () => {
  const data = projection();
  const item = {
    ...data.items[1],
    passage_anchors: [{
      reference: "Psalm 82:1-8",
      relationship: "direct",
      temporal_relation: "contemporary",
      relevance_rationale: "The recorded anchor remains attached to the source passage.",
    }],
    applicable_passage_anchors: [],
  };
  const trail = explorer.createTrail({book: "Deuteronomy", chapter: 32, reference: "Deuteronomy 32:8-9"});
  const opened = [];
  const view = explorer.renderEvidenceDetail(item, [], trail, {
    document: fakeDocument(),
    knownBooks: [{value: "Deuteronomy", chapters: 34}, {value: "Psalms", chapters: 150}],
    onOpenPassage: (...args) => opened.push(args),
  });
  const link = descendants(view).find((element) => element.tagName === "BUTTON"
    && element.textContent === "Open Psalms 82:1-8");
  const sourceReference = descendants(view).find((element) => element.tagName === "P"
    && element.textContent.startsWith("Psalm 82:1-8"));

  assert.ok(link, "the singular CKL spelling should produce a canonical reader link");
  assert.ok(sourceReference, "the original CKL reference remains visible");
  assert.equal(item.passage_anchors[0].reference, "Psalm 82:1-8");
  link.click();
  assert.equal(opened.length, 1);
  assert.equal(opened[0][0].reference, "Psalms 82:1-8");
  assert.equal(opened[0][1].anchor, "Psalm 82:1-8");
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
    assert.match(view.textContent, /connection trail has reached its 3-link limit/i);
    assert.match(view.textContent, /Connection trail: 3 of 3 links followed/i);
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
  assert.match(garden.textContent, /geography and place identification/i);
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
  assert.match(watchers.textContent, /does not establish that reception as the earlier passage's original meaning/i);
  assert.match(watchers.textContent, /CKL Scripture link is marked contemporary/i);

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

test("the real Genesis 1 evidence pair preserves source, uncertainty, bibliography, and historical qualifications", () => {
  const data = JSON.parse(fs.readFileSync(path.join(
    __dirname,
    "../fixtures/narrative_explorer/ne5a_baseline/genesis_1.json",
  ), "utf8"));
  const sourceId = "ckl:mesopotamian-creation-and-flood-comparisons#evidence:genesis-ordered-worldview-observation";
  const targetId = "ckl:mesopotamian-creation-and-flood-comparisons#evidence:enuma-elish-cosmic-ordering-comparison";
  const source = data.items.find((item) => item.id === sourceId);
  const target = data.items.find((item) => item.id === targetId);
  const connection = data.connections.find((edge) => edge.source_id === sourceId && edge.target_id === targetId);
  const eligibleConnection = {...connection, basis: {...connection.basis, target_resolution_status: "eligible"}};
  const trail = explorer.addEvidenceStep(
    explorer.createTrail({book: "Genesis", chapter: 1, reference: "Genesis 1"}),
    source,
  );
  let followed = null;
  const sourceView = explorer.renderEvidenceDetail(source, [eligibleConnection], trail, {
    document: fakeDocument(),
    resolveEvidenceTarget: (id) => data.items.find((item) => item.id === id) || null,
    onFollowEvidence: (item, relationship, button) => {
      followed = explorer.followEvidence(trail, item, relationship, button.dataset.narrativeFocusId);
    },
  });
  const button = descendants(sourceView).find((element) => element.tagName === "BUTTON" && element.textContent.includes("Enuma Elish cosmic-ordering comparison"));
  assert.ok(button);
  button.click();
  assert.equal(followed.error, null);
  assert.equal(followed.state.nodes.at(-1).id, targetId);
  assert.equal(followed.state.nodes.at(-1).relationshipHops, 1);

  const targetView = explorer.renderEvidenceDetail(target, [], followed.state, {document: fakeDocument()});
  assert.deepEqual(target.source_ids, ["lambert-babylonian-creation-2013", "sarna-genesis-comparison"]);
  assert.match(targetView.textContent, /lambert-babylonian-creation-2013/);
  assert.match(targetView.textContent, /sarna-genesis-comparison/);
  assert.match(targetView.textContent, /probable/);
  assert.match(targetView.textContent, /major_scholarly_disagreement/);
  assert.match(targetView.textContent, /in_review/);
  assert.match(targetView.textContent, /draft/);
  assert.match(targetView.textContent, /Babylonian Creation Myths/);
  assert.match(targetView.textContent, /composition date, ritual uses, and genetic relationship to Genesis are reconstructed and debated/);
  assert.match(targetView.textContent, /Known witnesses and proposed composition dates span a broad range/);
  assert.match(targetView.textContent, /does not establish literary borrowing or dependence/);
});

test("overview guides readers and reports coverage-aware linked record counts", () => {
  const data = projection({
    passage: {reference: "Genesis 6:1-4", book: "Genesis", chapter: 6, verse_start: 1, verse_end: 4, scope: "verse_range"},
    sections: [
      section("biblical_narrative", ["ckl:creation#claim:days"], "available"),
      section("archaeology_ancient_history", [], "not_represented"),
      {...section("biblical_geography"), source_domains: ["canonical_knowledge_library", "passage_maps"], state: "unknown"},
      section("divine_council_cosmic_geography", ["ckl:creation#claim:days"], "partial"),
      section("themes_biblical_connections"),
      section("people_events_relationships"),
    ],
    items: [projection().items[0]],
  });

  const root = explorer.renderOverview(data, {document: fakeDocument()});
  const sectionsHost = descendants(root).find((element) => element.className === "narrative-explorer-sections");
  const sectionCard = (id) => sectionsHost.children.find((element) => element.dataset.sectionId === id);

  assert.match(root.textContent, /Explore the sources and connections recorded for this passage/);
  assert.match(root.textContent, /Sources and counts show what was returned for this passage/);
  const coverageLines = descendants(root).filter((element) => element.className === "narrative-explorer-coverage");
  assert.ok(coverageLines.some((element) => element.textContent.includes("Evidence library:")));
  assert.doesNotMatch(coverageLines.map((element) => element.textContent).join(" "), /\bCKL\b/);
  const readerGuidance = descendants(root).find((element) => element.className === "narrative-explorer-section-heading");
  assert.match(readerGuidance.textContent, /A Scripture reference shows where evidence applies/i);
  assert.match(readerGuidance.textContent, /doesn't automatically mean two passages are connected/i);
  assert.doesNotMatch(readerGuidance.textContent, /CKL relationship|projection|metadata/i);
  assert.match(sectionCard("biblical_narrative").textContent, /1 linked record/);
  assert.match(sectionCard("archaeology_ancient_history").textContent, /No records were found for this passage/);
  assert.match(sectionCard("biblical_geography").textContent, /No count is available because the source lookup did not finish/);
  assert.match(sectionCard("divine_council_cosmic_geography").textContent, /1 linked record in incomplete results/);
  assert.doesNotMatch(root.textContent, /CKL parent records|0 claims · 0 evidence records/);
});

test("passage overview cards label text, comparison, reception, and interpretation from CKL records", () => {
  const cases = [
    {
      file: "genesis_6_1_4.json",
      id: "ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions",
      label: "Scholarly interpretation · disputed position",
      sourceId: "g2-doedens-sons-god",
      rawCategory: "worldview-concept",
    },
    {
      file: "genesis_6_1_4.json",
      id: "ckl:genesis-flood-postflood-context#evidence:g6-nephilim-and-mighty-men",
      label: "Scholarly interpretation · literary reading",
      sourceId: "g2-doedens-sons-god",
      rawCategory: "literary-convention",
    },
    {
      file: "genesis_6_1_4.json",
      id: "ckl:genesis-flood-postflood-context#evidence:g6-second-temple-watchers-reception",
      label: "Later reception",
      sourceId: "g2-1-enoch-6",
      rawCategory: "ancient-text",
    },
    {
      file: "psalm_82.json",
      id: "ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language",
      label: "Original biblical text · worldview language",
      sourceId: "psalm-82-hebrew-text",
      rawCategory: "worldview-concept",
    },
    {
      file: "psalm_82.json",
      id: "ckl:ancient-divine-assembly-imagery#evidence:ugaritic-council-comparison",
      label: "Ancient comparative literature",
      sourceId: "smith-ugaritic-baal-cycle-1994",
      rawCategory: "ancient-text",
    },
    {
      file: "genesis_2.json",
      id: "ckl:genesis#evidence:g2-garden-planting-presence",
      label: "Geography and place identification",
      sourceId: "g1-amit-eden-exposition",
      rawCategory: "geography-environment",
    },
    {
      file: "genesis_2.json",
      id: "ckl:genesis#evidence:g2-rivers-and-eden-geographic-limits",
      label: "Geography and place identification",
      sourceId: "g1-amit-eden-exposition",
      rawCategory: "geography-environment",
    },
  ];
  const fixturePath = (name) => path.join(__dirname, "../fixtures/narrative_explorer/ne5a_baseline", name);

  for (const testCase of cases) {
    const data = JSON.parse(fs.readFileSync(fixturePath(testCase.file), "utf8"));
    const sectionId = data.sections.find((entry) => entry.item_ids.includes(testCase.id))?.id;
    const root = explorer.renderOverview(data, {document: fakeDocument(), onInspect: () => {}});
    const sectionCard = descendants(root).find((element) => element.dataset.sectionId === sectionId);
    const inspect = descendants(sectionCard).find((element) => element.className.includes("narrative-explorer-inspect"));
    inspect.click();
    const itemCard = descendants(sectionCard).find((element) => element.tagName === "ARTICLE"
      && descendants(element).some((child) => child.dataset.narrativeItemId === testCase.id));
    const label = descendants(itemCard).find((element) => element.className === "narrative-explorer-item-kind");
    const provenance = descendants(itemCard).find((element) => element.className === "narrative-explorer-provenance");

    assert.equal(label.textContent, testCase.label, `${testCase.id} should use its reader-facing evidence layer`);
    assert.doesNotMatch(label.textContent, /worldview-concept|ancient-text|geography-environment|literary-convention/);
    assert.match(provenance.textContent, new RegExp(`Evidence category: ${testCase.rawCategory}`));
    assert.match(provenance.textContent, new RegExp(testCase.sourceId));
    assert.match(provenance.textContent, /Passage relationship:/);
  }
});

test("overview keeps passage evidence concise and separates anchors from recorded connection bases", () => {
  const fixturePath = (name) => path.join(__dirname, "../fixtures/narrative_explorer/ne5a_baseline", name);
  const cases = [
    {
      file: "genesis_6_1_4.json",
      titles: [
        "Sons of God: documented interpretive positions",
        "Second Temple Watchers reception of Genesis 6",
        "Gilgamesh Tablet XI flood comparison",
      ],
    },
    {
      file: "psalm_82.json",
      titles: ["Psalm 82 divine-assembly language", "Ugaritic council imagery comparison"],
    },
    {
      file: "deuteronomy_32_8_9.json",
      titles: ["Deuteronomy 32:8 manuscript variation"],
    },
    {
      file: "genesis_2.json",
      titles: ["Garden planting and divine presence", "Four rivers and limits of Eden identification"],
    },
  ];

  for (const testCase of cases) {
    const data = JSON.parse(fs.readFileSync(fixturePath(testCase.file), "utf8"));
    const inspected = [];
    const root = explorer.renderOverview(data, {
      document: fakeDocument(),
      onInspect: (item) => inspected.push(item.id),
    });
    const discovery = descendants(root).find((element) => element.className.includes("narrative-explorer-connection-discovery"));

    assert.ok(discovery, `${testCase.file} should expose the connection discovery entry point`);
    assert.match(discovery.textContent, /Evidence about /);
    const readerGuidance = descendants(discovery).find((element) => element.className === "narrative-explorer-section-heading");
    assert.match(readerGuidance.textContent, /A Scripture reference shows where evidence applies/i);
    assert.match(readerGuidance.textContent, /doesn't automatically mean two passages are connected/i);
    assert.doesNotMatch(readerGuidance.textContent, /CKL relationship|projection|metadata/i);
    assert.doesNotMatch(discovery.textContent, /Explore related passages and evidence/);
    const cards = descendants(discovery).filter((element) => element.dataset.narrativeConnectionPreview === "true");
    assert.ok(cards.length > 0 && cards.length <= 3, `${testCase.file} should keep the preview concise`);
    assert.deepEqual(
      cards.map((card) => descendants(card).find((element) => element.tagName === "H5")?.textContent),
      testCase.titles,
      `${testCase.file} should order its compact preview by reader-facing evidence type`,
    );

    for (const title of testCase.titles) {
      const card = cards.find((element) => element.textContent.includes(title));
      assert.ok(card, `${testCase.file} should surface ${title}`);
      const description = descendants(card).find((element) => element.className === "narrative-explorer-item-copy");
      assert.ok(description, `${title} should have one source-grounded descriptive sentence`);
      assert.equal((description.textContent.match(/[.!?](?:\s|$)/g) || []).length, 1, `${title} should have one concise sentence`);
      assert.doesNotMatch(description.textContent, /(^|\s)[*_][^*_]+[*_](\s|$)/, `${title} should render Markdown emphasis without literal markers`);
      assert.match(card.textContent, /Connection context:|Why this evidence appears:/);
      assert.doesNotMatch(card.textContent, /Evidence anchor:|Comparison anchor:/, `${title} should not present an anchor as a connection`);
      const provenance = descendants(card).find((element) => element.className === "narrative-explorer-provenance");
      assert.ok(provenance, `${title} should retain expandable evidence provenance`);
      const previewBasis = descendants(card).find((element) => element.className === "narrative-explorer-preview-basis");
      assert.ok(previewBasis, `${title} should expose a recorded connection or relevance basis`);
      assert.ok(provenance.textContent.includes(previewBasis.textContent.replace(/^(Connection context|Why this evidence appears): /, "")), `${title} should retain the recorded preview context in its details`);
      const sourceIds = data.items.find((item) => item.title === title)?.source_ids || [];
      assert.ok(sourceIds.some((sourceId) => provenance.textContent.includes(sourceId)), `${title} should retain a recorded source ID`);
      const sourceItem = data.items.find((item) => item.title === title);
      [sourceItem.claim_text, sourceItem.description].filter(Boolean).forEach((sourceText) => {
        assert.ok(provenance.textContent.includes(sourceText.replaceAll("*", "")), `${title} should retain the full original wording in expandable details`);
      });
      assert.match(provenance.textContent, /Original relationship types:|Connection basis:/);
      assert.match(provenance.textContent, /Passage relationship:/, `${title} should retain its passage anchor in details`);
      const explore = descendants(card).find((element) => element.className.includes("narrative-explorer-item-inspect"));
      assert.equal(explore?.textContent, "Explore this evidence", `${title} should use reader-facing detail navigation`);
      explore.click();
    }

    assert.equal(inspected.length, testCase.titles.length, "the preview action should reuse the existing inspect callback");
    if (testCase.file === "genesis_6_1_4.json") {
      const sons = cards.find((element) => element.textContent.includes("Sons of God: documented interpretive positions"));
      assert.match(sons.textContent, /Who the [“\"]?sons of God[”\"]? are and what the episode means remain disputed/i);
      assert.doesNotMatch(sons.textContent, /Major scholarly disagreement/i);
      const gilgamesh = cards.find((element) => element.textContent.includes("Gilgamesh Tablet XI flood comparison"));
      assert.match(gilgamesh.textContent, /flood motifs.*how the traditions are related remains debated/i);
      assert.doesNotMatch(gilgamesh.textContent, /Major scholarly disagreement/i);
      const watchers = cards.find((element) => element.textContent.includes("Second Temple Watchers reception"));
      const watcherQualification = descendants(watchers).find((element) => element.className === "narrative-explorer-item-qualification");
      assert.match(watcherQualification.textContent, /later reception/i);
      assert.match(watcherQualification.textContent, /later than Genesis.*time label needs review/i);
      assert.doesNotMatch(watcherQualification.textContent, /CKL|metadata/i);
      assert.match(watchers.textContent, /Later reception/);
    }
    if (testCase.file === "psalm_82.json") {
      assert.match(cards[0].textContent, /identity of the figures addressed in Psalm 82 remains disputed/i);
      assert.doesNotMatch(cards[0].textContent, /Interpretation remains disputed/i);
      const comparison = cards.find((element) => element.textContent.includes("Ugaritic council imagery comparison"));
      assert.match(comparison.textContent, /Ancient comparative literature/);
      assert.match(comparison.textContent, /not decide the referents/);
      assert.match(comparison.textContent, /Ugaritic parallels.*relationship to biblical language remains uncertain/i);
      assert.doesNotMatch(comparison.textContent, /Major scholarly disagreement/i);
    }
    if (testCase.file === "deuteronomy_32_8_9.json") {
      assert.match(cards[0].textContent, /Manuscript\/textual witness/);
      assert.match(cards[0].textContent, /manuscripts preserve different wording at Deuteronomy 32:8.*earliest remains debated/i);
    }
    if (testCase.file === "genesis_2.json") {
      const rivers = cards.find((element) => element.textContent.includes("Four rivers and limits"));
      assert.match(rivers.textContent, /identification.*uncertain|location.*uncertain/i);
    }
  }
});

test("supported Markdown emphasis renders as safe text in evidence details without changing CKL data", () => {
  const fixturePath = path.join(__dirname, "../fixtures/narrative_explorer/ne5a_baseline/genesis_2.json");
  const data = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
  const item = data.items.find((candidate) => candidate.title === "Genesis 2:4 as literary hinge");
  const originalDescription = item.description;
  const detail = explorer.renderEvidenceDetail(item, [], null, {document: fakeDocument()});
  const emphasis = descendants(detail).find((element) => element.tagName === "EM" && element.textContent === "toledot");

  assert.ok(emphasis, "the Hebrew transliteration should render in an emphasis element");
  assert.match(detail.textContent, /toledot/);
  assert.doesNotMatch(detail.textContent, /\*toledot\*/);
  assert.equal(item.description, originalDescription, "rendering must not modify the projected CKL wording");

  const unsafeLookingText = explorer.renderEvidenceDetail({
    ...item,
    description: "A *safe term* with literal <img src=x onerror=alert(1)> text.",
  }, [], null, {document: fakeDocument()});
  assert.match(unsafeLookingText.textContent, /literal <img src=x onerror=alert\(1\)> text/);
  assert.doesNotMatch(descendants(unsafeLookingText).map((element) => element.tagName).join(" "), /IMG/);
});

test("raw CKL record navigation remains available from the detailed evidence view", () => {
  const fixturePath = path.join(__dirname, "../fixtures/narrative_explorer/ne5a_baseline/genesis_6_1_4.json");
  const data = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
  const item = data.items.find((candidate) => candidate.title === "Sons of God: documented interpretive positions");
  let opened = 0;
  const detail = explorer.renderEvidenceDetail(item, [], null, {
    document: fakeDocument(),
    onNavigate: () => { opened += 1; },
  });
  const action = descendants(detail).find((element) => element.className.includes("narrative-explorer-item-action"));

  assert.equal(action?.textContent, "Open CKL record");
  action.click();
  assert.equal(opened, 1);
  assert.match(detail.textContent, /CKL parent object/);
});

test("uncertain evidence keeps its original CKL status in detail and uses a neutral fallback when needed", () => {
  const fixturePath = path.join(__dirname, "../fixtures/narrative_explorer/ne5a_baseline/genesis_6_1_4.json");
  const data = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
  const sons = data.items.find((candidate) => candidate.title === "Sons of God: documented interpretive positions");
  const detail = explorer.renderEvidenceDetail(sons, [], null, {document: fakeDocument()});

  assert.match(detail.textContent, /Dispute state: major_scholarly_disagreement/);
  assert.match(detail.textContent, /identity of the figures and the force of the episode remain disputed/i);

  const unspecified = {
    ...sons,
    title: "Unspecified evidence disagreement",
    claim_text: null,
    description: "The record does not explain what remains disputed.",
    rationale: {},
  };
  const fallbackRoot = explorer.renderOverview({
    ...data,
    items: data.items.map((candidate) => candidate.id === sons.id ? unspecified : candidate),
  }, {document: fakeDocument()});
  const fallbackCard = descendants(fallbackRoot).find((element) =>
    element.dataset.narrativeConnectionPreview === "true"
      && element.textContent.includes("Unspecified evidence disagreement"));

  assert.ok(fallbackCard);
  assert.match(fallbackCard.textContent, /Some conclusions about this evidence remain unsettled\./);
  assert.doesNotMatch(fallbackCard.textContent, /Major scholarly disagreement|identity of the.*sons of God/i);
});

test("connection preview distinguishes missing coverage from no recorded eligible relationships", () => {
  const noEdges = projection({connections: []});
  const noEdgeRoot = explorer.renderOverview(noEdges, {document: fakeDocument()});
  const noEdgeDiscovery = descendants(noEdgeRoot).find((element) => element.className.includes("narrative-explorer-connection-discovery"));
  assert.match(noEdgeDiscovery.textContent, /No evidence preview with a source explanation is available/i);
  assert.doesNotMatch(noEdgeDiscovery.textContent, /No evidence exists/i);

  const unavailable = projection({
    coverage: projection().coverage.map((entry) => entry.domain === "ckl"
      ? {...entry, state: "unknown", query_status: "failed", reason_code: "ckl_lookup_failed"}
      : entry),
    connections: [],
  });
  const unavailableRoot = explorer.renderOverview(unavailable, {document: fakeDocument()});
  const unavailableDiscovery = descendants(unavailableRoot).find((element) => element.className.includes("narrative-explorer-connection-discovery"));
  assert.match(unavailableDiscovery.textContent, /The source lookup did not finish/i);

  const partial = projection({
    coverage: projection().coverage.map((entry) => entry.domain === "ckl"
      ? {...entry, state: "partial", query_status: "partial", reason_code: "partial_results"}
      : entry),
    connections: [],
  });
  const partialRoot = explorer.renderOverview(partial, {document: fakeDocument()});
  const partialDiscovery = descendants(partialRoot).find((element) => element.className.includes("narrative-explorer-connection-discovery"));
  assert.match(partialDiscovery.textContent, /No source-linked previews are available among the returned records/i);
  assert.doesNotMatch(partialDiscovery.textContent, /No evidence exists/i);

  const fixturePath = path.join(__dirname, "../fixtures/narrative_explorer/ne5a_baseline/genesis_6_1_4.json");
  const partialWithRecords = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
  partialWithRecords.coverage = partialWithRecords.coverage.map((entry) => entry.domain === "ckl"
    ? {...entry, state: "partial", query_status: "partial", reason_code: "partial_results"}
    : entry);
  const partialRecordsRoot = explorer.renderOverview(partialWithRecords, {document: fakeDocument()});
  const partialRecordsDiscovery = descendants(partialRecordsRoot).find((element) => element.className.includes("narrative-explorer-connection-discovery"));
  assert.match(partialRecordsDiscovery.textContent, /Some linked source records may not be available in this preview/i);
  assert.ok(descendants(partialRecordsDiscovery).some((element) => element.dataset.narrativeConnectionPreview === "true"));
});

test("direct Scripture anchors are not rendered as unclassified CKL associations", () => {
  const fixturePath = path.join(__dirname, "../fixtures/narrative_explorer/ne5a_baseline/psalm_82.json");
  const data = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
  const item = data.items.find((candidate) => candidate.id === "ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language");
  const anchor = data.connections.find((edge) => edge.source_id === item.id && edge.basis?.kind === "ckl_scripture_anchor");
  const detail = explorer.renderEvidenceDetail(item, [anchor], explorer.createTrail({book: "Psalms", chapter: 82, reference: "Psalms 82"}), {
    document: fakeDocument(),
    knownBooks: [{value: "Psalms", chapters: 150}],
  });

  assert.match(detail.textContent, /Scripture passage anchor/);
  assert.match(detail.textContent, /shows the evidence's passage scope/i);
  assert.match(detail.textContent, /Recorded CKL relationships \(0\)/);
  assert.match(detail.textContent, /Passage anchors \(1\)/);
  assert.match(detail.textContent, /Evidence scope: Scripture passage anchor/);
  assert.doesNotMatch(detail.textContent, /This authored label is a descriptive association/);

  const comparison = data.items.find((candidate) => candidate.id === "ckl:ancient-divine-assembly-imagery#evidence:ugaritic-council-comparison");
  const comparisonAnchor = data.connections.find((edge) => edge.source_id === comparison.id && edge.basis?.kind === "ckl_scripture_anchor");
  const comparisonDetail = explorer.renderEvidenceDetail(comparison, [comparisonAnchor], explorer.createTrail({book: "Psalms", chapter: 82, reference: "Psalms 82"}), {
    document: fakeDocument(),
    knownBooks: [{value: "Psalms", chapters: 150}],
  });
  assert.match(comparisonDetail.textContent, /Comparative passage anchor/);
  assert.match(comparisonDetail.textContent, /Evidence scope: Comparative passage anchor/);
  assert.match(comparisonDetail.textContent, /does not establish a literary or theological relationship/);
  assert.doesNotMatch(comparisonDetail.textContent, /This authored label is a descriptive association/);
});
