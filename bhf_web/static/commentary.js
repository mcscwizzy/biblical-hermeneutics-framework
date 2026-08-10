/* Synchronized, non-AI reader companion for the local commentary resource. */
(function () {
  const cache = new Map();
  let requestSequence = 0;
  let activeKey = "";
  let pendingSelection = null;

  function key(book, chapter) {
    return `${String(book || "").trim().toLowerCase()}|${Number(chapter || 0)}`;
  }

  function body() {
    return document.querySelector("[data-commentary-body]");
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function reference(anchor) {
    if (!anchor) return "Chapter note";
    const start = anchor.start_verse ? `${anchor.start_chapter}:${anchor.start_verse}` : `${anchor.start_chapter}`;
    const end = anchor.end_verse && anchor.end_verse !== anchor.start_verse
      ? `-${anchor.end_verse}`
      : "";
    return `${anchor.book} ${start}${end}`;
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
      kind.textContent = entry.kind.replaceAll("_", " ");
      const text = document.createElement("p");
      text.textContent = entry.body;
      article.append(title, kind, text);
      target.appendChild(article);
    }
    if (payload.source) {
      const source = document.createElement("footer");
      source.className = "commentary-source";
      source.innerHTML = `<strong>${escapeHtml(payload.source.name)}</strong><br>${escapeHtml(payload.source.attribution || payload.source.license || "")}`;
      target.appendChild(source);
    }
    if (pendingSelection) focusSelection(pendingSelection);
  }

  async function loadChapter(book, chapter) {
    const requestId = ++requestSequence;
    const currentKey = key(book, chapter);
    activeKey = currentKey;
    pendingSelection = null;
    const target = body();
    if (!target) return;
    if (cache.has(currentKey)) {
      render(cache.get(currentKey));
      return;
    }
    target.innerHTML = `<p class="empty">Loading Tyndale Study Notes for ${escapeHtml(book)} ${escapeHtml(chapter)}...</p>`;
    try {
      const api = window.BHFApi;
      if (!api?.requestJson) throw new Error("Commentary API is not available.");
      const payload = await api.requestJson(
        `/api/commentary/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`,
        {},
        "Could not load Tyndale Study Notes.",
      );
      if (requestId !== requestSequence || activeKey !== currentKey) return;
      cache.set(currentKey, payload);
      render(payload);
      // Keep adjacent chapters warm without changing the visible chapter.
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
    const currentKey = key(book, chapter);
    if (cache.has(currentKey)) return;
    const api = window.BHFApi;
    if (!api?.requestJson) return;
    api.requestJson(`/api/commentary/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`, {}, "").then((payload) => {
      cache.set(currentKey, payload);
    }).catch(() => {});
  }

  function focusSelection(selection) {
    const target = body();
    if (!target || !selection) return;
    pendingSelection = {...selection};
    const start = Number(selection.startVerse || selection.verseStart || 0);
    const end = Number(selection.endVerse || selection.verseEnd || start);
    target.querySelectorAll("[data-commentary-entry-id]").forEach((entry) => {
      const anchor = cache.get(activeKey)?.entries?.find((item) => String(item.id) === entry.dataset.commentaryEntryId)?.anchor;
      const overlaps = anchor && anchor.start_chapter === Number(selection.chapter)
        && (anchor.start_verse == null || anchor.start_verse <= end)
        && (anchor.end_verse == null || anchor.end_verse >= start);
      entry.classList.toggle("is-focused", Boolean(overlaps));
    });
    // A reader selection is also used to create highlights. Keep the matching
    // notes marked, but leave the reader's viewport under the user's control.
  }

  function clearSelection() {
    pendingSelection = null;
    body()?.querySelectorAll(".commentary-entry.is-focused").forEach((entry) => entry.classList.remove("is-focused"));
  }

  window.BHFCommentary = {loadChapter, focusSelection, clearSelection};
})();
