const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");


function loadController(companionContext) {
  const window = {
    BHFCompanionContext: companionContext,
    clearTimeout: () => {},
    setTimeout: (callback) => {
      queueMicrotask(callback);
      return 1;
    },
  };
  const context = vm.createContext({
    AbortController,
    DOMException,
    console,
    queueMicrotask,
    window,
  });
  vm.runInContext(
    fs.readFileSync("bhf_web/static/companion-context-controller.js", "utf8"),
    context,
  );
  return window.BHFCompanionContextController;
}


function selection(chapter) {
  return {book: "1 Samuel", chapter, startVerse: 1, endVerse: 1};
}


function passageKey(value) {
  return `${value.book}|${value.chapter}|${value.startVerse}|${value.endVerse}`;
}


function initialContext(chapter) {
  return {
    reference: `1 Samuel ${chapter}:1`,
    presentation_packet: {cards: [{id: `local-${chapter}`}], presentation_mode: "deterministic_fallback"},
    presentation_enhancement: {available: true, evidence_hash: `hash-${chapter}`},
  };
}


function enhancedContext(chapter) {
  return {
    reference: `1 Samuel ${chapter}:1`,
    evidence_bundle: {evidence_hash: `hash-${chapter}`},
    presentation_packet: {cards: [{id: `ai-${chapter}`}], presentation_mode: "generated"},
    presentation_evidence: [],
  };
}


async function settle() {
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
}


test("deterministic context is ready before lazy presentation resolves", async () => {
  let finishEnhancement;
  const events = [];
  const api = {
    requestKey: passageKey,
    load: async (value) => initialContext(value.chapter),
    enhance: async () => new Promise((resolve) => { finishEnhancement = resolve; }),
  };
  const controller = loadController(api).create({
    delay: 0,
    onReady: (context) => events.push(["ready", context.presentation_packet.cards[0].id]),
    onEnhanced: (context) => events.push(["enhanced", context.presentation_packet.cards[0].id]),
  });

  controller.setSelection(selection(25));
  await settle();

  assert.deepEqual(events, [["ready", "local-25"]]);
  finishEnhancement(enhancedContext(25));
  await settle();
  assert.deepEqual(events, [["ready", "local-25"], ["enhanced", "ai-25"]]);
});


test("late presentation for a previous chapter cannot replace current discoveries", async () => {
  const pending = new Map();
  const enhanced = [];
  const api = {
    requestKey: passageKey,
    load: async (value) => initialContext(value.chapter),
    enhance: async (value) => new Promise((resolve) => pending.set(value.chapter, resolve)),
  };
  const controller = loadController(api).create({
    delay: 0,
    onEnhanced: (context) => enhanced.push(context.presentation_packet.cards[0].id),
  });

  controller.setSelection(selection(25));
  await settle();
  controller.setSelection(selection(26));
  await settle();
  pending.get(26)(enhancedContext(26));
  await settle();
  pending.get(25)(enhancedContext(25));
  await settle();

  assert.deepEqual(enhanced, ["ai-26"]);
  assert.equal(controller.getRecord().context.reference, "1 Samuel 26:1");
});
