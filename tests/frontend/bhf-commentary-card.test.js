const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");


class FakeElement {
  constructor(selectors = {}) {
    this.selectors = selectors;
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.hidden = false;
    this.textContent = "";
  }

  querySelector(selector) {
    return this.selectors[selector] || null;
  }

  replaceChildren(...children) {
    this.children = children;
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  removeAttribute(name) {
    delete this.attributes[name];
  }

  addEventListener() {}
}


function loadCard({requestJson} = {}) {
  const document = {
    readyState: "loading",
    querySelector: () => null,
    createElement: () => new FakeElement(),
    addEventListener: () => {},
  };
  const window = {
    BHFApi: requestJson ? {requestJson} : undefined,
    BHFStudySelection: {
      subscribe: () => {},
      getState: () => ({book: "Genesis", chapter: 13}),
    },
  };
  const context = vm.createContext({AbortController, document, window, fetch: async () => {}});
  vm.runInContext(
    fs.readFileSync("bhf_web/static/bhf-commentary-card.js", "utf8"),
    context,
  );
  return window.BHFCommentaryCard;
}


function makeRoot() {
  const selectors = {};
  [
    "[data-bhf-commentary-availability]",
    "[data-bhf-commentary-reference]",
    "[data-bhf-commentary-status]",
    "[data-bhf-commentary-body]",
    "[data-bhf-commentary-meta]",
    "[data-bhf-commentary-verse-refs]",
    "[data-bhf-commentary-evidence-count]",
  ].forEach((selector) => { selectors[selector] = new FakeElement(); });
  return new FakeElement(selectors);
}


test("availability labels preserve the unrecorded legacy state", () => {
  const api = loadCard();
  assert.equal(api.availabilityLabel("AVAILABLE"), "Context available");
  assert.equal(api.availabilityLabel("THIN"), "Limited contextual evidence");
  assert.equal(api.availabilityLabel("DATA_GAP"), "Contextual evidence not currently available");
  assert.equal(api.availabilityLabel(null), "Context status not recorded");
});


test("context card renders commentary, metadata, and clickable verse references", () => {
  const api = loadCard();
  const root = makeRoot();
  const instance = api.init(root);
  instance.render({
    available: true,
    release: "commentary-v1.0",
    book: "Genesis",
    chapter: 13,
    availability: "AVAILABLE",
    commentary: "Abram and Lot separate.",
    verse_references: ["Genesis 13:5-12"],
    evidence_count: 2,
  });

  assert.equal(root.hidden, false);
  assert.equal(root.dataset.state, "ready");
  assert.equal(root.dataset.availability, "AVAILABLE");
  assert.equal(root.selectors["[data-bhf-commentary-availability]"].textContent, "Context available");
  assert.equal(root.selectors["[data-bhf-commentary-body]"].textContent, "Abram and Lot separate.");
  assert.equal(root.selectors["[data-bhf-commentary-evidence-count]"].textContent, "2 evidence items");
  assert.equal(root.selectors["[data-bhf-commentary-verse-refs]"].children[0].textContent, "Genesis 13:5-12");
});


test("data gap card remains informative without an evidence explorer", () => {
  const api = loadCard();
  const root = makeRoot();
  api.init(root).render({
    available: true,
    release: "commentary-v1.0",
    book: "Leviticus",
    chapter: 2,
    availability: "DATA_GAP",
    commentary: "The chapter describes the offering procedures.",
    verse_references: ["Leviticus 2:1-16"],
    evidence_count: 0,
  });

  assert.equal(root.selectors["[data-bhf-commentary-availability]"].textContent, "Contextual evidence not currently available");
  assert.match(root.selectors["[data-bhf-commentary-status]"].textContent, /does not currently have anchored contextual evidence/);
  assert.equal(root.selectors["[data-bhf-commentary-evidence-count]"].textContent, "No anchored evidence cited");
});


test("thin card exposes its limitation without hiding the commentary", () => {
  const api = loadCard();
  const root = makeRoot();
  api.init(root).render({
    available: true,
    release: "commentary-v1.0",
    book: "Genesis",
    chapter: 13,
    availability: "THIN",
    commentary: "A concise contextual observation.",
    verse_references: [],
    evidence_count: 1,
  });

  assert.equal(root.selectors["[data-bhf-commentary-availability]"].textContent, "Limited contextual evidence");
  assert.equal(root.selectors["[data-bhf-commentary-body]"].textContent, "A concise contextual observation.");
  assert.equal(root.selectors["[data-bhf-commentary-evidence-count]"].textContent, "1 evidence item");
});


test("card exposes loading and error states without presenting stale content", async () => {
  const api = loadCard({requestJson: async () => { throw new Error("offline"); }});
  const root = makeRoot();
  const instance = api.init(root);
  const pending = instance.load({book: "Genesis", chapter: 13});

  assert.equal(root.dataset.state, "loading");
  assert.equal(root.selectors["[data-bhf-commentary-status]"].textContent, "Loading BHF context…");
  await pending;
  assert.equal(root.dataset.state, "error");
  assert.equal(root.selectors["[data-bhf-commentary-status]"].textContent, "BHF Context is unavailable right now.");
  assert.equal(root.selectors["[data-bhf-commentary-body]"].textContent, "");
});
