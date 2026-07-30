import { createBibleMap } from "./BibleMap.js";
import {
  getOrderedJourneyStops,
  loadJourneyCatalog,
} from "./JourneyMapData.js";
import {
  loadMapCatalog,
  loadPlacesForPassage,
  loadRoutesForPassage,
  searchMapCatalog,
} from "./mapService.js?v=20260630";
import {
  renderMapOrientationCard,
  renderSelectedMarker as renderSelectedMarkerHtml,
  renderSelectedRoute as renderSelectedRouteHtml,
} from "./MapPanelContent.js";
import {
  buildCautionNote,
  buildPlaceExplanation,
  buildRouteCautionNote,
  buildRouteExplanation,
  escapeHtml,
  buildSourceText,
} from "./MapPanelText.js";
import { normalizeHistoricalPeriod } from "./MapPanelStateHelpers.js";
import { buildGoogleEarthUrl } from "./MapExternalLinks.js";

// Source links still point to `/sources/` in the rendered map panel markup.
const BHF_HTTP = window.BHFApi || {};

let mapController = null;
let selectedMarker = null;
let selectedRoute = null;
let mapMode = "passage";
let lastPassageContext = null;
let loadedMarkers = [];
let loadedRoutes = [];
let loadedJourneys = [];
let selectedJourneyId = "";
let selectedJourneyStopId = "";
let selectedJourneySegmentId = "";
let studyMode = "passage";
let journeyVisibility = true;
let browseSearchResults = [];
let browseSearchQuery = "";
let browseSearchKind = "all";
let browseSearchPeriod = "all";
let historicalPeriod = "all";
let timelinePeriodOptions = [
  { value: "all", label: "All periods" },
  { value: "Broad / uncertain period", label: "Broad / uncertain period" },
  { value: "Divided Kingdom", label: "Divided Kingdom" },
  { value: "Assyrian period", label: "Assyrian period" },
  { value: "Babylonian period", label: "Babylonian period" },
  { value: "Persian period", label: "Persian period" },
  { value: "Hellenistic period", label: "Hellenistic period" },
  { value: "NT / Roman period", label: "NT / Roman period" },
];
let mapModalOpen = false;
let lastModalTrigger = null;

function requestJson(url, options = {}, fallbackMessage = "Request failed.") {
  if (typeof BHF_HTTP.requestJson === "function") {
    return BHF_HTTP.requestJson(url, options, fallbackMessage);
  }
  const resolvedUrl = typeof BHF_HTTP.resolveUrl === "function" ? BHF_HTTP.resolveUrl(url) : url;
  return fetch(resolvedUrl, options).then(async (response) => {
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || fallbackMessage);
    }
    return data;
  });
}

function getPanelElements() {
  return {
    panel: document.querySelector("#map-panel"),
    status: document.querySelector("#map-panel-status"),
    pinHint: document.querySelector("#map-pin-hint"),
    pinHintSummary: document.querySelector("#map-pin-hint-summary"),
    pinHintText: document.querySelector("#map-pin-hint-text"),
    stage: document.querySelector("#map-stage"),
    reference: document.querySelector("#map-panel-reference"),
    details: document.querySelector("#map-details"),
    historicalPeriod: document.querySelector("[data-historical-period]"),
    mapBrowser: document.querySelector("[data-map-browser]"),
    studyMode: document.querySelector("[data-map-study-mode]"),
    contextSummary: document.querySelector("[data-map-context-summary]"),
    navigator: document.querySelector("#map-study-navigator"),
    navigatorOpen: document.querySelector("[data-map-navigator-open]"),
    detailsColumn: document.querySelector("#map-details-column"),
    detailsOpen: document.querySelector("[data-map-details-open]"),
    mapSearchQuery: document.querySelector("[data-map-search-query]"),
    mapSearchKind: document.querySelector("[data-map-search-kind]"),
    mapSearchPeriod: document.querySelector("[data-map-search-period]"),
    mapSearchSubmit: document.querySelector("[data-map-search-submit]"),
    mapSearchClear: document.querySelector("[data-map-search-clear]"),
    mapSearchResults: document.querySelector("#map-search-results"),
    mapSearchResultsCount: document.querySelector("#map-search-results-count"),
    mapSearchResultsList: document.querySelector("#map-search-results-list"),
    journeySelector: document.querySelector("[data-map-journey-selector]"),
    journeyToggle: document.querySelector("[data-map-journey-toggle]"),
    workspace: document.querySelector("#map-workspace"),
    inlineHost: document.querySelector("#map-workspace-inline-host"),
    modal: document.querySelector("#map-modal"),
    modalHost: document.querySelector("#map-workspace-modal-host"),
  };
}

function renderPeriodOptions(options = timelinePeriodOptions) {
  return (Array.isArray(options) && options.length ? options : timelinePeriodOptions)
    .map((option) => `<option value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</option>`)
    .join("");
}

function applyTimelineOptions(options = timelinePeriodOptions) {
  const normalizedOptions = Array.isArray(options) && options.length > 0 ? options : timelinePeriodOptions;
  timelinePeriodOptions = normalizedOptions;
  const markup = renderPeriodOptions(normalizedOptions);
  const { historicalPeriod: historicalPeriodSelect, mapSearchPeriod } = getPanelElements();
  if (historicalPeriodSelect) {
    historicalPeriodSelect.innerHTML = markup;
    historicalPeriodSelect.value = normalizeHistoricalPeriod(historicalPeriod, normalizedOptions);
  }
  if (mapSearchPeriod) {
    mapSearchPeriod.innerHTML = markup;
    mapSearchPeriod.value = normalizeHistoricalPeriod(browseSearchPeriod, normalizedOptions);
  }
}

function formatReference(context) {
  if (!context || !context.book || !context.chapter) {
    return "";
  }
  const verseStart = Number(context.verseStart || context.startVerse || 0);
  const verseEnd = Number(context.verseEnd || context.endVerse || verseStart || 0);
  if (!verseStart) {
    return `${context.book} ${context.chapter}`;
  }
  return verseStart === verseEnd
    ? `${context.book} ${context.chapter}:${verseStart}`
    : `${context.book} ${context.chapter}:${verseStart}-${verseEnd}`;
}

function normalizeConfidenceClass(value) {
  return String(value || "unknown").trim().toLowerCase().replace(/\s+/g, "-") || "unknown";
}

function getSelectedJourney() {
  return loadedJourneys.find((journey) => journey.id === selectedJourneyId) || null;
}

function getVisibleJourneys() {
  return loadedJourneys;
}

function getSelectedJourneyStop(journey = getSelectedJourney()) {
  if (!journey || !selectedJourneyStopId) {
    return null;
  }
  return (journey.stops || []).find((stop) => stop.id === selectedJourneyStopId) || null;
}

function getSelectedJourneySegment(journey = getSelectedJourney()) {
  if (!journey || !selectedJourneySegmentId) {
    return null;
  }
  return (journey.segments || []).find((segment) => segment.id === selectedJourneySegmentId) || null;
}

function syncJourneyControls() {
  const { journeySelector, journeyToggle } = getPanelElements();
  const visibleJourneys = getVisibleJourneys();

  if (journeyToggle) {
    journeyToggle.checked = journeyVisibility;
  }
  if (journeySelector) {
    const selectedStillVisible = visibleJourneys.some((journey) => journey.id === selectedJourneyId);
    journeySelector.innerHTML = [
      `<option value="">${visibleJourneys.length ? "Choose a journey" : "No matching journeys"}</option>`,
      ...visibleJourneys.map((journey) =>
        `<option value="${escapeHtml(journey.id)}" ${journey.id === selectedJourneyId && selectedStillVisible ? "selected" : ""}>${escapeHtml(journey.title)}</option>`
      ),
    ].join("");
    journeySelector.value = selectedStillVisible ? selectedJourneyId : "";
  }
}

function renderJourneySidebar() {
  // Journey controls stay compact beside search so place results keep their space.
  syncJourneyControls();
}

function renderSupplementalControls() {
  renderJourneySidebar();
  syncStudyMode();
}

function syncStudyMode() {
  const { studyMode: studyModeSelect, contextSummary } = getPanelElements();
  if (studyModeSelect) {
    studyModeSelect.value = studyMode;
  }
  if (!contextSummary) {
    return;
  }
  const messages = {
    passage: lastPassageContext
      ? `Showing places and routes connected to ${formatReference(lastPassageContext)}.`
      : "Open a passage to focus the map on its chapter context.",
    places: "Search for a place to focus the map on one location and its related passages.",
    journeys: "Choose a curated journey to see numbered stops and an approximate route.",
    events: "Event records are not available in the local map data yet.",
  };
  contextSummary.textContent = messages[studyMode] || messages.passage;
}

function setStudyMode(nextMode) {
  const allowed = new Set(["passage", "places", "journeys", "events"]);
  studyMode = allowed.has(nextMode) ? nextMode : "passage";
  syncStudyMode();
}

function getLoadContext(context = {}) {
  return {
    ...context,
    period: historicalPeriod,
  };
}

async function loadPassageMapData(context = {}) {
  const loadContext = getLoadContext(context);
  const [
    placeResult,
    routeResult,
  ] = await Promise.all([
    loadPlacesForPassage(loadContext),
    loadRoutesForPassage(loadContext),
  ]);
  const offline = [
    placeResult,
    routeResult,
  ].some((result) => Boolean(result?.offline));
  return {
    placeResult,
    routeResult,
    offline,
  };
}

async function loadBrowseMapData() {
  return {
    placeResult: { markers: [] },
    routeResult: { routes: [] },
    offline: false,
  };
}

async function loadMapData(context = {}) {
  return mapMode === "browse" ? loadBrowseMapData() : loadPassageMapData(context);
}

async function loadSupplementalMapData() {
  const journeyCatalog = await loadJourneyCatalog();
  loadedJourneys = journeyCatalog.journeys || [];
  if (selectedJourneyId && !loadedJourneys.some((journey) => journey.id === selectedJourneyId)) {
    selectedJourneyId = "";
    selectedJourneyStopId = "";
    selectedJourneySegmentId = "";
  }
}

function setStatus(message, kind = "loading") {
  const { status } = getPanelElements();
  if (!status) {
    return;
  }
  status.hidden = false;
  status.dataset.state = kind;
  status.textContent = message;
}

function clearStatus() {
  const { status } = getPanelElements();
  if (!status) {
    return;
  }
  status.hidden = true;
  status.textContent = "";
  delete status.dataset.state;
}

function setPinHint(message = "", options = {}) {
  const { pinHint, pinHintSummary, pinHintText } = getPanelElements();
  if (!pinHint || !pinHintSummary || !pinHintText) {
    return;
  }
  const { open = false, summary = "Why no pin?" } = options;
  if (!message) {
    pinHint.hidden = true;
    pinHint.open = false;
    pinHintSummary.textContent = "Why no pin?";
    pinHintText.textContent = "";
    return;
  }
  pinHint.hidden = false;
  pinHint.open = Boolean(open);
  pinHintSummary.textContent = summary;
  pinHintText.textContent = message;
}

function ensurePanelVisible(context) {
  const { panel, reference } = getPanelElements();
  const emptyState = document.querySelector("[data-map-pane-empty]");
  if (!panel) {
    throw new Error("Map panel is missing.");
  }
  panel.hidden = false;
  if (emptyState) {
    emptyState.hidden = true;
  }
  if (reference) {
    reference.textContent = formatReference(context);
  }
  document.dispatchEvent(new CustomEvent("bhf:map-panel-opened"));
}

function syncMapViewport() {
  if (!mapController || typeof mapController.invalidateSize !== "function") {
    return;
  }
  window.requestAnimationFrame(() => {
    mapController.invalidateSize();
  });
}

function moveWorkspaceToHost(hostType) {
  const { workspace, inlineHost, modalHost } = getPanelElements();
  if (!workspace || !inlineHost || !modalHost) {
    return;
  }
  const targetHost = hostType === "modal" ? modalHost : inlineHost;
  if (!targetHost || workspace.parentElement === targetHost) {
    workspace.dataset.mapHost = hostType;
    syncMapViewport();
    return;
  }
  targetHost.appendChild(workspace);
  workspace.dataset.mapHost = hostType;
  syncMapViewport();
}

function setMapMode(nextMode) {
  mapMode = nextMode === "browse" ? "browse" : "passage";
  const { mapBrowser, mapSearchResults } = getPanelElements();
  if (mapBrowser) {
    mapBrowser.hidden = mapMode !== "browse";
  }
  if (mapSearchResults) {
    mapSearchResults.hidden = mapMode !== "browse";
  }
}

function getMapSearchState() {
  const { mapSearchQuery, mapSearchKind, mapSearchPeriod } = getPanelElements();
  return {
    query: mapSearchQuery?.value?.trim() || "",
    kind: mapSearchKind?.value || "all",
    period: mapSearchPeriod?.value || historicalPeriod || "all",
  };
}

function syncMapSearchState() {
  const { mapSearchPeriod } = getPanelElements();
  if (mapSearchPeriod && mapSearchPeriod.value !== browseSearchPeriod) {
    mapSearchPeriod.value = browseSearchPeriod;
  }
}

function renderBrowseInstructions(message = "Browse the curated map catalog without choosing a chapter first.") {
  const { mapSearchResults, mapSearchResultsList, mapSearchResultsCount } = getPanelElements();
  browseSearchResults = [];
  if (mapSearchResultsCount) {
    mapSearchResultsCount.textContent = "0";
  }
  if (mapSearchResultsList) {
    mapSearchResultsList.innerHTML = `
      <p class="empty">${message}</p>
      <ul class="map-search-hints">
        <li>Search a topic, place, or route.</li>
        <li>Use the Type dropdown to narrow the catalog before you search.</li>
        <li>Select a result to center the map and open its details.</li>
      </ul>
    `;
  }
  if (mapSearchResults) {
    mapSearchResults.hidden = false;
  }
}

function renderBrowseSearchResults(results, query = "") {
  const { mapSearchResults, mapSearchResultsList, mapSearchResultsCount } = getPanelElements();
  browseSearchResults = Array.isArray(results) ? results.slice() : [];
  browseSearchQuery = query;
  if (!mapSearchResults || !mapSearchResultsList || !mapSearchResultsCount) {
    return;
  }
  mapSearchResults.hidden = mapMode !== "browse";
  mapSearchResultsCount.textContent = String(browseSearchResults.length);
  if (browseSearchResults.length === 0) {
    const searchLabel = query ? ` for “${escapeHtml(query)}”` : "";
    mapSearchResultsList.innerHTML = `
      <p class="empty">No browse results${searchLabel}.</p>
    `;
    return;
  }
  mapSearchResultsList.innerHTML = browseSearchResults
    .map((result, index) => {
      const score = Number(result.search_score || 0);
      const earthUrl = result.kind === "place" ? buildGoogleEarthUrl(result.item) : "";
      return `
        <article class="map-search-result" data-map-search-result data-search-index="${index}">
          <button type="button" class="map-search-result-button" data-map-search-result-button data-search-index="${index}">
            <div class="map-search-result-topline">
              <strong>${escapeHtml(String(result.title || result.id || "Untitled"))}</strong>
              <span>${escapeHtml(String(result.kind_label || result.kind || "Result"))}</span>
            </div>
            <div class="map-search-result-subtitle">${escapeHtml(String(result.subtitle || result.period || ""))}</div>
            <p class="map-search-result-summary">${escapeHtml(String(result.summary || ""))}</p>
            <div class="map-search-result-meta">
              <span>${escapeHtml(String(result.kind_label || result.kind || ""))}</span>
              <span>Score ${escapeHtml(String(score))}</span>
            </div>
          </button>
          ${earthUrl ? `<a class="secondary-link map-search-earth-link" href="${escapeHtml(earthUrl)}" target="_blank" rel="noopener noreferrer">Open ${escapeHtml(String(result.title || "location"))} in Google Earth <span aria-hidden="true">↗</span></a>` : ""}
        </article>
      `;
    })
    .join("");
}

function uniqueItemsById(items = []) {
  const seen = new Set();
  const uniqueItems = [];
  for (const item of items) {
    const id = String(item?.id || "");
    if (!id || seen.has(id)) {
      continue;
    }
    seen.add(id);
    uniqueItems.push(item);
  }
  return uniqueItems;
}

function supportedMapResults(results = []) {
  return (Array.isArray(results) ? results : []).filter(
    (result) => result?.item && (result.kind === "place" || result.kind === "route")
  );
}

function browsePayloadFromSearchResults(results = []) {
  const values = supportedMapResults(results);
  return {
    markers: uniqueItemsById(values.filter((result) => result.kind === "place").map((result) => result.item)),
    routes: uniqueItemsById(values.filter((result) => result.kind === "route").map((result) => result.item)),
  };
}

function refreshBrowseMapResults(results = []) {
  const payload = browsePayloadFromSearchResults(results);
  loadedMarkers = payload.markers;
  loadedRoutes = payload.routes;
  const routeVisibility = true;
  ensureMapController(
    loadedMarkers,
    loadedRoutes,
    routeVisibility
  );
}

function clearCurrentMapSelection() {
  selectedMarker = null;
  selectedRoute = null;
  syncDetailsState(false);
}

function syncDetailsState(hasSelection) {
  const { panel, detailsColumn } = getPanelElements();
  if (panel) {
    panel.classList.toggle("has-map-selection", Boolean(hasSelection));
  }
  if (detailsColumn) {
    detailsColumn.dataset.open = hasSelection ? "true" : "false";
    detailsColumn.classList.toggle("is-mobile-open", Boolean(hasSelection));
  }
}

function setBrowseSearchControls({ query = "", kind = "all", period = "all" } = {}) {
  const { mapSearchQuery, mapSearchKind, mapSearchPeriod } = getPanelElements();
  if (mapSearchQuery) {
    mapSearchQuery.value = query;
  }
  if (mapSearchKind) {
    mapSearchKind.value = kind;
  }
  if (mapSearchPeriod) {
    mapSearchPeriod.value = period;
  }
  browseSearchQuery = query;
  browseSearchKind = kind;
  browseSearchPeriod = period;
  syncMapSearchState();
}

function setSelectedSearchResult(result) {
  if (!result || !result.item) {
    return;
  }
  // The inline Maps tab shares the narrow study column with the reader. Once a
  // catalog result is chosen, use the purpose-built expanded workspace so the
  // navigator at the left, the map, and its details can be viewed together.
  if (
    !mapModalOpen &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(min-width: 901px)").matches
  ) {
    openMapModal();
  }
  clearStatus();
  setPinHint("");
  clearCurrentMapSelection();

  if (result.kind === "place") {
    selectedMarker = result.item;
    renderSelectedMarker(selectedMarker, null);
    focusMapSelection(result);
    return;
  }
  if (result.kind === "route") {
    selectedRoute = result.item;
    renderSelectedRoute(selectedRoute, null);
    focusMapSelection(result);
    return;
  }
}

async function runBrowseSearch() {
  const { query, kind, period } = getMapSearchState();
  browseSearchKind = kind;
  browseSearchPeriod = normalizeHistoricalPeriod(period);
  setBrowseSearchControls({ query, kind, period: browseSearchPeriod });

  if (!query) {
    clearCurrentMapSelection();
    renderBrowseInstructions();
    refreshBrowseMapResults([]);
    clearStatus();
    return;
  }

  setStatus(`Searching the map catalog for "${query}"...`, "loading");
  clearCurrentMapSelection();
  try {
    const result = await searchMapCatalog(query, {
      kind,
      period: browseSearchPeriod,
      limit: 30,
    });
    const results = supportedMapResults(result.results);
    renderBrowseSearchResults(results, query);
    refreshBrowseMapResults(results);
    if ((result.results || []).length === 0) {
      setStatus(`No curated map results matched "${query}".`, "empty");
    } else {
      clearStatus();
    }
  } catch (error) {
    setStatus(error.message || "Could not search the map catalog.", "error");
    renderBrowseInstructions("The map catalog search is temporarily unavailable.");
  }
}

function clearBrowseSearch() {
  const { mapSearchQuery } = getPanelElements();
  if (mapSearchQuery) {
    mapSearchQuery.value = "";
  }
  browseSearchQuery = "";
  browseSearchResults = [];
  clearCurrentMapSelection();
  renderBrowseInstructions();
  refreshBrowseMapResults([]);
  clearStatus();
}

function openMapModal() {
  const { modal } = getPanelElements();
  if (!modal || mapModalOpen) {
    return;
  }
  lastModalTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  moveWorkspaceToHost("modal");
  if (typeof modal.showModal === "function") {
    modal.showModal();
  } else {
    modal.setAttribute("open", "");
  }
  document.body.classList.add("map-modal-open");
  mapModalOpen = true;
  syncMapViewport();
}

function closeMapModal() {
  const { modal } = getPanelElements();
  if (!modal || !mapModalOpen) {
    return;
  }
  if (typeof modal.close === "function" && modal.open) {
    modal.close();
  } else {
    modal.removeAttribute("open");
    finalizeMapModalClose();
  }
}

function finalizeMapModalClose() {
  if (!mapModalOpen) {
    return;
  }
  moveWorkspaceToHost("inline");
  document.body.classList.remove("map-modal-open");
  mapModalOpen = false;
  if (lastModalTrigger && typeof lastModalTrigger.focus === "function") {
    lastModalTrigger.focus({ preventScroll: true });
  }
  lastModalTrigger = null;
}

function ensureMapController(markers, routes, routeVisibility) {
  const { stage } = getPanelElements();
  if (!stage) {
    throw new Error("Map stage is missing.");
  }
  if (mapController) {
    mapController.destroy();
    mapController = null;
  }
  mapController = createBibleMap(stage, markers, {
    routes,
    journey: getSelectedJourney(),
    journeyVisibility,
    selectedJourneyStopId,
    selectedJourneySegmentId,
    routeVisibility,
    onTileError(error) {
      setStatus(error.message, "error");
    },
    onMarkerClick(marker) {
      selectedMarker = marker;
      selectedRoute = null;
      renderSelectedMarker(marker, lastPassageContext);
    },
    onRouteClick(route) {
      selectedRoute = route;
      selectedMarker = null;
      renderSelectedRoute(route, lastPassageContext);
    },
    onJourneyStopClick(journey, stop) {
      selectedJourneyId = journey.id;
      selectedJourneyStopId = stop.id;
      selectedJourneySegmentId = "";
      if (mapController) {
        mapController.setSelectedJourneyStop(stop.id);
      }
      renderJourneySidebar();
      renderSelectedJourneyStop(journey, stop);
    },
    onJourneySegmentClick(journey, segment) {
      selectedJourneyId = journey.id;
      selectedJourneyStopId = "";
      selectedJourneySegmentId = segment.id;
      if (mapController) {
        mapController.setSelectedJourneySegment(segment.id);
      }
      renderJourneySidebar();
      renderSelectedJourneySegment(journey, segment);
    },
  });
  return mapController;
}

async function openMapPanel(context = {}) {
  const [catalog] = await Promise.all([
    loadMapCatalog({ period: "all" }),
    loadSupplementalMapData(),
  ]);
  if (catalog?.timeline?.period_options) {
    applyTimelineOptions(catalog.timeline.period_options);
  }
  renderSupplementalControls();
  const browseMode = context.mode === "browse" || (!context.book && !context.chapter);
  setMapMode(browseMode ? "browse" : "passage");
  if (browseMode) {
    clearCurrentMapSelection();
    lastPassageContext = null;
    browseSearchPeriod = normalizeHistoricalPeriod(context.period || historicalPeriod || "all");
    setBrowseSearchControls({
      query: browseSearchQuery,
      kind: browseSearchKind,
      period: browseSearchPeriod,
    });
  } else {
    const nextReference = formatReference(context);
    const previousReference = formatReference(lastPassageContext);
    if (nextReference !== previousReference) {
      clearCurrentMapSelection();
    }
  }
  if (!browseMode) {
    lastPassageContext = context;
  }
  ensurePanelVisible(context);
  setPinHint("");
  setStatus(browseMode ? "Loading map catalog..." : "Loading map data...", "loading");
  renderEmptyDetails(
    browseMode
      ? "Loading the curated map catalog so you can search by topic, location, or route."
      : "Loading place and route details..."
  );

  try {
    const routeVisibility = true;
    const {
      placeResult,
      routeResult,
      offline,
    } = await loadMapData(context);
    loadedRoutes = routeResult.routes || [];
    loadedMarkers = placeResult.markers || [];
    syncStudyMode();
    if (selectedMarker && !loadedMarkers.some((marker) => marker.id === selectedMarker.id)) {
      selectedMarker = null;
    }
    if (selectedRoute && !loadedRoutes.some((route) => route.id === selectedRoute.id)) {
      selectedRoute = null;
    }

    ensureMapController(
      loadedMarkers,
      loadedRoutes,
      routeVisibility
    );
    syncHistoricalPeriod();

    if (browseMode) {
      clearStatus();
      if (browseSearchResults.length > 0) {
        renderBrowseSearchResults(browseSearchResults, browseSearchQuery);
        refreshBrowseMapResults(browseSearchResults);
      } else {
        renderBrowseInstructions("Browse the catalog, or search by topic, location, or route.");
        refreshBrowseMapResults([]);
      }
      return;
    }

    if (selectedMarker && (placeResult.markers || []).some((marker) => marker.id === selectedMarker.id)) {
      renderSelectedMarker(selectedMarker, context);
      clearStatus();
    } else if (selectedRoute && loadedRoutes.some((route) => route.id === selectedRoute.id)) {
      renderSelectedRoute(selectedRoute, context);
      clearStatus();
    } else {
      clearStatus();
      if (placeResult.empty_state) {
        const noCuratedMatches =
          loadedRoutes.length === 0;
        renderEmptyDetails(
          "No curated point-place match was found for this passage. You can still study any available route below."
        );
        if (noCuratedMatches) {
          setPinHint(
            "The local map dataset does not contain a curated place pin for this passage, so the map is falling back to a text-only geography explanation.",
            { summary: "Why there is no local map data" }
          );
          setStatus(
            "No curated local map data matched this passage. Asking BHF for a text-based geography fallback inside this Maps tab.",
            "empty"
          );
          if (window.BHFWorkspace && typeof window.BHFWorkspace.requestMapAIFallback === "function") {
            window.BHFWorkspace.requestMapAIFallback(
              {
                ...context,
                passage_reference: formatReference(context),
              },
              {
                localSummary:
                  "No curated local map places or routes matched this passage.",
              }
            );
          }
        } else {
          setPinHint(
            "This passage did not resolve to a local point pin, but it does have an available route to study."
          );
          setStatus(
            "No local place pin matched this passage. Showing the available route instead.",
            "empty"
          );
        }
      } else {
        setPinHint("");
        renderEmptyDetails("Select a place pin or route to inspect its details here.");
      }
    }

    if (routeVisibility && loadedRoutes.length === 0) {
      setStatus("Route view is on, but no curated routes are stored for this passage.", "empty");
    }
    if (offline) {
      setStatus(
        "Loaded cached local map data. The structured map responses will refresh automatically when the API is available.",
        "warning"
      );
    }
  } catch (error) {
    setPinHint("");
    setStatus(error.message || "Could not load the map.", "error");
    renderEmptyDetails("Could not load place and route details.");
  }
}

function closeMapPanel() {
  const { panel } = getPanelElements();
  const emptyState = document.querySelector("[data-map-pane-empty]");
  if (panel) {
    panel.hidden = true;
  }
  if (emptyState) {
    emptyState.hidden = false;
  }
  setPinHint("");
  document.dispatchEvent(new CustomEvent("bhf:map-panel-closed"));
}

function applySelectedJourneyToMap({ fit = true } = {}) {
  const journey = getSelectedJourney();
  if (journey && !selectedJourneyStopId && !selectedJourneySegmentId) {
    const firstStop = getOrderedJourneyStops(journey)[0];
    selectedJourneyStopId = firstStop?.id || "";
  }
  if (mapController) {
    mapController.setJourney(journey);
    mapController.setJourneyVisibility(Boolean(journey && journeyVisibility));
    if (selectedJourneyStopId) {
      mapController.setSelectedJourneyStop(selectedJourneyStopId);
    } else if (selectedJourneySegmentId) {
      mapController.setSelectedJourneySegment(selectedJourneySegmentId);
    }
    if (fit && journey) {
      mapController.fitToContent();
    }
  }
  renderJourneySidebar();
}

function selectJourney(journeyId, { fit = true } = {}) {
  const journey = loadedJourneys.find((item) => item.id === journeyId) || null;
  selectedJourneyId = journey?.id || "";
  selectedJourneySegmentId = "";
  const firstStop = getOrderedJourneyStops(journey)[0];
  selectedJourneyStopId = firstStop?.id || "";
  applySelectedJourneyToMap({ fit });
  if (journey && selectedJourneyStopId) {
    const stop = getSelectedJourneyStop(journey);
    renderSelectedJourneyStop(journey, stop);
    focusMapSelection({
      kind: "journey_stop",
      item: { ...stop, id: stop.id },
    });
  }
}

function selectJourneyStop(stopId) {
  const journey = getSelectedJourney();
  const stop = (journey?.stops || []).find((item) => item.id === stopId);
  if (!journey || !stop) {
    return;
  }
  selectedJourneyStopId = stop.id;
  selectedJourneySegmentId = "";
  if (mapController) {
    mapController.setSelectedJourneyStop(stop.id);
  }
  renderJourneySidebar();
  renderSelectedJourneyStop(journey, stop);
  focusMapSelection({ kind: "journey_stop", item: stop });
}

function selectJourneySegment(segmentId) {
  const journey = getSelectedJourney();
  const segment = (journey?.segments || []).find((item) => item.id === segmentId);
  if (!journey || !segment) {
    return;
  }
  selectedJourneyStopId = "";
  selectedJourneySegmentId = segment.id;
  if (mapController) {
    mapController.setSelectedJourneySegment(segment.id);
  }
  renderJourneySidebar();
  renderSelectedJourneySegment(journey, segment);
  focusMapSelection({ kind: "journey_segment", item: segment });
}

async function openPassageReference(reference) {
  const passageReference = String(reference || "").trim();
  if (!passageReference) {
    return false;
  }
  if (window.BHFReader && typeof window.BHFReader.openPassageReference === "function") {
    await window.BHFReader.openPassageReference(passageReference);
    return true;
  }
  return false;
}

async function setHistoricalPeriod(period) {
  historicalPeriod = normalizeHistoricalPeriod(period);
  const { historicalPeriod: historicalPeriodSelect } = getPanelElements();
  if (historicalPeriodSelect) {
    historicalPeriodSelect.value = historicalPeriod;
  }
  if (mapMode === "browse") {
    browseSearchPeriod = historicalPeriod;
    syncMapSearchState();
    setStatus("Loading map catalog...", "loading");
  } else if (!lastPassageContext) {
    return;
  }

  try {
    if (mapMode === "browse") {
      setStatus("Loading map catalog...", "loading");
    } else {
      setStatus("Loading map data...", "loading");
    }
    const {
      placeResult,
      routeResult,
    } = await loadMapData(lastPassageContext);
    loadedMarkers = placeResult.markers || [];
    loadedRoutes = routeResult.routes || [];
    if (selectedMarker && !loadedMarkers.some((marker) => marker.id === selectedMarker.id)) {
      selectedMarker = null;
    }
    if (selectedRoute && !loadedRoutes.some((route) => route.id === selectedRoute.id)) {
      selectedRoute = null;
    }
    const routeVisibility = true;
    ensureMapController(
      loadedMarkers,
      loadedRoutes,
      routeVisibility
    );
    if (mapMode === "browse") {
      clearStatus();
      if (browseSearchResults.length > 0) {
        renderBrowseSearchResults(browseSearchResults, browseSearchQuery);
        refreshBrowseMapResults(browseSearchResults);
      } else {
        renderBrowseInstructions("Browse the catalog, or search by topic, location, or route.");
        refreshBrowseMapResults([]);
      }
    } else if (selectedMarker) {
      renderSelectedMarker(selectedMarker, lastPassageContext);
    } else if (selectedRoute) {
      renderSelectedRoute(selectedRoute, lastPassageContext);
    } else {
      renderEmptyDetails("Choose a place, route, or journey stop to inspect its details here.");
    }
    clearStatus();
  } catch (error) {
    setStatus(error.message || "Could not load map data.", "error");
    renderEmptyDetails("Could not load map data.");
  }
}

function renderSelectedMarker(marker, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = renderSelectedMarkerHtml(marker, passageContext, {
    historicalOverview: "",
  });
  syncDetailsState(true);
}

function renderSelectedRoute(route, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = renderSelectedRouteHtml(route, passageContext, {
    historicalOverview: "",
  });
  syncDetailsState(true);
}

function renderPassageChips(passages = []) {
  const values = Array.isArray(passages) ? passages.filter(Boolean) : [];
  if (!values.length) {
    return `<p>Not provided.</p>`;
  }
  return `
    <div class="map-journey-passage-row">
      ${values.map((passage) =>
        `<button type="button" class="map-passage-chip" data-map-open-passage="${escapeHtml(passage)}">${escapeHtml(passage)}</button>`
      ).join("")}
    </div>
  `;
}

function renderSelectedJourneyStop(journey, stop) {
  const { details } = getPanelElements();
  if (!details || !journey || !stop) {
    return;
  }
  const earthUrl = buildGoogleEarthUrl(stop);
  const externalOnline = typeof navigator === "undefined" || navigator.onLine !== false;
  details.innerHTML = `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(stop.name || "Unnamed stop")}</h3>
          <div class="map-details-subtitle">${escapeHtml(journey.title || "Journey")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(normalizeConfidenceClass(stop.confidence || journey.confidence))}">
          ${escapeHtml(stop.confidence || journey.confidence || "unknown")}
        </span>
      </div>
      <section class="map-detail-section">
        <h4>Location</h4>
        <p>${escapeHtml([stop.region, stop.modernLocation].filter(Boolean).join(" · ") || "Not supplied.")}</p>
      </section>
      ${earthUrl ? `
        <section class="map-detail-section map-external-section">
          <h4>External online feature</h4>
          ${externalOnline
            ? `<a class="secondary-link map-earth-link" href="${escapeHtml(earthUrl)}" target="_blank" rel="noopener noreferrer">Open in Google Earth <span aria-hidden="true">↗</span></a>`
            : `<span class="map-external-disabled" aria-disabled="true">Google Earth is unavailable offline</span>`}
          <p class="map-layer-note">Opens this journey stop in a new browser context.</p>
        </section>
      ` : ""}
      <section class="map-detail-section">
        <h4>Related passages</h4>
        ${renderPassageChips(stop.passages)}
      </section>
      <section class="map-detail-section">
        <h4>Why this stop matters</h4>
        <p>${escapeHtml(stop.description || "No stop description is available.")}</p>
      </section>
      <section class="map-detail-section map-caution">
        <h4>BHF caution</h4>
        <p>${escapeHtml(stop.caution || stop.notes || journey.caution || "This journey route is simplified for study and should not be treated as a precise reconstruction.")}</p>
      </section>
      <section class="map-detail-section map-action-section">
        <a class="secondary-link map-kml-link" href="/api/maps/journeys/${encodeURIComponent(journey.id)}.kml" download>Download journey KML</a>
      </section>
    </div>
  `;
  syncDetailsState(true);
}

function renderSelectedJourneySegment(journey, segment) {
  const { details } = getPanelElements();
  if (!details || !journey || !segment) {
    return;
  }
  const from = journey.stops.find((stop) => stop.id === segment.from);
  const to = journey.stops.find((stop) => stop.id === segment.to);
  details.innerHTML = `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(segment.label || "Journey segment")}</h3>
          <div class="map-details-subtitle">${escapeHtml(`${from?.name || segment.from} → ${to?.name || segment.to}`)}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(normalizeConfidenceClass(segment.confidence || journey.confidence))}">
          ${escapeHtml(segment.confidence || journey.confidence || "unknown")}
        </span>
      </div>
      <section class="map-detail-section">
        <h4>Journey</h4>
        <p>${escapeHtml(journey.title || "Journey")}</p>
      </section>
      <section class="map-detail-section">
        <h4>Related passages</h4>
        ${renderPassageChips(segment.passages)}
      </section>
      <section class="map-detail-section">
        <h4>Movement</h4>
        <p>${escapeHtml(segment.description || "No segment description is available.")}</p>
      </section>
      <section class="map-detail-section map-caution">
        <h4>BHF caution</h4>
        <p>${escapeHtml(segment.caution || journey.caution || "This line is a study route, not a precise ancient road trace.")}</p>
      </section>
    </div>
  `;
  syncDetailsState(true);
}

function focusMapSelection(result) {
  if (!mapController || !result) {
    return;
  }
  if (typeof mapController.focusSelection === "function") {
    mapController.focusSelection(result.kind, result.item);
    return;
  }
  if (mapController.map && Number.isFinite(result.item?.latitude) && Number.isFinite(result.item?.longitude)) {
    mapController.map.setView([result.item.latitude, result.item.longitude], 9);
  }
}

function activateAskWorkspace() {
  const askTab = document.querySelector('[data-workspace-tab="ask"]');
  if (askTab && askTab.getAttribute("aria-selected") !== "true") {
    askTab.click();
  }
}

function setMapStudyQuestion(question) {
  const input = document.querySelector(".ask-form [name='question']");
  if (input) {
    input.value = question;
  }
}

function setStudyFormValue(name, value) {
  const input = document.querySelector(`.ask-form [name="${name}"]`);
  if (input) {
    input.value = value;
  }
}

function setStudyMapContext(context) {
  const input = document.querySelector('.ask-form [name="map_context"]');
  if (input) {
    input.value = context ? JSON.stringify(context) : "";
  }
}

function setReaderPassageContext(reference) {
  if (!reference) {
    return "";
  }
  const book = String(reference.book || "").trim();
  const chapter = String(reference.chapter || "").trim();
  const verseStart = reference.verseStart || reference.verse_start || "";
  const verseEnd = reference.verseEnd || reference.verse_end || verseStart || "";
  const readable = verseStart
    ? `${book} ${chapter}:${verseStart}${String(verseEnd) !== String(verseStart) ? `-${verseEnd}` : ""}`
    : `${book} ${chapter}`;
  setStudyFormValue("reader_book", book);
  setStudyFormValue("reader_chapter", chapter);
  setStudyFormValue("reader_start_verse", verseStart ? String(verseStart) : "");
  setStudyFormValue("reader_end_verse", verseStart ? String(verseEnd) : "");
  setStudyFormValue("reader_selected_text", "");
  return readable;
}

function submitRelatedPassageShortcut(reference, questionPrefix = "What should I know about") {
  const readable = setReaderPassageContext(reference);
  if (!readable) {
    return;
  }
  const form = document.querySelector(".ask-form");
  if (!form) {
    return;
  }
  setStudyFormValue("ask_mode", "cross_references");
  setStudyFormValue("study_action", "related_passages");
  setMapStudyQuestion(`${questionPrefix} ${readable}?`);
  setStudyMapContext({
    shortcut_reference: readable,
    selected_passage_reference: readable,
  });
  submitStudyForm(form);
}

function submitStudyForm(form) {
  activateAskWorkspace();
  if (typeof form.requestSubmit === "function") {
    form.requestSubmit();
  } else {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  }
}

function renderEmptyDetails(message) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = `
    ${renderMapOrientationCard({
      callout: message,
    })}
  `;
  syncDetailsState(false);
}

function syncHistoricalPeriod() {
  const { historicalPeriod: historicalPeriodSelect } = getPanelElements();
  if (historicalPeriodSelect) {
    historicalPeriodSelect.value = normalizeHistoricalPeriod(historicalPeriod, timelinePeriodOptions);
  }
}

function wirePanelButtons() {
  const modalCloseButton = document.querySelector("[data-map-modal-close]");
  const mapSearchQuery = document.querySelector("[data-map-search-query]");
  const mapSearchKind = document.querySelector("[data-map-search-kind]");
  const mapSearchPeriod = document.querySelector("[data-map-search-period]");
  const mapSearchSubmit = document.querySelector("[data-map-search-submit]");
  const mapSearchClear = document.querySelector("[data-map-search-clear]");
  const mapSearchResultsList = document.querySelector("#map-search-results-list");
  const historicalPeriodSelect = document.querySelector("[data-historical-period]");
  const {
    modal,
    journeySelector,
    journeyToggle,
  } = getPanelElements();
  const details = document.querySelector("#map-details");
  const {
    studyMode: studyModeSelect,
    navigatorOpen,
    detailsOpen,
  } = getPanelElements();

  if (modalCloseButton) {
    modalCloseButton.addEventListener("click", closeMapModal);
  }
  if (mapSearchQuery) {
    mapSearchQuery.addEventListener("keydown", async (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        await runBrowseSearch();
      }
    });
  }
  if (mapSearchKind) {
    mapSearchKind.addEventListener("change", async () => {
      await runBrowseSearch();
    });
  }
  if (mapSearchPeriod) {
    mapSearchPeriod.addEventListener("change", async (event) => {
      await setHistoricalPeriod(event.target.value);
      if (mapMode === "browse") {
        await runBrowseSearch();
      }
    });
  }
  if (mapSearchSubmit) {
    mapSearchSubmit.addEventListener("click", async () => {
      await runBrowseSearch();
    });
  }
  if (mapSearchClear) {
    mapSearchClear.addEventListener("click", () => {
      clearBrowseSearch();
    });
  }
  if (modal) {
    modal.addEventListener("close", finalizeMapModalClose);
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeMapModal();
      }
    });
  }
  if (historicalPeriodSelect) {
    historicalPeriodSelect.addEventListener("change", async (event) => {
      await setHistoricalPeriod(event.target.value);
    });
  }
  if (studyModeSelect) {
    studyModeSelect.addEventListener("change", (event) => {
      setStudyMode(event.target.value);
    });
  }
  if (navigatorOpen) {
    navigatorOpen.addEventListener("click", () => {
      getPanelElements().navigator?.classList.toggle("is-mobile-open");
    });
  }
  if (detailsOpen) {
    detailsOpen.addEventListener("click", () => {
      getPanelElements().detailsColumn?.classList.toggle("is-mobile-open");
    });
  }
  if (journeySelector) {
    journeySelector.addEventListener("change", (event) => {
      selectJourney(event.target.value);
    });
  }
  if (journeyToggle) {
    journeyToggle.addEventListener("change", (event) => {
      journeyVisibility = Boolean(event.target.checked);
      if (mapController) {
        mapController.setJourneyVisibility(journeyVisibility);
      }
      renderJourneySidebar();
    });
  }
  if (details) {
    details.addEventListener("click", async (event) => {
      const passageShortcut = event.target.closest("[data-passage-shortcut]");
      const openPassageButton = event.target.closest("[data-map-open-passage]");
      if (openPassageButton) {
        await openPassageReference(openPassageButton.getAttribute("data-map-open-passage"));
        return;
      }
      if (passageShortcut) {
        const reference = {
          book: passageShortcut.getAttribute("data-book") || "",
          chapter: passageShortcut.getAttribute("data-chapter") || "",
          verse_start: passageShortcut.getAttribute("data-verse-start") || "",
          verse_end: passageShortcut.getAttribute("data-verse-end") || "",
          reference: passageShortcut.getAttribute("data-reference") || "",
        };
        await submitRelatedPassageShortcut(reference);
        return;
      }
    });
  }
  if (mapSearchResultsList) {
    mapSearchResultsList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-map-search-result-button]");
      if (!button) {
        return;
      }
      const index = Number(button.getAttribute("data-search-index"));
      if (!Number.isInteger(index) || index < 0 || index >= browseSearchResults.length) {
        return;
      }
      setSelectedSearchResult(browseSearchResults[index]);
    });
  }
}

function initializeMapPanel() {
  wirePanelButtons();
  renderEmptyDetails("Select a place pin, route, or journey stop to inspect its details here.");
  syncHistoricalPeriod();
  syncStudyMode();
  const pendingContext = window.BHFPendingMapPanelContext;
  if (pendingContext) {
    window.BHFPendingMapPanelContext = null;
    openMapPanel(pendingContext);
  }
}

if (typeof window !== "undefined") {
  window.BHFMaps = {
    openMapPanel,
    closeMapPanel,
    openMapModal,
    closeMapModal,
    initializeMapPanel,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeMapPanel, { once: true });
  } else {
    initializeMapPanel();
  }
}
