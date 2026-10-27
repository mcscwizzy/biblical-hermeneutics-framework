const test = require("node:test");
const assert = require("node:assert/strict");

const discoveries = require("../../bhf_web/static/companion-discoveries.js");


class FakeElement {
  constructor(tagName, ownerDocument) {
    this.tagName = String(tagName).toUpperCase();
    this.ownerDocument = ownerDocument;
    this.children = [];
    this.className = "";
    this.dataset = {};
    this.hidden = false;
    this.textContent = "";
    this.type = "";
    this.attributes = {};
    this.classList = {
      add: (...names) => {
        const values = new Set(this.className.split(/\s+/).filter(Boolean));
        names.forEach((name) => values.add(name));
        this.className = [...values].join(" ");
      },
    };
  }

  append(...children) {
    this.children.push(...children);
  }

  replaceChildren(...children) {
    this.children = children;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }
}


function fixturePanel() {
  const document = {
    createElement: (tagName) => new FakeElement(tagName, document),
  };
  const selectors = {};
  for (const name of ["land", "discoveries"]) {
    selectors[`[data-companion-${name}-section]`] = new FakeElement("section", document);
    selectors[`[data-companion-${name}]`] = new FakeElement("div", document);
  }
  return {
    document,
    selectors,
    panel: {querySelector: (selector) => selectors[selector] || null},
  };
}


function card(id, type, action = null) {
  return {
    id,
    type,
    headline: `Headline ${id}`,
    body: `Body ${id}`,
    dig_in_summary: id === "place"
      ? "The linked place locates the passage's travel detail in the lakeside setting."
      : null,
    evidence_ids: ["evidence-1"],
    confidence: "high",
    interpretation_level: type === "why_it_matters" ? "inference" : "fact",
    dig_deeper_actions: [
      {type: "show_evidence", label: "View evidence"},
      ...(action ? [action] : []),
    ],
  };
}


test("discovery cards render bounded sections with grounded Dig In evidence", () => {
  const {panel, selectors} = fixturePanel();
  const context = {
    presentation_packet: {
      presentation_mode: "bundled",
      cards: [
        card("place", "walk_the_land", {
          type: "open_map",
          label: "Show this location",
          target_id: "gerasene-region",
        }),
        ...[1, 2, 3, 4].map((number) => card(`fact-${number}`, "did_you_know")),
        card("meaning", "why_it_matters"),
      ],
    },
    presentation_evidence: [{
        id: "evidence-1",
        claim: "The supplied evidence claim.",
        category: "geography",
        confidence: "high",
        sources: [{id: "source-1", title: "Curated map source"}],
      }],
  };

  discoveries.render(panel, context);

  assert.equal(selectors["[data-companion-land-section]"].hidden, false);
  assert.equal(selectors["[data-companion-discoveries-section]"].hidden, false);
  assert.equal(selectors["[data-companion-significance-section]"], undefined);
  assert.equal(selectors["[data-companion-land]"].children.length, 1);
  assert.equal(selectors["[data-companion-discoveries]"].children.length, 3);

  const rendered = selectors["[data-companion-land]"].children[0];
  const details = rendered.children[3];
  const explanation = details.children[1];
  const evidenceList = details.children[2];
  const evidence = evidenceList.children[1];
  const actions = details.children[3];
  assert.equal(details.tagName, "DETAILS");
  assert.equal(details.children[0].textContent, "Dig In");
  assert.equal(explanation.className, "companion-discovery-explanation");
  assert.equal(explanation.textContent, "The linked place locates the passage's travel detail in the lakeside setting.");
  assert.equal(evidenceList.children[0].textContent, "Evidence");
  assert.equal(evidence.children[0].textContent, "The supplied evidence claim.");
  assert.match(evidence.children[1].textContent, /Sources: Curated map source/);
  assert.equal(actions.children[0].textContent, "Actions");
  assert.equal(actions.children.length, 2);
  assert.equal(actions.children[1].dataset.presentationAction, "open_map");
  assert.equal(actions.children[1].dataset.presentationTarget, "gerasene-region");
});


test("Dig In omits duplicate explanations while keeping evidence and actions", () => {
  const {panel, selectors} = fixturePanel();
  const fallback = card("fallback", "did_you_know", {
    type: "explore_history",
    label: "Explore the historical setting",
  });
  fallback.dig_in_summary = null;
  discoveries.render(panel, {
    presentation_packet: {cards: [fallback]},
    presentation_evidence: [{
      id: "evidence-1",
      claim: "Visible raw evidence remains available.",
      category: "history",
      confidence: "high",
      sources: [{title: "Curated source"}],
    }],
  });

  const details = selectors["[data-companion-discoveries]"].children[0].children[3];
  fallback.dig_in_summary = "Body fallback";
  discoveries.render(panel, {
    presentation_packet: {cards: [fallback]},
    presentation_evidence: [{
      id: "evidence-1",
      claim: "Visible raw evidence remains available.",
      category: "history",
      confidence: "high",
      sources: [{title: "Curated source"}],
    }],
  });
  const duplicateDetails = selectors["[data-companion-discoveries]"].children[0].children[3];
  assert.equal(duplicateDetails.children.length, 3);
  assert.equal(duplicateDetails.children[1].children[0].textContent, "Evidence");
  assert.equal(duplicateDetails.children[1].children[1].children[0].textContent, "Visible raw evidence remains available.");
  assert.equal(duplicateDetails.children[2].children[1].dataset.presentationAction, "explore_history");
  assert.equal(duplicateDetails.children.some((child) => child.className === "companion-discovery-explanation"), false);

  fallback.dig_in_summary = "This detail matters.";
  discoveries.render(panel, {
    presentation_packet: {cards: [fallback]},
    presentation_evidence: [{
      id: "evidence-1",
      claim: "Visible raw evidence remains available.",
      category: "history",
      confidence: "high",
      sources: [{title: "Curated source"}],
    }],
  });
  assert.equal(
    selectors["[data-companion-discoveries]"].children[0].children[3].children
      .some((child) => child.className === "companion-discovery-explanation"),
    false,
  );
});


test("legacy standalone significance packets never render as discovery cards", () => {
  const {panel, selectors} = fixturePanel();
  discoveries.render(panel, {
    presentation_packet: {cards: [card("legacy", "why_it_matters")]},
  });

  assert.equal(selectors["[data-companion-discoveries-section]"].hidden, true);
  assert.deepEqual(selectors["[data-companion-discoveries]"].children, []);
});


test("hidden discovery mode clears cards and sections", () => {
  const {panel, selectors} = fixturePanel();
  discoveries.render(panel, {
    presentation_packet: {cards: [card("fact", "did_you_know")]},
  }, {visible: false});

  assert.equal(selectors["[data-companion-discoveries-section]"].hidden, true);
  assert.deepEqual(selectors["[data-companion-discoveries]"].children, []);
});


test("Walk the Land navigation consolidates only an exact map ID already shown in Locations", () => {
  const {panel, selectors} = fixturePanel();
  const shared = card("walk-shared", "walk_the_land", {
    type: "open_map", label: "Open map", target_id: "map-exact-1",
  });
  const distinct = card("walk-distinct", "walk_the_land", {
    type: "open_map", label: "Open map", target_id: "map-exact-2",
  });
  discoveries.render(panel, {
    presentation_packet: {cards: [shared]},
    locations: {items: [{origin: "maps", id: "map-exact-1", title: "Same Place"}]},
  });
  assert.equal(selectors["[data-companion-land-section]"].hidden, true);
  assert.equal(selectors["[data-companion-land]"].children.length, 0);

  discoveries.render(panel, {
    presentation_packet: {cards: [distinct]},
    locations: {items: [{origin: "maps", id: "map-exact-1", title: "Same Place"}]},
  });
  assert.equal(selectors["[data-companion-land-section]"].hidden, false);
  assert.equal(selectors["[data-companion-land]"].children.length, 1);
});


test("grounded map and entity actions dispatch to existing BHF resources", async () => {
  const calls = [];
  const options = {
    mapPlaceIds: new Set(["corinth"]),
    openResource: async (resource, values) => calls.push(["resource", resource, values]),
    openCanonicalDetail: async (target) => calls.push(["canonical", target]),
  };
  const mapButton = {
    dataset: {presentationAction: "explore_place", presentationTarget: "corinth"},
  };
  const personButton = {
    dataset: {presentationAction: "explore_person", presentationTarget: "abigail"},
  };

  assert.equal(await discoveries.dispatchAction(mapButton, options), true);
  assert.equal(await discoveries.dispatchAction(personButton, options), true);
  assert.deepEqual(calls, [
    ["resource", "maps", {
      trigger: mapButton,
      mapFocus: {kind: "place", targetId: "corinth", acknowledgeFocus: true},
    }],
    ["resource", "canonical", {trigger: personButton}],
    ["canonical", "abigail"],
  ]);
});


test("unknown or unfulfillable actions do not navigate", async () => {
  const calls = [];
  const handled = await discoveries.dispatchAction(
    {dataset: {presentationAction: "explore_person"}},
    {openResource: async (...values) => calls.push(values)},
  );

  assert.equal(handled, false);
  assert.deepEqual(calls, []);
});


function verifiedHandoffFixture(identity) {
  const discovery = {
    id: "discovery-1",
    type: "did_you_know",
    evidence_ids: ["evidence-1"],
  };
  const route = {
    id: "genesis-1-john-1-creation-word",
    provenance: "ckl_documented_claim",
    source_passage: "Genesis 1:1-5",
    destination_passage: "John 1:1-5",
    relationship_category: "interpretive_association",
    evidence_layer: "thematic_interpretation",
    direction: "interpretive_comparison",
    explanation: "John's Logos language is read alongside creation and wisdom traditions.",
    uncertainty: "This does not establish direct borrowing or a single source.",
    supporting_records: [{
      id: "ckl:john#claim:john-logos",
      object_id: "john",
      record_kind: "claim",
      record_id: "john-logos",
    }],
  };
  return {
    discovery,
    context: {
      reference: "Genesis 1:1-5",
      presentation_packet: {cards: [discovery]},
      presentation_evidence: [{id: "evidence-1", ckl_record_identity: identity}],
    },
    projection: {
      passage: {reference: "Genesis 1:1-5"},
      related_passages: {
        state: "available",
        query_status: "complete",
        authored_relationships: [],
        evidence_backed_bridges: [route],
      },
    },
  };
}


test("verified handoff matches the complete CKL parent, record kind, and local ID", () => {
  const fixture = verifiedHandoffFixture({
    object_id: "john",
    record_kind: "claim",
    record_id: "john-logos",
  });

  const matches = discoveries.findVerifiedConnections(
    fixture.discovery,
    fixture.context,
    fixture.projection,
    {narrativeExplorerEnabled: true},
  );

  assert.deepEqual(matches.map((route) => route.id), ["genesis-1-john-1-creation-word"]);
});


test("wrong CKL identity, source-only matches, and topic matches never create a handoff", () => {
  for (const identity of [
    {object_id: "wrong-parent", record_kind: "claim", record_id: "john-logos"},
    {object_id: "john", record_kind: "evidence", record_id: "john-logos"},
    {object_id: "john", record_kind: "claim", record_id: "another-claim"},
    null,
  ]) {
    const fixture = verifiedHandoffFixture(identity);
    fixture.context.presentation_evidence[0].sources = [{id: "john-greek"}];
    fixture.context.presentation_evidence[0].topics = ["creation"];

    assert.deepEqual(discoveries.findVerifiedConnections(
      fixture.discovery,
      fixture.context,
      fixture.projection,
      {narrativeExplorerEnabled: true},
    ), []);
  }
});


test("only complete confirmed routes match, and multiple verified routes remain distinct choices", () => {
  const fixture = verifiedHandoffFixture({
    object_id: "john",
    record_kind: "claim",
    record_id: "john-logos",
  });
  const authored = {
    ...fixture.projection.related_passages.evidence_backed_bridges[0],
    id: "authored:curated-relationship:John 1:1-5",
    provenance: "authored_ckl_relationship",
    supporting_records: undefined,
    supporting_record_ids: ["ckl:john#claim:john-logos"],
  };
  fixture.projection.related_passages.authored_relationships.push(authored);
  fixture.projection.related_passages.held_candidates = [{
    id: "held-candidate",
    supporting_records: [{object_id: "john", record_kind: "claim", record_id: "john-logos"}],
  }];

  assert.deepEqual(discoveries.findVerifiedConnections(
    fixture.discovery,
    fixture.context,
    fixture.projection,
    {narrativeExplorerEnabled: true},
  ).map((route) => route.id), [
    "authored:curated-relationship:John 1:1-5",
    "genesis-1-john-1-creation-word",
  ]);

  fixture.projection.related_passages.query_status = "partial";
  assert.deepEqual(discoveries.findVerifiedConnections(
    fixture.discovery,
    fixture.context,
    fixture.projection,
    {narrativeExplorerEnabled: true},
  ), []);
  assert.deepEqual(discoveries.findVerifiedConnections(
    fixture.discovery,
    fixture.context,
    {...fixture.projection, related_passages: {
      ...fixture.projection.related_passages,
      query_status: "complete",
      authored_relationships: [],
      evidence_backed_bridges: [],
    }},
    {narrativeExplorerEnabled: false},
  ), []);
  assert.deepEqual(discoveries.findVerifiedConnections(
    fixture.discovery,
    fixture.context,
    {...fixture.projection, related_passages: {
      ...fixture.projection.related_passages,
      query_status: "complete",
      authored_relationships: [],
      evidence_backed_bridges: [{...fixture.projection.related_passages.evidence_backed_bridges[0], uncertainty: ""}],
    }},
    {narrativeExplorerEnabled: true},
  ), []);
});


test("Jonah to Matthew reception is offered only for the precise selected passage and supporting claim", () => {
  const discovery = {id: "jonah-discovery", type: "did_you_know", evidence_ids: ["three-days"]};
  const route = {
    id: "jonah-1-17-matthew-12-40-sign-of-jonah",
    provenance: "ckl_documented_claim",
    source_passage: "Jonah 1:17",
    destination_passage: "Matthew 12:40",
    relationship_category: "later_canonical_reception",
    explanation: "Matthew compares the narrated duration in Jonah with the time in the earth.",
    uncertainty: "The idiom and chronology remain uncertain.",
    supporting_records: [{object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"}],
  };
  const context = {
    reference: "Jonah 1:17",
    presentation_packet: {cards: [discovery]},
    presentation_evidence: [{
      id: "three-days",
      ckl_record_identity: {object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"},
    }],
  };
  const projection = {
    passage: {reference: "Jonah 1:17"},
    related_passages: {state: "available", query_status: "complete", authored_relationships: [], evidence_backed_bridges: [route]},
  };

  assert.deepEqual(discoveries.findVerifiedConnections(discovery, context, projection, {narrativeExplorerEnabled: true}).map((value) => value.id), [route.id]);
  assert.deepEqual(discoveries.findVerifiedConnections(discovery, context, {
    ...projection,
    passage: {reference: "Jonah 1"},
  }, {narrativeExplorerEnabled: true}), []);
  assert.deepEqual(discoveries.findVerifiedConnections(discovery, {
    ...context,
    reference: "Matthew 12:40",
  }, projection, {narrativeExplorerEnabled: true}), []);
});


test("held, absent, topic-only, and source-only candidates never create a route action", () => {
  const discovery = {id: "negative-control", type: "did_you_know", evidence_ids: ["evidence"]};
  const contextFor = (reference, identity = null) => ({
    reference,
    presentation_packet: {cards: [discovery]},
    presentation_evidence: [{
      id: "evidence",
      topics: ["Psalm 110", "enthronement"],
      sources: [{id: "psalm-110"}],
      ...(identity ? {ckl_record_identity: identity} : {}),
    }],
  });
  const context = contextFor("Acts 2:22-36");
  const authoredPsalm110Route = {
    id: "authored:existing-acts2-psalm110-route",
    provenance: "authored_ckl_relationship",
    source_passage: "Acts 2",
    destination_passage: "Psalm 110:1-7",
    relationship_category: "later_canonical_reception",
    explanation: "This existing authored pathway records Acts 2's reception of Psalm 110.",
    uncertainty: "Acts 2 is a later Christian interpretation of Israel's Scriptures.",
    supporting_record_ids: ["ckl:messiah-theme#source:psalm-110"],
  };
  const projection = {
    passage: {reference: "Acts 2:22-36"},
    related_passages: {
      state: "available",
      query_status: "complete",
      authored_relationships: [authoredPsalm110Route],
      evidence_backed_bridges: [],
      held_candidates: [{id: "psalm-110-acts-2-enthronement", supporting_records: authoredPsalm110Route.supporting_record_ids}],
    },
  };

  assert.deepEqual(discoveries.findVerifiedConnections(discovery, context, projection, {narrativeExplorerEnabled: true}), []);
  const psalm22Context = contextFor("Psalm 22:1-31", {
    object_id: "psalms", record_kind: "claim", record_id: "passion-psalms",
  });
  assert.deepEqual(discoveries.findVerifiedConnections(discovery, psalm22Context, {
    passage: {reference: "Psalm 22:1-31"},
    related_passages: {state: "not_represented", query_status: "complete", authored_relationships: [], evidence_backed_bridges: []},
  }, {narrativeExplorerEnabled: true}), []);
  const deuteronomyContext = contextFor("Deuteronomy 32:8-9", {
    object_id: "ancient-divine-assembly-imagery", record_kind: "claim", record_id: "assembly-textual-comparison",
  });
  assert.deepEqual(discoveries.findVerifiedConnections(discovery, deuteronomyContext, {
    passage: {reference: "Deuteronomy 32:8-9"},
    related_passages: {
      state: "not_represented",
      query_status: "complete",
      authored_relationships: [],
      evidence_backed_bridges: [],
      held_candidates: [{id: "deuteronomy-32-psalm-82-job-1-divine-assembly", supporting_records: ["ckl:ancient-divine-assembly-imagery#interpretive_note_sha256:held"]}],
    },
  }, {narrativeExplorerEnabled: true}), []);
});


test("a confirmed discovery renders the direct action with its route and exact CKL key", () => {
  const {panel, selectors} = fixturePanel();
  const fixture = verifiedHandoffFixture({
    object_id: "john",
    record_kind: "claim",
    record_id: "john-logos",
  });

  discoveries.render(panel, fixture.context, {
    narrativeExplorerEnabled: true,
    verifiedProjection: fixture.projection,
  });

  const details = selectors["[data-companion-discoveries]"].children[0].children[3];
  const actions = details.children.find((child) => child.className === "companion-discovery-actions");
  const button = actions.children[1];
  assert.equal(button.textContent, "Explore this connection");
  assert.equal(button.attributes["aria-label"], "Explore this connection");
  assert.equal(button.dataset.presentationAction, "explore_connection");
  assert.equal(button.dataset.presentationRouteId, "genesis-1-john-1-creation-word");
  assert.equal(button.dataset.presentationPassageReference, "Genesis 1:1-5");
  assert.equal(button.dataset.presentationObjectId, "john");
  assert.equal(button.dataset.presentationRecordKind, "claim");
  assert.equal(button.dataset.presentationRecordId, "john-logos");
});


test("direct action falls back to generic cross-references if its route is no longer available", async () => {
  const calls = [];
  const button = {
    dataset: {
      presentationAction: "explore_connection",
      presentationRouteId: "jonah-1-17-matthew-12-40-sign-of-jonah",
      presentationPassageReference: "Jonah 1:17",
      presentationObjectId: "jonah",
      presentationRecordKind: "claim",
      presentationRecordId: "jonah-three-days",
    },
  };

  const handled = await discoveries.dispatchAction(button, {
    narrativeExplorerEnabled: true,
    openResource: async (resource, values) => {
      calls.push([resource, values]);
      return false;
    },
  });

  assert.equal(handled, true);
  assert.equal(calls[0][0], "narrative_explorer");
  assert.deepEqual(calls[0][1].routeHandoff, {
    routeId: "jonah-1-17-matthew-12-40-sign-of-jonah",
    identity: {object_id: "jonah", record_kind: "claim", record_id: "jonah-three-days"},
    passageReference: "Jonah 1:17",
  });
  assert.equal(calls[1][0], "cross_references");
});
