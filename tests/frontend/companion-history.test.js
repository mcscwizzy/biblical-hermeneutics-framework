const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

function loadHistoryController() {
  const stack = [{state: null, url: "/reader"}];
  let index = 0;
  const listeners = new Map();
  const fakeWindow = {
    location: {href: "/reader"},
    addEventListener: (type, listener) => listeners.set(type, listener),
    removeEventListener: (type) => listeners.delete(type),
    history: {
      get state() { return stack[index].state; },
      pushState(state, _title, url) {
        stack.splice(index + 1);
        stack.push({state, url});
        index += 1;
      },
      replaceState(state, _title, url) { stack[index] = {state, url}; },
      back() {
        if (index === 0) return;
        index -= 1;
        listeners.get("popstate")?.({state: stack[index].state});
      },
      forward() {
        if (index >= stack.length - 1) return;
        index += 1;
        listeners.get("popstate")?.({state: stack[index].state});
      },
    },
  };
  const previousWindow = global.window;
  global.window = fakeWindow;
  const modulePath = path.resolve(__dirname, "../../bhf_web/static/companion-history.js");
  delete require.cache[modulePath];
  require(modulePath);
  return {
    controller: fakeWindow.BHFCompanionHistory,
    browserHistory: fakeWindow.history,
    restore: () => {
      if (previousWindow === undefined) delete global.window;
      else global.window = previousWindow;
    },
  };
}

test("Companion Back and Forward restore the exact bounded Narrative Explorer trail", async () => {
  const {controller, browserHistory, restore} = loadHistoryController();
  const applied = [];
  const history = controller.create({apply: async (snapshot) => applied.push(snapshot)});
  const origin = {
    kind: "passage",
    id: "passage:Exodus 3:1-6",
    label: "Exodus 3:1-6",
    reference: "Exodus 3:1-6",
    selection: {
      book: "Exodus", chapter: 3, startVerse: 1, endVerse: 6,
      selectedVerses: [1, 2, 3, 4, 5, 6], selectedText: "Selected reader text",
      translation: "web", selectedWord: {lemma: "ehyeh"}, reference: "Exodus 3:1-6",
    },
    relationshipHops: 0,
    focusControlId: "",
  };
  const inspected = {
    kind: "evidence",
    id: "ckl:presence-theme#evidence:exodus-3",
    label: "Presence evidence",
    parentObjectId: "presence-theme",
    selection: origin.selection,
    relationshipHops: 0,
    focusControlId: "item:ckl:presence-theme#evidence:exodus-3",
  };
  const connected = {
    kind: "subject",
    id: "ckl:divine-presence",
    targetId: "divine-presence",
    subjectId: "divine-presence",
    label: "Divine Presence",
    relationship: {id: "edge-1", originalRelationshipType: "related-concept", direction: "one_way"},
    selection: origin.selection,
    relationshipHops: 1,
    focusControlId: "connection:edge-1",
  };
  const originalTrail = {originSelection: origin.selection, nodes: [origin], activeIndex: 0};
  const detailTrail = {originSelection: origin.selection, nodes: [origin, inspected], activeIndex: 1};
  const subjectTrail = {originSelection: origin.selection, nodes: [origin, inspected, connected], activeIndex: 2};
  try {
    history.initialize({state: "study", mode: "passage", resource: "narrative_explorer", trail: originalTrail});
    history.push({state: "study", mode: "passage", resource: "narrative_explorer", trail: detailTrail});
    history.push({state: "study", mode: "passage", resource: "narrative_explorer", trail: subjectTrail});
    history.backFromResource();
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(history.current().trail, detailTrail);
    history.backFromResource();
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(history.current().trail, originalTrail);
    browserHistory.forward();
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(history.current().trail, detailTrail);
    browserHistory.forward();
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(history.current().trail, subjectTrail);
    assert.equal(applied.length, 4);

    history.replace({
      state: "study",
      mode: "passage",
      resource: "narrative_explorer",
      trail: {
        originSelection: origin.selection,
        nodes: [origin, ...Array.from({length: 20}, (_value, nodeIndex) => ({
          kind: "subject",
          id: `ckl:subject-${nodeIndex}`,
          targetId: `subject-${nodeIndex}`,
          subjectId: `subject-${nodeIndex}`,
          label: `Subject ${nodeIndex}`,
          relationshipHops: Math.min(nodeIndex, 3),
          selection: origin.selection,
        }))],
        activeIndex: 20,
      },
    });
    assert.equal(history.current().trail.nodes.length, 12);
    assert.equal(history.current().trail.activeIndex, 11);
  } finally {
    history.destroy();
    restore();
  }
});

test("Companion history preserves the basis of an authored evidence relationship hop", () => {
  const {controller, restore} = loadHistoryController();
  const history = controller.create();
  const selection = {book: "Genesis", chapter: 1, reference: "Genesis 1"};
  const relationship = {
    id: "evidence-edge",
    sourceId: "ckl:creation#evidence:source",
    targetId: "ckl:creation#evidence:target",
    originalRelationshipType: "compared-with",
    direction: "reciprocal",
    basisKind: "ckl_related_evidence",
    parentObjectId: "creation",
    localRecordId: "source",
    targetEvidenceId: "target",
    targetResolutionStatus: "eligible",
    notes: "The authored comparison basis.",
    weight: "6",
  };
  try {
    history.initialize({
      state: "study",
      mode: "passage",
      resource: "narrative_explorer",
      trail: {
        originSelection: selection,
        nodes: [
          {kind: "passage", id: "passage:Genesis 1", label: "Genesis 1", selection, relationshipHops: 0},
          {kind: "evidence", id: relationship.targetId, label: "Linked evidence", parentObjectId: "creation", selection, relationshipHops: 1, relationship},
        ],
        activeIndex: 1,
      },
    });
    assert.deepEqual(history.current().trail.nodes[1].relationship, relationship);
  } finally {
    history.destroy();
    restore();
  }
});

test("Narrative Explorer history preserves known views and rejects invalid categories", () => {
  const {controller, restore} = loadHistoryController();
  const history = controller.create();
  const view = {kind: "category", categoryId: "themes_biblical_connections"};
  try {
    history.initialize({state: "study", mode: "passage", resource: "narrative_explorer", narrativeView: view});
    assert.deepEqual(history.current().narrativeView, view);

    [
      {kind: "category", categoryId: "made_up_category"},
      {kind: "category", categoryId: "x".repeat(1000)},
      {kind: "other", categoryId: "themes_biblical_connections"},
      null,
    ].forEach((narrativeView) => {
      history.replace({state: "study", mode: "passage", resource: "narrative_explorer", narrativeView});
      assert.deepEqual(history.current().narrativeView, {kind: "overview"});
    });
  } finally {
    history.destroy();
    restore();
  }
});

test("Narrative Explorer Back and Forward restore focused category and exact trail", async () => {
  const {controller, browserHistory, restore} = loadHistoryController();
  const applied = [];
  const history = controller.create({apply: async (snapshot) => applied.push(snapshot)});
  const selection = {book: "Genesis", chapter: 1, reference: "Genesis 1"};
  const trail = {
    originSelection: selection,
    nodes: [{
      kind: "passage",
      id: "passage:Genesis 1",
      label: "Genesis 1",
      reference: "Genesis 1",
      selection,
      relationshipHops: 0,
      focusControlId: "category:themes_biblical_connections",
    }],
    activeIndex: 0,
  };
  const categoryView = {kind: "category", categoryId: "themes_biblical_connections"};
  const relationship = {
    id: "genesis-john-route",
    provenance: "ckl_documented_claim",
    sourcePassage: "Genesis 1:1",
    destinationPassage: "John 1:1",
    relationshipCategory: "thematic_connection",
    explanation: "A documented relationship with an explanation that remains attached to the route.",
    uncertainty: "The relationship does not establish literary dependence.",
    humanScholarlyApproval: "not_recorded",
    direction: "one_way",
    supportingRecordIds: Array.from({length: 14}, (_, index) => `ckl:genesis#evidence:${index}`),
    supportingSourceIds: Array.from({length: 14}, (_, index) => `source-${index}`),
  };
  try {
    history.initialize({state: "study", mode: "passage", resource: "narrative_explorer", trail, narrativeView: {kind: "overview"}});
    history.push({state: "study", mode: "passage", resource: "narrative_explorer", trail, narrativeView: categoryView});
    history.push({
      state: "study",
      mode: "passage",
      resource: "narrative_explorer",
      trail: {...trail, nodes: [...trail.nodes, {
        kind: "evidence",
        id: "ckl:genesis#evidence:creation",
        label: "Creation evidence",
        relationship,
        parentObjectId: "genesis",
        selection,
        relationshipHops: 0,
        focusControlId: "evidence:creation",
      }], activeIndex: 1},
      narrativeView: categoryView,
    });

    history.backFromResource();
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(history.current().narrativeView, categoryView);
    assert.equal(history.current().trail.nodes.length, 1);
    history.backFromResource();
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(history.current().narrativeView, {kind: "overview"});

    browserHistory.forward();
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(history.current().narrativeView, categoryView);
    assert.equal(history.current().trail.nodes.length, 1);
    browserHistory.forward();
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(history.current().narrativeView, categoryView);
    assert.equal(history.current().trail.nodes.length, 2);
    assert.deepEqual(history.current().trail.nodes[1].relationship, {
      id: relationship.id,
      provenance: relationship.provenance,
      sourcePassage: relationship.sourcePassage,
      destinationPassage: relationship.destinationPassage,
      relationshipCategory: relationship.relationshipCategory,
      explanation: relationship.explanation,
      uncertainty: relationship.uncertainty,
      humanScholarlyApproval: relationship.humanScholarlyApproval,
      direction: relationship.direction,
      supportingRecordIds: relationship.supportingRecordIds.slice(0, 12),
      supportingSourceIds: relationship.supportingSourceIds.slice(0, 12),
    });
    assert.equal(applied.length, 4);
  } finally {
    history.destroy();
    restore();
  }
});
