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
