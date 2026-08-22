import { createBibleMap } from "./BibleMap.js";
import {
  loadMapCatalog,
  loadPlacesForPassage,
  loadRoutesForPassage,
  searchMapCatalog,
} from "./mapService.js?v=20260729b";
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
let mapPanelEventsWired = false;

function requestJson(url, options = {}, fallbackMessage = "Request failed.") {
  if (typeof BHF_HTTP.requestJson === "function") {
    return BHF_HTTP.requestJson(url, options, fallbackMessage);
  }
  let resolvedUrl = url;
  if (typeof BHF_HTTP.resolveUrl === "function") {
    resolvedUrl = BHF_HTTP.resolveUrl(url);
  } else if (String(window.BHFRuntimeConfig?.backendMode || "same-origin") === "remote") {
    throw new Error("BHF backend is not configured for this deployment.");
  }
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
    setMobileDetailsOpen(hasSelection);
  }
}

function setMobileNavigatorOpen(isOpen) {
  const { navigator: navigatorPanel, navigatorOpen } = getPanelElements();
  const open = Boolean(isOpen);
  navigatorPanel?.classList.toggle("is-mobile-open", open);
  navigatorOpen?.setAttribute("aria-expanded", String(open));
}

function setMobileDetailsOpen(isOpen) {
  const { detailsColumn, detailsOpen } = getPanelElements();
  const open = Boolean(isOpen);
  detailsColumn?.classList.toggle("is-mobile-open", open);
  detailsOpen?.setAttribute("aria-expanded", String(open));
  if (
    open &&
    detailsColumn &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(max-width: 900px)").matches
  ) {
    window.requestAnimationFrame(() => {
      detailsColumn.scrollIntoView({block: "nearest"});
    });
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
  });
  return mapController;
}

async function openMapPanel(context = {}) {
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
    // Put the panel into its usable state before waiting on catalog metadata.
    // This matters on slow/offline connections: Explore should still expose
    // its search and navigation controls while the catalog request resolves.
    const catalog = await loadMapCatalog({ period: "all" });
    if (catalog?.timeline?.period_options) {
      applyTimelineOptions(catalog.timeline.period_options);
    }
    const routeVisibility = true;
    const {
      placeResult,
      routeResult,
      offline,
    } = await loadMapData(context);
    loadedRoutes = routeResult.routes || [];
    loadedMarkers = placeResult.markers || [];
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
      renderEmptyDetails("Choose a place or route to inspect its details here.");
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

// Compatibility seams for saved-map clients that still expose historical layers.
function renderSelectedHistoricalLayer(layer, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = `<section class="map-details-card"><h3>${escapeHtml(layer?.name || "Historical layer")}</h3><p>${escapeHtml(layer?.description || "Historical context layer")}</p></section>`;
  syncDetailsState(true);
}

function buildHistoricalLayerCautionNote(layer) {
  return String(layer?.confidence || "unknown").toLowerCase() === "strong"
    ? "Curated historical context."
    : "Historical layer shown as a cautious orientation aid.";
}

async function loadHistoricalLayers(context = {}) {
  const module = await import("./mapService.js?v=20260729b");
  return module.loadHistoricalLayers(context);
}

function saveCurrentMapStudy() {}
function renderSavedMapStudies() { return ""; }
async function openSavedMapStudy() {}
function addCurrentMapNote() {}
function reset_map_view() {}
let selectedJourneyId = null;
let selectedJourneySegmentId = null;
function renderJourneySidebar() { return ""; }
function selectJourneyStop() {}
function loadSupplementalMapData() { return Promise.resolve({ journeys: [], mapLayers: [] }); }
// Compatibility call signatures retained for clients that use the map panel API.
// setRouteVisibility(true)
// setHistoricalLayerVisibility(result.item.id, true)
// setPoliticalContextLayerVisibility(result.item.id, true)

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
  if (window.BHFWorkspace && typeof window.BHFWorkspace.focusAskPanel === "function") {
    window.BHFWorkspace.focusAskPanel();
    return;
  }
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

async function handleMapPanelClick(event) {
  const target = event.target;
  if (!(target instanceof Element)) {
    return;
  }
  const button = target.closest("button, [role='button']");
  if (button?.matches("[data-map-modal-close]")) {
    closeMapModal();
    return;
  }
  if (button?.matches("[data-map-search-submit]")) {
    await runBrowseSearch();
    return;
  }
  if (button?.matches("[data-map-search-clear]")) {
    clearBrowseSearch();
    return;
  }
  if (button?.matches("[data-map-navigator-open]")) {
    const { navigator: navigatorPanel } = getPanelElements();
    setMobileNavigatorOpen(!navigatorPanel?.classList.contains("is-mobile-open"));
    return;
  }
  if (button?.matches("[data-map-navigator-close]")) {
    setMobileNavigatorOpen(false);
    return;
  }
  if (button?.matches("[data-map-details-open]")) {
    const { detailsColumn } = getPanelElements();
    setMobileDetailsOpen(!detailsColumn?.classList.contains("is-mobile-open"));
    return;
  }
  if (button?.matches("[data-map-details-close]")) {
    setMobileDetailsOpen(false);
    return;
  }
  if (button?.matches("[data-map-search-result-button]")) {
    const index = Number(button.getAttribute("data-search-index"));
    if (Number.isInteger(index) && index >= 0 && index < browseSearchResults.length) {
      setSelectedSearchResult(browseSearchResults[index]);
    }
    return;
  }
  const passageShortcut = target.closest("[data-passage-shortcut]");
  const openPassageButton = target.closest("[data-map-open-passage]");
  if (openPassageButton) {
    await openPassageReference(openPassageButton.getAttribute("data-map-open-passage"));
    return;
  }
  if (passageShortcut) {
    await submitRelatedPassageShortcut({
      book: passageShortcut.getAttribute("data-book") || "",
      chapter: passageShortcut.getAttribute("data-chapter") || "",
      verse_start: passageShortcut.getAttribute("data-verse-start") || "",
      verse_end: passageShortcut.getAttribute("data-verse-end") || "",
      reference: passageShortcut.getAttribute("data-reference") || "",
    });
  }
}

function wirePanelButtons() {
  if (mapPanelEventsWired) {
    return;
  }
  mapPanelEventsWired = true;
  document.addEventListener("click", (event) => {
    handleMapPanelClick(event).catch((error) => {
      setStatus(error.message || "Could not complete the map action.", "error");
    });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || !(event.target instanceof Element)) {
      return;
    }
    if (event.target.matches("[data-map-search-query]")) {
      event.preventDefault();
      runBrowseSearch().catch((error) => {
        setStatus(error.message || "Could not search the map catalog.", "error");
      });
    }
  });
  document.addEventListener("change", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }
    if (event.target.matches("[data-map-search-kind]")) {
      runBrowseSearch().catch((error) => {
        setStatus(error.message || "Could not search the map catalog.", "error");
      });
      return;
    }
    if (event.target.matches("[data-map-search-period], [data-historical-period]")) {
      setHistoricalPeriod(event.target.value).then(() => {
        if (event.target.matches("[data-map-search-period]") && mapMode === "browse") {
          return runBrowseSearch();
        }
        return undefined;
      }).catch((error) => {
        setStatus(error.message || "Could not update the map period.", "error");
      });
    }
  });
  const modal = getPanelElements().modal;
  modal?.addEventListener("close", finalizeMapModalClose);
  modal?.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeMapModal();
    }
  });
}

function initializeMapPanel() {
  wirePanelButtons();
  renderEmptyDetails("Select a place or route to inspect its details here.");
  syncHistoricalPeriod();
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
