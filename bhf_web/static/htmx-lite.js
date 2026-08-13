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
const APP_DOCK_BOTTOM_HIDE_THRESHOLD_PX = 24;
const GENERAL_QUESTION_MODE = "general_question";
const THEME_STORAGE_KEY = "bhf-theme";
const READER_MODE_STORAGE_KEY = "bhf-reader-mode";
const READER_SPEECH_RATE_STORAGE_KEY = "bhf-reader-speech-rate";
const READER_SPEECH_VOICE_STORAGE_KEY = "bhf-reader-speech-voice";
const READER_SPEECH_AUTO_NEXT_STORAGE_KEY = "bhf-reader-speech-auto-next";
const READER_SPEECH_RATES = new Set([0.75, 0.9, 1, 1.25, 1.5]);
const READER_SPEECH_DEFAULT_RATE = 0.9;
const READER_SPEECH_DEFAULT_AUTO_NEXT = true;
const READER_SPEECH_HIDE_SCROLL_DELTA_PX = 24;
const READER_SPEECH_SHOW_SCROLL_DELTA_PX = 8;
const BHF_TRANSLATION_STORAGE_KEY = "bhf-reader-translation";
const BHF_TRANSLATION_DOWNLOAD_METADATA_KEY =
  "bhf-translation-download-metadata";
const READER_TABS_STORAGE_KEY = "bhf-reader-tabs";
const READER_TABS_METADATA_ID = "reader-tabs";
const READER_TAB_LIMIT = 8;
const BHF_CANONICAL_BOOK_NAMES = [
  "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
  "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
  "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
  "Psalms", "Proverbs", "Ecclesiastes", "Song of Songs", "Isaiah",
  "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
  "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
  "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John",
  "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
  "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
  "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
  "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John",
  "Jude", "Revelation",
];
const READER_LOCATION_STORAGE_KEY = "bhf-reader-location";
const READER_LOCATION_METADATA_ID = "reader-location";
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
  "archaeology",
  "compare_archaeology",
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
  "archaeology",
]);
const BHF_AUTO_ORGANIZED_CONTEXT_ACTIONS = new Set([
  "full_context",
  "historical_context",
  "cultural_context",
  "original_audience",
  "covenant_context",
  "literary_context",
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
let readerTabs = [];
let activeReaderTabId = null;
let readerTabSequence = 0;
let readerLoadToken = 0;
let readerSpeechState = "idle";
let readerSpeechSession = 0;
let readerSpeechVerseIndex = null;
let readerSpeechUtterance = null;
let readerSpeechContinuationToken = 0;
let readerSpeechVoicePreference;
let readerSpeechStatusMessage = "";
let readerSpeechStartTimer = null;
let readerSpeechControlsScrollAnchorY = 0;
let readerSpeechControlsScrollFrame = null;
let noteContext = null;
let currentNotes = [];
let currentHighlights = [];
const savedStudiesCache = new Map();
const savedStudiesRequests = new Map();
let contextMenuState = null;
let contextMenuPosition = null;
let lastMapAIFallbackKey = null;
let activeLiveAnswerPanel = null;
let latestDeterministicStudyResult = null;
let readerLongPressState = null;
let suppressHighlightedVerseTapUntil = 0;
let appSection = null;
let lastAskWorkspaceTab = "ask";
let lastNotesWorkspaceTab = "notes";
let lastExploreWorkspaceTab = "maps";
let minimizedWorkspaceTab = null;
let readerControlsTrigger = null;
let translationCatalogState = null;
let appDockScrollFrame = null;
let readerLocationSaveTimer = null;
let pendingReaderLocation = null;
let pendingReaderTabsPersistence = null;
let wordStudyNavigationStack = [];
let lastArchaeologyStudyAction = null;
const BHF_HTTP = window.BHFApi || {};

document.addEventListener("DOMContentLoaded", function () {
  initializeTheme();
  initializeReaderMode();
  initializeWorkspaceExpansion();
  initializeWorkspaceMinimize();
  initializeWorkspaceTabs();
  initializeAppNavigation();
  initializeReaderControlsSheet();
  initializeReader();
  initializeWorkspaceBridge();
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    flushReaderLocationPersistence();
  }
});

window.addEventListener("pagehide", flushReaderLocationPersistence);

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
    const providerHeaders = window.BHFModelSettings
      ? await window.BHFModelSettings.getProviderHeaders()
      : {};
    const job = await requestJson(
      form.dataset.jobPost,
      {
        method: "POST",
        body: new FormData(form),
        headers: {Accept: "application/json", ...providerHeaders},
      },
      "Could not start request.",
    );
    if (!job.job_id) {
      throw new Error("Could not start request.");
    }
    latestJobId = job.job_id;
    latestJobComplete = false;

    const finalStatus = await pollJob(form, statusPanel, job.job_id);
    const result = await requestText(
      form.dataset.resultBase + finalStatus.job_id,
      {},
      "Could not render result.",
    );
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
    wireAnswerPanelControls(answerPanel);
    revealAnswerPanel(answerPanel);
    latestJobComplete = false;
  } finally {
    if (window.BHFModelSettings) {
      window.BHFModelSettings.persistFormSettings().catch(() => {});
    }
    stopWaiting();
    answerPanel.removeAttribute("aria-busy");
    resetSubmitTargets(form);
    setFormValue("deterministic_fact_packet", "");
    setFormValue("ask_mode", "");
    setFormValue("study_action", "");
    setRunning(form, submitButton, false);
  }
});

function createReaderTabId() {
  readerTabSequence += 1;
  return `reader-tab-${Date.now()}-${readerTabSequence}`;
}

function activeReaderTab() {
  return readerTabs.find((tab) => tab.id === activeReaderTabId) || null;
}

function activeReaderPane() {
  const reader = document.querySelector("#chapter-reader");
  if (!reader) {
    return null;
  }
  return Array.from(reader.querySelectorAll("[data-reader-pane]")).find(
    (pane) => pane.dataset.readerPane === activeReaderTabId,
  ) || null;
}

function readerPaneForElement(element) {
  const pane = element?.closest?.("[data-reader-pane]");
  if (!pane) {
    return null;
  }
  return readerTabs.find((tab) => tab.id === pane.dataset.readerPane) || null;
}

function activateReaderPaneForElement(element) {
  const tab = readerPaneForElement(element);
  if (!tab || tab.id === activeReaderTabId) {
    return tab;
  }
  stopReaderSpeech();
  saveCurrentReaderTabState();
  activeReaderTabId = tab.id;
  currentChapter = tab.data || null;
  currentSelection = tab.selection ? {...tab.selection} : null;
  syncReaderControlsToActiveTab();
  if (currentSelection) {
    applySelectionContext(currentSelection);
  } else {
    clearReaderSelection();
  }
  syncAskFields();
  updateChapterNavigationState();
  if (currentChapter) {
    void Promise.all([
      loadNotes(currentChapter.book, currentChapter.chapter),
      loadHighlights(currentChapter.book, currentChapter.chapter),
      loadSavedStudies(currentChapter.book, currentChapter.chapter),
    ]);
  }
  return tab;
}

function normalizeReaderTab(value, index = 0) {
  const tab = value?.payload || value || {};
  const book = String(tab.book || "").trim();
  const chapter = Number(tab.chapter || 0);
  if (!book || !Number.isInteger(chapter) || chapter < 1) {
    return null;
  }
  const selection = tab.selection && typeof tab.selection === "object"
    ? {
        ...tab.selection,
        selectedVerses: Array.isArray(tab.selection.selectedVerses)
          ? tab.selection.selectedVerses.map(Number).filter((verse) => Number.isInteger(verse) && verse > 0)
          : [],
      }
    : null;
  return {
    id: String(tab.id || `reader-tab-${index + 1}`),
    book,
    chapter,
    translation: String(tab.translation || "asv").trim().toLowerCase() || "asv",
    verse: Number.isInteger(Number(tab.verse)) && Number(tab.verse) > 0 ? Number(tab.verse) : null,
    selection,
    data: null,
    updatedAt: String(tab.updatedAt || ""),
  };
}

function normalizeReaderTabsPayload(value) {
  const payload = value?.payload || value || {};
  if (!Array.isArray(payload.tabs)) {
    return null;
  }
  const tabs = payload.tabs
    .slice(0, READER_TAB_LIMIT)
    .map((tab, index) => normalizeReaderTab(tab, index))
    .filter(Boolean);
  if (tabs.length === 0) {
    return null;
  }
  const requestedActive = String(payload.activeTabId || "");
  const activeTabId = tabs.some((tab) => tab.id === requestedActive)
    ? requestedActive
    : tabs[0].id;
  return {
    tabs,
    activeTabId,
    updatedAt: String(payload.updatedAt || value?.updatedAt || ""),
  };
}

function readerTabsPayload() {
  return {
    version: 1,
    activeTabId: activeReaderTabId,
    updatedAt: new Date().toISOString(),
    tabs: readerTabs.map((tab) => ({
      id: tab.id,
      book: tab.book,
      chapter: Number(tab.chapter),
      translation: tab.translation,
      verse: tab.verse || null,
      selection: tab.selection || null,
      updatedAt: tab.updatedAt || "",
    })),
  };
}

function persistReaderTabs() {
  if (readerTabs.length === 0) {
    return;
  }
  const payload = readerTabsPayload();
  try {
    window.localStorage.setItem(READER_TABS_STORAGE_KEY, JSON.stringify(payload));
  } catch (_error) {
    // IndexedDB remains available when localStorage is blocked.
  }
  pendingReaderTabsPersistence = payload;
}

function readerTabLabel(tab) {
  const abbreviation = String(
    tab.data?.translation?.id || tab.translation || "asv",
  ).toUpperCase();
  return `${tab.book} ${tab.chapter} · ${abbreviation}`;
}

function renderReaderTabs() {
  const list = document.querySelector("[data-reader-tab-list]");
  const newTabButton = document.querySelector("[data-reader-new-tab]");
  if (!list) {
    return;
  }
  list.replaceChildren();
  readerTabs.forEach((tab) => {
    const wrapper = document.createElement("div");
    wrapper.className = "reader-tab-item";
    wrapper.dataset.readerTab = tab.id;
    wrapper.setAttribute("role", "presentation");

    const button = document.createElement("button");
    button.type = "button";
    button.className = "reader-tab";
    button.dataset.readerTabSelect = tab.id;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", String(tab.id === activeReaderTabId));
    button.tabIndex = tab.id === activeReaderTabId ? 0 : -1;
    button.textContent = readerTabLabel(tab);
    button.title = `Read ${tab.book} ${tab.chapter} in ${String(tab.translation || "asv").toUpperCase()}`;

    const close = document.createElement("button");
    close.type = "button";
    close.className = "reader-tab-close";
    close.dataset.readerTabClose = tab.id;
    close.setAttribute("aria-label", `Close ${readerTabLabel(tab)}`);
    close.title = `Close ${readerTabLabel(tab)}`;
    close.textContent = "×";
    close.disabled = readerTabs.length === 1;

    wrapper.appendChild(button);
    wrapper.appendChild(close);
    list.appendChild(wrapper);
  });
  if (newTabButton) {
    newTabButton.disabled = readerTabs.length >= READER_TAB_LIMIT;
    newTabButton.title = readerTabs.length >= READER_TAB_LIMIT
      ? `You can have up to ${READER_TAB_LIMIT} reading tabs.`
      : "Open a new reading tab";
  }
}

function saveCurrentReaderTabState() {
  const tab = activeReaderTab();
  if (!tab || !currentChapter) {
    return;
  }
  tab.book = currentChapter.book;
  tab.chapter = Number(currentChapter.chapter);
  tab.translation = String(currentChapter.translation?.id || selectedTranslationId() || "asv").toLowerCase();
  tab.selection = currentSelection ? {...currentSelection} : null;
  tab.verse = getVisibleReaderVerse() || tab.verse || null;
  tab.updatedAt = new Date().toISOString();
  persistReaderTabs();
}

function syncReaderControlsToActiveTab() {
  const tab = activeReaderTab();
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  const translationSelect = document.querySelector("[data-reader-translation]");
  if (!tab || !bookSelect || !chapterSelect) {
    renderReaderTabs();
    return;
  }
  const book = resolveReaderBookValue(tab.book, bookSelect);
  if (book) {
    bookSelect.value = book;
    populateChapterOptions(bookSelect, chapterSelect);
  }
  chapterSelect.value = resolveReaderChapterValue(tab.chapter, chapterSelect, "1");
  if (translationSelect) {
    syncTranslationSelectOptions();
    translationSelect.value = tab.translation;
  }
  renderReaderTabs();
}

async function selectReaderTab(tabId, options = {}) {
  const tab = readerTabs.find((candidate) => candidate.id === tabId);
  if (!tab) {
    return false;
  }
  if (activeReaderTabId !== tab.id) {
    stopReaderSpeech();
    saveCurrentReaderTabState();
    activeReaderTabId = tab.id;
  }
  syncReaderControlsToActiveTab();
  persistReaderTabs();
  await loadReaderChapter(tab.book, tab.chapter, {
    tabId: tab.id,
    translation: tab.translation,
    persistLocation: false,
    useCache: options.useCache !== false,
  });
  return true;
}

async function openNewReaderTab() {
  if (readerTabs.length >= READER_TAB_LIMIT) {
    return false;
  }
  saveCurrentReaderTabState();
  stopReaderSpeech();
  const current = activeReaderTab();
  const tab = normalizeReaderTab({
    id: createReaderTabId(),
    book: current?.book || "John",
    chapter: current?.chapter || 1,
    translation: current?.translation || selectedTranslationId(),
    verse: current?.verse || null,
  });
  if (!tab) {
    return false;
  }
  // The new tab starts at the same passage, so reuse the already-loaded
  // chapter while keeping selection state independent. This also prevents a
  // transient active pane with no verses while the async tab switch settles.
  tab.data = current?.data || currentChapter || null;
  readerTabs.push(tab);
  activeReaderTabId = tab.id;
  renderReaderTabs();
  await selectReaderTab(tab.id);
  return true;
}

async function closeReaderTab(tabId) {
  if (readerTabs.length <= 1) {
    return false;
  }
  const index = readerTabs.findIndex((tab) => tab.id === tabId);
  if (index < 0) {
    return false;
  }
  saveCurrentReaderTabState();
  const wasActive = activeReaderTabId === tabId;
  if (wasActive) {
    stopReaderSpeech();
  }
  readerTabs.splice(index, 1);
  if (wasActive) {
    const nextTab = readerTabs[Math.min(index, readerTabs.length - 1)];
    activeReaderTabId = nextTab.id;
    await selectReaderTab(nextTab.id);
  } else {
    renderReaderTabs();
    renderChapter(null);
  }
  persistReaderTabs();
  return true;
}

function handleReaderTabInteraction(event) {
  const close = event.target.closest("[data-reader-tab-close]");
  if (close) {
    event.preventDefault();
    event.stopPropagation();
    void closeReaderTab(close.dataset.readerTabClose);
    return;
  }
  const tab = event.target.closest("[data-reader-tab-select]");
  if (tab) {
    event.preventDefault();
    void selectReaderTab(tab.dataset.readerTabSelect);
  }
}

function handleReaderTabKeydown(event) {
  const tabs = Array.from(document.querySelectorAll("[data-reader-tab-select]"));
  const index = tabs.indexOf(event.currentTarget);
  if (index < 0) {
    return;
  }
  let nextIndex = null;
  if (event.key === "ArrowRight") {
    nextIndex = (index + 1) % tabs.length;
  } else if (event.key === "ArrowLeft") {
    nextIndex = (index - 1 + tabs.length) % tabs.length;
  } else if (event.key === "Home") {
    nextIndex = 0;
  } else if (event.key === "End") {
    nextIndex = tabs.length - 1;
  }
  if (nextIndex === null || !tabs[nextIndex]) {
    return;
  }
  event.preventDefault();
  const nextTab = tabs[nextIndex];
  void selectReaderTab(nextTab.dataset.readerTabSelect).then(() => nextTab.focus());
}

function normalizeReaderLocation(value) {
  const location = value?.payload || value;
  const book = String(location?.book || "").trim();
  const chapter = Number(location?.chapter || 0);
  const verse = Number(location?.verse || 0);
  if (!book || !Number.isInteger(chapter) || chapter < 1) {
    return null;
  }
  return {
    book,
    chapter,
    verse: Number.isInteger(verse) && verse > 0 ? verse : null,
    translation: String(location?.translation || "").trim().toLowerCase(),
    updatedAt: String(location?.updatedAt || value?.updatedAt || ""),
  };
}

function readLocalReaderLocation() {
  try {
    return normalizeReaderLocation(
      JSON.parse(localStorage.getItem(READER_LOCATION_STORAGE_KEY) || "null"),
    );
  } catch (_error) {
    return null;
  }
}

async function loadSavedReaderLocation() {
  const candidates = [];
  const localLocation = readLocalReaderLocation();
  if (localLocation) {
    candidates.push(localLocation);
  }
  const offlineDb = window.BHFOfflineDB;
  if (offlineDb && typeof offlineDb.get === "function") {
    try {
      const record = await offlineDb.get("metadata", READER_LOCATION_METADATA_ID);
      const storedLocation = normalizeReaderLocation(record);
      if (storedLocation) {
        candidates.push(storedLocation);
      }
    } catch (_error) {
      // localStorage remains available if IndexedDB is unavailable or corrupt.
    }
  }
  candidates.sort((left, right) => {
    const leftTime = Date.parse(left.updatedAt) || 0;
    const rightTime = Date.parse(right.updatedAt) || 0;
    return rightTime - leftTime;
  });
  return candidates[0] || null;
}

function readLocalReaderTabs() {
  try {
    return normalizeReaderTabsPayload(
      JSON.parse(localStorage.getItem(READER_TABS_STORAGE_KEY) || "null"),
    );
  } catch (_error) {
    return null;
  }
}

async function loadSavedReaderTabs() {
  const candidates = [];
  const localTabs = readLocalReaderTabs();
  if (localTabs) {
    candidates.push(localTabs);
  }
  const offlineDb = window.BHFOfflineDB;
  if (offlineDb && typeof offlineDb.get === "function") {
    try {
      const record = await offlineDb.get("metadata", READER_TABS_METADATA_ID);
      const storedTabs = normalizeReaderTabsPayload(record);
      if (storedTabs) {
        candidates.push(storedTabs);
      }
    } catch (_error) {
      // localStorage remains available if IndexedDB is unavailable or corrupt.
    }
  }
  candidates.sort((left, right) => {
    const leftTime = Date.parse(left.updatedAt) || 0;
    const rightTime = Date.parse(right.updatedAt) || 0;
    return rightTime - leftTime;
  });
  if (candidates[0]) {
    return candidates[0];
  }

  const legacyLocation = await loadSavedReaderLocation();
  if (!legacyLocation) {
    return null;
  }
  const legacyTab = normalizeReaderTab({
    id: createReaderTabId(),
    ...legacyLocation,
  });
  return legacyTab
    ? {tabs: [legacyTab], activeTabId: legacyTab.id, updatedAt: legacyLocation.updatedAt}
    : null;
}

function resolveReaderBookValue(book, bookSelect) {
  const normalized = String(book || "").trim().toLowerCase();
  if (!normalized || !bookSelect) {
    return null;
  }
  const option = Array.from(bookSelect.options).find(
    (candidate) => candidate.value.trim().toLowerCase() === normalized,
  );
  return option?.value || null;
}

function resolveReaderChapterValue(chapter, chapterSelect, fallback) {
  const requested = String(Number(chapter || 0));
  if (chapterSelect?.querySelector(`option[value="${requested}"]`)) {
    return requested;
  }
  return String(fallback || "1");
}

function restoreSavedReaderLocation(location) {
  if (!location || !currentChapter) {
    rememberReaderLocation(1);
    return;
  }
  const sameChapter =
    String(location.book).toLowerCase() === String(currentChapter.book).toLowerCase() &&
    Number(location.chapter) === Number(currentChapter.chapter);
  const verse = Number(location.verse || 0);
  const verseExists = currentChapter.verses?.some(
    (candidate) => Number(candidate.verse) === verse,
  );
  if (sameChapter && verseExists) {
    scrollToVerse(verse, "auto");
    rememberReaderLocation(verse);
    return;
  }
  rememberReaderLocation(getVisibleReaderVerse() || 1);
}

function readerLocationPayload(verseNumber) {
  if (!currentChapter) {
    return null;
  }
  const verse = Number(verseNumber || 0);
  return {
    book: currentChapter.book,
    chapter: Number(currentChapter.chapter),
    verse: Number.isInteger(verse) && verse > 0 ? verse : null,
    translation: String(currentChapter.translation?.id || selectedTranslationId() || "")
      .trim()
      .toLowerCase(),
    updatedAt: new Date().toISOString(),
  };
}

function rememberReaderLocation(verseNumber) {
  const location = readerLocationPayload(verseNumber);
  if (!location) {
    return;
  }
  const tab = activeReaderTab();
  if (tab) {
    tab.book = location.book;
    tab.chapter = location.chapter;
    tab.translation = location.translation || tab.translation;
    tab.verse = location.verse;
    tab.updatedAt = location.updatedAt;
    persistReaderTabs();
  }
  pendingReaderLocation = location;
  try {
    localStorage.setItem(READER_LOCATION_STORAGE_KEY, JSON.stringify(location));
  } catch (_error) {
    // IndexedDB below is the durable local-storage path when localStorage is blocked.
  }
  if (readerLocationSaveTimer) {
    window.clearTimeout(readerLocationSaveTimer);
  }
  readerLocationSaveTimer = window.setTimeout(flushReaderLocationPersistence, 250);
}

function flushReaderLocationPersistence() {
  if (readerLocationSaveTimer) {
    window.clearTimeout(readerLocationSaveTimer);
    readerLocationSaveTimer = null;
  }
  const location = pendingReaderLocation;
  const tabs = pendingReaderTabsPersistence;
  pendingReaderLocation = null;
  pendingReaderTabsPersistence = null;
  const offlineDb = window.BHFOfflineDB;
  if (!offlineDb || typeof offlineDb.put !== "function") {
    return;
  }
  const writes = [];
  if (location) {
    writes.push(
      offlineDb.put("metadata", {
        id: READER_LOCATION_METADATA_ID,
        updatedAt: location.updatedAt,
        cachedAt: location.updatedAt,
        payload: location,
      }),
    );
  }
  if (tabs) {
    writes.push(
      offlineDb.put("metadata", {
        id: READER_TABS_METADATA_ID,
        updatedAt: tabs.updatedAt,
        cachedAt: tabs.updatedAt,
        payload: tabs,
      }),
    );
  }
  void Promise.all(writes).catch(() => undefined);
}

function getVisibleReaderVerse() {
  const reader = activeReaderPane();
  if (!reader || !currentChapter) {
    return null;
  }
  const readerRect = reader.getBoundingClientRect();
  if (readerRect.bottom < 0 || readerRect.top > window.innerHeight) {
    return null;
  }
  const targetY = readerRect.top + Math.min(readerRect.height * 0.35, 280);
  let closestVerse = null;
  let closestDistance = Number.POSITIVE_INFINITY;
  for (const verse of reader.querySelectorAll("[data-verse]")) {
    const rect = verse.getBoundingClientRect();
    if (rect.bottom < 0 || rect.top > window.innerHeight) {
      continue;
    }
    const distance = Math.abs(rect.top - targetY);
    if (distance < closestDistance) {
      closestDistance = distance;
      closestVerse = Number(verse.dataset.verse || 0);
    }
  }
  return closestVerse || null;
}

function rememberVisibleReaderVerse() {
  const verse = getVisibleReaderVerse();
  if (verse) {
    rememberReaderLocation(verse);
  }
}

async function initializeReader() {
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  const translationSelect = document.querySelector("[data-reader-translation]");
  const translationImportButton = document.querySelector(
    "[data-reader-translation-import]",
  );
  const reader = document.querySelector("#chapter-reader");
  const askForm = document.querySelector(".ask-form");
  if (!bookSelect || !chapterSelect || !reader || !askForm) {
    return;
  }

  const defaultBook = reader.dataset.defaultBook || bookSelect.value || "John";
  if (!bookSelect.value && defaultBook) {
    bookSelect.value = defaultBook;
  }

  const savedTabs = await loadSavedReaderTabs();
  if (savedTabs) {
    readerTabs = savedTabs.tabs;
    activeReaderTabId = savedTabs.activeTabId;
  } else {
    const initialTab = normalizeReaderTab({
      id: createReaderTabId(),
      book: bookSelect.value || defaultBook,
      chapter: reader.dataset.defaultChapter || 1,
      translation: readLocalStorageValue(BHF_TRANSLATION_STORAGE_KEY) || "asv",
    });
    readerTabs = initialTab ? [initialTab] : [];
    activeReaderTabId = initialTab?.id || null;
  }
  const activeTab = activeReaderTab();
  const restoredBook = resolveReaderBookValue(activeTab?.book, bookSelect);
  if (restoredBook && activeTab) {
    activeTab.book = restoredBook;
  } else if (activeTab) {
    activeTab.book = bookSelect.value || defaultBook;
    activeTab.chapter = Number(reader.dataset.defaultChapter || 1);
    activeTab.data = null;
    activeTab.selection = null;
    activeTab.verse = null;
  }
  populateChapterOptions(bookSelect, chapterSelect);
  readerTabs = readerTabs.map((tab) => {
    const resolvedBook = resolveReaderBookValue(tab.book, bookSelect) || defaultBook;
    const bookOption = Array.from(bookSelect.options).find(
      (option) => option.value === resolvedBook,
    );
    const chapterCount = Number(bookOption?.dataset.chapters || 1);
    const chapter = Math.min(Math.max(Number(tab.chapter) || 1, 1), chapterCount);
    return {
      ...tab,
      book: resolvedBook,
      chapter,
      data: null,
    };
  });
  activeReaderTabId = activeReaderTab()?.id || readerTabs[0]?.id || null;
  if (!chapterSelect.options.length) {
    reader.innerHTML = `<p class="empty">No chapter data is available for ${escapeHtml(bookSelect.value || defaultBook)}.</p>`;
    return;
  }
  if (activeTab) {
    activeTab.chapter = Number(resolveReaderChapterValue(
      activeTab.chapter,
      chapterSelect,
      reader.dataset.defaultChapter || chapterSelect.options[0].value || "1",
    ));
  }
  const defaultChapter = resolveReaderChapterValue(
    activeTab?.chapter,
    chapterSelect,
    reader.dataset.defaultChapter || chapterSelect.options[0].value || "1",
  );
  chapterSelect.value = defaultChapter;
  if (translationSelect) {
    try {
      translationCatalogState = await loadTranslationState("/api/translations");
    } catch (_error) {
      translationCatalogState = null;
    }
    if (
      translationCatalogState?.default_translation &&
      !readLocalStorageValue(BHF_TRANSLATION_STORAGE_KEY) &&
      !savedTabs
    ) {
      setSelectedTranslationId(translationCatalogState.default_translation);
    }
    syncTranslationSelectOptions();
    if (activeTab && !installedTranslationIds().has(activeTab.translation)) {
      activeTab.translation = selectedTranslationId();
    }
    translationSelect.value = activeTab?.translation || selectedTranslationId();
  }
  syncReaderControlsToActiveTab();
  renderReaderTabs();
  const initialReaderTab = activeReaderTab();
  await loadReaderChapter(
    initialReaderTab?.book || bookSelect.value || defaultBook,
    initialReaderTab?.chapter || chapterSelect.value || defaultChapter,
    {
      tabId: initialReaderTab?.id,
      translation: initialReaderTab?.translation,
      persistLocation: false,
    },
  );
  void preloadRestoredReaderTabs(initialReaderTab?.id);

  bookSelect.addEventListener("change", async () => {
    const tab = activeReaderTab();
    if (tab) {
      tab.book = bookSelect.value;
      tab.chapter = 1;
      tab.data = null;
      tab.selection = null;
      tab.verse = null;
    }
    populateChapterOptions(bookSelect, chapterSelect);
    chapterSelect.value = "1";
    await loadReaderChapter(bookSelect.value, chapterSelect.value);
  });
  chapterSelect.addEventListener("change", async () => {
    const tab = activeReaderTab();
    if (tab) {
      tab.chapter = Number(chapterSelect.value || 1);
      tab.data = null;
      tab.selection = null;
      tab.verse = null;
    }
    await loadReaderChapter(bookSelect.value, chapterSelect.value);
  });
  if (translationSelect) {
    translationSelect.addEventListener("change", async () => {
      const requestedTranslation = String(
        translationSelect.value || "asv",
      ).toLowerCase();
      const previousTranslation = selectedTranslationId();
      try {
        const tab = activeReaderTab();
        if (tab) {
          tab.translation = requestedTranslation;
          tab.data = null;
        }
        await persistReaderDefaultTranslation(requestedTranslation);
        await loadReaderChapter(bookSelect.value, chapterSelect.value);
      } catch (error) {
        const tab = activeReaderTab();
        if (tab) {
          tab.translation = previousTranslation;
        }
        setSelectedTranslationId(previousTranslation);
        translationSelect.value = previousTranslation;
        renderChapter(null);
        const errorPane = activeReaderPane();
        if (errorPane) {
          errorPane.innerHTML = errorHtml(
            error.message || "Could not update translation.",
          );
        }
      }
    });
  }
  if (translationImportButton) {
    translationImportButton.addEventListener("click", async () => {
      await openTranslationImportDialog();
    });
  }
  const readerTabList = document.querySelector("[data-reader-tab-list]");
  if (readerTabList) {
    readerTabList.addEventListener("click", handleReaderTabInteraction);
    readerTabList.addEventListener("keydown", (event) => {
      if (event.target.matches("[data-reader-tab-select]")) {
        handleReaderTabKeydown(event);
      }
    });
  }
  const newReaderTab = document.querySelector("[data-reader-new-tab]");
  if (newReaderTab) {
    newReaderTab.addEventListener("click", () => {
      void openNewReaderTab();
    });
  }
  document.addEventListener("selectionchange", updateSelectionFromDocument);
  document.addEventListener("click", closeContextMenuOnOutside);
  document.addEventListener("keydown", closeContextMenuOnEscape);
  window.addEventListener("scroll", keepContextMenuVisibleOnReaderScroll, true);
  window.addEventListener("scroll", rememberVisibleReaderVerse, {passive: true});
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
  const searchResultsBody = document.querySelector(
    "#reader-search-results-body",
  );
  if (contextMenu) {
    contextMenu.addEventListener("click", handleContextMenuAction);
    contextMenu.addEventListener("mouseover", handleContextSubmenuHover);
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
    addNoteButton.disabled = false;
  }
  document.querySelectorAll("[data-new-note]").forEach((button) => {
    button.addEventListener("click", () => openNoteEditor());
  });
  document.querySelectorAll("[data-notes-view]").forEach((button) => {
    button.addEventListener("click", () => {
      void showNotesView(button.dataset.notesView);
    });
  });
  updateNotesViewControls();
  const attachNoteSelection = document.querySelector("[data-attach-note-selection]");
  if (attachNoteSelection) {
    attachNoteSelection.addEventListener("click", attachCurrentSelectionToNote);
  }
  const clearNoteReferenceButton = document.querySelector("[data-clear-note-reference]");
  if (clearNoteReferenceButton) {
    clearNoteReferenceButton.addEventListener("click", clearNoteReference);
  }
  const noteEditor = document.querySelector("#note-editor");
  if (noteEditor) {
    noteEditor.addEventListener("submit", saveNote);
    noteEditor.elements.body.addEventListener("input", () => {
      noteDraftDirty = true;
      scheduleNoteAutoSave();
    });
    noteEditor.elements.canonical_object_ids?.addEventListener("input", () => {
      noteDraftDirty = true;
      scheduleNoteAutoSave();
    });
  }
  const cancelNote = document.querySelector("[data-cancel-note]");
  if (cancelNote) {
    cancelNote.addEventListener("click", closeNoteEditor);
  }
  document.addEventListener("bhf:map-panel-opened", () =>
    activateWorkspaceTab("maps"),
  );
  document.addEventListener("bhf:map-panel-closed", () => {
    syncMapWorkspaceEmptyState();
    closeWorkspaceDrawer();
  });
  wireAnswerPanelControls(document.querySelector("#answer-panel"));
  wireAnswerPanelControls(document.querySelector("#map-ai-answer-panel"));
  wireSaveStudyButtons(document);
  syncMapWorkspaceEmptyState();
}

function handleChapterNavigationClick(event) {
  const button = event.target.closest(
    "[data-next-chapter], [data-prev-chapter]",
  );
  if (!button) {
    return;
  }
  activateReaderPaneForElement(button);
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
    tab.addEventListener("click", () => {
      if (tab.dataset.workspaceTab === "ask") {
        focusAskPanel();
        return;
      }
      activateWorkspaceTab(tab.dataset.workspaceTab);
    });
    tab.addEventListener("keydown", (event) =>
      handleWorkspaceTabKeydown(
        event,
        tabs.filter((candidate) => !candidate.hidden),
      ),
    );
  }
  setActiveWorkspaceTab(defaultTab);
}

function initializeAppNavigation() {
  const dock = document.querySelector("[data-app-dock]");
  const buttons = Array.from(
    dock?.querySelectorAll("[data-app-section]") || [],
  );
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
      const section = button.dataset.appSection || "bible";
      if (section === "ask") {
        focusAskPanel();
        return;
      }
      activateAppSection(section);
    });
  }

  document.addEventListener("bhf:workspace-tab-changed", (event) => {
    const tabId = event.detail?.tabId;
    rememberWorkspaceSubtab(tabId);
    if (window.BHFStudyCompanion) {
      return;
    }
    const nextSection = appSectionFromWorkspaceTab(tabId);
    if (nextSection) {
      activateAppSection(nextSection);
    }
  });

  window.addEventListener("resize", handleAppViewportChange);
  window.addEventListener("scroll", scheduleAppDockVisibilityUpdate, {
    passive: true,
  });
  scheduleAppDockVisibilityUpdate();
}

function initializeWorkspaceBridge() {
  if (typeof window === "undefined") {
    return;
  }
  window.BHFWorkspace = {
    requestMapAIFallback,
    focusAskPanel,
  };
  window.BHFReader = {
    navigateToPassage,
    openPassageReference,
    getStudySelection: () => window.BHFStudySelection?.getState?.() || null,
  };
  window.BHFStudyActions = {
    perform: performCompanionStudyAction,
    openWorkspaceTab: activateWorkspaceTab,
    openAdvancedMenu: openCompanionAdvancedMenu,
    openCanonicalQuery,
    savePassage: saveSelectedPassage,
    getSavedStudies: getSavedStudiesForSelection,
    syncAskSelection: syncAskFields,
  };
}

function activateAppSection(sectionId, options = {}) {
  const nextSection = normalizeAppSection(sectionId);
  appSection = nextSection;
  document.body.dataset.appSection = nextSection;
  if (
    nextSection !== "bible" &&
    document.body.classList.contains("reader-mode")
  ) {
    // Reader mode is an immersive Bible view. Leave it when the user opens
    // another app section so that the section's controls remain usable.
    applyReaderMode(false, {persist: false});
  }
  syncAppDockState(nextSection);
  syncWorkspaceTabsForSection(nextSection);

  if (options.persist !== false) {
    persistAppSection(nextSection);
  }

  if (isCompactViewport()) {
    applyCompactSectionLayout(nextSection);
  } else {
    applyDesktopSectionLayout(nextSection, options);
  }
  scheduleAppDockVisibilityUpdate();
}

function ensureExploreMapBrowserOpen() {
  const panel = document.querySelector("#map-panel");
  if (panel && !panel.hidden) {
    return;
  }
  openMapPanel({mode: "browse"});
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

  applyWorkspaceMinimized(false);
  restoreMinimizedWorkspaceTab();
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
    applyReaderMode(false, {persist: false});
  }
  applyWorkspaceMinimized(false);
  restoreMinimizedWorkspaceTab();
  applyWorkspaceExpansion(false);
}

function handleAppViewportChange() {
  const nextSection = normalizeAppSection(
    appSection || readAppSectionPreference() || "bible",
  );
  activateAppSection(nextSection, {
    persist: false,
    focusReader: false,
  });
  scheduleAppDockVisibilityUpdate();
}

function scheduleAppDockVisibilityUpdate() {
  if (appDockScrollFrame !== null) {
    return;
  }
  appDockScrollFrame = window.requestAnimationFrame(() => {
    appDockScrollFrame = null;
    updateAppDockVisibilityForScroll();
  });
}

function updateAppDockVisibilityForScroll() {
  const dock = document.querySelector("[data-app-dock]");
  if (!dock) {
    return;
  }

  const scrollingElement =
    document.scrollingElement || document.documentElement;
  const maxScroll = Math.max(
    0,
    scrollingElement.scrollHeight - window.innerHeight,
  );
  const scrollTop = Math.max(
    window.scrollY || window.pageYOffset || 0,
    scrollingElement.scrollTop || 0,
  );
  const shouldHideDock =
    isCompactViewport() &&
    maxScroll > APP_DOCK_BOTTOM_HIDE_THRESHOLD_PX &&
    scrollTop >= maxScroll - APP_DOCK_BOTTOM_HIDE_THRESHOLD_PX;

  document.body.classList.toggle("app-dock-hidden-at-bottom", shouldHideDock);
  dock.toggleAttribute("inert", shouldHideDock);
  if (shouldHideDock) {
    dock.setAttribute("aria-hidden", "true");
    if (dock.contains(document.activeElement)) {
      document.activeElement.blur();
    }
  } else {
    dock.removeAttribute("aria-hidden");
  }
}

function focusReaderArea() {
  const reader = document.querySelector(".reader-column");
  if (!reader) {
    return;
  }
  reader.scrollIntoView({block: "start", behavior: "smooth"});
}

function appSectionFromWorkspaceTab(tabId) {
  if (!tabId) {
    return null;
  }
  if (tabId === "commentary") {
    return "bible";
  }
  if (tabId === "ask" || tabId === "lexicon" || tabId === "context") {
    return "ask";
  }
  if (tabId === "notes" || tabId === "highlights") {
    return "notes";
  }
  if (tabId === "saved") {
    return "notes";
  }
  if (tabId === "maps" || tabId === "journey") {
    return "explore";
  }
  return null;
}

function appSectionToWorkspaceTab(sectionId) {
  const normalized = normalizeAppSection(sectionId);
  if (normalized === "bible") {
    return "commentary";
  }
  if (normalized === "ask") {
    const currentWorkspaceTab = getCurrentWorkspaceTab();
    if (currentWorkspaceTab === "ask" || currentWorkspaceTab === "lexicon" || currentWorkspaceTab === "context") {
      return currentWorkspaceTab;
    }
    return lastAskWorkspaceTab || "ask";
  }
  if (normalized === "notes") {
    const currentWorkspaceTab = getCurrentWorkspaceTab();
    if (
      currentWorkspaceTab === "notes" ||
      currentWorkspaceTab === "highlights" ||
      currentWorkspaceTab === "saved"
    ) {
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
  if (tabId === "ask" || tabId === "lexicon" || tabId === "context") {
    lastAskWorkspaceTab = tabId;
  } else if (tabId === "notes" || tabId === "highlights" || tabId === "saved") {
    lastNotesWorkspaceTab = tabId;
  } else if (tabId === "maps" || tabId === "journey") {
    lastExploreWorkspaceTab = tabId;
  }
}

function getCurrentWorkspaceTab() {
  const activeTab = document.querySelector(
    ".workspace-tab[aria-selected='true']",
  );
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
    const legacySaved = window.localStorage.getItem(
      LEGACY_MOBILE_SECTION_STORAGE_KEY,
    );
    return normalizeAppSection(saved || legacySaved || "bible");
  } catch (_error) {
    return "bible";
  }
}

function persistAppSection(sectionId) {
  try {
    window.localStorage.setItem(
      APP_SECTION_STORAGE_KEY,
      normalizeAppSection(sectionId),
    );
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
  applyTheme(savedTheme, {persist: false});
  for (const toggle of toggles) {
    toggle.addEventListener("click", toggleTheme);
  }
}

function initializeReaderMode() {
  initializeReaderSpeechControls();
  const toggles = Array.from(
    document.querySelectorAll("[data-reader-mode-toggle]"),
  );
  if (toggles.length === 0) {
    return;
  }
  const savedMode = readReaderModePreference();
  applyReaderMode(savedMode, {persist: false});
  for (const toggle of toggles) {
    toggle.addEventListener("click", toggleReaderMode);
  }

  const reader = document.querySelector("#chapter-reader");
  if (reader) {
    reader.addEventListener("click", handleReaderSurfaceTap);
  }
  document.addEventListener("keydown", handleReaderModeKeydown);
}

function supportsReaderSpeech() {
  return Boolean(
    window.speechSynthesis &&
    typeof window.speechSynthesis.speak === "function" &&
    typeof window.SpeechSynthesisUtterance === "function",
  );
}

function supportsReaderMediaSession() {
  return Boolean("mediaSession" in navigator && navigator.mediaSession);
}

function readerSpeechVoiceKey(voice) {
  return String(voice?.voiceURI || `${voice?.name || ""}|${voice?.lang || ""}`);
}

function readReaderSpeechRate() {
  try {
    const saved = Number(window.localStorage.getItem(READER_SPEECH_RATE_STORAGE_KEY));
    if (READER_SPEECH_RATES.has(saved)) {
      return saved;
    }
  } catch (_error) {
    // Use the default rate when storage is unavailable.
  }
  return READER_SPEECH_DEFAULT_RATE;
}

function saveReaderSpeechRate(rate) {
  if (!READER_SPEECH_RATES.has(rate)) {
    return READER_SPEECH_DEFAULT_RATE;
  }
  try {
    window.localStorage.setItem(READER_SPEECH_RATE_STORAGE_KEY, String(rate));
  } catch (_error) {
    // The in-memory selection still applies in restricted environments.
  }
  return rate;
}

function readReaderSpeechAutoNextPreference() {
  try {
    const saved = window.localStorage.getItem(READER_SPEECH_AUTO_NEXT_STORAGE_KEY);
    if (saved === "on" || saved === "off") {
      return saved === "on";
    }
  } catch (_error) {
    // Use the default when storage is unavailable.
  }
  return READER_SPEECH_DEFAULT_AUTO_NEXT;
}

function saveReaderSpeechAutoNextPreference(enabled) {
  const nextEnabled = Boolean(enabled);
  try {
    window.localStorage.setItem(
      READER_SPEECH_AUTO_NEXT_STORAGE_KEY,
      nextEnabled ? "on" : "off",
    );
  } catch (_error) {
    // The in-memory selection still applies in restricted environments.
  }
  return nextEnabled;
}

function selectedReaderSpeechVoice() {
  if (readerSpeechVoicePreference === undefined) {
    try {
      readerSpeechVoicePreference =
        window.localStorage.getItem(READER_SPEECH_VOICE_STORAGE_KEY) || "";
    } catch (_error) {
      readerSpeechVoicePreference = "";
    }
  }
  const voiceKey = readerSpeechVoicePreference;
  if (!voiceKey || !supportsReaderSpeech()) {
    return null;
  }
  return window.speechSynthesis
    .getVoices()
    .find((voice) => readerSpeechVoiceKey(voice) === voiceKey) || null;
}

function refreshReaderSpeechVoices() {
  const voiceSelect = document.querySelector("[data-reader-speech-voice]");
  if (!voiceSelect || !supportsReaderSpeech()) {
    return;
  }
  const voices = window.speechSynthesis
    .getVoices()
    .slice()
    .sort((left, right) => {
      const leftLabel = `${left.lang} ${left.name}`;
      const rightLabel = `${right.lang} ${right.name}`;
      return leftLabel.localeCompare(rightLabel);
    });
  const savedVoice = selectedReaderSpeechVoice();
  voiceSelect.innerHTML = "";
  const automatic = document.createElement("option");
  automatic.value = "";
  automatic.textContent = "Default voice";
  voiceSelect.appendChild(automatic);
  for (const voice of voices) {
    const option = document.createElement("option");
    option.value = readerSpeechVoiceKey(voice);
    option.textContent = `${voice.name} (${voice.lang})${voice.default ? " — default" : ""}`;
    voiceSelect.appendChild(option);
  }
  voiceSelect.value = savedVoice ? readerSpeechVoiceKey(savedVoice) : "";
}

function changeReaderSpeechVoice(event) {
  const voiceKey = String(event.target.value || "");
  readerSpeechVoicePreference = voiceKey;
  try {
    if (voiceKey) {
      window.localStorage.setItem(READER_SPEECH_VOICE_STORAGE_KEY, voiceKey);
    } else {
      window.localStorage.removeItem(READER_SPEECH_VOICE_STORAGE_KEY);
    }
  } catch (_error) {
    // The selected voice still applies for the current browser session.
  }
  if (readerSpeechState !== "idle") {
    startReaderSpeechAtIndex(readerSpeechVerseIndex || 0);
  }
}

function readerSpeechElements() {
  return {
    controls: document.querySelector("[data-reader-speech-controls]"),
    listen: document.querySelector("[data-reader-speech-listen]"),
    pause: document.querySelector("[data-reader-speech-pause]"),
    stop: document.querySelector("[data-reader-speech-stop]"),
    rate: document.querySelector("[data-reader-speech-rate]"),
    voice: document.querySelector("[data-reader-speech-voice]"),
    autoNext: document.querySelector("[data-reader-speech-auto-next]"),
    status: document.querySelector("[data-reader-speech-status]"),
  };
}

function initializeReaderSpeechControls() {
  const {controls, listen, pause, stop, rate, voice, autoNext} = readerSpeechElements();
  if (!controls || !listen || !pause || !stop || !rate || !voice || !autoNext) {
    return;
  }
  controls.hidden = false;
  rate.value = String(readReaderSpeechRate());
  autoNext.checked = readReaderSpeechAutoNextPreference();
  listen.addEventListener("click", startReaderSpeech);
  pause.addEventListener("click", toggleReaderSpeechPause);
  stop.addEventListener("click", stopReaderSpeech);
  rate.addEventListener("change", changeReaderSpeechRate);
  voice.addEventListener("change", changeReaderSpeechVoice);
  autoNext.addEventListener("change", (event) =>
    saveReaderSpeechAutoNextPreference(event.target.checked),
  );
  refreshReaderSpeechVoices();
  if (supportsReaderSpeech()) {
    if (typeof window.speechSynthesis.addEventListener === "function") {
      window.speechSynthesis.addEventListener("voiceschanged", refreshReaderSpeechVoices);
    } else {
      window.speechSynthesis.onvoiceschanged = refreshReaderSpeechVoices;
    }
  }
  initializeReaderMediaSession();
  updateReaderSpeechControls();
  readerSpeechControlsScrollAnchorY = readerSpeechScrollY();
  window.addEventListener("scroll", scheduleReaderSpeechControlsVisibilityUpdate, {
    passive: true,
  });
}

function readerSpeechScrollY() {
  const scrollingElement =
    document.scrollingElement || document.documentElement;
  return Math.max(
    window.scrollY || window.pageYOffset || 0,
    scrollingElement?.scrollTop || 0,
  );
}

function setReaderSpeechControlsScrolledAway(shouldHide) {
  const {controls} = readerSpeechElements();
  if (!controls) {
    return;
  }
  controls.classList.toggle("is-scrolled-away", shouldHide);
  controls.toggleAttribute("inert", shouldHide);
  if (shouldHide) {
    controls.setAttribute("aria-hidden", "true");
    if (controls.contains(document.activeElement)) {
      document.activeElement.blur();
    }
  } else {
    controls.removeAttribute("aria-hidden");
  }
}

function scheduleReaderSpeechControlsVisibilityUpdate() {
  if (readerSpeechControlsScrollFrame !== null) {
    return;
  }
  readerSpeechControlsScrollFrame = window.requestAnimationFrame(() => {
    readerSpeechControlsScrollFrame = null;
    updateReaderSpeechControlsVisibilityForScroll();
  });
}

function updateReaderSpeechControlsVisibilityForScroll() {
  if (!document.body.classList.contains("reader-mode")) {
    setReaderSpeechControlsScrolledAway(false);
    return;
  }

  const scrollY = readerSpeechScrollY();
  const scrollDelta = scrollY - readerSpeechControlsScrollAnchorY;
  if (scrollY <= READER_SPEECH_SHOW_SCROLL_DELTA_PX) {
    setReaderSpeechControlsScrolledAway(false);
    readerSpeechControlsScrollAnchorY = scrollY;
  } else if (scrollDelta >= READER_SPEECH_HIDE_SCROLL_DELTA_PX) {
    setReaderSpeechControlsScrolledAway(true);
    readerSpeechControlsScrollAnchorY = scrollY;
  } else if (scrollDelta <= -READER_SPEECH_SHOW_SCROLL_DELTA_PX) {
    setReaderSpeechControlsScrolledAway(false);
    readerSpeechControlsScrollAnchorY = scrollY;
  }
}

function updateReaderSpeechControls() {
  const {controls, listen, pause, stop, rate, voice, autoNext, status} = readerSpeechElements();
  if (!controls || !listen || !pause || !stop || !rate || !voice || !autoNext || !status) {
    return;
  }
  controls.hidden = false;
  const supported = supportsReaderSpeech();
  const hasVerses = Array.isArray(currentChapter?.verses) && currentChapter.verses.length > 0;
  const isPlaying = readerSpeechState === "playing";
  const isPaused = readerSpeechState === "paused";
  listen.disabled = !supported || !hasVerses || readerSpeechState !== "idle";
  pause.disabled = !supported || readerSpeechState === "idle";
  stop.disabled = !supported || readerSpeechState === "idle";
  rate.disabled = !supported;
  voice.disabled = !supported;
  autoNext.disabled = !supported;
  pause.textContent = isPaused ? "Resume" : "Pause";
  pause.setAttribute("aria-label", isPaused ? "Resume Scripture reading" : "Pause Scripture reading");
  pause.setAttribute("aria-pressed", String(isPaused));
  if (readerSpeechStatusMessage) {
    status.textContent = readerSpeechStatusMessage;
  } else if (!supported) {
    status.textContent = "Text-to-speech is not available in this browser.";
  } else if (isPlaying && Number.isInteger(readerSpeechVerseIndex)) {
    status.textContent = `Reading verse ${currentChapter.verses[readerSpeechVerseIndex]?.verse || ""}.`;
  } else if (isPaused) {
    status.textContent = "Scripture reading paused.";
  } else {
    status.textContent = "";
  }
  updateReaderMediaSession();
}

function setReaderMediaSessionAction(action, handler) {
  if (!supportsReaderMediaSession()) {
    return;
  }
  try {
    navigator.mediaSession.setActionHandler(action, handler);
  } catch (_error) {
    // Browsers expose different subsets of Media Session actions.
  }
}

function initializeReaderMediaSession() {
  if (!supportsReaderMediaSession()) {
    return;
  }
  setReaderMediaSessionAction("play", () => {
    if (readerSpeechState === "paused") {
      resumeReaderSpeech();
    } else if (readerSpeechState === "idle" && document.body.classList.contains("reader-mode")) {
      startReaderSpeech();
    }
  });
  setReaderMediaSessionAction("pause", pauseReaderSpeech);
  setReaderMediaSessionAction("stop", stopReaderSpeech);
}

function updateReaderMediaSession() {
  if (!supportsReaderMediaSession()) {
    return;
  }
  try {
    navigator.mediaSession.playbackState =
      readerSpeechState === "playing"
        ? "playing"
        : readerSpeechState === "paused"
          ? "paused"
          : "none";
    if (readerSpeechState === "idle" || !currentChapter) {
      navigator.mediaSession.metadata = null;
      return;
    }
    if (typeof window.MediaMetadata === "function") {
      const verse = currentChapter.verses?.[readerSpeechVerseIndex];
      navigator.mediaSession.metadata = new window.MediaMetadata({
        title: `${currentChapter.book} ${currentChapter.chapter}${verse ? `:${verse.verse}` : ""}`,
        artist: String(currentChapter.translation?.name || currentChapter.translation?.id || "BHF Bible Reader"),
        album: "BHF Bible Reader",
      });
    }
  } catch (_error) {
    // Media Session integration is optional and must never interrupt speech.
  }
}

function setReaderSpeechHighlight(verseNumber) {
  clearReaderSpeechHighlights();
  const pane = activeReaderPane();
  const verse = pane?.querySelector(`.verse[data-verse="${Number(verseNumber)}"]`);
  verse?.classList.add("is-speaking");
}

function clearReaderSpeechHighlights() {
  document
    .querySelectorAll("#chapter-reader .verse.is-speaking")
    .forEach((verse) => verse.classList.remove("is-speaking"));
}

function startReaderSpeech() {
  if (!supportsReaderSpeech() || !Array.isArray(currentChapter?.verses)) {
    readerSpeechStatusMessage = !supportsReaderSpeech()
      ? "Text-to-speech is not available in this browser."
      : "Wait for the chapter to finish loading, then try Listen again.";
    updateReaderSpeechControls();
    return;
  }
  readerSpeechStatusMessage = "";
  startReaderSpeechAtIndex(0);
}

function startReaderSpeechAtIndex(startIndex) {
  if (!supportsReaderSpeech() || !Array.isArray(currentChapter?.verses)) {
    updateReaderSpeechControls();
    return;
  }
  readerSpeechStatusMessage = "";
  stopReaderSpeech();
  readerSpeechState = "playing";
  readerSpeechVerseIndex = Math.max(0, Number(startIndex) || 0);
  const session = (readerSpeechSession += 1);
  updateReaderSpeechControls();
  speakReaderSpeechVerse(session);
}

function speakReaderSpeechVerse(session) {
  if (
    session !== readerSpeechSession ||
    readerSpeechState !== "playing" ||
    !Array.isArray(currentChapter?.verses)
  ) {
    return;
  }
  const verse = currentChapter.verses[readerSpeechVerseIndex];
  if (!verse) {
    finishReaderSpeech(session);
    return;
  }
  const utterance = new window.SpeechSynthesisUtterance();
  utterance.text = verse.text;
  utterance.rate = readReaderSpeechRate();
  const selectedVoice = selectedReaderSpeechVoice();
  if (selectedVoice) {
    utterance.voice = selectedVoice;
  }
  utterance.onend = () => {
    clearReaderSpeechStartTimer();
    if (session !== readerSpeechSession || readerSpeechState !== "playing") {
      return;
    }
    readerSpeechVerseIndex += 1;
    speakReaderSpeechVerse(session);
  };
  utterance.onstart = () => {
    clearReaderSpeechStartTimer();
  };
  utterance.onerror = (event) => {
    clearReaderSpeechStartTimer();
    if (session === readerSpeechSession) {
      const detail = String(event?.error || "unknown error").replace(/[-_]/g, " ");
      readerSpeechStatusMessage = `Speech could not start (${detail}). Try Listen again or select another voice.`;
      stopReaderSpeech({preserveStatus: true});
    }
  };
  readerSpeechUtterance = utterance;
  setReaderSpeechHighlight(verse.verse);
  updateReaderSpeechControls();
  try {
    // Some browser speech engines can remain paused after an interrupted read.
    // Resuming before queuing is harmless when the engine is already active.
    window.speechSynthesis.resume();
    window.speechSynthesis.speak(utterance);
    scheduleReaderSpeechStartCheck(session, utterance);
  } catch (_error) {
    readerSpeechStatusMessage = "Speech could not start. Try Listen again or select another voice.";
    stopReaderSpeech({preserveStatus: true});
  }
}

function clearReaderSpeechStartTimer() {
  if (readerSpeechStartTimer !== null) {
    window.clearTimeout(readerSpeechStartTimer);
    readerSpeechStartTimer = null;
  }
}

function scheduleReaderSpeechStartCheck(session, utterance) {
  clearReaderSpeechStartTimer();
  readerSpeechStartTimer = window.setTimeout(() => {
    if (
      session !== readerSpeechSession ||
      readerSpeechState !== "playing" ||
      readerSpeechUtterance !== utterance ||
      window.speechSynthesis.speaking
    ) {
      return;
    }
    readerSpeechStatusMessage = "Speech did not begin. Try Listen again or select another voice.";
    stopReaderSpeech({preserveStatus: true});
  }, 3000);
}

function pauseReaderSpeech() {
  if (!supportsReaderSpeech()) {
    return;
  }
  if (readerSpeechState === "playing") {
    window.speechSynthesis.pause();
    readerSpeechState = "paused";
  }
  updateReaderSpeechControls();
}

function resumeReaderSpeech() {
  if (!supportsReaderSpeech()) {
    return;
  }
  if (readerSpeechState === "paused") {
    window.speechSynthesis.resume();
    readerSpeechState = "playing";
  }
  updateReaderSpeechControls();
}

function toggleReaderSpeechPause() {
  if (readerSpeechState === "paused") {
    resumeReaderSpeech();
  } else {
    pauseReaderSpeech();
  }
}

function changeReaderSpeechRate(event) {
  const rate = saveReaderSpeechRate(Number(event.target.value));
  event.target.value = String(rate);
  if (readerSpeechState !== "idle") {
    startReaderSpeechAtIndex(readerSpeechVerseIndex || 0);
  }
}

function finishReaderSpeech(session) {
  if (session !== readerSpeechSession) {
    return;
  }
  readerSpeechState = "idle";
  clearReaderSpeechStartTimer();
  readerSpeechVerseIndex = null;
  readerSpeechUtterance = null;
  clearReaderSpeechHighlights();
  updateReaderSpeechControls();
  if (readReaderSpeechAutoNextPreference()) {
    const continuationToken = (readerSpeechContinuationToken += 1);
    goToNextChapter({readerSpeechContinuationToken: continuationToken});
  }
}

function stopReaderSpeech(options = {}) {
  clearReaderSpeechStartTimer();
  readerSpeechSession += 1;
  if (!options.preserveReaderSpeechContinuation) {
    readerSpeechContinuationToken += 1;
  }
  if (supportsReaderSpeech() && (readerSpeechState !== "idle" || readerSpeechUtterance)) {
    window.speechSynthesis.cancel();
  }
  readerSpeechState = "idle";
  readerSpeechVerseIndex = null;
  readerSpeechUtterance = null;
  if (!options.preserveStatus) {
    readerSpeechStatusMessage = "";
  }
  clearReaderSpeechHighlights();
  updateReaderSpeechControls();
}

function initializeWorkspaceExpansion() {
  const toggles = Array.from(
    document.querySelectorAll("[data-workspace-expand-toggle]"),
  );
  if (toggles.length === 0) {
    return;
  }
  applyWorkspaceExpansion(false);
  for (const toggle of toggles) {
    toggle.addEventListener("click", toggleWorkspaceExpansion);
  }
}

function initializeWorkspaceMinimize() {
  const workspaceToggle = document.querySelector(
    "[data-workspace-minimize-toggle]",
  );
  const dockToggle = document.querySelector("[data-workspace-dock-toggle]");
  if (!workspaceToggle && !dockToggle) {
    return;
  }

  applyWorkspaceMinimized(false);
  workspaceToggle?.addEventListener("click", toggleWorkspaceMinimized);
  dockToggle?.addEventListener("click", toggleWorkspaceFromDock);
}

function applyWorkspaceMinimized(enabled) {
  const nextEnabled = Boolean(enabled);
  if (nextEnabled && !document.body.classList.contains("workspace-minimized")) {
    minimizedWorkspaceTab = getCurrentWorkspaceTab();
  }
  document.body.classList.toggle("workspace-minimized", nextEnabled);
  if (nextEnabled) {
    applyWorkspaceExpansion(false);
    closeWorkspaceDrawer();
  }

  const workspaceToggle = document.querySelector(
    "[data-workspace-minimize-toggle]",
  );
  if (workspaceToggle) {
    const accessibleLabel = nextEnabled
      ? "Restore workspace"
      : "Minimize workspace to dock";
    workspaceToggle.setAttribute("aria-label", accessibleLabel);
    workspaceToggle.setAttribute("title", accessibleLabel);
    workspaceToggle.setAttribute("aria-pressed", String(nextEnabled));
  }

  const dockToggle = document.querySelector("[data-workspace-dock-toggle]");
  if (dockToggle) {
    const accessibleLabel = "Restore workspace";
    setControlLabel(dockToggle, "Restore");
    dockToggle.hidden = !nextEnabled;
    dockToggle.setAttribute("aria-label", accessibleLabel);
    dockToggle.setAttribute("title", accessibleLabel);
    dockToggle.setAttribute("aria-pressed", String(nextEnabled));
  }
}

function toggleWorkspaceMinimized() {
  const nextEnabled = !document.body.classList.contains("workspace-minimized");
  applyWorkspaceMinimized(nextEnabled);
  if (nextEnabled) {
    activateAppSection("bible", {focusReader: true});
    document.querySelector("[data-workspace-dock-toggle]")?.focus();
  }
}

function toggleWorkspaceFromDock() {
  if (!document.body.classList.contains("workspace-minimized")) {
    return;
  }
  const tabToRestore = minimizedWorkspaceTab || "ask";
  const sectionToRestore = appSectionFromWorkspaceTab(tabToRestore) || "ask";
  applyWorkspaceMinimized(false);
  activateAppSection(sectionToRestore, {focusReader: false});
  activateWorkspaceTab(tabToRestore);
  minimizedWorkspaceTab = null;
}

function restoreMinimizedWorkspaceTab() {
  if (!minimizedWorkspaceTab) {
    return;
  }
  const tabToRestore = minimizedWorkspaceTab;
  minimizedWorkspaceTab = null;
  activateWorkspaceTab(tabToRestore);
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
    const accessibleLabel = nextEnabled
      ? "Collapse workspace"
      : "Expand workspace";
    setControlStatus(
      toggle,
      `Current value: ${nextEnabled ? "Expanded" : "Collapsed"}`,
    );
    toggle.setAttribute("aria-label", accessibleLabel);
    toggle.setAttribute("title", accessibleLabel);
    toggle.setAttribute("aria-pressed", String(nextEnabled));
    toggle.setAttribute("aria-expanded", String(nextEnabled));
  }
}

function toggleWorkspaceExpansion() {
  applyWorkspaceExpansion(
    !document.body.classList.contains("workspace-expanded"),
  );
}

function revealAnswerPanel(answerPanel) {
  if (!answerPanel || !isCompactViewport()) {
    return;
  }
  window.requestAnimationFrame(() => {
    if (answerPanel.isConnected) {
      answerPanel.scrollIntoView({block: "start", behavior: "smooth"});
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
  closeButton.setAttribute(
    "aria-label",
    "Close answer and return to the reader",
  );
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
  if (!nextEnabled) {
    stopReaderSpeech();
  }
  document.body.classList.toggle("reader-mode", nextEnabled);
  readerSpeechControlsScrollAnchorY = readerSpeechScrollY();
  setReaderSpeechControlsScrolledAway(false);
  if (nextEnabled) {
    closeWorkspaceDrawer();
    closeReaderControlsSheet();
    hideContextMenu();
  }
  const toggles = document.querySelectorAll("[data-reader-mode-toggle]");
  for (const toggle of toggles) {
    setControlLabel(toggle, nextEnabled ? "Full view" : "Reader mode");
    setControlStatus(toggle, `Current value: ${nextEnabled ? "On" : "Off"}`);
    toggle.setAttribute("aria-pressed", String(nextEnabled));
  }
  const reader = document.querySelector("#chapter-reader");
  if (reader) {
    reader.setAttribute(
      "aria-label",
      nextEnabled
        ? "Scripture text. Tap the passage to show reading controls."
        : "Scripture text",
    );
  }
  if (options.persist !== false) {
    try {
      window.localStorage.setItem(
        READER_MODE_STORAGE_KEY,
        nextEnabled ? "on" : "off",
      );
    } catch (_error) {
      // Ignore storage errors in restricted environments.
    }
  }
}

function toggleReaderMode() {
  applyReaderMode(!document.body.classList.contains("reader-mode"));
}

function handleReaderSurfaceTap(event) {
  if (!document.body.classList.contains("reader-mode")) {
    return;
  }
  if (
    event.target.closest(
      "button, a, input, select, textarea, summary, [role='button']",
    )
  ) {
    return;
  }
  event.preventDefault();
  event.stopImmediatePropagation();
  applyReaderMode(false);
}

function handleReaderModeKeydown(event) {
  if (
    document.body.classList.contains("reader-mode") &&
    event.key === "Escape"
  ) {
    event.preventDefault();
    applyReaderMode(false);
  }
}

function readThemePreference() {
  if (window.BHFTestMode) {
    return "light";
  }
  try {
    const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === "light" || saved === "dark") {
      return saved;
    }
  } catch (_error) {
    return "light";
  }
  return window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
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
  const currentTheme =
    document.documentElement.dataset.theme === "dark" ? "dark" : "light";
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
  const triggers = Array.from(
    document.querySelectorAll("[data-reader-controls-trigger]"),
  );
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
    const action = event.target.closest(
      "[data-theme-toggle], [data-reader-mode-toggle]",
    );
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
}

function openReaderControlsSheet(trigger) {
  const sheet = document.querySelector("[data-reader-controls-sheet]");
  if (!sheet) {
    return;
  }
  readerControlsTrigger = trigger || document.activeElement;
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

function workspaceTabsForSection(sectionId) {
  const normalized = normalizeAppSection(sectionId);
  if (normalized === "bible") {
    return ["commentary"];
  }
  if (normalized === "ask") {
    return ["ask", "lexicon", "context"];
  }
  if (normalized === "notes") {
    return ["notes", "highlights", "saved"];
  }
  if (normalized === "studies") {
    return ["saved"];
  }
  if (normalized === "explore") {
    return ["maps"];
  }
  return ["ask"];
}

function syncWorkspaceTabsForSection(sectionId) {
  const workspace = document.querySelector("[data-workspace-tabs]");
  if (!workspace) {
    return;
  }
  const normalizedSection = normalizeAppSection(sectionId);
  const visibleTabs = new Set(workspaceTabsForSection(normalizedSection));
  let visibleCount = 0;
  workspace.querySelectorAll("[data-workspace-tab]").forEach((tab) => {
    const isVisible = visibleTabs.has(tab.dataset.workspaceTab);
    tab.hidden = !isVisible;
    tab.tabIndex =
      isVisible && tab.getAttribute("aria-selected") === "true" ? 0 : -1;
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
  const statusSelector =
    form.dataset.activeStatusTarget || form.dataset.statusTarget;
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
    const body = await response.text();
    let data;
    try {
      data = JSON.parse(body);
    } catch (_error) {
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("text/html") || /^\s*<!doctype html/i.test(body)) {
        throw new Error(
          `${fallbackMessage} (HTTP ${response.status}; the server returned HTML instead of JSON)`,
        );
      }
      throw new Error(`${fallbackMessage} (HTTP ${response.status}; invalid JSON response)`);
    }
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
  if (
    /^(?:[a-z]+:)?\/\//i.test(raw) ||
    raw.startsWith("data:") ||
    raw.startsWith("blob:")
  ) {
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
  if (getCurrentWorkspaceTab() === tabId) {
    return;
  }
  if (!setActiveWorkspaceTab(tabId)) {
    return;
  }
  document.dispatchEvent(
    new CustomEvent("bhf:workspace-tab-changed", {
      detail: {tabId},
    }),
  );
}

function focusAskPanel() {
  if (window.BHFMaps && typeof window.BHFMaps.closeMapModal === "function") {
    window.BHFMaps.closeMapModal();
  }

  activateAppSection(window.BHFStudyCompanion ? "bible" : "ask");
  activateWorkspaceTab("ask");
  window.BHFStudyCompanion?.ensureResourceVisible?.("ask");

  const focusQuestion = () => {
    const question = document.querySelector('.ask-form [name="question"]');
    if (!question || question.disabled || question.hidden) {
      return;
    }
    question.focus({preventScroll: true});
    if (isCompactViewport()) {
      question.scrollIntoView({block: "nearest", behavior: "smooth"});
    }
  };

  // Let the drawer/modal transition settle before focusing so it cannot steal
  // focus back to the triggering map or dock control.
  const schedule =
    typeof window.requestAnimationFrame === "function"
      ? window.requestAnimationFrame.bind(window)
      : (callback) => window.setTimeout(callback, 0);
  schedule(() => schedule(focusQuestion));
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
    button.addEventListener("click", () => openMapPanel({mode: "browse"}));
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

async function loadReaderChapter(book, chapter, options = {}) {
  const continuationToken = options.readerSpeechContinuationToken;
  const shouldResumeReaderSpeech = Number.isInteger(continuationToken);
  stopReaderSpeech({preserveReaderSpeechContinuation: shouldResumeReaderSpeech});
  const reader = document.querySelector("#chapter-reader");
  if (!reader) {
    return;
  }
  const tab = readerTabs.find((candidate) => candidate.id === options.tabId) || activeReaderTab();
  if (tab && activeReaderTabId !== tab.id) {
    activeReaderTabId = tab.id;
  }
  const persistLocation = options.persistLocation !== false;
  const translationId = String(
    options.translation || tab?.translation || selectedTranslationId() || "asv",
  ).toLowerCase();
  const requestToken = (readerLoadToken += 1);
  if (tab) {
    tab.book = book;
    tab.chapter = Number(chapter);
    tab.translation = translationId;
  }
  reader.setAttribute("aria-busy", "true");
  hideContextMenu();
  renderChapter(null);
  try {
    let data = null;
    if (
      options.useCache !== false &&
      tab?.data &&
      String(tab.data.book).toLowerCase() === String(book).toLowerCase() &&
      Number(tab.data.chapter) === Number(chapter) &&
      String(tab.data.translation?.id || translationId).toLowerCase() === translationId
    ) {
      data = tab.data;
    } else {
      const params = new URLSearchParams({translation: translationId});
      data = await requestJson(
        `/api/bible/${encodeURIComponent(book)}/${encodeURIComponent(chapter)}?${params.toString()}`,
        {},
        "Could not load chapter.",
      );
    }
    if (requestToken !== readerLoadToken) {
      return;
    }
    currentChapter = data;
    currentSelection = null;
    window.BHFStudySelection?.setChapter?.({
      book: data.book,
      chapter: Number(data.chapter),
      translation: String(data.translation?.id || translationId),
    }, "reader-chapter");
    latestJobId = null;
    latestJobComplete = false;
    currentNotes = [];
    currentHighlights = [];
    if (tab) {
      tab.data = data;
      tab.book = data.book;
      tab.chapter = Number(data.chapter);
      tab.translation = String(data.translation?.id || translationId).toLowerCase();
    }
    renderChapter(data);
    if (tab?.selection) {
      const savedSelection = {...tab.selection};
      applySelectionContext(savedSelection);
    }
    if (tab?.verse) {
      const verseExists = data.verses?.some(
        (candidate) => Number(candidate.verse) === Number(tab.verse),
      );
      if (verseExists) {
        scrollToVerse(Number(tab.verse), "auto");
      }
    }
    if (persistLocation) {
      rememberReaderLocation(getVisibleReaderVerse() || 1);
    }
    clearReaderSearchState();
    syncReaderControlsToActiveTab();
    syncAskFields();
    updateChapterNavigationState();
    if (
      shouldResumeReaderSpeech &&
      continuationToken === readerSpeechContinuationToken &&
      readReaderSpeechAutoNextPreference()
    ) {
      startReaderSpeechAtIndex(0);
    }
    if (window.BHFCommentary && typeof window.BHFCommentary.loadChapter === "function") {
      void window.BHFCommentary.loadChapter(data.book, data.chapter);
    }
    await Promise.all([
      loadNotes(data.book, data.chapter),
      loadHighlights(data.book, data.chapter),
      loadSavedStudies(data.book, data.chapter),
    ]);
    if (lastArchaeologyStudyAction) {
      void requestDeterministicStudyAction(
        {
          ...lastArchaeologyStudyAction,
          book: data.book,
          chapter: Number(data.chapter),
          verseStart: null,
          verseEnd: null,
          selectedVerses: [],
          selectedText: "",
          isSelection: false,
        },
        {chapterRefresh: true},
      );
    }
  } catch (error) {
    if (translationId !== "asv") {
      if (tab) {
        tab.translation = "asv";
        tab.data = null;
      }
      setSelectedTranslationId("asv");
      await loadReaderChapter(book, chapter, {...options, translation: "asv", useCache: false});
      return;
    }
    renderChapter(null);
    const errorPane = activeReaderPane();
    if (errorPane) {
      errorPane.innerHTML = errorHtml(error.message || "Could not load chapter.");
    }
  } finally {
    if (requestToken === readerLoadToken) {
      reader.removeAttribute("aria-busy");
    }
  }
}

function loadReaderTabData(tab) {
  if (!tab || tab.data) {
    return Promise.resolve(tab?.data || null);
  }
  if (tab.pendingLoad) {
    return tab.pendingLoad;
  }
  const translationId = String(tab.translation || "asv").toLowerCase();
  const params = new URLSearchParams({translation: translationId});
  const request = requestJson(
    `/api/bible/${encodeURIComponent(tab.book)}/${encodeURIComponent(tab.chapter)}?${params.toString()}`,
    {},
    "Could not load chapter.",
  ).then((data) => {
    tab.data = data;
    tab.book = data.book;
    tab.chapter = Number(data.chapter);
    tab.translation = String(data.translation?.id || translationId).toLowerCase();
    return data;
  });
  tab.pendingLoad = request.finally(() => {
    tab.pendingLoad = null;
  });
  return tab.pendingLoad;
}

async function preloadRestoredReaderTabs(activeTabId) {
  const pendingTabs = readerTabs.filter(
    (tab) => tab.id !== activeTabId && !tab.data,
  );
  if (!pendingTabs.length) {
    return;
  }
  await Promise.allSettled(pendingTabs.map((tab) => loadReaderTabData(tab)));
  // Do not replace a chapter the user started loading after refresh. The
  // active-tab loader owns the visible pane once the user switches tabs.
  if (activeReaderTabId === activeTabId) {
    renderChapter(currentChapter);
  }
}

function clearReaderSearchState() {
  if (typeof clearBibleSearchResults === "function") {
    clearBibleSearchResults();
  }
}

async function navigateToPassage(book, chapter, verseStart, verseEnd, options = {}) {
  if (options.newTab) {
    await openNewReaderTab();
  }
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  const tab = activeReaderTab();
  if (bookSelect && chapterSelect) {
    bookSelect.value = book;
    populateChapterOptions(bookSelect, chapterSelect);
    chapterSelect.value = String(chapter);
  }
  if (tab) {
    tab.book = book;
    tab.chapter = Number(chapter);
    tab.data = null;
    tab.selection = null;
    tab.verse = verseStart ? Number(verseStart) : null;
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
    text: collectSelectedVerseText(
      Number(verseStart),
      Number(verseEnd || verseStart),
    ),
    isSelection: Number(verseEnd || verseStart) !== Number(verseStart),
  };
  applySelectionContext(context);
  scrollToVerse(Number(verseStart));
}

function goToNextChapter(options = {}) {
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  if (!bookSelect || !chapterSelect) {
    return false;
  }
  const selectedBook = bookSelect.selectedOptions[0] || bookSelect.options[0];
  const chapterCount = Number(selectedBook?.dataset.chapters || 0);
  const currentChapterNumber = Number(chapterSelect.value || "0");
  if (
    !chapterCount ||
    !currentChapterNumber ||
    currentChapterNumber >= chapterCount
  ) {
    return false;
  }
  const nextChapter = currentChapterNumber + 1;
  chapterSelect.value = String(nextChapter);
  const tab = activeReaderTab();
  if (tab) {
    tab.chapter = nextChapter;
    tab.data = null;
    tab.selection = null;
    tab.verse = null;
  }
  void loadReaderChapter(bookSelect.value, nextChapter, options);
  return true;
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
  const tab = activeReaderTab();
  if (tab) {
    tab.chapter = previousChapter;
    tab.data = null;
    tab.selection = null;
    tab.verse = null;
  }
  loadReaderChapter(bookSelect.value, previousChapter);
}

function parsePassageReference(reference) {
  const rawReference = String(reference || "").trim();
  if (!rawReference) {
    return null;
  }

  const chapterMatch = rawReference.match(
    /^(?<book>.+?)\s+(?<chapter>\d+)(?::(?<verseStart>\d+)(?:-(?<verseEnd>\d+))?|-(?<chapterEnd>\d+))?$/,
  );
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
  const verseStart = chapterMatch.groups.verseStart
    ? Number(chapterMatch.groups.verseStart)
    : null;
  const verseEnd = chapterMatch.groups.verseEnd
    ? Number(chapterMatch.groups.verseEnd)
    : verseStart;

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
  await navigateToPassage(
    parsed.book,
    parsed.chapter,
    parsed.verseStart,
    parsed.verseEnd,
  );
  return true;
}

function renderChapter(data) {
  const reader = document.querySelector("#chapter-reader");
  if (!reader) {
    return;
  }
  const grid = document.createElement("div");
  grid.className = "reader-pane-grid";

  readerTabs.forEach((tab) => {
    if (tab.id === activeReaderTabId && data) {
      tab.data = data;
    }
    if (tab.data) {
      grid.appendChild(createReaderPane(tab.data, tab));
      return;
    }
    const loading = document.createElement("article");
    loading.className = "reader-pane reader-pane-loading";
    loading.dataset.readerPane = tab.id;
    loading.setAttribute("aria-label", `Loading ${readerTabLabel(tab)}`);
    loading.innerHTML = `<p class="empty">Loading ${escapeHtml(readerTabLabel(tab))}...</p>`;
    grid.appendChild(loading);
  });

  reader.innerHTML = "";
  reader.classList.toggle("has-multiple-reader-panes", readerTabs.length > 1);
  reader.appendChild(grid);
  scheduleAppDockVisibilityUpdate();
}

function createReaderPane(data, tab) {
  const pane = document.createElement("article");
  pane.className = "reader-pane";
  pane.dataset.readerPane = tab.id;
  pane.classList.toggle("is-active", tab.id === activeReaderTabId);
  pane.setAttribute("aria-label", `${data.book} ${data.chapter} ${String(data.translation?.id || tab.translation || "").toUpperCase()}`);

  const header = document.createElement("div");
  header.className = "reader-chapter-header";

  const passageHeading = document.createElement("div");
  passageHeading.className = "reader-passage-heading";

  const heading = document.createElement("h3");
  heading.textContent = `${data.book} ${data.chapter}`;

  const translation = data.translation || {};
  const abbreviation = translation.id || String(tab.translation || "asv").toUpperCase();
  const translationBadge = document.createElement("button");
  translationBadge.type = "button";
  translationBadge.className = "reader-translation-badge";
  translationBadge.dataset.translationSelectorTrigger = "true";
  translationBadge.textContent = abbreviation;
  translationBadge.setAttribute(
    "aria-label",
    `Translation: ${abbreviation}. Open translation selector.`,
  );
  translationBadge.title = "Open translation selector";

  passageHeading.appendChild(heading);
  passageHeading.appendChild(translationBadge);
  header.appendChild(passageHeading);
  pane.appendChild(header);

  const paragraph = document.createElement("p");
  paragraph.className = "chapter-text";
  for (const verse of data.verses) {
    const verseSpan = document.createElement("span");
    verseSpan.className = "verse";
    verseSpan.dataset.verse = String(verse.verse);
    const savedSelection = selectedVerseNumbers(tab.selection);
    const isSelected = savedSelection.includes(Number(verse.verse));
    verseSpan.classList.toggle("selected", isSelected);

    const number = document.createElement("button");
    number.type = "button";
    number.className = "verse-number";
    number.dataset.verseSelect = "true";
    number.textContent = String(verse.verse);
    number.setAttribute(
      "aria-label",
      `Select ${data.book} ${data.chapter}:${verse.verse}`,
    );
    number.setAttribute("aria-pressed", String(isSelected));
    number.addEventListener("click", (event) => {
      activateReaderPaneForElement(verseSpan);
      handleVerseSelectionClick(event, verseSpan);
    });

    const indicators = document.createElement("span");
    indicators.className = "verse-state-indicators";
    indicators.dataset.verseIndicators = "true";

    const text = document.createElement("span");
    text.className = "verse-text";
    text.textContent = verse.text + " ";

    verseSpan.appendChild(number);
    verseSpan.appendChild(indicators);
    verseSpan.appendChild(text);
    paragraph.appendChild(verseSpan);
  }
  pane.appendChild(paragraph);

  const footer = document.createElement("div");
  footer.className = "reader-chapter-footer reader-next-chapter-footer";
  footer.appendChild(createChapterNavButton("prev", "◀ Previous Chapter"));
  footer.appendChild(createChapterNavButton("next", "Next Chapter ▶"));
  pane.appendChild(footer);
  return pane;
}

function currentTranslationAbbreviation() {
  return (
    currentChapter?.translation?.id || selectedTranslationId().toUpperCase()
  );
}

async function handleTranslationSelectorClick(event) {
  const trigger = event.target.closest("[data-translation-selector-trigger]");
  if (!trigger) {
    return;
  }
  activateReaderPaneForElement(trigger);
  event.preventDefault();
  event.stopPropagation();
  await openTranslationSelector(trigger);
}

async function openTranslationSelector(trigger) {
  const dialog = ensureTranslationSelectorDialog();
  dialog.hidden = false;
  document.body.classList.add("translation-selector-open");
  dialog.setAttribute("aria-busy", "true");
  dialog.querySelector("[data-translation-selector-body]").innerHTML =
    `<p class="empty">Loading translations...</p>`;
  try {
    translationCatalogState = await loadTranslationState("/api/translations/catalog");
    renderTranslationSelector(translationCatalogState);
  } catch (error) {
    dialog.querySelector("[data-translation-selector-body]").innerHTML =
      errorHtml(error.message || "Could not load translations.");
  } finally {
    dialog.removeAttribute("aria-busy");
    const closeButton = dialog.querySelector(
      "[data-close-translation-selector]",
    );
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
    if (
      event.target === dialog ||
      event.target.closest("[data-close-translation-selector]")
    ) {
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
  body.appendChild(
    renderTranslationSection("Installed", sections.installed || []),
  );
  const actions = document.createElement("div");
  actions.className =
    "translation-selector-entry-actions translation-import-actions";
  const importer = document.createElement("button");
  importer.type = "button";
  importer.className = "secondary";
  importer.dataset.translationImport = "";
  importer.textContent = "Import Bible";
  actions.appendChild(importer);
  body.appendChild(actions);
}

async function loadTranslationState(url) {
  const state = await requestJson(
    url,
    {},
    "Could not load translations.",
  );
  return mergeDeviceTranslations(state);
}

async function mergeDeviceTranslations(state) {
  const offlineDb = window.BHFOfflineDB;
  if (!offlineDb || typeof offlineDb.list !== "function") {
    return state;
  }
  let localEntries = [];
  try {
    localEntries = (await offlineDb.list("translations"))
      .map(deviceTranslationEntry)
      .filter(Boolean);
  } catch (_error) {
    return state;
  }
  if (!localEntries.length) {
    return state;
  }

  const localIds = new Set(localEntries.map((entry) => entry.id));
  const mergeEntries = (entries) => [
    ...(Array.isArray(entries) ? entries : []).filter(
      (entry) => !localIds.has(String(entry?.id || "").toLowerCase()),
    ),
    ...localEntries,
  ];
  const merged = {
    ...state,
    translations: mergeEntries(state?.translations),
    catalog: mergeEntries(state?.catalog),
    sections: {
      ...(state?.sections || {}),
      installed: mergeEntries(state?.sections?.installed),
    },
  };
  const selected = String(
    readLocalStorageValue(BHF_TRANSLATION_STORAGE_KEY) || "",
  ).toLowerCase();
  if (localIds.has(selected)) {
    merged.default_translation = selected;
  } else if (selected && !["asv", "kjv"].includes(selected)) {
    writeLocalStorageValue(BHF_TRANSLATION_STORAGE_KEY, "asv");
  }
  return merged;
}

function deviceTranslationEntry(record) {
  const payload = record?.payload || {};
  const dataset = payload.dataset || {};
  const installation = payload.installation || {};
  if (!installation.device_local || !dataset.translation) {
    return null;
  }
  const translation = dataset.translation;
  const id = String(
    payload.translation_id || translation.id || record.id || "",
  ).toLowerCase();
  if (!id || id === "asv" || id === "kjv") {
    return null;
  }
  return {
    id,
    name: String(translation.name || id.toUpperCase()),
    abbreviation: String(translation.id || id.toUpperCase()).toUpperCase(),
    language: translation.language || "en",
    language_code: translation.language || "en",
    bundled: false,
    install_mode: "device_local",
    license_status: "user_supplied",
    source: translation.source || "device import",
    installed: true,
    default: false,
    can_select: true,
    can_download: false,
    can_remove: true,
    can_set_default: true,
    status_label: "On this device",
    third_party: false,
    third_party_notice: "",
    created_date: record.cachedAt || "",
    device_local: true,
    private_local_install: true,
  };
}

function translationCatalogWithLocalState(state) {
  const selectedId = selectedTranslationId();
  const sections = state?.sections || {};
  const installed = Array.isArray(sections.installed) ? sections.installed : [];
  const decoratedInstalled = installed.map((entry) => ({
    ...entry,
    selected: String(entry.id || "").toLowerCase() === selectedId,
    can_select: true,
    can_set_default: true,
    can_remove: !entry.bundled,
    can_download: false,
    status_label: entry.id === "asv"
      ? "Built in"
      : (entry.device_local ? "On this device" : "Installed locally"),
  }));

  return {
    ...state,
    sections: {
      installed: decoratedInstalled,
    },
  };
}

function installedTranslationIds() {
  const ids = new Set(["asv"]);
  if (
    translationCatalogState &&
    Array.isArray(translationCatalogState.sections?.installed)
  ) {
    for (const entry of translationCatalogState.sections.installed) {
      const id = String(entry.id || "").toLowerCase();
      if (id) {
        ids.add(id);
      }
    }
  }
  return ids;
}

function selectedTranslationId() {
  const fallback = "asv";
  const tabTranslation = String(activeReaderTab()?.translation || "").toLowerCase();
  const stored = String(
    tabTranslation || readLocalStorageValue(BHF_TRANSLATION_STORAGE_KEY) || fallback,
  ).toLowerCase();
  return installedTranslationIds().has(stored) ? stored : fallback;
}

function setSelectedTranslationId(id) {
  const normalized = String(id || "asv").toLowerCase();
  const selected = installedTranslationIds().has(normalized)
    ? normalized
    : "asv";
  const tab = activeReaderTab();
  if (tab) {
    tab.translation = selected;
    tab.data = null;
    persistReaderTabs();
  }
  writeLocalStorageValue(BHF_TRANSLATION_STORAGE_KEY, selected);
  syncTranslationSelect(selected);
}

async function persistReaderDefaultTranslation(id) {
  const normalized = String(id || "asv").toLowerCase();
  if (isDeviceLocalTranslation(normalized)) {
    writeLocalStorageValue(BHF_TRANSLATION_STORAGE_KEY, normalized);
    updateTranslationCatalogDefault(normalized);
    setSelectedTranslationId(normalized);
    return normalized;
  }
  const payload = await requestJson(
    "/api/settings/reader",
    {
      method: "PUT",
      headers: {Accept: "application/json", "Content-Type": "application/json"},
      body: JSON.stringify({default_translation: normalized}),
    },
    "Could not update default translation.",
  );
  const persisted = String(
    payload.default_translation || normalized,
  ).toLowerCase();
  updateTranslationCatalogDefault(persisted);
  setSelectedTranslationId(persisted);
  return persisted;
}

function updateTranslationCatalogDefault(id) {
  const normalized = String(id || "asv").toLowerCase();
  if (!translationCatalogState) {
    return;
  }
  translationCatalogState.default_translation = normalized;
  const markDefault = (entries) => {
    if (!Array.isArray(entries)) {
      return;
    }
    for (const entry of entries) {
      entry.default = String(entry.id || "").toLowerCase() === normalized;
    }
  };
  markDefault(translationCatalogState.translations);
  markDefault(translationCatalogState.catalog);
  for (const entries of Object.values(translationCatalogState.sections || {})) {
    markDefault(entries);
  }
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
  const makeDefault = event.target.closest("[data-translation-make-default]");
  if (!download && !importer && !select && !remove && !makeDefault) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();

  if (download) {
    await downloadTranslationFromGithub(download.dataset.translationDownload);
    await persistReaderDefaultTranslation(download.dataset.translationDownload);
    translationCatalogState = await loadTranslationState("/api/translations/installed");
    renderTranslationSelector(translationCatalogState);
    closeTranslationSelector();
    await reloadCurrentReaderChapter();
    announceStudyResourceChange("translations", "installed");
    return;
  }
  if (select) {
    await persistReaderDefaultTranslation(select.dataset.translationSelect);
    closeTranslationSelector();
    await reloadCurrentReaderChapter();
    return;
  }
  if (makeDefault) {
    await persistReaderDefaultTranslation(
      makeDefault.dataset.translationMakeDefault,
    );
    renderTranslationSelector(translationCatalogState);
    closeTranslationSelector();
    await reloadCurrentReaderChapter();
    return;
  }
  if (importer) {
    closeTranslationSelector();
    await openTranslationImportDialog();
    return;
  }
  if (remove) {
    await removeInstalledTranslation(remove.dataset.translationRemove);
    translationCatalogState = await loadTranslationState("/api/translations/installed");
    renderTranslationSelector(translationCatalogState);
    await reloadCurrentReaderChapter();
    announceStudyResourceChange("translations", "removed");
  }
}

function installTranslation(id) {
  syncTranslationSelectOptions();
}

function installImportedTranslation(id) {
  syncTranslationSelectOptions();
}

async function removeInstalledTranslation(id) {
  const normalized = String(id || "").toLowerCase();
  if (!normalized || normalized === "asv") {
    return;
  }
  if (isDeviceLocalTranslation(normalized)) {
    await removeDeviceTranslation(normalized);
    return;
  }
  await requestJson(
    `/api/translations/${encodeURIComponent(normalized)}`,
    {
      method: "DELETE",
      headers: {Accept: "application/json"},
    },
    "Could not remove translation.",
  );
  const selectedBeforeRemoval = selectedTranslationId();
  if (selectedBeforeRemoval === normalized) {
    setSelectedTranslationId("asv");
  }
}

async function reloadCurrentReaderChapter() {
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  const book = bookSelect?.value || currentChapter?.book || "John";
  const chapter = chapterSelect?.value || currentChapter?.chapter || "1";
  const tab = activeReaderTab();
  if (tab) {
    tab.data = null;
  }
  await loadReaderChapter(book, chapter, {useCache: false});
}

async function downloadTranslationFromGithub(id) {
  const normalized = String(id || "").toLowerCase();
  const metadata = await requestJson(
    `/api/translations/${encodeURIComponent(normalized)}/install`,
    {
      method: "POST",
      headers: {Accept: "application/json"},
    },
    "Could not download translation.",
  );
  persistTranslationDownloadMetadata(normalized, metadata);
  translationCatalogState = await loadTranslationState("/api/translations/installed");
  installTranslation(normalized);
  return metadata;
}

function persistTranslationDownloadMetadata(id, metadata) {
  let stored = {};
  try {
    stored = JSON.parse(
      readLocalStorageValue(BHF_TRANSLATION_DOWNLOAD_METADATA_KEY) || "{}",
    );
  } catch {
    stored = {};
  }
  stored[String(id || "").toLowerCase()] = metadata;
  writeLocalStorageValue(
    BHF_TRANSLATION_DOWNLOAD_METADATA_KEY,
    JSON.stringify(stored),
  );
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
  const translations = Array.isArray(state.translations)
    ? state.translations
    : [];
  const selectedId = String(
    translationSelect.value || selectedTranslationId() || "asv",
  ).toLowerCase();
  translationSelect.replaceChildren();
  for (const entry of translations) {
    const id = String(entry.id || "").toLowerCase();
    if (!id || !entry.installed) {
      continue;
    }
    const option = document.createElement("option");
    option.value = id;
    option.textContent = translationSelectOptionLabel(
      id,
      installedTranslationIds(),
      entry,
    );
    translationSelect.appendChild(option);
  }

  translationSelect.value = translations.some(
    (entry) =>
      entry.installed && String(entry.id || "").toLowerCase() === selectedId,
  )
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

function translationSelectOptionLabel(
  translationId,
  installedIds = installedTranslationIds(),
  entry = null,
) {
  const normalized = String(translationId || "").toLowerCase();
  const resolved = entry || translationCatalogEntry(normalized);
  const abbreviation = resolved?.abbreviation || normalized.toUpperCase();
  const name = resolved?.name || abbreviation;
  return `${abbreviation} - ${name}`;
}

function isDeviceLocalTranslation(translationId) {
  return Boolean(translationCatalogEntry(translationId)?.device_local);
}

async function removeDeviceTranslation(translationId) {
  const offlineDb = window.BHFOfflineDB;
  if (!offlineDb) {
    throw new Error("Device translation storage is unavailable.");
  }
  const remove = offlineDb.remove || offlineDb.delete;
  if (typeof remove !== "function") {
    throw new Error("Device translation storage is unavailable.");
  }
  const normalized = String(translationId || "").toLowerCase();
  await remove.call(offlineDb, "translations", normalized);
  await remove.call(
    offlineDb,
    "apiResponses",
    `/api/translations/${encodeURIComponent(normalized)}/offline-data`,
  );
  if (selectedTranslationId() === normalized) {
    setSelectedTranslationId("asv");
  }
}

async function importTranslationXml() {
  const form = document.querySelector("[data-translation-import-form]");
  const nameInput = form?.querySelector("[data-translation-import-name]");
  const fileInput = form?.querySelector("[data-translation-import-file]");
  const translationName = String(nameInput?.value || "").trim();
  if (!translationName) {
    throw new Error("Enter a translation name.");
  }
  const file =
    fileInput?.files && fileInput.files.length ? fileInput.files[0] : null;
  if (!file) {
    throw new Error("Choose an XML file to import.");
  }
  const normalized = translationIdFromName(translationName);
  if (!normalized) {
    throw new Error(
      "Use at least two letters or numbers in the translation name.",
    );
  }
  const xmlText = await file.text();
  const payload = parseDeviceTranslationXml(
    xmlText,
    normalized,
    translationName,
    file.name || `${normalized}.xml`,
  );
  const offlineDb = window.BHFOfflineDB;
  if (!offlineDb || typeof offlineDb.cacheApiResponse !== "function") {
    throw new Error("Device translation storage is unavailable.");
  }
  await offlineDb.cacheApiResponse(
    `/api/translations/${encodeURIComponent(normalized)}/offline-data`,
    payload,
  );
  const result = {
    translation_id: normalized,
    installed: true,
    availability: "device_local",
    offline_supported: true,
    device_local: true,
  };
  translationCatalogState = await loadTranslationState("/api/translations/installed");
  installImportedTranslation(normalized);
  await persistReaderDefaultTranslation(normalized);
  return result;
}

function announceStudyResourceChange(resource, action) {
  document.dispatchEvent(new CustomEvent("bhf:study-resources-changed", {
    detail: {resource, action},
  }));
}

function parseDeviceTranslationXml(xmlText, translationId, translationName, sourceFilename) {
  const documentNode = new DOMParser().parseFromString(xmlText, "application/xml");
  if (documentNode.querySelector("parsererror")) {
    throw new Error("Bible XML is not well-formed.");
  }
  const root = documentNode.documentElement;
  const books = [];
  const bookElements = Array.from(documentNode.getElementsByTagName("*"))
    .filter((element) => ["book", "biblebook"].includes(xmlLocalName(element)));
  for (const bookElement of bookElements) {
    const bookName = deviceBookName(bookElement);
    if (!bookName) {
      continue;
    }
    const chapters = [];
    for (const chapterElement of Array.from(bookElement.children || [])
      .filter((element) => xmlLocalName(element) === "chapter")) {
      const chapterNumber = xmlPositiveNumber(chapterElement, ["cnumber", "number", "n", "id"]);
      if (!chapterNumber) {
        continue;
      }
      const verses = [];
      for (const verseElement of Array.from(chapterElement.children || [])
        .filter((element) => ["verse", "vers"].includes(xmlLocalName(element)))) {
        const verseNumber = xmlPositiveNumber(verseElement, ["vnumber", "number", "n", "id"]);
        const text = String(verseElement.textContent || "").replace(/\s+/gu, " ").trim();
        if (verseNumber && text) {
          verses.push({book: bookName, chapter: chapterNumber, verse: verseNumber, text});
        }
      }
      if (verses.length) {
        chapters.push({chapter: chapterNumber, verses});
      }
    }
    if (chapters.length) {
      books.push({
        name: bookName,
        order: BHF_CANONICAL_BOOK_NAMES.indexOf(bookName) + 1,
        chapters,
      });
    }
  }
  if (!books.length || !books.some((book) => book.chapters.some((chapter) => chapter.verses.length))) {
    throw new Error("Bible XML contains no readable books and verses.");
  }
  books.sort((left, right) => left.order - right.order);
  const translation = {
    id: translationId.toUpperCase(),
    name: translationName,
    language: root.getAttribute("language") || root.getAttribute("language_code") || "en",
    publication_year: null,
    license: "User imported local XML; BHF does not provide or verify this file",
    source: sourceFilename,
    source_note: "Device-only XML import. This file is not uploaded to BHF.",
  };
  return {
    translation_id: translationId,
    dataset: {translation, books},
    installation: {
      translation_id: translationId,
      installed: true,
      bundled: false,
      availability: "device_local",
      offline_supported: true,
      private_local_install: true,
      device_local: true,
    },
  };
}

function xmlLocalName(element) {
  return String(element?.localName || element?.nodeName || "")
    .split(":")
    .pop()
    .toLowerCase();
}

function xmlAttribute(element, names) {
  for (const name of names) {
    const value = element?.getAttribute(name);
    if (value) {
      return value;
    }
  }
  return "";
}

function xmlPositiveNumber(element, names) {
  const match = String(xmlAttribute(element, names)).match(/\d+/u);
  return match ? Number(match[0]) : 0;
}

function deviceBookName(bookElement) {
  const rawName = xmlAttribute(bookElement, ["bname", "name", "book", "osisID"]);
  const rawNumber = xmlPositiveNumber(bookElement, ["bnumber", "number", "n", "id"]);
  if (rawNumber >= 1 && rawNumber <= BHF_CANONICAL_BOOK_NAMES.length) {
    return BHF_CANONICAL_BOOK_NAMES[rawNumber - 1];
  }
  const compact = rawName.toLowerCase().replace(/[^a-z0-9]/gu, "");
  const aliases = {
    gen: "Genesis", ex: "Exodus", lev: "Leviticus", num: "Numbers", deut: "Deuteronomy",
    ps: "Psalms", psalm: "Psalms", songofsolomon: "Song of Songs", canticles: "Song of Songs",
    rev: "Revelation",
  };
  if (aliases[compact]) {
    return aliases[compact];
  }
  return BHF_CANONICAL_BOOK_NAMES.find(
    (name) => name.toLowerCase().replace(/[^a-z0-9]/gu, "") === compact,
  ) || "";
}

async function openTranslationImportDialog() {
  document.body.classList.add("translation-selector-open");
  try {
    if (!translationCatalogState) {
      translationCatalogState = await loadTranslationState("/api/translations/installed");
    }
    const dialog = ensureTranslationImportDialog();
    renderTranslationImportDialogDetails();
    dialog.hidden = false;
    const nameInput = dialog.querySelector("[data-translation-import-name]");
    if (nameInput) {
      nameInput.value = "";
      nameInput.focus();
    }
    const fileInput = dialog.querySelector("[data-translation-import-file]");
    if (fileInput) {
      fileInput.value = "";
    }
  } catch (error) {
    document.body.classList.remove("translation-selector-open");
    throw error;
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
        <h2 id="translation-import-title">Import Bible</h2>
        <button type="button" class="secondary icon-button" data-close-translation-import aria-label="Close import dialog">×</button>
      </div>
      <div class="translation-selector-body">
        <label class="translation-import-field">
          <span>Translation name</span>
          <input type="text" data-translation-import-name autocomplete="off" required>
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
          <button type="submit">Import Bible</button>
        </div>
      </div>
    </form>
  `;
  dialog.addEventListener("click", (event) => {
    if (
      event.target === dialog ||
      event.target.closest("[data-close-translation-import]")
    ) {
      closeTranslationImportDialog();
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

function renderTranslationImportDialogDetails() {
  const dialog = document.querySelector("[data-translation-import-dialog]");
  const details = dialog?.querySelector("[data-translation-import-details]");
  if (!details) {
    return;
  }
  details.innerHTML = "";
  const notice = document.createElement("p");
  notice.className = "translation-license-explanation";
  notice.textContent =
    "This import stays local to this BHF instance. BHF does not provide, distribute, upload, or verify the file.";
  details.appendChild(notice);
}

function translationIdFromName(name) {
  const normalized = String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/gu, "-")
    .replace(/^-+|-+$/gu, "")
    .slice(0, 32);
  return /^[a-z0-9][a-z0-9_-]{1,31}$/u.test(normalized) ? normalized : "";
}

function translationCatalogEntry(translationId) {
  const id = String(translationId || "").toLowerCase();
  const catalog = Array.isArray(translationCatalogState?.catalog)
    ? translationCatalogState.catalog
    : [];
  return catalog.find((entry) => String(entry.id || "").toLowerCase() === id);
}

async function submitTranslationImportForm(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const confirmed = form.querySelector("[data-translation-import-confirm]");
  if (!confirmed?.checked) {
    return;
  }
  const submit = form.querySelector("button[type='submit']");
  submit.disabled = true;
  try {
    await importTranslationXml();
    closeTranslationImportDialog();
    await reloadCurrentReaderChapter();
    announceStudyResourceChange("translations", "imported");
  } catch (error) {
    const details = form.querySelector("[data-translation-import-details]");
    if (details) {
      details.insertAdjacentHTML(
        "afterbegin",
        errorHtml(error.message || "Could not import translation XML."),
      );
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
  if (
    entry.install_mode === "licensed_provider" ||
    entry.availability === "license_required"
  ) {
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
    importer.textContent = "Import";
    importer.title = "Import a legally obtained Bible file for local-only use.";
    controls.appendChild(importer);
  }
  if (entry.can_download) {
    const download = document.createElement("button");
    download.type = "button";
    download.className = "secondary";
    download.dataset.translationDownload = entry.id;
    download.textContent = "Install for offline use";
    download.title =
      "Download this approved third-party source for offline reading.";
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

function handleVerseSelectionClick(event, verse) {
  if (!verse || !currentChapter) {
    return;
  }

  event.preventDefault();
  event.stopPropagation();

  const verseNumber = Number(verse.dataset.verse || "0");
  if (!verseNumber) {
    return;
  }

  clearDocumentSelection();

  if (event.shiftKey && currentSelection) {
    const context = contextFromVerseRange(
      currentSelection.startVerse,
      verseNumber,
    );
    if (context) {
      applySelectionContext(context);
    }
    return;
  }

  const selectedVerses = selectedVerseNumbers(currentSelection);
  const selectedIndex = selectedVerses.indexOf(verseNumber);
  if (selectedIndex >= 0) {
    selectedVerses.splice(selectedIndex, 1);
  } else {
    selectedVerses.push(verseNumber);
  }

  const context = contextFromVerseNumbers(selectedVerses);
  if (context) {
    applySelectionContext(context);
  } else {
    clearReaderSelection();
  }
}

function handleReaderActionButtonClick(event) {
  activateReaderPaneForElement(event.target);
  const verseSelect = event.target.closest("[data-verse-select]");
  if (!verseSelect) {
    const tappedVerse = event.target.closest("[data-verse]");
    if (tappedVerse && !event.target.closest("a, button, input, select, textarea")) {
      handleVerseSelectionClick(event, tappedVerse);
    }
    return;
  }
  const verse = verseSelect.closest("[data-verse]");
  if (!verse || !currentChapter) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  handleVerseSelectionClick(event, verse);
}

async function handleHighlightedVerseTap(event) {
  if (Date.now() < suppressHighlightedVerseTapUntil) {
    return;
  }
  const verse = event.target.closest("[data-verse]");
  const reader = activeReaderPane() || document.querySelector("#chapter-reader");
  if (!verse || !reader || !reader.contains(verse) || !currentChapter) {
    return;
  }
  const verseNumber = Number(verse.dataset.verse || "0");
  if (!verseNumber || highlightsForVerse(verseNumber).length === 0) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  await removeHighlightsForContext({
    book: currentChapter.book,
    chapter: currentChapter.chapter,
    verseStart: verseNumber,
    verseEnd: verseNumber,
  });
}

function collectSelectedVerseText(startVerse, endVerse) {
  const reader = activeReaderPane() || document.querySelector("#chapter-reader");
  if (!reader) {
    return "";
  }
  return Array.from(reader.querySelectorAll("[data-verse]"))
    .filter((verse) => {
      const number = Number(verse.dataset.verse);
      return startVerse <= number && number <= endVerse;
    })
    .map(
      (verse) => verse.querySelector(".verse-text")?.textContent.trim() || "",
    )
    .join(" ")
    .trim();
}

function scrollToVerse(verseNumber, behavior = "smooth") {
  const reader = activeReaderPane() || document.querySelector("#chapter-reader");
  const verse = reader?.querySelector(`[data-verse="${String(verseNumber)}"]`);
  if (!verse) {
    return;
  }
  verse.scrollIntoView({behavior, block: "center"});
}

function handleReaderContextMenu(event) {
  suppressHighlightedVerseTapUntil = Date.now() + 800;
  activateReaderPaneForElement(event.target);
  const verse = event.target.closest("[data-verse]");
  const reader = document.querySelector("#chapter-reader");
  if (!verse || !reader || !reader.contains(verse) || !currentChapter) {
    return;
  }

  let context = contextForVerseAction(verse);
  const verseNumber = Number(verse.dataset.verse || "0");
  if (
    verseNumber &&
    highlightsForVerse(verseNumber).length > 0 &&
    highlightsForContext(context).length === 0
  ) {
    context = contextFromVerse(verse);
  }
  if (!context) {
    return;
  }

  event.preventDefault();
  contextMenuState = context;
  showContextMenu(event.clientX, event.clientY, context);
}

function handleReaderPointerDown(event) {
  if (event.button && event.button !== 0) {
    suppressHighlightedVerseTapUntil = Date.now() + 800;
  }
  if (event.pointerType !== "touch") {
    cancelReaderLongPress();
    return;
  }
  activateReaderPaneForElement(event.target);
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
  if (
    !readerLongPressState ||
    event.pointerId !== readerLongPressState.pointerId
  ) {
    return;
  }
  const deltaX = Math.abs(event.clientX - readerLongPressState.startX);
  const deltaY = Math.abs(event.clientY - readerLongPressState.startY);
  if (
    deltaX > READER_LONG_PRESS_MOVE_THRESHOLD_PX ||
    deltaY > READER_LONG_PRESS_MOVE_THRESHOLD_PX
  ) {
    cancelReaderLongPress();
    return;
  }
  readerLongPressState.clientX = event.clientX;
  readerLongPressState.clientY = event.clientY;
}

function handleReaderPointerLeave(event) {
  if (
    !readerLongPressState ||
    event.pointerId !== readerLongPressState.pointerId
  ) {
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
  suppressHighlightedVerseTapUntil = Date.now() + 800;
  contextMenuState = context;
  showContextMenu(
    readerLongPressState.clientX,
    readerLongPressState.clientY,
    context,
  );
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
  if (
    !selection ||
    !reader ||
    selection.rangeCount === 0 ||
    selection.isCollapsed
  ) {
    return null;
  }
  const range = selection.getRangeAt(0);
  if (!reader.contains(range.commonAncestorContainer)) {
    return null;
  }
  const rangeElement = range.commonAncestorContainer.nodeType === Node.ELEMENT_NODE
    ? range.commonAncestorContainer
    : range.commonAncestorContainer.parentElement;
  const pane = rangeElement?.closest?.("[data-reader-pane]");
  const tab = pane ? readerTabs.find((candidate) => candidate.id === pane.dataset.readerPane) : null;
  if (tab && tab.id !== activeReaderTabId) {
    activateReaderPaneForElement(rangeElement);
  }
  const selectionReader = activeReaderPane() || reader;
  const selectedVerses = Array.from(
    selectionReader.querySelectorAll("[data-verse]"),
  ).filter((verse) => range.intersectsNode(verse));
  if (selectedVerses.length === 0) {
    return null;
  }
  const selectedText = selection.toString().trim();
  return {
    book: currentChapter.book,
    chapter: currentChapter.chapter,
    startVerse: Number(selectedVerses[0].dataset.verse),
    endVerse: Number(selectedVerses[selectedVerses.length - 1].dataset.verse),
    selectedVerses: selectedVerses.map((verse) => Number(verse.dataset.verse)),
    text: selectedText,
    selectedWord: selectedVerses.length === 1 && /^\S+$/.test(selectedText)
      ? {surfaceForm: selectedText}
      : null,
    isSelection: true,
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
    selectedVerses: [verseNumber],
    text: verse.querySelector(".verse-text")?.textContent.trim() || "",
    isSelection: false,
  };
}

function contextFromVerseRange(startVerse, endVerse) {
  if (!currentChapter) {
    return null;
  }
  const rangeStart = Math.min(Number(startVerse), Number(endVerse));
  const rangeEnd = Math.max(Number(startVerse), Number(endVerse));
  if (!rangeStart || !rangeEnd) {
    return null;
  }
  return {
    book: currentChapter.book,
    chapter: currentChapter.chapter,
    startVerse: rangeStart,
    endVerse: rangeEnd,
    selectedVerses: Array.from({length: rangeEnd - rangeStart + 1}, (_, index) => rangeStart + index),
    text: collectSelectedVerseText(rangeStart, rangeEnd),
    isSelection: rangeStart !== rangeEnd,
  };
}

function selectedVerseNumbers(context) {
  if (!context) {
    return [];
  }
  if (Array.isArray(context.selectedVerses) && context.selectedVerses.length > 0) {
    return Array.from(
      new Set(
        context.selectedVerses
          .map((verseNumber) => Number(verseNumber))
          .filter((verseNumber) => Number.isInteger(verseNumber) && verseNumber > 0),
      ),
    ).sort((left, right) => left - right);
  }
  const startVerse = Number(context.startVerse || 0);
  const endVerse = Number(context.endVerse || startVerse);
  if (!startVerse || !endVerse || endVerse < startVerse) {
    return [];
  }
  return Array.from({length: endVerse - startVerse + 1}, (_, index) => startVerse + index);
}

function contextFromVerseNumbers(verseNumbers) {
  if (!currentChapter) {
    return null;
  }
  const selected = Array.from(
    new Set(
      (verseNumbers || [])
        .map((verseNumber) => Number(verseNumber))
        .filter((verseNumber) => Number.isInteger(verseNumber) && verseNumber > 0),
    ),
  ).sort((left, right) => left - right);
  if (selected.length === 0) {
    return null;
  }
  return {
    book: currentChapter.book,
    chapter: currentChapter.chapter,
    startVerse: selected[0],
    endVerse: selected[selected.length - 1],
    selectedVerses: selected,
    text: selected
      .map((verseNumber) => (activeReaderPane() || document.querySelector("#chapter-reader"))
        ?.querySelector(`[data-verse="${String(verseNumber)}"] .verse-text`)
        ?.textContent.trim() || "")
      .filter(Boolean)
      .join(" "),
    isSelection: selected.length > 1,
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
  if (Array.isArray(context.selectedVerses) && context.selectedVerses.length > 0) {
    return selectedVerseNumbers(context).includes(verseNumber);
  }
  return Number(context.startVerse) <= verseNumber && verseNumber <= Number(context.endVerse || context.startVerse);
}

function showContextMenu(x, y, context) {
  const menu = document.querySelector("#reader-context-menu");
  if (!menu) {
    return;
  }
  const isSelection = Boolean(context.isSelection);
  setContextLabel("ask_bhf", "Ask BHF");
  setContextLabel(
    "cultural_context",
    isSelection ? "Cultural Context" : "Cultural Context",
  );
  setContextLabel(
    "literary_context",
    isSelection ? "Literary Context" : "Literary Context",
  );
  setContextLabel(
    "cross_references",
    isSelection ? "Cross References" : "Cross References",
  );
  setContextLabel(
    "related_ot_themes",
    isSelection ? "Related OT Themes" : "Related OT Themes",
  );
  setContextLabel("people", isSelection ? "People" : "People");
  setContextLabel("places", isSelection ? "Places" : "Places");
  setContextLabel("themes", isSelection ? "Themes" : "Themes");
  setContextLabel(
    "fulfillment_nt",
    isSelection ? "Fulfillment in the NT" : "Fulfillment in the NT",
  );
  setContextLabel(
    "compare_translations",
    isSelection ? "Compare Translations" : "Compare Translations",
  );
  setContextLabel("timeline", isSelection ? "Timeline" : "Timeline");
  setContextLabel("open_map_panel", isSelection ? "Maps" : "Maps");
  setContextLabel("compare_archaeology", "Compare with archaeology");
  setContextLabel("save_study", "Save Study");
  setContextLabel("note", isSelection ? "Add Note" : "Add Note");
  setContextLabel("highlight", isSelection ? "Highlight Selection" : "Highlight Verse");
  setContextLabel("remove_highlight", "Remove Highlight");
  const hasHighlight = highlightsForContext(context).length > 0;
  setContextVisibility("remove_highlight", hasHighlight);
  resetContextSubmenus(menu);
  if (hasHighlight) {
    const actionsTrigger = menu.querySelector('[data-context-submenu="actions"]');
    if (actionsTrigger) {
      openContextSubmenu(actionsTrigger);
    }
  }
  contextMenuPosition = {x, y};
  menu.hidden = false;
  positionContextMenu(menu, x, y);
  const firstButton = menu.querySelector("button");
  if (firstButton) {
    firstButton.focus({preventScroll: true});
  }
}

function positionContextMenu(menu, x, y) {
  const rect = menu.getBoundingClientRect();
  const isNarrowViewport = window.matchMedia("(max-width: 680px)").matches;
  const submenuWidth = isNarrowViewport ? 190 : 230;
  const submenuGap = isNarrowViewport ? 4 : 6;
  const menuWidth = Math.min(rect.width, window.innerWidth - 16);
  if (isNarrowViewport) {
    const menuHeight = Math.min(rect.height, window.innerHeight - 16);
    menu.style.left = "8px";
    menu.style.top = `${Math.max(8, (window.innerHeight - menuHeight) / 2)}px`;
    menu.classList.remove("opens-left");
    return;
  }
  const left = Math.min(x, window.innerWidth - menuWidth - 8);
  const top = Math.min(y, window.innerHeight - rect.height - 8);
  let clampedLeft = Math.max(8, left);
  const clampedTop = Math.max(8, top);
  let opensLeft = false;
  const rightFlyoutFits =
    clampedLeft + menuWidth + submenuGap + submenuWidth <=
    window.innerWidth - 8;
  const leftFlyoutFits = clampedLeft - submenuGap - submenuWidth >= 8;
  if (!rightFlyoutFits && leftFlyoutFits) {
    opensLeft = true;
  } else if (!rightFlyoutFits && !leftFlyoutFits) {
    const pairedWidth = menuWidth + submenuGap + submenuWidth;
    if (pairedWidth <= window.innerWidth - 16) {
      opensLeft = x > window.innerWidth / 2;
      clampedLeft = opensLeft ? window.innerWidth - menuWidth - 8 : 8;
    }
  }
  menu.style.left = `${clampedLeft}px`;
  menu.style.top = `${clampedTop}px`;
  menu.classList.toggle("opens-left", opensLeft);
}

function resetContextSubmenus(
  menu = document.querySelector("#reader-context-menu"),
) {
  if (!menu) {
    return;
  }
  menu.querySelectorAll(".context-menu-section.is-open").forEach((section) => {
    section.classList.remove("is-open");
  });
  menu.querySelectorAll("[data-context-submenu]").forEach((trigger) => {
    trigger.setAttribute("aria-expanded", "false");
  });
}

function openContextSubmenu(trigger) {
  const section = trigger.closest(".context-menu-section");
  const menu = trigger.closest(".context-menu");
  if (!section || !menu || section.classList.contains("is-open")) {
    return;
  }
  resetContextSubmenus(menu);
  section.classList.add("is-open");
  trigger.setAttribute("aria-expanded", "true");
}

function handleContextSubmenuHover(event) {
  const submenuTrigger = event.target.closest("[data-context-submenu]");
  if (submenuTrigger) {
    openContextSubmenu(submenuTrigger);
  }
}

function setContextLabel(action, label) {
  const button = document.querySelector(`[data-context-action="${action}"]`);
  if (button) {
    button.textContent = label;
  }
}

function setContextVisibility(action, visible) {
  const button = document.querySelector(`[data-context-action="${action}"]`);
  if (button) {
    button.hidden = !visible;
  }
}

async function handleContextMenuAction(event) {
  const submenuTrigger = event.target.closest("[data-context-submenu]");
  if (submenuTrigger) {
    event.preventDefault();
    event.stopPropagation();
    openContextSubmenu(submenuTrigger);
    return;
  }
  const button = event.target.closest("[data-context-action]");
  if (!button || !contextMenuState) {
    return;
  }
  const actionType = resolveContextAction(button.dataset.contextAction);
  const context = contextMenuState;
  hideContextMenu();
  if (actionType === "copy") {
    await copyContextToClipboard(context);
    return;
  }
  await dispatchStudyAction(createStudyAction(actionType, context));
}

function resolveContextAction(actionType) {
  return actionType;
}

function formatContextReferenceForClipboard(context) {
  if (!context?.book || !context?.chapter) {
    return "";
  }
  const verses = selectedVerseNumbers(context);
  if (verses.length === 0) {
    return `${context.book} ${context.chapter}`;
  }

  const ranges = [];
  let rangeStart = verses[0];
  let rangeEnd = verses[0];
  verses.slice(1).forEach((verse) => {
    if (verse === rangeEnd + 1) {
      rangeEnd = verse;
      return;
    }
    ranges.push(rangeStart === rangeEnd ? String(rangeStart) : `${rangeStart}-${rangeEnd}`);
    rangeStart = verse;
    rangeEnd = verse;
  });
  ranges.push(rangeStart === rangeEnd ? String(rangeStart) : `${rangeStart}-${rangeEnd}`);
  return `${context.book} ${context.chapter}:${ranges.join(",")}`;
}

function formatContextForClipboard(context) {
  const reference = formatContextReferenceForClipboard(context);
  const text = String(context?.text || "").trim();
  return [reference, text].filter(Boolean).join("\n\n");
}

async function copyContextToClipboard(context) {
  const text = formatContextForClipboard(context);
  if (!text) {
    return false;
  }

  try {
    if (window.navigator?.clipboard?.writeText) {
      await window.navigator.clipboard.writeText(text);
      return true;
    }
  } catch (_error) {
    // Some browser contexts deny Clipboard API access. Fall back below.
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  return copied;
}

function createStudyAction(type, context) {
  const sourceTranslation =
    currentChapter?.translation?.id || selectedTranslationId().toUpperCase();
  const verseStart = context.startVerse == null ? null : Number(context.startVerse);
  const verseEnd = context.endVerse == null
    ? verseStart
    : Number(context.endVerse);
  const selectedWord = context.selectedWord && typeof context.selectedWord === "object"
    ? context.selectedWord
    : {};
  return {
    type,
    book: context.book,
    chapter: Number(context.chapter),
    verseStart,
    verseEnd,
    selectedVerses: selectedVerseNumbers(context),
    selectedText: context.text || "",
    isSelection: Boolean(context.isSelection),
    sourceTranslation,
    selectedWord: Object.keys(selectedWord).length ? {...selectedWord} : null,
    wordPosition: selectedWord.wordPosition || selectedWord.position || null,
    surfaceForm: selectedWord.surfaceForm || selectedWord.surface_form || "",
    lemma: selectedWord.lemma || "",
    language: selectedWord.language || "",
    strongsNumber: selectedWord.strongsNumber || selectedWord.strongs_number || selectedWord.strongs || "",
  };
}

async function dispatchStudyAction(studyAction) {
  studyAction.type =
    BHF_STUDY_ACTION_ALIASES[studyAction.type] || studyAction.type;
  if (studyAction.type === "ask_bhf") {
    applyStudyActionContext(studyAction);
    focusAskPanel();
    setFormValue("ask_mode", "");
    setFormValue("study_action", "");
    setFormValue("deterministic_fact_packet", "");
    setMapContextValue("");
    insertSelectedTextIntoAskQuestion(studyAction);
  } else if (BHF_DETERMINISTIC_STUDY_ACTIONS.has(studyAction.type)) {
    applyStudyActionContext(studyAction);
    await requestDeterministicStudyAction(studyAction);
  } else if (BHF_STUDY_ACTIONS.has(studyAction.type)) {
    applyStudyActionContext(studyAction);
    focusAskPanel();
    setFormValue("ask_mode", studyAction.type);
    setFormValue("study_action", studyAction.type);
    setMapContextValue(buildReaderMapContext(studyAction));
    submitAskForm();
  } else if (studyAction.type === "note") {
    applyStudyActionContext(studyAction);
    openNoteEditor();
  } else if (studyAction.type === "highlight") {
    await createHighlight(studyAction);
  } else if (studyAction.type === "remove_highlight") {
    await removeHighlightsForContext(studyAction);
  } else if (studyAction.type === "save_study") {
    applyStudyActionContext(studyAction);
    await saveLatestStudy();
  } else if (studyAction.type === "open_map_panel") {
    applyStudyActionContext(studyAction);
    setFormValue("ask_mode", "");
    setFormValue("study_action", "");
    openMapPanel(studyAction);
  } else if (studyAction.type === "compare_archaeology") {
    applyStudyActionContext(studyAction);
    setFormValue("ask_mode", "maps");
    setFormValue("study_action", studyAction.type);
    setFormValue(
      "question",
      "What archaeology is connected with this passage or location?",
    );
    setMapContextValue(buildReaderMapContext(studyAction));
    submitAskForm();
  }
}

function companionSelectionContext() {
  const shared = window.BHFStudySelection?.getState?.();
  if (!shared?.book || !shared?.chapter) {
    return currentChapter
      ? {book: currentChapter.book, chapter: currentChapter.chapter}
      : null;
  }
  return {
    book: shared.book,
    chapter: shared.chapter,
    startVerse: shared.startVerse,
    endVerse: shared.endVerse,
    selectedVerses: shared.selectedVerses || [],
    text: shared.selectedText || "",
    selectedWord: shared.selectedWord || null,
    translation: shared.translation || selectedTranslationId(),
    isSelection: (shared.selectedVerses || []).length > 1,
  };
}

async function performCompanionStudyAction(type, overrides = {}) {
  const context = {...(companionSelectionContext() || {}), ...overrides};
  if (!context.book || !context.chapter) {
    if (type === "open_map_panel") {
      openMapPanel({mode: "browse"});
      return true;
    }
    return false;
  }
  await dispatchStudyAction(createStudyAction(type, context));
  return true;
}

function openCompanionAdvancedMenu(trigger) {
  const context = companionSelectionContext();
  if (!context?.startVerse) {
    return false;
  }
  contextMenuState = context;
  const rect = trigger?.getBoundingClientRect?.() || {
    left: window.innerWidth / 2,
    width: 0,
    bottom: window.innerHeight / 2,
  };
  showContextMenu(rect.left + rect.width / 2, rect.bottom + 8, context);
  return true;
}

function openCanonicalQuery(query) {
  activateWorkspaceTab("context");
  const form = document.querySelector("[data-canonical-browser-form]");
  const input = form?.querySelector("[name='q']");
  if (!form || !input) {
    return false;
  }
  input.value = String(query || "");
  input.dispatchEvent(new Event("input", {bubbles: true}));
  if (typeof form.requestSubmit === "function") {
    form.requestSubmit();
  } else {
    form.dispatchEvent(new Event("submit", {bubbles: true, cancelable: true}));
  }
  return true;
}

function savedStudyChapterKey(value) {
  return `${String(value?.book || "").trim().toLowerCase()}|${Number(value?.chapter || 0)}`;
}

function getSavedStudiesForSelection(selection, options = {}) {
  const key = savedStudyChapterKey(selection);
  if (!selection?.book || !selection?.chapter) return Promise.resolve([]);
  if (!options.refresh && savedStudiesCache.has(key)) {
    return Promise.resolve(savedStudiesCache.get(key));
  }
  return requestSavedStudies(selection.book, selection.chapter);
}

async function saveSelectedPassage() {
  const shared = window.BHFStudySelection?.getState?.();
  if (!shared?.book || !shared?.chapter || shared.hasPassageSelection !== true) {
    return false;
  }
  const title = shared.reference || `${shared.book} ${shared.chapter}`;
  await requestJson(
    "/api/saved-studies",
    {
      method: "POST",
      headers: {Accept: "application/json", "Content-Type": "application/json"},
      body: JSON.stringify({
        title,
        book: shared.book,
        chapter: shared.chapter,
        start_verse: shared.startVerse,
        end_verse: shared.endVerse,
        selected_text: shared.selectedText || "",
        source_translation: shared.translation || selectedTranslationId(),
        study_type: "passage",
        question: title,
        answer: shared.selectedText || `Saved passage: ${title}`,
        personal_notes: "",
        canonical_object_ids: [],
      }),
    },
    "Could not save this passage.",
  );
  await loadSavedStudies(shared.book, shared.chapter, {propagateError: true});
  return true;
}

function insertSelectedTextIntoAskQuestion(studyAction) {
  const question = document.querySelector('.ask-form [name="question"]');
  if (!question) {
    return;
  }

  const selectedText = String(studyAction.selectedText || "").trim();
  if (!selectedText) {
    question.focus();
    return;
  }

  const currentText = String(question.value || "");
  if (!currentText.trim()) {
    question.value = selectedText;
  } else if (!currentText.includes(selectedText)) {
    const separator = currentText.endsWith("\n") ? "\n" : "\n\n";
    question.value = `${currentText}${separator}${selectedText}`;
  }

  question.dispatchEvent(new Event("input", {bubbles: true}));
  question.focus();
  if (typeof question.setSelectionRange === "function") {
    const cursorPosition = question.value.length;
    question.setSelectionRange(cursorPosition, cursorPosition);
  }
}

function applyStudyActionContext(studyAction) {
  if (!studyAction.verseStart) {
    window.BHFStudySelection?.setChapter?.({
      book: studyAction.book,
      chapter: studyAction.chapter,
      translation: studyAction.sourceTranslation || selectedTranslationId(),
    }, "study-action-chapter");
    currentSelection = null;
    syncAskFields();
    return;
  }
  applySelectionContext({
    book: studyAction.book,
    chapter: studyAction.chapter,
    startVerse: studyAction.verseStart,
    endVerse: studyAction.verseEnd,
    selectedVerses: studyAction.selectedVerses,
    text: studyAction.selectedText,
    selectedWord: studyAction.selectedWord || null,
    isSelection:
      Boolean(studyAction.isSelection) ||
      studyAction.verseStart !== studyAction.verseEnd,
  });
}

async function requestDeterministicStudyAction(studyAction, options = {}) {
  const isWordStudy = studyAction.type === "word_study";
  if (!options.fromWordStudyChoice) {
    wordStudyNavigationStack = [];
  }
  if (studyAction.type === "archaeology") {
    lastArchaeologyStudyAction = {...studyAction};
  } else if (!options.chapterRefresh) {
    lastArchaeologyStudyAction = null;
  }
  activateWorkspaceTab(isWordStudy ? "lexicon" : "ask");
  setFormValue("ask_mode", "");
  setFormValue("study_action", "");
  setFormValue("deterministic_fact_packet", "");
  setMapContextValue("");

  const answerPanel = document.querySelector(
    isWordStudy ? "#lexicon-panel" : "#answer-panel",
  );
  const statusPanel = document.querySelector("#status-panel");
  activeLiveAnswerPanel = answerPanel;
  latestJobId = null;
  latestJobComplete = false;
  latestDeterministicStudyResult = null;

  if (
    statusPanel &&
    typeof resetStatus === "function" &&
    typeof startWaiting === "function"
  ) {
    resetStatus(statusPanel);
    startWaiting(statusPanel);
  }
  if (answerPanel) {
    answerPanel.setAttribute("aria-busy", "true");
    const loadingMessage = shouldAutoOrganizeContext(studyAction)
      ? `Loading and organizing ${escapeHtml(studyActionLabel(studyAction.type).toLowerCase())}...`
      : `Loading deterministic ${escapeHtml(studyActionLabel(studyAction.type).toLowerCase())}...`;
    answerPanel.innerHTML = `<p class="empty">${loadingMessage}</p>`;
  }

  try {
    const result = await requestJson(
      "/api/study/actions",
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...deterministicStudyPayload(studyAction),
          ...(shouldAutoOrganizeContext(studyAction) ? {presentation: "ai"} : {}),
        }),
      },
      "Could not load deterministic study result.",
    );
    latestDeterministicStudyResult = result;
    if (answerPanel) {
      answerPanel.innerHTML = renderDeterministicStudyResult(result, {
        showWordStudyBack: isWordStudy && wordStudyNavigationStack.length > 0,
      });
      wireDeterministicStudyControls(answerPanel, result, studyAction);
      addMobileAnswerCloseControl(answerPanel);
      revealAnswerPanel(answerPanel);
    }
    if (statusPanel && typeof markStatusComplete === "function") {
      markStatusComplete(statusPanel, {
        message:
          result.presentation?.mode === "ai"
            ? "Organized context ready"
            : result.status === "complete"
            ? "Deterministic result ready"
            : "Partial deterministic result ready",
        percent_complete: 100,
      });
    }
    expandWorkspaceForMobileAnswer();
  } catch (error) {
    if (statusPanel && typeof markStatusFailed === "function") {
      markStatusFailed(statusPanel, error.message || "Request failed.");
    }
    if (answerPanel) {
      const message = error.message || "Request failed.";
      answerPanel.innerHTML = `${errorHtml(message)}${isWordStudy && wordStudyNavigationStack.length > 0 ? `<div class="answer-actions"><button type="button" class="secondary" data-word-study-back>Back to word list</button></div>` : ""}`;
      wireWordStudyBackControl(answerPanel);
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
    selected_verses: studyAction.selectedVerses || [],
    selected_text: studyAction.selectedText || "",
    source_translation:
      studyAction.sourceTranslation || selectedTranslationId(),
    word_position: studyAction.wordPosition || "",
    surface_form: studyAction.surfaceForm || "",
    lemma: studyAction.lemma || "",
    language: studyAction.language || "",
    strongs_number: studyAction.strongsNumber || "",
    query: document.querySelector('.ask-form [name="question"]')?.value || "",
  };
}

function shouldAutoOrganizeContext(studyAction) {
  return BHF_AUTO_ORGANIZED_CONTEXT_ACTIONS.has(studyAction?.type);
}

function renderDeterministicStudyResult(result, options = {}) {
  if (result?.action === "word_study" && result?.metadata?.word_study) {
    return renderWordStudyResult(result, options);
  }
  if (result?.action === "archaeology") {
    return renderArchaeologyResult(result);
  }
  if (result?.presentation && result?.evidence_packet) {
    return renderContextPresentation(result);
  }
  const sections = Array.isArray(result.sections) ? result.sections : [];
  const status = String(result.status || "unknown");
  const source = String(result.source || "deterministic");
  const confidence = Number(result.confidence || 0);
  const sectionHtml = sections.length
    ? sections.map(renderDeterministicSection).join("")
    : `<p class="empty">No deterministic Scripture or CKL facts were found for this action.</p>`;
  const refs = Array.isArray(result.references)
    ? result.references.filter(Boolean)
    : [];
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
          ${result.agent_fallback_allowed ? `<button type="button" class="secondary" data-deterministic-explain>${result.evidence_packet ? "Organize with AI" : "Explain with BHF"}</button>` : ""}
          <button type="button" class="secondary" data-deterministic-ask>Ask a Question</button>
        </div>
      </header>
      ${sectionHtml}
      ${refsHtml}
    </article>
  `;
}

function renderArchaeologyResult(result) {
  const presentation = result.presentation || {};
  const items = Array.isArray(presentation.items)
    ? presentation.items.filter(Boolean).slice(0, 8)
    : [];
  const cards = items.length
    ? items.map((item) => {
        const media = Array.isArray(item.media) ? item.media : [];
        const bundledMedia = media.find(
          (candidate) =>
            candidate &&
            candidate.can_redistribute &&
            candidate.can_cache &&
            (candidate.image_url || candidate.local_asset_path),
        );
        const source = item.source || {};
        const primaryMedia = bundledMedia || media.find((candidate) => candidate && candidate.image_url);
        const attribution = primaryMedia && primaryMedia.attribution_text;
        const imageHtml = bundledMedia
          ? `<figure class="archaeology-media"><img loading="lazy" src="${escapeHtml(bundledMedia.image_url || bundledMedia.local_asset_path)}" alt="${escapeHtml(bundledMedia.title || item.title || "Archaeology evidence")}" onerror="this.hidden=true;this.parentElement.classList.add('archaeology-media--failed')"><figcaption>${escapeHtml(bundledMedia.caption || "")}</figcaption><p class="archaeology-media-failure" aria-live="polite">Image unavailable. Source details remain below.</p></figure>`
          : `<div class="archaeology-media archaeology-media--empty" role="img" aria-label="Archaeology record; image unavailable for redistribution"><strong>Archaeology record</strong><span>Image unavailable for redistribution</span></div>`;
        const references = Array.isArray(item.scripture_references)
          ? item.scripture_references.filter(Boolean)
          : [];
        const cautions = Array.isArray(item.cautions)
          ? item.cautions.filter(Boolean)
          : [];
        const evidenceSources = Array.isArray(item.evidence_sources)
          ? item.evidence_sources.filter((source) => source && source.url)
          : [];
        const detailRows = [
          ["Discovery context", item.discovery_context],
          ["What was found", item.physical_description],
          ["Evidence summary", item.evidence_summary],
          ["Dating basis", item.dating_basis],
          ["Scholarly context", item.scholarly_context],
          ["Current location", item.current_location],
        ].filter(([, value]) => value);
        const detailsHtml = detailRows.length
          ? `<details class="archaeology-card-details"><summary>More details</summary><dl>${detailRows.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}</dl></details>`
          : "";
        const hasCoordinates = item.coordinates && item.coordinates.latitude !== null && item.coordinates.longitude !== null;
        return `
          <article class="archaeology-card" data-archaeology-id="${escapeHtml(item.id || "")}">
            ${imageHtml}
            <div class="archaeology-card-body">
              <p class="archaeology-card-kicker">${escapeHtml([item.item_type, item.date_display || item.period].filter(Boolean).join(" · "))}</p>
              <h3>${escapeHtml(item.title || "Archaeological Evidence")}</h3>
              ${item.site_name ? `<p class="archaeology-card-site">${escapeHtml(item.site_name)}</p>` : ""}
              <section class="archaeology-card-section"><h4>What you're looking at</h4><p>${escapeHtml(item.description || "No description is available.")}</p></section>
              ${item.biblical_relevance || item.significance ? `<section class="archaeology-card-section"><h4>Why it matters here</h4><p>${escapeHtml(item.biblical_relevance || item.significance)}</p></section>` : ""}
              ${item.evidence_summary ? `<section class="archaeology-card-section"><h4>Historical significance</h4><p>${escapeHtml(item.evidence_summary)}</p></section>` : ""}
              <p class="archaeology-card-confidence"><strong>${escapeHtml(String(item.confidence || "Unknown"))}</strong> evidence · ${escapeHtml(String(item.dispute_status || "not_disputed").replaceAll("_", " "))}</p>
              ${cautions.length ? `<aside class="archaeology-card-caution" role="note"><strong>Archaeological caution:</strong> ${escapeHtml(cautions.join(" "))}</aside>` : ""}
              ${detailsHtml}
              ${references.length ? `<p class="archaeology-card-references"><strong>Related passages:</strong> ${escapeHtml(references.join(", "))}</p>` : ""}
              ${attribution ? `<p class="archaeology-card-attribution"><strong>Photo:</strong> ${escapeHtml(attribution)}</p>` : ""}
              ${evidenceSources.length ? `<p class="archaeology-card-provenance"><strong>Data source:</strong> ${evidenceSources.map((source) => `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.label || "Evidence record")} ↗</a>${source.license ? ` <span>(${escapeHtml(source.license)})</span>` : ""}`).join("; ")}</p>` : ""}
              <div class="archaeology-card-actions">
                ${source.url ? `<a class="secondary-link" href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">View Source ↗</a>` : ""}
                ${hasCoordinates ? `<button type="button" class="secondary" data-archaeology-map="${escapeHtml(item.id || "")}">View on Map</button>` : ""}
              </div>
            </div>
          </article>
        `;
      }).join("")
    : `<p class="empty">No curated archaeology evidence was found for this chapter or passage.</p>`;
  return `
    <article class="answer deterministic-study-result archaeology-result" data-deterministic-study-result>
      <header class="answer-header">
        <div>
          <p class="answer-eyebrow">Deterministic archaeological evidence</p>
          <h2>${escapeHtml(result.title || "Archaeology")}</h2>
        </div>
        <div class="answer-actions">
          <button type="button" class="secondary answer-save" data-deterministic-save>Save Study</button>
          <button type="button" class="secondary" data-deterministic-explain>Explain with BHF</button>
          <button type="button" class="secondary" data-deterministic-ask>Ask a Question</button>
        </div>
      </header>
      <p class="archaeology-result-note">Evidence and interpretation are kept distinct. Archaeological records provide historical context and do not by themselves establish theological conclusions.</p>
      <div class="archaeology-card-list">${cards}</div>
    </article>
  `;
}

function renderContextPresentation(result) {
  const presentation = result.presentation || {};
  const facts = Array.isArray(presentation.key_facts)
    ? presentation.key_facts.filter((fact) => fact && fact.fact).slice(0, 6)
    : [];
  const later = Array.isArray(presentation.later_biblical_connections)
    ? presentation.later_biblical_connections.filter((item) => item && item.connection).slice(0, 6)
    : [];
  const sources = Array.isArray(presentation.sources)
    ? presentation.sources.filter(Boolean)
    : [];
  const caution = String(presentation.important_caution || "").trim();
  const confidenceLabel = (value) => {
    const normalized = String(value || "medium").toLowerCase();
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
  };
  const factsHtml = facts.length
    ? facts.map((fact) => `
      <article class="context-fact-card">
        <p class="context-fact">${escapeHtml(fact.fact)}</p>
        ${fact.why_it_matters ? `<p class="context-why"><strong>Why this matters:</strong> ${escapeHtml(fact.why_it_matters)}</p>` : ""}
        <p class="context-confidence">${escapeHtml(confidenceLabel(fact.confidence))} confidence</p>
      </article>
    `).join("")
    : `<p class="empty">No validated original-context facts were found for this selection.</p>`;
  const laterHtml = later.length
    ? `
      <section class="context-later-connections" aria-labelledby="later-biblical-connections-heading">
        <h3 id="later-biblical-connections-heading">Connections elsewhere in the Bible</h3>
        <p class="context-later-note">These connections come from elsewhere in the Bible, not from the passage’s original setting.</p>
        <div class="context-fact-list">
          ${later.map((item) => `
            <article class="context-fact-card context-later-card">
              <p class="context-fact">${escapeHtml(item.connection)}</p>
              ${item.reference ? `<p class="context-reference">${escapeHtml(item.reference)}</p>` : ""}
              <p class="context-confidence">${escapeHtml(confidenceLabel(item.confidence))} confidence</p>
            </article>
          `).join("")}
        </div>
      </section>
    `
    : "";
  const sourcesHtml = sources.length
    ? `
      <details class="context-study-details">
        <summary>Study Details</summary>
        <div class="context-source-list">
          ${sources.map((source) => `
            <div class="context-source-row">
              <strong>${escapeHtml(source.evidence_id || source.record_id || "Evidence")}</strong>
              <span>${escapeHtml([source.scope, source.evidence_type, source.relationship, source.confidence].filter(Boolean).join(" · "))}</span>
              ${source.retrieval_reason ? `<small>${escapeHtml(source.retrieval_reason)}</small>` : ""}
            </div>
          `).join("")}
        </div>
      </details>
    `
    : "";
  return `
    <article class="answer deterministic-study-result context-presentation" data-deterministic-study-result>
      <header class="answer-header">
        <div>
          <p class="answer-eyebrow">${escapeHtml(presentation.mode === "ai" ? "AI-organized validated evidence" : "Validated CKL evidence")}</p>
          <h2>${escapeHtml(result.title || "Context")}</h2>
        </div>
        <div class="answer-actions">
          <button type="button" class="secondary answer-save" data-deterministic-save>Save Study</button>
          ${result.agent_fallback_allowed ? `<button type="button" class="secondary" data-deterministic-explain>Explain with BHF</button>` : ""}
          <button type="button" class="secondary" data-deterministic-ask>Ask a Question</button>
        </div>
      </header>
      <section class="context-overview" aria-labelledby="context-overview-heading">
        <h3 id="context-overview-heading">At a glance</h3>
        <p>${escapeHtml(presentation.summary || "No overview is available.")}</p>
      </section>
      <section class="context-key-facts" aria-labelledby="context-key-facts-heading">
        <h3 id="context-key-facts-heading">What stands out</h3>
        <div class="context-fact-list">${factsHtml}</div>
      </section>
      ${caution ? `<aside class="context-caution" role="note"><strong>Important caution:</strong> ${escapeHtml(caution)}</aside>` : ""}
      ${laterHtml}
      ${sourcesHtml}
      <label class="saved-study-notes-field">
        <span>Personal notes</span>
        <textarea data-personal-notes rows="3" placeholder="Add your reflections or follow-up questions before saving."></textarea>
      </label>
    </article>
  `;
}

function renderWordStudyResult(result, options = {}) {
  const study = result.metadata?.word_study || {};
  const status = String(result.status || study.status || "unknown");
  const source = String(result.source || "ckl_sqlite");
  const confidence = Number(result.confidence || study.confidence || 0);
  const refs = Array.isArray(result.references)
    ? result.references.filter(Boolean)
    : [];
  const refsHtml = refs.length
    ? `<section><h3>References</h3><ul>${refs.map((ref) => `<li>${escapeHtml(ref)}</li>`).join("")}</ul></section>`
    : "";
  const bodyHtml =
    study.status === "ambiguous"
      ? renderWordStudyAmbiguity(study)
      : study.status === "complete"
        ? renderWordStudyComplete(study)
        : renderWordStudyUnavailable(study);
  return `
    <article class="answer deterministic-study-result word-study-result" data-deterministic-study-result>
      <header class="answer-header">
        <div>
          <p class="answer-eyebrow">${escapeHtml(status)} - ${escapeHtml(source)} - ${Math.round(confidence * 100)}% confidence</p>
          <h2>${escapeHtml(result.title || "Word Study")}</h2>
        </div>
        <div class="answer-actions">
          ${options.showWordStudyBack ? `<button type="button" class="secondary word-study-back" data-word-study-back>Back to word list</button>` : ""}
          <button type="button" class="secondary answer-save" data-deterministic-save>Save Study</button>
          ${result.agent_fallback_allowed ? `<button type="button" class="secondary" data-deterministic-explain>Explain in Context</button>` : ""}
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
  const range = Array.isArray(study.lexical_range)
    ? study.lexical_range.filter(Boolean).slice(0, 8)
    : [];
  const context = Array.isArray(study.contextual_information)
    ? study.contextual_information.filter(Boolean)
    : [];
  const sources = Array.isArray(study.sources)
    ? study.sources.filter(Boolean)
    : [];
  return `
    <section class="word-study-reader">
      ${renderWordStudyTranslation(study)}
      <div class="word-study-facts">
        ${facts
          .map(
            ([label, value]) => `
          <div class="word-study-fact">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
          </div>
        `,
          )
          .join("")}
      </div>
      ${range.length ? `<section><h3>Meaning Range</h3><ul>${range.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>` : ""}
      ${context.length ? `<section><h3>Contextual Information</h3><ul>${context.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>` : ""}
      ${sources.length ? `<section><h3>Sources</h3><ul>${sources.map((source) => `<li>${escapeHtml(wordStudySourceLabel(source))}</li>`).join("")}</ul></section>` : ""}
    </section>
    ${renderWordStudyScholar(study)}
  `;
}

function renderWordStudyAmbiguity(study) {
  const ambiguities = Array.isArray(study.ambiguities)
    ? study.ambiguities.filter(Boolean)
    : [];
  return `
    <section class="word-study-reader">
      ${renderWordStudyTranslation(study)}
      <h3>${escapeHtml(study.message || "Multiple possible original-language words found.")}</h3>
      <p class="word-study-order-note">Words are listed in the original text’s reading order. A translation may use a different order or several English words for one original-language word.</p>
      <ol class="word-study-choice-list">
        ${ambiguities
          .map(
            (word) => `
          <li>
            <button type="button" class="word-study-choice" data-word-study-position="${escapeHtml(word.position || "")}" data-word-study-language="${escapeHtml(word.language || "")}" data-word-study-surface="${escapeHtml(word.surface_form || "")}" data-word-study-lemma="${escapeHtml(word.lemma || "")}" data-word-study-strongs="${escapeHtml(word.strongs_number || "")}">
              <strong class="word-study-source-word"${wordStudyLanguageAttributes(word.language)}>${escapeHtml(word.surface_form || word.lemma || "word")}</strong>
              <span>${escapeHtml([word.gloss, word.lemma, word.strongs_number, word.position ? `position ${word.position}` : ""].filter(Boolean).join(" - "))}</span>
            </button>
          </li>
        `,
          )
          .join("")}
      </ol>
    </section>
  `;
}

function renderWordStudyUnavailable(study) {
  const guardrails = Array.isArray(study.guardrails)
    ? study.guardrails.filter(Boolean)
    : [];
  return `
    <section class="word-study-reader">
      ${renderWordStudyTranslation(study)}
      <p class="empty">${escapeHtml(study.message || "No deterministic lexical data was found for this word study.")}</p>
    </section>
    <details class="word-study-scholar">
      <summary>Scholar View</summary>
      ${guardrails.length ? `<section><h3>Safeguards</h3><ul>${guardrails.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>` : ""}
    </details>
  `;
}

function renderWordStudyTranslation(study) {
  const text = String(study.translation_text || "").trim();
  if (!text) {
    return "";
  }
  const translation = String(study.translation_id || "selected").trim().toUpperCase();
  return `
    <section class="word-study-translation" aria-label="Selected translation text">
      <h3>Selected translation${translation ? ` (${escapeHtml(translation)})` : ""}</h3>
      <p>${escapeHtml(text)}</p>
    </section>
  `;
}

function wordStudyLanguageAttributes(language) {
  const normalized = String(language || "").toLowerCase();
  if (normalized === "hebrew" || normalized === "aramaic") {
    return ' lang="he" dir="rtl"';
  }
  if (normalized === "greek") {
    return ' lang="el" dir="ltr"';
  }
  return "";
}

function renderWordStudyScholar(study) {
  const morphologyRows = keyValueRows(study.morphology || {});
  const entries = Array.isArray(study.lexical_entries)
    ? study.lexical_entries.filter(Boolean)
    : [];
  const senses = entries.flatMap((entry) =>
    (entry.senses || []).map((sense) => ({...sense, entry})),
  );
  const occurrences = Array.isArray(study.representative_occurrences)
    ? study.representative_occurrences.filter(Boolean)
    : [];
  const sources = Array.isArray(study.sources)
    ? study.sources.filter(Boolean)
    : [];
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
  const keys = [
    "part_of_speech",
    "stem",
    "conjugation",
    "tense",
    "voice",
    "mood",
    "person",
    "gender",
    "number",
    "case",
    "state",
  ];
  const parts = keys.map((key) => morphology[key]).filter(Boolean);
  return parts.length ? parts.join(", ") : study.morphology_code || "";
}

function keyValueRows(value) {
  return Object.entries(value || {})
    .filter(
      ([, item]) => item !== null && item !== undefined && String(item).trim(),
    )
    .map(([key, item]) => [key.replace(/_/g, " "), String(item)]);
}

function renderKeyValueTable(rows) {
  return `
    <dl class="word-study-key-values">
      ${rows
        .map(
          ([key, value]) => `
        <div>
          <dt>${escapeHtml(key)}</dt>
          <dd>${escapeHtml(value)}</dd>
        </div>
      `,
        )
        .join("")}
    </dl>
  `;
}

function wordStudySourceLabel(source) {
  return (
    [source.name, source.license].filter(Boolean).join(" - ") ||
    "Lexical source"
  );
}

function wordStudyDatasetLabel(source) {
  return [source.name, source.revision, source.license, source.attribution]
    .filter(Boolean)
    .join(" - ");
}

function wordStudySenseLabel(sense) {
  return [sense.gloss, sense.definition, sense.semantic_domain]
    .filter(Boolean)
    .join(" - ");
}

function wordStudyOccurrenceLabel(word) {
  const reference =
    word.reference ||
    [
      word.book,
      word.chapter && word.verse ? `${word.chapter}:${word.verse}` : "",
    ]
      .filter(Boolean)
      .join(" ");
  return [reference, word.surface_form, word.morphology_code]
    .filter(Boolean)
    .join(" - ");
}

function renderDeterministicSection(section) {
  const items = Array.isArray(section.items)
    ? section.items.filter(Boolean)
    : [];
  if (!items.length) {
    return "";
  }
  const cardSectionTitles = new Set(["themes", "people", "places", "cross references"]);
  const sectionTitle = String(section.title || "").trim().toLowerCase();
  const isCardSection = cardSectionTitles.has(sectionTitle);
  const sectionSlug = sectionTitle.replace(/\s+/g, "-");
  const sectionClass = isCardSection
    ? `deterministic-section deterministic-${sectionSlug}-section`
    : "deterministic-section";
  const listClass = isCardSection
    ? "deterministic-item-list deterministic-card-list"
    : "deterministic-item-list";
  return `
    <section class="${sectionClass}">
      <h3>${escapeHtml(section.title || "Section")}</h3>
      <ul class="${listClass}">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </section>
  `;
}

function wireDeterministicStudyControls(answerPanel, result, studyAction) {
  wireWordStudyChoiceControls(answerPanel, studyAction);
  wireWordStudyBackControl(answerPanel);
  answerPanel.querySelectorAll("[data-archaeology-map]").forEach((button) => {
    button.addEventListener("click", () => {
      openMapPanel({
        ...studyAction,
        archaeologyId: button.dataset.archaeologyMap || "",
      });
    });
  });
  answerPanel
    .querySelector("[data-deterministic-explain]")
    ?.addEventListener("click", async () => {
      if (result.action === "archaeology") {
        const packet = result.fact_packet || compactDeterministicResult(result);
        setFormValue("deterministic_fact_packet", JSON.stringify(packet));
        setFormValue("ask_mode", "");
        setFormValue("study_action", result.action || studyAction.type);
        setFormValue(
          "question",
          `Explain ${result.title || "this archaeological evidence"} using BHF, preserving the supplied citations and uncertainty.`,
        );
        submitAskForm();
        return;
      }
      if (result.evidence_packet) {
        await requestAIContextPresentation(studyAction, answerPanel);
        return;
      }
      const packet = result.fact_packet || compactDeterministicResult(result);
      setFormValue("deterministic_fact_packet", JSON.stringify(packet));
      setFormValue("ask_mode", "");
      setFormValue("study_action", result.action || studyAction.type);
      setFormValue(
        "question",
        `Explain ${result.title || "this deterministic study result"} using BHF.`,
      );
      submitAskForm();
    });
  answerPanel
    .querySelector("[data-deterministic-ask]")
    ?.addEventListener("click", () => {
      setFormValue("deterministic_fact_packet", "");
      focusAskPanel();
      const question = document.querySelector('.ask-form [name="question"]');
      if (question) {
        question.value = "";
      }
    });
  answerPanel
    .querySelector("[data-deterministic-save]")
    ?.addEventListener("click", async () => {
      await saveDeterministicStudy(result, studyAction);
    });
}

async function requestAIContextPresentation(studyAction, answerPanel) {
  const statusPanel = document.querySelector("#status-panel");
  if (answerPanel) {
    answerPanel.setAttribute("aria-busy", "true");
    answerPanel.innerHTML = `<p class="empty">Organizing validated evidence...</p>`;
  }
  try {
    const result = await requestJson(
      "/api/study/actions",
      {
        method: "POST",
        headers: {Accept: "application/json", "Content-Type": "application/json"},
        body: JSON.stringify({...deterministicStudyPayload(studyAction), presentation: "ai"}),
      },
      "Could not organize the context result.",
    );
    if (answerPanel) {
      answerPanel.innerHTML = renderDeterministicStudyResult(result, {
        showWordStudyBack: wordStudyNavigationStack.length > 0,
      });
      wireDeterministicStudyControls(answerPanel, result, studyAction);
      addMobileAnswerCloseControl(answerPanel);
    }
  } catch (error) {
    if (answerPanel) {
      const message = error.message || "Could not organize the context result.";
      answerPanel.innerHTML = `${errorHtml(message)}${wordStudyNavigationStack.length > 0 ? `<div class="answer-actions"><button type="button" class="secondary" data-word-study-back>Back to word list</button></div>` : ""}`;
      wireWordStudyBackControl(answerPanel);
      addMobileAnswerCloseControl(answerPanel);
    }
  } finally {
    if (answerPanel) {
      answerPanel.removeAttribute("aria-busy");
    }
    if (statusPanel && typeof markStatusComplete === "function") {
      markStatusComplete(statusPanel, {message: "Context result ready", percent_complete: 100});
    }
  }
}

function wireWordStudyBackControl(answerPanel) {
  answerPanel
    ?.querySelector("[data-word-study-back]")
    ?.addEventListener("click", () => restorePreviousWordStudy(answerPanel));
}

function restorePreviousWordStudy(answerPanel) {
  const previous = wordStudyNavigationStack.pop();
  if (!previous || !answerPanel) {
    return;
  }
  applyStudyActionContext(previous.studyAction);
  latestDeterministicStudyResult = previous.result;
  answerPanel.innerHTML = renderDeterministicStudyResult(previous.result, {
    showWordStudyBack: wordStudyNavigationStack.length > 0,
  });
  wireDeterministicStudyControls(answerPanel, previous.result, previous.studyAction);
  addMobileAnswerCloseControl(answerPanel);
  revealAnswerPanel(answerPanel);
}

function wireWordStudyChoiceControls(answerPanel, studyAction) {
  answerPanel
    .querySelectorAll("[data-word-study-position]")
    .forEach((button) => {
      button.addEventListener("click", async () => {
        const wordPosition = Number(button.dataset.wordStudyPosition || "0");
        if (!wordPosition) {
          return;
        }
        if (latestDeterministicStudyResult) {
          wordStudyNavigationStack.push({
            result: latestDeterministicStudyResult,
            studyAction: {...studyAction},
          });
        }
        const selectedWord = {
          wordPosition,
          language: button.dataset.wordStudyLanguage || "",
          surfaceForm: button.dataset.wordStudySurface || "",
          lemma: button.dataset.wordStudyLemma || "",
          strongsNumber: button.dataset.wordStudyStrongs || "",
        };
        const nextAction = {
          ...studyAction,
          type: "word_study",
          ...selectedWord,
          selectedWord,
        };
        applyStudyActionContext(nextAction);
        await requestDeterministicStudyAction(nextAction, {fromWordStudyChoice: true});
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
      word_study_prompt_context:
        result.metadata?.word_study_prompt_context || "",
    },
  };
}

async function saveDeterministicStudy(result, studyAction) {
  const notesField = document.querySelector("#answer-panel [data-personal-notes]");
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
    personal_notes: notesField?.value || "",
    canonical_object_ids: result.metadata?.object_ids || [],
  };
  await requestJson(
    "/api/saved-studies",
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    "Could not save deterministic study.",
  );
  await loadSavedStudies(currentChapter?.book, currentChapter?.chapter);
}

function deterministicStudyMarkdown(result) {
  if (result.presentation && result.evidence_packet) {
    return contextPresentationMarkdown(result);
  }
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

function contextPresentationMarkdown(result) {
  const presentation = result.presentation || {};
  const lines = [`# ${result.title || "Context"}`, ""];
  if (presentation.summary) {
    lines.push(String(presentation.summary), "");
  }
  const facts = Array.isArray(presentation.key_facts) ? presentation.key_facts : [];
  if (facts.length) {
    lines.push("## What Stands Out");
    facts.forEach((fact) => {
      if (!fact?.fact) {
        return;
      }
      const why = fact.why_it_matters ? ` — ${fact.why_it_matters}` : "";
      lines.push(`- ${fact.fact}${why}`);
    });
    lines.push("");
  }
  if (presentation.important_caution) {
    lines.push("## Important Caution", String(presentation.important_caution), "");
  }
  const connections = Array.isArray(presentation.later_biblical_connections)
    ? presentation.later_biblical_connections
    : [];
  if (connections.length) {
    lines.push("## Connections Elsewhere in the Bible");
    connections.forEach((connection) => {
      if (connection?.connection) {
        lines.push(`- ${connection.connection}${connection.reference ? ` (${connection.reference})` : ""}`);
      }
    });
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
    form.dispatchEvent(new Event("submit", {bubbles: true, cancelable: true}));
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
      `The local curated map dataset has no direct match for ${reference}. Give a cautious text-only geography explanation, identify any explicit or implied locations or regions, and clearly label uncertainty.`,
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

function keepContextMenuVisibleOnReaderScroll(event) {
  const menu = document.querySelector("#reader-context-menu");
  if (
    !menu ||
    menu.hidden ||
    menu.contains(event.target) ||
    !contextMenuPosition
  ) {
    return;
  }
  positionContextMenu(menu, contextMenuPosition.x, contextMenuPosition.y);
}

function hideContextMenu() {
  const menu = document.querySelector("#reader-context-menu");
  if (menu) {
    menu.hidden = true;
    resetContextSubmenus(menu);
  }
  contextMenuState = null;
  contextMenuPosition = null;
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
  const reader = activeReaderPane() || document.querySelector("#chapter-reader");
  if (!reader || !context) {
    return;
  }

  const selectedVerses = selectedVerseNumbers(context);
  currentSelection = {
    ...context,
    selectedVerses,
    startVerse: selectedVerses[0] || Number(context.startVerse),
    endVerse: selectedVerses[selectedVerses.length - 1] || Number(context.endVerse || context.startVerse),
    isSelection: selectedVerses.length > 1,
  };
  window.BHFStudySelection?.setSelection?.({
    book: currentSelection.book,
    chapter: currentSelection.chapter,
    startVerse: currentSelection.startVerse,
    endVerse: currentSelection.endVerse,
    selectedVerses: currentSelection.selectedVerses,
    selectedText: currentSelection.text,
    translation: currentChapter?.translation?.id || selectedTranslationId(),
    selectedWord: currentSelection.selectedWord || null,
  }, "reader-selection");
  const tab = activeReaderTab();
  if (tab) {
    tab.selection = {...currentSelection};
  }
  rememberReaderLocation(Number(context.startVerse));

  reader.querySelectorAll("[data-verse]").forEach((verse) => {
    const verseNumber = Number(verse.dataset.verse || "0");
    const selected = selectedVerses.includes(verseNumber);

    verse.classList.toggle("selected", selected);

    const verseButton = verse.querySelector("[data-verse-select]");
    if (verseButton) {
      verseButton.setAttribute("aria-pressed", String(selected));
      verseButton.setAttribute(
        "aria-label",
        selected
          ? `Deselect ${currentChapter.book} ${currentChapter.chapter}:${verseNumber}`
          : `Select ${currentChapter.book} ${currentChapter.chapter}:${verseNumber}`,
      );
    }
  });

  syncAskFields();
  if (window.BHFCommentary && typeof window.BHFCommentary.focusSelection === "function") {
    window.BHFCommentary.focusSelection(currentSelection);
  }
}

function clearReaderSelection() {
  const reader = activeReaderPane() || document.querySelector("#chapter-reader");

  if (reader) {
    reader.querySelectorAll("[data-verse]").forEach((verse) => {
      verse.classList.remove("selected");

      const verseNumber = Number(verse.dataset.verse || "0");
      const verseButton = verse.querySelector("[data-verse-select]");

      if (verseButton) {
        verseButton.setAttribute("aria-pressed", "false");

        if (currentChapter) {
          verseButton.setAttribute(
            "aria-label",
            `Select ${currentChapter.book} ${currentChapter.chapter}:${verseNumber}`,
          );
        }
      }
    });
  }

  currentSelection = null;
  window.BHFStudySelection?.clearSelection?.("reader-selection-clear");
  const tab = activeReaderTab();
  if (tab) {
    tab.selection = null;
    persistReaderTabs();
  }
  syncAskFields();
  if (window.BHFCommentary && typeof window.BHFCommentary.clearSelection === "function") {
    window.BHFCommentary.clearSelection();
  }
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
  return currentHighlights.filter((highlight) =>
    rangesOverlap(
      startVerse,
      endVerse,
      Number(highlight.start_verse),
      Number(highlight.end_verse || highlight.start_verse),
    ),
  );
}

function isContextHighlighted(context) {
  return highlightsForContext(context).length > 0;
}

function notesForVerse(verseNumber) {
  return currentNotes.filter((note) =>
    highlightContainsVerse(note, verseNumber),
  );
}

function highlightsForVerse(verseNumber) {
  return currentHighlights.filter((highlight) =>
    highlightContainsVerse(highlight, verseNumber),
  );
}

function highlightContainsVerse(record, verseNumber) {
  const startVerse = Number(record.start_verse || record.verseStart || 0);
  const endVerse = Number(record.end_verse || record.verseEnd || startVerse);
  return Boolean(
    startVerse &&
    endVerse &&
    startVerse <= verseNumber &&
    verseNumber <= endVerse,
  );
}

function rangesOverlap(startA, endA, startB, endB) {
  return startA <= endB && startB <= endA;
}

function applyVerseStateIndicatorsToReader() {
  const reader = activeReaderPane() || document.querySelector("#chapter-reader");
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
    const highlightColors = Array.from(
      new Set(
        highlights
          .map((highlight) => String(highlight.color || "").trim())
          .filter(Boolean),
      ),
    );

    verse.classList.toggle("has-notes", notes.length > 0);
    verse.classList.toggle("has-highlights", highlightColors.length > 0);
    indicatorContainer.innerHTML = "";
    const indicatorLabels = [];

    if (notes.length > 0) {
      const noteIndicator = document.createElement("span");
      noteIndicator.className = "verse-state-indicator verse-state-note";
      noteIndicator.title =
        notes.length === 1 ? "Has note" : `Has ${notes.length} notes`;
      noteIndicator.textContent = "N";
      noteIndicator.setAttribute("aria-hidden", "true");
      indicatorLabels.push(
        notes.length === 1 ? "Has note" : `Has ${notes.length} notes`,
      );
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
  const studySelection = window.BHFStudySelection?.getState?.() || {
    book: currentChapter.book,
    chapter: currentChapter.chapter,
    startVerse: currentSelection?.startVerse || null,
    endVerse: currentSelection?.endVerse || null,
    selectedVerses: currentSelection?.selectedVerses || [],
    selectedText: currentSelection?.text || "",
    translation: selectedTranslationId(),
    hasPassageSelection: Boolean(currentSelection),
  };
  setFormValue("reader_book", studySelection.book || currentChapter.book);
  setFormValue("reader_chapter", studySelection.chapter || currentChapter.chapter);
  setFormValue(
    "reader_start_verse",
    studySelection.hasPassageSelection ? studySelection.startVerse : "",
  );
  setFormValue(
    "reader_end_verse",
    studySelection.hasPassageSelection ? studySelection.endVerse : "",
  );
  setFormValue(
    "reader_selected_verses",
    studySelection.hasPassageSelection ? JSON.stringify(studySelection.selectedVerses || []) : "",
  );
  setFormValue(
    "reader_selected_text",
    studySelection.hasPassageSelection ? studySelection.selectedText : "",
  );
  setFormValue(
    "reader_selected_word",
    studySelection.selectedWord ? JSON.stringify(studySelection.selectedWord) : "",
  );
  setFormValue("reader_translation", studySelection.translation || selectedTranslationId());

  const summary = document.querySelector("#selection-summary");
  const addNoteButton = document.querySelector("[data-add-note]");
  if (studySelection.hasPassageSelection) {
    const reference = studySelection.reference || formatReference(
      studySelection.book,
      studySelection.chapter,
      studySelection.startVerse,
      studySelection.endVerse,
    );
    const translationLabel = translationSelectOptionLabel(
      selectedTranslationId(),
      installedTranslationIds(),
    );
    if (summary) {
      summary.textContent = `Selected ${translationLabel} ${reference}`;
    }
    if (addNoteButton) {
      addNoteButton.disabled = false;
    }
  } else {
    if (summary) {
      summary.textContent = "";
    }
    if (addNoteButton) {
      addNoteButton.disabled = false;
    }
  }
  if (noteContext) {
    refreshNoteReferenceActions();
  }
  if (notesView === "passage") {
    renderNotes(notesForCurrentPassage());
  }
}

function updateChapterNavigationState() {
  const bookSelect = document.querySelector("[data-reader-book]");
  const chapterSelect = document.querySelector("[data-reader-chapter]");
  const nextButtons = document.querySelectorAll("[data-next-chapter]");
  const prevButtons = document.querySelectorAll("[data-prev-chapter]");
  if (
    !bookSelect ||
    !chapterSelect ||
    (nextButtons.length === 0 && prevButtons.length === 0)
  ) {
    return;
  }
  const selectedBook = bookSelect.selectedOptions[0] || bookSelect.options[0];
  const chapterCount = Number(
    selectedBook?.dataset.chapters || chapterSelect.options.length || 0,
  );
  const currentChapterNumber = Number(chapterSelect.value || "0");
  const available = Boolean(
    chapterCount && currentChapterNumber && currentChapterNumber < chapterCount,
  );
  const canGoBack = Boolean(currentChapterNumber && currentChapterNumber > 1);
  nextButtons.forEach((button) => {
    button.disabled = !available;
    button.setAttribute(
      "aria-label",
      available
        ? `Go to chapter ${currentChapterNumber + 1}`
        : "No next chapter available",
    );
    button.title = available ? "Next chapter" : "No next chapter available";
  });
  prevButtons.forEach((button) => {
    button.disabled = !canGoBack;
    button.setAttribute(
      "aria-label",
      canGoBack
        ? `Go to chapter ${currentChapterNumber - 1}`
        : "No previous chapter available",
    );
    button.title = canGoBack
      ? "Previous chapter"
      : "No previous chapter available";
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
    source_translation:
      studyAction.sourceTranslation ||
      translationSelectOptionLabel(
        selectedTranslationId(),
        installedTranslationIds(),
      ),
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
    const hasPassageContext = Boolean(
      context && (context.book || context.chapter),
    );
    window.BHFMaps.openMapPanel(hasPassageContext ? context : {mode: "browse"});
    return;
  }
  const hasPassageContext = Boolean(
    context && (context.book || context.chapter),
  );
  window.BHFPendingMapPanelContext = hasPassageContext
    ? context
    : {mode: "browse"};
}

async function pollJob(form, statusPanel, jobId) {
  while (true) {
    const status = await requestJson(
      form.dataset.statusBase + jobId,
      {
        headers: {Accept: "application/json"},
      },
      "Could not read request status.",
    );

    renderStatus(statusPanel, status);
    if (status.done) {
      return status;
    }
    await delay(POLL_INTERVAL_MS);
  }
}
