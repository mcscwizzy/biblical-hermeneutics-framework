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


function fallbackContext(chapter) {
  return {
    reference: `1 Samuel ${chapter}:1`,
    evidence_bundle: {evidence_hash: `hash-${chapter}`},
    presentation_packet: {
      cards: [{id: `server-fallback-${chapter}`}],
      presentation_mode: "deterministic_fallback",
    },
    presentation_evidence: [],
  };
}


function cachedContext(chapter) {
  const context = enhancedContext(chapter);
  context.presentation_packet.presentation_mode = "cached";
  context.presentation_packet.generated_from = {
    evidence_hash: `hash-${chapter}`,
    evidence_bundle_version: "evidence-bundle-v1",
    presentation_schema_version: "presentation-packet-v1",
    prompt_version: "presentation-v4",
    model: "cached-provider-model",
  };
  return context;
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
    onEnhancementLoading: (context) => events.push(["generating", context.presentation_packet.cards[0].id]),
    onEnhanced: (context) => events.push(["enhanced", context.presentation_packet.cards[0].id]),
  });

  controller.setSelection(selection(25));
  await settle();

  assert.deepEqual(events, [["ready", "local-25"], ["generating", "local-25"]]);
  assert.equal(controller.getRecord().context.presentation_packet.cards[0].id, "local-25");
  finishEnhancement(enhancedContext(25));
  await settle();
  assert.deepEqual(events, [
    ["ready", "local-25"],
    ["generating", "local-25"],
    ["enhanced", "ai-25"],
  ]);
  assert.equal(controller.getRecord().enhancementStatus, "generated");
});


test("HTTP enhancement failure keeps deterministic presentation and reports failure", async () => {
  const statuses = [];
  const api = {
    requestKey: passageKey,
    load: async (value) => initialContext(value.chapter),
    enhance: async () => { throw new Error("HTTP 503"); },
  };
  const controller = loadController(api).create({
    delay: 0,
    onEnhancementLoading: () => statuses.push("generating"),
    onEnhancementError: () => statuses.push("failed"),
  });

  controller.setSelection(selection(25));
  await settle();

  assert.deepEqual(statuses, ["generating", "failed"]);
  assert.equal(controller.getRecord().context.presentation_packet.cards[0].id, "local-25");
  assert.equal(controller.getRecord().enhancementStatus, "failed");
});


test("HTTP 200 deterministic fallback is not treated as an AI enhancement", async () => {
  const enhanced = [];
  const failures = [];
  const api = {
    requestKey: passageKey,
    load: async (value) => initialContext(value.chapter),
    enhance: async (value) => fallbackContext(value.chapter),
  };
  const controller = loadController(api).create({
    delay: 0,
    onEnhanced: (context) => enhanced.push(context.presentation_packet.cards[0].id),
    onEnhancementError: (_error, _selection, record) => failures.push(record.enhancementReason),
  });

  controller.setSelection(selection(25));
  await settle();

  assert.deepEqual(enhanced, []);
  assert.deepEqual(failures, ["fallback"]);
  assert.equal(controller.getRecord().context.presentation_packet.cards[0].id, "local-25");
});


test("enabled AI without a provider reports unavailable and makes no request", async () => {
  let requests = 0;
  const unavailable = [];
  const api = {
    requestKey: passageKey,
    load: async (value) => initialContext(value.chapter),
    getEnhancementAvailability: async () => ({
      available: false,
      reason: "provider_unavailable",
      requestOptions: null,
    }),
    enhance: async () => { requests += 1; },
  };
  const controller = loadController(api).create({
    delay: 0,
    onEnhancementUnavailable: (reason) => unavailable.push(reason),
  });

  controller.setSelection(selection(25));
  await settle();

  assert.equal(requests, 0);
  assert.deepEqual(unavailable, ["provider_unavailable"]);
  assert.equal(controller.getRecord().context.presentation_packet.cards[0].id, "local-25");
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


test("aborted previous-passage enhancement is silent and the new passage owns the UI", async () => {
  const enhanced = [];
  const failures = [];
  const api = {
    requestKey: passageKey,
    load: async (value) => initialContext(value.chapter),
    enhance: async (value, _context, options) => {
      if (value.chapter === 26) return enhancedContext(26);
      return new Promise((_resolve, reject) => {
        options.signal.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        }, {once: true});
      });
    },
  };
  const controller = loadController(api).create({
    delay: 0,
    onEnhanced: (context) => enhanced.push(context.presentation_packet.cards[0].id),
    onEnhancementError: () => failures.push("failed"),
  });

  controller.setSelection(selection(25));
  await settle();
  controller.setSelection(selection(26));
  await settle();

  assert.deepEqual(failures, []);
  assert.deepEqual(enhanced, ["ai-26"]);
  assert.equal(controller.getRecord().context.reference, "1 Samuel 26:1");
});


test("disabled AI presentation renders deterministic context without an enhancement request", async () => {
  let requests = 0;
  const ready = [];
  const enhancementEvents = [];
  const api = {
    requestKey: passageKey,
    load: async (value) => initialContext(value.chapter),
    getEnhancementAvailability: async () => ({
      available: false,
      reason: "disabled",
      requestOptions: null,
    }),
    enhance: async () => { requests += 1; },
  };
  const controller = loadController(api).create({
    delay: 0,
    onReady: (context) => ready.push(context.presentation_packet.cards[0].id),
    onEnhancementUnavailable: () => enhancementEvents.push("unavailable"),
    onEnhancementError: () => enhancementEvents.push("failed"),
  });

  controller.setSelection(selection(25));
  await settle();

  assert.deepEqual(ready, ["local-25"]);
  assert.equal(requests, 0);
  assert.deepEqual(enhancementEvents, []);
  assert.equal(controller.getRecord().enhancementStatus, "idle");
});


test("turning AI presentation on enhances the already-loaded passage", async () => {
  let enabled = false;
  let requests = 0;
  const enhanced = [];
  const api = {
    requestKey: passageKey,
    load: async (value) => initialContext(value.chapter),
    canEnhance: async () => enabled,
    enhance: async (value) => {
      requests += 1;
      return enhancedContext(value.chapter);
    },
  };
  const controller = loadController(api).create({
    delay: 0,
    onEnhanced: (context) => enhanced.push(context.presentation_packet.cards[0].id),
  });

  controller.setSelection(selection(25));
  await settle();
  assert.equal(requests, 0);

  enabled = true;
  assert.equal(controller.refreshEnhancement(), true);
  await settle();
  assert.equal(requests, 1);
  assert.deepEqual(enhanced, ["ai-25"]);

  controller.cancelEnhancement();
  assert.equal(controller.getRecord().context.presentation_packet.cards[0].id, "local-25");
});


test("turning AI presentation off aborts a late optional response", async () => {
  let finishEnhancement;
  const enhanced = [];
  const statuses = [];
  const api = {
    requestKey: passageKey,
    load: async (value) => initialContext(value.chapter),
    canEnhance: async () => true,
    enhance: async () => new Promise((resolve) => { finishEnhancement = resolve; }),
  };
  const controller = loadController(api).create({
    delay: 0,
    onEnhancementLoading: () => statuses.push("generating"),
    onEnhanced: (context) => enhanced.push(context.presentation_packet.cards[0].id),
    onPresentationReset: () => statuses.push("reset"),
    onEnhancementCancelled: () => statuses.push("cancelled"),
    onEnhancementError: () => statuses.push("failed"),
  });

  controller.setSelection(selection(25));
  await settle();
  controller.cancelEnhancement();
  finishEnhancement(enhancedContext(25));
  await settle();

  assert.deepEqual(enhanced, []);
  assert.deepEqual(statuses, ["generating", "reset", "cancelled"]);
  assert.equal(controller.getRecord().context.presentation_packet.cards[0].id, "local-25");
  assert.equal(controller.getRecord().enhancementStatus, "idle");
});


test("cached AI-generated packet is accepted without a failure status", async () => {
  const enhanced = [];
  const failures = [];
  const api = {
    requestKey: passageKey,
    load: async (value) => initialContext(value.chapter),
    enhance: async (value) => cachedContext(value.chapter),
  };
  const controller = loadController(api).create({
    delay: 0,
    onEnhanced: (context) => enhanced.push(context.presentation_packet.cards[0].id),
    onEnhancementError: () => failures.push("failed"),
  });

  controller.setSelection(selection(25));
  await settle();

  assert.deepEqual(enhanced, ["ai-25"]);
  assert.deepEqual(failures, []);
  assert.equal(controller.getRecord().enhancementStatus, "generated");
});


test("pre-generated bundle already in local context is enhanced without another request", async () => {
  let requests = 0;
  const localBundle = initialContext(25);
  localBundle.presentation_packet = cachedContext(25).presentation_packet;
  localBundle.presentation_packet.presentation_mode = "bundled";
  const enhanced = [];
  const api = {
    requestKey: passageKey,
    load: async () => localBundle,
    getEnhancementAvailability: async () => ({
      available: true,
      reason: "",
      requestOptions: {enabled: true},
    }),
    enhance: async () => { requests += 1; },
  };
  const controller = loadController(api).create({
    delay: 0,
    onEnhanced: (context) => enhanced.push(context.presentation_packet.presentation_mode),
  });

  controller.setSelection(selection(25));
  await settle();

  assert.equal(requests, 0);
  assert.deepEqual(enhanced, ["bundled"]);
  assert.equal(controller.getRecord().enhancementStatus, "generated");
});


test("cached deterministic metadata is not presented as AI-generated", async () => {
  const result = cachedContext(25);
  result.presentation_packet.generated_from.prompt_version = "deterministic-v4";
  result.presentation_packet.generated_from.model = "deterministic";
  const failures = [];
  const api = {
    requestKey: passageKey,
    load: async (value) => initialContext(value.chapter),
    enhance: async () => result,
  };
  const controller = loadController(api).create({
    delay: 0,
    onEnhancementError: () => failures.push("failed"),
  });

  controller.setSelection(selection(25));
  await settle();

  assert.deepEqual(failures, ["failed"]);
  assert.equal(controller.getRecord().context.presentation_packet.cards[0].id, "local-25");
});
