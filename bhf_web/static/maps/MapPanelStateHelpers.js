function normalizeHistoricalPeriod(value, options = []) {
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
  return options.some((option) => option.value === canonical) ? canonical : "all";
}

function syncRouteToggle(mapController, routeToggle) {
  if (!routeToggle || !mapController) {
    return;
  }
  routeToggle.checked = mapController.getRouteVisibility();
}

function syncHistoricalLayerToggles(details, visibleHistoricalLayerIds) {
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

function syncPoliticalContextLayerToggles(details, visiblePoliticalContextLayerIds) {
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

export {
  normalizeHistoricalPeriod,
  syncHistoricalLayerToggles,
  syncPoliticalContextLayerToggles,
  syncRouteToggle,
};
