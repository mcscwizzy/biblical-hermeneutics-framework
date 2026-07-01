import { renderMapMarkerPopup } from "./MapMarkerPopup.js";
import {
  archaeologyMarkerStyle,
  entityMarkerIcon,
  historicalLayerStyle,
  manuscriptMarkerStyle,
  politicalContextStyle,
  routeStyle,
} from "./MapStyles.js";
import {
  renderArchaeologyPopup,
  renderHistoricalLayerPopup,
  renderManuscriptPopup,
  renderPoliticalContextPopup,
  renderRoutePopup,
} from "./MapPopups.js";

// The `map-entity-marker` class remains part of the rendered Leaflet icon markup.
const DEFAULT_CENTER = [31.8, 35.1];
const DEFAULT_ZOOM = 7;

function buildBounds(markers) {
  const validMarkers = markers.filter(
    (marker) => Number.isFinite(marker.latitude) && Number.isFinite(marker.longitude)
  );
  if (validMarkers.length === 0) {
    return null;
  }
  return validMarkers.map((marker) => [marker.latitude, marker.longitude]);
}

export function createBibleMap(container, markers, options = {}) {
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

  const tileLayer = window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
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
  const historicalLayerGroup = window.L.layerGroup();
  const historicalLayers = new Map();
  const historicalVisibleIds = new Set(
    Array.isArray(options.historicalLayerIds) ? options.historicalLayerIds.map((value) => String(value)) : []
  );
  let historicalItems = Array.isArray(options.historicalLayers) ? options.historicalLayers.slice() : [];
  const politicalContextLayerGroup = window.L.layerGroup();
  const politicalContextLayers = new Map();
  const politicalContextVisibleIds = new Set(
    Array.isArray(options.politicalContextLayerIds)
      ? options.politicalContextLayerIds.map((value) => String(value))
      : []
  );
  let politicalContextItems = Array.isArray(options.politicalContextLayers) ? options.politicalContextLayers.slice() : [];

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

  function currentHistoricalBounds() {
    const boundsList = [];
    for (const historical of historicalLayers.values()) {
      if (!historicalVisibleIds.has(historical.item.id)) {
        continue;
      }
      const layerBounds = historical.layer.getBounds ? historical.layer.getBounds() : null;
      if (layerBounds && layerBounds.isValid()) {
        boundsList.push(layerBounds);
      }
    }
    return boundsList;
  }

  function currentPoliticalContextBounds() {
    const boundsList = [];
    for (const politicalContext of politicalContextLayers.values()) {
      if (!politicalContextVisibleIds.has(politicalContext.item.id)) {
        continue;
      }
      const layerBounds = politicalContext.layer.getBounds ? politicalContext.layer.getBounds() : null;
      if (layerBounds && layerBounds.isValid()) {
        boundsList.push(layerBounds);
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

  function applyHistoricalVisibility() {
    const anyVisible = Array.from(historicalLayers.values()).some((historical) =>
      historicalVisibleIds.has(historical.item.id)
    );
    if (anyVisible) {
      if (!map.hasLayer(historicalLayerGroup)) {
        historicalLayerGroup.addTo(map);
      }
    } else if (map.hasLayer(historicalLayerGroup)) {
      map.removeLayer(historicalLayerGroup);
    }

    for (const historical of historicalLayers.values()) {
      const shouldShow = historicalVisibleIds.has(historical.item.id);
      const hasLayer = historicalLayerGroup.hasLayer(historical.layer);
      if (shouldShow && !hasLayer) {
        historicalLayerGroup.addLayer(historical.layer);
      } else if (!shouldShow && hasLayer) {
        historicalLayerGroup.removeLayer(historical.layer);
      }
    }
  }

  function applyPoliticalContextVisibility() {
    const anyVisible = Array.from(politicalContextLayers.values()).some((politicalContext) =>
      politicalContextVisibleIds.has(politicalContext.item.id)
    );
    if (anyVisible) {
      if (!map.hasLayer(politicalContextLayerGroup)) {
        politicalContextLayerGroup.addTo(map);
      }
    } else if (map.hasLayer(politicalContextLayerGroup)) {
      map.removeLayer(politicalContextLayerGroup);
    }

    for (const politicalContext of politicalContextLayers.values()) {
      const shouldShow = politicalContextVisibleIds.has(politicalContext.item.id);
      const hasLayer = politicalContextLayerGroup.hasLayer(politicalContext.layer);
      if (shouldShow && !hasLayer) {
        politicalContextLayerGroup.addLayer(politicalContext.layer);
      } else if (!shouldShow && hasLayer) {
        politicalContextLayerGroup.removeLayer(politicalContext.layer);
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
    const historicalBoundsList = currentHistoricalBounds();
    const politicalContextBoundsList = currentPoliticalContextBounds();
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

    for (const layerBounds of historicalBoundsList) {
      allBounds.push(
        [layerBounds.getSouthWest().lat, layerBounds.getSouthWest().lng],
        [layerBounds.getNorthEast().lat, layerBounds.getNorthEast().lng]
      );
    }

    for (const layerBounds of politicalContextBoundsList) {
      allBounds.push(
        [layerBounds.getSouthWest().lat, layerBounds.getSouthWest().lng],
        [layerBounds.getNorthEast().lat, layerBounds.getNorthEast().lng]
      );
    }

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
    if (kind === "historical_layer") {
      const layer = historicalLayers.get(item.id);
      if (focusLayerBounds(layer?.layer, 8)) {
        layer?.layer?.openPopup?.();
        return;
      }
    }
    if (kind === "political_context") {
      const layer = politicalContextLayers.get(item.id);
      if (focusLayerBounds(layer?.layer, 8)) {
        layer?.layer?.openPopup?.();
        return;
      }
    }
    if (Number.isFinite(item.latitude) && Number.isFinite(item.longitude)) {
      map.setView([item.latitude, item.longitude], 9);
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

  function refreshHistoricalLayers(layers) {
    historicalItems = Array.isArray(layers) ? layers.slice() : [];
    historicalLayerGroup.clearLayers();
    historicalLayers.clear();

    for (const layerItem of historicalItems) {
      if (!layerItem?.geojson) {
        continue;
      }
      const geoJsonLayer = window.L.geoJSON(layerItem.geojson, {
        style: () => historicalLayerStyle(layerItem),
        onEachFeature(feature, layer) {
          layer.on("click", () => {
            if (typeof options.onHistoricalLayerClick === "function") {
              options.onHistoricalLayerClick(layerItem);
            }
          });
          layer.bindPopup(renderHistoricalLayerPopup(layerItem), {
            maxWidth: 360,
            closeButton: true,
          });
        },
      });
      historicalLayers.set(layerItem.id, { item: layerItem, layer: geoJsonLayer });
    }

    applyHistoricalVisibility();
  }

  function refreshPoliticalContextLayers(layers) {
    politicalContextItems = Array.isArray(layers) ? layers.slice() : [];
    politicalContextLayerGroup.clearLayers();
    politicalContextLayers.clear();

    for (const layerItem of politicalContextItems) {
      if (!layerItem?.geojson) {
        continue;
      }
      const geoJsonLayer = window.L.geoJSON(layerItem.geojson, {
        style: () => politicalContextStyle(layerItem),
        onEachFeature(feature, layer) {
          layer.on("click", () => {
            if (typeof options.onPoliticalContextClick === "function") {
              options.onPoliticalContextClick(layerItem);
            }
          });
          layer.bindPopup(renderPoliticalContextPopup(layerItem), {
            maxWidth: 360,
            closeButton: true,
          });
        },
      });
      politicalContextLayers.set(layerItem.id, { item: layerItem, layer: geoJsonLayer });
    }

    applyPoliticalContextVisibility();
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
  refreshHistoricalLayers(historicalItems);
  refreshPoliticalContextLayers(Array.isArray(options.politicalContextLayers) ? options.politicalContextLayers : []);
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
        historicalLayerIds: Array.from(historicalVisibleIds),
        politicalContextLayerIds: Array.from(politicalContextVisibleIds),
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
    getHistoricalLayerVisibility(layerId) {
      return historicalVisibleIds.has(String(layerId));
    },
    setHistoricalLayerVisibility(layerId, visible) {
      const normalizedId = String(layerId);
      if (!normalizedId) {
        return;
      }
      if (visible) {
        historicalVisibleIds.add(normalizedId);
      } else {
        historicalVisibleIds.delete(normalizedId);
      }
      applyHistoricalVisibility();
      fitToContent();
    },
    setHistoricalLayers(layers) {
      refreshHistoricalLayers(layers);
      fitToContent();
    },
    getPoliticalContextLayerVisibility(layerId) {
      return politicalContextVisibleIds.has(String(layerId));
    },
    setPoliticalContextLayerVisibility(layerId, visible) {
      const normalizedId = String(layerId);
      if (!normalizedId) {
        return;
      }
      if (visible) {
        politicalContextVisibleIds.add(normalizedId);
      } else {
        politicalContextVisibleIds.delete(normalizedId);
      }
      applyPoliticalContextVisibility();
      fitToContent();
    },
    setPoliticalContextLayers(layers) {
      refreshPoliticalContextLayers(layers);
      fitToContent();
    },
    getPoliticalContextLayerIds() {
      return Array.from(politicalContextVisibleIds);
    },
    getPoliticalContextLayers() {
      return politicalContextItems.slice();
    },
    getHistoricalLayerIds() {
      return Array.from(historicalVisibleIds);
    },
    getHistoricalLayers() {
      return historicalItems.slice();
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
