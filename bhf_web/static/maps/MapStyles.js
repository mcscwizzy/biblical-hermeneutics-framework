const CONFIDENCE_ALIASES = {
  established: "Established",
  strong: "Established",
  "well supported": "Well Supported",
  likely: "Well Supported",
  "reasonably supported": "Reasonably Supported",
  moderate: "Reasonably Supported",
  tentative: "Tentative",
  possible: "Tentative",
  disputed: "Tentative",
  "traditional identification": "Traditional Identification",
  traditional: "Traditional Identification",
  "traditional identification": "Traditional Identification",
  "well-supported": "Well Supported",
  "reasonably-supported": "Reasonably Supported",
};

function normalizeConfidence(value) {
  const normalized = String(value || "").trim();
  if (!normalized) {
    return "Tentative";
  }
  return CONFIDENCE_ALIASES[normalized.toLowerCase()] || normalized;
}

function routeStyle(route) {
  const confidence = normalizeConfidence(route.confidence);
  const palette = {
    Established: { color: "#245b36", weight: 4, dashArray: "0" },
    "Well Supported": { color: "#245b82", weight: 4, dashArray: "4 6" },
    "Reasonably Supported": { color: "#7d5c13", weight: 3, dashArray: "8 8" },
    Tentative: { color: "#9a2c2c", weight: 3, dashArray: "2 6" },
    "Traditional Identification": { color: "#52616f", weight: 3, dashArray: "6 8" },
  };
  const base = palette[confidence] || palette.Tentative;
  return {
    ...base,
    opacity: 0.95,
  };
}

function historicalLayerStyle(layerItem) {
  const confidence = normalizeConfidence(layerItem.confidence);
  const palette = {
    Established: { color: "#5f3dc4", fillColor: "#d9ccff", weight: 2, dashArray: "0" },
    "Well Supported": { color: "#245b82", fillColor: "#d6e8f8", weight: 2, dashArray: "4 6" },
    "Reasonably Supported": { color: "#8c5a11", fillColor: "#f4e0b8", weight: 2, dashArray: "8 8" },
    Tentative: { color: "#9a2c2c", fillColor: "#f8d7d7", weight: 2, dashArray: "2 6" },
    "Traditional Identification": { color: "#52616f", fillColor: "#dce3ea", weight: 2, dashArray: "6 8" },
  };
  const base = palette[confidence] || palette.Tentative;
  return {
    ...base,
    opacity: 0.9,
    fillOpacity: 0.2,
  };
}

function politicalContextStyle(layerItem) {
  const confidence = normalizeConfidence(layerItem.confidence);
  const palette = {
    Established: { color: "#7a2f2f", fillColor: "#f4c7c7", weight: 2, dashArray: "0" },
    "Well Supported": { color: "#8b5a00", fillColor: "#f7dfb0", weight: 2, dashArray: "4 6" },
    "Reasonably Supported": { color: "#245b82", fillColor: "#d6e8f8", weight: 2, dashArray: "8 8" },
    Tentative: { color: "#8a3d73", fillColor: "#f1d2ea", weight: 2, dashArray: "2 6" },
    "Traditional Identification": { color: "#52616f", fillColor: "#dce3ea", weight: 2, dashArray: "6 8" },
  };
  const base = palette[confidence] || palette.Tentative;
  return {
    ...base,
    opacity: 0.9,
    fillOpacity: 0.18,
  };
}

function archaeologyMarkerStyle(item) {
  const confidence = normalizeConfidence(item.confidence);
  const palette = {
    Established: { color: "#9a5a00", fillColor: "#ffd89a" },
    "Well Supported": { color: "#b26a00", fillColor: "#ffe0b3" },
    "Reasonably Supported": { color: "#c78200", fillColor: "#fff0cc" },
    Tentative: { color: "#8d3a1c", fillColor: "#f5c9ba" },
    "Traditional Identification": { color: "#7b5a2a", fillColor: "#e7d6b2" },
  };
  const base = palette[confidence] || palette.Tentative;
  return {
    ...base,
    radius: 8,
    weight: 2,
    opacity: 1,
    fillOpacity: 0.9,
  };
}

function manuscriptMarkerStyle(item) {
  const confidence = normalizeConfidence(item.confidence);
  const palette = {
    Established: { color: "#1b4f72", fillColor: "#bcdaf0" },
    "Well Supported": { color: "#175d8c", fillColor: "#cde4f5" },
    "Reasonably Supported": { color: "#4c7091", fillColor: "#dceaf4" },
    Tentative: { color: "#6b4a7c", fillColor: "#eadcf0" },
    "Traditional Identification": { color: "#4f6472", fillColor: "#d9e3ea" },
  };
  const base = palette[confidence] || palette.Tentative;
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
  };
  const classByKind = {
    place: "map-entity-marker--place",
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
