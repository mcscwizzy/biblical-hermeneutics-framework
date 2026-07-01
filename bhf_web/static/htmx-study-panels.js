function loadNotes(book, chapter) {
  const list = document.querySelector("#notes-list");
  const count = document.querySelector("#notes-count");
  if (!list) {
    return;
  }
  return requestJson(`/api/notes/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`, {}, "Could not load notes.")
    .then((data) => {
      renderNotes(data.notes || []);
      if (count) {
        count.textContent = String((data.notes || []).length);
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
    verse.classList.remove("highlight-yellow", "highlight-green", "highlight-blue", "highlight-pink");
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
      body: ""
    };
  } else {
    return;
  }

  editor.hidden = false;
  editor.elements.id.value = noteContext.id || "";
  editor.elements.body.value = noteContext.body || "";
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
    body: form.elements.body.value
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

function saveLatestStudy() {
  if (!latestJobId || !latestJobComplete) {
    window.alert("Run a study first, then save it.");
    return Promise.resolve();
  }
  const saveButton = activeLiveAnswerPanel?.querySelector("[data-save-study]") || null;
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
      job_id: latestJobId
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
  const button = answerPanel.querySelector("[data-save-study]");
  if (!button) {
    return;
  }
  if (!button.dataset.saveBound) {
    button.addEventListener("click", saveLatestStudy);
    button.dataset.saveBound = "true";
  }
  updateSaveButtons();
}

function updateSaveButtons() {
  document.querySelectorAll("[data-save-study]").forEach((button) => {
    const panel = button.closest(".answer-panel");
    const isActive = Boolean(activeLiveAnswerPanel) && panel === activeLiveAnswerPanel;
    button.disabled = !(latestJobId && latestJobComplete && isActive);
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
