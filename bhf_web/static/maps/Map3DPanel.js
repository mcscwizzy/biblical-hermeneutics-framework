const CESIUM_VERSION = "1.118.2";
const CESIUM_BASE_URL = `https://cdn.jsdelivr.net/npm/cesium@${CESIUM_VERSION}/Build/Cesium/`;
const JOURNEY_FILES = [
  "abraham.json",
  "exodus.json",
  "joshua-conquest.json",
  "david-fleeing-saul.json",
  "elijah-elisha.json",
  "jesus-galilean-ministry.json",
  "jesus-final-week.json",
  "paul-first-missionary.json",
  "paul-second-missionary.json",
  "paul-third-missionary.json",
  "paul-rome-voyage.json",
  "exile-return.json",
];
const JOURNEY_DATA_BASE_PATHS = [
  "/static/data/journeys",
];
const MAP_LAYER_FILES = [
  "ancientCities.json",
  "biblicalRegions.json",
  "rivers.json",
  "mountains.json",
  "tradeRoutes.json",
  "kingdoms.json",
];
const MAP_LAYER_DATA_BASE_PATHS = [
  "/static/data/mapLayers",
];
const PLAYBACK_SPEEDS = {
  slow: { label: "Slow", intervalMs: 2200 },
  normal: { label: "Normal", intervalMs: 1400 },
  fast: { label: "Fast", intervalMs: 800 },
};

let cesiumAssetsPromise = null;
let journeyCatalogPromise = null;
let mapLayerCatalogPromise = null;
let journeyModalOpen = false;
let lastJourneyModalTrigger = null;

const journeyState = {
  viewer: null,
  viewerReady: false,
  loading: false,
  journeys: [],
  selectedJourneyId: "",
  selectedStopId: "",
  selectedSegmentId: "",
  selectedLayerFeatureId: "",
  activeStopId: "",
  activeSegmentId: "",
  isPlaying: false,
  currentStopIndex: 0,
  playbackSpeed: "normal",
  playbackTimerId: null,
  playbackModeEnabled: true,
  journeySearch: "",
  journeyTestament: "",
  journeyCategory: "",
  journeyEra: "",
  activePeriod: "",
  libraryFacets: {
    categories: [],
    eras: [],
    testaments: [],
    tags: [],
  },
  mapLayers: [],
  layerVisibility: {},
  layerEntities: new Map(),
  layerFeatureIndex: new Map(),
  journeyEntities: new Set(),
  stopEntities: new Map(),
  segmentEntities: new Map(),
};

function applyCesiumIonToken(Cesium) {
  const ionToken = String(window.BHFCesiumIonToken || "").trim();
  if (ionToken && Cesium?.Ion) {
    Cesium.Ion.defaultAccessToken = ionToken;
  }
}

function getJourneyPanel() {
  return document.querySelector("#journey-panel");
}

function getElements() {
  return {
    panel: getJourneyPanel(),
    status: document.querySelector("[data-journey-status]"),
    stageStatus: document.querySelector("[data-journey-stage-status]"),
    selector: document.querySelector("[data-journey-selector]"),
    title: document.querySelector("[data-journey-title]"),
    description: document.querySelector("[data-journey-description]"),
    primaryPassages: document.querySelector("[data-journey-primary-passages]"),
    note: document.querySelector("[data-journey-note]"),
    metadata: document.querySelector("[data-journey-metadata]"),
    metadataTestament: document.querySelector("[data-journey-metadata-testament]"),
    metadataCategory: document.querySelector("[data-journey-metadata-category]"),
    metadataEra: document.querySelector("[data-journey-metadata-era]"),
    metadataBookRange: document.querySelector("[data-journey-metadata-book-range]"),
    metadataTags: document.querySelector("[data-journey-metadata-tags]"),
    layerControls: document.querySelector("[data-journey-layer-controls]"),
    layerDetailTitle: document.querySelector("[data-journey-layer-detail-title]"),
    layerDetailConfidence: document.querySelector("[data-journey-layer-detail-confidence]"),
    layerDetailSubtitle: document.querySelector("[data-journey-layer-detail-subtitle]"),
    layerDetailBody: document.querySelector("[data-journey-layer-detail-body]"),
    layerDetailDescription: document.querySelector("[data-journey-layer-detail-description]"),
    layerDetailNote: document.querySelector("[data-journey-layer-detail-note]"),
    layerOpenPassage: document.querySelector("[data-journey-layer-open-passage]"),
    searchInput: document.querySelector("[data-journey-search]"),
    testamentFilter: document.querySelector("[data-journey-filter-testament]"),
    categoryFilter: document.querySelector("[data-journey-filter-category]"),
    eraFilter: document.querySelector("[data-journey-filter-era]"),
    visibleCount: document.querySelector("[data-journey-visible-count]"),
    zoomButton: document.querySelector("[data-journey-zoom]"),
    playbackState: document.querySelector("[data-journey-playback-state]"),
    playButton: document.querySelector("[data-journey-playback-play]"),
    pauseButton: document.querySelector("[data-journey-playback-pause]"),
    previousButton: document.querySelector("[data-journey-playback-prev]"),
    nextButton: document.querySelector("[data-journey-playback-next]"),
    restartButton: document.querySelector("[data-journey-playback-restart]"),
    speedSelect: document.querySelector("[data-journey-playback-speed]"),
    progressLabel: document.querySelector("[data-journey-playback-label]"),
    progressBar: document.querySelector("[data-journey-playback-bar]"),
    progressPercent: document.querySelector("[data-journey-playback-percent]"),
    progressValue: document.querySelector("[data-journey-playback-value]"),
    stopList: document.querySelector("[data-journey-stop-list]"),
    stopCount: document.querySelector("[data-journey-stop-count]"),
    segmentList: document.querySelector("[data-journey-segment-list]"),
    segmentCount: document.querySelector("[data-journey-segment-count]"),
    detailTitle: document.querySelector("[data-journey-detail-title]"),
    detailConfidence: document.querySelector("[data-journey-detail-confidence]"),
    detailSubtitle: document.querySelector("[data-journey-detail-subtitle]"),
    detailBody: document.querySelector("[data-journey-detail-body]"),
    detailDescription: document.querySelector("[data-journey-detail-description]"),
    detailNote: document.querySelector("[data-journey-detail-note]"),
    openPassage: document.querySelector("[data-journey-open-passage]"),
    stage: document.querySelector("[data-journey-stage]"),
    panel: document.querySelector("#journey-panel"),
    inlineHost: document.querySelector("#journey-panel-inline-host"),
    modal: document.querySelector("#journey-modal"),
    modalHost: document.querySelector("#journey-panel-modal-host"),
    expandButton: document.querySelector("[data-journey-expand]"),
    modalCloseButton: document.querySelector("[data-journey-modal-close]"),
  };
}

function normalizeConfidence(value) {
  return String(value || "unknown").trim().toLowerCase().replace(/\s+/g, "-") || "unknown";
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getSelectedJourney() {
  return journeyState.journeys.find((journey) => journey.id === journeyState.selectedJourneyId) || null;
}

function getSelectedStop(journey) {
  if (!journey) {
    return null;
  }
  return journey.stops.find((stop) => stop.id === journeyState.selectedStopId) || null;
}

function getSelectedSegment(journey) {
  if (!journey) {
    return null;
  }
  return journey.segments.find((segment) => segment.id === journeyState.selectedSegmentId) || null;
}

function getSelectedLayerFeature() {
  if (!journeyState.selectedLayerFeatureId) {
    return null;
  }
  return journeyState.layerFeatureIndex.get(journeyState.selectedLayerFeatureId) || null;
}

function normalizeSearchValue(value) {
  return String(value ?? "").trim().toLowerCase();
}

function getJourneyFacetValues(journeys, field) {
  return Array.from(
    new Set(
      journeys
        .flatMap((journey) => (Array.isArray(journey[field]) ? journey[field] : journey[field] ? [journey[field]] : []))
        .map((value) => String(value).trim())
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b));
}

function getVisibleJourneys() {
  const search = normalizeSearchValue(journeyState.journeySearch);
  return journeyState.journeys.filter((journey) => {
    if (journeyState.journeyTestament && journey.testament !== journeyState.journeyTestament) {
      return false;
    }
    if (journeyState.journeyCategory && journey.category !== journeyState.journeyCategory) {
      return false;
    }
    if (journeyState.journeyEra && journey.era !== journeyState.journeyEra) {
      return false;
    }
    if (!search) {
      return true;
    }
    const haystack = [
      journey.title,
      journey.description,
      journey.category,
      journey.testament,
      journey.era,
      ...(journey.tags || []),
      ...(journey.bookRange || []),
    ]
      .map(normalizeSearchValue)
      .join(" ");
    return haystack.includes(search);
  });
}

function syncJourneySelectionToVisibleJourneys() {
  const visibleJourneys = getVisibleJourneys();
  const hasSearch = Boolean(normalizeSearchValue(journeyState.journeySearch));
  if (visibleJourneys.length === 0) {
    if (journeyState.selectedJourneyId) {
      journeyState.selectedJourneyId = "";
      resetPlaybackForJourney(null);
      renderJourneyUi();
      if (journeyState.viewerReady && journeyState.viewer) {
        removeJourneyEntities();
        showGlobeOverview();
        journeyState.viewer.scene.requestRender();
      }
    }
    return;
  }
  if (visibleJourneys.some((journey) => journey.id === journeyState.selectedJourneyId)) {
    return;
  }
  if (!hasSearch && !journeyState.selectedJourneyId) {
    return;
  }
  const nextJourney = visibleJourneys[0];
  clearSelectionsForJourneyChange(nextJourney);
  renderJourneyUi();
  loadJourneyIntoViewer(nextJourney);
  if (journeyState.viewerReady && journeyState.viewer) {
    journeyState.viewer.scene.requestRender();
  }
}

function getActivePeriodFilter() {
  const externalOptions = window.BHFJourneyPanelOptions || window.BHFJourneyContext || {};
  return String(journeyState.activePeriod || externalOptions.activePeriod || externalOptions.selectedPeriod || "").trim();
}

function setActivePeriod(period) {
  journeyState.activePeriod = typeof period === "string" ? period.trim() : "";
  const selectedLayerFeature = getSelectedLayerFeature();
  if (selectedLayerFeature && !featureMatchesActivePeriod(selectedLayerFeature.feature)) {
    journeyState.selectedLayerFeatureId = "";
  }
  syncLayerEntityStyles();
  renderJourneyUi();
  if (journeyState.viewerReady && journeyState.viewer) {
    journeyState.viewer.scene.requestRender();
  }
}

function getLayerFeatureKey(layerId, featureId) {
  return `${layerId}:${featureId}`;
}

function featureMatchesActivePeriod(feature) {
  const activePeriod = getActivePeriodFilter();
  if (!activePeriod) {
    return true;
  }
  const periods = Array.isArray(feature?.periods) ? feature.periods.map((period) => normalizeSearchValue(period)) : [];
  return periods.length === 0 || periods.includes(normalizeSearchValue(activePeriod));
}

function isLayerVisible(layer) {
  return journeyState.layerVisibility[layer.id] !== false;
}

function getVisibleLayerFeatures(layer) {
  return (layer?.features || []).filter((feature) => featureMatchesActivePeriod(feature));
}

function getOrderedJourneyStops(journey) {
  return (journey?.stops || [])
    .map((stop, index) => ({
      stop,
      index,
      hasOrder: isFiniteNumber(stop.order),
    }))
    .sort((a, b) => {
      if (a.hasOrder && b.hasOrder) {
        return a.stop.order - b.stop.order || a.index - b.index;
      }
      if (a.hasOrder !== b.hasOrder) {
        return a.hasOrder ? -1 : 1;
      }
      return a.index - b.index;
    })
    .map((entry) => entry.stop);
}

function getPlaybackStopIndex(journey, stopId) {
  return getOrderedJourneyStops(journey).findIndex((stop) => stop.id === stopId);
}

function getPlaybackSegmentBetweenStops(journey, previousStopId, currentStopId) {
  if (!journey || !previousStopId || !currentStopId) {
    return null;
  }
  return (
    journey.segments.find(
      (segment) =>
        (segment.from === previousStopId && segment.to === currentStopId) ||
        (segment.from === currentStopId && segment.to === previousStopId)
    ) || null
  );
}

function getPlaybackIntervalMs() {
  return PLAYBACK_SPEEDS[journeyState.playbackSpeed]?.intervalMs || PLAYBACK_SPEEDS.normal.intervalMs;
}

function buildStopPinSvg(stop, { selected = false, active = false } = {}) {
  const fill = selected ? "#d18a16" : active ? "#0f7c7b" : "#245b82";
  const stroke = selected ? "#8e5c0a" : active ? "#0a4a49" : "#153f5d";
  const ring = active
    ? `<circle cx="28" cy="27" r="16" fill="none" stroke="${selected ? "#f1d28a" : "#7dd9d6"}" stroke-width="3" opacity="0.95"/>`
    : "";
  const orderText = Number.isFinite(stop.order) ? String(stop.order) : "";
  const label = orderText
    ? `<text x="28" y="33" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="${selected ? "#fff" : "#fff"}">${escapeHtml(orderText)}</text>`
    : "";
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="56" height="72" viewBox="0 0 56 72" fill="none">
      ${ring}
      <path d="M28 70C28 70 50 44.2 50 27.2C50 15.1 40.2 5.3 28 5.3C15.8 5.3 6 15.1 6 27.2C6 44.2 28 70 28 70Z" fill="${fill}" stroke="${stroke}" stroke-width="3"/>
      <circle cx="28" cy="27" r="11" fill="rgba(255,255,255,0.94)"/>
      ${label}
    </svg>
  `;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function buildSegmentMaterial({ selected = false, active = false } = {}) {
  const Cesium = window.Cesium;
  const color = selected
    ? Cesium.Color.fromCssColorString("#d18a16")
    : active
      ? Cesium.Color.fromCssColorString("#0f7c7b")
    : Cesium.Color.fromCssColorString("#245b82");
  return new Cesium.PolylineGlowMaterialProperty({
    glowPower: selected ? 0.3 : active ? 0.24 : 0.18,
    color,
  });
}

function buildLayerTint(layer, feature, { selected = false } = {}) {
  const Cesium = window.Cesium;
  const palette = {
    "ancient-cities": "#8e5c0a",
    "biblical-regions": "#6a7f3c",
    rivers: "#1f6fa6",
    mountains: "#8c6a3d",
    "trade-routes": "#8a4e2f",
    kingdoms: "#8a3f73",
  };
  const layerColor = Cesium.Color.fromCssColorString(palette[layer.id] || "#245b82");
  return selected ? layerColor.withAlpha(0.98) : layerColor.withAlpha(feature?.confidence === "low" ? 0.65 : 0.82);
}

function buildLayerStrokeColor(layer, feature, options = {}) {
  return buildLayerTint(layer, feature, options);
}

function buildLayerFillColor(layer, feature, { selected = false } = {}) {
  const Cesium = window.Cesium;
  const color = buildLayerTint(layer, feature, { selected });
  return color.withAlpha(selected ? 0.22 : 0.12);
}

function buildLayerLineMaterial(layer, feature, { selected = false } = {}) {
  const Cesium = window.Cesium;
  return new Cesium.PolylineGlowMaterialProperty({
    glowPower: selected ? 0.28 : 0.16,
    color: buildLayerTint(layer, feature, { selected }),
  });
}

function buildLayerPolygonMaterial(layer, feature, { selected = false } = {}) {
  return buildLayerFillColor(layer, feature, { selected });
}

function buildLayerPointSvg(feature, layer, { selected = false } = {}) {
  const fill = buildLayerTint(layer, feature, { selected }).toCssColorString();
  const stroke = selected ? "#6b4c09" : "#17364d";
  const label = escapeHtml(feature.name || "");
  const ring = selected ? '<circle cx="26" cy="26" r="18" fill="none" stroke="#f1d28a" stroke-width="3" opacity="0.9"/>' : "";
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="52" height="66" viewBox="0 0 52 66" fill="none">
      ${ring}
      <path d="M26 64C26 64 46 39.2 46 24.9C46 13.8 37.1 4.9 26 4.9C14.9 4.9 6 13.8 6 24.9C6 39.2 26 64 26 64Z" fill="${fill}" stroke="${stroke}" stroke-width="3"/>
      <circle cx="26" cy="25" r="10" fill="rgba(255,255,255,0.95)"/>
      <text x="26" y="29" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#1d252d">${label.slice(0, 1).toUpperCase()}</text>
    </svg>
  `)}`;
}

function buildFallbackGlobeImageryProvider(Cesium) {
  const rectangle = Cesium.Rectangle.fromDegrees(-180, -90, 180, 90);
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="2048" height="1024" viewBox="0 0 2048 1024">
      <rect width="2048" height="1024" fill="#b8d7e8"/>
      <path d="M260 235 C355 150 492 170 566 258 C626 329 575 412 445 413 C334 414 239 355 260 235Z" fill="#6f9857"/>
      <path d="M433 451 C541 410 655 462 723 536 C805 627 748 742 612 760 C486 776 378 711 354 613 C335 535 363 479 433 451Z" fill="#759b5c"/>
      <path d="M890 235 C980 164 1120 176 1215 252 C1300 320 1270 412 1150 436 C1014 463 880 392 854 304 C845 274 856 252 890 235Z" fill="#7fa15e"/>
      <path d="M1040 468 C1146 418 1300 430 1390 506 C1471 574 1450 674 1334 711 C1208 751 1045 696 1004 600 C979 543 991 491 1040 468Z" fill="#6f9857"/>
      <path d="M1458 258 C1557 178 1712 185 1810 265 C1904 341 1864 450 1711 466 C1579 480 1452 407 1430 318 C1423 291 1434 273 1458 258Z" fill="#7a9f5d"/>
      <path d="M1560 590 C1648 542 1780 560 1845 638 C1905 710 1850 800 1718 805 C1610 809 1516 754 1501 681 C1493 640 1514 609 1560 590Z" fill="#769c59"/>
      <path d="M0 512 H2048" stroke="#ffffff" stroke-opacity="0.18" stroke-width="2"/>
      <path d="M0 256 H2048 M0 768 H2048" stroke="#ffffff" stroke-opacity="0.12" stroke-width="2"/>
      <path d="M512 0 V1024 M1024 0 V1024 M1536 0 V1024" stroke="#ffffff" stroke-opacity="0.1" stroke-width="2"/>
    </svg>
  `;
  return new Cesium.SingleTileImageryProvider({
    url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
    rectangle,
  });
}

function clearPlaybackTimer() {
  if (journeyState.playbackTimerId !== null) {
    window.clearTimeout(journeyState.playbackTimerId);
    journeyState.playbackTimerId = null;
  }
}

function pausePlayback({ preserveTimer = false } = {}) {
  journeyState.isPlaying = false;
  if (!preserveTimer) {
    clearPlaybackTimer();
  }
}

function schedulePlaybackAdvance() {
  clearPlaybackTimer();
  if (!journeyState.isPlaying) {
    return;
  }
  journeyState.playbackTimerId = window.setTimeout(() => {
    advancePlayback(1, { autoplay: true });
  }, getPlaybackIntervalMs());
}

function setPlaybackStepByIndex(index, { flyTo = true, updateSelection = true, previousStopId = null, focusRouteSegment = true } = {}) {
  const journey = getSelectedJourney();
  if (!journey) {
    return;
  }

  const orderedStops = getOrderedJourneyStops(journey);
  const nextStop = orderedStops[index] || null;
  if (!nextStop) {
    return;
  }

  journeyState.currentStopIndex = index;
  journeyState.activeStopId = nextStop.id;
  journeyState.selectedStopId = updateSelection ? nextStop.id : journeyState.selectedStopId;
  journeyState.selectedSegmentId = "";

  const previousStop = previousStopId ? journey.stops.find((stop) => stop.id === previousStopId) : orderedStops[index - 1] || null;
  const segment = focusRouteSegment ? getPlaybackSegmentBetweenStops(journey, previousStop?.id || "", nextStop.id) : null;
  journeyState.activeSegmentId = segment?.id || "";

  refreshJourneyUi({ zoom: false });

  if (flyTo && journeyState.viewerReady && journeyState.viewer) {
    if (segment) {
      focusSegment(segment);
    } else {
      flyToStop(nextStop);
    }
  }
}

function advancePlayback(delta, { autoplay = false } = {}) {
  const journey = getSelectedJourney();
  if (!journey) {
    return;
  }

  const orderedStops = getOrderedJourneyStops(journey);
  if (orderedStops.length === 0) {
    pausePlayback();
    return;
  }

  const currentIndex = Math.max(0, journeyState.currentStopIndex || 0);
  const nextIndex = Math.min(Math.max(currentIndex + delta, 0), orderedStops.length - 1);
  const previousStop = orderedStops[currentIndex] || null;

  if (nextIndex === currentIndex) {
    pausePlayback();
    refreshJourneyUi({ zoom: false });
    return;
  }

  setPlaybackStepByIndex(nextIndex, {
    flyTo: true,
    updateSelection: true,
    previousStopId: previousStop?.id || null,
    focusRouteSegment: true,
  });

  if (autoplay && nextIndex < orderedStops.length - 1) {
    schedulePlaybackAdvance();
    return;
  }

  pausePlayback();
  refreshJourneyUi({ zoom: false });
}

function playPlayback() {
  const journey = getSelectedJourney();
  if (!journey) {
    return;
  }
  const orderedStops = getOrderedJourneyStops(journey);
  if (orderedStops.length === 0) {
    return;
  }
  journeyState.isPlaying = true;
  if (journeyState.currentStopIndex >= orderedStops.length) {
    journeyState.currentStopIndex = 0;
  }
  schedulePlaybackAdvance();
  refreshJourneyUi({ zoom: false });
}

function restartPlayback() {
  const journey = getSelectedJourney();
  if (!journey) {
    return;
  }
  pausePlayback();
  const orderedStops = getOrderedJourneyStops(journey);
  if (orderedStops.length === 0) {
    refreshJourneyUi({ zoom: false });
    return;
  }
  setPlaybackStepByIndex(0, { flyTo: true, updateSelection: true, previousStopId: null, focusRouteSegment: false });
}

function handlePlaybackSpeedChange(event) {
  journeyState.playbackSpeed = event.target.value in PLAYBACK_SPEEDS ? event.target.value : "normal";
  if (journeyState.isPlaying) {
    schedulePlaybackAdvance();
  }
  refreshJourneyUi({ zoom: false });
}

function setStatus(message, kind = "loading") {
  const { status, stageStatus } = getElements();
  for (const element of [status, stageStatus]) {
    if (!element) {
      continue;
    }
    element.hidden = !message;
    element.textContent = message || "";
    element.dataset.state = kind;
    element.classList.toggle("is-error", kind === "error");
  }
}

function clearStatus() {
  setStatus("", "ready");
}

function syncJourneyViewport({ zoom = false } = {}) {
  if (!journeyState.viewer) {
    return;
  }
  window.requestAnimationFrame(() => {
    if (!journeyState.viewer) {
      return;
    }
    if (typeof journeyState.viewer.resize === "function") {
      journeyState.viewer.resize();
    } else if (journeyState.viewer.cesiumWidget && typeof journeyState.viewer.cesiumWidget.resize === "function") {
      journeyState.viewer.cesiumWidget.resize();
    }
    if (zoom) {
      fitJourney();
    }
    journeyState.viewer.scene.requestRender();
  });
}

function moveJourneyPanelToHost(hostType) {
  const { panel, inlineHost, modalHost } = getElements();
  if (!panel || !inlineHost || !modalHost) {
    return;
  }
  const targetHost = hostType === "modal" ? modalHost : inlineHost;
  if (!targetHost || panel.parentElement === targetHost) {
    panel.dataset.journeyHost = hostType;
    syncJourneyViewport({ zoom: hostType === "modal" });
    return;
  }
  targetHost.appendChild(panel);
  panel.dataset.journeyHost = hostType;
  syncJourneyViewport({ zoom: hostType === "modal" });
}

function openJourneyModal() {
  const { modal } = getElements();
  if (!modal || journeyModalOpen) {
    return;
  }
  lastJourneyModalTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  moveJourneyPanelToHost("modal");
  if (typeof modal.showModal === "function") {
    modal.showModal();
  } else {
    modal.setAttribute("open", "");
  }
  document.body.classList.add("journey-modal-open");
  journeyModalOpen = true;
  syncJourneyViewport({ zoom: true });
}

function closeJourneyModal() {
  const { modal } = getElements();
  if (!modal || !journeyModalOpen) {
    return;
  }
  if (typeof modal.close === "function" && modal.open) {
    modal.close();
  } else {
    modal.removeAttribute("open");
    finalizeJourneyModalClose();
  }
}

function finalizeJourneyModalClose() {
  if (!journeyModalOpen) {
    return;
  }
  moveJourneyPanelToHost("inline");
  document.body.classList.remove("journey-modal-open");
  journeyModalOpen = false;
  syncJourneyViewport();
  if (lastJourneyModalTrigger && typeof lastJourneyModalTrigger.focus === "function") {
    lastJourneyModalTrigger.focus({ preventScroll: true });
  }
  lastJourneyModalTrigger = null;
}

function loadCesiumAssets() {
  if (window.Cesium) {
    applyCesiumIonToken(window.Cesium);
    return Promise.resolve(window.Cesium);
  }
  if (!cesiumAssetsPromise) {
    cesiumAssetsPromise = new Promise((resolve, reject) => {
      window.CESIUM_BASE_URL = CESIUM_BASE_URL;

      if (!document.querySelector('link[data-cesium-css="true"]')) {
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = `${CESIUM_BASE_URL}Widgets/widgets.css`;
        link.dataset.cesiumCss = "true";
        document.head.appendChild(link);
      }

      const existingScript = document.querySelector('script[data-cesium-js="true"]');
      if (existingScript) {
        if (existingScript.dataset.cesiumJsState === "error") {
          cesiumAssetsPromise = null;
          reject(new Error("Could not load CesiumJS from the CDN."));
          return;
        }
        if (window.Cesium) {
          applyCesiumIonToken(window.Cesium);
          resolve(window.Cesium);
          return;
        }
        if (existingScript.dataset.cesiumJsState === "loaded") {
          cesiumAssetsPromise = null;
          reject(new Error("Cesium loaded, but the global API was not available."));
          return;
        }
        existingScript.addEventListener(
          "load",
          () => {
            if (window.Cesium) {
              applyCesiumIonToken(window.Cesium);
              resolve(window.Cesium);
              return;
            }
            cesiumAssetsPromise = null;
            reject(new Error("Cesium loaded, but the global API was not available."));
          },
          { once: true }
        );
        existingScript.addEventListener(
          "error",
          () => {
            cesiumAssetsPromise = null;
            reject(new Error("Could not load CesiumJS from the CDN."));
          },
          { once: true }
        );
        return;
      }

      const script = document.createElement("script");
      script.src = `${CESIUM_BASE_URL}Cesium.js`;
      script.async = true;
      script.dataset.cesiumJs = "true";
      script.onload = () => {
        script.dataset.cesiumJsState = "loaded";
        if (!window.Cesium) {
          cesiumAssetsPromise = null;
          reject(new Error("Cesium loaded, but the global API was not available."));
          return;
        }
        applyCesiumIonToken(window.Cesium);
        resolve(window.Cesium);
      };
      script.onerror = () => {
        script.dataset.cesiumJsState = "error";
        script.remove();
        cesiumAssetsPromise = null;
        reject(new Error("Could not load CesiumJS from the CDN."));
      };
      document.head.appendChild(script);
    });
  }
  return cesiumAssetsPromise;
}

function validateJourney(journey, sourceLabel = "<unknown journey>") {
  const errors = [];

  if (!isPlainObject(journey)) {
    errors.push("journey must be an object");
  } else {
    if (typeof journey.id !== "string" || !journey.id.trim()) {
      errors.push("missing id");
    }
    if (typeof journey.title !== "string" || !journey.title.trim()) {
      errors.push("missing title");
    }
    if (!Array.isArray(journey.stops) || journey.stops.length === 0) {
      errors.push("stops must be a non-empty array");
    }
  }

  if (errors.length > 0) {
    console.warn(`[BHF Journey] Skipping invalid journey ${sourceLabel}: ${errors.join(", ")}`);
    return false;
  }

  const stopIds = new Set();
  for (const stop of journey.stops) {
    if (!isPlainObject(stop)) {
      errors.push(`stop entries must be objects (${sourceLabel})`);
      continue;
    }
    if (typeof stop.id !== "string" || !stop.id.trim()) {
      errors.push(`stop missing id (${sourceLabel})`);
    } else {
      if (stopIds.has(stop.id)) {
        errors.push(`duplicate stop id "${stop.id}" (${sourceLabel})`);
      }
      stopIds.add(stop.id);
    }
    if (typeof stop.name !== "string" || !stop.name.trim()) {
      errors.push(`stop ${stop.id || "<unknown>"} missing name (${sourceLabel})`);
    }
    if (!isFiniteNumber(stop.lat)) {
      errors.push(`stop ${stop.id || "<unknown>"} missing numeric lat (${sourceLabel})`);
    }
    if (!isFiniteNumber(stop.lng)) {
      errors.push(`stop ${stop.id || "<unknown>"} missing numeric lng (${sourceLabel})`);
    }
    if (Object.prototype.hasOwnProperty.call(stop, "order") && !isFiniteNumber(stop.order)) {
      errors.push(`stop ${stop.id || "<unknown>"} has non-numeric order (${sourceLabel})`);
    }
  }

  const segmentIds = new Set();
  for (const segment of Array.isArray(journey.segments) ? journey.segments : []) {
    if (!isPlainObject(segment)) {
      errors.push(`segment entries must be objects (${sourceLabel})`);
      continue;
    }
    if (typeof segment.id !== "string" || !segment.id.trim()) {
      errors.push(`segment missing id (${sourceLabel})`);
    } else {
      if (segmentIds.has(segment.id)) {
        errors.push(`duplicate segment id "${segment.id}" (${sourceLabel})`);
      }
      segmentIds.add(segment.id);
    }
    if (!stopIds.has(segment.from)) {
      errors.push(`segment from "${segment.from}" does not match a stop id (${sourceLabel})`);
    }
    if (!stopIds.has(segment.to)) {
      errors.push(`segment to "${segment.to}" does not match a stop id (${sourceLabel})`);
    }
  }

  if (errors.length > 0) {
    console.warn(`[BHF Journey] Skipping invalid journey ${sourceLabel}: ${errors.join(", ")}`);
    return false;
  }

  return true;
}

async function fetchJourneyFile(fileName) {
  const failures = [];
  for (const basePath of JOURNEY_DATA_BASE_PATHS) {
    const url = `${basePath}/${fileName}?v=20260630c`;
    try {
      const response = await fetch(url);
      if (!response.ok) {
        failures.push(`${url}: ${response.status}`);
        continue;
      }
      return response.json();
    } catch (error) {
      failures.push(`${url}: ${error.message || "request failed"}`);
    }
  }
  throw new Error(`Could not load ${fileName}. Tried ${failures.join("; ")}`);
}

async function loadJourneyCatalog() {
  const records = await Promise.allSettled(JOURNEY_FILES.map((fileName) => fetchJourneyFile(fileName)));
  const journeys = [];

  for (const [index, record] of records.entries()) {
    const fileName = JOURNEY_FILES[index];
    if (record.status !== "fulfilled") {
      console.warn(`[BHF Journey] Skipping journey file ${fileName}: ${record.reason?.message || "unknown error"}`);
      continue;
    }
    if (validateJourney(record.value, fileName)) {
      journeys.push(record.value);
    }
  }

  return {
    journeys,
    defaultJourneyId: "",
  };
}

async function loadJourneys() {
  if (!journeyCatalogPromise) {
    journeyCatalogPromise = loadJourneyCatalog()
      .then((catalog) => catalog.journeys || [])
      .catch((error) => {
        journeyCatalogPromise = null;
        throw error;
      });
  }
  return journeyCatalogPromise;
}

function validateMapLayer(layer, sourceLabel = "<unknown layer>") {
  const errors = [];
  const warnings = [];

  if (!isPlainObject(layer)) {
    errors.push("layer must be an object");
  } else {
    if (typeof layer.id !== "string" || !layer.id.trim()) {
      errors.push("missing id");
    }
    if (typeof layer.title !== "string" || !layer.title.trim()) {
      errors.push("missing title");
    }
    if (!["points", "lines", "polygons"].includes(layer.type)) {
      errors.push("type must be points, lines, or polygons");
    }
    if (!Array.isArray(layer.features) || layer.features.length === 0) {
      errors.push("features must be a non-empty array");
    }
    if (Object.prototype.hasOwnProperty.call(layer, "defaultVisible") && typeof layer.defaultVisible !== "boolean") {
      warnings.push("defaultVisible should be a boolean if provided");
    }
  }

  if (warnings.length > 0) {
    console.warn(`[BHF Layer] Metadata warnings for ${sourceLabel}: ${warnings.join(", ")}`);
  }

  if (errors.length > 0) {
    console.warn(`[BHF Layer] Skipping invalid layer ${sourceLabel}: ${errors.join(", ")}`);
    return false;
  }

  const featureIds = new Set();
  const features = [];
  for (const feature of layer.features) {
    if (!isPlainObject(feature)) {
      console.warn(`[BHF Layer] Skipping invalid feature in ${sourceLabel}: feature entries must be objects`);
      continue;
    }
    if (typeof feature.id !== "string" || !feature.id.trim()) {
      console.warn(`[BHF Layer] Skipping invalid feature in ${sourceLabel}: missing id`);
      continue;
    }
    if (featureIds.has(feature.id)) {
      console.warn(`[BHF Layer] Skipping duplicate feature id "${feature.id}" in ${sourceLabel}`);
      continue;
    }
    if (typeof feature.name !== "string" || !feature.name.trim()) {
      console.warn(`[BHF Layer] Skipping invalid feature "${feature.id}" in ${sourceLabel}: missing name`);
      continue;
    }
    if (layer.type === "points") {
      if (!isFiniteNumber(feature.lat) || !isFiniteNumber(feature.lng)) {
        console.warn(`[BHF Layer] Skipping invalid point feature "${feature.id}" in ${sourceLabel}: numeric lat/lng required`);
        continue;
      }
    } else {
      if (!Array.isArray(feature.points) || feature.points.length === 0) {
        console.warn(`[BHF Layer] Skipping invalid ${layer.type.slice(0, -1)} feature "${feature.id}" in ${sourceLabel}: points must be a non-empty array`);
        continue;
      }
      const invalidPoint = feature.points.some((point) => !Array.isArray(point) || point.length < 2 || !isFiniteNumber(point[0]) || !isFiniteNumber(point[1]));
      if (invalidPoint) {
        console.warn(`[BHF Layer] Skipping invalid ${layer.type.slice(0, -1)} feature "${feature.id}" in ${sourceLabel}: each point must be [lat, lng]`);
        continue;
      }
    }
    if (Object.prototype.hasOwnProperty.call(feature, "periods") && !Array.isArray(feature.periods)) {
      console.warn(`[BHF Layer] Feature "${feature.id}" in ${sourceLabel} has non-array periods; ignoring the field`);
      feature.periods = [];
    }
    if (Object.prototype.hasOwnProperty.call(feature, "passages") && !Array.isArray(feature.passages)) {
      console.warn(`[BHF Layer] Feature "${feature.id}" in ${sourceLabel} has non-array passages; ignoring the field`);
      feature.passages = [];
    }
    featureIds.add(feature.id);
    features.push({
      ...feature,
      periods: Array.isArray(feature.periods) ? feature.periods : [],
      passages: Array.isArray(feature.passages) ? feature.passages : [],
    });
  }

  if (features.length === 0) {
    console.warn(`[BHF Layer] Skipping invalid layer ${sourceLabel}: no valid features remain`);
    return false;
  }

  return {
    ...layer,
    defaultVisible: Boolean(layer.defaultVisible),
    features,
  };
}

async function fetchMapLayerFile(fileName) {
  const failures = [];
  for (const basePath of MAP_LAYER_DATA_BASE_PATHS) {
    const url = `${basePath}/${fileName}?v=20260630a`;
    try {
      const response = await fetch(url);
      if (!response.ok) {
        failures.push(`${url}: ${response.status}`);
        continue;
      }
      return response.json();
    } catch (error) {
      failures.push(`${url}: ${error.message || "request failed"}`);
    }
  }
  throw new Error(`Could not load ${fileName}. Tried ${failures.join("; ")}`);
}

async function loadMapLayerCatalog() {
  const records = await Promise.allSettled(MAP_LAYER_FILES.map((fileName) => fetchMapLayerFile(fileName)));
  const layers = [];

  for (const [index, record] of records.entries()) {
    const fileName = MAP_LAYER_FILES[index];
    if (record.status !== "fulfilled") {
      console.warn(`[BHF Layer] Skipping layer file ${fileName}: ${record.reason?.message || "unknown error"}`);
      continue;
    }
    const layer = validateMapLayer(record.value, fileName);
    if (layer) {
      layers.push(layer);
    }
  }

  return {
    layers,
    mapLayersById: Object.fromEntries(layers.map((layer) => [layer.id, layer])),
    defaultVisibleLayerIds: layers.filter((layer) => layer.defaultVisible).map((layer) => layer.id),
  };
}

function renderJourneyLibraryFilters(visibleJourneys) {
  const { searchInput, testamentFilter, categoryFilter, eraFilter, visibleCount } = getElements();
  const allJourneys = journeyState.journeys;
  const facets = journeyState.libraryFacets;

  if (searchInput && searchInput.value !== journeyState.journeySearch) {
    searchInput.value = journeyState.journeySearch;
  }

  const populateSelect = (select, values, currentValue) => {
    if (!select) {
      return;
    }
    const existingValue = select.value || currentValue || "";
    select.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "All";
    select.appendChild(placeholder);
    for (const value of values) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    }
    select.value = values.includes(existingValue) ? existingValue : "";
  };

  populateSelect(testamentFilter, facets.testaments, journeyState.journeyTestament);
  populateSelect(categoryFilter, facets.categories, journeyState.journeyCategory);
  populateSelect(eraFilter, facets.eras, journeyState.journeyEra);

  if (visibleCount) {
    visibleCount.textContent = `Showing ${visibleJourneys.length} of ${allJourneys.length} journeys`;
  }
}

function renderJourneySelector(visibleJourneys) {
  const { selector } = getElements();
  if (!selector) {
    return;
  }

  selector.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = visibleJourneys.length === 0 ? "Search for journeys" : "Choose a journey";
  placeholder.selected = !journeyState.selectedJourneyId;
  selector.appendChild(placeholder);
  if (visibleJourneys.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No matching journeys";
    selector.appendChild(option);
    selector.disabled = true;
    return;
  }

  selector.disabled = false;
  for (const journey of visibleJourneys) {
    const option = document.createElement("option");
    option.value = journey.id;
    option.textContent = journey.title;
    option.selected = journey.id === journeyState.selectedJourneyId;
    selector.appendChild(option);
  }
}

function renderJourneyOverview(journey) {
  const { title, description, primaryPassages, note, metadata, metadataTestament, metadataCategory, metadataEra, metadataBookRange, metadataTags } = getElements();
  if (title) {
    title.textContent = journey?.title || "Search for a journey";
  }
  if (description) {
    description.textContent = journey?.description || "Pick a journey from the selector or search to load the 3D view.";
  }
  if (primaryPassages) {
    primaryPassages.innerHTML = "";
    for (const passage of journey?.primaryPassages || []) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "journey-passage-pill journey-passage-pill--button";
      chip.textContent = passage;
      chip.addEventListener("click", () => openJourneyPassage(passage));
      primaryPassages.appendChild(chip);
    }
  }
  if (note) {
    const noteText = journey
      ? [journey.confidence ? `Confidence: ${journey.confidence}.` : "", journey.caution || ""].filter(Boolean).join(" ")
      : "No journey is selected yet.";
    note.hidden = !noteText;
    note.textContent = noteText;
  }
  if (metadata) {
    const chips = [
      [metadataTestament, journey?.testament || "Search first"],
      [metadataCategory, journey?.category || "Search first"],
      [metadataEra, journey?.era || "Search first"],
      [metadataBookRange, Array.isArray(journey?.bookRange) ? journey.bookRange.join(" • ") : "Search first"],
      [metadataTags, Array.isArray(journey?.tags) ? journey.tags.join(" • ") : "Search first"],
    ];
    for (const [element, value] of chips) {
      if (!element) {
        continue;
      }
      element.textContent = value;
    }
    metadata.hidden = !journey;
  }
}

function renderLayerControls() {
  const { layerControls } = getElements();
  if (!layerControls) {
    return;
  }

  if (!journeyState.mapLayers.length) {
    layerControls.innerHTML = '<p class="journey-layer-empty">No context layers are available yet.</p>';
    return;
  }

  const activePeriod = getActivePeriodFilter();
  layerControls.innerHTML = journeyState.mapLayers
    .map((layer) => {
      const visible = isLayerVisible(layer);
      const featureCount = getVisibleLayerFeatures(layer).length;
      const totalCount = layer.features.length;
      const periodNote = activePeriod
        ? `<span class="journey-layer-toggle-filter">Filtered by ${escapeHtml(activePeriod)}</span>`
        : "";
      return `
        <label class="journey-layer-toggle">
          <input type="checkbox" data-journey-layer-toggle data-layer-id="${escapeHtml(layer.id)}" ${visible ? "checked" : ""}>
          <span class="journey-layer-toggle-main">
            <span class="journey-layer-toggle-title">${escapeHtml(layer.title)}</span>
            <span class="journey-layer-toggle-meta">${escapeHtml(String(featureCount))}/${escapeHtml(String(totalCount))} visible</span>
          </span>
          <span class="journey-layer-toggle-description">${escapeHtml(layer.description || "")}</span>
          ${periodNote}
        </label>
      `;
    })
    .join("");
}

function renderLayerFeatureDetail() {
  const {
    layerDetailTitle,
    layerDetailConfidence,
    layerDetailSubtitle,
    layerDetailBody,
    layerDetailDescription,
    layerDetailNote,
    layerOpenPassage,
  } = getElements();

  if (!layerDetailTitle || !layerDetailConfidence || !layerDetailSubtitle || !layerDetailBody || !layerDetailDescription || !layerDetailNote || !layerOpenPassage) {
    return;
  }

  const selection = getSelectedLayerFeature();
  layerDetailBody.innerHTML = "";
  layerDetailNote.hidden = true;
  layerDetailNote.textContent = "";

  if (!selection) {
    layerDetailTitle.textContent = "Select a context feature";
    layerDetailConfidence.textContent = "--";
    layerDetailConfidence.className = "journey-detail-confidence journey-confidence-chip";
    layerDetailSubtitle.textContent = "Click a city, region, river, mountain, route, or kingdom to inspect it here.";
    layerDetailDescription.textContent = "Context layer details will appear here.";
    const dl = document.createElement("dl");
    for (const [label, value] of [
      ["Layer", "Not selected"],
      ["Periods", "Not provided"],
      ["Passages", "Not provided"],
    ]) {
      const [dt, dd] = renderDetailBodyRow(label, value);
      dl.appendChild(dt);
      dl.appendChild(dd);
    }
    layerDetailBody.appendChild(dl);
    layerOpenPassage.disabled = true;
    layerOpenPassage.textContent = "Open Passage";
    layerOpenPassage.dataset.kind = "";
    return;
  }

  const { layer, feature } = selection;
  layerDetailTitle.textContent = feature.name;
  layerDetailConfidence.textContent = feature.confidence || "unknown";
  layerDetailConfidence.className = `journey-detail-confidence journey-confidence-chip confidence-${normalizeConfidence(feature.confidence)}`;
  layerDetailSubtitle.textContent = `${layer.title} · ${feature.periods?.length ? feature.periods.join(" • ") : "No period tags provided"}`;
  layerDetailDescription.textContent = feature.summary || feature.description || "No context description is available.";
  const dl = document.createElement("dl");
  const detailRows = [
    { label: "Layer", value: layer.title },
    { label: "Periods", value: feature.periods?.length ? feature.periods.join(" • ") : "Not provided" },
  ];
  if (feature.description && feature.description !== layerDetailDescription.textContent) {
    detailRows.push({ label: "Description", value: feature.description });
  }
  detailRows.push({ label: "Passages", value: "" });
  const passagesDd = appendDetailRows(dl, detailRows).get("Passages");
  if (passagesDd) {
    passagesDd.replaceChildren(renderChipList(feature.passages || []));
  }
  layerDetailBody.appendChild(dl);
  if (feature.caution) {
    layerDetailNote.hidden = false;
    layerDetailNote.textContent = feature.caution;
  }
  layerOpenPassage.disabled = !Array.isArray(feature.passages) || feature.passages.length === 0;
  layerOpenPassage.textContent = "Open Passage";
  layerOpenPassage.dataset.kind = "layer";
}

function renderPlaybackControls(journey) {
  const {
    playButton,
    pauseButton,
    previousButton,
    nextButton,
    restartButton,
    speedSelect,
    progressLabel,
    progressBar,
    progressPercent,
    progressValue,
    playbackState,
  } = getElements();

  if (!playButton || !pauseButton || !previousButton || !nextButton || !restartButton || !speedSelect || !progressLabel || !progressBar || !progressPercent || !progressValue || !playbackState) {
    return;
  }

  const orderedStops = getOrderedJourneyStops(journey);
  const totalStops = orderedStops.length;
  const hasStops = totalStops > 0;
  const activeIndex = Math.max(0, Math.min(journeyState.currentStopIndex || 0, Math.max(totalStops - 1, 0)));
  const activeStop = orderedStops[activeIndex] || null;

  playButton.disabled = !hasStops || journeyState.isPlaying;
  pauseButton.disabled = !hasStops || !journeyState.isPlaying;
  previousButton.disabled = !hasStops || activeIndex <= 0;
  nextButton.disabled = !hasStops || activeIndex >= totalStops - 1;
  restartButton.disabled = !hasStops;
  speedSelect.disabled = !hasStops;

  if (speedSelect.value !== journeyState.playbackSpeed) {
    speedSelect.value = journeyState.playbackSpeed;
  }

  const playbackLabel = hasStops && activeStop
    ? `Stop ${activeIndex + 1} of ${totalStops} — ${activeStop.name}`
    : "No journey stops available";
  const progress = totalStops > 1 ? Math.round((activeIndex / (totalStops - 1)) * 100) : hasStops ? 100 : 0;

  playbackState.textContent = journeyState.isPlaying ? "Playing" : "Paused";
  progressLabel.textContent = playbackLabel;
  progressPercent.textContent = `${progress}%`;
  progressValue.style.width = `${progress}%`;
  progressBar.setAttribute("aria-valuenow", String(progress));
  progressBar.setAttribute("aria-valuetext", playbackLabel);
  progressBar.setAttribute("aria-disabled", String(!hasStops));
}

function renderStopList(journey) {
  const { stopList, stopCount } = getElements();
  if (!stopList) {
    return;
  }

  const orderedStops = getOrderedJourneyStops(journey);
  stopList.innerHTML = "";
  for (const stop of orderedStops) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "journey-list-item";
    button.dataset.stopId = stop.id;
    button.setAttribute("aria-pressed", String(stop.id === journeyState.selectedStopId || stop.id === journeyState.activeStopId));
    button.addEventListener("click", () => selectStop(stop.id, { flyTo: true }));

    const order = document.createElement("span");
    order.className = `journey-stop-order ${Number.isFinite(stop.order) ? "" : "is-missing"}`.trim();
    order.textContent = Number.isFinite(stop.order) ? String(stop.order) : "•";

    const meta = document.createElement("div");
    meta.className = "journey-list-item-meta";

    const title = document.createElement("div");
    title.className = "journey-list-item-title";
    title.textContent = stop.name;

    const subtitle = document.createElement("div");
    subtitle.className = "journey-list-item-subtitle";
    const summaryParts = [];
    if (stop.region) {
      summaryParts.push(stop.region);
    }
    if (stop.modernLocation) {
      summaryParts.push(stop.modernLocation);
    }
    if (stop.passages?.length) {
      summaryParts.push(stop.passages.join(" • "));
    }
    subtitle.textContent = summaryParts.join(" · ");

    meta.appendChild(title);
    meta.appendChild(subtitle);
    button.appendChild(order);
    button.appendChild(meta);
    stopList.appendChild(button);
  }

  if (stopCount) {
    stopCount.textContent = String(orderedStops.length || 0);
  }
}

function renderSegmentList(journey) {
  const { segmentList, segmentCount } = getElements();
  if (!segmentList) {
    return;
  }

  segmentList.innerHTML = "";
  for (const segment of journey?.segments || []) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "journey-list-item";
    button.dataset.segmentId = segment.id;
    button.setAttribute("aria-pressed", String(segment.id === journeyState.selectedSegmentId || segment.id === journeyState.activeSegmentId));
    button.addEventListener("click", () => selectSegment(segment.id, { focus: true }));

    const meta = document.createElement("div");
    meta.className = "journey-list-item-meta";

    const title = document.createElement("div");
    title.className = "journey-list-item-title";
    title.textContent = segment.label;

    const subtitle = document.createElement("div");
    subtitle.className = "journey-list-item-subtitle";
    const from = journey.stops.find((stop) => stop.id === segment.from);
    const to = journey.stops.find((stop) => stop.id === segment.to);
    const route = `${from?.name || segment.from} → ${to?.name || segment.to}`;
    const passages = segment.passages?.length ? segment.passages.join(" • ") : "";
    subtitle.textContent = [route, passages].filter(Boolean).join(" · ");

    meta.appendChild(title);
    meta.appendChild(subtitle);
    button.appendChild(meta);
    segmentList.appendChild(button);
  }

  if (segmentCount) {
    segmentCount.textContent = String(journey?.segments?.length || 0);
  }
}

function renderDetailBodyRow(label, value) {
  const dt = document.createElement("dt");
  dt.textContent = label;
  const dd = document.createElement("dd");
  dd.textContent = value || "Not provided";
  return [dt, dd];
}

function appendDetailRows(list, rows) {
  const refs = new Map();
  for (const row of rows) {
    const [dt, dd] = renderDetailBodyRow(row.label, row.value);
    list.appendChild(dt);
    list.appendChild(dd);
    refs.set(row.label, dd);
  }
  return refs;
}

function renderChipList(values) {
  const wrap = document.createElement("div");
  wrap.className = "journey-chip-list";
  for (const value of values.filter(Boolean)) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "journey-passage-pill journey-passage-pill--button";
    chip.textContent = value;
    chip.addEventListener("click", () => openJourneyPassage(value));
    wrap.appendChild(chip);
  }
  if (wrap.childElementCount === 0) {
    const empty = document.createElement("span");
    empty.className = "journey-passage-pill";
    empty.textContent = "Not provided";
    wrap.appendChild(empty);
  }
  return wrap;
}

function renderSelectedDetail(journey) {
  const {
    detailTitle,
    detailConfidence,
    detailSubtitle,
    detailBody,
    detailDescription,
    detailNote,
    openPassage,
  } = getElements();

  if (!detailTitle || !detailConfidence || !detailSubtitle || !detailBody || !detailDescription || !detailNote || !openPassage) {
    return;
  }

  const selectedStop = getSelectedStop(journey);
  const selectedSegment = getSelectedSegment(journey);
  detailBody.innerHTML = "";
  detailNote.hidden = true;
  detailNote.textContent = "";

  if (selectedSegment) {
    const from = journey.stops.find((stop) => stop.id === selectedSegment.from);
    const to = journey.stops.find((stop) => stop.id === selectedSegment.to);
    detailTitle.textContent = selectedSegment.label;
    detailConfidence.textContent = selectedSegment.confidence || journey.confidence || "unknown";
    detailConfidence.className = `journey-detail-confidence journey-confidence-chip confidence-${normalizeConfidence(selectedSegment.confidence || journey.confidence)}`;
    detailSubtitle.textContent = `${from?.name || selectedSegment.from} → ${to?.name || selectedSegment.to}`;
    detailDescription.textContent = selectedSegment.description || "No segment description is available.";
    const dl = document.createElement("dl");
    const passagesDd = appendDetailRows(dl, [
      { label: "Passages", value: "" },
      { label: "Route", value: `${from?.name || selectedSegment.from} → ${to?.name || selectedSegment.to}` },
      { label: "Segment ID", value: selectedSegment.id },
    ]).get("Passages");
    if (passagesDd) {
      passagesDd.replaceChildren(renderChipList(selectedSegment.passages || []));
    }
    detailBody.appendChild(dl);
    if (selectedSegment.caution) {
      detailNote.hidden = false;
      detailNote.textContent = selectedSegment.caution;
    } else if (journey.caution) {
      detailNote.hidden = false;
      detailNote.textContent = journey.caution;
    }
    openPassage.disabled = false;
    openPassage.textContent = "Open Passage";
    openPassage.dataset.kind = "segment";
    return;
  }

  if (selectedStop) {
    detailTitle.textContent = selectedStop.name;
    detailConfidence.textContent = selectedStop.confidence || journey.confidence || "unknown";
    detailConfidence.className = `journey-detail-confidence journey-confidence-chip confidence-${normalizeConfidence(selectedStop.confidence || journey.confidence)}`;
    const subtitleParts = [];
    if (Number.isFinite(selectedStop.order)) {
      subtitleParts.push(`Stop ${selectedStop.order}`);
    }
    if (selectedStop.region) {
      subtitleParts.push(selectedStop.region);
    }
    detailSubtitle.textContent = subtitleParts.join(" · ") || "Selected stop";
    detailDescription.textContent = selectedStop.description || "No stop description is available.";
    const dl = document.createElement("dl");
    const passagesDd = appendDetailRows(dl, [
      { label: "Order", value: Number.isFinite(selectedStop.order) ? String(selectedStop.order) : "Not provided" },
      { label: "Region", value: selectedStop.region || "Not provided" },
      { label: "Modern location", value: selectedStop.modernLocation || "Not provided" },
      { label: "Passages", value: "" },
      { label: "Notes", value: selectedStop.notes || "Not provided" },
    ]).get("Passages");
    if (passagesDd) {
      passagesDd.replaceChildren(renderChipList(selectedStop.passages || []));
    }
    detailBody.appendChild(dl);
    if (selectedStop.caution) {
      detailNote.hidden = false;
      detailNote.textContent = selectedStop.caution;
    } else if (journey.caution) {
      detailNote.hidden = false;
      detailNote.textContent = journey.caution;
    }
    openPassage.disabled = false;
    openPassage.textContent = "Open Passage";
    openPassage.dataset.kind = "stop";
    return;
  }

  detailTitle.textContent = "Select a stop or segment";
  detailConfidence.textContent = "--";
  detailConfidence.className = "journey-detail-confidence journey-confidence-chip";
  detailSubtitle.textContent = "Click a stop or segment to inspect details here.";
  detailDescription.textContent = "The detail card updates when you pick a stop or segment.";
  const dl = document.createElement("dl");
  for (const [label, value] of [
    ["Journey", journey?.title || "Not available"],
    ["Primary passages", (journey?.primaryPassages || []).join(" • ") || "Not provided"],
  ]) {
    const parts = renderDetailBodyRow(label, value);
    parts.forEach((node) => dl.appendChild(node));
  }
  detailBody.appendChild(dl);
  openPassage.disabled = true;
  openPassage.textContent = "Open Passage";
  openPassage.dataset.kind = "";
}

function renderJourneyUi() {
  const journey = getSelectedJourney();
  const visibleJourneys = getVisibleJourneys();
  renderJourneyLibraryFilters(visibleJourneys);
  renderJourneySelector(visibleJourneys);
  renderJourneyOverview(journey);
  renderLayerControls();
  renderPlaybackControls(journey);
  renderStopList(journey);
  renderSegmentList(journey);
  renderSelectedDetail(journey);
  renderLayerFeatureDetail();
  syncListStates();
}

function updateJourneyFilters({ search, testament, category, era } = {}) {
  if (typeof search === "string") {
    journeyState.journeySearch = search;
  }
  if (typeof testament === "string") {
    journeyState.journeyTestament = testament;
  }
  if (typeof category === "string") {
    journeyState.journeyCategory = category;
  }
  if (typeof era === "string") {
    journeyState.journeyEra = era;
  }
}

function handleJourneyFilterChange() {
  syncJourneySelectionToVisibleJourneys();
  refreshJourneyUi({ zoom: false });
}

function syncListStates() {
  const { stopList, segmentList } = getElements();
  if (stopList) {
    stopList.querySelectorAll("[data-stop-id]").forEach((button) => {
      const isSelected = button.dataset.stopId === journeyState.selectedStopId;
      const isActive = button.dataset.stopId === journeyState.activeStopId;
      button.classList.toggle("is-selected", isSelected);
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", String(isSelected || isActive));
    });
  }
  if (segmentList) {
    segmentList.querySelectorAll("[data-segment-id]").forEach((button) => {
      const isSelected = button.dataset.segmentId === journeyState.selectedSegmentId;
      const isActive = button.dataset.segmentId === journeyState.activeSegmentId;
      button.classList.toggle("is-selected", isSelected);
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", String(isSelected || isActive));
    });
  }
}

function syncEntityStyles() {
  const journey = getSelectedJourney();
  if (!journeyState.viewer) {
    return;
  }

  if (journey) {
    for (const stop of journey.stops) {
      const entity = journeyState.stopEntities.get(stop.id);
      if (!entity) {
        continue;
      }
      entity.billboard.image = buildStopPinSvg(stop, {
        selected: stop.id === journeyState.selectedStopId,
        active: stop.id === journeyState.activeStopId,
      });
    }
    for (const segment of journey.segments) {
      const entity = journeyState.segmentEntities.get(segment.id);
      if (!entity) {
        continue;
      }
      entity.polyline.material = buildSegmentMaterial({
        selected: segment.id === journeyState.selectedSegmentId,
        active: segment.id === journeyState.activeSegmentId,
      });
      entity.polyline.width = segment.id === journeyState.selectedSegmentId ? 8 : segment.id === journeyState.activeSegmentId ? 7 : 5;
    }
  }

  const activePeriod = getActivePeriodFilter();
  for (const [layerId, featureMap] of journeyState.layerEntities.entries()) {
    const layer = journeyState.mapLayers.find((item) => item.id === layerId);
    if (!layer) {
      continue;
    }
    const layerVisible = isLayerVisible(layer);
    for (const [featureId, entity] of featureMap.entries()) {
      const feature = entity.__bhfLayerFeature || null;
      const visible = Boolean(layerVisible && (!activePeriod || featureMatchesActivePeriod(feature)));
      entity.show = visible;
      if (!visible || !feature) {
        continue;
      }
      const isSelected = getLayerFeatureKey(layer.id, feature.id) === journeyState.selectedLayerFeatureId;
      entity.label = entity.label || {};
      entity.description = feature.description || "";
      if (layer.type === "points") {
        entity.billboard.image = buildLayerPointSvg(feature, layer, {
          selected: isSelected,
        });
      } else if (layer.type === "lines") {
        entity.polyline.material = buildLayerLineMaterial(layer, feature, {
          selected: isSelected,
        });
        entity.polyline.width = isSelected ? 7 : 5;
      } else if (layer.type === "polygons") {
        entity.polygon.material = buildLayerPolygonMaterial(layer, feature, {
          selected: isSelected,
        });
        entity.polygon.outlineColor = buildLayerStrokeColor(layer, feature, {
          selected: isSelected,
        });
      }
    }
  }
}

function syncLayerEntityStyles() {
  syncEntityStyles();
}

function buildJourneyBounds(Cesium, stops) {
  const positions = stops
    .filter((stop) => Number.isFinite(stop.lat) && Number.isFinite(stop.lng))
    .map((stop) => Cesium.Cartesian3.fromDegrees(stop.lng, stop.lat, 240000));
  if (positions.length === 0) {
    return null;
  }
  return Cesium.BoundingSphere.fromPoints(positions);
}

function buildLayerPositions(Cesium, feature) {
  if (Array.isArray(feature.points) && feature.points.length > 0) {
    return feature.points.map((point) => Cesium.Cartesian3.fromDegrees(point[1], point[0], 12000));
  }
  if (isFiniteNumber(feature.lat) && isFiniteNumber(feature.lng)) {
    return [Cesium.Cartesian3.fromDegrees(feature.lng, feature.lat, 12000)];
  }
  return [];
}

function buildLayerBounds(Cesium, feature) {
  const positions = buildLayerPositions(Cesium, feature);
  if (positions.length === 0) {
    return null;
  }
  return Cesium.BoundingSphere.fromPoints(positions);
}

function findJourneyEntityCollections() {
  return Array.from(journeyState.journeyEntities.values()).filter(Boolean);
}

function removeJourneyEntities() {
  if (!journeyState.viewer) {
    journeyState.journeyEntities.clear();
    journeyState.stopEntities.clear();
    journeyState.segmentEntities.clear();
    return;
  }
  for (const entity of findJourneyEntityCollections()) {
    journeyState.viewer.entities.remove(entity);
  }
  journeyState.journeyEntities.clear();
  journeyState.stopEntities.clear();
  journeyState.segmentEntities.clear();
}

function ensureLayerEntityRecord(layer) {
  if (!journeyState.layerEntities.has(layer.id)) {
    journeyState.layerEntities.set(layer.id, new Map());
  }
  return journeyState.layerEntities.get(layer.id);
}

function createLayerFeatureEntity(layer, feature, Cesium) {
  const visible = isLayerVisible(layer) && featureMatchesActivePeriod(feature);
  const key = getLayerFeatureKey(layer.id, feature.id);
  const common = {
    id: key,
    name: feature.name,
    description: feature.description || "",
  };

  if (layer.type === "points") {
    return journeyState.viewer.entities.add({
      ...common,
      position: Cesium.Cartesian3.fromDegrees(feature.lng, feature.lat, 15000),
      billboard: {
        image: buildLayerPointSvg(feature, layer, {
          selected: key === journeyState.selectedLayerFeatureId,
        }),
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        width: 28,
        height: 36,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: feature.name,
        font: "700 12px system-ui, sans-serif",
        fillColor: buildLayerTint(layer, feature, { selected: key === journeyState.selectedLayerFeatureId }),
        outlineColor: Cesium.Color.fromCssColorString("#17364d"),
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        showBackground: true,
        backgroundColor: Cesium.Color.fromAlpha(Cesium.Color.fromCssColorString("#ffffff"), 0.72),
        backgroundPadding: new Cesium.Cartesian2(6, 4),
        pixelOffset: new Cesium.Cartesian2(0, 18),
        verticalOrigin: Cesium.VerticalOrigin.TOP,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      show: visible,
    });
  }

  if (layer.type === "lines") {
    return journeyState.viewer.entities.add({
      ...common,
      polyline: {
        positions: buildLayerPositions(Cesium, feature),
        width: key === journeyState.selectedLayerFeatureId ? 7 : 5,
        arcType: Cesium.ArcType.NONE,
        clampToGround: false,
        material: buildLayerLineMaterial(layer, feature, {
          selected: key === journeyState.selectedLayerFeatureId,
        }),
      },
      show: visible,
    });
  }

  const positions = buildLayerPositions(Cesium, feature);
  return journeyState.viewer.entities.add({
    ...common,
    polygon: {
      hierarchy: positions,
      material: buildLayerPolygonMaterial(layer, feature, {
        selected: key === journeyState.selectedLayerFeatureId,
      }),
      outline: true,
      outlineColor: buildLayerStrokeColor(layer, feature, {
        selected: key === journeyState.selectedLayerFeatureId,
      }),
      extrudedHeight: 0,
    },
    show: visible,
  });
}

function loadMapLayerIntoViewer(layer) {
  if (!journeyState.viewer || !window.Cesium || !layer) {
    return;
  }
  const Cesium = window.Cesium;
  const featureMap = ensureLayerEntityRecord(layer);
  for (const feature of layer.features) {
    const key = getLayerFeatureKey(layer.id, feature.id);
    let entity = featureMap.get(feature.id);
    if (!entity) {
      entity = createLayerFeatureEntity(layer, feature, Cesium);
      entity.__bhfKind = "layer-feature";
      entity.__bhfLayerId = layer.id;
      entity.__bhfLayerFeatureId = feature.id;
      entity.__bhfLayerFeatureKey = key;
      entity.__bhfLayer = layer;
      entity.__bhfLayerFeature = feature;
      featureMap.set(feature.id, entity);
      journeyState.layerFeatureIndex.set(key, { layer, feature, entity });
      journeyState.journeyEntities.add(entity);
      continue;
    }
    entity.__bhfLayerFeature = feature;
    entity.__bhfLayer = layer;
  }
}

function loadMapLayersIntoViewer() {
  if (!journeyState.viewer || !window.Cesium) {
    return;
  }
  // Future phase: timeline slider can filter these overlays by period.
  // Future phase: archaeology layer can share the same visibility stack.
  // Future phase: AI narration can reference the currently visible layers.
  // Future phase: richer GIS datasets can replace these curated overlays.
  // Future phase: confidence/source citation model can annotate each feature.
  // Future phase: localStorage layer preferences can persist toggle state.
  for (const layer of journeyState.mapLayers) {
    loadMapLayerIntoViewer(layer);
  }
  syncLayerEntityStyles();
  journeyState.viewer.scene.requestRender();
}

function fitJourney() {
  const journey = getSelectedJourney();
  if (!journeyState.viewer || !window.Cesium || !journey) {
    return;
  }
  const bounds = buildJourneyBounds(window.Cesium, journey.stops);
  if (!bounds) {
    return;
  }
  journeyState.viewer.camera.flyToBoundingSphere(bounds, {
    duration: 1.1,
    offset: new window.Cesium.HeadingPitchRange(0, window.Cesium.Math.toRadians(-40), bounds.radius * 2.0),
  });
}

function showGlobeOverview() {
  if (!journeyState.viewer || !window.Cesium) {
    return;
  }
  journeyState.viewer.scene.globe.show = true;
  journeyState.viewer.scene.skyBox.show = false;
  journeyState.viewer.camera.flyTo({
    destination: window.Cesium.Cartesian3.fromDegrees(18, 24, 12000000),
    orientation: {
      heading: window.Cesium.Math.toRadians(0),
      pitch: window.Cesium.Math.toRadians(-55),
      roll: 0,
    },
    duration: 0.8,
  });
}

function flyToStop(stop) {
  if (!journeyState.viewer || !window.Cesium || !stop) {
    return;
  }
  journeyState.viewer.camera.flyTo({
    destination: window.Cesium.Cartesian3.fromDegrees(stop.lng, stop.lat, 350000),
    orientation: {
      heading: window.Cesium.Math.toRadians(0),
      pitch: window.Cesium.Math.toRadians(-40),
      roll: 0,
    },
    duration: 1.0,
  });
}

function focusSegment(segment) {
  const journey = getSelectedJourney();
  if (!journeyState.viewer || !window.Cesium || !journey || !segment) {
    return;
  }
  const from = journey.stops.find((stop) => stop.id === segment.from);
  const to = journey.stops.find((stop) => stop.id === segment.to);
  const positions = [from, to]
    .filter(Boolean)
    .map((stop) => window.Cesium.Cartesian3.fromDegrees(stop.lng, stop.lat, 350000));
  if (positions.length === 0) {
    return;
  }
  const bounds = window.Cesium.BoundingSphere.fromPoints(positions);
  journeyState.viewer.camera.flyToBoundingSphere(bounds, {
    duration: 1.0,
    offset: new window.Cesium.HeadingPitchRange(0, window.Cesium.Math.toRadians(-35), bounds.radius * 2.2),
  });
}

function flyToLayerFeature(layer, feature) {
  if (!journeyState.viewer || !window.Cesium || !layer || !feature) {
    return;
  }
  if (layer.type === "points" && isFiniteNumber(feature.lat) && isFiniteNumber(feature.lng)) {
    journeyState.viewer.camera.flyTo({
      destination: window.Cesium.Cartesian3.fromDegrees(feature.lng, feature.lat, 320000),
      orientation: {
        heading: window.Cesium.Math.toRadians(0),
        pitch: window.Cesium.Math.toRadians(-40),
        roll: 0,
      },
      duration: 1.0,
    });
    return;
  }
  const bounds = buildLayerBounds(window.Cesium, feature);
  if (!bounds) {
    return;
  }
  journeyState.viewer.camera.flyToBoundingSphere(bounds, {
    duration: 1.0,
    offset: new window.Cesium.HeadingPitchRange(0, window.Cesium.Math.toRadians(-35), bounds.radius * 2.1),
  });
}

async function openJourneyPassage(reference) {
  const journey = getSelectedJourney();
  const selectedStop = getSelectedStop(journey);
  const selectedSegment = getSelectedSegment(journey);
  const passageReference =
    String(reference || "").trim() ||
    selectedStop?.passages?.[0] ||
    selectedSegment?.passages?.[0] ||
    journey?.primaryPassages?.[0] ||
    "";
  if (!passageReference) {
    console.info("[BHF Journey] No passage reference is available for the current selection.", {
      journeyId: journey?.id || "",
      selectedStopId: selectedStop?.id || "",
      selectedSegmentId: selectedSegment?.id || "",
    });
    return false;
  }

  if (window.BHFReader && typeof window.BHFReader.openPassageReference === "function") {
    await window.BHFReader.openPassageReference(passageReference);
    return true;
  }

  console.info("[BHF Journey] TODO Phase 6: open passage from journey detail", {
    journeyId: journey?.id || "",
    selectedStopId: selectedStop?.id || "",
    selectedSegmentId: selectedSegment?.id || "",
    passageReference,
  });
  return false;
}

async function openLayerPassagePlaceholder() {
  const selection = getSelectedLayerFeature();
  const passageReference = selection?.feature?.passages?.[0] || "";
  if (!passageReference) {
    console.info("[BHF Layer] No passage reference is available for the current context selection.", {
      layerId: selection?.layer?.id || "",
      featureId: selection?.feature?.id || "",
    });
    return false;
  }
  if (window.BHFReader && typeof window.BHFReader.openPassageReference === "function") {
    await window.BHFReader.openPassageReference(passageReference);
    return true;
  }
  console.info("[BHF Layer] TODO Phase 7: open passage from layer detail", {
    layerId: selection?.layer?.id || "",
    featureId: selection?.feature?.id || "",
    passageReference,
  });
  return false;
}

function resetPlaybackForJourney(journey) {
  pausePlayback();
  const orderedStops = journey ? getOrderedJourneyStops(journey) : [];
  const firstStop = orderedStops[0] || null;
  journeyState.currentStopIndex = 0;
  journeyState.activeStopId = firstStop?.id || "";
  journeyState.activeSegmentId = "";
  journeyState.selectedStopId = firstStop?.id || "";
  journeyState.selectedSegmentId = "";
}

function clearSelectionsForJourneyChange(journey) {
  journeyState.selectedJourneyId = journey?.id || "";
  resetPlaybackForJourney(journey);
}

function loadJourneyIntoViewer(journey) {
  if (!journeyState.viewer || !window.Cesium || !journey) {
    return;
  }

  removeJourneyEntities();

  const Cesium = window.Cesium;
  const stopById = new Map(journey.stops.map((stop) => [stop.id, stop]));

  for (const stop of journey.stops) {
    const entity = journeyState.viewer.entities.add({
      id: stop.id,
      name: stop.name,
      position: Cesium.Cartesian3.fromDegrees(stop.lng, stop.lat, 18000),
      billboard: {
        image: buildStopPinSvg(stop, {
          selected: stop.id === journeyState.selectedStopId,
          active: stop.id === journeyState.activeStopId,
        }),
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        width: 30,
        height: 38,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: Number.isFinite(stop.order) ? `${stop.order}` : stop.name,
        font: "700 13px system-ui, sans-serif",
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.fromCssColorString("#17364d"),
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        showBackground: true,
        backgroundColor: Cesium.Color.fromAlpha(Cesium.Color.fromCssColorString("#163f5d"), 0.72),
        backgroundPadding: new Cesium.Cartesian2(8, 4),
        pixelOffset: new Cesium.Cartesian2(0, 18),
        verticalOrigin: Cesium.VerticalOrigin.TOP,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
    entity.__bhfKind = "stop";
    entity.__bhfStopId = stop.id;
    journeyState.stopEntities.set(stop.id, entity);
    journeyState.journeyEntities.add(entity);
  }

  // Future phase: playback animation can follow the active stop step more precisely.
  // Future phase: timeline synchronization can tie journey steps to scripture dates.
  // Future phase: scripture reader synchronization can highlight passages per step.
  // Future phase: smooth route-following animation can move along route legs.
  // Future phase: AI narration can attach guidance to each playback step.
  // Future phase: archaeology layer synchronization can attach context to stops.
  for (const segment of journey.segments) {
    const from = stopById.get(segment.from);
    const to = stopById.get(segment.to);
    if (!from || !to) {
      continue;
    }
    const entity = journeyState.viewer.entities.add({
      id: segment.id,
      name: segment.label,
      description: segment.description || "",
      polyline: {
        positions: [
          Cesium.Cartesian3.fromDegrees(from.lng, from.lat, 22000),
          Cesium.Cartesian3.fromDegrees(to.lng, to.lat, 22000),
        ],
        width: segment.id === journeyState.selectedSegmentId ? 8 : segment.id === journeyState.activeSegmentId ? 7 : 5,
        arcType: Cesium.ArcType.NONE,
        clampToGround: false,
        material: buildSegmentMaterial({
          selected: segment.id === journeyState.selectedSegmentId,
          active: segment.id === journeyState.activeSegmentId,
        }),
      },
    });
    entity.__bhfKind = "segment";
    entity.__bhfSegmentId = segment.id;
    journeyState.segmentEntities.set(segment.id, entity);
    journeyState.journeyEntities.add(entity);
  }

  syncEntityStyles();
  journeyState.viewer.scene.requestRender();
}

function refreshJourneyUi({ zoom = false } = {}) {
  const journey = getSelectedJourney();
  if (!journey) {
    setStatus("No valid journeys are available.", "error");
    return;
  }
  renderJourneyUi();
  syncEntityStyles();
  if (journeyState.viewerReady && journeyState.viewer) {
    if (zoom) {
      fitJourney();
    }
    journeyState.viewer.scene.requestRender();
  }
}

function selectJourney(journeyId) {
  const journey = journeyState.journeys.find((item) => item.id === journeyId);
  if (!journey) {
    return;
  }
  clearSelectionsForJourneyChange(journey);
  refreshJourneyUi({ zoom: true });
  loadJourneyIntoViewer(journey);
}

function selectStop(stopId, { flyTo = false } = {}) {
  const journey = getSelectedJourney();
  if (!journey) {
    return;
  }
  pausePlayback();
  const orderedStops = getOrderedJourneyStops(journey);
  const stop = orderedStops.find((item) => item.id === stopId) || journey.stops.find((item) => item.id === stopId);
  if (!stop) {
    return;
  }
  journeyState.selectedStopId = stop.id;
  journeyState.activeStopId = stop.id;
  journeyState.activeSegmentId = "";
  journeyState.selectedSegmentId = "";
  journeyState.selectedLayerFeatureId = "";
  journeyState.currentStopIndex = Math.max(0, getPlaybackStopIndex(journey, stop.id));
  refreshJourneyUi({ zoom: false });
  if (flyTo) {
    flyToStop(stop);
  }
}

function selectSegment(segmentId, { focus = false } = {}) {
  const journey = getSelectedJourney();
  if (!journey) {
    return;
  }
  pausePlayback();
  const segment = journey.segments.find((item) => item.id === segmentId);
  if (!segment) {
    return;
  }
  journeyState.selectedSegmentId = segment.id;
  journeyState.selectedStopId = "";
  journeyState.activeSegmentId = segment.id;
  journeyState.selectedLayerFeatureId = "";
  refreshJourneyUi({ zoom: false });
  if (focus) {
    focusSegment(segment);
  }
}

function selectLayerFeature(layerId, featureId, { flyTo = false } = {}) {
  const layer = journeyState.mapLayers.find((item) => item.id === layerId);
  if (!layer) {
    return;
  }
  const feature = layer.features.find((item) => item.id === featureId);
  if (!feature) {
    return;
  }

  pausePlayback();
  journeyState.selectedLayerFeatureId = getLayerFeatureKey(layer.id, feature.id);
  journeyState.selectedStopId = "";
  journeyState.selectedSegmentId = "";
  journeyState.activeStopId = "";
  journeyState.activeSegmentId = "";
  refreshJourneyUi({ zoom: false });
  if (flyTo && journeyState.viewerReady && journeyState.viewer) {
    flyToLayerFeature(layer, feature);
  }
}

function bindOpenPassage() {
  const { openPassage } = getElements();
  if (!openPassage || openPassage.dataset.bound === "true") {
    return;
  }
  openPassage.dataset.bound = "true";
  openPassage.addEventListener("click", () => openJourneyPassage());
}

function bindLayerOpenPassage() {
  const { layerOpenPassage } = getElements();
  if (!layerOpenPassage || layerOpenPassage.dataset.bound === "true") {
    return;
  }
  layerOpenPassage.dataset.bound = "true";
  layerOpenPassage.addEventListener("click", openLayerPassagePlaceholder);
}

function handleViewerClick(movement) {
  if (!journeyState.viewer || !window.Cesium) {
    return;
  }
  const picked = journeyState.viewer.scene.pick(movement.position);
  const entity = picked && picked.id && typeof picked.id === "object" ? picked.id : null;
  if (!entity) {
    return;
  }
  if (entity.__bhfKind === "stop" && entity.__bhfStopId) {
    selectStop(entity.__bhfStopId, { flyTo: true });
    return;
  }
  if (entity.__bhfKind === "segment" && entity.__bhfSegmentId) {
    selectSegment(entity.__bhfSegmentId, { focus: true });
    return;
  }
  if (entity.__bhfKind === "layer-feature" && entity.__bhfLayerId && entity.__bhfLayerFeatureId) {
    selectLayerFeature(entity.__bhfLayerId, entity.__bhfLayerFeatureId, { flyTo: true });
  }
}

function createViewer(Cesium) {
  if (journeyState.viewer) {
    return journeyState.viewer;
  }

  const { stage } = getElements();
  if (!stage) {
    throw new Error("Journey stage is missing.");
  }

  stage.innerHTML = "";
  const baseLayer = new Cesium.ImageryLayer(buildFallbackGlobeImageryProvider(Cesium));
  const viewer = new Cesium.Viewer(stage, {
    animation: false,
    baseLayerPicker: false,
    baseLayer,
    geocoder: false,
    homeButton: false,
    infoBox: false,
    navigationHelpButton: false,
    sceneModePicker: false,
    selectionIndicator: false,
    timeline: false,
    fullscreenButton: false,
    shouldAnimate: false,
  });

  viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#dfeaf3");
  viewer.scene.skyAtmosphere.show = true;
  viewer.scene.skyBox.show = false;
  viewer.scene.globe.enableLighting = true;
  viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#f4f7fa");
  viewer.scene.globe.translucency.enabled = false;
  viewer.scene.screenSpaceCameraController.enableCollisionDetection = true;
  viewer.cesiumWidget.creditContainer.style.display = "none";

  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
  handler.setInputAction(handleViewerClick, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  journeyState.viewer = viewer;
  return viewer;
}
function handleWorkspaceTabChange(event) {
  if (event?.detail?.tabId !== "journey") {
    return;
  }
  window.requestAnimationFrame(() => {
    initializeJourneyPanel();
  });
}

async function initializeJourneyPanel() {
  const {
    panel,
    selector,
    openPassage,
    layerOpenPassage,
    layerControls,
    playButton,
    pauseButton,
    previousButton,
    nextButton,
    restartButton,
    speedSelect,
    zoomButton,
    searchInput,
    testamentFilter,
    categoryFilter,
    eraFilter,
    expandButton,
    modalCloseButton,
    modal,
  } = getElements();
  if (!panel || journeyState.loading || (panel.dataset.journeyBound === "true" && journeyState.viewerReady)) {
    return;
  }

  panel.dataset.journeyBound = "true";
  journeyState.loading = true;
  setStatus("Loading journey catalog...");

  if (selector && !selector.dataset.bound) {
    selector.dataset.bound = "true";
    selector.addEventListener("change", (event) => selectJourney(event.target.value));
  }
  if (searchInput && !searchInput.dataset.bound) {
    searchInput.dataset.bound = "true";
    searchInput.addEventListener("input", (event) => {
      updateJourneyFilters({ search: event.target.value });
      handleJourneyFilterChange();
    });
  }
  if (testamentFilter && !testamentFilter.dataset.bound) {
    testamentFilter.dataset.bound = "true";
    testamentFilter.addEventListener("change", (event) => {
      updateJourneyFilters({ testament: event.target.value });
      handleJourneyFilterChange();
    });
  }
  if (categoryFilter && !categoryFilter.dataset.bound) {
    categoryFilter.dataset.bound = "true";
    categoryFilter.addEventListener("change", (event) => {
      updateJourneyFilters({ category: event.target.value });
      handleJourneyFilterChange();
    });
  }
  if (eraFilter && !eraFilter.dataset.bound) {
    eraFilter.dataset.bound = "true";
    eraFilter.addEventListener("change", (event) => {
      updateJourneyFilters({ era: event.target.value });
      handleJourneyFilterChange();
    });
  }
  if (openPassage && !openPassage.dataset.bound) {
    openPassage.dataset.bound = "true";
    openPassage.addEventListener("click", () => openJourneyPassage());
  }
  if (layerOpenPassage && !layerOpenPassage.dataset.bound) {
    layerOpenPassage.dataset.bound = "true";
    layerOpenPassage.addEventListener("click", openLayerPassagePlaceholder);
  }
  if (layerControls && !layerControls.dataset.bound) {
    layerControls.dataset.bound = "true";
    layerControls.addEventListener("change", (event) => {
      const checkbox = event.target.closest("[data-journey-layer-toggle]");
      if (!checkbox) {
        return;
      }
      const layerId = checkbox.dataset.layerId || "";
      if (!layerId) {
        return;
      }
      journeyState.layerVisibility[layerId] = Boolean(checkbox.checked);
      if (!journeyState.layerVisibility[layerId] && journeyState.selectedLayerFeatureId.startsWith(`${layerId}:`)) {
        journeyState.selectedLayerFeatureId = "";
      }
      syncLayerEntityStyles();
      renderJourneyUi();
      if (journeyState.viewerReady && journeyState.viewer) {
        journeyState.viewer.scene.requestRender();
      }
    });
  }
  if (playButton && !playButton.dataset.bound) {
    playButton.dataset.bound = "true";
    playButton.addEventListener("click", playPlayback);
  }
  if (pauseButton && !pauseButton.dataset.bound) {
    pauseButton.dataset.bound = "true";
    pauseButton.addEventListener("click", () => {
      pausePlayback();
      refreshJourneyUi({ zoom: false });
    });
  }
  if (previousButton && !previousButton.dataset.bound) {
    previousButton.dataset.bound = "true";
    previousButton.addEventListener("click", () => {
      pausePlayback();
      advancePlayback(-1, { autoplay: false });
    });
  }
  if (nextButton && !nextButton.dataset.bound) {
    nextButton.dataset.bound = "true";
    nextButton.addEventListener("click", () => {
      pausePlayback();
      advancePlayback(1, { autoplay: false });
    });
  }
  if (restartButton && !restartButton.dataset.bound) {
    restartButton.dataset.bound = "true";
    restartButton.addEventListener("click", restartPlayback);
  }
  if (speedSelect && !speedSelect.dataset.bound) {
    speedSelect.dataset.bound = "true";
    speedSelect.addEventListener("change", handlePlaybackSpeedChange);
  }
  if (zoomButton && !zoomButton.dataset.bound) {
    zoomButton.dataset.bound = "true";
    zoomButton.addEventListener("click", fitJourney);
  }
  if (expandButton && !expandButton.dataset.bound) {
    expandButton.dataset.bound = "true";
    expandButton.addEventListener("click", openJourneyModal);
  }
  if (modalCloseButton && !modalCloseButton.dataset.bound) {
    modalCloseButton.dataset.bound = "true";
    modalCloseButton.addEventListener("click", closeJourneyModal);
  }
  if (modal && !modal.dataset.bound) {
    modal.dataset.bound = "true";
    modal.addEventListener("close", finalizeJourneyModalClose);
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeJourneyModal();
      }
    });
  }

  try {
    const [journeys, layerCatalog] = await Promise.all([
      loadJourneys(),
      loadMapLayerCatalog(),
    ]);
  journeyState.journeys = journeys;
    if (journeyState.journeys.length === 0) {
      throw new Error("No valid journey data was found.");
    }
    journeyState.mapLayers = layerCatalog.layers || [];
    for (const layer of journeyState.mapLayers) {
      if (!Object.prototype.hasOwnProperty.call(journeyState.layerVisibility, layer.id)) {
        journeyState.layerVisibility[layer.id] = false;
      }
    }
    journeyState.libraryFacets = {
      categories: getJourneyFacetValues(journeyState.journeys, "category"),
      eras: getJourneyFacetValues(journeyState.journeys, "era"),
      testaments: getJourneyFacetValues(journeyState.journeys, "testament"),
      tags: getJourneyFacetValues(journeyState.journeys, "tags"),
    };
    journeyState.selectedJourneyId = "";
    resetPlaybackForJourney(null);
    renderJourneyUi();
    clearStatus();
  } catch (error) {
    journeyCatalogPromise = null;
    journeyState.loading = false;
    journeyState.viewerReady = false;
    setStatus(error.message || "Could not load the 3D Journey catalog.", "error");
    return;
  }

  try {
    await loadCesiumAssets();
    createViewer(window.Cesium);
    journeyState.viewerReady = true;
    const selectedJourney = getSelectedJourney();
    loadJourneyIntoViewer(selectedJourney);
    loadMapLayersIntoViewer();
    if (selectedJourney) {
      fitJourney();
    } else {
      showGlobeOverview();
    }
    clearStatus();
  } catch (error) {
    cesiumAssetsPromise = null;
    journeyState.viewerReady = false;
    setStatus(error.message || "Could not load the 3D Journey viewer.", "error");
  }

  journeyState.loading = false;
  journeyState.mounted = true;
  bindOpenPassage();
  window.BHFJourneyLayers = {
    setActivePeriod,
    clearActivePeriod: () => setActivePeriod(""),
  };
}

function disposeJourneyPanel() {
  clearPlaybackTimer();
  journeyState.isPlaying = false;
}

document.addEventListener("bhf:workspace-tab-changed", handleWorkspaceTabChange);
window.addEventListener("pagehide", disposeJourneyPanel);
window.addEventListener("beforeunload", disposeJourneyPanel);

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeJourneyPanel);
} else {
  initializeJourneyPanel();
}

// Future phase: journey playback, timeline synchronization, scripture reader
// sync, archaeology overlays, smooth route-following, and AI narration will
// extend this data model without reintroducing hardcoded journey logic.
