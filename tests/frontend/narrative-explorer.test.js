const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const presentationPolicy = require("../../bhf_web/static/narrative-presentation-policy.js");
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
  return {
    createElement: (tagName) => new FakeElement(tagName),
    createElementNS: (_namespace, tagName) => new FakeElement(tagName),
  };
}

function descendants(element) {
  return [element, ...element.children.flatMap(descendants)];
}

function readerEligible(item, reference = "Genesis 1") {
  const sources = Array.isArray(item.sources) && item.sources.length
    ? item.sources.map((source, index) => {
      const bibliography = source.bibliographic_details && typeof source.bibliographic_details === "object"
        ? source.bibliographic_details
        : {};
      return {
        ...source,
        details_available: true,
        bibliographic_details: {
          ...bibliography,
          title: bibliography.title || source.title || `Test cited source ${index + 1}`,
        author: bibliography.author || source.author || "Test source author",
        year: bibliography.year || source.year || 2024,
        },
      };
    })
    : [{id: "test-cited-source", details_available: true, bibliographic_details: {title: "Test cited source", author: "Test source author", year: 2024}}];
  const anchors = Array.isArray(item.applicable_passage_anchors) && item.applicable_passage_anchors.length
    ? item.applicable_passage_anchors
    : [{reference, relationship: "direct"}];
  return {...item, applicable_passage_anchors: anchors, sources};
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

function renderCategory(data, categoryId, options = {}) {
  return explorer.renderOverview(data, {
    ...options,
    view: {kind: "category", categoryId},
  });
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

test("overview shows six concise category cards and no evidence inventory", () => {
  const opened = [];
  const openedContext = [];
  const openedSources = [];
  const root = explorer.renderOverview(projection(), {
    document: fakeDocument(),
    onOpenCategory: (categoryId, trigger) => opened.push({categoryId, trigger}),
    onOpenUnderstandPassage: (trigger) => openedContext.push(trigger),
    onOpenResearchSources: (trigger) => openedSources.push(trigger),
  });
  const categoryIds = [
    "biblical_narrative",
    "archaeology_ancient_history",
    "biblical_geography",
    "divine_council_cosmic_geography",
    "themes_biblical_connections",
    "people_events_relationships",
  ];
  const cards = descendants(root).filter((element) => element.className === "narrative-explorer-category-card");
  const connectionEntry = descendants(root).find((element) => element.className === "narrative-explorer-follow-connection");
  const contextEntry = descendants(root).find((element) => element.className === "narrative-explorer-understand-passage");
  const sourcesEntry = descendants(root).find((element) => element.className === "narrative-explorer-browse-sources");

  assert.match(root.textContent, /Explore this passage/);
  assert.match(root.textContent, /Current passage: Genesis 1/);
  assert.deepEqual(cards.map((element) => element.dataset.sectionId), categoryIds);
  assert.equal(cards.filter((card) => descendants(card).some((element) => element.tagName === "SVG"
    && element.attributes["aria-hidden"] === "true")).length, 6);
  assert.match(connectionEntry.textContent, /Follow a Connection/);
  assert.match(contextEntry.textContent, /Understand the Passage/);
  assert.match(contextEntry.textContent, /Explore the historical setting, original audience, literary structure, and cultural background\./);
  assert.match(sourcesEntry.textContent, /Find a source/);
  assert.equal(descendants(root).filter((element) => element.className === "narrative-explorer-item").length, 0);
  assert.equal(descendants(root).filter((element) => element.className === "narrative-explorer-category-count").length, 0);
  assert.ok(descendants(root).some((element) => element.className === "narrative-explorer-featured-discoveries"));

  connectionEntry.click();
  contextEntry.click();
  sourcesEntry.click();

  assert.equal(opened.length, 1);
  assert.equal(opened[0].categoryId, "themes_biblical_connections");
  assert.equal(opened[0].trigger, connectionEntry);
  assert.deepEqual(openedContext, [contextEntry]);
  assert.deepEqual(openedSources, [sourcesEntry]);
});

test("reader overview features only eligible discoveries and keeps inaccessible evidence out of reader cards", () => {
  const featured = {
    ...projection().items[0],
    id: "ckl:nahum#evidence:nahum-3-8-9-one-city-text-critical-proposal",
    object_id: "nahum",
    evidence_id: "nahum-3-8-9-one-city-text-critical-proposal",
    title: "Does Nahum 3:8–9 compare Nineveh with No-Amon?",
    description: "A disputed text-critical proposal.",
    source_ids: ["gruetter-nahum3-one-city-2017"],
    sources: [{id: "gruetter-nahum3-one-city-2017", details_available: true, bibliographic_details: {
      title: "A Tale of One City", author: "Nesina Grütter", publisher: "Journal of Septuagint and Cognate Studies", year: 2017, locator: "pp. 160–175",
    }}],
    applicable_passage_anchors: [{reference: "Nahum 3:8–9", relationship: "direct"}],
    review_status: "in_review",
    content_status: "draft",
    human_review_required: true,
  };
  const withheld = {
    ...featured,
    id: "ckl:psalms#evidence:psalm-100-worship-and-the-psalter-sequence",
    evidence_id: "psalm-100-worship-and-the-psalter-sequence",
    title: "A proposed Psalter sequence",
    applicable_passage_anchors: [{reference: "Psalm 100", relationship: "direct"}],
  };
  const data = projection({
    passage: {reference: "Nahum 3:8–9", book: "Nahum", chapter: 3, verse_start: 8, verse_end: 9, scope: "verse_range"},
    items: [featured, withheld],
    sections: [section("biblical_narrative", [featured.id, withheld.id])],
  });

  const root = explorer.renderOverview(data, {document: fakeDocument()});
  const discovery = descendants(root).find((element) => element.className === "narrative-explorer-featured-discoveries");
  const cards = descendants(root).filter((element) => element.className === "narrative-explorer-featured-card");

  assert.ok(discovery);
  assert.match(discovery.textContent, /What to notice/);
  assert.match(discovery.textContent, /Nineveh/);
  assert.match(discovery.textContent, /proposed historical explanation/i);
  assert.match(discovery.textContent, /How we know/);
  assert.match(discovery.textContent, /A Tale of One City/);
  assert.doesNotMatch(discovery.textContent, /human_review_required|in_review|draft|ckl:nahum|gruetter-nahum3/);
  assert.doesNotMatch(root.textContent, /Draft evidence|awaiting human review|Additional sourced records|psalm-100-worship/);
  assert.equal(cards.length, 1);
  assert.doesNotMatch(cards[0].textContent, /Draft evidence|CKL ID|Source ID|Review state|Content state|Human review required/);
  assert.equal(presentationPolicy.tierFor(withheld), "withheld_from_reader_promotion");
});

test("overview leads with study paths when no featured discovery qualifies", () => {
  const root = explorer.renderOverview(projection(), {document: fakeDocument()});
  const section = descendants(root).find((element) => element.className === "narrative-explorer-featured-discoveries");
  const guidance = descendants(section).find((element) => element.className === "narrative-explorer-featured-guidance");

  assert.ok(guidance);
  assert.match(guidance.textContent, /Start with a study topic or explore the original context/i);
  assert.match(guidance.textContent, /verified biblical connection/i);
  assert.equal(descendants(section).filter((element) => element.className === "narrative-explorer-featured-card").length, 0);
  assert.equal(descendants(section).some((element) => element.className === "narrative-explorer-featured-empty"), false);
  assert.equal(descendants(root).filter((element) => element.className === "narrative-explorer-category-card").length, 6);
});

test("overview explains a completed empty CKL result after reader-first guidance", () => {
  const data = projection({
    passage: {reference: "1 Kings 2", book: "1 Kings", chapter: 2, verse_start: null, verse_end: null, scope: "chapter"},
    coverage: [
      {domain: "ckl", source_domain: "canonical_knowledge_library", state: "not_represented", query_status: "complete", query_returned_count: 0, projected_item_count: 0, reason_code: "no_eligible_records", missing_subdomains: [], description: "The completed lookup found no passage-eligible CKL records."},
      {domain: "maps", source_domain: "passage_maps", state: "not_represented", query_status: "complete", query_returned_count: 0, projected_item_count: 0, reason_code: "no_eligible_records", missing_subdomains: [], description: "The completed map lookup returned no eligible records."},
      {domain: "archaeology", source_domain: "archaeology_passage_resolver", state: "not_represented", query_status: "complete", query_returned_count: 0, projected_item_count: 0, reason_code: "no_eligible_records", missing_subdomains: [], description: "The completed archaeology lookup returned no eligible records."},
    ],
    sections: [
      section("biblical_narrative"),
      section("archaeology_ancient_history"),
      section("biblical_geography"),
      section("divine_council_cosmic_geography"),
      section("themes_biblical_connections"),
      section("people_events_relationships"),
    ],
    items: [],
    connections: [],
    related_passages: {state: "not_represented", query_status: "complete", authored_relationships: [], evidence_backed_bridges: []},
  });
  const root = explorer.renderOverview(data, {document: fakeDocument()});
  const guidance = descendants(root).find((element) => element.className === "narrative-explorer-featured-guidance");
  const notice = descendants(root).find((element) => element.className === "narrative-explorer-featured-empty");

  assert.ok(guidance);
  assert.ok(notice);
  assert.match(notice.textContent, /No eligible Evidence library research is currently available for 1 Kings 2/);
  assert.match(notice.textContent, /BHF's current coverage/i);
  assert.match(notice.textContent, /not the passage's importance/i);
  assert.ok(root.textContent.indexOf(guidance.textContent) < root.textContent.indexOf(notice.textContent));
  assert.ok(descendants(root).some((element) => element.className === "narrative-explorer-understand-passage"));
  assert.equal(descendants(root).filter((element) => element.className === "narrative-explorer-category-card").length, 6);
});

test("overview provides a collapsed, plain-language guide to recurring research terms", () => {
  const root = explorer.renderOverview(projection(), {document: fakeDocument()});
  const guide = descendants(root).find((element) => element.className === "narrative-explorer-terms-guide");

  assert.ok(guide);
  assert.equal(guide.tagName, "DETAILS");
  assert.equal(guide.attributes.open, undefined);
  assert.match(guide.textContent, /Textual witness/);
  assert.match(guide.textContent, /Masoretic Text/);
  assert.match(guide.textContent, /Septuagint/);
  assert.match(guide.textContent, /redaction/i);
  assert.match(guide.textContent, /lexical range/i);
  assert.match(guide.textContent, /definitions explain terminology; they do not settle how a term applies/i);
});

test("overview retires the additional sourced records list from the reader journey", () => {
  const kephale = {
    ...projection().items[0],
    id: "ckl:1-corinthians#claim:1cor-kephale",
    object_id: "1-corinthians",
    parent_object_id: "1-corinthians",
    claim_id: "1cor-kephale",
    evidence_id: null,
    title: "Kephale in 1 Corinthians 11:3",
    claim_text: "Kephale means head, but its relational force remains disputed.",
    claim_type: "lexical",
    certainty: "disputed",
    dispute_status: "lexical_uncertainty",
    source_ids: ["bdag"],
    sources: [{id: "bdag", details_available: true, bibliographic_details: {title: "BDAG"}}],
    passage_anchors: [{reference: "1 Corinthians 11:3", relationship: "direct"}],
    applicable_passage_anchors: [{reference: "1 Corinthians 11:3", relationship: "direct"}],
    section_ids: [],
  };
  const assignedDuplicate = {
    ...kephale,
    id: "ckl:1-corinthians#claim:already-assigned",
    claim_id: "already-assigned",
    section_ids: ["themes_biblical_connections"],
  };
  const broadObject = {
    ...kephale,
    id: "ckl:new-jerusalem-prophecy",
    object_id: "new-jerusalem-prophecy",
    parent_object_id: "new-jerusalem-prophecy",
    claim_id: null,
    record_kind: "object",
  };
  const sourceLess = {
    ...kephale,
    id: "ckl:1-corinthians#claim:no-sources",
    claim_id: "no-sources",
    source_ids: [],
    sources: [],
  };
  const noApplicableAnchor = {
    ...kephale,
    id: "ckl:1-corinthians#claim:wrong-passage",
    claim_id: "wrong-passage",
    passage_anchors: [{reference: "1 Corinthians 5:1-3", relationship: "direct"}],
    applicable_passage_anchors: [],
  };
  const connectionPreview = {
    ...kephale,
    id: "ckl:1-corinthians#evidence:already-previewed",
    record_kind: "evidence",
    claim_id: null,
    evidence_id: "already-previewed",
    claim_text: null,
    evidence_category: "ancient-text",
    title: "Already previewed evidence",
  };
  const base = projection();
  const data = projection({
    passage: {reference: "1 Corinthians 11", book: "1 Corinthians", chapter: 11, verse_start: null, verse_end: null, scope: "chapter"},
    sections: base.sections.map((entry) => entry.id === "themes_biblical_connections"
      ? {...entry, item_ids: [...entry.item_ids, assignedDuplicate.id]}
      : entry),
    items: [kephale, assignedDuplicate, broadObject, sourceLess, noApplicableAnchor, connectionPreview],
    connections: [{
      id: "connection:already-previewed",
      source_id: connectionPreview.id,
      target_id: "ckl:1-corinthians#evidence:target",
      connection_type: "related",
      basis: {kind: "ckl_related_evidence", notes: "Recorded evidence relationship."},
    }],
  });

  const root = explorer.renderOverview(data, {document: fakeDocument(), onInspect: () => {}});
  const disclosure = descendants(root).find((element) => element.className.split(" ").includes("narrative-explorer-additional-records-toggle"));
  assert.equal(disclosure, undefined);
  assert.equal(descendants(root).filter((element) => element.className === "narrative-explorer-item").length, 0);
  assert.doesNotMatch(root.textContent, /Additional sourced records|Kephale means head|already-assigned|new-jerusalem-prophecy|no-sources|wrong-passage/);
  assert.equal(kephale.section_ids.length, 0);
  assert.equal(descendants(root).filter((element) => element.className === "narrative-explorer-category-card").length, 6);
});

test("overview defers the empty origin-only trail until a connection is followed", () => {
  const origin = explorer.createTrail({book: "Genesis", chapter: 1, reference: "Genesis 1"});
  const overview = explorer.renderOverview(projection(), {document: fakeDocument(), trail: origin});

  assert.equal(descendants(overview).filter((element) => element.className === "narrative-explorer-trail-header").length, 0);

  const followed = explorer.followPassage(origin, {
    reference: "John 1",
    selection: {book: "John", chapter: 1, reference: "John 1"},
  }, {
    provenance: "authored_ckl_relationship",
    source_passage: "Genesis 1",
    destination_passage: "John 1",
    original_relationship_type: "thematic_relationship",
    direction: "one_way",
  });
  const connected = explorer.renderOverview(projection(), {document: fakeDocument(), trail: followed.state});

  assert.equal(descendants(connected).filter((element) => element.className === "narrative-explorer-trail-header").length, 1);
  assert.match(connected.textContent, /Origin passage/);
  assert.match(connected.textContent, /Recorded connection/);
  assert.match(connected.textContent, /John 1/);
});

test("focused category shows only its previews and passage return controls", () => {
  const actions = [];
  const root = explorer.renderOverview(projection(), {
    document: fakeDocument(),
    view: {kind: "category", categoryId: "biblical_narrative"},
    onInspect: () => {},
    onBackToOverview: (trigger) => actions.push({kind: "back", trigger}),
    onReturnToOrigin: (trigger) => actions.push({kind: "return", trigger}),
  });
  const category = descendants(root).find((element) => element.className.split(" ").includes("narrative-explorer-section")
    && element.dataset.sectionId === "biblical_narrative");
  const otherCategories = descendants(root).filter((element) => element.className.split(" ").includes("narrative-explorer-section")
    && element.dataset.sectionId !== "biblical_narrative");
  const previews = descendants(category).find((element) => element.className === "narrative-explorer-previews");
  const buttons = descendants(root).filter((element) => element.tagName === "BUTTON");
  const back = buttons.find((element) => element.textContent === "Back to topics");
  const returnToPassage = buttons.find((element) => element.textContent === "Return to Genesis 1");

  assert.match(root.textContent, /Biblical Narrative/);
  assert.equal(otherCategories.length, 0);
  assert.equal(previews.children.length, 0, "incomplete source details stay out of the reader preview");
  assert.match(category.textContent, /No source-linked findings met this topic's reader filter/);
  assert.equal(buttons.some((element) => element.textContent === "Browse more research"), false);
  assert.ok(back);
  assert.ok(returnToPassage);
  back.click();
  returnToPassage.click();
  assert.deepEqual(actions.map((action) => action.kind), ["back", "return"]);
});

test("overview keeps category cards uncluttered and focused empty states honest", () => {
  const data = projection({
    sections: [
      ...projection().sections.map((entry) => entry.id === "biblical_geography"
        ? {...entry, state: "unknown", item_ids: []}
        : entry.id === "divine_council_cosmic_geography"
          ? {...entry, state: "partial", item_ids: ["ckl:creation#evidence:cosmos"]}
          : entry),
    ],
  });
  const root = explorer.renderOverview(data, {document: fakeDocument()});
  const cardFor = (id) => descendants(root).find((element) => element.className === "narrative-explorer-category-card"
    && element.dataset.sectionId === id);
  const geography = cardFor("biblical_geography");
  const cosmic = cardFor("divine_council_cosmic_geography");
  assert.doesNotMatch(geography.textContent, /Availability could not be checked|linked records/);
  assert.doesNotMatch(cosmic.textContent, /Some results may be missing|\d+ linked records/);
  const focusedUnknown = renderCategory(data, "biblical_geography", {document: fakeDocument()});
  assert.match(focusedUnknown.textContent, /could not check source availability/i);
  const focusedPartial = renderCategory(data, "divine_council_cosmic_geography", {document: fakeDocument()});
  assert.match(focusedPartial.textContent, /some research may be missing from this topic/i);
});

test("Follow a Connection opens the focused view with recorded passage routes", () => {
  const data = projection({
    related_passages: {
      state: "available",
      query_status: "complete",
      description: "Passage routes are available from the records listed here.",
      authored_relationships: [{
        id: "authored:genesis-john",
        provenance: "authored_ckl_relationship",
        source_passage: "Genesis 1:1",
        destination_passage: "John 1:1",
        relationship_category: "thematic_relationship",
        original_relationship_type: "canonical-fulfillment",
        source_id: "ckl:genesis#evidence:creation",
        target_id: "ckl:john#claim:logos",
        direction: "one_way",
        relationship_mode: "inferred",
        temporal_layer: "later_reception",
        basis: {kind: "ckl_related_object", notes: "Recorded authored relationship basis."},
        explanation: "A recorded authored relationship links these passages.",
        uncertainty: "This does not establish direct quotation.",
      }],
      evidence_backed_bridges: [{
        id: "bridge:genesis-john",
        provenance: "ckl_documented_claim",
        source_passage: "Genesis 1:1",
        destination_passage: "John 1:1",
        relationship_category: "interpretive_association",
        evidence_layer: "thematic_interpretation",
        direction: "interpretive_comparison",
        explanation: "The bridge is documented through the listed CKL claim.",
        uncertainty: "The interpretation remains debated.",
        human_scholarly_approval: "not_recorded",
        supporting_records: [{
          id: "ckl:john#claim:logos",
          object_id: "john",
          record_kind: "claim",
          record_id: "logos",
          statement: "The prologue places the Logos at the beginning.",
          source_ids: ["john-source"],
        }],
        supporting_sources: [{id: "john-source", title: "John source"}],
      }],
    },
  });
  const opened = [];
  const overview = explorer.renderOverview(data, {
    document: fakeDocument(),
    onOpenCategory: (categoryId) => opened.push(categoryId),
  });
  const entry = descendants(overview).find((element) => element.className === "narrative-explorer-follow-connection");

  assert.equal(descendants(overview).filter((element) => element.className === "narrative-explorer-related-passage").length, 0);
  entry.click();
  assert.deepEqual(opened, ["themes_biblical_connections"]);

  const focused = explorer.renderOverview(data, {
    document: fakeDocument(),
    view: {kind: "category", categoryId: "themes_biblical_connections"},
    knownBooks: [{value: "John", chapters: 21}],
    onOpenPassage: (destination, relationship) => opened.push({destination, relationship}),
  });
  const routes = descendants(focused).filter((element) => element.className === "narrative-explorer-related-passage");
  const passageButton = descendants(focused).find((element) => element.tagName === "BUTTON"
    && element.textContent.includes("John 1:1"));

  assert.equal(routes.length, 2);
  assert.match(focused.textContent, /Connections recorded in BHF/);
  assert.match(focused.textContent, /Connections supported by passage-specific research/);
  assert.match(focused.textContent, /Shared theme · Interpretive link/);
  assert.doesNotMatch(focused.textContent, /canonical-fulfillment|human scholarly approval|not_recorded|ckl:john/);
  assert.ok(passageButton);
});

test("trail header shows readable progression and preserves recorded direction", () => {
  const origin = {book: "Psalms", chapter: 22, reference: "Psalm 22"};
  const destination = {book: "Mark", chapter: 15, startVerse: 34, endVerse: 34, reference: "Mark 15:34"};
  const relationship = {
    id: "psalm-22-mark-15-lament",
    provenance: "authored_ckl_relationship",
    source_passage: "Psalm 22",
    destination_passage: "Mark 15:34",
    relationship_category: "thematic_relationship",
    original_relationship_type: "canonical-fulfillment",
    direction: "one_way",
    explanation: "The recorded relationship links the lament language in these passages.",
    uncertainty: "The relationship does not establish direct quotation or fulfillment.",
    human_scholarly_approval: "not_recorded",
    supporting_record_ids: ["ckl:psalm-22#evidence:psalm-22-lament"],
    supporting_ckl_sources: [{source_id: "source:psalm-22-lament", object_id: "psalm-22"}],
  };
  const followed = explorer.followPassage(
    explorer.createTrail(origin),
    {reference: destination.reference, selection: destination},
    relationship,
  );
  const root = renderCategory(projection({
    passage: {reference: destination.reference, book: "Mark", chapter: 15, verse_start: 34, verse_end: 34},
  }), "themes_biblical_connections", {document: fakeDocument(), trail: followed.state});
  const navigation = descendants(root).find((element) => element.tagName === "NAV"
    && element.attributes["aria-label"] === "Evidence trail");
  const steps = descendants(navigation).filter((element) => element.className.split(" ").includes("narrative-explorer-trail-step"));
  const currentStep = descendants(steps[2]).find((element) => element.attributes["aria-current"] === "page");

  assert.equal(steps.length, 3);
  assert.match(steps[0].textContent, /Origin passage.*Psalm 22/);
  assert.match(steps[1].textContent, /Recorded connection.*Psalm 22 → Mark 15:34/);
  assert.match(steps[1].textContent, /Psalm 22 → Mark 15:34/);
  assert.match(steps[2].textContent, /Related passage.*Mark 15:34/);
  assert.equal(currentStep.textContent, "Mark 15:34");
  assert.doesNotMatch(root.textContent, /Connection trail:|canonical-fulfillment|Supporting CKL|Human scholarly approval/);
  assert.match(root.textContent, /does not establish direct quotation or fulfillment/);
  assert.match(root.textContent, /Psalm 22 → Mark 15:34/);
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
    view: {kind: "category", categoryId: "themes_biblical_connections"},
    knownBooks: [{value: "John", chapters: 21}, {value: "Revelation", chapters: 22}],
    onOpenPassage: (destination, relationship) => opened.push({destination, relationship}),
  });

  assert.ok(descendants(root).some((item) => item.className === "narrative-explorer-passage" && item.textContent === "Current passage: Genesis 1"));
  assert.match(root.textContent, /Connections to other passages/);
  assert.match(root.textContent, /Connections recorded in BHF/);
  assert.match(root.textContent, /Connections supported by passage-specific research/);
  assert.match(root.textContent, /Shared theme/);
  assert.match(root.textContent, /The conceptual genealogy is debated/);
  assert.doesNotMatch(root.textContent, /canonical-fulfillment|major_scholarly_disagreement|human scholarly approval|ckl:john|one_way/);
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
  }), {document: fakeDocument(), trail: followed.state, view: {kind: "category", categoryId: "themes_biblical_connections"}});
  assert.ok(descendants(destinationView).some((item) => item.className === "narrative-explorer-passage" && item.textContent === "Current passage: John 1:1-18"));
  assert.match(destinationView.textContent, /About this connection/);
  assert.match(destinationView.textContent, /The conceptual genealogy is debated/);
  assert.doesNotMatch(destinationView.textContent, /ckl:john#claim:john-logos|human_review|not_recorded/);
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
  }), {document: fakeDocument(), view: {kind: "category", categoryId: "themes_biblical_connections"}});

  assert.match(view.textContent, /Connections to other passages/);
  assert.match(view.textContent, /lookup did not finish/);
  assert.match(view.textContent, /more may be available/);
  assert.doesNotMatch(view.textContent, /No biblical passage connection exists/);
});


test("selected passage route expands hidden pages and exposes a focusable highlighted heading", () => {
  const targetId = "route-6";
  const routes = Array.from({length: 6}, (_value, index) => ({
    id: `route-${index + 1}`,
    provenance: "ckl_documented_claim",
    source_passage: "Genesis 1:1-5",
    destination_passage: `John 1:${index + 1}`,
    relationship_category: "interpretive_association",
    evidence_layer: "thematic_interpretation",
    direction: "interpretive_comparison",
    explanation: "The texts are read in comparison.",
    uncertainty: "The relationship remains interpretive.",
    supporting_records: [{
      id: "ckl:john#claim:john-logos",
      object_id: "john",
      record_kind: "claim",
      record_id: "john-logos",
      source_ids: ["john-greek"],
    }],
    supporting_sources: [{id: "john-greek", title: "Greek New Testament"}],
  }));
  const view = explorer.renderOverview(projection({
    related_passages: {
      state: "available",
      query_status: "complete",
      description: "Passage routes are available from the records listed here.",
      authored_relationships: [],
      evidence_backed_bridges: routes,
    },
  }), {
    document: fakeDocument(),
    view: {kind: "category", categoryId: "themes_biblical_connections"},
    knownBooks: [{value: "John", chapters: 21}],
    selectedRouteId: targetId,
  });

  const articles = descendants(view).filter((item) => item.className === "narrative-explorer-related-passage"
    || item.className === "narrative-explorer-related-passage is-selected");
  const target = articles.find((item) => item.dataset.routeId === targetId);
  const heading = descendants(view).find((item) => item.dataset.narrativeRouteFocusId === targetId);
  assert.equal(articles.length, 6);
  assert.ok(target, "the hidden target route should be expanded into view");
  assert.match(target.className, /is-selected/);
  assert.equal(target.attributes["aria-current"], "true");
  assert.ok(heading, "the selected route should have a focusable heading");
  assert.equal(heading.attributes.tabindex, "-1");
  assert.match(heading.textContent, /John 1:6/);
  assert.ok(descendants(view).some((item) => item.attributes.role === "status" && /selected connection/i.test(item.textContent)));
});


test("route handoff resolves only a complete exact CKL record identity in the selected projection", () => {
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
  const data = projection({
    passage: {reference: "Jonah 1:17", book: "Jonah", chapter: 1, verse_start: 17, verse_end: 17, scope: "verse_range"},
    related_passages: {
      state: "available",
      query_status: "complete",
      description: "Passage routes are available from the records listed here.",
      authored_relationships: [],
      evidence_backed_bridges: [route],
      held_candidates: [{id: route.id, supporting_records: route.supporting_records}],
    },
  });
  const identity = {object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"};

  assert.equal(
    explorer.findVerifiedPassageRoute(data, route.id, identity, "Jonah 1:17")?.id,
    route.id,
  );
  for (const wrongIdentity of [
    {object_id: "wrong-parent", record_kind: "claim", record_id: "jonah-three-days"},
    {object_id: "jonah", record_kind: "evidence", record_id: "jonah-three-days"},
    {object_id: "jonah", record_kind: "claim", record_id: "another-claim"},
  ]) {
    assert.equal(explorer.findVerifiedPassageRoute(data, route.id, wrongIdentity, "Jonah 1:17"), null);
  }
  assert.equal(explorer.findVerifiedPassageRoute(data, "unknown-route", identity, "Jonah 1:17"), null);
  assert.equal(explorer.findVerifiedPassageRoute(data, route.id, identity, "Jonah 2:1"), null);

  data.passage.reference = "Jonah 1:18";
  assert.equal(explorer.findVerifiedPassageRoute(data, route.id, identity, "Jonah 1:18"), null);
  data.passage.reference = "Jonah 1:16-18";
  assert.equal(explorer.findVerifiedPassageRoute(data, route.id, identity, "Jonah 1:16-18")?.id, route.id);

  data.related_passages.query_status = "partial";
  assert.equal(explorer.findVerifiedPassageRoute(data, route.id, identity, "Jonah 1:17"), null);
  data.related_passages.query_status = "complete";
  data.related_passages.authored_relationships = [{
    ...route,
    id: route.id,
    provenance: "authored_ckl_relationship",
    supporting_records: undefined,
    supporting_record_ids: ["ckl:jonah#claim:jonah-three-days"],
  }];
  assert.equal(explorer.findVerifiedPassageRoute(data, route.id, identity, "Jonah 1:17"), null);
});

test("related passage lists omit routes whose endpoints exclude the selected passage", () => {
  const unrelatedRoute = {
    id: "jonah-1-17-matthew-12-40-sign-of-jonah",
    provenance: "ckl_documented_claim",
    source_passage: "Jonah 1:17",
    destination_passage: "Matthew 12:40",
    relationship_category: "later_canonical_reception",
    explanation: "Matthew compares Jonah's narrated duration with the Son of Man's time in the earth.",
    uncertainty: "The idiom and chronology remain uncertain.",
    supporting_records: [{object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"}],
  };
  const view = explorer.renderOverview(projection({
    passage: {reference: "Exodus 3:1-5", book: "Exodus", chapter: 3, verse_start: 1, verse_end: 5, scope: "verse_range"},
    related_passages: {
      state: "available",
      query_status: "complete",
      authored_relationships: [],
      evidence_backed_bridges: [unrelatedRoute],
    },
  }), {document: fakeDocument(), view: {kind: "category", categoryId: "themes_biblical_connections"}});

  assert.doesNotMatch(view.textContent, /jonah-1-17-matthew-12-40-sign-of-jonah|Connection to Matthew 12:40/);
  assert.match(view.textContent, /No source-linked connection is available here/);
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
  }), {document: fakeDocument(), view: {kind: "category", categoryId: "themes_biblical_connections"}});
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
  }), {document: fakeDocument(), view: {kind: "category", categoryId: "themes_biblical_connections"}});

  assert.match(view.textContent, /The earlier text is Genesis 1:1-5; the later passage is John 1:1-18/);
  assert.match(view.textContent, /You can follow this link from either passage/i);
});

test("the Jonah-Matthew route displays its reception direction, explanation, and uncertainty from Matthew", () => {
  const view = explorer.renderOverview(projection({
    passage: {reference: "Matthew 12:40", book: "Matthew", chapter: 12, verse_start: 40, verse_end: 40, scope: "verse_range"},
    related_passages: {
      state: "available",
      query_status: "complete",
      description: "Passage routes are available from the records listed here.",
      authored_relationships: [],
      evidence_backed_bridges: [{
        id: "jonah-1-17-matthew-12-40-sign-of-jonah",
        provenance: "ckl_documented_claim",
        source_passage: "Matthew 12:40",
        destination_passage: "Jonah 1:17",
        source_text_passage: "Jonah 1:17",
        receiving_text_passage: "Matthew 12:40",
        relationship_category: "later_canonical_reception",
        evidence_layer: "later_reception",
        direction: "source_to_receiving_text",
        relationship_mode: "documented_interpretation",
        explanation: "Matthew 12:40 explicitly compares Jonah’s narrated three days and nights in the fish with the Son of Man’s time in the heart of the earth. Jonah 1:17 is standard English numbering for MT/LXX Jonah 2:1.",
        uncertainty: "Ancient time reckoning and idiom leave the chronology unsettled; the expression ‘heart of the earth’ and the comparison’s broader theological interpretation also remain uncertain.",
        human_scholarly_approval: "not_recorded",
        supporting_records: [{id: "ckl:jonah#claim:jonah-three-days", source_ids: ["jonah-masoretic", "jonah-new-testament"]}],
        supporting_sources: [
          {id: "jonah-masoretic", title: "Masoretic Text of Jonah", source_type: "scripture"},
          {id: "jonah-new-testament", title: "New Testament sign-of-Jonah passages", source_type: "scripture"},
        ],
      }],
    },
  }), {document: fakeDocument(), view: {kind: "category", categoryId: "themes_biblical_connections"}, knownBooks: [{value: "Jonah", chapters: 4}, {value: "Matthew", chapters: 28}]});

  assert.match(view.textContent, /Later use of Scripture/);
  assert.doesNotMatch(view.textContent, /Later canonical reception · Later canonical reception/);
  assert.match(view.textContent, /The earlier text is Jonah 1:17; the later passage is Matthew 12:40/);
  assert.match(view.textContent, /Matthew 12:40 explicitly compares Jonah’s narrated three days and nights/);
  assert.match(view.textContent, /MT\/LXX Jonah 2:1/);
  assert.match(view.textContent, /Ancient time reckoning and idiom leave the chronology unsettled/);
  assert.match(view.textContent, /the comparison’s broader theological interpretation also remain uncertain/);
  assert.doesNotMatch(view.textContent, /ckl:jonah#claim:jonah-three-days|jonah-masoretic|jonah-new-testament/);
  assert.match(view.textContent, /Masoretic Text of Jonah/);
  assert.match(view.textContent, /New Testament sign-of-Jonah passages/);
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
  const overview = explorer.renderOverview(data, {document: trackedDocument});
  const root = renderCategory(data, "biblical_narrative", {document: trackedDocument, onNavigate: (item, action) => navigations.push({item, action})});
  const archaeologyView = renderCategory(data, "archaeology_ancient_history", {document: trackedDocument});
  const geographyView = renderCategory(data, "biblical_geography", {document: trackedDocument, onNavigate: (item, action) => navigations.push({item, action})});
  const cosmicView = renderCategory(data, "divine_council_cosmic_geography", {document: trackedDocument, onNavigate: (item, action) => navigations.push({item, action})});
  const narrativeCard = descendants(root).find((child) => child.dataset.sectionId === "biblical_narrative");
  const geographyCard = descendants(geographyView).find((child) => child.dataset.sectionId === "biblical_geography");
  const cosmicCard = descendants(cosmicView).find((child) => child.dataset.sectionId === "divine_council_cosmic_geography");
  const narrativePreviewList = narrativeCard.children.find((element) => element.className === "narrative-explorer-previews");
  const allText = [overview, root, archaeologyView, geographyView, cosmicView].map((view) => view.textContent).join(" ");

  for (const title of ["Biblical Narrative", "Archaeology & Ancient History", "Biblical Geography", "Divine Council & Cosmic Geography", "Themes & Biblical Connections", "People, Events & Relationships"]) {
    assert.match(overview.textContent, new RegExp(title.replace(/[&]/g, "\\&")));
  }
  assert.equal(descendants(overview).filter((element) => element.tagName === "ARTICLE").length, 0);
  assert.match(overview.textContent, /What to notice/);
  assert.doesNotMatch(overview.textContent, /\d+ linked records|No linked records returned|source_domain|canonical_knowledge_library/);
  assert.doesNotMatch(geographyView.textContent, /Maps: 3 source records found|pilot-place|maps:01-eden/);
  assert.match(archaeologyView.textContent, /No source-linked research was found|No source-linked findings met this topic's reader filter/);
  assert.equal(narrativePreviewList.children.length, 0, "records with incomplete citations stay out of reader promotion");
  assert.doesNotMatch(narrativeCard.textContent, /80 linked records|Claim 0|Claim 79|Show \d+ more records/);
  assert.doesNotMatch(allText, /Genesis 1:1-31|high|probable|tablet-k|Original relationship types: direct|<img src=x onerror=alert\(1\)>/);
  assert.equal(created.some((element) => element.tagName === "IMG"), false);
  assert.doesNotMatch(geographyView.textContent, /40|latitude|longitude|identification_unresolved/);
  assert.equal(descendants(geographyCard).filter((element) => element.className.includes("narrative-explorer-item-action")).length, 1, "duplicate map previews collapse to one item");
  assert.equal(descendants(cosmicCard).filter((element) => element.className.includes("narrative-explorer-item-action")).length, 0);
  const initialMapAction = descendants(geographyCard).find((element) => element.className.includes("narrative-explorer-item-action"));
  initialMapAction.click();
  assert.equal(navigations[0].action.mapFocusAllowed, true);
  navigations.length = 0;
  const inspect = geographyCard.children.find((element) => element.className.includes("narrative-explorer-inspect"));
  inspect.click();
  const fullList = geographyCard.children.find((element) => element.className === "narrative-explorer-record-list");
  const mapActions = descendants(fullList).filter((element) => element.className.includes("narrative-explorer-item-action"));
  mapActions.forEach((action) => action.click());
  const navigationByTarget = new Map(navigations.map((entry) => [entry.item.navigation.target_id, entry.action]));
  assert.equal(navigationByTarget.get("maps:00-eden-safe").mapFocusAllowed, true);
  assert.equal(navigationByTarget.get("maps:01-eden-uncertain").mapFocusAllowed, false);
  assert.equal(navigationByTarget.has("maps:02-no-selection"), false);
  assert.ok(mapActions.some((action) => /try to focus this item/.test(action.textContent)));
  assert.ok(mapActions.some((action) => /general Maps Explorer/.test(action.textContent)));
  const unsupportedCard = descendants(geographyCard).find((element) => element.tagName === "ARTICLE" && element.textContent.includes("Collection-only place"));
  assert.equal(descendants(unsupportedCard).filter((element) => element.className.includes("narrative-explorer-item-action")).length, 0);
  assert.doesNotMatch(allText, /shared motifs prove direct quotation/i);
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
    items: [physical, ...concepts.map((item) => readerEligible(item)), readerEligible(keywordTrap)],
  });

  const physicalView = renderCategory(data, "biblical_geography", {document: fakeDocument()});
  const cosmicView = renderCategory(data, "divine_council_cosmic_geography", {document: fakeDocument()});
  const physicalCard = descendants(physicalView).find((element) => element.dataset.sectionId === "biblical_geography");
  const cosmicCard = descendants(cosmicView).find((element) => element.dataset.sectionId === "divine_council_cosmic_geography");
  physicalCard.children.find((element) => element.className.includes("narrative-explorer-inspect")).click();
  cosmicCard.children.find((element) => element.className.includes("narrative-explorer-inspect")).click();
  const lines = `${physicalView.textContent} ${cosmicView.textContent}`;
  assert.doesNotMatch(lines, /pilot-place|Physical identification status|Place identification confidence|Dispute status|Passage relationship|Original relationship types/);
  assert.match(lines, /Source: Test map catalog/);
  assert.match(lines, /License: CC BY 4\.0/);
  assert.match(lines, /Open source/);
  assert.match(lines, /exact location remains uncertain, so no map point is shown/i);
  assert.doesNotMatch(lines, /identification_unresolved|no_geometry|\blow\b/);
  assert.match(lines, /Sacred-space interpretation/);
  assert.match(lines, /Sacred-space guarding context/);
  assert.match(lines, /Heavenly assembly language/);
  assert.match(lines, /Ancient cosmology comparison/);
  assert.match(lines, /Divine beings with disputed interpretation/);
  assert.match(lines, /These do not establish physical locations/i);
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
  const data = projection({items: projection().items.map((item) => readerEligible(item))});
  const inspected = [];
  const root = renderCategory(data, "biblical_narrative", {
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
  const returned = explorer.returnToOrigin(third.state);
  assert.equal(returned.activeIndex, 0);
  assert.deepEqual(returned.originSelection, explorer.createTrail(origin).originSelection);
  assert.equal(explorer.trailReturnFocusId(returned), "item:ckl:genesis#evidence:g2-garden-planting-presence");
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
  const view = explorer.renderEvidenceDetail(readerEligible(source), [edge], trail, {
    document: fakeDocument(),
    resolveEvidenceTarget: (id) => id === target.id ? target : null,
    onFollowEvidence: (...args) => opened.push(args),
  });
  const button = descendants(view).find((element) => element.tagName === "BUTTON" && element.textContent.includes("Target evidence"));

  assert.ok(button);
  assert.match(view.textContent, /Related research/);
  assert.match(view.textContent, /This is a link between two research records, not a direct link between Bible passages/);
  assert.match(view.textContent, /A recorded comparison does not establish literary borrowing or dependence/);
  assert.match(view.textContent, /Why it connects: Readers can inspect the comparison without treating it as borrowing/);
  assert.match(view.textContent, /Related passages to read: Psalm 82:1-8/);
  assert.match(view.textContent, /Ancient writing for comparison \(not Scripture\): KTU 1.1-1.2/);
  assert.match(view.textContent, /A. Scholar, 2013/);
  assert.match(view.textContent, /Comparison does not establish literary dependence/);
  assert.doesNotMatch(view.textContent, /Curation confidence|CKL evidence certainty|Human scholarly approval|Curation status|not_recorded|textually_explicit/);
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
  const detail = explorer.renderEvidenceDetail(readerEligible(target), [], followed.state, {document: fakeDocument()});
  assert.match(detail.textContent, /You opened this research from another linked research item/);
  assert.doesNotMatch(detail.textContent, /CKL|evidence IDs|Destination resolution|compared-with/);
  assert.match(detail.textContent, /without treating it as borrowing|does not establish literary dependence/i);
  assert.match(detail.textContent, /Why it connects: Readers can inspect the comparison without treating it as borrowing/);
  assert.match(detail.textContent, /Recorded comparative evidence/);
  assert.match(detail.textContent, /Comparison does not establish literary dependence/);
  assert.doesNotMatch(detail.textContent, /Human scholarly approval|Curation confidence|major_scholarly_disagreement|in_review|draft|target-study/);
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
  assert.match(view.textContent, /Why it connects: The connection records a later Christian reception of Israel's Scriptures/);
  assert.match(view.textContent, /Passages discussed here: Acts 2:22-36/);
  assert.doesNotMatch(view.textContent, /Connection type:/);
  assert.match(view.textContent, /Acts 2 is a later Christian interpretation/);
  assert.doesNotMatch(view.textContent, /Original CKL|temporal layer|Curation confidence|evidence certainty|Human scholarly approval|not_recorded/);

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
  const view = explorer.renderEvidenceDetail(readerEligible(item, "Exodus 14:21-31"), [edge], trail, {
    document: fakeDocument(),
    knownBooks: passages.map(({book, chapters}) => ({value: book, chapters})),
    onOpenPassage: (...args) => opened.push(args),
  });

  assert.match(view.textContent, /Passages discussed here: Exodus 14:21-31/);
  assert.match(view.textContent, /Some source references lack reader-ready bibliographic details/);
  assert.match(view.textContent, /New Exodus is a useful scholarly description/);
  assert.doesNotMatch(view.textContent, /the-exodus\/isaiah-43|Human scholarly approval|Source subject|new-exodus-theme|one-way/);

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
    const view = explorer.renderEvidenceDetail(readerEligible(source, "Genesis 6:1-4"), [edge], trail, {
      document: fakeDocument(),
      resolveEvidenceTarget: () => { resolutionCalls += 1; return hiddenTarget; },
      onFollowEvidence() {},
    });
    assert.match(view.textContent, /linked research (?:is not available|could not be opened|could not be confirmed)/i);
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
  const wrongParentView = explorer.renderEvidenceDetail(readerEligible(source, "Genesis 6:1-4"), [edge], trail, {
    document: fakeDocument(),
    resolveEvidenceTarget: () => wrongParent,
    onFollowEvidence() {},
  });
  assert.match(wrongParentView.textContent, /linked research could not be confirmed/i);
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
  const incomingView = explorer.renderEvidenceDetail(readerEligible(reverse), [incoming], explorer.createTrail({book: "Genesis", chapter: 1, reference: "Genesis 1"}), {
    document: fakeDocument(),
    resolveEvidenceTarget: () => source,
    onFollowEvidence() {},
  });
  assert.match(incomingView.textContent, /Related research/);
  assert.doesNotMatch(incomingView.textContent, /incoming-edge|does not create a reverse navigation edge/);
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
  const reciprocalView = explorer.renderEvidenceDetail(readerEligible(reverse), [forwardReciprocal, reverseEdge], explorer.createTrail({book: "Genesis", chapter: 1, reference: "Genesis 1"}), {
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
    applicable_passage_anchors: [{reference: "Psalm 82:1-8", relationship: "direct"}],
  };
  const trail = explorer.createTrail({book: "Deuteronomy", chapter: 32, reference: "Deuteronomy 32:8-9"});
  const opened = [];
  const view = explorer.renderEvidenceDetail(readerEligible(item, "Psalm 82:1-8"), [], trail, {
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
      basis: {kind: "ckl_related_object", notes: "This research records a later sanctuary development; the two building histories are distinct."},
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
  const view = explorer.renderEvidenceDetail(readerEligible(item, "Psalm 82"), connections, explorer.createTrail({
    book: "Psalm", chapter: 82, reference: "Psalm 82",
  }), {
    document: fakeDocument(),
    knownBooks: [{value: "Psalm", chapters: 150}],
    onFollowConnection: () => {},
  });

  assert.doesNotMatch(view.textContent, /ckl:creation#evidence:comparison|ugaritic-study|in_review|human_review_required/);
  assert.match(view.textContent, /Ancient writing compared with this passage/);
  assert.match(view.textContent, /Scholars disagree about this interpretation|Some conclusions about this evidence remain unsettled/);
  assert.doesNotMatch(view.textContent, /probable|major_scholarly_disagreement|in_review|draft|Human review required/);
  assert.match(view.textContent, /The Baal Cycle/);
  assert.match(view.textContent, /Mark S\. Smith/);
  assert.match(view.textContent, /Brill/);
  assert.match(view.textContent, /1994/);
  assert.match(view.textContent, /Tablet II/);
  assert.doesNotMatch(view.textContent, /ugaritic-study/);
  assert.match(view.textContent, /This research records a later sanctuary development; the two building histories are distinct/);
  assert.match(view.textContent, /The reverse edge is recorded/);
  assert.doesNotMatch(view.textContent, /original CKL label|Direction:|incoming-only|does not create a reverse navigation edge|reciprocal CKL edge/);
  assert.match(view.textContent, /does not establish how the two topics are related/i);
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
  assert.doesNotMatch(malformedReciprocal.textContent, /Direction:|reciprocal CKL edge/);
  assert.doesNotMatch(malformedReciprocal.textContent, /A reciprocal CKL edge is recorded/);
});

test("research without a usable cited source stays withheld from reader detail", () => {
  const item = {
    ...projection().items[2],
    title: "Unreviewed cosmic language note",
    claim_text: "A draft observation that needs editorial review.",
    review_status: "in_review",
    content_status: "draft",
    human_review_required: true,
    source_ids: ["missing-source-record"],
    sources: [],
  };
  const view = explorer.renderEvidenceDetail(item, [], null, {document: fakeDocument()});
  assert.equal(presentationPolicy.tierFor(item), "withheld_from_reader_promotion");
  assert.equal(view.className, "narrative-explorer-evidence-unavailable");
  assert.match(view.textContent, /cannot be opened from the current passage view/i);
  assert.match(view.textContent, /research tools/);
  assert.doesNotMatch(view.textContent, /Draft|awaiting human review|in_review|human_review_required|missing-source-record|CKL ID/);
});

test("reader cards hide editorial review labels while preserving research eligibility rules", () => {
  const data = projection();
  const draftEvidenceId = "ckl:creation#evidence:comparison";
  data.items = data.items.map((item) => item.id === draftEvidenceId
    ? readerEligible({...item, review_status: "in_review", content_status: "draft", human_review_required: true})
    : item);

  const preview = renderCategory(data, "archaeology_ancient_history", {document: fakeDocument()});
  const card = descendants(preview).find((element) =>
    element.className === "narrative-explorer-item" && element.textContent.includes("Ancient textual comparison"));
  assert.ok(card);
  assert.doesNotMatch(card.textContent, /Draft|awaiting human review|in_review|human_review_required|Content state/);
  assert.match(card.textContent, /How we know/);
  assert.match(card.textContent, /source is cited, but its support for this claim was not independently checked/i);

  const published = renderCategory(projection(), "biblical_narrative", {document: fakeDocument()});
  assert.doesNotMatch(published.textContent, /Draft evidence|awaiting human review|in_review|human_review_required/);
});

test("reader source disclosure replaces bibliographic diagnostics with a plain limitation", () => {
  const item = {
    ...projection().items[0],
    id: "ckl:sample#claim:incomplete-bibliography",
    title: "An observation with an incomplete citation",
    applicable_passage_anchors: [{reference: "Genesis 1:1", relationship: "direct"}],
    source_ids: ["sample-source"],
    sources: [{
      id: "sample-source",
      details_available: true,
      bibliographic_details: {title: "A Study", author: "A. Author", locator: "p. 12"},
    }],
  };
  const data = projection({
    items: [item],
    sections: [section("biblical_narrative", [item.id], "available")],
  });
  const view = renderCategory(data, "biblical_narrative", {document: fakeDocument()});
  const card = descendants(view).find((element) => element.className === "narrative-explorer-item");
  const sourceDisclosure = descendants(card).find((element) => element.className === "narrative-explorer-provenance");

  assert.match(sourceDisclosure.textContent, /A Study · A\. Author/);
  assert.match(sourceDisclosure.textContent, /Some citation details are unavailable/);
  assert.doesNotMatch(sourceDisclosure.textContent, /The citation is missing|sample-source|source_id/);
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
  const view = explorer.renderEvidenceDetail(readerEligible(item, "Exodus 25:8-9"), [edge], trail, {
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
  const evidenceView = explorer.renderEvidenceDetail(readerEligible(item, "Exodus 25"), [edge], atLimit, {
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
    assert.match(view.textContent, /connection trail has reached its navigation limit/i);
    assert.doesNotMatch(view.textContent, /Connection trail: \d+ of \d+ links followed/);
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
    readerEligible({id: "ckl:psalm-82#evidence:assembly", title: "Assembly-language evidence"}, "Psalm 82"),
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
  assert.match(view.textContent, /The Jerusalem temple is a distinct permanent structure/);
  assert.doesNotMatch(view.textContent, /later-sanctuary-development|Original relationship type|temporal layer|CKL/);
  assert.match(view.textContent, /does not by itself establish a relationship between Bible passages/i);
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
  assert.match(garden.textContent, /Scholars disagree about this interpretation/);
  assert.doesNotMatch(garden.textContent, /interpretive_uncertainty|ckl:/);

  const cherubim = render(readItem("genesis_3.json", "ckl:genesis#evidence:g3-cherubim-biblical-sacred-space-context"));
  assert.match(cherubim.textContent, /Scholarly interpretation/);
  assert.match(cherubim.textContent, /Exodus 25:18/);
  assert.doesNotMatch(cherubim.textContent, /ckl:|Source ID|Evidence ID/);

  const sons = render(readItem("genesis_6.json", "ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions"));
  const watchers = render(readItem("genesis_6.json", "ckl:genesis-flood-postflood-context#evidence:g6-second-temple-watchers-reception"));
  assert.match(sons.textContent, /Who the [“\"]?sons of God[”\"]? are and what the episode means remain disputed/i);
  assert.doesNotMatch(sons.textContent, /disputed position|major_scholarly_disagreement|ckl:/);
  assert.match(watchers.textContent, /Later reception/);
  assert.match(watchers.textContent, /attest later interpretation rather than adding details to Genesis/);
  assert.match(watchers.textContent, /does not establish Genesis's original meaning/i);
  assert.match(watchers.textContent, /timing label that needs checking/i);
  assert.doesNotMatch(watchers.textContent, /CKL|temporal_relation|later_canonical_reception/);

  const assembly = render(readItem("psalm_82.json", "ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language"));
  const ugaritic = render(readItem("psalm_82.json", "ckl:ancient-divine-assembly-imagery#evidence:ugaritic-council-comparison"));
  assert.match(assembly.textContent, /Textual observation/);
  assert.match(assembly.textContent, /This is a direct observation from Psalm 82/);
  assert.match(ugaritic.textContent, /Ancient writing compared with this passage/);
  assert.match(ugaritic.textContent, /relationship to biblical language remains uncertain/);
  assert.match(ugaritic.textContent, /not direct evidence for Psalm 82's author or audience/);

  const manuscript = render(readItem("deuteronomy_32.json", "ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant"));
  assert.match(manuscript.textContent, /Manuscript and text/);
  assert.match(manuscript.textContent, /different ancient textual witnesses preserve different wording|manuscripts preserve different wording/i);
  assert.doesNotMatch(manuscript.textContent, /textual_variant|ckl:|review_status|human_review_required/);
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
  assert.doesNotMatch(targetView.textContent, /lambert-babylonian-creation-2013|sarna-genesis-comparison|probable|major_scholarly_disagreement|in_review|draft|ckl:/);
  assert.match(targetView.textContent, /Babylonian Creation Myths/);
  assert.match(targetView.textContent, /Known witnesses and proposed composition dates span a broad range/);
  assert.match(targetView.textContent, /does not by itself establish a relationship between Bible passages/);
});

test("overview guides readers and explains coverage without linked-record counts", () => {
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
  const cardHost = descendants(root).find((element) => element.className === "narrative-explorer-sections");
  const topicCards = cardHost.children;
  const categoryView = (id) => renderCategory(data, id, {document: fakeDocument()});
  const narrative = categoryView("biblical_narrative");
  const archaeology = categoryView("archaeology_ancient_history");
  const geography = categoryView("biblical_geography");
  const cosmic = categoryView("divine_council_cosmic_geography");
  const theme = categoryView("themes_biblical_connections");
  const sectionCard = (view) => descendants(view).find((element) => element.className.includes("narrative-explorer-section is-focused"));

  assert.match(root.textContent, /Choose a topic to explore more research connected with this passage/);
  assert.equal(topicCards.length, 6);
  assert.equal(descendants(root).filter((element) => element.tagName === "ARTICLE").length, 0);
  assert.doesNotMatch([narrative, archaeology, geography, cosmic].map((view) => view.textContent).join(" "), /\d+ linked records|No records were found for this passage/);
  assert.match(geography.textContent, /could not check source availability/i);
  assert.match(cosmic.textContent, /some research may be missing from this topic/i);
  const coverageLines = [narrative, archaeology, geography, cosmic].flatMap((view) =>
    descendants(view).filter((element) => element.className === "narrative-explorer-coverage"));
  assert.equal(coverageLines.length, 0);
  const discovery = descendants(theme).find((element) => element.className === "narrative-explorer-connection-discovery");
  const readerGuidance = descendants(discovery).find((element) => element.className === "narrative-explorer-section-heading");
  assert.match(readerGuidance.textContent, /A Scripture reference shows where evidence applies/i);
  assert.match(readerGuidance.textContent, /doesn't automatically mean two passages are connected/i);
  assert.doesNotMatch(readerGuidance.textContent, /CKL relationship|projection|metadata/i);
  assert.doesNotMatch([narrative, archaeology, geography, cosmic, theme].map((view) => view.textContent).join(" "), /CKL parent records|\d+ claims · \d+ evidence records|source_domain/);
});

test("passage research cards use plain evidence labels and withhold internal identifiers", () => {
  const cases = [
    {
      file: "genesis_6_1_4.json",
      id: "ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions",
      label: "Scholarly interpretation",
      sourceId: "g2-doedens-sons-god",
      rawCategory: "worldview-concept",
    },
    {
      file: "genesis_6_1_4.json",
      id: "ckl:genesis-flood-postflood-context#evidence:g6-nephilim-and-mighty-men",
      label: "Scholarly interpretation",
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
      label: "Textual observation",
      sourceId: "psalm-82-hebrew-text",
      rawCategory: "worldview-concept",
    },
    {
      file: "psalm_82.json",
      id: "ckl:ancient-divine-assembly-imagery#evidence:ugaritic-council-comparison",
      label: "Ancient writing compared with this passage",
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
    const root = renderCategory(data, sectionId, {document: fakeDocument(), onInspect: () => {}});
    const sectionCard = descendants(root).find((element) => element.dataset.sectionId === sectionId);
    const inspect = descendants(sectionCard).find((element) => element.className.includes("narrative-explorer-inspect"));
    inspect.click();
    const itemCard = descendants(sectionCard).find((element) => element.tagName === "ARTICLE"
      && descendants(element).some((child) => child.dataset.narrativeItemId === testCase.id));
    const label = descendants(itemCard).find((element) => element.className === "narrative-explorer-item-kind");
    const provenance = descendants(itemCard).find((element) => element.className === "narrative-explorer-provenance");

    assert.equal(label.textContent, testCase.label, `${testCase.id} should use its reader-facing evidence layer`);
    assert.match(provenance.textContent, /How we know/);
    const sourceTitles = (data.items.find((item) => item.id === testCase.id)?.sources || [])
      .map((source) => source.bibliographic_details?.title)
      .filter(Boolean);
    assert.ok(sourceTitles.some((title) => provenance.textContent.includes(title)), `${testCase.id} should disclose a cited source by title`);
    assert.doesNotMatch(provenance.textContent, /Evidence category:|Passage relationship:|Source ID:|source_id|ckl:|g2-doedens|g2-1-enoch|psalm-82-hebrew|smith-ugaritic/);
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
    const root = renderCategory(data, "themes_biblical_connections", {
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
      assert.match(card.textContent, /Connection context:|Why it matters here:/);
      assert.doesNotMatch(card.textContent, /Evidence anchor:|Comparison anchor:/, `${title} should not present an anchor as a connection`);
      const provenance = descendants(card).find((element) => element.className === "narrative-explorer-provenance");
      assert.ok(provenance, `${title} should retain expandable evidence provenance`);
      const previewBasis = descendants(card).find((element) => element.className === "narrative-explorer-preview-basis");
      assert.ok(previewBasis, `${title} should expose a recorded connection or relevance basis`);
      assert.ok(card.textContent.includes(previewBasis.textContent.replace(/^(Connection context|Why it matters here): /, "")), `${title} should retain the reader-relevant preview context`);
      assert.match(provenance.textContent, /Cited source|source supports this claim/);
      assert.doesNotMatch(provenance.textContent, /Original relationship types:|Passage relationship:|Source ID:|source_id|ckl:/);
      const sourceItem = data.items.find((item) => item.title === title);
      assert.doesNotMatch(provenance.textContent, /CKL parent object|Source ID:|Curation confidence/);
      const explore = descendants(card).find((element) => element.className.includes("narrative-explorer-item-inspect"));
      assert.equal(explore?.textContent, "Explore this evidence", `${title} should use reader-facing detail navigation`);
      explore.click();
    }

    assert.equal(inspected.length, testCase.titles.length, "the preview action should reuse the existing inspect callback");
    if (testCase.file === "genesis_6_1_4.json") {
      const sons = cards.find((element) => element.textContent.includes("Sons of God: documented interpretive positions"));
      assert.match(sons.textContent, /Who the [“\"]?sons of God[”\"]? are and what the episode means remain disputed/i);
      assert.doesNotMatch(sons.textContent, /Major scholarly disagreement/i);
      const watchers = cards.find((element) => element.textContent.includes("Second Temple Watchers reception"));
      const watcherQualification = descendants(watchers).find((element) => element.className === "narrative-explorer-item-qualification");
      assert.match(watcherQualification.textContent, /later writing/i);
      assert.match(watcherQualification.textContent, /timing label that needs checking/i);
      assert.doesNotMatch(watcherQualification.textContent, /CKL|metadata/i);
      assert.match(watchers.textContent, /Later reception/);
    }
    if (testCase.file === "psalm_82.json") {
      assert.match(cards[0].textContent, /identity of the figures addressed in Psalm 82 remains disputed/i);
      assert.doesNotMatch(cards[0].textContent, /Interpretation remains disputed/i);
      const comparison = cards.find((element) => element.textContent.includes("Ugaritic council imagery comparison"));
      assert.match(comparison.textContent, /Ancient writing compared with this passage/);
      assert.match(comparison.textContent, /disagreeing about .*identity of biblical plural beings/i);
      assert.match(comparison.textContent, /Ugaritic parallels.*relationship to biblical language remains uncertain/i);
      assert.doesNotMatch(comparison.textContent, /Major scholarly disagreement/i);
    }
    if (testCase.file === "deuteronomy_32_8_9.json") {
      assert.match(cards[0].textContent, /Manuscript and text/);
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

  assert.equal(action?.textContent, "Open research record");
  action.click();
  assert.equal(opened, 1);
  assert.doesNotMatch(detail.textContent, /CKL parent object|ckl:genesis|Source ID/);
});

test("uncertain evidence retains natural-language qualifications without exposing workflow states", () => {
  const fixturePath = path.join(__dirname, "../fixtures/narrative_explorer/ne5a_baseline/genesis_6_1_4.json");
  const data = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
  const sons = data.items.find((candidate) => candidate.title === "Sons of God: documented interpretive positions");
  const detail = explorer.renderEvidenceDetail(sons, [], null, {document: fakeDocument()});

  assert.match(detail.textContent, /identity of the figures and the force of the episode remain disputed/i);
  assert.doesNotMatch(detail.textContent, /major_scholarly_disagreement|review_status|in_review|draft|human_review_required/);

  const unspecified = {
    ...sons,
    title: "Unspecified evidence disagreement",
    claim_text: null,
    description: "The record does not explain what remains disputed.",
    rationale: {},
  };
  const fallbackDetail = explorer.renderEvidenceDetail(unspecified, [], null, {document: fakeDocument()});
  assert.match(fallbackDetail.textContent, /Some conclusions about this evidence remain unsettled\./);
  assert.doesNotMatch(fallbackDetail.textContent, /Major scholarly disagreement|identity of the.*sons of God|major_scholarly_disagreement/i);
});

test("connection preview distinguishes missing coverage from no recorded eligible relationships", () => {
  const noEdges = projection({connections: []});
  const noEdgeRoot = renderCategory(noEdges, "themes_biblical_connections", {document: fakeDocument()});
  const noEdgeDiscovery = descendants(noEdgeRoot).find((element) => element.className.includes("narrative-explorer-connection-discovery"));
  assert.match(noEdgeDiscovery.textContent, /No source-linked connection is ready to show for this passage/i);
  assert.doesNotMatch(noEdgeDiscovery.textContent, /No evidence exists/i);

  const unavailable = projection({
    coverage: projection().coverage.map((entry) => entry.domain === "ckl"
      ? {...entry, state: "unknown", query_status: "failed", reason_code: "ckl_lookup_failed"}
      : entry),
    connections: [],
  });
  const unavailableRoot = renderCategory(unavailable, "themes_biblical_connections", {document: fakeDocument()});
  const unavailableDiscovery = descendants(unavailableRoot).find((element) => element.className.includes("narrative-explorer-connection-discovery"));
  assert.match(unavailableDiscovery.textContent, /could not check source availability/i);
  assert.match(unavailableDiscovery.textContent, /Try again later/i);

  const partial = projection({
    coverage: projection().coverage.map((entry) => entry.domain === "ckl"
      ? {...entry, state: "partial", query_status: "partial", reason_code: "partial_results"}
      : entry),
    connections: [],
  });
  const partialRoot = renderCategory(partial, "themes_biblical_connections", {document: fakeDocument()});
  const partialDiscovery = descendants(partialRoot).find((element) => element.className.includes("narrative-explorer-connection-discovery"));
  assert.match(partialDiscovery.textContent, /No source-linked preview is ready from the returned records/i);
  assert.doesNotMatch(partialDiscovery.textContent, /No evidence exists/i);

  const fixturePath = path.join(__dirname, "../fixtures/narrative_explorer/ne5a_baseline/genesis_6_1_4.json");
  const partialWithRecords = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
  partialWithRecords.coverage = partialWithRecords.coverage.map((entry) => entry.domain === "ckl"
    ? {...entry, state: "partial", query_status: "partial", reason_code: "partial_results"}
    : entry);
  const partialRecordsRoot = renderCategory(partialWithRecords, "themes_biblical_connections", {document: fakeDocument()});
  const partialRecordsDiscovery = descendants(partialRecordsRoot).find((element) => element.className.includes("narrative-explorer-connection-discovery"));
  assert.match(partialRecordsDiscovery.textContent, /Some source records may be missing/i);
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

  assert.match(detail.textContent, /Passage where this research applies/);
  assert.match(detail.textContent, /shows where the research applies/i);
  assert.match(detail.textContent, /Passages where this research applies/);
  assert.doesNotMatch(detail.textContent, /Recorded CKL relationships|Passage anchors \(|Evidence scope:|This authored label is a descriptive association|ckl:/);

  const comparison = data.items.find((candidate) => candidate.id === "ckl:ancient-divine-assembly-imagery#evidence:ugaritic-council-comparison");
  const comparisonAnchor = data.connections.find((edge) => edge.source_id === comparison.id && edge.basis?.kind === "ckl_scripture_anchor");
  const comparisonDetail = explorer.renderEvidenceDetail(comparison, [comparisonAnchor], explorer.createTrail({book: "Psalms", chapter: 82, reference: "Psalms 82"}), {
    document: fakeDocument(),
    knownBooks: [{value: "Psalms", chapters: 150}],
  });
  assert.match(comparisonDetail.textContent, /Passage used for comparison/);
  assert.match(comparisonDetail.textContent, /Passages where this research applies/);
  assert.match(comparisonDetail.textContent, /does not by itself establish a relationship between passages/);
  assert.doesNotMatch(comparisonDetail.textContent, /Evidence scope:|This authored label is a descriptive association|ckl:/);
});
