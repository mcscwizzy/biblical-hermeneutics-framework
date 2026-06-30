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

function politicalContextStyle(layerItem) {
  const confidence = String(layerItem.confidence || "unknown").toLowerCase();
  const palette = {
    strong: { color: "#7a2f2f", fillColor: "#f4c7c7", weight: 2, dashArray: "0" },
    likely: { color: "#8b5a00", fillColor: "#f7dfb0", weight: 2, dashArray: "4 6" },
    possible: { color: "#245b82", fillColor: "#d6e8f8", weight: 2, dashArray: "8 8" },
    disputed: { color: "#8a3d73", fillColor: "#f1d2ea", weight: 2, dashArray: "2 6" },
    unknown: { color: "#52616f", fillColor: "#dce3ea", weight: 2, dashArray: "6 8" },
  };
  const base = palette[confidence] || palette.unknown;
  return {
    ...base,
    opacity: 0.9,
    fillOpacity: 0.18,
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

function manuscriptMarkerStyle(item) {
  const confidence = String(item.confidence || "unknown").toLowerCase();
  const palette = {
    strong: { color: "#1b4f72", fillColor: "#bcdaf0" },
    likely: { color: "#175d8c", fillColor: "#cde4f5" },
    possible: { color: "#4c7091", fillColor: "#dceaf4" },
    disputed: { color: "#6b4a7c", fillColor: "#eadcf0" },
    unknown: { color: "#4f6472", fillColor: "#d9e3ea" },
  };
  const base = palette[confidence] || palette.unknown;
  return {
    ...base,
    radius: 7,
    weight: 2,
    opacity: 1,
    fillOpacity: 0.92,
  };
}

function entityMarkerIcon(item) {
  const kind = String(item?.marker_kind || "place").toLowerCase();
  const labelByKind = {
    place: "PL",
    archaeology: "AR",
    manuscript: "MS",
  };
  const classByKind = {
    place: "map-entity-marker--place",
    archaeology: "map-entity-marker--archaeology",
    manuscript: "map-entity-marker--manuscript",
  };
  const label = labelByKind[kind] || labelByKind.place;
  const className = classByKind[kind] || classByKind.place;
  return window.L.divIcon({
    className: `map-entity-marker ${className}`,
    html: `<span class="map-entity-marker__label">${label}</span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 34],
    popupAnchor: [0, -30],
  });
}

export {
  archaeologyMarkerStyle,
  entityMarkerIcon,
  historicalLayerStyle,
  manuscriptMarkerStyle,
  politicalContextStyle,
  routeStyle,
};
