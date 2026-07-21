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
const BHF_TRANSLATION_STORAGE_KEY = "bhf-reader-translation";
const BHF_INSTALLED_TRANSLATIONS_STORAGE_KEY = "bhf-installed-translations";
const BHF_TRANSLATION_DOWNLOAD_METADATA_KEY = "bhf-translation-download-metadata";
const BHF_TRANSLATION_IMPORT_PREFERENCE_KEY = "bhf-translation-import-preference";
const BHF_IMPORTABLE_TRANSLATION_IDS = new Set(["kjv", "niv", "esv", "csb", "nasb", "lsb", "nlt"]);
const BHF_STUDY_ACTIONS = new Set([
  "full_context",
  "historical_context",
  "cultural_context",
  "original_audience",
  "covenant_context",
  // Legacy action values remain accepted for saved links and older clients.
  "ancient_context",
  "literary_context",
  "cross_references",
  "related_ot_themes",
  "fulfillment_nt",
  "compare_translations",
  "timeline",
  "word_study",
  "people",
  "places",
  "themes",
  "ask_location",
  "compare_archaeology",
  "related_passages",
]);

const BHF_DETERMINISTIC_STUDY_ACTIONS = new Set([
  "full_context",
  "historical_context",
  "cultural_context",
  "original_audience",
  "covenant_context",
  "literary_context",
  "cross_references",
  "related_ot_themes",
  "word_study",
  "people",
  "places",
  "themes",
]);

const BHF_STUDY_ACTION_ALIASES = {
  ancient_context: "cultural_context",
  ancient_cultural_context: "cultural_context",
  related_ot_themes: "themes",
};

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
let latestDeterministicStudyResult = null;
let readerLongPressState = null;
let appSection = null;
let lastAskWorkspaceTab = "ask";
let lastNotesWorkspaceTab = "notes";
let lastExploreWorkspaceTab = "maps";
let readerControlsTrigger = null;
let translationCatalogState = null;
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
    setFormValue("deterministic_fact_packet", "");
    setFormValue("ask_mode", "");
    setFormValue("study_action", "");
    setRunning(form, submitButton, false);
  }
});

async function initializeReader() {
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  const translationSelect = document.querySelector("[data-reader-translation]");
  const translationImportButton = document.querySelector("[data-reader-translation-import]");
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
  if (translationSelect) {
    try {
      translationCatalogState = await requestJson("/api/translations", {}, "Could not load translations.");
    } catch (_error) {
      translationCatalogState = null;
    }
    if (translationCatalogState?.default_translation) {
      setSelectedTranslationId(translationCatalogState.default_translation);
    }
    syncTranslationSelectOptions();
    translationSelect.value = selectedTranslationId();
  }
  await loadReaderChapter(bookSelect.value || defaultBook, chapterSelect.value || defaultChapter);

  bookSelect.addEventListener("change", async () => {
    populateChapterOptions(bookSelect, chapterSelect);
    chapterSelect.value = "1";
    await loadReaderChapter(bookSelect.value, chapterSelect.value);
  });
  chapterSelect.addEventListener("change", async () => {
    await loadReaderChapter(bookSelect.value, chapterSelect.value);
  });
  if (translationSelect) {
    translationSelect.addEventListener("change", async () => {
      const requestedTranslation = String(translationSelect.value || "asv").toLowerCase();
      try {
        const entry = translationCatalogEntry(requestedTranslation);
        if (entry?.install_mode === "direct_download" && !installedTranslationIds().has(requestedTranslation)) {
          await downloadTranslationFromGithub(requestedTranslation);
        } else if (entry?.install_mode === "licensed_provider" && !installedTranslationIds().has(requestedTranslation)) {
          await openTranslationSelector(translationSelect);
          translationSelect.value = selectedTranslationId();
          return;
        }
        setSelectedTranslationId(requestedTranslation);
        await loadReaderChapter(bookSelect.value, chapterSelect.value);
      } catch (error) {
        setSelectedTranslationId("asv");
        translationSelect.value = "asv";
        reader.innerHTML = errorHtml(error.message || "Could not download translation.");
      }
    });
  }
  if (translationImportButton) {
    translationImportButton.addEventListener("click", async () => {
      await openTranslationImportDialog();
    });
  }
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
  reader.addEventListener("click", handleTranslationSelectorClick);
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
  if (tabId === "ask" || tabId === "context") {
    return "ask";
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
    const currentWorkspaceTab = getCurrentWorkspaceTab();
    if (currentWorkspaceTab === "ask" || currentWorkspaceTab === "context") {
      return currentWorkspaceTab;
    }
    return lastAskWorkspaceTab || "ask";
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
  if (tabId === "ask" || tabId === "context") {
    lastAskWorkspaceTab = tabId;
  } else if (tabId === "notes" || tabId === "highlights") {
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
    return ["ask", "context"];
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
  const translationId = selectedTranslationId();
  reader.setAttribute("aria-busy", "true");
  hideContextMenu();
  reader.innerHTML = `<p class="empty">Loading ${escapeHtml(currentTranslationAbbreviation())} text...</p>`;
  try {
    const params = new URLSearchParams({ translation: translationId });
    const data = await requestJson(`/api/bible/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}?${params.toString()}`, {}, "Could not load chapter.");
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
    if (translationId !== "asv") {
      setSelectedTranslationId("asv");
      await loadReaderChapter(book, chapter);
      return;
    }
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

  const translation = data.translation || {};
  const abbreviation = translation.id || currentTranslationAbbreviation();
  const translationBadge = document.createElement("button");
  translationBadge.type = "button";
  translationBadge.className = "reader-translation-badge";
  translationBadge.dataset.translationSelectorTrigger = "true";
  translationBadge.textContent = abbreviation;
  translationBadge.setAttribute("aria-label", `Translation: ${abbreviation}. Open translation selector.`);
  translationBadge.title = "Open translation selector";

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

function currentTranslationAbbreviation() {
  return currentChapter?.translation?.id || selectedTranslationId().toUpperCase();
}

async function handleTranslationSelectorClick(event) {
  const trigger = event.target.closest("[data-translation-selector-trigger]");
  if (!trigger) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  await openTranslationSelector(trigger);
}

async function openTranslationSelector(trigger) {
  const dialog = ensureTranslationSelectorDialog();
  dialog.hidden = false;
  document.body.classList.add("translation-selector-open");
  dialog.setAttribute("aria-busy", "true");
  dialog.querySelector("[data-translation-selector-body]").innerHTML = `<p class="empty">Loading translations...</p>`;
  try {
    translationCatalogState = await requestJson("/api/translations/catalog", {}, "Could not load translations.");
    renderTranslationSelector(translationCatalogState);
  } catch (error) {
    dialog.querySelector("[data-translation-selector-body]").innerHTML = errorHtml(error.message || "Could not load translations.");
  } finally {
    dialog.removeAttribute("aria-busy");
    const closeButton = dialog.querySelector("[data-close-translation-selector]");
    if (closeButton) {
      closeButton.focus();
    }
  }
  dialog.dataset.triggerSelector = trigger ? "reader" : "";
}

function ensureTranslationSelectorDialog() {
  let dialog = document.querySelector("[data-translation-selector]");
  if (dialog) {
    return dialog;
  }
  dialog = document.createElement("div");
  dialog.className = "translation-selector-overlay";
  dialog.dataset.translationSelector = "true";
  dialog.hidden = true;
  dialog.innerHTML = `
    <div class="translation-selector" role="dialog" aria-modal="true" aria-labelledby="translation-selector-title">
      <div class="translation-selector-header">
        <h2 id="translation-selector-title">Translations</h2>
        <button type="button" class="secondary icon-button" data-close-translation-selector aria-label="Close translation selector">×</button>
      </div>
      <div class="translation-selector-body" data-translation-selector-body></div>
    </div>
  `;
  dialog.addEventListener("click", (event) => {
    handleTranslationSelectorDialogClick(event);
    if (event.target === dialog || event.target.closest("[data-close-translation-selector]")) {
      closeTranslationSelector();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !dialog.hidden) {
      closeTranslationSelector();
    }
  });
  document.body.appendChild(dialog);
  return dialog;
}

function closeTranslationSelector() {
  const dialog = document.querySelector("[data-translation-selector]");
  if (dialog) {
    dialog.hidden = true;
  }
  document.body.classList.remove("translation-selector-open");
}

function renderTranslationSelector(state) {
  const body = document.querySelector("[data-translation-selector-body]");
  if (!body) {
    return;
  }
  const sections = translationCatalogWithLocalState(state).sections || {};
  body.innerHTML = "";
  body.appendChild(renderTranslationSection("Import Local XML", sections.import_local_xml || []));
  body.appendChild(renderTranslationSection("Installed", sections.installed || []));
  body.appendChild(renderTranslationSection("Available to Download", sections.available_to_download || []));
  body.appendChild(renderTranslationSection("Additional English Translations", sections.additional_english_translations || []));
}

function translationCatalogWithLocalState(state) {
  const catalog = Array.isArray(state?.catalog) ? state.catalog : [];
  const selectedId = selectedTranslationId();
  const sections = state?.sections || {};
  const installed = Array.isArray(sections.installed) ? sections.installed : [];
  const availableToDownload = Array.isArray(sections.available_to_download) ? sections.available_to_download : [];
  const licenseRequired = Array.isArray(sections.license_required) ? sections.license_required : Array.isArray(sections.additional_english_translations) ? sections.additional_english_translations : [];
  const installedById = new Set(installed.map((entry) => String(entry.id || "").toLowerCase()));
  const decoratedInstalled = installed.map((entry) => ({
    ...entry,
    selected: String(entry.id || "").toLowerCase() === selectedId,
    can_select: true,
    can_set_default: true,
    can_remove: !entry.bundled,
    can_download: false,
    status_label: entry.id === "asv" ? "Built in" : "Installed locally",
  }));
  const decoratedAvailable = availableToDownload.map((entry) => ({
    ...entry,
    selected: String(entry.id || "").toLowerCase() === selectedId,
    can_select: false,
    can_remove: false,
    can_download: true,
    status_label: entry.status_label || "Download for offline use",
  }));
  const decoratedLicense = licenseRequired.map((entry) => ({
    ...entry,
    selected: String(entry.id || "").toLowerCase() === selectedId,
    can_select: false,
    can_remove: false,
    can_download: false,
    can_import: true,
    status_label: "License required",
  }));
  const importableEntries = decoratedLicense.filter((entry) => !installedById.has(String(entry.id || "").toLowerCase()));

  return {
    ...state,
    sections: {
      import_local_xml: importableEntries,
      installed: decoratedInstalled,
      available_to_download: decoratedAvailable,
      additional_english_translations: decoratedLicense,
      license_required: decoratedLicense,
    },
  };
}

function installedTranslationIds() {
  const ids = new Set(["asv"]);
  if (translationCatalogState && Array.isArray(translationCatalogState.sections?.installed)) {
    for (const entry of translationCatalogState.sections.installed) {
      const id = String(entry.id || "").toLowerCase();
      if (id) {
        ids.add(id);
      }
    }
  }
  try {
    const stored = JSON.parse(readLocalStorageValue(BHF_INSTALLED_TRANSLATIONS_STORAGE_KEY) || "[]");
    if (Array.isArray(stored)) {
      for (const id of stored) {
        const normalized = String(id || "").toLowerCase();
        if (normalized) {
          ids.add(normalized);
        }
      }
    }
  } catch {
    return ids;
  }
  return ids;
}

function persistInstalledTranslationIds(ids) {
  const normalized = Array.from(ids)
    .map((id) => String(id || "").toLowerCase())
    .filter((id) => Boolean(id));
  if (!normalized.includes("asv")) {
    normalized.unshift("asv");
  }
  writeLocalStorageValue(BHF_INSTALLED_TRANSLATIONS_STORAGE_KEY, JSON.stringify(Array.from(new Set(normalized))));
}

function selectedTranslationId() {
  const fallback = "asv";
  const stored = String(readLocalStorageValue(BHF_TRANSLATION_STORAGE_KEY) || fallback).toLowerCase();
  return installedTranslationIds().has(stored) ? stored : fallback;
}

function setSelectedTranslationId(id) {
  const normalized = String(id || "asv").toLowerCase();
  const selected = installedTranslationIds().has(normalized) ? normalized : "asv";
  writeLocalStorageValue(BHF_TRANSLATION_STORAGE_KEY, selected);
  syncTranslationSelect(selected);
}

function readLocalStorageValue(key) {
  try {
    return window.localStorage?.getItem(key);
  } catch {
    return null;
  }
}

function writeLocalStorageValue(key, value) {
  try {
    window.localStorage?.setItem(key, value);
  } catch {
    return false;
  }
  return true;
}

async function handleTranslationSelectorDialogClick(event) {
  const download = event.target.closest("[data-translation-download]");
  const importer = event.target.closest("[data-translation-import]");
  const select = event.target.closest("[data-translation-select]");
  const remove = event.target.closest("[data-translation-remove]");
  if (!download && !importer && !select && !remove) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();

  if (download) {
    await downloadTranslationFromGithub(download.dataset.translationDownload);
    setSelectedTranslationId(download.dataset.translationDownload);
    renderTranslationSelector(translationCatalogState);
    closeTranslationSelector();
    await reloadCurrentReaderChapter();
    return;
  }
  if (select) {
    setSelectedTranslationId(select.dataset.translationSelect);
    closeTranslationSelector();
    await reloadCurrentReaderChapter();
    return;
  }
  const makeDefault = event.target.closest("[data-translation-make-default]");
  if (makeDefault) {
    await requestJson(
      "/api/settings/reader",
      {
        method: "PUT",
        headers: { "Accept": "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ default_translation: makeDefault.dataset.translationMakeDefault }),
      },
      "Could not update default translation."
    );
    setSelectedTranslationId(makeDefault.dataset.translationMakeDefault);
    renderTranslationSelector(translationCatalogState);
    closeTranslationSelector();
    await reloadCurrentReaderChapter();
    return;
  }
  if (importer) {
    closeTranslationSelector();
    await openTranslationImportDialog(importer.dataset.translationImport);
    return;
  }
  if (remove) {
    await removeInstalledTranslation(remove.dataset.translationRemove);
    renderTranslationSelector(translationCatalogState);
    await reloadCurrentReaderChapter();
  }
}

function installTranslation(id) {
  const normalized = String(id || "").toLowerCase();
  const ids = installedTranslationIds();
  ids.add(normalized);
  persistInstalledTranslationIds(ids);
  syncTranslationSelectOptions();
}

function installImportedTranslation(id) {
  const normalized = String(id || "").toLowerCase();
  if (!BHF_IMPORTABLE_TRANSLATION_IDS.has(normalized)) {
    return;
  }
  const ids = installedTranslationIds();
  ids.add(normalized);
  persistInstalledTranslationIds(ids);
  syncTranslationSelectOptions();
}

async function removeInstalledTranslation(id) {
  const normalized = String(id || "").toLowerCase();
  if (!normalized || normalized === "asv") {
    return;
  }
  await requestJson(
    `/api/translations/${encodeURIComponent(normalized)}`,
    {
      method: "DELETE",
      headers: { "Accept": "application/json" },
    },
    "Could not remove translation."
  );
  const selectedBeforeRemoval = selectedTranslationId();
  const ids = installedTranslationIds();
  ids.delete(normalized);
  persistInstalledTranslationIds(ids);
  if (selectedBeforeRemoval === normalized) {
    setSelectedTranslationId("asv");
  }
}

async function reloadCurrentReaderChapter() {
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  const book = bookSelect?.value || currentChapter?.book || "John";
  const chapter = chapterSelect?.value || currentChapter?.chapter || "1";
  await loadReaderChapter(book, chapter);
}

async function downloadTranslationFromGithub(id) {
  const normalized = String(id || "").toLowerCase();
  const metadata = await requestJson(
    `/api/translations/${encodeURIComponent(normalized)}/install`,
    {
      method: "POST",
      headers: { "Accept": "application/json" },
    },
    "Could not download translation."
  );
  installTranslation(normalized);
  persistTranslationDownloadMetadata(normalized, metadata);
  return metadata;
}

function persistTranslationDownloadMetadata(id, metadata) {
  let stored = {};
  try {
    stored = JSON.parse(readLocalStorageValue(BHF_TRANSLATION_DOWNLOAD_METADATA_KEY) || "{}");
  } catch {
    stored = {};
  }
  stored[String(id || "").toLowerCase()] = metadata;
  writeLocalStorageValue(BHF_TRANSLATION_DOWNLOAD_METADATA_KEY, JSON.stringify(stored));
}

function syncTranslationSelect(translationId = selectedTranslationId()) {
  syncTranslationSelectOptions();
  const translationSelect = document.querySelector("[data-reader-translation]");
  if (translationSelect && translationSelect.value !== translationId) {
    translationSelect.value = translationId;
  }
}

function syncTranslationSelectOptions() {
  const translationSelect = document.querySelector("[data-reader-translation]");
  if (!translationSelect) {
    return;
  }
  const state = translationCatalogState || {};
  const translations = Array.isArray(state.translations) ? state.translations : [];
  const selectedId = String(translationSelect.value || selectedTranslationId() || "asv").toLowerCase();
  translationSelect.replaceChildren();
  for (const entry of translations) {
    const id = String(entry.id || "").toLowerCase();
    if (!id) {
      continue;
    }
    const option = document.createElement("option");
    option.value = id;
    option.textContent = translationSelectOptionLabel(id, installedTranslationIds(), entry);
    translationSelect.appendChild(option);
  }

  translationSelect.value = translations.some((entry) => String(entry.id || "").toLowerCase() === selectedId)
    ? selectedId
    : selectedTranslationId();
  if (!translationSelect.options.length) {
    const fallbackOption = document.createElement("option");
    fallbackOption.value = "asv";
    fallbackOption.textContent = "ASV - American Standard Version";
    translationSelect.appendChild(fallbackOption);
    translationSelect.value = "asv";
  }
}

function translationSelectOptionLabel(translationId, installedIds = installedTranslationIds(), entry = null) {
  const normalized = String(translationId || "").toLowerCase();
  const resolved = entry || translationCatalogEntry(normalized);
  const abbreviation = resolved?.abbreviation || normalized.toUpperCase();
  const name = resolved?.name || abbreviation;
  if (normalized === "asv") {
    return `${abbreviation} - ${name}`;
  }
  if (resolved?.install_mode === "direct_download" && !installedIds.has(normalized)) {
    return `${abbreviation} - Download for offline use`;
  }
  if (resolved?.install_mode === "licensed_provider" && !installedIds.has(normalized)) {
    return `${abbreviation} - License required`;
  }
  return installedIds.has(normalized) ? `${abbreviation} - Installed locally` : `${abbreviation} - ${name}`;
}

async function importTranslationXml(id) {
  const normalized = String(id || "").toLowerCase();
  if (!BHF_IMPORTABLE_TRANSLATION_IDS.has(normalized)) {
    throw new Error("This translation cannot be imported.");
  }
  const form = document.querySelector("[data-translation-import-form]");
  const fileInput = form?.querySelector("[data-translation-import-file]");
  const file = fileInput?.files && fileInput.files.length ? fileInput.files[0] : null;
  if (!file) {
    throw new Error("Choose an XML file to import.");
  }
  const formData = new FormData();
  formData.set("confirmed", "true");
  formData.set("file", file);
  const result = await requestJson(
    `/api/translations/${encodeURIComponent(normalized)}/import`,
    {
      method: "POST",
      body: formData,
      headers: { "Accept": "application/json" },
    },
    "Could not import translation XML."
  );
  installImportedTranslation(normalized);
  setSelectedTranslationId(normalized);
  return result;
}

async function openTranslationImportDialog(translationId = null) {
  if (!translationCatalogState) {
    translationCatalogState = await requestJson("/api/translations/catalog", {}, "Could not load translations.");
  }
  const dialog = ensureTranslationImportDialog();
  const select = dialog.querySelector("[data-translation-import-id]");
  const normalized = BHF_IMPORTABLE_TRANSLATION_IDS.has(String(translationId || "").toLowerCase())
    ? String(translationId).toLowerCase()
    : translationImportPreference() || selectedTranslationId() || "asv";
  select.value = normalized;
  renderTranslationImportDialogDetails(normalized);
  dialog.hidden = false;
  document.body.classList.add("translation-selector-open");
  const fileInput = dialog.querySelector("[data-translation-import-file]");
  if (fileInput) {
    fileInput.value = "";
    fileInput.focus();
  }
}

function ensureTranslationImportDialog() {
  let dialog = document.querySelector("[data-translation-import-dialog]");
  if (dialog) {
    return dialog;
  }
  dialog = document.createElement("div");
  dialog.className = "translation-selector-overlay";
  dialog.dataset.translationImportDialog = "true";
  dialog.hidden = true;
  dialog.innerHTML = `
    <form class="translation-selector translation-import-dialog" data-translation-import-form role="dialog" aria-modal="true" aria-labelledby="translation-import-title">
      <div class="translation-selector-header">
        <h2 id="translation-import-title">Import XML</h2>
        <button type="button" class="secondary icon-button" data-close-translation-import aria-label="Close import dialog">×</button>
      </div>
      <div class="translation-selector-body">
        <label class="translation-import-field">
          <span>Translation</span>
          <select data-translation-import-id>
            <option value="niv">NIV - New International Version</option>
            <option value="esv">ESV - English Standard Version</option>
            <option value="csb">CSB - Christian Standard Bible</option>
            <option value="nasb">NASB - New American Standard Bible</option>
            <option value="lsb">LSB - Legacy Standard Bible</option>
            <option value="nlt">NLT - New Living Translation</option>
            <option value="kjv">KJV - King James Version</option>
          </select>
        </label>
        <div data-translation-import-details></div>
        <label class="translation-import-field">
          <span>XML file</span>
          <input type="file" accept=".xml,application/xml,text/xml" data-translation-import-file required>
        </label>
        <label class="check translation-import-confirm">
          <input type="checkbox" data-translation-import-confirm required>
          <span>I confirm that I obtained this XML file lawfully and have the right to use it on this device.</span>
        </label>
        <div class="translation-selector-entry-actions translation-import-actions">
          <button type="button" class="secondary" data-close-translation-import>Cancel</button>
          <button type="submit">Import local XML</button>
        </div>
      </div>
    </form>
  `;
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog || event.target.closest("[data-close-translation-import]")) {
      closeTranslationImportDialog();
    }
  });
  const select = dialog.querySelector("[data-translation-import-id]");
  select.addEventListener("change", () => {
    persistTranslationImportPreference(select.value);
    renderTranslationImportDialogDetails(select.value);
  });
  const fileInput = dialog.querySelector("[data-translation-import-file]");
  fileInput?.addEventListener("change", () => {
    const guessedTranslation = guessTranslationIdFromFilename(fileInput.files?.[0]?.name || "");
    if (guessedTranslation && select.value !== guessedTranslation) {
      select.value = guessedTranslation;
      renderTranslationImportDialogDetails(guessedTranslation);
    }
  });
  const form = dialog.querySelector("[data-translation-import-form]");
  form.addEventListener("submit", submitTranslationImportForm);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !dialog.hidden) {
      closeTranslationImportDialog();
    }
  });
  document.body.appendChild(dialog);
  return dialog;
}

function closeTranslationImportDialog() {
  const dialog = document.querySelector("[data-translation-import-dialog]");
  if (dialog) {
    dialog.hidden = true;
  }
  document.body.classList.remove("translation-selector-open");
}

function renderTranslationImportDialogDetails(translationId) {
  const dialog = document.querySelector("[data-translation-import-dialog]");
  const details = dialog?.querySelector("[data-translation-import-details]");
  if (!details) {
    return;
  }
  const entry = translationCatalogEntry(translationId);
  const abbreviation = entry?.abbreviation || String(translationId || "").toUpperCase();
  const name = entry?.name || abbreviation;
  details.innerHTML = "";
  const notice = document.createElement("p");
  notice.className = "translation-license-explanation";
  notice.textContent = "This import stays local to this BHF instance. BHF does not provide, distribute, upload, or verify the file.";
  details.appendChild(notice);
  const target = document.createElement("p");
  target.className = "translation-license-actions";
  target.textContent = `Import target: ${abbreviation} - ${name}`;
  details.appendChild(target);
  if (entry?.approved_source_url) {
    const source = document.createElement("p");
    source.className = "translation-license-actions";
    source.append("Approved source: ");
    const link = document.createElement("a");
    link.href = entry.approved_source_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "GitHub source";
    source.appendChild(link);
    details.appendChild(source);
  } else if (entry?.license_status === "copyrighted") {
    const warning = document.createElement("p");
    warning.className = "translation-license-explanation";
    warning.textContent = "No GitHub download link is provided for this copyrighted translation. Use only a legally obtained XML file.";
    details.appendChild(warning);
  }
}

function guessTranslationIdFromFilename(filename) {
  const normalized = String(filename || "")
    .toLowerCase()
    .split(/[\\/]/)
    .pop()
    .replace(/\.(xml|txt|json)$/u, "");
  if (!normalized) {
    return null;
  }
  const candidates = ["nasb", "csb", "esv", "lsb", "nlt", "niv", "kjv"];
  for (const id of candidates) {
    const tokenPattern = new RegExp(`(?:^|[^a-z0-9])${id}(?:[^a-z0-9]|$)`);
    if (tokenPattern.test(normalized) || normalized.includes(id)) {
      return id;
    }
  }
  return null;
}

function translationImportPreference() {
  const stored = String(readLocalStorageValue(BHF_TRANSLATION_IMPORT_PREFERENCE_KEY) || "").toLowerCase();
  return BHF_IMPORTABLE_TRANSLATION_IDS.has(stored) ? stored : null;
}

function persistTranslationImportPreference(id) {
  const normalized = String(id || "").toLowerCase();
  if (!BHF_IMPORTABLE_TRANSLATION_IDS.has(normalized)) {
    return;
  }
  writeLocalStorageValue(BHF_TRANSLATION_IMPORT_PREFERENCE_KEY, normalized);
}

function translationCatalogEntry(translationId) {
  const id = String(translationId || "").toLowerCase();
  const catalog = Array.isArray(translationCatalogState?.catalog) ? translationCatalogState.catalog : [];
  return catalog.find((entry) => String(entry.id || "").toLowerCase() === id);
}

async function submitTranslationImportForm(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const select = form.querySelector("[data-translation-import-id]");
  const confirmed = form.querySelector("[data-translation-import-confirm]");
  if (!confirmed?.checked) {
    return;
  }
  const submit = form.querySelector("button[type='submit']");
  submit.disabled = true;
  try {
    await importTranslationXml(select.value);
    closeTranslationImportDialog();
    await reloadCurrentReaderChapter();
  } catch (error) {
    const details = form.querySelector("[data-translation-import-details]");
    if (details) {
      details.insertAdjacentHTML("afterbegin", errorHtml(error.message || "Could not import translation XML."));
    }
  } finally {
    submit.disabled = false;
  }
}

function renderTranslationSection(title, entries) {
  const section = document.createElement("section");
  section.className = "translation-selector-section";
  const heading = document.createElement("h3");
  heading.textContent = title;
  section.appendChild(heading);
  if (!entries.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No translations in this section.";
    section.appendChild(empty);
    return section;
  }
  const list = document.createElement("div");
  list.className = "translation-selector-list";
  for (const entry of entries) {
    list.appendChild(renderTranslationEntry(entry));
  }
  section.appendChild(list);
  return section;
}

function renderTranslationEntry(entry) {
  const row = document.createElement("article");
  row.className = "translation-selector-entry";
  row.dataset.translationId = entry.id;

  const main = document.createElement("div");
  main.className = "translation-selector-entry-main";
  const title = document.createElement("h4");
  title.textContent = `${entry.abbreviation} — ${entry.status_label || entry.name}`;
  const subtitle = document.createElement("p");
  subtitle.textContent = entry.name;
  main.appendChild(title);
  main.appendChild(subtitle);
  if (entry.license_explanation) {
    const explanation = document.createElement("p");
    explanation.className = "translation-license-explanation";
    explanation.textContent = entry.license_explanation;
    main.appendChild(explanation);
  }
  if (entry.third_party_notice) {
    const notice = document.createElement("p");
    notice.className = "translation-license-explanation";
    notice.textContent = entry.third_party_notice;
    main.appendChild(notice);
  }
  if (entry.approved_source_url) {
    const source = document.createElement("p");
    source.className = "translation-license-actions";
    const link = document.createElement("a");
    link.href = entry.approved_source_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "GitHub source";
    source.appendChild(link);
    main.appendChild(source);
  }
  if (Array.isArray(entry.actions) && entry.actions.length) {
    const actions = document.createElement("p");
    actions.className = "translation-license-actions";
    actions.textContent = entry.actions.join(" · ");
    main.appendChild(actions);
  }

  const controls = document.createElement("div");
  controls.className = "translation-selector-entry-actions";
  if (entry.install_mode === "licensed_provider" || entry.availability === "license_required") {
    const lock = document.createElement("span");
    lock.className = "translation-license-indicator";
    lock.textContent = "License required";
    controls.appendChild(lock);
  }
  if (entry.can_import || entry.availability === "license_required") {
    const importer = document.createElement("button");
    importer.type = "button";
    importer.className = "secondary";
    importer.dataset.translationImport = entry.id;
    importer.textContent = "Import XML";
    importer.title = "Import a legally obtained XML file for local-only use.";
    controls.appendChild(importer);
  }
  if (entry.can_download) {
    const download = document.createElement("button");
    download.type = "button";
    download.className = "secondary";
    download.dataset.translationDownload = entry.id;
    download.textContent = "Install for offline use";
    download.title = "Download this approved third-party source for offline reading.";
    controls.appendChild(download);
  } else if (entry.can_select) {
    const select = document.createElement("button");
    select.type = "button";
    select.className = entry.selected ? "primary" : "secondary";
    select.dataset.translationSelect = entry.id;
    select.textContent = entry.selected ? "Selected" : "Select";
    select.disabled = Boolean(entry.selected);
    controls.appendChild(select);
    if (entry.can_set_default) {
      const makeDefault = document.createElement("button");
      makeDefault.type = "button";
      makeDefault.className = "secondary";
      makeDefault.dataset.translationMakeDefault = entry.id;
      makeDefault.textContent = "Set as default";
      makeDefault.title = "Use this translation as the reader default.";
      controls.appendChild(makeDefault);
    }
    if (entry.can_remove) {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "secondary";
      remove.dataset.translationRemove = entry.id;
      remove.textContent = "Remove";
      remove.title = "Remove this translation from the local reader.";
      controls.appendChild(remove);
    }
  }
  row.appendChild(main);
  row.appendChild(controls);
  return row;
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
  setContextLabel("cultural_context", isSelection ? "Cultural Context" : "Cultural Context");
  setContextLabel("literary_context", isSelection ? "Literary Context" : "Literary Context");
  setContextLabel("cross_references", isSelection ? "Cross References" : "Cross References");
  setContextLabel("related_ot_themes", isSelection ? "Related OT Themes" : "Related OT Themes");
  setContextLabel("people", isSelection ? "People" : "People");
  setContextLabel("places", isSelection ? "Places" : "Places");
  setContextLabel("themes", isSelection ? "Themes" : "Themes");
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
  const sourceTranslation = currentChapter?.translation?.id || selectedTranslationId().toUpperCase();
  return {
    type,
    book: context.book,
    chapter: Number(context.chapter),
    verseStart: Number(context.startVerse),
    verseEnd: Number(context.endVerse || context.startVerse),
    selectedText: context.text || "",
    isSelection: Boolean(context.isSelection),
    sourceTranslation,
  };
}

async function dispatchStudyAction(studyAction) {
  studyAction.type = BHF_STUDY_ACTION_ALIASES[studyAction.type] || studyAction.type;
  applyStudyActionContext(studyAction);
  if (studyAction.type === "ask_bhf") {
    activateWorkspaceTab("ask");
    setFormValue("ask_mode", "");
    setFormValue("study_action", "");
    setFormValue("deterministic_fact_packet", "");
    setMapContextValue("");
    const question = document.querySelector('.ask-form [name="question"]');
    if (question) {
      question.focus();
    }
  } else if (BHF_DETERMINISTIC_STUDY_ACTIONS.has(studyAction.type)) {
    await requestDeterministicStudyAction(studyAction);
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

async function requestDeterministicStudyAction(studyAction) {
  activateWorkspaceTab("ask");
  setFormValue("ask_mode", "");
  setFormValue("study_action", "");
  setFormValue("deterministic_fact_packet", "");
  setMapContextValue("");

  const answerPanel = document.querySelector("#answer-panel");
  const statusPanel = document.querySelector("#status-panel");
  activeLiveAnswerPanel = answerPanel;
  latestJobId = null;
  latestJobComplete = false;
  latestDeterministicStudyResult = null;

  if (statusPanel && typeof resetStatus === "function" && typeof startWaiting === "function") {
    resetStatus(statusPanel);
    startWaiting(statusPanel);
  }
  if (answerPanel) {
    answerPanel.setAttribute("aria-busy", "true");
    answerPanel.innerHTML = `<p class="empty">Loading deterministic ${escapeHtml(studyActionLabel(studyAction.type).toLowerCase())}...</p>`;
  }

  try {
    const result = await requestJson("/api/study/actions", {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(deterministicStudyPayload(studyAction)),
    }, "Could not load deterministic study result.");
    latestDeterministicStudyResult = result;
    if (answerPanel) {
      answerPanel.innerHTML = renderDeterministicStudyResult(result);
      wireDeterministicStudyControls(answerPanel, result, studyAction);
      addMobileAnswerCloseControl(answerPanel);
      revealAnswerPanel(answerPanel);
    }
    if (statusPanel && typeof markStatusComplete === "function") {
      markStatusComplete(statusPanel, {
        message: result.status === "complete" ? "Deterministic result ready" : "Partial deterministic result ready",
        percent_complete: 100,
      });
    }
    expandWorkspaceForMobileAnswer();
  } catch (error) {
    if (statusPanel && typeof markStatusFailed === "function") {
      markStatusFailed(statusPanel, error.message || "Request failed.");
    }
    if (answerPanel) {
      answerPanel.innerHTML = errorHtml(error.message || "Request failed.");
      addMobileAnswerCloseControl(answerPanel);
      revealAnswerPanel(answerPanel);
    }
  } finally {
    if (typeof stopWaiting === "function") {
      stopWaiting();
    }
    if (answerPanel) {
      answerPanel.removeAttribute("aria-busy");
    }
  }
}

function deterministicStudyPayload(studyAction) {
  return {
    action: studyAction.type,
    book: studyAction.book,
    chapter: studyAction.chapter,
    verse_start: studyAction.verseStart,
    verse_end: studyAction.verseEnd,
    selected_text: studyAction.selectedText || "",
    source_translation: studyAction.sourceTranslation || selectedTranslationId(),
    word_position: studyAction.wordPosition || "",
    surface_form: studyAction.surfaceForm || "",
    lemma: studyAction.lemma || "",
    language: studyAction.language || "",
    strongs_number: studyAction.strongsNumber || "",
    query: document.querySelector('.ask-form [name="question"]')?.value || "",
  };
}

function renderDeterministicStudyResult(result) {
  if (result?.action === "word_study" && result?.metadata?.word_study) {
    return renderWordStudyResult(result);
  }
  const sections = Array.isArray(result.sections) ? result.sections : [];
  const status = String(result.status || "unknown");
  const source = String(result.source || "deterministic");
  const confidence = Number(result.confidence || 0);
  const sectionHtml = sections.length
    ? sections.map(renderDeterministicSection).join("")
    : `<p class="empty">No deterministic Scripture or CKL facts were found for this action.</p>`;
  const refs = Array.isArray(result.references) ? result.references.filter(Boolean) : [];
  const refsHtml = refs.length
    ? `<section><h3>References</h3><ul>${refs.map((ref) => `<li>${escapeHtml(ref)}</li>`).join("")}</ul></section>`
    : "";
  return `
    <article class="answer deterministic-study-result" data-deterministic-study-result>
      <header class="answer-header">
        <div>
          <p class="answer-eyebrow">${escapeHtml(status)} - ${escapeHtml(source)} - ${Math.round(confidence * 100)}% confidence</p>
          <h2>${escapeHtml(result.title || "Study Result")}</h2>
        </div>
        <div class="answer-actions">
          <button type="button" class="secondary answer-save" data-deterministic-save>Save Study</button>
          ${result.agent_fallback_allowed ? `<button type="button" class="secondary" data-deterministic-explain>Explain with BHF</button>` : ""}
          <button type="button" class="secondary" data-deterministic-ask>Ask a Question</button>
        </div>
      </header>
      ${sectionHtml}
      ${refsHtml}
    </article>
  `;
}

function renderWordStudyResult(result) {
  const study = result.metadata?.word_study || {};
  const status = String(result.status || study.status || "unknown");
  const source = String(result.source || "ckl_sqlite");
  const confidence = Number(result.confidence || study.confidence || 0);
  const refs = Array.isArray(result.references) ? result.references.filter(Boolean) : [];
  const refsHtml = refs.length
    ? `<section><h3>References</h3><ul>${refs.map((ref) => `<li>${escapeHtml(ref)}</li>`).join("")}</ul></section>`
    : "";
  const bodyHtml = study.status === "ambiguous"
    ? renderWordStudyAmbiguity(study)
    : renderWordStudyComplete(study);
  return `
    <article class="answer deterministic-study-result word-study-result" data-deterministic-study-result>
      <header class="answer-header">
        <div>
          <p class="answer-eyebrow">${escapeHtml(status)} - ${escapeHtml(source)} - ${Math.round(confidence * 100)}% confidence</p>
          <h2>${escapeHtml(result.title || "Word Study")}</h2>
        </div>
        <div class="answer-actions">
          <button type="button" class="secondary answer-save" data-deterministic-save>Save Study</button>
          ${result.agent_fallback_allowed ? `<button type="button" class="secondary" data-deterministic-explain>Explain in Context</button>` : ""}
          <button type="button" class="secondary" data-deterministic-ask>Ask a Question</button>
        </div>
      </header>
      ${bodyHtml}
      ${refsHtml}
    </article>
  `;
}

function renderWordStudyComplete(study) {
  const facts = [
    ["Original Word", study.surface_form],
    ["Lemma", study.lemma],
    ["Transliteration", study.transliteration],
    ["Strong's", study.strongs_number],
    ["Morphology", wordStudyMorphologySummary(study)],
  ].filter(([, value]) => value);
  const range = Array.isArray(study.lexical_range) ? study.lexical_range.filter(Boolean).slice(0, 8) : [];
  const context = Array.isArray(study.contextual_information) ? study.contextual_information.filter(Boolean) : [];
  const sources = Array.isArray(study.sources) ? study.sources.filter(Boolean) : [];
  return `
    <section class="word-study-reader">
      <div class="word-study-facts">
        ${facts.map(([label, value]) => `
          <div class="word-study-fact">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
          </div>
        `).join("")}
      </div>
      ${range.length ? `<section><h3>Meaning Range</h3><ul>${range.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>` : ""}
      ${context.length ? `<section><h3>Contextual Information</h3><ul>${context.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>` : ""}
      ${sources.length ? `<section><h3>Sources</h3><ul>${sources.map((source) => `<li>${escapeHtml(wordStudySourceLabel(source))}</li>`).join("")}</ul></section>` : ""}
    </section>
    ${renderWordStudyScholar(study)}
  `;
}

function renderWordStudyAmbiguity(study) {
  const ambiguities = Array.isArray(study.ambiguities) ? study.ambiguities.filter(Boolean) : [];
  return `
    <section class="word-study-reader">
      <h3>${escapeHtml(study.message || "Multiple possible original-language words found.")}</h3>
      <ol class="word-study-choice-list">
        ${ambiguities.map((word) => `
          <li>
            <button type="button" class="word-study-choice" data-word-study-position="${escapeHtml(word.position || "")}" data-word-study-language="${escapeHtml(word.language || "")}" data-word-study-surface="${escapeHtml(word.surface_form || "")}" data-word-study-lemma="${escapeHtml(word.lemma || "")}" data-word-study-strongs="${escapeHtml(word.strongs_number || "")}">
              <strong>${escapeHtml(word.surface_form || word.lemma || "word")}</strong>
              <span>${escapeHtml([word.lemma, word.strongs_number, word.position ? `position ${word.position}` : ""].filter(Boolean).join(" - "))}</span>
            </button>
          </li>
        `).join("")}
      </ol>
    </section>
  `;
}

function renderWordStudyScholar(study) {
  const morphologyRows = keyValueRows(study.morphology || {});
  const entries = Array.isArray(study.lexical_entries) ? study.lexical_entries.filter(Boolean) : [];
  const senses = entries.flatMap((entry) => (entry.senses || []).map((sense) => ({ ...sense, entry })));
  const occurrences = Array.isArray(study.representative_occurrences) ? study.representative_occurrences.filter(Boolean) : [];
  const sources = Array.isArray(study.sources) ? study.sources.filter(Boolean) : [];
  return `
    <details class="word-study-scholar">
      <summary>Scholar View</summary>
      ${morphologyRows.length ? `<section><h3>Full Morphology</h3>${renderKeyValueTable(morphologyRows)}</section>` : ""}
      ${senses.length ? `<section><h3>Lexical Senses</h3><ul>${senses.map((sense) => `<li>${escapeHtml(wordStudySenseLabel(sense))}</li>`).join("")}</ul></section>` : ""}
      ${entries.length ? `<section><h3>Source Identifiers</h3><ul>${entries.map((entry) => `<li>${escapeHtml([entry.source, entry.source_entry_id, entry.license].filter(Boolean).join(" - "))}</li>`).join("")}</ul></section>` : ""}
      ${occurrences.length ? `<section><h3>Occurrence List</h3><ul>${occurrences.map((word) => `<li>${escapeHtml(wordStudyOccurrenceLabel(word))}</li>`).join("")}</ul></section>` : ""}
      ${sources.length ? `<section><h3>Dataset Information</h3><ul>${sources.map((source) => `<li>${escapeHtml(wordStudyDatasetLabel(source))}</li>`).join("")}</ul></section>` : ""}
      ${(study.guardrails || []).length ? `<section><h3>Safeguards</h3><ul>${study.guardrails.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>` : ""}
    </details>
  `;
}

function wordStudyMorphologySummary(study) {
  const morphology = study.morphology || {};
  const keys = ["part_of_speech", "stem", "conjugation", "tense", "voice", "mood", "person", "gender", "number", "case", "state"];
  const parts = keys.map((key) => morphology[key]).filter(Boolean);
  return parts.length ? parts.join(", ") : study.morphology_code || "";
}

function keyValueRows(value) {
  return Object.entries(value || {})
    .filter(([, item]) => item !== null && item !== undefined && String(item).trim())
    .map(([key, item]) => [key.replace(/_/g, " "), String(item)]);
}

function renderKeyValueTable(rows) {
  return `
    <dl class="word-study-key-values">
      ${rows.map(([key, value]) => `
        <div>
          <dt>${escapeHtml(key)}</dt>
          <dd>${escapeHtml(value)}</dd>
        </div>
      `).join("")}
    </dl>
  `;
}

function wordStudySourceLabel(source) {
  return [source.name, source.license].filter(Boolean).join(" - ") || "Lexical source";
}

function wordStudyDatasetLabel(source) {
  return [source.name, source.revision, source.license, source.attribution].filter(Boolean).join(" - ");
}

function wordStudySenseLabel(sense) {
  return [sense.gloss, sense.definition, sense.semantic_domain].filter(Boolean).join(" - ");
}

function wordStudyOccurrenceLabel(word) {
  const reference = word.reference || [word.book, word.chapter && word.verse ? `${word.chapter}:${word.verse}` : ""].filter(Boolean).join(" ");
  return [reference, word.surface_form, word.morphology_code].filter(Boolean).join(" - ");
}

function renderDeterministicSection(section) {
  const items = Array.isArray(section.items) ? section.items.filter(Boolean) : [];
  if (!items.length) {
    return "";
  }
  return `
    <section>
      <h3>${escapeHtml(section.title || "Section")}</h3>
      <ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </section>
  `;
}

function wireDeterministicStudyControls(answerPanel, result, studyAction) {
  wireWordStudyChoiceControls(answerPanel, studyAction);
  answerPanel.querySelector("[data-deterministic-explain]")?.addEventListener("click", () => {
    const packet = result.fact_packet || compactDeterministicResult(result);
    setFormValue("deterministic_fact_packet", JSON.stringify(packet));
    setFormValue("ask_mode", "");
    setFormValue("study_action", result.action || studyAction.type);
    setFormValue("question", `Explain ${result.title || "this deterministic study result"} using BHF.`);
    submitAskForm();
  });
  answerPanel.querySelector("[data-deterministic-ask]")?.addEventListener("click", () => {
    setFormValue("deterministic_fact_packet", "");
    const question = document.querySelector('.ask-form [name="question"]');
    if (question) {
      question.value = "";
      question.focus();
    }
  });
  answerPanel.querySelector("[data-deterministic-save]")?.addEventListener("click", async () => {
    await saveDeterministicStudy(result, studyAction);
  });
}

function wireWordStudyChoiceControls(answerPanel, studyAction) {
  answerPanel.querySelectorAll("[data-word-study-position]").forEach((button) => {
    button.addEventListener("click", async () => {
      const wordPosition = Number(button.dataset.wordStudyPosition || "0");
      if (!wordPosition) {
        return;
      }
      await requestDeterministicStudyAction({
        ...studyAction,
        type: "word_study",
        wordPosition,
        language: button.dataset.wordStudyLanguage || "",
        surfaceForm: button.dataset.wordStudySurface || "",
        lemma: button.dataset.wordStudyLemma || "",
        strongsNumber: button.dataset.wordStudyStrongs || "",
      });
    });
  });
}

function compactDeterministicResult(result) {
  return {
    action: result.action,
    status: result.status,
    source: result.source,
    title: result.title,
    sections: (result.sections || []).slice(0, 8).map((section) => ({
      title: section.title,
      items: (section.items || []).slice(0, 6),
      source: section.source || "deterministic",
    })),
    references: (result.references || []).slice(0, 12),
    confidence: result.confidence,
    metadata: {
      reference: result.metadata?.reference,
      object_ids: (result.metadata?.object_ids || []).slice(0, 12),
      word_study_prompt_context: result.metadata?.word_study_prompt_context || "",
    },
  };
}

async function saveDeterministicStudy(result, studyAction) {
  const payload = {
    title: result.title || studyActionLabel(result.action || studyAction.type),
    book: studyAction.book,
    chapter: studyAction.chapter,
    start_verse: studyAction.verseStart,
    end_verse: studyAction.verseEnd,
    selected_text: studyAction.selectedText || "",
    study_type: result.action || studyAction.type,
    question: result.title || "",
    answer: deterministicStudyMarkdown(result),
    canonical_object_ids: result.metadata?.object_ids || [],
  };
  await requestJson("/api/saved-studies", {
    method: "POST",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  }, "Could not save deterministic study.");
  await loadSavedStudies(currentChapter?.book, currentChapter?.chapter);
}

function deterministicStudyMarkdown(result) {
  const lines = [`# ${result.title || "Study Result"}`, ""];
  (result.sections || []).forEach((section) => {
    lines.push(`## ${section.title || "Section"}`);
    (section.items || []).forEach((item) => lines.push(`- ${item}`));
    lines.push("");
  });
  if ((result.references || []).length) {
    lines.push("## References");
    result.references.forEach((ref) => lines.push(`- ${ref}`));
  }
  return lines.join("\n").trim();
}

function studyActionLabel(action) {
  return String(action || "study action").replace(/_/g, " ");
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
  setFormValue("reader_translation", selectedTranslationId());

  const summary = document.querySelector("#selection-summary");
  const addNoteButton = document.querySelector("[data-add-note]");
  if (currentSelection) {
    const reference = formatReference(
      currentChapter.book,
      currentChapter.chapter,
      currentSelection.startVerse,
      currentSelection.endVerse
    );
    const translationLabel = translationSelectOptionLabel(selectedTranslationId(), installedTranslationIds());
    if (summary) {
      summary.textContent = `Selected ${translationLabel} ${reference}`;
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
    source_translation: studyAction.sourceTranslation || translationSelectOptionLabel(selectedTranslationId(), installedTranslationIds()),
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
