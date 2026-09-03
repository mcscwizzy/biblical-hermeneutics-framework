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
  for (const name of ["land", "discoveries", "significance"]) {
    selectors[`[data-companion-${name}-section]`] = new FakeElement("section", document);
    selectors[`[data-companion-${name}]`] = new FakeElement("div", document);
  }
  selectors["[data-companion-presentation-status]"] = new FakeElement("p", document);
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
    dig_in_summary: id === "place" ? "A grounded explanation from the same evidence." : null,
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
      presentation_mode: "generated",
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
  assert.equal(selectors["[data-companion-significance-section]"].hidden, false);
  assert.equal(selectors["[data-companion-land]"].children.length, 1);
  assert.equal(selectors["[data-companion-discoveries]"].children.length, 3);
  assert.equal(selectors["[data-companion-significance]"].children.length, 1);

  const rendered = selectors["[data-companion-land]"].children[0];
  const details = rendered.children[3];
  const explanation = details.children[1];
  const evidenceList = details.children[2];
  const evidence = evidenceList.children[1];
  const actions = details.children[3];
  assert.equal(details.tagName, "DETAILS");
  assert.equal(details.children[0].textContent, "Dig In");
  assert.equal(explanation.children[0].textContent, "Why this is worth noticing");
  assert.equal(explanation.children[1].textContent, "A grounded explanation from the same evidence.");
  assert.equal(evidenceList.children[0].textContent, "Evidence");
  assert.equal(evidence.children[0].textContent, "The supplied evidence claim.");
  assert.match(evidence.children[1].textContent, /Sources: Curated map source/);
  assert.equal(actions.children[0].textContent, "Actions");
  assert.equal(actions.children.length, 2);
  assert.equal(actions.children[1].dataset.presentationAction, "open_map");
  assert.equal(actions.children[1].dataset.presentationTarget, "gerasene-region");
});


test("presentation lifecycle status is polite and never replaces deterministic cards", () => {
  const {panel, selectors} = fixturePanel();
  discoveries.render(panel, {
    presentation_packet: {cards: [card("local", "did_you_know")]},
  });
  const list = selectors["[data-companion-discoveries]"];
  const status = selectors["[data-companion-presentation-status]"];

  discoveries.renderStatus(panel, "generating");
  assert.equal(list.children[0].children[0].textContent, "Headline local");
  assert.equal(status.textContent, "Adding AI context…");
  assert.equal(status.hidden, false);
  assert.equal(status.attributes.role, "status");
  assert.equal(status.attributes["aria-live"], "polite");

  discoveries.renderStatus(panel, "fallback");
  assert.equal(status.textContent, "BHF evidence summary");

  discoveries.renderStatus(panel, "failed");
  assert.equal(status.textContent, "AI summary unavailable — showing BHF evidence.");
  assert.equal(list.children.length, 1);

  discoveries.renderStatus(panel, "unavailable", "provider_unavailable");
  assert.equal(status.textContent, "Connect an AI provider to add AI passage summaries.");

  discoveries.renderStatus(panel, "generated");
  assert.equal(status.textContent, "AI-assisted summary");

  discoveries.renderStatus(panel, "cancelled");
  assert.equal(status.textContent, "");
  assert.equal(status.hidden, true);
  assert.equal(list.children.length, 1);
});


test("Dig In fallback keeps evidence and actions when no AI explanation exists", () => {
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
  assert.equal(details.children.length, 3);
  assert.equal(details.children[1].children[0].textContent, "Evidence");
  assert.equal(details.children[1].children[1].children[0].textContent, "Visible raw evidence remains available.");
  assert.equal(details.children[2].children[1].dataset.presentationAction, "explore_history");
});


test("hidden discovery mode clears cards and sections", () => {
  const {panel, selectors} = fixturePanel();
  discoveries.render(panel, {
    presentation_packet: {cards: [card("fact", "did_you_know")]},
  }, {visible: false});

  assert.equal(selectors["[data-companion-discoveries-section]"].hidden, true);
  assert.deepEqual(selectors["[data-companion-discoveries]"].children, []);
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
      mapFocus: {kind: "place", targetId: "corinth"},
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
