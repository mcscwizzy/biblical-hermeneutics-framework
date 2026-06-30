// This file stays intentionally monolithic for now.
// It is the central client-side controller for reader, notes, highlights,
// map fallback, and search interactions, and the shared request helpers and
// status helpers have already been split into separate scripts.
const POLL_INTERVAL_MS = 750;
const READER_LONG_PRESS_DELAY_MS = 550;
const READER_LONG_PRESS_MOVE_THRESHOLD_PX = 14;
const BHF_STUDY_ACTIONS = new Set([
  "ancient_context",
  "literary_context",
  "cross_references",
  "related_ot_themes",
  "fulfillment_nt",
  "compare_translations",
  "timeline",
  "word_study",
  "ask_location",
  "compare_archaeology",
  "related_passages",
]);

let latestJobId = null;
let latestJobComplete = false;
let currentChapter = null;
let currentSelection = null;
let noteContext = null;
let currentHighlights = [];
let contextMenuState = null;
let lastMapAIFallbackKey = null;
let activeLiveAnswerPanel = null;
let readerLongPressState = null;
let latestBibleSearchRequestId = 0;
const BHF_HTTP = window.BHFApi || {};

document.addEventListener("DOMContentLoaded", function () {
  initializeWorkspaceTabs();
  initializeReader();
  initializeWorkspaceBridge();
});

document.addEventListener("submit", async function (event) {
  const form = event.target;
  if (!form.matches("[data-job-post]")) {
    return;
  }

  event.preventDefault();

  const targets = resolveSubmitTargets(form);
  const answerPanel = targets.answerPanel;
  const statusPanel = targets.statusPanel;
  const submitButton = form.querySelector("button[type='submit']");
  if (!answerPanel || !statusPanel) {
    form.submit();
    return;
  }

  activeLiveAnswerPanel = answerPanel;
  updateSaveButtons();
  setRunning(form, submitButton, true);
  resetStatus(statusPanel);
  startWaiting(statusPanel);
  answerPanel.innerHTML = "";
  answerPanel.setAttribute("aria-busy", "true");

  try {
    const job = await requestJson(form.dataset.jobPost, {
      method: "POST",
      body: new FormData(form),
      headers: { "Accept": "application/json" }
    }, "Could not start request.");
    if (!job.job_id) {
      throw new Error("Could not start request.");
    }
    latestJobId = job.job_id;
    latestJobComplete = false;

    const finalStatus = await pollJob(form, statusPanel, job.job_id);
    const result = await requestText(form.dataset.resultBase + finalStatus.job_id, {}, "Could not render result.");
    answerPanel.innerHTML = result;

    if (finalStatus.error) {
      markStatusFailed(statusPanel, finalStatus.error || "Request failed.");
      latestJobComplete = false;
    } else {
      markStatusComplete(statusPanel, finalStatus);
      latestJobComplete = true;
      wireAnswerPanelControls(answerPanel);
      await loadSavedStudies(currentChapter?.book, currentChapter?.chapter);
    }
  } catch (error) {
    markStatusFailed(statusPanel, error.message || "Request failed.");
    answerPanel.innerHTML = errorHtml(error.message || "Request failed.");
    latestJobComplete = false;
  } finally {
    stopWaiting();
    answerPanel.removeAttribute("aria-busy");
    resetSubmitTargets(form);
    setFormValue("ask_mode", "");
    setFormValue("study_action", "");
    setRunning(form, submitButton, false);
  }
});

async function initializeReader() {
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  const reader = document.querySelector("#chapter-reader");
  const askForm = document.querySelector(".ask-form");
  if (!bookSelect || !chapterSelect || !reader || !askForm) {
    return;
  }

  populateChapterOptions(bookSelect, chapterSelect);
  chapterSelect.value = reader.dataset.defaultChapter || "1";
  await loadReaderChapter(bookSelect.value, chapterSelect.value);

  bookSelect.addEventListener("change", async () => {
    populateChapterOptions(bookSelect, chapterSelect);
    chapterSelect.value = "1";
    await loadReaderChapter(bookSelect.value, chapterSelect.value);
  });
  chapterSelect.addEventListener("change", async () => {
    await loadReaderChapter(bookSelect.value, chapterSelect.value);
  });
  document.addEventListener("selectionchange", updateSelectionFromDocument);
  document.addEventListener("click", closeContextMenuOnOutside);
  document.addEventListener("keydown", closeContextMenuOnEscape);
  window.addEventListener("scroll", hideContextMenu, true);
  reader.addEventListener("contextmenu", handleReaderContextMenu);
  reader.addEventListener("pointerdown", handleReaderPointerDown);
  reader.addEventListener("pointermove", handleReaderPointerMove);
  reader.addEventListener("pointerup", cancelReaderLongPress);
  reader.addEventListener("pointercancel", cancelReaderLongPress);
  reader.addEventListener("pointerleave", handleReaderPointerLeave);
  const contextMenu = document.querySelector("#reader-context-menu");
  const searchForm = document.querySelector("[data-bible-search]");
  const searchResultsBody = document.querySelector("#reader-search-results-body");
  if (contextMenu) {
    contextMenu.addEventListener("click", handleContextMenuAction);
  }
  if (searchForm) {
    searchForm.addEventListener("submit", submitBibleSearch);
    const clearButton = searchForm.querySelector("[data-search-clear]");
    if (clearButton) {
      clearButton.addEventListener("click", clearBibleSearchResults);
    }
  }
  if (searchResultsBody) {
    searchResultsBody.addEventListener("click", handleBibleSearchResultAction);
  }
  const addNoteButton = document.querySelector("[data-add-note]");
  if (addNoteButton) {
    addNoteButton.addEventListener("click", openNoteEditor);
    addNoteButton.disabled = true;
  }
  const noteEditor = document.querySelector("#note-editor");
  if (noteEditor) {
    noteEditor.addEventListener("submit", saveNote);
  }
  const cancelNote = document.querySelector("[data-cancel-note]");
  if (cancelNote) {
    cancelNote.addEventListener("click", closeNoteEditor);
  }
  document.addEventListener("bhf:map-panel-opened", () => activateWorkspaceTab("maps"));
  document.addEventListener("bhf:map-panel-closed", syncMapWorkspaceEmptyState);
  wireAnswerPanelControls(document.querySelector("#answer-panel"));
  wireAnswerPanelControls(document.querySelector("#map-ai-answer-panel"));
  syncMapWorkspaceEmptyState();
}

function initializeWorkspaceTabs() {
  const workspace = document.querySelector("[data-workspace-tabs]");
  if (!workspace) {
    return;
  }
  const tabs = Array.from(workspace.querySelectorAll("[data-workspace-tab]"));
  const defaultTab = workspace.dataset.defaultTab || "ask";
  for (const tab of tabs) {
    tab.addEventListener("click", () => activateWorkspaceTab(tab.dataset.workspaceTab));
    tab.addEventListener("keydown", (event) => handleWorkspaceTabKeydown(event, tabs));
  }
  activateWorkspaceTab(defaultTab);
}

function initializeWorkspaceBridge() {
  if (typeof window === "undefined") {
    return;
  }
  window.BHFWorkspace = {
    requestMapAIFallback,
  };
}

function resolveSubmitTargets(form) {
  const answerSelector = form.dataset.activeTarget || form.dataset.target;
  const statusSelector = form.dataset.activeStatusTarget || form.dataset.statusTarget;
  return {
    answerPanel: answerSelector ? document.querySelector(answerSelector) : null,
    statusPanel: statusSelector ? document.querySelector(statusSelector) : null,
  };
}

function resetSubmitTargets(form) {
  delete form.dataset.activeTarget;
  delete form.dataset.activeStatusTarget;
}

function requestJson(url, options = {}, fallbackMessage = "Request failed.") {
  if (typeof BHF_HTTP.requestJson === "function") {
    return BHF_HTTP.requestJson(url, options, fallbackMessage);
  }
  return fetch(url, options).then(async (response) => {
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || fallbackMessage);
    }
    return data;
  });
}

function requestText(url, options = {}, fallbackMessage = "Request failed.") {
  if (typeof BHF_HTTP.requestText === "function") {
    return BHF_HTTP.requestText(url, options, fallbackMessage);
  }
  return fetch(url, options).then(async (response) => {
    const data = await response.text();
    if (!response.ok) {
      throw new Error(data || fallbackMessage);
    }
    return data;
  });
}

function handleWorkspaceTabKeydown(event, tabs) {
  const currentIndex = tabs.indexOf(event.currentTarget);
  if (currentIndex === -1) {
    return;
  }

  let nextIndex = null;
  if (event.key === "ArrowRight") {
    nextIndex = (currentIndex + 1) % tabs.length;
  } else if (event.key === "ArrowLeft") {
    nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
  } else if (event.key === "Home") {
    nextIndex = 0;
  } else if (event.key === "End") {
    nextIndex = tabs.length - 1;
  }

  if (nextIndex === null) {
    return;
  }

  event.preventDefault();
  const nextTab = tabs[nextIndex];
  if (!nextTab) {
    return;
  }
  activateWorkspaceTab(nextTab.dataset.workspaceTab);
  nextTab.focus();
}

function activateWorkspaceTab(tabId) {
  const workspace = document.querySelector("[data-workspace-tabs]");
  if (!workspace || !tabId) {
    return;
  }
  workspace.querySelectorAll("[data-workspace-tab]").forEach((tab) => {
    const isActive = tab.dataset.workspaceTab === tabId;
    tab.setAttribute("aria-selected", String(isActive));
    tab.tabIndex = isActive ? 0 : -1;
  });
  workspace.querySelectorAll("[data-workspace-pane]").forEach((pane) => {
    pane.hidden = pane.dataset.workspacePane !== tabId;
  });
}

function syncMapWorkspaceEmptyState() {
  const mapPanel = document.querySelector("#map-panel");
  const emptyState = document.querySelector("[data-map-pane-empty]");
  if (!emptyState) {
    return;
  }
  emptyState.hidden = Boolean(mapPanel) && !mapPanel.hidden;
}

function populateChapterOptions(bookSelect, chapterSelect) {
  const selected = bookSelect.options[bookSelect.selectedIndex];
  const chapterCount = Number(selected.dataset.chapters || 1);
  chapterSelect.innerHTML = "";
  for (let chapter = 1; chapter <= chapterCount; chapter += 1) {
    const option = document.createElement("option");
    option.value = String(chapter);
    option.textContent = String(chapter);
    chapterSelect.appendChild(option);
  }
}

async function loadReaderChapter(book, chapter) {
  const reader = document.querySelector("#chapter-reader");
  if (!reader) {
    return;
  }
  reader.setAttribute("aria-busy", "true");
  hideContextMenu();
  reader.innerHTML = `<p class="empty">Loading ASV text...</p>`;
  try {
    const data = await requestJson(`/api/bible/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`, {}, "Could not load chapter.");
    currentChapter = data;
    currentSelection = null;
    latestJobId = null;
    latestJobComplete = false;
    currentHighlights = [];
    renderChapter(data);
    syncAskFields();
    await Promise.all([
      loadNotes(data.book, data.chapter),
      loadHighlights(data.book, data.chapter),
      loadSavedStudies(data.book, data.chapter),
    ]);
  } catch (error) {
    reader.innerHTML = errorHtml(error.message || "Could not load chapter.");
  } finally {
    reader.removeAttribute("aria-busy");
  }
}

async function navigateToPassage(book, chapter, verseStart, verseEnd) {
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  if (bookSelect && chapterSelect) {
    bookSelect.value = book;
    populateChapterOptions(bookSelect, chapterSelect);
    chapterSelect.value = String(chapter);
  }
  await loadReaderChapter(book, chapter);
  if (!verseStart) {
    clearReaderSelection();
    return;
  }
  const context = {
    book,
    chapter: Number(chapter),
    startVerse: Number(verseStart),
    endVerse: Number(verseEnd || verseStart),
    text: collectSelectedVerseText(Number(verseStart), Number(verseEnd || verseStart)),
    isSelection: Number(verseEnd || verseStart) !== Number(verseStart),
  };
  applySelectionContext(context);
  scrollToVerse(Number(verseStart));
}

function renderChapter(data) {
  const reader = document.querySelector("#chapter-reader");
  const heading = document.createElement("h3");
  heading.textContent = `${data.book} ${data.chapter}`;
  const paragraph = document.createElement("p");
  paragraph.className = "chapter-text";
  for (const verse of data.verses) {
    const verseSpan = document.createElement("span");
    verseSpan.className = "verse";
    verseSpan.dataset.verse = String(verse.verse);

    const number = document.createElement("sup");
    number.className = "verse-number";
    number.textContent = String(verse.verse);

    const text = document.createElement("span");
    text.className = "verse-text";
    text.textContent = verse.text + " ";

    verseSpan.appendChild(number);
    verseSpan.appendChild(text);
    paragraph.appendChild(verseSpan);
  }
  reader.innerHTML = "";
  reader.appendChild(heading);
  reader.appendChild(paragraph);
}

function collectSelectedVerseText(startVerse, endVerse) {
  const reader = document.querySelector("#chapter-reader");
  if (!reader) {
    return "";
  }
  return Array.from(reader.querySelectorAll("[data-verse]"))
    .filter((verse) => {
      const number = Number(verse.dataset.verse);
      return startVerse <= number && number <= endVerse;
    })
    .map((verse) => verse.querySelector(".verse-text")?.textContent.trim() || "")
    .join(" ")
    .trim();
}

function scrollToVerse(verseNumber) {
  const verse = document.querySelector(`#chapter-reader [data-verse="${String(verseNumber)}"]`);
  if (!verse) {
    return;
  }
  verse.scrollIntoView({ behavior: "smooth", block: "center" });
}

function handleReaderContextMenu(event) {
  const verse = event.target.closest("[data-verse]");
  const reader = document.querySelector("#chapter-reader");
  if (!verse || !reader || !reader.contains(verse) || !currentChapter) {
    return;
  }

  const context = selectionContextFromDocument() || contextFromVerse(verse);
  if (!context) {
    return;
  }

  event.preventDefault();
  contextMenuState = context;
  applySelectionContext(context);
  showContextMenu(event.clientX, event.clientY, context);
}

function handleReaderPointerDown(event) {
  if (event.pointerType !== "touch") {
    cancelReaderLongPress();
    return;
  }
  const verse = event.target.closest("[data-verse]");
  const reader = document.querySelector("#chapter-reader");
  if (!verse || !reader || !reader.contains(verse) || !currentChapter) {
    cancelReaderLongPress();
    return;
  }
  cancelReaderLongPress();
  readerLongPressState = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    clientX: event.clientX,
    clientY: event.clientY,
    verse,
    triggered: false,
    timerId: window.setTimeout(() => {
      triggerReaderLongPress();
    }, READER_LONG_PRESS_DELAY_MS),
  };
}

function handleReaderPointerMove(event) {
  if (!readerLongPressState || event.pointerId !== readerLongPressState.pointerId) {
    return;
  }
  const deltaX = Math.abs(event.clientX - readerLongPressState.startX);
  const deltaY = Math.abs(event.clientY - readerLongPressState.startY);
  if (deltaX > READER_LONG_PRESS_MOVE_THRESHOLD_PX || deltaY > READER_LONG_PRESS_MOVE_THRESHOLD_PX) {
    cancelReaderLongPress();
    return;
  }
  readerLongPressState.clientX = event.clientX;
  readerLongPressState.clientY = event.clientY;
}

function handleReaderPointerLeave(event) {
  if (!readerLongPressState || event.pointerId !== readerLongPressState.pointerId) {
    return;
  }
  cancelReaderLongPress();
}

function triggerReaderLongPress() {
  if (!readerLongPressState || readerLongPressState.triggered) {
    return;
  }
  const context = selectionContextFromDocument() || contextFromVerse(readerLongPressState.verse);
  if (!context) {
    cancelReaderLongPress();
    return;
  }
  readerLongPressState.triggered = true;
  contextMenuState = context;
  applySelectionContext(context);
  showContextMenu(readerLongPressState.clientX, readerLongPressState.clientY, context);
  if (window.navigator?.vibrate) {
    window.navigator.vibrate(10);
  }
}

function cancelReaderLongPress() {
  if (!readerLongPressState) {
    return;
  }
  if (readerLongPressState.timerId) {
    window.clearTimeout(readerLongPressState.timerId);
  }
  readerLongPressState = null;
}

function selectionContextFromDocument() {
  const selection = window.getSelection();
  const reader = document.querySelector("#chapter-reader");
  if (!selection || !reader || selection.rangeCount === 0 || selection.isCollapsed) {
    return null;
  }
  const range = selection.getRangeAt(0);
  if (!reader.contains(range.commonAncestorContainer)) {
    return null;
  }
  const selectedVerses = Array.from(reader.querySelectorAll("[data-verse]"))
    .filter((verse) => range.intersectsNode(verse));
  if (selectedVerses.length === 0) {
    return null;
  }
  return {
    book: currentChapter.book,
    chapter: currentChapter.chapter,
    startVerse: Number(selectedVerses[0].dataset.verse),
    endVerse: Number(selectedVerses[selectedVerses.length - 1].dataset.verse),
    text: selection.toString().trim(),
    isSelection: true
  };
}

function contextFromVerse(verse) {
  if (!currentChapter) {
    return null;
  }
  const verseNumber = Number(verse.dataset.verse);
  return {
    book: currentChapter.book,
    chapter: currentChapter.chapter,
    startVerse: verseNumber,
    endVerse: verseNumber,
    text: verse.querySelector(".verse-text")?.textContent.trim() || "",
    isSelection: false
  };
}

function showContextMenu(x, y, context) {
  const menu = document.querySelector("#reader-context-menu");
  if (!menu) {
    return;
  }
  const isSelection = Boolean(context.isSelection);
  setContextLabel("ancient_context", isSelection ? "Ancient Context" : "Ancient Context");
  setContextLabel("literary_context", isSelection ? "Literary Context" : "Literary Context");
  setContextLabel("cross_references", isSelection ? "Cross References" : "Cross References");
  setContextLabel("related_ot_themes", isSelection ? "Related OT Themes" : "Related OT Themes");
  setContextLabel("fulfillment_nt", isSelection ? "Fulfillment in the NT" : "Fulfillment in the NT");
  setContextLabel("compare_translations", isSelection ? "Compare Translations" : "Compare Translations");
  setContextLabel("timeline", isSelection ? "Timeline" : "Timeline");
  setContextLabel("ask_location", isSelection ? "Ask about this location" : "Ask about this location");
  setContextLabel("open_map_panel", isSelection ? "Open map panel" : "Open map panel");
  setContextLabel("save_map_study", "Save map study");
  setContextLabel("map_note", "Add map note");
  setContextLabel("compare_archaeology", "Compare with archaeology");
  setContextLabel("related_passages", "View related passages");
  setContextLabel("view_historical_layer", "View historical layer");
  setContextLabel("save_study", "Save Study");
  setContextLabel("note", isSelection ? "Add note to selection" : "Add note to this verse");
  setContextLabel("highlight", isSelection ? "Highlight selection" : "Highlight this verse");
  menu.hidden = false;
  const rect = menu.getBoundingClientRect();
  const left = Math.min(x, window.innerWidth - rect.width - 8);
  const top = Math.min(y, window.innerHeight - rect.height - 8);
  menu.style.left = `${Math.max(8, left)}px`;
  menu.style.top = `${Math.max(8, top)}px`;
  const firstButton = menu.querySelector("button");
  if (firstButton) {
    firstButton.focus({ preventScroll: true });
  }
}

function setContextLabel(action, label) {
  const button = document.querySelector(`[data-context-action="${action}"]`);
  if (button) {
    button.textContent = label;
  }
}

async function handleContextMenuAction(event) {
  const button = event.target.closest("[data-context-action]");
  if (!button || !contextMenuState) {
    return;
  }
  const actionType = button.dataset.contextAction;
  const context = contextMenuState;
  hideContextMenu();
  await dispatchStudyAction(createStudyAction(actionType, context));
}

function createStudyAction(type, context) {
  return {
    type,
    book: context.book,
    chapter: Number(context.chapter),
    verseStart: Number(context.startVerse),
    verseEnd: Number(context.endVerse || context.startVerse),
    selectedText: context.text || "",
    sourceTranslation: "ASV"
  };
}

async function dispatchStudyAction(studyAction) {
  applyStudyActionContext(studyAction);
  if (BHF_STUDY_ACTIONS.has(studyAction.type)) {
    activateWorkspaceTab("ask");
    const askMode = studyAction.type === "ask_location" ? "maps" : studyAction.type;
    if (studyAction.type === "ask_location") {
      setFormValue("question", "What does the geography of this passage suggest?");
    } else if (studyAction.type === "related_passages") {
      setFormValue("question", "What related passages should I review for this location?");
    }
    setFormValue("ask_mode", askMode);
    setFormValue("study_action", studyAction.type);
    setMapContextValue(buildReaderMapContext(studyAction));
    submitAskForm();
  } else if (studyAction.type === "note") {
    openNoteEditor();
  } else if (studyAction.type === "highlight") {
    await createHighlight(studyAction);
  } else if (studyAction.type === "save_study") {
    await saveLatestStudy();
  } else if (studyAction.type === "open_map_panel") {
    setFormValue("ask_mode", "");
    setFormValue("study_action", "");
    openMapPanel(studyAction);
  } else if (studyAction.type === "save_map_study") {
    activateWorkspaceTab("maps");
    if (window.BHFMaps && typeof window.BHFMaps.saveCurrentMapStudy === "function") {
      await window.BHFMaps.saveCurrentMapStudy();
    } else {
      openMapPanel(studyAction);
    }
  } else if (studyAction.type === "map_note") {
    activateWorkspaceTab("maps");
    if (window.BHFMaps && typeof window.BHFMaps.focusMapNoteEditor === "function") {
      window.BHFMaps.focusMapNoteEditor();
    } else {
      openMapPanel(studyAction);
    }
  } else if (studyAction.type === "compare_archaeology") {
    setFormValue("ask_mode", "maps");
    setFormValue("study_action", studyAction.type);
    setFormValue("question", "What archaeology is connected with this passage or location?");
    setMapContextValue(buildReaderMapContext(studyAction));
    submitAskForm();
  } else if (studyAction.type === "related_passages") {
    setFormValue("ask_mode", "cross_references");
    setFormValue("study_action", studyAction.type);
    setMapContextValue(buildReaderMapContext(studyAction));
    submitAskForm();
  } else if (studyAction.type === "view_historical_layer") {
    openMapPanel(studyAction);
  }
}

function applyStudyActionContext(studyAction) {
  applySelectionContext({
    book: studyAction.book,
    chapter: studyAction.chapter,
    startVerse: studyAction.verseStart,
    endVerse: studyAction.verseEnd,
    text: studyAction.selectedText,
    isSelection: studyAction.verseStart !== studyAction.verseEnd || Boolean(studyAction.selectedText)
  });
}

function submitAskForm() {
  const form = document.querySelector(".ask-form");
  if (!form) {
    return;
  }
  if (typeof form.requestSubmit === "function") {
    form.requestSubmit();
  } else {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  }
}

function requestMapAIFallback(mapContext = {}, options = {}) {
  const form = document.querySelector(".ask-form");
  if (!form) {
    return false;
  }
  const reference =
    mapContext.passage_reference ||
    [mapContext.book, mapContext.chapter].filter(Boolean).join(" ") ||
    "the selected passage";
  const localSummary =
    options.localSummary ||
    "No curated local map places, routes, archaeology, manuscripts, historical layers, or political-context overlays matched this passage.";
  const key = JSON.stringify({
    reference,
    summary: localSummary,
  });
  if (lastMapAIFallbackKey === key) {
    return false;
  }
  lastMapAIFallbackKey = key;
  form.dataset.activeTarget = "#map-ai-answer-panel";
  form.dataset.activeStatusTarget = "#map-ai-status-panel";
  activateWorkspaceTab("maps");
  setFormValue(
    "question",
    options.question ||
      `The local curated map dataset has no direct match for ${reference}. Give a cautious text-only geography explanation, identify any explicit or implied locations or regions, and clearly label uncertainty.`
  );
  setFormValue("ask_mode", "maps");
  setFormValue("study_action", "ask_location");
  setMapContextValue({
    ...mapContext,
    local_map_fallback: true,
    local_map_summary: localSummary,
  });
  const mapAnswerPanel = document.querySelector("#map-ai-answer-panel");
  if (mapAnswerPanel) {
    activeLiveAnswerPanel = mapAnswerPanel;
  }
  updateSaveButtons();
  submitAskForm();
  return true;
}

function closeContextMenuOnOutside(event) {
  const menu = document.querySelector("#reader-context-menu");
  if (menu && !menu.hidden && !menu.contains(event.target)) {
    hideContextMenu();
  }
}

function closeContextMenuOnEscape(event) {
  if (event.key === "Escape") {
    hideContextMenu();
  }
}

function hideContextMenu() {
  const menu = document.querySelector("#reader-context-menu");
  if (menu) {
    menu.hidden = true;
  }
  contextMenuState = null;
}

function updateSelectionFromDocument() {
  const context = selectionContextFromDocument();
  if (!context) {
    return;
  }
  applySelectionContext(context);
}

function applySelectionContext(context) {
  const reader = document.querySelector("#chapter-reader");
  if (!reader) {
    return;
  }
  currentSelection = context;
  reader.querySelectorAll(".verse.selected").forEach((verse) => {
    verse.classList.remove("selected");
  });
  reader.querySelectorAll("[data-verse]").forEach((verse) => {
    const verseNumber = Number(verse.dataset.verse);
    if (context.startVerse <= verseNumber && verseNumber <= context.endVerse) {
      verse.classList.add("selected");
    }
  });
  syncAskFields();
}

function clearReaderSelection() {
  const reader = document.querySelector("#chapter-reader");
  if (reader) {
    reader.querySelectorAll(".verse.selected").forEach((verse) => {
      verse.classList.remove("selected");
    });
  }
  currentSelection = null;
  syncAskFields();
}

function syncAskFields() {
  if (!currentChapter) {
    return;
  }
  setFormValue("reader_book", currentChapter.book);
  setFormValue("reader_chapter", currentChapter.chapter);
  setFormValue("reader_start_verse", currentSelection ? currentSelection.startVerse : "");
  setFormValue("reader_end_verse", currentSelection ? currentSelection.endVerse : "");
  setFormValue("reader_selected_text", currentSelection ? currentSelection.text : "");

  const summary = document.querySelector("#selection-summary");
  const addNoteButton = document.querySelector("[data-add-note]");
  if (currentSelection) {
    const reference = formatReference(
      currentChapter.book,
      currentChapter.chapter,
      currentSelection.startVerse,
      currentSelection.endVerse
    );
    if (summary) {
      summary.textContent = `Selected ASV ${reference}`;
    }
    if (addNoteButton) {
      addNoteButton.disabled = false;
    }
  } else {
    if (summary) {
      summary.textContent = `Ask about ${currentChapter.book} ${currentChapter.chapter}, or select verse text for a focused question.`;
    }
    if (addNoteButton) {
      addNoteButton.disabled = true;
    }
  }
}

function setFormValue(name, value) {
  const input = document.querySelector(`.ask-form [name="${name}"]`);
  if (input) {
    input.value = value;
  }
}

function setMapContextValue(context) {
  const input = document.querySelector(`.ask-form [name="map_context"]`);
  if (!input) {
    return;
  }
  input.value = context ? JSON.stringify(context) : "";
}

function buildReaderMapContext(studyAction) {
  const passageReference = `${studyAction.book} ${studyAction.chapter}:${studyAction.verseStart}-${studyAction.verseEnd}`;
  return {
    passage_reference: passageReference,
    book: studyAction.book,
    chapter: studyAction.chapter,
    verse_start: studyAction.verseStart,
    verse_end: studyAction.verseEnd,
    selected_text: studyAction.selectedText || "",
    source_translation: studyAction.sourceTranslation || "ASV",
    note: "Structured map context from the reader selection. A more specific place will be supplied after the map resolves curated data.",
  };
}

function openMapPanel(context) {
  activateWorkspaceTab("maps");
  const panel = document.querySelector("#map-panel");
  if (panel) {
    panel.hidden = false;
  }
  syncMapWorkspaceEmptyState();
  if (window.BHFMaps && typeof window.BHFMaps.openMapPanel === "function") {
    window.BHFMaps.openMapPanel(context);
    return;
  }
}

async function pollJob(form, statusPanel, jobId) {
  while (true) {
    const status = await requestJson(form.dataset.statusBase + jobId, {
      headers: { "Accept": "application/json" }
    }, "Could not read request status.");

    renderStatus(statusPanel, status);
    if (status.done) {
      return status;
    }
    await delay(POLL_INTERVAL_MS);
  }
}
