const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");


function loadHandoff({runtimeConfig = {}, fetch} = {}) {
  const window = {BHFRuntimeConfig: runtimeConfig};
  const context = vm.createContext({fetch, URL, window});
  vm.runInContext(
    fs.readFileSync("bhf_web/static/assistant-handoff.js", "utf8"),
    context,
  );
  return window.BHFAssistantHandoff;
}


function node(initial = {}) {
  const listeners = new Map();
  return {
    hidden: false,
    href: "",
    open: false,
    selected: false,
    textContent: "",
    value: "",
    ...initial,
    addEventListener(type, handler) {
      listeners.set(type, handler);
    },
    async dispatch(type) {
      return listeners.get(type)({preventDefault() {}});
    },
    focus() {},
    select() { this.selected = true; },
  };
}


function handoffNodes() {
  const dialog = node({
    showModal() { this.open = true; },
    close() { this.open = false; },
  });
  return {
    dialog,
    reference: node(),
    question: node(),
    prepared: node(),
    status: node(),
    primary: node(),
    manualCopy: node(),
    openFallback: node({hidden: true}),
  };
}


test("formatReference preserves a selected verse range", () => {
  const handoff = loadHandoff();

  assert.equal(
    handoff.formatReference({book: "James", chapter: 1, reference: "James 1:2-4"}),
    "James 1:2-4",
  );
});


test("formatReference preserves a selected chapter reference", () => {
  const handoff = loadHandoff();

  assert.equal(
    handoff.formatReference({book: "James", chapter: 1, reference: "James 2"}),
    "James 2",
  );
});


test("buildHandoffText trims the question envelope", () => {
  const handoff = loadHandoff();

  assert.equal(
    handoff.buildHandoffText({reference: "James 1", question: " Why wisdom? "}),
    "I'm studying James 1 in the Biblical Hermeneutics Framework (BHF).\n\nMy question:\nWhy wisdom?",
  );
});


test("buildHandoffText rejects a blank question with a user-facing error", () => {
  const handoff = loadHandoff();

  assert.throws(
    () => handoff.buildHandoffText({reference: "James 1", question: " \t\n "}),
    /Please enter a question/i,
  );
});


test("opening uses the current selection without a network request", () => {
  let requests = 0;
  const handoff = loadHandoff({fetch: () => { requests += 1; }});
  const nodes = handoffNodes();
  const controller = handoff.create({
    ...nodes,
    getSelection: () => ({book: "James", chapter: 2}),
  });

  controller.open();

  assert.equal(nodes.dialog.open, true);
  assert.equal(nodes.reference.textContent, "James 2");
  assert.equal(requests, 0);
});


test("primary handoff copies prepared text and opens the configured destination", async () => {
  const handoff = loadHandoff({runtimeConfig: {assistantUrl: "https://assistant.example/bhf"}});
  const nodes = handoffNodes();
  const copied = [];
  const opened = [];
  const controller = handoff.create({
    ...nodes,
    getSelection: () => ({book: "James", chapter: 1}),
    openWindow: (...args) => { opened.push(args); return {}; },
    writeClipboard: async (text) => copied.push(text),
  });
  nodes.question.value = " Why wisdom? ";
  controller.open();

  await nodes.primary.dispatch("click");

  const expected = "I'm studying James 1 in the Biblical Hermeneutics Framework (BHF).\n\nMy question:\nWhy wisdom?";
  assert.equal(nodes.prepared.value, expected);
  assert.deepEqual(copied, [expected]);
  assert.deepEqual(opened, [["https://assistant.example/bhf", "_blank", "noopener,noreferrer"]]);
  assert.match(nodes.status.textContent, /copied/i);
});


test("primary handoff reserves the popup before clipboard writing settles", async () => {
  const handoff = loadHandoff({runtimeConfig: {assistantUrl: "https://assistant.example/bhf"}});
  const nodes = handoffNodes();
  let finishCopy;
  const opened = [];
  const controller = handoff.create({
    ...nodes,
    getSelection: () => ({book: "James", chapter: 1}),
    openWindow: (...args) => { opened.push(args); return {}; },
    writeClipboard: () => new Promise((resolve) => { finishCopy = resolve; }),
  });
  nodes.question.value = "Why wisdom?";
  controller.open();

  const action = nodes.primary.dispatch("click");
  assert.equal(opened.length, 1);
  finishCopy();
  await action;
});


test("clipboard failure leaves the prepared question visible and selectable", async () => {
  const handoff = loadHandoff({runtimeConfig: {assistantUrl: "https://assistant.example/bhf"}});
  const nodes = handoffNodes();
  const controller = handoff.create({
    ...nodes,
    getSelection: () => ({book: "James", chapter: 1}),
    openWindow: () => ({}),
    writeClipboard: async () => { throw new Error("denied"); },
  });
  nodes.question.value = "Why wisdom?";
  controller.open();

  await nodes.primary.dispatch("click");

  assert.match(nodes.prepared.value, /Why wisdom\?/);
  assert.equal(nodes.manualCopy.hidden, false);
  assert.match(nodes.status.textContent, /Copy the prepared question manually/i);
});


test("reopening clears stale prepared text so manual copy uses the current selection", async () => {
  const handoff = loadHandoff({runtimeConfig: {assistantUrl: "https://assistant.example/bhf"}});
  const nodes = handoffNodes();
  let currentSelection = {book: "James", chapter: 1};
  const copied = [];
  let copyAttempts = 0;
  const controller = handoff.create({
    ...nodes,
    getSelection: () => currentSelection,
    openWindow: () => ({}),
    writeClipboard: async (text) => {
      copyAttempts += 1;
      if (copyAttempts === 1) throw new Error("denied");
      copied.push(text);
    },
  });
  nodes.question.value = "Why James 1?";
  controller.open();
  await nodes.primary.dispatch("click");
  assert.match(nodes.prepared.value, /James 1/);

  currentSelection = {book: "James", chapter: 2};
  nodes.question.value = "Why James 2?";
  controller.open();
  await nodes.manualCopy.dispatch("click");

  const expected = "I'm studying James 2 in the Biblical Hermeneutics Framework (BHF).\n\nMy question:\nWhy James 2?";
  assert.equal(nodes.prepared.value, expected);
  assert.deepEqual(copied, [expected]);
});


test("unsafe configured URLs never populate the fallback or open a popup", async () => {
  for (const assistantUrl of ["javascript:alert(1)", "data:text/html,unsafe", "http://assistant.example/bhf"]) {
    const handoff = loadHandoff({runtimeConfig: {assistantUrl}});
    const nodes = handoffNodes();
    const opened = [];
    const controller = handoff.create({
      ...nodes,
      getSelection: () => ({book: "James", chapter: 1}),
      openWindow: (...args) => opened.push(args),
      writeClipboard: async () => {},
    });
    nodes.question.value = "Why wisdom?";

    controller.open();
    await nodes.primary.dispatch("click");

    assert.equal(nodes.openFallback.href, "");
    assert.equal(opened.length, 0);
    assert.match(nodes.status.textContent, /destination is unavailable/i);
    assert.match(nodes.prepared.value, /Why wisdom\?/);
  }
});


test("a blocked popup exposes an explicit Open BHF fallback", async () => {
  const handoff = loadHandoff({runtimeConfig: {assistantUrl: "https://assistant.example/bhf"}});
  const nodes = handoffNodes();
  const controller = handoff.create({
    ...nodes,
    getSelection: () => ({book: "James", chapter: 1}),
    openWindow: () => null,
    writeClipboard: async () => {},
  });
  nodes.question.value = "Why wisdom?";
  controller.open();

  await nodes.primary.dispatch("click");

  assert.equal(nodes.openFallback.hidden, false);
  assert.equal(nodes.openFallback.href, "https://assistant.example/bhf");
  assert.match(nodes.status.textContent, /Open BHF/i);
});
