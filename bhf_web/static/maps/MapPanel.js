import { createBibleMap } from "./BibleMap.js";
import {
  loadArchaeologyForPassage,
  loadHistoricalLayers,
  loadPlacesForPassage,
  loadRoutesForPassage,
  loadSavedMapStudy,
  loadSavedMapStudies,
} from "./mapService.js";

let mapController = null;
let selectedMarker = null;
let selectedArchaeology = null;
let selectedRoute = null;
let selectedHistoricalLayer = null;
let lastPassageContext = null;
let loadedMarkers = [];
let loadedArchaeologyMarkers = [];
let loadedRoutes = [];
let loadedHistoricalLayers = [];
let loadedSavedMapStudies = [];
let historicalPeriod = "all";
let archaeologyVisible = false;
const visibleHistoricalLayerIds = new Set();

const HISTORICAL_PERIOD_OPTIONS = [
  { value: "all", label: "All periods" },
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
    stage: document.querySelector("#map-stage"),
    reference: document.querySelector("#map-panel-reference"),
    details: document.querySelector("#map-details"),
    savedMapStudiesList: document.querySelector("#saved-map-studies-list"),
    savedMapStudiesCount: document.querySelector("#saved-map-studies-count"),
    archaeologyToggle: document.querySelector("[data-archaeology-toggle]"),
    routeToggle: document.querySelector("[data-route-toggle]"),
    historicalPeriod: document.querySelector("[data-historical-period]"),
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

function ensurePanelVisible(context) {
  const { panel, reference } = getPanelElements();
  if (!panel) {
    throw new Error("Map panel is missing.");
  }
  panel.hidden = false;
  if (reference) {
    reference.textContent = formatReference(context);
  }
}

function ensureMapController(markers, archaeologyMarkers, routes, historicalLayers, routeVisibility) {
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
    routes,
    historicalLayers,
    historicalLayerIds: Array.from(visibleHistoricalLayerIds),
    routeVisibility,
    archaeologyVisibility,
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
      renderSelectedArchaeology(marker, lastPassageContext);
    },
    onRouteClick(route) {
      selectedRoute = route;
      selectedMarker = null;
      selectedArchaeology = null;
      selectedHistoricalLayer = null;
      renderSelectedRoute(route, lastPassageContext);
    },
    onHistoricalLayerClick(layer) {
      selectedHistoricalLayer = layer;
      selectedMarker = null;
      selectedArchaeology = null;
      selectedRoute = null;
      visibleHistoricalLayerIds.add(layer.id);
      if (mapController) {
        mapController.setHistoricalLayerVisibility(layer.id, true);
      }
      renderSelectedHistoricalLayer(layer, lastPassageContext);
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
    selectedRoute = null;
    selectedHistoricalLayer = null;
  }
  if (context.savedMapStudy?.map_view_state?.historicalPeriod) {
    historicalPeriod = normalizeHistoricalPeriod(context.savedMapStudy.map_view_state.historicalPeriod);
  }
  if (context.savedMapStudy?.map_view_state && Object.prototype.hasOwnProperty.call(context.savedMapStudy.map_view_state, "archaeologyVisibility")) {
    archaeologyVisible = Boolean(context.savedMapStudy.map_view_state.archaeologyVisibility);
  }
  lastPassageContext = context;
  ensurePanelVisible(context);
  setStatus("Loading map data...", "loading");
  renderEmptyDetails("Loading place, archaeology, route, and layer details...");

  try {
    const routeToggle = getPanelElements().routeToggle;
    const archaeologyToggle = getPanelElements().archaeologyToggle;
    archaeologyVisible = archaeologyToggle ? Boolean(archaeologyToggle.checked) : archaeologyVisible;
    const routeVisibility = Boolean(routeToggle?.checked);
    const [placeResult, archaeologyResult, routeResult, layerResult] = await Promise.all([
      loadPlacesForPassage(context),
      loadArchaeologyForPassage(context),
      loadRoutesForPassage(context),
      loadHistoricalLayers({ period: historicalPeriod }),
    ]);
    const savedMapStudiesResult = await loadSavedMapStudies(context);
    loadedRoutes = routeResult.routes || [];
    loadedMarkers = placeResult.markers || [];
    loadedArchaeologyMarkers = archaeologyResult.markers || [];
    loadedHistoricalLayers = layerResult.layers || [];
    loadedSavedMapStudies = savedMapStudiesResult.saved_map_studies || [];
    if (selectedHistoricalLayer && !loadedHistoricalLayers.some((layer) => layer.id === selectedHistoricalLayer.id)) {
      selectedHistoricalLayer = null;
    }
    if (selectedArchaeology && !loadedArchaeologyMarkers.some((marker) => marker.id === selectedArchaeology.id)) {
      selectedArchaeology = null;
    }

    ensureMapController(
      loadedMarkers,
      loadedArchaeologyMarkers,
      loadedRoutes,
      loadedHistoricalLayers,
      routeVisibility
    );
    if (context.savedMapStudy) {
      await applySavedMapStudyState(context.savedMapStudy);
    }
    syncArchaeologyToggle();
    syncRouteToggle();
    syncHistoricalPeriod();
    syncHistoricalLayerToggles();
    renderSavedMapStudies();

    if (selectedMarker && (placeResult.markers || []).some((marker) => marker.id === selectedMarker.id)) {
      renderSelectedMarker(selectedMarker, context);
      clearStatus();
    } else if (selectedArchaeology && loadedArchaeologyMarkers.some((marker) => marker.id === selectedArchaeology.id)) {
      renderSelectedArchaeology(selectedArchaeology, context);
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
    } else {
      clearStatus();
      if (placeResult.empty_state) {
        renderEmptyDetails(
          "No curated biblical places were matched in this passage. Historical layers and routes remain available as study overlays."
        );
        setStatus(
          "No curated biblical places were matched in this passage. Showing the historical map framework for reference.",
          "empty"
        );
      } else {
        renderEmptyDetails("Click a marker, route, or historical layer to view details.");
      }
    }

    if (routeVisibility && loadedRoutes.length === 0) {
      setStatus("No curated routes matched this passage.", "empty");
    }
    if (archaeologyVisible && loadedArchaeologyMarkers.length === 0) {
      setStatus("No curated archaeology markers matched this passage.", "empty");
    }
    if (
      !loadedHistoricalLayers.length &&
      !selectedMarker &&
      !selectedArchaeology &&
      !selectedRoute &&
      !selectedHistoricalLayer
    ) {
      setStatus("No historical layers matched the selected period.", "empty");
    }
  } catch (error) {
    setStatus(error.message || "Could not load the map.", "error");
    renderEmptyDetails("Could not load place, archaeology, route, and layer details.");
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
  selectedRoute = null;
  selectedHistoricalLayer = null;

  if (mapController && typeof mapController.setRouteVisibility === "function" && Object.prototype.hasOwnProperty.call(viewState, "routeVisibility")) {
    mapController.setRouteVisibility(Boolean(viewState.routeVisibility));
  }
  if (mapController && typeof mapController.setArchaeologyVisibility === "function" && Object.prototype.hasOwnProperty.call(viewState, "archaeologyVisibility")) {
    archaeologyVisible = Boolean(viewState.archaeologyVisibility);
    mapController.setArchaeologyVisibility(Boolean(viewState.archaeologyVisibility));
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
  if (study.selected_route_id) {
    selectedRoute = loadedRoutes.find((route) => route.id === study.selected_route_id) || null;
  }
  if (study.selected_layer_id) {
    selectedHistoricalLayer =
      loadedHistoricalLayers.find((layer) => layer.id === study.selected_layer_id) || null;
  } else if (selectedLayerIds.size > 0) {
    const firstLayerId = Array.from(selectedLayerIds)[0];
    selectedHistoricalLayer =
      loadedHistoricalLayers.find((layer) => layer.id === firstLayerId) || null;
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
  if (panel) {
    panel.hidden = true;
  }
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
    setStatus("No curated routes matched this passage.", "empty");
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
    setStatus("No curated archaeology markers matched this passage.", "empty");
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
    const layerResult = await loadHistoricalLayers({ period: historicalPeriod });
    loadedHistoricalLayers = layerResult.layers || [];
    if (selectedHistoricalLayer && !loadedHistoricalLayers.some((layer) => layer.id === selectedHistoricalLayer.id)) {
      selectedHistoricalLayer = null;
    }
    if (mapController) {
      mapController.setHistoricalLayers(loadedHistoricalLayers);
    }
    syncHistoricalLayerToggles();
    if (selectedMarker) {
      renderSelectedMarker(selectedMarker, lastPassageContext);
    } else if (selectedArchaeology) {
      renderSelectedArchaeology(selectedArchaeology, lastPassageContext);
    } else if (selectedRoute) {
      renderSelectedRoute(selectedRoute, lastPassageContext);
    } else if (selectedHistoricalLayer) {
      renderSelectedHistoricalLayer(selectedHistoricalLayer, lastPassageContext);
    } else {
      renderHistoricalLayerOverview();
    }
    if (!loadedHistoricalLayers.length) {
      setStatus("No historical layers matched the selected period.", "empty");
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
  if (selectedMarker) {
    renderSelectedMarker(selectedMarker, lastPassageContext);
  } else if (selectedArchaeology) {
    renderSelectedArchaeology(selectedArchaeology, lastPassageContext);
  } else if (selectedRoute) {
    renderSelectedRoute(selectedRoute, lastPassageContext);
  } else if (selectedHistoricalLayer) {
    renderSelectedHistoricalLayer(selectedHistoricalLayer, lastPassageContext);
  } else {
    renderHistoricalLayerOverview();
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

function renderSelectedMarker(marker, passageContext) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  const relatedVerses = Array.isArray(marker.related_references) ? marker.related_references : [];
  const confidenceLabel = prettyConfidence(marker.confidence);
  const caution = buildCautionNote(marker);
  const explanation = buildPlaceExplanation(marker, passageContext);
  const sourceText = buildSourceText(marker);
  const aliases = Array.isArray(marker.aliases) ? marker.aliases : [];

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
        <h4>Modern location</h4>
        <p>${escapeHtml(marker.modern_location || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Ancient region</h4>
        <p>${escapeHtml(marker.ancient_region || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Related verses</h4>
        ${renderRelatedVerses(relatedVerses)}
      </section>

      <section class="map-detail-section">
        <h4>Source</h4>
        <p>${escapeHtml(sourceText)}</p>
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

      <section class="map-detail-section">
        <h4>Source</h4>
        <p>${escapeHtml(sourceText)}</p>
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

      <section class="map-detail-section">
        <h4>Source</h4>
        <p>${escapeHtml(sourceText)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Why this route matters</h4>
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
      <p class="map-layer-note">The boundaries are schematic. They are intended to frame the passage, not to claim exact borders.</p>
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
          : `<p class="empty map-details-empty">No curated archaeology markers match the selected passage.</p>`
      }
      <p class="map-layer-note">Archaeology markers are displayed as study aids. They are not proof of interpretation and should be read with the attached cautions.</p>
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
  return null;
}

function buildCurrentMapStudyPayload() {
  const context = lastPassageContext || {};
  const selection = getCurrentMapSelection();
  const mapViewState = mapController?.getViewState ? mapController.getViewState() : {};
  const selectedLayers = mapController?.getHistoricalLayerIds
    ? mapController.getHistoricalLayerIds()
    : Array.from(visibleHistoricalLayerIds);

  return {
    book: context.book,
    chapter: context.chapter,
    start_verse: context.verseStart || context.startVerse,
    end_verse: context.verseEnd || context.endVerse || context.verseStart || context.startVerse,
    passage_reference: formatReference(context),
    selected_place_id: selection?.kind === "place" ? selection.item.id : "",
    selected_archaeology_id: selection?.kind === "archaeology" ? selection.item.id : "",
    selected_route_id: selection?.kind === "route" ? selection.item.id : "",
    selected_layer_id: selection?.kind === "layer" ? selection.item.id : "",
    selected_place_name: selection?.kind === "place" ? selection.item.name : "",
    selected_archaeology_name: selection?.kind === "archaeology" ? selection.item.name : "",
    selected_route_name: selection?.kind === "route" ? selection.item.name : "",
    selected_layer_name: selection?.kind === "layer" ? selection.item.name : "",
    modern_location: selection?.kind === "place" ? selection.item.modern_location : "",
    ancient_region: selection?.kind === "place" ? selection.item.ancient_region : "",
    archaeology_location: selection?.kind === "archaeology" ? selection.item.location : "",
    confidence: selection?.item?.confidence || "",
    description: selection?.item?.description || "",
    period:
      selection?.kind === "layer"
        ? selection.item.period
        : selection?.kind === "route"
          ? selection.item.period
          : selection?.kind === "archaeology"
            ? selection.item.period
            : "",
    selected_layers: selectedLayers,
    map_view_state: mapViewState,
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
  if (selection.kind === "layer") {
    return `${name} in ${reference} as a ${item.period || "historical"} study layer.`;
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
    window.alert("Select a place, route, or historical layer first.");
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
  await refreshSavedMapStudies();
}

async function addCurrentMapNote() {
  if (!lastPassageContext) {
    window.alert("Open a passage on the map first.");
    return;
  }
  const selection = getCurrentMapSelection();
  if (!selection) {
    window.alert("Select a place, route, or historical layer first.");
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
  await refreshSavedMapStudies();
}

async function askAboutCurrentMapSelection() {
  const selection = getCurrentMapSelection();
  if (!selection) {
    window.alert("Select a place, route, or historical layer first.");
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
    window.alert("Select a place, route, or historical layer first.");
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
  await refreshSavedMapStudies();
}

function renderEmptyDetails(message) {
  const { details } = getPanelElements();
  if (!details) {
    return;
  }
  details.innerHTML = `
    <p class="empty map-details-empty">${escapeHtml(message)}</p>
    ${renderHistoricalLayerOverview()}
    ${renderArchaeologyLayerOverview()}
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
  const primaryLabel = kind === "archaeology" ? "Ask about this item" : "Ask about this location";
  return `
    <section class="map-detail-section map-action-section">
      <div class="map-action-buttons">
        <button type="button" class="secondary" data-map-action="ask_location">${escapeHtml(primaryLabel)}</button>
        <button type="button" class="secondary" data-map-action="save_map_study">Save map study</button>
        <button type="button" class="secondary" data-map-action="map_note">Add map note</button>
        <button type="button" class="secondary" data-map-action="compare_archaeology">Compare with archaeology</button>
        <button type="button" class="secondary" data-map-action="related_passages">View related passages</button>
        ${kind === "layer" || kind === "archaeology" ? "" : '<button type="button" class="secondary" data-map-action="view_historical_layer">View historical layer</button>'}
      </div>
      <p class="map-layer-note">Selected ${escapeHtml(kind)} confidence: ${escapeHtml(selectedLabel)}. Map actions use the curated local data only.</p>
    </section>
  `;
}

function buildSourceText(item) {
  const sourceName = item.source_name || "No source recorded";
  const sourceUrl = item.source_url ? ` (${item.source_url})` : "";
  const license = item.license ? ` License: ${item.license}.` : "";
  return `${sourceName}${sourceUrl}.${license}`;
}

function prettyConfidence(value) {
  const normalized = String(value || "unknown").toLowerCase();
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
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
        <li>
          <strong>${escapeHtml(reference.book)} ${escapeHtml(String(reference.chapter))}:${escapeHtml(verseRange)}</strong>
          <span>${escapeHtml(reference.relationship_type)}</span>
          <p>${escapeHtml(reference.notes || "")}</p>
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
  return HISTORICAL_PERIOD_OPTIONS.some((option) => option.value === normalized) ? normalized : "all";
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
  const archaeologyToggle = document.querySelector("[data-archaeology-toggle]");
  const routeToggle = document.querySelector("[data-route-toggle]");
  const historicalPeriodSelect = document.querySelector("[data-historical-period]");
  const details = document.querySelector("#map-details");

  if (closeButton) {
    closeButton.addEventListener("click", closeMapPanel);
  }
  if (resetButton) {
    resetButton.addEventListener("click", resetMapView);
  }
  if (archaeologyToggle) {
    archaeologyToggle.addEventListener("change", (event) => {
      setArchaeologyVisibility(Boolean(event.target.checked));
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
      }
    });
    details.addEventListener("change", (event) => {
      const toggle = event.target.closest("[data-historical-layer-toggle]");
      if (!toggle) {
        return;
      }
      setHistoricalLayerVisibility(toggle.getAttribute("data-layer-id"), Boolean(toggle.checked));
    });
  }
}

function initializeMapPanel() {
  wirePanelButtons();
  renderEmptyDetails("Click a marker, archaeology item, route, or historical layer to view details.");
  syncArchaeologyToggle();
  syncHistoricalPeriod();
}

if (typeof window !== "undefined") {
  window.BHFMaps = {
    openMapPanel,
    closeMapPanel,
    resetMapView,
    initializeMapPanel,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeMapPanel, { once: true });
  } else {
    initializeMapPanel();
  }
}
