import { renderMapMarkerPopup } from "./MapMarkerPopup.js";

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

function routeStyle(route) {
  const confidence = String(route.confidence || "unknown").toLowerCase();
  const palette = {
    strong: { color: "#245b36", weight: 4, dashArray: "0" },
    likely: { color: "#245b82", weight: 4, dashArray: "4 6" },
    possible: { color: "#7d5c13", weight: 3, dashArray: "8 8" },
    disputed: { color: "#9a2c2c", weight: 3, dashArray: "2 6" },
    unknown: { color: "#52616f", weight: 3, dashArray: "6 8" },
  };
  const base = palette[confidence] || palette.unknown;
  return {
    ...base,
    opacity: 0.95,
  };
}

function historicalLayerStyle(layerItem) {
  const confidence = String(layerItem.confidence || "unknown").toLowerCase();
  const palette = {
    strong: { color: "#5f3dc4", fillColor: "#d9ccff", weight: 2, dashArray: "0" },
    likely: { color: "#245b82", fillColor: "#d6e8f8", weight: 2, dashArray: "4 6" },
    possible: { color: "#8c5a11", fillColor: "#f4e0b8", weight: 2, dashArray: "8 8" },
    disputed: { color: "#9a2c2c", fillColor: "#f8d7d7", weight: 2, dashArray: "2 6" },
    unknown: { color: "#52616f", fillColor: "#dce3ea", weight: 2, dashArray: "6 8" },
  };
  const base = palette[confidence] || palette.unknown;
  return {
    ...base,
    opacity: 0.9,
    fillOpacity: 0.2,
  };
}

function archaeologyMarkerStyle(item) {
  const confidence = String(item.confidence || "unknown").toLowerCase();
  const palette = {
    strong: { color: "#9a5a00", fillColor: "#ffd89a" },
    likely: { color: "#b26a00", fillColor: "#ffe0b3" },
    possible: { color: "#c78200", fillColor: "#fff0cc" },
    disputed: { color: "#8d3a1c", fillColor: "#f5c9ba" },
    unknown: { color: "#7b5a2a", fillColor: "#e7d6b2" },
  };
  const base = palette[confidence] || palette.unknown;
  return {
    ...base,
    radius: 8,
    weight: 2,
    opacity: 1,
    fillOpacity: 0.9,
  };
}

function renderRoutePopup(route) {
  const name = escapeHtml(route.name || "Unnamed route");
  const period = escapeHtml(route.period || "Unknown period");
  const routeType = escapeHtml(route.route_type || "route");
  const description = escapeHtml(route.description || "No description available.");
  return `
    <article class="map-popup">
      <h3>${name}</h3>
      <p class="map-popup-region">${period}</p>
      <p class="map-popup-confidence">${routeType}</p>
      <p class="map-popup-description">${description}</p>
    </article>
  `;
}

function renderHistoricalLayerPopup(layerItem) {
  const name = escapeHtml(layerItem.name || "Unnamed layer");
  const period = escapeHtml(layerItem.period || "Unknown period");
  const layerType = escapeHtml(layerItem.layer_type || "layer");
  const description = escapeHtml(layerItem.description || "No description available.");
  const confidence = escapeHtml(layerItem.confidence || "unknown");
  return `
    <article class="map-popup">
      <h3>${name}</h3>
      <p class="map-popup-region">${period}</p>
      <p class="map-popup-confidence">${layerType} · Confidence: ${confidence}</p>
      <p class="map-popup-description">${description}</p>
    </article>
  `;
}

function renderArchaeologyPopup(item) {
  const name = escapeHtml(item.name || "Unnamed archaeology item");
  const siteName = escapeHtml(item.site_name || "Unknown site");
  const period = escapeHtml(item.period || "Unknown period");
  const itemType = escapeHtml(item.item_type || "archaeology item");
  const relationship = escapeHtml(item.relationship || "");
  const whyItMatters = escapeHtml(item.why_it_matters || "No explanation available.");
  return `
    <article class="map-popup">
      <h3>${name}</h3>
      <p class="map-popup-region">${siteName}</p>
      <p class="map-popup-confidence">${period} · ${itemType}</p>
      <p class="map-popup-description">${relationship ? `${relationship}. ` : ""}${whyItMatters}</p>
    </article>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
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
  const archaeologyLayer = window.L.layerGroup();
  const archaeologyLayers = new Map();
  const routeLayer = window.L.layerGroup();
  const routeLayers = new Map();
  let routeVisibility = Boolean(options.routeVisibility);
  let archaeologyVisibility = Boolean(options.archaeologyVisibility);
  let archaeologyItems = Array.isArray(options.archaeologyMarkers) ? options.archaeologyMarkers.slice() : [];
  let routeItems = Array.isArray(options.routes) ? options.routes.slice() : [];
  const historicalLayerGroup = window.L.layerGroup();
  const historicalLayers = new Map();
  const historicalVisibleIds = new Set(
    Array.isArray(options.historicalLayerIds) ? options.historicalLayerIds.map((value) => String(value)) : []
  );
  let historicalItems = Array.isArray(options.historicalLayers) ? options.historicalLayers.slice() : [];

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

  function fitToContent() {
    const markerBounds = currentMarkerBounds();
    const routeBoundsList = routeVisibility ? currentRouteBounds() : [];
    const historicalBoundsList = currentHistoricalBounds();
    const archaeologyBoundsList = archaeologyVisibility ? currentArchaeologyBounds() : [];
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

    for (const layerBounds of archaeologyBoundsList) {
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
      const archaeologyMarker = window.L.circleMarker([item.latitude, item.longitude], archaeologyMarkerStyle(item));
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

  for (const marker of markers) {
    if (!Number.isFinite(marker.latitude) || !Number.isFinite(marker.longitude)) {
      continue;
    }
    const leafletMarker = window.L.marker([marker.latitude, marker.longitude], {
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
  }

  const markerBounds = currentMarkerBounds();
  if (markerBounds && markerBounds.length === 1) {
    map.setView(markerBounds[0], Math.max(options.singleMarkerZoom || 8, map.getZoom()));
  } else if (markerBounds && markerBounds.length > 1) {
    map.fitBounds(markerBounds, { padding: [32, 32] });
  }

  refreshRoutes(routeItems);
  refreshArchaeologyMarkers(archaeologyItems);
  refreshHistoricalLayers(historicalItems);
  fitToContent();

  let tileErrorRaised = false;
  tileLayer.on("tileerror", () => {
    if (tileErrorRaised) {
      return;
    }
    tileErrorRaised = true;
    if (typeof options.onTileError === "function") {
      options.onTileError(new Error("Map tiles could not be loaded."));
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
        historicalLayerIds: Array.from(historicalVisibleIds),
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
    getHistoricalLayerIds() {
      return Array.from(historicalVisibleIds);
    },
    getHistoricalLayers() {
      return historicalItems.slice();
    },
    fitToMarkers() {
      fitToContent();
    },
    fitToContent,
    invalidateSize() {
      map.invalidateSize();
    },
    destroy() {
      map.remove();
    },
  };
}
