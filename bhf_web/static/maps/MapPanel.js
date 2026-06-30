import { createBibleMap } from "./BibleMap.js";
import {
  loadArchaeologyForPassage,
  loadHistoricalLayers,
  invalidateMapCache,
  loadPlacesForPassage,
  loadManuscriptsForPassage,
  loadPoliticalContextForPassage,
  loadRoutesForPassage,
  loadSavedMapStudy,
  loadSavedMapStudies,
} from "./mapService.js";

let mapController = null;
let selectedMarker = null;
let selectedArchaeology = null;
let selectedManuscript = null;
let selectedRoute = null;
let selectedHistoricalLayer = null;
let selectedPoliticalContext = null;
let lastPassageContext = null;
let loadedMarkers = [];
let loadedArchaeologyMarkers = [];
let loadedManuscriptMarkers = [];
let loadedRoutes = [];
let loadedHistoricalLayers = [];
let loadedPoliticalContextLayers = [];
let loadedSavedMapStudies = [];
let historicalPeriod = "all";
let archaeologyVisible = false;
let manuscriptsVisible = false;
let mapModalOpen = false;
let lastModalTrigger = null;
const visibleHistoricalLayerIds = new Set();
const visiblePoliticalContextLayerIds = new Set();

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

async function loadMapData(context = {}) {
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
  if (context.savedMapStudy?.map_view_state?.historicalPeriod) {
    historicalPeriod = normalizeHistoricalPeriod(context.savedMapStudy.map_view_state.historicalPeriod);
  }
  if (context.savedMapStudy?.map_view_state && Object.prototype.hasOwnProperty.call(context.savedMapStudy.map_view_state, "archaeologyVisibility")) {
    archaeologyVisible = Boolean(context.savedMapStudy.map_view_state.archaeologyVisibility);
  }
  if (context.savedMapStudy?.map_view_state && Object.prototype.hasOwnProperty.call(context.savedMapStudy.map_view_state, "manuscriptVisibility")) {
    manuscriptsVisible = Boolean(context.savedMapStudy.map_view_state.manuscriptVisibility);
  }
  lastPassageContext = context;
  ensurePanelVisible(context);
  setPinHint("");
  setStatus("Loading map data...", "loading");
  renderEmptyDetails("Loading place, archaeology, manuscript, route, historical, and political context details...");

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
    renderSavedMapStudies();

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
  if (!lastPassageContext) {
    return;
  }

  try {
    setStatus("Loading historical layers...", "loading");
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
    renderSavedMapStudies();
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
  if (!routeToggle || !mapController) {
    return;
  }
  routeToggle.checked = mapController.getRouteVisibility();
}

function syncArchaeologyToggle() {
  const { archaeologyToggle } = getPanelElements();
  if (!archaeologyToggle || !mapController) {
    return;
  }
  archaeologyToggle.checked = mapController.getArchaeologyVisibility();
}

function syncManuscriptToggle() {
  const { manuscriptToggle } = getPanelElements();
  if (!manuscriptToggle || !mapController) {
    return;
  }
  manuscriptToggle.checked = mapController.getManuscriptVisibility();
}

function syncHistoricalLayerToggles() {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  const toggles = details.querySelectorAll("[data-historical-layer-toggle]");
  toggles.forEach((toggle) => {
    const layerId = String(toggle.getAttribute("data-layer-id") || "");
    if (!layerId) {
      return;
    }
    toggle.checked = visibleHistoricalLayerIds.has(layerId);
  });
}

function syncPoliticalContextLayerToggles() {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  const toggles = details.querySelectorAll("[data-political-context-toggle]");
  toggles.forEach((toggle) => {
    const layerId = String(toggle.getAttribute("data-layer-id") || "");
    if (!layerId) {
      return;
    }
    toggle.checked = visiblePoliticalContextLayerIds.has(layerId);
  });
}

function renderSelectedMarker(marker, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  const relatedPassages = marker.related_passages && Array.isArray(marker.related_passages.groups)
    ? marker.related_passages
    : null;
  const relatedVerses = Array.isArray(marker.related_references) ? marker.related_references : [];
  const confidenceLabel = prettyConfidence(marker.confidence);
  const caution = buildCautionNote(marker);
  const explanation = buildPlaceExplanation(marker, passageContext);
  const sourceText = buildSourceText(marker);
  const aliases = Array.isArray(marker.aliases) ? marker.aliases : [];
  const periods = formatPeriodList(marker.periods);

  details.innerHTML = `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(marker.name || "Unnamed place")}</h3>
          <div class="map-details-subtitle">${escapeHtml(marker.region || marker.ancient_region || "Unknown region")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(marker.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Aliases</h4>
        <p>${aliases.length ? aliases.map(escapeHtml).join(", ") : "No aliases in the local data."}</p>
      </section>

      <section class="map-detail-section">
        <h4>Periods</h4>
        <p>${escapeHtml(periods)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Modern location</h4>
        <p>${escapeHtml(marker.modern_location || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Ancient region</h4>
        <p>${escapeHtml(marker.ancient_region || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Related passages</h4>
        ${renderRelatedPassages(relatedPassages || relatedVerses)}
      </section>

      <section class="map-detail-section map-attribution">
        <h4>Attribution</h4>
        ${renderSourceAttribution(marker, sourceText)}
      </section>

      <section class="map-detail-section">
        <h4>Why this location matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Historical / Geographical context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("place", marker)}
      ${renderHistoricalLayerOverview()}
    </div>
  `;
}

function renderSelectedArchaeology(marker, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  const scriptureLinks = Array.isArray(marker.scripture_links) ? marker.scripture_links : [];
  const confidenceLabel = prettyConfidence(marker.confidence);
  const caution = buildArchaeologyCautionNote(marker);
  const explanation = buildArchaeologyExplanation(marker, passageContext);
  const sourceText = buildSourceText(marker);

  details.innerHTML = `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(marker.name || "Unnamed archaeology item")}</h3>
          <div class="map-details-subtitle">${escapeHtml(marker.site_name || marker.location || "Unknown location")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(marker.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Type</h4>
        <p>${escapeHtml(marker.item_type || "Archaeology item")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Period</h4>
        <p>${escapeHtml(marker.period || "Unknown period")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Location</h4>
        <p>${escapeHtml(marker.location || marker.site_name || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Related passages</h4>
        ${renderRelatedVerses(scriptureLinks)}
      </section>

      <section class="map-detail-section">
        <h4>Relationship</h4>
        <p>${escapeHtml(marker.relationship || "No relationship text recorded in the local data.")}</p>
      </section>

      <section class="map-detail-section map-attribution">
        <h4>Attribution</h4>
        ${renderSourceAttribution(marker, sourceText)}
      </section>

      <section class="map-detail-section">
        <h4>Why this matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Historical / Archaeological context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("archaeology", marker)}
      ${renderArchaeologyLayerOverview()}
    </div>
  `;
}

function renderSelectedManuscript(marker, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  const scriptureLinks = Array.isArray(marker.scripture_links) ? marker.scripture_links : [];
  const confidenceLabel = prettyConfidence(marker.confidence);
  const caution = buildManuscriptCautionNote(marker);
  const explanation = buildManuscriptExplanation(marker, passageContext);
  const sourceText = buildSourceText(marker);
  const relatedBooks = Array.isArray(marker.related_books) ? marker.related_books : [];

  details.innerHTML = `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(marker.name || "Unnamed manuscript")}</h3>
          <div class="map-details-subtitle">${escapeHtml(marker.discovery_location || marker.current_location || "Unknown location")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(marker.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Type</h4>
        <p>${escapeHtml(marker.manuscript_type || "Manuscript")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Language</h4>
        <p>${escapeHtml(marker.language || "Unknown language")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Date</h4>
        <p>${escapeHtml(marker.date || "Unknown date")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Material</h4>
        <p>${escapeHtml(marker.material || "Unknown material")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Discovery location</h4>
        <p>${escapeHtml(marker.discovery_location || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Current location</h4>
        <p>${escapeHtml(marker.current_location || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Related books</h4>
        <p>${relatedBooks.length ? relatedBooks.map(escapeHtml).join(", ") : "No related books recorded."}</p>
      </section>

      <section class="map-detail-section">
        <h4>Related passages</h4>
        ${renderRelatedVerses(scriptureLinks)}
      </section>

      <section class="map-detail-section">
        <h4>Significance</h4>
        <p>${escapeHtml(marker.significance || "No significance text recorded.")}</p>
      </section>

      <section class="map-detail-section map-attribution compact">
        <h4>Attribution</h4>
        ${renderSourceAttribution(marker, sourceText)}
      </section>

      <section class="map-detail-section">
        <h4>Why this matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Textual / Historical context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution compact">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("manuscript", marker)}
      ${renderManuscriptLayerOverview()}
    </div>
  `;
}

function renderSelectedRoute(route, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  const scriptureLinks = Array.isArray(route.scripture_links) ? route.scripture_links : [];
  const confidenceLabel = prettyConfidence(route.confidence);
  const caution = buildRouteCautionNote(route);
  const explanation = buildRouteExplanation(route, passageContext);
  const sourceText = buildSourceText(route);

  details.innerHTML = `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(route.name || "Unnamed route")}</h3>
          <div class="map-details-subtitle">${escapeHtml(route.period || "Unknown period")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(route.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Route type</h4>
        <p>${escapeHtml(route.route_type || "Route")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Related verses</h4>
        ${renderRelatedVerses(scriptureLinks)}
      </section>

      <section class="map-detail-section map-attribution compact">
        <h4>Attribution</h4>
        ${renderSourceAttribution(route, sourceText)}
      </section>

      <section class="map-detail-section">
        <h4>Why this route matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Historical / Geographical context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution compact">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("route", route)}
      ${renderHistoricalLayerOverview()}
    </div>
  `;
}

function renderSelectedHistoricalLayer(layer, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  const confidenceLabel = prettyConfidence(layer.confidence);
  const caution = buildHistoricalLayerCautionNote(layer);
  const explanation = buildHistoricalLayerExplanation(layer, passageContext);
  const sourceText = buildSourceText(layer);

  details.innerHTML = `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(layer.name || "Unnamed layer")}</h3>
          <div class="map-details-subtitle">${escapeHtml(layer.period || "Unknown period")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(layer.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Layer type</h4>
        <p>${escapeHtml(layer.layer_type || "Layer")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Description</h4>
        <p>${escapeHtml(layer.description || "No description available.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Source</h4>
        <p>${escapeHtml(sourceText)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Why this layer matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Historical / Geographical context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("layer", layer)}
      ${renderHistoricalLayerOverview()}
    </div>
  `;
}

function renderSelectedPoliticalContext(layer, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  const confidenceLabel = prettyConfidence(layer.confidence);
  const caution = buildPoliticalContextCautionNote(layer);
  const explanation = buildPoliticalContextExplanation(layer, passageContext);
  const sourceText = buildSourceText(layer);

  details.innerHTML = `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(layer.name || "Unnamed political context")}</h3>
          <div class="map-details-subtitle">${escapeHtml(layer.entity_type || layer.period || "Unknown period")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(layer.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Summary</h4>
        <p>${escapeHtml(layer.summary || "No summary available.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Period</h4>
        <p>${escapeHtml(formatPeriodList(layer.periods))}</p>
      </section>

      <section class="map-detail-section">
        <h4>Passage links</h4>
        ${renderRelatedVerses(Array.isArray(layer.scripture_links) ? layer.scripture_links : [])}
      </section>

      <section class="map-detail-section">
        <h4>Source</h4>
        <p>${escapeHtml(sourceText)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Why this matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Political context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("political_context", layer)}
      ${renderPoliticalContextLayerOverview()}
    </div>
  `;
}

function renderHistoricalLayerOverview() {
  const layers = Array.isArray(loadedHistoricalLayers) ? loadedHistoricalLayers : [];
  const visibleCount = layers.filter((layer) => visibleHistoricalLayerIds.has(layer.id)).length;
  const items = layers
    .map((layer) => {
      const checked = visibleHistoricalLayerIds.has(layer.id) ? "checked" : "";
      return `
        <label class="map-layer-toggle">
          <input
            type="checkbox"
            data-historical-layer-toggle
            data-layer-id="${escapeHtml(layer.id)}"
            ${checked}
          >
          <span>
            <strong>${escapeHtml(layer.name || "Unnamed layer")}</strong>
            <span>${escapeHtml(layer.period || "Unknown period")} · ${escapeHtml(prettyConfidence(layer.confidence))}</span>
          </span>
        </label>
      `;
    })
    .join("");

  return `
    <section class="map-detail-section map-layer-section">
      <div class="map-section-header">
        <h4>Historical layers</h4>
        <span>${visibleCount}/${layers.length} shown</span>
      </div>
      ${
        layers.length
          ? `<div class="map-layer-list">${items}</div>`
          : `<p class="empty map-details-empty">No historical layers match the selected period.</p>`
      }
      <p class="map-layer-note">These borders are broad study overlays. Use them to understand the setting and period, not as exact boundary claims.</p>
    </section>
  `;
}

function renderPoliticalContextLayerOverview() {
  const layers = Array.isArray(loadedPoliticalContextLayers) ? loadedPoliticalContextLayers : [];
  const visibleCount = layers.filter((layer) => visiblePoliticalContextLayerIds.has(layer.id)).length;
  const items = layers
    .map((layer) => {
      const checked = visiblePoliticalContextLayerIds.has(layer.id) ? "checked" : "";
      return `
        <label class="map-layer-toggle">
          <input
            type="checkbox"
            data-political-context-toggle
            data-layer-id="${escapeHtml(layer.id)}"
            ${checked}
          >
          <span>
            <strong>${escapeHtml(layer.name || "Unnamed context")}</strong>
            <span>${escapeHtml(layer.entity_type || layer.period || "Unknown period")} · ${escapeHtml(prettyConfidence(layer.confidence))}</span>
          </span>
        </label>
      `;
    })
    .join("");

  return `
    <section class="map-detail-section map-layer-section">
      <div class="map-section-header">
        <h4>Political context</h4>
        <span>${visibleCount}/${layers.length} shown</span>
      </div>
      ${
        layers.length
          ? `<div class="map-layer-list">${items}</div>`
          : `<p class="empty map-details-empty">No political context layers match the selected period.</p>`
      }
      <p class="map-layer-note">These overlays explain the larger world behind the passage. They are intentionally broad and may represent a region or empire rather than one exact place.</p>
    </section>
  `;
}

function renderArchaeologyLayerOverview() {
  const markers = Array.isArray(loadedArchaeologyMarkers) ? loadedArchaeologyMarkers : [];
  const visibleCount = archaeologyVisible ? markers.length : 0;
  const items = markers
    .map((marker) => {
      return `
        <label class="map-layer-toggle">
          <input type="radio" name="archaeology-item" value="${escapeHtml(marker.id)}" disabled>
          <span>
            <strong>${escapeHtml(marker.name || "Unnamed item")}</strong>
            <span>${escapeHtml(marker.site_name || marker.location || "Unknown location")} · ${escapeHtml(prettyConfidence(marker.confidence))}</span>
          </span>
        </label>
      `;
    })
    .join("");

  return `
    <section class="map-detail-section map-layer-section">
      <div class="map-section-header">
        <h4>Archaeology layer</h4>
        <span>${visibleCount}/${markers.length} shown</span>
      </div>
      ${
        markers.length
          ? `<div class="map-layer-list">${items}</div>`
          : `<p class="empty map-details-empty">No curated archaeology items are stored for this passage right now.</p>`
      }
      <p class="map-layer-note">Archaeology items are optional study aids. They can add historical texture, but they do not prove one interpretation by themselves.</p>
    </section>
  `;
}

function renderManuscriptLayerOverview() {
  const markers = Array.isArray(loadedManuscriptMarkers) ? loadedManuscriptMarkers : [];
  const visibleCount = manuscriptsVisible ? markers.length : 0;
  const items = markers
    .map((marker) => {
      return `
        <label class="map-layer-toggle">
          <input type="radio" name="manuscript-item" value="${escapeHtml(marker.id)}" disabled>
          <span>
            <strong>${escapeHtml(marker.name || "Unnamed manuscript")}</strong>
            <span>${escapeHtml(marker.discovery_location || marker.current_location || "Unknown location")} · ${escapeHtml(prettyConfidence(marker.confidence))}</span>
          </span>
        </label>
      `;
    })
    .join("");

  return `
    <section class="map-detail-section map-layer-section">
      <div class="map-section-header">
        <h4>Manuscript layer</h4>
        <span>${visibleCount}/${markers.length} shown</span>
      </div>
      ${
        markers.length
          ? `<div class="map-layer-list">${items}</div>`
          : `<p class="empty map-details-empty">No curated manuscript items are stored for this passage right now.</p>`
      }
      <p class="map-layer-note">Manuscripts are textual witnesses, not archaeology finds. Locations are shown cautiously when the local record includes them.</p>
    </section>
  `;
}

function getCurrentMapSelection() {
  if (selectedMarker) {
    return {
      kind: "place",
      item: selectedMarker,
    };
  }
  if (selectedArchaeology) {
    return {
      kind: "archaeology",
      item: selectedArchaeology,
    };
  }
  if (selectedManuscript) {
    return {
      kind: "manuscript",
      item: selectedManuscript,
    };
  }
  if (selectedRoute) {
    return {
      kind: "route",
      item: selectedRoute,
    };
  }
  if (selectedHistoricalLayer) {
    return {
      kind: "layer",
      item: selectedHistoricalLayer,
    };
  }
  if (selectedPoliticalContext) {
    return {
      kind: "political_context",
      item: selectedPoliticalContext,
    };
  }
  return null;
}

function buildCurrentMapStudyPayload() {
  const context = lastPassageContext || {};
  const selection = getCurrentMapSelection();
  const mapViewState = mapController?.getViewState ? mapController.getViewState() : {};
  const selectedLayers = [
    ...(mapController?.getHistoricalLayerIds ? mapController.getHistoricalLayerIds() : Array.from(visibleHistoricalLayerIds)),
    ...(mapController?.getPoliticalContextLayerIds
      ? mapController.getPoliticalContextLayerIds()
      : Array.from(visiblePoliticalContextLayerIds)),
  ];

  return {
    book: context.book,
    chapter: context.chapter,
    start_verse: context.verseStart || context.startVerse,
    end_verse: context.verseEnd || context.endVerse || context.verseStart || context.startVerse,
    passage_reference: formatReference(context),
    selected_place_id: selection?.kind === "place" ? selection.item.id : "",
    selected_archaeology_id: selection?.kind === "archaeology" ? selection.item.id : "",
    selected_manuscript_id: selection?.kind === "manuscript" ? selection.item.id : "",
    selected_route_id: selection?.kind === "route" ? selection.item.id : "",
    selected_layer_id:
      selection?.kind === "layer" || selection?.kind === "political_context" ? selection.item.id : "",
    selected_place_name: selection?.kind === "place" ? selection.item.name : "",
    selected_archaeology_name: selection?.kind === "archaeology" ? selection.item.name : "",
    selected_manuscript_name: selection?.kind === "manuscript" ? selection.item.name : "",
    selected_route_name: selection?.kind === "route" ? selection.item.name : "",
    selected_layer_name:
      selection?.kind === "layer" || selection?.kind === "political_context" ? selection.item.name : "",
    modern_location: selection?.kind === "place" ? selection.item.modern_location : "",
    ancient_region: selection?.kind === "place" ? selection.item.ancient_region : "",
    archaeology_location: selection?.kind === "archaeology" ? selection.item.location : "",
    confidence: selection?.item?.confidence || "",
    description: selection?.item?.description || "",
    period:
      selection?.kind === "layer" || selection?.kind === "political_context"
        ? selection.item.period
        : selection?.kind === "route"
          ? selection.item.period
          : selection?.kind === "archaeology"
            ? selection.item.period
            : selection?.kind === "manuscript"
              ? selection.item.period
            : "",
    selected_layers: Array.from(new Set(selectedLayers)),
    map_view_state: {
      ...mapViewState,
      historicalPeriod,
    },
    generated_summary: buildMapStudySummary(selection, context),
    user_notes: "",
  };
}

function buildMapStudySummary(selection, context) {
  const reference = formatReference(context) || "the selected passage";
  if (!selection) {
    return `Map study for ${reference}.`;
  }
  const item = selection.item;
  const name = item.name || "Unnamed item";
  if (selection.kind === "route") {
    return `${name} in ${reference} with route confidence ${prettyConfidence(item.confidence)}.`;
  }
  if (selection.kind === "archaeology") {
    return `${name} in ${reference} as an archaeology witness with confidence ${prettyConfidence(item.confidence)}.`;
  }
  if (selection.kind === "manuscript") {
    return `${name} in ${reference} as a textual witness with confidence ${prettyConfidence(item.confidence)}.`;
  }
  if (selection.kind === "layer") {
    return `${name} in ${reference} as a ${item.period || "historical"} study layer.`;
  }
  if (selection.kind === "political_context") {
    return `${name} in ${reference} as a ${item.entity_type || "political"} context layer.`;
  }
  return `${name} in ${reference} with confidence ${prettyConfidence(item.confidence)}.`;
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
    ...buildCurrentMapStudyPayload(),
    user_notes: notes.trim(),
  };
  const response = await fetch("/api/map-studies", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    window.alert(data.error || "Could not save map study.");
    return;
  }
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
    ...buildCurrentMapStudyPayload(),
    note_body: noteBody.trim(),
    place_id: selection.kind === "place" ? selection.item.id : "",
    archaeology_id: selection.kind === "archaeology" ? selection.item.id : "",
    manuscript_id: selection.kind === "manuscript" ? selection.item.id : "",
    route_id: selection.kind === "route" ? selection.item.id : "",
    layer_id: selection.kind === "layer" ? selection.item.id : "",
  };
  const response = await fetch("/api/map-notes", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    window.alert(data.error || "Could not save map note.");
    return;
  }
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
  submitMapStudyQuestion(buildCurrentMapStudyPayload());
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
  submitMapStudyQuestion(buildCurrentMapStudyPayload());
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
  setStudyMapContext(buildCurrentMapStudyPayload());
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
  if (!lastPassageContext) {
    return;
  }
  const response = await loadSavedMapStudies(lastPassageContext);
  loadedSavedMapStudies = response.saved_map_studies || [];
  renderSavedMapStudies();
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
  const response = await fetch(`/api/map-studies/${encodeURIComponent(studyId)}`, {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    const data = await response.json();
    window.alert(data.error || "Could not delete saved map study.");
    return;
  }
  invalidateMapCache("/api/map-studies");
  await refreshSavedMapStudies();
}

function renderMapOrientationCard(options = {}) {
  const {
    title = "How to read this map",
    summary = "This workspace combines exact place pins with broader study overlays. Some passages match a city or site. Others only match a region, empire, route, or historical frame.",
    callout = "",
  } = options;
  const calloutMarkup = callout
    ? `<p class="map-orientation-callout">${escapeHtml(callout)}</p>`
    : "";
  return `
    <section class="map-detail-section map-orientation-card">
      <div class="map-section-header map-section-header-stack">
        <h4>${escapeHtml(title)}</h4>
        <p class="map-orientation-summary">${escapeHtml(summary)}</p>
      </div>
      ${calloutMarkup}
      <div class="map-orientation-list">
        <div class="map-orientation-item">
          <strong>Place pins</strong>
          <p>Use these when the passage matches a curated location with coordinates.</p>
        </div>
        <div class="map-orientation-item">
          <strong>Historical and political layers</strong>
          <p>Use these when the passage is better understood as a region, kingdom, empire, or broad time-setting rather than one pin.</p>
        </div>
        <div class="map-orientation-item">
          <strong>Routes, archaeology, and manuscripts</strong>
          <p>These are optional study layers. Some passages have them; many do not.</p>
        </div>
      </div>
      <div class="map-next-steps">
        <strong>What to do next</strong>
        <p>Click a marker or overlay, toggle layers on the right, or use Expand for a larger map. If no local map data exists, BHF can still show a text-only geography fallback below.</p>
      </div>
    </section>
  `;
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

function renderSavedMapStudies() {
  const { savedMapStudiesList, savedMapStudiesCount } = getPanelElements();
  if (!savedMapStudiesList) {
    return;
  }
  const studies = Array.isArray(loadedSavedMapStudies) ? loadedSavedMapStudies : [];
  if (savedMapStudiesCount) {
    savedMapStudiesCount.textContent = String(studies.length);
  }
  if (!studies.length) {
    savedMapStudiesList.innerHTML = `<p class="empty">No saved map studies for this passage yet.</p>`;
    return;
  }
  savedMapStudiesList.innerHTML = "";
  for (const study of studies) {
    const article = document.createElement("article");
    article.className = "saved-map-study";
    article.dataset.savedMapStudyId = study.id;

    const title = document.createElement("h4");
    title.textContent = study.passage_reference || formatStudyReference(study);

    const meta = document.createElement("p");
    meta.className = "saved-study-meta";
    meta.textContent = [
      study.selected_place_id ? `Place: ${study.selected_place_id}` : null,
      study.selected_archaeology_id ? `Archaeology: ${study.selected_archaeology_id}` : null,
      study.selected_manuscript_id ? `Manuscript: ${study.selected_manuscript_id}` : null,
      study.selected_route_id ? `Route: ${study.selected_route_id}` : null,
      study.selected_layer_id ? `Layer: ${study.selected_layer_id}` : null,
    ].filter(Boolean).join(" · ") || "Map study";

    const summary = document.createElement("p");
    summary.textContent = study.generated_summary || "Saved map state";

    const actions = document.createElement("div");
    actions.className = "note-actions";

    const open = document.createElement("button");
    open.type = "button";
    open.className = "secondary";
    open.textContent = "Open";
    open.addEventListener("click", () => openSavedMapStudy(study.id));

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "secondary danger";
    remove.textContent = "Delete";
    remove.addEventListener("click", () => deleteSavedMapStudy(study.id));

    actions.appendChild(open);
    actions.appendChild(remove);
    article.appendChild(title);
    article.appendChild(meta);
    article.appendChild(summary);
    article.appendChild(actions);
    savedMapStudiesList.appendChild(article);
  }
}

function formatStudyReference(study) {
  if (!study) {
    return "";
  }
  if (!study.start_verse) {
    return `${study.book} ${study.chapter}`;
  }
  const suffix = Number(study.start_verse) === Number(study.end_verse)
    ? String(study.start_verse)
    : `${study.start_verse}-${study.end_verse}`;
  return `${study.book} ${study.chapter}:${suffix}`;
}

function buildPlaceExplanation(marker, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = marker.name || "This place";
  const region = marker.ancient_region || marker.region || "the ancient setting";
  return {
    why: `${name}${passagePhrase} helps orient the reader in the biblical story and keeps the geography concrete without overclaiming what the text does not say.`,
    context: `${name} sits in ${region}. The local data connects it to the passage through curated references, and the marker should be read as historical context rather than proof of interpretation.`,
  };
}

function buildRouteExplanation(route, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = route.name || "This route";
  const period = route.period || "the relevant biblical period";
  return {
    why: `${name}${passagePhrase} helps trace movement through ${period} and clarifies the narrative geography without locking the entire story into a single exact path.`,
    context: `The route is stored as curated GeoJSON. It is intended to show movement pattern and approximate waypoints, not a GPS-precise reconstruction.`,
  };
}

function buildHistoricalLayerExplanation(layer, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = layer.name || "This layer";
  const period = layer.period || "the relevant historical period";
  return {
    why: `${name}${passagePhrase} helps situate the passage in ${period} and gives the reader a broad political-geographic frame without pretending the borders are exact.`,
    context: `The overlay is a curated GeoJSON study layer. Its boundaries are schematic and should be treated as a historical orientation aid, not a precise political reconstruction.`,
  };
}

function buildPoliticalContextExplanation(layer, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = layer.name || "This political context";
  const entityType = layer.entity_type || "political background";
  return {
    why: `${name}${passagePhrase} helps locate the passage within the larger ${entityType} that shaped the world of the text.`,
    context: `The layer is a curated schematic overlay. It highlights dominant political background, not exact borders or a single fixed date.`,
  };
}

function buildArchaeologyExplanation(marker, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = marker.name || "This archaeology item";
  const location = marker.location || marker.site_name || "its discovery context";
  return {
    why: `${name}${passagePhrase} helps anchor the passage in a concrete historical setting at ${location}, while still leaving room for uncertainty where the evidence is debated.`,
    context: `The item is stored as curated local archaeology data. It should be read as a historical witness with a specific genre and confidence level, not as a flattening of the text's meaning.`,
  };
}

function buildManuscriptExplanation(marker, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = marker.name || "This manuscript";
  const discoveryLocation = marker.discovery_location || marker.current_location || "a known repository";
  return {
    why: `${name}${passagePhrase} helps anchor textual transmission in a concrete witness from ${discoveryLocation}, which is useful when comparing wording without treating any one manuscript as the final word.`,
    context: `The manuscript is curated as a textual witness separate from archaeology. Its value comes from the transmission history it represents, not from proving the passage by itself.`,
  };
}

function buildCautionNote(marker) {
  const confidence = String(marker.confidence || "unknown").toLowerCase();
  if (confidence === "strong" || confidence === "likely") {
    return "This is a curated local identification with a clear map coordinate, but it still functions as historical background rather than proof of the passage's meaning.";
  }
  if (confidence === "possible") {
    return "This location is possible, not certain. Treat the marker as a cautious guide to a debated or approximate identification.";
  }
  if (confidence === "disputed") {
    return "This location is disputed in the literature. Use it only as a debated reference point, not as settled geography.";
  }
  return "The location data is incomplete or uncertain. The app shows it only as a cautious reference point.";
}

function buildManuscriptCautionNote(marker) {
  const confidence = String(marker.confidence || "unknown").toLowerCase();
  if (confidence === "strong" || confidence === "likely") {
    return "This is a curated textual witness with a clear local record, but it should still be read as one witness in a larger transmission history.";
  }
  if (confidence === "possible") {
    return "This manuscript witness is approximate or partly uncertain. Treat the location and transmission notes cautiously.";
  }
  if (confidence === "disputed") {
    return "This manuscript witness is disputed or unevenly documented. Use it only as a cautious historical reference.";
  }
  return "The manuscript data is uncertain. Read it as a cautious textual witness only.";
}

function buildPoliticalContextCautionNote(layer) {
  const confidence = String(layer.confidence || "unknown").toLowerCase();
  if (confidence === "strong" || confidence === "likely") {
    return "This is a curated political-context layer. It is meant to orient the reader, not to settle border debates or compress historical change into one snapshot.";
  }
  if (confidence === "possible") {
    return "This political-context layer is broad and approximate. Treat it as a study guide, not a precise boundary map.";
  }
  if (confidence === "disputed") {
    return "This political-context layer is disputed or heavily simplified. Use it only as a cautious background frame.";
  }
  return "The political-context data is uncertain. Read it as a cautious historical backdrop only.";
}

function buildRouteCautionNote(route) {
  const confidence = String(route.confidence || "unknown").toLowerCase();
  if (confidence === "strong" || confidence === "likely") {
    return "This route is a curated approximation. It should be read as a study overlay, not as a claim that every segment is certain.";
  }
  if (confidence === "possible") {
    return "This route is approximate and partly debated. The overlay marks a plausible path, not a settled reconstruction.";
  }
  if (confidence === "disputed") {
    return "This route is disputed in the literature. Use it as a debated heuristic only.";
  }
  return "The route geometry is uncertain. The overlay should be read cautiously.";
}

function buildHistoricalLayerCautionNote(layer) {
  const confidence = String(layer.confidence || "unknown").toLowerCase();
  if (confidence === "strong" || confidence === "likely") {
    return "This is a broad study overlay. It is useful for orientation, but the exact borders remained fluid and should not be read too literally.";
  }
  if (confidence === "possible") {
    return "This overlay is approximate and intentionally broad. It helps with study context, not precise boundary claims.";
  }
  if (confidence === "disputed") {
    return "This overlay is disputed or heavily debated. Use it only as a cautious historical guide.";
  }
  return "The boundary data is uncertain. Read the overlay as a cautious background layer only.";
}

function buildArchaeologyCautionNote(marker) {
  const confidence = String(marker.confidence || "unknown").toLowerCase();
  if (confidence === "strong" || confidence === "likely") {
    return "This is a curated archaeology witness with a clear local data source, but it still functions as historical background rather than direct proof of interpretation.";
  }
  if (confidence === "possible") {
    return "This archaeology item is approximate or debated. Treat it as a study aid, not a settled identification.";
  }
  if (confidence === "disputed") {
    return "This archaeology item is disputed. Use it only as a debated historical reference point.";
  }
  return "The archaeology data is uncertain. Read it cautiously and avoid overclaiming what it proves.";
}

function renderMapActionBar(kind, item) {
  const selectedLabel = prettyConfidence(item.confidence || "unknown");
  const primaryLabel =
    kind === "archaeology"
      ? "Ask about this item"
      : kind === "political_context"
        ? "Ask about this context"
        : "Ask about this location";
  return `
    <section class="map-detail-section map-action-section">
      <div class="map-action-buttons">
        <button type="button" class="secondary" data-map-action="ask_location">${escapeHtml(primaryLabel)}</button>
        <button type="button" class="secondary" data-map-action="save_map_study">Save map study</button>
        <button type="button" class="secondary" data-map-action="map_note">Add map note</button>
        <button type="button" class="secondary" data-map-action="compare_archaeology">Compare with archaeology</button>
        <button type="button" class="secondary" data-map-action="related_passages">View related passages</button>
        <button type="button" class="secondary" data-map-action="reset_map_view">Reset map view</button>
        ${
          kind === "layer" || kind === "archaeology" || kind === "political_context" || kind === "manuscript"
            ? ""
            : '<button type="button" class="secondary" data-map-action="view_historical_layer">View historical layer</button>'
        }
      </div>
      <p class="map-layer-note">Selected ${escapeHtml(kind)} confidence: ${escapeHtml(selectedLabel)}. These actions use the local curated map record for the current selection.</p>
    </section>
  `;
}

function buildSourceText(item) {
  const source = item?.source || {};
  const sourceName = source.label || item.source_name || "No source recorded";
  const sourceUrl = source.url || item.source_url || "";
  const license = source.license || item.license || "";
  const parts = [sourceName];
  if (sourceUrl) {
    parts.push(sourceUrl);
  }
  if (license) {
    parts.push(`License: ${license}`);
  }
  return parts.join(" · ");
}

function renderSourceAttribution(item, sourceText) {
  const source = item?.source || {};
  const sourceId = source.id || item.source_id || "";
  const sourceLink = sourceId ? `<a href="/sources/${encodeURIComponent(sourceId)}">Open source record</a>` : "No source record";
  const warning = sourceId ? "" : '<p class="map-source-warning">Missing source metadata in the local registry.</p>';
  const url = source.url || item.source_url || "";
  const license = source.license || item.license || "";
  return `
    <p class="map-attribution-source">${escapeHtml(sourceText)}</p>
    ${url ? `<p class="map-attribution-url">${escapeHtml(url)}</p>` : ""}
    ${license ? `<p class="map-attribution-license">${escapeHtml(license)}</p>` : ""}
    <p class="map-attribution-link">${sourceLink}</p>
    ${warning}
  `;
}

function prettyConfidence(value) {
  const normalized = String(value || "unknown").toLowerCase();
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function formatPeriodList(periods) {
  if (!Array.isArray(periods) || periods.length === 0) {
    return "Unknown period";
  }
  return periods.join(" · ");
}

function renderRelatedVerses(references) {
  if (!references.length) {
    return "<p>No curated related verses are stored for this item.</p>";
  }
  const items = references
    .map((reference) => {
      const verseRange =
        Number(reference.verse_start) === Number(reference.verse_end)
          ? String(reference.verse_start)
          : `${reference.verse_start}-${reference.verse_end}`;
      return `
        <li class="map-related-item">
          <strong>${escapeHtml(reference.book)} ${escapeHtml(String(reference.chapter))}:${escapeHtml(verseRange)}</strong>
          <span>${escapeHtml(reference.relationship_type)}</span>
          <p>${escapeHtml(reference.notes || "")}</p>
          <button
            type="button"
            class="secondary map-shortcut"
            data-passage-shortcut
            data-book="${escapeHtml(reference.book || "")}"
            data-chapter="${escapeHtml(String(reference.chapter || ""))}"
            data-verse-start="${escapeHtml(String(reference.verse_start || ""))}"
            data-verse-end="${escapeHtml(String(reference.verse_end || ""))}"
            data-reference="${escapeHtml(reference.reference || `${reference.book || ""} ${reference.chapter || ""}:${verseRange}`)}"
          >Ask about this passage</button>
        </li>
      `;
    })
    .join("");
  return `<ul class="map-related-verses">${items}</ul>`;
}

function renderRelatedPassages(relatedPassages) {
  if (Array.isArray(relatedPassages)) {
    return renderRelatedVerses(relatedPassages);
  }
  const groups = Array.isArray(relatedPassages?.groups) ? relatedPassages.groups : [];
  if (!groups.length) {
    return "<p>No curated related passages are stored for this place.</p>";
  }
  const totalCount = Number(relatedPassages?.count || 0);
  const sections = groups
    .map((group) => {
      const testamentGroups = Array.isArray(group.testament_groups) ? group.testament_groups : [];
      const passageCount = Array.isArray(group.passages) ? group.passages.length : 0;
      const groupItems = testamentGroups.length
        ? testamentGroups
            .map((testamentGroup) => {
              const groupPassages = Array.isArray(testamentGroup.passages) ? testamentGroup.passages : [];
              return `
                <section class="map-related-group">
                  <h5>${escapeHtml(testamentGroup.label || "Location links")}</h5>
                  ${renderRelatedPassagesList(groupPassages)}
                </section>
              `;
            })
            .join("")
        : renderRelatedPassagesList(Array.isArray(group.passages) ? group.passages : []);
      return `
        <article class="map-related-passages-group">
          <h5>${escapeHtml(group.label || "Related passages")}</h5>
          <p class="map-related-group-summary">${escapeHtml(group.summary || "")}</p>
          ${groupItems}
          <p class="map-related-group-count">${escapeHtml(String(passageCount))} passage${passageCount === 1 ? "" : "s"}</p>
        </article>
      `;
    })
    .join("");
  return `
    <div class="map-related-passages">
      <p class="map-related-passages-total">${escapeHtml(String(totalCount))} curated passage${totalCount === 1 ? "" : "s"} linked to this place.</p>
      ${sections}
    </div>
  `;
}

function renderRelatedPassagesList(passages) {
  if (!Array.isArray(passages) || passages.length === 0) {
    return "<p class=\"empty\">No curated passages in this group.</p>";
  }
  const items = passages
    .map((passage) => {
      const source = passage.source || {};
      const sourceParts = [
        source.name ? escapeHtml(source.name) : null,
        source.label ? escapeHtml(source.label) : null,
      ].filter(Boolean);
      const sourceText = sourceParts.length ? sourceParts.join(" · ") : "Curated local data";
      return `
        <li class="map-related-item">
          <strong>${escapeHtml(passage.reference || "")}</strong>
          <span>${escapeHtml(passage.relationship_label || passage.relationship_type || "")}</span>
          <p>${escapeHtml(passage.notes || "")}</p>
          <p class="map-related-source">${sourceText}</p>
          <button
            type="button"
            class="secondary map-shortcut"
            data-passage-shortcut
            data-book="${escapeHtml(passage.book || "")}"
            data-chapter="${escapeHtml(String(passage.chapter || ""))}"
            data-verse-start="${escapeHtml(String(passage.verse_start || ""))}"
            data-verse-end="${escapeHtml(String(passage.verse_end || ""))}"
            data-reference="${escapeHtml(passage.reference || "")}"
          >Ask about this passage</button>
        </li>
      `;
    })
    .join("");
  return `<ul class="map-related-verses">${items}</ul>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeHistoricalPeriod(value) {
  const normalized = String(value || "all").trim();
  if (!normalized || normalized.toLowerCase() === "all") {
    return "all";
  }
  const aliases = {
    "New Testament / Roman period": "NT / Roman period",
    "new testament / roman period": "NT / Roman period",
    "Broad / uncertain": "Broad / uncertain period",
    "broad / uncertain period": "Broad / uncertain period",
    "uncertain / broad period": "Broad / uncertain period",
  };
  const canonical = aliases[normalized] || normalized;
  return HISTORICAL_PERIOD_OPTIONS.some((option) => option.value === canonical) ? canonical : "all";
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
  const archaeologyToggle = document.querySelector("[data-archaeology-toggle]");
  const manuscriptToggle = document.querySelector("[data-manuscript-toggle]");
  const routeToggle = document.querySelector("[data-route-toggle]");
  const historicalPeriodSelect = document.querySelector("[data-historical-period]");
  const { modal } = getPanelElements();
  const details = document.querySelector("#map-details");

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
