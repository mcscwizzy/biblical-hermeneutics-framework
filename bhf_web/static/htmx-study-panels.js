let currentCanonicalBrowser = {
  results: [],
  selectedObjectId: null,
  query: "",
};

function loadNotes(book, chapter) {
  const list = document.querySelector("#notes-list");
  const count = document.querySelector("#notes-count");
  if (!list) {
    return;
  }
  return requestJson(`/api/notes/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`, {}, "Could not load notes.")
    .then((data) => {
      currentNotes = data.notes || [];
      renderNotes(currentNotes);
      applyVerseStateIndicatorsToReader();
      if (count) {
        count.textContent = String(currentNotes.length);
      }
    })
    .catch((error) => {
      list.innerHTML = errorHtml(error.message || "Could not load notes.");
    });
}

function loadHighlights(book, chapter) {
  const list = document.querySelector("#highlights-list");
  const count = document.querySelector("#highlights-count");
  if (!list) {
    return;
  }
  return requestJson(`/api/highlights/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`, {}, "Could not load highlights.")
    .then((data) => {
      currentHighlights = data.highlights || [];
      renderHighlights(currentHighlights);
      applyHighlightsToReader(currentHighlights);
      applyVerseStateIndicatorsToReader();
      if (count) {
        count.textContent = String(currentHighlights.length);
      }
    })
    .catch((error) => {
      list.innerHTML = errorHtml(error.message || "Could not load highlights.");
    });
}

function renderHighlights(highlights) {
  const list = document.querySelector("#highlights-list");
  if (!list) {
    return;
  }
  if (highlights.length === 0) {
    list.innerHTML = `<p class="empty">No highlights for this chapter yet.</p>`;
    return;
  }
  list.innerHTML = "";
  for (const highlight of highlights) {
    const article = document.createElement("article");
    article.className = "highlight-item";
    article.dataset.highlightId = highlight.id;

    const reference = document.createElement("h3");
    reference.textContent = formatReference(highlight.book, highlight.chapter, highlight.start_verse, highlight.end_verse);

    const chip = document.createElement("span");
    chip.className = `highlight-chip ${highlight.color}`;
    chip.textContent = highlight.color;

    const excerpt = document.createElement("p");
    excerpt.textContent = highlight.selected_text || "Highlighted passage";

    const actions = document.createElement("div");
    actions.className = "note-actions";
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "secondary danger";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => deleteExistingHighlight(highlight.id));

    actions.appendChild(remove);
    article.appendChild(reference);
    article.appendChild(chip);
    article.appendChild(excerpt);
    article.appendChild(actions);
    list.appendChild(article);
  }
}

function applyHighlightsToReader(highlights) {
  const reader = document.querySelector("#chapter-reader");
  if (!reader) {
    return;
  }
  reader.querySelectorAll("[data-verse]").forEach((verse) => {
    Array.from(verse.classList)
      .filter((className) => className.startsWith("highlight-"))
      .forEach((className) => verse.classList.remove(className));
  });
  for (const highlight of highlights) {
    reader.querySelectorAll("[data-verse]").forEach((verse) => {
      const verseNumber = Number(verse.dataset.verse);
      if (highlight.start_verse <= verseNumber && verseNumber <= highlight.end_verse) {
        verse.classList.add(`highlight-${highlight.color}`);
      }
    });
  }
}

function createHighlight(context) {
  if (!currentChapter) {
    return Promise.resolve();
  }
  return requestJson("/api/highlights", {
    method: "POST",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      book: context.book,
      chapter: context.chapter,
      start_verse: context.verseStart,
      end_verse: context.verseEnd,
      selected_text: context.selectedText,
      color: "yellow"
    })
  }, "Could not save highlight.")
    .then(() => {
      activateWorkspaceTab("highlights");
      return loadHighlights(currentChapter.book, currentChapter.chapter);
    });
}

function removeHighlightsForContext(context) {
  if (!currentChapter) {
    return Promise.resolve();
  }
  const highlights = highlightsForContext(context);
  if (highlights.length === 0) {
    return Promise.resolve();
  }
  return Promise.all(highlights.map((highlight) => requestJson(`/api/highlights/${encodeURIComponent(highlight.id)}`, {
    method: "DELETE",
    headers: { "Accept": "application/json" }
  }, "Could not remove highlight.")))
    .then(() => loadHighlights(currentChapter.book, currentChapter.chapter));
}

function renderNotes(notes) {
  const list = document.querySelector("#notes-list");
  if (!list) {
    return;
  }
  if (notes.length === 0) {
    list.innerHTML = `<p class="empty">No notes for this chapter yet.</p>`;
    return;
  }
  list.innerHTML = "";
  for (const note of notes) {
    const article = document.createElement("article");
    article.className = "note";
    article.dataset.noteId = note.id;

    const reference = document.createElement("h3");
    reference.textContent = formatReference(note.book, note.chapter, note.start_verse, note.end_verse);

    const body = document.createElement("p");
    body.textContent = note.body;

    if (Array.isArray(note.canonical_object_ids) && note.canonical_object_ids.length > 0) {
      const canonical = document.createElement("div");
      canonical.className = "canonical-note-links";
      appendCanonicalObjectBadges(canonical, note.canonical_object_ids, {
        variant: "note",
        compact: true,
      });
      article.appendChild(canonical);
    }

    const actions = document.createElement("div");
    actions.className = "note-actions";

    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "secondary";
    edit.textContent = "Edit";
    edit.addEventListener("click", () => openNoteEditor(note));

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "secondary danger";
    remove.textContent = "Delete";
    remove.addEventListener("click", () => deleteExistingNote(note.id));

    actions.appendChild(edit);
    actions.appendChild(remove);
    article.appendChild(reference);
    article.appendChild(body);
    article.appendChild(actions);
    list.appendChild(article);
  }
}

function openNoteEditor(existingNote) {
  if (!currentChapter) {
    return;
  }
  activateWorkspaceTab("notes");
  const editor = document.querySelector("#note-editor");
  if (!editor) {
    return;
  }
  const note = existingNote && existingNote.id ? existingNote : null;
  if (note) {
    noteContext = note;
  } else if (currentSelection) {
    noteContext = {
      id: "",
      book: currentChapter.book,
      chapter: currentChapter.chapter,
      start_verse: currentSelection.startVerse,
      end_verse: currentSelection.endVerse,
      selected_text: currentSelection.text,
      body: "",
      canonical_object_ids: getCanonicalObjectIdsFromAnswerPanel(),
    };
  } else {
    return;
  }

  editor.hidden = false;
  editor.elements.id.value = noteContext.id || "";
  editor.elements.body.value = noteContext.body || "";
  if (editor.elements.canonical_object_ids) {
    editor.elements.canonical_object_ids.value = canonicalObjectIdsToString(
      noteContext.canonical_object_ids || getCanonicalObjectIdsFromAnswerPanel()
    );
  }
  const reference = document.querySelector("#note-reference");
  if (reference) {
    reference.textContent = formatReference(
      noteContext.book,
      noteContext.chapter,
      noteContext.start_verse,
      noteContext.end_verse
    );
  }
  editor.elements.body.focus();
}

function closeNoteEditor() {
  const editor = document.querySelector("#note-editor");
  if (editor) {
    editor.hidden = true;
    editor.reset();
  }
  noteContext = null;
}

function saveNote(event) {
  event.preventDefault();
  if (!noteContext || !currentChapter) {
    return Promise.resolve();
  }
  const form = event.target;
  const payload = {
    ...noteContext,
    body: form.elements.body.value,
    canonical_object_ids: canonicalObjectIdsFromInput(form.elements.canonical_object_ids?.value || ""),
  };
  const noteId = form.elements.id.value;
  const url = noteId ? `/api/notes/${encodeURIComponent(noteId)}` : "/api/notes";
  const method = noteId ? "PUT" : "POST";
  return requestJson(url, {
    method,
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  }, "Could not save note.")
    .then(() => {
      closeNoteEditor();
      return loadNotes(currentChapter.book, currentChapter.chapter);
    });
}

function deleteExistingNote(noteId) {
  if (!currentChapter) {
    return Promise.resolve();
  }
  return requestJson(`/api/notes/${encodeURIComponent(noteId)}`, {
    method: "DELETE",
    headers: { "Accept": "application/json" }
  }, "Could not delete note.")
    .then(() => loadNotes(currentChapter.book, currentChapter.chapter));
}

function deleteExistingHighlight(highlightId) {
  if (!currentChapter) {
    return Promise.resolve();
  }
  return requestJson(`/api/highlights/${encodeURIComponent(highlightId)}`, {
    method: "DELETE",
    headers: { "Accept": "application/json" }
  }, "Could not remove highlight.")
    .then(() => loadHighlights(currentChapter.book, currentChapter.chapter));
}

function loadSavedStudies(book, chapter) {
  const list = document.querySelector("#saved-studies-list");
  const count = document.querySelector("#saved-studies-count");
  if (!list || !book || !chapter) {
    return Promise.resolve();
  }
  return requestJson(`/api/saved-studies?book=${encodeURIComponent(book)}&chapter=${encodeURIComponent(chapter)}`, {}, "Could not load saved studies.")
    .then((data) => {
      const studies = data.saved_studies || [];
      renderSavedStudies(studies);
      if (count) {
        count.textContent = String(studies.length);
      }
    })
    .catch((error) => {
      list.innerHTML = errorHtml(error.message || "Could not load saved studies.");
    });
}

function renderSavedStudies(studies) {
  const list = document.querySelector("#saved-studies-list");
  if (!list) {
    return;
  }
  if (studies.length === 0) {
    list.innerHTML = `<p class="empty">No saved studies for this chapter yet.</p>`;
    return;
  }
  list.innerHTML = "";
  for (const study of studies) {
    const article = document.createElement("article");
    article.className = "saved-study";
    article.dataset.savedStudyId = study.id;
    const studyType = prettyStudyType(study.study_type);

    const title = document.createElement("h3");
    title.textContent = study.title || formatReference(study.book, study.chapter, study.start_verse, study.end_verse);

    const meta = document.createElement("p");
    meta.className = "saved-study-meta";
    meta.textContent = `${formatReference(study.book, study.chapter, study.start_verse, study.end_verse)} · ${studyType}`;

    const excerpt = document.createElement("p");
    excerpt.textContent = study.selected_text || "Saved study";

    const actions = document.createElement("div");
    actions.className = "note-actions";

    const open = document.createElement("button");
    open.type = "button";
    open.className = "secondary";
    open.textContent = "Open";
    open.addEventListener("click", () => openSavedStudy(study.id));

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "secondary danger";
    remove.textContent = "Delete";
    remove.addEventListener("click", () => deleteSavedStudy(study.id));

    actions.appendChild(open);
    actions.appendChild(remove);
    article.appendChild(title);
    article.appendChild(meta);
    article.appendChild(excerpt);
    article.appendChild(actions);
    list.appendChild(article);
  }
}

function openSavedStudy(studyId) {
  activateWorkspaceTab("ask");
  const answerPanel = document.querySelector("#answer-panel");
  if (!answerPanel) {
    return Promise.resolve();
  }
  return requestText(`/api/saved-studies/${encodeURIComponent(studyId)}`, {
    headers: { "Accept": "text/html" }
  }, "Could not open saved study.")
    .then((html) => {
      answerPanel.innerHTML = html;
      activeLiveAnswerPanel = answerPanel;
      latestJobComplete = false;
      wireAnswerPanelControls(answerPanel);
    });
}

function deleteSavedStudy(studyId) {
  if (!currentChapter) {
    return Promise.resolve();
  }
  return requestJson(`/api/saved-studies/${encodeURIComponent(studyId)}`, {
    method: "DELETE",
    headers: { "Accept": "application/json" }
  }, "Could not delete saved study.")
    .then(() => loadSavedStudies(currentChapter.book, currentChapter.chapter));
}

function saveLatestStudy(event) {
  const sourceButton = event?.currentTarget || null;
  const jobId = sourceButton?.dataset.jobId || latestJobId;
  if (!jobId || (!sourceButton?.dataset.jobId && !latestJobComplete)) {
    window.alert("Run a study first, then save it.");
    return Promise.resolve();
  }
  const saveButton = sourceButton || activeLiveAnswerPanel?.querySelector("[data-save-study]") || null;
  if (saveButton) {
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";
  }
  return requestJson("/api/saved-studies", {
    method: "POST",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      job_id: jobId
    })
  }, "Could not save study.")
    .then(() => {
      if (saveButton) {
        saveButton.textContent = "Saved";
      }
      activateWorkspaceTab("saved");
      if (currentChapter) {
        return loadSavedStudies(currentChapter.book, currentChapter.chapter);
      }
    })
    .then(() => {
      updateSaveButtons();
    });
}

function wireAnswerPanelControls(answerPanel) {
  if (!answerPanel) {
    return;
  }
  answerPanel.querySelectorAll("[data-save-study]").forEach((button) => {
    if (!button.dataset.saveBound) {
      button.addEventListener("click", saveLatestStudy);
      button.dataset.saveBound = "true";
    }
  });
  wireCanonicalAnswerPanelControls(answerPanel);
  updateSaveButtons();
}

function updateSaveButtons() {
  document.querySelectorAll("[data-save-study]").forEach((button) => {
    const panel = button.closest(".answer-panel");
    const isActive = Boolean(activeLiveAnswerPanel) && panel === activeLiveAnswerPanel;
    button.disabled = !(isActive && (button.dataset.jobId || (latestJobId && latestJobComplete)));
  });
}

function formatReference(book, chapter, startVerse, endVerse) {
  if (!startVerse) {
    return `${book} ${chapter}`;
  }
  const suffix = Number(startVerse) === Number(endVerse) ? String(startVerse) : `${startVerse}-${endVerse}`;
  return `${book} ${chapter}:${suffix}`;
}

function prettyStudyType(value) {
  return String(value || "Study")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function initializeCanonicalBrowser() {
  const form = document.querySelector("[data-canonical-browser-form]");
  const resultsList = document.querySelector("[data-canonical-browser-results]");
  const detailPanel = document.querySelector("[data-canonical-detail-title]");
  if (!form && !resultsList && !detailPanel) {
    return;
  }
  if (document.body.dataset.canonicalBrowserBound === "true") {
    return;
  }
  document.body.dataset.canonicalBrowserBound = "true";

  if (form && !form.dataset.bound) {
    form.addEventListener("submit", handleCanonicalBrowserSubmit);
    form.dataset.bound = "true";
    const clearButton = form.querySelector("[data-canonical-browser-clear]");
    if (clearButton && !clearButton.dataset.bound) {
      clearButton.dataset.bound = "true";
      clearButton.addEventListener("click", handleCanonicalBrowserClear);
    }
  }

  const homeButton = document.querySelector("[data-canonical-browser-home]");
  if (homeButton && !homeButton.dataset.bound) {
    homeButton.dataset.bound = "true";
    homeButton.addEventListener("click", handleCanonicalBrowserHome);
  }

  const askButton = document.querySelector("[data-canonical-browser-ask]");
  if (askButton && !askButton.dataset.bound) {
    askButton.dataset.bound = "true";
    askButton.addEventListener("click", () => activateWorkspaceTab("ask"));
  }

  document.addEventListener("bhf:workspace-tab-changed", handleCanonicalWorkspaceTabChanged);
  loadCanonicalBrowser({ selectFirst: true }).catch(() => {
    // The browser should fail quietly if the local CKL API is unavailable.
  });
}

function handleCanonicalWorkspaceTabChanged(event) {
  if (event.detail?.tabId !== "context") {
    return;
  }
  if (currentCanonicalBrowser.results.length === 0) {
    loadCanonicalBrowser({ selectFirst: true }).catch(() => {});
  }
}

function handleCanonicalBrowserSubmit(event) {
  event.preventDefault();
  loadCanonicalBrowser({ selectFirst: true }).catch((error) => {
    showCanonicalBrowserError(error.message || "Could not load canonical objects.");
  });
}

function handleCanonicalBrowserClear(event) {
  event.preventDefault();
  const form = document.querySelector("[data-canonical-browser-form]");
  if (form) {
    form.reset();
  }
  loadCanonicalBrowser({ selectFirst: true }).catch((error) => {
    showCanonicalBrowserError(error.message || "Could not load canonical objects.");
  });
}

function handleCanonicalBrowserHome(event) {
  event.preventDefault();
  const form = document.querySelector("[data-canonical-browser-form]");
  if (form) {
    form.reset();
  }
  loadCanonicalBrowser({ selectFirst: true }).catch((error) => {
    showCanonicalBrowserError(error.message || "Could not load canonical objects.");
  });
}

async function loadCanonicalBrowser(options = {}) {
  const form = document.querySelector("[data-canonical-browser-form]");
  const resultsList = document.querySelector("[data-canonical-browser-results]");
  const summary = document.querySelector("[data-canonical-browser-summary]");
  const count = document.querySelector("[data-canonical-browser-count]");
  if (!resultsList) {
    return;
  }

  const formData = form ? new FormData(form) : new FormData();
  const params = new URLSearchParams();
  const query = String(options.query ?? formData.get("q") ?? "").trim();
  const objectType = String(options.objectType ?? formData.get("type") ?? "all").trim();
  const reviewStatus = String(options.reviewStatus ?? formData.get("review_status") ?? "all").trim();
  const contentStatus = String(options.contentStatus ?? formData.get("content_status") ?? "all").trim();
  const includePlaceholders = options.includePlaceholders !== undefined
    ? Boolean(options.includePlaceholders)
    : true;

  if (query) {
    params.set("q", query);
  }
  if (objectType && objectType !== "all") {
    params.set("type", objectType);
  }
  if (reviewStatus && reviewStatus !== "all") {
    params.set("review_status", reviewStatus);
  }
  if (contentStatus && contentStatus !== "all") {
    params.set("content_status", contentStatus);
  }
  if (!includePlaceholders) {
    params.set("include_placeholders", "false");
  }

  const url = `/api/canonical/search?${params.toString()}`;
  resultsList.innerHTML = `<p class="empty">Loading canonical context...</p>`;
  if (summary) {
    summary.textContent = query ? `Searching for "${query}"...` : "Browsing curated canonical objects...";
  }

  const data = await requestJson(url, {}, "Could not load canonical objects.");
  currentCanonicalBrowser.query = query;
  currentCanonicalBrowser.results = Array.isArray(data.results) ? data.results : [];

  renderCanonicalBrowserResults(currentCanonicalBrowser.results);
  if (count) {
    count.textContent = String(currentCanonicalBrowser.results.length);
  }

  if (summary) {
    if (currentCanonicalBrowser.results.length === 0) {
      summary.textContent = query
        ? `No canonical objects matched "${query}".`
        : "No canonical objects available for the current filters.";
    } else {
      const retrievalMethod = String(data.metadata?.retrieval_method || data.filters?.type || "browse");
      summary.textContent = query
        ? `Found ${currentCanonicalBrowser.results.length} canonical object${currentCanonicalBrowser.results.length === 1 ? "" : "s"} using ${retrievalMethod}.`
        : `Showing ${currentCanonicalBrowser.results.length} canonical object${currentCanonicalBrowser.results.length === 1 ? "" : "s"} from the browse catalog.`;
    }
  }

  if (currentCanonicalBrowser.results.length > 0) {
    const selectedId = options.selectObjectId || currentCanonicalBrowser.selectedObjectId || currentCanonicalBrowser.results[0].id;
    const selected = currentCanonicalBrowser.results.find((item) => item.id === selectedId) || currentCanonicalBrowser.results[0];
    if (selected) {
      await loadCanonicalObject(selected.id, { preview: selected });
    }
  } else {
    renderCanonicalBrowserDetail(null);
  }
}

function renderCanonicalBrowserResults(results) {
  const list = document.querySelector("[data-canonical-browser-results]");
  if (!list) {
    return;
  }
  if (!Array.isArray(results) || results.length === 0) {
    list.innerHTML = `<p class="empty">Browse the curated canonical library or search for a topic.</p>`;
    return;
  }

  list.innerHTML = "";
  for (const item of results) {
    const article = document.createElement("article");
    article.className = "canonical-result-card";
    article.dataset.canonicalObjectId = item.id;
    if (currentCanonicalBrowser.selectedObjectId && currentCanonicalBrowser.selectedObjectId === item.id) {
      article.classList.add("is-selected");
    }

    const header = document.createElement("div");
    header.className = "canonical-result-header";

    const titleWrap = document.createElement("div");
    titleWrap.className = "canonical-result-title-wrap";

    const titleButton = document.createElement("button");
    titleButton.type = "button";
    titleButton.className = "canonical-result-title";
    titleButton.textContent = item.title || item.id;
    titleButton.addEventListener("click", () => loadCanonicalObject(item.id, { preview: item }));

    const summary = document.createElement("p");
    summary.className = "canonical-result-summary";
    summary.textContent = item.summary || "No summary recorded.";

    titleWrap.appendChild(titleButton);
    titleWrap.appendChild(summary);

    const status = document.createElement("span");
    status.className = "canonical-status-chip";
    status.textContent = formatCanonicalLabel(item.review_status || "unknown");

    header.appendChild(titleWrap);
    header.appendChild(status);

    const badges = document.createElement("div");
    badges.className = "canonical-result-badges";
    appendCanonicalBadge(badges, formatCanonicalLabel(item.type || "unknown"), "search-badge");
    appendCanonicalBadge(badges, formatCanonicalLabel(item.content_status || "unknown"), "search-badge");
    appendCanonicalBadge(badges, formatCanonicalLabel(item.confidence || "unrated"), "search-badge");
    appendCanonicalBadge(badges, formatCanonicalLabel(item.match_type || "browse"), "search-badge search-badge--muted");

    const reason = document.createElement("p");
    reason.className = "canonical-result-reason";
    reason.textContent = item.reason || "Browse result";

    const actions = document.createElement("div");
    actions.className = "canonical-result-actions";
    const viewButton = document.createElement("button");
    viewButton.type = "button";
    viewButton.className = "secondary";
    viewButton.textContent = "View details";
    viewButton.dataset.testid = "canonical-result-view-button";
    viewButton.addEventListener("click", () => loadCanonicalObject(item.id, { preview: item }));

    const linkButton = document.createElement("button");
    linkButton.type = "button";
    linkButton.className = "secondary";
    linkButton.textContent = "Link to note";
    linkButton.dataset.testid = "canonical-result-link-note";
    linkButton.addEventListener("click", () => appendCanonicalObjectToCurrentNote(item.id));

    actions.appendChild(viewButton);
    actions.appendChild(linkButton);

    article.appendChild(header);
    article.appendChild(badges);
    article.appendChild(reason);
    article.appendChild(actions);
    list.appendChild(article);
  }
}

async function loadCanonicalObject(objectId, options = {}) {
  const normalizedId = normalizeCanonicalObjectId(objectId);
  if (!normalizedId) {
    return;
  }
  currentCanonicalBrowser.selectedObjectId = normalizedId;
  const results = currentCanonicalBrowser.results || [];
  const preview = options.preview || results.find((item) => normalizeCanonicalObjectId(item.id) === normalizedId) || null;
  const detailPanel = document.querySelector("[data-canonical-detail-title]");
  if (detailPanel && !preview) {
    renderCanonicalBrowserDetail(null, { loading: true });
  }

  try {
    const detail = await requestJson(`/api/canonical/objects/${encodeURIComponent(normalizedId)}`, {}, "Could not load canonical object.");
    renderCanonicalBrowserDetail(detail, { selectedId: normalizedId });
  } catch (error) {
    if (preview) {
      renderCanonicalBrowserDetail(preview, { selectedId: normalizedId, error: error.message || "Could not load canonical object." });
      return;
    }
    renderCanonicalBrowserDetail(null, { error: error.message || "Could not load canonical object." });
  }
  renderCanonicalBrowserResults(currentCanonicalBrowser.results);
}

function renderCanonicalBrowserDetail(object, options = {}) {
  const title = document.querySelector("[data-canonical-detail-title]");
  const summary = document.querySelector("[data-canonical-detail-summary]");
  const status = document.querySelector("[data-canonical-detail-status]");
  const badges = document.querySelector("[data-canonical-detail-badges]");
  const reason = document.querySelector("[data-canonical-detail-reason]");
  const scripture = document.querySelector("[data-canonical-detail-scripture]");
  const related = document.querySelector("[data-canonical-detail-related]");
  const sources = document.querySelector("[data-canonical-detail-sources]");
  const editor = document.querySelector("[data-canonical-detail-editor]");
  const curation = document.querySelector("[data-canonical-detail-curation]");
  const addNote = document.querySelector("[data-canonical-detail-add-note]");
  if (!title || !summary || !status || !badges || !reason || !scripture || !related || !sources) {
    return;
  }

  badges.innerHTML = "";
  scripture.innerHTML = "";
  related.innerHTML = "";
  sources.innerHTML = "";
  reason.hidden = true;
  reason.textContent = "";

  if (!object) {
    title.textContent = "Select an object";
    summary.textContent = options.error
      ? options.error
      : options.loading
        ? "Loading canonical object..."
        : "Search results will populate here.";
    status.textContent = "--";
    if (curation) {
      curation.href = "/curation";
    }
    if (editor) {
      editor.hidden = true;
      editor.href = "/canonical/editor";
    }
    if (addNote) {
      addNote.disabled = true;
    }
    if (options.error) {
      reason.hidden = false;
      reason.textContent = options.error;
    }
    return;
  }

  const normalizedId = normalizeCanonicalObjectId(object.id);
  currentCanonicalBrowser.selectedObjectId = normalizedId;
  title.textContent = object.title || object.id || "Canonical object";
  summary.textContent = object.summary || "No summary recorded.";
  status.textContent = formatCanonicalLabel(object.review_status || "unknown");
  if (curation) {
    curation.href = object.browse_url || "/curation";
  }
  if (editor) {
    editor.href = `/canonical/editor?object_id=${encodeURIComponent(normalizedId)}`;
    editor.hidden = object.content_status === "complete" && object.review_status === "approved";
  }
  if (addNote) {
    addNote.disabled = false;
  }

  appendCanonicalBadge(badges, formatCanonicalLabel(object.type || "unknown"), "search-badge");
  appendCanonicalBadge(badges, formatCanonicalLabel(object.content_status || "unknown"), "search-badge");
  appendCanonicalBadge(badges, formatCanonicalLabel(object.review_status || "unknown"), "search-badge");
  appendCanonicalBadge(badges, formatCanonicalLabel(object.confidence || "unrated"), "search-badge");
  appendCanonicalBadge(badges, `importance ${object.importance ?? 0}`, "search-badge");
  if (object.source_count !== undefined) {
    appendCanonicalBadge(badges, `${object.source_count} source${Number(object.source_count) === 1 ? "" : "s"}`, "search-badge");
  }

  const reasonText = object.reason || object.match_type || "";
  if (reasonText) {
    reason.hidden = false;
    reason.textContent = reasonText;
  }

  if (Array.isArray(object.scripture_references) && object.scripture_references.length > 0) {
    for (const ref of object.scripture_references) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "scripture-link";
      button.textContent = ref.reference || "Scripture reference";
      button.dataset.bibleReference = ref.reference || "";
      button.addEventListener("click", () => openScriptureReference(ref.reference));

      const note = document.createElement("span");
      note.className = "scripture-link-note";
      note.textContent = ref.relationship || "";

      const wrapper = document.createElement("div");
      wrapper.className = "canonical-detail-item";
      wrapper.appendChild(button);
      if (note.textContent) {
        wrapper.appendChild(note);
      }
      scripture.appendChild(wrapper);
    }
  } else {
    scripture.innerHTML = `<p class="empty">No Scripture references recorded.</p>`;
  }

  const relatedObjects = Array.isArray(object.related_object_links) && object.related_object_links.length > 0
    ? object.related_object_links
    : Array.isArray(object.related_objects)
      ? object.related_objects
      : [];
  if (relatedObjects.length > 0) {
    for (const relation of relatedObjects) {
      const objectId = relation.id || relation.object_id || "";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "canonical-related-object";
      button.textContent = relation.title || objectId || "Related object";
      button.addEventListener("click", () => loadCanonicalObject(objectId || relation.id || ""));

      const meta = document.createElement("p");
      meta.className = "canonical-detail-meta";
      meta.textContent = [relation.relationship, relation.weight ? `weight ${relation.weight}` : ""]
        .filter(Boolean)
        .join(" · ");

      const wrapper = document.createElement("div");
      wrapper.className = "canonical-detail-item";
      wrapper.appendChild(button);
      if (meta.textContent) {
        wrapper.appendChild(meta);
      }
      related.appendChild(wrapper);
    }
  } else {
    related.innerHTML = `<p class="empty">No related objects recorded.</p>`;
  }

  if (Array.isArray(object.sources) && object.sources.length > 0) {
    for (const source of object.sources) {
      const article = document.createElement("article");
      article.className = "canonical-source-card";

      const sourceTitle = document.createElement("h4");
      sourceTitle.textContent = source.title || "Untitled source";
      article.appendChild(sourceTitle);

      const meta = document.createElement("p");
      meta.className = "canonical-detail-meta";
      const parts = [
        source.author,
        source.publisher,
        source.year,
        source.source_type,
        source.locator,
      ].filter((value) => value !== null && value !== undefined && String(value).trim() !== "");
      meta.textContent = parts.join(" · ");
      if (meta.textContent) {
        article.appendChild(meta);
      }

      if (source.url) {
        const link = document.createElement("a");
        link.href = source.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = source.url;
        article.appendChild(link);
      }

      if (source.notes) {
        const notes = document.createElement("p");
        notes.className = "canonical-detail-notes";
        notes.textContent = source.notes;
        article.appendChild(notes);
      }

      sources.appendChild(article);
    }
  } else {
    sources.innerHTML = `<p class="empty">No sources recorded.</p>`;
  }

  if (options.error && reason) {
    reason.hidden = false;
    reason.textContent = options.error;
  }

  renderCanonicalBrowserResults(currentCanonicalBrowser.results);
}

function showCanonicalBrowserError(message) {
  const summary = document.querySelector("[data-canonical-browser-summary]");
  const resultsList = document.querySelector("[data-canonical-browser-results]");
  if (summary) {
    summary.textContent = message;
  }
  if (resultsList) {
    resultsList.innerHTML = `<div class="error" role="alert"><p>${escapeHtml(message)}</p></div>`;
  }
  renderCanonicalBrowserDetail(null, { error: message });
}

function handleCanonicalPanelClick(event) {
  const canonicalButton = event.target.closest("[data-canonical-object-id]");
  if (canonicalButton) {
    event.preventDefault();
    const objectId = canonicalButton.dataset.canonicalObjectId || "";
    if (!objectId) {
      return;
    }
    activateWorkspaceTab("context");
    loadCanonicalObject(objectId, { preview: canonicalButton.dataset.canonicalObjectTitle ? { id: objectId, title: canonicalButton.dataset.canonicalObjectTitle } : null }).catch(() => {});
    return;
  }

  const scriptureButton = event.target.closest("[data-bible-reference]");
  if (scriptureButton) {
    event.preventDefault();
    openScriptureReference(scriptureButton.dataset.bibleReference || "");
    return;
  }

  const noteButton = event.target.closest("[data-canonical-link-note]");
  if (noteButton) {
    event.preventDefault();
    appendCanonicalObjectToCurrentNote(noteButton.dataset.canonicalLinkNote || "");
    return;
  }

  const openBrowser = event.target.closest("[data-open-canonical-browser]");
  if (openBrowser) {
    event.preventDefault();
    activateWorkspaceTab("context");
  }
}

function wireCanonicalAnswerPanelControls(answerPanel) {
  if (!answerPanel || answerPanel.dataset.canonicalBound === "true") {
    return;
  }
  answerPanel.dataset.canonicalBound = "true";
  answerPanel.addEventListener("click", handleCanonicalPanelClick);
}

function appendCanonicalObjectToCurrentNote(objectId) {
  const normalizedId = normalizeCanonicalObjectId(objectId);
  if (!normalizedId) {
    return;
  }
  const noteEditor = document.querySelector("#note-editor");
  if (!noteEditor || noteEditor.hidden) {
    const addNoteButton = document.querySelector("[data-add-note]");
    if (addNoteButton) {
      addNoteButton.click();
    }
  }
  const input = document.querySelector("#note-editor [name='canonical_object_ids']");
  if (!input) {
    activateWorkspaceTab("notes");
    return;
  }
  const ids = canonicalObjectIdsFromInput(input.value);
  if (!ids.includes(normalizedId)) {
    ids.push(normalizedId);
  }
  input.value = canonicalObjectIdsToString(ids);
  if (noteContext) {
    noteContext.canonical_object_ids = ids;
  }
  activateWorkspaceTab("notes");
}

function getCanonicalObjectIdsFromAnswerPanel() {
  const answerPanel = activeLiveAnswerPanel || document.querySelector("#answer-panel");
  if (!answerPanel) {
    return [];
  }
  const ids = Array.from(answerPanel.querySelectorAll(".canonical-object-badge[data-canonical-object-id]"))
    .map((button) => normalizeCanonicalObjectId(button.dataset.canonicalObjectId || ""));
  return Array.from(new Set(ids.filter(Boolean)));
}

function canonicalObjectIdsFromInput(value) {
  return Array.from(
    new Set(
      String(value || "")
        .split(/[\n,;]+/)
        .map((item) => normalizeCanonicalObjectId(item))
        .filter(Boolean)
    )
  );
}

function canonicalObjectIdsToString(ids) {
  return Array.from(new Set((ids || []).map((item) => normalizeCanonicalObjectId(item)).filter(Boolean))).join(", ");
}

function normalizeCanonicalObjectId(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-");
}

function formatCanonicalLabel(value) {
  return String(value || "")
    .trim()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function appendCanonicalBadge(container, text, className) {
  if (!container || !text) {
    return;
  }
  const badge = document.createElement("span");
  badge.className = className || "search-badge";
  badge.textContent = text;
  container.appendChild(badge);
}

function appendCanonicalObjectBadges(container, ids, options = {}) {
  if (!container) {
    return;
  }
  const variantClass = options.variant === "note" ? "canonical-object-badge--note" : "";
  for (const objectId of canonicalObjectIdsFromInput(Array.isArray(ids) ? ids.join(",") : ids)) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = ["canonical-object-badge", variantClass].filter(Boolean).join(" ");
    button.dataset.canonicalObjectId = objectId;
    button.textContent = objectId;
    button.addEventListener("click", () => {
      activateWorkspaceTab("context");
      loadCanonicalObject(objectId).catch(() => {});
    });
    container.appendChild(button);
  }
}

function openScriptureReference(reference) {
  const parsed = typeof parsePassageReference === "function" ? parsePassageReference(reference) : null;
  if (!parsed || !parsed.book) {
    return;
  }
  activateWorkspaceTab("ask");
  if (typeof navigateToPassage === "function") {
    navigateToPassage(parsed.book, parsed.chapter, parsed.verseStart, parsed.verseEnd).catch(() => {});
  }
}

document.addEventListener("DOMContentLoaded", initializeCanonicalBrowser);
