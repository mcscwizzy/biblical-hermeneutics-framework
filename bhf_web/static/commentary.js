/* Synchronized, non-AI reader companion for published Tyndale Open Study Notes. */
(function () {
  "use strict";

  const cache = new Map();
  const inFlight = new Map();
  let requestSequence = 0;
  let activeKey = "";
  let pendingSelection = null;
  let contextSequence = 0;
  let contextKey = "";
  let renderedContextSignature = "";

  function key(book, chapter) {
    return `${String(book || "").trim().toLowerCase()}|${Number(chapter || 0)}`;
  }

  function body() {
    return document.querySelector("[data-commentary-body]");
  }

  function cardSlot() {
    return document.querySelector("[data-companion-tyndale-card-slot]");
  }

  function selectedVerses(selection) {
    const supplied = Array.isArray(selection?.selectedVerses)
      ? Array.from(new Set(selection.selectedVerses.map(Number).filter((verse) => Number.isInteger(verse) && verse > 0)))
      : [];
    if (supplied.length) return supplied.sort((left, right) => left - right);
    const start = Number(selection?.startVerse || selection?.verseStart || 0);
    const end = Number(selection?.endVerse || selection?.verseEnd || start);
    if (!Number.isInteger(start) || start <= 0) return [];
    return Array.from({length: Math.max(0, end - start + 1)}, (_unused, index) => start + index);
  }

  function formatReference(selection) {
    if (!selection?.book || !selection?.chapter) return "";
    const verses = selectedVerses(selection);
    if (!verses.length) return `${selection.book} ${selection.chapter}`;
    const ranges = [];
    let start = verses[0];
    let end = start;
    verses.slice(1).forEach((verse) => {
      if (verse === end + 1) {
        end = verse;
      } else {
        ranges.push(start === end ? String(start) : `${start}-${end}`);
        start = verse;
        end = verse;
      }
    });
    ranges.push(start === end ? String(start) : `${start}-${end}`);
    return `${selection.book} ${selection.chapter}:${ranges.join(",")}`;
  }

  function selectionKey(selection) {
    if (!selection?.book || !selection?.chapter) return "";
    const verses = selectedVerses(selection);
    return `${key(selection.book, selection.chapter)}|${verses.join(",")}`;
  }

  function selectionMatchesChapter(selection, book, chapter) {
    return Boolean(selection?.book)
      && key(selection.book, selection.chapter) === key(book, chapter);
  }

  function anchorMatchesBook(anchor, book) {
    return Boolean(anchor?.book)
      && String(anchor.book).trim().toLowerCase() === String(book || "").trim().toLowerCase();
  }

  function anchorChapterRange(anchor) {
    const start = Number(anchor?.start_chapter) || null;
    const end = Number(anchor?.end_chapter) || start;
    return {start, end};
  }

  function anchorOverlapsChapter(anchor, selection) {
    if (!anchorMatchesBook(anchor, selection.book)) return false;
    const chapter = Number(selection.chapter);
    const {start, end} = anchorChapterRange(anchor);
    return (!start || start <= chapter) && (!end || end >= chapter);
  }

  function readerVerseCount(selection) {
    const pane = document.querySelector("#chapter-reader .reader-pane.is-active");
    if (!pane) return 0;
    const heading = pane.querySelector("h3")?.textContent?.trim() || "";
    if (heading && heading.toLowerCase() !== `${selection.book} ${selection.chapter}`.toLowerCase()) return 0;
    return Array.from(pane.querySelectorAll("[data-verse]")).reduce((count, element) =>
      Math.max(count, Number(element.dataset.verse) || 0), 0);
  }

  function coversWholeChapter(anchor, selection, verseCount) {
    if (!verseCount || !anchorOverlapsChapter(anchor, selection)) return false;
    const chapter = Number(selection.chapter);
    const {start, end} = anchorChapterRange(anchor);
    return start === chapter
      && end === chapter
      && (Number(anchor.start_verse) || 1) <= 1
      && (Number(anchor.end_verse || anchor.start_verse) || Number.MAX_SAFE_INTEGER) >= verseCount;
  }

  function isIntroduction(entry) {
    return entry?.kind === "book_introduction" || entry?.kind === "book_introduction_summary";
  }

  function entriesForChapter(entries, selection, verseCount) {
    return (entries || []).filter((entry) => {
      if (isIntroduction(entry)) return false;
      const anchor = entry?.anchor;
      if (!anchorOverlapsChapter(anchor, selection)) return false;
      const {start} = anchorChapterRange(anchor);
      return Boolean(start) && (
        (anchor.start_verse == null && anchor.end_verse == null)
        || coversWholeChapter(anchor, selection, verseCount)
      );
    });
  }

  function entriesForVerses(entries, selection, verses) {
    return (entries || []).filter((entry) => {
      if (isIntroduction(entry)) return false;
      const anchor = entry?.anchor;
      if (!anchorOverlapsChapter(anchor, selection)) return false;
      const {start: startChapter, end: endChapter} = anchorChapterRange(anchor);
      if (!startChapter && !endChapter) return false;
      const chapter = Number(selection.chapter);
      const first = startChapter === chapter ? Number(anchor.start_verse) || 1 : 1;
      const last = endChapter === chapter
        ? Number(anchor.end_verse || anchor.start_verse) || Number.MAX_SAFE_INTEGER
        : Number.MAX_SAFE_INTEGER;
      return verses.some((verse) => verse >= first && verse <= last);
    });
  }

  function notePriority(entry, selection, verses) {
    const anchor = entry.anchor;
    const {start: startChapter, end: endChapter} = anchorChapterRange(anchor);
    const chapter = Number(selection.chapter);
    const startVerse = startChapter === chapter ? Number(anchor.start_verse) || 1 : 1;
    const endVerse = endChapter === chapter
      ? Number(anchor.end_verse || anchor.start_verse) || Number.MAX_SAFE_INTEGER
      : Number.MAX_SAFE_INTEGER;
    const contiguous = verses.every((verse, index) => verse === verses[0] + index);
    const selectedStart = verses[0];
    const selectedEnd = verses[verses.length - 1];

    const sameChapter = startChapter === chapter && endChapter === chapter;
    if (sameChapter && startVerse === endVerse && verses.includes(startVerse)) return 0;
    if (sameChapter && contiguous && startVerse === selectedStart && endVerse === selectedEnd) return 1;
    if (Number.isSafeInteger(endVerse) && Number.isSafeInteger(startVerse)) {
      return (sameChapter ? 10 : 1000 + Math.max(0, endChapter - startChapter) * 100)
        + Math.max(0, endVerse - startVerse);
    }
    return sameChapter ? 500 : 1000 + Math.max(0, endChapter - startChapter) * 100;
  }

  function orderedEntries(entries, selection, verses) {
    const seen = new Set();
    return (entries || [])
      .filter((entry) => {
        const id = String(entry?.id ?? entry?.external_id ?? "");
        if (id && seen.has(id)) return false;
        if (id) seen.add(id);
        return true;
      })
      .map((entry, index) => ({entry, index, priority: notePriority(entry, selection, verses)}))
      .sort((left, right) => left.priority - right.priority
        || (Number(left.entry.anchor.start_chapter) || 0) - (Number(right.entry.anchor.start_chapter) || 0)
        || (Number(left.entry.anchor.start_verse) || 0) - (Number(right.entry.anchor.start_verse) || 0)
        || (Number(left.entry.sort_order) || left.index) - (Number(right.entry.sort_order) || right.index)
        || String(left.entry.id ?? "").localeCompare(String(right.entry.id ?? "")))
      .map(({entry}) => entry);
  }

  function reference(anchor) {
    if (!anchor?.book) return "Chapter note";
    const startChapter = Number(anchor.start_chapter) || null;
    const endChapter = Number(anchor.end_chapter) || startChapter;
    if (!startChapter) return `${anchor.book} introduction`;
    const start = anchor.start_verse ? `${startChapter}:${anchor.start_verse}` : String(startChapter);
    if (!endChapter || endChapter === startChapter) {
      const endVerse = Number(anchor.end_verse || anchor.start_verse) || null;
      return endVerse && endVerse !== Number(anchor.start_verse)
        ? `${anchor.book} ${start}-${endVerse}`
        : `${anchor.book} ${start}`;
    }
    const end = anchor.end_verse ? `${endChapter}:${anchor.end_verse}` : String(endChapter);
    return `${anchor.book} ${start}-${end}`;
  }

  function sourceFooter(parent, source) {
    if (!source) return;
    const footer = document.createElement("footer");
    footer.className = "commentary-source tyndale-source";
    const name = document.createElement("strong");
    name.textContent = source.name || "Tyndale Open Study Notes";
    footer.appendChild(name);
    const attribution = source.attribution || source.license || "";
    if (attribution) {
      const text = document.createElement("p");
      text.textContent = attribution;
      footer.appendChild(text);
    }
    parent.appendChild(footer);
  }

  function appendWorkspaceButton(parent) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary tyndale-workspace-action";
    button.textContent = "Open full Tyndale workspace";
    button.addEventListener("click", () => {
      window.BHFStudyActions?.openWorkspaceTab?.("commentary");
    });
    parent.appendChild(button);
  }

  function cardParts(slot) {
    let status = slot.querySelector("[data-tyndale-live-status]");
    if (!status) {
      status = document.createElement("p");
      status.className = "visually-hidden tyndale-card-status";
      status.dataset.tyndaleLiveStatus = "true";
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      slot.appendChild(status);
    }
    let card = slot.querySelector(".companion-tyndale-card");
    if (!card) {
      card = document.createElement("article");
      card.className = "companion-section companion-tyndale-card";
      slot.appendChild(card);
    }
    return {card, status};
  }

  function cardFrame(selection, {statusText = "", busy = false, source = null} = {}) {
    const slot = cardSlot();
    if (!slot) return null;
    slot.hidden = false;
    const {card, status} = cardParts(slot);
    card.replaceChildren();
    card.setAttribute("aria-labelledby", "companion-tyndale-title");
    card.setAttribute("aria-busy", String(busy));
    status.textContent = statusText;

    const header = document.createElement("header");
    header.className = "companion-section-heading tyndale-card-heading";
    const title = document.createElement("h3");
    title.id = "companion-tyndale-title";
    title.textContent = "Tyndale Study Notes";
    const location = document.createElement("p");
    location.className = "tyndale-card-reference";
    location.textContent = selection.reference || formatReference(selection);
    header.append(title, location);
    card.appendChild(header);

    const content = document.createElement("div");
    content.className = "tyndale-card-content";
    content.dataset.tyndaleCardContent = "true";
    card.appendChild(content);
    sourceFooter(card, source);
    appendWorkspaceButton(card);
    return {card, content, status};
  }

  function unavailableMessage(payload) {
    if (payload?.reason === "commentary_not_installed") {
      return "Tyndale Study Notes are not installed for this installation. Open the full workspace to check available notes.";
    }
    return "Tyndale Study Notes are unavailable right now. Check your connection and try the full workspace later.";
  }

  function emptyMessage(selection, verses) {
    if (verses.length) {
      return "No Tyndale note is linked directly to this selection. Open the full Tyndale workspace to browse broader notes.";
    }
    if (Number(selection.chapter) === 1) {
      return "No Tyndale introduction is linked to this book in the installed notes. Open the full workspace to browse broader notes.";
    }
    return "No Tyndale chapter notes are linked to this passage. Open the full workspace to browse broader notes.";
  }

  function excerpt(text, limit = 320) {
    const value = String(text || "").trim();
    if (value.length <= limit) return value;
    const clipped = value.slice(0, limit);
    const boundary = clipped.lastIndexOf(" ");
    return `${clipped.slice(0, boundary > limit * 0.7 ? boundary : limit).trimEnd()}…`;
  }

  function noteHeading(entry) {
    return entry.title || reference(entry.anchor) || "Tyndale study note";
  }

  function renderLongBody(parent, heading, text, summaryLabel) {
    const details = document.createElement("details");
    details.className = "tyndale-note-details";
    const summary = document.createElement("summary");
    summary.textContent = summaryLabel;
    const bodyText = document.createElement("p");
    bodyText.textContent = text;
    details.append(summary, bodyText);
    parent.appendChild(details);
  }

  function renderIntroduction(content, full, summary) {
    const article = document.createElement("article");
    article.className = "tyndale-introduction";
    article.dataset.tyndaleEntryId = String(full?.id ?? summary?.id ?? "");
    const heading = document.createElement("h4");
    heading.textContent = full?.title || summary?.title || "Book introduction";
    article.appendChild(heading);

    if (full && summary) {
      const preview = document.createElement("p");
      preview.className = "tyndale-introduction-preview";
      preview.textContent = summary.body;
      article.appendChild(preview);
    } else if (full) {
      const preview = document.createElement("p");
      preview.className = "tyndale-introduction-preview";
      preview.textContent = excerpt(full.body);
      article.appendChild(preview);
    } else if (summary) {
      const preview = document.createElement("p");
      preview.className = "tyndale-introduction-preview";
      preview.textContent = summary.body;
      article.appendChild(preview);
    }

    if (full) {
      renderLongBody(article, full.title || "Book introduction", full.body, "Read the full introduction");
    }
    content.appendChild(article);
  }

  function renderNote(content, entry) {
    const article = document.createElement("article");
    article.className = "tyndale-note";
    article.dataset.tyndaleEntryId = String(entry.id ?? "");
    const heading = document.createElement("h4");
    heading.textContent = noteHeading(entry);
    article.appendChild(heading);
    const location = document.createElement("p");
    location.className = "tyndale-note-reference";
    location.textContent = reference(entry.anchor);
    article.appendChild(location);
    if (String(entry.body || "").length > 700) {
      renderLongBody(article, noteHeading(entry), entry.body, "Read this note");
    } else {
      const text = document.createElement("p");
      text.className = "tyndale-note-body";
      text.textContent = entry.body || "";
      article.appendChild(text);
    }
    content.appendChild(article);
  }

  function renderContextPayload(selection, payload) {
    const verses = selectedVerses(selection);
    const verseCount = readerVerseCount(selection);
    const contextSignature = `${selectionKey(selection)}|${verseCount}|${payload?.available}|${(payload?.entries || []).length}`;
    if (contextSignature === renderedContextSignature) return;
    renderedContextSignature = contextSignature;
    const frame = cardFrame(selection, {source: payload?.source});
    if (!frame) return;
    if (!payload?.available) {
      const message = document.createElement("p");
      message.className = "empty tyndale-card-empty";
      message.textContent = unavailableMessage(payload);
      frame.content.appendChild(message);
      frame.status.textContent = unavailableMessage(payload);
      return;
    }

    if (verses.length) {
      const matches = orderedEntries(entriesForVerses(payload.entries, selection, verses), selection, verses);
      if (!matches.length) {
        const message = document.createElement("p");
        message.className = "empty tyndale-card-empty";
        message.textContent = emptyMessage(selection, verses);
        frame.content.appendChild(message);
        frame.status.textContent = `No matching Tyndale note is linked to ${selection.reference || formatReference(selection)}.`;
        return;
      }
      matches.forEach((entry) => renderNote(frame.content, entry));
      frame.status.textContent = `${matches.length} Tyndale ${matches.length === 1 ? "note" : "notes"} linked to ${selection.reference || formatReference(selection)}.`;
      return;
    }

    if (Number(selection.chapter) === 1) {
      const introductions = (payload.entries || []).filter((entry) =>
        isIntroduction(entry) && anchorOverlapsChapter(entry.anchor, selection));
      const full = introductions.find((entry) => entry.kind === "book_introduction") || null;
      const summary = introductions.find((entry) => entry.kind === "book_introduction_summary") || null;
      if (full || summary) {
        renderIntroduction(frame.content, full, summary);
        frame.status.textContent = `Tyndale book introduction loaded for ${selection.reference || formatReference(selection)}.`;
        return;
      }
    } else {
      const matches = entriesForChapter(payload.entries, selection, verseCount)
        .slice()
        .sort((left, right) => (Number(left.anchor.start_verse) || 0) - (Number(right.anchor.start_verse) || 0)
          || (Number(left.sort_order) || 0) - (Number(right.sort_order) || 0));
      if (matches.length) {
        matches.forEach((entry) => renderNote(frame.content, entry));
        frame.status.textContent = `${matches.length} Tyndale ${matches.length === 1 ? "chapter note" : "chapter notes"} loaded for ${selection.reference || formatReference(selection)}.`;
        return;
      }
    }

    const message = document.createElement("p");
    message.className = "empty tyndale-card-empty";
    message.textContent = emptyMessage(selection, verses);
    frame.content.appendChild(message);
    frame.status.textContent = Number(selection.chapter) === 1
      ? `No Tyndale book introduction is available for ${selection.book}.`
      : `No Tyndale chapter notes are linked to ${selection.reference || formatReference(selection)}.`;
  }

  function showContextLoading(selection) {
    const frame = cardFrame(selection, {
      statusText: `Loading Tyndale Study Notes for ${selection.reference || formatReference(selection)}.`,
      busy: true,
    });
    if (!frame) return;
    const message = document.createElement("p");
    message.className = "empty tyndale-card-loading";
    message.textContent = `Loading Tyndale Study Notes for ${selection.reference || formatReference(selection)}…`;
    frame.content.appendChild(message);
  }

  function showContextUnavailable(selection) {
    const frame = cardFrame(selection, {
      statusText: `Tyndale Study Notes are unavailable for ${selection.reference || formatReference(selection)}.`,
    });
    if (!frame) return;
    const message = document.createElement("p");
    message.className = "empty tyndale-card-empty";
    message.textContent = unavailableMessage(null);
    frame.content.appendChild(message);
  }

  function syncContext(selection) {
    const slot = cardSlot();
    if (!selection?.book || !Number(selection.chapter)) {
      contextSequence += 1;
      contextKey = "";
      renderedContextSignature = "";
      if (slot) {
        const parts = cardParts(slot);
        parts.status.textContent = "";
        parts.card.replaceChildren();
        slot.hidden = true;
      }
      return;
    }
    const currentKey = selectionKey(selection);
    if (currentKey === contextKey) return;
    contextKey = currentKey;
    renderedContextSignature = "";
    const requestId = ++contextSequence;
    const currentSelection = {...selection};
    showContextLoading(currentSelection);
    loadPayload(currentSelection.book, currentSelection.chapter)
      .then((payload) => {
        if (requestId !== contextSequence || contextKey !== currentKey) return;
        renderContextPayload(currentSelection, payload);
      })
      .catch(() => {
        if (requestId !== contextSequence || contextKey !== currentKey) return;
        contextKey = "";
        showContextUnavailable(currentSelection);
      });
  }

  function render(payload) {
    const target = body();
    if (!target) return;
    target.replaceChildren();
    if (!payload?.available) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = payload?.reason === "commentary_not_installed"
        ? "Tyndale Study Notes are not installed. Import the official local archive to enable this pane."
        : "Tyndale Study Notes are unavailable for this installation.";
      target.appendChild(empty);
      return;
    }
    const heading = document.createElement("p");
    heading.className = "commentary-location";
    heading.textContent = `${payload.book} ${payload.chapter}`;
    target.appendChild(heading);
    if (!payload.entries?.length) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "No Tyndale notes are available for this chapter.";
      target.appendChild(empty);
    }
    for (const entry of payload.entries || []) {
      const article = document.createElement("article");
      article.className = "commentary-entry";
      article.dataset.commentaryEntryId = String(entry.id);
      const title = document.createElement("h3");
      title.textContent = entry.title || reference(entry.anchor);
      const kind = document.createElement("span");
      kind.className = "commentary-kind";
      kind.textContent = String(entry.kind || "study note").replaceAll("_", " ");
      const text = document.createElement("p");
      text.textContent = entry.body || "";
      article.append(title, kind, text);
      target.appendChild(article);
    }
    sourceFooter(target, payload.source);
    if (pendingSelection) focusFullPane(pendingSelection);
  }

  function focusFullPane(selection) {
    const target = body();
    if (!target || !selection) return;
    const verses = selectedVerses(selection);
    const targetKey = key(selection.book, selection.chapter);
    target.querySelectorAll("[data-commentary-entry-id]").forEach((element) => {
      const entry = cache.get(activeKey)?.entries?.find((item) => String(item.id) === element.dataset.commentaryEntryId);
      const anchor = entry?.anchor;
      const relevant = targetKey === activeKey
        && verses.length > 0
        && anchorOverlapsChapter(anchor, selection)
        && entriesForVerses([entry], selection, verses).length > 0;
      element.classList.toggle("is-focused", relevant);
    });
  }

  function loadPayload(book, chapter) {
    const currentKey = key(book, chapter);
    if (cache.has(currentKey)) return Promise.resolve(cache.get(currentKey));
    if (inFlight.has(currentKey)) return inFlight.get(currentKey);
    const api = window.BHFApi;
    if (!api?.requestJson) return Promise.reject(new Error("Commentary API is not available."));
    const pending = Promise.resolve()
      .then(() => api.requestJson(
        `/api/commentary/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`,
        {},
        "Could not load Tyndale Study Notes.",
      ))
      .then((payload) => {
        cache.set(currentKey, payload);
        return payload;
      })
      .finally(() => {
        if (inFlight.get(currentKey) === pending) inFlight.delete(currentKey);
      });
    inFlight.set(currentKey, pending);
    return pending;
  }

  async function loadChapter(book, chapter) {
    const requestId = ++requestSequence;
    const currentKey = key(book, chapter);
    activeKey = currentKey;
    if (pendingSelection && !selectionMatchesChapter(pendingSelection, book, chapter)) {
      pendingSelection = null;
    }
    const currentSelection = window.BHFStudySelection?.getState?.();
    if (!pendingSelection && selectionMatchesChapter(currentSelection, book, chapter) && selectedVerses(currentSelection).length) {
      pendingSelection = {...currentSelection};
    }
    const selectionForChapter = selectionMatchesChapter(pendingSelection, book, chapter)
      ? pendingSelection
      : selectionMatchesChapter(currentSelection, book, chapter)
        ? currentSelection
        : {book, chapter: Number(chapter), selectedVerses: [], reference: `${book} ${chapter}`};
    syncContext(selectionForChapter);
    const target = body();
    if (!target) return;
    if (cache.has(currentKey)) {
      const payload = cache.get(currentKey);
      render(payload);
      const latestSelection = window.BHFStudySelection?.getState?.();
      renderContextPayload(
        selectionMatchesChapter(latestSelection, book, chapter) ? latestSelection : selectionForChapter,
        payload,
      );
      return;
    }
    const loading = document.createElement("p");
    loading.className = "empty";
    loading.textContent = `Loading Tyndale Study Notes for ${book} ${chapter}…`;
    target.replaceChildren(loading);
    try {
      const payload = await loadPayload(book, chapter);
      if (requestId !== requestSequence || activeKey !== currentKey) return;
      render(payload);
      const latestSelection = window.BHFStudySelection?.getState?.();
      renderContextPayload(
        selectionMatchesChapter(latestSelection, book, chapter) ? latestSelection : selectionForChapter,
        payload,
      );
      for (const neighbor of [Number(chapter) - 1, Number(chapter) + 1]) {
        if (neighbor > 0) prefetch(book, neighbor);
      }
    } catch (_error) {
      if (requestId === requestSequence && activeKey === currentKey) {
        render({available: false, reason: "commentary_database_error"});
      }
    }
  }

  function prefetch(book, chapter) {
    loadPayload(book, chapter).catch(() => {});
  }

  function focusSelection(selection) {
    if (!selection) return;
    pendingSelection = selectedVerses(selection).length ? {...selection} : null;
    if (key(selection.book, selection.chapter) === activeKey) focusFullPane(selection);
    syncContext(selection);
  }

  function clearSelection() {
    pendingSelection = null;
    body()?.querySelectorAll("[data-commentary-entry-id]").forEach((element) => {
      element.classList.remove("is-focused");
    });
    const selection = window.BHFStudySelection?.getState?.();
    if (selection?.book && selection?.chapter) syncContext(selection);
  }

  window.BHFCommentary = {loadChapter, focusSelection, clearSelection};

  if (window.BHFStudySelection?.subscribe) {
    window.BHFStudySelection.subscribe((selection) => {
      pendingSelection = selectedVerses(selection).length ? {...selection} : null;
      if (key(selection.book, selection.chapter) === activeKey && pendingSelection) {
        focusFullPane(pendingSelection);
      } else if (key(selection.book, selection.chapter) === activeKey) {
        body()?.querySelectorAll("[data-commentary-entry-id]").forEach((element) => {
          element.classList.remove("is-focused");
        });
      }
      syncContext(selection);
    });
  } else {
    syncContext(window.BHFStudySelection?.getState?.() || null);
  }
})();
