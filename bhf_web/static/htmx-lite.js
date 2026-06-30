const POLL_INTERVAL_MS = 750;
const WAITING_MESSAGE_BASE_DELAY_MS = 3000;
const WAITING_MESSAGE_JITTER_MS = 900;
const READER_LONG_PRESS_DELAY_MS = 550;
const READER_LONG_PRESS_MOVE_THRESHOLD_PX = 14;
const WAITING_MESSAGES = [
  "Consulting the scrolls...",
  "Parting the data sea...",
  "Gathering manna packets...",
  "Counting the begats...",
  "Sharpening the sword...",
  "Lighting the lampstand...",
  "Dusting off the tablets...",
  "Wrestling the context angel...",
  "Summoning the Bereans...",
  "Checking the prophets...",
  "Cross-referencing the scrolls...",
  "Feeding the five queries...",
  "Multiplying the insights...",
  "Walking through the wilderness...",
  "Circling Jericho...",
  "Sounding the tiny trumpet...",
  "Building the ark cache...",
  "Sorting clean and unclean data...",
  "Calibrating the ephod...",
  "Tuning the psaltery...",
  "Plucking the harp strings...",
  "Reading the fine papyrus...",
  "Unrolling Isaiah...",
  "Decoding Daniel...",
  "Pondering in the heart...",
  "Seeking wisdom from Proverbs...",
  "Chasing Ecclesiastes vibes...",
  "Loading Lamentations responsibly...",
  "Avoiding Job’s friends...",
  "Checking the original audience...",
  "Hermeneuticizing the heavens...",
  "Exegeting the electrons...",
  "Sanctifying the syntax...",
  "Baptizing the breadcrumbs...",
  "Anointing the answer...",
  "Blessing the backend...",
  "Rebuking hallucinations...",
  "Casting out bad context...",
  "Binding loose assumptions...",
  "Loosing fresh insights...",
  "Rightly dividing the response...",
  "Testing every spirit...",
  "Weighing the witnesses...",
  "Marching around the thesis...",
  "Gathering twelve baskets...",
  "Waiting on the answer...",
  "Praying over the payload...",
  "Turning water into output...",
  "Ascending the context mountain...",
  "Calling the Schwartz of Solomon...",
];
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

let waitingTimerId = null;
let waitingMessageIndex = 0;
let latestStatus = null;
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
    const createResponse = await fetch(form.dataset.jobPost, {
      method: "POST",
      body: new FormData(form),
      headers: { "Accept": "application/json" }
    });
    const job = await createResponse.json();
    if (!createResponse.ok || !job.job_id) {
      throw new Error(job.error || "Could not start request.");
    }
    latestJobId = job.job_id;
    latestJobComplete = false;

    const finalStatus = await pollJob(form, statusPanel, job.job_id);
    const resultResponse = await fetch(form.dataset.resultBase + finalStatus.job_id);
    answerPanel.innerHTML = await resultResponse.text();

    if (finalStatus.error || !resultResponse.ok) {
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
    const response = await fetch(`/api/bible/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Could not load chapter.");
    }
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

async function submitBibleSearch(event) {
  event.preventDefault();
  const form = event.target;
  syncBibleSearchConfig(form);
  const queryInput = form.querySelector("[name='query']");
  const query = queryInput ? queryInput.value.trim() : "";
  if (!query) {
    setBibleSearchStatus("Enter a search term or reference.", "empty");
    showBibleSearchResults();
    renderBibleSearchResults([]);
    updateBibleSearchSummary("");
    return;
  }

  const requestId = ++latestBibleSearchRequestId;
  showBibleSearchResults();
  updateBibleSearchSummary(`Searching ASV for “${query}”`);
  setBibleSearchStatus("Searching local ASV text...", "loading");
  renderBibleSearchResults([]);

  try {
    const response = await fetch(`/api/bible/search?${new URLSearchParams({ q: query, limit: "25" })}`);
    const data = await response.json();
    if (requestId !== latestBibleSearchRequestId) {
      return;
    }
    if (!response.ok) {
      throw new Error(data.error || "Could not search the ASV text.");
    }
    if (Array.isArray(data.results) && data.results.length > 0) {
      updateBibleSearchSummary(`${data.total_results} local result${data.total_results === 1 ? "" : "s"} for “${query}”`);
      clearBibleSearchStatus();
      renderBibleSearchResults(data.results, { source: "local" });
      return;
    }

    renderBibleSearchResults([]);
    if (data.ai_fallback_eligible) {
      updateBibleSearchSummary(`No local ASV matches for “${query}”. Asking BHF for likely passages.`);
      setBibleSearchStatus("No local match found. Asking BHF for likely passages...", "loading");
      await runBibleSearchFallback(form, query, requestId);
      return;
    }

    updateBibleSearchSummary(`No local ASV matches for “${query}”`);
    setBibleSearchStatus(data.no_results_message || "No local ASV matches were found.", "empty");
  } catch (error) {
    if (requestId !== latestBibleSearchRequestId) {
      return;
    }
    setBibleSearchStatus(error.message || "Could not search the ASV text.", "error");
  }
}

async function runBibleSearchFallback(form, query, requestId) {
  const payload = new FormData(form);
  const response = await fetch("/api/bible/search/fallback/jobs", {
    method: "POST",
    body: payload,
    headers: { Accept: "application/json" },
  });
  const job = await response.json();
  if (!response.ok || !job.job_id) {
    throw new Error(job.error || "Could not start the BHF search fallback.");
  }
  const result = await pollBibleSearchFallback(job.job_id, requestId);
  if (requestId !== latestBibleSearchRequestId) {
    return;
  }
  if (Array.isArray(result.results) && result.results.length > 0) {
    updateBibleSearchSummary(`BHF suggested ${result.results.length} likely passage${result.results.length === 1 ? "" : "s"} for “${query}”`);
    clearBibleSearchStatus();
    renderBibleSearchResults(result.results, { source: "ai" });
    return;
  }
  renderBibleSearchResults([]);
  setBibleSearchStatus(result.message || "BHF could not identify likely passage candidates.", "empty");
}

function syncBibleSearchConfig(searchForm) {
  const askForm = document.querySelector(".ask-form");
  if (!askForm || !searchForm) {
    return;
  }
  for (const name of [
    "profile",
    "answer_mode",
    "model",
    "base_url",
    "temperature",
    "max_tokens",
    "timeout_seconds",
    "memory_max_turns",
    "session_id",
    "memory_path",
  ]) {
    const askInput = askForm.querySelector(`[name="${name}"]`);
    let searchInput = searchForm.querySelector(`[name="${name}"]`);
    if (!searchInput) {
      searchInput = document.createElement("input");
      searchInput.type = "hidden";
      searchInput.name = name;
      searchForm.appendChild(searchInput);
    }
    searchInput.value = askInput ? askInput.value : "";
  }
  syncBibleSearchCheckbox(searchForm, askForm, "show_method_notes");
  syncBibleSearchCheckbox(searchForm, askForm, "memory_enabled");
}

function syncBibleSearchCheckbox(searchForm, askForm, name) {
  const existing = searchForm.querySelector(`[name="${name}"]`);
  const askInput = askForm.querySelector(`[name="${name}"]`);
  const checked = Boolean(askInput && askInput.checked);
  if (!checked && existing) {
    existing.remove();
    return;
  }
  if (checked && !existing) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = "on";
    searchForm.appendChild(input);
    return;
  }
  if (existing) {
    existing.value = "on";
  }
}

async function pollBibleSearchFallback(jobId, requestId) {
  while (true) {
    const statusResponse = await fetch(`/api/bible/search/fallback/status/${encodeURIComponent(jobId)}`);
    const status = await statusResponse.json();
    if (requestId !== latestBibleSearchRequestId) {
      return { results: [], message: "" };
    }
    if (!statusResponse.ok) {
      throw new Error(status.error || "Could not check BHF fallback search status.");
    }
    if (status.done) {
      const resultResponse = await fetch(`/api/bible/search/fallback/result/${encodeURIComponent(jobId)}`);
      const result = await resultResponse.json();
      if (!resultResponse.ok) {
        throw new Error(result.error || "BHF search fallback failed.");
      }
      return result;
    }
    await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
  }
}

function showBibleSearchResults() {
  const panel = document.querySelector("#reader-search-results");
  if (panel) {
    panel.hidden = false;
  }
}

function clearBibleSearchResults() {
  latestBibleSearchRequestId += 1;
  const panel = document.querySelector("#reader-search-results");
  const body = document.querySelector("#reader-search-results-body");
  const summary = document.querySelector("#reader-search-summary");
  const status = document.querySelector("#reader-search-status");
  if (panel) {
    panel.hidden = true;
  }
  if (body) {
    body.innerHTML = "";
  }
  if (summary) {
    summary.textContent = "";
  }
  if (status) {
    status.hidden = true;
    status.textContent = "";
    status.classList.remove("is-empty", "is-error");
  }
}

function updateBibleSearchSummary(text) {
  const summary = document.querySelector("#reader-search-summary");
  if (summary) {
    summary.textContent = text || "";
  }
}

function setBibleSearchStatus(message, state) {
  const status = document.querySelector("#reader-search-status");
  if (!status) {
    return;
  }
  status.hidden = false;
  status.textContent = message;
  status.classList.toggle("is-empty", state === "empty");
  status.classList.toggle("is-error", state === "error");
}

function clearBibleSearchStatus() {
  const status = document.querySelector("#reader-search-status");
  if (!status) {
    return;
  }
  status.hidden = true;
  status.textContent = "";
  status.classList.remove("is-empty", "is-error");
}

function renderBibleSearchResults(results, options = {}) {
  const body = document.querySelector("#reader-search-results-body");
  if (!body) {
    return;
  }
  if (!Array.isArray(results) || results.length === 0) {
    body.innerHTML = "";
    return;
  }
  const source = options.source || "local";
  body.innerHTML = `
    <div class="search-results-list">
      ${results.map((result) => renderBibleSearchResultCard(result, source)).join("")}
    </div>
  `;
}

function renderBibleSearchResultCard(result, source) {
  const canGoToVerse = Boolean(result.verse_start);
  const sourceBadge = source === "ai" ? "BHF likely passage" : result.match_type === "direct_reference" ? "Direct reference" : "ASV";
  const confidenceBadge = source === "ai" && result.confidence ? `<span class="search-badge">${escapeHtml(String(result.confidence))}</span>` : "";
  const subtitle = source === "ai"
    ? escapeHtml(result.reason || "Likely topical connection.")
    : escapeHtml(result.excerpt || "");
  return `
    <article class="search-result-card">
      <div class="search-result-header">
        <div>
          <h4>${escapeHtml(result.reference || "")}</h4>
          <p class="search-result-meta">${subtitle}</p>
        </div>
        <div class="search-result-badges">
          <span class="search-badge ${source === "ai" ? "source-ai" : ""}">${escapeHtml(sourceBadge)}</span>
          ${confidenceBadge}
        </div>
      </div>
      <div class="search-result-actions">
        ${canGoToVerse ? `<button type="button" class="secondary" data-search-action="go-to-verse" data-book="${escapeHtml(result.book || "")}" data-chapter="${escapeHtml(String(result.chapter || ""))}" data-verse-start="${escapeHtml(String(result.verse_start || ""))}" data-verse-end="${escapeHtml(String(result.verse_end || ""))}">Go to verse</button>` : ""}
        <button type="button" class="secondary" data-search-action="open-chapter" data-book="${escapeHtml(result.book || "")}" data-chapter="${escapeHtml(String(result.chapter || ""))}">Open chapter</button>
      </div>
    </article>
  `;
}

async function handleBibleSearchResultAction(event) {
  const button = event.target.closest("[data-search-action]");
  if (!button) {
    return;
  }
  const book = button.getAttribute("data-book") || "";
  const chapter = Number(button.getAttribute("data-chapter") || "0");
  if (!book || !chapter) {
    return;
  }
  if (button.getAttribute("data-search-action") === "go-to-verse") {
    await navigateToPassage(
      book,
      chapter,
      Number(button.getAttribute("data-verse-start") || "0"),
      Number(button.getAttribute("data-verse-end") || button.getAttribute("data-verse-start") || "0")
    );
    return;
  }
  await navigateToPassage(book, chapter, null, null);
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

async function loadNotes(book, chapter) {
  const list = document.querySelector("#notes-list");
  const count = document.querySelector("#notes-count");
  if (!list) {
    return;
  }
  try {
    const response = await fetch(`/api/notes/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Could not load notes.");
    }
    renderNotes(data.notes || []);
    if (count) {
      count.textContent = String((data.notes || []).length);
    }
  } catch (error) {
    list.innerHTML = errorHtml(error.message || "Could not load notes.");
  }
}

async function loadHighlights(book, chapter) {
  const list = document.querySelector("#highlights-list");
  const count = document.querySelector("#highlights-count");
  if (!list) {
    return;
  }
  try {
    const response = await fetch(`/api/highlights/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Could not load highlights.");
    }
    currentHighlights = data.highlights || [];
    renderHighlights(currentHighlights);
    applyHighlightsToReader(currentHighlights);
    if (count) {
      count.textContent = String(currentHighlights.length);
    }
  } catch (error) {
    list.innerHTML = errorHtml(error.message || "Could not load highlights.");
  }
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

async function createHighlight(context) {
  if (!currentChapter) {
    return;
  }
  const response = await fetch("/api/highlights", {
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
  });
  const data = await response.json();
  if (!response.ok) {
    window.alert(data.error || "Could not save highlight.");
    return;
  }
  activateWorkspaceTab("highlights");
  await loadHighlights(currentChapter.book, currentChapter.chapter);
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

async function saveNote(event) {
  event.preventDefault();
  if (!noteContext || !currentChapter) {
    return;
  }
  const form = event.target;
  const payload = {
    ...noteContext,
    body: form.elements.body.value
  };
  const noteId = form.elements.id.value;
  const url = noteId ? `/api/notes/${encodeURIComponent(noteId)}` : "/api/notes";
  const method = noteId ? "PUT" : "POST";
  const response = await fetch(url, {
    method,
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok) {
    window.alert(data.error || "Could not save note.");
    return;
  }
  closeNoteEditor();
  await loadNotes(currentChapter.book, currentChapter.chapter);
}

async function deleteExistingNote(noteId) {
  if (!currentChapter) {
    return;
  }
  const response = await fetch(`/api/notes/${encodeURIComponent(noteId)}`, {
    method: "DELETE",
    headers: { "Accept": "application/json" }
  });
  if (!response.ok) {
    const data = await response.json();
    window.alert(data.error || "Could not delete note.");
    return;
  }
  await loadNotes(currentChapter.book, currentChapter.chapter);
}

async function deleteExistingHighlight(highlightId) {
  if (!currentChapter) {
    return;
  }
  const response = await fetch(`/api/highlights/${encodeURIComponent(highlightId)}`, {
    method: "DELETE",
    headers: { "Accept": "application/json" }
  });
  if (!response.ok) {
    const data = await response.json();
    window.alert(data.error || "Could not remove highlight.");
    return;
  }
  await loadHighlights(currentChapter.book, currentChapter.chapter);
}

async function loadSavedStudies(book, chapter) {
  const list = document.querySelector("#saved-studies-list");
  const count = document.querySelector("#saved-studies-count");
  if (!list || !book || !chapter) {
    return;
  }
  try {
    const response = await fetch(`/api/saved-studies?book=${encodeURIComponent(book)}&chapter=${encodeURIComponent(chapter)}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Could not load saved studies.");
    }
    const studies = data.saved_studies || [];
    renderSavedStudies(studies);
    if (count) {
      count.textContent = String(studies.length);
    }
  } catch (error) {
    list.innerHTML = errorHtml(error.message || "Could not load saved studies.");
  }
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

async function openSavedStudy(studyId) {
  activateWorkspaceTab("ask");
  const answerPanel = document.querySelector("#answer-panel");
  if (!answerPanel) {
    return;
  }
  const response = await fetch(`/api/saved-studies/${encodeURIComponent(studyId)}`, {
    headers: { "Accept": "text/html" }
  });
  const html = await response.text();
  if (!response.ok) {
    answerPanel.innerHTML = html;
    return;
  }
  answerPanel.innerHTML = html;
  activeLiveAnswerPanel = answerPanel;
  latestJobComplete = false;
  wireAnswerPanelControls(answerPanel);
}

async function deleteSavedStudy(studyId) {
  if (!currentChapter) {
    return;
  }
  const response = await fetch(`/api/saved-studies/${encodeURIComponent(studyId)}`, {
    method: "DELETE",
    headers: { "Accept": "application/json" }
  });
  if (!response.ok) {
    const data = await response.json();
    window.alert(data.error || "Could not delete saved study.");
    return;
  }
  await loadSavedStudies(currentChapter.book, currentChapter.chapter);
}

async function saveLatestStudy() {
  if (!latestJobId || !latestJobComplete) {
    window.alert("Run a study first, then save it.");
    return;
  }
  const saveButton = activeLiveAnswerPanel?.querySelector("[data-save-study]") || null;
  if (saveButton) {
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";
  }
  const response = await fetch("/api/saved-studies", {
    method: "POST",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      job_id: latestJobId
    })
  });
  const data = await response.json();
  if (!response.ok) {
    window.alert(data.error || "Could not save study.");
    if (saveButton) {
      saveButton.disabled = false;
      saveButton.textContent = "Save Study";
    }
    return;
  }
  if (saveButton) {
    saveButton.textContent = "Saved";
  }
  activateWorkspaceTab("saved");
  if (currentChapter) {
    await loadSavedStudies(currentChapter.book, currentChapter.chapter);
  }
  updateSaveButtons();
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

async function pollJob(form, statusPanel, jobId) {
  while (true) {
    const response = await fetch(form.dataset.statusBase + jobId, {
      headers: { "Accept": "application/json" }
    });
    const status = await response.json();
    if (!response.ok) {
      throw new Error(status.error || "Could not read request status.");
    }

    renderStatus(statusPanel, status);
    if (status.done) {
      return status;
    }
    await delay(POLL_INTERVAL_MS);
  }
}

function resetStatus(statusPanel) {
  latestStatus = null;
  waitingMessageIndex = 0;
  statusPanel.hidden = false;
  statusPanel.classList.remove("complete", "failed");
  statusPanel.querySelector(".status-active").hidden = false;
  statusPanel.querySelector(".status-summary").hidden = true;
  statusPanel.querySelector(".status-summary").textContent = "";
  statusPanel.querySelector(".status-current").textContent = "Preparing request";
}

function renderStatus(statusPanel, status) {
  latestStatus = status;
  statusPanel.hidden = false;
  statusPanel.classList.toggle("failed", Boolean(status.error || status.status === "error"));
  statusPanel.classList.toggle("complete", Boolean(status.done && !status.error));
  if (status.error || status.status === "error") {
    statusPanel.querySelector(".status-current").textContent = "Failed";
  } else if (status.done) {
    statusPanel.querySelector(".status-current").textContent = status.message;
  }
}

function startWaiting(statusPanel) {
  stopWaiting();
  setWaitingMessage(statusPanel);
  scheduleNextWaitingMessage(statusPanel);
}

function stopWaiting() {
  if (waitingTimerId !== null) {
    window.clearTimeout(waitingTimerId);
    waitingTimerId = null;
  }
}

function setWaitingMessage(statusPanel) {
  const current = statusPanel.querySelector(".status-current");
  if (!current) {
    return;
  }
  current.textContent = WAITING_MESSAGES[waitingMessageIndex % WAITING_MESSAGES.length];
  waitingMessageIndex += 1;
}

function scheduleNextWaitingMessage(statusPanel) {
  waitingTimerId = window.setTimeout(() => {
    setWaitingMessage(statusPanel);
    if (!latestStatus || !latestStatus.done) {
      scheduleNextWaitingMessage(statusPanel);
    }
  }, randomWaitingDelay());
}

function randomWaitingDelay() {
  const jitter = Math.floor((Math.random() * 2 - 1) * WAITING_MESSAGE_JITTER_MS);
  return WAITING_MESSAGE_BASE_DELAY_MS + jitter;
}

function markStatusComplete(statusPanel, status) {
  stopWaiting();
  const elapsed = Number(status.elapsed_total_seconds || 0);
  statusPanel.classList.remove("failed");
  statusPanel.classList.add("complete");
  statusPanel.querySelector(".status-active").hidden = true;
  const summary = statusPanel.querySelector(".status-summary");
  summary.hidden = false;
  summary.textContent = `Complete - finished in ${formatSeconds(elapsed)}`;
}

function markStatusFailed(statusPanel, message) {
  stopWaiting();
  statusPanel.hidden = false;
  statusPanel.classList.remove("complete");
  statusPanel.classList.add("failed");
  statusPanel.querySelector(".status-active").hidden = false;
  statusPanel.querySelector(".status-summary").hidden = true;
  statusPanel.querySelector(".status-current").textContent = "Failed";
}

function setRunning(form, submitButton, running) {
  form.setAttribute("aria-busy", running ? "true" : "false");
  if (submitButton) {
    submitButton.disabled = running;
    submitButton.textContent = running ? "Asking BHF..." : "Ask BHF";
  }
}

function errorHtml(message) {
  const escaped = escapeHtml(message);
  return `<div class="error" role="alert"><h2>Could not ask BHF</h2><p>${escaped}</p></div>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#039;");
}

function formatSeconds(value) {
  const seconds = Math.max(0, Number(value) || 0);
  return `${seconds.toFixed(1)}s`;
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
