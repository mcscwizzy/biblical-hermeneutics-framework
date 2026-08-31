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
  const evidence = details.children[1].children[0];
  const actions = details.children[2];
  assert.equal(details.tagName, "DETAILS");
  assert.equal(details.children[0].textContent, "Dig In");
  assert.equal(evidence.children[0].textContent, "The supplied evidence claim.");
  assert.match(evidence.children[1].textContent, /Sources: Curated map source/);
  assert.equal(actions.children.length, 1);
  assert.equal(actions.children[0].dataset.presentationAction, "open_map");
  assert.equal(actions.children[0].dataset.presentationTarget, "gerasene-region");
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
