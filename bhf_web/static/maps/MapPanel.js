import { createBibleMap } from "./BibleMap.js";
import {
  getOrderedJourneyStops,
  journeyMatchesFilters,
  loadJourneyCatalog,
} from "./JourneyMapData.js";
import {
  loadMapCatalog,
  loadHistoricalLayers,
  invalidateMapCache,
  loadPlacesForPassage,
  loadPoliticalContextForPassage,
  loadRoutesForPassage,
  loadSavedMapStudy,
  loadSavedMapStudies,
  searchMapCatalog,
} from "./mapService.js?v=20260630";
import {
  renderHistoricalLayerOverview as renderHistoricalLayerOverviewHtml,
  renderMapOrientationCard,
  renderSavedMapStudies,
  renderSelectedHistoricalLayer as renderSelectedHistoricalLayerHtml,
  renderSelectedMarker as renderSelectedMarkerHtml,
  renderSelectedPoliticalContext as renderSelectedPoliticalContextHtml,
  renderSelectedRoute as renderSelectedRouteHtml,
  renderPoliticalContextLayerOverview as renderPoliticalContextLayerOverviewHtml,
} from "./MapPanelContent.js";
import {
  buildCautionNote,
  buildHistoricalLayerCautionNote,
  buildHistoricalLayerExplanation,
  buildMapStudySummary,
  buildPlaceExplanation,
  buildPoliticalContextCautionNote,
  buildPoliticalContextExplanation,
  buildRouteCautionNote,
  buildRouteExplanation,
  escapeHtml,
  buildSourceText,
} from "./MapPanelText.js";
import {
  buildCurrentMapStudyPayload,
  getCurrentMapSelection,
  normalizeHistoricalPeriod,
  syncRouteToggle as syncRouteToggleHtml,
} from "./MapPanelStateHelpers.js";

// Source links still point to `/sources/` in the rendered map panel markup.
const BHF_HTTP = window.BHFApi || {};

let mapController = null;
let selectedMarker = null;
let selectedRoute = null;
let selectedHistoricalLayer = null;
let selectedPoliticalContext = null;
let mapMode = "passage";
let lastPassageContext = null;
let loadedMarkers = [];
let loadedRoutes = [];
let loadedHistoricalLayers = [];
let loadedPoliticalContextLayers = [];
let loadedSavedMapStudies = [];
let loadedJourneys = [];
let journeyFacets = { categories: [], eras: [], testaments: [], tags: [] };
let selectedJourneyId = "";
let selectedJourneyStopId = "";
let selectedJourneySegmentId = "";
let studyMode = "passage";
let journeySearch = "";
let journeyTestament = "";
let journeyCategory = "";
let journeyEra = "";
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
const visibleHistoricalLayerIds = new Set();
const visiblePoliticalContextLayerIds = new Set();

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
    savedMapStudiesList: document.querySelector("#saved-map-studies-list"),
    savedMapStudiesCount: document.querySelector("#saved-map-studies-count"),
    routeToggle: document.querySelector("[data-route-toggle]"),
    historicalPeriod: document.querySelector("[data-historical-period]"),
    mapBrowser: document.querySelector("[data-map-browser]"),
    mapModeButtons: document.querySelectorAll("[data-map-mode-switch]"),
    studyMode: document.querySelector("[data-map-study-mode]"),
    contextSummary: document.querySelector("[data-map-context-summary]"),
    layerControls: document.querySelector("#map-layer-controls"),
    layerReset: document.querySelector("[data-map-layer-reset]"),
    navigator: document.querySelector("#map-study-navigator"),
    navigatorOpen: document.querySelector("[data-map-navigator-open]"),
    navigatorClose: document.querySelector("[data-map-navigator-close]"),
    detailsColumn: document.querySelector("#map-details-column"),
    detailsOpen: document.querySelector("[data-map-details-open]"),
    detailsClose: document.querySelector("[data-map-details-close]"),
    mapSearchQuery: document.querySelector("[data-map-search-query]"),
    mapSearchKind: document.querySelector("[data-map-search-kind]"),
    mapSearchPeriod: document.querySelector("[data-map-search-period]"),
    mapSearchSubmit: document.querySelector("[data-map-search-submit]"),
    mapSearchClear: document.querySelector("[data-map-search-clear]"),
    mapSearchResults: document.querySelector("#map-search-results"),
    mapSearchResultsCount: document.querySelector("#map-search-results-count"),
    mapSearchResultsList: document.querySelector("#map-search-results-list"),
    journeyPanel: document.querySelector("[data-map-journeys]"),
    journeySearch: document.querySelector("[data-map-journey-search]"),
    journeySelector: document.querySelector("[data-map-journey-selector]"),
    journeyTestament: document.querySelector("[data-map-journey-filter-testament]"),
    journeyCategory: document.querySelector("[data-map-journey-filter-category]"),
    journeyEra: document.querySelector("[data-map-journey-filter-era]"),
    journeyToggle: document.querySelector("[data-map-journey-toggle]"),
    journeyCount: document.querySelector("[data-map-journey-count]"),
    journeyStopList: document.querySelector("[data-map-journey-stop-list]"),
    journeySegmentList: document.querySelector("[data-map-journey-segment-list]"),
    journeyDetail: document.querySelector("[data-map-journey-detail]"),
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
  return loadedJourneys.filter((journey) =>
    journeyMatchesFilters(journey, {
      search: journeySearch,
      testament: journeyTestament,
      category: journeyCategory,
      era: journeyEra,
    })
  );
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

function renderSelectOptions(values, currentValue, placeholder = "All") {
  const options = [`<option value="">${escapeHtml(placeholder)}</option>`];
  for (const value of values || []) {
    options.push(`<option value="${escapeHtml(value)}" ${value === currentValue ? "selected" : ""}>${escapeHtml(value)}</option>`);
  }
  return options.join("");
}

function syncJourneyControls() {
  const {
    journeySearch: searchInput,
    journeySelector,
    journeyTestament: testamentSelect,
    journeyCategory: categorySelect,
    journeyEra: eraSelect,
    journeyToggle,
    journeyCount,
  } = getPanelElements();
  const visibleJourneys = getVisibleJourneys();

  if (searchInput && searchInput.value !== journeySearch) {
    searchInput.value = journeySearch;
  }
  if (journeyToggle) {
    journeyToggle.checked = journeyVisibility;
  }
  if (journeyCount) {
    journeyCount.textContent = `${visibleJourneys.length} of ${loadedJourneys.length}`;
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
  if (testamentSelect) {
    testamentSelect.innerHTML = renderSelectOptions(journeyFacets.testaments, journeyTestament);
    testamentSelect.value = journeyTestament;
  }
  if (categorySelect) {
    categorySelect.innerHTML = renderSelectOptions(journeyFacets.categories, journeyCategory);
    categorySelect.value = journeyCategory;
  }
  if (eraSelect) {
    eraSelect.innerHTML = renderSelectOptions(journeyFacets.eras, journeyEra);
    eraSelect.value = journeyEra;
  }
}

function renderJourneySidebar() {
  const { journeyStopList, journeySegmentList, journeyDetail } = getPanelElements();
  const journey = getSelectedJourney();
  const orderedStops = getOrderedJourneyStops(journey);

  if (journeyStopList) {
    journeyStopList.innerHTML = orderedStops.length
      ? orderedStops.map((stop) => `
          <button type="button" class="map-journey-list-item ${stop.id === selectedJourneyStopId ? "is-selected" : ""}" data-map-journey-stop="${escapeHtml(stop.id)}" aria-pressed="${stop.id === selectedJourneyStopId}">
            <span class="map-journey-list-order">${Number.isFinite(stop.order) ? escapeHtml(String(stop.order)) : "•"}</span>
            <span>
              <strong>${escapeHtml(stop.name)}</strong>
              <span>${escapeHtml([stop.region, stop.modernLocation].filter(Boolean).join(" · ") || "No location detail")}</span>
            </span>
          </button>
        `).join("")
      : `<p class="empty">Choose a journey to see its stops.</p>`;
  }

  if (journeySegmentList) {
    journeySegmentList.innerHTML = journey?.segments?.length
      ? journey.segments.map((segment) => {
          const from = journey.stops.find((stop) => stop.id === segment.from);
          const to = journey.stops.find((stop) => stop.id === segment.to);
          return `
            <button type="button" class="map-journey-list-item ${segment.id === selectedJourneySegmentId ? "is-selected" : ""}" data-map-journey-segment="${escapeHtml(segment.id)}" aria-pressed="${segment.id === selectedJourneySegmentId}">
              <span>
                <strong>${escapeHtml(segment.label || "Segment")}</strong>
                <span>${escapeHtml(`${from?.name || segment.from} → ${to?.name || segment.to}`)}</span>
              </span>
            </button>
          `;
        }).join("")
      : `<p class="empty">Journey segments will appear here.</p>`;
  }

  if (journeyDetail) {
    if (!journey) {
      journeyDetail.innerHTML = `<p class="empty">Search or choose a journey to draw its stops and route on the map.</p>`;
    } else {
      const selectedStop = getSelectedJourneyStop(journey);
      const selectedSegment = getSelectedJourneySegment(journey);
      const title = selectedStop?.name || selectedSegment?.label || journey.title;
      const subtitle = selectedStop
        ? [selectedStop.region, selectedStop.modernLocation].filter(Boolean).join(" · ")
        : selectedSegment
          ? "Selected route segment"
          : [journey.testament, journey.category, journey.era].filter(Boolean).join(" · ");
      const description = selectedStop?.description || selectedSegment?.description || journey.description || "";
      journeyDetail.innerHTML = `
        <div class="map-journey-detail-card">
          <div class="map-section-header">
            <h4>${escapeHtml(title)}</h4>
            <span class="map-confidence confidence-${escapeHtml(normalizeConfidenceClass(selectedStop?.confidence || selectedSegment?.confidence || journey.confidence))}">
              ${escapeHtml(selectedStop?.confidence || selectedSegment?.confidence || journey.confidence || "unknown")}
            </span>
          </div>
          <p class="map-details-subtitle">${escapeHtml(subtitle || "Journey overview")}</p>
          <p>${escapeHtml(description || "No description supplied.")}</p>
          <div class="map-journey-passage-row">
            ${(selectedStop?.passages || selectedSegment?.passages || journey.primaryPassages || []).slice(0, 4).map((passage) =>
              `<button type="button" class="map-passage-chip" data-map-open-passage="${escapeHtml(passage)}">${escapeHtml(passage)}</button>`
            ).join("")}
          </div>
        </div>
      `;
    }
  }
  syncJourneyControls();
}

function renderSupplementalControls() {
  renderJourneySidebar();
  renderLayerControls();
  syncStudyMode();
}

function renderLayerControls() {
  const { layerControls } = getPanelElements();
  if (!layerControls) {
    return;
  }
  const historical = loadedHistoricalLayers.map((layer) => `
    <label class="map-layer-toggle ${visibleHistoricalLayerIds.has(layer.id) ? "is-selected" : ""}">
      <input type="checkbox" data-historical-layer-toggle data-layer-id="${escapeHtml(layer.id)}" ${visibleHistoricalLayerIds.has(layer.id) ? "checked" : ""}>
      <span><strong>${escapeHtml(layer.name || "Historical layer")}</strong><small>${escapeHtml(layer.period || "Broad study context")} · ${escapeHtml(layer.confidence || "Uncertain")}</small></span>
    </label>
  `).join("");
  const political = loadedPoliticalContextLayers.map((layer) => `
    <label class="map-layer-toggle ${visiblePoliticalContextLayerIds.has(layer.id) ? "is-selected" : ""}">
      <input type="checkbox" data-political-context-toggle data-layer-id="${escapeHtml(layer.id)}" ${visiblePoliticalContextLayerIds.has(layer.id) ? "checked" : ""}>
      <span><strong>${escapeHtml(layer.name || "Regional context")}</strong><small>${escapeHtml(layer.entity_type || layer.period || "Regional context")}</small></span>
    </label>
  `).join("");
  layerControls.innerHTML = historical || political
    ? `${historical}${political}`
    : `<p class="empty">No regional overlays match this study yet.</p>`;
}

function syncStudyMode() {
  const { studyMode: studyModeSelect, contextSummary, journeyPanel } = getPanelElements();
  if (studyModeSelect) {
    studyModeSelect.value = studyMode;
  }
  if (journeyPanel) {
    journeyPanel.open = studyMode === "journeys" || Boolean(selectedJourneyId);
  }
  if (!contextSummary) {
    return;
  }
  const messages = {
    passage: lastPassageContext
      ? `Showing locations and broader context connected to ${formatReference(lastPassageContext)}.`
      : "Open a passage to focus the map on its chapter context.",
    places: "Search for a place to focus the map on one location and its related passages.",
    journeys: "Choose a curated journey to see numbered stops and an approximate route.",
    events: "Event records are not available in the local map data yet.",
    regions: "Search or select a region to emphasize broad geographic context.",
  };
  contextSummary.textContent = messages[studyMode] || messages.passage;
}

function setStudyMode(nextMode) {
  const allowed = new Set(["passage", "places", "journeys", "events", "regions"]);
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
    layerResult,
    politicalContextResult,
    savedMapStudiesResult,
  ] = await Promise.all([
    loadPlacesForPassage(loadContext),
    loadRoutesForPassage(loadContext),
    loadHistoricalLayers({ period: historicalPeriod }),
    loadPoliticalContextForPassage(loadContext),
    loadSavedMapStudies(context),
  ]);
  const offline = [
    placeResult,
    routeResult,
    layerResult,
    politicalContextResult,
    savedMapStudiesResult,
  ].some((result) => Boolean(result?.offline));
  return {
    placeResult,
    routeResult,
    layerResult,
    politicalContextResult,
    savedMapStudiesResult,
    offline,
  };
}

async function loadBrowseMapData() {
  const savedMapStudiesResult = await loadSavedMapStudies();
  return {
    placeResult: { markers: [] },
    routeResult: { routes: [] },
    layerResult: { layers: [] },
    politicalContextResult: { layers: [] },
    savedMapStudiesResult: savedMapStudiesResult || { saved_map_studies: [] },
    offline: Boolean(savedMapStudiesResult?.offline),
  };
}

async function loadMapData(context = {}) {
  return mapMode === "browse" ? loadBrowseMapData() : loadPassageMapData(context);
}

async function loadSupplementalMapData() {
  const journeyCatalog = await loadJourneyCatalog();
  loadedJourneys = journeyCatalog.journeys || [];
  journeyFacets = journeyCatalog.facets || { categories: [], eras: [], testaments: [], tags: [] };
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
  const { mapBrowser, mapModeButtons, mapSearchResults, journeyPanel } = getPanelElements();
  if (mapBrowser) {
    mapBrowser.hidden = mapMode !== "browse";
  }
  if (mapSearchResults) {
    mapSearchResults.hidden = mapMode !== "browse";
  }
  if (journeyPanel && "open" in journeyPanel) {
    journeyPanel.open = mapMode !== "browse" || Boolean(selectedJourneyId);
  }
  mapModeButtons.forEach((button) => {
    const isActive = button.getAttribute("data-map-mode-switch") === mapMode;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
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
        <li>Search a topic, place, route, historical layer, or political context.</li>
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

function browsePayloadFromSearchResults(results = []) {
  const values = Array.isArray(results) ? results : [];
  return {
    markers: uniqueItemsById(values.filter((result) => result.kind === "place").map((result) => result.item)),
    routes: uniqueItemsById(values.filter((result) => result.kind === "route").map((result) => result.item)),
    historicalLayers: uniqueItemsById(values.filter((result) => result.kind === "historical_layer").map((result) => result.item)),
    politicalContextLayers: uniqueItemsById(values.filter((result) => result.kind === "political_context").map((result) => result.item)),
  };
}

function refreshBrowseMapResults(results = []) {
  const payload = browsePayloadFromSearchResults(results);
  loadedMarkers = payload.markers;
  loadedRoutes = payload.routes;
  loadedHistoricalLayers = payload.historicalLayers;
  loadedPoliticalContextLayers = payload.politicalContextLayers;
  renderLayerControls();
  const routeVisibility = Boolean(getPanelElements().routeToggle?.checked);
  ensureMapController(
    loadedMarkers,
    loadedRoutes,
    loadedHistoricalLayers,
    loadedPoliticalContextLayers,
    routeVisibility
  );
  syncRouteToggle();
}

function clearCurrentMapSelection({ clearVisibleLayers = false } = {}) {
  selectedMarker = null;
  selectedRoute = null;
  selectedHistoricalLayer = null;
  selectedPoliticalContext = null;
  if (clearVisibleLayers) {
    visibleHistoricalLayerIds.clear();
    visiblePoliticalContextLayerIds.clear();
  }
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
  clearStatus();
  setPinHint("");
  clearCurrentMapSelection({ clearVisibleLayers: true });

  if (result.kind === "place") {
    selectedMarker = result.item;
    renderSelectedMarker(selectedMarker, null);
    focusMapSelection(result);
    return;
  }
  if (result.kind === "route") {
    selectedRoute = result.item;
    setRouteVisibility(true);
    renderSelectedRoute(selectedRoute, null);
    focusMapSelection(result);
    return;
  }
  if (result.kind === "historical_layer") {
    selectedHistoricalLayer = result.item;
    setHistoricalLayerVisibility(result.item.id, true);
    renderSelectedHistoricalLayer(selectedHistoricalLayer, null);
    focusMapSelection(result);
    return;
  }
  if (result.kind === "political_context") {
    selectedPoliticalContext = result.item;
    setPoliticalContextLayerVisibility(result.item.id, true);
    renderSelectedPoliticalContext(selectedPoliticalContext, null);
    focusMapSelection(result);
  }
}

async function runBrowseSearch() {
  const { query, kind, period } = getMapSearchState();
  browseSearchKind = kind;
  browseSearchPeriod = normalizeHistoricalPeriod(period);
  setBrowseSearchControls({ query, kind, period: browseSearchPeriod });

  if (!query) {
    clearCurrentMapSelection({ clearVisibleLayers: true });
    renderBrowseInstructions();
    refreshBrowseMapResults([]);
    clearStatus();
    return;
  }

  setStatus(`Searching the map catalog for "${query}"...`, "loading");
  clearCurrentMapSelection({ clearVisibleLayers: true });
  try {
    const result = await searchMapCatalog(query, {
      kind,
      period: browseSearchPeriod,
      limit: 30,
    });
    const results = result.results || [];
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
  clearCurrentMapSelection({ clearVisibleLayers: true });
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

function ensureMapController(
  markers,
  routes,
  historicalLayers,
  politicalContextLayers,
  routeVisibility
) {
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
    historicalLayers,
    historicalLayerIds: Array.from(visibleHistoricalLayerIds),
    politicalContextLayers,
    politicalContextLayerIds: Array.from(visiblePoliticalContextLayerIds),
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
      selectedHistoricalLayer = null;
      renderSelectedMarker(marker, lastPassageContext);
    },
    onRouteClick(route) {
      selectedRoute = route;
      selectedMarker = null;
      selectedHistoricalLayer = null;
      renderSelectedRoute(route, lastPassageContext);
    },
    onHistoricalLayerClick(layer) {
      selectedHistoricalLayer = layer;
      selectedMarker = null;
      selectedRoute = null;
      selectedPoliticalContext = null;
      visibleHistoricalLayerIds.add(layer.id);
      if (mapController) {
        mapController.setHistoricalLayerVisibility(layer.id, true);
      }
      renderSelectedHistoricalLayer(layer, lastPassageContext);
    },
    onPoliticalContextClick(layer) {
      selectedPoliticalContext = layer;
      selectedMarker = null;
      selectedRoute = null;
      selectedHistoricalLayer = null;
      visiblePoliticalContextLayerIds.add(layer.id);
      if (mapController) {
        mapController.setPoliticalContextLayerVisibility(layer.id, true);
      }
      renderSelectedPoliticalContext(layer, lastPassageContext);
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
  const browseMode = context.mode === "browse" || (!context.book && !context.chapter && !context.savedMapStudy);
  setMapMode(browseMode ? "browse" : "passage");
  if (browseMode) {
    clearCurrentMapSelection({ clearVisibleLayers: true });
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
      clearCurrentMapSelection({ clearVisibleLayers: true });
    }
  }
  if (context.savedMapStudy?.map_view_state?.historicalPeriod) {
    historicalPeriod = normalizeHistoricalPeriod(context.savedMapStudy.map_view_state.historicalPeriod);
  }
  if (!browseMode) {
    lastPassageContext = context;
  }
  ensurePanelVisible(context);
  setPinHint("");
  setStatus(browseMode ? "Loading map catalog..." : "Loading map data...", "loading");
  renderEmptyDetails(
    browseMode
      ? "Loading the curated map catalog so you can search by topic, location, route, or regional context."
      : "Loading place, route, historical, and political context details..."
  );

  try {
    const routeToggle = getPanelElements().routeToggle;
    const routeVisibility = Boolean(routeToggle?.checked);
    const {
      placeResult,
      routeResult,
      layerResult,
      politicalContextResult,
      savedMapStudiesResult,
      offline,
    } = await loadMapData(context);
    loadedRoutes = routeResult.routes || [];
    loadedMarkers = placeResult.markers || [];
    loadedHistoricalLayers = layerResult.layers || [];
    loadedPoliticalContextLayers = politicalContextResult.layers || [];
    loadedSavedMapStudies = savedMapStudiesResult.saved_map_studies || [];
    renderLayerControls();
    syncStudyMode();
    if (selectedMarker && !loadedMarkers.some((marker) => marker.id === selectedMarker.id)) {
      selectedMarker = null;
    }
    if (selectedHistoricalLayer && !loadedHistoricalLayers.some((layer) => layer.id === selectedHistoricalLayer.id)) {
      selectedHistoricalLayer = null;
    }
    if (selectedRoute && !loadedRoutes.some((route) => route.id === selectedRoute.id)) {
      selectedRoute = null;
    }
    if (selectedPoliticalContext && !loadedPoliticalContextLayers.some((layer) => layer.id === selectedPoliticalContext.id)) {
      selectedPoliticalContext = null;
    }

    ensureMapController(
      loadedMarkers,
      loadedRoutes,
      loadedHistoricalLayers,
      loadedPoliticalContextLayers,
      routeVisibility
    );
    if (context.savedMapStudy) {
      await applySavedMapStudyState(context.savedMapStudy);
    }
    syncRouteToggle();
    syncHistoricalPeriod();
    await refreshSavedMapStudies();

    if (browseMode) {
      clearStatus();
      if (browseSearchResults.length > 0) {
        renderBrowseSearchResults(browseSearchResults, browseSearchQuery);
        refreshBrowseMapResults(browseSearchResults);
      } else {
        renderBrowseInstructions("Browse the catalog, or search by topic, location, route, or regional context.");
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
    } else if (
      selectedHistoricalLayer &&
      loadedHistoricalLayers.some((layer) => layer.id === selectedHistoricalLayer.id)
    ) {
      renderSelectedHistoricalLayer(selectedHistoricalLayer, context);
      clearStatus();
    } else if (
      selectedPoliticalContext &&
      loadedPoliticalContextLayers.some((layer) => layer.id === selectedPoliticalContext.id)
    ) {
      renderSelectedPoliticalContext(selectedPoliticalContext, context);
      clearStatus();
    } else if (placeResult.empty_state && loadedPoliticalContextLayers.length > 0) {
      selectedPoliticalContext = loadedPoliticalContextLayers[0];
      visiblePoliticalContextLayerIds.add(selectedPoliticalContext.id);
      if (mapController && typeof mapController.setPoliticalContextLayerVisibility === "function") {
        mapController.setPoliticalContextLayerVisibility(selectedPoliticalContext.id, true);
      }
      renderSelectedPoliticalContext(selectedPoliticalContext, context);
      setPinHint(
        `${selectedPoliticalContext.name || "This passage"} does not have a curated point-place pin here. It is mapped as broader political or regional context because the reference fits a territory, empire, or people-group better than one exact site.`,
        { open: true, summary: "Why this is a region" }
      );
      setStatus(
        `No curated point-place marker matched this passage. Showing political context for ${selectedPoliticalContext.name || "the matched region"} instead, because this reference maps more naturally to a broader region or governing power.`,
        "empty"
      );
    } else {
      clearStatus();
      if (placeResult.empty_state) {
        const noCuratedMatches =
          loadedRoutes.length === 0 &&
          loadedHistoricalLayers.length === 0 &&
          loadedPoliticalContextLayers.length === 0;
        renderEmptyDetails(
          "No curated point-place match was found for this passage. You can still study any available route, region, empire, or historical layer below."
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
                  "No curated local map places, routes, historical layers, or political-context overlays matched this passage.",
              }
            );
          }
        } else {
          setPinHint(
            "This passage did not resolve to a local point pin. It may map better to a broader region, empire, or study overlay than to one exact location."
          );
          setStatus(
            "No local place pin matched this passage. Showing the available map framework so you can still study broader context.",
            "empty"
          );
        }
      } else {
        setPinHint("");
        renderEmptyDetails("Select a place pin, route, historical layer, or political context overlay to inspect its details here.");
      }
    }

    if (routeVisibility && loadedRoutes.length === 0) {
      setStatus("Route view is on, but no curated routes are stored for this passage.", "empty");
    }
    if (
      !loadedHistoricalLayers.length &&
      !loadedPoliticalContextLayers.length &&
      !selectedMarker &&
      !selectedRoute &&
      !selectedHistoricalLayer &&
      !selectedPoliticalContext
    ) {
      setStatus("No historical or political overlays matched the selected period.", "empty");
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
    renderEmptyDetails("Could not load place, route, and layer details.");
  }
}

async function applySavedMapStudyState(study) {
  if (!study) {
    return;
  }
  const viewState = study.map_view_state || {};
  historicalPeriod = normalizeHistoricalPeriod(viewState.historicalPeriod || "all");
  selectedMarker = null;
  selectedRoute = null;
  selectedHistoricalLayer = null;
  selectedPoliticalContext = null;

  if (mapController && typeof mapController.setRouteVisibility === "function" && Object.prototype.hasOwnProperty.call(viewState, "routeVisibility")) {
    mapController.setRouteVisibility(Boolean(viewState.routeVisibility));
  }

  const selectedLayerIds = new Set(
    Array.isArray(viewState.historicalLayerIds)
      ? viewState.historicalLayerIds.map((value) => String(value))
      : Array.isArray(study.selected_layers)
        ? study.selected_layers.map((value) => String(value))
        : []
  );

  if (mapController && selectedLayerIds.size > 0) {
    for (const layer of loadedHistoricalLayers) {
      mapController.setHistoricalLayerVisibility(layer.id, selectedLayerIds.has(layer.id));
      if (selectedLayerIds.has(layer.id)) {
        visibleHistoricalLayerIds.add(layer.id);
      } else {
        visibleHistoricalLayerIds.delete(layer.id);
      }
    }
  }

  if (mapController && typeof mapController.setHistoricalLayers === "function") {
    mapController.setHistoricalLayers(loadedHistoricalLayers);
  }

  if (study.selected_place_id) {
    selectedMarker = loadedMarkers.find((marker) => marker.id === study.selected_place_id) || null;
  }
  if (study.selected_route_id) {
    selectedRoute = loadedRoutes.find((route) => route.id === study.selected_route_id) || null;
  }
  if (study.selected_layer_id) {
    selectedHistoricalLayer =
      loadedHistoricalLayers.find((layer) => layer.id === study.selected_layer_id) || null;
    if (!selectedHistoricalLayer) {
      selectedPoliticalContext =
        loadedPoliticalContextLayers.find((layer) => layer.id === study.selected_layer_id) || null;
    }
  } else if (selectedLayerIds.size > 0) {
    const firstLayerId = Array.from(selectedLayerIds)[0];
    selectedHistoricalLayer =
      loadedHistoricalLayers.find((layer) => layer.id === firstLayerId) || null;
    if (!selectedHistoricalLayer) {
      selectedPoliticalContext =
        loadedPoliticalContextLayers.find((layer) => layer.id === firstLayerId) || null;
    }
  }
  if (selectedPoliticalContext) {
    visiblePoliticalContextLayerIds.add(selectedPoliticalContext.id);
    if (mapController && typeof mapController.setPoliticalContextLayerVisibility === "function") {
      mapController.setPoliticalContextLayerVisibility(selectedPoliticalContext.id, true);
    }
  }
  if (study.map_view_state && study.map_view_state.center && mapController?.map) {
    const center = study.map_view_state.center;
    const zoom = Number(study.map_view_state.zoom || mapController.map.getZoom());
    if (Array.isArray(center) && center.length === 2) {
      mapController.map.setView(center, zoom);
    }
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

function resetMapView() {
  if (!mapController) {
    setStatus("The map is still loading. Try resetting the view again in a moment.", "warning");
    return;
  }
  mapController.fitToContent();
  setStatus("Map view reset.", "success");
}

function setRouteVisibility(visible) {
  if (!mapController) {
    return;
  }
  mapController.setRouteVisibility(visible);
  if (visible && loadedRoutes.length === 0) {
    setStatus("Route view is on, but no curated routes are stored for this passage.", "empty");
  } else if (visible) {
    clearStatus();
  }
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
      setStatus("Loading historical layers...", "loading");
    }
    const {
      placeResult,
      routeResult,
      layerResult,
      politicalContextResult,
      savedMapStudiesResult,
    } = await loadMapData(lastPassageContext);
    loadedMarkers = placeResult.markers || [];
    loadedRoutes = routeResult.routes || [];
    loadedHistoricalLayers = layerResult.layers || [];
    loadedPoliticalContextLayers = politicalContextResult.layers || [];
    loadedSavedMapStudies = savedMapStudiesResult.saved_map_studies || [];
    renderLayerControls();
    if (selectedMarker && !loadedMarkers.some((marker) => marker.id === selectedMarker.id)) {
      selectedMarker = null;
    }
    if (selectedHistoricalLayer && !loadedHistoricalLayers.some((layer) => layer.id === selectedHistoricalLayer.id)) {
      selectedHistoricalLayer = null;
    }
    if (selectedRoute && !loadedRoutes.some((route) => route.id === selectedRoute.id)) {
      selectedRoute = null;
    }
    if (
      selectedPoliticalContext &&
      !loadedPoliticalContextLayers.some((layer) => layer.id === selectedPoliticalContext.id)
    ) {
      selectedPoliticalContext = null;
    }
    const routeToggle = getPanelElements().routeToggle;
    const routeVisibility = Boolean(routeToggle?.checked);
    ensureMapController(
      loadedMarkers,
      loadedRoutes,
      loadedHistoricalLayers,
      loadedPoliticalContextLayers,
      routeVisibility
    );
    syncRouteToggle();
    if (mapMode === "browse") {
      clearStatus();
      if (browseSearchResults.length > 0) {
        renderBrowseSearchResults(browseSearchResults, browseSearchQuery);
        refreshBrowseMapResults(browseSearchResults);
      } else {
        renderBrowseInstructions("Browse the catalog, or search by topic, location, route, or regional context.");
        refreshBrowseMapResults([]);
      }
    } else if (selectedMarker) {
      renderSelectedMarker(selectedMarker, lastPassageContext);
    } else if (selectedRoute) {
      renderSelectedRoute(selectedRoute, lastPassageContext);
    } else if (selectedHistoricalLayer) {
      renderSelectedHistoricalLayer(selectedHistoricalLayer, lastPassageContext);
    } else if (selectedPoliticalContext) {
      renderSelectedPoliticalContext(selectedPoliticalContext, lastPassageContext);
    } else {
      renderEmptyDetails("Choose a layer in the navigator to inspect its context here.");
    }
    renderLayerControls();
    await refreshSavedMapStudies();
    if (!loadedHistoricalLayers.length && !loadedPoliticalContextLayers.length) {
      setStatus("No historical or political overlays matched the selected period.", "empty");
    } else {
      clearStatus();
    }
  } catch (error) {
    setStatus(error.message || "Could not load historical layers.", "error");
    renderEmptyDetails("Could not load historical layers.");
  }
}

function setHistoricalLayerVisibility(layerId, visible) {
  const normalizedId = String(layerId || "");
  if (!normalizedId) {
    return;
  }
  if (visible) {
    visibleHistoricalLayerIds.add(normalizedId);
    const matchingLayer = loadedHistoricalLayers.find((layer) => layer.id === normalizedId);
    if (matchingLayer) {
      selectedHistoricalLayer = matchingLayer;
    }
  } else {
    visibleHistoricalLayerIds.delete(normalizedId);
    if (selectedHistoricalLayer && selectedHistoricalLayer.id === normalizedId) {
      selectedHistoricalLayer = null;
    }
  }
  if (mapController) {
    mapController.setHistoricalLayerVisibility(normalizedId, visible);
  }
  if (selectedMarker) {
    renderSelectedMarker(selectedMarker, lastPassageContext);
  } else if (selectedRoute) {
    renderSelectedRoute(selectedRoute, lastPassageContext);
  } else if (selectedHistoricalLayer) {
    renderSelectedHistoricalLayer(selectedHistoricalLayer, lastPassageContext);
  } else if (selectedPoliticalContext) {
    renderSelectedPoliticalContext(selectedPoliticalContext, lastPassageContext);
  } else {
    renderEmptyDetails("Choose a layer in the navigator to inspect its context here.");
  }
  renderLayerControls();
}

function setPoliticalContextLayerVisibility(layerId, visible) {
  const normalizedId = String(layerId || "");
  if (!normalizedId) {
    return;
  }
  if (visible) {
    visiblePoliticalContextLayerIds.add(normalizedId);
    const matchingLayer = loadedPoliticalContextLayers.find((layer) => layer.id === normalizedId);
    if (matchingLayer) {
      selectedPoliticalContext = matchingLayer;
    }
  } else {
    visiblePoliticalContextLayerIds.delete(normalizedId);
    if (selectedPoliticalContext && selectedPoliticalContext.id === normalizedId) {
      selectedPoliticalContext = null;
    }
  }
  if (mapController) {
    mapController.setPoliticalContextLayerVisibility(normalizedId, visible);
  }
  if (selectedMarker) {
    renderSelectedMarker(selectedMarker, lastPassageContext);
  } else if (selectedRoute) {
    renderSelectedRoute(selectedRoute, lastPassageContext);
  } else if (selectedHistoricalLayer) {
    renderSelectedHistoricalLayer(selectedHistoricalLayer, lastPassageContext);
  } else if (selectedPoliticalContext) {
    renderSelectedPoliticalContext(selectedPoliticalContext, lastPassageContext);
  } else {
    renderEmptyDetails("Choose a regional context layer in the navigator to inspect it here.");
  }
  renderLayerControls();
}

function syncRouteToggle() {
  const { routeToggle } = getPanelElements();
  syncRouteToggleHtml(mapController, routeToggle);
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

function renderSelectedHistoricalLayer(layer, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = renderSelectedHistoricalLayerHtml(layer, passageContext, {
    historicalOverview: "",
  });
  syncDetailsState(true);
}

function renderSelectedPoliticalContext(layer, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = renderSelectedPoliticalContextHtml(layer, passageContext, {
    politicalOverview: "",
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

function renderHistoricalLayerOverview() {
  return renderHistoricalLayerOverviewHtml(loadedHistoricalLayers, visibleHistoricalLayerIds);
}

function renderPoliticalContextLayerOverview() {
  return renderPoliticalContextLayerOverviewHtml(loadedPoliticalContextLayers, visiblePoliticalContextLayerIds);
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

async function saveCurrentMapStudy() {
  if (!lastPassageContext) {
    window.alert("Open a passage on the map first.");
    return;
  }
  const selection = getCurrentMapSelection();
  if (!selection) {
    window.alert("Select a place, route, historical layer, or political context first.");
    return;
  }
  const notes = window.prompt("Optional notes for this map study:", "");
  if (notes === null) {
    return;
  }
  const payload = {
    ...buildCurrentMapStudyPayload({
      lastPassageContext,
      mapController,
      visibleHistoricalLayerIds,
      visiblePoliticalContextLayerIds,
      historicalPeriod,
      selectedMarker,
      selectedRoute,
      selectedHistoricalLayer,
      selectedPoliticalContext,
      buildMapStudySummary,
      formatReference,
    }),
    user_notes: notes.trim(),
  };
  await requestJson("/api/map-studies", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  }, "Could not save map study.");
  invalidateMapCache("/api/map-studies");
  await refreshSavedMapStudies();
  setStatus("Map study saved.", "success");
}

async function addCurrentMapNote() {
  if (!lastPassageContext) {
    window.alert("Open a passage on the map first.");
    return;
  }
  const selection = getCurrentMapSelection();
  if (!selection) {
    window.alert("Select a place, route, historical layer, or political context first.");
    return;
  }
  const noteBody = window.prompt("Map note:", "");
  if (noteBody === null || !noteBody.trim()) {
    return;
  }
  const payload = {
    ...buildCurrentMapStudyPayload({
      lastPassageContext,
      mapController,
      visibleHistoricalLayerIds,
      visiblePoliticalContextLayerIds,
      historicalPeriod,
      selectedMarker,
      selectedRoute,
      selectedHistoricalLayer,
      selectedPoliticalContext,
      buildMapStudySummary,
      formatReference,
    }),
    note_body: noteBody.trim(),
    place_id: selection.kind === "place" ? selection.item.id : "",
    route_id: selection.kind === "route" ? selection.item.id : "",
    layer_id: selection.kind === "layer" || selection.kind === "political_context" ? selection.item.id : "",
  };
  await requestJson("/api/map-notes", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  }, "Could not save map note.");
  invalidateMapCache("/api/map-studies");
  await refreshSavedMapStudies();
  setStatus("Map note saved.", "success");
}

function activateAskWorkspace() {
  const askTab = document.querySelector('[data-workspace-tab="ask"]');
  if (askTab && askTab.getAttribute("aria-selected") !== "true") {
    askTab.click();
  }
}

async function askAboutCurrentMapSelection() {
  const selection = getCurrentMapSelection();
  if (!selection) {
    window.alert("Select a place, route, historical layer, or political context first.");
    return;
  }
  setMapStudyQuestion(
    `What does ${selection.item.name || "this location"} tell us about the historical setting of ${formatReference(lastPassageContext)}?`
  );
  submitMapStudyQuestion(buildCurrentMapStudyPayload({
    lastPassageContext,
    mapController,
    visibleHistoricalLayerIds,
    visiblePoliticalContextLayerIds,
    historicalPeriod,
    selectedMarker,
    selectedRoute,
    selectedHistoricalLayer,
    selectedPoliticalContext,
    buildMapStudySummary,
    formatReference,
  }));
}

async function viewRelatedPassagesForCurrentSelection() {
  setMapStudyQuestion(
    `What related passages or cross references should I review for ${formatReference(lastPassageContext)}?`
  );
  const form = document.querySelector(".ask-form");
  if (!form) {
    return;
  }
  setStudyFormValue("ask_mode", "cross_references");
  setStudyFormValue("study_action", "related_passages");
  setStudyMapContext(buildCurrentMapStudyPayload({
    lastPassageContext,
    mapController,
    visibleHistoricalLayerIds,
    visiblePoliticalContextLayerIds,
    historicalPeriod,
    selectedMarker,
    selectedRoute,
    selectedHistoricalLayer,
    selectedPoliticalContext,
    buildMapStudySummary,
    formatReference,
  }));
  submitStudyForm(form);
}

function setMapStudyQuestion(question) {
  const input = document.querySelector(".ask-form [name='question']");
  if (input) {
    input.value = question;
  }
}

function submitMapStudyQuestion(mapContext) {
  const form = document.querySelector(".ask-form");
  if (!form) {
    setStatus("The Ask panel is unavailable right now.", "error");
    return;
  }
  activateAskWorkspace();
  setStudyFormValue("ask_mode", "maps");
  setStudyFormValue("study_action", "ask_location");
  setStudyMapContext(mapContext);
  submitStudyForm(form);
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

async function refreshSavedMapStudies() {
  const { savedMapStudiesList, savedMapStudiesCount } = getPanelElements();
  if (!lastPassageContext) {
    if (savedMapStudiesCount) {
      savedMapStudiesCount.textContent = String(loadedSavedMapStudies.length);
    }
    if (savedMapStudiesList) {
      savedMapStudiesList.innerHTML = renderSavedMapStudies(loadedSavedMapStudies);
    }
    return;
  }
  const response = await loadSavedMapStudies(lastPassageContext);
  loadedSavedMapStudies = response.saved_map_studies || [];
  if (savedMapStudiesCount) {
    savedMapStudiesCount.textContent = String(loadedSavedMapStudies.length);
  }
  if (savedMapStudiesList) {
    savedMapStudiesList.innerHTML = renderSavedMapStudies(loadedSavedMapStudies);
  }
}

async function openSavedMapStudy(studyId) {
  const response = await loadSavedMapStudy(studyId);
  await openMapPanel({
    book: response.book,
    chapter: response.chapter,
    verseStart: response.start_verse,
    verseEnd: response.end_verse,
    savedMapStudy: response,
  });
}

async function deleteSavedMapStudy(studyId) {
  await requestJson(`/api/map-studies/${encodeURIComponent(studyId)}`, {
    method: "DELETE",
    headers: { Accept: "application/json" },
  }, "Could not delete saved map study.");
  invalidateMapCache("/api/map-studies");
  await refreshSavedMapStudies();
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
  const closeButton = document.querySelector("[data-map-close]");
  const resetButton = document.querySelector("[data-map-reset]");
  const expandButton = document.querySelector("[data-map-expand]");
  const modalCloseButton = document.querySelector("[data-map-modal-close]");
  const mapModeButtons = document.querySelectorAll("[data-map-mode-switch]");
  const mapSearchQuery = document.querySelector("[data-map-search-query]");
  const mapSearchKind = document.querySelector("[data-map-search-kind]");
  const mapSearchPeriod = document.querySelector("[data-map-search-period]");
  const mapSearchSubmit = document.querySelector("[data-map-search-submit]");
  const mapSearchClear = document.querySelector("[data-map-search-clear]");
  const mapSearchResultsList = document.querySelector("#map-search-results-list");
  const routeToggle = document.querySelector("[data-route-toggle]");
  const historicalPeriodSelect = document.querySelector("[data-historical-period]");
  const {
    modal,
    journeySearch: journeySearchInput,
    journeySelector,
    journeyTestament: journeyTestamentSelect,
    journeyCategory: journeyCategorySelect,
    journeyEra: journeyEraSelect,
    journeyToggle,
    journeyStopList,
    journeySegmentList,
    journeyDetail,
  } = getPanelElements();
  const details = document.querySelector("#map-details");
  const {
    savedMapStudiesList,
    studyMode: studyModeSelect,
    layerControls,
    layerReset,
    navigatorOpen,
    navigatorClose,
    detailsOpen,
    detailsClose,
  } = getPanelElements();

  if (closeButton) {
    closeButton.addEventListener("click", closeMapPanel);
  }
  if (resetButton) {
    resetButton.addEventListener("click", resetMapView);
  }
  if (expandButton) {
    expandButton.addEventListener("click", openMapModal);
  }
  if (modalCloseButton) {
    modalCloseButton.addEventListener("click", closeMapModal);
  }
  mapModeButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const nextMode = button.getAttribute("data-map-mode-switch");
      setMapMode(nextMode);
      if (nextMode === "browse") {
        await openMapPanel({ mode: "browse" });
      } else if (lastPassageContext) {
        await openMapPanel(lastPassageContext);
      }
    });
  });
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
  if (routeToggle) {
    routeToggle.addEventListener("change", (event) => {
      setRouteVisibility(Boolean(event.target.checked));
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
      getPanelElements().navigator?.classList.add("is-mobile-open");
    });
  }
  if (navigatorClose) {
    navigatorClose.addEventListener("click", () => {
      getPanelElements().navigator?.classList.remove("is-mobile-open");
    });
  }
  if (detailsOpen) {
    detailsOpen.addEventListener("click", () => {
      getPanelElements().detailsColumn?.classList.add("is-mobile-open");
    });
  }
  if (detailsClose) {
    detailsClose.addEventListener("click", () => {
      getPanelElements().detailsColumn?.classList.remove("is-mobile-open");
    });
  }
  if (layerReset) {
    layerReset.addEventListener("click", () => {
      visibleHistoricalLayerIds.clear();
      visiblePoliticalContextLayerIds.clear();
      loadedHistoricalLayers.forEach((layer) => mapController?.setHistoricalLayerVisibility(layer.id, false));
      loadedPoliticalContextLayers.forEach((layer) => mapController?.setPoliticalContextLayerVisibility(layer.id, false));
      selectedHistoricalLayer = null;
      selectedPoliticalContext = null;
      renderLayerControls();
      renderEmptyDetails("Layers cleared. Select a place, route, or layer to study it.");
    });
  }
  if (layerControls) {
    layerControls.addEventListener("change", (event) => {
      const toggle = event.target.closest("[data-historical-layer-toggle], [data-political-context-toggle]");
      if (!toggle) {
        return;
      }
      const layerId = toggle.getAttribute("data-layer-id");
      if (toggle.matches("[data-historical-layer-toggle]")) {
        setHistoricalLayerVisibility(layerId, toggle.checked);
      } else {
        setPoliticalContextLayerVisibility(layerId, toggle.checked);
      }
    });
  }
  if (journeySearchInput) {
    journeySearchInput.addEventListener("input", (event) => {
      journeySearch = event.target.value || "";
      if (selectedJourneyId && !getVisibleJourneys().some((journey) => journey.id === selectedJourneyId)) {
        selectedJourneyId = "";
        selectedJourneyStopId = "";
        selectedJourneySegmentId = "";
        applySelectedJourneyToMap({ fit: false });
      }
      renderJourneySidebar();
    });
  }
  if (journeySelector) {
    journeySelector.addEventListener("change", (event) => {
      selectJourney(event.target.value);
    });
  }
  if (journeyTestamentSelect) {
    journeyTestamentSelect.addEventListener("change", (event) => {
      journeyTestament = event.target.value || "";
      renderJourneySidebar();
    });
  }
  if (journeyCategorySelect) {
    journeyCategorySelect.addEventListener("change", (event) => {
      journeyCategory = event.target.value || "";
      renderJourneySidebar();
    });
  }
  if (journeyEraSelect) {
    journeyEraSelect.addEventListener("change", (event) => {
      journeyEra = event.target.value || "";
      renderJourneySidebar();
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
  if (journeyStopList) {
    journeyStopList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-map-journey-stop]");
      if (button) {
        selectJourneyStop(button.getAttribute("data-map-journey-stop"));
      }
    });
  }
  if (journeySegmentList) {
    journeySegmentList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-map-journey-segment]");
      if (button) {
        selectJourneySegment(button.getAttribute("data-map-journey-segment"));
      }
    });
  }
  if (journeyDetail) {
    journeyDetail.addEventListener("click", async (event) => {
      const passageButton = event.target.closest("[data-map-open-passage]");
      if (passageButton) {
        await openPassageReference(passageButton.getAttribute("data-map-open-passage"));
      }
    });
  }
  if (details) {
    details.addEventListener("click", async (event) => {
      const actionButton = event.target.closest("[data-map-action]");
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
      if (!actionButton) {
        return;
      }
      try {
        const action = actionButton.getAttribute("data-map-action");
        if (action === "ask_location") {
          await askAboutCurrentMapSelection();
        } else if (action === "save_map_study") {
          await saveCurrentMapStudy();
        } else if (action === "map_note") {
          await addCurrentMapNote();
        } else if (action === "related_passages") {
          await viewRelatedPassagesForCurrentSelection();
        } else if (action === "view_historical_layer") {
          const selection = getCurrentMapSelection();
          const { details } = getPanelElements();
          if (selection?.kind === "layer") {
            renderSelectedHistoricalLayer(selection.item, lastPassageContext);
          } else if (selection?.kind === "political_context") {
            renderSelectedPoliticalContext(selection.item, lastPassageContext);
          } else if (details) {
            details.innerHTML = `${renderHistoricalLayerOverview()}${renderPoliticalContextLayerOverview()}`;
            syncDetailsState(true);
          }
        } else if (action === "reset_map_view") {
          resetMapView();
        }
      } catch (error) {
        setStatus(error.message || "Could not complete that map action.", "error");
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
  if (savedMapStudiesList) {
    savedMapStudiesList.addEventListener("click", async (event) => {
      const actionButton = event.target.closest("[data-saved-map-study-action]");
      if (!actionButton) {
        return;
      }
      const studyId = actionButton.getAttribute("data-study-id");
      if (!studyId) {
        return;
      }
      const action = actionButton.getAttribute("data-saved-map-study-action");
      if (action === "open") {
        await openSavedMapStudy(studyId);
      } else if (action === "delete") {
        await deleteSavedMapStudy(studyId);
      }
    });
  }
}

function initializeMapPanel() {
  wirePanelButtons();
  renderEmptyDetails("Select a place pin, route, historical layer, or political context overlay to inspect its details here.");
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
    resetMapView,
    initializeMapPanel,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeMapPanel, { once: true });
  } else {
    initializeMapPanel();
  }
}
