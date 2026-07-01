import { createBibleMap } from "./BibleMap.js";
import {
  loadArchaeologyForPassage,
  loadMapCatalog,
  loadHistoricalLayers,
  invalidateMapCache,
  loadPlacesForPassage,
  loadManuscriptsForPassage,
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
  renderSelectedArchaeology as renderSelectedArchaeologyHtml,
  renderSelectedHistoricalLayer as renderSelectedHistoricalLayerHtml,
  renderSelectedMarker as renderSelectedMarkerHtml,
  renderSelectedManuscript as renderSelectedManuscriptHtml,
  renderSelectedPoliticalContext as renderSelectedPoliticalContextHtml,
  renderSelectedRoute as renderSelectedRouteHtml,
  renderPoliticalContextLayerOverview as renderPoliticalContextLayerOverviewHtml,
  renderArchaeologyLayerOverview as renderArchaeologyLayerOverviewHtml,
  renderManuscriptLayerOverview as renderManuscriptLayerOverviewHtml,
} from "./MapPanelContent.js";
import {
  buildArchaeologyCautionNote,
  buildArchaeologyExplanation,
  buildCautionNote,
  buildHistoricalLayerCautionNote,
  buildHistoricalLayerExplanation,
  buildMapStudySummary,
  buildManuscriptCautionNote,
  buildManuscriptExplanation,
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
  syncArchaeologyToggle as syncArchaeologyToggleHtml,
  syncHistoricalLayerToggles as syncHistoricalLayerTogglesHtml,
  syncManuscriptToggle as syncManuscriptToggleHtml,
  syncPoliticalContextLayerToggles as syncPoliticalContextLayerTogglesHtml,
  syncRouteToggle as syncRouteToggleHtml,
} from "./MapPanelStateHelpers.js";

// Source links still point to `/sources/` in the rendered map panel markup.
const BHF_HTTP = window.BHFApi || {};

let mapController = null;
let selectedMarker = null;
let selectedArchaeology = null;
let selectedManuscript = null;
let selectedRoute = null;
let selectedHistoricalLayer = null;
let selectedPoliticalContext = null;
let mapMode = "passage";
let lastPassageContext = null;
let loadedMarkers = [];
let loadedArchaeologyMarkers = [];
let loadedManuscriptMarkers = [];
let loadedRoutes = [];
let loadedHistoricalLayers = [];
let loadedPoliticalContextLayers = [];
let loadedSavedMapStudies = [];
let browseSearchResults = [];
let browseSearchQuery = "";
let browseSearchKind = "all";
let browseSearchPeriod = "all";
let historicalPeriod = "all";
let archaeologyVisible = false;
let manuscriptsVisible = false;
let mapModalOpen = false;
let lastModalTrigger = null;
const visibleHistoricalLayerIds = new Set();
const visiblePoliticalContextLayerIds = new Set();

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

const HISTORICAL_PERIOD_OPTIONS = [
  { value: "all", label: "All periods" },
  { value: "Broad / uncertain period", label: "Broad / uncertain period" },
  { value: "Divided Kingdom", label: "Divided Kingdom" },
  { value: "Assyrian period", label: "Assyrian period" },
  { value: "Babylonian period", label: "Babylonian period" },
  { value: "Persian period", label: "Persian period" },
  { value: "Hellenistic period", label: "Hellenistic period" },
  { value: "NT / Roman period", label: "NT / Roman period" },
];

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
    archaeologyToggle: document.querySelector("[data-archaeology-toggle]"),
    manuscriptToggle: document.querySelector("[data-manuscript-toggle]"),
    routeToggle: document.querySelector("[data-route-toggle]"),
    historicalPeriod: document.querySelector("[data-historical-period]"),
    mapBrowser: document.querySelector("[data-map-browser]"),
    mapModeButtons: document.querySelectorAll("[data-map-mode-switch]"),
    mapSearchQuery: document.querySelector("[data-map-search-query]"),
    mapSearchKind: document.querySelector("[data-map-search-kind]"),
    mapSearchPeriod: document.querySelector("[data-map-search-period]"),
    mapSearchSubmit: document.querySelector("[data-map-search-submit]"),
    mapSearchClear: document.querySelector("[data-map-search-clear]"),
    mapSearchResults: document.querySelector("#map-search-results"),
    mapSearchResultsCount: document.querySelector("#map-search-results-count"),
    mapSearchResultsList: document.querySelector("#map-search-results-list"),
    workspace: document.querySelector("#map-workspace"),
    inlineHost: document.querySelector("#map-workspace-inline-host"),
    modal: document.querySelector("#map-modal"),
    modalHost: document.querySelector("#map-workspace-modal-host"),
  };
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
    archaeologyResult,
    manuscriptResult,
    routeResult,
    layerResult,
    politicalContextResult,
    savedMapStudiesResult,
  ] = await Promise.all([
    loadPlacesForPassage(loadContext),
    loadArchaeologyForPassage(loadContext),
    loadManuscriptsForPassage(loadContext),
    loadRoutesForPassage(loadContext),
    loadHistoricalLayers({ period: historicalPeriod }),
    loadPoliticalContextForPassage(loadContext),
    loadSavedMapStudies(context),
  ]);
  const offline = [
    placeResult,
    archaeologyResult,
    manuscriptResult,
    routeResult,
    layerResult,
    politicalContextResult,
    savedMapStudiesResult,
  ].some((result) => Boolean(result?.offline));
  return {
    placeResult,
    archaeologyResult,
    manuscriptResult,
    routeResult,
    layerResult,
    politicalContextResult,
    savedMapStudiesResult,
    offline,
  };
}

async function loadBrowseMapData() {
  const [
    catalog,
    savedMapStudiesResult,
  ] = await Promise.all([
    loadMapCatalog({ period: browseSearchPeriod }),
    loadSavedMapStudies(),
  ]);
  return {
    placeResult: { markers: catalog.places || [] },
    archaeologyResult: { markers: catalog.archaeology || [] },
    manuscriptResult: { markers: catalog.manuscripts || [] },
    routeResult: { routes: catalog.routes || [] },
    layerResult: { layers: catalog.historical_layers || [] },
    politicalContextResult: { layers: catalog.political_context || [] },
    savedMapStudiesResult: savedMapStudiesResult || { saved_map_studies: [] },
    offline: Boolean(catalog.offline || savedMapStudiesResult?.offline),
  };
}

async function loadMapData(context = {}) {
  return mapMode === "browse" ? loadBrowseMapData() : loadPassageMapData(context);
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
  const { mapBrowser, mapModeButtons, mapSearchResults } = getPanelElements();
  if (mapBrowser) {
    mapBrowser.hidden = mapMode !== "browse";
  }
  if (mapSearchResults) {
    mapSearchResults.hidden = mapMode !== "browse";
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
        <li>Search a topic, place, route, archaeology item, manuscript, historical layer, or political context.</li>
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
  selectedMarker = null;
  selectedArchaeology = null;
  selectedManuscript = null;
  selectedRoute = null;
  selectedHistoricalLayer = null;
  selectedPoliticalContext = null;

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
  if (result.kind === "archaeology") {
    selectedArchaeology = result.item;
    renderSelectedArchaeology(selectedArchaeology, null);
    focusMapSelection(result);
    return;
  }
  if (result.kind === "manuscript") {
    selectedManuscript = result.item;
    renderSelectedManuscript(selectedManuscript, null);
    focusMapSelection(result);
    return;
  }
  if (result.kind === "historical_layer") {
    selectedHistoricalLayer = result.item;
    renderSelectedHistoricalLayer(selectedHistoricalLayer, null);
    focusMapSelection(result);
    return;
  }
  if (result.kind === "political_context") {
    selectedPoliticalContext = result.item;
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
    renderBrowseInstructions();
    clearStatus();
    return;
  }

  setStatus(`Searching the map catalog for "${query}"...`, "loading");
  try {
    const result = await searchMapCatalog(query, {
      kind,
      period: browseSearchPeriod,
      limit: 30,
    });
    renderBrowseSearchResults(result.results || [], query);
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
  renderBrowseInstructions();
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
  archaeologyMarkers,
  manuscriptMarkers,
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
    archaeologyMarkers,
    manuscriptMarkers,
    routes,
    historicalLayers,
    historicalLayerIds: Array.from(visibleHistoricalLayerIds),
    politicalContextLayers,
    politicalContextLayerIds: Array.from(visiblePoliticalContextLayerIds),
    routeVisibility,
    archaeologyVisibility: archaeologyVisible,
    manuscriptVisibility: manuscriptsVisible,
    onTileError(error) {
      setStatus(error.message, "error");
    },
    onMarkerClick(marker) {
      selectedMarker = marker;
      selectedArchaeology = null;
      selectedRoute = null;
      selectedHistoricalLayer = null;
      renderSelectedMarker(marker, lastPassageContext);
    },
    onArchaeologyClick(marker) {
      selectedArchaeology = marker;
      selectedMarker = null;
      selectedRoute = null;
      selectedHistoricalLayer = null;
      selectedManuscript = null;
      renderSelectedArchaeology(marker, lastPassageContext);
    },
    onManuscriptClick(marker) {
      selectedManuscript = marker;
      selectedMarker = null;
      selectedArchaeology = null;
      selectedRoute = null;
      selectedHistoricalLayer = null;
      selectedPoliticalContext = null;
      renderSelectedManuscript(marker, lastPassageContext);
    },
    onRouteClick(route) {
      selectedRoute = route;
      selectedMarker = null;
      selectedArchaeology = null;
      selectedHistoricalLayer = null;
      selectedManuscript = null;
      renderSelectedRoute(route, lastPassageContext);
    },
    onHistoricalLayerClick(layer) {
      selectedHistoricalLayer = layer;
      selectedMarker = null;
      selectedArchaeology = null;
      selectedRoute = null;
      selectedManuscript = null;
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
      selectedArchaeology = null;
      selectedRoute = null;
      selectedHistoricalLayer = null;
      selectedManuscript = null;
      visiblePoliticalContextLayerIds.add(layer.id);
      if (mapController) {
        mapController.setPoliticalContextLayerVisibility(layer.id, true);
      }
      renderSelectedPoliticalContext(layer, lastPassageContext);
    },
  });
  return mapController;
}

async function openMapPanel(context = {}) {
  const browseMode = context.mode === "browse" || (!context.book && !context.chapter && !context.savedMapStudy);
  setMapMode(browseMode ? "browse" : "passage");
  if (browseMode) {
    selectedMarker = null;
    selectedArchaeology = null;
    selectedManuscript = null;
    selectedRoute = null;
    selectedHistoricalLayer = null;
    selectedPoliticalContext = null;
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
      selectedMarker = null;
      selectedArchaeology = null;
      selectedManuscript = null;
      selectedRoute = null;
      selectedHistoricalLayer = null;
      selectedPoliticalContext = null;
    }
  }
  if (context.savedMapStudy?.map_view_state?.historicalPeriod) {
    historicalPeriod = normalizeHistoricalPeriod(context.savedMapStudy.map_view_state.historicalPeriod);
  }
  if (context.savedMapStudy?.map_view_state && Object.prototype.hasOwnProperty.call(context.savedMapStudy.map_view_state, "archaeologyVisibility")) {
    archaeologyVisible = Boolean(context.savedMapStudy.map_view_state.archaeologyVisibility);
  }
  if (context.savedMapStudy?.map_view_state && Object.prototype.hasOwnProperty.call(context.savedMapStudy.map_view_state, "manuscriptVisibility")) {
    manuscriptsVisible = Boolean(context.savedMapStudy.map_view_state.manuscriptVisibility);
  }
  if (!browseMode) {
    lastPassageContext = context;
  }
  ensurePanelVisible(context);
  setPinHint("");
  setStatus(browseMode ? "Loading map catalog..." : "Loading map data...", "loading");
  renderEmptyDetails(
    browseMode
      ? "Loading the curated map catalog so you can search by topic, location, or archaeological evidence."
      : "Loading place, archaeology, manuscript, route, historical, and political context details..."
  );

  try {
    const routeToggle = getPanelElements().routeToggle;
    const archaeologyToggle = getPanelElements().archaeologyToggle;
    archaeologyVisible = archaeologyToggle ? Boolean(archaeologyToggle.checked) : archaeologyVisible;
    const routeVisibility = Boolean(routeToggle?.checked);
    const {
      placeResult,
      archaeologyResult,
      manuscriptResult,
      routeResult,
      layerResult,
      politicalContextResult,
      savedMapStudiesResult,
      offline,
    } = await loadMapData(context);
    loadedRoutes = routeResult.routes || [];
    loadedMarkers = placeResult.markers || [];
    loadedArchaeologyMarkers = archaeologyResult.markers || [];
    loadedManuscriptMarkers = manuscriptResult.markers || [];
    loadedHistoricalLayers = layerResult.layers || [];
    loadedPoliticalContextLayers = politicalContextResult.layers || [];
    loadedSavedMapStudies = savedMapStudiesResult.saved_map_studies || [];
    if (selectedMarker && !loadedMarkers.some((marker) => marker.id === selectedMarker.id)) {
      selectedMarker = null;
    }
    if (selectedHistoricalLayer && !loadedHistoricalLayers.some((layer) => layer.id === selectedHistoricalLayer.id)) {
      selectedHistoricalLayer = null;
    }
    if (selectedArchaeology && !loadedArchaeologyMarkers.some((marker) => marker.id === selectedArchaeology.id)) {
      selectedArchaeology = null;
    }
    if (selectedManuscript && !loadedManuscriptMarkers.some((marker) => marker.id === selectedManuscript.id)) {
      selectedManuscript = null;
    }
    if (selectedRoute && !loadedRoutes.some((route) => route.id === selectedRoute.id)) {
      selectedRoute = null;
    }
    if (selectedPoliticalContext && !loadedPoliticalContextLayers.some((layer) => layer.id === selectedPoliticalContext.id)) {
      selectedPoliticalContext = null;
    }

    ensureMapController(
      loadedMarkers,
      loadedArchaeologyMarkers,
      loadedManuscriptMarkers,
      loadedRoutes,
      loadedHistoricalLayers,
      loadedPoliticalContextLayers,
      routeVisibility
    );
    if (context.savedMapStudy) {
      await applySavedMapStudyState(context.savedMapStudy);
    }
    syncArchaeologyToggle();
    syncManuscriptToggle();
    syncRouteToggle();
    syncHistoricalPeriod();
    syncHistoricalLayerToggles();
    syncPoliticalContextLayerToggles();
    await refreshSavedMapStudies();

    if (browseMode) {
      clearStatus();
      if (browseSearchResults.length > 0) {
        renderBrowseSearchResults(browseSearchResults, browseSearchQuery);
      } else {
        renderBrowseInstructions("Browse the catalog, or search by topic, location, or archaeology evidence.");
      }
      return;
    }

    if (selectedMarker && (placeResult.markers || []).some((marker) => marker.id === selectedMarker.id)) {
      renderSelectedMarker(selectedMarker, context);
      clearStatus();
    } else if (selectedArchaeology && loadedArchaeologyMarkers.some((marker) => marker.id === selectedArchaeology.id)) {
      renderSelectedArchaeology(selectedArchaeology, context);
      clearStatus();
    } else if (selectedManuscript && loadedManuscriptMarkers.some((marker) => marker.id === selectedManuscript.id)) {
      renderSelectedManuscript(selectedManuscript, context);
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
          loadedArchaeologyMarkers.length === 0 &&
          loadedManuscriptMarkers.length === 0 &&
          loadedHistoricalLayers.length === 0 &&
          loadedPoliticalContextLayers.length === 0;
        renderEmptyDetails(
          "No curated point-place match was found for this passage. You can still study any available region, empire, historical, archaeology, or manuscript layers below."
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
                  "No curated local map places, routes, archaeology markers, manuscript witnesses, historical layers, or political-context overlays matched this passage.",
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
        renderEmptyDetails("Select a place pin, route, archaeology item, manuscript, or overlay to inspect its details here.");
      }
    }

    if (routeVisibility && loadedRoutes.length === 0) {
      setStatus("Route view is on, but no curated routes are stored for this passage.", "empty");
    }
    if (archaeologyVisible && loadedArchaeologyMarkers.length === 0) {
      setStatus("Archaeology view is on, but no curated archaeology items are stored for this passage.", "empty");
    }
    if (
      !loadedHistoricalLayers.length &&
      !loadedPoliticalContextLayers.length &&
      !selectedMarker &&
      !selectedArchaeology &&
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
    renderEmptyDetails("Could not load place, archaeology, manuscript, route, and layer details.");
  }
}

async function applySavedMapStudyState(study) {
  if (!study) {
    return;
  }
  const viewState = study.map_view_state || {};
  historicalPeriod = normalizeHistoricalPeriod(viewState.historicalPeriod || "all");
  selectedMarker = null;
  selectedArchaeology = null;
  selectedManuscript = null;
  selectedRoute = null;
  selectedHistoricalLayer = null;
  selectedPoliticalContext = null;

  if (mapController && typeof mapController.setRouteVisibility === "function" && Object.prototype.hasOwnProperty.call(viewState, "routeVisibility")) {
    mapController.setRouteVisibility(Boolean(viewState.routeVisibility));
  }
  if (mapController && typeof mapController.setArchaeologyVisibility === "function" && Object.prototype.hasOwnProperty.call(viewState, "archaeologyVisibility")) {
    archaeologyVisible = Boolean(viewState.archaeologyVisibility);
    mapController.setArchaeologyVisibility(Boolean(viewState.archaeologyVisibility));
  }
  if (mapController && typeof mapController.setManuscriptVisibility === "function" && Object.prototype.hasOwnProperty.call(viewState, "manuscriptVisibility")) {
    manuscriptsVisible = Boolean(viewState.manuscriptVisibility);
    mapController.setManuscriptVisibility(Boolean(viewState.manuscriptVisibility));
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
  if (study.selected_archaeology_id) {
    selectedArchaeology =
      loadedArchaeologyMarkers.find((marker) => marker.id === study.selected_archaeology_id) || null;
  }
  if (study.selected_manuscript_id) {
    selectedManuscript =
      loadedManuscriptMarkers.find((marker) => marker.id === study.selected_manuscript_id) || null;
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
  if (selectedManuscript && mapController && typeof mapController.setManuscriptVisibility === "function") {
    manuscriptsVisible = true;
    mapController.setManuscriptVisibility(true);
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
    return;
  }
  mapController.fitToContent();
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

function setArchaeologyVisibility(visible) {
  archaeologyVisible = Boolean(visible);
  const { archaeologyToggle } = getPanelElements();
  if (archaeologyToggle) {
    archaeologyToggle.checked = archaeologyVisible;
  }
  if (!mapController) {
    return;
  }
  mapController.setArchaeologyVisibility(archaeologyVisible);
  if (archaeologyVisible && loadedArchaeologyMarkers.length === 0) {
    setStatus("Archaeology view is on, but no curated archaeology items are stored for this passage.", "empty");
  } else if (archaeologyVisible) {
    clearStatus();
    if (selectedMarker) {
      renderSelectedMarker(selectedMarker, lastPassageContext);
    } else if (selectedArchaeology) {
      renderSelectedArchaeology(selectedArchaeology, lastPassageContext);
    } else if (selectedRoute) {
      renderSelectedRoute(selectedRoute, lastPassageContext);
    } else if (selectedHistoricalLayer) {
      renderSelectedHistoricalLayer(selectedHistoricalLayer, lastPassageContext);
    } else {
      renderArchaeologyLayerOverview();
    }
  }
}

function setManuscriptVisibility(visible) {
  manuscriptsVisible = Boolean(visible);
  const { manuscriptToggle } = getPanelElements();
  if (manuscriptToggle) {
    manuscriptToggle.checked = manuscriptsVisible;
  }
  if (!mapController) {
    return;
  }
  mapController.setManuscriptVisibility(manuscriptsVisible);
  if (manuscriptsVisible && loadedManuscriptMarkers.length === 0) {
    setStatus("Manuscript view is on, but no curated manuscript items are stored for this passage.", "empty");
  } else if (manuscriptsVisible) {
    clearStatus();
    if (selectedMarker) {
      renderSelectedMarker(selectedMarker, lastPassageContext);
    } else if (selectedArchaeology) {
      renderSelectedArchaeology(selectedArchaeology, lastPassageContext);
    } else if (selectedManuscript) {
      renderSelectedManuscript(selectedManuscript, lastPassageContext);
    } else if (selectedRoute) {
      renderSelectedRoute(selectedRoute, lastPassageContext);
    } else if (selectedHistoricalLayer) {
      renderSelectedHistoricalLayer(selectedHistoricalLayer, lastPassageContext);
    } else if (selectedPoliticalContext) {
      renderSelectedPoliticalContext(selectedPoliticalContext, lastPassageContext);
    } else {
      renderManuscriptLayerOverview();
    }
  }
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
      archaeologyResult,
      manuscriptResult,
      routeResult,
      layerResult,
      politicalContextResult,
      savedMapStudiesResult,
    } = await loadMapData(lastPassageContext);
    loadedMarkers = placeResult.markers || [];
    loadedArchaeologyMarkers = archaeologyResult.markers || [];
    loadedManuscriptMarkers = manuscriptResult.markers || [];
    loadedRoutes = routeResult.routes || [];
    loadedHistoricalLayers = layerResult.layers || [];
    loadedPoliticalContextLayers = politicalContextResult.layers || [];
    loadedSavedMapStudies = savedMapStudiesResult.saved_map_studies || [];
    if (selectedMarker && !loadedMarkers.some((marker) => marker.id === selectedMarker.id)) {
      selectedMarker = null;
    }
    if (selectedHistoricalLayer && !loadedHistoricalLayers.some((layer) => layer.id === selectedHistoricalLayer.id)) {
      selectedHistoricalLayer = null;
    }
    if (selectedArchaeology && !loadedArchaeologyMarkers.some((marker) => marker.id === selectedArchaeology.id)) {
      selectedArchaeology = null;
    }
    if (selectedManuscript && !loadedManuscriptMarkers.some((marker) => marker.id === selectedManuscript.id)) {
      selectedManuscript = null;
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
    const manuscriptToggle = getPanelElements().manuscriptToggle;
    manuscriptsVisible = manuscriptToggle ? Boolean(manuscriptToggle.checked) : manuscriptsVisible;
    ensureMapController(
      loadedMarkers,
      loadedArchaeologyMarkers,
      loadedManuscriptMarkers,
      loadedRoutes,
      loadedHistoricalLayers,
      loadedPoliticalContextLayers,
      routeVisibility
    );
    syncArchaeologyToggle();
    syncManuscriptToggle();
    syncRouteToggle();
    syncHistoricalLayerToggles();
    if (mapMode === "browse") {
      clearStatus();
      if (browseSearchResults.length > 0) {
        renderBrowseSearchResults(browseSearchResults, browseSearchQuery);
      } else {
        renderBrowseInstructions("Browse the catalog, or search by topic, location, or archaeology evidence.");
      }
    } else if (selectedMarker) {
      renderSelectedMarker(selectedMarker, lastPassageContext);
    } else if (selectedArchaeology) {
      renderSelectedArchaeology(selectedArchaeology, lastPassageContext);
    } else if (selectedManuscript) {
      renderSelectedManuscript(selectedManuscript, lastPassageContext);
    } else if (selectedRoute) {
      renderSelectedRoute(selectedRoute, lastPassageContext);
    } else if (selectedHistoricalLayer) {
      renderSelectedHistoricalLayer(selectedHistoricalLayer, lastPassageContext);
    } else if (selectedPoliticalContext) {
      renderSelectedPoliticalContext(selectedPoliticalContext, lastPassageContext);
    } else {
      renderHistoricalLayerOverview();
    }
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
  syncHistoricalLayerToggles();
  syncPoliticalContextLayerToggles();
  if (selectedMarker) {
    renderSelectedMarker(selectedMarker, lastPassageContext);
  } else if (selectedArchaeology) {
    renderSelectedArchaeology(selectedArchaeology, lastPassageContext);
  } else if (selectedManuscript) {
    renderSelectedManuscript(selectedManuscript, lastPassageContext);
  } else if (selectedRoute) {
    renderSelectedRoute(selectedRoute, lastPassageContext);
  } else if (selectedHistoricalLayer) {
    renderSelectedHistoricalLayer(selectedHistoricalLayer, lastPassageContext);
  } else if (selectedPoliticalContext) {
    renderSelectedPoliticalContext(selectedPoliticalContext, lastPassageContext);
  } else {
    renderHistoricalLayerOverview();
  }
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
  syncPoliticalContextLayerToggles();
  if (selectedMarker) {
    renderSelectedMarker(selectedMarker, lastPassageContext);
  } else if (selectedArchaeology) {
    renderSelectedArchaeology(selectedArchaeology, lastPassageContext);
  } else if (selectedRoute) {
    renderSelectedRoute(selectedRoute, lastPassageContext);
  } else if (selectedHistoricalLayer) {
    renderSelectedHistoricalLayer(selectedHistoricalLayer, lastPassageContext);
  } else if (selectedPoliticalContext) {
    renderSelectedPoliticalContext(selectedPoliticalContext, lastPassageContext);
  } else {
    renderPoliticalContextLayerOverview();
  }
}

function syncRouteToggle() {
  const { routeToggle } = getPanelElements();
  syncRouteToggleHtml(mapController, routeToggle);
}

function syncArchaeologyToggle() {
  const { archaeologyToggle } = getPanelElements();
  syncArchaeologyToggleHtml(mapController, archaeologyToggle);
}

function syncManuscriptToggle() {
  const { manuscriptToggle } = getPanelElements();
  syncManuscriptToggleHtml(mapController, manuscriptToggle);
}

function syncHistoricalLayerToggles() {
  const { details } = getPanelElements();
  syncHistoricalLayerTogglesHtml(details, visibleHistoricalLayerIds);
}

function syncPoliticalContextLayerToggles() {
  const { details } = getPanelElements();
  syncPoliticalContextLayerTogglesHtml(details, visiblePoliticalContextLayerIds);
}

function renderSelectedMarker(marker, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = renderSelectedMarkerHtml(marker, passageContext, {
    historicalOverview: renderHistoricalLayerOverview(),
  });
}

function renderSelectedArchaeology(marker, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = renderSelectedArchaeologyHtml(marker, passageContext, {
    archaeologyOverview: renderArchaeologyLayerOverview(),
  });
}

function renderSelectedManuscript(marker, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = renderSelectedManuscriptHtml(marker, passageContext, {
    manuscriptOverview: renderManuscriptLayerOverview(),
  });
}

function renderSelectedRoute(route, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = renderSelectedRouteHtml(route, passageContext, {
    historicalOverview: renderHistoricalLayerOverview(),
  });
}

function renderSelectedHistoricalLayer(layer, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = renderSelectedHistoricalLayerHtml(layer, passageContext, {
    historicalOverview: renderHistoricalLayerOverview(),
  });
}

function renderSelectedPoliticalContext(layer, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = renderSelectedPoliticalContextHtml(layer, passageContext, {
    politicalOverview: renderPoliticalContextLayerOverview(),
  });
}

function renderHistoricalLayerOverview() {
  return renderHistoricalLayerOverviewHtml(loadedHistoricalLayers, visibleHistoricalLayerIds);
}

function renderPoliticalContextLayerOverview() {
  return renderPoliticalContextLayerOverviewHtml(loadedPoliticalContextLayers, visiblePoliticalContextLayerIds);
}

function renderArchaeologyLayerOverview() {
  return renderArchaeologyLayerOverviewHtml(loadedArchaeologyMarkers, archaeologyVisible);
}

function renderManuscriptLayerOverview() {
  return renderManuscriptLayerOverviewHtml(loadedManuscriptMarkers, manuscriptsVisible);
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
    window.alert("Select a place, archaeology item, manuscript, route, or historical layer first.");
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
      selectedArchaeology,
      selectedManuscript,
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
}

async function addCurrentMapNote() {
  if (!lastPassageContext) {
    window.alert("Open a passage on the map first.");
    return;
  }
  const selection = getCurrentMapSelection();
  if (!selection) {
    window.alert("Select a place, archaeology item, manuscript, route, or historical layer first.");
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
      selectedArchaeology,
      selectedManuscript,
      selectedRoute,
      selectedHistoricalLayer,
      selectedPoliticalContext,
      buildMapStudySummary,
      formatReference,
    }),
    note_body: noteBody.trim(),
    place_id: selection.kind === "place" ? selection.item.id : "",
    archaeology_id: selection.kind === "archaeology" ? selection.item.id : "",
    manuscript_id: selection.kind === "manuscript" ? selection.item.id : "",
    route_id: selection.kind === "route" ? selection.item.id : "",
    layer_id: selection.kind === "layer" ? selection.item.id : "",
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
}

async function askAboutCurrentMapSelection() {
  const selection = getCurrentMapSelection();
  if (!selection) {
    window.alert("Select a place, archaeology item, manuscript, route, or historical layer first.");
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
    selectedArchaeology,
    selectedManuscript,
    selectedRoute,
    selectedHistoricalLayer,
    selectedPoliticalContext,
    buildMapStudySummary,
    formatReference,
  }));
}

async function compareArchaeologyForCurrentSelection() {
  const selection = getCurrentMapSelection();
  if (!selection) {
    window.alert("Select a place, archaeology item, manuscript, route, or historical layer first.");
    return;
  }
  setMapStudyQuestion(
    `What archaeology is connected with ${selection.item.name || "this location"} and the passage ${formatReference(lastPassageContext)}?`
  );
  submitMapStudyQuestion(buildCurrentMapStudyPayload({
    lastPassageContext,
    mapController,
    visibleHistoricalLayerIds,
    visiblePoliticalContextLayerIds,
    historicalPeriod,
    selectedMarker,
    selectedArchaeology,
    selectedManuscript,
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
    selectedArchaeology,
    selectedManuscript,
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
    return;
  }
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
    ${renderHistoricalLayerOverview()}
    ${renderPoliticalContextLayerOverview()}
    ${renderArchaeologyLayerOverview()}
    ${renderManuscriptLayerOverview()}
  `;
}

function syncHistoricalPeriod() {
  const { historicalPeriod: historicalPeriodSelect } = getPanelElements();
  if (historicalPeriodSelect) {
    historicalPeriodSelect.value = historicalPeriod;
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
  const archaeologyToggle = document.querySelector("[data-archaeology-toggle]");
  const manuscriptToggle = document.querySelector("[data-manuscript-toggle]");
  const routeToggle = document.querySelector("[data-route-toggle]");
  const historicalPeriodSelect = document.querySelector("[data-historical-period]");
  const { modal } = getPanelElements();
  const details = document.querySelector("#map-details");
  const { savedMapStudiesList } = getPanelElements();

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
  if (archaeologyToggle) {
    archaeologyToggle.addEventListener("change", (event) => {
      setArchaeologyVisibility(Boolean(event.target.checked));
    });
  }
  if (manuscriptToggle) {
    manuscriptToggle.addEventListener("change", (event) => {
      setManuscriptVisibility(Boolean(event.target.checked));
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
  if (details) {
    details.addEventListener("click", async (event) => {
      const actionButton = event.target.closest("[data-map-action]");
      const passageShortcut = event.target.closest("[data-passage-shortcut]");
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
      const action = actionButton.getAttribute("data-map-action");
      if (action === "ask_location") {
        await askAboutCurrentMapSelection();
      } else if (action === "save_map_study") {
        await saveCurrentMapStudy();
      } else if (action === "map_note") {
        await addCurrentMapNote();
      } else if (action === "compare_archaeology") {
        await compareArchaeologyForCurrentSelection();
      } else if (action === "related_passages") {
        await viewRelatedPassagesForCurrentSelection();
      } else if (action === "view_historical_layer") {
        const selection = getCurrentMapSelection();
        if (selection?.kind === "layer") {
          renderSelectedHistoricalLayer(selection.item, lastPassageContext);
        } else {
          renderHistoricalLayerOverview();
        }
      } else if (action === "reset_map_view") {
        resetMapView();
      }
    });
    details.addEventListener("change", (event) => {
      const toggle = event.target.closest("[data-historical-layer-toggle]");
      if (!toggle) {
        const politicalToggle = event.target.closest("[data-political-context-toggle]");
        if (!politicalToggle) {
          return;
        }
        setPoliticalContextLayerVisibility(
          politicalToggle.getAttribute("data-layer-id"),
          Boolean(politicalToggle.checked)
        );
        return;
      }
      setHistoricalLayerVisibility(toggle.getAttribute("data-layer-id"), Boolean(toggle.checked));
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
  renderEmptyDetails("Select a place pin, route, archaeology item, manuscript, or overlay to inspect its details here.");
  syncArchaeologyToggle();
  syncManuscriptToggle();
  syncHistoricalPeriod();
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
