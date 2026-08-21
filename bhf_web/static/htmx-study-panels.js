let currentCanonicalBrowser = {
  results: [],
  selectedObjectId: null,
  query: "",
};
let allNotes = [];
let notesView = "passage";
let noteAutoSaveTimer = null;
let noteAutoSaveInFlight = false;
let noteDraftDirty = false;
let noteCloseAfterSave = false;

function hasNoteReference(note) {
  return Boolean(note?.book && note?.chapter);
}

function setNoteSaveStatus(message) {
  const status = document.querySelector("[data-note-save-status]");
  if (status) {
    status.textContent = message;
  }
}

function updateNotesViewControls() {
  document.querySelectorAll("[data-notes-view]").forEach((button) => {
    const active = button.dataset.notesView === notesView;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function notesForCurrentPassage() {
  if (!currentSelection) {
    return currentNotes;
  }
  return currentNotes.filter((note) => (
    hasNoteReference(note)
    && Number(note.start_verse) <= Number(currentSelection.endVerse)
    && Number(note.end_verse) >= Number(currentSelection.startVerse)
  ));
}

function loadNotes(book, chapter) {
  const list = document.querySelector("#notes-list");
  const count = document.querySelector("#notes-count");
  if (!list) {
    return;
  }
  return requestJson(`/api/notes/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`, {}, "Could not load notes.")
    .then((data) => {
      currentNotes = data.notes || [];
      if (notesView === "passage") {
        renderNotes(notesForCurrentPassage());
      }
      applyVerseStateIndicatorsToReader();
      if (count && notesView === "passage") {
        count.textContent = String(notesForCurrentPassage().length);
      }
    })
    .catch((error) => {
      list.innerHTML = errorHtml(error.message || "Could not load notes.");
    });
}

function loadAllNotes() {
  const list = document.querySelector("#notes-list");
  if (!list) {
    return Promise.resolve();
  }
  return requestJson("/api/notes", {}, "Could not load notes.")
    .then((data) => {
      allNotes = data.notes || [];
      if (notesView === "all") {
        renderNotes(allNotes);
      }
      return allNotes;
    })
    .catch((error) => {
      if (notesView === "all") {
        list.innerHTML = errorHtml(error.message || "Could not load notes.");
      }
      return [];
    });
}

function showNotesView(view) {
  notesView = view === "all" ? "all" : "passage";
  updateNotesViewControls();
  activateAppSection("notes");
  activateWorkspaceTab("notes");
  if (notesView === "all") {
    return loadAllNotes();
  }
  if (!currentChapter) {
    renderNotes([]);
    return Promise.resolve();
  }
  renderNotes(notesForCurrentPassage());
  return loadNotes(currentChapter.book, currentChapter.chapter);
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
  const reader = activeReaderPane?.() || document.querySelector("#chapter-reader");
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
      suppressHighlightedVerseTapUntil = 0;
      clearDocumentSelection();
      clearReaderSelection();
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
  const count = document.querySelector("#notes-count");
  if (count) {
    count.textContent = String(notes.length);
  }
  if (notes.length === 0) {
    list.innerHTML = `<p class="empty">${notesView === "all" ? "No notes yet. Capture your next thought with New note." : "No notes for this passage yet."}</p>`;
    return;
  }
  list.innerHTML = "";
  for (const note of notes) {
    const article = document.createElement("article");
    article.className = "note";
    article.dataset.noteId = note.id;

    const reference = document.createElement(hasNoteReference(note) ? "button" : "h3");
    if (hasNoteReference(note)) {
      reference.type = "button";
      reference.className = "note-reference-button";
      reference.addEventListener("click", () => openNoteReference(note));
    }
    reference.textContent = formatReference(note.book, note.chapter, note.start_verse, note.end_verse);

    const body = document.createElement("p");
    body.textContent = note.body;

    const meta = document.createElement("p");
    meta.className = "note-meta";
    meta.textContent = `Edited ${formatNoteTimestamp(note.updated_at || note.created_at)}`;

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
    article.appendChild(meta);
    article.appendChild(actions);
    list.appendChild(article);
  }
}

function formatNoteTimestamp(value) {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) {
    return "recently";
  }
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

async function openNoteReference(note) {
  if (!hasNoteReference(note)) {
    return;
  }
  await loadReaderChapter(note.book, note.chapter);
  if (note.start_verse) {
    scrollToVerse(Number(note.start_verse), "smooth");
  }
}

function openNoteEditor(existingNote) {
  activateAppSection("notes");
  activateWorkspaceTab("notes");
  const editor = document.querySelector("#note-editor");
  if (!editor) {
    return;
  }
  const note = existingNote && existingNote.id ? existingNote : null;
  if (note) {
    noteContext = {...note};
  } else if (currentSelection && currentChapter) {
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
    noteContext = {
      id: "",
      book: null,
      chapter: null,
      start_verse: null,
      end_verse: null,
      selected_text: "",
      body: "",
      canonical_object_ids: getCanonicalObjectIdsFromAnswerPanel(),
    };
  }

  noteDraftDirty = false;
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
  refreshNoteReferenceActions();
  setNoteSaveStatus(noteContext.id ? "Saved" : "New note");
  window.BHFStudyCompanion?.showPersonalResource?.("note", "Note");
  editor.elements.body.focus();
}

function refreshNoteReferenceActions() {
  const attach = document.querySelector("[data-attach-note-selection]");
  const clear = document.querySelector("[data-clear-note-reference]");
  if (attach) {
    attach.disabled = !(currentSelection && currentChapter);
  }
  if (clear) {
    clear.disabled = !hasNoteReference(noteContext);
  }
}

function updateNoteEditorReference() {
  const reference = document.querySelector("#note-reference");
  if (reference && noteContext) {
    reference.textContent = formatReference(
      noteContext.book,
      noteContext.chapter,
      noteContext.start_verse,
      noteContext.end_verse,
    );
  }
  refreshNoteReferenceActions();
}

function attachCurrentSelectionToNote() {
  if (!noteContext || !currentSelection || !currentChapter) {
    return;
  }
  noteContext = {
    ...noteContext,
    book: currentChapter.book,
    chapter: currentChapter.chapter,
    start_verse: currentSelection.startVerse,
    end_verse: currentSelection.endVerse,
    selected_text: currentSelection.text,
  };
  noteDraftDirty = true;
  updateNoteEditorReference();
  scheduleNoteAutoSave();
}

function clearNoteReference() {
  if (!noteContext) {
    return;
  }
  noteContext = {
    ...noteContext,
    book: null,
    chapter: null,
    start_verse: null,
    end_verse: null,
    selected_text: "",
  };
  noteDraftDirty = true;
  updateNoteEditorReference();
  scheduleNoteAutoSave();
}

function closeNoteEditor() {
  const body = document.querySelector("#note-editor [name='body']")?.value.trim();
  if (noteContext && body && noteDraftDirty) {
    void persistCurrentNote({close: true});
    return;
  }
  finishClosingNoteEditor();
}

function finishClosingNoteEditor() {
  window.clearTimeout(noteAutoSaveTimer);
  noteAutoSaveTimer = null;
  const editor = document.querySelector("#note-editor");
  if (editor) {
    editor.hidden = true;
    editor.reset();
  }
  noteContext = null;
  noteDraftDirty = false;
  noteCloseAfterSave = false;
}

function saveNote(event) {
  event.preventDefault();
  return persistCurrentNote({close: true});
}

function scheduleNoteAutoSave() {
  window.clearTimeout(noteAutoSaveTimer);
  if (!noteContext || !document.querySelector("#note-editor [name='body']")?.value.trim()) {
    return;
  }
  setNoteSaveStatus("Saving…");
  noteAutoSaveTimer = window.setTimeout(() => {
    void persistCurrentNote();
  }, 650);
}

function persistCurrentNote({close = false} = {}) {
  if (!noteContext) {
    return Promise.resolve();
  }
  if (noteAutoSaveInFlight) {
    noteCloseAfterSave = noteCloseAfterSave || close;
    return Promise.resolve();
  }
  const form = document.querySelector("#note-editor");
  if (!form) {
    return Promise.resolve();
  }
  const body = form.elements.body.value.trim();
  if (!body) {
    setNoteSaveStatus("Start typing to save");
    if (close) {
      finishClosingNoteEditor();
    }
    return Promise.resolve();
  }
  const payload = {
    ...noteContext,
    body,
    canonical_object_ids: canonicalObjectIdsFromInput(form.elements.canonical_object_ids?.value || ""),
  };
  const noteId = form.elements.id.value;
  const url = noteId ? `/api/notes/${encodeURIComponent(noteId)}` : "/api/notes";
  const method = noteId ? "PUT" : "POST";
  noteAutoSaveInFlight = true;
  setNoteSaveStatus("Saving…");
  return requestJson(url, {
    method,
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  }, "Could not save note.")
    .then((saved) => {
      noteContext = {...noteContext, ...saved};
      form.elements.id.value = noteContext.id || "";
      noteDraftDirty = false;
      setNoteSaveStatus("Saved");
      const reloads = [];
      if (currentChapter) {
        reloads.push(loadNotes(currentChapter.book, currentChapter.chapter));
      }
      if (notesView === "all") {
        reloads.push(loadAllNotes());
      }
      return Promise.all(reloads);
    })
    .then(() => {
      if (close || noteCloseAfterSave) {
        noteCloseAfterSave = false;
        finishClosingNoteEditor();
      }
    })
    .catch((error) => {
      setNoteSaveStatus(error.message || "Could not save note");
      throw error;
    })
    .finally(() => {
      noteAutoSaveInFlight = false;
      if (noteDraftDirty && !close) {
        scheduleNoteAutoSave();
      }
    });
}

function deleteExistingNote(noteId) {
  if (noteContext?.id === noteId) {
    finishClosingNoteEditor();
  }
  return requestJson(`/api/notes/${encodeURIComponent(noteId)}`, {
    method: "DELETE",
    headers: { "Accept": "application/json" }
  }, "Could not delete note.")
    .then(() => Promise.all([
      currentChapter ? loadNotes(currentChapter.book, currentChapter.chapter) : Promise.resolve(),
      notesView === "all" ? loadAllNotes() : Promise.resolve(),
    ]));
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

function requestSavedStudies(book, chapter) {
  if (!book || !chapter) {
    return Promise.resolve([]);
  }
  const key = savedStudyChapterKey({book, chapter});
  let request = savedStudiesRequests.get(key);
  if (!request) {
    request = requestJson(
      `/api/saved-studies?book=${encodeURIComponent(book)}&chapter=${encodeURIComponent(chapter)}`,
      {requireDeviceData: true},
      "Could not load saved studies.",
    )
      .then((data) => {
        if (!Array.isArray(data?.saved_studies)) {
          throw new Error("Could not load saved studies.");
        }
        const studies = data.saved_studies;
        savedStudiesCache.set(key, studies);
        document.dispatchEvent(new CustomEvent("bhf:saved-studies-changed", {
          detail: {book, chapter: Number(chapter), studies},
        }));
        return studies;
      })
      .finally(() => savedStudiesRequests.delete(key));
    savedStudiesRequests.set(key, request);
  }
  return request;
}

function loadSavedStudies(book, chapter, options = {}) {
  const list = document.querySelector("#saved-studies-list");
  const count = document.querySelector("#saved-studies-count");
  if (!book || !chapter) {
    return Promise.resolve([]);
  }
  const key = savedStudyChapterKey({book, chapter});
  return requestSavedStudies(book, chapter)
    .then((studies) => {
      const isCurrentChapter = savedStudyChapterKey(currentChapter) === key;
      if (list && isCurrentChapter) renderSavedStudies(studies);
      if (count) {
        if (isCurrentChapter) count.textContent = String(studies.length);
      }
      return studies;
    })
    .catch((error) => {
      if (list) list.innerHTML = errorHtml(error.message || "Could not load saved studies.");
      if (options.propagateError) throw error;
      return [];
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

async function savePersonalStudyNotes(button) {
  const studyId = button?.dataset.savedStudyId;
  const notesField = button?.closest(".answer-panel, .answer")?.querySelector("[data-personal-notes]")
    || document.querySelector("[data-personal-notes]");
  if (!studyId || !notesField || !window.BHFOfflineDB) {
    return;
  }
  const study = await window.BHFOfflineDB.get("savedStudies", studyId);
  if (!study) {
    window.alert("This saved study is not available on this device.");
    return;
  }
  button.disabled = true;
  button.textContent = "Saving notes...";
  try {
    await window.BHFOfflineDB.upsertOfflineSavedStudy({
      ...study,
      personal_notes: notesField.value,
      updated_at: new Date().toISOString(),
    });
    button.textContent = "Notes saved";
    if (currentChapter) {
      await loadSavedStudies(currentChapter.book, currentChapter.chapter);
    }
  } finally {
    button.disabled = false;
  }
}

function saveLatestStudy(event) {
  const sourceButton = event?.currentTarget || null;
  const answerPanel = sourceButton?.closest(".ask-form")
    ? document.querySelector("#answer-panel")
    : activeLiveAnswerPanel || document.querySelector("[data-device-study]");
  const studyNode = answerPanel?.matches?.("[data-device-study]")
    ? answerPanel
    : answerPanel?.querySelector?.("[data-device-study]") || document.querySelector("[data-device-study]");
  const encodedStudy = studyNode?.dataset.deviceStudy || "";
  let studyPayload = null;
  try {
    studyPayload = encodedStudy ? JSON.parse(encodedStudy) : null;
  } catch (_error) {
    studyPayload = null;
  }
  if (!studyPayload) {
    window.alert("Run a study first, then save it.");
    return Promise.resolve();
  }
  const notesField = studyNode?.querySelector?.("[data-personal-notes]");
  studyPayload.personal_notes = notesField?.value || "";
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
    body: JSON.stringify(studyPayload)
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
  wireSaveStudyButtons(answerPanel);
  wireCanonicalAnswerPanelControls(answerPanel);
  answerPanel.querySelectorAll("[data-save-personal-notes]").forEach((button) => {
    if (!button.dataset.personalNotesBound) {
      button.addEventListener("click", () => savePersonalStudyNotes(button));
      button.dataset.personalNotesBound = "true";
    }
  });
  updateSaveButtons();
}

function wireSaveStudyButtons(root = document) {
  root.querySelectorAll("[data-save-study]").forEach((button) => {
    if (!button.dataset.saveBound) {
      button.addEventListener("click", saveLatestStudy);
      button.dataset.saveBound = "true";
    }
  });
}

function updateSaveButtons() {
  document.querySelectorAll("[data-save-study]").forEach((button) => {
    const panel = button.closest(".answer-panel");
    const isAskFormButton = Boolean(button.closest(".ask-form"));
    const isGeneralQuestion = button.closest(".ask-form")?.dataset.questionScope === "general_question";
    const isActive = isAskFormButton
      ? activeLiveAnswerPanel?.id === "answer-panel"
      : Boolean(activeLiveAnswerPanel) && panel === activeLiveAnswerPanel;
    button.disabled = isGeneralQuestion || !(isActive && (button.dataset.jobId || (latestJobId && latestJobComplete)));
  });
}

function formatReference(book, chapter, startVerse, endVerse) {
  if (!book || !chapter) {
    return "Standalone note";
  }
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

  const detailAddNoteButton = document.querySelector("[data-canonical-detail-add-note]");
  if (detailAddNoteButton && !detailAddNoteButton.dataset.bound) {
    detailAddNoteButton.dataset.bound = "true";
    detailAddNoteButton.addEventListener("click", () => {
      appendCanonicalObjectToCurrentNote(detailAddNoteButton.dataset.canonicalLinkNote || currentCanonicalBrowser.selectedObjectId || "");
    });
  }

  const backToResultsButton = document.querySelector("[data-canonical-browser-back]");
  if (backToResultsButton && !backToResultsButton.dataset.bound) {
    backToResultsButton.dataset.bound = "true";
    backToResultsButton.addEventListener("click", handleCanonicalBrowserBack);
  }

  const detailModal = document.querySelector("#canonical-context-modal");
  const closeModalButton = document.querySelector("[data-canonical-context-modal-close]");
  if (closeModalButton && !closeModalButton.dataset.bound) {
    closeModalButton.dataset.bound = "true";
    closeModalButton.addEventListener("click", () => closeCanonicalContextModal());
  }
  if (detailModal && !detailModal.dataset.bound) {
    detailModal.dataset.bound = "true";
    detailModal.addEventListener("cancel", () => {
      window.setTimeout(() => restoreCanonicalContextTrigger(), 0);
    });
    detailModal.addEventListener("click", (event) => {
      if (event.target === detailModal) {
        closeCanonicalContextModal();
      }
    });
  }

  const requestedObjectId = normalizeCanonicalObjectId(
    new URLSearchParams(window.location.search).get("canonical") || ""
  );
  if (requestedObjectId) {
    window.setTimeout(() => {
      activateWorkspaceTab("context");
      loadCanonicalObject(requestedObjectId, { openModal: true }).catch(() => {});
    }, 0);
  }

}

function handleCanonicalBrowserSubmit(event) {
  event.preventDefault();
  const form = document.querySelector("[data-canonical-browser-form]");
  const query = String((form ? new FormData(form) : new FormData()).get("q") || "").trim();
  if (!query) {
    clearCanonicalBrowserResults("Enter a search term to see canonical objects.");
    return;
  }
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
  clearCanonicalBrowserResults();
}

function handleCanonicalBrowserBack(event) {
  event.preventDefault();
  closeCanonicalContextModal({returnFocus: false});
  const resultsList = document.querySelector("[data-canonical-browser-results]");
  if (!resultsList) {
    return;
  }
  const selectedId = normalizeCanonicalObjectId(currentCanonicalBrowser.selectedObjectId || "");
  const selected = Array.from(resultsList.querySelectorAll("[data-canonical-object-id]")).find(
    (item) => normalizeCanonicalObjectId(item.dataset.canonicalObjectId || "") === selectedId,
  ) || resultsList.querySelector("[data-canonical-object-id]");
  selected?.scrollIntoView({behavior: "smooth", block: "nearest"});
  selected?.focus({preventScroll: true});
}

async function loadCanonicalBrowser(options = {}) {
  const form = document.querySelector("[data-canonical-browser-form]");
  const resultsList = document.querySelector("[data-canonical-browser-results]");
  const summary = document.querySelector("[data-canonical-browser-summary]");
  const count = document.querySelector("[data-canonical-browser-count]");
  const backToResultsButton = document.querySelector("[data-canonical-browser-back]");
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
    : form
      ? formData.has("include_placeholders")
      : true;

  if (!query) {
    clearCanonicalBrowserResults("Enter a search term to see canonical objects.");
    return;
  }

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
    summary.textContent = `Searching for "${query}"...`;
  }

  const data = await requestJson(url, {}, "Could not load canonical objects.");
  currentCanonicalBrowser.query = query;
  currentCanonicalBrowser.results = Array.isArray(data.results) ? data.results : [];

  const hasActiveFilters = canonicalBrowserHasActiveFilters(objectType, reviewStatus, contentStatus, includePlaceholders);
  renderCanonicalBrowserResults(currentCanonicalBrowser.results, { query, hasActiveFilters });
  if (count) {
    count.textContent = String(currentCanonicalBrowser.results.length);
  }

  if (summary) {
    if (currentCanonicalBrowser.results.length === 0) {
      summary.textContent = `No canonical objects matched "${query}".`;
    } else {
      const retrievalMethod = String(data.metadata?.retrieval_method || data.filters?.type || "browse");
      summary.textContent = `Found ${currentCanonicalBrowser.results.length} canonical object${currentCanonicalBrowser.results.length === 1 ? "" : "s"} using ${retrievalMethod}.`;
    }
  }

  if (currentCanonicalBrowser.results.length > 0) {
    const selectedId = options.selectObjectId || currentCanonicalBrowser.selectedObjectId || currentCanonicalBrowser.results[0].id;
    const selected = currentCanonicalBrowser.results.find((item) => item.id === selectedId) || currentCanonicalBrowser.results[0];
    if (selected) {
      await loadCanonicalObject(selected.id, { preview: selected });
    }
  } else {
    currentCanonicalBrowser.selectedObjectId = null;
    renderCanonicalBrowserDetail(null);
  }
  if (backToResultsButton) {
    backToResultsButton.hidden = currentCanonicalBrowser.results.length === 0;
  }
}

function clearCanonicalBrowserResults(message = "Search the canonical library to see results.") {
  const resultsList = document.querySelector("[data-canonical-browser-results]");
  const summary = document.querySelector("[data-canonical-browser-summary]");
  const count = document.querySelector("[data-canonical-browser-count]");
  const backToResultsButton = document.querySelector("[data-canonical-browser-back]");
  currentCanonicalBrowser.query = "";
  currentCanonicalBrowser.results = [];
  currentCanonicalBrowser.selectedObjectId = null;
  if (summary) {
    summary.textContent = message;
  }
  if (count) {
    count.textContent = "0";
  }
  if (backToResultsButton) {
    backToResultsButton.hidden = true;
  }
  if (resultsList) {
    resultsList.innerHTML = `<p class="empty">${escapeHtml(message)}</p>`;
  }
  renderCanonicalBrowserDetail(null);
}

function renderCanonicalBrowserResults(results, options = {}) {
  const list = document.querySelector("[data-canonical-browser-results]");
  if (!list) {
    return;
  }
  if (!Array.isArray(results) || results.length === 0) {
    if (options.query) {
      list.innerHTML = `<div class="canonical-browser-empty"><h4>No search results</h4><p class="empty">No CKL objects matched "${escapeHtml(options.query)}". Try a different term, passage, or object ID.</p></div>`;
    } else if (options.hasActiveFilters) {
      list.innerHTML = `<div class="canonical-browser-empty"><h4>No filter matches</h4><p class="empty">No objects match the active filters. Clear filters or broaden the selected states.</p></div>`;
    } else {
      list.innerHTML = `<div class="canonical-browser-empty"><h4>No objects available</h4><p class="empty">The canonical library did not return any browseable objects.</p></div>`;
    }
    return;
  }

  list.innerHTML = "";
  for (const item of results) {
    const article = document.createElement("article");
    article.className = "canonical-result-card";
    article.dataset.canonicalObjectId = item.id;
    article.tabIndex = 0;
    article.setAttribute("role", "button");
    article.setAttribute("aria-label", `View ${item.title || item.id || "canonical object"}`);
    if (currentCanonicalBrowser.selectedObjectId && currentCanonicalBrowser.selectedObjectId === normalizeCanonicalObjectId(item.id)) {
      article.classList.add("is-selected");
      article.setAttribute("aria-current", "true");
    }
    article.addEventListener("click", (event) => {
      if (event.target.closest("button, a, input, select, textarea, summary, details")) {
        return;
      }
      loadCanonicalObject(item.id, { preview: item, openModal: true, trigger: article }).catch(() => {});
    });
    article.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }
      event.preventDefault();
      loadCanonicalObject(item.id, { preview: item, openModal: true, trigger: article }).catch(() => {});
    });

    const header = document.createElement("div");
    header.className = "canonical-result-header";

    const titleWrap = document.createElement("div");
    titleWrap.className = "canonical-result-title-wrap";

    const titleButton = document.createElement("button");
    titleButton.type = "button";
    titleButton.className = "canonical-result-title";
    titleButton.textContent = item.title || item.id;
    titleButton.addEventListener("click", (event) => {
      event.stopPropagation();
      loadCanonicalObject(item.id, { preview: item, openModal: true, trigger: titleButton }).catch(() => {});
    });

    const summary = document.createElement("p");
    summary.className = "canonical-result-summary";
    summary.textContent = item.summary || "No summary recorded.";

    const meta = document.createElement("p");
    meta.className = "canonical-result-meta";
    meta.textContent = canonicalResultMetadata(item).join(" · ");

    const status = document.createElement("span");
    status.className = "canonical-status-chip";
    status.textContent = formatCanonicalLabel(item.review_status || "unknown");

    titleWrap.appendChild(titleButton);
    titleWrap.appendChild(meta);
    titleWrap.appendChild(summary);

    header.appendChild(titleWrap);
    header.appendChild(status);

    const reason = document.createElement("p");
    reason.className = "canonical-result-reason";
    const showReason = item.reason && item.match_type && item.match_type !== "browse";
    reason.textContent = showReason ? item.reason : "";

    const actions = document.createElement("div");
    actions.className = "canonical-result-actions";
    const viewButton = document.createElement("button");
    viewButton.type = "button";
    viewButton.className = "secondary";
    viewButton.textContent = "Open";
    viewButton.dataset.testid = "canonical-result-view-button";
    viewButton.addEventListener("click", (event) => {
      event.stopPropagation();
      loadCanonicalObject(item.id, { preview: item, openModal: true, trigger: viewButton }).catch(() => {});
    });

    const linkButton = document.createElement("button");
    linkButton.type = "button";
    linkButton.className = "secondary";
    linkButton.textContent = "Link to note";
    linkButton.dataset.testid = "canonical-result-link-note";
    linkButton.addEventListener("click", (event) => {
      event.stopPropagation();
      appendCanonicalObjectToCurrentNote(item.id);
    });

    actions.appendChild(viewButton);
    actions.appendChild(linkButton);

    article.appendChild(header);
    if (reason.textContent) {
      article.appendChild(reason);
    }
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
  if (options.openModal) {
    openCanonicalContextModal(options.trigger);
  }
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

function openCanonicalContextModal(trigger) {
  const modal = document.querySelector("#canonical-context-modal");
  if (!modal || typeof modal.showModal !== "function") {
    return;
  }
  if (trigger instanceof HTMLElement) {
    modal._canonicalContextTrigger = trigger;
  }
  if (!modal.open) {
    modal.showModal();
  }
}

function restoreCanonicalContextTrigger() {
  const modal = document.querySelector("#canonical-context-modal");
  const trigger = modal?._canonicalContextTrigger;
  if (modal) {
    modal._canonicalContextTrigger = null;
  }
  if (trigger && trigger.isConnected) {
    trigger.focus({preventScroll: true});
  }
}

function closeCanonicalContextModal(options = {}) {
  const modal = document.querySelector("#canonical-context-modal");
  if (!modal?.open) {
    return;
  }
  modal.close();
  if (options.returnFocus !== false) {
    restoreCanonicalContextTrigger();
  }
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
  const sourceCount = document.querySelector("[data-canonical-detail-source-count]");
  const notes = document.querySelector("[data-canonical-detail-notes]");
  const editor = document.querySelector("[data-canonical-detail-editor]");
  const curation = document.querySelector("[data-canonical-detail-curation]");
  const addNote = document.querySelector("[data-canonical-detail-add-note]");
  const backToResultsButton = document.querySelector("[data-canonical-browser-back]");
  if (!title || !summary || !status || !badges || !reason || !scripture || !related || !sources) {
    return;
  }

  badges.innerHTML = "";
  scripture.innerHTML = "";
  related.innerHTML = "";
  sources.innerHTML = "";
  if (notes) {
    notes.innerHTML = "";
  }
  if (sourceCount) {
    sourceCount.textContent = "";
  }
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
    badges.innerHTML = `<p class="empty">Select a CKL object to inspect its metadata.</p>`;
    scripture.innerHTML = `<p class="empty">No object selected.</p>`;
    sources.innerHTML = `<p class="empty">No object selected.</p>`;
    related.innerHTML = `<p class="empty">No object selected.</p>`;
    if (notes) {
      notes.innerHTML = `<p class="empty">No object selected.</p>`;
    }
    if (curation) {
      curation.href = "/curation";
    }
    if (editor) {
      editor.hidden = true;
      editor.href = "/canonical/editor";
    }
    if (addNote) {
      addNote.disabled = true;
      delete addNote.dataset.canonicalLinkNote;
    }
    if (backToResultsButton) {
      backToResultsButton.hidden = true;
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
    addNote.dataset.canonicalLinkNote = normalizedId;
  }
  if (backToResultsButton) {
    backToResultsButton.hidden = false;
  }

  appendCanonicalMetadata(badges, "Object type", formatCanonicalLabel(object.type || "unknown"));
  appendCanonicalMetadata(badges, "Content state", formatCanonicalLabel(object.content_status || "unknown"));
  appendCanonicalMetadata(badges, "Review state", formatCanonicalLabel(object.review_status || "unknown"));
  appendCanonicalMetadata(badges, "Confidence", formatCanonicalLabel(object.confidence || "unrated"));
  appendCanonicalMetadata(badges, "Importance", object.importance ?? 0);
  if (object.source_count !== undefined) {
    appendCanonicalMetadata(badges, "Sources", `${object.source_count} source${Number(object.source_count) === 1 ? "" : "s"}`);
  }
  appendCanonicalMetadata(badges, "Canonical ID", normalizedId);
  if (object.updated_at || object.last_updated) {
    appendCanonicalMetadata(badges, "Last updated", object.updated_at || object.last_updated);
  }

  const reasonText = object.reason || object.match_type || "";
  if (reasonText) {
    reason.hidden = false;
    reason.textContent = reasonText;
  }

  if (Array.isArray(object.scripture_references) && object.scripture_references.length > 0) {
    renderCanonicalScriptureReferences(scripture, object.scripture_references);
  } else {
    scripture.innerHTML = `<p class="empty">No Scripture references recorded.</p>`;
  }

  const relatedObjects = Array.isArray(object.related_object_links) && object.related_object_links.length > 0
    ? object.related_object_links
    : Array.isArray(object.related_objects)
      ? object.related_objects
      : [];
  if (relatedObjects.length > 0) {
    renderCanonicalRelationships(related, relatedObjects);
  } else {
    related.innerHTML = `<p class="empty">No related objects recorded.</p>`;
  }
  const archaeologyLinks = Array.isArray(object.related_archaeology) ? object.related_archaeology : [];
  if (archaeologyLinks.length > 0) {
    const archaeologySection = document.createElement("section");
    archaeologySection.className = "canonical-related-archaeology";
    archaeologySection.innerHTML = `<h5>Related Archaeological Evidence</h5>`;
    archaeologyLinks.forEach((item) => {
      const link = document.createElement("a");
      link.href = `/archaeology?q=${encodeURIComponent(item.title || item.id || "")}`;
      link.textContent = item.title || item.id;
      link.className = "canonical-related-archaeology-link";
      archaeologySection.appendChild(link);
    });
    related.appendChild(archaeologySection);
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
    if (sourceCount) {
      sourceCount.textContent = `${object.sources.length} source${object.sources.length === 1 ? "" : "s"}`;
    }
  } else {
    sources.innerHTML = `<p class="empty">No sources recorded.</p>`;
    if (sourceCount) {
      sourceCount.textContent = "0 sources";
    }
  }

  if (notes) {
    renderCanonicalLinkedNotes(notes, normalizedId);
  }

  if (options.error && reason) {
    reason.hidden = false;
    reason.textContent = options.error;
  }

  renderCanonicalBrowserResults(currentCanonicalBrowser.results);
}

function canonicalBrowserHasActiveFilters(type, reviewStatus, contentStatus, includePlaceholders) {
  return Boolean(
    (type && type !== "all")
    || (reviewStatus && reviewStatus !== "all")
    || (contentStatus && contentStatus !== "all")
    || includePlaceholders === false
  );
}

function canonicalResultMetadata(item) {
  const parts = [
    formatCanonicalLabel(item.type || "unknown"),
    `Importance ${item.importance ?? 0}`,
  ];
  if (item.source_count !== undefined) {
    parts.push(`${item.source_count} source${Number(item.source_count) === 1 ? "" : "s"}`);
  }
  if (item.content_status && item.content_status !== "complete") {
    parts.push(formatCanonicalLabel(item.content_status));
  }
  return parts;
}

function appendCanonicalMetadata(container, label, value) {
  if (!container || value === null || value === undefined || String(value).trim() === "") {
    return;
  }
  const item = document.createElement("div");
  item.className = "canonical-metadata-item";

  const term = document.createElement("dt");
  term.textContent = label;

  const description = document.createElement("dd");
  description.textContent = String(value);

  item.appendChild(term);
  item.appendChild(description);
  container.appendChild(item);
}

function renderCanonicalScriptureReferences(container, references) {
  const groups = new Map();
  for (const ref of references) {
    const relationship = String(ref.relationship || "other").trim().toLowerCase() || "other";
    if (!groups.has(relationship)) {
      groups.set(relationship, []);
    }
    groups.get(relationship).push(ref);
  }

  const orderedKeys = [
    ...["primary", "primary passage", "main"].filter((key) => groups.has(key)),
    ...["supporting", "support", "secondary"].filter((key) => groups.has(key)),
    ...Array.from(groups.keys()).filter((key) => !["primary", "primary passage", "main", "supporting", "support", "secondary"].includes(key)),
  ];

  for (const key of orderedKeys) {
    const groupReferences = groups.get(key) || [];
    const section = document.createElement("section");
    section.className = "canonical-reference-group";

    const heading = document.createElement("h5");
    heading.textContent = canonicalScriptureGroupLabel(key, groupReferences.length);
    section.appendChild(heading);

    const list = document.createElement("div");
    list.className = "canonical-reference-list";
    for (const ref of groupReferences) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "scripture-link canonical-detail-item";
      button.dataset.bibleReference = ref.reference || "";
      button.addEventListener("click", () => openScriptureReference(ref.reference));

      const reference = document.createElement("span");
      reference.className = "canonical-reference-text";
      reference.textContent = ref.reference || "Scripture reference";
      button.appendChild(reference);

      if (ref.notes) {
        const note = document.createElement("span");
        note.className = "scripture-link-note";
        note.textContent = ref.notes;
        button.appendChild(note);
      }
      list.appendChild(button);
    }

    section.appendChild(list);
    container.appendChild(section);
  }
}

function canonicalScriptureGroupLabel(key, count) {
  if (["primary", "primary passage", "main"].includes(key)) {
    return count === 1 ? "Primary passage" : "Primary passages";
  }
  if (["supporting", "support", "secondary"].includes(key)) {
    return "Supporting passages";
  }
  return formatCanonicalLabel(key);
}

function renderCanonicalRelationships(container, relationships) {
  const groups = new Map();
  for (const relation of relationships) {
    const relationship = String(relation.relationship || "related").trim() || "related";
    if (!groups.has(relationship)) {
      groups.set(relationship, []);
    }
    groups.get(relationship).push(relation);
  }

  for (const [relationship, items] of groups.entries()) {
    const section = document.createElement("section");
    section.className = "canonical-relationship-group";

    const heading = document.createElement("h5");
    heading.textContent = formatCanonicalLabel(relationship);
    section.appendChild(heading);

    const list = document.createElement("div");
    list.className = "canonical-relationship-list";
    for (const relation of items) {
      const objectId = relation.id || relation.object_id || "";
      const wrapper = document.createElement("div");
      wrapper.className = "canonical-detail-item canonical-related-row";

      const button = document.createElement("button");
      button.type = "button";
      button.className = "canonical-related-object";
      button.textContent = relation.title || objectId || "Related object";
      button.addEventListener("click", () => loadCanonicalObject(objectId || relation.id || "").catch(() => {}));
      wrapper.appendChild(button);

      const metaParts = [
        relation.type ? formatCanonicalLabel(relation.type) : "",
        relation.review_status ? formatCanonicalLabel(relation.review_status) : "",
        relation.weight ? `Weight ${relation.weight}` : "",
      ].filter(Boolean);
      if (metaParts.length > 0) {
        const meta = document.createElement("p");
        meta.className = "canonical-detail-meta";
        meta.textContent = metaParts.join(" · ");
        wrapper.appendChild(meta);
      }

      if (relation.notes || relation.summary) {
        const note = document.createElement("p");
        note.className = "canonical-detail-notes";
        note.textContent = relation.notes || relation.summary;
        wrapper.appendChild(note);
      }
      list.appendChild(wrapper);
    }

    section.appendChild(list);
    container.appendChild(section);
  }
}

function renderCanonicalLinkedNotes(container, objectId) {
  const linkedNotes = typeof currentNotes !== "undefined" && Array.isArray(currentNotes)
    ? currentNotes.filter((note) => canonicalObjectIdsFromInput(note.canonical_object_ids || []).includes(objectId))
    : [];
  if (linkedNotes.length === 0) {
    container.innerHTML = `<p class="empty">No notes linked to this object yet.</p>`;
    return;
  }
  for (const note of linkedNotes) {
    const article = document.createElement("article");
    article.className = "canonical-linked-note";

    const reference = document.createElement("h5");
    reference.textContent = formatReference(note.book, note.chapter, note.start_verse, note.end_verse);
    article.appendChild(reference);

    const body = document.createElement("p");
    body.textContent = note.body || "Linked note";
    article.appendChild(body);

    container.appendChild(article);
  }
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
    loadCanonicalObject(objectId, {
      preview: canonicalButton.dataset.canonicalObjectTitle ? { id: objectId, title: canonicalButton.dataset.canonicalObjectTitle } : null,
      openModal: true,
      trigger: canonicalButton,
    }).catch(() => {});
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
  if (!currentSelection) {
    const selectedVerse = document.querySelector("#chapter-reader [data-verse].selected");
    if (selectedVerse) {
      applySelectionContext(contextFromVerse(selectedVerse));
    }
  }
  const noteEditor = document.querySelector("#note-editor");
  if (!noteEditor || noteEditor.hidden) {
    if (!currentSelection) {
      const verse = document.querySelector("#chapter-reader [data-verse].selected")
        || document.querySelector("#chapter-reader [data-verse]");
      if (verse) {
        applySelectionContext(contextFromVerse(verse));
      }
    }
    openNoteEditor();
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
      loadCanonicalObject(objectId, { openModal: true, trigger: button }).catch(() => {});
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
