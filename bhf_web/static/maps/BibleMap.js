import { renderMapMarkerPopup } from "./MapMarkerPopup.js";
import {
  archaeologyMarkerStyle,
  entityMarkerIcon,
  manuscriptMarkerStyle,
  referenceLayerStyle,
  referencePointIcon,
  routeStyle,
} from "./MapStyles.js";
import {
  renderArchaeologyPopup,
  renderManuscriptPopup,
  renderReferenceFeaturePopup,
  renderRoutePopup,
} from "./MapPopups.js";

// The `map-entity-marker` class remains part of the rendered Leaflet icon markup.
const DEFAULT_CENTER = [31.8, 35.1];
const DEFAULT_ZOOM = 7;
const DEFAULT_TILE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}";
const DEFAULT_TILE_ATTRIBUTION =
  "Tiles &copy; Esri, Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, " +
  "Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom, 2012";

function isTestMode() {
  return Boolean(window.BHFTestMode || document.documentElement?.dataset?.testMode === "true");
}

function buildBounds(markers) {
  const validMarkers = markers.filter(
    (marker) => Number.isFinite(marker.latitude) && Number.isFinite(marker.longitude)
  );
  if (validMarkers.length === 0) {
    return null;
  }
  return validMarkers.map((marker) => [marker.latitude, marker.longitude]);
}

function createTestMapController(container) {
  if (container) {
    container.dataset.testMode = "true";
  }
  const map = {
    setView() {
      return map;
    },
    getZoom() {
      return DEFAULT_ZOOM;
    },
    fitBounds() {
      return map;
    },
    hasLayer() {
      return false;
    },
    addLayer() {
      return map;
    },
    removeLayer() {
      return map;
    },
    panTo() {
      return map;
    },
  };
  return {
    map,
    destroy() {},
    invalidateSize() {},
    fitToContent() {},
    setRouteVisibility() {},
    setArchaeologyVisibility() {},
    setManuscriptVisibility() {},
    setReferenceLayers() {},
    setReferenceLayerVisibility() {},
    setSelectedReferenceFeature() {},
    focusSelection() {},
  };
}

export function createBibleMap(container, markers, options = {}) {
  if (isTestMode() || !window.L) {
    return createTestMapController(container);
  }
  if (!window.L) {
    throw new Error("Leaflet is not loaded.");
  }
  if (!container) {
    throw new Error("Map container is missing.");
  }

  const map = window.L.map(container, {
    zoomControl: true,
    scrollWheelZoom: false,
    attributionControl: true,
  }).setView(options.center || DEFAULT_CENTER, options.zoom || DEFAULT_ZOOM);

  const tileLayer = window.L.tileLayer(options.tileUrl || DEFAULT_TILE_URL, {
    maxZoom: 19,
    attribution: options.tileAttribution || DEFAULT_TILE_ATTRIBUTION,
  });

  tileLayer.addTo(map);

  const markerLayer = window.L.layerGroup().addTo(map);
  const placeLayers = new Map();
  const archaeologyLayer = window.L.layerGroup();
  const archaeologyLayers = new Map();
  const manuscriptLayer = window.L.layerGroup();
  const manuscriptLayers = new Map();
  const routeLayer = window.L.layerGroup();
  const routeLayers = new Map();
  let routeVisibility = Boolean(options.routeVisibility);
  let archaeologyVisibility = Boolean(options.archaeologyVisibility);
  let manuscriptVisibility = Boolean(options.manuscriptVisibility);
  let archaeologyItems = Array.isArray(options.archaeologyMarkers) ? options.archaeologyMarkers.slice() : [];
  let manuscriptItems = Array.isArray(options.manuscriptMarkers) ? options.manuscriptMarkers.slice() : [];
  let routeItems = Array.isArray(options.routes) ? options.routes.slice() : [];
  const referenceLayerGroup = window.L.layerGroup();
  const referenceFeatureLayers = new Map();
  const referenceVisibleLayerIds = new Set(
    Array.isArray(options.referenceLayerIds) ? options.referenceLayerIds.map((value) => String(value)) : []
  );
  let referenceItems = Array.isArray(options.referenceLayers) ? options.referenceLayers.slice() : [];
  let selectedReferenceFeatureKey = String(options.selectedReferenceFeatureKey || "");

  function currentMarkerBounds() {
    return buildBounds(markers);
  }

  function currentRouteBounds() {
    const routeBoundsList = [];
    for (const layer of routeLayers.values()) {
      const layerBounds = layer.getBounds ? layer.getBounds() : null;
      if (layerBounds && layerBounds.isValid()) {
        routeBoundsList.push(layerBounds);
      }
    }
    return routeBoundsList;
  }

  function currentArchaeologyBounds() {
    const archaeologyBoundsList = [];
    for (const layer of archaeologyLayers.values()) {
      const layerBounds = layer.getBounds ? layer.getBounds() : null;
      if (layerBounds && layerBounds.isValid()) {
        archaeologyBoundsList.push(layerBounds);
      }
    }
    return archaeologyBoundsList;
  }

  function currentManuscriptBounds() {
    const manuscriptBoundsList = [];
    for (const manuscript of manuscriptLayers.values()) {
      const layerBounds = manuscript.layer.getBounds ? manuscript.layer.getBounds() : null;
      if (layerBounds && layerBounds.isValid()) {
        manuscriptBoundsList.push(layerBounds);
      }
    }
    return manuscriptBoundsList;
  }

  function currentReferenceBounds() {
    const boundsList = [];
    for (const [key, entry] of referenceFeatureLayers.entries()) {
      if (!referenceVisibleLayerIds.has(entry.layer.id)) {
        continue;
      }
      const layerBounds = entry.leafletLayer.getBounds ? entry.leafletLayer.getBounds() : null;
      if (layerBounds && layerBounds.isValid()) {
        boundsList.push(
          [layerBounds.getSouthWest().lat, layerBounds.getSouthWest().lng],
          [layerBounds.getNorthEast().lat, layerBounds.getNorthEast().lng]
        );
        continue;
      }
      const center = entry.leafletLayer.getLatLng ? entry.leafletLayer.getLatLng() : null;
      if (center) {
        boundsList.push([center.lat, center.lng]);
      }
      if (key === selectedReferenceFeatureKey && center) {
        boundsList.push([center.lat, center.lng]);
      }
    }
    return boundsList;
  }

  function applyRouteVisibility() {
    if (routeVisibility) {
      if (!map.hasLayer(routeLayer)) {
        routeLayer.addTo(map);
      }
    } else if (map.hasLayer(routeLayer)) {
      map.removeLayer(routeLayer);
    }
  }

  function applyReferenceLayerVisibility() {
    const anyVisible = Array.from(referenceFeatureLayers.values()).some((entry) =>
      referenceVisibleLayerIds.has(entry.layer.id)
    );
    if (anyVisible) {
      if (!map.hasLayer(referenceLayerGroup)) {
        referenceLayerGroup.addTo(map);
      }
    } else if (map.hasLayer(referenceLayerGroup)) {
      map.removeLayer(referenceLayerGroup);
    }

    for (const entry of referenceFeatureLayers.values()) {
      const shouldShow = referenceVisibleLayerIds.has(entry.layer.id);
      const hasLayer = referenceLayerGroup.hasLayer(entry.leafletLayer);
      if (shouldShow && !hasLayer) {
        referenceLayerGroup.addLayer(entry.leafletLayer);
      } else if (!shouldShow && hasLayer) {
        referenceLayerGroup.removeLayer(entry.leafletLayer);
      }
    }
  }

  function applyArchaeologyVisibility() {
    if (archaeologyVisibility) {
      if (!map.hasLayer(archaeologyLayer)) {
        archaeologyLayer.addTo(map);
      }
    } else if (map.hasLayer(archaeologyLayer)) {
      map.removeLayer(archaeologyLayer);
    }

    for (const archaeology of archaeologyLayers.values()) {
      const shouldShow = archaeologyVisibility;
      const hasLayer = archaeologyLayer.hasLayer(archaeology.layer);
      if (shouldShow && !hasLayer) {
        archaeologyLayer.addLayer(archaeology.layer);
      } else if (!shouldShow && hasLayer) {
        archaeologyLayer.removeLayer(archaeology.layer);
      }
    }
  }

  function applyManuscriptVisibility() {
    if (manuscriptVisibility) {
      if (!map.hasLayer(manuscriptLayer)) {
        manuscriptLayer.addTo(map);
      }
    } else if (map.hasLayer(manuscriptLayer)) {
      map.removeLayer(manuscriptLayer);
    }

    for (const manuscript of manuscriptLayers.values()) {
      const shouldShow = manuscriptVisibility;
      const hasLayer = manuscriptLayer.hasLayer(manuscript.layer);
      if (shouldShow && !hasLayer) {
        manuscriptLayer.addLayer(manuscript.layer);
      } else if (!shouldShow && hasLayer) {
        manuscriptLayer.removeLayer(manuscript.layer);
      }
    }
  }

  function fitToContent() {
    const markerBounds = currentMarkerBounds();
    const routeBoundsList = routeVisibility ? currentRouteBounds() : [];
    const referenceBoundsList = currentReferenceBounds();
    const archaeologyBoundsList = archaeologyVisibility ? currentArchaeologyBounds() : [];
    const manuscriptBoundsList = manuscriptVisibility ? currentManuscriptBounds() : [];
    const allBounds = [];

    if (markerBounds) {
      allBounds.push(...markerBounds);
    }

    for (const layerBounds of routeBoundsList) {
      allBounds.push(
        [layerBounds.getSouthWest().lat, layerBounds.getSouthWest().lng],
        [layerBounds.getNorthEast().lat, layerBounds.getNorthEast().lng]
      );
    }

    allBounds.push(...referenceBoundsList);

    for (const layerBounds of archaeologyBoundsList) {
      allBounds.push(
        [layerBounds.getSouthWest().lat, layerBounds.getSouthWest().lng],
        [layerBounds.getNorthEast().lat, layerBounds.getNorthEast().lng]
      );
    }

    for (const layerBounds of manuscriptBoundsList) {
      allBounds.push(
        [layerBounds.getSouthWest().lat, layerBounds.getSouthWest().lng],
        [layerBounds.getNorthEast().lat, layerBounds.getNorthEast().lng]
      );
    }

    if (allBounds.length === 0) {
      map.setView(options.center || DEFAULT_CENTER, options.zoom || DEFAULT_ZOOM);
      return;
    }
    if (allBounds.length === 1) {
      map.setView(allBounds[0], Math.max(options.singleMarkerZoom || 8, map.getZoom()));
      return;
    }
    map.fitBounds(allBounds, { padding: [32, 32] });
  }

  function focusLayerBounds(layer, zoomFallback = 9) {
    if (!layer) {
      return false;
    }
    const bounds = layer.getBounds ? layer.getBounds() : null;
    if (bounds && bounds.isValid && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [24, 24] });
      return true;
    }
    const center = layer.getLatLng ? layer.getLatLng() : null;
    if (center) {
      map.setView([center.lat, center.lng], zoomFallback);
      return true;
    }
    return false;
  }

function focusSelection(kind, item) {
    if (!item) {
      return;
    }
    if (kind === "place" && Number.isFinite(item.latitude) && Number.isFinite(item.longitude)) {
      const placeLayer = placeLayers.get(item.id);
      if (placeLayer) {
        map.setView([item.latitude, item.longitude], 10);
        placeLayer.openPopup();
        return;
      }
      map.setView([item.latitude, item.longitude], 10);
      return;
    }
    if (kind === "archaeology") {
      const archaeology = archaeologyLayers.get(item.id);
      if (focusLayerBounds(archaeology?.layer, 10)) {
        archaeology?.layer?.openPopup?.();
        return;
      }
    }
    if (kind === "manuscript") {
      const manuscript = manuscriptLayers.get(item.id);
      if (focusLayerBounds(manuscript?.layer, 10)) {
        manuscript?.layer?.openPopup?.();
        return;
      }
    }
    if (kind === "route") {
      const route = routeLayers.get(item.id);
      if (focusLayerBounds(route, 9)) {
        route?.openPopup?.();
        return;
      }
    }
    if (kind === "reference_feature") {
      const key = `${item.layerId}:${item.featureId}`;
      const entry = referenceFeatureLayers.get(key);
      if (focusLayerBounds(entry?.leafletLayer, 8)) {
      entry?.leafletLayer?.openPopup?.();
      // Legacy map-layer clients use this equivalent popup hook.
      // layer?.layer?.openPopup?.()
        return;
      }
    }
    if (Number.isFinite(item.latitude) && Number.isFinite(item.longitude)) {
      map.setView([item.latitude, item.longitude], 9);
    }
  }

  function getReferenceFeatureKey(layerId, featureId) {
    return `${layerId}:${featureId}`;
  }

  function syncReferenceStyles() {
    for (const [key, entry] of referenceFeatureLayers.entries()) {
      const selected = key === selectedReferenceFeatureKey;
      if (entry.layer.type === "points" && entry.leafletLayer.setIcon) {
        entry.leafletLayer.setIcon(referencePointIcon(entry.layer, entry.feature, { selected }));
      } else if (entry.leafletLayer.setStyle) {
        entry.leafletLayer.setStyle(referenceLayerStyle(entry.layer, entry.feature, { selected }));
      }
    }
  }

  function refreshRoutes(routes) {
    routeItems = Array.isArray(routes) ? routes.slice() : [];
    routeLayer.clearLayers();
    routeLayers.clear();

    for (const route of routeItems) {
      if (!route?.geojson) {
        continue;
      }
      const routeGeoJson = window.L.geoJSON(route.geojson, {
        style: () => routeStyle(route),
        onEachFeature(feature, layer) {
          layer.on("click", () => {
            if (typeof options.onRouteClick === "function") {
              options.onRouteClick(route);
            }
          });
          layer.bindPopup(renderRoutePopup(route), {
            maxWidth: 340,
            closeButton: true,
          });
        },
      });
      routeLayers.set(route.id, routeGeoJson);
      routeGeoJson.addTo(routeLayer);
    }

    applyRouteVisibility();
  }

  function refreshArchaeologyMarkers(markersList) {
    archaeologyItems = Array.isArray(markersList) ? markersList.slice() : [];
    archaeologyLayer.clearLayers();
    archaeologyLayers.clear();

    for (const item of archaeologyItems) {
      if (!Number.isFinite(item?.latitude) || !Number.isFinite(item?.longitude)) {
        continue;
      }
      const archaeologyMarker = window.L.marker([item.latitude, item.longitude], {
        icon: entityMarkerIcon(item),
        title: item.name || "Unnamed archaeology item",
      });
      archaeologyMarker.bindPopup(renderArchaeologyPopup(item), {
        maxWidth: 360,
        closeButton: true,
      });
      archaeologyMarker.on("click", () => {
        if (typeof options.onArchaeologyClick === "function") {
          options.onArchaeologyClick(item);
        }
      });
      archaeologyLayers.set(item.id, { item, layer: archaeologyMarker });
    }

    applyArchaeologyVisibility();
  }

  function refreshManuscriptMarkers(markersList) {
    manuscriptItems = Array.isArray(markersList) ? markersList.slice() : [];
    manuscriptLayer.clearLayers();
    manuscriptLayers.clear();

    for (const item of manuscriptItems) {
      if (!Number.isFinite(item?.latitude) || !Number.isFinite(item?.longitude)) {
        continue;
      }
      const manuscriptMarker = window.L.marker([item.latitude, item.longitude], {
        icon: entityMarkerIcon(item),
        title: item.name || "Unnamed manuscript",
      });
      manuscriptMarker.bindPopup(renderManuscriptPopup(item), {
        maxWidth: 360,
        closeButton: true,
      });
      manuscriptMarker.on("click", () => {
        if (typeof options.onManuscriptClick === "function") {
          options.onManuscriptClick(item);
        }
      });
      manuscriptLayers.set(item.id, { item, layer: manuscriptMarker });
    }

    applyManuscriptVisibility();
  }

  function refreshReferenceLayers(layers) {
    referenceItems = Array.isArray(layers) ? layers.slice() : [];
    referenceLayerGroup.clearLayers();
    referenceFeatureLayers.clear();

    for (const layerItem of referenceItems) {
      for (const feature of layerItem.features || []) {
        const key = getReferenceFeatureKey(layerItem.id, feature.id);
        let leafletLayer = null;
        if (layerItem.type === "points") {
          leafletLayer = window.L.marker([feature.lat, feature.lng], {
            icon: referencePointIcon(layerItem, feature, { selected: key === selectedReferenceFeatureKey }),
            title: feature.name || "Unnamed reference point",
          });
        } else if (layerItem.type === "lines") {
          leafletLayer = window.L.polyline(feature.points, referenceLayerStyle(layerItem, feature, {
            selected: key === selectedReferenceFeatureKey,
          }));
        } else if (layerItem.type === "polygons") {
          leafletLayer = window.L.polygon(feature.points, referenceLayerStyle(layerItem, feature, {
            selected: key === selectedReferenceFeatureKey,
          }));
        }
        if (!leafletLayer) {
          continue;
        }
        leafletLayer.bindPopup(renderReferenceFeaturePopup(layerItem, feature), {
          maxWidth: 340,
          closeButton: true,
        });
        leafletLayer.on("click", () => {
          if (typeof options.onReferenceFeatureClick === "function") {
            options.onReferenceFeatureClick(layerItem, feature);
          }
        });
        referenceFeatureLayers.set(key, { layer: layerItem, feature, leafletLayer });
      }
    }

    applyReferenceLayerVisibility();
  }

  for (const marker of markers) {
    if (!Number.isFinite(marker.latitude) || !Number.isFinite(marker.longitude)) {
      continue;
    }
    const leafletMarker = window.L.marker([marker.latitude, marker.longitude], {
      icon: entityMarkerIcon(marker),
      title: marker.name || "Unnamed place",
    });
    leafletMarker.bindPopup(renderMapMarkerPopup(marker), {
      maxWidth: 320,
      closeButton: true,
      autoPanPadding: [24, 24],
    });
    leafletMarker.on("click", () => {
      if (typeof options.onMarkerClick === "function") {
        options.onMarkerClick(marker);
      }
    });
    leafletMarker.addTo(markerLayer);
    placeLayers.set(marker.id, leafletMarker);
  }

  const markerBounds = currentMarkerBounds();
  if (markerBounds && markerBounds.length === 1) {
    map.setView(markerBounds[0], Math.max(options.singleMarkerZoom || 8, map.getZoom()));
  } else if (markerBounds && markerBounds.length > 1) {
    map.fitBounds(markerBounds, { padding: [32, 32] });
  }

  refreshRoutes(routeItems);
  refreshArchaeologyMarkers(archaeologyItems);
  refreshManuscriptMarkers(manuscriptItems);
  refreshReferenceLayers(referenceItems);
  fitToContent();

  let tileErrorRaised = false;
  tileLayer.on("tileerror", () => {
    if (tileErrorRaised) {
      return;
    }
    tileErrorRaised = true;
    map.getContainer().classList.add("map-tiles-failed");
    if (typeof options.onTileError === "function") {
      options.onTileError(new Error("Map tiles could not be loaded. Structured local data remains available."));
    }
  });

  return {
    map,
    getViewState() {
      const center = map.getCenter();
      return {
        center: [center.lat, center.lng],
        zoom: map.getZoom(),
        routeVisibility,
        archaeologyVisibility,
        manuscriptVisibility,
        referenceLayerIds: Array.from(referenceVisibleLayerIds),
      };
    },
    getRouteVisibility() {
      return routeVisibility;
    },
    setRouteVisibility(visible) {
      routeVisibility = Boolean(visible);
      applyRouteVisibility();
      fitToContent();
    },
    setRoutes(routes) {
      refreshRoutes(routes);
      fitToContent();
    },
    getArchaeologyVisibility() {
      return archaeologyVisibility;
    },
    setArchaeologyVisibility(visible) {
      archaeologyVisibility = Boolean(visible);
      applyArchaeologyVisibility();
      fitToContent();
    },
    setArchaeologyMarkers(markersList) {
      refreshArchaeologyMarkers(markersList);
      fitToContent();
    },
    getManuscriptVisibility() {
      return manuscriptVisibility;
    },
    setManuscriptVisibility(visible) {
      manuscriptVisibility = Boolean(visible);
      applyManuscriptVisibility();
      fitToContent();
    },
    setManuscriptMarkers(markersList) {
      refreshManuscriptMarkers(markersList);
      fitToContent();
    },
    getManuscriptMarkers() {
      return manuscriptItems.slice();
    },
    setReferenceLayers(layers) {
      refreshReferenceLayers(layers);
      fitToContent();
    },
    setReferenceLayerVisibility(layerId, visible) {
      const normalizedId = String(layerId || "");
      if (!normalizedId) {
        return;
      }
      if (visible) {
        referenceVisibleLayerIds.add(normalizedId);
      } else {
        referenceVisibleLayerIds.delete(normalizedId);
      }
      applyReferenceLayerVisibility();
      fitToContent();
    },
    setSelectedReferenceFeature(layerId, featureId) {
      selectedReferenceFeatureKey = layerId && featureId ? getReferenceFeatureKey(layerId, featureId) : "";
      syncReferenceStyles();
    },
    getReferenceLayerIds() {
      return Array.from(referenceVisibleLayerIds);
    },
    getReferenceLayers() {
      return referenceItems.slice();
    },
    fitToMarkers() {
      fitToContent();
    },
    focusSelection,
    fitToContent,
    invalidateSize() {
      map.invalidateSize();
    },
    destroy() {
      map.remove();
    },
  };
}

function setJourney(journey) {}
// setJourney(journey)
function journeyStopIcon() {}
function referencePointIcon() {}
function renderJourneyStopPopup() {}
function renderReferenceFeaturePopup() {}
