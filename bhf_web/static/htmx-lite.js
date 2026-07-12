// This file stays intentionally monolithic for now.
// It is the central client-side controller for reader, notes, highlights,
// map fallback, and search interactions, and the shared request helpers and
// status helpers have already been split into separate scripts.
const POLL_INTERVAL_MS = 750;
const READER_LONG_PRESS_DELAY_MS = 550;
const READER_LONG_PRESS_MOVE_THRESHOLD_PX = 14;
const APP_SECTION_STORAGE_KEY = "bhf-app-section";
const LEGACY_MOBILE_SECTION_STORAGE_KEY = "bhf-mobile-section";
const BHF_RUNTIME = window.BHFRuntimeConfig || {};
const TABLET_BREAKPOINT = Number(BHF_RUNTIME.breakpoints?.tablet || 900);
const GENERAL_QUESTION_MODE = "general_question";
const THEME_STORAGE_KEY = "bhf-theme";
const READER_MODE_STORAGE_KEY = "bhf-reader-mode";
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
let currentNotes = [];
let currentHighlights = [];
let contextMenuState = null;
let lastMapAIFallbackKey = null;
let activeLiveAnswerPanel = null;
let readerLongPressState = null;
let appSection = null;
let lastNotesWorkspaceTab = "notes";
let lastExploreWorkspaceTab = "maps";
let readerControlsTrigger = null;
const BHF_HTTP = window.BHFApi || {};

document.addEventListener("DOMContentLoaded", function () {
  initializeTheme();
  initializeReaderMode();
  initializeWorkspaceExpansion();
  initializeWorkspaceTabs();
  initializeAppNavigation();
  initializeReaderControlsSheet();
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
      expandWorkspaceForMobileAnswer();
      addMobileAnswerCloseControl(answerPanel);
      wireAnswerPanelControls(answerPanel);
      revealAnswerPanel(answerPanel);
      await loadSavedStudies(currentChapter?.book, currentChapter?.chapter);
    }
  } catch (error) {
    markStatusFailed(statusPanel, error.message || "Request failed.");
    answerPanel.innerHTML = errorHtml(error.message || "Request failed.");
    expandWorkspaceForMobileAnswer();
    addMobileAnswerCloseControl(answerPanel);
    revealAnswerPanel(answerPanel);
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

  const defaultBook = reader.dataset.defaultBook || bookSelect.value || "John";
  if (!bookSelect.value && defaultBook) {
    bookSelect.value = defaultBook;
  }
  populateChapterOptions(bookSelect, chapterSelect);
  if (!chapterSelect.options.length) {
    reader.innerHTML = `<p class="empty">No chapter data is available for ${escapeHtml(bookSelect.value || defaultBook)}.</p>`;
    return;
  }
  const defaultChapter = reader.dataset.defaultChapter || chapterSelect.options[0].value || "1";
  chapterSelect.value = defaultChapter;
  await loadReaderChapter(bookSelect.value || defaultBook, chapterSelect.value || defaultChapter);

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
  window.addEventListener("scroll", closeContextMenuOnReaderScroll, true);
  reader.addEventListener("contextmenu", handleReaderContextMenu);
  reader.addEventListener("pointerdown", handleReaderPointerDown);
  reader.addEventListener("pointermove", handleReaderPointerMove);
  reader.addEventListener("pointerup", cancelReaderLongPress);
  reader.addEventListener("pointercancel", cancelReaderLongPress);
  reader.addEventListener("pointerleave", handleReaderPointerLeave);
  reader.addEventListener("click", handleReaderActionButtonClick);
  document.addEventListener("click", handleChapterNavigationClick);
  const contextMenu = document.querySelector("#reader-context-menu");
  const searchForm = document.querySelector("[data-bible-search]");
  const searchResultsBody = document.querySelector("#reader-search-results-body");
  if (contextMenu) {
    contextMenu.addEventListener("click", handleContextMenuAction);
  }
  if (searchForm) {
    searchForm.addEventListener("submit", submitBibleSearch);
    const queryInput = searchForm.querySelector("[name='query']");
    if (queryInput && typeof syncBibleSearchClearState === "function") {
      queryInput.addEventListener("input", syncBibleSearchClearState);
      syncBibleSearchClearState();
    }
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
  document.addEventListener("bhf:map-panel-closed", () => {
    syncMapWorkspaceEmptyState();
    closeWorkspaceDrawer();
  });
  wireAnswerPanelControls(document.querySelector("#answer-panel"));
  wireAnswerPanelControls(document.querySelector("#map-ai-answer-panel"));
  syncMapWorkspaceEmptyState();
}

function handleChapterNavigationClick(event) {
  const button = event.target.closest("[data-next-chapter], [data-prev-chapter]");
  if (!button) {
    return;
  }
  if (button.matches("[data-prev-chapter]")) {
    goToPreviousChapter();
    return;
  }
  goToNextChapter();
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
    tab.addEventListener("keydown", (event) => handleWorkspaceTabKeydown(event, tabs.filter((candidate) => !candidate.hidden)));
  }
  setActiveWorkspaceTab(defaultTab);
}

function initializeAppNavigation() {
  const dock = document.querySelector("[data-app-dock]");
  const buttons = Array.from(dock?.querySelectorAll("[data-app-section]") || []);
  if (!dock || buttons.length === 0) {
    return;
  }

  const initialSection = resolveInitialAppSection(readAppSectionPreference());
  activateAppSection(initialSection, {
    persist: false,
    focusReader: false,
  });

  for (const button of buttons) {
    button.addEventListener("click", () => {
      activateAppSection(button.dataset.appSection || "bible");
    });
  }

  document.addEventListener("bhf:workspace-tab-changed", (event) => {
    const tabId = event.detail?.tabId;
    rememberWorkspaceSubtab(tabId);
    const nextSection = appSectionFromWorkspaceTab(tabId);
    if (nextSection) {
      activateAppSection(nextSection);
    }
  });

  window.addEventListener("resize", handleAppViewportChange);
}

function initializeWorkspaceBridge() {
  if (typeof window === "undefined") {
    return;
  }
  window.BHFWorkspace = {
    requestMapAIFallback,
  };
  window.BHFReader = {
    navigateToPassage,
    openPassageReference,
  };
}

function activateAppSection(sectionId, options = {}) {
  const nextSection = normalizeAppSection(sectionId);
  appSection = nextSection;
  document.body.dataset.appSection = nextSection;
  syncAppDockState(nextSection);
  syncWorkspaceTabsForSection(nextSection);
  syncReaderControlsSheetAvailability();

  if (options.persist !== false) {
    persistAppSection(nextSection);
  }

  if (isCompactViewport()) {
    applyCompactSectionLayout(nextSection);
  } else {
    applyDesktopSectionLayout(nextSection, options);
  }
  syncReaderControlsSheetAvailability();
}

function syncAppDockState(sectionId) {
  const activeSection = normalizeAppSection(sectionId || appSection || "bible");
  document.querySelectorAll("[data-app-section]").forEach((button) => {
    const isActive = button.dataset.appSection === activeSection;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function applyCompactSectionLayout(sectionId) {
  if (sectionId === "bible") {
    applyWorkspaceExpansion(false);
    closeWorkspaceDrawer();
    return;
  }

  setWorkspaceDrawerOpen(true);
}

function applyDesktopSectionLayout(sectionId, options = {}) {
  closeWorkspaceDrawer();
  if (sectionId === "bible") {
    applyWorkspaceExpansion(false);
    if (options.focusReader !== false) {
      focusReaderArea();
    }
    return;
  }

  if (document.body.classList.contains("reader-mode")) {
    applyReaderMode(false, { persist: false });
  }
  applyWorkspaceExpansion(false);
}

function handleAppViewportChange() {
  const nextSection = normalizeAppSection(appSection || readAppSectionPreference() || "bible");
  activateAppSection(nextSection, {
    persist: false,
    focusReader: false,
  });
}

function focusReaderArea() {
  const reader = document.querySelector(".reader-column");
  if (!reader) {
    return;
  }
  reader.scrollIntoView({ block: "start", behavior: "smooth" });
}

function appSectionFromWorkspaceTab(tabId) {
  if (!tabId) {
    return null;
  }
  if (tabId === "ask") {
    return tabId;
  }
  if (tabId === "notes" || tabId === "highlights") {
    return "notes";
  }
  if (tabId === "saved") {
    return "studies";
  }
  if (tabId === "maps" || tabId === "journey") {
    return "explore";
  }
  return null;
}

function appSectionToWorkspaceTab(sectionId) {
  const normalized = normalizeAppSection(sectionId);
  if (normalized === "ask" || normalized === "bible") {
    return "ask";
  }
  if (normalized === "notes") {
    const currentWorkspaceTab = getCurrentWorkspaceTab();
    if (currentWorkspaceTab === "notes" || currentWorkspaceTab === "highlights") {
      return currentWorkspaceTab;
    }
    return lastNotesWorkspaceTab || "notes";
  }
  if (normalized === "studies") {
    return "saved";
  }
  if (normalized === "explore") {
    const currentWorkspaceTab = getCurrentWorkspaceTab();
    if (currentWorkspaceTab === "maps" || currentWorkspaceTab === "journey") {
      return currentWorkspaceTab;
    }
    return lastExploreWorkspaceTab || "maps";
  }
  return normalized === "bible" ? null : normalized;
}

function rememberWorkspaceSubtab(tabId) {
  if (tabId === "notes" || tabId === "highlights") {
    lastNotesWorkspaceTab = tabId;
  } else if (tabId === "maps" || tabId === "journey") {
    lastExploreWorkspaceTab = tabId;
  }
}

function getCurrentWorkspaceTab() {
  const activeTab = document.querySelector(".workspace-tab[aria-selected='true']");
  return activeTab?.dataset.workspaceTab || null;
}

function normalizeAppSection(sectionId) {
  const normalized = String(sectionId || "bible").toLowerCase();
  if (normalized === "maps" || normalized === "journey") {
    return "explore";
  }
  if (["bible", "ask", "notes", "studies", "explore"].includes(normalized)) {
    return normalized;
  }
  return "bible";
}

function isCompactViewport() {
  return window.matchMedia(`(max-width: ${TABLET_BREAKPOINT}px)`).matches;
}

function readAppSectionPreference() {
  try {
    const saved = window.localStorage.getItem(APP_SECTION_STORAGE_KEY);
    const legacySaved = window.localStorage.getItem(LEGACY_MOBILE_SECTION_STORAGE_KEY);
    return normalizeAppSection(saved || legacySaved || "bible");
  } catch (_error) {
    return "bible";
  }
}

function persistAppSection(sectionId) {
  try {
    window.localStorage.setItem(APP_SECTION_STORAGE_KEY, normalizeAppSection(sectionId));
  } catch (_error) {
    // Ignore storage errors in restricted environments.
  }
}

function resolveInitialAppSection(savedSection) {
  const saved = normalizeAppSection(savedSection || "bible");
  return saved;
}

function initializeTheme() {
  const toggles = Array.from(document.querySelectorAll("[data-theme-toggle]"));
  if (toggles.length === 0) {
    return;
  }
  const savedTheme = readThemePreference();
  applyTheme(savedTheme, { persist: false });
  for (const toggle of toggles) {
    toggle.addEventListener("click", toggleTheme);
  }
}

function initializeReaderMode() {
  const toggles = Array.from(document.querySelectorAll("[data-reader-mode-toggle]"));
  if (toggles.length === 0) {
    return;
  }
  const savedMode = readReaderModePreference();
  applyReaderMode(savedMode, { persist: false });
  for (const toggle of toggles) {
    toggle.addEventListener("click", toggleReaderMode);
  }
}

function initializeWorkspaceExpansion() {
  const toggles = Array.from(document.querySelectorAll("[data-workspace-expand-toggle]"));
  if (toggles.length === 0) {
    return;
  }
  applyWorkspaceExpansion(false);
  for (const toggle of toggles) {
    toggle.addEventListener("click", toggleWorkspaceExpansion);
  }
}

function applyWorkspaceExpansion(enabled) {
  const nextEnabled = Boolean(enabled);
  document.body.classList.toggle("workspace-expanded", nextEnabled);
  if (nextEnabled) {
    closeWorkspaceDrawer();
  } else if (isCompactViewport()) {
    closeWorkspaceDrawer();
  }
  const toggles = document.querySelectorAll("[data-workspace-expand-toggle]");
  for (const toggle of toggles) {
    setControlLabel(
      toggle,
      nextEnabled ? "Collapse" : "Expand",
      nextEnabled ? "Collapse workspace" : "Expand workspace"
    );
    setControlStatus(toggle, `Current value: ${nextEnabled ? "Expanded" : "Collapsed"}`);
    toggle.setAttribute("aria-pressed", String(nextEnabled));
    toggle.setAttribute("aria-expanded", String(nextEnabled));
  }
  syncReaderControlsSheetAvailability();
}

function toggleWorkspaceExpansion() {
  applyWorkspaceExpansion(!document.body.classList.contains("workspace-expanded"));
}

function revealAnswerPanel(answerPanel) {
  if (!answerPanel || !isCompactViewport()) {
    return;
  }
  window.requestAnimationFrame(() => {
    if (answerPanel.isConnected) {
      answerPanel.scrollIntoView({ block: "start", behavior: "smooth" });
    }
  });
}

function expandWorkspaceForMobileAnswer() {
  if (!isCompactViewport()) {
    return;
  }
  if (document.body.classList.contains("workspace-expanded")) {
    return;
  }
  applyWorkspaceExpansion(true);
}

function addMobileAnswerCloseControl(answerPanel) {
  if (!answerPanel || !isCompactViewport()) {
    return;
  }
  if (answerPanel.querySelector("[data-mobile-answer-close]")) {
    return;
  }
  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "secondary mobile-answer-close";
  closeButton.textContent = "×";
  closeButton.setAttribute("aria-label", "Close answer and return to the reader");
  closeButton.setAttribute("title", "Close answer");
  closeButton.setAttribute("data-testid", "mobile-answer-close");
  closeButton.setAttribute("data-mobile-answer-close", "true");
  closeButton.addEventListener("click", closeMobileAnswerView);
  answerPanel.insertAdjacentElement("afterbegin", closeButton);
}

function closeMobileAnswerView() {
  if (!isCompactViewport()) {
    return;
  }
  applyWorkspaceExpansion(false);
}

function readReaderModePreference() {
  try {
    const saved = window.localStorage.getItem(READER_MODE_STORAGE_KEY);
    if (saved === "on" || saved === "off") {
      return saved === "on";
    }
  } catch (_error) {
    return false;
  }
  return false;
}

function applyReaderMode(enabled, options = {}) {
  const nextEnabled = Boolean(enabled);
  document.body.classList.toggle("reader-mode", nextEnabled);
  if (nextEnabled) {
    closeWorkspaceDrawer();
  }
  const toggles = document.querySelectorAll("[data-reader-mode-toggle]");
  for (const toggle of toggles) {
    setControlLabel(toggle, nextEnabled ? "Full view" : "Reader mode");
    setControlStatus(toggle, `Current value: ${nextEnabled ? "On" : "Off"}`);
    toggle.setAttribute("aria-pressed", String(nextEnabled));
  }
  if (options.persist !== false) {
    try {
      window.localStorage.setItem(READER_MODE_STORAGE_KEY, nextEnabled ? "on" : "off");
    } catch (_error) {
      // Ignore storage errors in restricted environments.
    }
  }
}

function toggleReaderMode() {
  applyReaderMode(!document.body.classList.contains("reader-mode"));
}

function readThemePreference() {
  try {
    const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === "light" || saved === "dark") {
      return saved;
    }
  } catch (_error) {
    return "light";
  }
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme, options = {}) {
  const nextTheme = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = nextTheme;
  const toggles = document.querySelectorAll("[data-theme-toggle]");
  const isDark = nextTheme === "dark";
  for (const toggle of toggles) {
    setControlLabel(toggle, isDark ? "Light mode" : "Dark mode");
    setControlStatus(toggle, `Current value: ${isDark ? "Dark" : "Light"}`);
    toggle.setAttribute("aria-pressed", String(isDark));
  }
  if (options.persist !== false) {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    } catch (_error) {
      // Ignore storage errors in restricted environments.
    }
  }
}

function toggleTheme() {
  const currentTheme = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  applyTheme(currentTheme === "dark" ? "light" : "dark");
}

function setControlLabel(control, compactLabel, fallbackLabel = compactLabel) {
  const label = control.querySelector("[data-control-label]");
  if (label) {
    label.textContent = compactLabel;
    return;
  }
  control.textContent = fallbackLabel;
}

function setControlStatus(control, text) {
  const status = control.querySelector("[data-control-status]");
  if (status) {
    status.textContent = text;
  }
}

function initializeReaderControlsSheet() {
  const sheet = document.querySelector("[data-reader-controls-sheet]");
  const triggers = Array.from(document.querySelectorAll("[data-reader-controls-trigger]"));
  if (!sheet || triggers.length === 0) {
    return;
  }

  for (const trigger of triggers) {
    trigger.addEventListener("click", () => openReaderControlsSheet(trigger));
  }

  sheet.querySelectorAll("[data-reader-controls-close]").forEach((button) => {
    button.addEventListener("click", closeReaderControlsSheet);
  });

  sheet.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeReaderControlsSheet();
  });

  sheet.addEventListener("click", (event) => {
    if (event.target === sheet) {
      closeReaderControlsSheet();
      return;
    }
    const action = event.target.closest("[data-theme-toggle], [data-reader-mode-toggle], [data-workspace-expand-toggle]");
    if (action && sheet.contains(action) && !action.disabled) {
      window.setTimeout(closeReaderControlsSheet, 0);
    }
  });

  sheet.addEventListener("close", () => {
    document.body.classList.remove("reader-controls-sheet-open");
    if (readerControlsTrigger?.isConnected) {
      readerControlsTrigger.focus();
    }
    readerControlsTrigger = null;
  });

  syncReaderControlsSheetAvailability();
}

function openReaderControlsSheet(trigger) {
  const sheet = document.querySelector("[data-reader-controls-sheet]");
  if (!sheet) {
    return;
  }
  readerControlsTrigger = trigger || document.activeElement;
  syncReaderControlsSheetAvailability();
  if (sheet.open) {
    return;
  }
  document.body.classList.add("reader-controls-sheet-open");
  if (typeof sheet.showModal === "function") {
    sheet.showModal();
  } else {
    sheet.setAttribute("open", "");
  }
}

function closeReaderControlsSheet() {
  const sheet = document.querySelector("[data-reader-controls-sheet]");
  if (!sheet || !sheet.open) {
    return;
  }
  if (typeof sheet.close === "function") {
    sheet.close();
  } else {
    sheet.removeAttribute("open");
    document.body.classList.remove("reader-controls-sheet-open");
    if (readerControlsTrigger?.isConnected) {
      readerControlsTrigger.focus();
    }
    readerControlsTrigger = null;
  }
}

function syncReaderControlsSheetAvailability() {
  const compact = isCompactViewport();
  const activeSection = normalizeAppSection(appSection || document.body.dataset.appSection || "bible");
  const workspaceUnavailable = compact && activeSection === "bible";
  document.querySelectorAll("[data-reader-settings-workspace]").forEach((button) => {
    button.disabled = workspaceUnavailable;
    button.setAttribute("aria-disabled", String(workspaceUnavailable));
    const hint = button.querySelector("[data-control-hint]");
    if (!hint) {
      return;
    }
    hint.hidden = !workspaceUnavailable;
    hint.textContent = workspaceUnavailable ? "Open Ask, Notes, Studies, or Explore first." : "";
  });
}

function workspaceTabsForSection(sectionId) {
  const normalized = normalizeAppSection(sectionId);
  if (normalized === "ask" || normalized === "bible") {
    return ["ask"];
  }
  if (normalized === "notes") {
    return ["notes", "highlights"];
  }
  if (normalized === "studies") {
    return ["saved"];
  }
  if (normalized === "explore") {
    return ["maps", "journey"];
  }
  return ["ask"];
}

function syncWorkspaceTabsForSection(sectionId) {
  const workspace = document.querySelector("[data-workspace-tabs]");
  if (!workspace) {
    return;
  }
  const visibleTabs = new Set(workspaceTabsForSection(sectionId));
  let visibleCount = 0;
  workspace.querySelectorAll("[data-workspace-tab]").forEach((tab) => {
    const isVisible = visibleTabs.has(tab.dataset.workspaceTab);
    tab.hidden = !isVisible;
    tab.tabIndex = isVisible && tab.getAttribute("aria-selected") === "true" ? 0 : -1;
    if (isVisible) {
      visibleCount += 1;
    }
  });
  const currentWorkspaceTab = getCurrentWorkspaceTab();
  if (!currentWorkspaceTab || !visibleTabs.has(currentWorkspaceTab)) {
    const fallbackTab = appSectionToWorkspaceTab(sectionId);
    if (fallbackTab) {
      setActiveWorkspaceTab(fallbackTab);
    }
  }
  const tabBar = workspace.querySelector("[data-workspace-tab-bar]");
  if (tabBar) {
    tabBar.hidden = visibleCount <= 1;
  }
}

function setActiveWorkspaceTab(tabId) {
  const workspace = document.querySelector("[data-workspace-tabs]");
  if (!workspace || !tabId) {
    return false;
  }
  const tabs = Array.from(workspace.querySelectorAll("[data-workspace-tab]"));
  const nextTab = tabs.find((tab) => tab.dataset.workspaceTab === tabId);
  if (!nextTab) {
    return false;
  }
  workspace.querySelectorAll("[data-workspace-tab]").forEach((tab) => {
    const isActive = tab.dataset.workspaceTab === tabId;
    tab.setAttribute("aria-selected", String(isActive));
    tab.tabIndex = isActive && !tab.hidden ? 0 : -1;
  });
  workspace.querySelectorAll("[data-workspace-pane]").forEach((pane) => {
    pane.hidden = pane.dataset.workspacePane !== tabId;
  });
  return true;
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
  return fetch(resolveBackendUrl(url), options).then(async (response) => {
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
  return fetch(resolveBackendUrl(url), options).then(async (response) => {
    const data = await response.text();
    if (!response.ok) {
      throw new Error(data || fallbackMessage);
    }
    return data;
  });
}

function resolveBackendUrl(url) {
  if (typeof BHF_HTTP.resolveUrl === "function") {
    return BHF_HTTP.resolveUrl(url);
  }
  const raw = String(url || "");
  if (/^(?:[a-z]+:)?\/\//i.test(raw) || raw.startsWith("data:") || raw.startsWith("blob:")) {
    return raw;
  }
  const base = String(BHF_RUNTIME.apiBaseUrl || "").replace(/\/+$/, "");
  if (!base) {
    return raw;
  }
  if (raw.startsWith("/")) {
    return `${base}${raw}`;
  }
  return `${base}/${raw}`;
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
  if (!setActiveWorkspaceTab(tabId)) {
    return;
  }
  document.dispatchEvent(
    new CustomEvent("bhf:workspace-tab-changed", {
      detail: { tabId },
    })
  );
}

function setWorkspaceDrawerOpen(open) {
  const panel = document.querySelector("#study-panel");
  const nextOpen = Boolean(open);
  document.body.classList.toggle("workspace-drawer-open", nextOpen);
  if (panel) {
    panel.classList.toggle("is-open", nextOpen);
  }
}

function syncMapWorkspaceEmptyState() {
  const mapPanel = document.querySelector("#map-panel");
  const emptyState = document.querySelector("[data-map-pane-empty]");
  if (!emptyState) {
    return;
  }
  emptyState.hidden = Boolean(mapPanel) && !mapPanel.hidden;
  if (emptyState.hidden) {
    return;
  }
  const button = emptyState.querySelector("[data-open-map-browser]");
  if (button && !button.dataset.bound) {
    button.dataset.bound = "true";
    button.addEventListener("click", () => openMapPanel({ mode: "browse" }));
  }
}

function closeWorkspaceDrawer() {
  const panel = document.querySelector("#study-panel");
  document.body.classList.remove("workspace-drawer-open");
  if (panel) {
    panel.classList.remove("is-open");
  }
}

function populateChapterOptions(bookSelect, chapterSelect) {
  const selected = bookSelect.selectedOptions[0] || bookSelect.options[0];
  const chapterCount = Number(selected?.dataset.chapters || 1);
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
    currentNotes = [];
    currentHighlights = [];
    renderChapter(data);
    clearReaderSearchState();
    syncAskFields();
    updateChapterNavigationState();
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

function clearReaderSearchState() {
  if (typeof clearBibleSearchResults === "function") {
    clearBibleSearchResults();
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

function goToNextChapter() {
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  if (!bookSelect || !chapterSelect) {
    return;
  }
  const selectedBook = bookSelect.selectedOptions[0] || bookSelect.options[0];
  const chapterCount = Number(selectedBook?.dataset.chapters || 0);
  const currentChapterNumber = Number(chapterSelect.value || "0");
  if (!chapterCount || !currentChapterNumber || currentChapterNumber >= chapterCount) {
    return;
  }
  const nextChapter = currentChapterNumber + 1;
  chapterSelect.value = String(nextChapter);
  loadReaderChapter(bookSelect.value, nextChapter);
}

function goToPreviousChapter() {
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  if (!bookSelect || !chapterSelect) {
    return;
  }
  const currentChapterNumber = Number(chapterSelect.value || "0");
  if (!currentChapterNumber || currentChapterNumber <= 1) {
    return;
  }
  const previousChapter = currentChapterNumber - 1;
  chapterSelect.value = String(previousChapter);
  loadReaderChapter(bookSelect.value, previousChapter);
}

function parsePassageReference(reference) {
  const rawReference = String(reference || "").trim();
  if (!rawReference) {
    return null;
  }

  const chapterMatch = rawReference.match(/^(?<book>.+?)\s+(?<chapter>\d+)(?::(?<verseStart>\d+)(?:-(?<verseEnd>\d+))?|-(?<chapterEnd>\d+))?$/);
  if (!chapterMatch?.groups) {
    return {
      book: rawReference,
      chapter: 1,
      verseStart: null,
      verseEnd: null,
      reference: rawReference,
    };
  }

  const chapter = Number(chapterMatch.groups.chapter);
  const verseStart = chapterMatch.groups.verseStart ? Number(chapterMatch.groups.verseStart) : null;
  const verseEnd = chapterMatch.groups.verseEnd ? Number(chapterMatch.groups.verseEnd) : verseStart;

  return {
    book: chapterMatch.groups.book.trim(),
    chapter: Number.isFinite(chapter) && chapter > 0 ? chapter : 1,
    verseStart,
    verseEnd,
    reference: rawReference,
  };
}

async function openPassageReference(reference) {
  const parsed = parsePassageReference(reference);
  if (!parsed) {
    return false;
  }
  await navigateToPassage(parsed.book, parsed.chapter, parsed.verseStart, parsed.verseEnd);
  return true;
}

function renderChapter(data) {
  const reader = document.querySelector("#chapter-reader");
  const header = document.createElement("div");
  header.className = "reader-chapter-header";

  const passageHeading = document.createElement("div");
  passageHeading.className = "reader-passage-heading";

  const heading = document.createElement("h3");
  heading.textContent = `${data.book} ${data.chapter}`;

  const translationBadge = document.createElement("span");
  translationBadge.className = "reader-translation-badge";
  translationBadge.textContent = "ASV";
  translationBadge.setAttribute("aria-label", "Translation: ASV");

  passageHeading.appendChild(heading);
  passageHeading.appendChild(translationBadge);

  header.appendChild(passageHeading);

  const paragraph = document.createElement("p");
  paragraph.className = "chapter-text";
  for (const verse of data.verses) {
    const verseSpan = document.createElement("span");
    verseSpan.className = "verse";
    verseSpan.dataset.verse = String(verse.verse);

    const number = document.createElement("button");
    number.type = "button";
    number.className = "verse-number";
    number.dataset.verseSelect = "true";
    number.textContent = String(verse.verse);
    number.setAttribute("aria-label", `Select ${data.book} ${data.chapter}:${verse.verse}`);

    const actions = document.createElement("button");
    actions.type = "button";
    actions.className = "secondary verse-actions-button";
    actions.dataset.verseActions = "true";
    actions.textContent = "⋮";
    actions.setAttribute("aria-label", "Verse actions");
    actions.title = `Verse actions for ${data.book} ${data.chapter}:${verse.verse}`;

    const indicators = document.createElement("span");
    indicators.className = "verse-state-indicators";
    indicators.dataset.verseIndicators = "true";

    const text = document.createElement("span");
    text.className = "verse-text";
    text.textContent = verse.text + " ";

    verseSpan.appendChild(number);
    verseSpan.appendChild(actions);
    verseSpan.appendChild(indicators);
    verseSpan.appendChild(text);
    paragraph.appendChild(verseSpan);
  }
  reader.innerHTML = "";
  reader.appendChild(header);
  reader.appendChild(paragraph);
  const footer = document.createElement("div");
  footer.className = "reader-chapter-footer reader-next-chapter-footer";
  footer.appendChild(createChapterNavButton("prev", "◀ Previous Chapter"));
  footer.appendChild(createChapterNavButton("next", "Next Chapter ▶"));
  reader.appendChild(footer);
}

function createChapterNavButton(direction, label) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `secondary reader-${direction}-chapter`;
  if (direction === "prev") {
    button.dataset.prevChapter = "";
    button.setAttribute("aria-label", "Previous chapter");
    button.title = "Previous chapter";
  } else {
    button.dataset.nextChapter = "";
    button.setAttribute("aria-label", "Next chapter");
    button.title = "Next chapter";
  }
  button.textContent = label;
  return button;
}

function handleReaderActionButtonClick(event) {
  const button = event.target.closest("[data-verse-actions]");
  const verseSelect = event.target.closest("[data-verse-select]");
  if (!button && !verseSelect) {
    return;
  }
  const verse = (button || verseSelect).closest("[data-verse]");
  if (!verse || !currentChapter) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();

  if (verseSelect) {
    const context = contextFromVerse(verse);
    if (context) {
      clearDocumentSelection();
      applySelectionContext(context);
    }
    return;
  }

  const context = contextForVerseAction(verse);
  if (!context) {
    return;
  }
  contextMenuState = context;
  applySelectionContext(context);
  const rect = button.getBoundingClientRect();
  showContextMenu(rect.left + rect.width / 2, rect.bottom + 8, context);
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

  const context = contextForVerseAction(verse);
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
  const context = contextForVerseAction(readerLongPressState.verse);
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

function contextForVerseAction(verse) {
  const verseNumber = Number(verse?.dataset?.verse || "0");
  const documentContext = selectionContextFromDocument();
  if (contextIncludesVerse(documentContext, verseNumber)) {
    return documentContext;
  }
  if (contextIncludesVerse(currentSelection, verseNumber)) {
    return currentSelection;
  }
  return contextFromVerse(verse);
}

function contextIncludesVerse(context, verseNumber) {
  if (!context || !verseNumber) {
    return false;
  }
  return Number(context.startVerse) <= verseNumber && verseNumber <= Number(context.endVerse || context.startVerse);
}

function showContextMenu(x, y, context) {
  const menu = document.querySelector("#reader-context-menu");
  if (!menu) {
    return;
  }
  const isSelection = Boolean(context.isSelection);
  const isHighlighted = isContextHighlighted(context);
  setContextLabel("ask_bhf", "Ask BHF");
  setContextLabel("ancient_context", isSelection ? "Ancient Context" : "Ancient Context");
  setContextLabel("literary_context", isSelection ? "Literary Context" : "Literary Context");
  setContextLabel("cross_references", isSelection ? "Cross References" : "Cross References");
  setContextLabel("related_ot_themes", isSelection ? "Related OT Themes" : "Related OT Themes");
  setContextLabel("fulfillment_nt", isSelection ? "Fulfillment in the NT" : "Fulfillment in the NT");
  setContextLabel("compare_translations", isSelection ? "Compare Translations" : "Compare Translations");
  setContextLabel("timeline", isSelection ? "Timeline" : "Timeline");
  setContextLabel("ask_location", isSelection ? "Ask about this location" : "Ask about this location");
  setContextLabel("open_map_panel", isSelection ? "Maps" : "Maps");
  setContextLabel("save_map_study", "Save map study");
  setContextLabel("map_note", "Add map note");
  setContextLabel("compare_archaeology", "Compare with archaeology");
  setContextLabel("related_passages", "View related passages");
  setContextLabel("view_historical_layer", "View historical layer");
  setContextLabel("save_study", "Save Study");
  setContextLabel("note", isSelection ? "Add Note" : "Add Note");
  setContextLabel("highlight", isHighlighted ? "Remove Highlight" : (isSelection ? "Highlight Selection" : "Highlight Verse"));
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
  const actionType = resolveContextAction(button.dataset.contextAction, contextMenuState);
  const context = contextMenuState;
  hideContextMenu();
  await dispatchStudyAction(createStudyAction(actionType, context));
}

function resolveContextAction(actionType, context) {
  if (actionType === "highlight" && isContextHighlighted(context)) {
    return "remove_highlight";
  }
  return actionType;
}

function createStudyAction(type, context) {
  return {
    type,
    book: context.book,
    chapter: Number(context.chapter),
    verseStart: Number(context.startVerse),
    verseEnd: Number(context.endVerse || context.startVerse),
    selectedText: context.text || "",
    isSelection: Boolean(context.isSelection),
    sourceTranslation: "ASV"
  };
}

async function dispatchStudyAction(studyAction) {
  applyStudyActionContext(studyAction);
  if (studyAction.type === "ask_bhf") {
    activateWorkspaceTab("ask");
    setFormValue("ask_mode", "");
    setFormValue("study_action", "");
    setMapContextValue("");
    const question = document.querySelector('.ask-form [name="question"]');
    if (question) {
      question.focus();
    }
  } else if (BHF_STUDY_ACTIONS.has(studyAction.type)) {
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
  } else if (studyAction.type === "remove_highlight") {
    await removeHighlightsForContext(studyAction);
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
    isSelection: Boolean(studyAction.isSelection) || studyAction.verseStart !== studyAction.verseEnd
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

function closeContextMenuOnReaderScroll(event) {
  const menu = document.querySelector("#reader-context-menu");
  if (menu && menu.contains(event.target)) {
    return;
  }
  hideContextMenu();
}

function hideContextMenu() {
  const menu = document.querySelector("#reader-context-menu");
  if (menu) {
    menu.hidden = true;
  }
  contextMenuState = null;
}

function clearDocumentSelection() {
  const selection = window.getSelection();
  if (selection) {
    selection.removeAllRanges();
  }
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

function isContextHighlighted(context) {
  if (!context || !currentHighlights.length) {
    return false;
  }
  const startVerse = Number(context.startVerse || context.verseStart || 0);
  const endVerse = Number(context.endVerse || context.verseEnd || startVerse);
  if (!startVerse || !endVerse) {
    return false;
  }
  for (let verseNumber = startVerse; verseNumber <= endVerse; verseNumber += 1) {
    if (!currentHighlights.some((highlight) => highlightContainsVerse(highlight, verseNumber))) {
      return false;
    }
  }
  return true;
}

function highlightsForContext(context) {
  if (!context || !currentHighlights.length) {
    return [];
  }
  const startVerse = Number(context.startVerse || context.verseStart || 0);
  const endVerse = Number(context.endVerse || context.verseEnd || startVerse);
  if (!startVerse || !endVerse) {
    return [];
  }
  return currentHighlights.filter((highlight) => rangesOverlap(
    startVerse,
    endVerse,
    Number(highlight.start_verse),
    Number(highlight.end_verse || highlight.start_verse)
  ));
}

function notesForVerse(verseNumber) {
  return currentNotes.filter((note) => highlightContainsVerse(note, verseNumber));
}

function highlightsForVerse(verseNumber) {
  return currentHighlights.filter((highlight) => highlightContainsVerse(highlight, verseNumber));
}

function highlightContainsVerse(record, verseNumber) {
  const startVerse = Number(record.start_verse || record.verseStart || 0);
  const endVerse = Number(record.end_verse || record.verseEnd || startVerse);
  return Boolean(startVerse && endVerse && startVerse <= verseNumber && verseNumber <= endVerse);
}

function rangesOverlap(startA, endA, startB, endB) {
  return startA <= endB && startB <= endA;
}

function applyVerseStateIndicatorsToReader() {
  const reader = document.querySelector("#chapter-reader");
  if (!reader) {
    return;
  }
  reader.querySelectorAll("[data-verse]").forEach((verse) => {
    const verseNumber = Number(verse.dataset.verse);
    const indicatorContainer = verse.querySelector("[data-verse-indicators]");
    if (!indicatorContainer) {
      return;
    }
    const notes = notesForVerse(verseNumber);
    const highlights = highlightsForVerse(verseNumber);
    const highlightColors = Array.from(new Set(highlights.map((highlight) => String(highlight.color || "").trim()).filter(Boolean)));

    verse.classList.toggle("has-notes", notes.length > 0);
    verse.classList.toggle("has-highlights", highlightColors.length > 0);
    indicatorContainer.innerHTML = "";
    const indicatorLabels = [];

    if (notes.length > 0) {
      const noteIndicator = document.createElement("span");
      noteIndicator.className = "verse-state-indicator verse-state-note";
      noteIndicator.title = notes.length === 1 ? "Has note" : `Has ${notes.length} notes`;
      noteIndicator.textContent = "N";
      noteIndicator.setAttribute("aria-hidden", "true");
      indicatorLabels.push(notes.length === 1 ? "Has note" : `Has ${notes.length} notes`);
      indicatorContainer.appendChild(noteIndicator);
    }

    highlightColors.forEach((color) => {
      const highlightIndicator = document.createElement("span");
      highlightIndicator.className = `verse-state-indicator verse-state-highlight highlight-${color}`;
      highlightIndicator.dataset.highlightColor = color;
      highlightIndicator.title = `${color} highlight`;
      highlightIndicator.setAttribute("aria-hidden", "true");
      indicatorLabels.push(`${color} highlight`);
      indicatorContainer.appendChild(highlightIndicator);
    });
    if (indicatorLabels.length > 0) {
      indicatorContainer.setAttribute("role", "img");
      indicatorContainer.setAttribute("aria-label", indicatorLabels.join(", "));
    } else {
      indicatorContainer.removeAttribute("role");
      indicatorContainer.removeAttribute("aria-label");
    }
  });
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

function updateChapterNavigationState() {
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  const nextButtons = document.querySelectorAll("[data-next-chapter]");
  const prevButtons = document.querySelectorAll("[data-prev-chapter]");
  if (!bookSelect || !chapterSelect || (nextButtons.length === 0 && prevButtons.length === 0)) {
    return;
  }
  const selectedBook = bookSelect.selectedOptions[0] || bookSelect.options[0];
  const chapterCount = Number(selectedBook?.dataset.chapters || chapterSelect.options.length || 0);
  const currentChapterNumber = Number(chapterSelect.value || "0");
  const available = Boolean(chapterCount && currentChapterNumber && currentChapterNumber < chapterCount);
  const canGoBack = Boolean(currentChapterNumber && currentChapterNumber > 1);
  nextButtons.forEach((button) => {
    button.disabled = !available;
    button.setAttribute(
      "aria-label",
      available ? `Go to chapter ${currentChapterNumber + 1}` : "No next chapter available"
    );
    button.title = available ? "Next chapter" : "No next chapter available";
  });
  prevButtons.forEach((button) => {
    button.disabled = !canGoBack;
    button.setAttribute(
      "aria-label",
      canGoBack ? `Go to chapter ${currentChapterNumber - 1}` : "No previous chapter available"
    );
    button.title = canGoBack ? "Previous chapter" : "No previous chapter available";
  });
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
  if (isCompactViewport()) {
    setWorkspaceDrawerOpen(true);
  }
  const panel = document.querySelector("#map-panel");
  if (panel) {
    panel.hidden = false;
  }
  syncMapWorkspaceEmptyState();
  if (window.BHFMaps && typeof window.BHFMaps.openMapPanel === "function") {
    const hasPassageContext = Boolean(context && (context.book || context.chapter || context.savedMapStudy));
    window.BHFMaps.openMapPanel(hasPassageContext ? context : { mode: "browse" });
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
