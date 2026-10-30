const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");


class FakeElement {
  constructor(tagName) {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.hidden = false;
    this.className = "";
    this.listeners = new Map();
    this.text = "";
    const classes = new Set();
    this.classList = {
      add: (...values) => values.forEach((value) => classes.add(value)),
      remove: (...values) => values.forEach((value) => classes.delete(value)),
      toggle: (value, force) => {
        const enabled = force === undefined ? !classes.has(value) : Boolean(force);
        if (enabled) classes.add(value);
        else classes.delete(value);
        return enabled;
      },
      contains: (value) => classes.has(value),
    };
  }

  append(...children) {
    children.forEach((child) => {
      if (child instanceof FakeElement) this.children.push(child);
    });
  }

  appendChild(child) {
    this.append(child);
    return child;
  }

  replaceChildren(...children) {
    this.children = [];
    this.text = "";
    this.append(...children);
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  getAttribute(name) {
    return this.attributes[name] ?? null;
  }

  addEventListener(name, listener) {
    this.listeners.set(name, listener);
  }

  set innerHTML(value) {
    this.children = [];
    this.text = String(value || "").replace(/<[^>]*>/g, "");
  }

  get textContent() {
    return this.text + this.children.map((child) => child.textContent).join("");
  }

  set textContent(value) {
    this.children = [];
    this.text = String(value ?? "");
  }

  querySelectorAll(selector) {
    const matches = [];
    const predicate = selector.startsWith(".")
      ? (element) => element.classList.contains(selector.slice(1))
      : selector === "h3"
        ? (element) => element.tagName === "H3"
        : selector === "[data-verse]"
          ? (element) => Object.hasOwn(element.dataset, "verse")
      : selector === "[data-commentary-entry-id]"
        ? (element) => Object.hasOwn(element.dataset, "commentaryEntryId")
        : selector === "[data-tyndale-live-status]"
          ? (element) => Object.hasOwn(element.dataset, "tyndaleLiveStatus")
          : selector === "[data-tyndale-card-content]"
            ? (element) => Object.hasOwn(element.dataset, "tyndaleCardContent")
        : () => false;
    const visit = (element) => {
      element.children.forEach((child) => {
        if (predicate(child)) matches.push(child);
        visit(child);
      });
    };
    visit(this);
    return matches;
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
}


function anchor(book, startChapter, startVerse, endChapter, endVerse) {
  return {
    book,
    start_chapter: startChapter,
    start_verse: startVerse,
    end_chapter: endChapter,
    end_verse: endVerse,
  };
}


function entry(id, kind, body, entryAnchor, title = "") {
  return {id, kind, body, title, anchor: entryAnchor};
}


function payload(book, chapter, entries) {
  return {
    available: true,
    book,
    chapter,
    entries,
    source: {
      name: "Tyndale Open Study Notes",
      attribution: "Copyright © 2022 Tyndale House Publishers. CC BY-SA 4.0.",
    },
  };
}


function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return {promise, resolve, reject};
}


function createFixture(requestJson = async () => payload("Genesis", 1, [])) {
  let selection = {};
  let selectionListener = null;
  const requests = [];
  const slot = new FakeElement("section");
  slot.hidden = true;
  const readerPane = new FakeElement("article");
  readerPane.classList.add("is-active");
  const fullBody = new FakeElement("div");
  const document = {
    querySelector(selector) {
      if (selector === "[data-companion-tyndale-card-slot]") return slot;
      if (selector === "[data-commentary-body]") return fullBody;
      if (selector === "#chapter-reader .reader-pane.is-active") return readerPane;
      return null;
    },
    createElement(tagName) {
      return new FakeElement(tagName);
    },
  };
  const window = {
    BHFStudySelection: {
      getState() { return selection; },
      subscribe(listener, options = {}) {
        selectionListener = listener;
        if (options.immediate !== false) listener(selection, {selection, source: "subscribe"});
        return () => { selectionListener = null; };
      },
    },
    BHFApi: {
      requestJson(url, options, fallback) {
        requests.push({url: String(url), options, fallback});
        return requestJson(String(url), options, fallback);
      },
    },
    BHFStudyActions: {
      openWorkspaceTab(tab) { window.openedWorkspaceTab = tab; },
    },
  };
  const context = vm.createContext({window, document, console, Promise, URLSearchParams});
  vm.runInContext(fs.readFileSync("bhf_web/static/commentary.js", "utf8"), context);

  return {
    window,
    slot,
    fullBody,
    requests,
    setReaderChapter(book, chapter, verseCount) {
      readerPane.replaceChildren();
      const heading = new FakeElement("h3");
      heading.textContent = `${book} ${chapter}`;
      readerPane.appendChild(heading);
      for (let verse = 1; verse <= verseCount; verse += 1) {
        const verseElement = new FakeElement("span");
        verseElement.dataset.verse = String(verse);
        readerPane.appendChild(verseElement);
      }
    },
    publish(next) {
      selection = next;
      selectionListener?.(selection, {selection, source: "test"});
    },
    async flush() {
      await new Promise((resolve) => setImmediate(resolve));
      await Promise.resolve();
    },
  };
}


test("chapter 1 shows the matching book introduction with its published summary", async () => {
  const fixture = createFixture(async () => payload("Genesis", 1, [
    entry(1, "book_introduction_summary", "Published Genesis summary.", anchor("Genesis", null, null, null, null)),
    entry(2, "book_introduction", "Published full Genesis introduction.", anchor("Genesis", null, null, null, null)),
    entry(3, "book_introduction", "Published Ruth introduction.", anchor("Ruth", null, null, null, null)),
  ]));

  fixture.publish({book: "Genesis", chapter: 1, selectedVerses: [], reference: "Genesis 1"});
  await fixture.flush();

  assert.equal(fixture.slot.hidden, false);
  assert.match(fixture.slot.textContent, /Published Genesis summary\./);
  assert.match(fixture.slot.textContent, /Published full Genesis introduction\./);
  assert.doesNotMatch(fixture.slot.textContent, /Published Ruth introduction\./);
  assert.match(fixture.slot.textContent, /Tyndale Open Study Notes/);
});


test("a later chapter shows chapter notes without the book introduction", async () => {
  const fixture = createFixture(async () => payload("Genesis", 2, [
    entry(1, "book_introduction", "Published full Genesis introduction.", anchor("Genesis", null, null, null, null)),
    entry(2, "chapter_note", "Published Genesis chapter two note.", anchor("Genesis", 2, null, 2, null)),
    entry(3, "chapter_note", "Published Genesis chapter range note.", anchor("Genesis", 1, null, 2, null)),
  ]));

  fixture.publish({book: "Genesis", chapter: 2, selectedVerses: [], reference: "Genesis 2"});
  await fixture.flush();

  assert.match(fixture.slot.textContent, /Published Genesis chapter two note\./);
  assert.match(fixture.slot.textContent, /Published Genesis chapter range note\./);
  assert.doesNotMatch(fixture.slot.textContent, /Published full Genesis introduction\./);
});


test("an unselected chapter shows full-chapter ranges but not narrow verse ranges", async () => {
  const fixture = createFixture(async () => payload("1 Chronicles", 3, [
    entry(1, "range_note", "Published full-chapter range note.", anchor("1 Chronicles", 3, 1, 3, 24)),
    entry(2, "range_note", "Published narrow verse range note.", anchor("1 Chronicles", 3, 1, 3, 4)),
  ]));
  fixture.setReaderChapter("1 Chronicles", 3, 24);

  fixture.publish({book: "1 Chronicles", chapter: 3, selectedVerses: [], reference: "1 Chronicles 3"});
  await fixture.flush();

  assert.match(fixture.slot.textContent, /Published full-chapter range note\./);
  assert.doesNotMatch(fixture.slot.textContent, /Published narrow verse range note\./);
});


test("a single verse selection displays matching and overlapping notes only", async () => {
  const fixture = createFixture(async () => payload("John", 1, [
    entry(1, "verse_note", "Published John 1:3 note.", anchor("John", 1, 3, 1, 3)),
    entry(2, "verse_note", "Published John 1:2 note.", anchor("John", 1, 2, 1, 2)),
    entry(3, "range_note", "Published John 1:2-4 note.", anchor("John", 1, 2, 1, 4)),
  ]));

  fixture.publish({book: "John", chapter: 1, startVerse: 3, endVerse: 3, selectedVerses: [3], reference: "John 1:3"});
  await fixture.flush();

  assert.match(fixture.slot.textContent, /Published John 1:3 note\./);
  assert.match(fixture.slot.textContent, /Published John 1:2-4 note\./);
  assert.doesNotMatch(fixture.slot.textContent, /Published John 1:2 note\./);
});


test("non-contiguous selections use selected verse numbers and rank direct notes first", async () => {
  const fixture = createFixture(async () => payload("John", 1, [
    entry(1, "verse_note", "Selected verse one note.", anchor("John", 1, 1, 1, 1)),
    entry(2, "verse_note", "Gap verse two note.", anchor("John", 1, 2, 1, 2)),
    entry(3, "verse_note", "Selected verse three note.", anchor("John", 1, 3, 1, 3)),
    entry(4, "range_note", "Range across verses one to three.", anchor("John", 1, 1, 1, 3)),
  ]));

  fixture.publish({book: "John", chapter: 1, startVerse: 1, endVerse: 3, selectedVerses: [1, 3], reference: "John 1:1,3"});
  await fixture.flush();

  const text = fixture.slot.textContent;
  assert.match(text, /Selected verse one note\./);
  assert.match(text, /Selected verse three note\./);
  assert.match(text, /Range across verses one to three\./);
  assert.doesNotMatch(text, /Gap verse two note\./);
  assert.ok(text.indexOf("Selected verse one note.") < text.indexOf("Range across verses one to three."));
});


test("a same-chapter exact range ranks ahead of a broader cross-chapter range", async () => {
  const fixture = createFixture(async () => payload("Genesis", 2, [
    entry(1, "range_note", "Broader Genesis 1:1-2:3 note.", anchor("Genesis", 1, 1, 2, 3)),
    entry(2, "range_note", "Exact Genesis 2:1-3 note.", anchor("Genesis", 2, 1, 2, 3)),
  ]));

  fixture.publish({book: "Genesis", chapter: 2, startVerse: 1, endVerse: 3, selectedVerses: [1, 2, 3], reference: "Genesis 2:1-3"});
  await fixture.flush();

  const text = fixture.slot.textContent;
  assert.ok(text.indexOf("Exact Genesis 2:1-3 note.") < text.indexOf("Broader Genesis 1:1-2:3 note."));
});


test("missing selected notes use a fallback that does not dismiss broader book information", async () => {
  const fixture = createFixture(async () => payload("Ruth", 3, [
    entry(1, "verse_note", "A note for Ruth 3:4.", anchor("Ruth", 3, 4, 3, 4)),
  ]));

  fixture.publish({book: "Ruth", chapter: 3, startVerse: 7, endVerse: 7, selectedVerses: [7], reference: "Ruth 3:7"});
  await fixture.flush();

  assert.match(fixture.slot.textContent, /No Tyndale note is linked directly to this selection/i);
  assert.match(fixture.slot.textContent, /full Tyndale workspace/i);
  assert.doesNotMatch(fixture.slot.textContent, /No Tyndale information is available for Ruth/i);
});


test("uninstalled and offline Tyndale data render a readable unavailable state", async (t) => {
  await t.test("uninstalled database", async () => {
    const fixture = createFixture(async () => ({available: false, reason: "commentary_not_installed", entries: []}));
    fixture.publish({book: "Genesis", chapter: 1, selectedVerses: [], reference: "Genesis 1"});
    await fixture.flush();
    assert.match(fixture.slot.textContent, /Tyndale Study Notes are not installed/i);
    assert.match(fixture.slot.querySelector("[data-tyndale-live-status]").textContent, /not installed/i);
    assert.doesNotMatch(fixture.slot.querySelector("[data-tyndale-live-status]").textContent, /ready/i);
  });

  await t.test("offline request failure", async () => {
    const fixture = createFixture(async () => { throw new Error("offline"); });
    fixture.publish({book: "Genesis", chapter: 1, selectedVerses: [], reference: "Genesis 1"});
    await fixture.flush();
    assert.match(fixture.slot.textContent, /Tyndale Study Notes are unavailable/i);
    assert.match(fixture.slot.querySelector("[data-tyndale-live-status]").textContent, /unavailable/i);
    assert.doesNotMatch(fixture.slot.querySelector("[data-tyndale-live-status]").textContent, /ready/i);
  });
});


test("card updates preserve one live status node for screen-reader announcements", async () => {
  const fixture = createFixture(async (url) => {
    const book = url.split("/").at(-2);
    return payload(book, 1, [entry(book, "book_introduction", `${book} introduction.`, anchor(book, null, null, null, null))]);
  });

  fixture.publish({book: "Genesis", chapter: 1, selectedVerses: [], reference: "Genesis 1"});
  await fixture.flush();
  const status = fixture.slot.querySelector("[data-tyndale-live-status]");
  assert.ok(status);
  assert.equal(status.getAttribute("role"), "status");
  assert.equal(status.getAttribute("aria-live"), "polite");

  fixture.publish({book: "Ruth", chapter: 1, selectedVerses: [], reference: "Ruth 1"});
  await fixture.flush();

  assert.equal(fixture.slot.querySelector("[data-tyndale-live-status]"), status);
  assert.match(status.textContent, /Ruth 1/);
});


test("the contextual card and full notes pane reuse one chapter request", async () => {
  const calls = [];
  const fixture = createFixture(async (url) => {
    calls.push(url);
    return payload("John", 1, [entry(1, "verse_note", "John verse one note.", anchor("John", 1, 1, 1, 1))]);
  });

  await fixture.window.BHFCommentary.loadChapter("John", 1);
  fixture.publish({book: "John", chapter: 1, startVerse: 1, endVerse: 1, selectedVerses: [1], reference: "John 1:1"});
  await fixture.flush();

  assert.equal(calls.filter((url) => url === "/api/commentary/John/1").length, 1);
  assert.match(fixture.slot.textContent, /John verse one note\./);
});


test("late chapter responses cannot replace the current card", async () => {
  const requests = new Map();
  const fixture = createFixture((url) => {
    const pending = deferred();
    requests.set(url, pending);
    return pending.promise;
  });

  fixture.publish({book: "Genesis", chapter: 1, selectedVerses: [], reference: "Genesis 1"});
  fixture.publish({book: "Ruth", chapter: 1, selectedVerses: [], reference: "Ruth 1"});
  void fixture.window.BHFCommentary.loadChapter("Genesis", 1);
  void fixture.window.BHFCommentary.loadChapter("Ruth", 1);
  await fixture.flush();

  requests.get("/api/commentary/Ruth/1").resolve(payload("Ruth", 1, [
    entry(1, "book_introduction", "Ruth introduction loaded last request first.", anchor("Ruth", null, null, null, null)),
  ]));
  await fixture.flush();
  requests.get("/api/commentary/Genesis/1").resolve(payload("Genesis", 1, [
    entry(2, "book_introduction", "Stale Genesis introduction.", anchor("Genesis", null, null, null, null)),
  ]));
  await fixture.flush();

  assert.match(fixture.slot.textContent, /Ruth introduction loaded last request first\./);
  assert.doesNotMatch(fixture.slot.textContent, /Stale Genesis introduction\./);
});


test("restored verse selection remains focused after its chapter loads", async () => {
  const fixture = createFixture(async () => payload("John", 1, [
    entry(1, "verse_note", "Restored verse note.", anchor("John", 1, 4, 1, 4)),
  ]));

  fixture.window.BHFCommentary.focusSelection({book: "John", chapter: 1, startVerse: 4, endVerse: 4});
  await fixture.window.BHFCommentary.loadChapter("John", 1);

  const restoredNote = fixture.fullBody.querySelector("[data-commentary-entry-id]");
  assert.ok(restoredNote);
  assert.equal(restoredNote.classList.contains("is-focused"), true);
});
